"""orchctl doctor — validate database consistency."""

import json

import click

from ..db import get_db
from ..db.migrate import run_migrations


def _check_orphan_attempts(conn) -> list[str]:
    rows = conn.execute(
        """
        SELECT a.attempt_id
        FROM attempts a
        LEFT JOIN issues i ON a.issue_id = i.id
        WHERE i.id IS NULL
        """
    ).fetchall()
    return [r["attempt_id"] for r in rows]


def _check_stale_leases(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT area, holder_pid, expires_at
        FROM leases
        WHERE expires_at < datetime('now')
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _check_schema_version(conn) -> int:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if row is None:
        return 0
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    return row[0] if row else 0


@click.command("doctor")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def cmd_doctor(ctx: click.Context, as_json: bool) -> None:
    """Check database consistency and report issues."""
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    run_migrations(conn)

    schema_ver = _check_schema_version(conn)
    orphan_attempts = _check_orphan_attempts(conn)
    stale_leases = _check_stale_leases(conn)
    conn.close()

    findings: list[dict] = []
    if orphan_attempts:
        findings.append({
            "type": "orphan_attempts",
            "count": len(orphan_attempts),
            "ids": orphan_attempts,
        })
    if stale_leases:
        findings.append({
            "type": "stale_leases",
            "count": len(stale_leases),
            "items": stale_leases,
        })

    data = {
        "schema_version": schema_ver,
        "healthy": len(findings) == 0,
        "findings": findings,
    }

    if as_json:
        click.echo(json.dumps(data, indent=2))
    else:
        status = "OK" if data["healthy"] else "ISSUES FOUND"
        click.echo(f"Doctor: {status}  (schema v{schema_ver})")
        for f in findings:
            click.echo(f"  [{f['type']}] count={f['count']}")
