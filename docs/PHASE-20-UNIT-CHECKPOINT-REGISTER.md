# Phase 20 — A-to-Z Unit Checkpoint Register

**Repository:** glad4u7-crypto/project-continue  
**Plan branch:** docs/phase-20-master-checklist  
**Status:** PLANNING ONLY — all unit checkpoints start as NOT STARTED unless separately evidenced.  
**Rule:** Mark a unit PASS only after its stated evidence is saved. A parent phase cannot pass while any required child unit is FAIL, BLOCKED or NOT STARTED.

## 20.0 — Phase 19 handoff ও entry gate

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-0-01 | বর্তমান main branch, HEAD SHA এবং working baseline পুনরায় পড়া | PASS | Main HEAD `d9165f1aea785f0c75a0b4c55405424532a422a6`; PR #69 base SHA একই; plan branch-এর CI-tested SHA `86152ee74a4e98bd935d72d495a91510d6ec8c05` verified. Colab/local working tree is excluded under the approved Colab-free execution model. |
| U20-0-02 | Phase 19 master index ও Phase 19.5 specification যাচাই | PASS | MASTER-PHASE-INDEX.md, docs/PHASE-19/README.md and docs/PHASE-19-5-CONTROLLED-NOTEBOOK-CREATION.md read from main; handoff report. |
| U20-0-03 | Issue #59-এর সব pending /pc-run অনুরোধ ও প্রতিক্রিয়া মিলিয়ে দেখা | PASS | All 65 comments and 23 `/pc-run` requests reconciled. Three unmatched Colab requests are explicitly retired/superseded by the approved Colab-free decision; duplicate replies for `7207977245` remain documented as a historical idempotency anomaly. No replay/cursor reset. |
| U20-0-04 | Notebook creation PASS-এর exact evidence, created file ও read-back যাচাই | PASS | User-uploaded Drive file independently read on 2026-11-28 06:47 Asia/Kolkata: 714 bytes and SHA-256 `c405d27615e7c91f2cb6f921292d29980098a62599922c834c1d9be34128c3fc` exactly match Issue #59 comment `7214096439`; JSON parse PASS; nbformat 4.5; 1 Markdown + 1 empty Code cell. No code executed. Addendum: `reports/Phase-20/2026-11-28-Phase20-0-U20-0-04-Notebook-Readback.md`. |
| U20-0-05 | Duplicate filename / symlink / invalid path protection-এর বাস্তব test evidence সংগ্রহ | PASS | GitHub Actions CI run `46021825415` on exact SHA `86152ee74a4e98bd935d72d495a91510d6ec8c05`: focused categories passed and full `python -m pytest -q` reported `310 passed, 11 skipped`; uploaded `phase-09-test-reports` artifact (242,853 bytes). The full default pytest suite includes `tests/test_colab_notebook_creation.py`; no separate Drive/Colab execution is claimed. |
| U20-0-06 | Phase 19.5-এর unresolved criteria আলাদা করে BLOCKED তালিকায় রাখা | PASS | Unresolved gates explicitly enumerated in 2026-11-27 Phase 19 handoff report. |
| U20-0-07 | Phase 19 handoff report তৈরি; কোনো অনিষ্পন্ন কাজকে PASS না বলা | PASS | reports/Phase-20/2026-11-27-Phase19-Handoff.md saved on plan branch. |

**20.0 exit gate:** COMPLETE. All 7 units are evidence-backed PASS. U20-0-04 was closed by the 2026-11-28 byte-for-byte uploaded-file verification; see `reports/Phase-20/2026-11-28-Phase20-0-U20-0-04-Notebook-Readback.md`. The earlier 2026-11-27 closure report remains unchanged as historical evidence of the then-open limitation. No Colab or Codespaces used.

