import os
import time
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import grpc
from concurrent import futures
import threading
import flight_service_pb2
import flight_service_pb2_grpc


app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/userdb")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
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


class UserService(flight_service_pb2_grpc.UserServiceServicer):
    def CheckUser(self, request, context):
        with app.app_context():
            user = db.session.get(User, request.email)
            return flight_service_pb2.CheckUserResponse(exists=bool(user))

    def GetUser(self, request, context):
        with app.app_context():
            user = db.session.get(User, request.email)
            if user:
                return flight_service_pb2.GetUserResponse(
                    email=user.email,
                    name=user.name,
                    surname=user.surname,
                    fiscal_code=user.fiscal_code or "",
                    bank_info=user.bank_info or "",
                    found=True
                )
            else:
                return flight_service_pb2.GetUserResponse(found=False)


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    flight_service_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port("[::]:50051")
    print("gRPC server started on port 50051")
    server.start()
    server.wait_for_termination()


@app.route("/users", methods=["POST"])
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


@app.route("/deleteUser", methods=["DELETE"])
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





@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    # Start gRPC server
    grpc_thread = threading.Thread(target=serve_grpc)
    grpc_thread.daemon = True
    grpc_thread.start()

    app.run(host="0.0.0.0", port=5000)
