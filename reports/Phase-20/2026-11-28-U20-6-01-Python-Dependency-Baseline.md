# U20-6-01 — Python and dependency baseline verification

**Date:** 2026-11-28 (Asia/Kolkata)  
**Repository:** `glad4u7-crypto/project-continue`  
**Branch:** `phase20/secure-dispatcher-u20-3-01`  
**Inspection base:** `01d51bd945bb408ae08a04cbc9c0e4efda66f8c5`  
**Status:** PASS — baseline verified; dependency lock absence explicitly recorded

## Evidence

- The Phase 20 ephemeral runner workflow explicitly selects CPython **3.11** through the SHA-pinned `actions/setup-python` action.
- The main CI workflow also selects CPython **3.11** and enables pip caching.
- `requirements.txt` declares runtime and test dependency ranges:
  - `streamlit>=1.39,<2`
  - `python-dotenv>=1,<2`
  - `requests>=2.32,<3`
  - `psycopg[binary]>=3.2,<4`
  - `pytest>=9.0.3,<10`
  - `pytest-cov>=6,<7`
- `pytest.ini` establishes repository-root import path, `tests` discovery, strict markers and the unit/integration/api/database/acceptance marker vocabulary.
- The main CI runs `pip-audit -r requirements.txt`; dependency audit is therefore part of the existing acceptance pipeline.
- No `requirements.lock`, `uv.lock`, `poetry.lock`, `Pipfile.lock` or other fully resolved dependency lock was present in the inspected repository tree.

## Decision and limitation

The verified runtime baseline is CPython 3.11 with the declared dependency ranges above. The repository currently uses bounded version ranges rather than a reproducible full transitive lock. This checkpoint does **not** claim that dependencies are locked or that the exact installed transitive versions were captured. Introducing a lockfile is a separate compatibility change and is not silently included in this baseline checkpoint.

## Acceptance

- Python runtime selected consistently by main CI and the Phase 20 runner: **PASS**
- Dependency declarations and audit mechanism inspected: **PASS**
- Pytest discovery/marker baseline inspected: **PASS**
- Missing full lockfile disclosed without misrepresenting it: **PASS**

**Checkpoint result: U20-6-01 PASS.** No application code, dependency versions, secrets, live services or production data were changed.
