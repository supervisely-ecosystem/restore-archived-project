<div align='center' markdown> <br>

# Restore archived project

<p align='center'>
  <a href='#overview'>Overview</a> •
  <a href='#how-to-run'>How to Run</a> •
  <a href='#results'>Results</a> •
  <a href='#troubleshooting'>Troubleshooting</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervisely.com/apps/supervisely-ecosystem/restore-archived-project)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervisely.com/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/restore-archived-project)
[![views](https://app.supervisely.com/img/badges/views/supervisely-ecosystem/restore-archived-project.png)](https://supervisely.com)
[![runs](https://app.supervisely.com/img/badges/runs/supervisely-ecosystem/restore-archived-project.png)](https://supervisely.com)

</div>

## Overview

📤 This **system application** allows every user to restore their archived projects.

   
## How to Run

🖱️ You only need to click the button "Restore Project" or "Download Project" inside the archived project in your workspace.

<img width="244" alt="buttons" src="https://github.com/supervisely-ecosystem/restore-archived-project/assets/57998637/9a97966e-0d81-4b1e-8bb1-444d90a1135b">


## Results

<img width="700" alt="resutls" src="https://github.com/supervisely-ecosystem/restore-archived-project/assets/57998637/327430ea-f99e-457e-9ff9-58537061162b">

1. The new project will be created in the same workspace with the name consist of:
    - `archived_project_id`
    - `archived_project_name`
2. The project will be available for download in Supervisely format as a `.tar` archive.


## Troubleshooting

The best way to solve problems is to follow the steps described below.

1. Check logs   
    - Go to [Workspace Tasks](https://app.supervisely.com/tasks) and find the last task for "Restore archived project" app. The most recent task is always at the top of the list.
    - If you have `Error` in the output column it also contains `Open log` (1) link. If no, click `⋮` (2) on the right and choose `Log`             
      ![Check logs](https://github.com/supervisely-ecosystem/restore-archived-project/assets/57998637/91ee330f-88df-44b2-adaa-4d2da1efc494)       
2. If errors related to downloading or unpacking archives, other unexplained errors appear in the log, and they are not resolved after several restoration attempts, you can try to run "Restore archived project" using your own agent. To do this, you need to perform the following steps.
    - Read [the article](https://docs.supervisely.com/getting-started/connect-your-computer) on what Supervisely Agent is and how to set it up on your computer
    - Set up the Agent on your computer
    - Go to [Workspace Tasks](https://app.supervisely.com/tasks)
    - Click the `⋮` button next to the problem task, then `Run Again`, and in the pop-up window, select your agent from the `Agent` drop-down list. `Run` the application
      ![Run on your agent](https://github.com/supervisely-ecosystem/restore-archived-project/assets/57998637/b75d1fc9-77d8-4e40-86b8-2ba296ca1337)
3. If the application on your agent is still unable to restore the project, please contact us and provide log file or `TASK ID`.