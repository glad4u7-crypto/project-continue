"""Deterministic tests for request validation and durable replay storage."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from database.connection import Database
from src.dispatcher.request_guard import RequestRejected, validate_and_claim
from src.dispatcher.replay_store import SQLiteReplayStore


class RequestGuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.envelope = {
            "schema_version": "1",
            "request_id": str(uuid4()),
            "nonce": str(uuid4()),
            "issued_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(seconds=120)).isoformat(),
            "actor": {"id": "354281323", "type": "user"},
            "repository": {"id": 1463557248, "full_name": "glad4u7-crypto/project-continue"},
            "commit_sha": "a" * 40,
            "task": "repo.read_file",
        }
        self.claimed = set()

    def claim_pair(self, request_id, nonce, expires):
        keys = (("request_id", request_id), ("nonce", nonce))
        if any(key in self.claimed for key in keys):
            return False
        self.claimed.update(keys)
        return True

    def validate(self, envelope=None, claim_pair=None):
        validate_and_claim(
            self.envelope if envelope is None else envelope,
            now=self.now,
            claim_pair=self.claim_pair if claim_pair is None else claim_pair,
        )

    def test_valid_request_claims_both_values(self):
        self.validate()
        self.assertEqual(len(self.claimed), 2)

    def test_missing_and_extra_fields_rejected(self):
        malformed = dict(self.envelope)
        malformed.pop("task")
        with self.assertRaises(RequestRejected):
            self.validate(malformed)
        with self.assertRaises(RequestRejected):
            self.validate(dict(self.envelope, unexpected=True))

    def test_malformed_timestamp_rejected(self):
        with self.assertRaises(RequestRejected):
            self.validate(dict(self.envelope, issued_at="yesterday"))

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(RequestRejected):
            self.validate(dict(self.envelope, issued_at=self.now.replace(tzinfo=None).isoformat()))

    def test_future_expired_and_excessive_ttl_rejected(self):
        cases = (
            dict(issued_at=(self.now + timedelta(seconds=1)).isoformat()),
            dict(expires_at=(self.now - timedelta(seconds=1)).isoformat()),
            dict(expires_at=(self.now + timedelta(seconds=301)).isoformat()),
        )
        for change in cases:
            with self.subTest(change=change), self.assertRaises(RequestRejected):
                self.validate(dict(self.envelope, **change))

    def test_invalid_actor_repository_sha_and_task_rejected(self):
        cases = (
            ("actor", {"id": "x", "type": "user"}),
            ("repository", {"id": 0, "full_name": "owner/repo"}),
            ("commit_sha", "bad"),
            ("task", "repo.delete_file"),
        )
        for key, value in cases:
            with self.subTest(key=key), self.assertRaises(RequestRejected):
                self.validate(dict(self.envelope, **{key: value}))

    def test_duplicate_pair_rejected(self):
        self.validate()
        with self.assertRaisesRegex(RequestRejected, "duplicate or replay"):
            self.validate()

    def test_store_error_propagates_fail_closed(self):
        def unavailable(*args):
            raise RuntimeError("store unavailable")
        with self.assertRaises(RuntimeError):
            self.validate(claim_pair=unavailable)


class SQLiteReplayStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "replay.sqlite3")
        self.store = SQLiteReplayStore(self.db)
        self.store.initialize()

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_pair_claim_is_durable_across_store_instances(self):
        expiry = datetime.now(timezone.utc) + timedelta(minutes=2)
        self.assertTrue(self.store.claim_pair("rid-1", "nonce-1", expiry))
        second = SQLiteReplayStore(self.db)
        self.assertFalse(second.claim_pair("rid-1", "nonce-2", expiry))
        self.assertFalse(second.claim_pair("rid-2", "nonce-1", expiry))

    def test_duplicate_nonce_rolls_back_new_request_id(self):
        expiry = datetime.now(timezone.utc) + timedelta(minutes=2)
        self.assertTrue(self.store.claim_pair("rid-1", "nonce-1", expiry))
        self.assertFalse(self.store.claim_pair("rid-2", "nonce-1", expiry))
        self.assertTrue(self.store.claim_pair("rid-2", "nonce-2", expiry))

    def test_expired_claims_are_cleaned_before_claim(self):
        past = datetime.now(timezone.utc) - timedelta(seconds=2)
        future = datetime.now(timezone.utc) + timedelta(minutes=2)
        self.assertTrue(self.store.claim_pair("rid", "nonce", past))
        self.assertTrue(self.store.claim_pair("rid", "nonce", future))


if __name__ == "__main__":
    unittest.main()
