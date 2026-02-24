---
name: dev-review-answer
description: Respond to PR review comments. Read review comments left by /dev-review, fix code, and request re-review. Activates on "fix review comments", "address review", "/dev-review-answer", etc.
---

# Dev-Review-Answer

## Workflow

### 1. Read Review Comments

```bash
cd {area}  # server/ or client/
gh pr view {PR#} --comments
gh api repos/{owner}/{repo}/pulls/{PR#}/reviews
```

### 2. Classify Comments

| Severity | Action |
|----------|--------|
| **[CRITICAL]** / **[WARNING]** | Must fix |
| **[SUGGESTION]** | Fix if valid, skip otherwise (reason required) |

### 3. Fix Code

Work in existing worktree or branch.

- **Fix only what the review comments address** — no unrelated refactoring/improvements
- **Commit**: `fix: address review comments (#{N})`
- **Push after fixing**

### 4. Post Response Comment on PR

**Must use `--body-file`** (avoids markdown backtick conflicts):

```bash
cat > /tmp/pr-{PR#}-response.md <<'RESPEOF'
## Review Response

### Fixed
| # | Severity | File:Line | Action |
|---|----------|-----------|--------|
| 1 | [CRITICAL] | `file:line` | Fixed — description |

### Skipped (Suggestion)
| # | File:Line | Reason |
|---|-----------|--------|
| 1 | `file:line` | Skip reason |

> Requesting re-review.
RESPEOF

gh pr comment {PR#} --body-file /tmp/pr-{PR#}-response.md
```

### 5. Notify User

- Summarize fixed/skipped item counts
- Advise to **run `/dev-review` in a new session**
