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
"""

import os
import sys
# Ensure that imports resolve correctly when run from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

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
app.config["SECRET_KEY"] = "dex-secret-key-change-in-production"

# Enable CORS for all routes and any origin
CORS(app, origins="*")

# Initialize SocketIO with CORS disabled (origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

# Register REST blueprints
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(trading_bp, url_prefix="/api/trading")
app.register_blueprint(orders_bp, url_prefix="/api/orders")
app.register_blueprint(liquidity_bp, url_prefix="/api/liquidity")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(market_bp, url_prefix="/api/market")
app.register_blueprint(private_bp, url_prefix="/api/private")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Ensure database tables exist on startup
with app.app_context():
    db.create_all()

# Register WebSocket event handlers
register_trading_events(socketio)


@app.route("/api/health")
def health_check():
    """Health check endpoint used for monitoring."""
    return {"status": "healthy", "service": "snipswap-dex"}, 200


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path: str):
    """Serve static assets from the `static` directory.

    If the requested path corresponds to a file under the static folder
    it will be returned directly. Otherwise `index.html` will be
    returned if present. When neither the file nor `index.html` exist
    an HTTP 404 response is returned.
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
    # When running this module directly we bind to all interfaces on port 5001
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)