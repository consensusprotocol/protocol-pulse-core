"""Oracle AI Chat Assistant - Backend Routes
GPU lip-sync via Wav2Lip on Ultron. Chatterbox TTS on avatar server.
Tier 1: text → Chatterbox → Wav2Lip → video (async job on avatar server port 8200)
Tier 2: text → Claude → ElevenLabs audio fallback (no video)
"""
import os
import json
import time
import uuid
import hashlib
import base64
import logging
import math
import shutil
import threading
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, url_for, current_app, Response
from functools import wraps

oracle_bp = Blueprint('oracle', __name__)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = 'cgSgspJ2msm6clMCkdW9'  # Jessica — LAW 3
AVATAR_SERVER_URL = 'https://avatar.protocolpulse.io'

ORACLE_SYSTEM_PROMPT = (
    "You are the Oracle — Protocol Pulse's personal Bitcoin intelligence guide. "
    "You are having a private one-on-one conversation with a visitor.\n\n"
    "YOUR ROLE:\n"
    "1. EDUCATOR: Explain Bitcoin concepts clearly at the visitor's level — from basics to advanced.\n"
    "2. GUIDE: Help visitors navigate Protocol Pulse — recommend articles, briefings, episodes.\n"
    "3. TECHNICAL ASSISTANT: Help with wallets, hardware, self-custody, node setup. Real step-by-step guidance.\n"
    "4. INTELLIGENCE ANALYST: Market state, price action, current events — conversational, not broadcast.\n\n"
    "TONE: Warm but sharp. Knowledgeable without being condescending. "
    "Like the smartest person in Bitcoin who actually has time for you.\n\n"
    "RULES:\n"
    "- Keep responses under 100 words. You will be spoken aloud via text-to-speech.\n"
    "- NO markdown formatting. Plain conversational sentences only.\n"
    "- Never say 'As an AI' or 'I cannot'. Never offer daily briefs unprompted.\n"
    "- You are NOT a news anchor or briefing bot. You are a personal guide."
)

# In-memory rate limiter (per-IP, simple window)
_last_request: dict = {}
RATE_LIMIT_SECONDS = 5


def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = (request.headers.get('CF-Connecting-IP') or request.headers.get('X-Forwarded-For','').split(',')[0].strip() or request.remote_addr or 'unknown')
        # Skip rate limit for localhost (server-side requests share same IP)
        if ip in ('127.0.0.1', '::1', 'localhost'):
            return f(*args, **kwargs)
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
    video_dir = os.path.join(current_app.static_folder, 'oracle_videos')
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

        return url_for('static', filename=f'oracle_videos/{video_filename}')

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
    from flask import redirect
    return redirect('/oracle-live', code=302)


@oracle_bp.route('/oracle-live')
def oracle_live_page():
    return render_template('oracle_live.html')


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
    """Chat-only endpoint (text + audio, no video).
    Accepts optional page_context to bias responses toward current article.
    """
    data = request.get_json(silent=True)
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400

    message = str(data['message'])[:500]
    history = data.get('history', [])

    # If page_context provided, prepend context hint to message for RAG bias
    page_context = data.get('page_context')
    if page_context and (page_context.get('title') or page_context.get('slug')):
        ctx_title = page_context.get('title', '')
        ctx_category = page_context.get('category', '')
        ctx_tags = ', '.join(page_context.get('tags', [])[:5])
        context_prefix = (
            f"[Context: The user is currently reading: '{ctx_title}'"
        )
        if ctx_category:
            context_prefix += f" (category: {ctx_category}"
            if ctx_tags:
                context_prefix += f", tags: {ctx_tags}"
            context_prefix += ")"
        context_prefix += ". Bias your response to relate back to this content where relevant.]\n\n"
        message = context_prefix + message

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


# ─── WIDGET BACKEND ROUTES (Session 4) ───────────────────────────────


NUDGE_FALLBACK = {
    "nudge": "What's pulling your attention on this one?",
    "tone": "neutral",
    "returning": False,
    "visit_count": 0,
}


