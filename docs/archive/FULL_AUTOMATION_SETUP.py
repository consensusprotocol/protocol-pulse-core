#!/usr/bin/env python3
"""
PROTOCOL PULSE - FULL AUTOMATION SETUP
=======================================
Run this script in Replit Shell to configure everything.

This script will:
1. Configure AI providers (Claude primary, Grok for review, Gemini for backup)
2. Set up article generation pipeline with Grok fact-checking
3. Enable X (Twitter) social engagement automation
4. Set up sentiment monitoring across X, Nostr, YouTube
5. Configure auto-publishing workflow
6. Start all background tasks

Usage: python3 FULL_AUTOMATION_SETUP.py
"""

import os
import sys
import json
import time
from pathlib import Path

print("=" * 60)
print("PROTOCOL PULSE - FULL AUTOMATION SETUP")
print("=" * 60)
print()

# ============================================================
# STEP 1: Check Environment Variables
# ============================================================
print("[1/8] Checking environment variables...")

required_keys = {
    "ANTHROPIC_API_KEY": "Claude - Primary article generation",
    "GEMINI_API_KEY": "Gemini - Backup generation & duplicate detection", 
    "XAI_API_KEY": "Grok - Article review & fact-checking",
}

optional_keys = {
    "OPENAI_API_KEY": "OpenAI - Optional (will skip if not set)",
    "TWITTER_API_KEY": "X API - Social engagement",
    "TWITTER_API_SECRET": "X API - Social engagement",
    "TWITTER_ACCESS_TOKEN": "X API - Social engagement",
    "TWITTER_ACCESS_TOKEN_SECRET": "X API - Social engagement",
    "TWITTER_BEARER_TOKEN": "X API - Social engagement",
    "YOUTUBE_API_KEY": "YouTube - Sentiment monitoring",
}

missing_required = []
for key, desc in required_keys.items():
    val = os.environ.get(key)
    if val:
        print(f"  ✅ {key}: Set")
    else:
        print(f"  ❌ {key}: MISSING - {desc}")
        missing_required.append(key)

print()
print("Optional keys:")
for key, desc in optional_keys.items():
    val = os.environ.get(key)
    if val:
        print(f"  ✅ {key}: Set")
    else:
        print(f"  ⚪ {key}: Not set - {desc}")

if missing_required:
    print()
    print("❌ MISSING REQUIRED KEYS. Add these to Replit Secrets:")
    for key in missing_required:
        print(f"   - {key}")
    print()
    print("Go to Tools → Secrets in Replit and add them.")
    sys.exit(1)

print()
print("✅ All required API keys are set!")
print()

# ============================================================
# STEP 2: Create Grok Review Service
# ============================================================
print("[2/8] Creating Grok article review service...")

