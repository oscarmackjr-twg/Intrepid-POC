"""Tests for authentication security — cookie-based token extraction."""
import pytest
from fastapi.testclient import TestClient
from auth.security import create_access_token
from api.main import app
from db.connection import get_db


@pytest.fixture
def client(test_db_session, override_get_db):
    """Test client with DB override."""
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers_admin(sample_admin_user):
    """Auth headers for admin user."""
    token = create_access_token({"sub": str(sample_admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestGetCurrentUserCookieFallback:
    """Test that get_current_user reads from HttpOnly cookie when no Authorization header."""

    def test_me_with_cookie_auth(self, client, sample_admin_user):
        """GET /api/auth/me succeeds when access_token cookie is set (no Authorization header)."""
        token = create_access_token({"sub": str(sample_admin_user.id), "role": sample_admin_user.role.value})
        cookie_value = f"Bearer {token}"
        response = client.get(
            "/api/auth/me",
            cookies={"access_token": cookie_value},
        )
        assert response.status_code == 200
        assert response.json()["username"] == sample_admin_user.username

    def test_me_without_auth_returns_401(self, client):
        """GET /api/auth/me without cookie or header returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_bearer_header_still_works(self, client, auth_headers_admin):
        """GET /api/auth/me still accepts Authorization header (backward compat for API clients)."""
        response = client.get("/api/auth/me", headers=auth_headers_admin)
        assert response.status_code == 200

    def test_cookie_without_bearer_prefix_returns_401(self, client, sample_admin_user):
        """Cookie value without 'Bearer ' prefix is rejected."""
        token = create_access_token({"sub": str(sample_admin_user.id)})
        response = client.get(
            "/api/auth/me",
            cookies={"access_token": token},  # missing "Bearer " prefix
        )
        assert response.status_code == 401

    def test_cookie_with_invalid_token_returns_401(self, client):
        """Cookie with a malformed token is rejected."""
        response = client.get(
            "/api/auth/me",
            cookies={"access_token": "Bearer not.a.real.token"},
        )
        assert response.status_code == 401
