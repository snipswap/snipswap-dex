"""
Order management routes for SnipSwap DEX.

This blueprint exposes endpoints for creating and querying orders.  It
supports both public and private orders as well as optional
cross‑chain routing.  Public orders are stored in plaintext within
the database, while private orders are encrypted before storage.

Routes
------
POST `/create`
    Create a new order.  Accepts a JSON body describing the order
    details.  Supports both private and public orders and optional
    cross‑chain bridging.

GET `/health`
    Simple health check for the orders service.
"""

import json
from decimal import Decimal

from flask import Blueprint, request, jsonify

from src.models.order import Order, db  # type: ignore
from src.models.trading_pair import TradingPair  # type: ignore
from src.utils.bridge import send_order_to_chain  # type: ignore
from cryptography.fernet import Fernet


orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/health")
def health() -> dict:
    """Health check endpoint for the orders blueprint."""
    return {"status": "orders routes ready"}


def _encrypt_order_details(details: dict) -> str:
    """Encrypt order details using a one‑time symmetric key.

    This helper uses a per‑call generated key to encrypt the
    serialized order details.  In production the key would be
    negotiated between client and server or derived from the user's
    permit on Secret Network.  The ciphertext is returned as a
    base64‑encoded string.  The key is not returned or stored here
    because this demonstration does not implement key management.

    Parameters
    ----------
    details: dict
        Arbitrary dictionary containing order parameters.

    Returns
    -------
    str
        Base64 encoded ciphertext.
    """
    payload_json = json.dumps(details, sort_keys=True).encode("utf-8")
    key = Fernet.generate_key()
    cipher = Fernet(key)
    encrypted_bytes = cipher.encrypt(payload_json)
    return encrypted_bytes.decode("utf-8")


@orders_bp.route("/create", methods=["POST"])
def create_order():
    """Create a new order (public or private).

    Expected JSON payload:

    .. code-block:: json

        {
          "user_address": "secret1...",   // required
          "pair_symbol": "SCRT/USDT",      // required
          "side": "buy",                 // required: buy or sell
          "order_type": "limit",          // required: market, limit, stop_loss, etc.
          "quantity": 10.5,               // required: numeric quantity
          "price": 0.45,                  // optional for market orders
          "is_private": true,             // optional: default false
          "target_chain": "osmosis-1"     // optional: IBC chain ID for cross‑chain execution
        }

    When ``is_private`` is true the order details are encrypted before
    being persisted.  When ``target_chain`` is provided the order
    payload is forwarded to the specified chain via a stubbed
    bridging function.  In either case a new order record is written
    to the database and the order ID is returned to the caller.

    Returns
    -------
    tuple
        A Flask tuple containing JSON and an HTTP status code.
    """
    data = request.get_json(silent=True) or {}
    # Basic validation of required fields
    required_fields = ["user_address", "pair_symbol", "side", "order_type", "quantity"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    user_address = str(data["user_address"])
    pair_symbol = str(data["pair_symbol"]).upper()
    side = str(data["side"]).lower()
    order_type = str(data["order_type"]).lower()
    # Convert quantity to Decimal via string to avoid float issues
    try:
        quantity = Decimal(str(data["quantity"]))
    except Exception:
        return jsonify({"error": "Invalid quantity"}), 400
    price = data.get("price")
    price_decimal = None
    if price is not None:
        try:
            price_decimal = Decimal(str(price))
        except Exception:
            return jsonify({"error": "Invalid price"}), 400
    is_private = bool(data.get("is_private", False))
    target_chain = data.get("target_chain")

    # Lookup the trading pair
    pair = TradingPair.query.filter_by(symbol=pair_symbol).first()
    if not pair:
        return jsonify({"error": f"Trading pair {pair_symbol} not found"}), 400

    # Build order kwargs for the model
    order_kwargs = {
        "user_address": user_address,
        "pair_id": pair.id,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
    }
    if price_decimal is not None:
        order_kwargs["price"] = price_decimal

    encrypted_details = None
    if is_private:
        # Encrypt full order details for storage
        encrypted_details = _encrypt_order_details(
            {
                "user_address": user_address,
                "pair_symbol": pair_symbol,
                "side": side,
                "order_type": order_type,
                "quantity": str(quantity),
                "price": str(price_decimal) if price_decimal is not None else None,
                "target_chain": target_chain,
            }
        )
        order_kwargs.update({"is_private": True, "encrypted_details": encrypted_details})

    # Create the order in the database
    try:
        order = Order.create_order(**order_kwargs)
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": f"Failed to create order: {exc}"}), 500

    # Forward to another chain if requested
    if target_chain:
        try:
            send_order_to_chain(
                target_chain,
                {
                    "order_id": order.order_id,
                    "pair_symbol": pair_symbol,
                    "side": side,
                    "order_type": order_type,
                    "quantity": str(quantity),
                    "price": str(price_decimal) if price_decimal is not None else None,
                    "is_private": is_private,
                },
            )
        except Exception as exc:
            # Do not fail the order creation if the bridge call fails
            return (
                jsonify(
                    {
                        "order_id": order.order_id,
                        "warning": f"Order created but failed to bridge: {exc}",
                    }
                ),
                201,
            )

    response_data = {"order_id": order.order_id, "status": "created"}
    if is_private:
        response_data["encrypted_details"] = encrypted_details
    return jsonify(response_data), 201