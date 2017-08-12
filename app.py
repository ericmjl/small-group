import os
import os.path as op

from collections import Counter, defaultdict

from flask import Flask, render_template, request

from member import Member

from smallgroup import SmallGroup

from tinydb import Query, TinyDB

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

FAITH_STATUSES = ['baptized', 'believer', 'seeker', 'unknown']
ROLES = ['counselor', 'facilitator', 'none']
MEMBER_SIGNATURE = ['name', 'surname', 'gender', 'faith_status', 'role',
                    'notes', 'active']


def members_summary():
    """
    A helper function that summarizes the members' data.
    """
    summary = defaultdict(Counter)
    for m in db.all():
        if m['active'] == 'true':
            for s in MEMBER_SIGNATURE[2:-2]:
                summary[s][m[s]] += 1
    return summary


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

    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           summary=members_summary())


@app.route('/archive/<int:id>', methods=['POST'])
def archive(id):
    """
    Archives the member.
    """
    db.update({'active': 'false'}, eids=[id])
    active, inactive = split_members_by_active()
    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           summary=members_summary())


@app.route('/activate/<int:id>', methods=['POST'])
def activate(id):
    """
    Activates the member.
    """
    db.update({'active': 'true'}, eids=[id])
    active, inactive = split_members_by_active()
    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           summary=members_summary())


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
        # print(k, v)
        db.update({k: v}, eids=[id])

    active, inactive = split_members_by_active()
    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           summary=members_summary())


@app.route('/add', methods=['POST'])
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
    # Add the new member to the database
    data = dict()
    for s in MEMBER_SIGNATURE:
        data[s] = request.form[s]
    db.insert(data)

    active, inactive = split_members_by_active()
    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           summary=members_summary())


@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """
    Deletes a member from the database.
    """
    db.remove(eids=[id])
    active, inactive = split_members_by_active()
    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           summary=members_summary())


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
    active, inactive = split_members_by_active()
    return render_template('index.html',
                           all_members=db.all(),
                           active=active,
                           inactive=inactive,
                           summary=members_summary())


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
