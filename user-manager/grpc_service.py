import grpc
from concurrent import futures
import user_manager_pb2
import user_manager_pb2_grpc
from database import db
from models import User

class UserService(user_manager_pb2_grpc.UserServiceServicer):
    def __init__(self, app):
        self.app = app

    def CheckUser(self, request, context):
        with self.app.app_context():
            user = db.session.get(User, request.email)
            return user_manager_pb2.CheckUserResponse(exists=bool(user))

    def GetUser(self, request, context):
        with self.app.app_context():
            user = db.session.get(User, request.email)
            if user:
                return user_manager_pb2.GetUserResponse(
                    email=user.email,
                    name=user.name,
                    surname=user.surname,
                    fiscal_code=user.fiscal_code or "",
                    bank_info=user.bank_info or "",
                    found=True
                )
            else:
                return user_manager_pb2.GetUserResponse(found=False)

def serve_grpc(app):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_manager_pb2_grpc.add_UserServiceServicer_to_server(UserService(app), server)
    server.add_insecure_port("[::]:50051")
    print("gRPC server started on port 50051")
    server.start()
    server.wait_for_termination()
