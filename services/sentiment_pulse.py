"""
SENTIMENT PULSE — Daily editorial digest of Bitcoin Twitter's best takes.
Scans thought leader tweets, picks top 5-7 by engagement, writes editorial article
with embedded tweet cards and hyperlinks.
"""

import os
import sys
import json
import logging
import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("sentiment_pulse")

# Reuse Comment Radar's X client and config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SentimentPulse:

    def __init__(self):
        from services.comment_radar import CommentRadar
        self.radar = CommentRadar()
        self.x_client = self.radar.x_client
        self.accounts = self.radar.cfg.get("target_accounts", [])
        logger.info(f"SentimentPulse initialized with {len(self.accounts)} accounts")

    def _get_todays_top_tweets(self, max_tweets=7, min_engagement=20) -> List[Dict]:
        """Scan all thought leaders for today's top tweets."""
        all_tweets = []
        # Sample accounts to stay within rate limits
        sample_size = min(20, len(self.accounts))
        sampled = random.sample(self.accounts, sample_size)

        for i, handle in enumerate(sampled):
            try:
                data = self.x_client.get_user_tweets(handle, max_results=10)
                if data is None:
                    # Likely rate limited — pause and retry once
                    logger.warning(f'Rate limited on @{handle}, pausing 5s...')
                    import time
                    time.sleep(5)
                    data = self.x_client.get_user_tweets(handle, max_results=10)
                
                # Pace requests to avoid 429
                if i < len(sampled) - 1:
                    import time
                    time.sleep(2)
                tweets = data.get("data", []) if data else []
                users = {u["id"]: u for u in data.get("includes", {}).get("users", [])} if data else {}

                for t in tweets:
                    metrics = t.get("public_metrics", {})
                    total = metrics.get("like_count", 0) + metrics.get("retweet_count", 0) + metrics.get("reply_count", 0)

                    if total < min_engagement:
                        continue

                    # Check it's from last 24h
                    created = t.get("created_at", "")
                    if created:
                        try:
                            tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            age_hours = (datetime.now(timezone.utc) - tweet_time).total_seconds() / 3600
                            if age_hours > 24:
                                continue
                        except:
                            pass

                    all_tweets.append({
                        "id": t["id"],
                        "text": t.get("text", ""),
                        "author": t.get("_author_username", handle),
                        "metrics": metrics,
                        "total_engagement": total,
                        "created_at": created,
                        "url": f"https://x.com/{handle}/status/{t['id']}",
                    })
            except Exception as e:
                logger.warning(f"Error scanning @{handle}: {e}")

        # Sort by engagement
        all_tweets.sort(key=lambda x: x["total_engagement"], reverse=True)
        logger.info(f"Found {len(all_tweets)} tweets above threshold from {sample_size} accounts")

        # Topic diversity — don't pick 5 tweets about the same thing
        selected = []
        seen_themes = set()
        for tweet in all_tweets:
            theme = self._detect_tweet_theme(tweet["text"])
            theme_count = sum(1 for s in seen_themes if s == theme)
            if theme_count >= 2:
                continue
            selected.append(tweet)
            seen_themes.add(theme)
            if len(selected) >= max_tweets:
                break

        logger.info(f"Selected {len(selected)} diverse top tweets")
        return selected

    def _detect_tweet_theme(self, text: str) -> str:
        """Simple theme detection for diversity."""
        text_lower = text.lower()
        themes = {
            "mining": ["mining", "miner", "hashrate", "difficulty"],
            "price": ["price", "rally", "crash", "correction", "bull", "bear"],
            "regulation": ["sec", "regulation", "congress", "law", "ban"],
            "etf": ["etf", "blackrock", "fidelity"],
            "self-custody": ["self-custody", "keys", "wallet", "seed"],
            "lightning": ["lightning", "layer 2", "payment"],
            "macro": ["fed", "inflation", "rates", "dollar", "yield"],
            "adoption": ["adoption", "country", "legal tender", "reserve"],
        }
        for theme, keywords in themes.items():
            if any(kw in text_lower for kw in keywords):
                return theme
        return "general"

    def _get_top_comments(self, tweet_id: str, min_likes: int = 5, max_comments: int = 3) -> List[Dict]:
        """Fetch top comments for a tweet."""
        try:
            data = self.x_client.get_conversation_replies(tweet_id)
            if not data or "data" not in data:
                return []

            comments = []
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])} if data else {}

            for reply in data.get("data", []):
                metrics = reply.get("public_metrics", {})
                likes = metrics.get("like_count", 0)
                if likes >= min_likes:
                    author_id = reply.get("author_id", "")
                    author = users.get(author_id, {}).get("username", "unknown")
                    comments.append({
                        "id": reply["id"],
                        "text": reply.get("text", ""),
                        "author": author,
                        "likes": likes,
                    })

            comments.sort(key=lambda x: x["likes"], reverse=True)
            return comments[:max_comments]
        except Exception as e:
            logger.warning(f"Error fetching comments for {tweet_id}: {e}")
            return []

    def _build_tweet_embed_html(self, tweet: Dict) -> str:
        """Build a dark-themed tweet embed card."""
        metrics = tweet["metrics"]
        likes = metrics.get("like_count", 0)
        rts = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        text = tweet["text"].replace("\n", "<br>")
        handle = tweet["author"]
        url = tweet["url"]

        return f'''<div class="tweet-embed" style="background: #15202b; border: 1px solid #38444d; border-radius: 12px; padding: 16px; margin: 20px auto; max-width: 550px; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
  <div style="display: flex; align-items: center; margin-bottom: 10px;">
    <strong style="color: #fff; font-size: 15px;">@{handle}</strong>
  </div>
  <p style="color: #e1e8ed; font-size: 15px; line-height: 1.5; margin: 0 0 12px 0;">{text}</p>
  <div style="color: #8899a6; font-size: 13px; padding-top: 8px; border-top: 1px solid #38444d;">
    <span style="margin-right: 16px;">♥ {likes:,}</span>
    <span style="margin-right: 16px;">↻ {rts:,}</span>
    <span>💬 {replies:,}</span>
  </div>
  <a href="{url}" target="_blank" rel="noopener" style="color: #1d9bf0; font-size: 13px; text-decoration: none; display: inline-block; margin-top: 8px;">View on X →</a>
</div>'''

    def _build_comment_embed_html(self, comment: Dict) -> str:
        """Build a smaller comment embed."""
        text = comment["text"].replace("\n", "<br>")
        return f'''<div style="background: #192734; border-left: 3px solid #1d9bf0; border-radius: 8px; padding: 12px; margin: 10px auto 10px 30px; max-width: 500px; font-family: -apple-system, sans-serif;">
  <strong style="color: #8899a6; font-size: 13px;">@{comment["author"]}</strong>
  <span style="color: #8899a6; font-size: 12px; margin-left: 8px;">♥ {comment["likes"]}</span>
  <p style="color: #d9d9d9; font-size: 14px; line-height: 1.4; margin: 6px 0 0 0;">{text}</p>
</div>'''

    def _generate_editorial(self, tweets: List[Dict], comments_map: Dict) -> Dict:
        """Use Grok API directly to write the editorial article."""
        import requests
        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            logger.error("XAI_API_KEY not set")
            return {"title": "Today's Pulse", "html": "<p>API key missing.</p>"}

        # Build the tweet data for the prompt
        tweet_block = ""
        for i, t in enumerate(tweets, 1):
            tweet_block += f"\nTWEET #{i}:\n"
            tweet_block += f"Author: @{t['author']}\n"
            tweet_block += f"Text: {t['text'][:300]}\n"
            tweet_block += f"Engagement: {t['metrics'].get('like_count',0)} likes, {t['metrics'].get('retweet_count',0)} RTs\n"
            
            # Add top comment if exists
            tweet_comments = comments_map.get(t["id"], [])
            if tweet_comments:
                best = tweet_comments[0]
                tweet_block += f'Top reply: "{best["text"][:200]}" — @{best["author"]} ({best["likes"]} likes)\n'

        system_prompt = """You are the editorial voice of Protocol Pulse. You write like a sharp financial journalist who happens to understand Bitcoin deeply — not a Bitcoin evangelist who learned to write.

Think Matt Taibbi covering Wall Street. Think Lyn Alden's newsletter. Think Bloomberg Businessweek's best feature writer.

VOICE:
- Confident but never preachy. You observe, you analyze, you imply. You do NOT lecture.
- Show the broken system. Let Bitcoin be the unspoken conclusion the reader reaches on their own.
- NEVER say "Bitcoin is the solution" or "this is why Bitcoin matters" or "this reinforces Bitcoin's value." If you have to explain why it matters, you've already lost.
- Suggestive over declarative. A well-placed observation does more work than a paragraph of evangelism.
- Dry wit welcome. Sycophancy forbidden.

BANNED PHRASES (instant rejection):
- "In the whirlwind of" / "painting a portrait" / "sobering dose of reality"
- "underscores" / "dovetails with" / "reinforcing" / "highlighting"
- "Bitcoin's role as a bulwark" / "ultimate hedge" / "path to financial sovereignty"  
- "the crypto community" / "sparked debate" / "sent shockwaves"
- "in an era of" / "in a world where" / "in the landscape of"
- Any sentence that starts with "This" followed by an abstract noun
- Any paragraph that ends by explaining what the reader should think

FORMAT:
- STRICT MAX: 700 words. Under 600 is better. This is a HARD limit.
- 1 tight paragraph per tweet. MAX 3-4 sentences of commentary. Then the embed. Move on.
- Opening: 1-2 sentences. Set the scene, don't summarize the article.
- Closing "The Takeaway": 2-3 sentences max. Land one sharp thought, not a sermon.
- Return valid HTML with h2 tags for section headers
- Use <!-- TWEET_EMBED:N --> placeholders (N = tweet number 1-7) where each tweet should appear
- Use <!-- COMMENT_EMBED:N --> after the tweet embed if there's a notable reply
- Do NOT wrap in html/body tags"""

        user_prompt = f"""Today's top tweets from Bitcoin thought leaders:

{tweet_block}

Write the Sentiment Pulse digest. STRICT RULES:
- UNDER 700 WORDS. This is non-negotiable. Count them.
- Lead with the most interesting story, not the most popular tweet.
- 1 short paragraph of context per tweet (3-4 sentences MAX), then <!-- TWEET_EMBED:N -->
- If a reply adds value, place <!-- COMMENT_EMBED:N --> after the embed
- Section headers should be sharp and specific (not "Bitcoin Update" but "The Whitepaper Hits Wall Street")
- Opening: 1-2 sentences. No throat-clearing.
- Closing "The Takeaway": 2-3 sentences. One sharp thought. Stop.
- DO NOT explain why Bitcoin matters. The reader already knows.
- DO NOT connect every story back to Bitcoin with a paragraph of analysis. If the connection is obvious, it doesn't need stating.

Return HTML only. No markdown. No code fences. No preamble."""

        try:
            import requests as _rq
            _hdrs = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            _url = "https://api.x.ai/v1/chat/completions"

            # Generate article body
            payload = {
                "model": "grok-3-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.8
            }
            resp = _rq.post(_url, headers=_hdrs, json=payload, timeout=120)
            resp.raise_for_status()
            article_html = resp.json()["choices"][0]["message"]["content"]
            article_html = article_html.replace("```html", "").replace("```", "").strip()
            logger.info(f"Article body generated: {len(article_html)} chars")

            # Generate title
            title_payload = {
                "model": "grok-3-mini",
                "messages": [
                    {"role": "system", "content": "Write punchy editorial headlines. One line only. No quotes. No colons. Max 10 words."},
                    {"role": "user", "content": f"Write ONE headline for today's Bitcoin Twitter digest based on these tweets:\n{tweet_block[:600]}"}
                ],
                "max_tokens": 50,
                "temperature": 0.9
            }
            t_resp = _rq.post(_url, headers=_hdrs, json=title_payload, timeout=30)
            t_resp.raise_for_status()
            title = t_resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")[:100]
            if not title or len(title) < 10:
                title = "Today's Pulse: What Bitcoin Twitter Is Really Saying"
            logger.info(f"Title generated: {title}")
            return {"title": title, "html": article_html}

        except Exception as e:
            logger.error(f"Editorial generation failed: {e}", exc_info=True)
            return {"title": "Today's Pulse", "html": "<p>Article generation failed.</p>"}

    def _insert_embeds(self, html: str, tweets: List[Dict], comments_map: Dict) -> str:
        """Replace <!-- TWEET_EMBED:N --> placeholders with actual embed HTML."""
        for i, tweet in enumerate(tweets, 1):
            embed = self._build_tweet_embed_html(tweet)
            html = html.replace(f"<!-- TWEET_EMBED:{i} -->", embed)

            # Comment embeds
            tweet_comments = comments_map.get(tweet["id"], [])
            if tweet_comments and f"<!-- COMMENT_EMBED:{i} -->" in html:
                comment_html = ""
                for c in tweet_comments[:2]:
                    comment_html += self._build_comment_embed_html(c)
                html = html.replace(f"<!-- COMMENT_EMBED:{i} -->", comment_html)
            else:
                html = html.replace(f"<!-- COMMENT_EMBED:{i} -->", "")

        return html

    def generate_daily_pulse(self) -> Dict:
        """Main entry point: generate the full Sentiment Pulse article."""
        logger.info("Starting daily Sentiment Pulse generation...")

        # 1. Get top tweets
        tweets = self._get_todays_top_tweets(max_tweets=7)
        if len(tweets) < 3:
            logger.warning(f"Only found {len(tweets)} tweets, need at least 3")
            return {"success": False, "reason": "not_enough_tweets"}

        # 2. Get top comments for each
        comments_map = {}
        for tweet in tweets:
            comments = self._get_top_comments(tweet["id"])
            if comments:
                comments_map[tweet["id"]] = comments

        logger.info(f"Collected {len(tweets)} tweets, {sum(len(v) for v in comments_map.values())} comments")

        # 3. Generate editorial
        editorial = self._generate_editorial(tweets, comments_map)

        # 4. Insert tweet embeds
        final_html = self._insert_embeds(editorial["html"], tweets, comments_map)

        # 5. Generate header image
        try:
            from services.image_service import generate_article_header_image
            header_image = generate_article_header_image(editorial["title"])
        except Exception as e:
            logger.warning(f"Header image generation failed: {e}")
            header_image = "/static/images/default-header.png"

        # 6. Save to database
        try:
            from app import app, db
            import models

            with app.app_context():
                article = models.Article(
                    title=editorial["title"],
                    content=final_html,
                    summary=f"Daily digest of the most engaged Bitcoin conversations from {len(tweets)} thought leaders across X.",
                    category="sentiment",
                    source_type="sentiment_pulse",
                    header_image_url=header_image,
                    published=True,
                )
                db.session.add(article)
                db.session.commit()

                logger.info(f"Published Sentiment Pulse article: [{article.id}] {editorial['title']}")

                return {
                    "success": True,
                    "article_id": article.id,
                    "title": editorial["title"],
                    "tweets_featured": len(tweets),
                    "comments_included": sum(len(v) for v in comments_map.values()),
                }

        except Exception as e:
            logger.error(f"Failed to save article: {e}")
            return {"success": False, "error": str(e)}


def generate_daily_sentiment_pulse() -> Dict:
    """Scheduler-safe entry point."""
    try:
        pulse = SentimentPulse()
        return pulse.generate_daily_pulse()
    except Exception as e:
        logger.error(f"Sentiment Pulse failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = generate_daily_sentiment_pulse()
    print(json.dumps(result, indent=2, default=str))
