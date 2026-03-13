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
