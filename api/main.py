"""
talent.yoga API — FastAPI application.

Run with:
    uvicorn api.main:app --reload
"""
from pathlib import Path
from fastapi import FastAPI, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse

from api.config import FRONTEND_URL, DEBUG
from api.routers import health, auth, dashboard, profiles, postings, matches, visualization, notifications, ledger, admin, mira, interactions, messages, y2y
from api.deps import get_current_user, get_db
from api.i18n import (
    get_language_from_request, create_translator, get_all_translations,
    SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
)

# Paths
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Create FastAPI app
app = FastAPI(
    title="talent.yoga API",
    description="Job matching based on skills, not keywords",
    version="0.1.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
)

# Static files and templates
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")
else:
    templates = None

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(profiles.router, prefix="/api")
app.include_router(postings.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(ledger.router, prefix="/api")
app.include_router(mira.router, prefix="/api")
app.include_router(interactions.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(y2y.router, prefix="/api")
app.include_router(visualization.router)
app.include_router(admin.router)


# --- i18n Helper ---

def get_i18n_context(request: Request) -> dict:
    """Get i18n context for templates."""
    lang = get_language_from_request(request)
    return {
        "t": create_translator(lang),
        "lang": lang,
        "languages": SUPPORTED_LANGUAGES,
    }


# --- i18n API Endpoints ---

@app.get("/api/i18n/{lang}")
def get_translations(lang: str):
    """Get all translations for a language (for client-side JS)."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return JSONResponse(content=get_all_translations(lang))


@app.get("/api/i18n/set/{lang}")
def set_language(lang: str, response: Response, request: Request):
    """Set language preference via cookie and redirect back."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    # Get referer or default to home
    referer = request.headers.get("referer", "/")
    
    response = RedirectResponse(url=referer, status_code=302)
    response.set_cookie(
        key="lang",
        value=lang,
        max_age=365 * 24 * 60 * 60,  # 1 year
        httponly=False,  # Allow JS to read for client-side i18n
        samesite="lax"
    )
    return response


# --- Page Routes ---

@app.get("/")
def landing_page(request: Request, conn=Depends(get_db)):
    """Landing page — lobby for visitors, redirect to dashboard if authenticated."""
    if not templates:
        return {"name": "talent.yoga", "version": "0.1.0", "status": "running"}
    
    user = get_current_user(request, conn)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Show lobby for unauthenticated users
    return templates.TemplateResponse("lobby.html", {
        "request": request,
        **get_i18n_context(request)
    })


@app.get("/login")
def login_page(request: Request, conn=Depends(get_db)):
    """Login page — redirect to dashboard if already authenticated."""
    if not templates:
        return {"error": "Frontend not configured"}
    
    user = get_current_user(request, conn)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    error = request.query_params.get("error")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        **get_i18n_context(request)
    })


@app.get("/dashboard")
def dashboard_page(request: Request, conn=Depends(get_db)):
    """Dashboard — requires authentication."""
    if not templates:
        return {"error": "Frontend not configured"}
    
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        **get_i18n_context(request)
    })


@app.get("/market")
def market_page(request: Request):
    """Job market terrain visualization — public page."""
    if not templates:
        return {"error": "Frontend not configured"}
    
    return templates.TemplateResponse("market.html", {
        "request": request,
        **get_i18n_context(request)
    })


@app.get("/profile")
def profile_page(request: Request, conn=Depends(get_db)):
    """Profile editor page."""
    if not templates:
        return {"error": "Frontend not configured"}
    
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    # Get user's profile if exists
    profile = None
    with conn.cursor() as cur:
        cur.execute("""
            SELECT profile_id, full_name as display_name, email,
                   current_title as title, desired_locations[1] as location,
                   min_seniority, desired_roles, desired_locations,
                   expected_salary_min, expected_salary_max
            FROM profiles
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        if row:
            profile = dict(row)
    
    # Get notification consent data (P0.8)
    notification_email = user.get('notification_email')
    notification_consent_at = user.get('notification_consent_at')
    notification_preferences = user.get('notification_preferences') or {}
    notification_consent = notification_consent_at is not None
    
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user,
        "profile": profile,
        "notification_consent": notification_consent,
        "notification_email": notification_email,
        "notification_consent_at": notification_consent_at,
        "notification_preferences": notification_preferences,
        **get_i18n_context(request)
    })


@app.get("/matches")
def matches_page(request: Request, conn=Depends(get_db)):
    """Match dashboard page."""
    if not templates:
        return {"error": "Frontend not configured"}
    
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("matches.html", {
        "request": request,
        "user": user,
        **get_i18n_context(request)
    })


@app.get("/messages")
def messages_page(request: Request, conn=Depends(get_db)):
    """Messages inbox page."""
    if not templates:
        return {"error": "Frontend not configured"}
    
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("messages.html", {
        "request": request,
        "user": user,
        **get_i18n_context(request)
    })


@app.get("/report/{match_id}")
def report_page(match_id: int, request: Request, conn=Depends(get_db)):
    """Report viewer page for a specific match."""
    if not templates:
        return {"error": "Frontend not configured"}
    
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("report.html", {
        "request": request,
        "user": user,
        "match_id": match_id,
        **get_i18n_context(request)
    })


# --- Legal Pages (no auth required) ---

@app.get("/impressum")
def impressum_page(request: Request):
    """Legal notice (Impressum)."""
    if not templates:
        return {"error": "Frontend not configured"}
    return templates.TemplateResponse("impressum.html", {
        "request": request,
        **get_i18n_context(request)
    })


@app.get("/privacy")
def privacy_page(request: Request):
    """Privacy policy."""
    if not templates:
        return {"error": "Frontend not configured"}
    return templates.TemplateResponse("privacy.html", {
        "request": request,
        **get_i18n_context(request)
    })


@app.get("/terms")
def terms_page(request: Request):
    """Terms of service."""
    if not templates:
        return {"error": "Frontend not configured"}
    return templates.TemplateResponse("terms.html", {
        "request": request,
        **get_i18n_context(request)
    })


@app.get("/finances")
def finances_page(request: Request):
    """Public finances/ledger page."""
    if not templates:
        return {"error": "Frontend not configured"}
    return templates.TemplateResponse("finances.html", {
        "request": request,
        **get_i18n_context(request)
    })


@app.get("/lobby")
def lobby_page(request: Request, conn=Depends(get_db)):
    """Public lobby page — redirect to dashboard if authenticated."""
    if not templates:
        return {"name": "talent.yoga", "version": "0.1.0", "status": "running"}
    
    user = get_current_user(request, conn)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("lobby.html", {
        "request": request,
        **get_i18n_context(request)
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
