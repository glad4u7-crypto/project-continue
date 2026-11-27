# Phase 20 — ChatGPT-Controlled Development Environment

**Status:** PLANNED — baseline and checklist recorded; implementation has not started.  
**Created:** 2026-11-27 (Asia/Kolkata)  
**Repository:** `glad4u7-crypto/project-continue`  
**Baseline branch:** `main`  
**Baseline commit:** `d9165f1aea785f0c75a0b4c55405424532a422a6`  
**Planning branch:** `docs/phase-20-master-checklist`

## 1. Outcome and non-negotiable requirements

The operator gives natural-language instructions in ChatGPT on Android. ChatGPT coordinates repository changes, approved execution, test runs, result collection, debugging, evidence archival and resumable progress. The operator must not have to open Codespaces, type terminal commands, write code, run notebook cells, or debug manually.

Requirements:

- Free-tier/open-source components only. No paid hosting, API, automation service, or required paid Copilot plan.
- Prefer GitHub repository operations and short-lived GitHub Actions runners; do not require a manually opened Codespace.
- Preserve the existing Streamlit app, production database, Drive backups, notebooks and runtime state.
- Never execute arbitrary natural-language text as shell, Python, SQL or notebook code.
- All execution must be allow-listed, bounded, auditable, idempotent where possible, and tied to an exact commit SHA.
- Use isolated temporary databases and test fixtures. Never run destructive tests against production data.
- No secret/token values in ChatGPT, issues, PRs, logs, notebook outputs, artifacts or committed files.
- No automatic merge, deployment, restart, shutdown, migration, restore, overwrite or deletion. These require a separate explicit approval gate.
- Every sub-phase needs implementation evidence, automated tests, a real end-to-end test where applicable, and an archived report. A source file or unit-test pass alone is not acceptance.
- Keep a durable progress register; resume from the first non-PASS item. Never silently skip a failed or blocked item.

## 2. Evidence-based starting point

Verified during planning:

