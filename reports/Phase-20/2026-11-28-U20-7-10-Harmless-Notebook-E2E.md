# U20-7-10 — Harmless notebook real end-to-end execution

**Date:** 2026-11-28 (Asia/Kolkata)  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code/test SHA:** 742280ca80160d52f28bbe27c74c1430027a063c  
**Acceptance:** [Notebook Sandbox Acceptance run 46129247588](https://github.com/glad4u7-crypto/project-continue/actions/runs/46129247588) — SUCCESS

## Test performed

A dedicated, explicitly allow-listed fixture at tests/fixtures/notebooks/harmless_execution.ipynb was executed inside the actual Docker sandbox. It contains only local arithmetic and short stdout statements; it does not access files outside the sandbox, network services, Colab, Google Drive, tokens or production data.

- The host resolved the exact checked-out commit and Git tree blob, then staged those immutable blob bytes as the only read-only host bind mount.
- Docker ran as UID/GID 10001, with read-only root filesystem, all capabilities dropped, no-new-privileges, 1 CPU, 512 MiB memory, 64 PIDs, 64 MiB /tmp, 1 MiB output tmpfs and --network=none.
- Two code cells executed successfully.
- Execution counts 1 and 2 were retained.
- Output text SANDBOX_E2E_OK 42 and SECOND_CELL_OK 42 was retained in the executed notebook artifact.
- The redacted artifact was streamed through bounded stdout before the auto-removed container exited; host-side validation, byte count and SHA-256 checks passed, then it was written with exclusive/no-follow semantics.
- The artifact was uploaded to the workflow as notebook-sandbox-e2e-artifact with seven-day retention.

## Exact-SHA evidence

Run 46129247588 checked out 742280ca80160d52f28bbe27c74c1430027a063c:
- Sandbox + execution-policy tests: **20 passed**.
- Docker image build: PASS.
- Non-root UID 10001 and explicit python3 kernelspec: PASS.
- Live external-network denial probe: PASS.
- Runtime dependency audit: no known vulnerabilities.
- End-to-end notebook: NOTEBOOK_E2E: PASS.
- Executed code cells: **2**.
- Artifact bytes: **1,408**.
- Artifact SHA-256: 572323e7034c518ca8ef2b3425ef393240a45c83797f5c845cf6de6ec5c8cbe1.
- Artifact upload: SUCCESS.

## Safety boundary

Only the harmless fixture was executed. The real notebooks/ProjectContinue-Recovery.ipynb was not executed. No Colab/Drive access, production mount, secret, credential, external network access or production data was used.

**Disposition:** U20-7-10 PASS. U20-7-11 and U20-7-12 remain NOT STARTED. PR #71 remains draft/unmerged; main is unchanged.
