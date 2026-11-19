# Development Guide

## Foundation layout

- `app.py` — Streamlit dashboard entry point.
- `config.py` — environment-backed settings; credentials are optional.
- `core/` — future project, task, planning, and verification logic.
- `database/` — future persistence layer.
- `integrations/` — future GitHub and AI adapters.
- `tests/` — automated tests.
- `docs/` — user and developer documentation.

## Local development

Use Python 3.11 or newer. Create a virtual environment, install dependencies with `pip install -r requirements.txt`, then run `streamlit run app.py`.

## Checkpoint policy

1. Inspect repository state before editing.
2. Make one logical change at a time.
3. Read every changed file back from GitHub.
4. Run compile checks and automated tests.
5. Record test evidence before marking work complete.
6. Require explicit approval for destructive or externally visible actions.
7. Never treat a commit alone as proof that a task is complete.

## Planned phases

1. Database schema and project registry.
2. Task model, statuses, and dependencies.
3. Dependency-aware next-task recommendations.
4. GitHub read-only integration and verification engine.
5. Dashboard workflows, automation, security hardening, and release.
