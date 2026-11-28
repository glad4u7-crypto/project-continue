"""Fail-closed authorization for reviewed production and harmless test notebook identities.

This module authorizes identity only. It does not start a kernel or execute code.
A notebook content change requires an explicit reviewed allow-list update.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

_ALLOWED_NOTEBOOKS = {
    "notebooks/ProjectContinue-Recovery.ipynb": "544c131c97101485c4f328f83de1f96e65162dad",
    "tests/fixtures/notebooks/harmless_execution.ipynb": "b62de83fd65d7faa0713ce52b8c87b4741ed9832",
    "tests/fixtures/notebooks/kernel_crash.ipynb": "43abfb0ea50c22f7321797ea32fb71a55d59e897",
    "tests/fixtures/notebooks/timeout.ipynb": "24bcb31a908db92035aa801b1e09e17d2714c7d3",
}
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_FIELDS = frozenset({"notebook_path", "commit_sha", "blob_sha"})


def authorize_notebook_execution(
    request: Any,
    *,
    checked_out_commit_sha: str,
    resolved_notebook_path: str,
    resolved_blob_sha: str,
) -> tuple[bool, tuple[str, ...]]:
    """Authorize a request only for the pinned notebook in the exact checkout.

    The caller must obtain checked_out_commit_sha and resolved_blob_sha from
    the trusted checkout adapter, never from the untrusted request itself.
    """
    errors: list[str] = []
    if not isinstance(request, dict) or set(request) != _REQUIRED_FIELDS:
        return False, ("request must contain exactly notebook_path, commit_sha and blob_sha",)

    requested_path = request.get("notebook_path")
    if not isinstance(requested_path, str) or not requested_path:
        errors.append("notebook_path must be a non-empty string")
    else:
        candidate = PurePosixPath(requested_path)
        if candidate.is_absolute() or ".." in candidate.parts or str(candidate) != requested_path:
            errors.append("notebook_path is not a canonical repository-relative path")
        if requested_path not in _ALLOWED_NOTEBOOKS:
            errors.append("notebook_path is not allow-listed")

    requested_commit = request.get("commit_sha")
    if not isinstance(requested_commit, str) or not _GIT_SHA_RE.fullmatch(requested_commit):
        errors.append("commit_sha must be a full 40-character immutable SHA")
    if not isinstance(checked_out_commit_sha, str) or not _GIT_SHA_RE.fullmatch(checked_out_commit_sha):
        errors.append("trusted checkout commit SHA is invalid")
    elif requested_commit != checked_out_commit_sha:
        errors.append("request commit does not match the trusted checkout")

    requested_blob = request.get("blob_sha")
    if not isinstance(requested_blob, str) or not _GIT_SHA_RE.fullmatch(requested_blob):
        errors.append("blob_sha must be a full 40-character Git blob SHA")
    if not isinstance(resolved_notebook_path, str) or requested_path != resolved_notebook_path:
        errors.append("resolved notebook path does not match the request")
    expected_blob = _ALLOWED_NOTEBOOKS.get(requested_path) if isinstance(requested_path, str) else None
    if expected_blob is None or resolved_blob_sha != expected_blob:
        errors.append("resolved notebook content is not the reviewed allow-listed identity")
    if requested_blob != resolved_blob_sha:
        errors.append("request blob SHA does not match the resolved notebook")

    return not errors, tuple(errors)
