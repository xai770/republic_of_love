"""
Admin console routes — operational stats, system health, OWL triage.
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import json
import pytz

from api.deps import get_db, get_current_user


ADMIN_DENIED_HTML = """
<html><head><title>Access Denied</title></head>
<body style="font-family: sans-serif; padding: 40px; background: #1a1a2e; color: #e0e0e0;">
    <h1>&#x1f512; Access Denied</h1>
    <p>Admin access required. <a href="/auth/google" style="color: #4fc3f7;">Log in</a> with an authorized account.</p>
</body></html>
"""


def _require_admin(request: Request, conn):
    """Check user is authenticated and is_admin. Returns (user, error_response)."""
    user = get_current_user(request, conn)
    if not user:
        return None, HTMLResponse(ADMIN_DENIED_HTML, status_code=401)
    if not user.get('is_admin'):
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
    
    # Build HTML
    html = f"""
    <!DOCTYPE html>
    <html data-theme="light">
    <head>
        <title>Admin Console - talent.yoga</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {{
                --bg-primary: #f5f5f5;
                --bg-card: #ffffff;
                --text-primary: #333333;
                --text-secondary: #666666;
                --border-color: #e0e0e0;
                --accent: #0066cc;
                --success: #28a745;
                --warning: #ffc107;
                --danger: #dc3545;
            }}
            [data-theme="dark"] {{
                --bg-primary: #1a1a2e;
                --bg-card: #16213e;
                --text-primary: #eee;
                --text-secondary: #aaa;
                --border-color: #333;
                --accent: #4dabf7;
            }}
            * {{ box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px;
                background: var(--bg-primary);
                color: var(--text-primary);
            }}
            h1 {{ color: var(--text-primary); }}
            h2 {{ 
                color: var(--text-primary); 
                border-bottom: 2px solid var(--accent);
                padding-bottom: 8px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
            }}
            .header-right {{
                display: flex;
                gap: 15px;
                align-items: center;
            }}
            .card {{
                background: var(--bg-card);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }}
            .stat-box {{
                background: var(--bg-card);
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .stat-number {{
                font-size: 2em;
                font-weight: bold;
                color: var(--accent);
            }}
            .stat-label {{
                color: var(--text-secondary);
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid var(--border-color);
            }}
            th {{
                background: var(--bg-primary);
                font-weight: 600;
            }}
            .status-completed {{ color: var(--success); font-weight: 600; }}
            .status-failed {{ color: var(--danger); font-weight: 600; }}
            .status-pending {{ color: var(--warning); font-weight: 600; }}
            .status-running {{ color: var(--accent); font-weight: 600; }}
            .timestamp {{
                color: var(--text-secondary);
                font-size: 0.85em;
            }}
            a {{ color: var(--accent); }}
            .refresh-btn {{
                background: var(--accent);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                cursor: pointer;
            }}
            .theme-toggle {{
                background: none;
                border: 1px solid var(--border-color);
                padding: 6px 10px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1.1em;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎛️ Admin Console</h1>
            <div class="header-right">
                <span class="timestamp">Last updated: {now.strftime('%Y-%m-%d %H:%M:%S')} CET</span>
                <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode">🌓</button>
                <button class="refresh-btn" onclick="location.reload()">↻ Refresh</button>
                <a href="/dashboard">← Dashboard</a>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{totals['total_postings']:,}</div>
                <div class="stat-label">Total Postings</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{totals['total_profiles']}</div>
                <div class="stat-label">Active Profiles</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{totals['total_actors']}</div>
                <div class="stat-label">Active Actors</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{totals['total_matches']:,}</div>
                <div class="stat-label">Total Matches</div>
            </div>
        </div>
        
        <div class="card">
            <h2>🎫 Ticket Activity (Last 24h)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Actor</th>
                        <th>Completed</th>
                        <th>Failed</th>
                        <th>Pending</th>
                        <th>Running</th>
                        <th>Avg Duration</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    if not actor_summary:
        html += '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No ticket activity in last 24 hours</td></tr>'
    else:
        for actor, stats in sorted(actor_summary.items()):
            avg_dur = f"{stats['avg_duration']:.1f}s" if stats['avg_duration'] else "—"
            html += f"""
                    <tr>
                        <td><strong>{actor}</strong></td>
                        <td class="status-completed">{stats['completed']}</td>
                        <td class="status-failed">{stats['failed']}</td>
                        <td class="status-pending">{stats['pending']}</td>
                        <td class="status-running">{stats['running']}</td>
                        <td>{avg_dur}</td>
                    </tr>
            """
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📦 Recent Batches</h2>
            <table>
                <thead>
                    <tr>
                        <th>Batch ID</th>
                        <th>Actor</th>
                        <th>Status</th>
                        <th>Progress</th>
                        <th>Started</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    if not recent_batches:
        html += '<tr><td colspan="5" style="text-align: center; color: var(--text-secondary);">No batches in last 24 hours</td></tr>'
    else:
        for batch in recent_batches:
            progress = f"{batch['completed_count']}/{batch['item_count']}"
            if batch['failed_count'] > 0:
                progress += f" <span class='status-failed'>({batch['failed_count']} failed)</span>"
            started = batch['started_at'].strftime('%H:%M:%S') if batch['started_at'] else "—"
            status_class = f"status-{batch['status']}"
            html += f"""
                    <tr>
                        <td>{batch['batch_id']}</td>
                        <td>{batch['actor_name']}</td>
                        <td class="{status_class}">{batch['status']}</td>
                        <td>{progress}</td>
                        <td class="timestamp">{started}</td>
                    </tr>
            """
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📡 Nightly Fetch Status</h2>
    """
    
    if fetch_stats:
        html += "<table><thead><tr><th>Date</th><th>Postings Fetched</th></tr></thead><tbody>"
        for stat in fetch_stats:
            html += f"<tr><td>{stat['fetch_date']}</td><td class='status-completed'>{stat['count']}</td></tr>"
        html += "</tbody></table>"
    else:
        html += '<p style="color: var(--text-secondary);">No arbeitsagentur postings fetched in last 24 hours. Check if nightly_fetch.sh ran.</p>'
    
    html += """
        </div>
        
        <script>
            function toggleTheme() {
                const html = document.documentElement;
                const current = html.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-theme', next);
                localStorage.setItem('theme', next);
            }
            
            // Restore theme on load
            (function() {
                const saved = localStorage.getItem('theme');
                if (saved) {
                    document.documentElement.setAttribute('data-theme', saved);
                } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    document.documentElement.setAttribute('data-theme', 'dark');
                }
            })();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html)


# =============================================================================
# OWL Triage — /admin/owl-triage
# =============================================================================

OWL_TRIAGE_CSS = """
    :root {
        --bg-primary: #f5f5f5; --bg-card: #ffffff; --text-primary: #333;
        --text-secondary: #666; --border-color: #e0e0e0; --accent: #0066cc;
        --success: #28a745; --warning: #ffc107; --danger: #dc3545;
    }
    [data-theme="dark"] {
        --bg-primary: #1a1a2e; --bg-card: #16213e; --text-primary: #eee;
        --text-secondary: #aaa; --border-color: #333; --accent: #4dabf7;
        --success: #2ecc71; --warning: #f1c40f; --danger: #e74c3c;
    }
    * { box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 960px; margin: 0 auto; padding: 20px;
        background: var(--bg-primary); color: var(--text-primary);
    }
    a { color: var(--accent); }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .header-right { display: flex; gap: 12px; align-items: center; }
    .stats-bar {
        display: flex; gap: 20px; margin-bottom: 24px; padding: 12px 20px;
        background: var(--bg-card); border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stats-bar .stat { text-align: center; }
    .stats-bar .stat-num { font-size: 1.4em; font-weight: bold; color: var(--accent); }
    .stats-bar .stat-lbl { font-size: 0.8em; color: var(--text-secondary); }
    .item {
        background: var(--bg-card); border-radius: 8px; padding: 20px; margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid var(--accent);
    }
    .item-title {
        font-size: 1.3em; font-weight: 700; margin-bottom: 12px;
        color: var(--text-primary);
    }
    .item-meta { font-size: 0.85em; color: var(--text-secondary); margin-bottom: 10px; }
    .candidates { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
    .candidate {
        display: flex; align-items: center; gap: 12px; padding: 10px 14px;
        border: 2px solid var(--border-color); border-radius: 6px;
        cursor: pointer; transition: all 0.15s;
    }
    .candidate:hover { border-color: var(--accent); background: rgba(0,102,204,0.05); }
    .candidate.selected { border-color: var(--success); background: rgba(40,167,69,0.08); }
    .score {
        font-family: monospace; font-size: 0.95em; font-weight: 600;
        padding: 3px 8px; border-radius: 4px; min-width: 52px; text-align: center;
    }
    .score-high { background: #d4edda; color: #155724; }
    .score-mid { background: #fff3cd; color: #856404; }
    .score-low { background: #f8d7da; color: #721c24; }
    [data-theme="dark"] .score-high { background: #1a3a2a; color: #7dcea0; }
    [data-theme="dark"] .score-mid { background: #3a3020; color: #f1c40f; }
    [data-theme="dark"] .score-low { background: #3a1a1a; color: #e74c3c; }
    .cand-name { flex: 1; font-weight: 500; }
    .cand-id { font-family: monospace; font-size: 0.85em; color: var(--text-secondary); }
    .actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .btn {
        border: none; padding: 8px 18px; border-radius: 5px; cursor: pointer;
        font-size: 0.95em; font-weight: 500; transition: opacity 0.15s;
    }
    .btn:hover { opacity: 0.85; }
    .btn-confirm { background: var(--success); color: white; }
    .btn-skip { background: var(--warning); color: #333; }
    .btn-reject { background: var(--danger); color: white; }
    .btn-nav { background: var(--accent); color: white; text-decoration: none; padding: 8px 18px; border-radius: 5px; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .flash {
        padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;
        font-weight: 500; text-align: center;
    }
    .flash-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .flash-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    [data-theme="dark"] .flash-success { background: #1a3a2a; color: #7dcea0; border-color: #2a5a3a; }
    [data-theme="dark"] .flash-error { background: #3a1a1a; color: #e74c3c; border-color: #5a2a2a; }
    .empty-state {
        text-align: center; padding: 60px 20px; color: var(--text-secondary);
        font-size: 1.1em;
    }
    .postings-count { font-size: 0.85em; color: var(--text-secondary); margin-left: 8px; }
    .theme-toggle {
        background: none; border: 1px solid var(--border-color);
        padding: 6px 10px; border-radius: 5px; cursor: pointer; font-size: 1.1em;
    }
    .keyboard-hint {
        font-size: 0.8em; color: var(--text-secondary); margin-top: 12px;
        text-align: center;
    }
    kbd {
        background: var(--bg-primary); border: 1px solid var(--border-color);
        padding: 2px 6px; border-radius: 3px; font-family: monospace; font-size: 0.9em;
    }
"""


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

    # Build items HTML
    items_html = ""
    if not items:
        items_html = '<div class="empty-state">All caught up! No pending items.</div>'
    else:
        for idx, item in enumerate(items):
            candidates = []
            if item['source_context']:
                ctx = item['source_context'] if isinstance(item['source_context'], dict) else json.loads(item['source_context'])
                candidates = ctx.get('candidates', [])

            cands_html = ""
            for ci, c in enumerate(candidates):
                score = c.get('score', 0)
                score_class = 'score-high' if score >= 0.70 else 'score-mid' if score >= 0.55 else 'score-low'
                cands_html += f"""
                    <div class="candidate" data-pid="{item['pending_id']}" data-bid="{c.get('berufenet_id', 0)}"
                         onclick="toggleCandidate(this, {item['pending_id']})">
                        <span class="score {score_class}">{score:.3f}</span>
                        <span class="cand-name">{c.get('name', '?')}</span>
                        <span class="cand-id">#{c.get('berufenet_id', '?')}</span>
                    </div>
                """

            raw_display = item['raw_value'] or '<em>(empty title)</em>'
            items_html += f"""
                <div class="item" id="item-{item['pending_id']}">
                    <div class="item-title">{raw_display}</div>
                    <div class="candidates">{cands_html}</div>
                    <div class="actions">
                        <form method="POST" action="/admin/owl-triage/resolve" style="display:inline">
                            <input type="hidden" name="pending_id" value="{item['pending_id']}">
                            <input type="hidden" name="berufenet_ids" id="bids-{item['pending_id']}" value="">
                            <input type="hidden" name="page" value="{page}">
                            <button type="submit" class="btn btn-confirm" id="confirm-{item['pending_id']}" disabled>Confirm</button>
                        </form>
                        <form method="POST" action="/admin/owl-triage/skip" style="display:inline">
                            <input type="hidden" name="pending_id" value="{item['pending_id']}">
                            <input type="hidden" name="action" value="skip">
                            <input type="hidden" name="page" value="{page}">
                            <button type="submit" class="btn btn-skip">Skip</button>
                        </form>
                        <form method="POST" action="/admin/owl-triage/skip" style="display:inline">
                            <input type="hidden" name="pending_id" value="{item['pending_id']}">
                            <input type="hidden" name="action" value="reject">
                            <input type="hidden" name="page" value="{page}">
                            <button type="submit" class="btn btn-reject">No Match</button>
                        </form>
                    </div>
                </div>
            """

    # Flash message
    flash_html = ""
    if flash:
        flash_html = f'<div class="flash flash-{flash_type}">{flash}</div>'

    # Pagination
    pagination_html = '<div style="display:flex; justify-content:center; gap:8px; margin-top:20px;">'
    if page > 1:
        pagination_html += f'<a href="/admin/owl-triage?page={page-1}" class="btn btn-nav">&larr; Prev</a>'
    pagination_html += f'<span style="padding:8px 12px; color:var(--text-secondary);">Page {page} / {total_pages}</span>'
    if page < total_pages:
        pagination_html += f'<a href="/admin/owl-triage?page={page+1}" class="btn btn-nav">Next &rarr;</a>'
    pagination_html += '</div>'

    html = f"""
    <!DOCTYPE html>
    <html data-theme="light">
    <head>
        <title>OWL Triage - talent.yoga</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>{OWL_TRIAGE_CSS}</style>
    </head>
    <body>
        <div class="header">
            <h1>OWL Triage</h1>
            <div class="header-right">
                <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode">&#x1F313;</button>
                <a href="/admin/console">&larr; Admin</a>
            </div>
        </div>

        <div class="stats-bar">
            <div class="stat">
                <div class="stat-num">{stats['pending']:,}</div>
                <div class="stat-lbl">Pending</div>
            </div>
            <div class="stat">
                <div class="stat-num">{affected_postings:,}</div>
                <div class="stat-lbl">Postings Affected</div>
            </div>
            <div class="stat">
                <div class="stat-num">{stats['resolved']:,}</div>
                <div class="stat-lbl">Resolved</div>
            </div>
            <div class="stat">
                <div class="stat-num">{stats['skipped']:,}</div>
                <div class="stat-lbl">Skipped</div>
            </div>
            <div class="stat">
                <div class="stat-num">{stats['rejected']:,}</div>
                <div class="stat-lbl">Rejected</div>
            </div>
        </div>

        <div style="display:flex; gap:10px; margin-bottom:20px; align-items:center;">
            <form method="POST" action="/admin/owl-triage/auto" style="display:inline">
                <input type="hidden" name="page" value="{page}">
                <input type="hidden" name="batch_size" value="50">
                <button type="submit" class="btn btn-nav" onclick="this.disabled=true; this.textContent='LLM working...';">
                    &#x1F916; Auto-triage next 50
                </button>
            </form>
            <span style="color:var(--text-secondary); font-size:0.85em;">
                LLM picks matches from candidates &mdash; resolved items get OWL synonyms
            </span>
        </div>

        {flash_html}
        {items_html}
        {pagination_html}

        <div class="keyboard-hint">
            Click one or more candidates then <kbd>Enter</kbd> to confirm &mdash;
            <kbd>S</kbd> to skip &mdash; <kbd>R</kbd> to reject &mdash;
            first selected = primary classification
        </div>

        <script>
            let activePendingId = null;

            function toggleCandidate(el, pendingId) {{
                el.classList.toggle('selected');
                // Collect all selected IDs for this item
                const item = document.getElementById('item-' + pendingId);
                const selected = item.querySelectorAll('.candidate.selected');
                const ids = Array.from(selected).map(c => c.dataset.bid);
                document.getElementById('bids-' + pendingId).value = ids.join(',');
                document.getElementById('confirm-' + pendingId).disabled = ids.length === 0;
                activePendingId = pendingId;
            }}

            document.addEventListener('keydown', function(e) {{
                if (!activePendingId) return;
                const item = document.getElementById('item-' + activePendingId);
                if (!item) return;
                if (e.key === 'Enter') {{
                    e.preventDefault();
                    const btn = document.getElementById('confirm-' + activePendingId);
                    if (!btn.disabled) btn.closest('form').submit();
                }} else if (e.key === 's' || e.key === 'S') {{
                    e.preventDefault();
                    item.querySelector('button.btn-skip').closest('form').submit();
                }} else if (e.key === 'r' || e.key === 'R') {{
                    e.preventDefault();
                    item.querySelector('button.btn-reject').closest('form').submit();
                }}
            }});

            function toggleTheme() {{
                const html = document.documentElement;
                const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-theme', next);
                localStorage.setItem('theme', next);
            }}
            (function() {{
                const saved = localStorage.getItem('theme');
                if (saved) document.documentElement.setAttribute('data-theme', saved);
                else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
                    document.documentElement.setAttribute('data-theme', 'dark');
            }})();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


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
