#!/bin/bash
# parse-dependencies.sh — Parse GitHub issue body for dependency issue numbers
#
# Usage: bash parse-dependencies.sh <issue_number> [area_dir]
#
# Reads the `### Dependencies` section from the issue body and extracts
# referenced issue numbers. Outputs space-separated issue numbers, or empty
# if none found.
#
# Section format (any of these lines are recognized):
#   - #42
#   - #42 optional description
#   - Closes #42
#   - none / 없음 / N/A  → no dependencies

set -euo pipefail

# ──────────────────────────────────────────────
# Cycle detection helper (Kahn's algorithm)
# Called separately: bash parse-dependencies.sh --check-cycles <issues_json> <dag_json>
# Returns: 0 = no cycles, 1 = cycle detected (prints cycle path to stderr)
# ──────────────────────────────────────────────

if [ "${1:-}" = "--check-cycles" ]; then
  ISSUES_JSON="${2:-[]}"
  DAG_JSON="${3:-}"
  [ -z "$DAG_JSON" ] && DAG_JSON='{}'

  # Use jq to run topological sort (Kahn's algorithm)
  CYCLE_RESULT=$(jq -rn \
    --argjson issues "$ISSUES_JSON" \
    --argjson dag "$DAG_JSON" \
    '
    # Build adjacency list and in-degree map
    # Only include edges where both endpoints are in $issues
    # (external/out-of-batch deps are ignored for cycle detection)
    def build_graph:
      reduce $issues[] as $n (
        {adj: {}, indegree: {}};
        .adj[($n|tostring)] //= [] |
        .indegree[($n|tostring)] //= 0 |
        reduce ([($dag[($n|tostring)] // [])[] | select(. as $d | $issues | any(. == $d))]) [] as $dep (
          .;
          .adj[($dep|tostring)] += [$n|tostring] |
          .indegree[($n|tostring)] += 1
        )
      );

    # Kahn'"'"'s algorithm
    def kahn(g):
      (g.indegree | to_entries | map(select(.value == 0)) | map(.key)) as $queue |
      {g: g, queue: $queue, sorted: [], visited: 0} |
      until(.queue | length == 0;
        (.queue[0]) as $node |
        .queue = .queue[1:] |
        .sorted += [$node] |
        .visited += 1 |
        reduce (.g.adj[$node] // [])[] as $nbr (
          .;
          .g.indegree[$nbr] -= 1 |
          if .g.indegree[$nbr] == 0 then .queue += [$nbr] else . end
        )
      ) |
      if .visited == ($issues | length) then "NO_CYCLE"
      else "CYCLE_DETECTED"
      end;

    build_graph | kahn(.)
    ' 2>/dev/null)

  if [ "$CYCLE_RESULT" = "CYCLE_DETECTED" ]; then
    echo "CYCLE_DETECTED" >&2
    exit 1
  fi
  exit 0
fi

ISSUE="${1:-}"
AREA_DIR="${2:-.}"

if [ -z "$ISSUE" ]; then
  echo "Usage: $0 <issue_number> [area_dir]" >&2
  exit 1
fi

# Fetch issue body
BODY=$(cd "$AREA_DIR" && gh issue view "$ISSUE" --json body --jq '.body' 2>/dev/null) || true

if [ -z "$BODY" ]; then
  # No body or issue not found — no dependencies
  exit 0
fi

# Extract content after "### Dependencies" heading
# Stops at the next "###" heading or end of string
DEPS_SECTION=$(echo "$BODY" | awk '
  tolower($0) ~ /^### *dependencies/ { found=1; next }
  found && /^###/ { exit }
  found { print }
')

if [ -z "$DEPS_SECTION" ]; then
  exit 0
fi

# Check for "no dependencies" markers
if echo "$DEPS_SECTION" | grep -qiE '^\s*(없음|none|n\/a|no dependencies|-\s*없음|-\s*none)\s*$'; then
  exit 0
fi

# Extract issue numbers — match patterns: #N, Closes #N, Fixes #N, Resolves #N
# Use || true so grep returning 1 (no matches) does not abort under set -euo pipefail
echo "$DEPS_SECTION" \
  | grep -oiE '(Closes|Fixes|Resolves|#)\s*#?[0-9]+' \
  | grep -oE '[0-9]+' \
  | sort -un \
  | tr '\n' ' ' \
  | sed 's/ $//' \
  || true
