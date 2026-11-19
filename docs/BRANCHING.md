# Branching Policy

## Authoritative branch

`main` is the canonical, authoritative branch for Project Continue. It is the source used for the stable project state and for Colab clone/sync operations unless a checkpoint explicitly specifies another branch.

## Working branches

- Use short-lived branches for isolated changes.
- Use descriptive prefixes such as `feature/`, `fix/`, and `maintenance/`.
- Do not force-push, reset, or delete a branch as a routine synchronization method.
- Do not merge a diverged branch blindly. Compare its commits and files with `main` first.

## Integration

1. Fetch and compare the source branch with `main`.
2. Review every changed file, including configuration and dependency differences.
3. Port only changes that are compatible with the current `main` baseline.
4. Open a pull request targeting `main`.
5. Run CI and review the diff before merging.
6. After merge, sync the local/Colab clone with a safe fast-forward.

## Checkpoint evidence

A branch or commit existing is not proof that a checkpoint passed. Record the exact branch, commit SHA, commands/tests, outputs, and remaining limitations in the checkpoint evidence.
