# 2026-03-10 Progress

## Pipeline headless CLAUDECODE unset + audit fixes (PR #119)

`pipeline_run_headless_core`의 CLAUDECODE 환경변수 미해제 버그를 수정하고,
종합 파이프라인 감사에서 발견된 5개 추가 이슈를 일괄 수정했다.

### 핵심 수정 (fix: unset CLAUDECODE)

- `pipeline_run_headless_core` 내 서브셸에 `unset CLAUDECODE` 추가
- Claude Code 세션 안에서 `claude -p` 호출 시 "cannot be launched inside another Claude Code session" 오류 재발 방지

### pipeline-helpers.sh 개선

- **gh stderr 격리**: `pipeline_check_review_exists` / `pipeline_check_new_commits`에서
  `2>&1` 대신 `mktemp` 임시 파일로 stderr 캡처 - gh가 exit 0이면서 경고를 출력할 때
  캡처된 변수를 오염시키는 문제 방지
- **meta 파일 guard**: 최종 meta 업데이트를 `jq -n`(재생성)에서 `jq`(기존 파일 업데이트)로 전환,
  `startedAt` 등 초기 필드 보존; 파일 없을 때만 `jq -n` 폴백; 실패 시 stderr 로그
- **merge lock 서브셸**: `pipeline_merge_pr`의 lock 보유 구간을 서브셸로 감싸고
  `trap EXIT`으로 신뢰성 있는 lock 해제 보장; 외부 `trap INT TERM`으로 race window 커버
- **rc=2 gh API 오류**: 두 check 함수 모두 gh 실패 시 rc=2 반환 (이전: 에러 무시)

### SKILL.md 개선

- source 경로 수정: `dev-pipeline/scripts/pipeline-helpers.sh` (헤더 + Section 0 두 곳)
- review/resolve 복구 진입점에 `RC=$?` / `rc=2` 오류 처리 패턴 추가

### orchestrate-helpers.sh 개선

- `_orch_pr_list` 실패 시 `"failed"` 낙수 → `"running"` 반환으로 수정 (gh API 오류 시 판단 보류)
- grace period 코멘트 수정: "since we last checked" → "since dispatch"

### orch-dispatch-wrapper.sh

- PR #118 terminal.json 계약과의 충돌 해결: main의 풍부한 스키마(schemaVersion, prNumber, merged, headSha, reason) 유지

### 관련 문서

- findings.017: `pipeline_run_headless_core` CLAUDECODE 전파 버그 기록
- process-lifecycle.md: 함수명, stale lock 설명, lock 디렉터리 내용 수정
- state-detection.md: .exit 파일 스키마 반영
