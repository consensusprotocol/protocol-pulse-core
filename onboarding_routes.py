from flask import Blueprint, render_template, jsonify, request, session
import secrets
import os

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')

@onboarding_bp.route('/')
def onboarding_start():
    # Ensure CSRF token exists so the ramp page can send it with /api/onboarding/step
    if "csrf_token" not in session:
        session["csrf_token"] = os.urandom(32).hex()
    return render_template('onboarding_ramp.html')

@onboarding_bp.route('/api/session', methods=['POST'])
def create_session():
    session_id = secrets.token_urlsafe(16)
    session['onboarding_id'] = session_id
    if "csrf_token" not in session:
        session["csrf_token"] = os.urandom(32).hex()
    return jsonify({
        'success': True,
        'session_id': session_id,
        'csrf_token': session.get('csrf_token', '')
    })
