"""
Distribution Pack Generator
=============================
One episode bundle → content for 7 platforms.
Auto-generated from the show plan + assembled video.

Platforms:
  1. YouTube (title, description, tags, chapters)
  2. YouTube Shorts (per-short metadata)
  3. X Thread (bullets + poll)
  4. Website Digest (Markdown article)
  5. Newsletter (email digest)
  6. Podcast Show Notes (RSS description)
  7. X Poll (engagement + editorial memory)
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("DistributionPack")


class DistributionPackGenerator:
    """Generate content for all distribution platforms."""

    def __init__(self, show_plan: dict, date_str: str = None):
        self.plan = show_plan
        self.date_str = date_str or show_plan.get("episode_date",
                                                     datetime.utcnow().strftime("%Y-%m-%d"))
        self.date_display = self._format_date(self.date_str)

    def generate_all(self, bundle_path: Path = None) -> Dict[str, dict]:
        """Generate all distribution content. Save to bundle."""
        logger.info(f"\n{'='*60}")
        logger.info(f"DISTRIBUTION PACK")
        logger.info(f"{'='*60}\n")

        pack = {}

        pack["youtube"] = self._youtube_metadata()
        pack["shorts"] = self._shorts_metadata()
        pack["x_thread"] = self._x_thread()
        pack["website_digest"] = self._website_digest()
        pack["newsletter"] = self._newsletter()
        pack["podcast"] = self._podcast_shownotes()
        pack["x_poll"] = self._x_poll()

        logger.info(f"  Generated content for {len(pack)} platforms")

        # Save to bundle
        if bundle_path:
            dist_dir = bundle_path / "distribution_pack"
            dist_dir.mkdir(parents=True, exist_ok=True)

            for platform, content in pack.items():
                if isinstance(content, str):
                    ext = "md"
                    (dist_dir / f"{platform}.md").write_text(content)
                else:
                    (dist_dir / f"{platform}.json").write_text(
                        json.dumps(content, indent=2, default=str))

            logger.info(f"  Saved to: {dist_dir}")

        return pack

    def _youtube_metadata(self) -> dict:
        """Generate YouTube video metadata."""
        headline = self.plan.get("episode_headline", "Bitcoin Daily Highlights")
        stories = self.plan.get("stories", [])
        quick_hits = self.plan.get("quick_hits", [])

        # Build description
        desc_lines = [
            f"Pulse Check | {headline} — {self.date_display}",
            "",
            self.plan.get("cold_open_script", "")[:200],
            "",
            "Today's stories:"
        ]

        for story in stories:
            desc_lines.append(f"  {story.get('headline', '')}")

        if quick_hits:
            desc_lines.append("\nQuick Hits:")
            for qh in quick_hits:
                desc_lines.append(f"  {qh.get('headline', '')}")

        # Sources
        sources = set()
        for story in stories + quick_hits:
            for clip in story.get("clips", []):
                sources.add(clip.get("source_name", ""))

        if sources:
            desc_lines.append("\nFeatured sources:")
            for s in sorted(sources):
                if s:
                    desc_lines.append(f"  {s}")

        desc_lines.extend([
            "",
            "Subscribe for daily Bitcoin intelligence.",
            "Follow @ProtocolPulse on X",
            "",
            "Disclaimer: Not financial advice. Partner links may earn commission."
        ])

        # Themes for tags
        theme = self.plan.get("dominant_theme", "Bitcoin")
        tags = ["Bitcoin", "BTC", "Pulse Check", "Bitcoin News",
                theme, "Protocol Pulse", "crypto news", "Bitcoin daily"]

        return {
            "title": f"Pulse Check | {headline} — {self.date_display}",
            "description": "\n".join(desc_lines),
            "tags": tags,
            "category": "News & Politics",
            "privacy": "public"
        }

    def _shorts_metadata(self) -> List[dict]:
        """Generate metadata for each vertical short."""
        shorts = []
        for i, short in enumerate(self.plan.get("shorts_plan", [])):
            hook = short.get("hook_text", "Bitcoin Update")
            shorts.append({
                "index": i,
                "title": f"{hook} | Pulse Check #{self.date_str}",
                "description": (
                    f"Full Pulse Check: link in bio\n"
                    f"#Bitcoin #BTC #PulseCheck #shorts"
                ),
                "hook_text": hook
            })
        return shorts

    def _x_thread(self) -> dict:
        """Generate X/Twitter thread."""
        headline = self.plan.get("episode_headline", "")
        stories = self.plan.get("stories", [])
        quick_hits = self.plan.get("quick_hits", [])
        svn = self.plan.get("signal_vs_noise", {})

        # Main tweet
        main_tweet = (
            f"PULSE CHECK — {self.date_display}\n\n"
            f"{headline}\n\n"
            f"Today's 5 bullets:\n"
        )

        bullets = []
        for i, story in enumerate(stories[:3], 1):
            bullets.append(f"{i}. {story.get('headline', '')}")

        if svn.get("signal"):
            bullets.append(f"{len(bullets)+1}. Signal: {svn['signal'][:80]}")
        if svn.get("wildcard"):
            bullets.append(f"{len(bullets)+1}. Wildcard: {svn['wildcard'][:80]}")

        main_tweet += "\n".join(bullets[:5])

        # Reply tweets
        replies = []
        for story in stories:
            wrap = story.get("narrator_wrap_script", "")
            if wrap:
                replies.append(wrap[:280])

        return {
            "main_tweet": main_tweet,
            "replies": replies,
            "poll": {
                "question": "Which story deserves a deep dive tomorrow?",
                "options": [s.get("headline", "")[:25] for s in stories[:3]] +
                           ["Viewer suggestion"]
            }
        }

    def _website_digest(self) -> str:
        """Generate Markdown article for protocolpulse.io."""
        headline = self.plan.get("episode_headline", "")
        stories = self.plan.get("stories", [])
        svn = self.plan.get("signal_vs_noise", {})
        market = ""  # Will be filled by caller if available

        lines = [
            f"# Pulse Check — {self.date_display}",
            f"## {headline}",
            "",
            f"*{self.plan.get('cold_open_script', '')}*",
            ""
        ]

        for story in stories:
            lines.append(f"### {story.get('headline', '')}")
            lines.append("")
            lines.append(story.get("narrator_intro_script", ""))
            lines.append("")

            wrap = story.get("narrator_wrap_script")
            if wrap:
                lines.append(f"**Bottom line:** {wrap}")
                lines.append("")

        # Signal vs Noise
        if svn:
            lines.append("### Signal vs Noise")
            lines.append(f"- **Signal:** {svn.get('signal', '')}")
            lines.append(f"- **Noise:** {svn.get('noise', '')}")
            lines.append(f"- **Wildcard:** {svn.get('wildcard', '')}")
            lines.append("")

        # Sources
        sources = set()
        for story in stories:
            for clip in story.get("clips", []):
                name = clip.get("source_name", "")
                vid = clip.get("source_id", "")
                if name and vid:
                    sources.add(f"[{name}](https://youtube.com/watch?v={vid})")

        if sources:
            lines.append("### Sources")
            for s in sorted(sources):
                lines.append(f"- {s}")

        return "\n".join(lines)

    def _newsletter(self) -> str:
        """Generate email newsletter digest (90-second read)."""
        headline = self.plan.get("episode_headline", "")
        stories = self.plan.get("stories", [])
        svn = self.plan.get("signal_vs_noise", {})
        watchlist = self.plan.get("tomorrows_watchlist", [])

        lines = [
            f"# Pulse Check — {self.date_display}",
            "",
            f"**{headline}**",
            "",
            self.plan.get("cold_open_script", "")[:300],
            ""
        ]

        # Lead takeaway
        if stories:
            lead = stories[0]
            lines.append(f"**Lead:** {lead.get('headline', '')}")
            wrap = lead.get("narrator_wrap_script", "")
            if wrap:
                lines.append(wrap[:200])
            lines.append("")

        # Quick hits
        for story in stories[1:]:
            lines.append(f"- **{story.get('headline', '')}**: "
                         f"{story.get('narrator_intro_script', '')[:100]}")

        lines.append("")

        # Signal/Noise
        if svn.get("signal"):
            lines.append(f"**Signal:** {svn['signal']}")
        if svn.get("noise"):
            lines.append(f"**Noise:** {svn['noise']}")

        # Tomorrow's watchlist
        if watchlist:
            lines.append("")
            lines.append("**Tomorrow's Watchlist:**")
            for item in watchlist[:3]:
                lines.append(f"- {item}")

        lines.append("")
        lines.append("Watch the full episode: [link]")

        return "\n".join(lines)

    def _podcast_shownotes(self) -> dict:
        """Generate podcast show notes for RSS feed."""
        headline = self.plan.get("episode_headline", "")
        stories = self.plan.get("stories", [])

        description = f"Pulse Check — {self.date_display}: {headline}\n\n"
        description += self.plan.get("cold_open_script", "")[:300] + "\n\n"

        description += "Stories:\n"
        for story in stories:
            description += f"- {story.get('headline', '')}\n"

        return {
            "title": f"Pulse Check | {headline} — {self.date_display}",
            "description": description,
            "episode_type": "full",
            "explicit": False
        }

    def _x_poll(self) -> dict:
        """Generate X poll for engagement + editorial memory feedback."""
        stories = self.plan.get("stories", [])
        options = [s.get("headline", "")[:25] for s in stories[:3]]
        options.append("Viewer suggestion")

        return {
            "question": "Which Pulse Check story deserves a deep dive tomorrow?",
            "options": options[:4],
            "duration_hours": 24
        }

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Format YYYY-MM-DD to display format."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except Exception:
            return date_str
