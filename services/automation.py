"""
Automation helpers for Protocol Pulse (core version).

Right now we only expose a thin wrapper for:
- Generating podcasts from all monitored partner channels
  (driven by `supported_sources.json` via `youtube_service.auto_process_partners`).

This keeps the `/admin/generate-podcasts-batch` route working end-to-end
without pulling in the entire legacy Replit automation module.
"""

import logging
from contextlib import contextmanager

from app import app, db  # type: ignore
import models  # type: ignore
from services.youtube_service import YouTubeService  # type: ignore


logger = logging.getLogger(__name__)


@contextmanager
def app_context():
    """Ensure we always run inside a Flask app context."""
    with app.app_context():
        yield


def generate_podcasts_from_partners() -> dict:
    """
    Generate podcasts from all monitored Bitcoin partner channels.

    - Uses `supported_sources.json` via `YouTubeService.auto_process_partners()`
    - Writes resulting podcasts/articles into the database (handled by youtube_service)
    - Returns a summary dict for admin dashboards / API responses
    """
    from services.youtube_service import youtube_service  # lazy import singleton if present

    with app_context():
        service: YouTubeService
        if "youtube_service" in globals():
            service = youtube_service  # type: ignore
        else:
            service = YouTubeService()

        logger.info("Starting partner podcast generation from supported_sources.json")
        try:
            results = service.auto_process_partners()
        except Exception as e:
            logger.error("Partner podcast generation failed: %s", e)
            raise

        # Optionally, we can record a simple AutomationRun entry for observability
        try:
            run = models.AutomationRun(
                task_name="generate_podcasts_from_partners",
                started_at=models.datetime.utcnow(),  # type: ignore[attr-defined]
                finished_at=models.datetime.utcnow(),  # type: ignore[attr-defined]
                status="completed",
            )
            db.session.add(run)
            db.session.commit()
        except Exception as e:
            logger.warning("Failed to record AutomationRun for podcast generation: %s", e)

        logger.info(
            "Partner podcast generation complete: %s",
            {
                "videos_found": results.get("videos_found"),
                "articles_generated": len(results.get("articles_generated", [])),
                "podcasts_generated": len(results.get("podcasts_generated", [])),
            },
        )
        return results

