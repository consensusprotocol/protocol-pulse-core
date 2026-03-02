"""Gather live Bitcoin data for Oracle Briefing.

Returns data in the format expected by briefing_writer and overlay_engine:
  btc:       {price, change_24h, market_cap}
  btc_7d:    [[timestamp_ms, price], ...]
  mempool:   {fastest_fee, half_hour_fee, hour_fee, economy_fee, tx_count, vsize}
  fng:       {value, label}
  hashrate:  {hashrate_eh, difficulty_epochs}
  block_height: int
  articles:  [{title, slug, summary}, ...]
  timestamp: ISO string
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

from relay import get_key


def gather_all():
    """Fetch all live data sources, return structured dict."""
    print("[data] Fetching live data...")
    btc = fetch_btc_price()
    btc_7d = fetch_btc_7d()
    mempool = fetch_mempool()
    fng = fetch_fear_greed()
    hashrate = fetch_hashrate()
    block_height = fetch_block_height()
    articles = fetch_latest_articles()

    data = {
        "btc": btc,
        "btc_7d": btc_7d,
        "mempool": mempool,
        "fng": fng,
        "hashrate": hashrate,
        "block_height": block_height,
        "articles": articles,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  BTC: ${btc['price']:,.0f} ({btc['change_24h']:+.1f}%)")
    print(f"  FNG: {fng['value']} ({fng['label']})")
    print(f"  Mempool: {mempool['tx_count']:,} txs, {mempool['fastest_fee']} sat/vB fastest")
    print(f"  Hashrate: {hashrate['hashrate_eh']} EH/s")
    print(f"  Block: {block_height:,}")
    return data


def fetch_btc_price():
    """BTC price + 24h change from CoinGecko."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()["bitcoin"]
        return {
            "price": d["usd"],
            "change_24h": round(d.get("usd_24h_change", 0), 2),
            "market_cap": d.get("usd_market_cap", 0),
            "volume_24h": d.get("usd_24h_vol", 0),
        }
    except Exception as e:
        print(f"  [data] BTC price error: {e}")
        return {"price": 0, "change_24h": 0, "market_cap": 0, "volume_24h": 0}


def fetch_btc_7d():
    """Fetch 7-day BTC price history for overlay chart."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": "7"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("prices", [])
    except Exception as e:
        print(f"  [data] BTC 7d error: {e}")
        return []


def fetch_mempool():
    """Mempool fees and unconfirmed transaction count."""
    result = {
        "fastest_fee": 0, "half_hour_fee": 0,
        "hour_fee": 0, "economy_fee": 0,
        "tx_count": 0, "vsize": 0,
    }
    try:
        r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=10)
        r.raise_for_status()
        fees = r.json()
        result["fastest_fee"] = fees.get("fastestFee", 0)
        result["half_hour_fee"] = fees.get("halfHourFee", 0)
        result["hour_fee"] = fees.get("hourFee", 0)
        result["economy_fee"] = fees.get("economyFee", 0)
    except Exception as e:
        print(f"  [data] Fees error: {e}")

    try:
        r = requests.get("https://mempool.space/api/mempool", timeout=10)
        r.raise_for_status()
        mp = r.json()
        result["tx_count"] = mp.get("count", 0)
        result["vsize"] = mp.get("vsize", 0)
    except Exception as e:
        print(f"  [data] Mempool error: {e}")

    return result


def fetch_hashrate():
    """Hashrate and difficulty from mempool.space."""
    try:
        r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=15)
        r.raise_for_status()
        data = r.json()
        hr = data.get("hashrates", [])
        diff = data.get("difficulty", [])
        current_hr = hr[-1]["avgHashrate"] if hr else 0
        return {
            "hashrate_eh": round(current_hr / 1e18, 1),
            "difficulty_epochs": diff[-5:] if len(diff) >= 5 else diff,
        }
    except Exception as e:
        print(f"  [data] Hashrate error: {e}")
        return {"hashrate_eh": 0, "difficulty_epochs": []}


def fetch_fear_greed():
    """Fear & Greed Index from alternative.me."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        r.raise_for_status()
        d = r.json()["data"][0]
        return {"value": int(d["value"]), "label": d["value_classification"]}
    except Exception as e:
        print(f"  [data] FNG error: {e}")
        return {"value": 50, "label": "Neutral"}


def fetch_block_height():
    """Current Bitcoin block height from mempool.space."""
    try:
        r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=10)
        r.raise_for_status()
        return int(r.text.strip())
    except Exception as e:
        print(f"  [data] Block height error: {e}")
        return 0


def fetch_latest_articles():
    """Fetch latest Protocol Pulse articles via Replit relay."""
    from relay import query_db
    try:
        raw = query_db(
            "SELECT title, slug, summary FROM articles ORDER BY published_at DESC LIMIT 5"
        )
        if raw:
            return json.loads(raw)
    except Exception as e:
        print(f"  [data] Articles error: {e}")
    return []


# Sample data for test mode
SAMPLE_DATA = {
    "btc": {"price": 87432, "change_24h": 2.4, "market_cap": 1720000000000, "volume_24h": 34000000000},
    "btc_7d": [
        [1709251200000, 84200], [1709337600000, 85100],
        [1709424000000, 84800], [1709510400000, 86300],
        [1709596800000, 85900], [1709683200000, 86700],
        [1709769600000, 87432],
    ],
    "mempool": {
        "fastest_fee": 12, "half_hour_fee": 8, "hour_fee": 5,
        "economy_fee": 3, "tx_count": 42000, "vsize": 180000000,
    },
    "fng": {"value": 72, "label": "Greed"},
    "hashrate": {"hashrate_eh": 792.3, "difficulty_epochs": []},
    "block_height": 939063,
    "articles": [
        {"title": "Bitcoin Crosses $87K As Institutional Demand Surges",
         "slug": "bitcoin-crosses-87k", "summary": "Bitcoin breaks above $87,000..."},
        {"title": "Mining Difficulty Hits All-Time High",
         "slug": "mining-difficulty-ath", "summary": "Network difficulty adjustment..."},
    ],
    "timestamp": datetime.now(timezone.utc).isoformat(),
}


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    if test_mode:
        data = SAMPLE_DATA
        print("=== Data Gatherer (TEST — sample data) ===\n")
    else:
        print("=== Data Gatherer (LIVE) ===\n")
        data = gather_all()

    print(json.dumps(data, indent=2, default=str))
