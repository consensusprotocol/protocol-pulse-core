#!/usr/bin/env python3
"""
Protocol Pulse Perception Layer — Session 4
============================================
Alternative intelligence aggregator. Fills the gaps that Newhedge/Perception.to
address: narrative velocity, social sentiment, Lightning health, macro structure,
trending alt rotation, and on-chain fundamentals beyond what signal_data_fetcher covers.

All sources are free public APIs, no auth required.
Runs every 15 minutes via cron, writes to data/perception_layer.json.
Also called on-demand by Panopticon SSE stream for the intelligence_update event.

Sources:
  - CoinGecko global       : BTC dominance, total mcap, 24h volume, active coins
  - CoinGecko trending     : Narrative proxy (what's rotating into)
  - Blockchain.com stats   : On-chain fundamentals (tx count, miner revenue, block times)
  - Mempool.space Lightning : Network health (nodes, channels, capacity)
  - Mempool.space fees     : Fee market signal (low fees = accumulation phase)
  - CryptoCompare social   : BTC social sentiment (Reddit, Twitter, Telegram followers)
  - alternative.me FG hist : Fear/Greed 7-day trend (direction matters more than value)
"""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BASE_DIR = Path("/home/ultron/protocol_pulse")
DATA_DIR = BASE_DIR / "data"
CACHE_PATH = DATA_DIR / "perception_layer.json"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "ProtocolPulse/PerceptionLayer/1.0 paul@consensusprotocol.org",
    "Accept": "application/json",
}
TIMEOUT = 10
_cache: dict = {}
_cache_ttl = 900  # 15 min


def _get(url: str, params: dict = None) -> Optional[dict]:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.debug("Perception GET %s: %s", url[:70], e)
        return None


def _cached_load() -> Optional[dict]:
    if CACHE_PATH.exists():
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < _cache_ttl:
            try:
                return json.loads(CACHE_PATH.read_text())
            except Exception:
                pass
    return None


# ── Individual fetchers ───────────────────────────────────────────────────────

def fetch_global_market() -> dict:
    """CoinGecko global — BTC dominance, total market cap, 24h volume."""
    d = _get("https://api.coingecko.com/api/v3/global")
    if not d:
        return {}
    data = d.get("data", {})
    btc_dom = data.get("market_cap_percentage", {}).get("btc", 0)
    total_mcap = data.get("total_market_cap", {}).get("usd", 0)
    total_vol = data.get("total_volume", {}).get("usd", 0)

    # Market structure signal
    if btc_dom > 60:
        dom_signal = "btc_dominance_peak"
        dom_note = "BTC absorbing alt capital — risk-off rotation"
    elif btc_dom > 55:
        dom_signal = "btc_dominant"
        dom_note = "BTC leading — typical bull market structure"
    elif btc_dom < 45:
        dom_signal = "alt_season"
        dom_note = "Alt coins outperforming — risk-on rotation"
    else:
        dom_signal = "neutral"
        dom_note = "Mixed market structure"

    return {
        "btc_dominance_pct": round(btc_dom, 2),
        "total_mcap_usd": total_mcap,
        "total_mcap_t": round(total_mcap / 1e12, 3),
        "total_vol_24h_usd": total_vol,
        "total_vol_24h_b": round(total_vol / 1e9, 1),
        "active_coins": data.get("active_cryptocurrencies", 0),
        "dominance_signal": dom_signal,
        "dominance_note": dom_note,
        "btc_signal": "bullish" if btc_dom > 55 else "bearish" if btc_dom < 45 else "neutral",
        "source": "CoinGecko Global",
    }


