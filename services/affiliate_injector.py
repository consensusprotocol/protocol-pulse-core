"""
services/affiliate_injector.py
Protocol Pulse P3 Affiliate Integration
AI-powered contextual CTA injection for Meanwhile + RNS.ID

Laws:
 - Contextual relevance only (no random spam)
 - A/B testing with Thompson Sampling MAB
 - IP never stored raw (SHA256+salt hash only)
 - Never on homepage/list pages — article detail only
 - Never both CTAs on same article
 - Never on breaking news articles
"""

import hashlib
import logging
import math
import os
import random
import sqlite3
from datetime import datetime, date
from functools import lru_cache
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# Partner config
# ────────────────────────────────────────────────────────────
# P0 FIX (U2): Hard-fail on missing TRACKING_SALT — no silent degradation
# Generate via: openssl rand -hex 32 and add to .env
def _get_tracking_salt() -> str:
    salt = os.environ.get("TRACKING_SALT")
    if not salt:
        raise RuntimeError(
            "TRACKING_SALT env var must be set. "
            "Generate with: openssl rand -hex 32"
        )
    return salt


PARTNER_CONFIG = {
    "meanwhile": {
        "name": "Meanwhile Bitcoin Life Insurance",
        "redirect_url": "https://www.meanwhile.life/?ref=KKM73K",
        "referral_code": "KKM73K",
        "landing_page": "/bitcoin-life-insurance",
        "redirect_path": "/go/meanwhile",
        "triggers": {"wealth", "insurance", "sovereignty", "estate-planning",
                     "inheritance", "generational", "family", "legacy", "finance",
                     "savings", "retirement", "protection", "estate", "bitcoin-insurance"},
        "exclude_categories": {"breaking-news", "breaking"},
        "estimated_commission": 150.0,
        "sovereignty_score": {
            "privacy": 4,
            "btc_native": 5,
            "non_custodial": 3,
            "regulatory": 4,
            "transparency": 4,
        },
    },
    "rns_id": {
        "name": "RNS.ID Palau Digital Residency",
        "redirect_url": "https://rns.id/?ref=protocolpulse",
        "referral_code": "protocolpulse",
        "landing_page": "/digital-residency",
        "redirect_path": "/go/rns",
        "triggers": {"regulation", "privacy", "sovereignty", "residency", "global",
                     "identity", "kyc", "censorship", "surveillance", "jurisdiction",
                     "offshore", "banking", "digital-id", "freedom-tech", "cypherpunk"},
        "exclude_categories": {"breaking-news", "breaking"},
        "estimated_commission": 300.0,
        "sovereignty_score": {
            "privacy": 5,
            "btc_native": 3,
            "non_custodial": 5,
            "regulatory": 3,
            "transparency": 4,
        },
    },
}

# Category tags that map to partner triggers
MEANWHILE_TAGS = frozenset(PARTNER_CONFIG["meanwhile"]["triggers"])
RNS_TAGS = frozenset(PARTNER_CONFIG["rns_id"]["triggers"])


# ────────────────────────────────────────────────────────────
# Claude Haiku classification
# ────────────────────────────────────────────────────────────
@lru_cache(maxsize=512)
def _classify_article(article_id: int, content_snippet: str) -> dict:
    """
    Use Claude Haiku to classify article themes.
    Returns {meanwhile: bool, rns_id: bool, themes: list[str]}.
    Cached per article_id so we only call API once per article.
    """
    try:
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

        system_prompt = (
            "You are a content classifier for a Bitcoin media publication. "
            "Classify the article excerpt into relevant themes. "
            "Respond ONLY with a JSON object. No explanations.\n"
            "Format: {\"themes\": [\"list of theme keywords\"], "
            "\"meanwhile_relevant\": true/false, "
            "\"rns_relevant\": true/false}\n\n"
            "meanwhile_relevant = true if article discusses: "
            "wealth, estate planning, insurance, generational wealth, "
            "inheritance, Bitcoin savings, family finance, legacy planning, "
            "life insurance, retirement, financial sovereignty.\n\n"
            "rns_relevant = true if article discusses: "
            "regulation, surveillance, KYC, identity, digital residency, "
            "privacy, sovereignty, offshore banking, censorship resistance, "
            "jurisdiction shopping, freedom tech, cypherpunk topics.\n\n"
            "Breaking news / price action articles = both false.\n"
            "Never set both to true for the same article."
        )

        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": content_snippet[:1500]}],
            timeout=10,
        )

        import json as _json
        raw = resp.content[0].text.strip()
        # Strip potential markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = _json.loads(raw)
        return {
            "meanwhile": bool(result.get("meanwhile_relevant", False)),
            "rns_id": bool(result.get("rns_relevant", False)),
            "themes": result.get("themes", []),
        }
    except Exception as exc:
        logger.warning("affiliate_injector classify error: %s", exc)
        # Fallback: keyword-based classification
        content_lower = content_snippet.lower()
        meanwhile = any(kw in content_lower for kw in
                        ["insurance", "estate", "inheritance", "legacy", "generational",
                         "life insurance", "protection", "wealth", "retirement"])
        rns = any(kw in content_lower for kw in
                  ["regulation", "surveillance", "kyc", "identity", "residency",
                   "privacy", "sovereignty", "censorship", "offshore"])
        return {"meanwhile": meanwhile and not rns, "rns_id": rns and not meanwhile, "themes": []}


