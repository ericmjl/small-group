import pytest
from app.group_divider import GroupMember, Group, MemberRole, divide_into_groups


@pytest.fixture
def sample_members():
    """Create a sample set of members for testing."""
    return [
        # Leaders (non-graduated)
        GroupMember(
            id=1,
            surname="Leader",
            given_name="1",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=2,
            surname="Leader",
            given_name="2",
            role=MemberRole.COUNSELOR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=3,
            surname="Leader",
            given_name="3",
            role=MemberRole.FACILITATOR,
            gender="F",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        # Regular members (non-graduated)
        GroupMember(
            id=4,
            surname="Member",
            given_name="1",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=5,
            surname="Member",
            given_name="2",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
        GroupMember(
            id=6,
            surname="Member",
            given_name="3",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
        GroupMember(
            id=7,
            surname="Member",
            given_name="4",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=8,
            surname="Member",
            given_name="5",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=False,
        ),
        # Graduated members
        GroupMember(
            id=9,
            surname="Grad",
            given_name="1",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="graduated",
            is_graduated=True,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=10,
            surname="Grad",
            given_name="2",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="believer",
            education_status="graduated",
            is_graduated=True,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=11,
            surname="Grad",
            given_name="3",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="seeker",
            education_status="graduated",
            is_graduated=True,
            is_present=True,
            prep_attended=False,
        ),
        GroupMember(
            id=12,
            surname="Grad",
            given_name="4",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="seeker",
            education_status="graduated",
            is_graduated=True,
            is_present=True,
            prep_attended=False,
        ),
    ]


@pytest.fixture
def absent_members(sample_members):
    """Create a copy of sample members with some marked as absent."""
    # Create new instances with modified is_present values
    absent = []
    for i, m in enumerate(sample_members):
        # Mark Member2 (index 4) and Grad1 (index 9) as absent
        is_present = False if i in [4, 9] else m.is_present
        absent.append(
            GroupMember(
                id=m.id,
                surname=m.surname,
                given_name=m.given_name,
                role=m.role,
                gender=m.gender,
                faith_status=m.faith_status,
                education_status=m.education_status,
                is_graduated=m.is_graduated,
                is_present=is_present,
                prep_attended=m.prep_attended,
            )
        )
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
        GroupMember(
            id=1,
            surname="Leader",
            given_name="1",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=2,
            surname="Member",
            given_name="1",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
    ]
    with pytest.raises(ValueError):
        divide_into_groups(few_members, num_groups=1)

    # Test with no leaders
    no_leaders = [
        GroupMember(
            id=i,
            surname="Member",
            given_name=str(i),
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        )
        for i in range(1, 8)
    ]
    with pytest.raises(ValueError):
        divide_into_groups(no_leaders, num_groups=1)

    # Test with all members absent
    all_absent = [
        GroupMember(
            id=1,
            surname="Leader",
            given_name="1",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=False,
            prep_attended=True,
        ),
        GroupMember(
            id=2,
            surname="Member",
            given_name="1",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=False,
            prep_attended=True,
        ),
        GroupMember(
            id=3,
            surname="Member",
            given_name="2",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=False,
            prep_attended=True,
        ),
    ]
    with pytest.raises(ValueError):
        divide_into_groups(all_absent, num_groups=1)


def test_group_size_constraints(sample_members):
    """Test that groups respect minimum size constraint of 4 members."""
    groups = divide_into_groups(sample_members, num_groups=2)

    for group in groups:
        assert (
            len(group.members) >= 4
        ), f"Group has fewer than 4 members: {len(group.members)}"


def test_target_size_behavior(sample_members):
    """Test that groups respect target size preferences while maintaining other constraints."""
    # Test with target size of 9
    groups_large = divide_into_groups(sample_members, num_groups=1, target_size=9)

    # Test with target size of 5
    groups_small = divide_into_groups(sample_members, num_groups=2, target_size=5)

    # Groups should still maintain minimum size of 4
    for group in groups_large + groups_small:
        assert len(group.members) >= 4, "Groups must have at least 4 members"

    # When target size is large, we should get fewer groups
    assert len(groups_large) <= len(
        groups_small
    ), "Larger target size should result in fewer groups"

    # Check that each non-graduated group still has at least one leader
    for group in groups_large + groups_small:
        if not any(m.is_graduated for m in group.members):
            assert any(
                m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
                for m in group.members
            ), "Non-graduate groups must have at least one leader"


def test_diversity_score_with_target_size():
    """Test that diversity score calculation properly accounts for target size."""
    members = [
        GroupMember(
            id=1,
            surname="Leader",
            given_name="1",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=2,
            surname="Member",
            given_name="1",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=3,
            surname="Member",
            given_name="2",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=4,
            surname="Member",
            given_name="3",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=5,
            surname="Member",
            given_name="4",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=6,
            surname="Member",
            given_name="5",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=7,
            surname="Member",
            given_name="6",
            role=MemberRole.REGULAR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=8,
            surname="Member",
            given_name="7",
            role=MemberRole.REGULAR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
    ]

    # Create two groups with different sizes
    group_small = Group(members=members[:4])  # 4 members
    group_large = Group(members=members[:8])  # 8 members

    # Test with target size of 4
    score_target_4_small = group_small.calculate_diversity_score(target_size=4)
    score_target_4_large = group_large.calculate_diversity_score(target_size=4)

    # Test with target size of 8
    score_target_8_small = group_small.calculate_diversity_score(target_size=8)
    score_target_8_large = group_large.calculate_diversity_score(target_size=8)

    # Group matching target size should score better than group deviating from target
    assert (
        score_target_4_small > score_target_4_large
    ), "Group matching target size 4 should score better"
    assert (
        score_target_8_large > score_target_8_small
    ), "Group matching target size 8 should score better"


def test_large_group_formation():
    """Test that the system can form large groups when appropriate."""
    # Create a larger set of members that would traditionally be split into 3 groups
    members = [
        # Leaders
        GroupMember(
            id=1,
            surname="Leader",
            given_name="1",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=2,
            surname="Leader",
            given_name="2",
            role=MemberRole.COUNSELOR,
            gender="F",
            faith_status="seeker",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        GroupMember(
            id=3,
            surname="Leader",
            given_name="3",
            role=MemberRole.FACILITATOR,
            gender="M",
            faith_status="believer",
            education_status="undergraduate",
            is_graduated=False,
            is_present=True,
            prep_attended=True,
        ),
        # Regular members with mixed gender and faith status
        *[
            GroupMember(
                id=i,
                surname="Member",
                given_name=str(i - 3),
                role=MemberRole.REGULAR,
                gender="M" if i % 2 == 0 else "F",
                faith_status="believer" if i % 3 == 0 else "seeker",
                education_status="undergraduate",
                is_graduated=False,
                is_present=True,
                prep_attended=True,
            )
            for i in range(4, 19)  # 15 regular members
        ],
    ]

    # Request 2 large groups instead of 3 smaller ones
    groups = divide_into_groups(members, num_groups=2, target_size=9)

    # We should get 2 groups
    assert len(groups) == 2, "Should form exactly 2 groups when requested"

    # Groups should be relatively balanced in size
    group_sizes = [len(g.members) for g in groups]
    assert max(group_sizes) - min(group_sizes) <= 2, "Group sizes should be balanced"

    # Each group should still maintain diversity and leader requirements
    for group in groups:
        # Check leader presence
        assert any(
            m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
            for m in group.members
        ), "Each group must have at least one leader"

        # Check gender diversity
        genders = {m.gender for m in group.members}
        assert len(genders) > 1, "Groups should maintain gender diversity"

        # Check faith status diversity
        faith_statuses = {m.faith_status for m in group.members}
        assert len(faith_statuses) > 1, "Groups should maintain faith status diversity"
