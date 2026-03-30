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
        content_engine_error = None
        fallback_error = None

        # ── PATH 1: RealNewsArticleGenerator (RSS + Claude/GPT-4o rewrite) ────
        try:
            from services.article_automation import RealNewsArticleGenerator, _sanitize_title, _is_banned_template

            auto_publish_enabled = lambda: True
            try:
                from services.content_generator import auto_publish_enabled
            except Exception:
                pass

            generator = RealNewsArticleGenerator()
            source = generator.select_best_source()
            if not source:
                raise ValueError("No RSS sources available")
            article_data = generator.generate_article_from_source(source)
            if not article_data:
                raise ValueError("generate_article_from_source returned None")

            raw_title = article_data.get("title", "")
            final_title = _sanitize_title(raw_title)
            if _is_banned_template(final_title):
                raise ValueError(f"Banned template: {final_title[:80]}")

            publish_allowed = True
            try:
                publish_allowed = auto_publish_enabled()
            except Exception:
                pass

            article = models.Article(
                title=final_title,
                content=article_data["content"],
                summary=article_data.get("summary", ""),
                category=article_data.get("category", "Bitcoin"),
                source_url=(article_data.get("source_url") or "").strip() or None,
                source_type=(article_data.get("source_type") or "rss"),
                author="Al Ingle",
                published=publish_allowed,
                cover_image_url="",
            )
            db.session.add(article)
            if not article.cover_image_url:
                try:
                    from services.pexels_image import get_pexels_image as _gpx
                    _img = _gpx(article.title or '', article.category or 'bitcoin', 0)
                    if _img and 'default-header' not in _img:
                        article.cover_image_url = _img
                except Exception:
                    pass
            db.session.commit()

            run.finished_at = datetime.utcnow()
            run.status = "completed"
            run.error = None
            db.session.commit()
            logger.info(f"[RSS] Published id={article.id}: {final_title[:70]}")
            return {"success": True, "title": final_title, "article_id": article.id}

        except Exception as e:
            content_engine_error = str(e)
            logger.warning("RealNewsArticleGenerator failed: %s", e)

        # ── PATH 2: Fallback to ContentEngine (OpenAI gpt-4o generic) ─────────
        topic = "Bitcoin network and market update"
        try:
            from services.content_engine import ContentEngine
            engine = ContentEngine()
            result = engine.generate_and_publish_article(
                topic, content_type="bitcoin_news", auto_publish=False
            )
            if result.get("success") and result.get("article_id"):
                article = models.Article.query.get(result["article_id"])
                if article:
                    article.published = True
                    db.session.commit()
                run.finished_at = datetime.utcnow()
                run.status = "completed"
                run.error = None
                db.session.commit()
                return {
                    "success": True,
                    "title": article.title if article else topic,
                    "article_id": result["article_id"],
                }
            fallback_error = "; ".join(result.get("errors") or ["No article_id returned"])
        except Exception as e:
            fallback_error = str(e)
            logger.warning("ContentEngine fallback failed: %s", e)

        # 3) All paths failed — if no published articles yet, create one stub so the site has something
        err_parts = []
        if content_engine_error:
            err_parts.append("RSS: " + (content_engine_error[:200] if isinstance(content_engine_error, str) else str(content_engine_error)[:200]))
        if fallback_error:
            err_parts.append("ContentEngine: " + (fallback_error[:200] if isinstance(fallback_error, str) else str(fallback_error)[:200]))
        full_error = " | ".join(err_parts) if err_parts else "No article generated"
        published_count = models.Article.query.filter_by(published=True).count()
        if published_count == 0:
            try:
                stub = models.Article(
                    title="Protocol Pulse Intel — Enable Auto-Drafting",
                    content="""<div class="tldr-section"><em><strong>TL;DR:</strong> This is a placeholder. Article drafting needs at least one AI API key (OPENAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY in .env). Reddit-sourced drafts also need REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT.</em></div>
<h2 class="article-header">Getting started</h2>
<p class="article-paragraph">Once your keys are set, use Admin → Dashboard → "Draft articles now" or run: <code>python -m core.scripts.draft_articles_now</code></p>
<h2 class="article-header">Sources</h2>
<ul class="sources-list"><li>Protocol Pulse ops</li></ul>""",
                    summary="Placeholder until drafting is configured.",
                    category="Bitcoin",
                    source_type="ai_generated",
                    author="Protocol Pulse",
                    published=True,
                )
                db.session.add(stub)
                db.session.commit()
                run.finished_at = datetime.utcnow()
                run.status = "completed"
                run.error = full_error[:500]
                db.session.commit()
                return {
                    "success": True,
                    "title": stub.title,
                    "article_id": stub.id,
                    "stub": True,
                    "error": full_error,
                }
            except Exception as e:
                logger.exception("Stub article creation failed: %s", e)
                run.finished_at = datetime.utcnow()
                run.status = "failed"
                run.error = full_error[:500]
                db.session.commit()
                return {"success": False, "error": run.error}
        # Already have articles; just report failure
        run.finished_at = datetime.utcnow()
        run.status = "failed"
        run.error = full_error[:500]
        db.session.commit()
        return {"success": False, "error": run.error}


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
                            author="Al Ingle",
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

