---
name: dev-workflow
description: GitHub Issue-based development workflow. Issue → Worktree → Code → Push → PR creation. Auto-activates when starting coding tasks. Reviews run in a separate session via /dev-review.
---

# Dev-Workflow

Issue → Worktree → Code → Push → PR. Review and merge handled by separate skills. Global rules (branch naming, commit format, multi-agent) in `CLAUDE.md`.

## Prerequisite: Git Remote

Monorepo — `server/` and `client/` are **independent Git repos**. Run all git/gh commands **inside the target area directory** (never from root).

| Area | GitHub Repo |
|------|-------------|
| `server/` | `pyo-sh/pyosh-blog-be` |
| `client/` | `pyo-sh/pyosh-blog-fe` |

## Workflow

### 0. Verify/Create Issue
Run `gh issue list --assignee @me` in the target area. If none exists, get user approval before creating.

### 1. Create Worktree
```bash
cd {area}
git worktree add -b {type}/issue-{N}-{desc} .claude/worktrees/issue-{N} main
cd .claude/worktrees/issue-{N}
```
→ Branch rules: [branch-naming.md](references/branch-naming.md)

### 2. Code
- Follow `{area}/CLAUDE.md` rules
- On technical investigation/decision → record via `/dev-log`

### 3. Record Progress (required)
**Must** run `/dev-log` to record progress before pushing.

### 4. Push & Create PR
```bash
git push -u origin {type}/issue-{N}-{desc}
```
PR **must use `--body-file`** (avoids shell escape bugs with markdown). → Template: [pr-template.md](references/pr-template.md)

### 5. Request Review
After PR creation, instruct user to **run `/dev-review` in a new session**. Do not review in this session.

> Follow-up: `/dev-review` → fix via `/dev-review-answer` → re-review → user approval & merge

### 6. Cleanup
```bash
cd {area}
git worktree remove .claude/worktrees/issue-{N}
git branch -d {type}/issue-{N}-{desc}
```

## References
- [Branch & commit rules](references/branch-naming.md)
- [PR template](references/pr-template.md)
