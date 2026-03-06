# Orchestrator pane release 누락 - interactive mode 잔류

> 날짜: 2026-03-06 | 태그: #orchestrator #pane #release #tmux #claude-code

## 현상

Orchestrator가 2개 이슈(#23, #31) 완료 후 후속 dispatch를 하지 않음. `orch_find_idle_panes`가 빈 목록 반환.

## 원인 분석

`claude --dangerously-skip-permissions 'prompt'`는 작업 완료 후에도 interactive 세션에 머무름. `orch_find_idle_panes`는 `#{pane_current_command}`가 bash/zsh/sh/fish인 pane만 idle로 판단하므로, claude 프로세스가 점유한 pane은 영구적으로 사용 불가.

### 왜 `-p`(print) 모드를 사용하지 않는가

`-p` 모드는 작업 완료 후 자동 종료되지만, pipeline의 Step 4b/5/6에서 `AskUserQuestion`을 호출함. `-p` 모드에서는 stdin이 없어 user interaction이 불가능.

### 왜 prompt에 "exit the session" 지시만으로는 부족한가

AI가 지시를 따를 수도 있지만, 보장되지 않음. 실제로 pipeline 완료 후에도 세션에 머무르는 것이 관찰됨. 반드시 fallback 메커니즘 필요.

## 해결

2계층 접근:

1. **Primary**: dispatch prompt에 `"After completing all steps, exit the session."` 포함 - AI가 자연스럽게 종료
2. **Fallback**: `orch_release_pane()` - 완료/실패 감지 후 Ctrl+C 전송 (최대 2회)

`orch_release_pane`은 pane을 파괴하지 않음 (`pipeline_kill_pane`과 차이). Shell prompt로 복귀시켜 다음 dispatch에 재사용.

## 안전성

- Ctrl+C는 `orch_check_completion`이 `completed`/`failed` 반환 후에만 실행
- completion detection은 4단계 검증 (signal file → pane command + state file → state file(AI 종료) → PR status)
- AI 프로세스가 아닌 경우 (이미 shell) early return
- 실패 시 다음 poll cycle의 stall detection이 커버

## 관련

- PR #54 (fix/orchestrator-pane-release)
- Issue #53
- [state-detection.md](../../../.agents/skills/dev-orchestrator/references/state-detection.md) - Pane Release 섹션
