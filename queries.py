import streamlit as st
import pandas as pd
from utility_funcs import connection_object
import janitor  # noqa: F401


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
