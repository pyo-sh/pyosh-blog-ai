---
name: dev-issue
description: >
  Create GitHub Issues from docs files or user requests.
  Use when: (1) converting docs/{area}/decisions/ or docs/{area}/plans/ files to Issues,
  (2) user describes a task to register as an Issue, (3) user says "/dev-issue", "create issues", "convert to issues".
---

# Dev-Issue

Area definitions, directory/repo mappings: [monorepo-layout.md](../../references/monorepo-layout.md)

## Workflow

### 1. Determine Source & Area

Use argument if provided. Otherwise ask the user:
- **Source**: decisions / plans / direct request
- **Area**: client / server / workspace

### 2. Gather Content

**decisions/**: Read `docs/{area}/decisions/*.md`. Extract `> **Status**: {status}`.

| Status | Action |
|--------|--------|
| `accepted`, `rejected` | Delete file + remove from index |
| `pending`, `deferred` | Skip (do not touch) |
| `draft`, no status | Convert to Issue |

**plans/**: Read `docs/{area}/plans/*.md`. Present candidate list for user selection.

**direct request**: Use the user's description as Issue content.

### 3. Format Issue

1. Read the target repo's `.github/ISSUE_TEMPLATE/*.yml` to get available types, fields, and labels.
2. Select the matching template (bug / feature / refactor) based on content.
3. Compose the Issue body following the template's field structure.

#### Title rules

- **No type prefix** in Issue titles. Do not prepend `feat:`, `fix:`, `refactor:`, etc.
- Type is conveyed through GitHub labels, not the title.
- Good: `Admin 댓글 관리 페이지`
- Bad: `feat: Admin 댓글 관리 페이지`

#### Labels

Labels are GitHub labels defined in each repo's `.github/labels.json`.

| Category | Labels |
|----------|--------|
| Type | `feat`, `bug`, `refactor`, `docs`, `test`, `chore` |
| Priority | `priority:0` ~ `priority:4` |
| Status | `fixed`, `duplicate`, `attention`, `question` |

Always apply **type + priority** labels when creating an Issue.

### 4. Create Issues

1. Check existing: `gh issue list --state open --repo {repo} --json number,title,labels`
2. Present draft to user for approval.
3. Group related items into a single Issue when appropriate.
4. Create with `--repo` flag and apply `--label` for type + priority.

### 5. Clean Up (docs sources only)

**decisions/**: Delete converted + accepted/rejected files → update `decisions.index.md`.
**plans/**: Delete converted files → update `plans.index.md` if it exists.

### 6. Report

Output: Issue number, URL, labels, and cleaned-up file list.

## Constraints

- Never modify/delete `pending` or `deferred` decision files
- Always get user approval before creating Issues
- Always use `--repo` flag for `gh` commands
