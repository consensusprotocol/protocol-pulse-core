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

import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from threading import Lock

logger = logging.getLogger(__name__)
_scheduler_started_at: Optional[datetime] = None
_apscheduler = None  # BackgroundScheduler, set in initialize_scheduler
_scheduler_lock = Lock()

# When False (default), Queued SentryJob posts are only written to data/pulseevents.jsonl with [DRY-RUN]. No live posting.
ENABLE_LIVE_POSTING = os.environ.get("ENABLE_LIVE_POSTING", "false").strip().lower() in {"1", "true", "yes", "on"}

# New article draft schedule: burst 4 every 15 min (UTC 00–07), break (08–11), then 1/hour (12–23). Only active when set.
ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE = os.environ.get("ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE", "false").strip().lower() in {"1", "true", "yes", "on"}

# Replit-style: generate one breaking_news article every 15 minutes (with DB lock).
# Keep OFF until explicitly enabled.
ENABLE_ARTICLE_AUTOMATION_15M = os.environ.get("ENABLE_ARTICLE_AUTOMATION_15M", "false").strip().lower() in {"1", "true", "yes", "on"}

# UTC hour windows: burst = 0–7, break = 8–11, slow = 12–23
ARTICLE_DRAFT_BURST_HOURS = set(range(0, 8))   # 00:00–07:59 UTC
ARTICLE_DRAFT_SLOW_HOURS = set(range(12, 24)) # 12:00–23:59 UTC

TASKS = {
    "x_engagement_cycle": {"interval_minutes": 5, "description": "X Engagement Sentry cycle (every 5m)"},
    "sentry_megaphone": {"interval_minutes": 2, "description": "SentryJob Queued -> pulseevents.jsonl [DRY-RUN] (no live post when ENABLE_LIVE_POSTING=False)"},
    "mining_snapshot_hourly": {"interval_minutes": 60, "description": "Mining risk snapshot_all (hourly)"},
    "cypherpunk_loop": {"interval_minutes": 120, "description": "Article auto-draft from trending (every 2h, around the clock)"},
    "social_guard": {"interval_minutes": 10, "description": "Social listening / reply checks"},
    "sarah_brief_prep": {"cron": "05:45", "description": "Sarah daily brief prep (05:45 UTC)"},
    "sarah_intelligence_briefing": {"cron": "06:00", "description": "Sarah daily intelligence briefing (06:00 UTC)"},
    "sentiment_buffer_update": {"interval_minutes": 5, "description": "Rolling sentiment buffer update"},
    "emergency_flash_check": {"interval_minutes": 5, "description": "Emergency flash check (40%+ drift)"},
    "daily_distribution_brief_9am_est": {"cron_est": "09:00", "description": "Sentry auto-poster daily brief dispatch (09:00 EST)"},
    "daily_medley_gpu1": {"cron_est": "09:10", "description": "Daily Beat medley render (GPU 1, 60s)"},
    "monetization_injector": {"interval_minutes": 30, "description": "Smart-link injector scan for briefs + x drafts"},
    "pulse_drop_rebuild_5am": {"cron_est": "05:00", "description": "Pulse Drop daily rebuild (05:00 EST)"},
    "auto_viral_reel": {"interval_minutes": 30, "description": "Viral reel: monitor → clip → narration → publish (X/Telegram if ENABLE_LIVE_POSTING)"},
    "intel_medley": {"interval_minutes": 60, "description": "Automated Intel Medley: monitor UC9ZM3N0ybRtp44 + partners, 3-5 clips, 5-10 min briefing, outro + CTAs"},
    "article_draft_burst_4": {"interval_minutes": 15, "description": "Article draft burst: 4 articles every 15 min (UTC 00–07 only, when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE)"},
    "article_draft_hourly_1": {"interval_minutes": 60, "description": "Article draft slow: 1 article per hour (UTC 12–23 only, when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE)"},
    "article_generation_15m": {"interval_minutes": 15, "description": "Replit-style: generate 1 breaking_news article every 15 minutes (when ENABLE_ARTICLE_AUTOMATION_15M)"},
}


def _send_alert_email(subject: str, body: str) -> bool:
    """Send alert email on failure. Uses SENDGRID_API_KEY and CONTACT_EMAIL or VIRAL_ALERT_EMAIL."""
    to = os.environ.get("VIRAL_ALERT_EMAIL") or os.environ.get("CONTACT_EMAIL") or os.environ.get("SENDGRID_FROM_EMAIL")
    if not to:
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
    except ImportError:
        return False
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        return False
    from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@protocolpulse.io")
    message = Mail(
        from_email=Email(from_email, "Protocol Pulse"),
        to_emails=To(to),
        subject=subject[:200],
        plain_text_content=Content("text/plain", body[:10000]),
    )
    try:
        SendGridAPIClient(api_key).send(message)
        return True
    except Exception as e:
        logger.warning("Alert email failed: %s", e)
        return False


