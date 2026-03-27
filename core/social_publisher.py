"""
Social Publisher — Auto-distribute content to Nostr + X on every publish.

Wraps existing nostr_publisher and x_automation_service into a single facade.
All calls are fire-and-forget: social failure NEVER blocks article/episode creation.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SocialPublisher:
    """Unified publisher for Nostr + X/Twitter."""

    BASE_URL = "https://protocolpulse.io/briefs"

    def __init__(self):
        self._nostr = None
        self._x = None
        self._init_nostr()
        self._init_x()

    # ── Init ──────────────────────────────────────────────────────────

    def _init_nostr(self):
        try:
            from nostr.nostr_publisher import publish_article as _na, publish_video as _nv
            self._nostr = {"article": _na, "video": _nv}
            logger.info("SocialPublisher: Nostr backend ready")
        except Exception as e:
            logger.warning("SocialPublisher: Nostr unavailable — %s", e)

    def _init_x(self):
        try:
            from services.x_automation_service import XAutomationService
            svc = XAutomationService()
            if svc.configured:
                self._x = svc
                logger.info("SocialPublisher: X/Twitter backend ready")
            else:
                logger.warning("SocialPublisher: X API keys not configured, skipping")
        except Exception as e:
            logger.warning("SocialPublisher: X unavailable — %s", e)

    # ── Nostr ─────────────────────────────────────────────────────────

    def nostr_publish_article(self, title: str, slug: str, content: str) -> Dict:
        if not self._nostr:
            logger.info("Nostr not configured, skipping article publish")
            return {"success": False, "error": "nostr_not_configured"}
        try:
            url = f"{self.BASE_URL}/{slug}"
            # Use first 200 chars of content as summary for the note
            summary = content[:200].replace("\n", " ").strip()
            full_content = f"{title}\n\n{summary}...\n\n{url}\n\n#Bitcoin #ProtocolPulse"
            return self._nostr["article"](title, full_content, url)
        except Exception as e:
            logger.error("Nostr article publish failed: %s", e)
            return {"success": False, "error": str(e)}

    def nostr_publish_episode(self, title: str, youtube_id: str) -> Dict:
        if not self._nostr:
            logger.info("Nostr not configured, skipping episode publish")
            return {"success": False, "error": "nostr_not_configured"}
        try:
            yt_url = f"https://youtu.be/{youtube_id}"
            return self._nostr["video"](title, yt_url)
        except Exception as e:
            logger.error("Nostr episode publish failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── X / Twitter ───────────────────────────────────────────────────

    def twitter_publish_article(self, title: str, slug: str, content: str) -> Dict:
        if not self._x:
            logger.info("X/Twitter not configured, skipping article publish")
            return {"success": False, "error": "x_not_configured"}
        try:
            url = f"{self.BASE_URL}/{slug}"
            return self._x.post_article(title, url)
        except Exception as e:
            logger.error("X article publish failed: %s", e)
            return {"success": False, "error": str(e)}

    def twitter_publish_episode(self, title: str, youtube_id: str) -> Dict:
        if not self._x:
            logger.info("X/Twitter not configured, skipping episode publish")
            return {"success": False, "error": "x_not_configured"}
        try:
            yt_url = f"https://youtu.be/{youtube_id}"
            tweet = f"NEW PULSE CHECK: {title}\n\nDaily Bitcoin intelligence briefing.\n\n{yt_url}\n\n#Bitcoin #PulseCheck"
            if len(tweet) > 280:
                tweet = f"NEW PULSE CHECK\n\n{yt_url}\n\n#Bitcoin #PulseCheck"
            return self._x.post_tweet(tweet)
        except Exception as e:
            logger.error("X episode publish failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Public API ────────────────────────────────────────────────────

    def publish_article(self, title: str, slug: str, content: str, tags: Optional[List[str]] = None) -> Dict:
        """Publish article to both Nostr and X. Never raises."""
        result = {"nostr": None, "twitter": None}
        try:
            result["nostr"] = self.nostr_publish_article(title, slug, content)
        except Exception as e:
            result["nostr"] = {"success": False, "error": str(e)}
            logger.error("Social publish (nostr) error: %s", e)
        try:
            result["twitter"] = self.twitter_publish_article(title, slug, content)
        except Exception as e:
            result["twitter"] = {"success": False, "error": str(e)}
            logger.error("Social publish (twitter) error: %s", e)

        nostr_ok = result["nostr"].get("success", False) if result["nostr"] else False
        x_ok = result["twitter"].get("success", False) if result["twitter"] else False
        logger.info("Social publish article '%s': nostr=%s, x=%s", title[:60], nostr_ok, x_ok)
        return result

    def publish_episode(self, title: str, youtube_id: str, description: str = "") -> Dict:
        """Publish episode to both Nostr and X. Never raises."""
        result = {"nostr": None, "twitter": None}
        try:
            result["nostr"] = self.nostr_publish_episode(title, youtube_id)
        except Exception as e:
            result["nostr"] = {"success": False, "error": str(e)}
            logger.error("Social publish (nostr) episode error: %s", e)
        try:
            result["twitter"] = self.twitter_publish_episode(title, youtube_id)
        except Exception as e:
            result["twitter"] = {"success": False, "error": str(e)}
            logger.error("Social publish (twitter) episode error: %s", e)

        nostr_ok = result["nostr"].get("success", False) if result["nostr"] else False
        x_ok = result["twitter"].get("success", False) if result["twitter"] else False
        logger.info("Social publish episode '%s': nostr=%s, x=%s", title[:60], nostr_ok, x_ok)
        return result