## 20.1 — GitHub capability ও permission audit

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-1-01 | বর্তমান GitHub connector-এর উপলভ্য action inventory সংরক্ষণ | PASS | `reports/Phase-20/2026-11-28-Phase20-1-GitHub-Capability-Audit.md` — in-session action inventory সংরক্ষিত। |
| U20-1-02 | Repository metadata/read permission বাস্তবে পরীক্ষা | PASS | `get_repo`, authenticated login, collaborator permission=admin, README read-back; audit report। |
| U20-1-03 | Branch create এবং branch read-back পরীক্ষা | PASS | `audit/phase20-1-capability-20261128` create/read-back; base SHA `d9165f1aea785f0c75a0b4c55405424532a422a6`; audit report। |
| U20-1-04 | Feature branch-এ disposable file create/read-back পরীক্ষা | PASS | `docs/audits/phase20-1-connector-probe-20261128.md`; blob SHA `b8b2b9b725b6e83fc80985acb7d3d05f83878c90`; commit `f6362e75842c24337499bbc2e769c4dd2341f690`; audit report। |
| U20-1-05 | Issue comment create/read-back round trip পরীক্ষা | PASS | Issue #59 comment `7231731907` create/read/update/read-back; harmless non-command marker; audit report। |
| U20-1-06 | Pull request create/update/read capability আলাদা করে যাচাই | PASS | Draft PR #70 create/update/read-back; পরে unmerged অবস্থায় closed; audit report। |
| U20-1-07 | Workflow run, job, log, artifact read capability যাচাই | PASS | Run `46093287827`, jobs `140818901418`/`140818901649`, logs 35,314 chars; artifact `15207999445` downloaded/read; PR test run `46093587157`, job `140819820015`, `321 passed in 14.56s`; audit report। |
| U20-1-08 | Workflow dispatch capability আছে কি না live proof দিয়ে নির্ধারণ | UNAVAILABLE | Current connector inventory-তে workflow-dispatch action নেই; run/job read এবং rerun dispatch নয়। Audit report। |
| U20-1-09 | Codespaces create/start/stop/delete capability আলাদা করে যাচাই | UNAVAILABLE | Current connector inventory-তে Codespaces lifecycle action নেই। Audit report। |
| U20-1-10 | Repository Secrets/Variables write capability আছে কি না যাচাই; secret value কখনো পড়ার চেষ্টা নয় | UNAVAILABLE | Current connector inventory-তে Secrets/Variables write action নেই; generic fetch GET-only এবং sensitive Secrets API excluded। কোনো secret value পড়া হয়নি। Audit report। |
| U20-1-11 | Colab runtime বা notebook execution bridge আছে কি না যাচাই | UNAVAILABLE | Direct Colab runtime/notebook execution action নেই; comment posting execution proof নয়। কোনো execution command পাঠানো হয়নি। Audit report। |
| U20-1-12 | প্রতিটি capability PASS / FAIL / UNAVAILABLE এবং প্রমাণসহ matrix-এ লেখা | PASS | ১২টি capability-র পূর্ণ disposition matrix এবং evidence: `reports/Phase-20/2026-11-28-Phase20-1-GitHub-Capability-Audit.md`। |

**20.1 exit gate:** 12 of 12 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.2 — Authentication ও least-privilege security

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-2-01 | GitHub App/বর্তমান connector-ই যথেষ্ট কি না নির্ধারণ | PASS | `reports/Phase-20/2026-11-28-U20-2-01-GitHub-App-Connector-Sufficiency.md` — evidence-backed qualified NO for full end-to-end; current connector retained for supported GitHub subset; no PAT requested. |
| U20-2-02 | প্রয়োজনীয় প্রতিটি action-এর permission map তৈরি | PASS | `reports/Phase-20/2026-11-28-Phase20-2-Authentication-Least-Privilege-Review.md` — documented action-to-minimum-permission map; unknown installed App grants explicitly separated. |
| U20-2-03 | Contents, Issues, Pull Requests, Actions ও Codespaces permission আলাদা করা | PASS | Same report — Contents, Issues, Pull Requests, Actions, Codespaces and Metadata separated with least-privilege boundaries. |
| U20-2-04 | PAT একান্ত দরকার হলে fine-grained repository-only scope প্রস্তাব | PASS | Same report — conditional fine-grained single-repository PAT proposal; no PAT requested or created. |
| U20-2-05 | Token owner, expiry, rotation ও revocation runbook তৈরি | PASS | Same report — owner, short expiry, 14-day rotation window, revocation and evidence runbook. |
| U20-2-06 | Token কেবল GitHub/Actions Secret Store-এ রাখার ব্যবস্থা যাচাই | UNAVAILABLE | Main workflows `phase14.yml`, `automation.yml`, `phase17.yml` read-only inspected; no `secrets.*` references in those workflows; connector inventory has no Secrets/Variables write/read-back. Follow-up: `reports/Phase-20/2026-11-28-U20-2-06-Secret-Store-Capability-Followup.md`; no secret accessed. |
| U20-2-07 | Chat, issue, PR, logs, notebook ও artifacts-এ secret redaction test | PASS | Same report — inspected `core/security.py`, `tests/test_security_logging.py`, `tests/test_security_hygiene.py`; existing CI run `46093587157`, job `140819820015`, SHA `f6362e75842c24337499bbc2e769c4dd2341f690`, 321 passed. |
| U20-2-08 | Unauthorized actor এবং revoked credential fail-closed test | UNAVAILABLE | Same report — no disposable secondary identity/credential lifecycle interface; live credential revocation test unsafe and unavailable. |
| U20-2-09 | কোনো credential value ChatGPT-তে না চাওয়া এবং না দেখানোর নিশ্চয়তা | PASS | Same report — no credential value requested/read/displayed; chat credential-handling rule recorded. |

