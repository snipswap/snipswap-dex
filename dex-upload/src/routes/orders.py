from flask import Blueprint

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/health')
def health():
    return {'status': 'orders routes ready'}

