# Phase 16 — Deployment & Final Delivery

**Repository:** `glad4u7-crypto/project-continue`  
**Branch:** `feature/phase-16-deployment-final-delivery`  
**Baseline:** `68466e2eacae26535c115e3984d105a2c4fb14b9`  
**Status:** STARTED — production configuration audit recorded; live deployment is gated.

## Objective

Prepare and deliver Project Continue to a real, selected hosting environment with reproducible configuration, secure secrets, durable storage, operational health checks, complete user/operator documentation, and verified backup/recovery. CI success alone is not a deployment.

## Phase 16 checkpoint register

| Checkpoint | Scope | Acceptance evidence | Initial status |
|---|---|---|---|
| PC-P16-S001 | Production Configuration | Validated production env contract, secret inventory, persistent DB path, auth/security gate review, config tests | IN PROGRESS — existing config contract audited; host values/provider not selected |
| PC-P16-S002 | Deployment Preparation | Provider decision, runtime/build specification, dependency lock/reproducibility, health probe, storage/secrets/network plan, rollback plan | BLOCKED — provider and deployment profile not selected |
| PC-P16-S003 | Deployment | Operator-approved release deployed to selected host, HTTPS, persistent storage, secret injection, release SHA recorded | NOT STARTED — no live deployment authorized or configured |
| PC-P16-S004 | Production Health Check | Live URL checks, login/denial checks, DB read/write, backup status, logs, restart/persistence and alert evidence | NOT STARTED — requires S003 |
| PC-P16-S005 | User Documentation | User workflows, screenshots where appropriate, limitations, troubleshooting and support path | NOT STARTED |
| PC-P16-S006 | Installation Guide | Clean-machine install, environment setup, start/stop/update, verification and uninstall | NOT STARTED |
| PC-P16-S007 | Backup & Recovery Guide | Backup schedule, encryption/retention, off-site policy, isolated restore drill, RPO/RTO and rollback | NOT STARTED |
| PC-P16-S008 | Final Project Sign-off | Exact release SHA, CI + host evidence, security review, docs, recovery evidence, known limitations and operator approval | NOT STARTED |

## PC-P16-S001 — Production Configuration (initial audit)

Existing repository contract observed at the baseline:

- `APP_ENV=production` selects production authentication behavior.
- `LOG_LEVEL=DEBUG` is rejected in production.
- `PROJECT_CONTINUE_DB` must be an absolute path in production.
- `SESSION_SIGNING_KEY` must contain at least 32 bytes; it belongs in the host secret manager, never Git.
- `GITHUB_TOKEN`, AI credentials and bootstrap admin credentials must be injected as secrets only when required.
- `.env` and Streamlit secrets files are ignored by Git; `.env.example` contains placeholders only.
- SQLite requires a durable private local volume and a single-writer/coordinated access model; arbitrary network filesystems are not assumed.
- A host-managed scheduler is required for reliable backups; Colab disconnection is not an always-on scheduler.

### Critical pre-deployment security gate

Phase 14 documentation explicitly records that the production login gate is admin-only and project membership checks are not yet wired through every data-bearing page/service operation. Therefore:

**Do not expose this application publicly or enable multi-user production access until end-to-end server-side authorization is implemented and tested.** A private single-operator deployment is still subject to a reviewed access boundary and operator approval; it is not automatically safe merely because login exists.

### Outstanding configuration decisions

- Hosting provider and service type.
- Persistent volume path/semantics and backup destination.
- Domain and HTTPS termination.
- Identity model and initial admin provisioning.
- Host secret manager and rotation process.
- Always-on backup scheduler and alert destination.
- Whether AI integration is enabled and which provider is approved.

### S001 acceptance plan

1. Select the intended deployment profile and provider.
2. Map every required setting to a secret/non-secret source without revealing secret values.
3. Validate production settings using synthetic test values and isolated temporary paths.
4. Verify missing/weak secrets and relative DB paths fail closed.
5. Verify no secret, live DB, or runtime state is added to Git.
6. Review Phase 14 authorization gaps before approving public exposure.
7. Record exact SHA, focused tests, full regression, and reviewer decision.

**S001 current result:** PARTIAL / IN PROGRESS. The existing configuration contract is documented above; provider-specific values and full production authorization acceptance are outstanding.

## Global safety rules

- Never reboot the user's existing Colab runtime or stop/restart the running Streamlit dashboard as part of Phase 16.
- Colab is not the production host and must remain available for existing acceptance work.
- Never copy live database files, tokens, passwords, signing keys or personal data into Git or chat.
- Never run backup retention, restore or migration against the live Colab database.
- Use synthetic identities and isolated temporary databases for tests and restore drills.
- Never claim deployment, HTTPS, persistence, monitoring, backup scheduling or recovery until verified on the actual host.
- No public exposure before the authorization gate is closed.
- Deployment/cutover, DNS changes, public release and destructive operations require explicit operator approval.
- Keep work on this feature branch; no direct changes to `main`; do not merge without explicit approval.

## Phase execution protocol

Run checkpoints in order. Each checkpoint must include its own exact commands, expected output, evidence to capture, rollback/safety notes and a unique resume identifier. A checkpoint is PASS only when its own evidence is recorded. CI, Colab, browser and real-host acceptance are separate evidence classes.
