# U20-7-09 — Notebook cell output, traceback and artifact persistence

**Date:** 2026-11-28 (Asia/Kolkata)  
**Branch:** `phase20/secure-dispatcher-u20-3-01`  
**Exact code/test SHA:** `8949e57fc8e6d582dd72e8691aeb9cc943d2c59d`  
**Sandbox acceptance:** [Run 46127711561](https://github.com/glad4u7-crypto/project-continue/actions/runs/46127711561) — SUCCESS

## Implemented

- Added `scripts/notebook_container_runner.py`, which uses the pinned `nbclient`/Jupyter kernel runtime.
- The container runner validates and redacts the input notebook before execution, executes with a 60-second per-cell timeout, and records execution counts and cell error/traceback outputs.
- A cell exception is captured as `cell_error`; the runner preserves the notebook's error output/traceback and emits a bounded summary rather than returning raw source or output text to the host log.
- Executed notebook JSON is revalidated and recursively redacted before artifact creation.
- Artifact metadata includes status, executed code-cell count, error-cell count, byte length and SHA-256.
- Artifact creation uses exclusive create + no-follow semantics, a fixed output filename and a 64 KiB maximum.
- Host `run_sandbox` now verifies the exact checked-out commit, resolves the notebook blob from that commit's Git tree/object database, and stages those exact immutable blob bytes as the sole read-only host mount.
- Container output now lives on a 1 MiB no-exec tmpfs, not a writable host bind mount. The runner streams the redacted artifact as a bounded base64 stdout record before Docker auto-removes the container; the host decodes only that fixed record, validates/redacts the notebook again, verifies artifact length/SHA-256, then writes a unique exclusive artifact in the requested output directory. This avoids relying on stopped-container tmpfs persistence or a writable host output mount.
- The sandbox no longer relies on checkout working-tree bytes for notebook identity, avoiding line-ending/filter differences.

## Tests and exact-SHA evidence

Workflow `46127711561` checked out exact SHA `8949e57fc8e6d582dd72e8691aeb9cc943d2c59d`:
- Sandbox unit/host orchestration tests: **12 passed**.
- Git tree/blob identity resolution: PASS.
- Host artifact copy, validation, exclusive persistence, execution count and traceback preservation tests: PASS.
- Docker image build and non-root UID 10001 runner import: PASS.
- Live network-denial probe: PASS.
- Runtime dependency audit: no known vulnerabilities.
- Entire Notebook Sandbox Acceptance workflow: SUCCESS.

## Safety boundary

- This checkpoint adds and tests the execution/artifact path but does **not** execute the real recovery notebook or any production notebook.
- Host-side artifact orchestration is tested with a mocked Docker process. The actual container runner is built and imported in CI; a harmless notebook must execute end-to-end in U20-7-10 before claiming live notebook execution acceptance.
- Container output storage is capped by a 1 MiB tmpfs; the final notebook artifact is capped at 64 KiB.
- No Colab, Google Drive, production mounts, production secrets or production data were accessed.

## Subsequent hardening verified by U20-7-10

The artifact handoff was refined from docker-cp retrieval to bounded stdout streaming so the 1 MiB output tmpfs can remain ephemeral and the container can use automatic removal. Exact-SHA workflow `46129247588` on `742280ca80160d52f28bbe27c74c1430027a063c` passed 20 sandbox/policy tests and executed the harmless fixture end-to-end; artifact size and SHA-256 checks passed. See `2026-11-28-U20-7-10-Harmless-Notebook-E2E.md`.

**Disposition:** U20-7-09 PASS. Its artifact handoff refinement is also verified by U20-7-10. PR #71 remains draft/unmerged; `main` is unchanged.
