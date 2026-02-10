"""
Lightweight X (Twitter) client for the Sovereign Sentry.

Responsible for:
- Initializing tweepy client using X_* or TWITTER_* env vars
- Fetching latest tweets from monitored accounts
- Posting replies
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

try:
    import tweepy  # type: ignore
except ImportError:  # pragma: no cover
    tweepy = None

logger = logging.getLogger(__name__)


def _get_env(var: str, fallback: str) -> str:
    """Support both new X_* and legacy TWITTER_* env names."""
    return os.environ.get(var) or os.environ.get(fallback) or ""


class XClient:
    """Wrapper around tweepy for v2 timelines + v1.1 replies."""

    def __init__(self) -> None:
        self.client_v2 = None
        self.client_v1 = None

        if tweepy is None:
            logger.warning("tweepy not installed; XClient is in dry-run mode.")
            return

        api_key = _get_env("X_API_KEY", "TWITTER_API_KEY")
        api_secret = _get_env("X_API_SECRET", "TWITTER_API_SECRET")
        access_token = _get_env("X_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN")
        access_secret = _get_env("X_ACCESS_TOKEN_SECRET", "TWITTER_ACCESS_TOKEN_SECRET")
        bearer = _get_env("X_BEARER_TOKEN", "TWITTER_BEARER_TOKEN")

        if not (api_key and api_secret and access_token and access_secret and bearer):
            logger.warning("XClient: missing X/Twitter env vars; operating in dry-run mode.")
            return

        try:
            # v2 client for reading timelines
            self.client_v2 = tweepy.Client(
                bearer_token=bearer,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret,
                wait_on_rate_limit=True,
            )

            # v1.1 client for posting replies with media if needed
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            self.client_v1 = tweepy.API(auth, wait_on_rate_limit=True)
            logger.info("XClient initialized (v1.1 + v2).")
        except Exception as e:  # pragma: no cover
            logger.error("Failed to initialize XClient: %s", e)
            self.client_v1 = None
            self.client_v2 = None

    @property
    def configured(self) -> bool:
        return self.client_v2 is not None and self.client_v1 is not None

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch_latest_tweets(
        self,
        handle: str,
        since_id: str | None = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent tweets from a handle (excluding replies and retweets).
        Returns list of dicts with id, text, created_at.
        """
        if not self.client_v2 or tweepy is None:
            logger.debug("XClient.fetch_latest_tweets dry-run for @%s", handle)
            return []

        try:
            user = self.client_v2.get_user(username=handle.strip())
            user_id = user.data.id if user and user.data else None
            if not user_id:
                return []

            params = {
                "exclude": ["retweets", "replies"],
                "max_results": max_results,
                "tweet_fields": ["created_at"],
            }
            if since_id:
                params["since_id"] = since_id

            res = self.client_v2.get_users_tweets(id=user_id, **params)
            if not res or not res.data:
                return []

            tweets: List[Dict[str, Any]] = []
            for t in res.data:
                tweets.append(
                    {
                        "id": str(t.id),
                        "text": t.text,
                        "created_at": t.created_at.replace(tzinfo=timezone.utc) if t.created_at else None,
                    }
                )
            return tweets
        except Exception as e:  # pragma: no cover
            logger.warning("XClient.fetch_latest_tweets error for @%s: %s", handle, e)
            return []

    # ------------------------------------------------------------------
    # Post
    # ------------------------------------------------------------------

    def post_reply(self, in_reply_to_tweet_id: str, text: str) -> Dict[str, Any]:
        """
        Post a reply tweet. Returns dict with { success, tweet_id, raw }.
        If client not configured, returns dry-run payload.
        """
        text = text.strip()
        if len(text) > 280:
            text = text[:277] + "..."

        if not self.client_v1 or tweepy is None:
            logger.info("XClient.post_reply dry-run: %s", text)
            return {
                "success": True,
                "tweet_id": None,
                "raw": {"dry_run": True, "text": text, "in_reply_to_status_id": in_reply_to_tweet_id},
            }

        try:
            status = self.client_v1.update_status(
                status=text,
                in_reply_to_status_id=in_reply_to_tweet_id,
                auto_populate_reply_metadata=True,
            )
            return {"success": True, "tweet_id": str(getattr(status, "id", None)), "raw": getattr(status, "_json", {})}
        except Exception as e:  # pragma: no cover
            logger.error("Failed to post reply to %s: %s", in_reply_to_tweet_id, e)
            return {"success": False, "tweet_id": None, "raw": {"error": str(e)}}

