"""
Search routes — Mira Search: interactive three-panel job search.

Panels: Domain (Berufsfeld) | Map (Leaflet heatmap) | Qualification Level
Cross-filtering: any panel change → single API call → all panels update.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import threading
import logging

from api.deps import get_db, require_user
from lib.posting_verifier import queue_stale_verification, find_stale_posting_ids

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])

# ============================================================
# KLDB domain mapping (mirrors tools/populate_domain_gate.py)
# ============================================================
KLDB_DOMAINS = {
    '01': 'Sicherheit & Verteidigung',
    '02': 'Sicherheit & Verteidigung',
    '03': 'Sicherheit & Verteidigung',
    '53': 'Sicherheit & Verteidigung',
    '11': 'Land- & Forstwirtschaft',
    '12': 'Land- & Forstwirtschaft',
    '13': 'Land- & Forstwirtschaft',
    '14': 'Land- & Forstwirtschaft',
    '21': 'Fertigung & Technik',
    '22': 'Fertigung & Technik',
    '23': 'Fertigung & Technik',
    '24': 'Fertigung & Technik',
    '27': 'Fertigung & Technik',
    '28': 'Fertigung & Technik',
    '25': 'Maschinen & Elektro',
    '26': 'Maschinen & Elektro',
    '29': 'Gastgewerbe & Lebensmittel',
    '31': 'Bau & Handwerk',
    '32': 'Bau & Handwerk',
    '33': 'Bau & Handwerk',
    '34': 'Bau & Handwerk',
    '54': 'Bau & Handwerk',
    '41': 'Wissenschaft & Forschung',
    '42': 'Wissenschaft & Forschung',
    '43': 'IT & Technologie',
    '51': 'Transport & Logistik',
    '52': 'Transport & Logistik',
    '61': 'Handel & Vertrieb',
    '62': 'Handel & Vertrieb',
    '63': 'Gastgewerbe & Tourismus',
    '71': 'Wirtschaft & Management',
    '72': 'Finanzen & Banken',
    '73': 'Verwaltung & Recht',
    '81': 'Gesundheit & Medizin',
    '82': 'Gesundheit & Medizin',
    '83': 'Bildung & Soziales',
    '84': 'Bildung & Soziales',
    '91': 'Kultur & Medien',
    '92': 'Kultur & Medien',
    '93': 'Kultur & Medien',
    '94': 'Kultur & Medien',
}

# Deduplicate: code → domain_name, preserving first occurrence order
DOMAIN_NAMES = {}
for _code, _name in KLDB_DOMAINS.items():
    if _name not in DOMAIN_NAMES:
        DOMAIN_NAMES[_name] = []
    DOMAIN_NAMES[_name].append(_code)

DOMAIN_COLORS = {
    'Gesundheit & Medizin': '#66c2a5',
    'IT & Technologie': '#fc8d62',
    'Fertigung & Technik': '#8da0cb',
    'Maschinen & Elektro': '#e78ac3',
    'Bau & Handwerk': '#a6d854',
    'Finanzen & Banken': '#ffd92f',
    'Handel & Vertrieb': '#e5c494',
    'Transport & Logistik': '#b3b3b3',
    'Bildung & Soziales': '#80b1d3',
    'Wissenschaft & Forschung': '#fdb462',
    'Gastgewerbe & Tourismus': '#bc80bd',
    'Gastgewerbe & Lebensmittel': '#ccebc5',
    'Verwaltung & Recht': '#ffed6f',
    'Wirtschaft & Management': '#d9d9d9',
    'Land- & Forstwirtschaft': '#ffffb3',
    'Sicherheit & Verteidigung': '#bebada',
    'Kultur & Medien': '#fb8072',
}

QL_LABELS = {
    1: 'Helfer',
    2: 'Fachkraft',
    3: 'Spezialist',
    4: 'Experte',
}


# ============================================================
# Search preview endpoint
# ============================================================

class SearchRequest(BaseModel):
    domains: Optional[List[str]] = None   # KLDB 2-digit codes
    ql: Optional[List[int]] = None        # qualification levels 1-4
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "domains": ["43", "81"],
                "ql": [2, 3],
                "lat": 48.14,
                "lon": 11.58,
                "radius_km": 50
            }
        }


@router.post("/search/preview")
def search_preview(
    req: SearchRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Cross-filter search preview.
    Returns: total, by_domain, by_ql, heatmap, fresh_count.
    All filters optional — no filters = everything.
    """
    with conn.cursor() as cur:
        # Build WHERE clauses — always exclude invalidated/disabled postings
        wheres = ["p.berufenet_id IS NOT NULL", "p.enabled = true", "p.invalidated = false"]
        params = []

        if req.domains:
            wheres.append("SUBSTRING(b.kldb FROM 3 FOR 2) = ANY(%s)")
            params.append(req.domains)

        if req.ql:
            wheres.append("CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) = ANY(%s)")
            params.append(req.ql)

        if req.lat is not None and req.lon is not None and req.radius_km:
            # Haversine approximation in SQL (km)
            wheres.append("""
                (6371 * acos(
                    cos(radians(%s)) * cos(radians(
                        CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT)
                    )) *
                    cos(radians(
                        CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS FLOAT)
                    ) - radians(%s)) +
                    sin(radians(%s)) * sin(radians(
                        CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT)
                    ))
                )) <= %s
            """)
            params.extend([req.lat, req.lon, req.lat, req.radius_km])

        where_sql = " AND ".join(wheres)

        # --- Total count ---
        cur.execute(f"""
            SELECT COUNT(*) as total
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
        """, params)
        total = cur.fetchone()['total']

        # --- By domain (always unfiltered by domain, but filtered by QL + geo) ---
        domain_wheres = [w for i, w in enumerate(wheres) if not (req.domains and 'SUBSTRING(b.kldb FROM 3 FOR 2)' in w)]
        domain_params = []
        if req.ql:
            domain_params.append(req.ql)
        if req.lat is not None and req.lon is not None and req.radius_km:
            domain_params.extend([req.lat, req.lon, req.lat, req.radius_km])

        domain_where_sql = " AND ".join(domain_wheres) if domain_wheres else "TRUE"
        cur.execute(f"""
            SELECT SUBSTRING(b.kldb FROM 3 FOR 2) as code,
                   COUNT(*) as count
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {domain_where_sql}
            GROUP BY code
            ORDER BY count DESC
        """, domain_params)
        by_domain_raw = cur.fetchall()

        # Map codes to domain names, aggregate
        domain_agg = {}
        for row in by_domain_raw:
            code = row['code']
            name = KLDB_DOMAINS.get(code, f'Sonstige ({code})')
            domain_agg[name] = domain_agg.get(name, 0) + row['count']

        by_domain = [
            {
                "name": name,
                "count": count,
                "color": DOMAIN_COLORS.get(name, '#cccccc'),
                "codes": DOMAIN_NAMES.get(name, []),
                "selected": bool(req.domains and any(c in req.domains for c in DOMAIN_NAMES.get(name, [])))
            }
            for name, count in sorted(domain_agg.items(), key=lambda x: x[0])
        ]

        # --- By QL (always unfiltered by QL, but filtered by domain + geo) ---
        ql_wheres = [w for i, w in enumerate(wheres) if not (req.ql and 'CAST(SUBSTRING(b.kldb FROM 7 FOR 1)' in w)]
        ql_params = []
        if req.domains:
            ql_params.append(req.domains)
        if req.lat is not None and req.lon is not None and req.radius_km:
            ql_params.extend([req.lat, req.lon, req.lat, req.radius_km])

        ql_where_sql = " AND ".join(ql_wheres) if ql_wheres else "TRUE"
        cur.execute(f"""
            SELECT CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) as level,
                   COUNT(*) as count
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {ql_where_sql}
              AND SUBSTRING(b.kldb FROM 7 FOR 1) ~ '^[1-4]$'
            GROUP BY level
            ORDER BY level
        """, ql_params)
        by_ql = [
            {
                "level": row['level'],
                "label": QL_LABELS.get(row['level'], f"Level {row['level']}"),
                "count": row['count'],
                "selected": bool(req.ql and row['level'] in req.ql)
            }
            for row in cur.fetchall()
        ]

        # --- Heatmap (uses ALL filters) ---
        cur.execute(f"""
            SELECT
                ROUND(CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS NUMERIC), 2) as lat,
                ROUND(CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS NUMERIC), 2) as lon,
                COUNT(*) as weight
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' IS NOT NULL
            GROUP BY lat, lon
        """, params)
        heatmap = [[float(r['lat']), float(r['lon']), r['weight']] for r in cur.fetchall()]

        # --- Map markers (individual postings with lat/lon, max 500) ---
        cur.execute(f"""
            SELECT
                p.posting_id,
                p.job_title,
                p.location_city,
                source_metadata->'raw_api_response'->'arbeitgeber'->>'name' as employer,
                CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT) as lat,
                CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS FLOAT) as lon
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' IS NOT NULL
            ORDER BY p.first_seen_at DESC NULLS LAST
            LIMIT 500
        """, params)
        markers = [
            {
                "id": r['posting_id'],
                "t": (r['job_title'] or '')[:60],
                "e": (r['employer'] or '')[:40],
                "c": r['location_city'] or '',
                "lat": round(float(r['lat']), 4),
                "lon": round(float(r['lon']), 4),
            }
            for r in cur.fetchall()
        ]

        # --- Freshness (postings in last 7 days within current filters) ---
        cur.execute(f"""
            SELECT COUNT(*) as fresh
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND (source_metadata->>'published_date')::date >= CURRENT_DATE - INTERVAL '7 days'
        """, params)
        fresh_count = cur.fetchone()['fresh']

        return {
            "total": total,
            "by_domain": by_domain,
            "by_ql": by_ql,
            "heatmap": heatmap,
            "markers": markers,
            "fresh_count": fresh_count,
        }


