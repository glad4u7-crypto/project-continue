# PC-P16-S001 to PC-P16-S008 — Deployment & Final Delivery

**Repository:** `glad4u7-crypto/project-continue`  
**Branch:** `feature/phase-16-deployment-final-delivery`  
**Baseline SHA:** `68466e2eacae26535c115e3984d105a2c4fb14b9`

## PC-P16-S001 — Production Configuration

**Goal:** Establish a fail-closed, provider-aware production configuration contract.

**Known existing requirements**
- `APP_ENV=production`
- `LOG_LEVEL` must not be DEBUG
- `PROJECT_CONTINUE_DB` must be an absolute path on durable private storage
- `SESSION_SIGNING_KEY` must be at least 32 bytes and supplied by a secret manager
- GitHub/AI/bootstrap credentials are optional and secret-injected only if enabled
- No secrets or real database files in Git

**Required work**
1. Choose a deployment profile/provider.
2. Build a setting-to-secret-source matrix.
3. Add/verify production configuration tests with synthetic values.
4. Verify fail-closed behavior for weak/missing signing key, invalid DB path and unsafe log level.
5. Review Phase 14 admin-only authentication and incomplete page/service project authorization.

**Evidence:** sanitized configuration matrix, test output, exact SHA, secret scan, reviewer sign-off.

**Safety:** Never paste actual secret values. Do not publicly expose the application while any data-bearing service path lacks server-side authorization.

**Initial status:** IN PROGRESS — repository contract audited; deployment target unresolved.

---

## PC-P16-S002 — Deployment Preparation

**Goal:** Prepare a reproducible, reversible deployment package for the selected provider.

**Required work**
1. Confirm provider, service type, region and runtime version.
2. Define build/install/start commands and pinned dependency strategy.
3. Define persistent volume mount, DB path, permissions and single-writer model.
4. Define HTTPS/domain, ingress restrictions and health/readiness probe.
5. Define host secret injection, bootstrap admin process and rotation.
6. Define external backup scheduler, private backup destination, retention/encryption and alerts.
7. Define release artifact, environment separation, rollback and incident contacts.
8. Run build and configuration validation without touching the live Colab process.

**Acceptance:** clean reproducible build; provider configuration reviewed; no secrets committed; rollback and access boundary documented.

**Status:** BLOCKED until provider/deployment profile is selected.

---

## PC-P16-S003 — Deployment

**Goal:** Deploy an approved release to the selected production host.

**Required work**
1. Confirm public/private exposure decision and authorization acceptance.
2. Confirm operator approval, release SHA and backup of any pre-existing target data.
3. Deploy using the selected provider's supported workflow.
4. Inject secrets through host controls; never through source files or chat.
5. Configure durable storage and HTTPS.
6. Verify process startup and capture deployment identifier/log summary.
7. Confirm rollback path before opening access.

**Acceptance:** real host URL/service identifier, exact release SHA, HTTPS result, persistence evidence, secret configuration evidence (presence only), and operator confirmation.

**Safety:** This checkpoint does not authorize DNS cutover, public release, destructive migration or replacement of existing data by itself.

**Status:** NOT STARTED.

---

## PC-P16-S004 — Production Health Check

**Goal:** Verify the deployed service under its actual host conditions.

**Required work**
- HTTPS and certificate validation.
- Login required; unauthenticated and unauthorized access denied.
- Authorized admin can load dashboard.
- Database read/write works and survives an approved service restart.
- Durable volume survives redeploy/restart.
- Health/readiness and safe logs contain no secrets or private paths.
- Backup job runs and reports safe success/failure.
- Restore drill is proven separately on an isolated destination.
- Monitoring/alert delivery verified where configured.

**Acceptance:** timestamped sanitized results, host/release SHA, screenshots or logs without credentials, failure/rollback record.

**Status:** NOT STARTED.

---

## PC-P16-S005 — User Documentation

**Goal:** Explain normal user workflows and safe usage.

**Required work**
- Project and task lifecycle.
- Dependencies, priorities and status.
- AI suggestions and human approval boundaries.
- Automation schedules/retries and GitHub read-only integration.
- Memory/checkpoints and resume behavior.
- Login/access model and current limitations.
- Common errors and safe troubleshooting.

**Acceptance:** docs match the deployed release; fresh-user walkthrough completed; screenshots are current and contain no sensitive data.

**Status:** NOT STARTED.

---

## PC-P16-S006 — Installation Guide

**Goal:** Reproduce installation on a clean supported host.

**Required work**
- Supported Python/runtime and OS assumptions.
- Clone/release checkout, isolated environment and dependency installation.
- Configuration and secret provisioning.
- Persistent DB directory and permissions.
- Start/stop/update commands and health verification.
- Upgrade/rollback and uninstall guidance.
- Separate development/Colab instructions from production instructions.

**Acceptance:** clean-environment install walkthrough passes without relying on undocumented local state.

**Status:** NOT STARTED.

---

## PC-P16-S007 — Backup & Recovery Guide

**Goal:** Provide an operator-safe, tested backup and recovery procedure.

**Required work**
- Backup cadence and owner.
- Consistent SQLite backup procedure and integrity verification.
- Private/off-site destination, encryption, access controls and retention.
- Monitoring and backup failure response.
- Isolated restore drill and application-level record checks.
- RPO/RTO assumptions and incident escalation.
- Non-destructive rollback/cutover procedure.

**Acceptance:** isolated restore drill passes on selected host/storage; no restore over active DB; guide matches actual provider implementation.

**Status:** NOT STARTED.

---

## PC-P16-S008 — Final Project Sign-off

**Goal:** Produce a truthful release handoff.

**Required evidence**
- Exact release SHA and merged PR reference.
- Required GitHub Actions and post-merge CI PASS.
- Focused/full regression and security/dependency checks.
- Exact-host deployment and health acceptance.
- Authentication/authorization review.
- User, installation, backup and recovery docs.
- Verified isolated restore drill.
- Known limitations, operational owner, rollback plan and explicit operator approval.

**Sign-off outcomes:** PASS / CONDITIONAL PASS / BLOCKED. Never mark PASS when host evidence or required authorization controls are missing.

**Status:** NOT STARTED.

---

## Resume markers

- `PC-P16-S001-PRODUCTION-CONFIG-AUDIT`
- `PC-P16-S002-DEPLOYMENT-PREPARATION`
- `PC-P16-S003-LIVE-DEPLOYMENT`
- `PC-P16-S004-PRODUCTION-HEALTH`
- `PC-P16-S005-USER-DOCUMENTATION`
- `PC-P16-S006-INSTALLATION-GUIDE`
- `PC-P16-S007-BACKUP-RECOVERY`
- `PC-P16-S008-FINAL-SIGNOFF`

Resume only from the marker whose evidence is not yet accepted. Preserve the existing Colab runtime and running dashboard throughout.
