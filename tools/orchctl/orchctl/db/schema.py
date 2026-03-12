"""SQLite schema definitions."""

SCHEMA_VERSION = 1

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
]
