# Workspace Progress - 2026-03-10

## Attempt isolation - attemptId + artifact directory separation (#79)

**Issue**: #79

### Changes
- Changed attemptId format from `{batchId}-issue{N}-attempt{M}` to `issue-{N}-a{M}`
- Added `orch_attempt_dir()` for per-attempt directories at `.workspace/orchestrate/{area}/issues/{N}/attempts/{attemptId}/`
- Updated `orch_dispatch` to create attempt directories instead of flat files, preserving previous attempt artifacts on retry
- Updated `orch-dispatch-wrapper.sh` to accept `attempt_dir` parameter and derive file paths from it
- Updated `orch_check_completion` and `orch_detect_stall` to resolve paths from attempt directory
- Updated SKILL.md, state-detection.md, and recovery.md docs
- Removed `orch_signal_path` alias and flat file cleanup (`rm -f`) in pre-dispatch
- Replaced `log` field in dispatched state with `attemptDir`

### Key insight
With attempt-isolated directories, the attemptId matching in terminal.json becomes a safety net rather than the primary collision prevention mechanism. The `log` field in dispatched state was never actually read by any function; replaced with `attemptDir` for explicit path derivation.
