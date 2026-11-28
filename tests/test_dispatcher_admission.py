"""Tests for persistent queue, concurrency and rate admission limits."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database.connection import Database
from src.dispatcher.admission import (
    AdmissionLimits,
    AdmissionRejected,
    SQLiteAdmissionController,
)


class AdmissionControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "admission.sqlite3")
        self.limits = AdmissionLimits(
            max_queued=2, max_concurrent=1, actor_rate_limit=3,
            global_rate_limit=5, rate_window_seconds=60, lease_seconds=120,
        )
        self.controller = SQLiteAdmissionController(self.db, self.limits)
        self.controller.initialize()
        self.now = datetime(2026, 11, 28, 5, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_admit_adds_ack_queue_entry(self):
        self.controller.admit("r1", "actor", now=self.now)
        self.assertEqual(self.controller.snapshot(now=self.now), {"queued": 1, "running": 0})

    def test_queue_capacity_rejects_excess(self):
        self.controller.admit("r1", "a", now=self.now)
        self.controller.admit("r2", "b", now=self.now)
        with self.assertRaisesRegex(AdmissionRejected, "queue capacity"):
            self.controller.admit("r3", "c", now=self.now)

    def test_start_obeys_global_concurrency_limit(self):
        self.controller.admit("r1", "a", now=self.now)
        self.controller.admit("r2", "b", now=self.now)
        self.controller.start("r1", now=self.now + timedelta(seconds=1))
        with self.assertRaisesRegex(AdmissionRejected, "concurrency capacity"):
            self.controller.start("r2", now=self.now + timedelta(seconds=2))
        self.assertEqual(self.controller.snapshot(now=self.now), {"queued": 1, "running": 1})

    def test_release_frees_concurrency_slot(self):
        self.controller.admit("r1", "a", now=self.now)
        self.controller.admit("r2", "b", now=self.now)
        self.controller.start("r1", now=self.now + timedelta(seconds=1))
        self.assertTrue(self.controller.release("r1"))
        self.controller.start("r2", now=self.now + timedelta(seconds=2))
        self.assertEqual(self.controller.snapshot(now=self.now), {"queued": 0, "running": 1})

    def test_actor_rate_limit_applies_within_sliding_window(self):
        for i in range(2):
            self.controller.admit(f"r{i}", "actor", now=self.now + timedelta(seconds=i))
        self.controller.release("r0")
        self.controller.release("r1")
        self.controller.admit("r2", "actor", now=self.now + timedelta(seconds=2))
        with self.assertRaisesRegex(AdmissionRejected, "actor request rate"):
            self.controller.admit("r3", "actor", now=self.now + timedelta(seconds=3))

    def test_global_rate_limit_applies_across_actors(self):
        for i in range(2):
            self.controller.admit(f"r{i}", f"actor{i}", now=self.now + timedelta(seconds=i))
            self.controller.release(f"r{i}")
        self.controller.admit("r2", "actor2", now=self.now + timedelta(seconds=2))
        self.controller.admit("r3", "actor3", now=self.now + timedelta(seconds=3))
        self.controller.admit("r4", "actor4", now=self.now + timedelta(seconds=4))
        with self.assertRaisesRegex(AdmissionRejected, "global request rate"):
            self.controller.admit("r5", "actor5", now=self.now + timedelta(seconds=5))

    def test_expired_leases_are_reclaimed(self):
        self.controller.admit("old", "actor", now=self.now)
        later = self.now + timedelta(seconds=121)
        self.controller.admit("new", "actor", now=later)
        self.assertEqual(self.controller.snapshot(now=later), {"queued": 1, "running": 0})

    def test_duplicate_request_id_is_rejected(self):
        self.controller.admit("r1", "actor", now=self.now)
        with self.assertRaises(AdmissionRejected):
            self.controller.admit("r1", "actor", now=self.now)

    def test_naive_timestamps_and_invalid_limits_rejected(self):
        with self.assertRaises(ValueError):
            self.controller.admit("r1", "a", now=datetime(2026, 11, 28))
        with self.assertRaises(ValueError):
            AdmissionLimits(max_concurrent=0)
        with self.assertRaises(ValueError):
            AdmissionLimits(actor_rate_limit=10, global_rate_limit=5)

    def test_missing_and_expired_queue_entries_cannot_start(self):
        with self.assertRaises(AdmissionRejected):
            self.controller.start("missing", now=self.now)
        self.controller.admit("expired", "actor", now=self.now)
        with self.assertRaises(AdmissionRejected):
            self.controller.start("expired", now=self.now + timedelta(seconds=121))

    def test_state_persists_across_controller_instances(self):
        self.controller.admit("r1", "actor", now=self.now)
        second = SQLiteAdmissionController(self.db, self.limits)
        self.assertEqual(second.snapshot(now=self.now), {"queued": 1, "running": 0})


if __name__ == "__main__":
    unittest.main()
