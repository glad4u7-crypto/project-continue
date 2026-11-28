from scripts.notebook_execution_policy import authorize_notebook_execution

COMMIT = "a" * 40
BLOB = "544c131c97101485c4f328f83de1f96e65162dad"
PATH = "notebooks/ProjectContinue-Recovery.ipynb"


def _request(**overrides):
    request = {"notebook_path": PATH, "commit_sha": COMMIT, "blob_sha": BLOB}
    request.update(overrides)
    return request


def _authorize(request):
    return authorize_notebook_execution(
        request,
        checked_out_commit_sha=COMMIT,
        resolved_notebook_path=PATH,
        resolved_blob_sha=BLOB,
    )


def test_exact_allowlisted_notebook_and_immutable_checkout_are_authorized():
    passed, errors = _authorize(_request())
    assert passed
    assert errors == ()


def test_unlisted_path_and_path_traversal_are_rejected():
    for path in ("notebooks/other.ipynb", "../notebooks/ProjectContinue-Recovery.ipynb",
                 "/notebooks/ProjectContinue-Recovery.ipynb"):
        passed, errors = _authorize(_request(notebook_path=path))
        assert not passed
        assert errors


def test_mutable_or_mismatched_commit_identity_is_rejected():
    for commit in ("main", "a" * 39, "b" * 40):
        passed, errors = _authorize(_request(commit_sha=commit))
        assert not passed
        assert errors


def test_changed_or_mismatched_notebook_blob_is_rejected():
    passed, errors = _authorize(_request(blob_sha="c" * 40))
    assert not passed
    assert errors
    passed, errors = authorize_notebook_execution(
        _request(), checked_out_commit_sha=COMMIT,
        resolved_notebook_path=PATH, resolved_blob_sha="c" * 40,
    )
    assert not passed
    assert errors


def test_untrusted_request_cannot_supply_extra_or_missing_fields():
    passed, errors = _authorize(_request(extra="unexpected"))
    assert not passed
    assert errors
    passed, errors = _authorize({"notebook_path": PATH})
    assert not passed
    assert errors


def test_non_object_request_fails_closed():
    passed, errors = _authorize(["not-a-request"])
    assert not passed
    assert errors

def test_only_pinned_harmless_e2e_fixture_is_additionally_allowlisted():
    path = "tests/fixtures/notebooks/harmless_execution.ipynb"
    blob = "b62de83fd65d7faa0713ce52b8c87b4741ed9832"
    passed, errors = authorize_notebook_execution(
        {"notebook_path": path, "commit_sha": COMMIT, "blob_sha": blob},
        checked_out_commit_sha=COMMIT,
        resolved_notebook_path=path,
        resolved_blob_sha=blob,
    )
    assert passed
    assert errors == ()

def test_only_pinned_failure_mode_fixtures_are_additionally_allowlisted():
    fixtures = (
        ("tests/fixtures/notebooks/kernel_crash.ipynb", "43abfb0ea50c22f7321797ea32fb71a55d59e897"),
        ("tests/fixtures/notebooks/timeout.ipynb", "24bcb31a908db92035aa801b1e09e17d2714c7d3"),
    )
    for path, blob in fixtures:
        passed, errors = authorize_notebook_execution(
            {"notebook_path": path, "commit_sha": COMMIT, "blob_sha": blob},
            checked_out_commit_sha=COMMIT,
            resolved_notebook_path=path,
            resolved_blob_sha=blob,
        )
        assert passed
        assert errors == ()
