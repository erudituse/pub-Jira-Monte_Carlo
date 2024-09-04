######### Author: Charan Atreya
####### 
# Purpose: The pupose of this script is to export tickets from Jira. Two files are created
# 1. Change logs (needed to calculate cycle time & cycle time distributions)
# 2. List of tickets without change logs  (needed to calculate throughput)
#######

########################################################################################################
#####  inputs needed for the script  ###################################################
#########################################################################################################

### provide path for configs file
configPath = 'configs.json'

import json
import requests
from requests.auth import HTTPBasicAuth
import csv
import datetime
import urllib.request
import math
import io
import json

########################################################################################################
#####  function to get list of fields used in a Jira install  ##########################################
########################################################################################################

def get_fields():
    response = requests.get(f'{jira_url}/rest/api/3/field', auth=auth)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve fields")
        return []
    

########################################################################################################
#####  function to open config files  ###################################################
########################################################################################################
def read_config(configFile):
    with open(configFile, 'r') as file:
        config_data = json.load(file)
    return config_data

########################################################################################################
#####  function to access API keys  ###################################################
########################################################################################################
def api_access(secretsFile):
    with open(secretsFile, 'r') as file:
        secret_data = json.load(file)
    return secret_data

########################################################################################################
#####  function to standardize the date time format  ###################################################
########################################################################################################
def fixDate(dateToBeFixed):
    ## function to format dates correctly and standardize them across the script
    dateToBeFixed = dateToBeFixed.replace("T",' ')
    dateToBeFixed = dateToBeFixed[:-5].strip()
    datetime_str = dateToBeFixed
    fixedDate = datetime.datetime.strptime(dateToBeFixed,'%Y-%m-%d %H:%M:%S.%f')
    return fixedDate

########################################################################################################
#####  function to determine the number of changes contained within each Jira ticket ###################
########################################################################################################
def calculateHistorySize(statusHistories, historyLength, issueKey, autho, headers, base_url,jira_ticket_api_query, jira_ticket_api_end_point):
    #revised logic to be implemented. 
    #1. need to receive ticket ID and length of the change history 
    #2. if length of status history is greater than 99, then we need to make another set of API calls to retrieve all change logs for the
    # calculate how many records within history contains updates to the status field
    sizeOfStatusRecords = []
    items_list = []
    stuffSize = 0
    if historyLength > 100:
        statusHistories = getIssueChangelogs(issueKey, historyLength, autho, headers, base_url, jira_ticket_api_end_point, jira_ticket_api_query)
        sort_order = "ascend"
    else:
        sort_order = "desend"

    
    stuffSize = len(statusHistories)

    for a in range(0,stuffSize,1):
        ## find out the number of items within each change ID
        items_count = len(statusHistories[a]["items"])
        for b in range(0,items_count,1):
            isStatus = statusHistories[a]["items"][b]["field"]
            if (isStatus == "status"):
                sizeOfStatusRecords.append(a)
    
    return sizeOfStatusRecords, statusHistories, sort_order

#################################################################################################################################
#####  function to make additional API calls to get ticket change logs if there are more than 100 change logs ###################
#################################################################################################################################
def getIssueChangelogs(issueKey, historyLength, autho, headers, base_url, jira_ticket_api_end_point, jira_ticket_api_query):

    issue_changelog_startat = 0
    # divide that by 100 to determine the # of calls to make along with starting position
    no_of_passes = math.ceil(historyLength/100)
    loop_counter = 0
    continue_loop= True
    issue_changeLogs = []

    while continue_loop:
        # create the Api call url
        api_end_point_to_call = base_url+jira_ticket_api_end_point+issueKey+jira_ticket_api_query+str(issue_changelog_startat)
        # print(api_end_point_to_call)
        # increment the loop counter
        loop_counter += 1
        issue_changelog_startat = issue_changelog_startat + 100

        # make the api calls and append to the dictionary
        response = requests.get(f"{api_end_point_to_call}", headers=headers, auth=autho)
        temp = response.json()
        issue_changeLogs.extend(temp["values"])

        # return the dictionary values to the calculateHistorySize function 

        if loop_counter > no_of_passes-1:
            continue_loop = False
    
    return (issue_changeLogs)


