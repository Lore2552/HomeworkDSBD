from flask import Blueprint, request, jsonify, current_app
from database import db
from models import Flight, UserAirport
from services import collect_flights, _flight_to_dict
from token_manager import token_manager
import threading
import grpc
import user_manager_pb2
import user_manager_pb2_grpc
from sqlalchemy import func
from datetime import datetime, timezone
from collections import Counter
import time
import requests

api_bp = Blueprint("api", __name__)


@api_bp.route("/register_airports", methods=["POST"])
def register_airports():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")
    airports = data.get("airports")

    if not email or not airports:
        return {"error": "Email and airports list are required"}, 400

    # Check if user exists via gRPC
    try:
        with grpc.insecure_channel("user-manager:50051") as channel:
            stub = user_manager_pb2_grpc.UserServiceStub(channel)
            response = stub.CheckUser(user_manager_pb2.CheckUserRequest(email=email))

            if not response.exists:
                return {"error": "User not found in User Manager"}, 404
    except grpc.RpcError as e:
        return {"error": f"gRPC error: {e.details()}"}, 500

    # Save airports to DataDB
    airport_codes_for_collection = []
    new_registrations = False
    updates_performed = False

    for airport_data in airports:
        # Handle both string (old format) and dict (new format)
        if isinstance(airport_data, str):
            code = airport_data
            high = None
            low = None
        elif isinstance(airport_data, dict):
            code = airport_data.get("code")
            high = airport_data.get("high_value")
            low = airport_data.get("low_value")
        else:
            continue

        if not code:
            continue

        # Validation: high > low if both present in request
        if high is not None and low is not None:
            if high <= low:
                return {"error": f"For airport {code}, high-value must be greater than low-value"}, 400

        airport_codes_for_collection.append(code)

        exists = UserAirport.query.filter_by(
            user_email=email, airport_code=code
        ).first()

        if exists:
            # Update existing
            current_high = exists.high_value
            current_low = exists.low_value
            
            new_high = high if high is not None else current_high
            new_low = low if low is not None else current_low

            # Validate against existing/new values
            if new_high is not None and new_low is not None:
                if new_high <= new_low:
                     return {"error": f"For airport {code}, update failed: high-value ({new_high}) must be greater than low-value ({new_low})"}, 400
            
            if high is not None: 
                exists.high_value = high
                updates_performed = True
            if low is not None: 
                exists.low_value = low
                updates_performed = True
        else:
            new_registrations = True
            new_airport = UserAirport(
                user_email=email, 
                airport_code=code,
                high_value=high,
                low_value=low
            )
            db.session.add(new_airport)

    db.session.commit()

    stats = collect_flights(target_airports=airport_codes_for_collection)
    
    has_errors = len(stats.get("errors", [])) > 0
    
    status_code = 200
    message = "Airports processed successfully."

    if new_registrations:
        if has_errors:
            message = "Failed to collect data for new airport(s)."
            status_code = 502 
        else:
            message = "Airports registered successfully."
            if updates_performed:
                message = "Airports registered and preferences updated successfully."
    elif updates_performed:
        message = "Preferences updated successfully."
    elif has_errors:
        message = "Errors occurred during flight data collection."
        status_code = 502

    return {
        "message": message,
        "collection_stats": stats
    }, status_code


@api_bp.route("/airports/deleteThresholds", methods=["DELETE"])
def delete_airport_thresholds():
    data = request.json
    if not data:
        return {"error": "Invalid JSON"}, 400

    email = data.get("email")
    airport_code = data.get("airport_code")

    if not email or not airport_code:
        return {"error": "Email and airport_code are required"}, 400

    user_airport = UserAirport.query.filter_by(
        user_email=email, airport_code=airport_code
    ).first()

    if not user_airport:
        return {"error": "Airport interest not found"}, 404

    user_airport.high_value = None
    user_airport.low_value = None
    
    try:
        db.session.commit()
        return {"message": f"Thresholds removed for airport {airport_code}"}, 200
    except Exception as e:
        db.session.rollback()
        return {"error": f"Database error: {str(e)}"}, 500


