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
