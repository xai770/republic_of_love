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
                       notification_email, notification_consent_at, notification_preferences
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
