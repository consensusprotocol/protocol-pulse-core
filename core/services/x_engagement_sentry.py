"""
X Engagement Sentry — end-to-end cycle for Sovereign Sentry replies.

Responsibilities:
- Load command_center_config.json for monitored accounts and thresholds
- Fetch new tweets via XClient
- Store in XInboxTweet
- Generate drafts via x_reply_writer using Sovereign Sentry V4 prompt

The central scheduler's `social_guard` task calls `run_cycle()` periodically.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from app import db
from models import XInboxTweet, XReplyDraft
from .x_client import XClient
from . import x_reply_writer

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load config/twitter_engagement.json first, fallback to core/config/command_center_config.json."""
    try:
        repo_root = Path(__file__).resolve().parents[2]
        preferred = repo_root / "config" / "twitter_engagement.json"
        legacy = Path(__file__).resolve().parents[1] / "config" / "command_center_config.json"
        for cfg_path in (preferred, legacy):
            if not cfg_path.exists():
                continue
            with cfg_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        logger.debug("X Sentry config missing at %s and %s", preferred, legacy)
        return {}
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to load X Sentry config: %s", e)
        return {}


def _get_conf() -> Dict[str, Any]:
    cfg = _load_config()
    return cfg.get("x_engagement_sentry") or {}


def _get_thresholds() -> Dict[str, float]:
    conf = _get_conf()
    return conf.get("confidence_thresholds", {}) or {}


def _get_monitored_accounts() -> List[Dict[str, Any]]:
    conf = _get_conf()
    return conf.get("monitored_accounts", []) or []


def _should_skip_text(text: str) -> bool:
    conf = _get_conf()
    blacklist = (conf.get("blacklist_keywords") or []) if conf else []
    lower = text.lower()
    return any(kw.lower() in lower for kw in blacklist)


def _find_since_id(handle: str) -> str | None:
    """Return highest tweet_id we have seen for this handle."""
    try:
        row = (
            XInboxTweet.query.filter_by(author_handle=handle)
            .order_by(XInboxTweet.tweet_id.desc())
            .first()
        )
        return row.tweet_id if row else None
    except Exception as e:  # pragma: no cover
        logger.debug("X Sentry: since_id lookup failed for %s: %s", handle, e)
        return None


def _ingest_new_tweets(x_client: XClient) -> int:
    """Fetch and insert new tweets for all monitored accounts."""
    accounts = _get_monitored_accounts()
    if not accounts:
        return 0

    inserted = 0
    for acc in accounts:
        handle = acc.get("handle")
        if not handle:
            continue

        since_id = _find_since_id(handle)
        tweets = x_client.fetch_latest_tweets(handle=handle, since_id=since_id)
        for t in tweets:
            text = t.get("text", "")
            if not text or _should_skip_text(text):
                continue

            # Deduplicate by tweet_id
            existing = XInboxTweet.query.filter_by(tweet_id=str(t["id"])).first()
            if existing:
                continue

            inbox = XInboxTweet(
                tweet_id=str(t["id"]),
                author_handle=handle,
                author_name=acc.get("name"),
                tweet_text=text,
                tweet_url=f"https://x.com/{handle}/status/{t['id']}",
                tweet_created_at=t.get("created_at") or datetime.utcnow(),
                status="new",
                tier=acc.get("tier"),
                style=acc.get("style"),
            )
            db.session.add(inbox)
            inserted += 1

    if inserted:
        try:
            db.session.commit()
        except Exception as e:  # pragma: no cover
            logger.error("X Sentry ingest commit failed: %s", e)
            db.session.rollback()
            inserted = 0

    return inserted


def _generate_drafts() -> int:
    """Generate drafts for new tweets using Sovereign Sentry prompt."""
    thresholds = _get_thresholds()
    queue_min = float(thresholds.get("queue_for_approval", 0.70))

    # Only generate for truly new tweets
    new_tweets: List[XInboxTweet] = (
        XInboxTweet.query.filter_by(status="new")
        .order_by(XInboxTweet.created_at.asc())
        .limit(10)
        .all()
    )
    created = 0

    for inbox in new_tweets:
        try:
            result = x_reply_writer.generate_reply(
                tweet_text=inbox.tweet_text,
                author_handle=inbox.author_handle,
                author_name=inbox.author_name,
                style_hint=inbox.style,
            )
            if result.get("skip"):
                inbox.status = "skipped"
                db.session.add(inbox)
                continue

            confidence = float(result.get("confidence", 0.0))
            if confidence < queue_min:
                inbox.status = "skipped"
                db.session.add(inbox)
                continue

            draft = XReplyDraft(
                inbox_id=inbox.id,
                draft_text=result.get("response", ""),
                confidence=confidence,
                reasoning=result.get("reasoning", ""),
                style_used=result.get("style_used", ""),
                risk_flags=None,
            )
            db.session.add(draft)
            inbox.status = "drafted"
            db.session.add(inbox)
            created += 1
        except Exception as e:  # pragma: no cover
            logger.warning("X Sentry draft generation failed for inbox %s: %s", inbox.id, e)
            inbox.status = "error"
            db.session.add(inbox)

    if new_tweets:
        try:
            db.session.commit()
        except Exception as e:  # pragma: no cover
            logger.error("X Sentry draft commit failed: %s", e)
            db.session.rollback()
            created = 0

    return created


def run_cycle() -> Dict[str, Any]:
    """
    Single engagement cycle:
    - fetch new tweets from monitored accounts
    - generate reply drafts for new inbox items
    """
    conf = _get_conf()
    if not conf or not conf.get("enabled", True):
        logger.debug("X Engagement Sentry disabled in config.")
        return {"success": True, "ingested": 0, "drafts": 0, "disabled": True}

    client = XClient()
    ingested = _ingest_new_tweets(client)
    drafts = _generate_drafts()

    logger.info("X Sentry cycle complete: ingested=%s, drafts=%s", ingested, drafts)
    return {"success": True, "ingested": ingested, "drafts": drafts}

