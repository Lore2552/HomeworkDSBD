import os
import threading
from flask import Flask
from database import db
from models import MessageId
from datetime import datetime
from routes import user_bp
from grpc_service import serve_grpc
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/userdb")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(user_bp)

def cleanup_expired_messages():
    print(f"[{datetime.now()}] Esecuzione cleanup cache messaggi...")
    try:
        now = datetime.now()
        deleted_count = MessageId.query.filter(MessageId.expires_at < now).delete()
        db.session.commit()
        if deleted_count > 0:
            print(f"Cleanup completato: rimossi {deleted_count} messaggi scaduti.")
    except Exception as e:
        db.session.rollback()
        print(f"Errore durante il cleanup: {e}")

def start_app_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(func=run_cleanup_job, trigger="interval", minutes=5)
    scheduler.start()

def run_cleanup_job():
    with app.app_context():
        cleanup_expired_messages()
        
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    start_app_scheduler()
    
    # Start gRPC server
    grpc_thread = threading.Thread(target=serve_grpc, args=(app,))
    grpc_thread.daemon = True
    grpc_thread.start()

    app.run(host="0.0.0.0", port=5000)
