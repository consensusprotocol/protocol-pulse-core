"""
Sovereign Context Engine — Unified Intelligence Brain

Reads ALL Protocol Pulse data streams, maintains a world-state snapshot,
detects cross-stream patterns, and emits SOVEREIGN ALERTS when multiple
streams confirm the same signal.

Every downstream system reads from this engine:
  Oracle briefings, Stage content, article generator,
  intelligence terminal, PANOPTICON dashboard.

Usage:
  python3 services/sovereign_context_engine.py --cycle
"""

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Lazy-loaded signal data fetcher
_signal_fetcher = None

def _get_signal_fetcher():
    global _signal_fetcher
    if _signal_fetcher is None:
        try:
            from services.signal_data_fetcher import SignalDataFetcher
            _signal_fetcher = SignalDataFetcher()
        except Exception as exc:
            logging.getLogger("sovereign_context_engine").warning(
                "SignalDataFetcher unavailable: %s", exc
            )
    return _signal_fetcher

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONTEXT_DIR = DATA_DIR / "sovereign_context"
LATEST_PATH = CONTEXT_DIR / "latest.json"
HISTORY_PATH = CONTEXT_DIR / "history.jsonl"
DAILY_SNAPSHOTS_DIR = CONTEXT_DIR / "daily_snapshots"
ALERTS_DB_PATH = DATA_DIR / "sovereign_alerts.db"
SOVEREIGN_INTEL_DB = DATA_DIR / "sovereign_intel.db"
SENTINEL_ALERTS_DB = DATA_DIR / "sentinel_alerts.db"
ACTIVE_SIGNAL_PATH = BASE_DIR / "video_pipeline_v3" / "cache" / "active_signal.json"
STAGE_BRIEF_PATH = BASE_DIR / "video_pipeline_v3" / "data" / "stage_briefs" / "latest.json"
PRICE_CACHE_PATH = DATA_DIR / "price_cache.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCE] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sovereign_context_engine")

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ProtocolPulse/SovereignContext/1.0"})
REQ_TIMEOUT = 12


def _get_json(url: str, timeout: int = REQ_TIMEOUT) -> Optional[dict]:
    """Safe JSON GET — returns None on any failure."""
    try:
        r = SESSION.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning("GET %s failed: %s", url, exc)
        return None


def _read_json_file(path: Path) -> Optional[dict]:
    """Read a local JSON file, return None on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:
        log.warning("Read %s failed: %s", path, exc)
    return None


# ---------------------------------------------------------------------------
# Alerts DB setup
# ---------------------------------------------------------------------------
def _init_alerts_db():
    """Create sovereign_alerts.db if needed."""
    conn = sqlite3.connect(str(ALERTS_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sovereign_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            pattern_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT DEFAULT 'WATCH',
            data_json TEXT,
            fingerprint TEXT UNIQUE
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sa_ts ON sovereign_alerts(ts_utc DESC)
    """)
    conn.commit()
    conn.close()


# ===================================================================
# DATA COLLECTORS — one per stream
# ===================================================================

def _fetch_btc_price() -> dict:
    """BTC price from CoinGecko (same source as price_service.py)."""
    data = _get_json(
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        "&include_7d_change=true&include_market_cap=true&include_24hr_vol=true"
    )
    if not data or "bitcoin" not in data:
        return {"price": 0, "change_24h": 0, "change_7d": 0, "market_cap": 0, "dominance": 0}
    btc = data["bitcoin"]
    # Dominance from CoinGecko global
    dom = 0
    g = _get_json("https://api.coingecko.com/api/v3/global")
    if g and "data" in g:
        dom = round(g["data"].get("market_cap_percentage", {}).get("btc", 0), 1)
    return {
        "price": btc.get("usd", 0),
        "change_24h": round(btc.get("usd_24h_change", 0), 2),
        "change_7d": round(btc.get("usd_7d_change", 0) if "usd_7d_change" in btc else 0, 2),
        "market_cap": btc.get("usd_market_cap", 0),
        "volume_24h": btc.get("usd_24h_vol", 0),
        "dominance": dom,
    }