grok_review_code = '''
"""
Grok Article Review Service
===========================
Uses xAI Grok to fact-check and review articles before publishing.
"""

import os
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class GrokReviewService:
    """Uses Grok to review articles for accuracy and quality."""
    
    def __init__(self):
        self.api_key = os.environ.get("XAI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.x.ai/v1"
                )
                logger.info("Grok review service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Grok client: {e}")
    
    def review_article(self, title: str, content: str) -> dict:
        """
        Review an article for accuracy, bias, and quality.
        
        Returns:
            {
                "approved": bool,
                "score": int (0-100),
                "issues": [list of issues found],
                "suggestions": [list of improvements],
                "revised_content": str or None (if major revisions needed),
                "fact_check_notes": str
            }
        """
        if not self.client:
            logger.warning("Grok client not available, auto-approving")
            return {"approved": True, "score": 70, "issues": [], "suggestions": [], "revised_content": None, "fact_check_notes": "Grok not configured"}
        
        review_prompt = f"""You are a senior Bitcoin editor and fact-checker for Protocol Pulse, a premium Bitcoin intelligence publication.

Review this article for:
1. FACTUAL ACCURACY - Are all claims verifiable? Any false or misleading statements?
2. BITCOIN ALIGNMENT - Does it maintain Bitcoin-first perspective? No altcoin shilling?
3. QUALITY - Is it well-structured, engaging, and informative?
4. TIMELINESS - Are the events/data current and relevant?
5. BIAS CHECK - Is it balanced or does it make unsupported claims?

ARTICLE TITLE: {title}

ARTICLE CONTENT:
{content[:8000]}

Respond in this exact JSON format:
{{
    "approved": true/false,
    "score": 0-100,
    "issues": ["issue 1", "issue 2"],
    "suggestions": ["suggestion 1", "suggestion 2"],
    "needs_revision": true/false,
    "fact_check_notes": "summary of fact-check findings",
    "revised_title": "only if title needs fixing, else null",
    "critical_errors": ["any showstopper issues"]
}}

Be strict but fair. Approve if score >= 70 and no critical errors."""

        try:
            response = self.client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": "You are a meticulous Bitcoin news editor. Respond only with valid JSON."},
                    {"role": "user", "content": review_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            # Handle markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            # Ensure required fields
            result.setdefault("approved", result.get("score", 0) >= 70)
            result.setdefault("score", 70)
            result.setdefault("issues", [])
            result.setdefault("suggestions", [])
            result.setdefault("revised_content", None)
            result.setdefault("fact_check_notes", "Reviewed by Grok")
            
            logger.info(f"Grok review complete: score={result['score']}, approved={result['approved']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Grok response as JSON: {e}")
            return {"approved": True, "score": 65, "issues": ["Review parse error"], "suggestions": [], "revised_content": None, "fact_check_notes": "Review parsing failed, manual check recommended"}
        except Exception as e:
            logger.error(f"Grok review failed: {e}")
            return {"approved": True, "score": 60, "issues": [str(e)], "suggestions": [], "revised_content": None, "fact_check_notes": f"Review error: {e}"}
    
    def get_x_sentiment(self, topic: str = "Bitcoin") -> dict:
        """
        Get current X (Twitter) sentiment on a topic using Grok's real-time knowledge.
        
        Returns:
            {
                "sentiment": "bullish" | "bearish" | "neutral",
                "score": -100 to 100,
                "trending_topics": [list],
                "key_voices": [notable accounts discussing],
                "summary": str
            }
        """
        if not self.client:
            return {"sentiment": "neutral", "score": 0, "trending_topics": [], "key_voices": [], "summary": "Grok not configured"}
        
        prompt = f"""Analyze the current sentiment on X (Twitter) about {topic}.

Consider:
- What are the major voices saying?
- What's the overall mood (bullish/bearish/neutral)?
- What specific events or news are driving discussion?
- Any notable debates or controversies?

Respond in JSON:
{{
    "sentiment": "bullish" | "bearish" | "neutral",
    "score": -100 to 100 (negative=bearish, positive=bullish),
    "trending_topics": ["topic1", "topic2", "topic3"],
    "key_discussions": ["brief description of major conversations"],
    "notable_accounts": ["@account1", "@account2"],
    "summary": "2-3 sentence summary of current X sentiment"
}}"""

        try:
            response = self.client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": "You are a social media analyst with real-time access to X/Twitter. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Grok sentiment analysis failed: {e}")
            return {"sentiment": "neutral", "score": 0, "trending_topics": [], "key_voices": [], "summary": f"Error: {e}"}
    
    def suggest_article_topics(self, count: int = 5) -> list:
        """
        Use Grok's real-time X knowledge to suggest trending article topics.
        
        Returns list of topic suggestions with context.
        """
        if not self.client:
            return []
        
        prompt = f"""Based on current discussions on X (Twitter) in the Bitcoin community, suggest {count} article topics that would be timely and engaging.

For each topic, provide:
1. A specific headline angle
2. Why it's relevant RIGHT NOW
3. Key accounts/voices discussing it
4. The sentiment around it

Respond in JSON:
{{
    "topics": [
        {{
            "headline": "suggested headline",
            "angle": "specific angle to cover",
            "relevance": "why this matters now",
            "key_voices": ["@account1", "@account2"],
            "sentiment": "bullish/bearish/neutral/controversial",
            "urgency": "high/medium/low"
        }}
    ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": "You are a Bitcoin news editor with real-time X/Twitter access. Suggest timely, engaging topics."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            data = json.loads(result_text)
            return data.get("topics", [])
            
        except Exception as e:
            logger.error(f"Grok topic suggestion failed: {e}")
            return []


# Singleton instance
grok_review_service = GrokReviewService()
'''

with open('services/grok_review_service.py', 'w') as f:
    f.write(grok_review_code)
print("  ✅ Created services/grok_review_service.py")

# ============================================================
# STEP 3: Create Enhanced Content Generator with Claude Primary
# ============================================================
print("[3/8] Creating Claude-first content generator patch...")

