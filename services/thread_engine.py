"""
THREAD ENGINE — Weekly deep-dive threads for massive reach.
============================================================
Single tweets cap at ~50K impressions.
Threads regularly hit 500K+.

Generates a 5-7 tweet thread on the biggest story of the week,
using Intel Briefing data for ammunition.
"""

import os
import sys
import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List

logger = logging.getLogger("thread_engine")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ThreadEngine:

    def __init__(self):
        from services.comment_radar import CommentRadar
        self.radar = CommentRadar()
        self.x_client = self.radar.x_client
        self.accounts = self.radar.cfg.get("target_accounts", [])
        logger.info("ThreadEngine initialized")

    def _find_week_biggest_story(self) -> Dict:
        """Scan discourse for the dominant story of the week."""
        all_posts = []
        sampled = random.sample(self.accounts, min(15, len(self.accounts)))

        for i, handle in enumerate(sampled):
            try:
                data = self.x_client.get_user_tweets(handle, max_results=10)
                if data is None:
                    time.sleep(5)
                    data = self.x_client.get_user_tweets(handle, max_results=10)
                if not data or "data" not in data:
                    continue

                for t in data["data"]:
                    m = t.get("public_metrics", {})
                    total = m.get("like_count", 0) + m.get("retweet_count", 0) * 2
                    if total > 50:
                        all_posts.append({
                            "text": t.get("text", ""),
                            "author": handle,
                            "engagement": total,
                        })

                if i < len(sampled) - 1:
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"Error scanning @{handle}: {e}")

        all_posts.sort(key=lambda x: x["engagement"], reverse=True)
        
        # Use Grok to identify the #1 story
        import requests
        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return {}

        posts_block = "\n".join(f"@{p['author']} ({int(p['engagement'])}): {p['text'][:150]}" for p in all_posts[:12])

        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-3-mini",
                    "messages": [
                        {"role": "system", "content": "Identify the single biggest Bitcoin story this week from these posts. Return JSON only: {\"story\": \"title\", \"summary\": \"3 sentences\", \"key_data\": [\"fact1\", \"fact2\", \"fact3\"], \"why_it_matters\": \"1 sentence\"}"},
                        {"role": "user", "content": f"Top Bitcoin posts:\n{posts_block}"}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7
                },
                timeout=30
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            story = json.loads(raw)
            logger.info(f"Week's biggest story: {story.get('story', 'unknown')}")
            return story

        except Exception as e:
            logger.error(f"Story identification failed: {e}")
            return {}

    def _generate_thread(self, story: Dict) -> List[str]:
        """Generate a 5-7 tweet thread on the biggest story."""
        import requests
        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return []

        system_prompt = """You write viral Twitter threads about Bitcoin. The thread format is the most powerful content format on X for reach and engagement.

THREAD STRUCTURE:
- Tweet 1 (HOOK): Stops the scroll. Bold claim, surprising number, or provocative question. Must make someone think "wait, what?" End with "A thread. 🧵" (only emoji allowed in entire thread)
- Tweet 2-3: The setup. Context most people are missing. Use specific numbers.
- Tweet 4-5: The insight. Your unique angle. What everyone else is getting wrong.
- Tweet 6: The implication. What happens next. Make a prediction or pose the question.
- Tweet 7 (CLOSER): One sharp sentence. Bookmark-worthy. Should work as a standalone tweet.

VOICE:
- Fund manager who reads everything and says very little
- Every tweet must stand alone AND advance the thread
- Short sentences. Fragments fine. No filler.
- No emojis except 🧵 in tweet 1
- No hashtags. No @mentions.
- Suggestive over declarative

RULES:
- Each tweet MUST be under 280 characters
- Never invent numbers. Use the data provided.
- Never preach about Bitcoin. Show the picture, let reader conclude.
- Write like someone who's about to close their phone and go run a fund

Return JSON array of strings: ["tweet 1", "tweet 2", ..., "tweet 7"]
No markdown. No backticks."""

        user_prompt = f"""Write a 7-tweet thread about:

Story: {story.get('story', '')}
Summary: {story.get('summary', '')}
Key data: {', '.join(story.get('key_data', []))}
Why it matters: {story.get('why_it_matters', '')}"""

        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-3-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.85
                },
                timeout=60
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            thread = json.loads(raw)
            
            # Enforce 280 char limit
            thread = [t[:280] for t in thread if isinstance(t, str)]
            logger.info(f"Generated {len(thread)}-tweet thread")
            return thread

        except Exception as e:
            logger.error(f"Thread generation failed: {e}")
            return []

    def _post_thread(self, thread: List[str]) -> Dict:
        """Post the thread as a reply chain."""
        if os.environ.get("ENABLE_TWEETS", "false").lower() != "true":
            logger.info(f"[DISABLED] Would post thread ({len(thread)} tweets)")
            for i, t in enumerate(thread):
                logger.info(f"  [{i+1}] {t[:80]}")
            return {"success": False, "reason": "tweets_disabled", "thread": thread}

        try:
            from services.x_service import XService
            x = XService()
            if not x.client_v2:
                return {"success": False, "reason": "no_client"}

            posted_ids = []
            parent_id = None

            for i, tweet_text in enumerate(thread):
                try:
                    if parent_id:
                        r = x.client_v2.create_tweet(text=tweet_text, in_reply_to_tweet_id=parent_id)
                    else:
                        r = x.client_v2.create_tweet(text=tweet_text)

                    if r and r.data:
                        tweet_id = str(r.data["id"])
                        posted_ids.append(tweet_id)
                        parent_id = tweet_id
                        logger.info(f"Thread [{i+1}/{len(thread)}] posted: {tweet_text[:60]}")
                        time.sleep(3)  # Space between thread tweets
                    else:
                        logger.error(f"Thread [{i+1}] failed to post")
                        break

                except Exception as e:
                    logger.error(f"Thread [{i+1}] error: {e}")
                    break

            # Log the thread
            self._log_thread(thread, posted_ids)
            return {"success": True, "tweets_posted": len(posted_ids), "thread_ids": posted_ids}

        except Exception as e:
            logger.error(f"Thread posting failed: {e}")
            return {"success": False, "error": str(e)}

    def _log_thread(self, thread, posted_ids):
        """Log posted threads."""
        log_file = "data/thread_log.json"
        os.makedirs("data", exist_ok=True)
        try:
            log = json.load(open(log_file)) if os.path.exists(log_file) else {"threads": []}
        except:
            log = {"threads": []}
        
        log["threads"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tweet_count": len(thread),
            "posted_count": len(posted_ids),
            "hook": thread[0][:100] if thread else "",
            "ids": posted_ids,
        })
        log["threads"] = log["threads"][-50:]
        json.dump(log, open(log_file, "w"), indent=2)

    def run_weekly_thread(self) -> Dict:
        """Full cycle: find story → generate thread → post."""
        logger.info("Starting weekly thread generation...")

        story = self._find_week_biggest_story()
        if not story:
            return {"success": False, "reason": "no_story_found"}

        thread = self._generate_thread(story)
        if len(thread) < 3:
            return {"success": False, "reason": "thread_too_short"}

        result = self._post_thread(thread)
        result["story"] = story.get("story", "")
        return result


def run_weekly_thread():
    """Scheduler entry point."""
    try:
        engine = ThreadEngine()
        return engine.run_weekly_thread()
    except Exception as e:
        logger.error(f"Thread engine failed: {e}")
        return {"success": False, "error": str(e)}
