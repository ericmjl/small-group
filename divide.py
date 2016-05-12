# The problem we want to solve:
# Given the facilitators present today, divde the group into smaller groups
# that maximize diversity of gender, baptism status, and counselors.
# But also need to make sure that there's sufficient switching around.

import pandas as pd

from member import Member
from random import shuffle
from smallgroup import SmallGroup

# Make members_list
members = pd.read_csv('members.csv')
members = members[members['present_today'] == True]

members_list = []
for r, d in members.iterrows():
    m = Member(d['name'], d['surname'], d['gender'], d['faith_status'],
               d['role'], d['present_today'])
    members_list.append(m)
shuffle(members_list)

# Instantiate small group and make swaps.
g = SmallGroup(members_list)
g.distribute_group_members()

for i in range(500):
    g.propose_swap()
    # print(g.summed_shannon_diversity())

for k, v in g.groups.items():
    print(v)
    print('')