**20.2 exit gate:** APPROVED TO PROCEED WITH 2 EXPLICIT UNAVAILABLE LIMITATIONS (2026-11-28 user approval). U20-2-06 and U20-2-08 remain UNAVAILABLE; 7/9 PASS. This is not a full PASS and no limitation was reclassified.

## 20.3 — Secure dispatcher ও command protocol

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-3-01 | Versioned JSON request envelope schema তৈরি | PASS | Schema Draft 2020-12; JSON.parse syntax check + GitHub read-back PASS; commit `263da3f6e60c48720abb23a4e86891a030c5096f`; report `reports/Phase-20/2026-11-28-U20-3-01-Request-Envelope-Schema.md`; read-back blob `4a79379eaee81b400d11d88dcb174a49489c4025`. |
| U20-3-02 | Unique request ID, idempotency key, actor, repo, SHA ও expiry বাধ্যতামূলক করা | PASS | Required fields enforced in schema; 12/12 deterministic contract checks PASS; schema commit `11960b76ce8d4a087e29798458b687b6ee8d432d`; report `reports/Phase-20/2026-11-28-U20-3-02-Mandatory-Envelope-Fields.md`; runtime cross-request uniqueness/idempotency persistence not claimed. |
| U20-3-03 | Fixed task registry এবং strict argument schema তৈরি | PASS | `schemas/dispatcher/task-registry.v1.json` + `schemas/dispatcher/task-registry.v1.schema.json`; 3 fixed task IDs; 16/16 deterministic contract checks PASS; read-back blob SHAs `4336220c3002e81a6f440c6152d0ffe534d564c6` / `2b8b79377e44099866047329edfa285e6d197012`; report `reports/Phase-20/2026-11-28-U20-3-03-Fixed-Task-Registry.md`. Declarative only; no handlers/runtime dispatch claimed. |
| U20-3-04 | Natural language-কে সরাসরি shell/Python/SQL হিসেবে চালানো নিষিদ্ধ করা | PASS | Policy `schemas/dispatcher/natural-language-execution-policy.v1.json`; 10/10 deterministic contract assertions + JSON parse/read-back; report `reports/Phase-20/2026-11-28-U20-3-04-Natural-Language-Execution-Policy.md`; policy commit `eb2307694a64bcb6c2aac967b4d223941b8ecb4d`; read-back blob `6459a285c569988603702c3b4238f7483e0eb517`. Declarative policy only; runtime enforcement/CI not claimed. |
| U20-3-05 | Authenticated actor ও allowed repository যাচাই | PASS | Policy `schemas/dispatcher/authorization-policy.v1.json`; live connector identity `glad4u7-crypto` / GitHub ID `354281323`, repo ID `1463557248`, canonical repo `glad4u7-crypto/project-continue`, permission `admin` (minimum `pull`); 10/10 deterministic contract checks; report `reports/Phase-20/2026-11-28-U20-3-05-Actor-Repository-Authorization.md`; policy commit `e061a7b19435b14856b26b6dbee2c109f77f952b`; read-back blob `b7b745acd05b4f821fb2f893d1c7787d519779de`. Runtime enforcement not claimed. |
| U20-3-06 | Malformed, expired, duplicate ও replayed request reject করা | NOT STARTED | — |
| U20-3-07 | ACK/RUNNING/PASS/FAIL/BLOCKED/CANCELLED state machine তৈরি | NOT STARTED | — |
| U20-3-08 | Queue depth, concurrency ও rate limit নির্ধারণ | NOT STARTED | — |
| U20-3-09 | Request/result ID correlation এবং audit event test | NOT STARTED | — |