########################################################################################################
#####  function to determine how many transition changes are recorded within a change ID ###############
########################################################################################################
def determineStatuswithinItems(items):
    itemsLength = len(items)
    statusPosition = []
    counter = 0
    for b in range (0,itemsLength,1):
        isStatus = items[b]["field"]
        if isStatus == "status":
            statusPosition.append(b)
            counter = counter + 1
    return statusPosition, counter

########################################################################################################
#####  function to calculate age of work in progress tickets ###########################################
########################################################################################################
def calculateWIP(dateOfChange):
    ## function to calculate WIP if the status of the ticket is not done
    todayDate = datetime.datetime.now()
    wipAge = (todayDate - dateOfChange).total_seconds()
    wipAge = math.ceil(wipAge/86400)
    return wipAge


########################################################################################################
#####  Step 1a: NO CHANGE-LOGS - run_export_tickets calls this function to do the work of exporting only tickets ############
########################################################################################################
def export_tickets( data, destination, writeMode, csvHeaders):
    
    destinationFile = destination
    appendMode = writeMode
    myData = []


    totalRecords = len(data["issues"]) ## total actual Jira tickets exported in the API
    ## append headers to csv file
    if (appendMode == 'w'):
        # ensure the order in which jira tickets get appended is in the same order as listed in the csvHeading
        myData.extend(csvHeaders)
        
    for x in range(0,totalRecords,1):
    # for x in range(0,100,1):
        ## Initialize variables
        componentsList = []
        releaseList = []
        currentSprint = []
        done_year = 0
        done_week = 0
        done_year_week = 0
        
        ## for every ticket get info
        # statHistories = data["issues"][x]["changelog"]["histories"]             ## get all ticket history into a list
        # historyLength = len(data["issues"][x]["changelog"]["histories"])        ## calculate the lengh of the history list
        currentStatus = data["issues"][x]["fields"]["status"]["name"]           ## find out the current status of the Jira ticket
        issueType = data["issues"][x]["fields"]["issuetype"]["name"]            ## capture the issue type (epic, story, task, subtask)
        issueKey = data["issues"][x]["key"]                                     ## capture the issue key
        issueSummary = data["issues"][x]["fields"]["summary"]                   ## capture the issue summary
        dateCreated = data["issues"][x]["fields"]["created"]                    ## get the issue created date
        labels = data["issues"][x]["fields"]["labels"]                          ## capture the labels attached to the ticket
        doneDate = data["issues"][x]["fields"]["resolutiondate"]                ## find out the resolution date
        issueDescription = data["issues"][x]["fields"]["description"]           ## capture the issue description

        # Example usage
        # jira_description = '{"version": 1, "type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Links to Laws-1365"}]}]}'
        cleaned_description = strip_json(issueDescription)
        # print(cleaned_description)

        ## fix the format of the date to eastern time
        dateCreated = fixDate(dateCreated)
        created_year, created_week, _ = dateCreated.isocalendar()
        created_week = f"{created_week:02}"
        created_year_week = str(created_year)+'-'+str(created_week)
        
         ## fix the format of the resolution date
        if (doneDate != None):
            doneDate = fixDate(doneDate)                                        
            done_year, done_week, _ = doneDate.isocalendar()
            done_week = f"{done_week:02}"
             ## create a column and store the completed data as 2024_01 format
            done_year_week = str(done_year)+'-'+str(done_week)  

        #categorize the tickets at a higher level - Backlog, Prioritized, WIP, Cancelled
        if (currentStatus == 'Done'):
            wipCategory = 'Done'
        elif (currentStatus == 'Cancelled'):
            wipCategory = 'Cancelled'
        elif (currentStatus == 'Backlog'):
            wipCategory = 'Backlog'
        elif (currentStatus == "To Do"):
            wipCategory = "Prioritized"
        else:
            wipCategory = "WIP"
            
        # get Epic link for each ticket. 
        try:
            epicLink = data["issues"][x]["fields"]["parent"]["fields"]["summary"]                 ## find Epic link (Atlassian cloud changed epic link to parent)
        except AttributeError:
            epicLink = ""
        except KeyError:
            epicLink = ""

        
        ## find out how many releases are added to each Jira ticket
        releaseLength = len(data["issues"][x]["fields"]["fixVersions"])        
        for fixver in range(0,releaseLength,1):                                 ## get all release
            releaseList.append(data["issues"][x]["fields"]["fixVersions"][fixver]["name"])

        ## find out how many components are added to each Jira ticket
        componentLength = len(data["issues"][x]["fields"]["components"])        
        for comp in range(0,componentLength,1):                                 ## get all components
            componentsList.append(data["issues"][x]["fields"]["components"][comp]["name"])
        
        ## append to csv file
        ## print ("ChangeID=",changeID,"---",issueKey,"---",statusPositions,"From Status: ", fromStatus, "---To Status:",toStatus)    ## for troubleshooting
        myData.append([issueKey,issueSummary, issueType, currentStatus, dateCreated,releaseList,componentsList,
                       labels,currentSprint,doneDate,epicLink, cleaned_description, wipCategory, done_year, done_week, done_year_week,
                       created_year, created_week, created_year_week])

    ## open the CSV file
    csvFile = open(destinationFile, appendMode, encoding='utf-8', newline='')
    ## overwrite the data in the CSV file
    
    with csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(myData)

    return

