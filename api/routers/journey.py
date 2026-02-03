"""
Journey router — visual board and badges for yogi progress.

The journey is visualized like a board game:
- Each posting's state represents a position on the board
- Past positions are shown (history)
- Current position highlighted
- Next possible moves indicated

Badges celebrate milestones:
- Novice Yogi: Profile created
- Active Yogi: First application
- Resilient Yogi: Continued after rejection
- Patient Yogi: Continued after ghosting
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Literal
from datetime import datetime, timedelta

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/journey", tags=["journey"])


# ============================================================================
# STATE MACHINE DEFINITION
# ============================================================================

# Board positions in order (like a board game path)
JOURNEY_STATES = [
    'unread',       # 0: Not yet seen
    'read',         # 1: Seen but no action
    'favorited',    # 2: Bookmarked for later
    'interested',   # 3: Expressed interest
    'researching',  # 4: Doug researching
    'informed',     # 5: Research complete
    'coaching',     # 6: Adele coaching
    'applied',      # 7: Application sent
    'outcome_pending',  # 8: Waiting for response
    # End states (branches)
    'hired',        # 🎉 Success!
    'rejected',     # ❌ Not selected
    'ghosted',      # 👻 No response (30+ days)
    'unresponsive', # 🔕 Company not responding
    'resting',      # 💤 Yogi taking a break
]

# Human-readable labels (du-form)
STATE_LABELS_DU = {
    'unread': ('Entdeckt 🔍', 'Mira hat diesen Job für dich gefunden'),
    'read': ('Gesehen 👀', 'Du hast dir den Job angeschaut'),
    'favorited': ('Gemerkt ⭐', 'Auf deiner Merkliste'),
    'interested': ('Interessiert 💡', 'Du möchtest mehr wissen'),
    'researching': ('Doug recherchiert 🔎', 'Doug sucht Infos zum Unternehmen'),
    'informed': ('Informiert 📚', 'Du hast Dougs Recherche gelesen'),
    'coaching': ('Adele übt mit dir 🎯', 'Interview-Vorbereitung läuft'),
    'applied': ('Beworben ✉️', 'Bewerbung abgeschickt!'),
    'outcome_pending': ('Abwarten ⏳', 'Du wartest auf Rückmeldung'),
    'hired': ('Eingestellt! 🎉', 'Herzlichen Glückwunsch!'),
    'rejected': ('Abgesagt ❌', 'Leider nicht geklappt'),
    'ghosted': ('Keine Antwort 👻', 'Über 30 Tage keine Rückmeldung'),
    'unresponsive': ('Keine Reaktion 🔕', 'Unternehmen antwortet nicht'),
    'resting': ('Pause 💤', 'Du machst gerade eine Pause'),
}

# Human-readable labels (Sie-form)
STATE_LABELS_SIE = {
    'unread': ('Entdeckt 🔍', 'Mira hat diesen Job für Sie gefunden'),
    'read': ('Gesehen 👀', 'Sie haben sich den Job angeschaut'),
    'favorited': ('Gemerkt ⭐', 'Auf Ihrer Merkliste'),
    'interested': ('Interessiert 💡', 'Sie möchten mehr wissen'),
    'researching': ('Doug recherchiert 🔎', 'Doug sucht Infos zum Unternehmen'),
    'informed': ('Informiert 📚', 'Sie haben Dougs Recherche gelesen'),
    'coaching': ('Adele übt mit Ihnen 🎯', 'Interview-Vorbereitung läuft'),
    'applied': ('Beworben ✉️', 'Bewerbung abgeschickt!'),
    'outcome_pending': ('Abwarten ⏳', 'Sie warten auf Rückmeldung'),
    'hired': ('Eingestellt! 🎉', 'Herzlichen Glückwunsch!'),
    'rejected': ('Abgesagt ❌', 'Leider nicht geklappt'),
    'ghosted': ('Keine Antwort 👻', 'Über 30 Tage keine Rückmeldung'),
    'unresponsive': ('Keine Reaktion 🔕', 'Unternehmen antwortet nicht'),
    'resting': ('Pause 💤', 'Sie machen gerade eine Pause'),
}

# Valid next states from each state
VALID_TRANSITIONS = {
    'unread': ['read'],
    'read': ['favorited', 'interested', 'resting'],
    'favorited': ['interested', 'read', 'resting'],
    'interested': ['researching', 'applied', 'resting'],
    'researching': ['informed'],  # Doug handles this
    'informed': ['coaching', 'applied', 'resting'],
    'coaching': ['applied', 'resting'],  # Adele handles this
    'applied': ['outcome_pending', 'hired', 'rejected'],
    'outcome_pending': ['hired', 'rejected', 'ghosted', 'unresponsive'],
    'hired': [],  # End state
    'rejected': ['read'],  # Can try again with same or different posting
    'ghosted': ['read'],
    'unresponsive': ['read'],
    'resting': ['read', 'interested', 'applied'],  # Can resume
}


# ============================================================================
# MODELS
# ============================================================================

class JourneyPosition(BaseModel):
    posting_id: int
    posting_title: str
    company: str
    state: str
    state_label: str
    state_description: str
    position: int  # Board position (0-based)
    next_moves: List[str]
    is_end_state: bool
    state_changed_at: Optional[datetime]


class JourneyBoard(BaseModel):
    positions: List[JourneyPosition]
    total_journeys: int
    active_journeys: int
    completed_journeys: int


class Badge(BaseModel):
    badge_id: str
    name: str
    description: str
    emoji: str
    earned_at: Optional[datetime]
    is_earned: bool


class BadgeCollection(BaseModel):
    badges: List[Badge]
    total_earned: int
    total_available: int


# ============================================================================
# BADGE DEFINITIONS
# ============================================================================

BADGE_DEFINITIONS = [
    {
        'badge_id': 'novice_yogi',
        'name': 'Novice Yogi',
        'description_du': 'Du hast dein Profil erstellt!',
        'description_sie': 'Sie haben Ihr Profil erstellt!',
        'emoji': '🧘',
        'check': 'has_profile'
    },
    {
        'badge_id': 'skill_master',
        'name': 'Skill Master',
        'description_du': 'Du hast mindestens 5 Skills eingetragen.',
        'description_sie': 'Sie haben mindestens 5 Skills eingetragen.',
        'emoji': '🎯',
        'check': 'has_5_skills'
    },
    {
        'badge_id': 'active_yogi',
        'name': 'Active Yogi',
        'description_du': 'Deine erste Bewerbung!',
        'description_sie': 'Ihre erste Bewerbung!',
        'emoji': '🎆',
        'check': 'first_application'
    },
    {
        'badge_id': 'resilient_yogi',
        'name': 'Resilient Yogi',
        'description_du': 'Nach einer Absage weitergemacht.',
        'description_sie': 'Nach einer Absage weitergemacht.',
        'emoji': '💪',
        'check': 'continued_after_rejection'
    },
    {
        'badge_id': 'patient_yogi',
        'name': 'Patient Yogi',
        'description_du': 'Nach Ghosting weitergemacht.',
        'description_sie': 'Nach Ghosting weitergemacht.',
        'emoji': '🕰️',
        'check': 'continued_after_ghosting'
    },
    {
        'badge_id': 'researcher_yogi',
        'name': 'Researcher Yogi',
        'description_du': 'Erste Recherche mit Doug.',
        'description_sie': 'Erste Recherche mit Doug.',
        'emoji': '🔬',
        'check': 'first_research'
    },
    {
        'badge_id': 'prepared_yogi',
        'name': 'Prepared Yogi',
        'description_du': 'Erstes Interview-Coaching mit Adele.',
        'description_sie': 'Erstes Interview-Coaching mit Adele.',
        'emoji': '🎤',
        'check': 'first_coaching'
    },
    {
        'badge_id': 'successful_yogi',
        'name': 'Successful Yogi',
        'description_du': 'Du wurdest eingestellt! 🎉',
        'description_sie': 'Sie wurden eingestellt! 🎉',
        'emoji': '🏆',
        'check': 'got_hired'
    },
]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/board", response_model=JourneyBoard)
def get_journey_board(
    uses_du: bool = True,
    limit: int = 20,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get the journey board showing all active job journeys.
    
    Returns posting states visualized as board game positions.
    """
    labels = STATE_LABELS_DU if uses_du else STATE_LABELS_SIE
    
    with conn.cursor() as cur:
        # Get all interactions with posting info
        cur.execute("""
            SELECT 
                i.posting_id, i.state, i.state_changed_at,
                p.job_title as title, p.posting_name as company_name
            FROM user_posting_interactions i
            JOIN postings p ON i.posting_id = p.posting_id
            WHERE i.user_id = %s
            ORDER BY i.state_changed_at DESC NULLS LAST
            LIMIT %s
        """, (user['user_id'], limit))
        
        rows = cur.fetchall()
        
        # Count stats
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE state NOT IN ('hired', 'rejected', 'ghosted', 'unresponsive')) as active,
                COUNT(*) FILTER (WHERE state IN ('hired', 'rejected', 'ghosted', 'unresponsive')) as completed
            FROM user_posting_interactions
            WHERE user_id = %s
        """, (user['user_id'],))
        
        stats = cur.fetchone()
    
    positions = []
    for row in rows:
        state = row['state']
        label, desc = labels.get(state, (state, ''))
        
        # Calculate board position
        if state in JOURNEY_STATES:
            position = JOURNEY_STATES.index(state)
        else:
            position = -1
        
        # Determine if end state
        is_end = state in ['hired', 'rejected', 'ghosted', 'unresponsive']
        
        # Get valid next moves
        next_moves = VALID_TRANSITIONS.get(state, [])
        
        positions.append(JourneyPosition(
            posting_id=row['posting_id'],
            posting_title=row['title'] or 'Unknown',
            company=row['company_name'] or 'Unknown',
            state=state,
            state_label=label,
            state_description=desc,
            position=position,
            next_moves=next_moves,
            is_end_state=is_end,
            state_changed_at=row['state_changed_at']
        ))
    
    return JourneyBoard(
        positions=positions,
        total_journeys=stats['total'],
        active_journeys=stats['active'],
        completed_journeys=stats['completed']
    )


@router.get("/posting/{posting_id}", response_model=JourneyPosition)
def get_posting_journey(
    posting_id: int,
    uses_du: bool = True,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Get journey position for a specific posting."""
    labels = STATE_LABELS_DU if uses_du else STATE_LABELS_SIE
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                i.posting_id, i.state, i.state_changed_at,
                p.job_title as title, p.posting_name as company_name
            FROM user_posting_interactions i
            JOIN postings p ON i.posting_id = p.posting_id
            WHERE i.user_id = %s AND i.posting_id = %s
        """, (user['user_id'], posting_id))
        
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="No journey found for this posting")
        
        state = row['state']
        label, desc = labels.get(state, (state, ''))
        position = JOURNEY_STATES.index(state) if state in JOURNEY_STATES else -1
        is_end = state in ['hired', 'rejected', 'ghosted', 'unresponsive']
        next_moves = VALID_TRANSITIONS.get(state, [])
        
        return JourneyPosition(
            posting_id=row['posting_id'],
            posting_title=row['title'] or 'Unknown',
            company=row['company_name'] or 'Unknown',
            state=state,
            state_label=label,
            state_description=desc,
            position=position,
            next_moves=next_moves,
            is_end_state=is_end,
            state_changed_at=row['state_changed_at']
        )


@router.get("/badges", response_model=BadgeCollection)
def get_badges(
    uses_du: bool = True,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get badge collection for user.
    
    Checks each badge condition and returns earned status.
    """
    with conn.cursor() as cur:
        # Gather all the data we need for badge checks
        
        # Check profile
        cur.execute("""
            SELECT 
                p.profile_id IS NOT NULL as has_profile,
                p.skill_keywords
            FROM users u
            LEFT JOIN profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user['user_id'],))
        profile_row = cur.fetchone()
        
        # Check interactions
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE state = 'applied') as applied_count,
                COUNT(*) FILTER (WHERE state = 'hired') as hired_count,
                COUNT(*) FILTER (WHERE state = 'rejected') as rejected_count,
                COUNT(*) FILTER (WHERE state = 'ghosted') as ghosted_count,
                COUNT(*) FILTER (WHERE state = 'informed') as informed_count,
                COUNT(*) FILTER (WHERE state = 'coaching') as coaching_count
            FROM user_posting_interactions
            WHERE user_id = %s
        """, (user['user_id'],))
        int_row = cur.fetchone()
        
        # Check for resilience (applied after rejection)
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM user_posting_interactions i1
                JOIN user_posting_interactions i2 ON i1.user_id = i2.user_id
                WHERE i1.user_id = %s 
                  AND i1.state = 'applied' 
                  AND i2.state = 'rejected'
                  AND i1.state_changed_at > i2.state_changed_at
            ) as resilient
        """, (user['user_id'],))
        resilient = cur.fetchone()['resilient']
        
        # Check for patience (applied after ghosting)
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM user_posting_interactions i1
                JOIN user_posting_interactions i2 ON i1.user_id = i2.user_id
                WHERE i1.user_id = %s 
                  AND i1.state = 'applied' 
                  AND i2.state = 'ghosted'
                  AND i1.state_changed_at > i2.state_changed_at
            ) as patient
        """, (user['user_id'],))
        patient = cur.fetchone()['patient']
    
    # Build badge status
    has_profile = profile_row['has_profile'] if profile_row else False
    skills = profile_row['skill_keywords'] if profile_row and profile_row['skill_keywords'] else '[]'
    
    # Count skills (parse JSON array)
    try:
        import json
        skill_count = len(json.loads(skills)) if skills else 0
    except:
        skill_count = 0
    
    badge_checks = {
        'has_profile': has_profile,
        'has_5_skills': skill_count >= 5,
        'first_application': int_row['applied_count'] > 0,
        'continued_after_rejection': resilient,
        'continued_after_ghosting': patient,
        'first_research': int_row['informed_count'] > 0,
        'first_coaching': int_row['coaching_count'] > 0,
        'got_hired': int_row['hired_count'] > 0,
    }
    
    badges = []
    earned_count = 0
    
    for badge_def in BADGE_DEFINITIONS:
        is_earned = badge_checks.get(badge_def['check'], False)
        if is_earned:
            earned_count += 1
        
        description = badge_def['description_du'] if uses_du else badge_def['description_sie']
        
        badges.append(Badge(
            badge_id=badge_def['badge_id'],
            name=badge_def['name'],
            description=description,
            emoji=badge_def['emoji'],
            earned_at=datetime.now() if is_earned else None,  # TODO: Track actual earned_at
            is_earned=is_earned
        ))
    
    return BadgeCollection(
        badges=badges,
        total_earned=earned_count,
        total_available=len(BADGE_DEFINITIONS)
    )


