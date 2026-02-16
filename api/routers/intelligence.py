"""
Intelligence routes — Market intelligence / Opportunity Landscape.

Provides regional demand comparison, related professions, and activity charts
based on pre-computed demand_snapshot and profession_similarity tables.

Endpoints:
  GET  /landscape                        → Page render
  POST /api/intelligence/regional        → Regional demand for a domain/profession
  POST /api/intelligence/related         → Related professions with demand
  POST /api/intelligence/activity        → 14-day activity by day
  POST /api/intelligence/overview        → Combined overview for UI
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging

from api.deps import get_db, require_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["intelligence"])

# KLDB domain names (shared with search.py)
KLDB_DOMAIN_NAMES = {
    '01': 'Sicherheit & Verteidigung', '02': 'Sicherheit & Verteidigung',
    '03': 'Sicherheit & Verteidigung', '53': 'Sicherheit & Verteidigung',
    '11': 'Land- & Forstwirtschaft', '12': 'Land- & Forstwirtschaft',
    '13': 'Land- & Forstwirtschaft', '14': 'Land- & Forstwirtschaft',
    '21': 'Fertigung & Technik', '22': 'Fertigung & Technik',
    '23': 'Fertigung & Technik', '24': 'Fertigung & Technik',
    '27': 'Fertigung & Technik', '28': 'Fertigung & Technik',
    '25': 'Maschinen & Elektro', '26': 'Maschinen & Elektro',
    '29': 'Gastgewerbe & Lebensmittel',
    '31': 'Bau & Handwerk', '32': 'Bau & Handwerk',
    '33': 'Bau & Handwerk', '34': 'Bau & Handwerk', '54': 'Bau & Handwerk',
    '41': 'Wissenschaft & Forschung', '42': 'Wissenschaft & Forschung',
    '43': 'IT & Technologie',
    '51': 'Transport & Logistik', '52': 'Transport & Logistik',
    '61': 'Handel & Vertrieb', '62': 'Handel & Vertrieb',
    '63': 'Gastgewerbe & Tourismus',
    '71': 'Wirtschaft & Management', '72': 'Finanzen & Banken',
    '73': 'Verwaltung & Recht',
    '81': 'Gesundheit & Medizin', '82': 'Gesundheit & Medizin',
    '83': 'Bildung & Soziales', '84': 'Bildung & Soziales',
    '91': 'Kultur & Medien', '92': 'Kultur & Medien',
    '93': 'Kultur & Medien', '94': 'Kultur & Medien',
}

# ── Demand level labels ─────────────────────────────────────────
def _demand_label(ratio: float) -> dict:
    """Convert demand ratio to human-readable label + emoji."""
    if ratio >= 2.0:
        return {"label": "sehr hoch", "emoji": "🔥", "level": "very_high"}
    elif ratio >= 1.3:
        return {"label": "hoch", "emoji": "↑", "level": "high"}
    elif ratio >= 0.7:
        return {"label": "stabil", "emoji": "→", "level": "stable"}
    elif ratio >= 0.3:
        return {"label": "niedrig", "emoji": "↓", "level": "low"}
    else:
        return {"label": "sehr niedrig", "emoji": "⬇", "level": "very_low"}


# ============================================================
# Request models
# ============================================================
class RegionalRequest(BaseModel):
    domain_code: str                          # 2-digit KLDB domain code
    berufenet_id: Optional[int] = None        # specific profession (optional)
    location_state: Optional[str] = None      # user's state for highlighting

class RelatedRequest(BaseModel):
    berufenet_id: int                         # profession to find related for
    location_state: Optional[str] = None      # optional: overlay regional demand

class ActivityRequest(BaseModel):
    domain_code: Optional[str] = None
    berufenet_id: Optional[int] = None
    location_state: Optional[str] = None
    days: int = 14

class OverviewRequest(BaseModel):
    domain_code: str
    berufenet_id: Optional[int] = None
    location_state: Optional[str] = None


# ============================================================
# API: Regional demand comparison
# ============================================================
@router.post("/intelligence/regional")
async def regional_demand(
    req: RegionalRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Regional demand for a domain or specific profession.
    Returns list of states sorted by demand_ratio descending.
    """
    with conn.cursor() as cur:
        if req.berufenet_id:
            cur.execute("""
                SELECT location_state, total_postings, fresh_14d, fresh_7d,
                       demand_ratio, berufenet_name
                FROM demand_snapshot
                WHERE domain_code = %s AND berufenet_id = %s
                ORDER BY demand_ratio DESC NULLS LAST
            """, [req.domain_code, req.berufenet_id])
        else:
            cur.execute("""
                SELECT location_state, total_postings, fresh_14d, fresh_7d,
                       demand_ratio
                FROM demand_snapshot
                WHERE domain_code = %s AND berufenet_id IS NULL
                ORDER BY demand_ratio DESC NULLS LAST
            """, [req.domain_code])

        rows = cur.fetchall()

    regions = []
    user_region = None
    for r in rows:
        ratio = float(r['demand_ratio']) if r['demand_ratio'] else 0
        entry = {
            "state": r['location_state'],
            "total": r['total_postings'],
            "fresh_14d": r['fresh_14d'],
            "fresh_7d": r['fresh_7d'],
            "ratio": round(ratio, 2),
            **_demand_label(ratio),
        }
        if req.location_state and r['location_state'] == req.location_state:
            entry["is_user_region"] = True
            user_region = entry
        regions.append(entry)

    # Narrative
    domain_name = KLDB_DOMAIN_NAMES.get(req.domain_code, req.domain_code)
    if user_region and regions:
        top = regions[0]
        if top['state'] != user_region['state'] and user_region['ratio'] > 0:
            multiplier = round(top['ratio'] / user_region['ratio'], 1)
            narrative = (
                f"Marktaktivität für {domain_name} in {top['state']} ist "
                f"derzeit {multiplier}× höher als in {user_region['state']}."
            )
        else:
            narrative = (
                f"{user_region['state']} hat die höchste Marktaktivität "
                f"für {domain_name} ({user_region['ratio']}× Durchschnitt)."
            )
    elif regions:
        narrative = (
            f"Stärkste Marktaktivität für {domain_name}: "
            f"{regions[0]['state']} ({regions[0]['ratio']}× Durchschnitt)."
        )
    else:
        narrative = "Keine Daten verfügbar."

    return {
        "domain_code": req.domain_code,
        "domain_name": domain_name,
        "regions": regions,
        "narrative": narrative,
        "user_region": user_region,
    }


