import os
import os.path as op

from collections import Counter, defaultdict

from flask import Flask, render_template, request, redirect

from member import Member

from smallgroup import SmallGroup

from tinydb import Query, TinyDB

from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.embed import components

# Initial checks
# 1. Make sure there is a ".smallgroup/" directory under the home dir.
db_dir = op.join(os.environ['HOME'], '.smallgroup')
if not op.isdir(db_dir):
    os.mkdir(db_dir)

db_path = op.join(db_dir, 'members.json')

# 2. Make sure the data are synced.
os.system('bash sync.sh')

# Initialize the app with the database.
app = Flask(__name__)
db = TinyDB(db_path)

GENDERS = ['M', 'F']
FAITH_STATUSES = ['baptized', 'believer', 'seeker', 'unknown']
ROLES = ['counselor', 'facilitator', 'none']
MEMBER_SIGNATURE = ['name', 'surname', 'gender', 'faith_status', 'role',
                    'notes', 'active']


def members_summary():
    """
    A helper function that summarizes the members' data.

    Returns the set of bokeh plots to show on the main interface.
    """
    summary = defaultdict(Counter)
    fields_of_interest = ['gender', 'faith_status', 'role']
    for m in db.all():
        if m['active'] == 'true':
            for s in fields_of_interest:
                summary[s][m[s]] += 1
    print(summary)

    genders = {'xlabels': GENDERS}
    genders['data'] = []
    for g in GENDERS:
        genders['data'].append(summary['gender'][g])
    gdata = ColumnDataSource(genders)

    faith_statuses = {'xlabels': FAITH_STATUSES}
    faith_statuses['data'] = []
    for f in FAITH_STATUSES:
        faith_statuses['data'].append(summary['faith_status'][f])
    fdata = ColumnDataSource(faith_statuses)

    roles = {'xlabels': ROLES}
    roles['data'] = []
    for r in ROLES:
        roles['data'].append(summary['role'][r])
    rdata = ColumnDataSource(roles)
    print(roles)

    pg = figure(x_range=genders['xlabels'], plot_height=250, plot_width=250)
    pg.vbar(x='xlabels', source=gdata, width=0.4, top='data')
    pg_script, pg_div = components(pg)

    pf = figure(x_range=faith_statuses['xlabels'], plot_height=250,
                plot_width=250)
    pf.vbar(x='xlabels', source=fdata, width=0.4, top='data')
    pf_script, pf_div = components(pf)

    pr = figure(x_range=roles['xlabels'], plot_height=250, plot_width=250)
    pr.vbar(x='xlabels', top='data', source=rdata, width=0.4)
    pr_script, pr_div = components(pr)

    bk = defaultdict(dict)
    bk['pg']['script'] = pg_script
    bk['pg']['div'] = pg_div
    bk['pr']['script'] = pr_script
    bk['pr']['div'] = pr_div
    bk['pf']['script'] = pf_script
    bk['pf']['div'] = pf_div

    return bk


def split_members_by_active():
    m = Query()
    active = db.search(m.active == 'true')
    inactive = db.search(m.active == 'false' or m.active == 'none')

    return active, inactive


@app.route('/')
def main():
    """
    The main page. Lists all the group members.
    """
    active, inactive = split_members_by_active()
    bokehplots = members_summary()
    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           bokehplots=bokehplots)


@app.route('/archive/<int:id>', methods=['POST'])
def archive(id):
    """
    Archives the member.
    """
    db.update({'active': 'false'}, eids=[id])
    return redirect('/')


@app.route('/activate/<int:id>', methods=['POST'])
def activate(id):
    """
    Activates the member.
    """
    db.update({'active': 'true'}, eids=[id])
    return redirect('/')


@app.route('/view_member/<int:id>', methods=['POST'])
def view_member(id):
    member = db.get(eid=id)
    return render_template('form.html',
                           member=member,
                           faith_statuses=FAITH_STATUSES,
                           roles=ROLES)


@app.route('/update_member/<int:id>', methods=['POST'])
def update_member(id):
    for k, v in request.form.items():
        db.update({k: v}, eids=[id])
    return redirect('/')


@app.route('/add')
def add():
    """
    The page used to add one member to the group.
    """
    return render_template('form.html',
                           member=None,
                           faith_statuses=FAITH_STATUSES,
                           roles=ROLES)


@app.route('/add_member', methods=['POST'])
def add_member():
    """
    Adds a member to the database.
    """
    data = dict()
    for s in MEMBER_SIGNATURE:
        data[s] = request.form[s]
    db.insert(data)
    return redirect('/')


@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """
    Deletes a member from the database.
    """
    db.remove(eids=[id])
    return redirect('/')


def has_one_believer(members):
    """
    Checks to ensure that there is at least one baptized believer available.
    """
    has_believer = False
    for member in members:
        if member.faith_status == 'baptized':
            has_believer = True
    return has_believer


def has_one_facilitator(members):
    """
    Checks to ensure that there is at least one facilitator available.
    """
    has_facilitator = False
    for member in members:
        if member.role == 'facilitator':
            has_facilitator = True
    return has_facilitator


@app.route('/shuffle', methods=['POST'])
def shuffle():
    """
    Shuffles the members that are checked.
    """
    present_ids = []
    for k, v in request.form.items():
        present_ids.append(v)

    members = []
    for id in present_ids:
        member_data = db.get(eid=int(id))
        data = dict()

        for s in MEMBER_SIGNATURE[:-1]:
            data[s] = member_data[s]

        members.append(Member(**data))

    """Check to make sure that there is at least one believer."""
    try:
        assert has_one_believer(members)
    except AssertionError:
        error_msg = "There are no baptized disciples to lead Bible study."
        return render_template('error.html', error_msg=error_msg)

    try:
        assert has_one_facilitator(members)
    except AssertionError:
        error_msg = "There are no facilitators to lead BIble study."
        return render_template('error.html', error_msg=error_msg)

    try:
        assert len(members) > 5
        g = SmallGroup(members)
        g.distribute_group_members()
        print(g.groups)
        return render_template('shuffle.html', groups=g.groups)

    except AssertionError:
        error_msg = 'There are fewer than 6 people; no need to shuffle.'
        return render_template('error.html', error_msg=error_msg)


@app.route('/sync', methods=['POST'])
def sync():
    """
    Forces a sync of the database with GitHub.
    """
    os.system('bash sync.sh')
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7777)
