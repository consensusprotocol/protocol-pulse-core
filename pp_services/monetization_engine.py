
"""
Monetization Engine
===================
Handles:
- Affiliate link injection
- Meanwhile (Bitcoin life insurance) integration
- Partner ramp tracking
- Revenue analytics
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MonetizationEngine:
    """
    Revenue generation and tracking.
    """
    
    def __init__(self):
        self.affiliates_file = Path("config/affiliates.json")
        self.partner_ramp_file = Path("config/partner_ramp.json")
        self.affiliates = self._load_affiliates()
        self.partners = self._load_partners()
    
    def _load_affiliates(self) -> Dict:
        """Load affiliate configuration."""
        if self.affiliates_file.exists():
            try:
                with open(self.affiliates_file) as f:
                    return json.load(f)
            except:
                pass
        
        # Default affiliates
        return {
            "meanwhile": {
                "name": "Meanwhile (Bitcoin Life Insurance)",
                "url": "https://application.meanwhile.bm/start?referralCode=KKM73K",
                "description": "Bitcoin-denominated life insurance",
                "commission": "Varies",
                "priority": 1,
                "keywords": ["life insurance", "insurance", "protection", "family", "inheritance"]
            },
            "amazon": {
                "name": "Amazon",
                "tag": os.environ.get("AMAZON_AFFILIATE_TAG", "protocolpulse-20"),
                "priority": 2
            },
            "trezor": {
                "name": "Trezor",
                "url": "https://trezor.io/?ref=protocolpulse",
                "description": "Hardware wallets",
                "priority": 2,
                "keywords": ["hardware wallet", "cold storage", "self-custody", "trezor"]
            },
            "river": {
                "name": "River",
                "url": "https://river.com/?ref=protocolpulse",
                "description": "Bitcoin exchange",
                "priority": 3,
                "keywords": ["buy bitcoin", "exchange", "dca", "recurring"]
            }
        }
    
    def _load_partners(self) -> Dict:
        """Load partner ramp configuration."""
        if self.partner_ramp_file.exists():
            try:
                with open(self.partner_ramp_file) as f:
                    return json.load(f)
            except:
                pass
        
        # Default partner ramp
        return {
            "categories": {
                "earn": [
                    {"name": "Strike", "url": "https://strike.me", "description": "Earn Bitcoin on purchases"}
                ],
                "borrow": [
                    {"name": "Unchained", "url": "https://unchained.com", "description": "Bitcoin-backed loans"}
                ],
                "insure": [
                    {"name": "Meanwhile", "url": "https://application.meanwhile.bm/start?referralCode=KKM73K", "description": "Bitcoin life insurance", "featured": True}
                ],
                "spend": [
                    {"name": "Fold", "url": "https://foldapp.com", "description": "Bitcoin rewards card"}
                ],
                "save": [
                    {"name": "Swan", "url": "https://swanbitcoin.com", "description": "Auto-DCA Bitcoin"}
                ],
                "custody": [
                    {"name": "Casa", "url": "https://keys.casa", "description": "Multi-sig self-custody"}
                ]
            }
        }
    
    def inject_affiliate_links(self, content: str) -> str:
        """
        Inject affiliate links into article content.
        """
        content_lower = content.lower()
        
        for aff_id, affiliate in self.affiliates.items():
            keywords = affiliate.get("keywords", [])
            url = affiliate.get("url", "")
            name = affiliate.get("name", "")
            
            if not url or not keywords:
                continue
            
            for keyword in keywords:
                if keyword in content_lower:
                    # Find the keyword in original content (case-insensitive)
                    import re
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                    
                    # Only replace first occurrence
                    match = pattern.search(content)
                    if match:
                        original = match.group()
                        linked = f'<a href="{url}" target="_blank" rel="sponsored" class="affiliate-link">{original}</a>'
                        content = content[:match.start()] + linked + content[match.end():]
                        break  # Only one link per affiliate
        
        return content
    
    def get_meanwhile_cta(self) -> Dict:
        """Get Meanwhile life insurance CTA block."""
        return {
            "title": "Protect Your Family's Future with Bitcoin",
            "description": "Meanwhile offers the first Bitcoin-denominated whole life insurance. Your policy, your keys, your sovereignty.",
            "cta_text": "Learn More",
            "url": self.affiliates.get("meanwhile", {}).get("url", "https://application.meanwhile.bm/start?referralCode=KKM73K"),
            "features": [
                "Bitcoin-denominated death benefit",
                "Self-custody friendly",
                "No fiat conversion required"
            ]
        }
    
    def get_partner_ramp(self) -> Dict:
        """Get full partner ramp for onboarding page."""
        return self.partners
    
    def track_click(self, partner_id: str, user_id: Optional[int] = None, source: str = "article") -> bool:
        """Track affiliate/partner click."""
        try:
            from app import app, db
            from models import AffiliateClick
            
            with app.app_context():
                click = AffiliateClick(
                    partner_id=partner_id,
                    user_id=user_id,
                    source=source,
                    timestamp=datetime.utcnow()
                )
                db.session.add(click)
                db.session.commit()
                return True
        except Exception as e:
            logger.warning(f"Click tracking error: {e}")
            return False
    
    def get_revenue_stats(self, days: int = 30) -> Dict:
        """Get revenue statistics."""
        try:
            from app import app
            from models import AffiliateClick
            from datetime import timedelta
            
            with app.app_context():
                cutoff = datetime.utcnow() - timedelta(days=days)
                
                clicks = AffiliateClick.query.filter(
                    AffiliateClick.timestamp >= cutoff
                ).all()
                
                by_partner = {}
                for click in clicks:
                    pid = click.partner_id or "unknown"
                    by_partner[pid] = by_partner.get(pid, 0) + 1
                
                return {
                    "total_clicks": len(clicks),
                    "by_partner": by_partner,
                    "period_days": days
                }
        except Exception as e:
            logger.warning(f"Revenue stats error: {e}")
            return {"total_clicks": 0, "by_partner": {}, "period_days": days}


# Singleton
monetization_engine = MonetizationEngine()
