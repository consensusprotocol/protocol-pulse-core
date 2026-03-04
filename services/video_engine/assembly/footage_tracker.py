"""
Footage Tracker
================
Track used stock footage to prevent repeats across episodes.
Stores used video IDs and URLs in a JSON file.
"""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("FootageTracker")

TRACKER_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "used_footage.json"
)


def load_used() -> dict:
    """Load the used footage registry."""
    if os.path.exists(TRACKER_FILE):
        try:
            return json.load(open(TRACKER_FILE))
        except (json.JSONDecodeError, IOError):
            return {"pexels": [], "urls": []}
    return {"pexels": [], "urls": []}


def mark_used(footage_id: str, source: str = "pexels"):
    """Mark a footage ID as used."""
    used = load_used()
    if footage_id not in used.get(source, []):
        used.setdefault(source, []).append(footage_id)
        Path(TRACKER_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(TRACKER_FILE, "w") as f:
            json.dump(used, f, indent=2)
        logger.debug(f"  Marked footage as used: {source}/{footage_id}")


def is_used(footage_id: str, source: str = "pexels") -> bool:
    """Check if a footage ID has been used before."""
    used = load_used()
    return footage_id in used.get(source, [])


def get_used_count(source: str = "pexels") -> int:
    """Get count of used footage for a source."""
    used = load_used()
    return len(used.get(source, []))