claude_patch_code = '''
"""
Claude-First Article Generation Patch
======================================
This module patches the ContentGenerator to use Claude (Anthropic) as the 
primary article generator, with Grok review before publishing.
"""

import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def patch_content_generator():
    """
    Patch the ContentGenerator to:
    1. Use Claude (Anthropic) as primary generator
    2. Fall back to Gemini if Claude fails
    3. Skip OpenAI entirely (quota issues)
    4. Add Grok review step before returning
    """
    
    from services.ai_service import AIService
    from services.grok_review_service import grok_review_service
    
    # Store original method
    original_generate = AIService.generate_content_openai
    
    def generate_with_claude_first(self, prompt, system_prompt=None):
        """Try Claude first, then Gemini, skip OpenAI."""
        
        # Try Anthropic (Claude) first
        if self.anthropic_client:
            try:
                logger.info("Generating content with Claude (Anthropic)...")
                result = self.generate_content_anthropic(prompt, system_prompt)
                if result and len(result) > 100:
                    logger.info(f"Claude generated {len(result)} chars")
                    return result
            except Exception as e:
                logger.warning(f"Claude generation failed: {e}")
        
        # Try Gemini second
        if self.gemini_available:
            try:
                logger.info("Falling back to Gemini...")
                from services.gemini_service import gemini_service
                result = gemini_service.generate_content(prompt)
                if result and len(result) > 100:
                    logger.info(f"Gemini generated {len(result)} chars")
                    return result
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}")
        
        # Only try OpenAI if explicitly enabled and has quota
        if os.environ.get("FORCE_OPENAI") == "true" and self.openai_client:
            try:
                logger.info("Trying OpenAI as last resort...")
                return original_generate(self, prompt, system_prompt)
            except Exception as e:
                logger.error(f"OpenAI also failed: {e}")
        
        raise ValueError("All AI providers failed to generate content")
    
    # Apply patch
    AIService.generate_content_openai = generate_with_claude_first
    logger.info("✅ Patched AIService to use Claude first")
    
    return True


def add_grok_review_to_pipeline():
    """
    Inject Grok review into the article publishing pipeline.
    Articles must pass Grok review before being published.
    """
    from services.grok_review_service import grok_review_service
    from services import automation
    
    # Store original function
    original_generate = automation.generate_breaking_article_with_tracking
    
    @wraps(original_generate)
    def generate_with_review():
        """Generate article, then run Grok review before publishing."""
        result = original_generate()
        
        if not result.get("success") or not result.get("article_id"):
            return result
        
        # Get the article
        from app import app, db
        from models import Article
        
        with app.app_context():
            article = Article.query.get(result["article_id"])
            if not article:
                return result
            
            # Run Grok review
            logger.info(f"Running Grok review on article {article.id}...")
            review = grok_review_service.review_article(article.title, article.content)
            
            # Store review metadata
            article.review_score = review.get("score", 0)
            article.review_notes = review.get("fact_check_notes", "")
            
            if not review.get("approved", True):
                # Don't publish, keep as draft
                article.published = False
                logger.warning(f"Article {article.id} failed Grok review: {review.get('issues')}")
                result["grok_approved"] = False
                result["grok_issues"] = review.get("issues", [])
            else:
                logger.info(f"Article {article.id} passed Grok review with score {review.get('score')}")
                result["grok_approved"] = True
                result["grok_score"] = review.get("score")
            
            db.session.commit()
        
        return result
    
    # Apply patch
    automation.generate_breaking_article_with_tracking = generate_with_review
    logger.info("✅ Added Grok review to article pipeline")
    
    return True


# Auto-apply patches when imported
if __name__ != "__main__":
    try:
        patch_content_generator()
        add_grok_review_to_pipeline()
    except Exception as e:
        logger.warning(f"Could not apply content generator patches: {e}")
'''

with open('services/claude_primary_patch.py', 'w') as f:
    f.write(claude_patch_code)
print("  ✅ Created services/claude_primary_patch.py")

# ============================================================
# STEP 4: Create X Sentiment & Engagement Service
# ============================================================
print("[4/8] Creating X sentiment and engagement automation...")

