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
import re as _re
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
    'Nicht klassifiziert': '#999999',
}

QL_LABELS = {
    0: 'Nicht klass.',
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
            CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT)
        )) *
        cos(radians(
            CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS FLOAT)
        ) - radians(%s)) +
        sin(radians(%s)) * sin(radians(
            CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT)
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
    require_berufenet: bool           = False,
) -> tuple[str, list]:
    """
    Build (WHERE sql, params) for any postings query.

    Three logical groups — omit a group by passing None for all its args:
      Subject  — domains OR professions OR profile_ids
      QL       — qualification level
      Location — states OR radius circle(s)

    All queries must alias:  postings AS p  LEFT JOIN berufenet AS b ON ...

    Unclassified postings (berufenet_id IS NULL) pass through domain/QL
    filters so banking/IT roles without Berufenet mappings remain visible.
    Set require_berufenet=True to restore the hard gate where needed.

    Cross-filter pattern (used in preview):
      • Domain bars  — omit subject             → pass domains/professions/profile_ids=None
      • QL bars      — omit ql                  → pass ql=None
      • Landscape    — omit professions/profile → pass professions/profile_ids=None
    """
    wheres: list[str] = [
        "p.enabled = true",
        "p.invalidated = false",
    ]
    if require_berufenet:
        wheres.append("p.berufenet_id IS NOT NULL")
    params: list = []

    # ── Subject group (domains OR professions OR profile_ids) ─────────────────
    # Unclassified postings (no berufenet_id) pass through domain filters.
    subj: list[str] = []
    if domains:
        subj.append("(SUBSTRING(b.kldb FROM 3 FOR 2) = ANY(%s) OR b.berufenet_id IS NULL)")
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
    # Unclassified postings pass through QL filters (assumed Spezialist/Experte).
    if ql:
        wheres.append("(CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER) = ANY(%s) OR b.berufenet_id IS NULL)")
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
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
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
                FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
                WHERE {ls_where}
            """, ls_params)
            landscape_total = cur.fetchone()['total']

        # ── 3. Domain bars (cross-filter: QL + location only, no subject) ─────
        dom_where, dom_params = _build_posting_where(ql=req.ql, **loc)
        cur.execute(f"""
            SELECT SUBSTRING(b.kldb FROM 3 FOR 2) AS code, COUNT(*) AS count
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {dom_where}
              AND b.berufenet_id IS NOT NULL
            GROUP BY code ORDER BY count DESC
        """, dom_params)
        domain_agg: dict = {}
        for row in cur.fetchall():
            name = KLDB_DOMAINS.get(row['code'], f'Sonstige ({row["code"]})')
            domain_agg[name] = domain_agg.get(name, 0) + row['count']
        # Count unclassified postings for a virtual "Unclassified" domain bar
        cur.execute(f"""
            SELECT COUNT(*) AS count
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {dom_where}
              AND b.berufenet_id IS NULL
        """, dom_params)
        unclassified_count = cur.fetchone()['count']
        if unclassified_count > 0:
            domain_agg['Nicht klassifiziert'] = unclassified_count
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
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {ql_where}
              AND b.berufenet_id IS NOT NULL
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
        # Add an "Unclassified" bucket so the user sees the gap
        cur.execute(f"""
            SELECT COUNT(*) AS count
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {ql_where}
              AND b.berufenet_id IS NULL
        """, ql_params)
        unclass_ql = cur.fetchone()['count']
        if unclass_ql > 0:
            by_ql.append({
                "level": 0,
                "label": "Nicht klass.",
                "count": unclass_ql,
                "selected": bool(req.ql and 0 in req.ql),
            })

        # ── 5. Heatmap (all filters) ──────────────────────────────────────────
        cur.execute(f"""
            SELECT
                ROUND(CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS NUMERIC), 2) AS lat,
                ROUND(CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS NUMERIC), 2) AS lon,
                COUNT(*) AS weight
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' IS NOT NULL
            GROUP BY lat, lon
        """, params)
        heatmap_rows = cur.fetchall()
        # Cap heatmap at 5000 grid cells to limit browser canvas memory
        if len(heatmap_rows) > 5000:
            heatmap_rows = sorted(heatmap_rows, key=lambda r: r['weight'], reverse=True)[:5000]
        heatmap = [[float(r['lat']), float(r['lon']), r['weight']] for r in heatmap_rows]

        # ── 6. Map markers (all filters, most recent 200 with coords) ─────────
        cur.execute(f"""
            SELECT
                p.posting_id,
                p.job_title,
                p.location_city,
                p.source_metadata->'raw_api_response'->'arbeitgeber'->>'name' AS employer,
                CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS FLOAT) AS lat,
                CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS FLOAT) AS lon
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' IS NOT NULL
            ORDER BY p.first_seen_at DESC NULLS LAST
            LIMIT 200
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
            FROM postings p LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE {where_sql}
              AND (p.source_metadata->>'published_date')::date >= CURRENT_DATE - INTERVAL '7 days'
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
# Profile scope — infer search filters from yogi's profile
# ============================================================

