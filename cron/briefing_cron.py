#!/usr/bin/env python3
"""
Market Briefing Room — Cron Scheduler (F2)

Fires 3x daily at market-critical times (US/Eastern):
  07:00 ET — Pre-Market Brief (overnight, Asian close)
  09:30 ET — Market Open Brief (what to watch)
  16:30 ET — Market Close Brief (what happened)

Run as:
  python3 cron/briefing_cron.py

Or register as a systemd service using cron/briefing_cron.service.

LAW 2: Do NOT retry more than 2 times on HeyGen failure.
        (retry limit enforced inside briefing_service.py)
"""

import logging
import os
import sys

# Allow importing from parent directory (protocol_pulse root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("briefing_cron")

ET = pytz.timezone("America/New_York")


def run_briefing(briefing_type: str) -> None:
    """Invoke briefing_service.generate_briefing with full error isolation."""
    logger.info("Cron fired: %s briefing", briefing_type)
    try:
        from services.briefing_service import generate_briefing
        result = generate_briefing(briefing_type)
        if result.get("success"):
            logger.info(
                "Briefing %s completed — id=%s video=%s",
                briefing_type,
                result.get("briefing_id"),
                result.get("video_url", "")[:60],
            )
        else:
            logger.error(
                "Briefing %s FAILED — %s", briefing_type, result.get("error")
            )
    except Exception as exc:
        # Cron must NEVER crash the scheduler — catch everything
        logger.exception("Unexpected error in %s briefing: %s", briefing_type, exc)


def main() -> None:
    scheduler = BlockingScheduler(timezone=ET)

    # 07:00 ET — Pre-Market Brief
    # max_instances=1: prevents job stacking if prev run hasn't finished
    # coalesce=True: if multiple fires were missed, execute only once on recovery
    scheduler.add_job(
        func=lambda: run_briefing("pre_market"),
        trigger=CronTrigger(hour=7, minute=0, timezone=ET),
        id="pre_market_brief",
        name="Pre-Market Brief (07:00 ET)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    # 09:30 ET — Market Open Brief
    scheduler.add_job(
        func=lambda: run_briefing("open"),
        trigger=CronTrigger(hour=9, minute=30, timezone=ET),
        id="open_brief",
        name="Market Open Brief (09:30 ET)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    # 16:30 ET — Market Close Brief
    scheduler.add_job(
        func=lambda: run_briefing("close"),
        trigger=CronTrigger(hour=16, minute=30, timezone=ET),
        id="close_brief",
        name="Market Close Brief (16:30 ET)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    logger.info("Briefing cron scheduler started — 3 jobs registered (ET timezone)")
    logger.info("Schedule: 07:00 pre_market | 09:30 open | 16:30 close")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Briefing cron scheduler stopped.")


if __name__ == "__main__":
    main()
