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
    prep_attended: bool

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

    @property
    def prep_attended_count(self) -> int:
        return sum(1 for m in self.members if m.prep_attended)

    def calculate_diversity_score(
        self, all_groups: List["Group"] | None = None
    ) -> float:
        """
        Calculate Shannon Diversity Index for gender and faith_status combined,
        with penalties for:
        1. Oversized groups (>8 members)
        2. Size imbalance between groups (if all_groups is provided)
        3. Prep attendance imbalance between groups

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

            # Apply prep attendance balance penalty
            prep_counts = [g.prep_attended_count for g in all_groups]
            avg_prep = sum(prep_counts) / len(prep_counts)
            prep_deviation = abs(self.prep_attended_count - avg_prep)
            # Quadratic penalty for deviating from average prep attendance
            prep_penalty = (prep_deviation**2) * 0.4
            diversity -= prep_penalty

        return diversity

    def add_member(self, member: GroupMember) -> "Group":
        return Group(members=self.members + [member])


def divide_into_groups(
    members: List[GroupMember], num_groups: int, max_iterations: int = 1000
) -> List[Group]:
    """
    Divide members into groups optimizing for diversity and constraints.
    The order of constraints is:
    1. Each group must have at least one member who attended Bible study prep
    2. Each group must have at least one leader (facilitator or counselor)
    3. Regular members are distributed with graduated members preferring to be together

    Each group must have:
    - At least one member who attended Bible study prep
    - At least one leader (facilitator or counselor)
    - Minimum of 4 members
    - Maximum of 8 members per group (enforced through diversity score penalty)
    - Leaders evenly distributed among all groups
    - Groups should be of similar size (enforced through diversity score penalty)
    - Prep attendees should be evenly distributed (enforced through diversity score penalty)

    :param members: List of members to divide
    :param num_groups: Number of groups to create (will be adjusted based on constraints)
    :param max_iterations: Maximum number of iterations for optimization
    :return: List of groups
    """
    # Filter for present members only
    present_members = [m for m in members if m.is_present]
    total_present = len(present_members)

    # First, separate prep attendees from others
    prep_attendees = [m for m in present_members if m.prep_attended]
    if not prep_attendees:
        raise ValueError("Cannot create groups: no members attended Bible study prep")

    # Then separate leaders from regular members
    leaders = [
        m
        for m in present_members
        if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
        and not m.prep_attended  # Exclude those who are both leaders and prep attendees
    ]
    regular_members = [
        m
        for m in present_members
        if m.role not in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
        and not m.prep_attended  # Exclude those who attended prep
    ]

    # Calculate minimum number of groups needed based on total members
    min_groups_by_size = (total_present + 7) // 8  # At most 8 members per group

    # Count total leaders (both prep and non-prep)
    total_leaders = len(leaders) + sum(
        1
        for m in prep_attendees
        if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
    )

    # Adjust number of groups based on constraints:
    # - Need enough groups to fit everyone (min_groups_by_size)
    # - Cannot have more groups than total leaders
    num_groups = min(
        total_leaders,  # Cannot have more groups than total leaders
        max(num_groups, min_groups_by_size),  # Must have enough groups to fit everyone
    )

    if num_groups < 1:
        raise ValueError(
            "Cannot create groups: insufficient members or constraints cannot be met"
        )

    # Initialize groups
    groups = [Group(members=[]) for _ in range(num_groups)]

    # First, distribute prep attendees evenly among all groups
    # Prioritize prep attendees who are also leaders
    prep_leaders = [
        m
        for m in prep_attendees
        if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
    ]
    prep_non_leaders = [
        m
        for m in prep_attendees
        if m.role not in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
    ]

    # Distribute prep leaders first
    random.shuffle(prep_leaders)
    for i, member in enumerate(prep_leaders):
        groups[i % num_groups].members.append(member)

    # Then distribute remaining prep attendees
    random.shuffle(prep_non_leaders)
    current_group = 0
    for member in prep_non_leaders:
        # Find the next group that doesn't have a prep attendee
        while current_group < num_groups and any(
            m.prep_attended for m in groups[current_group].members
        ):
            current_group += 1
        if current_group < num_groups:
            groups[current_group].members.append(member)

    # Then distribute remaining leaders
    random.shuffle(leaders)
    for i, leader in enumerate(leaders):
        # Find the group with the fewest leaders
        group_idx = min(
            range(num_groups),
            key=lambda i: sum(
                1
                for m in groups[i].members
                if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
            ),
        )
        groups[group_idx].members.append(leader)

    # Optimization loop for remaining members
    best_groups = None
    best_diversity = float("-inf")

    for _ in range(max_iterations):
        # Create a new distribution starting with the prep and leader distribution
        current_groups = [Group(members=group.members[:]) for group in groups]

        # Handle graduated members based on their count
        grad_groups = []
        graduated_regular = [
            m for m in regular_members if m.education_status == "graduated"
        ]
        non_graduated_regular = [
            m for m in regular_members if m.education_status != "graduated"
        ]

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
        prep_constraint_met = all(
            any(m.prep_attended for m in g.members) for g in current_groups
        )
        leader_constraint_met = all(
            any(
                m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
                for m in g.members
            )
            for g in current_groups
        )

        if (
            all_distributed
            and min_size_met
            and prep_constraint_met
            and leader_constraint_met
        ):
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
