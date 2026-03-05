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