@router.post("/rest/{posting_id}")
def set_resting(
    posting_id: int,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Mark a posting journey as 'resting' (taking a break).
    
    Yogi can return later by moving to another state.
    """
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE user_posting_interactions
            SET state = 'resting',
                state_changed_at = NOW(),
                updated_at = NOW()
            WHERE user_id = %s AND posting_id = %s
            RETURNING state
        """, (user['user_id'], posting_id))
        
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="No journey found for this posting")
        
        conn.commit()
        
        logger.info(f"User {user['user_id']} set posting {posting_id} to resting")
        return {"status": "ok", "posting_id": posting_id, "state": "resting"}


@router.get("/summary")
def get_journey_summary(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get summary statistics for user's job search journey.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                state, 
                COUNT(*) as count
            FROM user_posting_interactions
            WHERE user_id = %s
            GROUP BY state
            ORDER BY count DESC
        """, (user['user_id'],))
        
        state_counts = {row['state']: row['count'] for row in cur.fetchall()}
        
        # Calculate funnel
        discovered = sum(state_counts.values())
        engaged = sum(v for k, v in state_counts.items() 
                     if k not in ['unread'])
        applied = sum(v for k, v in state_counts.items() 
                     if k in ['applied', 'outcome_pending', 'hired', 'rejected', 'ghosted', 'unresponsive'])
        outcomes = sum(v for k, v in state_counts.items() 
                      if k in ['hired', 'rejected', 'ghosted', 'unresponsive'])
        hired = state_counts.get('hired', 0)
    
    return {
        "state_counts": state_counts,
        "funnel": {
            "discovered": discovered,
            "engaged": engaged,
            "applied": applied,
            "outcomes": outcomes,
            "hired": hired
        },
        "conversion_rates": {
            "engaged_rate": round(engaged / discovered * 100, 1) if discovered > 0 else 0,
            "applied_rate": round(applied / engaged * 100, 1) if engaged > 0 else 0,
            "success_rate": round(hired / applied * 100, 1) if applied > 0 else 0
        }
    }
