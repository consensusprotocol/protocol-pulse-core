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
                results.append(SpaceInfo(
                    space_id=sid,
                    title=info.get("title", ""),
                    host=account,
                    date=info.get("upload_date", ""),
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
    Tries API v2 → Guest Token → yt-dlp in order.
    """

    def __init__(self):
        bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
        self.api_scraper = TwitterAPIv2Scraper(bearer) if bearer else None
        self.guest_scraper = GuestTokenScraper()
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)

    def _load_processed(self) -> set[str]:
        """Load set of already-processed Space IDs."""
        processed_file = self.cache_dir / "processed_ids.json"
        if processed_file.exists():
            try:
                return set(json.loads(processed_file.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
        return set()

    def _save_processed(self, ids: set[str]):
        processed_file = self.cache_dir / "processed_ids.json"
        processed_file.write_text(json.dumps(sorted(ids), indent=2))

    def mark_processed(self, space_id: str):
        ids = self._load_processed()
        ids.add(space_id)
        self._save_processed(ids)

    def find_spaces(self, skip_processed: bool = True) -> list[SpaceInfo]:
        """
        Find recent Bitcoin X Spaces. Returns list of SpaceInfo,
        filtering out already-processed ones if skip_processed=True.
        """
        processed = self._load_processed() if skip_processed else set()
        all_spaces: list[SpaceInfo] = []
        seen_ids: set[str] = set()

        # 1. Twitter API v2
        if self.api_scraper:
            logger.info("Searching via Twitter API v2...")
            for kw in SPACE_KEYWORDS[:2]:
                for space in self.api_scraper.search_spaces(kw, state="all"):
                    if space.space_id not in seen_ids and space.space_id not in processed:
                        seen_ids.add(space.space_id)
                        all_spaces.append(space)

        # 2. Guest Token GraphQL search
        if not all_spaces:
            logger.info("Searching via Guest Token GraphQL...")
            for space in self.guest_scraper.search_spaces(SPACE_KEYWORDS):
                if space.space_id not in seen_ids and space.space_id not in processed:
                    seen_ids.add(space.space_id)
                    all_spaces.append(space)

        # 3. yt-dlp fallback (check a few target accounts)
        if not all_spaces:
            logger.info("Trying yt-dlp metadata fallback for target accounts...")
            for account in TARGET_ACCOUNTS[:5]:
                for space in ytdlp_find_spaces(account):
                    if space.space_id not in seen_ids and space.space_id not in processed:
                        seen_ids.add(space.space_id)
                        all_spaces.append(space)

        # Filter to last 7 days where possible
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent = []
        for s in all_spaces:
            if s.date:
                try:
                    dt = datetime.fromisoformat(s.date.replace("Z", "+00:00"))
                    if dt < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass
            recent.append(s)

        logger.info(f"Found {len(recent)} spaces ({len(processed)} previously processed)")
        return recent


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