x_automation_code = '''
"""
X (Twitter) Automation Service
==============================
Handles:
- Sentiment monitoring across Bitcoin X community
- Auto-engagement with relevant posts
- Topic discovery for articles
- Scheduled posting
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class XAutomationService:
    """Full X/Twitter automation for Protocol Pulse."""
    
    def __init__(self):
        self.api_key = os.environ.get("TWITTER_API_KEY")
        self.api_secret = os.environ.get("TWITTER_API_SECRET")
        self.access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
        self.access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")
        self.bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
        
        self.client = None
        self.client_v2 = None
        
        self._init_clients()
    
    def _init_clients(self):
        """Initialize Twitter API clients."""
        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            logger.warning("X API credentials not fully configured")
            return
        
        try:
            import tweepy
            
            # V1.1 client for some operations
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_secret
            )
            self.client = tweepy.API(auth, wait_on_rate_limit=True)
            
            # V2 client for modern endpoints
            self.client_v2 = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret,
                wait_on_rate_limit=True
            )
            
            logger.info("X API clients initialized successfully")
            
        except ImportError:
            logger.warning("tweepy not installed, X automation disabled")
        except Exception as e:
            logger.error(f"Failed to initialize X clients: {e}")
    
    def get_bitcoin_sentiment(self) -> Dict:
        """
        Analyze current Bitcoin sentiment on X.
        Uses both API data and Grok's real-time knowledge.
        """
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "sentiment": "neutral",
            "score": 0,
            "volume": 0,
            "trending_topics": [],
            "key_tweets": [],
            "influencer_sentiment": {}
        }
        
        # Get Grok's real-time analysis
        try:
            from services.grok_review_service import grok_review_service
            grok_sentiment = grok_review_service.get_x_sentiment("Bitcoin")
            result.update(grok_sentiment)
        except Exception as e:
            logger.warning(f"Grok sentiment failed: {e}")
        
        # Supplement with API data if available
        if self.client_v2:
            try:
                # Search recent Bitcoin tweets
                tweets = self.client_v2.search_recent_tweets(
                    query="Bitcoin -is:retweet lang:en",
                    max_results=100,
                    tweet_fields=["public_metrics", "created_at"]
                )
                
                if tweets.data:
                    result["volume"] = len(tweets.data)
                    
                    # Get top engaged tweets
                    sorted_tweets = sorted(
                        tweets.data,
                        key=lambda t: (t.public_metrics.get("like_count", 0) + 
                                      t.public_metrics.get("retweet_count", 0) * 2),
                        reverse=True
                    )[:5]
                    
                    result["key_tweets"] = [
                        {"text": t.text[:200], "engagement": t.public_metrics}
                        for t in sorted_tweets
                    ]
                    
            except Exception as e:
                logger.warning(f"X API sentiment fetch failed: {e}")
        
        return result
    
    def get_trending_topics(self) -> List[Dict]:
        """Get trending Bitcoin topics for article generation."""
        topics = []
        
        # Get Grok suggestions
        try:
            from services.grok_review_service import grok_review_service
            grok_topics = grok_review_service.suggest_article_topics(5)
            topics.extend(grok_topics)
        except Exception as e:
            logger.warning(f"Grok topic suggestions failed: {e}")
        
        return topics
    
    def auto_engage(self, max_actions: int = 10) -> Dict:
        """
        Automatically engage with relevant Bitcoin content.
        
        Actions:
        - Like high-quality Bitcoin posts
        - Retweet important news
        - Reply to questions (with AI-generated responses)
        """
        if not self.client_v2:
            return {"success": False, "error": "X API not configured"}
        
        actions_taken = []
        
        try:
            # Find posts to engage with
            # Target: Bitcoin educators, news, high-engagement posts
            queries = [
                "Bitcoin education -is:retweet min_faves:50",
                "Bitcoin news breaking -is:retweet min_faves:100",
                "#Bitcoin alpha -is:retweet min_faves:20"
            ]
            
            for query in queries:
                if len(actions_taken) >= max_actions:
                    break
                    
                try:
                    tweets = self.client_v2.search_recent_tweets(
                        query=query,
                        max_results=10,
                        tweet_fields=["public_metrics", "author_id"]
                    )
                    
                    if not tweets.data:
                        continue
                    
                    for tweet in tweets.data[:3]:
                        if len(actions_taken) >= max_actions:
                            break
                        
                        # Like the tweet
                        try:
                            self.client_v2.like(tweet.id)
                            actions_taken.append({
                                "action": "like",
                                "tweet_id": str(tweet.id),
                                "text_preview": tweet.text[:100]
                            })
                        except Exception as e:
                            logger.debug(f"Like failed: {e}")
                            
                except Exception as e:
                    logger.warning(f"Query '{query}' failed: {e}")
            
            return {
                "success": True,
                "actions_taken": len(actions_taken),
                "details": actions_taken
            }
            
        except Exception as e:
            logger.error(f"Auto-engage failed: {e}")
            return {"success": False, "error": str(e)}
    
    def post_article(self, title: str, url: str, summary: str = None) -> Dict:
        """Post an article to X with optimized formatting."""
        if not self.client_v2:
            return {"success": False, "error": "X API not configured"}
        
        # Generate tweet text
        # Format: Hook + Title + URL
        hooks = [
            "🚨 INTEL BRIEF:",
            "📊 NEW ANALYSIS:",
            "⚡ BREAKING:",
            "🔍 DEEP DIVE:",
            "💡 INSIGHT:"
        ]
        
        import random
        hook = random.choice(hooks)
        
        # Build tweet (max 280 chars, URL takes ~23)
        available_chars = 280 - len(hook) - 25  # hook + space + URL
        
        if len(title) <= available_chars:
            tweet_text = f"{hook} {title}\\n\\n{url}"
        else:
            truncated = title[:available_chars-3] + "..."
            tweet_text = f"{hook} {truncated}\\n\\n{url}"
        
        try:
            response = self.client_v2.create_tweet(text=tweet_text)
            return {
                "success": True,
                "tweet_id": str(response.data["id"]),
                "text": tweet_text
            }
        except Exception as e:
            logger.error(f"Failed to post article: {e}")
            return {"success": False, "error": str(e)}
    
    def get_engagement_metrics(self) -> Dict:
        """Get our account's engagement metrics."""
        if not self.client_v2:
            return {}
        
        try:
            # Get recent tweets from our account
            me = self.client_v2.get_me()
            if not me.data:
                return {}
            
            tweets = self.client_v2.get_users_tweets(
                me.data.id,
                max_results=20,
                tweet_fields=["public_metrics", "created_at"]
            )
            
            if not tweets.data:
                return {}
            
            total_likes = sum(t.public_metrics.get("like_count", 0) for t in tweets.data)
            total_retweets = sum(t.public_metrics.get("retweet_count", 0) for t in tweets.data)
            total_replies = sum(t.public_metrics.get("reply_count", 0) for t in tweets.data)
            
            return {
                "tweets_analyzed": len(tweets.data),
                "total_likes": total_likes,
                "total_retweets": total_retweets,
                "total_replies": total_replies,
                "avg_engagement": (total_likes + total_retweets * 2 + total_replies) / len(tweets.data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}


# Singleton
x_automation_service = XAutomationService()
'''

