"""
lib/usage_tracker.py — Billable AI event logging + trial gate

Usage in any route:
    from lib.usage_tracker import log_event, check_access

    # Check before doing expensive AI work:
    check_access(conn, user_id)   # raises HTTP 402 if trial expired + unpaid

    # Log after successful AI action:
    log_event(conn, user_id, 'mira_message', context={'tokens': 380})

Event types (defined in usage_event_prices table):
    mira_message    — 2 cents   — one Mira chat exchange
    cv_extraction   — 50 cents  — Adele CV parse
    cover_letter    — 30 cents  — Clara cover letter
    match_report    — 20 cents  — Clara match report
    profile_embed   — 5 cents   — profile embedding refresh

Costs are read live from the DB so they can be changed without a code deploy.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Local cache: event_type → cost_cents, refreshed on first call per process.
# Fine for a long-running server — prices rarely change.
_price_cache: dict[str, int] = {}


def _get_price(conn, event_type: str) -> int:
    """Return cost in cents for event_type. Caches per process."""
    if event_type not in _price_cache:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cost_cents FROM usage_event_prices WHERE event_type = %s",
                (event_type,),
            )
            row = cur.fetchone()
        if row is None:
            logger.warning("Unknown usage event_type %r — defaulting to 0 cents", event_type)
            _price_cache[event_type] = 0
        else:
            _price_cache[event_type] = row["cost_cents"]
    return _price_cache[event_type]


def log_event(
    conn,
    user_id: int,
    event_type: str,
    context: dict[str, Any] | None = None,
    *,
    commit: bool = True,
) -> int:
    """
    Record one billable AI event. Returns the new event_id.

    Never raises — if the insert fails it logs a warning and returns -1
    so the caller's main work is not disrupted.
    """
    import json

    cost = _get_price(conn, event_type)
    ctx_json = json.dumps(context or {})
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usage_events (user_id, event_type, cost_cents, context)
                VALUES (%s, %s, %s, %s)
                RETURNING event_id
                """,
                (user_id, event_type, cost, ctx_json),
            )
            event_id = cur.fetchone()["event_id"]
        if commit:
            conn.commit()
        return event_id
    except Exception as exc:
        logger.warning("usage_tracker: failed to log event %r for user %d: %s", event_type, user_id, exc)
        try:
            conn.rollback()
        except Exception:
            pass
        return -1


def check_access(conn, user_id: int, *, raise_on_block: bool = True) -> bool:
    """
    Return True if the user may use AI features.
    Return False (or raise HTTP 402) if their trial has expired and
    they have not subscribed.

    Logic:
      - Admin users: always allowed
      - subscription_status = 'active': always allowed
      - trial_ends_at IS NULL or trial_ends_at > now(): allowed (still in trial)
      - trial_ends_at <= now() AND subscription_status != 'active': blocked
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT is_admin, subscription_status, trial_ends_at
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="User not found")

    if row["is_admin"]:
        return True

    if row["subscription_status"] == "active":
        return True

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    trial_ends = row["trial_ends_at"]

    # trial_ends_at is timezone-aware from the DB
    if trial_ends is None or trial_ends > now:
        return True  # still in trial

    # Trial expired, not subscribed
    if raise_on_block:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "trial_expired",
                "message": "Your free trial has ended. Please subscribe to continue.",
                "subscribe_url": "/account#subscribe",
            },
        )
    return False


def get_balance(conn, user_id: int) -> dict:
    """
    Return a summary dict for the current user's usage.
    Used by the account page and the live meter in the header.

    Returns:
        {
            "total_spent_cents": 142,
            "unbilled_cents": 80,
            "event_count": 34,
            "trial_active": True,
            "trial_ends_at": "2026-02-28T...",
            "needs_payment": False,
            "subscription_status": "free",
        }
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                total_spent_cents,
                unbilled_cents,
                event_count,
                trial_active,
                trial_ends_at,
                needs_payment,
                subscription_status
            FROM user_trial_balance
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if row is None:
        return {
            "total_spent_cents": 0,
            "unbilled_cents": 0,
            "event_count": 0,
            "trial_active": True,
            "trial_ends_at": None,
            "needs_payment": False,
            "subscription_status": "free",
        }

    result = dict(row)
    # Convert datetime to ISO string for JSON serialisation
    if result.get("trial_ends_at"):
        result["trial_ends_at"] = result["trial_ends_at"].isoformat()
    return result
