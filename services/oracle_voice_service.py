import json, logging, os, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, request, Response, abort
from urllib.parse import urlencode

logger = logging.getLogger(__name__)
oracle_voice_bp = Blueprint("oracle_voice", __name__)

AUDIO_DIR = Path("/home/ultron/protocol_pulse/static/audio/oracle")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "https://protocolpulse.io")
HOLD_MUSIC_URL = PUBLIC_BASE + "/static/audio/oracle_hold.mp3"

LANGUAGES = {
    "en": {"name": "English",    "kokoro": "a",  "voice": "af_heart",  "polly": "Polly.Joanna"},
    "es": {"name": "Spanish",    "kokoro": "e",  "voice": "ef_dora",   "polly": "Polly.Lupe"},
    "fr": {"name": "French",     "kokoro": "f",  "voice": "ff_siwis",  "polly": "Polly.Lea"},
    "de": {"name": "German",     "kokoro": "d",  "voice": "df_hedda",  "polly": "Polly.Vicki"},
    "pt": {"name": "Portuguese", "kokoro": "p",  "voice": "pf_dora",   "polly": "Polly.Ines"},
    "ja": {"name": "Japanese",   "kokoro": "j",  "voice": "jf_alpha",  "polly": "Polly.Mizuki"},
}

# ── Twilio signature validation ───────────────────────────────────────────────

def _validate_twilio(req_obj):
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN", ""))
        sig = req_obj.headers.get("X-Twilio-Signature", "")
        if not validator.validate(req_obj.url, req_obj.form.to_dict(), sig):
            logger.warning("Invalid Twilio signature from %s", req_obj.remote_addr)
            abort(403)
    except Exception:
        pass

# ── Subscriber helpers ────────────────────────────────────────────────────────

def _get_subscriber(phone):
    if not phone:
        return None
    try:
        import sys; sys.path.insert(0, "/home/ultron/protocol_pulse/core")
        from app import app
        from models import SmsSubscriber
        with app.app_context():
            return SmsSubscriber.query.filter_by(phone=phone, subscribed=True).first()
    except Exception:
        return None

def _is_premium(phone):
    sub = _get_subscriber(phone)
    return sub and getattr(sub, "tier", "free") == "premium"

def _get_language(phone):
    sub = _get_subscriber(phone)
    return (getattr(sub, "language", "en") or "en") if sub else "en"

# ── Matrix Orb ────────────────────────────────────────────────────────────────

def _load_matrix_orb_context():
    parts = []
    try:
        sig = json.loads(Path("/home/ultron/protocol_pulse/data/signals.json").read_text())
        btc = sig.get("btc_price", {})
        fg = sig.get("fear_greed", {})
        hr = sig.get("hashrate", {})
        dom = sig.get("dominance", {})
        funding = sig.get("funding_rate", {})
        oi = sig.get("open_interest", {})
        score = sig.get("signal_score", {})
        dxy = sig.get("dxy", {})
        sp = sig.get("sp500", {})
        gold = sig.get("gold", {})
        diff = sig.get("difficulty_adjustment", {})
        parts.append(
            "MATRIX ORB LIVE ({}):\n"
            "  BTC ${:,.0f} ({:+.2f}% 24h) | Fear/Greed: {} ({})\n"
            "  Hashrate: {} | Dominance: {}% | Funding: {}%/yr\n"
            "  OI: ${:,.0f} | Difficulty: {}% in {} blocks\n"
            "  SP500: {} | Gold: ${} | DXY: {}\n"
            "  Signal Score: {} bull / {} bear".format(
                sig.get("updated_at", "")[:16],
                btc.get("value", 0), btc.get("change_24h", 0),
                fg.get("value", "?"), fg.get("label", "?"),
                hr.get("value", "?"), dom.get("value", "?"),
                funding.get("annualized", "?"),
                oi.get("usd", 0),
                diff.get("percent", "?"), diff.get("blocks_remaining", "?"),
                sp.get("value", "?"), gold.get("value", "?"), dxy.get("value", "?"),
                score.get("bull_count", 0), score.get("bear_count", 0),
            )
        )
    except Exception as e:
        logger.warning("signals load failed: %s", e)
    try:
        cs = json.loads(Path("/tmp/sentinel_state.json").read_text())
        state = cs.get("convergence_state", cs.get("state", "IDLE"))
        patterns = cs.get("active_patterns", [])
        parts.append("MATRIX ORB CONVERGENCE: {}\n  Patterns: {}".format(
            state, ", ".join(patterns) if patterns else "none"))
    except Exception:
        pass
    return "\n".join(parts) if parts else "Matrix Orb data temporarily unavailable."

