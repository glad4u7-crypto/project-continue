"""Versioned SQLite schema for Project Continue persistence."""

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);
INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 1);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo', 'in_progress', 'blocked', 'done')),
    due_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (task_id, depends_on_task_id),
    CHECK (task_id <> depends_on_task_id)
);

CREATE TABLE IF NOT EXISTS activity_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_project_priority ON tasks(project_id, priority);
CREATE INDEX IF NOT EXISTS idx_dependencies_target ON task_dependencies(depends_on_task_id);
CREATE INDEX IF NOT EXISTS idx_activity_project_created ON activity_history(project_id, created_at);

CREATE TRIGGER IF NOT EXISTS trg_dependency_same_project
BEFORE INSERT ON task_dependencies
BEGIN
    SELECT CASE
      WHEN (SELECT project_id FROM tasks WHERE id = NEW.task_id)
        <> (SELECT project_id FROM tasks WHERE id = NEW.depends_on_task_id)
      THEN RAISE(ABORT, 'task dependencies must belong to the same project')
    END;
END;

-- Keep activity events attached only to tasks owned by the same project.
CREATE TRIGGER IF NOT EXISTS trg_activity_task_same_project_insert
BEFORE INSERT ON activity_history
WHEN NEW.task_id IS NOT NULL
BEGIN
    SELECT CASE
      WHEN (SELECT project_id FROM tasks WHERE id = NEW.task_id) IS NULL
        OR (SELECT project_id FROM tasks WHERE id = NEW.task_id) <> NEW.project_id
      THEN RAISE(ABORT, 'activity task must belong to the same project')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_activity_task_same_project_update
BEFORE UPDATE OF project_id, task_id ON activity_history
WHEN NEW.task_id IS NOT NULL
BEGIN
    SELECT CASE
      WHEN (SELECT project_id FROM tasks WHERE id = NEW.task_id) IS NULL
        OR (SELECT project_id FROM tasks WHERE id = NEW.task_id) <> NEW.project_id
      THEN RAISE(ABORT, 'activity task must belong to the same project')
    END;
END;
"""