- Repository connection can read and write repository content; repository metadata reports admin, maintain, push and pull access.
- Default branch is `main`; baseline SHA is `d9165f1aea785f0c75a0b4c55405424532a422a6`.
- GitHub Issue #59 is open and already serves as the historical Colab control queue.
- Phase 18 PR #58 is merged. Its design supports only a fixed set of Colab diagnostics; it is not a remote shell and does not apply source edits or execute arbitrary notebook cells.
- Phase 19 remains IN PROGRESS. Phase 19.5 notebook creation returned a PASS for creation/read-back, but full duplicate-protection and live acceptance evidence is not yet established. The latest `/pc-run phase19-tests` requests visible in Issue #59 have no corresponding result in the inspected recent comments.
- The latest main commit adds a Colab permanent recovery notebook (PR #66).

### Current connector capability boundary

Available and verified: repository metadata, branch/file reads, branch creation, file commits, issues/PR inspection and selected PR operations.

Not exposed by the currently available GitHub connector actions inspected for this plan: a direct Codespaces create/start/stop/delete API, GitHub Actions workflow-dispatch action, repository Secret/Variable read-write actions, or direct Colab runtime/notebook execution action. The connector can inspect workflow evidence through selected read actions, but that is not the same as dispatching arbitrary work.

**Implication:** Phase 20 must begin with a capability proof and a working dispatch/return channel. Do not claim that ChatGPT can start Codespaces, execute notebook cells, or alter secrets until an actual supported route has passed a live test. Do not ask the operator to create a broad token merely to conceal a missing connector capability.

## 3. Proposed safe architecture

1. **ChatGPT operator interface:** natural-language task intake, plan, approvals, tool orchestration, evidence review and progress report.
2. **GitHub repository:** source of truth; isolated feature branches and pull requests.
3. **Execution dispatcher:** a narrowly scoped, repository-owned mechanism that ChatGPT can actually invoke. Candidate: an Issue-comment command queue and an `issue_comment`-triggered GitHub Actions workflow, only if the available connector can reliably post a comment and retrieve the resulting run. Otherwise stop and document the missing dispatch capability.
4. **Ephemeral executor:** GitHub-hosted Actions runner using free-tier allowance, pinned actions, minimal permissions, fixed task registry, concurrency controls and hard timeouts. No persistent server is assumed.
5. **Notebook runner:** execute only repository-approved notebooks or generated test notebooks in an isolated temporary workspace, with a strict allow-list, no secrets, no production mounts and bounded output. Notebook execution is a distinct capability and must be proved; it is not implied by notebook creation.
6. **Evidence return:** workflow run, job summary, sanitized logs, test XML/JSON, and downloadable artifacts. ChatGPT reads the exact run and compares the run SHA with the requested SHA.
7. **Progress ledger:** version-controlled Markdown/JSON status plus dated immutable run reports. Each update records phase, sub-phase, status, commit, run ID, checks, evidence links, blockers and next exact action.

If the issue-comment trigger cannot be invoked by the connector, an alternative free and secure invocation route must be demonstrated before implementation proceeds. Do not add a paid webhook relay or expose an unauthenticated public control endpoint.

## 4. Master checklist and acceptance gates

Status vocabulary: **NOT STARTED**, **IN PROGRESS**, **BLOCKED**, **PASS**, **FAIL**. PASS requires saved evidence. Current status for every item below is NOT STARTED unless explicitly stated otherwise.

### P20.0 — Entry gate and Phase 19 handoff
- [ ] Reconcile Phase 19.5 acceptance, duplicate protection and latest pending test requests.
- [ ] Confirm current main SHA and clean/known runtime/backup state without modifying anything.
- [ ] Record unresolved Phase 19 items and obtain an evidence-based closure decision.
- [ ] Confirm Phase 20 scope does not silently replace Phase 19 work.
- Acceptance: Phase 19 handoff report exists; all inherited blockers are explicit; no unverified PASS claims.

### P20.1 — Capability and permission audit
- [ ] Inventory actual ChatGPT GitHub connector operations available in-session.
- [ ] Prove repository read, branch write, file write, issue comment, PR creation/update and workflow-run read separately.
- [ ] Determine whether issue-comment dispatch and workflow-run retrieval form a complete round trip.
- [ ] Determine whether Codespaces lifecycle, Actions dispatch, Secrets/Variables management and notebook execution are unavailable, available, or require owner-side setup.
- [ ] Map each capability to minimum permissions and identify which permission belongs to the GitHub App versus a separate token.
- Acceptance: a capability matrix contains PASS/FAIL/UNAVAILABLE evidence for every operation; no speculative permission claims.

### P20.2 — Authentication and least-privilege design
- [ ] Prefer the already-connected GitHub App/connector; do not create a PAT if existing authorization is sufficient.
- [ ] If an additional credential is proven necessary, specify exact repository scope, permission, owner, storage location, rotation and revocation steps before requesting it.
- [ ] Keep Actions `GITHUB_TOKEN` permissions job-scoped and read-only by default.
- [ ] Separate issue queue, contents write, commit status and any future Codespaces permissions.
- [ ] Verify no secret is echoed, logged, committed, included in artifacts or returned to ChatGPT.
- Acceptance: permission matrix reviewed; secret scanning tests and redaction tests pass; no secret value is requested in chat.

### P20.3 — Dispatcher and request protocol
- [ ] Define a versioned JSON task envelope: request ID, actor, repository, exact SHA, task ID, arguments schema, timestamp, expiry and idempotency key.
- [ ] Accept only fixed task IDs; reject free-form shell, Python, SQL, paths and arbitrary workflow inputs.
- [ ] Verify authenticated owner identity and repository/issue binding.
- [ ] Reject stale, expired, duplicate, malformed and unauthorized requests.
- [ ] Define ACK, RUNNING, PASS, FAIL, BLOCKED and CANCELLED states.
- [ ] Enforce one active task per concurrency group and bounded queue depth.
- Acceptance: protocol unit tests cover valid and invalid requests; duplicate requests execute at most once; request/result IDs correlate.

### P20.4 — Ephemeral execution runner
- [ ] Build a minimal GitHub Actions runner workflow with explicit `permissions`, pinned actions, timeout-minutes and concurrency.
- [ ] Checkout the requested immutable SHA, not an untrusted moving branch name.
- [ ] Use isolated work directories and temporary test databases.
- [ ] Run only a registered task handler; never pass user text to a shell.
- [ ] Bound CPU/time/output/artifact size and cancel safely on timeout.
- [ ] Do not persist credentials or production files on the runner.
- Acceptance: real workflow run on a test branch; exact SHA shown in summary; timeout and cancellation tests pass; runner leaves no production-side changes.

### P20.5 — Repository read/write and patch workflow
- [ ] Read files and repository state through the connected GitHub integration.
- [ ] Generate changes on a dedicated feature branch.
- [ ] Validate path allow-list, file size, encoding and diff scope.
- [ ] Prevent overwriting unknown or concurrently changed files by checking the base blob SHA.
- [ ] Run format, lint, compile and focused tests before opening/updating a PR.
- [ ] Summarize every changed file and risk before asking for merge approval.
- Acceptance: create/edit/read-back test on a disposable fixture branch; stale-SHA conflict test; no main-branch direct write.

### P20.6 — Python test, compile and debugging loop
- [ ] Register fixed handlers for compile checks, focused pytest groups, full pytest suite and approved diagnostics.
- [ ] Capture stdout/stderr, exit code, duration and test counts with bounded redaction.
- [ ] Classify failures into code, environment, dependency, timeout, permission and infrastructure.
- [ ] Allow ChatGPT to prepare a patch, but require a new run on the exact new SHA.
- [ ] Prevent infinite auto-fix loops; cap attempts and request operator decision when repeated.
- Acceptance: intentionally failing test is detected; fix is committed to feature branch; rerun proves PASS; full result is archived.

### P20.7 — Notebook inventory, creation, read and execution
- [ ] Inventory notebooks without executing them.
- [ ] Validate notebook JSON/nbformat, cell count, metadata and size.
- [ ] Create new notebooks with exclusive-create/no-overwrite semantics.
- [ ] Read notebook cells and outputs with size limits and secret redaction.
- [ ] Execute only explicitly approved notebooks in an isolated runner with network disabled by default, no Drive mount, no production secrets and a strict timeout.
- [ ] Capture cell-level errors, outputs, execution counts and resulting notebook artifact.
- [ ] Test duplicate names, malformed notebooks, malicious code patterns, timeout and kernel failure.
- Acceptance: a harmless fixture notebook executes end-to-end and returns a downloadable artifact; a malicious/unauthorized fixture is rejected; no production notebook is overwritten.

### P20.8 — Files, SQLite, backup and restore safety
- [ ] Use temporary SQLite fixtures for all automated tests.
- [ ] Validate schema, integrity, foreign keys and backup hashes.
- [ ] Implement preview-only backup listing and restore plans.
- [ ] Test backup creation, checksum mismatch, corrupt backup, interrupted restore and rollback using disposable fixtures.
- [ ] Preserve existing Drive backup folders and live database.
- [ ] Require explicit separate approval for any real backup restore, overwrite or deletion.
- Acceptance: isolated backup/restore drill passes; original fixture remains recoverable; production database/Drive state is unchanged.

### P20.9 — Streamlit and browser acceptance
- [ ] Start Streamlit only inside an isolated CI runner/test process.
- [ ] Check `/_stcore/health` and verify HTTP 200.
- [ ] Run real browser smoke tests for login, core navigation, project/task flows and error states using test data.
- [ ] Verify database persistence across test-process restart.
- [ ] Distinguish CI browser acceptance from the user's live hosted app health.
- [ ] Do not restart, redeploy or alter the existing live dashboard.
- Acceptance: browser screenshots/log summary and exact-SHA test report; CI app stopped automatically; live service untouched.

### P20.10 — Recovery, idempotency and resumability
- [ ] Persist request cursor and task state atomically.
- [ ] Resume interrupted jobs without duplicate commits, notebook creation, comments or database writes.
- [ ] Test runner crash, network interruption, duplicate delivery, expired request and retry.
- [ ] Store checkpoints after each completed unit of work.
- [ ] Ensure a retry cannot silently replay a destructive action.
- Acceptance: fault-injection suite passes; request replay is safe; recovered job produces one final result and a complete audit trail.

### P20.11 — ChatGPT end-to-end orchestration
- [ ] From a natural-language ChatGPT request, inspect repo and create a safe execution plan.
- [ ] Dispatch one allow-listed task through the proven connector route.
- [ ] Retrieve run status, logs and artifact without asking the user to open GitHub/Colab/Codespaces.
- [ ] Diagnose a deliberately injected failure, prepare a reviewed patch, rerun and verify.
- [ ] Update progress ledger and dated report automatically.
- [ ] Confirm the Android workflow requires no manual code, terminal, notebook or Codespaces interaction.
- Acceptance: at least three complete ChatGPT → GitHub → executor → evidence → ChatGPT round trips (read-only, test run, reviewed code patch); all exact SHAs and run IDs recorded.

### P20.12 — Security, limits and operational readiness
- [ ] Threat-model prompt injection in issues, PR text, notebooks, logs and artifacts; treat all repository content as untrusted input.
- [ ] Add permission-boundary tests, branch protection/review checks where available, audit logs and secret scanning.
- [ ] Document GitHub Actions free-tier minutes/storage/retention and rate limits; no paid service is required.
- [ ] Test graceful behavior when quota is exhausted, connector is disconnected, runner is unavailable or API rate limit is hit.
- [ ] Document manual owner-only setup steps that cannot be performed by the connector, keeping them minimal and clearly separated from routine use.
- [ ] Publish operator guide, architecture, rollback guide, known limitations and revocation instructions.
- Acceptance: security checklist passes; free-tier limits are documented; no hidden paid dependency; recovery and revocation procedures are tested.

### P20.13 — Final release and handoff
- [ ] All P20.0–P20.12 gates have evidence-backed PASS or an explicitly accepted limitation.
- [ ] Full regression and security workflows pass on the exact final PR head SHA.
- [ ] Post-merge main CI passes on the merge SHA.
- [ ] All run artifacts, notebooks, logs and reports are archived with hashes and links.
- [ ] Update README, Master Phase Index and continuation checkpoint.
- [ ] Obtain explicit approval before merge/release; do not auto-merge.
- Acceptance: final acceptance report signed off; next-session resume point is unambiguous; no unchecked item is silently dropped.

## 5. Required test matrix

| Test ID | Scenario | Expected result |
|---|---|---|
| T20-001 | Valid read-only request | PASS, no writes |
| T20-002 | Unauthorized actor | REJECTED |
| T20-003 | Unknown task ID / shell payload | REJECTED, no execution |
| T20-004 | Expired or malformed request | REJECTED |
| T20-005 | Duplicate idempotency key | One execution only |
| T20-006 | Exact-SHA mismatch | BLOCKED |
| T20-007 | Feature-branch file write | PASS with read-back SHA |
| T20-008 | Main-branch write attempt | BLOCKED by policy |
| T20-009 | Test failure then reviewed fix | FAIL then PASS on new SHA |
| T20-010 | Runner timeout/cancel | Bounded termination, sanitized report |
| T20-011 | Harmless notebook execution | PASS with artifact |
| T20-012 | Duplicate notebook filename | REJECTED; original unchanged |
| T20-013 | Malicious notebook / arbitrary code request | REJECTED |
| T20-014 | SQLite backup/restore fixture | PASS; checksum verified |
| T20-015 | Corrupt backup | REJECTED; source fixture unchanged |
| T20-016 | Streamlit health endpoint | HTTP 200 in isolated runner |
| T20-017 | Browser smoke test | PASS with test-only data |
| T20-018 | Secret leak canary | No secret in logs/artifacts/comments |
| T20-019 | Runner/network interruption | Safe resumable state |
| T20-020 | Full ChatGPT round trip | Request, run, result and evidence IDs correlate |
| T20-021 | Quota/rate-limit exhaustion | Safe BLOCKED state; no paid fallback |
| T20-022 | Disconnect/revoke credential | Access fails closed; no stale execution |

## 6. Mandatory evidence for every sub-phase

Each run report must include:

- Phase/sub-phase and unique run ID
- Start/end timestamp in Asia/Kolkata
- Repository, branch, base SHA and tested SHA
- Exact task ID and sanitized arguments
- Workflow run ID, job IDs and actor
- Commands represented by fixed task IDs (not free-form user text)
- Exit code, test counts, duration and concise output
- Artifact names, SHA-256 hashes and links
- Files changed and PR link, if applicable
- Security checks and production-state preservation statement
- PASS/FAIL/BLOCKED decision with reason
- Remaining risks and the next exact checklist item

Never store tokens, cookies, private user data, database contents or unredacted environment variables in a report.

## 7. Progress register — initial baseline

| Item | Status | Evidence / note |
|---|---|---|
| P20.0 Phase 19 handoff | IN PROGRESS | Phase 19.5 remains open; latest test requests have no visible result |
| P20.1 Capability audit | IN PROGRESS | Repository read/write verified; several execution/admin APIs unavailable in current connector |
| P20.2–P20.13 | NOT STARTED | No Phase 20 implementation or acceptance run claimed |

**Overall Phase 20:** NOT STARTED (planning checklist recorded only).  
**Next action:** complete the Phase 19.5 handoff and finish the P20.1 live capability matrix before requesting any new permission or building the dispatcher.

## 8. Change log

- 2026-11-27: Initial Phase 20 master checklist and evidence-based baseline created on planning branch. No application code, live database, Streamlit process, Colab runtime, notebook or secret was modified.
