"""orchctl event log and webhook notification.

Public API
----------
emit_event(conn, event_type, area=None, issue_id=None, payload=None)
    Persist an event row and fire the configured webhook (if enabled).
    The connection must have no active transaction when called.

dispatch_webhook(url, payload_json)
    POST *payload_json* to *url* with a 5-second timeout.
    Returns (ok: bool, status_or_error: str).
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from typing import Any

from .db import get_config, get_config_bool, get_config_json


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

EVENT_ISSUE_STATE_CHANGED = "issue_state_changed"
EVENT_ATTEMPT_STARTED = "attempt_started"
EVENT_ATTEMPT_COMPLETED = "attempt_completed"
EVENT_ATTEMPT_FAILED = "attempt_failed"
EVENT_ESCALATION = "escalation"


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def emit_event(
    conn: sqlite3.Connection,
    event_type: str,
    *,
    area: str | None = None,
    issue_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    """Insert an event row and optionally fire the configured webhook.

    The connection must have no active transaction when called.
    ``emit_event`` calls ``conn.commit()`` internally; passing a connection
    with uncommitted DML would prematurely commit that work.

    Design note: because this function issues its own ``conn.commit()``, the
    event insert cannot be made atomic with a preceding state-change on the
    same connection. A crash between the state-change commit and this call
    will lose the event row. This tradeoff is acceptable for the current
    CLI/observer use-case. If ``emit_event`` is later wired into the
    orchestrator's hot path, consider accepting a ``db_path`` so it can open
    an independent connection.

    Returns the new event *id*.
    """
    if conn.in_transaction:
        raise RuntimeError(
            "emit_event must be called on a connection with no active transaction; "
            "call conn.commit() or conn.rollback() first"
        )

    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    cur = conn.execute(
        "INSERT INTO events (area, issue_id, event_type, payload) VALUES (?, ?, ?, ?)",
        (area, issue_id, event_type, payload_json),
    )
    conn.commit()
    event_id = cur.lastrowid
    if event_id is None:
        raise RuntimeError("INSERT INTO events did not return a lastrowid")

    _maybe_dispatch_webhook(conn, event_type, area, payload or {})
    return event_id


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

def dispatch_webhook(url: str, payload_json: str) -> tuple[bool, str]:
    """POST *payload_json* to *url*.

    Returns (ok, detail) where *detail* is the HTTP status code string on
    success or the error message on failure.
    """
    data = payload_json.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True, str(resp.status)
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _fire(url: str, body: str) -> None:
    """Execute webhook delivery and log failures to stderr."""
    ok, detail = dispatch_webhook(url, body)
    if not ok:
        print(f"[orchctl] webhook delivery failed: {detail}", file=sys.stderr)


def _start_webhook_thread(url: str, body: str) -> None:
    """Start a non-daemon thread to fire the webhook without blocking the caller.

    Non-daemon so the process stays alive (up to the 5-second HTTP timeout)
    until delivery completes. Daemon threads are killed on process exit and
    would silently drop notifications in short-lived CLI invocations.
    """
    threading.Thread(target=_fire, args=(url, body), daemon=False).start()


def _maybe_dispatch_webhook(
    conn: sqlite3.Connection,
    event_type: str,
    area: str | None,
    payload: dict[str, Any],
) -> None:
    """Fire the webhook in a background thread if enabled and event passes the filter."""
    enabled = get_config_bool(conn, "webhook_enabled", default=False)
    if not enabled:
        return

    url = get_config(conn, "webhook_url", default="")
    if not url:
        return

    allowed: list[str] = get_config_json(conn, "webhook_events", default=[])
    if allowed and event_type not in allowed:
        return

    body = json.dumps(
        {"event_type": event_type, "area": area, "data": payload},
        ensure_ascii=False,
    )
    _start_webhook_thread(url, body)
