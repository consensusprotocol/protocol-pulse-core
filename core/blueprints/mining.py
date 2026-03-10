"""
MINING INTEL BLUEPRINT — Protocol Pulse
=========================================
Routes:
  GET  /mining-intel                          — World-class mining intelligence page
  GET  /api/mining/dashboard                  — Hashprice, hashrate, difficulty, block reward
  GET  /api/mining/pools                      — Pool market share (mempool.space, 1w)
  GET  /api/mining/profitability              — Per-ASIC profitability at given $/kWh
  GET  /api/mining/blockware                  — Blockware Intelligence RSS (4h cache)

Data sources: mempool.space (free), CoinGecko (free), Blockware RSS
"""

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import requests
from flask import Blueprint, jsonify, render_template, request

logger = logging.getLogger(__name__)

mining_bp = Blueprint("mining_intel", __name__)

# ── In-memory cache (avoids hammering free APIs) ─────────────────────────────

_CACHE: dict[str, tuple[float, Any]] = {}

def _cache_get(key: str, ttl: int) -> Any:
    entry = _CACHE.get(key)
    if entry and (time.time() - entry[0]) < ttl:
        return entry[1]
    return None

def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.time(), value)


# ── ASIC hardware table (pre-seeded, user adjusts electricity) ───────────────

ASIC_MODELS = [
    {"model": "Antminer S21 Pro",  "th_s": 234,  "watts": 3510, "efficiency_w_th": 15.0},
    {"model": "Antminer S21",      "th_s": 200,  "watts": 3500, "efficiency_w_th": 17.5},
    {"model": "Antminer T21",      "th_s": 190,  "watts": 3610, "efficiency_w_th": 19.0},
    {"model": "Antminer S19 XP",   "th_s": 140,  "watts": 3010, "efficiency_w_th": 21.5},
    {"model": "Antminer S19 Pro",  "th_s": 110,  "watts": 3250, "efficiency_w_th": 29.5},
    {"model": "Whatsminer M60S",   "th_s": 186,  "watts": 3441, "efficiency_w_th": 18.5},
    {"model": "Whatsminer M50S",   "th_s": 126,  "watts": 3276, "efficiency_w_th": 26.0},
]


