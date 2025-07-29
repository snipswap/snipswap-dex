from flask import Blueprint

trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/health')
def health():
    return {'status': 'trading routes ready'}

