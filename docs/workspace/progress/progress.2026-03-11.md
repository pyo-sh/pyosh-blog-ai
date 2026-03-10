# Progress: 2026-03-11

## Completed

- [x] Archive + rotation for orchestrator - `orch_archive_batch`, `orch_archive_list`, `orch_archive_rotate` helper functions added to `orchestrate-helpers.sh`; SKILL.md Step 6 + recovery.md updated; batchId collision-resistance improved (#81, PR #127)

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

- [ ] Fix `--sandbox danger-full-access` invalid flag bug in `pipeline-helpers.sh` line 412 (separate issue)

## Notes

- Related PR: #127 (feat/issue-81-archive-rotation) merged into main
- Archive path: `.workspace/orchestrate/{area}/archive/{batchId}/`
- Default rotation: keeps 5 most recent batches (`max_keep=5`)
