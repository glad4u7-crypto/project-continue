# U20-3-04 — Natural-language execution prohibition

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Policy commit: `eb2307694a64bcb6c2aac967b4d223941b8ecb4d`
- Policy path: `schemas/dispatcher/natural-language-execution-policy.v1.json`
- Read-back blob SHA: `6459a285c569988603702c3b4238f7483e0eb517`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — declarative policy and contract checks only

## Implemented contract

The versioned policy defaults to reject and contains ten explicit rules. Natural-language text is never executable input to shell, Python, SQL, eval/exec, subprocess, workflow commands, or notebook cells. An intent resolver may only propose a fixed registry task ID and structured JSON arguments. Unknown or ambiguous intent fails closed. Arguments must be checked against the selected task's closed schema. Caller-supplied source, command strings, SQL, arbitrary flags, and dynamic handler names are forbidden. Actor, repository, immutable SHA, expiry and authorization checks are prerequisites. Only fixed reviewed handler references may be resolved. Destructive or external side effects require a separate approval gate.

## Evidence and checks

- Deterministic policy contract assertions: 10/10 PASS.
- JSON parsed after GitHub write and read-back: PASS.
- Read-back confirmed exactly 10 policy rules and fail-closed default: PASS.
- Existing fixed registry IDs cross-checked: `repo.read_file`, `repo.list_tree`, `tests.run_pytest`.

## Scope limitation

This checkpoint establishes a versioned policy contract; it does not claim runtime enforcement. No dispatcher/handler implementation exists in this unit's evidence, and no pytest or GitHub Actions run was executed because the current connector does not expose workflow dispatch. Runtime enforcement and CI tests remain required in subsequent implementation/integration checkpoints. No shell, Python, SQL, notebook, production data, or live service was executed or modified.

## Disposition

U20-3-04 is PASS for the policy artifact and deterministic contract/read-back evidence. Runtime enforcement is explicitly not claimed.
