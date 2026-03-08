# Findings 015: agent-tracker 과도 설계 - `/proc` BFS가 tmux API보다 나쁜 이유

> **Date**: 2026-03-08
> **Tags**: #agent-tracker #proc #tmux #overengineering #process-detection
> **Issue**: #68

## 문제

orchestrator 배치 테이블이 agent-tracker 대시보드에서 렌더링되지 않음.

## 원인

`render_orchestrator`의 liveness 체크가 `_find_claude_pid` -> `_match_agent`를 사용. `_match_agent` 조건:

```bash
[[ "$exe" == "claude" ]] ||
[[ "$cmdline" =~ @anthropic-ai/claude-code|claude-code/cli ]]
```

실제 프로세스:
- exe: `/home/dev/.local/share/claude/versions/2.1.71` -> basename = `"2.1.71"` (not `"claude"`)
- cmdline: `"claude --dangerously-skip-permissions"` (not containing `claude-code/cli`)

두 조건 모두 실패 -> `_find_claude_pid` 실패 -> `|| continue`로 배치 섹션 전체 스킵.

## 같은 파일 내 모순

```bash
# 에이전트 행 감지 (fast path) - 정상 동작
case "$pane_cmd" in
  claude) etype="claude" ;;  # #{pane_current_command} = "claude"

# orchestrator liveness - 실패
_claude_pid=$(_find_claude_pid "$_pane_root")  # /proc BFS -> exe "2.1.71" -> 불일치
```

tmux가 이미 `"claude"`를 제공하는데, `/proc`에서 재탐색하면서 다른 결과를 얻음.

## 과도 설계 누적 경로

```
03-01 구현 -> 03-01 수정 4회 -> 03-02 push 아키텍처 (12라운드 리뷰)
-> 03-03 버그 2건 -> 03-04 토큰 수정 -> 03-06 pane 감지 실패
-> 03-07 UI 3건 + orchestrator -> 03-08 칸 밀림 -> 03-08 테이블 미렌더
```

8일간 15+ PR. 매번 "수정"이 새로운 복잡도를 추가하고, 그 복잡도가 다음 버그의 원인.

### AI 행동 패턴

1. **"만약에" 방어 코딩**: fast path가 99% 처리하는데, 나머지 1%를 위해 80줄 BFS 구현. 이 fallback 자체가 버그를 만듦
2. **기존 코드를 의심하지 않음**: 각 세션이 기존 코드를 "정답"으로 취급하고 그 위에 쌓음
3. **삭제보다 추가를 선호**: BFS가 문제면 제거하는 게 맞는데, 캐시 추가 -> 캐시 제거 -> 매 사이클 재감지 -> fast path 추가 순서로 진행
4. **저수준 API 선호**: tmux/ps가 제공하는 정보를 `/proc` readlink + cmdline 파싱으로 재구현

## 수정

| Before | After |
|--------|-------|
| `_find_claude_pid` BFS (80줄, 5함수) | `ps -t <tty> -o comm=` (6줄) |
| pane -> pane_pid -> BFS -> claude PID -> starttime | `kill -0 $stored_pid` + starttime |
| 3-pass 컬럼 폭 계산 | 1-pass (수집 시 계산) |
| 17-branch if-elif 도구 디스패치 | jq object lookup |

## 원칙

- **사용 가능한 가장 높은 수준의 API를 사용할 것**. tmux가 `#{pane_current_command}`, `#{pane_tty}`를 제공하면 `/proc`을 읽지 말 것
- **2단계 이상의 fallback 체인 금지**. 3번째 fallback부터는 문제를 가리는 것이지 해결하는 게 아님
- **버그 수정 시 "이 코드를 삭제할 수 있는가?"를 먼저 물을 것**. workaround 추가보다 원인 제거가 우선
