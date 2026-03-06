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
