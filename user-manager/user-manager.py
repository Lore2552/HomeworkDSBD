import os
import threading
from flask import Flask
from database import db
from routes import user_bp
from grpc_service import serve_grpc

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/userdb")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(user_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    # Start gRPC server
    grpc_thread = threading.Thread(target=serve_grpc, args=(app,))
    grpc_thread.daemon = True
    grpc_thread.start()

    app.run(host="0.0.0.0", port=5000)
