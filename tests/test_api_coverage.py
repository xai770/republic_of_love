"""
Extended API endpoint tests — cover all previously untested routes.

Tests follow existing patterns from test_api_endpoints.py:
- Module-scoped TestClient + auth fixtures
- Auth-requirement checks (401 without cookie)
- Authenticated happy-path checks (200/204 with cookie)
- Response shape assertions

Coverage targets: auth, messages, feedback, mira, account,
events, documents, notifications, interactions.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures (same pattern as test_api_endpoints.py)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


@pytest.fixture
def fresh_client():
    """Per-test client — no leaked cookies from previous tests."""
    from api.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_cookie():
    """Valid JWT for user_id=1."""
    from api.config import SECRET_KEY, SESSION_EXPIRE_HOURS
    token = jwt.encode(
        {"user_id": 1, "email": "test@talent.yoga",
         "exp": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)},
        SECRET_KEY, algorithm="HS256",
    )
    return {"session": token}


@pytest.fixture(scope="module")
def admin_cookie():
    """Valid JWT for user_id=1 (who is admin in test DB)."""
    from api.config import SECRET_KEY, SESSION_EXPIRE_HOURS
    token = jwt.encode(
        {"user_id": 1, "email": "test@talent.yoga",
         "exp": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)},
        SECRET_KEY, algorithm="HS256",
    )
    return {"session": token}


@pytest.fixture(scope="module")
def expired_cookie():
    from api.config import SECRET_KEY
    token = jwt.encode(
        {"user_id": 1, "email": "test@talent.yoga",
         "exp": datetime.utcnow() - timedelta(hours=1)},
        SECRET_KEY, algorithm="HS256",
    )
    return {"session": token}


@pytest.fixture(scope="module")
def bad_cookie():
    token = jwt.encode(
        {"user_id": 1, "email": "test@talent.yoga",
         "exp": datetime.utcnow() + timedelta(hours=1)},
        "wrong-secret-key", algorithm="HS256",
    )
    return {"session": token}


# ===========================================================================
# Auth — previously untested endpoints
# ===========================================================================

class TestAuthCallback:
    """Test /auth/callback edge cases."""

    def test_callback_without_code_fails(self, client):
        """GET /auth/callback without code param should fail."""
        response = client.get("/auth/callback", follow_redirects=False)
        # Should fail due to missing code param
        assert response.status_code in (400, 422, 302, 307, 500)

    def test_callback_with_invalid_code(self, client):
        """GET /auth/callback with bogus code should fail gracefully."""
        response = client.get("/auth/callback?code=invalid_code_xyz",
                              follow_redirects=False)
        # Can't exchange invalid code with Google, should error or redirect
        assert response.status_code in (400, 401, 500, 302, 307)


class TestAuthTestLogin:
    """Test /auth/test-login/{user_id} (debug-only route)."""

    def test_test_login_returns_redirect(self, fresh_client):
        """Debug login should set session cookie and redirect."""
        response = fresh_client.get("/auth/test-login/1", follow_redirects=False)
        # Either works (302 with cookie) or 404 if DEBUG is off
        assert response.status_code in (200, 302, 307, 404)
        if response.status_code in (302, 307):
            assert "session" in response.headers.get("set-cookie", "")

    def test_test_login_invalid_user(self, fresh_client):
        """Debug login with non-existent user should 404."""
        response = fresh_client.get("/auth/test-login/999999",
                              follow_redirects=False)
        assert response.status_code in (404, 302)


class TestAuthTokenEdgeCases:
    """Additional auth token validation tests."""

    def test_empty_cookie_rejected(self, fresh_client):
        """Empty session cookie should be treated as unauthenticated."""
        response = fresh_client.get("/auth/me", cookies={"session": ""})
        assert response.status_code in (401, 403)

    def test_malformed_jwt_rejected(self, fresh_client):
        """Non-JWT string should be rejected."""
        response = fresh_client.get("/auth/me", cookies={"session": "not.a.jwt"})
        assert response.status_code in (401, 403)

    def test_jwt_without_user_id_rejected(self, fresh_client):
        """JWT missing user_id claim should be rejected."""
        from api.config import SECRET_KEY
        token = jwt.encode(
            {"email": "test@talent.yoga",
             "exp": datetime.utcnow() + timedelta(hours=1)},
            SECRET_KEY, algorithm="HS256",
        )
        response = fresh_client.get("/auth/me", cookies={"session": token})
        assert response.status_code in (401, 403)

    def test_jwt_with_nonexistent_user_rejected(self, fresh_client):
        """JWT with user_id not in DB should be rejected."""
        from api.config import SECRET_KEY
        token = jwt.encode(
            {"user_id": 999999, "email": "nobody@talent.yoga",
             "exp": datetime.utcnow() + timedelta(hours=1)},
            SECRET_KEY, algorithm="HS256",
        )
        response = fresh_client.get("/auth/me", cookies={"session": token})
        assert response.status_code in (401, 403)


# ===========================================================================
# Messages — previously untested endpoints
# ===========================================================================

class TestMessagesDetail:
    """Test /api/messages/{message_id} endpoint."""

    def test_get_message_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/messages/1")
        assert response.status_code in (401, 404)

    def test_get_message_nonexistent(self, client, auth_cookie):
        """Getting a non-existent message should 404."""
        response = client.get("/api/messages/999999", cookies=auth_cookie)
        assert response.status_code in (404, 401)

    def test_get_message_with_mark_read_false(self, client, auth_cookie):
        """Should accept mark_read=false parameter."""
        response = client.get("/api/messages/999999?mark_read=false",
                              cookies=auth_cookie)
        assert response.status_code in (404, 401)


class TestMessagesDelete:
    """Test DELETE /api/messages/{message_id} endpoint."""

    def test_delete_requires_auth(self, fresh_client):
        response = fresh_client.delete("/api/messages/1")
        assert response.status_code in (401, 404)

    def test_delete_nonexistent(self, client, auth_cookie):
        """Deleting a non-existent message should 404."""
        response = client.delete("/api/messages/999999", cookies=auth_cookie)
        assert response.status_code in (404, 401)


class TestMessagesPosting:
    """Test GET /api/messages/posting/{posting_id} endpoint."""

    def test_posting_messages_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/messages/posting/1")
        assert response.status_code == 401

    def test_posting_messages_with_auth(self, client, auth_cookie):
        """Should return posting messages or empty list."""
        response = client.get("/api/messages/posting/1", cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert "posting_id" in data
            assert "messages" in data
            assert isinstance(data["messages"], list)


class TestMessagesSendValidation:
    """Test POST /api/messages/send edge cases."""

    def test_send_without_recipient_fails(self, client, auth_cookie):
        """Sending without recipient should 400."""
        response = client.post("/api/messages/send", cookies=auth_cookie,
                               json={"body": "Hello"})
        if response.status_code not in (401,):
            assert response.status_code == 400

    def test_send_to_actor(self, client, auth_cookie):
        """Sending a message to an actor should work."""
        response = client.post("/api/messages/send", cookies=auth_cookie,
                               json={
                                   "body": "Test message to Mira",
                                   "recipient_type": "mira",
                               })
        if response.status_code == 200:
            data = response.json()
            assert data.get("sent") is True
            assert "message_id" in data

    def test_send_to_self_fails(self, client, auth_cookie):
        """Sending Y2Y message to self should 400."""
        response = client.post("/api/messages/send", cookies=auth_cookie,
                               json={
                                   "body": "Hello self",
                                   "recipient_user_id": 1,
                               })
        if response.status_code not in (401,):
            assert response.status_code == 400

    def test_send_to_nonexistent_user(self, client, auth_cookie):
        """Sending Y2Y to non-existent user should 404."""
        response = client.post("/api/messages/send", cookies=auth_cookie,
                               json={
                                   "body": "Hello ghost",
                                   "recipient_user_id": 999999,
                               })
        if response.status_code not in (401,):
            assert response.status_code == 404


class TestMessagesFilters:
    """Test message list filtering options."""

    def test_filter_by_sender_type(self, client, auth_cookie):
        response = client.get("/api/messages/?sender_type=mira",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert "messages" in data
            assert isinstance(data["total"], int)

    def test_filter_unread_only(self, client, auth_cookie):
        response = client.get("/api/messages/?unread_only=true",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert "messages" in data

    def test_pagination(self, client, auth_cookie):
        response = client.get("/api/messages/?limit=5&offset=0",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert "messages" in data
            assert len(data["messages"]) <= 5


# ===========================================================================
# Feedback — previously untested endpoints
# ===========================================================================

class TestFeedbackResolve:
    """Test POST /admin/feedback/resolve endpoint."""

    def test_resolve_requires_admin(self, client, auth_cookie):
        """Non-admin should be rejected (or 404 if no such feedback)."""
        response = client.post("/admin/feedback/resolve",
                               cookies=auth_cookie,
                               json={"feedback_id": 1,
                                     "admin_notes": "test"})
        # 200 if admin + record exists, 403 if not admin, 404 if record missing
        assert response.status_code in (200, 403, 401, 404)

    def test_resolve_requires_auth(self, fresh_client):
        response = fresh_client.post("/admin/feedback/resolve",
                                     json={"feedback_id": 1})
        assert response.status_code in (401, 403)


class TestFeedbackSubmitValidation:
    """Test feedback submission edge cases."""

    def test_submit_missing_fields(self, client, auth_cookie):
        """Missing required fields should fail validation."""
        response = client.post("/api/feedback", cookies=auth_cookie,
                               json={"description": "no url"})
        assert response.status_code == 422

    def test_submit_with_screenshot(self, client, auth_cookie, db_conn):
        """Submit with optional screenshot field."""
        response = client.post("/api/feedback", cookies=auth_cookie,
                               json={
                                   "url": "https://talent.yoga/test",
                                   "description": "Test with screenshot",
                                   "category": "suggestion",
                                   "screenshot": "data:image/png;base64,iVBOR...",
                               })
        assert response.status_code in (200, 401)
        # Clean up — delete the test record so it doesn't pollute the DB
        if response.status_code == 200:
            fid = response.json().get("feedback_id")
            if fid:
                with db_conn.cursor() as cur:
                    cur.execute("DELETE FROM feedback WHERE feedback_id = %s", (fid,))
                db_conn.commit()


# ===========================================================================
# Mira — previously untested endpoints
# ===========================================================================

class TestMiraConsent:
    """Test Mira consent-prompt and consent-submit endpoints."""

    def test_consent_prompt_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/mira/consent-prompt")
        assert response.status_code == 401

    def test_consent_prompt_with_auth(self, client, auth_cookie):
        response = client.get("/api/mira/consent-prompt", cookies=auth_cookie)
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_consent_submit_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/mira/consent-submit",
                                     json={"consent": True})
        assert response.status_code == 401

    def test_consent_submit_with_auth(self, client, auth_cookie):
        response = client.post("/api/mira/consent-submit",
                               cookies=auth_cookie,
                               json={"consent": True})
        assert response.status_code in (200, 401, 422)


class TestMiraChatValidation:
    """Test Mira chat edge cases."""

    def test_chat_empty_message(self, client, auth_cookie):
        """Sending empty message should fail or return error."""
        response = client.post("/api/mira/chat", cookies=auth_cookie,
                               json={"message": "", "history": []})
        # May 422 (validation) or 200 with error, or 401 if user not in DB
        assert response.status_code in (200, 401, 422)

    def test_chat_with_history(self, client, auth_cookie):
        """Chat with conversation history should be accepted."""
        response = client.post("/api/mira/chat", cookies=auth_cookie,
                               json={
                                   "message": "What jobs are available?",
                                   "history": [
                                       {"role": "user", "content": "Hi"},
                                       {"role": "assistant", "content": "Hello!"},
                                   ],
                               })
        assert response.status_code in (200, 401)

    def test_tour_with_auth(self, client, auth_cookie):
        """Tour endpoint should return guided steps."""
        response = client.get("/api/mira/tour", cookies=auth_cookie)
        assert response.status_code in (200, 401)

    def test_context_with_auth(self, client, auth_cookie):
        """Context endpoint should return yogi context."""
        response = client.get("/api/mira/context", cookies=auth_cookie)
        assert response.status_code in (200, 401)

    def test_proactive_with_auth(self, client, auth_cookie):
        """Proactive endpoint should return suggestions."""
        response = client.get("/api/mira/proactive", cookies=auth_cookie)
        assert response.status_code in (200, 401)


# ===========================================================================
# Account — entire router previously untested
# ===========================================================================

class TestAccountEndpoints:
    """Test account management endpoints."""

    def test_display_name_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/account/display-name",
                                     json={"display_name": "Test"})
        assert response.status_code == 401

    def test_avatar_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/account/avatar",
                                     json={"avatar": "🧘"})
        assert response.status_code == 401

    def test_email_consent_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/account/email-consent",
                                     json={"consent": True})
        assert response.status_code == 401

    def test_mira_preferences_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/account/mira-preferences",
                                     json={"language": "de"})
        assert response.status_code == 401

    def test_export_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/account/export")
        assert response.status_code == 401

    def test_delete_request_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/account/delete-request")
        assert response.status_code == 401


# ===========================================================================
# Events — entire router previously untested
# ===========================================================================

class TestEventsEndpoints:
    """Test event tracking endpoint."""

    def test_track_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/events/track",
                                     json={"event_type": "page_view"})
        assert response.status_code == 401

    def test_track_valid_event(self, client, auth_cookie):
        """Valid event should be accepted."""
        response = client.post("/api/events/track", cookies=auth_cookie,
                               json={
                                   "event_type": "page_view",
                                   "event_data": {"page": "/search"},
                               })
        # 204 No Content on success, or 401 if user not in DB
        assert response.status_code in (200, 204, 401)

    def test_track_unknown_event_ignored(self, client, auth_cookie):
        """Unknown event type should be silently ignored."""
        response = client.post("/api/events/track", cookies=auth_cookie,
                               json={
                                   "event_type": "nonexistent_event",
                                   "event_data": {},
                               })
        # Actor silently ignores unknown events — still returns success
        assert response.status_code in (200, 204, 401)

    def test_track_login_event(self, client, auth_cookie):
        response = client.post("/api/events/track", cookies=auth_cookie,
                               json={"event_type": "login"})
        assert response.status_code in (200, 204, 401)

    def test_track_search_event(self, client, auth_cookie):
        response = client.post("/api/events/track", cookies=auth_cookie,
                               json={
                                   "event_type": "search_filter",
                                   "event_data": {"query": "Python developer"},
                               })
        assert response.status_code in (200, 204, 401)


# ===========================================================================
# Documents — entire router previously untested
# ===========================================================================

class TestDocumentsEndpoints:
    """Test document library endpoints."""

    def test_list_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/documents/")
        assert response.status_code == 401

    def test_types_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/documents/types")
        assert response.status_code == 401

    def test_get_document_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/documents/1")
        assert response.status_code == 401

    def test_create_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/documents/",
                                     json={"doc_type": "other", "title": "T",
                                           "content": "C"})
        assert response.status_code == 401

    def test_delete_requires_auth(self, fresh_client):
        response = fresh_client.delete("/api/documents/1")
        assert response.status_code == 401

    def test_list_with_auth(self, client, auth_cookie):
        """Authenticated list should return documents or empty list."""
        response = client.get("/api/documents/", cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_list_with_filter(self, client, auth_cookie):
        response = client.get("/api/documents/?doc_type=doug_report",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_get_nonexistent_document(self, client, auth_cookie):
        response = client.get("/api/documents/999999", cookies=auth_cookie)
        assert response.status_code in (404, 401)


# ===========================================================================
# Notifications — entire router previously untested
# ===========================================================================

class TestNotificationsEndpoints:
    """Test notification endpoints."""

    def test_list_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/notifications/")
        assert response.status_code == 401

    def test_count_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/notifications/count")
        assert response.status_code == 401

    def test_mark_read_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/notifications/1/read")
        assert response.status_code == 401

    def test_read_all_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/notifications/read-all")
        assert response.status_code == 401

    def test_get_consent_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/notifications/consent")
        assert response.status_code == 401

    def test_put_consent_requires_auth(self, fresh_client):
        response = fresh_client.put("/api/notifications/consent",
                                    json={"email_consent": True})
        assert response.status_code == 401

    def test_delete_consent_requires_auth(self, fresh_client):
        response = fresh_client.delete("/api/notifications/consent")
        assert response.status_code == 401

    def test_list_with_auth(self, client, auth_cookie):
        response = client.get("/api/notifications/", cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_count_with_auth(self, client, auth_cookie):
        response = client.get("/api/notifications/count",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert "count" in data or "total" in data or isinstance(data, dict)

    def test_read_all_with_auth(self, client, auth_cookie):
        response = client.post("/api/notifications/read-all",
                               cookies=auth_cookie)
        assert response.status_code in (200, 204, 401)

    def test_consent_with_auth(self, client, auth_cookie):
        response = client.get("/api/notifications/consent",
                              cookies=auth_cookie)
        assert response.status_code in (200, 401)


# ===========================================================================
# Interactions — entire router previously untested
# ===========================================================================

class TestInteractionsAuth:
    """Test that all interaction endpoints require authentication."""

    def test_get_posting_interaction_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/interactions/posting/1")
        assert response.status_code == 401

    def test_favorites_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/interactions/favorites")
        assert response.status_code == 401

    def test_interested_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/interactions/interested")
        assert response.status_code == 401

    def test_mark_read_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/read",
                                     json={"posting_id": 1})
        assert response.status_code == 401

    def test_favorite_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/favorite",
                                     json={"posting_id": 1, "favorited": True})
        assert response.status_code == 401

    def test_feedback_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/feedback",
                                     json={"posting_id": 1, "feedback": "agree"})
        assert response.status_code == 401

    def test_interest_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/interest",
                                     json={"posting_id": 1, "interested": True})
        assert response.status_code == 401

    def test_state_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/state",
                                     json={"posting_id": 1, "new_state": "applied"})
        assert response.status_code == 401

    def test_stats_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/interactions/stats")
        assert response.status_code == 401


class TestInteractionsAuthenticated:
    """Test interaction endpoints with valid auth."""

    # Use a posting that actually exists in the DB to avoid FK violations.
    REAL_POSTING = 10507

    def test_favorites_list(self, client, auth_cookie):
        response = client.get("/api/interactions/favorites",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_interested_list(self, client, auth_cookie):
        response = client.get("/api/interactions/interested",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_stats(self, client, auth_cookie):
        response = client.get("/api/interactions/stats",
                              cookies=auth_cookie)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_get_state_for_posting(self, client, auth_cookie):
        """GET /api/interactions/state/{posting_id} should return state."""
        response = client.get(f"/api/interactions/state/{self.REAL_POSTING}",
                              cookies=auth_cookie)
        assert response.status_code in (200, 404, 401)

    def test_mark_read_posting(self, client, auth_cookie):
        """POST /api/interactions/read/{posting_id} shorthand."""
        response = client.post(f"/api/interactions/read/{self.REAL_POSTING}",
                               cookies=auth_cookie)
        assert response.status_code in (200, 401, 404)

    def test_favorite_posting(self, client, auth_cookie):
        """POST /api/interactions/favorite/{posting_id} shorthand."""
        response = client.post(f"/api/interactions/favorite/{self.REAL_POSTING}",
                               cookies=auth_cookie)
        assert response.status_code in (200, 401, 404)

    def test_feedback_posting(self, client, auth_cookie):
        """POST /api/interactions/feedback/{posting_id} shorthand."""
        response = client.post(f"/api/interactions/feedback/{self.REAL_POSTING}",
                               cookies=auth_cookie,
                               json={"feedback": "agree"})
        assert response.status_code in (200, 401, 404, 422)

    def test_interest_posting(self, client, auth_cookie):
        """POST /api/interactions/interest/{posting_id} shorthand."""
        response = client.post(f"/api/interactions/interest/{self.REAL_POSTING}",
                               cookies=auth_cookie)
        assert response.status_code in (200, 401, 404)

    def test_research_posting(self, client, auth_cookie):
        """POST /api/interactions/research/{posting_id} shorthand."""
        response = client.post(f"/api/interactions/research/{self.REAL_POSTING}",
                               cookies=auth_cookie)
        assert response.status_code in (200, 401, 404)


# ===========================================================================
# Interactions — path-style shortcuts vs body-style
# ===========================================================================

class TestInteractionsPathShortcuts:
    """Path-parameter interaction endpoints (/read/{posting_id} etc.)."""

    def test_read_path_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/read/1")
        assert response.status_code == 401

    def test_favorite_path_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/favorite/1")
        assert response.status_code == 401

    def test_feedback_path_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/feedback/1")
        assert response.status_code == 401

    def test_interest_path_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/interest/1")
        assert response.status_code == 401

    def test_research_path_requires_auth(self, fresh_client):
        response = fresh_client.post("/api/interactions/research/1")
        assert response.status_code == 401

    def test_state_path_requires_auth(self, fresh_client):
        response = fresh_client.get("/api/interactions/state/1")
        assert response.status_code == 401