def _fetch_dxy() -> float:
    """Calculate approximate DXY from live exchange rates."""
    try:
        data = _get_json("https://api.exchangerate-api.com/v4/latest/USD")
        if not data or "rates" not in data:
            return None
        r = data["rates"]
        eur = r.get("EUR", 0.92)
        jpy = r.get("JPY", 150)
        gbp = r.get("GBP", 0.79)
        cad = r.get("CAD", 1.36)
        sek = r.get("SEK", 10.5)
        chf = r.get("CHF", 0.88)
        # DXY formula: weighted geometric mean
        # API gives USD->X rates. DXY uses EURUSD (1/eur) and GBPUSD (1/gbp)
        eurusd = 1.0 / eur  # how many USD per 1 EUR
        gbpusd = 1.0 / gbp  # how many USD per 1 GBP
        dxy = 50.14348112 * (eurusd ** -0.576) * (jpy ** 0.136) * (gbpusd ** -0.119) * (cad ** 0.091) * (sek ** 0.042) * (chf ** 0.036)
        return round(dxy, 2)
    except Exception:
        return None

def _fetch_fear_greed() -> dict:
    """Fear & Greed Index from alternative.me."""
    data = _get_json("https://api.alternative.me/fng/?limit=1")
    if not data or "data" not in data:
        return {"value": 50, "label": "Neutral"}
    d = data["data"][0]
    return {"value": int(d.get("value", 50)), "label": d.get("value_classification", "Neutral")}


def _fetch_mempool() -> dict:
    """Mempool stats + fee estimates from mempool.space."""
    stats = _get_json("https://mempool.space/api/mempool") or {}
    fees = _get_json("https://mempool.space/api/v1/fees/recommended") or {}
    return {
        "fee_low": fees.get("economyFee", 0),
        "fee_mid": fees.get("halfHourFee", 0),
        "fee_high": fees.get("fastestFee", 0),
        "unconfirmed": stats.get("count", 0),
        "size_mb": round(stats.get("vsize", 0) / 1_000_000, 1),
    }


def _fetch_network() -> dict:
    """Hashrate, difficulty, next adjustment from mempool.space."""
    hr_data = _get_json("https://mempool.space/api/v1/mining/hashrate/3d")
    diff = _get_json("https://mempool.space/api/v1/difficulty-adjustment") or {}
    block_height = 0
    tip = _get_json("https://mempool.space/api/blocks/tip/height")
    if isinstance(tip, int):
        block_height = tip
    elif isinstance(tip, dict):
        block_height = tip.get("height", 0)

    hashrate_eh = 0
    if hr_data and "currentHashrate" in hr_data:
        hashrate_eh = round(hr_data["currentHashrate"] / 1e18, 1)
    elif hr_data and "hashrates" in hr_data and hr_data["hashrates"]:
        last = hr_data["hashrates"][-1]
        hashrate_eh = round(last.get("avgHashrate", 0) / 1e18, 1)

    return {
        "hashrate_eh": hashrate_eh,
        "difficulty": diff.get("difficulty", 0),
        "next_adj_pct": round(diff.get("difficultyChange", 0), 2),
        "next_adj_blocks": diff.get("remainingBlocks", 0),
        "block_height": block_height,
    }


def _fetch_lightning() -> dict:
    """Lightning Network stats from mempool.space."""
    data = _get_json("https://mempool.space/api/v1/lightning/statistics/latest")
    if not data or "latest" not in data:
        return {"capacity_btc": 0, "channels": 0, "nodes": 0}
    ln = data["latest"]
    return {
        "capacity_btc": round(ln.get("total_capacity", 0) / 1e8, 1),
        "channels": ln.get("channel_count", 0),
        "nodes": ln.get("node_count", 0),
    }


