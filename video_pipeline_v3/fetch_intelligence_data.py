#!/usr/bin/env python3
"""fetch_intelligence_data.py — Fetch live BTC intelligence data for Today Intelligence charts.

APIs: CoinGecko (price 7d hourly, dominance), Mempool.space (hashrate 30d), Alternative.me (fear/greed).
Cache: cache/intelligence_charts_cache.json (6h TTL).

Usage:
    from fetch_intelligence_data import fetch_all, load_or_refresh
    data = load_or_refresh()           # cached if < 6h old
    data = load_or_refresh(max_age_hours=1)  # custom TTL
    data = fetch_all()                 # force fresh
"""

import json
import logging
import os
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [intel_data] %(levelname)s %(message)s")
log = logging.getLogger("intel_data")

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "intelligence_charts_cache.json")


def _api_get(url: str, timeout: int = 10) -> dict:
    """GET JSON from URL with timeout."""
    req = urllib.request.Request(url, headers={"User-Agent": "ProtocolPulse/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_all() -> dict:
    """Fetch all intelligence data from APIs and save to cache.

    Returns dict with keys: price_7d, hashrate_30d, btc_dominance,
    fear_greed_value, fear_greed_label, fetched_at.
    """
    log.info("Fetching all intelligence data...")

    # 1. CoinGecko — BTC price 7 day hourly
    price_7d = []
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7"
        data = _api_get(url)
        price_7d = data.get("prices", [])  # list of [timestamp_ms, price]
        log.info("Price 7d: %d hourly points", len(price_7d))
    except Exception as e:
        log.warning("Price 7d fetch failed: %s", e)

    # 2. Mempool.space — hashrate 30 day
    hashrate_30d = []
    try:
        url = "https://mempool.space/api/v1/mining/hashrate/1m"
        data = _api_get(url)
        hashrate_30d = data.get("hashrates", [])  # list of {timestamp, avgHashrate}
        log.info("Hashrate 30d: %d data points", len(hashrate_30d))
    except Exception as e:
        log.warning("Hashrate 30d fetch failed: %s", e)

    # 3. CoinGecko — BTC dominance (global endpoint)
    btc_dominance = 0.0
    try:
        url = "https://api.coingecko.com/api/v3/global"
        data = _api_get(url)
        btc_dominance = data.get("data", {}).get("market_cap_percentage", {}).get("btc", 0.0)
        log.info("BTC Dominance: %.1f%%", btc_dominance)
    except Exception as e:
        log.warning("Dominance fetch failed: %s", e)

    # 4. Alternative.me — Fear & Greed Index
    fear_greed_value = 0
    fear_greed_label = "N/A"
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        data = _api_get(url)
        fg_data = data.get("data", [{}])[0]
        fear_greed_value = int(fg_data.get("value", 0))
        fear_greed_label = fg_data.get("value_classification", "N/A")
        log.info("Fear & Greed: %d (%s)", fear_greed_value, fear_greed_label)
    except Exception as e:
        log.warning("Fear & Greed fetch failed: %s", e)

    result = {
        "fetched_at": time.time(),
        "price_7d": price_7d,
        "hashrate_30d": hashrate_30d,
        "btc_dominance": btc_dominance,
        "fear_greed_value": fear_greed_value,
        "fear_greed_label": fear_greed_label,
    }

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(result, f)

    log.info("Intelligence data cached: %d price pts, %d hashrate pts, dominance=%.1f%%, F&G=%d (%s)",
             len(price_7d), len(hashrate_30d), btc_dominance, fear_greed_value, fear_greed_label)

    return result


def load_or_refresh(max_age_hours: float = 6) -> dict:
    """Load from cache if fresh (< max_age_hours), otherwise fetch fresh.

    Falls back to stale cache on fetch error.
    """
    max_age_sec = max_age_hours * 3600

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            age = time.time() - data.get("fetched_at", 0)
            if age < max_age_sec:
                log.info("Using cached intelligence data (%.0fm old, max %.0fh)", age / 60, max_age_hours)
                return data
            log.info("Cache expired (%.1fh old, max %.0fh) — refreshing", age / 3600, max_age_hours)
        except Exception:
            pass

    # Try fresh fetch, fall back to stale cache on error
    try:
        return fetch_all()
    except Exception as e:
        log.warning("Fresh fetch failed: %s — trying stale cache", e)
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE) as f:
                    data = json.load(f)
                log.info("Using stale cache as fallback")
                return data
            except Exception:
                pass
        # Return empty defaults
        return {
            "fetched_at": 0,
            "price_7d": [],
            "hashrate_30d": [],
            "btc_dominance": 0.0,
            "fear_greed_value": 0,
            "fear_greed_label": "N/A",
        }


if __name__ == "__main__":
    data = fetch_all()
    print(f"Price 7d points: {len(data['price_7d'])}")
    print(f"Hashrate 30d points: {len(data['hashrate_30d'])}")
    print(f"BTC Dominance: {data['btc_dominance']:.1f}%")
    print(f"Fear & Greed: {data['fear_greed_value']} ({data['fear_greed_label']})")
