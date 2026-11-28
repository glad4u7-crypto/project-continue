"""Tests for authorization-before-handler secure dispatcher orchestration."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from database.connection import Database
from src.dispatcher.request_guard import RequestGuard
from src.dispatcher.replay_store import SQLiteReplayStore
from src.dispatcher.runtime import AuthorizationRejected, SecureDispatcher, TaskArgumentsRejected


ROOT = Path(__file__).resolve().parents[1]


class SecureDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.database = Database(Path(self.tempdir.name) / "dispatcher.sqlite3")
        self.store = SQLiteReplayStore(self.database)
        self.store.initialize()
        self.guard = RequestGuard(self.store)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.policy = json.loads((ROOT / "schemas/dispatcher/authorization-policy.v1.json").read_text())
        self.registry = json.loads((ROOT / "schemas/dispatcher/task-registry.v1.json").read_text())
        self.calls = []
        self.dispatcher = self.make_dispatcher()

    def tearDown(self):
        self.database.close()
        self.tempdir.cleanup()

    def make_dispatcher(self, **overrides):
        options = {
            "policy": self.policy,
            "registry": self.registry,
            "request_guard": self.guard,
            "authenticated_identity": lambda: {"id": "354281323", "login": "glad4u7-crypto", "type": "user"},
            "repository_lookup": lambda rid: {"id": rid, "full_name": "glad4u7-crypto/project-continue", "owner_id": 354281323},
            "permission_lookup": lambda login, repo: "admin",
            "commit_verifier": lambda repo, sha: sha == "a" * 40,
            "handlers": {"repo.read_file.v1": lambda env, args: self.calls.append((env, args)) or {"ok": True}},
        }
        options.update(overrides)
        return SecureDispatcher(**options)

    def envelope(self, **changes):
        value = {
            "schema_version": "1.0",
            "request_id": str(uuid4()),
            "nonce": str(uuid4()),
            "idempotency_key": "retry-key-12345678",
            "actor": {"id": "354281323", "type": "user"},
            "repository": {"id": 1463557248, "full_name": "glad4u7-crypto/project-continue", "commit_sha": "a" * 40},
            "task": {"task_id": "repo.read_file", "arguments": {"path": "README.md"}},
            "issued_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(seconds=90)).isoformat(),
        }
        value.update(changes)
        return value

    def test_authorized_request_calls_only_fixed_handler(self):
        result = self.dispatcher.dispatch(self.envelope(), now=self.now)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(self.calls), 1)

    def test_untrusted_actor_claim_cannot_override_authenticated_identity(self):
        envelope = self.envelope(actor={"id": "999", "type": "user"})
        with self.assertRaises(AuthorizationRejected):
            self.dispatcher.dispatch(envelope, now=self.now)
        self.assertEqual(self.calls, [])

    def test_unlisted_repository_is_rejected(self):
        envelope = self.envelope(repository={"id": 7, "full_name": "attacker/repo", "commit_sha": "a" * 40})
        with self.assertRaises(AuthorizationRejected):
            self.dispatcher.dispatch(envelope, now=self.now)

    def test_live_repository_mismatch_is_rejected(self):
        dispatcher = self.make_dispatcher(repository_lookup=lambda rid: {"id": rid, "full_name": "fork/repo", "owner_id": 354281323})
        with self.assertRaises(AuthorizationRejected):
            dispatcher.dispatch(self.envelope(), now=self.now)

    def test_insufficient_permission_is_rejected(self):
        dispatcher = self.make_dispatcher(permission_lookup=lambda login, repo: "read")
        with self.assertRaises(AuthorizationRejected):
            dispatcher.dispatch(self.envelope(), now=self.now)

    def test_unverified_commit_is_rejected(self):
        dispatcher = self.make_dispatcher(commit_verifier=lambda repo, sha: False)
        with self.assertRaises(AuthorizationRejected):
            dispatcher.dispatch(self.envelope(), now=self.now)

    def test_unknown_task_is_rejected_before_handler_lookup(self):
        envelope = self.envelope(task={"task_id": "repo.delete", "arguments": {}})
        with self.assertRaises(AuthorizationRejected):
            self.dispatcher.dispatch(envelope, now=self.now)

    def test_invalid_arguments_are_rejected_before_handler_call(self):
        envelope = self.envelope(task={"task_id": "repo.read_file", "arguments": {"path": "../secret"}})
        with self.assertRaises(TaskArgumentsRejected):
            self.dispatcher.dispatch(envelope, now=self.now)
        self.assertEqual(self.calls, [])

    def test_replay_is_rejected_before_second_handler_call(self):
        envelope = self.envelope()
        self.dispatcher.dispatch(envelope, now=self.now)
        with self.assertRaises(ValueError):
            self.dispatcher.dispatch(envelope, now=self.now)
        self.assertEqual(len(self.calls), 1)

    def test_identity_lookup_failure_fails_closed(self):
        dispatcher = self.make_dispatcher(authenticated_identity=lambda: None)
        with self.assertRaises(AuthorizationRejected):
            dispatcher.dispatch(self.envelope(), now=self.now)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
