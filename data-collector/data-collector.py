import os
import threading
import time
import socket
from datetime import datetime
from flask import Flask
from database import db
from routes import api_bp
from services import collect_flights
from grpc_service import serve_grpc
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_client import start_http_server

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/datadb")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

app.register_blueprint(api_bp)

def run_scheduled_flights():
    with app.app_context():
        collect_flights()

if __name__ == "__main__":
    # Start Prometheus Metrics Server
    start_http_server(8001)

    with app.app_context():
        db.create_all()
    scheduler = BackgroundScheduler(daemon = True)
    # Start background scheduler
    scheduler.add_job(func=run_scheduled_flights, trigger="interval", hours=12, next_run_time=datetime.now())
    scheduler.start()

    # Start gRPC server
    grpc_thread = threading.Thread(target=serve_grpc, args=(app,))
    grpc_thread.daemon = True
    grpc_thread.start()

    app.run(host="0.0.0.0", port=5001)
