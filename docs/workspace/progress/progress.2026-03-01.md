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

## Completed (8)
- [x] PR #13 리뷰 라운드 2 — 도움말 텍스트 interval 수정 후 머지 (#12)

  **Codex 2라운드 리뷰 결과:**
  - [WARNING] `scripts/agent-tracker.sh:49` — 도움말 텍스트에 기본 interval이 `2`초로 표기되나 실제 `INTERVAL=1`로 변경됨
  - [SUGGESTION] 모델 ID 파싱 패턴이 `claude-{name}-{major}-{minor}` 형식만 처리

  **Fix (Claude Sonnet resolve):** `default: 2` → `default: 1` (1줄 변경)

  **Pipeline 완료:**
  - PR #13 squash merge (pyo-sh/pyosh-blog-ai#13)
  - 브랜치 `fix/issue-12-agent-tracker-improvements` 삭제
  - 워크트리 `.workspace/worktrees/issue-12` 제거
  - 이슈 #12 종료

## Discoveries (8)
- `pipeline-helpers.sh`의 `MONOREPO_ROOT`는 source 시점 CWD 기반 `git rev-parse --show-toplevel` 결과
  - 워크트리 내부에서 source하면 워크트리 경로(`/workspace/.workspace/worktrees/issue-12`)가 MONOREPO_ROOT로 설정됨
  - `WORKTREE_DIR` 계산이 꼬여 `pipeline_resolve_worktree_path`가 PATH_INVALID 반환 → PATH_INVALID 에러의 근본 원인
  - 대책: **반드시 monorepo root(`/workspace`)에서 `cd /workspace && source .agents/skills/dev-pipeline/scripts/pipeline-helpers.sh`**
- `pipeline_open_pane_verified` 첫 pane이 3s 내 죽어도 retry path(`WORKTREE_DIR/issue-12`)로 열면 성공하는 패턴 확인
  - 첫 pane workdir=`/workspace`로 열린 codex가 빠르게 실패, 재시도 workdir=worktree로 성공
  - 원인 미확정: tmux pane 분할 타이밍 또는 codex startup 경로 이슈 가능성

---

## Discoveries (7)
- bash `<<<` here-string은 변수 내 첫 번째 `\n`에서 멈춤 → field separator가 `\x1e`여도 task 내 개행이 read를 조기 종료시킴
- jq `@base64` 필터는 출력에 개행 없는 단일 라인 문자열 반환 → bash read와 완전 호환
- `base64 -d <<< "$b64"` 역시 안전: 입력이 base64(개행 없음)이므로 here-string 잘림 위험 없음

---

