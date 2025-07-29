import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from src.models.user import db
from src.models.trading_pair import TradingPair
from src.models.order import Order
from src.models.trade import Trade
from src.models.liquidity_pool import LiquidityPool
from src.routes.user import user_bp
from src.routes.trading import trading_bp
from src.routes.orders import orders_bp
from src.routes.liquidity import liquidity_bp
from src.routes.auth import auth_bp
from src.routes.market import market_bp
from src.websocket.trading_handler import register_trading_events

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'dex-secret-key-change-in-production'

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(trading_bp, url_prefix='/api/trading')
app.register_blueprint(orders_bp, url_prefix='/api/orders')
app.register_blueprint(liquidity_bp, url_prefix='/api/liquidity')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(market_bp, url_prefix='/api/market')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize database
with app.app_context():
    db.create_all()

# Register WebSocket events
register_trading_events(socketio)

@app.route('/api/health')
def health_check():
    return {'status': 'healthy', 'service': 'snipswap-dex'}, 200

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)

