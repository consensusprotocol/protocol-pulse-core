#!/usr/bin/env python3
"""
SYSTEM 6: Telegram + Twilio Notification Hub

Central notification system for Protocol Pulse pipeline enforcement.
- Always sends Telegram (instant, free)
- Optional SMS via Twilio for critical-only alerts
- Never crashes the caller — all failures logged silently

Usage:
    from utils.notify import notify, notify_critical
    notify("Grade improved to 72")
    notify_critical("Both GPUs idle for 2+ hours")

Env vars (from .env):
    TELEGRAM_BOT_TOKEN  — from @BotFather
    TELEGRAM_CHAT_ID    — your personal chat id
    TWILIO_ACCOUNT_SID  — optional
    TWILIO_AUTH_TOKEN    — optional
    TWILIO_FROM          — optional (+1xxxxxxxxxx)
    TWILIO_TO            — optional (+1xxxxxxxxxx)
"""
import json
import logging
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS_FILE = os.path.join(BASE, 'PIPELINE_LESSONS.md')

# ── Load env vars ────────────────────────────────────────────────────────────

def _load_env():
    """Load .env file into os.environ if not already set."""
    env_path = os.path.join(BASE, '.env')
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    key = key.strip()
                    val = val.strip().strip("'").strip('"')
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass

_load_env()


def _get_env(key: str) -> str:
    return os.environ.get(key, '')


# ── Telegram ─────────────────────────────────────────────────────────────────

def _send_telegram(message: str) -> bool:
    """Send a Telegram message. Returns True on success."""
    bot_token = _get_env('TELEGRAM_BOT_TOKEN')
    chat_id = _get_env('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id:
        return False

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = json.dumps({
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True,
    }).encode()

    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status == 200
    except Exception as e:
        logger.warning(f'Telegram send failed: {e}')
        return False


# ── Twilio SMS ───────────────────────────────────────────────────────────────

def _send_sms(message: str) -> bool:
    """Send SMS via Twilio. Returns True on success."""
    sid = _get_env('TWILIO_ACCOUNT_SID')
    token = _get_env('TWILIO_AUTH_TOKEN')
    from_num = _get_env('TWILIO_FROM')
    to_num = _get_env('TWILIO_TO')

    if not all([sid, token, from_num, to_num]):
        return False

    url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
    data = urllib.parse.urlencode({
        'From': from_num,
        'To': to_num,
        'Body': message[:1600],  # SMS limit
    }).encode()

    try:
        # Basic auth
        import base64
        credentials = base64.b64encode(f'{sid}:{token}'.encode()).decode()
        req = urllib.request.Request(url, data=data, headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status in (200, 201)
    except Exception as e:
        logger.warning(f'Twilio SMS send failed: {e}')
        return False


# ── Log failures to PIPELINE_LESSONS.md ──────────────────────────────────────

def _log_failure(channel: str, error: str):
    """Log notification failure to PIPELINE_LESSONS.md."""
    try:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        entry = f"\n### NOTIFY FAILURE [{ts}] {channel}: {error}\n"
        with open(LESSONS_FILE, 'a') as f:
            f.write(entry)
    except Exception:
        pass


# ── Public API ───────────────────────────────────────────────────────────────

def notify(message: str, critical: bool = False):
    """Send notification. Always Telegram. If critical=True, also SMS.

    Never crashes the caller.
    """
    prefix = '🚨 *CRITICAL*' if critical else '📡 *Protocol Pulse*'
    formatted = f'{prefix}\n{message}'

    # Always send Telegram
    tg_ok = _send_telegram(formatted)
    if not tg_ok:
        _log_failure('telegram', f'Failed to send: {message[:80]}')

    # Critical = also SMS (if Twilio configured)
    if critical:
        sms_ok = _send_sms(f'[Protocol Pulse CRITICAL] {message}')
        if not sms_ok and _get_env('TWILIO_ACCOUNT_SID'):
            _log_failure('twilio', f'SMS failed: {message[:80]}')


def notify_critical(message: str):
    """Convenience wrapper for critical notifications (Telegram + SMS)."""
    notify(message, critical=True)
