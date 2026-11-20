# PC-P10-S004 — Safe Logging and Error Handling

**Status:** IN PROGRESS  
**Phase:** 10 — Production Readiness & Security

## Implemented controls

- Added `core.security.redact_secrets` to mask common GitHub token formats, bearer authorization values, and common credential key/value pairs.
- Added a logging filter to configured application handlers so formatted log messages are redacted before output.
- Updated `handle_application_error` to redact caller-supplied context and continue omitting exception messages.
- Added tests for GitHub token patterns, bearer headers, parameterized logger messages, and application exception handling.

## Acceptance criteria

- Secret values do not appear in application log output.
- Exception messages remain excluded from the safe application error handler.
- Redaction preserves useful non-secret diagnostic information.
- Focused unit tests and the full regression suite pass.

## CI evidence

- CI verification pending after the security logging changes.

## Next

After acceptance, proceed to PC-P10-S005 — Database Operational Safety.
