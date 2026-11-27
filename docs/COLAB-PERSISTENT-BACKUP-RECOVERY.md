# Colab Persistent Backup & Recovery

This utility adds versioned, hash-verified backups for a Colab workflow. It is deliberately
separate from the application's production backup runner: Colab is not an always-on scheduler.

## Durable locations

- Backup history: `/content/drive/MyDrive/Project-Continue-Backups/automatic/<UTC timestamp>/`
- Latest successful pointer: `Project-Continue-Backups/LATEST_SUCCESSFUL.json`
- Durable notebooks: `/content/drive/MyDrive/Project-Continue-Notebooks/`

The first save imports the ten previously verified notebooks from
`recovery_full_20261127_110845/notebooks/` into the durable notebook folder if their
filenames do not already exist. It never overwrites an existing notebook.

## One-time setup in Colab

1. Mount Google Drive at `/content/drive`.
2. Ensure the repository is checked out at `/content/project-continue`.
3. Use this branch until its pull request is merged; afterwards use `main`:

```bash
cd /content/project-continue
git fetch origin
git checkout feature/colab-persistent-recovery-20261127
git pull --ff-only origin feature/colab-persistent-recovery-20261127
```

4. Save/open all Project Continue notebooks from the Drive folder
   `Project-Continue-Notebooks`. A notebook that has never been saved to Drive cannot be
   recovered after its runtime disappears.

## The one final save cell

Run this at the end of a work session:

```python
from pathlib import Path
import subprocess, sys

repo = Path("/content/project-continue")
script = repo / "scripts" / "colab_persistence.py"
if not Path("/content/drive/MyDrive").is_dir():
    raise RuntimeError("Mount Google Drive at /content/drive first.")
if not script.is_file():
    raise FileNotFoundError(script)

subprocess.run([sys.executable, str(script), "save"], cwd=repo, check=True)
```

The save command creates a new timestamped snapshot; it does not delete older snapshots.
It includes a repository source archive, a Git bundle containing refs/history, every valid
Notebook JSON file under the durable notebook folder, and the database if
`PROJECT_CONTINUE_DB` points to it or the default `.data/project_continue.sqlite3` exists.
It also copies the known Colab Agent State path `/content/.project_continue_agent_state.json`
and a Streamlit log when `PROJECT_CONTINUE_LOG` is configured and the file exists.

If the live database is elsewhere, set its exact path before saving:

```python
import os
os.environ["PROJECT_CONTINUE_DB"] = "/absolute/path/to/project_continue.sqlite3"
```

For a non-default Agent State or Streamlit log, set
`PROJECT_CONTINUE_AGENT_STATE` or `PROJECT_CONTINUE_LOG` to the exact file path.
Never put tokens, passwords, signing keys, or other secrets in these variables or manifests.

The latest-successful pointer is updated only after the archive, bundle, notebooks and manifest
have been written and verified. A failed run leaves prior successful snapshots intact.

## New runtime / recovery

1. Mount Google Drive.
2. Clone or open the repository at the required release.
3. Run this in a new, empty recovery environment:

```bash
cd /content/project-continue
python scripts/colab_persistence.py restore-latest
```

This creates a timestamped folder under
`Project-Continue-Backups/RESTORES/` containing a repository source copy, Git bundle,
notebook copies, database copies and a restore report. It does **not** overwrite the active
repository, live database, current notebook files, Agent State or logs. Validate the isolated
copies before any separately approved cutover.

## Important limits

- Colab runtimes can disconnect at any time. This is a manual end-of-session save, not a
  background scheduler or continuous autosave.
- Save the notebook itself to Drive before running the final cell; unsaved browser edits and
  unsaved notebook outputs are not guaranteed to be captured.
- Future notebooks are discovered when saved under `Project-Continue-Notebooks`; notebooks
  saved elsewhere are not included.
- A Streamlit process may write logs to an unknown path. Configure
  `PROJECT_CONTINUE_LOG` if a specific log file needs to be preserved.
- GitHub and Google Drive are separate failure domains only if the user retains independent
  access and permissions. Keep a second private copy of critical backups where practical.
- No backup can guarantee zero data loss if data has not yet been saved, Drive is unavailable,
  or the source itself is corrupted. Verify the printed success result and keep previous
  timestamped snapshots.
- This tool does not restart the Agent, start Streamlit, push secrets, or perform production
  deployment.
