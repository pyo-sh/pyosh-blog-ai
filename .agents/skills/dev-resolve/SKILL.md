---
name: dev-resolve
description: Respond to PR review comments. Reads review feedback, applies fixes in the issue worktree, pushes, posts a review-response comment, and requests re-review. Works correctly when the Claude session starts from monorepo root.
---

# Dev-Resolve

Read PR review -> fix code -> push -> post response.

> Scripts: `$MONOREPO_ROOT/.agents/skills/dev-resolve/scripts/`
> `MONOREPO_ROOT`: use `source .agents/scripts/monorepo-helpers.sh` from monorepo root, or bootstrap with `source "$(git worktree list --porcelain | awk 'NR==1{print $2}')/.agents/scripts/monorepo-helpers.sh"`

## Invariants

1. All edits in issue worktree only, never canonical repo.
2. `[CRITICAL]`/`[WARNING]`: must fix.
3. `[SUGGESTION]`: fix if valid, skip with reason.
4. Commit message: `fix: address review comments (#{ISSUE})`.

## Environment

`REPO`, `PR`, `ISSUE`, `WORKTREE_DIR` from pipeline env vars or user input.

## Workflow

### 1. Read review

```
python3 $MONOREPO_ROOT/.agents/skills/dev-resolve/scripts/review_reader.py --repo "$REPO" --pr "$PR" [--review-id $REVIEW_ID]
```

Output JSON: `{ "title", "state", "reviewBody", "comments" }`.

### 2. Classify and plan (AI judgment)

Parse severity labels (`[CRITICAL]`, `[WARNING]`, `[SUGGESTION]`).
Plan fix strategy per item.

### 3. Fix code (AI judgment)

All edits in `$WORKTREE_DIR` using Read/Edit/Write tools. Never edit files in the canonical repo dir.

### 4. Commit and push

```bash
git -C "$WORKTREE_DIR" add -A
git -C "$WORKTREE_DIR" commit -m "fix: address review comments (#$ISSUE)"
git -C "$WORKTREE_DIR" push
```

### 5. Post response

Write response per [response-template.md](references/response-template.md).
Response file: `.workspace/messages/${REPO##*/}-pr-${PR}-response.md`

```
python3 $MONOREPO_ROOT/.agents/skills/dev-resolve/scripts/response_poster.py --repo "$REPO" --pr "$PR" --body-file <path> --cleanup
```

### 6. Notify user

Summarize fixed and skipped counts. Advise re-review.

## Constraints

- Use `-R "$REPO"` for all `gh` commands.
- Scripts use `$MONOREPO_ROOT`-based absolute paths. Do not run them from a relative working directory.
