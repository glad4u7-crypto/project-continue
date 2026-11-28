import hashlib
import json

import pytest

from scripts.phase20_notebook_policy import authorize_notebook


def test_policy_requires_exact_commit_content_and_explicit_approval(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text('{"nbformat":4,"nbformat_minor":5,"metadata":{},"cells":[]}', encoding="utf-8")
    digest = hashlib.sha256(notebook.read_bytes()).hexdigest()
    commit = "a" * 40
    policy = tmp_path / "allow.json"
    policy.write_text(json.dumps({
        "schema_version": 1,
        "entries": [{
            "path": "safe.ipynb", "sha256": digest, "approval_id": "review-123",
            "enabled": True, "network_access": False, "secrets_access": False,
            "external_mounts": False,
        }],
    }), encoding="utf-8")
    result = authorize_notebook(tmp_path, "safe.ipynb", current_commit=commit,
                                requested_commit=commit, approval_id="review-123",
                                policy_path=policy)
    assert result["authorized"]
    assert result["sha256"] == digest
    assert result["network_access"] is False


def test_policy_denies_unlisted_or_modified_notebook(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    policy = tmp_path / "allow.json"
    policy.write_text('{"schema_version":1,"entries":[]}', encoding="utf-8")
    args = dict(current_commit="a" * 40, requested_commit="a" * 40,
                approval_id="review-123", policy_path=policy)
    with pytest.raises(PermissionError):
        authorize_notebook(tmp_path, "safe.ipynb", **args)


def test_policy_denies_stale_commit_and_unsafe_capabilities(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    policy = tmp_path / "allow.json"
    policy.write_text(json.dumps({"schema_version": 1, "entries": [{
        "path": "safe.ipynb", "sha256": hashlib.sha256(notebook.read_bytes()).hexdigest(),
        "approval_id": "review-123", "enabled": True,
        "network_access": True, "secrets_access": False, "external_mounts": False,
    }]}), encoding="utf-8")
    with pytest.raises(PermissionError):
        authorize_notebook(tmp_path, "safe.ipynb", current_commit="a"*40,
                           requested_commit="b"*40, approval_id="review-123", policy_path=policy)
    with pytest.raises(PermissionError):
        authorize_notebook(tmp_path, "safe.ipynb", current_commit="a"*40,
                           requested_commit="a"*40, approval_id="review-123", policy_path=policy)


def test_policy_rejects_traversal_symlink_and_missing_approval(tmp_path):
    outside = tmp_path.parent / "outside.ipynb"
    outside.write_text("{}", encoding="utf-8")
    (tmp_path / "link.ipynb").symlink_to(outside)
    policy = tmp_path / "allow.json"
    policy.write_text('{"schema_version":1,"entries":[]}', encoding="utf-8")
    args = dict(current_commit="a"*40, requested_commit="a"*40,
                approval_id="review-123", policy_path=policy)
    for name in ("../outside.ipynb", "link.ipynb", ".hidden.ipynb"):
        with pytest.raises(PermissionError):
            authorize_notebook(tmp_path, name, **args)
    with pytest.raises(PermissionError):
        authorize_notebook(tmp_path, "outside.ipynb", current_commit="a"*40,
                           requested_commit="a"*40, approval_id="", policy_path=policy)
