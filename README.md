# pub-Jira-Monte_Carlo
This is a public repo to export jira tickets using Atlassian API and run monte carlo simulation to predict delivery dates <br /><br />

Step 1:<br />
Update your Jira credentials<br />
Edit the "secrets.json" file in the creds folder <br />
Enter user name<br />
Enter password (or the API token from Atlassian)<br />
<br /><br />
Step 2:<br />
Update the configuration file<br />
-- Project: Name of your Jira Project (usually the project Key)<br />
-- FolderPath: this is the location where you intend to store your python files<br />
-- csvFileName: choose a file name you want for your jira ticket CHANGE LOGS<br />
-- csv_list_of_tickets: choose a file name for your jira tickets WITHOUT change logs<br />
-- folderForCreds: update the path where you stored the Jira access credentials<br />
-- credFile: name of the json file that has the creds<br />
-- csvFolderPath: enter path where you want to csv files to be written<br />
-- imagesPath: enter path where you want the statistics graphs stored<br />
-- release: If you use Fix/Version field in Jira to track releases, update this field as a string otherwise leave it blank
-- epic_to_exclude: If you want to exclude any Epics from the analysis update the Epic Names as a list othrewise leave blank if you want to include all Epics<br />
-- excluded_issue_types: Update this list if you want to exclude any ticket types from the analysis. The default is "Epic", "Study (Spike)", "Test", "Sub-tasks"<br />
-- not_started_contributing_states: there's likely going to be queues in your workflow that don't contribute to Cycle Time calculations. Default is "Backlog" and "To Do". Update this list to suite your unique workflow<br />
-- wip_categories_included: Don't update this as cycle times are calculated for both Done and WIP (aging) tickets<br />
-- excluded_from_status: Jira change logs include two statuses for each field changed: From and To. Tickets in the Backlog, To-Do and Done queues don't contribute to cycle time. Update this for your own unique workflow. For example, in your workflow, tickets in UAT might not count towards Cycle Time. <br />
-- fields_without_changelogs: DON't UPDATE THIS. This is used as label headings in your exported CSV<br />
-- remainingTicketCount: While you can edit this, it is updated dynamically once you pull data fro Jira<br />
-- finalTicketCount: this is also updated dynamically. 10% of your remaining tickets is added as additional buffer to account for unknown unknowns <br />
-- rollingAvgWeeks: By default, 8 week rolling average is used to calculate your weekly throughput. Increase or decrease this number to suite your unique situation<br />
-- confidenceLevels: By default the Monte Carlo analysis will compute the probability of achieving a certain date at 85% confidence levels. This works for most situations. Change this percentage if you need lower or higher confidence levels on your completion dates<br />