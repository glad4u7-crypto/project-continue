# Project Continue

Project Continue is a project-progress assistant foundation. It is designed to track projects and tasks, identify the next actionable task, connect to GitHub, and verify work using evidence rather than commit messages alone.

## Current status

**Phase:** 01 — Project Foundation  
**Status:** Foundation scaffold in progress

## Features planned

- Project and task tracking
- Dependency-aware next-task suggestions
- GitHub repository and commit inspection
- Verification checkpoints and test evidence
- Human approval for sensitive actions
- A lightweight dashboard suitable for desktop and mobile browsers

## Requirements

- Python 3.11 or newer
- pip

## Quick start

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Copy `.env.example` to `.env` and fill in values only when needed.
5. Start the dashboard.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The dashboard can start without GitHub credentials. Never commit real tokens or secrets.

## Configuration

Environment variables are optional for the initial foundation. See `.env.example`.

## Development checks

```bash
python -m compileall -q .
pytest -q
```

## Safety principles

- No secrets in source control.
- No destructive GitHub action without explicit approval.
- A task is not complete just because a commit exists.
- Completion requires defined acceptance criteria and verification evidence.

## Roadmap

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the foundation plan and [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for initial usage notes.
