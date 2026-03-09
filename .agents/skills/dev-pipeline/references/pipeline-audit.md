# Pipeline audit summary

## Core diagnosis (resolved)

The original design mixed three execution contexts into one variable (`workdir`). This was resolved by separating:

1. `skillCwd` - Claude session cwd (monorepo root) for skill discovery
2. `repoDir` - canonical repo dir for `gh` / repo-level git commands
3. `worktreeDir` - issue worktree for source-file edits and feature-branch git

## Mandatory invariants

- Claude headless session must start from monorepo root.
- Repo-level commands must use explicit repo selection (`-R owner/name`).
- Feature-branch edits must happen only inside the issue worktree.
- Merge lock must be acquired and released in one helper/process.
- All transient files must be area-scoped.

## Resolved issues

All items from the original audit have been fixed:

1. `pipeline_recovery_log` jq variable - fixed with `--argjson entry`
2. Merge lock stale detection - changed from PID-based to TTL-based
3. `gh` helpers cwd dependency - all use explicit `-R owner/name`
4. Log name collisions - area-scoped paths
5. Message file name collisions - area-scoped paths
6. Worktree path not area-scoped - canonical path `.workspace/worktrees/{area}/issue-{N}`
7. `monorepo_area_from_dir` - replaced with explicit area parameter
8. Merge step sync logic - rebase/push in worktree, `gh pr merge` in repo dir