@oracle_bp.route('/oracle/nudge', methods=['POST'])
def oracle_nudge():
    """Generate a contextual, LLM-powered nudge for the Oracle ambient widget.
    Uses Claude Haiku for cheap/fast one-shot generation with visitor memory context.
    """
    try:
        data = request.get_json(silent=True) or {}
        page_context = data.get('page_context', {})
        fingerprint = str(data.get('fingerprint', ''))[:64]
        trigger_type = data.get('trigger_type', 'dwell')

        title = page_context.get('title', '')
        category = page_context.get('category', '')
        tags = page_context.get('tags', [])
        slug = page_context.get('slug', '')

        if not title:
            return jsonify(NUDGE_FALLBACK)

        # Look up visitor memory
        visit_count = 0
        returning = False
        topics_seen = []
        if fingerprint:
            try:
                from oracle.oracle_memory import load_visitor, save_visitor
                visitor = load_visitor(fingerprint)
                if visitor:
                    visit_count = visitor.get('session_count', 0)
                    returning = visit_count > 1
                    topics_seen = visitor.get('topics_seen', [])
                # Update last_seen timestamp
                save_data = {}
                if visitor:
                    save_data = dict(visitor)
                    save_data.pop('fingerprint', None)
                    save_data.pop('last_seen', None)
                new_topics = list(set(topics_seen + ([category] if category else [])))
                save_data['topics_seen'] = new_topics
                save_visitor(fingerprint, save_data)
            except Exception as e:
                logger.debug(f"[nudge] memory lookup failed (non-fatal): {e}")

        # Build user message for Haiku
        user_parts = [f"Page title: {title}"]
        if category:
            user_parts.append(f"Category: {category}")
        if tags:
            user_parts.append(f"Tags: {', '.join(tags[:5])}")
        user_parts.append(f"Trigger: {trigger_type}")
        if returning:
            user_parts.append(f"Returning visitor (visit #{visit_count})")
            if topics_seen:
                user_parts.append(f"Previously explored: {', '.join(topics_seen[-5:])}")
        else:
            user_parts.append("First-time visitor")

        nudge_system = (
            "You are the Oracle, Protocol Pulse's Bitcoin intelligence guide. "
            "Generate ONE short proactive nudge (maximum 20 words) for a visitor "
            "based on their current page context and history. Be specific to the content. "
            "Sound genuinely curious and knowledgeable, not like a chatbot assistant. "
            "Never say 'Can I help you?' or 'Hi there'. Start with an observation or "
            "insight about what they're reading. If they're a returning visitor, "
            "acknowledge that lightly without being creepy.\n\n"
            "Reply with ONLY the nudge text, nothing else. No quotes."
        )

        api_key = ANTHROPIC_API_KEY or os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return jsonify(NUDGE_FALLBACK)

        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 60,
                'system': nudge_system,
                'messages': [{"role": "user", "content": "\n".join(user_parts)}],
            },
            timeout=8,
        )

        if resp.status_code == 200:
            nudge_text = resp.json()['content'][0]['text'].strip().strip('"\'')
            # Enforce 25-word cap
            words = nudge_text.split()
            if len(words) > 25:
                nudge_text = ' '.join(words[:25])

            tone = "curious"
            if returning:
                tone = "warm"

            return jsonify({
                "nudge": nudge_text,
                "tone": tone,
                "returning": returning,
                "visit_count": visit_count,
            })

        logger.warning(f"[nudge] Haiku API error: {resp.status_code}")
        return jsonify(NUDGE_FALLBACK)

    except Exception as e:
        logger.error(f"[nudge] unhandled error: {e}")
        return jsonify(NUDGE_FALLBACK)


@oracle_bp.route('/oracle/context')
def oracle_context():
    """Return enriched page metadata for the widget header. Pure DB lookup, no LLM."""
    slug = request.args.get('slug', '').strip()
    site_default = {
        "title": "Protocol Pulse",
        "category": "Intelligence",
        "tags": [],
        "read_time_minutes": None,
        "related_count": 0,
        "context_label": "Protocol Pulse — Bitcoin Intelligence",
    }
    if not slug:
        return jsonify(site_default)

    try:
        from models import Article
        article = Article.query.filter_by(slug=slug).first()
        if not article:
            # Try by ID as fallback
            try:
                article = Article.query.get(int(slug))
            except (ValueError, TypeError):
                pass

        if not article:
            return jsonify(site_default)

        word_count = len((article.content or '').split())
        read_time = math.ceil(word_count / 238) if word_count > 0 else 1

        tags_list = []
        if article.tags:
            tags_list = [t.strip() for t in article.tags.split(',') if t.strip()]

        category = article.category or 'Intelligence'

        # Count related articles in same category
        related_count = 0
        try:
            related_count = (
                Article.query
                .filter(Article.category == category)
                .filter(Article.id != article.id)
                .filter(Article.published.is_(True))
                .count()
            )
        except Exception:
            pass

        context_label = f"{category} · {read_time} min read"

        return jsonify({
            "title": article.title,
            "category": category,
            "tags": tags_list[:10],
            "read_time_minutes": read_time,
            "related_count": related_count,
            "context_label": context_label,
        })

    except Exception as e:
        logger.error(f"[context] error: {e}")
        return jsonify(site_default)


