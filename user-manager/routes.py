from flask import Blueprint, request, jsonify
from database import db
from models import User, MessageId
import grpc
import user_manager_pb2
import user_manager_pb2_grpc
from datetime import datetime,timedelta
from metrics import USER_REGISTRATION_ERRORS_TOTAL, HOSTNAME, SERVICE_NAME

user_bp = Blueprint('user_api', __name__)

@user_bp.route("/addUser", methods=["POST"])
def add_user():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400
    
    message_id = data.get("message_id")
    if not message_id:
        return {"error": "Message ID is required"}, 400

    email = data.get("email")
    if not email:
        return {"error": "Email is required"}, 400

    
    cached_msg = db.session.query(MessageId).filter_by(id=message_id).first()
    if cached_msg:
        return cached_msg.response_data, cached_msg.response_status
    
    try:
        existing_user = db.session.query(User).filter_by(email=email).first()
        if existing_user:
            response_body = {"error": "User already exists"}
            status_code = 409
            USER_REGISTRATION_ERRORS_TOTAL.labels(service=SERVICE_NAME, node=HOSTNAME, error_type="user_exists").inc()
        else:
            fiscal_code = data.get("fiscal_code")
            existing_cf = None
            if fiscal_code:
                existing_cf = db.session.query(User).filter_by(fiscal_code=fiscal_code).first()

            if existing_cf:
                response_body = {"error": "Fiscal code already used by another user"}
                status_code = 409
                USER_REGISTRATION_ERRORS_TOTAL.labels(service=SERVICE_NAME, node=HOSTNAME, error_type="fiscal_code_exists").inc()
            else:
                # CREO UTENTE
                user = User(
                    email=email,
                    name=data.get("name"),
                    surname=data.get("surname"),
                    fiscal_code=fiscal_code,
                    bank_info=data.get("bank_info"),
                )
                db.session.add(user)

                response_body = {"message": "User created"}
                status_code = 201

        expiration_time = datetime.now() + timedelta(minutes=5)
        message_record = MessageId(
            id=message_id,
            response_data=response_body,
            response_status=status_code,
            expires_at=expiration_time
        )
        db.session.add(message_record)
        db.session.commit()

        return response_body, status_code
    
    except Exception as e:
        db.session.rollback()
        USER_REGISTRATION_ERRORS_TOTAL.labels(service=SERVICE_NAME, node=HOSTNAME, error_type="internal_server_error").inc()
        return {"error": f"Internal Server Error: {str(e)}"}, 500

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

    try:
        with grpc.insecure_channel("data-collector:50052") as channel:
            stub = user_manager_pb2_grpc.CollectorServiceStub(channel)
            response = stub.CleanupUser(user_manager_pb2.CleanupUserRequest(email=email))
    except grpc.RpcError as e:
        print(f"Failed to notify data-collector cleanup via gRPC: {e.details()}")

    return {"message": "User deleted"}, 200


@user_bp.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@user_bp.route("/messageIds", methods=["GET"])
def get_message_ids():
    message_ids = MessageId.query.all()
    return jsonify([msg.to_dict() for msg in message_ids]), 200


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
