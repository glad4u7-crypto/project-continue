# Phase 09 — Automated Testing

## Objective

Provide repeatable, isolated automated verification for Project Continue. Tests must not use the user's live project database or depend on an external network service.

## Checkpoint map

| Checkpoint | Scope | Evidence |
| --- | --- | --- |
| PC-P09-S001 | Pytest configuration | strict discovery, registered markers, collection |
| PC-P09-S002 | Unit tests | isolated configuration, validation, service and engine tests |
| PC-P09-S003 | Integration tests | cross-module and workflow tests |
| PC-P09-S004 | API tests | mocked GitHub HTTP contract, validation and sanitized failures |
| PC-P09-S005 | Database tests | temporary SQLite files, constraints, transactions and persistence |
| PC-P09-S006 | Failure detection | expected exceptions, invalid inputs, rollback and safe API error tests |
| PC-P09-S007 | Test reports | JUnit XML, terminal coverage and HTML/XML coverage artifacts |
| PC-P09-S008 | Coverage review | inspect module-level coverage and record justified gaps |

## Test isolation rules

- Database tests use pytest temporary paths or isolated in-memory databases.
- GitHub API tests use fake sessions and fake responses; they do not require a token or network.
- Do not point automated tests at a user's existing production/project database.
- CI must run the deterministic automated suite. Live external API smoke checks are not part of the required test gate.

## Running tests

Install development dependencies:

```bash
pip install -r requirements.txt
```

Run all tests:

```bash
python -m pytest -q
```

Run a test category:

```bash
python -m pytest -m unit -q
python -m pytest -m integration -q
python -m pytest -m api -q
python -m pytest -m database -q
```

Run tests with reports:

```bash
mkdir -p reports
python -m pytest -q \
  --junitxml=reports/junit.xml \
  --cov=app --cov=config --cov=core --cov=database \
  --cov=integrations --cov=services \
  --cov-report=term-missing \
  --cov-report=xml:reports/coverage.xml \
  --cov-report=html:reports/coverage-html
```

## CI outputs

GitHub Actions compiles the repository, runs the full deterministic suite, creates JUnit and coverage reports, and uploads the `reports/` directory as the `phase-09-test-reports` artifact even when a test step fails (if the runner reaches the upload step).

## Completion policy

A checkpoint is PASS only when its focused tests and required evidence have been reviewed. A Git commit or a successful test collection alone is not proof that tests passed. Coverage percentages must be reviewed against meaningful branches and failure paths; a high percentage alone is not acceptance.
