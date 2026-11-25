# Phase 14 — Deployment Architecture & Operational Baseline

**Checkpoint:** PC-P14-S001  
**Current baseline:** `main` at `20bc8759bbf22effb02a56abfd10c9fdcb3d52d9`  
**Authorization implementation:** `18d5b4320163cd17bbb01f9b610887ed4d3d9fdc`  
**Refreshed:** 2026-11-25  
**Status:** IMPLEMENTATION INVENTORY UPDATED; provider and host acceptance remain open.

## 1. Current architecture

| Area | Current implementation | Remaining operational work |
|---|---|---|
| Web application | Streamlit `app.py`; project/task, AI, automation, memory/checkpoint and GitHub panels | Browser acceptance on the selected release |
| Authentication | HMAC-signed expiring sessions; live account verification | Host secret provisioning and onboarding |
| Authorization | Owner/Editor/Viewer membership, canonical project/resource scope, service-level enforcement | Exact-SHA CI and manual cross-project browser checks |
| Configuration | Immutable settings; production DB path and log-level validation; `AUTHORIZATION_ENFORCED` switch | Provider-specific values and secret mapping |
| Persistence | SQLite, foreign keys, short-lived connections, shared cached repository and atomic schema initialization | Durable private host volume and single-writer coordination |
| Backups | Online SQLite backup, integrity checks, preview-first retention and isolated restore primitives | Always-on scheduler, private off-site destination, encryption and host restore drill |
| Automation | Allow-listed schedules, bounded retries, project-scoped rules/notifications | Host scheduler and alert delivery |
| CI | Python 3.11, secret scan, dependency audit, compile, focused tests and full suite | Confirm current candidate branch workflow result |
| Runtime | Streamlit application; Colab is a development/acceptance environment | A separately selected always-on production host |

## 2. Trust boundaries

1. **Browser → Streamlit:** production defaults to an administrator-only signed-session gate. Setting `AUTHORIZATION_ENFORCED=true` explicitly enables signed-in project members. Feature services receive a verified request-scoped principal.
2. **Services → SQLite:** authorization resolves the resource's canonical project ID from database rows. Host-account access to the SQLite file remains a separate infrastructure trust boundary.
3. **AI approvals:** project access and requester ownership are checked before a decision is recorded; approval is not permission to execute an external/destructive action.
4. **Automation:** project rules and notifications are membership-scoped; global scheduler controls and unscoped notifications require an administrator.
5. **GitHub API:** read-only repository inspection; tokens remain host secrets and outside source control.
6. **Backups and storage:** application code verifies SQLite backups; confidentiality, off-site replication, retention and access controls depend on the selected host.

## 3. Authorization implementation

- `ui/authentication.py` verifies signed sessions and creates a request-scoped authorization context.
- `services/authorization.py` and `services/authorization_context.py` enforce read/write/manage decisions and resolve resource scope server-side.
- Project, task, AI, automation and memory/checkpoint services accept the verified context and enforce permissions at service boundaries.
- `tests/test_authorization.py` covers role boundaries, forged/disabled identities, project/task scope, memory/checkpoint recovery, AI approval ownership and admin-only automation controls.
- The review branch `fix/phase16-auth-checkpoint-docs` additionally binds checkpoint lookup/recovery/resume to the project selected in the UI.

See `docs/security/PROJECT-MEMBERSHIP-AUTHORIZATION.md` and `docs/SECURITY-AUTHORIZATION-WIRING-AUDIT.md`.

## 4. Remaining deployment decisions

- Hosting provider, service type and region.
- Persistent private volume semantics and database path.
- Domain, HTTPS termination and ingress restrictions.
- Secret manager, bootstrap administrator provisioning and rotation.
- Always-on backup scheduler, private backup destination, encryption, retention and alert destination.
- Operational owner, rollback procedure, RPO/RTO and incident contacts.

No provider, credentials or production host are assumed.

## 5. Acceptance boundaries

Repository implementation and isolated tests do not establish a secure live deployment. Release acceptance still requires exact-SHA GitHub Actions, manual browser checks across two projects and all roles, host HTTPS and durable-storage evidence, secret provisioning, scheduled backup evidence, an isolated host restore drill, and operator approval.

**Checkpoint result:** PARTIAL. The current authorization implementation is present in source; provider-specific and real-host acceptance remain pending. Do not publicly expose the application until the authorization and host gates are evidenced.
