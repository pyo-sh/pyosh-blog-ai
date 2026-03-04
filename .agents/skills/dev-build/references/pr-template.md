# PR Template

Use the area's `.github/PULL_REQUEST_TEMPLATE.md` as the base. Fill in each section; delete sections that don't apply.

## PR Title
```
{type}: {description} (#{N})
```

## gh pr create

**`--body-file` required** - inline `--body` causes shell escape conflicts with markdown backticks.

```bash
mkdir -p .workspace/messages
cat > .workspace/messages/pr-{N}-body.md <<'PREOF'
## Summary
Closes #{N}
- Change description

## Changes
| File | Change |
|------|--------|
| `file` | description |
PREOF

gh pr create \
  --title "{type}: description (#{N})" \
  --body-file .workspace/messages/pr-{N}-body.md

rm .workspace/messages/pr-{N}-body.md
```
