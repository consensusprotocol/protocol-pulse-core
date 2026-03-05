"""Analytics Store — per-episode performance data persistence.

Saves and loads episode metrics to data/performance/{episode_id}.json.
YouTube analytics fields (avg_view_duration_pct, ctr, impressions, likes,
comments) are populated later by a separate analytics pull job.
"""
import json
import logging
import os
from glob import glob

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERF_DIR = os.path.join(BASE, "data", "performance")


def save_episode_performance(episode_id: str, data: dict):
    """Write episode performance data to data/performance/{episode_id}.json."""
    os.makedirs(PERF_DIR, exist_ok=True)
    path = os.path.join(PERF_DIR, f"{episode_id}.json")
    data["episode_id"] = episode_id
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Performance data saved: {path}")


def load_episode_performance(episode_id: str) -> dict:
    """Read episode performance data."""
    path = os.path.join(PERF_DIR, f"{episode_id}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading {path}: {e}")
        return {}


def get_all_performance(last_n: int = 20) -> list:
    """Return performance data for the last N episodes, sorted by date."""
    os.makedirs(PERF_DIR, exist_ok=True)
    files = sorted(glob(os.path.join(PERF_DIR, "*.json")))
    results = []
    for path in files[-last_n:]:
        try:
            with open(path) as f:
                results.append(json.load(f))
        except Exception:
            continue
    return results
