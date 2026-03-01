# Claude Code Transcript JSONL 접근 방법

## Metadata
- **Date**: 2026-03-01
- **Related Issue**: #10

## Problem

`agent-tracker.sh`에서 Claude Code pane의 Token 사용량과 마지막 Task를 읽어야 했으나,
Codex와 달리 Claude Code는 transcript JSONL 파일을 FD로 열어두지 않아
`/proc/PID/fd` 스캔으로 파일을 특정할 수 없었다.

## Research

### Option A: pane 스크래핑 (기존 방식)

`tmux capture-pane`으로 화면 텍스트 grep:
- `[0-9]+% of [0-9]+k tokens` → token %
- `💬 .*` → last user message (context-bar.sh hook 출력)

**Pros**: 설정 없이 동작
**Cons**:
- Claude TUI alternate screen 재렌더링 시 status bar 가려짐
- AI 스트리밍 중 capture 타이밍에 텍스트 부재
- context-bar.sh 미설정 시 완전 무동작
- token %만 얻을 수 있어 실제 수량 계산 필요

### Option B: `/proc/PID/fd` FD 스캔 (Codex 방식)

Codex CLI는 세션 JSONL을 열어두므로 pane PID → 프로세스 트리 → FD 스캔으로 파일 특정 가능.
Claude Code에서는 transcript FD를 열어두지 않아 이 방식으로 파일을 찾을 수 없다.

### Option C: cwd → project dir 매핑 (채택)

Claude Code transcript 경로 규칙:
```
~/.claude/projects/{cwd_with_slashes_replaced_by_dashes}/*.jsonl
```

예: pane cwd = `/workspace` → `~/.claude/projects/-workspace/*.jsonl`

pane cwd는 `tmux display-message -t {pane_id} -p '#{pane_current_path}'`로 얻을 수 있다.
최신 JSONL 파일은 `ls -t ... | head -1`로 선택.

**Pros**:
- FD 의존 없이 안정적으로 파일 특정
- 성능: 880KB JSONL → jq 8ms (2초 갱신 주기에 충분)
- pane scraping fallback 유지로 context-bar.sh 없어도 부분 동작

**Cons**:
- 동일 cwd에서 여러 Claude 세션 실행 시 가장 최신 파일만 읽음 (실용상 문제없음)

## Decision

**Option C 채택**: cwd → project dir 매핑으로 최신 JSONL 직접 읽기.

### jq 쿼리 (context-bar.sh와 동일한 로직)

**Token 사용량:**
```bash
ctx_len=$(jq -s '
  map(select(.message.usage and .isSidechain != true and .isApiErrorMessage != true)) |
  last |
  if . then
    (.message.usage.input_tokens // 0) +
    (.message.usage.cache_read_input_tokens // 0) +
    (.message.usage.cache_creation_input_tokens // 0)
  else 0 end
' < "$transcript")
```

**마지막 user 메시지 (null-safe):**
```bash
last_msg=$(jq -rs '
  [.[] | select(.type == "user") |
   select(.message.content | type == "string" or
          (type == "array" and any(.[]; .type == "text")))] |
  map(.message.content |
      if type == "string" then .
      else [.[] | select(.type == "text") | .text] | join(" ") end |
      gsub("\n"; " ") | gsub("  +"; " ")) |
  last // ""
' < "$transcript")
```

`map()` 안에서 먼저 string 변환 후 `last // ""`를 적용해야 null-safe.
`last` 이후 `.message.content` 접근하면 빈 배열에서 null 오류 발생.

### user message content 형식

실측 결과 (880KB JSONL, 53 user messages):
- `string` 타입: 14개 (직접 텍스트 입력)
- `array` 타입: 39개 (대부분 tool_result — text 필터 필수)

`any(.[]; .type == "text")` 조건으로 text block이 하나라도 있는 array만 통과시킨다.

## Implementation Guide

```bash
find_claude_transcript() {
  local pane_id="$1"
  local pane_cwd project_dir

  pane_cwd=$(tmux display-message -t "$pane_id" -p '#{pane_current_path}' 2>/dev/null)
  [[ -z "$pane_cwd" ]] && return

  # /workspace → -workspace  (Claude project dir naming convention)
  project_dir="${pane_cwd//\//-}"
  ls -t "${HOME}/.claude/projects/$project_dir"/*.jsonl 2>/dev/null | head -1
}
```

## References
- `scripts/agent-tracker.sh` — `find_claude_transcript()`, `parse_claude_pane()`
- `scripts/context-bar.sh` — 동일 jq 쿼리 참조
- `docs/workspace/findings/findings.004-claude-code-vs-codex-hooks.md` — Claude vs Codex 비교
