import panel as pn
import param


from dotenv import load_dotenv

load_dotenv()

import os

import pandas as pd
import psycopg2
from psycopg2.extensions import parse_dsn
import janitor

con = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)


lambs = pd.read_sql("select * from lambs", con=con).concatenate_columns(
    ["given_name", "surname"], sep=" ", new_column_name="name"
)


lambs_table = pn.widgets.DataFrame(lambs, height=300)

class SmallGroupDivider(param.Parameterized):
    lambs = param.DataFrame(default=lambs)

    def lambs_table(self):
        text = pn.pane.Markdown("# Lambs")
        table = pn.widgets.DataFrame(self.lambs, height=300)
        layout = pn.Column(text, table)
        return layout

sg = SmallGroupDivider()
pn.panel(sg.lambs_table).servable()

