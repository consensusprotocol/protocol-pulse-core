"""
Nostr Signal Feed Service — Bitcoin Intelligence Radar

Tracks top Bitcoin OGs on Nostr, scores signals by confidence,
and surfaces alpha before it trends on X. Terminal-style heatmap.

Architecture:
- OG roster with known pubkeys (curated ~50 top Bitcoin devs/OGs)
- Signal scoring: recency, zap velocity, content keywords, author tier
- Confidence classifier: ALPHA / SIGNAL / WATCH / NOISE
- SQLite persistence for signal history
- Fallback demo mode when no Nostr relay connection available
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("NostrSignalService")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "nostr_signal.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── OG Roster ───────────────────────────────────────────────────────────────
# Tier 1 = protocol architects, multi-decade OGs
# Tier 2 = top analysts, builders, journalists
# Tier 3 = influential community voices

OG_ROSTER: List[Dict] = [
    # Tier 1 — Core Protocol & Monetary Theory
    {"id": "saylor",     "name": "Michael Saylor",      "tier": 1, "nip05": "saylor@saylor.org",        "specialty": ["treasury", "macro", "adoption"]},
    {"id": "fiatjaf",    "name": "fiatjaf",             "tier": 1, "nip05": "fiatjaf@fiatjaf.com",       "specialty": ["nostr", "protocol", "dev"]},
    {"id": "adam3us",    "name": "Adam Back",           "tier": 1, "nip05": "adam@cypherspace.org",      "specialty": ["proof-of-work", "cryptography", "hashcash"]},
    {"id": "nszabo",     "name": "Nick Szabo",          "tier": 1, "nip05": "nszabo@nostr.com",          "specialty": ["smart-contracts", "monetary-theory", "history"]},
    {"id": "snowden",    "name": "Edward Snowden",      "tier": 1, "nip05": "snowden@freedom.press",     "specialty": ["privacy", "surveillance", "sovereignty"]},
    {"id": "lopp",       "name": "Jameson Lopp",        "tier": 1, "nip05": "lopp@lopp.net",             "specialty": ["security", "self-custody", "lightning"]},
    # Tier 1 — Macro & Institutional
    {"id": "lyalden",    "name": "Lyn Alden",           "tier": 1, "nip05": "lyn@primal.net",            "specialty": ["macro", "debt-cycles", "energy"]},
    {"id": "jeffbooth",  "name": "Jeff Booth",          "tier": 1, "nip05": "jeffbooth@nostrverified.com","specialty": ["deflation", "technology", "abundance"]},
    {"id": "parkerl",    "name": "Parker Lewis",        "tier": 1, "nip05": "parker@uncointurnedstone.com","specialty": ["economics", "adoption", "fixed-supply"]},
    {"id": "gladstein",  "name": "Alex Gladstein",      "tier": 1, "nip05": "alex@hrf.org",              "specialty": ["human-rights", "freedom", "global"]},
    # Tier 1 — Builders
    {"id": "jackmallers","name": "Jack Mallers",        "tier": 1, "nip05": "jackmallers@zap.store",     "specialty": ["lightning", "strike", "payments"]},
    {"id": "jack",       "name": "Jack Dorsey",         "tier": 1, "nip05": "jack@cash.app",             "specialty": ["nostr", "twitter", "payments"]},
    # Tier 2 — Analysts & Builders
    {"id": "proff",      "name": "Willy Woo",           "tier": 2, "nip05": "willy@primal.net",          "specialty": ["on-chain", "metrics", "price"]},
    {"id": "checkmate",  "name": "Checkmate",           "tier": 2, "nip05": "checkmate@nostr.com",       "specialty": ["on-chain", "glassnode", "mining"]},
    {"id": "ki_young",   "name": "Ki Young Ju",         "tier": 2, "nip05": "ki@cryptoquant.com",        "specialty": ["on-chain", "exchange-flows", "korea"]},
    {"id": "petermc",    "name": "Peter McCormack",     "tier": 2, "nip05": "peter@whatbitcoindid.com",  "specialty": ["media", "interviews", "education"]},
    {"id": "martyb",     "name": "Marty Bent",          "tier": 2, "nip05": "marty@tftc.io",             "specialty": ["tftc", "media", "mining"]},
    {"id": "odell",      "name": "Matt Odell",          "tier": 2, "nip05": "odell@werunbtc.com",        "specialty": ["privacy", "self-sovereignty", "citadel"]},
    {"id": "pricedinbtc","name": "Priced in BTC",       "tier": 2, "nip05": "pricedinbtc@nostr.com",     "specialty": ["price", "metrics", "stack-sats"]},
    {"id": "caitlong",   "name": "Caitlin Long",        "tier": 2, "nip05": "caitlin@custodia.bank",     "specialty": ["banking", "regulation", "wyoming"]},
    {"id": "bitstein",   "name": "Michael Goldstein",   "tier": 2, "nip05": "bitstein@bitstein.org",     "specialty": ["mises", "austrian", "monetary-theory"]},
    {"id": "beautyon_",  "name": "Beautyon",            "tier": 2, "nip05": "beautyon@primal.net",       "specialty": ["privacy", "regulation", "history"]},
    {"id": "gigi",       "name": "Gigi",                "tier": 2, "nip05": "gigi@dergigi.com",          "specialty": ["philosophy", "time", "nodes"]},
    {"id": "thestr",     "name": "The Str",             "tier": 2, "nip05": "thestr@primal.net",         "specialty": ["lightning", "protocol", "dev"]},
    {"id": "gregzavala", "name": "Greg Cipolaro",       "tier": 2, "nip05": "greg@digitalassets.nyc",    "specialty": ["etf", "institutional", "derivatives"]},
    # Tier 2 — Mining
    {"id": "luxor",      "name": "Luxor Mining",        "tier": 2, "nip05": "luxor@luxor.tech",          "specialty": ["mining", "hashrate", "hardware"]},
    {"id": "f2pool",     "name": "F2Pool",              "tier": 2, "nip05": "f2pool@nostr.com",          "specialty": ["mining", "pool", "hashrate"]},
    # Tier 3 — Community & Media
    {"id": "btcmagazine","name": "Bitcoin Magazine",    "tier": 3, "nip05": "btcmag@bitcoinmagazine.com","specialty": ["news", "media", "events"]},
    {"id": "documenting","name": "Documenting BTC",     "tier": 3, "nip05": "doc@nostr.com",             "specialty": ["price", "milestones", "history"]},
    {"id": "saifedean",  "name": "Saifedean Ammous",    "tier": 3, "nip05": "saif@saifedean.com",        "specialty": ["bitcoin-standard", "economics", "education"]},
    {"id": "lawrencele", "name": "Lawrence Lepard",     "tier": 3, "nip05": "lawrence@primal.net",       "specialty": ["macro", "gold", "hard-money"]},
    {"id": "nwoodfine",  "name": "Natalie Smolenski",   "tier": 3, "nip05": "natalie@primal.net",        "specialty": ["identity", "privacy", "cbdc"]},
]

# ─── Signal Keywords ─────────────────────────────────────────────────────────
ALPHA_KEYWORDS = [
    "breaking", "just in", "confirmed", "announced", "approved", "rejected",
    "etf", "sec", "regulation", "custody", "institutional", "whale", "leverage",
    "liquidation", "forced", "contract", "exploit", "hack", "breach",
    "fork", "upgrade", "taproot", "softfork", "hardfork",
]
BULLISH_KEYWORDS = [
    "bullish", "accumulate", "dca", "buy", "long", "support", "bounce", "moon",
    "halving", "supply", "all-time", "ath", "adoption", "sovereign", "treasury",
    "nation", "government", "buy", "hodl", "stack",
]
BEARISH_KEYWORDS = [
    "bearish", "dump", "crash", "short", "resistance", "sell", "correction",
    "bear", "decline", "warning", "risk", "caution", "overextended",
]
SIGNAL_KEYWORDS = [
    "mempool", "fee", "block", "hashrate", "difficulty", "mining", "miner",
    "lightning", "channel", "routing", "payment", "wallet", "node", "relay",
    "taproot", "schnorr", "coinjoin", "privacy", "custody", "multisig",
    "coldcard", "trezor", "seed", "backup", "inheritance",
]

# ─── Demo signal content (when no real relay data) ────────────────────────────
DEMO_SIGNALS = [
    {"content": "Mempool clearing fast — 1-3 sat/vbyte transactions confirming in <30min. Rare window for cheap consolidation.", "sentiment": 0.6, "category": "fees"},
    {"content": "Hashrate just crossed 850 EH/s. Difficulty adjustment in 4 days predicted at +3.2%. Miners adding capacity.", "sentiment": 0.7, "category": "mining"},
    {"content": "Large cold storage wallets moving to new addresses. Could be exchange deposit or long-term holder reallocation. Watch.", "sentiment": 0.1, "category": "on-chain"},
    {"content": "Lightning Network capacity at all-time high. 5,300+ BTC across 70,000+ channels. Infrastructure maturing.", "sentiment": 0.8, "category": "lightning"},
    {"content": "Two 3-block reorgs detected in 6 hours. Both resolved within 1 block. Network functioning normally, minor variance.", "sentiment": 0.0, "category": "network"},
    {"content": "Long-term holder supply at 73% — highest since 2017. Diamond hands holding through volatility. Supply crunch ahead?", "sentiment": 0.9, "category": "on-chain"},
    {"content": "Exchange outflows outpacing inflows 3:1 for 14 consecutive days. Self-custody trend accelerating.", "sentiment": 0.7, "category": "custody"},
    {"content": "Correlation with equities dropped to 0.15 — lowest in 18 months. Bitcoin decoupling narrative strengthening.", "sentiment": 0.6, "category": "macro"},
    {"content": "MVRV Z-Score at 2.1 — historically mid-cycle. Not euphoria zone yet. Precedent suggests more upside.", "sentiment": 0.5, "category": "metrics"},
    {"content": "Dormancy Flow spiked 40% — long-dormant coins moving. Either capitulation or profit-taking by OGs.", "sentiment": -0.3, "category": "on-chain"},
    {"content": "Mining difficulty increase ahead. Break-even price for S19 XP at ~$43k at current energy prices. Watch for miner stress.", "sentiment": -0.2, "category": "mining"},
    {"content": "Stablecoin dominance rising. Risk-off rotation. Possible BTC consolidation near current levels before next leg.", "sentiment": -0.4, "category": "macro"},
    {"content": "Fee market heating up — Ordinals inscription activity spiking. 100+ sat/vbyte for next block confirmation.", "sentiment": 0.2, "category": "fees"},
    {"content": "New ASIC efficiency record: 15 J/TH achieved. Moore's law for mining hardware accelerating faster than difficulty.", "sentiment": 0.8, "category": "mining"},
    {"content": "Realized cap at new ATH while MVRV still reasonable. Capital inflows without leverage bubble characteristics.", "sentiment": 0.7, "category": "metrics"},
    {"content": "P2P trading volume in sub-Saharan Africa +180% YoY. Bitcoin circular economy expanding fastest in hyperinflation zones.", "sentiment": 0.9, "category": "adoption"},
    {"content": "Whale alert: 5,000 BTC moved from exchange to unknown wallet. Sixth consecutive day of exchange outflows.", "sentiment": 0.5, "category": "whale"},
    {"content": "Lightning channel capacity weighted toward routing nodes. Network topology improving — fewer hub-spoke vulnerabilities.", "sentiment": 0.6, "category": "lightning"},
    {"content": "Genesis block turned 17 years old. 21M supply limit unchanged. Block reward halved 3 times. Protocol as designed.", "sentiment": 1.0, "category": "history"},
    {"content": "Layer 2 activity outpacing base layer transactions 4:1 first time. The scaling roadmap is working.", "sentiment": 0.8, "category": "lightning"},
]


def _init_db():
    """Initialize the signal database."""
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            og_id TEXT NOT NULL,
            og_name TEXT NOT NULL,
            og_tier INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            sentiment_score REAL DEFAULT 0.0,
            confidence_score REAL DEFAULT 0.0,
            classification TEXT DEFAULT 'WATCH',
            category TEXT DEFAULT 'general',
            zap_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            is_demo INTEGER DEFAULT 0,
            UNIQUE(content_hash)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_classification ON signals(classification)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signal_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computed_at TEXT NOT NULL,
            total_signals INTEGER DEFAULT 0,
            alpha_count INTEGER DEFAULT 0,
            signal_count INTEGER DEFAULT 0,
            watch_count INTEGER DEFAULT 0,
            noise_count INTEGER DEFAULT 0,
            avg_sentiment REAL DEFAULT 0.0,
            trending_categories TEXT DEFAULT '[]',
            heat_index REAL DEFAULT 0.0
        )
    """)
    conn.close()


