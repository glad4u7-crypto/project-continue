# Project Continue

Project Continue organizes projects, tasks and dependencies, recommends actionable work and verifies results with evidence.

## Verified project status

| Phase | Scope | Repository status |
|---|---|---|
| 01 | Foundation | PASS with documented evidence limitations |
| 02 | Environment Setup | 8/8 checkpoints PASS |
| 03 | Core Architecture | 8/8 checkpoints PASS |
| 04 | Database System | 8/8 implementation checkpoints; documented exact-SHA Colab acceptance PASS |
| 05 | Project Management | 8/8 checkpoints PASS |
| 06 | Task Management | Implementation and isolated CI acceptance PASS; Colab/manual UI gates pending |
| 07 | Intelligent Task Engine | Implementation and capability CI PASS; Colab/manual UI gates pending |
| 08 | GitHub Integration | Read-only integration merged |
| 09 | Automated Testing | 8/8 checkpoints PASS; Phase 12 regression reached 191 tests |
| 10 | Production Readiness & Security | 8/8 checkpoints PASS; not a production certification |
| 11 | AI Brain | Merged; safe provider/advisory architecture and explicit approval gate |
| 12 | Automation Engine | Merged; schedules, bounded retries, notifications and automated checks |
| 13 | Memory & Checkpoint Engine | Implementation on feature branch; CI and merge gates pending |

## Technology

Python 3.11+, Streamlit, SQLite, python-dotenv, Requests and Pytest.

## Quick start

1. Create and activate a Python virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and configure required values.
4. Run `streamlit run app.py`.
5. Run `python -m pytest -q`.

Never commit `.env`, tokens, passwords or private keys.

## Project structure

- `app.py` — Streamlit entry point
- `config.py` — validated application settings
- `core/` — errors, logging and validation
- `database/` — SQLite connection, schema and repository
- `integrations/` — external API clients
- `services/` — project, task and integration use cases
- `ui/` — Streamlit presentation
- `scripts/` — isolated phase acceptance workflows
- `docs/` — architecture, user guide and phase evidence
- `tests/` — automated tests

## Project and task management

The dashboard supports project registration, search, lifecycle management, task creation/editing, free-text assignment, priority/status tracking, dependency management and dependency-aware completion. Assignees are labels, not authenticated users. Dependency cycles are rejected, and tasks cannot be completed while prerequisites remain unfinished.

## GitHub integration

The GitHub panel is read-only. Public repositories can be inspected without a token; private repositories require a fine-grained token with read-only Contents and Metadata permissions. Configure `GITHUB_REPOSITORY` and optional `GITHUB_TOKEN` in an untracked `.env` file.

## Phase 13 memory and recovery

The Memory & Checkpoint Engine adds project-scoped typed memory, SHA-256 verified snapshots, session history, decision records, Markdown handoffs, a strict resume command parser and preview-first additive task recovery. Recovery never overwrites existing project/task records. See `docs/PHASE-13-MEMORY-CHECKPOINT-ENGINE.md`.

## Documentation

- Durable handoff: `docs/PROJECT-CONTINUATION-CHECKPOINT.md`
- Streamlit UI acceptance: `docs/STREAMLIT-UI-ACCEPTANCE.md`
- Development Guide: `docs/DEVELOPMENT.md`
- Phase 11: `docs/PHASE-11-AI-BRAIN.md`
- Phase 12: `docs/PHASE-12-AUTOMATION-ENGINE.md`
- Phase 13: `docs/PHASE-13-MEMORY-CHECKPOINT-ENGINE.md`
- Phase 13 checkpoint evidence: `docs/checkpoints/PC-P13-S001-TO-S008-MEMORY-CHECKPOINT-ENGINE.md`