# ============================================================
# Domain metadata (for initial page load)
# ============================================================

@router.get("/search/domains")
def get_domains(user: dict = Depends(require_user)):
    """Return all domain names, codes, and colors."""
    result = []
    seen = set()
    for name, codes in DOMAIN_NAMES.items():
        if name not in seen:
            seen.add(name)
            result.append({
                "name": name,
                "codes": codes,
                "color": DOMAIN_COLORS.get(name, '#cccccc'),
            })
    return result


@router.get("/search/ql-levels")
def get_ql_levels(user: dict = Depends(require_user)):
    """Return qualification level labels."""
    return [{"level": k, "label": v} for k, v in QL_LABELS.items()]


# ============================================================
# Save search as active search for matching pipeline
# ============================================================

class SaveSearchRequest(BaseModel):
    domains: Optional[List[str]] = None
    ql: Optional[List[int]] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: Optional[int] = None


@router.post("/search/save")
def save_search(
    req: SaveSearchRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """Save (or update) the yogi's active search parameters."""
    with conn.cursor() as cur:
        search_data = {
            "domains": req.domains,
            "ql": req.ql,
            "lat": req.lat,
            "lon": req.lon,
            "radius_km": req.radius_km,
        }

        # Upsert into profiles.search_params (JSONB column)
        cur.execute("""
            UPDATE profiles
            SET search_params = %s::jsonb,
                updated_at = NOW()
            WHERE user_id = %s
            RETURNING profile_id
        """, (json.dumps(search_data), user['user_id']))

        result = cur.fetchone()
        conn.commit()

        if not result:
            return JSONResponse(
                status_code=404,
                content={"error": "Kein Profil gefunden. Bitte erstelle zuerst ein Profil."}
            )

        return {"status": "saved", "profile_id": result['profile_id']}


@router.get("/search/saved")
def get_saved_search(
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """Get the yogi's saved search parameters."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT search_params
            FROM profiles
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()

        if not row or not row.get('search_params'):
            return {"search_params": None}

        return {"search_params": row['search_params']}


# ============================================================
# Search results — actual postings matching the filters
# ============================================================

class SearchResultsRequest(BaseModel):
    domains: Optional[List[str]] = None
    ql: Optional[List[int]] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: Optional[int] = None
    offset: int = 0
    limit: int = 20


@router.post("/search/results")
def search_results(
    req: SearchResultsRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Return actual posting records matching the current filters.
    Paginated with offset/limit. Returns posting details + user interest status.
    """
    with conn.cursor() as cur:
        # Always exclude invalidated/disabled postings
        wheres = ["p.berufenet_id IS NOT NULL", "p.enabled = true", "p.invalidated = false"]
        params = []

        if req.domains:
            wheres.append("SUBSTRING(b.kldb FROM 3 FOR 2) = ANY(%s)")
            params.append(req.domains)

        if req.ql:
            wheres.append("CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) = ANY(%s)")
            params.append(req.ql)

        if req.lat is not None and req.lon is not None and req.radius_km:
            wheres.append("""
                (6371 * acos(
                    cos(radians(%s)) * cos(radians(
                        CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT)
                    )) *
                    cos(radians(
                        CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS FLOAT)
                    ) - radians(%s)) +
                    sin(radians(%s)) * sin(radians(
                        CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT)
                    ))
                )) <= %s
            """)
            params.extend([req.lat, req.lon, req.lat, req.radius_km])

        where_sql = " AND ".join(wheres)

        # Fetch postings with LEFT JOIN to interest table for this user
        # user_id must come first — it's used in the JOIN before WHERE params
        query_params = [user['user_id']] + params + [req.limit, req.offset]
        cur.execute(f"""
            SELECT
                p.posting_id,
                p.job_title,
                p.berufenet_name,
                p.location_city,
                p.location_state,
                p.qualification_level,
                p.external_url,
                p.extracted_summary,
                p.first_seen_at,
                p.source,
                SUBSTRING(b.kldb FROM 3 FOR 2) as domain_code,
                CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) as ql_level,
                source_metadata->'raw_api_response'->'arbeitgeber'->>'name' as employer_name,
                pi.interested,
                pi.reason as interest_reason
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            LEFT JOIN posting_interest pi ON pi.posting_id = p.posting_id AND pi.user_id = %s
            WHERE {where_sql}
            ORDER BY p.first_seen_at DESC NULLS LAST
            LIMIT %s OFFSET %s
        """, query_params)
        postings = cur.fetchall()

        results = []
        for row in postings:
            domain_name = KLDB_DOMAINS.get(row['domain_code'], 'Sonstige')
            ql_label = QL_LABELS.get(row['ql_level'], f"Level {row['ql_level']}")
            results.append({
                "posting_id": row['posting_id'],
                "job_title": row['job_title'] or row['berufenet_name'] or 'Untitled',
                "berufenet_name": row['berufenet_name'],
                "location": row['location_city'] or row['location_state'] or '',
                "employer": row['employer_name'] or '',
                "domain": domain_name,
                "domain_code": row['domain_code'],
                "domain_color": DOMAIN_COLORS.get(domain_name, '#cccccc'),
                "ql_level": row['ql_level'],
                "ql_label": ql_label,
                "external_url": row['external_url'],
                "summary": row['extracted_summary'] or '',
                "source": row['source'] or '',
                "first_seen": row['first_seen_at'].isoformat() if row['first_seen_at'] else None,
                "interested": row['interested'],  # None, True, or False
            })

        # Lazy verification: queue stale postings for background checking.
        # This runs AFTER we return results — user sees immediate response,
        # stale postings get verified in background for next search.
        result_ids = [r['posting_id'] for r in results]
        stale_ids = find_stale_posting_ids(result_ids, conn)
        if stale_ids:
            queue_stale_verification(stale_ids)

        return {
            "results": results,
            "offset": req.offset,
            "limit": req.limit,
            "has_more": len(results) == req.limit,
        }


# ============================================================
# Posting interest — record interested / not interested
# ============================================================

class PostingInterestRequest(BaseModel):
    posting_id: int
    interested: bool
    reason: Optional[str] = None


@router.post("/search/interest")
def record_interest(
    req: PostingInterestRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """Record the user's interest (or lack thereof) in a posting."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO posting_interest (user_id, posting_id, interested, reason)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, posting_id)
            DO UPDATE SET interested = EXCLUDED.interested,
                          reason = EXCLUDED.reason,
                          created_at = NOW()
            RETURNING interest_id
        """, (user['user_id'], req.posting_id, req.interested, req.reason))
        result = cur.fetchone()
        conn.commit()
        return {"status": "recorded", "interest_id": result['interest_id']}


# ============================================================
# Search intelligence — activity + state ranking + profession ranking
# ============================================================

class IntelligenceRequest(BaseModel):
    domains: Optional[List[str]] = None   # selected KLDB 2-digit codes
    ql: Optional[List[int]] = None
    days: int = 30

@router.post("/search/intelligence")
def search_intelligence(
    req: IntelligenceRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Intelligence panel data for the current search filters.
    Returns: activity (14-day sparkline), states ranking, professions ranking.
    Works with or without domain selection.
    """
    has_domains = bool(req.domains)

    with conn.cursor() as cur:
        # ── 14-day activity (new postings per day) ───────────────
        if has_domains:
            cur.execute("""
                SELECT DATE(p.first_seen_at) AS day, COUNT(*) AS count
                FROM postings p
                JOIN berufenet b ON b.berufenet_id = p.berufenet_id
                WHERE p.enabled = true AND p.invalidated = false
                  AND SUBSTRING(b.kldb FROM 3 FOR 2) = ANY(%s)
                  AND p.first_seen_at > NOW() - INTERVAL '30 days'
                GROUP BY day ORDER BY day
            """, [req.domains])
        else:
            cur.execute("""
                SELECT DATE(p.first_seen_at) AS day, COUNT(*) AS count
                FROM postings p
                WHERE p.enabled = true AND p.invalidated = false
                  AND p.berufenet_id IS NOT NULL
                  AND p.first_seen_at > NOW() - INTERVAL '30 days'
                GROUP BY day ORDER BY day
            """)
        raw_activity = {str(r['day']): r['count'] for r in cur.fetchall()}
        
        # Fill in missing days with zero counts (ensure full 30-day span)
        from datetime import date, timedelta
        today = date.today()
        activity = []
        for i in range(29, -1, -1):  # 30 days, oldest first
            d = today - timedelta(days=i)
            activity.append({"date": str(d), "count": raw_activity.get(str(d), 0)})

        # ── States ranking (fresh_14d from demand_snapshot) ──────
        if has_domains:
            cur.execute("""
                SELECT location_state,
                       SUM(fresh_14d) AS fresh,
                       SUM(total_postings) AS total
                FROM demand_snapshot
                WHERE domain_code = ANY(%s) AND berufenet_id IS NULL
                GROUP BY location_state
                ORDER BY fresh DESC
            """, [req.domains])
        else:
            cur.execute("""
                SELECT location_state,
                       SUM(fresh_14d) AS fresh,
                       SUM(total_postings) AS total
                FROM demand_snapshot
                WHERE berufenet_id IS NULL
                GROUP BY location_state
                ORDER BY fresh DESC
            """)
        states = [
            {"state": r['location_state'], "fresh": r['fresh'], "total": r['total']}
            for r in cur.fetchall()
        ]

        # ── Professions ranking (top 15 by fresh_14d nationally) ─
        if has_domains:
            cur.execute("""
                SELECT berufenet_name AS name,
                       SUM(fresh_14d) AS fresh,
                       SUM(total_postings) AS total
                FROM demand_snapshot
                WHERE domain_code = ANY(%s) AND berufenet_id IS NOT NULL
                GROUP BY berufenet_name
                ORDER BY fresh DESC
                LIMIT 15
            """, [req.domains])
        else:
            cur.execute("""
                SELECT berufenet_name AS name,
                       SUM(fresh_14d) AS fresh,
                       SUM(total_postings) AS total
                FROM demand_snapshot
                WHERE berufenet_id IS NOT NULL
                GROUP BY berufenet_name
                ORDER BY fresh DESC
                LIMIT 15
            """)
        professions = [
            {"name": r['name'], "fresh": r['fresh'], "total": r['total']}
            for r in cur.fetchall()
        ]

    return {
        "activity": activity,
        "states": states,
        "professions": professions,
    }


# ============================================================
# Posting detail — full posting info for modal
# ============================================================

@router.get("/search/posting/{posting_id}")
def get_posting_detail(
    posting_id: int,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """Get full posting details for the detail modal."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                p.posting_id,
                p.job_title,
                p.job_description,
                p.berufenet_name,
                p.location_city,
                p.location_state,
                p.location_country,
                p.qualification_level,
                p.external_url,
                p.extracted_summary,
                p.first_seen_at,
                p.last_seen_at,
                p.source,
                SUBSTRING(b.kldb FROM 3 FOR 2) as domain_code,
                CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) as ql_level,
                source_metadata->'raw_api_response'->'arbeitgeber'->>'name' as employer_name,
                source_metadata->'raw_api_response'->'arbeitgeber'->>'branche' as employer_industry,
                source_metadata->'raw_api_response'->>'eintrittsdatum' as start_date,
                source_metadata->'raw_api_response'->>'befristung' as contract_type,
                source_metadata->'raw_api_response'->'arbeitszeit'->>'text' as work_hours,
                pi.interested,
                pi.reason as interest_reason
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            LEFT JOIN posting_interest pi ON pi.posting_id = p.posting_id AND pi.user_id = %s
            WHERE p.posting_id = %s
        """, (user['user_id'], posting_id))
        row = cur.fetchone()

        if not row:
            return JSONResponse(status_code=404, content={"error": "Posting not found"})

        domain_name = KLDB_DOMAINS.get(row['domain_code'], 'Sonstige')
        return {
            "posting_id": row['posting_id'],
            "job_title": row['job_title'] or row['berufenet_name'] or 'Untitled',
            "job_description": row['job_description'] or '',
            "berufenet_name": row['berufenet_name'],
            "location": ', '.join(filter(None, [row['location_city'], row['location_state'], row['location_country']])),
            "employer": row['employer_name'] or '',
            "employer_industry": row['employer_industry'] or '',
            "domain": domain_name,
            "domain_color": DOMAIN_COLORS.get(domain_name, '#cccccc'),
            "ql_level": row['ql_level'],
            "ql_label": QL_LABELS.get(row['ql_level'], ''),
            "external_url": row['external_url'],
            "summary": row['extracted_summary'] or '',
            "source": row['source'] or '',
            "first_seen": row['first_seen_at'].isoformat() if row['first_seen_at'] else None,
            "last_seen": row['last_seen_at'].isoformat() if row['last_seen_at'] else None,
            "start_date": row['start_date'] or '',
            "contract_type": row['contract_type'] or '',
            "work_hours": row['work_hours'] or '',
            "interested": row['interested'],
        }
