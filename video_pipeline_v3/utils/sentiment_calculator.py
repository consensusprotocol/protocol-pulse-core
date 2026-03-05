#!/usr/bin/env python3
"""Sentiment Calculator — Compute composite sentiment from daily_signals.

Reads daily_signals.json, computes weighted average sentiment across topics,
and writes data/intelligence/sentiment.json per PULSE_TERMINAL_LAWS Section 3.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("sentiment_calculator")

BASE_DIR = Path(__file__).resolve().parent.parent
INTELLIGENCE_DIR = BASE_DIR / "data" / "intelligence"
SIGNALS_PATH = INTELLIGENCE_DIR / "daily_signals.json"
OUTPUT_PATH = INTELLIGENCE_DIR / "sentiment.json"

# Topic-to-category mapping for breakdown
INSTITUTIONAL_TOPICS = {"etf", "institutional"}
MINING_TOPICS = {"mining"}
RETAIL_TOPICS = {"price", "self-custody", "lightning"}

SENTIMENT_SCORES = {
    "very_bullish": 90,
    "bullish": 75,
    "neutral": 50,
    "bearish": 25,
    "very_bearish": 10,
}


def _sentiment_to_score(label: str) -> int:
    return SENTIMENT_SCORES.get(label.lower(), 50)


def _score_to_label(score: int) -> str:
    if score >= 80:
        return "very_bullish"
    if score >= 60:
        return "bullish"
    if score >= 40:
        return "neutral"
    if score >= 20:
        return "bearish"
    return "very_bearish"


def compute_sentiment() -> dict:
    """Compute composite sentiment from daily_signals.json."""
    if not SIGNALS_PATH.exists():
        logger.warning(f"daily_signals.json not found at {SIGNALS_PATH}")
        return {"error": "No signals data available"}

    with open(SIGNALS_PATH) as f:
        signals = json.load(f)

    topics = signals.get("topic_velocity", [])
    if not topics:
        return {"error": "No topic velocity data"}

    # Weighted average: weight by channels covering (more channels = more signal)
    total_weight = 0
    weighted_sum = 0
    inst_scores, inst_weight = 0, 0
    mining_scores, mining_weight = 0, 0
    retail_scores, retail_weight = 0, 0

    for t in topics:
        sentiment = t.get("sentiment", "neutral")
        score = _sentiment_to_score(sentiment)
        channels = max(t.get("channels", 1), 1)
        topic_name = t.get("topic", "").lower()

        weighted_sum += score * channels
        total_weight += channels

        if topic_name in INSTITUTIONAL_TOPICS:
            inst_scores += score * channels
            inst_weight += channels
        elif topic_name in MINING_TOPICS:
            mining_scores += score * channels
            mining_weight += channels
        elif topic_name in RETAIL_TOPICS:
            retail_scores += score * channels
            retail_weight += channels

    overall_score = round(weighted_sum / total_weight) if total_weight else 50
    overall_label = _score_to_label(overall_score)

    def _breakdown(scores, weight):
        if weight == 0:
            return {"score": 50, "label": "neutral", "driver": "insufficient data"}
        s = round(scores / weight)
        return {"score": s, "label": _score_to_label(s)}

    inst = _breakdown(inst_scores, inst_weight)
    mining = _breakdown(mining_scores, mining_weight)
    retail = _breakdown(retail_scores, retail_weight)

    # Find driver for each
    for t in topics:
        topic_name = t.get("topic", "").lower()
        if topic_name in INSTITUTIONAL_TOPICS and "driver" not in inst:
            inst["driver"] = f"{t.get('topic', '')} narrative"
        if topic_name in MINING_TOPICS and "driver" not in mining:
            mining["driver"] = f"{t.get('topic', '')} trend"
        if topic_name in RETAIL_TOPICS and "driver" not in retail:
            retail["driver"] = f"{t.get('topic', '')} activity"

    # Load previous for change calculation
    prev_score = None
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                prev = json.load(f)
            prev_score = prev.get("data", {}).get("overall", {}).get("score")
        except (json.JSONDecodeError, OSError):
            pass

    change_24h = f"{overall_score - prev_score:+d}" if prev_score is not None else "N/A"

    result = {
        "data": {
            "overall": {
                "score": overall_score,
                "label": overall_label,
                "change_24h": change_24h,
                "components": {
                    "youtube_sentiment": overall_score,
                    "topic_velocity_bullish_pct": round(
                        sum(1 for t in topics if t.get("sentiment") == "bullish") / max(len(topics), 1) * 100
                    ),
                },
            },
            "breakdown": {
                "institutional": inst,
                "retail": retail,
                "mining": mining,
            },
            "historical": [],  # Populated by accumulating daily results
        },
        "scan_time": signals.get("scan_time", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
    }

    # Accumulate historical
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                prev = json.load(f)
            hist = prev.get("data", {}).get("historical", [])
            # Keep last 90 days
            result["data"]["historical"] = hist[-89:] + [
                {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "score": overall_score}
            ]
        except (json.JSONDecodeError, OSError):
            result["data"]["historical"] = [
                {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "score": overall_score}
            ]

    # Write
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Sentiment written: overall={overall_score} ({overall_label}) -> {OUTPUT_PATH}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = compute_sentiment()
    print(json.dumps(result, indent=2))
