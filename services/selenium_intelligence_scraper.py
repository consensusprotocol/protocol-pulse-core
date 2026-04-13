"""
Selenium Intelligence Scraper (Playwright-based)
=================================================
Competitive intelligence collector for on-chain metrics and congressional data.

Targets:
  1. Glassnode Studio (free tier) — MVRV, Puell Multiple, SOPR
  2. CryptoQuant (free tier) — Exchange Reserve, Fund Flow Ratio
  3. efts.house.gov — STOCK Act disclosures (direct fallback for QuiverQuant)

Architecture:
  - Playwright headless Chromium (Selenium unavailable on Ultron)
  - Network interception to capture chart API data (no OCR needed)
  - Plain HTTP for efts.house.gov (no browser needed)
  - Results stored in signals.json + pro_metrics_cache.json

Cron: 0 4 * * * (4am ET daily — off-peak, low detection risk)
"""

import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SIGNALS_PATH = DATA_DIR / "signals.json"
PRO_METRICS_PATH = DATA_DIR / "pro_metrics_cache.json"
SCREENSHOT_DIR = DATA_DIR / "intelligence_screenshots"

# ── Anti-detection: User-agent pool ────────────────────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
]

# ── Crypto tickers for congress filtering (matches panopticon_service.py) ──
CRYPTO_TICKERS = {
    "IBIT", "FBTC", "GBTC", "ARKB", "BITB", "HODL", "BTCO", "EZBC",
    "BRRR", "BTCW", "BITO", "BITX", "BITI", "ETHE", "ETHA", "COIN",
    "HOOD", "MSTR", "MARA", "RIOT", "CLSK", "HUT", "BTBT", "CIFR",
    "WULF", "IREN", "CORZ", "BITF", "BTDR", "SQ", "PYPL",
}


