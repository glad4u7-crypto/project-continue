# U20-3-08 — Queue depth, concurrency and rate limits

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — implementation, focused tests, full CI, container checks and read-back verified

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
- U20-3-08 CI run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46108860907 — SUCCESS (run 822; all 13 workflow steps successful).
- Full suite: 344 passed, 11 skipped, 23 subtests passed; coverage 79%.
- Focused admission tests: 11 tests are included in the full suite; focused dispatcher categories and all security/container checks passed.
- Test/coverage artifact: https://github.com/glad4u7-crypto/project-continue/actions/runs/46108860907/artifacts/15248647645.

## Acceptance

- Acceptance met: compile, secret scan, dependency audit, production container build, Compose validation, container smoke test, focused categories, full suite and artifact upload all successful.
- PostgreSQL integration checks were skipped because dedicated TEST_POSTGRES_* DSNs are not configured; this is recorded as an environment limitation, not a pass of live PostgreSQL integration.
- Source, tests, report and tracker were read back from this branch.
