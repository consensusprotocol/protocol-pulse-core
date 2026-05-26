"""
PULSE CHECK DASHBOARD
======================
Admin dashboard for monitoring the intelligence pipeline.
Shows run history, channel status, highlight scores, and distribution status.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, jsonify, request

from pp_services.config_loader import get_enabled_channels, get_settings, load_channels_config, toggle_channel
from pp_services.video_engine.pipeline_state import (
    get_recent_runs, get_run, get_highlights, get_distributions,
    get_daily_stats, get_completed_channels, get_incomplete_channels
)
from pp_services.video_engine.ultron_client import ultron

logger = logging.getLogger("Dashboard")

dashboard_bp = Blueprint(
    "dashboard", __name__,
    template_folder="templates",
    url_prefix="/dashboard"
)

INTEL_DIR = Path("data/video_engine/intel")
EPISODES_DIR = Path("data/episodes")
EDITORIAL_MEMORY_PATH = Path("state/editorial_memory.json")
LOCK_FILE = Path("state/run.lock")


@dashboard_bp.route("/")
def index():
    """Main dashboard view."""
    runs = get_recent_runs(limit=10)
    channels = get_enabled_channels()
    settings = get_settings()
    today = datetime.now().strftime("%Y-%m-%d")
    stats = get_daily_stats(today)

    return render_template("dashboard.html",
                           runs=runs,
                           channels=channels,
                           settings=settings,
                           today=today,
                           stats=stats)


@dashboard_bp.route("/api/status")
def api_status():
    """Get current pipeline status as JSON."""
    today = datetime.now().strftime("%Y-%m-%d")
    stats = get_daily_stats(today)
    health = ultron.health_check()

    return jsonify({
        "date": today,
        "ultron": health,
        "pipeline": stats,
        "channels_enabled": len(get_enabled_channels())
    })


@dashboard_bp.route("/api/run/<run_id>")
def api_run_detail(run_id):
    """Get detailed run information."""
    run = get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404

    highlights = get_highlights(run_id)
    distributions = get_distributions(run_id)
    completed = get_completed_channels(run_id)
    incomplete = get_incomplete_channels(run_id)

    return jsonify({
        "run": run,
        "highlights": highlights,
        "distributions": distributions,
        "channels_completed": [dict(c) for c in completed],
        "channels_incomplete": [dict(c) for c in incomplete]
    })


@dashboard_bp.route("/api/highlights/<run_id>")
def api_highlights(run_id):
    """Get highlights for a run."""
    min_score = request.args.get("min_score", 0, type=int)
    highlights = get_highlights(run_id, min_score=min_score)
    return jsonify({"highlights": highlights, "count": len(highlights)})


@dashboard_bp.route("/api/intel/<date>")
def api_intel(date):
    """Get daily intelligence feed."""
    intel_path = INTEL_DIR / f"daily_intel_{date}.json"
    if intel_path.exists():
        return jsonify(json.loads(intel_path.read_text()))
    return jsonify({"error": "No intel for this date"}), 404


@dashboard_bp.route("/api/channels", methods=["GET"])
def api_channels():
    """Get all channels with config."""
    config = load_channels_config()
    return jsonify(config)


@dashboard_bp.route("/api/channels/<channel_id>/toggle", methods=["POST"])
def api_toggle_channel(channel_id):
    """Enable/disable a channel."""
    data = request.json or {}
    enabled = data.get("enabled", True)
    success = toggle_channel(channel_id, enabled)
    return jsonify({"success": success, "channel_id": channel_id, "enabled": enabled})


@dashboard_bp.route("/api/ultron/health")
def api_ultron_health():
    """Check Ultron health."""
    return jsonify(ultron.health_check())


@dashboard_bp.route("/api/ultron/disk")
def api_ultron_disk():
    """Get Ultron disk usage."""
    result = ultron.disk_usage()
    return jsonify(result or {"error": "Could not fetch disk usage"})


@dashboard_bp.route("/api/ultron/output")
def api_ultron_output():
    """List Ultron output files."""
    return jsonify({"files": ultron.list_output()})


# ─── Content OS (Pulse Check v4) Dashboard ───

@dashboard_bp.route("/pulse")
def pulse_dashboard():
    """Content OS dashboard — last run, memory, costs, controls."""
    today = datetime.now().strftime("%Y-%m-%d")
    last_run = _get_last_pulse_run()
    memory = _load_editorial_memory()
    costs = _get_recent_costs(limit=7)
    is_locked = LOCK_FILE.exists()

    return jsonify({
        "date": today,
        "last_run": last_run,
        "editorial_memory": {
            "recent_episodes": memory.get("recent_episodes", [])[:7],
            "running_stories": len(memory.get("running_stories", [])),
            "overused_sources": memory.get("overused_sources", []),
            "tomorrows_watchlist": memory.get("tomorrows_watchlist", []),
        },
        "cost_history": costs,
        "is_locked": is_locked
    })


@dashboard_bp.route("/pulse/status")
def pulse_status():
    """Quick status check for the Content OS pipeline."""
    today = datetime.now().strftime("%Y-%m-%d")
    episode_dir = EPISODES_DIR / today
    has_run_today = (episode_dir / "costs" / "run_costs.json").exists() if episode_dir.exists() else False

    status = {
        "date": today,
        "has_run_today": has_run_today,
        "is_locked": LOCK_FILE.exists(),
        "episode_exists": episode_dir.exists(),
    }

    if has_run_today:
        costs_path = episode_dir / "costs" / "run_costs.json"
        try:
            costs = json.loads(costs_path.read_text())
            status["last_cost_usd"] = costs.get("estimated_cost_usd", 0)
            status["last_runtime_s"] = costs.get("total_runtime_seconds", 0)
        except Exception:
            pass

        # Check what artifacts exist
        status["artifacts"] = {
            "show_plan": (episode_dir / "show_plan").exists(),
            "clips": len(list((episode_dir / "clips").glob("*.mp4"))) if (episode_dir / "clips").exists() else 0,
            "voiceovers": len(list((episode_dir / "voiceovers").glob("*.mp3"))) if (episode_dir / "voiceovers").exists() else 0,
            "final_video": len(list((episode_dir / "final").glob("*.mp4"))) if (episode_dir / "final").exists() else 0,
            "shorts": len(list((episode_dir / "shorts").glob("*.mp4"))) if (episode_dir / "shorts").exists() else 0,
            "distribution_pack": (episode_dir / "distribution_pack").exists(),
        }

    return jsonify(status)


@dashboard_bp.route("/pulse/trigger", methods=["POST"])
def pulse_trigger():
    """Trigger a Content OS pipeline run."""
    import threading

    data = request.json or {}
    dry_run = data.get("dry_run", False)
    force = data.get("force", False)
    date_str = data.get("date")

    if LOCK_FILE.exists() and not force:
        return jsonify({"error": "Pipeline is locked (already running or ran today). Use force=true to override."}), 409

    def _run_pipeline():
        try:
            from pp_services.video_engine.daily_driver import DailyDriver
            driver = DailyDriver(date_str=date_str, dry_run=dry_run, force=force)
            driver.run()
        except Exception as e:
            logger.error(f"Triggered pipeline failed: {e}")

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return jsonify({
        "status": "started",
        "dry_run": dry_run,
        "force": force,
        "date": date_str or datetime.now().strftime("%Y-%m-%d")
    })


@dashboard_bp.route("/pulse/episodes")
def pulse_episodes():
    """List recent episode bundles."""
    episodes = []
    if EPISODES_DIR.exists():
        for ep_dir in sorted(EPISODES_DIR.iterdir(), reverse=True)[:14]:
            if ep_dir.is_dir():
                ep = {"date": ep_dir.name, "artifacts": {}}
                costs_path = ep_dir / "costs" / "run_costs.json"
                if costs_path.exists():
                    try:
                        costs = json.loads(costs_path.read_text())
                        ep["cost_usd"] = costs.get("estimated_cost_usd", 0)
                        ep["runtime_s"] = costs.get("total_runtime_seconds", 0)
                    except Exception:
                        pass
                plan_dir = ep_dir / "show_plan"
                if plan_dir.exists():
                    plans = list(plan_dir.glob("*.json"))
                    if plans:
                        try:
                            plan = json.loads(plans[0].read_text())
                            ep["headline"] = plan.get("episode_headline", "")
                            ep["stories"] = len(plan.get("stories", []))
                        except Exception:
                            pass
                episodes.append(ep)
    return jsonify({"episodes": episodes})


def _get_last_pulse_run():
    """Get the most recent episode run info."""
    if not EPISODES_DIR.exists():
        return None
    for ep_dir in sorted(EPISODES_DIR.iterdir(), reverse=True):
        if ep_dir.is_dir():
            costs_path = ep_dir / "costs" / "run_costs.json"
            if costs_path.exists():
                try:
                    costs = json.loads(costs_path.read_text())
                    return {
                        "date": ep_dir.name,
                        "cost_usd": costs.get("estimated_cost_usd", 0),
                        "runtime_s": costs.get("total_runtime_seconds", 0),
                        "grok_tokens": costs.get("grok_tokens_in", 0) + costs.get("grok_tokens_out", 0),
                        "claude_tokens": costs.get("claude_tokens_in", 0) + costs.get("claude_tokens_out", 0),
                        "elevenlabs_chars": costs.get("elevenlabs_characters", 0),
                    }
                except Exception:
                    pass
    return None


def _load_editorial_memory():
    """Load editorial memory."""
    if EDITORIAL_MEMORY_PATH.exists():
        try:
            return json.loads(EDITORIAL_MEMORY_PATH.read_text())
        except Exception:
            pass
    return {}


@dashboard_bp.route("/pulse/alert", methods=["POST"])
def pulse_alert_trigger():
    """Manually trigger a Pulse Alert scan."""
    import threading

    def _run_scan():
        try:
            from pp_services.video_engine.pulse_alert import PulseAlert
            alert = PulseAlert()
            alert.enabled = True  # Force enable for manual trigger
            results = alert.scan_and_process()
            for result in results:
                alert.distribute(result)
        except Exception as e:
            logger.error(f"Manual alert scan failed: {e}")

    thread = threading.Thread(target=_run_scan, daemon=True)
    thread.start()
    return jsonify({"status": "scan_started"})


@dashboard_bp.route("/pulse/alert/manual", methods=["POST"])
def pulse_alert_manual():
    """Submit a manual breaking event for Pulse Alert processing."""
    data = request.json or {}
    headline = data.get("headline")
    details = data.get("details", {})

    if not headline:
        return jsonify({"error": "headline required"}), 400

    event = {
        "type": "manual",
        "headline": headline,
        "details": details,
        "severity": data.get("severity", "medium"),
        "detected_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    try:
        from pp_services.video_engine.pulse_alert import PulseAlert
        alert = PulseAlert()
        alert.enabled = True
        result = alert.process_event(event)
        alert.distribute(result)
        return jsonify({"status": "processed", "event": event})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/pulse/alerts")
def pulse_alert_history():
    """Get recent Pulse Alert history."""
    alert_state_path = Path("state/pulse_alerts.json")
    if alert_state_path.exists():
        try:
            state = json.loads(alert_state_path.read_text())
            return jsonify({
                "alerts": state.get("recent_alerts", [])[:20],
                "last_scan": state.get("last_scan")
            })
        except Exception:
            pass
    return jsonify({"alerts": [], "last_scan": None})


def _get_recent_costs(limit=7):
    """Get cost data from recent episodes."""
    costs = []
    if not EPISODES_DIR.exists():
        return costs
    for ep_dir in sorted(EPISODES_DIR.iterdir(), reverse=True)[:limit]:
        if ep_dir.is_dir():
            costs_path = ep_dir / "costs" / "run_costs.json"
            if costs_path.exists():
                try:
                    data = json.loads(costs_path.read_text())
                    costs.append({
                        "date": ep_dir.name,
                        "cost_usd": data.get("estimated_cost_usd", 0),
                        "runtime_s": data.get("total_runtime_seconds", 0),
                    })
                except Exception:
                    pass
    return costs
