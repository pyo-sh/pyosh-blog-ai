---
name: dev-resolve
description: Respond to PR review comments. Read review comments left by /dev-review, fix code, and request re-review. Activates on "fix review comments", "address review", "/dev-resolve", etc.
---

# Dev-Resolve

Fix PR review comments → record → push → request re-review.

## Workflow

### 1. Read review

```bash
cd {area}
gh pr view {PR#} --comments
gh api repos/{owner}/{repo}/pulls/{PR#}/reviews
```

### 2. Classify & plan

| Severity | Action |
|----------|--------|
| `[CRITICAL]` / `[WARNING]` | Must fix |
| `[SUGGESTION]` | Fix if valid, skip with reason |

### 3. Fix code

Work inside the worktree — not the main branch:

```bash
cd .workspace/worktrees/issue-{N}
```

Fix only reviewed items. Commit: `fix: address review comments (#{N})`.

### 4. Record progress (required)

Run `/dev-log`. Include which comments were addressed and any technical decisions.

### 5. Push & post response

```bash
git push
```

Post response comment. → [response-template.md](references/response-template.md)

### 6. Notify user

Summarize fixed/skipped counts. Advise to run `/dev-review` in a new session for re-review.
