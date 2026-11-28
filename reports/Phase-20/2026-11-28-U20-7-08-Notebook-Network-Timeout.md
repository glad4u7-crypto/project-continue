# U20-7-08 — Network default-deny and bounded notebook execution

**Date:** 2026-11-28 (Asia/Kolkata)  
**Branch:** `phase20/secure-dispatcher-u20-3-01`  
**Exact code/test SHA:** `d14e05366c266b661fe5032f23e70da469b44977`  
**Sandbox acceptance:** [Run 46126268550](https://github.com/glad4u7-crypto/project-continue/actions/runs/46126268550) — SUCCESS

## Implemented

- Every sandbox invocation now includes Docker `--network=none`; the container cannot reach external network services.
- Added a fixed 120-second maximum execution deadline. Callers may choose a shorter timeout (minimum 1 second) but cannot raise the maximum.
- Timeout handling kills the Docker client process group, then explicitly issues `docker kill` and `docker rm --force` for the uniquely named container.
- Docker stop grace is capped at 5 seconds.
- Docker client stdout/stderr are written to temporary files under a 64 KiB + 1 byte file-size limit; returned text is capped at 64 KiB per stream and truncation is reported.
- Container names are generated and validated against a strict fixed pattern; caller-supplied option injection is rejected.
- Mount paths reject comma/newline characters to prevent Docker `--mount` argument ambiguity.

## Tests and exact-SHA evidence

Workflow `46126268550` checked out exact SHA `d14e05366c266b661fe5032f23e70da469b44977`:
- Sandbox tests: **8 passed**.
- Docker image build: PASS.
- Non-root UID 10001 and pinned kernel package import: PASS.
- Live Docker `--network=none` external connection probe: **NETWORK_DENIAL: PASS**.
- Notebook runtime dependency audit: PASS.
- Entire Notebook Sandbox Acceptance workflow: SUCCESS.

Timeout unit test verifies that an expired process is killed as a process group and that the named container cleanup path is invoked. The workflow did not run a long-running notebook fixture to trigger a real timeout; that remains a later end-to-end acceptance case.

## Safety boundary

- No notebook cell was executed; no Colab/Google Drive access, production mount, production secret, or production data was used.
- This proves network isolation and timeout mechanics for the fixed sandbox command. It does not yet implement cell-by-cell output/result artifact persistence (U20-7-09) or a harmless notebook end-to-end run (U20-7-10).
- The Streamlit browser acceptance selector flake was separately fixed on the same SHA; Dashboard Browser Acceptance run `46126268639` succeeded, covering CRUD/persistence and read-only self-check.

**Disposition:** U20-7-08 PASS on the exact code/test SHA above. PR #71 remains draft/unmerged; `main` is unchanged.
