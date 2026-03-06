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
