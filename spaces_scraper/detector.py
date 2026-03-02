"""
detector.py — X Spaces Detector
Tries three approaches in order:
  1. X API v2 (if bearer token exists)
  2. Guest Token + GraphQL (no auth required)
  3. Playwright headless scraper (fallback)
"""

import asyncio
import json
import logging
import re
import time
import argparse
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


@dataclass
class LiveSpace:
    space_id: str
    host_username: str
    title: str
    participant_count: int
    started_at: str
    url: str
    hls_url: Optional[str] = None
    detected_via: str = "unknown"
    detected_at: float = field(default_factory=time.time)

    def to_dict(self):
        return asdict(self)


# ─── Option A: X API v2 ─────────────────────────────────────────────────────

class XAPIDetector:
    """Uses official X API v2 Spaces search endpoint."""

    def __init__(self, bearer_token: str):
        self.bearer = bearer_token
        self.base = "https://api.twitter.com/2"

    def search_spaces(self, query: str = "bitcoin") -> list[LiveSpace]:
        """Search for live Bitcoin spaces via X API v2."""
        try:
            r = requests.get(
                f"{self.base}/spaces/search",
                headers={"Authorization": f"Bearer {self.bearer}"},
                params={
                    "query": query,
                    "state": "live",
                    "space.fields": "id,title,host_ids,participant_count,started_at,state",
                    "expansions": "host_ids",
                    "user.fields": "username",
                },
                timeout=10,
            )
            if r.status_code == 403:
                logger.warning("X API v2: 403 Forbidden — bearer token lacks Spaces access")
                return []
            r.raise_for_status()
            data = r.json()
            spaces = data.get("data", [])
            users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}

            results = []
            for s in spaces:
                host_id = (s.get("host_ids") or [""])[0]
                results.append(LiveSpace(
                    space_id=s["id"],
                    host_username=users.get(host_id, "unknown"),
                    title=s.get("title", ""),
                    participant_count=s.get("participant_count", 0),
                    started_at=s.get("started_at", ""),
                    url=f"https://twitter.com/i/spaces/{s['id']}",
                    detected_via="x_api_v2",
                ))
            return results
        except Exception as e:
            logger.error(f"XAPIDetector error: {e}")
            return []


# ─── Option B: Guest Token + AudioSpace GraphQL ─────────────────────────────

GRAPHQL_HEADERS_BASE = {
    "Authorization": f"Bearer {config.X_PUBLIC_BEARER}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "X-Twitter-Active-User": "yes",
    "X-Twitter-Client-Language": "en",
    "Origin": "https://twitter.com",
    "Referer": "https://twitter.com/",
}

# GraphQL query IDs (these change periodically; update if requests fail)
AUDIO_SPACE_BY_ID_QUERY = "xVEgTJ5D2lCMBDerNuMSIg"
USER_BY_SCREEN_NAME_QUERY = "oUZZZ8Oddwxs8Ln2Tos-LA"


