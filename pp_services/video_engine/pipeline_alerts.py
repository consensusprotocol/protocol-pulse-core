"""
PIPELINE ALERTS
================
Webhook-based alerting for pipeline events.
Supports Discord and Telegram.

Env vars:
  DISCORD_WEBHOOK_URL  — Discord webhook for alerts
  TELEGRAM_BOT_TOKEN   — Telegram bot token
  TELEGRAM_CHAT_ID     — Telegram chat/group ID
  ENABLE_PIPELINE_ALERTS — Master switch (default: true)
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("PipelineAlerts")


def send_alert(title: str, message: str, level: str = "info", fields: Dict = None):
    """Send alert to all configured channels.

    Args:
        title: Alert title (e.g. "Pipeline Complete")
        message: Alert body
        level: "info", "warning", "error", "success"
        fields: Optional key-value pairs for structured data
    """
    if os.environ.get("ENABLE_PIPELINE_ALERTS", "true").lower() not in ("true", "1"):
        return

    discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat = os.environ.get("TELEGRAM_CHAT_ID")

    if discord_url:
        _send_discord(discord_url, title, message, level, fields)

    if telegram_token and telegram_chat:
        _send_telegram(telegram_token, telegram_chat, title, message, level, fields)

    if not discord_url and not (telegram_token and telegram_chat):
        logger.debug("No alert channels configured (set DISCORD_WEBHOOK_URL or TELEGRAM_BOT_TOKEN)")


def send_pipeline_complete(run_result: Dict, run_log: Dict):
    """Send a success alert after pipeline completes."""
    channels = run_result.get("channels_scanned", 0)
    highlights = run_result.get("videos_analyzed", 0)
    clips = run_result.get("clips_selected", 0)
    video = run_result.get("video", {})
    shorts_count = len(video.get("shorts", []))
    date = run_result.get("date", "unknown")

    feed_info = run_log.get("intel_feeds", {})
    articles = feed_info.get("articles", {}).get("count", 0)
    tweets = feed_info.get("tweets", {}).get("count", 0)

    message = (
        f"Scanned {channels} channels, analyzed {highlights} videos.\n"
        f"Selected {clips} clips, produced {shorts_count} shorts.\n"
        f"Generated {articles} articles, posted {tweets} tweets."
    )

    fields = {
        "Channels": str(channels),
        "Highlights": str(highlights),
        "Clips": str(clips),
        "Shorts": str(shorts_count),
        "Articles": str(articles),
        "Tweets": str(tweets)
    }

    send_alert(f"Pulse Check Complete — {date}", message, level="success", fields=fields)


def send_pipeline_error(error: str, stage: str = "unknown", date: str = None):
    """Send an error alert when pipeline fails."""
    date = date or datetime.now().strftime("%Y-%m-%d")
    message = f"Stage: {stage}\nError: {error}"
    send_alert(f"Pipeline FAILED — {date}", message, level="error",
               fields={"Stage": stage, "Error": error[:200]})


def send_ultron_offline(date: str = None):
    """Alert when Ultron is unreachable."""
    date = date or datetime.now().strftime("%Y-%m-%d")
    send_alert(
        f"Ultron OFFLINE — {date}",
        "Ultron GPU server is unreachable. Pipeline aborted.\nCheck: ssh ultron",
        level="error",
        fields={"Server": "video.protocolpulse.io", "Action": "SSH to ultron and restart api_server.py"}
    )


# ─────────────────────────────────────────────────────────
# DISCORD
# ─────────────────────────────────────────────────────────

LEVEL_COLORS = {
    "success": 0x2ECC71,   # green
    "info": 0x3498DB,      # blue
    "warning": 0xF39C12,   # orange
    "error": 0xE74C3C,     # red
}

LEVEL_EMOJI = {
    "success": ":white_check_mark:",
    "info": ":information_source:",
    "warning": ":warning:",
    "error": ":rotating_light:",
}


def _send_discord(webhook_url: str, title: str, message: str,
                  level: str, fields: Optional[Dict]):
    """Send a Discord webhook embed."""
    embed = {
        "title": f"{LEVEL_EMOJI.get(level, '')} {title}",
        "description": message,
        "color": LEVEL_COLORS.get(level, 0x95A5A6),
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Protocol Pulse Pipeline"}
    }

    if fields:
        embed["fields"] = [
            {"name": k, "value": v, "inline": True}
            for k, v in fields.items()
        ]

    payload = {"embeds": [embed]}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code not in (200, 204):
            logger.warning(f"Discord alert failed ({resp.status_code}): {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"Discord alert failed: {e}")


# ─────────────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────────────

LEVEL_ICON = {
    "success": "\u2705",
    "info": "\u2139\ufe0f",
    "warning": "\u26a0\ufe0f",
    "error": "\ud83d\udea8",
}


def _send_telegram(token: str, chat_id: str, title: str, message: str,
                   level: str, fields: Optional[Dict]):
    """Send a Telegram bot message."""
    icon = LEVEL_ICON.get(level, "")
    text = f"{icon} <b>{title}</b>\n\n{message}"

    if fields:
        text += "\n\n"
        for k, v in fields.items():
            text += f"<b>{k}:</b> {v}\n"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Telegram alert failed ({resp.status_code}): {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")
