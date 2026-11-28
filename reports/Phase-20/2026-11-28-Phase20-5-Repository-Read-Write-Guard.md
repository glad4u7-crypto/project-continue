# Phase 20.5 — Repository read/write guard foundation (U20-5-01..05)

- Repository: glad4u7-crypto/project-continue
- Branch: phase20/secure-dispatcher-u20-3-01
- Date: 2026-11-28 (Asia/Kolkata)
- Status: IMPLEMENTED — dedicated runner PASS; main CI for exact latest SHA pending.

## Artifacts
- src/dispatcher/repository_guard.py
- tests/test_dispatcher_repository_guard.py

## Implemented checkpoints
| Unit | Work | Current evidence |
|---|---|---|
| U20-5-01 | Immutable repository snapshot file read and tree listing | Exact 40-character commit binding; UTF-8 file read with SHA-256/size; deterministic tree listing capped at 1000 entries |
| U20-5-02 | Base branch and SHA precondition | Requires full SHA and rejects changed observed base SHA |
| U20-5-03 | Separate feature branch | Rejects main/master and requires distinct phase20/ or feature/ target branch |
| U20-5-04 | Path protection | Rejects absolute/traversal/backslash/NUL/hidden paths, symlinks, sensitive extensions and paths escaping root |
| U20-5-05 | Content validation | UTF-8 strict, non-empty, no NUL, 256 KiB max, JSON parse check, credential-pattern rejection, Git blob SHA optimistic overwrite protection |

## Tests and debugging history
- The first deep CI run identified two test/implementation mismatches: feature branches are intentionally permitted, and an invalid-UTF8 fixture was accidentally encoded as literal ASCII backslash text.
- Corrected feature-branch expectation and used an actual invalid UTF-8 byte fixture.
- Corrected Git blob hashing to use the canonical NUL-delimited Git blob header and corrected NUL-byte rejection to check an actual zero byte.
- Final dedicated runner run 46110628198 — SUCCESS on exact SHA 4a4f2a772f791cd5a11fad988b5b4073e4860958.
- Fixed dispatcher/repository-guard suite: 64 passed, 45 subtests passed.
- Runner full suite: 380 passed, 11 PostgreSQL tests skipped, 50 subtests passed in 9.61s.
- Main repository CI run 46110628207 is still running; do not mark the units PASS until it finishes green and final read-back completes.

## Integration boundary
- This is a host-injected local checkout/snapshot guard, not a live GitHub Contents API adapter. The host must bind the checkout to the verified immutable SHA before constructing RepositorySnapshot.
- No direct write, merge, PR creation, production mutation or live GitHub write was performed.
- GitHub connector write operations remain separately governed by branch/SHA checks and explicit feature-branch use.