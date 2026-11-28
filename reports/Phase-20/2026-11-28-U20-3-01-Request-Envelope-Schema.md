# Phase 20.3 — U20-3-01 Versioned JSON Request Envelope Schema

- **Timestamp:** 2026-11-28 07:29:57 Asia/Kolkata
- **Repository:** `glad4u7-crypto/project-continue`
- **Branch:** `phase20/secure-dispatcher-u20-3-01`
- **Schema commit:** `263da3f6e60c48720abb23a4e86891a030c5096f`
- **Schema path:** `schemas/dispatcher/request-envelope.v1.schema.json`
- **Read-back blob SHA:** `4a79379eaee81b400d11d88dcb174a49489c4025`

## Result

**PASS — U20-3-01 only.**

Created a versioned JSON Schema using JSON Schema Draft 2020-12. The envelope defines:
- protocol version `1.0`;
- request and idempotency identifiers;
- actor identity;
- repository full name and immutable 40-character commit SHA;
- fixed task identifier plus task arguments;
- issued/expiry timestamps and optional trace correlation ID.

The root object rejects unknown top-level properties. Nested actor, repository and task objects also reject unknown properties. Task arguments remain data only and must be validated against a fixed task registry before dispatch.

## Verification evidence

1. The generated schema text was parsed with JavaScript `JSON.parse` before the GitHub write — syntax check PASS.
2. The committed file was fetched again from the feature branch — read-back PASS.
3. Read-back confirmed Draft 2020-12, version constant `1.0`, root `additionalProperties: false`, and the expected nine envelope properties.
4. Read-back blob SHA: `4a79379eaee81b400d11d88dcb174a49489c4025`.

## Scope limits

- No JSON Schema validator package or runtime dispatcher was executed; semantic validator tests remain future work.
- U20-3-02 will separately make request ID, idempotency key, actor, repository/SHA and expiry mandatory and enforce their uniqueness/authorization semantics.
- No shell, Python, SQL, workflow dispatch, credential access, production data or live service was invoked.
- No merge to main was performed.

## Phase 20.2 approved limitations

The user explicitly approved proceeding with the two Phase 20.2 limitations retained as **UNAVAILABLE**: U20-2-06 (Secret Store verification) and U20-2-08 (revoked-credential fail-closed test). Neither is reclassified as PASS. The 20.2 parent is recorded as accepted limitations / approved to proceed, not fully passed.
