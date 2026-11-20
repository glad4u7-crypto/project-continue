# Project Continue

Project Continue organizes projects, tasks and dependencies, recommends actionable work and verifies results with evidence.

## Current status
**Phase 04:** database foundation merged into main.
**Phase 05:** Project Management merged through PR #13.
**Phase 06:** Task Management implementation in progress on feature/phase-06-task-management. See docs/PHASE-06-TASK-MANAGEMENT.md.
**Latest verified main before Phase 06:** 71ad78131046d5f4ed03d43bd83aa7d962d61db5.

## Technology
Python 3.11+, Streamlit, SQLite, python-dotenv, Requests and Pytest.

## Quick start
1. Create and activate a Python virtual environment.
2. Install dependencies with pip install -r requirements.txt.
3. Copy .env.example to .env and configure required values.
4. Run streamlit run app.py.
5. Run python -m pytest -q.

Never commit .env, tokens, passwords or private keys.

## Project structure
- app.py — Streamlit entry point
- core/ — errors, logging and validation
- database/ — SQLite connection, schema and repository
- services/ — project and task management use cases
- ui/ — Streamlit presentation
- docs/ — architecture, user guide and phase evidence
- tests/ — automated tests

## Project and task management
The dashboard supports project registration, search, lifecycle management, task creation/editing, free-text assignment, priority/status tracking, dependency management and dependency-aware completion. Assignees are labels, not authenticated users. Dependency cycles are rejected, and tasks cannot be completed while prerequisites remain unfinished.

## Documentation
- Development Guide: docs/DEVELOPMENT.md
- Core Architecture: docs/CORE-ARCHITECTURE.md
- User Guide: docs/USER_GUIDE.md
- Branching Policy: docs/BRANCHING.md
- Phase 05: docs/PHASE-05-PROJECT-MANAGEMENT.md
- Phase 06: docs/PHASE-06-TASK-MANAGEMENT.md
