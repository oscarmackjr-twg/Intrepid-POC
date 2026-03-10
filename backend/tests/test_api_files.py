"""Tests for file API error sanitization (HARD-04).

RED phase: these tests verify behaviors that do not yet exist.
- Correlation IDs in error responses
- No raw exception text leaked to callers
"""
import re
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from auth.security import create_access_token, get_password_hash
from db.connection import Base, get_db
from db.models import User, UserRole


@pytest.fixture
def db_engine():
    """Fresh in-memory SQLite engine for each test function."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """DB session bound to fresh engine."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user(db_session):
    """Create a fresh admin user in the test DB."""
    user = User(
        email="files_admin@test.com",
        username="files_admin",
        hashed_password=get_password_hash("testpass"),
        full_name="Files Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session):
    """Test client with DB override."""
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(admin_user):
    """Auth headers for admin user."""
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestFileApiErrorSanitization:
    """Test that file API errors do not leak raw exception text."""

    def test_list_files_error_returns_generic_message(self, client, auth_headers):
        """GET /api/files/list when storage raises must NOT return raw exception in detail."""
        with patch("api.files.get_storage_backend") as mock_storage_factory:
            mock_backend = MagicMock()
            mock_backend.list_files.side_effect = RuntimeError("secret internal path: /etc/passwd")
            mock_storage_factory.return_value = mock_backend

            response = client.get("/api/files/list", headers=auth_headers)

        assert response.status_code == 500
        detail = response.json().get("detail", "")
        # Must NOT contain the raw exception string
        assert "secret internal path" not in detail, (
            f"Raw exception text leaked in error response: {detail!r}"
        )
        assert "/etc/passwd" not in detail, (
            f"Internal path leaked in error response: {detail!r}"
        )

    def test_error_response_contains_correlation_id(self, client, auth_headers):
        """GET /api/files/list error detail must contain a UUID correlation reference."""
        with patch("api.files.get_storage_backend") as mock_storage_factory:
            mock_backend = MagicMock()
            mock_backend.list_files.side_effect = RuntimeError("internal error")
            mock_storage_factory.return_value = mock_backend

            response = client.get("/api/files/list", headers=auth_headers)

        assert response.status_code == 500
        detail = response.json().get("detail", "")
        # Must contain "ref:" followed by a UUID-like string
        assert "ref:" in detail, (
            f"Expected 'ref:' correlation marker in error detail, got: {detail!r}"
        )
        # UUID pattern: 8-4-4-4-12 hex chars
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        assert re.search(uuid_pattern, detail), (
            f"Expected UUID pattern in error detail, got: {detail!r}"
        )

    def test_upload_error_does_not_leak_exception_text(self, client, auth_headers, tmp_path):
        """POST /api/files/upload when storage raises must not leak raw exception."""
        with patch("api.files.get_storage_backend") as mock_storage_factory:
            mock_backend = MagicMock()
            mock_backend.write_file.side_effect = OSError("disk full: /mnt/secret")
            mock_storage_factory.return_value = mock_backend

            test_file = tmp_path / "test.txt"
            test_file.write_bytes(b"hello")

            with open(str(test_file), "rb") as f:
                response = client.post(
                    "/api/files/upload",
                    headers=auth_headers,
                    files={"file": ("test.txt", f, "text/plain")},
                )

        assert response.status_code == 500
        detail = response.json().get("detail", "")
        assert "/mnt/secret" not in detail, (
            f"Internal path leaked in upload error: {detail!r}"
        )

    def test_get_url_error_does_not_leak_exception_text(self, client, auth_headers):
        """GET /api/files/url/{path} error must not expose raw exception text."""
        with patch("api.files.get_storage_backend") as mock_storage_factory:
            mock_backend = MagicMock()
            mock_backend.file_exists.return_value = True
            mock_backend.get_file_url.side_effect = RuntimeError("s3 credentials: key=AKIA...")
            mock_storage_factory.return_value = mock_backend

            response = client.get("/api/files/url/some/file.xlsx", headers=auth_headers)

        assert response.status_code == 500
        detail = response.json().get("detail", "")
        assert "AKIA" not in detail, (
            f"Credential string leaked in URL error: {detail!r}"
        )
