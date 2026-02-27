"""
Story-Level Dedup — catches same story told with different headlines.
Uses GPT-4o-mini (~$0.0004/check) + category rotation + keyword count.

Three layers:
1. is_same_story_gpt() — LLM semantic check (48h window, 50 titles)
2. enforce_category_rotation() — keyword category cap (last 8 articles)
3. count_similar_titles() — fast 3+ shared-word count (pre-check)

Main entry point: is_topic_oversaturated_v2(title)
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger("article_automation")

CATEGORIES = {
    "mining": ["mining", "miner", "hashrate", "hash rate", "difficulty", "asic"],
    "price": ["price", "rally", "crash", "correction", "bull", "bear", "ath"],
    "etf": ["etf", "blackrock", "fidelity", "grayscale", "ishares"],
    "regulation": ["regulation", "sec", "congress", "law", "ban", "mica", "policy"],
    "network": ["network", "node", "mempool", "fee", "resilience"],
    "institutional": ["institution", "wall street", "fund", "bank", "treasury",
                      "microstrategy", "saylor", "corporate"],
    "lightning": ["lightning", "layer 2", "l2"],
    "privacy": ["privacy", "surveillance", "kyc", "aml", "wasabi"],
    "energy": ["energy", "power", "grid", "renewable"],
    "geopolitics": ["china", "russia", "el salvador", "brics", "tariff", "reserve"],
    "gold_macro": ["gold", "fed", "interest rate", "inflation", "macro", "dollar"],
}

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
    "to", "for", "of", "and", "or", "but", "as", "by", "with", "its",
})


def _get_recent_headlines(hours=48, limit=50):
    """Fetch recent article titles from DB (48h window, 50 titles by default)."""
    try:
        import models
        from app import db
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = (
            models.Article.query
            .filter(models.Article.created_at >= cutoff)
            .order_by(models.Article.created_at.desc())
            .limit(limit)
            .all()
        )
        return [a.title for a in recent if a.title]
    except Exception as e:
        logger.warning(f"Failed to fetch recent headlines: {e}")
        return []


def _detect_category(title):
    """Detect primary category of an article from its title."""
    tl = title.lower()
    scores = {}
    for cat, kws in CATEGORIES.items():
        s = sum(1 for kw in kws if kw in tl)
        if s > 0:
            scores[cat] = s
    return max(scores, key=scores.get) if scores else "general"


# ----------------------------------------------------------------
# Layer 1: GPT-4o-mini semantic check
# ----------------------------------------------------------------
def is_same_story_gpt(candidate_title, recent_headlines=None, hours=48):
    """Use GPT-4o-mini to check if candidate covers the same event as any recent headline."""
    if recent_headlines is None:
        recent_headlines = _get_recent_headlines(hours=hours, limit=50)
    if not recent_headlines:
        return False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        headlines_text = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(recent_headlines))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""News editor duplicate check.

CANDIDATE:
  "{candidate_title}"

ALREADY PUBLISHED (last {hours}h):
{headlines_text}

Does CANDIDATE cover the SAME underlying news event/story as ANY published headline?
"Same story" = same event, data point, or development, even if phrased differently.

SAME examples:
- "Hashrate Drops 15%" and "Mining Exodus as Network Sheds Hashrate" = SAME
- "Saylor Buys Bitcoin" and "MicroStrategy's Bold Buying Spree" = SAME

DIFFERENT examples:
- "Hashrate Drops 15%" and "Lightning Hits New Milestone" = DIFFERENT

Reply ONLY: SAME or DIFFERENT"""
            }],
            max_tokens=5,
            temperature=0
        )
        answer = resp.choices[0].message.content.strip().upper()
        is_same = "SAME" in answer
        if is_same:
            logger.info(f"STORY DEDUP: Blocking '{candidate_title[:70]}' — same story already covered")
        return is_same
    except Exception as e:
        logger.warning(f"GPT story dedup failed (allowing): {e}")
        return False


# Alias used by article_automation imports
is_semantic_duplicate = is_same_story_gpt


# ----------------------------------------------------------------
# Layer 2: Category rotation
# ----------------------------------------------------------------
def enforce_category_rotation(candidate_title, max_same=2, lookback=8):
    """Block if the same category already has max_same articles in recent lookback."""
    try:
        import models
        recent = models.Article.query.order_by(models.Article.created_at.desc()).limit(lookback).all()
        candidate_cat = _detect_category(candidate_title)
        if candidate_cat == "general":
            return False
        same_count = sum(1 for a in recent if _detect_category(a.title) == candidate_cat)
        if same_count >= max_same:
            logger.info(
                f"CATEGORY ROTATION: Skipping '{candidate_title[:60]}' — "
                f"'{candidate_cat}' has {same_count}/{lookback} recent"
            )
            return True
        return False
    except Exception as e:
        logger.warning(f"Category rotation check failed: {e}")
        return False


# ----------------------------------------------------------------
# Layer 3: Fast keyword overlap count
# ----------------------------------------------------------------
def count_similar_titles(proposed_title, hours=24):
    """Quick count of recent titles sharing 3+ content words with proposed title."""
    recent = _get_recent_headlines(hours=hours, limit=100)
    if not recent:
        return 0

    proposed_words = set(proposed_title.lower().split()) - _STOPWORDS
    count = 0
    for title in recent:
        title_words = set(title.lower().split()) - _STOPWORDS
        if len(proposed_words & title_words) >= 3:
            count += 1
    return count


# ----------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------
def is_topic_oversaturated_v2(title, max_same=1, hours=24):
    """Combined dedup: keyword count + GPT semantic + category rotation."""
    # Fast pre-check: if 3+ similar titles already, very likely duplicate
    similar = count_similar_titles(title, hours=hours)
    if similar >= 3:
        logger.info(
            f"KEYWORD DEDUP: Blocking '{title[:60]}' — {similar} similar titles in {hours}h"
        )
        return True
    # GPT semantic check (wider window)
    if is_same_story_gpt(title, hours=48):
        return True
    # Category rotation
    if enforce_category_rotation(title, max_same=2, lookback=8):
        return True
    return False
