"""
Interactions router — track yogi engagement with postings.

Handles:
- Read/unread state
- Favorites/bookmarks
- Match feedback (agree/disagree)
- Interest expression
- Journey state transitions
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/interactions", tags=["interactions"])


# ============================================================
# Models
# ============================================================

class InteractionState(BaseModel):
    posting_id: int
    is_read: bool
    view_count: int
    is_favorited: bool
    is_interested: bool
    match_feedback: Optional[str]
    state: str


class MarkReadRequest(BaseModel):
    posting_id: int
    view_seconds: Optional[int] = 0


class FavoriteRequest(BaseModel):
    posting_id: int
    favorited: bool


class FeedbackRequest(BaseModel):
    posting_id: int
    feedback: Literal["agree", "disagree"]


class InterestRequest(BaseModel):
    posting_id: int
    interested: bool


class StateTransitionRequest(BaseModel):
    posting_id: int
    new_state: str


# ============================================================
# Helpers
# ============================================================

def get_or_create_interaction(cur, user_id: int, posting_id: int) -> dict:
    """Get existing interaction or create new one."""
    cur.execute("""
        INSERT INTO user_posting_interactions (user_id, posting_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, posting_id) DO NOTHING
        RETURNING interaction_id
    """, (user_id, posting_id))
    
    cur.execute("""
        SELECT * FROM user_posting_interactions
        WHERE user_id = %s AND posting_id = %s
    """, (user_id, posting_id))
    
    return cur.fetchone()


# ============================================================
# Endpoints
# ============================================================

@router.get("/posting/{posting_id}", response_model=InteractionState)
def get_interaction(
    posting_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get interaction state for a specific posting."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT posting_id, first_viewed_at, view_count, 
                   is_favorited, is_interested, match_feedback, state
            FROM user_posting_interactions
            WHERE user_id = %s AND posting_id = %s
        """, (user['user_id'], posting_id))
        
        row = cur.fetchone()
        
        if not row:
            return InteractionState(
                posting_id=posting_id,
                is_read=False,
                view_count=0,
                is_favorited=False,
                is_interested=False,
                match_feedback=None,
                state="unread"
            )
        
        return InteractionState(
            posting_id=row['posting_id'],
            is_read=row['first_viewed_at'] is not None,
            view_count=row['view_count'],
            is_favorited=row['is_favorited'],
            is_interested=row['is_interested'],
            match_feedback=row['match_feedback'],
            state=row['state']
        )


@router.get("/favorites", response_model=List[int])
def get_favorites(
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get list of favorited posting IDs."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT posting_id FROM user_posting_interactions
            WHERE user_id = %s AND is_favorited = TRUE
            ORDER BY favorited_at DESC
        """, (user['user_id'],))
        
        return [row['posting_id'] for row in cur.fetchall()]


@router.get("/interested", response_model=List[int])
def get_interested(
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get list of posting IDs where yogi expressed interest."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT posting_id FROM user_posting_interactions
            WHERE user_id = %s AND is_interested = TRUE
            ORDER BY interested_at DESC
        """, (user['user_id'],))
        
        return [row['posting_id'] for row in cur.fetchall()]


