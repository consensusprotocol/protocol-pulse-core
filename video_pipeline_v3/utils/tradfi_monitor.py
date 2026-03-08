#!/usr/bin/env python3
"""
tradfi_monitor.py — TradFi Voices Intelligence Feed

Monitors top Traditional Finance voices on X for insights relevant to Bitcoin:
- Macro policy (Fed, inflation, rates, dollar)
- Hard asset / commodity commentary (gold, silver, commodities)
- Risk-on/risk-off signals
- Any direct Bitcoin/crypto mentions
- Institutional capital flow commentary

Output: data/intelligence/tradfi_signals.json
Used by: sentiment_service (macro context), weekly TradFi segment generator

Cron: */30 * * * * (every 30 min — TradFi moves slower than Bitcoin)
"""

import json, logging, os, time, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADFI_SIGNALS = os.path.join(BASE, "data", "intelligence", "tradfi_signals.json")
WEEKLY_SEGMENT_CACHE = os.path.join(BASE, "data", "intelligence", "tradfi_weekly.json")

logger = logging.getLogger("TradFiMonitor")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [tradfi] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────
# MASTER TRADFI HANDLE LIST — 2 tiers
# ─────────────────────────────────────────────────────────────────────────────
TRADFI_TIER1 = [  # Major established voices — always monitored
    "ZeroHedge", "morganhousel", "LizAnnSonders", "BrianFeroldi", "ritholtz",
    "Nouriel", "elerianm", "peterschiff", "AswathDamodaran", "matt_levine",
    "awealthofcs", "ReformedBroker", "PeterLBrandt", "thestalwart", "steve_hanke",
    "TraderLion_", "WarriorTrading", "timothysykes", "alphatrends", "optionshawk",
    "scottmelker", "ASvanevik", "callieabost", "EddyElfenbein", "Citrini7",
    "abnormalreturns", "hmeisler", "PiQSuite", "MadelonVos__",
]

TRADFI_TIER2 = [  # Active mid-size — weekly harvest only
    "waleswoosh", "banditxbt", "inversebrah", "CryptoCred", "kriptokalamar",
    "convexical", "frxresearch", "Sea_Bitcoin", "MCarrilloFX", "alaidi",
    "valuestockgeek", "SJosephBurns", "TraderDanielle", "ripster47",
    "super_trades", "RedDogT3", "traderstewie", "Burns277", "investorslive",
    "UniqueTrades", "EzyBitcoin", "aussiehaggie", "BollingerBeans",
    "LewPayne", "JustinGallum", "TonySeverinoCMT",
]

ALL_TRADFI_HANDLES = TRADFI_TIER1 + TRADFI_TIER2

X_PUBLIC_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# Keywords that flag a TradFi post as Bitcoin-relevant
BITCOIN_RELEVANCE_KEYWORDS = [
    "bitcoin", "btc", "crypto", "digital asset", "digital gold",
    "hard money", "sound money", "store of value", "hyperinflation",
    "dollar collapse", "dollar debasement", "currency debasement",
    "fiat", "central bank", "cbdc", "fed", "inflation hedge",
    "gold", "commodity", "risk asset", "institutional", "etf",
    "blackrock", "microstrategy", "saylor", "treasury", "devaluation",
    "monetary policy", "rate cut", "rate hike", "quantitative easing",
    "qe", "money printing", "debt ceiling", "national debt", "fiscal",
]

# Bitcoin Lens sentiment mapping — how bitcoiners read TradFi signals
BULLISH_FOR_BTC = [
    "inflation", "dollar weak", "debasement", "rate cut", "qe", "stimulus",
    "money printing", "debt", "deficit", "gold up", "safe haven", "risk off",
    "institutional", "etf inflows", "adoption",
]
BEARISH_FOR_BTC = [
    "rate hike", "dollar strong", "risk off sell", "deleveraging", "recession",
    "liquidity crunch", "margin call", "tightening", "sec", "regulation", "ban",
]


def _get_bearer():
    return os.environ.get("TWITTER_BEARER_TOKEN", X_PUBLIC_BEARER)

def _api_headers():
    return {"Authorization": f"Bearer {_get_bearer()}", "User-Agent": "ProtocolPulse/2.0"}

def _resolve_user_ids(handles):
    handle_to_id = {}
    for i in range(0, len(handles), 100):
        chunk = handles[i:i+100]
        try:
            r = requests.get(
                "https://api.twitter.com/2/users/by",
                params={"usernames": ",".join(chunk), "user.fields": "id,username"},
                headers=_api_headers(), timeout=15,
            )
            if r.status_code == 200:
                for u in r.json().get("data", []):
                    handle_to_id[u["username"].lower()] = u["id"]
        except Exception as e:
            logger.debug(f"resolve_user_ids chunk error: {e}")
    return handle_to_id

def is_bitcoin_relevant(text: str) -> tuple:
    """
    Returns (is_relevant: bool, btc_lens_sentiment: int 0-100, matched_keywords: list)
    btc_lens_sentiment: how this signal reads through a Bitcoin lens
    """
    text_lower = text.lower()
    matched = [kw for kw in BITCOIN_RELEVANCE_KEYWORDS if kw in text_lower]
    if not matched:
        return False, 50, []
    bull = sum(1 for kw in BULLISH_FOR_BTC if kw in text_lower)
    bear = sum(1 for kw in BEARISH_FOR_BTC if kw in text_lower)
    if bull > bear:
        btc_sentiment = min(85, 55 + bull * 8)
    elif bear > bull:
        btc_sentiment = max(15, 45 - bear * 8)
    else:
        btc_sentiment = 50
    return True, btc_sentiment, matched

