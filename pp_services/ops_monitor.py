"""
OPS MONITOR — System health dashboard for all scheduled jobs.
==============================================================
Single API endpoint returns status of every component.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict

logger = logging.getLogger("ops_monitor")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class OpsMonitor:

    def get_full_status(self) -> Dict:
        """Return status of every system component."""
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_keys": self._check_api_keys(),
            "x_clients": self._check_x_clients(),
            "scheduled_jobs": self._check_jobs(),
            "recent_articles": self._check_articles(),
            "tweet_activity": self._check_tweet_activity(),
            "newsletter": self._check_newsletter(),
            "disk": self._check_disk(),
        }

        # Overall health
        issues = []
        if not status["api_keys"].get("all_set"):
            issues.append("Missing API keys")
        if not status["x_clients"].get("v2"):
            issues.append("X client not initialized")
        if status["recent_articles"].get("hours_since_last", 99) > 1:
            issues.append("No articles in last hour")
        
        status["health"] = "healthy" if not issues else "degraded"
        status["issues"] = issues
        
        return status

    def _check_api_keys(self) -> Dict:
        keys = {
            "TWITTER_BEARER_TOKEN": bool(os.environ.get("TWITTER_BEARER_TOKEN")),
            "TWITTER_API_KEY": bool(os.environ.get("TWITTER_API_KEY")),
            "XAI_API_KEY": bool(os.environ.get("XAI_API_KEY")),
            "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
            "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "RESEND_API_KEY": bool(os.environ.get("RESEND_API_KEY")),
            "ENABLE_TWEETS": os.environ.get("ENABLE_TWEETS", "false"),
            "NOSTR_PRIVATE_KEY": bool(os.environ.get("NOSTR_PRIVATE_KEY")),
        }
        keys["all_set"] = all(v for k, v in keys.items() if k != "ENABLE_TWEETS")
        return keys

    def _check_x_clients(self) -> Dict:
        try:
            from pp_services.x_service import XService
            x = XService()
            return {"v1": x.client is not None, "v2": x.client_v2 is not None}
        except Exception as e:
            return {"v1": False, "v2": False, "error": str(e)}

    def _check_jobs(self) -> Dict:
        """Check data files for last-run evidence."""
        jobs = {}
        
        # Check engagement log
        log_files = {
            "engagement_log": "data/engagement_log.json",
            "reply_back_log": "data/reply_back_log.json",
            "thread_log": "data/thread_log.json",
            "performance_log": "data/performance_log.json",
            "strategy_weights": "data/strategy_weights.json",
            "newsletter_sent": "data/newsletter_sent.json",
        }
        
        for name, path in log_files.items():
            if os.path.exists(path):
                try:
                    data = json.load(open(path))
                    # Find most recent timestamp
                    latest = None
                    for key in ["posts", "history", "threads", "entries"]:
                        items = data.get(key, [])
                        if items and isinstance(items, list):
                            last = items[-1]
                            ts = last.get("timestamp", "")
                            if ts:
                                latest = ts
                    
                    jobs[name] = {"exists": True, "last_activity": latest}
                except:
                    jobs[name] = {"exists": True, "last_activity": None}
            else:
                jobs[name] = {"exists": False}

        return jobs

    def _check_articles(self) -> Dict:
        try:
            from app import app, db
            import models
            
            with app.app_context():
                latest = models.Article.query.order_by(models.Article.id.desc()).first()
                if not latest:
                    return {"total": 0}
                
                total = models.Article.query.count()
                published = models.Article.query.filter_by(published=True).count()
                
                age = (datetime.utcnow() - latest.created_at).total_seconds() / 3600 if latest.created_at else 99
                
                # Category breakdown (last 24h)
                cutoff = datetime.utcnow() - timedelta(hours=24)
                recent = models.Article.query.filter(models.Article.created_at >= cutoff).all()
                categories = {}
                for a in recent:
                    cat = a.category or "uncategorized"
                    categories[cat] = categories.get(cat, 0) + 1
                
                return {
                    "total": total,
                    "published": published,
                    "latest_id": latest.id,
                    "latest_title": latest.title[:60],
                    "hours_since_last": round(age, 1),
                    "last_24h": len(recent),
                    "categories_24h": categories,
                }
        except Exception as e:
            return {"error": str(e)}

    def _check_tweet_activity(self) -> Dict:
        log_file = "data/engagement_log.json"
        if not os.path.exists(log_file):
            return {"total_logged": 0}
        
        try:
            data = json.load(open(log_file))
            posts = data.get("posts", [])
            
            # Count by strategy
            strategies = {}
            for p in posts:
                s = p.get("strategy", "unknown")
                strategies[s] = strategies.get(s, 0) + 1
            
            return {
                "total_logged": len(posts),
                "by_strategy": strategies,
                "latest": posts[-1].get("timestamp", "") if posts else None,
                "latest_text": posts[-1].get("text", "")[:80] if posts else None,
            }
        except:
            return {"total_logged": 0}

    def _check_newsletter(self) -> Dict:
        try:
            from app import app, db
            from models import User
            with app.app_context():
                subs = User.query.filter_by(newsletter_subscribed=True).count()
                return {
                    "subscribers": subs,
                    "resend_configured": bool(os.environ.get("RESEND_API_KEY")),
                }
        except Exception as e:
            return {"error": str(e)}

    def _check_disk(self) -> Dict:
        img_dir = "static/images/headers"
        if os.path.exists(img_dir):
            files = os.listdir(img_dir)
            total_size = sum(os.path.getsize(os.path.join(img_dir, f)) for f in files if os.path.isfile(os.path.join(img_dir, f)))
            return {
                "header_images": len(files),
                "total_size_mb": round(total_size / 1024 / 1024, 1),
            }
        return {"header_images": 0}


def get_ops_status():
    return OpsMonitor().get_full_status()
