"""
PREMIUM TIER SYSTEM
===================
Manages free vs premium content delivery.

TIERS:
- FREE: Regime + top signal only
- PREMIUM: Full signal board + all intelligence + triggers + macro

DELIVERY METHODS:
- Newsletter (via newsletter_alpha_integration.py)
- Telegram (via telegram_alerts.py)  
- API endpoint (for custom integrations)

SUBSCRIBER MANAGEMENT:
- Simple JSON-based for now
- Can upgrade to database later
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import hashlib

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sovereign_intel_terminal import SovereignIntelTerminal, get_db
from newsletter_alpha_integration import NewsletterAlphaGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PremiumTier")


class SubscriberManager:
    """
    Manages subscriber list and tiers.
    Simple JSON-based storage for now.
    """
    
    def __init__(self):
        self.subscribers_file = "data/subscribers.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Ensure subscribers file exists."""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.subscribers_file):
            self._save_data({"subscribers": [], "stats": {"total": 0, "premium": 0, "free": 0}})
    
    def _load_data(self) -> Dict:
        """Load subscriber data."""
        try:
            with open(self.subscribers_file) as f:
                return json.load(f)
        except:
            return {"subscribers": [], "stats": {"total": 0, "premium": 0, "free": 0}}
    
    def _save_data(self, data: Dict):
        """Save subscriber data."""
        with open(self.subscribers_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def _hash_email(self, email: str) -> str:
        """Hash email for privacy."""
        return hashlib.sha256(email.lower().strip().encode()).hexdigest()[:16]
    
    def add_subscriber(self, email: str, tier: str = "free", metadata: Dict = None) -> Dict:
        """Add a new subscriber."""
        data = self._load_data()
        
        email_hash = self._hash_email(email)
        
        # Check if already exists
        for sub in data["subscribers"]:
            if sub["email_hash"] == email_hash:
                # Update tier if upgrading
                if tier == "premium" and sub["tier"] == "free":
                    sub["tier"] = "premium"
                    sub["upgraded_at"] = datetime.now(timezone.utc).isoformat()
                    self._save_data(data)
                    return {"status": "upgraded", "email_hash": email_hash}
                return {"status": "exists", "email_hash": email_hash}
        
        # Add new subscriber
        subscriber = {
            "email_hash": email_hash,
            "email": email,  # Store for delivery
            "tier": tier,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        data["subscribers"].append(subscriber)
        
        # Update stats
        data["stats"]["total"] = len(data["subscribers"])
        data["stats"]["premium"] = len([s for s in data["subscribers"] if s["tier"] == "premium"])
        data["stats"]["free"] = len([s for s in data["subscribers"] if s["tier"] == "free"])
        
        self._save_data(data)
        
        return {"status": "added", "email_hash": email_hash, "tier": tier}
    
    def get_subscriber(self, email: str) -> Optional[Dict]:
        """Get subscriber by email."""
        data = self._load_data()
        email_hash = self._hash_email(email)
        
        for sub in data["subscribers"]:
            if sub["email_hash"] == email_hash:
                return sub
        return None
    
    def is_premium(self, email: str) -> bool:
        """Check if subscriber is premium."""
        sub = self.get_subscriber(email)
        return sub is not None and sub.get("tier") == "premium"
    
    def get_subscribers_by_tier(self, tier: str) -> List[Dict]:
        """Get all subscribers of a specific tier."""
        data = self._load_data()
        return [s for s in data["subscribers"] if s["tier"] == tier]
    
    def get_all_subscribers(self) -> List[Dict]:
        """Get all subscribers."""
        data = self._load_data()
        return data["subscribers"]
    
    def get_stats(self) -> Dict:
        """Get subscriber statistics."""
        data = self._load_data()
        return data["stats"]
    
    def upgrade_to_premium(self, email: str) -> bool:
        """Upgrade a subscriber to premium."""
        result = self.add_subscriber(email, tier="premium")
        return result["status"] in ["added", "upgraded"]
    
    def remove_subscriber(self, email: str) -> bool:
        """Remove a subscriber."""
        data = self._load_data()
        email_hash = self._hash_email(email)
        
        original_count = len(data["subscribers"])
        data["subscribers"] = [s for s in data["subscribers"] if s["email_hash"] != email_hash]
        
        if len(data["subscribers"]) < original_count:
            # Update stats
            data["stats"]["total"] = len(data["subscribers"])
            data["stats"]["premium"] = len([s for s in data["subscribers"] if s["tier"] == "premium"])
            data["stats"]["free"] = len([s for s in data["subscribers"] if s["tier"] == "free"])
            self._save_data(data)
            return True
        return False


class PremiumContentGenerator:
    """
    Generates content appropriate for each tier.
    """
    
    def __init__(self):
        self.terminal = SovereignIntelTerminal()
        self.newsletter_gen = NewsletterAlphaGenerator()
        self.subscriber_mgr = SubscriberManager()
    
    def get_content_for_email(self, email: str) -> Dict[str, Any]:
        """
        Get appropriate content for a subscriber.
        Returns tier-appropriate HTML and data.
        """
        is_premium = self.subscriber_mgr.is_premium(email)
        
        result = self.newsletter_gen.generate_newsletter_section(is_premium=is_premium)
        
        return {
            "email": email,
            "tier": "premium" if is_premium else "free",
            "html": result["html"],
            "regime": result["regime"],
            "signals_count": result["signals_count"],
            "timestamp": result["timestamp"]
        }
    
    def get_free_content(self) -> Dict[str, Any]:
        """Get free tier content."""
        return self.newsletter_gen.generate_newsletter_section(is_premium=False)
    
    def get_premium_content(self) -> Dict[str, Any]:
        """Get premium tier content."""
        return self.newsletter_gen.generate_newsletter_section(is_premium=True)
    
    def generate_teaser(self, analysis: Dict) -> str:
        """
        Generate a teaser for free users showing what they're missing.
        """
        signals = analysis.get("signals", [])
        hidden_count = len(signals) - 1 if len(signals) > 1 else 0
        
        teaser = f"""
----------------------------------------
PREMIUM SUBSCRIBERS GET:
----------------------------------------

- {hidden_count} additional signals
- Full signal board with z-scores
- Invalidation triggers for each signal
- Macro correlations (BTC vs yields, DXY)
- Operator checklists
- Historical backtest data (when available)

Upgrade at: https://protocolpulse.substack.com/subscribe

----------------------------------------
"""
        return teaser


class PremiumDeliverySystem:
    """
    Handles delivery of content to subscribers.
    """
    
    def __init__(self):
        self.subscriber_mgr = SubscriberManager()
        self.content_gen = PremiumContentGenerator()
    
    def prepare_newsletter_batch(self) -> Dict[str, List[Dict]]:
        """
        Prepare newsletter content for all subscribers.
        Returns dict with 'free' and 'premium' lists.
        """
        free_content = self.content_gen.get_free_content()
        premium_content = self.content_gen.get_premium_content()
        
        free_subscribers = self.subscriber_mgr.get_subscribers_by_tier("free")
        premium_subscribers = self.subscriber_mgr.get_subscribers_by_tier("premium")
        
        return {
            "free": {
                "subscribers": [s["email"] for s in free_subscribers],
                "count": len(free_subscribers),
                "content": free_content
            },
            "premium": {
                "subscribers": [s["email"] for s in premium_subscribers],
                "count": len(premium_subscribers),
                "content": premium_content
            },
            "stats": self.subscriber_mgr.get_stats()
        }
    
    def print_delivery_summary(self):
        """Print summary of what would be delivered."""
        batch = self.prepare_newsletter_batch()
        
        print("""
======================================================================
                    NEWSLETTER DELIVERY SUMMARY                        
======================================================================
""")
        print(f"FREE TIER:")
        print(f"   Subscribers: {batch['free']['count']}")
        print(f"   Content: Regime + top signal + upgrade CTA")
        print()
        print(f"PREMIUM TIER:")
        print(f"   Subscribers: {batch['premium']['count']}")
        print(f"   Content: Full signal board + all intelligence")
        print()
        print(f"TOTAL SUBSCRIBERS: {batch['stats']['total']}")
        print()
        print("======================================================================")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
Usage: python3 premium_tier.py <command> [args]

Commands:
  add <email> [tier]     - Add subscriber (tier: free or premium)
  upgrade <email>        - Upgrade to premium
  remove <email>         - Remove subscriber
  check <email>          - Check subscriber status
  list                   - List all subscribers
  stats                  - Show subscriber stats
  preview free           - Preview free tier content
  preview premium        - Preview premium tier content
  batch                  - Prepare newsletter batch
""")
        sys.exit(1)
    
    cmd = sys.argv[1]
    subscriber_mgr = SubscriberManager()
    content_gen = PremiumContentGenerator()
    delivery = PremiumDeliverySystem()
    
    if cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: python3 premium_tier.py add <email> [tier]")
            sys.exit(1)
        email = sys.argv[2]
        tier = sys.argv[3] if len(sys.argv) > 3 else "free"
        result = subscriber_mgr.add_subscriber(email, tier)
        print(f"Result: {result}")
    
    elif cmd == "upgrade":
        if len(sys.argv) < 3:
            print("Usage: python3 premium_tier.py upgrade <email>")
            sys.exit(1)
        email = sys.argv[2]
        if subscriber_mgr.upgrade_to_premium(email):
            print(f"SUCCESS: {email} upgraded to premium")
        else:
            print(f"ERROR: Could not upgrade {email}")
    
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("Usage: python3 premium_tier.py remove <email>")
            sys.exit(1)
        email = sys.argv[2]
        if subscriber_mgr.remove_subscriber(email):
            print(f"SUCCESS: {email} removed")
        else:
            print(f"ERROR: {email} not found")
    
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("Usage: python3 premium_tier.py check <email>")
            sys.exit(1)
        email = sys.argv[2]
        sub = subscriber_mgr.get_subscriber(email)
        if sub:
            print(f"Email: {email}")
            print(f"Tier: {sub['tier'].upper()}")
            print(f"Created: {sub['created_at']}")
        else:
            print(f"Subscriber not found: {email}")
    
    elif cmd == "list":
        subscribers = subscriber_mgr.get_all_subscribers()
        print(f"\nTotal subscribers: {len(subscribers)}\n")
        for sub in subscribers:
            tier_badge = "[PREMIUM]" if sub["tier"] == "premium" else "[FREE]"
            print(f"  {tier_badge} {sub['email']}")
    
    elif cmd == "stats":
        stats = subscriber_mgr.get_stats()
        print(f"\nSubscriber Stats:")
        print(f"  Total: {stats['total']}")
        print(f"  Premium: {stats['premium']}")
        print(f"  Free: {stats['free']}")
    
    elif cmd == "preview":
        if len(sys.argv) < 3:
            print("Usage: python3 premium_tier.py preview [free|premium]")
            sys.exit(1)
        tier = sys.argv[2]
        
        if tier == "free":
            content = content_gen.get_free_content()
        else:
            content = content_gen.get_premium_content()
        
        print(f"\n{tier.upper()} TIER PREVIEW:")
        print(f"Regime: {content['regime']}")
        print(f"Signals: {content['signals_count']}")
        print(f"\nHTML saved to: data/preview_{tier}.html")
        
        with open(f"data/preview_{tier}.html", "w") as f:
            f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{tier.upper()} Tier Preview</title>
    <style>
        body {{
            background: #0d0d0d;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            max-width: 600px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
{content['html']}
</body>
</html>
            """)
    
    elif cmd == "batch":
        delivery.print_delivery_summary()
    
    else:
        print(f"Unknown command: {cmd}")
