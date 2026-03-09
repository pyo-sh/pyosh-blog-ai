# Claude Code shared config

Shared Claude Code configuration for the pyosh-blog workspace.
This directory is the source of truth - bootstrap copies these templates to each repo.

## Directory structure

```
tools/claude/
├── bootstrap.sh                  # Sync script (--dry-run / --apply)
├── README.md                     # This file
├── README.ko.md                  # Korean version
└── templates/
    ├── root/                     # Workspace root repo
    │   ├── CLAUDE.md
    │   └── .claude/settings.json
    ├── client/                   # Next.js frontend repo
    │   ├── CLAUDE.md
    │   └── .claude/
    │       ├── settings.json
    │       └── rules/
    │           ├── frontend-fsd.md
    │           └── tailwind-v4.md
    ├── server/                   # Fastify backend repo
    │   ├── CLAUDE.md
    │   └── .claude/
    │       ├── settings.json
    │       └── rules/
    │           └── backend-fastify.md
    └── shared/                   # Copied to all three repos
        └── .claude/
            └── rules/
                ├── bash.md
                ├── docs-context.md
                ├── git-safety.md
                ├── markdown-writing.md
                └── worktree-workflow.md
```

## What bootstrap does

1. Copies each repo's `CLAUDE.md` and `.claude/settings.json`
2. Copies `shared/.claude/rules/` to all three repos
3. Copies repo-specific `.claude/rules/` on top (client or server rules)
4. Creates `.claude/settings.local.json` in client/server with `claudeMdExcludes` to prevent parent rule duplication (create-only - never overwrites existing)
5. Adds `settings.local.json` and `CLAUDE.local.md` to each repo's `.git/info/exclude`
6. Backs up existing files to `.workspace/backups/claude-code/`

## Quick start

```bash
# Preview what will change
bash tools/claude/bootstrap.sh --dry-run

# Apply changes
bash tools/claude/bootstrap.sh --apply
```

## After applying

Open Claude Code in each repo and verify:

- `/memory` - loaded CLAUDE.md and rules
- `/permissions` - allow, ask, deny lists

## How to edit

1. Edit templates in `tools/claude/templates/`, not the deployed copies
2. Run `bootstrap.sh --apply` to sync changes
3. Commit the template changes in this repo

## What goes where

| Content | Location |
|---------|----------|
| Repo purpose, tech stack, workflow | `templates/{repo}/CLAUDE.md` |
| Permissions, env vars | `templates/{repo}/.claude/settings.json` |
| Shared team rules (bash, git, docs) | `templates/shared/.claude/rules/` |
| Repo-specific coding rules | `templates/{repo}/.claude/rules/` |
| Personal preferences | `CLAUDE.local.md` or `.claude/settings.local.json` (not here) |

## Notes

- `settings.local.json` is personal/machine-specific. Bootstrap creates it only if absent.
- If you move the workspace directory, run bootstrap again to update absolute paths in child repo excludes.
