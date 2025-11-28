from database import db

class User(db.Model):
    __tablename__ = "users"

    email = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    surname = db.Column(db.String(255), nullable=False)
    fiscal_code = db.Column(db.String(16), nullable=True)
    bank_info = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            "email": self.email,
            "name": self.name,
            "surname": self.surname,
            "fiscal_code": self.fiscal_code,
            "bank_info": self.bank_info,
        }


class MessageId(db.Model):
    __tablename__ = "message_ids"

    id = db.Column(db.String(36), primary_key=True)  # UUID format

    def to_dict(self):
        return {"id": self.id}