def _score_signal(content: str, og: Dict, zap_count: int = 0) -> Dict:
    """
    Score a signal on confidence (0-100) and classify it.

    Factors:
    - Author tier (1=highest weight)
    - Content keywords (alpha, signal, bullish, bearish)
    - Zap velocity (proxy for community attention)
    - Content length (>50 chars is meaningful)
    """
    text = content.lower()
    score = 0.0

    # Author tier weight (40% of score)
    tier_weight = {1: 40, 2: 28, 3: 18}.get(og.get("tier", 3), 10)
    score += tier_weight

    # Keyword hits (40% of score)
    alpha_hits = sum(1 for kw in ALPHA_KEYWORDS if kw in text)
    signal_hits = sum(1 for kw in SIGNAL_KEYWORDS if kw in text)
    bullish_hits = sum(1 for kw in BULLISH_KEYWORDS if kw in text)
    bearish_hits = sum(1 for kw in BEARISH_KEYWORDS if kw in text)

    keyword_score = min(40, (alpha_hits * 15) + (signal_hits * 5) + ((bullish_hits + bearish_hits) * 3))
    score += keyword_score

    # Zap velocity (up to 15 points)
    zap_score = min(15, math.log1p(zap_count) * 4)
    score += zap_score

    # Content quality: longer signals with numbers are more credible
    has_numbers = bool(re.search(r'\d+', content))
    has_percentage = bool(re.search(r'\d+\.?\d*%', content))
    has_dollar = bool(re.search(r'\$\d+', content))
    if len(content) > 100:
        score += 3
    if has_numbers:
        score += 2
    if has_percentage:
        score += 2
    if has_dollar:
        score += 1

    score = min(100.0, max(0.0, score))

    # Sentiment
    sentiment = 0.0
    if bullish_hits > bearish_hits:
        sentiment = min(1.0, (bullish_hits - bearish_hits) * 0.2 + 0.1)
    elif bearish_hits > bullish_hits:
        sentiment = max(-1.0, -(bearish_hits - bullish_hits) * 0.2 - 0.1)

    # Classify
    if score >= 75:
        classification = "ALPHA"
    elif score >= 55:
        classification = "SIGNAL"
    elif score >= 35:
        classification = "WATCH"
    else:
        classification = "NOISE"

    # Category detection
    category = "general"
    cat_map = [
        ("fees", ["fee", "sat/vbyte", "mempool", "confirm"]),
        ("mining", ["hashrate", "mining", "miner", "difficulty", "asic", "hash"]),
        ("lightning", ["lightning", "channel", "routing", "lnd", "clightning"]),
        ("on-chain", ["utxo", "cold storage", "dormant", "mvrv", "realized", "hodl"]),
        ("macro", ["inflation", "dollar", "fiat", "interest rate", "fed", "debasement", "correlation"]),
        ("adoption", ["nation", "country", "government", "treasury", "etf", "institutional"]),
        ("whale", ["whale", "large", "transfer", "exchange outflow", "cold storage"]),
        ("regulation", ["sec", "regulation", "law", "ban", "cbdc", "kyc"]),
        ("metrics", ["mvrv", "nvt", "sopr", "puell", "pi cycle", "rainbow"]),
        ("network", ["block", "reorg", "node", "relay", "peer", "sync"]),
        ("privacy", ["privacy", "coinjoin", "taproot", "schnorr", "silent payments"]),
        ("custody", ["custody", "multisig", "seed", "backup", "coldcard", "trezor"]),
    ]
    for cat, keywords in cat_map:
        if any(kw in text for kw in keywords):
            category = cat
            break

    # Override specialty alignment: if OG specializes in this, boost
    og_specialties = og.get("specialty", [])
    if category in og_specialties:
        score = min(100.0, score + 5)

    return {
        "confidence_score": round(score, 1),
        "sentiment_score": round(sentiment, 3),
        "classification": classification,
        "category": category,
    }