def fetch_trending_narratives() -> dict:
    """CoinGecko trending — what capital is rotating into (narrative proxy)."""
    d = _get("https://api.coingecko.com/api/v3/search/trending")
    if not d:
        return {"trending_coins": [], "narrative_signal": "unknown"}

    coins = []
    for item in d.get("coins", [])[:7]:
        c = item.get("item", {})
        coins.append({
            "symbol": c.get("symbol", "?"),
            "name": c.get("name", "?"),
            "rank": c.get("market_cap_rank"),
            "score": c.get("score", 0),
        })

    # Narrative classification
    symbols = [c["symbol"].upper() for c in coins]
    has_l2 = any(s in symbols for s in ["ARB", "OP", "MATIC", "STRK", "ZK", "SCROLL"])
    has_ai = any(s in symbols for s in ["TAO", "FET", "AGIX", "NEAR", "ICP", "RENDER"])
    has_defi = any(s in symbols for s in ["UNI", "AAVE", "MKR", "CRV", "GMX", "PENDLE"])
    has_meme = any(s in symbols for s in ["DOGE", "SHIB", "PEPE", "FLOKI", "WIF", "BONK"])

    narratives = []
    if has_l2:   narratives.append("Layer-2 scaling")
    if has_ai:   narratives.append("AI/DePIN")
    if has_defi: narratives.append("DeFi")
    if has_meme: narratives.append("Meme/Speculation")
    if not narratives: narratives.append("BTC-adjacent")

    # Meme rotation = risk-on = historically late-cycle
    btc_signal = "bearish" if has_meme else "bullish" if has_ai or has_defi else "neutral"

    return {
        "trending_coins": coins,
        "active_narratives": narratives,
        "has_meme_rotation": has_meme,
        "has_ai_rotation": has_ai,
        "narrative_signal": ", ".join(narratives),
        "btc_signal": btc_signal,
        "note": "Meme rotation signals late-cycle risk. AI/DeFi rotation signals mid-cycle strength.",
        "source": "CoinGecko Trending",
    }


def fetch_onchain_fundamentals() -> dict:
    """Blockchain.com stats — on-chain fundamentals not in signals.json."""
    d = _get("https://api.blockchain.info/stats")
    if not d:
        return {}

    tx_count = d.get("n_tx", 0)
    miners_rev_usd = d.get("miners_revenue_usd", 0)
    minutes_per_block = d.get("minutes_between_blocks", 10)
    difficulty = d.get("difficulty", 0)
    hash_rate = d.get("hash_rate", 0)  # GH/s from blockchain.com

    # Miner capitulation signal
    if miners_rev_usd < 10_000_000:
        miner_signal = "capitulation_risk"
        miner_note = "Miner revenue critically low — capitulation pressure"
    elif miners_rev_usd < 20_000_000:
        miner_signal = "stress"
        miner_note = "Miner revenue below sustainability threshold"
    elif miners_rev_usd > 50_000_000:
        miner_signal = "healthy"
        miner_note = "Miners highly profitable — hash rate expansion likely"
    else:
        miner_signal = "normal"
        miner_note = "Miner economics within normal range"

    # Block time signal
    if minutes_per_block > 12:
        block_signal = "slow_blocks"
    elif minutes_per_block < 8:
        block_signal = "fast_blocks"
    else:
        block_signal = "normal"

    return {
        "tx_count_24h": tx_count,
        "miners_revenue_usd": miners_rev_usd,
        "miners_revenue_m": round(miners_rev_usd / 1e6, 2),
        "minutes_between_blocks": round(minutes_per_block, 2),
        "difficulty": difficulty,
        "estimated_btc_sent": d.get("estimated_btc_sent", 0),
        "total_fees_btc": d.get("total_fees_btc", 0),
        "miner_signal": miner_signal,
        "miner_note": miner_note,
        "block_signal": block_signal,
        "btc_signal": "bearish" if miner_signal == "capitulation_risk" else "bullish" if miner_signal == "healthy" else "neutral",
        "source": "Blockchain.com Stats",
    }


def fetch_lightning_health() -> dict:
    """Mempool.space Lightning — network health and growth signal."""
    d = _get("https://mempool.space/api/v1/lightning/statistics/latest")
    if not d:
        return {}
    latest = d.get("latest", {})

    node_count = latest.get("node_count", 0)
    channel_count = latest.get("channel_count", 0)
    capacity_sats = latest.get("total_capacity", 0)
    capacity_btc = round(capacity_sats / 1e8, 2) if capacity_sats else 0
    avg_capacity = round(capacity_sats / channel_count / 1e8, 4) if channel_count else 0

    # Health classification
    if node_count > 20000:
        health = "excellent"
        note = "Lightning network at full scale — institutional adoption underway"
    elif node_count > 15000:
        health = "healthy"
        note = "Lightning network growing steadily"
    else:
        health = "developing"
        note = "Lightning network still in growth phase"

    return {
        "node_count": node_count,
        "channel_count": channel_count,
        "capacity_btc": capacity_btc,
        "capacity_sats": capacity_sats,
        "avg_channel_capacity_btc": avg_capacity,
        "network_health": health,
        "health_note": note,
        "btc_signal": "bullish" if health in ("excellent", "healthy") else "neutral",
        "source": "mempool.space Lightning",
    }


