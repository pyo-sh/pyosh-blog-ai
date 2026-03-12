# Dependency resolution

How the orchestrator builds a DAG from GitHub issue bodies and validates it.

## Issue body formats

### Fenced orchestrator block (preferred)

Use a fenced code block tagged `orchestrator`. Parser priority: fenced block > `### Dependencies` section > no deps.

```orchestrator
hard: #12, #15
soft: #20
cross-area: server/#30
cross-area soft: client/#5
```

| Line prefix | Meaning |
|-------------|---------|
| `hard: #N, #M` | In-batch hard dependencies (default). Must complete before downstream dispatches. Failure blocks downstream. |
| `soft: #N` | In-batch soft dependencies. Downstream proceeds even if dep fails. |
| `cross-area: area/#N` | Cross-area hard dep (different repo). Downstream -> `blocked-external`. |
| `cross-area soft: area/#N` | Cross-area soft dep. Treated as always satisfied. |

Multiple issue numbers may appear on one line, comma- or space-separated.

### Legacy `### Dependencies` section (fallback)

Issues without a fenced block fall back to the `### Dependencies` section. All deps parsed here are treated as **hard**.

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

### Parsed patterns (legacy section)

| Pattern | Example |
|---------|---------|
| `#N` | `- #42` |
| `Closes #N` | `Closes #42` |
| `Fixes #N` | `Fixes #12` |
| `Resolves #N` | `Resolves #5` |

Output: space-separated issue numbers (sorted, deduplicated), or empty string.

## Parsing utilities

### `--parse-typed <issue> [area_dir]`

Returns JSON with type annotations:

```json
{
  "hard": [12, 15],
  "soft": [20],
  "crossArea": [
    {"area": "server", "issue": 30, "type": "hard"},
    {"area": "client", "issue": 5, "type": "soft"}
  ]
}
```

### Default mode `<issue> [area_dir]`

Returns space-separated in-batch dep numbers (legacy, all treated as hard).

## DAG construction

```bash
declare -A dag

for N in $ISSUES; do
  TYPED=$(bash scripts/parse-dependencies.sh --parse-typed "$N" "$AREA_DIR")
  HARD_DEPS=$(echo "$TYPED" | jq -r '.hard[]')
  SOFT_DEPS=$(echo "$TYPED" | jq -r '.soft[]')
  dag[$N]="$HARD_DEPS $SOFT_DEPS"
done
```

Convert to JSON for `orch_init`:

```bash
# Build dag_json, dep_types_json, cross_area_deps_json from --parse-typed output.
# Filter each dep list to in-batch issues only.
# issues_json must be assigned BEFORE the loop (used inside for in-batch filtering).

issues_json=$(echo "$ISSUES" | tr ' ' '\n' | jq -R 'tonumber' | jq -sc '.')

dag_json="{"
dep_types_json="{"
cross_area_deps_json="{"
for N in $ISSUES; do
  TYPED=$(bash scripts/parse-dependencies.sh --parse-typed "$N" "$AREA_DIR")

  # In-batch deps (hard + soft combined, filtered to batch)
  ALL_DEPS=$(echo "$TYPED" | jq --argjson issues_arr "$issues_json" \
    '[(.hard + .soft)[] | select(. as $d | $issues_arr | any(. == $d))]')
  dag_json="${dag_json}\"${N}\": ${ALL_DEPS},"

  # Dep types for in-batch deps only
  TYPES=$(echo "$TYPED" | jq --argjson issues_arr "$issues_json" \
    '([.hard[] | select(. as $d | $issues_arr | any(. == $d)) | {key: tostring, value: "hard"}] +
      [.soft[] | select(. as $d | $issues_arr | any(. == $d)) | {key: tostring, value: "soft"}]) |
     from_entries')
  dep_types_json="${dep_types_json}\"${N}\": ${TYPES},"

  # Cross-area deps
  CROSS=$(echo "$TYPED" | jq '.crossArea')
  cross_area_deps_json="${cross_area_deps_json}\"${N}\": ${CROSS},"
done
dag_json="${dag_json%,}}"
dep_types_json="${dep_types_json%,}}"
cross_area_deps_json="${cross_area_deps_json%,}}"

orch_init "$AREA" "$AGENT" "$issues_json" "$dag_json" 4 "$dep_types_json" "$cross_area_deps_json"
```

## Dependency semantics

### Hard dependency (default)

| Dep status | Downstream action |
|------------|------------------|
| `completed` | Satisfied; unblock downstream |
| Any terminal non-completed | `blocked-failed-dependency` (terminal; downstream not dispatched) |

Terminal non-completed statuses: `failed`, `skipped_dep_failed`, `blocked-failed-dependency`, `blocked-external`, `cycle-isolated`.

### Soft dependency

| Dep status | Downstream action |
|------------|------------------|
| `completed` | Satisfied |
| Any failure status | Also satisfied (proceeds to `pending`) |

### Cross-area dependency

Deps in a different area repo cannot be tracked by the orchestrator.

| Cross-area dep type | Downstream action |
|--------------------|------------------|
| `hard` | `blocked-external` (terminal; requires manual intervention) |
| `soft` | Treated as always satisfied |

## Cycle detection and SCC isolation

Run `--find-sccs` to identify cycle participants:

```bash
scc_json=$(bash scripts/parse-dependencies.sh --find-sccs "$issues_json" "$dag_json")
# {"hasCycle": true, "sccNodes": [12, 15]}
```

`orch_init` calls `--find-sccs` internally. Issues in cycles get `cycle-isolated` status (terminal). Non-cycle issues proceed normally - the whole batch is not aborted.

The `--check-cycles` mode (backward compat) still exits 1 on any cycle; prefer `--find-sccs` for new code.

## Initial status assignment

After DAG construction, `orch_init` assigns initial status:

| Condition | Initial status |
|-----------|---------------|
| Issue in SCC cycle | `cycle-isolated` |
| Has in-batch deps (hard or soft) | `blocked` |
| No in-batch deps, has cross-area hard deps | `blocked-external` |
| No deps (or only soft cross-area) | `pending` |

Issues already in `.workspace/pipeline/{area}/issue-N.state.json` -> skip (already running).

## Dependency satisfaction and unblocking

`orch_unblock()` is called on every completion event. For each `blocked` issue:

1. Any dep still non-terminal -> remain `blocked`
2. All deps terminal, >= 1 hard dep failed -> `blocked-failed-dependency`
3. All deps terminal, no hard failures -> check cross-area hard deps:
   - Has cross-area hard deps -> `blocked-external`
   - No cross-area hard deps -> `pending`

Soft dep failures are ignored (treated as satisfied).

`skipped_dep_failed` is a legacy terminal status kept for backward compat with existing state files. It is equivalent to `blocked-failed-dependency`.

## Edge cases

- **Issue not in batch**: Out-of-batch deps are filtered from the DAG. A warning is logged; the issue proceeds as if that dependency doesn't exist.
- **Self-dependency**: `dag[N]` containing N itself -> caught by SCC detection -> `cycle-isolated`.
- **Empty `### Dependencies` section**: Treated as no dependencies -> `pending`.
- **Mixed in-batch + cross-area hard**: Issue is `blocked` initially; after in-batch deps resolve, becomes `blocked-external` if all in-batch satisfied.