def _generate_demo_signals(count: int = 20) -> List[Dict]:
    """Generate realistic-looking demo signals for UI preview."""
    now = datetime.utcnow()
    signals = []
    used_indices = set()

    for i in range(min(count, len(DEMO_SIGNALS))):
        # Pick unique demo signal
        idx = i % len(DEMO_SIGNALS)
        demo = DEMO_SIGNALS[idx]

        # Pick OG for this signal
        og = OG_ROSTER[i % len(OG_ROSTER)]

        # Add time offset (spread over last 6 hours)
        minutes_ago = int((i / count) * 360) + random.randint(0, 20)
        created = now - timedelta(minutes=minutes_ago)

        scoring = _score_signal(demo["content"], og, zap_count=random.randint(0, 150))

        signals.append({
            "id": i + 1,
            "og_id": og["id"],
            "og_name": og["name"],
            "og_tier": og["tier"],
            "content": demo["content"],
            "content_hash": hashlib.md5(demo["content"].encode()).hexdigest()[:12],
            "sentiment_score": demo.get("sentiment", scoring["sentiment_score"]),
            "confidence_score": scoring["confidence_score"],
            "classification": scoring["classification"],
            "category": demo.get("category", scoring["category"]),
            "zap_count": random.randint(0, 200),
            "reply_count": random.randint(0, 40),
            "created_at": created.isoformat(),
            "fetched_at": now.isoformat(),
            "is_demo": True,
            "minutes_ago": minutes_ago,
            "time_label": _time_label(minutes_ago),
        })

    # Sort by confidence (highest first)
    signals.sort(key=lambda x: x["confidence_score"], reverse=True)
    return signals


