"""
Match endpoints — profile↔posting matches.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from api.deps import get_db, require_user

router = APIRouter(prefix="/matches", tags=["matches"])


class MatchSummary(BaseModel):
    match_id: int
    posting_id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    skill_match_score: float
    recommendation: Optional[str]
    matched_at: Optional[datetime]
    user_applied: Optional[bool] = False
    user_rating: Optional[int] = None
    application_status: Optional[str] = None
    application_outcome: Optional[str] = None


class MatchDetail(MatchSummary):
    profile_id: int
    similarity_avg: Optional[float]
    matched_skills: List[str]
    missing_skills: List[str]
    clara_verdict: Optional[str]


@router.get("/", response_model=List[MatchSummary])
def list_my_matches(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    recommendation: Optional[str] = Query(None, description="Filter: APPLY or SKIP"),
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    List matches for the current user's profile.
    """
    with conn.cursor() as cur:
        # First get user's profile
        cur.execute("SELECT profile_id FROM profiles WHERE user_id = %s", (user['user_id'],))
        profile = cur.fetchone()
        
        if not profile:
            return []  # No profile = no matches
        
        query = """
            SELECT m.match_id, m.posting_id, p.job_title as title, 
                   p.posting_name as company, p.location_city as location,
                   m.skill_match_score, m.recommendation, m.computed_at as matched_at,
                   m.user_applied, m.user_rating, m.application_status, m.application_outcome
            FROM profile_posting_matches m
            JOIN postings p ON m.posting_id = p.posting_id
            WHERE m.profile_id = %s
        """
        params = [profile['profile_id']]
        
        if recommendation:
            query += " AND m.recommendation = %s"
            params.append(recommendation.upper())
        
        query += " ORDER BY m.skill_match_score DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        return [MatchSummary(**row) for row in cur.fetchall()]


