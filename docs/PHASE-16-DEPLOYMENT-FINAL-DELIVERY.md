# Phase 16 — Deployment & Final Delivery

**Repository:** `glad4u7-crypto/project-continue`  
**Canonical branch:** `main`  
**Release work branch:** `release/phase16-container-delivery`  
**Scope:** provider-neutral container packaging, production configuration, security acceptance, deployment and operations.

## Delivery register

| Checkpoint | Scope | Repository deliverable | Evidence boundary |
|---|---|---|---|
| PC-P16-S001 | Production Configuration | Validated `APP_ENV`, absolute persistent DB path, signing-key requirements, secret-safe config tests and production env template | CI config tests; host secret values remain operator-owned |
| PC-P16-S002 | Deployment Preparation | Dockerfile, Compose service, non-root UID, read-only root filesystem, persistent SQLite volume, health probe, loopback binding, container CI smoke test | Candidate CI proves image build/startup; host firewall/TLS/volume semantics remain host checks |
| PC-P16-S003 | Deployment | Reproducible self-hosted Docker deployment instructions | Requires an actual host, domain, TLS proxy, secret store and operator-approved rollout |
| PC-P16-S004 | Production Health | Streamlit health endpoint, container healthcheck and safe operational health service | Live URL, login, persistence, monitoring and host backup require the selected host |
| PC-P16-S005 | User Documentation | `docs/USER-GUIDE.md` | Repository documentation delivered; real user walkthrough remains a host/browser acceptance |
| PC-P16-S006 | Installation Guide | Python and Docker installation, configuration, upgrade and rollback instructions | Clean-host execution is a host acceptance |
| PC-P16-S007 | Backup & Recovery | Verified SQLite backup runner, preview-first retention, isolated restore helper and operator guide | Host scheduler, off-host copy, encryption and restore drill require host configuration |
| PC-P16-S008 | Final Sign-off | Durable release record, exact SHA, CI and known-limitations register | Requires deployed SHA, host evidence, recovery evidence and operator approval |

## PC-P16-S001 — Production configuration

The repository enforces:
- `APP_ENV=production` for production authentication behavior.
- `LOG_LEVEL` cannot be DEBUG in production.
- `PROJECT_CONTINUE_DB` must be an absolute path in production.
- `SESSION_SIGNING_KEY` must contain at least 32 bytes and must be stored outside Git and image layers.
- Bootstrap admin variables are used only when the identity table is empty; remove them after first account creation.
- `.env`, `.env.production` and Streamlit secrets are ignored by Git. `.env.production.example` contains placeholders only.

The container image does not bake in secrets. Docker Compose reads the host's ignored `.env.production` file. Production defaults to administrator-only access; membership mode is explicitly opt-in after users and project memberships are provisioned.

## PC-P16-S002 — Container deployment package

Delivered assets:
- `Dockerfile`: Python 3.11 slim, non-root UID/GID 10001, healthcheck and Streamlit entrypoint.
- `.dockerignore`: excludes Git history, local databases, virtualenvs, test output and secret files.
- `docker-compose.yml`: read-only root filesystem, bounded temporary filesystem, dropped Linux capabilities, no-new-privileges, persistent named SQLite volume and loopback-only port binding.
- `.env.production.example`: safe placeholder template.
- `docs/CONTAINER-DEPLOYMENT.md`: build, first admin bootstrap, HTTPS reverse proxy, backup, upgrade and rollback instructions.
- `.github/workflows/ci.yml`: image build and synthetic-credential container health smoke test.

The application remains on SQLite. The optional PostgreSQL adapter is not selected by the container deployment. The SQLite volume is single-instance and must reside on durable local storage.

## PC-P16-S003 / S004 — Host rollout and health

The repository now provides a repeatable Docker deployment package. A real rollout still requires:
1. A selected always-on Linux host with Docker Engine and Compose v2.
2. An operator-controlled domain and trusted HTTPS reverse proxy.
3. Host-managed signing key and bootstrap administrator secrets.
4. A durable private local Docker volume and independent backup destination.
5. Firewall rules that expose only the HTTPS proxy, not port 8501.
6. A real health/login check, persistent-volume test, backup execution and isolated restore drill.

No provider, domain, credentials or host has been supplied/selected in this repository task. Do not fabricate a live deployment or health result.

## PC-P16-S005 to S007 — Documentation and recovery

- User workflows and troubleshooting: `docs/USER-GUIDE.md`.
- Python and container installation: `docs/INSTALLATION-GUIDE.md` and `docs/CONTAINER-DEPLOYMENT.md`.
- Backup, retention and isolated restore: `docs/BACKUP-AND-RECOVERY-GUIDE.md`.
- Operations and security: `docs/PHASE-14-OPERATIONS-RUNBOOK.md` and `docs/SECURITY-AUTHORIZATION-WIRING-AUDIT.md`.

The repository's backup helper is scheduler-callable but does not install a scheduler or provision off-host encrypted storage. A Docker named volume is persistence, not a backup.

## Security release gate

Signed-principal verification and project membership enforcement are implemented in project, task, AI, automation and memory/checkpoint service paths. PR #45 additionally binds checkpoint lookup/recovery/resume to the selected project and clears stale session state when project or principal changes. Production defaults to administrator-only. Set `AUTHORIZATION_ENFORCED=true` only after accounts, owners and memberships have been provisioned and the two-project Owner/Editor/Viewer/Non-member browser matrix passes.

Do not publicly expose the app until exact-release CI, browser authorization checks, HTTPS, durable storage, host secret handling and restore controls have been verified.

## Safety rules

- This deployment package is for a separate production host; it is not a Colab deployment.
- Do not reboot the user's existing Colab runtime or stop/restart an existing dashboard.
- Never copy live databases, credentials, signing keys or personal data into Git or chat.
- Never run retention, restore or migration against the user's live Colab database.
- Do not use `docker compose down -v`; it deletes the persistent named volume.
- Use synthetic identities and temporary volumes for CI.
- DNS changes, public release, production cutover and destructive recovery require explicit operator approval.

## Release acceptance record

The release PR must record:
- exact candidate SHA and all required CI workflow conclusions;
- Docker image build and container health smoke test;
- security scan and dependency audit;
- exact merge SHA;
- actual host, image digest, HTTPS, persistent-volume and login results;
- backup timestamp, off-host destination and restore-drill evidence;
- operator approval and rollback reference.

A successful GitHub Actions run proves repository and CI-container behavior only. It does not substitute for the selected host's acceptance evidence.
