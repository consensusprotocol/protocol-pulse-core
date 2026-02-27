
#!/usr/bin/env python3
"""
PROTOCOL PULSE - MASTER AUTOMATION
===================================
The "leave it running overnight" script.

Runs continuously:
- Article generation every 15 minutes (Claude + Grok review)
- Sentiment monitoring every 5 minutes
- X engagement every 30 minutes (if enabled)
- Article posting to X every hour (if enabled)

Usage:
    python3 master_automation.py

Environment variables:
    ENABLE_ARTICLE_AUTOMATION_15M=true  (required)
    ENABLE_AUTO_PUBLISH=true            (required)
    AUTOPOST_X=true                     (optional)
    ENABLE_X_ENGAGE=true                (optional)
"""

import os
import json
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta
from threading import Event
from services.radar_automation import run_radar_cycle_safe

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/master_automation.log")
    ]
)
logger = logging.getLogger("MasterAutomation")

# Ensure directories
os.makedirs("logs", exist_ok=True)

class MasterAutomation:
    """
    Main automation orchestrator.
    """
    
    def __init__(self):
        self.stop_event = Event()
        
        # Intervals (seconds)
        self.article_interval = 15 * 60  # 15 min
        self.sentiment_interval = 5 * 60  # 5 min
        self.engage_interval = 30 * 60   # 30 min
        self.post_interval = 6 * 60 * 60  # 6 hours
        self.pulse_interval = 6 * 60 * 60  # 6 hours - Partner channel intelligence
        
        # Last run times
        self.last_article = None
        self.last_sentiment = None
        self.last_engage = None
        self.last_post = None
        self.last_pulse = None
        
        # Stats
        self.stats = {
            "articles_generated": 0,
            "articles_published": 0,
            "sentiment_checks": 0,
            "x_posts": 0,
            "x_engagements": 0,
            "pulse_runs": 0,
            "errors": 0,
            "started_at": datetime.utcnow().isoformat()
        }
    
    def should_run(self, last_time: datetime, interval: int) -> bool:
        """Check if task should run."""
        if last_time is None:
            return True
        return (datetime.utcnow() - last_time).total_seconds() >= interval
    
    def run_article_generation(self):
        """Generate a new article."""
        try:
            from services.article_automation import run_article_generation_cycle
            
            result = run_article_generation_cycle()
            
            self.stats["articles_generated"] += 1
            if result.get("published"):
                self.stats["articles_published"] += 1
                
                # Post to X if enabled
                if os.environ.get("AUTOPOST_X", "").lower() == "true":
                    self.post_to_x(result.get("article_id"))
            
            return result
            
        except Exception as e:
            logger.error(f"Article generation error: {e}")
            self.stats["errors"] += 1
            return {"success": False, "error": str(e)}
    
    def run_sentiment_check(self):
        """Check multi-platform sentiment."""
        try:
            from services.sentiment_aggregator import sentiment_aggregator
            
            sentiment = sentiment_aggregator.get_aggregated_sentiment()
            self.stats["sentiment_checks"] += 1
            
            logger.info(f"Sentiment: {sentiment['sentiment']} (score: {sentiment['score']})")
            return sentiment
            
        except Exception as e:
            logger.warning(f"Sentiment check error: {e}")
            self.stats["errors"] += 1
            return None
    
    def run_x_engagement(self):
        """Auto-engage on X."""
        if os.environ.get("ENABLE_X_ENGAGE", "").lower() != "true":
            return None
        
        try:
            from services.x_automation_service import x_automation_service
            
            result = x_automation_service.auto_engage(max_actions=5)
            self.stats["x_engagements"] += result.get("actions", 0)
            
            logger.info(f"X engagement: {result.get('actions', 0)} actions")
            return result
            
        except Exception as e:
            logger.warning(f"X engagement error: {e}")
            self.stats["errors"] += 1
            return None
    

    def run_pulse_intelligence(self):
        """Run partner channel intelligence pulse"""
        try:
            from services.pulse_intelligence import pulse_intelligence
            
            logger.info("Running Pulse Intelligence...")
            result = pulse_intelligence.run_daily_pulse()
            
            self.stats["pulse_runs"] += 1
            
            if result.get("status") == "success":
                logger.info(f"Pulse complete: {result.get('videos_processed', 0)} videos processed")
                
                # Post top X hook if we have one
                x_posts = result.get("x_posts", [])
                if x_posts and os.environ.get("AUTOPOST_X", "").lower() == "true":
                    try:
                        from services.x_service import XService
                        
                        from datetime import datetime
                        
                        POSTED_FILE = "data/posted_urls.json"
                        DAILY_LIMIT = 2  # Max pulse posts per day
                        
                        # Load posted data
                        os.makedirs("data", exist_ok=True)
                        if os.path.exists(POSTED_FILE):
                            with open(POSTED_FILE, 'r') as f:
                                posted_data = json.load(f)
                        else:
                            posted_data = {"urls": [], "daily_posts": {}, "last_cleanup": None}
                        
                        # Ensure daily_posts exists
                        if "daily_posts" not in posted_data:
                            posted_data["daily_posts"] = {}
                        
                        today = datetime.utcnow().strftime("%Y-%m-%d")
                        today_count = posted_data["daily_posts"].get(today, 0)
                        
                        # Check daily limit
                        if today_count >= DAILY_LIMIT:
                            logger.info(f"Daily X post limit reached ({today_count}/{DAILY_LIMIT}). Skipping.")
                        else:
                            x_service = XService()
                            posted = False
                            
                            for post in x_posts:
                                video = post.get("video", {})
                                video_url = video.get("url", "")
                                video_id = video_url.split("v=")[-1].split("&")[0] if "v=" in video_url else video_url
                                
                                # Check ALL variations of the URL
                                url_variants = [
                                    video_url,
                                    video_url.replace("https://www.", "https://"),
                                    video_url.replace("https://", "https://www."),
                                    f"https://www.youtube.com/watch?v={video_id}",
                                    f"https://youtube.com/watch?v={video_id}",
                                    video_id
                                ]
                                
                                is_duplicate = any(u in posted_data["urls"] for u in url_variants if u)
                                
                                if is_duplicate:
                                    logger.info(f"DUPLICATE BLOCKED: {video_id}")
                                    continue
                                
                                # Post it
                                hook = post["hook"].replace("[LINK]", video_url)
                                # Use quality gate for pulse posts
                                from services.human_voice_filter import humanize
                                from services.post_quality_gate import post_quality_gate
                                
                                clean_hook = humanize(hook)
                                
                                # Verify link
                                link_check = post_quality_gate.verify_link(video_url)
                                if not link_check["valid"]:
                                    logger.warning(f"Skipping post - link invalid: {video_url}")
                                    continue
                                
                                x_service.post_tweet(clean_hook)
                                
                                # Save ALL variants to prevent future duplicates
                                for u in url_variants:
                                    if u and u not in posted_data["urls"]:
                                        posted_data["urls"].append(u)
                                
                                # Update daily count
                                posted_data["daily_posts"][today] = today_count + 1
                                
                                # Keep only last 1000 URLs
                                if len(posted_data["urls"]) > 1000:
                                    posted_data["urls"] = posted_data["urls"][-1000:]
                                
                                with open(POSTED_FILE, 'w') as f:
                                    json.dump(posted_data, f, indent=2)
                                
                                logger.info(f"Posted pulse hook to X: {hook[:50]}...")
                                posted = True
                                break
                            
                            if not posted:
                                logger.info("No new unique content to post")
                    except Exception as e:
                        logger.error(f"Failed to post pulse to X: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Pulse intelligence error: {e}")
            self.stats["errors"] += 1
            return None



    def post_to_x(self, article_id: int = None):
        """Post article to X."""
        if os.environ.get("AUTOPOST_X", "").lower() != "true":
            return None
        
        try:
            from app import app
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
                    return None
                
                base_url = os.environ.get("SITE_URL", "https://protocolpulse.io")
                url = f"{base_url}/articles/{article.id}"  # Note: /articles/ not /article/
                
                # Use quality gate for all posts
                from services.post_quality_gate import post_quality_gate
                
                gate_result = post_quality_gate.process_article_post(
                    article_id=article.id,
                    article_title=article.title,
                    article_summary=article.summary or ""
                )
                
                if not gate_result["approved"]:
                    logger.warning(f"Post rejected by quality gate: {gate_result.get('rejection_reason')}")
                    return {"rejected": True, "reason": gate_result.get("rejection_reason")}
                
                # Post the quality-approved tweet
                result = x_automation_service.post_tweet(gate_result["tweet_text"])
                
                if result.get("success"):
                    self.stats["x_posts"] += 1
                    logger.info(f"Posted to X: {article.title[:40]}...")
                
                return result
                
        except Exception as e:
            logger.warning(f"X post error: {e}")
            self.stats["errors"] += 1
            return None
    
    def log_stats(self):
        """Log current statistics."""
        logger.info(
            f"STATS | Articles: {self.stats['articles_generated']} "
            f"(published: {self.stats['articles_published']}) | "
            f"Sentiment: {self.stats['sentiment_checks']} | "
            f"X: {self.stats['x_posts']} posts, {self.stats['x_engagements']} engagements | "
            f"Errors: {self.stats['errors']}"
        )
    
    def run(self):
        """
        Main loop.
        """
        logger.info("=" * 60)
        logger.info("PROTOCOL PULSE - MASTER AUTOMATION STARTED")
        logger.info("=" * 60)
        
        # Check required env vars
        if os.environ.get("ENABLE_ARTICLE_AUTOMATION_15M", "").lower() != "true":
            logger.warning("ENABLE_ARTICLE_AUTOMATION_15M not set - articles won't generate")
        
        if os.environ.get("ENABLE_AUTO_PUBLISH", "").lower() != "true":
            logger.warning("ENABLE_AUTO_PUBLISH not set - articles will be drafts only")
        
        logger.info(f"Article interval: {self.article_interval // 60} min")
        logger.info(f"Sentiment interval: {self.sentiment_interval // 60} min")
        logger.info(f"X engage enabled: {os.environ.get('ENABLE_X_ENGAGE', 'false')}")
        logger.info(f"X autopost enabled: {os.environ.get('AUTOPOST_X', 'false')}")
        logger.info("=" * 60)
        
        cycle = 0
        while not self.stop_event.is_set():
            cycle += 1
            now = datetime.utcnow()
            
            try:
                # Article generation
                if self.should_run(self.last_article, self.article_interval):
                    if os.environ.get("ENABLE_ARTICLE_AUTOMATION_15M", "").lower() == "true":
                        logger.info(f"[Cycle {cycle}] Running article generation...")
                        self.run_article_generation()
                        self.last_article = now
                
                # Sentiment check
                if self.should_run(self.last_sentiment, self.sentiment_interval):
                    self.run_sentiment_check()
                    self.last_sentiment = now
                
                # X engagement
                if self.should_run(self.last_engage, self.engage_interval):
                    self.run_x_engagement()
                    self.last_engage = now
                
                # Pulse Intelligence (every 6 hours)
                if self.should_run(self.last_pulse, self.pulse_interval):
                    logger.info(f"[Cycle {cycle}] Running Pulse Intelligence...")
                    self.run_pulse_intelligence()
                    self.last_pulse = now
                
                # Log stats every 10 cycles
                if cycle % 10 == 0:
                    self.log_stats()
                    
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                traceback.print_exc()
                self.stats["errors"] += 1
            
            # Sleep 1 minute between checks
            # --- Comment Radar (every 3 hours, self-timed) ---
            try:
                run_radar_cycle_safe()
            except Exception as e:
                logger.error(f'Radar cycle error: {e}')

            time.sleep(60)
        
        logger.info("Master automation stopped")
        self.log_stats()
    
    def stop(self):
        """Stop the automation."""
        self.stop_event.set()


def main():
    automation = MasterAutomation()
    
    try:
        automation.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        automation.stop()


if __name__ == "__main__":
    main()

    def run_newsletter(self):
        """Send daily newsletter at 9am ET (14:00 UTC)"""
        current_hour = datetime.utcnow().hour
        
        # Only run at 14:00 UTC (9am ET)
        if current_hour != 14:
            return None
        
        try:
            from services.newsletter_engine import newsletter_engine
            
            result = newsletter_engine.run_daily_newsletter()
            
            if result.get("success"):
                logger.info(f"Newsletter sent to {result.get('sent', 0)} subscribers")
                self.stats["newsletters_sent"] = self.stats.get("newsletters_sent", 0) + 1
            
            return result
            
        except Exception as e:
            logger.error(f"Newsletter error: {e}")
            return None
