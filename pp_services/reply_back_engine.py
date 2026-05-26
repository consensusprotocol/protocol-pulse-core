"""
REPLY-BACK ENGINE — Respond to replies on our own tweets.
==========================================================
The algorithm LOVES reply chains. A tweet with responses from the 
original author gets 3-5x the reach of an abandoned one.

Strategy:
- Fetch our recent tweets
- Find replies with highest engagement
- Generate witty, on-brand responses
- Reply to 2-3 best replies per tweet
- Never reply to trolls or spam
"""

import os
import sys
import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List

logger = logging.getLogger("reply_back")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROTOCOL_PULSE_USERNAME = "ProtocolPulse"


class ReplyBackEngine:

    def __init__(self):
        from pp_services.comment_radar import CommentRadar
        self.radar = CommentRadar()
        self.x_client = self.radar.x_client
        logger.info("ReplyBackEngine initialized")

    def _get_our_recent_tweets(self, max_tweets=10) -> List[Dict]:
        """Fetch Protocol Pulse's recent tweets."""
        try:
            data = self.x_client.get_user_tweets(PROTOCOL_PULSE_USERNAME, max_results=max_tweets)
            if not data or "data" not in data:
                return []
            
            tweets = []
            for t in data["data"]:
                m = t.get("public_metrics", {})
                # Only engage with tweets that got replies
                if m.get("reply_count", 0) >= 1:
                    tweets.append({
                        "id": t["id"],
                        "text": t.get("text", ""),
                        "metrics": m,
                        "reply_count": m.get("reply_count", 0),
                    })
            
            tweets.sort(key=lambda x: x["reply_count"], reverse=True)
            logger.info(f"Found {len(tweets)} of our tweets with replies")
            return tweets

        except Exception as e:
            logger.error(f"Failed to fetch our tweets: {e}")
            return []

    def _get_best_replies(self, tweet_id: str, max_replies=5) -> List[Dict]:
        """Get the best replies to one of our tweets."""
        try:
            data = self.x_client.get_conversation_replies(tweet_id)
            if not data or "data" not in data:
                return []

            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])} if data else {}
            
            replies = []
            for r in data.get("data", []):
                m = r.get("public_metrics", {})
                likes = m.get("like_count", 0)
                text = r.get("text", "")
                author_id = r.get("author_id", "")
                author = users.get(author_id, {}).get("username", "unknown")
                
                # Skip our own replies
                if author.lower() == PROTOCOL_PULSE_USERNAME.lower():
                    continue
                
                # Skip low-effort or toxic replies
                if len(text) < 10:
                    continue
                if any(bad in text.lower() for bad in ["scam", "rug", "shill", "ratio", "L take", "trash"]):
                    continue
                
                replies.append({
                    "id": r["id"],
                    "text": text,
                    "author": author,
                    "likes": likes,
                    "engagement": likes + m.get("reply_count", 0),
                })

            replies.sort(key=lambda x: x["engagement"], reverse=True)
            return replies[:max_replies]

        except Exception as e:
            logger.warning(f"Failed to get replies for {tweet_id}: {e}")
            return []

    def _check_already_replied(self, tweet_id: str) -> bool:
        """Check if we already replied to this specific reply."""
        log_file = "data/reply_back_log.json"
        try:
            if os.path.exists(log_file):
                log = json.load(open(log_file))
                return tweet_id in log.get("replied_to", [])
        except:
            pass
        return False

    def _record_reply(self, reply_to_id: str, our_text: str):
        """Record that we replied to avoid double-responding."""
        log_file = "data/reply_back_log.json"
        os.makedirs("data", exist_ok=True)
        try:
            log = json.load(open(log_file)) if os.path.exists(log_file) else {"replied_to": [], "history": []}
        except:
            log = {"replied_to": [], "history": []}
        
        log["replied_to"].append(reply_to_id)
        log["history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reply_to_id": reply_to_id,
            "text": our_text,
        })
        # Keep manageable
        log["replied_to"] = log["replied_to"][-500:]
        log["history"] = log["history"][-200:]
        json.dump(log, open(log_file, "w"), indent=2)

    def _generate_responses(self, our_tweet: str, replies: List[Dict]) -> List[Dict]:
        """Generate responses to the best replies."""
        import requests

        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return []

        replies_block = ""
        for i, r in enumerate(replies):
            replies_block += f"\nREPLY {i+1} by @{r['author']} ({r['likes']} likes):\n{r['text'][:200]}\n"

        system_prompt = """You are Protocol Pulse responding to replies on your own tweets. You are continuing a conversation, not starting one.

RULES:
- VERY short. 1 sentence max. Under 100 characters is ideal.
- Match the energy of the reply. If they're funny, be funny. If they're serious, be sharp.
- Acknowledge their point without being sycophantic. No "great point!" or "exactly!"
- Add a tiny twist or new angle. Don't just agree — push the thought forward.
- If they asked a question, answer it with a question or implication.
- No emojis. No hashtags. Casual punctuation is fine.
- Sound like a real person continuing a real conversation.

GOOD EXAMPLES:
- Reply: "this is why I've been stacking since 2020" → Response: "2020 stackers have a patience most people won't understand for another decade."
- Reply: "institutions don't care about decentralization" → Response: "they don't have to. they just have to keep buying."
- Reply: "what about the miners?" → Response: "the ones still mining or the ones doing the math?"

BAD EXAMPLES:
- "Great point!" / "Absolutely!" / "This is the way" (sycophantic)
- Any response longer than the reply itself
- Explaining Bitcoin fundamentals to someone who clearly already gets it

OUTPUT: JSON array only: [{"reply_to_index": 1, "response": "your response text", "confidence": 0.85}, ...]"""

        user_prompt = f"""Our tweet: "{our_tweet[:200]}"

Replies to respond to:
{replies_block}

Generate 1 response for each reply. Short, sharp, conversational."""

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "grok-3-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.85
        }
        for attempt in range(3):
            try:
                resp = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=45
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]
                raw = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(raw)
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Response generation failed after 3 attempts: {e}")
                    return []
                logger.debug(f"Generation attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)

    def run_reply_back_cycle(self, max_replies_per_cycle=3) -> Dict:
        """Main entry: find our tweets, find best replies, respond."""
        logger.info("Starting reply-back cycle...")

        our_tweets = self._get_our_recent_tweets()
        if not our_tweets:
            return {"success": False, "reason": "no_tweets_with_replies"}

        total_replied = 0
        results = []

        for tweet in our_tweets[:3]:  # Check top 3 tweets
            replies = self._get_best_replies(tweet["id"])
            # Filter already-replied
            fresh = [r for r in replies if not self._check_already_replied(r["id"])]

            if not fresh:
                continue

            responses = self._generate_responses(tweet["text"], fresh[:3])

            for resp in responses:
                if total_replied >= max_replies_per_cycle:
                    break

                idx = resp.get("reply_to_index", 1) - 1
                if idx >= len(fresh):
                    continue

                target = fresh[idx]
                text = resp["response"][:280]

                if os.environ.get("ENABLE_TWEETS", "false").lower() != "true":
                    logger.info(f"[DISABLED] Would reply to @{target['author']}: {text}")
                    results.append({"posted": False, "text": text, "to": target["author"]})
                    continue

                try:
                    from pp_services.x_service import reply_to_tweet
                    result = reply_to_tweet(target["id"], text)
                    if result:
                        self._record_reply(target["id"], text)
                        total_replied += 1
                        logger.info(f"Replied to @{target['author']}: {text[:60]}")
                        results.append({"posted": True, "text": text, "to": target["author"]})
                        time.sleep(15)  # Space out replies
                except Exception as e:
                    logger.error(f"Reply failed: {e}")

        return {"success": True, "replies_posted": total_replied, "details": results}


def run_reply_back():
    """Scheduler entry point."""
    try:
        engine = ReplyBackEngine()
        return engine.run_reply_back_cycle()
    except Exception as e:
        logger.error(f"Reply-back failed: {e}")
        return {"success": False, "error": str(e)}
