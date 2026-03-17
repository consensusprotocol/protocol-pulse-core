#!/usr/bin/env python3
"""episode_memory.py — Feedback loop for Pulse Check render quality.

Records Gemini grade data after each render and exposes historical
scoring functions so the script writer can adapt to trends.
"""
import json
import os
import time
from typing import Optional

BASE = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE, "..", "data", "episode_memory.json")


def _load() -> list:
    """Load the episodes array from disk."""
    try:
        with open(MEMORY_FILE) as f:
            data = json.load(f)
        return data.get("episodes", []) if isinstance(data, dict) else data
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(episodes: list) -> None:
    """Persist episodes array to disk."""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump({"episodes": episodes}, f, indent=2)


def record_episode(render_id: str, date: str, gemini_scores: dict,
                   clips_used: list, topics: list = None) -> None:
    """Append an episode record after a Gemini grade run.

    Args:
        render_id: Unique render identifier (e.g. run_20260317_120000)
        date: ISO date string (YYYY-MM-DD)
        gemini_scores: Full Gemini grade JSON (grade, overall_score, dimensions, etc.)
        clips_used: List of dicts with channel, video_id keys
        topics: Optional list of topic strings that appeared in this episode
    """
    episodes = _load()

    record = {
        "render_id": render_id,
        "date": date,
        "overall_score": gemini_scores.get("overall_score", 0),
        "grade": gemini_scores.get("grade", "F"),
        "clips": clips_used,
        "dimensions": gemini_scores.get("dimensions", {}),
        "technical_score": gemini_scores.get("technical_score", 0),
        "content_score": gemini_scores.get("content_score", 0),
        "production_score": gemini_scores.get("production_score", 0),
        "topics": topics or [],
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    episodes.append(record)
    _save(episodes)


def get_channel_scores() -> dict:
    """Return channel -> average Gemini overall_score dict."""
    episodes = _load()
    totals: dict = {}  # channel -> [scores]
    for ep in episodes:
        score = ep.get("overall_score", 0)
        for clip in ep.get("clips", []):
            ch = clip.get("channel", "Unknown")
            if ch and ch != "Unknown":
                totals.setdefault(ch, []).append(score)
    return {ch: round(sum(scores) / len(scores), 1)
            for ch, scores in totals.items() if scores}


def get_segment_scores() -> dict:
    """Return segment_type -> average dimension score dict."""
    episodes = _load()
    totals: dict = {}  # dimension_name -> [scores]
    for ep in episodes:
        dims = ep.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict):
                s = dim_data.get("score")
            else:
                s = dim_data
            if isinstance(s, (int, float)):
                totals.setdefault(dim_name, []).append(s)
    return {dim: round(sum(scores) / len(scores), 1)
            for dim, scores in totals.items() if scores}


def get_best_channels(n: int = 10) -> list:
    """Return top N channels sorted by average Gemini score (desc)."""
    channel_scores = get_channel_scores()
    ranked = sorted(channel_scores.items(), key=lambda x: x[1], reverse=True)
    return [{"channel": ch, "avg_score": sc} for ch, sc in ranked[:n]]


def get_episode_count() -> int:
    """Return total number of recorded episodes."""
    return len(_load())


def get_weak_dimensions(threshold: float = 6.0) -> list:
    """Return dimensions that historically score below threshold."""
    seg_scores = get_segment_scores()
    return [{"dimension": dim, "avg_score": sc}
            for dim, sc in sorted(seg_scores.items(), key=lambda x: x[1])
            if sc < threshold]


def get_strong_dimensions(threshold: float = 8.0) -> list:
    """Return dimensions that historically score above threshold."""
    seg_scores = get_segment_scores()
    return [{"dimension": dim, "avg_score": sc}
            for dim, sc in sorted(seg_scores.items(), key=lambda x: x[1], reverse=True)
            if sc >= threshold]


if __name__ == "__main__":
    count = get_episode_count()
    print(f"Episodes recorded: {count}")
    if count:
        print(f"\nChannel scores: {json.dumps(get_channel_scores(), indent=2)}")
        print(f"\nTop channels: {json.dumps(get_best_channels(5), indent=2)}")
        print(f"\nSegment scores: {json.dumps(get_segment_scores(), indent=2)}")
        weak = get_weak_dimensions()
        if weak:
            print(f"\nWeak dimensions: {json.dumps(weak, indent=2)}")
