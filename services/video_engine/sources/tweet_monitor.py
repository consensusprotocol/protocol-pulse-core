"""
Tweet Monitor
==============
Fetches notable tweets from monitored Bitcoin accounts.
Soft dependency — pipeline works without it.

Uses Twitter API v2 (Bearer token) for search.
Falls back gracefully: if no token, returns empty list.
Caches results to avoid rate limit issues on retry.
"""
import os
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("TweetMonitor")

CACHE_DIR = Path("data/video_engine/cache")


class TweetMonitor:
    """Fetch and filter notable tweets from monitored accounts."""

    def __init__(self, accounts: List[str], min_likes: int = 1000,
                 hours: int = 24):
        self.accounts = accounts
        self.min_likes = min_likes
        self.hours = hours
        self.bearer_token = (os.environ.get("TWITTER_BEARER_TOKEN", "") or
                              os.environ.get("TWITTER_BEARER", ""))

    @property
    def configured(self) -> bool:
        return bool(self.bearer_token)

    def fetch_notable_tweets(self, bundle_path: Path = None) -> List[dict]:
        """Fetch tweets from monitored accounts. Returns empty list if unconfigured."""
        if not self.configured:
            logger.info("  Tweet monitor: TWITTER_BEARER not set, skipping (soft dependency)")
            return []

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"tweets_{datetime.utcnow().strftime('%Y-%m-%d')}.json"

        # Check cache first
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text())
                age_minutes = (time.time() - cached.get("fetched_at", 0)) / 60
                if age_minutes < 30:
                    logger.info(f"  Using cached tweets ({len(cached['tweets'])} tweets, "
                                f"{age_minutes:.0f}min old)")
                    return cached["tweets"]
            except Exception:
                pass

        # Fetch from Twitter API
        tweets = []
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.bearer_token}"}

            since = (datetime.utcnow() - timedelta(hours=self.hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ")

            for account in self.accounts:
                try:
                    account_tweets = self._fetch_user_tweets(
                        account, since, headers)
                    tweets.extend(account_tweets)
                    if account_tweets:
                        logger.info(f"  @{account}: {len(account_tweets)} tweets")
                    time.sleep(0.5)  # Rate limit courtesy
                except Exception as e:
                    logger.warning(f"  @{account}: fetch failed — {e}")

        except ImportError:
            logger.warning("  requests not available for tweet fetching")
            return []
        except Exception as e:
            logger.error(f"  Tweet fetch failed: {e}")
            return []

        # Filter by engagement
        notable = [t for t in tweets if t.get("likes", 0) >= self.min_likes]
        notable.sort(key=lambda t: t.get("likes", 0), reverse=True)

        logger.info(f"  Tweets: {len(tweets)} total, {len(notable)} notable "
                    f"(>= {self.min_likes} likes)")

        # Cache results
        try:
            cache_data = {"fetched_at": time.time(), "tweets": notable}
            cache_file.write_text(json.dumps(cache_data, indent=2, default=str))
        except Exception:
            pass

        # Save to bundle if provided
        if bundle_path and notable:
            out = bundle_path / "inputs" / "tweets.json"
            out.write_text(json.dumps({
                "fetched_at": datetime.utcnow().isoformat(),
                "accounts_checked": len(self.accounts),
                "total_found": len(tweets),
                "notable_count": len(notable),
                "min_likes": self.min_likes,
                "tweets": notable
            }, indent=2, default=str))

        return notable

    def _fetch_user_tweets(self, username: str, since: str,
                            headers: dict) -> List[dict]:
        """Fetch recent tweets for a specific user via Twitter API v2."""
        import requests

        # First get user ID
        user_url = f"https://api.twitter.com/2/users/by/username/{username}"
        user_resp = requests.get(user_url, headers=headers, timeout=10)
        if user_resp.status_code != 200:
            return []

        user_data = user_resp.json().get("data", {})
        user_id = user_data.get("id")
        if not user_id:
            return []

        # Get tweets
        tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "start_time": since,
            "max_results": 20,
            "tweet.fields": "created_at,public_metrics,text",
            "exclude": "retweets,replies"
        }
        resp = requests.get(tweets_url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return []

        results = []
        for tweet in resp.json().get("data", []):
            metrics = tweet.get("public_metrics", {})
            results.append({
                "tweet_id": tweet["id"],
                "author_handle": f"@{username}",
                "author_name": user_data.get("name", username),
                "text": tweet.get("text", ""),
                "created_at": tweet.get("created_at", ""),
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "url": f"https://x.com/{username}/status/{tweet['id']}"
            })

        return results
