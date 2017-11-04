import math
from collections import Counter, defaultdict
from random import choice, sample, shuffle

from sdi import sdi


class SmallGroup(object):
    """docstring for SmallGroup"""
    def __init__(self, members):
        super(SmallGroup, self).__init__()
        self.members = members
        self.groups = defaultdict(list)
        self.unassigned_members = members
        self.assigned_members = list()

    def group_shannon_diversity(self, criteria):
        """
        Criteria should be one of: 'gender', 'faith_status'
        """
        assert criteria in ['gender', 'faith_status', 'role']
        sdis = dict()
        for group, members in self.groups.items():
            genders = Counter(eval("[m.{0} for m in members]"
                                   .format(criteria)))
            sdis[group] = sdi(genders)

        return sdis

    def criteria_shannon_diversity(self, criteria):
        """
        Returns the summed SDIs for a given criteria.
        """
        sdis = self.group_shannon_diversity(criteria)
        return sum(sdis.values())

    def summed_shannon_diversity(self):
        criteria = ['gender', 'faith_status', 'role']
        sum_sdi = 0
        for c in criteria:
            sum_sdi += self.criteria_shannon_diversity(c)
        return sum_sdi

    def distribute_group_members(self):
        """
        Distributes the facilitators who are present.
        Then it distributes the other members.

        Returns nothing.
        """
        count = 0
        num_groups = math.ceil(len(self.members) / 5)
        print(num_groups)
        shuffle(self.unassigned_members)

        # First, assign facilitators amongst the groups.
        for m in self.unassigned_members:
            if ((m.role == 'facilitator' or m.role == 'counselor')
                    and (m not in self.assigned_members)
                    and (count < num_groups)):
                self.groups[count].append(m)
                self.assigned_members.append(m)
                count += 1

        self.unassigned_members = set(self.unassigned_members) -\
            set(self.assigned_members)
        self.unassigned_members = list(self.unassigned_members)

        count = 0
        shuffle(self.unassigned_members)
        for m in self.unassigned_members:
            remainder = count % len(self.groups)
            if m not in self.assigned_members:
                self.groups[remainder].append(m)
                count += 1

        for i in range(1000):
            print('Swap {0}'.format(i))
            self.propose_swap()
            print(self.summed_shannon_diversity())
            if not self.passed_rejection_criteria():
                print('not pass')
                self.propose_swap()

    def find_member(self, first_name):
        """
        Finds a member by their first name.
        """
        member = None
        for m in self.members:
            if m.name == first_name:
                member = m
        return member

    def passed_rejection_criteria(self):
        passed1 = self.two_members_not_in_same_group('Fang', 'Mengyi')
        passed2 = self.two_members_not_in_same_group('Yufeng', 'Jingyuan')

        return all([passed1, passed2])

    def two_members_not_in_same_group(self, mbr1, mbr2):
        passed = False
        member1 = self.find_member(mbr1)
        member2 = self.find_member(mbr2)

        if member1 and member2:
            for g, members in self.groups.items():
                has_member1 = member1 in members
                has_member2 = member2 in members
                if not has_member1 and has_member2:
                    passed = True
        else:
            passed = True

        return passed

    def propose_swap(self):
        """
        Constructs a proposed random swap.

        Computes summed SDI over each criteria, then sums all the SDI scores.
        If it increases sum of summed SDI, then accept proposed random swap.
        """
        curr_sum_sdi = self.summed_shannon_diversity()
        g1, g2 = sample(self.groups.keys(), 2)
        member1 = choice(self.groups[g1])
        member2 = choice(self.groups[g2])

        self.groups[g1].append(member2)
        self.groups[g1].remove(member1)
        self.groups[g2].append(member1)
        self.groups[g2].remove(member2)

        new_sum_sdi = self.summed_shannon_diversity()
        # Next line is the old version. Line after is the new one.
        if new_sum_sdi >= curr_sum_sdi and self.passed_rejection_criteria():
            return new_sum_sdi
        else:
            self.groups[g1].append(member1)
            self.groups[g2].remove(member1)
            self.groups[g1].remove(member2)
            self.groups[g2].append(member2)

            return curr_sum_sdi
