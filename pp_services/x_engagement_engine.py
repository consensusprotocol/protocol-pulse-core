"""
X ENGAGEMENT ENGINE — Protocol Pulse Viral Tweet Strategy
=========================================================
Multi-faceted approach:

STRATEGY 1 — COMMENT RADAR (already built)
  → Reply to viral tweets from 63 thought leaders
  → Mirror crowd sentiment + add cypherpunk edge
  → Runs every 3 hours

STRATEGY 2 — ORIGINAL VIRAL TWEETS (this file)
  → Scan top-performing posts across Bitcoin Twitter
  → Analyze comment language, sentiment, what resonates
  → Generate original tweets that match current discourse
  → Post from Protocol Pulse main account
  → Runs every 4 hours, offset from Comment Radar

STRATEGY 3 — QUOTE TWEET AMPLIFIER
  → Find underappreciated tweets with high potential
  → Add sharp one-liner and quote tweet
  → Rides the original's reach while adding value
"""

import os
import sys
import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("x_engine")

# Reuse Comment Radar's X client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ViralTweetEngine:

    def __init__(self):
        from pp_services.comment_radar import CommentRadar
        self.radar = CommentRadar()
        self.x_client = self.radar.x_client
        self.accounts = self.radar.cfg.get("target_accounts", [])
        logger.info(f"ViralTweetEngine initialized with {len(self.accounts)} accounts")

    # ================================================================
    # PHASE 1: SCAN — Find what's working right now
    # ================================================================

    def _scan_top_posts(self, sample_size=15, min_engagement=100) -> List[Dict]:
        """Scan thought leaders for today's highest-performing posts."""
        all_posts = []
        sampled = random.sample(self.accounts, min(sample_size, len(self.accounts)))

        for i, handle in enumerate(sampled):
            try:
                data = self.x_client.get_user_tweets(handle, max_results=10)
                if data is None:
                    logger.warning(f"Rate limited on @{handle}, pausing...")
                    time.sleep(5)
                    data = self.x_client.get_user_tweets(handle, max_results=10)
                
                if not data or "data" not in data:
                    continue

                for t in data["data"]:
                    m = t.get("public_metrics", {})
                    total = m.get("like_count", 0) + m.get("retweet_count", 0) * 1.5 + m.get("reply_count", 0) * 2
                    
                    if total < min_engagement:
                        continue

                    # Check recency (last 24h)
                    created = t.get("created_at", "")
                    if created:
                        try:
                            tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            age = (datetime.now(timezone.utc) - tweet_time).total_seconds() / 3600
                            if age > 24:
                                continue
                        except:
                            pass

                    all_posts.append({
                        "id": t["id"],
                        "text": t.get("text", ""),
                        "author": handle,
                        "metrics": m,
                        "engagement_score": total,
                        "url": f"https://x.com/{handle}/status/{t['id']}",
                    })
                
                if i < len(sampled) - 1:
                    time.sleep(2)

            except Exception as e:
                logger.warning(f"Error scanning @{handle}: {e}")

        all_posts.sort(key=lambda x: x["engagement_score"], reverse=True)
        logger.info(f"Scanned {len(sampled)} accounts, found {len(all_posts)} qualifying posts")
        return all_posts[:10]

    # ================================================================
    # PHASE 2: ANALYZE — What language and sentiment is resonating?
    # ================================================================

    def _analyze_comments(self, posts: List[Dict]) -> Dict:
        """Fetch top comments from best posts to understand what resonates."""
        all_comments = []
        themes = []

        for post in posts[:5]:  # Top 5 posts only
            try:
                data = self.x_client.get_conversation_replies(post["id"])
                if not data or "data" not in data:
                    continue

                post_comments = []
                for reply in data.get("data", []):
                    likes = reply.get("public_metrics", {}).get("like_count", 0)
                    if likes >= 3:
                        post_comments.append({
                            "text": reply.get("text", ""),
                            "likes": likes,
                        })

                post_comments.sort(key=lambda x: x["likes"], reverse=True)
                top_3 = post_comments[:3]
                all_comments.extend(top_3)

                themes.append({
                    "post_text": post["text"][:200],
                    "post_engagement": post["engagement_score"],
                    "top_comments": [c["text"][:150] for c in top_3],
                    "author": post["author"],
                })

            except Exception as e:
                logger.warning(f"Error fetching comments for {post['id']}: {e}")

        logger.info(f"Analyzed {len(themes)} posts, collected {len(all_comments)} top comments")
        return {
            "themes": themes,
            "total_comments": len(all_comments),
            "top_comment_texts": [c["text"][:150] for c in sorted(all_comments, key=lambda x: x["likes"], reverse=True)[:15]],
        }

    # ================================================================
    # PHASE 3: GENERATE — Create original viral tweets
    # ================================================================

    def _generate_viral_tweets(self, posts: List[Dict], analysis: Dict) -> List[Dict]:
        """Use Grok to generate original viral tweets based on current discourse."""
        import requests

        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            logger.error("XAI_API_KEY not set")
            return []

        # Build the context block
        discourse = ""
        for t in analysis.get("themes", [])[:5]:
            discourse += f"\n--- @{t['author']} ({int(t['post_engagement'])} engagement) ---\n"
            discourse += f"POST: {t['post_text']}\n"
            if t["top_comments"]:
                discourse += f"TOP REPLIES: {' | '.join(t['top_comments'][:2])}\n"

        top_comments = analysis.get("top_comment_texts", [])
        comment_block = "\n".join(f"- {c}" for c in top_comments[:10])

        system_prompt = """You are the voice behind Protocol Pulse on X. You write original tweets that feel like they came from the sharpest person at a Bitcoin conference — someone who reads the entire timeline, distills it, and drops one perfect take.

PROCESS:
1. Read the trending posts and their top comments
2. Identify what LANGUAGE resonates (short? questioning? confrontational? ironic?)
3. Identify what SENTIMENT is winning (bullish? skeptical? angry? amused?)
4. Generate original tweets that ride the same current but add something NEW

VOICE RULES:
- Under 200 characters is elite. Under 140 is god-tier. Max 240.
- One thought per tweet. No threads.
- SUGGESTIVE over DECLARATIVE. Questions and implications > statements.
- No emojis. No hashtags. No ALL CAPS words. No "BREAKING".
- Lowercase starts are natural. Fragments are fine.
- Sound like a fund manager between meetings, not a content creator.
- Never directly reference or paraphrase any specific tweet you're given. Create something ORIGINAL.
- Never invent facts, numbers, or prices.

BANNED:
- "the crypto community" / "sparked debate" / "sent shockwaves"
- Any phrase an AI would use
- Anything preachy about Bitcoin being the answer
- Direct commentary on another person's tweet

WHAT WORKS:
- Observations that make people go "exactly"
- Questions nobody is asking but everyone is thinking  
- Dry humor about fiat, regulation, or altcoin culture
- Compressed wisdom that sounds effortless
- Takes that are 80% what the crowd believes + 20% edge they didn't think of

OUTPUT: Return a JSON array of 5 tweet objects. No markdown, no backticks:
[
  {"tweet": "the tweet text", "strategy": "2-3 words why this works", "confidence": 0.85},
  ...
]"""

        user_prompt = f"""Current Bitcoin Twitter discourse (last 24h):

{discourse}

Highest-liked comment language right now:
{comment_block}

Generate 5 original tweets for Protocol Pulse. Each must feel like it belongs in TODAY's conversation without copying anyone. Range of approaches — at least one question, one observation, one with dry humor."""

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
                    "max_tokens": 800,
                    "temperature": 0.9
                },
                timeout=60
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            tweets = json.loads(raw)
            logger.info(f"Generated {len(tweets)} viral tweet candidates")
            return tweets

        except Exception as e:
            logger.error(f"Viral tweet generation failed: {e}")
            return []

    # ================================================================
    # PHASE 4: SELECT & POST — Pick the best and fire
    # ================================================================

    def _select_and_post(self, candidates: List[Dict], strategy: str = "original") -> Dict:
        """Pick the highest-confidence tweet and post it."""
        if not candidates:
            return {"success": False, "reason": "no_candidates"}

        # Sort by confidence
        candidates.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        best = candidates[0]
        tweet_text = best["tweet"][:280]

        # Final safety check
        if len(tweet_text) < 15:
            return {"success": False, "reason": "tweet_too_short"}
        
        banned = ["BREAKING", "🚨", "⚡", "#Bitcoin", "#BTC"]
        for b in banned:
            if b in tweet_text:
                tweet_text = tweet_text.replace(b, "").strip()

        # Check ENABLE_TWEETS
        if os.environ.get("ENABLE_TWEETS", "false").lower() != "true":
            logger.info(f"[TWEETS DISABLED] Would post: {tweet_text}")
            return {"success": False, "reason": "tweets_disabled", "would_post": tweet_text}

        # Global gate check
        try:
            from pp_services.x_service import can_post_tweet
            allowed, reason = can_post_tweet(tweet_text, source=f"engagement_{strategy}")
            if not allowed:
                logger.warning(f"[X GATE REJECT] {strategy} | {reason}")
                return {"success": False, "reason": reason, "gate_blocked": True}
        except Exception as e:
            logger.warning(f"Gate check failed: {e}")

        try:
            from pp_services.x_service import post_tweet
            result = post_tweet(tweet_text, source=f"engagement_{strategy}")
            if result:
                tweet_id = result.get("id", "unknown") if isinstance(result, dict) else "unknown"
                logger.info(f"POSTED [{strategy}]: {tweet_text}")
                
                # Save to log
                self._log_post(tweet_text, tweet_id, strategy, best.get("confidence", 0))
                return {"success": True, "tweet_id": tweet_id, "text": tweet_text, "strategy": strategy}
            else:
                logger.error("Post returned no result")
                return {"success": False, "reason": "post_failed"}

        except Exception as e:
            logger.error(f"Failed to post: {e}")
            return {"success": False, "reason": str(e)}

    # ================================================================
    # PHASE 5: QUOTE TWEET AMPLIFIER
    # ================================================================

    def _find_quotable_tweets(self, posts: List[Dict]) -> List[Dict]:
        """Find mid-range tweets that deserve amplification with a sharp take."""
        # Look for tweets with good content but not yet mega-viral
        quotable = [p for p in posts if 50 < p["engagement_score"] < 500]
        quotable.sort(key=lambda x: x["engagement_score"], reverse=True)
        return quotable[:3]

    def _generate_quote_takes(self, quotable: List[Dict]) -> List[Dict]:
        """Generate one-liner takes to add when quote-tweeting."""
        import requests

        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return []

        tweets_block = ""
        for i, t in enumerate(quotable):
            tweets_block += f"\nTWEET {i+1} by @{t['author']}:\n{t['text'][:250]}\nEngagement: {int(t['engagement_score'])}\nURL: {t['url']}\n"

        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-3-mini",
                    "messages": [
                        {"role": "system", "content": "Generate sharp one-liner quote tweet additions. Under 100 characters each. Suggestive, not preachy. No emojis, no hashtags. JSON array only."},
                        {"role": "user", "content": f"Add a one-liner to each of these tweets:\n{tweets_block}\n\nReturn JSON: [{{'tweet_index': 1, 'take': 'your one-liner', 'confidence': 0.8}}, ...]"}
                    ],
                    "max_tokens": 400,
                    "temperature": 0.85
                },
                timeout=30
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)

        except Exception as e:
            logger.error(f"Quote take generation failed: {e}")
            return []

    def _post_quote_tweet(self, take: Dict, quotable: List[Dict]) -> Dict:
        """Post a quote tweet."""
        idx = take.get("tweet_index", 1) - 1
        if idx >= len(quotable):
            return {"success": False}

        source = quotable[idx]
        text = f"{take['take']} {source['url']}"[:280]

        if os.environ.get("ENABLE_TWEETS", "false").lower() != "true":
            logger.info(f"[TWEETS DISABLED] Would quote: {text}")
            return {"success": False, "reason": "tweets_disabled", "would_post": text}

        # Global gate check
        try:
            from pp_services.x_service import can_post_tweet
            allowed, reason = can_post_tweet(text, source="engagement_quote_tweet")
            if not allowed:
                logger.warning(f"[X GATE REJECT] quote_tweet | {reason}")
                return {"success": False, "reason": reason, "gate_blocked": True}
        except Exception as e:
            logger.warning(f"Gate check failed: {e}")

        try:
            from pp_services.x_service import post_tweet
            result = post_tweet(text, source="engagement_quote_tweet")
            if result:
                logger.info(f"POSTED [quote]: {text[:80]}")
                self._log_post(text, "unknown", "quote_tweet", take.get("confidence", 0))
                return {"success": True, "text": text}
            return {"success": False}
        except Exception as e:
            logger.error(f"Quote tweet failed: {e}")
            return {"success": False}

    def _log_post(self, text, tweet_id, strategy, confidence):
        """Log posted tweets for dedup and tracking."""
        log_file = "data/engagement_log.json"
        os.makedirs("data", exist_ok=True)
        try:
            log = json.load(open(log_file)) if os.path.exists(log_file) else {"posts": []}
        except:
            log = {"posts": []}

        log["posts"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tweet_id": str(tweet_id),
            "text": text[:280],
            "strategy": strategy,
            "confidence": confidence,
        })

        # Keep last 200
        log["posts"] = log["posts"][-200:]
        json.dump(log, open(log_file, "w"), indent=2)

    # ================================================================
    # MAIN ENTRY POINTS
    # ================================================================


    # ================================================================
    # STRATEGY 4: INTEL JOURNALIST TWEETS
    # Posts original tweets in investigative journalist voice
    # "sources say..." / "word from trading desks..." style
    # ================================================================

    def _generate_intel_tweets(self, posts: List[Dict], analysis: Dict) -> List[Dict]:
        """Generate tweets in investigative journalist voice."""
        import requests

        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return []

        discourse = ""
        for t in analysis.get("themes", [])[:5]:
            discourse += f"POST: {t['post_text'][:200]}\nTOP REPLIES: {' | '.join(t['top_comments'][:2])}\n\n"

        system_prompt = """You write tweets as a well-connected financial journalist covering Bitcoin. You sound like you just got off the phone with sources. Never reveal your intel comes from Twitter.

VOICE:
- "Word from mining desks..." / "Sources familiar with the matter say..." / "Interesting chatter from institutional circles..."
- You hint at things. You don't explain them.
- Under 200 characters is ideal. Max 240.
- No emojis. No hashtags. Lowercase starts fine.
- Sound like a Bloomberg terminal alert written by a human with a sense of irony.

EXAMPLES OF WHAT WE WANT:
- "word from OTC desks: quiet accumulation all week. nobody wants to talk about it."
- "interesting that the loudest critics went silent right around the difficulty adjustment."
- "hearing institutions are running the numbers on mining exposure again. last time this happened was Q3."
- "the gap between what officials say publicly and what their treasuries are doing has never been wider."

WHAT WE DON'T WANT:
- Direct references to tweets or social media
- Preachy Bitcoin maximalism
- Anything an AI would say
- Facts you made up

Return JSON array only: [{"tweet": "text", "confidence": 0.8}, ...]
Generate 3 tweets."""

        user_prompt = f"Current market intelligence:\n\n{discourse}\n\nWrite 3 tweets in investigative journalist voice."

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
                    "max_tokens": 500,
                    "temperature": 0.9
                },
                timeout=45
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            tweets = json.loads(raw)
            logger.info(f"Generated {len(tweets)} intel journalist tweets")
            return tweets

        except Exception as e:
            logger.error(f"Intel tweet generation failed: {e}")
            return []

    def run_viral_tweet_cycle(self) -> Dict:
        """Full cycle: scan → analyze → generate → post one original tweet."""
        logger.info("Starting viral tweet cycle...")

        posts = self._scan_top_posts()
        if len(posts) < 3:
            return {"success": False, "reason": "not_enough_posts"}

        analysis = self._analyze_comments(posts)
        candidates = self._generate_viral_tweets(posts, analysis)
        
        if not candidates:
            return {"success": False, "reason": "generation_failed"}

        result = self._select_and_post(candidates, strategy="original_viral")
        logger.info(f"Viral tweet cycle result: {result.get('success')}")
        return result

    def run_quote_tweet_cycle(self) -> Dict:
        """Find and quote-tweet an underappreciated post."""
        logger.info("Starting quote tweet cycle...")

        posts = self._scan_top_posts(sample_size=10, min_engagement=30)
        quotable = self._find_quotable_tweets(posts)
        
        if not quotable:
            return {"success": False, "reason": "nothing_quotable"}

        takes = self._generate_quote_takes(quotable)
        if not takes:
            return {"success": False, "reason": "generation_failed"}

        # Pick highest confidence
        takes.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        result = self._post_quote_tweet(takes[0], quotable)
        return result

    def run_full_strategy(self) -> Dict:
        """Run the complete multi-faceted strategy."""
        results = {}

        # Rotate strategies to avoid repetition
        strategies = ["viral", "intel", "viral", "quote"]
        pick = strategies[int(time.time() / 3600) % len(strategies)]
        
        if pick == "viral":
            results["viral"] = self.run_viral_tweet_cycle()
        elif pick == "intel":
            # Intel journalist voice tweets
            posts = self._scan_top_posts(sample_size=12, min_engagement=50)
            if len(posts) >= 3:
                analysis = self._analyze_comments(posts)
                candidates = self._generate_intel_tweets(posts, analysis)
                if candidates:
                    results["intel"] = self._select_and_post(candidates, strategy="intel_journalist")
                else:
                    results["intel"] = {"success": False, "reason": "generation_failed"}
            else:
                results["intel"] = {"success": False, "reason": "not_enough_posts"}
        elif pick == "quote":
            results["quote"] = self.run_quote_tweet_cycle()

        return results


