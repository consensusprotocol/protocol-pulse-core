"""
PULSE CHECK SCHEDULER
======================
Daily automation for the intelligence pipeline.
Runs at configurable time (default 10 AM Eastern).

Uses APScheduler for reliable scheduling with:
- Cron-based triggers
- Misfire handling
- Crash recovery
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from services.video_engine.intelligence_pipeline import IntelligencePipeline
from services.video_engine.pulse_distributor import distribute_pulse
from services.video_engine.intel_feed_consumer import consume_intel_feeds
from services.video_engine.pipeline_alerts import (
    send_pipeline_complete, send_pipeline_error, send_ultron_offline
)
from services.video_engine.ultron_client import ultron

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger("PulseScheduler")

# Configuration
RUN_HOUR = int(os.environ.get("PULSE_RUN_HOUR", "10"))
RUN_MINUTE = int(os.environ.get("PULSE_RUN_MINUTE", "0"))
RUN_TZ = os.environ.get("PULSE_RUN_TZ", "America/New_York")
ENABLE_SCHEDULER = os.environ.get("ENABLE_PULSE_SCHEDULER", "false").lower() in ("true", "1", "yes")

LOG_DIR = Path("data/video_engine/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

scheduler = BackgroundScheduler()


def run_daily_pipeline():
    """Execute the full daily pipeline: scan -> analyze -> select -> produce -> distribute."""
    today = datetime.now(pytz.timezone(RUN_TZ)).strftime("%Y-%m-%d")
    logger.info(f"\n{'#'*70}")
    logger.info(f"  SCHEDULED RUN: {today}")
    logger.info(f"  Time: {datetime.now(pytz.timezone(RUN_TZ)).strftime('%I:%M %p %Z')}")
    logger.info(f"{'#'*70}\n")

    run_log = {
        "date": today,
        "started_at": datetime.utcnow().isoformat(),
        "status": "running"
    }

    try:
        # Pre-flight: check Ultron
        health = ultron.health_check()
        if health.get("status") != "ok":
            logger.error(f"Ultron offline, aborting scheduled run")
            run_log["status"] = "aborted"
            run_log["error"] = "Ultron offline"
            _save_run_log(today, run_log)
            send_ultron_offline(today)
            return

        # Run the intelligence pipeline
        pipeline = IntelligencePipeline()
        result = pipeline.run()

        run_log["pipeline_result"] = result

        if result.get("status") == "complete":
            # Distribute
            logger.info("\n  Starting distribution...")
            dist_result = distribute_pulse(
                pipeline.run_id,
                pipeline.today,
                result.get("video", {}),
                result.get("intel", {})
            )
            run_log["distribution"] = dist_result

            # Feed downstream systems (articles, tweets, newsletter)
            logger.info("\n  Consuming intel feeds...")
            try:
                feed_result = consume_intel_feeds(pipeline.today)
                run_log["intel_feeds"] = feed_result
                articles_count = feed_result.get("articles", {}).get("count", 0)
                tweets_count = feed_result.get("tweets", {}).get("count", 0)
                logger.info(f"  Intel feeds: {articles_count} articles, {tweets_count} tweets")
            except Exception as e:
                logger.error(f"  Intel feed consumption failed: {e}")
                run_log["intel_feeds"] = {"error": str(e)}

            run_log["status"] = "complete"

            logger.info(f"\n  Daily pipeline COMPLETE")
            logger.info(f"  Channels: {result.get('channels_scanned', 0)}")
            logger.info(f"  Highlights: {result.get('videos_analyzed', 0)}")
            logger.info(f"  Clips: {result.get('clips_selected', 0)}")

            # Send success alert
            send_pipeline_complete(result, run_log)
        else:
            run_log["status"] = "pipeline_error"
            run_log["error"] = result.get("error", "Unknown pipeline error")
            logger.error(f"  Pipeline failed: {result.get('error')}")
            send_pipeline_error(result.get("error", "Unknown"), stage="pipeline", date=today)

        # Cleanup old files on Ultron (keep 3 days)
        ultron.cleanup(days=3)
        logger.info("  Ultron cleanup done")

    except Exception as e:
        logger.error(f"  Scheduled run failed: {e}", exc_info=True)
        run_log["status"] = "error"
        run_log["error"] = str(e)
        send_pipeline_error(str(e), stage="scheduler", date=today)

    run_log["completed_at"] = datetime.utcnow().isoformat()
    _save_run_log(today, run_log)


def _save_run_log(date: str, log_data: dict):
    """Save run log to disk for audit trail."""
    log_path = LOG_DIR / f"scheduled_run_{date}.json"
    log_path.write_text(json.dumps(log_data, indent=2, default=str))
    logger.info(f"  Run log saved: {log_path}")


def start_scheduler():
    """Start the APScheduler with the daily pipeline job."""
    if not ENABLE_SCHEDULER:
        logger.info("Pulse scheduler disabled (ENABLE_PULSE_SCHEDULER != true)")
        return None

    tz = pytz.timezone(RUN_TZ)

    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=RUN_HOUR, minute=RUN_MINUTE, timezone=tz),
        id="pulse_daily_pipeline",
        name=f"Pulse Check Daily Pipeline ({RUN_HOUR}:{RUN_MINUTE:02d} {RUN_TZ})",
        replace_existing=True,
        misfire_grace_time=3600  # Allow up to 1 hour late
    )

    # Register Pulse Alert scanner (every 30 minutes)
    try:
        from services.video_engine.pulse_alert import PulseAlertScheduler
        alert_scheduler = PulseAlertScheduler()
        alert_scheduler.register_with_scheduler(scheduler)
    except Exception as e:
        logger.warning(f"Pulse Alert registration failed: {e}")

    scheduler.start()
    logger.info(f"Scheduler started: daily pipeline at {RUN_HOUR}:{RUN_MINUTE:02d} {RUN_TZ}")
    return scheduler


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_next_run_time() -> str:
    """Get the next scheduled run time."""
    jobs = scheduler.get_jobs()
    for job in jobs:
        if job.id == "pulse_daily_pipeline":
            return str(job.next_run_time)
    return "Not scheduled"


def trigger_manual_run():
    """Manually trigger a pipeline run (outside of schedule)."""
    logger.info("Manual run triggered")
    run_daily_pipeline()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # Run immediately
        logger.info("Running pipeline immediately (manual trigger)")
        run_daily_pipeline()
    else:
        # Start scheduler
        logger.info("Starting Pulse Check Scheduler...")
        start_scheduler()

        try:
            import time
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            stop_scheduler()
