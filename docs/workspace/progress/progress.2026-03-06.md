# 2026-03-06 Workspace progress

## Pipeline tmux pane resilience 개선 (PR #46)

- **Issue**: Pipeline 오케스트레이터가 review pane을 3-4개 생성하는 orphan pane 증식 문제
- **Root cause**: `pipeline_open_pane_verified`의 내부 retry가 pane 2개 생성 + 오케스트레이터의 output capture 실패로 3회 재호출 = 3-6개 orphan pane
- **Changes**:
  - `pipeline_open_pane_verified` 내부 retry 제거, single attempt only
  - `remain-on-exit` + `#{pane_dead}` flag 기반 startup 검증 (기존 `pipeline_pane_alive`는 remain-on-exit 상태에서 dead pane도 true 반환)
  - `pipeline_open_pane_with_retry` state 기반 retry wrapper 추가 (세션 크래시 후에도 retry 횟수 유지)
  - Atomic state write (`mktemp` + `mv`) - 크래시 시 half-written JSON 방지
  - `pipeline_state_update`에 jq guard + auto `updatedAt` + `(now | todate)` 연산자 우선순위 수정
  - `pipeline_pane_alive_verified` - recovery entry point 전용 (tmux ID 재사용 방지)
  - `pipeline_pane_alive` - polling 전용 (child process가 `#{pane_current_command}` 변경 시 false PANE_DEAD 방지)
  - 3-layer pane protocol (pre-defense + execution + post-diagnosis) 문서화
  - PANE_DEAD 시 retry counter reset 제거 (무한 루프 방지)
  - SKILL.md에 self-recovery entry point 통합 (각 step이 진입 시 자체 검증)
- **Review**: Codex 2회, Claude Opus 2회, RAPHL self-fix 5 iteration
- **Files**: `pipeline-helpers.sh`, `SKILL.md`, `pane-lifecycle.md`, `recovery.md`

## Orchestrator pipeline 완료 감지 - state file 부재 기반 (#48, PR #49)

- **Issue**: orchestrator signal file(issue-N.exit)을 pipeline AI가 쓰지 않아 완료 감지 실패. PR search fallback도 body 형식 불일치 시 실패.
- **Solution**: pipeline Step 7이 state file을 삭제하는 점을 활용. `orch_check_completion()`에 state file 부재 감지 추가.
- **Design decisions**:
  - Hook 기반 접근(Stop hook) 검토 후 폐기 - pipeline AI가 Claude Code를 종료하지 않아 발동 안됨, tmux pane 매칭은 동적 환경에서 취약
  - `pipelineStarted` 플래그로 "아직 미생성" vs "Step 7 삭제" 구분 - 이전 state file 기반 감지의 false failure 재발 방지
  - pipeline-helpers.sh 수정 없음 - 스킬 간 결합 방지
- **Changes**:
  - `orch_check_completion()`: 4단계 감지 (signal file → pane command + state file → state file(AI 종료) → PR fallback)
  - `orch_record_dispatch()`: `pipelineStarted: false` 추가
  - stall retry 시 `pipelineStarted` false 리셋
  - `orch_state_update` 호출에 `|| true` guard ("always returns 0" 계약 보호)
  - `state-detection.md` 갱신
- **Bug review**: 3회 반복 검증 - retry 미리셋(HIGH), set-e 위반(MED), docs 불일치(MED) 발견 및 수정
- **Files**: `orchestrate-helpers.sh`, `state-detection.md`

## Orchestrator pane release 누락 + agent model/pane flexibility (#53, PR #54)

- **Issue**: `claude --dangerously-skip-permissions`가 pipeline 완료 후 interactive 모드에 머물러 pane 점유 지속. `orch_find_idle_panes`가 shell(bash/zsh)만 idle로 판단하므로 후속 dispatch 불가.
- **Root cause**: `orch_poll_cycle`이 완료 감지 후 AI 프로세스를 종료하지 않음. `-p`(print) 모드는 pipeline의 `AskUserQuestion` 호출과 비호환.
- **Changes**:
  - C-1: `orch_release_pane()` - 완료/실패 후 Ctrl+C로 AI 프로세스 종료 (pane 파괴 안 함). 2회 retry 포함.
  - C-2: `_orch_parse_agent()` - `"claude:sonnet"` 형식 파싱, `orch_dispatch()`에 `--model` flag 조건부 추가
  - C-3: `ORCH_WORK_PANES` env var - 명시적 pane ID 지정 모드. 기존 window-based discovery는 default 유지.
  - `orch_poll_cycle` step 1/2에서 pane_id 추출 후 `orch_release_pane` 호출
- **Side effect analysis**: completion detection 4단계 통과 필수이므로 false positive 리스크 극히 낮음. shell injection은 agent 값이 내부 입력이라 실질적 위험 없음.
- **Files**: `orchestrate-helpers.sh` (+91 -24), `SKILL.md`, `state-detection.md`

## agent-tracker 동적 pane 감지 실패 수정 (#47, PR #50)

- **Issue**: 다른 pane에서 Claude Code를 동적 시작 시 tokens=0, status=idle 고정
- **Root cause**: AGENT_TYPE_CACHE의 negative cache가 `return 0` 반환 (호출자가 성공으로 판단) + 캐시 무효화 없음
- **Changes**:
  - AGENT_TYPE_CACHE 완전 제거 - 매 사이클 재감지 (비용 무시 가능)
  - PostToolUse에서 needs-input → working 상태 복구
  - `AGENT_TRACKER_PANE` env var로 on-statusline.sh pane ID 안정화
  - `updated_at` 기반 staleness 감지 (30초 초과 시 idle 전환)
  - sidecar 디렉토리 `chmod 700` 일관 적용 (3곳)
  - `make_line`/`token_bar` 변수 `i` local 선언
  - `TRANSCRIPT_LAST_MSG` single-pass 복원 (context-bar.sh 소비 확인)
- **Review**: 5단계 심층 검토 2회 실행 - TRANSCRIPT_LAST_MSG 삭제 회귀 발견 및 복원
- **Files**: `agent-tracker.sh`, `on-status.sh`, `on-statusline.sh`, `statusline-wrapper.sh`
- **Findings**: [findings.012](../findings/findings.012-agent-tracker-detection-failures.md)