@api_bp.route("/user_info/<email>", methods=["GET"])
def get_user_info(email):
    user_data = {}
    try:
        with grpc.insecure_channel("user-manager:50051") as channel:
            stub = user_manager_pb2_grpc.UserServiceStub(channel)
            response = stub.GetUser(user_manager_pb2.GetUserRequest(email=email))

            if response.found:
                user_data = {
                    "email": response.email,
                    "name": response.name,
                    "surname": response.surname,
                    "fiscal_code": response.fiscal_code,
                    "bank_info": response.bank_info,
                }
            else:
                return {"error": "User not found"}, 404
    except grpc.RpcError as e:
        return {"error": f"gRPC error: {e.details()}"}, 500

    user_airports = UserAirport.query.filter_by(user_email=email).all()
    airports_list = [ua.airport_code for ua in user_airports]

    result = {"user": user_data, "airports": airports_list}

    return jsonify(result), 200

''' Useful for debugging 
@api_bp.route("/get_token", methods=["GET"])
def get_token_route():
    try:
        token = token_manager.get_token()
        return jsonify({"access_token": token}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

# test for token usage
@api_bp.route("/states/all", methods=["GET"])
def get_all_states():
    token = None
    try:
        token = token_manager.get_token()
    except Exception as e:
        return jsonify({"error": f"Failed to get token: {e}"}), 400

    headers = {"Authorization": f"Bearer {token}"}
    OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
    response = requests.get(OPENSKY_STATES_URL, headers=headers)

    if response.status_code != 200:
        return (
            jsonify(
                {"error": "Failed to fetch OpenSky data", "details": response.text}
            ),
            response.status_code,
        )

    return jsonify(response.json()), 200


@api_bp.route("/flights", methods=["GET"])
def get_flights():
    flights = Flight.query.all()
    result = []
    for f in flights:
        result.append(_flight_to_dict(f))
    return jsonify(result), 200


@api_bp.route("/airports/<airport_code>/last_flight", methods=["GET"])
def get_last_flight(airport_code):
    direction = request.args.get("direction")  

    response = {}

    if direction in [None, "arrival"]:
        last_arrival = (
            Flight.query.filter_by(airport_monitored=airport_code, direction="arrival")
            .order_by(Flight.first_seen.desc())
            .first()
        )
        response["arrival"] = _flight_to_dict(last_arrival) if last_arrival else None

    if direction in [None, "departure"]:
        last_departure = (
            Flight.query.filter_by(
                airport_monitored=airport_code, direction="departure"
            )
            .order_by(Flight.first_seen.desc())
            .first()
        )
        response["departure"] = (
            _flight_to_dict(last_departure) if last_departure else None
        )

    return jsonify(response), 200


@api_bp.route("/airports/<airport_code>/average_flights", methods=["GET"])
def get_average_flights(airport_code):
    try:
        days = int(request.args.get("days", 7))
    except ValueError:
        return jsonify({"error": "Invalid days parameter"}), 400

    direction = request.args.get("direction")  

    now = int(time.time())
    start_time = now - (days * 24 * 3600)

    query = db.session.query(func.count(Flight.id)).filter(Flight.airport_monitored == airport_code, Flight.first_seen >= start_time)

    if direction:
        query = query.filter(Flight.direction == direction)

    total_flights = query.scalar()

    average = total_flights / days if days > 0 else 0

    return (
        jsonify(
            {
                "airport": airport_code,
                "days_analyzed": days,
                "direction": direction if direction else "both",
                "total_flights": total_flights,
                "average_per_day": round(average, 2),
            }
        ),
        200,
    )


@api_bp.route("/airports/<airport_code>/busiest_hour", methods=["GET"])
def get_busiest_hour(airport_code):
    flights = (db.session.query(Flight.first_seen).filter_by(airport_monitored=airport_code).all())

    if not flights:
        return jsonify({"message": "No flights found for this airport"}), 404

    hours = [datetime.fromtimestamp(f[0], tz=timezone.utc).hour for f in flights]

    hour_counts = Counter(hours)

    if not hour_counts:
        return jsonify({"message": "No data"}), 404

    busiest_hour, count = hour_counts.most_common(1)[0]

    return (
        jsonify(
            {
                "airport": airport_code,
                "busiest_hour_utc": busiest_hour,
                "flight_count": count,
                "total_flights_analyzed": len(flights),
            }
        ),
        200,
    )


@api_bp.route("/collect_flights", methods=["POST"])
def trigger_collect_flights():
    result = collect_flights()
    return jsonify(result), 200


@api_bp.route("/usersinterests", methods=["GET"])
def get_users_interests():
    users_interests = {}
    user_airports = UserAirport.query.all()
    for ua in user_airports:
        if ua.user_email not in users_interests:
            users_interests[ua.user_email] = {"airports": []}
        users_interests[ua.user_email]["airports"].append(ua.airport_code)
    return jsonify(users_interests), 200
