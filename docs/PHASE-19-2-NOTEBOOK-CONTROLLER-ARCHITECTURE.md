# Phase 19.2 — Colab Notebook Controller Architecture

Status: DESIGN BASELINE (implementation not yet enabled)
Target branch: `feature/phase-18-free-control-plane`
Constraint: free-tier and open-source components only.

## 1. Purpose and boundary

Phase 19.2 defines the architecture for controlling Google Colab notebooks through the existing GitHub Issue #59 command bridge. It does not yet discover, create, edit, or execute notebooks; those capabilities belong to later Phase 19.x gates.

The existing Phase 18 bridge remains the control-plane transport. Its fixed diagnostic commands and read-only allowlist must continue to work. Notebook operations are a separate, explicitly allow-listed capability set and must not become arbitrary shell execution.

## 2. Logical components

1. **ChatGPT command interface** — expresses an approved operation as a strict, versioned request; displays returned status, output, and errors.
2. **GitHub Issue queue (Issue #59)** — transports requests and replies. It is not the source of truth for notebook contents.
3. **Colab Control Agent** — authenticates using the existing Colab Secret, validates request author/schema/operation/arguments, enforces idempotency, and dispatches only approved handlers.
4. **Notebook Controller** — owns notebook discovery, metadata inspection, creation, and notebook-level lifecycle operations. It must use supported Colab/Jupyter interfaces and a bounded workspace.
5. **Cell Controller** — owns cell listing, safe source inspection, insertion, and editing. It must preserve cell order and stable cell identifiers where available.
6. **Execution Controller** — executes only explicitly selected cells after a separate execution authorization check; captures execution state, outputs, and exceptions.
7. **Result Reporter** — serializes bounded, redacted results back to the GitHub queue for ChatGPT to inspect.
8. **State Store** — persists queue cursor, processed request IDs, operation status, and recovery metadata outside the repository. Writes are atomic and concurrency-safe.

## 3. Request lifecycle

`RECEIVED → VALIDATED → AUTHORIZED → RUNNING → SUCCEEDED | FAILED | INTERRUPTED`

- Reject malformed, unknown-version, unauthorized-author, oversized, or unknown-operation requests before dispatch.
- Assign every request a unique request ID. A repeated ID must return the prior recorded outcome and must not repeat a side effect.
- Record `RUNNING` before dispatch and persist the terminal result before posting a reply.
- If a runtime stops during execution, mark the operation `INTERRUPTED`; do not silently replay potentially non-idempotent work.
- Replies include request ID, operation, notebook/cell identifiers when applicable, status, elapsed time when available, and bounded output/error details.
- Never include tokens, environment values, notebook secrets, or unredacted credential-like strings in logs or replies.

## 4. State and concurrency model

The existing Phase 18 state currently contains only `last_comment_id`. Phase 19 must extend it compatibly rather than discard or reset it.

Proposed versioned state shape:

```json
{
  "schema_version": 1,
  "last_comment_id": 7207815863,
  "processed_requests": {},
  "active_operation": null,
  "updated_at": null
}
```

Implementation requirements:
- Missing `schema_version` is treated as the legacy Phase 18 shape and migrated in memory without losing `last_comment_id`.
- Use an exclusive process lock around poll/dispatch/state mutation so concurrent Colab agent instances cannot process the same request simultaneously.
- Use atomic temp-file replacement for state writes, with restrictive file permissions where supported.
- Persist a request as claimed before performing a side effect; persist its result before publishing a reply.
- Keep a bounded processed-request history and define safe pruning without moving the queue cursor backwards.
- A lock conflict must cause a clear “another agent is active” response and a clean exit, not a second poll loop.

## 5. Notebook and cell safety boundaries

- Operate only inside an explicitly configured notebook workspace; reject path traversal and symlink escapes.
- Notebook discovery and reading are read-only.
- Notebook creation must use a deterministic, collision-resistant name and must never overwrite an existing notebook.
- Cell edits require an explicit notebook ID, cell ID/index, and complete replacement/insertion payload; retain a recoverable pre-edit copy.
- Execution is a distinct operation from editing. Editing a cell must never implicitly execute it.
- Execution requires an explicit notebook ID and cell selection; no implicit “run all” operation.
- Apply configurable execution timeout and output-size limits; return truncation metadata.
- Do not expose raw shell, arbitrary subprocess, unrestricted filesystem, secrets, or runtime-management operations through the command schema.

## 6. Module boundaries

Planned implementation boundaries (names are provisional until code review):

- `scripts/colab_control_agent.py`: transport, authentication, request validation, polling, lock, state and dispatch only.
- `scripts/colab_notebook_controller.py`: notebook discovery, metadata, creation, and bounded file access.
- `scripts/colab_cell_controller.py`: cell inspection and mutation with backup/validation.
- `scripts/colab_execution_controller.py`: explicit cell execution and output/error capture.
- `scripts/colab_control_models.py`: versioned request/result schemas and validation.
- `tests/test_colab_*`: isolated unit tests with mocked Colab/GitHub boundaries; no credentials or live notebook required for unit tests.

The implementation may consolidate modules only if the same security and test boundaries remain clear.

## 7. Phase gates and evidence

- **19.3:** two-way command bridge schema, authorization, request IDs, idempotency and duplicate-delivery tests.
- **19.4–19.6:** notebook discovery, creation, read/inspect with real Colab evidence.
- **19.7–19.9:** cell mutation, execution, output and exception round-trip.
- **19.10–19.12:** bounded file control, runtime monitoring, interruption/recovery.
- **19.13–19.14:** Streamlit integration and security/permission tests.
- **19.15:** end-to-end acceptance: create a real notebook, execute `print("Hello from Colab")`, return exact output to ChatGPT, and verify persisted status.

A phase is not PASS from syntax checks alone. Each gate requires relevant automated tests plus real Colab/GitHub evidence where the capability crosses those boundaries.

## 8. Current known risks carried forward

- Phase 18 has no process-level poll lock. Duplicate replies were observed for some request comments; a current process check returned zero running agent processes, which does not rule out overlapping processes at the time of those duplicates.
- The existing state file was observed to exist and contain `last_comment_id`; its current recorded value is `7207815863`.
- The working tree previously reported untracked `streamlit_phase18.log`. Preserve it; do not delete, overwrite, or stage it as part of Phase 19 work.
- The current command allowlist does not provide notebook operations. Do not claim notebook control until later phases implement and verify it.

## 9. Free-tier constraints

Use the existing Colab runtime, GitHub Issue API, Python standard library, and already-installed/open-source packages. No paid hosting, paid API, paid automation service, or new paid dependency is permitted. Colab runtime availability and GitHub API rate limits remain external constraints; the agent is not always-on.
