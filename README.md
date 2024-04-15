# pub-Jira-Monte_Carlo
This is a public repo to export jira tickets using Atlassian API and perform statistical analysis including Monte Carlo simulation to manage schedule and scope risks <br /><br />

<strong>Disclaimer</strong>
<p>
This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.
</p>
<p>
This software is developed independently, and the views and opinions expressed are those of the author only. The software is not endorsed by any other entity, unless explicitly stated.
</p>
<p>
Users are solely responsible for complying with applicable laws and must evaluate, and bear all risks associated with the use of this software, including any reliance on its functionality, accuracy, and completeness.
</p>
<p>
Contributions to this project are welcome, but they must be made under the same license terms and all contributors must agree to abide by these terms.
</p>
<p>
In future, the software may include contributions from third-party individuals or organizations. All rights and acknowledgments to those contributors are as specified within the project.
</p>
<h1>Steps to configure and use the scripts</h2>
<h2>Step 1:</h2><br />
Update your Jira credentials<br />
<ul>
<li>CAUTION: Ensure the creds folder and user credentials file doesn't get uploaded to Github. Update the .gitignore file</li>
<li>Edit the "secrets.json" file in the creds folder</li>
<li>Enter user name</li>
<li>Enter password (or the API token from Atlassian)</li>
</ul>
<br /><br />
<h2>Step 2:</h2><br />
Update the configuration file. "configs.json"<br />
<ul>
<li>The scripts assumes Atlassian Cloud offering. </li>
<ul>
<li>base_url: update the domain section of the URL for your Jira installation</li>
<li>api_end_point: update this to the API end point. Usually you'll only need to update values before the "?"</li>
<li>jql_query: this is the JQL query to export jira tickets WITHOUT change logs</li>
<li>jql_changelog_query: this is the JQL query to export jira tickets WITH change logs</li>
<li>project: Name of your Jira Project (usually the project Key)</li>
<li>Note: concatenate the base_url+api_end_point+project key+jql_query to test the link in a Browser or Postman.<p>
Note: Within the jql_query, custom fields might need to be added/edited for your install. Adding additional fields or editing existing fields to export, will need a change to the underlying code of export_tickets.py script. Feel free to edit the code as needed to your requirements.
</p>
</li>
</ul>
<li>folderPath: this is the location where you intend to store your python files</li>
<li>csvFileName: choose a file name you want for your jira ticket CHANGE LOGS</li>
<li>csv_list_of_tickets: choose a file name for your jira tickets WITHOUT change logs</li>
<li>folderForCreds: update the path where you stored the Jira access credentials</li>
<li>credFile: name of the json file that has the creds. NOTE: Protect your credentials and prevent them from syncing with Github</li>
<li>csvFolderPath: enter path where you want to csv files to be written</li>
<li>imagesPath: enter path where you want the statistics graphs stored</li>
<li>release: If you use Fix/Version field in Jira to track releases, update this field as a string otherwise leave it blank. The analysis is created to work for the entire jira project or just ONE release. You will get an error if you attempt to add multiple release values</li>
<li>epic_to_exclude: Leave this value blank if you want to include all Epics in the project, else enter the Epic Name as strings within this list</li>
<li>excluded_issue_types: Update this list if you want to exclude any ticket types from the analysis. The default is "Epic", "Study (Spike)", "Test", "Sub-tasks"</li>
<li>not_started_contributing_states: there's likely going to be queues in your workflow that don't contribute to Cycle Time calculations. Default is "Backlog" and "To Do". Update this list to suite your unique workflow</li>
<li>excluded_from_status: Jira change logs include two statuses for each field changed: From and To. Tickets in the Backlog, To-Do and Done queues don't contribute to cycle time. Update this for your own unique workflow. For example, in your workflow, tickets in UAT might not count towards Cycle Time. </li>
<li>remainingTicketCount: While you can edit this, it is updated dynamically once you pull data fro Jira</li>
<li>finalTicketCount: this is also updated dynamically. 10% of your remaining tickets is added as additional buffer to account for unknown unknowns </li>
<li>rollingAvgWeeks: By default, 8 week rolling average is used to calculate your weekly throughput. Increase or decrease this number to suite your unique situation</li>
<li>confidenceLevels: By default the Monte Carlo analysis will compute the probability of achieving a certain date at 85% confidence levels. This works for most situations. Change this percentage if you need lower or higher confidence levels on your completion dates</li>
</ul>
<br />
-- DO NOT UPDATE THE FOLLOWING LISTS <br />
--- change_logs_csv_header </br />
--- fields_without_changelogs<br />
--- wip_categories_included<br/><br />


<h2>Step 3:</h2><br />
<ul>
<li>Ensure "monte_carlo.py", "export_tickets.py",  and "jira_tickets_list.py" are in the same folder as the config file "configs.json"</li>
</ul>

<h2>Step 4:</h2><br />
<strong>Run the monte_carlo.py script</strong>

<h2>OUTPUT</h2><br />
<ul>
<li>There are two key csv files that will be created when the jira export script is run. These two files store the exported data from Jira needed to run the statistical analysis</li>
<ul>
<li>jira.csv (as defined in the config file)- this file contains the change logs</li>
<li>jira_tickets_list.csv (as defined in the config file)- this file contains all jira tickets WITHOUT change logs</li>
</ul>
<li>Within the csv folder, you'll also see a number of files starting with "debug_". <ul><li>They are not only helpful in validating the various data pieces needed for statistical analysis, but also useful in troubleshooting issues</li></ul>
<li>Four images will be created within the Images folder</li>
<ul>
<li>history_distribution.png: This graph will show the histogram of completed and aging tickets. You can also see the Mean (Average), Median, Standard Deviation stats of your data</li>
<li>weeklyThroughput.png: This line graph shows how the weekly throughput i.e. tickets completed per week</li>
<li>weeksToComplete.png: This is the result of the Monte Carlo analysis. The analysis runs 10,000 simulations, and plots the median completion of each of the remaining incomplete tickets. The verbose results calculated prediction dates, by default, at the 85th percentile (update config file to change the percentile that suits your needs)</li>
<li>weekly_created_tickets: This is a column graph that helps visualize tickets created weekly vs completed. While Jira has an out of the box report for this, you have greater control on the types of tickets to include/exclude</li>
</ul>
</ul>




