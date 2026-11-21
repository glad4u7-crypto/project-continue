# Phase 13 — Memory & Checkpoint Engine

## Checkpoint register

| Checkpoint | Scope | Implementation |
|---|---|---|
| PC-P13-S001 | Project Memory Schema | Typed, project-scoped SQLite memory; bounded JSON values and upsert semantics |
| PC-P13-S002 | Checkpoint Storage | Immutable project/task/dependency snapshot with SHA-256 integrity |
| PC-P13-S003 | Session History | Append-only, project-scoped session events and metadata |
| PC-P13-S004 | Decision Records | Auditable decisions with context, rationale and lifecycle status |
| PC-P13-S005 | Handoff Generator | Deterministic Markdown handoff from live state and durable history |
| PC-P13-S006 | Resume Command Parser | Strict allow-listed grammar; no shell, eval or arbitrary action execution |
| PC-P13-S007 | State Recovery | Digest verification and preview-first additive restore |
| PC-P13-S008 | Recovery Tests | Nine isolated temporary SQLite regression tests |

## Safety and compatibility

- Phase 13 tables are additive and initialized independently; existing schema version and project/task rows are not rewritten.
- Memory is project-scoped. Callers must not store credentials or secrets in memory values.
- Checkpoints are SHA-256 verified before reading or recovery.
- Recovery is preview-first. Applying a recovery restores missing tasks only; existing tasks and project metadata are never overwritten or deleted.
- Recovery requires the original project row to exist. Recreating a deleted project is intentionally not automatic.
- Resume parsing is a command router only. It never executes shell commands, Python, AI-generated code, or arbitrary tools.
- Session history and decision records are durable in the existing SQLite database.
- Streamlit panel: ui/memory_checkpoint.py, mounted from app.py; includes memory CRUD, checkpoint creation, session/decision entry, handoff download and explicit recovery confirmation.

## Verification

Run in the existing Colab environment only after the feature is merged and the exact main SHA is known:

~~~bash
python -m compileall -q services/memory_checkpoint_engine.py tests/test_memory_checkpoint_engine.py
python -m pytest -q tests/test_memory_checkpoint_engine.py
python -m pytest -q
~~~

Automated PASS requires focused tests, full regression and CI. Exact-SHA Colab runtime and manual Streamlit UI evidence are separate acceptance gates.
