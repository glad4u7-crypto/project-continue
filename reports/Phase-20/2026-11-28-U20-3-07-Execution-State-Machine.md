# U20-3-07 — ACK/RUNNING/PASS/FAIL/BLOCKED/CANCELLED state machine

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: IMPLEMENTED — CI PENDING; NOT PASS UNTIL GREEN

## Implemented artifacts

1. `src/dispatcher/execution_state.py`
   - Enumerates exactly ACK, RUNNING, PASS, FAIL, BLOCKED and CANCELLED.
   - Starts every accepted request in ACK (version 1).
   - Allows ACK -> RUNNING/BLOCKED/CANCELLED.
   - Allows RUNNING -> PASS/FAIL/BLOCKED/CANCELLED.
   - PASS, FAIL, BLOCKED and CANCELLED are terminal.
   - Rejects unknown states, invalid jumps, repeated transitions, stale expected versions, naive timestamps and backwards event timestamps.
   - FAIL, BLOCKED and CANCELLED require a non-empty reason.
   - Exposes immutable event-history snapshots and monotonically increasing versions.

2. `tests/test_dispatcher_execution_state.py`
   - 11 tests cover initial state, successful path, all terminal outcomes, preflight block/cancel, forbidden jumps, terminal immutability, mandatory reasons, stale versions, invalid timestamps/states and immutable monotonic history.

## Scope and explicit boundary

- This unit implements a deterministic in-process domain state machine only.
- Durable cross-worker state persistence, queue coordination and concurrency/rate limits are separate checkpoints (U20-3-08 and later integration); this module does not claim distributed locking or persistence.
- No workflow dispatch, production service, secret or live data was invoked or modified.

## CI evidence

- U20-3-06 baseline green CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46105212163 — 333 passed, 11 skipped, 10 subtests passed; 79% repository coverage.
- CI for this unit's two new files is pending. Record its run and final test counts here after completion.

## Acceptance

- Require a green workflow covering compile, focused dispatcher tests and the full test suite.
- Read back both implementation and test files from this branch before marking PASS.
