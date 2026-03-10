"""Tests for AuditLog DB model and write behavior (HARD-06).

RED phase: these tests verify behaviors that do not yet exist.
- AuditLog table schema exists in SQLite-compatible form
- log_user_action writes a row to DB when db session provided
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.connection import Base
from db.models import User, UserRole
from auth.security import get_password_hash


@pytest.fixture
def audit_engine():
    """Fresh in-memory SQLite engine that includes AuditLog table."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def audit_session(audit_engine):
    """DB session for audit tests."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=audit_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def audit_user(audit_session):
    """Create a user in the audit test DB."""
    user = User(
        email="audit_test@test.com",
        username="audit_test",
        hashed_password=get_password_hash("testpass"),
        full_name="Audit Test User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    audit_session.add(user)
    audit_session.commit()
    audit_session.refresh(user)
    return user


class TestAuditLogTableSchema:
    """Test AuditLog SQLAlchemy model and DB table structure."""

    def test_audit_log_table_exists(self, audit_engine):
        """audit_log table must exist after Base.metadata.create_all."""
        inspector = inspect(audit_engine)
        tables = inspector.get_table_names()
        assert "audit_log" in tables, (
            f"Expected 'audit_log' table to exist after create_all, but tables are: {tables}"
        )

    def test_audit_log_table_schema(self, audit_engine):
        """audit_log table must have all required columns."""
        inspector = inspect(audit_engine)
        columns = {col["name"] for col in inspector.get_columns("audit_log")}
        required_columns = {
            "id", "event_type", "user_id", "timestamp",
            "source_ip", "resource", "outcome", "detail_json",
        }
        missing = required_columns - columns
        assert not missing, (
            f"audit_log table is missing columns: {missing}. Found: {columns}"
        )

    def test_audit_log_model_importable(self):
        """AuditLog model must be importable from db.models."""
        from db.models import AuditLog  # noqa: F401 — import test


class TestAuditLogDbWrite:
    """Test that log_user_action writes a row to audit_log when db session is provided."""

    def test_log_user_action_writes_db_row(self, audit_session, audit_user):
        """log_user_action with db=session must insert one row to audit_log."""
        from auth.audit import log_user_action
        from db.models import AuditLog

        log_user_action(
            action="login",
            user=audit_user,
            db=audit_session,
            source_ip="127.0.0.1",
            resource="/api/auth/login",
            outcome="success",
        )

        rows = audit_session.query(AuditLog).all()
        assert len(rows) == 1, (
            f"Expected 1 row in audit_log after log_user_action, got {len(rows)}"
        )

    def test_log_user_action_stores_correct_values(self, audit_session, audit_user):
        """log_user_action must store action, user_id, outcome in the inserted row."""
        from auth.audit import log_user_action
        from db.models import AuditLog

        log_user_action(
            action="file_upload",
            user=audit_user,
            db=audit_session,
            source_ip="10.0.0.1",
            resource="/api/files/upload",
            outcome="success",
            details={"filename": "report.xlsx"},
        )

        row = audit_session.query(AuditLog).first()
        assert row is not None
        assert row.event_type == "file_upload"
        assert row.user_id == audit_user.id
        assert row.outcome == "success"
        assert row.source_ip == "10.0.0.1"
        assert row.resource == "/api/files/upload"

    def test_log_user_action_no_db_does_not_raise(self, audit_user):
        """log_user_action without db parameter must not raise (logger-only path preserved)."""
        from auth.audit import log_user_action

        # Should not raise even without db
        log_user_action(action="logout", user=audit_user)

    def test_log_user_action_db_failure_does_not_raise(self, audit_user):
        """log_user_action must not propagate DB errors to the caller."""
        from unittest.mock import MagicMock
        from auth.audit import log_user_action

        bad_db = MagicMock()
        bad_db.add.side_effect = RuntimeError("DB connection lost")

        # Must not raise — audit failure must not break the request
        log_user_action(
            action="login",
            user=audit_user,
            db=bad_db,
            outcome="success",
        )