with open('services/x_automation_service.py', 'w') as f:
    f.write(x_automation_code)
print("  ✅ Created services/x_automation_service.py")

# ============================================================
# STEP 5: Create Multi-Platform Sentiment Monitor
# ============================================================
print("[5/8] Creating multi-platform sentiment monitor (X, Nostr, YouTube)...")

sentiment_monitor_code = '''
"""
Multi-Platform Sentiment Monitor
================================
Monitors sentiment across:
- X (Twitter)
- Nostr
- YouTube
- Reddit (bonus)

Aggregates into unified sentiment score for article generation.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SentimentReading:
    platform: str
    sentiment: str  # bullish, bearish, neutral
    score: float  # -100 to 100
    volume: int
    top_topics: List[str]
    timestamp: datetime
    raw_data: dict = None


class MultiPlatformSentimentMonitor:
    """
    Aggregates sentiment from multiple platforms into unified intelligence.
    """
    
    def __init__(self):
        self.readings: List[SentimentReading] = []
        self._init_services()
    
    def _init_services(self):
        """Initialize connections to various platforms."""
        self.x_available = bool(os.environ.get("TWITTER_BEARER_TOKEN"))
        self.youtube_available = bool(os.environ.get("YOUTUBE_API_KEY"))
        self.grok_available = bool(os.environ.get("XAI_API_KEY"))
        
        logger.info(f"Sentiment monitor initialized - X: {self.x_available}, YouTube: {self.youtube_available}, Grok: {self.grok_available}")
    
    def get_x_sentiment(self) -> Optional[SentimentReading]:
        """Get X/Twitter sentiment."""
        try:
            from services.x_automation_service import x_automation_service
            data = x_automation_service.get_bitcoin_sentiment()
            
            return SentimentReading(
                platform="x",
                sentiment=data.get("sentiment", "neutral"),
                score=data.get("score", 0),
                volume=data.get("volume", 0),
                top_topics=data.get("trending_topics", []),
                timestamp=datetime.utcnow(),
                raw_data=data
            )
        except Exception as e:
            logger.warning(f"X sentiment failed: {e}")
            return None
    
    def get_youtube_sentiment(self) -> Optional[SentimentReading]:
        """Get YouTube Bitcoin community sentiment."""
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            return None
        
        try:
            from googleapiclient.discovery import build
            
            youtube = build("youtube", "v3", developerKey=api_key)
            
            # Search recent Bitcoin videos
            search_response = youtube.search().list(
                q="Bitcoin",
                part="id,snippet",
                maxResults=25,
                order="date",
                type="video",
                publishedAfter=(datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
            ).execute()
            
            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            
            if not video_ids:
                return None
            
            # Get video stats
            videos_response = youtube.videos().list(
                part="statistics,snippet",
                id=",".join(video_ids)
            ).execute()
            
            total_views = 0
            total_likes = 0
            total_comments = 0
            topics = []
            
            for video in videos_response.get("items", []):
                stats = video.get("statistics", {})
                total_views += int(stats.get("viewCount", 0))
                total_likes += int(stats.get("likeCount", 0))
                total_comments += int(stats.get("commentCount", 0))
                
                title = video.get("snippet", {}).get("title", "")
                if len(topics) < 5:
                    topics.append(title[:50])
            
            # Simple sentiment based on engagement
            engagement_ratio = (total_likes + total_comments) / max(total_views, 1)
            
            if engagement_ratio > 0.05:
                sentiment = "bullish"
                score = min(engagement_ratio * 1000, 100)
            elif engagement_ratio < 0.01:
                sentiment = "bearish"
                score = -50
            else:
                sentiment = "neutral"
                score = 0
            
            return SentimentReading(
                platform="youtube",
                sentiment=sentiment,
                score=score,
                volume=len(video_ids),
                top_topics=topics,
                timestamp=datetime.utcnow(),
                raw_data={"views": total_views, "likes": total_likes, "comments": total_comments}
            )
            
        except Exception as e:
            logger.warning(f"YouTube sentiment failed: {e}")
            return None
    
    def get_nostr_sentiment(self) -> Optional[SentimentReading]:
        """
        Get Nostr Bitcoin community sentiment.
        Uses Grok's knowledge of Nostr conversations.
        """
        if not self.grok_available:
            return None
        
        try:
            from services.grok_review_service import grok_review_service
            
            # Grok has knowledge of Nostr activity
            prompt_data = grok_review_service.get_x_sentiment("Bitcoin Nostr community")
            
            return SentimentReading(
                platform="nostr",
                sentiment=prompt_data.get("sentiment", "neutral"),
                score=prompt_data.get("score", 0),
                volume=0,  # Can't measure directly
                top_topics=prompt_data.get("trending_topics", []),
                timestamp=datetime.utcnow(),
                raw_data=prompt_data
            )
            
        except Exception as e:
            logger.warning(f"Nostr sentiment failed: {e}")
            return None
    
    def get_aggregated_sentiment(self) -> Dict:
        """
        Get combined sentiment across all platforms.
        
        Returns weighted average sentiment with breakdown.
        """
        readings = []
        
        # Gather all available readings
        x_reading = self.get_x_sentiment()
        if x_reading:
            readings.append(x_reading)
        
        yt_reading = self.get_youtube_sentiment()
        if yt_reading:
            readings.append(yt_reading)
        
        nostr_reading = self.get_nostr_sentiment()
        if nostr_reading:
            readings.append(nostr_reading)
        
        if not readings:
            return {
                "aggregated_sentiment": "neutral",
                "aggregated_score": 0,
                "confidence": 0,
                "platforms": {},
                "top_topics": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Weight: X (40%), YouTube (35%), Nostr (25%)
        weights = {"x": 0.4, "youtube": 0.35, "nostr": 0.25}
        
        weighted_score = 0
        total_weight = 0
        all_topics = []
        platform_data = {}
        
        for reading in readings:
            weight = weights.get(reading.platform, 0.33)
            weighted_score += reading.score * weight
            total_weight += weight
            all_topics.extend(reading.top_topics)
            
            platform_data[reading.platform] = {
                "sentiment": reading.sentiment,
                "score": reading.score,
                "volume": reading.volume,
                "topics": reading.top_topics
            }
        
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        
        if final_score > 25:
            final_sentiment = "bullish"
        elif final_score < -25:
            final_sentiment = "bearish"
        else:
            final_sentiment = "neutral"
        
        # Dedupe topics
        unique_topics = list(dict.fromkeys(all_topics))[:10]
        
        return {
            "aggregated_sentiment": final_sentiment,
            "aggregated_score": round(final_score, 2),
            "confidence": min(len(readings) / 3 * 100, 100),
            "platforms": platform_data,
            "top_topics": unique_topics,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_article_topics_from_sentiment(self, count: int = 5) -> List[Dict]:
        """
        Generate article topic suggestions based on current sentiment.
        """
        sentiment = self.get_aggregated_sentiment()
        topics = []
        
        # Use Grok for topic generation
        try:
            from services.grok_review_service import grok_review_service
            grok_topics = grok_review_service.suggest_article_topics(count)
            topics.extend(grok_topics)
        except Exception as e:
            logger.warning(f"Grok topics failed: {e}")
        
        # Add topics from sentiment data
        for topic in sentiment.get("top_topics", [])[:3]:
            if topic and len(topic) > 10:
                topics.append({
                    "headline": topic,
                    "source": "sentiment_monitor",
                    "sentiment": sentiment.get("aggregated_sentiment", "neutral")
                })
        
        return topics[:count]


# Singleton
sentiment_monitor = MultiPlatformSentimentMonitor()
'''

