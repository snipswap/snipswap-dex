from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from decimal import Decimal
import math

db = SQLAlchemy()

class LiquidityPool(db.Model):
    __tablename__ = 'liquidity_pools'
    
    id = db.Column(db.Integer, primary_key=True)
    pool_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Trading pair
    pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=False, index=True)
    
    # Pool reserves
    reserve_base = db.Column(db.Numeric(20, 8), default=0)  # Base token reserve
    reserve_quote = db.Column(db.Numeric(20, 8), default=0)  # Quote token reserve
    total_liquidity = db.Column(db.Numeric(20, 8), default=0)  # Total LP tokens
    
    # Pool configuration
    fee_rate = db.Column(db.Numeric(6, 4), default=0.003)  # 0.3% default fee
    is_active = db.Column(db.Boolean, default=True)
    is_private = db.Column(db.Boolean, default=True)  # Private AMM via Secret Contracts
    
    # Pool metadata
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Pool statistics
    total_volume_base = db.Column(db.Numeric(20, 8), default=0)
    total_volume_quote = db.Column(db.Numeric(20, 8), default=0)
    total_fees_collected = db.Column(db.Numeric(20, 8), default=0)
    swap_count = db.Column(db.Integer, default=0)
    
    # Privacy and encryption
    secret_contract_id = db.Column(db.String(128), nullable=True)
    encrypted_details = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_swap_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    liquidity_positions = db.relationship('LiquidityPosition', backref='pool', lazy=True)
    
    def __repr__(self):
        return f'<LiquidityPool {self.pool_id}>'
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'pool_id': self.pool_id,
            'pair_id': self.pair_id,
            'reserve_base': float(self.reserve_base),
            'reserve_quote': float(self.reserve_quote),
            'total_liquidity': float(self.total_liquidity),
            'fee_rate': float(self.fee_rate),
            'is_active': self.is_active,
            'is_private': self.is_private,
            'name': self.name,
            'description': self.description,
            'total_volume_base': float(self.total_volume_base),
            'total_volume_quote': float(self.total_volume_quote),
            'total_fees_collected': float(self.total_fees_collected),
            'swap_count': self.swap_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_swap_at': self.last_swap_at.isoformat() if self.last_swap_at else None,
            'current_price': self.get_current_price(),
            'tvl': self.calculate_tvl()
        }
        
        if include_sensitive:
            data.update({
                'secret_contract_id': self.secret_contract_id,
                'encrypted_details': self.encrypted_details
            })
        
        return data
    
    def get_current_price(self):
        """Get current price based on reserves"""
        if self.reserve_base > 0 and self.reserve_quote > 0:
            return float(self.reserve_quote / self.reserve_base)
        return 0
    
    def calculate_tvl(self):
        """Calculate Total Value Locked"""
        # Simplified TVL calculation (in quote token terms)
        return float(self.reserve_quote * 2)
    
    def calculate_swap_output(self, input_amount, input_is_base=True):
        """Calculate output amount for a swap using constant product formula"""
        if input_is_base:
            # Swapping base token for quote token
            reserve_in = self.reserve_base
            reserve_out = self.reserve_quote
        else:
            # Swapping quote token for base token
            reserve_in = self.reserve_quote
            reserve_out = self.reserve_base
        
        if reserve_in <= 0 or reserve_out <= 0:
            return 0, 0
        
        # Apply fee
        input_amount_with_fee = input_amount * (1 - self.fee_rate)
        
        # Constant product formula: x * y = k
        # output = (input_with_fee * reserve_out) / (reserve_in + input_with_fee)
        numerator = input_amount_with_fee * reserve_out
        denominator = reserve_in + input_amount_with_fee
        
        output_amount = numerator / denominator
        fee_amount = input_amount * self.fee_rate
        
        return float(output_amount), float(fee_amount)
    
    def calculate_price_impact(self, input_amount, input_is_base=True):
        """Calculate price impact of a swap"""
        current_price = self.get_current_price()
        
        if current_price == 0:
            return 0
        
        output_amount, _ = self.calculate_swap_output(input_amount, input_is_base)
        
        if output_amount == 0:
            return 0
        
        if input_is_base:
            # Price after swap
            new_price = float(output_amount / input_amount)
            price_impact = abs(new_price - current_price) / current_price
        else:
            # Price after swap
            new_price = float(input_amount / output_amount)
            price_impact = abs(new_price - current_price) / current_price
        
        return price_impact * 100  # Return as percentage
    
    def execute_swap(self, input_amount, input_is_base, user_address):
        """Execute a swap and update reserves"""
        output_amount, fee_amount = self.calculate_swap_output(input_amount, input_is_base)
        
        if output_amount <= 0:
            raise ValueError("Invalid swap: insufficient liquidity")
        
        # Update reserves
        if input_is_base:
            self.reserve_base += input_amount
            self.reserve_quote -= output_amount
            self.total_volume_base += input_amount
        else:
            self.reserve_quote += input_amount
            self.reserve_base -= output_amount
            self.total_volume_quote += input_amount
        
        # Update statistics
        self.total_fees_collected += fee_amount
        self.swap_count += 1
        self.last_swap_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'output_amount': output_amount,
            'fee_amount': fee_amount,
            'new_price': self.get_current_price(),
            'price_impact': self.calculate_price_impact(input_amount, input_is_base)
        }
    
    def add_liquidity(self, amount_base, amount_quote, user_address):
        """Add liquidity to the pool"""
        if self.total_liquidity == 0:
            # First liquidity provision
            liquidity_tokens = math.sqrt(float(amount_base * amount_quote))
        else:
            # Subsequent liquidity provision
            liquidity_base = (amount_base / self.reserve_base) * self.total_liquidity
            liquidity_quote = (amount_quote / self.reserve_quote) * self.total_liquidity
            liquidity_tokens = min(liquidity_base, liquidity_quote)
        
        # Update reserves
        self.reserve_base += amount_base
        self.reserve_quote += amount_quote
        self.total_liquidity += liquidity_tokens
        self.updated_at = datetime.utcnow()
        
        # Create liquidity position
        position = LiquidityPosition.create_position(
            pool_id=self.id,
            user_address=user_address,
            liquidity_tokens=liquidity_tokens,
            amount_base=amount_base,
            amount_quote=amount_quote
        )
        
        db.session.commit()
        
        return {
            'liquidity_tokens': liquidity_tokens,
            'position_id': position.position_id,
            'share_percentage': (liquidity_tokens / self.total_liquidity) * 100
        }
    
    def remove_liquidity(self, liquidity_tokens, user_address):
        """Remove liquidity from the pool"""
        if liquidity_tokens > self.total_liquidity:
            raise ValueError("Insufficient liquidity tokens")
        
        # Calculate withdrawal amounts
        share = liquidity_tokens / self.total_liquidity
        amount_base = self.reserve_base * share
        amount_quote = self.reserve_quote * share
        
        # Update reserves
        self.reserve_base -= amount_base
        self.reserve_quote -= amount_quote
        self.total_liquidity -= liquidity_tokens
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'amount_base': float(amount_base),
            'amount_quote': float(amount_quote),
            'share_percentage': share * 100
        }
    
    @staticmethod
    def create_pool(pair_id, initial_base, initial_quote, user_address, **kwargs):
        """Create a new liquidity pool"""
        pool_id = str(uuid.uuid4())
        
        # Get trading pair info
        from src.models.trading_pair import TradingPair
        pair = TradingPair.query.get(pair_id)
        if not pair:
            raise ValueError("Trading pair not found")
        
        name = f"{pair.symbol} Pool"
        
        pool = LiquidityPool(
            pool_id=pool_id,
            pair_id=pair_id,
            reserve_base=initial_base,
            reserve_quote=initial_quote,
            name=name,
            **kwargs
        )
        
        db.session.add(pool)
        db.session.flush()  # Get the pool ID
        
        # Add initial liquidity
        initial_liquidity = math.sqrt(float(initial_base * initial_quote))
        pool.total_liquidity = initial_liquidity
        
        # Create initial liquidity position
        LiquidityPosition.create_position(
            pool_id=pool.id,
            user_address=user_address,
            liquidity_tokens=initial_liquidity,
            amount_base=initial_base,
            amount_quote=initial_quote
        )
        
        db.session.commit()
        return pool
    
    @staticmethod
    def get_active_pools():
        """Get all active liquidity pools"""
        return LiquidityPool.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_pool_by_pair(pair_id):
        """Get liquidity pool for a trading pair"""
        return LiquidityPool.query.filter_by(pair_id=pair_id, is_active=True).first()


