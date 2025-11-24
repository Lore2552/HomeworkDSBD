import os
import time
import threading
import requests
from datetime import datetime, timezone
from collections import Counter
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import grpc
import user_manager_pb2
import user_manager_pb2_grpc

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/datadb")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


CLIENT_ID = os.getenv("CLIENT_ID", "lore25-api-client")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "FozpkBoBcLEhsFcEZNh1ySEGmsb7bYbJ")


TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"


class UserAirport(db.Model):
    __tablename__ = "user_airports"

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), nullable=False)
    airport_code = db.Column(db.String(10), nullable=False)


class Flight(db.Model):
    __tablename__ = "flights"

    id = db.Column(db.Integer, primary_key=True)
    icao24 = db.Column(db.String(20))
    callsign = db.Column(db.String(20))
    est_departure_airport = db.Column(db.String(10))
    est_arrival_airport = db.Column(db.String(10))
    first_seen = db.Column(db.Integer)
    last_seen = db.Column(db.Integer)
    airport_monitored = db.Column(db.String(10))
    direction = db.Column(db.String(10))  # 'arrival' or 'departure'


def _flight_to_dict(flight):
    if not flight:
        return None
    return {
        "id": flight.id,
        "icao24": flight.icao24,
        "callsign": flight.callsign,
        "est_departure_airport": flight.est_departure_airport,
        "est_arrival_airport": flight.est_arrival_airport,
        "first_seen": flight.first_seen,
        "last_seen": flight.last_seen,
        "airport_monitored": flight.airport_monitored,
        "direction": flight.direction,
    }


class TokenManager:
    def __init__(self, token_url, client_id, client_secret):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._expiry_ts = 0
        self._lock = threading.Lock()
        # ssecondi
        self._margin = 30

    #metodo privato!
    def _request_new_token(self):
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(self.token_url, data=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"Token endpoint error: {resp.status_code} {resp.text}")
        data = resp.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 300)  # fallback se manca il campo
        if not token:
            raise RuntimeError("Token endpoint did not return access_token")
        expiry_ts = int(time.time()) + int(expires_in)
        return token, expiry_ts

    def get_token(self):
        with self._lock:
            now = int(time.time())
            # se token valido e non vicino alla scadenza, lo riuso
            if self._access_token and (self._expiry_ts - now) > self._margin:
                return self._access_token
            # altrimenti richiedo un nuovo token e aggiorno cache
            token, expiry_ts = self._request_new_token()
            self._access_token = token
            self._expiry_ts = expiry_ts
            return self._access_token

# istanza globale
token_manager = TokenManager(TOKEN_URL, CLIENT_ID, CLIENT_SECRET)

@app.route("/register_airports", methods=["POST"])
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
    for airport_code in airports:
        exists = UserAirport.query.filter_by(
            user_email=email, airport_code=airport_code
        ).first()
        if not exists:
            new_airport = UserAirport(user_email=email, airport_code=airport_code)
            db.session.add(new_airport)

    db.session.commit()

    # Trigger immediate collection for these airports in background
    def async_collection(app_instance, codes):
        with app_instance.app_context():
            collect_flights(target_airports=codes)

    threading.Thread(target=async_collection, args=(app, airports)).start()

    return {"message": "Airports registered successfully. Flight data collection started."}, 200


@app.route("/user_info/<email>", methods=["GET"])
def get_user_info(email):
    # 1. Get user details from User Manager via gRPC
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
                    "bank_info": response.bank_info
                }
            else:
                return {"error": "User not found"}, 404
    except grpc.RpcError as e:
        return {"error": f"gRPC error: {e.details()}"}, 500

    # 2. Get airports from local DB
    user_airports = UserAirport.query.filter_by(user_email=email).all()
    airports_list = [ua.airport_code for ua in user_airports]

    # 3. Combine and return
    result = {
        "user": user_data,
        "airports": airports_list
    }
    
    return jsonify(result), 200

