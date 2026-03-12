#!/bin/bash
# parse-dependencies.sh — Parse GitHub issue body for dependency issue numbers
#
# Modes:
#   <issue_number> [area_dir]
#       Parse issue deps (### Dependencies fallback). Output: space-separated numbers.
#
#   --parse-typed <issue_number> [area_dir]
#       Parse with type annotations. Output JSON:
#         {"hard":[N,...],"soft":[N,...],"crossArea":[{"area":A,"issue":N,"type":"hard"|"soft"},...]}
#       Priority: fenced orchestrator block > ### Dependencies section > empty.
#
#   --find-sccs <issues_json> <dag_json>
#       Find SCC (cycle) nodes via Kahn's algorithm. Output JSON:
#         {"hasCycle":bool,"sccNodes":[N,...]}
#       sccNodes = issue numbers that participate in at least one cycle.
#
#   --check-cycles <issues_json> <dag_json>
#       Returns: 0 = no cycles, 1 = cycle detected (prints CYCLE_DETECTED to stderr).
#
# Fenced block format (```orchestrator ... ```):
#   hard: #12, #15          — in-batch hard deps (default; must complete before downstream)
#   soft: #20               — in-batch soft deps (failed dep OK; downstream still proceeds)
#   cross-area: server/#30  — cross-area hard dep (downstream -> blocked-external)
#   cross-area soft: server/#31  — cross-area soft dep (treated as always satisfied)

set -euo pipefail

# ──────────────────────────────────────────────
# --check-cycles: Kahn's algorithm (backward compat)
# ──────────────────────────────────────────────