class GuestTokenDetector:
    """
    Uses X's guest authentication flow to poll user timelines/spaces
    without requiring account credentials.
    """

    def __init__(self):
        self.guest_token: Optional[str] = None
        self.guest_token_fetched_at: float = 0
        self.session = requests.Session()
        self.session.headers.update(GRAPHQL_HEADERS_BASE)

    def _refresh_guest_token(self) -> bool:
        """Fetch a fresh guest token (valid ~15 minutes)."""
        try:
            r = self.session.post(
                "https://api.twitter.com/1.1/guest/activate.json",
                timeout=10,
            )
            r.raise_for_status()
            self.guest_token = r.json()["guest_token"]
            self.guest_token_fetched_at = time.time()
            self.session.headers["X-Guest-Token"] = self.guest_token
            logger.info(f"Guest token refreshed: {self.guest_token[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Guest token fetch failed: {e}")
            return False

    def _ensure_token(self):
        age = time.time() - self.guest_token_fetched_at
        if not self.guest_token or age > 800:  # refresh every ~13 min
            self._refresh_guest_token()

    def _get_user_id(self, screen_name: str) -> Optional[str]:
        """Resolve @username → numeric user ID."""
        self._ensure_token()
        try:
            variables = json.dumps({
                "screen_name": screen_name,
                "withSafetyModeUserFields": True,
            })
            features = json.dumps({
                "hidden_profile_likes_enabled": False,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": False,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
            })
            r = self.session.get(
                "https://twitter.com/i/api/graphql/oUZZZ8Oddwxs8Ln2Tos-LA/UserByScreenName",
                params={"variables": variables, "features": features},
                timeout=10,
            )
            if r.status_code in (401, 403):
                logger.debug(f"UserByScreenName {screen_name}: {r.status_code}")
                return None
            data = r.json()
            user = data.get("data", {}).get("user", {}).get("result", {})
            return user.get("rest_id")
        except Exception as e:
            logger.debug(f"_get_user_id({screen_name}): {e}")
            return None

    def _check_user_space(self, screen_name: str) -> Optional[LiveSpace]:
        """Check if a user is currently hosting a live Space."""
        self._ensure_token()
        try:
            # Use the AudioSpaceByCreatorId or search user's pinned/banner Space
            variables = json.dumps({"screenName": screen_name})
            r = self.session.get(
                "https://twitter.com/i/api/graphql/xVEgTJ5D2lCMBDerNuMSIg/AudioSpaceSearch",
                params={"variables": variables},
                timeout=10,
            )
            # This endpoint may 404 — just try and move on
            if r.status_code == 200:
                data = r.json()
                logger.debug(f"AudioSpaceSearch for {screen_name}: {json.dumps(data)[:200]}")
        except Exception:
            pass
        return None

    def search_live_spaces(self, keywords: list[str]) -> list[LiveSpace]:
        """Search for live audio spaces matching given keywords."""
        self._ensure_token()
        results = []
        for keyword in keywords[:2]:  # limit to avoid rate limiting
            try:
                variables = json.dumps({
                    "query": keyword,
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
                    timeout=10,
                )
                if r.status_code != 200:
                    logger.debug(f"SearchTimeline {keyword}: HTTP {r.status_code}")
                    continue

                data = r.json()
                # Walk timeline entries looking for AudioSpace cards
                entries = (
                    data.get("data", {})
                    .get("search_by_raw_query", {})
                    .get("search_timeline", {})
                    .get("timeline", {})
                    .get("instructions", [])
                )
                for instruction in entries:
                    for entry in instruction.get("entries", []):
                        content = entry.get("content", {})
                        item_content = content.get("itemContent", {})
                        space_result = item_content.get("audioSpace", {})
                        if space_result and space_result.get("metadata", {}).get("state") == "Running":
                            meta = space_result["metadata"]
                            results.append(LiveSpace(
                                space_id=meta.get("rest_id", ""),
                                host_username=meta.get("creator_results", {})
                                    .get("result", {}).get("legacy", {}).get("screen_name", "unknown"),
                                title=meta.get("title", ""),
                                participant_count=meta.get("participant_count", 0),
                                started_at=meta.get("started_at", ""),
                                url=f"https://twitter.com/i/spaces/{meta.get('rest_id','')}",
                                detected_via="guest_token",
                            ))
            except Exception as e:
                logger.debug(f"search_live_spaces({keyword}): {e}")

        return results

    def get_space_stream_url(self, space_id: str) -> Optional[str]:
        """Fetch the HLS stream URL for a given Space ID."""
        self._ensure_token()
        try:
            variables = json.dumps({
                "id": space_id,
                "isMetatagsQuery": False,
                "withReplays": True,
                "withListeners": True,
            })
            r = self.session.get(
                f"https://twitter.com/i/api/graphql/{AUDIO_SPACE_BY_ID_QUERY}/AudioSpaceById",
                params={"variables": variables},
                timeout=10,
            )
            if r.status_code != 200:
                return None
            data = r.json()
            audio_space = (
                data.get("data", {}).get("audioSpace", {})
            )
            media_key = (
                audio_space.get("metadata", {}).get("media_key")
                or audio_space.get("sharings", {}).get("items", [{}])[0].get("media_key")
            )
            if not media_key:
                return None

            # Fetch the actual stream location from periscope
            stream_r = self.session.get(
                "https://twitter.com/i/api/1.1/live_video_stream/status/" + media_key,
                params={"client": "web", "use_syndication_guest_id": "false", "cookie_set_host": "twitter.com"},
                timeout=10,
            )
            if stream_r.status_code != 200:
                return None
            location = stream_r.json().get("source", {}).get("location")
            return location
        except Exception as e:
            logger.debug(f"get_space_stream_url({space_id}): {e}")
            return None


# ─── Option C: Playwright Scraper ───────────────────────────────────────────

class PlaywrightDetector:
    """
    Headless Chromium scraper. Last resort if API approaches fail.
    Monitors target account pages for live Space badges and intercepts HLS URLs.
    """

    async def check_account(self, username: str) -> Optional[LiveSpace]:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-first-run",
                    ],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()

                hls_found: list[str] = []

                async def capture_hls(route, request):
                    url = request.url
                    if ("pscp.tv" in url or "periscope.tv" in url) and ".m3u8" in url:
                        hls_found.append(url)
                        logger.info(f"HLS intercepted for @{username}: {url[:80]}...")
                    await route.continue_()

                await page.route("**/*", capture_hls)

                await page.goto(f"https://twitter.com/{username}", wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)

                # Check for live Space badge
                is_live = await page.evaluate("""() => {
                    const text = document.body.innerText.toLowerCase();
                    return text.includes('live') || text.includes('listening');
                }""")

                space_url = None
                if is_live:
                    # Try to find Space link
                    links = await page.evaluate("""() => {
                        const anchors = Array.from(document.querySelectorAll('a[href*="/i/spaces/"]'));
                        return anchors.map(a => a.href);
                    }""")
                    if links:
                        space_url = links[0]
                        space_id_match = re.search(r"/i/spaces/(\w+)", space_url)
                        space_id = space_id_match.group(1) if space_id_match else ""

                        # Navigate to the Space itself to trigger HLS
                        await page.goto(space_url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(5)  # wait for stream to start

                        await browser.close()
                        return LiveSpace(
                            space_id=space_id,
                            host_username=username,
                            title="",
                            participant_count=0,
                            started_at="",
                            url=space_url,
                            hls_url=hls_found[0] if hls_found else None,
                            detected_via="playwright",
                        )

                await browser.close()
                return None
        except Exception as e:
            logger.error(f"PlaywrightDetector.check_account({username}): {e}")
            return None

    async def scan_accounts(self, accounts: list[str]) -> list[LiveSpace]:
        """Check multiple accounts concurrently (max 3 at a time)."""
        sem = asyncio.Semaphore(3)

        async def check_with_sem(acc):
            async with sem:
                return await self.check_account(acc)

        results = await asyncio.gather(*[check_with_sem(a) for a in accounts])
        return [r for r in results if r is not None]


# ─── Unified Detector ───────────────────────────────────────────────────────

class SpaceDetector:
    """
    Unified detector. Tries API → Guest Token → Playwright in order.
    Falls back gracefully when each approach is unavailable or blocked.
    """

    def __init__(self):
        self.api_detector = (
            XAPIDetector(config.TWITTER_BEARER_TOKEN)
            if config.TWITTER_BEARER_TOKEN
            else None
        )
        self.guest_detector = GuestTokenDetector()
        self.playwright_detector = PlaywrightDetector()
        self._active_spaces: dict[str, LiveSpace] = {}

    async def detect_once(self) -> list[LiveSpace]:
        """Run a single detection pass and return all currently live spaces."""
        found: list[LiveSpace] = []

        # Try X API v2 first
        if self.api_detector:
            logger.info("Trying X API v2...")
            api_results = self.api_detector.search_spaces()
            if api_results:
                logger.info(f"X API v2: found {len(api_results)} spaces")
                found.extend(api_results)

        # Try guest token
        if not found:
            logger.info("Trying guest token approach...")
            try:
                guest_results = self.guest_detector.search_live_spaces(config.SPACE_SEARCH_KEYWORDS)
                if guest_results:
                    logger.info(f"Guest token: found {len(guest_results)} spaces")
                    found.extend(guest_results)
            except Exception as e:
                logger.warning(f"Guest token approach failed: {e}")

        # Enrich found spaces with HLS stream URLs
        for space in found:
            if not space.hls_url and space.space_id:
                try:
                    hls = self.guest_detector.get_space_stream_url(space.space_id)
                    if hls:
                        space.hls_url = hls
                        logger.info(f"HLS resolved for {space.space_id}: {hls[:60]}...")
                except Exception as e:
                    logger.debug(f"HLS resolution failed for {space.space_id}: {e}")

        # Playwright fallback for target accounts (check a few)
        if not found:
            logger.info("No spaces via API/guest token — trying Playwright for target accounts...")
            try:
                # Only check first 4 accounts to keep it fast
                pw_results = await self.playwright_detector.scan_accounts(
                    config.TARGET_ACCOUNTS[:4]
                )
                if pw_results:
                    logger.info(f"Playwright: found {len(pw_results)} spaces")
                    found.extend(pw_results)
            except Exception as e:
                logger.warning(f"Playwright scan failed: {e}")

        # Update internal state
        for space in found:
            self._active_spaces[space.space_id] = space

        # Prune spaces no longer in found list (they ended)
        current_ids = {s.space_id for s in found}
        ended = [sid for sid in self._active_spaces if sid not in current_ids]
        for sid in ended:
            logger.info(f"Space ended: {sid}")
            del self._active_spaces[sid]

        return found

    async def run_poll_loop(self, callback=None):
        """Continuously poll for live spaces."""
        logger.info(f"SpaceDetector polling every {config.DETECTOR_POLL_INTERVAL}s")
        while True:
            try:
                spaces = await self.detect_once()
                logger.info(f"Poll result: {len(spaces)} live space(s)")
                if callback:
                    await callback(spaces)
            except Exception as e:
                logger.error(f"Poll loop error: {e}")
            await asyncio.sleep(config.DETECTOR_POLL_INTERVAL)

    @property
    def active_spaces(self) -> list[LiveSpace]:
        return list(self._active_spaces.values())


# ─── CLI Test ────────────────────────────────────────────────────────────────

async def _test():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("=== SpaceDetector test ===")
    detector = SpaceDetector()
    spaces = await detector.detect_once()
    if spaces:
        print(f"\nFound {len(spaces)} live space(s):")
        for s in spaces:
            print(f"  [{s.detected_via}] @{s.host_username}: {s.title or '(no title)'}")
            print(f"    URL: {s.url}")
            print(f"    HLS: {s.hls_url or 'not resolved'}")
            print(f"    Participants: {s.participant_count}")
    else:
        print("\nNo live Bitcoin spaces found at this time.")
    return spaces


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        asyncio.run(_test())
