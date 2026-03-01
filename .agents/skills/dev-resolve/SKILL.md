---
name: dev-resolve
description: Respond to PR review comments. Read review comments left by /dev-review, fix code, and request re-review. Activates on "fix review comments", "address review", "/dev-resolve", etc.
---

# Dev-Resolve

Fix PR review comments → record → push → request re-review. Git remote and branch rules in `CLAUDE.md`.

## Workflow

### 1. Read Review Comments

```bash
cd {area}
gh pr view {PR#} --comments
gh api repos/{owner}/{repo}/pulls/{PR#}/reviews
```

### 2. Classify & Plan

| Severity | Action |
|----------|--------|
| `[CRITICAL]` / `[WARNING]` | Must fix |
| `[SUGGESTION]` | Fix if valid, skip with reason |

### 3. Fix Code

**Must work inside the worktree** — not the main branch. Worktrees live at the **monorepo root** `.workspace/`:

```bash
cd .workspace/worktrees/issue-{N}
```

> When launched by `/dev-pipeline`, the pane already opens in the worktree directory. Verify with `pwd`.

- **Fix only reviewed items** — no unrelated changes
- Commit: `fix: address review comments (#{N})`

### 3.5. Update Test Plan Checkboxes

After fixing code, update verified `- [ ]` items in the PR body to `- [x]`:

```bash
BODY=$(gh pr view {PR#} --json body --jq '.body')
# Replace verified items (one per line as needed)
BODY=$(echo "$BODY" | sed 's/- \[ \] Verified item text/- [x] Verified item text/')
gh pr edit {PR#} --body "$BODY"
```

Only check items that can be verified from the current code state. Leave runtime-dependent items as `- [ ]`.

### 4. Record Progress (required)

**Must** run `/dev-log` before pushing. Include which comments were addressed and any technical decisions.

### 5. Push & Post Response

**Must use `--body-file`**:

```bash
git push

mkdir -p .workspace/messages
cat > .workspace/messages/pr-{PR#}-response.md <<'EOF'
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
EOF

gh pr comment {PR#} --body-file .workspace/messages/pr-{PR#}-response.md
rm .workspace/messages/pr-{PR#}-response.md
```

### 6. Notify User

Summarize fixed/skipped counts. Advise to **run `/dev-review` in a new session** for re-review.
