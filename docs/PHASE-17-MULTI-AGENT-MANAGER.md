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

The focused suite covers U01 registration and validation, U02 role lifecycle, U03 role/capability matching and balancing, U04 delivery/read receipts and cross-project rejection. CI success, post-merge main CI, browser acceptance and live-host deployment are separate gates.

## Current delivery boundary
Implementation on the feature branch is not a completed release until focused tests and full regression pass, the pull request is reviewed, and the user authorizes merge. Manual browser acceptance is still required before claiming the dashboard workflow has been accepted. No production deployment is included.
