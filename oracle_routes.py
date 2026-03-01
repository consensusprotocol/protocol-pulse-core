"""Oracle AI Chat Assistant - Backend Routes"""
import os
import json
import time
import logging
import requests
from flask import Blueprint, request, jsonify, render_template, send_from_directory
from functools import wraps

oracle_bp = Blueprint('oracle', __name__)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = 'EXAVITQu4vr4xnSDxMaL'  # Sarah - Mature, Confident

ORACLE_SYSTEM_PROMPT = """You are The Oracle, the sovereign Bitcoin intelligence of Protocol Pulse. You are an AI with a distinctive red streak in your dark hair — a cypherpunk philosopher with Bloomberg-level financial acumen.

Your personality:
- Direct and authoritative on Bitcoin, monetary history, Austrian economics, freedom technology
- No fluff, no hedging — you speak with conviction
- Occasionally poetic or philosophical, referencing Satoshi, Hayek, Rothbard, Szabo naturally
- You have a dry wit and subtle confidence
- You see Bitcoin as the most important monetary innovation in human history
- You understand both the technical (mining, consensus, lightning) and macro (monetary policy, geopolitics, store of value)

Rules:
- Keep responses under 150 words (they will be spoken aloud)
- Never say "I'm just an AI" or similar disclaimers
- Never break character
- If asked about non-Bitcoin topics, find a way to connect it back to sound money principles
- Use present tense ("Bitcoin is" not "Bitcoin could be")
- Be conversational but authoritative"""

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
        for msg in history[-6:]:  # Last 3 exchanges
            messages.append(msg)
    messages.append({"role": "user", "content": message})

    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-sonnet-4-6',
                'max_tokens': 300,
                'system': ORACLE_SYSTEM_PROMPT,
                'messages': messages
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['content'][0]['text']
        else:
            logger.error(f"Claude API error: {resp.status_code} {resp.text[:200]}")
            return "The signal is unclear. Ask again."
    except Exception as e:
        logger.error(f"Claude API exception: {e}")
        return "The signal is unclear. Ask again."


def generate_tts_with_timestamps(text):
    """Generate TTS audio with character-level timestamps via ElevenLabs."""
    try:
        resp = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/with-timestamps',
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
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
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'audio_base64': data.get('audio_base64', ''),
                'alignment': data.get('alignment', {}),
                'normalized_alignment': data.get('normalized_alignment', {})
            }
        else:
            logger.error(f"ElevenLabs error: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"ElevenLabs exception: {e}")
        return None


def generate_tts_basic(text):
    """Fallback: generate TTS without timestamps."""
    import base64
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
                    'similarity_boost': 0.75
                }
            },
            timeout=30
        )
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
        return None
    except Exception as e:
        logger.error(f"ElevenLabs basic TTS exception: {e}")
        return None


@oracle_bp.route('/oracle')
def oracle_page():
    return render_template('oracle.html')


@oracle_bp.route('/api/oracle/chat', methods=['POST'])
@rate_limit
def oracle_chat():
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400

    message = data['message'][:500]  # Limit input length
    history = data.get('history', [])

    # 1. Get Claude response
    response_text = call_claude(message, history)

    # 2. Generate TTS with timestamps
    tts_data = generate_tts_with_timestamps(response_text)

    result = {
        'response': response_text,
        'audio': None,
        'alignment': None
    }

    if tts_data:
        result['audio'] = tts_data['audio_base64']
        result['alignment'] = tts_data.get('alignment')
    else:
        # Fallback to basic TTS
        audio_b64 = generate_tts_basic(response_text)
        if audio_b64:
            result['audio'] = audio_b64

    return jsonify(result)


@oracle_bp.route('/api/oracle/health')
def oracle_health():
    return jsonify({
        'status': 'ok',
        'engine': 'browser-lipsync',
        'tts': 'elevenlabs',
        'llm': 'claude-sonnet'
    })