# ================================================================
# TIER 1 HANDLES — high-signal Bitcoin accounts to engage with
# ================================================================
TIER1_HANDLES = [
    "saborbtc", "LynAldenContact", "DocumentingBTC", "ODELL",
    "daboradelacruz", "natbrunell", "gladstein", "BitcoinMagazine",
    "CoinDesk", "Blockworks_", "hodlonaut", "aantonop",
    "PeterMcCormack", "MartyBent", "presabordelacruz",
]


# ================================================================
# AUTO-ENGAGEMENT: mentions, likes, retweets
# ================================================================

def run_auto_engagement() -> Dict:
    """
    Auto-engagement cycle (runs 2x daily):
    1. Check @ProtocolPulseHQ mentions in last 12 hours
    2. Reply to real accounts with on-brand responses
    3. Like 3-5 high-signal tweets from TIER1 handles
    4. Retweet max 1 exceptional post from TIER1
    """
    results = {"success": True, "replies": 0, "likes": 0, "retweets": 0, "errors": []}

    try:
        from pp_services.x_service import XService
        x = XService()
        if not x.client_v2:
            return {"success": False, "error": "X client not configured"}

        # 1. Reply to mentions
        try:
            mentions_result = _reply_to_mentions(x)
            results["replies"] = mentions_result.get("replied", 0)
        except Exception as e:
            results["errors"].append(f"mentions: {e}")
            logger.warning("Mention replies failed: %s", e)

        # 2. Like high-signal tweets from TIER1
        try:
            likes_result = _like_tier1_tweets(x)
            results["likes"] = likes_result.get("liked", 0)
        except Exception as e:
            results["errors"].append(f"likes: {e}")
            logger.warning("Tier1 likes failed: %s", e)

        # 3. Retweet max 1 exceptional post
        try:
            rt_result = _retweet_tier1(x)
            results["retweets"] = rt_result.get("retweeted", 0)
        except Exception as e:
            results["errors"].append(f"retweet: {e}")
            logger.warning("Tier1 retweet failed: %s", e)

    except Exception as e:
        logger.error("Auto-engagement failed: %s", e)
        return {"success": False, "error": str(e)}

    logger.info("Auto-engagement: %d replies, %d likes, %d RTs", results["replies"], results["likes"], results["retweets"])
    return results


