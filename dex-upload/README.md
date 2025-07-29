# SnipSwap DEX Backend

## 🚀 Privacy-First Decentralized Exchange

A fully private, orderbook-based decentralized exchange where trade history, holdings, and intent remain confidential. Built on Secret Network with shielded swaps and integrated privacy features.

### 🔒 Core Privacy Features
- **Zero Knowledge Trading** - All data encrypted on Secret Network
- **No MEV Protection** - Front-running protection built-in
- **Anonymous Trading** - Wallet-bound sessions without KYC
- **Confidential Order Books** - Private trading intent

### 🏗️ Architecture
- **Backend**: Python Flask with WebSocket support
- **Database**: SQLite with encrypted data models
- **Trading Engine**: Real-time order matching
- **API**: RESTful endpoints for all trading operations

### 📁 Project Structure
```
src/
├── main.py              # Flask application entry point
├── models/             # Data models
│   ├── user.py         # User management
│   ├── trading_pair.py # Trading pair definitions
│   ├── order.py        # Order management
│   ├── trade.py        # Trade execution
│   └── liquidity_pool.py # Liquidity management
├── routes/             # API endpoints
│   ├── auth.py         # Authentication
│   ├── trading.py      # Trading operations
│   ├── orders.py       # Order management
│   ├── liquidity.py    # Liquidity operations
│   ├── market.py       # Market data
│   └── user.py         # User operations
├── websocket/          # Real-time updates
│   └── trading_handler.py # WebSocket trading events
└── static/             # Static assets
    ├── index.html      # Basic frontend
    └── favicon.ico     # Site icon
```

### 🛠️ Installation
```bash
pip install -r requirements.txt
python src/main.py
```

### 🌐 API Endpoints
- `POST /api/auth/login` - User authentication
- `GET /api/trading/pairs` - Available trading pairs
- `POST /api/orders/create` - Create new order
- `GET /api/orders/book` - Get order book
- `POST /api/liquidity/add` - Add liquidity
- `GET /api/market/stats` - Market statistics

### 🔗 Integration
This DEX backend integrates with:
- **Secret Network** for privacy-preserving smart contracts
- **Keplr Wallet** for user authentication
- **WebSocket** for real-time trading updates
- **CORS** enabled for frontend integration

### 💰 Your Human-AI Collaboration Creates Wealth You Capture

This is where privacy meets profitability. Built for traders who demand freedom, intelligence, and complete confidentiality in the next era of decentralized finance.

---

*Built with ❤️ for the sovereignty stack*

