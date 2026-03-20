#!/usr/bin/env python3
"""Tier 2 Discovery Engine — find high-credibility NON-Bitcoin channels covering Bitcoin.

Uses YouTube Data API v3 to search for crossover videos: a Bret Weinstein or Lex Fridman
covering Bitcoin is more signal-rich than another Bitcoin-native channel.

Exports: discover_crossover_videos() -> list[dict]
"""
import json
import logging
import math
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

BASE = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(BASE, "channels.yaml")
CACHE_FILE = os.path.join(BASE, "data", "tier2_cache.json")
CACHE_TTL_HOURS = 6

logger = logging.getLogger("Tier2Discovery")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[tier2] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ── Search queries ───────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    "bitcoin",
    "bitcoin federal reserve",
    "bitcoin sound money",
    "bitcoin inflation hedge",
    "bitcoin financial sovereignty",
]

# ── Known Bitcoin channels from channels.yaml (loaded once) ──────────────────
_KNOWN_CHANNEL_IDS: set | None = None
_KNOWN_CHANNEL_NAMES: set | None = None


def _load_known_channels() -> tuple[set, set]:
    """Load channel IDs and names from channels.yaml for crossover detection."""
    global _KNOWN_CHANNEL_IDS, _KNOWN_CHANNEL_NAMES
    if _KNOWN_CHANNEL_IDS is not None:
        return _KNOWN_CHANNEL_IDS, _KNOWN_CHANNEL_NAMES

    ids = set()
    names = set()
    try:
        with open(CHANNELS_FILE) as f:
            config = yaml.safe_load(f)
        for section in ["channels", "mainstream"]:
            for ch in config.get(section, []) or []:
                name = ch.get("name", "")
                if name:
                    names.add(name.lower())
                # Extract channel ID from URL if available
                handle = ch.get("handle", "")
                if handle:
                    names.add(handle.lower().lstrip("@"))
    except Exception as e:
        logger.warning(f"Could not load channels.yaml: {e}")

    _KNOWN_CHANNEL_IDS = ids
    _KNOWN_CHANNEL_NAMES = names
    return ids, names


def _is_known_bitcoin_channel(channel_id: str, channel_title: str) -> bool:
    """Check if a channel is already in our Bitcoin-native channels.yaml."""
    ids, names = _load_known_channels()
    if channel_id in ids:
        return True
    title_lower = channel_title.lower()
    # Check against known names
    for known in names:
        if known in title_lower or title_lower in known:
            return True
    return False


