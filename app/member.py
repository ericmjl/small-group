class Member(object):
    """docstring for Member"""

    def __init__(
        self,
        given_name: str,
        surname: str,
        gender: str,
        faith_status: str,
        role: str,
        notes: str,
        id: int,
    ) -> None:
        super(Member, self).__init__()
        self.given_name = given_name
        self.surname = surname
        self.gender = gender
        self.faith_status = faith_status
        self.role = role
        self.notes = notes
        self.id = id

    def __repr__(self):
        return "{0} {1}".format(self.surname, self.name)
