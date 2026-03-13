# Findings 019 - Tarjan SCC vs Kahn for dependency cycle quarantine

**Date**: 2026-03-14
**Tags**: #orchctl #cycle-detection #tarjan #scc #scheduling

## Context

Issue #100 added a cycle-quarantine pass to `orchctl reconcile`. The initial approach used Kahn's topological sort: nodes that could not reach indegree 0 after full processing were considered cycle members. This turned out to be too broad.

## Problem with Kahn's algorithm

Kahn's marks a node as "stuck" when *any* predecessor is stuck. Consider:

```
A <-> B   (A and B form a 2-cycle)
C -> A    (C depends on A)
```

Kahn's never reduces A or B to indegree 0, so C is also stuck - even though C is not part of a cycle. The reconcile pass would quarantine C unnecessarily, blocking a healthy issue from advancing.

## Solution - Tarjan's SCC

Tarjan's Strongly Connected Components algorithm identifies exactly which nodes belong to cycles:

- An SCC of size > 1 is a multi-node cycle.
- An SCC of size 1 with a self-loop is a self-cycle.
- An SCC of size 1 with no self-loop is a DAG node - not quarantined.

The implementation uses forward adjacency (issue → its dependencies). Only issues inside SCCs matching the cycle criteria are moved to `cycle-isolated`; downstream issues like C above remain `blocked` and are processed normally by `_unblock_pass`.

## Key implementation detail - snapshot vs re-read

After `_cycle_quarantine_pass` transitions some issues to `cycle-isolated`, the per-pass `issues_by_state` snapshot should NOT be re-read before `_dispatch_pass`. Re-reading would surface issues that `_mark_complete_pass` moved to `pending` in the same pass, violating the single-pass contract. Instead, `_unblock_pass` performs a lightweight per-issue DB state check (SELECT state) to skip any issues that the cycle pass already transitioned.

## Rate-limit detection scope

Rate-limit handling (`_is_rate_limit_error` / `_handle_rate_limit_error`) is intentionally wired only in `_discovery_pass`. Dispatch and heartbeat paths use shell invocations that surface transient errors as non-zero exit codes without a parseable 429 body, making generic backoff error-prone. The scope decision is documented in the `_is_rate_limit_error` docstring. If dispatch-path rate limits become a recurring issue a follow-up task should add per-path detection.

## Exponential backoff design

- Config keys: `rate_limit_backoff_base_s` (default 60s), `infra_degraded_threshold` (default 5).
- Per-area state: `{area}.backoff_count`, `{area}.backoff_until`, `{area}.infra_degraded`.
- `cmd_resume` clears all three keys so the area re-enters normal exponential-backoff on the next rate-limit event.
- `_check_and_release_backoff` auto-resumes when `backoff_until` has elapsed; if the timestamp is unparseable it clears all backoff state to prevent a silent permanent pause.

## References

- Issue #100, PR #202
