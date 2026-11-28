# Phase 20.9 — Streamlit and Chromium Browser Acceptance

- Date: 2026-11-28 (Asia/Kolkata)
- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/u20-9-streamlit-browser-acceptance`
- Exact acceptance SHA: `b046d23403ebf59f1966bb47af7124caaa0b04bb`
- Dedicated fixed-task runner: [46121735439](https://github.com/glad4u7-crypto/project-continue/actions/runs/46121735439) — SUCCESS
- Main CI: [46121735454](https://github.com/glad4u7-crypto/project-continue/actions/runs/46121735454) — SUCCESS
- Browser evidence artifact: [phase20-streamlit-browser-evidence](https://github.com/glad4u7-crypto/project-continue/actions/runs/46121735439/artifacts/15253188930) (artifact ID 15253188930; 7-day retention)
- Full regression: 435 passed, 11 skipped (PostgreSQL DSN-dependent), 52 subtests passed.
- Focused dispatcher acceptance: 85 passed, 52 subtests passed.
- No production service, live database, external credential, or Google Drive mount was touched.

## Browser acceptance coverage

The dedicated workflow pins the browser runner to Ubuntu 24.04 for supported Playwright Chromium installation and executes a real headless Chromium browser against an isolated Streamlit process.

1. Isolated temporary SQLite database and isolated local Streamlit process.
2. `/_stcore/health` returns HTTP 200.
3. ImportError and ModuleNotFoundError startup probes are captured from process logs and surfaced through the health-wait diagnostic.
4. Real Chromium document load and browser smoke checks.
5. Production login gate blocks the dashboard before authentication; a test-only bootstrap operator can sign in. Credentials and signing key are ephemeral test values and are never printed or persisted in evidence.
6. Project create, read and update via browser.
7. Task create, update and completion via browser. Dependency prerequisite/cycle/project-scope rules are covered by full-regression service tests:
   - `tests/test_task_management.py::test_dependency_completion_gate_and_removal`
   - `tests/test_task_management.py::test_dependency_cycles_and_project_scope`
8. GitHub integration panel renders its explicit empty-configuration state without injecting a token. API/network error sanitization is covered by `tests/test_github_integration.py`; no live GitHub API call is made by this browser run.
9. Restart the Streamlit process against the same temporary database; the project and task remain present.
10. Every isolated app process is stopped in `finally` cleanup and verified exited.
11. Browser screenshots and a JSON acceptance manifest are uploaded as the GitHub Actions artifact above.

## Acceptance output

```text
PHASE20_STREAMLIT_BROWSER_ACCEPTANCE=PASS
health_endpoint=HTTP_200
startup_import_dependency_error_capture=PASS
browser=Chromium
project_create_read_update=PASS
task_create_update_complete=PASS
task_dependency_service_tests=PASS
github_panel_empty_state=PASS
restart_persistence=PASS
production_login_gate=PASS
isolated_process_cleanup=PASS
external_credentials=NOT_INJECTED
live_database_or_service=NOT_TOUCHED
```

## Corrected CI failures retained

- Playwright 1.56 does not support the runner's then-current Ubuntu 26.04 image. The dedicated runner is pinned to Ubuntu 24.04.
- Streamlit expander controls are `summary` elements, not buttons; browser selectors were corrected.
- The production login harness needed explicit ephemeral signing key and bootstrap admin values.
- Browser field labels such as `Name`, `Title`, and `Password` were made exact to avoid matching help buttons and visibility toggles.
- Streamlit rerender animations can leave submit buttons unstable; the harness now waits for form visibility and uses a forced click only on explicit submit/action controls.
- Expander state is preserved across reruns by checking the nearest `details` element before toggling.
- Browser task dependency UI automation proved brittle because the app rerendered and collapsed the selected task context; dependency semantics are instead verified by dedicated service tests in the full regression. The report does not claim browser-level dependency interaction.

All failed attempts remain visible in Actions history; the final success is on the exact SHA above.

## Limitations

- GitHub panel browser test intentionally exercises the no-repository/no-token empty state, not a live authenticated GitHub request. API error/timeout sanitization is covered by unit tests; loading-spinner timing is not separately asserted.
- PostgreSQL tests remain skipped without dedicated DSNs and are not counted as PASS.
- Optional Ruff lint remains SKIPPED when Ruff is not installed.
- Evidence artifact retention is 7 days per free GitHub Actions artifact policy; the durable report and acceptance code remain in the repository.
- This is a test harness acceptance, not deployment or proof of public Streamlit hosting availability.

## Unit checkpoint dispositions

| Unit | Result | Evidence |
|---|---|---|
| U20-9-01 | PASS | Isolated temporary SQLite DB and app process |
| U20-9-02 | PASS | HTTP 200 from `/_stcore/health` |
| U20-9-03 | PASS | ImportError and ModuleNotFoundError log-capture probes |
| U20-9-04 | PASS | Real headless Chromium harness |
| U20-9-05 | PASS | Production login gate and ephemeral test admin sign-in |
| U20-9-06 | PASS | Browser project create/read/update |
| U20-9-07 | PASS | Browser task create/update/complete plus dependency service regression tests |
| U20-9-08 | PASS | GitHub panel empty state; API/network error sanitization unit tests; no live token/API call |
| U20-9-09 | PASS | Process restart preserves project/task in the same isolated DB |
| U20-9-10 | PASS | Three isolated processes stop and exit; no live app/database touched |
| U20-9-11 | PASS | Screenshot set and JSON manifest uploaded; exact SHA and Actions run recorded |

## Exit decision

Phase 20.9 is 11/11 PASS. Browser-level task dependency selection and live GitHub API loading/error states are explicitly outside the browser proof; their service behavior is covered by existing unit tests, and no unsupported claim is made.
