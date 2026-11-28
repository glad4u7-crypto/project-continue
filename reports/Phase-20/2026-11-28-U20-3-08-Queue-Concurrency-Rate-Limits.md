# U20-3-08 — Queue depth, concurrency and rate limits

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — final transaction fix, focused tests, full CI, container checks and read-back verified

## Policy defaults

- Maximum queued ACK requests: 25.
- Maximum concurrently RUNNING requests: 3.
- Per-authenticated-actor admission rate: 30 requests per rolling 60 seconds.
- Global admission rate: 120 requests per rolling 60 seconds.
- Admission lease: 900 seconds; expired queue/running leases are reclaimed.
- Limits are configurable through validated positive integer settings; actor limit cannot exceed global limit.

## Implementation

- `src/dispatcher/admission.py`: SQLite-backed admission controller.
- `tests/test_dispatcher_admission.py`: 11 tests.
- `BEGIN IMMEDIATE` serializes admission/start/release operations to avoid concurrent workers exceeding queue, concurrency or rate limits when they share one durable SQLite database.
- Admission creates an ACK queue lease and a rate event atomically.
- Start promotes ACK to RUNNING only when a concurrency slot is available.
- Release frees a slot; expired leases are reclaimed.
- Actor and global sliding-window counters remain after release, preventing release/re-admit rate-limit bypass.
- Duplicate request IDs, invalid timestamps, missing/expired queue entries and capacity violations fail closed.

## Operational boundary

- A single durable SQLite database must be shared by all dispatcher workers. Per-worker or ephemeral databases do not enforce global limits.
- SQLite may not be appropriate for multi-host/high-throughput deployment; a PostgreSQL implementation would be required before scaling beyond this documented topology.
- The admission controller is a storage primitive and is not yet wired into a deployed HTTP/queue service. No live traffic was affected.
- No paid service or external API added.

## CI evidence

- U20-3-07 state-machine baseline CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46108629396 — SUCCESS.
- Earlier run `46108860907` exposed a transaction persistence defect in the explicit `BEGIN IMMEDIATE` path; later run `46109449835` exposed the remaining test isolation issue. Both failures are preserved as historical evidence.
- Corrective commit: `a029c3e09351fe70838b319acfee4430dbb9a010` — admission test now releases each queue lease while retaining rate events, so global rate-limit behavior is tested independently from queue capacity.
- Final CI run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46109666102 — SUCCESS; all workflow steps completed.
- Full suite: 363 passed, 11 skipped, 29 subtests passed in 13.38s; coverage 79% (2,575 statements, 544 missed).
- Focused categories: unit 74 passed; integration 28 passed / 11 skipped (PostgreSQL DSNs unavailable); API 21 passed; database 23 passed.
- Admission suite contains 11 tests; audit suite contains 8 tests, both included in the successful full suite.
- Test/coverage artifact (279,692 bytes; SHA-256 `107655929c09fbf5a2e7d94daf36e5e799d84f60d366935d6d64ff131c62a4e4`): https://github.com/glad4u7-crypto/project-continue/actions/runs/46109666102/artifacts/15248872135.

## Acceptance

- Acceptance met: compile, secret scan, dependency audit, production container build, Compose validation, container smoke test, focused categories, full suite and artifact upload all successful.
- PostgreSQL integration checks were skipped because dedicated TEST_POSTGRES_* DSNs are not configured; this is recorded as an environment limitation, not a pass of live PostgreSQL integration.
- Source, tests, report and tracker were read back from this branch.
