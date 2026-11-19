# Core Architecture

## Application entry points

- `streamlit run app.py` starts the current dashboard shell.
- `python -m app` starts the core application bootstrap.

## Configuration

`config.Settings` is immutable. Use `get_settings(mapping)` for deterministic tests or `get_settings()` to read the process environment. The module-level `settings` object is loaded once at import time. Restart the process after changing environment configuration.

Supported `APP_ENV` values: `development`, `test`, and `production`.

Supported `LOG_LEVEL` values: standard Python levels from `DEBUG` through `CRITICAL`.

## Errors and logging

Expected application failures derive from `ProjectContinueError`. The error handler logs the exception type and a caller-supplied context, not the exception message. Configure named loggers with `setup_logging`; root logging is not modified.

## Data validation

The `core.validation` module provides small standard-library validators. It does not yet represent persisted project/task entities or replace a future database schema.

## Lifecycle

`ApplicationLifecycle` manages one process-local lifecycle. It is a reusable primitive, not a background worker, scheduler, or distributed lifecycle coordinator.
