#!/usr/bin/env python3
"""telegram.py — zero-dependency Telegram helper for the Sovereign Agent Fleet.

Follows the same env var contract as services/scheduler.py + services/local_watchdog.py:
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID

No-op (returns False) when tokens aren't configured. Never raises.
"""
import logging
import os

logger = logging.getLogger("agent.telegram")


def send(message, silent=False):
    """Send a Telegram message. Returns True on 200 response, False otherwise."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.debug("telegram skipped — TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set")
        return False
    try:
        import requests
    except ImportError:
        logger.warning("requests not installed — telegram alert dropped")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
                "disable_notification": bool(silent),
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        logger.warning(f"telegram API {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        logger.warning(f"telegram alert failed: {exc}")
    return False
