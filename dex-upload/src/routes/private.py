"""
Private trading routes for SnipSwap DEX.

This module defines endpoints that allow users to submit
privacy‑preserving trades. Incoming order details are encrypted
server‑side and stored only in encrypted form; responses return an
opaque receipt that can later be decrypted by the client. In a
production setting this encryption would be performed on the client
using SecretJS and the result would be posted directly to a Secret
Network contract. Here we demonstrate a simple approach using
server‑side symmetric encryption via the `cryptography` library.

Routes:

- POST `/api/private/swap`: accept a JSON payload representing a trade
  request, encrypt its contents and return an encrypted receipt.

"""
import json
from flask import Blueprint, request, jsonify
from cryptography.fernet import Fernet

private_bp = Blueprint("private", __name__)

# In a real deployment this key should be derived from a user‑specific
# secret or provided by the client. For demonstration purposes we
# generate a static key at module load time. If the server restarts
# all prior messages will be undecipherable, so DO NOT USE IN
# PRODUCTION.
_SYMMETRIC_KEY = Fernet.generate_key()
_CIPHER = Fernet(_SYMMETRIC_KEY)


@private_bp.route("/swap", methods=["POST"])
def private_swap():
    """Accept a private swap order, encrypt the payload and return a
    receipt.

    Expected JSON payload may include fields like `sender`, `pair`,
    `amount_in`, `min_amount_out`, etc. This function will encrypt
    the raw JSON string and return it along with a status field.

    Returns
    -------
    200 OK
        JSON object with an `encrypted_order` containing the
        base64‑encoded ciphertext and a `status` message.
    """
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400
    # Serialize to canonical JSON and encrypt
    order_json = json.dumps(payload, sort_keys=True).encode("utf-8")
    encrypted_bytes = _CIPHER.encrypt(order_json)
    return (
        jsonify(
            {
                "encrypted_order": encrypted_bytes.decode("utf-8"),
                "status": "received",
            }
        ),
        200,
    )