#######################################################################################################
#####  Step 1: function to determine status transition of each ticket and record them in a csv file ############
########################################################################################################
def run_export_tickets():
    ### number of results for API calls your Jira install is configured to return
    maxResultsForAPICalls = 100
    # destination = destinationPath+csvFileName
    readConfigs = read_config(configPath)
    project = readConfigs['configData'][0]['project']
    destPath = readConfigs['configData'][0]['csvFolderPath']
    destFileName = readConfigs['configData'][0]['csv_list_of_tickets']
    project = readConfigs['configData'][0]['project']
    destination = destPath+destFileName
    csvFileHeading = readConfigs['configData'][0]['fields_without_changelogs']
    epics_to_exclude = readConfigs['configData'][0]['epic_to_exclude']
    release = readConfigs['configData'][0]['release']
    weeks_rolling_avg = readConfigs['configData'][0]['rollingAvgWeeks']
    confidence_level = readConfigs['configData'][0]['confidenceLevels']
    exclude_from_status = ['Backlog']
    # Define States that contribute to the "To Do" wait time
    not_started_contributing_states = readConfigs['configData'][0]['not_started_contributing_states']
    issue_types = readConfigs['configData'][0]['excluded_issue_types']
    wip_category_included = readConfigs['configData'][0]['wip_categories_included']

    path_for_secrets = readConfigs['configData'][0]['folderForCreds']
    fileName_for_secrets = readConfigs['configData'][0]['credsFile']

    ### create the URL of the REST API endpoint you want to access
    ### don't delete or modify the following two lines (unless Atlassian publishes a new end point/version)
    base_url = readConfigs['configData'][0]['base_url']
    project_api_endpoint = readConfigs['configData'][0]['api_end_point']
    jql = readConfigs['configData'][0]['jql_query']
    
    ### if you add additional fields remember to update the myData.append lines across all functions to ensure the fields gets exported
    # jql = "&fields=key,summary, created, issuetype, status, parent, labels, fixVersions,components,customfield_10007,resolutiondate,assignee&sorter/order=ASC&maxResults=1000&startAt="

    recordPullStartAt = 0
    passNumber = 0
    ticketsLoop = True                  ## set defatult value - used to loop through the API if total tickets > 1000
    writeMode = "w"                     ## default creation of csv file a new file using the flag "w"

    # Set up the headers & authorization with the API token
    headers = {
        "Content-Type": "application/json",
        }
    secrets_data = []
    secrets_data = api_access(path_for_secrets+fileName_for_secrets)
    api_user = secrets_data['creds'][0]["userName"]
    api_token = secrets_data["creds"][0]["apiKey"]
    autho = HTTPBasicAuth(api_user, api_token)

    ### the JIRA API end point is configured to return only 100 tickets. the while statement loops to return all tickets in increments of 100
    while ticketsLoop:
        ##create the dynamic API URL
        apiURL = base_url+project_api_endpoint+project+jql+str(recordPullStartAt)
        ## send the API request and receive the json response
        response = requests.get(f"{apiURL}", headers=headers, auth=autho)
        data = response.json()

        ## get project level information
        totalJiraTickets = data["total"]                        ## find the total # of Jira tickets
        ticketIDStartAt = data["startAt"]                       ## starting point of exporting Jira ticket within the API
        totalRecords = len(data["issues"])                      ## total actual Jira tickets exported in the API
        firstIssueKey = data["issues"][0]["key"]                ## determine the first issue id in the API's result
        lastIssuekey = data["issues"][totalRecords-1]["key"]    ## determine the last issue id in the API's result
        if totalRecords <= maxResultsForAPICalls:               ## needed for the last API call
            totalRecords = maxResultsForAPICalls
        
        numberOfPasses = math.ceil(totalJiraTickets/totalRecords)       ## determine how many times to call the API for each jira project
        if passNumber == 0:
            print("Total Jira tickets = ",totalJiraTickets, ".\n") 
            ## un-comment the two lines below if you need the json file
            ##with open(destinationPath+jsonFileName, 'w', encoding='utf-8') as f:
            ##    json.dump(data, f, ensure_ascii=False, indent=6)

        print (f"Pass {passNumber+1}  of {numberOfPasses}.")
        print(f"{totalRecords} tickets being exported starting at ticket {firstIssueKey} and last ticket {lastIssuekey}.")
    
    
        ## call the export to CSV function from the json

        export_tickets(data,destination,writeMode,csvFileHeading)

        ### check if all tickets have been exported. 
        if passNumber < numberOfPasses - 1:
            recordPullStartAt = recordPullStartAt + 100
            passNumber = passNumber+1
            writeMode = 'a'
        else:
            ### exit the loop if all the tickets have been exported
            ticketsLoop = False     