def _fetch_mempool_hashrate() -> dict:
    """Fetch current hashrate + difficulty from mempool.space."""
    try:
        r = requests.get(
            "https://mempool.space/api/v1/mining/hashrate/1m",
            timeout=10,
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        if r.ok:
            return r.json()
    except Exception as e:
        logger.warning("mempool hashrate fetch error: %s", e)
    return {}


def _fetch_difficulty_adjustment() -> dict:
    """Fetch next difficulty adjustment estimate."""
    try:
        r = requests.get(
            "https://mempool.space/api/v1/difficulty-adjustment",
            timeout=10,
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        if r.ok:
            return r.json()
    except Exception as e:
        logger.warning("difficulty adjustment fetch error: %s", e)
    return {}


def _fetch_btc_price() -> float | None:
    """Fetch BTC/USD from CoinGecko free tier."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=10,
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        if r.ok:
            return r.json().get("bitcoin", {}).get("usd")
    except Exception as e:
        logger.warning("CoinGecko price fetch error: %s", e)
    return None


def _fetch_block_tip() -> int | None:
    """Get current block height."""
    try:
        r = requests.get(
            "https://mempool.space/api/blocks/tip/height",
            timeout=8,
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        if r.ok:
            return int(r.text.strip())
    except Exception:
        pass
    return None


def _fetch_mempool_fees() -> dict:
    try:
        r = requests.get(
            "https://mempool.space/api/v1/fees/recommended",
            timeout=8,
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}


def _compute_hashprice(hashrate_eh: float, btc_price: float) -> float:
    """
    Hash price in $/TH/day.
    Formula: (3.125 BTC subsidy * 144 blocks/day * BTC price) / (hashrate in TH/s)
    hashrate_eh: exahash/s → multiply by 1e6 for TH/s
    """
    th_s = hashrate_eh * 1e6  # EH/s → TH/s
    if th_s <= 0:
        return 0.0
    return round((3.125 * 144 * btc_price) / th_s, 4)


def _blocks_to_halving(current_height: int) -> int:
    """Blocks remaining until next halving at 1,050,000."""
    NEXT_HALVING = 1_050_000
    return max(0, NEXT_HALVING - current_height)


# ── Page route ───────────────────────────────────────────────────────────────

@mining_bp.route("/mining-intel")
def mining_intel_page():
    """Bitcoin Mining Intelligence Hub — the spec's flagship page."""
    return render_template("mining_intel.html")


# ── API: dashboard ───────────────────────────────────────────────────────────

@mining_bp.route("/api/mining/dashboard")
def api_mining_dashboard():
    """
    Consolidated mining dashboard data.
    Returns: hashprice, hashrate, difficulty, next adjustment, block reward.
    Cached 90s.
    """
    cached = _cache_get("mining_dashboard", 90)
    if cached:
        return jsonify(cached)

    result: dict[str, Any] = {
        "hashrate_eh": None,
        "difficulty": None,
        "difficulty_formatted": None,
        "btc_price_usd": None,
        "hash_price_usd_per_th": None,        # $/TH/day (the KEY metric)
        "hash_price_usd_per_ph": None,         # $/PH/day (alternative display)
        "block_subsidy_btc": 3.125,
        "block_height": None,
        "blocks_to_halving": None,
        "days_to_halving": None,
        "next_adjustment_pct": None,
        "blocks_until_adjustment": None,
        "estimated_adjustment_days": None,
        "epoch_progress_pct": None,
        "daily_revenue_btc": None,             # total network miner revenue/day
        "daily_revenue_usd": None,
        "mempool_fee_low": None,
        "mempool_fee_mid": None,
        "mempool_fee_high": None,
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Hashrate + difficulty
    hashrate_data = _fetch_mempool_hashrate()
    if hashrate_data:
        raw_hashrate = hashrate_data.get("currentHashrate") or 0
        result["hashrate_eh"] = round(raw_hashrate / 1e18, 2) if raw_hashrate else None
        diff = hashrate_data.get("currentDifficulty") or 0
        result["difficulty"] = diff
        if diff:
            result["difficulty_formatted"] = f"{diff / 1e12:.2f}T"

    # Difficulty adjustment
    adj_data = _fetch_difficulty_adjustment()
    if adj_data:
        result["next_adjustment_pct"] = round(adj_data.get("difficultyChange", 0), 2)
        remaining = adj_data.get("remainingBlocks", 0)
        result["blocks_until_adjustment"] = remaining
        remaining_time = adj_data.get("remainingTime", 0)  # seconds
        if remaining_time:
            result["estimated_adjustment_days"] = round(remaining_time / 86400, 1)
        if remaining is not None:
            result["epoch_progress_pct"] = round(
                max(0, min(100, ((2016 - remaining) / 2016) * 100)), 1
            )

    # Block height + halving countdown
    height = _fetch_block_tip()
    if height:
        result["block_height"] = height
        bth = _blocks_to_halving(height)
        result["blocks_to_halving"] = bth
        result["days_to_halving"] = round(bth * 10 / 1440, 1)  # ~10min blocks

    # BTC price
    btc_price = _fetch_btc_price()
    if btc_price:
        result["btc_price_usd"] = btc_price

    # Hash price (requires both hashrate + price)
    if result["hashrate_eh"] and btc_price:
        hp_per_th = _compute_hashprice(result["hashrate_eh"], btc_price)
        result["hash_price_usd_per_th"] = hp_per_th
        result["hash_price_usd_per_ph"] = round(hp_per_th * 1000, 4)
        # Daily network revenue (3.125 subsidy * 144 blocks * price — fees not included in base)
        result["daily_revenue_btc"] = round(3.125 * 144, 2)
        result["daily_revenue_usd"] = round(3.125 * 144 * btc_price, 0)

    # Mempool fees
    fees = _fetch_mempool_fees()
    if fees:
        result["mempool_fee_low"] = fees.get("economyFee")
        result["mempool_fee_mid"] = fees.get("halfHourFee")
        result["mempool_fee_high"] = fees.get("fastestFee")

    _cache_set("mining_dashboard", result)
    return jsonify(result)


# ── API: pools ────────────────────────────────────────────────────────────────

@mining_bp.route("/api/mining/pools")
def api_mining_pools():
    """
    Pool market share from mempool.space last 7 days.
    Cached 5 min.
    """
    cached = _cache_get("mining_pools", 300)
    if cached:
        return jsonify(cached)

    try:
        r = requests.get(
            "https://mempool.space/api/v1/mining/pools/1w",
            timeout=12,
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        if not r.ok:
            return jsonify({"pools": [], "error": "upstream error", "hhi": None}), 502

        data = r.json()
        pools_raw = data.get("pools", [])
        total_blocks = sum(p.get("blockCount", 0) for p in pools_raw)

        pools = []
        hhi = 0.0
        for p in pools_raw[:10]:
            blocks = p.get("blockCount", 0)
            share = round((blocks / total_blocks * 100), 2) if total_blocks else 0
            hhi += share ** 2
            pools.append({
                "name": p.get("name", "Unknown"),
                "slug": p.get("slug", ""),
                "share_pct": share,
                "block_count": blocks,
            })

        hhi_r = round(hhi)
        concentration = (
            "HIGH" if hhi_r > 2500
            else ("MODERATE" if hhi_r > 1500 else "HEALTHY")
        )
        top3 = sum(p["share_pct"] for p in pools[:3])
        result = {
            "pools": pools,
            "hhi": hhi_r,
            "concentration_label": concentration,
            "top3_share_pct": round(top3, 1),
            "centralization_warning": top3 > 51,
            "updated_at": datetime.utcnow().isoformat(),
        }
        _cache_set("mining_pools", result)
        return jsonify(result)

    except Exception as e:
        logger.error("mining pools error: %s", e)
        return jsonify({"pools": [], "error": "internal error", "hhi": None}), 500


# ── API: profitability calculator ─────────────────────────────────────────────

@mining_bp.route("/api/mining/profitability")
def api_mining_profitability():
    """
    Per-ASIC profitability given electricity cost.
    Query param: electricity ($/kWh, default 0.07)
    Computes: daily revenue, daily power cost, daily profit, break-even BTC price.
    """
    try:
        electricity = float(request.args.get("electricity", 0.07))
        electricity = max(0.01, min(0.30, electricity))  # clamp
    except (ValueError, TypeError):
        electricity = 0.07

    # Get current data (use cache if available)
    dashboard_cached = _cache_get("mining_dashboard", 90)
    if dashboard_cached:
        hash_price_per_th = dashboard_cached.get("hash_price_usd_per_th")
        btc_price = dashboard_cached.get("btc_price_usd")
    else:
        # Fetch fresh
        hashrate_data = _fetch_mempool_hashrate()
        btc_price = _fetch_btc_price()
        hash_price_per_th = None
        if hashrate_data and btc_price:
            raw = hashrate_data.get("currentHashrate") or 0
            eh = round(raw / 1e18, 2) if raw else None
            if eh:
                hash_price_per_th = _compute_hashprice(eh, btc_price)

    models_data = []
    for asic in ASIC_MODELS:
        th = asic["th_s"]
        watts = asic["watts"]
        w_th = asic["efficiency_w_th"]

        daily_kwh = (watts * 24) / 1000
        daily_power_cost = round(daily_kwh * electricity, 2)

        if hash_price_per_th:
            daily_revenue = round(hash_price_per_th * th, 2)
            daily_profit = round(daily_revenue - daily_power_cost, 2)
            # Break-even BTC price: solve for P where revenue = power cost
            # daily_revenue = (3.125 * 144 * P / (hashrate_eh * 1e6)) * th
            # We know hash_price_per_th = daily_revenue / th
            # So break-even P = (daily_power_cost / th) * (hashrate_eh * 1e6) / (3.125 * 144)
            # Simplified: break_even_P = (daily_power_cost / hash_price_per_th) * btc_price / th
            if hash_price_per_th > 0 and btc_price:
                be_btc = round((daily_power_cost / th / hash_price_per_th) * btc_price, 0)
            else:
                be_btc = None
            roi_days = (
                round(daily_revenue / max(0.01, daily_profit) * 1, 0)
                if daily_profit > 0 else None
            )
        else:
            daily_revenue = None
            daily_profit = None
            be_btc = None
            roi_days = None

        models_data.append({
            "model": asic["model"],
            "th_s": th,
            "watts": watts,
            "efficiency_w_th": w_th,
            "daily_kwh": round(daily_kwh, 1),
            "daily_power_cost_usd": daily_power_cost,
            "daily_revenue_usd": daily_revenue,
            "daily_profit_usd": daily_profit,
            "break_even_btc_price": be_btc,
            "profitable": daily_profit > 0 if daily_profit is not None else None,
        })

    return jsonify({
        "electricity_usd_kwh": electricity,
        "btc_price_usd": btc_price,
        "hash_price_usd_per_th": hash_price_per_th,
        "models": models_data,
        "updated_at": datetime.utcnow().isoformat(),
    })


# ── API: Blockware Intelligence RSS ──────────────────────────────────────────

@mining_bp.route("/api/mining/blockware")
def api_mining_blockware():
    """
    Parse Blockware Intelligence Substack RSS feed.
    Falls back gracefully if 403/network error.
    Cached 4h.
    """
    cached = _cache_get("mining_blockware", 14400)
    if cached:
        return jsonify(cached)

    FEED_URLS = [
        "https://blockwareintelligence.substack.com/feed",
        "https://blockwareintelligence.substack.com/feed.xml",
    ]

    articles = []
    error_msg = None

    for feed_url in FEED_URLS:
        try:
            r = requests.get(
                feed_url,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ProtocolPulseBot/1.0)",
                    "Accept": "application/rss+xml, application/xml, text/xml",
                },
            )
            if r.status_code == 403:
                logger.warning("Blockware RSS returned 403 — trying fallback URL")
                continue
            if not r.ok:
                logger.warning("Blockware RSS error %s for %s", r.status_code, feed_url)
                continue

            root = ET.fromstring(r.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//item")

            for item in items[:5]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date_str = (item.findtext("pubDate") or "").strip()
                desc_raw = (item.findtext("description") or "").strip()

                # Strip HTML tags from description
                import re
                desc_clean = re.sub(r"<[^>]+>", "", desc_raw)[:300].strip()

                # Parse date
                date_formatted = pub_date_str
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_date_str)
                    date_formatted = dt.strftime("%b %d, %Y")
                except Exception:
                    pass

                articles.append({
                    "title": title,
                    "link": link,
                    "date": date_formatted,
                    "summary": desc_clean,
                })

            if articles:
                break  # Success

        except ET.ParseError as e:
            logger.warning("Blockware RSS parse error: %s", e)
            error_msg = "RSS parse error"
        except Exception as e:
            logger.warning("Blockware RSS fetch error: %s", e)
            error_msg = str(e)

    if not articles:
        # Return graceful empty state — never crash
        logger.warning("Blockware RSS: no articles fetched (error: %s)", error_msg)
        result = {
            "articles": [],
            "source": "Blockware Intelligence",
            "feed_url": FEED_URLS[0],
            "error": error_msg or "No articles available",
            "updated_at": datetime.utcnow().isoformat(),
        }
    else:
        result = {
            "articles": articles,
            "source": "Blockware Intelligence",
            "feed_url": FEED_URLS[0],
            "updated_at": datetime.utcnow().isoformat(),
        }

    _cache_set("mining_blockware", result)
    return jsonify(result)
