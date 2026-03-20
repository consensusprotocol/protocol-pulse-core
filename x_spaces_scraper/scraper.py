"""
scraper.py — Find recent X Spaces from key Bitcoin accounts (last 7 days).

Detection order:
  1. Twitter API v2 (if TWITTER_BEARER_TOKEN set)
  2. Guest Token + GraphQL (no auth needed)
  3. yt-dlp metadata extraction (per-account fallback)

Unlike the live spaces_scraper, this targets *ended* Spaces with replays.
"""

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# X public bearer (same as spaces_scraper)
X_PUBLIC_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

TARGET_ACCOUNTS = [
    "saylor",
    "nvk",
    "giacomozucco",
    "dergigi",
    "natbrunell",
    "saifedean",
    "aantonop",
    "stacker_news",
    "BitcoinMagazine",
    # extras from the live scraper
    "thebitcoinlayer",
    "WhatBitcoinDid",
    "MartyBent",
    "gladstein",
    "LynAldenContact",
]

SPACE_KEYWORDS = ["bitcoin", "btc", "lightning", "sats", "nostr"]


@dataclass
class SpaceInfo:
    """Metadata for a discovered X Space."""
    space_id: str
    title: str
    host: str
    date: str               # ISO format
    participant_count: int
    state: str               # "ended", "live", "scheduled"
    url: str
    replay_available: bool = False
    detected_via: str = "unknown"
    detected_at: float = field(default_factory=time.time)

    def to_dict(self):
        return asdict(self)


# ─── Twitter API v2 ─────────────────────────────────────────────────────────

class TwitterAPIv2Scraper:
    """Uses X API v2 to search for recent Spaces (requires elevated access)."""

    def __init__(self, bearer_token: str):
        self.bearer = bearer_token
        self.base = "https://api.twitter.com/2"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.bearer}"

    def search_spaces(self, query: str = "bitcoin", state: str = "all") -> list[SpaceInfo]:
        try:
            r = self.session.get(
                f"{self.base}/spaces/search",
                params={
                    "query": query,
                    "state": state,
                    "space.fields": "id,title,host_ids,participant_count,started_at,state,ended_at",
                    "expansions": "host_ids",
                    "user.fields": "username",
                },
                timeout=15,
            )
            if r.status_code == 403:
                logger.warning("Twitter API v2: 403 — token lacks Spaces access")
                return []
            r.raise_for_status()
            data = r.json()

            spaces = data.get("data", [])
            users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}

            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            results = []
            for s in spaces:
                started = s.get("started_at", "")
                if started:
                    try:
                        dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                        if dt < cutoff:
                            continue
                    except ValueError:
                        pass

                host_id = (s.get("host_ids") or [""])[0]
                results.append(SpaceInfo(
                    space_id=s["id"],
                    title=s.get("title", ""),
                    host=users.get(host_id, "unknown"),
                    date=started,
                    participant_count=s.get("participant_count", 0),
                    state=s.get("state", "ended").lower(),
                    url=f"https://twitter.com/i/spaces/{s['id']}",
                    replay_available=s.get("state", "").lower() == "ended",
                    detected_via="twitter_api_v2",
                ))
            return results
        except Exception as e:
            logger.error(f"TwitterAPIv2 search error: {e}")
            return []

    def get_spaces_by_user(self, user_id: str) -> list[SpaceInfo]:
        """Get spaces created by a specific user."""
        try:
            r = self.session.get(
                f"{self.base}/spaces/by/creator_ids",
                params={
                    "user_ids": user_id,
                    "space.fields": "id,title,host_ids,participant_count,started_at,state,ended_at",
                    "expansions": "host_ids",
                    "user.fields": "username",
                },
                timeout=15,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            spaces = data.get("data", [])
            users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}

            results = []
            for s in spaces:
                host_id = (s.get("host_ids") or [""])[0]
                results.append(SpaceInfo(
                    space_id=s["id"],
                    title=s.get("title", ""),
                    host=users.get(host_id, "unknown"),
                    date=s.get("started_at", ""),
                    participant_count=s.get("participant_count", 0),
                    state=s.get("state", "ended").lower(),
                    url=f"https://twitter.com/i/spaces/{s['id']}",
                    replay_available=s.get("state", "").lower() == "ended",
                    detected_via="twitter_api_v2",
                ))
            return results
        except Exception as e:
            logger.debug(f"get_spaces_by_user error: {e}")
            return []


