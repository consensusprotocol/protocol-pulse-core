"""
Automation helpers for Protocol Pulse (core version).

- generate_article_with_tracking: webhook-triggered article drafting (e.g. from cron).
- get_last_run_status: for /health/automation.
- generate_from_trending_reddit: Reddit → articles (used by run_daily_pipeline).
- process_all_partner_channels: YouTube partners → articles/podcasts (used by run_daily_pipeline).
- generate_podcasts_from_partners: podcasts from supported_sources.json.
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta

from app import app, db  # type: ignore
import models  # type: ignore
from services.youtube_service import YouTubeService  # type: ignore


logger = logging.getLogger(__name__)

AUTOMATION_TASK_NAME = "trigger_automation"
SKIP_IF_RAN_WITHIN_MINUTES = 10
ARTICLE_AUTOMATION_TASK_NAME = "article_generation_15m"

# Replit-style topic pool (shuffled each run; filtered by 3-tier duplicate detection).
TOPICS = [
    "Bitcoin mining difficulty reaches new all-time high as hash rate surges",
    "Major institutional investors allocate billions to Bitcoin treasury reserves",
    "Lightning Network payment volume breaks monthly records",
    "DeFi protocols implement revolutionary new yield farming mechanisms",
    "Central banks accelerate CBDC development in response to Bitcoin adoption",
    "Major corporations announce Bitcoin payment integration plans",
    "Renewable energy Bitcoin mining initiatives expand globally",
    "DeFi total value locked reaches new milestone despite market volatility",
    "Bitcoin ETF inflows surge as retail and institutional demand grows",
    "Layer 2 scaling solutions see unprecedented adoption rates",
    "Bitcoin node count reaches new highs as decentralization strengthens",
    "Nostr protocol adoption grows as censorship-resistant social media expands",
    "Bitcoin self-custody solutions see record downloads amid banking concerns",
    "Hardware wallet manufacturers report surge in demand",
    "Bitcoin development activity increases with new BIP proposals",
    "Stablecoin regulations face scrutiny as Bitcoin alternative gains attention",
    "Bitcoin ordinals and inscriptions drive on-chain activity surge",
    "Countries explore strategic Bitcoin reserve policies",
    "Bitcoin privacy improvements proposed in new protocol upgrades",
    "Cross-border Bitcoin payments reduce remittance costs globally",
]

# Tier 1: core-topic matching (prevents “same event, different wording” repeats).
CORE_TOPICS = {
    "mining_difficulty": ["mining", "difficulty", "hash", "hashrate"],
    "lightning_network": ["lightning", "network", "payment", "volume"],
    "defi_tvl": ["defi", "tvl", "locked", "value"],
    "etf_inflows": ["etf", "inflow", "inflows", "demand"],
    "institutional": ["institutional", "treasury", "billion"],
    "strategic_reserve": ["reserve", "reserves", "strategic", "nation", "sovereign"],
    "regulation": ["regulation", "regulatory", "sec", "cftc", "law", "bill"],
    "price_milestone": ["price", "milestone", "ath", "high", "record"],
    "adoption": ["adoption", "accept", "acceptance", "mainstream"],
    "halving": ["halving", "halvening", "block", "reward", "subsidy"],
}


def _get_core_topic(text: str) -> str | None:
    import re
    text_lower = (text or "").lower()
    words = set(re.findall(r"\b[a-zA-Z]{3,}\b", text_lower))
    for topic_id, keywords in CORE_TOPICS.items():
        matches = sum(1 for kw in keywords if kw in words)
        if matches >= 2:
            return topic_id
    return None


def _get_topic_keywords(text: str) -> set[str]:
    import re
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "bitcoin", "btc", "crypto", "market", "surge", "record", "high", "new",
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", (text or "").lower())
    return {w for w in words if w not in stop_words}


def _keyword_jaccard_similar(new_topic: str, existing_title: str, threshold: float = 0.35) -> bool:
    new_kw = _get_topic_keywords(new_topic)
    existing_kw = _get_topic_keywords(existing_title)
    if not new_kw or not existing_kw:
        return False
    inter = len(new_kw & existing_kw)
    union = len(new_kw | existing_kw)
    sim = inter / union if union else 0.0
    return sim >= threshold


def is_topic_similar_to_recent(topic: str, hours: int = 48) -> bool:
    """3-tier duplicate detection: core topic, keyword Jaccard, then Gemini semantic gatekeeper."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent_articles = models.Article.query.filter(
        models.Article.created_at >= cutoff,
        models.Article.published.is_(True),
    ).order_by(models.Article.created_at.desc()).limit(50).all()
    if not recent_articles:
        return False

    # Tier 1: core topic match
    new_core = _get_core_topic(topic)
    if new_core:
        for a in recent_articles:
            if _get_core_topic(a.title or "") == new_core:
                return True

    # Tier 2: keyword similarity (Jaccard)
    for a in recent_articles:
        if _keyword_jaccard_similar(topic, a.title or ""):
            return True

    # Tier 3: semantic duplicate check (Gemini). If not configured, this safely returns False.
    try:
        from services.content_generator import is_topic_duplicate_via_gemini
        if is_topic_duplicate_via_gemini(topic):
            return True
    except Exception:
        pass

    return False


