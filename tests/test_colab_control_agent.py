from unittest.mock import patch
from scripts.colab_control_agent import COMMAND_RE, run_task

def test_parser_accepts_only_fixed_commands():
    for name in ("phase18-tests", "compile", "dashboard-health", "git-status"):
        assert COMMAND_RE.fullmatch("/pc-run " + name)
    assert not COMMAND_RE.fullmatch("/pc-run pytest; rm -rf /")
    assert not COMMAND_RE.fullmatch("/pc-run python -c 'print(1)'")
    assert not COMMAND_RE.fullmatch("/pc-run compile --unsafe")

def test_unknown_task_is_rejected():
    passed, output = run_task("arbitrary-shell")
    assert not passed and "not allow-listed" in output

def test_dashboard_health_is_read_only():
    with patch("scripts.colab_control_agent.check_local_streamlit", return_value=(True, "HTTP 200")):
        assert run_task("dashboard-health") == (True, "HTTP 200")

def test_subprocess_never_uses_shell():
    with patch("scripts.colab_control_agent.subprocess.run") as run:
        run.return_value.returncode=0
        run.return_value.stdout="ok"
        run.return_value.stderr=""
        passed,output=run_task("git-status")
    assert passed and "ok" in output
    assert run.call_args.kwargs["shell"] is False
