#!/usr/bin/env python3
"""Engagement Scorer — editorial intelligence layer for clip selection.

Reads real audience engagement data (tweet_study, engagement_log, sentiment_posts,
episode_memory) and produces weighted scores for channels, topics, and X handles.

Scores feed into clip_scorer.py (channel multiplier) and script_writer.py (trending
topics context). Weights are persisted to data/engagement_weights.json.

Graceful fallback: if engagement data is sparse, uses editorial hierarchy defaults.
"""
import json
import logging
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)

ENGAGEMENT_LOG = os.path.join(BASE, "engagement_log.json")
SENTIMENT_POSTS = os.path.join(BASE, "sentiment_posts.json")
RAW_TWEETS = os.path.join(BASE, "tweet_study", "raw_tweets.json")
EPISODE_MEMORY = os.path.join(BASE, "episode_memory.json")
WEIGHTS_FILE = os.path.join(BASE, "engagement_weights.json")

logger = logging.getLogger("EngagementScorer")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[engagement] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ── Editorial Hierarchy Defaults ─────────────────────────────────────────────
# Used as fallback when real engagement data is sparse.
# Scale 0-10. Based on known Bitcoin community editorial influence.
DEFAULT_CHANNEL_SCORES = {
    "Preston Pysh": 8.8,
    "Lyn Alden": 8.5,
    "Robert Breedlove": 8.0,
    "TFTC": 7.8,
    "Simply Bitcoin": 7.6,
    "Bitcoin Magazine": 7.4,
    "Blockworks": 7.0,
    "What Bitcoin Did": 7.2,
    "Swan Bitcoin": 6.8,
    "Bitcoin Audible": 7.0,
    "Coin Bureau": 6.5,
    "The Bitcoin Layer": 7.3,
}

DEFAULT_HANDLE_SCORES = {
    "@PrestonPysh": 8.8,
    "@LynAldenContact": 8.5,
    "@Breedlove22": 8.0,
    "@MartyBent": 7.8,
    "@saylor": 9.0,
    "@gladstein": 7.5,
    "@CryptoHayes": 7.3,
    "@ErikVoorhees": 7.0,
    "@WClementeIII": 7.2,
    "@nic__carter": 7.5,
    "@adam3us": 7.8,
    "@APompliano": 6.5,
    "@maxkeiser": 6.8,
    "@PeterMcCormack": 6.5,
    "@NickSzabo4": 8.0,
}

DEFAULT_TOPIC_SCORES = {
    "halving": 8.0,
    "ETF": 7.5,
    "sovereignty": 7.0,
    "mining": 6.5,
    "self-custody": 7.2,
    "lightning": 6.0,
    "regulation": 6.8,
    "institutional": 7.0,
    "macro": 7.3,
    "hash rate": 6.5,
}

# Minimum data thresholds before trusting real data over defaults
MIN_TWEETS_FOR_HANDLE_SCORE = 3
MIN_EPISODES_FOR_CHANNEL_SCORE = 2


