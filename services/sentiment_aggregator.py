
"""
Multi-Platform Sentiment Aggregator
===================================
Combines sentiment from:
- X (Twitter) via Grok
- YouTube comments/engagement
- Reddit r/bitcoin
- Nostr via Grok

Produces unified sentiment score for article topics.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class PlatformSentiment:
    platform: str
    sentiment: str  # bullish, bearish, neutral
    score: float  # -100 to 100
    volume: int
    topics: List[str]
    confidence: float  # 0-1


class SentimentAggregator:
    """
    Aggregates sentiment across platforms.
    """
    
    def __init__(self):
        self.grok_available = bool(os.environ.get("XAI_API_KEY"))
        self.youtube_available = bool(os.environ.get("YOUTUBE_API_KEY"))
        self.reddit_available = bool(os.environ.get("REDDIT_CLIENT_ID"))
    
    def get_x_sentiment(self) -> Optional[PlatformSentiment]:
        """X/Twitter sentiment via Grok."""
        try:
            from services.grok_review_service import grok_review_service
            data = grok_review_service.get_x_sentiment("Bitcoin")
            
            return PlatformSentiment(
                platform="x",
                sentiment=data.get("sentiment", "neutral"),
                score=data.get("score", 0),
                volume=0,
                topics=data.get("trending_topics", []),
                confidence=0.8 if self.grok_available else 0.3
            )
        except Exception as e:
            logger.warning(f"X sentiment error: {e}")
            return None
    
    def get_youtube_sentiment(self) -> Optional[PlatformSentiment]:
        """YouTube Bitcoin content sentiment."""
        if not self.youtube_available:
            return None
        
        try:
            from googleapiclient.discovery import build
            
            youtube = build("youtube", "v3", developerKey=os.environ.get("YOUTUBE_API_KEY"))
            
            # Get recent Bitcoin videos
            search = youtube.search().list(
                q="Bitcoin",
                part="id,snippet",
                maxResults=20,
                order="date",
                type="video",
                publishedAfter=(datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
            ).execute()
            
            video_ids = [item["id"]["videoId"] for item in search.get("items", [])]
            
            if not video_ids:
                return None
            
            # Get engagement metrics
            videos = youtube.videos().list(
                part="statistics",
                id=",".join(video_ids)
            ).execute()
            
            total_views = 0
            total_likes = 0
            
            for video in videos.get("items", []):
                stats = video.get("statistics", {})
                total_views += int(stats.get("viewCount", 0))
                total_likes += int(stats.get("likeCount", 0))
            
            # Simple engagement-based sentiment
            engagement = total_likes / max(total_views, 1)
            
            if engagement > 0.05:
                sentiment = "bullish"
                score = min(engagement * 1000, 80)
            elif engagement < 0.01:
                sentiment = "bearish"
                score = -40
            else:
                sentiment = "neutral"
                score = 0
            
            return PlatformSentiment(
                platform="youtube",
                sentiment=sentiment,
                score=score,
                volume=len(video_ids),
                topics=[],
                confidence=0.6
            )
            
        except Exception as e:
            logger.warning(f"YouTube sentiment error: {e}")
            return None
    
    def get_reddit_sentiment(self) -> Optional[PlatformSentiment]:
        """Reddit r/bitcoin sentiment."""
        if not self.reddit_available:
            return None
        
        try:
            import praw
            
            reddit = praw.Reddit(
                client_id=os.environ.get("REDDIT_CLIENT_ID"),
                client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
                user_agent=os.environ.get("REDDIT_USER_AGENT", "ProtocolPulse/1.0")
            )
            
            subreddit = reddit.subreddit("bitcoin")
            
            # Get hot posts
            posts = list(subreddit.hot(limit=25))
            
            total_score = sum(p.score for p in posts)
            total_comments = sum(p.num_comments for p in posts)
            
            # Engagement-based sentiment
            avg_score = total_score / len(posts) if posts else 0
            
            if avg_score > 500:
                sentiment = "bullish"
                score = min(avg_score / 10, 70)
            elif avg_score < 100:
                sentiment = "bearish"
                score = -30
            else:
                sentiment = "neutral"
                score = 0
            
            topics = [p.title[:50] for p in posts[:5]]
            
            return PlatformSentiment(
                platform="reddit",
                sentiment=sentiment,
                score=score,
                volume=len(posts),
                topics=topics,
                confidence=0.5
            )
            
        except Exception as e:
            logger.warning(f"Reddit sentiment error: {e}")
            return None
    
    def get_nostr_sentiment(self) -> Optional[PlatformSentiment]:
        """Nostr sentiment via Grok's knowledge."""
        try:
            from services.grok_review_service import grok_review_service
            data = grok_review_service.get_x_sentiment("Bitcoin Nostr")
            
            return PlatformSentiment(
                platform="nostr",
                sentiment=data.get("sentiment", "neutral"),
                score=data.get("score", 0) * 0.8,  # Slightly less confident
                volume=0,
                topics=data.get("trending_topics", []),
                confidence=0.5
            )
        except Exception as e:
            logger.warning(f"Nostr sentiment error: {e}")
            return None
    
    def get_aggregated_sentiment(self) -> Dict:
        """
        Get weighted aggregate sentiment across all platforms.
        """
        readings = []
        
        # Gather all
        x = self.get_x_sentiment()
        if x:
            readings.append(x)
        
        yt = self.get_youtube_sentiment()
        if yt:
            readings.append(yt)
        
        reddit = self.get_reddit_sentiment()
        if reddit:
            readings.append(reddit)
        
        nostr = self.get_nostr_sentiment()
        if nostr:
            readings.append(nostr)
        
        if not readings:
            return {
                "sentiment": "neutral",
                "score": 0,
                "confidence": 0,
                "platforms": {},
                "topics": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Weighted by confidence
        total_weight = sum(r.confidence for r in readings)
        weighted_score = sum(r.score * r.confidence for r in readings) / total_weight if total_weight else 0
        
        # Aggregate sentiment
        if weighted_score > 20:
            sentiment = "bullish"
        elif weighted_score < -20:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        
        # Collect all topics
        all_topics = []
        for r in readings:
            all_topics.extend(r.topics)
        unique_topics = list(dict.fromkeys(all_topics))[:10]
        
        return {
            "sentiment": sentiment,
            "score": round(weighted_score, 2),
            "confidence": round(total_weight / len(readings), 2),
            "platforms": {r.platform: asdict(r) for r in readings},
            "topics": unique_topics,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_article_topics(self, count: int = 5) -> List[Dict]:
        """
        Get trending topics suitable for articles.
        """
        # Get Grok suggestions
        try:
            from services.grok_review_service import grok_review_service
            return grok_review_service.suggest_trending_topics(count)
        except Exception as e:
            logger.warning(f"Topic suggestion error: {e}")
            return []


# Singleton
sentiment_aggregator = SentimentAggregator()
