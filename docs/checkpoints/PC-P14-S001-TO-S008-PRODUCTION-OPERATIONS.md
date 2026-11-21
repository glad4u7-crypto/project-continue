# Phase 14 — Checkpoint Instructions

This document is the operational register for Phase 14. Run checkpoints in order; do not mark a checkpoint PASS merely because its files were committed.

## PC-P14-S001 — Deployment Architecture & Operational Baseline

**Goal:** Establish the actual deployment model, trust boundaries, operational risks and acceptance contract before introducing authentication, data isolation or infrastructure changes.

**Actions**
1. Inspect the repository entry point, configuration, database lifecycle, session state, GitHub integration, automation runner, memory/checkpoint engine and current CI workflows.
2. Document the supported deployment profiles and their limitations. Treat Colab as a development/acceptance environment, not an always-on production host.
3. Define trust boundaries for browser, Streamlit server, SQLite file, GitHub API, secrets, scheduled jobs and backup storage.
4. Record data classification, threat scenarios, operational recovery objectives and assumptions that require a hosting-provider decision.
5. Identify compatibility risks and the additive migration strategy for subsequent checkpoints.

**Acceptance**
- Architecture and trust-boundary documentation is checked in.
- Every production gap from Phase 10 is mapped to one or more Phase 14 checkpoints.
- No live database, runtime or dashboard is changed.
- Review confirms the remaining checkpoints are implementable without inventing a hosting provider or exposing the app publicly.

**Evidence to capture**
- Exact repository SHA and branch.
- Inventory of entry points, configuration, database and automation components.
- Documented deployment assumptions, unresolved provider-specific decisions and risk register.
- Focused documentation/architecture checks and full regression result.

**Status:** IN PROGRESS — branch and phase plan created; architecture audit and acceptance evidence not yet complete.

---

## PC-P14-S002 — Authentication & Authorization

**Goal:** Add a server-enforced identity and role boundary appropriate to the selected deployment profile.

**Required work:** Select a supported identity provider/session model; define roles and permissions; protect every data-bearing service operation; use secure cookie/session settings where applicable; test unauthenticated and unauthorized denial paths. No public exposure before this checkpoint passes.

**Safety:** Do not invent provider credentials or store secrets in Git. Use fake identities in tests.

## PC-P14-S003 — Project/User Isolation

**Goal:** Ensure users can access only projects and records authorized to them.

**Required work:** Define ownership/membership policy; enforce it in service/repository boundaries; add migration-safe ownership metadata if required; test cross-user reads, writes, task dependencies, memory, checkpoints, sessions, decisions, exports and backups.

**Safety:** Never infer authorization from UI filtering. Use isolated temporary databases.

## PC-P14-S004 — Secrets & Data Protection

**Goal:** Define and enforce secret lifecycle and data-at-rest protection boundaries.

**Required work:** Validate secret sources and rotation guidance; ensure logs/errors never reveal credentials; document which encryption controls are application-managed versus host-managed; add tests for unsafe configuration and secret leakage.

**Safety:** Do not claim encryption-at-rest unless verified for the selected host and storage. Do not add encryption keys to the repository.

## PC-P14-S005 — Automated Backup & Retention

**Goal:** Make backups scheduled, verifiable and governed by an explicit retention policy.

**Required work:** Add a scheduler-compatible backup runner, atomic/consistent SQLite backup, integrity verification, retention preview and safe cleanup, metrics/events and isolated tests.

**Safety:** Retention cleanup must be preview-first and must never touch the active DB or arbitrary paths. Colab disconnection is not an always-on schedule.

## PC-P14-S006 — Restore Drill & Disaster Recovery

**Goal:** Prove recovery from a verified backup using a repeatable, non-destructive drill.

**Required work:** Restore to a new isolated destination, verify schema/integrity and application-level records, document RPO/RTO assumptions, failure handling and rollback.

**Safety:** Never restore over the live database by default. Require an explicit separate operator procedure for any production cutover.

## PC-P14-S007 — Operational Observability

**Goal:** Make service health and operational failures diagnosable without leaking sensitive data.

**Required work:** Add health/readiness checks, dependency/database diagnostics, structured safe events, backup/restore status and audit trails for privileged actions.

**Safety:** Health endpoints must not disclose secrets, file paths, private records or stack traces.

## PC-P14-S008 — Deployment Pipeline & Final Acceptance

**Goal:** Establish reproducible deployment checks and a truthful release/operations handoff.

**Required work:** CI for compile, focused tests, full regression, security/dependency checks and migration/backup/restore tests; provider-neutral deployment guide; operator checklist; final limitations and evidence report.

**Acceptance gates:** Feature CI, post-merge main CI, exact-SHA Colab checks, manual browser checks and real-host deployment evidence are reported separately. Do not claim a live production deployment without real-host evidence.
