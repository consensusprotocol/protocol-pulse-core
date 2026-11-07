"""
Automation helpers for Protocol Pulse (core version).

- generate_article_with_tracking: webhook-triggered article drafting (e.g. from cron).
- get_last_run_status: for /health/automation.
- generate_from_trending_reddit: Reddit → articles (used by run_daily_pipeline).
- process_all_partner_channels: YouTube partners → articles/podcasts (used by run_daily_pipeline).
- generate_podcasts_from_partners: podcasts from supported_sources.json.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timedelta

from app import app, db  # type: ignore
import models  # type: ignore
from services.youtube_service import YouTubeService  # type: ignore


logger = logging.getLogger(__name__)

AUTOMATION_TASK_NAME = "trigger_automation"
SKIP_IF_RAN_WITHIN_MINUTES = 10


@contextmanager
def app_context():
    """Ensure we always run inside a Flask app context."""
    with app.app_context():
        yield


def get_last_run_status() -> dict:
    """Return status of last trigger_automation run for /health/automation."""
    with app_context():
        run = (
            models.AutomationRun.query.filter_by(task_name=AUTOMATION_TASK_NAME)
            .order_by(models.AutomationRun.started_at.desc())
            .first()
        )
        if not run:
            return {"status": "never_run", "last_run": None}
        return {
            "status": run.status or "unknown",
            "last_run": run.finished_at.isoformat() if run.finished_at else run.started_at.isoformat(),
            "error": run.error,
        }


def generate_article_with_tracking(force: bool = False) -> dict:
    """
    Generate one article and record the run. Used by /api/trigger-automation.
    Skips if a run completed within the last SKIP_IF_RAN_WITHIN_MINUTES minutes (unless force=True).
    Articles are saved as published=True so they appear on the site immediately.
    Returns: {success, title, article_id}, {skipped}, or {error}.
    """
    with app_context():
        # Clean stale locks (older than 10 minutes with no finish)
        stale_threshold = datetime.utcnow() - timedelta(minutes=10)
        try:
            models.AutomationRun.query.filter(
                models.AutomationRun.task_name == AUTOMATION_TASK_NAME,
                models.AutomationRun.status == "running",
                models.AutomationRun.started_at < stale_threshold,
                models.AutomationRun.finished_at.is_(None),
            ).update(
                {"status": "failed", "error": "Stale lock expired", "finished_at": datetime.utcnow()},
                synchronize_session=False,
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Skip if we ran recently (unless force=True for manual/admin runs)
        if not force:
            recent = (
                models.AutomationRun.query.filter_by(task_name=AUTOMATION_TASK_NAME)
                .filter(models.AutomationRun.finished_at.isnot(None))
                .order_by(models.AutomationRun.started_at.desc())
                .first()
            )
            if recent and recent.finished_at:
                if datetime.utcnow() - recent.finished_at < timedelta(minutes=SKIP_IF_RAN_WITHIN_MINUTES):
                    return {"skipped": True, "message": "Another process is running or ran recently"}
        run = models.AutomationRun(
            task_name=AUTOMATION_TASK_NAME,
            started_at=datetime.utcnow(),
            finished_at=None,
            status="running",
        )
        db.session.add(run)
        db.session.commit()
        # ── REAL NEWS ONLY — no evergreen/topic-only fallback ────────────
        # Rule: an article is never published without a real news source.
        # Try up to 5 RSS/Reddit candidates before giving up.
        import re as _re

        try:
            from services.article_automation import (
                RealNewsArticleGenerator, _sanitize_title, _is_banned_template,
            )
            from services.articles.title_guard import derive_title, validate_title

            auto_publish_enabled = lambda: True
            try:
                from services.content_generator import auto_publish_enabled
            except Exception:
                pass

            generator = RealNewsArticleGenerator()

            # Date-slop rejection pattern
            _DATE_SLOP_RE = _re.compile(
                r"As (?:we approach|of) "
                r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
                r" 20\d{2}"
            )

            MAX_SOURCE_ATTEMPTS = 5
            last_err = None
            for attempt_idx in range(MAX_SOURCE_ATTEMPTS):
                try:
                    source = generator.select_best_source()
                    if not source:
                        last_err = "No RSS sources available"
                        break  # no point retrying — feed queue is empty

                    article_data = generator.generate_article_from_source(source)
                    if not article_data:
                        last_err = f"generate_article_from_source returned None (source: {source.get('title','')[:60]})"
                        logger.warning("Attempt %d/%d: %s", attempt_idx + 1, MAX_SOURCE_ATTEMPTS, last_err)
                        continue

                    # ── Title guard ──
                    raw_title = article_data.get("title", "")
                    final_title = _sanitize_title(raw_title)
                    if _is_banned_template(final_title):
                        last_err = f"Banned template: {final_title[:80]}"
                        logger.warning("Attempt %d/%d: %s", attempt_idx + 1, MAX_SOURCE_ATTEMPTS, last_err)
                        continue

                    # Apply title_guard as extra gate
                    guarded = derive_title(raw_title, article_data.get("content", ""))
                    if guarded:
                        final_title = guarded
                    if not validate_title(final_title):
                        last_err = f"Title guard rejected: {final_title[:80]}"
                        logger.warning("Attempt %d/%d: %s", attempt_idx + 1, MAX_SOURCE_ATTEMPTS, last_err)
                        continue

                    # ── Date anchoring: reject stale-date slop ──
                    content_text = article_data.get("content", "")
                    source_text = source.get("summary", "")
                    if _DATE_SLOP_RE.search(content_text):
                        # Only reject if the phrase is NOT in the source material
                        if not _DATE_SLOP_RE.search(source_text):
                            last_err = "Date slop detected (stale month reference not in source)"
                            logger.warning("Attempt %d/%d: %s", attempt_idx + 1, MAX_SOURCE_ATTEMPTS, last_err)
                            continue

                    # ── Source URL is mandatory ──
                    source_url = (article_data.get("source_url") or source.get("url") or "").strip()
                    if not source_url:
                        last_err = "No source_url — cannot publish without real news source"
                        logger.warning("Attempt %d/%d: %s", attempt_idx + 1, MAX_SOURCE_ATTEMPTS, last_err)
                        continue

                    publish_allowed = True
                    try:
                        publish_allowed = auto_publish_enabled()
                    except Exception:
                        pass

                    article = models.Article(
                        title=final_title,
                        content=content_text,
                        summary=article_data.get("summary", ""),
                        category=article_data.get("category", "Bitcoin"),
                        source_url=source_url,
                        source_type=(article_data.get("source_type") or "rss"),
                        author="Protocol Pulse",
                        published=publish_allowed,
                        cover_image_url="",
                    )
                    db.session.add(article)
                    db.session.flush()
                    from services.content_engine import _ensure_slug
                    _ensure_slug(article)
                    if not article.cover_image_url:
                        try:
                            from services.pexels_image import get_pexels_image as _gpx
                            _img, _phash = _gpx(article.title or '', article.category or 'bitcoin', article_id=article.id)
                            if _img and 'default-header' not in _img:
                                article.cover_image_url = _img
                                if _phash and hasattr(article, 'image_phash'):
                                    article.image_phash = _phash
                        except Exception:
                            pass
                    db.session.commit()

                    run.finished_at = datetime.utcnow()
                    run.status = "completed"
                    run.error = None
                    db.session.commit()
                    logger.info("[RSS] Published id=%d: %s", article.id, final_title[:70])
                    return {"success": True, "title": final_title, "article_id": article.id}

                except Exception as inner_e:
                    last_err = str(inner_e)
                    logger.warning("Attempt %d/%d failed: %s", attempt_idx + 1, MAX_SOURCE_ATTEMPTS, last_err)
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

            # All attempts exhausted — no qualifying source this tick
            full_error = f"no qualifying source this tick ({last_err})"
            logger.info(full_error)
            run.finished_at = datetime.utcnow()
            run.status = "failed"
            run.error = full_error[:500]
            db.session.commit()
            return {"success": False, "error": full_error}

        except Exception as e:
            full_error = f"RealNewsArticleGenerator init failed: {e}"
            logger.warning(full_error)
            run.finished_at = datetime.utcnow()
            run.status = "failed"
            run.error = full_error[:500]
            db.session.commit()
            return {"success": False, "error": full_error}


def generate_from_trending_reddit() -> dict:
    """Generate articles from trending Reddit posts. Used by admin run_daily_pipeline."""
    with app_context():
        try:
            from services.reddit_service import RedditService
            from services.content_generator import ContentGenerator
            reddit = RedditService()
            gen = ContentGenerator()
            ideas = reddit.get_content_ideas(topic_type="bitcoin", limit=3)
            articles_generated = []
            for idea in ideas:
                try:
                    topic = idea.get("title") or idea.get("article_angle", "Bitcoin trend")
                    article_data = gen.generate_article(topic, content_type="news_article", source_type="reddit")
                    if article_data and not article_data.get("skipped") and article_data.get("title"):
                        article = models.Article(
                            title=article_data["title"],
                            content=article_data["content"],
                            summary=article_data.get("summary", ""),
                            category=article_data.get("category", "Bitcoin"),
                            source_type="reddit",
                            author="Protocol Pulse",
                            published=False,
                        )
                        db.session.add(article)
                        db.session.commit()
                        articles_generated.append(article.id)
                except Exception as e:
                    logger.warning("Reddit idea article failed: %s", e)
            return {"articles_generated": len(articles_generated)}
        except Exception as e:
            logger.error("generate_from_trending_reddit failed: %s", e)
            return {"articles_generated": 0}


def process_all_partner_channels() -> dict:
    """Process YouTube partner channels for articles/podcasts. Used by admin run_daily_pipeline."""
    with app_context():
        try:
            service = YouTubeService()
            results = service.auto_process_partners()
            return {
                "articles_generated": len(results.get("articles_generated", [])),
                "podcasts_generated": len(results.get("podcasts_generated", [])),
            }
        except Exception as e:
            logger.error("process_all_partner_channels failed: %s", e)
            return {"articles_generated": 0, "podcasts_generated": 0}


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

