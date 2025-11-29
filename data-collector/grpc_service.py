import grpc
from concurrent import futures
import user_manager_pb2
import user_manager_pb2_grpc
from database import db
from models import UserAirport

class CollectorService(user_manager_pb2_grpc.CollectorServiceServicer):
    def __init__(self, app):
        self.app = app

    def CleanupUser(self, request, context):
        from models import Flight  
        with self.app.app_context():
            try:
                user_airports = UserAirport.query.filter_by(user_email=request.email).all()
                deleted_flights = 0
                for ua in user_airports:
                    code = ua.airport_code
                    other = UserAirport.query.filter(
                        UserAirport.airport_code == code,
                        UserAirport.user_email != request.email
                    ).first()
                    if not other:
                        deleted_flights += Flight.query.filter_by(airport_monitored=code).delete()
                deleted_count = UserAirport.query.filter_by(user_email=request.email).delete()
                db.session.commit()
                return user_manager_pb2.CleanupUserResponse(
                    success=True,
                    message=f"Cleaned up {deleted_count} airport preferences and {deleted_flights} flights for user {request.email}"
                )
            except Exception as e:
                db.session.rollback()
                return user_manager_pb2.CleanupUserResponse(
                    success=False,
                    message=str(e)
                )

    def RemoveAirportInterest(self, request, context):
        from models import Flight
        with self.app.app_context():
            try:
                # Find and delete the user airport interest
                user_airport = UserAirport.query.filter_by(
                    user_email=request.email,
                    airport_code=request.airport_code
                ).first()
                
                if not user_airport:
                    return user_manager_pb2.RemoveAirportInterestResponse(
                        success=False,
                        message=f"Airport interest not found for user {request.email} and airport {request.airport_code}"
                    )
                
                # Delete the interest
                db.session.delete(user_airport)
                db.session.commit()
                
                # Check if this airport has other users interested
                other_users = UserAirport.query.filter_by(
                    airport_code=request.airport_code
                ).first()
                
                deleted_flights = 0
                if not other_users:
                    # No other users interested in this airport, delete all flights for it
                    deleted_flights = Flight.query.filter_by(
                        airport_monitored=request.airport_code
                    ).delete()
                    db.session.commit()
                
                return user_manager_pb2.RemoveAirportInterestResponse(
                    success=True,
                    message=f"Removed airport interest for {request.airport_code}. Deleted {deleted_flights} flights."
                )
            except Exception as e:
                db.session.rollback()
                return user_manager_pb2.RemoveAirportInterestResponse(
                    success=False,
                    message=str(e)
                )

def serve_grpc(app):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_manager_pb2_grpc.add_CollectorServiceServicer_to_server(CollectorService(app), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    server.wait_for_termination()
