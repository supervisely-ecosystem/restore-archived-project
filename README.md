<div align='center' markdown> <br>

# Restore archived project

<p align='center'>
  <a href='#overview'>Overview</a> •
  <a href='#how-to-run'>How to Run</a> •
  <a href='#results'>Results</a>
  <a href='#troubleshooting'>Results</a>
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

<img width="673" alt="resutls" src="https://github.com/supervisely-ecosystem/restore-archived-project/assets/57998637/ed74eace-08c0-4db5-accb-00e19b39123d">

1. The new project will be created in the same workspace with the name consist of:
   - `archived_project_id`
   - `archived_project_name`
2. The project will be available for download in Supervisely format as a `.tar` archive.

## Troubleshooting

The best way to solve problems is to follow the steps described below.

1. Check logs 
   
   1. Go to [Workspace Tasks](https://app.supervisely.com/tasks) and find the last task for "Restore archived project" app. The most recent task is always at the top of the list.
   2. If you have `Error` in the output column it also contains `Open log` (1) link. If no, click `⋮` (2) on the right and choose `Log`
      <div>
        <br>
        <img width="700" alt="Log" src="https://github.com/supervisely-ecosystem/restore-archived-project/assets/57998637/71232198-80be-484c-a1eb-ff34af72a5e9">
        <br>
      </div>

2. If you see errors in the log related to downloading or unpacking archives, some other unexplained errors, and they do not go away after several restore attempts, you can try to run "Restore archived project" using own agent. To do this, you will need to do the following.
   1. Read [the article](https://docs.supervisely.com/getting-started/connect-your-computer) on what an agent is and how to set it up on your computer
   2. Set up the agent on your computer
   3. Go to [Workspace Tasks](https://app.supervisely.com/tasks)
   4. Click `⋮` near the problem task, then `Run Again` and select your agent from the drop-down list "Agent" in the pop-up window. Run app.
      <div>
        <br>
        <img width="700" alt="Run Again" src="https://github.com/supervisely-ecosystem/restore-archived-project/assets/57998637/b75d1fc9-77d8-4e40-86b8-2ba296ca1337">
        <br>
      </div>

3. If the application on your agent is still unable to restore the project, please contact us and provide log file or `TASK ID`.