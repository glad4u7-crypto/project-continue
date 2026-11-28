# Phase 20.2 — Authentication & Least-Privilege Security Review

- Date: 2026-11-28 (Asia/Kolkata)
- Repository: glad4u7-crypto/project-continue
- Planning branch: docs/phase-20-master-checklist
- Main HEAD inspected: d9165f1aea785f0c75a0b4c55405424532a422a6
- Planning branch HEAD before this report: de4e6c8e46ac2e3e966e675ea31cd8bc78e519da
- Scope: U20-2-02 through U20-2-09; U20-2-01 remains evidenced in its own report.
- Mode: least-privilege design, repository inspection, read-only capability checks, and use of existing CI evidence. No permission or credential changes.

## Executive result

Phase 20.2 is **PARTIALLY COMPLETE WITH TWO UNAVAILABLE CHECKPOINTS**:
- PASS: U20-2-01, U20-2-02, U20-2-03, U20-2-04, U20-2-05, U20-2-07, U20-2-09.
- UNAVAILABLE: U20-2-06 (cannot verify/configure Actions Secret Store through the current connector); U20-2-08 (no safe isolated test identity/credential lifecycle interface is available to prove revoked-credential denial end-to-end).
- No FAIL is hidden or converted to PASS. Phase 20.2 parent exit gate is NOT COMPLETE while these two checkpoints remain unavailable.

## U20-2-02 — Operation-to-minimum-permission map (PASS)

The map below describes GitHub's documented minimum permission categories for the operation, not the unknown installed App grant. Exact endpoint requirements can vary; check each endpoint's current GitHub REST documentation and `X-Accepted-GitHub-Permissions` header before implementation.

| Required operation | Minimum permission / token boundary | Notes |
|---|---|---|
| Repository metadata, default branch, collaborator metadata | Repository Metadata: read | Repository access must be installation-selected; actor rights do not prove App grants. |
| Read files, trees, commits, branches, artifacts linked as repository content | Contents: read; Metadata: read | Read-only inspection. |
| Create/update/delete repository files, create/update refs, commits, feature branches | Contents: write; Metadata: read | Never direct-write main; branch/SHA guard remains mandatory. |
| Edit `.github/workflows/**` | Contents: write plus Workflows: write | GitHub documents a distinct Workflows permission for Actions workflow files. |
| Read issues, comments, labels, milestones | Issues: read | PR conversation comments may be served by Issues endpoints. |
| Create/update/comment/label/assign issues | Issues: write | Only when the requested operation needs mutation. |
| Read PR metadata, diff, reviews, comments | Pull requests: read; Metadata: read | Some conversation operations may also use Issues permission; verify endpoint. |
| Create/update PR, request review, add review/comment, merge | Pull requests: write; potentially Contents: write for merge/branch changes | Merge remains explicit-approval-only even if technically authorized. |
| Read Actions workflow runs, jobs, logs, artifacts | Actions: read | Existing connector has tested read support for selected run/job/log/artifact resources. |
| Rerun jobs / dispatch a workflow | Actions: write | Workflow dispatch is not exposed as an action by the current connector; permission alone does not create a missing connector action. |
| Manage repository Actions secrets/variables | Actions: write for Actions secret/variable endpoints, plus authorized repository access | Values must never be read into ChatGPT. Current connector does not expose the required write action. |
| Manage Codespaces lifecycle | Codespaces: write (and Codespaces: read for inventory); token type/endpoint support must be checked | Codespaces lifecycle is not exposed by the current connector and is excluded from this execution design. User-scoped Codespaces operations may require user authorization rather than an installation token. |
| Execute a Colab notebook/runtime | No GitHub repository permission is sufficient by itself | Requires a separate authenticated execution bridge; none is exposed in the current connector. |

Baseline: least privilege means grant only permissions required for the enabled endpoint set. Do not request Administration, organization-wide, enterprise-wide, or broad account permissions for this repository workflow.

## U20-2-03 — Permission families separated (PASS)

1. **Contents** — repository metadata/read, source reads, branch/ref and file changes. Use read for inspection and write only on feature branches for approved patches. Add **Workflows: write** only if editing files under `.github/workflows/`.
2. **Issues** — issue records and issue comments, labels, assignees, milestones. Read/write are separate levels.
3. **Pull requests** — PR records, reviews and PR review comments; read/write separated. Do not infer that Issues write automatically grants every Pull Requests endpoint.
4. **Actions** — workflow run/job/log/artifact read; write for rerun/dispatch and Actions secrets/variables management where the endpoint documents it. The current connector's read and write action surface is narrower than GitHub's full API.
5. **Codespaces** — distinct Codespaces permission family; lifecycle operations require their own endpoint and token eligibility checks. Current connector has no lifecycle actions. Do not add Codespaces permission to the GitHub App merely to compensate for an absent connector tool.
6. **Metadata** — read-only baseline for repository metadata and installation-selected repository context.

The installation permission object was not returned by the available installation inventory. The observed webhook event subscriptions and the actor's `admin=true` repository role are not evidence of the App's granted permission levels.

## U20-2-04 — Fine-grained PAT proposal (PASS; proposal only, not requested)

Decision: **do not create/request a PAT now**. The existing connector remains the primary interface for supported operations. A PAT is not a remedy for a missing connector action unless a supported integration can securely consume it.

