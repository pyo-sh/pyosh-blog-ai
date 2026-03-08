# 2026-03-08 Workspace progress

## agent-tracker 칸 밀림 근본 수정 + orchestrator pane 기반 렌더링 (#66)

- **Issue**: #64에서 칸 밀림을 `pad_right` -> `trunc` 교체로 수정했다고 했으나 근본 원인 미해결. (1) `pad_right`(`printf '%-*s'`)가 byte 기준 padding - UTF-8 multi-byte 문자(`└─` 8 bytes / 4 display cols)에서 padding 미적용, (2) orchestrator 렌더링이 `batch.state.json` 존재만으로 결정 - PID liveness는 스타일링에만 사용, (3) footer done/active/pending/blocked 카운트가 header done/total과 중복.
- **Changes**:
  - `pad_right`: `printf '%-*s'` -> `display_width`(wc -L) 기반 padding으로 교체. ASCII fast path 유지.
  - `render_orchestrator`: pane 기반 liveness - `orchestratorPane`에서 Claude Code PID 탐색 -> `/proc/PID/stat` field 22 starttime 비교. 불일치 시 섹션 전체 스킵. "stopped" 상태 제거.
  - `orch_init()`: `orchestratorPane` ($TMUX_PANE) 필드 기록 추가. `orchestratorPid` 제거.
  - `_find_claude_pid()`: pane의 process tree에서 Claude Code PID를 찾는 헬퍼 추가.
  - orchestrator footer: done/active/pending/blocked 카운트 -> `⏱ elapsed` + failed 카운트 + [DONE] 라벨.
  - header/footer gap 계산: `${#string}` -> `display_width` 일관 적용 (`⚙`, `●` 등 non-ASCII 문자).
- **Files**: `agent-tracker.sh`, `orchestrate-helpers.sh`
