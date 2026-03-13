# Progress 2026-03-14

## orchctl dashboard / webhook / notification (#105, PR #200)

Stage 4 observability feature: event log, webhook dispatch, and CLI commands so operators can query orchestrator lifecycle events in real time and receive HTTP notifications on key state changes.

### Changes merged

- **`db/schema.py`** - migration v15: `events` append-only table (`area`, `issue_id` FK nullable, `event_type`, `payload` JSON, `created_at`); indexes on `area`, `issue_id`, `event_type`, `created_at`; webhook config defaults (`webhook_url`, `webhook_enabled`, `webhook_events`)
- **`events.py`** (new) - `emit_event(conn, event_type, ...)`: guards `conn.in_transaction` to prevent premature commit, inserts event row, fires `_maybe_dispatch_webhook`; `dispatch_webhook(url, payload_json)`: urllib POST with 5-second timeout; `_fire` / `_start_webhook_thread`: non-daemon thread (process stays alive up to 5 s) with stderr notice and failure logging; `_maybe_dispatch_webhook`: enabled/URL/event-type filter before dispatch; five `EVENT_*` constants
- **`commands/events.py`** (new) - `orchctl events list`: area/type/limit filters with paired `(predicate, value)` tuple structure to keep WHERE clause safe; JSON output flag
- **`commands/notify.py`** (new) - `orchctl notify status` (JSON or text), `orchctl notify set` (atomic single-commit upsert for url/enable/events), `orchctl notify test` (scheme-validated POST with dispatch_webhook)
- **`cli.py`** - registered `events` and `notify` command groups
- **`tests/test_events.py`** (new) - 33 tests: emit_event row insertion, nullable fields, webhook enable/filter/block, failure stderr logging (sync `_start_webhook_thread` patch for capsys), `in_transaction` guard, `dispatch_webhook` success/HTTP error/network error, CLI `events list` filters/limit/JSON, `notify status/set/test` including scheme validation and atomicity
- **`tests/test_multi_area.py`** - `test_latest_version_is_15` (rebased from 14 after upstream conflict with v14 cycle-quarantine migration)
- **554 tests** passing

### Key design decisions

- `emit_event` takes a shared `conn` and calls `conn.commit()` internally; callers must not pass a connection with pending DML (`in_transaction` guard fails fast). Design note documented: atomic state-change + event emission is not possible with this interface - future integration into the orchestrator hot path should accept `db_path` for an independent connection.
- Non-daemon webhook thread chosen over daemon to prevent silent notification loss in short-lived CLI processes; documented 5-second exit delay tradeoff.
- `_start_webhook_thread` extracted as a module-level function for test patching (avoids threading/capsys race in unit tests).
- WHERE clause in `events list` uses paired `(predicate_literal, value)` tuples so only fixed string constants are composed into the query string - all values are bound via `?` parameters.
- Schema conflict with upstream v14 (cycle-quarantine) resolved by renumbering events migration to v15.

### Review rounds

- Round 1 (WARNING x2, SUGGESTION x1): webhook delivery silently swallowed, `--url` accepted any scheme, `# type: ignore` on `lastrowid` - stderr logging, scheme validation, explicit RuntimeError guard added
- Round 2 (WARNING x1, SUGGESTION x2): `notify test --url` skipped scheme validation, `assert` stripped by `-O`, missing `idx_events_issue_id` - consistent validation, `if/raise`, index added
- Round 3 (WARNING x2, SUGGESTION x2): `conn.commit()` premature-commit risk, synchronous webhook blocks hot path - `in_transaction` guard added, daemon thread → non-daemon thread with `_start_webhook_thread`/`_fire` extraction; `notify set` made atomic (single commit)
- Round 4 (WARNING x2, SUGGESTION x2): daemon thread killed on exit, f-string WHERE injection risk - non-daemon thread, paired-tuple WHERE builder, design-limitation docstring
- Round 5 (WARNING x3, SUGGESTION x1): `issue_id` absent from webhook body, atomicity gap re-raised for visibility, exit delay undocumented - `issue_id` added to body, dispatch notice printed to stderr, docstring updated
- Round 6 (CLEAN): approved and merged

## orchctl git conflict rebase playbook (#99, PR #201)

