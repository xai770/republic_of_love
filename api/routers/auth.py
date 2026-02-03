"""
Google OAuth authentication routes.

Flow:
1. User clicks "Login with Google" → GET /auth/google
2. Redirect to Google consent screen
3. Google redirects back → GET /auth/callback
4. We exchange code for tokens, get user info
5. Create/update user in database
6. Set session cookie
7. Redirect to dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
import httpx
import jwt
from datetime import datetime, timedelta
from urllib.parse import urlencode

from api.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    SECRET_KEY,
    SESSION_EXPIRE_HOURS,
    FRONTEND_URL,
    DEBUG,
)
from api.deps import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
def login_with_google():
    """
    Initiate Google OAuth flow.
    Redirects user to Google consent screen.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(code: str = None, error: str = None, conn=Depends(get_db)):
    """
    Handle Google OAuth callback.
    Exchange code for tokens, create/update user, set session.
    """
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error={error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
        )
    
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    
    tokens = token_response.json()
    access_token = tokens.get("access_token")
    
    # Get user info from Google
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    
    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    google_user = userinfo_response.json()
    google_id = google_user.get("id")
    email = google_user.get("email")
    display_name = google_user.get("name")
    avatar_url = google_user.get("picture")
    
    # Create or update user in database
    with conn.cursor() as cur:
        # Try to find existing user by google_id or email
        cur.execute("""
            SELECT user_id FROM users 
            WHERE google_id = %s OR email = %s
        """, (google_id, email))
        existing = cur.fetchone()
        
        if existing:
            # Update existing user
            cur.execute("""
                UPDATE users SET
                    google_id = %s,
                    display_name = %s,
                    avatar_url = %s,
                    last_login_at = NOW()
                WHERE user_id = %s
                RETURNING user_id
            """, (google_id, display_name, avatar_url, existing['user_id']))
            user_id = cur.fetchone()['user_id']
        else:
            # Create new user
            cur.execute("""
                INSERT INTO users (email, google_id, display_name, avatar_url, last_login_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING user_id
            """, (email, google_id, display_name, avatar_url))
            user_id = cur.fetchone()['user_id']
            
            # Try to link to existing profile with matching email
            cur.execute("""
                UPDATE profiles SET user_id = %s
                WHERE email = %s AND user_id IS NULL
            """, (user_id, email))
        
        conn.commit()
    
    # Create session token
    session_token = jwt.encode(
        {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
    
    # Redirect to dashboard with session cookie
    response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=False,  # Set True in production with HTTPS
        samesite="lax",
        max_age=SESSION_EXPIRE_HOURS * 3600,
    )
    return response


@router.get("/logout")
def logout():
    """
    Clear session cookie and redirect to home.
    """
    response = RedirectResponse(url=FRONTEND_URL)
    response.delete_cookie(key="session")
    return response


@router.get("/me")
def get_current_user_info(request: Request, conn=Depends(get_db)):
    """
    Get current authenticated user info.
    Returns 401 if not authenticated.
    """
    from api.deps import get_current_user
    user = get_current_user(request, conn)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return user


# DEBUG-only test login (remove in production)
if DEBUG:
    @router.get("/test-login/{user_id}")
    def test_login(user_id: int, conn=Depends(get_db)):
        """
        DEBUG ONLY: Log in as any user by ID.
        This allows testing without Google OAuth.
        """
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, email FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create session token
        token = jwt.encode(
            {
                "user_id": user['user_id'],
                "email": user['email'],
                "exp": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS),
            },
            SECRET_KEY,
            algorithm="HS256",
        )
        
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=SESSION_EXPIRE_HOURS * 3600,
        )
        return response