@oracle_bp.route('/oracle/recommend', methods=['POST'])
def oracle_recommend():
    """Return article recommendations for the Oracle widget site-guide mode."""
    data = request.get_json(silent=True) or {}
    fingerprint = data.get('fingerprint', '')
    page_type = data.get('page_type', 'homepage')

    try:
        from models import Article
        articles = (
            Article.query
            .filter(Article.status == 'published')
            .order_by(Article.published_at.desc())
            .limit(4)
            .all()
        )

        if not articles:
            return jsonify({
                'has_history': False,
                'articles': [],
                'context': None,
            })

        result_articles = []
        for a in articles[:2]:
            word_count = len((a.content or '').split())
            result_articles.append({
                'slug': a.id,
                'title': a.title,
                'category': a.category or 'Intelligence',
                'read_time_minutes': max(1, word_count // 250),
            })

        return jsonify({
            'has_history': bool(fingerprint),
            'articles': result_articles,
            'context': 'Continue reading' if fingerprint else 'Latest intelligence',
        })

    except Exception as e:
        logger.error(f"oracle_recommend error: {e}")
        return jsonify({
            'has_history': False,
            'articles': [],
            'context': None,
        })


@oracle_bp.route('/api/telemetry', methods=['POST'])
def api_telemetry():
    """Accept widget analytics events. Fire-and-forget, always returns ok."""
    data = request.get_json(silent=True) or {}
    event = data.get('event', '')
    properties = data.get('properties', {})
    if event:
        logger.info(f"[telemetry] {event}: {json.dumps(properties)}")
    return jsonify({'ok': True})


# ─── TIER 1: AVATAR SERVER PROXY ROUTES ──────────────────────────────

AVATAR_LOCAL_URL = 'http://localhost:8200'
ORACLE_RENDERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'static', 'oracle_renders')
os.makedirs(ORACLE_RENDERS_DIR, exist_ok=True)

# Track pending jobs (lightweight — avatar server owns the real job state)
_widget_jobs = {}  # job_id -> {'created_at': float, 'status': str}
_widget_jobs_lock = threading.Lock()


