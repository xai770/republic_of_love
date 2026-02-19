"""
FastAPI Dependencies — database connection, current user, etc.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import Depends, HTTPException, status, Request
from typing import Optional
import jwt
from datetime import datetime

from api.config import DATABASE_URL, SECRET_KEY


def get_db():
    """Database connection dependency."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(request: Request, conn=Depends(get_db)) -> Optional[dict]:
    """
    Extract current user from session cookie.
    Returns None if not authenticated.
    """
    token = request.cookies.get('session')
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        # Check if token is expired
        exp = payload.get('exp')
        if exp and datetime.utcnow().timestamp() > exp:
            return None
        
        # Fetch user from database
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, email, display_name, avatar_url, enabled,
                       notification_email, notification_consent_at, notification_preferences,
                       is_admin, yogi_name, onboarding_completed_at
                FROM users
                WHERE user_id = %s AND enabled = TRUE
            """, (user_id,))
            user = cur.fetchone()
        
        return dict(user) if user else None
    
    except jwt.InvalidTokenError:
        return None


def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """
    Dependency that requires authentication.
    Raises 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def user_has_owl_privilege(conn, user_id: int, privilege_name: str) -> bool:
    """
    Check if a user has a specific privilege via OWL role graph.

    Resolution path:
        user → yogi (instance_of) → yogi_role → has_privilege → privilege
    Roles inherit up the child_of chain, so yogi_admin inherits from
    yogi_internal which inherits from yogi (root).
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH RECURSIVE user_roles AS (
                -- Step 1: Find the yogi entity for this user_id
                SELECT r.related_owl_id AS role_id
                FROM owl yogi
                JOIN owl_relationships r ON r.owl_id = yogi.owl_id
                WHERE yogi.owl_type = 'yogi'
                  AND (yogi.metadata->>'user_id')::int = %s
                  AND r.relationship = 'instance_of'

                UNION

                -- Step 2: Walk up the role hierarchy via child_of
                SELECT r.related_owl_id
                FROM user_roles ur
                JOIN owl_relationships r ON r.owl_id = ur.role_id
                WHERE r.relationship = 'child_of'
            ),
            role_privileges AS (
                -- Step 3: Collect all privileges from all roles in the chain
                SELECT p.canonical_name
                FROM user_roles ur
                JOIN owl_relationships rel ON rel.owl_id = ur.role_id
                    AND rel.relationship = 'has_privilege'
                JOIN owl p ON p.owl_id = rel.related_owl_id
                    AND p.owl_type = 'privilege'
                    AND p.status = 'active'
            )
            SELECT EXISTS (
                SELECT 1 FROM role_privileges WHERE canonical_name = %s
            ) AS has_priv
        """, (user_id, privilege_name))
        return cur.fetchone()['has_priv']
