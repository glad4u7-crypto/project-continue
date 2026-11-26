# Phase 18 — Capability Audit and Threat Model

## S001 — Verified capability and permission audit

### GitHub repository operations available through the connected GitHub integration

Verified in this project session: inspect repository files and pull requests, compare commit refs, create a feature branch, commit files to that branch, open/update a pull request, and retrieve commit-associated workflow/status evidence where the connector exposes it. These are repository-level operations; they do not imply access to the user's Colab runtime or Streamlit hosting account.

The connector surface available in this session does not provide a supported action to invoke arbitrary Streamlit app methods, read the user's private Streamlit provider logs, or restart/deploy a Community Cloud app. GitHub Actions can make a bounded outbound HTTPS request to the app's public Streamlit health endpoint after the owner configures the repository variable.

### Streamlit capability boundary

- Built-in `/_stcore/health`: server-level HTTP health only.
- In-app Automated self-check: administrator-triggered, read-only checks for database connection, SQLite tables/schema/integrity/foreign keys, GitHub repository configuration, and environment label. It deliberately omits filesystem paths, records, credentials and SQL exception text.
- Provider platform logs, build logs, app restart, secrets and deployment controls: use the provider's own interface; no general-purpose control API is assumed.
- No unattended ChatGPT-to-Streamlit custom API integration is assumed or claimed.

### S002 — Threat model and operation matrix

| Operation | Classification | Control |
|---|---|---|
| Read repository files, PR metadata and CI status | Read-only | Connected GitHub permission |
| Scheduled GET to `/_stcore/health` | Read-only | HTTPS only, 10-second timeout, no redirects, no response-body logging |
| Run in-app self-check | Read-only | Existing administrator access; no data writes |
| Read application/provider logs | Sensitive read | Not exposed through this workflow; inspect provider UI |
| Create feature branch/PR commits | Reversible write | Explicit task request; isolated feature branch; reviewable diff |
| Merge PR | Release write | Explicit user approval required |
| Change GitHub variables/secrets | Sensitive write | Owner action in GitHub settings; never request secret values in chat |
| Deploy, restart, migrate DB, restore/delete backups | High-impact/destructive | Explicit user approval and operator-side execution only |

### Security controls

- GitHub Actions permissions are `contents: read`; no repository write token is granted.
- Workflow concurrency prevents overlapping health probes.
- Probe URL must be HTTPS and cannot contain credentials, query strings or fragments.
- Redirects are rejected; the URL and response body are never printed.
- Connection errors are reduced to a generic message to avoid leaking host/network details.
- The health probe does not authenticate or access project/task content.
- No third-party paid service or external monitoring API is added.
- Scheduled checks are hourly to keep free-tier consumption bounded.

## S003/S004 — Delivered implementation

- `scripts/check_dashboard_health.py`: dependency-free, sanitized Streamlit health probe.
- `tests/test_dashboard_health_check.py`: unit coverage for HTTPS validation, 200 response, redirect rejection, sanitized errors and unconfigured URL behavior.
- `.github/workflows/dashboard-health.yml`: hourly and manual read-only health workflow.
- `docs/PHASE-18-OPERATOR-RUNBOOK.md`: configuration and operator instructions.

## S005 — ChatGPT workflow verification

The connected GitHub integration was used to inspect PR #58 and its branch, then add implementation commits to that feature branch. ChatGPT can assist with repository review and PR evidence through the available connector actions. Direct Streamlit platform administration is not available in this session. The safe bridge is a GitHub Actions health result plus operator inspection of provider-only controls.

## S006 — Acceptance gates and limitations

Automated CI must pass on the exact final PR head SHA. The owner must configure the repository variable `STREAMLIT_APP_URL` to enable live hourly probes; without it the workflow intentionally reports SKIP. A successful probe proves only that the Streamlit server health endpoint returned HTTP 200 at the check time. It does not prove successful login, database durability, feature correctness, or production readiness.

No production deployment, live database change, backup operation, Colab runtime reboot, dashboard restart, secret change or PR merge is performed by this phase. PR #58 remains subject to review and explicit merge approval.