# ═══════════════════════════════════════════════════════════════════════════
# HEADLESS BROWSER MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class HeadlessBrowser:
    """Manages Playwright headless Chromium lifecycle with anti-detection."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """Launch headless Chromium with stealth settings."""
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-extensions",
            ],
        )
        ua = random.choice(_USER_AGENTS)
        self._context = self._browser.new_context(
            user_agent=ua,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            # Block unnecessary resources to speed up loads
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
            },
        )
        # Stealth: override navigator.webdriver + realistic fingerprints
        self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            // Mock realistic PluginArray (PDF Viewer + Chrome PDF Viewer + Widevine)
            const pluginData = [
                {name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                {name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                {name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                {name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer', description: ''},
                {name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer', description: ''},
            ];
            const pluginArray = Object.create(PluginArray.prototype);
            pluginData.forEach((p, i) => {
                const plugin = Object.create(Plugin.prototype);
                Object.defineProperties(plugin, {
                    name: {get: () => p.name}, filename: {get: () => p.filename},
                    description: {get: () => p.description}, length: {get: () => 1}
                });
                pluginArray[i] = plugin;
            });
            Object.defineProperty(pluginArray, 'length', {get: () => pluginData.length});
            Object.defineProperty(navigator, 'plugins', {get: () => pluginArray});
        """)
        logger.info("HeadlessBrowser started (UA: %s...)", ua[:50])

    def close(self):
        """Clean shutdown — prevents zombie processes."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning("Browser close error: %s", e)
        finally:
            self._context = None
            self._browser = None
            self._playwright = None

    def new_page(self):
        """Create a new page in the browser context."""
        if not self._context:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._context.new_page()

    @staticmethod
    def human_delay(min_s: float = 2.0, max_s: float = 6.0):
        """Random delay to mimic human browsing."""
        time.sleep(random.uniform(min_s, max_s))


# ═══════════════════════════════════════════════════════════════════════════
# GLASSNODE SCRAPER
# ═══════════════════════════════════════════════════════════════════════════

class GlassnodeScraper:
    """Scrape on-chain metrics from Glassnode Studio free dashboard.

    Strategy: Navigate to free chart pages → intercept API responses →
    extract latest values from the JSON payloads.
    Falls back to screenshot + manual review if interception fails.
    """

    # On-chain chart URLs — updated 2026-04-13
    # Glassnode studio.glassnode.com/metrics URLs are all 404 as of Apr 2026.
    # bitcoinmagazinepro.com (confirmed 200) covers Puell + MVRV.
    # blockchain.com/explorer/charts (confirmed 200) covers SOPR + hashrate.
    CHARTS = {
        "sopr": {
            "url": "https://www.blockchain.com/explorer/charts/sopr",
            "api_pattern": r"blockchain\.com.*(sopr|chart)",
            "description": "Spent Output Profit Ratio",
            "free_tier": True,
            "source_label": "Blockchain.com",
            "wait_selector": "canvas, svg.chart, .highcharts-root, .chart-title:not(:text('Unknown'))",
            "wait_ms": 7000,
        },
        "puell_multiple": {
            "url": "https://www.bitcoinmagazinepro.com/charts/puell-multiple/",
            "api_pattern": r"bitcoinmagazinepro\.com.*(api|chart|data)",
            "description": "Puell Multiple",
            "free_tier": True,
            "source_label": "Bitcoin Magazine Pro",
            "wait_selector": "canvas, svg, .chart-container",
            "wait_ms": 6000,
        },
        "mvrv_zscore": {
            "url": "https://www.bitcoinmagazinepro.com/charts/mvrv-zscore/",
            "api_pattern": r"bitcoinmagazinepro\.com.*(api|chart|data)",
            "description": "MVRV Z-Score",
            "free_tier": True,
            "source_label": "Bitcoin Magazine Pro",
            "wait_selector": "canvas, svg, .chart-container",
            "wait_ms": 6000,
        },
        "hodl_waves": {
            "url": "https://www.blockchain.com/explorer/charts/hodl-waves",
            "api_pattern": r"blockchain\.com.*(hodl|chart)",
            "description": "HODL Waves",
            "free_tier": True,
            "source_label": "Blockchain.com",
            "wait_selector": "canvas, svg.chart, .highcharts-root",
            "wait_ms": 5000,
        },
    }

    def __init__(self, browser: Optional[HeadlessBrowser] = None):
        self._browser = browser
        self._owns_browser = browser is None

    def scrape_all(self) -> dict:
        """Scrape all configured Glassnode charts. Returns metric dict.

        Only scrapes free-tier charts unless GLASSNODE_API_KEY is set.
        """
        has_api_key = bool(os.environ.get("GLASSNODE_API_KEY"))
        results = {}
        browser = self._browser
        if self._owns_browser:
            browser = HeadlessBrowser()
            browser.start()

        try:
            for metric_key, chart_info in self.CHARTS.items():
                # Skip gated metrics unless we have an API key
                if not chart_info.get("free_tier", True) and not has_api_key:
                    logger.debug("Glassnode %s: skipping (requires API key)", metric_key)
                    continue
                try:
                    value = self._scrape_chart(browser, metric_key, chart_info)
                    results[metric_key] = {
                        "value": value,
                        "description": chart_info["description"],
                        "source": "glassnode",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
                    logger.info("Glassnode %s = %s", metric_key, value)
                    HeadlessBrowser.human_delay(3.0, 8.0)
                except Exception as e:
                    logger.warning("Glassnode %s failed: %s", metric_key, e)
                    results[metric_key] = {
                        "value": None,
                        "error": str(e),
                        "source": "glassnode",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
        finally:
            if self._owns_browser:
                browser.close()

        return results

    def _scrape_chart(self, browser: HeadlessBrowser, metric_key: str, chart_info: dict) -> Optional[float]:
        """Navigate to chart page, intercept API call, extract latest value."""
        page = browser.new_page()
        captured_data = []

        # Set up network interception to capture Glassnode API responses
        api_pattern = chart_info["api_pattern"]

        def handle_response(response):
            url = response.url
            if re.search(api_pattern, url, re.IGNORECASE):
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = response.json()
                        captured_data.append(body)
                except Exception:
                    pass
            # Also capture Glassnode metric data API responses (not price/metadata)
            elif "api.glassnode.com" in url and "/v1/metrics/" in url and "price" not in url:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = response.json()
                        if isinstance(body, list) and body:
                            captured_data.append(body)
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            # Use domcontentloaded + explicit wait — some Glassnode charts
            # have persistent WebSocket connections that prevent networkidle
            page.goto(chart_info["url"], wait_until="domcontentloaded", timeout=30000)
            wait_ms = chart_info.get("wait_ms", 5000)
            selector = chart_info.get("wait_selector", "canvas")

            # Wait for chart element to appear
            try:
                page.wait_for_selector(selector, timeout=wait_ms)
            except Exception:
                pass

            # Extra settle time for SPA charts (blockchain.com, BMP need JS to populate)
            page.wait_for_timeout(wait_ms)

            # Screenshot: try to crop to just the chart element for clean display
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out_path = SCREENSHOT_DIR / f"glassnode_{metric_key}_{ts}.png"
            captured_chart = False

            # Try element-level screenshot first (crops out nav/sidebar)
            for sel in [selector, "canvas", "svg.chart", ".chart-container",
                        ".highcharts-root", "[class*=chart]"]:
                try:
                    el = page.locator(sel).first
                    if el.count() > 0:
                        bbox = el.bounding_box()
                        if bbox and bbox["width"] > 200 and bbox["height"] > 100:
                            el.screenshot(path=str(out_path))
                            logger.info("Screenshot saved (element crop): %s (%d bytes)",
                                        out_path.name, out_path.stat().st_size)
                            captured_chart = True
                            break
                except Exception:
                    continue

            # Fallback: full page screenshot
            if not captured_chart:
                page.screenshot(path=str(out_path), full_page=False)
                logger.info("Screenshot saved (full page): %s (%d bytes)",
                            out_path.name, out_path.stat().st_size)

            logger.info("Glassnode %s: screenshot from %s", metric_key, chart_info["url"])

            # Bonus: extract any intercepted API value
            if captured_data:
                for data in reversed(captured_data):
                    val = self._extract_latest_value(data)
                    if val is not None:
                        return val

            return None

        finally:
            page.close()

    @staticmethod
    def _extract_latest_value(data) -> Optional[float]:
        """Extract the most recent value from Glassnode API response."""
        if isinstance(data, list) and data:
            # Glassnode returns [{t: timestamp, v: value}, ...]
            last_entry = data[-1]
            if isinstance(last_entry, dict):
                val = last_entry.get("v") or last_entry.get("value")
                if val is not None:
                    return round(float(val), 6)
        elif isinstance(data, dict):
            # Sometimes nested under "data" key
            inner = data.get("data", data)
            if isinstance(inner, list) and inner:
                last = inner[-1]
                val = last.get("v") or last.get("value")
                if val is not None:
                    return round(float(val), 6)
        return None

    @staticmethod
    def _extract_from_dom(page, metric_key: str) -> Optional[float]:
        """Try to extract the displayed value from the page DOM."""
        selectors = [
            '[class*="current-value"]',
            '[class*="latest-value"]',
            '[class*="metric-value"]',
            '[data-testid*="value"]',
            '.chart-tooltip .value',
        ]
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    # Parse numeric value (handle commas, negative, decimals)
                    match = re.search(r'-?[\d,]+\.?\d*', text.replace(",", ""))
                    if match:
                        return round(float(match.group()), 6)
            except Exception:
                continue
        return None

    @staticmethod
    def _save_screenshot(page, name: str):
        """Save a screenshot for manual review."""
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOT_DIR / f"{name}_{ts}.png"
        page.screenshot(path=str(path), full_page=False)
        logger.info("Screenshot saved: %s", path)


# ═══════════════════════════════════════════════════════════════════════════
# CRYPTOQUANT SCRAPER
# ═══════════════════════════════════════════════════════════════════════════

class CryptoQuantScraper:
    """Scrape on-chain metrics from CryptoQuant free tier.

    Strategy: Intercept API responses OR read Y-axis values from the chart DOM.
    CryptoQuant is a heavy SPA that loads chart data via internal API or WebSocket.
    The chart renders SVG/Canvas with visible axis labels we can read.
    """

    # CryptoQuant is now 403 on all endpoints (Apr 2026).
    # Switched to blockchain.com and mempool.space equivalents.
    CHARTS = {
        "exchange_reserve": {
            "url": "https://www.blockchain.com/explorer/charts/trade-volume",
            "api_pattern": r"blockchain\.com.*(volume|chart)",
            "description": "BTC Exchange Trade Volume",
            "unit": "btc",
            "source_label": "Blockchain.com",
            "wait_selector": "canvas, svg.chart, .highcharts-root",
            "wait_ms": 5000,
        },
        "mempool_size": {
            "url": "https://mempool.space/graphs/mempool#1m",
            "api_pattern": r"mempool\.space.*(api|mempool)",
            "description": "Mempool Size",
            "unit": "vbytes",
            "source_label": "Mempool.space",
            "wait_selector": "canvas, .chart, svg",
            "wait_ms": 4000,
        },
        "hashrate": {
            "url": "https://www.blockchain.com/explorer/charts/hash-rate",
            "api_pattern": r"blockchain\.com.*(hash|chart)",
            "description": "Bitcoin Hashrate",
            "unit": "th/s",
            "source_label": "Blockchain.com",
            "wait_selector": "canvas, svg.chart, .highcharts-root",
            "wait_ms": 5000,
        },
    }

    def __init__(self, browser: Optional[HeadlessBrowser] = None):
        self._browser = browser
        self._owns_browser = browser is None

    def scrape_all(self) -> dict:
        """Scrape all configured CryptoQuant charts."""
        results = {}
        browser = self._browser
        if self._owns_browser:
            browser = HeadlessBrowser()
            browser.start()

        try:
            for metric_key, chart_info in self.CHARTS.items():
                try:
                    value = self._scrape_chart(browser, metric_key, chart_info)
                    results[metric_key] = {
                        "value": value,
                        "description": chart_info["description"],
                        "source": "cryptoquant",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
                    logger.info("CryptoQuant %s = %s", metric_key, value)
                    HeadlessBrowser.human_delay(3.0, 8.0)
                except Exception as e:
                    logger.warning("CryptoQuant %s failed: %s", metric_key, e)
                    results[metric_key] = {
                        "value": None,
                        "error": str(e),
                        "source": "cryptoquant",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
        finally:
            if self._owns_browser:
                browser.close()

        return results

    def _scrape_chart(self, browser: HeadlessBrowser, metric_key: str, chart_info: dict) -> Optional[float]:
        """Navigate to chart, intercept API, extract latest value.

        CryptoQuant is a heavy SPA that never reaches 'networkidle'
        (WebSocket connections keep it busy). We use 'domcontentloaded'
        then wait for API data to arrive via response interception.
        """
        page = browser.new_page()
        captured_data = []

        api_pattern = chart_info["api_pattern"]

        def handle_response(response):
            # CryptoQuant may use various internal API patterns
            url = response.url
            if re.search(api_pattern, url, re.IGNORECASE):
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = response.json()
                        captured_data.append(body)
                except Exception:
                    pass
            # Also capture any JSON response from cryptoquant.com that looks like chart data
            elif "cryptoquant.com" in url and "/api/" in url:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = response.json()
                        captured_data.append(body)
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            # Use 'domcontentloaded' since CryptoQuant SPAs never reach 'networkidle'
            page.goto(chart_info["url"], wait_until="domcontentloaded", timeout=30000)
            # Wait for chart data to load (API calls happen after DOM is ready)
            page.wait_for_load_state("networkidle", timeout=15000)

            if captured_data:
                # Try each captured response for chart data
                for data in reversed(captured_data):
                    val = self._extract_latest_value(data)
                    if val is not None:
                        return val

            # Fallback 1: Try to read the latest value from chart tooltip
            # Hover over the right edge of the chart to trigger tooltip
            val = self._read_chart_tooltip(page)
            if val is not None:
                logger.info("CryptoQuant %s: extracted value from tooltip", metric_key)
                return val

            # Fallback 2: screenshot
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = SCREENSHOT_DIR / f"cryptoquant_{metric_key}_{ts}.png"
            page.screenshot(path=str(path), full_page=False)
            logger.warning("CryptoQuant %s: no API data captured, screenshot saved", metric_key)
            return None

        finally:
            page.close()

    @staticmethod
    def _extract_latest_value(data) -> Optional[float]:
        """Extract latest value from CryptoQuant API response."""
        # CryptoQuant API formats: {"result": {"data": [{"date": ..., "value": ...}]}}
        # or {"data": [...]} or direct list
        if isinstance(data, dict):
            # Try nested paths
            for path in [
                lambda d: d.get("result", {}).get("data", []),
                lambda d: d.get("data", []),
                lambda d: d.get("result", []),
            ]:
                try:
                    items = path(data)
                    if isinstance(items, list) and items:
                        last = items[-1]
                        if isinstance(last, dict):
                            for key in ("value", "v", "close", "y"):
                                if key in last and last[key] is not None:
                                    return round(float(last[key]), 6)
                        elif isinstance(last, (int, float)):
                            return round(float(last), 6)
                except (TypeError, AttributeError):
                    continue
        elif isinstance(data, list) and data:
            last = data[-1]
            if isinstance(last, dict):
                for key in ("value", "v", "close"):
                    if key in last:
                        return round(float(last[key]), 6)
        return None

    @staticmethod
    def _read_chart_tooltip(page) -> Optional[float]:
        """Try to read chart value by hovering over the rightmost data point.

        CryptoQuant charts show a tooltip with the current value when you
        hover over the chart area. We move the mouse to the right edge
        of the chart to trigger the tooltip for the latest data point.
        """
        try:
            # Find the chart container (typically a canvas or SVG element)
            chart = page.query_selector('canvas, svg.chart, [class*="chart-container"], [class*="ChartView"]')
            if not chart:
                return None

            box = chart.bounding_box()
            if not box:
                return None

            # Hover near the right edge of the chart (latest data point)
            right_x = box["x"] + box["width"] - 10
            mid_y = box["y"] + box["height"] / 2
            page.mouse.move(right_x, mid_y)
            page.wait_for_timeout(1000)

            # Look for tooltip elements
            tooltip_selectors = [
                '[class*="tooltip"]',
                '[class*="Tooltip"]',
                '[class*="crosshair-value"]',
                '[class*="chart-value"]',
                '[class*="data-value"]',
            ]
            for sel in tooltip_selectors:
                tooltip = page.query_selector(sel)
                if tooltip:
                    text = tooltip.inner_text()
                    # Extract numeric value from tooltip text
                    # Handle formats like "2,734,521", "0.0832", "$71,740", "2.7M"
                    cleaned = text.replace(",", "").replace("$", "").strip()
                    # Handle suffix multipliers
                    multiplier = 1
                    if cleaned.upper().endswith("M"):
                        multiplier = 1_000_000
                        cleaned = cleaned[:-1]
                    elif cleaned.upper().endswith("K"):
                        multiplier = 1_000
                        cleaned = cleaned[:-1]
                    elif cleaned.upper().endswith("B"):
                        multiplier = 1_000_000_000
                        cleaned = cleaned[:-1]

                    match = re.search(r'-?[\d.]+', cleaned)
                    if match:
                        return round(float(match.group()) * multiplier, 6)

        except Exception as e:
            logger.debug("Chart tooltip read failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# CONGRESS SCRAPER (efts.house.gov direct)
# ═══════════════════════════════════════════════════════════════════════════

class CongressScraper:
    """Direct STOCK Act disclosure scraper for House Financial Disclosures.

    This is a FALLBACK for when QuiverQuant API is down.
    Uses Playwright to submit the search form at disclosures-clerk.house.gov
    (ASP.NET Core with anti-forgery tokens — requires browser interaction).

    Also tries efts.house.gov Elasticsearch API as a first attempt.
    """

    SEARCH_URL = "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewSearch"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape_disclosures(self, limit: int = 50, browser: Optional[HeadlessBrowser] = None) -> list[dict]:
        """Scrape STOCK Act disclosures, filter for crypto tickers.

        Tries efts.house.gov Elasticsearch API first, then Playwright for clerk site.
        """
        # Method 1: EFTS Elasticsearch API
        efts_results = self._query_efts(limit)
        if efts_results:
            logger.info("EFTS: fetched %d crypto-related disclosures", len(efts_results))
            return efts_results[:limit]

        # Method 2: Playwright-driven House Clerk search
        clerk_results = self._scrape_clerk_with_browser(limit, browser)
        if clerk_results:
            logger.info("House Clerk: scraped %d filings", len(clerk_results))
            return clerk_results[:limit]

        logger.warning("Congress scraper: all methods failed")
        return []

    def _query_efts(self, limit: int) -> list[dict]:
        """Query efts.house.gov Elasticsearch-style API for crypto tickers."""
        results = []
        search_terms = ["bitcoin", "IBIT", "GBTC", "MSTR", "COIN"]

        for term in search_terms:
            try:
                resp = self._session.get(
                    "https://efts.house.gov/LATEST/search-index",
                    params={
                        "q": f'"{term}"',
                        "page[size]": str(min(limit, 20)),
                        "sort": "-date",
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json() if "json" in resp.headers.get("content-type", "") else {}
                hits = data.get("hits", {}).get("hits", data.get("results", []))

                for hit in hits:
                    src = hit.get("_source", hit) if isinstance(hit, dict) else {}
                    parsed = self._parse_efts_hit(src)
                    if parsed:
                        results.append(parsed)

                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                logger.debug("EFTS query failed for '%s': %s", term, e)
                continue

        # Deduplicate
        seen = set()
        unique = []
        for r in results:
            key = f"{r.get('entity', '')}|{r.get('ticker', '')}|{r.get('date_filed', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique[:limit]

    @staticmethod
    def _parse_efts_hit(src: dict) -> Optional[dict]:
        """Parse an EFTS search hit into a disclosure dict."""
        if not src:
            return None
        filer = src.get("filer_name") or src.get("name") or src.get("member", "Unknown")
        filing_date = src.get("filing_date") or src.get("date") or src.get("filed_date", "")
        text = json.dumps(src).upper()
        matched_tickers = [t for t in CRYPTO_TICKERS if t in text]
        if not matched_tickers:
            return None
        ticker = matched_tickers[0]
        tx_text = (src.get("transaction_type") or src.get("type") or "").lower()
        if "purchase" in tx_text or "buy" in tx_text:
            trade_type = "purchase"
        elif "sale" in tx_text or "sell" in tx_text:
            trade_type = "sale"
        else:
            trade_type = "disclosure"
        return {
            "entity": filer,
            "asset": ticker,
            "ticker": ticker,
            "trade_type": trade_type,
            "amount_range": src.get("amount") or "See filing",
            "date_filed": filing_date,
            "source_url": src.get("url") or "",
            "source": "efts.house.gov / STOCK Act Filing",
            "tier": "confirmed",
            "is_live": True,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    def _scrape_clerk_with_browser(self, limit: int, browser: Optional[HeadlessBrowser] = None) -> list[dict]:
        """Use Playwright to submit House Clerk search form and parse results.

        The clerk site (disclosures-clerk.house.gov) is an ASP.NET Core app
        with anti-forgery tokens. Form fields:
          - LastName (text)
          - FilingYear (select: 2008-2026)
          - State (select)
          - District (text)
          - __RequestVerificationToken (hidden)
        """
        owns_browser = browser is None
        if owns_browser:
            browser = HeadlessBrowser()
            browser.start()

        try:
            page = browser.new_page()
            captured_html = []

            def on_response(response):
                url = response.url
                if "ViewMemberSearchResult" in url or "SearchResult" in url:
                    try:
                        captured_html.append(response.text())
                    except Exception:
                        pass

            page.on("response", on_response)

            page.goto(self.SEARCH_URL, wait_until="networkidle", timeout=30000)
            HeadlessBrowser.human_delay(1.0, 2.0)

            # Select current year in the filing year dropdown
            current_year = str(datetime.now().year)
            year_select = page.query_selector('select#FilingYear')
            if year_select:
                page.select_option('select#FilingYear', current_year)
                HeadlessBrowser.human_delay(0.5, 1.0)

            # Submit the first form (Members section — not Candidates)
            forms = page.query_selector_all('form')
            if forms:
                submit_btn = forms[0].query_selector('button[type="submit"]')
                if submit_btn:
                    submit_btn.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    HeadlessBrowser.human_delay(1.0, 2.0)

            # Parse results — either from captured network response or current page
            results_html = captured_html[-1] if captured_html else page.content()
            disclosures = self._parse_search_results(results_html, limit)

            page.close()
            return disclosures

        except Exception as e:
            logger.warning("House Clerk browser scrape failed: %s", e)
            return []
        finally:
            if owns_browser:
                browser.close()

    @staticmethod
    def _parse_search_results(html: str, limit: int) -> list[dict]:
        """Parse the search results table from House Clerk response.

        Results table typically has columns: Name, Office, Year, Filing (type + PDF link).
        """
        results = []

        # Look for table rows — the results appear in a <table> after form submission
        # Pattern matches: <tr>...<td>Name</td><td>Office</td><td>Year</td><td>Filing info</td>...</tr>
        row_pattern = re.compile(
            r'<tr[^>]*>\s*'
            r'<td[^>]*>(.*?)</td>\s*'     # Column 1: Name
            r'<td[^>]*>(.*?)</td>\s*'     # Column 2: Office/District
            r'<td[^>]*>(.*?)</td>\s*'     # Column 3: Year
            r'<td[^>]*>(.*?)</td>',       # Column 4: Filing type/link
            re.DOTALL | re.IGNORECASE,
        )

        for match in row_pattern.finditer(html):
            name_html = match.group(1)
            office = match.group(2)
            year = match.group(3)
            filing_html = match.group(4)

            name = re.sub(r'<[^>]+>', '', name_html).strip()
            office_clean = re.sub(r'<[^>]+>', '', office).strip()
            year_clean = re.sub(r'<[^>]+>', '', year).strip()
            filing_type = re.sub(r'<[^>]+>', '', filing_html).strip()

            # Skip header rows
            if not name or name.lower() in ("name", "member"):
                continue

            # Extract PDF link if present
            pdf_match = re.search(r'href="([^"]*\.pdf[^"]*)"', filing_html, re.IGNORECASE)
            pdf_url = pdf_match.group(1) if pdf_match else ""
            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = f"https://disclosures-clerk.house.gov{pdf_url}"

            # Determine if it's a PTR (Periodic Transaction Report)
            is_ptr = "ptr" in filing_type.lower() or "periodic" in filing_type.lower() or "transaction" in filing_type.lower()

            results.append({
                "entity": f"Rep. {name}" + (f" ({office_clean})" if office_clean else ""),
                "asset": "See filing",
                "ticker": "",
                "trade_type": "periodic_transaction" if is_ptr else "disclosure",
                "amount_range": "See filing",
                "date_filed": year_clean,
                "filing_type": filing_type,
                "source_url": pdf_url,
                "source": "disclosures-clerk.house.gov",
                "tier": "confirmed",
                "is_live": True,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

            if len(results) >= limit:
                break

        return results


# ═══════════════════════════════════════════════════════════════════════════
# DATA STORAGE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

def _load_json(path: Path) -> dict:
    """Load JSON file, return empty dict on failure."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug("Could not load %s: %s", path, e)
        return {}


