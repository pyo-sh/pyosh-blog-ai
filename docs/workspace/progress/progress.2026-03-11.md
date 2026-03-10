# Progress: 2026-03-11

## Completed

- [x] Archive + rotation for orchestrator - `orch_archive_batch`, `orch_archive_list`, `orch_archive_rotate` helper functions added to `orchestrate-helpers.sh`; SKILL.md Step 6 + recovery.md updated; batchId collision-resistance improved (#81, PR #127)
- [x] Codex headless review 3 bugs + SKILL turn conflict - `--sandbox danger-full-access` → `--dangerously-bypass-approvals-and-sandbox`; codex stderr→log redirect (`> /dev/null 2>"$log"`); SKILL.md Required runtime shape + Step 2 turn-end + task-notification wait clarified; codex "stdout" note corrected to "stderr"; "Do not end turn" constraint got review carve-out (#128)
- [x] dev-pipeline 안정화 Epic 1 - review 상태 3분할(`review_dispatch/review_wait/review_process`), `pipeline_run_review` 단일 진입점 강제, `reviewJob` 메타데이터 + 중복 dispatch 방지(`_pipeline_review_fail` early-return 보호 포함), `pipeline_parse_review_body` canonical schema, resolve 4-case 결정 테이블, state machine 전이 테이블, `pipeline_log_transition` + escalation 개선 + subprocess 로그, `tests/smoke-test.sh` 8 cases (#131, PR #130)

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

## Next Steps



## Notes

- Related PR: #127 (feat/issue-81-archive-rotation) merged into main
- Archive path: `.workspace/orchestrate/{area}/archive/{batchId}/`
- Default rotation: keeps 5 most recent batches (`max_keep=5`)
