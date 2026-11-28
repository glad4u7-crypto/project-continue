# U20-7-07 — Isolated notebook kernel image and runner boundary

**Date:** 2026-11-28 (Asia/Kolkata)  
**Branch:** `phase20/secure-dispatcher-u20-3-01`  
**Exact code SHA:** `ee79824aac866d8f5d83bbd5978365ef312cb283`  
**Acceptance workflow:** [Run 46125899271](https://github.com/glad4u7-crypto/project-continue/actions/runs/46125899271) — SUCCESS

## Implemented

- Added `notebook-sandbox/Dockerfile`, a dedicated Python 3.11 notebook-kernel image, separate from the production Streamlit image.
- Added a separately pinned runtime requirements file: `ipykernel==6.29.5`, `nbclient==0.10.2`, `nbformat==5.10.4`.
- The image creates and runs as non-root UID/GID 10001.
- Added `scripts/notebook_sandbox.py` to build a fixed Docker argv. It mounts only the selected notebook file (read-only) and a caller-provided disposable output directory (writable).
- The command contract applies read-only root filesystem, drops all Linux capabilities, disables privilege escalation, limits PIDs to 64, memory to 512 MiB, CPU to 1, and gives the container a bounded temporary filesystem.
- The command does not pass host environment variables, GitHub tokens, Actions runtime tokens, Google credentials, Drive paths, or production data mounts.
- Added `tests/test_notebook_sandbox.py` and `.github/workflows/notebook-sandbox.yml`.

## Acceptance evidence

Exact SHA `ee79824aac866d8f5d83bbd5978365ef312cb283`, workflow `46125899271`:
- Sandbox command contract tests: PASS.
- Docker image build: PASS.
- Container runtime identity check: UID 10001 confirmed.
- `ipykernel`, `nbclient`, and `nbformat` imports: PASS.
- `pip-audit -r notebook-sandbox/requirements.txt`: PASS.
- Entire Notebook Sandbox Acceptance workflow: SUCCESS.

## Safety boundary and remaining work

- This checkpoint proves the isolated kernel image and command boundary, not execution of a notebook.
- No notebook cell was executed; no Colab, Google Drive, production mount, production secret, or production data was accessed.
- Docker network denial and explicit execution timeout are handled in U20-7-08.
- Cell output/error capture and artifact handling are handled in U20-7-09; harmless end-to-end execution is U20-7-10.
- The current command builder is a fixed argv constructor; it does not itself start Docker. The future trusted runner adapter must call it only after the U20-7-06 identity authorization passes.

**Disposition:** U20-7-07 PASS on the exact SHA above. PR #71 remains draft/unmerged; `main` is unchanged.
