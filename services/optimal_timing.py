"""
OPTIMAL TIMING — Post when Bitcoin Twitter is most active.
==========================================================
Peak hours for Bitcoin content (all UTC):
- 13:00-15:00 (US morning, EU afternoon) — PRIME
- 17:00-19:00 (US afternoon) — HIGH
- 21:00-23:00 (US evening) — MEDIUM-HIGH
- 01:00-03:00 (Asia morning) — MEDIUM

Strategy: Add random jitter within peak windows.
"""

import os
import json
import random
import logging
from datetime import datetime, timezone

logger = logging.getLogger("optimal_timing")

PEAK_WINDOWS_UTC = [
    {"start": 13, "end": 15, "weight": 1.5, "label": "US morning prime"},
    {"start": 17, "end": 19, "weight": 1.2, "label": "US afternoon"},
    {"start": 21, "end": 23, "weight": 1.0, "label": "US evening"},
    {"start": 1, "end": 3, "weight": 0.8, "label": "Asia morning"},
]

DEAD_HOURS_UTC = [5, 6, 7, 8, 9, 10]  # 1am-6am ET — minimal engagement


def is_good_time_to_post() -> bool:
    """Check if now is a reasonable time to post."""
    hour = datetime.now(timezone.utc).hour
    return hour not in DEAD_HOURS_UTC


def get_current_window_weight() -> float:
    """Get the engagement weight for the current hour."""
    hour = datetime.now(timezone.utc).hour
    for w in PEAK_WINDOWS_UTC:
        if w["start"] <= hour < w["end"]:
            return w["weight"]
    if hour in DEAD_HOURS_UTC:
        return 0.3
    return 0.7


def should_post_now(strategy: str = "default") -> bool:
    """Probabilistic posting decision based on timing."""
    if not is_good_time_to_post():
        return False
    
    weight = get_current_window_weight()
    
    # Load performance weights if available
    try:
        if os.path.exists("data/strategy_weights.json"):
            weights = json.load(open("data/strategy_weights.json"))
            strategy_weight = weights.get(strategy, 1.0)
            weight *= strategy_weight
    except:
        pass

    # During prime time, almost always post. During off-peak, sometimes skip.
    threshold = random.random()
    return threshold < min(weight, 1.0)


def add_jitter_seconds(max_jitter=600) -> int:
    """Add random delay to avoid posting at exact cron times."""
    return random.randint(30, max_jitter)
