# pyosh-blog

Personal blog monorepo — Next.js frontend + Fastify API server.

## Git Repo Structure (Important)

Each directory is an **independent Git repo**. Run `gh` commands from the corresponding directory.

| Path | GitHub Repo | Contents |
|------|------------|----------|
| `/` (root) | `pyo-sh/pyosh-blog-ai` | docs, skills, workflow config |
| `/client/` | `pyo-sh/pyosh-blog-fe` | Next.js frontend |
| `/server/` | `pyo-sh/pyosh-blog-be` | Fastify API server |

```bash
# Example: check server issues
cd /Users/pyosh/Workspace/pyosh-blog/server && gh issue list
```

## Directory Structure

```
pyosh-blog/
├── client/                      # Next.js (independent repo) → client/CLAUDE.md
├── server/                      # Fastify (independent repo) → server/CLAUDE.md
├── docs/{client,server,workspace}/ # progress/, findings/, decisions/ records
├── skills/                      # Skill sources
└── .workspace/                  # gitignored — worktrees, pipeline state
```

### docs/ Reference

When you need context about past work, technical decisions, or known issues, **read the relevant docs first**:

| Path | Contents |
|------|----------|
| `docs/{area}/progress.index.md` | Task completion timeline |
| `docs/{area}/findings.index.md` | Technical research & issue resolutions |
| `docs/{area}/decisions.index.md` | Architecture/tech decisions |

- `workspace` area covers root repo changes (tools/, Docker, tmux, skills, workflow config)
- CI/CD is recorded under the respective area (`client` or `server`), not `workspace`

## Writing style

- Use sentence case for headers, not title case
- Never use em dashes (—). Use spaced hyphens ` - ` (space, hyphen, space) instead.
- Don't make up or add content I didn't say. Stick to what I've said. Rephrasing is okay, but don't embellish.

## Behavior

When I paste large content with no instructions, just summarize it.

For a complex bash command, break it down into multiple simple commands so the user doesn't have to approve each one individually. Alternatively, put it in a bash script file and run it with `bash /tmp/<script>.sh`.

Example - instead of:
```bash
sleep 60 && ps aux | grep foo | wc -l && echo "---" && ls -la /some/path
```

Do this:
```bash
sleep 60
```
```bash
ps aux | grep foo | wc -l
```
```bash
ls -la /some/path
```

Also avoid complex pipes. Instead of:
```bash
grep "file: '" patch-cli.js | sed "s/.*file: '\([^']*\)'.*/\1/" | sort > /tmp/used.txt
```

Either run each step individually or put it in a script file and run with `bash {PROJECT ROOT}/.workspace/scripts/YYYY-MM-DD-{TASK}-{ID}.sh`. This temporary file should be deleted after work.

For git operations in other directories, use `cd <path> && git ...` instead of `git -C <path>`.

Never use `2>&1` in bash commands. Keep stderr and stdout separate.

## Common dev principles

- TypeScript Strict Mode
- pnpm package manager
- ESLint + Prettier auto-formatting
- File names in kebab-case

---

## Task Rules

### client / server (Issue-driven)

`/dev-pipeline` manages the full cycle: build → review → resolve → merge.
Branch, commit, PR, and worktree rules are built into the skill.

### root repo (user-directed)

Perform tasks as directed by the user. An Issue may be created depending on scope.
After completing work, record it in `docs/workspace/` with `/dev-log`.

```
create worktree → work → commit → STOP: ask user (local merge or PR) → /dev-log
```

> **IMPORTANT**: Any task involving file edits must start by **creating a worktree first**.
> The moment you determine that edits are needed — even mid-analysis — switch to a worktree before making any changes.
> Never edit files directly on main.

> **IMPORTANT**: After committing in a worktree, **always stop and ask the user** whether to merge locally or open a PR.
> Never merge automatically unless the user has explicitly instructed it in the same request.

- Worktree: `.workspace/worktrees/{type}-{description}`
- Branch: `{type}/{description}`
- Commit: `{type}: {description}`

## Git Rules

- main + feature branches only. Never push directly to main.
- All work must go through a worktree (`.workspace/worktrees/`).
- Always run `git pull origin main` to sync with remote before merging into main.
- Multi-agent: 1 agent = 1 task, worktree isolation. Never modify the same file concurrently.

## Skills

| Skill | Purpose |
|-------|---------|
| `/dev-pipeline` | Full cycle: build → review → resolve → merge (client/server) |
| `/dev-build` | Issue → Worktree → Code → PR (client/server) |
| `/dev-log` | progress / findings / decisions records |
| `/dev-review` | PR code review |
| `/dev-resolve` | Address review comments |
| `/frontend-design` | UI design tasks |
