# PC-P04-S007 — Database CRUD

**Implementation:** database/repository.py — ProjectRepository  
**Status:** IMPLEMENTED — CI and Colab verification pending

The repository provides parameterized create/read/list/update/delete operations for projects and tasks, plus dependency and activity-history operations. Domain values pass through existing core validators. Writes use explicit transactions; dynamic UPDATE column names are selected only from fixed internal allowlists. Dependency insertion checks project boundaries and recursive reachability to prevent cycles.

Acceptance: CRUD operations pass, missing records and integrity violations fail predictably, and transaction rollback prevents partial writes.
