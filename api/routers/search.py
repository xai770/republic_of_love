"""
Search routes — Mira Search: interactive three-panel job search.

Panels: Domain (Berufsfeld) | Map (Leaflet heatmap) | Qualification Level
Cross-filtering: any panel change → single API call → all panels update.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import json
import os
import threading
import logging
import hashlib

import numpy as np
import requests as _requests

from api.deps import get_db, require_user
from lib.posting_verifier import queue_stale_verification, find_stale_posting_ids

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])

# ─── Profession translations (DE → EN) ───────────────────────────────────────
_PROF_TRANS: dict = {}
_PROF_TRANS_MTIME: float = 0.0
_PROF_TRANS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'profession_translations_en.json')
)

def _get_prof_trans() -> dict:
    """Load / hot-reload profession translations; caches per file mtime."""
    global _PROF_TRANS, _PROF_TRANS_MTIME
    try:
        mtime = os.path.getmtime(_PROF_TRANS_PATH)
        if mtime > _PROF_TRANS_MTIME:
            with open(_PROF_TRANS_PATH, 'r', encoding='utf-8') as f:
                _PROF_TRANS = json.load(f)
            _PROF_TRANS_MTIME = mtime
    except (OSError, json.JSONDecodeError):
        pass
    return _PROF_TRANS

# ─── Nominatim proxy ──────────────────────────────────────────────────────────
_GEO_CACHE: dict = {}  # simple in-process cache to respect Nominatim's rate limit
_GEO_HEADERS = {
    'User-Agent': 'TalentYoga/1.0 (https://talent.yoga; kontakt@talent.yoga)',
    'Accept-Language': 'de',
}

@router.get("/geo/search")
def geo_search(q: str = Query(..., min_length=2, max_length=100)):
    """
    Server-side proxy for Nominatim city/address lookup.
    Caches results in-process; enforces User-Agent for OSM usage policy.
    """
    cache_key = q.lower().strip()
    if cache_key in _GEO_CACHE:
        return JSONResponse(_GEO_CACHE[cache_key])

    try:
        resp = _requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'format': 'json', 'countrycodes': 'de', 'limit': 5, 'q': q},
            headers=_GEO_HEADERS,
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Nominatim proxy error: %s", exc)
        return JSONResponse([], status_code=200)

    # Cache up to 2000 entries (memory-cheap strings)
    if len(_GEO_CACHE) > 2000:
        _GEO_CACHE.clear()
    _GEO_CACHE[cache_key] = data
    return JSONResponse(data)

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
# Geo helpers — support single and multi-location radius search
# ============================================================

class GeoLocation(BaseModel):
    """A single lat/lon + radius circle for geo filtering."""
    lat: float
    lon: float
    radius_km: Optional[int] = None


_HAVERSINE_TMPL = """
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
    )) <= %s"""


def _build_geo_where(
    geo_locations: Optional[List[GeoLocation]],
    legacy_lat: Optional[float],
    legacy_lon: Optional[float],
    legacy_radius: Optional[int],
) -> tuple[Optional[str], list]:
    """
    Build an OR-joined haversine WHERE fragment for one or more location circles.
    Accepts both geo_locations array (new) and legacy lat/lon/radius_km (backward compat).
    Returns (sql_fragment_or_None, params_list).
    """
    locs: list[tuple[float, float, int]] = []
    if geo_locations:
        for g in geo_locations:
            if g.lat is not None and g.lon is not None and g.radius_km:
                locs.append((g.lat, g.lon, g.radius_km))
    if not locs and legacy_lat is not None and legacy_lon is not None and legacy_radius:
        locs.append((legacy_lat, legacy_lon, legacy_radius))
    if not locs:
        return None, []
    clauses = [_HAVERSINE_TMPL for _ in locs]
    geo_params: list = []
    for lat, lon, radius_km in locs:
        geo_params.extend([lat, lon, lat, radius_km])
    return '(' + ' OR '.join(clauses) + ')', geo_params


# ─── Posting WHERE builder ───────────────────────────────────────────────────

def _build_posting_where(
    *,
    domains:     Optional[List[str]]  = None,
    professions: Optional[List[str]]  = None,
    profile_ids: Optional[List[int]]  = None,
    ql:          Optional[List[int]]  = None,
    states:      Optional[List[str]]  = None,
    geo_sql:     Optional[str]        = None,
    geo_params:  Optional[list]       = None,
) -> tuple[str, list]:
    """
    Build (WHERE sql, params) for any postings query.

    Three logical groups — omit a group by passing None for all its args:
      Subject  — domains OR professions OR profile_ids
      QL       — qualification level
      Location — states OR radius circle(s)

    All queries must alias:  postings AS p  JOIN berufenet AS b ON b.berufenet_id = p.berufenet_id

    Cross-filter pattern (used in preview):
      • Domain bars  — omit subject             → pass domains/professions/profile_ids=None
      • QL bars      — omit ql                  → pass ql=None
      • Landscape    — omit professions/profile → pass professions/profile_ids=None
    """
    wheres: list[str] = [
        "p.berufenet_id IS NOT NULL",
        "p.enabled = true",
        "p.invalidated = false",
    ]
    params: list = []

    # ── Subject group (domains OR professions OR profile_ids) ─────────────────
    subj: list[str] = []
    if domains:
        subj.append("SUBSTRING(b.kldb FROM 3 FOR 2) = ANY(%s)")
        params.append(domains)
    if professions:
        subj.append("p.berufenet_name = ANY(%s)")
        params.append(professions)
    if profile_ids:
        subj.append("p.posting_id = ANY(%s)")
        params.append(profile_ids)
    if subj:
        wheres.append("(" + " OR ".join(subj) + ")")

    # ── Qualification level ───────────────────────────────────────────────────
    if ql:
        wheres.append("CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) = ANY(%s)")
        params.append(ql)

    # ── Location group (states OR geo circles) ────────────────────────────────
    loc: list[str] = []
    if states:
        loc.append("p.location_state = ANY(%s)")
        params.append(states)
    if geo_sql:
        loc.append(geo_sql)
        params.extend(geo_params or [])
    if loc:
        wheres.append("(" + " OR ".join(loc) + ")")

    return " AND ".join(wheres), params


# ============================================================
# Search preview endpoint
# ============================================================

class SearchRequest(BaseModel):
    domains: Optional[List[str]] = None   # KLDB 2-digit codes
    ql: Optional[List[int]] = None        # qualification levels 1-4
    lat: Optional[float] = None           # legacy single-location (kept for compat)
    lon: Optional[float] = None
    radius_km: Optional[int] = None
    states: Optional[List[str]] = None    # Bundesland filter (location_state)
    geo_locations: Optional[List[GeoLocation]] = None  # multi-location (OR-joined)
    professions: Optional[List[str]] = None  # berufenet_name filter (clicked from intel)
    profile_ids: Optional[List[int]] = None   # posting_id list from profile match (OR'd with professions)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "domains": ["43", "81"],
                "ql": [2, 3],
                "lat": 48.14,
                "lon": 11.58,
                "radius_km": 50
            }
        }
    )


@router.post("/search/preview")
def search_preview(
    req: SearchRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Cross-filter search preview.
    Returns: total, by_domain, by_ql, heatmap, markers, fresh_count.
    All filters optional — no filters = everything.

    Cross-filter principle:
      • Domain bars  show counts for QL + location only  (subject excluded)
      • QL bars      show counts for subject + location   (ql excluded)
      • Total        uses all filters
    """
    with conn.cursor() as cur:
        # Resolve location once — shared by all sub-queries
        geo_sql, geo_params = _build_geo_where(
            req.geo_locations, req.lat, req.lon, req.radius_km
        )
        loc = dict(states=req.states, geo_sql=geo_sql, geo_params=geo_params)

        # ── 1. Total (all filters) ────────────────────────────────────────────
        where_sql, params = _build_posting_where(
            domains=req.domains, professions=req.professions, profile_ids=req.profile_ids,
            ql=req.ql, **loc
        )
        cur.execute(f"""
            SELECT COUNT(*) AS total
            FROM postings p JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
        """, params)
        total = cur.fetchone()['total']

        # ── 2. Landscape total (no profession/profile; used for "374 of 10,652") ─
        # Only computed when a profession is active but no profile — so the UI
        # can show "N of M" where M is the broader domain+QL+location pool.
        landscape_total = None
        if req.professions and not req.profile_ids:
            ls_where, ls_params = _build_posting_where(
                domains=req.domains, ql=req.ql, **loc
            )
            cur.execute(f"""
                SELECT COUNT(*) AS total
                FROM postings p JOIN berufenet b ON b.berufenet_id = p.berufenet_id
                WHERE {ls_where}
            """, ls_params)
            landscape_total = cur.fetchone()['total']

        # ── 3. Domain bars (cross-filter: QL + location only, no subject) ─────
        dom_where, dom_params = _build_posting_where(ql=req.ql, **loc)
        cur.execute(f"""
            SELECT SUBSTRING(b.kldb FROM 3 FOR 2) AS code, COUNT(*) AS count
            FROM postings p JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {dom_where}
            GROUP BY code ORDER BY count DESC
        """, dom_params)
        domain_agg: dict = {}
        for row in cur.fetchall():
            name = KLDB_DOMAINS.get(row['code'], f'Sonstige ({row["code"]})')
            domain_agg[name] = domain_agg.get(name, 0) + row['count']
        by_domain = [
            {
                "name": name,
                "count": count,
                "color": DOMAIN_COLORS.get(name, '#cccccc'),
                "codes": DOMAIN_NAMES.get(name, []),
                "selected": bool(
                    req.domains and
                    any(c in req.domains for c in DOMAIN_NAMES.get(name, []))
                ),
            }
            for name, count in sorted(domain_agg.items(), key=lambda x: x[0])
        ]

        # ── 4. QL bars (cross-filter: subject + location only, no ql filter) ──
        ql_where, ql_params = _build_posting_where(
            domains=req.domains, professions=req.professions, profile_ids=req.profile_ids,
            **loc
        )
        cur.execute(f"""
            SELECT CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) AS level,
                   COUNT(*) AS count
            FROM postings p JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {ql_where}
              AND SUBSTRING(b.kldb FROM 7 FOR 1) ~ '^[1-4]$'
            GROUP BY level ORDER BY level
        """, ql_params)
        by_ql = [
            {
                "level": row['level'],
                "label": QL_LABELS.get(row['level'], f"Level {row['level']}"),
                "count": row['count'],
                "selected": bool(req.ql and row['level'] in req.ql),
            }
            for row in cur.fetchall()
        ]

        # ── 5. Heatmap (all filters) ──────────────────────────────────────────
        cur.execute(f"""
            SELECT
                ROUND(CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS NUMERIC), 2) AS lat,
                ROUND(CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS NUMERIC), 2) AS lon,
                COUNT(*) AS weight
            FROM postings p JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' IS NOT NULL
            GROUP BY lat, lon
        """, params)
        heatmap = [[float(r['lat']), float(r['lon']), r['weight']] for r in cur.fetchall()]

        # ── 6. Map markers (all filters, most recent 500 with coords) ─────────
        cur.execute(f"""
            SELECT
                p.posting_id,
                p.job_title,
                p.location_city,
                source_metadata->'raw_api_response'->'arbeitgeber'->>'name' AS employer,
                CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT) AS lat,
                CAST(source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS FLOAT) AS lon
            FROM postings p JOIN berufenet b ON b.berufenet_id = p.berufenet_id
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

        # ── 7. Freshness (all filters, last 7 days) ───────────────────────────
        cur.execute(f"""
            SELECT COUNT(*) AS fresh
            FROM postings p JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND (source_metadata->>'published_date')::date >= CURRENT_DATE - INTERVAL '7 days'
        """, params)
        fresh_count = cur.fetchone()['fresh']

        return {
            "total": total,
            "landscape_total": landscape_total,
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
    lat: Optional[float] = None           # legacy single-location (kept for compat)
    lon: Optional[float] = None
    radius_km: Optional[int] = None
    states: Optional[List[str]] = None    # Bundesland filter
    geo_locations: Optional[List[GeoLocation]] = None  # multi-location (OR-joined)
    professions: Optional[List[str]] = None  # berufenet_name filter
    profile_ids: Optional[List[int]] = None   # posting_id list from profile match (OR'd with professions)
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
        geo_sql, geo_params = _build_geo_where(
            req.geo_locations, req.lat, req.lon, req.radius_km
        )
        where_sql, params = _build_posting_where(
            domains=req.domains, professions=req.professions, profile_ids=req.profile_ids,
            ql=req.ql, states=req.states, geo_sql=geo_sql, geo_params=geo_params,
        )

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

        profile_id_set = set(req.profile_ids) if req.profile_ids else set()

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
                "profile_match": row['posting_id'] in profile_id_set,
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
            {"name": r['name'], "fresh": r['fresh'], "total": r['total'],
             "name_en": _get_prof_trans().get(r['name'])}
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


# ============================================================
# Stream B — Profile similarity search
# ============================================================

@router.get("/search/profile")
def search_profile(
    user: dict = Depends(require_user),
    conn=Depends(get_db),
    limit: int = 500,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[int] = None,
    states: Optional[List[str]] = Query(default=None),
):
    """
    Stream B: semantic search based on the yogi's skill profile.

    Two modes (transparently selected):

    CLARA mode  — when Clara has precomputed matches for this profile
    (profile_posting_matches with computed_at within the last 7 days),
    return those posting_ids directly. Clara ran against ALL 173K postings;
    this is the high-quality path.

    RUNTIME mode — fallback when Clara hasn't run yet. Pulls a
    geographically stratified candidate pool (top 350 per state,
    ~5 600 candidates) and scores by cosine similarity against the
    profile embedding. Stratified so Berlin/Bayern are not drowned
    out by whatever states the nightly AA fetch happened to finish on.

    Returns {available: false, reason: ...} when the profile is not
    ready (no skills, no cached embedding).
    """
    # ── 1. Load profile skills ────────────────────────────────────
    with conn.cursor() as cur:
        cur.execute("""
            SELECT skill_keywords, current_title, profile_summary, experience_level, location
            FROM profiles
            WHERE user_id = %s AND skill_keywords IS NOT NULL
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 1
        """, (user['user_id'],))
        profile = cur.fetchone()

    if not profile:
        return {"available": False, "results": [], "reason": "no_profile"}

    raw_skills = profile['skill_keywords']
    if isinstance(raw_skills, list):
        skills = raw_skills
    elif isinstance(raw_skills, dict):
        skills = raw_skills.get('keywords', [])
    else:
        skills = []

    if not skills:
        return {"available": False, "results": [], "reason": "no_skills"}

    # ── 2. Build profile text (same convention as Clara) ─────────
    parts = []
    if profile['current_title']:
        parts.append(profile['current_title'])
    if skills:
        parts.append(' '.join(str(s) for s in skills))
    if profile['profile_summary']:
        parts.append(profile['profile_summary'][:500])
    if profile['experience_level']:
        parts.append(profile['experience_level'])
    profile_text = ' | '.join(filter(None, parts)).strip()

    if not profile_text:
        return {"available": False, "results": [], "reason": "empty_profile_text"}

    # ── 3. Look up profile embedding (content-addressed cache) ───
    text_clean = profile_text.lower().strip()
    profile_hash = hashlib.sha256(text_clean.encode()).hexdigest()[:32]

    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding FROM embeddings WHERE text_hash = %s",
            (profile_hash,)
        )
        row = cur.fetchone()

    if not row:
        # Not yet cached — Adele will compute and cache on next profile update
        return {"available": False, "results": [], "reason": "embedding_pending"}

    profile_emb = np.array(row['embedding'], dtype=np.float32)
    profile_norm = float(np.linalg.norm(profile_emb))
    if profile_norm == 0:
        return {"available": False, "results": [], "reason": "zero_embedding"}

    # ── 4a. CLARA mode — use precomputed matches if recent (< 30 days old) ─
    # Clara runs nightly across ALL postings; her results are higher quality
    # and geographically unbiased. Use them when available.
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ppm.posting_id
            FROM profiles pr
            JOIN profile_posting_matches ppm ON ppm.profile_id = pr.profile_id
            WHERE pr.user_id = %s
              AND ppm.computed_at > NOW() - INTERVAL '30 days'
            ORDER BY ppm.computed_at DESC
            LIMIT 2000
        """, (user['user_id'],))
        clara_rows = cur.fetchall()

    if clara_rows:
        # Return Clara's results in the same shape the frontend expects:
        # [{posting_id: x}, ...] — the frontend only reads r.posting_id.
        # The results query will filter by location/ql/domain on top of these.
        return {
            "available": True,
            "results": [{"posting_id": r['posting_id']} for r in clara_rows],
            "source": "clara",
            "profile_location": profile.get('location') or None,
            "experience_level": profile.get('experience_level') or None,
        }

    # ── 4b. RUNTIME mode — stratified candidate pool ─────────────────────
    # Pull the top 350 most-recent active postings PER STATE.
    # ~16 states × 350 = ~5 600 candidates, geographically representative.
    # This avoids the "5000 most-recent = whatever state AA fetched last"
    # recency bias that made Bayern / Berlin / BW invisible in the pool.
    #
    # Location is NOT pre-filtered here. The results query handles that.
    # Invariant: adding any location filter can only reduce counts, not increase.
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                p.posting_id,
                p.job_title,
                p.location_city,
                p.location_state,
                p.external_url,
                p.extracted_summary,
                p.first_seen_at,
                p.source,
                SUBSTRING(b.kldb FROM 3 FOR 2)                       AS domain_code,
                CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER)       AS ql_level,
                source_metadata->'raw_api_response'->'arbeitgeber'->>'name' AS employer_name,
                p.berufenet_name,
                COALESCE(
                    p.extracted_summary,
                    p.job_description,
                    p.job_title,
                    p.berufenet_name
                ) AS match_text
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY location_state
                           ORDER BY first_seen_at DESC NULLS LAST
                       ) AS state_rank
                FROM postings
                WHERE enabled = true
                  AND invalidated = false
                  AND berufenet_id IS NOT NULL
            ) p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE p.state_rank <= 350
        """)
        candidates = list(cur.fetchall())

    if not candidates:
        return {"available": True, "results": []}

    # ── 5. Batch-fetch embeddings for candidates ─────────────────
    candidate_hashes = []
    for c in candidates:
        mt = c['match_text'] or ''
        h = hashlib.sha256(mt.lower().strip().encode()).hexdigest()[:32]
        candidate_hashes.append(h)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT text_hash, embedding FROM embeddings WHERE text_hash = ANY(%s)",
            (candidate_hashes,)
        )
        emb_map = {r['text_hash']: r['embedding'] for r in cur.fetchall()}

    # ── 6. Cosine similarity scoring ─────────────────────────────
    scored = []
    for c, h in zip(candidates, candidate_hashes):
        emb_data = emb_map.get(h)
        if emb_data is None:
            continue
        posting_emb = np.array(emb_data, dtype=np.float32)
        posting_norm = float(np.linalg.norm(posting_emb))
        if posting_norm == 0:
            continue
        score = float(np.dot(profile_emb, posting_emb) / (profile_norm * posting_norm))
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    # ── 7. Format response ────────────────────────────────────────
    seen_ids: set = set()
    results = []
    for score, row in scored:
        if len(results) >= limit:
            break
        pid = row['posting_id']
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        domain_name = KLDB_DOMAINS.get(row['domain_code'], 'Sonstige')
        ql_level = row['ql_level']
        results.append({
            "posting_id": pid,
            "job_title": row['job_title'] or row['berufenet_name'] or 'Untitled',
            "berufenet_name": row['berufenet_name'],
            "location": row['location_city'] or row['location_state'] or '',
            "employer": row['employer_name'] or '',
            "domain": domain_name,
            "domain_code": row['domain_code'],
            "domain_color": DOMAIN_COLORS.get(domain_name, '#cccccc'),
            "ql_level": ql_level,
            "ql_label": QL_LABELS.get(ql_level, '') if ql_level else '',
            "external_url": row['external_url'],
            "summary": row['extracted_summary'] or '',
            "source": row['source'] or '',
            "first_seen": row['first_seen_at'].isoformat() if row['first_seen_at'] else None,
            "score": round(score, 3),
        })

    return {
        "available": True,
        "results": results,
        "source": "runtime",
        "profile_location": profile.get('location') or None,
        "experience_level": profile.get('experience_level') or None,
    }

