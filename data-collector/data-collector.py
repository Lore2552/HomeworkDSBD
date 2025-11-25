import os
import threading
import time
from flask import Flask
from database import db
from routes import api_bp
from services import collect_flights

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/datadb")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

app.register_blueprint(api_bp)

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
