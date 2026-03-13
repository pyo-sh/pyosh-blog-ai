# Progress 2026-03-14

## orchctl advanced scheduling + admission control (#101, PR #196)

Implemented Stage 3 of the orchestrator redesign: priority-based dispatch ordering, configurable scheduling weights, and the `max_awaiting_merge` admission gate.

### Changes merged

- **DB migration v11** - `priority INTEGER NOT NULL DEFAULT 0` column on `issues`; config defaults for all new keys
- **Priority parsing** - `parse_priority_from_body()` extracts `priority: N` from the fenced `orchestrator` block in GitHub issue body; stored at enqueue and refreshed on reopen
- **Dispatch scoring** - `_sort_pending()` sorts pending issues before dispatch using: `priority_weight * priority + age_weight * age_days - retry_weight * retry_count`
- **`max_awaiting_merge` gate** - per-area admission control that blocks new dispatches when completed+unmerged PR count reaches the configured limit
- **`get_config_float`** moved to `db/config.py` alongside `get_config_int`/`get_config_bool`
- **Policy YAML** - new `scheduling:` section (priority/age/retry weights) and `guardrails.max_awaiting_merge`
- **414 tests** passing (37 new in `test_scheduling.py`)

### Review rounds

- Round 1 (WARNING): NULL merge_state SQL semantics in `_count_awaiting_merge`, `datetime.utcnow()` deprecation, stale priority on reopen - all fixed
- Round 2 (WARNING): `_count_awaiting_merge` was global, not per-area - fixed with `area` parameter; `body` fetch comment added
- Round 3 (SUGGESTION only): `get_config_float` moved to `db/config.py`; negative `max_awaiting_merge` clamped to 0; docstring note on non-negative priority constraint

## orchctl multi-area coordination (#104, PR #197)

Implemented Stage 4 of the orchestrator redesign: global quota enforcement, cross-area dependency resolution, and a multi-area scheduler command.

### Changes merged

- **DB migration v12** - `dependencies` table with per-edge `dep_type` (`hard`/`soft`), CASCADE delete, unique constraint on `(issue_id, dep_area, dep_number)`
- **`_resolve_per_edge(dep_rows)`** - per-edge dep_type resolution: blocked if any dep is non-terminal, `blocked-failed-dependency` if any hard dep is non-completed, `pending` otherwise
- **`_unblock_pass`** - uses `dependencies` table for cross-area dep resolution; optimistic unblock when no dep rows exist; unknown deps keep issue blocked
- **Global quota** - `max_open_pr` remains the single DB config key; `global_quota` / `global_max` in policy YAML are synonyms that write to it; `_observe_config` exposes it as `global_quota`; log messages say `"globalQuota=N reached (config key: max_open_pr)"`
- **`reconcile-all` command** (`reconcile_all.py`) - sequential multi-area scheduler sharing one SQLite connection for atomic global quota enforcement; per-area lease acquired before policy load; `--areas` / `--dry-run` / `--policy-file` options
- **Policy YAML** - `concurrency.global_quota` and `concurrency.global_max` use `elif` to avoid double-write to `max_open_pr`
- **396 tests** passing (22 new in `test_multi_area.py`)

### Review rounds

- Round 1 (WARNING): policy double-write when both `global_max` and `global_quota` present - fixed with `elif`; dead `max_open_pr = global_quota` variable in `_dispatch_pass` removed; deferred import of `resolve_blocked_issue` moved to module level then removed
- Round 2 (WARNING): `dependencies.dep_type` fetched but unused - resolution used uniform issue-level `dependency_type`; fixed with `_resolve_per_edge` reading per-edge `dep_type`; `_resolve_deps` wrapper removed
- Round 3 (SUGGESTION only): policy load before lease acquisition in `reconcile_all._reconcile_area` - moved inside try block after `acquire`
- Rebase conflict: another PR added v11 (priority scheduling); our migration renumbered to v12; `test_chaos.py::TestDependencyCycle` updated to insert explicit dep rows instead of relying on old deferred behavior
