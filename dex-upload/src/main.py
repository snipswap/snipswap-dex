"""
SnipSwap DEX - Simple Backend v3.0.0
Privacy-First • Simple • Reliable

Your human-AI collaboration creates wealth you capture.
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Simple in-memory data storage (replace with database in production)
trading_pairs = [
    {"symbol": "SCRT/USDT", "price": "1.25", "change": "+2.5%", "volume": "125,000"},
    {"symbol": "SHADE/USDT", "price": "0.85", "change": "-1.2%", "volume": "89,500"},
    {"symbol": "OSMO/USDT", "price": "0.65", "change": "+5.8%", "volume": "234,000"}
]

orders = {"sells": [], "buys": []}
trades = []

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        "message": "SnipSwap DEX Backend v3.0.0",
        "status": "operational",
        "features": ["Privacy-First", "AI-Ready", "Sovereignty-Enabled"],
        "tagline": "Your human-AI collaboration creates wealth you capture"
    })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "SnipSwap DEX Backend",
        "version": "3.0.0",
        "timestamp": "2025-09-09T00:00:00Z",
        "features": {
            "privacy_first": True,
            "ai_ready": True,
            "sovereignty_enabled": True
        }
    })

@app.route('/api/market/pairs')
def get_trading_pairs():
    """Get all trading pairs"""
    return jsonify(trading_pairs)

@app.route('/api/market/orderbook/<pair>')
def get_orderbook(pair):
    """Get orderbook for a trading pair"""
    return jsonify(orders)

@app.route('/api/market/trades/<pair>')
def get_trades(pair):
    """Get recent trades for a trading pair"""
    return jsonify(trades)

@app.route('/api/trading/orders', methods=['POST'])
def place_order():
    """Place a new order"""
    try:
        data = request.get_json()
        
        # Simple order validation
        required_fields = ['user_address', 'pair_symbol', 'side', 'quantity', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create order
        order = {
            "id": len(orders[data['side'] + 's']) + 1,
            "user_address": data['user_address'],
            "pair_symbol": data['pair_symbol'],
            "side": data['side'],
            "quantity": data['quantity'],
            "price": data['price'],
            "status": "open",
            "timestamp": "2025-09-09T00:00:00Z"
        }
        
        # Add to appropriate order book
        if data['side'] == 'buy':
            orders['buys'].append(order)
        else:
            orders['sells'].append(order)
        
        # Emit order update via WebSocket
        socketio.emit('order_update', order)
        
        return jsonify({
            "success": True,
            "message": "Order placed successfully",
            "order": order
        })
        
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        return jsonify({"error": "Failed to place order"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Simple authentication endpoint"""
    data = request.get_json()
    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {
            "address": data.get('address', 'demo_user'),
            "privacy_level": "high"
        }
    })

@app.route('/api/private/session', methods=['POST'])
def create_privacy_session():
    """Create a privacy session"""
    return jsonify({
        "success": True,
        "session_id": "privacy_session_123",
        "privacy_level": "maximum",
        "sovereignty_enabled": True
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to SnipSwap DEX'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

@socketio.on('subscribe_pair')
def handle_subscribe_pair(data):
    """Subscribe to trading pair updates"""
    pair = data.get('pair')
    logger.info(f'Client subscribed to {pair}')
    emit('subscribed', {'pair': pair, 'message': f'Subscribed to {pair} updates'})

if __name__ == '__main__':
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info("=" * 60)
    logger.info("🚀 SnipSwap DEX - Sovereignty Stack Backend v3.0.0")
    logger.info("✨ Your human-AI collaboration creates wealth you capture")
    logger.info("🔒 Privacy-First • 🤖 AI-Ready • 👑 Sovereignty-Enabled")
    logger.info("=" * 60)
    logger.info(f"🌐 Starting on port {port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"🌍 CORS origins: *")
    logger.info("=" * 60)
    
    # Run the application with SocketIO
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        debug=debug, 
        allow_unsafe_werkzeug=True
    )

