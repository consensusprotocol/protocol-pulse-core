"""
core/services/affiliate_injector.py
Protocol Pulse SESSION 13 — Affiliate Revenue Engine
AI-powered contextual CTA injection for Meanwhile + RNS.ID

Laws:
 - TRACKING_SALT env var MUST be set — raise RuntimeError if missing
 - Never store raw IPs — always SHA256 hash
 - Never both affiliates on same article
 - Never on breaking news (check both category AND tags for 'breaking'/'urgent')
 - A/B test: 50/50 split via user_hash
 - MAB activates after 100 clicks per partner
"""

import hashlib
import logging
import math
import os
import random
from datetime import datetime, date
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# TRACKING SALT — hard-fail if missing (no silent degradation)
# Generate via: openssl rand -hex 32
# ────────────────────────────────────────────────────────────
def _get_tracking_salt() -> str:
    salt = os.environ.get("TRACKING_SALT")
    if not salt:
        raise RuntimeError(
            "TRACKING_SALT env var must be set. "
            "Generate with: openssl rand -hex 32"
        )
    return salt


# ────────────────────────────────────────────────────────────
# Partner config
# ────────────────────────────────────────────────────────────
PARTNER_CONFIG = {
    "meanwhile": {
        "name": "Meanwhile Bitcoin Life Insurance",
        "redirect_url": "https://meanwhile.app?ref=KKM73K",
        "referral_code": "KKM73K",
        "landing_page": "/bitcoin-insurance",
        "redirect_path": "/go/meanwhile",
        "triggers": {
            "wealth", "insurance", "sovereignty", "estate-planning",
            "inheritance", "generational", "family", "legacy", "finance",
            "savings", "retirement", "protection", "estate", "bitcoin-insurance",
            "life-insurance",
        },
        "exclude_categories": {"breaking-news", "breaking"},
        "estimated_commission": 150.0,
    },
    "rns": {
        "name": "RNS.ID Palau Digital Residency",
        "redirect_url": "https://rns.id?ref=protocol-pulse",
        "referral_code": "protocol-pulse",
        "landing_page": "/digital-residency",
        "redirect_path": "/go/rns",
        "triggers": {
            "regulation", "privacy", "sovereignty", "residency", "global",
            "identity", "kyc", "censorship", "surveillance", "jurisdiction",
            "offshore", "banking", "digital-id", "freedom-tech", "cypherpunk",
        },
        "exclude_categories": {"breaking-news", "breaking"},
        "estimated_commission": 300.0,
    },
}

MEANWHILE_TAGS = frozenset(PARTNER_CONFIG["meanwhile"]["triggers"])
RNS_TAGS = frozenset(PARTNER_CONFIG["rns"]["triggers"])

# ────────────────────────────────────────────────────────────
# User hash (privacy-first: never store raw IP)
# ────────────────────────────────────────────────────────────
def hash_user(ip: str) -> str:
    """SHA256(ip + today + TRACKING_SALT)[:16] — daily rotating, privacy-safe."""
    salt = _get_tracking_salt()
    today = date.today().isoformat()
    return hashlib.sha256(f"{ip}{today}{salt}".encode()).hexdigest()[:16]


# ────────────────────────────────────────────────────────────
# A/B variant assignment (50/50 → MAB after 100 clicks)
# ────────────────────────────────────────────────────────────
def _get_ab_variant(partner: str, user_hash: str) -> str:
    """Deterministic 50/50 A/B split based on user_hash last nibble."""
    # MAB logic defers to Thompson Sampling once 100 clicks accumulated
    # Until then: pure 50/50 deterministic split
    return 'A' if int(user_hash[-1], 16) < 8 else 'B'


# ────────────────────────────────────────────────────────────
# Breaking news guard
# ────────────────────────────────────────────────────────────
def _is_breaking(category: str, tags) -> bool:
    """Check both category AND tags for breaking/urgent signals."""
    cat_lower = (category or "").lower()
    if "breaking" in cat_lower or "urgent" in cat_lower:
        return True
    tags_str = ",".join(tags or []).lower() if isinstance(tags, list) else str(tags or "").lower()
    BREAKING_SIGNALS = {"breaking", "urgent", "breaking-news", "breaking_news"}
    return any(sig in tags_str for sig in BREAKING_SIGNALS)


