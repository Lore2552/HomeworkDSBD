from flask import Blueprint, request, jsonify
from database import db
from models import User

user_bp = Blueprint('user_api', __name__)

@user_bp.route("/addUser", methods=["POST"])
def add_user():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")

    if not email:
        return {"error": "Email is required"}, 400

    if db.session.get(User, email):
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


@user_bp.route("/deleteUser", methods=["DELETE"])
def delete_user():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")
    if not email:
        return {"error": "Email is required"}, 400

    user = db.session.get(User, email)
    if not user:
        return {"error": "User not found"}, 404

    db.session.delete(user)
    db.session.commit()

    return {"message": "User deleted"}, 200


@user_bp.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200
