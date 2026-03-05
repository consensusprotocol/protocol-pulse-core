#!/usr/bin/env python3
"""Node Pulse Monitor — Bitnodes API integration + milestone detection.

Polls Bitnodes for current node count, compares snapshots,
and detects milestones (every 5K nodes). Saves snapshots to
data/node_snapshots/{timestamp}.json.

Per CONTENT_INTELLIGENCE_LAWS Addendum C.
"""

import json
import logging
import os
from datetime import datetime, timezone

import requests

logger = logging.getLogger("NodeMonitor")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[node_monitor] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "data", "node_snapshots")
LATEST_PATH = os.path.join(SNAPSHOTS_DIR, "latest.json")

BITNODES_API = "https://bitnodes.io/api/v1/snapshots/latest/"


def get_node_snapshot() -> dict:
    """Fetch the latest node snapshot from Bitnodes API."""
    resp = requests.get(BITNODES_API, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "total_nodes": data.get("total_nodes", 0),
        "timestamp": data.get("timestamp", ""),
        "latest_height": data.get("latest_height", 0),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def load_previous_snapshot() -> dict | None:
    """Load the most recent saved snapshot."""
    if not os.path.exists(LATEST_PATH):
        return None
    with open(LATEST_PATH) as f:
        return json.load(f)


def save_snapshot(snapshot: dict):
    """Save snapshot to timestamped file and update latest.json."""
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    ts = snapshot.get("fetched_at", "").replace(":", "-").replace("T", "_").replace("Z", "")
    if ts:
        ts_path = os.path.join(SNAPSHOTS_DIR, f"{ts}.json")
        with open(ts_path, "w") as f:
            json.dump(snapshot, f, indent=2)
    with open(LATEST_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)


def compare_snapshots(current: dict, previous: dict | None) -> dict:
    """Compare two snapshots and detect milestones."""
    if not previous:
        return {"net_change": 0, "is_milestone": False, "milestone_number": None}

    current_total = current.get("total_nodes", 0)
    previous_total = previous.get("total_nodes", 0)
    net = current_total - previous_total

    # Milestone: every 5K boundary crossing
    current_bucket = current_total // 5000
    previous_bucket = previous_total // 5000
    is_milestone = current_bucket != previous_bucket

    return {
        "net_change": net,
        "is_milestone": is_milestone,
        "milestone_number": current_bucket * 5000 if is_milestone else None,
    }


def run():
    """Main polling routine — fetch, compare, save, log."""
    logger.info("Fetching node snapshot from Bitnodes...")
    try:
        current = get_node_snapshot()
    except Exception as e:
        logger.error(f"Failed to fetch Bitnodes data: {e}")
        return None

    previous = load_previous_snapshot()
    comparison = compare_snapshots(current, previous)

    current["comparison"] = comparison
    save_snapshot(current)

    logger.info(f"NODE PULSE: {current['total_nodes']} reachable nodes "
                f"(block {current['latest_height']})")

    if comparison["net_change"] != 0:
        direction = "+" if comparison["net_change"] > 0 else ""
        logger.info(f"  Net change: {direction}{comparison['net_change']} nodes")

    if comparison["is_milestone"]:
        logger.info(f"  MILESTONE: Crossed {comparison['milestone_number']} nodes!")

    return current


if __name__ == "__main__":
    result = run()
    if result:
        print(json.dumps(result, indent=2))
