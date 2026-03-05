# Pipeline pane orphan 증식 원인과 해결

## Metadata
- **Date**: 2026-03-06
- **Related Issue**: PR #46

## Problem

Pipeline 오케스트레이터가 review pane을 열 때 3-4개의 orphan pane이 생성됨.

## Root cause

두 가지 독립적 결함의 복합 작용:

1. **`pipeline_open_pane_verified` 내부 retry**: 실패 시 내부에서 1회 재시도 → 호출당 최대 2개 pane 생성
2. **Orchestrator output capture 실패**: bash variable capture (`PANE=$(func)`) 방식이 간헐적으로 빈 문자열 반환 → orchestrator가 "실패"로 판단하고 재호출 (최대 3회)

결과: 2 pane/call × 3 calls = 최대 6개 orphan pane.

## Findings

### remain-on-exit와 pane_alive의 상호작용

`tmux set-option remain-on-exit on` 설정 시, 죽은 pane이 `list-panes`에 계속 표시됨. 따라서 `pipeline_pane_alive()` (list-panes 기반)가 dead pane에 대해 true를 반환.

해결: `#{pane_dead}` tmux format variable로 직접 확인:
```bash
is_dead=$(tmux display-message -t "$pane_id" -p '#{pane_dead}')
# "1" = dead, "0" or empty = alive
```

### pane_alive vs pane_alive_verified 분리

- `pipeline_pane_alive`: 기본 존재 확인. **polling 루프에서 사용**. child process (git, gh 등)가 `#{pane_current_command}`를 변경하므로 command 확인하면 false PANE_DEAD 발생.
- `pipeline_pane_alive_verified`: 존재 + `#{pane_current_command}`가 `claude|codex`인지 확인. **recovery entry point에서만 사용** (이전 세션의 stale pane ID가 tmux 재시작 후 재사용될 수 있으므로).

### jq 연산자 우선순위

```bash
# 잘못된 예: todate가 전체 object에 적용됨
.updatedAt = now | todate

# 올바른 예: 괄호로 우선순위 지정
.updatedAt = (now | todate)
```

`|`가 `=`보다 우선순위가 낮아서, `= now | todate`는 `(= now) | todate`로 파싱되어 전체 JSON object에 `todate`가 적용됨.

### State 기반 retry vs 자연어 retry 지시

"retry once" 같은 자연어 지시는 AI 오케스트레이터가 일관되게 따르지 않음. State JSON에 `reviewPaneRetries`, `maxPaneRetries` 필드를 두고 `pipeline_open_pane_with_retry`가 자동 관리하는 방식이 안정적.

PANE_DEAD 발생 시 retry counter를 reset하면 무한 루프 가능 - counter는 성공 시에만 reset.

## References
- [findings.003-tmux-pane-lifecycle.md](findings.003-tmux-pane-lifecycle.md) - 기존 pane lifecycle 패턴
- [pane-lifecycle.md](../../.agents/skills/dev-pipeline/references/pane-lifecycle.md) - 3-layer protocol 문서
