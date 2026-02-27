from __future__ import annotations

from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from typing import List
from xml.sax.saxutils import escape

from app import app
import models


class PodcastEngine:
    """Generate an Apple-compatible RSS feed from podcast rows + daily medley artifact."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.logs_path = self.project_root / "logs"
        self.medley_file = self.logs_path / "medley_daily_beat.mp4"
        self.default_image = "/static/images/protocol-pulse-logo-transparent.png"

    def _base_url(self) -> str:
        return (app.config.get("PUBLIC_BASE_URL") or "").rstrip("/") or "https://protocolpulse.io"

    def _media_url(self, relative_path: str) -> str:
        return f"{self._base_url()}{relative_path}"

    def _latest_podcasts(self, limit: int = 40) -> List[models.Podcast]:
        return (
            models.Podcast.query.order_by(models.Podcast.published_date.desc(), models.Podcast.id.desc())
            .limit(limit)
            .all()
        )

    def generate_feed_xml(self) -> str:
        now = datetime.utcnow()
        channel_title = "Protocol Pulse Daily Beat"
        channel_link = self._base_url()
        channel_desc = "Bitcoin-native signal briefings, medley clips, and operator intelligence."
        image_url = self._media_url(self.default_image)

        items = []
        for pod in self._latest_podcasts():
            pub = pod.published_date or now
            enclosure = pod.audio_url or ""
            if enclosure and enclosure.startswith("/"):
                enclosure = self._media_url(enclosure)
            if not enclosure:
                continue
            title = escape(pod.title or f"Episode {pod.id}")
            desc = escape((pod.description or "Protocol Pulse intelligence drop.")[:1800])
            guid = escape(enclosure)
            items.append(
                (
                    f"<item>"
                    f"<title>{title}</title>"
                    f"<description>{desc}</description>"
                    f"<pubDate>{format_datetime(pub)}</pubDate>"
                    f"<enclosure url=\"{escape(enclosure)}\" type=\"audio/mpeg\" />"
                    f"<guid isPermaLink=\"false\">{guid}</guid>"
                    f"</item>"
                )
            )

        if self.medley_file.exists() and self.medley_file.stat().st_size > 0:
            medley_url = self._media_url("/media/daily-beat.mp4")
            items.insert(
                0,
                (
                    "<item>"
                    "<title>Daily Beat Medley</title>"
                    "<description>60-second daily beat stitched from top-zapped partner clips.</description>"
                    f"<pubDate>{format_datetime(now)}</pubDate>"
                    f"<enclosure url=\"{escape(medley_url)}\" type=\"video/mp4\" />"
                    f"<guid isPermaLink=\"false\">{escape(medley_url)}</guid>"
                    "</item>"
                ),
            )

        items_xml = "".join(items) or (
            "<item><title>Protocol Pulse Feed Warmup</title>"
            "<description>No episodes yet. Feed is live and waiting for drops.</description>"
            f"<pubDate>{format_datetime(now)}</pubDate>"
            f"<guid isPermaLink=\"false\">{escape(self._base_url())}/feed.xml#warmup</guid>"
            "</item>"
        )

        xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<rss version=\"2.0\" "
            "xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\" "
            "xmlns:atom=\"http://www.w3.org/2005/Atom\">"
            "<channel>"
            f"<title>{escape(channel_title)}</title>"
            f"<link>{escape(channel_link)}</link>"
            f"<description>{escape(channel_desc)}</description>"
            f"<language>en-us</language>"
            f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>"
            f"<itunes:author>Protocol Pulse</itunes:author>"
            f"<itunes:summary>{escape(channel_desc)}</itunes:summary>"
            "<itunes:explicit>false</itunes:explicit>"
            f"<itunes:image href=\"{escape(image_url)}\" />"
            f"<atom:link href=\"{escape(self._media_url('/feed.xml'))}\" rel=\"self\" type=\"application/rss+xml\" />"
            f"{items_xml}"
            "</channel>"
            "</rss>"
        )
        return xml


podcast_engine = PodcastEngine()
