import os
from collections import Counter
from copy import copy
from random import sample
from typing import Dict, Iterator, List

import pandas as pd
import psycopg2
import streamlit as st


@st.cache
def db_dsn():
    DB_NAME = os.getenv("DB_NAME")
    DB_PASS = os.getenv("DB_PASS")
    DB_USER = os.getenv("DB_USER")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")

    return dict(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )


def connection_object():
    dsn = db_dsn()
    print(dsn)

    con = psycopg2.connect(**dsn)
    return con


def sdi(data):
    """ Given a hash { 'species': count } , returns the SDI
    >>> sdi({'a': 10, 'b': 20, 'c': 30,})
    1.0114042647073518"""

    from math import log as ln

    def p(n, N):
        """ Relative abundance """
        if n is 0:
            return 0
        else:
            return (float(n) / N) * ln(float(n) / N)

    N = sum(data.values())

    return -sum(p(n, N) for n in data.values() if n is not 0)


def assign_lambs(
    groups: Dict[int, pd.DataFrame],
    group_cycler: Iterator,
    lambs: pd.DataFrame,
) -> Dict[int, pd.DataFrame]:
    """
    Assign lambs to groups.
    """
    for r, lamb in lambs.iterrows():
        grp_num = next(group_cycler)
        groups[grp_num] = groups[grp_num].append(lamb)
    return groups


def group_sdi(group: pd.DataFrame) -> float:
    # Calculate SDI for one group only.
    genders = Counter(group["gender"])
    faith_statuses = Counter(group["faith_status"])
    roles = Counter(group["role"])
    family = Counter(group["family_head"])
    return sdi(genders) + sdi(faith_statuses) + sdi(roles) + sdi(family)


def total_sdi(groups: Dict[int, List[pd.DataFrame]]) -> float:
    # Calculate total SDI over all groups
    total_sdi: float = 0
    for num, group in groups.items():
        total_sdi += group_sdi(group)
    return total_sdi


def propose_swap(groups: Dict[int, List[pd.DataFrame]]) -> Dict:
    # Propose a swap between two groups
    proposed = copy(groups)
    grp1, grp2 = sample(groups.keys(), 2)
    m1 = groups[grp1].sample(1)
    m1name = m1.iloc[0]["name"]
    m2 = groups[grp2].sample(1)
    m2name = m2.iloc[0]["name"]

    proposed[grp1] = proposed[grp1].query("name != @m1name").append(m2)
    proposed[grp2] = proposed[grp2].query("name != @m2name").append(m1)
    return proposed
