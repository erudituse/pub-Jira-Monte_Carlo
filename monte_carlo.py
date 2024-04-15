######### Author: Charan Atreya
####### 
# Purpose: The goal of this script is to run the Monte Carlo analysis and forecast release dates
#######

### Location of the config File
configPath = 'configs.json'

###### Do not edit below this line unless you know what you are doing ##### 

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import subprocess
import ast
import json
import matplotlib.pyplot as plt
import scipy.stats as stats
import sys
from collections import defaultdict
import os

# Step 1: read the config file
def read_config(configFile):
    with open(configFile, 'r') as file:
        config_data = json.load(file)
    return config_data

# Step 2: Read the CSV File and Filter tickets
def read_csv(file_path,releases, exclude_from_status, issue_types, wip_category_included,excluded_epics):
    #read the csv file
    try:
        df = pd.read_csv(file_path)
    except:
        print('The csv file containing historical jira tickets can\'t be found')
        sys.exit()

        # filter in only the releavant releases
    if (releases != ""):
        df['Release']=df['Release'].apply(ast.literal_eval)
        value_to_find = releases
        df = df[df['Release'].apply(lambda x: value_to_find in x)]
   
    
    filtered_df = df[df['WIP Category'].isin(wip_category_included) &
                    ~df['IssueType'].isin(issue_types) &
                    ~ df["From status"].isin(exclude_from_status) 
                    ]

    return filtered_df

# Step 3: Calculate Cycle times for the filtered data
def sum_cycle_times(df):
    # Ensure the time spent in each state is numeric
    df = df.copy()
    df['Time in From Status (days)'] = pd.to_numeric(df['Time in From Status (days)'], errors='coerce')

    cycle_times = [] # initialize an empty list to store cycle times

    # Group by ticket_id and sum the time_in_state for contributing states
    grouped = df.groupby('Jira Key')['Time in From Status (days)'].sum().reset_index()
    
    # create an array of cycle times for all tickets
    for _, row in grouped.iterrows():
        total_cycle_time = row['Time in From Status (days)']
        cycle_times.append(total_cycle_time)  # Correct usage of append on a list    

    return(np.array(cycle_times))

# Step 4: Calculate weekly throughput of completed tickets
def avg_weekly_throughput(df,weeksForRollAvg):
    # remove the WIP from completed data
    filtered_df= df[(df['WIP Category'] == 'Done')]

    # remove duplicate tickets since year week will contain the weekly 
    df_done_unique = filtered_df.drop_duplicates(subset=['Jira Key', 'Done Year', 'Done Week'])
    df_done_unique.to_csv('csv/debug-Unique_done_tickets.csv')
    # Count the number of tickets closed by week
    grouped = df_done_unique.groupby('Year Week')['Jira Key'].count().reset_index()
   
    # create a new column 'takt time". divide the count of tickets completed in a week by 5
    # ... to get tickets completed per day
    grouped['Takt Time'] = grouped['Jira Key']/5
    
    weekly_rolling_throughput_average = grouped['Jira Key'].tail(weeksForRollAvg).mean()

    return grouped, weekly_rolling_throughput_average, len(df_done_unique)

# Step 5: run the monte carlo simulation
def takt_time_simulations(weekly_takt_time_list, remaining_tickets, weeksForRollAvg, n_simulations = 1000):
    weeks_to_complete = np.zeros(n_simulations)
    
    # use the last configured weeks for rolling average 
    # logic is to use the most recent throughput data as it's the realistic expection of the team output
    historical_tickets_completed = np.array(weekly_takt_time_list['Jira Key'])[-weeksForRollAvg:]
    takt_times = np.array(weekly_takt_time_list['Takt Time'])[-weeksForRollAvg:]

    
    for i in range(n_simulations):
    # Randomly sample from historical data for each simulation
        sampled_takt_times = np.random.choice(takt_times, size=remaining_tickets, replace=True)
        
        # Adding up all the days in the sample
        total_time_required = sampled_takt_times.sum() 

        # Estimate weeks to complete by dividing total time by average weekly capacity        
        avg_weekly_capacity = np.mean(historical_tickets_completed) * np.mean(takt_times)
        weeks_to_complete[i] = total_time_required / avg_weekly_capacity

    return weeks_to_complete

