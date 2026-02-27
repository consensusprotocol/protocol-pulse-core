import os
_TWEETS_ENABLED = os.environ.get('ENABLE_TWEETS', 'false').lower() == 'true'

import os
import logging
import json
import re
import tempfile
import requests
try:
    import tweepy
except ImportError:
    tweepy = None
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

def _strip_hashtags(text):
    """Remove all hashtags from text - Protocol Pulse never uses hashtags."""
    if not text:
        return text
    return re.sub(r'#\w+\s*', '', text).strip()

class XService:
    def __init__(self):
        self.client = None
        self.client_v2 = None
        self.openai_client = None
        
        try:
            api_key = os.environ.get("TWITTER_API_KEY", "")
            api_secret = os.environ.get("TWITTER_API_SECRET", "")
            access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
            access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
            bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
            
            if api_key and api_secret and access_token and access_secret:
                import tweepy
                auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
                self.client = tweepy.API(auth)
                self.client_v2 = tweepy.Client(
                    bearer_token=bearer,
                    consumer_key=api_key,
                    consumer_secret=api_secret,
                    access_token=access_token,
                    access_token_secret=access_secret,
                    wait_on_rate_limit=False
                )
                logging.info("X/Twitter clients initialized successfully")
            else:
                logging.warning("X/Twitter API keys not fully configured")
        except Exception as e:
            logging.error(f"X/Twitter client init failed: {e}")
        
        self.openai_client = (OpenAI(api_key=os.environ.get('OPENAI_API_KEY')) if OpenAI and os.environ.get('OPENAI_API_KEY') else None)
        
    def get_feedback(self, handle):
        if not self.client:
            return [{'id': 'mock_id', 'text': f'Mock tweet from @{handle}', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
        try:
            tweets = self.client.search_recent_tweets(query=f'from:{handle} -is:retweet', max_results=10, expansions='referenced_tweets.id').data or []
            filtered = []
            for tweet in tweets:
                if not hasattr(tweet, 'referenced_tweets') or not tweet.referenced_tweets:
                    relevance = self._is_relevant(tweet.text)
                    if relevance['is_relevant']:
                        filtered.append({'id': tweet.id, 'text': tweet.text, 'is_relevant': True, 'topic': relevance['topic'], 'nuance': relevance['nuance']})
            return filtered
        except Exception as e:
            logging.error(f"X API error: {e}")
            return [{'id': 'mock_id', 'text': f'Mock tweet from @{handle}', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
    
    def _is_relevant(self, text):
        if not self.openai_client:
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}
        if len(text.split()) < 10 or any(m in text.lower() for m in ['lol', '😂', 'meme']):
            return {'is_relevant': False}
        try:
            response = self.openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': f"Analyze tweet: '{text}'. Is it relevant to Web3/Bitcoin/DeFi? If yes, extract topic and nuance. Return JSON: {{'is_relevant': bool, 'topic': str, 'nuance': str}}"}],
                max_tokens=100
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Relevance analysis error: {e}")
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}

    def post_article_tweet(self, article, base_url=''):
        """Route article tweets through unified quality gate."""
        if not self.client and not self.client_v2:
            logging.warning("Twitter API not configured - skipping tweet")
            return None
        if not _TWEETS_ENABLED:
            logging.info('[TWEETS DISABLED] Skipping article tweet')
            return None
        try:
            from services.unified_post_gate import unified_post_gate
            result = unified_post_gate.process_article_post(
                article.id,
                article.title,
                getattr(article, 'summary', '') or ''
            )
            if result.get("approved") and result.get("tweet_text"):
                tweet_text = result["tweet_text"][:280]
                if self.client_v2:
                    r = self.client_v2.create_tweet(text=tweet_text)
                    return str(r.data["id"]) if r and r.data else None
                elif self.client:
                    response = self.client.update_status(tweet_text)
                    return response.id
            else:
                logging.info(f"Tweet rejected by quality gate: {result.get('rejection_reason', 'unknown')}")
                return None
        except Exception as e:
            logging.error(f"Failed to post tweet: {e}")
            return None

    # ... rest of your velocity and video methods stay the same ...

    def get_upload_status(self):
        return {
            'configured': self.client is not None,
            'v2_available': self.client_v2 is not None,
            'can_post_video': self.client is not None
        }

    def post_reply(self, tweet_id, text):
        """
        Post a reply to a tweet (for Zap-Comment / Diplomat bridge).
        Returns reply tweet id or None.
        """
        text = _strip_hashtags(text)
        if len(text) > 280:
            text = text[:277] + "..."
        try:
            if self.client_v2:
                if not _TWEETS_ENABLED:
                    logging.info(f'[TWEETS DISABLED]')
                    return None
                r = self.client_v2.create_tweet(text=text, in_reply_to_tweet_id=str(tweet_id))
                if r and r.data and getattr(r.data, "id", None):
                    return str(r.data.id)
            if self.client:
                resp = self.client.update_status(status=text, in_reply_to_status_id=str(tweet_id))
                return str(resp.id) if resp else None
        except Exception as e:
            logging.error("post_reply failed: %s", e)
        return None

    def _get_branded_pulse_path(self):
        """Path to Protocol Pulse branded logo (cover + pulse). Fallback to main logo if brand asset missing."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        brand_path = os.path.join(base, "static", "images", "brand", "pp-pulse-brand.png")
        if os.path.isfile(brand_path):
            return brand_path
        fallback = os.path.join(base, "static", "images", "protocol-pulse-logo.png")
        return fallback if os.path.isfile(fallback) else None

    def post_dual_image_news(self, text, cover_url, dry_run=False):
        """
        Post a breaking-news tweet with two images: (1) cover/header from the story, (2) Protocol Pulse branded pulse logo.
        Builds trust and brand consistency across X (IG/Nostr later).
        Returns tweet id or None. If dry_run=True, returns dict with draft text and image urls/paths without posting.
        """
        text = _strip_hashtags(text)
        if len(text) > 280:
            text = text[:277] + "..."
        branded_path = self._get_branded_pulse_path()
        if not branded_path:
            logging.warning("No branded pulse image found; dual-image post may fail.")
        if dry_run:
            return {
                "dry_run": True,
                "text": text,
                "cover_url": cover_url,
                "branded_path": branded_path,
                "message": "Would post to X with 2 images (cover + branded)." if self.client else "X API not configured."
            }
        if not self.client:
            logging.warning("X API not configured - skipping dual-image post")
            return None
        try:
            media_ids = []
            # Download cover image to temp file
            if cover_url:
                r = requests.get(cover_url, timeout=15)
                r.raise_for_status()
                ext = "jpg" if "jpeg" in (r.headers.get("content-type") or "").lower() or cover_url.lower().endswith((".jpg", ".jpeg")) else "png"
                with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                    tmp.write(r.content)
                    tmp.flush()
                    try:
                        media_ids.append(self.client.media_upload(tmp.name).media_id_string)
                    finally:
                        try:
                            os.unlink(tmp.name)
                        except OSError:
                            pass
            if branded_path:
                media_ids.append(self.client.media_upload(branded_path).media_id_string)
            if not media_ids:
                logging.warning("No media uploaded for dual-image post; posting text only.")
            response = self.client.update_status(status=text, media_ids=media_ids)
            return response.id
        except Exception as e:
            logging.error("Dual-image news post failed: %s", e)
            return None

# Backward compatibility functions

    def post_tweet(self, text: str, image_path: str = None) -> dict:
        """Post a simple tweet, optionally with an image"""
        if not self.client_v2:
            return {"error": "Twitter client not initialized"}
        
        try:
            text = _strip_hashtags(text)
            
            if image_path:
                media = self.client.media_upload(image_path)
                response = self.client_v2.create_tweet(text=text, media_ids=[media.media_id])
            else:
                response = self.client_v2.create_tweet(text=text)
            
            return {"success": True, "tweet_id": response.data['id']}
        except Exception as e:
            return {"error": str(e)}


# Backward compatibility functions
def get_social_feedback(topic):
    """Get social feedback for backward compatibility"""
    return {
        'sentiment': 'neutral',
        'sentiment_score': 0.5,
        'key_insights': [f"Mock insight about {topic}", "Community discussion ongoing", "Market watching closely"],
        'source': 'stubbed_data'
    }


# ============================================================
# MODULE-LEVEL WRAPPERS — used by Comment Radar & Engagement Engine
# ============================================================
_x_instance = None

def _get_x():
    global _x_instance
    if _x_instance is None:
        _x_instance = XService()
    return _x_instance

def post_tweet(text, image_path=None):
    """Post a tweet. Returns dict with 'id' or None."""
    x = _get_x()
    return x.post_tweet(text, image_path)

def reply_to_tweet(tweet_id, text):
    """Reply to a tweet. Returns dict with 'id' or None."""
    x = _get_x()
    return x.post_reply(tweet_id, text)

def quote_tweet(text, url=None):
    """Post a quote tweet (text + url). Returns dict with 'id' or None."""
    x = _get_x()
    if url:
        text = f"{text} {url}".strip()[:280]
    return x.post_tweet(text)
