"""
Protocol Pulse - Comment Radar Automation
Safe wrapper for master_automation.py integration.
Runs every 3 hours. Respects dry_run/live mode setting.
"""
import logging
import traceback
from datetime import datetime, timezone

log = logging.getLogger("radar_automation")

_last_radar_run = None
RADAR_INTERVAL_HOURS = 3

def should_run_radar():
    global _last_radar_run
    if _last_radar_run is None:
        return True
    elapsed = (datetime.now(timezone.utc) - _last_radar_run).total_seconds() / 3600
    return elapsed >= RADAR_INTERVAL_HOURS

def run_radar_cycle_safe():
    global _last_radar_run
    if not should_run_radar():
        return {"skipped": True, "reason": "interval not elapsed"}
    try:
        from pp_services.comment_radar import CommentRadar
        log.info("[RADAR] Starting Comment Radar cycle...")
        radar = CommentRadar()
        result = radar.run_cycle()
        log.info("[RADAR] Done: %d posts, %d drafts",
                 result.get("processed", 0), result.get("drafts_generated", 0))
        _last_radar_run = datetime.now(timezone.utc)
        return result
    except Exception as e:
        log.error("[RADAR] Cycle failed (non-fatal): %s", e)
        log.error(traceback.format_exc())
        _last_radar_run = datetime.now(timezone.utc)
        return {"processed": 0, "drafts_generated": 0, "error": str(e)}
