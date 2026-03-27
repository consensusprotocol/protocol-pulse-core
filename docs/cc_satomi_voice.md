Read ~/protocol_pulse/core/models.py lines 12-90 (User model).
Read ~/protocol_pulse/core/routes.py lines 119-145 (premium_required decorator).
Read ~/protocol_pulse/.env (grep TWILIO and STRIPE lines only - do not print full file).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SATOMI VOICE SYSTEM + PREMIUM ONBOARDING + TEAM PROMO CODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Install twilio if not installed:
  pip install twilio --break-system-packages 2>/dev/null

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1: DATABASE MIGRATION — Add phone_number to User model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In models.py, add to the User class after stripe_subscription_id:
  # Satomi voice call opt-in
  phone_number = db.Column(db.String(20), nullable=True)  # E.164 format +1XXXXXXXXXX
  satomi_calls_enabled = db.Column(db.Boolean, default=False)  # opt-in to daily calls
  satomi_call_time = db.Column(db.String(10), default='09:00')  # preferred call time ET

Run the migration:
  python3 -c "
  import sys; sys.path.insert(0,'/home/ultron/protocol_pulse/core')
  from app import app, db
  with app.app_context():
      try:
          db.engine.execute('ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)')
          db.engine.execute('ALTER TABLE users ADD COLUMN satomi_calls_enabled BOOLEAN DEFAULT 0')
          db.engine.execute('ALTER TABLE users ADD COLUMN satomi_call_time VARCHAR(10) DEFAULT \"09:00\"')
          print('Migration OK')
      except Exception as e:
          print(f'Migration note: {e}')  # Column may already exist
  "

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2: SATOMI VOICE SERVICE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create ~/protocol_pulse/services/satomi_voice.py:

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

import os, logging
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
        import re
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
        import re
        clean = re.sub(r'[*#_`]', '', brief_text)[:2000]
        resp.say(clean, voice='Polly.Joanna', language='en-US')
    elif digit == '2' and market_summary:
        import re
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
        import re
        clean = re.sub(r'[*#_`<>]', '', brief_text)[:300]
        body = f"⚡ SATOMI BRIEF\n{clean}\n\nFull brief: protocolpulse.io/briefings\n\nReply STOP to unsubscribe."
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
        try:
            sys.path.insert(0, '/home/ultron/protocol_pulse')
            from services.stage_broadcast_service import get_latest_brief_text
            brief = get_latest_brief_text()
        except:
            brief = None
        
        if brief:
            import re
            clean = re.sub(r'[*#_`]', '', brief)[:280]
            resp.message(f"⚡ {clean}\n\nprotocolpulse.io")
        else:
            resp.message("⚡ Satomi: No brief ready. Check protocolpulse.io for live intel.")
    
    elif body_lower in ('stop', 'unsubscribe'):
        resp.message("You've been unsubscribed from Satomi briefs. Reply START to re-subscribe.")
    
    elif body_lower in ('start', 'subscribe'):
        resp.message("⚡ Welcome back to Satomi briefs. Text BRIEF anytime for your signal.")
    
    else:
        resp.message("⚡ Satomi here. Text BRIEF for your intelligence signal. protocolpulse.io")
    
    return str(resp)


def call_all_opted_in_subscribers(brief_text: str) -> dict:
    """
    Call all premium subscribers who have opted in to Satomi calls.
    Called by cron at their preferred time.
    Returns summary of calls made.
    """
    results = {'called': 0, 'failed': 0, 'skipped': 0}
    try:
        import sys
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
                import time
                time.sleep(1)
    except Exception as e:
        logger.error(f'call_all_opted_in_subscribers error: {e}')
    
    return results

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 3: FLASK ROUTES — Add to core/routes.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add these routes to core/routes.py (find a good place near other /api routes):

@app.route('/api/satomi/voice', methods=['POST', 'GET'])
def satomi_voice_incoming():
    """Twilio webhook: handles incoming calls to our number. Set this URL in Twilio console."""
    from flask import Response
    try:
        from services.satomi_voice import generate_incoming_twiml
        # Get latest brief from stage broadcast queue
        brief_text = None
        try:
            import json
            queue_path = '/home/ultron/protocol_pulse/video_pipeline_v3/data/stage_briefs/broadcast_queue.json'
            with open(queue_path) as f:
                queue = json.load(f)
            if queue:
                # Get first non-filler item
                for item in queue:
                    if item.get('type') not in ('FILLER_INSIGHT',) and item.get('script'):
                        brief_text = item['script']
                        break
                if not brief_text and queue[0].get('script'):
                    brief_text = queue[0]['script']
        except Exception:
            pass
        
        twiml = generate_incoming_twiml(brief_text)
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        logging.error(f'satomi_voice_incoming error: {e}')
        from twilio.twiml.voice_response import VoiceResponse
        resp = VoiceResponse()
        resp.say("Signal unavailable. Stay sovereign.", voice='Polly.Joanna')
        return Response(str(resp), mimetype='text/xml')


