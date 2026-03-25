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
            posts = data.get("tweets", data if isinstance(data, list) else [])
            if posts:
                # Dedup by handle FIRST, then truncate to max_posts
                seen_handles = set()
                deduped = []
                for p in posts:
                    h = p.get('handle', '').lower().strip('@')
                    if h and h not in seen_handles:
                        seen_handles.add(h)
                        deduped.append(p)
                deduped = deduped[:max_posts]
                logger.info(f"Social: {len(deduped)} curated tweets loaded")
                return deduped
        except Exception as e:
            logger.warning(f"Error reading daily_tweets.json: {e}")

    # Priority 2: Raw study data — highest engagement tweets
    if os.path.exists(TWEET_STUDY_PATH):
        try:
            with open(TWEET_STUDY_PATH) as f:
                content = f.read()
            # Handle concatenated JSON arrays (multiple appends)
            try:
                raw = json.loads(content)
            except json.JSONDecodeError:
                decoder = json.JSONDecoder()
                raw = []
                pos = 0
                while pos < len(content):
                    stripped = content[pos:].lstrip()
                    if not stripped:
                        break
                    try:
                        obj, end = decoder.raw_decode(stripped)
                        if isinstance(obj, list):
                            raw.extend(obj)
                        else:
                            raw.append(obj)
                        pos += len(content) - len(stripped) + end
                    except json.JSONDecodeError:
                        break
                if not raw:
                    raise json.JSONDecodeError("No valid JSON found", content, 0)
            from datetime import datetime, timezone, timedelta
            now_utc = datetime.now(timezone.utc)
            def _sort_key(t):
                raw_ts = t.get('created_at', '')
                try:
                    ts = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                    age_h = (now_utc - ts).total_seconds() / 3600
                except Exception:
                    age_h = 9999
                er = t.get('engagement_rate', 0) or 0
                likes = t.get('likes', 0) or 0
                recency = 10.0 if age_h < 24 else (1.0 if age_h < 168 else 0.0)
                return recency + er + (likes / 100000.0)
            tweets = sorted(raw, key=_sort_key, reverse=True)

            # KOL FRESHNESS LAW: Only use tweets from the last 24 hours
            # to prevent stale quotes being narrated as "today's" intelligence.
            # Fallback to 7-day window only if zero 24h tweets exist.
            cutoff_24h = now_utc - timedelta(hours=24)
            cutoff_7d = now_utc - timedelta(days=7)
            fresh_24h = []
            recent_7d = []
            for t in tweets:
                try:
                    created = datetime.fromisoformat(
                        t.get("created_at", "").replace("Z", "+00:00")
                    )
                    created_aware = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
                    if created_aware > cutoff_24h:
                        fresh_24h.append(t)
                    elif created_aware > cutoff_7d:
                        recent_7d.append(t)
                except (ValueError, TypeError):
                    continue
            recent = fresh_24h if fresh_24h else recent_7d
            if not fresh_24h:
                logger.warning("Social: No tweets from last 24h — falling back to 7-day pool (%d tweets)", len(recent_7d))

            # DIVERSITY FIX: sort by likes desc FIRST, then dedup by handle
            # This ensures the highest-engagement tweet per handle is retained
            pool = recent if recent else tweets
            pool = sorted(pool, key=lambda t: t.get('likes', t.get('like_count', 0)) or 0, reverse=True)
            seen_h = set()
            deduped_pool = []
            for t in pool:
                h = t.get('handle', '').lower().strip('@')
                if h and h not in seen_h:
                    seen_h.add(h)
                    deduped_pool.append(t)
            source = deduped_pool[:max_posts]
            posts = [
                {
                    "handle": t.get("handle", "unknown"),
                    "text": t.get("text", "")[:280],
                    "likes": t.get("likes", t.get("like_count", 0)),
                    "retweets": t.get("retweets", t.get("retweet_count", 0)),
                    "created_at": t.get("created_at", ""),
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
