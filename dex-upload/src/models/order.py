from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from decimal import Decimal

db = SQLAlchemy()

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Trading pair and user
    pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=False, index=True)
    user_address = db.Column(db.String(64), nullable=False, index=True)
    
    # Order details
    side = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    order_type = db.Column(db.String(20), nullable=False)  # 'market', 'limit', 'stop_loss', 'take_profit'
    price = db.Column(db.Numeric(20, 8), nullable=False)
    quantity = db.Column(db.Numeric(20, 8), nullable=False)
    remaining_quantity = db.Column(db.Numeric(20, 8), nullable=False)
    filled_quantity = db.Column(db.Numeric(20, 8), default=0)
    
    # Order status and execution
    status = db.Column(db.String(20), default='pending')  # pending, open, filled, cancelled, expired
    time_in_force = db.Column(db.String(10), default='GTC')  # GTC, IOC, FOK
    
    # Privacy and encryption
    is_private = db.Column(db.Boolean, default=True)
    encrypted_details = db.Column(db.Text, nullable=True)  # Encrypted order details
    secret_contract_id = db.Column(db.String(128), nullable=True)  # Secret Network contract
    
    # Pricing and fees
    average_fill_price = db.Column(db.Numeric(20, 8), default=0)
    total_fees = db.Column(db.Numeric(20, 8), default=0)
    fee_currency = db.Column(db.String(10), default='SCRT')
    
    # Stop orders
    stop_price = db.Column(db.Numeric(20, 8), nullable=True)
    trigger_condition = db.Column(db.String(20), nullable=True)  # 'above', 'below'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    filled_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    trades = db.relationship('Trade', backref='order', lazy=True)
    
    def __repr__(self):
        return f'<Order {self.order_id} {self.side} {self.quantity} @ {self.price}>'
    
    def to_dict(self, include_private=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'order_id': self.order_id,
            'pair_id': self.pair_id,
            'side': self.side,
            'order_type': self.order_type,
            'price': float(self.price),
            'quantity': float(self.quantity),
            'remaining_quantity': float(self.remaining_quantity),
            'filled_quantity': float(self.filled_quantity),
            'status': self.status,
            'time_in_force': self.time_in_force,
            'is_private': self.is_private,
            'average_fill_price': float(self.average_fill_price),
            'total_fees': float(self.total_fees),
            'fee_currency': self.fee_currency,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None
        }
        
        if include_private:
            data.update({
                'user_address': self.user_address,
                'encrypted_details': self.encrypted_details,
                'secret_contract_id': self.secret_contract_id,
                'stop_price': float(self.stop_price) if self.stop_price else None,
                'trigger_condition': self.trigger_condition
            })
        
        return data
    
    def fill_order(self, fill_quantity, fill_price):
        """Fill order partially or completely"""
        if fill_quantity > self.remaining_quantity:
            raise ValueError("Fill quantity exceeds remaining quantity")
        
        self.filled_quantity += fill_quantity
        self.remaining_quantity -= fill_quantity
        
        # Update average fill price
        total_filled_value = (self.average_fill_price * (self.filled_quantity - fill_quantity)) + (fill_price * fill_quantity)
        self.average_fill_price = total_filled_value / self.filled_quantity
        
        # Update status
        if self.remaining_quantity == 0:
            self.status = 'filled'
            self.filled_at = datetime.utcnow()
        elif self.filled_quantity > 0:
            self.status = 'partially_filled'
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def cancel_order(self):
        """Cancel the order"""
        if self.status in ['filled', 'cancelled']:
            raise ValueError(f"Cannot cancel order with status: {self.status}")
        
        self.status = 'cancelled'
        self.cancelled_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def is_executable(self, market_price):
        """Check if order can be executed at market price"""
        if self.status != 'open':
            return False
        
        if self.order_type == 'market':
            return True
        elif self.order_type == 'limit':
            if self.side == 'buy':
                return market_price <= self.price
            else:  # sell
                return market_price >= self.price
        elif self.order_type in ['stop_loss', 'take_profit']:
            if self.trigger_condition == 'above':
                return market_price >= self.stop_price
            else:  # below
                return market_price <= self.stop_price
        
        return False
    
    def calculate_total_value(self):
        """Calculate total order value"""
        return float(self.quantity * self.price)
    
    def calculate_remaining_value(self):
        """Calculate remaining order value"""
        return float(self.remaining_quantity * self.price)
    
    @staticmethod
    def create_order(user_address, pair_id, side, order_type, quantity, price=None, **kwargs):
        """Create a new order"""
        order_id = str(uuid.uuid4())
        
        order = Order(
            order_id=order_id,
            user_address=user_address,
            pair_id=pair_id,
            side=side,
            order_type=order_type,
            quantity=quantity,
            remaining_quantity=quantity,
            price=price or 0,
            **kwargs
        )
        
        db.session.add(order)
        db.session.commit()
        return order
    
    @staticmethod
    def get_user_orders(user_address, status=None, pair_id=None):
        """Get orders for a specific user"""
        query = Order.query.filter_by(user_address=user_address)
        
        if status:
            query = query.filter_by(status=status)
        
        if pair_id:
            query = query.filter_by(pair_id=pair_id)
        
        return query.order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_open_orders(pair_id=None, side=None):
        """Get all open orders"""
        query = Order.query.filter_by(status='open')
        
        if pair_id:
            query = query.filter_by(pair_id=pair_id)
        
        if side:
            query = query.filter_by(side=side)
        
        return query.order_by(Order.created_at.asc()).all()
    
    @staticmethod
    def match_orders(buy_order, sell_order):
        """Match two orders for execution"""
        if buy_order.side != 'buy' or sell_order.side != 'sell':
            raise ValueError("Invalid order sides for matching")
        
        if buy_order.pair_id != sell_order.pair_id:
            raise ValueError("Orders must be for the same trading pair")
        
        # Check if orders can match
        if buy_order.price >= sell_order.price:
            # Determine execution price (usually the maker's price)
            execution_price = sell_order.price if buy_order.created_at > sell_order.created_at else buy_order.price
            
            # Determine execution quantity
            execution_quantity = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
            
            return {
                'can_match': True,
                'execution_price': execution_price,
                'execution_quantity': execution_quantity,
                'buy_order': buy_order,
                'sell_order': sell_order
            }
        
        return {'can_match': False}
    
    @staticmethod
    def cleanup_expired_orders():
        """Clean up expired orders"""
        expired_orders = Order.query.filter(
            Order.expires_at < datetime.utcnow(),
            Order.status.in_(['open', 'pending'])
        ).all()
        
        for order in expired_orders:
            order.status = 'expired'
            order.updated_at = datetime.utcnow()
        
        db.session.commit()
        return len(expired_orders)

