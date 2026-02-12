"""
Central scheduler for Protocol Pulse automation tasks.
Defines the 6 Replit-style tasks; run via cron hitting a single endpoint or run_task(name).

Tasks:
- Cypherpunk'd Loop: every 6h — article generation from trending
- Social Guard: every 10min — (optional) social listening / reply checks
- Sarah Daily Brief: 05:45 UTC — prep
- Sarah Intelligence Briefing: 06:00 UTC — generate and publish daily brief
- Sentiment Buffer Update: every 5min — rolling sentiment
- Emergency Flash Check: every 5min — detect 40%+ sentiment drift
"""

import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
_scheduler_started_at: Optional[datetime] = None
_apscheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = Lock()

TASKS = {
    "x_engagement_cycle": {"interval_minutes": 5, "description": "X Engagement Sentry cycle (every 5m)"},
    "mining_snapshot_hourly": {"interval_minutes": 60, "description": "Mining risk snapshot_all (hourly)"},
    "cypherpunk_loop": {"interval_minutes": 360, "description": "Article generation from trending (every 6h)"},
    "social_guard": {"interval_minutes": 10, "description": "Social listening / reply checks"},
    "sarah_brief_prep": {"cron": "05:45", "description": "Sarah daily brief prep (05:45 UTC)"},
    "sarah_intelligence_briefing": {"cron": "06:00", "description": "Sarah daily intelligence briefing (06:00 UTC)"},
    "sentiment_buffer_update": {"interval_minutes": 5, "description": "Rolling sentiment buffer update"},
    "emergency_flash_check": {"interval_minutes": 5, "description": "Emergency flash check (40%+ drift)"},
    "daily_distribution_brief_9am_est": {"cron_est": "09:00", "description": "Sentry auto-poster daily brief dispatch (09:00 EST)"},
    "daily_medley_gpu1": {"cron_est": "09:10", "description": "Daily Beat medley render (GPU 1, 60s)"},
}


