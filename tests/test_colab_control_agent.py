from unittest.mock import patch

from scripts.colab_control_agent import (
    COMMAND_RE, CREATE_NOTEBOOK_COMMAND_RE, DISCOVERY_COMMAND_RE, READ_COMMAND_RE,
    process_comments, read_project_file, run_task,
)


def test_parser_accepts_only_fixed_commands():
    for name in ("phase18-tests", "compile", "dashboard-health", "git-status"):
        assert COMMAND_RE.fullmatch("/pc-run " + name)
    assert not COMMAND_RE.fullmatch("/pc-run pytest; rm -rf /")
    assert not COMMAND_RE.fullmatch("/pc-run python -c 'print(1)'")
    assert not COMMAND_RE.fullmatch("/pc-run compile --unsafe")


def test_discovery_command_is_exact():
    assert DISCOVERY_COMMAND_RE.fullmatch("/pc-discover")
    assert not DISCOVERY_COMMAND_RE.fullmatch("/pc-discover /content")
    assert not DISCOVERY_COMMAND_RE.fullmatch("/pc-discover; rm -rf /")


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



def test_read_command_accepts_only_allowlisted_paths():
    assert READ_COMMAND_RE.fullmatch("/pc-read README.md")
    assert READ_COMMAND_RE.fullmatch("/pc-read app.py")
    assert not READ_COMMAND_RE.fullmatch("/pc-read ../../.env")
    assert not READ_COMMAND_RE.fullmatch("/pc-read secrets.json")


def test_read_project_file_is_bounded_and_allowlisted(tmp_path):
    (tmp_path / "README.md").write_text("safe project text", encoding="utf-8")
    with patch("scripts.colab_control_agent.REPO_ROOT", tmp_path):
        assert read_project_file("README.md") == (
            True, "File: README.md\n\nsafe project text"
        )
        passed, detail = read_project_file("../.env")
        assert not passed and "not allow-listed" in detail


def test_read_project_file_rejects_oversized_files(tmp_path):
    (tmp_path / "README.md").write_text("x" * 12001, encoding="utf-8")
    with patch("scripts.colab_control_agent.REPO_ROOT", tmp_path):
        passed, detail = read_project_file("README.md")
    assert not passed and "12 KB" in detail


def test_read_project_file_rejects_symlinked_file(tmp_path):
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("must not be read", encoding="utf-8")
    (tmp_path / "README.md").symlink_to(outside)
    with patch("scripts.colab_control_agent.REPO_ROOT", tmp_path):
        passed, detail = read_project_file("README.md")
    assert not passed
    assert "unavailable" in detail or "unsafe" in detail


def test_read_project_file_rejects_symlinked_parent(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "colab_control_agent.py").write_text("secret", encoding="utf-8")
    (tmp_path / "scripts").symlink_to(real_dir, target_is_directory=True)
    with patch("scripts.colab_control_agent.REPO_ROOT", tmp_path):
        passed, detail = read_project_file("scripts/colab_control_agent.py")
    assert not passed
    assert "unavailable" in detail or "unsafe" in detail


def test_read_project_file_rejects_non_regular_file(tmp_path):
    (tmp_path / "README.md").mkdir()
    with patch("scripts.colab_control_agent.REPO_ROOT", tmp_path):
        passed, detail = read_project_file("README.md")
    assert not passed



def test_discovery_command_returns_only_aggregate_report(tmp_path):
    command = {
        "id": 201,
        "user": {"login": "glad4u7-crypto"},
        "body": "/pc-discover",
    }

    def fake_api_request(token, method, url, payload=None):
        if method == "GET":
            return [command] if url.endswith("&page=1") else []
        if method == "POST":
            assert "notebook-discovery" in payload["body"]
            assert "private-name.ipynb" not in payload["body"]
            return {"id": 999}
        raise AssertionError(f"Unexpected API call: {method} {url}")

    with (
        patch("scripts.colab_control_agent.STATE_PATH", tmp_path / "state.json"),
        patch("scripts.colab_control_agent.api_request", side_effect=fake_api_request),
        patch(
            "scripts.colab_control_agent.discover_project_files",
            return_value=(True, "Metadata-only discovery completed. notebooks=2"),
        ) as discover,
    ):
        processed = process_comments("token", 59, {"last_comment_id": 0})

    assert processed == 1
    discover.assert_called_once()



def test_create_notebook_command_is_strict():
    assert CREATE_NOTEBOOK_COMMAND_RE.fullmatch("/pc-create-notebook Analysis 01")
    assert not CREATE_NOTEBOOK_COMMAND_RE.fullmatch("/pc-create-notebook ../escape")
    assert not CREATE_NOTEBOOK_COMMAND_RE.fullmatch("/pc-create-notebook folder/name")
    assert not CREATE_NOTEBOOK_COMMAND_RE.fullmatch("/pc-create-notebook Analysis; rm -rf /")


def test_authorized_issue_command_creates_notebook_and_posts_report(tmp_path):
    command = {
        "id": 301,
        "user": {"login": "glad4u7-crypto"},
        "body": "/pc-create-notebook Created By Agent",
    }

    def fake_api_request(token, method, url, payload=None):
        if method == "GET":
            return [command] if url.endswith("&page=1") else []
        if method == "POST":
            assert "notebook-create" in payload["body"]
            assert "Created By Agent.ipynb" in payload["body"]
            return {"id": 1001}
        raise AssertionError(f"Unexpected API call: {method} {url}")

    with (
        patch("scripts.colab_control_agent.STATE_PATH", tmp_path / "state.json"),
        patch("scripts.colab_control_agent.api_request", side_effect=fake_api_request),
        patch(
            "scripts.colab_control_agent.create_notebook",
            return_value=(True, "Notebook created. File: Created By Agent.ipynb"),
        ) as create,
    ):
        processed = process_comments("token", 59, {"last_comment_id": 0})

    assert processed == 1
    create.assert_called_once_with("Created By Agent")
