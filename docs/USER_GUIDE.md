# User Guide

## Run the dashboard
1. Install Python 3.11 or newer.
2. Clone this repository and open its folder.
3. Create and activate a virtual environment.
4. Install packages with pip install -r requirements.txt.
5. Start the app with streamlit run app.py.
6. Open the local address printed by Streamlit. The layout supports mobile browsers.

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

Existing schema v1 databases are migrated to v2 automatically by adding a nullable assignee column without deleting tasks. The default SQLite file is .data/project_continue.sqlite3; PROJECT_CONTINUE_DB selects another path.

## Current boundaries
Free-text assignment is not authentication, account management, authorization, notifications or workload balancing. Those require a future identity subsystem. Dependency-aware next-task recommendations, GitHub operations and deployment are separate capabilities.

Keep .env private; it is excluded by .gitignore. Never share access tokens in chat, screenshots or source code.