def _fetch_kol_sentiment() -> dict:
    """KOL sentiment from kol_pulse_item table (last 50 posts)."""
    db_path = BASE_DIR / "instance" / "protocol_pulse.db"
    if not db_path.exists():
        db_path = BASE_DIR / "protocol_pulse.db"
    if not db_path.exists():
        return {"sentiment_score": 50, "top_topics": [], "post_count_24h": 0}

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Count posts in last 24h
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM kol_pulse_item "
            "WHERE created_at > datetime('now', '-1 day')"
        ).fetchone()
        count_24h = row["cnt"] if row else 0

        # Last 50 posts for basic topic extraction
        rows = conn.execute(
            "SELECT content FROM kol_pulse_item ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        conn.close()

        # Simple keyword-based topic extraction
        topic_counts: Dict[str, int] = {}
        keywords = {
            "etf": ["etf", "blackrock", "ishares", "grayscale"],
            "halving": ["halving", "halvening", "block reward"],
            "regulation": ["sec", "regulation", "regulatory", "gensler", "congress"],
            "mining": ["mining", "hashrate", "miner", "asic"],
            "lightning": ["lightning", "ln", "layer 2", "layer2"],
            "self-custody": ["self-custody", "self custody", "not your keys", "cold storage"],
            "macro": ["fed", "inflation", "interest rate", "treasury", "macro"],
            "stablecoin": ["stablecoin", "usdt", "usdc", "tether"],
            "defi": ["defi", "dex", "yield", "lending"],
            "cbdc": ["cbdc", "digital dollar", "digital currency"],
        }
        for row in rows:
            text = (row["content"] or "").lower()
            for topic, kws in keywords.items():
                if any(kw in text for kw in kws):
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1

        top_topics = sorted(topic_counts, key=topic_counts.get, reverse=True)[:5]

        # Rough sentiment: count bullish vs bearish keywords
        bullish_kw = ["bullish", "moon", "pump", "ath", "accumulate", "buy", "long", "breakout", "green"]
        bearish_kw = ["bearish", "dump", "crash", "sell", "short", "fear", "capitulation", "red"]
        bull = sum(1 for r in rows if any(k in (r["content"] or "").lower() for k in bullish_kw))
        bear = sum(1 for r in rows if any(k in (r["content"] or "").lower() for k in bearish_kw))
        total = bull + bear
        sentiment_score = int((bull / total * 100) if total > 0 else 50)

        return {
            "sentiment_score": sentiment_score,
            "top_topics": top_topics,
            "post_count_24h": count_24h,
        }
    except Exception as exc:
        log.warning("KOL sentiment fetch failed: %s", exc)
        return {"sentiment_score": 50, "top_topics": [], "post_count_24h": 0}


def _fetch_article_narrative() -> dict:
    """Article corpus: last 20 articles, dominant theme, sentiment."""
    db_path = BASE_DIR / "instance" / "protocol_pulse.db"
    if not db_path.exists():
        db_path = BASE_DIR / "protocol_pulse.db"
    if not db_path.exists():
        return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT title, category, sentiment, narrative_label FROM articles "
            "ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        conn.close()

        if not rows:
            return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}

        # Dominant theme from narrative_label or category
        themes: Dict[str, int] = {}
        sentiments = []
        for r in rows:
            label = r["narrative_label"] or r["category"] or "general"
            themes[label] = themes.get(label, 0) + 1
            if r["sentiment"]:
                sentiments.append(r["sentiment"])

        dominant = max(themes, key=themes.get) if themes else "unknown"

        # Aggregate sentiment
        if sentiments:
            bull = sum(1 for s in sentiments if s and "bull" in s.lower())
            bear = sum(1 for s in sentiments if s and "bear" in s.lower())
            if bull > bear:
                agg_sentiment = "bullish"
            elif bear > bull:
                agg_sentiment = "bearish"
            else:
                agg_sentiment = "neutral"
        else:
            agg_sentiment = "neutral"

        return {
            "dominant_theme": dominant,
            "sentiment": agg_sentiment,
            "article_count": len(rows),
        }
    except Exception as exc:
        log.warning("Article narrative fetch failed: %s", exc)
        return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}


def _fetch_polymarket() -> dict:
    """Polymarket crypto/macro sentiment."""
    try:
        # Import from existing service
        sys.path.insert(0, str(BASE_DIR))
        from services.polymarket_service import (
            get_bitcoin_markets,
            get_macro_sentiment_score,
            get_top_market_by_volume,
        )
        top = get_top_market_by_volume()
        score = get_macro_sentiment_score()
        return {
            "macro_sentiment": score,
            "top_market": top["question"] if top else "N/A",
            "top_probability": round(max(top["outcomes"].values()), 1) if top and top.get("outcomes") else 0,
        }
    except Exception as exc:
        log.warning("Polymarket fetch failed: %s", exc)
        return {"macro_sentiment": 50, "top_market": "N/A", "top_probability": 0}


