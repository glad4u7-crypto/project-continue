# Phase 19 Execution Reports

Store dated Markdown reports for Phase 19 diagnostics, test runs, acceptance decisions, and recovery events.

## Naming

`YYYY-MM-DD-Phase19-5-Acceptance.md`

Use a new report for each distinct run. Do not replace historical reports.

## Required contents

- Exact sub-phase and run identifier
- Status and timestamp/timezone
- Repository, branch, and commit SHA
- Notebook path and Google Drive backup path, if applicable
- Exact checks/commands and outputs
- Failures, unresolved issues, and risks
- Acceptance decision and links to supporting notebook/test evidence

Never include tokens, passwords, cookies, or private keys. Do not label a run PASS unless the acceptance checks actually passed.