def _save_json(path: Path, data: dict):
    """Atomically save JSON file (write to .tmp then rename)."""
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, default=str))
    tmp_path.rename(path)


def update_signals(glassnode_data: dict, cryptoquant_data: dict):
    """Merge scraped on-chain metrics into signals.json.

    Updates the null fields (sopr, nupl, realized_price) that our
    API-based fetchers can't populate.
    """
    signals = _load_json(SIGNALS_PATH)
    now = datetime.now(timezone.utc).isoformat()

    # Map Glassnode metrics to signals.json fields
    if "sopr" in glassnode_data and glassnode_data["sopr"].get("value") is not None:
        signals["sopr"] = {
            "value": glassnode_data["sopr"]["value"],
            "source": "glassnode (scraped)",
            "scraped_at": now,
        }

    if "sopr_adjusted" in glassnode_data and glassnode_data["sopr_adjusted"].get("value") is not None:
        signals["sopr_adjusted"] = {
            "value": glassnode_data["sopr_adjusted"]["value"],
            "source": "glassnode (scraped)",
            "scraped_at": now,
        }

    # Exchange reserve from CryptoQuant
    if "exchange_reserve" in cryptoquant_data and cryptoquant_data["exchange_reserve"].get("value") is not None:
        signals["exchange_reserve"] = {
            "value": cryptoquant_data["exchange_reserve"]["value"],
            "source": "cryptoquant (scraped)",
            "scraped_at": now,
        }

    _save_json(SIGNALS_PATH, signals)
    logger.info("signals.json updated with scraped on-chain metrics")