@router.get("/{match_id}", response_model=MatchDetail)
def get_match_detail(match_id: int, user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Get detailed match information including skill breakdown.
    """
    with conn.cursor() as cur:
        # Get match with authorization check
        cur.execute("""
            SELECT m.match_id, m.profile_id, m.posting_id, 
                   p.job_title as title, p.posting_name as company, p.location_city as location,
                   m.skill_match_score, m.recommendation, m.created_at as matched_at,
                   m.similarity_matrix, m.clara_verdict
            FROM profile_posting_matches m
            JOIN postings p ON m.posting_id = p.posting_id
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        # Verify ownership
        cur.execute("SELECT user_id FROM profiles WHERE profile_id = %s", (match['profile_id'],))
        profile = cur.fetchone()
        if not profile or profile['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot view other users' matches")
        
        # Get matched skills (from similarity matrix if available)
        matched_skills = []
        missing_skills = []
        similarity_avg = None
        
        if match.get('similarity_matrix'):
            matrix = match['similarity_matrix']
            if isinstance(matrix, dict) and 'matches' in matrix:
                for m_entry in matrix['matches']:
                    if m_entry.get('similarity', 0) >= 0.7:
                        matched_skills.append(m_entry.get('requirement', ''))
                    elif m_entry.get('similarity', 0) < 0.6:
                        missing_skills.append(m_entry.get('requirement', ''))
                
                sims = [m_entry.get('similarity', 0) for m_entry in matrix['matches']]
                if sims:
                    similarity_avg = sum(sims) / len(sims)
        
        return MatchDetail(
            match_id=match['match_id'],
            profile_id=match['profile_id'],
            posting_id=match['posting_id'],
            title=match['title'],
            company=match['company'],
            location=match['location'],
            skill_match_score=match['skill_match_score'],
            recommendation=match['recommendation'],
            matched_at=match['matched_at'],
            similarity_avg=similarity_avg,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            clara_verdict=match.get('clara_verdict')
        )


class RatingInput(BaseModel):
    rating: int  # 1-5 stars OR -1/+1 for thumbs
    feedback: Optional[str] = None


@router.post("/{match_id}/rate")
def rate_match(
    match_id: int,
    rating: int = Query(..., ge=1, le=5, description="Rating 1-5"),
    feedback: Optional[str] = Query(None, description="Optional feedback"),
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Rate a match (1-5 stars).
    """
    with conn.cursor() as cur:
        # Verify ownership
        cur.execute("""
            SELECT m.match_id, pr.user_id
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot rate other users' matches")
        
        cur.execute("""
            UPDATE profile_posting_matches
            SET user_rating = %s, user_feedback = %s, rated_at = NOW()
            WHERE match_id = %s
        """, (rating, feedback, match_id))
        conn.commit()
        
        return {"status": "ok", "rating": rating, "feedback": feedback}


@router.post("/{match_id}/thumbs")
def thumbs_rating(
    match_id: int,
    thumbs: int = Query(..., description="1 = good match, -1 = bad match"),
    feedback: Optional[str] = Query(None, description="Why? (optional)"),
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Quick thumbs up/down rating for feedback loop.
    Stored as rating: -1 (👎) or 6 (👍) to distinguish from 1-5 stars.
    """
    if thumbs not in (-1, 1):
        raise HTTPException(status_code=400, detail="thumbs must be -1 or 1")
    
    with conn.cursor() as cur:
        # Verify ownership
        cur.execute("""
            SELECT m.match_id, pr.user_id
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot rate other users' matches")
        
        # Store thumbs as: -1 = bad, 6 = good (distinct from 1-5 stars)
        rating_val = 6 if thumbs == 1 else -1
        
        cur.execute("""
            UPDATE profile_posting_matches
            SET user_rating = %s, user_feedback = %s, rated_at = NOW()
            WHERE match_id = %s
        """, (rating_val, feedback, match_id))
        conn.commit()
        
        return {"status": "ok", "thumbs": thumbs, "feedback": feedback}


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None  # applied, interviewing, offered, rejected, withdrawn
    outcome: Optional[str] = None  # hired, rejected, ghosted, withdrew


@router.post("/{match_id}/applied")
def mark_applied(
    match_id: int,
    applied: bool = True,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Mark that user applied to this job.
    """
    with conn.cursor() as cur:
        # Verify ownership
        cur.execute("""
            SELECT m.match_id, pr.user_id
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot update other users' matches")
        
        cur.execute("""
            UPDATE profile_posting_matches
            SET user_applied = %s, 
                applied_at = CASE WHEN %s THEN NOW() ELSE NULL END,
                application_status = CASE WHEN %s THEN 'applied' ELSE NULL END
            WHERE match_id = %s
        """, (applied, applied, applied, match_id))
        conn.commit()
        
        return {"status": "ok", "applied": applied, "application_status": "applied" if applied else None}


@router.patch("/{match_id}/application")
def update_application(
    match_id: int,
    status: Optional[str] = Query(None, description="applied, interviewing, offered, rejected, withdrawn"),
    outcome: Optional[str] = Query(None, description="hired, rejected, ghosted, withdrew"),
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Update application status or outcome.
    """
    valid_statuses = {'applied', 'interviewing', 'offered', 'rejected', 'withdrawn'}
    valid_outcomes = {'hired', 'rejected', 'ghosted', 'withdrew'}
    
    if status and status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    if outcome and outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"Invalid outcome. Must be one of: {valid_outcomes}")
    
    with conn.cursor() as cur:
        # Verify ownership
        cur.execute("""
            SELECT m.match_id, m.user_applied, pr.user_id
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot update other users' matches")
        
        updates = []
        params = []
        
        if status:
            updates.append("application_status = %s")
            params.append(status)
            # Auto-set user_applied if setting status
            if not match.get('user_applied'):
                updates.append("user_applied = TRUE")
                updates.append("applied_at = NOW()")
        
        if outcome:
            updates.append("application_outcome = %s")
            updates.append("outcome_at = NOW()")
            params.append(outcome)
        
        if updates:
            params.append(match_id)
            cur.execute(f"""
                UPDATE profile_posting_matches
                SET {', '.join(updates)}
                WHERE match_id = %s
            """, params)
            conn.commit()
        
        return {"status": "ok", "application_status": status, "application_outcome": outcome}


@router.get("/{match_id}/report")
def get_match_report(
    match_id: int,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get full transparency report for a match (markdown format).
    """
    with conn.cursor() as cur:
        # Get match with all details
        cur.execute("""
            SELECT m.*, 
                   p.job_title, p.posting_name as company, p.location_city,
                   p.job_description, p.extracted_requirements,
                   pr.full_name as profile_name, pr.user_id
            FROM profile_posting_matches m
            JOIN postings p ON m.posting_id = p.posting_id
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot view other users' reports")
        
        # Build markdown report
        report = f"""# Match Report: {match['job_title']}

**Company:** {match['company'] or 'Unknown'}  
**Location:** {match['location_city'] or 'Not specified'}  
**Match Score:** {float(match['skill_match_score'] or 0):.1%}  
**Recommendation:** {match['recommendation'] or 'PENDING'}

---

## Summary

"""
        # Add recommendation reasoning
        if match['recommendation'] == 'APPLY':
            report += "✅ **This looks like a good match!**\n\n"
            if match.get('go_reasons'):
                report += "### Why Apply\n"
                for reason in (match['go_reasons'] if isinstance(match['go_reasons'], list) else []):
                    report += f"- {reason}\n"
                report += "\n"
        else:
            report += "⚠️ **Some concerns with this match.**\n\n"
            if match.get('nogo_reasons'):
                report += "### Concerns\n"
                for reason in (match['nogo_reasons'] if isinstance(match['nogo_reasons'], list) else []):
                    report += f"- {reason}\n"
                report += "\n"
        
        # Skill breakdown
        report += "## Skill Analysis\n\n"
        if match.get('similarity_matrix') and isinstance(match['similarity_matrix'], dict):
            matrix = match['similarity_matrix']
            if 'matches' in matrix:
                report += "| Requirement | Your Skill | Match |\n"
                report += "|-------------|------------|-------|\n"
                for entry in matrix['matches']:
                    req = entry.get('requirement', '')[:40]
                    skill = entry.get('matched_skill', '-')[:30]
                    sim = entry.get('similarity', 0)
                    status = '✅' if sim >= 0.7 else '🟡' if sim >= 0.6 else '❌'
                    report += f"| {req} | {skill} | {status} {sim:.0%} |\n"
                report += "\n"
        
        # Cover letter if available
        if match.get('cover_letter'):
            report += "## Draft Cover Letter\n\n"
            report += match['cover_letter']
            report += "\n\n"
        
        # No-go narrative if available
        if match.get('nogo_narrative'):
            report += "## Why This Might Not Fit\n\n"
            report += match['nogo_narrative']
            report += "\n"
        
        report += f"\n---\n*Generated {match['computed_at']}*"
        
        return {"match_id": match_id, "report": report, "format": "markdown"}


@router.get("/{match_id}/detail")
def get_match_detail_full(
    match_id: int,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get full match detail as structured JSON for report viewer.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.*, 
                   p.job_title, p.posting_name as company, p.location_city,
                   p.job_description, p.external_url, p.posting_id,
                   pr.full_name as profile_name, pr.user_id
            FROM profile_posting_matches m
            JOIN postings p ON m.posting_id = p.posting_id
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot view other users' reports")
        
        # Build skill breakdown from similarity matrix
        skill_breakdown = []
        if match.get('similarity_matrix') and isinstance(match['similarity_matrix'], dict):
            matrix = match['similarity_matrix']
            if 'matches' in matrix:
                for entry in matrix['matches']:
                    skill_breakdown.append({
                        "requirement": entry.get('requirement', ''),
                        "matched_skill": entry.get('matched_skill', ''),
                        "similarity": entry.get('similarity', 0),
                        "status": "strong" if entry.get('similarity', 0) >= 0.7 
                                  else "partial" if entry.get('similarity', 0) >= 0.6 
                                  else "gap"
                    })
        
        return {
            "match_id": match['match_id'],
            "posting_id": match['posting_id'],
            "title": match['job_title'],
            "company": match['company'],
            "location": match['location_city'],
            "posting_url": match.get('external_url'),
            "score": float(match['skill_match_score'] or 0),
            "recommendation": match['recommendation'],
            "go_reasons": match.get('go_reasons') or [],
            "nogo_reasons": match.get('nogo_reasons') or [],
            "nogo_narrative": match.get('nogo_narrative'),
            "skill_breakdown": skill_breakdown,
            "similarity_matrix": match.get('similarity_matrix'),
            "cover_letter": match.get('cover_letter'),
            "user_applied": match.get('user_applied', False),
            "user_rating": match.get('user_rating'),
            "computed_at": str(match.get('computed_at', ''))
        }


@router.get("/calibration")
def get_calibration_metrics(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get threshold calibration metrics for P4.3.
    Shows how well current thresholds match user preferences.
    """
    with conn.cursor() as cur:
        # Approval rate by tier
        cur.execute("""
            SELECT 
                CASE 
                    WHEN skill_match_score >= 0.70 THEN 'strong'
                    WHEN skill_match_score >= 0.60 THEN 'partial'
                    ELSE 'low'
                END as tier,
                COUNT(*) as total_rated,
                SUM(CASE WHEN user_rating IN (4, 5, 6) THEN 1 ELSE 0 END) as approved,
                ROUND(100.0 * SUM(CASE WHEN user_rating IN (4, 5, 6) THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as approval_pct
            FROM profile_posting_matches
            WHERE user_rating IS NOT NULL
            GROUP BY 1
            ORDER BY 1;
        """)
        approval_by_tier = [dict(row) for row in cur.fetchall()]
        
        # Application rate by score bucket
        cur.execute("""
            SELECT 
                ROUND(skill_match_score, 1) as score_bucket,
                COUNT(*) as total_matches,
                SUM(CASE WHEN user_applied THEN 1 ELSE 0 END) as applied,
                ROUND(100.0 * SUM(CASE WHEN user_applied THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as apply_rate
            FROM profile_posting_matches
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT 10;
        """)
        application_by_score = [dict(row) for row in cur.fetchall()]
        
        # Outcomes summary
        cur.execute("""
            SELECT 
                application_outcome,
                COUNT(*) as count
            FROM profile_posting_matches
            WHERE application_outcome IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC;
        """)
        outcomes = [dict(row) for row in cur.fetchall()]
        
        # Rating distribution
        cur.execute("""
            SELECT 
                CASE 
                    WHEN user_rating = 6 THEN 'thumbs_up'
                    WHEN user_rating = -1 THEN 'thumbs_down'
                    WHEN user_rating BETWEEN 1 AND 5 THEN 'stars_' || user_rating::text
                    ELSE 'unrated'
                END as rating_type,
                COUNT(*) as count
            FROM profile_posting_matches
            GROUP BY 1
            ORDER BY 2 DESC;
        """)
        rating_distribution = [dict(row) for row in cur.fetchall()]
        
        return {
            "approval_by_tier": approval_by_tier,
            "application_by_score": application_by_score,
            "outcomes": outcomes,
            "rating_distribution": rating_distribution,
            "current_thresholds": {
                "strong": 0.70,
                "partial": 0.60,
                "cutoff": 0.50
            }
        }

