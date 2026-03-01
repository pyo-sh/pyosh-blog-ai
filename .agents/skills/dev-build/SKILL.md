---
name: dev-build
description: GitHub Issue-based development workflow. Issue → Worktree → Code → Push → PR creation. Auto-activates when starting coding tasks. Reviews run in a separate session via /dev-review.
---

# Dev-Build

Issue → Worktree → Code → Push → PR. Review/merge handled by separate skills.

## Workflow

### 0. Verify/create issue

Run `gh issue list --assignee @me` in the target area. If none exists, get user approval before creating.

### 1. Create worktree

**`cd {area}` first** — each area is an independent Git repo. Worktrees live at monorepo root `.workspace/`, not inside the area.

```bash
cd {area}
git worktree add -b {type}/issue-{N}-{desc} ../.workspace/worktrees/issue-{N} main
cd ../.workspace/worktrees/issue-{N}
```

→ [branch-naming.md](references/branch-naming.md)

### 2. Code

Follow `{area}/CLAUDE.md`. Record technical decisions via `/dev-log`.

### 2.5. Check Definition of Done (feat issues only)

After implementation, mark completed DoD items in the Issue body:

```bash
BODY=$(gh issue view {N} --json body -q '.body')
BODY=$(echo "$BODY" | sed 's/- \[ \] Completed item/- [x] Completed item/')
gh issue edit {N} --body "$BODY"
```

Only check fully implemented items. Leave partial or future items unchecked.

### 3. Record progress (required)

Run `/dev-log` before pushing.

### 4. Push & create PR

```bash
git push -u origin {type}/issue-{N}-{desc}
```

Write body to `.workspace/messages/pr-{N}-body.md`, then:

```bash
gh pr create --title "{type}: description (#{N})" --body-file .workspace/messages/pr-{N}-body.md
rm .workspace/messages/pr-{N}-body.md
```

→ [pr-template.md](references/pr-template.md)

### 5. Next step

Instruct user to run `/dev-review` in a new session or `/dev-pipeline` for automated orchestration.

### 6. Cleanup

```bash
cd {area}
git worktree remove ../.workspace/worktrees/issue-{N}
git branch -d {type}/issue-{N}-{desc}
```
