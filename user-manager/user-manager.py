import os
import threading
import time
import socket
from flask import Flask
from database import db
from models import MessageId
from datetime import datetime
from routes import user_bp
from grpc_service import serve_grpc
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_client import start_http_server
from metrics import HOSTNAME, SERVICE_NAME, CLEANUP_DURATION, MESSAGES_CLEANED_TOTAL

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/userdb")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(user_bp)

def cleanup_expired_messages():
    try:
        now = datetime.now()
        deleted_count = MessageId.query.filter(MessageId.expires_at < now).delete()
        db.session.commit()
        if deleted_count > 0:
            MESSAGES_CLEANED_TOTAL.labels(service=SERVICE_NAME, node=HOSTNAME).inc(deleted_count)
    except Exception as e:
        db.session.rollback()

def start_app_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(func=run_cleanup_job, trigger="interval", minutes=5, next_run_time=datetime.now())
    scheduler.start()

def run_cleanup_job():
    with app.app_context():
        start_time = time.time()
        cleanup_expired_messages()
        duration = time.time() - start_time
        CLEANUP_DURATION.labels(service=SERVICE_NAME, node=HOSTNAME).set(duration)
        
if __name__ == "__main__":
    # Start Prometheus Metrics Server
    start_http_server(8000)

    with app.app_context():
        db.create_all()
    start_app_scheduler()
    
    # Start gRPC server
    grpc_thread = threading.Thread(target=serve_grpc, args=(app,))
    grpc_thread.daemon = True
    grpc_thread.start()

    app.run(host="0.0.0.0", port=5000)
