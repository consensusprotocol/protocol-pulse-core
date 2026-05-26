
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
            from pp_services.x_automation_service import x_automation_service
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
            from pp_services.grok_review_service import grok_review_service
            
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
            from pp_services.grok_review_service import grok_review_service
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
