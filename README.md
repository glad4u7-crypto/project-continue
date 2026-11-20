# Project Continue

Project Continue organizes projects, tasks and dependencies, recommends actionable work and verifies results with evidence.

## Current status

**Phase 04:** database foundation merged into main.  
**Phase 05:** Project Management merged through PR #13; all eight Phase 05 checkpoints are accepted.  
**Phase 06:** Task Management merged into main through PR #14.  
**Phase 07:** Intelligent Task Engine runtime acceptance passed, including ranking, explainable priority, dependency analysis, actionable-task selection, blocked-task detection and dependency-aware completion verification.  
**Phase 08:** GitHub read-only integration merged; runtime configuration and dashboard connection check included.  
**Phase 09:** Automated testing merged into main through PR #20. CI passed after branch synchronization (112 tests; 96% statement coverage). Eight checkpoint records and test reports are documented in docs/PHASE-09-AUTOMATED-TESTING.md.  
**Phase 10:** Production readiness and security hardening merged into main through PR #21. All eight checkpoints PASS; Gitleaks, pip-audit and PR CI passed. Main-branch post-merge CI is tracked by run #270.

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
- config.py — validated application settings
- core/ — errors, logging and validation
- database/ — SQLite connection, schema and repository
- integrations/ — external API clients
- services/ — project, task and integration use cases
- ui/ — Streamlit presentation
- docs/ — architecture, user guide and phase evidence
- tests/ — automated tests

## Project and task management

The dashboard supports project registration, search, lifecycle management, task creation/editing, free-text assignment, priority/status tracking, dependency management and dependency-aware completion. Assignees are labels, not authenticated users. Dependency cycles are rejected, and tasks cannot be completed while prerequisites remain unfinished.

## GitHub integration

The GitHub panel is read-only. Public repositories can be inspected without a token; private repositories require a fine-grained token with read-only Contents and Metadata permissions. Configure GITHUB_REPOSITORY and optional GITHUB_TOKEN in an untracked .env file. The panel checks repository metadata, branches, recent commits, README and open pull requests.

## Documentation

- Development Guide: docs/DEVELOPMENT.md
- Core Architecture: docs/CORE-ARCHITECTURE.md
- User Guide: docs/USER_GUIDE.md
- Branching Policy: docs/BRANCHING.md
- Phase 05: docs/PHASE-05-PROJECT-MANAGEMENT.md
- Phase 06: docs/PHASE-06-TASK-MANAGEMENT.md
- Phase 08: docs/PHASE-08-GITHUB-INTEGRATION.md
- Phase 09: docs/PHASE-09-AUTOMATED-TESTING.md
- Phase 10: docs/PHASE-10-PRODUCTION-READINESS-SECURITY.md
- Database Operations: docs/DATABASE-OPERATIONS.md
