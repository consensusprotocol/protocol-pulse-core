"""Telegram Alerts — push notifications for pipeline events.

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
All functions are no-ops when tokens aren't configured (never crash).
"""
import logging
import os

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

LEVEL_EMOJI = {
    "info": "\u2139\ufe0f",       # ℹ️
    "warning": "\u26a0\ufe0f",    # ⚠️
    "error": "\u274c",            # ❌
    "critical": "\U0001f6a8",     # 🚨
}


def send_alert(message: str, level: str = "info") -> bool:
    """Send a Telegram message. Returns True on success, False otherwise.

    Levels: info, warning, error, critical.
    No-op if bot token or chat ID not configured.
    """
    if not BOT_TOKEN or not CHAT_ID:
        return False

    try:
        import requests
    except ImportError:
        logger.warning("requests not available for Telegram alerts")
        return False

    emoji = LEVEL_EMOJI.get(level, "\u2139\ufe0f")
    text = f"{emoji} *Protocol Pulse*\n{message}"

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=10)
        if resp.status_code == 200:
            return True
        logger.warning(f"Telegram API {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")
    return False


def alert_pipeline_start(episode_date: str, test_mode: bool = False):
    mode = " (TEST)" if test_mode else ""
    send_alert(f"Pipeline started{mode} — {episode_date}")


def alert_pipeline_success(episode_date: str, quality_score: int,
                           duration: float, output_path: str):
    send_alert(
        f"Episode {episode_date} complete\n"
        f"Score: {quality_score}/100\n"
        f"Duration: {duration:.0f}s\n"
        f"Path: {os.path.basename(output_path)}"
    )


def alert_pipeline_failure(episode_date: str, step: str, error: str):
    send_alert(
        f"PIPELINE FAILED at step {step}\n"
        f"Episode: {episode_date}\n"
        f"Error: {error[:200]}",
        level="critical",
    )


def alert_quality_hold(episode_date: str, quality_score: int, reason: str = ""):
    send_alert(
        f"QUALITY HOLD — Episode {episode_date}\n"
        f"Score: {quality_score}/100\n"
        f"Below 85 threshold"
        + (f"\nReason: {reason}" if reason else ""),
        level="warning",
    )


def alert_upload_success(episode_date: str, youtube_url: str):
    send_alert(f"Uploaded: {episode_date}\n{youtube_url}")
