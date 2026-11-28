"""Safe immutable-snapshot reads and guarded feature-branch patch validation."""
from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$")
_ALLOWED_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".toml", ".txt", ".ini", ".cfg"}
_DENIED_NAMES = {".env", ".env.local", ".env.production"}
_DENIED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".db", ".sqlite", ".sqlite3", ".ipynb"}
_MAX_FILE_BYTES = 256 * 1024
_MAX_TREE_ENTRIES = 1000


class RepositoryAccessRejected(ValueError):
    """Raised when repository access or patch policy rejects an operation."""


@dataclass(frozen=True)
class RepositoryFile:
    path: str
    commit_sha: str
    content: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ValidatedPatch:
    path: str
    content: str
    size_bytes: int
    new_blob_sha: str
    previous_blob_sha: str | None


def _validate_sha(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA40.fullmatch(value):
        raise RepositoryAccessRejected(f"{field} must be a full 40-character commit/blob SHA")
    return value


def _safe_path(value: str, *, allow_root: bool = False) -> PurePosixPath:
    if allow_root and value == "":
        return PurePosixPath(".")
    if not isinstance(value, str) or not value or len(value) > 240:
        raise RepositoryAccessRejected("path is empty or exceeds 240 characters")
    if value.startswith("/") or "\\" in value or "\x00" in value:
        raise RepositoryAccessRejected("absolute, backslash or NUL paths are forbidden")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        raise RepositoryAccessRejected("hidden, empty and traversal path components are forbidden")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise RepositoryAccessRejected("absolute paths are forbidden")
    if path.name.lower() in _DENIED_NAMES or path.suffix.lower() in _DENIED_SUFFIXES:
        raise RepositoryAccessRejected("sensitive file path is forbidden")
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        raise RepositoryAccessRejected("file extension is not allow-listed")
    return path


def _blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


class RepositorySnapshot:
    """Read-only view rooted at a checkout already bound to an immutable SHA."""

    def __init__(self, root: str | Path, commit_sha: str) -> None:
        self.commit_sha = _validate_sha(commit_sha, "commit_sha")
        root_path = Path(root)
        if root_path.is_symlink() or not root_path.is_dir():
            raise RepositoryAccessRejected("repository root must be a real directory")
        self.root = root_path.resolve(strict=True)

    def _check_commit(self, expected_commit_sha: str) -> None:
        if _validate_sha(expected_commit_sha, "expected_commit_sha") != self.commit_sha:
            raise RepositoryAccessRejected("requested commit does not match immutable snapshot")

    def _resolve(self, relative: PurePosixPath) -> Path:
        target = self.root
        for component in relative.parts:
            target = target / component
            try:
                mode = target.lstat().st_mode
            except FileNotFoundError as exc:
                raise RepositoryAccessRejected("repository path does not exist") from exc
            if stat.S_ISLNK(mode):
                raise RepositoryAccessRejected("symlinks are not readable")
        resolved = target.resolve(strict=True)
        if self.root not in resolved.parents and resolved != self.root:
            raise RepositoryAccessRejected("resolved path escapes repository root")
        return resolved

    def read_file(self, path: str, *, expected_commit_sha: str) -> RepositoryFile:
        self._check_commit(expected_commit_sha)
        relative = _safe_path(path)
        target = self._resolve(relative)
        if not target.is_file():
            raise RepositoryAccessRejected("path is not a regular file")
        size = target.stat().st_size
        if size > _MAX_FILE_BYTES:
            raise RepositoryAccessRejected("file exceeds 256 KiB read limit")
        raw = target.read_bytes()
        try:
            content = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise RepositoryAccessRejected("file must be valid UTF-8") from exc
        if "\x00" in content:
            raise RepositoryAccessRejected("NUL bytes are forbidden")
        return RepositoryFile(path, self.commit_sha, content, len(raw), hashlib.sha256(raw).hexdigest())

    def list_tree(self, *, expected_commit_sha: str, path: str = "") -> tuple[str, ...]:
        self._check_commit(expected_commit_sha)
        if path:
            relative = _safe_path(path)
            base = self._resolve(relative)
            if not base.is_dir():
                raise RepositoryAccessRejected("tree path is not a directory")
        else:
            base = self.root
        entries: list[str] = []
        for candidate in sorted(base.rglob("*")):
            rel = candidate.relative_to(self.root).as_posix()
            if any(part.startswith(".") for part in PurePosixPath(rel).parts):
                continue
            if candidate.is_symlink():
                continue
            if candidate.is_file():
                try:
                    _safe_path(rel)
                except RepositoryAccessRejected:
                    continue
                entries.append(rel)
                if len(entries) > _MAX_TREE_ENTRIES:
                    raise RepositoryAccessRejected("tree exceeds 1000 file entry limit")
        return tuple(entries)


def validate_target_branch(
    *, target_branch: str, base_branch: str, observed_base_sha: str, expected_base_sha: str
) -> None:
    """Require a separate feature branch based on the exact reviewed base SHA."""
    if not isinstance(target_branch, str) or not _BRANCH.fullmatch(target_branch):
        raise RepositoryAccessRejected("target branch name is invalid")
    if target_branch in {"main", "master"} or not target_branch.startswith(("phase20/", "feature/")):
        raise RepositoryAccessRejected("writes require a dedicated phase20/ or feature/ branch")
    if target_branch == base_branch:
        raise RepositoryAccessRejected("target branch must differ from base branch")
    if _validate_sha(observed_base_sha, "observed_base_sha") != _validate_sha(expected_base_sha, "expected_base_sha"):
        raise RepositoryAccessRejected("base branch SHA changed; re-read before writing")


def validate_patch(
    *, path: str, content: str, current_content: str | None, expected_blob_sha: str | None
) -> ValidatedPatch:
    """Validate safe text patch, content bounds and optimistic overwrite protection."""
    relative = _safe_path(path)
    if not isinstance(content, str):
        raise RepositoryAccessRejected("patch content must be text")
    try:
        raw = content.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise RepositoryAccessRejected("patch content must be valid UTF-8") from exc
    if not raw or len(raw) > _MAX_FILE_BYTES or b"\\x00" in raw:
        raise RepositoryAccessRejected("patch is empty, contains NUL or exceeds 256 KiB")
    if re.search(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}", raw, re.I):
        raise RepositoryAccessRejected("credential-like content is forbidden")
    if relative.suffix.lower() == ".json":
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            raise RepositoryAccessRejected("JSON patch must parse successfully") from exc

    previous = None
    if current_content is None:
        if expected_blob_sha is not None:
            raise RepositoryAccessRejected("new file must not supply an existing blob SHA")
    else:
        old = current_content.encode("utf-8", errors="strict")
        previous = _blob_sha(old)
        if _validate_sha(expected_blob_sha, "expected_blob_sha") != previous:
            raise RepositoryAccessRejected("stale or missing blob SHA; re-read before overwrite")
    return ValidatedPatch(path, content, len(raw), _blob_sha(raw), previous)