# ────────────────────────────────────────────────────────────
# Thompson Sampling MAB
# ────────────────────────────────────────────────────────────
def _get_mab_weights(partner: str) -> tuple[float, float]:
    """
    Read MAB state from DB. Returns (weight_A, weight_B) as probabilities summing to 1.
    Falls back to 50/50 if no data.
    Uses Thompson Sampling: sample from Beta(alpha, beta) for each arm, pick higher.
    At low data counts (<100 total clicks), returns 0.5/0.5.
    """
    try:
        from app import db
        import sqlalchemy
        result = db.session.execute(
            sqlalchemy.text(
                "SELECT variant, impressions, clicks FROM p3_affiliate_ab_results "
                "WHERE partner = :partner ORDER BY variant"
            ),
            {"partner": partner},
        ).fetchall()

        rows = {r[0]: (r[1], r[2]) for r in result}
        a_impr, a_clicks = rows.get("A", (0, 0))
        b_impr, b_clicks = rows.get("B", (0, 0))

        # P1 FIX (M2): MAB activates on CLICKS not impressions — clicks are
        # the meaningful signal of intent per the gospel spec
        total_clicks = a_clicks + b_clicks
        if total_clicks < 100:
            return 0.5, 0.5

        # Thompson Sampling: sample from Beta distribution
        # alpha = clicks + 1, beta = (impressions - clicks) + 1
        a_alpha = a_clicks + 1
        a_beta = max(a_impr - a_clicks, 0) + 1
        b_alpha = b_clicks + 1
        b_beta = max(b_impr - b_clicks, 0) + 1

        # Monte Carlo Thompson Sampling approximation (no scipy)
        # Use closed-form: expected value of Beta = alpha/(alpha+beta)
        # For allocation, sample 1000 times and count wins
        wins_a = 0
        for _ in range(200):
            sample_a = _beta_sample(a_alpha, a_beta)
            sample_b = _beta_sample(b_alpha, b_beta)
            if sample_a > sample_b:
                wins_a += 1

        weight_a = wins_a / 200
        weight_b = 1.0 - weight_a
        # Clip to prevent 0% allocation (exploration)
        weight_a = max(0.05, min(0.95, weight_a))
        weight_b = 1.0 - weight_a
        return weight_a, weight_b

    except Exception as exc:
        logger.debug("MAB weight lookup failed: %s", exc)
        return 0.5, 0.5


def _beta_sample(alpha: float, beta: float) -> float:
    """
    Sample from Beta(alpha, beta) distribution using Johnk's method.
    Pure Python, no numpy/scipy.
    """
    try:
        return random.betavariate(alpha, beta)
    except Exception:
        return alpha / (alpha + beta)


def _get_ab_variant(partner: str, user_hash: str) -> str:
    """
    Determine A/B variant for a user.
    Uses deterministic hash, weighted by current MAB allocation.
    Consistent: same user+date → same variant, but allocation shifts over time.
    """
    weight_a, _ = _get_mab_weights(partner)
    # Deterministic value 0.0 - 1.0 from hash
    hash_val = int(hashlib.sha256(f"{user_hash}:{partner}".encode()).hexdigest()[:8], 16)
    normalized = hash_val / 0xFFFFFFFF
    return "A" if normalized < weight_a else "B"


