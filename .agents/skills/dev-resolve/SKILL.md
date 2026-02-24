---
name: dev-resolve
description: Respond to PR review comments. Read review comments left by /dev-review, fix code, and request re-review. Activates on "fix review comments", "address review", "/dev-resolve", etc.
---

# Dev-Resolve

Fix PR review comments → record → push → request re-review. Global rules in `CLAUDE.md`.

## Workflow

### 1. Read Review Comments

```bash
cd {area}  # server/ or client/
gh pr view {PR#} --comments
gh api repos/{owner}/{repo}/pulls/{PR#}/reviews
```

### 2. Classify & Plan

| Severity | Action |
|----------|--------|
| **[CRITICAL]** / **[WARNING]** | Must fix |
| **[SUGGESTION]** | Fix if valid, skip with reason on PR |

### 3. Fix Code

Work in existing worktree or branch.

- **Fix only reviewed items** — no unrelated changes
- **Commit**: `fix: address review comments (#{N})`

### 4. Record Progress (required)

**Must** run `/dev-log` to record progress before pushing. Include:
- Which review comments were addressed
- Any technical decisions made during fixes

### 5. Push & Post Response

Push changes, then post response comment on PR.

**Must use `--body-file`** (avoids markdown backtick conflicts):

```bash
git push

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

### 6. Notify User

- Summarize fixed/skipped item counts
- Advise to **run `/dev-review` in a new session**
