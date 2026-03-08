#!/bin/bash
# orch-dispatch-wrapper.sh - Wrapper for dispatched pipeline processes
# Provides: heartbeat, structured exit file (JSON), signal handling
#
# Usage: bash orch-dispatch-wrapper.sh <attempt_id> <exit_file> <heartbeat_file> <pid_file> -- <command...>
#
# The wrapper:
#   1. Writes its PID to pid_file (= PGID when launched via setsid)
#   2. Starts a heartbeat loop (updates heartbeat_file every 60s)
#   3. Runs the given command
#   4. On exit (normal or signal), writes a JSON exit file with attemptId

set -uo pipefail

ATTEMPT_ID="$1"; EXIT_FILE="$2"; HEARTBEAT_FILE="$3"; PID_FILE="$4"
shift 4
[ "${1:-}" = "--" ] && shift

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

# Exit handler: always write structured exit file
trap '
  _rc=$?
  kill "$_HB_PID" 2>/dev/null
  wait "$_HB_PID" 2>/dev/null
  _status="failed"
  [ $_rc -eq 0 ] && _status="completed"
  printf "{\"attemptId\":\"%s\",\"status\":\"%s\",\"rc\":%d,\"endedAt\":\"%s\"}\n" \
    "$ATTEMPT_ID" "$_status" "$_rc" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "$EXIT_FILE"
  rm -f "$PID_FILE" "$HEARTBEAT_FILE"
' EXIT

# Execute the actual command (not exec - we need EXIT trap to fire)
"$@"
