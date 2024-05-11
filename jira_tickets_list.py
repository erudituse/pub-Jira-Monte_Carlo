######### Author: Charan Atreya
####### 
# Purpose: The goal of this script is create the statitical plots of the tickets
#######

########################################################################################################
#####  inputs needed for the script  ###################################################
#########################################################################################################

### provide path for configs file
configPath = 'configs.json'

import json
import numpy as np
import pandas as pd
import ast
import matplotlib.pyplot as plt
import scipy.stats as stats
import sys
from collections import defaultdict
import os
from datetime import datetime
import math

########################################################################################################
#####  function to open config files  ###################################################
########################################################################################################
def read_config(configFile):
    with open(configFile, 'r') as file:
        config_data = json.load(file)
    return config_data

def read_csv_filter_data(csv_file_name,wip_category_included,issue_types,excluded_epics):
    try:
        # load the file into a dataframe
        df = pd.read_csv(csv_file_name)
    except:
        print(f'The {csv_file_name} file containing historical jira tickets can\'t be found')
        sys.exit()

    # filter out releases
    # if (release != ""):
    #    df['Release']=df['Release'].apply(ast.literal_eval)
    #    value_to_find = release
    #    df = df[df['Release'].apply(lambda x: value_to_find in x)]
    
    filtered_df = df[~df['IssueType'].isin(issue_types) &
                    ~df["Epic Link"].isin(excluded_epics)
                     ]
    
    return filtered_df


# sum of all open tickets
def sum_of_tickets(csv_file_name, releases, issue_types, excluded_epics,json_file, configurations):
    try:
        # load the file into a dataframe
        df = pd.read_csv(csv_file_name)
    except:
        print(f'The {csv_file_name} file containing historical jira tickets can\'t be found')
        sys.exit()
    
    if releases != "":
        df['Release']=df['Release'].apply(ast.literal_eval)
        value_to_find = release
        df = df[df['Release'].apply(lambda x: value_to_find in x)]

    filtered_df = df[((df['WIP Category'] == "Prioritized") | 
                     (df['WIP Category'] == "WIP") |
                     (df['WIP Category'] == "Backlog")) &
                     ~df['IssueType'].isin(issue_types) &
                     ~df["Epic Link"].isin(excluded_epics)
                     ]
    filtered_df.to_csv('csv/debug_sum_jira_tickets.csv')
    remaining_tickets = len(filtered_df)

    configurations['configData'][0]['remainingTicketCount'] = remaining_tickets
    print(f"Remaining tickets: {configurations['configData'][0]['remainingTicketCount']}")
    configurations['configData'][0]['finalTicketCount'] = int(math.ceil(remaining_tickets *.10))
    

    with open(json_file, 'w') as file:
        json.dump(configurations, file, indent=4)
    print(f'Configuration file updated with remaining tickets value.\n')
    return

# function to calculate and plot the graph
def mean_of_closed_tickets(source_file, release, issue_types, epics_to_exclude, configPath, readConfigs):
    try:
        # load the file into a dataframe
        df = pd.read_csv(source_file)
    except:
        print(f'The {source_file} file containing historical jira tickets can\'t be found')
        sys.exit()
    analysis_type = ''
    # filter out releases
    if (analysis_type != "all"):
        df['Release']=df['Release'].apply(ast.literal_eval)
        value_to_find = release
        df = df[df['Release'].apply(lambda x: value_to_find in x)]


    closed_tickets = df[(df['WIP Category'] == 'Done') &
                        (df['IssueType'] == 'DevOps Support')
                        ]
    
    grouped_tickets = closed_tickets.groupby(['Done Year Week'])['Jira Key'].count().reset_index()
    # print(grouped_tickets)
    group_mean = np.mean(grouped_tickets['Jira Key'])

    xlabel = 'Week number'
    ylabel = 'Count of closed tickets'
    title = 'Closed DevOps tickets by week'
    imagesPath = 'images/completed_devops_tickets.png'
    # print(f"Plotting graph - Completed DevOps Tickets (No Change Logs)")
    # plot_line_graph(grouped_tickets, group_mean, imagesPath, xlabel, ylabel, title)

    return

def plot_line_graph(data, group_mean, imagesPath, xlabel,ylabel,title):
    x = np.array(data['Done Year Week'])
    y = np.array(data['Jira Key'])

    # Rotates labels to 80 degrees and reduces font size
    plt.xticks(rotation=80, fontsize='small') 

        # Adding text
    #plt.text(x.min(), 3.8, f'Mean: {group_mean:.2f}/week', color='blue', fontsize = 10)
    
    plt.plot(x, y, marker='o')
    
    # Adding title and labels
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    
    plt.savefig(imagesPath)
    plt.clf()

    return