def fetch_fee_market() -> dict:
    """Mempool fee market signal — low fees signal accumulation, high fees signal congestion."""
    d = _get("https://mempool.space/api/v1/fees/recommended")
    if not d:
        return {}

    fastest = d.get("fastestFee", 0)
    hour = d.get("hourFee", 0)
    economy = d.get("economyFee", 0)

    # Fee signal
    if fastest > 100:
        signal = "high_congestion"
        note = "Mempool congested — high on-chain activity or block space demand"
        btc_signal = "bullish"  # high activity = bullish demand
    elif fastest > 30:
        signal = "moderate"
        note = "Normal fee environment"
        btc_signal = "neutral"
    elif fastest <= 5:
        signal = "accumulation_phase"
        note = "Near-zero fees — low on-chain activity, classic accumulation signal"
        btc_signal = "neutral"  # historically precedes bull runs
    else:
        signal = "low"
        note = "Low fee environment — ample block space"
        btc_signal = "neutral"

    return {
        "fastest_fee_sat_vb": fastest,
        "hour_fee_sat_vb": hour,
        "economy_fee_sat_vb": economy,
        "fee_signal": signal,
        "fee_note": note,
        "btc_signal": btc_signal,
        "source": "mempool.space Fees",
    }


def fetch_social_sentiment() -> dict:
    """CryptoCompare social data — Reddit/Twitter/Telegram BTC community metrics."""
    d = _get("https://min-api.cryptocompare.com/data/social/coin/histo/day?fsym=BTC&limit=7")
    if not d:
        return {}

    data_list = d.get("Data", {}).get("Data", [])
    if not data_list:
        return {}

    latest = data_list[-1] if data_list else {}
    prev = data_list[-7] if len(data_list) >= 7 else data_list[0]

    reddit_subs = latest.get("reddit_subscribers", 0)
    twitter_followers = latest.get("twitter_followers", 0)
    fb_likes = latest.get("fb_likes", 0)
    points = latest.get("points", 0)
    comments_per_hr = latest.get("reddit_comments_per_hour", 0)
    posts_per_hr = latest.get("reddit_posts_per_hour", 0)

    # Week-over-week sentiment velocity
    prev_points = prev.get("points", points) if prev else points
    sentiment_change = round(((points - prev_points) / prev_points * 100) if prev_points else 0, 1)

    if sentiment_change > 20:
        velocity = "surging"
        btc_signal = "bullish"
    elif sentiment_change > 5:
        velocity = "rising"
        btc_signal = "bullish"
    elif sentiment_change < -20:
        velocity = "collapsing"
        btc_signal = "bearish"
    elif sentiment_change < -5:
        velocity = "declining"
        btc_signal = "bearish"
    else:
        velocity = "stable"
        btc_signal = "neutral"

    return {
        "reddit_subscribers": reddit_subs,
        "twitter_followers": twitter_followers,
        "fb_likes": fb_likes,
        "social_points": points,
        "reddit_comments_per_hr": comments_per_hr,
        "reddit_posts_per_hr": posts_per_hr,
        "sentiment_velocity_7d_pct": sentiment_change,
        "velocity_label": velocity,
        "btc_signal": btc_signal,
        "note": f"Social engagement {velocity} ({sentiment_change:+.1f}% vs 7 days ago)",
        "source": "CryptoCompare Social",
    }


def fetch_fg_trend() -> dict:
    """Fear & Greed 7-day trend — direction matters more than absolute value."""
    d = _get("https://api.alternative.me/fng/?limit=7&format=json")
    if not d:
        return {}

    data = d.get("data", [])
    if not data:
        return {}

    values = [int(x.get("value", 50)) for x in data]
    latest = values[0]
    oldest = values[-1]
    trend_delta = latest - oldest

    if trend_delta > 15:
        trend = "rapidly_improving"
        btc_signal = "bullish"
        note = f"F&G rising sharply ({oldest} -> {latest}) — sentiment recovery"
    elif trend_delta > 5:
        trend = "improving"
        btc_signal = "bullish"
        note = f"F&G trending up ({oldest} -> {latest})"
    elif trend_delta < -15:
        trend = "rapidly_deteriorating"
        btc_signal = "bearish"
        note = f"F&G collapsing ({oldest} -> {latest}) — capitulation building"
    elif trend_delta < -5:
        trend = "deteriorating"
        btc_signal = "bearish"
        note = f"F&G trending down ({oldest} -> {latest})"
    else:
        trend = "stable"
        btc_signal = "neutral"
        note = f"F&G stable at {latest}"

    return {
        "current": latest,
        "7d_ago": oldest,
        "7d_delta": trend_delta,
        "trend": trend,
        "7d_values": values,
        "btc_signal": btc_signal,
        "note": note,
        "label": data[0].get("value_classification", ""),
        "source": "alternative.me F&G",
    }


