"""
Seed staging admin user — idempotent.

Run via ECS one-off task:
  aws ecs run-task --cluster intrepid-poc-qa --task-definition intrepid-poc-qa \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[SUBNET_IDS],securityGroups=[SG_ID],assignPublicIp=ENABLED}" \
    --overrides '{"containerOverrides":[{"name":"app","command":["python","scripts/seed_staging_user.py"]}]}'

Safe to run multiple times — updates password if user already exists.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import User, UserRole
from auth.security import get_password_hash

STAGING_USERNAME = "admin"
STAGING_PASSWORD = "IntrepidStaging2024!"  # hardcoded — staging internal-only, RDS not publicly accessible
STAGING_EMAIL = "admin@staging.intrepid"
STAGING_FULL_NAME = "Staging Admin"


def seed_staging_user() -> None:
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == STAGING_USERNAME).first()
        if existing:
            existing.hashed_password = get_password_hash(STAGING_PASSWORD)
            existing.is_active = True
            db.commit()
            print(f"Admin user updated: {STAGING_USERNAME}")
        else:
            user = User(
                username=STAGING_USERNAME,
                email=STAGING_EMAIL,
                hashed_password=get_password_hash(STAGING_PASSWORD),
                full_name=STAGING_FULL_NAME,
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"Admin user created: {STAGING_USERNAME}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_staging_user()
