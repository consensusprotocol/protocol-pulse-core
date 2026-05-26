"""
Daily Pulse Check Scheduler
Runs the full Pulse Check pipeline on a schedule and distributes to all platforms.

Usage:
  # Run as standalone scheduler (for Replit "Always On" or background worker)
  python services/video_engine/daily_scheduler.py

  # Or import and start in your main app
  from pp_services.video_engine.daily_scheduler import start_scheduler
  start_scheduler()

  # Or set up as cron on Ultron:
  # crontab -e
  # 0 14 * * * cd /path/to/project && python -m services.video_engine.daily_scheduler --once
"""

import os
import sys
import json
import logging
import signal
import time
from datetime import datetime, timedelta
from threading import Thread, Event

logger = logging.getLogger(__name__)

# ── Schedule Config ───────────────────────────────────────────────
SCHEDULE_HOUR = int(os.environ.get("PULSE_SCHEDULE_HOUR", "14"))
SCHEDULE_MINUTE = int(os.environ.get("PULSE_SCHEDULE_MINUTE", "0"))
SCHEDULE_TIMEZONE = os.environ.get("PULSE_SCHEDULE_TZ", "US/Eastern")

MAX_RETRIES = 2
RETRY_DELAY_MINUTES = 15
RESULTS_LOG_FILE = "data/video_engine/pulse_check_log.json"


class PulseScheduler:
    """Manages scheduled execution of the Pulse Check pipeline."""

    def __init__(self):
        self._stop_event = Event()
        self._thread = None
        self._last_run_date = None

    def run_once(self) -> dict:
        """Execute the pipeline once, right now."""
        from pp_services.video_engine.pulse_check_ultron import run_and_distribute

        date_str = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"═══ Pulse Check triggered for {date_str} ═══")

        result = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                result = run_and_distribute(date_str)
                if result.get("success"):
                    logger.info("✓ Pipeline completed successfully")
                    self._log_result(result)
                    return result
                else:
                    logger.warning(
                        f"Pipeline returned errors (attempt {attempt + 1}): "
                        f"{result.get('errors', [])}"
                    )
            except Exception as e:
                logger.error(
                    f"Pipeline exception (attempt {attempt + 1}/{MAX_RETRIES + 1}): {e}"
                )

            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY_MINUTES} minutes...")
                time.sleep(RETRY_DELAY_MINUTES * 60)

        if result:
            self._log_result(result)
        return result or {"success": False, "error": "All retries exhausted"}

    def start(self):
        """Start the scheduler in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler already running")
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info(
            f"Pulse Check scheduler started - "
            f"runs daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} "
            f"{SCHEDULE_TIMEZONE}"
        )

    def stop(self):
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Scheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            try:
                now = self._get_local_time()
                today = now.strftime("%Y-%m-%d")
                if (
                    now.hour == SCHEDULE_HOUR
                    and now.minute == SCHEDULE_MINUTE
                    and self._last_run_date != today
                ):
                    logger.info("Scheduled run triggered")
                    self._last_run_date = today
                    self.run_once()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            self._stop_event.wait(60)

    def _get_local_time(self) -> datetime:
        """Get current time in configured timezone."""
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(SCHEDULE_TIMEZONE))
        except ImportError:
            try:
                import pytz
                tz = pytz.timezone(SCHEDULE_TIMEZONE)
                return datetime.now(tz)
            except ImportError:
                return datetime.utcnow() - timedelta(hours=5)

    def _log_result(self, result: dict):
        """Append result to log file."""
        try:
            os.makedirs(os.path.dirname(RESULTS_LOG_FILE), exist_ok=True)
            log = []
            if os.path.exists(RESULTS_LOG_FILE):
                with open(RESULTS_LOG_FILE, "r") as f:
                    log = json.load(f)
            result["logged_at"] = datetime.now().isoformat()
            log.append(result)
            log = log[-90:]
            with open(RESULTS_LOG_FILE, "w") as f:
                json.dump(log, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to log result: {e}")

    def get_history(self, days: int = 7) -> list[dict]:
        """Get pipeline run history."""
        try:
            if not os.path.exists(RESULTS_LOG_FILE):
                return []
            with open(RESULTS_LOG_FILE, "r") as f:
                log = json.load(f)
            return log[-days:]
        except Exception:
            return []


_scheduler = None

def start_scheduler() -> PulseScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = PulseScheduler()
    _scheduler.start()
    return _scheduler

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.stop()

def run_now() -> dict:
    scheduler = PulseScheduler()
    return scheduler.run_once()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if "--once" in sys.argv:
        result = run_now()
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result.get("success") else 1)

    elif "--history" in sys.argv:
        scheduler = PulseScheduler()
        history = scheduler.get_history(30)
        for entry in history:
            status = "✓" if entry.get("success") else "✗"
            date = entry.get("date", "?")
            clips = len(entry.get("clips", []))
            print(f"  {status} {date} - {clips} clips")

    else:
        print(f"Starting Pulse Check scheduler...")
        print(f"  Schedule: daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} {SCHEDULE_TIMEZONE}")
        print(f"  Press Ctrl+C to stop")
        print()

        scheduler = start_scheduler()

        def signal_handler(sig, frame):
            print("\nShutting down...")
            stop_scheduler()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_scheduler()
