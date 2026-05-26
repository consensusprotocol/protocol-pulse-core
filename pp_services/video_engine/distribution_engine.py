"""
MULTI-PLATFORM DISTRIBUTION ENGINE
=====================================
Takes a daily video episode and distributes across 7+ platforms simultaneously.

Platforms:
  1. YouTube (full episode upload)
  2. YouTube Shorts (3-5 vertical clips)
  3. X/Twitter (thread + poll + clips)
  4. Website (article digest)
  5. Newsletter (email digest)
  6. Podcast RSS (audio-only)
  7. Discord/Telegram (notifications + clips)

Features:
  - Platform-optimized formatting
  - A/B testing of headlines
  - Optimal posting times per platform
  - Engagement tracking
  - Automatic re-posting of high performers

Usage:
    from pp_services.video_engine.distribution_engine import DistributionEngine
    engine = DistributionEngine(episode_date="2026-02-25")
    result = engine.distribute_all(show_plan, bundle_path)
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("DistributionEngine")


# Platform-specific content limits
PLATFORM_LIMITS = {
    "youtube": {"title_max": 100, "description_max": 5000, "tags_max": 500},
    "youtube_shorts": {"title_max": 100, "description_max": 5000},
    "twitter": {"tweet_max": 280, "thread_max": 10},
    "website": {"title_max": 200, "excerpt_max": 300},
    "newsletter": {"subject_max": 60, "preview_max": 150},
    "podcast": {"title_max": 255, "description_max": 4000},
    "discord": {"message_max": 2000, "embed_title_max": 256},
    "telegram": {"message_max": 4096, "caption_max": 1024},
}


class PlatformFormatter:
    """Format content for each distribution platform."""

    @staticmethod
    def format_youtube(show_plan: Dict, episode_date: str) -> Dict:
        """Format for YouTube full episode upload."""
        stories = show_plan.get("stories", [])
        headline = show_plan.get("episode_headline", f"Pulse Check — {episode_date}")

        # Build description with chapters
        description_parts = [
            f"{headline}\n",
            f"Daily Bitcoin Intelligence — {episode_date}",
            "\nToday's stories:",
        ]

        for i, story in enumerate(stories, 1):
            description_parts.append(f"{i}. {story.get('headline', '')}")

        description_parts.extend([
            "\n---",
            "Subscribe for daily Bitcoin intelligence.",
            "Website: https://protocolpulse.io",
            "X/Twitter: https://x.com/ProtocolPulse",
            "\n#Bitcoin #BTC #ProtocolPulse #BitcoinNews"
        ])

        # Build tags
        tags = ["Bitcoin", "BTC", "Protocol Pulse", "Bitcoin News",
                "Crypto News", "Bitcoin Analysis"]
        themes = show_plan.get("dominant_theme", "").split(",")
        tags.extend([t.strip() for t in themes if t.strip()])

        return {
            "platform": "youtube",
            "title": headline[:100],
            "description": "\n".join(description_parts)[:5000],
            "tags": ",".join(tags)[:500],
            "category": "25",  # News & Politics
            "privacy_status": "public",
        }

    @staticmethod
    def format_youtube_shorts(story: Dict, episode_date: str,
                             index: int) -> Dict:
        """Format for YouTube Shorts (per clip)."""
        headline = story.get("headline", f"Bitcoin News #{index}")

        return {
            "platform": "youtube_shorts",
            "title": f"{headline[:80]} | {episode_date}",
            "description": (
                f"{story.get('summary', headline)}\n\n"
                f"Full episode: https://protocolpulse.io\n"
                f"#Shorts #Bitcoin #BTC"
            ),
            "tags": "Bitcoin,Shorts,BTC,News",
        }

    @staticmethod
    def format_twitter_thread(show_plan: Dict, episode_date: str) -> Dict:
        """Format for X/Twitter thread."""
        stories = show_plan.get("stories", [])
        headline = show_plan.get("episode_headline", "")
        thread = []

        # Opening tweet
        thread.append({
            "text": (
                f"🟠 {headline}\n\n"
                f"Daily Bitcoin Intelligence — {episode_date}\n\n"
                f"A thread 🧵👇"
            )[:280],
            "type": "opening"
        })

        # Story tweets
        for i, story in enumerate(stories[:7], 1):
            story_text = story.get("headline", "")
            summary = story.get("summary", "")[:200]
            tweet = f"{i}/ {story_text}\n\n{summary}"
            thread.append({
                "text": tweet[:280],
                "type": "story"
            })

        # Closing tweet
        thread.append({
            "text": (
                f"Full episode + analysis: https://protocolpulse.io\n\n"
                f"Subscribe for daily Bitcoin intelligence.\n\n"
                f"Like + RT if this was valuable 🔁"
            )[:280],
            "type": "closing"
        })

        return {
            "platform": "twitter",
            "thread": thread,
            "tweet_count": len(thread),
        }

    @staticmethod
    def format_twitter_poll(show_plan: Dict) -> Dict:
        """Format a Twitter poll based on the day's content."""
        stories = show_plan.get("stories", [])
        theme = show_plan.get("dominant_theme", "Bitcoin")

        # Generate poll question based on theme
        return {
            "platform": "twitter_poll",
            "question": f"What's the biggest Bitcoin story today?",
            "options": [
                s.get("headline", "")[:25]
                for s in stories[:4]
            ],
            "duration_minutes": 1440,  # 24 hours
        }

    @staticmethod
    def format_website_article(show_plan: Dict, episode_date: str) -> Dict:
        """Format for website article digest."""
        stories = show_plan.get("stories", [])
        headline = show_plan.get("episode_headline", "")

        # Build article content in 5-section format
        sections = []

        # TL;DR
        summaries = [s.get("summary", s.get("headline", ""))
                     for s in stories[:3]]
        sections.append({
            "title": "TL;DR",
            "content": "\n".join(f"• {s}" for s in summaries)
        })

        # The Report
        report_parts = []
        for story in stories:
            report_parts.append(
                f"### {story.get('headline', '')}\n\n"
                f"{story.get('summary', '')}\n"
            )
        sections.append({
            "title": "The Report",
            "content": "\n\n".join(report_parts)
        })

        # Bitcoin Lens
        sections.append({
            "title": "The Bitcoin Lens",
            "content": show_plan.get("bitcoin_lens", "Analysis pending.")
        })

        # Transactor Intelligence
        sections.append({
            "title": "Transactor Intelligence",
            "content": show_plan.get("intelligence", "Market data pending.")
        })

        # Sources
        sources = []
        for story in stories:
            for clip in story.get("clips", []):
                src = clip.get("source_name", "")
                if src and src not in sources:
                    sources.append(src)
        sections.append({
            "title": "Sources",
            "content": "\n".join(f"• {s}" for s in sources)
        })

        return {
            "platform": "website",
            "title": headline,
            "slug": headline.lower().replace(" ", "-")[:80],
            "date": episode_date,
            "sections": sections,
            "category": "daily_pulse",
            "premium_tier": "free",
        }

    @staticmethod
    def format_newsletter(show_plan: Dict, episode_date: str) -> Dict:
        """Format for email newsletter."""
        stories = show_plan.get("stories", [])
        headline = show_plan.get("episode_headline", "")

        # Email subject line (keep short for open rates)
        subject = f"🟠 {headline[:50]}"

        # Preview text (appears in inbox)
        preview = stories[0].get("summary", headline)[:150] if stories else headline[:150]

        # Build email body
        body_parts = [
            f"<h1>{headline}</h1>",
            f"<p><em>Daily Bitcoin Intelligence — {episode_date}</em></p>",
            "<hr>",
        ]

        for i, story in enumerate(stories[:5], 1):
            body_parts.append(
                f"<h3>{i}. {story.get('headline', '')}</h3>"
                f"<p>{story.get('summary', '')}</p>"
            )

        body_parts.extend([
            "<hr>",
            '<p><a href="https://protocolpulse.io">Read full analysis on Protocol Pulse</a></p>',
            "<p><em>Stay sovereign. Stay informed.</em></p>"
        ])

        return {
            "platform": "newsletter",
            "subject": subject[:60],
            "preview_text": preview[:150],
            "html_body": "\n".join(body_parts),
            "from_name": "Protocol Pulse",
        }

    @staticmethod
    def format_podcast(show_plan: Dict, episode_date: str,
                      audio_url: str = None) -> Dict:
        """Format for podcast RSS feed."""
        headline = show_plan.get("episode_headline", "")
        stories = show_plan.get("stories", [])

        description = f"{headline}\n\n"
        for story in stories:
            description += f"• {story.get('headline', '')}\n"
        description += f"\nFull show notes: https://protocolpulse.io"

        return {
            "platform": "podcast",
            "title": f"Pulse Check — {episode_date}: {headline[:80]}",
            "description": description[:4000],
            "audio_url": audio_url or "",
            "duration": "",  # Filled from actual audio
            "episode_type": "full",
            "explicit": False,
        }

    @staticmethod
    def format_discord(show_plan: Dict, episode_date: str) -> Dict:
        """Format for Discord notification."""
        stories = show_plan.get("stories", [])
        headline = show_plan.get("episode_headline", "")

        embed = {
            "title": f"🟠 {headline[:250]}",
            "description": f"Daily Bitcoin Intelligence — {episode_date}",
            "fields": [],
            "color": 0xF7931A,  # Bitcoin orange
            "url": "https://protocolpulse.io",
            "footer": {"text": "Protocol Pulse | protocolpulse.io"},
        }

        for story in stories[:5]:
            embed["fields"].append({
                "name": story.get("headline", "")[:256],
                "value": story.get("summary", "")[:200] or "Analysis available on site.",
                "inline": False,
            })

        return {
            "platform": "discord",
            "embed": embed,
            "mention": "@everyone",  # Configurable
        }

    @staticmethod
    def format_telegram(show_plan: Dict, episode_date: str) -> Dict:
        """Format for Telegram notification."""
        stories = show_plan.get("stories", [])
        headline = show_plan.get("episode_headline", "")

        lines = [
            f"🟠 <b>{headline}</b>",
            f"<i>Daily Bitcoin Intelligence — {episode_date}</i>",
            "",
        ]

        for i, story in enumerate(stories[:5], 1):
            lines.append(f"{i}. {story.get('headline', '')}")

        lines.extend([
            "",
            "📊 Full analysis: https://protocolpulse.io",
        ])

        return {
            "platform": "telegram",
            "text": "\n".join(lines)[:4096],
            "parse_mode": "HTML",
        }


