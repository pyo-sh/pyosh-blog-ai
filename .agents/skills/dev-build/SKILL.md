---
name: dev-build
description: GitHub Issue-based development workflow. Issue → Worktree → Code → Push → PR creation. Auto-activates when starting coding tasks. Reviews run in a separate session via /dev-review.
---

# Dev-Build

Issue → Worktree → Code → Push → PR. Review/merge handled by separate skills.

> CLI: `python3 $MONOREPO_ROOT/.agents/skills/dev-build/scripts/<script>.py`
> `MONOREPO_ROOT`: use `source .agents/scripts/monorepo-helpers.sh` from monorepo root, or bootstrap with `source "$(git worktree list --porcelain | awk 'NR==1{print $2}')/.agents/scripts/monorepo-helpers.sh"`
> Area definitions, directory/repo mappings, worktree paths: [monorepo-layout.md](../../references/monorepo-layout.md)

## Invariants

1. Each area is an independent Git repo. Run git/gh commands in the correct area directory.
2. Worktrees live at monorepo root `.workspace/worktrees/{area}/issue-{N}`, not inside the area.
3. Branch: `{type}/issue-{N}-{desc}` - desc is kebab-case, English, max 3 words, lowercase.
4. Commit: `{type}: {description} (#{N})`
5. PR title: `{type}: {description} (#{N})`
6. PR body uses `--body-file` (not inline `--body`) to avoid shell escape conflicts.
7. `gh issue view` must always include `--json number,title,body,state,labels`. Calling it without `--json` triggers a GitHub Projects (classic) deprecation error and exits with code 1.
   Correct: `gh issue view $N -R $REPO --json number,title,body,state,labels`

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation change |
| `style` | Code formatting (no logic change) |
| `refactor` | Refactoring (no behavior change) |
| `test` | Add/modify tests |
| `chore` | Build, config changes |

## Workflow

### 0. Verify/create issue

Run `gh issue list --assignee @me` in the target area. If none exists, get user approval before creating.

### 1. Create worktree

```
python3 $MONOREPO_ROOT/.agents/skills/dev-build/scripts/worktree_setup.py \
  --area {area} --issue {N} --type {type} --desc {desc}
```

Output JSON: `{"worktreePath", "branch", "repoDir", "repo"}`. `cd` into `worktreePath`.

### 2. Code

Follow `{area}/CLAUDE.md`. Record technical decisions via `/dev-log`.

### 2.5. Check definition of done (feat issues only)

After implementation, mark completed DoD items in the issue body. Only check fully implemented items. Leave partial or future items unchecked.

### 3. Push and create PR

```
python3 $MONOREPO_ROOT/.agents/skills/dev-build/scripts/pr_helpers.py push \
  --worktree {worktreePath} --branch {branch}
```

Read `{area}/.github/PULL_REQUEST_TEMPLATE.md` for the PR body structure. Write body to `.workspace/messages/pr-{N}-body.md`, then:

```
python3 $MONOREPO_ROOT/.agents/skills/dev-build/scripts/pr_helpers.py create \
  --worktree {worktreePath} --repo {repo} \
  --title "{type}: description (#{N})" --body-file .workspace/messages/pr-{N}-body.md
```

Output JSON: `{"number", "url"}`. Clean up the body file after.

### 4. Next step

If called from `/dev-pipeline`, return control to the caller. Otherwise, instruct user to run `/dev-review` in a new session.

### 5. Cleanup

```
python3 $MONOREPO_ROOT/.agents/skills/dev-build/scripts/worktree_cleanup.py \
  --repo-dir {repoDir} --worktree {worktreePath} --branch {branch}
```
