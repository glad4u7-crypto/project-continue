# Phase 20.5 — Repository read/write and patch workflow

- Repository: glad4u7-crypto/project-continue
- Branch: phase20/secure-dispatcher-u20-3-01
- Status: PASS — 11/11 checkpoints verified; PR #71 opened as DRAFT, not merged.
- Accepted code SHA: cf6e342badd589f572ae05afecb64af2253ba58e

## Implementation artifacts
- src/dispatcher/repository_guard.py
- tests/test_dispatcher_repository_guard.py

## Checkpoint acceptance
| Unit | Acceptance | Evidence | Status |
|---|---|---|---|
| U20-5-01 | Immutable repository file/tree read | Snapshot bound to full commit SHA; UTF-8 read, SHA-256/size metadata, deterministic tree listing capped at 1000 entries | PASS |
| U20-5-02 | Branch/base SHA check before write | Full SHA validation and stale-base rejection; verified by prepare_patch | PASS |
| U20-5-03 | Separate feature branch | Only phase20/ or feature/ branches accepted; target must differ from base | PASS |
| U20-5-04 | Path traversal and sensitive path guard | Rejects absolute/traversal/backslash/NUL/hidden paths, symlinks, sensitive extensions, and root escapes | PASS |
| U20-5-05 | File size, encoding and content validation | UTF-8 strict, 256 KiB max, non-empty, NUL rejection, JSON parse, credential-pattern rejection | PASS |
| U20-5-06 | Existing file overwrite guarded by blob SHA | Canonical Git blob SHA required and compared with current content; stale/missing SHA fails closed | PASS |
| U20-5-07 | Stale SHA conflict causes re-read, not write | prepare_patch raises RepositoryAccessRejected on stale base or blob SHA; no patch returned | PASS |
| U20-5-08 | Diff review lists files and line counts | summarize_diff returns path, additions, deletions, old/new blob SHA; PR table records per-file review | PASS |
| U20-5-09 | PR creation after successful checks | Draft PR #71 created after compile, focused tests and full CI passed | PASS |
| U20-5-10 | PR body records evidence, risk, rollback and tests | PR #71 body includes summary, 45-file diff stats, test runs, skipped PostgreSQL conditions, risks, rollback and review gate | PASS |
| U20-5-11 | Direct main-branch writes blocked | prepare_patch rejects main/master; only separate feature branches pass tests | PASS |

## CI evidence
- Main repository CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46111096455 — SUCCESS on code SHA cf6e342badd589f572ae05afecb64af2253ba58e.
- Dedicated fixed-task runner: https://github.com/glad4u7-crypto/project-continue/actions/runs/46111096475 — SUCCESS on the same code SHA.
- Repository guard/dispatcher suite: 69 passed, 47 subtests passed.
- Runner full regression: 385 passed, 11 skipped, 52 subtests passed.
- Main CI full regression: 385 passed, 11 skipped, 52 subtests passed in 13.08s.
- Coverage: 79% (2,575 statements, 544 missed).
- Main CI stages all green: secret scan, dependency audit, compile, production container build, Compose validation, smoke test, focused test categories, full suite and artifact upload.
- Artifact: https://github.com/glad4u7-crypto/project-continue/actions/runs/46111096455/artifacts/15249911064; 285,611 bytes; SHA-256 4f92ff37a94a704af81f898cd4db790f83861a456c90d22c09dbffaa8730865a.
- Draft PR: https://github.com/glad4u7-crypto/project-continue/pull/71 (45 changed files, 4,169 additions, 1 deletion; 128 commits ahead of main at review time).

## Limitations and safety
- PostgreSQL integration/backup tests: 11 skipped because TEST_POSTGRES_* DSNs were not configured. SQLite/local tests are not a substitute for live PostgreSQL acceptance.
- RepositorySnapshot is a host-injected local checkout guard, not a live GitHub Contents API adapter. The host must bind the checkout to the trusted immutable commit SHA.
- No live production data, credentials, deployment, merge or main-branch write occurred.
- PR #71 intentionally remains DRAFT; a human must review and explicitly approve any promotion/merge.
- Branch currently contains the accumulated Phase 20 workstream (45 files), not only this subphase; this scope is called out in the PR body.

## Rollback
- Close draft PR #71 without merging; no main-branch change has occurred.
- If separately approved and later merged, revert the merge commit to roll back.