# Phase 19.5 — Controlled Colab Notebook Creation

## Goal

Allow the authorized Project Continue operator to request creation of one minimal Jupyter/Colab notebook in an explicitly selected Google Drive folder, receive a bounded GitHub Issue reply, and preserve all existing files.

## Implementation

- `scripts/colab_notebook_creation.py` creates a minimal nbformat 4 notebook with one Markdown introduction cell and one empty Python code cell.
- The destination must already exist and must be explicitly configured with `PROJECT_CONTINUE_NOTEBOOK_CREATE_DIR`.
- The requested name is a single filename stem (1–64 ASCII letters, digits, spaces, underscores or hyphens); path separators, hidden names, traversal and extensions are rejected.
- Creation uses exclusive file creation. Existing files and symlinks are never overwritten.
- The result is read back and checked as JSON/nbformat before PASS is returned.
- The report contains only the safe filename, byte count and SHA-256 digest; it does not expose the Drive absolute path or notebook contents.
- The starter code cell is empty and is never executed by the agent.
- No arbitrary shell, source editing, notebook execution, deletion, overwrite, restart or deployment command is added.

## Operator setup in Colab

1. Mount Google Drive.
2. Check that the intended destination folder already exists.
3. Set the environment variable in the active Colab runtime (do not put a token in the value):

   ```python
   import os
   os.environ["PROJECT_CONTINUE_NOTEBOOK_CREATE_DIR"] = (
       "/content/drive/MyDrive/Colab Notebooks"
   )
   ```

4. Run the focused tests from the synchronized repository checkout:

   ```bash
   python -m pytest -q tests/test_colab_notebook_creation.py tests/test_colab_control_agent.py
   ```

5. Configure the existing GitHub Control Agent token only through Colab Secrets as documented in the Phase 18 runbook. Never print or paste the token.
6. Start a one-shot poll for the configured control issue:

   ```bash
   python scripts/colab_control_agent.py --issue ISSUE_NUMBER
   ```

   Replace `ISSUE_NUMBER` with the existing operator-controlled GitHub Issue number. Do not start a continuous polling loop unless the operator explicitly needs it; Colab is not an always-on service.

## GitHub command

Post this exact command as a comment on the configured repository Issue, from the authorized GitHub account `glad4u7-crypto`:

```text
/pc-create-notebook Analysis 01
```

The agent replies with PASS/FAIL, request comment ID, task name and bounded creation report. A duplicate name intentionally returns FAIL and leaves the original file unchanged.

## Required acceptance gates

| Gate | Evidence required |
|---|---|
| Static/automated | Creation module and agent compile; focused tests pass |
| Safe destination | Existing configured Drive folder accepted; missing and symlinked roots rejected |
| Valid notebook | Read-back JSON parses; nbformat is 4; expected Markdown and empty code cells exist |
| No overwrite | Pre-existing file and symlink collision are rejected without changing target |
| Name safety | Traversal, separators, hidden names and malformed names rejected |
| Real Colab creation | One new `.ipynb` appears in the configured Drive folder and opens in Colab |
| GitHub round-trip | Authorized Issue command is polled and the matching PASS/FAIL report is posted |
| Error reporting | Duplicate, invalid destination, invalid name and write/validation errors return sanitized FAIL |
| State preservation | Existing notebooks, Streamlit process, database, agent state and backup manifest remain intact |

## Status rule

A passing unit test or a merged PR does not prove real Colab Drive creation. Phase 19.5 is COMPLETE only after exact-current-commit Colab tests, one real notebook creation/open, duplicate/error checks, GitHub Issue reply, and state-preservation evidence are supplied. Do not mark live round-trip or full Phase 19.5 acceptance PASS from source inspection alone.
