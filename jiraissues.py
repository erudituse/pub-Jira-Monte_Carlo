######### Author: Charan Atreya, 
### Initial Creation Date: Apr 2017
####### 
# Purpose: The goal of this file is to:
# 1. Export tickets Change Logs, and
# 2. Export tickets WITHOUT change logs
# Change logs are not accessible using out of the box Jira reports
#######

########################################################################################################
#####  inputs needed for the script  ###################################################
#########################################################################################################

### provide path for configs file
configPath = '/Users/charan/Documents/GitHub/delivery_forecasting/ignore/configs.json'
#########################################################################################################


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
def calculateHistorySize(statusHistories):
    # calculate how many records within history contains updates to the status field
    stuffSize = len(statusHistories)
    sizeOfStatusRecords = []
    for a in range(0,stuffSize,1):
        isStatus = statusHistories[a]["items"][0]["field"]
        if (isStatus == "status"):
            sizeOfStatusRecords.append(a)
    return sizeOfStatusRecords

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
#####  function to determine status transition of each ticket and record them in a csv file ############
########################################################################################################
def exportCSV( data, destination, writeMode ):
    
    destinationFile = destination
    appendMode = writeMode
    myData = []

    totalRecords = len(data["issues"]) ## total actual Jira tickets exported in the API
    ## append headers to csv file
    if (appendMode == 'w'):
        myData = [["Jira Key","Summary","IssueType","Current Status","Ticket Created On", "From status", "To status", "Date changed","Time in From Status (days)","Release","Components","Labels","Sprint","Date Completed","Epic Link","Age in the last WIP Status","Jira Change ID", "WIP Category","Done Year", "Done Week", "Year Week"]]
    
    for x in range(0,totalRecords,1):
        ## Initialize variables
        statusList = []
        componentsList = []
        releaseList = []
        currentSprint = []
        listOfStatusRecords = []
        WIPageinCurrentStatus = 0
        lastRecordValue = 0                                                     ### reset the last record value variable for every Jira ticket
        done_year = 0
        done_week = 0
        year_week = 0
        
        ## for every ticket get info
        statHistories = data["issues"][x]["changelog"]["histories"]             ## get all ticket history into a list
        historyLength = len(data["issues"][x]["changelog"]["histories"])        ## calculate the lengh of the history list
        currentStatus = data["issues"][x]["fields"]["status"]["name"]           ## find out the current status of the Jira ticket
        issueType = data["issues"][x]["fields"]["issuetype"]["name"]            ## capture the issue type (epic, story, task, subtask)
        issueKey = data["issues"][x]["key"]                                     ## capture the issue key
        issueSummary = data["issues"][x]["fields"]["summary"]                   ## capture the issue summary
        dateCreated = data["issues"][x]["fields"]["created"]                    ## get the issue created date
        dateCreated = fixDate(dateCreated)                                      ## fix the format of the date to eastern time
        doneDate = data["issues"][x]["fields"]["resolutiondate"]                ## find out the resolution date
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
            
        try:
            epicLink = data["issues"][x]["fields"]["parent"]["fields"]["summary"]                 ## find Epic link (Atlassian cloud changed epic link to parent)
        except AttributeError:
            epicLink = ""
        except KeyError:
            epicLink = ""

        
        if (doneDate != None):
            doneDate = fixDate(doneDate)                                        ## fix the format of the resolution date
            done_year, done_week, _ = doneDate.isocalendar()
            done_week = f"{done_week:02}"
            year_week = str(done_year)+'-'+str(done_week)                                 ## create a column and store the completed data as 2024_-01 format

        labels = data["issues"][x]["fields"]["labels"]                          ## capture the labels attached to the ticket
        

        releaseLength = len(data["issues"][x]["fields"]["fixVersions"])        ## find out how many components are added to each Jira ticket
        for fixver in range(0,releaseLength,1):                                 ## get all components
            releaseList.append(data["issues"][x]["fields"]["fixVersions"][fixver]["name"])

  
        componentLength = len(data["issues"][x]["fields"]["components"])        ## find out how many components are added to each Jira ticket
        for comp in range(0,componentLength,1):                                 ## get all components
            componentsList.append(data["issues"][x]["fields"]["components"][comp]["name"])
        

        listOfStatusRecords = calculateHistorySize(statHistories)               ## from the history list, find out which ones contain Workflow transition status
        lengthOfRecord = len(listOfStatusRecords)                               ## get the length of the list that contain the transition status locations

        if lengthOfRecord > 0:                                                  ## since indexes start at 0
            lastRecordValue = listOfStatusRecords[lengthOfRecord-1]             ## store the location of the last status record
        
        if (historyLength == 0):                                                ## capture items in the backlog without any change history
            fromStatus = data["issues"][x]["fields"]["status"]["name"]
            WIPageinCurrentStatus = calculateWIP(dateCreated)
            changeID = 0
            ## print ("issue key when history length = 0", issueKey, " and x is ",x)    
            myData.append([issueKey,issueSummary, issueType, currentStatus, dateCreated,fromStatus,None,None,None,releaseList,componentsList,labels,currentSprint,None,epicLink,WIPageinCurrentStatus,changeID, wipCategory, done_year, done_week,year_week])
        
        ## iterate through history of every Jira story - variable "z"; if changes in ascending order, increment the loop, else decrement the loop
        for z in range(historyLength-1,-1,-1):                                  
            ## initialize variables for every change record in the history
            WIPageinCurrentStatus = 0
            statusPositions = []
            locationOfStatus = 0
            lengthOfResolutionChangeID = 0
            
            ## find out how many changes are within a change ID and if there are more than one ...
            ## ... find out where within the change ID does the item = status reside in
            ## (hopefully there are no change records with multiple transition changes within the same changeID)
            lengthOfResolutionChangeID = len(data["issues"][x]["changelog"]["histories"][z]["items"])
            if lengthOfResolutionChangeID >= 1:
                statusPositions = determineStatuswithinItems(data["issues"][x]["changelog"]["histories"][z]["items"])
                statusExists = statusPositions[1]
                if statusExists == 0:
                    locationOfStatus = 0
                else:
                    locationOfStatus = statusPositions[0]
                    locationOfStatus = locationOfStatus[0]
            else:
                locationOfStatus = 0

            statusHist = data["issues"][x]["changelog"]["histories"][z]["items"][locationOfStatus]["field"]         ## get the list of the status change from the identified changeID
            changeID = data["issues"][x]["changelog"]["histories"][z]["id"]                                         ## log the Jira change ID for future troubleshooting and include it into the CSV
            
            if (statusHist == "status" or statusHist == "resolution"):                                               ## (legacy code) only grab the data for status change and discard the rest
                statusList.append(z)                                                                                ## determine which record in the change history releates to "Status" and remember it
                fromStatus = data["issues"][x]["changelog"]["histories"][z]["items"][locationOfStatus]["fromString"]     ## get the from Status

                if (fromStatus == None):
                    fromStatus = data["issues"][x]["changelog"]["histories"][z]["items"][0]["fromString"]               ## get the from status
                if (lengthOfResolutionChangeID > 1):
                    toStatus = data["issues"][x]["changelog"]["histories"][z]["items"][locationOfStatus]["toString"]    ## get the to status
                else:
                    toStatus = data["issues"][x]["changelog"]["histories"][z]["items"][locationOfStatus]["toString"]    ## get the to status

                statusChangeDate = data["issues"][x]["changelog"]["histories"][z]["created"]                            ## get the status change date
                statusChangeDate = fixDate(statusChangeDate)                                                            ## fix the format of the date

                ## calculate the time in status
                if (z==lastRecordValue):                        ## if change records are stored in asecending order, z==0
                    timeInStatus = statusChangeDate - dateCreated                                                       
                else:
                    ## to identify the precise location of the previous status record in the changelog history
                    listLength = len(statusList)-2
                    prevStatDate = data["issues"][x]["changelog"]["histories"][statusList[listLength]]["created"]
                    prevStatDate = fixDate(prevStatDate)
                    timeInStatus =  statusChangeDate - prevStatDate
                
                if (currentStatus != "Done"):
                    ## if a ticket is not closed, get the aging days in its current status    
                    changeDateOfLastStatus = data["issues"][x]["changelog"]["histories"][lastRecordValue]["created"]
                    changeDateOfLastStatus = fixDate(changeDateOfLastStatus)
                    WIPageinCurrentStatus = calculateWIP(changeDateOfLastStatus)
                    
                timeInStatus = math.ceil(timeInStatus.total_seconds()/86400)   # convert time to days
                if (timeInStatus < 0.0001):
                    timeInStatus = 0

                ## append to csv file
                ## print ("ChangeID=",changeID,"---",issueKey,"---",statusPositions,"From Status: ", fromStatus, "---To Status:",toStatus)    ## for troubleshooting
                myData.append([issueKey,issueSummary, issueType, currentStatus, dateCreated,fromStatus,toStatus,statusChangeDate,timeInStatus,releaseList,componentsList,labels,currentSprint,doneDate,epicLink,WIPageinCurrentStatus,changeID,wipCategory, done_year, done_week, year_week])

    ## open the CSV file
    csvFile = open(destinationFile, appendMode, encoding='utf-8', newline='')
    ## overwrite the data in the CSV file
    
    with csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(myData)

    return
        