# Step 6: Plot graphs
def plot_cycle_time_distribution(cycle_times_data, imagesPath,xlabel,ylabel,title):
    #plot histogram
    num_bins = 30
    n, bins, patches = plt.hist(cycle_times_data, num_bins, alpha=0.75, color='skyblue', edgecolor='black')

    historical_mean = np.mean(cycle_times_data)
    historical_median = np.median(cycle_times_data)
    historical_std_dev = np.std(cycle_times_data)
    historical_count = len(cycle_times_data)

    plt.axvline(historical_mean, color='blue', linestyle='dashed', linewidth=1, label=f'Mean: {historical_mean:.2f}')
    plt.axvline(historical_median, color='green', linestyle = 'dashed', linewidth=1,label=f'Median: {historical_median:.2f}')
    plt.axvline(historical_std_dev,color='grey', linewidth =0.1, label=f'Std. Dev. {historical_std_dev:.2f}')
    plt.axvline(historical_median + historical_std_dev, color='orange', linestyle='dashed', linewidth=1, label=f'Median + 1 Std Dev: {historical_median + historical_std_dev:.2f}')
    
    plt.legend()

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(str(datetime.today().strftime('%Y-%m-%d'))+'\n'+title)
    plt.savefig(imagesPath)
    plt.clf()
    
    return

