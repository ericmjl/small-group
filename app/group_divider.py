from dataclasses import dataclass
from typing import List, Dict, Set
from enum import Enum
import random
from math import log as ln
from collections import Counter


class MemberRole(str, Enum):
    FACILITATOR = "facilitator"
    COUNSELOR = "counselor"
    REGULAR = "regular"

    @classmethod
    def from_db_role(cls, role: str) -> "MemberRole":
        """Convert database role to MemberRole enum.

        :param role: Role string from database
        :return: Corresponding MemberRole enum value
        """
        role_map = {
            "facilitator": cls.FACILITATOR,
            "counselor": cls.COUNSELOR,
            "none": cls.REGULAR,
            "regular": cls.REGULAR,
        }
        return role_map.get(role.lower(), cls.REGULAR)


@dataclass
class GroupMember:
    id: int
    surname: str
    given_name: str
    role: MemberRole
    gender: str
    faith_status: str
    education_status: str
    is_graduated: bool
    is_present: bool

    @property
    def name(self) -> str:
        return f"{self.surname}{self.given_name}"


@dataclass
class Group:
    members: List[GroupMember]

    @property
    def has_facilitator(self) -> bool:
        return any(m.role == MemberRole.FACILITATOR for m in self.members)

    @property
    def counselor_count(self) -> int:
        return sum(1 for m in self.members if m.role == MemberRole.COUNSELOR)

    def calculate_diversity_score(self) -> float:
        """Calculate Shannon Diversity Index for gender and faith_status combined."""
        if not self.members:
            return 0.0

        # Combine gender and faith status into a single characteristic
        characteristics = [f"{m.gender}_{m.faith_status}" for m in self.members]
        counts = Counter(characteristics)

        total = len(characteristics)
        diversity = 0.0

        for count in counts.values():
            p = count / total
            diversity -= p * ln(p)

        return diversity

    def add_member(self, member: GroupMember) -> "Group":
        return Group(members=self.members + [member])


def divide_into_groups(
    members: List[GroupMember], num_groups: int, max_iterations: int = 1000
) -> List[Group]:
    """
    Divide members into groups optimizing for diversity and constraints.
    Leaders (counselors and facilitators) are distributed evenly across all groups
    regardless of their graduation status. Regular members are then distributed
    with graduated members preferring to be together.

    Each group must have:
    - At least one leader (facilitator or counselor)
    - Minimum of 4 members
    - Maximum of 7 members per group (can be exceeded only if necessary to ensure leader coverage)
    - Leaders evenly distributed among all groups

    :param members: List of members to divide
    :param num_groups: Number of groups to create (will be adjusted based on constraints)
    :param max_iterations: Maximum number of iterations for optimization
    :return: List of groups
    """
    # Filter for present members only
    present_members = [m for m in members if m.is_present]
    total_present = len(present_members)

    # First, separate leaders from regular members
    leaders = [
        m
        for m in present_members
        if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
    ]
    regular_members = [
        m
        for m in present_members
        if m.role not in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
    ]

    # Further separate regular members by graduation status
    graduated_regular = [
        m for m in regular_members if m.education_status == "graduated"
    ]
    non_graduated_regular = [
        m for m in regular_members if m.education_status != "graduated"
    ]

    # Number of groups cannot exceed number of leaders
    num_groups = min(num_groups, len(leaders))

    if num_groups < 1:
        raise ValueError("Cannot create groups: no leaders are present")

    # Calculate minimum number of groups needed based on total members
    min_groups_by_size = (total_present + 6) // 7  # Initial estimate

    # If we have fewer leaders than minimum groups needed, we'll have to exceed
    # the maximum group size to ensure leader coverage
    if num_groups < min_groups_by_size:
        print(
            f"Warning: Only {num_groups} leaders available for {total_present} members. "
            "Some groups will exceed the recommended maximum size to ensure leader coverage."
        )

    # Initialize groups with one leader each
    groups = [Group(members=[]) for _ in range(num_groups)]

    # First, distribute leaders evenly among all groups
    random.shuffle(leaders)
    for i, leader in enumerate(leaders):
        groups[i % num_groups].members.append(leader)

    # Optimization loop
    best_groups = None
    best_diversity = float("-inf")

    for _ in range(max_iterations):
        # Create a new distribution starting with the leader distribution
        current_groups = [Group(members=group.members[:]) for group in groups]

        # Handle graduated members first if there are enough of them
        if len(graduated_regular) >= 4:
            # Select a random group for graduated members
            grad_group_idx = random.randrange(num_groups)
            grad_group = current_groups[grad_group_idx]

            # Add all graduated members to this group
            for member in graduated_regular:
                grad_group.members.append(member)

        # Now distribute non-graduated members among the remaining groups
        random.shuffle(non_graduated_regular)

        # Calculate minimum members per group to ensure all members are distributed
        remaining_members = (
            non_graduated_regular
            if len(graduated_regular) >= 4
            else graduated_regular + non_graduated_regular
        )
        min_members_per_group = (len(remaining_members) + num_groups - 1) // num_groups

        # Distribute remaining members
        for member in remaining_members:
            if len(graduated_regular) >= 4 and member in graduated_regular:
                continue  # Skip graduated members as they've already been placed

            # Find the group with the fewest members that isn't the graduated group
            eligible_groups = [
                g
                for i, g in enumerate(current_groups)
                if (len(graduated_regular) < 4 or i != grad_group_idx)
            ]

            # Prioritize groups that haven't reached minimum size
            under_min_groups = [
                g for g in eligible_groups if len(g.members) < min_members_per_group
            ]
            target_groups = under_min_groups if under_min_groups else eligible_groups

            target_group = min(target_groups, key=lambda g: len(g.members))
            target_group.members.append(member)

        # Verify distribution is valid
        all_distributed = sum(len(g.members) for g in current_groups) == total_present
        min_size_met = all(len(g.members) >= 4 for g in current_groups)

        if all_distributed and min_size_met:
            total_diversity = sum(g.calculate_diversity_score() for g in current_groups)
            if total_diversity > best_diversity:
                best_diversity = total_diversity
                best_groups = current_groups

    if best_groups is None:
        raise ValueError(
            "Could not find a valid distribution satisfying all constraints. "
            f"Try adjusting the number of groups (currently {num_groups}) "
            f"for {total_present} members."
        )

    return best_groups
