# 2026-03-07 Workspace progress

## Headless pipeline - tmux pane을 synchronous subprocess로 전환 + self-healing (#55, PR #56)

- **Issue**: dev-pipeline이 review/resolve AI를 tmux side pane으로 실행하여 잦은 오류 발생 (PANE_DEAD, orphan pane, pane ID 재사용). ~230줄의 방어 코드가 pipeline-helpers.sh의 46% 차지. Docker 환경에서 tmux 의존으로 실행 불가.
- **Decision**: Approach B (synchronous blocking subprocess) 채택. `timeout 900 claude -p --dangerously-skip-permissions --no-session-persistence --allowedTools ... --max-turns N` 으로 blocking 실행.
- **Changes**:
  - tmux pane 함수 전체 제거 (~150줄): `pipeline_orchestrator_pane`, `pipeline_open_pane*`, `pipeline_pane_alive*`, `pipeline_pane_snapshot`, `pipeline_pane_orphan_cleanup`, `pipeline_kill_pane`, `pipeline_kill_state_pane`
  - polling 함수 제거: `pipeline_poll_review`, `pipeline_poll_commits`
  - `pipeline_run_headless()` 추가 - synchronous `claude -p` with timeout, tool allowlist, max-turns
  - Self-healing 함수 추가: `pipeline_stage_retry()` (per-stage max 3), `pipeline_recovery_log()`, `pipeline_format_escalation()`
  - dev-review: diff-first 워크플로우 (`gh pr diff` 우선, 코드베이스 탐색 금지), `--json` 명시 필드, repo 경고
  - dev-build: worktree 생성 전 `git fetch origin && git rebase origin/main || git merge origin/main`
  - dev-resolve: repo 경고 추가
  - SKILL.md 55% 축소 (258 -> 116줄) via progressive disclosure into `references/process-lifecycle.md`, `references/recovery.md`
  - `pane-lifecycle.md` 삭제, `process-lifecycle.md` 신규
- **Review**: PR #56 comment review - WARNING 2 (decision doc 불일치, status), SUGGESTION 2 (vestigial agent field, step 5 annotation)
- **Files**: `pipeline-helpers.sh`, `SKILL.md`, `process-lifecycle.md`, `recovery.md`, `dev-review/SKILL.md`, `dev-build/SKILL.md`, `dev-resolve/SKILL.md`