def update_pro_metrics(glassnode_data: dict, cryptoquant_data: dict):
    """Merge scraped metrics into pro_metrics_cache.json.

    Adds MVRV Z-Score, Puell Multiple, Fund Flow Ratio.
    """
    metrics = _load_json(PRO_METRICS_PATH)
    now = datetime.now(timezone.utc).isoformat()

    # MVRV Z-Score from Glassnode
    if "mvrv_zscore" in glassnode_data and glassnode_data["mvrv_zscore"].get("value") is not None:
        val = glassnode_data["mvrv_zscore"]["value"]
        signal = "BULLISH" if val < 1 else ("BEARISH" if val > 6 else "NEUTRAL")
        metrics["mvrv_zscore"] = {
            "value": val,
            "signal": signal,
            "description": f"MVRV Z-Score at {val:.2f} — {'undervalued' if val < 1 else 'overheated' if val > 6 else 'fair value'}",
            "source": "glassnode (scraped)",
            "scraped_at": now,
        }

    # Puell Multiple from Glassnode
    if "puell_multiple" in glassnode_data and glassnode_data["puell_multiple"].get("value") is not None:
        val = glassnode_data["puell_multiple"]["value"]
        signal = "BULLISH" if val < 0.5 else ("BEARISH" if val > 4 else "NEUTRAL")
        metrics["puell_multiple"] = {
            "value": val,
            "signal": signal,
            "description": f"Puell Multiple at {val:.2f} — {'miners under stress' if val < 0.5 else 'miners taking profit' if val > 4 else 'normal miner revenue'}",
            "source": "glassnode (scraped)",
            "scraped_at": now,
        }

    # Fund Flow Ratio from CryptoQuant
    if "fund_flow_ratio" in cryptoquant_data and cryptoquant_data["fund_flow_ratio"].get("value") is not None:
        val = cryptoquant_data["fund_flow_ratio"]["value"]
        signal = "BEARISH" if val > 0.1 else ("BULLISH" if val < 0.05 else "NEUTRAL")
        metrics["fund_flow_ratio"] = {
            "value": val,
            "signal": signal,
            "description": f"Fund Flow Ratio at {val:.4f} — {'high exchange inflow' if val > 0.1 else 'low exchange inflow' if val < 0.05 else 'normal flow'}",
            "source": "cryptoquant (scraped)",
            "scraped_at": now,
        }

    # Miner Revenue from CryptoQuant
    if "miner_revenue" in cryptoquant_data and cryptoquant_data["miner_revenue"].get("value") is not None:
        val = cryptoquant_data["miner_revenue"]["value"]
        metrics["miner_revenue"] = {
            "value": val,
            "signal": "NEUTRAL",
            "description": f"Daily miner revenue: ${val:,.0f}" if val > 1000 else f"Miner revenue: {val}",
            "source": "cryptoquant (scraped)",
            "scraped_at": now,
        }

    metrics["timestamp"] = now
    _save_json(PRO_METRICS_PATH, metrics)
    logger.info("pro_metrics_cache.json updated with scraped metrics")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

