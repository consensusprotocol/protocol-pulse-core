"""
X Spaces Monitor (Skeleton)
=============================
Interface ready for Twitter Spaces ingestion.
Pipeline continues without Spaces data — this is a future moat.

TODO: Implement when Twitter Spaces API access confirmed.
"""
import logging
from typing import List
from pathlib import Path

logger = logging.getLogger("SpacesMonitor")


def fetch_recent_spaces(accounts: List[str] = None, hours: int = 24,
                         bundle_path: Path = None) -> List[dict]:
    """
    Fetch recent X Spaces from monitored accounts.

    Returns empty list for now — pipeline continues without Spaces data.
    When implemented, will return list of:
    {
        "space_id": str,
        "title": str,
        "host": str,
        "speakers": [str],
        "started_at": str,
        "duration_minutes": int,
        "listener_count": int,
        "recording_url": str | None,
        "transcript": str | None
    }
    """
    logger.info("  Spaces monitor: not yet implemented (skeleton)")
    return []
