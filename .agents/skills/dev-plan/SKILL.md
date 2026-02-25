---
name: dev-plan
description: Convert decision files in decisions/ directory to GitHub Issues. Establish tasks from decision files, register Issues, and clean up files. Used as a pre-step before /dev-build. Activates on "/dev-plan", "create issues", "convert decisions to issues", etc.
---

# Dev-Plan

Convert decision files → GitHub Issues → clean up. Pre-step for `/dev-build`. Git remote rules in `CLAUDE.md`.

## Workflow

### 1. Detect Target Area

Use argument if provided. Otherwise infer from context, scan both `docs/{client,server}/decisions/`, or ask user.

### 2. Scan & Classify Decision Files

Read all `.md` in `docs/{area}/decisions/`. Extract status from `> **Status**: {status}` line.

| Status | Action |
|--------|--------|
| `accepted`, `rejected` | Delete file + remove from index |
| `pending`, `deferred` | Do not touch |
| `draft`, no status | **Convert to GitHub Issue** |

### 3. Determine Priority

1. Query existing: `gh issue list --state open --repo {repo} --json number,title,labels`
2. AI judges priority based on phase, dependencies, impact
3. **Present to user for approval** before creating

Reference: [priority-guide.md](references/priority-guide.md)

### 4. Create Issues

May group related decisions into a single Issue. Use `--repo` flag.

```markdown
## Overview
{decision goals/background}

## Scope
{decision scope}

## Tasks
- [ ] Item 1
- [ ] Item 2

## References
- Decision filename, phase, dependencies
```

Apply type label + priority label via `--label`.

### 5. Clean Up

1. Delete converted decision files
2. Delete `accepted`/`rejected` files
3. Update `decisions.index.md`

### 6. Report

Output created Issues (number + URL + priority) and cleaned-up files.

## Constraints

- Never modify/delete `pending` or `deferred` files
- Always get priority approval before creating Issues
- Always use `--repo` flag for `gh` commands
