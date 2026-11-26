# Phase 18 — Operator Runbook

## What the automatic dashboard check does

The GitHub Actions workflow `.github/workflows/dashboard-health.yml` runs hourly and can also be started manually from the repository Actions tab. It performs a read-only HTTPS GET against Streamlit's built-in `/_stcore/health` endpoint. The probe:

- requires HTTPS and rejects embedded credentials, query strings and fragments;
- does not follow redirects;
- uses a 10-second request timeout;
- prints only a sanitized PASS/FAIL result, never the configured URL or response body;
- does not sign in, inspect project/task records, run database mutations, access provider logs, restart the app, or deploy code.

## Enable the live check

In the GitHub repository, open **Settings → Secrets and variables → Actions → Variables**, create a repository variable named `STREAMLIT_APP_URL`, and set its value to the public HTTPS base URL of the Streamlit app (for example, `https://your-app.streamlit.app`). Do not include credentials, query parameters or fragments. This is a non-secret URL; do not put tokens or passwords in it.

Until the variable is configured, scheduled runs intentionally report SKIP rather than falsely claiming the live dashboard was checked. After configuration, use **Actions → Streamlit Dashboard Health → Run workflow** for an immediate check. Review the run result and timestamp.

## What a PASS means — and does not mean

PASS means only that the configured HTTPS Streamlit health endpoint returned HTTP 200 at that time. It confirms server-level reachability, not successful login, database durability, application feature correctness, GitHub integration, or production readiness. A failing probe reports a sanitized failure; investigate through the Streamlit provider's own dashboard and logs.

The existing in-app **Automated self-check** remains the application-level diagnostic. An administrator must sign in and run it from the dashboard; it checks configured application/database conditions and presents a sanitized report. It is not an unattended external endpoint.

## Free-tier and control boundaries

GitHub Actions usage is subject to GitHub's current included-minute and storage limits; this workflow is deliberately short and uses no paid third-party service. The user must confirm the account's current allowance.

Streamlit Community Cloud does not expose a general-purpose project API here for platform process logs, arbitrary restart, or deployment administration. Those operations remain in the provider interface. Do not claim ChatGPT can see private provider logs or restart the hosted app through this health workflow.

All workflow permissions are read-only (`contents: read`). No deployment, restart, database migration, backup deletion/restore, or secret modification is performed.