# ─── Guest Token + GraphQL ──────────────────────────────────────────────────

class GuestTokenScraper:
    """Uses guest authentication to find Spaces via GraphQL."""

    GRAPHQL_HEADERS = {
        "Authorization": f"Bearer {X_PUBLIC_BEARER}",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "X-Twitter-Active-User": "yes",
        "X-Twitter-Client-Language": "en",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.GRAPHQL_HEADERS)
        self.guest_token: Optional[str] = None
        self.token_time: float = 0

    def _refresh_token(self) -> bool:
        try:
            r = self.session.post(
                "https://api.twitter.com/1.1/guest/activate.json",
                timeout=10,
            )
            r.raise_for_status()
            self.guest_token = r.json()["guest_token"]
            self.token_time = time.time()
            self.session.headers["X-Guest-Token"] = self.guest_token
            logger.info(f"Guest token refreshed: {self.guest_token[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Guest token refresh failed: {e}")
            return False

    def _ensure_token(self):
        if not self.guest_token or (time.time() - self.token_time) > 780:
            self._refresh_token()

    def search_spaces(self, keywords: list[str]) -> list[SpaceInfo]:
        """Search for Spaces (both live and ended) matching keywords."""
        self._ensure_token()
        results = []
        seen_ids = set()

        for keyword in keywords[:3]:
            try:
                variables = json.dumps({
                    "query": f"{keyword} space",
                    "count": 20,
                    "product": "Top",
                })
                features = json.dumps({
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                    "responsive_web_graphql_timeline_navigation_enabled": True,
                    "spaces_2022_h2_spaces_communities_enabled": True,
                    "spaces_2022_h2_clipping_enabled": True,
                })
                r = self.session.get(
                    "https://twitter.com/i/api/graphql/nK1dw4oV3k4w5TdtcAdSww/SearchTimeline",
                    params={"variables": variables, "features": features},
                    timeout=15,
                )
                if r.status_code != 200:
                    logger.debug(f"SearchTimeline {keyword}: HTTP {r.status_code}")
                    continue

                data = r.json()
                instructions = (
                    data.get("data", {})
                    .get("search_by_raw_query", {})
                    .get("search_timeline", {})
                    .get("timeline", {})
                    .get("instructions", [])
                )
                for instruction in instructions:
                    for entry in instruction.get("entries", []):
                        content = entry.get("content", {})
                        item_content = content.get("itemContent", {})

                        # Check for AudioSpace cards
                        space_result = item_content.get("audioSpace", {})
                        if not space_result:
                            # Also check tweet card bindings for Space links
                            tweet_result = item_content.get("tweet_results", {}).get("result", {})
                            card = tweet_result.get("card", {}).get("legacy", {})
                            binding_values = card.get("binding_values", [])
                            for bv in binding_values:
                                if bv.get("key") == "card_url":
                                    url_val = bv.get("value", {}).get("string_value", "")
                                    space_match = re.search(r"/i/spaces/(\w+)", url_val)
                                    if space_match:
                                        sid = space_match.group(1)
                                        if sid not in seen_ids:
                                            seen_ids.add(sid)
                                            results.append(SpaceInfo(
                                                space_id=sid,
                                                title="(from tweet card)",
                                                host="unknown",
                                                date="",
                                                participant_count=0,
                                                state="unknown",
                                                url=f"https://twitter.com/i/spaces/{sid}",
                                                detected_via="guest_token_card",
                                            ))
                            continue

                        meta = space_result.get("metadata", {})
                        sid = meta.get("rest_id", "")
                        if not sid or sid in seen_ids:
                            continue
                        seen_ids.add(sid)

                        creator = (
                            meta.get("creator_results", {})
                            .get("result", {})
                            .get("legacy", {})
                            .get("screen_name", "unknown")
                        )
                        state = meta.get("state", "").lower()
                        results.append(SpaceInfo(
                            space_id=sid,
                            title=meta.get("title", ""),
                            host=creator,
                            date=meta.get("started_at", ""),
                            participant_count=meta.get("total_live_listeners", 0),
                            state="ended" if state in ("ended", "timedout") else state,
                            url=f"https://twitter.com/i/spaces/{sid}",
                            replay_available=state in ("ended", "timedout"),
                            detected_via="guest_token",
                        ))
            except Exception as e:
                logger.debug(f"search_spaces({keyword}): {e}")

        return results

    def get_space_details(self, space_id: str) -> Optional[dict]:
        """Get detailed metadata for a specific Space."""
        self._ensure_token()
        try:
            variables = json.dumps({
                "id": space_id,
                "isMetatagsQuery": False,
                "withReplays": True,
                "withListeners": True,
            })
            r = self.session.get(
                "https://twitter.com/i/api/graphql/xVEgTJ5D2lCMBDerNuMSIg/AudioSpaceById",
                params={"variables": variables},
                timeout=15,
            )
            if r.status_code != 200:
                return None
            return r.json().get("data", {}).get("audioSpace", {})
        except Exception as e:
            logger.debug(f"get_space_details({space_id}): {e}")
            return None


