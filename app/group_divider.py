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
    name: str
    role: MemberRole
    gender: str
    faith_status: str
    is_graduated: bool
    is_present: bool


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
    Handles graduated and non-graduated members separately.

    Each group must have:
    - At least one leader (facilitator or counselor)
    - Between 4-7 members total
    - Leaders evenly distributed among non-graduated groups

    :param members: List of members to divide
    :param num_groups: Number of groups to create (will be adjusted based on constraints)
    :param max_iterations: Maximum number of iterations for optimization
    :return: List of groups
    """
    # Filter for present members only
    present_members = [m for m in members if m.is_present]
    total_present = len(present_members)

    # Separate graduated and non-graduated members
    graduated = [m for m in present_members if m.is_graduated]
    non_graduated = [m for m in present_members if not m.is_graduated]

    # Calculate number of groups needed for each category
    grad_groups = (len(graduated) + 6) // 7  # Ceiling division for graduated members
    if grad_groups > 0 and len(graduated) < 4:
        grad_groups = 0  # Don't create a separate grad group if less than 4 members
        # Add graduated members to non_graduated for distribution
        non_graduated.extend(graduated)
        graduated = []

    nongrad_min_groups = (len(non_graduated) + 6) // 7  # Ceiling division
    nongrad_max_groups = len(non_graduated) // 4  # Floor division
    nongrad_groups = max(
        nongrad_min_groups, min(num_groups - grad_groups, nongrad_max_groups)
    )

    if nongrad_groups < 1:
        raise ValueError(
            f"Cannot create groups with {len(non_graduated)} non-graduated members. "
            "Need at least 4 members total."
        )

    # Get all leaders from non-graduated members and shuffle them
    leaders = [
        m
        for m in non_graduated
        if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
    ]
    random.shuffle(leaders)

    if not leaders and nongrad_groups > 0:
        raise ValueError("Cannot create non-graduated groups: no leaders are present")

    # Adjust number of non-graduated groups based on available leaders if necessary
    nongrad_groups = min(nongrad_groups, len(leaders))

    # Initialize groups
    groups = []

    # Create graduated groups if needed
    if grad_groups > 0:
        grad_group = Group(members=graduated)
        groups.append(grad_group)

    # Create and initialize non-graduated groups
    nongrad_group_list = [Group(members=[]) for _ in range(nongrad_groups)]

    # Distribute leaders among non-graduated groups
    for i, leader in enumerate(leaders):
        nongrad_group_list[i % nongrad_groups].members.append(leader)

    # Get remaining regular members
    regular_members = [m for m in non_graduated if m.role == MemberRole.REGULAR]

    # Optimization loop for non-graduated groups
    best_nongrad_groups = None
    best_diversity = float("-inf")

    for _ in range(max_iterations):
        # Create a new distribution
        current_groups = [
            Group(members=group.members[:]) for group in nongrad_group_list
        ]

        # Randomly distribute regular members
        remaining = regular_members.copy()
        random.shuffle(remaining)

        # Try to distribute members evenly first
        target_size = (len(non_graduated) + nongrad_groups - 1) // nongrad_groups

        for member in remaining:
            # Find groups that need more members to reach target size
            eligible_groups = [
                g for g in current_groups if len(g.members) < min(target_size, 7)
            ]

            if not eligible_groups:
                # If all groups reached target size, allow up to 7 members
                eligible_groups = [g for g in current_groups if len(g.members) < 7]
                if not eligible_groups:
                    break

            # Among eligible groups, pick the smallest one
            target_group = min(eligible_groups, key=lambda g: len(g.members))
            target_group.members.append(member)

        # Verify distribution is valid
        all_distributed = sum(len(g.members) for g in current_groups) == len(
            non_graduated
        )
        valid_sizes = all(4 <= len(g.members) <= 7 for g in current_groups)

        if all_distributed and valid_sizes:
            total_diversity = sum(g.calculate_diversity_score() for g in current_groups)
            if total_diversity > best_diversity:
                best_diversity = total_diversity
                best_nongrad_groups = current_groups

    if best_nongrad_groups is None:
        raise ValueError(
            "Could not find a valid distribution satisfying all constraints. "
            f"Try adjusting the number of groups (currently {nongrad_groups}) "
            f"for {len(non_graduated)} non-graduated members."
        )

    # Combine graduated and non-graduated groups
    groups.extend(best_nongrad_groups)
    return groups
