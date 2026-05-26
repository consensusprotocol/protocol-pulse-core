"""
Signal collection from X (Twitter), Nostr, and Stacker News for Sarah's briefings
and sentiment/signal pipelines. Persists to CollectedSignal for use by briefing_engine.
"""

import logging
import re
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

# Legendary handles (3x priority) — align with editorial rule
LEGENDARY_HANDLES = {
    "saylor", "lynaldencontact", "adam3us", "jeffbooth", "prestonpysh", "saifedean",
    "breedlove22", "jack", "lopp", "odell", "pierre_rochard", "martybent", "marshalllong",
    "_checkmatey_", "woonomic", "natbrunell", "nvk", "coryklippsten",
}


class SentimentTrackerService:
    def __init__(self):
        self._x_client = None
        self._x_client_v2 = None
        try:
            import os
            import tweepy
            if all([
                os.environ.get("TWITTER_API_KEY"),
                os.environ.get("TWITTER_API_SECRET"),
                os.environ.get("TWITTER_ACCESS_TOKEN"),
                os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
            ]):
                auth = tweepy.OAuthHandler(
                    os.environ.get("TWITTER_API_KEY"),
                    os.environ.get("TWITTER_API_SECRET"),
                )
                auth.set_access_token(
                    os.environ.get("TWITTER_ACCESS_TOKEN"),
                    os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
                )
                self._x_client = tweepy.API(auth, wait_on_rate_limit=True)
                logger.info("SentimentTracker: X API initialized")
        except Exception as e:
            logger.warning("SentimentTracker: X API not available: %s", e)

    def fetch_x_posts(self, hours_back=24, max_per_user=5, handles=None):
        """Fetch recent posts from legendary/monitored X handles. Returns list of dicts (not yet saved to DB)."""
        if not self._x_client:
            return []
        out = []
        if handles:
            handles = [str(h).strip().lstrip("@") for h in handles if str(h).strip()]
        else:
            handles = list(LEGENDARY_HANDLES)[:15]
        for handle in handles:
            try:
                user = self._x_client.get_user(screen_name=handle)
                if not user:
                    continue
                tweets = self._x_client.user_timeline(
                    user_id=user.id, count=max_per_user, tweet_mode="extended", include_rts=False
                )
                for t in tweets:
                    created = t.created_at
                    if created.replace(tzinfo=None) < datetime.utcnow() - timedelta(hours=hours_back):
                        continue
                    text = getattr(t, "full_text", None) or getattr(t, "text", "") or ""
                    if not text or len(text) < 20:
                        continue
                    post_id = f"x_{t.id}"
                    engagement = (t.favorite_count or 0) + (t.retweet_count or 0) * 2
                    out.append({
                        "platform": "x",
                        "post_id": post_id,
                        "author_name": user.name,
                        "author_handle": handle,
                        "author_tier": "macro",
                        "content": text[:2000],
                        "url": f"https://twitter.com/{handle}/status/{t.id}",
                        "engagement_likes": t.favorite_count or 0,
                        "engagement_reposts": t.retweet_count or 0,
                        "engagement_replies": 0,
                        "engagement_score": float(engagement),
                        "posted_at": created,
                        "is_legendary": handle.lower() in LEGENDARY_HANDLES,
                    })
            except Exception as e:
                logger.debug("X fetch %s: %s", handle, e)
        return out

    def fetch_nostr_notes(self, hours_back=24, limit=30):
        """Fetch recent notes from Nostr (e.g. via nostr.band API). Returns list of dicts."""
        out = []
        try:
            # nostr.band API: recent notes (Bitcoin-related)
            since = int((datetime.utcnow() - timedelta(hours=hours_back)).timestamp())
            r = requests.get(
                "https://api.nostr.band/v0/trending/notes",
                params={"tag": "bitcoin", "limit": limit},
                timeout=15,
            )
            if r.status_code != 200:
                return out
            data = r.json()
            for note in (data.get("notes") or data.get("trending") or [])[:limit]:
                created_at = note.get("created_at") or 0
                if created_at < since:
                    continue
                post_id = f"nostr_{note.get('id', note.get('event_id', ''))}"
                content = (note.get("content") or "")[:2000]
                if len(content) < 20:
                    continue
                author = note.get("user") or note.get("author") or {}
                name = author.get("name") or author.get("display_name") or "Unknown"
                handle = author.get("nip05") or author.get("npub", "")[:20]
                out.append({
                    "platform": "nostr",
                    "post_id": post_id,
                    "author_name": name,
                    "author_handle": handle or "nostr",
                    "author_tier": "general",
                    "content": content,
                    "url": note.get("url") or f"https://primal.net/e/{note.get('id', '')}",
                    "engagement_likes": note.get("reactions_count") or note.get("likes") or 0,
                    "engagement_reposts": 0,
                    "engagement_replies": 0,
                    "engagement_score": float(note.get("reactions_count") or note.get("score") or 0),
                    "posted_at": datetime.utcfromtimestamp(created_at) if created_at else datetime.utcnow(),
                    "is_legendary": False,
                })
        except Exception as e:
            logger.warning("Nostr fetch failed: %s", e)
        return out

    def fetch_stacker_news(self, limit=15):
        """Fetch recent posts from Stacker News (GraphQL or RSS). Returns list of dicts."""
        out = []
        try:
            # Stacker News GraphQL
            r = requests.post(
                "https://stacker.news/api/graphql",
                json={
                    "query": """
                    query { posts(limit: %d) {
                        id title url sats ncomments user { name }
                        createdAt
                      } }
                    """ % limit
                },
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                posts = (data.get("data") or {}).get("posts") or []
                for p in posts:
                    post_id = f"stacker_{p.get('id', '')}"
                    title = (p.get("title") or "")[:500]
                    if not title:
                        continue
                    user = p.get("user") or {}
                    author_name = user.get("name") or "Stacker"
                    out.append({
                        "platform": "stacker_news",
                        "post_id": post_id,
                        "author_name": author_name,
                        "author_handle": author_name,
                        "author_tier": "media",
                        "content": title,
                        "url": p.get("url") or f"https://stacker.news/items/{p.get('id')}",
                        "engagement_likes": p.get("sats") or 0,
                        "engagement_reposts": 0,
                        "engagement_replies": p.get("ncomments") or 0,
                        "engagement_score": float(p.get("sats") or 0) / 1000 + (p.get("ncomments") or 0),
                        "posted_at": datetime.utcnow(),  # GraphQL may not return ISO
                        "is_legendary": False,
                    })
                return out
        except Exception as e:
            logger.debug("Stacker News GraphQL failed: %s", e)
        # Fallback: RSS
        try:
            r = requests.get("https://stacker.news/rss", timeout=10)
            if r.status_code != 200:
                return out
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.text)
            for item in root.findall(".//item")[:limit]:
                link = item.find("link")
                title_el = item.find("title")
                title = (title_el.text or "")[:500] if title_el is not None else ""
                if not title:
                    continue
                post_id = f"stacker_rss_{hash(link.text or '') % 10**10}"
                out.append({
                    "platform": "stacker_news",
                    "post_id": post_id,
                    "author_name": "Stacker News",
                    "author_handle": "stacker.news",
                    "author_tier": "media",
                    "content": title,
                    "url": (link.text or "")[:500],
                    "engagement_likes": 0,
                    "engagement_reposts": 0,
                    "engagement_replies": 0,
                    "engagement_score": 1.0,
                    "posted_at": datetime.utcnow(),
                    "is_legendary": False,
                })
        except Exception as e:
            logger.warning("Stacker News RSS fallback failed: %s", e)
        return out

    def save_signals_to_db(self, posts):
        """Persist list of post dicts (from fetch_*) to CollectedSignal. Skips duplicates by post_id."""
        from app import app, db
        import models
        with app.app_context():
            saved = 0
            for p in posts:
                existing = models.CollectedSignal.query.filter_by(
                    platform=p["platform"], post_id=p["post_id"]
                ).first()
                if existing:
                    continue
                s = models.CollectedSignal(
                    platform=p["platform"],
                    post_id=p["post_id"],
                    author_name=p.get("author_name", "")[:200],
                    author_handle=p.get("author_handle", "")[:100],
                    author_tier=p.get("author_tier", "general")[:50],
                    content=p.get("content", "")[:5000],
                    url=(p.get("url") or "")[:500],
                    engagement_likes=p.get("engagement_likes", 0) or 0,
                    engagement_reposts=p.get("engagement_reposts", 0) or 0,
                    engagement_replies=p.get("engagement_replies", 0) or 0,
                    engagement_score=float(p.get("engagement_score", 0)),
                    posted_at=p.get("posted_at"),
                    is_verified=True,
                    is_legendary=bool(p.get("is_legendary")),
                )
                db.session.add(s)
                saved += 1
            try:
                db.session.commit()
                logger.info("Saved %d new signals to DB", saved)
            except Exception as e:
                db.session.rollback()
                logger.warning("Failed to save signals: %s", e)
            return saved
