"""
Dashboard routes — main user interface.
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
import markdown

from api.deps import get_db, get_current_user, require_user

router = APIRouter(tags=["dashboard"])


# ============================================================
# HOME STATS — single endpoint for all dashboard numbers
# ============================================================

@router.get("/api/home/stats")
def get_home_stats(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    All stats the home page needs in one call:
    - resume_complete: 0-100%
    - new_matches: matches with no interaction (never seen)
    - unread_matches: matches seen but not read (clicked < 5s)
    - saved_matches: favorited
    - open_applications: state = 'applied'
    """
    with conn.cursor() as cur:
        user_id = user['user_id']

        # Profile / resume completeness
        cur.execute("""
            SELECT profile_id, full_name, location, experience_level,
                   skill_keywords, desired_locations, desired_roles
            FROM profiles WHERE user_id = %s
        """, (user_id,))
        profile = cur.fetchone()

        resume_complete = 0
        profile_id = None
        if profile:
            profile_id = profile['profile_id']
            if profile['full_name']: resume_complete += 10
            if profile['location']: resume_complete += 10
            if profile['experience_level']: resume_complete += 10
            skills = profile['skill_keywords']
            if skills and skills != '[]' and len(str(skills)) > 2: resume_complete += 30
            if profile['desired_locations']: resume_complete += 20
            if profile['desired_roles']: resume_complete += 20

        if not profile_id:
            return {
                "resume_complete": 0,
                "new_matches": 0,
                "unread_matches": 0,
                "saved_matches": 0,
                "open_applications": 0,
                "has_profile": False,
            }

        # All match counts in one query
        cur.execute("""
            SELECT
                -- New: match exists but no interaction row at all (never seen)
                COUNT(*) FILTER (
                    WHERE i.interaction_id IS NULL
                ) as new_matches,
                -- Unread: has been seen (interaction exists) but viewed < 5s
                COUNT(*) FILTER (
                    WHERE i.interaction_id IS NOT NULL
                      AND COALESCE(i.total_view_seconds, 0) < 5
                      AND i.state NOT IN ('favorited', 'applied', 'hired', 'rejected')
                ) as unread_matches,
                -- Saved: favorited
                COUNT(*) FILTER (
                    WHERE i.is_favorited = true
                ) as saved_matches,
                -- Open applications
                COUNT(*) FILTER (
                    WHERE i.state = 'applied'
                ) as open_applications
            FROM profile_posting_matches m
            LEFT JOIN user_posting_interactions i
                ON i.user_id = %s AND i.posting_id = m.posting_id
            WHERE m.profile_id = %s
              AND m.skill_match_score > 0.30
        """, (user_id, profile_id))

        row = cur.fetchone()

        return {
            "resume_complete": resume_complete,
            "new_matches": row['new_matches'] or 0,
            "unread_matches": row['unread_matches'] or 0,
            "saved_matches": row['saved_matches'] or 0,
            "open_applications": row['open_applications'] or 0,
            "has_profile": True,
        }


# ============================================================
# JOURNEY STATS — three-column progress tracker
# ============================================================

