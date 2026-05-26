"""
Market Intelligence Dashboard — Real-time Bitcoin market data aggregation.

Data sources (all free, no API key required):
- CoinGecko: BTC price, market cap, volume, dominance, global data
- alternative.me: Fear & Greed Index
- Blockchain.com: Hashrate, difficulty, mempool
- Mempool.space: Fee estimates, mempool stats

Caches data with configurable TTL to respect rate limits.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache helper
# ---------------------------------------------------------------------------

class _Cache:
    """Simple thread-safe TTL cache."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store and time.time() < self._expiry.get(key, 0):
                return self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 60):
        with self._lock:
            self._store[key] = value
            self._expiry[key] = time.time() + ttl


_cache = _Cache()
_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json", "User-Agent": "ProtocolPulse/2.0"})
_TIMEOUT = 12


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def _fetch_btc_price() -> Dict:
    """Core BTC price data from CoinGecko."""
    cached = _cache.get("btc_price")
    if cached:
        return cached

    try:
        resp = _SESSION.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "true",
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        md = data.get("market_data", {})

        result = {
            "price_usd": md.get("current_price", {}).get("usd", 0),
            "price_btc_sats": 100_000_000,  # 1 BTC = 100M sats
            "change_1h": md.get("price_change_percentage_1h_in_currency", {}).get("usd", 0),
            "change_24h": md.get("price_change_percentage_24h", 0),
            "change_7d": md.get("price_change_percentage_7d", 0),
            "change_30d": md.get("price_change_percentage_30d", 0),
            "market_cap": md.get("market_cap", {}).get("usd", 0),
            "total_volume_24h": md.get("total_volume", {}).get("usd", 0),
            "circulating_supply": md.get("circulating_supply", 0),
            "max_supply": 21_000_000,
            "ath": md.get("ath", {}).get("usd", 0),
            "ath_date": md.get("ath_date", {}).get("usd", ""),
            "ath_change_pct": md.get("ath_change_percentage", {}).get("usd", 0),
            "sparkline_7d": md.get("sparkline_7d", {}).get("price", []),
            "high_24h": md.get("high_24h", {}).get("usd", 0),
            "low_24h": md.get("low_24h", {}).get("usd", 0),
            "last_updated": data.get("last_updated", datetime.utcnow().isoformat()),
        }
        _cache.set("btc_price", result, ttl=45)
        return result
    except Exception as e:
        logger.error("BTC price fetch failed: %s", e)
        return {}


def _fetch_global_market() -> Dict:
    """Global crypto market data from CoinGecko."""
    cached = _cache.get("global_market")
    if cached:
        return cached

    try:
        resp = _SESSION.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})

        result = {
            "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
            "total_volume_24h": data.get("total_volume", {}).get("usd", 0),
            "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
            "eth_dominance": data.get("market_cap_percentage", {}).get("eth", 0),
            "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
            "markets": data.get("markets", 0),
            "market_cap_change_24h": data.get("market_cap_change_percentage_24h_usd", 0),
        }
        _cache.set("global_market", result, ttl=120)
        return result
    except Exception as e:
        logger.error("Global market fetch failed: %s", e)
        return {}


