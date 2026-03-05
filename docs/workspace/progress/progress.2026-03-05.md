# Progress: 2026-03-05

## Completed
- [x] Orchestrator dispatch 버그 3종 수정 (PR #44)
  - `set -e` 안전성: `orch_check_completion`, `orch_detect_stall` 항상 return 0
  - sub-pane 필터: `orch_find_idle_panes` window당 main pane만 반환 (`head -1`)
  - `maxConcurrent` 제한: `orch_init` 파라미터 + `orch_poll_cycle` 슬롯 체크
  - `pane-base-index` 방어: `head -1` 방식으로 tmux 설정 무관
- [x] Orchestrator 구조적 약점 3종 수정 (PR #44 추가 커밋)
  - DAG 외부 dep 자동 필터링: `orch_init`에서 batch issues에 없는 dep 제거
  - dispatch 시작 검증: `orch_verify_startup` 통합, 실패 시 즉시 pending 복귀
  - `recovery.md` batch completion jq 표현식 수정

## Discoveries
- `set -euo pipefail`과 shell function의 `return 1`은 command substitution `$(...)` 안에서 전파됨
- tmux `pane-base-index` 설정이 0이 아니면 `pane_index == 0` 필터가 실패
- `orch_unblock`에서 batch에 없는 dep의 status가 `"null"`이 되어 영구 blocked

## Notes
- Related findings: `findings/findings.010-orchestrator-dispatch-bugs.md`
