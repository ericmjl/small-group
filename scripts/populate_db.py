"""Script to populate the database with mock data."""

from datetime import date, timedelta
import random
from pathlib import Path
import sys

# Add the parent directory to the path so we can import the app
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_db
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
    "宜蓁",
    "俊宏",
    "怡萱",
    "柏宏",
    "雅琪",
    "志豪",
    "佳慧",
    "宗翰",
    "雅文",
    "俊賢",
    "怡婷",
    "柏均",
    "淑娟",
    "建志",
    "美君",
]

SURNAMES = ["陳", "林", "張", "李", "王", "吳", "劉", "蔡", "楊", "黃"]

ROLES = ["counselor", "facilitator", "none"]
ROLE_WEIGHTS = [0.2, 0.2, 0.6]  # 20% counselors, 20% facilitators, 60% none

FAITH_STATUSES = ["baptized", "believer", "seeker", "unknown"]
FAITH_WEIGHTS = [0.3, 0.3, 0.3, 0.1]  # 30% each except unknown

EDUCATION_STATUSES = ["undergraduate", "graduate", "graduated"]
EDUCATION_WEIGHTS = [0.5, 0.3, 0.2]  # 50% undergrad, 30% grad, 20% graduated


def create_mock_members(num_members=30):
    """Create mock members with realistic Chinese names and varied statuses."""
    db = next(get_db())
    created_members = []

    try:
        # Create members
        for i in range(num_members):
            member = Member(
                given_name=GIVEN_NAMES[i],  # Use unique names
                surname=random.choice(SURNAMES),
                gender=random.choice(["M", "F"]),
                faith_status=random.choices(FAITH_STATUSES, weights=FAITH_WEIGHTS)[0],
                role=random.choices(ROLES, weights=ROLE_WEIGHTS)[0],
                education_status=random.choices(
                    EDUCATION_STATUSES, weights=EDUCATION_WEIGHTS
                )[0],
                active=True,  # Make all members active by default
                notes="這是測試資料",
            )
            db.add(member)
            created_members.append(member)

        db.commit()

        # Print debug information
        print(f"\nCreated {len(created_members)} members:")
        for i, member in enumerate(created_members, 1):
            print(
                f"{i}. {member.surname}{member.given_name} "
                f"({member.gender}, {member.role}, {member.education_status}, "
                f"active={member.active})"
            )

        # Create today's attendance records for all members
        today = date.today()
        for member in created_members:
            attendance = Attendance(
                member_id=member.id,
                date=today,
                present=True,  # Make all members present by default
                notes="準時參加",
            )
            db.add(attendance)

        db.commit()
        print(f"\nCreated attendance records for {len(created_members)} members.")

    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Delete existing data first
    db = next(get_db())
    try:
        print("Clearing existing data...")
        db.query(Attendance).delete()
        db.query(Member).delete()
        db.commit()
        print("Database cleared.")
    except Exception as e:
        print(f"Error clearing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    # Create new members
    print("\nCreating new members...")
    create_mock_members()
