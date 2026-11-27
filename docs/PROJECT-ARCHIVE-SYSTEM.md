# Project Continue — Phase Documentation & Archive System

## Purpose

Keep every project phase, sub-phase, notebook, execution result, test record, and acceptance decision discoverable and historically traceable. This is the canonical documentation policy for the repository.

## Canonical locations

- `MASTER-PHASE-INDEX.md`: project-wide navigation and current phase status.
- `docs/PHASE-XX/`: phase overview, scope, progress, decisions, and acceptance criteria.
- `notebooks/Phase-XX/`: one immutable Jupyter Notebook artifact per executed sub-phase or explicitly named acceptance run.
- `reports/Phase-XX/`: human-readable execution, diagnostic, test, and acceptance reports.
- `tests/`: repeatable automated tests; keep these distinct from execution evidence.

## Notebook and report rules

1. Create a separate notebook for each sub-phase when that sub-phase is actually started/executed and notebook evidence is useful or requested.
2. Never create empty/fictitious notebooks merely to reserve future sub-phase numbers.
3. Never overwrite or silently replace a previously saved notebook or report.
4. If a correction or rerun is needed, create a new versioned artifact with a clear suffix such as `-r02` or a dated run identifier, and link it from the phase progress document.
5. Preserve executed cell outputs, errors, test summaries, timestamps, repository commit, branch, and relevant runtime details where safe.
6. Never store credentials, access tokens, private keys, cookies, or other secrets in notebooks, reports, or logs.
7. Mark a sub-phase complete only after its stated acceptance checks pass and the evidence is saved. A plan or notebook existing is not proof of completion.
8. Keep the Git repository and Google Drive backup aligned; record the exact Drive backup location in the relevant report, but do not treat a Drive-only file as committed to Git.
9. Do not reset execution cursors, replay old commands, or overwrite existing notebook artifacts as part of documentation maintenance.
10. Keep all implementation compatible with the project's free-tier/open-source constraint; explicitly document any service limits.

## Suggested phase layout

```text
MASTER-PHASE-INDEX.md
docs/
  PROJECT-ARCHIVE-SYSTEM.md
  PHASE-XX/
    README.md
    Progress.md
    Acceptance-Criteria.md
    Decisions.md
notebooks/
  Phase-XX/
    Phase-XX-Subphase-YY-<purpose>.ipynb
reports/
  Phase-XX/
    YYYY-MM-DD-Subphase-YY-<run-or-acceptance>.md
tests/
  test_*.py
```

Directories for future work may contain a README explaining the policy, but must not contain fabricated completion evidence or empty placeholder notebooks.

## Standard report metadata

Each report should identify:

- Phase and sub-phase
- Status: NOT STARTED / IN PROGRESS / BLOCKED / PASS / FAIL
- Date/time (with timezone)
- Repository, branch, and commit SHA
- Notebook path and Drive backup path, when applicable
- Commands/tests executed and their exact results
- Errors, deviations, and unresolved risks
- Acceptance decision and evidence links

## Change management

- Add new artifacts without replacing historical artifacts.
- Update the master index only after checking the actual repository files and evidence.
- Prefer small, reviewable commits with descriptive messages.
- Do not claim a file is saved until the GitHub write succeeds and its path can be fetched again.