def get_unique_topic(max_attempts: int = 10) -> str | None:
    """Pick a topic that passes the 3-tier duplicate check; fall back to dynamic topics."""
    import random
    available = list(TOPICS)
    random.shuffle(available)
    for t in available[:max_attempts]:
        if not is_topic_similar_to_recent(t):
            return t

    dynamic_topics = [
        f"Bitcoin adoption trends and market analysis for {datetime.utcnow().strftime('%B %Y')}",
        "Weekly Bitcoin network statistics show evolving usage patterns",
        "Bitcoin's role in the evolving global monetary landscape",
        "Technical analysis of Bitcoin's current market cycle position",
        "Bitcoin mining industry developments and energy usage trends",
    ]
    for t in dynamic_topics:
        if not is_topic_similar_to_recent(t):
            return t
    return None


def acquire_lock(task_name: str, ttl_minutes: int = 10) -> models.AutomationRun | None:
    """DB-backed lock using AutomationRun rows (prevents overlapping scheduler runs)."""
    # Clean stale locks (older than 30 minutes)
    stale_threshold = datetime.utcnow() - timedelta(minutes=30)
    try:
        models.AutomationRun.query.filter(
            models.AutomationRun.task_name == task_name,
            models.AutomationRun.status == "running",
            models.AutomationRun.started_at < stale_threshold,
            models.AutomationRun.finished_at.is_(None),
        ).update(
            {"status": "failed", "error": "Stale lock", "finished_at": datetime.utcnow()},
            synchronize_session=False,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Check for active lock in ttl window
    cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
    active = models.AutomationRun.query.filter(
        models.AutomationRun.task_name == task_name,
        models.AutomationRun.started_at >= cutoff,
        models.AutomationRun.finished_at.is_(None),
        models.AutomationRun.status == "running",
    ).first()
    if active:
        return None

    run = models.AutomationRun(task_name=task_name, started_at=datetime.utcnow(), finished_at=None, status="running")
    db.session.add(run)
    db.session.commit()
    return run


def release_lock(run: models.AutomationRun, status: str = "success", error: str | Exception | None = None) -> None:
    run.finished_at = datetime.utcnow()
    run.status = status
    if error:
        run.error = str(error)[:500]
    db.session.commit()


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
        from services.content_generator import auto_publish_enabled, validate_article_for_publish
        publish_allowed = auto_publish_enabled()
        # Replit-style execution locking:
        # - Always prevent overlapping runs (even when force=True).
        # - force=True only bypasses the "ran recently" cooldown.
        run = acquire_lock(AUTOMATION_TASK_NAME, ttl_minutes=SKIP_IF_RAN_WITHIN_MINUTES)
        if not run:
            return {"skipped": True, "message": "Another process is running"}
        if not force:
            recent = (
                models.AutomationRun.query.filter_by(task_name=AUTOMATION_TASK_NAME)
                .filter(models.AutomationRun.finished_at.isnot(None))
                .order_by(models.AutomationRun.started_at.desc())
                .first()
            )
            if recent and recent.finished_at:
                if datetime.utcnow() - recent.finished_at < timedelta(minutes=SKIP_IF_RAN_WITHIN_MINUTES):
                    release_lock(run, "skipped", "Ran recently")
                    return {"skipped": True, "message": "Ran recently"}
        content_engine_error = None
        reddit_error = None
        topic = "Bitcoin network and market update"

        # 1) Try ContentEngine (needs OPENAI_API_KEY for bitcoin_news)
        try:
            from services.content_engine import ContentEngine
            engine = ContentEngine()
            result = engine.generate_and_publish_article(
                topic, content_type="bitcoin_news", auto_publish=False
            )
            if result.get("success") and result.get("article_id"):
                article = models.Article.query.get(result["article_id"])
                if article:
                    ok, errs = validate_article_for_publish(article)
                    from services.content_generator import should_article_be_draft_by_word_count
                    draft_by_words = should_article_be_draft_by_word_count(article.content or "")
                    if publish_allowed and ok and not draft_by_words:
                        article.published = True
                    else:
                        article.published = False
                    db.session.commit()
                release_lock(run, "success", None)
                return {
                    "success": True,
                    "title": article.title if article else topic,
                    "article_id": result["article_id"],
                }
            content_engine_error = "; ".join(result.get("errors") or ["No article_id returned"])
        except Exception as e:
            content_engine_error = str(e)
            logger.warning("ContentEngine article generation failed: %s", e)

        # 2) Fallback: ContentGenerator with same topic (tries OpenAI → Gemini → Anthropic)
        try:
            from services.content_generator import ContentGenerator
            gen = ContentGenerator()
            article_data = gen.generate_article(topic, content_type="news_article", source_type="ai_generated")
            if article_data and not article_data.get("skipped") and article_data.get("title"):
                ok, errs = validate_article_for_publish(article_data)
                from services.content_generator import should_article_be_draft_by_word_count, get_article_header_url
                draft_by_words = should_article_be_draft_by_word_count(article_data.get("content") or "")
                header_url = (article_data.get("header_image_url") or "").strip() or get_article_header_url(article_data["title"])
                article = models.Article(
                    title=article_data["title"],
                    content=article_data["content"],
                    summary=article_data.get("summary", ""),
                    category=article_data.get("category", "Bitcoin"),
                    source_url=(article_data.get("source_url") or "").strip() or None,
                    source_type=(article_data.get("source_type") or "ai_generated"),
                    author="Al Ingle",
                    published=(publish_allowed and ok and not draft_by_words),
                    header_image_url=header_url,
                )
                db.session.add(article)
                db.session.commit()
                release_lock(
                    run,
                    "success" if (publish_allowed and ok) else "failed",
                    None if (publish_allowed and ok) else ("publish blocked" if not publish_allowed else ("rejected: " + "; ".join(errs))[:500]),
                )
                return {"success": True, "title": article.title, "article_id": article.id}
        except Exception as e:
            reddit_error = str(e)
            logger.warning("ContentGenerator (ai_generated) fallback failed: %s", e)

        # 3) Fallback: Reddit trending → ContentGenerator
        try:
            from services.reddit_service import RedditService
            from services.content_generator import ContentGenerator
            reddit = RedditService()
            ideas = reddit.get_content_ideas(topic_type="bitcoin", limit=1)
            if ideas:
                idea = ideas[0]
                topic_reddit = idea.get("title") or idea.get("article_angle") or topic
            else:
                topic_reddit = topic
            gen = ContentGenerator()
            article_data = gen.generate_article(topic_reddit, content_type="news_article", source_type="reddit")
            if article_data and not article_data.get("skipped") and article_data.get("title"):
                ok, errs = validate_article_for_publish(article_data)
                from services.content_generator import should_article_be_draft_by_word_count, get_article_header_url
                draft_by_words = should_article_be_draft_by_word_count(article_data.get("content") or "")
                header_url = (article_data.get("header_image_url") or "").strip() or get_article_header_url(article_data["title"])
                article = models.Article(
                    title=article_data["title"],
                    content=article_data["content"],
                    summary=article_data.get("summary", ""),
                    category=article_data.get("category", "Bitcoin"),
                    source_url=(article_data.get("source_url") or "").strip() or None,
                    source_type=(article_data.get("source_type") or "reddit"),
                    author="Al Ingle",
                    published=(publish_allowed and ok and not draft_by_words),
                    header_image_url=header_url,
                )
                db.session.add(article)
                db.session.commit()
                release_lock(
                    run,
                    "success" if (publish_allowed and ok) else "failed",
                    None if (publish_allowed and ok) else ("publish blocked" if not publish_allowed else ("rejected: " + "; ".join(errs))[:500]),
                )
                return {"success": True, "title": article.title, "article_id": article.id}
        except Exception as e:
            reddit_error = str(e)
            logger.warning("Reddit/ContentGenerator fallback failed: %s", e)

        # 4) All paths failed — if no published articles yet, create one stub so the site has something
        err_parts = []
        if content_engine_error:
            err_parts.append("ContentEngine: " + (content_engine_error[:200] if isinstance(content_engine_error, str) else str(content_engine_error)[:200]))
        if reddit_error:
            err_parts.append("Fallbacks: " + reddit_error[:200])
        full_error = " | ".join(err_parts) if err_parts else "No article generated"
        published_count = models.Article.query.filter_by(published=True).count()
        if published_count == 0:
            try:
                # Even the stub should respect the freeze and remain a draft by default.
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
                    published=bool(publish_allowed),
                )
                db.session.add(stub)
                db.session.commit()
                # Stub created successfully, but record original failure details.
                release_lock(run, "success", full_error[:500])
                return {
                    "success": True,
                    "title": stub.title,
                    "article_id": stub.id,
                    "stub": True,
                    "error": full_error,
                }
            except Exception as e:
                logger.exception("Stub article creation failed: %s", e)
                release_lock(run, "failed", full_error[:500])
                return {"success": False, "error": run.error}
        # Already have articles; just report failure
        release_lock(run, "failed", full_error[:500])
        return {"success": False, "error": run.error}


