import json

from scripts.colab_notebook_creation import create_notebook


def test_create_notebook_writes_valid_starter_json(tmp_path):
    passed, report = create_notebook("Analysis 01", configured_root=tmp_path)

    assert passed
    assert "No code was executed" in report
    target = tmp_path / "Analysis 01.ipynb"
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["nbformat"] == 4
    assert len(document["cells"]) == 2
    assert document["cells"][0]["cell_type"] == "markdown"
    assert document["cells"][1]["cell_type"] == "code"
    assert document["cells"][1]["source"] == []
    assert document["cells"][1]["execution_count"] is None
    assert document["cells"][1]["outputs"] == []


def test_create_notebook_never_overwrites_existing_file(tmp_path):
    target = tmp_path / "Existing.ipynb"
    original = '{"keep":"untouched"}'
    target.write_text(original, encoding="utf-8")

    passed, report = create_notebook("Existing", configured_root=tmp_path)

    assert not passed
    assert "already exists" in report
    assert target.read_text(encoding="utf-8") == original


def test_create_notebook_rejects_path_traversal_and_invalid_names(tmp_path):
    for name in ("../escape", "folder/name", ".hidden", "name.ipynb", "bad\\name", ""):
        passed, _ = create_notebook(name, configured_root=tmp_path)
        assert not passed
    assert not (tmp_path.parent / "escape.ipynb").exists()


def test_create_notebook_requires_existing_configured_directory(tmp_path):
    passed, report = create_notebook("Safe", configured_root=tmp_path / "missing")
    assert not passed
    assert "unavailable or unsafe" in report


def test_create_notebook_rejects_symlinked_destination(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)

    passed, report = create_notebook("Safe", configured_root=link)

    assert not passed
    assert "unavailable or unsafe" in report
    assert not (real / "Safe.ipynb").exists()


def test_create_notebook_uses_explicit_environment_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_CONTINUE_NOTEBOOK_CREATE_DIR", str(tmp_path))

    passed, _ = create_notebook("From Env")

    assert passed
    assert (tmp_path / "From Env.ipynb").is_file()


def test_create_notebook_rejects_symlink_collision(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("untouched", encoding="utf-8")
    (tmp_path / "Linked.ipynb").symlink_to(outside)

    passed, report = create_notebook("Linked", configured_root=tmp_path)

    assert not passed
    assert "already exists" in report
    assert outside.read_text(encoding="utf-8") == "untouched"


def test_create_notebook_report_contains_hash_and_no_absolute_path(tmp_path):
    passed, report = create_notebook("Report", configured_root=tmp_path)

    assert passed
    assert "SHA-256:" in report
    assert str(tmp_path) not in report
    assert "Report.ipynb" in report
