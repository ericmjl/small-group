"""Script to populate the database with mock data."""

from datetime import date, timedelta
import random
from pathlib import Path
import sys

# Add the parent directory to the path so we can import the app
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Member, Attendance

# Mock data
GIVEN_NAMES = [
    "志明",
    "家豪",
    "建宏",
    "俊傑",
    "宗翰",
    "雅婷",
    "佳穎",
    "淑芬",
    "美玲",
    "怡君",
    "偉誠",
    "柏翰",
    "家瑋",
    "雅雯",
    "詩涵",
]

SURNAMES = ["陳", "林", "張", "李", "王", "吳", "劉", "蔡", "楊", "黃"]

ROLES = ["counselor", "facilitator", "none"]
ROLE_WEIGHTS = [0.2, 0.2, 0.6]  # 20% counselors, 20% facilitators, 60% none

FAITH_STATUSES = ["baptized", "believer", "seeker", "unknown"]
FAITH_WEIGHTS = [0.3, 0.3, 0.3, 0.1]  # 30% each except unknown

EDUCATION_STATUSES = ["undergraduate", "graduate", "graduated"]
EDUCATION_WEIGHTS = [0.6, 0.3, 0.1]  # 60% undergrad, 30% grad, 10% graduated


def create_mock_members(num_members=15):
    """Create mock members with realistic Chinese names and varied statuses."""
    db = SessionLocal()

    try:
        # Create members
        for _ in range(num_members):
            member = Member(
                given_name=random.choice(GIVEN_NAMES),
                surname=random.choice(SURNAMES),
                gender=random.choice(["M", "F"]),
                faith_status=random.choices(FAITH_STATUSES, weights=FAITH_WEIGHTS)[0],
                role=random.choices(ROLES, weights=ROLE_WEIGHTS)[0],
                education_status=random.choices(
                    EDUCATION_STATUSES, weights=EDUCATION_WEIGHTS
                )[0],
                active=random.choices([True, False], weights=[0.8, 0.2])[
                    0
                ],  # 80% active
                notes="這是測試資料",
            )
            db.add(member)

        db.commit()

        # Create some attendance records for the past week
        members = db.query(Member).filter(Member.active == True).all()
        today = date.today()

        for i in range(7):  # Past week
            record_date = today - timedelta(days=i)
            for member in members:
                # 70% chance of being present if the member is active
                if random.random() < 0.7:
                    attendance = Attendance(
                        member_id=member.id,
                        date=record_date,
                        present=True,
                        notes="準時參加",
                    )
                    db.add(attendance)

        db.commit()
        print(
            f"Successfully created {num_members} mock members and their attendance records."
        )

    finally:
        db.close()


if __name__ == "__main__":
    create_mock_members()