def _fetch_pcaf_score() -> int:
    """PCAF anomaly score from active_signal.json (Nostr relay cache)."""
    data = _read_json_file(ACTIVE_SIGNAL_PATH)
    if not data:
        return 0
    # Score based on filtered post count (higher = more signal activity)
    return min(data.get("total_scored", 0) * 5, 100)


def _fetch_exchange_flow() -> str:
    """Exchange netflow from sentinel_alerts.db or sovereign_intel.db signals."""
    # Check sovereign_intel signals table for exchange flow direction
    if SOVEREIGN_INTEL_DB.exists():
        try:
            conn = sqlite3.connect(str(SOVEREIGN_INTEL_DB))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT direction FROM signals "
                "WHERE category = 'onchain' AND metric LIKE '%exchange%' "
                "ORDER BY ts_utc DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                return row["direction"]
        except Exception:
            pass

    # Check sentinel for whale-related alerts
    if SENTINEL_ALERTS_DB.exists():
        try:
            conn = sqlite3.connect(str(SENTINEL_ALERTS_DB))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT message FROM alerts "
                "WHERE rule LIKE '%exchange%' OR rule LIKE '%whale%' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                msg = (row["message"] or "").lower()
                if "outflow" in msg:
                    return "outflow"
                if "inflow" in msg:
                    return "inflow"
        except Exception:
            pass

    return "neutral"


def _fetch_stage_brief() -> dict:
    """Latest narrative from stage briefs."""
    data = _read_json_file(STAGE_BRIEF_PATH)
    if not data:
        return {"narrative": "N/A", "brief_type": "unknown"}
    return {
        "narrative": (data.get("script_summary") or "N/A")[:200],
        "brief_type": data.get("brief_type", "unknown"),
    }


def _fetch_whale_alerts() -> List[dict]:
    """Recent whale alerts from sentinel_alerts.db."""
    if not SENTINEL_ALERTS_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(SENTINEL_ALERTS_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT tier, rule, message, score, created_at FROM alerts "
            "ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        log.warning("Whale alerts fetch failed: %s", exc)
        return []


# ===================================================================
# PATTERN DETECTION
# ===================================================================

class Alert:
    """A sovereign pattern-match alert."""

    def __init__(self, pattern_id: str, title: str, description: str,
                 severity: str = "WATCH", data: Optional[dict] = None):
        self.pattern_id = pattern_id
        self.title = title
        self.description = description
        self.severity = severity  # CRITICAL, WATCH, NOTE
        self.data = data or {}
        self.ts = datetime.now(timezone.utc).isoformat()

    def fingerprint(self) -> str:
        """Unique ID per pattern + hour to prevent spam."""
        hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        raw = f"{self.pattern_id}:{hour}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "ts": self.ts,
            "data": self.data,
        }


