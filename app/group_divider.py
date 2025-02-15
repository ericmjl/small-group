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
        self, all_groups: List["Group"] | None = None
    ) -> float:
        """
        Calculate Shannon Diversity Index for gender and faith_status combined,
        with penalties for:
        1. Oversized groups (>8 members)
        2. Size imbalance between groups (if all_groups is provided)
        3. Prep attendance imbalance between groups
        4. Leader density imbalance (too many leaders in one group)

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
    groups: List[Group], max_iterations: int = 1000, temperature: float = 0.1
) -> List[Group]:
    """
    Balance gender distribution in non-graduate groups through stochastic swaps using
    Metropolis-Hastings acceptance criteria. Only swaps members with identical status
    (prep attendance and leadership role) between different gender but within non-graduate groups.

    :param groups: List of groups to balance
    :param max_iterations: Maximum number of swap attempts
    :param temperature: Temperature parameter for Metropolis-Hastings (higher = more likely to accept worse swaps)
    :return: List of balanced groups
    """
    logger.info(f"Starting gender balancing with {max_iterations} iterations")

    def get_member_ids(groups: List[Group]) -> Set[int]:
        """Get set of all member IDs across all groups."""
        return {m.id for g in groups for m in g.members}

    def has_duplicates(groups: List[Group]) -> bool:
        """Check if any member appears in multiple groups."""
        all_ids = []
        for g in groups:
            all_ids.extend(m.id for m in g.members)
        return len(all_ids) != len(set(all_ids))

    def can_swap(m1: GroupMember, m2: GroupMember) -> bool:
        """Check if two members can be swapped.

        Rules:
        1. Different genders
        2. Same exact role (counselor with counselor, facilitator with facilitator, regular with regular)
        3. Same prep attendance status
        4. Both non-graduates
        """
        return (
            m1.gender != m2.gender
            and m1.role == m2.role  # Must be exact same role
            and m1.prep_attended == m2.prep_attended
            and not m1.is_graduated
            and not m2.is_graduated
        )

    def is_non_graduate_group(group: Group) -> bool:
        """Determine if a group is considered a non-graduate group.
        A group is non-graduate if all regular members (excluding leaders/counselors) are students.
        """
        # Get regular members (non-leaders)
        regular_members = [m for m in group.members if m.role == MemberRole.REGULAR]

        if not regular_members:  # If no regular members, consider it non-graduate
            return True

        # Check if any regular member is graduated
        return not any(m.is_graduated for m in regular_members)

    def calculate_gender_entropy(groups: List[Group]) -> float:
        """Calculate Shannon entropy of gender distribution and counselor distribution
        for each non-graduate group."""
        # First check for duplicates - return very low entropy if duplicates found
        if has_duplicates(groups):
            return float("-inf")

        total_entropy = 0.0
        for group in groups:
            # Skip graduate groups
            if not is_non_graduate_group(group):
                continue

            # Gender entropy
            males = sum(1 for m in group.members if m.gender == "M")
            females = sum(1 for m in group.members if m.gender == "F")
            total = males + females

            if total > 0:
                p_male = males / total
                p_female = females / total
                # Calculate entropy, handling edge cases where p = 0
                group_entropy = 0.0
                if p_male > 0:
                    group_entropy -= p_male * ln(p_male)
                if p_female > 0:
                    group_entropy -= p_female * ln(p_female)
                total_entropy += group_entropy

            # Counselor balance entropy
            # We want to balance male/female counselors within each group
            male_counselors = sum(
                1
                for m in group.members
                if m.gender == "M" and m.role == MemberRole.COUNSELOR
            )
            female_counselors = sum(
                1
                for m in group.members
                if m.gender == "F" and m.role == MemberRole.COUNSELOR
            )
            total_counselors = male_counselors + female_counselors

            if total_counselors > 0:
                p_male_counselor = male_counselors / total_counselors
                p_female_counselor = female_counselors / total_counselors
                counselor_entropy = 0.0
                if p_male_counselor > 0:
                    counselor_entropy -= p_male_counselor * ln(p_male_counselor)
                if p_female_counselor > 0:
                    counselor_entropy -= p_female_counselor * ln(p_female_counselor)
                # Weight counselor entropy equally with gender entropy
                total_entropy += counselor_entropy

        return total_entropy

    # Create a deep copy of groups to work with
    balanced_groups = [Group(members=list(group.members)) for group in groups]

    # Get non-graduate groups
    non_grad_groups = [
        (i, g) for i, g in enumerate(balanced_groups) if is_non_graduate_group(g)
    ]
    logger.info(f"Found {len(non_grad_groups)} non-graduate groups to balance")

    if len(non_grad_groups) < 2:
        logger.warning("Not enough non-graduate groups to perform balancing")
        return groups

    # Store initial member IDs to ensure no members are lost or duplicated
    initial_member_ids = get_member_ids(balanced_groups)

    current_entropy = calculate_gender_entropy(balanced_groups)
    best_entropy = current_entropy
    best_groups = balanced_groups.copy()
    logger.info(f"Initial entropy: {current_entropy}")

    # Add debug info about each group
    for i, group in enumerate(balanced_groups):
        grad_count = sum(1 for m in group.members if m.is_graduated)
        total = len(group.members)
        is_non_grad = is_non_graduate_group(group)
        logger.debug(
            f"Group {i+1}: {grad_count}/{total} graduates, considered non-grad: {is_non_grad}"
        )

    for iteration in range(max_iterations):
        if iteration % 100 == 0:
            logger.debug(f"Iteration {iteration}, current entropy: {current_entropy}")

        g1_idx, g1 = random.choice(non_grad_groups)
        g2_idx, g2 = random.choice(non_grad_groups)

        if g1_idx == g2_idx:
            continue

        # Try to find swappable members
        swappable_pairs = [
            (m1, m2) for m1 in g1.members for m2 in g2.members if can_swap(m1, m2)
        ]

        if not swappable_pairs:
            continue

        # Randomly select a swappable pair
        m1, m2 = random.choice(swappable_pairs)

        # Temporarily make the swap
        g1_members = [m2 if m == m1 else m for m in g1.members]
        g2_members = [m1 if m == m2 else m for m in g2.members]

        # Create temporary groups with the swap
        temp_groups = balanced_groups.copy()
        temp_groups[g1_idx] = Group(members=g1_members)
        temp_groups[g2_idx] = Group(members=g2_members)

        # Verify no members were lost or duplicated
        temp_member_ids = get_member_ids(temp_groups)
        if temp_member_ids != initial_member_ids:
            continue

        # Calculate new entropy
        new_entropy = calculate_gender_entropy(temp_groups)

        # Metropolis-Hastings acceptance criteria
        # Higher entropy is better (more balanced)
        delta_entropy = new_entropy - current_entropy

        # Always accept if better, otherwise use M-H criteria
        if delta_entropy > 0 or random.random() < exp(delta_entropy / temperature):
            balanced_groups = temp_groups
            current_entropy = new_entropy

            # Keep track of best solution seen
            if current_entropy > best_entropy:
                best_entropy = current_entropy
                best_groups = [Group(members=list(g.members)) for g in balanced_groups]
                logger.info(f"New best entropy found: {best_entropy}")

        # Anneal temperature (optional)
        temperature *= 0.999

    # Verify final groups have no duplicates
    if has_duplicates(best_groups):
        logger.error(
            "Duplicate members found in final groups, reverting to original groups"
        )
        return groups

    logger.info(f"Gender balancing complete. Final entropy: {best_entropy}")
    return best_groups


def divide_into_groups(
    members: List[GroupMember], num_groups: int, max_iterations: int = 1000
) -> List[Group]:
    """
    Divide members into groups using a deterministic approach.
    Target group size is 7 people.

    Distribution sequence:
    1. Calculate number of groups needed for target size of 7
    2. Distribute prep attendees first
    3. Randomly distribute leaders, ensuring each group gets one if possible
    4. Place graduates together in dedicated groups
    5. Distribute current students to remaining groups

    :param members: List of members to divide
    :param num_groups: Initial suggestion for number of groups (will be adjusted)
    :param max_iterations: Number of iterations for gender balancing (if > 0)
    :return: List of groups
    """
    # Filter for present members only
    present_members = [m for m in members if m.is_present]
    total_present = len(present_members)

    # Calculate number of groups needed for target size of 7
    TARGET_SIZE = 7
    num_groups = max(1, (total_present + TARGET_SIZE - 1) // TARGET_SIZE)

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

    # Second pass: try to give each group one counselor
    groups_without_counselors = [
        i
        for i, g in enumerate(groups)
        if not any(m.role == MemberRole.COUNSELOR for m in g.members)
    ]

    # Randomly assign one counselor to each group that needs one
    for group_idx in groups_without_counselors:
        if remaining_counselors:
            counselor = remaining_counselors.pop()
            groups[group_idx].members.append(counselor)
            assigned_members.add(counselor)

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

    # Fourth pass: distribute any remaining counselors evenly
    if remaining_counselors:
        # Sort groups by number of counselors (fewest first)
        available_groups = list(range(len(groups)))

        while remaining_counselors:
            # Sort groups by counselor count, then by total size for tiebreaking
            available_groups.sort(
                key=lambda i: (
                    sum(1 for m in groups[i].members if m.role == MemberRole.COUNSELOR),
                    len(groups[i].members),
                )
            )

            # Add counselor to group with fewest counselors
            group_idx = available_groups[0]
            counselor = remaining_counselors.pop()
            groups[group_idx].members.append(counselor)
            assigned_members.add(counselor)

    # 3. Handle remaining members
    unassigned = [m for m in present_members if m not in assigned_members]

    # Separate graduates and current students
    graduates = [m for m in unassigned if m.education_status == "graduated"]
    current_students = [m for m in unassigned if m.education_status != "graduated"]

    # Calculate how many graduate groups we need
    grad_group_size = TARGET_SIZE  # Target same size as regular groups
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
        groups = balance_gender_in_groups(groups, max_iterations)

    return groups
