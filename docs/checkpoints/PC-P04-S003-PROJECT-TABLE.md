# PC-P04-S003 — Project Table

**Implementation:** database/schema.py and ProjectRepository.create_project/get_project/list_projects/update_project/delete_project  
**Status:** IMPLEMENTED — CI and Colab verification pending

Projects have a stable text primary key, unique non-empty name (validated in the repository), description, active/archived status constraint, and UTC creation/update timestamps. Project records are indexed by their primary/unique keys. Project deletion cascades to dependent project data by foreign-key policy.

Acceptance: create/read/list/update/delete project records; reject duplicate IDs/names and invalid status; confirm cascade behavior.
