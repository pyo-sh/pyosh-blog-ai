---
name: dev-plan
description: Convert decision files in decisions/ directory to GitHub Issues. Establish tasks from decision files, register Issues, and clean up files. Used as a pre-step before /dev-workflow. Activates on "/dev-plan", "create issues", "convert decisions to issues", etc.
---

# Dev-Plan

Convert decision files in `decisions/` to GitHub Issues and clean up. Pre-step for `/dev-workflow`.

## Git Remote

| Area | Path | GitHub Repo |
|------|------|-------------|
| server | `server/` | `pyo-sh/pyosh-blog-be` |
| client | `client/` | `pyo-sh/pyosh-blog-fe` |

## Workflow

### 1. Detect Target Area

Use argument if provided. Otherwise:
- Infer from current conversation context
- Scan both `decisions/` directories for convertible files
- Ask user if unable to determine

### 2. Scan & Classify Decision Files

Read all `.md` files in `docs/{area}/decisions/` and classify by **status**:

| Status | Action |
|--------|--------|
| `accepted`, `rejected` | Delete file + remove from index (already completed) |
| `pending`, `deferred` | Do not touch (in progress/deferred) |
| `draft`, no status | **Convert to GitHub Issue** |

Extract status from file metadata (e.g., `> **Status**: draft`).

### 3. Determine Priority

1. Query existing open Issues: `gh issue list --state open --repo {repo} --json number,title,labels`
2. Check priority labels in `{area}/.github/labels.json`
3. AI judges priority based on each decision's phase, dependencies, and content vs. existing Issues
4. **Present priority assignments to user for approval** before proceeding

Reference: [priority-guide.md](references/priority-guide.md)

### 4. Create Issues

- May **group** related decision files into a single Issue (AI judgment)
- For each Issue:
  - Use `--repo` flag to target the correct repo
  - Apply type label + priority label via `--label`
  - Write `--body` based on decision file content (goals, scope, tasks)

Issue body format:
```
## Overview
{decision file goals/background}

## Scope
{decision file scope}

## Tasks
- [ ] Item 1
- [ ] Item 2

## References
- Decision filename, phase info, dependencies, etc.
```

### 5. Clean Up Files

After Issue creation:
1. Delete converted decision files
2. Delete `accepted`/`rejected` status files
3. Remove deleted file references from `decisions.index.md`
4. Report cleanup results to user

### 6. Report Results

Output summary of created Issues (number + URL + priority) and cleaned-up files.

## Constraints

- Never modify/delete `pending` or `deferred` status files
- Always get priority approval before creating Issues
- Never run `gh` from root — always use `--repo` flag
