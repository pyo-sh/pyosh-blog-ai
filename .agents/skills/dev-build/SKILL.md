---
name: dev-build
description: GitHub Issue-based development workflow. Issue → Worktree → Code → Push → PR creation. Auto-activates when starting coding tasks. Reviews run in a separate session via /dev-review.
---

# Dev-Build

Issue → Worktree → Code → Push → PR. Review/merge handled by separate skills. Git remote and branch rules in `CLAUDE.md`.

## Workflow

### 0. Verify/Create Issue
Run `gh issue list --assignee @me` in the target area. If none exists, get user approval before creating.

### 1. Create Worktree
```bash
cd {area}
git worktree add -b {type}/issue-{N}-{desc} .workspace/worktrees/issue-{N} main
cd .workspace/worktrees/issue-{N}
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
PR **must use `--body-file`** (avoids shell escape issues). → Template: [pr-template.md](references/pr-template.md)

### 5. Next Step
Instruct user to run `/dev-review` in a new session or `/dev-pipeline` for automated orchestration. Do not review in this session.

### 6. Cleanup
```bash
cd {area}
git worktree remove .workspace/worktrees/issue-{N}
git branch -d {type}/issue-{N}-{desc}
```

## References
- [Branch & commit rules](references/branch-naming.md)
- [PR template](references/pr-template.md)
