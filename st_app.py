import math
from collections import defaultdict
from itertools import cycle
from typing import Dict

import janitor  # noqa: F401
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from queries import query_families, query_lambs
from utility_funcs import assign_lambs, propose_swap, total_sdi

load_dotenv()


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

    # Firstly, assign facilitators and counselors
    groups = assign_lambs(groups, group_cycler, leaders)
    # Now, assign the rest of the lambs.
    followers = lambs.query("role not in ['facilitator', 'counselor']")
    groups = assign_lambs(groups, group_cycler, followers)

    # Calculate shannon diversity of groups
    # shannon diversity is computed over two columns: gender & faith status

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
