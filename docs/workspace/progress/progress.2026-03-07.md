# 2026-03-07 Workspace progress

## agent-tracker sidecar 경로 이동 + pipeline 중복 제거 + 토큰 버그 수정 (#62)

- **Issue**: agent-tracker에 3가지 문제. (1) sidecar 파일이 `/tmp/agent-tracker/`에 위치하여 시스템 재부팅 시 소실 + `chmod 700` 방어 필요, (2) footer pipeline state 요약이 orchestrator 섹션과 중복 표시, (3) TOKENS 컬럼이 대화 초반 값에서 갱신 안 됨 - transcript JSONL의 단일 턴 `input_tokens`가 누적값이 아닌 문제.
- **Changes**:
  - sidecar 경로: `/tmp/agent-tracker` -> `$REPO_ROOT/.workspace/agent-tracker` (agent-tracker.sh, on-statusline.sh, on-status.sh, setup.sh). `chmod 700` 방어 코드 제거.
  - `get_pipeline_summary()` 함수 + footer `pipeline_str` 참조 제거. orchestrator 섹션이 동일 정보를 더 상세히 표시.
  - 토큰 계산: transcript 파싱 -> statusLine JSON의 `current_usage` 필드 사용 (Claude Code v2.0.72+). `used_percentage` fallback. `TRANSCRIPT_TOKENS` export 유지 (context-bar.sh 호환).
  - on-statusline.sh: wrapper의 pre-computed `TRANSCRIPT_TOKENS` 우선 사용, standalone 호출 시에만 `current_usage` fallback (중복 jq 제거).
- **Research**: Claude Code statusLine JSON 공식 스키마 조사. `total_input_tokens`는 세션 누적값 (context 아님), `current_usage`가 정확한 per-request context 토큰. #13783 참조.
- **Review**: /simplify - 토큰 jq 중복 계산 제거 (wrapper pre-computed 우선 사용)
- **Files**: `agent-tracker.sh`, `on-statusline.sh`, `on-status.sh`, `statusline-wrapper.sh`, `setup.sh`, `README.md`

## agent-tracker UI 버그 수정 (#64)

- **Issue**: agent-tracker 대시보드 3가지 문제. (1) orchestrator 테이블에서 `pad_right`가 truncate하지 않아 가변 폭 컬럼 overflow 시 칸 밀림, (2) agent 작업 완료 후 done과 idle이 동일한 `○ idle` 뱃지로 표시, orchestrator footer에서도 done/active가 같은 `●` 아이콘, (3) `batch.state.json` 파일 존재만으로 orchestrator 실행 판별 - stop 후에도 파일이 남아 계속 실행 중으로 표시.
- **Changes**:
  - `agent-tracker.sh`: orchestrator 행 `pad_right` -> `trunc` 교체로 overflow 시 ellipsis 처리
  - `agent-tracker.sh`: `status_badge`/`_orch_badge`에 `done` 케이스 추가 (`✓ done`, blue). `(Done)` prefix 감지로 idle에서 done 승격. orchestrator footer done `✓` vs active `●` 아이콘 분리
  - `agent-tracker.sh`: orchestrator batch liveness - `orchestratorPid` + `orchestratorStartedAt`(lstart) 비교로 PID reuse 방지. batch_status: done/active/stopped 3단계 + header 색상 + footer `[DONE]`/`[STOPPED]` 라벨
  - `orchestrate-helpers.sh`: `orch_init()`에 `$PPID`(Claude Code PID) + `ps -o lstart=` 시작 시각을 `batch.state.json`에 기록
  - `session.docker.yml`: 현재 tmux 구성에 맞게 정리 - server2/client2 제거, 4 panes -> 2 panes (even-horizontal)
- **Files**: `agent-tracker.sh`, `orchestrate-helpers.sh`, `session.docker.yml`

## Orchestrator 안정성 개선 (#59, #60, #61)

- **Issue**: /dev-orchestrator 실행 시 3가지 문제 발생. (1) headless 프로세스 상태를 트래킹할 수 없음 (#59), (2) pipeline 내부 review/resolve 서브프로세스가 orchestrator가 지정한 모델이 아닌 CLI 기본 모델로 실행됨 (#60), (3) dispatch + state 기록이 분리되어 tool call 에러 시 orphan 프로세스 발생 (#61).
- **Changes**:
  - `agent-tracker.sh`: `render_orchestrator()` 추가 - `batch.state.json` 자동 감지, dispatched 이슈별 step/status/time/PR 표시, `ps aux` 기반 review/resolve 서브프로세스 `└─` 트리 표시, done/active/pending/blocked 카운트 footer, 다중 배치(client+server) 지원
  - `pipeline-helpers.sh`: `pipeline_run_headless()` 에 optional model 파라미터 추가, `${model:+--model "$model"}` 전달
  - `orchestrate-helpers.sh`: `orch_dispatch()` atomic화 - 프로세스 launch + state 기록을 단일 함수로 통합, state 기록 실패 시 orphan kill. `orch_record_dispatch()` 제거. dispatch prompt에 model 정보 포함. retryCount 파라미터 추가로 retry 시 double state write 제거.
  - `SKILL.md` (orchestrator): Step 4+5를 "Enter poll cycle" 단일 단계로 통합, 수동 dispatch 금지 명시
  - `SKILL.md` (pipeline): review/resolve 호출에 `$MODEL` 전달 예시 추가
  - `process-lifecycle.md`: model 파라미터 시그니처 + state schema 업데이트
  - `README.md` (agent-tracker): orchestrator section 문서 추가
- **Review**: /simplify - jq 2회 호출을 1회로 통합, `date +%s` 루프 외 캐싱, PID null guard 추가, retryCount 파라미터로 double state write 제거
- **Files**: `agent-tracker.sh`, `agent-tracker/README.md`, `orchestrate-helpers.sh`, `pipeline-helpers.sh`, `SKILL.md` (orchestrator/pipeline), `process-lifecycle.md`

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
