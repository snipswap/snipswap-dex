from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Trade(db.Model):
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Trading pair and orders
    pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=False, index=True)
    buy_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    sell_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    
    # Trade participants (encrypted for privacy)
    buyer_address = db.Column(db.String(64), nullable=False, index=True)
    seller_address = db.Column(db.String(64), nullable=False, index=True)
    
    # Trade execution details
    price = db.Column(db.Numeric(20, 8), nullable=False)
    quantity = db.Column(db.Numeric(20, 8), nullable=False)
    total_value = db.Column(db.Numeric(20, 8), nullable=False)
    
    # Privacy and encryption
    is_private = db.Column(db.Boolean, default=True)
    encrypted_details = db.Column(db.Text, nullable=True)  # Encrypted trade details
    secret_contract_tx = db.Column(db.String(128), nullable=True)  # Secret Network transaction
    
    # Fees
    buyer_fee = db.Column(db.Numeric(20, 8), default=0)
    seller_fee = db.Column(db.Numeric(20, 8), default=0)
    total_fees = db.Column(db.Numeric(20, 8), default=0)
    fee_currency = db.Column(db.String(10), default='SCRT')
    
    # Trade metadata
    trade_type = db.Column(db.String(20), default='spot')  # spot, margin, futures
    settlement_status = db.Column(db.String(20), default='pending')  # pending, settled, failed
    
    # Timestamps
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    settled_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Trade {self.trade_id} {self.quantity} @ {self.price}>'
    
    def to_dict(self, include_private=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'trade_id': self.trade_id,
            'pair_id': self.pair_id,
            'price': float(self.price),
            'quantity': float(self.quantity),
            'total_value': float(self.total_value),
            'is_private': self.is_private,
            'total_fees': float(self.total_fees),
            'fee_currency': self.fee_currency,
            'trade_type': self.trade_type,
            'settlement_status': self.settlement_status,
            'executed_at': self.executed_at.isoformat(),
            'settled_at': self.settled_at.isoformat() if self.settled_at else None
        }
        
        if include_private:
            data.update({
                'buy_order_id': self.buy_order_id,
                'sell_order_id': self.sell_order_id,
                'buyer_address': self.buyer_address,
                'seller_address': self.seller_address,
                'buyer_fee': float(self.buyer_fee),
                'seller_fee': float(self.seller_fee),
                'encrypted_details': self.encrypted_details,
                'secret_contract_tx': self.secret_contract_tx
            })
        
        return data
    
    def to_public_dict(self):
        """Convert to public dictionary (no private information)"""
        return {
            'trade_id': self.trade_id,
            'price': float(self.price),
            'quantity': float(self.quantity),
            'executed_at': self.executed_at.isoformat(),
            'side': 'unknown'  # Don't reveal trade direction for privacy
        }
    
    def settle_trade(self):
        """Mark trade as settled"""
        self.settlement_status = 'settled'
        self.settled_at = datetime.utcnow()
        db.session.commit()
    
    def fail_settlement(self):
        """Mark trade settlement as failed"""
        self.settlement_status = 'failed'
        db.session.commit()
    
    @staticmethod
    def create_trade(buy_order, sell_order, execution_price, execution_quantity):
        """Create a new trade from matched orders"""
        trade_id = str(uuid.uuid4())
        total_value = execution_price * execution_quantity
        
        # Calculate fees (0.1% for each side)
        fee_rate = 0.001
        buyer_fee = total_value * fee_rate
        seller_fee = execution_quantity * execution_price * fee_rate
        total_fees = buyer_fee + seller_fee
        
        trade = Trade(
            trade_id=trade_id,
            pair_id=buy_order.pair_id,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            buyer_address=buy_order.user_address,
            seller_address=sell_order.user_address,
            price=execution_price,
            quantity=execution_quantity,
            total_value=total_value,
            buyer_fee=buyer_fee,
            seller_fee=seller_fee,
            total_fees=total_fees,
            is_private=True  # All trades are private by default
        )
        
        db.session.add(trade)
        db.session.commit()
        return trade
    
    @staticmethod
    def get_user_trades(user_address, pair_id=None, limit=50):
        """Get trades for a specific user"""
        query = Trade.query.filter(
            db.or_(
                Trade.buyer_address == user_address,
                Trade.seller_address == user_address
            )
        )
        
        if pair_id:
            query = query.filter_by(pair_id=pair_id)
        
        return query.order_by(Trade.executed_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_pair_trades(pair_id, limit=100, include_private=False):
        """Get trades for a specific trading pair"""
        query = Trade.query.filter_by(pair_id=pair_id)
        
        if not include_private:
            query = query.filter_by(is_private=False)
        
        return query.order_by(Trade.executed_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_trade_history(pair_id, start_time=None, end_time=None):
        """Get trade history for analysis"""
        query = Trade.query.filter_by(pair_id=pair_id)
        
        if start_time:
            query = query.filter(Trade.executed_at >= start_time)
        
        if end_time:
            query = query.filter(Trade.executed_at <= end_time)
        
        return query.order_by(Trade.executed_at.asc()).all()
    
    @staticmethod
    def calculate_volume_24h(pair_id):
        """Calculate 24-hour trading volume"""
        from datetime import timedelta
        
        start_time = datetime.utcnow() - timedelta(hours=24)
        
        trades = Trade.query.filter(
            Trade.pair_id == pair_id,
            Trade.executed_at >= start_time,
            Trade.settlement_status == 'settled'
        ).all()
        
        total_volume = sum(float(trade.total_value) for trade in trades)
        total_quantity = sum(float(trade.quantity) for trade in trades)
        
        return {
            'volume_quote': total_volume,
            'volume_base': total_quantity,
            'trade_count': len(trades)
        }
    
    @staticmethod
    def get_price_data(pair_id, interval='1h', limit=100):
        """Get OHLCV price data for charting"""
        from datetime import timedelta
        
        # This is a simplified implementation
        # In production, you'd use proper time-series aggregation
        
        trades = Trade.query.filter_by(
            pair_id=pair_id
        ).order_by(Trade.executed_at.desc()).limit(limit * 10).all()
        
        if not trades:
            return []
        
        # Group trades by time intervals
        price_data = []
        current_candle = None
        
        for trade in reversed(trades):  # Process chronologically
            trade_time = trade.executed_at
            price = float(trade.price)
            volume = float(trade.quantity)
            
            # Create new candle if needed
            if not current_candle:
                current_candle = {
                    'timestamp': trade_time.isoformat(),
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                }
            else:
                # Update current candle
                current_candle['high'] = max(current_candle['high'], price)
                current_candle['low'] = min(current_candle['low'], price)
                current_candle['close'] = price
                current_candle['volume'] += volume
        
        if current_candle:
            price_data.append(current_candle)
        
        return price_data[-limit:] if len(price_data) > limit else price_data

