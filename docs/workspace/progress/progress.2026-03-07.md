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

## Orchestrator headless 전환 + merge queue (#57)

- **Issue**: dev-orchestrator가 tmux pane 기반 dispatch 사용. pane release 실패, 과잉 dispatch, pane death 감지 등 반복적 버그 발생. dev-pipeline이 이미 headless 전환 완료 (#55).
- **Changes**:
  - tmux pane 함수 전체 제거: `orch_find_idle_panes`, `orch_pane_alive`, `orch_release_pane`, `orch_verify_startup`, `ORCH_WORK_WINDOWS`
  - `orch_dispatch()`: tmux send-keys → 백그라운드 `claude -p &` + PID 반환
  - `orch_process_alive()`, `orch_stop_process()` 추가 (PID 기반)
  - `orch_check_completion()`: pane command 체크 → `kill -0 $pid` 체크
  - `_orch_pr_list()`: `cd area_dir && gh pr list` → `gh pr list -R $repo` (explicit repo targeting)
  - `orch_detect_stall()`: 3 params → 2 params (area_dir 제거)
  - `orch_record_dispatch()`: 2회 state write → 단일 jq filter
  - `orch_check_completion()`: 2회 `gh pr list` (merged + open) → 단일 `--state all` 호출
  - `orch_init()`: `orchestratorPane` 파라미터/필드 제거
  - `orch_poll_cycle()`, `orch_print_summary()`: 파라미터 축소
  - Merge queue: `pipeline_acquire_merge_lock()` / `pipeline_release_merge_lock()` - `mkdir` 기반 atomic lock + PID stale 감지
  - `$BASHPID` 수정: merge lock PID가 `$$`(top-level shell)이 아닌 현재 프로세스 PID 기록
  - `pipeline_list()`: 3 jq → 1 jq 통합
  - SKILL.md, references 최적화: 중복 JSON 예시 제거, stale 함수 시그니처 수정, Kahn's algorithm 설명 제거
  - README.md: 다이어그램 tmux → headless, orchestrator 섹션 추가, merge queue 섹션 추가
- **Review**: /simplify 3회 통과. `$$` → `$BASHPID` 버그 수정, 죽은 변수 제거, pipeline_list 효율화.
- **Files**: `orchestrate-helpers.sh`, `pipeline-helpers.sh`, `SKILL.md` (orchestrator/pipeline), `state-detection.md`, `dependency-resolution.md`, `recovery.md`, `process-lifecycle.md`, `README.md`