def run_full_scrape(targets: Optional[list[str]] = None, test_mode: bool = False):
    """Run all intelligence scrapers. Returns summary dict.

    Args:
        targets: List of targets to scrape ('glassnode', 'cryptoquant', 'congress').
                 None = all targets.
        test_mode: If True, only scrape one metric per target for testing.
    """
    if targets is None:
        targets = ["glassnode", "cryptoquant", "congress"]

    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "targets": {},
        "errors": [],
    }

    glassnode_data = {}
    cryptoquant_data = {}

    # Run browser-based scrapers with shared browser instance
    browser_targets = [t for t in targets if t in ("glassnode", "cryptoquant")]
    if browser_targets:
        try:
            with HeadlessBrowser() as browser:
                if "glassnode" in targets:
                    logger.info("=== Scraping Glassnode Studio ===")
                    scraper = GlassnodeScraper(browser)
                    if test_mode:
                        # Only scrape SOPR in test mode
                        chart = scraper.CHARTS["sopr"]
                        val = scraper._scrape_chart(browser, "sopr", chart)
                        glassnode_data = {"sopr": {"value": val, "source": "glassnode", "scraped_at": datetime.now(timezone.utc).isoformat()}}
                    else:
                        glassnode_data = scraper.scrape_all()
                    results["targets"]["glassnode"] = glassnode_data
                    HeadlessBrowser.human_delay(5.0, 10.0)

                if "cryptoquant" in targets:
                    logger.info("=== Scraping CryptoQuant ===")
                    scraper = CryptoQuantScraper(browser)
                    if test_mode:
                        chart = scraper.CHARTS["exchange_reserve"]
                        val = scraper._scrape_chart(browser, "exchange_reserve", chart)
                        cryptoquant_data = {"exchange_reserve": {"value": val, "source": "cryptoquant", "scraped_at": datetime.now(timezone.utc).isoformat()}}
                    else:
                        cryptoquant_data = scraper.scrape_all()
                    results["targets"]["cryptoquant"] = cryptoquant_data

        except Exception as e:
            error_msg = f"Browser scraper error: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

    # Congress scraper (no browser needed)
    if "congress" in targets:
        logger.info("=== Scraping Congress STOCK Act ===")
        try:
            congress = CongressScraper()
            limit = 5 if test_mode else 50
            disclosures = congress.scrape_disclosures(limit=limit)
            results["targets"]["congress"] = {
                "count": len(disclosures),
                "disclosures": disclosures,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            error_msg = f"Congress scraper error: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

    # Update data files
    if glassnode_data or cryptoquant_data:
        try:
            update_signals(glassnode_data, cryptoquant_data)
            update_pro_metrics(glassnode_data, cryptoquant_data)
        except Exception as e:
            error_msg = f"Data update error: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    success_count = sum(
        1 for t in results["targets"].values()
        if isinstance(t, dict) and (t.get("value") is not None or t.get("count", 0) > 0 or any(
            v.get("value") is not None for v in t.values() if isinstance(v, dict)
        ))
    )
    results["summary"] = f"Scraped {success_count}/{len(targets)} targets successfully"

    logger.info("Intelligence scrape complete: %s", results["summary"])
    return results


# ═══════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Protocol Pulse Intelligence Scraper")
    parser.add_argument("--test", action="store_true", help="Test mode (one metric per target)")
    parser.add_argument(
        "--target",
        choices=["glassnode", "cryptoquant", "congress", "all"],
        default="all",
        help="Which target to scrape",
    )
    args = parser.parse_args()

    targets = None if args.target == "all" else [args.target]
    result = run_full_scrape(targets=targets, test_mode=args.test)

    print(json.dumps(result, indent=2, default=str))
