# Dependency Resolution

How the orchestrator builds a DAG from GitHub issue bodies and validates it.

## Issue Body Convention

Issues declare dependencies in a `### Dependencies` section:

```markdown
### Dependencies

- #12
- #15 (auth must be done first)
```

Or for no dependencies:

```markdown
### Dependencies

없음
```

Accepted "no dependency" markers: `없음`, `none`, `N/A`, `no dependencies` (case-insensitive).

## Parsing

`parse-dependencies.sh` fetches the issue body via `gh issue view {N} --json body` and extracts the `### Dependencies` section. It matches any of:

| Pattern | Example |
|---------|---------|
| `#N` | `- #42` |
| `Closes #N` | `Closes #42` |
| `Fixes #N` | `Fixes #12` |
| `Resolves #N` | `Resolves #5` |

Output: space-separated issue numbers (sorted, deduplicated), or empty string.

## DAG Construction

```bash
declare -A dag  # dag[N]="dep1 dep2"

for N in $ISSUES; do
  DEPS=$(bash scripts/parse-dependencies.sh "$N" "$AREA_DIR")
  dag[$N]="$DEPS"
done
```

Convert to JSON for `orch_init`:

```bash
# Build dag_json: {"N": [dep1, dep2], ...}
dag_json="{"
for N in $ISSUES; do
  DEPS=$(bash scripts/parse-dependencies.sh "$N" "$AREA_DIR")
  deps_arr=$(echo "$DEPS" | tr ' ' '\n' | grep -E '^[0-9]+$' | jq -R 'tonumber' | jq -sc '.')
  dag_json="${dag_json}\"${N}\": ${deps_arr},"
done
dag_json="${dag_json%,}}"  # trim trailing comma

issues_json=$(echo "$ISSUES" | tr ' ' '\n' | jq -R 'tonumber' | jq -sc '.')
```

## Cycle Detection

Run Kahn's algorithm via `parse-dependencies.sh --check-cycles`:

```bash
bash scripts/parse-dependencies.sh --check-cycles "$issues_json" "$dag_json"
rc=$?
if [ $rc -eq 1 ]; then
  echo "ERROR: Circular dependency detected. Aborting." >&2
  exit 1
fi
```

## Initial Status Assignment

After DAG construction, assign initial status to each issue:

| Condition | Initial Status |
|-----------|---------------|
| `dag[N]` is empty | `pending` |
| `dag[N]` has one or more deps | `blocked` |

Issues already in `.workspace/pipeline/{area}/issue-N.state.json` → skip (already running).

## Dependency satisfaction and failed dependency propagation

An issue transitions from `blocked` when all its dependencies reach a terminal state:

| All deps | Transition |
|----------|------------|
| All `completed` | `blocked` -> `pending` (ready to dispatch) |
| All resolved, >= 1 `failed` or `skipped_dep_failed` | `blocked` -> `skipped_dep_failed` |

`skipped_dep_failed` is a terminal state. The issue is NOT dispatched, but it still
triggers `orch_unblock` for downstream issues (propagating the skip).

`orch_unblock()` in `orchestrate-helpers.sh` automates this check on each completion event.

## Edge Cases

- **Issue not in batch**: If a dependency references an issue not in the current batch, `orch_init` auto-filters it out (only in-batch dependencies are stored in the DAG). A warning is logged but the issue proceeds as if that dependency doesn't exist.
- **Self-dependency**: `dag[N]` containing N itself → caught by cycle detection.
- **Empty `### Dependencies` section**: Treated as no dependencies → `pending`.
