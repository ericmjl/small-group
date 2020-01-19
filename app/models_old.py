from .database import db


class Lamb(db.Model):
    __tablename__ = "lambs"
    id = db.Column(db.Integer, primary_key=True)
    given_name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    gender = db.Column(db.String(1))
    faith_status = db.Column(db.String(8))
    role = db.Column(db.String(11))
    active = db.Column(db.Boolean)
    notes = db.Column(db.Text(1000))

    def __init__(
        self,
        id,
        given_name,
        surname,
        gender,
        faith_status,
        role,
        active,
        notes,
    ):
        self.id = id
        self.given_name = given_name
        self.surname = surname
        self.gender = gender
        self.faith_status = faith_status
        self.role = role
        if active == "true":
            self.active = True
        elif active == "false":
            self.active = False
        else:
            self.active = active
        self.notes = notes
