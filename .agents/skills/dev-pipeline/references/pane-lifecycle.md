# Pane lifecycle

## Return codes

| Code | stdout | Meaning |
|------|--------|---------|
| 0 | result | Success |
| 1 | `TIMEOUT` | Polling expired |
| 2 | `PANE_DEAD` | Pane process died |
| 3 | `PATH_INVALID` | Working directory not found |
| 4 | `RETRY_FAILED` | Auto-retry also failed |

## Key behaviors

- `pipeline_open_pane_verified()`: validates dir → opens pane → 3s startup check → auto-retries once with path re-resolution on failure
- `pipeline_poll_review()` / `pipeline_poll_commits()`: checks API first (catches normal exit), then pane health. Prevents false PANE_DEAD when task completed normally.
- Auto-retry policy: max 1 retry per pane-open or polling cycle. On retry failure → report to user.