# ── Master aggregator ─────────────────────────────────────────────────────────

def compute_composite_signal(layers: dict) -> dict:
    """
    Aggregate all layer signals into a composite Perception Score.
    Weights: on-chain (30%), market structure (25%), sentiment (20%), 
             social velocity (15%), Lightning (10%)
    """
    signals = {
        "global": layers.get("global_market", {}).get("btc_signal", "neutral"),
        "trending": layers.get("trending_narratives", {}).get("btc_signal", "neutral"),
        "onchain": layers.get("onchain_fundamentals", {}).get("btc_signal", "neutral"),
        "lightning": layers.get("lightning_health", {}).get("btc_signal", "neutral"),
        "fees": layers.get("fee_market", {}).get("btc_signal", "neutral"),
        "social": layers.get("social_sentiment", {}).get("btc_signal", "neutral"),
        "fg_trend": layers.get("fg_trend", {}).get("btc_signal", "neutral"),
    }

    weights = {"global": 0.25, "trending": 0.10, "onchain": 0.30,
               "lightning": 0.10, "fees": 0.05, "social": 0.10, "fg_trend": 0.10}

    score = 0.0
    for key, sig in signals.items():
        w = weights.get(key, 0.1)
        if sig == "bullish":   score += w * 100
        elif sig == "bearish": score += w * 0
        else:                  score += w * 50

    score = round(score)

    if score >= 70:    label, overall = "Bullish", "bullish"
    elif score >= 55:  label, overall = "Cautiously Bullish", "bullish"
    elif score >= 45:  label, overall = "Neutral", "neutral"
    elif score >= 30:  label, overall = "Cautiously Bearish", "bearish"
    else:              label, overall = "Bearish", "bearish"

    bull_count = sum(1 for s in signals.values() if s == "bullish")
    bear_count = sum(1 for s in signals.values() if s == "bearish")

    return {
        "perception_score": score,
        "label": label,
        "overall_signal": overall,
        "bull_layers": bull_count,
        "bear_layers": bear_count,
        "neutral_layers": len(signals) - bull_count - bear_count,
        "layer_signals": signals,
    }


def fetch_all() -> dict:
    """Fetch all perception layer data. Returns full payload."""
    # Check cache first
    cached = _cached_load()
    if cached:
        return cached

    logger.info("Perception Layer: fetching all sources...")
    t_start = time.time()

    global_market   = fetch_global_market()
    trending        = fetch_trending_narratives()
    onchain         = fetch_onchain_fundamentals()
    lightning       = fetch_lightning_health()
    fees            = fetch_fee_market()
    social          = fetch_social_sentiment()
    fg_trend        = fetch_fg_trend()

    layers = {
        "global_market":        global_market,
        "trending_narratives":  trending,
        "onchain_fundamentals": onchain,
        "lightning_health":     lightning,
        "fee_market":           fees,
        "social_sentiment":     social,
        "fg_trend":             fg_trend,
    }

    composite = compute_composite_signal(layers)

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "fetch_time_ms": round((time.time() - t_start) * 1000),
        "composite": composite,
        **layers,
    }

    try:
        CACHE_PATH.write_text(json.dumps(result, indent=2, default=str))
        logger.info("Perception Layer: cached to %s (score=%d, %s)", 
                    CACHE_PATH, composite["perception_score"], composite["label"])
    except Exception as e:
        logger.error("Cache write failed: %s", e)

    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    data = fetch_all()
    print(f"Perception Score: {data['composite']['perception_score']}/100 — {data['composite']['label']}")
    print(f"Bull layers: {data['composite']['bull_layers']} | Bear: {data['composite']['bear_layers']}")
    print(f"BTC Dominance: {data['global_market'].get('btc_dominance_pct')}%")
    print(f"Lightning: {data['lightning_health'].get('node_count')} nodes, {data['lightning_health'].get('capacity_btc')} BTC")
    print(f"Fee market: {data['fee_market'].get('fee_signal')} ({data['fee_market'].get('fastest_fee_sat_vb')} sat/vB)")
    print(f"Social velocity: {data['social_sentiment'].get('velocity_label')} ({data['social_sentiment'].get('sentiment_velocity_7d_pct',0):+.1f}%)")
    print(f"F&G trend: {data['fg_trend'].get('trend')} (7d delta: {data['fg_trend'].get('7d_delta',0):+d})")
    print(f"Trending narratives: {data['trending_narratives'].get('narrative_signal')}")
    print(f"Fetch time: {data['fetch_time_ms']}ms")