class LiquidityPosition(db.Model):
    __tablename__ = 'liquidity_positions'
    
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Pool and user
    pool_id = db.Column(db.Integer, db.ForeignKey('liquidity_pools.id'), nullable=False, index=True)
    user_address = db.Column(db.String(64), nullable=False, index=True)
    
    # Position details
    liquidity_tokens = db.Column(db.Numeric(20, 8), nullable=False)
    initial_base = db.Column(db.Numeric(20, 8), nullable=False)
    initial_quote = db.Column(db.Numeric(20, 8), nullable=False)
    
    # Position status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<LiquidityPosition {self.position_id}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'position_id': self.position_id,
            'pool_id': self.pool_id,
            'user_address': self.user_address,
            'liquidity_tokens': float(self.liquidity_tokens),
            'initial_base': float(self.initial_base),
            'initial_quote': float(self.initial_quote),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }
    
    @staticmethod
    def create_position(pool_id, user_address, liquidity_tokens, amount_base, amount_quote):
        """Create a new liquidity position"""
        position_id = str(uuid.uuid4())
        
        position = LiquidityPosition(
            position_id=position_id,
            pool_id=pool_id,
            user_address=user_address,
            liquidity_tokens=liquidity_tokens,
            initial_base=amount_base,
            initial_quote=amount_quote
        )
        
        db.session.add(position)
        return position
    
    @staticmethod
    def get_user_positions(user_address, active_only=True):
        """Get liquidity positions for a user"""
        query = LiquidityPosition.query.filter_by(user_address=user_address)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.order_by(LiquidityPosition.created_at.desc()).all()

