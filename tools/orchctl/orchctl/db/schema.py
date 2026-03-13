"""SQLite schema definitions."""

# Each entry: (version, sql)
MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            id      INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS issues (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            area            TEXT    NOT NULL,
            number          INTEGER NOT NULL,
            state           TEXT    NOT NULL DEFAULT 'pending'
                                    CHECK(state IN ('pending','running','done','failed','blocked')),
            dependency_type TEXT    NOT NULL DEFAULT 'none',
            retry_budget    INTEGER NOT NULL DEFAULT 3,
            failure_class   TEXT,
            escalation      TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (area, number)
        );

        CREATE TRIGGER IF NOT EXISTS issues_updated_at
        AFTER UPDATE ON issues
        BEGIN
            UPDATE issues SET updated_at = datetime('now') WHERE id = NEW.id;
        END;

        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id      TEXT    PRIMARY KEY,
            issue_id        INTEGER NOT NULL REFERENCES issues(id),
            pid             INTEGER,
            pgid            INTEGER,
            started_at      TEXT,
            finished_at     TEXT,
            status          TEXT    NOT NULL DEFAULT 'running'
                                    CHECK(status IN ('running','success','failure','cancelled')),
            terminal_json   TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_attempts_issue_id ON attempts(issue_id);

        CREATE TABLE IF NOT EXISTS heartbeats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id  TEXT    NOT NULL REFERENCES attempts(attempt_id),
            timestamp   TEXT    NOT NULL DEFAULT (datetime('now')),
            signals     TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_heartbeats_attempt_id ON heartbeats(attempt_id);

        CREATE TABLE IF NOT EXISTS leases (
            area        TEXT    PRIMARY KEY,
            holder_pid  INTEGER NOT NULL,
            acquired_at TEXT    NOT NULL DEFAULT (datetime('now')),
            expires_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS config (
            key         TEXT    PRIMARY KEY,
            value       TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        INSERT INTO config (key, value) VALUES
            ('max_concurrent',  '4'),
            ('retry_budget',    '3'),
            ('heartbeat_ttl',   '120'),
            ('lease_ttl',       '60')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
    (
        2,
        """
        -- Recreate issues with full state vocabulary.
        -- Old states: pending, running, done, failed, blocked
        -- New states: pending, dispatched, completed, failed-terminal,
        --             needs-human, blocked-external, cancelled,
        --             blocked, blocked-failed-dependency
        CREATE TABLE issues_v2 (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            area            TEXT    NOT NULL,
            number          INTEGER NOT NULL,
            state           TEXT    NOT NULL DEFAULT 'pending'
                                    CHECK(state IN (
                                        'pending',
                                        'dispatched',
                                        'completed',
                                        'failed-terminal',
                                        'needs-human',
                                        'blocked-external',
                                        'cancelled',
                                        'blocked',
                                        'blocked-failed-dependency'
                                    )),
            dependency_type TEXT    NOT NULL DEFAULT 'none'
                                    CHECK(dependency_type IN ('none','soft','hard')),
            retry_budget    INTEGER NOT NULL DEFAULT 3,
            failure_class   TEXT,
            escalation      TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (area, number)
        );

        INSERT INTO issues_v2 (id, area, number, state, dependency_type,
                               retry_budget, failure_class, escalation,
                               created_at, updated_at)
        SELECT
            id,
            area,
            number,
            CASE state
                WHEN 'running' THEN 'dispatched'
                WHEN 'done'    THEN 'completed'
                WHEN 'failed'  THEN 'failed-terminal'
                ELSE state
            END,
            dependency_type,
            retry_budget,
            failure_class,
            escalation,
            created_at,
            updated_at
        FROM issues;

        DROP TRIGGER IF EXISTS issues_updated_at;
        DROP TABLE issues;
        ALTER TABLE issues_v2 RENAME TO issues;

        CREATE TRIGGER issues_updated_at
        AFTER UPDATE ON issues
        BEGIN
            UPDATE issues SET updated_at = datetime('now') WHERE id = NEW.id;
        END;

        -- Recreate attempts with new status vocabulary.
        -- Old statuses: running, success, failure, cancelled
        -- New statuses: created, running, completed, failed, timed-out
        -- Note: old 'cancelled' is mapped to 'failed' because the new vocabulary
        -- does not distinguish cancellation from failure at the attempt level.
        -- Downstream code must not rely on distinguishing these for pre-v2 rows.
        CREATE TABLE attempts_v2 (
            attempt_id      TEXT    PRIMARY KEY,
            issue_id        INTEGER NOT NULL REFERENCES issues(id),
            pid             INTEGER,
            pgid            INTEGER,
            started_at      TEXT,
            finished_at     TEXT,
            status          TEXT    NOT NULL DEFAULT 'created'
                                    CHECK(status IN (
                                        'created',
                                        'running',
                                        'completed',
                                        'failed',
                                        'timed-out'
                                    )),
            terminal_json   TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        INSERT INTO attempts_v2 (attempt_id, issue_id, pid, pgid,
                                  started_at, finished_at, status,
                                  terminal_json, created_at)
        SELECT
            attempt_id,
            issue_id,
            pid,
            pgid,
            started_at,
            finished_at,
            CASE status
                WHEN 'success'   THEN 'completed'
                WHEN 'failure'   THEN 'failed'
                WHEN 'cancelled' THEN 'failed'
                ELSE status
            END,
            terminal_json,
            created_at
        FROM attempts;

        DROP TABLE attempts;
        ALTER TABLE attempts_v2 RENAME TO attempts;

        CREATE INDEX idx_attempts_issue_id ON attempts(issue_id);

        CREATE INDEX idx_issues_state ON issues(state);
        """,
    ),
    (
        3,
        """
        -- v3: add heartbeat_at to leases; unique partial index on active attempts
        ALTER TABLE leases ADD COLUMN heartbeat_at TEXT;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_attempts_active_unique
        ON attempts(issue_id)
        WHERE status = 'running';
        """,
    ),
    (
        4,
        """
        -- v4: add max_open_pr and drain_mode config defaults
        INSERT INTO config (key, value) VALUES
            ('max_open_pr', '2'),
            ('drain_mode',  'false')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
    (
        5,
        """
        -- v5: issue discovery + configurable scope
        INSERT INTO config (key, value) VALUES
            ('discovery_enabled',    'false'),
            ('scope_include_labels', '[]'),
            ('scope_exclude_labels', '[]'),
            ('scope_milestone',      ''),
            ('scope_allow_unassigned', 'true')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
    (
        6,
        """
        -- v6: policy config + merge gate + guardrails

        -- retry_count tracks how many times an issue has been re-dispatched
        ALTER TABLE issues ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;

        -- merge_state tracks per-issue merge gate status
        ALTER TABLE issues ADD COLUMN merge_state TEXT NOT NULL DEFAULT 'none'
            CHECK(merge_state IN ('none', 'eligible', 'pending', 'done', 'rejected'));

        -- Policy config defaults (scope keys already in v5)
        INSERT INTO config (key, value) VALUES
            ('merge_enabled',              'false'),
            ('merge_require_checks',       'true'),
            ('merge_require_clean_rebase', 'true'),
            ('repo_allowlist',             ''),
            ('protected_branches',         'main'),
            ('max_concurrent_repair',      '1'),
            ('scheduler_overlap',          'false'),
            ('dangerous_tools',            ''),
            ('retry_budget_by_class',      '{}')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
    (
        7,
        """
        -- v7: legacy cutover support
        -- {area}.legacy_mode = 'true' means the legacy shell orchestrator is still active
        -- for that area.  orchctl control cutover <area> sets this to 'false'.
        -- The sentinel path is stored so rollback can locate and remove it.
        INSERT INTO config (key, value) VALUES
            ('client.legacy_mode',   'true'),
            ('server.legacy_mode',   'true'),
            ('workspace.legacy_mode', 'true')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
    (
        8,
        """
        -- v8: failure classification system
        -- Adds failure_class to attempts so each attempt records its own class.
        -- The issues.failure_class column (added in v1) already tracks the most
        -- recent failure class at the issue level.
        ALTER TABLE attempts ADD COLUMN failure_class TEXT;
        """,
    ),
    (
        9,
        """
        -- v9: stall detection threshold
        -- stall_threshold_s: activity window in seconds for multi-signal stall detection.
        -- Independent of heartbeat_ttl (which governs lease renewal).
        -- Default matches the SIGNAL_THRESHOLD_S constant in orchctl.heartbeat.
        INSERT INTO config (key, value) VALUES
            ('stall_threshold_s', '600')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
    (
        10,
        """
        -- v10: per-class retry budgets for crash/timeout/flaky auto-retry playbook.
        -- Sets default budgets only when the operator has not yet customised the
        -- value (i.e. it is still the empty-dict default from v6).
        INSERT INTO config (key, value) VALUES
            ('retry_budget_by_class',
             '{"infra_crash": 3, "timeout": 3, "flaky_test": 2, "default": 1}')
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
            WHERE value = '{}';
        """,
    ),
    (
        11,
        """
        -- v11: advanced scheduling + admission control
        -- priority: dispatch order weight from the fenced orchestrator block.
        -- Higher values are dispatched first (default 0 = normal priority).
        ALTER TABLE issues ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;

        -- Scheduling policy config defaults.
        -- priority_weight: multiplier for the priority field in the dispatch score.
        -- age_weight:      multiplier for issue age (days) in the dispatch score.
        -- retry_weight:    penalty multiplier for retry_count in the dispatch score.
        -- max_awaiting_merge: stop new dispatches when this many completed issues
        --   still have unmerged PRs (merge_state NOT IN ('done', 'rejected')).
        --   0 = no limit.
        INSERT INTO config (key, value) VALUES
            ('scheduling_priority_weight', '1.0'),
            ('scheduling_age_weight',      '0.1'),
            ('scheduling_retry_weight',    '1.0'),
            ('max_awaiting_merge',         '0')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
    (
        12,
        """
        -- v12: cross-area dependency table.
        --
        -- dependencies: explicit cross-area (and same-area) dependency edges.
        --   issue_id    = the blocked issue
        --   dep_area    = area of the dependency
        --   dep_number  = issue number of the dependency
        --   dep_type    = hard (must complete) | soft (any terminal state unblocks)
        --
        -- The global concurrent-dispatch ceiling was historically stored as
        -- 'max_open_pr'.  Policy YAML accepts both 'global_max' and 'global_quota'
        -- as synonyms; both write to the same 'max_open_pr' config key so that
        -- existing reconcile code continues to work unchanged.
        CREATE TABLE IF NOT EXISTS dependencies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id    INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
            dep_area    TEXT    NOT NULL,
            dep_number  INTEGER NOT NULL,
            dep_type    TEXT    NOT NULL DEFAULT 'hard'
                                CHECK(dep_type IN ('hard', 'soft')),
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (issue_id, dep_area, dep_number)
        );

        CREATE INDEX IF NOT EXISTS idx_dependencies_issue_id ON dependencies(issue_id);
        """,
    ),
    (
        13,
        """
        -- v13: CI failure repair + blocker issue playbook.
        -- Sets the repair budget for deterministic_test_failure to 2 (two repair
        -- attempts before a blocker issue is created and the issue escalates to
        -- needs-human).  Only updates when the existing value does not already
        -- include a deterministic_test_failure entry, so operator customisations
        -- are preserved.
        --
        -- Prerequisite: each target GitHub repo must have a 'blocker' label.
        -- Create it with: gh label create blocker -R <owner/repo> --color e11d48
        --
        -- Ensure the key exists before patching (safe for fresh installs where
        -- retry_budget_by_class was never written to the config table).
        INSERT OR IGNORE INTO config (key, value)
        VALUES ('retry_budget_by_class', '{}');

        UPDATE config
        SET value = json_set(value, '$.deterministic_test_failure', 2)
        WHERE key = 'retry_budget_by_class'
          AND json_extract(value, '$.deterministic_test_failure') IS NULL;
        """,
    ),
    (
        14,
        """
        -- v14: event log + webhook notification support.
        --
        -- events: append-only log of orchestrator lifecycle events.
        --   area       = area the event belongs to (may be NULL for global events)
        --   issue_id   = FK to issues.id (nullable; non-issue events omit this)
        --   event_type = string key, e.g. 'issue_state_changed', 'attempt_started'
        --   payload    = JSON blob with event-specific details
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            area        TEXT,
            issue_id    INTEGER REFERENCES issues(id) ON DELETE SET NULL,
            event_type  TEXT    NOT NULL,
            payload     TEXT    NOT NULL DEFAULT '{}',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_events_area       ON events(area);
        CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

        -- Webhook config defaults.
        -- webhook_url:     HTTP(S) URL to POST events to. Empty = disabled.
        -- webhook_enabled: master switch; 'false' suppresses all outbound calls.
        -- webhook_events:  JSON array of event_type strings to forward.
        --                  Empty array = forward all events.
        INSERT INTO config (key, value) VALUES
            ('webhook_url',     ''),
            ('webhook_enabled', 'false'),
            ('webhook_events',  '[]')
        ON CONFLICT(key) DO NOTHING;
        """,
    ),
]

LATEST_VERSION: int = max(v for v, _ in MIGRATIONS)