def detect_patterns(ws: dict) -> List[Alert]:
    """Run all pattern detection rules against the world state."""
    alerts: List[Alert] = []

    btc = ws.get("btc", {})
    fg = ws.get("fear_greed", {})
    mempool = ws.get("mempool", {})
    network = ws.get("network", {})
    lightning = ws.get("lightning", {})
    kol = ws.get("kol", {})
    narrative = ws.get("narrative", {})
    polymarket = ws.get("polymarket", {})
    exchange_flow = ws.get("exchange_flow", "neutral")

    fg_val = fg.get("value", 50)
    change_24h = btc.get("change_24h", 0)
    hashrate = network.get("hashrate_eh", 0)
    fee_high = mempool.get("fee_high", 0)

    # 1. ACCUMULATION SIGNAL
    # hashrate UP (positive adj) + exchange outflows + FG < 30
    if (network.get("next_adj_pct", 0) > 0
            and exchange_flow == "outflow"
            and fg_val < 30):
        alerts.append(Alert(
            "ACCUMULATION",
            "Stealth accumulation detected",
            f"Hashrate adj +{network['next_adj_pct']}%, exchange outflows active, "
            f"Fear & Greed at {fg_val} ({fg.get('label', '')}).",
            severity="WATCH",
            data={"fg": fg_val, "adj_pct": network["next_adj_pct"], "flow": exchange_flow},
        ))

    # 2. SUPPLY SHOCK PRECURSOR
    # hashrate UP + price DOWN + miners not capitulating
    if (network.get("next_adj_pct", 0) > 0
            and change_24h < -2
            and hashrate > 0):
        alerts.append(Alert(
            "SUPPLY_SHOCK",
            "Miners not capitulating — supply shock risk",
            f"Hashrate {hashrate} EH/s (adj +{network['next_adj_pct']}%), "
            f"price down {change_24h}% — miners holding.",
            severity="WATCH",
            data={"hashrate": hashrate, "change_24h": change_24h},
        ))

    # 3. NARRATIVE DIVERGENCE
    # article sentiment BULLISH + KOL sentiment BEARISH (or vice versa)
    art_sent = narrative.get("sentiment", "neutral")
    kol_score = kol.get("sentiment_score", 50)
    if art_sent == "bullish" and kol_score < 35:
        alerts.append(Alert(
            "NARRATIVE_DIVERGENCE",
            "Narrative split — watch for resolution",
            f"Articles bullish but KOL sentiment at {kol_score}/100 (bearish). "
            "Divergence often precedes volatility.",
            severity="WATCH",
            data={"article_sentiment": art_sent, "kol_score": kol_score},
        ))
    elif art_sent == "bearish" and kol_score > 65:
        alerts.append(Alert(
            "NARRATIVE_DIVERGENCE",
            "Narrative split — watch for resolution",
            f"Articles bearish but KOL sentiment at {kol_score}/100 (bullish). "
            "Divergence often precedes volatility.",
            severity="WATCH",
            data={"article_sentiment": art_sent, "kol_score": kol_score},
        ))

    # 4. POLYMARKET CONFIRMATION
    # Big probability shift + KOL mention overlap
    poly_sent = polymarket.get("macro_sentiment", 50)
    if abs(poly_sent - 50) > 20 and kol.get("post_count_24h", 0) > 10:
        direction = "bullish" if poly_sent > 50 else "bearish"
        alerts.append(Alert(
            "POLYMARKET_CONFIRM",
            "Market consensus shifting",
            f"Polymarket sentiment {poly_sent}/100 ({direction}), "
            f"{kol['post_count_24h']} KOL posts in 24h — consensus forming.",
            severity="WATCH",
            data={"poly_sentiment": poly_sent, "kol_posts": kol["post_count_24h"]},
        ))

    # 5. MEMPOOL PRESSURE
    # fees > 50 sat/vB + Lightning growing
    if fee_high > 50 and lightning.get("capacity_btc", 0) > 0:
        alerts.append(Alert(
            "MEMPOOL_PRESSURE",
            "On-chain congestion — Lightning demand increasing",
            f"Priority fees at {fee_high} sat/vB, Lightning capacity "
            f"{lightning['capacity_btc']} BTC across {lightning['channels']} channels.",
            severity="NOTE",
            data={"fee_high": fee_high, "ln_capacity": lightning["capacity_btc"]},
        ))

    # 6. FEAR CAPITULATION
    # FG < 15 + exchange inflows + price DOWN >5%
    if fg_val < 15 and exchange_flow == "inflow" and change_24h < -5:
        alerts.append(Alert(
            "FEAR_CAPITULATION",
            "Extreme fear — historically bullish 30-day forward",
            f"Fear & Greed at {fg_val}, exchange inflows active, "
            f"price down {change_24h}%. Capitulation pattern detected.",
            severity="CRITICAL",
            data={"fg": fg_val, "change_24h": change_24h, "flow": exchange_flow},
        ))

    # 7. CROSS-ASSET DIVERGENCE
    # 3+ signals diverge from their baseline simultaneously
    divergence_count = 0
    divergence_details = []

    if abs(change_24h) > 5:
        divergence_count += 1
        divergence_details.append(f"Price {change_24h:+.1f}%")
    if abs(fg_val - 50) > 25:
        divergence_count += 1
        divergence_details.append(f"F&G {fg_val}")
    if abs(kol_score - 50) > 25:
        divergence_count += 1
        divergence_details.append(f"KOL {kol_score}")
    if abs(poly_sent - 50) > 25:
        divergence_count += 1
        divergence_details.append(f"Polymarket {poly_sent}")
    if fee_high > 100:
        divergence_count += 1
        divergence_details.append(f"Fees {fee_high} sat/vB")

    if divergence_count >= 3:
        alerts.append(Alert(
            "CROSS_DIVERGENCE",
            "DIVERGENCE ALERT — major move probable 24-72h",
            f"{divergence_count} signals diverging: {', '.join(divergence_details)}. "
            "Multiple streams confirming unusual activity.",
            severity="CRITICAL",
            data={"count": divergence_count, "details": divergence_details},
        ))

    return alerts


