from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/health')
def health():
    return {'status': 'auth routes ready'}

