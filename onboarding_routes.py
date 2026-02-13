from flask import Blueprint, render_template, jsonify, request, session
import secrets

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')

@onboarding_bp.route('/')
def onboarding_start():
    return render_template('onboarding_ramp.html')

@onboarding_bp.route('/api/session', methods=['POST'])
def create_session():
    session_id = secrets.token_urlsafe(16)
    session['onboarding_id'] = session_id
    return jsonify({'success': True, 'session_id': session_id})
