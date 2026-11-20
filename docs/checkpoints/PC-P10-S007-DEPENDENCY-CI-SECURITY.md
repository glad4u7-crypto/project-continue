# PC-P10-S007 — Dependency and CI Security

**Status:** IN PROGRESS  
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

- Dependency audit result pending.

## Next

After acceptance, proceed to PC-P10-S008 — Production Readiness Acceptance.