def plot_line_graph(data,imagesPath, xlabel,ylabel,title):
    x = np.array(data['Year Week'])
    y = np.array(data['Jira Key'])

    # Rotates labels to 45 degrees and reduces font size
    plt.xticks(rotation=80, fontsize='small') 

    plt.plot(x, y, marker='o')
    
    # Adding title and labels
    # plt.legend()
    plt.title(str(datetime.today().strftime('%Y-%m-%d'))+'\n'+title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    
    plt.savefig(imagesPath)
    plt.clf()

    return
    
def box_plot(cycle_times_data,imagesPath):
     #boxplot
    plt.boxplot(cycle_times_data, vert=False)
    plt.title('Boxplot - Shows data outliers')
    plt.savefig(imagesPath)
    plt.clf()


######################################################################################
############### Main Program #####################
######################################################################################

# clear terminal screen
os.system('clear')


##########################################################################
########### User inputs to update the data from Jira #####################
##########################################################################
update= input('Update data from Jira (Y): ')
if (update == 'y' or update == 'Y'):
    subprocess.run(['python','export_tickets.py'])
subprocess.run(['python','jira_tickets_list.py'])

#read the config file
configData = read_config(configPath)
# get open tickets from the config file
openTickets = configData['configData'][0]['remainingTicketCount']

# get the folder path where all python files are stored
folderPath = configData['configData'][0]['folderPath']
# get the path of the folder where we need to export csv files
csvFolderPath = configData['configData'][0]['csvFolderPath']
# name of the file that exports tickets WITHOUT Change Log
jiraIssuesPythonPath = configData['configData'][0]['exportJiraListFile']
# name of the release to filter data on
release = configData['configData'][0]['release']

# not currently used - but future vision is to enable forecasting based on project start date
useCurrentDate = configData['configData'][0]['useCurrentDate']

growthInTickets = configData['configData'][0]['finalTicketCount']
projectedTickets = openTickets+growthInTickets
imagesPath = configData['configData'][0]['imagesPath']
rollingAvgWeeks = configData['configData'][0]['rollingAvgWeeks']
confidence = configData['configData'][0]['confidenceLevels']
epic_to_exclude = configData['configData'][0]['epic_to_exclude']
# name of the file that will store jira tickets without change logs
no_change_jira_file = configData['configData'][0]['csv_list_of_tickets']

# full path including folder and file name of the python file that exports tickets WITHOUT Changelogs
get_jira_list_python = folderPath+jiraIssuesPythonPath
csvFileName = configData['configData'][0]['csvFileName']
file_path = csvFolderPath + csvFileName

# Define conditions that don't contribute to cycle time for Done & WIP tickets
exclude_from_status = configData['configData'][0]['excluded_from_status']
not_started_contributing_states = configData['configData'][0]['not_started_contributing_states']
issue_types = configData['configData'][0]['excluded_issue_types']
wip_category_included = configData['configData'][0]['wip_categories_included']

# read the jira change log csv file and filter out the unnecessary data
df = read_csv(file_path, release, exclude_from_status, issue_types,wip_category_included,epic_to_exclude)
df.to_csv(csvFolderPath+"debug_step1_filteredData.csv")

# calculate the cycle time of the completed and the aging for WIP tickets
cycle_time_history = sum_cycle_times(df)
np.savetxt(csvFolderPath+'debug_step2_CycleTimeHistory.csv',cycle_time_history, delimiter=',', fmt='%f')


# get the list of weekly throughput of completed tickets and rolling average
weekly_throughput, throughput, completed_tickets_count = avg_weekly_throughput(df,rollingAvgWeeks)
weekly_throughput.to_csv(csvFolderPath+"debug_step3_throughputData.csv")

if completed_tickets_count >= 10:
    # plot the distribution of actual cycle times
    xlabel = 'Ticket completion in Days'
    ylabel = 'Frequency'
    graphTitle = 'Distribution of Cycle Time for Done and Aging for WIP tickets'
    plot_cycle_time_distribution(cycle_time_history,imagesPath+'history_distribution.png',xlabel, ylabel,graphTitle)

    # plot actual weekly completion ticket count as a line graph (only Done tickets used)
    xlabel = 'Year Week'
    ylabel = 'Count of tickets'
    graphTitle = 'Weekly ticket completion rate'
    plot_line_graph(weekly_throughput,imagesPath+'weeklyThroughput.png',xlabel,ylabel,graphTitle)

    # run Monte carlo on the takt time
    if openTickets != 0:
        weeks_to_complete = takt_time_simulations(weekly_throughput, projectedTickets, rollingAvgWeeks, n_simulations = 10000)
        np.savetxt('csv/debug-WeeksToComplete.csv',weeks_to_complete, delimiter=',', fmt='%f')
        xlabel = 'Weeks'
        ylabel = '# of Simulations'
        graphTitle = 'Distribution of the simulated completion times (weeks)'
        plot_cycle_time_distribution(weeks_to_complete,imagesPath+'weeksToComplete.png',xlabel, ylabel, graphTitle)

        outer_bound_days_to_complete = np.percentile(weeks_to_complete,confidence) * 5
        inner_bound_days_to_complete = np.percentile(weeks_to_complete,5) * 5
        # print(f"{inner_bound_days_to_complete} and {timedelta(inner_bound_days_to_complete)} and {outer_bound_days_to_complete}")
        outer_bound_date = datetime.today()+timedelta(days=outer_bound_days_to_complete)
        inner_bound_date = datetime.today()+timedelta(days=inner_bound_days_to_complete)

        if release == "":
            release = "'Completed tickets in all releases'"
        
        print(f"\nThe following emperical data for the Release: {release} is used to forecast release dates: \n"
              f"- {wip_category_included} are included\n"
              f"- Time spent in {exclude_from_status} queues are NOT included\n"
              f"- {issue_types} ticket types are NOT included\n"
              f"- {completed_tickets_count} tickets have been completed so far\n "
              f"-- with a median cycle time of {np.median(cycle_time_history)} working days per ticket and "
              f"standard deviation of {np.std(cycle_time_history):.2f} working days \n "
              f"-- between min {np.min(cycle_time_history)} day/s and max {np.max(cycle_time_history)} day/s \n "
              f"-- with a rolling {rollingAvgWeeks} week average completion "
              f"rate of {throughput:.2f} tickets/week \n\n"
              f"Forecast: There's a {confidence}% chance that the remaining {openTickets} (+10% additional tickets to account for unknown unknowns) tickets "
              f"is expected to be delivered between "
              f"{inner_bound_date.strftime('%d %B, %Y')} and {outer_bound_date.strftime('%d %B, %Y')}\n\n")
    else:
        print(f'Congratulations! Looks like all tickets for the release is done.')
else:
    print(f'There\'s not enough completed tickets to run a Monte Carlo simulation. Complete at least 10 tickets. ')
