---
name: dev-review
description: PR code review skill. Run in a separate session from the code author to provide unbiased review. Outputs GitHub PR Review (inline comments + summary). Activates on "review PR", "code review", "/dev-review", etc.
---

# Dev-Review

Review PRs in a **different session** from the code author. Comments only — never modify code.

## Steps

### 1. Check PR

```bash
gh pr view {PR#}
gh pr diff {PR#}
gh issue view {Issue#}
```

### 2. Analyze Code

Read diff + surrounding context. Check compliance with `{area}/CLAUDE.md`.

**Focus**: Security (OWASP Top 10), type safety, edge cases, error handling, performance (N+1), conventions.

### 2.5. Verify Test Plan

Read PR body and check `- [ ]` test plan items:

```bash
BODY=$(gh pr view {PR#} --json body --jq '.body')
```

For each `- [ ]` item, determine if it can be verified by reading the diff and reasoning about correctness. Mark verified items by updating the PR body (replace `- [ ]` with `- [x]`):

```bash
# Update a verified item (repeat for each verified line)
BODY=$(echo "$BODY" | sed 's/- \[ \] Verified item description/- [x] Verified item description/')
gh pr edit {PR#} --body "$BODY"
```

- Items verifiable from the diff → check and update PR body
- Items requiring runtime/manual testing → leave as `- [ ]`, note as `[SUGGESTION]` in review

### 3. Classify Severity

| Tag | Meaning |
|-----|---------|
| `[CRITICAL]` | Must fix — bugs, security, data loss |
| `[WARNING]` | Should fix — potential issues, perf degradation |
| `[SUGGESTION]` | Optional — readability, conventions, better patterns |

### 4. Submit Review

**Must use `--body-file`** to avoid shell conflicts:

```bash
mkdir -p .workspace/messages
cat > .workspace/messages/pr-{PR#}-review.md <<'EOF'
## Review Summary

| Severity | Count |
|----------|-------|
| [CRITICAL] | N |
| [WARNING] | N |
| [SUGGESTION] | N |

### Critical
1. `file:line` — description

### Warning
1. `file:line` — description

### Suggestion
1. `file:line` — description
EOF

gh pr review {PR#} --body-file .workspace/messages/pr-{PR#}-review.md --{comment|request-changes}
rm .workspace/messages/pr-{PR#}-review.md
```

- 1+ Critical → `--request-changes`
- 0 Critical → `--comment`

### 5. Report

Summarize counts. If Critical → advise `/dev-resolve`. If none → advise approve & merge.

## Constraints

- **Comments only** — never modify code
- **No bias** — evaluate code itself, not assumed intent
- **Be specific** — cite `file:line` with problem and alternative
- **No over-reviewing** — don't flag trivial style differences as Critical/Warning
