"""Audit logging for authentication and authorization."""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from db.models import User, AuditLog

logger = logging.getLogger(__name__)


def log_user_action(
    action: str,
    user: User = None,
    db: Session = None,
    target_user_id: Optional[int] = None,
    details: Optional[dict] = None,
    source_ip: Optional[str] = None,
    resource: Optional[str] = None,
    outcome: str = "success",
):
    """
    Log user action for audit trail.

    Writes to logger.info always. When db session is provided, also persists
    to the audit_log table. Audit failures must never propagate to callers.

    Args:
        action: Action performed (e.g., 'login', 'create_user', 'file_upload')
        user: User performing the action (may be None for anonymous actions)
        db: Optional SQLAlchemy session — when provided, writes to audit_log table
        target_user_id: Optional ID of target user (for user management actions)
        details: Optional additional details dict (stored in detail_json column)
        source_ip: Remote IP address of the request
        resource: Resource path being accessed (e.g., '/api/files/upload')
        outcome: "success" or "failure"
    """
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'user_id': getattr(user, 'id', None),
        'username': getattr(user, 'username', None),
        'user_role': getattr(user, 'role', None) and getattr(user.role, 'value', str(user.role)),
        'sales_team_id': getattr(user, 'sales_team_id', None),
        'outcome': outcome,
        'source_ip': source_ip,
        'resource': resource,
    }

    if target_user_id:
        log_data['target_user_id'] = target_user_id

    if details:
        log_data.update(details)

    logger.info("audit: action=%s user=%s outcome=%s source_ip=%s resource=%s",
                action, getattr(user, 'id', None), outcome, source_ip, resource)

    # DB write when session provided — failures must not propagate
    if db is not None:
        try:
            detail_payload = dict(details) if details else {}
            if target_user_id:
                detail_payload['target_user_id'] = target_user_id

            entry = AuditLog(
                event_type=action,
                user_id=getattr(user, 'id', None),
                source_ip=source_ip,
                resource=resource,
                outcome=outcome,
                detail_json=detail_payload or None,
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            logger.error("Failed to write audit log to DB: %s", e)
            # Do NOT re-raise — audit failure must not break the request
            try:
                db.rollback()
            except Exception:
                pass


def log_data_access(
    user: User,
    resource_type: str,
    resource_id: Optional[str] = None,
    sales_team_id: Optional[int] = None
):
    """
    Log data access for audit trail.

    Args:
        user: User accessing data
        resource_type: Type of resource (e.g., 'pipeline_run', 'loan_fact')
        resource_id: Optional resource ID
        sales_team_id: Optional sales team ID of accessed data
    """
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': 'data_access',
        'user_id': user.id,
        'username': user.username,
        'user_role': user.role.value,
        'user_sales_team_id': user.sales_team_id,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'accessed_sales_team_id': sales_team_id,
    }

    logger.info(f"Data access: {log_data}")


def log_authorization_failure(
    user: User,
    action: str,
    reason: str,
    resource_id: Optional[str] = None
):
    """
    Log authorization failure for security monitoring.

    Args:
        user: User attempting action
        action: Action attempted
        reason: Reason for failure
        resource_id: Optional resource ID
    """
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': 'authorization_failure',
        'user_id': user.id,
        'username': user.username,
        'user_role': user.role.value,
        'sales_team_id': user.sales_team_id,
        'attempted_action': action,
        'reason': reason,
        'resource_id': resource_id,
    }

    logger.warning(f"Authorization failure: {log_data}")
