# services/signal_feeds.py
"""
Async external data feed fetchers for the Convergence Detection engine.

ALL fetchers are async and require a shared aiohttp.ClientSession passed
from sentinel.py. No synchronous HTTP calls exist in this file.

Circuit breaker: after 3 consecutive failures on any feed, that feed is
marked DEGRADED and skipped for CIRCUIT_BREAKER_COOLDOWN_SECONDS.
"""

import os
import logging
import re
import time
from typing import Optional, Dict, Any

import aiohttp

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER_THRESHOLD = 3          # failures before DEGRADED
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 300  # 5 minutes cooldown


class SignalFeeds:
    """
    All external data fetchers. Requires a live aiohttp.ClientSession.
    Session is owned by sentinel.py and shared — do NOT create sessions here.
    Config is a ConvergenceConfig instance.
    """

    def __init__(self, session: aiohttp.ClientSession, config):
        self.session = session
        self.config = config
        # Per-feed failure counters for circuit breaker
        self._failure_counts: Dict[str, int] = {}
        self._degraded_until: Dict[str, float] = {}

    # ── Circuit breaker helpers ───────────────────────────────────────────────

    def _is_degraded(self, feed_name: str) -> bool:
        return time.monotonic() < self._degraded_until.get(feed_name, 0)

    def _record_success(self, feed_name: str) -> None:
        self._failure_counts[feed_name] = 0
        self._degraded_until.pop(feed_name, None)

    def _record_failure(self, feed_name: str) -> None:
        count = self._failure_counts.get(feed_name, 0) + 1
        self._failure_counts[feed_name] = count
        if count >= CIRCUIT_BREAKER_THRESHOLD:
            cooldown_until = time.monotonic() + CIRCUIT_BREAKER_COOLDOWN_SECONDS
            self._degraded_until[feed_name] = cooldown_until
            logger.warning(
                f"Feed '{feed_name}' circuit breaker OPEN after {count} consecutive failures. "
                f"Cooldown for {CIRCUIT_BREAKER_COOLDOWN_SECONDS}s."
            )

    # ── Feed 1: VIX ───────────────────────────────────────────────────────────

    async def fetch_vix(self) -> Optional[float]:
        """
        VIX with primary (Yahoo Finance) and fallback (Alpha Vantage).
        content_type=None handles Yahoo's occasional text/html responses.
        """
        feed_name = "vix"
        if self._is_degraded(feed_name):
            logger.debug(f"Feed '{feed_name}' is degraded — skipping.")
            return None

        timeout_s = self.config.get("feeds", "vix", "timeout_seconds") or 8
        timeout = aiohttp.ClientTimeout(total=timeout_s)

        # Primary: Yahoo Finance
        primary_url = self.config.get("feeds", "vix", "primary_url")
        try:
            async with self.session.get(primary_url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    result = data.get("chart", {}).get("result") or []
                    if result:
                        price = result[0].get("meta", {}).get("regularMarketPrice")
                        if price is not None:
                            self._record_success(feed_name)
                            return float(price)
                logger.warning(f"VIX primary returned status {resp.status}")
        except Exception as e:
            logger.warning(f"VIX primary (Yahoo) failed: {e}")

        # Fallback: Alpha Vantage
        try:
            key = os.environ.get("ALPHA_VANTAGE_KEY")
            if not key:
                logger.error("VIX fallback unavailable: ALPHA_VANTAGE_KEY env var not set.")
                self._record_failure(feed_name)
                return None
            fallback_url = (
                f"https://www.alphavantage.co/query"
                f"?function=GLOBAL_QUOTE&symbol=VIX&apikey={key}"
            )
            fallback_timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(fallback_url, timeout=fallback_timeout) as resp:
                data = await resp.json(content_type=None)
                price = data.get("Global Quote", {}).get("05. price")
                if price is not None:
                    self._record_success(feed_name)
                    return float(price)
        except Exception as e:
            logger.warning(f"VIX fallback (Alpha Vantage) failed: {e}")

        self._record_failure(feed_name)
        return None

    # ── Feed 2: SPY ───────────────────────────────────────────────────────────

    async def fetch_spy(self) -> Optional[float]:
        """SPY price. Same Yahoo/Alpha Vantage dual-source pattern as VIX."""
        feed_name = "spy"
        if self._is_degraded(feed_name):
            return None

        timeout_s = self.config.get("feeds", "spy", "timeout_seconds") or 8
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        primary_url = self.config.get("feeds", "spy", "primary_url")

        try:
            async with self.session.get(primary_url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    result = data.get("chart", {}).get("result") or []
                    if result:
                        price = result[0].get("meta", {}).get("regularMarketPrice")
                        if price is not None:
                            self._record_success(feed_name)
                            return float(price)
                logger.warning(f"SPY primary returned status {resp.status}")
        except Exception as e:
            logger.warning(f"SPY primary (Yahoo) failed: {e}")

        try:
            key = os.environ.get("ALPHA_VANTAGE_KEY")
            if not key:
                logger.error("SPY fallback unavailable: ALPHA_VANTAGE_KEY not set.")
                self._record_failure(feed_name)
                return None
            fallback_url = (
                f"https://www.alphavantage.co/query"
                f"?function=GLOBAL_QUOTE&symbol=SPY&apikey={key}"
            )
            fallback_timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(fallback_url, timeout=fallback_timeout) as resp:
                data = await resp.json(content_type=None)
                price = data.get("Global Quote", {}).get("05. price")
                if price is not None:
                    self._record_success(feed_name)
                    return float(price)
        except Exception as e:
            logger.warning(f"SPY fallback (Alpha Vantage) failed: {e}")

        self._record_failure(feed_name)
        return None

    # ── Feed 3: WTI Crude Oil ─────────────────────────────────────────────────

    async def fetch_wti(self) -> Optional[float]:
        """WTI crude spot price via EIA API."""
        feed_name = "wti"
        if self._is_degraded(feed_name):
            return None

        timeout_s = self.config.get("feeds", "wti", "timeout_seconds") or 10
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        url = self.config.get("feeds", "wti", "primary_url")
        api_key = os.environ.get("EIA_API_KEY", "")

        try:
            params = {
                "api_key": api_key,
                "frequency": "daily",
                "data[]": "value",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 1,
            }
            async with self.session.get(url, params=params, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    rows = (data.get("response", {}).get("data") or [])
                    if rows:
                        self._record_success(feed_name)
                        return float(rows[0].get("value", 0))
                logger.warning(f"WTI fetch returned status {resp.status}")
        except Exception as e:
            logger.warning(f"WTI fetch failed: {e}")

        self._record_failure(feed_name)
        return None

    # ── Feed 4: Deribit BTC Perpetual Funding Rate ────────────────────────────

    async def fetch_deribit_funding(self) -> Optional[float]:
        """Deribit BTC-PERPETUAL 8h funding rate."""
        feed_name = "deribit_funding"
        if self._is_degraded(feed_name):
            return None

        timeout_s = self.config.get("feeds", "deribit_funding", "timeout_seconds") or 5
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        url = self.config.get("feeds", "deribit_funding", "primary_url")

        try:
            params = {
                "instrument_name": "BTC-PERPETUAL",
                "start_timestamp": int((time.time() - 28800) * 1000),
                "end_timestamp": int(time.time() * 1000),
            }
            async with self.session.get(url, params=params, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    result = data.get("result", {})
                    rate = result.get("current_funding") if isinstance(result, dict) else None
                    if rate is not None:
                        self._record_success(feed_name)
                        return float(rate)
                logger.warning(f"Deribit funding fetch returned status {resp.status}")
        except Exception as e:
            logger.warning(f"Deribit funding fetch failed: {e}")

        self._record_failure(feed_name)
        return None

    # ── Feed 5: Stablecoin Flows (DeFi Llama) ────────────────────────────────

    async def fetch_stablecoin_flows(self) -> Optional[Dict[str, Any]]:
        """Stablecoin net flow data via DeFi Llama."""
        feed_name = "stablecoin_flows"
        if self._is_degraded(feed_name):
            return None

        timeout_s = self.config.get("feeds", "stablecoin_flows", "timeout_seconds") or 15
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        url = (
            os.environ.get("STABLECOIN_FEED_URL")
            or self.config.get("feeds", "stablecoin_flows", "primary_url")
            or "https://stablecoins.llama.fi/stablecoinchains"
        )

        try:
            async with self.session.get(url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    self._record_success(feed_name)
                    return data
                logger.warning(f"Stablecoin flows fetch returned status {resp.status}")
        except Exception as e:
            logger.warning(f"Stablecoin flows fetch failed: {e}")

        self._record_failure(feed_name)
        return None

    # ── Feed 6: HodlHodl P2P Premium ─────────────────────────────────────────

    async def fetch_hodlhodl_premium(self) -> Optional[float]:
        """HodlHodl P2P BTC/USD offer spread as proxy for OTC premium."""
        feed_name = "hodlhodl"
        if self._is_degraded(feed_name):
            return None

        timeout_s = self.config.get("feeds", "hodlhodl", "timeout_seconds") or 10
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        url = self.config.get("feeds", "hodlhodl", "primary_url")

        try:
            params = {"filters[currency_code]": "USD", "filters[side]": "sell"}
            async with self.session.get(url, params=params, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    offers = data.get("offers", [])
                    if offers:
                        prices = [
                            float(o["price"]["amount"])
                            for o in offers
                            if o.get("price", {}).get("amount")
                        ]
                        if prices:
                            self._record_success(feed_name)
                            return sum(prices) / len(prices)
                logger.warning(f"HodlHodl fetch returned status {resp.status}")
        except Exception as e:
            logger.warning(f"HodlHodl fetch failed: {e}")

        self._record_failure(feed_name)
        return None

    # ── Feed 7: RSS News Sentiment ────────────────────────────────────────────

    async def fetch_rss_news(self) -> Optional[Dict[str, Any]]:
        """Fetches configured RSS feeds and returns title list for sentiment scoring."""
        feed_name = "rss_news"
        if self._is_degraded(feed_name):
            return None

        timeout_s = self.config.get("feeds", "rss_news", "timeout_seconds") or 8
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        feed_urls = self.config.get("feeds", "rss_news", "feeds") or []

        all_titles = []
        any_success = False

        for feed_url in feed_urls:
            try:
                async with self.session.get(feed_url, timeout=timeout) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        titles = re.findall(r"<title>(.*?)</title>", text, re.DOTALL)
                        all_titles.extend(titles[:20])  # cap per feed
                        any_success = True
                    else:
                        logger.warning(f"RSS feed {feed_url} returned status {resp.status}")
            except Exception as e:
                # Per-feed isolation — one failure does not abort all feeds
                logger.warning(f"RSS feed {feed_url} failed: {e}")

        if any_success:
            self._record_success(feed_name)
            return {"titles": all_titles, "feed_count": len(feed_urls)}

        self._record_failure(feed_name)
        return None

    # ── Feed 8: Custodian Wallet Flows ────────────────────────────────────────

    async def fetch_custodian_wallet_flows(self) -> Optional[Dict[str, Any]]:
        """On-chain BTC flow data for known ETF custodian wallets."""
        feed_name = "custodian_wallet_flows"
        if self._is_degraded(feed_name):
            return None

        timeout_s = self.config.get("feeds", "custodian_wallet_flows", "timeout_seconds") or 20
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        url = (
            os.environ.get("CUSTODIAN_FEED_URL")
            or self.config.get("feeds", "custodian_wallet_flows", "primary_url")
        )

        if not url:
            logger.warning("Custodian wallet flows: no URL configured. Set CUSTODIAN_FEED_URL.")
            return None

        try:
            async with self.session.get(url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    self._record_success(feed_name)
                    return data
                logger.warning(f"Custodian wallet flows returned status {resp.status}")
        except Exception as e:
            logger.warning(f"Custodian wallet flows fetch failed: {e}")

        self._record_failure(feed_name)
        return None
