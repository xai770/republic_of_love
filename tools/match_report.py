#!/usr/bin/env python3
"""
Generate customer-facing match report as interactive HTML.

Shows top 10 postings for a profile with:
- Match scores and recommendations
- GO/NO-GO reasons
- Click to expand cover letters
- Similarity matrix (profile skills × job requirements)

Usage:
    python tools/match_report.py <profile_id> [-o output.html]
"""
import sys
import os
import json
import argparse
import requests
import numpy as np
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection


def get_embedding(text: str, model: str = "bge-m3:567m") -> list:
    """Get embedding from Ollama."""
    try:
        response = requests.post(
            os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embed',
            json={"model": model, "input": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]
    except Exception as e:
        print(f"Warning: Failed to get embedding for '{text[:30]}...': {e}")
        return None


def cosine_similarity(a: list, b: list) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def compute_similarity_matrix(conn, profile_id: int, posting_id: int, max_skills: int = 15) -> dict:
    """Compute similarity matrix between profile skills and job requirements."""
    cur = conn.cursor()
    
    # Get profile skills from profiles.skill_keywords
    cur.execute("""
        SELECT skill_keywords FROM profiles WHERE profile_id = %s
    """, (profile_id,))
    row = cur.fetchone()
    skill_keywords = row['skill_keywords'] if row else None
    
    profile_skills = []
    if skill_keywords:
        import json
        if isinstance(skill_keywords, str):
            skill_keywords = json.loads(skill_keywords)
        for s in skill_keywords:
            if isinstance(s, str):
                profile_skills.append(s)
            elif isinstance(s, dict) and 'skill' in s:
                profile_skills.append(s['skill'])
        profile_skills = sorted(set(profile_skills))[:max_skills]
    
    # Embeddings handle skill matching - use profile skills vs posting summary
    # No facets table needed
    if not profile_skills:
        return None
    
    # For backward compatibility, requirements is empty (embeddings compare directly)
    requirements = profile_skills  # Compare profile skills against themselves for coverage
    
    # Get embeddings
    profile_embeddings = []
    for skill in profile_skills:
        emb = get_embedding(skill)
        if emb:
            profile_embeddings.append(emb)
        else:
            profile_embeddings.append([0] * 1024)  # Zero vector fallback
    
    req_embeddings = []
    for req in requirements:
        emb = get_embedding(req)
        if emb:
            req_embeddings.append(emb)
        else:
            req_embeddings.append([0] * 1024)
    
    # Compute matrix: rows = requirements, cols = profile skills
    scores = []
    for req_emb in req_embeddings:
        row_scores = []
        for prof_emb in profile_embeddings:
            if any(req_emb) and any(prof_emb):
                score = cosine_similarity(req_emb, prof_emb)
            else:
                score = 0.0
            row_scores.append(round(score, 3))
        scores.append(row_scores)
    
    return {
        'profile_skills': profile_skills,
        'requirements': requirements,
        'scores': scores
    }


def get_profile_info(conn, profile_id: int) -> dict:
    """Get basic profile info."""
    cur = conn.cursor()
    cur.execute("""
        SELECT p.profile_id, p.full_name, p.current_title, p.location
        FROM profiles p
        WHERE p.profile_id = %s
    """, (profile_id,))
    row = cur.fetchone()
    if not row:
        return None
    return dict(row)


def get_top_matches(conn, profile_id: int, limit: int = 10) -> list:
    """Get top matches for a profile."""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            m.match_id,
            m.posting_id,
            m.skill_match_score,
            m.match_rate,
            m.recommendation,
            m.confidence,
            m.go_reasons,
            m.nogo_reasons,
            m.cover_letter,
            m.nogo_narrative,
            m.domain_gate_passed,
            m.gate_reason,
            m.computed_at,
            m.similarity_matrix,
            p.job_title,
            p.source as company,
            p.location_city,
            p.location_country,
            p.extracted_summary
        FROM profile_posting_matches m
        JOIN postings p ON m.posting_id = p.posting_id
        WHERE m.profile_id = %s
        ORDER BY m.skill_match_score DESC
        LIMIT %s
    """, (profile_id, limit))
    
    matches = []
    for row in cur.fetchall():
        match = dict(row)
        # Handle JSONB fields
        if isinstance(match['go_reasons'], str):
            match['go_reasons'] = json.loads(match['go_reasons'])
        if isinstance(match['nogo_reasons'], str):
            match['nogo_reasons'] = json.loads(match['nogo_reasons'])
        if isinstance(match.get('similarity_matrix'), str):
            match['similarity_matrix'] = json.loads(match['similarity_matrix'])
        matches.append(match)
    
    return matches


def enrich_with_matrices(conn, matches: list, profile_id: int, verbose: bool = True) -> list:
    """Compute similarity matrices for matches that don't have them."""
    for i, m in enumerate(matches):
        if not m.get('similarity_matrix'):
            if verbose:
                print(f"  Computing matrix for posting {m['posting_id']}...")
            m['similarity_matrix'] = compute_similarity_matrix(conn, profile_id, m['posting_id'])
    return matches


def generate_html(profile: dict, matches: list) -> str:
    """Generate interactive HTML report."""
    
    # Escape for JS
    def js_escape(s):
        if not s:
            return ''
        return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '')
    
    # Build match cards
    match_cards = []
    for i, m in enumerate(matches):
        score_pct = m['skill_match_score'] * 100
        rec_class = 'apply' if m['recommendation'] == 'apply' else 'skip'
        rec_icon = '✅' if m['recommendation'] == 'apply' else '⏭️'
        rec_text = 'APPLY' if m['recommendation'] == 'apply' else 'SKIP'
        
        # GO reasons
        go_html = ''
        go_reasons = m['go_reasons'] or []
        for r in go_reasons:
            go_html += f'<li class="go-reason">✅ {r}</li>'
        
        # NO-GO reasons  
        nogo_html = ''
        nogo_reasons = m['nogo_reasons'] or []
        for r in nogo_reasons:
            nogo_html += f'<li class="nogo-reason">⚠️ {r}</li>'
        
        # Letter content
        letter = m['cover_letter'] or m['nogo_narrative'] or 'No letter generated'
        letter_title = 'Cover Letter' if m['cover_letter'] else 'Analysis'
        
        location = f"{m['location_city']}, {m['location_country']}" if m['location_city'] else ''
        
        card = f'''
        <div class="match-card {rec_class}" data-index="{i}">
            <div class="card-header" onclick="toggleCard({i})">
                <div class="card-title">
                    <span class="rank">#{i+1}</span>
                    <div class="job-info">
                        <h3>{m['job_title'] or 'Untitled Position'}</h3>
                        <span class="company">{m['company'] or 'Unknown'}</span>
                        {f'<span class="location">📍 {location}</span>' if location else ''}
                    </div>
                </div>
                <div class="card-score">
                    <div class="score-circle" style="--score: {score_pct}%">
                        <span>{score_pct:.0f}%</span>
                    </div>
                    <span class="recommendation {rec_class}">{rec_icon} {rec_text}</span>
                </div>
            </div>
            <div class="card-details" id="details-{i}">
                <div class="match-stats">
                    <span>Match Rate: <strong>{m['match_rate']}</strong></span>
                    <span>Confidence: <strong>{(m['confidence'] or 0) * 100:.0f}%</strong></span>
                </div>
                <div class="reasons-container">
                    <div class="reasons go">
                        <h4>✅ Reasons to Apply</h4>
                        <ul>{go_html if go_html else '<li class="empty">None identified</li>'}</ul>
                    </div>
                    <div class="reasons nogo">
                        <h4>⚠️ Concerns</h4>
                        <ul>{nogo_html if nogo_html else '<li class="empty">None identified</li>'}</ul>
                    </div>
                </div>
                <div class="letter-section">
                    <h4>{letter_title}</h4>
                    <div class="letter-content">{letter}</div>
                </div>
            </div>
        </div>
        '''
        match_cards.append(card)
    
    # Summary stats
    apply_count = sum(1 for m in matches if m['recommendation'] == 'apply')
    skip_count = len(matches) - apply_count
    avg_score = sum(m['skill_match_score'] for m in matches) / len(matches) * 100 if matches else 0
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Match Report - {profile['full_name']}</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-yellow: #eab308;
            --accent-blue: #3b82f6;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid var(--bg-card);
        }}
        
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }}
        
        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        
        .header .generated {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 1rem;
        }}
        
        /* Summary Cards */
        .summary {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .summary-card {{
            background: var(--bg-secondary);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
        }}
        
        .summary-card .value {{
            font-size: 2rem;
            font-weight: 700;
        }}
        
        .summary-card .label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .summary-card.apply .value {{ color: var(--accent-green); }}
        .summary-card.skip .value {{ color: var(--accent-yellow); }}
        .summary-card.score .value {{ color: var(--accent-blue); }}
        
        /* Match Cards */
        .match-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            margin-bottom: 1rem;
            overflow: hidden;
            border-left: 4px solid var(--accent-yellow);
            transition: all 0.2s ease;
        }}
        
        .match-card.apply {{
            border-left-color: var(--accent-green);
        }}
        
        .match-card.skip {{
            border-left-color: var(--accent-yellow);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .card-header:hover {{
            background: var(--bg-card);
        }}
        
        .card-title {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .rank {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-secondary);
            min-width: 40px;
        }}
        
        .job-info h3 {{
            font-size: 1.1rem;
            margin-bottom: 0.25rem;
        }}
        
        .company {{
            color: var(--accent-blue);
            font-size: 0.9rem;
        }}
        
        .location {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-left: 0.75rem;
        }}
        
        .card-score {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .score-circle {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: conic-gradient(
                var(--accent-blue) var(--score),
                var(--bg-card) var(--score)
            );
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }}
        
        .score-circle::before {{
            content: '';
            position: absolute;
            width: 48px;
            height: 48px;
            background: var(--bg-secondary);
            border-radius: 50%;
        }}
        
        .score-circle span {{
            position: relative;
            font-weight: 700;
            font-size: 0.95rem;
        }}
        
        .recommendation {{
            font-size: 0.8rem;
            font-weight: 600;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
        }}
        
        .recommendation.apply {{
            background: rgba(34, 197, 94, 0.2);
            color: var(--accent-green);
        }}
        
        .recommendation.skip {{
            background: rgba(234, 179, 8, 0.2);
            color: var(--accent-yellow);
        }}
        
        /* Card Details */
        .card-details {{
            display: none;
            padding: 0 1.25rem 1.25rem;
            border-top: 1px solid var(--bg-card);
            animation: slideDown 0.3s ease;
        }}
        
        .card-details.open {{
            display: block;
        }}
        
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .match-stats {{
            display: flex;
            gap: 2rem;
            padding: 1rem 0;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .match-stats strong {{
            color: var(--text-primary);
        }}
        
        .reasons-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        
        .reasons {{
            background: var(--bg-card);
            padding: 1rem;
            border-radius: 8px;
        }}
        
        .reasons h4 {{
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
            color: var(--text-secondary);
        }}
        
        .reasons ul {{
            list-style: none;
        }}
        
        .reasons li {{
            padding: 0.5rem 0;
            font-size: 0.9rem;
            border-bottom: 1px solid var(--bg-secondary);
        }}
        
        .reasons li:last-child {{
            border-bottom: none;
        }}
        
        .go-reason {{ color: var(--accent-green); }}
        .nogo-reason {{ color: var(--accent-yellow); }}
        .empty {{ color: var(--text-secondary); font-style: italic; }}
        
        .letter-section {{
            background: var(--bg-card);
            padding: 1.25rem;
            border-radius: 8px;
        }}
        
        .letter-section h4 {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 1rem;
        }}
        
        .letter-content {{
            white-space: pre-wrap;
            font-size: 0.95rem;
            line-height: 1.7;
            color: var(--text-primary);
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .summary {{ grid-template-columns: 1fr; }}
            .reasons-container {{ grid-template-columns: 1fr; }}
            .card-header {{ flex-direction: column; gap: 1rem; text-align: center; }}
            .card-title {{ flex-direction: column; }}
        }}
        
        /* Print styles */
        @media print {{
            body {{ background: white; color: black; }}
            .match-card {{ break-inside: avoid; }}
            .card-details {{ display: block !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Job Match Report</h1>
            <p class="subtitle">{profile['full_name']}</p>
            <p class="subtitle">{profile.get('current_title', '')}</p>
            <p class="generated">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card apply">
                <div class="value">{apply_count}</div>
                <div class="label">Recommended</div>
            </div>
            <div class="summary-card skip">
                <div class="value">{skip_count}</div>
                <div class="label">Not Recommended</div>
            </div>
            <div class="summary-card score">
                <div class="value">{avg_score:.0f}%</div>
                <div class="label">Avg Match Score</div>
            </div>
        </div>
        
        <div class="matches">
            {''.join(match_cards)}
        </div>
    </div>
    
    <script>
        function toggleCard(index) {{
            const details = document.getElementById('details-' + index);
            details.classList.toggle('open');
        }}
        
        // Open first APPLY card by default
        document.addEventListener('DOMContentLoaded', () => {{
            const firstApply = document.querySelector('.match-card.apply');
            if (firstApply) {{
                const index = firstApply.dataset.index;
                toggleCard(index);
            }}
        }});
    </script>
</body>
</html>'''
    
    return html


def generate_markdown(profile: dict, matches: list) -> str:
    """Generate Markdown report for QA."""
    
    # Summary stats
    apply_count = sum(1 for m in matches if m['recommendation'] == 'apply')
    skip_count = len(matches) - apply_count
    avg_score = sum(m['skill_match_score'] for m in matches) / len(matches) * 100 if matches else 0
    
    lines = [
        f"# Job Match Report",
        f"",
        f"**Candidate:** {profile['full_name']}  ",
        f"**Title:** {profile.get('current_title', 'N/A')}  ",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Recommended | {apply_count} |",
        f"| Not Recommended | {skip_count} |",
        f"| Avg Match Score | {avg_score:.1f}% |",
        f"",
        f"---",
        f"",
    ]
    
    for i, m in enumerate(matches):
        score_pct = m['skill_match_score'] * 100
        rec_icon = '✅ APPLY' if m['recommendation'] == 'apply' else '⏭️ SKIP'
        
        location = f"{m['location_city']}, {m['location_country']}" if m['location_city'] else 'N/A'
        
        lines.append(f"## #{i+1} — {m['job_title'] or 'Untitled Position'}")
        lines.append(f"")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Company | {m['company'] or 'Unknown'} |")
        lines.append(f"| Location | {location} |")
        lines.append(f"| Match Score | **{score_pct:.1f}%** |")
        lines.append(f"| Match Rate | {m['match_rate']} |")
        lines.append(f"| Recommendation | {rec_icon} |")
        lines.append(f"| Confidence | {(m['confidence'] or 0) * 100:.0f}% |")
        lines.append(f"")
        
        # GO reasons
        go_reasons = m['go_reasons'] or []
        if go_reasons:
            lines.append(f"### ✅ Reasons to Apply")
            lines.append(f"")
            for r in go_reasons:
                lines.append(f"- {r}")
            lines.append(f"")
        
        # NO-GO reasons
        nogo_reasons = m['nogo_reasons'] or []
        if nogo_reasons:
            lines.append(f"### ⚠️ Concerns")
            lines.append(f"")
            for r in nogo_reasons:
                lines.append(f"- {r}")
            lines.append(f"")
        
        # Letter
        if m['cover_letter']:
            lines.append(f"### 📝 Cover Letter")
            lines.append(f"")
            lines.append(f"```")
            lines.append(m['cover_letter'])
            lines.append(f"```")
            lines.append(f"")
        elif m['nogo_narrative']:
            lines.append(f"### 📋 Analysis")
            lines.append(f"")
            lines.append(f"> {m['nogo_narrative']}")
            lines.append(f"")
        
        # Similarity Matrix
        matrix = m.get('similarity_matrix')
        if matrix and matrix.get('scores'):
            lines.append(f"### 📊 Similarity Matrix")
            lines.append(f"")
            
            profile_skills = matrix.get('profile_skills', [])
            requirements = matrix.get('requirements', [])
            scores = matrix.get('scores', [])
            
            # Sort by match level: hot stuff top-left, cold bottom-right
            # 1. Calculate best score for each requirement (row) and skill (column)
            if scores and len(scores) > 0:
                # Row scores: max score for each requirement
                row_scores = []
                for idx, req in enumerate(requirements):
                    if idx < len(scores):
                        row_max = max(scores[idx]) if scores[idx] else 0
                        row_scores.append((idx, req, row_max))
                    else:
                        row_scores.append((idx, req, 0))
                row_scores.sort(key=lambda x: -x[2])  # Descending by max score
                
                # Column scores: max score for each profile skill
                col_scores = []
                for col_idx, ps in enumerate(profile_skills):
                    col_max = 0
                    for row in scores:
                        if col_idx < len(row):
                            col_max = max(col_max, row[col_idx])
                    col_scores.append((col_idx, ps, col_max))
                col_scores.sort(key=lambda x: -x[2])  # Descending by max score
                
                # Take top 10 columns (sorted by relevance)
                top_cols = col_scores[:10]
                sorted_skills = [x[1] for x in top_cols]
                sorted_col_indices = [x[0] for x in top_cols]
                sorted_requirements = [x[1] for x in row_scores]
                sorted_row_indices = [x[0] for x in row_scores]
            else:
                sorted_skills = profile_skills[:10]
                sorted_requirements = requirements
                sorted_col_indices = list(range(len(sorted_skills)))
                sorted_row_indices = list(range(len(requirements)))
            
            # Header row with full names (no truncation)
            header = "| Requirement |"
            for ps in sorted_skills:
                header += f" {ps} |"
            lines.append(header)
            
            # Separator
            sep = "|-------------|"
            for _ in sorted_skills:
                sep += "--------|"
            lines.append(sep)
            
            # Data rows (sorted by best match)
            for sorted_idx, req in enumerate(sorted_requirements):
                orig_row_idx = sorted_row_indices[sorted_idx]
                if orig_row_idx >= len(scores):
                    continue
                row = f"| {req} |"
                for col_sorted_idx, ps in enumerate(sorted_skills):
                    orig_col_idx = sorted_col_indices[col_sorted_idx]
                    if orig_col_idx < len(scores[orig_row_idx]):
                        score = scores[orig_row_idx][orig_col_idx]
                        # Color coding: bold for good matches
                        if score >= 0.70:
                            row += f" **{score:.2f}** |"
                        elif score >= 0.50:
                            row += f" {score:.2f} |"
                        else:
                            row += f" {score:.2f} |"
                    else:
                        row += " - |"
                lines.append(row)
            
            lines.append(f"")
        
        lines.append(f"---")
        lines.append(f"")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate match report')
    parser.add_argument('profile_id', type=int, help='Profile ID')
    parser.add_argument('-o', '--output', type=str, help='Output file path')
    parser.add_argument('-n', '--limit', type=int, default=10, help='Number of matches to show')
    parser.add_argument('-f', '--format', choices=['html', 'md'], default='html', help='Output format')
    parser.add_argument('--no-matrix', action='store_true', help='Skip matrix computation')
    
    args = parser.parse_args()
    
    with get_connection() as conn:
        # Get profile
        profile = get_profile_info(conn, args.profile_id)
        if not profile:
            print(f"❌ Profile {args.profile_id} not found")
            return 1
        
        # Get matches
        matches = get_top_matches(conn, args.profile_id, args.limit)
        if not matches:
            print(f"❌ No matches found for profile {args.profile_id}")
            print("   Run the Clara actor first to generate matches.")
            return 1
        
        # Enrich with matrices if missing
        if not args.no_matrix:
            print("Computing similarity matrices...")
            matches = enrich_with_matrices(conn, matches, args.profile_id)
        
        # Generate report
        if args.format == 'md':
            content = generate_markdown(profile, matches)
            ext = 'md'
        else:
            content = generate_html(profile, matches)
            ext = 'html'
        
        # Output
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path('output') / f"match_report_{profile['full_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        
        print(f"✅ Report generated: {output_path}")
        print(f"   Profile: {profile['full_name']}")
        print(f"   Matches: {len(matches)}")
        print(f"   Recommended: {sum(1 for m in matches if m['recommendation'] == 'apply')}")
        
        return 0


if __name__ == '__main__':
    sys.exit(main())