@app.route('/api/satomi/voice/choice', methods=['POST'])
def satomi_voice_choice():
    """Handles menu digit press from incoming call."""
    from flask import Response, request
    try:
        from services.satomi_voice import generate_choice_twiml
        digit = request.form.get('Digits', '')
        brief_text = request.form.get('brief_text', '')
        twiml = generate_choice_twiml(digit, brief_text, '')
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        from twilio.twiml.voice_response import VoiceResponse
        resp = VoiceResponse()
        resp.say("Stay sovereign.", voice='Polly.Joanna')
        return Response(str(resp), mimetype='text/xml')


@app.route('/api/satomi/voice/outbound-twiml', methods=['POST', 'GET'])
def satomi_voice_outbound_twiml():
    """TwiML served when outbound call is answered by subscriber."""
    from flask import Response
    try:
        from services.satomi_voice import generate_incoming_twiml
        brief_text = None
        try:
            import json
            queue_path = '/home/ultron/protocol_pulse/video_pipeline_v3/data/stage_briefs/broadcast_queue.json'
            with open(queue_path) as f:
                queue = json.load(f)
            if queue and queue[0].get('script'):
                brief_text = queue[0]['script']
        except Exception:
            pass
        twiml = generate_incoming_twiml(brief_text)
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        from twilio.twiml.voice_response import VoiceResponse
        resp = VoiceResponse()
        resp.say("Good morning. Satomi here with your Protocol Pulse brief. Stay sovereign.", voice='Polly.Joanna')
        return Response(str(resp), mimetype='text/xml')


@app.route('/api/satomi/sms', methods=['POST'])
def satomi_sms_incoming():
    """Twilio webhook: handles incoming SMS."""
    from flask import Response, request
    try:
        from services.satomi_voice import handle_incoming_sms
        from_number = request.form.get('From', '')
        body = request.form.get('Body', '')
        twiml = handle_incoming_sms(from_number, body)
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message("⚡ Satomi: protocolpulse.io")
        return Response(str(resp), mimetype='text/xml')


@app.route('/api/satomi/call-subscribers', methods=['POST'])
def satomi_call_subscribers():
    """Internal endpoint: trigger outbound calls to all opted-in subscribers."""
    # Require internal auth token
    from flask import request, jsonify
    token = request.headers.get('X-Internal-Token', '')
    if token != os.environ.get('INTERNAL_API_TOKEN', 'pp-internal-2026'):
        return jsonify({'error': 'unauthorized'}), 403
    try:
        from services.satomi_voice import call_all_opted_in_subscribers
        brief_text = request.json.get('brief_text', 'Satomi here with your Protocol Pulse daily signal.')
        results = call_all_opted_in_subscribers(brief_text)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 4: PROMO CODE — SOVEREIGN-TEAM-2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add to routes.py near the /join or /premium routes:

@app.route('/api/apply-promo', methods=['POST'])
def apply_promo_code():
    """Apply a promo code to unlock premium access for team/testing."""
    from flask import request, jsonify, session
    code = request.json.get('code', '').strip().upper()
    
    PROMO_CODES = {
        'SOVEREIGN-TEAM-2026': 'commander',
        'STAY-SOVEREIGN': 'operator',
    }
    
    tier = PROMO_CODES.get(code)
    if not tier:
        return jsonify({'success': False, 'error': 'Invalid promo code'}), 400
    
    # Apply to current user if logged in
    if current_user.is_authenticated:
        current_user.subscription_tier = tier
        db.session.commit()
        return jsonify({'success': True, 'tier': tier, 'message': f'Commander access activated. Welcome, Sovereign.'})
    else:
        # Store in session for post-login application
        session['pending_promo_tier'] = tier
        return jsonify({'success': True, 'tier': tier, 'redirect': '/login?promo=1'})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 5: ENV CLEANUP — ensure correct Twilio creds are used
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The .env has two sets of Twilio creds. The LAST one wins (ACbb20ca... with +13185048199).
Verify by checking:
  python3 -c "import os; from dotenv import load_dotenv; load_dotenv('/home/ultron/protocol_pulse/.env'); print(os.environ.get('TWILIO_ACCOUNT_SID','')[:10], os.environ.get('TWILIO_FROM',''))"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  kill -HUP $(pgrep -f "gunicorn.*5000" | grep -v golds | grep -v relay | head -1)
  sleep 8
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/api/satomi/voice
  # Expected: 200 with XML response

COMMIT:
  git add core/models.py core/routes.py services/satomi_voice.py
  git commit -m "feat(satomi+voice): Twilio voice/SMS handler, per-subscriber calls, promo codes"
  git push