@router.get("/api/home/journey")
def get_journey_stats(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Returns status for each journey step:
      A. Resume: upload/create, fix gaps, confirm skills
      B. Search: define search, review matches, select favorites
      C. Apply:  ship documents, await reply, train with coach, interview

    Each step returns: status ('not_started' | 'in_progress' | 'complete'), detail (string)
    """
    with conn.cursor() as cur:
        user_id = user['user_id']

        # ── A. Resume ──
        cur.execute("""
            SELECT profile_id, full_name, location, experience_level,
                   skill_keywords, desired_locations, desired_roles
            FROM profiles WHERE user_id = %s
        """, (user_id,))
        profile = cur.fetchone()

        resume_pct = 0
        profile_id = None
        missing_fields = []
        if profile:
            profile_id = profile['profile_id']
            if profile['full_name']: resume_pct += 10
            else: missing_fields.append('name')
            if profile['location']: resume_pct += 10
            else: missing_fields.append('location')
            if profile['experience_level']: resume_pct += 10
            else: missing_fields.append('experience')
            skills = profile['skill_keywords']
            if skills and skills != '[]' and len(str(skills)) > 2:
                resume_pct += 30
            else:
                missing_fields.append('skills')
            if profile['desired_locations']: resume_pct += 20
            else: missing_fields.append('desired_locations')
            if profile['desired_roles']: resume_pct += 20
            else: missing_fields.append('desired_roles')

        has_skills = profile and profile['skill_keywords'] and str(profile['skill_keywords']) not in ('[]', '', 'None')

        # A1: Upload/Create
        if not profile:
            a1 = {'status': 'not_started', 'detail': '0%'}
        elif resume_pct >= 100:
            a1 = {'status': 'complete', 'detail': '100%'}
        else:
            a1 = {'status': 'in_progress', 'detail': f'{resume_pct}%'}

        # A2: Fix gaps
        if resume_pct >= 100:
            a2 = {'status': 'complete', 'detail': ''}
        elif resume_pct > 0 and missing_fields:
            a2 = {'status': 'in_progress', 'detail': ', '.join(missing_fields[:3])}
        else:
            a2 = {'status': 'not_started', 'detail': ''}

        # A3: Confirm implied skills
        if has_skills:
            a3 = {'status': 'complete', 'detail': ''}
        elif profile:
            a3 = {'status': 'not_started', 'detail': ''}
        else:
            a3 = {'status': 'not_started', 'detail': ''}

        # ── B. Search ──
        has_search = profile and profile.get('desired_locations') is not None
        # Check search_params separately
        cur.execute("SELECT search_params FROM profiles WHERE user_id = %s", (user_id,))
        sp_row = cur.fetchone()
        has_search_params = sp_row and sp_row['search_params'] is not None

        # Match counts
        new_matches = 0
        unread_matches = 0
        favorites = 0
        if profile_id:
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE i.interaction_id IS NULL) as new_count,
                    COUNT(*) FILTER (
                        WHERE i.interaction_id IS NOT NULL
                          AND COALESCE(i.total_view_seconds, 0) < 5
                          AND i.state NOT IN ('favorited', 'applied', 'hired', 'rejected')
                    ) as unread_count,
                    COUNT(*) FILTER (WHERE i.is_favorited = true) as fav_count
                FROM profile_posting_matches m
                LEFT JOIN user_posting_interactions i
                    ON i.user_id = %s AND i.posting_id = m.posting_id
                WHERE m.profile_id = %s AND m.skill_match_score > 0.30
            """, (user_id, profile_id))
            mrow = cur.fetchone()
            new_matches = mrow['new_count'] or 0
            unread_matches = mrow['unread_count'] or 0
            favorites = mrow['fav_count'] or 0

        # Also count posting_interest likes as "favorites" alternative
        cur.execute("SELECT COUNT(*) as cnt FROM posting_interest WHERE user_id = %s AND interested = true", (user_id,))
        interest_likes = cur.fetchone()['cnt'] or 0
        total_favorites = favorites + interest_likes

        # B1: Define search
        if has_search_params:
            b1 = {'status': 'complete', 'detail': ''}
        else:
            b1 = {'status': 'not_started', 'detail': ''}

        # B2: Review matches
        total_to_review = new_matches + unread_matches
        if total_to_review == 0 and (favorites > 0 or interest_likes > 0):
            b2 = {'status': 'complete', 'detail': ''}
        elif total_to_review > 0:
            b2 = {'status': 'in_progress', 'detail': str(total_to_review)}
        else:
            b2 = {'status': 'not_started', 'detail': ''}

        # B3: Select favorites
        if total_favorites > 0:
            b3 = {'status': 'in_progress' if total_favorites < 3 else 'complete', 'detail': str(total_favorites)}
        else:
            b3 = {'status': 'not_started', 'detail': ''}

        # ── C. Apply (placeholder — tables don't exist yet) ──
        c1 = {'status': 'not_started', 'detail': ''}
        c2 = {'status': 'not_started', 'detail': ''}
        c3 = {'status': 'not_started', 'detail': ''}
        c4 = {'status': 'not_started', 'detail': ''}

        return {
            "resume": {
                "upload_create": a1,
                "fix_gaps": a2,
                "confirm_skills": a3,
            },
            "search": {
                "define_search": b1,
                "review_matches": b2,
                "select_favorites": b3,
            },
            "apply": {
                "ship_documents": c1,
                "await_reply": c2,
                "train_coach": c3,
                "interview": c4,
            },
            "resume_pct": resume_pct,
            "total_favorites": total_favorites,
            "new_matches": new_matches,
            "unread_matches": unread_matches,
        }


# ============================================================
# ACTIVITY LOG — first-person narrative of recent yogi events
# ============================================================

