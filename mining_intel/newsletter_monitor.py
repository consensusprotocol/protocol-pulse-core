"""
Newsletter Monitor — Blockware Intelligence Substack Fetcher
=============================================================
Monitors Blockware's RSS feed for new issues and fetches supplementary
mining data from mempool.space, hashrateindex, and other sources.
"""

import os
import json
import hashlib
import logging
import requests
import feedparser
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
NEWSLETTERS_DIR = BASE_DIR / "newsletters"
NEWSLETTERS_DIR.mkdir(exist_ok=True)

BLOCKWARE_RSS = "https://blockwareintelligence.substack.com/feed"
MEMPOOL_API = "https://mempool.space/api"

LAST_CHECK_FILE = NEWSLETTERS_DIR / ".last_check"


def _load_last_check() -> str:
    """Return ISO date of last successful check, or empty string."""
    if LAST_CHECK_FILE.exists():
        return LAST_CHECK_FILE.read_text().strip()
    return ""


def _save_last_check(date_str: str):
    LAST_CHECK_FILE.write_text(date_str)


def check_for_new_newsletter() -> dict | None:
    """
    Check Blockware RSS for new posts since last check.
    Returns parsed newsletter dict or None if nothing new.
    """
    logger.info("Checking Blockware Intelligence RSS feed...")
    try:
        feed = feedparser.parse(BLOCKWARE_RSS)
        if not feed.entries:
            logger.info("No entries in Blockware RSS feed")
            return None

        latest = feed.entries[0]
        pub_date = ""
        if hasattr(latest, "published_parsed") and latest.published_parsed:
            pub_date = datetime(*latest.published_parsed[:6]).strftime("%Y-%m-%d")
        elif hasattr(latest, "updated_parsed") and latest.updated_parsed:
            pub_date = datetime(*latest.updated_parsed[:6]).strftime("%Y-%m-%d")
        else:
            pub_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        last_check = _load_last_check()
        if pub_date <= last_check:
            logger.info(f"No new newsletter (latest: {pub_date}, last check: {last_check})")
            return None

        # New newsletter found
        title = latest.get("title", "Untitled")
        link = latest.get("link", "")
        content_html = ""
        if hasattr(latest, "content") and latest.content:
            content_html = latest.content[0].get("value", "")
        elif hasattr(latest, "summary"):
            content_html = latest.summary or ""

        newsletter = {
            "date": pub_date,
            "title": title,
            "url": link,
            "source": "Blockware Intelligence",
            "content_html": content_html,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

        # Cache to disk
        cache_file = NEWSLETTERS_DIR / f"{pub_date}.json"
        cache_file.write_text(json.dumps(newsletter, indent=2))
        _save_last_check(pub_date)

        logger.info(f"New Blockware newsletter: '{title}' ({pub_date})")
        return newsletter

    except Exception as e:
        logger.error(f"Error checking Blockware RSS: {e}")
        return None


def fetch_mempool_data() -> dict:
    """
    Fetch current mining and network data from mempool.space API.
    Returns structured dict with hashrate, difficulty, fees, blocks.
    """
    data = {
        "source": "mempool.space",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "hashrate": None,
        "difficulty": None,
        "difficulty_adjustment": None,
        "block_height": None,
        "avg_fee": None,
        "mempool_size": None,
    }

    # Hashrate (3-day average)
    try:
        r = requests.get(f"{MEMPOOL_API}/v1/mining/hashrate/3d", timeout=10)
        if r.status_code == 200:
            hd = r.json()
            if hd.get("hashrates"):
                latest_hr = hd["hashrates"][-1]
                # Convert H/s to EH/s
                data["hashrate"] = {
                    "value": latest_hr.get("avgHashrate", 0),
                    "ehs": round(latest_hr.get("avgHashrate", 0) / 1e18, 1),
                    "unit": "EH/s"
                }
            if hd.get("difficulty"):
                latest_diff = hd["difficulty"][-1]
                data["difficulty"] = {
                    "value": latest_diff.get("difficulty", 0),
                    "trillion": round(latest_diff.get("difficulty", 0) / 1e12, 2),
                    "unit": "T"
                }
    except Exception as e:
        logger.warning(f"Mempool hashrate fetch failed: {e}")

    # Difficulty adjustment estimate
    try:
        r = requests.get(f"{MEMPOOL_API}/v1/difficulty-adjustment", timeout=10)
        if r.status_code == 200:
            adj = r.json()
            data["difficulty_adjustment"] = {
                "progress_pct": round(adj.get("progressPercent", 0), 1),
                "estimated_change_pct": round(adj.get("difficultyChange", 0), 2),
                "remaining_blocks": adj.get("remainingBlocks", 0),
                "estimated_retarget_date": adj.get("estimatedRetargetDate", "")
            }
    except Exception as e:
        logger.warning(f"Mempool difficulty adjustment fetch failed: {e}")

    # Latest block
    try:
        r = requests.get(f"{MEMPOOL_API}/blocks/tip/height", timeout=10)
        if r.status_code == 200:
            data["block_height"] = int(r.text.strip())
    except Exception as e:
        logger.warning(f"Mempool block height fetch failed: {e}")

    # Recommended fees
    try:
        r = requests.get(f"{MEMPOOL_API}/v1/fees/recommended", timeout=10)
        if r.status_code == 200:
            fees = r.json()
            data["avg_fee"] = {
                "fastest": fees.get("fastestFee", 0),
                "half_hour": fees.get("halfHourFee", 0),
                "hour": fees.get("hourFee", 0),
                "economy": fees.get("economyFee", 0),
                "minimum": fees.get("minimumFee", 0),
                "unit": "sat/vB"
            }
    except Exception as e:
        logger.warning(f"Mempool fees fetch failed: {e}")

    # Mempool stats
    try:
        r = requests.get(f"{MEMPOOL_API}/mempool", timeout=10)
        if r.status_code == 200:
            mp = r.json()
            data["mempool_size"] = {
                "count": mp.get("count", 0),
                "vsize": mp.get("vsize", 0),
                "total_fee_btc": round(mp.get("total_fee", 0) / 1e8, 4)
            }
    except Exception as e:
        logger.warning(f"Mempool stats fetch failed: {e}")

    logger.info(f"Mempool data fetched: hashrate={data['hashrate']}, block={data['block_height']}")
    return data


def fetch_btc_price() -> dict:
    """Fetch current BTC price from CoinGecko."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
            timeout=10
        )
        if r.status_code == 200:
            d = r.json().get("bitcoin", {})
            return {
                "usd": d.get("usd", 0),
                "change_24h_pct": round(d.get("usd_24h_change", 0), 2)
            }
    except Exception as e:
        logger.warning(f"CoinGecko price fetch failed: {e}")
    return {"usd": 0, "change_24h_pct": 0}


def fetch_fear_greed_index() -> dict:
    """Fetch Bitcoin Fear & Greed Index."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        if r.status_code == 200:
            d = r.json().get("data", [{}])[0]
            return {
                "value": int(d.get("value", 50)),
                "classification": d.get("value_classification", "Neutral")
            }
    except Exception as e:
        logger.warning(f"Fear & Greed fetch failed: {e}")
    return {"value": 50, "classification": "Neutral"}


def fetch_mining_pools() -> dict:
    """Fetch mining pool distribution from mempool.space."""
    try:
        r = requests.get(f"{MEMPOOL_API}/v1/mining/pools/1w", timeout=10)
        if r.status_code == 200:
            d = r.json()
            pools = []
            for p in d.get("pools", [])[:10]:
                pools.append({
                    "name": p.get("name", "Unknown"),
                    "blocks": p.get("blockCount", 0),
                    "share_pct": round(p.get("share", 0) * 100, 1) if p.get("share") else 0
                })
            return {
                "period": "1w",
                "total_blocks": d.get("blockCount", 0),
                "pools": pools
            }
    except Exception as e:
        logger.warning(f"Mining pools fetch failed: {e}")
    return {"period": "1w", "total_blocks": 0, "pools": []}


def gather_all_data(force: bool = False) -> dict:
    """
    Gather all mining intel data.
    Returns combined dict with newsletter + supplementary data.
    """
    newsletter = check_for_new_newsletter()
    if not newsletter and not force:
        logger.info("No new newsletter and force=False — checking supplementary only")

    mempool = fetch_mempool_data()
    btc_price = fetch_btc_price()
    fng = fetch_fear_greed_index()
    pools = fetch_mining_pools()

    return {
        "gathered_at": datetime.now(timezone.utc).isoformat(),
        "newsletter": newsletter,
        "mempool": mempool,
        "btc_price": btc_price,
        "fear_greed": fng,
        "mining_pools": pools,
        "has_newsletter": newsletter is not None
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    data = gather_all_data(force=True)
    print(json.dumps(data, indent=2, default=str))
