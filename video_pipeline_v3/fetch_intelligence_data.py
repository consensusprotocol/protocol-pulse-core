#!/usr/bin/env python3
"""fetch_intelligence_data.py — Fetch live BTC intelligence data for Today Intelligence charts.

APIs: CoinGecko (price history), Mempool.space (hashrate), CoinGecko (dominance).
Cache: cache/intelligence_data.json (10 min TTL).

Usage:
    from fetch_intelligence_data import fetch_all, load_or_refresh
    data = load_or_refresh()  # cached, fast
    data = fetch_all()        # force fresh
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
CACHE_FILE = os.path.join(CACHE_DIR, "intelligence_data.json")
CACHE_TTL = 600  # 10 minutes


def _api_get(url: str, timeout: int = 8) -> dict:
    """GET JSON from URL with timeout."""
    req = urllib.request.Request(url, headers={"User-Agent": "ProtocolPulse/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_price_history(days: int = 14) -> list:
    """Fetch BTC/USD daily price from CoinGecko. Returns list of [timestamp_ms, price]."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval=daily"
        data = _api_get(url)
        prices = data.get("prices", [])
        log.info("Price history: %d data points (%d days)", len(prices), days)
        return prices
    except Exception as e:
        log.warning("Price history fetch failed: %s", e)
        return []


def fetch_hashrate_history(days: int = 14) -> list:
    """Fetch hashrate from Mempool.space. Returns list of {timestamp, avgHashrate}."""
    try:
        period = f"{days}d" if days <= 30 else "1m"
        url = f"https://mempool.space/api/v1/mining/hashrate/{period}"
        data = _api_get(url)
        points = data.get("hashrates", [])
        log.info("Hashrate history: %d data points", len(points))
        return points
    except Exception as e:
        log.warning("Hashrate history fetch failed: %s", e)
        return []


def fetch_dominance() -> dict:
    """Fetch BTC dominance from CoinGecko global endpoint."""
    try:
        url = "https://api.coingecko.com/api/v3/global"
        data = _api_get(url)
        gd = data.get("data", {})
        btc_dom = gd.get("market_cap_percentage", {}).get("btc", 0)
        total_mcap = gd.get("total_market_cap", {}).get("usd", 0)
        btc_mcap = gd.get("total_market_cap", {}).get("btc", 0)
        log.info("Dominance: BTC %.1f%%", btc_dom)
        return {
            "btc_dominance": round(btc_dom, 2),
            "total_market_cap_usd": total_mcap,
            "btc_market_cap_usd": btc_mcap,
            "eth_dominance": round(gd.get("market_cap_percentage", {}).get("eth", 0), 2),
        }
    except Exception as e:
        log.warning("Dominance fetch failed: %s", e)
        return {"btc_dominance": 61.0, "total_market_cap_usd": 0, "eth_dominance": 0}


def fetch_current_price() -> float:
    """Fetch current BTC price. Returns float or 0."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        data = _api_get(url)
        return data.get("bitcoin", {}).get("usd", 0)
    except Exception:
        try:
            url2 = "https://mempool.space/api/v1/prices"
            data = _api_get(url2)
            return data.get("USD", 0)
        except Exception:
            return 0


def fetch_all() -> dict:
    """Fetch all intelligence data and save to cache. Returns full data dict."""
    log.info("Fetching all intelligence data...")

    price_history = fetch_price_history(14)
    hashrate_history = fetch_hashrate_history(14)
    dominance = fetch_dominance()
    current_price = fetch_current_price()

    result = {
        "fetched_at": time.time(),
        "current_price": current_price,
        "price_history": price_history,
        "hashrate_history": hashrate_history,
        "dominance": dominance,
    }

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(result, f)

    log.info("Intelligence data cached: price=$%s, dominance=%.1f%%, %d price points, %d hashrate points",
             f"{current_price:,.0f}" if current_price else "N/A",
             dominance.get("btc_dominance", 0),
             len(price_history), len(hashrate_history))

    return result


def load_or_refresh() -> dict:
    """Load from cache if fresh (< 10 min), otherwise fetch fresh."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            age = time.time() - data.get("fetched_at", 0)
            if age < CACHE_TTL:
                log.info("Using cached intelligence data (%.0fs old)", age)
                return data
        except Exception:
            pass
    return fetch_all()


if __name__ == "__main__":
    data = fetch_all()
    print(f"BTC Price: ${data['current_price']:,.0f}")
    print(f"Price points: {len(data['price_history'])}")
    print(f"Hashrate points: {len(data['hashrate_history'])}")
    print(f"BTC Dominance: {data['dominance']['btc_dominance']}%")
