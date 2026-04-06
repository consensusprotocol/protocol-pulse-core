"""
profile_poller.py — Free X Spaces detection via profile polling + nitter URL scanning.

Replaces the $5K/mo Twitter API v2 Spaces search with two zero-cost methods:

METHOD 1 (PRIMARY): Scan raw_tweets.json from the nitter scraper for Space URLs.
  - The nitter scraper already monitors 44+ KOL handles every 6 hours.
  - Tweets containing twitter.com/i/spaces/ or x.com/i/spaces/ URLs are extracted.
  - Filtered to tweets from the last 24 hours.

METHOD 2 (SUPPLEMENTARY): Twitter Syndication timeline polling.
  - Unauthenticated endpoint: syndication.twitter.com/srv/timeline-profile/screen-name/{handle}
  - Returns recent tweets as embedded JSON. Works for most public accounts.
  - Extracts Space URLs from tweet text.
  - Polls a subset of high-priority KOL handles.

Combined output is deduplicated by space_id and scored for relevance.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
RAW_TWEETS_PATH = PROJECT_ROOT / "data" / "tweet_study" / "raw_tweets.json"
CACHE_DIR = Path(__file__).parent / "cache"

# Space URL pattern
SPACE_URL_RE = re.compile(r'(?:twitter\.com|x\.com)/i/spaces/([a-zA-Z0-9]+)')

# High-priority handles for syndication polling (subset — most active Spaces hosts)
SYNDICATION_HANDLES = [
    "saylor", "MartyBent", "PrestonPysh", "natbrunell", "gladstein",
    "PeterMcCormack", "lopp", "DocumentingBTC", "BitcoinMagazine",
    "SimplyBitcoinTV", "stephanlivera", "saifedean", "coryklippsten",
    "LynAldenContact", "TomerStrolight", "TheGuySwann", "BTCsessions",
    "WhatBitcoinDid", "TheBitcoinConf", "APompliano",
]

# All known KOL handles for raw_tweets matching
from x_spaces_scraper.scraper import TIER1_HANDLES, TIER2_HANDLES


def scan_raw_tweets_for_spaces(max_age_hours: int = 24) -> list[dict]:
    """Scan raw_tweets.json for tweets containing X Space URLs.

    Returns list of dicts with: space_id, title, host_handle, state, detected_via, tweet_text, tweet_time.
    """
    if not RAW_TWEETS_PATH.exists():
        logger.warning("[ProfilePoller] raw_tweets.json not found")
        return []

    try:
        tweets = json.loads(RAW_TWEETS_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"[ProfilePoller] Failed to read raw_tweets.json: {e}")
        return []

    if not isinstance(tweets, list):
        logger.warning("[ProfilePoller] raw_tweets.json is not a list")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    spaces = []
    seen_ids: set[str] = set()

    for tweet in tweets:
        text = tweet.get("text", "")
        match = SPACE_URL_RE.search(text)
        if not match:
            continue

        space_id = match.group(1)
        if space_id in seen_ids:
            continue

        # Parse timestamp
        ts_str = tweet.get("timestamp", "") or tweet.get("created_at", "")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if dt < cutoff:
                    continue
            except (ValueError, TypeError):
                pass  # Keep if can't parse — better to include than miss

        seen_ids.add(space_id)
        handle = tweet.get("handle", "") or tweet.get("monitored_handle", "")

        spaces.append({
            "space_id": space_id,
            "title": _extract_title_from_text(text, space_id),
            "host_handle": handle,
            "creator_id": "",
            "participant_count": 0,
            "started_at": ts_str,
            "state": "ended",  # Assume ended; live detection is bonus
            "detected_via": "nitter_raw_tweets",
            "tweet_text": text[:300],
        })

    logger.info(f"[ProfilePoller] Found {len(spaces)} space(s) from raw_tweets.json")
    return spaces


def poll_syndication_for_spaces(handles: Optional[list[str]] = None,
                                 max_age_hours: int = 24) -> list[dict]:
    """Poll Twitter syndication timelines for Space URLs in recent tweets.

    Returns list of dicts with: space_id, title, host_handle, state, detected_via.
    """
    if handles is None:
        handles = SYNDICATION_HANDLES

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    spaces = []
    seen_ids: set[str] = set()
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

    for handle in handles:
        try:
            url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
            r = session.get(url, timeout=10)
            if r.status_code != 200:
                logger.debug(f"[ProfilePoller] Syndication {handle}: HTTP {r.status_code}")
                continue

            # Extract __NEXT_DATA__ JSON from HTML
            match = re.search(
                r'__NEXT_DATA__.*?type="application/json">(.*?)</script>',
                r.text,
            )
            if not match:
                continue

            data = json.loads(match.group(1))
            entries = (
                data.get("props", {})
                .get("pageProps", {})
                .get("timeline", {})
                .get("entries", [])
            )

            for entry in entries:
                tweet = entry.get("content", {}).get("tweet", {})
                text = tweet.get("text", "")

                space_match = SPACE_URL_RE.search(text)
                if not space_match:
                    # Also check expanded URLs in entities
                    for u in tweet.get("entities", {}).get("urls", []):
                        expanded = u.get("expanded_url", "")
                        space_match = SPACE_URL_RE.search(expanded)
                        if space_match:
                            break
                    if not space_match:
                        continue

                space_id = space_match.group(1)
                if space_id in seen_ids:
                    continue

                # Check tweet age
                created = tweet.get("created_at", "")
                if created:
                    try:
                        # Twitter format: "Thu Apr 03 19:48:01 +0000 2026"
                        dt = _parse_twitter_date(created)
                        if dt and dt < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass

                seen_ids.add(space_id)
                spaces.append({
                    "space_id": space_id,
                    "title": _extract_title_from_text(text, space_id),
                    "host_handle": handle,
                    "creator_id": "",
                    "participant_count": 0,
                    "started_at": created,
                    "state": "ended",
                    "detected_via": "syndication_poll",
                    "tweet_text": text[:300],
                })

        except requests.exceptions.RequestException as e:
            logger.debug(f"[ProfilePoller] Syndication {handle} request error: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"[ProfilePoller] Syndication {handle} parse error: {e}")

        # Rate limit: small delay between requests
        time.sleep(0.3)

    logger.info(f"[ProfilePoller] Found {len(spaces)} space(s) from syndication polling ({len(handles)} handles)")
    return spaces


def find_live_spaces(max_age_hours: int = 24) -> list[dict]:
    """Combined Space detection: nitter + syndication. Deduplicated by space_id.

    Returns list of dicts compatible with scraper.py's find_live_bitcoin_spaces() format:
    {space_id, title, creator_id, participant_count, started_at, state, host_handle, detected_via, score}
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache (15-min TTL)
    now = datetime.now(timezone.utc)
    cache_file = CACHE_DIR / "poller_spaces.json"
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            cache_age = time.time() - cached.get("fetched_at", 0)
            if cache_age < 900:  # 15 min
                logger.info(f"[ProfilePoller] Using cached results ({len(cached['spaces'])} spaces, {cache_age:.0f}s old)")
                return cached["spaces"]
        except (json.JSONDecodeError, KeyError):
            pass

    # Method 1: Nitter raw tweets
    nitter_spaces = scan_raw_tweets_for_spaces(max_age_hours=max_age_hours)

    # Method 2: Syndication polling
    syndication_spaces = poll_syndication_for_spaces(max_age_hours=max_age_hours)

    # Merge + deduplicate (nitter takes priority since it has KOL metadata)
    seen_ids: set[str] = set()
    merged: list[dict] = []

    for s in nitter_spaces:
        sid = s["space_id"]
        if sid not in seen_ids:
            seen_ids.add(sid)
            merged.append(s)

    for s in syndication_spaces:
        sid = s["space_id"]
        if sid not in seen_ids:
            seen_ids.add(sid)
            merged.append(s)

    # Score for relevance
    for s in merged:
        s["score"] = _score_detected_space(s)
    merged.sort(key=lambda x: x["score"], reverse=True)

    # Top 10
    result = merged[:10]

    logger.info(f"[ProfilePoller] Combined: {len(result)} unique space(s) (nitter={len(nitter_spaces)}, syndication={len(syndication_spaces)})")
    for s in result[:5]:
        logger.info(f"[ProfilePoller]   [{s['detected_via']}] @{s['host_handle']}: {s['title'][:60]} (score={s['score']:.0f})")

    # Cache
    cache_file.write_text(json.dumps({
        "spaces": result,
        "fetched_at": time.time(),
        "nitter_count": len(nitter_spaces),
        "syndication_count": len(syndication_spaces),
    }, indent=2))

    return result