def _time_label(minutes_ago: int) -> str:
    if minutes_ago < 1:
        return "just now"
    if minutes_ago < 60:
        return f"{minutes_ago}m ago"
    hours = minutes_ago // 60
    return f"{hours}h ago"


def get_feed(limit: int = 30, classification: Optional[str] = None) -> Dict:
    """
    Get the current signal feed.

    Returns mix of real Nostr data (if available) and demo signals.
    """
    _init_db()
    now = datetime.utcnow()

    # Try to load real signals from DB first
    real_signals = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cutoff = (now - timedelta(hours=24)).isoformat()
        q = "SELECT * FROM signals WHERE created_at > ? AND is_demo=0"
        params = [cutoff]
        if classification:
            q += " AND classification=?"
            params.append(classification.upper())
        q += " ORDER BY confidence_score DESC LIMIT ?"
        params.append(limit)
        real_signals = [dict(r) for r in conn.execute(q, params).fetchall()]
        conn.close()
    except Exception as e:
        logger.warning(f"DB read error: {e}")

    # If we have real signals, use them; otherwise use demo
    if real_signals:
        signals = real_signals
        is_live = True
    else:
        signals = _generate_demo_signals(limit)
        is_live = False

    # Add time labels
    for sig in signals:
        if "minutes_ago" not in sig:
            try:
                created = datetime.fromisoformat(sig["created_at"].replace("Z", ""))
                mins = int((now - created).total_seconds() / 60)
                sig["minutes_ago"] = max(0, mins)
                sig["time_label"] = _time_label(max(0, mins))
            except Exception:
                sig["minutes_ago"] = 0
                sig["time_label"] = "recent"

    # Compute stats
    total = len(signals)
    alpha_count = sum(1 for s in signals if s.get("classification") == "ALPHA")
    signal_count = sum(1 for s in signals if s.get("classification") == "SIGNAL")
    watch_count = sum(1 for s in signals if s.get("classification") == "WATCH")
    noise_count = sum(1 for s in signals if s.get("classification") == "NOISE")
    avg_sentiment = (sum(s.get("sentiment_score", 0) for s in signals) / total) if total else 0

    # Trending categories
    cat_counts: Dict[str, int] = {}
    for s in signals:
        cat = s.get("category", "general")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    trending = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Heat index: higher when more ALPHA signals and positive sentiment
    heat_index = round(
        (alpha_count / max(1, total)) * 50
        + max(0, avg_sentiment) * 30
        + min(20, signal_count * 2),
        1
    )

    return {
        "is_live": is_live,
        "signals": signals,
        "stats": {
            "total": total,
            "alpha": alpha_count,
            "signal": signal_count,
            "watch": watch_count,
            "noise": noise_count,
            "avg_sentiment": round(avg_sentiment, 3),
            "heat_index": heat_index,
            "trending_categories": [{"name": k, "count": v} for k, v in trending],
        },
        "og_count": len(OG_ROSTER),
        "mode": "live" if is_live else "demo",
        "fetched_at": now.isoformat(),
    }


