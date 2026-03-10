# 2026-03-10 Progress

## Pipeline direct resolve + auto-merge (PR #121, #120)

headless `/dev-resolve` sub-agent를 제거하고 pipeline 세션에서 직접 resolve하도록 전환했다.
review-resolve 자동 루프(최대 5라운드)와 severity 기반 auto-merge 로직을 추가했다.

### 핵심 변경 - direct resolve

- `pipeline_run_resolve()`, `pipeline_resolve_prompt()` 삭제
- `pipeline_fetch_review_comments()` 신규 - inline review 코멘트 fetch (`gh api --paginate | jq -s`)
- `pipeline_run_headless_core`에서 resolve stage 제거 (review only)
- SKILL.md Step 4를 직접 resolve 워크플로우로 전면 재작성 (4a-4d sub-steps)
- dev-resolve/SKILL.md에서 pipeline runtime contract 섹션 제거 (standalone skill로 유지)

### 자동 review-resolve 루프

- state에 `reviewResolveRound`, `maxReviewResolveRounds: 5` 추가
- Critical/Warning: 자동 resolve → re-review (5라운드 후 사용자 확인)
- Suggestion-only: AI 판단으로 auto-merge / resolve+re-review / resolve+merge
- Clean review (0 findings): auto-merge
- Headless(비대화형): Critical/Warning 라운드 초과 시 자동 escalation, Suggestion-only는 auto-merge

### Merge lock 강화

- Stale lock reclaim에 fencing 검증 추가 (sleep 0.2 + issue 재확인으로 TOCTOU race 방지)
- No-timestamp stuck lock: lock dir mtime 기반 grace period(30s) reclaim
- Conditional trap clear: lock release 성공 시에만 EXIT trap 해제

### 기타 개선

- `pipeline_check_review_exists`: `--paginate | jq -s` 페이지네이션 안전 처리
- `pipeline_check_new_commits`: `gh pr view --json headRefOid`로 간소화
- `pipeline_stage_retry`: `--arg`/`--argjson`으로 jq injection 방지
- `pipeline_fetch_review`: stderr mktemp 격리 + 에러 핸들링
- `pipeline_cleanup`: message 파일 정리 추가, resolve stage 로그 참조 제거
- v1 state migration 로직 삭제, legacy worktree path fallback 삭제
- `monorepo-layout.md`: worktree path를 area-scoped 규약으로 통일
- recovery.md: resolve 복구 플로우 전면 재작성 (local HEAD 체크, dirty state 핸들링)
- process-lifecycle.md: state schema v2, direct resolve 설명
- pipeline-audit.md: 8개 원본 버그 + lock 강화 resolved 기록
- orchestrate-helpers.sh: dispatch prompt에서 resolve subprocess 참조 제거

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
