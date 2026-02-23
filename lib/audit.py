"""
lib/audit.py — Append-only compliance / audit log

Every significant user-data-touching event gets one row in ``yogi_audit_log``.
The table is protected by DB-level rules (no UPDATE / DELETE allowed).

Usage::

    from lib.audit import log_audit_event

    log_audit_event(conn, user_id, actor='adele',
                    event_type='adele_save',
                    detail={'roles': 3, 'phase': 'work_history'})

Actor values:
    'system'  — automated / startup events (login, logout)
    'adele'   — Adele conversational profile builder
    'mira'    — Mira chat assistant
    'yogi'    — the user themselves (CV upload, self-edits)
    'admin'   — manual admin action (freeze, unfreeze)

Event types (extend freely — these are the initial set):
    login               — user authenticated via Google OAuth
    logout              — user cleared session
    cv_upload           — CV text sent to LLM extraction pipeline
    adele_save          — incremental Adele-collected profile saved to DB
    profile_translate   — translation job completed
    profile_embed       — embedding recomputed
    freeze              — admin froze user (LLM access suspended)
    unfreeze            — admin unfroze user
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_audit_event(
    conn,
    user_id: int,
    actor: str,
    event_type: str,
    detail: dict[str, Any] | None = None,
    *,
    commit: bool = True,
) -> int:
    """
    Append one row to ``yogi_audit_log``.

    Never raises — if the insert fails it logs a warning and returns -1
    so the caller's main work is not disrupted.

    Returns the new ``audit_id`` on success, -1 on failure.
    """
    detail_json = json.dumps(detail or {})
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO yogi_audit_log (user_id, actor, event_type, detail)
                VALUES (%s, %s, %s, %s)
                RETURNING audit_id
                """,
                (user_id, actor, event_type, detail_json),
            )
            audit_id: int = cur.fetchone()["audit_id"]
        if commit:
            conn.commit()
        return audit_id
    except Exception as exc:
        logger.warning(
            "audit: failed to log %r for user %d (%s): %s",
            event_type, user_id, actor, exc
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return -1


def get_audit_timeline(
    conn,
    user_id: int,
    limit: int = 100,
) -> list[dict]:
    """
    Return the last ``limit`` audit events for ``user_id``, newest first.
    Safe read — no side effects.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT audit_id, actor, event_type, detail, created_at
                  FROM yogi_audit_log
                 WHERE user_id = %s
                 ORDER BY created_at DESC
                 LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
        return [
            {
                "audit_id":   r["audit_id"],
                "actor":      r["actor"],
                "event_type": r["event_type"],
                "detail":     r["detail"] if isinstance(r["detail"], dict) else {},
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("audit: get_audit_timeline failed for user %d: %s", user_id, exc)
        return []


# ── Prose formatter ──────────────────────────────────────────────────────────

_EVENT_PROSE: dict[str, str] = {
    "login":              "Logged in",
    "logout":             "Logged out",
    "cv_upload":          "Uploaded a CV for extraction",
    "adele_save":         "Adele saved profile data",
    "profile_translate":  "Translated profile to {lang}",
    "profile_embed":      "Profile embedding refreshed",
    "freeze":             "Account frozen by admin",
    "unfreeze":           "Account unfrozen by admin",
}


def event_to_prose(event: dict) -> str:
    """Convert one audit event dict to a human-readable sentence."""
    tmpl = _EVENT_PROSE.get(event["event_type"], event["event_type"])
    try:
        detail = event.get("detail") or {}
        prose = tmpl.format(**detail)
    except (KeyError, TypeError):
        prose = tmpl
    actor = event.get("actor", "system")
    ts = event.get("created_at", "")[:16].replace("T", " ")
    return f"[{ts}] ({actor}) {prose}"