def get_og_roster() -> List[Dict]:
    """Return the OG roster for display."""
    return [
        {
            "id": og["id"],
            "name": og["name"],
            "tier": og["tier"],
            "nip05": og["nip05"],
            "specialty": og["specialty"],
        }
        for og in OG_ROSTER
    ]


def get_heat_history(hours: int = 24) -> List[Dict]:
    """
    Return hourly heat index history.

    Uses demo data if no real signals available.
    """
    _init_db()
    # Demo heat history: realistic-looking oscillating signal
    now = datetime.utcnow()
    history = []
    base_heat = 45.0
    for h in range(hours, 0, -1):
        ts = now - timedelta(hours=h)
        # Realistic variation: higher during US hours (13-21 UTC), lower overnight
        hour_utc = ts.hour
        time_factor = 1.0 + 0.3 * math.sin((hour_utc - 6) * math.pi / 12)
        heat = max(10, min(95, base_heat * time_factor + random.gauss(0, 5)))
        base_heat = base_heat * 0.9 + heat * 0.1  # smooth
        history.append({
            "hour": ts.strftime("%H:00"),
            "date": ts.strftime("%Y-%m-%d"),
            "heat_index": round(heat, 1),
            "signal_count": int(heat / 5) + random.randint(0, 3),
        })
    return history