EXP_TO_QL = {'junior': 2, 'mid': 3, 'senior': 4, 'lead': 4, 'executive': 4, 'expert': 4}

@router.get("/search/profile-scope")
def profile_scope(
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Infer search scope from the yogi's profile.

    Returns:
        {
          "available": true,
          "domains":  ["71"],        // KLDB 2-digit codes
          "ql":       [2, 3, 4],     // qualification levels
          "location": "Berlin",      // city name (for geocoding client-side)
          "experience_level": "mid",
          "profile_id": 41
        }

    When no usable profile exists:
        {"available": false, "reason": "..."}
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT profile_id, current_title, desired_roles,
                   experience_level, location
            FROM profiles
            WHERE user_id = %s
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 1
        """, (user['user_id'],))
        profile = cur.fetchone()

    if not profile:
        return {"available": False, "reason": "no_profile"}

    # ── Infer domain codes from title + desired_roles tokens ──────
    raw_title = profile['current_title'] or ''
    raw_roles = profile['desired_roles'] or []
    title_parts = _re.split(r'[\s/,;|]+', raw_title)
    term_pool = [t for t in list(title_parts) + list(raw_roles) if len(t) >= 4]

    inferred_domains: list = []
    if term_pool:
        like_clauses = ' OR '.join(['name ILIKE %s'] * len(term_pool))
        like_params = ['%' + t + '%' for t in term_pool]
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT DISTINCT SUBSTRING(kldb FROM 3 FOR 2) AS domain_code"
                f" FROM berufenet WHERE {like_clauses}",
                like_params,
            )
            inferred_domains = [r['domain_code'] for r in cur.fetchall()]

    # ── Infer QL from experience_level ────────────────────────────
    exp = (profile['experience_level'] or '').lower()
    base_ql = EXP_TO_QL.get(exp)
    inferred_ql = []
    if base_ql:
        min_ql = max(1, base_ql - 1)
        inferred_ql = list(range(min_ql, 5))  # e.g. mid→[2,3,4]

    return {
        "available": True,
        "domains": inferred_domains,
        "ql": inferred_ql,
        "location": profile['location'] or None,
        "experience_level": profile['experience_level'] or None,
        "profile_id": profile['profile_id'],
    }


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
    score: bool = False                   # request cosine scoring from profile embedding


def _attach_cosine_scores(
    postings: list,
    results: list,
    user_id: int,
    conn,
) -> None:
    """
    Decorate *results* in-place with a ``score`` field (0.0–1.0).

    Loads the caller's profile embedding once, then batch-scores every
    posting on the current page via cosine similarity.  Results that
    cannot be scored (missing embedding) get ``score: None``.
    """
    import hashlib as _hl

    # ── 1. Load profile → build text → look up embedding ─────────
    with conn.cursor() as cur:
        cur.execute("""
            SELECT skill_keywords, current_title, profile_summary,
                   experience_level
            FROM profiles
            WHERE user_id = %s AND skill_keywords IS NOT NULL
            ORDER BY updated_at DESC NULLS LAST LIMIT 1
        """, (user_id,))
        profile = cur.fetchone()

    if not profile:
        return

    raw_skills = profile['skill_keywords']
    if isinstance(raw_skills, list):
        skills = raw_skills
    elif isinstance(raw_skills, dict):
        skills = raw_skills.get('keywords', [])
    else:
        skills = []

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
        return

    profile_hash = _hl.sha256(profile_text.lower().strip().encode()).hexdigest()[:32]

    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding FROM embeddings WHERE text_hash = %s",
            (profile_hash,),
        )
        row = cur.fetchone()

    if not row:
        return

    profile_emb = np.array(row['embedding'], dtype=np.float32)
    profile_norm = float(np.linalg.norm(profile_emb))
    if profile_norm == 0:
        return

    # ── 2. Batch-fetch posting embeddings via SQL join ────────────
    # Use the same normalize_text_python() + SHA256 path that the
    # embedding actor wrote, so hashes match exactly.
    posting_ids = [p['posting_id'] for p in postings]

    with conn.cursor() as cur:
        cur.execute("""
            SELECT pfm.posting_id, e.embedding
            FROM postings_for_matching pfm
            JOIN embeddings e ON e.text_hash = LEFT(ENCODE(SHA256(
                CONVERT_TO(normalize_text_python(pfm.match_text), 'UTF8')
            ), 'hex'), 32)
            WHERE pfm.posting_id = ANY(%s)
        """, (posting_ids,))
        emb_map = {r['posting_id']: r['embedding'] for r in cur.fetchall()}

    # ── 3. Cosine similarity → attach to results ─────────────────
    for res, row in zip(results, postings):
        emb_data = emb_map.get(row['posting_id'])
        if emb_data is None:
            res['score'] = None
            continue
        posting_emb = np.array(emb_data, dtype=np.float32)
        posting_norm = float(np.linalg.norm(posting_emb))
        if posting_norm == 0:
            res['score'] = None
            continue
        cosine = float(np.dot(profile_emb, posting_emb) / (profile_norm * posting_norm))
        res['score'] = round(cosine, 3)


@router.post("/search/results")
def search_results(
    req: SearchResultsRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Return actual posting records matching the current filters.
    Paginated with offset/limit. Returns posting details + user interest status.

    When score=true, results are ranked by cosine similarity (profile → posting
    embedding) instead of recency. The server scores ALL matching postings in
    a single pass and paginates by score rank — so page 2 truly shows the
    next-best matches, not the next-newest.
    """
    with conn.cursor() as cur:
        geo_sql, geo_params = _build_geo_where(
            req.geo_locations, req.lat, req.lon, req.radius_km
        )
        where_sql, params = _build_posting_where(
            domains=req.domains, professions=req.professions, profile_ids=req.profile_ids,
            ql=req.ql, states=req.states, geo_sql=geo_sql, geo_params=geo_params,
        )

        # ── Score-ranked mode ─────────────────────────────────────────────
        # When score=true, load ALL matching postings, batch-score via cosine
        # similarity against the user's profile embedding, then paginate the
        # scored list. This is the "show me what's relevant" path.
        if req.score:
            return _score_ranked_results(req, user, conn, where_sql, params)

        # ── Recency-ranked mode (default) ─────────────────────────────────
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
            LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            LEFT JOIN posting_interest pi ON pi.posting_id = p.posting_id AND pi.user_id = %s
            WHERE {where_sql}
            ORDER BY p.first_seen_at DESC NULLS LAST
            LIMIT %s OFFSET %s
        """, query_params)
        postings = cur.fetchall()

        profile_id_set = set(req.profile_ids) if req.profile_ids else set()

        results = []
        for row in postings:
            domain_name = KLDB_DOMAINS.get(row['domain_code'], 'Nicht klassifiziert') if row['domain_code'] else 'Nicht klassifiziert'
            ql_label = QL_LABELS.get(row['ql_level'], '') if row['ql_level'] else ''
            results.append({
                "posting_id": row['posting_id'],
                "job_title": row['job_title'] or row['berufenet_name'] or 'Untitled',
                "berufenet_name": row['berufenet_name'],
                "location": row['location_city'] or row['location_state'] or '',
                "employer": row['employer_name'] or '',
                "domain": domain_name,
                "domain_code": row['domain_code'] or '',
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
        result_ids = [r['posting_id'] for r in results]
        stale_ids = find_stale_posting_ids(result_ids, conn)
        if stale_ids:
            queue_stale_verification(stale_ids)

        return {
            "results": results,
            "offset": req.offset,
            "limit": req.limit,
            "has_more": len(results) == req.limit,
            "sort": "recency",
        }


def _score_ranked_results(
    req: 'SearchResultsRequest',
    user: dict,
    conn,
    where_sql: str,
    params: list,
) -> dict:
    """
    Score-ranked search: fetch all matching postings, compute cosine similarity
    against the user's profile embedding, sort by score DESC, then paginate.
    """
    import hashlib as _hl

    # ── 1. Load profile embedding ────────────────────────────────
    with conn.cursor() as cur:
        cur.execute("""
            SELECT skill_keywords, current_title, profile_summary,
                   experience_level
            FROM profiles
            WHERE user_id = %s AND skill_keywords IS NOT NULL
            ORDER BY updated_at DESC NULLS LAST LIMIT 1
        """, (user['user_id'],))
        profile = cur.fetchone()

    if not profile:
        # No profile → fall back to recency sort
        req_copy = SearchResultsRequest(**req.model_dump())
        req_copy.score = False
        return search_results(req_copy, user, conn)

    raw_skills = profile['skill_keywords']
    if isinstance(raw_skills, list):
        skills = raw_skills
    elif isinstance(raw_skills, dict):
        skills = raw_skills.get('keywords', [])
    else:
        skills = []

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
        req_copy = SearchResultsRequest(**req.model_dump())
        req_copy.score = False
        return search_results(req_copy, user, conn)

    profile_hash = _hl.sha256(profile_text.lower().strip().encode()).hexdigest()[:32]

    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding FROM embeddings WHERE text_hash = %s",
            (profile_hash,),
        )
        row = cur.fetchone()

    if not row:
        req_copy = SearchResultsRequest(**req.model_dump())
        req_copy.score = False
        return search_results(req_copy, user, conn)

    profile_emb = np.array(row['embedding'], dtype=np.float32)
    profile_norm = float(np.linalg.norm(profile_emb))
    if profile_norm == 0:
        req_copy = SearchResultsRequest(**req.model_dump())
        req_copy.score = False
        return search_results(req_copy, user, conn)

    # ── 2. Fetch all matching postings + their embeddings in one query ─
    with conn.cursor() as cur:
        query_params = [user['user_id']] + params
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
                p.source_metadata->'raw_api_response'->'arbeitgeber'->>'name' as employer_name,
                pi.interested,
                pi.reason as interest_reason,
                e.embedding
            FROM postings p
            LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            LEFT JOIN posting_interest pi ON pi.posting_id = p.posting_id AND pi.user_id = %s
            LEFT JOIN postings_for_matching pfm ON pfm.posting_id = p.posting_id
            LEFT JOIN embeddings e ON e.text_hash = LEFT(ENCODE(SHA256(
                CONVERT_TO(normalize_text_python(pfm.match_text), 'UTF8')
            ), 'hex'), 32)
            WHERE {where_sql}
        """, query_params)
        all_postings = cur.fetchall()

    # ── 3. Score and sort ────────────────────────────────────────
    profile_id_set = set(req.profile_ids) if req.profile_ids else set()
    scored_results = []

    for row in all_postings:
        emb_data = row['embedding']
        score = None
        if emb_data is not None:
            posting_emb = np.array(emb_data, dtype=np.float32)
            posting_norm = float(np.linalg.norm(posting_emb))
            if posting_norm > 0:
                score = float(np.dot(profile_emb, posting_emb) / (profile_norm * posting_norm))
                score = round(score, 3)

        domain_name = KLDB_DOMAINS.get(row['domain_code'], 'Nicht klassifiziert') if row['domain_code'] else 'Nicht klassifiziert'
        ql_label = QL_LABELS.get(row['ql_level'], '') if row['ql_level'] else ''
        scored_results.append({
            "posting_id": row['posting_id'],
            "job_title": row['job_title'] or row['berufenet_name'] or 'Untitled',
            "berufenet_name": row['berufenet_name'],
            "location": row['location_city'] or row['location_state'] or '',
            "employer": row['employer_name'] or '',
            "domain": domain_name,
            "domain_code": row['domain_code'] or '',
            "domain_color": DOMAIN_COLORS.get(domain_name, '#cccccc'),
            "ql_level": row['ql_level'],
            "ql_label": ql_label,
            "external_url": row['external_url'],
            "summary": row['extracted_summary'] or '',
            "source": row['source'] or '',
            "first_seen": row['first_seen_at'].isoformat() if row['first_seen_at'] else None,
            "interested": row['interested'],
            "profile_match": row['posting_id'] in profile_id_set,
            "score": score,
        })

    # Sort: scored postings first (by score DESC), then unscored by recency
    scored_results.sort(
        key=lambda r: (r['score'] is not None, r['score'] or 0),
        reverse=True,
    )

    # ── 4. Paginate ──────────────────────────────────────────────
    page = scored_results[req.offset : req.offset + req.limit]

    # Lazy verification
    result_ids = [r['posting_id'] for r in page]
    stale_ids = find_stale_posting_ids(result_ids, conn)
    if stale_ids:
        queue_stale_verification(stale_ids)

    return {
        "results": page,
        "offset": req.offset,
        "limit": req.limit,
        "has_more": (req.offset + req.limit) < len(scored_results),
        "total_scored": len(scored_results),
        "sort": "score",
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
            LEFT JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            LEFT JOIN posting_interest pi ON pi.posting_id = p.posting_id AND pi.user_id = %s
            WHERE p.posting_id = %s
        """, (user['user_id'], posting_id))
        row = cur.fetchone()

        if not row:
            return JSONResponse(status_code=404, content={"error": "Posting not found"})

        domain_name = KLDB_DOMAINS.get(row['domain_code'], 'Nicht klassifiziert') if row['domain_code'] else 'Nicht klassifiziert'
        ql_level = row['ql_level'] if row['ql_level'] else 0
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
            "ql_level": ql_level,
            "ql_label": QL_LABELS.get(ql_level, ''),
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
    (profile_posting_matches with computed_at within the last 30 days),
    return those posting_ids directly. Clara ran against ALL 173K postings;
    this is the high-quality path.

    RUNTIME mode — fallback when Clara hasn't run yet.

      Step 1 — Domain inference (retrieve):
        Tokenise profile.current_title + desired_roles (words ≥ 4 chars).
        ILIKE-match tokens against berufenet.name to extract domain codes.
        German berufenet names contain loanwords (Software, Manager, Cloud,
        Data, IT, Consultant) that survive English title tokenisation.
        Result: a domain-relevant pool of 5K–20K postings.

      Step 2 — Cosine ranking (rerank):
        Fetch embeddings for the domain pool, score by cosine similarity
        against the profile embedding, return top N.

    This is the retrieve-then-rerank pattern. Every candidate in the pool
    is a priori domain-relevant; the embedding scorer only needs to judge
    fit within that relevant set, not filter out nursing/logistics/trades.

    Fallback: if domain inference produces nothing (rare, exotic titles),
    reverts to the stratified geographic pool (top 350 per state ≈ 5 600
    candidates). Stratified so Berlin/Bayern are not drowned out by
    whatever states the nightly AA fetch happened to finish on.

    Returns {available: false, reason: ...} when the profile is not
    ready (no skills, no cached embedding).
    """
    # ── 1. Load profile skills ────────────────────────────────────
    with conn.cursor() as cur:
        cur.execute("""
            SELECT skill_keywords, current_title, profile_summary,
                   experience_level, location, desired_roles
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
    # Minimum threshold: if Clara has fewer than 50 matches, the pipeline
    # likely hasn't finished a full cycle yet — fall through to runtime mode
    # which returns hundreds of cosine-ranked candidates immediately.
    CLARA_MIN_MATCHES = 50
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

    if len(clara_rows) >= CLARA_MIN_MATCHES:
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

    # ── 4b. RUNTIME mode — domain-inferred candidate pool ───────────────────
    # Retrieve-then-rerank:
    #   1. Infer relevant domain codes from profile title / desired_roles
    #      by ILIKE-matching tokens against berufenet.name.
    #   2. Pull ALL active postings in those domains.
    #   3. Score by cosine similarity → return top N.
    #
    # Fallback: if no domains are inferred (exotic/untranslatable titles),
    # revert to stratified geographic sampling (top 350 per state ≈ 5 600).

    # ── Infer domain codes from title tokens ──────────────────────
    import re as _re
    raw_title   = profile.get('current_title') or ''
    raw_roles   = profile.get('desired_roles') or []
    title_parts = _re.split(r'[\s/,;|]+', raw_title)
    term_pool   = [t for t in list(title_parts) + list(raw_roles) if len(t) >= 4]

    inferred_domains: list = []
    if term_pool:
        like_clauses = ' OR '.join(['name ILIKE %s'] * len(term_pool))
        like_params  = ['%' + t + '%' for t in term_pool]
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT DISTINCT SUBSTRING(kldb FROM 3 FOR 2) AS domain_code"
                f" FROM berufenet WHERE {like_clauses}",
                like_params,
            )
            inferred_domains = [r['domain_code'] for r in cur.fetchall()]

    # ── Build candidate pool SQL ──────────────────────────────────
    _POSTING_COLS = """
                p.posting_id,
                p.job_title,
                p.location_city,
                p.location_state,
                p.external_url,
                p.extracted_summary,
                p.first_seen_at,
                p.source,
                SUBSTRING(b.kldb FROM 3 FOR 2)                        AS domain_code,
                CAST(SUBSTRING(b.kldb FROM 7 FOR 1) AS INTEGER)        AS ql_level,
                source_metadata->'raw_api_response'->'arbeitgeber'->>'name' AS employer_name,
                p.berufenet_name,
                COALESCE(
                    p.extracted_summary,
                    p.job_description,
                    p.job_title,
                    p.berufenet_name
                ) AS match_text"""

    if inferred_domains:
        # Domain-inferred pool — all active postings in the relevant domains.
        # No geographic pre-filter; the results query handles location later.
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {_POSTING_COLS}
                FROM postings p
                JOIN berufenet b ON b.berufenet_id = p.berufenet_id
                WHERE p.enabled = true
                  AND p.invalidated = false
                  AND p.berufenet_id IS NOT NULL
                  AND SUBSTRING(b.kldb FROM 3 FOR 2) = ANY(%s)
            """, (inferred_domains,))
            candidates = list(cur.fetchall())
    else:
        # Stratified fallback — top 350 most-recent per state ≈ 5 600 total.
        # Used when title/roles produce no domain signal (rare).
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {_POSTING_COLS}
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
        "runtime_pool": "domain" if inferred_domains else "stratified",
        "inferred_domains": inferred_domains or None,
        "profile_location": profile.get('location') or None,
        "experience_level": profile.get('experience_level') or None,
    }


