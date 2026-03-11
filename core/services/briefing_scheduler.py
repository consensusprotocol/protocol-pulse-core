"""
Market Briefing Room — Briefing Scheduler

Generates HeyGen Sarah briefings 3x/day at scheduled ET times.

Schedule:
  Pre-Market : 06:45 ET  (11:45 UTC standard / 10:45 UTC DST)
  Market Open: 09:15 ET  (14:15 UTC standard / 13:15 UTC DST)
  Market Close: 16:15 ET (21:15 UTC standard / 20:15 UTC DST)

Avatar : d259c335741f4fc0b061e04c59388b4e  (Sarah — Photo Avatar III)
Voice  : 5f745b3db0db43739f31499f4f0aedd6  (Claire Lawson — Broadcaster)
Cost   : ~$1/min — 2 min cap per briefing = $2/briefing = $6/day max
LAW    : 3 briefings/day MAXIMUM — enforced by briefing_service cost guard.
LAW    : Never retry HeyGen more than 2x on failure (enforced in briefing_service).

Usage:
  python3 -m services.briefing_scheduler --type pre_market
  python3 -m services.briefing_scheduler --type open
  python3 -m services.briefing_scheduler --type close

Cron (add to crontab):
  45  6  * * 1-5  cd /home/ultron/protocol_pulse && python3 -m core.services.briefing_scheduler --type pre_market >> logs/briefing_scheduler.log 2>&1
  15  9  * * 1-5  cd /home/ultron/protocol_pulse && python3 -m core.services.briefing_scheduler --type open >> logs/briefing_scheduler.log 2>&1
  15 16  * * 1-5  cd /home/ultron/protocol_pulse && python3 -m core.services.briefing_scheduler --type close >> logs/briefing_scheduler.log 2>&1
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# Ensure project root is on the path so 'import models' and 'from app import app' resolve.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load .env from project root (harmless if already loaded)
try:
    from dotenv import load_dotenv
    _env_file = os.path.join(_project_root, ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [briefing_scheduler] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SARAH_AVATAR_ID = "d259c335741f4fc0b061e04c59388b4e"
SARAH_VOICE_ID  = "5f745b3db0db43739f31499f4f0aedd6"   # Claire Lawson — Broadcaster
MAX_BRIEFINGS_PER_DAY = 3

VALID_TYPES = ("pre_market", "open", "close")

SCHEDULE_ET = {
    "pre_market": "06:45 ET",
    "open":       "09:15 ET",
    "close":      "16:15 ET",
}


# ---------------------------------------------------------------------------
# Core trigger
# ---------------------------------------------------------------------------

def trigger_briefing(briefing_type: str) -> dict:
    """
    Trigger a single briefing generation.

    Returns:
        dict with keys: success (bool), briefing_id (int|None), error (str|None)
    """
    if briefing_type not in VALID_TYPES:
        msg = f"Invalid briefing_type '{briefing_type}'. Must be one of: {VALID_TYPES}"
        logger.error(msg)
        return {"success": False, "briefing_id": None, "error": msg}

    logger.info(
        "Triggering %s briefing (%s) — Sarah avatar %s",
        briefing_type, SCHEDULE_ET[briefing_type], SARAH_AVATAR_ID[:8],
    )

    try:
        from services.briefing_service import generate_briefing
    except ImportError as exc:
        logger.error("briefing_service import failed: %s", exc)
        return {"success": False, "briefing_id": None, "error": str(exc)}

    result = generate_briefing(briefing_type)

    if result.get("success"):
        logger.info(
            "%s briefing completed — id=%s video=%s duration=%ss",
            briefing_type,
            result.get("briefing_id"),
            (result.get("video_url") or "")[:60],
            result.get("duration_seconds"),
        )
    else:
        logger.warning(
            "%s briefing failed: %s",
            briefing_type,
            result.get("error", "unknown error"),
        )

    return result


# ---------------------------------------------------------------------------
# Daily count guard (informational — actual guard is in briefing_service)
# ---------------------------------------------------------------------------

def briefings_today_count() -> int:
    """Return number of non-failed briefings created today (ET date).
    Informational only — the hard guard is enforced in briefing_service.
    """
    try:
        import pytz
        ET = pytz.timezone("America/New_York")
        today_et = datetime.now(ET).strftime("%Y-%m-%d")
        import models
        from app import app
        with app.app_context():
            count = (
                models.MarketBriefing.query
                .filter(
                    models.MarketBriefing.scheduled_date == today_et,
                    models.MarketBriefing.status != "failed",
                )
                .count()
            )
            return count
    except Exception as exc:
        logger.warning("briefings_today_count check failed: %s", exc)
        return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Market Briefing Room — HeyGen Sarah 3x/day scheduler"
    )
    parser.add_argument(
        "--type",
        choices=list(VALID_TYPES),
        required=True,
        help="Briefing slot to generate",
    )
    args = parser.parse_args()

    # Informational daily count check before firing
    today_count = briefings_today_count()
    logger.info("Briefings generated today (ET): %d / %d max", today_count, MAX_BRIEFINGS_PER_DAY)

    if today_count >= MAX_BRIEFINGS_PER_DAY:
        logger.warning(
            "Cost guard: %d briefings already generated today — skipping %s",
            today_count, args.type,
        )
        sys.exit(0)

    result = trigger_briefing(args.type)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