def _load_json(path: str) -> dict | list | None:
    """Load a JSON file, return None on failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"Could not load {path}: {e}")
        return None


def _load_engagement_log() -> list:
    """Load engagement_log.json posts array."""
    data = _load_json(ENGAGEMENT_LOG)
    if isinstance(data, dict):
        return data.get("posts", [])
    if isinstance(data, list):
        return data
    return []


def _load_sentiment_posts() -> list:
    """Load sentiment_posts.json posts array."""
    data = _load_json(SENTIMENT_POSTS)
    if isinstance(data, dict):
        return data.get("posts", [])
    if isinstance(data, list):
        return data
    return []


def _load_raw_tweets() -> list:
    """Load tweet_study raw_tweets.json."""
    data = _load_json(RAW_TWEETS)
    if isinstance(data, list):
        return data
    return []


def _load_episode_memory() -> list:
    """Load episode_memory.json episodes."""
    data = _load_json(EPISODE_MEMORY)
    if isinstance(data, dict):
        return data.get("episodes", [])
    if isinstance(data, list):
        return data
    return []


# ── Channel name ↔ handle mapping ────────────────────────────────────────────
CHANNEL_HANDLE_MAP = {
    "saylor": "Bitcoin Magazine",
    "PrestonPysh": "Preston Pysh",
    "LynAldenContact": "Lyn Alden",
    "Breedlove22": "Robert Breedlove",
    "MartyBent": "TFTC",
    "gladstein": "Human Rights Foundation",
    "CryptoHayes": "BitMEX",
    "ErikVoorhees": "ShapeShift",
    "WClementeIII": "Reflexivity Research",
    "nic__carter": "Castle Island Ventures",
    "adam3us": "Blockstream",
    "APompliano": "Pomp Investments",
    "maxkeiser": "Max Keiser",
    "PeterMcCormack": "What Bitcoin Did",
    "NickSzabo4": "Nick Szabo",
    "americanhodl": "American HODL",
    "daborosgrams": "Simply Bitcoin",
}


# ── Scoring Functions ─────────────────────────────────────────────────────────

def score_channel(channel_name: str) -> float:
    """Score a YouTube channel 0-10 based on audience engagement history.

    Combines:
    - Episode memory Gemini grades (if available)
    - Tweet engagement when the channel is mentioned
    - Editorial hierarchy default as baseline
    """
    # Start with default
    default = DEFAULT_CHANNEL_SCORES.get(channel_name, 5.0)

    # Factor 1: Episode memory — Gemini grades for episodes featuring this channel
    episodes = _load_episode_memory()
    channel_scores = []
    for ep in episodes:
        for clip in ep.get("clips", []):
            if clip.get("channel", "").lower() == channel_name.lower():
                channel_scores.append(ep.get("overall_score", 0))

    # Factor 2: Tweet mentions — engagement when our content mentions this channel
    tweets = _load_raw_tweets()
    mention_engagement = []
    name_lower = channel_name.lower()
    for tw in tweets:
        text = tw.get("text", "").lower()
        if name_lower in text:
            mention_engagement.append(tw.get("engagement_rate", 0))

    # Combine
    if len(channel_scores) >= MIN_EPISODES_FOR_CHANNEL_SCORE:
        # Enough episode data — weight it heavily
        ep_avg = sum(channel_scores) / len(channel_scores)
        ep_score = min(10.0, ep_avg)  # Gemini scores are 0-10
        score = ep_score * 0.6 + default * 0.4
    elif mention_engagement:
        # Some tweet data — use it with default blend
        avg_eng = sum(mention_engagement) / len(mention_engagement)
        # Normalize engagement rate to 0-10 scale (typical rates are 0.0001 to 0.01)
        eng_score = min(10.0, avg_eng * 1000)
        score = eng_score * 0.4 + default * 0.6
    else:
        # Pure default
        score = default

    return round(score, 1)


def score_topic(topic_keywords: list) -> float:
    """Score a topic 0-10 based on recent engagement spikes.

    Scans tweet_study and sentiment_posts for keyword frequency and
    engagement rates when those keywords appear.
    """
    if not topic_keywords:
        return 5.0

    tweets = _load_raw_tweets()
    sentiment_posts = _load_sentiment_posts()
    engagement_posts = _load_engagement_log()

    keywords_lower = [kw.lower() for kw in topic_keywords]
    topic_key = topic_keywords[0].lower()

    # Default score
    default = DEFAULT_TOPIC_SCORES.get(topic_key, 5.0)

    # Scan tweets for keyword engagement
    matching_rates = []
    for tw in tweets:
        text = tw.get("text", "").lower()
        if any(kw in text for kw in keywords_lower):
            matching_rates.append(tw.get("engagement_rate", 0))

    # Scan sentiment_posts
    sentiment_matches = 0
    for post in sentiment_posts:
        text = post.get("text", "").lower()
        if any(kw in text for kw in keywords_lower):
            sentiment_matches += 1

    # Scan engagement_log
    engagement_matches = 0
    for post in engagement_posts:
        text = post.get("text", "").lower()
        if any(kw in text for kw in keywords_lower):
            engagement_matches += 1

    if not matching_rates:
        return default

    avg_rate = sum(matching_rates) / len(matching_rates)
    # Normalize: typical engagement_rate range 0.0001-0.01 → 0-10
    raw_score = min(10.0, avg_rate * 1000)

    # Velocity bonus: more mentions = higher velocity
    volume_bonus = min(2.0, len(matching_rates) / 20)

    # Blend with default
    score = raw_score * 0.5 + default * 0.3 + volume_bonus * 0.2 * 10
    return round(min(10.0, score), 1)


def score_handle(x_handle: str) -> float:
    """Score an X handle 0-10 by historical engagement when quoted/mentioned.

    Args:
        x_handle: Twitter handle with or without @ prefix.
    """
    handle = x_handle.lstrip("@")
    handle_lower = handle.lower()
    at_handle = f"@{handle}"

    default = DEFAULT_HANDLE_SCORES.get(at_handle, 5.0)
    # Also check without @
    if default == 5.0:
        for k, v in DEFAULT_HANDLE_SCORES.items():
            if k.lstrip("@").lower() == handle_lower:
                default = v
                break

    tweets = _load_raw_tweets()

    # Find tweets BY this handle
    handle_tweets = [tw for tw in tweets if tw.get("handle", "").lower() == handle_lower]

    if len(handle_tweets) < MIN_TWEETS_FOR_HANDLE_SCORE:
        return default

    avg_rate = sum(tw.get("engagement_rate", 0) for tw in handle_tweets) / len(handle_tweets)
    # Normalize to 0-10
    raw_score = min(10.0, avg_rate * 1000)

    # Best tweet bonus
    best_rate = max(tw.get("engagement_rate", 0) for tw in handle_tweets)
    best_bonus = min(2.0, best_rate * 200)

    score = raw_score * 0.5 + default * 0.3 + best_bonus
    return round(min(10.0, score), 1)


def get_top_channels(n: int = 10) -> list:
    """Return top N channels sorted by engagement score.

    Returns list of (channel_name, score) tuples.
    """
    # Score all known channels
    all_channels = set(DEFAULT_CHANNEL_SCORES.keys())

    # Add channels from episode memory
    episodes = _load_episode_memory()
    for ep in episodes:
        for clip in ep.get("clips", []):
            ch = clip.get("channel")
            if ch:
                all_channels.add(ch)

    scored = [(ch, score_channel(ch)) for ch in all_channels]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]


def get_trending_topics() -> list:
    """Return topics sorted by recent engagement velocity.

    Scans all data sources for topic keywords and ranks by frequency × engagement.
    Returns list of (topic, score) tuples.
    """
    # Combine all text sources
    tweets = _load_raw_tweets()
    sentiment_posts = _load_sentiment_posts()
    engagement_posts = _load_engagement_log()

    # Bitcoin-relevant topic keywords to scan for
    TOPIC_KEYWORDS = {
        "halving": ["halving", "halvening", "block reward", "subsidy"],
        "ETF": ["etf", "spot etf", "bitcoin etf", "ishares", "blackrock etf"],
        "sovereignty": ["sovereignty", "sovereign", "self-sovereign", "censorship resistance"],
        "mining": ["mining", "miner", "hash rate", "hashrate", "asic"],
        "self-custody": ["self-custody", "self custody", "cold storage", "hardware wallet", "not your keys"],
        "lightning": ["lightning", "lightning network", "ln", "bolt"],
        "regulation": ["regulation", "sec", "congress", "legislation", "compliance"],
        "institutional": ["institutional", "wall street", "pension", "endowment", "sovereign wealth"],
        "macro": ["macro", "inflation", "fed", "interest rate", "monetary policy", "treasury"],
        "stacking": ["stacking", "dca", "dollar cost", "accumulation"],
        "privacy": ["privacy", "coinjoin", "mixer", "payjoin"],
        "layer 2": ["layer 2", "l2", "sidechain", "liquid", "fedimint"],
        "adoption": ["adoption", "merchant", "payment", "el salvador", "legal tender"],
        "on-chain": ["on-chain", "utxo", "mempool", "fees", "block space"],
    }

    topic_scores = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        topic_scores[topic] = score_topic(keywords)

    ranked = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


def build_weights() -> dict:
    """Build full engagement weights dict. Saved to data/engagement_weights.json.

    Returns:
        Dict with channels, topics, handles, and metadata.
    """
    logger.info("Building engagement weights...")

    # Channels
    top_channels = get_top_channels(20)
    channels_dict = {ch: score for ch, score in top_channels}

    # Topics
    trending = get_trending_topics()
    topics_dict = {topic: score for topic, score in trending}

    # Handles
    handles_dict = {}
    for handle in DEFAULT_HANDLE_SCORES:
        handles_dict[handle] = score_handle(handle)

    # Also score handles from raw tweets
    tweets = _load_raw_tweets()
    seen_handles = set()
    for tw in tweets:
        h = tw.get("handle", "")
        if h and f"@{h}" not in handles_dict:
            seen_handles.add(h)
    for h in seen_handles:
        handles_dict[f"@{h}"] = score_handle(h)

    weights = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "channels": channels_dict,
        "topics": topics_dict,
        "handles": handles_dict,
    }

    logger.info(f"Weights built: {len(channels_dict)} channels, "
                f"{len(topics_dict)} topics, {len(handles_dict)} handles")
    return weights


def refresh_weights() -> dict:
    """Run build_weights() and save to disk. Called by cron weekly."""
    weights = build_weights()
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, indent=2)
    logger.info(f"Weights saved to {WEIGHTS_FILE}")
    return weights


def load_weights() -> dict:
    """Load cached weights from disk. Returns empty dict if not found."""
    data = _load_json(WEIGHTS_FILE)
    return data if isinstance(data, dict) else {}


def get_channel_engagement_multiplier(channel_name: str) -> float:
    """Get engagement multiplier for clip scoring (0.5-1.5 range).

    Used by clip_scorer.py to boost/penalize clips from channels based on
    historical audience engagement.
    """
    score = score_channel(channel_name)
    # Map 0-10 score to 0.5-1.5 multiplier (5.0 = neutral 1.0)
    multiplier = 0.5 + (score / 10.0)
    return round(multiplier, 2)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    weights = refresh_weights()

    print("\n" + "=" * 60)
    print("ENGAGEMENT WEIGHTS GENERATED")
    print("=" * 60)

    print("\nTop 10 Channels by Engagement:")
    for ch, score in sorted(weights["channels"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {ch:30s} {score:.1f}/10")

    print("\nTop 10 Trending Topics:")
    for topic, score in sorted(weights["topics"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {topic:30s} {score:.1f}/10")

    print("\nTop 10 Handles by Engagement:")
    for handle, score in sorted(weights["handles"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {handle:30s} {score:.1f}/10")

    print(f"\nWeights saved to: {WEIGHTS_FILE}")
    print(f"Updated: {weights['updated']}")
    print("=" * 60)