def _event_to_sentence(event_type: str, job_title: str, company: str, note: str | None) -> str:
    """
    Convert a yogi_posting_events row into a one-sentence first-person German sentence.
    Falls back gracefully if no job_title/company.
    """
    role = job_title or "eine Stelle"
    loc  = f" bei {company}" if company else ""

    templates_map = {
        "viewed":           f"Ich habe die Stelle {role}{loc} angesehen.",
        "saved":            f"Ich habe {role}{loc} auf meine Merkliste gesetzt.",
        "dismissed":        f"Ich habe {role}{loc} übersprungen.",
        "apply_intent":     f"Ich plane, mich auf {role}{loc} zu bewerben.",
        "applied":          f"Ich habe mich auf {role}{loc} beworben.",
        "not_applied":      f"Ich habe mich gegen eine Bewerbung auf {role}{loc} entschieden.",
        "outcome_received": f"Ich habe eine Rückmeldung zur Stelle {role}{loc} erhalten.",
    }
    base = templates_map.get(event_type, f"Aktivität: {event_type} — {role}{loc}.")
    if note:
        base = base.rstrip('.') + ': \u201e' + note + '\u201c'
    return base


@router.get("/api/home/activity")
def get_activity_log(
    limit: int = Query(default=6, ge=1, le=20),
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Return the last N yogi events as first-person narrative items.
    Used by the Activity Log panel on /home.
    """
    with conn.cursor() as cur:
        user_id = user["user_id"]

        # Get the active profile for this user
        cur.execute(
            "SELECT profile_id FROM profiles WHERE user_id = %s AND enabled = TRUE LIMIT 1",
            (user_id,),
        )
        profile_row = cur.fetchone()
        if not profile_row:
            return {"items": [], "has_profile": False}

        profile_id = profile_row["profile_id"]

        cur.execute("""
            SELECT
                e.event_type,
                e.note,
                e.created_at,
                p.job_title,
                p.location_city
            FROM yogi_posting_events e
            LEFT JOIN postings p ON p.posting_id = e.posting_id
            WHERE e.profile_id = %s
            ORDER BY e.created_at DESC
            LIMIT %s
        """, (profile_id, limit))

        rows = cur.fetchall()
        items = []
        for row in rows:
            items.append({
                "sentence":   _event_to_sentence(
                    row["event_type"],
                    row["job_title"],
                    row["location_city"],
                    row["note"],
                ),
                "event_type": row["event_type"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })

        return {"items": items, "has_profile": True}


# ============================================================
# YOGI-METER — funnel counts for the progress chart
# ============================================================

# Ordered funnel stages (top → bottom)
YOGI_FUNNEL_STAGES = [
    "viewed",
    "saved",
    "dismissed",
    "apply_intent",
    "applied",
    "not_applied",
    "outcome_received",
]

YOGI_FUNNEL_LABELS = {
    "viewed":           "Angesehen",
    "saved":            "Gemerkt",
    "dismissed":        "Übersprungen",
    "apply_intent":     "Geplant",
    "applied":          "Beworben",
    "not_applied":      "Abgesagt",
    "outcome_received": "Feedback",
}


@router.get("/api/home/yogimeter")
def get_yogimeter(
    period: str = Query(default="week", regex="^(day|week|month|all)$"),
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Return event counts by type for the Yogi-meter funnel chart.
    period: day=last 24h, week=last 7 days, month=last 30 days, all=lifetime.
    """
    PERIOD_FILTER = {
        "day":   "AND e.created_at >= NOW() - INTERVAL '1 day'",
        "week":  "AND e.created_at >= NOW() - INTERVAL '7 days'",
        "month": "AND e.created_at >= NOW() - INTERVAL '30 days'",
        "all":   "",
    }
    time_filter = PERIOD_FILTER.get(period, "")

    with conn.cursor() as cur:
        user_id = user["user_id"]

        cur.execute(
            "SELECT profile_id FROM profiles WHERE user_id = %s AND enabled = TRUE LIMIT 1",
            (user_id,),
        )
        profile_row = cur.fetchone()
        if not profile_row:
            return {"stages": [], "total_matches": 0, "days_active": 0, "period": period}

        profile_id = profile_row["profile_id"]

        # Event counts per type, filtered by time window
        cur.execute(f"""
            SELECT event_type, COUNT(*) as cnt
            FROM yogi_posting_events e
            WHERE profile_id = %s {time_filter}
            GROUP BY event_type
        """, (profile_id,))
        counts = {row["event_type"]: row["cnt"] for row in cur.fetchall()}

        # Total events in this period (for the subtitle counter)
        total_period = sum(counts.values())

        # Total matches for this profile (lifetime denominator)
        cur.execute(
            "SELECT COUNT(*) as cnt FROM profile_posting_matches WHERE profile_id = %s",
            (profile_id,),
        )
        total_matches = cur.fetchone()["cnt"] or 0

        # Days active = days since first event (lifetime)
        cur.execute("""
            SELECT EXTRACT(DAY FROM NOW() - MIN(created_at))::int as days
            FROM yogi_posting_events WHERE profile_id = %s
        """, (profile_id,))
        days_row = cur.fetchone()
        days_active = days_row["days"] if days_row and days_row["days"] else 0

        stages = [
            {
                "key":   stage,
                "label": YOGI_FUNNEL_LABELS[stage],
                "count": counts.get(stage, 0),
            }
            for stage in YOGI_FUNNEL_STAGES
        ]

        return {
            "stages":        stages,
            "total_matches": total_matches,
            "total_period":  total_period,
            "days_active":   days_active,
            "period":        period,
        }


# ============================================================
# BEWERBUNGSPROTOKOLL — full job-search log for employment agency
# ============================================================

# Human-readable German labels for the protocol
# 'viewed' is intentionally absent — viewing is not a state change and does not
# belong in the Bewerbungsprotokoll. It is tracked only for the Yogi-Meter funnel.
_PROTOKOLL_ACTION = {
    "saved":            "Stelle vorgemerkt",
    "dismissed":        "Stelle abgelehnt",
    "apply_intent":     "Bewerbung geplant",
    "applied":          "Beworben",
    "not_applied":      "Nicht beworben (Entscheidung)",
    "outcome_received": "Rückmeldung erhalten",
}

# Which event types count as "documented decisions" for the agency
_ENTSCHEIDUNG_TYPES = {
    "dismissed", "apply_intent", "applied", "not_applied", "outcome_received"
}


def _build_protokoll_rows(cur, profile_id: int, decisions_only: bool = False) -> list[dict]:
    """
    Fetch all protocol rows for a profile, optionally filtered to decisions only.
    Returns dicts with all fields needed for both JSON and text export.
    """
    # 'viewed' is never shown in the Protokoll — it is not a state change.
    # decisions_only further narrows to the 5 documented decision types (excludes 'saved').
    type_filter = (
        "AND e.event_type IN ('dismissed','apply_intent','applied','not_applied','outcome_received')"
        if decisions_only else
        "AND e.event_type != 'viewed'"
    )
    cur.execute(f"""
        SELECT
            e.event_id,
            e.event_type,
            e.note,
            e.reason,
            e.created_at,
            p.job_title,
            p.location_city,
            p.external_url,
            m.recommendation,
            m.go_reasons,
            m.nogo_reasons,
            m.user_decision,
            m.application_status,
            m.application_outcome
        FROM yogi_posting_events e
        LEFT JOIN postings p ON p.posting_id = e.posting_id
        LEFT JOIN profile_posting_matches m ON m.match_id = e.match_id
        WHERE e.profile_id = %s
        {type_filter}
        ORDER BY e.created_at DESC
    """, (profile_id,))

    rows = []
    for row in cur.fetchall():
        # Flatten nogo / go reasons from JSONB
        nogo = row["nogo_reasons"] or []
        go   = row["go_reasons"]   or []
        if isinstance(nogo, str):
            import json as _json
            nogo = _json.loads(nogo)
        if isinstance(go, str):
            import json as _json
            go = _json.loads(go)

        # Build rationale string from note + nogo_reasons (for dismissed/not_applied)
        rationale = row["note"] or ""
        if row["event_type"] in ("dismissed", "not_applied") and not rationale and nogo:
            rationale = "; ".join(nogo)

        rows.append({
            "event_id":          row["event_id"],
            "event_type":        row["event_type"],
            "action_label":      _PROTOKOLL_ACTION.get(row["event_type"], row["event_type"]),
            "is_decision":       row["event_type"] in _ENTSCHEIDUNG_TYPES,
            "created_at":        row["created_at"].isoformat() if row["created_at"] else None,
            "created_date":      row["created_at"].strftime("%d.%m.%Y") if row["created_at"] else "",
            "created_time":      row["created_at"].strftime("%H:%M") if row["created_at"] else "",
            "job_title":         row["job_title"] or "Unbekannte Stelle",
            "location_city":     row["location_city"] or "",
            "external_url":      row["external_url"] or "",
            "rationale":         rationale,
            "nogo_reasons":      nogo,
            "go_reasons":        go,
            "recommendation":    row["recommendation"] or "",
            "user_decision":     row["user_decision"] or "",
            "application_status": row["application_status"] or "",
            "application_outcome": row["application_outcome"] or "",
        })
    return rows


@router.get("/api/home/protokoll")
def get_protokoll(
    decisions_only: bool = Query(default=False, description="True = only the 5 documented decision types; False = all state changes (viewed is always excluded)"),
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Full Bewerbungsprotokoll — all job-search events with rationales.
    Designed for employment agency documentation (Agentur für Arbeit / Jobcenter).
    """
    with conn.cursor() as cur:
        user_id = user["user_id"]
        cur.execute(
            "SELECT profile_id FROM profiles WHERE user_id = %s AND enabled = TRUE LIMIT 1",
            (user_id,),
        )
        profile_row = cur.fetchone()
        if not profile_row:
            return {"entries": [], "total": 0, "has_profile": False}

        profile_id = profile_row["profile_id"]
        rows = _build_protokoll_rows(cur, profile_id, decisions_only=decisions_only)

        # Summary counts for the header
        total_applications = sum(1 for r in rows if r["event_type"] == "applied")
        total_decisions    = sum(1 for r in rows if r["is_decision"])

        return {
            "entries":           rows,
            "total":             len(rows),
            "total_applications": total_applications,
            "total_decisions":   total_decisions,
            "has_profile":       True,
        }


@router.get("/api/home/protokoll/download")
def download_protokoll(
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Plain-text Bewerbungsprotokoll suitable for printing and handing to
    the Agentur für Arbeit or Jobcenter as proof of active job search.
    """
    from fastapi.responses import PlainTextResponse
    from datetime import date

    with conn.cursor() as cur:
        user_id = user["user_id"]

        # Get user display info
        cur.execute(
            "SELECT display_name, yogi_name FROM users WHERE user_id = %s",
            (user_id,),
        )
        u = cur.fetchone()
        name = u["display_name"] or u["yogi_name"] or "Nutzer/in"

        cur.execute(
            "SELECT profile_id, full_name, location FROM profiles WHERE user_id = %s AND enabled = TRUE LIMIT 1",
            (user_id,),
        )
        profile_row = cur.fetchone()
        if not profile_row:
            return PlainTextResponse("Kein Profil gefunden.", status_code=404)

        profile_id = profile_row["profile_id"]
        profile_name = profile_row["full_name"] or name
        profile_location = profile_row["location"] or ""

        rows = _build_protokoll_rows(cur, profile_id, decisions_only=False)

    today = date.today().strftime("%d.%m.%Y")
    lines = [
        "=" * 70,
        "BEWERBUNGSPROTOKOLL",
        "Nachweisdokument für die Agentur für Arbeit / das Jobcenter",
        "=" * 70,
        f"Name:     {profile_name}",
        f"Wohnort:  {profile_location}",
        f"Erstellt: {today}",
        f"Quelle:   talent.yoga (automatisch protokolliert)",
        "",
        f"Gesamteinträge:     {len(rows)}",
        f"Bewerbungen:        {sum(1 for r in rows if r['event_type'] == 'applied')}",
        f"Entscheidungen:     {sum(1 for r in rows if r['is_decision'])}",
        "",
        "-" * 70,
        "",
    ]

    current_month = None
    for row in reversed(rows):  # chronological order for the document
        # Month separator
        month = row["created_at"][:7] if row["created_at"] else ""
        if month != current_month:
            if current_month is not None:
                lines.append("")
            try:
                from datetime import datetime as _dt
                mo = _dt.fromisoformat(row["created_at"])
                lines.append(f"── {mo.strftime('%B %Y')} {'─' * 50}")
            except Exception:
                lines.append(f"── {month} {'─' * 50}")
            lines.append("")
            current_month = month

        action = row["action_label"]
        title  = row["job_title"]
        loc    = f" ({row['location_city']})" if row["location_city"] else ""
        dt     = f"{row['created_date']} {row['created_time']}"

        lines.append(f"{dt}  [{action}]")
        lines.append(f"  Stelle: {title}{loc}")

        if row["external_url"]:
            lines.append(f"  URL:    {row['external_url']}")

        if row["rationale"]:
            lines.append(f"  Begründung: {row['rationale']}")
        elif row["nogo_reasons"]:
            lines.append(f"  Begründung: {'; '.join(row['nogo_reasons'])}")

        lines.append("")

    lines += [
        "-" * 70,
        f"Dieses Dokument wurde am {today} automatisch von talent.yoga erstellt.",
        "talent.yoga protokolliert alle Stellenaktivitäten automatisch und",
        "datumssicher. Das Dokument kann als Nachweis bei der Agentur für Arbeit",
        "oder beim Jobcenter eingereicht werden.",
        "=" * 70,
    ]

    filename = f"bewerbungsprotokoll_{date.today().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content="\n".join(lines),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def render_base(content: str, user: dict = None) -> str:
    """Wrap content in base HTML template."""
    nav = ""
    if user:
        nav = f"""
        <nav style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #ddd; margin-bottom: 20px;">
            <a href="/home" style="font-size: 1.5em; text-decoration: none;">🎯 talent.yoga</a>
            <div>
                <span style="margin-right: 15px;">👤 {user['display_name']}</span>
                <a href="/auth/logout">Logout</a>
            </div>
        </nav>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>talent.yoga</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px; 
                margin: 0 auto; 
                padding: 20px;
                background: #f5f5f5;
            }}
            a {{ color: #0066cc; }}
            .card {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 10px;
            }}
            .score {{
                font-size: 1.4em;
                font-weight: bold;
                color: #333;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
            }}
            .badge-apply {{
                background: #d4edda;
                color: #155724;
            }}
            .badge-skip {{
                background: #fff3cd;
                color: #856404;
            }}
            .job-title {{
                font-size: 1.2em;
                font-weight: 600;
                margin: 0 0 5px 0;
            }}
            .job-meta {{
                color: #666;
                font-size: 0.9em;
            }}
            .actions {{
                margin-top: 15px;
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}
            .btn {{
                padding: 8px 16px;
                border-radius: 5px;
                border: none;
                cursor: pointer;
                font-size: 0.9em;
                text-decoration: none;
                display: inline-block;
            }}
            .btn-primary {{
                background: #0066cc;
                color: white;
            }}
            .btn-secondary {{
                background: #e9ecef;
                color: #333;
            }}
            .btn-success {{
                background: #28a745;
                color: white;
            }}
            .rating {{
                display: flex;
                gap: 5px;
            }}
            .rating button {{
                background: none;
                border: none;
                font-size: 1.5em;
                cursor: pointer;
                opacity: 0.3;
                transition: opacity 0.2s;
            }}
            .rating button:hover,
            .rating button.active {{
                opacity: 1;
            }}
            .filters {{
                margin-bottom: 20px;
                display: flex;
                gap: 10px;
            }}
            .filters a {{
                padding: 8px 16px;
                background: white;
                border-radius: 5px;
                text-decoration: none;
                color: #333;
            }}
            .filters a.active {{
                background: #0066cc;
                color: white;
            }}
            .empty {{
                text-align: center;
                padding: 40px;
                color: #666;
            }}
            .feedback-form {{
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid #eee;
            }}
            .feedback-text {{
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 0.9em;
                margin-top: 5px;
            }}
            .htmx-indicator {{
                opacity: 0;
                transition: opacity 200ms ease-in;
            }}
            .htmx-request .htmx-indicator {{
                opacity: 1;
            }}
            .toast {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 15px 25px;
                background: #333;
                color: white;
                border-radius: 5px;
                animation: fadeIn 0.3s, fadeOut 0.3s 2.7s;
            }}
            @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
            @keyframes fadeOut {{ from {{ opacity: 1; }} to {{ opacity: 0; }} }}
        </style>
    </head>
    <body>
        {nav}
        {content}
    </body>
    </html>
    """


@router.get("/dashboard-legacy", response_class=HTMLResponse)
def dashboard_legacy(
    request: Request, 
    filter: str = Query("all", description="all, apply, skip"),
    conn=Depends(get_db)
):
    """
    Main dashboard — shows matches with ratings.
    """
    user = get_current_user(request, conn)
    
    if not user:
        return HTMLResponse(render_base("""
            <div class="card" style="text-align: center; padding: 60px 20px;">
                <h1>🎯 talent.yoga</h1>
                <p style="font-size: 1.2em; color: #666; margin: 20px 0;">
                    Find jobs that match your skills
                </p>
                <a href="/auth/google" class="btn btn-primary" style="font-size: 1.1em; padding: 12px 30px;">
                    Sign in with Google
                </a>
            </div>
        """))
    
    # Get user's profile
    with conn.cursor() as cur:
        cur.execute("SELECT profile_id FROM profiles WHERE user_id = %s", (user['user_id'],))
        profile = cur.fetchone()
        
        if not profile:
            return HTMLResponse(render_base("""
                <div class="card empty">
                    <h2>No profile linked</h2>
                    <p>Your account isn't linked to a profile yet.</p>
                    <p>Contact support to set up your profile.</p>
                </div>
            """, user))
        
        # Build query based on filter
        query = """
            SELECT m.match_id, m.posting_id, p.job_title as title, 
                   p.posting_name as company, p.location_city as location,
                   m.skill_match_score, m.recommendation, m.user_rating,
                   m.user_applied, p.external_url as url
            FROM profile_posting_matches m
            JOIN postings p ON m.posting_id = p.posting_id
            WHERE m.profile_id = %s
        """
        params = [profile['profile_id']]
        
        if filter == "apply":
            query += " AND m.recommendation = 'APPLY'"
        elif filter == "skip":
            query += " AND m.recommendation = 'SKIP'"
        
        query += " ORDER BY m.skill_match_score DESC LIMIT 50"
        
        cur.execute(query, params)
        matches = cur.fetchall()
    
    # Build filter tabs
    filter_html = f"""
    <div class="filters">
        <a href="/home?filter=all" class="{'active' if filter == 'all' else ''}">All</a>
        <a href="/home?filter=apply" class="{'active' if filter == 'apply' else ''}">✅ Apply</a>
        <a href="/home?filter=skip" class="{'active' if filter == 'skip' else ''}">⏭️ Skip</a>
    </div>
    """
    
    if not matches:
        return HTMLResponse(render_base(filter_html + """
            <div class="card empty">
                <h2>No matches yet</h2>
                <p>We're still processing job postings. Check back soon!</p>
            </div>
        """, user))
    
    # Build match cards
    cards_html = ""
    for m in matches:
        badge_class = "badge-apply" if m['recommendation'] == 'APPLY' else "badge-skip"
        badge_text = "✅ APPLY" if m['recommendation'] == 'APPLY' else "⏭️ SKIP"
        
        # Star rating
        stars_html = '<div class="rating">'
        current_rating = m['user_rating'] or 0
        for i in range(1, 6):
            active = "active" if i <= current_rating else ""
            stars_html += f'''
                <button class="{active}" 
                        hx-post="/api/rate/{m['match_id']}?rating={i}"
                        hx-swap="none"
                        hx-on::after-request="this.parentElement.querySelectorAll('button').forEach((b,idx) => b.classList.toggle('active', idx < {i}))">
                    ⭐
                </button>
            '''
        stars_html += '</div>'
        
        # Applied button
        applied_class = "btn-success" if m['user_applied'] else "btn-secondary"
        applied_text = "✓ Applied" if m['user_applied'] else "Mark Applied"
        
        cards_html += f"""
        <div class="card" id="match-{m['match_id']}">
            <div class="card-header">
                <div>
                    <span class="badge {badge_class}">{badge_text}</span>
                </div>
                <span class="score">{m['skill_match_score']*100:.0f}%</span>
            </div>
            <h3 class="job-title">{m['title']}</h3>
            <p class="job-meta">
                🏢 {m['company'] or 'Unknown'} &nbsp;|&nbsp; 
                📍 {m['location'] or 'Unknown'}
            </p>
            <div class="actions">
                <a href="/match/{m['match_id']}" class="btn btn-primary">View Details</a>
                {'<a href="' + m['url'] + '" target="_blank" class="btn btn-secondary">View Job ↗</a>' if m['url'] else ''}
                <button class="btn {applied_class}"
                        hx-post="/api/applied/{m['match_id']}?applied={str(not m['user_applied']).lower()}"
                        hx-swap="outerHTML">
                    {applied_text}
                </button>
            </div>
            <div class="feedback-form">
                <label>Rate this match:</label>
                {stars_html}
            </div>
        </div>
        """
    
    content = f"""
        <h1>Your Matches ({len(matches)})</h1>
        {filter_html}
        {cards_html}
    """
    
    return HTMLResponse(render_base(content, user))


@router.get("/match/{match_id}", response_class=HTMLResponse)
def match_detail(match_id: int, request: Request, conn=Depends(get_db)):
    """
    Detailed match view with skill breakdown.
    """
    user = get_current_user(request, conn)
    if not user:
        return HTMLResponse(render_base('<p>Please <a href="/auth/google">log in</a></p>'))
    
    with conn.cursor() as cur:
        # Get match with authorization
        cur.execute("""
            SELECT m.*, p.job_title as title, p.posting_name as company_name, 
                   p.location_city, p.external_url as url,
                   p.extracted_summary, pr.user_id
            FROM profile_posting_matches m
            JOIN postings p ON m.posting_id = p.posting_id
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match or match['user_id'] != user['user_id']:
            return HTMLResponse(render_base('<p>Match not found</p>', user))
        
        # Requirements: embeddings handle skill matching, no facets table
        requirements = []
        
        # Get profile skills from profiles.skill_keywords
        cur.execute("""
            SELECT skill_keywords FROM profiles WHERE profile_id = %s
        """, (match['profile_id'],))
        row = cur.fetchone()
        skill_keywords = row['skill_keywords'] if row else None
        skills = []
        if skill_keywords:
            import json
            if isinstance(skill_keywords, str):
                skill_keywords = json.loads(skill_keywords)
            skills = sorted(set(skill_keywords)) if skill_keywords else []
    
    badge_class = "badge-apply" if match['recommendation'] == 'APPLY' else "badge-skip"
    badge_text = "✅ APPLY" if match['recommendation'] == 'APPLY' else "⏭️ SKIP"
    
    # Build skills comparison
    req_html = "<h3>Job Requirements</h3><ul>"
    for req in requirements[:15]:
        req_html += f"<li>{req}</li>"
    req_html += "</ul>"
    
    skills_html = "<h3>Your Matching Skills</h3><ul>"
    for skill in skills[:15]:
        skills_html += f"<li>{skill}</li>"
    skills_html += "</ul>"
    
    content = f"""
        <a href="/home" style="display: inline-block; margin-bottom: 20px;">← Back to matches</a>
        
        <div class="card">
            <div class="card-header">
                <span class="badge {badge_class}">{badge_text}</span>
                <span class="score">{match['skill_match_score']*100:.0f}%</span>
            </div>
            <h2 class="job-title">{match['title']}</h2>
            <p class="job-meta">
                🏢 {match['company_name'] or 'Unknown'} &nbsp;|&nbsp; 
                📍 {match['location_city'] or 'Unknown'} &nbsp;|&nbsp;
                <span style="color: #888; font-size: 0.9em;">ID: {match['posting_id']}</span>
            </p>
            
            <div style="display: flex; gap: 10px; margin: 15px 0;">
                {f'<a href="{match["url"]}" target="_blank" class="btn btn-primary">View Original Job ↗</a>' if match['url'] else ''}
                <a href="/viz/match/{match_id}" target="_blank" class="btn btn-secondary">🎯 View Skill Matrix</a>
            </div>
        </div>
        
        <div class="card">
            <h3>Job Summary</h3>
            <div>{markdown.markdown(match['extracted_summary']) if match['extracted_summary'] else 'No summary available'}</div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div class="card">{req_html}</div>
            <div class="card">{skills_html}</div>
        </div>
        
        <div class="card">
            <h3>Your Feedback</h3>
            <p>How relevant is this match?</p>
            <form hx-post="/api/feedback/{match['match_id']}" hx-swap="outerHTML">
                <textarea name="feedback" class="feedback-text" rows="3" 
                    placeholder="What did you like or dislike about this match? This helps us improve..."></textarea>
                <button type="submit" class="btn btn-primary" style="margin-top: 10px;">Submit Feedback</button>
            </form>
        </div>
    """
    
    return HTMLResponse(render_base(content, user))


# API endpoints for HTMX
@router.post("/api/rate/{match_id}")
def rate_match_htmx(match_id: int, rating: int, request: Request, conn=Depends(get_db)):
    """Rate a match via HTMX."""
    user = get_current_user(request, conn)
    if not user:
        return HTMLResponse("Unauthorized", status_code=401)
    
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE profile_posting_matches m
            SET user_rating = %s, rated_at = NOW()
            FROM profiles p
            WHERE m.match_id = %s 
              AND m.profile_id = p.profile_id 
              AND p.user_id = %s
        """, (rating, match_id, user['user_id']))
        conn.commit()
    
    return HTMLResponse(f'<div class="toast">Rated {rating} stars</div>')


@router.post("/api/applied/{match_id}")
def mark_applied_htmx(match_id: int, applied: bool, request: Request, conn=Depends(get_db)):
    """Mark as applied via HTMX."""
    user = get_current_user(request, conn)
    if not user:
        return HTMLResponse("Unauthorized", status_code=401)
    
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE profile_posting_matches m
            SET user_applied = %s, applied_at = CASE WHEN %s THEN NOW() ELSE NULL END
            FROM profiles p
            WHERE m.match_id = %s 
              AND m.profile_id = p.profile_id 
              AND p.user_id = %s
        """, (applied, applied, match_id, user['user_id']))
        conn.commit()
    
    btn_class = "btn-success" if applied else "btn-secondary"
    btn_text = "✓ Applied" if applied else "Mark Applied"
    return HTMLResponse(f'''
        <button class="btn {btn_class}"
                hx-post="/api/applied/{match_id}?applied={str(not applied).lower()}"
                hx-swap="outerHTML">
            {btn_text}
        </button>
    ''')


@router.post("/api/feedback/{match_id}")
def submit_feedback_htmx(match_id: int, request: Request, conn=Depends(get_db)):
    """Submit text feedback via HTMX."""
    user = get_current_user(request, conn)
    if not user:
        return HTMLResponse("Unauthorized", status_code=401)
    
    # For now, just acknowledge - we'll add feedback storage later
    return HTMLResponse('''
        <div class="card" style="background: #d4edda; color: #155724;">
            ✓ Thank you for your feedback! This helps us improve your matches.
        </div>
    ''')
