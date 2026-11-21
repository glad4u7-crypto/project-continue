# Project Continue

Project Continue organizes projects, tasks and dependencies, recommends actionable work and verifies results with evidence.

## Verified project status

| Phase | Scope | Repository status |
|---|---|---|
| 01 | Foundation | PASS with documented evidence limitations |
| 02 | Environment Setup | 8/8 checkpoints PASS |
| 03 | Core Architecture | 8/8 checkpoints PASS |
| 04 | Database System | 8/8 implementation checkpoints; exact-SHA Colab runtime acceptance PASS |
| 05 | Project Management | 8/8 checkpoints PASS; Colab and dashboard acceptance recorded |
| 06 | Task Management | Implementation and isolated file-backed acceptance PASS in PR #27 CI; exact-current-SHA Colab and manual UI gates pending |
| 07 | Intelligent Task Engine | Implementation and eight capability checks PASS in PR #27 CI; exact-current-SHA Colab and manual UI gates pending |
| 08 | GitHub Integration | Read-only integration merged; live panel is user-triggered |
| 09 | Automated Testing | 8/8 checkpoints PASS; PR #27 CI: 167 tests passed, 96% statement coverage |
| 10 | Production Readiness & Security | 8/8 checkpoints PASS; not a production certification |

PR #27 merged at `5d0610d3f9118cbcb3fe621280f6fa8e8fa5e3f9`. Its GitHub Actions CI passed on Python 3.11.18: 167 tests passed, 96% statement coverage (821 statements; 34 uncovered). Post-merge main CI must be checked independently. Phase 06/07 exact-current-SHA Colab acceptance and the eight manual browser checks remain separate pending gates.

Phase 04 Colab verification was supplied against main SHA `50b001467e9b5d9692cb2490bce26efef497e0d2` using Python 3.13.18. Compile, database-marked, focused database, and full test commands completed successfully. The evidence was recorded by merged PR #26.

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

The GitHub panel is read-only. Public repositories can be inspected without a token; private repositories require a fine-grained token with read-only Contents and Metadata permissions. Configure `GITHUB_REPOSITORY` and optional `GITHUB_TOKEN` in an untracked `.env` file. The panel checks repository metadata, branches, recent commits, README and open pull requests.

## Documentation

- Durable handoff: `docs/PROJECT-CONTINUATION-CHECKPOINT.md`
- Streamlit UI acceptance checklist: `docs/STREAMLIT-UI-ACCEPTANCE.md`
- Development Guide: `docs/DEVELOPMENT.md`
- Core Architecture: `docs/CORE-ARCHITECTURE.md`
- User Guide: `docs/USER_GUIDE.md`
- Phase 04: `docs/PHASE-04-DATABASE-SYSTEM.md`
- Phase 05: `docs/PHASE-05-PROJECT-MANAGEMENT.md`
- Phase 06: `docs/PHASE-06-TASK-MANAGEMENT.md`
- Phase 07: `docs/PHASE-07-INTELLIGENT-TASK-ENGINE.md`
- Phase 08: `docs/PHASE-08-GITHUB-INTEGRATION.md`
- Phase 09: `docs/PHASE-09-AUTOMATED-TESTING.md`
- Phase 10: `docs/PHASE-10-PRODUCTION-READINESS-SECURITY.md`
- Database Operations: `docs/DATABASE-OPERATIONS.md`
