"""
Dashboard routes — main user interface.
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
import markdown

from api.deps import get_db, get_current_user

router = APIRouter(tags=["dashboard"])


def render_base(content: str, user: dict = None) -> str:
    """Wrap content in base HTML template."""
    nav = ""
    if user:
        nav = f"""
        <nav style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #ddd; margin-bottom: 20px;">
            <a href="/dashboard" style="font-size: 1.5em; text-decoration: none;">🎯 talent.yoga</a>
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
        <a href="/dashboard?filter=all" class="{'active' if filter == 'all' else ''}">All</a>
        <a href="/dashboard?filter=apply" class="{'active' if filter == 'apply' else ''}">✅ Apply</a>
        <a href="/dashboard?filter=skip" class="{'active' if filter == 'skip' else ''}">⏭️ Skip</a>
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
        
        # Get posting requirements (from posting_facets if available)
        cur.execute("""
            SELECT skill_owl_name FROM posting_facets 
            WHERE posting_id = %s AND skill_owl_name IS NOT NULL
        """, (match['posting_id'],))
        requirements = [r['skill_owl_name'] for r in cur.fetchall()]
        
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
        <a href="/dashboard" style="display: inline-block; margin-bottom: 20px;">← Back to matches</a>
        
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
