# Phase 14 — Deployment Architecture & Operational Baseline

**Checkpoint:** PC-P14-S001  
**Audit baseline:** main `308c30a77af0e2dfecddcf4526051eca48421b18`  
**Audit date:** 2026-11-21  
**Status:** IN PROGRESS — repository inspection recorded; review and acceptance checks remain.

## 1. Observed architecture

| Area | Current implementation | Operational implication |
|---|---|---|
| Web application | Streamlit entry point `app.py`; project, AI, automation, memory/checkpoint and GitHub panels | Browser UI is not an identity boundary |
| Configuration | Immutable `Settings`; APP_ENV, LOG_LEVEL, GITHUB_REPOSITORY, token-presence flag and DB path | Production requires absolute DB path and disallows DEBUG; no provider-specific deployment config |
| Persistence | SQLite via `Database`; short-lived connections, foreign keys, busy timeout and transaction helper | Single-file persistence; host filesystem permissions and durable volume are essential |
| Schema | Version 2; projects/tasks/dependencies/activity; automation and Phase 13 tables initialized by their services | Existing schema has no user, role, membership or tenant ownership model |
| Repository/service access | ProjectRepository and feature services accept project/task identifiers | No authenticated principal is passed through service/repository calls |
| Backups | Online SQLite backup, exclusive destination creation, POSIX owner-only mode and integrity/FK verification | Backup primitive exists; scheduling, retention, off-site replication and restore drill are absent |
| Automation | Allow-listed interval schedules, retry state and runner; GitHub Actions verification schedule | GitHub Actions verifies code, but cannot operate on a user's private Colab SQLite file |
| Secrets/logging | Existing secret hygiene and redaction controls from Phase 10 | Host secret storage, rotation and storage encryption remain deployment responsibilities |
| CI | Python 3.11, secret scan, dependency audit, compile, focused tests and full suite | CI is not a live deployment or hosted-environment acceptance |
| Runtime | User-operated Colab and Streamlit browser session | Colab is an acceptance/development environment, not an always-on production host |

## 2. Trust boundaries

1. **Browser → Streamlit process:** currently no login/session identity or server-enforced authorization layer is visible in the application entry point.
2. **Streamlit/services → SQLite:** local process-level access; anyone able to execute code as the host account may access the database file.
3. **Application → GitHub API:** outbound integration; token presence is configuration-only and credentials must remain outside source control.
4. **Automation scheduler → SQLite:** runner executes checks against the configured database on the host where it runs. GitHub-hosted runners do not share the user's Colab filesystem.
5. **Backup destination/storage:** backup API creates verified local files; confidentiality, off-site replication, retention and access policy depend on the operator/host.

## 3. Gaps mapped to Phase 14

- Authentication and authorization: PC-P14-S002.
- Project/user membership and cross-project access control: PC-P14-S003.
- Secret lifecycle and encryption-at-rest boundary: PC-P14-S004.
- Scheduled backups, retention and off-site strategy: PC-P14-S005.
- Non-destructive restore drills and recovery objectives: PC-P14-S006.
- Health/readiness and safe operational audit signals: PC-P14-S007.
- Reproducible deployment and release acceptance: PC-P14-S008.

## 4. Architecture decisions and open questions

**Confirmed decisions**
- Keep SQLite support and current Colab workflow backward-compatible during Phase 14.
- Use synthetic identities and temporary databases for automated tests.
- Enforce authorization in server-side service boundaries, not only by hiding Streamlit controls.
- Do not expose a public deployment until authentication and authorization checks pass.
- Do not claim host-level encryption, off-site backup or production deployment without provider evidence.

**Provider-specific decisions intentionally unresolved**
- Hosting target and persistent-volume semantics.
- Identity provider and supported login/session mechanism.
- Backup destination, retention period, encryption and off-site replication provider.
- Operational alert destination and service-level objectives.

These decisions must be explicit before provider-specific code is merged. No hosting provider or credentials are assumed.

## 5. Acceptance evidence still required

- Reviewer confirmation that the architecture inventory matches the current branch.
- Focused architecture/documentation checks.
- Full regression suite on the feature branch.
- CI success and read-back of the committed audit.
- Colab/browser/deployment checks remain separate; no runtime or dashboard restart is permitted for this audit.

**Checkpoint result:** IN PROGRESS. This audit is not a production-readiness certification and does not mark PC-P14-S001 PASS.