def export_change_logs( data, destination, writeMode,autho, headers, base_url,jira_ticket_api_query, jira_ticket_api_end_point):
    
    destinationFile = destination
    appendMode = writeMode
    myData = []

    bugCount = 0
    totalRecords = len(data["issues"]) ## total actual Jira tickets exported in the API
    ## append headers to csv file
    if (appendMode == 'w'):
        myData = [["Jira Key","Summary","IssueType","Current Status","Ticket Created On", "From status", "To status", "Date changed","Time in From Status (days)","Release","Components","Labels","Sprint","Date Completed","Epic Link","Age in the last WIP Status","Jira Change ID", "WIP Category","Done Year", "Done Week", "Done Year Week"]]
    
    # iterate through every ticket
    for x in range(0,totalRecords,1):
        ## Initialize variables
        historyLength = 0
        componentsList = []
        releaseList = []
        currentSprint = []
        listOfStatusRecords = []
        WIPageinCurrentStatus = 0
        done_year = 0
        done_week = 0
        year_week = 0
        
        ## for every ticket get info
        ## capture the issue key
        issueKey = data["issues"][x]["key"]
        ## capture the issue summary
        issueSummary = data["issues"][x]["fields"]["summary"]
        ## get all ticket history into a list
        statHistories = data["issues"][x]["changelog"]["histories"]
        ## calculate the lengh of the history list
        downloadedHistoryLength = len(data["issues"][x]["changelog"]["histories"])
        historyLength = data["issues"][x]["changelog"]["total"]
        ## find out the current status of the Jira ticket
        currentStatus = data["issues"][x]["fields"]["status"]["name"]
        ## capture the issue type (epic, story, task, subtask)
        issueType = data["issues"][x]["fields"]["issuetype"]["name"]
        ## get the issue created date
        dateCreated = data["issues"][x]["fields"]["created"]
        ## fix the format of the date to eastern time
        dateCreated = fixDate(dateCreated)
        ## find out the resolution date
        doneDate = data["issues"][x]["fields"]["resolutiondate"]
        if (currentStatus == 'Done' or currentStatus == "Ready for Prod" or currentStatus == "PROD Deployed" or currentStatus == "PROD On Hold"):
            wipCategory = 'Done'
        elif (currentStatus == 'Cancelled'):
            wipCategory = 'Cancelled'
        elif (currentStatus == 'Backlog' or currentStatus == "PO Review"):
            wipCategory = 'Backlog'
        elif (currentStatus == "To Do"):
            wipCategory = "Prioritized"
        else:
            wipCategory = "WIP"
        
        ## find Epic link (Atlassian cloud changed epic link to parent)
        try:
            epicLink = data["issues"][x]["fields"]["parent"]["fields"]["summary"]
        except AttributeError:
            epicLink = ""
        except KeyError:
            epicLink = ""

        ## fix the format of the resolution date
        if (doneDate != None):
            doneDate = fixDate(doneDate)                                        
            done_year, done_week, _ = doneDate.isocalendar()
            done_week = f"{done_week:02}"
            ## create a column and store the completed data as 2024-01 format
            year_week = str(done_year)+'-'+str(done_week)                                 

         ## capture the labels attached to the ticket
        labels = data["issues"][x]["fields"]["labels"]                         
        
        ## find out how many releases are added to each Jira ticket
        releaseLength = len(data["issues"][x]["fields"]["fixVersions"])
         ## get all releases
        for fixver in range(0,releaseLength,1):                                
            releaseList.append(data["issues"][x]["fields"]["fixVersions"][fixver]["name"])

        ## find out how many components are added to each Jira ticket
        componentLength = len(data["issues"][x]["fields"]["components"])
        ## get all components
        for comp in range(0,componentLength,1):                                 
            componentsList.append(data["issues"][x]["fields"]["components"][comp]["name"])
        

        ## from the history list, find out which ones contain Workflow transition status
        ## ticketChangeLog is the revised list of change histories for tickets with more than 100 change records
        status_history_exists = True
        listOfStatusRecords, ticketChangeLog, sort_order = calculateHistorySize(statHistories, historyLength, issueKey,autho, headers, base_url,jira_ticket_api_query, jira_ticket_api_end_point)
        ## get the length of the list that contain the transition status locations
        
        lengthOfRecord = len(listOfStatusRecords)
        if lengthOfRecord == 0:
            status_history_exists = False
            ## capture items in the backlog without any change history
            fromStatus = data["issues"][x]["fields"]["status"]["name"]
            WIPageinCurrentStatus = calculateWIP(dateCreated)
            changeID = 0
            ## print ("issue key when history length = 0", issueKey, " and x is ",x)    
            myData.append([issueKey,issueSummary, issueType, currentStatus, dateCreated,fromStatus,None,None,None,releaseList,componentsList,labels,currentSprint,None,epicLink,WIPageinCurrentStatus,changeID, wipCategory, done_year, done_week,year_week])

        while status_history_exists:
            # what is the sort order of the change log history
            # if there are less than 100 records in the change log, it's part of the original data pull ..
            # ...and the order when using that API is descending
            # otherwise the order is ascending when using the ISSUE end point
            if sort_order =="desend":
                for_loop_param_a = lengthOfRecord -1
                for_loop_param_b = -1
                for_loop_param_c = -1
            elif sort_order == "ascend":
                for_loop_param_a = 0
                for_loop_param_b = lengthOfRecord
                for_loop_param_c = 1
            
            # Now to find the indexes with the change records and calculate time in the From state
            ######################## Apr 22 Update ################################ 
            ##### update on the logic to calculate time in each state 
            # go through each change ID
            # if "z"" matches listOfStatusRecords value
            # for the first hit, subtract date - created date
            # store previous date somewhere
            # for subsequent hits subtract the created date - store previous date somewhere

            # iterate through the listOfStatusRecords - it contains the index of the status changes
            for z in range(for_loop_param_a,for_loop_param_b,for_loop_param_c):
                # starting position of the index counter
                value_of_index = listOfStatusRecords[z]

                changeID = ticketChangeLog[value_of_index]["id"]
                transitionDate = ticketChangeLog[value_of_index]["created"]
                transitionDate = fixDate(transitionDate)
                # find out how many items are within one change ID
                len_of_last_item = len(ticketChangeLog[value_of_index]["items"])
                
                # for the last status update record
                if (sort_order == "desend" and z == 0) or (sort_order == "ascend" and z == lengthOfRecord -1):
                    status_history_exists = False
                    fromStatus = ticketChangeLog[value_of_index]["items"][len_of_last_item-1]["fromString"]
                    toStatus = ticketChangeLog[value_of_index]["items"][len_of_last_item-1]["toString"]
                    if (currentStatus != "Done"):
                        WIPageinCurrentStatus = calculateWIP(transitionDate)
                else:
                    fromStatus = ticketChangeLog[value_of_index]["items"][len_of_last_item-1]["fromString"]
                    toStatus = ticketChangeLog[value_of_index]["items"][len_of_last_item-1]["toString"]

                # if this is the first change record, then time in status = transition date - date created
                if z == for_loop_param_a:
                    timeInStatus = transitionDate - dateCreated
                else:
                    # getting the transition date of the previous record depends on the order in which records are pulled
                    if sort_order == "desend":
                        previous_value_of_index = listOfStatusRecords[z+1]
                    elif sort_order == "ascend":
                        previous_value_of_index = listOfStatusRecords[z-1]
                    previous_transition_date = ticketChangeLog[previous_value_of_index]["created"]
                    previous_transition_date = fixDate(previous_transition_date)
                    timeInStatus = transitionDate - previous_transition_date
                # convert time to days
                timeInStatus = round(timeInStatus.total_seconds()/86400,2)
                if timeInStatus < 0.001:
                    timeInStatus = 0.25
                

                #append the row to the csv file
                myData.append([issueKey,issueSummary, issueType, currentStatus, dateCreated,fromStatus,toStatus,transitionDate,timeInStatus,releaseList,componentsList,labels,currentSprint,doneDate,epicLink,WIPageinCurrentStatus,changeID,wipCategory, done_year, done_week, year_week])
                


            ######################## Apr 22 Update ################################
            
    ## open the CSV file
    csvFile = open(destinationFile, appendMode, encoding='utf-8', newline='')
    ## overwrite the data in the CSV file
    with csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(myData)

    return


