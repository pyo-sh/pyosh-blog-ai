# Progress: 2026-03-11

## Completed

- [x] Archive + rotation for orchestrator - `orch_archive_batch`, `orch_archive_list`, `orch_archive_rotate` helper functions added to `orchestrate-helpers.sh`; SKILL.md Step 6 + recovery.md updated; batchId collision-resistance improved (#81, PR #127)
- [x] Codex headless review 3 bugs + SKILL turn conflict - `--sandbox danger-full-access` → `--dangerously-bypass-approvals-and-sandbox`; codex stderr→log redirect (`> /dev/null 2>"$log"`); SKILL.md Required runtime shape + Step 2 turn-end + task-notification wait clarified; codex "stdout" note corrected to "stderr"; "Do not end turn" constraint got review carve-out (#128)
- [x] dev-pipeline 안정화 Epic 1 - review 상태 3분할(`review_dispatch/review_wait/review_process`), `pipeline_run_review` 단일 진입점 강제, `reviewJob` 메타데이터 + 중복 dispatch 방지(`_pipeline_review_fail` early-return 보호 포함), `pipeline_parse_review_body` canonical schema, resolve 4-case 결정 테이블, state machine 전이 테이블, `pipeline_log_transition` + escalation 개선 + subprocess 로그, `tests/smoke-test.sh` 8 cases (#131, PR #130)
- [x] dev-pipeline Python 마이그레이션 리뷰 피드백 수정 + 잔여 개선 - CLAUDECODE env leak `replace_env=True`, legacy step migration `"review"` -> `"review_dispatch"`, review state 필터링 (DISMISSED/PENDING 제외), area validation `paths.py` 중앙화, meta startedAt 보존, typed model 도입 (`state_read` -> `PipelineState`, `state_write` -> `PipelineState`), stale review job TTL recovery, `cmd_state` TypeError 수정, path builder `validate_area()` 적용, `check_review_exists` max id 선택; 128 tests (#129, #133, PR #134)

## Discoveries

- SIGPIPE-safe batchId nonce: combining two `$RANDOM` calls via arithmetic avoids subshell `$(...)` which is susceptible to SIGPIPE in pipeline contexts
- `.archived-at` timestamp file enables deterministic rotation ordering independent of filesystem mtime
- Hidden file glob `.[!.]*` required to capture temp files like `.tmp.state.*` during archive
- `codex exec review --dangerously-bypass-approvals-and-sandbox` is the correct flag; `--sandbox danger-full-access` is invalid - noted as a separate bug in `pipeline-helpers.sh` line 412

## Issues & Resolutions

- **Issue**: `batch-$(date +%Y%m%d-%H%M%S)` batchId had second-precision collision risk and SIGPIPE exposure from `$(...)` subshell
- **Resolution**: `batch-$(date +%Y%m%d-%H%M%S)-$(printf '%04x' "$(( (RANDOM % 256) * 256 + (RANDOM % 256) ))")` - shell arithmetic only, no subshell for nonce

- **Issue**: Archive rotation ordering was non-deterministic if filesystem mtime was unreliable
- **Resolution**: `.archived-at` file written at creation time; `orch_archive_rotate` sorts by this file for stable oldest-first ordering

- [x] dev-pipeline shell 잔재 제거 + dev-resolve 정리 + review template 준수 - `pipeline-helpers.sh` 삭제 (949줄), `smoke-test.sh` 삭제, CLI 서브커맨드 5개 추가 (`init`, `state-update`, `stage-retry`, `check-review`, `check-commits`), SKILL.md 전면 재작성 (shell→Python CLI), reference 문서 Python 함수명으로 업데이트, dev-resolve/dev-build "Record progress" step 삭제, dev-review template inline 삽입, codex output `normalize_codex_output()` 추가 + blockquote 기반 parser leak 방지; 133 tests (#129, #133, PR #136)

## Discoveries

- Codex review normalization - blockquote (`> `) prefix가 line-based parser에서 fenced code block보다 안전: `strip()` 후 `> ### Critical`은 `startswith("### Critical")`에 매칭되지 않음
- skill-creator 최적화 원칙 적용 시 SKILL.md와 reference 간 중복 정보 제거로 총 69줄 절감 (915→846)

## Issues & Resolutions

- **Issue**: `normalize_codex_output()` fallback wrapper에서 fenced code block 내 `### Critical` / `1. item` 라인이 `parse_review_body()`에 의해 실제 findings로 오탐
- **Resolution**: Fenced code block 대신 blockquote prefix (`> `) 사용 - `strip()` 후에도 `>` prefix가 남아 section header/item 매칭 방지

- **Issue**: `${TOOL}` 미설정 시 argparse choices 검증 실패 (빈 문자열이 choices에 없음)
- **Resolution**: SKILL.md에서 `${TOOL:+--tool "$TOOL"}` 사용 - 값이 있을 때만 `--tool` 인자 전달

- **Issue**: codex 출력이 비어있어도 `log.stat().st_size > 0` guard가 normalization 블록 전체를 건너뛰어 정상 종료
- **Resolution**: `rc==0` 진입 후 빈 로그를 early return 1로 처리, normalization은 항상 실행

## Next Steps


## Notes

- Related PR: #127 (feat/issue-81-archive-rotation) merged into main
- Archive path: `.workspace/orchestrate/{area}/archive/{batchId}/`
- Default rotation: keeps 5 most recent batches (`max_keep=5`)
