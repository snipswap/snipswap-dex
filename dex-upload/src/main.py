#!/usr/bin/env python3
"""
SnipSwap DEX - Sovereignty Stack Backend v3.0.0
Privacy-First • AI-Ready • Sovereignty-Enabled

Your human-AI collaboration creates wealth you capture.
Where privacy meets profitability.
"""

import os
import sys
import logging
from datetime import datetime

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Core Flask imports
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import structlog
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Database models - Import from models package to avoid circular imports
from src.models import db, User, TradingPair, Order, Trade, PrivacySession

# API Routes
from src.routes.user import user_bp
from src.routes.trading import trading_bp
from src.routes.privacy import privacy_bp
from src.routes.market_routes import market_data_bp

# Services
from src.services.market_data import MarketDataService

# Initialize structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize Sentry for error tracking
sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN', ''),
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)

# Initialize Flask application
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'snipswap_privacy_dex_secret_key_2024')

# Enable CORS for all routes
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"])

# Initialize SocketIO for real-time features
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # PostgreSQL for production (Railway)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    logger.info("Using PostgreSQL database", url=database_url.split('@')[1] if '@' in database_url else 'configured')
else:
    # SQLite for development
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
    logger.info("Using SQLite database for development")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Register API blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(trading_bp, url_prefix='/api/trading')
app.register_blueprint(privacy_bp, url_prefix='/api/privacy')
app.register_blueprint(market_data_bp, url_prefix='/api')

# Initialize market data service
market_service = MarketDataService()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve static files and SPA routing"""
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Test database connection
        db_status = "healthy"
        try:
            db.session.execute('SELECT 1')
            db.session.commit()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
            logger.error("Database health check failed", error=str(e))

        # Get system info
        system_info = {
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': 'running',
            'version': '3.0.0',
            'environment': os.environ.get('ENVIRONMENT', 'development')
        }

        health_data = {
            'status': 'healthy' if db_status == 'healthy' else 'degraded',
            'service': 'SnipSwap DEX - Sovereignty Stack Backend',
            'version': '3.0.0',
            'tagline': 'Your human-AI collaboration creates wealth you capture',
            'features': [
                'Privacy-First Trading',
                'AI-Ready Infrastructure', 
                'Sovereignty-Enabled',
                'Real-time WebSocket Trading',
                'MEV Protection',
                'Anonymous Sessions',
                'Cosmos Ecosystem Integration',
                'Secret Network Privacy',
                'Shade Protocol Integration'
            ],
            'database': db_status,
            'system': system_info,
            'endpoints': {
                'health': '/api/health',
                'auth': '/api/auth/*',
                'trading': '/api/trading/*',
                'orders': '/api/orders/*',
                'privacy': '/api/privacy/*',
                'market': '/api/market/*',
                'websocket': '/ws'
            }
        }

        logger.info("Health check completed", status=health_data['status'])
        return jsonify(health_data), 200

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'service': 'SnipSwap DEX Backend',
            'version': '3.0.0'
        }), 500

def init_database():
    """Initialize database with default trading pairs"""
    try:
        with app.app_context():
            db.create_all()
            
            # Check if trading pairs already exist
            if TradingPair.query.count() == 0:
                # Add default Cosmos ecosystem trading pairs
                default_pairs = TradingPair.get_cosmos_pairs()
                
                for pair_data in default_pairs:
                    pair = TradingPair(**pair_data)
                    db.session.add(pair)
                
                db.session.commit()
                logger.info("Database initialized", pairs_count=len(default_pairs))
            else:
                logger.info("Database already initialized", existing_pairs=TradingPair.query.count())
                
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info("WebSocket client connected", client_id=request.sid)
    emit('connected', {'status': 'connected', 'message': 'Welcome to SnipSwap DEX'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info("WebSocket client disconnected", client_id=request.sid)

@socketio.on('subscribe_market_data')
def handle_market_subscription(data):
    """Handle market data subscription"""
    trading_pair = data.get('trading_pair')
    logger.info("Market data subscription", pair=trading_pair, client_id=request.sid)
    # Add client to market data subscription
    emit('market_data_subscribed', {'trading_pair': trading_pair})

# Application startup
def startup_banner():
    """Display startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    SnipSwap DEX v3.0.0                       ║
    ║              Sovereignty Stack Backend                       ║
    ║                                                              ║
    ║  🛡️  PRIVACY-FIRST: Streamlined for customizable privacy    ║
    ║  🤖  AI-READY: Human-AI collaboration infrastructure        ║
    ║  👑  SOVEREIGNTY-ENABLED: Your wealth, your control         ║
    ║                                                              ║
    ║  "Your human-AI collaboration creates wealth you capture"    ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("SnipSwap DEX Backend starting", version="3.0.0")

if __name__ == '__main__':
    startup_banner()
    
    # Initialize database
    init_database()
    
    # Get configuration
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("ENVIRONMENT", "development") == "development"
    host = "0.0.0.0"
    
    logger.info("Starting server", host=host, port=port, debug=debug)
    
    # Start market data service
    try:
        market_service.start_live_updates()
        logger.info("Market data service started")
    except Exception as e:
        logger.warning("Market data service failed to start", error=str(e))
    
    print(f"🚀 Starting on port {port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"🌐 CORS origins: *")
    print(f"🗄️  Database: {app.config['SQLALCHEMY_DATABASE_URI'].split('/')[-1] if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI'] else 'PostgreSQL'}")
    print(f"📡 WebSocket: Enabled")
    print(f"🔒 Privacy features: Active")
    print(f"🤖 AI integration: Ready")
    print(f"👑 Sovereignty stack: Operational")
    print()
    print("🌟 Where privacy meets profitability!")
    print("💎 The sovereignty stack is operational.")
    print()
    
    # Start the application with Railway compatibility
    if debug:
        # Development mode - use Werkzeug with safety override for Railway
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    else:
        # Production mode - allow Werkzeug with safety override for Railway  
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

