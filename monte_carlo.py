######### Author: Charan Atreya
#### verion 2
####### 
# Purpose: The pupose of this script is to analyze Jira tickets and produce flow metrics:
# Throughput - tickets per week
# Cycle Time - completed tickets
# Forecast probabilistic delivery dates, along with distribution of probabilities
#######

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import subprocess
import json
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator
import sys
import os
import ast  # Import the 'ast' module for literal evaluation
import math

# Step 1: Configuration Management
class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path  # Store the file path for future use
        self.config = self.read_config(config_path)

    @staticmethod
    def read_config(config_path: str) -> dict:
        """Reads the configuration file and returns its contents as a dictionary."""
        with open(config_path, 'r') as file:
            return json.load(file)

    def get(self, key: str, default=None):
        """Retrieves a configuration value by key, with an optional default."""
        return self.config['configData'][0].get(key, default)
    
    def set(self, key: str, value):
        """Sets a configuration value by key and writes the updated configuration to the file."""
        self.config['configData'][0][key] = value
        self.write_config()

    def write_config(self):
        """Writes the current in-memory configuration back to the JSON file."""
        try:
            with open(self.config_path, 'w') as file:
                json.dump(self.config, file, indent=4)
        except IOError as e:
            print(f"Error writing to config file {self.config_path}: {e}")


