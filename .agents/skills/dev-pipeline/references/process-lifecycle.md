# Process lifecycle

## Execution model

Review and resolve run as synchronous `claude -p` subprocesses via `pipeline_run_headless()`. The pipeline AI blocks until the subprocess exits, then checks the GitHub API for results.

```
pipeline_run_headless(workdir, prompt, issue, area, stage)
  -> timeout $SEC claude -p --dangerously-skip-permissions ... "$prompt" > $LOG
  -> returns exit code
```

## Exit codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Check API for result |
| 124 | Timeout (`timeout` command) | Self-heal: retry |
| Other | Error | Check API first (may have succeeded), then self-heal |

## Tool allowlists

| Stage | Tools | Max turns | Timeout |
|-------|-------|-----------|---------|
| review | `Bash,Read,Skill` | 15 | 900s |
| resolve | `Bash,Read,Edit,Write,Grep,Glob,Skill` | 25 | 900s |

## Completion detection

Always check API after subprocess exits, regardless of exit code:
- Review: `pipeline_check_review_exists()` - looks for review body starting with `## Review Summary`
- Resolve: `pipeline_check_new_commits()` - compares latest commit SHA against stored SHA

If API confirms result exists, treat as success even if exit code was non-zero.

## Self-healing

Per-stage retry with `pipeline_stage_retry()`. Max 3 retries per stage. Recovery actions logged to `recoveryLog` in state. On max retries exceeded, escalate to user with `pipeline_format_escalation()`.