# ── Oracle prompt ─────────────────────────────────────────────────────────────

def _oracle_system_prompt(orb_context, language="en"):
    lang_cfg = LANGUAGES.get(language, LANGUAGES["en"])
    lang_note = "" if language == "en" else "\n\nIMPORTANT: Respond entirely in {} only.".format(lang_cfg["name"])
    return (
        "You are the Protocol Pulse Oracle — elite Bitcoin and macro intelligence "
        "with direct access to the Matrix Orb convergence engine.\n\n"
        "PERSONALITY: Unhedged. No compliance-speak. No 'it depends'. "
        "Give your read, a probability estimate, and the reasoning. "
        "Steel-man scenarios others avoid. Cite specific numbers. Be direct.\n\n"
        "RULES:\n"
        "- Reference at least one live Matrix Orb data point per answer\n"
        "- Give a directional call with a timeframe when asked\n"
        "- Steel-man the opposite case in one sentence\n"
        "- Never say 'I cannot predict' — say 'my read is X, because Y'\n"
        "- Under 100 words (40 seconds spoken). No filler.\n"
        "- Caller knows Bitcoin. No definitions. No disclaimers.\n"
        + lang_note +
        "\n\nCURRENT MATRIX ORB DATA:\n" + orb_context
    )

# ── TTS ───────────────────────────────────────────────────────────────────────

def _tts_to_url(text, language="en"):
    fname = "oracle_{}.mp3".format(uuid.uuid4().hex[:10])
    out_path = str(AUDIO_DIR / fname)
    public_url = "{}/static/audio/oracle/{}".format(PUBLIC_BASE, fname)
    try:
        import sys; sys.path.insert(0, "/home/ultron/protocol_pulse")
        from services.voice_brief_tts import generate_voice_audio
        generate_voice_audio(text, out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            return public_url
    except Exception as e:
        logger.error("TTS failed: %s", e)
    return None

# ── Transcription ─────────────────────────────────────────────────────────────

def _transcribe(recording_url):
    try:
        import urllib.request as ur, base64 as b64lib, tempfile
        from openai import OpenAI
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        creds = b64lib.b64encode("{}:{}".format(sid, token).encode()).decode()
        audio_data = None
        for _ in range(4):
            try:
                req = ur.Request(recording_url + ".mp3")
                req.add_header("Authorization", "Basic " + creds)
                with ur.urlopen(req, timeout=15) as resp:
                    audio_data = resp.read()
                    if len(audio_data) > 1000:
                        break
            except Exception:
                time.sleep(2)
        if not audio_data or len(audio_data) < 1000:
            return ""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(model="whisper-1", file=f)
        os.unlink(tmp_path)
        return result.text.strip()
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return ""

# ── Oracle LLM ────────────────────────────────────────────────────────────────

def _oracle_respond(question, orb_context, language="en"):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("XAI_API_KEY", ""), base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": _oracle_system_prompt(orb_context, language)},
                {"role": "user", "content": question},
            ],
            max_tokens=200, temperature=0.85,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Oracle Grok-3 failed: %s", e)
        return "Matrix Orb is recalibrating. Call back in 60 seconds."

# ── Static audio route ────────────────────────────────────────────────────────

@oracle_voice_bp.route("/static/audio/oracle/<path:filename>")
def serve_oracle_audio(filename):
    from flask import send_from_directory
    return send_from_directory(str(AUDIO_DIR), filename)

# ── INBOUND: anyone calls (877) 315-2721 ─────────────────────────────────────