# ===================================================================
# ALERT PERSISTENCE
# ===================================================================

def emit_alerts(alerts: List[Alert]):
    """Write alerts to sovereign_alerts.db (dedup by fingerprint per hour)."""
    if not alerts:
        return
    _init_alerts_db()
    conn = sqlite3.connect(str(ALERTS_DB_PATH))
    inserted = 0
    for a in alerts:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO sovereign_alerts "
                "(ts_utc, pattern_id, title, description, severity, data_json, fingerprint) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (a.ts, a.pattern_id, a.title, a.description,
                 a.severity, json.dumps(a.data), a.fingerprint()),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # duplicate fingerprint — already emitted this hour
    conn.commit()
    conn.close()
    if inserted:
        log.info("Emitted %d new alert(s): %s",
                 inserted, ", ".join(a.pattern_id for a in alerts))


# ===================================================================
# MAIN ENGINE
# ===================================================================

def _calculate_proprietary_indices(
    btc: dict, network: dict, kol: dict,
    exchange_flow: str, whale_alerts: list, fg: dict
) -> dict:
    """Compute Protocol Pulse proprietary branded indices from raw data.

    Three indices (consensus P0 from cross-LLM audit):
      1. Miner Conviction Index — hashrate strength vs price weakness
      2. Exchange Pressure Ratio — -2 to +2 flow directional score
      3. Social-to-Market Divergence — KOL sentiment vs price action delta
    """
    hashrate = network.get("hashrate_eh", 0)
    change_7d = btc.get("change_7d", 0)
    change_24h = btc.get("change_24h", 0)
    kol_score = kol.get("sentiment_score", 50)
    fg_val = fg.get("value", 50)

    # 1. Miner Conviction Index (0-100 scale, >50 = conviction, <50 = capitulation)
    # Normalized: hashrate relative to ~900 EH/s baseline + inverse price pressure
    hashrate_norm = min(100, (hashrate / 900) * 50) if hashrate > 0 else 25
    price_pressure = max(-25, min(25, -change_7d))  # negative change = positive conviction
    miner_conviction = max(0, min(100, int(hashrate_norm + price_pressure + 25)))

    if miner_conviction >= 70:
        mc_interp = "Miners expanding despite price consolidation — supply shock precursor."
        mc_signal = "bullish"
    elif miner_conviction <= 30:
        mc_interp = "Miner stress detected — potential capitulation zone."
        mc_signal = "bearish"
    else:
        mc_interp = "Miner activity within normal range."
        mc_signal = "neutral"

    # 2. Exchange Pressure Ratio (-2 to +2)
    ep_score = 0
    if exchange_flow == "outflow":
        ep_score += 1
    elif exchange_flow == "inflow":
        ep_score -= 1
    # Whale alert direction analysis
    whale_withdrawals = sum(1 for w in whale_alerts if "withdraw" in (w.get("message", "") or "").lower())
    whale_deposits = sum(1 for w in whale_alerts if "deposit" in (w.get("message", "") or "").lower())
    if whale_withdrawals > whale_deposits:
        ep_score += 1
    elif whale_deposits > whale_withdrawals:
        ep_score -= 1

    ep_labels = {
        2: ("Strong outflow — bullish accumulation", "bullish"),
        1: ("Net outflow detected", "bullish"),
        0: ("Neutral exchange flow", "neutral"),
        -1: ("Net inflow — selling pressure", "bearish"),
        -2: ("Strong inflow — distribution detected", "bearish"),
    }
    ep_interp, ep_signal = ep_labels.get(ep_score, ("Neutral", "neutral"))

    # 3. Social-to-Market Divergence
    # Formula: (kol_sentiment - 50) - (btc_7d_change * 2)
    social_div = round((kol_score - 50) - (change_7d * 2), 1)

    if social_div > 20:
        sd_interp = "Social FOMO ahead of price — potential local top signal."
        sd_signal = "bearish"
    elif social_div < -20:
        sd_interp = "Social capitulation while price holds — potential accumulation zone."
        sd_signal = "bullish"
    else:
        sd_interp = "Social sentiment aligned with price action."
        sd_signal = "neutral"

    return {
        "miner_conviction": {
            "score": miner_conviction,
            "interpretation": mc_interp,
            "signal": mc_signal,
        },
        "exchange_pressure": {
            "score": ep_score,
            "interpretation": ep_interp,
            "signal": ep_signal,
        },
        "social_divergence": {
            "score": social_div,
            "interpretation": sd_interp,
            "signal": sd_signal,
        },
    }


