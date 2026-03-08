#!/usr/bin/env bash
# tools/agent-tracker/agent-tracker.sh
# Real-time tmux agent dashboard — reads from sidecar files (push model).
#
# Architecture (#72):
#   collect_snapshot() → JSON → render_dashboard()
#   No \x1e/\x1f delimiter protocols. All data boundaries are JSON + @tsv.
#   Layers: collect (lib/collect.sh) → render (lib/render.sh) → util (lib/util.sh)
#
# Claude Code panes: data pushed by hooks → .workspace/agent-tracker/{pane_id}.json
# Codex panes: pane scraping fallback (no hooks support)
#
# Usage: bash tools/agent-tracker/agent-tracker.sh [-s SESSION] [-i INTERVAL]
#   -s SESSION   tmux session name (default: lab)
#   -i INTERVAL  refresh interval in seconds (default: 1)

SESSION="lab"
INTERVAL=1
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE_DIR="${PIPELINE_DIR:-"$REPO_ROOT/.workspace/pipeline"}"
ORCH_DIR="${ORCH_DIR:-"$REPO_ROOT/.workspace/orchestrate"}"
SIDECAR_DIR="$REPO_ROOT/.workspace/agent-tracker"

# ── Source library modules ──
source "$SCRIPT_DIR/lib/util.sh"
source "$SCRIPT_DIR/lib/collect.sh"
source "$SCRIPT_DIR/lib/render.sh"

# ── Terminal lifecycle ──
# Preserve exit code through cleanup (#72).
# Only trap EXIT — handles normal exit, exit N, SIGINT (130), SIGTERM (143).
cleanup() {
  local ec=$?
  tput cnorm 2>/dev/null
  tput rmcup 2>/dev/null
  exit "$ec"
}
trap cleanup EXIT

# ── Argument parsing ──
while getopts ":s:i:h" opt; do
  case $opt in
    s) SESSION="$OPTARG" ;;
    i) INTERVAL="$OPTARG" ;;
    h)
      printf 'Usage: %s [-s SESSION] [-i INTERVAL]\n' "$(basename "$0")"
      printf '  -s SESSION   tmux session name (default: lab)\n'
      printf '  -i INTERVAL  refresh interval in seconds (default: 1)\n'
      exit 0 ;;
    \?) printf 'Unknown option: -%s\n' "$OPTARG" >&2; exit 1 ;;
  esac
done

# Validate INTERVAL: must be a positive number
if ! [[ "$INTERVAL" =~ ^[0-9]*\.?[0-9]+$ ]] || \
   ! awk "BEGIN { exit ($INTERVAL > 0) ? 0 : 1 }"; then
  printf 'Error: -i INTERVAL must be a positive number (got: %s)\n' "$INTERVAL" >&2
  exit 1
fi

# ── Sidecar cleanup (safe) ──
# Only clean orphan sidecars when tmux session is confirmed accessible (#72).
# If tmux session doesn't exist or query fails, skip cleanup entirely
# to avoid deleting valid sidecars from another session.
mkdir -p "$SIDECAR_DIR"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  declare -A _active_panes=()
  while IFS= read -r _pid; do
    _active_panes["$_pid"]=1
  done < <(tmux list-panes -s -t "$SESSION" -F '#{pane_id}' 2>/dev/null | sed 's/^%//')
  for _f in "$SIDECAR_DIR"/*.json; do
    [[ -f "$_f" ]] || continue
    _fname="${_f##*/}"
    _pane="${_fname%.json}"
    [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
  done
  unset _active_panes _fname _pane _f _pid
fi

# ── Main loop ──
tput smcup 2>/dev/null
tput civis 2>/dev/null

while true; do
  snapshot=$(collect_snapshot "$SESSION" "$SIDECAR_DIR" "$ORCH_DIR" "$PIPELINE_DIR")
  render_dashboard "$snapshot" "$SESSION"
  sleep "$INTERVAL"
done