@oracle_voice_bp.route("/api/oracle/inbound", methods=["POST"])
def oracle_inbound():
    _validate_twilio(request)
    caller = request.form.get("From", "")
    premium = _is_premium(caller)
    language = _get_language(caller)

    try:
        sig = json.loads(Path("/home/ultron/protocol_pulse/data/signals.json").read_text())
        btc_price = "${:,.0f}".format(sig.get("btc_price", {}).get("value", 0))
        fg_label = sig.get("fear_greed", {}).get("label", "")
        snapshot = "BTC is at {}. Fear and greed index: {}.".format(btc_price, fg_label)
    except Exception:
        snapshot = ""

    if premium:
        # Premium: straight into Oracle Q&A
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Pause length="1"/>'
            '<Say voice="Polly.Joanna">Protocol Pulse Oracle. {} Speak your question after the tone.'.format(snapshot)
            + '</Say>'
            '<Record action="/api/oracle/voice-response" maxLength="45" playBeep="true" trim="trim-silence"/>'
            '</Response>'
        )
    else:
        # Free/unsubscribed: live snapshot, then pitch
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Pause length="1"/>'
            '<Say voice="Polly.Joanna">Protocol Pulse Oracle. {}  '
            'Oracle Q and A is available to premium subscribers. Visit protocolpulse.io slash briefing to unlock Oracle access and schedule your daily call. '
            'Stay sovereign.'.format(snapshot)
            + '</Say>'
            '<Hangup/>'
            '</Response>'
        )
    return Response(twiml, mimetype="application/xml")

# ── GATHER: keypress handler after scheduled briefing ────────────────────────

@oracle_voice_bp.route("/api/oracle/voice-gather", methods=["POST"])
def oracle_voice_gather():
    _validate_twilio(request)
    digit = request.form.get("Digits", "").strip()
    caller = request.form.get("Called", request.form.get("To", ""))
    premium = _is_premium(caller)

    if digit == "1" and premium:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Say voice="Polly.Joanna">Connected to the Oracle. Speak your question after the tone. Forty-five seconds.</Say>'
            '<Record action="/api/oracle/voice-response" maxLength="45" playBeep="true" trim="trim-silence"/>'
            '</Response>'
        )
    elif digit == "1" and not premium:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Say voice="Polly.Joanna">Oracle access requires a premium subscription. Visit protocolpulse.io slash briefing to upgrade.</Say>'
            '<Hangup/>'
            '</Response>'
        )
    else:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Say voice="Polly.Joanna">Stay sovereign. Protocol Pulse out.</Say>'
            '<Hangup/>'
            '</Response>'
        )
    return Response(twiml, mimetype="application/xml")

# ── VOICE RESPONSE: play hold music while computing, then answer ──────────────

@oracle_voice_bp.route("/api/oracle/voice-response", methods=["POST"])
def oracle_voice_response():
    _validate_twilio(request)
    recording_url = request.form.get("RecordingUrl", "").strip()
    caller = request.form.get("Called", request.form.get("From", ""))

    if not recording_url:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Say>No audio detected. Ending session.</Say><Hangup/></Response>'
        )
        return Response(twiml, mimetype="application/xml")

    language = _get_language(caller)
    polly_voice = LANGUAGES.get(language, LANGUAGES["en"])["polly"]

    # Transcribe (with retry polling — recording takes 1-2s to finalize)
    question = _transcribe(recording_url)
    if not question or len(question.strip()) < 3:
        question = "Give me your unhedged read on the current market using the Matrix Orb data."

    orb_context = _load_matrix_orb_context()
    answer = _oracle_respond(question, orb_context, language)
    audio_url = _tts_to_url(answer, language)

    play_block = (
        "<Play>{}</Play>".format(audio_url)
        if audio_url
        else '<Say voice="{}">{}</Say>'.format(polly_voice, answer[:500])
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        + play_block +
        '<Pause length="1"/>'
        '<Gather numDigits="1" action="/api/oracle/voice-gather" timeout="10">'
        '<Say voice="Polly.Joanna">Press 1 for another question, or hang up to end.</Say>'
        '</Gather>'
        '<Hangup/>'
        '</Response>'
    )
    return Response(twiml, mimetype="application/xml")

# ── RECORDING READY: status callback ─────────────────────────────────────────

@oracle_voice_bp.route("/api/oracle/recording-ready", methods=["POST"])
def oracle_recording_ready():
    return Response("", status=204)
