"""Lightweight heartbeat service for Command Deck health actions."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict

import requests


def get_system_status() -> Dict:
    token = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
    chat = bool(os.environ.get("TELEGRAM_CHAT_ID"))
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "telegram_configured": token and chat,
        "telegram_token": token,
        "telegram_chat": chat,
        "status": "ready" if token and chat else "degraded",
    }


def send_heartbeat_sync() -> Dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {
            "success": False,
            "error": "missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID",
            "status_code": None,
        }

    text = (
        "pulse heartbeat\\n"
        "status: empire ready\\n"
        "signal lane: active\\n"
        f"timestamp: {datetime.utcnow().isoformat()}z"
    )
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"success": True, "status_code": 200}
        return {"success": False, "error": f"telegram returned {resp.status_code}", "status_code": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e), "status_code": None}
