from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class TradingPair(db.Model):
    __tablename__ = 'trading_pairs'
    
    id = db.Column(db.Integer, primary_key=True)
    pair_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    
    # Token information
    base_token = db.Column(db.String(64), nullable=False)  # e.g., SCRT
    quote_token = db.Column(db.String(64), nullable=False)  # e.g., USDT
    base_token_address = db.Column(db.String(128), nullable=True)
    quote_token_address = db.Column(db.String(128), nullable=True)
    
    # Pair metadata
    symbol = db.Column(db.String(32), nullable=False, index=True)  # e.g., SCRT/USDT
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Trading configuration
    is_active = db.Column(db.Boolean, default=True)
    is_private = db.Column(db.Boolean, default=True)  # Private trading via Secret Contracts
    min_order_size = db.Column(db.Numeric(20, 8), default=0.00000001)
    max_order_size = db.Column(db.Numeric(20, 8), nullable=True)
    price_precision = db.Column(db.Integer, default=8)
    quantity_precision = db.Column(db.Integer, default=8)
    
    # Market data
    last_price = db.Column(db.Numeric(20, 8), default=0)
    price_change_24h = db.Column(db.Numeric(10, 4), default=0)  # Percentage
    volume_24h_base = db.Column(db.Numeric(20, 8), default=0)
    volume_24h_quote = db.Column(db.Numeric(20, 8), default=0)
    high_24h = db.Column(db.Numeric(20, 8), default=0)
    low_24h = db.Column(db.Numeric(20, 8), default=0)
    
    # Liquidity information
    total_liquidity = db.Column(db.Numeric(20, 8), default=0)
    liquidity_base = db.Column(db.Numeric(20, 8), default=0)
    liquidity_quote = db.Column(db.Numeric(20, 8), default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_trade_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    orders = db.relationship('Order', backref='trading_pair', lazy=True)
    trades = db.relationship('Trade', backref='trading_pair', lazy=True)
    liquidity_pools = db.relationship('LiquidityPool', backref='trading_pair', lazy=True)
    
    def __repr__(self):
        return f'<TradingPair {self.symbol}>'
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'pair_id': self.pair_id,
            'base_token': self.base_token,
            'quote_token': self.quote_token,
            'symbol': self.symbol,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'is_private': self.is_private,
            'min_order_size': float(self.min_order_size),
            'max_order_size': float(self.max_order_size) if self.max_order_size else None,
            'price_precision': self.price_precision,
            'quantity_precision': self.quantity_precision,
            'last_price': float(self.last_price),
            'price_change_24h': float(self.price_change_24h),
            'volume_24h_base': float(self.volume_24h_base),
            'volume_24h_quote': float(self.volume_24h_quote),
            'high_24h': float(self.high_24h),
            'low_24h': float(self.low_24h),
            'total_liquidity': float(self.total_liquidity),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_trade_at': self.last_trade_at.isoformat() if self.last_trade_at else None
        }
        
        if include_sensitive:
            data.update({
                'base_token_address': self.base_token_address,
                'quote_token_address': self.quote_token_address,
                'liquidity_base': float(self.liquidity_base),
                'liquidity_quote': float(self.liquidity_quote)
            })
        
        return data
    
    def update_market_data(self, price, volume_base, volume_quote):
        """Update market data after a trade"""
        old_price = float(self.last_price)
        self.last_price = price
        self.last_trade_at = datetime.utcnow()
        
        # Update 24h high/low
        if price > self.high_24h:
            self.high_24h = price
        if price < self.low_24h or self.low_24h == 0:
            self.low_24h = price
        
        # Update volume (this would be more complex in production)
        self.volume_24h_base += volume_base
        self.volume_24h_quote += volume_quote
        
        # Calculate price change
        if old_price > 0:
            self.price_change_24h = ((float(price) - old_price) / old_price) * 100
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_orderbook(self, depth=20):
        """Get orderbook for this trading pair"""
        from src.models.order import Order
        
        # Get buy orders (bids) - highest price first
        buy_orders = Order.query.filter_by(
            pair_id=self.id,
            side='buy',
            status='open'
        ).order_by(Order.price.desc()).limit(depth).all()
        
        # Get sell orders (asks) - lowest price first
        sell_orders = Order.query.filter_by(
            pair_id=self.id,
            side='sell',
            status='open'
        ).order_by(Order.price.asc()).limit(depth).all()
        
        return {
            'bids': [[float(order.price), float(order.remaining_quantity)] for order in buy_orders],
            'asks': [[float(order.price), float(order.remaining_quantity)] for order in sell_orders],
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_recent_trades(self, limit=50):
        """Get recent trades for this pair"""
        from src.models.trade import Trade
        
        trades = Trade.query.filter_by(
            pair_id=self.id
        ).order_by(Trade.executed_at.desc()).limit(limit).all()
        
        return [trade.to_dict() for trade in trades]
    
    def calculate_spread(self):
        """Calculate bid-ask spread"""
        orderbook = self.get_orderbook(depth=1)
        
        if orderbook['bids'] and orderbook['asks']:
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            spread = best_ask - best_bid
            spread_percentage = (spread / best_ask) * 100 if best_ask > 0 else 0
            
            return {
                'spread': spread,
                'spread_percentage': spread_percentage,
                'best_bid': best_bid,
                'best_ask': best_ask
            }
        
        return None
    
    @staticmethod
    def get_active_pairs():
        """Get all active trading pairs"""
        return TradingPair.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_pair_by_symbol(symbol):
        """Get trading pair by symbol"""
        return TradingPair.query.filter_by(symbol=symbol, is_active=True).first()
    
    @staticmethod
    def create_pair(base_token, quote_token, **kwargs):
        """Create a new trading pair"""
        import uuid
        
        pair_id = str(uuid.uuid4())[:8]
        symbol = f"{base_token}/{quote_token}"
        name = f"{base_token} / {quote_token}"
        
        pair = TradingPair(
            pair_id=pair_id,
            base_token=base_token,
            quote_token=quote_token,
            symbol=symbol,
            name=name,
            **kwargs
        )
        
        db.session.add(pair)
        db.session.commit()
        return pair