###############################################################################################################################
################## Main program ###############################################################################################
###############################################################################################################################


### provide the name of the exported json file if you also want the json in addition to the csv
jsonFileName = "data.json"
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


#########################################################################
### do not change anything below unless you understand what you are doing
#########################################################################

### create the URL of the REST API endpoint you want to access
### don't delete or modify the following two lines (unless Atlassian publishes a new end point/version)
base_url = "https://ontariodigital.atlassian.net"  
project_api_endpoint = "/rest/api/3/search?jql=project+%3D+"
### if you add additional fields remember to update the myData.append lines across all functions to ensure the fields gets exported
jql = "&fields=key,summary, created, issuetype, status, parent, labels, fixVersions,components,customfield_10007,resolutiondate&sorter/order=ASC&type=story&maxResults=1000&expand=changelog&startAt="

recordPullStartAt = 0
passNumber = 0
ticketsLoop = True                  ## set defatult value - used to loop through the API if total tickets > 1000
writeMode = "w"                     ## default creation of csv file a new file using the flag "w"

### check if the value of maxREsultsForAPICalls will result in too many API calls. Stop executing rest of the code
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
    apiURL = base_url+project_api_endpoint+project+jql+str(recordPullStartAt)
    
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
        print(f"Total Jira tickets with ChangeLogs being downloaded = {totalJiraTickets}."
              " Actual total Jira tickets slated for the release may be higher. ") 
        ## un-comment the two lines below if you need the json file
        ##with open(destinationPath+jsonFileName, 'w', encoding='utf-8') as f:
        ##    json.dump(data, f, ensure_ascii=False, indent=6)

    print ("Pass ",passNumber+1, " of ",numberOfPasses)
    print("Tickets in json = ",totalRecords, "starting at ticket ",firstIssueKey, "and last ticket ",lastIssuekey)
    
    
    ## call the export to CSV function form the json
    exportCSV(data,destination,writeMode)

    ### check if all tickets have been exported. 
    if passNumber < numberOfPasses - 1:
        recordPullStartAt = recordPullStartAt + 100
        passNumber = passNumber+1
        writeMode = 'a'
    else:
        ticketsLoop = False                             ### exit the loop if all the tickets have been exported

  


#myData = [["Jira Key","Summary","IssueType","Current Status","Ticket Created On", "From status", "To status", "Date changed","Time in From Status (days)","Release","Components","Labels","Sprint","Date Completed","Epic Link","Age in the last WIP Status","Jira Change ID"]]    
#myData.append([issueKey,issueSummary, issueType, currentStatus, dateCreated,fromStatus,None (toStatus),   None(date change),       None (time in from status),ReleaseList,componentsList,labels,None,None,None,WIPageinCurrentStatus,changeID])
#myData.append([issueKey,issueSummary, issueType, currentStatus, dateCreated,fromStatus,toStatus,statusChangeDate,timeInStatus,releaseName,componentsList,labels,None,doneDate,None,WIPageinCurrentStatus,changeID])