def run_task(name: str) -> Dict:
    if name == "x_engagement_cycle":
        try:
            from app import app
            from core.services.x_engagement_sentry import run_cycle
            with app.app_context():
                out = run_cycle()
            return {"success": bool(out.get("success")), "message": "X engagement cycle run", "result": out}
        except Exception as e:
            logger.warning("x_engagement_cycle failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "mining_snapshot_hourly":
        try:
            from app import app
            from services.mining_risk_service import snapshot_all
            with app.app_context():
                out = snapshot_all()
            return {"success": bool(out.get("success")), "message": "Mining snapshot captured", "result": out}
        except Exception as e:
            logger.warning("mining_snapshot_hourly failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    """
    Run a single named task. Returns { success, message, result }.
    """
    if name == "cypherpunk_loop":
        try:
            from services.automation import generate_article_with_tracking
            out = generate_article_with_tracking()
            return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
        except Exception as e:
            logger.exception("cypherpunk_loop failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "social_guard":
        # Optional: social_listener check or reply queue
        return {"success": True, "message": "Social guard (no-op)", "result": None}

    if name == "sarah_brief_prep":
        # Optional: collect signals before brief
        try:
            from services.sentiment_tracker_service import SentimentTrackerService
            t = SentimentTrackerService()
            x = t.fetch_x_posts(hours_back=24)
            n = t.fetch_nostr_notes(hours_back=24)
            s = t.fetch_stacker_news(limit=15)
            t.save_signals_to_db(x + n + s)
            return {"success": True, "message": f"Signals collected: X={len(x)} Nostr={len(n)} Stacker={len(s)}", "result": None}
        except Exception as e:
            logger.warning("sarah_brief_prep: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "sarah_intelligence_briefing":
        try:
            from services.briefing_engine import briefing_engine
            article_id = briefing_engine.generate_daily_brief()
            return {"success": article_id is not None, "message": f"Brief article_id={article_id}", "result": {"article_id": article_id}}
        except Exception as e:
            logger.exception("sarah_intelligence_briefing failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "sentiment_buffer_update":
        try:
            from services.sentiment_service import sentiment_service
            result = sentiment_service.update_buffer()
            return {"success": True, "message": "Buffer updated", "result": result}
        except Exception as e:
            # sentiment_service may not exist yet
            logger.debug("sentiment_buffer_update: %s", e)
            return {"success": True, "message": "Sentiment service not configured", "result": None}

    if name == "emergency_flash_check":
        try:
            from services.briefing_engine import briefing_engine
            flash = briefing_engine.check_emergency_flash()
            return {"success": True, "message": "Flash checked", "result": flash}
        except Exception as e:
            logger.warning("emergency_flash_check: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "daily_distribution_brief_9am_est":
        try:
            from services.distribution_manager import distribution_manager
            result = distribution_manager.dispatch_daily_brief()
            return {"success": bool(result.get("success")), "message": "Daily distribution brief dispatch attempted", "result": result}
        except Exception as e:
            logger.warning("daily_distribution_brief_9am_est: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "daily_medley_gpu1":
        try:
            root = "/home/ultron/protocol_pulse"
            out = f"{root}/logs/medley_daily_beat.mp4"
            prog = f"{root}/logs/medley_daily_beat.progress"
            rep = f"{root}/logs/medley_daily_beat.report.json"
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = "1"
            cmd = [
                f"{root}/venv/bin/python",
                f"{root}/medley_director.py",
                "--output", out,
                "--progress-file", prog,
                "--report-file", rep,
                "--duration", "60",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
            ok = proc.returncode == 0
            return {
                "success": ok,
                "message": "Daily medley render attempted on GPU 1",
                "result": {
                    "returncode": proc.returncode,
                    "output": out,
                    "report": rep,
                    "stderr_tail": (proc.stderr or "")[-300:],
                },
            }
        except Exception as e:
            logger.warning("daily_medley_gpu1: %s", e)
            return {"success": False, "message": str(e), "result": None}

    return {"success": False, "message": f"Unknown task: {name}", "result": None}


def run_all_due() -> List[Dict]:
    """Run all tasks that are 'due' based on interval (simplified: run each once). For cron, prefer calling run_task per schedule."""
    results = []
    for task_name in TASKS:
        try:
            r = run_task(task_name)
            results.append({"task": task_name, **r})
        except Exception as e:
            results.append({"task": task_name, "success": False, "message": str(e), "result": None})
    return results


def initialize_scheduler() -> Dict:
    """
    Compatibility shim for admin command deck.
    We use systemd + endpoint-triggered tasks; this marks scheduler as active.
    """
    global _scheduler_started_at, _apscheduler
    with _scheduler_lock:
        if _apscheduler and _apscheduler.running:
            return {"success": True, "started_at": _scheduler_started_at.isoformat() if _scheduler_started_at else None, "already_running": True}

        _apscheduler = BackgroundScheduler(timezone="UTC")
        _apscheduler.add_job(lambda: run_task("x_engagement_cycle"), trigger=IntervalTrigger(minutes=5), id="x_engagement_cycle", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("mining_snapshot_hourly"), trigger=IntervalTrigger(hours=1), id="mining_snapshot_hourly", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("daily_medley_gpu1"), trigger=CronTrigger(hour=23, minute=0), id="daily_medley_gpu1", replace_existing=True)
        _apscheduler.start()
        _scheduler_started_at = datetime.utcnow()
    return {"success": True, "started_at": _scheduler_started_at.isoformat(), "mode": "apscheduler"}


def get_scheduler_status() -> Dict:
    """Compatibility status payload expected by command deck UI."""
    jobs = [{"name": name, **meta} for name, meta in TASKS.items()]
    return {
        "running": bool(_apscheduler and _apscheduler.running),
        "started_at": _scheduler_started_at.isoformat() if _scheduler_started_at else None,
        "jobs": jobs,
        "mode": "apscheduler+systemd",
    }
