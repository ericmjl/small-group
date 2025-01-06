"""Script to populate the database with mock data."""

from datetime import date, timedelta
import random
from pathlib import Path
import sys
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

# Add the parent directory to the path so we can import the app
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_db
from app.models import Member, Attendance


class Profile(str, Enum):
    DEFAULT = "default"
    TYPICAL = "typical"
    IMBALANCED = "imbalanced"
    GRAD_HEAVY = "grad_heavy"


@dataclass
class MemberProfile:
    role: str
    education_status: str
    count: int
    faith_status_weights: Optional[List[float]] = None
    gender_weights: Optional[List[float]] = None


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

FAITH_STATUSES = ["baptized", "believer", "seeker", "unknown"]

# Profile definitions
PROFILES = {
    Profile.DEFAULT: [
        MemberProfile(
            role="counselor",
            education_status="any",
            count=int(30 * 0.2),  # 20% counselors
            faith_status_weights=[0.3, 0.3, 0.3, 0.1],
        ),
        MemberProfile(
            role="facilitator",
            education_status="any",
            count=int(30 * 0.2),  # 20% facilitators
            faith_status_weights=[0.3, 0.3, 0.3, 0.1],
        ),
        MemberProfile(
            role="none",
            education_status="any",
            count=int(30 * 0.6),  # 60% regular members
            faith_status_weights=[0.3, 0.3, 0.3, 0.1],
        ),
    ],
    Profile.TYPICAL: [
        # Counselors - all graduated
        MemberProfile(
            role="counselor",
            education_status="graduated",
            count=3,
            faith_status_weights=[0.5, 0.5, 0.0, 0.0],  # Only baptized or believer
            gender_weights=[0.5, 0.5],  # Equal gender distribution
        ),
        # Facilitators - all undergrads
        MemberProfile(
            role="facilitator",
            education_status="undergraduate",
            count=5,
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],  # Mostly baptized or believer
            gender_weights=[0.5, 0.5],  # Equal gender distribution
        ),
        # Regular undergrad members
        MemberProfile(
            role="none",
            education_status="undergraduate",
            count=8,  # Half of regular members are undergrads
            faith_status_weights=[0.2, 0.3, 0.4, 0.1],  # More seekers
            gender_weights=[0.5, 0.5],  # Equal gender distribution
        ),
        # Regular graduate student members
        MemberProfile(
            role="none",
            education_status="graduate",
            count=5,  # About a third are grad students
            faith_status_weights=[0.3, 0.3, 0.3, 0.1],  # Equal distribution
            gender_weights=[0.5, 0.5],
        ),
        # Regular graduated members
        MemberProfile(
            role="none",
            education_status="graduated",
            count=3,  # A few graduated members
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],  # More mature in faith
            gender_weights=[0.5, 0.5],
        ),
    ],
    Profile.IMBALANCED: [
        # Single counselor (graduated)
        MemberProfile(
            role="counselor",
            education_status="graduated",
            count=1,
            faith_status_weights=[0.5, 0.5, 0.0, 0.0],  # Only baptized or believer
            gender_weights=[0.5, 0.5],
        ),
        # Two facilitators (mix of education status)
        MemberProfile(
            role="facilitator",
            education_status="undergraduate",
            count=1,
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],  # Mostly baptized or believer
            gender_weights=[0.5, 0.5],
        ),
        MemberProfile(
            role="facilitator",
            education_status="graduate",
            count=1,
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],
            gender_weights=[0.5, 0.5],
        ),
        # Regular members - diverse mix of education statuses
        MemberProfile(
            role="none",
            education_status="undergraduate",
            count=8,  # 40% undergrads
            faith_status_weights=[0.2, 0.3, 0.4, 0.1],  # More seekers
            gender_weights=[0.5, 0.5],
        ),
        MemberProfile(
            role="none",
            education_status="graduate",
            count=7,  # 35% grad students
            faith_status_weights=[0.3, 0.3, 0.3, 0.1],
            gender_weights=[0.5, 0.5],
        ),
        MemberProfile(
            role="none",
            education_status="graduated",
            count=5,  # 25% graduated
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],  # More mature in faith
            gender_weights=[0.5, 0.5],
        ),
    ],
    Profile.GRAD_HEAVY: [
        # Counselors - mix of graduated and current
        MemberProfile(
            role="counselor",
            education_status="graduated",
            count=2,
            faith_status_weights=[0.5, 0.5, 0.0, 0.0],  # Only baptized or believer
            gender_weights=[0.5, 0.5],
        ),
        MemberProfile(
            role="counselor",
            education_status="graduate",
            count=1,
            faith_status_weights=[0.5, 0.5, 0.0, 0.0],
            gender_weights=[0.5, 0.5],
        ),
        # Facilitators - mix of education statuses
        MemberProfile(
            role="facilitator",
            education_status="undergraduate",
            count=2,
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],  # Mostly baptized or believer
            gender_weights=[0.5, 0.5],
        ),
        MemberProfile(
            role="facilitator",
            education_status="graduate",
            count=2,
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],
            gender_weights=[0.5, 0.5],
        ),
        # Regular graduated members (larger group)
        MemberProfile(
            role="none",
            education_status="graduated",
            count=6,  # Significant graduated presence
            faith_status_weights=[0.4, 0.4, 0.2, 0.0],  # More mature in faith
            gender_weights=[0.5, 0.5],
        ),
        # Regular graduate students
        MemberProfile(
            role="none",
            education_status="graduate",
            count=4,
            faith_status_weights=[0.3, 0.3, 0.3, 0.1],  # Equal distribution
            gender_weights=[0.5, 0.5],
        ),
        # Regular undergrad members
        MemberProfile(
            role="none",
            education_status="undergraduate",
            count=7,
            faith_status_weights=[0.2, 0.3, 0.4, 0.1],  # More seekers
            gender_weights=[0.5, 0.5],
        ),
    ],
}


