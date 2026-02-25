---
name: dev-review
description: PR code review skill. Run in a separate session from the code author to provide unbiased review. Outputs GitHub PR Review (inline comments + summary). Activates on "review PR", "code review", "/dev-review", etc.
---

# Dev-Review

Review PRs in a **different session** from the code author. Leave comments only — never modify code.

## Review Steps

### 1. Check PR

Run in the target area (`server/` or `client/`):

```bash
gh pr view {PR#}
gh pr diff {PR#}
gh issue view {Issue#}  # check related Issue
```

### 2. Analyze Code

Read PR diff + surrounding context of changed files. Verify compliance with `client/CLAUDE.md` or `server/CLAUDE.md`.

**Focus areas**: Security (OWASP Top 10), type safety (`any` abuse, missing nullable), edge cases, error handling, performance (N+1 queries, etc.), project conventions

### 3. Classify Severity

| Tag | Meaning |
|-----|---------|
| `[CRITICAL]` | Must fix — bugs, security vulnerabilities, data loss risk |
| `[WARNING]` | Should fix — potential issues, performance degradation |
| `[SUGGESTION]` | Optional improvement — readability, conventions, better patterns |

### 4. Submit PR Review

Use `gh pr review` with inline comments + summary. **Must use `--body-file`** (avoids shell conflicts with markdown backticks):

```bash
mkdir -p .workspace/messages
cat > .workspace/messages/pr-{PR#}-review.md <<'REVIEWEOF'
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
REVIEWEOF

gh pr review {PR#} \
  --body-file .workspace/messages/pr-{PR#}-review.md \
  --{comment|request-changes}

rm .workspace/messages/pr-{PR#}-review.md
```

- 1+ Critical → `--request-changes`
- 0 Critical → `--comment`

### 5. Report to User

- Summarize Critical/Warning/Suggestion counts
- If Critical exists → advise fixing via `/dev-resolve`
- If no Critical → advise user can approve and merge

## Review Principles

- **No code modifications** — comments only
- **No bias** — evaluate the code itself, not assumed intent
- **Be specific** — cite `file:line` with problem and alternative
- **No over-reviewing** — do not use Critical/Warning for trivial style differences
