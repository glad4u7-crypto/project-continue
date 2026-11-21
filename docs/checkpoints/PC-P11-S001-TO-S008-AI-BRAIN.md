# Phase 11 Checkpoint Record — PC-P11-S001 through PC-P11-S008

All eight requested checkpoints have implementation and focused offline tests on `feature/phase-11-ai-brain`.

- S001 provider protocol, mock provider and HTTPS OpenAI-compatible adapter.
- S002 opt-in configuration with strict timeout/context bounds; no credential in settings repr.
- S003 project-scoped allow-listed context with deterministic size bounds.
- S004 safe read-only instruction generator; project content is explicitly untrusted.
- S005 deterministic dependency-aware next-task result plus separate AI advice.
- S006 strict JSON-only parser with action allow-list and no tool/action execution.
- S007 one-time explicit approval/rejection gate; approval does not itself mutate application data.
- S008 offline integration tests, no live API key or external network required.

**Evidence state:** implementation committed to feature branch. CI and full repository regression must pass before any checkpoint is marked PASS. Manual Streamlit UI evidence is separate and is not claimed here.
