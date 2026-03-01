# Review template

## Severity tags

| Tag | Meaning |
|-----|---------|
| `[CRITICAL]` | Must fix — bugs, security, data loss |
| `[WARNING]` | Should fix — potential issues, perf degradation |
| `[SUGGESTION]` | Optional — readability, conventions, better patterns |

1+ Critical → `--request-changes`. 0 Critical → `--comment`.

## Review body

```markdown
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
```

## Submission

```bash
mkdir -p .workspace/messages
cat > .workspace/messages/pr-{PR#}-review.md <<'EOF'
{body}
EOF

gh pr review {PR#} --body-file .workspace/messages/pr-{PR#}-review.md --{comment|request-changes}
rm .workspace/messages/pr-{PR#}-review.md
```
