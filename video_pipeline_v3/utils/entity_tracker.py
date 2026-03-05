#!/usr/bin/env python3
"""Entity Tracker — NER-lite extraction from channel archive transcripts.

Scans all transcripts in data/channel_archive/*/*.json for known entities,
counts mentions per 24h window, and writes data/intelligence/entity_mentions.json.
"""

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("entity_tracker")

BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = BASE_DIR / "data" / "channel_archive"
OUTPUT_PATH = BASE_DIR / "data" / "intelligence" / "entity_mentions.json"

# Known entities to track — name variants map to canonical name
KNOWN_ENTITIES = {
    # People
    "saylor": {"canonical": "Michael Saylor", "type": "person"},
    "michael saylor": {"canonical": "Michael Saylor", "type": "person"},
    "larry fink": {"canonical": "Larry Fink", "type": "person"},
    "cathie wood": {"canonical": "Cathie Wood", "type": "person"},
    "gary gensler": {"canonical": "Gary Gensler", "type": "person"},
    "elizabeth warren": {"canonical": "Elizabeth Warren", "type": "person"},
    "jack dorsey": {"canonical": "Jack Dorsey", "type": "person"},
    "jack mallers": {"canonical": "Jack Mallers", "type": "person"},
    "elon musk": {"canonical": "Elon Musk", "type": "person"},
    "trump": {"canonical": "Donald Trump", "type": "person"},
    "donald trump": {"canonical": "Donald Trump", "type": "person"},
    "powell": {"canonical": "Jerome Powell", "type": "person"},
    "jerome powell": {"canonical": "Jerome Powell", "type": "person"},
    "sam bankman": {"canonical": "Sam Bankman-Fried", "type": "person"},
    "cz": {"canonical": "CZ (Binance)", "type": "person"},
    "changpeng zhao": {"canonical": "CZ (Binance)", "type": "person"},
    "max keiser": {"canonical": "Max Keiser", "type": "person"},
    "pomp": {"canonical": "Anthony Pompliano", "type": "person"},
    "pompliano": {"canonical": "Anthony Pompliano", "type": "person"},
    "raoul pal": {"canonical": "Raoul Pal", "type": "person"},
    "ross ulbricht": {"canonical": "Ross Ulbricht", "type": "person"},
    "jeff booth": {"canonical": "Jeff Booth", "type": "person"},
    "parker lewis": {"canonical": "Parker Lewis", "type": "person"},
    "lyn alden": {"canonical": "Lyn Alden", "type": "person"},
    "saifedean": {"canonical": "Saifedean Ammous", "type": "person"},
    # Companies/Orgs
    "blackrock": {"canonical": "BlackRock", "type": "company"},
    "fidelity": {"canonical": "Fidelity", "type": "company"},
    "grayscale": {"canonical": "Grayscale", "type": "company"},
    "microstrategy": {"canonical": "MicroStrategy", "type": "company"},
    "strategy": {"canonical": "MicroStrategy", "type": "company"},
    "coinbase": {"canonical": "Coinbase", "type": "company"},
    "binance": {"canonical": "Binance", "type": "company"},
    "ark invest": {"canonical": "ARK Invest", "type": "company"},
    "bitwise": {"canonical": "Bitwise", "type": "company"},
    "vaneck": {"canonical": "VanEck", "type": "company"},
    "invesco": {"canonical": "Invesco", "type": "company"},
    "jp morgan": {"canonical": "JPMorgan", "type": "company"},
    "jpmorgan": {"canonical": "JPMorgan", "type": "company"},
    "goldman sachs": {"canonical": "Goldman Sachs", "type": "company"},
    "goldman": {"canonical": "Goldman Sachs", "type": "company"},
    "tesla": {"canonical": "Tesla", "type": "company"},
    "marathon": {"canonical": "Marathon Digital", "type": "company"},
    "riot": {"canonical": "Riot Platforms", "type": "company"},
    "strike": {"canonical": "Strike", "type": "company"},
    "swan bitcoin": {"canonical": "Swan Bitcoin", "type": "company"},
    "unchained": {"canonical": "Unchained", "type": "company"},
    "casa": {"canonical": "Casa", "type": "company"},
    "sec": {"canonical": "SEC", "type": "regulator"},
    "federal reserve": {"canonical": "Federal Reserve", "type": "regulator"},
    "the fed": {"canonical": "Federal Reserve", "type": "regulator"},
    # Protocols
    "lightning network": {"canonical": "Lightning Network", "type": "protocol"},
    "lightning": {"canonical": "Lightning Network", "type": "protocol"},
    "nostr": {"canonical": "Nostr", "type": "protocol"},
}

# Compile regex patterns for efficiency
_PATTERNS = {}
for variant, info in KNOWN_ENTITIES.items():
    _PATTERNS[variant] = re.compile(r'\b' + re.escape(variant) + r'\b', re.IGNORECASE)


def scan_archive(hours: int = 48) -> dict:
    """Scan channel archive transcripts for entity mentions.

    Args:
        hours: Only consider videos archived within this many hours.

    Returns:
        Dict of {canonical_name: {type, mentions, channels, videos}}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    entity_counts = defaultdict(lambda: {
        "type": "",
        "mentions": 0,
        "channels": set(),
        "videos": set(),
    })

    if not ARCHIVE_DIR.exists():
        logger.warning(f"Archive dir not found: {ARCHIVE_DIR}")
        return {}

    for channel_dir in ARCHIVE_DIR.iterdir():
        if not channel_dir.is_dir():
            continue
        for video_file in channel_dir.glob("*.json"):
            try:
                with open(video_file) as f:
                    video = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            # Check freshness
            archived_at = video.get("archived_at", "")
            if archived_at:
                try:
                    ts = datetime.fromisoformat(archived_at.replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                except ValueError:
                    pass

            # Get text to search — title + transcript
            text = video.get("title", "") + " " + video.get("transcript_text", "")
            if not text.strip():
                continue

            channel = video.get("channel", channel_dir.name)
            video_id = video.get("video_id", video_file.stem)

            # Count entities (deduplicated per video)
            seen_in_video = set()
            for variant, pattern in _PATTERNS.items():
                canonical = KNOWN_ENTITIES[variant]["canonical"]
                if canonical in seen_in_video:
                    continue
                matches = pattern.findall(text)
                if matches:
                    seen_in_video.add(canonical)
                    info = KNOWN_ENTITIES[variant]
                    entry = entity_counts[canonical]
                    entry["type"] = info["type"]
                    entry["mentions"] += 1  # 1 per video (deduplicated)
                    entry["channels"].add(channel)
                    entry["videos"].add(video_id)

    return entity_counts


def build_entity_mentions(hours: int = 48) -> dict:
    """Build the entity_mentions.json structure."""
    raw = scan_archive(hours)
    entities = []
    for name, data in sorted(raw.items(), key=lambda x: x[1]["mentions"], reverse=True):
        entities.append({
            "name": name,
            "type": data["type"],
            "mentions_24h": data["mentions"],
            "channels_covering": len(data["channels"]),
            "channel_names": sorted(data["channels"]),
            "video_count": len(data["videos"]),
        })

    result = {
        "entities": entities[:50],  # Top 50
        "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_entities_detected": len(entities),
        "archive_window_hours": hours,
    }

    # Write to file
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Entity mentions written: {len(entities)} entities -> {OUTPUT_PATH}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = build_entity_mentions()
    print(json.dumps(result, indent=2))