If a future, approved gap analysis proves that a PAT is necessary, use a fine-grained PAT restricted to:
- Resource owner: glad4u7-crypto.
- Repository access: only `project-continue`.
- Permissions, initially minimum: Metadata read; Contents read/write only if patch operations are required; Issues read/write only if issue mutation is required; Pull requests read/write only if PR mutation is required; Actions read/write only if Actions API operations are required; Workflows write only if workflow YAML files must be edited.
- Do not add Administration, organization permissions, package/deployment/security permissions, or Codespaces permissions without a separately justified endpoint requirement.
- Actions secrets/variables endpoints must be rechecked against current GitHub documentation before any permission request. Never fetch or display secret values.
- The PAT must be consumed only by a supported secret-backed integration, never pasted into ChatGPT, an issue, PR, notebook, source file, or log.

This is a future conditional proposal, not authorization to create a credential.

## U20-2-05 — Token owner, expiry, rotation and revocation runbook (PASS; operational runbook)

1. Owner: the repository/account owner who creates and approves the credential; record the owner identity and purpose in the private credential inventory, not in repository source.
2. Scope: fine-grained, single repository, minimum permissions; use a GitHub App installation token where the integration supports it.
3. Expiry: choose the shortest practical expiry; proposed default maximum lifetime for an operational PAT is 90 days, or shorter if the integration permits. Never create a non-expiring credential.
4. Rotation: schedule rotation at least 14 days before expiry; create and validate the replacement through the approved secret manager, switch the integration, then revoke the old credential. Do not place either value in a ticket or chat.
5. Revocation: revoke immediately on suspected exposure, owner departure, purpose ending, or unexpected use; then invalidate dependent sessions/jobs and review audit logs.
6. Verification: after rotation/revocation, perform a harmless authorized health check through the secret-backed integration. Do not test by printing token values.
7. Recovery: if rotation fails, stop credential-dependent tasks and mark BLOCKED; do not fall back to asking the user to paste a token.
8. Evidence: retain timestamp, credential label (not value), owner, scope, expiry, rotation/revocation event ID and health-check result. Never retain the credential value or fingerprint in public reports.

The 90-day period is a conservative project policy recommendation, not a statement of GitHub's universal token expiry default.

## U20-2-06 — Secret Store arrangement verification (UNAVAILABLE)

The current connector inventory does not expose an Actions repository Secrets/Variables write action. The generic GitHub fetch tool is GET-only and excludes sensitive Secrets API families. No safe read-back can establish whether the required secret exists, and no configuration change was attempted.

Disposition: UNAVAILABLE pending a supported, owner-approved secret-store integration. No secret name/value was requested; no secret value was read, written, or exposed. Do not mark PASS based on workflow YAML references alone.

## U20-2-07 — Secret redaction tests (PASS using existing CI evidence)

Repository files inspected on main:
- `core/security.py` implements redaction for Bearer authorization values, GitHub token prefixes (`github_pat_`, `gh[pousr]_`), and common token/api-key/password/secret key-value patterns.
- `tests/test_security_logging.py` verifies GitHub token and Bearer redaction, formatted log redaction, and suppression of exception message/context secrets.
- `tests/test_security_hygiene.py` verifies sensitive local files are git-ignored and that `.env.example` has no active `GITHUB_TOKEN` assignment.
- `docs/checkpoints/PC-P10-S003-SECRETS-HYGIENE.md` records the earlier Gitleaks and security hygiene CI acceptance.

Run evidence: Phase 20.1 PR CI run `46093587157`, job `140819820015`, exact tested commit `f6362e75842c24337499bbc2e769c4dd2341f690`, reported `321 passed in 14.56s`. This is the existing full-suite evidence used for the repository's unit regression coverage; it is not a new run triggered by this review. No live credential was used. The tests use synthetic placeholder strings only.

Limit: this verifies the implemented/tested application log redaction paths; it does not prove every external provider log, GitHub artifact, notebook output or third-party system is redacted. Those remain separate future acceptance coverage.

## U20-2-08 — Unauthorized actor and revoked credential fail-closed test (UNAVAILABLE)

No isolated secondary identity, disposable credential issuance/revocation workflow, or connector-supported credential administration is available. Testing with the user's live account token or revoking the active connection would risk disrupting the project and is not authorized.

Disposition: UNAVAILABLE. Required future safe test: use a disposable least-privilege identity and short-lived credential in a dedicated test repository; prove unauthorized actor and revoked credential both receive denial; assert no mutation and no credential value in output; then revoke/delete only the disposable fixture after explicit approval. Do not test against main or the user's active credential.

## U20-2-09 — No credential values requested/displayed in ChatGPT (PASS)

This project operating rule is explicit and was followed in this review:
- No PAT, password, API key, GitHub App private key, Actions secret, or credential value was requested from the user.
- No credential value was read, echoed, copied into a report, issue, PR, notebook, or log.
- Any future credential setup must occur through GitHub's supported secure UI/secret store or another approved secret manager, not through chat.
- If a credential is pasted accidentally, stop processing it, do not repeat it, advise revocation/rotation, and continue only with a newly secured credential path.

## Safety / scope

- No GitHub App installation permission changed.
- No PAT requested or created.
- No Secrets/Variables API called.
- No Codespaces lifecycle operation or Colab execution attempted.
- No production database, Google Drive backup, live Streamlit service, main branch, merge, or deployment changed.
- No paid dependency introduced.

## Parent phase disposition

U20-2-01 PASS is recorded in its separate report. U20-2-02, 03, 04, 05, 07 and 09 are PASS. U20-2-06 and U20-2-08 are UNAVAILABLE for the explicit capability/safety reasons above. Therefore **Phase 20.2 is not complete** and its exit gate remains open. The next sequential work must resolve the first unavailable dependency through an approved supported integration; do not skip it or silently convert it to PASS.

## Official reference material

- GitHub Docs — Choosing permissions for a GitHub App: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- GitHub Docs — Permissions required for GitHub Apps: https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps
- GitHub Docs — Fine-grained PAT permissions: https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens
