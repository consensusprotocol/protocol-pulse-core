"""
Signal Data Fetcher — Live Bitcoin Intelligence from Free Public APIs
=====================================================================
Fetches ALL signals from free/available APIs and writes to data/signals.json.
Safe to run every 5 minutes via cron. Total runtime target: under 30 seconds.

Sources (no auth required):
  A) CoinGecko     — price, market cap, volume, 24h change
  B) mempool.space  — difficulty, block height, fees, hashrate, lightning, mempool
  C) alternative.me — Fear & Greed Index
  D) Deribit        — funding rate, open interest (public API)

Optional (if keys in .env):
  - GLASSNODE_API_KEY: SOPR, NUPL, realized price
  - COINGLASS_API_KEY: funding rate, open interest
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path

import requests

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SIGNALS_PATH = DATA_DIR / "signals.json"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "signal_fetcher.log"

# ── Logging ────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_PATH)),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("signal_fetcher")

# ── Config ─────────────────────────────────────────────────────────────────
TIMEOUT = 10
HEADERS = {"User-Agent": "ProtocolPulse/SignalFetcher/2.0", "Accept": "application/json"}

# Load .env if present
_env_path = BASE_DIR / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def _get(url, params=None, timeout=TIMEOUT, custom_headers=None):
    """Safe HTTP GET — returns parsed JSON or None."""
    try:
        h = {**HEADERS, **(custom_headers or {})}
        r = requests.get(url, params=params, headers=h, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("GET %s failed: %s", url, e)
        return None


def _load_previous_signals():
    """Load last good signals.json for cache-first fallback."""
    try:
        if SIGNALS_PATH.exists():
            return json.loads(SIGNALS_PATH.read_text())
    except Exception:
        pass
    return {}


# ═══════════════════════════════════════════════════════════════════════════
# A) PRICE + MARKET DATA — CoinGecko
# ═══════════════════════════════════════════════════════════════════════════

def fetch_price_data():
    """BTC price, 24h change, market cap, volume from CoinGecko."""
    result = {
        "btc_price": {"value": None, "change_24h": None, "source": "coingecko"},
        "market_cap": {"value": None, "source": "coingecko"},
        "volume_24h": {"value": None, "source": "coingecko"},
    }

    data = _get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": "bitcoin",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        },
    )
    if data and "bitcoin" in data:
        btc = data["bitcoin"]
        result["btc_price"]["value"] = btc.get("usd")
        result["btc_price"]["change_24h"] = round(btc.get("usd_24h_change", 0) or 0, 2)
        result["market_cap"]["value"] = btc.get("usd_market_cap")
        result["volume_24h"]["value"] = btc.get("usd_24h_vol")

    # Fallback: try CoinGecko coins endpoint for richer data
    if result["btc_price"]["value"] is None:
        data2 = _get(
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            params={"localization": "false", "tickers": "false",
                    "community_data": "false", "developer_data": "false"},
        )
        if data2 and "market_data" in data2:
            md = data2["market_data"]
            result["btc_price"]["value"] = md.get("current_price", {}).get("usd")
            result["btc_price"]["change_24h"] = round(md.get("price_change_percentage_24h", 0) or 0, 2)
            result["market_cap"]["value"] = md.get("market_cap", {}).get("usd")
            result["volume_24h"]["value"] = md.get("total_volume", {}).get("usd")

    log.info("Price: $%s (%.2f%%)", result["btc_price"]["value"], result["btc_price"]["change_24h"] or 0)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# B) ON-CHAIN DATA — mempool.space
# ═══════════════════════════════════════════════════════════════════════════

def fetch_network_data():
    """Block height, difficulty adjustment, hashrate from mempool.space."""
    result = {
        "block_height": {"value": None, "source": "mempool.space"},
        "difficulty_adjustment": {"percent": None, "blocks_remaining": None, "estimated_date": None, "source": "mempool.space"},
        "hashrate": {"value": None, "raw_eh": None, "source": "mempool.space"},
    }

    # Block height
    data = _get("https://mempool.space/api/blocks/tip/height")
    if data is not None:
        result["block_height"]["value"] = int(data)

    # Difficulty adjustment
    data = _get("https://mempool.space/api/v1/difficulty-adjustment")
    if data:
        result["difficulty_adjustment"]["percent"] = round(data.get("difficultyChange", 0), 2)
        result["difficulty_adjustment"]["blocks_remaining"] = data.get("remainingBlocks")
        est = data.get("estimatedRetargetDate")
        if est:
            result["difficulty_adjustment"]["estimated_date"] = datetime.fromtimestamp(est / 1000, tz=timezone.utc).isoformat()

    # Hashrate (3-day average)
    data = _get("https://mempool.space/api/v1/mining/hashrate/3d")
    if data and "currentHashrate" in data:
        raw = float(data["currentHashrate"])
        eh = raw / 1e18
        result["hashrate"]["raw_eh"] = round(eh, 1)
        result["hashrate"]["value"] = f"{round(eh, 1)} EH/s"

    log.info("Network: block=%s, diff_adj=%.2f%%, hashrate=%s",
             result["block_height"]["value"],
             result["difficulty_adjustment"]["percent"] or 0,
             result["hashrate"]["value"])
    return result


def fetch_mempool_data():
    """Mempool size, fees from mempool.space."""
    result = {
        "mempool_size": {"tx_count": None, "vsize_mb": None, "source": "mempool.space"},
        "recommended_fees": {"fastest": None, "hour": None, "economy": None, "source": "mempool.space"},
    }

    # Mempool stats
    data = _get("https://mempool.space/api/mempool")
    if data:
        result["mempool_size"]["tx_count"] = data.get("count")
        vsize = data.get("vsize", 0)
        result["mempool_size"]["vsize_mb"] = round(vsize / 1e6, 1) if vsize else 0

    # Recommended fees
    data = _get("https://mempool.space/api/v1/fees/recommended")
    if data:
        result["recommended_fees"]["fastest"] = data.get("fastestFee")
        result["recommended_fees"]["hour"] = data.get("halfHourFee")
        result["recommended_fees"]["economy"] = data.get("economyFee")

    log.info("Mempool: %s txs, %.1f vMB, fees=%s/%s/%s",
             result["mempool_size"]["tx_count"],
             result["mempool_size"]["vsize_mb"] or 0,
             result["recommended_fees"]["fastest"],
             result["recommended_fees"]["hour"],
             result["recommended_fees"]["economy"])
    return result


def fetch_lightning_data():
    """Lightning Network stats from mempool.space."""
    result = {
        "lightning": {"node_count": None, "channel_count": None, "capacity_btc": None, "source": "mempool.space"},
    }

    data = _get("https://mempool.space/api/v1/lightning/statistics/latest")
    if data and "latest" in data:
        ln = data["latest"]
        result["lightning"]["node_count"] = ln.get("node_count")
        result["lightning"]["channel_count"] = ln.get("channel_count")
        cap = ln.get("total_capacity")
        if cap:
            result["lightning"]["capacity_btc"] = round(int(cap) / 1e8, 1)

    log.info("Lightning: %s nodes, %s channels, %s BTC",
             result["lightning"]["node_count"],
             result["lightning"]["channel_count"],
             result["lightning"]["capacity_btc"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# C) FEAR & GREED — alternative.me
# ═══════════════════════════════════════════════════════════════════════════

def fetch_fear_greed():
    """Fear & Greed index from alternative.me."""
    result = {"fear_greed": {"value": None, "label": None, "previous": None, "source": "alternative.me"}}

    data = _get("https://api.alternative.me/fng/?limit=2&format=json")
    if data and "data" in data and len(data["data"]) > 0:
        current = data["data"][0]
        result["fear_greed"]["value"] = int(current.get("value", 0))
        result["fear_greed"]["label"] = current.get("value_classification", "")
        if len(data["data"]) > 1:
            result["fear_greed"]["previous"] = int(data["data"][1].get("value", 0))

    log.info("Fear & Greed: %s (%s)", result["fear_greed"]["value"], result["fear_greed"]["label"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# D) FUTURES / FUNDING — Deribit (no auth, Binance geo-blocked)
# ═══════════════════════════════════════════════════════════════════════════

def fetch_derivatives():
    """Funding rate, open interest from Deribit public API."""
    result = {
        "funding_rate": {"value": None, "annualized": None, "source": "deribit"},
        "open_interest": {"btc": None, "usd": None, "source": "deribit"},
    }

    data = _get(
        "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
        params={"currency": "BTC", "kind": "future"},
    )
    if data and "result" in data:
        perp = None
        total_oi_usd = 0
        for f in data["result"]:
            total_oi_usd += float(f.get("open_interest", 0))
            if f.get("instrument_name") == "BTC-PERPETUAL":
                perp = f

        if perp:
            funding_8h = float(perp.get("funding_8h", 0))
            result["funding_rate"]["value"] = round(funding_8h, 8)
            result["funding_rate"]["annualized"] = round(funding_8h * 3 * 365 * 100, 2)

            mark = float(perp.get("mark_price", 0))
            if mark > 0 and total_oi_usd > 0:
                result["open_interest"]["usd"] = round(total_oi_usd)
                result["open_interest"]["btc"] = round(total_oi_usd / mark, 1)

    # Fallback: try Binance (may be geo-blocked)
    if result["funding_rate"]["value"] is None:
        binance = _get("https://fapi.binance.com/fapi/v1/fundingRate",
                        params={"symbol": "BTCUSDT", "limit": 1})
        if binance and isinstance(binance, list) and binance:
            rate = float(binance[0].get("fundingRate", 0))
            result["funding_rate"]["value"] = round(rate, 6)
            result["funding_rate"]["annualized"] = round(rate * 3 * 365 * 100, 2)
            result["funding_rate"]["source"] = "binance"

    log.info("Derivatives: funding=%.6f, OI=$%s",
             result["funding_rate"]["value"] or 0,
             result["open_interest"]["usd"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# E) EXCHANGE VOLUMES — CoinGecko
# ═══════════════════════════════════════════════════════════════════════════

def fetch_exchange_volumes():
    """Exchange volume as proxy for exchange flow."""
    result = {
        "exchange_volume": {"binance_btc": None, "coinbase_btc": None, "source": "coingecko"},
    }

    for exchange in ("binance", "coinbase-exchange"):
        data = _get(f"https://api.coingecko.com/api/v3/exchanges/{exchange}")
        if data:
            vol = data.get("trade_volume_24h_btc")
            key = "binance_btc" if "binance" in exchange else "coinbase_btc"
            if vol is not None:
                result["exchange_volume"][key] = round(float(vol), 1)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# F) BTC DOMINANCE — CoinGecko global + CoinPaprika fallback
# ═══════════════════════════════════════════════════════════════════════════

def fetch_dominance():
    """BTC market dominance percentage."""
    result = {"dominance": {"value": None, "source": "coingecko"}}

    data = _get("https://api.coingecko.com/api/v3/global")
    if data and "data" in data:
        dom = data["data"].get("market_cap_percentage", {}).get("btc")
        if dom is not None:
            result["dominance"]["value"] = round(dom, 2)
            log.info("Dominance (CoinGecko): %.2f%%", dom)
            return result

    # Fallback: CoinPaprika (no rate limit issues)
    data = _get("https://api.coinpaprika.com/v1/global")
    if data:
        dom = data.get("bitcoin_dominance_percentage")
        if dom is not None:
            result["dominance"]["value"] = round(float(dom), 2)
            result["dominance"]["source"] = "coinpaprika"
            log.info("Dominance (CoinPaprika fallback): %.2f%%", dom)
            return result

    log.warning("Dominance: all sources failed")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# G) MACRO — Gold, S&P 500, DXY
# ═══════════════════════════════════════════════════════════════════════════

def fetch_macro():
    """Gold, S&P 500, DXY from Yahoo Finance (free, no auth)."""
    result = {
        "gold": {"value": None, "source": "yahoo"},
        "sp500": {"value": None, "source": "yahoo"},
        "dxy": {"value": None, "source": "yahoo"},
    }

    yahoo_headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    for ticker, key in [("GC=F", "gold"), ("^GSPC", "sp500"), ("DX-Y.NYB", "dxy")]:
        data = _get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={"interval": "1d", "range": "1d"},
            custom_headers=yahoo_headers,
        )
        if data:
            res = data.get("chart", {}).get("result", [])
            if res:
                price = res[0].get("meta", {}).get("regularMarketPrice")
                if price is not None:
                    result[key]["value"] = round(float(price), 2)

    # DXY fallback: calculate from exchange rates if Yahoo fails
    if result["dxy"]["value"] is None:
        data = _get("https://api.exchangerate-api.com/v4/latest/USD")
        if data and "rates" in data:
            r = data["rates"]
            try:
                eurusd = 1.0 / r.get("EUR", 0.92)
                gbpusd = 1.0 / r.get("GBP", 0.79)
                jpy = r.get("JPY", 150)
                cad = r.get("CAD", 1.36)
                sek = r.get("SEK", 10.5)
                chf = r.get("CHF", 0.88)
                dxy = 50.14348112 * (eurusd ** -0.576) * (jpy ** 0.136) * (gbpusd ** -0.119) * (cad ** 0.091) * (sek ** 0.042) * (chf ** 0.036)
                result["dxy"]["value"] = round(dxy, 2)
                result["dxy"]["source"] = "exchangerate-api"
            except Exception:
                pass

    log.info("Macro: Gold=$%s, S&P=%s, DXY=%s",
             result["gold"]["value"], result["sp500"]["value"], result["dxy"]["value"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# H) HALVING COUNTDOWN — calculated
# ═══════════════════════════════════════════════════════════════════════════

def calc_halving():
    """Calculate halving countdown from known block data."""
    LAST_HALVING_DATE = date(2024, 4, 19)
    LAST_HALVING_BLOCK = 840_000
    NEXT_HALVING_BLOCK = 1_050_000
    BLOCKS_PER_DAY = 144

    today = date.today()
    days_since = (today - LAST_HALVING_DATE).days
    blocks_to_next = NEXT_HALVING_BLOCK - LAST_HALVING_BLOCK  # 210,000
    days_total = blocks_to_next / BLOCKS_PER_DAY  # ~1458 days
    days_to_next = max(0, round(days_total - days_since))

    return {
        "halving": {
            "days_since": days_since,
            "days_to_next": days_to_next,
            "next_block": NEXT_HALVING_BLOCK,
            "current_subsidy": 3.125,
            "progress_pct": round(days_since / days_total * 100, 1),
            "source": "calculated",
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# G) WHALE DETECTION — mempool.space large txs
# ═══════════════════════════════════════════════════════════════════════════

def fetch_whale_txs():
    """Detect large unconfirmed transactions from mempool."""
    result = {"whale_moves": {"count": 0, "total_btc": 0, "txs": [], "source": "mempool.space"}}

    data = _get("https://mempool.space/api/mempool/recent")
    if data and isinstance(data, list):
        for tx in data[:100]:
            value_sat = tx.get("value", 0)
            value_btc = value_sat / 1e8
            if value_btc >= 100:  # 100+ BTC = whale
                result["whale_moves"]["count"] += 1
                result["whale_moves"]["total_btc"] += value_btc
                if len(result["whale_moves"]["txs"]) < 5:
                    result["whale_moves"]["txs"].append({
                        "txid": tx.get("txid", "")[:12],
                        "btc": round(value_btc, 2),
                    })
        result["whale_moves"]["total_btc"] = round(result["whale_moves"]["total_btc"], 2)

    log.info("Whales: %d txs, %.1f BTC total", result["whale_moves"]["count"], result["whale_moves"]["total_btc"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# H) OPTIONAL KEYED APIS
# ═══════════════════════════════════════════════════════════════════════════

def fetch_glassnode():
    """Glassnode on-chain metrics (if API key available)."""
    result = {
        "sopr": {"value": None, "source": "unavailable"},
        "nupl": {"value": None, "source": "unavailable"},
        "realized_price": {"value": None, "source": "unavailable"},
    }

    key = os.environ.get("GLASSNODE_API_KEY", "")
    if not key:
        return result

    for metric, field in [("sopr", "sopr"), ("nupl", "nupl"), ("market/price_realized_usd", "realized_price")]:
        data = _get(
            f"https://api.glassnode.com/v1/metrics/{metric}",
            params={"a": "BTC", "api_key": key, "i": "24h", "s": str(int(time.time()) - 86400)},
        )
        if data and isinstance(data, list) and data:
            val = data[-1].get("v")
            if val is not None:
                result[field]["value"] = round(float(val), 4) if field != "realized_price" else round(float(val), 2)
                result[field]["source"] = "glassnode"

    return result


def fetch_coinglass():
    """CoinGlass derivatives data (if API key available)."""
    result = {
        "cg_funding_rate": {"value": None, "source": "unavailable"},
        "cg_open_interest": {"value": None, "source": "unavailable"},
    }

    key = os.environ.get("COINGLASS_API_KEY", "")
    if not key:
        return result

    data = _get(
        "https://open-api.coinglass.com/public/v2/funding",
        params={"symbol": "BTC", "time_type": "h8"},
    )
    if data and data.get("data"):
        items = data["data"]
        if isinstance(items, list) and items:
            result["cg_funding_rate"]["value"] = items[0].get("rate")
            result["cg_funding_rate"]["source"] = "coinglass"

    return result


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL SCORE CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

def calc_signal_score(signals):
    """Count bull/bear/neutral signals from fetched data."""
    bull = 0
    bear = 0
    neutral = 0

    # Fear & Greed
    fng = signals.get("fear_greed", {}).get("value")
    if fng is not None:
        if fng > 60:
            bull += 1
        elif fng < 40:
            bear += 1
        else:
            neutral += 1

    # Price 24h change
    change = signals.get("btc_price", {}).get("change_24h")
    if change is not None:
        if change > 0:
            bull += 1
        elif change < -2:
            bear += 1
        else:
            neutral += 1

    # Difficulty adjustment (positive = miners investing = bullish)
    diff = signals.get("difficulty_adjustment", {}).get("percent")
    if diff is not None:
        if diff > 0:
            bull += 1
        elif diff < -3:
            bear += 1
        else:
            neutral += 1

    # Funding rate
    fr = signals.get("funding_rate", {}).get("value")
    if fr is not None:
        if fr > 0:
            bull += 1
        elif fr < -0.001:
            bear += 1
        else:
            neutral += 1

    # Mempool congestion
    vsize = signals.get("mempool_size", {}).get("vsize_mb")
    if vsize is not None:
        if vsize > 200:
            bear += 1
        elif vsize < 50:
            bull += 1
        else:
            neutral += 1

    return {"bull_count": bull, "bear_count": bear, "neutral_count": neutral}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN FETCHER
# ═══════════════════════════════════════════════════════════════════════════

def fetch_all_signals():
    """Fetch all signals and return consolidated dict."""
    t0 = time.time()
    signals = {"updated_at": datetime.now(timezone.utc).isoformat()}

    # Load previous signals for cache-first fallback on failures
    prev = _load_previous_signals()

    # Each fetch is wrapped in try/except so one failure doesn't kill the rest
    # CoinGecko calls (price, dominance, exchange_volume) are spaced to avoid 429s
    fetchers = [
        ("price", fetch_price_data),
        ("network", fetch_network_data),
        ("mempool", fetch_mempool_data),
        ("lightning", fetch_lightning_data),
        ("fear_greed", fetch_fear_greed),
        ("derivatives", fetch_derivatives),
        ("dominance", fetch_dominance),
        ("macro", fetch_macro),
        ("exchange_volume", fetch_exchange_volumes),
        ("halving", calc_halving),
        ("whales", fetch_whale_txs),
        ("glassnode", fetch_glassnode),
        ("coinglass", fetch_coinglass),
    ]

    # Track which CoinGecko fetchers need rate-limit spacing
    coingecko_fetchers = {"price", "dominance", "exchange_volume"}

    for name, fn in fetchers:
        try:
            # Rate-limit protection: pause 1.5s between CoinGecko calls
            if name in coingecko_fetchers:
                time.sleep(1.5)
            result = fn()
            signals.update(result)
        except Exception as e:
            log.error("Fetcher '%s' crashed: %s", name, e)

    # Cache-first fallback: fill any NULLs from previous good values
    for key, val in signals.items():
        if isinstance(val, dict):
            for subkey, subval in val.items():
                if subval is None and key in prev and isinstance(prev.get(key), dict):
                    cached_val = prev[key].get(subkey)
                    if cached_val is not None:
                        val[subkey] = cached_val
                        log.info("Cache fallback: %s.%s = %s", key, subkey, cached_val)

    # Calculate composite signal score
    signals["signal_score"] = calc_signal_score(signals)

    elapsed = time.time() - t0
    log.info("All signals fetched in %.1fs — bull=%d bear=%d neutral=%d",
             elapsed,
             signals["signal_score"]["bull_count"],
             signals["signal_score"]["bear_count"],
             signals["signal_score"]["neutral_count"])

    return signals


def write_signals():
    """Fetch all signals and write to data/signals.json."""
    signals = fetch_all_signals()

    # Atomic write via temp file
    tmp_path = SIGNALS_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(signals, indent=2, default=str))
    tmp_path.rename(SIGNALS_PATH)

    log.info("Wrote %s (%d bytes)", SIGNALS_PATH, SIGNALS_PATH.stat().st_size)
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# CLI ENTRY
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("=== Signal Data Fetcher starting ===")
    signals = write_signals()
    price = signals.get("btc_price", {}).get("value", "N/A")
    fng = signals.get("fear_greed", {}).get("value", "N/A")
    log.info("=== Done. BTC=$%s F&G=%s ===", price, fng)
