"""Tests for authentication routes."""
import pytest
from fastapi.testclient import TestClient
from db.models import User, SalesTeam, UserRole
from auth.security import create_access_token


class TestUserRegistration:
    """Test user registration."""
    
    def test_register_user_admin(self, client, auth_headers_admin, test_db_session, sample_sales_team):
        """Test admin can register users."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "TestPass123!",
                "full_name": "New User",
                "role": "analyst",
                "sales_team_id": None
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        assert response.json()["email"] == "newuser@test.com"
    
    def test_register_sales_team_user(self, client, auth_headers_admin, test_db_session, sample_sales_team):
        """Test registering sales team user with sales_team_id."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "sales@test.com",
                "username": "salesuser",
                "password": "TestPass123!",
                "full_name": "Sales User",
                "role": "sales_team",
                "sales_team_id": sample_sales_team.id
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        assert response.json()["sales_team_id"] == sample_sales_team.id
    
    def test_register_sales_team_without_id(self, client, auth_headers_admin, test_db_session):
        """Test registering sales team user without sales_team_id fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "sales@test.com",
                "username": "salesuser",
                "password": "TestPass123!",
                "full_name": "Sales User",
                "role": "sales_team",
                "sales_team_id": None
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 400
    
    def test_register_duplicate_email(self, client, auth_headers_admin, test_db_session, sample_admin_user):
        """Test registering with duplicate email fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": sample_admin_user.email,
                "username": "different",
                "password": "TestPass123!",
                "full_name": "Different User",
                "role": "analyst"
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 400
    
    def test_register_non_admin_forbidden(self, client, auth_headers_sales):
        """Test non-admin cannot register users."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@test.com",
                "username": "test",
                "password": "TestPass123!",
                "full_name": "Test User",
                "role": "analyst"
            },
            headers=auth_headers_sales
        )
        assert response.status_code == 403


class TestUserUpdate:
    """Test user update."""
    
    def test_update_user_admin(self, client, auth_headers_admin, test_db_session, sample_sales_team):
        """Test admin can update users."""
        # Create user to update
        user = User(
            email="update@test.com",
            username="update",
            hashed_password="hash",
            role=UserRole.ANALYST
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        response = client.put(
            f"/api/auth/users/{user.id}",
            json={
                "full_name": "Updated Name",
                "role": "sales_team",
                "sales_team_id": sample_sales_team.id
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"
        assert response.json()["role"] == "sales_team"
    
    def test_update_sales_team_assignment(self, client, auth_headers_admin, test_db_session, sample_sales_team):
        """Test updating sales team assignment."""
        user = User(
            email="update@test.com",
            username="update",
            hashed_password="hash",
            role=UserRole.ANALYST
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        response = client.put(
            f"/api/auth/users/{user.id}",
            json={
                "role": "sales_team",
                "sales_team_id": sample_sales_team.id
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        assert response.json()["sales_team_id"] == sample_sales_team.id
    
    def test_update_sales_team_without_id_fails(self, client, auth_headers_admin, test_db_session):
        """Test updating to sales_team without sales_team_id fails."""
        user = User(
            email="update@test.com",
            username="update",
            hashed_password="hash",
            role=UserRole.ANALYST
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        response = client.put(
            f"/api/auth/users/{user.id}",
            json={
                "role": "sales_team",
                "sales_team_id": None
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 400
    
    def test_update_own_role_forbidden(self, client, auth_headers_admin, test_db_session, sample_admin_user):
        """Test user cannot change own role."""
        response = client.put(
            f"/api/auth/users/{sample_admin_user.id}",
            json={
                "role": "sales_team"
            },
            headers=auth_headers_admin
        )
        assert response.status_code == 403


class TestUserList:
    """Test user listing."""
    
    def test_list_users_admin(self, client, auth_headers_admin, test_db_session):
        """Test admin can list users."""
        response = client.get("/api/auth/users", headers=auth_headers_admin)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_list_users_filter_by_role(self, client, auth_headers_admin, test_db_session):
        """Test filtering users by role."""
        response = client.get(
            "/api/auth/users",
            params={"role": "sales_team"},
            headers=auth_headers_admin
        )
        assert response.status_code == 200
        users = response.json()
        assert all(u["role"] == "sales_team" for u in users)
    
    def test_list_users_non_admin_forbidden(self, client, auth_headers_sales):
        """Test non-admin cannot list users."""
        response = client.get("/api/auth/users", headers=auth_headers_sales)
        assert response.status_code == 403


class TestCookieLogin:
    """Test HttpOnly cookie-based login (HARD-03)."""

    def test_login_sets_httponly_cookie(self, client, sample_admin_user):
        """Successful login sets an HttpOnly access_token cookie."""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "testpass"},
        )
        assert response.status_code == 200
        # Cookie must be present
        assert "access_token" in response.cookies
        # The Set-Cookie header must have HttpOnly flag
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie_header.lower()

    def test_login_response_has_no_access_token_in_body(self, client, sample_admin_user):
        """Login response body does NOT expose access_token (tokens are in the cookie only)."""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "testpass"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" not in body

    def test_login_response_body_contains_user_info(self, client, sample_admin_user):
        """Login response body contains user information."""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "testpass"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "user" in body
        assert body["user"]["username"] == "admin"

    def test_logout_clears_cookie(self, client, sample_admin_user):
        """POST /api/auth/logout clears the access_token cookie."""
        # First login to get a cookie
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "testpass"},
        )
        assert login_resp.status_code == 200
        # Now logout
        logout_resp = client.post("/api/auth/logout")
        assert logout_resp.status_code == 200
        # Cookie should be cleared (max-age=0 or expires in the past)
        set_cookie_header = logout_resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie_header
        # Either max-age=0 or expires past date signals deletion
        assert "max-age=0" in set_cookie_header.lower() or "expires" in set_cookie_header.lower()

    def test_cookie_samesite_strict(self, client, sample_admin_user):
        """Login cookie has SameSite=Strict attribute."""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "testpass"},
        )
        assert response.status_code == 200
        set_cookie_header = response.headers.get("set-cookie", "").lower()
        assert "samesite=strict" in set_cookie_header


class TestRateLimit:
    """Test login rate limiting (10 requests per minute per IP)."""

    def test_eleventh_login_returns_429(self, client):
        """11th login attempt within 1 minute returns HTTP 429 Too Many Requests."""
        for _ in range(10):
            client.post(
                "/api/auth/login",
                data={"username": "wrong", "password": "wrong"},
            )
        response = client.post(
            "/api/auth/login",
            data={"username": "wrong", "password": "wrong"},
        )
        assert response.status_code == 429


class TestPasswordPolicy:
    """Test password policy enforcement on register endpoint (HARD-02).

    Tests validate_password_strength validator added to UserCreate in auth/routes.py.
    """

    def test_password_too_short_returns_422(self, client, auth_headers_admin, test_db_session):
        """Password shorter than 12 chars must return 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "short@test.com",
                "username": "shortpwuser",
                "password": "short1A",
                "full_name": "Short Password",
                "role": "analyst",
            },
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    def test_password_no_uppercase_returns_422(self, client, auth_headers_admin, test_db_session):
        """Password with no uppercase letter must return 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "noup@test.com",
                "username": "noupperuser",
                "password": "alllowercase123",
                "full_name": "No Uppercase",
                "role": "analyst",
            },
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    def test_password_no_lowercase_returns_422(self, client, auth_headers_admin, test_db_session):
        """Password with no lowercase letter must return 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "nolo@test.com",
                "username": "noloweruser",
                "password": "ALLUPPERCASE123",
                "full_name": "No Lowercase",
                "role": "analyst",
            },
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    def test_password_no_digit_returns_422(self, client, auth_headers_admin, test_db_session):
        """Password with no digit must return 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "nodig@test.com",
                "username": "nodigituser",
                "password": "NoDigitsHereAtAll",
                "full_name": "No Digit",
                "role": "analyst",
            },
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    def test_valid_password_succeeds(self, client, auth_headers_admin, test_db_session):
        """Password meeting all requirements must succeed (200)."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "validpw@test.com",
                "username": "validpassuser",
                "password": "ValidPass123!",
                "full_name": "Valid Password",
                "role": "analyst",
            },
            headers=auth_headers_admin,
        )
        assert response.status_code == 200


