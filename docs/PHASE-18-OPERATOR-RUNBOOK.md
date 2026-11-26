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

## Existing Colab dashboard: publish health to GitHub

The current dashboard has historically run on Colab loopback at `127.0.0.1:8501`; GitHub-hosted runners cannot reach that address directly. Use the Colab-side reporter instead of inventing a public URL:

1. Follow `docs/PHASE-18-COLAB-HEALTH-REPORTER.md` to create a fine-grained token with only **Commit statuses: Read and write** for this repository.
2. Store it in Colab Secrets as `PROJECT_CONTINUE_GITHUB_STATUS_TOKEN`; never paste it into chat or notebook output.
3. Run `python scripts/colab_dashboard_status.py` from the repository checkout.
4. For repeat checks while Colab remains active, run `python scripts/colab_dashboard_status.py --interval-seconds 3600` in a separate cell.
5. The script prints the exact checked commit SHA. ChatGPT can inspect that SHA's combined GitHub status for context `project-continue/colab-dashboard-health`.

The reporter checks local loopback and publishes a minimal status against the exact checked-out commit. It does not restart Streamlit. Colab can disconnect; the reporter is not an always-on service. The public HTTPS Actions workflow remains optional for a separately hosted public dashboard and reports SKIP until `STREAMLIT_APP_URL` is configured.
