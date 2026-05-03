#!/usr/bin/env bash
# Start the tmuxinator session, then replace the project pane's process
# with docker attach — bypassing zsh send-keys race condition.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../.env"

tmuxinator start -p "$SCRIPT_DIR/session.host.yml" --no-attach

# respawn-pane -k: kill the pane's shell and replace it with this command directly.
# This runs the wait-loop as the pane's process (no zsh involved).
tmux respawn-pane -k -t blog:project "
  while ! docker exec dev-lab tmux has-session -t lab 2>/dev/null; do
    sleep 0.2
  done
  exec docker exec -it dev-lab tmux attach -t lab
"

# Now attach to the session
tmux attach -t blog