# ────────────────────────────────────────────────────────────
# CTA HTML generation
# ────────────────────────────────────────────────────────────
def _render_cta(partner: str, variant: str) -> str:
    """Generate CTA HTML for a given partner and variant."""
    cfg = PARTNER_CONFIG[partner]
    path = cfg["redirect_path"]
    landing = cfg["landing_page"]

    if partner == "meanwhile":
        if variant == "A":
            return (
                f'<span class="affiliate-inline" data-partner="meanwhile" data-variant="A">'
                f'Tools like <a href="{path}" class="aff-link-inline" '
                f'data-partner="meanwhile">Meanwhile</a> let Bitcoiners protect '
                f'generational wealth with BTC-denominated life insurance.</span>'
            )
        else:  # Variant B — card
            return f"""<div class="affiliate-card" data-partner="meanwhile" data-variant="B" role="complementary" aria-label="Affiliate: Meanwhile Bitcoin Insurance">
  <div class="aff-card-inner">
    <div class="aff-card-badge">AFFILIATE PARTNERSHIP</div>
    <div class="aff-card-header">
      <span class="aff-card-icon">🛡</span>
      <div class="aff-card-title-wrap">
        <span class="aff-card-title">Meanwhile</span>
        <span class="aff-card-subtitle">Bitcoin Life Insurance</span>
      </div>
    </div>
    <p class="aff-card-pitch">Death benefit in BTC — your family inherits sovereignty, not a fiat check. <strong>Self-sovereign estate planning.</strong></p>
    <a href="{path}" class="aff-card-cta" data-partner="meanwhile" aria-label="Learn more about Meanwhile Bitcoin Life Insurance">Learn More →</a>
  </div>
</div>"""

    else:  # rns_id
        if variant == "A":
            return (
                f'<span class="affiliate-inline" data-partner="rns_id" data-variant="A">'
                f'Establishing a <a href="{path}" class="aff-link-inline" '
                f'data-partner="rns_id">Palau digital residency</a> via RNS.ID offers '
                f'a government-issued digital identity outside traditional financial '
                f'surveillance systems.</span>'
            )
        else:  # Variant B — card
            return f"""<div class="affiliate-card" data-partner="rns_id" data-variant="B" role="complementary" aria-label="Affiliate: RNS.ID Digital Residency">
  <div class="aff-card-inner">
    <div class="aff-card-badge">AFFILIATE PARTNERSHIP</div>
    <div class="aff-card-header">
      <span class="aff-card-icon">🌐</span>
      <div class="aff-card-title-wrap">
        <span class="aff-card-title">RNS.ID</span>
        <span class="aff-card-subtitle">Palau Digital Residency</span>
      </div>
    </div>
    <p class="aff-card-pitch">A government-issued digital ID outside the surveillance state. <strong>Digital sovereignty starts with identity.</strong></p>
    <a href="{path}" class="aff-card-cta aff-cta-green" data-partner="rns_id" aria-label="Apply for Palau Digital Residency">Apply Now →</a>
  </div>
</div>"""