# ── Cache ────────────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    """Load tier2_cache.json. Returns {video_id: {data..., cached_at: iso}}."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict):
    """Write cache to disk."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def _get_cached_results() -> list[dict] | None:
    """Return cached results if ALL entries are within TTL, else None."""
    cache = _load_cache()
    if not cache:
        return None
    now = datetime.now(timezone.utc)
    results = []
    for vid, data in cache.items():
        cached_at = data.get("cached_at", "")
        try:
            ct = datetime.fromisoformat(cached_at)
            if ct.tzinfo is None:
                ct = ct.replace(tzinfo=timezone.utc)
            if (now - ct).total_seconds() > CACHE_TTL_HOURS * 3600:
                return None  # Stale — re-fetch everything
        except (ValueError, TypeError):
            return None
        # Reconstruct video dict from cache
        entry = {k: v for k, v in data.items() if k != "cached_at"}
        results.append(entry)
    return results if results else None


def _cache_results(videos: list[dict]):
    """Cache results keyed by video_id."""
    cache = {}
    now_iso = datetime.now(timezone.utc).isoformat()
    for v in videos:
        vid = v.get("video_id", "")
        if vid:
            entry = dict(v)
            entry["cached_at"] = now_iso
            cache[vid] = entry
    _save_cache(cache)


# ── YouTube Data API v3 ─────────────────────────────────────────────────────

def _yt_api_get(endpoint: str, params: dict, api_key: str) -> dict | None:
    """Make a YouTube Data API v3 GET request."""
    params["key"] = api_key
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}"
    try:
        if HAS_REQUESTS:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"YouTube API {resp.status_code}: {resp.text[:200]}")
                return None
            return resp.json()
        else:
            # Fallback to curl
            import urllib.parse
            qs = urllib.parse.urlencode(params)
            full_url = f"{url}?{qs}"
            result = subprocess.run(
                ["curl", "-s", "--max-time", "15", full_url],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode != 0:
                return None
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"YouTube API request failed: {e}")
        return None


def _search_videos(query: str, api_key: str, max_results: int = 15) -> list[dict]:
    """Search YouTube for recent videos matching query."""
    published_after = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "relevance",
        "publishedAfter": published_after,
        "maxResults": max_results,
    }
    data = _yt_api_get("search", params, api_key)
    if not data:
        return []

    results = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        vid = item.get("id", {}).get("videoId", "")
        if not vid:
            continue
        results.append({
            "video_id": vid,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
        })
    return results


def _fetch_channel_stats(channel_ids: list[str], api_key: str) -> dict:
    """Fetch channel statistics for a batch of channel IDs.

    Returns {channel_id: {subscriber_count, video_count, published_at}}.
    YouTube API allows up to 50 IDs per request.
    """
    stats = {}
    # Batch in groups of 50
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        params = {
            "part": "statistics,snippet",
            "id": ",".join(batch),
        }
        data = _yt_api_get("channels", params, api_key)
        if not data:
            continue
        for item in data.get("items", []):
            cid = item.get("id", "")
            s = item.get("statistics", {})
            snip = item.get("snippet", {})
            stats[cid] = {
                "subscriber_count": int(s.get("subscriberCount", 0)),
                "video_count": int(s.get("videoCount", 0)),
                "published_at": snip.get("publishedAt", ""),
            }
    return stats


def _fetch_video_durations(video_ids: list[str], api_key: str) -> dict:
    """Fetch video durations for a batch of video IDs.

    Returns {video_id: duration_seconds}.
    """
    durations = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        params = {
            "part": "contentDetails",
            "id": ",".join(batch),
        }
        data = _yt_api_get("videos", params, api_key)
        if not data:
            continue
        for item in data.get("items", []):
            vid = item.get("id", "")
            duration_iso = item.get("contentDetails", {}).get("duration", "PT0S")
            durations[vid] = _parse_iso_duration(duration_iso)
    return durations


def _parse_iso_duration(iso: str) -> float:
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0.0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return float(hours * 3600 + minutes * 60 + seconds)


# ── Scoring ──────────────────────────────────────────────────────────────────

def _score_video(
    subscriber_count: int,
    hours_since_published: float,
    is_crossover: bool,
    avg_videos_per_day: float,
) -> float:
    """Score a video for crossover signal value."""
    if subscriber_count < 50000:
        return -1  # Disqualified
    if avg_videos_per_day > 2:
        return -1  # Spam filter

    base_score = math.log10(max(subscriber_count, 1)) * 10
    recency_bonus = max(0, 48 - hours_since_published) * 0.5
    crossover_bonus = 25 if is_crossover else 0
    frequency_penalty = -20 if avg_videos_per_day > 2 else 0

    return base_score + recency_bonus + crossover_bonus + frequency_penalty


# ── Transcript fetch (same method as channel_scanner.py) ─────────────────────

def _fetch_transcript(video_id: str) -> tuple[str, str]:
    """Fetch transcript via yt-dlp subtitles. Returns (text, timestamped_text)."""
    # Check transcript cache first
    transcript_dir = os.path.join(BASE, "transcripts")
    cache_path = os.path.join(transcript_dir, f"{video_id}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path) as f:
                cached = json.load(f)
            return cached.get("text", ""), cached.get("timestamped_text", "")
        except Exception:
            pass

    # Use yt-dlp to get auto-generated subtitles
    url = f"https://www.youtube.com/watch?v={video_id}"
    tmp_dir = os.path.join(BASE, "downloads", "subs_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    sub_path = os.path.join(tmp_dir, video_id)

    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "json3",
        "--skip-download",
        "--no-warnings",
        "--quiet",
        "-o", sub_path,
        url,
    ]

    # Add cookies if available
    cookies_path = os.path.join(BASE, "..", "data", "yt_cookies.txt")
    if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
        cmd.extend(["--cookies", cookies_path])

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp subtitle download timed out: {video_id}")
        return "", ""

    # Find the subtitle file
    sub_file = None
    for ext in [".en.json3", ".en.vtt", ".en.srv3"]:
        candidate = sub_path + ext
        if os.path.exists(candidate):
            sub_file = candidate
            break

    if not sub_file:
        # Try glob for any subtitle file
        import glob
        matches = glob.glob(f"{sub_path}*")
        if matches:
            sub_file = matches[0]

    if not sub_file:
        return "", ""

    try:
        with open(sub_file) as f:
            content = f.read()

        text_parts = []
        timestamped_lines = []

        if sub_file.endswith(".json3"):
            data = json.loads(content)
            for event in data.get("events", []):
                segs = event.get("segs", [])
                line = "".join(s.get("utf8", "") for s in segs).strip()
                if line and line != "\n":
                    text_parts.append(line)
                    start_ms = event.get("tStartMs", 0)
                    mm = int((start_ms / 1000) // 60)
                    ss = int((start_ms / 1000) % 60)
                    timestamped_lines.append(f"[{mm:02d}:{ss:02d}] {line}")
        else:
            # VTT/SRT — simple line extraction
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("WEBVTT") and "-->" not in line and not line.isdigit():
                    text_parts.append(line)

        text = " ".join(text_parts)
        timestamped = "\n".join(timestamped_lines) if timestamped_lines else text

        # Clean up temp file
        try:
            os.remove(sub_file)
        except OSError:
            pass

        return text, timestamped

    except Exception as e:
        logger.warning(f"Failed to parse subtitles for {video_id}: {e}")
        return "", ""


# ── Claude topic confirmation ───────────────────────────────────────────────

def _confirm_bitcoin_topic(transcript: str) -> bool:
    """Use Claude Haiku to confirm Bitcoin is the PRIMARY topic."""
    if len(transcript.split()) < 500:
        return False  # Too short to confirm

    from relay import call_llm, reload_env
    reload_env()

    # Truncate to ~2000 words to save tokens
    words = transcript.split()
    if len(words) > 2000:
        transcript = " ".join(words[:2000])

    prompt = (
        "Is Bitcoin or sound money the PRIMARY subject of this video transcript? "
        "Answer only YES or NO.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    try:
        response = call_llm(prompt, max_tokens=5, temperature=0.0, model="claude-haiku-4-5-20251001")
        if response is None:
            # Fallback: keyword density check
            btc_count = transcript.lower().count("bitcoin")
            return btc_count >= 5
        return response.strip().upper().startswith("YES")
    except Exception as e:
        logger.warning(f"Claude topic confirmation failed: {e}")
        # Fallback: keyword density
        btc_count = transcript.lower().count("bitcoin")
        return btc_count >= 5


# ── Main entry point ─────────────────────────────────────────────────────────

def discover_crossover_videos() -> list[dict]:
    """Discover high-credibility non-Bitcoin channels that recently covered Bitcoin.

    Returns list of video dicts in the same schema as scan_all_channels().
    """
    # Check cache first
    cached = _get_cached_results()
    if cached:
        logger.info(f"Tier 2 cache hit: {len(cached)} videos (TTL {CACHE_TTL_HOURS}h)")
        return cached

    # Load API key
    from relay import get_key, reload_env
    reload_env()
    api_key = get_key("YOUTUBE_API_KEY", required=False)
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not found in .env — Tier 2 Discovery disabled")
        return []

    logger.info(f"Tier 2 Discovery: searching {len(SEARCH_QUERIES)} queries...")

    # Step 1: Search across all queries, deduplicate by video_id
    all_videos = {}  # video_id -> video dict
    channel_ids_needed = set()

    for query in SEARCH_QUERIES:
        results = _search_videos(query, api_key, max_results=15)
        logger.info(f"  Query '{query}': {len(results)} results")
        for v in results:
            vid = v["video_id"]
            if vid not in all_videos:
                all_videos[vid] = v
                channel_ids_needed.add(v["channel_id"])
        time.sleep(0.1)  # Be nice to API

    logger.info(f"  Total unique videos: {len(all_videos)}, unique channels: {len(channel_ids_needed)}")

    if not all_videos:
        return []

    # Step 2: Fetch channel stats (batched, deduplicated)
    channel_stats = _fetch_channel_stats(list(channel_ids_needed), api_key)
    logger.info(f"  Channel stats fetched: {len(channel_stats)}/{len(channel_ids_needed)}")

    # Step 3: Fetch video durations
    video_durations = _fetch_video_durations(list(all_videos.keys()), api_key)

    # Step 4: Score and filter
    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)
    scored = []

    for vid, video in all_videos.items():
        cid = video["channel_id"]
        stats = channel_stats.get(cid, {})
        sub_count = stats.get("subscriber_count", 0)
        video_count = stats.get("video_count", 0)
        channel_published = stats.get("published_at", "")

        # Disqualify: subscriber count < 50k
        if sub_count < 50000:
            continue

        # Disqualify: channel age < 1 year
        if channel_published:
            try:
                ch_date = datetime.fromisoformat(channel_published.replace("Z", "+00:00"))
                if ch_date > one_year_ago:
                    continue
                channel_age_days = (now - ch_date).days
            except (ValueError, TypeError):
                channel_age_days = 365  # Assume old enough if unparseable
        else:
            channel_age_days = 365

        # Calculate average videos per day
        avg_videos_per_day = video_count / max(channel_age_days, 1)

        # Hours since published
        published_at = video.get("published_at", "")
        try:
            pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            hours_since = (now - pub_dt).total_seconds() / 3600
        except (ValueError, TypeError):
            hours_since = 24  # Default

        # Check crossover status
        is_crossover = not _is_known_bitcoin_channel(cid, video["channel"])

        score = _score_video(sub_count, hours_since, is_crossover, avg_videos_per_day)
        if score < 0:
            continue  # Disqualified

        # Duration filter: skip shorts (<2min) and super-long (>4h)
        duration = video_durations.get(vid, 0)
        if duration < 120 or duration > 14400:
            continue

        if score > 40:
            video["credibility_score"] = round(score, 1)
            video["subscriber_count"] = sub_count
            video["duration"] = duration
            video["hours_since"] = round(hours_since, 1)
            video["is_crossover"] = is_crossover
            scored.append(video)

    logger.info(f"  Scored > 40pts: {len(scored)} videos")

    if not scored:
        _cache_results([])
        return []

    # Sort by score descending for priority
    scored.sort(key=lambda v: v["credibility_score"], reverse=True)

    # Step 5: Fetch transcripts and confirm topic via Claude
    confirmed = []
    for video in scored:
        vid = video["video_id"]
        logger.info(f"  Checking [{video['channel']}] {video['title'][:50]}... (score: {video['credibility_score']})")

        text, timestamped = _fetch_transcript(vid)
        if not text or len(text.split()) < 500:
            logger.info(f"    Skipped — transcript too short ({len(text.split()) if text else 0} words)")
            continue

        if not _confirm_bitcoin_topic(text):
            logger.info(f"    Skipped — Bitcoin not primary topic")
            continue

        # Parse upload_date from published_at
        published_at = video.get("published_at", "")
        try:
            pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            upload_date = pub_dt.strftime("%Y%m%d")
        except (ValueError, TypeError):
            upload_date = datetime.now().strftime("%Y%m%d")

        confirmed.append({
            "video_id": vid,
            "title": video["title"],
            "channel": video["channel"],
            "channel_id": video["channel_id"],
            "duration": video["duration"],
            "upload_date": upload_date,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "transcript_text": text,
            "timestamped_text": timestamped,
            "source": "tier2_discovery",
            "credibility_score": video["credibility_score"],
            "subscriber_count": video["subscriber_count"],
        })
        logger.info(f"    CONFIRMED — {video['channel']} | score: {video['credibility_score']}")

        # Cap at 10 confirmed to limit API spend
        if len(confirmed) >= 10:
            break

    logger.info(f"Tier 2 Discovery: {len(confirmed)} crossover videos confirmed")

    # Cache results
    _cache_results(confirmed)

    return confirmed


if __name__ == "__main__":
    results = discover_crossover_videos()
    print(f"\nFound {len(results)} crossover videos")
    for v in results[:5]:
        xover = "CROSSOVER" if v.get("source") == "tier2_discovery" else "KNOWN"
        print(f"  [{xover}] {v['channel']} | {v['title'][:60]} | score: {v['credibility_score']} | subs: {v.get('subscriber_count', 0):,}")