#usiamola solo per debug e poi eliminiamo questo endopoint quando consegniamo il progetto 
@app.route("/get_token", methods=["GET"])
def get_token_route():
    try:
        token = token_manager.get_token()
        return jsonify({"access_token": token}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#eliminiamo quando consegniamo il progetto, era una prova
@app.route("/states/all", methods=["GET"])
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


@app.route("/flights", methods=["GET"])
def get_flights():
    flights = Flight.query.all()
    result = []
    for f in flights:
        result.append(_flight_to_dict(f))
    return jsonify(result), 200


@app.route("/airports/<airport_code>/last_flight", methods=["GET"])
def get_last_flight(airport_code):
    direction = request.args.get("direction") # 'arrival', 'departure' or None for both

    response = {}

    if direction in [None, 'arrival']:
        last_arrival = Flight.query.filter_by(airport_monitored=airport_code, direction='arrival')\
            .order_by(Flight.first_seen.desc()).first()
        response['arrival'] = _flight_to_dict(last_arrival) if last_arrival else None

    if direction in [None, 'departure']:
        last_departure = Flight.query.filter_by(airport_monitored=airport_code, direction='departure')\
            .order_by(Flight.first_seen.desc()).first()
        response['departure'] = _flight_to_dict(last_departure) if last_departure else None
    
    return jsonify(response), 200


@app.route("/airports/<airport_code>/average_flights", methods=["GET"])
def get_average_flights(airport_code):
    try:
        days = int(request.args.get("days", 7))
    except ValueError:
        return jsonify({"error": "Invalid days parameter"}), 400
    
    direction = request.args.get("direction") # 'arrival', 'departure' or None for total

    now = int(time.time())
    start_time = now - (days * 24 * 3600)

    query = db.session.query(func.count(Flight.id)).filter(
        Flight.airport_monitored == airport_code,
        Flight.first_seen >= start_time
    )

    if direction:
        query = query.filter(Flight.direction == direction)
    
    total_flights = query.scalar()
    
    average = total_flights / days if days > 0 else 0

    return jsonify({
        "airport": airport_code,
        "days_analyzed": days,
        "direction": direction if direction else "both",
        "total_flights": total_flights,
        "average_per_day": round(average, 2)
    }), 200


@app.route("/airports/<airport_code>/busiest_hour", methods=["GET"])
def get_busiest_hour(airport_code):
    # Fetch all first_seen timestamps for the airport
    flights = db.session.query(Flight.first_seen).filter_by(airport_monitored=airport_code).all()
    
    if not flights:
        return jsonify({"message": "No flights found for this airport"}), 404

    # Extract hour from timestamp (UTC)
    hours = [datetime.fromtimestamp(f[0], tz=timezone.utc).hour for f in flights]
    
    hour_counts = Counter(hours)
    
    if not hour_counts:
         return jsonify({"message": "No data"}), 404

    busiest_hour, count = hour_counts.most_common(1)[0]
    
    return jsonify({
        "airport": airport_code,
        "busiest_hour_utc": busiest_hour,
        "flight_count": count,
        "total_flights_analyzed": len(flights)
    }), 200





@app.route("/collect_flights", methods=["POST"])
def trigger_collect_flights():
    # Run synchronously for debugging purposes
    result = collect_flights()
    return jsonify(result), 200


def collect_flights(target_airports=None):
    print("Starting flight collection cycle...")
    stats = {"airports_processed": 0, "flights_added": 0, "errors": []}
    
    airport_codes = []
    if target_airports:
        airport_codes = target_airports
    else:
        # Get unique airports
        try:
            airports = db.session.query(UserAirport.airport_code).distinct().all()
            airport_codes = [a[0] for a in airports]
        except Exception as e:
            return {"error": f"Error querying airports: {e}"}

    if not airport_codes:
        if target_airports:
             return {"message": "No valid airports provided."}
        return {"message": "No airports to monitor found in DB."}

    # Auth logic: Prefer Basic Auth if vars are set, else try Token
    auth = None
    headers = {}
    token = None

    try:
        token = token_manager.get_token()
    except Exception as e:
        return jsonify({"error": f"Failed to get token: {e}"}), 400
    
    if token:
        headers = {"Authorization": f"Bearer {token}"}
    # Time window: End 2 hours ago to ensure data availability (OpenSky delay)
    # and cover the last 12 hours from that point.
    end_time = int(time.time()) - 7200 
    begin_time = end_time - (12 * 3600)

    print(f"Collecting flights from {begin_time} to {end_time}")

    for code in airport_codes:
        stats["airports_processed"] += 1
        # Arrivals
        try:
            url = f"https://opensky-network.org/api/flights/arrival?airport={code}&begin={begin_time}&end={end_time}"
            print(f"Fetching arrivals for {code}: {url}")
            resp = requests.get(url, headers=headers, auth=auth)
            
            if resp.status_code == 200:
                flights = resp.json()
                print(f"Found {len(flights)} arrivals for {code}")
                for f in flights:
                    # Avoid duplicates if needed, or just insert log-style
                    new_flight = Flight(
                        icao24=f.get('icao24'),
                        callsign=f.get('callsign', '').strip(),
                        est_departure_airport=f.get('estDepartureAirport'),
                        est_arrival_airport=f.get('estArrivalAirport'),
                        first_seen=f.get('firstSeen'),
                        last_seen=f.get('lastSeen'),
                        airport_monitored=code,
                        direction='arrival'
                    )
                    db.session.add(new_flight)
                    stats["flights_added"] += 1
            elif resp.status_code == 404:
                print(f"No arrivals found for {code} (404). This is normal if no flights occurred in the window.")
            else:
                error_msg = f"Error fetching arrivals for {code}: {resp.status_code} {resp.text}"
                print(error_msg)
                stats["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Exception fetching arrivals for {code}: {e}"
            print(error_msg)
            stats["errors"].append(error_msg)

        # Departures
        try:
            url = f"https://opensky-network.org/api/flights/departure?airport={code}&begin={begin_time}&end={end_time}"
            print(f"Fetching departures for {code}: {url}")
            resp = requests.get(url, headers=headers, auth=auth)
            
            if resp.status_code == 200:
                flights = resp.json()
                print(f"Found {len(flights)} departures for {code}")
                for f in flights:
                    new_flight = Flight(
                        icao24=f.get('icao24'),
                        callsign=f.get('callsign', '').strip(),
                        est_departure_airport=f.get('estDepartureAirport'),
                        est_arrival_airport=f.get('estArrivalAirport'),
                        first_seen=f.get('firstSeen'),
                        last_seen=f.get('lastSeen'),
                        airport_monitored=code,
                        direction='departure'
                    )
                    db.session.add(new_flight)
                    stats["flights_added"] += 1
            elif resp.status_code == 404:
                print(f"No departures found for {code} (404). This is normal if no flights occurred in the window.")
            else:
                error_msg = f"Error fetching departures for {code}: {resp.status_code} {resp.text}"
                print(error_msg)
                stats["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Exception fetching departures for {code}: {e}"
            print(error_msg)
            stats["errors"].append(error_msg)
        
    try:
        db.session.commit()
        print("Flight collection cycle completed and saved to DB.")
    except Exception as e:
        error_msg = f"Error saving flights to DB: {e}"
        print(error_msg)
        db.session.rollback()
        stats["errors"].append(error_msg)
    
    return stats


def start_scheduler():
    while True:
        with app.app_context():
            collect_flights()
        # Sleep for 12 hours
        time.sleep(12 * 3600)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    # Start background scheduler
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    app.run(host="0.0.0.0", port=5001)
