"""
Content Governor — Protocol Pulse article rotation system.
===========================================================
Enforces category diversity across every 6 articles generated.

SLOT CYCLE (repeats):
  0: bitcoin_news   — breaking RSS story, any topic
  1: mining_intel   — RSS filtered for mining/hashrate/difficulty
  2: market_macro   — RSS filtered for price/ETF/institutional/macro
  3: opinion        — intel_briefing.py editorial column
  4: regulation     — RSS filtered for regulation/policy/legal
  5: wildcard       — RSS story NOT in a capped category (broadens feed)

State persisted to: data/governor_state.json
"""

import json
import logging
import os
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

STATE_FILE = Path("/home/ultron/protocol_pulse/data/governor_state.json")

# --- Slot definitions -----------------------------------------------------------

SLOTS = [
    "bitcoin_news",   # 0
    "mining_intel",   # 1
    "market_macro",   # 2
    "opinion",        # 3
    "regulation",     # 4
    "wildcard",       # 5
]

SLOT_RSS_FILTERS: Dict[str, List[str]] = {
    "bitcoin_news":  [],   # no filter — any story
    "mining_intel":  ["mining", "miner", "hashrate", "hash rate", "difficulty", "asic", "energy"],
    "market_macro":  ["price", "etf", "blackrock", "fidelity", "institutional", "macro",
                      "fed", "inflation", "gold", "interest rate", "treasury", "saylor",
                      "microstrategy", "whale", "ath", "all-time high"],
    "regulation":    ["regulation", "sec", "congress", "senate", "law", "ban", "policy",
                      "mica", "hearing", "legislation", "cbdc", "legal", "court"],
    "wildcard":      [],   # open — exclude capped categories
    "opinion":       [],   # no RSS — handled by intel_briefing.py
}

# Category names to display in logs / article metadata
SLOT_CATEGORY: Dict[str, str] = {
    "bitcoin_news":  "Bitcoin",
    "mining_intel":  "Mining Intel",
    "market_macro":  "Markets",
    "opinion":       "opinion",
    "regulation":    "Regulation",
    "wildcard":      "Bitcoin",
}

# Keywords that make a story "capped" for wildcard selection
CAPPED_TOPICS_FOR_WILDCARD = [
    "mining", "hashrate", "hash rate", "difficulty",
    "regulation", "sec", "congress",
    "etf", "institutional", "price"
]

# --- State management -----------------------------------------------------------

def _load_state() -> Dict:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Governor state load failed: {e}")
    return {"slot_index": 0, "history": []}

def _save_state(state: Dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Governor state save failed: {e}")

def get_next_slot() -> str:
    """Return the slot type for the next article and advance the index."""
    state = _load_state()
    idx = state.get("slot_index", 0) % len(SLOTS)
    slot = SLOTS[idx]
    state["slot_index"] = (idx + 1) % len(SLOTS)
    _save_state(state)
    logger.info(f"[GOVERNOR] Slot {idx} → {slot}")
    return slot

def peek_current_slot() -> str:
    """Return the current slot without advancing."""
    state = _load_state()
    return SLOTS[state.get("slot_index", 0) % len(SLOTS)]

def record_published(slot: str, title: str, article_id: int) -> None:
    """Record a successfully published article in governor history."""
    state = _load_state()
    history = state.get("history", [])
    history.append({
        "slot": slot,
        "title": title,
        "article_id": article_id,
        "published_at": datetime.utcnow().isoformat(),
    })
    # Keep last 50 records
    state["history"] = history[-50:]
    _save_state(state)

def get_recent_history(hours: int = 24) -> List[Dict]:
    state = _load_state()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    return [
        r for r in state.get("history", [])
        if datetime.fromisoformat(r["published_at"]) > cutoff
    ]

# --- RSS source filtering -------------------------------------------------------

def _title_matches_filter(title: str, keywords: List[str]) -> bool:
    tl = title.lower()
    return any(kw in tl for kw in keywords)

def _title_is_capped(title: str) -> bool:
    return _title_matches_filter(title, CAPPED_TOPICS_FOR_WILDCARD)

def fetch_rss_for_slot(slot: str, limit: int = 20) -> List[Dict]:
    """Fetch RSS items, filtered by slot category keywords."""
    try:
        import feedparser
        from services.article_automation import NEWS_FEEDS
    except ImportError:
        NEWS_FEEDS = [
            "https://bitcoinmagazine.com/.rss/full/",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cointelegraph.com/rss",
            "https://decrypt.co/feed",
            "https://www.theblock.co/rss.xml",
        ]
        try:
            import feedparser
        except ImportError:
            logger.error("feedparser not installed")
            return []

    keywords = SLOT_RSS_FILTERS.get(slot, [])
    items = []

    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", ""))[:1000]
                if not title or not url:
                    continue
                # Apply slot filter
                if keywords and not _title_matches_filter(title, keywords):
                    continue
                # For wildcard: skip capped topics
                if slot == "wildcard" and _title_is_capped(title):
                    continue
                items.append({
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "source": feed_url.split("/")[2],
                    "type": "rss",
                    "priority": 1,
                    "slot": slot,
                    "category": SLOT_CATEGORY.get(slot, "Bitcoin"),
                })
        except Exception as e:
            logger.warning(f"RSS fetch failed for {feed_url}: {e}")

    # Shuffle to avoid always picking same feed's top story
    random.shuffle(items)
    return items[:limit]

def select_source_for_slot(slot: str) -> Optional[Dict]:
    """
    Select the best unused source for a given slot.
    Returns None for 'opinion' slot (handled by intel_briefing.py).
    """
    if slot == "opinion":
        return None  # Caller handles this

    items = fetch_rss_for_slot(slot)
    if not items:
        logger.warning(f"[GOVERNOR] No RSS items for slot '{slot}', falling back to bitcoin_news")
        items = fetch_rss_for_slot("bitcoin_news")

    if not items:
        return None

    # Load used URLs to avoid repeats
    used_path = Path("/home/ultron/protocol_pulse/data/used_article_urls.json")
    try:
        used_urls = set(json.loads(used_path.read_text())) if used_path.exists() else set()
    except Exception:
        used_urls = set()

    # Pick first unused item
    for item in items:
        if item["url"] not in used_urls:
            # Mark as used
            used_urls.add(item["url"])
            try:
                used_path.parent.mkdir(parents=True, exist_ok=True)
                used_path.write_text(json.dumps(list(used_urls)[-500:]))  # keep last 500
            except Exception:
                pass
            return item

    # All used — return first anyway (better than nothing)
    logger.warning(f"[GOVERNOR] All RSS items for slot '{slot}' already used, recycling")
    return items[0] if items else None

# --- Main entry point -----------------------------------------------------------

def get_next_assignment() -> Tuple[str, Optional[Dict]]:
    """
    Returns (slot_name, source_dict_or_None).
    For 'opinion' slot, source is None — caller uses intel_briefing.py.
    For all other slots, source is a dict with title/url/summary/category.
    """
    slot = get_next_slot()
    source = select_source_for_slot(slot)
    return slot, source

def get_status() -> Dict:
    """Return current governor status for admin/health endpoints."""
    state = _load_state()
    history = get_recent_history(hours=24)
    slot_counts = {}
    for r in history:
        slot_counts[r["slot"]] = slot_counts.get(r["slot"], 0) + 1
    return {
        "next_slot": SLOTS[state.get("slot_index", 0) % len(SLOTS)],
        "slot_index": state.get("slot_index", 0),
        "published_last_24h": len(history),
        "slot_breakdown_24h": slot_counts,
        "last_published": history[-1] if history else None,
    }