Stage 3 self-healing playbook: `git_conflict` failures now trigger automated rebase repair attempts with PR/branch/conflict context, and create a blocker GitHub issue after the rebase budget is exhausted.

### Changes merged

- **`reconcile.py`** - `_run_git_rebase_playbook(conn, area, number, terminal_json, *, pid, owns_lease)`: parses PR number and conflict reason from terminal_json, resolves PR head branch via `get_pr_branch()`, renews lease before the second sequential gh call, posts rebase-attempt context comment (with conflict reason and branch name) in the within-budget branch; `_create_git_rebase_blocker_issue(conn, area, issue_id, number, retry_count, terminal_json)`: queries terminal attempts, builds conflict history, creates blocker issue (with 'blocker' label and requeue instructions), posts blocker reference comment on original issue; `_next_action_to_state()` now calls both functions for `FailureClass.GIT_CONFLICT` in the within-budget and budget-exhausted branches respectively
- **`tests/test_git_rebase_playbook.py`** (new) - 14 tests: next_action routing, within-budget rebase scheduling, budget exhaustion (blocker created + referenced in comment), playbook not called on exhaustion, comment with PR+reason/branch/no-reason/no-PR, lease renewal gating, blocker body conflict history, dry-run skip, requeue instructions in body
- **488 tests** passing

### Key design decisions

