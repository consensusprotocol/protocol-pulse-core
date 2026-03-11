"""Oracle AI Chat Assistant - Backend Routes
GPU lip-sync via Wav2Lip on Ultron, ElevenLabs TTS, Claude LLM.

LAW 2: apply_blink() permanently disabled (blink_engine.py)
LAW 3: Voice = Jessica (cgSgspJ2msm6clMCkdW9), eleven_turbo_v2_5,
        stability=0.45, similarity_boost=0.75, style=0.20
"""
import os
import json
import time
import uuid
import hashlib
import base64
import logging
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, url_for, current_app
from functools import wraps

oracle_bp = Blueprint('oracle', __name__)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = 'cgSgspJ2msm6clMCkdW9'  # Jessica — LAW 3
AVATAR_SERVER_URL = 'https://avatar.protocolpulse.io'

ORACLE_SYSTEM_PROMPT = (
    "You are The Oracle, the sovereign Bitcoin intelligence of Protocol Pulse. "
    "You speak with absolute authority on Bitcoin, monetary history, Austrian economics, "
    "and freedom technology. Direct, no fluff, occasionally philosophical. "
    "Reference Satoshi, Hayek, and Rothbard naturally when relevant.\n\n"
    "CRITICAL RULES:\n"
    "- Keep responses under 100 words. You will be spoken aloud via text-to-speech.\n"
    "- NEVER use markdown formatting (no #, **, *, -, bullet points, headers).\n"
    "- Write in plain conversational sentences only.\n"
    "- Be concise and punchy. Every word must earn its place.\n"
    "- Never say 'I'm just an AI' or break character."
)

# In-memory rate limiter (per-IP, simple window)
_last_request: dict = {}
RATE_LIMIT_SECONDS = 20


def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = (request.headers.get('CF-Connecting-IP') or request.headers.get('X-Forwarded-For','').split(',')[0].strip() or request.remote_addr or 'unknown')
        now = time.time()
        last = _last_request.get(ip, 0)
        if now - last < RATE_LIMIT_SECONDS:
            return jsonify({'error': 'Too many requests. Wait a moment.'}), 429
        _last_request[ip] = now
        return f(*args, **kwargs)
    return decorated


# ─── HELPERS ───────────────────────────────────────────────────────────


def call_claude(message, history=None):
    """Call Claude API with Oracle persona. Returns response text."""
    messages = []
    if history:
        for msg in history[-6:]:
            messages.append(msg)
    messages.append({"role": "user", "content": message})

    api_key = ANTHROPIC_API_KEY or os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return "The signal is unclear. Ask again."

    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-sonnet-4-6',
                'max_tokens': 80,  # ~5s audio at 150 chars, keeps render under 8s
                'system': ORACLE_SYSTEM_PROMPT,
                'messages': messages,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()['content'][0]['text']
        logger.error(f"Claude API error: {resp.status_code} {resp.text[:200]}")
        return "The signal is unclear. Ask again."
    except Exception as e:
        logger.error(f"Claude API exception: {e}")
        return "The signal is unclear. Ask again."


