---
name: dev-review
description: PR code review skill. Runs in a separate session from the code author. Outputs structured review JSON, then publishes via review_publish.py. Works correctly when the Claude session starts from monorepo root and the target repo is provided via environment variables.
---

# Dev-review

Comments only. Never modify code.

## Runtime contract when invoked by dev-pipeline

The parent pipeline may launch this skill from monorepo root. Use these environment variables if present:

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

### 3. Write review JSON

Write a `review.json` file conforming to the schema at `.agents/skills/dev-review/scripts/review_schema.json`.

Output directory: `.workspace/dev-review/pr-{PR}/review.json`

```json
{
  "verdict": "approve | request_changes | comment",
  "summary": "Short prose summary of findings.",
  "issues": [
    {
      "severity": "P0 | P1 | P2 | P3 | info",
      "path": "relative/file/path",
      "line": 42,
      "title": "One-line issue title",
      "body": "Explanation and evidence.",
      "suggested_fix": "Optional fix description"
    }
  ]
}
```

Verdict rules:
- `request_changes` when any P0 or P1 issue exists
- `comment` when only P2/P3/info issues exist
- `approve` when no issues found

### 4. Publish via review_publish.py

After writing `review.json`, call the publisher CLI. Never post reviews directly.

```bash
MONOREPO="${PIPELINE_MONOREPO_ROOT:-/workspace}"
REVIEW_DIR="${MONOREPO}/.workspace/dev-review/pr-${PR}"
PUBLISHER="${MONOREPO}/.agents/skills/dev-review/scripts/review_publish.py"

python3 "$PUBLISHER" \
  --input "${REVIEW_DIR}/review.json" \
  --mode "${REVIEW_MODE:-dry-run}" \
  --repo "$REPO" \
  --pr "$PR" \
  --output-dir "$REVIEW_DIR"
```

The publisher validates schema, checks for contamination, renders markdown, and publishes only in `publish` mode. If validation fails, the publisher exits non-zero and no review is posted.

### 5. Report result

Report the artifact path and publisher exit status, then exit.

## Prohibited actions

The following commands must never be used directly:

- `gh pr comment`
- `gh pr review`
- `gh api` (for posting comments or reviews)

All GitHub review publishing must go through `review_publish.py`.

## Constraints

- Comments only
- Never modify code
- Do not inspect unrelated code outside the diff unless absolutely necessary
- All review output must pass through the publisher boundary
