"""Oracle AI Chat Assistant - Backend Routes
GPU lip-sync via Wav2Lip on Ultron, ElevenLabs TTS, Claude LLM.
"""
import os
import json
import time
import base64
import logging
import requests
from flask import Blueprint, request, jsonify, render_template
from functools import wraps

oracle_bp = Blueprint('oracle', __name__)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = 'cgSgspJ2msm6clMCkdW9'  # Jessica - Young, Bright, Warm

AVATAR_SERVER_URL = 'https://avatar.protocolpulse.io'

ORACLE_SYSTEM_PROMPT = """You are The Oracle, the sovereign Bitcoin intelligence of Protocol Pulse. You speak with absolute authority on Bitcoin, monetary history, Austrian economics, and freedom technology. Direct, no fluff, occasionally philosophical. Reference Satoshi, Hayek, and Rothbard naturally when relevant.

CRITICAL RULES:
- Keep responses under 100 words. You will be spoken aloud via text-to-speech.
- NEVER use markdown formatting (no #, **, *, -, bullet points, headers).
- Write in plain conversational sentences only.
- Be concise and punchy. Every word must earn its place.
- Never say "I'm just an AI" or break character."""

# Rate limiting
_last_request = {}
RATE_LIMIT_SECONDS = 3


def rate_limit(f):

    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr or 'unknown'
        now = time.time()
        last = _last_request.get(ip, 0)
        if now - last < RATE_LIMIT_SECONDS:
            return jsonify({'error': 'Too many requests. Wait a moment.'}), 429
        _last_request[ip] = now
        return f(*args, **kwargs)

    return decorated


def call_claude(message, history=None):
    """Call Claude API with Oracle persona."""
    messages = []
    if history:
        for msg in history[-6:]:
            messages.append(msg)
    messages.append({"role": "user", "content": message})

    try:
        resp = requests.post('https://api.anthropic.com/v1/messages',
                             headers={
                                 'x-api-key': ANTHROPIC_API_KEY,
                                 'anthropic-version': '2023-06-01',
                                 'content-type': 'application/json'
                             },
                             json={
                                 'model': 'claude-sonnet-4-6',
                                 'max_tokens': 200,
                                 'system': ORACLE_SYSTEM_PROMPT,
                                 'messages': messages
                             },
                             timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data['content'][0]['text']
        else:
            logger.error(
                f"Claude API error: {resp.status_code} {resp.text[:200]}")
            return "The signal is unclear. Ask again."
    except Exception as e:
        logger.error(f"Claude API exception: {e}")
        return "The signal is unclear. Ask again."


def generate_tts(text):
    """Generate TTS audio via ElevenLabs. Returns base64 audio string."""
    try:
        resp = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}',
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'audio/mpeg'
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                'voice_settings': {
                    'stability': 0.5,
                    'similarity_boost': 0.75,
                    'style': 0.1
                }
            },
            timeout=30)
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
        else:
            logger.error(
                f"ElevenLabs error: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"ElevenLabs exception: {e}")
        return None


def generate_avatar_video(audio_base64, text=""):
    """Send audio to Ultron GPU server for Wav2Lip lip-sync video generation."""
    try:
        resp = requests.post(f'{AVATAR_SERVER_URL}/generate',
                             json={
                                 'audio_base64': audio_base64,
                                 'text': text
                             },
                             timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('video_base64'), data.get('duration')
        else:
            logger.warning(f"Avatar server error: {resp.status_code}")
            return None, None
    except requests.exceptions.Timeout:
        logger.warning("Avatar server timeout")
        return None, None
    except Exception as e:
        logger.warning(f"Avatar server exception: {e}")
        return None, None


def check_avatar_server():
    """Check if Ultron avatar server is reachable."""
    try:
        resp = requests.get(f'{AVATAR_SERVER_URL}/health', timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ─── ROUTES ────────────────────────────────────────────────────────


@oracle_bp.route('/oracle')
def oracle_page():
    return render_template('oracle.html')


@oracle_bp.route('/api/oracle/chat', methods=['POST'])
@rate_limit
def oracle_chat():
    """Chat-only endpoint (text + audio, no video)."""
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400

    message = data['message'][:500]
    history = data.get('history', [])

    response_text = call_claude(message, history)
    audio_b64 = generate_tts(response_text)

    return jsonify({'response': response_text, 'audio': audio_b64})


@oracle_bp.route('/api/oracle/speak', methods=['POST'])
@rate_limit
def oracle_speak():
    """Full pipeline: Claude response + ElevenLabs audio + Wav2Lip video."""
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400

    message = data['message'][:500]
    history = data.get('history', [])

    # Step 1: Get Claude response
    t0 = time.time()
    response_text = call_claude(message, history)
    t_claude = time.time() - t0

    # Step 2: Generate TTS audio
    t1 = time.time()
    audio_b64 = generate_tts(response_text)
    t_tts = time.time() - t1

    # Step 3: Generate lip-sync video (if audio succeeded and avatar server is up)
    video_b64 = None
    t_avatar = 0
    if audio_b64:
        t2 = time.time()
        video_b64, duration = generate_avatar_video(audio_b64, response_text)
        t_avatar = time.time() - t2

    total = time.time() - t0
    logger.info(
        f"Oracle pipeline: claude={t_claude:.1f}s tts={t_tts:.1f}s avatar={t_avatar:.1f}s total={total:.1f}s"
    )

    result = {
        'response': response_text,
        'audio_base64': audio_b64 or '',
        'pipeline_time': round(total, 1)
    }

    if video_b64:
        result['video_base64'] = video_b64
    else:
        result['fallback'] = True

    return jsonify(result)


@oracle_bp.route('/api/oracle/health')
def oracle_health():
    avatar_connected = check_avatar_server()
    return jsonify({
        'status':
        'ok',
        'llm':
        'claude-sonnet',
        'tts':
        'elevenlabs',
        'voice':
        'Jessica',
        'engine':
        'wav2lip-gpu',
        'avatar_server':
        'connected' if avatar_connected else 'disconnected'
    })