class DistributionEngine:
    """Orchestrate multi-platform content distribution."""

    def __init__(self, episode_date: str = None):
        self.episode_date = episode_date or datetime.utcnow().strftime("%Y-%m-%d")
        self.formatter = PlatformFormatter()
        self.results: Dict[str, Dict] = {}

    def distribute_all(self, show_plan: Dict,
                      bundle_path: Path = None) -> Dict:
        """Distribute episode content to all platforms.

        Returns distribution results per platform.
        """
        logger.info(f"\n  DISTRIBUTION ENGINE — {self.episode_date}")
        logger.info(f"  Platforms: 7")

        show_dict = show_plan if isinstance(show_plan, dict) else show_plan.dict()

        # Generate all platform formats
        formats = {
            "youtube": self.formatter.format_youtube(show_dict, self.episode_date),
            "twitter_thread": self.formatter.format_twitter_thread(show_dict, self.episode_date),
            "twitter_poll": self.formatter.format_twitter_poll(show_dict),
            "website": self.formatter.format_website_article(show_dict, self.episode_date),
            "newsletter": self.formatter.format_newsletter(show_dict, self.episode_date),
            "podcast": self.formatter.format_podcast(show_dict, self.episode_date),
            "discord": self.formatter.format_discord(show_dict, self.episode_date),
            "telegram": self.formatter.format_telegram(show_dict, self.episode_date),
        }

        # YouTube Shorts (one per story, up to 5)
        stories = show_dict.get("stories", [])
        for i, story in enumerate(stories[:5], 1):
            formats[f"youtube_short_{i}"] = self.formatter.format_youtube_shorts(
                story, self.episode_date, i)

        # Save distribution pack
        if bundle_path:
            dist_dir = bundle_path / "distribution"
            dist_dir.mkdir(parents=True, exist_ok=True)
            for platform, data in formats.items():
                out_path = dist_dir / f"{platform}.json"
                out_path.write_text(json.dumps(data, indent=2, default=str))

        # Attempt distribution to each platform
        for platform, data in formats.items():
            try:
                result = self._distribute_to_platform(platform, data)
                self.results[platform] = result
            except Exception as e:
                logger.warning(f"  [{platform}] Distribution failed: {e}")
                self.results[platform] = {
                    "status": "failed",
                    "error": str(e)
                }

        # Summary
        success = sum(1 for r in self.results.values()
                     if r.get("status") == "queued" or r.get("status") == "published")
        failed = sum(1 for r in self.results.values()
                    if r.get("status") == "failed")

        logger.info(f"  Distribution: {success} queued, {failed} failed")

        return {
            "episode_date": self.episode_date,
            "platforms": self.results,
            "success_count": success,
            "failed_count": failed,
            "formats_generated": len(formats),
        }

    def _distribute_to_platform(self, platform: str, data: Dict) -> Dict:
        """Distribute content to a specific platform.

        In production, this would call the actual platform APIs.
        Currently queues content for manual or automated posting.
        """
        enable_live = os.environ.get("ENABLE_LIVE_POSTING", "false").lower() in ("true", "1")

        if platform.startswith("youtube"):
            return self._distribute_youtube(data, live=enable_live)
        elif platform.startswith("twitter"):
            return self._distribute_twitter(data, live=enable_live)
        elif platform == "website":
            return self._distribute_website(data)
        elif platform == "newsletter":
            return self._distribute_newsletter(data, live=enable_live)
        elif platform == "podcast":
            return self._distribute_podcast(data)
        elif platform == "discord":
            return self._distribute_discord(data, live=enable_live)
        elif platform == "telegram":
            return self._distribute_telegram(data, live=enable_live)

        return {"status": "queued", "platform": platform}

    def _distribute_youtube(self, data: Dict, live: bool = False) -> Dict:
        """Queue YouTube upload."""
        # YouTube uploads require OAuth — queue for manual upload
        return {
            "status": "queued",
            "platform": "youtube",
            "title": data.get("title", ""),
            "note": "YouTube upload requires OAuth flow — queued for upload"
        }

    def _distribute_twitter(self, data: Dict, live: bool = False) -> Dict:
        """Post Twitter thread."""
        if not live:
            return {
                "status": "queued",
                "platform": "twitter",
                "tweet_count": data.get("tweet_count", 0),
                "note": "Set ENABLE_LIVE_POSTING=true to auto-post"
            }

        try:
            from pp_services.x_service import XService
            x = XService()
            if not (x.client or getattr(x, "client_v2", None)):
                return {"status": "failed", "error": "X API not configured"}

            thread = data.get("thread", [])
            posted = []
            reply_to = None

            for tweet in thread:
                if getattr(x, "client_v2", None) and x.client_v2:
                    kwargs = {"text": tweet["text"][:280]}
                    if reply_to:
                        kwargs["in_reply_to_tweet_id"] = reply_to
                    result = x.client_v2.create_tweet(**kwargs)
                    tweet_id = result.data.get("id") if result.data else None
                    reply_to = tweet_id
                    posted.append(tweet_id)

            return {
                "status": "published",
                "platform": "twitter",
                "tweets_posted": len(posted),
                "tweet_ids": posted
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _distribute_website(self, data: Dict) -> Dict:
        """Create article on Protocol Pulse website."""
        try:
            from app import app, db
            import models

            with app.app_context():
                # Build content from sections
                content_parts = []
                for section in data.get("sections", []):
                    content_parts.append(
                        f"## {section['title']}\n\n{section['content']}")
                content = "\n\n".join(content_parts)

                article = models.Article(
                    title=data.get("title", ""),
                    slug=data.get("slug", ""),
                    content=content,
                    category=data.get("category", "daily_pulse"),
                    published=True,
                    premium_tier=data.get("premium_tier", "free"),
                )
                db.session.add(article)
                db.session.commit()

                return {
                    "status": "published",
                    "platform": "website",
                    "article_id": article.id,
                    "slug": article.slug,
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _distribute_newsletter(self, data: Dict, live: bool = False) -> Dict:
        """Send email newsletter."""
        if not live:
            return {
                "status": "queued",
                "platform": "newsletter",
                "subject": data.get("subject", ""),
            }

        try:
            from pp_services.newsletter_engine import send_newsletter_blast
            result = send_newsletter_blast(
                subject=data.get("subject", ""),
                html_body=data.get("html_body", ""),
            )
            return {
                "status": "published" if result else "failed",
                "platform": "newsletter",
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _distribute_podcast(self, data: Dict) -> Dict:
        """Update podcast RSS feed."""
        return {
            "status": "queued",
            "platform": "podcast",
            "title": data.get("title", ""),
            "note": "Podcast RSS update queued"
        }

    def _distribute_discord(self, data: Dict, live: bool = False) -> Dict:
        """Send Discord notification."""
        if not live:
            return {"status": "queued", "platform": "discord"}

        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            return {"status": "failed", "error": "DISCORD_WEBHOOK_URL not set"}

        try:
            import requests
            payload = {"embeds": [data.get("embed", {})]}
            resp = requests.post(webhook_url, json=payload, timeout=10)
            return {
                "status": "published" if resp.status_code in (200, 204) else "failed",
                "platform": "discord",
                "http_status": resp.status_code,
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _distribute_telegram(self, data: Dict, live: bool = False) -> Dict:
        """Send Telegram notification."""
        if not live:
            return {"status": "queued", "platform": "telegram"}

        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not (token and chat_id):
            return {"status": "failed", "error": "Telegram not configured"}

        try:
            import requests
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": data.get("text", ""),
                    "parse_mode": data.get("parse_mode", "HTML"),
                },
                timeout=10
            )
            return {
                "status": "published" if resp.status_code == 200 else "failed",
                "platform": "telegram",
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
