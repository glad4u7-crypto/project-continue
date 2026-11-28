# U20-7-02 to U20-7-04 — Notebook structure, bounds and safe creation

**Date:** 2026-11-28 (Asia/Kolkata)  
**Repository:** `glad4u7-crypto/project-continue`  
**Verified branch HEAD:** `88c9d1d829f5c6d5c15a959211b5bf6caec1955f`  
**CI:** [Project Continue CI run 46123632152](https://github.com/glad4u7-crypto/project-continue/actions/runs/46123632152) — SUCCESS  
**Result:** PASS — U20-7-02, U20-7-03 and U20-7-04

## Issue detected and safe correction

The repository notebook `notebooks/ProjectContinue-Recovery.ipynb` declared nbformat 4.5 but its five cells did not contain the required cell `id` values. The file was patched on the feature branch only, adding deterministic IDs `pc-recovery-01` through `pc-recovery-05`. Cell source, metadata and existing empty outputs were preserved. New notebook blob SHA: `544c131c97101485c4f328f83de1f96e65162dad`.

No notebook cell was executed.

## Checkpoint evidence

| Unit | Result | Evidence |
|---|---|---|
| U20-7-02 JSON and nbformat validation | PASS | Added `scripts/notebook_validation.py`; strict UTF-8 JSON parsing, nbformat major 4 and supported minor 0–5 validation, nbformat 4.5 cell-ID requirement, duplicate-ID rejection. Current repository notebook passes validation. |
| U20-7-03 cell, metadata, size and output bounds | PASS | Validator enforces object metadata, markdown/code/raw cell types, string source, 32 KiB per-cell source, 64 KiB notebook, maximum 200 cells, maximum 100 outputs per code cell, output-type structure and execution-count shape. Malformed/unhashable values and invalid Unicode fail closed. |
| U20-7-04 exclusive create and no-overwrite | PASS | Existing `scripts/colab_notebook_creation.py` uses `O_CREAT | O_EXCL` and `O_NOFOLLOW`; `tests/test_colab_notebook_creation.py` covers existing target preservation, symlink destination/collision, invalid names and successful JSON read-back. The full CI run executed the repository test suite successfully. |

## Automated tests

- Added `tests/test_notebook_validation.py` with 11 tests, including current notebook read/validation, malformed JSON/UTF-8, unsupported nbformat, missing/duplicate IDs, invalid cell/metadata/source, output and size limits, invalid schema types, and invalid Unicode.
- Exact-head main CI run [46123632152](https://github.com/glad4u7-crypto/project-continue/actions/runs/46123632152): **402 passed, 11 skipped, 52 subtests passed**; compile, dependency audit, production container build/smoke and full regression completed successfully.
- The 11 skips are PostgreSQL DSN-gated tests in the non-PostgreSQL main job; separate PostgreSQL integration was not required for this notebook validation checkpoint.

## Scope and safety boundaries

- Inventory is repository-only; no Google Drive or Colab connection was used.
- Notebook code was not executed.
- No notebook was uploaded, deleted or overwritten.
- The existing starter notebook creation path remains explicit-destination only and non-overwriting.
- Earlier failed run on an intermediate commit exposed an incorrectly escaped invalid-Unicode test fixture; the fixture was corrected before the exact-head successful run. Failed evidence remains in Actions history and is not counted as PASS.

**Checkpoint results:** U20-7-02 PASS; U20-7-03 PASS; U20-7-04 PASS.