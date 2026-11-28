# U20-3-05 — Authenticated actor and allowed repository validation

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Policy commit: `e061a7b19435b14856b26b6dbee2c109f77f952b`
- Policy: `schemas/dispatcher/authorization-policy.v1.json`
- Read-back blob SHA: `b7b745acd05b4f821fb2f893d1c7787d519779de`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — live connector identity/repository evidence plus versioned fail-closed policy contract

## Live connector evidence

- Authenticated GitHub login lookup: `glad4u7-crypto`, numeric user ID `354281323`.
- Authenticated profile lookup returned the same numeric ID and login nickname.
- Repository metadata lookup: canonical full name `glad4u7-crypto/project-continue`, repository ID `1463557248`, owner ID `354281323`.
- Repository collaborator permission lookup for the authenticated login: `admin` (exceeds the policy minimum `pull`).
- The authenticated identity, repository identity, and permission were obtained from GitHub connector calls, not from the request payload or user-provided text.

## Policy and deterministic checks

- Default decision is reject.
- Exactly one actor is allow-listed by numeric GitHub ID + login + actor type.
- Exactly one repository is allow-listed by numeric repository ID + canonical full_name + owner ID.
- Envelope actor claims must match verified connector identity; claims are not treated as authentication.
- Repository aliases, forks, mismatched IDs/names, missing permissions, identity lookup failures, and commit verification failures fail closed.
- All three fixed tasks require at least `pull` repository permission.
- Deterministic policy contract assertions: 10/10 PASS.
- JSON parse and GitHub read-back: PASS; read-back confirmed exact actor and repository bindings.

## Scope limitation

This proves the current connected GitHub identity and repository permission at audit time, and records the required authorization contract. It does not claim that an application dispatcher currently enforces these checks at runtime. The policy requires exact commit-SHA membership verification before handler lookup; runtime enforcement remains future work. No credential values were read or exposed, and no repository data or live service was modified.

## Disposition

U20-3-05 is PASS for live identity/repository/permission evidence and the versioned authorization contract. Runtime enforcement is explicitly not claimed.
