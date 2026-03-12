---
name: dev-review
description: PR code review skill. Outputs structured review JSON then publishes via review_publish.py. Runs in a separate session from the code author, invoked from monorepo root with target repo via environment variables.
---

# Dev-review

Read-only review. Never modify code.

## Invariants

1. Never modify code - read-only review only.
2. All publishing via `review_publish.py`. Never call `gh pr comment`, `gh pr review`, or `gh api` for posting directly.
3. **All verdicts publish.** `approve`: empty `findings`, `verdict: "approve"` - still complete Steps 3-5.

## Environment

Use these env vars when present (pipeline sets them). Do not assume cwd is the repo checkout.

```bash
REPO="${PIPELINE_REPO:-pyo-sh/pyosh-blog-fe}"
REPO_DIR="${PIPELINE_REPO_DIR:-/workspace/client}"
PR="${PIPELINE_PR:?PIPELINE_PR is required}"
MONOREPO="${PIPELINE_MONOREPO_ROOT:-/workspace}"
```

## Workflow

1. **Read PR** with explicit `-R`: `gh pr diff "$PR" -R "$REPO"` and `gh pr view "$PR" -R "$REPO" --json number,title,state,body`
2. **Analyze**: Review diff first. Read files under `REPO_DIR` only when diff context is insufficient.
3. **Write review JSON** to `${MONOREPO}/.workspace/dev-review/pr-${PR}/review.json` conforming to `scripts/review_schema.json`.
4. **Publish** via `review_publish.py`. Never post reviews directly.

```bash
REVIEW_DIR="${MONOREPO}/.workspace/dev-review/pr-${PR}"
python3 "${MONOREPO}/.agents/skills/dev-review/scripts/review_publish.py" \
  --input "${REVIEW_DIR}/review.json" \
  --mode "${REVIEW_MODE:-publish}" \
  --repo "$REPO" --pr "$PR" --output-dir "$REVIEW_DIR"
```

5. **Report** artifact path and publisher exit status, then exit.

## Constraints

### Verdict rules

- `request_changes`: any P0 or P1 issue exists
- `comment`: only P2/P3/info issues
- `approve`: no issues found