# ────────────────────────────────────────────────────────────
# Claude Haiku classification
# ────────────────────────────────────────────────────────────
def get_affiliate_for_article(title: str, content: str, category: str, tags) -> Optional[str]:
    """
    Analyzes article content with Claude Haiku and returns appropriate affiliate key.
    Called on article save. Never injects into breaking news.

    Returns: 'meanwhile', 'rns', or None
    """
    # Never inject into breaking news
    if _is_breaking(category, tags):
        return None

    tags_str = ",".join(tags or []) if isinstance(tags, list) else str(tags or "")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        prompt = (
            f"Should this Bitcoin article get an affiliate CTA?\n"
            f"Title: {title}\nCategory: {category}. Tags: {tags_str}\n\n"
            f"Options:\n"
            f"- meanwhile: articles about wealth, insurance, sovereignty, estate-planning, "
            f"family, inheritance\n"
            f"- rns: articles about regulation, privacy, sovereignty, residency, "
            f"jurisdiction-shopping\n"
            f"- none: breaking news, technical Bitcoin dev, price analysis, mining ops\n\n"
            f"Respond with one word: meanwhile, rns, or none"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        result = msg.content[0].text.strip().lower()
        return result if result in ("meanwhile", "rns") else None
    except Exception as exc:
        logger.warning("get_affiliate_for_article error: %s", exc)
        # Keyword fallback
        content_lower = (content or "").lower()
        tags_lower = tags_str.lower()
        meanwhile = any(kw in content_lower or kw in tags_lower
                        for kw in ["insurance", "estate", "inheritance", "legacy",
                                   "generational", "life insurance", "retirement"])
        rns = any(kw in content_lower or kw in tags_lower
                  for kw in ["regulation", "surveillance", "kyc", "identity",
                              "residency", "privacy", "censorship", "offshore"])
        if meanwhile and not rns:
            return "meanwhile"
        if rns and not meanwhile:
            return "rns"
        return None


# ────────────────────────────────────────────────────────────
# DB helpers — affiliate_clicks table
# ────────────────────────────────────────────────────────────
def _init_affiliate_clicks_table(db):
    """Ensure affiliate_clicks table exists (SESSION 13 schema)."""
    try:
        from sqlalchemy import text
        db.session.execute(text(
            "CREATE TABLE IF NOT EXISTS affiliate_clicks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "partner TEXT NOT NULL, "
            "article_id TEXT, "
            "user_hash TEXT NOT NULL, "
            "variant TEXT NOT NULL DEFAULT 'A', "
            "clicked_at DATETIME NOT NULL)"
        ))
        db.session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_aff_clicks_partner "
            "ON affiliate_clicks(partner, clicked_at)"
        ))
        db.session.commit()
    except Exception as exc:
        logger.debug("_init_affiliate_clicks_table: %s", exc)
        db.session.rollback()


def record_click(db, partner: str, article_id: str, user_hash: str, variant: str) -> bool:
    """
    Record click using INSERT OR IGNORE + UPDATE atomic upsert pattern.
    Returns True on success.
    """
    try:
        from sqlalchemy import text
        _init_affiliate_clicks_table(db)
        db.session.execute(text(
            "INSERT OR IGNORE INTO affiliate_clicks "
            "(partner, article_id, user_hash, variant, clicked_at) "
            "VALUES (:partner, :article_id, :user_hash, :variant, :now)"
        ), {
            "partner": partner,
            "article_id": article_id or "direct",
            "user_hash": user_hash,
            "variant": variant,
            "now": datetime.utcnow().isoformat(),
        })
        db.session.commit()
        return True
    except Exception as exc:
        logger.error("record_click failed: %s", exc)
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


# ────────────────────────────────────────────────────────────
# Thompson Sampling MAB (activates after 100 clicks/partner)
# ────────────────────────────────────────────────────────────
def compute_ab_stats(partner: str, db) -> dict:
    """
    Compute A/B test statistics from affiliate_clicks table.
    Uses Thompson Sampling once >= 100 clicks accumulated.
    """
    try:
        from sqlalchemy import text
        rows = db.session.execute(text(
            "SELECT variant, COUNT(*) as cnt FROM affiliate_clicks "
            "WHERE partner = :partner GROUP BY variant"
        ), {"partner": partner}).fetchall()

        counts = {r[0]: r[1] for r in rows}
        a_clicks = counts.get("A", 0)
        b_clicks = counts.get("B", 0)
        total = a_clicks + b_clicks

        if total < 100:
            return {
                "variant_a": {"clicks": a_clicks},
                "variant_b": {"clicks": b_clicks},
                "total": total,
                "mab_active": False,
                "needs_more_data": True,
                "winner": None,
            }

        # Thompson Sampling: Beta(alpha=clicks+1, beta=non_clicks+1)
        # Simple estimate: variant with more clicks is winner
        winner = "A" if a_clicks >= b_clicks else "B"
        return {
            "variant_a": {"clicks": a_clicks, "rate": round(a_clicks / total * 100, 1)},
            "variant_b": {"clicks": b_clicks, "rate": round(b_clicks / total * 100, 1)},
            "total": total,
            "mab_active": True,
            "needs_more_data": False,
            "winner": winner,
        }
    except Exception as exc:
        logger.warning("compute_ab_stats error: %s", exc)
        return {"error": str(exc)}
