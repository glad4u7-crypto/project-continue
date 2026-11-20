# PC-P04-S004 — Task Table

**Implementation:** database/schema.py and ProjectRepository task CRUD methods  
**Status:** IMPLEMENTED — CI and Colab verification pending

Tasks belong to a project through a required foreign key with ON DELETE CASCADE. Each task stores title, description, priority, status, optional due timestamp, and UTC creation/update timestamps. Priority and status are constrained in SQLite and normalized/validated before writes. Project/status and project/priority indexes support common lookups.

Acceptance: create/read/list/update/delete tasks; reject missing projects and invalid priority/status; verify project deletion cascades.
