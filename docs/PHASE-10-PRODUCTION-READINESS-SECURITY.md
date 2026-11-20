# Phase 10 — Production Readiness & Security

## Objective

Harden Project Continue for safer deployment and operation without changing its current product behavior or exposing user data. All work is isolated on `feature/phase-10-production-readiness-security` until reviewed and merged through a pull request.

## Scope and safety boundaries

- Preserve the read-only GitHub integration.
- Never add real credentials, tokens, private keys, database files, or user data to Git.
- Keep automated tests isolated from live databases and external network services.
- Do not claim production certification, authentication, authorization, encryption-at-rest, or hosted deployment unless those capabilities are implemented and verified.
- Do not modify `main` directly; use a feature branch and pull request.
- Prefer additive, backwards-compatible changes.

## Checkpoint map

| Checkpoint | Scope | Evidence required | Status |
| --- | --- | --- | --- |
| PC-P10-S001 | Security baseline and threat model | Repository inventory, trust boundaries, prioritized risks | PASS |
| PC-P10-S002 | Production configuration validation | Strict production settings and deterministic tests | PASS |
| PC-P10-S003 | Secrets and repository hygiene | Secret-safe templates, ignore rules, automated leak checks | PASS |
| PC-P10-S004 | Safe logging and error handling | Redaction tests for tokens, exception messages and sensitive headers | PASS |
| PC-P10-S005 | Database operational safety | SQLite durability/backup guidance and safe backup verification | PASS |
| PC-P10-S006 | Input and integration hardening | Boundary tests for untrusted values, URLs, timeouts and API failures | IN PROGRESS |
| PC-P10-S007 | Dependency and CI security checks | Reproducible dependency audit and CI security gate | IN PROGRESS |
| PC-P10-S008 | Production readiness acceptance | Full suite, security checklist, documented limitations and final report | PENDING |

## Initial repository baseline

- Python 3.11+, Streamlit, SQLite, Requests and python-dotenv.
- GitHub integration is read-only and already sanitizes common HTTP/network errors.
- Configuration is immutable and validates environment names, log levels and repository syntax.
- `.env`, private keys, Streamlit secrets, local databases and local data directories are ignored by Git.
- SQLite connections enable foreign keys and a busy timeout; transactions roll back on exceptions.
- Existing automated suite is green on `main`: 112 tests and 96% statement coverage.
- Current app is a single-user Streamlit application; no authentication/authorization boundary is claimed.

## Acceptance policy

A checkpoint is PASS only after implementation, focused tests, full relevant regression checks, and read-back verification. A file commit alone is not acceptance. Any unverified control remains explicitly marked pending.

## Resume protocol

Use the checkpoint IDs above. Resume from the first checkpoint not marked PASS. Each checkpoint document under `docs/checkpoints/` records its scope, exact actions, commands, evidence and next checkpoint.