def fetch_recent_tweets(user_id: str, handle: str, hours_back: int = 2) -> list:
    """Fetch recent tweets for a user and filter for Bitcoin relevance."""
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = requests.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            params={
                "start_time": since,
                "max_results": 10,
                "tweet.fields": "text,created_at,public_metrics",
            },
            headers=_api_headers(), timeout=12,
        )
        if r.status_code != 200:
            return []
        relevant = []
        for tweet in r.json().get("data", []):
            text = tweet.get("text", "")
            is_rel, btc_sentiment, keywords = is_bitcoin_relevant(text)
            if is_rel:
                metrics = tweet.get("public_metrics", {})
                relevant.append({
                    "tweet_id": tweet["id"],
                    "handle": handle,
                    "text": text,
                    "created_at": tweet.get("created_at", ""),
                    "btc_lens_sentiment": btc_sentiment,
                    "matched_keywords": keywords,
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "tier": "tier1" if handle in [h.lower() for h in TRADFI_TIER1] else "tier2",
                })
        return relevant
    except Exception as e:
        logger.debug(f"fetch_tweets {handle}: {e}")
        return []

def load_tradfi_signals():
    if os.path.exists(TRADFI_SIGNALS):
        try:
            with open(TRADFI_SIGNALS) as f: return json.load(f)
        except: pass
    return {"signals": [], "last_updated": None, "weekly_segment_ready": False}

def save_tradfi_signals(data):
    os.makedirs(os.path.dirname(TRADFI_SIGNALS), exist_ok=True)
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp = TRADFI_SIGNALS + ".tmp"
    with open(tmp, "w") as f: json.dump(data, f, indent=2)
    os.replace(tmp, TRADFI_SIGNALS)

def check_weekly_segment_trigger():
    """
    Return True if it's time to generate the weekly TradFi segment.
    Triggers: Sunday between 06:00-08:00 UTC (before the week's first episode).
    """
    now = datetime.now(timezone.utc)
    return now.weekday() == 6 and 6 <= now.hour < 8  # Sunday 6-8am UTC

def build_weekly_segment_data(signals: list) -> dict:
    """
    Aggregate the week's Bitcoin-relevant TradFi signals into a segment brief.
    Top 5 insights, overall macro tone, BTC lens commentary.
    """
    if not signals:
        return {}

    # Sort by engagement + btc_lens_sentiment deviation from 50
    def score_signal(s):
        engagement = s.get("likes", 0) + s.get("retweets", 0) * 3
        sentiment_strength = abs(s.get("btc_lens_sentiment", 50) - 50)
        return engagement + sentiment_strength * 2

    top5 = sorted(signals, key=score_signal, reverse=True)[:5]
    avg_btc_sentiment = sum(s["btc_lens_sentiment"] for s in signals) / len(signals)

    if avg_btc_sentiment >= 60:
        macro_tone = "BULLISH FOR BITCOIN"
        macro_summary = "Traditional finance is sending signals that historically favor Bitcoin. Inflation concerns, dollar weakness, and rate cut expectations are all tailwinds."
    elif avg_btc_sentiment <= 40:
        macro_tone = "CAUTIOUS FOR BITCOIN"
        macro_summary = "TradFi signals this week suggest a risk-off environment with dollar strength and tightening conditions — historically a headwind for Bitcoin price action."
    else:
        macro_tone = "NEUTRAL — WATCH CLOSELY"
        macro_summary = "Mixed signals from traditional finance this week. No strong directional macro catalyst either way — Bitcoin is trading on its own fundamentals."

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "week_signal_count": len(signals),
        "top_insights": top5,
        "macro_tone": macro_tone,
        "macro_summary": macro_summary,
        "avg_btc_lens_sentiment": round(avg_btc_sentiment, 1),
        "segment_ready": True,
    }

def run():
    """
    Main: fetch recent tweets from Tier 1 handles, filter Bitcoin-relevant,
    accumulate into tradfi_signals.json. Check for weekly segment trigger.
    """
    logger.info(f"Scanning {len(TRADFI_TIER1)} Tier 1 TradFi handles...")
    handle_to_id = _resolve_user_ids(TRADFI_TIER1)
    if not handle_to_id:
        logger.warning("No user IDs resolved — bearer token issue?")
        return

    data = load_tradfi_signals()
    # Keep last 7 days of signals
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    data["signals"] = [s for s in data.get("signals", []) if s.get("created_at","") > cutoff]

    new_count = 0
    existing_ids = {s["tweet_id"] for s in data["signals"]}
    for handle, uid in handle_to_id.items():
        tweets = fetch_recent_tweets(uid, handle, hours_back=2)
        for t in tweets:
            if t["tweet_id"] not in existing_ids:
                data["signals"].append(t)
                existing_ids.add(t["tweet_id"])
                new_count += 1
                logger.info(f"  [{handle}] BTC-relevant: {t['text'][:80]}... (sentiment={t['btc_lens_sentiment']})")

    logger.info(f"Added {new_count} new BTC-relevant TradFi signals ({len(data['signals'])} total in window)")

    # Weekly segment trigger
    if check_weekly_segment_trigger():
        weekly = build_weekly_segment_data(data["signals"])
        if weekly:
            os.makedirs(os.path.dirname(WEEKLY_SEGMENT_CACHE), exist_ok=True)
            with open(WEEKLY_SEGMENT_CACHE, "w") as f:
                json.dump(weekly, f, indent=2)
            data["weekly_segment_ready"] = True
            logger.info(f"WEEKLY SEGMENT READY: {weekly['macro_tone']} — {weekly['week_signal_count']} signals")

    save_tradfi_signals(data)

if __name__ == "__main__":
    run()

