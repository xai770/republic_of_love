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

from api.deps import get_db, require_user

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
        # Build WHERE clauses
        wheres = ["p.berufenet_id IS NOT NULL"]
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
            for name, count in sorted(domain_agg.items(), key=lambda x: -x[1])
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
