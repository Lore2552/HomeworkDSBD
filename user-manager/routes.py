from flask import Blueprint, request, jsonify
from database import db
from models import User, MessageId
import grpc
import user_manager_pb2
import user_manager_pb2_grpc

user_bp = Blueprint('user_api', __name__)

@user_bp.route("/addUser", methods=["POST"])
def add_user():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")
    message_id = data.get("message_id")

    if not email:
        return {"error": "Email is required"}, 400

    if not message_id:
        return {"error": "Message ID (UUID) is required"}, 400

    # Check if message has already been processed (at most once semantics)
    existing_message = db.session.get(MessageId, message_id)
    if existing_message:
        return {"error": "Request already processed - user already registered"}, 409

    if db.session.get(User, email):
        return {"error": "User already exists"}, 409

    fiscal_code = data.get("fiscal_code")
    if fiscal_code:
        existing_cf = User.query.filter_by(fiscal_code=fiscal_code).first()
        if existing_cf:
            return {"error": "Fiscal code already used by another user"}, 409

    user = User(
        email=email,
        name=data.get("name"),
        surname=data.get("surname"),
        fiscal_code=fiscal_code,
        bank_info=data.get("bank_info"),
    )

    # Save the message ID to ensure idempotency
    message_record = MessageId(id=message_id)
    
    db.session.add(user)
    db.session.add(message_record)
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

    # Notify Data Collector to clean up user data via gRPC
    try:
        with grpc.insecure_channel("data-collector:50052") as channel:
            stub = user_manager_pb2_grpc.CollectorServiceStub(channel)
            response = stub.CleanupUser(user_manager_pb2.CleanupUserRequest(email=email))
            print(f"Data Collector cleanup response: {response.message}")
    except grpc.RpcError as e:
        print(f"Failed to notify data-collector cleanup via gRPC: {e.details()}")

    return {"message": "User deleted"}, 200


@user_bp.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

''' For testing
@user_bp.route("/messageIds", methods=["GET"])
def get_message_ids():
    message_ids = MessageId.query.all()
    return jsonify([msg.to_dict() for msg in message_ids]), 200
'''


@user_bp.route("/removeAirportInterest", methods=["DELETE"])
def remove_airport_interest():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")
    airport_code = data.get("airport_code")

    if not email or not airport_code:
        return {"error": "Email and airport_code are required"}, 400

    # Check if user exists
    user = db.session.get(User, email)
    if not user:
        return {"error": "User not found"}, 404

    # Notify Data Collector to remove airport interest via gRPC
    try:
        with grpc.insecure_channel("data-collector:50052") as channel:
            stub = user_manager_pb2_grpc.CollectorServiceStub(channel)
            response = stub.RemoveAirportInterest(
                user_manager_pb2.RemoveAirportInterestRequest(
                    email=email,
                    airport_code=airport_code
                )
            )
            
            if response.success:
                return {"message": response.message}, 200
            else:
                return {"error": response.message}, 400
    except grpc.RpcError as e:
        return {"error": f"Failed to remove airport interest: {e.details()}"}, 500