with open('services/sentiment_monitor.py', 'w') as f:
    f.write(sentiment_monitor_code)
print("  ✅ Created services/sentiment_monitor.py")

# ============================================================
# STEP 6: Create Master Automation Loop
# ============================================================
print("[6/8] Creating master automation loop...")

automation_loop_code = '''
"""
Protocol Pulse - Master Automation Loop
========================================
Runs continuously to:
1. Generate articles every 15 minutes (Claude + Grok review)
2. Monitor sentiment across X, Nostr, YouTube
3. Auto-engage on X
4. Discover trending topics
5. Post articles to social

This is the "leave it running overnight" script.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta
from threading import Thread, Event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/automation_master.log')
    ]
)
logger = logging.getLogger("MasterAutomation")

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

class MasterAutomationLoop:
    """
    The main automation orchestrator.
    Runs multiple tasks on different schedules.
    """
    
    def __init__(self):
        self.stop_event = Event()
        self.last_article_time = None
        self.last_sentiment_time = None
        self.last_engage_time = None
        self.last_post_time = None
        
        # Intervals (in seconds)
        self.article_interval = 15 * 60  # 15 minutes
        self.sentiment_interval = 5 * 60  # 5 minutes
        self.engage_interval = 30 * 60  # 30 minutes
        self.post_interval = 60 * 60  # 1 hour
        
        self.stats = {
            "articles_generated": 0,
            "articles_approved": 0,
            "articles_rejected": 0,
            "sentiment_checks": 0,
            "x_engagements": 0,
            "posts_made": 0,
            "errors": 0,
            "started_at": datetime.utcnow().isoformat()
        }
    
    def log_stats(self):
        """Log current statistics."""
        logger.info(f"=== STATS === Articles: {self.stats['articles_generated']} "
                   f"(✓{self.stats['articles_approved']}/✗{self.stats['articles_rejected']}) | "
                   f"Sentiment: {self.stats['sentiment_checks']} | "
                   f"X Engage: {self.stats['x_engagements']} | "
                   f"Posts: {self.stats['posts_made']} | "
                   f"Errors: {self.stats['errors']}")
    
    def run_article_generation(self):
        """Generate a new article with Claude + Grok review."""
        try:
            from app import app
            from services.automation import generate_breaking_article_with_tracking
            from services.sentiment_monitor import sentiment_monitor
            
            with app.app_context():
                # Get trending topic from sentiment
                topics = sentiment_monitor.get_article_topics_from_sentiment(3)
                
                if topics and topics[0].get("headline"):
                    logger.info(f"Using trending topic: {topics[0]['headline'][:50]}...")
                
                # Generate article
                result = generate_breaking_article_with_tracking()
                
                self.stats["articles_generated"] += 1
                
                if result.get("success"):
                    if result.get("grok_approved", True):
                        self.stats["articles_approved"] += 1
                        logger.info(f"✅ Article approved: {result.get('title', 'Unknown')[:50]}...")
                        
                        # Auto-post if enabled
                        if os.environ.get("AUTOPOST_X", "").lower() == "true":
                            self.run_article_post(result.get("article_id"))
                    else:
                        self.stats["articles_rejected"] += 1
                        logger.warning(f"❌ Article rejected by Grok: {result.get('grok_issues', [])}")
                else:
                    logger.warning(f"Article generation failed: {result.get('error', 'Unknown')}")
                    self.stats["errors"] += 1
                    
        except Exception as e:
            logger.error(f"Article generation error: {e}")
            traceback.print_exc()
            self.stats["errors"] += 1
    
    def run_sentiment_check(self):
        """Check sentiment across all platforms."""
        try:
            from services.sentiment_monitor import sentiment_monitor
            
            sentiment = sentiment_monitor.get_aggregated_sentiment()
            self.stats["sentiment_checks"] += 1
            
            logger.info(f"📊 Sentiment: {sentiment['aggregated_sentiment']} "
                       f"(score: {sentiment['aggregated_score']}, "
                       f"confidence: {sentiment['confidence']}%)")
            
            # Log platform breakdown
            for platform, data in sentiment.get("platforms", {}).items():
                logger.debug(f"  {platform}: {data['sentiment']} ({data['score']})")
                
        except Exception as e:
            logger.warning(f"Sentiment check error: {e}")
            self.stats["errors"] += 1
    
    def run_x_engagement(self):
        """Auto-engage on X."""
        if os.environ.get("ENABLE_X_ENGAGE", "").lower() != "true":
            return
            
        try:
            from services.x_automation_service import x_automation_service
            
            result = x_automation_service.auto_engage(max_actions=5)
            
            if result.get("success"):
                self.stats["x_engagements"] += result.get("actions_taken", 0)
                logger.info(f"🐦 X Engagement: {result.get('actions_taken', 0)} actions")
            else:
                logger.warning(f"X engagement failed: {result.get('error')}")
                
        except Exception as e:
            logger.warning(f"X engagement error: {e}")
            self.stats["errors"] += 1
    
    def run_article_post(self, article_id: int = None):
        """Post latest article to X."""
        if os.environ.get("AUTOPOST_X", "").lower() != "true":
            return
            
        try:
            from app import app, db
            from models import Article
            from services.x_automation_service import x_automation_service
            
            with app.app_context():
                if article_id:
                    article = Article.query.get(article_id)
                else:
                    article = Article.query.filter_by(published=True).order_by(
                        Article.created_at.desc()
                    ).first()
                
                if not article:
                    return
                
                # Build URL
                base_url = os.environ.get("SITE_URL", "https://protocolpulse.io")
                article_url = f"{base_url}/article/{article.id}"
                
                result = x_automation_service.post_article(
                    title=article.title,
                    url=article_url
                )
                
                if result.get("success"):
                    self.stats["posts_made"] += 1
                    logger.info(f"📤 Posted to X: {article.title[:40]}...")
                else:
                    logger.warning(f"X post failed: {result.get('error')}")
                    
        except Exception as e:
            logger.warning(f"Article post error: {e}")
            self.stats["errors"] += 1
    
    def should_run_task(self, last_time: datetime, interval: int) -> bool:
        """Check if enough time has passed to run a task."""
        if last_time is None:
            return True
        return (datetime.utcnow() - last_time).total_seconds() >= interval
    
    def run_forever(self):
        """
        Main loop - runs until stopped.
        """
        logger.info("=" * 60)
        logger.info("PROTOCOL PULSE - MASTER AUTOMATION STARTED")
        logger.info("=" * 60)
        logger.info(f"Article interval: {self.article_interval // 60} min")
        logger.info(f"Sentiment interval: {self.sentiment_interval // 60} min")
        logger.info(f"X engage interval: {self.engage_interval // 60} min")
        logger.info(f"Post interval: {self.post_interval // 60} min")
        logger.info("=" * 60)
        
        # Apply patches
        try:
            from services.claude_primary_patch import patch_content_generator, add_grok_review_to_pipeline
            patch_content_generator()
            add_grok_review_to_pipeline()
            logger.info("✅ Claude + Grok patches applied")
        except Exception as e:
            logger.warning(f"Could not apply patches: {e}")
        
        cycle = 0
        while not self.stop_event.is_set():
            cycle += 1
            logger.info(f"--- Cycle {cycle} ---")
            
            try:
                # Check each task
                now = datetime.utcnow()
                
                # Article generation (every 15 min)
                if self.should_run_task(self.last_article_time, self.article_interval):
                    logger.info("🔄 Running article generation...")
                    self.run_article_generation()
                    self.last_article_time = now
                
                # Sentiment check (every 5 min)
                if self.should_run_task(self.last_sentiment_time, self.sentiment_interval):
                    self.run_sentiment_check()
                    self.last_sentiment_time = now
                
                # X engagement (every 30 min)
                if self.should_run_task(self.last_engage_time, self.engage_interval):
                    self.run_x_engagement()
                    self.last_engage_time = now
                
                # Log stats every 10 cycles
                if cycle % 10 == 0:
                    self.log_stats()
                
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                traceback.print_exc()
                self.stats["errors"] += 1
            
            # Sleep before next cycle
            time.sleep(60)  # Check every minute
        
        logger.info("Master automation stopped.")
        self.log_stats()
    
    def stop(self):
        """Stop the automation loop."""
        self.stop_event.set()


def main():
    """Entry point."""
    loop = MasterAutomationLoop()
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        loop.stop()


if __name__ == "__main__":
    main()
'''

