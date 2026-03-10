#!/bin/bash
# orch-dispatch-wrapper.sh - Wrapper for dispatched pipeline processes
# Provides: heartbeat, terminal.json (explicit completion contract), signal handling
#
# Usage: bash orch-dispatch-wrapper.sh <attempt_id> <attempt_dir> <issue> <pipeline_state_file> -- <command...>
#
# Artifact paths are derived from <attempt_dir>:
#   {attempt_dir}/pid            - wrapper PID (= PGID when launched via setsid)
#   {attempt_dir}/heartbeat      - epoch timestamp, updated every 60s
#   {attempt_dir}/terminal.json  - completion contract (written on exit)
#   {attempt_dir}/worker.log     - stdout (set up by orch_dispatch via redirect)
#   {attempt_dir}/worker.err     - stderr (set up by orch_dispatch via redirect)
#
# The wrapper:
#   1. Writes its PID to pid file (= PGID when launched via setsid)
#   2. Starts a heartbeat loop (updates heartbeat file every 60s)
#   3. Runs the given command
#   4. On exit (normal or signal), writes terminal.json with full schema
#
# terminal.json schema (schemaVersion 1):
#   schemaVersion  - always 1
#   attemptId      - unique attempt identifier from orchestrator
#   issue          - issue number (integer)
#   status         - "completed" | "failed"
#   prNumber       - PR number if pipeline created one, else null
#   merged         - true if pipeline reached the log/done step, else false
#   headSha        - last commit SHA on the PR branch if known, else null
#   finishedAt     - ISO-8601 UTC timestamp
#   reason         - human-readable summary of exit cause

set -uo pipefail

ATTEMPT_ID="$1"; ATTEMPT_DIR="$2"
ISSUE="$3"; PIPELINE_STATE_FILE="$4"
shift 4
[ "${1:-}" = "--" ] && shift

# Derive artifact paths from attempt directory
PID_FILE="$ATTEMPT_DIR/pid"
HEARTBEAT_FILE="$ATTEMPT_DIR/heartbeat"
TERMINAL_FILE="$ATTEMPT_DIR/terminal.json"

# Write our PID. When launched via setsid, $$ = session leader PID = PGID.
echo $$ > "$PID_FILE"

# Heartbeat loop: update file every 60s
_HB_PID=""
(
  while true; do
    date +%s > "$HEARTBEAT_FILE"
    sleep 60
  done
) &
_HB_PID=$!

# Ensure SIGTERM triggers EXIT trap (default bash behavior kills immediately)
trap 'exit 143' TERM INT

# Exit handler: always write terminal.json
trap '
  _rc=$?
  kill "$_HB_PID" 2>/dev/null
  wait "$_HB_PID" 2>/dev/null

  _status="failed"
  [ $_rc -eq 0 ] && _status="completed"

  # Enrich terminal.json from pipeline state if available
  _pr_number="null"
  _merged="false"
  _head_sha=""
  _reason="pipeline exited with rc=$_rc"
  if [ -f "$PIPELINE_STATE_FILE" ]; then
    _pr_raw=$(jq -r ".pr // empty" "$PIPELINE_STATE_FILE" 2>/dev/null) || true
    [ -n "$_pr_raw" ] && _pr_number="$_pr_raw"
    _step=$(jq -r ".step // empty" "$PIPELINE_STATE_FILE" 2>/dev/null) || _step=""
    _sha=$(jq -r ".lastCommitSha // empty" "$PIPELINE_STATE_FILE" 2>/dev/null) || true
    [ -n "$_sha" ] && _head_sha="$_sha"
    { [ "$_step" = "log" ] || [ "$_step" = "done" ]; } && _merged="true"
    [ $_rc -eq 0 ] && _reason="pipeline completed at step=${_step:-unknown}"
  fi

  _finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # Write terminal.json; fall back to minimal printf if jq unavailable.
  # The fallback omits prNumber/merged/headSha/reason intentionally: it only runs when jq
  # is absent (extremely rare) and orch_check_completion only reads attemptId + status.
  if command -v jq >/dev/null 2>&1; then
    jq -n \
      --arg attemptId "$ATTEMPT_ID" \
      --argjson issue "$ISSUE" \
      --arg status "$_status" \
      --argjson prNumber "$_pr_number" \
      --argjson merged "$_merged" \
      --arg headSha "$_head_sha" \
      --arg finishedAt "$_finished_at" \
      --arg reason "$_reason" \
      "{schemaVersion:1, attemptId:\$attemptId, issue:\$issue,
        status:\$status, prNumber:\$prNumber, merged:\$merged,
        headSha:(if \$headSha == \"\" then null else \$headSha end),
        finishedAt:\$finishedAt, reason:\$reason}" \
      > "$TERMINAL_FILE" 2>/dev/null || \
    printf "{\"schemaVersion\":1,\"attemptId\":\"%s\",\"issue\":%s,\"status\":\"%s\",\"finishedAt\":\"%s\"}\n" \
      "$ATTEMPT_ID" "$ISSUE" "$_status" "$_finished_at" \
      > "$TERMINAL_FILE"
  else
    printf "{\"schemaVersion\":1,\"attemptId\":\"%s\",\"issue\":%s,\"status\":\"%s\",\"finishedAt\":\"%s\"}\n" \
      "$ATTEMPT_ID" "$ISSUE" "$_status" "$_finished_at" \
      > "$TERMINAL_FILE"
  fi

  rm -f "$PID_FILE" "$HEARTBEAT_FILE"
' EXIT

# Execute the actual command (not exec - we need EXIT trap to fire)
"$@"
