"""Default-deny, commit-bound notebook execution authorization."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

MAX_POLICY_BYTES = 16 * 1024
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def authorize_notebook(
    notebook_root: str | Path,
    notebook_name: str,
    *,
    current_commit: str,
    requested_commit: str,
    approval_id: str,
    policy_path: str | Path,
) -> dict[str, Any]:
    """Authorize only an exact path+content hash+commit+approval tuple.

    Policy entries must explicitly deny network, secrets and mounted external data.
    An empty/missing/invalid policy fails closed.
    """
    if not _SHA.fullmatch(current_commit or "") or requested_commit != current_commit:
        raise PermissionError("notebook execution commit binding mismatch")
    if not isinstance(approval_id, str) or not approval_id.strip() or len(approval_id) > 128:
        raise PermissionError("explicit approval identifier is required")
    root = Path(notebook_root).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise PermissionError("unsafe notebook root")
    relative = Path(notebook_name)
    if relative.is_absolute() or any(part in ("", ".", "..") or part.startswith(".") for part in relative.parts):
        raise PermissionError("unsafe notebook identity")
    if relative.suffix.lower() != ".ipynb" or "\\" in notebook_name:
        raise PermissionError("only safe .ipynb identities are allowed")
    target = root / relative
    if target.is_symlink() or not target.resolve(strict=True).is_relative_to(root) or not target.is_file():
        raise PermissionError("notebook is not a regular file within the root")
    if target.stat().st_size > 256 * 1024:
        raise PermissionError("notebook exceeds execution size limit")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    policy = Path(policy_path)
    if policy.is_symlink() or not policy.is_file() or policy.stat().st_size > MAX_POLICY_BYTES:
        raise PermissionError("execution allow-list is missing or unsafe")
    try:
        data = json.loads(policy.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PermissionError("execution allow-list is invalid") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("entries"), list):
        raise PermissionError("execution allow-list schema is invalid")
    for entry in data["entries"]:
        if not isinstance(entry, dict):
            continue
        if (entry.get("path") == relative.as_posix()
                and entry.get("sha256") == digest
                and entry.get("approval_id") == approval_id
                and entry.get("enabled") is True
                and entry.get("network_access") is False
                and entry.get("secrets_access") is False
                and entry.get("external_mounts") is False):
            return {
                "authorized": True,
                "path": relative.as_posix(),
                "sha256": digest,
                "commit_sha": current_commit,
                "approval_id": approval_id,
                "network_access": False,
                "secrets_access": False,
                "external_mounts": False,
            }
    raise PermissionError("notebook is not explicitly allow-listed for this exact content and approval")