# Step 2: Data Management
class DataManager:
    @staticmethod
    def read_csv(file_path, releases, exclude_from_status, issue_types, wip_category_included, excluded_epics,change_log):
        try:
            df = pd.read_csv(file_path)
        except FileNotFoundError:
            print('The CSV file containing historical JIRA tickets can\'t be found')
            sys.exit()

        # Filter by release and other conditions
        if releases:
            df['Release'] = df['Release'].apply(ast.literal_eval)
            df = df[df['Release'].apply(lambda x: releases in x)]

        # Apply initial filters
        filtered_df = df[
        df['WIP Category'].isin(wip_category_included) &
        ~df['IssueType'].isin(issue_types)
        ]

        # Apply additional filter conditionally
        if change_log == "yes":
            filtered_df = filtered_df[~filtered_df["From status"].isin(exclude_from_status)]

        return filtered_df

    @staticmethod
    def calculate_cycle_times(df,config):
        df['Time in From Status (days)'] = pd.to_numeric(df['Time in From Status (days)'], errors='coerce')
        grouped = df.groupby('Jira Key')['Time in From Status (days)'].sum().reset_index()
        cycle_times = grouped['Time in From Status (days)'].values

        # Get the output path for the CSV from the configuration
        output_csv_path = config.get('csvFolderPath')
        full_output_path = os.path.join(output_csv_path, 'debug_step2-data_for_cycle_time_calcs.csv')

        # Save filtered data to a CSV file for debugging
        df.to_csv(full_output_path)

        return np.array(cycle_times)

    @staticmethod
    def calculate_avg_weekly_throughput(df, weeks_for_roll_avg):
        completed_df = df[df['WIP Category'] == 'Done'].drop_duplicates(subset=['Jira Key', 'Done Year', 'Done Week'])
        weekly_counts = completed_df.groupby('Done Year Week')['Jira Key'].count().reset_index()
        weekly_counts['Takt Time'] = weekly_counts['Jira Key'] / 5
        
        rolling_median = weekly_counts['Jira Key'].tail(weeks_for_roll_avg).median()
        return weekly_counts, rolling_median, len(completed_df)
    
    @staticmethod
    def sum_of_tickets(csv_file_name, releases, issue_types, excluded_epics, config_manager):
        """
        Sum the tickets based on filters and update the configuration file.
        """
        try:
            # Load the CSV file into a DataFrame
            df = pd.read_csv(csv_file_name)
        except FileNotFoundError:
            print(f'The {csv_file_name} file containing historical JIRA tickets can\'t be found.')
            sys.exit()

        # Filter by release if specified
        if releases:
            df['Release'] = df['Release'].apply(ast.literal_eval)
            df = df[df['Release'].apply(lambda x: releases in x)]

        # Apply filters to the DataFrame
        filtered_df = df[
            ((df['WIP Category'] == "Prioritized") | 
             (df['WIP Category'] == "WIP") |
             (df['WIP Category'] == "Backlog")) &
            ~df['IssueType'].isin(issue_types) &
            ~df["Epic Link"].isin(excluded_epics)
        ]

        # Get the output path for the CSV from the configuration
        output_csv_path = config_manager.get('csvFolderPath')
        full_output_path = os.path.join(output_csv_path, 'debug_sum_jira_tickets.csv')

        # Save filtered data to a CSV file for debugging
        filtered_df.to_csv(full_output_path)

        # Calculate remaining tickets and update configuration
        remaining_tickets = len(filtered_df)
        config_manager.set('remainingTicketCount', remaining_tickets)  # Update the value in the config
        print(f"Remaining tickets: {remaining_tickets}")

        # Calculate final ticket count and update configuration
        final_ticket_count = int(math.ceil(remaining_tickets * 1.10))
        config_manager.set('finalTicketCount', final_ticket_count)  # Update final ticket count
        print(f"Final ticket count (with buffer): {final_ticket_count}")

        return
    
    @staticmethod
    def calculate_takt_time_from_demand(config_manager):
        # Load the path from the configuration
        csv_file_path = config_manager.get('csvFolderPath') + config_manager.get('csv_list_of_tickets')

        try:
            df = pd.read_csv(csv_file_path)
        except FileNotFoundError:
            print(f'The file {csv_file_path} containing the list of tickets cannot be found.')
            sys.exit()

        # Filter out tickets not in the current release
        releases = config_manager.get('release')
        if releases:
            df['Release'] = df['Release'].apply(ast.literal_eval)
            df = df[df['Release'].apply(lambda x: releases in x)]

        # Filter out specific ticket types
        issue_types = config_manager.get('excluded_issue_types')
        if issue_types:
            df = df[~df['IssueType'].isin(issue_types)]

        # Calculate the number of tickets completed per week (Throughput)
        completed_tickets_per_week = df[df['WIP Category'] == 'Done'].groupby('Done Year Week')['Jira Key'].count().mean()

        # Ensure throughput is not zero
        if completed_tickets_per_week == 0:
            return float('inf')  # Infinite Takt Time if no tickets are completed

        # Get available hours per week from the configuration
        available_hours_per_week = config_manager.get('available_hours_per_week', 36.25)  # Default to 36.25 hours per week

        # Calculate Takt Time based on completed tickets per week
        takt_time = available_hours_per_week / completed_tickets_per_week
        return takt_time
    
    @staticmethod
    def calculate_tickets_per_week_to_meet_deadline(remaining_tickets, end_date):
        """
        Calculate the number of tickets that need to be completed per week to meet the specified end date.

        Parameters:
        - remaining_tickets (int): The number of tickets left to complete.
        - end_date (str): The target end date in the format 'YYYY-MM-DD'.

        Returns:
        - float: The required tickets per week to meet the end date.
        """
        # Convert end_date to a datetime object
        target_date = datetime.strptime(end_date, '%Y-%m-%d')
        current_date = datetime.today()

        # Calculate the number of weeks until the target date
        days_until_deadline = (target_date - current_date).days
        weeks_until_deadline = days_until_deadline / 7

        # Calculate tickets per week needed
        if weeks_until_deadline > 0:
            tickets_per_week = remaining_tickets / weeks_until_deadline
        else:
            tickets_per_week = float('inf')  # Deadline has passed or is today, handle accordingly

        return tickets_per_week

# Step 3: Simulation
class MonteCarloSimulator:
    @staticmethod
    def run_simulation(weekly_takt_time_list, remaining_tickets, takt_time, weeks_for_roll_avg, config, n_simulations=10000):
        """
        Run a Monte Carlo simulation to estimate the number of weeks required to complete the remaining tickets.
        This version uses historical data to simulate the completion time using the approach from Scrumage.
        """

        # Ensure weeks_for_roll_avg is an integer
        weeks_for_roll_avg = int(weeks_for_roll_avg)

        # Initialize an array to store the weeks needed to complete in each simulation
        weeks_to_complete = np.zeros(n_simulations)

        # Use the most recent throughput data based on the configured rolling average weeks
        historical_tickets_completed = np.array(weekly_takt_time_list['Jira Key'])[-weeks_for_roll_avg:]

        for i in range(n_simulations):
            # Initialize counters for simulation
            remaining = remaining_tickets
            weeks = 0

            while remaining > 0:
                # Randomly sample from the historical ticket completions for each week
                sampled_throughput = np.random.choice(historical_tickets_completed)

                # Deduct the sampled throughput from remaining tickets
                remaining -= sampled_throughput

                # Increment the number of weeks required
                weeks += 1

            # Store the result
            weeks_to_complete[i] = weeks
        # Convert simulation results to a DataFrame
        simulation_df = pd.DataFrame({'Weeks to Complete': weeks_to_complete})

        # Save the DataFrame to a CSV file
        output_csv_path = config.get('csvFolderPath')
        simulation_df.to_csv(output_csv_path+'debug_step3_monte_carlo.csv', index=False)
        
        return weeks_to_complete


