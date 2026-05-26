
"""
X (Twitter) Automation Service
==============================
Handles:
- Auto-engagement with Bitcoin content
- Article posting to X
- Sentiment monitoring
- Follower growth tactics
"""

import os
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# TWEET KILL SWITCH - remove after deploy confirmed
import os
_TWEETS_ENABLED = os.environ.get("ENABLE_TWEETS", "false").lower() == "true"

class XAutomationService:
    """
    Full X/Twitter automation for Protocol Pulse.
    """
    
    def __init__(self):
        self.api_key = os.environ.get("TWITTER_API_KEY", "")
        self.api_secret = os.environ.get("TWITTER_API_SECRET", "")
        self.access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
        self.access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
        self.bearer_token = os.environ.get("TWITTER_BEARER_TOKEN", "")
        self.client = None
        self.client_v2 = None
        self.configured = False
        self._init_clients()
    
    def _init_clients(self):
        """Initialize Twitter API clients - DISABLED."""
        try:
            if self.api_key and self.api_secret and self.access_token and self.access_secret:
                import tweepy
                auth = tweepy.OAuth1UserHandler(self.api_key, self.api_secret, self.access_token, self.access_secret)
                self.client = tweepy.API(auth)
                self.client_v2 = tweepy.Client(
                    bearer_token=self.bearer_token,
                    consumer_key=self.api_key,
                    consumer_secret=self.api_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_secret,
                    wait_on_rate_limit=False
                )
                self.configured = True
                logger.info("XAutomationService clients initialized")
            else:
                logger.warning("X API keys not fully configured")
        except Exception as e:
            logger.error(f"X API init failed: {e}")

    def post_article(self, title: str, url: str, hashtags: List[str] = None) -> Dict:
        """
        Post an article to X with optimized formatting.
        """
        if not self.client_v2:
            return {"success": False, "error": "X API not configured"}
        
        # Generate engaging hook
        # No hooks - the tweet itself should be the hook
        hook = ""
        
        # Build tweet (280 char limit, URL = ~23 chars)
        available = 280 - len(hook) - 25 - 2  # hook + URL + spaces
        
        tags = ""  # NO HASHTAGS — X algorithms penalize them
        
        if len(title) > available:
            title = title[:available-3] + "..."
        
        tweet = f"{hook} {title}\n\n{tags}\n{url}"
        
        try:
            if not _TWEETS_ENABLED:
                logger.info(f'[TWEETS DISABLED] Would have posted: {tweet[:80]}')
                return {'success': False, 'reason': 'tweets disabled'}
            response = self.client_v2.create_tweet(text=tweet)
            tweet_id = response.data["id"]
            
            logger.info(f"Posted to X: {tweet_id}")
            return {
                "success": True,
                "tweet_id": str(tweet_id),
                "text": tweet
            }
            
        except Exception as e:
            logger.error(f"X post failed: {e}")
            return {"success": False, "error": str(e)}
    
    def auto_engage(self, max_actions: int = 5) -> Dict:
        """
        Automatically engage with relevant Bitcoin content.
        Likes high-quality posts from Bitcoin educators.
        """
        if not self.client_v2:
            return {"success": False, "error": "X API not configured", "actions": 0}
        
        actions = []
        
        # Target queries for quality Bitcoin content
        queries = [
            "Bitcoin analysis -is:retweet min_faves:100 lang:en",
            "BTC alpha -is:retweet min_faves:50 lang:en",
            "#Bitcoin education -is:retweet min_faves:20 lang:en",
        ]
        
        try:
            for query in queries:
                if len(actions) >= max_actions:
                    break
                
                try:
                    tweets = self.client_v2.search_recent_tweets(
                        query=query,
                        max_results=10,
                        tweet_fields=["public_metrics", "author_id"]
                    )
                    
                    if not tweets.data:
                        continue
                    
                    for tweet in tweets.data[:2]:
                        if len(actions) >= max_actions:
                            break
                        
                        try:
                            self.client_v2.like(tweet.id)
                            actions.append({
                                "type": "like",
                                "tweet_id": str(tweet.id),
                                "preview": tweet.text[:50]
                            })
                            logger.debug(f"Liked tweet {tweet.id}")
                        except Exception as e:
                            logger.debug(f"Like failed: {e}")
                            
                except Exception as e:
                    logger.debug(f"Query failed: {e}")
            
            return {
                "success": True,
                "actions": len(actions),
                "details": actions
            }
            
        except Exception as e:
            logger.error(f"Auto-engage error: {e}")
            return {"success": False, "error": str(e), "actions": 0}
    
    def get_bitcoin_mentions(self, count: int = 20) -> List[Dict]:
        """Get recent Bitcoin mentions for sentiment analysis."""
        if not self.client_v2:
            return []
        
        try:
            tweets = self.client_v2.search_recent_tweets(
                query="Bitcoin -is:retweet lang:en",
                max_results=count,
                tweet_fields=["public_metrics", "created_at"]
            )
            
            if not tweets.data:
                return []
            
            return [
                {
                    "id": str(t.id),
                    "text": t.text,
                    "likes": t.public_metrics.get("like_count", 0),
                    "retweets": t.public_metrics.get("retweet_count", 0),
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in tweets.data
            ]
            
        except Exception as e:
            logger.error(f"Get mentions error: {e}")
            return []
    
    def get_account_metrics(self) -> Dict:
        """Get our account's performance metrics."""
        if not self.client_v2:
            return {}
        
        try:
            me = self.client_v2.get_me(user_fields=["public_metrics"])
            if not me.data:
                return {}
            
            metrics = me.data.public_metrics or {}
            return {
                "followers": metrics.get("followers_count", 0),
                "following": metrics.get("following_count", 0),
                "tweets": metrics.get("tweet_count", 0),
                "listed": metrics.get("listed_count", 0)
            }
            
        except Exception as e:
            logger.error(f"Get metrics error: {e}")
            return {}


# Singleton
    def post_tweet(self, text: str, image_path: str = None) -> dict:
        """Post a tweet. Wrapper for compatibility."""
        try:
            if not self.client:
                return {"success": False, "error": "X client not initialized"}
            
            if image_path and self.api:
                media = self.api.media_upload(image_path)
                response = self.client.create_tweet(text=text, media_ids=[media.media_id])
            else:
                response = self.client.create_tweet(text=text)
            
            if response and response.data:
                return {
                    "success": True,
                    "tweet_id": response.data.get("id"),
                    "text": text
                }
            return {"success": False, "error": "No response from X API"}
        except Exception as e:
            return {"success": False, "error": str(e)}


x_automation_service = XAutomationService()


# ============================================
# UNIFIED POSTING WITH QUALITY GATE
# ============================================


def post_with_quality_gate(text: str, url: str = None) -> dict:
    """
    Universal posting function with full quality pipeline.
    Use this for ALL automated posts.
    """
    from pp_services.human_voice_filter import humanize
    from pp_services.post_quality_gate import post_quality_gate
    
    # 1. Apply human voice filter
    clean_text = humanize(text)
    
    # 2. If URL provided, verify it works
    if url:
        link_check = post_quality_gate.verify_link(url)
        if not link_check["valid"]:
            return {"error": f"Link failed: {link_check.get('error')}", "posted": False}
        
        # Add URL to text if not already there
        if url not in clean_text:
            clean_text = f"{clean_text}\n\n{url}"
    
    # 3. Verify quality
    quality = post_quality_gate.verify_tweet_quality(clean_text.replace(url, '').strip() if url else clean_text)
    
    if not quality.get("approved", True):
        return {"error": f"Quality rejected: {quality.get('reason')}", "posted": False}
    
    # 4. Post it
    try:
        response = x_automation_service.client_v2.create_tweet(text=clean_text[:280])
        tweet_id = response.data["id"]
        
        logging.info(f"Posted with quality gate: {tweet_id}")
        return {"success": True, "tweet_id": tweet_id, "text": clean_text, "posted": True}
        
    except Exception as e:
        logging.error(f"Post failed: {e}")
        return {"error": str(e), "posted": False}


