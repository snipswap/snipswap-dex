"""In‑memory Order model for SnipSwap.

This stub defines a simple ``Order`` class used by the ``orders``
blueprint to create and store orders in memory.  It provides a
minimal API similar to what a SQLAlchemy model might expose,
including a class method ``create_order`` that returns a new order
instance.  Orders are stored in a class level list for retrieval if
needed.  The ``db`` object contains a ``session`` with ``add`` and
``commit`` methods that are no‑ops, satisfying references in the
Flask routes without requiring an actual database connection.
"""

from __future__ import annotations

from typing import List, Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class _DBSession:
    """No‑op session stub mimicking SQLAlchemy's session."""

    def add(self, instance: Any) -> None:
        # In a real implementation this would add the instance to the DB
        return None

    def commit(self) -> None:
        # In a real implementation this would commit the transaction
        return None


@dataclass
class _DB:
    """Database stub with a session attribute."""

    session: _DBSession = field(default_factory=_DBSession)


db = _DB()


@dataclass
class Order:
    """Simple in‑memory order representation."""

    order_id: int
    user_address: str
    pair_id: int
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    is_private: bool = False
    encrypted_details: Optional[str] = None

    # Class‑level list to store orders
    _orders: List['Order'] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def create_order(cls, **kwargs: Dict[str, Any]) -> 'Order':
        """Create and persist a new order in memory.

        Parameters
        ----------
        **kwargs: dict
            Keyword arguments corresponding to the order fields.

        Returns
        -------
        Order
            The newly created order instance.
        """
        # Generate a new order ID sequentially
        new_id = len(cls._orders) + 1
        order = cls(order_id=new_id, **kwargs)
        cls._orders.append(order)
        # Mimic SQLAlchemy behaviour of adding to session then committing
        db.session.add(order)
        db.session.commit()
        return order

    @classmethod
    def get_order_by_id(cls, order_id: int) -> Optional['Order']:
        for order in cls._orders:
            if order.order_id == order_id:
                return order
        return None