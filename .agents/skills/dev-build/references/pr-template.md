# PR Template

## Body

```markdown
## Summary
Closes #{N}

- Change 1
- Change 2

## Changes
- **file1**: Description
- **file2**: Description

## Check plan
- Verification step 1
- Verification step 2

## Screenshots
(Attach if UI changes)
```

## Required
1. `Closes #{N}` — Auto-closes the Issue
2. **Summary** — 1-3 bullet points
3. **Check plan** — Post-merge verification steps (plain list, no checkboxes)

## PR Title
```
{type}: {description} (#{N})
```

## gh pr create

**`--body-file` required** — inline `--body` causes shell escape conflicts with markdown backticks.

```bash
mkdir -p .workspace/messages
cat > .workspace/messages/pr-{N}-body.md <<'PREOF'
## Summary
Closes #{N}
- Change description
## Check plan
- Verification step
PREOF

gh pr create \
  --title "{type}: description (#{N})" \
  --body-file .workspace/messages/pr-{N}-body.md

rm .workspace/messages/pr-{N}-body.md
```