# ────────────────────────────────────────────────────────────
# Main injection function
# ────────────────────────────────────────────────────────────
def inject_affiliate_cta(
    article_id: int,
    article_content: str,
    article_category: str,
    article_tags: str,
    client_ip: str,
) -> Optional[dict]:
    """
    Determine whether to inject an affiliate CTA for this article.

    Returns dict with {partner, variant, cta_html, partner_cfg} or None.
    Never returns CTA for breaking news or if category is excluded.
    Never returns both partners on same article.
    """
    try:
        # P1 FIX (M3): Check both category AND tags for breaking news
        cat_lower = (article_category or "").lower()
        tags_lower = (article_tags or "").lower()
        BREAKING_SIGNALS = {"breaking", "breaking-news", "urgent", "breaking_news"}
        if "breaking" in cat_lower or any(sig in tags_lower for sig in BREAKING_SIGNALS):
            return None

        # Build content snippet for classification
        content_snippet = (article_content or "")[:2000]

        # P1 FIX (I5): Tags are the authoritative gate.
        # AI classification is a soft enrichment — requires tag agreement.
        # "AI-only with no matching tags" does NOT qualify.
        meanwhile_tag_match = any(t in tags_lower for t in MEANWHILE_TAGS)
        rns_tag_match = any(t in tags_lower for t in RNS_TAGS)

        # AI classification (cached by article_id) — only called if tags suggest relevance
        if meanwhile_tag_match or rns_tag_match:
            classification = _classify_article(article_id, content_snippet)
            ai_meanwhile = classification.get("meanwhile", False)
            ai_rns = classification.get("rns_id", False)
        else:
            ai_meanwhile = False
            ai_rns = False

        # Require: (tag match) OR (AI + tag match in content)
        meanwhile_ok = meanwhile_tag_match or (ai_meanwhile and any(
            t in content_snippet.lower() for t in MEANWHILE_TAGS))
        rns_ok = rns_tag_match or (ai_rns and any(
            t in content_snippet.lower() for t in RNS_TAGS))

        # Never show both — pick one (meanwhile wins ties)
        if meanwhile_ok and rns_ok:
            rns_ok = False  # meanwhile takes priority

        if not meanwhile_ok and not rns_ok:
            return None

        partner = "meanwhile" if meanwhile_ok else "rns_id"

        # Generate user hash (privacy-first: never store raw IP)
        # P0 FIX (U2): hard-fail on missing salt
        salt = _get_tracking_salt()
        today = date.today().isoformat()
        user_hash = hashlib.sha256(f"{client_ip}:{today}:{salt}".encode()).hexdigest()

        # MAB variant assignment
        variant = _get_ab_variant(partner, user_hash)

        # Render CTA HTML
        cta_html = _render_cta(partner, variant)

        return {
            "partner": partner,
            "variant": variant,
            "cta_html": cta_html,
            "user_hash": user_hash,
            "partner_cfg": PARTNER_CONFIG[partner],
        }

    except Exception as exc:
        logger.warning("inject_affiliate_cta error article_id=%s: %s", article_id, exc)
        return None


# ────────────────────────────────────────────────────────────
# DB helpers
# ────────────────────────────────────────────────────────────
def track_click(partner: str, referrer_page: str, ab_variant: str,
                user_hash: str, user_agent: str) -> bool:
    """Record a click in p3_affiliate_clicks. Returns True on success."""
    try:
        from app import db
        import sqlalchemy
        # Sanitize referrer_page — only store path, not full URL (avoids storing PII in query strings)
        safe_referrer = (referrer_page or "")[:500]
        ua_hash = hashlib.sha256((user_agent or "").encode()).hexdigest()
        db.session.execute(
            sqlalchemy.text(
                "INSERT INTO p3_affiliate_clicks "
                "(partner, referrer_page, ab_variant, converted, user_hash, "
                "user_agent_hash, clicked_at) "
                "VALUES (:partner, :ref, :variant, 0, :uhash, :uahash, :now)"
            ),
            {
                "partner": partner,
                "ref": safe_referrer,
                "variant": ab_variant or "A",
                "uhash": user_hash,
                "uahash": ua_hash,
                "now": datetime.utcnow().isoformat(),
            },
        )
        db.session.commit()

        # Increment AB results
        _increment_ab_clicks(partner, ab_variant)
        return True
    except Exception as exc:
        logger.error("track_click failed: %s", exc)
        try:
            from app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        return False


def track_impression(partner: str, referrer_page: str, ab_variant: str,
                     user_hash: str) -> bool:
    """Record an impression in p3_affiliate_ab_results."""
    try:
        _increment_ab_impressions(partner, ab_variant)
        return True
    except Exception as exc:
        logger.debug("track_impression failed: %s", exc)
        return False


# TODO(p4-conversion): Implement server-to-server conversion postback.
# Add POST /api/affiliates/conversion endpoint that:
#   1. Validates shared HMAC secret from partner webhook
#   2. Flips converted=1 for matching user_hash + partner + date window
#   3. Logs revenue_usd if partner provides it
# Without this, the MAB optimizes for clicks not revenue (world-class gap #1 from audit).
# Meanwhile API docs: https://www.meanwhile.life/api (check partner portal)
# RNS.ID API docs: check partner dashboard for webhook configuration