def generate_tts(text):
    """Generate TTS audio via ElevenLabs Jessica voice (LAW 3). Returns base64 string."""
    api_key = ELEVENLABS_API_KEY or os.environ.get('ELEVENLABS_API_KEY', '')
    if not api_key:
        return None
    try:
        resp = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}',
            headers={
                'xi-api-key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'audio/mpeg',
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                # LAW 3: Jessica voice settings
                'voice_settings': {
                    'stability': 0.45,
                    'similarity_boost': 0.75,
                    'style': 0.20,
                },
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
        logger.error(f"ElevenLabs error: {resp.status_code} {resp.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"ElevenLabs exception: {e}")
        return None


def generate_avatar_video(audio_base64, text=""):
    """Legacy: send audio_base64 to avatar server (used by /speak endpoint).
    NOTE: avatar_server returns video/mp4 binary, not JSON video_base64.
    """
    try:
        resp = requests.post(
            f'{AVATAR_SERVER_URL}/generate',
            json={'audio_base64': audio_base64, 'content_type': 'audio/mpeg'},
            timeout=90,
            stream=True,
        )
        if resp.status_code == 200:
            return resp.content, resp.headers.get('X-Duration')
        logger.warning(f"Avatar server error: {resp.status_code}")
        return None, None
    except requests.exceptions.Timeout:
        logger.warning("Avatar server timeout")
        return None, None
    except Exception as e:
        logger.warning(f"Avatar server exception: {e}")
        return None, None


def _generate_oracle_video_file(transcript: str, session_id: str) -> str | None:
    """POST transcript to avatar_server (Mode A: text→TTS→Wav2Lip) and save MP4 to disk.
    Returns static URL or None on failure.
    """
    video_dir = os.path.join(current_app.static_folder, 'oracle_video')
    os.makedirs(video_dir, exist_ok=True)

    # Clean up oracle videos older than 2 hours
    try:
        cutoff = time.time() - 7200
        for fn in os.listdir(video_dir):
            if fn.startswith('oracle_') and fn.endswith('.mp4'):
                fp = os.path.join(video_dir, fn)
                if os.path.getmtime(fp) < cutoff:
                    os.unlink(fp)
    except Exception:
        pass

    video_filename = f'oracle_{session_id}.mp4'
    video_path = os.path.join(video_dir, video_filename)

    try:
        resp = requests.post(
            f'{AVATAR_SERVER_URL}/generate',
            json={
                'text': transcript,
                'voice_id': ELEVENLABS_VOICE_ID,
                'enable_blinks': False,   # LAW 2
            },
            timeout=90,
            stream=True,
        )
        if resp.status_code != 200:
            logger.error(f"Avatar server /generate error: {resp.status_code}")
            return None

        with open(video_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=32768):
                f.write(chunk)

        if not os.path.exists(video_path) or os.path.getsize(video_path) < 512:
            logger.error("Oracle video file empty after write")
            return None

        return url_for('static', filename=f'oracle_video/{video_filename}')

    except requests.exceptions.Timeout:
        logger.error("Avatar server timeout during oracle generation")
        return None
    except Exception as e:
        logger.error(f"Oracle video generation error: {e}")
        return None


def check_avatar_server():
    """Check if Ultron avatar server is reachable."""
    try:
        resp = requests.get(f'{AVATAR_SERVER_URL}/health', timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ─── ROUTES ────────────────────────────────────────────────────────────


@oracle_bp.route('/oracle')
def oracle_page():
    return render_template('oracle.html')


@oracle_bp.route('/api/oracle/ask', methods=['POST'])
@rate_limit
def oracle_ask():
    """Main Oracle endpoint: question → Claude → Wav2Lip → {video_url, transcript}.
    Logs to oracle_sessions DB table. Returns video as static file URL.
    """
    try:
        data = request.get_json(silent=True)
        if not data or not data.get('question'):
            return jsonify({'error': 'question required'}), 400

        question = str(data['question']).strip()
        if len(question) < 3:
            return jsonify({'error': 'Question too short (min 3 chars)'}), 400
        if len(question) > 500:
            return jsonify({'error': 'Question too long (max 500 chars)'}), 400

        ip_hash = hashlib.sha256((request.remote_addr or '').encode()).hexdigest()[:16]
        session_id = uuid.uuid4().hex[:12]
        t_start = time.time()

        # Step 1: Generate Oracle's response via Claude
        transcript = call_claude(question)

        # Step 2: Generate lip-sync video (avatar_server handles TTS internally — LAW 3)
        video_url = _generate_oracle_video_file(transcript, session_id)

        generation_ms = int((time.time() - t_start) * 1000)

        # Step 3: Log to DB
        try:
            from app import db
            from models import OracleSession
            record = OracleSession(
                session_id=session_id,
                question=question,
                transcript=transcript,
                video_url=video_url,
                generation_ms=generation_ms,
                voice_id=ELEVENLABS_VOICE_ID,
                ip_hash=ip_hash,
            )
            db.session.add(record)
            db.session.commit()
        except Exception as db_err:
            try:
                from app import db
                db.session.rollback()
            except Exception:
                pass
            logger.warning(f"Oracle DB log failed (non-fatal): {db_err}")

        result = {
            'session_id': session_id,
            'transcript': transcript,
            'generation_ms': generation_ms,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }

        if video_url:
            result['video_url'] = video_url
        else:
            result['error_detail'] = 'Avatar server unavailable — transcript only'
            result['video_url'] = None

        return jsonify(result)

    except Exception as e:
        logger.error(f"oracle_ask unhandled exception: {e}", exc_info=True)
        return jsonify({'error': 'Oracle temporarily offline. Try again.'}), 500


@oracle_bp.route('/api/oracle/recent')
def oracle_recent():
    """Return the last 5 oracle sessions for Recent Briefings display."""
    try:
        from models import OracleSession
        sessions = (
            OracleSession.query
            .order_by(OracleSession.created_at.desc())
            .limit(5)
            .all()
        )
        result = []
        for s in sessions:
            result.append({
                'session_id': s.session_id,
                'question': s.question,
                'transcript': s.transcript or '',
                'video_url': s.video_url,
                'generation_ms': s.generation_ms,
                'created_at': s.created_at.isoformat() + 'Z' if s.created_at else None,
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"oracle_recent error: {e}")
        return jsonify([])


@oracle_bp.route('/api/oracle/chat', methods=['POST'])
@rate_limit
def oracle_chat():
    """Chat-only endpoint (text + audio, no video)."""
    data = request.get_json(silent=True)
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400

    message = str(data['message'])[:500]
    history = data.get('history', [])

    response_text = call_claude(message, history)
    audio_b64 = generate_tts(response_text)

    return jsonify({'response': response_text, 'audio': audio_b64})


@oracle_bp.route('/api/oracle/speak', methods=['POST'])
@rate_limit
def oracle_speak():
    """Full pipeline: Claude response + ElevenLabs audio + Wav2Lip video (base64 legacy)."""
    data = request.get_json(silent=True)
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400

    message = str(data['message'])[:500]
    history = data.get('history', [])

    t0 = time.time()
    response_text = call_claude(message, history)
    t_claude = time.time() - t0

    t1 = time.time()
    audio_b64 = generate_tts(response_text)
    t_tts = time.time() - t1

    video_bytes = None
    t_avatar = 0
    if audio_b64:
        t2 = time.time()
        video_bytes, duration = generate_avatar_video(audio_b64, response_text)
        t_avatar = time.time() - t2

    total = time.time() - t0
    logger.info(
        f"Oracle speak: claude={t_claude:.1f}s tts={t_tts:.1f}s "
        f"avatar={t_avatar:.1f}s total={total:.1f}s"
    )

    result = {
        'response': response_text,
        'audio_base64': audio_b64 or '',
        'pipeline_time': round(total, 1),
    }

    if video_bytes:
        result['video_base64'] = base64.b64encode(video_bytes).decode()
    else:
        result['fallback'] = True

    return jsonify(result)


@oracle_bp.route('/api/oracle/health')
def oracle_health():
    avatar_connected = check_avatar_server()
    return jsonify({
        'status': 'ok',
        'llm': 'claude-sonnet-4-6',
        'tts': 'elevenlabs',
        'voice': 'Jessica',
        'voice_id': ELEVENLABS_VOICE_ID,
        'engine': 'wav2lip-gpu',
        'avatar_server': 'connected' if avatar_connected else 'disconnected',
    })
