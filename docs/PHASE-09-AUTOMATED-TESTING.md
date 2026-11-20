# Phase 09 — Automated Testing

## Objective

Provide repeatable, isolated automated verification for Project Continue. Tests must not use the user's live project database or depend on an external network service.

## Checkpoint map

| Checkpoint | Scope | Evidence | Status |
| --- | --- | --- | --- |
| PC-P09-S001 | Pytest configuration | strict discovery, registered markers, collection | PASS |
| PC-P09-S002 | Unit tests | isolated configuration, validation, service and engine tests | PASS |
| PC-P09-S003 | Integration tests | cross-module and workflow tests | PASS |
| PC-P09-S004 | API tests | mocked GitHub HTTP contract, validation and sanitized failures | PASS |
| PC-P09-S005 | Database tests | temporary SQLite files, constraints, transactions and persistence | PASS |
| PC-P09-S006 | Failure detection | expected exceptions, invalid inputs, rollback and safe API error tests | PASS |
| PC-P09-S007 | Test reports | JUnit XML, terminal coverage and HTML/XML coverage artifacts | PASS |
| PC-P09-S008 | Coverage review | inspect module-level coverage and record justified gaps | PASS |

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


## Verification record

- GitHub Actions run #174: PASS.
- Python 3.11.18 compile check: PASS.
- Focused unit, integration, API and database category runs: PASS.
- Full automated suite: **112 passed in 3.41s**.
- Statement coverage: **96% (730 statements; 32 uncovered)**.
- JUnit, coverage XML and HTML reports uploaded as artifact `phase-09-test-reports` (artifact ID `14631377954`).
- Pull request #20: MERGED into `main` on 2026-11-20.
- Merge commit: `62d70f1cea3a9207ff10e0bd859ddecd3e75f01e`.
- Branch synchronization commit: `c565a3d1d35a1266bb840dbffc9cd6d259f14601`.
- Post-synchronization GitHub Actions runs #194 (push) and #195 (pull request): PASS.
- Post-merge `main` CI run #196 was queued at the time of this record; final main-branch CI confirmation is tracked separately.
- Test report artifact from synchronized run #195: `phase-09-test-reports` (artifact ID `14631664115`).

**Implementation, review integration, and pre-merge CI acceptance: COMPLETE.**
