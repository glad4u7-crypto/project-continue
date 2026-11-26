# Colab Dashboard Health Reporter

The current Project Continue dashboard has historically run inside the user's Google Colab runtime at `127.0.0.1:8501`. A GitHub-hosted runner cannot reach that loopback address directly. This reporter checks the local dashboard from inside Colab, then publishes only a minimal health result as a GitHub commit status. ChatGPT can read that status through the connected GitHub integration.

## One-time setup

1. Create a fine-grained personal access token for only `glad4u7-crypto/project-continue`.
2. Grant only **Commit statuses: Read and write**. Do not grant Contents, Actions, Administration, or workflow permissions.
3. In the Colab notebook, open the Secrets (key) panel and add `PROJECT_CONTINUE_GITHUB_STATUS_TOKEN`. Enable notebook access for that secret.
4. Never paste the token into chat, notebook output, a source file, or a committed `.env` file.
5. Ensure the Project Continue repository checkout is the folder containing this script and that the Streamlit dashboard is already running on port 8501.

## Run one check

From a Colab cell in the repository:

```bash
python scripts/colab_dashboard_status.py
```

The script checks only `http://127.0.0.1:8501/_stcore/health`, reads the current Git commit SHA, and posts a status with context `project-continue/colab-dashboard-health`. It does not stop or restart Streamlit, inspect project/task records, read application logs, or transmit the token. It prints the checked commit SHA so the operator/ChatGPT can inspect the matching commit status.

## Repeat while the Colab runtime is active

```bash
python scripts/colab_dashboard_status.py --interval-seconds 3600
```

This checks hourly while that cell/process continues to run. Stop only the reporter cell with its interrupt control; this does not stop Streamlit. Colab can disconnect or terminate an idle runtime, so this is not an always-on monitoring guarantee. The check must be started again after a runtime session ends.

## What the result means

- `success`: the local Streamlit built-in health endpoint returned HTTP 200 at that time.
- `failure`: the endpoint did not return HTTP 200, or the GitHub status could not be published.
- The GitHub status is attached to the exact local checkout commit SHA. If Colab is running an older commit, the status appears on that older commit rather than falsely claiming the current `main` build is running.
- A PASS confirms server reachability only. It does not prove login, database durability, feature correctness, or production readiness.

The reporter uses the GitHub Commit Status API with a narrowly scoped token. Each run creates a new status record; hourly reporting is the recommended default. No paid service, public tunnel, or external monitoring API is required.