@router.post("/read")
def mark_read(
    request: MarkReadRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Mark a posting as read, track view time."""
    with conn.cursor() as cur:
        interaction = get_or_create_interaction(cur, user['user_id'], request.posting_id)
        
        # Update view tracking
        if interaction['first_viewed_at'] is None:
            # First view
            cur.execute("""
                UPDATE user_posting_interactions
                SET first_viewed_at = NOW(),
                    view_count = 1,
                    total_view_seconds = %s,
                    state = CASE WHEN state = 'unread' THEN 'read' ELSE state END,
                    state_changed_at = CASE WHEN state = 'unread' THEN NOW() ELSE state_changed_at END,
                    updated_at = NOW()
                WHERE user_id = %s AND posting_id = %s
            """, (request.view_seconds, user['user_id'], request.posting_id))
        else:
            # Subsequent view
            cur.execute("""
                UPDATE user_posting_interactions
                SET view_count = view_count + 1,
                    total_view_seconds = total_view_seconds + %s,
                    updated_at = NOW()
                WHERE user_id = %s AND posting_id = %s
            """, (request.view_seconds, user['user_id'], request.posting_id))
        
        conn.commit()
        
        logger.info(f"User {user['user_id']} viewed posting {request.posting_id} (+{request.view_seconds}s)")
        return {"status": "ok", "posting_id": request.posting_id}


@router.post("/favorite")
def toggle_favorite(
    request: FavoriteRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Add or remove posting from favorites."""
    with conn.cursor() as cur:
        get_or_create_interaction(cur, user['user_id'], request.posting_id)
        
        if request.favorited:
            cur.execute("""
                UPDATE user_posting_interactions
                SET is_favorited = TRUE,
                    favorited_at = NOW(),
                    state = CASE WHEN state IN ('unread', 'read') THEN 'favorited' ELSE state END,
                    state_changed_at = CASE WHEN state IN ('unread', 'read') THEN NOW() ELSE state_changed_at END,
                    updated_at = NOW()
                WHERE user_id = %s AND posting_id = %s
            """, (user['user_id'], request.posting_id))
        else:
            cur.execute("""
                UPDATE user_posting_interactions
                SET is_favorited = FALSE,
                    favorited_at = NULL,
                    state = CASE WHEN state = 'favorited' THEN 'read' ELSE state END,
                    state_changed_at = CASE WHEN state = 'favorited' THEN NOW() ELSE state_changed_at END,
                    updated_at = NOW()
                WHERE user_id = %s AND posting_id = %s
            """, (user['user_id'], request.posting_id))
        
        conn.commit()
        
        action = "favorited" if request.favorited else "unfavorited"
        logger.info(f"User {user['user_id']} {action} posting {request.posting_id}")
        return {"status": "ok", "posting_id": request.posting_id, "favorited": request.favorited}


@router.post("/feedback")
def submit_feedback(
    request: FeedbackRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Submit match quality feedback (agree/disagree)."""
    with conn.cursor() as cur:
        get_or_create_interaction(cur, user['user_id'], request.posting_id)
        
        cur.execute("""
            UPDATE user_posting_interactions
            SET match_feedback = %s,
                match_feedback_at = NOW(),
                updated_at = NOW()
            WHERE user_id = %s AND posting_id = %s
        """, (request.feedback, user['user_id'], request.posting_id))
        
        conn.commit()
        
        logger.info(f"User {user['user_id']} feedback on posting {request.posting_id}: {request.feedback}")
        return {"status": "ok", "posting_id": request.posting_id, "feedback": request.feedback}


@router.post("/interest")
def toggle_interest(
    request: InterestRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Express or withdraw interest in a posting."""
    with conn.cursor() as cur:
        get_or_create_interaction(cur, user['user_id'], request.posting_id)
        
        if request.interested:
            cur.execute("""
                UPDATE user_posting_interactions
                SET is_interested = TRUE,
                    interested_at = NOW(),
                    state = CASE WHEN state IN ('unread', 'read', 'favorited') THEN 'interested' ELSE state END,
                    state_changed_at = CASE WHEN state IN ('unread', 'read', 'favorited') THEN NOW() ELSE state_changed_at END,
                    updated_at = NOW()
                WHERE user_id = %s AND posting_id = %s
            """, (user['user_id'], request.posting_id))
        else:
            cur.execute("""
                UPDATE user_posting_interactions
                SET is_interested = FALSE,
                    interested_at = NULL,
                    state = CASE 
                        WHEN state = 'interested' AND is_favorited THEN 'favorited'
                        WHEN state = 'interested' THEN 'read'
                        ELSE state 
                    END,
                    state_changed_at = CASE WHEN state = 'interested' THEN NOW() ELSE state_changed_at END,
                    updated_at = NOW()
                WHERE user_id = %s AND posting_id = %s
            """, (user['user_id'], request.posting_id))
        
        conn.commit()
        
        action = "interested in" if request.interested else "no longer interested in"
        logger.info(f"User {user['user_id']} {action} posting {request.posting_id}")
        return {"status": "ok", "posting_id": request.posting_id, "interested": request.interested}


@router.post("/state")
def update_state(
    request: StateTransitionRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Manually transition posting state (for journey tracking)."""
    valid_states = [
        'unread', 'read', 'favorited', 'interested',
        'researching', 'informed', 'coaching',
        'applied', 'outcome_pending',
        'hired', 'rejected', 'ghosted', 'unresponsive'
    ]
    
    if request.new_state not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid state. Must be one of: {valid_states}")
    
    with conn.cursor() as cur:
        get_or_create_interaction(cur, user['user_id'], request.posting_id)
        
        cur.execute("""
            UPDATE user_posting_interactions
            SET state = %s,
                state_changed_at = NOW(),
                updated_at = NOW()
            WHERE user_id = %s AND posting_id = %s
            RETURNING state
        """, (request.new_state, user['user_id'], request.posting_id))
        
        result = cur.fetchone()
        conn.commit()
        
        logger.info(f"User {user['user_id']} posting {request.posting_id} → {request.new_state}")
        return {"status": "ok", "posting_id": request.posting_id, "state": result['state']}


@router.get("/stats")
def get_stats(
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get yogi's interaction statistics."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE first_viewed_at IS NOT NULL) as total_viewed,
                COUNT(*) FILTER (WHERE is_favorited) as total_favorited,
                COUNT(*) FILTER (WHERE is_interested) as total_interested,
                COUNT(*) FILTER (WHERE match_feedback = 'agree') as feedback_agree,
                COUNT(*) FILTER (WHERE match_feedback = 'disagree') as feedback_disagree,
                COUNT(*) FILTER (WHERE state = 'applied') as total_applied,
                COUNT(*) FILTER (WHERE state = 'hired') as total_hired,
                COUNT(*) FILTER (WHERE state = 'rejected') as total_rejected,
                COUNT(*) FILTER (WHERE state = 'ghosted') as total_ghosted,
                COALESCE(SUM(total_view_seconds), 0) as total_view_seconds
            FROM user_posting_interactions
            WHERE user_id = %s
        """, (user['user_id'],))
        
        row = cur.fetchone()
        
        return {
            "viewed": row['total_viewed'],
            "favorited": row['total_favorited'],
            "interested": row['total_interested'],
            "feedback": {
                "agree": row['feedback_agree'],
                "disagree": row['feedback_disagree']
            },
            "applications": {
                "applied": row['total_applied'],
                "hired": row['total_hired'],
                "rejected": row['total_rejected'],
                "ghosted": row['total_ghosted']
            },
            "total_view_minutes": round(row['total_view_seconds'] / 60, 1)
        }


# ============================================================
# Simple path-based endpoints for frontend convenience
# ============================================================

@router.get("/state/{posting_id}")
def get_state(
    posting_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get interaction state for a specific posting (simpler endpoint)."""
    return get_interaction(posting_id, user, conn)


@router.post("/read/{posting_id}")
def mark_read_simple(
    posting_id: int,
    view_seconds: int = 0,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Mark a posting as read (path-based)."""
    request = MarkReadRequest(posting_id=posting_id, view_seconds=view_seconds)
    return mark_read(request, user, conn)


@router.post("/favorite/{posting_id}")
def toggle_favorite_simple(
    posting_id: int,
    favorited: bool = True,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Toggle favorite (path-based)."""
    request = FavoriteRequest(posting_id=posting_id, favorited=favorited)
    return toggle_favorite(request, user, conn)


@router.post("/feedback/{posting_id}")
def submit_feedback_simple(
    posting_id: int,
    feedback: Optional[Literal["agree", "disagree"]] = None,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Submit feedback (path-based). Pass no feedback to clear."""
    if feedback is None:
        # Clear feedback
        with conn.cursor() as cur:
            get_or_create_interaction(cur, user['user_id'], posting_id)
            cur.execute("""
                UPDATE user_posting_interactions
                SET match_feedback = NULL,
                    match_feedback_at = NULL,
                    updated_at = NOW()
                WHERE user_id = %s AND posting_id = %s
            """, (user['user_id'], posting_id))
            conn.commit()
            
            logger.info(f"User {user['user_id']} cleared feedback on posting {posting_id}")
            return {"status": "ok", "posting_id": posting_id, "feedback": None}
    
    request = FeedbackRequest(posting_id=posting_id, feedback=feedback)
    return submit_feedback(request, user, conn)


@router.post("/interest/{posting_id}")
def toggle_interest_simple(
    posting_id: int,
    interested: bool = True,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Toggle interest (path-based)."""
    request = InterestRequest(posting_id=posting_id, interested=interested)
    return toggle_interest(request, user, conn)


@router.post("/research/{posting_id}")
def request_research(
    posting_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Request Doug to research this posting.
    Sets state to 'researching'. Doug actor picks it up.
    """
    cur = conn.cursor()
    user_id = user['user_id']
    
    # Ensure interaction exists
    cur.execute("""
        INSERT INTO user_posting_interactions (user_id, posting_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, posting_id) DO NOTHING
    """, (user_id, posting_id))
    
    # Check current state
    cur.execute("""
        SELECT state FROM user_posting_interactions
        WHERE user_id = %s AND posting_id = %s
    """, (user_id, posting_id))
    
    row = cur.fetchone()
    current_state = row['state'] if row else 'unread'
    
    # Don't re-research if already done
    if current_state in ('researching', 'informed', 'coaching', 'applied', 
                         'outcome_pending', 'hired', 'rejected', 'ghosted'):
        return {
            "status": "already_processed", 
            "posting_id": posting_id, 
            "state": current_state,
            "message": "Research already requested or completed"
        }
    
    # Set to researching
    cur.execute("""
        UPDATE user_posting_interactions
        SET state = 'researching', state_changed_at = NOW(), updated_at = NOW(),
            is_interested = TRUE  -- Requesting research implies interest
        WHERE user_id = %s AND posting_id = %s
        RETURNING interaction_id
    """, (user_id, posting_id))
    
    result = cur.fetchone()
    conn.commit()
    
    logger.info(f"User {user_id} requested research on posting {posting_id}")
    
    return {
        "status": "ok",
        "posting_id": posting_id,
        "state": "researching",
        "message": "Doug is on it! You'll receive a message when the research is ready."
    }
