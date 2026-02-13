"""
Admin console routes — operational stats, system health, OWL triage.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import json
import pytz

from api.deps import get_db, get_current_user, user_has_owl_privilege

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


ADMIN_DENIED_HTML = """
<html><head><title>Access Denied</title></head>
<body style="font-family: sans-serif; padding: 40px; background: #1a1a2e; color: #e0e0e0;">
    <h1>&#x1f512; Access Denied</h1>
    <p>Admin access required. <a href="/auth/google" style="color: #4fc3f7;">Log in</a> with an authorized account.</p>
</body></html>
"""


def _require_admin(request: Request, conn):
    """Check user is authenticated and has admin privileges via OWL.
    Falls back to is_admin column for backwards compat."""
    user = get_current_user(request, conn)
    if not user:
        return None, HTMLResponse(ADMIN_DENIED_HTML, status_code=401)
    # Check OWL privilege first, fall back to is_admin column
    if not (user.get('is_admin') or user_has_owl_privilege(conn, user['user_id'], 'admin_console')):
        return None, HTMLResponse(ADMIN_DENIED_HTML, status_code=403)
    return user, None


def _require_privilege(request: Request, conn, privilege: str):
    """Check user is authenticated and has a specific OWL privilege.
    Falls back to is_admin (admins can do everything)."""
    user = get_current_user(request, conn)
    if not user:
        return None, HTMLResponse(ADMIN_DENIED_HTML, status_code=401)
    if not (user.get('is_admin') or user_has_owl_privilege(conn, user['user_id'], privilege)):
        return None, HTMLResponse(ADMIN_DENIED_HTML, status_code=403)
    return user, None

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/console", response_class=HTMLResponse)
def admin_console(request: Request, conn=Depends(get_db)):
    """
    Admin console — last 24h ticket summary by actor, nightly fetch status.
    """
    user, err = _require_admin(request, conn)
    if err:
        return err
    
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(berlin_tz)
    last_24h = now - timedelta(hours=24)
    
    with conn.cursor() as cur:
        # Ticket summary by actor (last 24h)
        cur.execute("""
            SELECT 
                a.actor_name,
                t.status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (t.completed_at - t.started_at))) as avg_duration_sec
            FROM tickets t
            JOIN actors a ON t.actor_id = a.actor_id
            WHERE t.created_at >= %s
            GROUP BY a.actor_name, t.status
            ORDER BY a.actor_name, t.status
        """, (last_24h,))
        ticket_stats = cur.fetchall()
        
        # Aggregate by actor
        actor_summary = {}
        for row in ticket_stats:
            actor = row['actor_name']
            if actor not in actor_summary:
                actor_summary[actor] = {'completed': 0, 'failed': 0, 'pending': 0, 'running': 0, 'avg_duration': None}
            actor_summary[actor][row['status']] = row['count']
            if row['status'] == 'completed' and row['avg_duration_sec']:
                actor_summary[actor]['avg_duration'] = row['avg_duration_sec']
        
        # Recent batch info
        cur.execute("""
            SELECT 
                b.batch_id,
                a.actor_name,
                b.status,
                b.item_count,
                b.completed_count,
                b.failed_count,
                b.started_at,
                b.completed_at
            FROM batches b
            JOIN actors a ON b.task_type_id = a.actor_id
            WHERE b.started_at >= %s
            ORDER BY b.started_at DESC
            LIMIT 10
        """, (last_24h,))
        recent_batches = cur.fetchall()
        
        # Nightly fetch status (check for arbeitsagentur postings from last 24h)
        cur.execute("""
            SELECT 
                DATE(first_seen_at AT TIME ZONE 'Europe/Berlin') as fetch_date,
                COUNT(*) as count
            FROM postings
            WHERE source = 'arbeitsagentur' 
                AND first_seen_at >= %s
            GROUP BY DATE(first_seen_at AT TIME ZONE 'Europe/Berlin')
            ORDER BY fetch_date DESC
        """, (last_24h,))
        fetch_stats = cur.fetchall()
        
        # Total counts
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM postings WHERE enabled = true) as total_postings,
                (SELECT COUNT(*) FROM profiles WHERE enabled = true) as total_profiles,
                (SELECT COUNT(*) FROM actors WHERE enabled = true) as total_actors,
                (SELECT COUNT(*) FROM profile_posting_matches) as total_matches
        """)
        totals = cur.fetchone()
    
    return templates.TemplateResponse("admin/console.html", {
        "request": request,
        "now": now.strftime('%Y-%m-%d %H:%M:%S'),
        "totals": totals,
        "actor_summary": actor_summary,
        "recent_batches": recent_batches,
        "fetch_stats": fetch_stats,
    })


