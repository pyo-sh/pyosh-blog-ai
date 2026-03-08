---
name: dev-resolve
description: Respond to PR review comments. Reads review feedback, applies fixes in the issue worktree, pushes, posts a review-response comment, and requests re-review. Works correctly when the Claude session starts from monorepo root.
---

# Dev-Resolve

Fix reviewed items, record the work, push, and request re-review.

## Runtime contract when invoked by dev-pipeline

The parent pipeline may launch this skill from monorepo root. Use these environment variables if present:

- `PIPELINE_AREA`
- `PIPELINE_REPO`
- `PIPELINE_REPO_DIR`
- `PIPELINE_WORKTREE_DIR`
- `PIPELINE_PR`
- `PIPELINE_ISSUE`
- `PIPELINE_MONOREPO_ROOT`

Do not assume the current cwd is the repo checkout or the worktree.

Recommended variables:

```bash
REPO="${PIPELINE_REPO:?PIPELINE_REPO is required}"
REPO_DIR="${PIPELINE_REPO_DIR:?PIPELINE_REPO_DIR is required}"
WORKTREE_DIR="${PIPELINE_WORKTREE_DIR:?PIPELINE_WORKTREE_DIR is required}"
PR="${PIPELINE_PR:?PIPELINE_PR is required}"
ISSUE="${PIPELINE_ISSUE:?PIPELINE_ISSUE is required}"
```

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

### 4. Record progress

Run `/dev-log` and include which comments were fixed or skipped.

### 5. Push and post response

Push from the worktree:

```bash
git push
```

Use an area-scoped response file to avoid collisions:

```bash
MSG_FILE="${PIPELINE_MONOREPO_ROOT:-/workspace}/.workspace/messages/${PIPELINE_AREA:-manual}-pr-${PR}-response.md"
mkdir -p "$(dirname "$MSG_FILE")"
cat > "$MSG_FILE" <<'EOF_RESPONSE'
{body}
EOF_RESPONSE

gh pr comment "$PR" -R "$REPO" --body-file "$MSG_FILE"
rm -f "$MSG_FILE"
```

### 6. Notify user

Summarize fixed and skipped counts. Advise re-review.
