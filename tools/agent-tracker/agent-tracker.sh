#!/usr/bin/env bash
# tools/agent-tracker/agent-tracker.sh
# Real-time tmux agent dashboard — reads from Python backend normalized export (#114).
#
# Architecture (#114):
#   Python backend daemon → current.json → render_dashboard()
#   No direct collection in the UI layer. All data comes from the normalized export.
#   Layers: backend/ (Python) → current.json → render (lib/render.sh) → util (lib/util.sh)
#
# Claude Code panes: data pushed by hooks → .workspace/agent-tracker/<socket-hash>/<session>/<pane>.json (v2)
# Codex panes: pane scraping fallback (no hooks support)
#
# Usage: bash tools/agent-tracker/agent-tracker.sh [-s SESSION] [-i INTERVAL]
#   -s SESSION   tmux session name (default: lab)
#   -i INTERVAL  refresh interval in seconds (default: 1)

SESSION="lab"
INTERVAL=1
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SIDECAR_DIR="$REPO_ROOT/.workspace/agent-tracker"
EXPORT_FILE="$REPO_ROOT/.workspace/agent-tracker/state/current.json"

# ── Source library modules ──
source "$SCRIPT_DIR/lib/util.sh"
source "$SCRIPT_DIR/lib/render.sh"

# ── Terminal lifecycle ──
# Preserve exit code through cleanup (#72).
# Only trap EXIT — handles normal exit, exit N, SIGINT (130), SIGTERM (143).
_BACKEND_PID=""
cleanup() {
  local ec=$?
  if [[ -n "$_BACKEND_PID" ]]; then
    kill "$_BACKEND_PID" 2>/dev/null
    wait "$_BACKEND_PID" 2>/dev/null
  fi
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

# ── Start Python backend daemon ──
# Backend writes normalized export to EXPORT_FILE at --interval seconds.
# Sidecar state dir must exist before backend starts.
mkdir -p "$(dirname "$EXPORT_FILE")"

# --interval is intentionally tied to $INTERVAL: backend export cadence = display refresh rate.
PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m backend \
  --root "$REPO_ROOT" \
  --session "$SESSION" \
  --interval "$INTERVAL" \
  --output "$EXPORT_FILE" \
  2>>"$REPO_ROOT/.workspace/agent-tracker/backend.log" &
_BACKEND_PID=$!

# Brief liveness check — catch immediate startup failures (missing module, bad flag, etc.)
# before entering the main loop where a dead backend silently yields empty snapshots.
# Poll 5×100 ms instead of a fixed sleep to avoid unnecessary latency on fast hosts.
_alive=false
for _i in 1 2 3 4 5; do
  sleep 0.1
  kill -0 "$_BACKEND_PID" 2>/dev/null && { _alive=true; break; }
done
unset _i
if [[ "$_alive" == false ]]; then
  printf '[agent-tracker] WARNING: backend exited early — check %s\n' \
    "$REPO_ROOT/.workspace/agent-tracker/backend.log" >&2
fi
unset _alive

# ── Sidecar cleanup (safe) ──
# Runs once at startup. Scoped to the current tmux server + target session only.
# 1. Remove stale v1 flat sidecars (immediate cutover, #109).
# 2. Remove orphan v2 sidecars for panes no longer active in SESSION.
# Skip entirely if session is inaccessible to avoid deleting sidecars from other sessions (#72).
mkdir -p "$SIDECAR_DIR"

# Compute socket hash for this tmux server ($TMUX: socket_path,server_pid,session_id)
# md5sum: GNU coreutils (Linux only)
_tmux_socket="${TMUX%%,*}"
_socket_hash=$(printf '%s' "$_tmux_socket" | md5sum | cut -c1-6)

# Remove v1 flat sidecars (old namespace: SIDECAR_DIR/*.json)
for _f in "$SIDECAR_DIR"/*.json; do
  [[ -f "$_f" ]] && rm -f "$_f"
done
unset _f

if tmux has-session -t "$SESSION" 2>/dev/null; then
  # Guard: if list-panes fails (race: session vanished after has-session),
  # skip orphan cleanup entirely. An empty _active_panes would delete ALL
  # sidecars, which is worse than leaving stale ones behind (#113).
  _pane_ids=$(tmux list-panes -s -t "$SESSION" -F '#{pane_id}' 2>/dev/null) || _pane_ids=""
  if [[ -n "$_pane_ids" ]]; then
    declare -A _active_panes=()
    while IFS= read -r _pid; do
      [[ -n "$_pid" ]] && _active_panes["${_pid#%}"]=1
    done <<< "$_pane_ids"
    # Remove orphan v2 sidecars for this server + session
    _v2_dir="$SIDECAR_DIR/${_socket_hash}/${SESSION}"
    if [[ -d "$_v2_dir" ]]; then
      for _f in "$_v2_dir"/*.json; do
        [[ -f "$_f" ]] || continue
        _fname="${_f##*/}"
        _pane="${_fname%.json}"
        [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
      done
    fi
    unset _active_panes _fname _pane _f _v2_dir _pid
  fi
  unset _pane_ids
fi
unset _tmux_socket _socket_hash

# ── Main loop ──
tput smcup 2>/dev/null
tput civis 2>/dev/null

while true; do
  # Read from the normalized export written by the Python backend.
  # Show an empty snapshot until the first export is ready.
  if [[ -f "$EXPORT_FILE" ]]; then
    snapshot=$(cat "$EXPORT_FILE")
  else
    snapshot='{}'
  fi
  render_dashboard "$snapshot" "$SESSION"
  sleep "$INTERVAL"
done
