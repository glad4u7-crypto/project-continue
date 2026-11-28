# Phase 20.3 — U20-3-03 Fixed task registry and strict argument schemas

- **Timestamp:** 2026-11-28 (Asia/Kolkata)
- **Repository:** `glad4u7-crypto/project-continue`
- **Branch:** `phase20/secure-dispatcher-u20-3-01`
- **Registry manifest commit:** `85ef0a1500be90e1ff62de5ad89d23b7c6cc7d43`
- **Registry schema commit:** `2564fdfc82b09d022e7a313283ba235e3ab65932`
- **Manifest:** `schemas/dispatcher/task-registry.v1.json`
- **Manifest read-back blob SHA:** `4336220c3002e81a6f440c6152d0ffe534d564c6`
- **Schema:** `schemas/dispatcher/task-registry.v1.schema.json`
- **Schema read-back blob SHA:** `2b8b79377e44099866047329edfa285e6d197012`

## Result

**PASS — fixed allow-list and per-task strict argument contracts are committed and read back.**

The v1 registry contains exactly three task IDs:

| Task ID | Handler reference | Risk | Argument contract |
|---|---|---|---|
| `repo.read_file` | `repo.read_file.v1` | read_only | Required relative `path`; bounded length and traversal/backslash exclusions |
| `repo.list_tree` | `repo.list_tree.v1` | read_only | Optional safe relative `path`; no other arguments |
| `tests.run_pytest` | `tests.run_pytest.v1` | test_only | `scope` is only `full` or `focused`; focused requires `test_path` matching `tests/test_*.py`; full forbids `test_path` |

Every task argument schema is an object with `additionalProperties: false`. The registry manifest itself has a separate Draft 2020-12 schema with a closed top-level object and fixed registry version. Handler references are symbolic identifiers, not dynamic imports or command strings.

No task is registered for arbitrary shell, Python, SQL, free-form command, arbitrary workflow dispatch, URL fetch, or arbitrary pytest flags.

## Verification

Both committed files were fetched back from the feature branch and parsed as JSON. A deterministic contract-inspection harness performed **16/16 PASS** checks:
- both JSON documents parse;
- registry version and exact task-ID allow-list;
- duplicate/unknown command-style task exclusion;
- fixed handler reference shape;
- closed argument objects;
- required/optional path behavior;
- pytest scope enum and conditional path rules;
- focused test path pattern;
- closed top-level manifest schema;
- both read-back blob SHA values.

## Scope and limitations

This is a declarative registry/contract checkpoint only. No JSON Schema validator package was installed or run; the 16 checks are deterministic assertions over the fetched JSON, not a full standards-validator execution. No handler implementation, task dispatch, shell/Python/SQL execution, pytest execution, workflow dispatch, credentials, production data, or live service was used. Handler availability and runtime enforcement remain future checkpoints. The registry does not make the three handlers executable by itself.

No merge to main.