# Step 4 Generate Forecasts
class ForecastGenerator:
    def __init__(self, release, wip_category_included, exclude_from_status, issue_types, completed_tickets,
                 median_cycle_time, std_dev, rolling_avg_completion_rate, confidence, remaining_tickets, weeks_to_complete, rolling_avg_weeks):
        self.release = release
        self.wip_category_included = wip_category_included
        self.exclude_from_status = exclude_from_status
        self.issue_types = issue_types
        self.completed_tickets = completed_tickets
        self.median_cycle_time = median_cycle_time
        self.std_dev = std_dev
        self.rolling_avg_completion_rate = rolling_avg_completion_rate
        self.confidence = confidence
        self.remaining_tickets = remaining_tickets
        self.weeks_to_complete = weeks_to_complete
        self.rolling_avg_weeks = rolling_avg_weeks

    def generate_summary(self):
        # lower_bound_days = np.percentile(self.weeks_to_complete, 100-self.confidence) * 5
        upper_bound_days = np.percentile(self.weeks_to_complete, self.confidence) * 5
        lower_bound_days = np.min(self.weeks_to_complete)*5

        inner_bound_date = datetime.today() + timedelta(days=lower_bound_days)
        outer_bound_date = datetime.today() + timedelta(days=upper_bound_days)

        summary = (
            f"\nThe following empirical data for the Release: {self.release} is used to forecast release dates:\n"
            f"- {self.wip_category_included} are included\n"
            f"- Time spent in {self.exclude_from_status} queues are NOT included\n"
            f"- {self.issue_types} ticket types are NOT included\n"
            f"- {self.completed_tickets} tickets have been completed so far\n"
            f" -- with a median cycle time of {self.median_cycle_time:.2f} working days per ticket and standard deviation of {self.std_dev:.2f} working days\n"
            f" -- with a {self.rolling_avg_weeks} week rolling median of {self.rolling_avg_completion_rate:.2f} tickets/week\n\n"
            f"Forecast: There's a {self.confidence}% chance that the remaining {self.remaining_tickets} (+10% additional tickets to account for unknown unknowns) tickets "
            f"are expected to be delivered on or before {outer_bound_date.strftime('%d %B, %Y')}\n"
        )
        return summary

    def generate_table(self):
        table_data = []
        # Define percentiles to represent a range from 10% to 90%
        percentiles = sorted(range(10, 100, 10))

        for probability in percentiles:
            # Correctly calculate the upper bound using the current percentile
            upper_bound_days = np.percentile(self.weeks_to_complete, probability) * 5

            # Calculate the date by adding the upper bound days to the current date
            to_date = datetime.today() + timedelta(days=upper_bound_days)

            # Append the data for each probability level
            table_data.append({
                'Probability | ': f"{probability}% | ",
                'On or before ': f"{to_date.strftime('%d %B, %Y')} "
            })

        # Convert table data to a DataFrame for easy display
        forecast_table = pd.DataFrame(table_data)
        return forecast_table

# Step 5: Plotting
from datetime import datetime

