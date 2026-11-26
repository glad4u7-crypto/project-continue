# Colab Control Agent — bounded remote test execution

This bridge accepts a small fixed set of diagnostics in the existing Colab runtime through a dedicated GitHub issue. It is not a remote shell.

## One-time owner setup

1. Create a GitHub issue titled **Project Continue — Colab Control Queue**.
2. Create a fine-grained token for only this repository with **Issues: Read and write**.
3. Add it to Colab Secrets as PROJECT_CONTINUE_CONTROL_TOKEN. Keep the commit-status token separate.
4. Set PROJECT_CONTINUE_CONTROL_ISSUE to the issue number, or pass --issue NUMBER.
5. Run from the existing checkout:

    python scripts/colab_control_agent.py --issue NUMBER --interval-seconds 60

The agent polls only while the current Colab runtime remains active. It does not start, stop, or restart Streamlit or Colab.

## Request format

Only comments authored by glad4u7-crypto are considered. The entire comment must exactly match one command:

- /pc-run phase18-tests — run the Phase 18 focused unit tests.
- /pc-run compile — compile-check project Python modules.
- /pc-run dashboard-health — read the local Streamlit health endpoint.
- /pc-run git-status — read current checkout status.
- /pc-read README.md — read an allow-listed project text file.
- /pc-read app.py — read the Streamlit entry point.
- /pc-read scripts/colab_control_agent.py — inspect the running bridge source.
- /pc-read docs/PHASE-18-COLAB-CONTROL-AGENT.md — read bridge documentation.

No shell fragments, command arguments, Python code, arbitrary paths, or free-form payloads are accepted. File reads are limited to four named UTF-8 project files and 12 KB per file; path traversal and symlink targets are rejected. This is read-only and does not expose `.env`, credentials, runtime files or arbitrary workspace content. Commands use fixed argument arrays, shell=False, bounded timeouts and truncated output. Results are posted as issue comments; the last processed comment ID is stored outside the repository.

## Source edits and high-impact operations

ChatGPT can prepare source changes on the isolated Phase 18 feature branch and submit them for review in PR #58. This bridge currently does not pull or apply code into the live Colab checkout, because changing files underneath a running dashboard can alter production behavior. Applying reviewed code to an isolated worktree is a later separately reviewed step.

Delete, arbitrary shell access, database migrations, backup restore/deletion, runtime restart, dashboard restart, deployment and PR merge are unsupported without separate explicit owner approval.

## Token boundary

The Issues read/write token can read and post comments on this repository issue. It is separate from PROJECT_CONTINUE_GITHUB_STATUS_TOKEN. Never paste either token into chat or source code. Revoke the dedicated token when no longer needed.

This uses free/open-source components; GitHub API rate limits and Colab runtime availability apply. It is not always-on.


## File writes and execution

The file-read commands above are read-only. This bridge does not write to the live checkout or execute arbitrary Python. Source changes must be proposed through a reviewed Git branch and pull request, then applied to Colab only through a separately reviewed, explicit synchronization step. Arbitrary runtime file writes and user-supplied code execution remain disabled.
