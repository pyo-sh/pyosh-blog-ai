# Orchestrator dispatch 버그 3종 분석 및 수정

## Metadata
- **Date**: 2026-03-05
- **Related Issue**: PR #44

## Problem

dev-orchestrator 실행 중 3가지 독립적 버그 발생:

1. poll-loop.sh가 첫 cycle에서 즉시 크래시
2. client1 window의 sub-pane에 의도하지 않은 AI dispatch
3. DAG에 외부(closed) issue가 포함되면 영구 blocked

## Research

### Bug 1: `set -e` + `return 1` 충돌

poll-loop.sh에 `set -euo pipefail` 적용 시, `orch_check_completion`이 "running" 상태에서 `return 1`을 함. `result=$(orch_check_completion ...)` 형태로 호출하면 command substitution이 exit code 1을 전파하고, `set -e`가 스크립트를 즉시 종료.

같은 패턴이 `orch_detect_stall`에도 존재 (active = `return 1`).

### Bug 2: sub-pane 과잉 dispatch

`orch_find_idle_panes`가 work window 내 모든 idle pane을 반환 (예: client1에 %4, %16, %17, %18). `orch_poll_cycle`에 동시성 제한이 없어서 idle pane 수만큼 dispatch. 사용자가 "2개만" 지시했으나 4개까지 dispatch됨.

### Bug 3: 외부 dep 영구 차단

`parse-dependencies.sh`가 issue body에서 모든 dep 번호를 반환 (예: closed #38). DAG에 `{"41": [38]}`이 들어가면 #38이 batch status에 없어 `orch_unblock`에서 `dep_status = "null"` → 영원히 blocked.

## Decision

### set -e 안전성
- `orch_check_completion`, `orch_detect_stall`: 항상 `return 0`, stdout으로만 상태 전달
- caller 변경: `orch_detect_stall` 호출부를 `if [ "$(orch_detect_stall ...)" = "stalled" ]` 패턴으로 교체

### sub-pane 필터
- `orch_find_idle_panes`: window당 첫 번째 pane만 반환 (`head -1`, `pane-base-index` 무관)
- `orch_init`에 `maxConcurrent` 파라미터 추가, `orch_poll_cycle` dispatch 단계에서 슬롯 제한 적용

### 외부 dep 필터
- `orch_init` 내부에서 DAG 자동 필터링: batch issues에 없는 dep 번호를 jq로 제거
- AI가 수동 필터하지 않아도 안전

### 추가 수정
- `orch_poll_cycle` dispatch 후 `orch_verify_startup` 호출 (5초 grace) - 실패 시 즉시 pending 복귀
- `recovery.md` batch completion jq 표현식 수정 (기존 표현식은 context 전환으로 동작 불가)

## References
- `orchestrate-helpers.sh` - 전체 수정
- `references/recovery.md` - jq 수정
