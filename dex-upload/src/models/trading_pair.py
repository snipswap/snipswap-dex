"""In‑memory TradingPair model for SnipSwap.

This stub implementation provides minimal functionality to satisfy
the Flask routes defined in ``src/routes/market.py``.  It defines
static sample trading pairs along with helper methods to return
order books and recent trades.  The API mirrors a subset of what a
SQLAlchemy model might expose: a class attribute ``query`` with a
``filter_by`` method returning an object with ``all`` and ``first``
methods, instance attributes such as ``symbol``, ``price`` and
``volume``, and instance methods ``to_dict``, ``get_orderbook`` and
``get_recent_trades``.

The sample data can be replaced or extended to suit your testing
needs.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


class _QueryProxy:
    """Proxy to mimic SQLAlchemy query interface for TradingPair."""

    def __init__(self, pairs: List['TradingPair']):
        self._pairs = pairs

    def filter_by(self, **kwargs) -> '_QueryProxy':
        # Support filtering by symbol (case insensitive) and is_active
        filtered = self._pairs
        for key, value in kwargs.items():
            if key == 'symbol':
                filtered = [p for p in filtered if p.symbol.upper() == str(value).upper()]
            elif key == 'is_active':
                filtered = [p for p in filtered if p.is_active == value]
        return _QueryProxy(filtered)

    def all(self) -> List['TradingPair']:
        return list(self._pairs)

    def first(self) -> Optional['TradingPair']:
        return self._pairs[0] if self._pairs else None


class TradingPair:
    """Simple representation of a trading pair."""

    # Sample static data for active trading pairs.
    _sample_pairs: List['TradingPair'] = []

    def __init__(self, symbol: str, price: float, change: float, volume: float, is_active: bool = True):
        self.id: int = len(TradingPair._sample_pairs) + 1
        self.symbol: str = symbol.upper()
        self.price: float = price
        self.change: float = change
        self.volume: float = volume
        self.is_active: bool = is_active

    @property
    def positive(self) -> bool:
        return self.change >= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'price': f"{self.price:.4f}",
            'change': f"{self.change:+.4f}",
            'positive': self.positive,
            'volume': f"{self.volume:.2f}",
            'is_active': self.is_active,
        }

    def get_orderbook(self, depth: int = 20) -> Dict[str, List[Dict[str, float]]]:
        """Generate a fake order book for demonstration purposes.

        Creates bids and asks around the current price with random sizes.

        Parameters
        ----------
        depth: int
            Number of price levels to generate for bids and asks.

        Returns
        -------
        dict
            A dictionary with ``bids`` and ``asks`` lists.
        """
        bids: List[Dict[str, float]] = []
        asks: List[Dict[str, float]] = []
        # Generate bids: slightly below the current price
        base_price = self.price
        for i in range(depth):
            price = base_price * (1 - (i + 1) * 0.001)
            quantity = random.uniform(1, 50)
            bids.append({'price': price, 'quantity': quantity})
        # Generate asks: slightly above the current price
        for i in range(depth):
            price = base_price * (1 + (i + 1) * 0.001)
            quantity = random.uniform(1, 50)
            asks.append({'price': price, 'quantity': quantity})
        return {'bids': bids, 'asks': asks}

    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Generate fake recent trades for demonstration.

        Produces a list of trade dictionaries with timestamps
        decreasing from now.  Sides alternate between buy and sell.

        Parameters
        ----------
        limit: int
            Number of trades to generate.

        Returns
        -------
        list
            A list of trade objects.
        """
        trades: List[Dict[str, Any]] = []
        now = datetime.utcnow()
        for i in range(limit):
            side = 'buy' if i % 2 == 0 else 'sell'
            # Price slightly varies around current price
            price_variation = (random.random() - 0.5) * 0.01 * self.price
            price = self.price + price_variation
            quantity = random.uniform(0.1, 10)
            timestamp = now - timedelta(seconds=i * 30)
            trades.append(
                {
                    'price': price,
                    'quantity': quantity,
                    'side': side,
                    'timestamp': timestamp.isoformat() + 'Z',
                }
            )
        return trades

    # Class level query proxy mimicking SQLAlchemy
    query: _QueryProxy = None  # type: ignore


# Populate the sample pairs when module is imported
def _init_sample_pairs():
    if TradingPair._sample_pairs:
        return
    # Define some plausible default pairs
    samples = [
        ('SCRT/USDT', 0.50, 0.01, 10000.0),
        ('SHD/USDT', 5.25, -0.12, 7500.0),
        ('OSMO/USDT', 0.90, 0.05, 8300.0),
        ('ATOM/USDT', 8.30, 0.20, 11000.0),
    ]
    for symbol, price, change, volume in samples:
        TradingPair._sample_pairs.append(TradingPair(symbol, price, change, volume))
    TradingPair.query = _QueryProxy(TradingPair._sample_pairs)


_init_sample_pairs()