# Project Continue — Real-Use Dashboard Acceptance

**Purpose:** verify the deployed Streamlit dashboard through its real browser UI. Repository unit/integration tests and Streamlit AppTest startup checks do not replace this acceptance.

**Safety boundary:** use the already-running dashboard. Do not reboot its runtime, stop/restart its process, change its database path, or run destructive maintenance. Do not use Colab as part of this acceptance. Use a clearly named temporary acceptance project and tasks; do not modify existing user projects or tasks.

## Before starting

Record:
- Dashboard URL and environment name (do not paste passwords, cookies, signing keys or tokens).
- Exact deployed Git SHA, if the operator can see it.
- Date/time and browser/device.
- Whether the dashboard is production-authenticated or development/test mode.

If the deployed SHA is not known, record **unknown**; do not infer it from the GitHub default branch.

## Real browser workflows

Use a unique project name such as `ACCEPTANCE-YYYYMMDD-HHMM`. Use synthetic task content only.

| ID | Browser action | Expected observable result |
|---|---|---|
| LIVE-001 | Open the existing dashboard URL | Dashboard renders; no uncaught error or blank page |
| LIVE-002 | Sign in with an authorized test/operator account; sign out and sign in again | Correct authenticated state; unauthorized login is rejected safely |
| LIVE-003 | Register a uniquely named acceptance project; search for it; open details; edit its description | Project appears in registry/search and edited value remains visible after rerun |
| LIVE-004 | Create two synthetic tasks; set assignee, due date and priority; edit status and title | Updated values and project progress are visible |
| LIVE-005 | Add a dependency from task B to task A; attempt to complete B first | B remains incomplete and a clear blocked explanation appears |
| LIVE-006 | Complete A, then B; remove dependency if desired | Both completion actions succeed in order; progress updates |
| LIVE-007 | Save a harmless project-memory note; create a checkpoint; preview recovery | Memory and checkpoint appear; preview verifies integrity and does not mutate tasks |
| LIVE-008 | Refresh the browser tab and reopen the same project | Project, tasks, memory and checkpoint remain visible |
| LIVE-009 | Exercise empty search and one invalid input; inspect GitHub/AI/automation panels where configured | Safe empty/error feedback; no secrets or stack traces displayed |
| LIVE-010 | In a separate isolated copy only, run backup verification and restore drill | Backup verifies; restored copy passes SQLite integrity and expected record checks |

## Authorization matrix

Only perform this with approved synthetic accounts and two test projects. Never change real user memberships as an experiment.

| Identity | Project A | Project B |
|---|---|---|
| Admin | Full administrative access | Full administrative access |
| Owner A | Manage | No access unless separately granted |
| Editor A | Read/write task and allowed memory operations | No access |
| Viewer A | Read-only; write actions denied | No access |
| Non-member | No project data or mutation access | No project data or mutation access |

Capture both allowed and denied outcomes. A hidden button alone is not proof: verify the server-side action is denied.

## Evidence format

For each ID record:
- ID and exact action performed.
- Expected result and actual visible result.
- PASS / FAIL / BLOCKED.
- Screenshot with secrets and personal data redacted.
- Exact deployed SHA if known.
- Error text, if any; redact credentials and session material.

Never record passwords, access tokens, cookies, session signing keys, private user data or database contents in screenshots.

## Boundaries and sign-off

- Browser refresh tests persistence without interrupting the running service.
- A process/container restart test is a separate maintenance operation. Do not perform it without explicit operator approval and a verified backup.
- Backup/restore tests must use an isolated copy/volume, never the live user database.
- HTTPS, firewall, durable-volume, host scheduler, off-site encrypted backup and monitoring checks require access to the selected production host.
- Do not mark any item PASS from source inspection, CI, or a screenshot of a different environment.

Final acceptance is **PASS** only when all applicable LIVE checks and the authorization matrix have actual evidence. Mark unavailable host-dependent checks **BLOCKED**, not PASS.
