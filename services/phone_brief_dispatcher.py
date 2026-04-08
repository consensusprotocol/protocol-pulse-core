#!/usr/bin/env python3
# phone_brief_dispatcher.py
# Runs every minute via cron: */1 * * * *
# Fires calls for subscribers whose scheduled call_time_et matches now (ET)
# Handles free (one-way) and premium (Oracle Q+A) tiers
import os, sys, logging
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / 'core'))
sys.path.insert(0, str(BASE))
os.chdir(str(BASE / core))  # Flask expects cwd=core/

logging.basicConfig(
    level=logging.INFO,
    format="[dispatcher] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(BASE / 'logs' / 'phone_dispatcher.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger('dispatcher')

def _load_env():
    env_path = BASE / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

def _current_time_et():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        import pytz
        return datetime.now(pytz.timezone('America/New_York'))

def _sub_time_et(sub):
    call_time = getattr(sub, 'call_time_et', '08:00') or '08:00'
    tz_str = getattr(sub, 'timezone', 'America/New_York') or 'America/New_York'
    return call_time, tz_str

def _already_called_today(sub, now_et):
    last = getattr(sub, 'last_called', None)
    if last is None:
        return False
    if isinstance(last, str):
        from datetime import datetime as _dt
        last = _dt.fromisoformat(last)
    return last.date() == now_et.date()

def run():
    from app import app, db
    from models import SmsSubscriber
    from services.satomi_brief_generator import generate_brief_script
    from services.twilio_service import send_morning_brief_call, send_premium_brief_call, send_sms

    now_et = _current_time_et()
    current_hhmm = now_et.strftime('%H:%M')
    logger.info("Dispatcher running at %s ET", current_hhmm)

    with app.app_context():
        subs = SmsSubscriber.query.filter_by(subscribed=True, call_active=True).all()
        logger.info("Active subscribers: %d", len(subs))

        for sub in subs:
            call_time, tz_str = _sub_time_et(sub)

            # Convert subscriber's desired time to ET equivalent for this day
            # For non-ET timezones, convert their HH:MM to ET
            try:
                if tz_str == 'America/New_York':
                    target_hhmm = call_time
                else:
                    from zoneinfo import ZoneInfo
                    h, m = map(int, call_time.split(':'))
                    sub_tz = ZoneInfo(tz_str)
                    et_tz = ZoneInfo('America/New_York')
                    sub_local = now_et.astimezone(sub_tz).replace(hour=h, minute=m, second=0, microsecond=0)
                    target_hhmm = sub_local.astimezone(et_tz).strftime('%H:%M')
            except Exception:
                target_hhmm = call_time

            if target_hhmm != current_hhmm:
                continue

            if _already_called_today(sub, now_et):
                logger.info("Already called %s today, skipping", sub.phone[-4:])
                continue

            logger.info("Firing call for %s (tier=%s, lang=%s, time=%s)",
                sub.phone[-4:], sub.tier, getattr(sub,'language','en'), call_time)

            try:
                script = generate_brief_script()
                tier = getattr(sub, 'tier', 'free') or 'free'

                if tier == 'premium':
                    call_ok = send_premium_brief_call(sub.phone, script)
                else:
                    call_ok = send_morning_brief_call(sub.phone, script)

                # SMS summary for all tiers
                sms_text = "[PP BRIEF] BTC: ${:,.0f} | {}\n{}...".format(
                    0, now_et.strftime('%b %d %Y'),
                    script[:200]
                )
                send_sms(sub.phone, sms_text)

                # Update last_called
                sub.last_called = datetime.now(timezone.utc)
                db.session.commit()
                logger.info("Delivered to %s (call=%s)", sub.phone[-4:], call_ok)

            except Exception as e:
                logger.error("Failed delivery to %s: %s", sub.phone[-4:], e)

if __name__ == '__main__':
    run()