def _reply_to_mentions(x) -> Dict:
    """Check and reply to recent mentions."""
    replied = 0
    try:
        # Get authenticated user's ID
        me = x.client_v2.get_me()
        if not me or not me.data:
            return {"replied": 0}
        user_id = me.data.id

        # Fetch recent mentions (last 12h via since_id would be better, but start simple)
        mentions = x.client_v2.get_users_mentions(
            user_id, max_results=10,
            tweet_fields=["created_at", "author_id", "public_metrics"]
        )
        if not mentions or not mentions.data:
            return {"replied": 0}

        for mention in mentions.data[:5]:
            # Skip old mentions (>12h)
            if mention.created_at:
                age = (datetime.now(timezone.utc) - mention.created_at).total_seconds() / 3600
                if age > 12:
                    continue

            # Skip low-quality (very short)
            if len(mention.text) < 20:
                continue

            # Generate reply via Grok
            reply_text = _generate_mention_reply(mention.text)
            if not reply_text:
                continue

            # Post reply (replies don't count against 3/day post limit)
            try:
                r = x.client_v2.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=str(mention.id))
                if r and r.data:
                    replied += 1
                    logger.info("Replied to mention %s: %s", mention.id, reply_text[:60])
                    time.sleep(30)  # Don't spam replies
            except Exception as e:
                logger.warning("Reply to %s failed: %s", mention.id, e)

            if replied >= 3:  # Max 3 replies per cycle
                break

    except Exception as e:
        logger.warning("Mention check failed: %s", e)

    return {"replied": replied}


