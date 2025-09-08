"""
Entry point for the SnipSwap DEX backend.

This Flask application exposes a REST API and a WebSocket server for
trading operations. It uses SQLAlchemy for database access and
Flask‑SocketIO for realtime event broadcasting. CORS is enabled
universally to allow front‑end clients to connect without restrictions.

Modifications from upstream:
    * Fixed bug in the static file handler which referenced an
      undefined variable `none`. It now correctly checks for
      `index_path`.
    * Added a new blueprint `private_bp` that exposes a private
      trading endpoint at `/api/private/swap`. This demonstrates how
      one could accept a client order and return an encrypted receipt
      using symmetric encryption. See `src/routes/private.py` for
      details.
    * Production-ready configuration with environment variables
    * Enhanced security and monitoring features
"""

import os
import sys
from datetime import datetime
# Ensure that imports resolve correctly when run from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

from src.models.user import db
from src.models.trading_pair import TradingPair  # noqa: F401 — imported for side effects
from src.models.order import Order  # noqa: F401 — imported for side effects
from src.models.trade import Trade  # noqa: F401 — imported for side effects
from src.models.liquidity_pool import LiquidityPool  # noqa: F401 — imported for side effects

from src.routes.user import user_bp
from src.routes.trading import trading_bp
from src.routes.orders import orders_bp
from src.routes.liquidity import liquidity_bp
from src.routes.auth import auth_bp
from src.routes.market import market_bp
from src.routes.private import private_bp  # new private trading routes

from src.websocket.trading_handler import register_trading_events


app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))

# Production-ready configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dex-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", 
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Security configurations
app.config['SESSION_COOKIE_SECURE'] = os.environ.get("FLASK_ENV") == "production"
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# CORS configuration
cors_origins = os.environ.get("CORS_ORIGINS", "*")
if cors_origins != "*":
    cors_origins = cors_origins.split(",")
CORS(app, origins=cors_origins)

# Initialize SocketIO with CORS configuration
socketio_origins = cors_origins if cors_origins != "*" else "*"
socketio = SocketIO(app, cors_allowed_origins=socketio_origins)

# Register REST blueprints
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(trading_bp, url_prefix="/api/trading")
app.register_blueprint(orders_bp, url_prefix="/api/orders")
app.register_blueprint(liquidity_bp, url_prefix="/api/liquidity")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(market_bp, url_prefix="/api/market")
app.register_blueprint(private_bp, url_prefix="/api/private")

# Initialize database
db.init_app(app)

# Ensure database tables exist on startup
with app.app_context():
    db.create_all()

# Register WebSocket event handlers
register_trading_events(socketio)


@app.route("/api/health")
def health_check():
    """Enhanced health check endpoint for monitoring."""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "snipswap-dex",
        "version": "2.0.0",
        "database": db_status,
        "websocket": "enabled",
        "privacy": "secret-network-ready",
        "timestamp": datetime.utcnow().isoformat()
    }, 200


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path: str):
    """Serve static assets from the `static` directory.

    If the requested path corresponds to a file under the static folder
    it will be returned directly. Otherwise `index.html` will be
    returned if present. When neither the file nor `index.html` exist
    an HTTP 404 response is returned.
    """
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404
    # If a specific file is requested and exists, serve it
    requested_path = os.path.join(static_folder_path, path)
    if path != "" and os.path.exists(requested_path):
        return send_from_directory(static_folder_path, path)
    # Otherwise fall back to index.html
    index_path = os.path.join(static_folder_path, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(static_folder_path, "index.html")
    return "index.html not found", 404


if __name__ == "__main__":
    # Production configuration
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") != "production"
    
    print(f"🚀 SnipSwap DEX starting on port {port}")
    print(f"🔒 Debug mode: {debug}")
    print(f"🌐 CORS origins: {os.environ.get('CORS_ORIGINS', '*')}")
    print(f"💾 Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
    
    socketio.run(app, host="0.0.0.0", port=port, debug=debug)