**20.3 exit gate:** 9 of 9 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.4 — Ephemeral execution runner

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-4-01 | নিরাপদ workflow trigger mechanism নির্বাচন ও প্রমাণ করা | NOT STARTED | — |
| U20-4-02 | Workflow-এ explicit minimal permissions নির্ধারণ | NOT STARTED | — |
| U20-4-03 | Actions ব্যবহার করলে action version SHA pin করা | NOT STARTED | — |
| U20-4-04 | Exact immutable commit SHA checkout করা | NOT STARTED | — |
| U20-4-05 | Fixed task handler ছাড়া অন্য execution নিষিদ্ধ করা | NOT STARTED | — |
| U20-4-06 | Runner workspace ও test data isolated রাখা | NOT STARTED | — |
| U20-4-07 | Timeout, CPU/output/artifact size bound করা | NOT STARTED | — |
| U20-4-08 | Cancellation ও failure cleanup test | NOT STARTED | — |
| U20-4-09 | Runner শেষে কোনো production state বা credential রেখে যায় না যাচাই | NOT STARTED | — |
| U20-4-10 | বাস্তব workflow run-এর URL, run ID, job ID ও SHA সংরক্ষণ | NOT STARTED | — |

**20.4 exit gate:** 10 of 10 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.5 — Repository read/write ও patch workflow

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-5-01 | Repository tree ও file content পড়া | NOT STARTED | — |
| U20-5-02 | File write-এর আগে branch ও base SHA যাচাই | NOT STARTED | — |
| U20-5-03 | প্রতিটি পরিবর্তনের জন্য আলাদা feature branch ব্যবহার | NOT STARTED | — |
| U20-5-04 | Path traversal, hidden path ও disallowed extension block করা | NOT STARTED | — |
| U20-5-05 | File size, encoding ও content validation | NOT STARTED | — |
| U20-5-06 | Existing file overwrite-এর আগে blob SHA compare করা | NOT STARTED | — |
| U20-5-07 | Stale SHA conflict হলে write বন্ধ করে re-read করা | NOT STARTED | — |
| U20-5-08 | Diff review-এ changed files ও line count প্রকাশ | NOT STARTED | — |
| U20-5-09 | Compile/lint/focused test সফল হলে PR তৈরি | NOT STARTED | — |
| U20-5-10 | PR body-তে evidence, risk, rollback ও test result যুক্ত করা | NOT STARTED | — |
| U20-5-11 | Main branch-এ direct write নিষিদ্ধ থাকার পরীক্ষা | NOT STARTED | — |

**20.5 exit gate:** 11 of 11 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.6 — Python compile, unit test ও debugging

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-6-01 | Python version ও dependency lock/baseline যাচাই | NOT STARTED | — |
| U20-6-02 | Compile-only task handler তৈরি | NOT STARTED | — |
| U20-6-03 | Focused pytest task handler তৈরি | NOT STARTED | — |
| U20-6-04 | Full pytest suite task handler তৈরি | NOT STARTED | — |
| U20-6-05 | Lint/type-check task handler প্রযোজ্য হলে যুক্ত করা | NOT STARTED | — |
| U20-6-06 | stdout/stderr/exit code/duration/test count সংগ্রহ | NOT STARTED | — |
| U20-6-07 | Failure classification: code/environment/dependency/permission/timeout/infrastructure | NOT STARTED | — |
| U20-6-08 | একটি intentional failing fixture দিয়ে FAIL detection পরীক্ষা | NOT STARTED | — |
| U20-6-09 | ChatGPT-প্রস্তুত patch feature branch-এ commit করা | NOT STARTED | — |
| U20-6-10 | নতুন exact SHA-তে focused ও regression retest | NOT STARTED | — |
| U20-6-11 | সীমিত retry; repeated failure হলে BLOCKED ও human decision | NOT STARTED | — |

