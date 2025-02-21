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


@st.composite
def group_members(draw, min_size: int = 1, max_size: int = 15) -> List[GroupMember]:
    """Strategy to generate a list of group members."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))

    return [
        GroupMember(
            id=i,
            surname=draw(st.text(min_size=1, max_size=10)),
            given_name=draw(st.text(min_size=1, max_size=10)),
            role=draw(st.sampled_from(list(MemberRole))),
            gender=draw(st.sampled_from(["M", "F"])),
            faith_status=draw(st.sampled_from(["已受洗", "慕道友"])),
            education_status=draw(
                st.sampled_from(["undergraduate", "graduate", "graduated"])
            ),
            is_graduated=draw(st.booleans()),
            is_present=True,  # Always True for diversity score testing
            prep_attended=draw(st.booleans()),
        )
        for i in range(size)
    ]


@given(
    st.lists(group_members(min_size=2, max_size=4), min_size=2, max_size=2),
)
def test_diversity_score_relative_properties(group_lists: List[List[GroupMember]]):
    """
    Test relative properties between groups' diversity scores.

    Properties tested:
    1. Leader density affects scores predictably
    2. Prep attendance balance affects scores predictably
    """
    groups = [Group(members=members) for members in group_lists]

    if len(groups) == 2:  # We need exactly 2 groups for these tests
        g1, g2 = groups

        # Test leader density penalty
        g1_leader_count = g1.leader_count
        g2_leader_count = g2.leader_count
        if (
            abs(g1_leader_count - g2_leader_count) > 2
        ):  # Test only with larger imbalances
            # Groups with very unbalanced leader counts should score lower
            high_leader_group = g1 if g1_leader_count > g2_leader_count else g2
            other_group = g2 if high_leader_group == g1 else g1

            # Only test if the other characteristics are relatively balanced
            if len(set(m.gender for m in high_leader_group.members)) == len(
                set(m.gender for m in other_group.members)
            ) and len(set(m.faith_status for m in high_leader_group.members)) == len(
                set(m.faith_status for m in other_group.members)
            ):
                score_with_imbalance = high_leader_group.calculate_diversity_score(
                    groups
                )

                # Create a more balanced version by converting some leaders to regular members
                balanced_members = []
                target_leader_count = (
                    other_group.leader_count + 1
                )  # Allow for one more leader
                current_leaders = 0

                for m in high_leader_group.members:
                    if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR):
                        if current_leaders < target_leader_count:
                            balanced_members.append(m)
                            current_leaders += 1
                        else:
                            balanced_members.append(
                                GroupMember(
                                    id=m.id,
                                    surname=m.surname,
                                    given_name=m.given_name,
                                    role=MemberRole.REGULAR,
                                    gender=m.gender,
                                    faith_status=m.faith_status,
                                    education_status=m.education_status,
                                    is_graduated=m.is_graduated,
                                    is_present=m.is_present,
                                    prep_attended=m.prep_attended,
                                )
                            )
                    else:
                        balanced_members.append(m)

                balanced_group = Group(members=balanced_members)
                score_with_balance = balanced_group.calculate_diversity_score(
                    [balanced_group if g == high_leader_group else g for g in groups]
                )

                assert (
                    score_with_balance >= score_with_imbalance - 1e-10
                ), "Groups with more balanced leader distribution should not score lower"

        # Test prep attendance balance
        g1_prep_count = g1.prep_attended_count
        g2_prep_count = g2.prep_attended_count
        if abs(g1_prep_count - g2_prep_count) > 2:  # Test only with larger imbalances
            # Groups with very unbalanced prep counts should score lower
            high_prep_group = g1 if g1_prep_count > g2_prep_count else g2
            other_group = g2 if high_prep_group == g1 else g1

            # Only test if the other characteristics are relatively balanced
            if len(set(m.gender for m in high_prep_group.members)) == len(
                set(m.gender for m in other_group.members)
            ) and len(set(m.faith_status for m in high_prep_group.members)) == len(
                set(m.faith_status for m in other_group.members)
            ):
                score_with_imbalance = high_prep_group.calculate_diversity_score(groups)

                # Create a more balanced version
                balanced_members = []
                target_prep_count = (
                    other_group.prep_attended_count + 1
                )  # Allow for one more prep
                current_prep = 0

                for m in high_prep_group.members:
                    if m.prep_attended:
                        if current_prep < target_prep_count:
                            balanced_members.append(m)
                            current_prep += 1
                        else:
                            balanced_members.append(
                                GroupMember(
                                    id=m.id,
                                    surname=m.surname,
                                    given_name=m.given_name,
                                    role=m.role,
                                    gender=m.gender,
                                    faith_status=m.faith_status,
                                    education_status=m.education_status,
                                    is_graduated=m.is_graduated,
                                    is_present=m.is_present,
                                    prep_attended=False,
                                )
                            )
                    else:
                        balanced_members.append(m)

                balanced_group = Group(members=balanced_members)
                score_with_balance = balanced_group.calculate_diversity_score(
                    [balanced_group if g == high_prep_group else g for g in groups]
                )

                assert (
                    score_with_balance >= score_with_imbalance - 1e-10
                ), "Groups with more balanced prep attendance should not score lower"
