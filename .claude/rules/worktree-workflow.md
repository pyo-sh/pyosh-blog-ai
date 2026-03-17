# Worktree workflow

- Any task involving file edits must start in a worktree.
- Do not edit directly on `main`.
- Use the workspace worktree convention: `.workspace/worktrees/{type}-{description}` from the workspace root.
- For area repos (client, server), worktrees also go under the **monorepo root** `.workspace/`, not inside the area directory. Path: `/workspace/.workspace/worktrees/{area}/{description}`. Read `.agents/references/monorepo-layout.md` before creating worktrees for area repos.
- Branch name: `{type}/{description}`
- Commit message: `{type}: {description}`
- After committing in a worktree, stop and ask whether to merge locally or open a PR.
- One agent equals one task. Avoid concurrent edits to the same file.
