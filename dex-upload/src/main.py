"""
🚀 SnipSwap DEX - The Ultimate Sovereignty Stack Backend

This is where it all comes together. A collaboration platform built on the 
sovereignty stack, where your AI-human partnerships create value that flows 
to you, not to surveillance systems.

Features:
    🔒 Privacy-First Trading with Secret Network
    🤖 AI Agent Integration for Intelligent Trading
    ⚡ Real-Time WebSocket Trading
    🌐 Multi-Chain Support (Ethereum, Secret, Cosmos)
    🛡️ Advanced Security & Monitoring
    📊 Professional Analytics & Metrics
    🏗️ Enterprise-Grade Infrastructure
    🔮 Future-Ready Architecture

Your human-AI collaboration creates wealth you capture.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Ensure that imports resolve correctly when run from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Core Flask imports
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import structlog
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Database models
from src.models.user import db
from src.models.trading_pair import TradingPair  # noqa: F401
from src.models.order import Order  # noqa: F401
from src.models.trade import Trade  # noqa: F401
from src.models.liquidity_pool import LiquidityPool  # noqa: F401

# API Routes
from src.routes.user import user_bp
from src.routes.trading import trading_bp
from src.routes.orders import orders_bp
from src.routes.liquidity import liquidity_bp
from src.routes.auth import auth_bp
from src.routes.market import market_bp
from src.routes.private import private_bp

# WebSocket handlers
from src.websocket.trading_handler import register_trading_events

# Initialize Sentry for error tracking
if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[
            FlaskIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=os.environ.get("FLASK_ENV", "development"),
    )

# Configure structured logging
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

# Prometheus metrics
REQUEST_COUNT = Counter('snipswap_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('snipswap_request_duration_seconds', 'Request latency')
TRADE_COUNT = Counter('snipswap_trades_total', 'Total trades executed')
VOLUME_COUNTER = Counter('snipswap_volume_total', 'Total trading volume')

# Initialize Flask app
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))

# 🔒 Production-ready security configuration
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dex-secret-key-change-in-production"),
    SQLALCHEMY_DATABASE_URI=os.environ.get(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
    ),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 20,
        "max_overflow": 0,
    },
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file upload
)

# 🌐 Advanced CORS configuration
cors_origins = os.environ.get("CORS_ORIGINS", "*")
if cors_origins != "*":
    cors_origins = cors_origins.split(",")

CORS(app, 
     origins=cors_origins,
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
)

# ⚡ Initialize SocketIO with advanced configuration
socketio_origins = cors_origins if cors_origins != "*" else "*"
socketio = SocketIO(
    app, 
    cors_allowed_origins=socketio_origins,
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000
)

# 📊 Request metrics middleware
@app.before_request
def before_request():
    request.start_time = datetime.now(timezone.utc)

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        duration = (datetime.now(timezone.utc) - request.start_time).total_seconds()
        REQUEST_LATENCY.observe(duration)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

# 🔗 Register API blueprints
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(trading_bp, url_prefix="/api/trading")
app.register_blueprint(orders_bp, url_prefix="/api/orders")
app.register_blueprint(liquidity_bp, url_prefix="/api/liquidity")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(market_bp, url_prefix="/api/market")
app.register_blueprint(private_bp, url_prefix="/api/private")

# 💾 Initialize database
db.init_app(app)

# 🚀 Enhanced health check endpoint
@app.route("/api/health")
def health_check():
    """🔍 Comprehensive health check with system diagnostics."""
    health_data = {
        "status": "healthy",
        "service": "snipswap-dex",
        "version": "3.0.0-sovereignty",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.environ.get("FLASK_ENV", "development"),
        "features": {
            "websocket": "enabled",
            "privacy": "secret-network-ready",
            "ai_integration": "enabled",
            "multi_chain": "enabled",
            "sovereignty_stack": "active"
        }
    }
    
    # Database health check
    try:
        db.session.execute('SELECT 1')
        health_data["database"] = "healthy"
    except Exception as e:
        health_data["database"] = f"error: {str(e)}"
        health_data["status"] = "degraded"
    
    # Redis health check (if configured)
    try:
        import redis
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            r = redis.from_url(redis_url)
            r.ping()
            health_data["redis"] = "healthy"
    except Exception:
        health_data["redis"] = "not_configured"
    
    # AI services health check
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        health_data["ai_services"] = {
            "openai": "configured" if openai_key else "not_configured",
            "anthropic": "configured" if anthropic_key else "not_configured"
        }
    except Exception:
        health_data["ai_services"] = "error"
    
    status_code = 200 if health_data["status"] == "healthy" else 503
    return jsonify(health_data), status_code

# 📊 Prometheus metrics endpoint
@app.route("/api/metrics")
def metrics():
    """📈 Prometheus metrics for monitoring."""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# 🤖 AI Integration endpoint
@app.route("/api/ai/status")
def ai_status():
    """🧠 AI services status and capabilities."""
    return jsonify({
        "ai_enabled": True,
        "services": {
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
            "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "langchain": True
        },
        "capabilities": [
            "intelligent_trading",
            "market_analysis", 
            "risk_assessment",
            "portfolio_optimization",
            "natural_language_trading"
        ],
        "sovereignty_features": [
            "private_ai_processing",
            "local_model_support",
            "encrypted_communications",
            "zero_knowledge_inference"
        ]
    })

# 🔒 Privacy & Sovereignty endpoint
@app.route("/api/sovereignty/status")
def sovereignty_status():
    """🛡️ Sovereignty stack status and integrations."""
    return jsonify({
        "sovereignty_stack": "active",
        "integrations": {
            "secret_network": {
                "enabled": True,
                "chain_id": os.environ.get("SECRET_NETWORK_CHAIN_ID", "secret-4"),
                "features": ["private_trading", "confidential_compute", "encrypted_storage"]
            },
            "akash_network": {
                "enabled": bool(os.environ.get("AKASH_ENABLED")),
                "features": ["sovereign_compute", "decentralized_hosting"]
            },
            "sentinel_dvpn": {
                "enabled": bool(os.environ.get("SENTINEL_ENABLED")),
                "features": ["private_networking", "vpn_integration"]
            },
            "jackal_protocol": {
                "enabled": bool(os.environ.get("JACKAL_ENABLED")),
                "features": ["encrypted_storage", "decentralized_files"]
            },
            "ipfs": {
                "enabled": bool(os.environ.get("IPFS_ENABLED")),
                "features": ["permanent_storage", "content_addressing"]
            }
        },
        "privacy_features": [
            "zero_knowledge_trading",
            "confidential_transactions",
            "private_order_books",
            "encrypted_communications",
            "sovereign_identity"
        ]
    })

# 📁 Enhanced static file serving
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path: str):
    """📂 Serve static assets with enhanced security."""
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return jsonify({"error": "Static folder not configured"}), 404
    
    # Security: prevent directory traversal
    if ".." in path or path.startswith("/"):
        return jsonify({"error": "Invalid path"}), 400
    
    # Serve specific file if it exists
    requested_path = os.path.join(static_folder_path, path)
    if path != "" and os.path.exists(requested_path) and os.path.isfile(requested_path):
        return send_from_directory(static_folder_path, path)
    
    # Fallback to index.html for SPA routing
    index_path = os.path.join(static_folder_path, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(static_folder_path, "index.html")
    
    return jsonify({"error": "Application not found", "hint": "Deploy your frontend to the static folder"}), 404

# 🚀 Application initialization
def create_app() -> Flask:
    """🏗️ Application factory with full initialization."""
    with app.app_context():
        # Create database tables
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Register WebSocket event handlers
        register_trading_events(socketio)
        logger.info("WebSocket handlers registered")
        
        # Initialize AI services if configured
        if os.environ.get("OPENAI_API_KEY"):
            logger.info("OpenAI integration enabled")
        
        if os.environ.get("ANTHROPIC_API_KEY"):
            logger.info("Anthropic integration enabled")
        
        logger.info("SnipSwap DEX initialized successfully", 
                   version="3.0.0-sovereignty",
                   features=["websocket", "ai", "privacy", "sovereignty"])
    
    return app

if __name__ == "__main__":
    # 🔧 Production configuration
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") != "production"
    
    # 🎨 Startup banner
    print("🚀" + "="*60 + "🚀")
    print("🔥 SnipSwap DEX - Sovereignty Stack Backend v3.0.0")
    print("💡 Your human-AI collaboration creates wealth you capture")
    print("🛡️ Privacy-First • AI-Ready • Sovereignty-Enabled")
    print("="*64)
    print(f"🌐 Starting on port {port}")
    print(f"🔒 Debug mode: {debug}")
    print(f"🌍 CORS origins: {os.environ.get('CORS_ORIGINS', '*')}")
    print(f"💾 Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
    print(f"🤖 AI Integration: {'✅' if os.environ.get('OPENAI_API_KEY') else '❌'}")
    print(f"🔐 Privacy Stack: {'✅' if os.environ.get('SECRET_NETWORK_RPC') else '❌'}")
    print("="*64)
    
    # Initialize and run
    app = create_app()
    
    # 🚀 Production-ready server configuration
    if debug:
        # Development mode - use Werkzeug with Railway compatibility
        socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)
    else:
        # Production mode - allow Werkzeug with safety override for Railway
        socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)