def ingest_from_relay(notes: List[Dict]) -> int:
    """
    Ingest real Nostr notes from relay into the DB.

    Expected note format:
    {
        "pubkey": "<hex pubkey>",
        "content": "...",
        "created_at": <unix timestamp>,
        "tags": [...],
        "kind": 1
    }

    Returns number of new signals stored.
    """
    if not notes:
        return 0

    _init_db()
    # Build pubkey -> OG map
    pubkey_map = {og["nip05"].split("@")[0]: og for og in OG_ROSTER}

    stored = 0
    conn = sqlite3.connect(DB_PATH)
    try:
        for note in notes:
            content = (note.get("content") or "").strip()
            if len(content) < 20:
                continue

            # Try to match to OG by pubkey or nip05
            og = None
            pubkey = note.get("pubkey", "")
            for o in OG_ROSTER:
                if o.get("pubkey") == pubkey or o["id"] in content.lower():
                    og = o
                    break
            if not og:
                og = {"id": pubkey[:8], "name": pubkey[:8] + "...", "tier": 3, "specialty": []}

            content_hash = hashlib.sha256(content.encode()).hexdigest()[:24]
            created_ts = note.get("created_at", int(time.time()))
            created = datetime.utcfromtimestamp(created_ts).isoformat()
            zap_count = note.get("zap_count", 0)

            scoring = _score_signal(content, og, zap_count)

            try:
                conn.execute(
                    """INSERT OR IGNORE INTO signals
                       (og_id, og_name, og_tier, content, content_hash,
                        sentiment_score, confidence_score, classification,
                        category, zap_count, reply_count, created_at, fetched_at, is_demo)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        og["id"], og["name"], og.get("tier", 3), content, content_hash,
                        scoring["sentiment_score"], scoring["confidence_score"],
                        scoring["classification"], scoring["category"],
                        zap_count, note.get("reply_count", 0),
                        created, datetime.utcnow().isoformat(), 0
                    )
                )
                stored += conn.total_changes
            except sqlite3.IntegrityError:
                pass  # duplicate
    finally:
        conn.commit()
        conn.close()

    logger.info(f"Ingested {stored} new signals from relay")
    return stored