class PlotManager:
    @staticmethod
    def plot_cycle_time_distribution(data, path, xlabel, ylabel, title, num_bins, completed_count, graph_type, config):
        plt.figure(figsize=(10, 6))
        historical_count = len(data)

        if historical_count == 0:
            print("No data to plot.")
            return

        # Adjust number of bins dynamically
        unique_values = len(np.unique(data))
        bins = min(num_bins, unique_values)  # Use either the specified number of bins or the number of unique values
        bins = 'auto' if bins < 2 else bins  # Use 'auto' if there are fewer than 2 unique values

        # Plot histogram
        n, bins, patches = plt.hist(data, bins=bins, alpha=0.75, color='skyblue', edgecolor='black')

        # Annotate histogram
        PlotManager._annotate_histogram(n, bins, historical_count)

        # Plot mean, median, and standard deviation lines
        mean, median, std_dev = np.mean(data), np.median(data), np.std(data)
        PlotManager._plot_vertical_lines(mean, median, std_dev)

        # Get the confidence level and calculate the corresponding percentile
        confidence_level = config.get('confidenceLevels', '85%')  # Default to '85%' if not specified
        # Handle both string and integer cases for confidence level
        if isinstance(confidence_level, str):
            confidence_percentile = float(confidence_level.strip('%'))
        else:
            confidence_percentile = float(confidence_level)
        
        percentile_value = np.percentile(data, confidence_percentile)  # Calculate the percentile value

        # Plot vertical line for the percentile
        plt.axvline(percentile_value, color='red', linestyle='dashed', linewidth=1.5, label=f'{confidence_level} Percentile: {percentile_value:.2f}')

        # Add titles, labels, and legend
        project = config.get('project', 'Unknown Project')
        release = config.get('release', 'Unknown Release')
        current_date = datetime.today().strftime('%d-%b-%Y')
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(f"{title}\nProject: {project}, Release: {release}, Date: {current_date}")
        plt.legend(loc='upper right')
        plt.gcf().subplots_adjust(bottom=0.15)
        plt.savefig(path, bbox_inches='tight')
        plt.clf()

    @staticmethod
    def _annotate_histogram(n, bins, historical_count):
        for count, center in zip(n, bins[:-1]):
            if count > 0:  # Only add a label if the count is greater than 0
                percentage = (count / historical_count) * 100
                plt.text(center, count, f'{percentage:.2f}%', ha='center', va='bottom', fontsize=6)


    @staticmethod
    def _plot_vertical_lines(mean, median, std_dev):
        """Plots vertical lines for mean, median, and standard deviation on a histogram."""
        plt.axvline(mean, color='blue', linestyle='dashed', linewidth=1, label=f'Mean: {mean:.2f}')
        plt.axvline(median, color='green', linestyle='dashed', linewidth=1, label=f'Median: {median:.2f}')
        # plt.axvline(median + std_dev, color='orange', linestyle='dashed', linewidth=1, label=f'Median + Std Dev: {median + std_dev:.2f}')
        # plt.axvline(mean + std_dev, color='grey', linestyle='dashed', linewidth=1, label=f'Mean + Std Dev: {mean + std_dev:.2f}')

    @staticmethod
    def plot_throughput_by_week(weekly_counts, output_path, config, week_start=True):
        # Convert 'Done Year Week' to datetime objects
        # First, interpret each "Year-Week" as the start of the week (Monday)
        weekly_counts['Date'] = pd.to_datetime(weekly_counts['Done Year Week'] + '-1', format='%Y-%W-%w')

        # Adjust to the correct week start (Sunday) or end (Saturday)
        if week_start:
            # Shift to previous Sunday
            weekly_counts['Date'] = weekly_counts['Date'] - pd.to_timedelta(1, unit='D')
        else:
            # Shift to following Saturday
            weekly_counts['Date'] = weekly_counts['Date'] + pd.to_timedelta(5, unit='D')

        # Plotting
        plt.figure(figsize=(10, 6))
        plt.plot(weekly_counts['Date'], weekly_counts['Jira Key'], marker='o', linestyle='-', color='blue')

        # Add labels to each data point
        for i, txt in enumerate(weekly_counts['Jira Key']):
            if txt > 0:
                plt.annotate(txt, (weekly_counts['Date'].iloc[i], weekly_counts['Jira Key'].iloc[i]),
                             textcoords="offset points", xytext=(0, 5), ha='center', fontsize=8)

        project = config.get('project', 'Unknown Project')
        release = config.get('release', 'Unknown Release')
        current_date = datetime.today().strftime('%d-%b-%Y')
        plt.xlabel('Week Starting')
        plt.ylabel('Tickets Completed')
        plt.title(f"Throughput by Week\nProject: {project}, Release: {release}, Date: {current_date}")

        # Adjust the x-axis to show the correct start or end of the week
        plt.gca().xaxis.set_major_locator(WeekdayLocator(byweekday=6 if week_start else 5))  # Sunday=6, Saturday=5
        plt.gca().xaxis.set_major_formatter(DateFormatter('%d %b (%a)'))  # Display the day, month, and weekday

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.clf()

    @staticmethod
    def plot_histogram_cycle_time(cycle_times, output_path, config):
        plt.figure(figsize=(10, 6))

        # Plot histogram
        counts, bins, patches = plt.hist(cycle_times, bins=20, color='skyblue', edgecolor='black', alpha=0.75)

        # Calculate cumulative data for the line plot
        cumulative_counts = np.cumsum(counts)
        cumulative_percentages = cumulative_counts / cumulative_counts[-1] * 100  # Convert to percentages

        # Plot cumulative line graph over the histogram with smaller dots at increments of 10
        bin_centers = (bins[:-1] + bins[1:]) / 2  # Calculate bin centers for plotting
        plt.plot(bin_centers, cumulative_percentages, color='grey', linestyle='dashed', marker='.', markersize=2, linewidth=1.5, label='Cumulative Completion (%)')

        # Add red dots at increments of 10 days and labels at increments of 20
        for i in range(0, 101, 10):  # Percentile increments of 10 for red dots
            days = np.percentile(cycle_times, i)
            percentile_value = np.interp(days, bin_centers, cumulative_percentages)  # Interpolate the percentile value on the cumulative line
            plt.plot(days, percentile_value, 'b.')  # Add small grey dot at each percentile

         # Label the red dots at increments of 20 days with conditional offsets
        for i in range(20, 101, 20):  # Start from 20% for the labels to avoid overlap at 0%
            days = np.percentile(cycle_times, i)
            percentile_value = np.interp(days, bin_centers, cumulative_percentages)  # Interpolate the percentile value on the cumulative line
            plt.plot(days, percentile_value, 'b.', markersize=1)  # Adjust 'markersize' for grey dots

            # Conditional offset to avoid overlap
            if i in [20]:  # Adjust these as needed for specific labels
                label_pos = (days, percentile_value + 20)
            elif i in [40, 60, 80]:
                label_pos = (days, percentile_value + 10)    
            elif i in [80]:
                label_pos = (days, percentile_value - 10)
            else:
                label_pos = (days, percentile_value + 5)

            plt.annotate(f"{i}%", xy=(days, percentile_value), xytext=label_pos,
                        arrowprops=dict(arrowstyle="->", color='grey', linestyle = 'dashed', lw=0.8),
                        fontsize=7, color='grey', ha='center')

        # Set x-axis ticks to increments of 7 days
        x_ticks = np.arange(0, max(cycle_times) + 14, 14)
        plt.xticks(x_ticks, fontsize=6)  # Adjust fontsize as needed

        # Add x-axis labels for clarity, showing count values only if they are greater than zero
        for i in range(len(counts)):
            if counts[i] > 0:  # Only display labels for bins with counts greater than zero
                plt.text(bin_centers[i], counts[i], str(int(counts[i])), ha='center', va='bottom', fontsize=8)

        # Plot mean, median, and standard deviation lines without green vertical lines
        mean = np.mean(cycle_times)
        median = np.median(cycle_times)
        plt.axvline(mean, color='blue', linestyle='dashed', linewidth=1, label=f'Mean: {mean:.2f}')
        plt.axvline(median, color='green', linestyle='dashed', linewidth=1, label=f'Median: {median:.2f}')

        # Get project details and current date
        project = config.get('project', 'Unknown Project')
        release = config.get('release', 'Unknown Release')
        current_date = datetime.today().strftime('%d-%b-%Y')

        # Update the title with the total number of tickets
        total_tickets = len(cycle_times)
        plt.xlabel('Cycle Time (Days)')
        plt.ylabel('Frequency / Cumulative Percentage')
        plt.title(f"Cycle Time Histogram with Cumulative Completion (Total Tickets: {total_tickets})\nProject: {project}, Release: {release}, Date: {current_date}")

        # Move the legend outside the plot area
        plt.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)
        plt.grid(False)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight')  # Adjust saving to accommodate legend outside plot
        plt.clf()
        


