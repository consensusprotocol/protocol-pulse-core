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
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

TASKS = {
    "cypherpunk_loop": {"interval_minutes": 360, "description": "Article generation from trending (every 6h)"},
    "social_guard": {"interval_minutes": 10, "description": "Social listening / reply checks"},
    "sarah_brief_prep": {"cron": "05:45", "description": "Sarah daily brief prep (05:45 UTC)"},
    "sarah_intelligence_briefing": {"cron": "06:00", "description": "Sarah daily intelligence briefing (06:00 UTC)"},
    "sentiment_buffer_update": {"interval_minutes": 5, "description": "Rolling sentiment buffer update"},
    "emergency_flash_check": {"interval_minutes": 5, "description": "Emergency flash check (40%+ drift)"},
    "x_spaces_sentiment_update": {"interval_minutes": 5, "description": "X Spaces sentiment stream update"},
    # Market Briefing Room — HeyGen Sarah 3x/day (06:45, 09:15, 16:15 ET)
    "briefing_pre_market": {"cron": "11:45", "description": "Pre-market briefing (06:45 ET / 11:45 UTC)"},
    "briefing_open":       {"cron": "14:15", "description": "Market-open briefing (09:15 ET / 14:15 UTC)"},
    "briefing_close":      {"cron": "21:15", "description": "Market-close briefing (16:15 ET / 21:15 UTC)"},
    # ── 3x Daily Pulse Check Renders (GPU 0 — render_lane) ──
    "pulse_render_morning": {"cron_est": "03:00", "description": "Pulse Check Episode 1 render (3:00 AM ET → publish 7 AM ET)"},
    "pulse_render_midday": {"cron_est": "08:30", "description": "Pulse Check Episode 2 render (8:30 AM ET → publish 12 PM ET)"},
    "pulse_render_afternoon": {"cron_est": "14:00", "description": "Pulse Check Episode 3 render (2:00 PM ET → publish 6 PM ET)"},
    "gpu_health_monitor": {"interval_minutes": 5, "description": "GPU health: temp, VRAM, deadlock detection, queue processing"},
}


def run_task(name: str) -> Dict:
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
        # X Engagement Sentry — run Sovereign Sentry cycle (tweet ingest + draft generation)
        try:
            from services import x_engagement_sentry

            result = x_engagement_sentry.run_cycle()
            return {
                "success": True,
                "message": f"X Sentry cycle: ingested={result.get('ingested', 0)} drafts={result.get('drafts', 0)}",
                "result": result,
            }
        except Exception as e:
            logger.warning("social_guard / X Sentry failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

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

    # Market Briefing Room — trigger HeyGen Sarah generation
    if name in ("briefing_pre_market", "briefing_open", "briefing_close"):
        slot_map = {
            "briefing_pre_market": "pre_market",
            "briefing_open":       "open",
            "briefing_close":      "close",
        }
        briefing_type = slot_map[name]
        try:
            from services.briefing_scheduler import trigger_briefing
            result = trigger_briefing(briefing_type)
            msg = (
                f"Briefing {briefing_type} id={result.get('briefing_id')} "
                f"duration={result.get('duration_seconds')}s"
                if result.get("success")
                else f"Briefing {briefing_type} failed: {result.get('error')}"
            )
            return {"success": result.get("success", False), "message": msg, "result": result}
        except Exception as e:
            logger.error("briefing task %s failed: %s", name, e)
            return {"success": False, "message": str(e), "result": None}

    if name == "tradfi_monitor":
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'video_pipeline_v3'))
            from utils.tradfi_monitor import run as tradfi_run
            tradfi_run()
        except Exception as e:
            logger.debug("tradfi_monitor: %s", e)
    if name == "x_spaces_sentiment_update":
        try:
            from services.spaces_sentiment_service import spaces_sentiment_service
            result = spaces_sentiment_service.run()
            logger.info("x_spaces_sentiment: score=%s active=%s", result.get('score'), result.get('active_count'))
            return {"success": True, "message": f"X Spaces sentiment: {result.get('score')} ({result.get('label')})", "result": result}
        except Exception as e:
            logger.warning("x_spaces_sentiment_update: %s", e)
            return {"success": False, "message": str(e), "result": None}

    # ── 3x Daily Pulse Check Renders (GPU 0 — render_lane) ──────────────────
    if name in ("pulse_render_morning", "pulse_render_midday", "pulse_render_afternoon"):
        try:
            from services.gpu_scheduler import get_scheduler
            sched = get_scheduler()
            episode_label = {
                "pulse_render_morning": "morning",
                "pulse_render_midday": "midday",
                "pulse_render_afternoon": "afternoon",
            }[name]
            episode_name = f"pulse_check_{episode_label}_{datetime.utcnow().strftime('%Y%m%d')}"
            result = sched.request_render(episode_name)
            return {"success": True, "message": f"Render {result['status']}: {episode_name}", "result": result}
        except Exception as e:
            logger.error("pulse_render %s failed: %s", name, e)
            return {"success": False, "message": str(e), "result": None}

    if name == "gpu_health_monitor":
        try:
            from services.gpu_scheduler import get_scheduler
            sched = get_scheduler()
            health = sched.status()
            alerts = health.get("health", {}).get("alerts", [])
            sched.process_queue()
            return {"success": True, "message": f"GPU health OK, {len(alerts)} alerts", "result": health}
        except Exception as e:
            logger.warning("gpu_health_monitor failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    return {"success": False, "message": f"Unknown task: {name}", "result": None}


def initialize_scheduler() -> Dict:
    """Start APScheduler with all GPU render + health tasks."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        return {"success": False, "error": "apscheduler not installed"}

    _et = "America/New_York"
    sched = BackgroundScheduler(timezone="UTC")
    # 3x daily renders
    sched.add_job(lambda: run_task("pulse_render_morning"), trigger=CronTrigger(hour=3, minute=0, timezone=_et), id="pulse_render_morning", replace_existing=True, max_instances=1, misfire_grace_time=1800)
    sched.add_job(lambda: run_task("pulse_render_midday"), trigger=CronTrigger(hour=8, minute=30, timezone=_et), id="pulse_render_midday", replace_existing=True, max_instances=1, misfire_grace_time=1800)
    sched.add_job(lambda: run_task("pulse_render_afternoon"), trigger=CronTrigger(hour=14, minute=0, timezone=_et), id="pulse_render_afternoon", replace_existing=True, max_instances=1, misfire_grace_time=1800)
    # GPU health every 5 min
    sched.add_job(lambda: run_task("gpu_health_monitor"), trigger=IntervalTrigger(minutes=5), id="gpu_health_monitor", replace_existing=True, max_instances=1)
    sched.start()
    # Start GPU health monitor thread
    try:
        from services.gpu_scheduler import get_scheduler as _get_gpu_sched
        _get_gpu_sched().start_health_monitor()
    except Exception:
        pass
    return {"success": True, "started_at": datetime.utcnow().isoformat(), "mode": "apscheduler"}


def get_scheduler_status() -> Dict:
    """Return scheduler status with GPU info."""
    try:
        from services.gpu_scheduler import get_scheduler
        gpu_status = get_scheduler().status()
    except Exception:
        gpu_status = {}
    jobs = [{"name": name, **meta} for name, meta in TASKS.items()]
    return {
        "running": True,
        "tasks": jobs,
        "task_count": len(jobs),
        "gpu": gpu_status,
    }


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
