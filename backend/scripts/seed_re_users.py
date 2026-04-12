"""Seed RE Dashboard users: create sales team, update/create oboksner, add kshah."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import User, UserRole
from auth.security import get_password_hash


def run():
    db: Session = SessionLocal()
    try:
        # 0. Ensure a sales_team row exists (FK constraint)
        existing_team = db.execute(text("SELECT id FROM sales_teams LIMIT 1")).fetchone()
        if not existing_team:
            db.execute(text("INSERT INTO sales_teams (id, name) VALUES (1, 'Sales Team 1')"))
            db.commit()
            print("Created sales_teams row: id=1, name='Sales Team 1'")
        else:
            print(f"Sales team already exists: id={existing_team[0]}")

        team_id = existing_team[0] if existing_team else 1

        # 1. Update or create oboksner as sales_team
        oboksner = db.query(User).filter(User.username == "oboksner").first()
        if oboksner:
            oboksner.role = UserRole.SALES_TEAM
            oboksner.sales_team_id = team_id
            db.commit()
            print(f"Updated oboksner -> role=sales_team, sales_team_id={team_id}")
        else:
            oboksner = User(
                username="oboksner",
                email="oboksner@twgglobal",
                full_name="O Boksner",
                hashed_password=get_password_hash("twg123"),
                role=UserRole.SALES_TEAM,
                sales_team_id=team_id,
                is_active=True,
            )
            db.add(oboksner)
            db.commit()
            print(f"Created oboksner -> role=sales_team, sales_team_id={team_id}, password=twg123")

        # 2. Add kshah as sales_team
        existing = db.query(User).filter(
            (User.username == "kshah") | (User.email == "kshah@twgglobal")
        ).first()
        if existing:
            print(f"User kshah already exists: {existing.username} ({existing.email}) role={existing.role.value}")
        else:
            kshah = User(
                username="kshah",
                email="kshah@twgglobal",
                full_name="Kamal Shah",
                hashed_password=get_password_hash("twg123"),
                role=UserRole.SALES_TEAM,
                sales_team_id=team_id,
                is_active=True,
            )
            db.add(kshah)
            db.commit()
            print(f"Created kshah (Kamal Shah) -> role=sales_team, sales_team_id={team_id}, password=twg123")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
