#!/usr/bin/env python3
"""pipeline/discover.py — K2 stage: find candidate videos for a keyword topic.

Niche modes:
  bitcoin — RSS feeds from channels.json registry, filter by keyword in title
  open — yt-dlp ytsearch + ytsearchdate, credibility filter (subs >= 50k)

Freshness windows:
  breaking — 24 h
  developing — 72 h
  analysis — 14 d
"""
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)

from scan import fetch_rss, parse_iso_datetime

FRESHNESS_HOURS = {
    "breaking": 24,
    "developing": 72,
    "analysis": 14 * 24,
}


def _keyword_match(title, keyword):
    """Check if any keyword term appears in the title (case-insensitive)."""
    title_lower = title.lower()
    terms = [t.strip().lower() for t in keyword.split() if len(t.strip()) >= 3]
    return any(t in title_lower for t in terms)


def _expand_synonyms(keyword):
    """Return keyword + basic synonyms (no LLM call for speed)."""
    terms = [keyword.lower()]
    # Common expansions
    expansions = {
        "bitcoin": ["btc", "bitcoin"],
        "btc": ["btc", "bitcoin"],
        "ethereum": ["eth", "ethereum"],
        "dollar": ["usd", "dollar", "greenback"],
        "bank": ["bank", "banking", "banks"],
        "shutdown": ["shutdown", "shut down", "closed", "closure"],
        "paraguay": ["paraguay", "paraguayan"],
    }
    for word in keyword.lower().split():
        if word in expansions:
            terms.extend(expansions[word])
    return list(set(terms))


def discover_bitcoin(keyword, freshness, run_dir):
    """RSS-based discovery from the channel registry."""
    channels_path = os.path.join(PIPELINE_DIR, "channels.json")
    with open(channels_path) as f:
        channels = json.load(f)

    window_hours = FRESHNESS_HOURS.get(freshness, 24)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    enabled = [ch for ch in channels if ch.get("enabled", True) and ch.get("channel_id")]
    print(f"  Scanning {len(enabled)} channels (window: {window_hours}h)")

    candidates = []
    synonyms = _expand_synonyms(keyword)

    for i, ch in enumerate(enabled):
        channel_id = ch["channel_id"]
        name = ch.get("display_name", ch.get("yt_handle", ""))
        videos = fetch_rss(channel_id)

        for v in videos:
            pub = parse_iso_datetime(v["published"])
            if pub is None or pub < cutoff:
                continue
            if "/shorts/" in v.get("url", ""):
                continue

            # Keyword filter: check title against synonyms
            title_lower = v["title"].lower()
            if not any(t in title_lower for t in synonyms):
                continue

            candidates.append({
                "video_id": v["video_id"],
                "title": v["title"],
                "channel": name,
                "handle": ch.get("yt_handle", ""),
                "tier": ch.get("tier", 3),
                "published": v["published"],
                "url": v["url"],
                "channel_id": channel_id,
                "source": "rss",
            })

    print(f"  RSS: {len(candidates)} candidates matching '{keyword}'")
    return candidates


def _ytdlp_search(query, max_results=40):
    """Run yt-dlp flat search and return metadata list."""
    cmd = [
        "yt-dlp", "--flat-playlist", "--dump-json",
        "--no-warnings", "--quiet",
        f"ytsearch{max_results}:{query}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        entries = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  WARN: yt-dlp search failed: {e}")
        return []


def _ytdlp_search_date(query, max_results=40):
    """yt-dlp date-sorted search."""
    cmd = [
        "yt-dlp", "--flat-playlist", "--dump-json",
        "--no-warnings", "--quiet",
        f"ytsearchdate{max_results}:{query}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        entries = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  WARN: yt-dlp date search failed: {e}")
        return []


def discover_open(keyword, freshness, run_dir):
    """yt-dlp search-based discovery for open niche."""
    window_hours = FRESHNESS_HOURS.get(freshness, 72)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    print(f"  Searching YouTube for '{keyword}' (window: {window_hours}h)")

    # Run both searches in parallel
    all_entries = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_ytdlp_search, keyword, 40)
        f2 = pool.submit(_ytdlp_search_date, keyword, 40)
        all_entries.extend(f1.result())
        all_entries.extend(f2.result())

    # Deduplicate by video_id
    seen = set()
    unique = []
    for e in all_entries:
        vid = e.get("id", e.get("url", ""))
        if vid not in seen:
            seen.add(vid)
            unique.append(e)

    print(f"  Raw results: {len(all_entries)} -> {len(unique)} unique")

    # Filter: duration 4-180 min, not Shorts, not music, language en
    candidates = []
    for e in unique:
        duration = e.get("duration")
        if duration is None:
            continue
        if duration < 240 or duration > 10800:  # 4 min to 3 hours
            continue

        # Not a Short
        if e.get("_type") == "short":
            continue

        # Channel subscriber count filter (>= 50k) — use from metadata if available
        subs = e.get("channel_follower_count", 0)
        if subs is not None and subs < 50000 and subs != 0:
            continue

        # Upload date recency check
        upload_date = e.get("upload_date", "")  # YYYYMMDD format
        if upload_date:
            try:
                pub_dt = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            except ValueError:
                pass

        candidates.append({
            "video_id": e.get("id", ""),
            "title": e.get("title", ""),
            "channel": e.get("channel", e.get("uploader", "")),
            "handle": e.get("channel_url", ""),
            "tier": 4,
            "published": upload_date,
            "url": e.get("webpage_url", f"https://www.youtube.com/watch?v={e.get('id', '')}"),
            "duration": duration,
            "channel_subs": subs,
            "source": "search",
        })

    print(f"  Filtered: {len(candidates)} candidates (4-180min, subs>=50k)")
    return candidates


def discover_sources(keyword, niche, freshness, run_dir):
    """Main entry point. Returns list of candidate dicts and writes sources.json."""
    t0 = time.time()
    print(f"\n=== DISCOVER: '{keyword}' (niche={niche}, freshness={freshness}) ===")

    if niche == "bitcoin":
        candidates = discover_bitcoin(keyword, freshness, run_dir)
    elif niche == "open":
        candidates = discover_open(keyword, freshness, run_dir)
    else:
        raise ValueError(f"Unknown niche: {niche}")

    # Sort by tier (lower = better), then by published date (newer first)
    candidates.sort(key=lambda c: (c.get("tier", 9), c.get("published", "")),
                    reverse=False)

    # Write sources.json
    sources_path = os.path.join(run_dir, "sources.json")
    with open(sources_path, "w") as f:
        json.dump(candidates, f, indent=2)

    elapsed = time.time() - t0
    print(f"  {len(candidates)} candidates written to {sources_path}")
    print(f"  Discover time: {elapsed:.1f}s")

    return candidates