# ─── yt-dlp metadata fallback ───────────────────────────────────────────────

def ytdlp_find_spaces(account: str) -> list[SpaceInfo]:
    """Use yt-dlp to check an account's Spaces (works for some ended Spaces)."""
    import subprocess
    results = []
    try:
        # yt-dlp can extract Space info from Twitter URLs
        proc = subprocess.run(
            [
                "yt-dlp", "--flat-playlist", "--dump-json",
                f"https://twitter.com/{account}/spaces",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return []
        for line in proc.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                info = json.loads(line)
                sid = info.get("id", "")
                # Parse upload_date — yt-dlp returns YYYYMMDD format
                raw = info.get("upload_date", "")
                if raw:
                    if len(raw) == 8 and raw.isdigit():
                        dt = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)
                        date_str = dt.isoformat()
                    else:
                        date_str = raw
                else:
                    date_str = ""
                results.append(SpaceInfo(
                    space_id=sid,
                    title=info.get("title", ""),
                    host=account,
                    date=date_str,
                    participant_count=0,
                    state="ended",
                    url=info.get("url", f"https://twitter.com/i/spaces/{sid}"),
                    replay_available=True,
                    detected_via="yt-dlp",
                ))
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.debug(f"ytdlp_find_spaces({account}): {e}")
    return results


# ─── Unified scraper ────────────────────────────────────────────────────────

class XSpacesScraper:
    """
    Finds recent Bitcoin X Spaces from target accounts.
    Runs all sources (API v2, Guest Token, yt-dlp) and unions results.
    Processed-ID tracking backed by SpaceStateDB (injected_at column).
    """

    def __init__(self):
        from x_spaces_scraper.spaces_state import SpaceStateDB
        bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
        self.api_scraper = TwitterAPIv2Scraper(bearer) if bearer else None
        self.guest_scraper = GuestTokenScraper()
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.db = SpaceStateDB()

    def _load_processed(self) -> set[str]:
        """Load set of already-processed Space IDs from DB."""
        return self.db.get_injected_ids()

    def mark_processed(self, space_id: str):
        """Mark a space as injected/processed in the DB."""
        self.db.mark(space_id, "injected")

    def find_spaces(self, skip_processed: bool = True) -> list[SpaceInfo]:
        """
        Find recent Bitcoin X Spaces. Returns list of SpaceInfo,
        filtering out already-processed ones if skip_processed=True.
        Always runs all three sources and unions results (deduplicated by space_id).
        """
        processed = self._load_processed() if skip_processed else set()
        all_spaces: dict[str, SpaceInfo] = {}  # keyed by space_id for dedup

        # Source 1: Twitter API v2 (always run if available)
        if self.api_scraper:
            logger.info("Searching via Twitter API v2...")
            for kw in SPACE_KEYWORDS[:2]:
                for space in self.api_scraper.search_spaces(kw, state="all"):
                    if space.space_id not in processed and space.space_id not in all_spaces:
                        all_spaces[space.space_id] = space

        # Source 2: Guest Token GraphQL (always run, even if API found results)
        logger.info("Searching via Guest Token GraphQL...")
        for space in self.guest_scraper.search_spaces(SPACE_KEYWORDS):
            if space.space_id not in processed and space.space_id not in all_spaces:
                all_spaces[space.space_id] = space

        # Source 3: yt-dlp (always run for target accounts)
        logger.info("Trying yt-dlp metadata for target accounts...")
        for account in TARGET_ACCOUNTS:
            for space in ytdlp_find_spaces(account):
                if space.space_id not in processed and space.space_id not in all_spaces:
                    all_spaces[space.space_id] = space

        # Filter to last 7 days — handle both ISO and YYYYMMDD formats
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent = []
        for s in all_spaces.values():
            if s.date:
                try:
                    raw = s.date
                    if len(raw) == 8 and raw.isdigit():
                        dt = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)
                    else:
                        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    if dt < cutoff:
                        continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"Cannot parse date for {s.space_id}: {s.date!r} — excluding")
                    continue  # EXCLUDE undatable spaces, never silently include them
            recent.append(s)

        logger.info(f"Found {len(recent)} spaces ({len(processed)} previously processed)")
        return recent


