"""
PERFORMANCE TRACKER — Learn what works, do more of it.
=======================================================
Fetches engagement data on our recent tweets,
scores each strategy, and adjusts weights for future cycles.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List

logger = logging.getLogger("performance_tracker")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WEIGHTS_FILE = "data/strategy_weights.json"
PERFORMANCE_FILE = "data/performance_log.json"

DEFAULT_WEIGHTS = {
    "viral": 1.0,
    "intel_journalist": 1.0,
    "quote_tweet": 1.0,
    "comment_radar": 1.0,
    "thread": 1.0,
    "bookmark_bait": 1.0,
}


class PerformanceTracker:

    def __init__(self):
        from services.comment_radar import CommentRadar
        self.radar = CommentRadar()
        self.x_client = self.radar.x_client
        os.makedirs("data", exist_ok=True)
        logger.info("PerformanceTracker initialized")

    def get_weights(self) -> Dict:
        """Get current strategy weights."""
        try:
            if os.path.exists(WEIGHTS_FILE):
                return json.load(open(WEIGHTS_FILE))
        except:
            pass
        return DEFAULT_WEIGHTS.copy()

    def _fetch_our_tweet_performance(self) -> List[Dict]:
        """Fetch engagement metrics for our recent tweets."""
        try:
            data = self.x_client.get_user_tweets("ProtocolPulse", max_results=20)
            if not data or "data" not in data:
                return []

            tweets = []
            for t in data["data"]:
                m = t.get("public_metrics", {})
                tweets.append({
                    "id": t["id"],
                    "text": t.get("text", "")[:100],
                    "likes": m.get("like_count", 0),
                    "retweets": m.get("retweet_count", 0),
                    "replies": m.get("reply_count", 0),
                    "bookmarks": m.get("bookmark_count", 0),
                    "impressions": m.get("impression_count", 0),
                    "score": (m.get("like_count", 0) * 1.0 
                             + m.get("retweet_count", 0) * 2.0 
                             + m.get("reply_count", 0) * 3.0 
                             + m.get("bookmark_count", 0) * 4.0),
                    "created_at": t.get("created_at", ""),
                })

            return tweets

        except Exception as e:
            logger.error(f"Failed to fetch performance: {e}")
            return []

    def _match_strategy(self, tweet_text: str) -> str:
        """Match a tweet to its source strategy using the engagement log."""
        log_file = "data/engagement_log.json"
        try:
            if os.path.exists(log_file):
                log = json.load(open(log_file))
                for entry in log.get("posts", []):
                    if entry.get("text", "")[:50] == tweet_text[:50]:
                        return entry.get("strategy", "unknown")
        except:
            pass
        
        # Heuristic fallback
        text_lower = tweet_text.lower()
        if "word from" in text_lower or "sources" in text_lower or "hearing" in text_lower:
            return "intel_journalist"
        if "thread" in text_lower or "🧵" in text_lower:
            return "thread"
        return "viral"

    def update_weights(self) -> Dict:
        """Analyze performance and update strategy weights."""
        tweets = self._fetch_our_tweet_performance()
        if not tweets:
            return {"success": False, "reason": "no_data"}

        # Group by strategy
        strategy_scores = {}
        for t in tweets:
            strat = self._match_strategy(t["text"])
            if strat not in strategy_scores:
                strategy_scores[strat] = []
            strategy_scores[strat].append(t["score"])

        # Calculate average score per strategy
        avg_scores = {}
        for strat, scores in strategy_scores.items():
            avg_scores[strat] = sum(scores) / len(scores) if scores else 0

        # Normalize to weights (best strategy gets 1.5, worst gets 0.6)
        if avg_scores:
            max_score = max(avg_scores.values()) or 1
            weights = self.get_weights()
            for strat, avg in avg_scores.items():
                # Blend with existing weight (70% new data, 30% previous)
                new_weight = 0.6 + (avg / max_score) * 0.9
                if strat in weights:
                    weights[strat] = round(weights[strat] * 0.3 + new_weight * 0.7, 2)
                else:
                    weights[strat] = round(new_weight, 2)

            json.dump(weights, open(WEIGHTS_FILE, "w"), indent=2)
            logger.info(f"Updated weights: {weights}")

        # Log performance
        perf = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tweets_analyzed": len(tweets),
            "strategy_averages": {k: round(v, 1) for k, v in avg_scores.items()},
            "top_tweet": max(tweets, key=lambda x: x["score"])["text"][:80] if tweets else "",
            "top_score": max(t["score"] for t in tweets) if tweets else 0,
        }

        try:
            log = json.load(open(PERFORMANCE_FILE)) if os.path.exists(PERFORMANCE_FILE) else {"entries": []}
        except:
            log = {"entries": []}
        log["entries"].append(perf)
        log["entries"] = log["entries"][-100:]
        json.dump(log, open(PERFORMANCE_FILE, "w"), indent=2)

        return {"success": True, "weights": self.get_weights(), "performance": perf}


def update_performance_weights():
    """Scheduler entry point."""
    try:
        tracker = PerformanceTracker()
        return tracker.update_weights()
    except Exception as e:
        logger.error(f"Performance tracking failed: {e}")
        return {"success": False, "error": str(e)}
