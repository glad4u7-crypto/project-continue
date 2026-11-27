"""Bounded, metadata-only notebook discovery for Project Continue.

The optional discovery directory must be explicitly configured by the Colab operator.
No file contents, credentials, hidden files, or directory names are uploaded to GitHub.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

MAX_DEPTH = 3
MAX_ENTRIES = 200
ALLOWED_SUFFIXES = {".ipynb", ".py", ".md"}


def _safe_root(path: Path) -> Path | None:
    try:
        if path.is_symlink():
            return None
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            return None
        return resolved
    except (OSError, RuntimeError):
        return None


def _scan_root(root: Path) -> dict:
    counts = {".ipynb": 0, ".py": 0, ".md": 0}
    total_bytes = 0
    visited = 0
    truncated = False
    stack = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if visited >= MAX_ENTRIES:
                        truncated = True
                        stack.clear()
                        break
                    visited += 1
                    if entry.name.startswith(".") or entry.is_symlink():
                        continue
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if depth < MAX_DEPTH:
                                stack.append((Path(entry.path), depth + 1))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        suffix = Path(entry.name).suffix.lower()
                        if suffix not in ALLOWED_SUFFIXES:
                            continue
                        info = entry.stat(follow_symlinks=False)
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        counts[suffix] += 1
                        total_bytes += info.st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return {
        "notebooks": counts[".ipynb"],
        "python_files": counts[".py"],
        "markdown_files": counts[".md"],
        "total_bytes": total_bytes,
        "entries_examined": visited,
        "truncated": truncated,
    }


def discover_project_files(repo_root: Path | None = None,
                           configured_root: str | None = None) -> tuple[bool, str]:
    """Return aggregate counts only; never return file names or file contents."""
    repo = _safe_root(repo_root or Path(__file__).resolve().parents[1])
    if repo is None:
        return False, "Discovery failed: repository root is unavailable or unsafe."

    roots = [("repository", repo)]
    configured = (configured_root if configured_root is not None
                  else os.environ.get("PROJECT_CONTINUE_DISCOVERY_DIR", "")).strip()
    if configured:
        candidate = _safe_root(Path(configured).expanduser())
        if candidate is None:
            return False, "Discovery failed: configured folder is unavailable or unsafe."
        if candidate != repo:
            roots.append(("configured_folder", candidate))

    reports = []
    for label, root in roots:
        result = _scan_root(root)
        reports.append(
            f"{label}: notebooks={result['notebooks']}, "
            f"python={result['python_files']}, markdown={result['markdown_files']}, "
            f"bytes={result['total_bytes']}, examined={result['entries_examined']}, "
            f"truncated={str(result['truncated']).lower()}"
        )
    return True, (
        "Metadata-only discovery completed. No paths or file contents were exported.\n"
        + "\n".join(reports)
        + "\nLimits: depth=3, entries=200 per root; hidden files and symlinks skipped; "
          "extensions limited to .ipynb, .py, .md."
    )