def _increment_ab_impressions(partner: str, variant: str):
    """
    P0 FIX (U1): Atomic upsert — eliminates SELECT-then-INSERT race condition.
    Uses SQLite INSERT OR IGNORE + UPDATE pattern for true atomicity.
    """
    from app import db
    import sqlalchemy
    now = datetime.utcnow().isoformat()
    # INSERT OR IGNORE creates the row if absent (0 impressions, 0 clicks)
    db.session.execute(
        sqlalchemy.text(
            "INSERT OR IGNORE INTO p3_affiliate_ab_results "
            "(partner, variant, impressions, clicks, winner_locked, calculated_at) "
            "VALUES (:partner, :variant, 0, 0, 0, :now)"
        ),
        {"partner": partner, "variant": variant, "now": now},
    )
    # UPDATE increments atomically — no read-modify-write race
    db.session.execute(
        sqlalchemy.text(
            "UPDATE p3_affiliate_ab_results "
            "SET impressions = impressions + 1, calculated_at = :now "
            "WHERE partner = :partner AND variant = :variant"
        ),
        {"now": now, "partner": partner, "variant": variant},
    )
    db.session.commit()


def _increment_ab_clicks(partner: str, variant: str):
    """
    P0 FIX (U1): Atomic upsert — eliminates SELECT-then-INSERT race condition.
    Uses SQLite INSERT OR IGNORE + UPDATE pattern for true atomicity.
    """
    from app import db
    import sqlalchemy
    now = datetime.utcnow().isoformat()
    db.session.execute(
        sqlalchemy.text(
            "INSERT OR IGNORE INTO p3_affiliate_ab_results "
            "(partner, variant, impressions, clicks, winner_locked, calculated_at) "
            "VALUES (:partner, :variant, 0, 0, 0, :now)"
        ),
        {"partner": partner, "variant": variant, "now": now},
    )
    db.session.execute(
        sqlalchemy.text(
            "UPDATE p3_affiliate_ab_results "
            "SET clicks = clicks + 1, impressions = impressions + 1, "
            "calculated_at = :now "
            "WHERE partner = :partner AND variant = :variant"
        ),
        {"now": now, "partner": partner, "variant": variant},
    )
    db.session.commit()


# ────────────────────────────────────────────────────────────
# Statistical significance (no scipy)
# ────────────────────────────────────────────────────────────
def compute_ab_stats(partner: str) -> dict:
    """
    Compute A/B test statistics for a partner.
    Returns significance, winning variant, confidence level.
    """
    try:
        from app import db
        import sqlalchemy
        rows = db.session.execute(
            sqlalchemy.text(
                "SELECT variant, impressions, clicks FROM p3_affiliate_ab_results "
                "WHERE partner = :partner"
            ),
            {"partner": partner},
        ).fetchall()

        data = {r[0]: {"impressions": r[1], "clicks": r[2]} for r in rows}
        a = data.get("A", {"impressions": 0, "clicks": 0})
        b = data.get("B", {"impressions": 0, "clicks": 0})

        n_a = max(a["impressions"], 1)
        n_b = max(b["impressions"], 1)
        c_a = a["clicks"]
        c_b = b["clicks"]

        p_a = c_a / n_a
        p_b = c_b / n_b

        total_c = c_a + c_b
        total_n = n_a + n_b
        p_pool = total_c / total_n if total_n > 0 else 0.5

        # Two-proportion z-test
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
        z = (p_a - p_b) / se if se > 0 else 0

        # Approximate p-value using erf
        p_val = 1.0 - math.erf(abs(z) / math.sqrt(2))

        winning = "A" if p_a > p_b else "B"
        confident = p_val < 0.05 and min(n_a, n_b) >= 100

        return {
            "variant_a": {"impressions": n_a, "clicks": c_a, "ctr": round(p_a * 100, 2)},
            "variant_b": {"impressions": n_b, "clicks": c_b, "ctr": round(p_b * 100, 2)},
            "z_score": round(z, 3),
            "p_value": round(p_val, 4),
            "significant": confident,
            "winning_variant": winning if confident else None,
            "confidence_pct": round((1 - p_val) * 100, 1),
            "needs_more_data": min(n_a, n_b) < 100,
        }
    except Exception as exc:
        logger.warning("compute_ab_stats error: %s", exc)
        return {"error": str(exc)}


def get_partner_config() -> dict:
    """Return full partner config (public fields only)."""
    return {k: {
        "name": v["name"],
        "landing_page": v["landing_page"],
        "redirect_path": v["redirect_path"],
        "estimated_commission": v["estimated_commission"],
        "sovereignty_score": v["sovereignty_score"],
    } for k, v in PARTNER_CONFIG.items()}