def generate_breaking_article_with_tracking() -> dict:
    """Scheduler target: generate one breaking_news article every 15 minutes (Replit-style)."""
    with app_context():
        run = acquire_lock(ARTICLE_AUTOMATION_TASK_NAME, ttl_minutes=14)
        if not run:
            return {"skipped": True, "message": "Another process is running"}
        try:
            from services.content_generator import (
                ContentGenerator,
                validate_article_for_publish,
                auto_publish_enabled,
                should_article_be_draft_by_word_count,
                get_article_header_url,
            )
            publish_allowed = auto_publish_enabled()

            topic = get_unique_topic()
            if not topic:
                release_lock(run, "skipped", "No unique topics available")
                return {"skipped": True, "message": "No unique topics available"}

            gen = ContentGenerator()
            article_data = gen.generate_article(topic=topic, content_type="breaking_news", source_type="ai_generated")
            if not article_data or article_data.get("skipped") or not article_data.get("title"):
                release_lock(run, "failed", "No article data generated")
                return {"success": False, "error": "No article data generated"}

            ok, errs = validate_article_for_publish(article_data)
            draft_by_words = should_article_be_draft_by_word_count(article_data.get("content") or "")
            header_url = (article_data.get("header_image_url") or "").strip() or get_article_header_url(article_data["title"])

            article = models.Article(
                title=article_data["title"],
                content=article_data["content"],
                summary="",
                category=article_data.get("category", "Bitcoin"),
                tags=article_data.get("tags", "bitcoin,breaking,news"),
                author="Al Ingle",
                seo_title=article_data.get("seo_title", article_data["title"]),
                seo_description=article_data.get("seo_description", ""),
                source_url=(article_data.get("source_url") or "").strip() or None,
                source_type=(article_data.get("source_type") or "ai_generated"),
                header_image_url=header_url,
                published=(publish_allowed and ok and not draft_by_words),
                featured=True,
            )
            db.session.add(article)
            db.session.commit()
            release_lock(
                run,
                "success" if article.published else "failed",
                None if article.published else ("rejected: " + "; ".join(errs))[:500],
            )
            return {"success": True, "article_id": article.id, "title": article.title, "published": bool(article.published)}
        except Exception as e:
            release_lock(run, "failed", e)
            return {"success": False, "error": str(e)}


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