def _extract_title_from_text(text: str, space_id: str) -> str:
    """Extract a meaningful title from the tweet text around a Space URL."""
    # Remove the URL itself
    cleaned = SPACE_URL_RE.sub("", text).strip()
    # Remove common prefixes
    for prefix in ("Listen in tomorrow.", "Starting in", "We're live,", "Join us"):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip(" .,!-")

    # Take first sentence or 120 chars
    if cleaned:
        first_line = cleaned.split("\n")[0].strip()
        return first_line[:120] if first_line else f"Space {space_id}"
    return f"Space {space_id}"


def _parse_twitter_date(date_str: str) -> Optional[datetime]:
    """Parse Twitter's date format: 'Thu Apr 03 19:48:01 +0000 2026'."""
    try:
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        # Try ISO format as fallback
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None


def _score_detected_space(space: dict) -> float:
    """Score a detected space for relevance/priority."""
    score = 0.0

    handle = (space.get("host_handle") or "").lower().lstrip("@")
    if handle in {h.lower() for h in TIER1_HANDLES}:
        score += 50
    elif handle in {h.lower() for h in TIER2_HANDLES}:
        score += 25

    # Recency bonus
    ts_str = space.get("started_at", "")
    if ts_str:
        try:
            dt = _parse_twitter_date(ts_str)
            if dt is None:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            if age_hours < 2:
                score += 30
            elif age_hours < 6:
                score += 20
            elif age_hours < 12:
                score += 10
        except (ValueError, TypeError):
            pass

    # Title keyword bonus
    title = (space.get("title") or "").lower()
    tweet_text = (space.get("tweet_text") or "").lower()
    combined = title + " " + tweet_text
    bitcoin_kws = {"bitcoin", "btc", "saylor", "lightning", "halving", "mining",
                   "etf", "blackrock", "hodl", "satoshi", "macro", "fed", "inflation"}
    for kw in bitcoin_kws:
        if kw in combined:
            score += 10
            break

    # Nitter detection is more reliable (curated KOL list)
    if space.get("detected_via") == "nitter_raw_tweets":
        score += 5

    return score


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    print("=== Profile Poller: Free Space Detection ===\n")
    spaces = find_live_spaces()
    print(f"\nDetected {len(spaces)} spaces via free methods:")
    for s in spaces:
        print(f"  [{s['detected_via']}] @{s['host_handle']}: {s['title'][:80]} (score={s['score']:.0f})")
