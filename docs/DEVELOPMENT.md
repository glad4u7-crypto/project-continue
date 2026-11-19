# Development Guide

## Requirements

- Python 3.11 or newer
- Git
- A GitHub account with access to this repository

## Local setup

```bash
python -m venv .venv
```

Activate the environment:

- macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`

Install dependencies:

```bash
pip install -r requirements.txt
```

Create local configuration:

```bash
cp .env.example .env
```

On Windows, copy the file manually if `cp` is unavailable.

Run the dashboard:

```bash
streamlit run app.py
```

Run automated tests (as tests are added):

```bash
pytest
```

## Checkpoint rules

For each implementation step:

1. Inspect the current repository state.
2. Make a focused change.
3. Read the changed file back from GitHub.
4. Check its contents and expected path.
5. Run relevant automated checks when an executable environment is available.
6. Report passed checks and any checks not yet run.

A Git commit confirms that content was saved; it does not by itself prove that the feature works.
