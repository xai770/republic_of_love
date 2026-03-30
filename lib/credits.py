"""
lib/credits.py — Credit balance operations for the pay-per-deliverable system.

Usage:
    from lib.credits import check_credit, spend_credit, topup_credit, get_credit_balance

    # Pre-check before expensive AI work:
    check_credit(conn, user_id, 'match_report')  # raises HTTP 402 if insufficient

    # Deduct after successful deliverable:
    spend_credit(conn, user_id, cost_cents=20, description='Clara match report',
                 deliverable_ref=f'clara:{match_id}')

    # Top-up from Stripe:
    topup_credit(conn, user_id, amount_cents=1000, stripe_pi='pi_xxx')

Credit prices are read from usage_event_prices (same table usage_tracker uses).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ── cache ────────────────────────────────────────────────────────────────
_price_cache: dict[str, int] = {}


def _get_price(conn, event_type: str) -> int:
    """Return price in cents for a deliverable type. Cached per process."""
    if event_type not in _price_cache:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cost_cents FROM usage_event_prices WHERE event_type = %s",
                (event_type,),
            )
            row = cur.fetchone()
        _price_cache[event_type] = row["cost_cents"] if row else 0
    return _price_cache[event_type]


# ── public API ───────────────────────────────────────────────────────────

def get_credit_balance(conn, user_id: int) -> dict:
    """
    Return current credit state for a user.

    Returns:
        {
            "balance_cents": 500,
            "balance_eur": "5.00",
            "badge": "🌿",
            "subscription_tier": "free",
            "is_sustainer": False,
        }
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT credit_balance, subscription_tier
            FROM users WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if row is None:
        return {
            "balance_cents": 0,
            "balance_eur": "0.00",
            "badge": "🌱",
            "subscription_tier": "free",
            "is_sustainer": False,
        }

    bal = row["credit_balance"]
    tier = row["subscription_tier"] or "free"
    return {
        "balance_cents": bal,
        "balance_eur": f"{bal / 100:.2f}",
        "badge": "🌳" if tier == "sustainer" else ("🌿" if bal > 0 else "🌱"),
        "subscription_tier": tier,
        "is_sustainer": tier == "sustainer",
    }


def check_credit(
    conn,
    user_id: int,
    event_type: str,
    *,
    raise_on_insufficient: bool = True,
) -> dict:
    """
    Pre-check: does the user have enough credit for this deliverable?

    Sustainers always pass (unlimited).
    Returns {"allowed": bool, "cost_cents": int, "balance_cents": int, ...}
    Raises HTTP 402 if insufficient and raise_on_insufficient=True.
    """
    cost = _get_price(conn, event_type)
    info = get_credit_balance(conn, user_id)
    bal = info["balance_cents"]

    # Sustainers bypass credit check
    if info["is_sustainer"]:
        return {
            "allowed": True,
            "cost_cents": 0,
            "balance_cents": bal,
            "balance_after": bal,
            "is_sustainer": True,
        }

    allowed = bal >= cost
    result = {
        "allowed": allowed,
        "cost_cents": cost,
        "cost_eur": f"{cost / 100:.2f}",
        "balance_cents": bal,
        "balance_eur": info["balance_eur"],
        "balance_after": bal - cost if allowed else bal,
        "is_sustainer": False,
    }

    if not allowed and raise_on_insufficient:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credit",
                "message": f"This costs €{cost / 100:.2f} but your balance is €{bal / 100:.2f}.",
                "cost_cents": cost,
                "balance_cents": bal,
                "topup_url": "/account#credits",
            },
        )

    return result


def spend_credit(
    conn,
    user_id: int,
    cost_cents: int,
    description: str,
    deliverable_ref: Optional[str] = None,
    *,
    commit: bool = True,
) -> int:
    """
    Deduct credits atomically. Returns new balance.
    Raises HTTP 402 if balance would go negative.
    """
    with conn.cursor() as cur:
        # Atomic deduct with check
        cur.execute(
            """
            UPDATE users
            SET credit_balance = credit_balance - %s
            WHERE user_id = %s AND credit_balance >= %s
            RETURNING credit_balance
            """,
            (cost_cents, user_id, cost_cents),
        )
        row = cur.fetchone()
        if row is None:
            if commit:
                conn.rollback()
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "insufficient_credit",
                    "message": f"Insufficient balance for €{cost_cents / 100:.2f} charge.",
                    "topup_url": "/account#credits",
                },
            )

        new_balance = row["credit_balance"]

        # Record transaction
        cur.execute(
            """
            INSERT INTO credit_transactions
                (user_id, amount_cents, balance_after, txn_type, description, deliverable_ref)
            VALUES (%s, %s, %s, 'spend', %s, %s)
            """,
            (user_id, -cost_cents, new_balance, description, deliverable_ref),
        )

    if commit:
        conn.commit()
    return new_balance


def topup_credit(
    conn,
    user_id: int,
    amount_cents: int,
    stripe_pi: Optional[str] = None,
    description: Optional[str] = None,
    *,
    commit: bool = True,
) -> int:
    """
    Add credits to user's balance. Returns new balance.
    """
    desc = description or f"Top-up €{amount_cents / 100:.2f}"
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET credit_balance = credit_balance + %s
            WHERE user_id = %s
            RETURNING credit_balance
            """,
            (amount_cents, user_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")

        new_balance = row["credit_balance"]

        cur.execute(
            """
            INSERT INTO credit_transactions
                (user_id, amount_cents, balance_after, txn_type, description,
                 stripe_payment_intent_id)
            VALUES (%s, %s, %s, 'topup', %s, %s)
            """,
            (user_id, amount_cents, new_balance, desc, stripe_pi),
        )

    if commit:
        conn.commit()
    return new_balance


def get_transaction_history(conn, user_id: int, limit: int = 20) -> list[dict]:
    """Return recent credit transactions for the account page."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT txn_id, amount_cents, balance_after, txn_type,
                   description, deliverable_ref, created_at
            FROM credit_transactions
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()

    return [
        {
            **dict(r),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]
