"""Contract tests for structured test execution and bounded retry policy."""
import unittest
from unittest.mock import patch

from scripts.phase20_test_harness import (
    MAX_RETRIES, build_command, classify, run_task,
)


class TestHarnessTests(unittest.TestCase):
    def test_only_fixed_task_ids_are_accepted(self):
        for task in ("baseline", "compile", "focused", "full", "lint", "failure-probe"):
            self.assertTrue(task == "lint" or build_command(task))
        for task in ("python -c 'bad'", "../full", "shell", "--help", ""):
            with self.assertRaises(ValueError):
                build_command(task)

    def test_commands_do_not_accept_shell_or_user_arguments(self):
        for task in ("compile", "focused", "full"):
            command = build_command(task)
            self.assertNotIn("shell", command)
            self.assertEqual(command[1:3], ("-m", "compileall") if task == "compile" else ("-m", "pytest"))

    def test_failure_classification(self):
        self.assertEqual(classify(1, "", "AssertionError: bad")[0], "code")
        self.assertEqual(classify(1, "", "ModuleNotFoundError")[0], "dependency")
        self.assertEqual(classify(1, "", "Permission denied")[0], "permission")
        self.assertEqual(classify(1, "", "503 Service Unavailable")[0], "infrastructure")
        self.assertEqual(classify(124, "", "", timed_out=True), ("timeout", True))

    def test_pytest_counts_are_reported(self):
        from scripts.phase20_test_harness import _counts
        self.assertEqual(_counts("12 passed, 2 skipped, 1 failed, 1 error", ""), (12, 1, 2, 1))

    def test_output_is_bounded_and_redacted(self):
        from scripts.phase20_test_harness import _bounded, MAX_STREAM_BYTES
        value = _bounded("token=ghp_abcdefghijklmnopqrstuvwxyz1234567890 " + "x" * (MAX_STREAM_BYTES + 10))
        self.assertLessEqual(len(value.encode()), MAX_STREAM_BYTES + 32)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz1234567890", value)

    def test_retry_limit_is_strict(self):
        with self.assertRaises(ValueError):
            run_task("compile", retries=MAX_RETRIES + 1)
        with self.assertRaises(ValueError):
            run_task("compile", retries=-1)

    @patch("scripts.phase20_test_harness.subprocess.run")
    def test_infrastructure_failure_retries_once_then_stops(self, mocked):
        from types import SimpleNamespace
        mocked.side_effect = [
            SimpleNamespace(stdout="", stderr="503 Service Unavailable", returncode=1),
            SimpleNamespace(stdout="ok", stderr="", returncode=0),
        ]
        result = run_task("compile", retries=1)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.attempts, 2)

    @patch("scripts.phase20_test_harness.subprocess.run")
    def test_code_failure_is_not_retried(self, mocked):
        from types import SimpleNamespace
        mocked.return_value = SimpleNamespace(stdout="", stderr="AssertionError", returncode=1)
        result = run_task("full", retries=1)
        self.assertEqual(result.failure_class, "code")
        self.assertEqual(result.attempts, 1)

    @patch("scripts.phase20_test_harness.subprocess.run")
    def test_intentional_failure_probe_is_detected_not_hidden(self, mocked):
        from types import SimpleNamespace
        mocked.return_value = SimpleNamespace(stdout="", stderr="AssertionError: intentional", returncode=1)
        result = run_task("failure-probe")
        self.assertEqual(result.status, "EXPECTED_FAILURE_DETECTED")
        self.assertEqual(result.failure_class, "intentional-code-failure")


if __name__ == "__main__":
    unittest.main()
