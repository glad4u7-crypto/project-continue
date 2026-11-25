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
| 13 | Memory & Checkpoint Engine | Merged; Colab acceptance evidence recorded; manual dashboard check pending |
| 14 | Production Deployment & Operations | Authentication, signed sessions, project membership enforcement, verified SQLite backup/restore and health diagnostics merged; real-host acceptance remains separate |
| 15 | Complete Integration | Merged to main; Colab acceptance: 170 focused test executions and 217 full-suite tests passed; manual browser/host gates pending |
| 16 | Deployment & Final Delivery | Project-scoped checkpoint isolation merged; provider-neutral Docker/Compose deployment package and CI container smoke test added; live-host, HTTPS, durable-volume and restore evidence remain host-specific |

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

## Database adapters

SQLite remains the default application database. An optional PostgreSQL adapter, explicit migration tooling, verified PostgreSQL backup/restore helpers, and PostgreSQL 16 integration workflow are now included. This does not switch the running application to PostgreSQL or migrate existing data; production backend selection requires separate compatibility and operator acceptance.

## Security and project membership

Production defaults to an administrator-only sign-in gate. To enable the signed-in Owner/Editor/Viewer membership workflow, explicitly set `AUTHORIZATION_ENFORCED=true` and configure a high-entropy `SESSION_SIGNING_KEY` (at least 32 bytes) through the host secret manager. Provision the initial administrator on a fresh database, then bootstrap ownership and grant memberships for existing projects. Do not expose the application publicly until exact-release CI, browser authorization checks, and host controls have been accepted. See `docs/security/PROJECT-MEMBERSHIP-AUTHORIZATION.md` and `docs/SECURITY-AUTHORIZATION-WIRING-AUDIT.md`.

## Phase 13 — Memory and recovery

The Memory & Checkpoint Engine adds project-scoped typed memory, SHA-256 verified snapshots, session history, decision records, Markdown handoffs, a strict resume command parser and preview-first additive task recovery. Recovery never overwrites existing project/task records. See `docs/PHASE-13-MEMORY-CHECKPOINT-ENGINE.md`.

## Phase 14 — Production operations

Phase 14 adds a fail-closed admin login gate for production, signed sessions, project membership authorization primitives, safe access audit events, verified SQLite backup orchestration, preview-first retention, isolated restore drills, health diagnostics and an external-host backup runner. It is not yet a multi-user production certification: project-scoped authorization wiring and host-specific HTTPS, persistent storage, secret management, scheduling and restore acceptance must be verified. See `docs/PHASE-14-PRODUCTION-DEPLOYMENT-OPERATIONS.md` and `docs/PHASE-14-OPERATIONS-RUNBOOK.md`.

## Phase 15 — Complete integration

The Phase 15 Colab acceptance run passed all six focused integration groups (170 passing test executions), the full repository suite (217 passed) and Python compile check. These are user-supplied Colab results on the recorded baseline SHA; PR CI, manual browser UI acceptance and Phase 14 host-specific production gates remain separate. See `docs/PHASE-15-COMPLETE-INTEGRATION.md` and `docs/checkpoints/PC-P15-S001-TO-S008-COMPLETE-INTEGRATION.md`.

## Documentation

- Durable handoff: `docs/PROJECT-CONTINUATION-CHECKPOINT.md`
- Streamlit UI acceptance: `docs/STREAMLIT-UI-ACCEPTANCE.md`
- Development Guide: `docs/DEVELOPMENT.md`
- Phase 11: `docs/PHASE-11-AI-BRAIN.md`
- Phase 12: `docs/PHASE-12-AUTOMATION-ENGINE.md`
- Phase 13: `docs/PHASE-13-MEMORY-CHECKPOINT-ENGINE.md`
- Phase 13 checkpoint evidence: `docs/checkpoints/PC-P13-S001-TO-S008-MEMORY-CHECKPOINT-ENGINE.md`
- Phase 14: `docs/PHASE-14-PRODUCTION-DEPLOYMENT-OPERATIONS.md`
- Phase 14 operations runbook: `docs/PHASE-14-OPERATIONS-RUNBOOK.md`
- Phase 14 checkpoint instructions: `docs/checkpoints/PC-P14-S001-TO-S008-PRODUCTION-OPERATIONS.md`
- Phase 15: `docs/PHASE-15-COMPLETE-INTEGRATION.md`
- Phase 15 checkpoint evidence: `docs/checkpoints/PC-P15-S001-TO-S008-COMPLETE-INTEGRATION.md`
- Phase 16 deployment & final delivery: `docs/PHASE-16-DEPLOYMENT-FINAL-DELIVERY.md`
- Phase 16 user guide: `docs/USER-GUIDE.md`
- Phase 16 installation guide: `docs/INSTALLATION-GUIDE.md`
- Phase 16 backup & recovery guide: `docs/BACKUP-AND-RECOVERY-GUIDE.md`
- Phase 16 checkpoint instructions: `docs/checkpoints/PC-P16-S001-TO-S008-DEPLOYMENT-FINAL-DELIVERY.md`
- Container deployment: `docs/CONTAINER-DEPLOYMENT.md`
- Authorization wiring audit / production release gate: `docs/SECURITY-AUTHORIZATION-WIRING-AUDIT.md`
