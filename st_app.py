import math
import os
from collections import Counter, defaultdict
from copy import copy
from itertools import cycle
from random import sample
from typing import Iterator, Dict, List

import janitor  # noqa: F401
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

from sdi import sdi

load_dotenv()


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


@st.cache
def query_lambs():
    con = connection_object()
    df = pd.read_sql("select * from lambs", con=con)
    return df


@st.cache
def query_families():
    con = connection_object()
    families = pd.read_sql("select * from family", con=con)
    lambs = query_lambs()
    families = (
        families.merge(lambs, left_on="lamb", right_on="id", how="outer")
        .fillna(0)
        .select_columns(
            [
                "family_head",
                "given_name",
                "surname",
                "gender",
                "faith_status",
                "role",
                "active",
                "notes",
            ]
        )
    )
    return families


df = (
    query_lambs()
    .query("active == 'true'")
    .concatenate_columns(
        ["given_name", "surname"], sep=" ", new_column_name="name"
    )
)

families = query_families()
families
df = df.merge(families)

lambs = st.multiselect(
    label="Select those who are present today.", options=df["name"].values
)

n_steps = st.slider(
    "Number of steps", min_value=100, max_value=1000, value=500, step=100
)
shuffle = st.button("Shuffle lambs")

if shuffle:
    print("Lambs < 6")

    lambs = df.query("name in @lambs")
    st.dataframe(lambs)

    # Let's now get the groups divided.
    # Algorithm:
    # - take n group members
    # - divide into n_groups, which is n_lambs / 6 rounded up.

    leaders = lambs.query("role in ['facilitator', 'counselor']")
    num_groups = math.ceil(len(lambs) / 6)

    groups: Dict[int, pd.DataFrame] = defaultdict(pd.DataFrame)
    group_cycler = cycle(range(num_groups))

    def assign_lambs(
        groups: Dict[int, pd.DataFrame],
        group_cycler: Iterator,
        lambs: pd.DataFrame,
    ) -> Dict[int, pd.DataFrame]:
        for r, lamb in lambs.iterrows():
            grp_num = next(group_cycler)
            groups[grp_num] = groups[grp_num].append(lamb)
        return groups

    # Firstly, assign facilitators and counselors
    groups = assign_lambs(groups, group_cycler, leaders)
    # Now, assign the rest of the lambs.
    followers = lambs.query("role not in ['facilitator', 'counselor']")
    groups = assign_lambs(groups, group_cycler, followers)

    # Calculate shannon diversity of groups
    # shannon diversity is computed over two columns: gender & faith status

    def group_sdi(group: pd.DataFrame) -> float:
        # Calculate SDI for one group only.
        genders = Counter(group["gender"])
        faith_statuses = Counter(group["faith_status"])
        roles = Counter(group["role"])
        family = Counter(group["family_head"])
        return sdi(genders) + sdi(faith_statuses) + sdi(roles) + sdi(family)

    def total_sdi(groups: Dict[int, List[pd.DataFrame]]) -> float:
        # Calculate total SDI over all groups
        total_sdi = 0
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

    # Monte Carlo search through arrangements of people
    best_sdi = total_sdi(groups)
    pbar = st.progress(0)
    sdi_history = [best_sdi]

    def pbar_update(i: int, n_steps):
        return int(i * 100 / n_steps)

    for i in range(n_steps):

        proposed = propose_swap(groups)
        pbar.progress(pbar_update(i, n_steps))
        new_sdi = total_sdi(proposed)
        if new_sdi > best_sdi:
            best_sdi = new_sdi
            groups = proposed
        sdi_history.append(best_sdi)

    # Now, present groups
    for g, d in groups.items():
        st.header(f"Group {g}")
        st.dataframe(
            d.select_columns(
                ["given_name", "surname", "role", "gender", "family_head"]
            )
        )

    fig, ax = plt.subplots()
    ax.plot(sdi_history)
    st.pyplot(fig)