**20.6 exit gate:** 11 of 11 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.7 — Notebook inventory, create, read ও execute

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-7-01 | Notebook inventory read-only ভাবে সংগ্রহ | NOT STARTED | — |
| U20-7-02 | Notebook JSON এবং nbformat version validation | NOT STARTED | — |
| U20-7-03 | Cell type, metadata, size ও output bounds যাচাই | NOT STARTED | — |
| U20-7-04 | Exclusive create এবং existing file no-overwrite test | NOT STARTED | — |
| U20-7-05 | Notebook read-এর সময় secret/token redaction | NOT STARTED | — |
| U20-7-06 | Execution allow-list এবং explicit notebook identity/commit binding | NOT STARTED | — |
| U20-7-07 | Isolated kernel/runner; production Drive mount ও secrets ছাড়া execution | NOT STARTED | — |
| U20-7-08 | Network access default-deny এবং timeout enforce | NOT STARTED | — |
| U20-7-09 | Cell output, execution count, traceback ও artifact সংরক্ষণ | NOT STARTED | — |
| U20-7-10 | Harmless notebook real end-to-end execution | NOT STARTED | — |
| U20-7-11 | Malicious/unauthorized notebook reject | NOT STARTED | — |
| U20-7-12 | Duplicate name, malformed JSON, timeout ও kernel crash test | NOT STARTED | — |

**20.7 exit gate:** 12 of 12 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.8 — SQLite, backup ও recovery safety

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-8-01 | Automated tests-এ temporary SQLite DB বাধ্যতামূলক | NOT STARTED | — |
| U20-8-02 | Live database path শনাক্ত করে test runner-এ block | NOT STARTED | — |
| U20-8-03 | Schema version, integrity_check ও foreign_key_check চালানো | NOT STARTED | — |
| U20-8-04 | Backup create এবং SHA-256 checksum যাচাই | NOT STARTED | — |
| U20-8-05 | Backup inventory ও restore preview-only report | NOT STARTED | — |
| U20-8-06 | Corrupt/truncated backup reject test | NOT STARTED | — |
| U20-8-07 | Interrupted restore ও rollback test disposable fixture-এ | NOT STARTED | — |
| U20-8-08 | Idempotent recovery এবং existing row no-overwrite test | NOT STARTED | — |
| U20-8-09 | Google Drive backup preservation যাচাই; কোনো mount পরিবর্তন নয় | NOT STARTED | — |
| U20-8-10 | Real restore/delete/overwrite-এর জন্য আলাদা explicit approval gate | NOT STARTED | — |

**20.8 exit gate:** 10 of 10 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.9 — Streamlit ও browser acceptance

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-9-01 | Isolated test DB দিয়ে Streamlit app start | NOT STARTED | — |
| U20-9-02 | /_stcore/health HTTP 200 পরীক্ষা | NOT STARTED | — |
| U20-9-03 | App startup, import error ও dependency error capture | NOT STARTED | — |
| U20-9-04 | Browser smoke test harness স্থাপন | NOT STARTED | — |
| U20-9-05 | Login/access flow (যদি প্রযোজ্য) test | NOT STARTED | — |
| U20-9-06 | Project create/read/update flow test | NOT STARTED | — |
| U20-9-07 | Task create/update/complete/dependency flow test | NOT STARTED | — |
| U20-9-08 | GitHub panel এবং error/empty/loading state test | NOT STARTED | — |
| U20-9-09 | Process restart-এর পর test DB persistence যাচাই | NOT STARTED | — |
| U20-9-10 | Test শেষে isolated app process বন্ধ; live app untouched | NOT STARTED | — |
| U20-9-11 | Browser evidence ও exact SHA report archive | NOT STARTED | — |

**20.9 exit gate:** 11 of 11 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.10 — Recovery, idempotency ও resumability

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-10-01 | Request state transition durable storage | NOT STARTED | — |
| U20-10-02 | Checkpoint write atomicity যাচাই | NOT STARTED | — |
| U20-10-03 | একই request দ্বিতীয়বার এলে duplicate execution block | NOT STARTED | — |
| U20-10-04 | Runner crash-এর পরে safe resume test | NOT STARTED | — |
| U20-10-05 | Network interruption ও API rate-limit recovery test | NOT STARTED | — |
| U20-10-06 | Partial artifact/upload failure recovery test | NOT STARTED | — |
| U20-10-07 | Commit/PR/comment duplicate prevention | NOT STARTED | — |
| U20-10-08 | Notebook create operation replay-safe test | NOT STARTED | — |
| U20-10-09 | Timeout/cancel state এবং cleanup verification | NOT STARTED | — |
| U20-10-10 | Fault-injection suite-এর ফলাফল report-এ সংরক্ষণ | NOT STARTED | — |

