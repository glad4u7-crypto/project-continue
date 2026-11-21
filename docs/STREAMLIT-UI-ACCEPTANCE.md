# Streamlit UI — Manual End-to-End Acceptance

**Purpose:** verify the real Streamlit dashboard in the intended Google Colab/browser environment. Automated AppTest startup coverage does not replace this manual audit.

## Checkpoint register

| Checkpoint | Manual workflow | Required evidence |
|---|---|---|
| PC-P04-UI-001 | Start and stop Streamlit app | App URL opens; dashboard renders; process stops cleanly |
| PC-P04-UI-002 | Project create, search, edit, archive and restore | Each action visible after rerun; filters and empty state behave |
| PC-P04-UI-003 | Task create, edit, status, priority and assignment | Values persist and are shown correctly |
| PC-P04-UI-004 | Dependency add/remove and blocked completion | Cycle/cross-project errors are safe; dependent task cannot complete early |
| PC-P04-UI-005 | GitHub integration panel | Configured repository connection check succeeds or safe actionable error appears |
| PC-P04-UI-006 | Restart persistence | Project/task data remains after stopping and restarting Streamlit |
| PC-P04-UI-007 | Backup and restore | Backup verifies; restored database has expected records and integrity |
| PC-P04-UI-008 | Error, empty and loading states | Empty registry, invalid input, API failure and loading feedback render safely |

## Colab preparation

Sync to the exact main SHA first. Keep the existing user database safe; use a separate acceptance database for destructive experiments.

```bash
cd /content/project-continue
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
```

Set the app database path to a dedicated test file before launching:

```bash
export APP_ENV=test
export PROJECT_CONTINUE_DB=/content/project-continue/.data/ui-acceptance.sqlite3
mkdir -p .data
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Open the forwarded Streamlit URL from Colab. Perform the eight workflows above. For persistence, stop Streamlit with Ctrl+C and start it again using the same database path. For backup/restore, use a separate copy and never overwrite the original user database.

## Evidence format

For each checkpoint, capture:
- Checkpoint ID.
- Exact `git rev-parse HEAD` SHA and Python version.
- Action performed and visible result.
- Any error text and whether it was expected/safely handled.
- PASS or FAIL. Do not mark a checkpoint PASS from source inspection alone.

Final sentinel after all eight manual checks:

```text
PC-P04-UI-001: PASS
PC-P04-UI-002: PASS
PC-P04-UI-003: PASS
PC-P04-UI-004: PASS
PC-P04-UI-005: PASS
PC-P04-UI-006: PASS
PC-P04-UI-007: PASS
PC-P04-UI-008: PASS
STREAMLIT UI END-TO-END ACCEPTANCE: PASS
```

Do not print the final sentinel unless all eight checkpoints have actually passed.