class SovereignContextEngine:
    """The connective brain that unifies all Protocol Pulse data streams."""

    def build_world_state(self) -> dict:
        """Assemble everything into one JSON world state."""
        log.info("Building world state...")
        t0 = time.monotonic()

        # Fetch all streams
        btc = _fetch_btc_price()
        fg = _fetch_fear_greed()
        mempool = _fetch_mempool()
        network = _fetch_network()
        lightning = _fetch_lightning()
        kol = _fetch_kol_sentiment()
        narrative = _fetch_article_narrative()
        polymarket = _fetch_polymarket()
        pcaf = _fetch_pcaf_score()
        exchange_flow = _fetch_exchange_flow()
        stage = _fetch_stage_brief()
        whale_alerts = _fetch_whale_alerts()

        # Fetch real signal data for 4 critical signals
        signal_data = {"macro": {}, "options": {}, "futures": {}, "on_chain": {}}
        fetcher = _get_signal_fetcher()
        if fetcher:
            try:
                signal_data = fetcher.fetch_all()
                log.info("Signal data fetched: macro=%d, options=%d, futures=%d, onchain=%d fields",
                         sum(1 for v in signal_data.get("macro", {}).values() if v is not None),
                         sum(1 for v in signal_data.get("options", {}).values() if v is not None),
                         sum(1 for v in signal_data.get("futures", {}).values() if v is not None),
                         sum(1 for v in signal_data.get("on_chain", {}).values() if v is not None))
            except Exception as exc:
                log.warning("Signal data fetch failed (non-fatal): %s", exc)

        block_height = network.pop("block_height", 0)

        world_state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_height": block_height,
            "btc": btc,
            "fear_greed": fg,
            "mempool": mempool,
            "network": network,
            "lightning": lightning,
            "kol": kol,
            "narrative": narrative,
            "polymarket": polymarket,
            "pcaf_score": pcaf,
            "exchange_flow": exchange_flow,
            "stage_brief": stage,
            "whale_alerts": whale_alerts,
            "macro": signal_data.get("macro", {}),
            "options": signal_data.get("options", {}),
            "futures": signal_data.get("futures", {}),
            "on_chain": signal_data.get("on_chain", {}),
            "active_alerts": [],
            "pattern_matches": [],
            "indices": _calculate_proprietary_indices(
                btc, network, kol, exchange_flow, whale_alerts, fg
            ),
        }

        # Fetch pro on-chain metrics (SSR, MPI, Dormancy Flow)
        pro_metrics = {}
        try:
            from services.pro_metrics_service import fetch_all_pro_metrics
            pro_metrics = fetch_all_pro_metrics() or {}
        except Exception as _pme:
            log.warning("Pro metrics fetch failed: %s", _pme)
        world_state["pro_metrics"] = pro_metrics

        # Enrich macro with DXY if missing
        if not world_state.get("macro", {}).get("dxy"):
            try:
                _dxy_val = _fetch_dxy()
                if _dxy_val:
                    if "macro" not in world_state:
                        world_state["macro"] = {}
                    world_state["macro"]["dxy"] = _dxy_val
            except Exception:
                pass

        elapsed = time.monotonic() - t0
        log.info("World state built in %.1fs — BTC $%s, F&G %s, Hashrate %s EH/s",
                 elapsed, f"{btc['price']:,.0f}", fg["value"], network["hashrate_eh"])
        return world_state

    def run_cycle(self) -> dict:
        """Full cycle: build state → detect patterns → emit alerts → save."""
        log.info("=== Sovereign Context Cycle Start ===")
        t0 = time.monotonic()

        # 1. Build world state
        ws = self.build_world_state()

        # 2. Detect patterns
        alerts = detect_patterns(ws)
        ws["active_alerts"] = [a.to_dict() for a in alerts]
        ws["pattern_matches"] = [a.pattern_id for a in alerts]

        if alerts:
            log.info("Detected %d pattern(s): %s",
                     len(alerts), ", ".join(a.pattern_id for a in alerts))
        else:
            log.info("No pattern matches this cycle")

        # 3. Emit alerts to DB
        emit_alerts(alerts)

        # 4. Save latest snapshot
        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        LATEST_PATH.write_text(json.dumps(ws, indent=2, default=str))
        log.info("Saved latest.json (%d bytes)", LATEST_PATH.stat().st_size)

        # 5. Append to history
        with open(HISTORY_PATH, "a") as f:
            f.write(json.dumps(ws, default=str) + "\n")

        # 6. Save daily signal snapshot (one file per day, overwrites)
        _save_daily_snapshot(ws)

        elapsed = time.monotonic() - t0
        log.info("=== Cycle complete in %.1fs — %d alerts ===", elapsed, len(alerts))
        return ws


