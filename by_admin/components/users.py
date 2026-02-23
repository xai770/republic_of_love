"""
Users Tab - Han Solo Freeze / Unfreeze panel
Admin can freeze/unfreeze accounts and inspect the audit timeline.
Connects directly to the `turing` DB (not base_yoga).
"""

import os
import streamlit as st
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from datetime import datetime

# ── turing DB credentials ────────────────────────────────────────────────────
_TURING_DB = {
    "dbname": "turing",
    "user": "base_admin",
    "password": os.getenv("DB_PASSWORD", "A40ytN2UEGc_tDliTLtMF-WyKOV_VslrULoLxmUZl38"),
    "host": "localhost",
    "port": "5432",
}


@contextmanager
def _turing_conn():
    conn = psycopg2.connect(**_TURING_DB)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── DB helpers ───────────────────────────────────────────────────────────────

def _fetch_users():
    with _turing_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, email, display_name, yogi_name,
                       is_admin, enabled, freeze_flag,
                       tier, last_login_at, created_at
                FROM users
                ORDER BY created_at DESC
            """)
            return cur.fetchall()


def _set_freeze(user_id: int, frozen: bool):
    with _turing_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET freeze_flag = %s WHERE user_id = %s",
                (frozen, user_id),
            )
            actor = "admin_gui"
            event = "freeze" if frozen else "unfreeze"
            detail = '{"via": "admin_gui"}'
            cur.execute(
                """
                INSERT INTO yogi_audit_log (user_id, actor, event_type, detail)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (user_id, actor, event, detail),
            )
        conn.commit()


def _fetch_audit(user_id: int, limit: int = 40):
    with _turing_conn() as conn:
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
            return cur.fetchall()


# ── prose formatter (mirrors lib/audit.py) ──────────────────────────────────
_PROSE = {
    "login":            "logged in",
    "logout":           "logged out",
    "cv_upload":        "uploaded a CV",
    "adele_save":       "Adele saved profile data",
    "profile_translate":"profile was translated",
    "profile_embed":    "profile embedding was updated",
    "freeze":           "account was frozen by admin",
    "unfreeze":         "account was unfrozen by admin",
}


def _to_prose(ev: dict) -> str:
    ts = ev["created_at"]
    if isinstance(ts, datetime):
        ts_str = ts.strftime("%Y-%m-%d %H:%M")
    else:
        ts_str = str(ts)[:16]
    label = _PROSE.get(ev["event_type"], ev["event_type"])
    return f"[{ts_str}] ({ev['actor']}) {label}"


# ── main renderer ────────────────────────────────────────────────────────────

def render_users_tab():
    st.header("👥 Users  ·  🧊 Han Solo Console")
    st.caption("Freeze or unfreeze user accounts. Changes are logged to the audit trail.")

    # ── refresh state ────────────────────────────────────────────────────────
    if "users_refresh" not in st.session_state:
        st.session_state.users_refresh = 0

    col_refresh, col_spacer = st.columns([1, 8])
    with col_refresh:
        if st.button("🔄 Refresh"):
            st.session_state.users_refresh += 1

    try:
        users = _fetch_users()
    except Exception as exc:
        st.error(f"Cannot load users: {exc}")
        return

    if not users:
        st.info("No users found.")
        return

    # ── summary metrics ──────────────────────────────────────────────────────
    total = len(users)
    frozen_count = sum(1 for u in users if u["freeze_flag"])
    disabled_count = sum(1 for u in users if not u["enabled"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Total users", total)
    m2.metric("🧊 Frozen", frozen_count)
    m3.metric("⛔ Disabled", disabled_count)

    st.divider()

    # ── per-user rows ────────────────────────────────────────────────────────
    st.subheader("All accounts")

    # Filter controls
    show_frozen_only = st.checkbox("Show frozen only", value=False)
    search_term = st.text_input("Search by email / name", placeholder="type to filter…")

    for user in users:
        uid = user["user_id"]
        email = user["email"] or "—"
        name = user["display_name"] or user["yogi_name"] or email
        frozen = bool(user["freeze_flag"])
        enabled = bool(user["enabled"])
        is_admin = bool(user["is_admin"])
        last_login = user["last_login_at"]
        last_login_str = last_login.strftime("%Y-%m-%d %H:%M") if last_login else "never"

        # apply filters
        if show_frozen_only and not frozen:
            continue
        if search_term and search_term.lower() not in email.lower() and search_term.lower() not in name.lower():
            continue

        # status badges
        badges = []
        if frozen:
            badges.append("🧊 FROZEN")
        if is_admin:
            badges.append("🔑 admin")
        if not enabled:
            badges.append("⛔ disabled")
        badge_str = "  ".join(badges) if badges else "✅ active"

        with st.expander(f"**{name}** — {email}  |  {badge_str}", expanded=False):
            col_info, col_action = st.columns([3, 1])

            with col_info:
                st.write(f"**user_id:** `{uid}`")
                st.write(f"**tier:** {user['tier']}  |  **last login:** {last_login_str}")

            with col_action:
                if frozen:
                    if st.button("🔓 Unfreeze", key=f"unfreeze_{uid}", type="primary"):
                        try:
                            _set_freeze(uid, False)
                            st.success(f"✅ {name} unfrozen.")
                            st.session_state.users_refresh += 1
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error: {exc}")
                else:
                    if st.button("🧊 Freeze", key=f"freeze_{uid}", type="secondary"):
                        try:
                            _set_freeze(uid, True)
                            st.warning(f"🧊 {name} frozen — carbonite engaged.")
                            st.session_state.users_refresh += 1
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error: {exc}")

            # ── audit log ───────────────────────────────────────────────────
            with st.container():
                st.caption("Recent audit events")
                try:
                    events = _fetch_audit(uid, limit=10)
                    if events:
                        for ev in events:
                            st.text(_to_prose(dict(ev)))
                    else:
                        st.text("(no events yet)")
                except Exception as exc:
                    st.caption(f"(audit unavailable: {exc})")
