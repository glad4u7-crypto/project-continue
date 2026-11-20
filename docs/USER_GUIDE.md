# User Guide

## Run the dashboard

1. Install Python 3.11 or newer.
2. Clone this repository and open its folder.
3. Create and activate a virtual environment.
4. Install packages: pip install -r requirements.txt.
5. Start the app: streamlit run app.py.
6. Open the local address printed by Streamlit in your browser. The layout is designed to work on mobile browsers too.

## Project management

The dashboard now provides a persistent project workspace:

- Register projects with a required name and optional description.
- Search projects by name or description.
- Filter active, archived, or all projects.
- Open project details to review metadata, task counts, task status breakdown, progress, and recent activity.
- Edit project name and description.
- Archive and restore projects. Archiving is reversible; the dashboard does not expose permanent deletion.

The default SQLite file is .data/project_continue.sqlite3. Set PROJECT_CONTINUE_DB to use a different database path. Keep database files private and back them up according to your operating requirements.

Progress is calculated from persisted tasks: completed tasks divided by all project tasks. A project with no tasks displays 0%.

## Current boundaries

Task creation/editing, dependency-aware recommendations, GitHub operations, and deployment are separate capabilities and are not claimed as complete by the project-management workspace.

## Optional GitHub configuration

Copy .env.example to .env and set only the values needed by the current application. Keep .env private; it is excluded by .gitignore. Never share a real access token in chat, screenshots, or source code.
