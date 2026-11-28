# U20-7-11 — Malicious and unauthorized notebook rejection

**Date:** 2026-11-28 (Asia/Kolkata)  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code/test SHA:** 50508d093f0a7c084d403ce7d6a242cc6a7d908c  
**Acceptance:** [Notebook Sandbox Acceptance run 46129560191](https://github.com/glad4u7-crypto/project-continue/actions/runs/46129560191) — SUCCESS

## Controls and tests

- The host execution gate rejects any notebook path not in the explicit allow-list, including path traversal and absolute-path substitutions.
- The request commit SHA must equal the trusted checked-out commit; the requested blob SHA and resolved commit-tree blob must match the pinned path/blob pair.
- The host reads the exact Git object bytes and stages them read-only; a working-tree file cannot substitute different content.
- Symlink notebook inputs are rejected before command construction.
- A malicious unallow-listed notebook fixture contained code that would write a marker file if executed. The test confirmed authorization failed, Docker Popen was never called, and the marker file was never created.
- The test suite also covers wrong/missing request fields, untrusted commit identity, changed blob identity, path traversal, and container-name option injection.
- The only notebook executed by the acceptance workflow remains the separate harmless arithmetic fixture.

## Exact-SHA evidence

Run 46129560191 checked out 50508d093f0a7c084d403ce7d6a242cc6a7d908c:
- Sandbox and execution-policy tests: **22 passed**.
- Docker image build and non-root UID 10001/kernel-spec checks: PASS.
- Live external-network denial: PASS.
- Runtime dependency audit: no known vulnerabilities.
- Harmless fixture E2E rerun: NOTEBOOK_E2E: PASS; 2 code cells; 1,408-byte redacted artifact uploaded.
- Entire Notebook Sandbox Acceptance workflow: SUCCESS.

## Safety boundary

The malicious notebook was rejected before Docker launch; its code was not executed. No recovery notebook, Colab, Google Drive, production mount, credential or production data was accessed.

**Disposition:** U20-7-11 PASS. U20-7-12 remains NOT STARTED. PR #71 remains draft/unmerged; main is unchanged.
