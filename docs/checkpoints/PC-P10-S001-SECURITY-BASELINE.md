# PC-P10-S001 — Security Baseline and Threat Model

**Status:** IN PROGRESS  
**Phase:** 10 — Production Readiness & Security

## Purpose

Establish the current trust boundaries and prioritized risks before changing security-sensitive code.

## Baseline inspected

- `config.py`: immutable settings; environment, log-level and repository-format validation; token presence is represented only as a boolean.
- `integrations/github_client.py`: token is private to the client, excluded from repr, request timeout is bounded, and common HTTP/network errors are sanitized.
- `core/errors.py`: application error logging records the exception class rather than its message.
- `core/logging.py`: named logger configuration avoids changing root logging.
- `database/connection.py`: SQLite foreign keys and busy timeout are enabled; transactions roll back on exceptions.
- `.gitignore`: excludes environment files, key files, Streamlit secrets, local database files and local data.
- `tests/`: deterministic tests exist for configuration, database behavior and mocked GitHub API interactions.
- CI on main is green after Phase 09: 112 tests, 96% statement coverage.

## Initial risks to address

1. Production mode currently has no explicit fail-closed policy for unsafe or missing runtime configuration.
2. Secret hygiene is based on ignore rules and developer discipline; no automated repository secret scan is configured.
3. Logging safety should be tested against common credential-bearing strings and exception paths.
4. Database backup/restore and file-permission expectations are not yet documented or tested.
5. Dependency security is not currently an explicit CI acceptance gate.
6. This Streamlit app has no authentication/authorization layer; it must not be represented as a multi-user secure service.

## Completion criteria

- Trust boundaries and current limitations are documented.
- Risks are prioritized without asserting controls that do not exist.
- The next checkpoint is PC-P10-S002.

## Evidence

- Source inspection completed against the `main` branch before Phase 10 changes.
- Phase 09 post-merge CI #196 and documentation-update CI #197: SUCCESS.

## Next

Implement PC-P10-S002 — Production Configuration Validation.
