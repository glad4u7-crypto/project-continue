# User Guide

## Run the dashboard
1. Install Python 3.11 or newer.
2. Clone this repository and open its folder.
3. Create and activate a virtual environment.
4. Install packages with pip install -r requirements.txt.
5. Copy .env.example to .env and adjust configuration.
6. Start the app with streamlit run app.py.
7. Open the local address printed by Streamlit. The layout supports mobile browsers.

## Project management
- Register projects, search by name or description, and filter active, archived or all projects.
- Open details to review metadata, task counts, progress and recent activity.
- Edit project metadata; archive and restore projects reversibly.

## Task management
Open a project and use Task management to:
- Create tasks with title, description, optional assignee, priority and due date.
- Assign a free-text name or email. This label creates no account and grants no access.
- Set priority to low, medium, high or critical.
- Track status as todo, in progress, blocked or done.
- Search and filter tasks by status, priority, title, description or assignee.
- Edit task details and clear an assignment by saving an empty assignee.
- Add or remove same-project dependencies. Cycles are rejected.
- Complete a task only after all prerequisite tasks are done.
- Review task changes in project activity history.

## GitHub integration
The GitHub integration panel is read-only. Configure `GITHUB_REPOSITORY=owner/repository` in `.env`, then select **Test GitHub connection** in the dashboard. Public repositories work without a token. Private repositories need a fine-grained GitHub token with read-only Contents and Metadata access, stored as `GITHUB_TOKEN` in `.env`.

The panel verifies repository metadata, branches, recent commits, README availability and open pull requests. It does not push code, create pull requests, merge changes or modify GitHub data.

## Current boundaries
Free-text assignment is not authentication, account management, authorization, notifications or workload balancing. Those require a future identity subsystem. Dependency-aware next-task recommendations and deployment are separate capabilities.

Keep .env private; it is excluded by .gitignore. Never share access tokens in chat, screenshots or source code.
