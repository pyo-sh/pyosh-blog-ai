# Progress: 2026-03-01

## Completed
- [x] Docker 컨테이너 타임존 UTC 고정 버그 수정
  - `docker-compose.yaml`: `TZ=${TZ:-}` → `TZ=${TZ:-Asia/Seoul}` 기본값 설정
  - `entrypoint.sh`: 데드 브랜치 제거 + zoneinfo 파일 존재 검증 추가
  - `ARCHITECTURE.md`: TZ 설명에 `.env` 오버라이드 안내 추가

## Discoveries
- Ubuntu 24.04 base image는 `/etc/localtime`이 UTC로 항상 존재하여 `[ ! -f /etc/localtime ]` 조건이 데드 브랜치가 됨
- Docker 컨테이너에서 호스트 TZ 자동 감지는 volume mount 또는 호스트 스크립트 의존이 불가피 → 단순한 `.env` + 기본값 방식 채택

## Issues & Resolutions
- **Issue**: entrypoint.sh의 elif 분기가 Ubuntu에서 항상 false
- **Resolution**: 조건 분기 단순화 — docker-compose.yaml에서 TZ 기본값 보장, entrypoint.sh는 적용만 담당

---

## Completed (2)
- [x] `scripts/agent-tracker.sh` 구현 (#7)
  - tmux `lab` 세션의 Claude Code / Codex 에이전트를 실시간 대시보드로 표시
  - 박스 드로잉 프레임(╔═╗║╚═╝), 컬럼 순서: PANE → TASK → ENGINE → STATUS → TOKENS
  - 상태 인디케이터: `● work` / `○ idle` / `◑ plan` / `✖ err`
  - 토큰 바: `▰▰▰▱▱` + 퍼센트 (Claude=blue, Codex=cyan)
  - Pipeline footer: `.workspace/pipeline/issue-*.state.json` 읽어 활성 파이프라인 표시
  - 2초 주기 갱신, alternate screen buffer (깜빡임 방지), Ctrl+C 종료 복원
  - `-s SESSION`, `-i INTERVAL` 옵션 지원

## Discoveries (2)
- Claude Code 상태 판별: `tmux capture-pane` 하단 8줄에서 spinner(✻, ⠋…) → working, `⏸` → plan, `❯` → idle 순으로 매칭
- Codex 데이터: `~/.codex/sessions/*/*/*-*.jsonl` 중 최신 파일을 jq로 파싱 (`turn_context`, `token_count`, `user_message` 이벤트)

---

## Completed (3)
- [x] PR #8 리뷰 코멘트 수정 — `scripts/agent-tracker.sh`
  - **[WARNING] PIPELINE_DIR 하드코딩**: `git rev-parse --show-toplevel` 기반으로 리포 루트 자동 감지 + `$PIPELINE_DIR` 환경변수 오버라이드 지원
  - **[WARNING] `grep -P` 이식성**: 모든 `grep -P`를 `grep -E` / `grep -oE | sed` 로 교체 — lookbehind/lookahead 패턴은 `grep -o + sed` 로 대체
  - **[WARNING] Codex 세션 전역 최신 파일**: `find_codex_session_file()` 함수 추가 — 패인 PID → 프로세스 트리 → `/proc/{pid}/fd` (Linux) → lsof 폴백 순으로 패인별 세션 JSONL 특정
  - **[SUGGESTION] INTERVAL 검증**: 인자 파싱 후 정규식 + awk로 양수 여부 검증, 잘못된 값 시 즉시 에러 종료

## Discoveries (3)
- `grep -P` lookbehind `(?<=💬 )` → `grep -o '💬 .*' | sed 's/.*💬 //'` 패턴으로 POSIX 호환 대체
- `grep -P` lookahead `[0-9]+(?=% of...)` → `grep -oE '...' | sed 's/%.*//'` 파이프라인으로 대체
- Linux `/proc/{pid}/fd` 심링크 스캔이 `lsof` 없이도 열린 파일 특정 가능 — 빠르고 의존성 없음

---

## Completed (4)
- [x] PR #8 머지 완료 — Issue #7 종료 (3 round 리뷰 통과)
  - `tools/tmux/session.docker.yml`: `tracker` window 추가
    - `layout: even-horizontal` (좌우 2 panes)
    - 왼쪽 pane: `bash scripts/agent-tracker.sh` 자동 실행
    - 오른쪽 pane: 빈 pane (자유 사용)
  - `tools/ARCHITECTURE.md`: tmux lab 세션 window 5 설명 추가
  - squash merge → `pyo-sh/pyosh-blog-ai#8`

---

## Completed (5)
- [x] agent-tracker 컬럼 정렬 수정 + transcript 기반 Task/Token 갱신 (#9, #10, PR #11)

  **Issue #9 — 컬럼 정렬 버그 3건 수정:**
  - `W_TOKENS` 9→10: `122k` 형태 토큰 수량 표시 공간 확보
  - `col_pane`: `pad_right`→`trunc` — PANE 컬럼 overflow 방지
  - `col_engine`: `printf "%-*s"` → `trunc` — 긴 Codex 모델명(예: `codex-mini-latest`) 절삭
  - STATUS badge 뒤 패딩 3칸→1칸 — `%b   ` 3-space 버그 수정
  - TOKENS 표시: `%2d%%`→`%3dk` — pct=100 overflow 수정 + 실제 수량(k) 표시

  **Issue #10 — transcript 직접 읽기로 Task/Token 갱신 신뢰성 개선:**
  - `find_claude_transcript()`: pane cwd를 `~/.claude/projects/{dir}` 경로로 변환, 최신 JSONL 반환
  - `parse_claude_pane()`: transcript에서 `input_tokens + cache_*` 합산 → `tok_k`; `map()|last//""` 방식으로 마지막 user 메시지 추출 (null-safe)
  - `parse_codex_pane()`: `tok_k` 필드 추가 (`total_tok / 1000`)
  - `render_dashboard()`: `model|status|pct|tok_k|task` 5-필드 파싱 반영
  - tok_k > 999 시 `"999+"` 표시로 W_TOKENS=10 overflow 방지

  Codex 2라운드 리뷰 통과 (round 1: WARNING×2 → round 2: CLEAN)

## Discoveries (5)
- Claude Code는 transcript JSONL FD를 열어두지 않음 → `/proc/PID/fd` 방식으로 파일 특정 불가
  - 해결책: pane cwd를 읽어 `pane_cwd//\\//-` 변환 → `~/.claude/projects/{dir}/*.jsonl` 최신 파일 선택
  - 참고: findings 007 (`findings/findings.007-claude-transcript-jsonl.md`)
- `printf "%-*s"` 는 padding만 하고 truncate 없음 → 모델명 overflow의 실제 원인
  - 기존 `trunc()` 함수 활용으로 padding+truncation 동시 처리

---

## Completed (6)
- [x] agent-tracker 다중 에이전트 트래킹 오류 및 대시보드 개선 (#12, PR 진행 중)

  **Issue #12 — 5가지 버그 수정 + 개선:**

  **1. Transcript 매핑 (Task/Token 공유 버그):**
  - `find_claude_transcript()` 전체 교체: TTY → Claude PID → `/proc/PID/fd` 스캔
  - `tasks/{UUID}` fd (flock 유지) 또는 `projects/{dir}/{UUID}` 서브디렉토리 패턴으로 session UUID 추출
  - 동일 CWD에서 여러 Claude 인스턴스가 각자의 transcript를 정확히 참조

  **2. CJK display width (trunc 깨짐):**
  - `display_width()` 함수 추가: `printf '%s' "$s" | wc -L` (GNU coreutils, CJK=2칸)
  - `trunc()` 교체: binary search로 `w-1` 이하의 display width prefix 탐색 후 `…` 접미

  **3. Engine 모델명 (Claude 폴백 버그):**
  - pane 스크래핑 제거 → transcript `message.model` 필드에서 추출
  - `claude-opus-4-6` → `Opus 4.6` 변환 (date-suffix IDs 포함: `claude-haiku-4-5-20251001`)
  - model/token/task를 **단일 jq 호출**로 통합 (RS `\u001e` 구분자로 `|` 충돌 방지)
  - 기존 2회 jq: ~150ms/pane → 1회: ~35ms/pane (성능 ~4× 향상)

  **4. Status 감지 오류 (spinner 80% miss):**
  - Claude Code 스피너 문자 추가: `✢|✶|✻|✽` (기존 `✻`만 → 4개)
  - `·` (middle dot) 제외: context bar separator와 false positive 방지

  **5. 반응형 레이아웃 + 1초 refresh:**
  - PANE/ENGINE/STATUS 고정, TASK fill, TOKENS min(=10)+grow 동적 계산
  - W_TOKENS = max(min, max over rows of bar(5)+sp(1)+str_len)
  - W_TASK = INNER - fixed_cols - 8 (trailing 2sp는 -8에 흡수)
  - `INTERVAL=2` → `INTERVAL=1`

## Discoveries (6)
- Claude Code는 `tasks/{UUID}` 디렉토리를 flock으로 session 동안 열어둠 → `/proc/PID/fd` 스캔으로 session UUID 추출 가능
  - `tasks/{UUID}/.lock` 또는 `tasks/{UUID}` 디렉토리 자체의 fd가 노출됨
  - 이전 발견(findings 007)과 달리 JSONL FD가 아닌 tasks/ FD를 활용
- `wc -L`(GNU coreutils)이 CJK double-width를 정확히 계산 → bash 순수 `${#s}` 대비 terminal columns 정확히 반영
- Claude Code spinner: `✢ · ✶ ✻ ✽` (5개). `·`은 context bar separator와 혼재 → false positive 위험
- `jq -rs` 단일 호출로 model+tokens+task 통합 시 RS(0x1e) 구분자 사용이 안전 (`|` 등 special char 포함 task 대응)
- W_TOKENS 공식에서 trailing 2sp는 -8 overhead에 흡수: `W_TOKENS` = bar+sp+str_len (trailing 제외), `-8` = left(2)+4seps(4)+right(2)

---

## Completed (7)
- [x] PR #13 리뷰 코멘트 수정 — `scripts/agent-tracker.sh` (#12)

  **[WARNING] `parse_claude_pane()` 멀티라인 task 잘림 버그:**
  - `IFS=$'\x1e' read -r raw_model ctx_len task_raw <<< "$raw_data"` 에서
    `<<<` here-string이 첫 번째 내장 개행 문자에서 멈춰 multi-line 사용자 메시지가 잘림
  - **Fix**: jq에서 task 필드를 `@base64`로 인코딩 → read 이후 `base64 -d` 복원
    - `"\($m)\u001e\($ctx)\u001e\($task | @base64)"` → IFS split 중 개행 영향 없음
    - 복원 후 기존 `${task_raw//$'\n'/ }` 정규화(개행→공백)가 그대로 동작
  - RS(0x1e) 구분자 유지 — model/ctx_len 필드는 개행 없으므로 변경 불필요

## Discoveries (7)
- bash `<<<` here-string은 변수 내 첫 번째 `\n`에서 멈춤 → field separator가 `\x1e`여도 task 내 개행이 read를 조기 종료시킴
- jq `@base64` 필터는 출력에 개행 없는 단일 라인 문자열 반환 → bash read와 완전 호환
- `base64 -d <<< "$b64"` 역시 안전: 입력이 base64(개행 없음)이므로 here-string 잘림 위험 없음
