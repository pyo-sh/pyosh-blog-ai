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
