"""Tests for the ACK/RUNNING/terminal execution lifecycle."""
import unittest
from datetime import datetime, timedelta, timezone

from src.dispatcher.execution_state import (
    ExecutionState,
    ExecutionStateMachine,
    InvalidTransition,
    StaleStateVersion,
)


class ExecutionStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)
        self.machine = ExecutionStateMachine(now=self.now)

    def test_initial_state_is_ack_with_version_one(self):
        self.assertEqual(self.machine.state, ExecutionState.ACK)
        self.assertEqual(self.machine.version, 1)
        self.assertFalse(self.machine.is_terminal)

    def test_ack_to_running_to_pass(self):
        self.machine.transition("RUNNING", now=self.now + timedelta(seconds=1), expected_version=1)
        event = self.machine.transition("PASS", now=self.now + timedelta(seconds=2), expected_version=2)
        self.assertEqual(event.version, 3)
        self.assertEqual(self.machine.state, ExecutionState.PASS)
        self.assertTrue(self.machine.is_terminal)

    def test_running_can_end_in_each_terminal_state(self):
        for target in ("PASS", "FAIL", "BLOCKED", "CANCELLED"):
            with self.subTest(target=target):
                machine = ExecutionStateMachine(now=self.now)
                machine.transition("RUNNING", now=self.now + timedelta(seconds=1))
                reason = "test terminal outcome" if target in {"FAIL", "BLOCKED", "CANCELLED"} else None
                machine.transition(target, now=self.now + timedelta(seconds=2), reason=reason)
                self.assertTrue(machine.is_terminal)

    def test_ack_can_be_blocked_or_cancelled(self):
        for target in ("BLOCKED", "CANCELLED"):
            with self.subTest(target=target):
                machine = ExecutionStateMachine(now=self.now)
                machine.transition(target, now=self.now + timedelta(seconds=1), reason="preflight rejected")
                self.assertEqual(machine.state.value, target)

    def test_ack_cannot_jump_directly_to_pass_or_fail(self):
        for target in ("PASS", "FAIL"):
            with self.subTest(target=target), self.assertRaises(InvalidTransition):
                self.machine.transition(target, now=self.now + timedelta(seconds=1), reason="not allowed")

    def test_running_cannot_return_to_ack_or_repeat_running(self):
        self.machine.transition("RUNNING", now=self.now + timedelta(seconds=1))
        for target in ("ACK", "RUNNING"):
            with self.subTest(target=target), self.assertRaises(InvalidTransition):
                self.machine.transition(target, now=self.now + timedelta(seconds=2))

    def test_terminal_state_cannot_transition_again(self):
        self.machine.transition("CANCELLED", now=self.now + timedelta(seconds=1), reason="cancelled")
        with self.assertRaises(InvalidTransition):
            self.machine.transition("RUNNING", now=self.now + timedelta(seconds=2))

    def test_failure_block_and_cancel_require_reason(self):
        for target in ("FAIL", "BLOCKED", "CANCELLED"):
            with self.subTest(target=target):
                machine = ExecutionStateMachine(now=self.now)
                machine.transition("RUNNING", now=self.now + timedelta(seconds=1))
                with self.assertRaises(InvalidTransition):
                    machine.transition(target, now=self.now + timedelta(seconds=2))

    def test_stale_version_is_rejected_without_mutation(self):
        with self.assertRaises(StaleStateVersion):
            self.machine.transition("RUNNING", now=self.now + timedelta(seconds=1), expected_version=0)
        self.assertEqual(self.machine.version, 1)
        self.assertEqual(self.machine.state, ExecutionState.ACK)

    def test_invalid_timestamp_and_unknown_state_are_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionStateMachine(now=datetime(2026, 11, 28))
        with self.assertRaises(InvalidTransition):
            self.machine.transition("UNKNOWN", now=self.now + timedelta(seconds=1))

    def test_event_history_is_immutable_and_timestamps_monotonic(self):
        self.machine.transition("RUNNING", now=self.now + timedelta(seconds=1))
        snapshot = self.machine.history
        with self.assertRaises(AttributeError):
            snapshot.append("tamper")
        with self.assertRaises(InvalidTransition):
            self.machine.transition("PASS", now=self.now)
        self.assertEqual(self.machine.state, ExecutionState.RUNNING)
        self.assertEqual(len(self.machine.history), 2)


if __name__ == "__main__":
    unittest.main()