# Main Execution
def main():
    # clear terminal screen
    os.system('clear')

    # Load configuration
    config = ConfigManager('ignore/configs.json')

    # Optionally update data from Jira
    if input('Update data from Jira (Y): ').lower() == 'y':
        subprocess.run(['python', config.get('exportJiraScript')])
    # subprocess.run(['python', config.get('exportJiraListFile')])

   # Use DataManager to process CSV and update the config file
    DataManager.sum_of_tickets(
        csv_file_name=config.get('csvFolderPath') + config.get('csv_list_of_tickets'),
        releases=config.get('release'),
        issue_types=config.get('excluded_issue_types'),
        excluded_epics=config.get('epic_to_exclude'),
        config_manager=config  # Use the 'config' instance here
    )
    
    # Calculate Takt Time
    takt_time = DataManager.calculate_takt_time_from_demand(config)

    # Load and process data to calculate cycle times from change log csv
    file_path = config.get('csvFolderPath') + config.get('csvFileName')
    change_log="yes"
    df = DataManager.read_csv(file_path, config.get('release'), config.get('excluded_from_status'), config.get('excluded_issue_types'),
                              config.get('wip_categories_included'), config.get('epic_to_exclude'),change_log)

    cycle_time_history = DataManager.calculate_cycle_times(df,config)
    
    # load and process data to calculate weekly throughput csv file without change logs
    file_path_regular = config.get('csvFolderPath')+config.get('csv_list_of_tickets')
    change_log="no"
    df_regular = DataManager.read_csv(file_path_regular, config.get('release'), "", config.get('excluded_issue_types'),
                              config.get('wip_categories_included'), config.get('epic_to_exclude'),change_log)
    weekly_throughput, throughput, completed_tickets_count = DataManager.calculate_avg_weekly_throughput(df_regular, config.get('rollingAvgWeeks'))

    # Plot throughput by week
    PlotManager.plot_throughput_by_week(
        weekly_counts=weekly_throughput,
        output_path=os.path.join(config.get('imagesPath'), 'throughput_by_week.png'),
        config=config
    )

    # Plot histogram of current cycle time
    PlotManager.plot_histogram_cycle_time(
        cycle_times=cycle_time_history,
        output_path=os.path.join(config.get('imagesPath'), 'histogram_cycle_time.png'),
        config=config
    )

    # Run Monte Carlo simulation
    if completed_tickets_count >= 10 and config.get('remainingTicketCount') != 0:
        weeks_to_complete = MonteCarloSimulator.run_simulation(
            weekly_throughput, 
            config.get('remainingTicketCount'), 
            takt_time,  # Pass the Takt Time to the simulation
            config.get('rollingAvgWeeks'),
            config
        )
        PlotManager.plot_cycle_time_distribution(weeks_to_complete, config.get('imagesPath') + 'weeksToComplete.png',
                                                 'Weeks', '# of Simulations', 'Monte Carlo Analysis', config.get('number_of_bins'), completed_tickets_count, "mc", config)

       # Generate and print forecast summary
        forecast_generator = ForecastGenerator(
            release=config.get('release'),
            wip_category_included=config.get('wip_categories_included'),
            exclude_from_status=config.get('excluded_from_status'),
            issue_types=config.get('excluded_issue_types'),
            completed_tickets=completed_tickets_count,
            median_cycle_time=np.median(cycle_time_history),
            std_dev=np.std(cycle_time_history),
            rolling_avg_completion_rate=throughput,
            confidence=config.get('confidenceLevels'),
            remaining_tickets=config.get('remainingTicketCount'),
            weeks_to_complete=weeks_to_complete,
            rolling_avg_weeks=config.get('rollingAvgWeeks')
        )

        print(forecast_generator.generate_summary())

        # Generate and display forecast table
        forecast_table = forecast_generator.generate_table()
        print("\nForecast Table:")
        print(forecast_table.to_string(index=False),"\n")


        # Calculate tickets per week required to meet deadline
        #end_date = input('Enter the target end date (YYYY-MM-DD): ')
        end_date = config.get('required_completion_date')
        remaining_tickets = config.get('remainingTicketCount')
        if end_date is None or end_date == "":
            print(f"To calculate the required throughput, please update the config file with desired delivery date")
        else:
            tickets_per_week_needed = DataManager.calculate_tickets_per_week_to_meet_deadline(remaining_tickets, end_date)
            # Correctly calculate the required takt time
            required_takt_time = 36.25 / tickets_per_week_needed  # Use the correct formula here

            print(f"To complete the remaining {remaining_tickets} tickets by {end_date}, the team needs to complete {tickets_per_week_needed:.2f} tickets per week.")
            print(f"Required Takt Time: {required_takt_time:.2f} hours per ticket ")

    else:
        print('Not enough completed tickets for simulation or all tickets are done.')

if __name__ == '__main__':
    main()