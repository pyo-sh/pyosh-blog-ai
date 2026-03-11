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

  # Check merge eligibility: runs when completed with a known PR.
  # Conditions: required checks pass, no conflict, no blocking labels.
  # Blocking labels: needs-human, manual-review, blocked.
  _merge_eligible=""
  _eligibility_checks='{"checksPass":null,"noConflict":null,"noBlockingLabels":null}'
  if [ "$_status" = "completed" ] && [ "$_pr_number" != "null" ] && command -v jq >/dev/null 2>&1 && command -v gh >/dev/null 2>&1; then
    _area_name=""
    [ -f "$PIPELINE_STATE_FILE" ] && _area_name=$(jq -r ".area // empty" "$PIPELINE_STATE_FILE" 2>/dev/null) || true
    _elig_repo=""
    case "$_area_name" in
      client)    _elig_repo="pyo-sh/pyosh-blog-fe" ;;
      server)    _elig_repo="pyo-sh/pyosh-blog-be" ;;
      workspace) _elig_repo="pyo-sh/pyosh-blog-ai" ;;
    esac
    if [ -n "$_elig_repo" ]; then
      # Required checks: no failed or cancelled runs
      _checks_failing=$(gh pr checks "$_pr_number" -R "$_elig_repo" \
        --json name,state \
        --jq '[.[] | select(.state == "fail" or .state == "cancelled")] | length' \
        2>/dev/null) || _checks_failing=""
      _checks_pass="null"
      [ "$_checks_failing" = "0" ] && _checks_pass="true"
      [ -n "$_checks_failing" ] && [ "$_checks_failing" != "0" ] && _checks_pass="false"

      # No conflict: PR must be MERGEABLE
      _mergeable=$(gh pr view "$_pr_number" -R "$_elig_repo" \
        --json mergeable --jq '.mergeable' 2>/dev/null) || _mergeable=""
      _no_conflict="null"
      [ "$_mergeable" = "MERGEABLE" ] && _no_conflict="true"
      [ "$_mergeable" = "CONFLICTING" ] && _no_conflict="false"

      # No blocking labels
      _blocking=$(gh pr view "$_pr_number" -R "$_elig_repo" --json labels \
        --jq '[.labels[].name | select(. == "needs-human" or . == "manual-review" or . == "blocked")] | length' \
        2>/dev/null) || _blocking=""
      _no_blocking="null"
      [ "$_blocking" = "0" ] && _no_blocking="true"
      [ -n "$_blocking" ] && [ "$_blocking" != "0" ] && _no_blocking="false"

      # PR head SHA matches current attempt (guard against unexpected force-pushes)
      _pr_head=$(gh pr view "$_pr_number" -R "$_elig_repo" \
        --json headRefOid --jq '.headRefOid' 2>/dev/null) || _pr_head=""
      _sha_match="null"
      if [ -n "$_pr_head" ] && [ -n "$_head_sha" ]; then
        [ "$_pr_head" = "$_head_sha" ] && _sha_match="true"
        [ "$_pr_head" != "$_head_sha" ] && _sha_match="false"
      fi

      _eligibility_checks="{\"checksPass\":${_checks_pass:-null},\"noConflict\":${_no_conflict:-null},\"noBlockingLabels\":${_no_blocking:-null},\"shaMatch\":${_sha_match:-null}}"

      # Eligible only when all four checks are explicitly true
      if [ "$_checks_pass" = "true" ] && [ "$_no_conflict" = "true" ] && [ "$_no_blocking" = "true" ] && [ "$_sha_match" = "true" ]; then
        _merge_eligible="true"
      elif [ "$_checks_pass" = "false" ] || [ "$_no_conflict" = "false" ] || [ "$_no_blocking" = "false" ] || [ "$_sha_match" = "false" ]; then
        _merge_eligible="false"
      fi
      # If any check returned null (API error), _merge_eligible stays "" (becomes null in JSON)
    fi
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
      --arg mergeEligible "$_merge_eligible" \
      --arg eligChecks "$_eligibility_checks" \
      --arg finishedAt "$_finished_at" \
      --arg reason "$_reason" \
      "{schemaVersion:1, attemptId:\$attemptId, issue:\$issue,
        status:\$status, prNumber:\$prNumber, merged:\$merged,
        headSha:(if \$headSha == \"\" then null else \$headSha end),
        mergeEligible:(if \$mergeEligible == \"true\" then true elif \$mergeEligible == \"false\" then false else null end),
        mergeEligibilityChecks:(\$eligChecks | fromjson),
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