## Completed (9)
- [x] `/dev-orchestrator` 스킬 구현 (#14)

  **파일 구성:**
  - `SKILL.md` — 7단계 워크플로우: area 감지 → 이슈 필터 → DAG 구성 → 초기 dispatch → 폴링 사이클 → 완료 요약 → /dev-log
  - `scripts/orchestrate-helpers.sh` — 핵심 함수 구현:
    - `orch_init`: 초기 batch.state.json 생성 (pending/blocked 자동 분류)
    - `orch_find_idle_panes`: bash/zsh 쉘 프롬프트 대기 pane 탐지
    - `orch_dispatch`: idle pane에 `send-keys`로 `/dev-pipeline #{N}` 전송
    - `orch_check_completion`: signal 파일 → pipeline 상태 파일 → PR 머지 상태 순으로 완료 판별
    - `orch_detect_stall`: 10분 무변동 감지 + 최신 commit SHA 갱신 확인
    - `orch_unblock`: 완료 이슈를 의존하던 blocked 이슈들을 pending으로 전환
    - `orch_poll_cycle`: 단일 폴링 반복 (완료 체크 → stall 감지 → unblock → dispatch)
    - `orch_print_summary`: 배치 완료 후 issue/status/PR URL 표 출력
  - `scripts/parse-dependencies.sh` — 이슈 body `### Dependencies` 섹션 파싱:
    - `#N`, `Closes #N`, `Fixes #N`, `Resolves #N` 패턴 인식
    - `없음/none/N/A` 마커 처리
    - `--check-cycles` 모드: Kahn's algorithm(jq 구현)으로 DAG 사이클 감지
  - `references/dependency-resolution.md` — DAG 구성 및 사이클 감지 문서
  - `references/state-detection.md` — 완료/stall 감지 전략 문서
  - `references/recovery.md` — batch.state.json 기반 크래시 복구 문서
  - `.claude/skills/dev-orchestrator` → symlink

  **설계 결정:**
  - 완료 판별: signal 파일(`issue-N.exit`) > pipeline state 삭제 + PR 머지 상태 순서로 확인
  - 상태 머신: `pending → dispatched → completed/failed`, `blocked → pending`(의존성 해소 시)
  - failed 이슈도 downstream unblock 수행 (의존성 시도로 간주)
  - 자동 재시도 최대 1회 (`retryCount` 추적)

## Discoveries (9)
- `tmux list-panes -s -F '#{pane_id} #{pane_current_command}'`에서 bash/zsh process가 foreground인 pane = idle pane (자식 프로세스 없는 쉘)
- Kahn's algorithm을 jq 단독으로 구현 가능: `reduce` + in-degree 배열로 위상 정렬 + 방문 count로 사이클 판별

---

## Completed (10)
- [x] PR #15 리뷰 코멘트 수정 — `dev-orchestrator` 스킬 (#14)

  **[CRITICAL] `parse-dependencies.sh` — `--check-cycles` 모드 도달 불가:**
  - `$1`을 이슈 번호로 바로 할당 후 `gh issue view "$ISSUE"` 호출 → `--check-cycles` 전달 시 body 조회 실패로 `:29-31`에서 `exit 0` 조기 종료
  - **Fix**: `--check-cycles` 분기를 스크립트 최상단(`set -euo pipefail` 직후)으로 이동 → 이슈 파싱 로직 전에 처리

  **[CRITICAL] `orchestrate-helpers.sh:345` — `failed` 상태 시 downstream deadlock:**
  - `if [ "$result" = "completed" ]` 조건만 unblock 수행 → upstream이 `failed`일 때 dependent 이슈가 영구 `blocked` 상태 유지
  - **Fix**: `if [ "$result" = "completed" ] || [ "$result" = "failed" ]` — 두 종료 상태 모두 unblock 수행 (문서 상태 머신과 일치)

  **[WARNING] `parse-dependencies.sh:52` — `grep` 무매치 시 `set -euo pipefail` 강제 종료:**
  - `grep -oE '...'` 가 매칭 없으면 exit 1 반환 → `set -euo pipefail` 환경에서 "의존성 없음" 정상 케이스가 스크립트 실패로 처리됨
  - **Fix**: 추출 파이프라인 끝에 `|| true` 추가

  **[SUGGESTION] `SKILL.md:126` — `orch_poll_cycle` 호출 인자 불일치:**
  - 문서 예시: `orch_poll_cycle "$AREA_DIR" "$AGENT"` (2개) vs 실제 함수 시그니처: `<area> <area_dir> <agent> <orchestrator_pane>` (4개)
  - **Fix**: `orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT" "$ORCH_PANE"` 로 정정 + Unblock 설명에 `failed` 추가

## Discoveries (10)
- bash 스크립트에서 `--flag` 분기는 positional 인자 파싱 이전에 처리해야 함 — `$1`을 변수로 할당 후 체크하면 다른 로직이 먼저 `$1`을 소비할 수 있음
- `grep -oE | ... | sort | tr | sed` 파이프라인의 첫 `grep`이 무매칭 시 전체 파이프라인이 pipefail로 종료 → `|| true`를 파이프라인 끝에 배치해 빈 출력을 정상 케이스로 처리

---

## Completed (11)
- [x] PR #15 2차 리뷰 코멘트 수정 — `dev-orchestrator` 스킬 (#14)

  **[CRITICAL] `orchestrate-helpers.sh:305` — `orch_unblock()` 내부 dep_status 판별 미완:**
  - 1차 수정(Completed 10)은 `orch_poll_cycle`의 외부 조건(`if completed || failed → orch_unblock()` 호출)은 고쳤으나,
    `orch_unblock()` 내부 loop에서 잔여 dep가 "해소됐는지" 판별 시 `completed`만 허용
    (`if [ "$dep_status" != "completed" ]; then still_blocked=1`)
  - **재현 시나리오**: `dag[3]=[1,2]`, `status[1]=failed`, `status[2]=failed` → `#3`이 영구 `blocked`
  - **Fix**: `orchestrate-helpers.sh:305` — `completed` 단독 비교 → `completed` OR `failed` 허용
    ```bash
    if [ "$dep_status" != "completed" ] && [ "$dep_status" != "failed" ]; then
    ```
  - **SKILL.md:141** — `orch_unblock "$ISSUE"` (1개 인자) → `orch_unblock "$AREA" "$ISSUE"` (2개) 문서 정정

## Discoveries (11)
- `orch_poll_cycle`에서 `orch_unblock` 호출 자체는 `completed|failed` 양쪽에서 발생해도,
  `orch_unblock` 내부 remaining-deps 루프가 `completed`만 "통과"로 간주하면 여전히 deadlock 발생
  → 외부 트리거와 내부 판별을 동시에 수정해야 상태 머신이 올바르게 동작함

---

## Completed (12)
- [x] PR #15 3-4차 리뷰 코멘트 수정 — `dev-orchestrator` 스킬 (#14)

  **3차 리뷰 수정 (이전 커밋에서 처리):**
  - **[CRITICAL] `parse-dependencies.sh:33`** — 외부 의존성(batch 밖 이슈)을 사이클 엣지로 오판:
    `$issues` 목록에 없는 dep 노드가 indegree만 올리고 queue에 들어가지 못해 CYCLE_DETECTED 오보
    → jq `select(. as $d | $issues | any(. == $d))` 필터로 in-batch 엣지만 포함
  - **[CRITICAL] `orchestrate-helpers.sh:205`** — 방금 dispatch된 이슈를 pipeline state 파일 미생성 상태에서 `failed`로 오판:
    → 60초 grace window 추가 (`dispatchedAt` 기반 경과 시간 체크)
  - **[WARNING] `orchestrate-helpers.sh:329`** — terminal 이슈가 `.dispatched`에 남아 매 사이클 재체크:
    → terminal 상태 도달 시 `del(.dispatched["$issue"])` 로 즉시 제거

  **4차 리뷰 수정 (이번 커밋):**
  - **[CRITICAL] `parse-dependencies.sh:26`** — `DAG_JSON="${3:-{}}"` 파라미터 확장 버그:
    bash가 `:-` 뒤 첫 `}`를 확장 종료로 해석 → `$3` 제공 시 뒤에 `}` 추가됨 → jq 파싱 실패
    → 2줄 분리: `DAG_JSON="${3:-}"` + `[ -z "$DAG_JSON" ] && DAG_JSON='{}'`
  - **[CRITICAL] `orchestrate-helpers.sh:80`** — `orch_state_update` jq 연산자 우선순위 버그:
    `"$filter + {updatedAt: ...}"` 에서 `+`가 `=`보다 높은 우선순위 → `orch_status_set` 호출 시 string+object 타입 에러
    → `"($filter) | .updatedAt = ..."` 파이프 체이닝으로 교체
  - **[SUGGESTION] `parse-dependencies.sh:113`** — 의존성 키워드 대소문자 미구분:
    `grep -oE` → `grep -oiE` 로 변경 (`closes #12` 등 소문자 형식 허용)

---

## Completed (13)
- [x] PR #19 [CRITICAL] 리뷰 수정 — `scripts/agent-tracker.sh` Codex 감지 (#16)

  **[CRITICAL] `scripts/agent-tracker.sh:412` — `node)` 분기 Codex 감지 실패:**
  - 기존 구현: `pgrep -P "$_cpid"` → `readlink /proc/{}/exe` → `/codex$` 매칭
  - **근본 원인**: Codex CLI는 Node.js shebang 스크립트 (`#!/usr/bin/env node`)이므로
    프로세스 실행 파일이 `.../node`로 resolve됨 — `.../codex` 경로는 존재하지 않음
    → `/codex$` 패턴이 절대 매칭되지 않아 Codex 패인이 항상 필터링됨 (기본 버그 미수정)
  - **Fix 1**: `codex_in_descendants()` 헬퍼 함수 추가 (line 382)
    - `pgrep -P "$parent"` 로 직접 자식 PID 획득
    - `/proc/{child}/cmdline`을 `tr '\0' ' '`로 변환 후 `@openai/codex|codex\.js` 정규식 매칭
    - 미매칭 시 재귀 호출로 후손 프로세스까지 탐색 (`codex_in_descendants "$child"`)
  - **Fix 2**: `node)` 분기를 `codex_in_descendants "$_pane_pid"` 호출로 교체
    - `_cpid` → `_pane_pid` (변수명 정정)
    - exe 경로 체인 제거 → argv 기반 탐지로 완전 교체

## Discoveries (13)
- Codex CLI는 npm 글로벌 설치 시 Node.js shebang 스크립트로 배포됨 → OS가 실행하는 바이너리는 `.../node`
  - `/proc/{pid}/exe` 는 항상 node 인터프리터를 가리킴 → 실행 파일 경로로 Codex를 구분 불가
  - 해결책: `/proc/{pid}/cmdline` argv 스캔으로 `@openai/codex` 또는 `codex.js` 경로 포함 여부 확인
- 재귀 `codex_in_descendants()`가 필요한 이유: shell → npx → node 같은 중간 프로세스가 있을 수 있음
  - 직접 자식(`pgrep -P`)만 체크하면 중간 프로세스가 있는 경우 누락 가능

---

## Completed (14)
- [x] PR #15 5-7차 리뷰 코멘트 최종 수정 — `dev-orchestrator` 스킬 (#14)

  **7차 리뷰에서 남은 2가지 수정 (이번 커밋):**

  **[CRITICAL] `orchestrate-helpers.sh:103` — `orch_find_idle_panes` 세션 범위 오류:**
  - 기존: `tmux list-panes -s -F '#{pane_id} #{pane_current_command}'` — `-s` 플래그는 현재 세션 범위이나,
    다중 tmux 세션 환경에서 `#{session_id}` 필터 없이 출력하면 의도치 않은 세션 pane 포함 가능
  - **Fix**: `tmux display-message -p '#{session_id}'`로 현재 세션 ID 추출 →
    `tmux list-panes -s -F '#{session_id} #{pane_id} #{pane_current_command}'` 출력 후
    awk에서 `$1 == sess` 필터링으로 현재 세션 pane만 선택

  **[WARNING] `orchestrate-helpers.sh:80-81` — `orch_state_update` 비원자적 쓰기:**
  - 기존: `tmp=$(jq ...)` + `echo "$tmp" > "$path"` — jq 실패 시 빈 내용으로 `batch.state.json` 덮어씀
  - **Fix**: `mktemp` → jq 출력을 임시 파일에 저장 → 성공 시 `mv`(원자적) → 실패 시 `rm` + 에러 메시지 + `return 1`

  **이전 커밋들에서 이미 처리된 수정 (5-6차 리뷰):**
  - **[WARNING] `orch_detect_stall` false stall when no PR**: no PR → `return 1` (early return)
  - **[WARNING] `parse-dependencies.sh:97`** 대소문자 구분 헤딩: `tolower($0) ~ /^### *dependencies/` 적용
  - **[SUGGESTION] `recovery.md`**: `failed` dep도 unblock 수행 명시 (`# both completed and failed unblock dependents` 주석)
  - **[CRITICAL] `orch_dispatch` cd area_dir 누락**: `cd '$area_dir' &&` 선행 추가
  - **[WARNING] auto-retry 미구현**: `retryCount` 기반 bounded retry 구현 (max 1회)
  - **[WARNING] `gh issue view` pipefail 종료**: `|| true` 추가

## Discoveries (14)
- `tmux list-panes -s` 는 현재 session 범위이나, 명시적 `#{session_id}` 필터링 없이는 다중 세션 환경에서
  세션 경계가 모호할 수 있음 → `tmux display-message -p '#{session_id}'` + awk `$1 == sess` 조합이 안전
- `mktemp` + `mv` 패턴이 배시 `echo > file` 대비 원자적: 다른 프로세스/에이전트가 state 파일을 읽는 도중에도
  부분 쓰기(partial write)나 빈 파일 노출이 발생하지 않음

---

## Completed (15)
- [x] PR #20 리뷰 코멘트 수정 — `pipeline-helpers.sh` `pipeline_orchestrator_pane()` 방어적 폴백 (#17, #18)

  **[SUGGESTION] `pipeline-helpers.sh:50` — `$TMUX_PANE` 비어있을 때 빈 target pane 반환:**
  - 기존: `echo "$TMUX_PANE"` 단순 반환 — 비표준 호출 컨텍스트(tmux 세션 내 비-tmux 쉘에서 source)에서 `$TMUX_PANE` 미설정 시 빈 문자열 반환
  - **Fix**: `[ -n "$TMUX_PANE" ]` 분기 추가 → 설정된 경우 `$TMUX_PANE` 반환,
    미설정 시 `tmux display-message -p '#{pane_id}' 2>/dev/null` 폴백으로 현재 포커스 pane ID 획득
  - 주석에 `$TMUX_PANE` 우선 이유(focused pane과 달리 `--continue` 세션에서 변하지 않음) 명시 유지

## Discoveries (15)
- `$TMUX_PANE`은 tmux가 pane 시작 시 환경 변수로 설정함 — 직접 fork한 쉘에는 존재하나,
  tmux 세션 내에서 `exec bash`나 외부 스크립트 경유 시 상속되지 않을 수 있음
- `tmux display-message -p '#{pane_id}'`는 현재 포커스 pane ID를 반환 — `--continue` 세션에서는
  focused pane이 orchestrator pane과 다를 수 있어 $TMUX_PANE이 우선순위를 가져야 함