# =============================================================================
# OWL Browser — /admin/owl-browser
# =============================================================================


@router.get("/owl-browser", response_class=HTMLResponse)
def owl_browser(
    request: Request,
    conn=Depends(get_db),
    id: int = None,
    type: str = None,
    q: str = None,
    page: int = 1,
):
    """OWL Browser — explore the entity graph with drill-down."""
    user, err = _require_privilege(request, conn, 'admin_owl_browser')
    if err:
        return err

    page_size = 100

    with conn.cursor() as cur:
        # Global stats (always shown)
        cur.execute("""
            SELECT owl_type, COUNT(*) AS cnt
            FROM owl GROUP BY owl_type ORDER BY cnt DESC
        """)
        type_counts = [(r['owl_type'], r['cnt']) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) AS c FROM owl_names")
        total_names = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) AS c FROM owl_relationships")
        total_rels = cur.fetchone()['c']

        context = {
            "request": request,
            "type_counts": type_counts,
            "total_names": total_names,
            "total_rels": total_rels,
            "breadcrumbs": [],
            "q": q,
            "entity": None,
            "search_results": None,
        }

        # ----- SINGLE ENTITY VIEW -----
        if id is not None:
            cur.execute("""
                SELECT owl_id, owl_type, canonical_name, status, description, metadata
                FROM owl WHERE owl_id = %s
            """, (id,))
            entity = cur.fetchone()
            if not entity:
                context["entity"] = None
                return templates.TemplateResponse("admin/owl_browser.html", context)

            # Build breadcrumb by walking up parent chain
            breadcrumbs = [{"id": entity['owl_id'], "name": entity['canonical_name']}]
            visited = {entity['owl_id']}
            walk_id = entity['owl_id']
            for _ in range(10):  # max depth
                cur.execute("""
                    SELECT r.related_owl_id, o.canonical_name
                    FROM owl_relationships r
                    JOIN owl o ON o.owl_id = r.related_owl_id
                    WHERE r.owl_id = %s
                      AND r.relationship IN ('belongs_to', 'child_of')
                    ORDER BY r.strength DESC NULLS LAST
                    LIMIT 1
                """, (walk_id,))
                parent = cur.fetchone()
                if not parent or parent['related_owl_id'] in visited:
                    break
                breadcrumbs.insert(0, {
                    "id": parent['related_owl_id'],
                    "name": parent['canonical_name'],
                })
                visited.add(parent['related_owl_id'])
                walk_id = parent['related_owl_id']

            # Names
            cur.execute("""
                SELECT display_name, language, is_primary, name_type, confidence
                FROM owl_names
                WHERE owl_id = %s
                ORDER BY is_primary DESC NULLS LAST, language, display_name
            """, (id,))
            names = cur.fetchall()

            # Children (entities that belong_to / child_of this one)
            cur.execute("""
                SELECT o.owl_id, o.owl_type, o.canonical_name,
                       (SELECT COUNT(*) FROM owl_names n WHERE n.owl_id = o.owl_id) AS name_count,
                       (SELECT COUNT(*) FROM owl_relationships r2 WHERE r2.owl_id = o.owl_id OR r2.related_owl_id = o.owl_id) AS rel_count,
                       (SELECT COUNT(*) FROM owl_relationships r3 WHERE r3.related_owl_id = o.owl_id AND r3.relationship IN ('belongs_to','child_of')) AS child_count
                FROM owl_relationships r
                JOIN owl o ON o.owl_id = r.owl_id
                WHERE r.related_owl_id = %s
                  AND r.relationship IN ('belongs_to', 'child_of')
                ORDER BY o.owl_type, o.canonical_name
                LIMIT 201
            """, (id,))
            children_raw = cur.fetchall()
            children_truncated = len(children_raw) > 200
            children = children_raw[:200]

            # Outgoing relationships (excluding child_of/belongs_to already shown)
            cur.execute("""
                SELECT r.related_owl_id, r.relationship, r.strength,
                       o.canonical_name AS related_name, o.owl_type AS related_type
                FROM owl_relationships r
                JOIN owl o ON o.owl_id = r.related_owl_id
                WHERE r.owl_id = %s
                ORDER BY r.relationship, o.canonical_name
                LIMIT 100
            """, (id,))
            rels_out = cur.fetchall()

            # Incoming relationships (not child_of, belongs_to — those are "children")
            cur.execute("""
                SELECT r.owl_id AS from_owl_id, r.relationship,
                       o.canonical_name AS from_name, o.owl_type AS from_type
                FROM owl_relationships r
                JOIN owl o ON o.owl_id = r.owl_id
                WHERE r.related_owl_id = %s
                  AND r.relationship NOT IN ('belongs_to', 'child_of')
                ORDER BY r.relationship, o.canonical_name
                LIMIT 101
            """, (id,))
            rels_in_raw = cur.fetchall()
            rels_in_truncated = len(rels_in_raw) > 100
            rels_in = rels_in_raw[:100]

            # Linked postings (for berufenet entities)
            postings = []
            posting_total = 0
            if entity['owl_type'] == 'berufenet' and entity.get('metadata'):
                meta = entity['metadata'] if isinstance(entity['metadata'], dict) else json.loads(entity['metadata'])
                bid = meta.get('berufenet_id')
                if bid:
                    cur.execute(
                        "SELECT COUNT(*) AS c FROM postings WHERE berufenet_id = %s", (bid,))
                    posting_total = cur.fetchone()['c']
                    cur.execute("""
                        SELECT job_title, location_city, first_seen_at
                        FROM postings WHERE berufenet_id = %s
                        ORDER BY first_seen_at DESC LIMIT 15
                    """, (bid,))
                    postings = cur.fetchall()

            context.update({
                "entity": entity,
                "breadcrumbs": breadcrumbs,
                "names": names,
                "children": children,
                "children_truncated": children_truncated,
                "rels_out": rels_out,
                "rels_in": rels_in,
                "rels_in_truncated": rels_in_truncated,
                "postings": postings,
                "posting_total": posting_total,
            })
            return templates.TemplateResponse("admin/owl_browser.html", context)

        # ----- SEARCH -----
        if q and q.strip():
            query = q.strip()
            cur.execute("""
                SELECT DISTINCT o.owl_id, o.owl_type, o.canonical_name,
                       n.display_name AS matched_name,
                       (SELECT COUNT(*) FROM owl_names n2 WHERE n2.owl_id = o.owl_id) AS name_count
                FROM owl o
                LEFT JOIN owl_names n ON n.owl_id = o.owl_id
                WHERE o.canonical_name ILIKE %s
                   OR n.display_name ILIKE %s
                ORDER BY
                    CASE WHEN o.canonical_name ILIKE %s THEN 0 ELSE 1 END,
                    o.owl_type, o.canonical_name
                LIMIT 101
            """, (f'%{query}%', f'%{query}%', f'{query}%'))
            results_raw = cur.fetchall()
            search_truncated = len(results_raw) > 100
            search_results = results_raw[:100]

            context.update({
                "search_results": search_results,
                "search_truncated": search_truncated,
            })
            return templates.TemplateResponse("admin/owl_browser.html", context)

        # ----- TYPE LISTING -----
        if type:
            offset = (page - 1) * page_size
            cur.execute("""
                SELECT o.owl_id, o.owl_type, o.canonical_name,
                       (SELECT COUNT(*) FROM owl_names n WHERE n.owl_id = o.owl_id) AS name_count,
                       (SELECT COUNT(*) FROM owl_relationships r WHERE r.owl_id = o.owl_id OR r.related_owl_id = o.owl_id) AS rel_count,
                       0 AS child_count
                FROM owl o
                WHERE o.owl_type = %s
                ORDER BY o.canonical_name
                LIMIT %s OFFSET %s
            """, (type, page_size + 1, offset))
            results_raw = cur.fetchall()
            search_truncated = len(results_raw) > page_size
            search_results = results_raw[:page_size]

            context.update({
                "search_results": search_results,
                "search_truncated": search_truncated,
                "breadcrumbs": [{"id": None, "name": type}],
            })
            return templates.TemplateResponse("admin/owl_browser.html", context)

        # ----- ROOT VIEW -----
        # Taxonomy roots with child counts
        cur.execute("""
            SELECT o.owl_id, o.canonical_name,
                   (SELECT COUNT(*) FROM owl_relationships r
                    WHERE r.related_owl_id = o.owl_id
                      AND r.relationship IN ('belongs_to','child_of')) AS child_count
            FROM owl o
            WHERE o.owl_type = 'taxonomy_root'
            ORDER BY o.canonical_name
        """)
        roots = cur.fetchall()

        # Domain gates with posting counts
        cur.execute("""
            SELECT o.owl_id, o.canonical_name, o.metadata
            FROM owl o
            WHERE o.owl_type = 'domain_gate'
            ORDER BY o.canonical_name
        """)
        gates_raw = cur.fetchall()
        gates = []
        for g in gates_raw:
            meta = g['metadata'] if isinstance(g['metadata'], dict) else (json.loads(g['metadata']) if g['metadata'] else {})
            gates.append({
                "owl_id": g['owl_id'],
                "canonical_name": g['canonical_name'],
                "color": meta.get('color', '#0066cc'),
                "posting_count": 0,  # Could query postings but expensive — skip for now
            })

        context.update({
            "roots": roots,
            "gates": gates,
        })
        return templates.TemplateResponse("admin/owl_browser.html", context)


