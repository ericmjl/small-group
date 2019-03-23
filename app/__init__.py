from collections import defaultdict

from bokeh.embed import components
from bokeh import __version__ as bkversion
from flask import Flask, redirect, render_template, request
from functools import partial

# from member import Member
from .smallgroup import SmallGroup
from .database import db
from .models import Lamb
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

import os
import psycopg2
import pandas as pd
import holoviews as hv
import janitor  # noqa: F401

render_template = partial(render_template, bkversion=bkversion)

renderer = hv.renderer("bokeh")

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_PASS = os.getenv("DB_PASS")
DB_USER = os.getenv("DB_USER")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
dsn = f"postgres://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = dsn
db.init_app(app)

# We have a psycopg2 connection because the holoviews plots are best done
# using pandas, and pandas read_sql requires a connection.
conn = psycopg2.connect(dsn=dsn)


GENDERS = ["M", "F"]
FAITH_STATUSES = ["baptized", "believer", "seeker", "unknown"]
ROLES = ["counselor", "facilitator", "none"]
MEMBER_SIGNATURE = [
    "given_name",
    "surname",
    "gender",
    "faith_status",
    "role",
    "notes",
    "active",
]


def members_summary():
    """
    A helper function that summarizes the members' data.

    Returns the set of bokeh plots to show on the main interface.
    """
    data = pd.read_sql("select * from lambs", con=conn).query(
        'active == "true"'
    )

    gdata = pd.DataFrame(data.groupby("gender").size()).rename_column(
        0, "count"
    )
    fdata = pd.DataFrame(data.groupby("faith_status").size()).rename_column(
        0, "count"
    )
    rdata = pd.DataFrame(data.groupby("role").size()).rename_column(0, "count")

    pg = hv.Bars(gdata, kdims="gender", vdims="count")
    pf = hv.Bars(fdata, kdims="faith_status", vdims="count")
    pr = hv.Bars(rdata, kdims="role", vdims="count")

    hvpg = renderer.get_plot(pg).state
    hvpf = renderer.get_plot(pf).state
    hvpr = renderer.get_plot(pr).state

    pg_script, pg_div = components(hvpg)
    pf_script, pf_div = components(hvpf)
    pr_script, pr_div = components(hvpr)

    bk = defaultdict(dict)
    bk["pg"]["script"] = pg_script
    bk["pg"]["div"] = pg_div
    bk["pr"]["script"] = pr_script
    bk["pr"]["div"] = pr_div
    bk["pf"]["script"] = pf_script
    bk["pf"]["div"] = pf_div

    return bk


def split_members_by_active():
    active = Lamb.query.filter(Lamb.active == "true")
    inactive = Lamb.query.filter(Lamb.active == "false")

    return active, inactive


@app.route("/")
def main():
    """
    The main page. Lists all the group members.
    """
    all_members = Lamb.query.all()
    active, inactive = split_members_by_active()
    return render_template(
        "index.html.j2",
        all_members=all_members,
        active=active,
        inactive=inactive,
    )


@app.route("/archive/<int:id>", methods=["POST"])
def archive(id):
    """
    Archives the member.
    """
    member = Lamb.query.filter(Lamb.id == id).first()
    member.active = False
    db.session.commit()
    return redirect("/")


@app.route("/activate/<int:id>", methods=["POST"])
def activate(id):
    """
    Activates the member.
    """
    member = Lamb.query.filter(Lamb.id == id).first()
    member.active = True
    db.session.commit()
    return redirect("/")


@app.route("/view_member/<int:id>", methods=["POST"])
def view_member(id):
    member = Lamb.query.filter(Lamb.id == id).first()
    return render_template(
        "form.html.j2",
        member=member,
        faith_statuses=FAITH_STATUSES,
        roles=ROLES,
    )


@app.route("/update_member/<int:id>", methods=["POST"])
def update_member(id):
    data = request.form
    member = Lamb.query.get(id)
    # Update the data based on what fields each member is supposed to have.
    for k in MEMBER_SIGNATURE:
        setattr(member, k, data[k])

    # Do a check on the value for "active".
    if data["active"] == "true":
        member.active = True
    elif data["active"] == "false":
        member.active = False

    # Now, commit the data.
    db.session.commit()
    return redirect("/")


@app.route("/add")
def add():
    """
    The page used to add one member to the group.
    """
    return render_template(
        "form.html.j2", member=None, faith_statuses=FAITH_STATUSES, roles=ROLES
    )


@app.route("/add_member", methods=["POST"])
def add_member():
    """
    Adds a member to the database.
    """
    data = dict()
    data["id"] = len(Lamb.query.all())
    # Grab out data from form.
    for s in MEMBER_SIGNATURE:
        data[s] = request.form[s]

    # Construct new member.
    member = Lamb(**data)
    print(member.__dict__)

    # Add to database.
    db.session.add(member)
    db.session.commit()

    return redirect("/")


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    """
    Deletes a member from the database.
    """
    # Taken from: https://stackoverflow.com/a/27159298/1274908
    Lamb.query.filter(Lamb.id == id).delete()
    db.session.commit()
    return redirect("/")


def has_one_believer(members):
    """
    Checks to ensure that there is at least one baptized believer available.
    """
    has_believer = False
    for member in members:
        if member.faith_status == "baptized":
            has_believer = True
    return has_believer


def has_one_facilitator(members):
    """
    Checks to ensure that there is at least one facilitator available.
    """
    has_facilitator = False
    for member in members:
        if member.role == "facilitator":
            has_facilitator = True
    return has_facilitator


@app.route("/shuffle", methods=["POST"])
def shuffle():
    """
    Shuffles the members that are checked.
    """
    present_ids = []
    for k, v in request.form.items():
        present_ids.append(v)

    members = []
    for id in present_ids:
        members.append(Lamb.query.get(id))

    # Check to make sure that there is at least one believer.
    try:
        assert has_one_believer(members)
    except AssertionError:
        error_msg = "There are no baptized disciples to lead Bible study."
        return render_template("error.html.j2", error_msg=error_msg)

    try:
        assert has_one_facilitator(members)
    except AssertionError:
        error_msg = "There are no facilitators to lead BIble study."
        return render_template("error.html.j2", error_msg=error_msg)

    # Check to make sure that there are at least 6 people, because otherwise,
    # shuffling is unnecessary.
    try:
        assert len(members) > 5
        g = SmallGroup(members)
        g.distribute_group_members()
        print(g.groups)
        return render_template("shuffle.html.j2", groups=g.groups)

    except AssertionError:
        error_msg = "There are fewer than 6 people; no need to shuffle."
        return render_template("error.html.j2", error_msg=error_msg)


@app.route("/data")
def data():
    """
    View page for the data.
    """
    bokehplots = members_summary()
    return render_template(
        "data.html.j2", bokehplots=bokehplots,
    )
