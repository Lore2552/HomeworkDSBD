import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import grpc


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/userdb"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


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


@app.route("/users", methods=["POST"])
def add_user():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")

    if not email:
        return {"error": "Email is required"}, 400

    if User.query.get(email):
        return {"error": "User already exists"}, 409

    user = User(
        email=email,
        name=data.get("name"),
        surname=data.get("surname"),
        fiscal_code=data.get("fiscal_code"),
        bank_info=data.get("bank_info"),
    )

    db.session.add(user)
    db.session.commit()

    return {"message": "User created"}, 201


@app.route("/deleteUser", methods=["DELETE"])
def delete_user():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")
    if not email:
        return {"error": "Email is required"}, 400

    user = User.query.get(email)
    if not user:
        return {"error": "User not found"}, 404

    db.session.delete(user)
    db.session.commit()

    return {"message": "User deleted"}, 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
