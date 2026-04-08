import json, logging, os, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, request, Response, abort

logger = logging.getLogger(__name__)
oracle_voice_bp = Blueprint("oracle_voice", __name__)

# Persistent audio dir served by Flask static
AUDIO_DIR = Path("/home/ultron/protocol_pulse/static/audio/oracle")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "https://protocolpulse.io")

# Supported languages with verified Kokoro voices + Polly fallback
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
            logger.warning("Twilio signature validation FAILED from %s", req_obj.remote_addr)
            abort(403)
    except ImportError:
        pass  # twilio package handles this; if not installed just pass
    except Exception as e:
        logger.warning("Signature validation error: %s", e)


# ── Matrix Orb context ────────────────────────────────────────────────────────

def _load_matrix_orb_context():
    parts = []
    try:
        sig_path = Path("/home/ultron/protocol_pulse/data/signals.json")
        if sig_path.exists():
            sig = json.loads(sig_path.read_text())
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
        logger.warning("signals.json load failed: %s", e)
    try:
        cs_path = Path("/tmp/sentinel_state.json")
        if cs_path.exists():
            cs = json.loads(cs_path.read_text())
            state = cs.get("convergence_state", cs.get("state", "IDLE"))
            patterns = cs.get("active_patterns", [])
            pcaf = cs.get("pcaf_score", None)
            parts.append(
                "MATRIX ORB CONVERGENCE: {}\n  Patterns: {}\n  PCAF: {}".format(
                    state,
                    ", ".join(patterns) if patterns else "none",
                    "{:.3f}".format(pcaf) if pcaf is not None else "n/a"
                )
            )
    except Exception as e:
        logger.debug("sentinel_state load failed: %s", e)
    return "\n".join(parts) if parts else "Matrix Orb data temporarily unavailable."


# ── System prompt ─────────────────────────────────────────────────────────────

def _oracle_system_prompt(orb_context, language="en"):
    lang_cfg = LANGUAGES.get(language, LANGUAGES["en"])
    lang_note = "" if language == "en" else "\n\nIMPORTANT: Respond entirely in {} only.".format(lang_cfg["name"])
    return (
        "You are the Protocol Pulse Oracle — an elite Bitcoin and macro intelligence system "
        "with direct access to the Matrix Orb convergence engine.\n\n"
        "PERSONALITY: Unhedged. No compliance-speak. No 'it depends'. Give your read, "
        "a probability estimate, and the reasoning. Steel-man scenarios others avoid. "
        "Cite specific numbers from the Matrix Orb. Be direct to the point of blunt.\n\n"
        "RULES:\n"
        "- Reference at least one live Matrix Orb data point per answer\n"
        "- Give a directional call — up/down/sideways with a timeframe\n"
        "- Steel-man the opposite case in one sentence\n"
        "- Never say 'I cannot predict' — say 'my read is X, because Y'\n"
        "- Under 110 words (45 seconds spoken). No filler.\n"
        "- Caller knows Bitcoin. No definitions. No disclaimers.\n"
        + lang_note +
        "\n\nCURRENT MATRIX ORB DATA:\n" + orb_context
    )


# ── TTS with language + Polly fallback ───────────────────────────────────────

def _tts_to_url(text, language="en"):
    lang_cfg = LANGUAGES.get(language, LANGUAGES["en"])
    fname = "oracle_{}.mp3".format(uuid.uuid4().hex[:10])
    out_path = str(AUDIO_DIR / fname)
    public_url = "{}/static/audio/oracle/{}".format(PUBLIC_BASE, fname)
    try:
        import sys; sys.path.insert(0, "/home/ultron/protocol_pulse")
        from services.voice_brief_tts import generate_voice_audio
        generate_voice_audio(text, out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            logger.info("Oracle TTS OK: %s (%d bytes)", fname, os.path.getsize(out_path))
            return public_url
        logger.warning("TTS output too small, falling back to Polly")
    except Exception as e:
        logger.error("TTS failed, will use Polly fallback: %s", e)
    return None  # Caller uses <Say> Polly fallback


# ── Transcription ─────────────────────────────────────────────────────────────

def _transcribe_audio(recording_url):
    try:
        import urllib.request as ur, base64 as b64lib, tempfile
        from openai import OpenAI
        # Twilio needs 2-3s to finalize recording - poll up to 8s
        mp3_url = recording_url + ".mp3"
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        creds = b64lib.b64encode("{}:{}".format(sid, token).encode()).decode()
        audio_data = None
        for attempt in range(4):
            try:
                req = ur.Request(mp3_url)
                req.add_header("Authorization", "Basic " + creds)
                with ur.urlopen(req, timeout=15) as resp:
                    audio_data = resp.read()
                    if len(audio_data) > 1000:
                        break
            except Exception:
                time.sleep(2)
        if not audio_data or len(audio_data) < 1000:
            logger.warning("Could not fetch recording after 4 attempts")
            return ""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(model="whisper-1", file=f)
        os.unlink(tmp_path)
        text = result.text.strip()
        logger.info("Transcribed (%d chars): %s", len(text), text[:60])
        return text
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
            max_tokens=220, temperature=0.85,
        )
        answer = resp.choices[0].message.content.strip()
        logger.info("Oracle answer (%d chars)", len(answer))
        return answer
    except Exception as e:
        logger.error("Oracle Grok-3 failed: %s", e)
        return "Matrix Orb is recalibrating. Call back in 60 seconds."


