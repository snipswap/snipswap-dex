"""
SnipSwap DEX Database Models
Proper initialization to avoid circular imports
"""

from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Import all models in the correct order to avoid circular imports
from .user import User
from .trading_pair import TradingPair
from .order import Order
from .trade import Trade
from .privacy_session import PrivacySession

# Export all models
__all__ = [
    'db',
    'User',
    'TradingPair', 
    'Order',
    'Trade',
    'PrivacySession'
]

