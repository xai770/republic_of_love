"""
API endpoint smoke tests — verify routes respond and return expected shapes.

Uses FastAPI TestClient (no real server needed).
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the FastAPI app."""
    from api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data or isinstance(data, dict)


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


class TestAdminEndpoint:
    """Test admin panel loads."""

    def test_admin_console_exists(self, client):
        response = client.get("/admin/console")
        # Should return HTML page or redirect (may require auth too)
        assert response.status_code in (200, 302, 307, 401, 403)


class TestDocsEndpoint:
    """Test API docs are accessible."""

    def test_openapi_schema(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "info" in data
