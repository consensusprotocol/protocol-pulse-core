"""
Voice ops Flask blueprint.

Endpoints (all require login + admin):
  POST /api/voice/command   — text command in, JSON {reply, tool_calls, engine} out
  POST /api/voice/speak     — text in, MP3 audio out (ElevenLabs PBX voice)
  POST /api/voice/full      — text in, audio bytes out + reply text in header (one-shot)
  GET  /api/voice/health    — diagnostic

STT happens in the browser (Web Speech API). Reasoning is Claude function-calling
with Gemini fallback (see services/satomi_voice_ops.py).
"""
import os
import logging
import json
import base64
from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
import urllib.request

logger = logging.getLogger(__name__)

voice_ops_bp = Blueprint('voice_ops', __name__)

ELEVEN_VOICE_ID = 'HmUVvDlHsEz0m3eUGLgu'  # PBX voice clone
ELEVEN_API = 'https://api.elevenlabs.io/v1'


def _admin_only():
    if not getattr(current_user, 'is_authenticated', False):
        return jsonify({'error': 'Auth required'}), 401
    if not getattr(current_user, 'is_admin', False):
        return jsonify({'error': 'Admin only'}), 403
    return None


def _eleven_tts(text: str) -> bytes:
    """Synthesize text -> MP3 bytes via ElevenLabs PBX voice."""
    api_key = os.environ.get('ELEVENLABS_API_KEY', '').strip() or os.environ.get('ELEVEN_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('ELEVENLABS_API_KEY not set')
    body = {
        'text': text,
        'model_id': 'eleven_turbo_v2_5',
        'voice_settings': {
            'stability': 0.55,
            'similarity_boost': 0.80,
            'style': 0.15,
            'use_speaker_boost': True,
        },
    }
    req = urllib.request.Request(
        f'{ELEVEN_API}/text-to-speech/{ELEVEN_VOICE_ID}',
        data=json.dumps(body).encode(),
        headers={
            'xi-api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


@voice_ops_bp.route('/api/voice/health')
@login_required
def voice_health():
    err = _admin_only()
    if err:
        return err
    return jsonify({
        'ok': True,
        'anthropic_key': bool(os.environ.get('ANTHROPIC_API_KEY')),
        'gemini_key': bool(os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')),
        'elevenlabs_key': bool(os.environ.get('ELEVENLABS_API_KEY') or os.environ.get('ELEVEN_API_KEY')),
        'voice_id': ELEVEN_VOICE_ID,
    })


@voice_ops_bp.route('/api/voice/command', methods=['POST'])
@login_required
def voice_command():
    """Text command -> tool execution -> text reply (no audio)."""
    err = _admin_only()
    if err:
        return err
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'ok': False, 'error': 'No text'}), 400

    try:
        from pp_services.satomi_voice_ops import process_command
        result = process_command(text, current_user)
        logger.info('voice cmd by %s: %r -> %r [%s]', current_user.email, text[:80], result.get('reply','')[:80], result.get('engine'))
        return jsonify(result)
    except Exception as e:
        logger.exception('voice_command failed')
        return jsonify({'ok': False, 'error': str(e), 'reply': "Something went wrong on my end."}), 500


@voice_ops_bp.route('/api/voice/speak', methods=['POST'])
@login_required
def voice_speak():
    """Text -> MP3 audio bytes."""
    err = _admin_only()
    if err:
        return err
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        audio = _eleven_tts(text)
        return Response(audio, mimetype='audio/mpeg')
    except Exception as e:
        logger.exception('voice_speak failed')
        return jsonify({'error': str(e)}), 500


@voice_ops_bp.route('/api/voice/full', methods=['POST'])
@login_required
def voice_full():
    """One-shot: text command in, JSON with text reply + base64 audio out."""
    err = _admin_only()
    if err:
        return err
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    speak = bool(data.get('speak', True))
    if not text:
        return jsonify({'ok': False, 'error': 'No text'}), 400

    try:
        from pp_services.satomi_voice_ops import process_command
        result = process_command(text, current_user)
        reply_text = result.get('reply', '')
        audio_b64 = ''
        if speak and reply_text:
            try:
                audio_bytes = _eleven_tts(reply_text)
                audio_b64 = base64.b64encode(audio_bytes).decode()
            except Exception as e:
                logger.warning('TTS failed: %s', e)
        result['audio_b64'] = audio_b64
        logger.info('voice full by %s: %r -> %r [%s]', current_user.email, text[:80], reply_text[:80], result.get('engine'))
        return jsonify(result)
    except Exception as e:
        logger.exception('voice_full failed')
        return jsonify({'ok': False, 'error': str(e)}), 500
