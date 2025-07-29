from flask import Blueprint

market_bp = Blueprint('market', __name__)

@market_bp.route('/health')
def health():
    return {'status': 'market routes ready'}

