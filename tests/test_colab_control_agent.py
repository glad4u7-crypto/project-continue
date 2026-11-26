from unittest.mock import patch

from scripts.colab_control_agent import COMMAND_RE, process_comments, run_task


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
    with patch(
        "scripts.colab_control_agent.check_local_streamlit",
        return_value=(True, "HTTP 200"),
    ):
        assert run_task("dashboard-health") == (True, "HTTP 200")


def test_subprocess_never_uses_shell():
    with patch("scripts.colab_control_agent.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = "ok"
        run.return_value.stderr = ""
        passed, output = run_task("git-status")
    assert passed and "ok" in output
    assert run.call_args.kwargs["shell"] is False


def test_issue_queue_reads_beyond_first_100_comments(tmp_path):
    first_page = [
        {"id": i, "user": {"login": "someone-else"}, "body": "/pc-run compile"}
        for i in range(1, 101)
    ]
    command = {
        "id": 101,
        "user": {"login": "glad4u7-crypto"},
        "body": "/pc-run git-status",
    }

    def fake_api_request(token, method, url, payload=None):
        if method == "GET" and url.endswith("&page=1"):
            return first_page
        if method == "GET" and url.endswith("&page=2"):
            return [command]
        if method == "GET" and url.endswith("&page=3"):
            return []
        if method == "POST":
            return {"id": 999}
        raise AssertionError(f"Unexpected API call: {method} {url}")

    state = {"last_comment_id": 0}
    with (
        patch("scripts.colab_control_agent.STATE_PATH", tmp_path / "state.json"),
        patch("scripts.colab_control_agent.api_request", side_effect=fake_api_request) as api,
        patch("scripts.colab_control_agent.run_task", return_value=(True, "ok")) as task,
    ):
        processed = process_comments("token", 59, state)

    assert processed == 1
    task.assert_called_once_with("git-status")
    assert state["last_comment_id"] == 101
    assert any("page=2" in call.args[2] for call in api.call_args_list)
