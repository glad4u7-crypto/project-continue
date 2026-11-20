# Project Continue

Project Continue is a project-workflow assistant designed to organize multiple projects, track tasks and dependencies, recommend the next actionable task, and verify work with evidence.

## Current status

**Phase:** Phase 04 database foundation plus Phase 05 Project Management implementation in review.  
**Dashboard:** persistent project registration, registry search/filter, project details, metadata editing, archive/restore, progress summaries, and activity history are implemented on the Phase 05 feature branch.  
**Verification:** GitHub Actions passed 54 tests on Phase 05 commit c1be4b9baac91ecaf693d20ee2fadc80a9c64c73 (runs #86 and #87). Colab/browser runtime acceptance remains pending.

The repository is built in verifiable checkpoints. main is the authoritative branch; see docs/BRANCHING.md. Phase 05 implementation is currently proposed through PR #13, stacked on the Phase 04 working branch.

## Planned capabilities

1. Project and task registry
2. Task status, priority, and dependency tracking
3. Next-task recommendations with clear reasoning
4. GitHub integration for repository and change inspection
5. Verification using tests and other evidence (a commit alone does not mean a task is complete)
6. Human approval for sensitive or destructive actions
7. A mobile-friendly dashboard
8. Automated tests and user documentation

## Technology baseline

- Python 3.11+
- Streamlit dashboard
- SQLite persistence through Python's standard library
- python-dotenv for local environment configuration
- Requests for future API integrations
- Pytest for automated tests

## Quick start

1. Create and activate a Python virtual environment.
2. Install dependencies: pip install -r requirements.txt
3. Copy .env.example to .env and fill in only the values you need.
4. Run the dashboard: streamlit run app.py
5. Run the core bootstrap: python -m app

Never commit .env, access tokens, passwords, or private keys.

## Project structure

- app.py — Streamlit dashboard entry point
- app/ — application bootstrap and lifecycle
- core/ — errors, logging, and input validation
- database/ — SQLite connection, schema, and repository
- services/ — project-management use cases and read models
- ui/ — Streamlit project-management presentation
- integrations/ — future external integrations
- docs/ — architecture, user guide, phase and checkpoint evidence
- tests/ — automated unit and integration tests

## Project management dashboard

The dashboard supports project registration, case-insensitive search, active/all/archived filtering, details, metadata editing, reversible archive/restore, task-derived progress, and recent activity. The default SQLite file is .data/project_continue.sqlite3; PROJECT_CONTINUE_DB overrides the path. The .data directory is excluded from Git.

Progress is calculated as completed tasks divided by all tasks. Projects with no tasks show 0%. Permanent project deletion is intentionally not exposed in the dashboard.

## Safety principles

- No secrets in source code or Git history.
- Ask for approval before destructive or externally visible actions.
- Treat repository changes as unverified until relevant checks pass.
- Record what was checked and what evidence supports completion.

## Documentation

- Development Guide: docs/DEVELOPMENT.md
- Core Architecture: docs/CORE-ARCHITECTURE.md
- User Guide: docs/USER_GUIDE.md
- Branching Policy: docs/BRANCHING.md
- Phase 05 Project Management: docs/PHASE-05-PROJECT-MANAGEMENT.md
