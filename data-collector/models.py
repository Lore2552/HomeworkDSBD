from database import db

class UserAirport(db.Model):
    __tablename__ = "user_airports"

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), nullable=False)
    airport_code = db.Column(db.String(10), nullable=False)
    high_value = db.Column(db.Integer, nullable=True)
    low_value = db.Column(db.Integer, nullable=True)


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
