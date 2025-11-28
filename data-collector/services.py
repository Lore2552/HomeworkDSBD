import time
import requests
from flask import jsonify
from database import db
from models import Flight, UserAirport
from token_manager import token_manager

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
        return {"error": f"Failed to get token: {e}"}
    
    if token:
        headers = {"Authorization": f"Bearer {token}"}
    # Time window: End 2 hours ago to ensure data availability
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
                    # Check for duplicates
                    exists = Flight.query.filter_by(
                        icao24=f.get('icao24'),
                        first_seen=f.get('firstSeen'),
                        airport_monitored=code,
                        direction='arrival'
                    ).first()
                    
                    if exists:
                        continue

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
                    # Check for duplicates
                    exists = Flight.query.filter_by(
                        icao24=f.get('icao24'),
                        first_seen=f.get('firstSeen'),
                        airport_monitored=code,
                        direction='departure'
                    ).first()
                    
                    if exists:
                        continue

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
