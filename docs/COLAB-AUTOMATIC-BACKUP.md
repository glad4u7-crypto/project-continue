# Colab automatic backup controller

## Components

- `scripts/colab_persistence.py save` creates a timestamped snapshot under `MyDrive/Project-Continue-Backups/automatic/`, writes `MASTER_RECOVERY_MANIFEST.json`, and only then publishes `LATEST_SUCCESSFUL.json`.
- `notebooks/ProjectContinue-Automatic-Backup.ipynb` runs one backup immediately and starts a 15-minute loop. Use `pc_backup_now()` after important changes.
- `scripts/colab_persistence.py restore-latest` restores the latest manifest-verified snapshot into a new isolated folder. It does not replace the live checkout or database.

## Required setup in Colab

1. Open the repository checkout at `/content/project-continue`, or change `PROJECT_CONTINUE_REPO` in the notebook to the actual checkout path.
2. Save working notebooks into `MyDrive/Project-Continue-Notebooks/`, or change `PROJECT_CONTINUE_NOTEBOOK_DIR` to the actual Drive folder containing the notebooks.
3. Set `PROJECT_CONTINUE_DB` to the actual live SQLite database path if the app uses one.
4. Set `PROJECT_CONTINUE_AGENT_STATE` to the actual persisted agent state/checkpoint file if one exists. Set `PROJECT_CONTINUE_LOG` to the actual log path if useful.
5. Run the notebook cells in order and inspect the first manifest. A database or runtime file marked `not-found-or-not-configured` / `not-copied` is not backed up.

## Scheduling and guarantees

The 15-minute loop is a daemon thread inside the current Colab runtime. It works only while that runtime remains connected and executing. It cannot run after Colab disconnects, shuts down, or resets, and it is not an always-on scheduler. Free Colab does not provide a durable background scheduler. The immediate first snapshot and explicit `pc_backup_now()` calls are the reliable triggers while the runtime is active.

The backup script stores a Git bundle for history and a source archive for the working tree. It excludes credentials such as `.env`, private keys, and virtual environments. It currently supports one configured SQLite database and one configured agent-state file; additional databases/state directories require explicit extension/configuration before they can be claimed as covered. A live Agent process itself cannot be resumed from a file backup.

## Recovery

In a new Colab runtime, mount Drive, load the repository/script, and run:

```python
import os, importlib.util, sys
os.environ.setdefault("PROJECT_CONTINUE_BACKUP_ROOT", "/content/drive/MyDrive/Project-Continue-Backups")
script = "/content/project-continue/scripts/colab_persistence.py"
spec = importlib.util.spec_from_file_location("pc_persistence", script)
pc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pc
spec.loader.exec_module(pc)
restore_path = pc.restore_latest()
print(restore_path)
```

Review `RESTORE_REPORT.json` and validate the isolated repository, notebooks, database, and runtime files before any manual cutover. Never point a restore directly at the live project directory.