def auto_viral_reel() -> Dict:
    """
    Batch 5: monitor → clip → narration → publish.
    Runs every 30m. If ENABLE_LIVE_POSTING, publishes to X and Telegram.
    On failure sends alert email.
    """
    try:
        from app import app
        import models
        from services.viralmoments import ViralMomentsReelEngine
        from pathlib import Path

        engine = ViralMomentsReelEngine()
        with app.app_context():
            # 1) Monitor partners (create ClipJobs for new videos)
            mon = engine.monitor_partners()
            job_ids = mon.get("job_ids") or []
            # 2) Pick one Planned job and render reel (or use latest Completed for publish-only)
            job = (
                models.ClipJob.query.filter(models.ClipJob.status == "Planned")
                .order_by(models.ClipJob.id.asc())
                .first()
            )
            if not job:
                return {
                    "success": True,
                    "message": "auto_viral_reel: no Planned job; monitor only",
                    "result": {"monitor": mon, "published": False},
                }
            # 3) Render reel (includes optional voiceover if VIRAL_ADD_VOICEOVER=1)
            render = engine.render_reel(job)
            if not render.get("ok"):
                _send_alert_email(
                    "[Protocol Pulse] auto_viral_reel render failed",
                    f"job_id={job.id} video_id={job.video_id}\nerror={render.get('error', 'unknown')}",
                )
                return {
                    "success": False,
                    "message": render.get("error", "render failed"),
                    "result": {"render": render},
                }
            out_path = render.get("output_path")
            base_url = os.environ.get("BASE_URL", "https://protocolpulse.io").rstrip("/")
            reel_url = f"{base_url}/static/clips/reels/{Path(out_path or '').name}" if out_path else None
            if not reel_url and out_path:
                reel_url = f"{base_url}/{out_path}" if not out_path.startswith("http") else out_path

            published_x = False
            published_tg = False
            if ENABLE_LIVE_POSTING and reel_url:
                # 4a) Publish to X (tweet with link)
                try:
                    from services.x_service import XService
                    x = XService()
                    if x.client or getattr(x, "client_v2", None):
                        text = f"New Intel Briefing reel — {job.channel_name or 'Partner'} | {reel_url}"
                        if len(text) > 280:
                            text = f"Intel Briefing | {job.channel_name or 'Partner'} {reel_url}"
                        if x.client:
                            x.client.update_status(text[:280])
                            published_x = True
                        elif getattr(x, "client_v2", None) and x.client_v2:
                            x.client_v2.create_tweet(text=text[:280])
                            published_x = True
                except Exception as ex:
                    logger.warning("auto_viral_reel X post failed: %s", ex)
                    _send_alert_email("[Protocol Pulse] auto_viral_reel X post failed", str(ex))
                # 4b) Publish to Telegram (message with link)
                try:
                    token = os.environ.get("TELEGRAM_BOT_TOKEN")
                    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
                    if token and chat_id:
                        import requests
                        msg = f"Intel Briefing reel — {job.channel_name or 'Partner'}\n{reel_url}"
                        r = requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={"chat_id": chat_id, "text": msg},
                            timeout=10,
                        )
                        published_tg = r.status_code == 200
                except Exception as ex:
                    logger.warning("auto_viral_reel Telegram post failed: %s", ex)
                    _send_alert_email("[Protocol Pulse] auto_viral_reel Telegram failed", str(ex))

            return {
                "success": True,
                "message": "auto_viral_reel: reel rendered" + (" and published" if (published_x or published_tg) else ""),
                "result": {
                    "job_id": job.id,
                    "reel_url": reel_url,
                    "published_x": published_x,
                    "published_tg": published_tg,
                    "monitor": mon,
                },
            }
    except Exception as e:
        logger.exception("auto_viral_reel failed: %s", e)
        _send_alert_email(
            "[Protocol Pulse] auto_viral_reel failed",
            f"auto_viral_reel error:\n{type(e).__name__}: {e}",
        )
        return {"success": False, "message": str(e), "result": None}


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

    if name == "sentry_megaphone":
        try:
            from app import app
            from pathlib import Path
            with app.app_context():
                import models
                jobs = models.SentryJob.query.filter_by(status="Queued").limit(50).all()
                log_path = Path(app.root_path) / "data" / "pulseevents.jsonl"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                for job in jobs:
                    line = json.dumps({
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "tag": "DRY-RUN",
                        "message": f"[DRY-RUN] SentryJob id={job.id} platform={job.platform}",
                        "sentry_job_id": job.id,
                        "platform": job.platform,
                        "content_preview": (job.content or "")[:200],
                    }) + "\n"
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(line)
                    job.status = "Written"
                    written += 1
                if written:
                    from app import db
                    db.session.commit()
            return {"success": True, "message": f"Sentry megaphone: {written} queued posts written to pulseevents.jsonl", "result": {"written": written, "live_posting": ENABLE_LIVE_POSTING}}
        except Exception as e:
            logger.warning("sentry_megaphone failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    """
    Run a single named task. Returns { success, message, result }.
    """
    if name == "cypherpunk_loop":
        if ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
            return {"success": True, "message": "cypherpunk_loop disabled when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE is on", "result": None}
        try:
            from services.automation import generate_article_with_tracking
            out = generate_article_with_tracking()
            return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
        except Exception as e:
            logger.exception("cypherpunk_loop failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "article_draft_burst_4":
        if not ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
            return {"success": True, "message": "article_draft_burst_4 skipped (new schedule disabled)", "result": None}
        hour_utc = datetime.utcnow().hour
        if hour_utc not in ARTICLE_DRAFT_BURST_HOURS:
            return {"success": True, "message": f"article_draft_burst_4 outside burst window (UTC hour {hour_utc})", "result": None}
        try:
            from services.automation import generate_article_with_tracking
            results = []
            for _ in range(4):
                out = generate_article_with_tracking(force=True)
                results.append(out)
            ok = any(r.get("success") for r in results)
            return {"success": ok, "message": f"Burst 4: {sum(1 for r in results if r.get('success'))}/4", "result": results}
        except Exception as e:
            logger.exception("article_draft_burst_4 failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "article_draft_hourly_1":
        if not ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
            return {"success": True, "message": "article_draft_hourly_1 skipped (new schedule disabled)", "result": None}
        hour_utc = datetime.utcnow().hour
        if hour_utc not in ARTICLE_DRAFT_SLOW_HOURS:
            return {"success": True, "message": f"article_draft_hourly_1 outside slow window (UTC hour {hour_utc})", "result": None}
        try:
            from services.automation import generate_article_with_tracking
            out = generate_article_with_tracking(force=True)
            return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
        except Exception as e:
            logger.exception("article_draft_hourly_1 failed: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "article_generation_15m":
        if not ENABLE_ARTICLE_AUTOMATION_15M:
            return {"success": True, "message": "article_generation_15m skipped (disabled)", "result": None}
        try:
            from services.automation import generate_breaking_article_with_tracking
            out = generate_breaking_article_with_tracking()
            return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
        except Exception as e:
            logger.exception("article_generation_15m failed: %s", e)
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

    if name == "monetization_injector":
        try:
            from app import app
            from services.monetization_engine import monetization_engine
            with app.app_context():
                report = monetization_engine.run()
            return {"success": True, "message": "Monetization injector scan complete", "result": report}
        except Exception as e:
            logger.warning("monetization_injector: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "pulse_drop_rebuild_5am":
        try:
            from app import app
            from services.channel_monitor import channel_monitor_service
            from services.highlight_extractor import highlight_extractor_service
            from services.commentary_generator import commentary_generator_service
            with app.app_context():
                h = channel_monitor_service.run_harvest(hours_back=24)
                x = highlight_extractor_service.run(hours_back=24)
                c = commentary_generator_service.run(hours_back=24)
            return {"success": True, "message": "Pulse Drop rebuild complete", "result": {"harvest": h, "extract": x, "commentary": c}}
        except Exception as e:
            logger.warning("pulse_drop_rebuild_5am: %s", e)
            return {"success": False, "message": str(e), "result": None}

    if name == "auto_viral_reel":
        return auto_viral_reel()

    if name == "intel_medley":
        return auto_viral_reel()

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
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    with _scheduler_lock:
        if _apscheduler and _apscheduler.running:
            return {"success": True, "started_at": _scheduler_started_at.isoformat() if _scheduler_started_at else None, "already_running": True}

        _apscheduler = BackgroundScheduler(timezone="UTC")
        _apscheduler.add_job(lambda: run_task("x_engagement_cycle"), trigger=IntervalTrigger(minutes=5), id="x_engagement_cycle", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("sentry_megaphone"), trigger=IntervalTrigger(minutes=2), id="sentry_megaphone", replace_existing=True)
        if ENABLE_ARTICLE_AUTOMATION_15M:
            _apscheduler.add_job(
                lambda: run_task("article_generation_15m"),
                trigger=IntervalTrigger(minutes=15),
                id="article_generation_15m",
                replace_existing=True,
                max_instances=1,
            )
        if ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
            _apscheduler.add_job(lambda: run_task("article_draft_burst_4"), trigger=IntervalTrigger(minutes=15), id="article_draft_burst_4", replace_existing=True)
            _apscheduler.add_job(lambda: run_task("article_draft_hourly_1"), trigger=IntervalTrigger(minutes=60), id="article_draft_hourly_1", replace_existing=True)
        else:
            _apscheduler.add_job(lambda: run_task("cypherpunk_loop"), trigger=IntervalTrigger(minutes=120), id="cypherpunk_loop", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("mining_snapshot_hourly"), trigger=IntervalTrigger(hours=1), id="mining_snapshot_hourly", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("daily_medley_gpu1"), trigger=CronTrigger(hour=23, minute=0), id="daily_medley_gpu1", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("monetization_injector"), trigger=IntervalTrigger(minutes=30), id="monetization_injector", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("pulse_drop_rebuild_5am"), trigger=CronTrigger(hour=10, minute=0), id="pulse_drop_rebuild_5am", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("auto_viral_reel"), trigger=IntervalTrigger(minutes=30), id="auto_viral_reel", replace_existing=True)
        _apscheduler.add_job(lambda: run_task("intel_medley"), trigger=IntervalTrigger(minutes=60), id="intel_medley", replace_existing=True)
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