def run_export_changelogs():
    ### number of results for API calls your Jira install is configured to return
    maxResultsForAPICalls = 100
    # destination = destinationPath+csvFileName
    readConfigs = read_config(configPath)
    destPath = readConfigs['configData'][0]['csvFolderPath']
    destFileName = readConfigs['configData'][0]['csvFileName']
    project = readConfigs['configData'][0]['project']
    destination = destPath+destFileName

    path_for_secrets = readConfigs['configData'][0]['folderForCreds']
    fileName_for_secrets = readConfigs['configData'][0]['credsFile']

    ### get the api end point parameters if we need to make change log calls for issues whose change logs exceed 100 (max returned results)
    jira_ticket_api_end_point = readConfigs["configData"][0]["jql_issue_api_endpoint"]
    jira_ticket_api_query = readConfigs["configData"][0]["jql_issue_changelog_query"]

    ### create the URL of the REST API endpoint you want to access
    ### don't delete or modify the following two lines (unless Atlassian publishes a new end point/version)
    base_url = readConfigs['configData'][0]['base_url']
    project_api_endpoint = readConfigs['configData'][0]['api_end_point']
    jql_changelog_query = readConfigs['configData'][0]['jql_changelog_query']
    ### if you add additional fields remember to update the myData.append lines across all functions to ensure the fields gets exported
    # jql_changelog_query = "&fields=key,summary, created, issuetype, status, parent, labels, fixVersions,components,customfield_10007,resolutiondate&sorter/order=ASC&type=story&maxResults=1000&expand=changelog&startAt="

    recordPullStartAt = 0
    passNumber = 0
    ticketsLoop = True                  ## set defatult value - used to loop through the API if total tickets > 1000
    writeMode = "w"                     ## default creation of csv file a new file using the flag "w"

    ## check if the value of maxREsultsForAPICalls will result in too many API calls. Stop executing rest of the code
    if maxResultsForAPICalls<100:
        print("#####################################################################")
        print("The value of 'maxResultsForAPICalls' is less than 100. This will result in too many API calls to Atlassian. Please validate this number and update the code.")
        print("#####################################################################")
        ticketsLoop = False

    # Set up the headers & authorization with the API token
    headers = {
        "Content-Type": "application/json",
    }

    secrets_data = []
    secrets_data = api_access(path_for_secrets+fileName_for_secrets)
    api_user = secrets_data['creds'][0]["userName"]
    api_token = secrets_data["creds"][0]["apiKey"]
    autho = HTTPBasicAuth(api_user, api_token)

    ### the JIRA API end point is configured to return only 100 tickets. the while statement loops to return all tickets in increments of 100
    while ticketsLoop:
        ##create the dynamic API URL
        apiURL = base_url+project_api_endpoint+project+jql_changelog_query+str(recordPullStartAt)
    
        ## print (apiURL)
        ## send the API request and receive the json response
        response = requests.get(f"{apiURL}", headers=headers, auth=autho)
        data = response.json()

        ## get project level information
        totalJiraTickets = data["total"]                        ## find the total # of Jira tickets
        ticketIDStartAt = data["startAt"]                       ## starting point of exporting Jira ticket within the API
        totalRecords = len(data["issues"])                      ## total actual Jira tickets exported in the API
        firstIssueKey = data["issues"][0]["key"]                ## determine the first issue id in the API's result
        lastIssuekey = data["issues"][totalRecords-1]["key"]    ## determine the last issue id in the API's result
        if totalRecords <= maxResultsForAPICalls:               ## needed for the last API call
            totalRecords = maxResultsForAPICalls
        numberOfPasses = math.ceil(totalJiraTickets/totalRecords)       ## determine how many times to call the API for each jira project
        if passNumber == 0:
            print(f"Only tickets with ChangeLogs being downloaded = {totalJiraTickets}."
              " Actual tickets slated for the release may be higher. ") 
            ## un-comment the two lines below if you need the json file
            ##with open(destinationPath+jsonFileName, 'w', encoding='utf-8') as f:
            ##    json.dump(data, f, ensure_ascii=False, indent=6)

        print ("Pass ",passNumber+1, " of ",numberOfPasses)
        print("Changelogs in json = ",totalRecords, "starting at ticket ",firstIssueKey, "and last ticket ",lastIssuekey)
    
        ## call the export to CSV function form the json
        export_change_logs(data,destination,writeMode,autho, headers, base_url, jira_ticket_api_query, jira_ticket_api_end_point)

        ### check if all tickets have been exported. 
        if passNumber < numberOfPasses - 1:
            recordPullStartAt = recordPullStartAt + 100
            passNumber = passNumber+1
            writeMode = 'a'
        else:
            ### exit the loop if all the tickets have been exported
            ticketsLoop = False

    return

#######################################################################################################
#####  function to clean up json content from DESCRIPTION                                   ############
########################################################################################################

def extract_text_only(data):
    text_content = ""

    if isinstance(data, dict):
        if "text" in data:
            text_content += data["text"] + "\n"
        for key, value in data.items():
            if key != "text":
                text_content += extract_text_only(value)
    elif isinstance(data, list):
        for item in data:
            text_content += extract_text_only(item)

    return text_content

def strip_json(jira_description):
    """
    Strips JSON keys from a JIRA field description and retains text values.

    Parameters:
    jira_description (dict): The JIRA field description containing JSON tags.

    Returns:
    str: The cleaned description with JSON keys removed.
    """
    # Extract text values from the dictionary
    cleaned_description = extract_text_only(jira_description)

    return cleaned_description.strip()





####################################################################################################
####################################################################################################
#############       MAIN PROGRAM ###################################################################
####################################################################################################
####################################################################################################

print(f'Exporting all Jira tickets without Change Logs.........................')
run_export_tickets()
print(f'\nExporting all Change Logs .........................\n Might take a bit longer depending on history size for each ticket...')
run_export_changelogs()
