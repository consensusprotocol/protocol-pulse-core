"""
Oracle Scheduler — SESSION 7
Wraps briefing_service.generate_briefing() for 3x daily scheduled runs.

Schedule (ET):
  07:45 → pre_market   (publishes 08:00)
  11:45 → open         (publishes 12:00)
  16:45 → close        (publishes 17:00)

Called from: scheduler.py (registered jobs) or cron
Usage:
  python3 -m core.services.oracle_scheduler --slot pre_market
  python3 -m core.services.oracle_scheduler --slot open
  python3 -m core.services.oracle_scheduler --slot close
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_SLOTS = ("pre_market", "open", "close")


def _load_root_env():
    """Ensure root .env is loaded so HEYGEN/ANTHROPIC keys are available."""
    try:
        from dotenv import load_dotenv
        root_env = Path(__file__).resolve().parent.parent.parent / ".env"
        if root_env.exists():
            load_dotenv(root_env, override=False)
    except ImportError:
        # Manual fallback
        root_env = Path(__file__).resolve().parent.parent.parent / ".env"
        if root_env.exists():
            for line in root_env.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def run_slot(briefing_type: str) -> dict:
    """Generate a single briefing slot. Returns result dict."""
    if briefing_type not in VALID_SLOTS:
        return {"success": False, "error": f"Invalid slot: {briefing_type}"}

    _load_root_env()

    logger.info("Oracle scheduler: triggering %s briefing", briefing_type)

    try:
        from services.briefing_service import generate_briefing
    except ImportError:
        # Try core-relative import
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            from briefing_service import generate_briefing
        except ImportError as exc:
            logger.error("Could not import briefing_service: %s", exc)
            return {"success": False, "error": str(exc)}

    result = generate_briefing(briefing_type)

    if result.get("success"):
        logger.info(
            "Oracle %s completed — briefing_id=%s video=%s",
            briefing_type,
            result.get("briefing_id"),
            result.get("video_url"),
        )
    else:
        logger.error("Oracle %s failed: %s", briefing_type, result.get("error"))

    return result


def schedule_all_slots(scheduler_instance=None):
    """Register oracle briefing jobs with the app scheduler.

    Passes scheduler_instance (APScheduler/custom) if available,
    otherwise logs the schedule for cron configuration.
    """
    slots = [
        ("pre_market", "07:45", "12:45 UTC"),
        ("open",       "11:45", "16:45 UTC"),
        ("close",      "16:45", "21:45 UTC"),
    ]

    if scheduler_instance is None:
        logger.info("Oracle briefing schedule (ET):")
        for slot_type, time_et, time_utc in slots:
            logger.info("  %s at %s ET (%s)", slot_type, time_et, time_utc)
        logger.info(
            "Add to cron: 45 12,16,21 * * * cd /home/ultron/protocol_pulse && "
            "python3 -m core.services.oracle_scheduler --slot <type>"
        )
        return

    for slot_type, time_et, _ in slots:
        h, m = map(int, time_et.split(":"))
        try:
            import pytz
            et = pytz.timezone("America/New_York")
            scheduler_instance.add_job(
                func=run_slot,
                args=[slot_type],
                trigger="cron",
                hour=h,
                minute=m,
                timezone=et,
                id=f"oracle_{slot_type}",
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300,
            )
            logger.info("Registered oracle_%s job at %s ET", slot_type, time_et)
        except Exception as exc:
            logger.warning("Could not register oracle_%s job: %s", slot_type, exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Oracle briefing scheduler")
    parser.add_argument(
        "--slot",
        choices=list(VALID_SLOTS),
        required=True,
        help="Briefing slot to generate",
    )
    args = parser.parse_args()
    result = run_slot(args.slot)
    sys.exit(0 if result.get("success") else 1)
