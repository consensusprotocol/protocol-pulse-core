"""
Market Data Snapshot
=====================
Pulls BTC market data for narrator context.
Primary: CoinGecko free API
Fallback: cached last-known data

Provides narrator-ready text:
  "Bitcoin is trading at $XX,XXX today, up 2.3% in 24 hours."
"""
import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("MarketData")

CACHE_DIR = Path("data/video_engine/cache")
CACHE_FILE = CACHE_DIR / "market_data_latest.json"


class MarketDataProvider:
    """Fetch and cache BTC market data."""

    def __init__(self):
        self.data = {}

    def fetch(self, bundle_path: Path = None) -> Dict:
        """Fetch current BTC market snapshot. Falls back to cache on failure."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Try CoinGecko
        data = self._fetch_coingecko()

        # Fallback to cache
        if not data:
            data = self._load_cache()
            if data:
                logger.info("  Using cached market data")
                data["cached"] = True

        # Final fallback: minimal data
        if not data:
            logger.warning("  No market data available (API + cache both failed)")
            data = {
                "price_usd": None,
                "change_24h_pct": None,
                "market_cap_usd": None,
                "dominance_pct": None,
                "narrator_text": "Bitcoin market data is temporarily unavailable.",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "fallback",
                "cached": True
            }

        self.data = data

        # Save to cache
        try:
            CACHE_FILE.write_text(json.dumps(data, indent=2, default=str))
        except Exception:
            pass

        # Save to bundle
        if bundle_path:
            out = bundle_path / "inputs" / "market_data.json"
            out.write_text(json.dumps(data, indent=2, default=str))

        return data

    def _fetch_coingecko(self) -> Optional[Dict]:
        """Fetch from CoinGecko free API."""
        try:
            import requests

            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            }

            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"  CoinGecko returned {resp.status_code}")
                return None

            btc = resp.json().get("bitcoin", {})
            price = btc.get("usd", 0)
            change = btc.get("usd_24h_change", 0)
            mcap = btc.get("usd_market_cap", 0)

            # Try to get dominance + extra data
            global_data = self._fetch_coingecko_global()
            dominance = global_data.get("dominance_pct") if global_data else None

            # Build narrator text
            direction = "up" if change >= 0 else "down"
            narrator_text = (
                f"Bitcoin is trading at ${price:,.0f} today, "
                f"{direction} {abs(change):.1f}% in 24 hours."
            )
            if dominance:
                narrator_text += f" BTC dominance sits at {dominance:.1f}%."

            data = {
                "price_usd": price,
                "change_24h_pct": round(change, 2),
                "market_cap_usd": mcap,
                "dominance_pct": dominance,
                "narrator_text": narrator_text,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "coingecko",
                "cached": False
            }

            logger.info(f"  Market data: ${price:,.0f} ({direction} {abs(change):.1f}%)")
            return data

        except ImportError:
            logger.warning("  requests not available for market data")
            return None
        except Exception as e:
            logger.warning(f"  CoinGecko fetch failed: {e}")
            return None

    def _fetch_coingecko_global(self) -> Optional[Dict]:
        """Fetch global market data for dominance."""
        try:
            import requests
            resp = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json().get("data", {})
            btc_dom = data.get("market_cap_percentage", {}).get("btc", 0)
            return {"dominance_pct": btc_dom}
        except Exception:
            return None

    def _load_cache(self) -> Optional[Dict]:
        """Load cached market data."""
        if not CACHE_FILE.exists():
            return None
        try:
            data = json.loads(CACHE_FILE.read_text())
            # Only use cache if < 6 hours old
            ts = data.get("timestamp", "")
            if ts:
                cached_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age_hours = (datetime.utcnow() - cached_time.replace(tzinfo=None)).total_seconds() / 3600
                if age_hours > 6:
                    logger.info(f"  Cache too old ({age_hours:.1f}h)")
                    return None
            return data
        except Exception:
            return None
