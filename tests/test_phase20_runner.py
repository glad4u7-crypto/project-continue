"""Safety tests for the fixed-task ephemeral runner."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts.phase20_runner import (
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

    @patch("scripts.phase20_runner.subprocess.run")
    def test_runner_uses_bounded_timeout_and_minimal_environment(self, run):
        run.return_value = SimpleNamespace(returncode=0)
        self.assertEqual(run_task("compile"), 0)
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["cwd"], REPOSITORY_ROOT)
        self.assertEqual(kwargs["timeout"], TASK_TIMEOUT_SECONDS)
        self.assertFalse(kwargs.get("shell", False))
        self.assertEqual(
            set(kwargs["env"]),
            {"PATH", "HOME", "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE"},
        )
        self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
        self.assertNotIn("ACTIONS_RUNTIME_TOKEN", kwargs["env"])

    @patch("scripts.phase20_runner.subprocess.run")
    def test_timeout_is_reported_as_exit_124(self, run):
        from subprocess import TimeoutExpired
        run.side_effect = TimeoutExpired(cmd="pytest", timeout=TASK_TIMEOUT_SECONDS)
        self.assertEqual(run_task("full-tests"), 124)


if __name__ == "__main__":
    unittest.main()