# ─── Space Tap: Discovery + Download + Clip Extraction ─────────────────────

CACHE_DIR = Path(__file__).parent / "cache"


def discover_recent_spaces(max_results: int = 10) -> list[dict]:
    """Search Twitter API v2 for recent tweets linking to Bitcoin X Spaces.

    Uses GET /2/tweets/search/recent with spaces-related query.
    Returns list sorted by follower_count descending.
    Results cached per space_id with 6-hour TTL.
    """
    bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if not bearer:
        logger.warning("TWITTER_BEARER_TOKEN not set — cannot discover spaces")
        return []

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache first — return cached results if under 6h old
    cache_index = CACHE_DIR / "discovery_cache.json"
    if cache_index.exists():
        try:
            cached = json.loads(cache_index.read_text())
            if time.time() - cached.get("fetched_at", 0) < 6 * 3600:
                logger.info(f"Using cached discovery ({len(cached['spaces'])} spaces)")
                return cached["spaces"]
        except (json.JSONDecodeError, KeyError):
            pass

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {bearer}"

    try:
        r = session.get(
            "https://api.twitter.com/2/tweets/search/recent",
            params={
                "query": "bitcoin has:spaces lang:en -is:retweet",
                "tweet.fields": "author_id,created_at,entities,public_metrics",
                "expansions": "attachments.media_keys,author_id",
                "user.fields": "username,profile_image_url,public_metrics",
                "max_results": min(max_results, 100),
            },
            timeout=15,
        )
        if r.status_code == 429:
            logger.warning("Twitter API rate limited — using cached/empty")
            return []
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.error(f"Twitter search failed: {e}")
        return []

    tweets = data.get("data", [])
    users_list = data.get("includes", {}).get("users", [])
    users_map = {u["id"]: u for u in users_list}

    results = []
    seen_space_ids = set()

    for tweet in tweets:
        # Extract space URLs from entities
        urls = (tweet.get("entities") or {}).get("urls", [])
        for url_obj in urls:
            expanded = url_obj.get("expanded_url", "") or url_obj.get("url", "")
            match = re.search(r"twitter\.com/i/spaces/(\w+)", expanded)
            if not match:
                match = re.search(r"x\.com/i/spaces/(\w+)", expanded)
            if not match:
                continue

            space_id = match.group(1)
            if space_id in seen_space_ids:
                continue
            seen_space_ids.add(space_id)

            author_id = tweet.get("author_id", "")
            user = users_map.get(author_id, {})
            handle = user.get("username", "unknown")
            name = user.get("name", handle)
            profile_img = user.get("profile_image_url", "")
            # Get higher-res profile image (replace _normal with _400x400)
            if profile_img:
                profile_img = profile_img.replace("_normal", "_400x400")
            follower_count = user.get("public_metrics", {}).get("followers_count", 0)

            entry = {
                "space_id": space_id,
                "host_handle": handle,
                "host_name": name,
                "host_profile_image_url": profile_img,
                "tweet_text": tweet.get("text", ""),
                "follower_count": follower_count,
                "created_at": tweet.get("created_at", ""),
            }
            results.append(entry)

            # Cache individual space meta
            space_cache = CACHE_DIR / space_id
            space_cache.mkdir(parents=True, exist_ok=True)
            meta_path = space_cache / "meta.json"
            meta_path.write_text(json.dumps(entry, indent=2))

    # Sort by follower_count descending
    results.sort(key=lambda x: x.get("follower_count", 0), reverse=True)

    # Cache the discovery results
    cache_index.write_text(json.dumps({
        "spaces": results,
        "fetched_at": time.time(),
    }, indent=2))

    logger.info(f"Discovered {len(results)} spaces with space links")
    return results


