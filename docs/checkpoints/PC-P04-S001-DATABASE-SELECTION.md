# PC-P04-S001 — Database Selection

**Phase:** 04 — Database System  
**Decision:** SQLite (Python standard-library sqlite3)  
**Status:** DECIDED — implementation approval recorded in this checkpoint

## Requirements considered

Project Continue is currently a Python 3.11+ application with a Streamlit dashboard shell. The repository has no deployed database service, no database credentials, and no multi-user hosting topology documented. The first persistence milestone must be easy to run in local development and Google Colab, test without external infrastructure, and keep setup reproducible.

## Decision

Use SQLite as the Phase 04 persistence engine, accessed through Python's built-in sqlite3 module.

## Rationale

- **Zero service setup:** SQLite is embedded; users do not need to provision or operate a separate database server.
- **Portable development:** the same database file can be used by local Python, CI, and Colab.
- **Standard library:** no new runtime dependency or ORM is required for the first persistence layer.
- **Transactional integrity:** SQLite supports atomic transactions, foreign keys, uniqueness checks, and indexes needed by project/task/dependency records.
- **Test isolation:** tests can use independent temporary database files or in-memory databases.
- **Explicit upgrade path:** a future move to PostgreSQL can be considered if concurrent multi-user writes, hosted deployment, or operational requirements justify a server database.

## Trade-offs and boundaries

- SQLite is best suited to a single application instance or modest write concurrency; it is not the chosen solution for horizontally scaled multi-writer deployment.
- The database file must be stored on a durable local volume. Ephemeral Colab storage is for verification only, not production persistence.
- Foreign-key enforcement must be enabled on every connection; the connection layer will enforce this.
- Schema changes will be versioned and tested. No claim is made that schema or CRUD features exist merely from this engine decision.

## Acceptance criteria

- The selected engine and rationale are documented.
- Runtime access uses the standard-library sqlite3 API.
- Connection-level foreign-key enforcement and transaction behavior are tested in S002/S008.
- The application can override the database path; tests do not write to a shared production path.

## Final disposition

**PC-P04-S001: DECISION RECORDED.** The selection checkpoint is complete; implementation and CI verification are tracked by subsequent checkpoints.
