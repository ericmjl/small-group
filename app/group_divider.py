from dataclasses import dataclass
from typing import List, Dict, Set
from enum import Enum
import random
from math import log as ln, exp
from collections import Counter
from loguru import logger


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


@dataclass(frozen=True)
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
    def leader_count(self) -> int:
        """Count total number of leaders (facilitators + counselors)."""
        return sum(
            1
            for m in self.members
            if m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
        )

    @property
    def prep_attended_count(self) -> int:
        return sum(1 for m in self.members if m.prep_attended)

    def calculate_diversity_score(
        self, all_groups: List["Group"] | None = None, target_size: int = 7
    ) -> float:
        """
        Calculate Shannon Diversity Index for gender, faith_status, and role combined,
        with penalties for:
        1. Oversized groups (>target_size+1 members)
        2. Size imbalance between groups (if all_groups is provided)
        3. Prep attendance imbalance between groups
        4. Leader density imbalance (too many leaders in one group)

        :param all_groups: Optional list of all groups to calculate size balance penalty
        :param target_size: Target size for each group (default: 7)
        :return: Diversity score with penalties applied
        """
        if not self.members:
            return 0.0

        # Calculate base diversity score
        characteristics = [
            f"{m.gender}_{m.faith_status}_{m.role.value}" for m in self.members
        ]
        counts = Counter(characteristics)
        total = len(characteristics)
        diversity = 0.0

        for count in counts.values():
            p = count / total
            diversity -= p * ln(p)

        # Apply size penalty for groups larger than target_size + 1
        # The penalty grows quadratically with size to discourage overly large groups
        if len(self.members) > target_size + 1:
            size_penalty = ((len(self.members) - (target_size + 1)) ** 2) * 0.5
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

            # Apply leader density penalty
            # Calculate the ideal leader ratio (total leaders / total members)
            total_leaders = sum(g.leader_count for g in all_groups)
            total_members = sum(len(g.members) for g in all_groups)
            ideal_leader_ratio = (
                total_leaders / total_members if total_members > 0 else 0
            )

            # Calculate this group's leader ratio
            group_leader_ratio = (
                self.leader_count / len(self.members) if self.members else 0
            )

            # Apply quadratic penalty for deviating from ideal ratio
            # Multiply by group size to penalize more for larger groups with bad ratios
            leader_ratio_deviation = abs(group_leader_ratio - ideal_leader_ratio)
            leader_density_penalty = (
                (leader_ratio_deviation**2) * len(self.members) * 0.6
            )
            diversity -= leader_density_penalty

        return diversity

    def add_member(self, member: GroupMember) -> "Group":
        return Group(members=self.members + [member])


def balance_gender_in_groups(
    groups: List[Group],
    max_iterations: int = 1000,
    temperature: float = 0.1,
    target_size: int = 7,
) -> List[Group]:
    """
    More efficient gender balancing algorithm that:
    1. Targets the most imbalanced groups for swaps
    2. Only attempts swaps between compatible members
    3. Uses early stopping when no improvements are found

    :param groups: List of groups to balance
    :param max_iterations: Maximum number of iterations
    :param temperature: Unused parameter, kept for backward compatibility
    :param target_size: Target size for each group (default: 7)
    :return: List of balanced groups
    """

    def get_gender_ratio(group: Group) -> float:
        """Calculate male/female ratio for a group. Returns male percentage."""
        males = sum(1 for m in group.members if m.gender == "M")
        total = len(group.members)
        return males / total if total > 0 else 0.5

    def get_group_imbalance(group: Group) -> float:
        """Calculate how far from 0.5 the gender ratio is."""
        return abs(get_gender_ratio(group) - 0.5)

    def calculate_total_imbalance(groups: List[Group]) -> float:
        """Calculate total gender imbalance across all groups."""
        return sum(get_group_imbalance(g) for g in groups)

    def find_swappable_pairs(
        g1: Group, g2: Group
    ) -> List[tuple[GroupMember, GroupMember]]:
        """Find all pairs of members that can be swapped between two groups."""
        pairs = []
        for m1 in g1.members:
            for m2 in g2.members:
                if (
                    m1.gender != m2.gender
                    and m1.role == m2.role  # Must be exact same role
                    and m1.prep_attended == m2.prep_attended
                    and not m1.is_graduated
                    and not m2.is_graduated
                ):
                    pairs.append((m1, m2))
        return pairs

    # Create a deep copy of groups to work with
    balanced_groups = [Group(members=list(group.members)) for group in groups]

    # Keep track of best solution
    best_groups = balanced_groups
    best_imbalance = calculate_total_imbalance(balanced_groups)

    # Counter for iterations without improvement
    stagnant_iterations = 0
    MAX_STAGNANT_ITERATIONS = 100  # Early stopping if no improvements

    for iteration in range(max_iterations):
        if stagnant_iterations >= MAX_STAGNANT_ITERATIONS:
            logger.info(
                f"Early stopping after {iteration} iterations - no recent improvements"
            )
            break

        # Sort groups by imbalance to focus on the most problematic ones
        group_imbalances = [
            (i, get_group_imbalance(g)) for i, g in enumerate(balanced_groups)
        ]
        group_imbalances.sort(key=lambda x: x[1], reverse=True)

        # Try to swap between the most imbalanced groups
        made_swap = False
        for i in range(len(group_imbalances) - 1):
            if made_swap:
                break

            g1_idx = group_imbalances[i][0]
            for j in range(i + 1, len(group_imbalances)):
                g2_idx = group_imbalances[j][0]

                # Find all possible swaps between these groups
                swappable_pairs = find_swappable_pairs(
                    balanced_groups[g1_idx], balanced_groups[g2_idx]
                )

                if not swappable_pairs:
                    continue

                # Try each possible swap
                for m1, m2 in swappable_pairs:
                    # Create temporary groups with the swap
                    temp_groups = [
                        Group(members=list(g.members)) for g in balanced_groups
                    ]

                    # Perform the swap
                    g1_members = [
                        m2 if m == m1 else m for m in temp_groups[g1_idx].members
                    ]
                    g2_members = [
                        m1 if m == m2 else m for m in temp_groups[g2_idx].members
                    ]
                    temp_groups[g1_idx] = Group(members=g1_members)
                    temp_groups[g2_idx] = Group(members=g2_members)

                    # Calculate new imbalance
                    new_imbalance = calculate_total_imbalance(temp_groups)

                    # Accept if better
                    if new_imbalance < best_imbalance:
                        best_imbalance = new_imbalance
                        best_groups = temp_groups
                        balanced_groups = temp_groups
                        made_swap = True
                        stagnant_iterations = 0
                        logger.debug(
                            f"Found better solution with imbalance {best_imbalance}"
                        )
                        break

                if made_swap:
                    break

        if not made_swap:
            stagnant_iterations += 1

    logger.info(f"Gender balancing complete. Final imbalance: {best_imbalance}")
    return best_groups


