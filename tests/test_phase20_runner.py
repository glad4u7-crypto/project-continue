"""Safety tests for the fixed-task ephemeral runner."""
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts.phase20_runner import (
    MAX_OUTPUT_BYTES,
    REPOSITORY_ROOT,
    TASK_TIMEOUT_SECONDS,
    build_command,
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
        self.assertEqual(run_task("compile"), 0)
        kwargs = popen.call_args.kwargs
        self.assertEqual(kwargs["cwd"], REPOSITORY_ROOT)
        self.assertTrue(kwargs["start_new_session"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["stdout"], unittest.mock.ANY)
        self.assertEqual(
            set(kwargs["env"]),
            {"PATH", "HOME", "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE"},
        )
        self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
        self.assertNotIn("ACTIONS_RUNTIME_TOKEN", kwargs["env"])
        self.assertEqual(process.wait.call_args.kwargs["timeout"], TASK_TIMEOUT_SECONDS)

    @patch("scripts.phase20_runner.os.killpg")
    @patch("scripts.phase20_runner.subprocess.Popen")
    def test_timeout_kills_process_group_and_returns_124(self, popen, killpg):
        process = SimpleNamespace(
            stdout=io.BytesIO(b"timed out"), pid=123, returncode=-9,
            wait=unittest.mock.Mock(side_effect=[
                __import__("subprocess").TimeoutExpired(cmd="pytest", timeout=TASK_TIMEOUT_SECONDS),
                -9,
            ]),
        )
        popen.return_value = process
        self.assertEqual(run_task("full-tests"), 124)
        killpg.assert_called_once()

    @patch("scripts.phase20_runner.subprocess.Popen")
    def test_output_is_truncated_to_fixed_bound(self, popen):
        process = SimpleNamespace(
            stdout=io.BytesIO(b"x" * (MAX_OUTPUT_BYTES + 1024)),
            pid=123, returncode=0, wait=unittest.mock.Mock(return_value=0),
        )
        popen.return_value = process
        with patch("sys.stdout", new_callable=io.StringIO) as captured:
            self.assertEqual(run_task("compile"), 0)
            rendered = captured.getvalue()
        self.assertIn("runner output truncated", rendered)
        self.assertLessEqual(len(rendered.encode("utf-8")), MAX_OUTPUT_BYTES + 200)


if __name__ == "__main__":
    unittest.main()
