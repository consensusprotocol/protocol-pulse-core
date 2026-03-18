#!/usr/bin/env python3
"""
spaces_pipeline.py — Bridge between x_spaces_scraper and assembler_v2.

Reads transcript cache from x_spaces_scraper/cache/ and returns
formatted segment data for video injection.

V3: Strict transcript truth — only audio_replay/live_capture sources.
context_only rejected entirely at this bridge level.
"""
import json
import logging
import os
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "x_spaces_scraper" / "cache"


def score_transcript(transcript: dict) -> int:
    """
    Score 0-100 for video injection priority.
    - Controversy/named entity keywords: +25
    - Data/metrics (numbers, %): +20
    - Named entity + prediction language: +20
    - Breaking/urgent reference: +10
    - Length bonus: 150-300w +5, 300-600w +10, 600w+ +15
    Max: 100
    """
    text = transcript.get("transcript", transcript.get("text", "")).lower()
    score = 0

    # Controversy / named entity keywords
    controversy_kws = [
        "saylor", "blackrock", "sec", "gensler", "etf", "ban", "regulation",
        "institutional", "congress", "fed", "powell", "inflation", "hack",
        "exploit", "lawsuit", "fraud", "arrest",
    ]
    if any(kw in text for kw in controversy_kws):
        score += 25

    # Data / metrics (numbers, %)
    if re.search(r'\d+\.?\d*\s*%', text) or re.search(r'\$\d+', text) or re.search(r'\d{4,}', text):
        score += 20

    # Named entity + prediction language
    prediction_kws = ["predict", "forecast", "expect", "will reach", "target", "by 20"]
    entity_kws = ["bitcoin", "btc", "lightning", "mining", "hashrate"]
    has_prediction = any(kw in text for kw in prediction_kws)
    has_entity = any(kw in text for kw in entity_kws)
    if has_prediction and has_entity:
        score += 20

    # Breaking / urgent
    if "breaking" in text or "urgent" in text or "just announced" in text:
        score += 10

    # Length bonus
    wc = len(text.split())
    if wc >= 600:
        score += 15
    elif wc >= 300:
        score += 10
    elif wc >= 150:
        score += 5

    return min(score, 100)


def get_latest_spaces_segment(max_age_hours: float = 4.0):
    """
    Scan x_spaces_scraper/cache/ for the highest-quality usable transcript
    written within the last max_age_hours.

    Returns a dict compatible with assembler_v2 SegmentSpec, or None if nothing fresh.

    Rules:
    - Only return transcripts with usable=True AND source in (audio_replay, live_capture)
    - Reject context_only entirely (usable=False always in this bridge)
    - Reject transcripts older than max_age_hours
    - Return highest impact_score among candidates
    - If max_age_hours=0, always return None (used in tests)
    """
    if max_age_hours <= 0:
        return None

    if not CACHE_DIR.exists():
        return None

    best = None
    best_impact = -1
    now = time.time()
    max_age_s = max_age_hours * 3600

    for item in CACHE_DIR.glob("transcript_*.json"):
        try:
            mtime = item.stat().st_mtime
            age = now - mtime
            if age > max_age_s:
                continue

            data = json.loads(item.read_text())

            # Normalize old cache format
            if "text" in data and "transcript" not in data:
                data["transcript"] = data["text"]

            # Strict source truth: only audio_replay / live_capture
            source = data.get("source", "")
            if source not in ("audio_replay", "live_capture"):
                continue

            # Must be marked usable
            if not data.get("usable", False):
                continue

            impact = score_transcript(data)
            if impact > best_impact:
                best_impact = impact
                best = data
                best["_mtime"] = mtime
                best["_impact"] = impact
        except (json.JSONDecodeError, OSError):
            continue

    if best is None:
        return None

    # Build TTS text: first 500 words, cleaned
    transcript_text = best.get("transcript", best.get("text", ""))
    words = transcript_text.split()[:500]
    tts_text = " ".join(words)
    # Strip HTML tags and special chars
    tts_text = re.sub(r'<[^>]+>', '', tts_text)
    tts_text = re.sub(r'[^\w\s.,!?\'-]', '', tts_text)

    source = best.get("source", "unknown")
    is_context = source == "context_only"

    return {
        "segment_type": "x_spaces",
        "space_id": best.get("space_id", ""),
        "host": best.get("host", best.get("speaker", "unknown")),
        "title": best.get("title", best.get("space_title", "X Space")),
        "transcript": transcript_text[:2000],
        "source": source,
        "word_count": len(transcript_text.split()),
        "quality_score": best.get("quality_score", 0.0),
        "impact_score": best["_impact"],
        "speakers": best.get("speakers", []),
        "tts_text": tts_text,
        "eyebrow": "LIVE INTEL — CONTEXT ONLY" if is_context else "LIVE X SPACES SIGNAL",
        "cached_at": best["_mtime"],
    }


if __name__ == "__main__":
    seg = get_latest_spaces_segment()
    print("SPACES SEGMENT:", json.dumps(seg, indent=2) if seg else "None")
