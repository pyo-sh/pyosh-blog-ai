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

## agent-tracker 프로세스 감지 단순화 + orchestrator liveness 수정 (#68)

- **Issue**: orchestrator 배치 테이블이 agent-tracker에서 렌더링되지 않음. 원인은 `_find_claude_pid`의 BFS `/proc` 탐색이 Claude Code 바이너리 exe name `2.1.71`(버전 번호)을 인식 못함. `_match_agent`가 `exe == "claude"` 또는 `cmdline =~ claude-code/cli`만 체크 - 둘 다 불일치. tmux `#{pane_current_command}`는 정상적으로 `"claude"`를 반환하지만 orchestrator liveness는 이 fast path를 사용하지 않고 별도의 BFS 경로를 타서 실패.
- **Changes**:
  - `/proc` BFS 프로세스 감지 5개 함수 삭제 (`_get_cmdline`, `_get_exe_name`, `_match_agent`, `detect_agent_type`, `_find_claude_pid`) - 80줄 제거
  - 에이전트 감지: tmux `#{pane_tty}` + `ps -t` 6줄로 대체
  - orchestrator liveness: `orchestratorPid` 직접 저장 + `kill -0` 체크. pane 경유 BFS 탐색 제거
  - 컬럼 폭 계산 3-pass -> 1-pass (데이터 수집 시 동시 계산)
  - on-status.sh 도구 디스패치: 17-branch if-elif -> jq object lookup 테이블
  - 순감소 -66줄 (899 -> 816)
- **Findings**: [findings.015](../findings/findings.015-agent-tracker-overengineering.md)
- **Files**: `agent-tracker.sh`, `on-status.sh`, `orchestrate-helpers.sh`

## agent-tracker 구조적 데이터 경계 및 신뢰성 전면 개편 (#72)

- **Issue**: orchestrator 배치 테이블이 렌더링되지 않는 문제가 #64, #66, #68에서 3회 이상 수정 시도되었으나 근본 원인 미해결. 원인은 jq가 12개 필드를 `\x1f`로 join한 뒤 `read -r meta dispatched_data` (2개 변수)로 분리 - `meta`에 area만 들어가고 `orch_pid` 포함 나머지 필드는 항상 빈 값.
- **Changes**:
  - 모놀리식 `agent-tracker.sh` (810줄)를 `lib/` 3-layer로 분리: `util.sh` (렌더링 헬퍼), `collect.sh` (데이터 수집), `render.sh` (대시보드 렌더링)
  - `\x1f`/`\x1e`/newline 구분자 프로토콜을 JSON snapshot + `@tsv` 기반으로 전면 교체
  - orchestrator 메타데이터: 단일 `IFS=\t read -r` 로 11개 필드 직접 추출 (중간 `meta` 변수 제거)
  - dispatched 이슈: 별도 jq 호출로 분리 - status가 `dispatched`인 항목만 필터
  - exit code 보존: `cleanup()` 에서 `exit 0` -> `local ec=$?; exit "$ec"`
  - sidecar cleanup 안전성: `tmux has-session` 가드 추가 (비존재 세션에서 orphan 삭제 방지)
  - 토큰 계산: 200k 하드코딩 -> 실제 window size 추출 (`[0-9]+% of [0-9]+k tokens`)
  - Codex JSONL 파싱: mtime 캐시로 변경 없는 파일 재파싱 스킵 + 멀티라인 메시지 `gsub` 정규화
  - `unknown` status badge 추가
  - 66개 fixture 테스트 추가 (orchestrator/claude-parse/codex-parse/exit-code/sidecar-cleanup/token-fallback)
- **Files**: `agent-tracker.sh` (rewrite), `lib/util.sh`, `lib/collect.sh`, `lib/render.sh`, `tests/` (helpers.sh, run-tests.sh, test-*.sh 6개)

## Shell script cleanup - stale code 삭제 및 과도한 복잡성 제거 (#70)

- **Issue**: #68 후속. 전체 sh 파일 검사에서 동일 패턴의 과도한 복잡성 잔존 확인.
- **Changes**:
  - `scripts/agent-tracker.sh` (648줄) 삭제 - `tools/agent-tracker/agent-tracker.sh`로 대체된 구버전
  - Codex `find_codex_session_file` BFS 프로세스 트리 탐색을 tty 기반 PID lookup으로 교체
  - `orchestrate-helpers.sh` macOS `date -j` dead code 제거 + 빈 `last_ts` 가드 추가 (false stall 방지)
  - `statusline-wrapper.sh` ↔ `context-bar.sh` 중복 jq 로직에 grep 가능한 SYNC 마커 추가
  - Codex pane tty 중복 호출 제거 (optional 파라미터 전달)
  - 순감소 -649줄
- **Files**: `scripts/agent-tracker.sh` (삭제), `agent-tracker.sh`, `statusline-wrapper.sh`, `context-bar.sh`, `orchestrate-helpers.sh`