**20.10 exit gate:** 10 of 10 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.11 — ChatGPT end-to-end orchestration

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-11-01 | ChatGPT-তে natural-language task থেকে structured plan তৈরি | NOT STARTED | — |
| U20-11-02 | Plan-কে fixed task ID ও validated arguments-এ রূপান্তর | NOT STARTED | — |
| U20-11-03 | Read-only repository task dispatch ও result retrieval | NOT STARTED | — |
| U20-11-04 | Automated test task dispatch ও run/log retrieval | NOT STARTED | — |
| U20-11-05 | Failure diagnosis ও feature-branch patch প্রস্তুত | NOT STARTED | — |
| U20-11-06 | Patch review-এর পরে new-SHA retest | NOT STARTED | — |
| U20-11-07 | Artifact download/read ও evidence verification | NOT STARTED | — |
| U20-11-08 | Progress register ও dated report update | NOT STARTED | — |
| U20-11-09 | Android ChatGPT থেকে সম্পূর্ণ flow; manual terminal/Codespaces/Colab cell ছাড়া পরীক্ষা | NOT STARTED | — |
| U20-11-10 | কমপক্ষে তিনটি পৃথক complete round trip evidence archive | NOT STARTED | — |

**20.11 exit gate:** 10 of 10 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.12 — Security, free-tier ও operational readiness

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-12-01 | Prompt injection threat model: issues, PRs, notebooks, logs, artifacts | NOT STARTED | — |
| U20-12-02 | Repository content-কে untrusted input হিসেবে treat করা | NOT STARTED | — |
| U20-12-03 | Least-privilege permission boundary tests | NOT STARTED | — |
| U20-12-04 | Secret scanning ও log/artifact redaction tests | NOT STARTED | — |
| U20-12-05 | Branch protection/review settings read ও প্রয়োজন হলে owner approval plan | NOT STARTED | — |
| U20-12-06 | GitHub Actions free-tier minutes/storage/retention/rate limits নথিভুক্ত | NOT STARTED | — |
| U20-12-07 | Quota exhaustion হলে safe BLOCKED behavior পরীক্ষা | NOT STARTED | — |
| U20-12-08 | Connector disconnect, revoked token ও runner outage পরীক্ষা | NOT STARTED | — |
| U20-12-09 | কোনো paid API/hosting/automation dependency নেই যাচাই | NOT STARTED | — |
| U20-12-10 | Setup, operation, rollback, recovery ও credential revocation runbook তৈরি | NOT STARTED | — |

**20.12 exit gate:** 10 of 10 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## 20.13 — Final integration, release ও handoff

| Unit ID | Checkpoint | Status | Evidence / run reference |
|---|---|---|---|
| U20-13-01 | 20.0–20.12-এর প্রতিটি unit checkpoint evidence audit | NOT STARTED | — |
| U20-13-02 | সব failed/blocked checkpoint-এর disposition লিখিতভাবে নির্ধারণ | NOT STARTED | — |
| U20-13-03 | Full regression suite final PR head SHA-তে চালানো | NOT STARTED | — |
| U20-13-04 | Security suite final PR head SHA-তে চালানো | NOT STARTED | — |
| U20-13-05 | Post-merge main CI merge SHA-তে যাচাই | NOT STARTED | — |
| U20-13-06 | All reports, notebooks, logs ও artifacts-এর hash/link archive | NOT STARTED | — |
| U20-13-07 | README, Master Phase Index ও continuation checkpoint update | NOT STARTED | — |
| U20-13-08 | Final acceptance report এবং known limitations প্রকাশ | NOT STARTED | — |
| U20-13-09 | Merge/release-এর আগে user-এর explicit approval | NOT STARTED | — |
| U20-13-10 | পরবর্তী session-এর exact resume checkpoint ও next action লেখা | NOT STARTED | — |

**20.13 exit gate:** 10 of 10 unit checkpoints must have evidence-backed PASS, or an explicitly approved limitation recorded in the final report. No silent skips.

## Register summary

- Parent phases: 14
- Atomic unit checkpoints: 142
- Initial PASS: 0
- Initial NOT STARTED: 142
- Initial FAIL: 0
- Initial BLOCKED: 0

## Run update protocol

For each unit, append/update the status only after execution. Evidence must include timestamp (Asia/Kolkata), repository, branch, exact commit SHA, test/run ID, result, artifact/report link, and sanitized output summary. Keep historical dated run reports; do not erase prior failures. If a checkpoint cannot be tested with the current connector, mark BLOCKED or UNAVAILABLE and document the exact missing capability. Never ask the operator to paste a token into ChatGPT.
