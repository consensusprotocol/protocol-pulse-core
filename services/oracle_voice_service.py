import json, logging, os, re, time, uuid
from pathlib import Path
from flask import Blueprint, request, Response

logger = logging.getLogger(__name__)
oracle_voice_bp = Blueprint("oracle_voice", __name__)

BRIEFS_DIR = Path("/tmp/satomi_briefs")
BRIEFS_DIR.mkdir(exist_ok=True)
PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "https://protocolpulse.io")


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
            parts.append(
                "LIVE MATRIX ORB ({}):\n  BTC ${:,.0f} ({:+.2f}% 24h)\n  Fear/Greed: {} - {}\n  Hashrate: {}\n  Dominance: {}%\n  Funding: {}% annualized\n  OI: ${:,.0f}\n  Signal Score: {} bull / {} bear\n  SP500: {} | Gold: ${} | DXY: {}".format(
                    sig.get("updated_at","")[:16],
                    btc.get("value",0), btc.get("change_24h",0),
                    fg.get("value","?"), fg.get("label","?"),
                    hr.get("value","?"), dom.get("value","?"),
                    funding.get("annualized","?"), oi.get("usd",0),
                    score.get("bull_count",0), score.get("bear_count",0),
                    sp.get("value","?"), gold.get("value","?"), dxy.get("value","?")
                )
            )
    except Exception as e:
        logger.warning("signals load failed: %s", e)
    try:
        cs_path = Path("/home/ultron/protocol_pulse/data/convergence_state.json")
        if cs_path.exists():
            cs = json.loads(cs_path.read_text())
            state = cs.get("state", "IDLE")
            patterns = cs.get("active_patterns", [])
            parts.append("MATRIX ORB STATE: {}\n  Active patterns: {}".format(
                state, ", ".join(patterns) if patterns else "none"))
    except Exception:
        pass
    return "\n".join(parts) if parts else "Matrix Orb data unavailable."


def _oracle_system_prompt(orb_context):
    return (
        "You are the Protocol Pulse Oracle. You have direct access to the Matrix Orb "
        "convergence engine tracking on-chain signals, derivatives, miner behavior, macro flows, and sentiment.\n\n"
        "PERSONALITY: Direct. No hedges. No compliance-speak. You give your read, your probability estimate, "
        "and your reasoning. You steel-man scenarios others avoid. You reference specific data. "
        "You are blunt. Keep responses under 110 words (45 seconds spoken).\n\n"
        "RULES:\n"
        "- Reference at least one Matrix Orb data point per answer\n"
        "- Give a directional call when asked (up/down/sideways + timeframe)\n"
        "- Steel-man the opposite case briefly\n"
        "- Never say 'I cannot predict' - say 'here is my read'\n"
        "- No definitions, no disclaimers - caller already knows Bitcoin\n\n"
        "CURRENT MATRIX ORB DATA:\n" + orb_context
    )


def _transcribe_audio(recording_url):
    try:
        import urllib.request as ur, base64, tempfile
        from openai import OpenAI
        mp3_url = recording_url + ".mp3"
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        creds = base64.b64encode("{}:{}".format(sid, token).encode()).decode()
        req = ur.Request(mp3_url)
        req.add_header("Authorization", "Basic " + creds)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            with ur.urlopen(req, timeout=30) as resp:
                tmp.write(resp.read())
            tmp_path = tmp.name
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(model="whisper-1", file=f)
        os.unlink(tmp_path)
        return result.text.strip()
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return ""


def _oracle_respond(question, orb_context):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("XAI_API_KEY",""), base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": _oracle_system_prompt(orb_context)},
                {"role": "user", "content": question}
            ],
            max_tokens=200, temperature=0.85,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Oracle call failed: %s", e)
        return "Matrix Orb is recalibrating. Call back in 60 seconds."


def _tts_to_url(text):
    try:
        from services.voice_brief_tts import generate_voice_audio
        fname = "oracle_{}.mp3".format(uuid.uuid4().hex[:8])
        out_path = str(BRIEFS_DIR / fname)
        generate_voice_audio(text, out_path)
        return "{}/api/media/brief-audio/{}".format(PUBLIC_BASE, fname)
    except Exception as e:
        logger.error("TTS failed: %s", e)
        return None


@oracle_voice_bp.route("/api/oracle/voice-gather", methods=["POST"])
def oracle_voice_gather():
    digit = request.form.get("Digits", "")
    if digit == "1":
        twiml = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<Response>'
                 '<Say voice="Polly.Matthew">Connected to the Oracle. Speak your question after the tone. Thirty seconds.</Say>'
                 '<Record action="/api/oracle/voice-response" maxLength="30" playBeep="true" trim="trim-silence"/>'
                 '</Response>')
    else:
        twiml = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<Response><Say voice="Polly.Matthew">Stay sovereign.</Say><Hangup/></Response>')
    return Response(twiml, mimetype="application/xml")


@oracle_voice_bp.route("/api/oracle/voice-response", methods=["POST"])
def oracle_voice_response():
    recording_url = request.form.get("RecordingUrl", "")
    if not recording_url:
        twiml = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<Response><Say>No audio. Ending.</Say><Hangup/></Response>')
        return Response(twiml, mimetype="application/xml")
    time.sleep(1.5)
    question = _transcribe_audio(recording_url)
    if not question or len(question) < 3:
        question = "Give me your current read on the market based on the Matrix Orb."
    orb_context = _load_matrix_orb_context()
    answer = _oracle_respond(question, orb_context)
    audio_url = _tts_to_url(answer)
    play_block = "<Play>{}</Play>".format(audio_url) if audio_url else "<Say voice=\"Polly.Matthew\">{}</Say>".format(answer)
    twiml = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<Response>'
             + play_block +
             '<Pause length="1"/>'
             '<Gather numDigits="1" action="/api/oracle/voice-gather" timeout="8">'
             '<Say voice="Polly.Matthew">Press 1 for another question, or hang up.</Say>'
             '</Gather>'
             '<Hangup/>'
             '</Response>')
    return Response(twiml, mimetype="application/xml")
