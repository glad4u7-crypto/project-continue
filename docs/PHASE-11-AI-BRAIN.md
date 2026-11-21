# Phase 11 — AI Brain

## Objective
Add provider-agnostic, bounded, read-only AI decision support. Model output is untrusted advice: it cannot run tools, edit tasks, or bypass a human approval decision. Remote AI is opt-in and disabled by default.

## Checkpoints
| ID | Scope | Acceptance evidence | Status |
|---|---|---|---|
| PC-P11-S001 | AI Provider Architecture | Provider protocol, offline mock and OpenAI-compatible adapter | Implemented; CI pending |
| PC-P11-S002 | AI Configuration | Validated opt-in settings, HTTPS endpoint, secret not exposed in settings repr | Implemented; CI pending |
| PC-P11-S003 | Project Context Builder | Project-scoped, allow-listed fields and bounded context | Implemented; CI pending |
| PC-P11-S004 | Instruction Generator | Read-only instruction, context treated as untrusted data | Implemented; CI pending |
| PC-P11-S005 | Next Task Reasoning | Existing deterministic dependency-aware engine retained alongside AI advice | Implemented; CI pending |
| PC-P11-S006 | AI Response Parser | Strict JSON schema, bounded text, fixed action allow-list, no tool execution | Implemented; CI pending |
| PC-P11-S007 | Human Approval | Explicit one-time approval/rejection; approval records intent only | Implemented; CI pending |
| PC-P11-S008 | AI Integration Tests | Offline tests for configuration, provider, context, prompt, parser and approval | Implemented; CI pending |

## Configuration
Set only in the deployment secret manager or local untracked environment:
- AI_ENABLED=false (default)
- AI_PROVIDER=mock or openai_compatible
- AI_MODEL=<provider model>
- AI_BASE_URL=https://<provider endpoint>
- AI_API_KEY=<secret; never commit>
- AI_TIMEOUT_SECONDS=20
- AI_MAX_CONTEXT_CHARS=12000

Remote provider calls require explicit enablement, HTTPS and an API key. Tests use the mock provider and never contact external services.

## Safety boundaries
- AI output is advisory and untrusted.
- The deterministic task engine remains authoritative for dependency readiness and next-task eligibility.
- No automatic task creation, update, completion, shell command, network tool, or GitHub write is permitted.
- Human approval is a separate explicit decision; the current gate is process-memory only and is not a durable audit log.
- The provider adapter supports OpenAI-compatible Chat Completions only; other providers require a separate adapter.
- No real model credential or live provider call is part of CI acceptance.

## Latest CI correction
- Fixed a malformed f-string in `ui/ai_brain.py` discovered by `compileall` on the first CI attempt.
- Re-run full CI against the corrected branch head before merge.

## Local acceptance
```bash
python -m compileall -q services/ai_brain.py tests/test_ai_brain.py
python -m pytest -q tests/test_ai_brain.py
python -m pytest -q
```

Do not mark the phase fully accepted until CI on the phase branch and merged main passes. The approval store's in-memory nature and absence of a live UI are explicit limitations, not production certification.
