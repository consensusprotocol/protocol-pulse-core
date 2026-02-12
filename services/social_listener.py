"""
Social Listener: 24/7 monitoring of high-value X handles.
When a priority target (e.g. Saylor, Lyn Alden) posts, detects the tweet, generates a branded
cyberpunk-style image using Gemini Imagen 3, and crafts a Walter Cronkite-style one-liner reply
for engagement. (Image generation requires Imagen API; reply can use OpenAI/Claude.)
"""

import logging
from typing import Dict, Optional, List
import os

from services.ollama_runtime import generate as ollama_generate

logger = logging.getLogger(__name__)

# Priority targets for reply engagement (Replit spec)
PRIORITY_HANDLES = [
    "saylor", "LynAldenContact", "saifedean", "jack", "lopp", "natbrunell",
    "JeffBooth", "PrestonPysh", "MartyBent", "pierre_rochard",
]


class SocialListener:
    def __init__(self):
        self._x = None
        self._ai = None
        self._imagen = None

    def get_recent_posts_from_priority(self, hours_back: int = 2) -> List[Dict]:
        """Fetch recent posts from PRIORITY_HANDLES. Returns list of { handle, post_id, text, posted_at }."""
        try:
            from services.sentiment_tracker_service import SentimentTrackerService
            tracker = SentimentTrackerService()
            posts = tracker.fetch_x_posts(hours_back=hours_back)
            return [
                {"handle": p.get("author_handle"), "post_id": p.get("post_id"), "text": p.get("content"), "posted_at": p.get("posted_at")}
                for p in posts if (p.get("author_handle") or "").lower() in [h.lower() for h in PRIORITY_HANDLES]
            ]
        except Exception as e:
            logger.warning("SocialListener get_recent_posts: %s", e)
            return []

    def generate_reply_one_liner(self, tweet_text: str, author_handle: str) -> str:
        """Generate a Walter Cronkite-style one-liner reply (authoritative, thoughtful, under 280 chars)."""
        prompt = f"""You are Protocol Pulse's social voice: Walter Cronkite style — authoritative, thoughtful, journalistic.

TWEET from @{author_handle}:
{tweet_text}

Write a single reply that adds value (insight or context). One sentence, max 280 chars. No hashtags, no emojis. Do not start with @handle."""
        preferred = os.environ.get("SOCIAL_LISTENER_MODEL", "llama3.3").strip()
        local = ollama_generate(
            prompt=prompt,
            preferred_model=preferred,
            options={"temperature": 0.5, "num_predict": 90},
            timeout=60,
        )
        if local:
            return local.splitlines()[0].strip()[:280]
        try:
            from services.ai_service import AIService
            ai = AIService()
            return (ai.generate_content_openai(prompt) or "").strip()[:280]
        except Exception as e:
            logger.warning("generate_reply_one_liner failed: %s", e)
            return ""

    def generate_cyberpunk_image(self, tweet_text: str, author_handle: str) -> Optional[str]:
        """
        Generate a branded cyberpunk-style image for the tweet (e.g. Gemini Imagen 3).
        Returns local file path or URL, or None if image generation not configured.
        """
        try:
            from services.gemini_service import gemini_service
            if hasattr(gemini_service, "generate_image") or hasattr(gemini_service, "imagen"):
                # Placeholder: actual Imagen call depends on Gemini image API
                logger.info("SocialListener: image generation stub for @%s", author_handle)
                return None
        except Exception as e:
            logger.debug("Cyberpunk image not available: %s", e)
        return None

    def process_new_priority_post(self, post: Dict) -> Dict:
        """
        For one priority post: optionally generate image, generate reply, return { reply_text, image_path }.
        Caller is responsible for posting reply to X.
        """
        reply_text = self.generate_reply_one_liner(post.get("text", ""), post.get("handle", ""))
        image_path = self.generate_cyberpunk_image(post.get("text", ""), post.get("handle", ""))
        return {"reply_text": reply_text, "image_path": image_path}


social_listener = SocialListener()
