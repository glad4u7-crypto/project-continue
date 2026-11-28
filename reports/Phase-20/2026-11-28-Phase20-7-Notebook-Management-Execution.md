# Phase 20.7 — Notebook inventory, create, read and isolated execution

- Repository: glad4u7-crypto/project-continue
- Branch: phase20/u20-7-notebook-management
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — 12/12 checkpoints
- Exact tested commit: e7201feecc43789c195f702e95212f2b39e2fb2d
- Dedicated runner: https://github.com/glad4u7-crypto/project-continue/actions/runs/46116960061 — SUCCESS
- Main CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46116960117 — SUCCESS
- Stacked Draft PR: #73 (base: phase20/u20-6-python-test-debug; not merged)

## Implementation

- scripts/phase20_notebooks.py — bounded read-only inventory, nbformat validation, bounded read, recursive secret redaction, exclusive notebook create/read-back.
- scripts/phase20_notebook_policy.py — default-deny path + content SHA-256 + approval ID + exact current commit policy.
- scripts/phase20_notebook_sandbox.py — Docker launcher that checks current Git HEAD and allow-list, runs only a pinned local image ID, and stores bounded/redacted result artifacts.
- docker/phase20-notebook-runner/ — non-root nbclient/ipykernel runner image.
- scripts/phase20_notebook_ci_acceptance.py — real GitHub Actions end-to-end acceptance for a harmless notebook plus timeout and kernel-crash probes.
- schemas/notebooks/execution-allowlist.v1.json — intentionally empty production allow-list.
- tests/test_phase20_notebooks.py, tests/test_phase20_notebook_policy.py, tests/test_phase20_notebook_sandbox.py and tests/fixtures/phase20_safe_notebook.ipynb — automated safety and acceptance tests.

## Checkpoint evidence

| Unit | Result | Acceptance evidence |
|---|---|---|
| U20-7-01 | PASS | Read-only bounded inventory returns relative path, size, SHA-256 and validation state; skips hidden paths and symlinks. |
| U20-7-02 | PASS | UTF-8 JSON object and nbformat 4.0–4.5 enforced; malformed JSON and unsupported versions rejected. |
| U20-7-03 | PASS | Notebook 256 KiB, 200 cells, source 32 KiB/cell, 20 outputs/cell, text 16 KiB/output, metadata depth 8. |
| U20-7-04 | PASS | Exclusive O_CREAT|O_EXCL and O_NOFOLLOW; mode 0600; duplicate and symlink collision never overwrite. |
| U20-7-05 | PASS | Recursive redaction of cell source, text/MIME outputs, tracebacks and metadata; API key, bearer, GitHub token and private-key patterns. |
| U20-7-06 | PASS | Default-deny exact path/content SHA/approval ID/current commit; network, secrets and external mounts must all be false. |
| U20-7-07 | PASS | Disposable non-root Docker kernel, read-only rootfs, no capabilities, no-new-privileges, 512 MiB, 1 CPU, 64 PIDs; no host env or production Drive mount. |
| U20-7-08 | PASS | Docker network=none, kernel timeout 1–120 seconds; actual socket probe denied; infinite-loop timeout probe stopped. |
| U20-7-09 | PASS | Execution counts and outputs preserved; bounded artifact streamed out, redacted, hashed and saved; timeout/kernel-crash artifacts retained. |
| U20-7-10 | PASS | Harmless notebook executed end-to-end on GitHub-hosted runner; valid output read-back, network denied, GITHUB_TOKEN absent. |
| U20-7-11 | PASS | Unlisted malicious notebook, stale commit, mismatched hash, missing approval and unsafe capability flags rejected before Docker. |
| U20-7-12 | PASS | Duplicate name, malformed JSON/nbformat, traversal, symlink, oversized output, timeout and kernel crash tests. |

## Exact-SHA CI results

Dedicated run 46116960061 completed every step successfully:
- Python/dependency baseline and compile: PASS.
- Existing dispatcher focused tests: 85 passed, 52 subtests.
- Phase 20.7 notebook safety suite: 35 passed.
- Isolated notebook image build: PASS.
- Harmless notebook E2E: PASS; artifact read-back valid.
- Network probe: DENIED.
- Secret probe: GITHUB_TOKEN absent in the container.
- Timeout probe: EXPECTED_FAILURE_RETAINED.
- Kernel crash probe: EXPECTED_FAILURE_RETAINED.
- Full regression: 418 passed, 11 skipped, 52 subtests (10.19s).

Main CI run 46116960117 completed successfully:
- Secret scan, dependency audit, Python compile, production container build, Compose validation, smoke test, focused categories, full regression and report upload: PASS.

### E2E artifact evidence

- Runtime Docker image ID: sha256:26e1dc2d290b9be33650860ebd0419c14e673929de9f0b7a6a409613c515716f
- Harmless executed notebook: 1,495 bytes.
- Output artifact SHA-256: 8a4f6724f32cd726cffeb30c93de5484c104dcea75785c07f599cb860a0a81c2
- Network access: false.
- Secrets access: false.
- External mounts: false.
- The CI-only artifact was read back and then removed from the ephemeral checkout; no notebook was written to Drive or production storage.

## Security model and limitations

- The committed production allow-list is empty. Execution is denied unless a trusted operator adds an exact notebook path, SHA-256 and approval ID under review. CI acceptance uses a temporary, short-lived policy entry for the harmless fixture only.
- The notebook runner image is built from python:3.11-slim with nbclient 0.10.2, nbformat 5.10.4 and ipykernel 6.29.5. The mutable base tag is resolved during build; execution is pinned to the immutable image ID recorded above. A fully digest-pinned base image and locked transitive dependency set remain future reproducibility improvements.
- The sandbox receives only the sanitized notebook as a read-only bind mount; no host environment variables, GitHub credentials, production Drive, database, or other user data are mounted. Output is bounded and returned through a 16 MiB tmpfs via stdout.
- This proves the isolated GitHub Actions test runner path, not a live Colab/Drive integration or a production ChatGPT host-adapter invocation. No real user notebook was executed.
- Full regression skipped 11 PostgreSQL DSN-dependent tests; they are not counted as PASS. Ruff remains not installed and optional lint is SKIPPED, not a lint PASS.
- A separate dashboard-health.yml push run failed with no job record; it is not part of the Phase 20.7 acceptance workflow. The dedicated runner and main CI passed on the exact tested SHA.

## Safety and rollback

- Draft PR #73 only; PRs #71 and #72 remain open Drafts.
- No merge, main-branch write, production deployment, Drive mount, database mutation, credential change, file deletion, or live service restart.
- Rollback: close Draft PR #73. No main-branch changes occurred.