class TestLoginAuditLog:
    """Login events must be persisted to audit_log table (HARD-06)."""

    def test_successful_login_writes_audit_row(self, client, sample_admin_user, test_db_session):
        """Successful login writes a row to audit_log with event_type='login' outcome='success'."""
        from db.models import AuditLog
        client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "testpass"},
        )
        rows = test_db_session.query(AuditLog).filter_by(event_type="login").all()
        assert len(rows) == 1
        assert rows[0].outcome == "success"
        assert rows[0].user_id == sample_admin_user.id

    def test_failed_login_writes_audit_row(self, client, sample_admin_user, test_db_session):
        """Failed login (wrong password) writes a row to audit_log with event_type='login_failed' outcome='failure'."""
        from db.models import AuditLog
        client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        rows = test_db_session.query(AuditLog).filter_by(event_type="login_failed").all()
        assert len(rows) == 1
        assert rows[0].outcome == "failure"
        assert rows[0].user_id == sample_admin_user.id

    def test_unknown_user_login_does_not_write_audit_row(self, client, test_db_session):
        """Login attempt for non-existent username does NOT write an audit row."""
        from db.models import AuditLog
        client.post(
            "/api/auth/login",
            data={"username": "nobody", "password": "anything"},
        )
        rows = test_db_session.query(AuditLog).all()
        assert len(rows) == 0
