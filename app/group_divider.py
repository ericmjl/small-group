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

    def calculate_diversity_score(
        self, all_groups: List["Group"] | None = None
    ) -> float:
        """
        Calculate Shannon Diversity Index for gender and faith_status combined,
        with penalties for:
        1. Oversized groups (>8 members)
        2. Size imbalance between groups (if all_groups is provided)

        :param all_groups: Optional list of all groups to calculate size balance penalty
        :return: Diversity score with penalties applied
        """
        if not self.members:
            return 0.0

        # Calculate base diversity score
        characteristics = [f"{m.gender}_{m.faith_status}" for m in self.members]
        counts = Counter(characteristics)
        total = len(characteristics)
        diversity = 0.0

        for count in counts.values():
            p = count / total
            diversity -= p * ln(p)

        # Apply size penalty for groups larger than 8
        # The penalty grows quadratically with size to strongly discourage large groups
        if len(self.members) > 8:
            size_penalty = ((len(self.members) - 8) ** 2) * 0.5
            diversity -= size_penalty

        # Apply size balance penalty if all groups are provided
        if all_groups:
            group_sizes = [len(g.members) for g in all_groups]
            avg_size = sum(group_sizes) / len(group_sizes)
            size_deviation = abs(len(self.members) - avg_size)
            # Quadratic penalty for deviating from average size
            balance_penalty = (size_deviation**2) * 0.3
            diversity -= balance_penalty

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
    with graduated members preferring to be together, but split into multiple groups
    if there are more than 8 graduated members.

    Each group must have:
    - At least one leader (facilitator or counselor)
    - Minimum of 4 members
    - Maximum of 8 members per group (enforced through diversity score penalty)
    - Leaders evenly distributed among all groups
    - Groups should be of similar size (enforced through diversity score penalty)

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

    # Calculate minimum number of groups needed based on total members
    min_groups_by_size = (total_present + 7) // 8

    # Adjust number of groups if we have enough leaders
    num_groups = min(len(leaders), max(num_groups, min_groups_by_size))

    if num_groups < 1:
        raise ValueError("Cannot create groups: no leaders are present")

    # Initialize groups
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

        # Handle graduated members based on their count
        grad_groups = []
        if len(graduated_regular) >= 4:
            # If we have more than 8 graduated members, create multiple groups
            num_grad_groups = (len(graduated_regular) + 7) // 8
            grad_group_size = len(graduated_regular) // num_grad_groups

            # Select random groups to be graduate groups
            available_group_indices = list(range(num_groups))
            random.shuffle(available_group_indices)
            grad_groups = available_group_indices[:num_grad_groups]

            # Distribute graduated members among grad groups
            random.shuffle(graduated_regular)
            for i, member in enumerate(graduated_regular):
                group_idx = grad_groups[i % num_grad_groups]
                current_groups[group_idx].members.append(member)

        # Now distribute non-graduated members among the remaining groups
        random.shuffle(non_graduated_regular)

        remaining_members = (
            non_graduated_regular
            if grad_groups  # If we created grad groups
            else graduated_regular + non_graduated_regular
        )

        # Distribute remaining members
        for member in remaining_members:
            if grad_groups and member in graduated_regular:
                continue

            # Find eligible groups (not the grad groups if we have them)
            eligible_groups = [
                g
                for i, g in enumerate(current_groups)
                if not grad_groups or i not in grad_groups
            ]

            # Calculate scores for each eligible group
            group_scores = []
            for group in eligible_groups:
                test_group = group.add_member(member)
                score = test_group.calculate_diversity_score(current_groups)
                group_scores.append((score, group))

            # Choose the group with the highest score
            _, target_group = max(group_scores, key=lambda x: x[0])
            target_group.members.append(member)

        # Verify distribution is valid
        all_distributed = sum(len(g.members) for g in current_groups) == total_present
        min_size_met = all(len(g.members) >= 4 for g in current_groups)

        if all_distributed and min_size_met:
            total_diversity = sum(
                g.calculate_diversity_score(current_groups) for g in current_groups
            )
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