def plot_created_date_graph(df, release):
    ### get all tickets
    ### get count of tickets by year-week
    ### plot the created by year-week
    if release != "":
        # print(df)
        df['Release']=df['Release'].apply(ast.literal_eval)
        # print(df['Release'])
        value_to_find = release
        df = df[df['Release'].apply(lambda x: value_to_find in x)]
        # print(f"{df['Release']}")
    
    df = df[(df['WIP Category'] != "Cancelled")]

    # print(f'Summarizing data for plotting graph of created tickets')
    imagesPath = 'images/weekly_created_tickets.png'
    csvPath = 'csv/'

    df.to_csv(csvPath+'debug-created-tickets.csv')
    df = df.copy()

    df['Created Year Week'] = df['Created Year Week'].astype(str)
    df['Done Year Week'] = df['Done Year Week'].astype(str)

    df['Count'] = 1
    # Count of tickets created each week
    created_grouped = df.groupby('Created Year Week')['Count'].count().reset_index(name='Tickets Created')
    # print (created_grouped)

    # Count of tickets completed each week
    completed_grouped = df[df['Done Year Week'].notna()].groupby('Done Year Week')['Count'].count().reset_index(name='Tickets Completed')

    # Merge on the 'Creation Week Year' and 'Completed Year Week' after renaming for a uniform 'Week' column
    created_grouped.rename(columns={'Created Year Week': 'Week'}, inplace=True)
    completed_grouped.rename(columns={'Done Year Week': 'Week'}, inplace=True)
    completed_grouped = completed_grouped[completed_grouped['Week'] != '0']

    summary_df = pd.merge(created_grouped, completed_grouped, on='Week', how='outer').fillna(0)

    # Ensure the 'Week' column is sorted properly
    summary_df['Week'] = pd.to_datetime(summary_df['Week'] + '-1', format='%Y-%W-%w')
    summary_df.sort_values('Week', inplace=True)

    # Convert 'Week' back to the original format for display purposes
    summary_df['Week'] = summary_df['Week'].dt.strftime('%Y-%W')

    if (len(summary_df) != 0):
    # print(summary_df)

        summary_df.set_index('Week', inplace=True)
        summary_df.plot(kind='bar', figsize=(12, 6), width=0.8)

        plt.title(str(datetime.today().strftime('%Y-%m-%d'))+'\nTickets Created vs. Completed by Week')
        plt.xlabel('Week')
        plt.ylabel('Number of Tickets')
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
    
        plt.savefig(imagesPath)
        plt.clf()
    else:
        print(f'Not enough data to plot the "created date graph"')

    return



###############################################################################################################################
################## Main program ###############################################################################################
###############################################################################################################################

readConfigs = read_config(configPath)
destPath = readConfigs['configData'][0]['csvFolderPath']
destFileName = readConfigs['configData'][0]['csv_list_of_tickets']
project = readConfigs['configData'][0]['project']
destination = destPath+destFileName
csvFileHeading = readConfigs['configData'][0]['fields_without_changelogs']
epics_to_exclude = readConfigs['configData'][0]['epic_to_exclude']
release = readConfigs['configData'][0]['release']
weeks_rolling_avg = readConfigs['configData'][0]['rollingAvgWeeks']
confidence_level = readConfigs['configData'][0]['confidenceLevels']
exclude_from_status = readConfigs['configData'][0]['excluded_from_status']
# Define States that contribute to the "To Do" wait time
not_started_contributing_states = readConfigs['configData'][0]['not_started_contributing_states']
#not_started_contributing_states = ['To Do','Backlog']

# issue_types = ['Epic','Study','Test Case','Sub-task']
issue_types = readConfigs['configData'][0]['excluded_issue_types']
#wip_category_included = ['Done', 'WIP']
wip_category_included = readConfigs['configData'][0]['wip_categories_included']

df = read_csv_filter_data(destination,wip_category_included,issue_types,epics_to_exclude)
df.to_csv(destPath+'debug_all_jira_tickets.csv')

#determine the count of open tickets and update the configuration file with that number
sum_of_tickets(destination, release, issue_types, epics_to_exclude, configPath, readConfigs)

## calculate the mean of closed tickets
# mean_of_closed_tickets(destination, release, issue_types, epics_to_exclude, configPath, readConfigs)

## plot the graph of created tickets
plot_created_date_graph(df, release)
