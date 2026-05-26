"""
B1 NEWSLETTER CRON — Protocol Pulse
=====================================
Sends daily newsletter at 08:00 ET (13:00 UTC).
LAW 2: One per day — enforced in newsletter_service.send_daily_newsletter().

Run modes:
  python3 cron/newsletter_cron.py              # scheduler loop (blocking)
  python3 cron/newsletter_cron.py --now        # send immediately
  python3 cron/newsletter_cron.py --test TO    # test send to address

Cron alternative (system cron @ 13:00 UTC):
  0 13 * * * cd /home/ultron/protocol_pulse && python3 cron/newsletter_cron.py --now
"""

import sys
import os
import time
import logging
from datetime import datetime, timezone

# Ensure project root is in path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] newsletter_cron: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("newsletter_cron")

# 08:00 ET = 13:00 UTC (standard time) / 12:00 UTC (daylight saving)
# We schedule in UTC. Use 13:00 UTC as safe default (covers both).
SEND_HOUR_UTC = 13
SEND_MINUTE_UTC = 0


def _run_in_app_context(fn):
    """Execute fn() inside Flask app context."""
    from app import app
    with app.app_context():
        return fn()


def fire_newsletter(force: bool = False) -> dict:
    """Send today's newsletter. Wrapped in app context."""
    from pp_services.newsletter_service import send_daily_newsletter

    def _send():
        return send_daily_newsletter(force=force)

    try:
        return _run_in_app_context(_send)
    except Exception as e:
        logger.error(f"Newsletter send failed: {e}")
        return {"success": False, "error": str(e)}


def fire_test(to_email: str) -> dict:
    """Send test newsletter. Wrapped in app context."""
    from pp_services.newsletter_service import send_test_newsletter

    def _send():
        return send_test_newsletter(to_email)

    try:
        return _run_in_app_context(_send)
    except Exception as e:
        logger.error(f"Test newsletter send failed: {e}")
        return {"success": False, "error": str(e)}


def scheduler_loop():
    """
    Blocking loop — checks every 60 seconds, fires at SEND_HOUR_UTC:SEND_MINUTE_UTC UTC.
    LAW 2 (already_sent_today) prevents double-sends even if the process restarts.
    """
    logger.info(
        f"Newsletter cron started — will send at {SEND_HOUR_UTC:02d}:{SEND_MINUTE_UTC:02d} UTC daily"
    )
    last_fired_date = None

    while True:
        try:
            now = datetime.now(timezone.utc)
            today = now.date()

            if (
                now.hour == SEND_HOUR_UTC
                and now.minute == SEND_MINUTE_UTC
                and last_fired_date != today
            ):
                logger.info(f"Firing newsletter for {today}")
                result = fire_newsletter(force=False)
                last_fired_date = today
                if result.get("success"):
                    logger.info(
                        f"Newsletter sent — {result.get('recipient_count', 0)} recipients"
                    )
                elif result.get("skipped"):
                    logger.info("Newsletter skipped (already sent today)")
                else:
                    logger.error(f"Newsletter failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Cron loop error: {e}")

        time.sleep(30)  # Check every 30 seconds


def main():
    args = sys.argv[1:]

    if "--now" in args:
        force = "--force" in args
        logger.info(f"Sending newsletter immediately (force={force})")
        result = fire_newsletter(force=force)
        print(result)
        sys.exit(0 if result.get("success") or result.get("skipped") else 1)

    if "--test" in args:
        idx = args.index("--test")
        if idx + 1 >= len(args):
            print("Usage: newsletter_cron.py --test <email>")
            sys.exit(1)
        to_email = args[idx + 1]
        logger.info(f"Sending test newsletter to {to_email}")
        result = fire_test(to_email)
        print(result)
        sys.exit(0 if result.get("success") else 1)

    # Default: run the scheduler loop
    scheduler_loop()


if __name__ == "__main__":
    main()