- Follows the same pattern as `_run_ci_repair_playbook` / `_create_ci_blocker_issue` (#98): orchestrator posts context + re-queues; re-dispatched worker performs the actual git rebase and test re-execution
- Lease renewal placed between `get_pr_branch()` and `post_issue_comment()` to prevent expiry from cumulative sequential gh call latency

## orchctl CI failure repair + blocker issue playbook (#98, PR #199)

Stage 3 self-healing playbook: `deterministic_test_failure` now triggers automated repair attempts with CI log context rather than immediate escalation, and creates a blocker GitHub issue after the repair budget is exhausted.

### Changes merged

- **`models.py`** - `DETERMINISTIC_TEST_FAILURE` next action changed from `ESCALATE` to `REPAIR`
- **`github.py`** - added `fetch_ci_logs(repo, branch)` (gh run list + gh run view --log-failed), `get_pr_branch(repo, pr_number)` (gh pr view), `create_issue(repo, title, body, labels)` (gh issue create)
- **`reconcile.py`** - `_run_ci_repair_playbook(conn, area, number, terminal_json, *, pid, owns_lease)`: collects CI logs from the PR head branch, renews lease before the second sequential gh call, posts repair context comment (with log tail) only when a repair will actually be re-queued (within-budget branch of `_next_action_to_state`); `_create_ci_blocker_issue(conn, area, issue_id, number, retry_count, terminal_json)`: queries terminal attempts (`status IN ('failed','timed-out')`), builds failure history, creates blocker issue (with 'blocker' label), posts blocker reference comment on original issue; module-level `import json`; `post_issue_comment` calls wrapped in try/except; `_next_action_to_state` accepts `terminal_json`, `pid`, `owns_lease` keyword args
- **`db/schema.py`** - v13 migration: `INSERT OR IGNORE` ensures key exists on fresh installs, then `json_set` patches `deterministic_test_failure: 2` into `retry_budget_by_class`; migration comment documents 'blocker' label prerequisite and `gh label create` command
- **`tests/test_ci_repair_playbook.py`** (new) - 10 tests: next_action routing, within-budget repair scheduling (assert_called_once for playbook), budget exhaustion (blocker created + referenced in comment), playbook not called on exhaustion, CI log comment with/without logs, no-PR-number fallback, blocker body failure history, dry-run skip
- **`tests/test_failure_classifier.py`** - `DETERMINISTIC_TEST_FAILURE` expected action updated to `REPAIR`
- **`tests/test_multi_area.py`** - schema version assertion updated to 13
- **474 tests** passing

### Key design decisions

- Repair playbook called only inside the within-budget branch - no misleading "repair scheduled" comment when budget is already exhausted
- Lease renewal placed between `get_pr_branch` and `fetch_ci_logs` calls - prevents expiry from cumulative gh subprocess timeouts (each up to 30 s)
- `create_issue` returns None on gh failure; `post_issue_comment` wrapped in try/except - all GitHub side-effects are non-fatal, reconcile pass never aborted
- Attempt history query restricted to `status IN ('failed', 'timed-out')` - excludes both non-terminal and successful `completed` rows
- v13 migration uses `INSERT OR IGNORE` before UPDATE to handle fresh installs where `retry_budget_by_class` was never seeded

### Review rounds

- Round 1 (codex, failed_parse - CRITICAL x2): repair playbook called after budget exhausted (misleading comment), no lease renewal around sequential gh calls - both fixed
- Round 2 (WARNING x1 + SUGGESTION x1): `post_issue_comment` not wrapped in try/except; `import json as _json` inline - module-level import added, both calls wrapped
- Round 3 (SUGGESTION x1 + INFO x1): attempt history query used NOT IN excluding only 'created'/'running'; misleading OR assertion in test - positive IN filter and test assertion fixed
- Round 4 (WARNING x2 + SUGGESTION x1): `assert_called_once` missing for playbook within budget; 'blocker' label undocumented; query included 'completed' success rows - all fixed
- Round 5 (CLEAN): approved and merged

## Agent tracker: read-only UI + footer semantics (#114, PR #198)

Stage 3 of the agent-tracker series. The tmux dashboard now consumes the Python backend normalized export instead of calling `lib/collect.sh` directly, and footer status aggregation correctly separates fault/unknown/stale from idle.

### Changes merged

- **`agent-tracker.sh`** - spawns Python backend daemon on startup (`python3 -m backend --interval $INTERVAL`); main loop reads from `current.json` export file; PYTHONPATH prepended (not overwritten); cleanup() waits for backend PID; startup liveness poll (5x100 ms) warns on early exit
- **`lib/render.sh`** - separate `n_fault` / `n_unknown` counters (no longer merged into `n_idle`); footer shows dead-orch count; `.orchestrators` key supported (Python backend v1 export); `.orchestrator` legacy key fallback retained via `// .orchestrator // []`; null-area guard in dead-orch jq filter
- **`lib/collect.sh`** - unchanged; preserved for reference but no longer called by the UI
- **`tests/test-footer-semantics.sh`** (new) - 23 tests covering fault/unknown/stale separation, null-area filtering, and both key names for dead-orch counting

### Key design decisions

- **Daemon model**: `agent-tracker.sh` starts the backend as a child process and reads from its output file; coupling `--interval` to `$INTERVAL` keeps display refresh and export cadence in sync
- **Backward compat**: render.sh accepts both `.orchestrators` (Python backend) and `.orchestrator` (legacy bash snapshot) via jq `//` fallback, applied consistently at all three call sites
- **Pre-increment vs post-increment**: `(( ++var ))` required in tests under `set -euo pipefail` since `(( 0 ))` exits with code 1

### Review rounds

- Round 1 (SUGGESTION): silent backend failure with no user warning - added startup liveness check
- Round 2 (WARNING): PYTHONPATH clobber, hardcoded 0.5 s sleep, cleanup not waiting for backend - all fixed
- Round 3 (WARNING): `(( n_total++ ))` post-increment breaks tests under set -e; `grep -c .` counting null jq output - fixed with pre-increment and null-area jq guard
- Round 4 (SUGGESTION only): test filter inconsistency, `if ! $_alive` idiom, interval comment - all applied; auto-merged

## orchctl history / audit query (#103, PR #194)

Implemented Stage 4 observability feature: persistent attempt history log and `orchctl history` query command for failure pattern analysis.

### Changes merged

- **`history.py`** (new) - `AttemptRecord` dataclass, append-only JSONL log at `.workspace/pipeline/history.jsonl`, `history_read()` with area/issue/since/until filters, `history_stats()` (outcome/failure_class/area/tool breakdowns), `history_patterns()` (repeated failure_class frequency, repeated issue failures, hourly failure distribution), table and JSON formatters
- **`steps.py`** - `step_log_finalize` appends success record before state deletion; `getattr` guard for `recovery_log`
- **`cli.py`** - `history` subcommand (`--mode list|stats|patterns`, `--format table|json`, `--area`, `--issue`, `--since`, `--until`); `history-record` subcommand for manual failure/escalation recording; `cmd_escalation` auto-records escalated outcomes; `_derive_failure_class()` shared helper extracts failure class conditionally based on pipeline step (review/resolve stages only)

### Key design decisions

- **JSONL append-only**: no lock needed for reads; O_APPEND writes are safe for short lines on Linux
- **Auto-record on success and escalation**: `step_log_finalize` (success) and `cmd_escalation` (escalated) are the two terminal outcome paths; `history-record` command available for manual recording
- **Failure class scoped to review stages**: `_derive_failure_class` returns `review_job.status` only for `review_dispatch/review_wait/review_process/resolve` steps; build/push stage escalations record `""` to avoid misleading data
- **Date filter boundary**: `--until YYYY-MM-DD` normalizes to `T23:59:59Z` to include the full boundary day

### Review rounds

- Round 1 (WARNING): unused `import tempfile`, misleading PIPE_BUF comment, unused `lineno` in `history_read` - all removed/fixed
- Round 2 (WARNING): `cmd_history_record` missing try/except around `state_exists` branch; `--failure-class` silently ignored when state exists - both fixed
- Round 3 (WARNING): `history_read` missing `encoding="utf-8"`; `--until YYYY-MM-DD` excluded boundary date - fixed
- Round 4 (WARNING): escalation auto-record added; O_APPEND comment softened; `recovery_log` getattr guard added; lambda E731 removed
- Round 5 (WARNING): `review_job.tool/model` null guard in `from_state`; `_derive_failure_class` extracted; `history_read` encoding fix; lambda cleanup
- Round 6 (round_limit, user approved continue): applied null guard + shared helper; further fixes
- Round 7 (SUGGESTION only): `format_table` `finished_at[:19]` cosmetic clip; stateless `history-record` success outcome clears failure_class - auto-merged

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

## orchctl cycle quarantine + rate limit (#100, PR #202)

Two self-healing playbooks added to the orchctl reconcile loop.

### Changes merged

- **`db/schema.py`** - migration v14: recreates issues table with `cycle-isolated` in the state CHECK constraint; adds `rate_limit_backoff_base_s=60` and `infra_degraded_threshold=5` config defaults
- **`models.py`** - `IssueState.CYCLE_ISOLATED = "cycle-isolated"` added; `BLOCKED → CYCLE_ISOLATED` and `CYCLE_ISOLATED → PENDING` transitions; `cycle-isolated` added to `TERMINAL_ISSUE_STATES`
- **`commands/reconcile.py`** - `_cycle_quarantine_pass`: Tarjan SCC-based cycle detection, quarantines only cycle members (not downstream dependents), posts GitHub comment (non-fatal); `_is_rate_limit_error` / `_handle_rate_limit_error`: exponential backoff (base_s * 2^(n-1), capped at 3600s), infra-degraded threshold, area pause; `_check_and_release_backoff`: auto-resume when window elapsed, full backoff-state clear on corrupt timestamp; `_tarjan_cycle_members`: recursive Tarjan SCC, forward adjacency, self-loop detection; pass order: check_backoff → observe → discovery → mark_complete → heartbeat → **cycle_quarantine** → unblock → dispatch
- **`commands/control.py`** - `cmd_resume` clears `infra_degraded`, `backoff_count`, `backoff_until` in addition to `paused`; `cycle-isolated` added to `_REQUEUEABLE` set in `cmd_requeue`
- **`tests/test_cycle_ratelimit.py`** (new) - 33 tests: IssueState model, schema v14, `_is_rate_limit_error`, `_handle_rate_limit_error`, `_check_and_release_backoff`, `_cycle_quarantine_pass` (correct member isolation, non-members unaffected, post-quarantine unblock, non-fatal comment failure), control requeue of cycle-isolated
- **`tests/test_multi_area.py`** - `test_latest_version_is_14` (was 13); 507 tests total

### Key decisions

- Tarjan SCC over Kahn's algorithm - Kahn incorrectly quarantines downstream dependents of cycle members; Tarjan identifies only actual cycle participants (SCC size > 1 or self-loop)
- Rate-limit detection scoped to `_discovery_pass` only - dispatch/heartbeat use shell invocations that surface 429s as generic non-zero exit codes; scope decision documented in `_is_rate_limit_error` docstring
- Per-issue DB state check in `_unblock_pass` (not snapshot re-read) - avoids single-pass dispatch contract violation

### Finding

- findings.019: Tarjan SCC vs Kahn for dependency cycle quarantine