if [ "${1:-}" = "--check-cycles" ]; then
  ISSUES_JSON="${2:-[]}"
  DAG_JSON="${3:-}"
  [ -z "$DAG_JSON" ] && DAG_JSON='{}'

  CYCLE_RESULT=$(jq -rn \
    --argjson issues "$ISSUES_JSON" \
    --argjson dag "$DAG_JSON" \
    '
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

# ──────────────────────────────────────────────
# --find-sccs: Identify cycle nodes (SCC isolation)
# Returns JSON: {"hasCycle":bool,"sccNodes":[N,...]}
# sccNodes contains ONLY issue numbers that are themselves in a cycle.
# Issues that merely depend on cycle nodes are NOT included (they get
# blocked-failed-dependency through the normal orch_unblock logic).
# ──────────────────────────────────────────────

if [ "${1:-}" = "--find-sccs" ]; then
  ISSUES_JSON="${2:-[]}"
  DAG_JSON="${3:-}"
  [ -z "$DAG_JSON" ] && DAG_JSON='{}'

  jq -n \
    --argjson issues "$ISSUES_JSON" \
    --argjson dag "$DAG_JSON" \
    '
    # Forward adjacency: adj[dep] = list of issues that depend on dep.
    # Filters deps to in-batch issues only.
    def build_adj:
      (reduce $issues[] as $m ({}; . + {($m|tostring): []})) as $init |
      reduce $issues[] as $n (
        $init;
        reduce ([($dag[($n|tostring)] // [])[] | select(. as $d | $issues | any(. == $d))]) [] as $dep (
          .;
          .[$dep|tostring] += [$n|tostring]
        )
      );

    # Is node n in a cycle? BFS from adj[n] (n'"'"'s successors), check if n is reachable.
    # A node is in a cycle iff it can reach itself through forward edges.
    # Uses $n/$adj (value-binding parameters) not path expressions.
    def is_in_cycle($n; $adj):
      {q: ($adj[$n] // []), visited: {}} |
      until(.q | length == 0;
        (.q[0]) as $curr |
        .q = .q[1:] |
        if .visited[$curr] then .
        else .visited[$curr] = true | .q += ($adj[$curr] // []) end
      ) |
      .visited[$n] == true;

    build_adj as $adj |
    ($issues | map(tostring) | map(select(is_in_cycle(.; $adj))) | map(tonumber)) as $cycle_nodes |
    {"hasCycle": ($cycle_nodes | length > 0), "sccNodes": $cycle_nodes}
    ' 2>/dev/null
  exit 0
fi

# ──────────────────────────────────────────────
# --parse-typed: Parse with type annotations
# Priority: fenced orchestrator block > ### Dependencies > empty
# Output JSON: {"hard":[N,...],"soft":[N,...],"crossArea":[{"area":A,"issue":N,"type":"hard"|"soft"},...]}
# ──────────────────────────────────────────────

if [ "${1:-}" = "--parse-typed" ]; then
  ISSUE="${2:-}"
  AREA_DIR="${3:-.}"

  if [ -z "$ISSUE" ]; then
    echo "Usage: $0 --parse-typed <issue_number> [area_dir]" >&2
    exit 1
  fi

  BODY=$(cd "$AREA_DIR" && gh issue view "$ISSUE" --json body --jq '.body' 2>/dev/null) || true

  if [ -z "$BODY" ]; then
    echo '{"hard":[],"soft":[],"crossArea":[]}'
    exit 0
  fi

  # Try fenced orchestrator block first
  # Matches: ```orchestrator ... ``` (must be at start of line)
  FENCED=$(echo "$BODY" | awk '/^```orchestrator/{found=1; next} found && /^```/{exit} found{print}')

  if [ -n "$FENCED" ]; then
    # Parse fenced block via jq
    # Supported line patterns:
    #   hard: #12, #15
    #   soft: #20
    #   cross-area: server/#30, client/#15
    #   cross-area soft: server/#31
    echo "$FENCED" | jq -Rs '
      split("\n") |
      map(select(length > 0)) |
      reduce .[] as $line (
        {"hard": [], "soft": [], "crossArea": []};
        if ($line | test("^cross-area soft:\\s*"; "i")) then
          .crossArea += (
            ($line | gsub("^cross-area soft:\\s*"; ""; "i")) |
            [match("([a-zA-Z][a-zA-Z0-9_-]*)/?#([0-9]+)"; "g")] |
            map({area: .captures[0].string, issue: (.captures[1].string | tonumber), type: "soft"})
          )
        elif ($line | test("^cross-area:\\s*"; "i")) then
          .crossArea += (
            ($line | gsub("^cross-area:\\s*"; ""; "i")) |
            [match("([a-zA-Z][a-zA-Z0-9_-]*)/?#([0-9]+)"; "g")] |
            map({area: .captures[0].string, issue: (.captures[1].string | tonumber), type: "hard"})
          )
        elif ($line | test("^soft:\\s*"; "i")) then
          .soft += (
            ($line | gsub("^soft:\\s*"; ""; "i")) |
            [scan("[0-9]+")] | map(tonumber)
          )
        elif ($line | test("^hard:\\s*"; "i")) then
          .hard += (
            ($line | gsub("^hard:\\s*"; ""; "i")) |
            [scan("[0-9]+")] | map(tonumber)
          )
        else .
        end
      ) |
      .hard |= (map(tostring) | unique | map(tonumber)) |
      .soft |= (map(tostring) | unique | map(tonumber))
    '
  else
    # Fall back to ### Dependencies section (all treated as hard)
    DEPS_SECTION=$(echo "$BODY" | awk '
      tolower($0) ~ /^### *dependencies/ { found=1; next }
      found && /^###/ { exit }
      found { print }
    ')

    if [ -z "$DEPS_SECTION" ]; then
      echo '{"hard":[],"soft":[],"crossArea":[]}'
      exit 0
    fi

    if echo "$DEPS_SECTION" | grep -qiE '^\s*(-\s*)?(없음|none|n\/a|no dependencies)\s*$'; then
      echo '{"hard":[],"soft":[],"crossArea":[]}'
      exit 0
    fi

    NUMS=$(echo "$DEPS_SECTION" \
      | grep -oiE '(Closes|Fixes|Resolves|#)\s*#?[0-9]+' \
      | grep -oE '[0-9]+' \
      | sort -un \
      | tr '\n' ',') || true
    NUMS="${NUMS%,}"

    if [ -z "$NUMS" ]; then
      echo '{"hard":[],"soft":[],"crossArea":[]}'
    else
      echo "$NUMS" | jq -Rs '
        split(",") | map(select(length > 0) | tonumber) |
        {"hard": ., "soft": [], "crossArea": []}
      '
    fi
  fi
  exit 0
fi

# ──────────────────────────────────────────────
# Default mode: <issue_number> [area_dir]
# Legacy flat output: space-separated issue numbers (backward compat)
# ──────────────────────────────────────────────

ISSUE="${1:-}"
AREA_DIR="${2:-.}"

if [ -z "$ISSUE" ]; then
  echo "Usage: $0 <issue_number> [area_dir]" >&2
  exit 1
fi

# Fetch issue body
BODY=$(cd "$AREA_DIR" && gh issue view "$ISSUE" --json body --jq '.body' 2>/dev/null) || true

if [ -z "$BODY" ]; then
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

# Check for "no dependencies" markers (with optional leading "- ")
if echo "$DEPS_SECTION" | grep -qiE '^\s*(-\s*)?(없음|none|n\/a|no dependencies)\s*$'; then
  exit 0
fi

# Extract issue numbers — match patterns: #N, Closes #N, Fixes #N, Resolves #N
echo "$DEPS_SECTION" \
  | grep -oiE '(Closes|Fixes|Resolves|#)\s*#?[0-9]+' \
  | grep -oE '[0-9]+' \
  | sort -un \
  | tr '\n' ' ' \
  | sed 's/ $//' \
  || true
