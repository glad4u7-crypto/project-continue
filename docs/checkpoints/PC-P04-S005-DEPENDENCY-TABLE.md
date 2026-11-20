# PC-P04-S005 — Dependency Table

**Implementation:** database/schema.py and ProjectRepository.add_dependency/list_dependencies  
**Status:** IMPLEMENTED — CI and Colab verification pending

Task dependencies use a composite primary key (task_id, depends_on_task_id), foreign keys with cascading deletion, and a self-dependency CHECK constraint. Repository validation rejects self-links, missing tasks, cross-project dependencies, duplicate links, and dependency cycles. A database trigger independently prevents cross-project links.

Acceptance: valid dependency chains persist; invalid/self/cross-project/cyclic links are rejected.
