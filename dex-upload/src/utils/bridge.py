import logging
from typing import Dict, Any, Optional
import requests

# Mapping of chain IDs to example endpoints for bridging.
CROSS_CHAIN_ENDPOINTS: Dict[str, str] = {
    "osmosis-1": "https://osmosis-bridge.example.com/api/bridge",
    "shade-1": "https://shade-bridge.example.com/api/bridge",
}


def send_order_to_chain(chain_id: str, order_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Send an order to another chain via a stubbed HTTP bridge.

    If the chain is not configured in `CROSS_CHAIN_ENDPOINTS` this simply
    logs the order. If an endpoint is configured it will attempt a POST
    request and return the JSON response.
    """
    endpoint = CROSS_CHAIN_ENDPOINTS.get(chain_id)
    if not endpoint:
        logging.info(f"Bridging order to {chain_id}: {order_payload}")
        return None
    try:
        response = requests.post(endpoint, json=order_payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logging.error(f"Failed to bridge order to {chain_id}: {exc}")
        raise