def _generate_mention_reply(mention_text: str) -> Optional[str]:
    """Generate a brief, on-brand reply to a mention."""
    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        return None

    import requests as req

    prompt = f"""Someone mentioned @ProtocolPulseHQ with this tweet:
"{mention_text[:300]}"

Write a 1-2 sentence reply. Rules:
- Bitcoin/sovereignty lens, never sycophantic
- Add value — disagree if appropriate
- No emojis, no hashtags, no "thanks for mentioning us"
- Sound like a knowledgeable peer, not a brand account
- Under 200 characters ideal, max 250
- If the mention is spam/bot/irrelevant, respond with exactly: SKIP

Return ONLY the reply text, nothing else."""

    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = req.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json={
                "model": "grok-3-mini",
                "messages": [
                    {"role": "system", "content": "You reply to tweets for Protocol Pulse, a Bitcoin intelligence platform. Brief, sharp, sovereign. Never corporate."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.7
            },
            timeout=30
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"].strip().strip('"')
        if reply.upper() == "SKIP" or len(reply) < 10:
            return None
        return reply
    except Exception as e:
        logger.warning("Reply generation failed: %s", e)
        return None


def _like_tier1_tweets(x) -> Dict:
    """Like 3-5 high-signal Bitcoin tweets from TIER1 handles."""
    liked = 0
    sampled = random.sample(TIER1_HANDLES, min(5, len(TIER1_HANDLES)))

    for handle in sampled:
        try:
            # Search for recent tweets from this handle
            tweets = x.client_v2.search_recent_tweets(
                query=f"from:{handle} -is:retweet -is:reply",
                max_results=5,
                tweet_fields=["public_metrics", "created_at"]
            )
            if not tweets or not tweets.data:
                continue

            for tweet in tweets.data[:1]:  # Like at most 1 per handle
                # Only like recent tweets (< 24h)
                if tweet.created_at:
                    age = (datetime.now(timezone.utc) - tweet.created_at).total_seconds() / 3600
                    if age > 24:
                        continue

                metrics = tweet.public_metrics or {}
                if metrics.get("like_count", 0) + metrics.get("retweet_count", 0) < 10:
                    continue  # Skip low-engagement

                try:
                    x.client_v2.like(tweet.id)
                    liked += 1
                    logger.info("Liked @%s tweet %s", handle, tweet.id)
                    time.sleep(5)
                except Exception:
                    pass

            if liked >= 5:
                break

        except Exception as e:
            logger.debug("Like scan for @%s failed: %s", handle, e)

    return {"liked": liked}


def _retweet_tier1(x) -> Dict:
    """Retweet max 1 exceptional post from TIER1 handles per cycle."""
    sampled = random.sample(TIER1_HANDLES, min(8, len(TIER1_HANDLES)))
    best_tweet = None
    best_score = 0

    for handle in sampled:
        try:
            tweets = x.client_v2.search_recent_tweets(
                query=f"from:{handle} -is:retweet -is:reply",
                max_results=5,
                tweet_fields=["public_metrics", "created_at"]
            )
            if not tweets or not tweets.data:
                continue

            for tweet in tweets.data:
                if tweet.created_at:
                    age = (datetime.now(timezone.utc) - tweet.created_at).total_seconds() / 3600
                    if age > 12:
                        continue

                metrics = tweet.public_metrics or {}
                score = metrics.get("like_count", 0) + metrics.get("retweet_count", 0) * 2
                if score > best_score and score >= 100:  # Only RT truly exceptional
                    best_score = score
                    best_tweet = tweet

        except Exception:
            continue

    if best_tweet:
        try:
            x.client_v2.retweet(best_tweet.id)
            logger.info("Retweeted tweet %s (score=%d)", best_tweet.id, best_score)
            return {"retweeted": 1}
        except Exception as e:
            logger.warning("Retweet failed: %s", e)

    return {"retweeted": 0}


# Scheduler-safe entry points
def run_viral_tweet():
    """Called by scheduler for original viral tweets."""
    try:
        engine = ViralTweetEngine()
        return engine.run_viral_tweet_cycle()
    except Exception as e:
        logger.error(f"Viral tweet cycle failed: {e}")
        return {"success": False, "error": str(e)}

def run_full_engagement_strategy():
    """Called by scheduler for full multi-faceted strategy."""
    try:
        engine = ViralTweetEngine()
        return engine.run_full_strategy()
    except Exception as e:
        logger.error(f"Full engagement strategy failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = ViralTweetEngine()
    result = engine.run_full_strategy()
    print(json.dumps(result, indent=2, default=str))
