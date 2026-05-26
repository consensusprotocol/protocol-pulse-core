"""
NEWSLETTER AUTOMATION — Protocol Pulse
========================================
Entrypoint for scheduled daily briefing sends.

Usage:
  From APScheduler (services/scheduler.py):
    from pp_services.newsletter_automation import send_daily_briefing
    _apscheduler.add_job(send_daily_briefing, trigger=CronTrigger(hour=13, minute=0), id="newsletter_daily")

  Cron (if APScheduler disabled):
    0 13 * * * cd /home/ultron/protocol_pulse && source .env && python3 -c "
    from pp_services.newsletter_automation import send_daily_briefing
    import flask; app = __import__('app').app
    with app.app_context(): send_daily_briefing()
    "

Laws:
  1. Resend API only — RESEND_API_KEY must be set
  2. One send per day — enforced by newsletter_service.already_sent_today()
  3. No crash on missing key — log warning and skip
"""

import logging

logger = logging.getLogger(__name__)


def send_daily_briefing(force: bool = False) -> dict:
    """
    Assemble and send the daily Protocol Pulse briefing to all active subscribers.

    Args:
        force: Skip LAW 2 daily-send guard (admin use only).

    Returns:
        dict with keys: success, recipient_count, subject, error (if any), skipped (if LAW 2 guard)
    """
    import os

    if not os.environ.get("RESEND_API_KEY"):
        logger.warning(
            "RESEND_API_KEY not set — newsletter send skipped. "
            "Set RESEND_API_KEY in .env to enable automated sends."
        )
        return {"success": False, "error": "RESEND_API_KEY not configured", "skipped": True}

    try:
        from pp_services.newsletter_service import send_daily_newsletter
        result = send_daily_newsletter(force=force)
        if result.get("success"):
            logger.info(
                "Daily briefing sent: %d recipients, subject=%s",
                result.get("recipient_count", 0),
                result.get("subject", ""),
            )
        elif result.get("skipped"):
            logger.info("Daily briefing skipped (LAW 2 — already sent today)")
        else:
            logger.error("Daily briefing failed: %s", result.get("error"))
        return result
    except Exception as e:
        logger.error("send_daily_briefing exception: %s", e)
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Allow direct invocation: python3 -m services.newsletter_automation
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from app import app
    with app.app_context():
        force = "--force" in sys.argv
        result = send_daily_briefing(force=force)
        print(result)
        sys.exit(0 if result.get("success") or result.get("skipped") else 1)
