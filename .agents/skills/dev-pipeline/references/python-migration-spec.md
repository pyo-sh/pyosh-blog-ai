# dev-pipeline Python migration spec (frozen)

## What is being migrated

All helper functions from `pipeline-helpers.sh` (950 lines) are being re-implemented
as a Python package at `.agents/skills/dev-pipeline/scripts/dev_pipeline/`.

### Functions migrated to Python

| Bash function | Python module | Python name |
|---|---|---|
| `pipeline_state_path` | `paths` | `pipeline_state_path()` |
| `pipeline_log_path` | `paths` | `pipeline_log_path()` |
| `pipeline_err_path` | `paths` | `pipeline_err_path()` |
| `pipeline_headless_meta_path` | `paths` | `pipeline_headless_meta_path()` |
| `pipeline_message_path` | `paths` | `pipeline_message_path()` |
| `pipeline_worktree_path` | `paths` | `pipeline_worktree_path()` |
| `pipeline_resolve_worktree_path` | `paths` | `resolve_worktree_path()` |
| `pipeline_init` | `paths` | `pipeline_init()` |
| `pipeline_state_read` | `state_store` | `state_read()` |
| `pipeline_state_write` | `state_store` | `state_write()` |
| `pipeline_state_update` | `state_store` | `state_update()` |
| `pipeline_state_delete` | `state_store` | `state_delete()` |
| `pipeline_log_transition` | `state_store` | `log_transition()` |
| `pipeline_recovery_log` | `state_store` | `recovery_log_append()` |
| `pipeline_stage_retry` | `state_store` | `stage_retry()` |
| `gh_check_review_exists` | `github_client` | `check_review_exists()` |
| `gh_fetch_review` | `github_client` | `fetch_review()` |
| `gh_check_new_commits` | `github_client` | `check_new_commits()` |
| `gh_fetch_review_comments` | `github_client` | `fetch_review_comments()` |
| `gh_merge_pr_squash` | `github_client` | `merge_pr_squash()` |
| `gh_post_review_comment` | `github_client` | `post_review_comment()` |
| `gh_post_pr_comment` | `github_client` | `post_pr_comment()` |
| `gh_get_pr_state` | `github_client` | `get_pr_state()` |
| `gh_get_pr_base_ref` | `github_client` | `get_pr_base_ref()` |
| `git_fetch` | `git_ops` | `fetch()` |
| `git_rebase` | `git_ops` | `rebase()` |
| `git_merge_no_edit` | `git_ops` | `merge_no_edit()` |
| `git_push_safely` | `git_ops` | `push_safely()` |
| `git_worktree_remove` | `git_ops` | `worktree_remove()` |
| `pipeline_dispatch_review` | `review_runner` | `dispatch_review()` |
| `pipeline_dispatch_claude_review` | `review_runner` | `_dispatch_claude()` |
| `pipeline_dispatch_codex_review` | `review_runner` | `_dispatch_codex()` |
| `pipeline_parse_review_body` | `review_normalizer` | `parse_review_body()` |
| `pipeline_merge_lock_acquire` | `merge_lock` | `MergeLock.acquire()` |
| `pipeline_merge_lock_release` | `merge_lock` | `MergeLock.release()` |
| `pipeline_format_escalation` | `controller` | `format_escalation()` |
| `pipeline_merge_pr` | `controller` | `merge_pr()` |
| `pipeline_cleanup` | `controller` | `cleanup()` |

## Migration complete

All `pipeline-helpers.sh` functions have been migrated to Python. The shell file
has been removed. `SKILL.md` now calls the Python CLI directly.

## State schema version 2 (frozen)

The JSON state file must match this exact camelCase schema:

```json
{
  "version": 2,
  "issue": 42,
  "area": "client",
  "pr": 129,
  "branch": "feat/issue-42",
  "paths": {
    "skillCwd": "/workspace",
    "repoDir": "/workspace/client",
    "worktreeDir": "/workspace/.workspace/worktrees/client/issue-42"
  },
  "step": "review_dispatch",
  "lastReviewId": 0,
  "lastCommitSha": "abc123",
  "skipReview": false,
  "reviewResolveRound": 0,
  "maxReviewResolveRounds": 5,
  "stageRetries": {
    "build": 0,
    "review_dispatch": 0,
    "review_wait": 0,
    "review_process": 0,
    "resolve": 0,
    "merge": 0,
    "log": 0
  },
  "maxStageRetries": 3,
  "reviewJob": {
    "runId": "",
    "status": "idle",
    "startedAt": null,
    "finishedAt": null,
    "tool": "",
    "model": ""
  },
  "transitionLog": [],
  "recoveryLog": [],
  "updatedAt": null
}
```

**Schema is frozen at version 2.** Do not add fields without bumping the version.

## Review format contract

A review is valid only when its body contains:

1. A `## Review Summary` header (level 2, exact spelling).
2. Sections `### Critical`, `### Warning`, and `### Suggestion` (or `### Suggestions`).
3. Numbered items (`1.`, `2.`, …) within each section counted as issues.

`parse_review_body()` raises `ValueError` when the `## Review Summary` header is absent.

## Failure / retry / escalation rules

- Each pipeline stage has a retry counter in `stageRetries`.
- `stage_retry()` increments the counter and returns `True` if retries remain,
  `False` when `maxStageRetries` (default: 3) is reached.
- On max retries, `format_escalation()` produces a human-readable message containing:
  - current state (step, PR, branch, round),
  - last transition,
  - stage-specific recovery log,
  - worktree and repo paths,
  - manual resume command.
- Escalation messages are surfaced to the operator; the pipeline halts.

## Package layout

```
.agents/skills/dev-pipeline/
  scripts/
    dev_pipeline/
      __init__.py
      __main__.py
      cli.py
      command_runner.py
      controller.py
      git_ops.py
      github_client.py
      merge_lock.py
      models.py
      paths.py
      review_normalizer.py
      review_runner.py
      state_store.py
    pyproject.toml
  tests/
    __init__.py
    conftest.py
    test_controller.py
    test_merge_lock.py
    test_models.py
    test_paths.py
    test_review_normalizer.py
    test_state_store.py
  references/
    python-migration-spec.md  (this file)
  SKILL.md
```