def create_mock_members(profile: Profile = Profile.DEFAULT):
    """Create mock members based on the specified profile."""
    db = next(get_db())
    created_members = []
    profile_config = PROFILES[profile]

    try:
        # Create members according to profile
        used_names = set()

        for member_profile in profile_config:
            for _ in range(member_profile.count):
                # Select a unique name
                while True:
                    given_name = random.choice(GIVEN_NAMES)
                    surname = random.choice(SURNAMES)
                    full_name = f"{surname}{given_name}"
                    if full_name not in used_names:
                        used_names.add(full_name)
                        break

                # Determine gender based on weights or default to random
                gender_weights = member_profile.gender_weights or [0.5, 0.5]
                gender = random.choices(["M", "F"], weights=gender_weights)[0]

                # Determine faith status based on weights or default
                faith_weights = member_profile.faith_status_weights or [
                    0.25,
                    0.25,
                    0.25,
                    0.25,
                ]
                faith_status = random.choices(FAITH_STATUSES, weights=faith_weights)[0]

                # Determine education status
                education_status = (
                    member_profile.education_status
                    if member_profile.education_status != "any"
                    else random.choices(
                        ["undergraduate", "graduate", "graduated"],
                        weights=[0.5, 0.3, 0.2],
                    )[0]
                )

                member = Member(
                    given_name=given_name,
                    surname=surname,
                    gender=gender,
                    faith_status=faith_status,
                    role=member_profile.role,
                    education_status=education_status,
                    active=True,
                    notes="這是測試資料",
                )
                db.add(member)
                created_members.append(member)

        db.commit()

        # Print debug information
        print(f"\nCreated {len(created_members)} members using {profile} profile:")
        for i, member in enumerate(created_members, 1):
            print(
                f"{i}. {member.surname}{member.given_name} "
                f"({member.gender}, {member.role}, {member.education_status}, "
                f"{member.faith_status}, active={member.active})"
            )

        # Create today's attendance records for all members
        today = date.today()
        for member in created_members:
            attendance = Attendance(
                member_id=member.id,
                date=today,
                present=True,
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
    import argparse

    parser = argparse.ArgumentParser(description="Populate database with mock data")
    parser.add_argument(
        "--profile",
        type=Profile,
        choices=list(Profile),
        default=Profile.DEFAULT,
        help="Profile to use for member generation",
    )

    args = parser.parse_args()

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
    print(f"\nCreating new members using {args.profile} profile...")
    create_mock_members(args.profile)