def download_and_transcribe_space(space_id: str, host_handle: str,
                                   host_profile_image_url: str = "") -> Optional[dict]:
    """Download a Space's audio, transcribe it, and extract best 15-30s clips.

    Returns clips dict or None if download/transcription fails.
    """
    space_dir = CACHE_DIR / space_id
    space_dir.mkdir(parents=True, exist_ok=True)
    clips_path = space_dir / "clips.json"

    # Return cached clips if recent (6h TTL)
    if clips_path.exists():
        try:
            cached = json.loads(clips_path.read_text())
            transcribed_at = cached.get("transcribed_at", "")
            if transcribed_at:
                dt = datetime.fromisoformat(transcribed_at)
                if (datetime.now(timezone.utc) - dt).total_seconds() < 6 * 3600:
                    logger.info(f"Using cached clips for {space_id}")
                    return cached
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 1: Download audio via yt-dlp
    space_url = f"https://twitter.com/i/spaces/{space_id}"
    audio_pattern = str(space_dir / "audio.%(ext)s")
    audio_path = space_dir / "audio.m4a"

    if not audio_path.exists():
        logger.info(f"Downloading space {space_id} via yt-dlp...")
        try:
            result = subprocess.run(
                ["yt-dlp", "-f", "bestaudio", "-o", audio_pattern, space_url],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                logger.warning(f"yt-dlp failed for {space_id}: {result.stderr[:200]}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning(f"yt-dlp timeout for {space_id}")
            return None
        except Exception as e:
            logger.warning(f"yt-dlp error for {space_id}: {e}")
            return None

        # Find the actual downloaded file (extension may vary)
        for ext in ("m4a", "mp4", "webm", "ogg", "opus"):
            candidate = space_dir / f"audio.{ext}"
            if candidate.exists():
                if ext != "m4a":
                    # Convert to m4a
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(candidate), "-c:a", "aac",
                         "-ar", "48000", str(audio_path)],
                        capture_output=True, timeout=120,
                    )
                    candidate.unlink(missing_ok=True)
                break

    if not audio_path.exists():
        logger.warning(f"No audio file found for {space_id}")
        return None

    # Step 2: Transcribe with faster-whisper
    logger.info(f"Transcribing {space_id}...")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cuda", compute_type="float16")
        segments_iter, info = model.transcribe(str(audio_path), language="en")
        transcript_segments = []
        for seg in segments_iter:
            transcript_segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })
    except Exception as e:
        logger.error(f"Transcription failed for {space_id}: {e}")
        return None

    if not transcript_segments:
        logger.warning(f"Empty transcript for {space_id}")
        return None

    # Step 3: Score sliding windows and extract best clips
    sys_path_added = False
    try:
        import sys
        pp_root = Path(__file__).parent.parent
        vp3_utils = pp_root / "video_pipeline_v3" / "utils"
        if str(vp3_utils) not in sys.path:
            sys.path.insert(0, str(vp3_utils))
            sys_path_added = True
        from spaces_pipeline import score_transcript
    except ImportError:
        logger.warning("score_transcript not available — using fallback scoring")
        score_transcript = None

    full_text = " ".join(s["text"] for s in transcript_segments)
    total_duration = transcript_segments[-1]["end"] if transcript_segments else 0

    # Sliding window: try every position, score each 15s window
    scored_windows = []
    step = 5.0  # 5s step
    window_size = 15.0  # 15s minimum clip

    t = 0.0
    while t + window_size <= total_duration:
        window_end = min(t + 30.0, total_duration)  # up to 30s
        window_segs = [s for s in transcript_segments
                       if s["end"] > t and s["start"] < window_end]
        window_text = " ".join(s["text"] for s in window_segs)

        if len(window_text.split()) < 10:
            t += step
            continue

        if score_transcript:
            score = score_transcript({"transcript": window_text})
        else:
            # Fallback: word count + keyword density
            wc = len(window_text.split())
            score = min(wc // 3, 50)

        scored_windows.append({
            "start_sec": round(t, 2),
            "end_sec": round(window_end, 2),
            "text": window_text,
            "score": score,
        })
        t += step

    # Take top 5 non-overlapping windows
    scored_windows.sort(key=lambda x: x["score"], reverse=True)
    top_clips = []
    for w in scored_windows:
        if len(top_clips) >= 5:
            break
        # Check overlap with already selected clips
        overlaps = False
        for tc in top_clips:
            if w["start_sec"] < tc["end_sec"] and w["end_sec"] > tc["start_sec"]:
                overlaps = True
                break
        if not overlaps:
            top_clips.append(w)

    # Step 4: Extract audio for each clip
    for i, clip in enumerate(top_clips):
        clip_path = space_dir / f"clip_{i}.m4a"
        duration = clip["end_sec"] - clip["start_sec"]
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(clip["start_sec"]),
                 "-i", str(audio_path), "-t", str(duration),
                 "-c:a", "aac", "-ar", "48000", str(clip_path)],
                capture_output=True, timeout=30,
            )
            clip["clip_path"] = str(clip_path)
        except Exception as e:
            logger.warning(f"Clip extraction failed for clip {i}: {e}")
            clip["clip_path"] = ""

    # Step 5: Fetch and resize host profile picture
    profile_path = space_dir / "profile.jpg"
    if host_profile_image_url and not profile_path.exists():
        try:
            resp = requests.get(host_profile_image_url, timeout=10)
            if resp.status_code == 200:
                raw_path = space_dir / "profile_raw.jpg"
                raw_path.write_bytes(resp.content)
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(raw_path),
                     "-vf", "scale=200:200", str(profile_path)],
                    capture_output=True, timeout=15,
                )
                raw_path.unlink(missing_ok=True)
        except Exception as e:
            logger.debug(f"Profile picture fetch failed: {e}")

    # Step 6: Save clips.json
    result = {
        "space_id": space_id,
        "host_handle": host_handle,
        "host_name": host_handle,
        "host_profile_image": str(profile_path) if profile_path.exists() else "",
        "clips": top_clips,
        "transcribed_at": datetime.now(timezone.utc).isoformat(),
    }
    clips_path.write_text(json.dumps(result, indent=2))

    logger.info(f"Space {space_id}: {len(top_clips)} clips extracted")
    return result


