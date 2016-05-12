from flask import Flask, render_template, request
from tinydb import TinyDB, Query
from member import Member
from smallgroup import SmallGroup
from collections import defaultdict, Counter

import os.path as op
import os

# Initial checks
# 1. Make sure there is a ".smallgroup/" directory under the home dir.
db_dir = op.join(os.environ['HOME'], '.smallgroup')
if not op.isdir(db_dir):
    os.mkdir(db_dir)

db_path = op.join(db_dir, 'members.json')

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
    M = Query()
    active = db.search(M.active == 'true')
    inactive = db.search(M.active == 'false' or M.active == 'none')

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
    # Membr = Query()  # calling it Membr so as not to reuse variable names
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

    g = SmallGroup(members)
    g.distribute_group_members()

    for i in range(1000):
        g.propose_swap()
    return render_template('shuffle.html', groups=g.groups)

if __name__ == '__main__':
    app.run(debug=True)
