"""
Admin console routes — operational stats and system health.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import pytz

from api.deps import get_db, get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/console", response_class=HTMLResponse)
def admin_console(request: Request, conn=Depends(get_db)):
    """
    Admin console — last 24h ticket summary by actor, nightly fetch status.
    """
    user = get_current_user(request, conn)
    
    # For now, allow anyone logged in (TODO: add admin role check)
    if not user:
        return HTMLResponse("""
            <html><head><title>Admin Console</title></head>
            <body style="font-family: sans-serif; padding: 40px;">
                <h1>🔐 Access Denied</h1>
                <p>Please <a href="/auth/google">log in</a> to access the admin console.</p>
            </body></html>
        """, status_code=401)
    
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