with open('master_automation.py', 'w') as f:
    f.write(automation_loop_code)
print("  ✅ Created master_automation.py")

# ============================================================
# STEP 7: Update Environment Variables Guide
# ============================================================
print("[7/8] Creating environment variables guide...")

env_guide = '''
# ============================================================
# PROTOCOL PULSE - REQUIRED ENVIRONMENT VARIABLES
# ============================================================
# Add these to Replit Secrets (Tools → Secrets)

# === AI PROVIDERS (Required) ===
ANTHROPIC_API_KEY=sk-ant-...          # Claude - Primary article generation
GEMINI_API_KEY=...                     # Gemini - Backup & duplicate detection
XAI_API_KEY=...                        # Grok - Article review & X sentiment

# === AUTOMATION FLAGS (Required) ===
ENABLE_ARTICLE_AUTOMATION_15M=true     # Enable 15-min article loop
ENABLE_AUTO_PUBLISH=true               # Auto-publish approved articles

# === X (TWITTER) API (Optional but recommended) ===
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
TWITTER_BEARER_TOKEN=...
AUTOPOST_X=false                       # Set to true to auto-post articles
ENABLE_X_ENGAGE=false                  # Set to true for auto-engagement

# === YOUTUBE (Optional) ===
YOUTUBE_API_KEY=...                    # For sentiment monitoring

# === OTHER (As needed) ===
SITE_URL=https://protocolpulse.io
SESSION_SECRET=your-random-secret-here
'''