# ============================================================
# API: Related professions with demand
# ============================================================
@router.post("/intelligence/related")
async def related_professions(
    req: RelatedRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Related professions for a given berufenet_id, with optional regional demand overlay.
    """
    with conn.cursor() as cur:
        # Get the source profession name
        cur.execute("SELECT name, kldb FROM berufenet WHERE berufenet_id = %s", [req.berufenet_id])
        source = cur.fetchone()
        if not source:
            return JSONResponse({"error": "Beruf nicht gefunden"}, status_code=404)

        # Get similar professions
        cur.execute("""
            SELECT ps.berufenet_id_b, b.name, b.kldb,
                   ps.kldb_score, ps.embedding_score, ps.combined_score, ps.rank_for_a,
                   b.salary_median
            FROM profession_similarity ps
            JOIN berufenet b ON b.berufenet_id = ps.berufenet_id_b
            WHERE ps.berufenet_id_a = %s
            ORDER BY ps.rank_for_a
        """, [req.berufenet_id])
        similar = cur.fetchall()

        # Overlay demand if location_state given
        related = []
        for s in similar:
            entry = {
                "berufenet_id": s['berufenet_id_b'],
                "name": s['name'],
                "similarity": round(float(s['combined_score']), 2),
                "kldb_score": round(float(s['kldb_score']), 2),
                "embedding_score": round(float(s['embedding_score']), 2) if s['embedding_score'] else None,
                "salary_median": s['salary_median'] if s['salary_median'] and s['salary_median'] > 0 else None,
                "rank": s['rank_for_a'],
            }

            if req.location_state:
                # Get demand for this profession in the user's state
                domain_code = s['kldb'].replace("B ", "").replace(" ", "")[:2] if s['kldb'] else None
                if domain_code:
                    cur.execute("""
                        SELECT total_postings, fresh_14d, demand_ratio
                        FROM demand_snapshot
                        WHERE berufenet_id = %s AND location_state = %s
                        LIMIT 1
                    """, [s['berufenet_id_b'], req.location_state])
                    demand = cur.fetchone()
                    if demand:
                        ratio = float(demand['demand_ratio']) if demand['demand_ratio'] else 0
                        entry["demand"] = {
                            "total": demand['total_postings'],
                            "fresh_14d": demand['fresh_14d'],
                            "ratio": round(ratio, 2),
                            **_demand_label(ratio),
                        }

            related.append(entry)

    return {
        "source": {
            "berufenet_id": req.berufenet_id,
            "name": source['name'],
        },
        "related": related,
        "location_state": req.location_state,
    }


# ============================================================
# API: 14-day activity chart
# ============================================================
@router.post("/intelligence/activity")
async def activity_chart(
    req: ActivityRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Daily posting counts for the last N days, filtered by domain/profession/state.
    Returns a list of {date, count} for sparkline rendering.
    """
    with conn.cursor() as cur:
        wheres = [
            "p.enabled = true",
            "p.invalidated = false",
            f"p.first_seen_at > NOW() - INTERVAL '{int(req.days)} days'",
        ]
        params = []

        if req.domain_code:
            wheres.append("SUBSTRING(b.kldb FROM 3 FOR 2) = %s")
            params.append(req.domain_code)

        if req.berufenet_id:
            wheres.append("p.berufenet_id = %s")
            params.append(req.berufenet_id)

        if req.location_state:
            wheres.append("p.location_state = %s")
            params.append(req.location_state)

        where_sql = " AND ".join(wheres)

        cur.execute(f"""
            SELECT DATE(p.first_seen_at) AS day, COUNT(*) AS count
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
            GROUP BY day
            ORDER BY day
        """, params)

        days = [{"date": str(r['day']), "count": r['count']} for r in cur.fetchall()]

    return {
        "days": days,
        "total": sum(d['count'] for d in days),
        "domain_code": req.domain_code,
        "berufenet_id": req.berufenet_id,
        "location_state": req.location_state,
    }


# ============================================================
# API: Combined overview
# ============================================================
@router.post("/intelligence/overview")
async def intelligence_overview(
    req: OverviewRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Combined overview: regional comparison + related professions + activity chart.
    Single call for the Opportunity Landscape UI.
    """
    with conn.cursor() as cur:
        domain_name = KLDB_DOMAIN_NAMES.get(req.domain_code, req.domain_code)

        # ── Regional comparison ──────────────────────────────────────
        if req.berufenet_id:
            cur.execute("""
                SELECT location_state, total_postings, fresh_14d, fresh_7d, demand_ratio
                FROM demand_snapshot
                WHERE domain_code = %s AND berufenet_id = %s
                ORDER BY demand_ratio DESC NULLS LAST
            """, [req.domain_code, req.berufenet_id])
        else:
            cur.execute("""
                SELECT location_state, total_postings, fresh_14d, fresh_7d, demand_ratio
                FROM demand_snapshot
                WHERE domain_code = %s AND berufenet_id IS NULL
                ORDER BY demand_ratio DESC NULLS LAST
            """, [req.domain_code])

        regions = []
        user_region = None
        for r in cur.fetchall():
            ratio = float(r['demand_ratio']) if r['demand_ratio'] else 0
            entry = {
                "state": r['location_state'],
                "total": r['total_postings'],
                "fresh_14d": r['fresh_14d'],
                "ratio": round(ratio, 2),
                **_demand_label(ratio),
            }
            if req.location_state and r['location_state'] == req.location_state:
                entry["is_user_region"] = True
                user_region = entry
            regions.append(entry)

        # ── Top professions in domain (for this state or nationally) ──
        if req.location_state:
            cur.execute("""
                SELECT berufenet_id, berufenet_name, total_postings, fresh_14d, demand_ratio
                FROM demand_snapshot
                WHERE domain_code = %s AND berufenet_id IS NOT NULL
                  AND location_state = %s
                ORDER BY total_postings DESC
                LIMIT 10
            """, [req.domain_code, req.location_state])
        else:
            cur.execute("""
                SELECT berufenet_id, berufenet_name,
                       SUM(total_postings) AS total_postings,
                       SUM(fresh_14d) AS fresh_14d,
                       AVG(demand_ratio) AS demand_ratio
                FROM demand_snapshot
                WHERE domain_code = %s AND berufenet_id IS NOT NULL
                GROUP BY berufenet_id, berufenet_name
                ORDER BY total_postings DESC
                LIMIT 10
            """, [req.domain_code])

        top_professions = []
        for r in cur.fetchall():
            ratio = float(r['demand_ratio']) if r['demand_ratio'] else 0
            top_professions.append({
                "berufenet_id": r['berufenet_id'],
                "name": r['berufenet_name'],
                "total": r['total_postings'],
                "fresh_14d": r['fresh_14d'],
                "ratio": round(ratio, 2),
                **_demand_label(ratio),
            })

        # ── Related professions (if berufenet_id given) ──────────────
        related = []
        if req.berufenet_id:
            cur.execute("""
                SELECT ps.berufenet_id_b, b.name, ps.combined_score, ps.rank_for_a,
                       b.salary_median
                FROM profession_similarity ps
                JOIN berufenet b ON b.berufenet_id = ps.berufenet_id_b
                WHERE ps.berufenet_id_a = %s
                ORDER BY ps.rank_for_a
                LIMIT 8
            """, [req.berufenet_id])

            for s in cur.fetchall():
                entry = {
                    "berufenet_id": s['berufenet_id_b'],
                    "name": s['name'],
                    "similarity": round(float(s['combined_score']), 2),
                    "salary_median": s['salary_median'] if s['salary_median'] and s['salary_median'] > 0 else None,
                }
                # Overlay demand
                if req.location_state:
                    cur.execute("""
                        SELECT total_postings, fresh_14d, demand_ratio
                        FROM demand_snapshot
                        WHERE berufenet_id = %s AND location_state = %s
                        LIMIT 1
                    """, [s['berufenet_id_b'], req.location_state])
                    demand = cur.fetchone()
                    if demand and demand['demand_ratio']:
                        ratio = float(demand['demand_ratio'])
                        entry["demand"] = {
                            "total": demand['total_postings'],
                            "fresh_14d": demand['fresh_14d'],
                            "ratio": round(ratio, 2),
                            **_demand_label(ratio),
                        }
                related.append(entry)

        # ── 14-day activity ──────────────────────────────────────────
        act_wheres = [
            "p.enabled = true", "p.invalidated = false",
            "p.first_seen_at > NOW() - INTERVAL '14 days'",
            "SUBSTRING(b.kldb FROM 3 FOR 2) = %s",
        ]
        act_params = [req.domain_code]
        if req.location_state:
            act_wheres.append("p.location_state = %s")
            act_params.append(req.location_state)
        if req.berufenet_id:
            act_wheres.append("p.berufenet_id = %s")
            act_params.append(req.berufenet_id)

        cur.execute(f"""
            SELECT DATE(p.first_seen_at) AS day, COUNT(*) AS count
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {' AND '.join(act_wheres)}
            GROUP BY day ORDER BY day
        """, act_params)
        activity = [{"date": str(r['day']), "count": r['count']} for r in cur.fetchall()]

        # ── Narrative ────────────────────────────────────────────────
        narrative_parts = []
        if regions:
            top = regions[0]
            if user_region and top['state'] != user_region['state'] and user_region['ratio'] > 0:
                mult = round(top['ratio'] / user_region['ratio'], 1)
                narrative_parts.append(
                    f"Marktaktivität für {domain_name} ist in {top['state']} "
                    f"derzeit {mult}× höher als in {user_region['state']}."
                )
            elif user_region:
                narrative_parts.append(
                    f"{user_region['state']} hat die höchste Marktaktivität "
                    f"für {domain_name}."
                )
            else:
                narrative_parts.append(
                    f"Stärkste Aktivität für {domain_name}: {top['state']} "
                    f"({top['ratio']}× Durchschnitt)."
                )

        if related:
            strong = [r for r in related if r.get('demand', {}).get('level') in ('very_high', 'high')]
            if strong:
                names = ", ".join(r['name'] for r in strong[:3])
                narrative_parts.append(f"Verwandte Berufe mit starker Nachfrage: {names}.")

        return {
            "domain_code": req.domain_code,
            "domain_name": domain_name,
            "regions": regions,
            "user_region": user_region,
            "top_professions": top_professions,
            "related": related,
            "activity": activity,
            "narrative": " ".join(narrative_parts) if narrative_parts else "Keine Daten verfügbar.",
        }
