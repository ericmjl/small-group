import pytest
from app.group_divider import (
    GroupMember,
    MemberRole,
    Group,
    divide_into_groups,
    balance_gender_in_groups,
)
from hypothesis import given, strategies as st
from typing import List


@pytest.fixture
def basic_members():
    """Basic set of members for testing."""
    return [
        GroupMember(
            id=1,
            surname="Zhang",
            given_name="San",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="已受洗",
            education_status="graduated",
            is_graduated=True,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=2,
            surname="Li",
            given_name="Si",
            role=MemberRole.COUNSELOR,
            gender="F",
            faith_status="已受洗",
            education_status="graduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=3,
            surname="Wang",
            given_name="Wu",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="慕道友",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
        GroupMember(
            id=4,
            surname="Zhao",
            given_name="Liu",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="慕道友",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
    ]


@pytest.fixture
def duplicate_prone_members():
    """Set of members that could trigger the duplication bug."""
    return [
        # Leaders
        GroupMember(
            id=1,
            surname="Zhang",
            given_name="San",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="已受洗",
            education_status="graduated",
            is_graduated=True,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=2,
            surname="Li",
            given_name="Si",
            role=MemberRole.COUNSELOR,
            gender="F",
            faith_status="已受洗",
            education_status="graduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=3,
            surname="Wang",
            given_name="Wu",
            role=MemberRole.COUNSELOR,
            gender="M",
            faith_status="已受洗",
            education_status="graduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        # Regular members with same characteristics (prone to swapping)
        GroupMember(
            id=4,
            surname="Zhao",
            given_name="Liu",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="慕道友",
            education_status="graduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
        GroupMember(
            id=5,
            surname="Qian",
            given_name="Qi",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="慕道友",
            education_status="graduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
        GroupMember(
            id=6,
            surname="Sun",
            given_name="Ba",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="慕道友",
            education_status="graduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
        GroupMember(
            id=7,
            surname="Zhou",
            given_name="Jiu",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="慕道友",
            education_status="graduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
    ]


def test_basic_group_division(basic_members):
    """Test basic group division functionality."""
    groups = divide_into_groups(basic_members, 2, max_iterations=0)

    # Check number of groups
    assert len(groups) == 2

    # Check all members are assigned
    all_members = [m for g in groups for m in g.members]
    assert len(all_members) == len(basic_members)
    assert len(set(m.id for m in all_members)) == len(basic_members)


def test_leader_distribution(basic_members):
    """Test that leaders are distributed properly."""
    groups = divide_into_groups(basic_members, 2, max_iterations=0)

    # Check each group has at least one leader
    for group in groups:
        assert any(
            m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
            for m in group.members
        )


def test_no_member_duplication(duplicate_prone_members):
    """Test that no member appears in multiple groups, even after gender balancing."""
    groups = divide_into_groups(duplicate_prone_members, 2, max_iterations=1000)

    # Get all member IDs
    member_ids = [m.id for g in groups for m in g.members]

    # Check for duplicates
    assert len(member_ids) == len(set(member_ids))
    assert len(member_ids) == len(duplicate_prone_members)


def test_graduate_separation(basic_members):
    """Test that graduates are properly separated into graduate groups."""
    # Add more graduates to force graduate group creation
    graduates = [
        GroupMember(
            id=10,
            surname="Test",
            given_name=str(i),
            role=MemberRole.REGULAR,
            gender="M" if i % 2 == 0 else "F",
            faith_status="已受洗",
            education_status="graduated",
            is_graduated=True,
            is_present=True,
            prep_attended=False,
        )
        for i in range(5)
    ]

    test_members = basic_members + graduates
    groups = divide_into_groups(test_members, 2, max_iterations=0)

    # Find group with most graduates
    grad_group = max(groups, key=lambda g: sum(1 for m in g.members if m.is_graduated))

    # Check that most graduates are in the same group
    grad_count = sum(1 for m in grad_group.members if m.is_graduated)
    assert grad_count >= 3  # Most graduates should be together


def test_gender_balance(duplicate_prone_members):
    """Test that gender balancing improves gender distribution."""
    # First divide without gender balancing
    unbalanced_groups = divide_into_groups(duplicate_prone_members, 2, max_iterations=0)

    # Then divide with gender balancing
    balanced_groups = divide_into_groups(
        duplicate_prone_members, 2, max_iterations=1000
    )

    def calculate_gender_imbalance(groups):
        """Calculate total gender imbalance across groups."""
        total_imbalance = 0
        for group in groups:
            males = sum(1 for m in group.members if m.gender == "M")
            females = sum(1 for m in group.members if m.gender == "F")
            total_imbalance += abs(males - females)
        return total_imbalance

    # Check that gender balancing reduced imbalance
    assert calculate_gender_imbalance(balanced_groups) <= calculate_gender_imbalance(
        unbalanced_groups
    )


def test_prep_attendee_distribution(basic_members):
    """Test that prep attendees are distributed evenly."""
    # Add more prep attendees
    prep_attendees = [
        GroupMember(
            id=20 + i,
            surname="Prep",
            given_name=str(i),
            role=MemberRole.REGULAR,
            gender="M" if i % 2 == 0 else "F",
            faith_status="慕道友",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        )
        for i in range(4)
    ]

    test_members = basic_members + prep_attendees
    groups = divide_into_groups(test_members, 2, max_iterations=0)

    # Calculate prep attendee counts
    prep_counts = [sum(1 for m in g.members if m.prep_attended) for g in groups]

    # Check that prep attendees are somewhat evenly distributed
    assert max(prep_counts) - min(prep_counts) <= 2


def test_empty_input():
    """Test handling of empty input."""
    groups = divide_into_groups([], 2, max_iterations=0)
    assert len(groups) == 1
    assert len(groups[0].members) == 0


def test_single_member(basic_members):
    """Test handling of single member input."""
    groups = divide_into_groups([basic_members[0]], 2, max_iterations=0)
    assert len(groups) == 1
    assert len(groups[0].members) == 1
    assert groups[0].members[0].id == basic_members[0].id


def test_counselor_distribution(duplicate_prone_members):
    """Test that counselors are distributed as evenly as possible."""
    groups = divide_into_groups(duplicate_prone_members, 2, max_iterations=0)

    # Count counselors in each group
    counselor_counts = [
        sum(1 for m in g.members if m.role == MemberRole.COUNSELOR) for g in groups
    ]

    # Check that counselor counts don't differ by more than 1
    assert max(counselor_counts) - min(counselor_counts) <= 1
