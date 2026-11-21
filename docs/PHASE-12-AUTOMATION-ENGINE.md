# Phase 12 — Automation Engine

| Checkpoint | Scope | Evidence target |
|---|---|---|
| PC-P12-S001 | SQLite automation architecture and allow-listed checks | Isolated tests + CI |
| PC-P12-S002 | Project-scoped task status update rules | Task integration tests |
| PC-P12-S003 | Durable interval schedules: health, overdue, stale checks | Schedule tests |
| PC-P12-S004 | Scheduled/manual GitHub Actions verification | Workflow run |
| PC-P12-S005 | Persistent-host CLI and automated verification | CLI + regression |
| PC-P12-S006 | Exponential retry, bounded attempts and manual recovery | Failure tests |
| PC-P12-S007 | Durable in-app notifications and read state | Notification tests |
| PC-P12-S008 | Temporary-database automation regression | Full CI + Colab |

## Operation and boundaries
- Only built-in checks execute; arbitrary Python or shell is never evaluated.
- Configure schedules in the app. A persistent host scheduler must periodically invoke python scripts/run_automation_checks.py. A disconnected Colab runtime is not an always-on scheduler.
- GitHub Actions scheduled runs validate repository code; they cannot access the user's Colab SQLite database.
- Notifications are stored in SQLite and shown in the Streamlit Automation panel. Email/SMS delivery is not implemented.
- Retries use bounded exponential backoff, stop after configured attempts and can be manually re-enabled.
- Automation tables are additive. Existing project/task rows are not rewritten.
- Tests use temporary SQLite databases and mocked failures, not the live project database.

## Verification commands
~~~bash
python -m compileall -q services ui scripts tests
python -m pytest -q tests/test_automation_engine.py
python scripts/run_automation_checks.py
python -m pytest -q
~~~

Implementation, CI, merged-main CI and exact-SHA Colab acceptance are separate gates.
