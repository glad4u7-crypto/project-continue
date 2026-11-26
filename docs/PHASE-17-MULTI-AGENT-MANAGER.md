# Phase 17 — Multi-Agent Manager

## Objective
Provide a project-scoped, persistent manager for registering agents, assigning roles, selecting capable agents and exchanging structured messages. This is a local coordination layer; it does not execute arbitrary tools, invoke external AI providers or grant agents user-account permissions.

## Unit acceptance matrix

| Unit | Scope | Implementation | Acceptance |
|---|---|---|---|
| U01 | Agent Registration | `services/multi_agent_manager.py`, `ui/multi_agent_manager.py` | Register, persist, retrieve, list, validate and disable agents |
| U02 | Agent Role Assignment | `pc_agent_roles` | Assign/remove allow-listed roles; multiple roles per agent |
| U03 | Agent Selection | `pc_agent_selections` | Select active role/capability match with least-used balancing and selection history |
| U04 | Agent-to-Agent Communication | `pc_agent_messages` | Project-local message queue, inbox/outbox, bounded JSON payload and read receipt |

## Allowed roles and message types
Roles: coordinator, planner, researcher, executor, reviewer, monitor.
Message types: task, request, response, status, handoff.

## Data and security boundaries
- Tables are additive and project-scoped; existing projects, tasks and SQLite data are not rewritten.
- Foreign keys cascade agent data only when its owning project is deleted.
- When an authorization context is supplied, reads require project read access and writes/selection/message acknowledgements require project write access.
- Agents are not application users and cannot authenticate, change project membership, approve AI actions or bypass the human approval gate.
- Messages are JSON objects limited to 16 KiB; sender and recipient must be distinct, active agents in the same project.
- Selection considers only active agents with the requested role and all required capabilities.
- No external API, paid provider, background worker, arbitrary tool execution or live deployment is introduced.

## Automated acceptance
Run against an isolated temporary SQLite database:
```bash
python -m compileall -q services/multi_agent_manager.py ui/multi_agent_manager.py tests/test_multi_agent_manager.py
python -m pytest -q tests/test_multi_agent_manager.py
python -m pytest -q
```

The focused suite covers U01 registration and validation, U02 role lifecycle, U03 role/capability matching and balancing, U04 delivery/read receipts and cross-project rejection. The merged PR #56 CI run passed the full regression, PostgreSQL 16 integration, Docker smoke test, security/dependency checks, and real Streamlit/Chromium browser acceptance. The merge to `main` is complete. Live-host deployment, durable production database storage, and live-host acceptance remain separate gates.

## Current delivery boundary
U01–U04 are merged to `main` through PR #56 (merge commit `d145fd85745002ca800b0e9506a9bff8c6818e4f`). Focused tests, full regression, PostgreSQL integration and automated real-browser acceptance passed in the recorded CI evidence. No live production deployment is included. Production completion still requires a selected host, durable database storage, configured secrets, backup/restore evidence and live-host acceptance. Streamlit Community Cloud local filesystem storage is not guaranteed to persist; do not use its local SQLite file as the authoritative production database.