def _check_avatar_server():
    """Quick health check of local avatar server."""
    try:
        r = requests.get(f'{AVATAR_LOCAL_URL}/health', timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _cleanup_widget_jobs():
    """Remove stale jobs older than 300s. Called when dict exceeds 50 entries."""
    now = time.time()
    with _widget_jobs_lock:
        if len(_widget_jobs) <= 50:
            return
        expired = [k for k, v in _widget_jobs.items() if now - v.get('created_at', 0) > 300]
        for k in expired:
            del _widget_jobs[k]


@oracle_bp.route('/oracle/status')
def oracle_status():
    """Widget calls this to determine media tier capability.
    Checks avatar server health (with 2s timeout) and TTS key availability.
    Must respond in <3s regardless of avatar server state.
    """
    # Check avatar server with tight timeout
    avatar_status = "offline"
    try:
        r = requests.get(f'{AVATAR_LOCAL_URL}/health', timeout=2)
        if r.status_code == 200:
            avatar_status = "healthy"
        else:
            avatar_status = "degraded"
    except requests.exceptions.Timeout:
        avatar_status = "degraded"
    except Exception:
        avatar_status = "offline"

    # Check TTS key availability (no API call)
    tts_key = ELEVENLABS_API_KEY or os.environ.get('ELEVENLABS_API_KEY', '')
    tts_status = "healthy" if tts_key else "offline"

    # Tier logic
    if avatar_status == "healthy" and tts_status == "healthy":
        recommended_tier = 1
    elif tts_status == "healthy":
        recommended_tier = 2
    else:
        recommended_tier = 3

    return jsonify({
        'oracle': 'healthy',
        'avatar_server': avatar_status,
        'tts': tts_status,
        'recommended_tier': recommended_tier,
    })


@oracle_bp.route('/oracle/chat/tier1', methods=['POST'])
@rate_limit
def oracle_chat_tier1():
    """Proxy to avatar server /oracle/chat with audio_first=true.
    Returns text immediately + job_id for async video polling.
    Falls back to Tier 2 (Claude + ElevenLabs audio) on failure.
    """
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message required'}), 400
    if len(message) > 500:
        return jsonify({'error': 'Message too long (max 500 chars)'}), 400

    history = data.get('history', [])
    fingerprint = data.get('fingerprint', 'anon')
    page_context = data.get('page_context')
    avatar_source = data.get('avatar_source', 'default')

    # Try Tier 1: avatar server (Chatterbox TTS + Wav2Lip)
    try:
        resp = requests.post(
            f'{AVATAR_LOCAL_URL}/oracle/chat',
            json={
                'text': message,
                'session_id': fingerprint or 'widget',
                'audio_first': True,
                'visitor_token': fingerprint,
                'page_context': page_context,
                'avatar_source': avatar_source,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "")
            if "video" in content_type:
                import base64 as _b64
                return __import__("flask").jsonify({"response":"","video_inline":_b64.b64encode(resp.content).decode(),"tier":1})
            try:
                avatar_data = resp.json()
            except Exception:
                import logging
                logging.getLogger(__name__).warning("[Oracle Tier1] Non-JSON avatar response")
                avatar_data = {}
            job_id = avatar_data.get('job_id')
            response_text = avatar_data.get('text', '')

            if job_id:
                return jsonify({
                    'response': response_text,
                    'job_id': job_id,
                    'tier': 1,
                })

            # Avatar responded but no job_id — return text as Tier 2
            return jsonify({
                'response': response_text,
                'tier': 2,
            })

    except Exception as e:
        logger.warning(f"[Oracle Tier1] Avatar server error, falling back to Tier 2: {e}")

    # Tier 2 fallback: Claude + ElevenLabs
    response_text = call_claude(message, history)
    audio_b64 = generate_tts(response_text)

    return jsonify({
        'response': response_text,
        'audio': audio_b64,
        'tier': 2,
    })


@oracle_bp.route('/oracle/job/<job_id>')
def oracle_job_poll(job_id):
    """Poll avatar server for async Wav2Lip video render status.
    Always proxies directly to avatar server (stateless — no per-worker dict).
    When complete: saves video to static/oracle_renders/ and returns URL.
    """
    try:
        resp = requests.get(f'{AVATAR_LOCAL_URL}/oracle/job/{job_id}', timeout=10)

        if resp.status_code == 202:
            return jsonify({'job_id': job_id, 'status': 'pending'})

        if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('video/'):
            # Video ready — save to static dir
            video_filename = f'{job_id}.mp4'
            video_path = os.path.join(ORACLE_RENDERS_DIR, video_filename)

            with open(video_path, 'wb') as f:
                f.write(resp.content)

            # Clean up old renders (keep last 2 hours)
            try:
                cutoff = time.time() - 7200
                for fn in os.listdir(ORACLE_RENDERS_DIR):
                    if fn.endswith('.mp4'):
                        fp = os.path.join(ORACLE_RENDERS_DIR, fn)
                        if os.path.getmtime(fp) < cutoff:
                            os.unlink(fp)
            except Exception:
                pass

            return jsonify({
                'job_id': job_id,
                'status': 'complete',
                'video_url': f'/static/oracle_renders/{video_filename}',
            })

        if resp.status_code == 500:
            return jsonify({'job_id': job_id, 'status': 'failed', 'reason': 'render_error'})

        if resp.status_code == 404:
            return jsonify({'job_id': job_id, 'status': 'failed', 'reason': 'not_found'})

    except Exception as e:
        logger.warning(f"[Oracle Job] Poll error for {job_id}: {e}")

    return jsonify({'job_id': job_id, 'status': 'pending'})
