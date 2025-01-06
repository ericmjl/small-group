import pytest
from app.group_divider import GroupMember, Group, MemberRole, divide_into_groups


@pytest.fixture
def sample_members():
    """Create a sample set of members for testing."""
    return [
        # Leaders (non-graduated)
        GroupMember(1, "Leader1", MemberRole.FACILITATOR, "M", "believer", False, True),
        GroupMember(2, "Leader2", MemberRole.COUNSELOR, "F", "seeker", False, True),
        GroupMember(3, "Leader3", MemberRole.FACILITATOR, "F", "believer", False, True),
        # Regular members (non-graduated)
        GroupMember(4, "Member1", MemberRole.REGULAR, "M", "believer", False, True),
        GroupMember(5, "Member2", MemberRole.REGULAR, "F", "seeker", False, True),
        GroupMember(6, "Member3", MemberRole.REGULAR, "M", "seeker", False, True),
        GroupMember(7, "Member4", MemberRole.REGULAR, "F", "believer", False, True),
        GroupMember(8, "Member5", MemberRole.REGULAR, "M", "believer", False, True),
        # Graduated members
        GroupMember(9, "Grad1", MemberRole.REGULAR, "M", "believer", True, True),
        GroupMember(10, "Grad2", MemberRole.REGULAR, "F", "believer", True, True),
        GroupMember(11, "Grad3", MemberRole.REGULAR, "M", "seeker", True, True),
        GroupMember(12, "Grad4", MemberRole.REGULAR, "F", "seeker", True, True),
    ]


@pytest.fixture
def absent_members(sample_members):
    """Create a copy of sample members with some marked as absent."""
    # Create deep copies of each GroupMember
    absent = [
        GroupMember(
            id=m.id,
            name=m.name,
            role=m.role,
            gender=m.gender,
            faith_status=m.faith_status,
            is_graduated=m.is_graduated,
            is_present=m.is_present,
        )
        for m in sample_members
    ]
    # Mark some members as absent
    absent[4].is_present = False  # Member2
    absent[9].is_present = False  # Grad1
    return absent


def test_basic_group_division(sample_members):
    """Test basic group division with all constraints met."""
    groups = divide_into_groups(sample_members, num_groups=2)

    # Check we got the right number of groups
    assert len(groups) >= 2

    # Check each group has 4-7 members
    for group in groups:
        assert 4 <= len(group.members) <= 7

    # Check each non-graduated group has at least one leader
    nongrad_groups = [g for g in groups if not any(m.is_graduated for m in g.members)]
    for group in nongrad_groups:
        assert any(
            m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
            for m in group.members
        )


def test_graduated_member_handling(sample_members):
    """Test that graduated members are handled appropriately."""
    groups = divide_into_groups(sample_members, num_groups=2)

    # Find groups with graduated members
    grad_groups = [g for g in groups if any(m.is_graduated for m in g.members)]

    # If we have 4 or more graduated members, they should be in their own group
    graduated = [m for m in sample_members if m.is_graduated and m.is_present]
    if len(graduated) >= 4:
        assert len(grad_groups) > 0
        assert all(m.is_graduated for m in grad_groups[0].members)

    # If less than 4 graduated members, they should be distributed
    if len(graduated) < 4:
        assert not any(all(m.is_graduated for m in g.members) for g in groups)


def test_leader_distribution(sample_members):
    """Test that leaders are distributed evenly among non-graduated groups."""
    groups = divide_into_groups(sample_members, num_groups=2)

    # Get non-graduated groups
    nongrad_groups = [g for g in groups if not any(m.is_graduated for m in g.members)]

    # Count leaders in each group
    leader_counts = [
        sum(
            1
            for m in g.members
            if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
        )
        for g in nongrad_groups
    ]

    # Check leader distribution is relatively even
    assert max(leader_counts) - min(leader_counts) <= 1


def test_absent_member_handling(absent_members):
    """Test that absent members are not included in groups."""
    groups = divide_into_groups(absent_members, num_groups=2)

    # Check that all members in groups are present
    for group in groups:
        assert all(member.is_present for member in group.members)

    # Check total number of members matches present members
    present_count = sum(1 for m in absent_members if m.is_present)
    total_grouped = sum(len(group.members) for group in groups)
    assert total_grouped == present_count


def test_diversity_optimization(sample_members):
    """Test that groups are diverse in terms of gender and faith status."""
    groups = divide_into_groups(sample_members, num_groups=2)

    for group in groups:
        if len(group.members) >= 4:  # Only check groups with enough members
            # Count gender distribution
            gender_counts = {"M": 0, "F": 0}
            faith_counts = {"believer": 0, "seeker": 0}

            for member in group.members:
                gender_counts[member.gender] += 1
                faith_counts[member.faith_status] += 1

            # Check that there's some mix of genders and faith statuses
            assert min(gender_counts.values()) > 0, "Group should have mixed genders"
            assert (
                min(faith_counts.values()) > 0
            ), "Group should have mixed faith status"


def test_edge_cases():
    """Test edge cases and error conditions."""
    # Test with too few members
    few_members = [
        GroupMember(1, "Leader1", MemberRole.FACILITATOR, "M", "believer", False, True),
        GroupMember(2, "Member1", MemberRole.REGULAR, "M", "believer", False, True),
    ]
    with pytest.raises(ValueError):
        divide_into_groups(few_members, num_groups=1)

    # Test with no leaders
    no_leaders = [
        GroupMember(i, f"Member{i}", MemberRole.REGULAR, "M", "believer", False, True)
        for i in range(1, 8)
    ]
    with pytest.raises(ValueError):
        divide_into_groups(no_leaders, num_groups=1)

    # Test with all members absent
    all_absent = [
        GroupMember(
            1, "Leader1", MemberRole.FACILITATOR, "M", "believer", False, False
        ),
        GroupMember(2, "Member1", MemberRole.REGULAR, "M", "believer", False, False),
        GroupMember(3, "Member2", MemberRole.REGULAR, "F", "seeker", False, False),
    ]
    with pytest.raises(ValueError):
        divide_into_groups(all_absent, num_groups=1)


def test_group_size_constraints(sample_members):
    """Test that groups respect size constraints of 4-7 members."""
    groups = divide_into_groups(sample_members, num_groups=2)

    for group in groups:
        assert (
            len(group.members) >= 4
        ), f"Group has fewer than 4 members: {len(group.members)}"
        assert (
            len(group.members) <= 7
        ), f"Group has more than 7 members: {len(group.members)}"
