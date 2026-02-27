"""Oracle API Routes v2 — Secure proxy for Anthropic + ElevenLabs + Avatar Pipeline"""
import os, json, logging, requests, hashlib, time, re, uuid, threading
from flask import Blueprint, request, jsonify, Response, render_template, send_from_directory

oracle_bp = Blueprint("oracle", __name__)
logger = logging.getLogger("oracle")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
# Jessica — young, bright, conversational
VOICE_ID = os.environ.get("ORACLE_VOICE_ID", "cgSgspJ2msm6clMCkdW9")
# Ultron avatar server (LAN or tunnel)
AVATAR_URL = os.environ.get("AVATAR_SERVER_URL", "https://coercionary-unmaturative-lakiesha.ngrok-free.dev")

STATIC_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "static", "oracle_audio")
STATIC_VIDEO_DIR = os.path.join(os.path.dirname(__file__), "static", "oracle_video")
os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)
os.makedirs(STATIC_VIDEO_DIR, exist_ok=True)

# Emotion-mapped voice settings for ElevenLabs
EMOTION_VOICE = {
    "neutral":   {"stability": 0.60, "similarity_boost": 0.80, "style": 0.40},
    "curious":   {"stability": 0.55, "similarity_boost": 0.80, "style": 0.50},
    "skeptical":  {"stability": 0.70, "similarity_boost": 0.80, "style": 0.30},
    "warning":   {"stability": 0.75, "similarity_boost": 0.80, "style": 0.25},
    "confident": {"stability": 0.50, "similarity_boost": 0.80, "style": 0.55},
}

# Content guardrails patterns
PRICE_PREDICTION = re.compile(r'price\s+will\s+(reach|hit|go\s+to)\s+\$', re.I)
FINANCIAL_ADVICE = re.compile(r'you\s+should\s+(buy|sell|invest|hodl)', re.I)
CERTAINTY_CLAIMS = re.compile(r'\b(guaranteed|100%|can\'t lose|sure thing|certain to)\b', re.I)
GUARDRAIL_SUFFIX = "\n\nNot financial advice. I analyze signals, I don't predict prices."

# Video generation status tracking (in-memory, production would use Redis)
_video_status = {}  # hash -> {"status": "processing"|"ready"|"failed", "video_url": "..."}


def _parse_emotion(text):
    """Extract EMOTION: tag from Claude response."""
    match = re.search(r'EMOTION:\s*(neutral|curious|skeptical|warning|confident)', text, re.I)
    if match:
        return match.group(1).lower()
    return "neutral"


def _clean_reply(text):
    """Remove EMOTION and RECOMMEND tags from reply text."""
    text = re.sub(r'\n?EMOTION:\s*\w+', '', text).strip()
    return text


def _apply_guardrails(text):
    """Scan reply for content that needs disclaimers."""
    needs_disclaimer = False
    if PRICE_PREDICTION.search(text):
        needs_disclaimer = True
    if FINANCIAL_ADVICE.search(text):
        needs_disclaimer = True
    if CERTAINTY_CLAIMS.search(text):
        needs_disclaimer = True
    if needs_disclaimer:
        text = text.rstrip() + GUARDRAIL_SUFFIX
    return text


def _check_input(text):
    """Check user input for abuse."""
    if not text or len(text) > 1000:
        return False, "Keep it focused."
    if re.search(r'(.)\1{10,}', text):  # Spam pattern
        return False, "Keep it focused."
    return True, ""


def _generate_tts(text, emotion="neutral"):
    """Generate TTS audio via ElevenLabs. Returns (audio_bytes, content_type) or (None, None)."""
    if not ELEVEN_KEY:
        return None, None
    voice_settings = EMOTION_VOICE.get(emotion, EMOTION_VOICE["neutral"])
    try:
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream",
            headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": voice_settings,
            },
            timeout=25,
        )
        if resp.status_code < 400:
            return resp.content, "audio/mpeg"
    except Exception as e:
        logger.error(f"TTS error: {e}")
    return None, None


def _bg_generate_video(audio_hash, audio_bytes, emotion):
    """Background thread: send audio to Ultron avatar server, save video."""
    try:
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode()
        resp = requests.post(
            f"{AVATAR_URL}/api/avatar/generate",
            json={"audio_b64": audio_b64, "format": "mp3", "emotion": emotion},
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=300,
        )
        if resp.status_code == 200 and len(resp.content) > 1000:
            # Server returns raw video file
            video_path = os.path.join(STATIC_VIDEO_DIR, f"{audio_hash}.mp4")
            with open(video_path, "wb") as f:
                f.write(resp.content)
            _video_status[audio_hash] = {
                "status": "ready",
                "video_url": f"/static/oracle_video/{audio_hash}.mp4",
            }
            logger.info(f"Avatar video ready: {audio_hash}")
            return
        _video_status[audio_hash] = {"status": "failed"}
        logger.warning(f"Avatar generation failed: {resp.status_code} ({len(resp.content)} bytes)")
    except Exception as e:
        _video_status[audio_hash] = {"status": "failed"}
        logger.error(f"Avatar bg error: {e}")


def _log_session(session_id, question, reply, emotion, audio_duration_ms, latency_ms):
    """Log oracle session to database."""
    try:
        from app import db
        db.session.execute(db.text("""
            INSERT INTO oracle_sessions (session_id, question, reply, emotion, audio_duration_ms, latency_ms, created_at)
            VALUES (:sid, :q, :r, :e, :ad, :lat, NOW())
        """), {"sid": session_id, "q": question[:500], "r": reply[:1000], "e": emotion, "ad": audio_duration_ms, "lat": latency_ms})
        db.session.commit()
    except Exception as e:
        logger.debug(f"Session log error (non-critical): {e}")