def divide_into_groups(
    members: List[GroupMember],
    num_groups: int,
    max_iterations: int = 1000,
    target_size: int = 7,
) -> List[Group]:
    """
    Divide members into groups using a deterministic approach.
    Target group size is configurable via target_size parameter.

    Distribution sequence:
    1. Calculate number of groups needed for target size
    2. Distribute prep attendees first
    3. Randomly distribute leaders, ensuring each group gets one if possible
    4. Place graduates together in dedicated groups
    5. Distribute current students to remaining groups

    :param members: List of members to divide
    :param num_groups: Initial suggestion for number of groups (will be adjusted)
    :param max_iterations: Number of iterations for gender balancing (if > 0)
    :param target_size: Target size for each group (default: 7)
    :return: List of groups
    """
    # Filter for present members only
    present_members = [m for m in members if m.is_present]
    total_present = len(present_members)

    # Calculate number of groups needed for target size
    min_groups = max(1, (total_present + target_size - 1) // target_size)
    max_groups = total_present // 2  # Don't allow groups smaller than 2 people

    # Use requested num_groups but keep it within reasonable bounds
    num_groups = max(min_groups, min(num_groups, max_groups))

    # Initialize groups
    groups = [Group(members=[]) for _ in range(num_groups)]

    # Helper function to find group with fewest members
    def find_smallest_group(groups: List[Group]) -> Group:
        return min(groups, key=lambda g: len(g.members))

    # Helper function to find group with fewest members that has no prep attendee
    def find_group_without_prep(groups: List[Group]) -> Group | None:
        no_prep_groups = [
            g for g in groups if not any(m.prep_attended for m in g.members)
        ]
        return (
            min(no_prep_groups, key=lambda g: len(g.members))
            if no_prep_groups
            else None
        )

    # Helper function to find group with fewest members that has no leader
    def find_group_without_leader(groups: List[Group]) -> Group | None:
        no_leader_groups = [
            g
            for g in groups
            if not any(
                m.role in (MemberRole.FACILITATOR, MemberRole.COUNSELOR)
                for m in g.members
            )
        ]
        return (
            min(no_leader_groups, key=lambda g: len(g.members))
            if no_leader_groups
            else None
        )

    # 1. First distribute prep attendees
    prep_attendees = [m for m in present_members if m.prep_attended]
    random.shuffle(prep_attendees)  # Randomly shuffle prep attendees

    # Calculate target number of prep attendees per group
    total_prep = len(prep_attendees)
    min_prep_per_group = total_prep // num_groups
    extra_prep = total_prep % num_groups

    # Initialize list of group indices and shuffle them for random distribution
    group_indices = list(range(num_groups))
    random.shuffle(group_indices)

    # First distribute minimum number of prep attendees to each group
    prep_index = 0
    for group_idx in group_indices:
        for _ in range(min_prep_per_group):
            if prep_index < len(prep_attendees):
                groups[group_idx].members.append(prep_attendees[prep_index])
                prep_index += 1

    # Distribute remaining prep attendees (the extras) randomly
    for i in range(extra_prep):
        if prep_index < len(prep_attendees):
            groups[group_indices[i]].members.append(prep_attendees[prep_index])
            prep_index += 1

    # Track who's been assigned
    assigned_members = set(prep_attendees)

    # 2. Distribute remaining leaders (facilitators and counselors)
    remaining_facilitators = [
        m
        for m in present_members
        if m.role == MemberRole.FACILITATOR and m not in assigned_members
    ]
    remaining_counselors = [
        m
        for m in present_members
        if m.role == MemberRole.COUNSELOR and m not in assigned_members
    ]

    # Randomly shuffle the leaders
    random.shuffle(remaining_facilitators)
    random.shuffle(remaining_counselors)

    # First pass: try to give each group one facilitator
    groups_without_facilitators = [
        i
        for i, g in enumerate(groups)
        if not any(m.role == MemberRole.FACILITATOR for m in g.members)
    ]

    # Randomly assign one facilitator to each group that needs one
    for group_idx in groups_without_facilitators:
        if remaining_facilitators:
            facilitator = remaining_facilitators.pop()
            groups[group_idx].members.append(facilitator)
            assigned_members.add(facilitator)

    # Second pass: distribute counselors evenly
    if remaining_counselors:
        # Calculate target number of counselors per group
        total_counselors = len(remaining_counselors)
        min_counselors_per_group = total_counselors // len(groups)
        extra_counselors = total_counselors % len(groups)

        # First ensure each group has the minimum number of counselors
        for group in groups:
            for _ in range(min_counselors_per_group):
                if remaining_counselors:
                    counselor = remaining_counselors.pop()
                    group.members.append(counselor)
                    assigned_members.add(counselor)

        # Then distribute extra counselors to groups with fewest total members
        if remaining_counselors:
            available_groups = list(range(len(groups)))
            while remaining_counselors and extra_counselors > 0:
                # Sort by total members
                available_groups.sort(key=lambda i: len(groups[i].members))
                group_idx = available_groups[0]
                counselor = remaining_counselors.pop()
                groups[group_idx].members.append(counselor)
                assigned_members.add(counselor)
                extra_counselors -= 1

    # Third pass: distribute any remaining facilitators
    if remaining_facilitators:
        # Get indices of groups sorted by size (smallest first)
        available_groups = list(range(len(groups)))
        random.shuffle(available_groups)  # Randomize order for equal-sized groups
        available_groups.sort(key=lambda i: len(groups[i].members))

        # Distribute remaining facilitators
        for facilitator in remaining_facilitators:
            group_idx = available_groups[0]  # Take the first (smallest) group
            groups[group_idx].members.append(facilitator)
            assigned_members.add(facilitator)

            # Re-sort available_groups by new group sizes
            available_groups.sort(key=lambda i: len(groups[i].members))

    # 3. Handle remaining members
    unassigned = [m for m in present_members if m not in assigned_members]

    # Separate graduates and current students
    graduates = [m for m in unassigned if m.education_status == "graduated"]
    current_students = [m for m in unassigned if m.education_status != "graduated"]

    # Calculate how many graduate groups we need
    grad_group_size = target_size  # Target same size as regular groups
    num_grad_groups = (len(graduates) + grad_group_size - 1) // grad_group_size

    if graduates:
        # Sort groups by number of graduates already in them (from prep/leader distribution)
        groups_by_grad_count = sorted(
            enumerate(groups),
            key=lambda x: sum(
                1 for m in x[1].members if m.education_status == "graduated"
            ),
            reverse=True,
        )

        # Select the groups that already have the most graduates to be graduate groups
        grad_group_indices = {idx for idx, _ in groups_by_grad_count[:num_grad_groups]}

        # Distribute graduates to graduate groups
        for member in graduates:
            # Find the graduate group with fewest members
            target_idx, target_group = min(
                ((i, g) for i, g in enumerate(groups) if i in grad_group_indices),
                key=lambda x: len(x[1].members),
            )
            target_group.members.append(member)
            assigned_members.add(member)

        # Now distribute current students to non-graduate groups
        non_grad_groups = [
            g for i, g in enumerate(groups) if i not in grad_group_indices
        ]

        # Keep track of distributed students to prevent duplicates
        distributed_students = set()

        if non_grad_groups:  # If we have non-graduate groups
            for student in current_students:
                if student not in distributed_students:
                    # Find the non-graduate group with fewest members
                    target_group = min(non_grad_groups, key=lambda g: len(g.members))
                    target_group.members.append(student)
                    assigned_members.add(student)
                    distributed_students.add(student)
        else:  # If all groups are graduate groups, distribute to minimize size differences
            for student in current_students:
                if student not in distributed_students:
                    target_group = find_smallest_group(groups)
                    target_group.members.append(student)
                    assigned_members.add(student)
                    distributed_students.add(student)
    else:
        # If no graduates, just distribute current students evenly
        distributed_students = set()
        for student in current_students:
            if student not in distributed_students:
                target_group = find_smallest_group(groups)
                target_group.members.append(student)
                assigned_members.add(student)
                distributed_students.add(student)

    # Apply gender balancing if max_iterations > 0
    if max_iterations > 0:
        groups = balance_gender_in_groups(
            groups, max_iterations=max_iterations, target_size=target_size
        )

    return groups