def get_best_space_clips(max_clips: int = 4) -> Optional[dict]:
    """Top-level function for daily_run.py — discover, download, rank clips.

    Returns {clips: [...], spaces_count: N} or None.
    """
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    spaces = discover_recent_spaces(max_results=10)
    if not spaces:
        logger.info("No spaces discovered")
        return None

    # Process top 3 by follower count
    all_clips = []
    spaces_processed = 0

    for space_meta in spaces[:3]:
        space_id = space_meta["space_id"]
        handle = space_meta["host_handle"]
        profile_url = space_meta.get("host_profile_image_url", "")

        result = download_and_transcribe_space(space_id, handle, profile_url)
        if result and result.get("clips"):
            spaces_processed += 1
            for clip in result["clips"]:
                clip["host_handle"] = handle
                clip["host_name"] = space_meta.get("host_name", handle)
                clip["host_profile_image"] = result.get("host_profile_image", "")
                clip["space_id"] = space_id
                all_clips.append(clip)

    if not all_clips:
        return None

    # Take top max_clips by score across all spaces
    all_clips.sort(key=lambda x: x.get("score", 0), reverse=True)
    best = all_clips[:max_clips]

    return {
        "clips": best,
        "spaces_count": spaces_processed,
    }


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    scraper = XSpacesScraper()
    spaces = scraper.find_spaces(skip_processed=False)
    if spaces:
        print(f"\nFound {len(spaces)} space(s):")
        for s in spaces:
            print(f"  [{s.detected_via}] @{s.host}: {s.title or '(no title)'}")
            print(f"    ID: {s.space_id} | State: {s.state} | Date: {s.date}")
            print(f"    URL: {s.url}")
    else:
        print("\nNo Bitcoin X Spaces found.")
