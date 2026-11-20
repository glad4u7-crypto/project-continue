# PC-P04-S006 — Activity History

**Implementation:** database/schema.py and ProjectRepository.record_activity/list_activity  
**Status:** IMPLEMENTED — CI and Colab verification pending

Activity history stores an integer event ID, required project foreign key, optional task foreign key, event type, JSON payload, and UTC timestamp. Project deletion cascades to its history; task deletion preserves the event and nulls its task reference. Project/time and event retrieval are indexed and bounded.

Acceptance: record and retrieve JSON event payloads; reject invalid foreign-key references; verify retention behavior on task deletion and project cascade.
