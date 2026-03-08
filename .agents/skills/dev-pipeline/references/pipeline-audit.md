# Pipeline audit summary

## Core diagnosis

The current design mixes three separate execution contexts into one variable (`workdir`):

1. Claude session cwd for skill discovery
2. repo cwd for `gh` / repo-level git commands
3. worktree cwd for source-file edits and feature-branch git commands

That conflation is the main reason the pipeline is brittle in a monorepo + worktree setup.

## Mandatory invariants

- Claude headless session must start from monorepo root.
- Repo-level commands must use explicit repo selection.
- Feature-branch edits must happen only inside the issue worktree.
- Merge lock must be acquired and released in one helper/process.
- All transient files must be area-scoped.

## Reported bugs covered

- Bash timeout earlier than `claude` timeout
- `Unknown skill: dev-resolve` from worktree cwd
- state path mismatch
- `gh pr merge` worktree conflict
- push rejected after rebase

## Additional hidden bugs found

1. `pipeline_recovery_log` currently builds a shell variable `entry` and then calls:
   - `.recoveryLog += [$entry]`
   - but `pipeline_state_update` does not pass `--argjson entry`
   - result: jq variable resolution failure

2. `merge.lock` stale detection by PID is unsafe when acquire/release happen in separate Bash tool invocations.
   - the creating shell exits
   - a later process sees the PID as dead
   - the lock is reclaimed too early

3. `gh` helpers depend on cwd for `{owner}/{repo}` resolution.
   - this is fragile in a monorepo
   - explicit `-R owner/name` or `repos/owner/name/...` is safer

4. global log names collide across repos:
   - `issue-29-review.log`
   - `issue-29-resolve.log`
   - client/server can overwrite each other

5. message file names collide across repos:
   - `.workspace/messages/pr-129-review.md`
   - `.workspace/messages/pr-129-response.md`

6. worktree path is not area-scoped:
   - `.workspace/worktrees/issue-29`
   - client/server issue number collisions are possible

7. `monorepo_area_from_dir` is incorrect for nested paths or worktrees.
   - `basename` on `/workspace/client/src` -> `src`
   - `basename` on worktree path -> `issue-29`

8. merge step sync logic currently targets `{area}` repo dir even though the feature branch is checked out in the worktree.
   - rebase/push belongs in the worktree
   - `gh pr merge` belongs in the canonical repo dir

## Files produced

- `monorepo-helpers.fixed.sh`
- `pipeline-helpers.fixed.sh`
- `dev-pipeline.fixed.md`
- `dev-review.fixed.md`
- `dev-resolve.fixed.md`
