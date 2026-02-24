# Workflow Examples

## Scenario 1: Progress Record (task completion)

**Issue**: `#42 - Blog post card component`

1. Read `docs/client/progress.index.md` → check recent work
2. Create `progress/progress.2026-02-15.md` (detailed log, refs `#42`)
3. Add one-line summary at top of `progress.index.md`

---

## Scenario 2: Findings Record (technical research)

**Issue**: `#55 - Post list API implementation`

1. Read `docs/server/findings.index.md` → check existing related research
2. Investigate pagination strategies (cursor-based vs offset-based)
3. Create `findings/findings.004-pagination-strategy.md`
4. Add entry to `findings.index.md`
5. Record progress (same as Scenario 1)

---

## Scenario 3: Decision Record (architecture decision)

**Issue**: `#78 - Image storage strategy`

1. Read `docs/server/decisions.index.md` → check existing decisions
2. Research S3 vs Cloudflare R2 vs local storage
3. Create `decisions/decision-003-image-storage.md` (status: **draft**, with option comparison)
4. Add entry to `decisions.index.md`
5. Request user decision → update status to `accepted` after approval

---

## Scenario 4: Parallel Agents (worktree isolation)

**Situation**: Agent A (server progress) + Agent B (client findings) running concurrently

### Agent A Flow
1. `git worktree add .claude/worktrees/dev-log-20260224-143022 -b dev-log/20260224-143022 main`
2. Write `docs/server/progress/progress.2026-02-24.md` inside worktree
3. `git add docs/ && git commit -m "docs: progress - API endpoint implementation"`
4. `mkdir .claude/dev-log.lock` → acquire lock
5. `git rebase main` → `git merge dev-log/20260224-143022 --ff-only`
6. `rmdir .claude/dev-log.lock` → release lock
7. `git worktree remove ...` → cleanup

### Agent B Flow (concurrent)
1. `git worktree add .claude/worktrees/dev-log-20260224-143025 -b dev-log/20260224-143025 main`
2. Write `docs/client/findings/findings.009-ssr-caching.md` inside worktree
3. `git add docs/ && git commit -m "docs: findings - SSR caching strategy research"`
4. `mkdir .claude/dev-log.lock` → **wait** (Agent A holds lock)
5. Agent A merge complete → acquire lock
6. `git rebase main` → Agent A's changes now reflected in main
7. `git merge dev-log/20260224-143025 --ff-only` → success
8. Release lock → cleanup

**Key**: Document writing runs in parallel; only merge is serialized.
