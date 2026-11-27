# Project Continue — Colab Permanent Recovery

## Purpose
Use `notebooks/ProjectContinue-Recovery.ipynb` from a fresh Colab runtime to recover the latest full Drive snapshot without modifying the source backup.

## Source and destination
- Source: `MyDrive/Project-Continue-Backups/recovery_full_*`
- Destination: `MyDrive/Project-Continue-Recovery-Restores/<backup>__RESTORED_<UTC timestamp>/`

The notebook selects the newest `recovery_full_*` directory containing a readable JSON manifest, copies the entire directory tree to a new destination, then verifies that every regular source file exists in the restored copy. It never overwrites an existing restore directory and never deletes the source.

## What is recovered
The entire backup tree is copied, including any repository, Git metadata, notebooks, database files, configuration artifacts, logs, and persisted Agent state/checkpoints that are actually present in the selected backup.

A running Colab process, in-memory Agent state, open sockets, or unsaved runtime files cannot be recreated from a Drive snapshot. A SQLite integrity check and file-level copy do not by themselves prove application-level correctness. Validate database integrity, record counts, repository status and application tests before reconnecting services.

## Operation
1. Open the notebook in a new Colab runtime.
2. Run Cell 1 to mount Drive and select a manifest-bearing full backup.
3. Run Cell 2 to copy the snapshot into a new timestamped recovery folder.
4. Run Cell 3 to verify the copy and inventory repositories, notebooks, databases and state/checkpoint candidates.
5. Review the inventory before starting any Agent or service.

## Backup policy
This notebook performs recovery only. It does not install an automatic scheduler or create periodic backups. Use the separately approved Final Backup Cell in the active Colab workflow when intentionally creating a new full snapshot. Do not overwrite or delete existing backups.

## Acceptance boundary
Repository delivery of this notebook is not the same as a live Drive installation or a successful fresh-Colab restore drill. Final operational acceptance requires the owner to run it against the actual Drive backup and review the printed inventory and application-level checks.
