"""Social Data Fetcher — real tweet/Nostr data for the social segment.

Per Law A1: if no real data exists, return empty list. Never fabricate.

Priority:
  1. data/daily_tweets.json (manually curated by operator)
  2. High-engagement tweets from data/tweet_study/raw_tweets.json
  3. Empty list (social segment skipped)
"""
import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TWEET_STUDY_PATH = os.path.join(BASE, "..", "data", "tweet_study", "raw_tweets.json")
DAILY_TWEETS_PATH = os.path.join(BASE, "data", "daily_tweets.json")


def get_todays_social_posts(max_posts=5):
    """Get real tweet data for the social segment.

    Returns:
        List of dicts with keys: handle, text, likes, retweets, source
        Empty list if no real data available (Law A1).
    """
    # Priority 1: Operator-curated daily tweets
    if os.path.exists(DAILY_TWEETS_PATH):
        try:
            with open(DAILY_TWEETS_PATH) as f:
                data = json.load(f)
            posts = data.get("tweets", data if isinstance(data, list) else [])[:max_posts]
            if posts:
                logger.info(f"Social: {len(posts)} curated tweets loaded")
                # Dedup by handle - max 1 tweet per account
                seen_handles = set()
                deduped = []
                for p in posts:
                    h = p.get('handle','').lower().strip('@')
                    if h not in seen_handles:
                        seen_handles.add(h)
                        deduped.append(p)
                return deduped
        except Exception as e:
            logger.warning(f"Error reading daily_tweets.json: {e}")

    # Priority 2: Raw study data — highest engagement tweets
    if os.path.exists(TWEET_STUDY_PATH):
        try:
            with open(TWEET_STUDY_PATH) as f:
                raw = json.load(f)
            # Sort by engagement rate descending
            tweets = sorted(raw, key=lambda t: t.get("engagement_rate", 0) or 0, reverse=True)

            # Prefer recent tweets (last 7 days) if available
            cutoff = datetime.utcnow() - timedelta(days=7)
            recent = []
            for t in tweets:
                try:
                    created = datetime.fromisoformat(
                        t.get("created_at", "").replace("Z", "+00:00")
                    )
                    if created.replace(tzinfo=None) > cutoff:
                        recent.append(t)
                except (ValueError, TypeError):
                    continue

            # DIVERSITY FIX: max 1 tweet per handle, varied accounts
            pool = recent if recent else tweets
            seen_h = set()
            deduped_pool = []
            for t in pool:
                h = t.get('handle','').lower().strip('@')
                if h not in seen_h:
                    seen_h.add(h)
                    deduped_pool.append(t)
            source = deduped_pool[:max_posts]
            posts = [
                {
                    "handle": t.get("handle", "unknown"),
                    "text": t.get("text", "")[:280],
                    "likes": t.get("likes", t.get("like_count", 0)),
                    "retweets": t.get("retweets", t.get("retweet_count", 0)),
                    "source": "raw_study",
                }
                for t in source
            ]
            if posts:
                logger.info(f"Social: {len(posts)} tweets from raw study data")
                return posts
        except Exception as e:
            logger.warning(f"Error reading raw_tweets.json: {e}")

    # No real data — return empty per Law A1
    logger.warning("Social: No real tweet data available. Segment will be skipped.")
    return []
