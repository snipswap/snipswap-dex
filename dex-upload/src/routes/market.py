"""
Market data routes for SnipSwap DEX.

This blueprint exposes endpoints for retrieving trading pair
information, order books and recent trades.  Clients can call these
endpoints to populate their user interfaces with real market data.

Routes
------
GET `/api/market/health`
    Health check for the market blueprint.

GET `/api/market/pairs`
    Return all active trading pairs with metadata such as last price
    and volume.

GET `/api/market/orderbook/<symbol>`
    Return the order book for a specific trading pair.  Accepts an
    optional `depth` query parameter to limit the number of price
    levels returned.

GET `/api/market/trades/<symbol>`
    Return recent trades for a specific trading pair.  Accepts an
    optional `limit` query parameter to control the number of trades.
"""

from flask import Blueprint, jsonify, request

from src.models.trading_pair import TradingPair  # type: ignore


market_bp = Blueprint("market", __name__)


@market_bp.route("/health")
def health():
    """Health check endpoint for the market blueprint."""
    return {"status": "market routes ready"}


@market_bp.route("/pairs", methods=["GET"])
def list_pairs():
    """List all active trading pairs.

    Returns a JSON array of objects produced by `TradingPair.to_dict()`,
    including pricing and volume data.
    """
    pairs = TradingPair.query.filter_by(is_active=True).all()
    data = [pair.to_dict() for pair in pairs]
    return jsonify(data)


@market_bp.route("/orderbook/<string:symbol>", methods=["GET"])
def get_orderbook(symbol: str):
    """Return the order book for a given trading pair symbol.

    Parameters
    ----------
    symbol: str
        Trading pair symbol in the form `BASE/QUOTE` (case
        insensitive), e.g. ``SCRT/USDT``.

    Query Parameters
    ----------------
    depth: int, optional
        Number of price levels to include in the order book (default
        20).  Larger values will return more bids and asks.
    """
    pair = TradingPair.query.filter_by(symbol=symbol.upper()).first()
    if not pair:
        return jsonify({"error": f"Trading pair {symbol} not found"}), 404
    depth = request.args.get("depth", default=20, type=int)
    return jsonify(pair.get_orderbook(depth=depth))


@market_bp.route("/trades/<string:symbol>", methods=["GET"])
def get_trades(symbol: str):
    """Return recent trades for a given trading pair symbol.

    Parameters
    ----------
    symbol: str
        Trading pair symbol, e.g. ``SCRT/USDT``.

    Query Parameters
    ----------------
    limit: int, optional
        Number of trades to return (default 50).
    """
    pair = TradingPair.query.filter_by(symbol=symbol.upper()).first()
    if not pair:
        return jsonify({"error": f"Trading pair {symbol} not found"}), 404
    limit = request.args.get("limit", default=50, type=int)
    return jsonify(pair.get_recent_trades(limit=limit))