---
name: dev-review
description: PR code review skill. Run in a separate session from the code author to provide unbiased review. Outputs GitHub PR Review (inline comments + summary). Activates on "review PR", "code review", "/dev-review", etc.
---

# Dev-Review

Review PRs in a **different session** from the code author. Comments only — never modify code.

## Steps

### 1. Read PR

```bash
gh pr view {PR#}
gh pr diff {PR#}
gh issue view {Issue#}
```

### 2. Analyze code

Read diff + surrounding context. Check `{area}/CLAUDE.md` compliance.

Focus: Security (OWASP Top 10), type safety, edge cases, error handling, performance (N+1), conventions.

### 2.5. Check plan review

Read Check plan items from PR body. For each item: note if covered by diff or requires post-merge verification.

### 3. Classify & submit

Classify findings by severity and submit. → [review-template.md](references/review-template.md)

### 4. Report

Summarize counts. If Critical → advise `/dev-resolve`. If none → advise approve & merge.

## Constraints

- Comments only — never modify code
- Cite `file:line` with problem and alternative
- Don't flag trivial style differences as Critical/Warning
