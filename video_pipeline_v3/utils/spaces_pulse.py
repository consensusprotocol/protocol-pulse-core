#!/usr/bin/env python3
"""Live Spaces Pulse — Phase 1: Impact scoring + quote tweet drafting.

Processes 30-second transcript chunks from X Spaces, scores them for impact,
drafts quote tweets for high-impact moments, and stores results for review.

Per LIVE_SPACES_PULSE_LAWS.md Section 1 (Impact Scoring) and Section 2 (Use Case 1).
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPACES_DATA_DIR = os.path.join(BASE, "data", "spaces")

# ──────────────────────────────────────────────────────────────
# Impact Scoring
# ──────────────────────────────────────────────────────────────

CONTROVERSY_WORDS = [
    "capitulate", "capitulation", "collapse", "crash", "scam", "fraud",
    "ponzi", "wrong", "disagree", "terrible", "disaster", "insane",
    "ridiculous", "dangerous", "reckless", "manipulation", "corrupt",
    "attack", "war", "ban", "dead", "dying", "never", "impossible",
    "catastrophe", "bubble", "overvalued", "undervalued", "delusional",
]

DATA_METRICS_RE = re.compile(
    r'\b(\d+[\.,]?\d*)\s*(%|percent|billion|million|trillion|thousand|x|bps|basis points'
    r'|dollars?|btc|sats?|hashrate|exahash|terahash|TH/s|EH/s)\b',
    re.IGNORECASE
)

NAMED_ENTITIES = [
    "saylor", "blackrock", "fidelity", "sec", "gensler", "powell",
    "trump", "biden", "warren", "microstrategy", "grayscale", "coinbase",
    "binance", "tether", "fed", "congress", "etf", "ibit", "fbtc",
    "el salvador", "bukele", "dorsey", "elon", "vitalik",
]

PREDICTION_WORDS = [
    "will", "going to", "predict", "expect", "bet", "believe",
    "think", "forecast", "projection", "target", "by 2025", "by 2026",
    "by 2027", "by 2030", "next year", "end of year",
]

BREAKING_WORDS = [
    "just happened", "breaking", "just announced", "confirmed",
    "leaked", "exclusive", "first time", "unprecedented", "just now",
]


def score_chunk(text: str) -> int:
    """Score a transcript chunk 0-100 for impact.

    Points:
    - Controversy words: +25
    - Data/metrics regex: +20
    - Named entity + prediction: +20
    - Breaking reference: +10
    - Length bonus: +5/+10/+15
    """
    score = 0
    text_lower = text.lower()

    # Controversy: +25 if any controversy word present
    if any(w in text_lower for w in CONTROVERSY_WORDS):
        score += 25

    # Data/metrics: +20 if numbers with units detected
    if DATA_METRICS_RE.search(text):
        score += 20

    # Named entity + prediction combo: +20
    has_entity = any(e in text_lower for e in NAMED_ENTITIES)
    has_prediction = any(p in text_lower for p in PREDICTION_WORDS)
    if has_entity and has_prediction:
        score += 20

    # Breaking reference: +10
    if any(b in text_lower for b in BREAKING_WORDS):
        score += 10

    # Length bonus (longer chunks tend to have more substance)
    word_count = len(text.split())
    if word_count >= 80:
        score += 15
    elif word_count >= 50:
        score += 10
    elif word_count >= 30:
        score += 5

    return min(score, 100)


# ──────────────────────────────────────────────────────────────
# Quote Tweet Drafting
# ──────────────────────────────────────────────────────────────

def draft_quote_tweet(chunk: str, handle: str, space_url: str, context: str = '') -> str:
    """Draft a quote tweet for a high-impact Space moment. Max 280 chars.

    Format:
      "[quote max 200 chars]"
      -- @handle, LIVE right now
      [context]
      [space_url]
    """
    # Trim chunk to fit as quote (max 200 chars)
    quote = chunk.strip()
    if len(quote) > 200:
        quote = quote[:197] + "..."

    # Build tweet parts
    parts = [f'"{quote}"']
    parts.append(f"\n\u2014 @{handle}, LIVE right now")
    if context:
        parts.append(f"\n{context}")
    parts.append(f"\n{space_url}")

    tweet = "".join(parts)

    # Enforce 280 char limit by trimming context first, then quote
    if len(tweet) > 280 and context:
        tweet = f'"{quote}"\n\u2014 @{handle}, LIVE right now\n{space_url}'
    if len(tweet) > 280:
        available = 280 - len(f'""\n\u2014 @{handle}, LIVE right now\n{space_url}')
        quote = quote[:available - 3] + "..."
        tweet = f'"{quote}"\n\u2014 @{handle}, LIVE right now\n{space_url}'

    return tweet


# ──────────────────────────────────────────────────────────────
# Chunk Processing Pipeline
# ──────────────────────────────────────────────────────────────

def process_spaces_chunk(
    space_id: str,
    chunk_text: str,
    speaker_handle: str,
    space_url: str,
    chunk_index: int,
) -> Optional[dict]:
    """Process a single transcript chunk from a Space.

    Scores it, drafts a tweet if >= 60, saves to data/spaces/{space_id}/chunks.jsonl.
    Returns result dict or None if below threshold.
    """
    impact_score = score_chunk(chunk_text)

    result = {
        "space_id": space_id,
        "chunk_index": chunk_index,
        "speaker": speaker_handle,
        "text": chunk_text,
        "impact_score": impact_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "approved": False,
    }

    if impact_score >= 60:
        result["tweet_draft"] = draft_quote_tweet(chunk_text, speaker_handle, space_url)

    # Save to chunks.jsonl
    space_dir = os.path.join(SPACES_DATA_DIR, space_id)
    os.makedirs(space_dir, exist_ok=True)
    chunks_file = os.path.join(space_dir, "chunks.jsonl")
    with open(chunks_file, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result if impact_score >= 60 else None


# ──────────────────────────────────────────────────────────────
# Pending Drafts Scanner
# ──────────────────────────────────────────────────────────────

def get_all_pending_drafts() -> list:
    """Scan all chunks.jsonl files, return unapproved high-impact drafts sorted by score desc."""
    drafts = []

    if not os.path.exists(SPACES_DATA_DIR):
        return drafts

    for space_id in os.listdir(SPACES_DATA_DIR):
        chunks_file = os.path.join(SPACES_DATA_DIR, space_id, "chunks.jsonl")
        if not os.path.exists(chunks_file):
            continue
        with open(chunks_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("tweet_draft") and not entry.get("approved"):
                    drafts.append(entry)

    drafts.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
    return drafts


# ──────────────────────────────────────────────────────────────
# Main test block
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test: Saylor prediction quote should score >= 60
    test_chunk = (
        "I think Bitcoin will hit 500 thousand dollars by 2030. "
        "MicroStrategy is going to keep buying. Saylor just confirmed "
        "another 10 billion dollar purchase. This is unprecedented for "
        "any corporate treasury strategy. The math doesn't lie — at this "
        "rate of accumulation, institutional demand will completely overwhelm "
        "the available supply within 18 months."
    )

    score = score_chunk(test_chunk)
    print(f"Impact score: {score}")
    assert score >= 60, f"Expected score >= 60, got {score}"

    tweet = draft_quote_tweet(
        test_chunk,
        "saylor",
        "https://twitter.com/i/spaces/test123",
        "MicroStrategy holds 500K+ BTC."
    )
    print(f"\nTweet draft ({len(tweet)} chars):")
    print(tweet)
    assert len(tweet) <= 280, f"Tweet too long: {len(tweet)} chars"

    # Test process_spaces_chunk
    result = process_spaces_chunk(
        "test_space_001", test_chunk, "saylor",
        "https://twitter.com/i/spaces/test123", 0
    )
    assert result is not None, "Expected high-impact result, got None"
    print(f"\nProcess result: score={result['impact_score']}, has_draft={bool(result.get('tweet_draft'))}")

    # Test pending drafts
    pending = get_all_pending_drafts()
    print(f"Pending drafts: {len(pending)}")

    print("\nAll tests passed.")
