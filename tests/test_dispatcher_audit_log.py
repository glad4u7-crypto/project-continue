"""Request/result correlation and append-only audit event tests."""
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from database.connection import Database
from src.dispatcher.audit_log import AuditEventRejected, SQLiteAuditLog


class SQLiteAuditLogTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.database = Database(Path(self.tempdir.name) / "audit.sqlite3")
        self.audit = SQLiteAuditLog(self.database)
        self.audit.initialize()
        self.request_id = str(uuid4())
        self.now = datetime(2026, 11, 28, 5, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.database.close()
        self.tempdir.cleanup()

    def append(self, **changes):
        values = dict(
            request_id=self.request_id, event_type="request.accepted",
            actor_id="354281323", repository_id=1463557248,
            task_id="repo.read_file", state="ACK", occurred_at=self.now,
        )
        values.update(changes)
        return self.audit.append(**values)

    def test_events_correlate_by_request_id_in_append_order(self):
        first = self.append()
        second = self.append(event_type="execution.started", state="RUNNING")
        third = self.append(event_type="execution.passed", state="PASS")
        events = self.audit.list_for_request(self.request_id)
        self.assertEqual([e.event_id for e in events], [first.event_id, second.event_id, third.event_id])
        self.assertTrue(all(e.request_id == self.request_id for e in events))
        self.assertEqual([e.state for e in events], ["ACK", "RUNNING", "PASS"])

    def test_audit_survives_new_log_instance_and_database_connection(self):
        self.append()
        reopened = SQLiteAuditLog(self.database)
        self.assertEqual(len(reopened.list_for_request(self.request_id)), 1)

    def test_duplicate_event_id_is_rejected(self):
        event_id = str(uuid4())
        self.append(event_id=event_id)
        with self.assertRaises(AuditEventRejected):
            self.append(event_id=event_id, event_type="execution.started", state="RUNNING")

    def test_duplicate_request_transition_is_rejected(self):
        self.append()
        with self.assertRaises(AuditEventRejected):
            self.append()

    def test_invalid_ids_actor_repository_task_state_and_type_rejected(self):
        invalid = [
            {"request_id": "bad"},
            {"actor_id": "actor"},
            {"repository_id": 0},
            {"task_id": ""},
            {"state": "UNKNOWN"},
            {"event_type": "arbitrary.command"},
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(AuditEventRejected):
                self.append(**change)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(AuditEventRejected):
            self.append(occurred_at=datetime(2026, 11, 28))

    def test_task_arguments_and_secret_values_are_not_persisted(self):
        self.append()
        with self.database.connection() as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(dispatcher_audit_events)")}
            rows = connection.execute("SELECT * FROM dispatcher_audit_events").fetchall()
        self.assertNotIn("arguments", columns)
        self.assertNotIn("secret", columns)
        self.assertEqual(len(rows), 1)

    def test_unknown_request_returns_empty_history(self):
        self.assertEqual(self.audit.list_for_request(str(uuid4())), ())


if __name__ == "__main__":
    unittest.main()
