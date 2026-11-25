# Phase 14 — Production Operations Checkpoint Register

Run checkpoints in order. A code change is not a PASS without the checkpoint's own evidence.

## PC-P14-S001 — Deployment Architecture & Operational Baseline

**Status: PARTIAL.** The current architecture and trust boundaries are documented in `docs/PHASE-14-DEPLOYMENT-ARCHITECTURE.md`. Provider selection, reviewer confirmation and exact-release acceptance remain open.

## PC-P14-S002 — Authentication & Authorization

**Implementation present:** `services/access_control.py` provides password hashing, HMAC-signed expiring sessions, live principal verification, roles and audit events. `ui/authentication.py` supplies a fail-closed production login gate. Production requires a high-entropy `SESSION_SIGNING_KEY` of at least 32 bytes.

**Mode selection:** Production is administrator-only by default. `AUTHORIZATION_ENFORCED=true` explicitly selects the signed-in project-member flow. Membership mode must not be enabled until the operator has provisioned the administrator, reviewed onboarding and completed acceptance.

**Acceptance still required:** exact-SHA CI, unauthenticated denial, invalid/disabled session denial, and role checks in browser workflows.

## PC-P14-S003 — Project/User Isolation

**Implementation present:** Owner/Editor/Viewer membership and deny-by-default project authorization are enforced in project, task, AI, automation and memory/checkpoint service paths. Resource scope is derived from canonical database records. AI approval decisions are requester- and project-bound. Global scheduler controls are administrator-only.

**Regression coverage present:** `tests/test_authorization.py` uses isolated SQLite and exercises role boundaries, forged principals, disabled accounts, task/project scope, memory/checkpoint recovery, AI approvals and automation controls.

**Follow-up:** `fix/phase16-auth-checkpoint-docs` adds selected-project binding to checkpoint lookup, recovery and resume, plus a regression test. CI is pending for this branch. The older PR #41 must not be merged wholesale because it is based on pre-authorization code.

**Acceptance still required:** exact-SHA CI and manual browser verification across at least two projects for Owner, Editor, Viewer and Non-member identities.

## PC-P14-S004 — Secrets & Data Protection

**Implementation present:** production configuration rejects unsafe settings; signing keys and integration credentials are expected from host secret controls; logs and health diagnostics must not disclose credentials or private database details.

**Status: PARTIAL.** Host secret manager, rotation, storage encryption and provider-specific data-at-rest controls are not configured or verified.

## PC-P14-S005 — Automated Backup & Retention

**Implementation present:** `services/backup_operations.py` provides consistent SQLite backup, integrity verification, retention preview and explicit-confirmation cleanup.

**Status: PARTIAL.** A host-managed always-on scheduler, private off-site destination, encryption, alerting and retention policy must be selected and verified.

## PC-P14-S006 — Restore Drill & Disaster Recovery

**Implementation present:** restore drills use managed verified backups, a new isolated destination and integrity checks; live/existing destinations are rejected.

**Status: PARTIAL.** Application-level verification and a restore drill on the selected production host remain pending. Never restore over the active database.

## PC-P14-S007 — Operational Observability

**Implementation present:** safe readiness diagnostics and append-only access-decision audit events.

**Status: PARTIAL.** Host monitoring, alert delivery, metrics and audit retention policy remain provider/operator responsibilities.

## PC-P14-S008 — Deployment Pipeline & Final Acceptance

**Status: BLOCKED ON HOST.** CI, exact-SHA acceptance, manual browser checks, provider-specific deployment and operator sign-off must be recorded separately. No live deployment is certified by repository tests.

## Safety requirements

- Use synthetic identities and isolated temporary databases for automated tests.
- Never place secrets, live database files or private user data in Git.
- Never claim HTTPS, persistent storage, backup scheduling, encryption or restore acceptance without host evidence.
- Do not publicly expose the application until exact-release authorization checks pass.
- Deployment, DNS cutover, destructive operations and production data migration require explicit operator approval.
