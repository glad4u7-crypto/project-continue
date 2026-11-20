# PC-P10-S007 — Dependency and CI Security

**Status:** PASS  
**Phase:** 10 — Production Readiness & Security

## Implemented controls

- CI runs Gitleaks secret scanning before application setup and tests.
- CI now installs `pip-audit` in the runner and audits the dependency set declared by `requirements.txt`.
- The workflow grants only repository contents read access and the security-events permission required by the secret scanning action.
- Existing compile, focused test categories, full regression suite and coverage reporting remain in place.

## Acceptance criteria

- Gitleaks completes successfully.
- `pip-audit -r requirements.txt` reports no known vulnerable dependencies.
- The workflow's full test and coverage steps pass.
- No production credentials are required by CI.

## CI evidence

- Gitleaks: **PASS** — no leaks found.
- pip-audit 2.10.1: **PASS** — no known vulnerabilities found after upgrading pytest to 9.2.0 (patched range ≥9.0.3).
- GitHub Actions run #245: **SUCCESS** — pinned actions, dependency audit, compile, focused tests, full suite and report upload passed.
- Pull request CI #251 exposed a shallow-checkout limitation in Gitleaks range scanning. The workflow now fetches full Git history.
- Pull request CI run #264: **SUCCESS** on the latest PR head; Gitleaks full-range scan, pip-audit, compilation, focused tests, full suite and coverage upload passed.
- Full suite: **161 passed**; statement coverage **95%** (821 statements; 39 uncovered).

## Next

After acceptance, proceed to PC-P10-S008 — Production Readiness Acceptance.