# ── Caller language lookup ────────────────────────────────────────────────────

def _get_caller_language(phone):
    if not phone:
        return "en"
    try:
        import sys; sys.path.insert(0, "/home/ultron/protocol_pulse/core")
        from app import app
        from models import SmsSubscriber
        with app.app_context():
            sub = SmsSubscriber.query.filter_by(phone=phone).first()
            if sub:
                return getattr(sub, "language", "en") or "en"
    except Exception:
        pass
    return "en"


# ── Static audio route ────────────────────────────────────────────────────────

@oracle_voice_bp.route("/static/audio/oracle/<path:filename>")
def serve_oracle_audio(filename):
    from flask import send_from_directory
    return send_from_directory(str(AUDIO_DIR), filename)


# ── Twilio webhook routes ─────────────────────────────────────────────────────

@oracle_voice_bp.route("/api/oracle/voice-gather", methods=["POST"])
def oracle_voice_gather():
    _validate_twilio(request)
    digit = request.form.get("Digits", "").strip()
    if digit == "1":
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Say voice="Polly.Joanna" language="en-US">Connected to the Oracle. Speak your question after the tone. Thirty seconds.</Say>'
            '<Record action="/api/oracle/voice-response" maxLength="30" playBeep="true" trim="trim-silence"/>'
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


@oracle_voice_bp.route("/api/oracle/voice-response", methods=["POST"])
def oracle_voice_response():
    _validate_twilio(request)
    recording_url = request.form.get("RecordingUrl", "").strip()
    caller = request.form.get("Called", request.form.get("To", ""))

    if not recording_url:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Say>No audio detected. Ending session.</Say><Hangup/></Response>'
        )
        return Response(twiml, mimetype="application/xml")

    language = _get_caller_language(caller)
    polly_voice = LANGUAGES.get(language, LANGUAGES["en"])["polly"]

    # Transcribe (with polling retry built in)
    question = _transcribe_audio(recording_url)
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
        '<Say voice="Polly.Joanna">Press 1 to ask another question, or hang up to end.</Say>'
        '</Gather>'
        '<Hangup/>'
        '</Response>'
    )
    return Response(twiml, mimetype="application/xml")


@oracle_voice_bp.route("/api/oracle/recording-ready", methods=["POST"])
def oracle_recording_ready():
    return Response("", status=204)


# ── Inbound call entry point ──────────────────────────────────────────────────
# Fires when someone calls (877) 315-2721 directly.
# No subscription required — open Oracle access for all callers.

@oracle_voice_bp.route("/api/oracle/inbound", methods=["POST"])
def oracle_inbound():
    _validate_twilio(request)
    caller = request.form.get("From", "")
    language = _get_caller_language(caller)  # pulls pref if they're a subscriber
    polly_voice = LANGUAGES.get(language, LANGUAGES["en"])["polly"]

    # Load live Matrix Orb snapshot for the greeting
    orb_context = _load_matrix_orb_context()
    try:
        import json as _json
        sig = _json.loads(open("/home/ultron/protocol_pulse/data/signals.json").read())
        btc_price = "${:,.0f}".format(sig.get("btc_price", {}).get("value", 0))
        fg_label = sig.get("fear_greed", {}).get("label", "")
        greeting_data = "BTC is at {} — fear and greed index is {}.".format(btc_price, fg_label)
    except Exception:
        greeting_data = ""

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        '<Pause length="1"/>'
        '<Say voice="{}" language="en-US">Protocol Pulse Oracle. {}Speak your question after the tone.</Say>'.format(polly_voice, greeting_data + " " if greeting_data else "")
        + '<Record action="/api/oracle/voice-response" maxLength="45" playBeep="true" trim="trim-silence"/>'
        '</Response>'
    )
    return Response(twiml, mimetype="application/xml")

