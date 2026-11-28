# Phase 20.3 — U20-3-02 Mandatory identity, idempotency and expiry fields

- **Timestamp:** 2026-11-28 07:31:28 Asia/Kolkata
- **Repository:** `glad4u7-crypto/project-continue`
- **Branch:** `phase20/secure-dispatcher-u20-3-01`
- **Schema update commit:** `11960b76ce8d4a087e29798458b687b6ee8d432d`
- **Schema path:** `schemas/dispatcher/request-envelope.v1.schema.json`
- **Read-back blob SHA:** `9a67d9799962833579376d16d4e8cad36a8fddf6`

## Result

**PASS — schema-level requirements for U20-3-02.**

The envelope now requires all of these fields:
`schema_version`, `request_id`, `idempotency_key`, `actor`, `repository`, `task`, `issued_at`, and `expires_at`. Only `trace_id` remains optional.

Existing constraints require a UUID-shaped request ID, a 16–128 character restricted idempotency key, a non-empty actor ID and actor type from the fixed `user|service` allow-list, repository full-name shape, a 40-character hexadecimal immutable commit SHA, a fixed-format task ID, and date-time timestamps.

The schema descriptions now specify:
- request IDs must be unique and duplicates rejected;
- idempotency keys are unique within actor + repository + task scope;
- retry with the same canonical payload returns the original result;
- reuse of the same idempotency key with a different payload is rejected;
- runtime validation must reject expired requests and require expiry later than issue time.

## Verification evidence

A deterministic JavaScript contract-check harness inspected the committed schema and exercised a valid envelope plus negative cases:
- valid envelope accepted;
- each of the seven non-version mandatory fields independently omitted and rejected;
- non-positive validity window rejected;
- malformed SHA rejected;
- invalid actor rejected;
- short idempotency key rejected.

**12/12 checks PASS.** The committed schema was fetched back from the feature branch and parsed as JSON. Read-back blob SHA is recorded above.

## Important limitation

No JSON Schema validator library or persistent idempotency store was run. The checks above are deterministic contract assertions against the schema's declared requirements, not a production dispatcher execution. Cross-request uniqueness, atomic idempotency reservation, canonical-payload comparison and replay behavior still require implementation and concurrency tests in later dispatcher/runtime checkpoints. No runtime uniqueness guarantee is claimed here.

No workflow dispatch, shell/Python/SQL execution, credential access, production data access or live service call occurred. No merge to main.

## Phase 20.2 disposition

The user's explicit approval to proceed with U20-2-06 and U20-2-08 retained as UNAVAILABLE remains in force. Neither limitation is reclassified as PASS.