def _fetch_fear_greed() -> Dict:
    """Fear & Greed Index from alternative.me."""
    cached = _cache.get("fear_greed")
    if cached:
        return cached

    try:
        resp = _SESSION.get(
            "https://api.alternative.me/fng/",
            params={"limit": 30, "format": "json"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        if not data:
            return {}

        current = data[0]
        history = [
            {
                "value": int(d["value"]),
                "label": d["value_classification"],
                "timestamp": int(d["timestamp"]),
            }
            for d in data[:30]
        ]

        result = {
            "value": int(current["value"]),
            "label": current["value_classification"],
            "timestamp": int(current["timestamp"]),
            "history_30d": history,
        }
        _cache.set("fear_greed", result, ttl=300)
        return result
    except Exception as e:
        logger.error("Fear & Greed fetch failed: %s", e)
        return {}


def _fetch_mempool_stats() -> Dict:
    """Mempool statistics from mempool.space."""
    cached = _cache.get("mempool")
    if cached:
        return cached

    try:
        result = {}

        # Fee estimates
        resp = _SESSION.get("https://mempool.space/api/v1/fees/recommended", timeout=_TIMEOUT)
        if resp.ok:
            fees = resp.json()
            result["fees"] = {
                "fastest": fees.get("fastestFee", 0),
                "half_hour": fees.get("halfHourFee", 0),
                "hour": fees.get("hourFee", 0),
                "economy": fees.get("economyFee", 0),
                "minimum": fees.get("minimumFee", 0),
            }

        # Mempool stats
        resp2 = _SESSION.get("https://mempool.space/api/mempool", timeout=_TIMEOUT)
        if resp2.ok:
            mp = resp2.json()
            result["mempool"] = {
                "tx_count": mp.get("count", 0),
                "vsize_bytes": mp.get("vsize", 0),
                "total_fee_btc": mp.get("total_fee", 0) / 1e8 if mp.get("total_fee") else 0,
            }

        # Hashrate + difficulty
        resp3 = _SESSION.get("https://mempool.space/api/v1/mining/hashrate/1m", timeout=_TIMEOUT)
        if resp3.ok:
            hr_data = resp3.json()
            hashrates = hr_data.get("hashrates", [])
            if hashrates:
                latest = hashrates[-1]
                result["mining"] = {
                    "hashrate_eh": round(latest.get("avgHashrate", 0) / 1e18, 2),
                    "difficulty": hr_data.get("currentDifficulty", 0),
                }

        _cache.set("mempool", result, ttl=60)
        return result
    except Exception as e:
        logger.error("Mempool stats fetch failed: %s", e)
        return {}


def _fetch_blockchain_stats() -> Dict:
    """On-chain metrics from blockchain.com."""
    cached = _cache.get("blockchain_stats")
    if cached:
        return cached

    try:
        resp = _SESSION.get("https://api.blockchain.info/stats", timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        result = {
            "hash_rate_gh": data.get("hash_rate", 0),
            "n_tx_24h": data.get("n_tx", 0),
            "n_blocks_mined_24h": data.get("n_blocks_mined", 0),
            "minutes_between_blocks": data.get("minutes_between_blocks", 0),
            "total_btc_sent_24h": data.get("total_btc_sent", 0) / 1e8 if data.get("total_btc_sent") else 0,
            "estimated_btc_sent_24h": data.get("estimated_btc_sent", 0) / 1e8 if data.get("estimated_btc_sent") else 0,
            "miners_revenue_btc": data.get("miners_revenue_btc", 0) / 1e8 if data.get("miners_revenue_btc") else 0,
            "trade_volume_btc": data.get("trade_volume_btc", 0),
            "difficulty": data.get("difficulty", 0),
            "blockchain_size_gb": round(data.get("blocks_size", 0) / 1e9, 2),
        }
        _cache.set("blockchain_stats", result, ttl=300)
        return result
    except Exception as e:
        logger.error("Blockchain stats fetch failed: %s", e)
        return {}


def _fetch_btc_price_history(days: int = 30) -> List[List]:
    """BTC price history from CoinGecko (for charts)."""
    cache_key = f"price_history_{days}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        resp = _SESSION.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        prices = resp.json().get("prices", [])
        _cache.set(cache_key, prices, ttl=600)
        return prices
    except Exception as e:
        logger.error("Price history fetch failed: %s", e)
        return []


def _fetch_trending() -> List[Dict]:
    """Trending coins from CoinGecko."""
    cached = _cache.get("trending")
    if cached:
        return cached

    try:
        resp = _SESSION.get("https://api.coingecko.com/api/v3/search/trending", timeout=_TIMEOUT)
        resp.raise_for_status()
        coins = resp.json().get("coins", [])
        result = [
            {
                "name": c["item"]["name"],
                "symbol": c["item"]["symbol"],
                "market_cap_rank": c["item"].get("market_cap_rank"),
                "thumb": c["item"].get("thumb", ""),
                "score": c["item"].get("score", 0),
            }
            for c in coins[:10]
        ]
        _cache.set("trending", result, ttl=600)
        return result
    except Exception as e:
        logger.error("Trending fetch failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_full_dashboard() -> Dict:
    """Aggregate all market data into a single dashboard payload."""
    btc = _fetch_btc_price()
    global_mkt = _fetch_global_market()
    fear_greed = _fetch_fear_greed()
    mempool = _fetch_mempool_stats()
    blockchain = _fetch_blockchain_stats()
    trending = _fetch_trending()

    return {
        "btc": btc,
        "global_market": global_mkt,
        "fear_greed": fear_greed,
        "mempool": mempool,
        "blockchain": blockchain,
        "trending": trending,
        "generated_at": datetime.utcnow().isoformat(),
    }


def get_btc_price_quick() -> Dict:
    """Lightweight BTC price endpoint (for nav ticker)."""
    cached = _cache.get("btc_quick")
    if cached:
        return cached

    try:
        resp = _SESSION.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true",
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("bitcoin", {})

        result = {
            "price": data.get("usd", 0),
            "change_24h": data.get("usd_24h_change", 0),
            "volume_24h": data.get("usd_24h_vol", 0),
            "market_cap": data.get("usd_market_cap", 0),
            "last_updated": datetime.utcnow().isoformat(),
        }
        _cache.set("btc_quick", result, ttl=30)
        return result
    except Exception as e:
        logger.error("BTC quick price failed: %s", e)
        return {"price": 0, "change_24h": 0, "volume_24h": 0, "market_cap": 0}


def get_price_history(days: int = 30) -> List[List]:
    """Return price history for charting."""
    return _fetch_btc_price_history(days)
