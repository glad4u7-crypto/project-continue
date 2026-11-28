# U20-3-09 — Request/result correlation and audit event tests

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: IMPLEMENTED — CI PENDING; NOT PASS UNTIL GREEN

## Implementation
- `src/dispatcher/audit_log.py`: SQLite-backed append-only audit event store.
- Each event carries an immutable event UUID and the originating request UUID, allowing request-to-result lifecycle correlation.
- Event types and lifecycle states are allow-listed; actor/repository/task identifiers and timezone-aware timestamps are validated.
- Unique event IDs and unique (request_id, event_type, state) transitions prevent duplicate audit writes.
- Ordered per-request history supports correlation across ACK, RUNNING and terminal outcomes.
- Audit schema intentionally excludes task arguments, arbitrary payloads and secret values.

## Tests
- `tests/test_dispatcher_audit_log.py`: 8 tests for correlation/order, persistence, duplicate rejection, validation, privacy minimization and empty history.
- Full CI is required before PASS.

## Operational boundary
- Uses the same injected durable SQLite database abstraction; multi-host/high-throughput use still requires a shared transactional PostgreSQL adapter.
- This is an audit storage primitive, not yet wired into the live HTTP/queue service. No production traffic or state changed.
- No credentials, paid services or external APIs added.

## Acceptance
- Require successful secret/dependency checks, compile, focused dispatcher tests, full suite, container build/smoke and repository read-back.
