"""Channel Scorer — rank channels by episode performance.

Analyzes data/performance/*.json to score channels by how often they
appear in episodes and the quality of episodes they appear in.

Designed to run weekly. Does NOT auto-modify channels.yaml — outputs
a report for manual review.
"""
import json
import logging
import os
from collections import defaultdict

from utils.analytics_store import get_all_performance

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def score_channels(last_n_episodes: int = 20) -> list:
    """Score all channels based on episode performance data.

    For each channel that appeared in recent episodes:
      - appearances: how many episodes featured this channel
      - avg_quality: average quality_score of episodes they appeared in
      - composite: weighted score (60% quality, 40% frequency)

    Returns:
        Sorted list of dicts: [{channel, appearances, avg_quality, composite}, ...]
    """
    episodes = get_all_performance(last_n=last_n_episodes)
    if not episodes:
        logger.info("No performance data available for scoring")
        return []

    channel_stats = defaultdict(lambda: {"quality_scores": [], "appearances": 0})

    for ep in episodes:
        quality = ep.get("quality_score", 0)
        for channel in ep.get("channels_used", []):
            if not channel:
                continue
            channel_stats[channel]["appearances"] += 1
            channel_stats[channel]["quality_scores"].append(quality)

    # Compute scores
    max_appearances = max((s["appearances"] for s in channel_stats.values()), default=1)
    results = []
    for channel, stats in channel_stats.items():
        appearances = stats["appearances"]
        avg_quality = sum(stats["quality_scores"]) / len(stats["quality_scores"])
        # Frequency normalized to 0-100
        freq_score = (appearances / max_appearances) * 100
        # Composite: 60% quality, 40% frequency
        composite = avg_quality * 0.6 + freq_score * 0.4
        results.append({
            "channel": channel,
            "appearances": appearances,
            "avg_quality": round(avg_quality, 1),
            "composite": round(composite, 1),
        })

    results.sort(key=lambda x: x["composite"], reverse=True)
    return results


def print_channel_report(last_n: int = 20):
    """Print a formatted channel performance report."""
    scores = score_channels(last_n)
    if not scores:
        print("No channel performance data available.")
        return

    print(f"\n{'='*60}")
    print(f"  CHANNEL PERFORMANCE REPORT (last {last_n} episodes)")
    print(f"{'='*60}")
    print(f"  {'Channel':<25} {'Apps':>4} {'AvgQ':>6} {'Score':>6}")
    print(f"  {'-'*25} {'-'*4} {'-'*6} {'-'*6}")
    for s in scores:
        print(f"  {s['channel']:<25} {s['appearances']:>4} {s['avg_quality']:>6.1f} {s['composite']:>6.1f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print_channel_report()
