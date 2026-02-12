"""
Target Monitor: monitors specific YouTube channels and X handles for new content.
When a monitored channel posts, fetches the content, runs it through AI analysis, and flags it
for article generation or intelligence stream posting. Used by automation and scheduler.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TargetMonitor:
    def __init__(self):
        self._sources = None
        self._youtube = None
        self._x = None

    def _get_sources(self):
        if self._sources is None:
            try:
                from services.supported_sources_loader import load_supported_sources
                self._sources = load_supported_sources()
            except Exception as e:
                logger.warning("TargetMonitor: supported sources not loaded: %s", e)
                self._sources = {"youtube_channels": [], "x_accounts": []}
        return self._sources

    def _get_youtube(self):
        if self._youtube is None:
            try:
                from services.youtube_service import YouTubeService
                self._youtube = YouTubeService()
            except Exception as e:
                logger.warning("TargetMonitor: YouTube not available: %s", e)
        return self._youtube

    def get_new_youtube_videos(self, since_hours: int = 24) -> List[Dict]:
        """
        Check configured YouTube channels for videos posted in the last since_hours.
        Returns list of { channel_name, channel_id, video_id, title, published_at }.
        """
        sources = self._get_sources()
        channels = sources.get("youtube_channels") or []
        out = []
        for ch in channels:
            name = ch.get("name")
            cid = ch.get("channel_id")
            if not cid:
                continue
            try:
                import requests
                r = requests.get(
                    f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}",
                    timeout=10,
                )
                if r.status_code != 200:
                    continue
                import xml.etree.ElementTree as ET
                root = ET.fromstring(r.text)
                cutoff = datetime.utcnow() - timedelta(hours=since_hours)
                for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall("entry"):
                    published = entry.find("{http://www.w3.org/2005/Atom}published") or entry.find("published")
                    if published is not None and published.text:
                        try:
                            from dateutil.parser import parse as parse_dt
                            pub_dt = parse_dt(published.text).replace(tzinfo=None)
                        except Exception:
                            pub_dt = datetime.utcnow()
                        if pub_dt < cutoff:
                            break
                    vid = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId") or entry.find("videoId")
                    video_id = vid.text if vid is not None and hasattr(vid, "text") else ""
                    title_el = entry.find("{http://www.w3.org/2005/Atom}title") or entry.find("title")
                    title = title_el.text if title_el is not None else ""
                    if video_id:
                        out.append({
                            "channel_name": name,
                            "channel_id": cid,
                            "video_id": video_id,
                            "title": title,
                            "published_at": published.text if published is not None else None,
                        })
            except Exception as e:
                logger.debug("TargetMonitor YouTube channel %s: %s", name, e)
        return out

    def get_new_x_posts(self, hours_back: int = 24, handles: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch recent posts from monitored X handles. Returns list of { handle, post_id, text, posted_at }.
        """
        try:
            from services.sentiment_tracker_service import SentimentTrackerService
            tracker = SentimentTrackerService()
            # Use provided handles when present; fallback to a compact sovereign core.
            h = [str(x).strip().lstrip("@").lower() for x in (handles or []) if str(x).strip()]
            if not h:
                h = ["saylor", "lynaldencontact", "saifedean", "jack", "lopp", "natbrunell"]
            posts = tracker.fetch_x_posts(hours_back=hours_back, max_per_user=3, handles=h)
            return [
                {
                    "handle": p.get("author_handle"),
                    "post_id": p.get("post_id"),
                    "text": p.get("content", "")[:500],
                    "posted_at": p.get("posted_at"),
                }
                for p in posts
                if (p.get("author_handle") or "").strip().lower() in h
            ]
        except Exception as e:
            logger.warning("TargetMonitor X posts: %s", e)
            return []

    def flag_for_article(self, source_type: str, title: str, url: str, metadata: Optional[Dict] = None):
        """
        Flag content for article generation (e.g. write to ContentSuggestion or queue).
        Caller can then run content_generator or automation on the queue.
        """
        try:
            from app import app, db
            import models
            with app.app_context():
                suggestion = models.ContentSuggestion(
                    suggestion_type=source_type,
                    title=title[:300],
                    description=url[:500],
                )
                db.session.add(suggestion)
                db.session.commit()
                logger.info("Flagged for article: %s", title[:80])
        except Exception as e:
            logger.warning("flag_for_article failed: %s", e)

    def flag_for_intel_stream(self, channel_name: str, video_id: str, title: str):
        """Flag a YouTube video for intelligence stream thread (partner tag)."""
        logger.info("Flagged for intel stream: %s / %s", channel_name, video_id)


target_monitor = TargetMonitor()
