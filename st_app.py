import streamlit as st
import psycopg2
from psycopg2.extensions import parse_dsn
import os


@st.cache
def db_dsn():
    DB_NAME = os.getenv("DB_NAME")
    DB_PASS = os.getenv("DB_PASS")
    DB_USER = os.getenv("DB_USER")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    dsn = f"postgres://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return dsn

@st.cache
def connection_object():
    dsn = db_dsn()
    con = psycopg2.connect(**parse_dsn(dsn))
    return con


@st.cache
def applicant_data():
    df = pd.read_sql("select * from finaid_applications", con=con)
    return df


df = applicant_data()

st.dataframe(df)
