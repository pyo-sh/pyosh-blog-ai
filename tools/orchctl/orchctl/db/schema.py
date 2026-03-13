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
]

LATEST_VERSION: int = max(v for v, _ in MIGRATIONS)