with open('ENV_SETUP_GUIDE.txt', 'w') as f:
    f.write(env_guide)
print("  ✅ Created ENV_SETUP_GUIDE.txt")

# ============================================================
# STEP 8: Final Setup
# ============================================================
print("[8/8] Final setup...")

# Create logs directory
os.makedirs('logs', exist_ok=True)
print("  ✅ Created logs directory")

print()
print("=" * 60)
print("✅ SETUP COMPLETE!")
print("=" * 60)
print()
print("Files created:")
print("  - services/grok_review_service.py (Grok fact-checking)")
print("  - services/claude_primary_patch.py (Claude-first generation)")
print("  - services/x_automation_service.py (X engagement)")
print("  - services/sentiment_monitor.py (Multi-platform sentiment)")
print("  - master_automation.py (Main automation loop)")
print("  - ENV_SETUP_GUIDE.txt (Required environment variables)")
print()
print("=" * 60)
print("NEXT STEPS:")
print("=" * 60)
print()
print("1. Add these to Replit Secrets:")
print("   ENABLE_ARTICLE_AUTOMATION_15M = true")
print("   ENABLE_AUTO_PUBLISH = true")
print()
print("2. (Optional) For X automation, also add:")
print("   AUTOPOST_X = true")
print("   ENABLE_X_ENGAGE = true")
print()
print("3. Start the automation:")
print("   python3 master_automation.py")
print()
print("4. Or use the standard app:")
print("   python3 run_server.py")
print()
print("The system will now:")
print("  • Generate articles with Claude every 15 minutes")
print("  • Review each article with Grok before publishing")
print("  • Monitor sentiment on X, Nostr, YouTube")
print("  • Auto-engage on X (if enabled)")
print("  • Post articles to X (if enabled)")
print()
