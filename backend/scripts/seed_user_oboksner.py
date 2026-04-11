"""
Seed user: Oleg Boksner (oboksner@twgglobal.com) — idempotent.

Run via ECS one-off task:
  aws ecs run-task --cluster intrepid-poc-qa --task-definition intrepid-poc-qa \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[SUBNET_IDS],securityGroups=[SG_ID],assignPublicIp=ENABLED}" \
    --overrides '{"containerOverrides":[{"name":"app","command":["python","scripts/seed_user_oboksner.py"]}]}'

Safe to run multiple times — updates password if user already exists.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import User, UserRole
from auth.security import get_password_hash

USERNAME = "oboksner"
PASSWORD = "Intrepid@Oleg2026!"
EMAIL = "oboksner@twgglobal.com"
FULL_NAME = "Oleg Boksner"
ROLE = UserRole.ANALYST


def seed_user() -> None:
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == USERNAME).first()
        if existing:
            existing.hashed_password = get_password_hash(PASSWORD)
            existing.is_active = True
            db.commit()
            print(f"User updated: {USERNAME}")
        else:
            user = User(
                username=USERNAME,
                email=EMAIL,
                hashed_password=get_password_hash(PASSWORD),
                full_name=FULL_NAME,
                role=ROLE,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"User created: {USERNAME} ({EMAIL}) role={ROLE.value}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_user()