# ============================================================
# Hierarchy endpoints — sector→profession tree, state→city tree
# ============================================================

class HierarchyRequest(BaseModel):
    """
    Cross-filter request for hierarchy panels.
    Each panel sends the *other* panel's selections so counts are cross-filtered.
    """
    domains: Optional[List[str]] = None       # selected KLDB 2-digit codes
    ql: Optional[List[int]] = None            # selected QL levels
    states: Optional[List[str]] = None        # selected Bundesländer
    cities: Optional[List[str]] = None        # selected cities (state:city format)
    professions: Optional[List[str]] = None   # selected berufenet_names
    geo_locations: Optional[List[GeoLocation]] = None


@router.post("/search/sector-tree")
def sector_tree(
    req: HierarchyRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Returns the sector→profession hierarchy with counts.

    Counts are cross-filtered by location selections (states/cities)
    but NOT by sector/domain selections — so the user sees how many
    postings each sector has given current location filters.

    Response shape:
    {
      "sectors": [
        {
          "name": "IT & Technologie",
          "codes": ["43"],
          "color": "#fc8d62",
          "count": 12345,
          "professions": [
            {"name": "Softwareentwicklung", "berufenet_id": 123, "count": 456},
            ...
          ]
        },
        ...
      ]
    }
    """
    with conn.cursor() as cur:
        # Build WHERE clauses for cross-filtering by location
        where_parts = []
        params = []

        if req.states:
            where_parts.append("ds.location_state = ANY(%s)")
            params.append(req.states)

        if req.ql:
            # QL filter: we need to look at postings directly for QL
            # For now, QL is encoded in profession-level data via berufenet.kldb
            # We'll handle QL at the display level or fall back to postings query
            pass

        where_sql = (" AND " + " AND ".join(where_parts)) if where_parts else ""

        # ── Domain-level counts (berufenet_id IS NULL rows in demand_snapshot) ──
        cur.execute(f"""
            SELECT ds.domain_code,
                   SUM(ds.total_postings) AS total,
                   SUM(ds.fresh_14d) AS fresh
            FROM demand_snapshot ds
            WHERE ds.berufenet_id IS NULL
            {where_sql}
            GROUP BY ds.domain_code
            ORDER BY total DESC
        """, params)

        domain_counts = {}
        for row in cur.fetchall():
            code = row['domain_code']
            name = KLDB_DOMAINS.get(code, f'Sonstige ({code})')
            if name not in domain_counts:
                domain_counts[name] = {"codes": [], "total": 0, "fresh": 0}
            domain_counts[name]["codes"].append(code)
            domain_counts[name]["total"] += row['total']
            domain_counts[name]["fresh"] += row['fresh']

        # ── Profession-level counts ──────────────────────────────────────
        cur.execute(f"""
            SELECT ds.domain_code,
                   ds.berufenet_id,
                   ds.berufenet_name,
                   SUM(ds.total_postings) AS total,
                   SUM(ds.fresh_14d) AS fresh
            FROM demand_snapshot ds
            WHERE ds.berufenet_id IS NOT NULL
            {where_sql}
            GROUP BY ds.domain_code, ds.berufenet_id, ds.berufenet_name
            ORDER BY total DESC
        """, params)

        prof_by_domain = {}
        for row in cur.fetchall():
            code = row['domain_code']
            name = KLDB_DOMAINS.get(code, f'Sonstige ({code})')
            if name not in prof_by_domain:
                prof_by_domain[name] = []
            prof_by_domain[name].append({
                "name": row['berufenet_name'],
                "berufenet_id": row['berufenet_id'],
                "count": row['total'],
                "fresh": row['fresh'],
                "name_en": _get_prof_trans().get(row['berufenet_name']),
            })

        # ── Assemble response ────────────────────────────────────────────
        sectors = []
        for name, data in sorted(domain_counts.items(), key=lambda x: x[1]['total'], reverse=True):
            profs = prof_by_domain.get(name, [])
            profs.sort(key=lambda p: p['count'], reverse=True)
            sectors.append({
                "name": name,
                "codes": data["codes"],
                "color": DOMAIN_COLORS.get(name, '#cccccc'),
                "count": data["total"],
                "fresh": data["fresh"],
                "professions": profs[:50],  # cap at 50 per sector
            })

        return {"sectors": sectors}


@router.post("/search/location-tree")
def location_tree(
    req: HierarchyRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Returns the Bundesland→City hierarchy with counts.

    Counts are cross-filtered by sector/domain selections
    but NOT by location selections — so the user sees how many
    postings each Bundesland has given current sector filters.

    Response shape:
    {
      "locations": [
        {
          "state": "Bayern",
          "count": 45000,
          "fresh": 1200,
          "cities": [
            {"city": "München", "count": 12000, "fresh": 340, "lat": 48.13, "lon": 11.58},
            ...
          ]
        },
        ...
      ]
    }
    """
    with conn.cursor() as cur:
        # Cross-filter by domain selections
        where_parts = []
        params = []

        if req.domains:
            where_parts.append("cs.domain_code = ANY(%s)")
            params.append(req.domains)

        # When domains are selected, use domain-specific rows; otherwise use totals
        if req.domains:
            domain_where = " AND " + " AND ".join(where_parts) if where_parts else ""
            # State-level: sum city_snapshot rows that have a matching domain_code
            cur.execute(f"""
                SELECT cs.location_state,
                       SUM(cs.total_postings) AS total,
                       SUM(cs.fresh_14d) AS fresh
                FROM city_snapshot cs
                WHERE cs.domain_code IS NOT NULL
                {domain_where}
                GROUP BY cs.location_state
                ORDER BY total DESC
            """, params)
        else:
            # No domain filter — use the total rows (domain_code IS NULL)
            cur.execute("""
                SELECT cs.location_state,
                       SUM(cs.total_postings) AS total,
                       SUM(cs.fresh_14d) AS fresh
                FROM city_snapshot cs
                WHERE cs.domain_code IS NULL
                GROUP BY cs.location_state
                ORDER BY total DESC
            """)

        state_data = []
        for row in cur.fetchall():
            state_data.append({
                "state": row['location_state'],
                "count": row['total'],
                "fresh": row['fresh'],
            })

        # ── City-level data per state ────────────────────────────────────
        # For each state, get top cities
        if req.domains:
            cur.execute(f"""
                SELECT cs.location_state,
                       cs.location_city,
                       SUM(cs.total_postings) AS total,
                       SUM(cs.fresh_14d) AS fresh,
                       AVG(cs.avg_lat) AS lat,
                       AVG(cs.avg_lon) AS lon
                FROM city_snapshot cs
                WHERE cs.domain_code IS NOT NULL
                {domain_where}
                GROUP BY cs.location_state, cs.location_city
                ORDER BY cs.location_state, total DESC
            """, params)
        else:
            cur.execute("""
                SELECT cs.location_state,
                       cs.location_city,
                       cs.total_postings AS total,
                       cs.fresh_14d AS fresh,
                       cs.avg_lat AS lat,
                       cs.avg_lon AS lon
                FROM city_snapshot cs
                WHERE cs.domain_code IS NULL
                ORDER BY cs.location_state, cs.total_postings DESC
            """)

        cities_by_state = {}
        for row in cur.fetchall():
            st = row['location_state']
            if st not in cities_by_state:
                cities_by_state[st] = []
            cities_by_state[st].append({
                "city": row['location_city'],
                "count": row['total'],
                "fresh": row['fresh'],
                "lat": round(float(row['lat']), 4) if row['lat'] else None,
                "lon": round(float(row['lon']), 4) if row['lon'] else None,
            })

        # Attach cities to states
        locations = []
        for sd in state_data:
            cities = cities_by_state.get(sd['state'], [])
            locations.append({
                **sd,
                "total_cities": len(cities),
                "cities": cities[:10],  # top 10 initially
            })

        return {"locations": locations}


@router.post("/search/location-tree/cities")
def location_tree_cities(
    state: str = Query(...),
    offset: int = Query(default=10),
    limit: int = Query(default=10),
    req: HierarchyRequest = None,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Load more cities for a Bundesland (paginated).
    Used by the "show more" button in the location tree panel.
    """
    if req is None:
        req = HierarchyRequest()

    with conn.cursor() as cur:
        if req.domains:
            cur.execute("""
                SELECT cs.location_city,
                       SUM(cs.total_postings) AS total,
                       SUM(cs.fresh_14d) AS fresh,
                       AVG(cs.avg_lat) AS lat,
                       AVG(cs.avg_lon) AS lon
                FROM city_snapshot cs
                WHERE cs.location_state = %s
                  AND cs.domain_code = ANY(%s)
                  AND cs.domain_code IS NOT NULL
                GROUP BY cs.location_city
                ORDER BY total DESC
                OFFSET %s LIMIT %s
            """, (state, req.domains, offset, limit))
        else:
            cur.execute("""
                SELECT cs.location_city AS location_city,
                       cs.total_postings AS total,
                       cs.fresh_14d AS fresh,
                       cs.avg_lat AS lat,
                       cs.avg_lon AS lon
                FROM city_snapshot cs
                WHERE cs.location_state = %s
                  AND cs.domain_code IS NULL
                ORDER BY cs.total_postings DESC
                OFFSET %s LIMIT %s
            """, (state, offset, limit))

        cities = [
            {
                "city": row['location_city'],
                "count": row['total'],
                "fresh": row['fresh'],
                "lat": round(float(row['lat']), 4) if row['lat'] else None,
                "lon": round(float(row['lon']), 4) if row['lon'] else None,
            }
            for row in cur.fetchall()
        ]

        return {"state": state, "cities": cities, "offset": offset}

