# Response template

## Review response body

```markdown
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
```

## Submission

```bash
mkdir -p .workspace/messages
cat > .workspace/messages/pr-{PR#}-response.md <<'EOF'
{body}
EOF

gh pr comment {PR#} --body-file .workspace/messages/pr-{PR#}-response.md
rm .workspace/messages/pr-{PR#}-response.md
```