@router.get("/owl-browser/children")
def owl_browser_children(
    request: Request,
    conn=Depends(get_db),
    parent_id: int = None,
):
    """JSON API: return children of a given OWL entity for lazy tree loading."""
    user, err = _require_privilege(request, conn, 'admin_owl_browser')
    if err:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    with conn.cursor() as cur:
        if parent_id is None:
            # Return taxonomy roots as top-level nodes
            cur.execute("""
                SELECT o.owl_id, o.owl_type, o.canonical_name,
                       (SELECT COUNT(*) FROM owl_relationships r
                        WHERE r.related_owl_id = o.owl_id
                          AND r.relationship IN ('belongs_to','child_of')) AS child_count
                FROM owl o
                WHERE o.owl_type = 'taxonomy_root'
                ORDER BY o.canonical_name
            """)
        else:
            # Return entities that belong_to / child_of this parent
            cur.execute("""
                SELECT o.owl_id, o.owl_type, o.canonical_name,
                       (SELECT COUNT(*) FROM owl_relationships r2
                        WHERE r2.related_owl_id = o.owl_id
                          AND r2.relationship IN ('belongs_to','child_of')) AS child_count
                FROM owl_relationships r
                JOIN owl o ON o.owl_id = r.owl_id
                WHERE r.related_owl_id = %s
                  AND r.relationship IN ('belongs_to', 'child_of')
                ORDER BY o.owl_type, o.canonical_name
                LIMIT 5000
            """, (parent_id,))

        rows = cur.fetchall()

    return [
        {
            "id": r['owl_id'],
            "type": r['owl_type'],
            "name": r['canonical_name'],
            "children": r['child_count'],
        }
        for r in rows
    ]


