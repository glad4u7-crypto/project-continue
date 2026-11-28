"""Safety and diagnostic-contract tests for the fixed-task ephemeral runner."""
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts.phase20_runner import (
    MAX_OUTPUT_BYTES,
    MAX_RETRIES,
    REPOSITORY_ROOT,
    TASK_TIMEOUT_SECONDS,
    _apply_child_limits,
    build_command,
    classify_failure,
    parse_test_counts,
    run_task,
)


class Phase20RunnerTests(unittest.TestCase):
    def test_only_exact_allowlisted_tasks_have_commands(self):
        for task in ("compile", "dispatcher-tests", "full-tests"):
            self.assertTrue(build_command(task))
        for task in ("python -c 'bad'", "../compile", "shell", "", "--help"):
            with self.subTest(task=task), self.assertRaises(ValueError):
                build_command(task)

    def test_commands_never_use_shell_or_caller_supplied_arguments(self):
        command = build_command("dispatcher-tests")
        self.assertEqual(command[1:4], ("-m", "pytest", "-q"))
        self.assertTrue(all(path.startswith("tests/test_dispatcher_") for path in command[4:]))
        self.assertNotIn("shell", command)

    @patch("scripts.phase20_runner.subprocess.Popen")
    def test_runner_uses_timeout_minimal_environment_and_no_shell(self, popen):
        process = SimpleNamespace(
            stdout=io.BytesIO(b"ok\n"), pid=123, returncode=0,
            wait=unittest.mock.Mock(return_value=0),
        )
        popen.return_value = process
        # The new runner writes stdout/stderr to separate bounded temporary files.
        self.assertEqual(run_task("compile"), 0)
        kwargs = popen.call_args.kwargs
        self.assertEqual(kwargs["cwd"], REPOSITORY_ROOT)
        self.assertTrue(kwargs["start_new_session"])
        self.assertIs(kwargs["preexec_fn"], _apply_child_limits)
        self.assertFalse(kwargs["shell"])
        self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
        self.assertNotIn("ACTIONS_RUNTIME_TOKEN", kwargs["env"])
        self.assertEqual(
            set(kwargs["env"]),
            {"PATH", "HOME", "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE"},
        )
        self.assertEqual(process.wait.call_args.kwargs["timeout"], TASK_TIMEOUT_SECONDS)

    @patch("scripts.phase20_runner.os.killpg")
    @patch("scripts.phase20_runner.subprocess.Popen")
    def test_timeout_kills_process_group(self, popen, killpg):
        process = SimpleNamespace(
            pid=123, returncode=-9,
            wait=unittest.mock.Mock(side_effect=[
                __import__("subprocess").TimeoutExpired(cmd="pytest", timeout=TASK_TIMEOUT_SECONDS),
                -9,
            ]),
        )
        popen.return_value = process
        self.assertEqual(run_task("full-tests"), 124)
        killpg.assert_called_once()

    @patch("scripts.phase20_runner.resource.setrlimit")
    def test_child_cpu_and_core_dump_limits_are_applied(self, setrlimit):
        import resource
        _apply_child_limits()
        setrlimit.assert_any_call(
            resource.RLIMIT_CPU, (TASK_TIMEOUT_SECONDS, TASK_TIMEOUT_SECONDS + 10)
        )
        setrlimit.assert_any_call(resource.RLIMIT_CORE, (0, 0))

    @patch("scripts.phase20_runner.build_command")
    def test_real_child_stdout_and_stderr_are_captured_separately(self, build):
        import sys
        from scripts.phase20_runner import _run_once
        build.return_value = (
            sys.executable, "-c",
            "import sys; print('stdout-sentinel'); print('stderr-sentinel', file=sys.stderr)",
        )
        result = _run_once("compile")
        self.assertEqual(result["classification"], "success")
        self.assertIn("stdout-sentinel", result["stdout"])
        self.assertNotIn("stderr-sentinel", result["stdout"])
        self.assertIn("stderr-sentinel", result["stderr"])
        self.assertNotIn("stdout-sentinel", result["stderr"])

    def test_output_parser_extracts_pytest_counts(self):
        output = "================ 12 passed, 2 skipped in 3.21s ================\n"
        self.assertEqual(parse_test_counts(output), {"passed": 12, "skipped": 2})

    def test_intentional_failing_fixture_is_classified_as_code_failure(self):
        # Synthetic pytest failure fixture: deliberately failing assertion evidence.
        output = "FAILED tests/fixtures/test_intentional_failure.py::test_expected_failure - AssertionError"
        self.assertEqual(classify_failure("full-tests", 1, output, ""), "code")

    def test_failure_classification_distinguishes_timeout_permission_dependency(self):
        self.assertEqual(classify_failure("compile", 124, "", "", True), "timeout")
        self.assertEqual(classify_failure("compile", 1, "", "Permission denied"), "permission")
        self.assertEqual(classify_failure("full-tests", 1, "", "ModuleNotFoundError"), "dependency")

    def test_retry_limit_is_validated(self):
        with self.assertRaises(ValueError):
            run_task("compile", retries=MAX_RETRIES + 1)

    @patch("scripts.phase20_runner._run_once")
    def test_only_transient_infrastructure_failure_is_retried_once(self, run_once):
        run_once.side_effect = [
            {"classification": "infrastructure", "task": "compile", "exit_code": 1,
             "duration_seconds": 0.1, "test_counts": {}, "stdout": "", "stderr": "",
             "stdout_truncated": False, "stderr_truncated": False},
            {"classification": "success", "task": "compile", "exit_code": 0,
             "duration_seconds": 0.1, "test_counts": {}, "stdout": "", "stderr": "",
             "stdout_truncated": False, "stderr_truncated": False},
        ]
        self.assertEqual(run_task("compile", retries=1), 0)
        self.assertEqual(run_once.call_count, 2)

    @patch("scripts.phase20_runner._run_once")
    def test_code_failure_is_not_retried(self, run_once):
        run_once.return_value = {
            "classification": "code", "task": "full-tests", "exit_code": 1,
            "duration_seconds": 0.1, "test_counts": {"failed": 1},
            "stdout": "", "stderr": "", "stdout_truncated": False,
            "stderr_truncated": False,
        }
        self.assertEqual(run_task("full-tests", retries=1), 1)
        self.assertEqual(run_once.call_count, 1)


if __name__ == "__main__":
    unittest.main()
