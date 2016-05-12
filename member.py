class Member(object):
    """docstring for Member"""
    def __init__(self, name, surname, gender, faith_status, role, notes):
        super(Member, self).__init__()
        self.name = name
        self.surname = surname
        self.gender = gender
        self.faith_status = faith_status
        self.role = role
        self.notes = notes

    def __repr__(self):
        return "{0} {1}".format(self.surname, self.name)