# =============================================================================
# OWL Triage — /admin/owl-triage
# =============================================================================



@router.get("/owl-triage", response_class=HTMLResponse)
def owl_triage(request: Request, conn=Depends(get_db), page: int = 1,
               flash: str = None, flash_type: str = "success"):
    """OWL Triage — resolve pending berufenet classifications."""
    user, err = _require_admin(request, conn)
    if err:
        return err

    page_size = 20
    offset = (page - 1) * page_size

    with conn.cursor() as cur:
        # Stats
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                COUNT(*) FILTER (WHERE status = 'resolved') AS resolved,
                COUNT(*) FILTER (WHERE status = 'skipped') AS skipped,
                COUNT(*) FILTER (WHERE status = 'rejected') AS rejected
            FROM owl_pending
            WHERE owl_type = 'berufenet'
        """)
        stats = cur.fetchone()

        # Count affected postings
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM postings
            WHERE berufenet_verified = 'pending_owl'
              AND berufenet_id IS NULL
        """)
        affected_postings = cur.fetchone()['cnt']

        # Get current page of pending items
        cur.execute("""
            SELECT pending_id, raw_value, source_context, created_at
            FROM owl_pending
            WHERE owl_type = 'berufenet'
              AND status = 'pending'
            ORDER BY created_at
            LIMIT %s OFFSET %s
        """, (page_size, offset))
        items = cur.fetchall()

    total_pending = stats['pending']
    total_pages = max(1, (total_pending + page_size - 1) // page_size)

    # Parse candidates from source_context for each item
    prepared_items = []
    for item in items:
        candidates = []
        if item['source_context']:
            ctx = item['source_context'] if isinstance(item['source_context'], dict) else json.loads(item['source_context'])
            candidates = ctx.get('candidates', [])
        prepared_items.append({
            'pending_id': item['pending_id'],
            'raw_value': item['raw_value'],
            'candidates': candidates,
        })

    return templates.TemplateResponse("admin/owl_triage.html", {
        "request": request,
        "stats": stats,
        "affected_postings": affected_postings,
        "items": prepared_items,
        "page": page,
        "total_pages": total_pages,
        "flash": flash,
        "flash_type": flash_type,
    })


@router.post("/owl-triage/resolve")
def owl_triage_resolve(
    request: Request,
    pending_id: int = Form(...),
    berufenet_ids: str = Form(...),
    page: int = Form(1),
    conn=Depends(get_db),
):
    """Resolve a pending OWL triage item — map to one or more berufenet entities.
    First ID becomes the primary berufenet_id on postings.
    All selected IDs get OWL synonyms so the title is recognized in future."""
    user, err = _require_admin(request, conn)
    if err:
        return err
    id_list = [int(x.strip()) for x in berufenet_ids.split(',') if x.strip().isdigit()]
    if not id_list:
        return RedirectResponse(
            f"/admin/owl-triage?page={page}&flash=No+candidates+selected&flash_type=error",
            status_code=303)

    with conn.cursor() as cur:
        # 1. Look up ALL selected berufenet entities
        cur.execute("""
            SELECT b.berufenet_id, b.name AS berufenet_name, b.kldb, b.qualification_level,
                   o.owl_id
            FROM berufenet b
            LEFT JOIN owl o ON o.owl_type = 'berufenet'
                           AND o.metadata->>'berufenet_id' = b.berufenet_id::text
            WHERE b.berufenet_id = ANY(%s)
            ORDER BY array_position(%s, b.berufenet_id)
        """, (id_list, id_list))
        berufe = cur.fetchall()
        if not berufe:
            return RedirectResponse(
                f"/admin/owl-triage?page={page}&flash=Berufenet+IDs+not+found&flash_type=error",
                status_code=303)

        # First selected = primary for posting classification
        primary = berufe[0]

        # 2. Get the pending item's raw_value
        cur.execute("SELECT raw_value FROM owl_pending WHERE pending_id = %s", (pending_id,))
        pending = cur.fetchone()
        if not pending:
            return RedirectResponse(
                f"/admin/owl-triage?page={page}&flash=Pending+item+not+found&flash_type=error",
                status_code=303)

        raw_value = pending['raw_value']

        # 3. Add OWL synonym for ALL selected entities (title recognized for all)
        for beruf in berufe:
            if beruf['owl_id']:
                cur.execute("""
                    INSERT INTO owl_names (owl_id, language, display_name, is_primary, name_type,
                                           created_by, confidence, confidence_source, observation_count,
                                           provenance)
                    VALUES (%s, 'de', %s, false, 'alias', 'human_triage', 1.0, 'human', 1,
                            '{"source": "owl_triage_ui"}'::jsonb)
                    ON CONFLICT (owl_id, language, display_name) DO UPDATE
                    SET confidence_source = 'human',
                        confidence = 1.0,
                        created_by = 'human_triage'
                """, (beruf['owl_id'], raw_value))

        # 4. Update all matching postings (primary entity)
        cur.execute("""
            UPDATE postings
            SET berufenet_id = %s,
                berufenet_name = %s,
                berufenet_kldb = %s,
                qualification_level = %s,
                berufenet_score = 1.0,
                berufenet_verified = 'human'
            WHERE berufenet_verified = 'pending_owl'
              AND berufenet_id IS NULL
              AND LOWER(job_title) = LOWER(%s)
        """, (primary['berufenet_id'], primary['berufenet_name'],
              primary['kldb'], primary['qualification_level'], raw_value))
        postings_updated = cur.rowcount

        # 5. Mark owl_pending as resolved
        names = [b['berufenet_name'] for b in berufe]
        notes = f"Mapped to {', '.join(names)} (primary: #{primary['berufenet_id']})"
        cur.execute("""
            UPDATE owl_pending
            SET status = 'resolved',
                resolved_owl_id = %s,
                resolution_notes = %s,
                processed_at = NOW(),
                processed_by = 'human_triage'
            WHERE pending_id = %s
        """, (primary['owl_id'], notes, pending_id))

        conn.commit()

    n = len(berufe)
    label = primary['berufenet_name'] if n == 1 else f"{n}+entities"
    flash = f"Resolved:+{raw_value}+->+{label}+({postings_updated}+postings)"
    return RedirectResponse(
        f"/admin/owl-triage?page={page}&flash={flash}&flash_type=success",
        status_code=303)


@router.post("/owl-triage/skip")
def owl_triage_skip(
    request: Request,
    pending_id: int = Form(...),
    action: str = Form("skip"),
    page: int = Form(1),
    conn=Depends(get_db),
):
    """Skip or reject a pending OWL triage item."""
    user, err = _require_admin(request, conn)
    if err:
        return err
    new_status = 'rejected' if action == 'reject' else 'skipped'

    with conn.cursor() as cur:
        cur.execute("SELECT raw_value FROM owl_pending WHERE pending_id = %s", (pending_id,))
        pending = cur.fetchone()

        if pending and new_status == 'rejected':
            # Mark matching postings as unclassifiable
            cur.execute("""
                UPDATE postings
                SET berufenet_verified = 'no_match'
                WHERE berufenet_verified = 'pending_owl'
                  AND berufenet_id IS NULL
                  AND LOWER(job_title) = LOWER(%s)
            """, (pending['raw_value'],))

        cur.execute("""
            UPDATE owl_pending
            SET status = %s,
                processed_at = NOW(),
                processed_by = 'human_triage'
            WHERE pending_id = %s
        """, (new_status, pending_id))
        conn.commit()

    label = "Rejected" if new_status == 'rejected' else "Skipped"
    raw = pending['raw_value'] if pending else '?'
    return RedirectResponse(
        f"/admin/owl-triage?page={page}&flash={label}:+{raw.replace(' ', '+')}&flash_type=success",
        status_code=303)


@router.post("/owl-triage/auto")
def owl_triage_auto(
    request: Request,
    page: int = Form(1),
    batch_size: int = Form(50),
    conn=Depends(get_db),
):
    """LLM auto-triage — ask qwen2.5:7b to pick matches for pending items."""
    user, err = _require_admin(request, conn)
    if err:
        return err
    from lib.berufenet_matching import llm_triage_pick

    with conn.cursor() as cur:
        # Get a batch of pending items
        cur.execute("""
            SELECT pending_id, raw_value, source_context
            FROM owl_pending
            WHERE owl_type = 'berufenet'
              AND status = 'pending'
              AND raw_value IS NOT NULL
              AND raw_value != ''
            ORDER BY created_at
            LIMIT %s
        """, (batch_size,))
        items = cur.fetchall()

    if not items:
        return RedirectResponse(
            f"/admin/owl-triage?page={page}&flash=No+pending+items&flash_type=error",
            status_code=303)

    resolved = 0
    rejected = 0
    skipped = 0

    for item in items:
        candidates = []
        if item['source_context']:
            ctx = item['source_context'] if isinstance(item['source_context'], dict) else json.loads(item['source_context'])
            candidates = ctx.get('candidates', [])

        if not candidates:
            skipped += 1
            continue

        # Ask LLM
        picked_indices = llm_triage_pick(item['raw_value'], candidates)

        if not picked_indices:
            # LLM says NONE — reject
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE postings
                    SET berufenet_verified = 'no_match'
                    WHERE berufenet_verified = 'pending_owl'
                      AND berufenet_id IS NULL
                      AND LOWER(job_title) = LOWER(%s)
                """, (item['raw_value'],))
                cur.execute("""
                    UPDATE owl_pending
                    SET status = 'rejected',
                        resolution_notes = 'LLM: no match',
                        processed_at = NOW(),
                        processed_by = 'llm_triage'
                    WHERE pending_id = %s
                """, (item['pending_id'],))
                conn.commit()
            rejected += 1
            continue

        # LLM picked candidates — resolve
        picked_ids = [candidates[i].get('berufenet_id') for i in picked_indices if candidates[i].get('berufenet_id')]
        if not picked_ids:
            skipped += 1
            continue

        with conn.cursor() as cur:
            # Look up berufenet entities
            cur.execute("""
                SELECT b.berufenet_id, b.name AS berufenet_name, b.kldb, b.qualification_level,
                       o.owl_id
                FROM berufenet b
                LEFT JOIN owl o ON o.owl_type = 'berufenet'
                               AND o.metadata->>'berufenet_id' = b.berufenet_id::text
                WHERE b.berufenet_id = ANY(%s)
                ORDER BY array_position(%s, b.berufenet_id)
            """, (picked_ids, picked_ids))
            berufe = cur.fetchall()
            if not berufe:
                skipped += 1
                continue

            primary = berufe[0]

            # Add OWL synonyms for all picked
            for beruf in berufe:
                if beruf['owl_id']:
                    cur.execute("""
                        INSERT INTO owl_names (owl_id, language, display_name, is_primary, name_type,
                                               created_by, confidence, confidence_source, observation_count,
                                               provenance)
                        VALUES (%s, 'de', %s, false, 'alias', 'llm_triage', 0.9, 'llm_confirmed', 1,
                                '{"source": "owl_triage_llm_auto"}'::jsonb)
                        ON CONFLICT (owl_id, language, display_name) DO UPDATE
                        SET observation_count = owl_names.observation_count + 1,
                            confidence_source = CASE
                                WHEN owl_names.observation_count + 1 >= 2 THEN 'llm_confirmed'
                                ELSE owl_names.confidence_source
                            END
                    """, (beruf['owl_id'], item['raw_value']))

            # Update postings (primary entity)
            cur.execute("""
                UPDATE postings
                SET berufenet_id = %s,
                    berufenet_name = %s,
                    berufenet_kldb = %s,
                    qualification_level = %s,
                    berufenet_score = 1.0,
                    berufenet_verified = 'llm_triage'
                WHERE berufenet_verified = 'pending_owl'
                  AND berufenet_id IS NULL
                  AND LOWER(job_title) = LOWER(%s)
            """, (primary['berufenet_id'], primary['berufenet_name'],
                  primary['kldb'], primary['qualification_level'], item['raw_value']))

            # Mark resolved
            names = [b['berufenet_name'] for b in berufe]
            cur.execute("""
                UPDATE owl_pending
                SET status = 'resolved',
                    resolved_owl_id = %s,
                    resolution_notes = %s,
                    processed_at = NOW(),
                    processed_by = 'llm_triage'
                WHERE pending_id = %s
            """, (primary['owl_id'],
                  f"LLM picked: {', '.join(names)}",
                  item['pending_id']))

            conn.commit()
            resolved += 1

    flash = f"LLM+auto-triage:+{resolved}+resolved,+{rejected}+rejected,+{skipped}+skipped+({resolved+rejected+skipped}/{len(items)})"
    return RedirectResponse(
        f"/admin/owl-triage?page={page}&flash={flash}&flash_type=success",
        status_code=303)
