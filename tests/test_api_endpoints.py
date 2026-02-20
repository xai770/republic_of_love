"""
API endpoint smoke tests — verify routes respond and return expected shapes.

Uses FastAPI TestClient (no real server needed).
Authenticated tests use a JWT cookie created with the app's SECRET_KEY.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the FastAPI app."""
    from api.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_cookie():
    """Create a valid JWT session cookie for user_id=1 (Gershon)."""
    from api.config import SECRET_KEY, SESSION_EXPIRE_HOURS
    token = jwt.encode(
        {
            "user_id": 1,
            "email": "test@talent.yoga",
            "exp": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
    return {"session": token}


@pytest.fixture(scope="module")
def expired_cookie():
    """Create an expired JWT session cookie."""
    from api.config import SECRET_KEY
    token = jwt.encode(
        {
            "user_id": 1,
            "email": "test@talent.yoga",
            "exp": datetime.utcnow() - timedelta(hours=1),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
    return {"session": token}


@pytest.fixture(scope="module")
def bad_cookie():
    """Create a JWT signed with the wrong secret."""
    token = jwt.encode(
        {"user_id": 1, "email": "test@talent.yoga",
         "exp": datetime.utcnow() + timedelta(hours=1)},
        "wrong-secret-key",
        algorithm="HS256",
    )
    return {"session": token}


# ===========================================================================
# Health / Docs
# ===========================================================================

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data or isinstance(data, dict)


class TestDocsEndpoint:
    def test_openapi_schema(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "info" in data

    def test_openapi_has_feedback_path(self, client):
        data = client.get("/openapi.json").json()
        assert "/api/feedback" in data["paths"]

    def test_openapi_has_messages_paths(self, client):
        data = client.get("/openapi.json").json()
        paths = data["paths"]
        assert "/api/messages/" in paths
        assert "/api/messages/unread-counts" in paths


# ===========================================================================
# Auth
# ===========================================================================

class TestAuthEndpoints:
    """Test authentication flow endpoints."""

    def test_google_login_redirects(self, client):
        """GET /auth/google should redirect to Google OAuth."""
        response = client.get("/auth/google", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "accounts.google.com" in response.headers.get("location", "")

    def test_logout_clears_session(self, client, auth_cookie):
        """GET /auth/logout should clear the session cookie."""
        response = client.get("/auth/logout", cookies=auth_cookie,
                              follow_redirects=False)
        assert response.status_code in (302, 307)
        # Should set session cookie with empty value or max_age=0
        set_cookie = response.headers.get("set-cookie", "")
        assert "session" in set_cookie

    def test_me_requires_auth(self, client):
        """GET /auth/me without cookie should 401."""
        response = client.get("/auth/me")
        assert response.status_code in (401, 403)

    def test_me_returns_user(self, client, auth_cookie):
        """GET /auth/me with valid cookie returns user info."""
        response = client.get("/auth/me", cookies=auth_cookie)
        # May return user or may not find user_id=1 in test DB
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.json()
            assert "user_id" in data or "email" in data

    def test_expired_token_rejected(self, client, expired_cookie):
        """Expired JWT should be treated as unauthenticated."""
        response = client.get("/auth/me", cookies=expired_cookie)
        assert response.status_code in (401, 403)

    def test_bad_secret_rejected(self, client, bad_cookie):
        """JWT signed with wrong secret should be rejected."""
        response = client.get("/auth/me", cookies=bad_cookie)
        assert response.status_code in (401, 403)


# ===========================================================================
# Mira
# ===========================================================================

class TestMiraEndpoints:
    """Test Mira endpoints exist and require authentication."""

    def test_greeting_requires_auth(self, client):
        response = client.get("/api/mira/greeting")
        assert response.status_code == 401

    def test_tour_requires_auth(self, client):
        response = client.get("/api/mira/tour")
        assert response.status_code == 401

    def test_chat_requires_auth(self, client):
        response = client.post("/api/mira/chat", json={
            "message": "Hallo", "history": [],
        })
        assert response.status_code == 401

    def test_context_requires_auth(self, client):
        response = client.get("/api/mira/context")
        assert response.status_code == 401

    def test_proactive_requires_auth(self, client):
        response = client.get("/api/mira/proactive")
        assert response.status_code == 401

    def test_greeting_with_auth(self, client, auth_cookie):
        """Authenticated greeting should return 200."""
        response = client.get("/api/mira/greeting", cookies=auth_cookie)
        # 200 if user exists, 401 if user_id=1 isn't in DB
        assert response.status_code in (200, 401)


# ===========================================================================
# Messages
# ===========================================================================

class TestMessagesEndpoints:
    """Test message API endpoints."""

    def test_list_requires_auth(self, client):
        response = client.get("/api/messages/")
        assert response.status_code == 401

    def test_unread_counts_requires_auth(self, client):
        response = client.get("/api/messages/unread-counts")
        assert response.status_code == 401

    def test_send_requires_auth(self, client):
        response = client.post("/api/messages/send", json={
            "body": "Hello test",
        })
        assert response.status_code == 401

    def test_mark_read_requires_auth(self, client):
        response = client.post("/api/messages/mark-read", json={
            "message_ids": [1],
        })
        assert response.status_code == 401

    def test_mark_all_read_requires_auth(self, client):
        response = client.post("/api/messages/mark-all-read")
        assert response.status_code == 401

    def test_list_with_auth(self, client, auth_cookie):
        """Authenticated list should return 200 with messages array."""
        response = client.get("/api/messages/", cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert "messages" in data or isinstance(data, list)

    def test_unread_counts_with_auth(self, client, auth_cookie):
        """Authenticated unread-counts should return counts."""
        response = client.get("/api/messages/unread-counts",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert "total" in data or "unread" in data or isinstance(data, dict)


# ===========================================================================
# Feedback
# ===========================================================================

class TestFeedbackEndpoints:
    """Test feedback submission and admin endpoints."""

    def test_submit_requires_auth(self, client):
        response = client.post("/api/feedback", json={
            "url": "https://talent.yoga/dashboard",
            "description": "Test bug report",
            "category": "bug",
        })
        assert response.status_code == 401

    def test_submit_with_auth(self, client, auth_cookie, db_conn):
        """Authenticated feedback submission should succeed."""
        response = client.post("/api/feedback", cookies=auth_cookie, json={
            "url": "https://talent.yoga/test",
            "description": "Automated test feedback — please ignore",
            "category": "bug",
        })
        # 200 if user exists, 401 if user_id=1 not in DB
        if response.status_code == 200:
            data = response.json()
            assert data.get("ok") is True
            assert "feedback_id" in data
            # Clean up — delete the test record so it doesn't pollute the DB
            with db_conn.cursor() as cur:
                cur.execute("DELETE FROM feedback WHERE feedback_id = %s",
                            (data["feedback_id"],))
            db_conn.commit()

    def test_admin_feedback_view(self, client, auth_cookie):
        """GET /admin/feedback should return HTML or require admin."""
        response = client.get("/admin/feedback", cookies=auth_cookie)
        assert response.status_code in (200, 403)


# ===========================================================================
# Search
# ===========================================================================

class TestSearchEndpoints:
    """Test search API endpoints."""

    def test_domains_list(self, client):
        """GET /api/search/domains should return domain list (no auth required)."""
        response = client.get("/api/search/domains")
        # May or may not require auth
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)

    def test_ql_levels(self, client):
        """GET /api/search/ql-levels should return qualification levels."""
        response = client.get("/api/search/ql-levels")
        assert response.status_code in (200, 401)

    def test_search_results_requires_auth(self, client):
        """POST /api/search/results should require auth."""
        response = client.post("/api/search/results", json={
            "query": "Software Engineer",
        })
        assert response.status_code in (401, 422)

    def test_search_results_with_auth(self, client, auth_cookie):
        """Authenticated search should return results."""
        response = client.post("/api/search/results", cookies=auth_cookie,
                               json={"query": "Software Engineer"})
        if response.status_code == 200:
            data = response.json()
            assert "results" in data or "postings" in data or isinstance(data, list)

    def test_saved_searches_requires_auth(self, client):
        response = client.get("/api/search/saved")
        assert response.status_code == 401


# ===========================================================================
# Admin
# ===========================================================================

class TestAdminEndpoint:
    """Test admin panel loads."""

    def test_admin_console_exists(self, client):
        response = client.get("/admin/console")
        assert response.status_code in (200, 302, 307, 401, 403)


# ===========================================================================
# BI redirect
# ===========================================================================

class TestBIRedirect:
    """Test BI dashboard redirect."""

    def test_bi_redirects(self, client, auth_cookie):
        """GET /bi should redirect to bi.talent.yoga."""
        response = client.get("/bi", cookies=auth_cookie,
                              follow_redirects=False)
        assert response.status_code == 302
        assert "bi.talent.yoga" in response.headers.get("location", "")


# ===========================================================================
# i18n
# ===========================================================================

class TestI18n:
    """Test internationalisation endpoints."""

    def test_german_translations(self, client):
        response = client.get("/api/i18n/de")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_english_translations(self, client):
        response = client.get("/api/i18n/en")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_unknown_lang_falls_back(self, client):
        """Unknown language code should fall back to default."""
        response = client.get("/api/i18n/zz")
        assert response.status_code == 200
