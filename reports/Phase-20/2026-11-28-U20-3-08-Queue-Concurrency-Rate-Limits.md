# U20-3-08 — Queue depth, concurrency and rate limits

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: IMPLEMENTED — CI PENDING; NOT PASS UNTIL GREEN

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
- U20-3-08 source/test CI run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46108860907 — in progress at report creation. Update after completion.

## Acceptance

- Require successful compile, secret/dependency checks, focused dispatcher tests, full suite and container smoke checks.
- Read back source, tests and report from this branch before marking PASS.
