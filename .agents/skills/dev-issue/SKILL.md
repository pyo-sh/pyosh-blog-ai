---
name: dev-issue
description: Create GitHub Issues from docs/{area}/{plans,decisions} files or user requests. Activates on "/dev-issue", "create issues", "convert to issues", etc.
---

# Dev-Issue

Create GitHub Issues from documentation files or user requests. Git remote rules in `CLAUDE.md`.

## Input Sources

1. **docs files**: `docs/{area}/plans/*.md` or `docs/{area}/decisions/*.md`
2. **User request**: Direct description from the user

When invoked, determine input from argument. If no argument or ambiguous, **ask the user** which source to use.

## Workflow

### 1. Determine Input Source & Area

- If argument specifies a source (file path, area, or direct request), use it.
- Otherwise ask the user:
  - Which source? (decisions / plans / direct request)
  - Which area? (client / server / workspace)

### 2. Gather Content

#### From `decisions/` files

Read `.md` files in `docs/{area}/decisions/`. Extract status from `> **Status**: {status}` line.

| Status | Action |
|--------|--------|
| `accepted`, `rejected` | Delete file + remove from index |
| `pending`, `deferred` | Do not touch |
| `draft`, no status | **Convert to GitHub Issue** |

#### From `plans/` files

Read `.md` files in `docs/{area}/plans/`. All files are candidates for conversion. Present list to user for selection.

#### From user request

Use the user's description directly as Issue content.

### 3. Determine Issue Type & Format

Read the target repository's `.github/ISSUE_TEMPLATE/*.yml` files to determine:
- Available issue types (bug, feature, refactor, etc.)
- Required and optional fields per type
- Available labels

Select the appropriate template based on the content. Compose the Issue body following the template's field structure.

### 4. Create Issues

1. Query existing issues: `gh issue list --state open --repo {repo} --json number,title,labels`
2. **Present draft Issues to user for approval** before creating
3. May group related items into a single Issue
4. Use `--repo` flag for `gh` commands
5. Apply type label + priority label via `--label`

### 5. Clean Up (docs files only)

For `decisions/` files:
1. Delete converted decision files (`draft` / no status)
2. Delete `accepted`/`rejected` files
3. Update `decisions.index.md`

For `plans/` files:
1. Delete converted plan files
2. Update `plans.index.md` if it exists

### 6. Report

Output created Issues (number + URL + labels) and cleaned-up files.

## Constraints

- Never modify/delete `pending` or `deferred` decision files
- Always get user approval before creating Issues
- Always use `--repo` flag for `gh` commands
- Always reference the target repo's `.github/ISSUE_TEMPLATE` for Issue format