# --- Routes ---

@oracle_bp.route("/oracle")
def oracle_page():
    return render_template("oracle_v2.html")

@oracle_bp.route("/onboarding")
def onboarding_page():
    intent = request.args.get("intent", "")
    return render_template("oracle_onboarding.html", preseed_intent=intent)


@oracle_bp.route("/api/oracle/speak", methods=["POST"])
def oracle_speak():
    """Two-phase response: immediate text+audio, background video generation."""
    t0 = time.time()
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", str(uuid.uuid4())[:12])
    message = (data.get("message") or "").strip()
    messages = data.get("messages", [])[-14:]
    system = data.get("system", "")

    # Input validation
    valid, err = _check_input(message)
    if not valid:
        return jsonify({"reply": err, "emotion": "skeptical", "audio_url": None, "video_status": "skipped", "video_poll_url": None})

    if not messages:
        messages = [{"role": "user", "content": message}]

    if not ANTHROPIC_KEY:
        return jsonify({"error": "key missing"}), 500

    # Step 1: Call Claude
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 400, "system": system, "messages": messages},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.error(f"Anthropic: {resp.status_code} {resp.text[:300]}")
            return jsonify({"error": "ai_error"}), 502
        raw_text = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
    except requests.Timeout:
        return jsonify({"error": "timeout"}), 504
    except Exception as e:
        logger.error(f"Oracle speak: {e}")
        return jsonify({"error": str(e)}), 500

    # Step 2: Parse emotion and clean reply
    emotion = _parse_emotion(raw_text)
    reply = _clean_reply(raw_text)
    reply = _apply_guardrails(reply)

    # Step 3: Generate TTS with emotion-mapped voice
    # Strip recommendation tags for TTS
    tts_text = re.sub(r'\[RECOMMEND:\w+\]', '', reply).strip()
    audio_bytes, _ = _generate_tts(tts_text, emotion)

    audio_url = None
    video_poll_url = None
    audio_hash = None

    if audio_bytes:
        audio_hash = hashlib.md5(audio_bytes[:2048]).hexdigest()[:16]
        audio_path = os.path.join(STATIC_AUDIO_DIR, f"{audio_hash}.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        audio_url = f"/static/oracle_audio/{audio_hash}.mp3"

        # Step 4: Start background video generation
        _video_status[audio_hash] = {"status": "processing"}
        video_poll_url = f"/api/oracle/video-status/{audio_hash}"
        thread = threading.Thread(target=_bg_generate_video, args=(audio_hash, audio_bytes, emotion), daemon=True)
        thread.start()

    latency_ms = int((time.time() - t0) * 1000)

    # Log session
    _log_session(session_id, message, reply, emotion, len(audio_bytes) if audio_bytes else 0, latency_ms)

    return jsonify({
        "reply": reply,
        "emotion": emotion,
        "audio_url": audio_url,
        "video_status": "processing" if audio_hash else "skipped",
        "video_poll_url": video_poll_url,
        "latency_ms": latency_ms,
    })


@oracle_bp.route("/api/oracle/video-status/<audio_hash>")
def video_status(audio_hash):
    """Poll endpoint for video generation status."""
    status = _video_status.get(audio_hash, {"status": "unknown"})
    return jsonify(status)


@oracle_bp.route("/api/oracle/chat", methods=["POST"])
def oracle_chat():
    """Legacy chat endpoint (kept for backward compatibility)."""
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])[-14:]
    system = data.get("system", "")
    if not messages:
        return jsonify({"error": "no messages"}), 400
    if not ANTHROPIC_KEY:
        return jsonify({"error": "key missing"}), 500
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 300, "system": system, "messages": messages},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.error(f"Anthropic: {resp.status_code} {resp.text[:300]}")
            return jsonify({"error": "ai_error"}), 502
        text = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        return jsonify({"text": text})
    except requests.Timeout:
        return jsonify({"error": "timeout"}), 504
    except Exception as e:
        logger.error(f"Oracle chat: {e}")
        return jsonify({"error": str(e)}), 500


@oracle_bp.route("/api/oracle/tts", methods=["POST"])
def oracle_tts():
    """TTS endpoint — uses emotion-mapped voice settings."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    emotion = data.get("emotion", "neutral")
    if not text:
        return jsonify({"error": "empty"}), 400
    audio_bytes, content_type = _generate_tts(text, emotion)
    if audio_bytes:
        return Response(audio_bytes, status=200, content_type=content_type)
    return jsonify({"error": "tts_failed"}), 502


@oracle_bp.route("/api/oracle/track", methods=["POST"])
def oracle_track():
    data = request.get_json(silent=True) or {}
    logger.info(f"ORACLE TRACK: {json.dumps(data)}")
    try:
        from services.analytics_service import emit_event
        emit_event(event_type="oracle_conversion", source="oracle", lane="conversion",
                   severity="info", title=f"Oracle {data.get('action','view')}: {data.get('intent','?')}",
                   detail=json.dumps(data), payload=data)
    except Exception:
        pass
    return jsonify({"ok": True})


# Proxy idle loops from Ultron avatar server
@oracle_bp.route("/api/avatar/idle")
def avatar_idle():
    variant = request.args.get("variant", "")
    try:
        url = f"{AVATAR_URL}/api/avatar/idle"
        if variant:
            url += f"?variant={variant}"
        resp = requests.get(url, timeout=10, headers={"ngrok-skip-browser-warning": "true"})
        if resp.status_code == 200:
            return Response(resp.content, status=200, content_type="video/mp4")
    except Exception as e:
        logger.warning(f"Avatar idle proxy error: {e}")
    return jsonify({"error": "idle not available"}), 503
