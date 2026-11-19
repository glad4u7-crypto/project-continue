# Project Continue

Project Continue is a project-workflow assistant designed to organize multiple projects, track tasks and dependencies, recommend the next actionable task, and verify work with evidence.

## Current status

**Phase:** Foundation  
**Status:** Initial scaffold

The repository is being built in small, verifiable checkpoints. Existing user files are preserved. `main` is the authoritative branch; see [Branching Policy](docs/BRANCHING.md).

## Planned capabilities

1. Project and task registry
2. Task status, priority, and dependency tracking
3. Next-task recommendations with clear reasoning
4. GitHub integration for repository and change inspection
5. Verification using tests and other evidence (a commit alone does not mean a task is complete)
6. Human approval for sensitive or destructive actions
7. A mobile-friendly dashboard
8. Automated tests and user documentation

## Technology baseline

- Python 3.11+
- Streamlit dashboard
- python-dotenv for local environment configuration
- Requests for future API integrations
- Pytest for automated tests

## Quick start

1. Create and activate a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in only the values you need.
4. Run: `streamlit run app.py`

Never commit `.env`, access tokens, passwords, or private keys.

## Project structure

```
project-continue/
├── .github/
│   └── workflows/
│       └── ci.yml
├── core/
│   └── __init__.py
├── database/
│   └── __init__.py
├── docs/
│   ├── BRANCHING.md
│   ├── DEVELOPMENT.md
│   └── USER_GUIDE.md
├── integrations/
│   └── __init__.py
├── tests/
│   └── test_config.py
├── app.py
├── config.py
├── pytest.ini
├── requirements.txt
├── .env.example
└── .gitignore
```

The `core/`, `database/`, and `integrations/` packages are currently placeholders; their implementation will be introduced in later checkpoints.

## Safety principles

- No secrets in source code or Git history.
- Ask for approval before destructive or externally visible actions.
- Treat repository changes as unverified until relevant checks pass.
- Record what was checked and what evidence supports completion.

## Documentation

- [Development Guide](docs/DEVELOPMENT.md)
- [User Guide](docs/USER_GUIDE.md)
- [Branching Policy](docs/BRANCHING.md)
