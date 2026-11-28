# U20-2-01 — GitHub App / Current Connector Sufficiency Decision

- Timestamp: 2026-11-28 07:23:12 Asia/Kolkata
- Repository: glad4u7-crypto/project-continue
- Branch audited: main
- Main HEAD SHA: d9165f1aea785f0c75a0b4c55405424532a422a6
- Planning branch at audit start: docs/phase-20-master-checklist
- Planning branch HEAD at audit start: 53c8257c42ea1c871ca729ac15e4e539453d0a9b
- Authenticated GitHub actor: glad4u7-crypto (ID 354281323)
- Installation: ID 180481050, account glad4u7-crypto, repository_selection=selected
- Installation event subscriptions observed: check_run, check_suite, commit_comment, issues, issue_comment, pull_request, pull_request_review, pull_request_review_comment, pull_request_review_thread, repository, status, sub_issues
- Secret/token values: not requested, read, or recorded.

## Evidence gathered

1. Current connector action inventory was enumerated in the Phase 20.1 audit report (88 available actions at that audit point). It supports repository metadata/profile, search, branch/ref/tree/blob/commit, file CRUD, issues/comments, PR lifecycle/reviews, commit status, selected Actions run/job/step/log/artifact reads/downloads, and workflow-job reruns.
2. list_installations returned installation ID 180481050 for account glad4u7-crypto with selected-repository selection. The response did not include a permissions object; event subscriptions are not equivalent to API permission grants.
3. get_repo for glad4u7-crypto/project-continue returned actor permission flags admin=true, maintain=true, push=true, pull=true, triage=true. This proves the authenticated actor's repository permission, not the complete GitHub App installation permission set.
4. get_repo_collaborator_permission for glad4u7-crypto returned admin.
5. Live reads of main workflow files found:
   - .github/workflows/phase14.yml declares workflow_dispatch, pull_request and push triggers; job permissions are contents: read.
   - .github/workflows/automation.yml declares workflow_dispatch, schedule and push triggers; job permissions are contents: read.
   - .github/workflows/phase17.yml uses pull_request/push triggers and contents: read.
   These declarations prove that workflow_dispatch is configured in repository YAML for the first two workflows; they do not prove that the current connector can invoke it.
6. In Phase 20.1 the available connector inventory had no workflow-dispatch action, Codespaces lifecycle actions, repository Actions Secrets/Variables write action, or direct Colab runtime/notebook execution action. The generic fetch operation is GET-only and excludes sensitive Secrets API families.
7. Repository Contents, branches, issues/comments, PR create/update/read and selected Actions run/job/log/artifact read were live-tested in Phase 20.1. The audit report records exact object IDs, SHAs, run IDs and artifacts.

## Decision

**The current GitHub App/connector is NOT sufficient by itself for the complete Phase 20 end-to-end target.**

It IS sufficient as the primary, least-privilege GitHub interface for:
- repository metadata and source reads;
- controlled feature-branch file changes and read-back;
- issue and pull-request collaboration;
- reading selected Actions runs, jobs, logs and artifacts;
- observing CI started by repository events such as pull_request/push.

It is NOT currently proven/capable through the exposed connector surface for:
- invoking workflow_dispatch (although workflows declare this trigger);
- Codespaces create/start/stop/delete;
- writing Actions repository Secrets/Variables;
- directly executing a Colab runtime or notebook.

## Least-privilege decision / no credential expansion now

- Retain the existing connector for all supported GitHub operations.
- Do NOT create or request a PAT at U20-2-01.
- Do NOT broaden installation permissions based only on assumptions or event subscriptions.
- U20-2-02 must map each required operation to the minimum GitHub App permission/API surface and identify which missing capabilities are genuinely required.
- U20-2-03 must separate Contents, Issues, Pull Requests, Actions and Codespaces permissions.
- U20-2-04 may propose a fine-grained repository-only PAT only if a specific required operation cannot be delivered by the existing connector/App; any PAT remains a proposal, not a request to paste it into ChatGPT.
- Direct Colab execution is an external execution-bridge question, not solved merely by granting GitHub repository permissions.

## Scope and safety

- Read-only inspection only for this unit; no GitHub installation settings or repository permissions changed.
- No PAT, token, password or secret requested or exposed.
- No workflow dispatch, Codespaces operation, Secrets/Variables write, Colab execution, production database change, Drive backup change, merge or deployment performed.
- No paid service or dependency introduced.

## Result

U20-2-01: PASS — the sufficiency decision is evidence-backed and persisted. The conclusion is a qualified NO for the complete end-to-end system and YES for the supported GitHub collaboration/read-write subset. Four capability gaps remain explicit; no unsupported capability is claimed.
