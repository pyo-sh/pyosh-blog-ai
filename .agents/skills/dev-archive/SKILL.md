---
name: dev-archive
description: Squash-merge accumulated docs branch commits into main via PR. Use when documentation has accumulated on the docs branch and should be merged to main. Activates on "/dev-archive", "archive docs", "merge docs to main", etc.
---

# Dev-archive

Merge `docs` -> `main` via squash-merge PR for traceability.

> CLI: `PYTHONPATH=$MONOREPO_ROOT/.agents/skills/dev-archive/scripts python3 -m dev_archive <cmd>`
> Prepend the PYTHONPATH above to every `python3 -m dev_archive` call below.
> `MONOREPO_ROOT`: headless → `$PIPELINE_MONOREPO_ROOT` / interactive → `source "$(git worktree list --porcelain | awk 'NR==1{print $2}')/.agents/scripts/monorepo-helpers.sh"`

## Workflow

### Step 1: Check diff

`python3 -m dev_archive check-diff --root "$ROOT_REPO"`

Returns `count` (number of commits ahead) and `commits` (oneline list). If `count` is 0, stop - nothing to archive.

### Step 2: Generate PR content

AI generates a title and body summarizing the accumulated doc changes from the commit list.

### Step 3: Ensure label

`python3 -m dev_archive ensure-label --root "$ROOT_REPO"` - creates `docs` label if not exists.

### Step 4: Create PR

`python3 -m dev_archive create-pr --root "$ROOT_REPO" --title "$TITLE" --body "$BODY"`

Returns `url` and `pr` number.

### Step 5: Squash merge

`python3 -m dev_archive squash-merge --root "$ROOT_REPO" --pr $PR`

Squash-merges the PR without deleting the `docs` branch.

### Step 6: Sync branch

`python3 -m dev_archive sync-branch --root "$ROOT_REPO"`

Resets `docs` branch to `origin/main` so future dev-log commits start fresh.
