"""
BOOKMARK BAIT — Tweets designed to be saved.
=============================================
Saves are the most underrated X metric.
They boost algorithmic reach silently because X treats saves
as high-intent engagement signals.

Format: "5 numbers that matter this week" / "one chart" / lists
"""

import os
import sys
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger("bookmark_bait")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class BookmarkBait:

    def __init__(self):
        from pp_services.comment_radar import CommentRadar
        self.radar = CommentRadar()
        self.x_client = self.radar.x_client
        self.accounts = self.radar.cfg.get("target_accounts", [])

    def _gather_week_data(self) -> str:
        """Scan recent discourse for data points."""
        all_posts = []
        sampled = random.sample(self.accounts, min(12, len(self.accounts)))

        for i, handle in enumerate(sampled):
            try:
                data = self.x_client.get_user_tweets(handle, max_results=5)
                if not data or "data" not in data:
                    continue
                for t in data["data"]:
                    m = t.get("public_metrics", {})
                    if m.get("like_count", 0) > 30:
                        all_posts.append(f"@{handle}: {t.get('text', '')[:200]}")
                if i < len(sampled) - 1:
                    time.sleep(2)
            except:
                pass

        return "\n".join(all_posts[:10])

    def generate_bookmark_tweet(self) -> Dict:
        """Generate a high-save-potential tweet."""
        import requests

        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return {"success": False}

        discourse = self._gather_week_data()

        templates = [
            "5 numbers Bitcoin maxis are watching this week",
            "the quiet shift nobody is talking about",
            "what the last 7 days actually told us",
            "3 things that changed this week (and 1 that didn't)",
            "the scorecard nobody asked for but everyone needs",
        ]
        template = random.choice(templates)

        system_prompt = f"""Write a tweet designed to be bookmarked/saved. The format is a compact, high-value list or observation that people want to reference later.

TEMPLATE STYLE: "{template}"

RULES:
- Use line breaks between items (not bullets, just new lines)
- Each line should be a standalone insight, under 40 characters
- The hook (first line) must stop the scroll
- 200-270 characters total
- No emojis except possibly one at the start for visual anchor
- No hashtags. No @mentions.
- Use real data/observations from the discourse provided
- Never invent specific numbers
- Should feel like a cheat sheet someone screenshots

OUTPUT: JSON only: {{"tweet": "the full tweet text", "confidence": 0.8}}"""

        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-3-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Current Bitcoin discourse:\n{discourse}"}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.9
                },
                timeout=45
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            tweet_text = result.get("tweet", "")[:280]
            if not tweet_text:
                return {"success": False}

            if os.environ.get("ENABLE_TWEETS", "false").lower() != "true":
                logger.info(f"[DISABLED] Bookmark bait: {tweet_text[:80]}")
                return {"success": False, "reason": "disabled", "would_post": tweet_text}

            from pp_services.x_service import post_tweet
            post_result = post_tweet(tweet_text)
            if post_result:
                logger.info(f"Posted bookmark bait: {tweet_text[:80]}")

                # Log it
                os.makedirs("data", exist_ok=True)
                log_file = "data/engagement_log.json"
                try:
                    log = json.load(open(log_file)) if os.path.exists(log_file) else {"posts": []}
                except:
                    log = {"posts": []}
                log["posts"].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "text": tweet_text, "strategy": "bookmark_bait",
                    "confidence": result.get("confidence", 0.8),
                })
                log["posts"] = log["posts"][-200:]
                json.dump(log, open(log_file, "w"), indent=2)

                return {"success": True, "text": tweet_text}

            return {"success": False, "reason": "post_failed"}

        except Exception as e:
            logger.error(f"Bookmark bait failed: {e}")
            return {"success": False, "error": str(e)}


def run_bookmark_bait():
    try:
        return BookmarkBait().generate_bookmark_tweet()
    except Exception as e:
        logger.error(f"Bookmark bait failed: {e}")
        return {"success": False, "error": str(e)}
