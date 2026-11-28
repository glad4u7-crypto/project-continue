# U20-7-06 — Notebook execution allow-list and immutable identity binding

**Date:** 2026-11-28 (Asia/Kolkata)  
**Branch:** `phase20/secure-dispatcher-u20-3-01`  
**Code/test commit:** `df891cdc960b360b40e9b61da1bbd0af375830f9`  
**Acceptance workflow:** [Run 46125535699](https://github.com/glad4u7-crypto/project-continue/actions/runs/46125535699) — SUCCESS

## Implemented

- Added `scripts/notebook_execution_policy.py`.
- The only allow-listed path is `notebooks/ProjectContinue-Recovery.ipynb`.
- Its reviewed Git blob identity is pinned to `544c131c97101485c4f328f83de1f96e65162dad`.
- The request must contain exactly `notebook_path`, `commit_sha`, and `blob_sha`; extra or missing fields fail closed.
- The commit must be a full 40-character SHA and equal the trusted checkout SHA supplied by the checkout adapter. Branch names and abbreviated SHAs are rejected.
- The requested path must be canonical, repository-relative, allow-listed, and equal the path resolved by the trusted adapter.
- Both the requested blob SHA and the resolved blob SHA must match the pinned reviewed notebook identity.
- The module only authorizes identity; it does not launch a kernel, execute notebook cells, access Drive, or read secrets.

## Tests and evidence

Added `tests/test_notebook_execution_policy.py` covering:
- Exact allow-listed notebook + exact checkout binding.
- Unlisted path, absolute path and path traversal rejection.
- Mutable/abbreviated/mismatched commit rejection.
- Changed or mismatched blob rejection.
- Missing/extra request fields and non-object request rejection.

Exact code SHA `df891cdc960b360b40e9b61da1bbd0af375830f9`:
- Secret scan, dependency install, Python compile and runner safety contract: PASS.
- Fixed-task acceptance workflow `46125535699`: SUCCESS.
- Full regression suite in that workflow: **411 passed, 11 skipped, 52 subtests passed**.
- The 11 skips are PostgreSQL DSN-gated in the runner workflow; a separate PostgreSQL integration workflow was also triggered for this exact SHA and is tracked independently.

## Limitations / safety boundary

- The checkout adapter must obtain the checked-out commit SHA and resolved notebook path/blob SHA from trusted checkout metadata; untrusted request fields are never treated as those trusted values.
- Any notebook content change requires an explicit reviewed update to the pinned blob SHA and tests.
- This checkpoint does not prove notebook execution. Execution isolation, network denial, output capture and end-to-end execution remain later U20-7 checkpoints.
- No Colab, Google Drive mount, production data, notebook execution, or paid service was used.

**Disposition:** U20-7-06 PASS on the exact code/test SHA above. No merge to `main`; PR #71 remains draft/unmerged.


## Subsequent test-only allow-list extension

For U20-7-10, the policy was extended with one additional exact path/blob pair for the harmless arithmetic-only fixture at tests/fixtures/notebooks/harmless_execution.ipynb. It is separately pinned to Git blob b62de83fd65d7faa0713ce52b8c87b4741ed9832 and covered by the execution-policy test. No other notebook path was added. The real recovery notebook remains unexecuted.
