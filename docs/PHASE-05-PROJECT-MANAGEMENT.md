# Phase 05 — Project Management

**Phase objective:** deliver a usable project registry and lifecycle workspace on top of the Phase 04 SQLite persistence layer.

**Planning provenance:** the available project history establishes the phase title and an eight-checkpoint structure, but the repository does not currently contain the original master roadmap or the authoritative Phase 05 checkpoint names. The implementation workstreams below are therefore a traceable working decomposition, not a claim that these labels reproduce the missing master document. Reconcile names/IDs with the canonical master plan when it is restored.

## Working checkpoint decomposition (provisional labels)

| Workstream | Scope | Acceptance evidence |
|---|---|---|
| PC-P05-S001 | Project creation service | generated stable ID, validation, persistence, creation activity, rejection tests |
| PC-P05-S002 | Project registration UI | form submission, success/error feedback, duplicate/invalid handling |
| PC-P05-S003 | Project registry | active/all/archived filters, text search, empty state |
| PC-P05-S004 | Project details | metadata, task summary, activity history |
| PC-P05-S005 | Project editing | validated name/description update, persisted activity |
| PC-P05-S006 | Project archive/restore | reversible lifecycle, idempotency, no destructive deletion |
| PC-P05-S007 | Project progress | status counts and completion percentage derived from tasks |
| PC-P05-S008 | Integration and acceptance | automated tests, full suite, CI and runtime workflow evidence |

## Architecture

- Persistence remains in database/ProjectRepository; Phase 05 does not duplicate SQL or alter the Phase 04 schema.
- Use cases and read models live in services/ProjectManagementService.
- Streamlit rendering lives in ui/project_management.py.
- The default database path is .data/project_continue.sqlite3; PROJECT_CONTINUE_DB may override it.
- Project archive is reversible. The UI does not expose hard deletion.
- Progress is done tasks / all tasks * 100; projects with no tasks report 0%.
- Activity events are written for create, update, archive and restore actions.

## Acceptance gates

1. Project creation validates names/descriptions and persists generated or supplied identifiers.
2. Project search is case-insensitive and searches name plus description.
3. Status filters accept only all, active, or archived.
4. Details include task counts, task status breakdown, progress and the latest 25 activity records.
5. Metadata updates preserve project ID and record an activity event.
6. Archive/restore are reversible and repeated same-state requests do not duplicate events.
7. Empty projects produce a zero progress percentage without division errors.
8. No hard delete is exposed in the UI.
9. Existing Phase 04 repository behavior and all previous tests remain unchanged.
10. Phase completion requires focused tests, full suite, GitHub Actions on the exact PR head, and a Colab/browser runtime acceptance record.

## Verification status

Implementation and test definitions are being added on feature/phase-05-project-management, based on Phase 04 commit 7d1a3ef10874bce97f90b9eab354bb4718c078ad. No checkpoint is complete until the relevant checks pass and evidence is recorded.


## First implementation verification record

- Commit: 2d05016b444c45c3bcc723dc75b42738037d0e8b
- GitHub Actions run: 83
- Workflow: Project Continue CI
- Result: PASS — compileall succeeded; full suite 50 passed in 0.60s.
- Scope: this evidence applies only to the commit above. Subsequent commits require a new exact-head CI run.
- Colab/browser runtime acceptance: pending.


## Expanded dashboard and runtime acceptance

The details panel also displays project identifiers and timestamps, task status counts, and a task table. The file-backed acceptance workflow is executable with:

    python scripts/phase05_acceptance.py

It verifies registration, task-derived progress, metadata/activity updates, archive/filter/restore, database reopen persistence, and SQLite integrity_check. The same workflow is covered by an automated pytest test.

### Latest exact-head CI evidence before this expansion

- Commit: c9c32f64b522f6dc414ac238b1dcbab584389a6b
- GitHub Actions runs #84 (push) and #85 (pull_request): PASS
- Compile: PASS
- Full test suite: 53 passed in 1.20s (run #84) and 53 passed in 1.29s (run #85)
- These results apply to c9c32f64... only. The current expanded commit must receive its own CI run.
- Colab/browser runtime acceptance: pending.
