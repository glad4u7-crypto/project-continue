"""Deterministic tests for dispatcher request validation (stdlib unittest)."""
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.dispatcher.request_guard import RequestRejected, validate_and_claim


class RequestGuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
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

    def claim(self, namespace, value, expires):
        key = (namespace, value)
        if key in self.claimed:
            return False
        self.claimed.add(key)
        return True

    def validate(self, envelope=None, claim=None):
        validate_and_claim(
            self.envelope if envelope is None else envelope,
            now=self.now,
            claim_once=self.claim if claim is None else claim,
        )

    def test_valid_request_claims_id_and_nonce(self):
        self.validate()
        self.assertEqual(len(self.claimed), 2)

    def test_malformed_missing_and_extra_fields_rejected(self):
        malformed = dict(self.envelope)
        malformed.pop("task")
        with self.assertRaises(RequestRejected):
            self.validate(malformed)
        malformed = dict(self.envelope, unexpected=True)
        with self.assertRaises(RequestRejected):
            self.validate(malformed)

    def test_malformed_timestamp_rejected(self):
        malformed = dict(self.envelope, issued_at="yesterday")
        with self.assertRaises(RequestRejected):
            self.validate(malformed)

    def test_expired_request_rejected(self):
        malformed = dict(self.envelope, expires_at=(self.now - timedelta(seconds=1)).isoformat())
        with self.assertRaises(RequestRejected):
            self.validate(malformed)

    def test_excessive_ttl_rejected(self):
        malformed = dict(self.envelope, expires_at=(self.now + timedelta(seconds=301)).isoformat())
        with self.assertRaises(RequestRejected):
            self.validate(malformed)

    def test_duplicate_request_id_rejected(self):
        self.validate()
        with self.assertRaises(RequestRejected):
            self.validate()

    def test_replayed_nonce_rejected(self):
        self.claimed.add(("nonce", self.envelope["nonce"]))
        with self.assertRaisesRegex(RequestRejected, "replay"):
            self.validate()

    def test_identity_repository_commit_and_task_shape_rejected(self):
        for key, value in (
            ("actor", {"id": "not-numeric", "type": "user"}),
            ("repository", {"id": 0, "full_name": "owner/repo"}),
            ("commit_sha", "bad"),
            ("task", "repo.delete_file"),
        ):
            malformed = dict(self.envelope, **{key: value})
            with self.subTest(key=key), self.assertRaises(RequestRejected):
                self.validate(malformed)

    def test_replay_store_failure_propagates(self):
        def unavailable(*args):
            raise RuntimeError("store unavailable")
        with self.assertRaises(RuntimeError):
            self.validate(claim=unavailable)


if __name__ == "__main__":
    unittest.main()
