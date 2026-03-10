---
name: dev-review
description: PR code review skill. Runs in a separate session from the code author. Posts a GitHub PR Review that begins with `## Review Summary`. Works correctly when the Claude session starts from monorepo root and the target repo is provided via environment variables.
---

# Dev-Review

Comments only. Never modify code.

## Runtime contract when invoked by dev-pipeline

The parent pipeline may launch this skill from monorepo root. In that case use these environment variables if present:

- `PIPELINE_AREA`
- `PIPELINE_REPO`
- `PIPELINE_REPO_DIR`
- `PIPELINE_PR`
- `PIPELINE_MONOREPO_ROOT`

Do not assume the current cwd is the repo checkout.

Recommended command style:

```bash
REPO="${PIPELINE_REPO:-pyo-sh/pyosh-blog-fe}"
REPO_DIR="${PIPELINE_REPO_DIR:-/workspace/client}"
PR="${PIPELINE_PR:?PIPELINE_PR is required}"

gh pr diff "$PR" -R "$REPO"
gh pr view "$PR" -R "$REPO" --json number,title,state,body
```

## Steps

### 1. Read PR

Use `gh pr diff` and `gh pr view` with explicit `-R`.

### 2. Analyze code

Review the diff first. Read specific files under `REPO_DIR` only when diff context is insufficient.

### 3. Classify and submit

The review body **must start with `## Review Summary`**.

#### Required review body format

```markdown
## Review Summary

| Severity | Count |
|----------|-------|
| [CRITICAL] | N |
| [WARNING] | N |
| [SUGGESTION] | N |

### Critical
1. `file:line` - description

### Warning
1. `file:line` - description

### Suggestion
1. `file:line` - description
```

Use `--request-changes` when Critical >= 1, `--comment` otherwise.

Write the temporary message file with an area-scoped name to avoid cross-repo collisions:

```bash
MSG_FILE="${PIPELINE_MONOREPO_ROOT:-/workspace}/.workspace/messages/${PIPELINE_AREA:-manual}-pr-${PR}-review.md"
mkdir -p "$(dirname "$MSG_FILE")"
cat > "$MSG_FILE" <<'EOF_REVIEW'
{body}
EOF_REVIEW

gh pr review "$PR" -R "$REPO" --body-file "$MSG_FILE" --comment
rm -f "$MSG_FILE"
```

Use `--request-changes` when 1+ Critical exists.

## Constraints

- Comments only
- Never modify code
- Do not inspect unrelated code outside the diff unless absolutely necessary
