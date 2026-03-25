"""
Satomi Voice Service — Twilio-powered AI voice briefings for premium subscribers.

Three modes:
1. INCOMING: Subscriber calls the Twilio number → Satomi answers and delivers a brief
2. OUTBOUND: System calls subscriber at their preferred time with a brief
3. SMS: Subscriber texts "brief" → receives Satomi's latest intelligence brief via SMS

Architecture:
- TWILIO_FROM: Our Twilio number (the caller ID for outbound, the number subscribers call)
- Subscriber phone numbers: stored in User.phone_number (per-user, not hardcoded)
- Works for unlimited subscribers, each gets their own call/SMS
"""

import os, logging, re, sys, time
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say, Gather, Play
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger('satomi_voice')

TWILIO_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM = os.environ.get('TWILIO_FROM', '')

# Use the NEW credentials (ACbb20ca...) since those match the new number
# Check which SID matches the FROM number
def get_client():
    """Get Twilio client with correct credentials."""
    return Client(TWILIO_SID, TWILIO_AUTH)


def generate_incoming_twiml(brief_text: str = None) -> str:
    """
    TwiML response for when someone calls our Twilio number.
    Satomi greets them and delivers the latest brief.
    """
    resp = VoiceResponse()

    # Gather optional: press 1 for full brief, 2 for market summary, hang up for closing
    gather = Gather(num_digits=1, timeout=3, action='/api/satomi/voice/choice')
    gather.say(
        "Hello. I'm Satomi, your Protocol Pulse signal anchor. "
        "Press 1 for the full intelligence brief. "
        "Press 2 for a quick market summary. "
        "Or stay on the line for today's top signal.",
        voice='Polly.Joanna',
        language='en-US'
    )
    resp.append(gather)

    # Default: read the brief if no key pressed
    if brief_text:
        # Clean text for TTS
        clean = re.sub(r'[*#_`]', '', brief_text)[:1500]  # max 1500 chars for TTS
        resp.say(clean, voice='Polly.Joanna', language='en-US')
    else:
        resp.say(
            "Bitcoin intelligence is loading. Stay sovereign.",
            voice='Polly.Joanna',
            language='en-US'
        )

    resp.say("Signal complete. Stay sovereign.", voice='Polly.Joanna')
    return str(resp)


def generate_choice_twiml(digit: str, brief_text: str, market_summary: str) -> str:
    """Handle menu choice from incoming call."""
    resp = VoiceResponse()
    if digit == '1' and brief_text:
        clean = re.sub(r'[*#_`]', '', brief_text)[:2000]
        resp.say(clean, voice='Polly.Joanna', language='en-US')
    elif digit == '2' and market_summary:
        clean = re.sub(r'[*#_`]', '', market_summary)[:800]
        resp.say(clean, voice='Polly.Joanna', language='en-US')
    else:
        resp.say("Signal not available. Stay sovereign.", voice='Polly.Joanna')
    resp.say("Stay sovereign.", voice='Polly.Joanna')
    return str(resp)


def make_outbound_call(to_number: str, brief_text: str) -> dict:
    """
    Make an outbound call to a subscriber's phone number.
    to_number: subscriber's phone in E.164 format (+1XXXXXXXXXX)
    Returns: {'success': bool, 'call_sid': str, 'error': str}
    """
    try:
        client = get_client()
        call = client.calls.create(
            to=to_number,
            from_=TWILIO_FROM,
            url='https://protocolpulse.io/api/satomi/voice/outbound-twiml',
            method='POST',
            timeout=30,
        )
        logger.info(f'Outbound call initiated to {to_number[:6]}*** SID:{call.sid}')
        return {'success': True, 'call_sid': call.sid}
    except Exception as e:
        logger.error(f'Outbound call failed to {to_number[:6]}***: {e}')
        return {'success': False, 'error': str(e)}


def send_sms_brief(to_number: str, brief_text: str) -> dict:
    """
    Send a brief via SMS to a subscriber.
    Truncates to SMS-friendly length with link to full brief.
    """
    try:
        client = get_client()
        clean = re.sub(r'[*#_`<>]', '', brief_text)[:300]
        body = f"\u26a1 SATOMI BRIEF\n{clean}\n\nFull brief: protocolpulse.io/briefings\n\nReply STOP to unsubscribe."
        msg = client.messages.create(
            to=to_number,
            from_=TWILIO_FROM,
            body=body
        )
        return {'success': True, 'message_sid': msg.sid}
    except Exception as e:
        logger.error(f'SMS failed: {e}')
        return {'success': False, 'error': str(e)}


def handle_incoming_sms(from_number: str, body: str) -> str:
    """
    Handle incoming SMS from a subscriber.
    Returns TwiML MessagingResponse string.
    """
    resp = MessagingResponse()
    body_lower = body.strip().lower()

    if body_lower in ('brief', 'signal', 'intel', 'b'):
        # Get latest brief and send it
        brief = None
        try:
            sys.path.insert(0, '/home/ultron/protocol_pulse')
            from services.stage_broadcast_service import get_latest_brief_text
            brief = get_latest_brief_text()
        except Exception:
            brief = None

        if brief:
            clean = re.sub(r'[*#_`]', '', brief)[:280]
            resp.message(f"\u26a1 {clean}\n\nprotocolpulse.io")
        else:
            resp.message("\u26a1 Satomi: No brief ready. Check protocolpulse.io for live intel.")

    elif body_lower in ('stop', 'unsubscribe'):
        resp.message("You've been unsubscribed from Satomi briefs. Reply START to re-subscribe.")

    elif body_lower in ('start', 'subscribe'):
        resp.message("\u26a1 Welcome back to Satomi briefs. Text BRIEF anytime for your signal.")

    else:
        resp.message("\u26a1 Satomi here. Text BRIEF for your intelligence signal. protocolpulse.io")

    return str(resp)


def call_all_opted_in_subscribers(brief_text: str) -> dict:
    """
    Call all premium subscribers who have opted in to Satomi calls.
    Called by cron at their preferred time.
    Returns summary of calls made.
    """
    results = {'called': 0, 'failed': 0, 'skipped': 0}
    try:
        sys.path.insert(0, '/home/ultron/protocol_pulse/core')
        from app import app
        with app.app_context():
            from models import User
            # Get all premium subscribers with phone and opt-in enabled
            subscribers = User.query.filter(
                User.satomi_calls_enabled == True,
                User.phone_number.isnot(None),
                User.phone_number != '',
                User.subscription_tier.in_(['commander', 'sovereign', 'operator'])
            ).all()

            for sub in subscribers:
                result = make_outbound_call(sub.phone_number, brief_text)
                if result['success']:
                    results['called'] += 1
                else:
                    results['failed'] += 1

                # Rate limit: 1 call per second to avoid Twilio throttling
                time.sleep(1)
    except Exception as e:
        logger.error(f'call_all_opted_in_subscribers error: {e}')

    return results
