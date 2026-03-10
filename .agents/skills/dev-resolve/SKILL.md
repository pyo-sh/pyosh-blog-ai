---
name: dev-resolve
description: Respond to PR review comments. Reads review feedback, applies fixes in the issue worktree, pushes, posts a review-response comment, and requests re-review. Works correctly when the Claude session starts from monorepo root.
---

# Dev-Resolve

Fix reviewed items, record the work, push, and request re-review.

## Workflow

### 1. Read review

Use the repo explicitly:

```bash
gh pr view "$PR" -R "$REPO" --json number,title,state,body,reviews
gh api "repos/${REPO}/pulls/${PR}/reviews"
```

### 2. Classify and plan

- `[CRITICAL]` / `[WARNING]` -> fix
- `[SUGGESTION]` -> fix if valid, otherwise skip with a reason

### 3. Fix code in the worktree

All source edits and feature-branch git commands must run inside the issue worktree:

```bash
cd "$WORKTREE_DIR"
```

Never edit files in the canonical repo dir.

Commit example:

```bash
git commit -m "fix: address review comments (#${ISSUE})"
```

### 4. Push and post response

Push from the worktree:

```bash
git push
```

Use a repo-scoped response file to avoid collisions:

```bash
MSG_FILE="/workspace/.workspace/messages/${REPO##*/}-pr-${PR}-response.md"
mkdir -p "$(dirname "$MSG_FILE")"
cat > "$MSG_FILE" <<'EOF_RESPONSE'
{body}
EOF_RESPONSE

gh pr comment "$PR" -R "$REPO" --body-file "$MSG_FILE"
rm -f "$MSG_FILE"
```

### 5. Notify user

Summarize fixed and skipped counts. Advise re-review.
