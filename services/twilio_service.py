"""
Twilio SMS + Voice Delivery Service
Direct phone-based intelligence delivery for Protocol Pulse.
Uses Kokoro af_heart (Eryn) for voice calls via <Play>, not Twilio alice TTS.
"""
import os
import uuid
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

_client = None

BRIEFS_DIR = '/home/ultron/protocol_pulse/static/audio/oracle'
import os; os.makedirs(BRIEFS_DIR, exist_ok=True)
PUBLIC_BASE = os.getenv('PUBLIC_BASE_URL', 'https://protocolpulse.io')


def get_client() -> Client:
    global _client
    if _client is None:
        sid = os.getenv('TWILIO_ACCOUNT_SID')
        token = os.getenv('TWILIO_AUTH_TOKEN')
        if not sid or not token:
            raise RuntimeError('TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set')
        _client = Client(sid, token)
    return _client


def _from_number() -> str:
    return os.getenv('TWILIO_FROM', '+13185048199')


def _generate_and_url(text: str) -> str:
    """Generate Kokoro audio, return public URL for Twilio <Play>."""
    from services.voice_brief_tts import generate_voice_audio
    filename = f'{uuid.uuid4().hex}.mp3'
    path = os.path.join(BRIEFS_DIR, filename)
    generate_voice_audio(text, path)
    return f'{PUBLIC_BASE}/api/media/brief-audio/{filename}'


def send_sms(to: str, message: str) -> bool:
    """Send an SMS. Returns True on success."""
    try:
        msg = get_client().messages.create(
            body=message[:1600],
            from_=_from_number(),
            to=to,
        )
        logger.info('SMS sent: %s to %s', msg.sid, to)
        return True
    except Exception as e:
        logger.error('SMS failed to %s: %s', to, e)
        return False


def send_voice_call(to: str, twiml_message: str) -> bool:
    """Place a voice call with Kokoro-generated audio."""
    try:
        audio_url = _generate_and_url(twiml_message)
        twiml = f'<Response><Play>{audio_url}</Play></Response>'
        call = get_client().calls.create(
            twiml=twiml,
            from_=_from_number(),
            to=to,
        )
        logger.info('Call initiated: %s to %s (audio: %s)', call.sid, to, audio_url)
        return True
    except Exception as e:
        logger.error('Call failed to %s: %s', to, e)
        return False


def send_morning_brief_call(to: str, brief_text: str) -> bool:
    """Place a voice call delivering the morning intelligence brief with Kokoro voice."""
    try:
        brief_url = _generate_and_url(brief_text)
        twiml = (
            f'<Response>'
            f'<Pause length="1"/>'
            f'<Play>{brief_url}</Play>'
            f'</Response>'
        )
        call = get_client().calls.create(
            twiml=twiml,
            from_=_from_number(),
            to=to,
            timeout=120,
        )
        logger.info('Morning brief call: %s to %s', call.sid, to)
        return True
    except Exception as e:
        logger.error('Morning brief call failed to %s: %s', to, e)
        return False


def send_spaces_alert(to: str, space_title: str, speaker: str, score: int) -> bool:
    """Send X Spaces hot-detection SMS alert."""
    msg = (
        f'[PROTOCOL PULSE] Hot X Space (score:{score}): '
        f'"{space_title}" with {speaker}. '
        f'Open Protocol Pulse for live intelligence.'
    )
    return send_sms(to, msg)


def _escape_twiml(text: str) -> str:
    """Escape characters that break TwiML XML."""
    return (
        text.replace('&', ' and ')
        .replace('<', '')
        .replace('>', '')
        .replace('"', "'")
    )


def send_premium_brief_call(to, brief_text):
    # Premium two-way call: briefing then Oracle Q+A
    try:
        brief_url = _generate_and_url(brief_text)
        twiml = (
            '<Response>'
            '<Pause length="1"/>'
            '<Play>' + brief_url + '</Play>'
            '<Pause length="1"/>'
            '<Gather numDigits="1" action="/api/oracle/voice-gather" timeout="12">'
            '<Say voice="Polly.Joanna">Press 1 to speak with the Oracle. Or hang up to end.</Say>'
            '</Gather>'
            '<Hangup/>'
            '</Response>'
        )
        call = get_client().calls.create(twiml=twiml, from_=_from_number(), to=to, timeout=180)
        logger.info('Premium Oracle call: %s to %s', call.sid, to)
        return True
    except Exception as e:
        logger.error('Premium call failed to %s: %s', to, e)
        return False
