#!/usr/bin/env python3
"""Colab-friendly, versioned Project Continue backup and non-destructive recovery.

Commands:
  python scripts/colab_persistence.py save
  python scripts/colab_persistence.py restore-latest

Required: Google Drive mounted at /content/drive.
Optional environment:
  PROJECT_CONTINUE_REPO=/content/project-continue
  PROJECT_CONTINUE_BACKUP_ROOT=/content/drive/MyDrive/Project-Continue-Backups
  PROJECT_CONTINUE_NOTEBOOK_DIR=/content/drive/MyDrive/Project-Continue-Notebooks
  PROJECT_CONTINUE_DB=/absolute/path/to/live.sqlite3
  PROJECT_CONTINUE_AGENT_STATE=/absolute/path/to/state.json
  PROJECT_CONTINUE_LOG=/absolute/path/to/streamlit.log

Restore is intentionally additive and never overwrites an existing repository,
database, state file, log, or notebook.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BACKUP_ROOT = Path("/content/drive/MyDrive/Project-Continue-Backups")
DEFAULT_NOTEBOOK_DIR = Path("/content/drive/MyDrive/Project-Continue-Notebooks")
LEGACY_BACKUP = DEFAULT_BACKUP_ROOT / "recovery_full_20261127_110845"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def env_path(name: str, default: Path | None = None) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else (default.resolve() if default else None)


def run_git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True, capture_output=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def sqlite_check(path: Path) -> str:
    uri = "file:" + str(path.resolve()).replace("?", "%3f") + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=30) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "NO_RESULT"


def copy_if_missing(source: Path, destination: Path) -> bool:
    if not source.is_file() or destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def discover_notebooks(notebook_dir: Path) -> list[dict]:
    records = []
    for path in sorted(notebook_dir.rglob("*.ipynb")):
        if not path.is_file():
            continue
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            valid = isinstance(notebook, dict) and isinstance(notebook.get("cells", []), list)
            cells = len(notebook.get("cells", [])) if valid else None
        except Exception:
            valid, cells = False, None
        records.append({
            "relative_path": str(path.relative_to(notebook_dir)),
            "size": path.stat().st_size,
            "sha256": sha256(path),
            "json_valid": valid,
            "cells": cells,
        })
    return records


def import_legacy_notebooks(notebook_dir: Path) -> list[str]:
    """Seed the durable notebook folder from the verified 2026-11-27 backup, without overwrite."""
    legacy = LEGACY_BACKUP / "notebooks"
    copied = []
    if legacy.is_dir():
        for source in sorted(legacy.glob("*.ipynb")):
            target = notebook_dir / source.name
            if copy_if_missing(source, target):
                copied.append(source.name)
    return copied


def make_sqlite_snapshot(source: Path, destination: Path) -> dict:
    if not source.is_file():
        raise FileNotFoundError(f"Configured SQLite database not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    src_uri = "file:" + str(source.resolve()).replace("?", "%3f") + "?mode=ro"
    try:
        with sqlite3.connect(src_uri, uri=True, timeout=60) as src:
            with sqlite3.connect(destination, timeout=60) as dst:
                src.backup(dst)
        integrity = sqlite_check(destination)
        if integrity != "ok":
            raise RuntimeError(f"SQLite backup integrity failed: {integrity}")
        return {
            "source_path": str(source),
            "backup_path": str(destination),
            "size": destination.stat().st_size,
            "sha256": sha256(destination),
            "integrity_check": integrity,
        }
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def save() -> Path:
    drive = Path("/content/drive/MyDrive")
    if not drive.is_dir():
        raise RuntimeError("Google Drive is not mounted at /content/drive.")
    repo = env_path("PROJECT_CONTINUE_REPO", Path("/content/project-continue"))
    backup_root = env_path("PROJECT_CONTINUE_BACKUP_ROOT", DEFAULT_BACKUP_ROOT)
    notebook_dir = env_path("PROJECT_CONTINUE_NOTEBOOK_DIR", DEFAULT_NOTEBOOK_DIR)
    assert repo and backup_root and notebook_dir
    if not repo.is_dir() or not (repo / ".git").exists():
        raise RuntimeError(f"Git repository not found at {repo}; set PROJECT_CONTINUE_REPO.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = backup_root / "automatic" / stamp
    run_dir.mkdir(parents=True, exist_ok=False)

    # Preserve older verified notebooks into the durable working folder, never replacing files.
    imported = import_legacy_notebooks(notebook_dir)
    notebook_dir.mkdir(parents=True, exist_ok=True)
    notebook_records = discover_notebooks(notebook_dir)
    if not notebook_records:
        raise RuntimeError(
            f"No .ipynb files found in {notebook_dir}. Save/open notebooks in this Drive folder first."
        )
    if not all(item["json_valid"] for item in notebook_records):
        raise RuntimeError("At least one notebook is invalid JSON; backup not marked successful.")

    repo_archive = run_dir / "repository-source.tar.gz"
    excluded = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    with tarfile.open(repo_archive, "w:gz") as archive:
        for item in sorted(repo.iterdir()):
            if item.name in excluded or item.name == ".env":
                continue
            archive.add(item, arcname=item.name, recursive=True)

    # Preserve Git history/refs separately. The bundle is a portable Git recovery artifact.
    bundle = run_dir / "repository.git.bundle"
    bundle_result = subprocess.run(
        ["git", "-C", str(repo), "bundle", "create", str(bundle), "--all"],
        text=True, capture_output=True, check=False,
    )
    if bundle_result.returncode != 0:
        bundle.unlink(missing_ok=True)
        raise RuntimeError("Git bundle creation failed; inspect repository refs and retry.")

    notebook_backup = run_dir / "notebooks"
    notebook_backup.mkdir()
    notebook_copy_records = []
    for item in notebook_records:
        source = notebook_dir / item["relative_path"]
        target = notebook_backup / item["relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha256(source) != sha256(target):
            raise RuntimeError(f"Notebook copy hash mismatch: {item['relative_path']}")
        notebook_copy_records.append(item)

    db_records = []
    db_source = env_path("PROJECT_CONTINUE_DB")
    if db_source:
        db_records.append(make_sqlite_snapshot(db_source, run_dir / "database" / db_source.name))
    else:
        # The previously verified database backups remain preserved; don't guess which DB is live.
        db_records.append({
            "status": "not-copied",
            "reason": "PROJECT_CONTINUE_DB is not configured; existing verified database backup retained.",
        })

    optional_files = {}
    for label, variable in (
        ("agent_state", "PROJECT_CONTINUE_AGENT_STATE"),
        ("streamlit_log", "PROJECT_CONTINUE_LOG"),
    ):
        source = env_path(variable)
        if source and source.is_file():
            target = run_dir / "runtime" / label / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            optional_files[label] = {
                "path": str(target), "size": target.stat().st_size, "sha256": sha256(target)
            }
        else:
            optional_files[label] = {"status": "not-found-or-not-configured"}

    manifest = {
        "project": "Project Continue",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "backup_directory": str(run_dir),
        "repository": {
            "source": str(repo),
            "branch": run_git(repo, "branch", "--show-current"),
            "commit": run_git(repo, "rev-parse", "HEAD"),
            "working_tree_status": run_git(repo, "status", "--short"),
            "source_archive": {
                "path": str(repo_archive), "size": repo_archive.stat().st_size,
                "sha256": sha256(repo_archive),
            },
            "git_bundle": {
                "path": str(bundle), "size": bundle.stat().st_size, "sha256": sha256(bundle),
            },
        },
        "notebooks": {
            "source_directory": str(notebook_dir),
            "legacy_notebooks_imported_this_run": imported,
            "count": len(notebook_copy_records),
            "all_json_valid": True,
            "files": notebook_copy_records,
        },
        "database": db_records,
        "runtime_files": optional_files,
        "safety": {
            "no_source_files_deleted": True,
            "no_existing_files_overwritten": True,
            "live_database_not_modified": True,
            "restore_not_performed": True,
        },
    }
    manifest_path = run_dir / "MASTER_RECOVERY_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    # Verify the manifest can be read and all declared backup hashes still match.
    json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in notebook_copy_records:
        copied = notebook_backup / record["relative_path"]
        if sha256(copied) != record["sha256"]:
            raise RuntimeError(f"Final notebook verification failed: {record['relative_path']}")

    latest_tmp = backup_root / "LATEST_SUCCESSFUL.tmp"
    latest = backup_root / "LATEST_SUCCESSFUL.json"
    latest_tmp.write_text(json.dumps({
        "backup_directory": str(run_dir),
        "manifest": str(manifest_path),
        "created_at_utc": manifest["created_at_utc"],
        "manifest_sha256": sha256(manifest_path),
    }, indent=2), encoding="utf-8")
    # Publish pointer only after all checks have passed.
    latest_tmp.replace(latest)
    return manifest_path


def restore_latest() -> Path:
    backup_root = env_path("PROJECT_CONTINUE_BACKUP_ROOT", DEFAULT_BACKUP_ROOT)
    assert backup_root
    pointer = backup_root / "LATEST_SUCCESSFUL.json"
    if not pointer.is_file():
        raise FileNotFoundError("No LATEST_SUCCESSFUL.json exists; run the save command first.")
    latest = json.loads(pointer.read_text(encoding="utf-8"))
    manifest_path = Path(latest["manifest"])
    if not manifest_path.is_file() or sha256(manifest_path) != latest["manifest_sha256"]:
        raise RuntimeError("Latest manifest is missing or its hash does not match.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    backup_dir = Path(manifest["backup_directory"])
    restore_root = backup_root / "RESTORES" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    restore_root.mkdir(parents=True, exist_ok=False)

    repo_record = manifest["repository"]
    archive = Path(repo_record["source_archive"]["path"])
    if sha256(archive) != repo_record["source_archive"]["sha256"]:
        raise RuntimeError("Repository archive hash mismatch.")
    repo_target = restore_root / "repository"
    repo_target.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        root = repo_target.resolve()
        for member in tar.getmembers():
            target = (repo_target / member.name).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError("Unsafe archive path rejected.")
        tar.extractall(repo_target)

    bundle_info = repo_record["git_bundle"]
    bundle = Path(bundle_info["path"])
    if sha256(bundle) != bundle_info["sha256"]:
        raise RuntimeError("Git bundle hash mismatch.")
    # Bundle is retained beside the source archive; initialize a separate Git clone only if refs exist.
    bundle_target = restore_root / "repository.git.bundle"
    shutil.copy2(bundle, bundle_target)

    notebooks_target = restore_root / "notebooks"
    notebooks_target.mkdir()
    for item in manifest["notebooks"]["files"]:
        source = backup_dir / "notebooks" / item["relative_path"]
        target = notebooks_target / item["relative_path"]
        if not source.is_file() or sha256(source) != item["sha256"]:
            raise RuntimeError(f"Notebook restore source failed verification: {item['relative_path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    # Database restores are copied only into the isolated restore directory, never to the live path.
    restored_dbs = []
    for item in manifest.get("database", []):
        if item.get("backup_path"):
            source = Path(item["backup_path"])
            if sha256(source) != item["sha256"] or sqlite_check(source) != "ok":
                raise RuntimeError("Database backup failed hash/integrity verification.")
            target = restore_root / "database" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored_dbs.append(str(target))

    (restore_root / "RESTORE_REPORT.json").write_text(json.dumps({
        "status": "isolated_restore_copy_created",
        "source_manifest": str(manifest_path),
        "repository_copy": str(repo_target),
        "git_bundle_copy": str(bundle_target),
        "notebooks_copy": str(notebooks_target),
        "database_copies": restored_dbs,
        "live_repository_or_database_modified": False,
        "note": "This is an isolated recovery copy; operator validation and any cutover are separate.",
    }, indent=2), encoding="utf-8")
    return restore_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("save", "restore-latest"))
    args = parser.parse_args()
    result = save() if args.command == "save" else restore_latest()
    print(json.dumps({"status": "success", "result": str(result)}, indent=2))


if __name__ == "__main__":
    main()
