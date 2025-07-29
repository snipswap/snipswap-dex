from flask import Blueprint

liquidity_bp = Blueprint('liquidity', __name__)

@liquidity_bp.route('/health')
def health():
    return {'status': 'liquidity routes ready'}