# ===================================================================
# Daily signal snapshots (for future heatmap with real data)
# ===================================================================

def _save_daily_snapshot(ws: dict) -> None:
    """Save a daily signal snapshot — one file per day, last write wins."""
    try:
        DAILY_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fg = (ws.get("fear_greed") or {}).get("value", 0)
        kol = (ws.get("kol") or {}).get("sentiment_score", 0)
        narr = ws.get("narrative") or {}
        art = 70 if narr.get("sentiment") == "bullish" else (30 if narr.get("sentiment") == "bearish" else 50)
        poly = (ws.get("polymarket") or {}).get("macro_sentiment", 50)
        flow = ws.get("exchange_flow", "neutral")
        exch = 70 if flow == "outflow" else (30 if flow == "inflow" else 50)

        snapshot = {
            "date": today,
            "timestamp": ws.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "signals": {
                "fear_greed": fg,
                "kol": kol,
                "article": art,
                "market": poly,
                "exchange": exch,
            }
        }
        path = DAILY_SNAPSHOTS_DIR / f"{today}.json"
        path.write_text(json.dumps(snapshot, indent=2))
    except Exception as e:
        log.warning("daily snapshot save failed: %s", e)


def get_daily_signal_history(days: int = 7) -> List[dict]:
    """Read up to N days of daily signal snapshots (newest first)."""
    if not DAILY_SNAPSHOTS_DIR.exists():
        return []
    files = sorted(DAILY_SNAPSHOTS_DIR.glob("*.json"), reverse=True)[:days]
    results = []
    for f in files:
        try:
            results.append(json.loads(f.read_text()))
        except Exception:
            continue
    return results


# ===================================================================
# Flask route helper (imported by app.py)
# ===================================================================

def get_latest_context() -> Optional[dict]:
    """Read the latest sovereign context snapshot for API serving."""
    return _read_json_file(LATEST_PATH)


def get_recent_alerts(limit: int = 20) -> List[dict]:
    """Read recent alerts from sovereign_alerts.db."""
    if not ALERTS_DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(ALERTS_DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts_utc, pattern_id, title, description, severity, data_json "
            "FROM sovereign_alerts ORDER BY ts_utc DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d.pop("data_json", "{}"))
            results.append(d)
        return results
    except Exception:
        return []


# ===================================================================
# CLI entrypoint
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Sovereign Context Engine")
    parser.add_argument("--cycle", action="store_true", help="Run one full cycle")
    args = parser.parse_args()

    if args.cycle:
        engine = SovereignContextEngine()
        ws = engine.run_cycle()
        print(json.dumps({
            "status": "ok",
            "btc_price": ws["btc"]["price"],
            "fear_greed": ws["fear_greed"]["value"],
            "hashrate_eh": ws["network"]["hashrate_eh"],
            "alerts": len(ws["active_alerts"]),
            "patterns": ws["pattern_matches"],
        }, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
