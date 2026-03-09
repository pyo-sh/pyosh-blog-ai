# Claude Code guide

This repository uses a shared Claude Code setup for team consistency.

## What is shared

These files are version-controlled and should be treated as team policy:

- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/rules/*.md`
- `.claude/hooks/*`
- `.claude/README.md`

## What stays personal

Put personal preferences and machine-specific overrides in:

- `CLAUDE.local.md`
- `.claude/settings.local.json`
- `~/.claude/CLAUDE.md`
- `~/.claude/settings.json`

Do not put personal preferences into the shared `CLAUDE.md`.

## Why the setup is split

- `CLAUDE.md` should stay short and stable.
- `.claude/rules/` holds modular rules, and path-scoped rules only load when relevant.
- `.claude/settings.json` holds permissions, hooks, shared environment, and additional directories.
- `.claude/settings.local.json` is for local excludes and personal overrides.

## Daily workflow

1. Start Claude Code from the repository you intend to change.
2. If you need file edits, create or switch to a worktree first.
3. Read the relevant docs index files before changing architecture or behavior.
4. Keep shell commands readable. Use a short script for multi-step or risky work.
5. After committing in a worktree, stop and decide whether to merge locally or open a PR.

## Bash and environment policy

- Small one-off commands may use 1 or 2 simple inline environment variables.
- If 3 or more environment variables are needed, or quoting is non-trivial, use a script.
- Shared or persistent environment belongs in `.claude/settings.json` or a `SessionStart` hook that writes to `CLAUDE_ENV_FILE`.
- Do not invent a custom JSON syntax inside bash commands.
- For `gh`, `pnpm`, or repo-local scripts in another repository, use `(cd "$repo" && ...)` inside one command or one short script.

## Child repo exclusions

When Claude runs inside `client/` or `server/`, parent workspace instructions would otherwise load too. The bootstrap script writes a local `.claude/settings.local.json` in child repos with absolute `claudeMdExcludes` entries so each child repo uses its own instructions without duplicating the root rules.

## Updating the shared setup

The source of truth is `tools/claude/templates/` in the workspace root.

Preview changes:

```bash
bash tools/claude/bootstrap.sh --dry-run
```

Apply changes:

```bash
bash tools/claude/bootstrap.sh --apply
```

## Verification

After rollout, open Claude in each repository and check:

- `/memory` - which `CLAUDE.md` and rules are loaded
- `/permissions` - effective allow, ask, and deny rules
- `/hooks` - installed hook behavior
