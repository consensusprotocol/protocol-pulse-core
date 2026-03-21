#!/usr/bin/env python3
"""
Stage Broadcast Service — Signal-driven queue for 24/7 autonomous Bitcoin broadcast.

Run via cron every 5 minutes:
  */5 * * * * python3 ~/protocol_pulse/services/stage_broadcast_service.py >> ~/protocol_pulse/logs/broadcast_service.log 2>&1

Polls 7 data sources, generates 30-90s spoken scripts via Claude Haiku,
writes to broadcast_queue.json with priority and TTL management.
"""

import fcntl
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
QUEUE_PATH = BASE / "video_pipeline_v3" / "data" / "stage_briefs" / "broadcast_queue.json"
PRICE_CACHE = Path("/tmp/stage_last_price.json")
METRICS_CACHE = Path("/tmp/stage_last_metrics.json")
FILLER_STATE = BASE / "data" / "stage_briefs" / "filler_state.json"
LOGS_DIR = BASE / "logs"
DATA_DIR = BASE / "data"

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_QUEUE_DEPTH = 8

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("stage_broadcast")
logger.setLevel(logging.INFO)

_fh = logging.FileHandler(str(LOGS_DIR / "broadcast_service.log"))
_fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_fh)

_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_sh)

# ---------------------------------------------------------------------------
# API Key
# ---------------------------------------------------------------------------

def _get_anthropic_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                key = line.split("=", 1)[1].strip("'\"")
                os.environ["ANTHROPIC_API_KEY"] = key
                return key
    raise RuntimeError("ANTHROPIC_API_KEY not set")


# ---------------------------------------------------------------------------
# Queue Management (file-locked atomic operations)
# ---------------------------------------------------------------------------

def _read_queue():
    """Read queue with file lock."""
    if not QUEUE_PATH.exists():
        return []
    try:
        with open(QUEUE_PATH, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def _write_queue(items):
    """Write queue with exclusive file lock."""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(items, f, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)


def _cleanup_queue(items):
    """Remove expired items and enforce max depth."""
    now = datetime.now(timezone.utc)
    valid = []
    for item in items:
        try:
            expires = datetime.fromisoformat(item["expires_at"].replace("Z", "+00:00"))
            if expires > now:
                valid.append(item)
        except (KeyError, ValueError):
            continue
    # Sort by priority (1=highest)
    valid.sort(key=lambda x: x.get("priority", 5))
    return valid[:MAX_QUEUE_DEPTH]


def _add_to_queue(item):
    """Add item to queue if not duplicate type within TTL window."""
    items = _read_queue()
    items = _cleanup_queue(items)

    # Prevent duplicate types (except FILLER_INSIGHT)
    if item["type"] != "FILLER_INSIGHT":
        for existing in items:
            if existing["type"] == item["type"]:
                logger.info("Skipping duplicate %s already in queue", item["type"])
                return items

    if len(items) >= MAX_QUEUE_DEPTH:
        # Drop lowest priority
        items = items[:MAX_QUEUE_DEPTH - 1]

    items.append(item)
    items = _cleanup_queue(items)
    _write_queue(items)
    logger.info("Queued %s (pri=%d): %s", item["type"], item["priority"],
                item["topic_preview"][:60])
    return items


# ---------------------------------------------------------------------------
# Data Fetching (patterns from stage_brief_pipeline.py)
# ---------------------------------------------------------------------------

def _fetch_btc_price():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd",
                    "include_24hr_change": "true", "include_market_cap": "true"},
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()["bitcoin"]
        return {
            "price": d["usd"],
            "change_24h": round(d.get("usd_24h_change", 0), 2),
            "market_cap": d.get("usd_market_cap", 0),
        }
    except Exception as e:
        logger.warning("BTC price fetch failed: %s", e)
        return None


def _fetch_mempool():
    try:
        r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=10)
        r.raise_for_status()
        fees = r.json()
        r2 = requests.get("https://mempool.space/api/mempool", timeout=10)
        r2.raise_for_status()
        mp = r2.json()
        return {
            "fastest_fee": fees.get("fastestFee", 0),
            "hour_fee": fees.get("hourFee", 0),
            "tx_count": mp.get("count", 0),
        }
    except Exception as e:
        logger.warning("Mempool fetch failed: %s", e)
        return None


def _fetch_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        r.raise_for_status()
        d = r.json()["data"][0]
        return {"value": int(d["value"]), "label": d["value_classification"]}
    except Exception as e:
        logger.warning("FNG fetch failed: %s", e)
        return None


def _fetch_hashrate():
    try:
        r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=15)
        r.raise_for_status()
        hr = r.json().get("hashrates", [])
        current_hr = hr[-1]["avgHashrate"] if hr else 0
        return {"hashrate_eh": round(current_hr / 1e18, 1)}
    except Exception as e:
        logger.warning("Hashrate fetch failed: %s", e)
        return None


def _fetch_block_height():
    try:
        r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=10)
        r.raise_for_status()
        return int(r.text.strip())
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Script Generation via Claude Haiku
# ---------------------------------------------------------------------------

ANCHOR_SYSTEM = (
    "You are the female anchor of Protocol Pulse, a 24/7 Bitcoin broadcast station. "
    "Voice: authoritative, calm, data-precise, cypherpunk worldview. "
    "Never hype, never FUD, always data-backed. "
    "Write a spoken script (30-90 seconds at ~150 words/minute, so 75-225 words). "
    "Use REAL data provided — never hallucinate prices or metrics. "
    "End with a natural segue like 'Stay with me, more signals incoming...' or similar. "
    "No greeting, no sign-off. Just deliver the intelligence."
)


def _generate_script(segment_type, context_data):
    """Generate a broadcast script via Claude Haiku."""
    api_key = _get_anthropic_key()

    prompt = f"Segment type: {segment_type}\n\nData:\n{json.dumps(context_data, indent=2)}\n\n"
    prompt += "Generate a spoken broadcast script based on this data."

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 400,
            "system": ANCHOR_SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    import re as _re
    text = resp.json()["content"][0]["text"].strip()
    text = _re.sub(r'^#+\s+[^\n]*\n?', '', text, flags=_re.MULTILINE)
    text = _re.sub(r'^---+\s*', '', text, flags=_re.MULTILINE)
    text = text.strip()
    return text


def _make_queue_item(seg_type, priority, script, source_label, topic_preview, ttl_minutes):
    now = datetime.now(timezone.utc)
    return {
        "id": str(uuid.uuid4()),
        "type": seg_type,
        "priority": priority,
        "script": script,
        "source_label": source_label,
        "topic_preview": topic_preview,
        "generated_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
    }


# ---------------------------------------------------------------------------
# Signal Checks (7 types)
# ---------------------------------------------------------------------------

def check_price_alert(btc_data):
    """PRICE_ALERT (pri=1): >0.8% move from cached price."""
    if not btc_data:
        return None

    current_price = btc_data["price"]
    cached_price = 0

    if PRICE_CACHE.exists():
        try:
            cached = json.loads(PRICE_CACHE.read_text())
            cached_price = cached.get("price", 0)
        except (json.JSONDecodeError, IOError):
            pass

    # Always update cache
    PRICE_CACHE.write_text(json.dumps({"price": current_price,
                                        "timestamp": datetime.now(timezone.utc).isoformat()}))

    if cached_price <= 0:
        logger.info("Price cache initialized at $%s", f"{current_price:,.0f}")
        return None

    pct_change = abs((current_price - cached_price) / cached_price) * 100
    if pct_change < 0.8:
        return None

    direction = "up" if current_price > cached_price else "down"
    logger.info("PRICE_ALERT: $%s → $%s (%.1f%% %s)",
                f"{cached_price:,.0f}", f"{current_price:,.0f}", pct_change, direction)

    script = _generate_script("PRICE_ALERT", {
        "previous_price": cached_price,
        "current_price": current_price,
        "percent_change": round(pct_change, 2),
        "direction": direction,
        "change_24h": btc_data["change_24h"],
    })

    return _make_queue_item(
        "PRICE_ALERT", 1, script,
        "📡 PRICE ALERT",
        f"Bitcoin {'breaks' if direction == 'up' else 'drops to'} ${current_price:,.0f}",
        30,
    )


def check_thought_leader():
    """THOUGHT_LEADER (pri=2): Priority-1 handles from raw_tweets.json."""
    PRIORITY_HANDLES = {
        "saylor", "natbrunell", "jack", "gladstein", "prestonpysh",
        "martybent", "lynaldencontact", "jeffbooth", "odell", "aantonop", "adam3us",
    }

    tweets_path = DATA_DIR / "tweet_study" / "raw_tweets.json"
    if not tweets_path.exists():
        return None

    try:
        tweets = json.loads(tweets_path.read_text())
        if not isinstance(tweets, list):
            return None

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        for tweet in tweets:
            handle = (tweet.get("handle") or tweet.get("username") or "").lower().lstrip("@")
            if handle not in PRIORITY_HANDLES:
                continue

            created = tweet.get("created_at") or tweet.get("timestamp") or ""
            if created:
                try:
                    tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if tweet_time < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass

            text = tweet.get("text") or tweet.get("content") or ""
            if len(text) < 30:
                continue

            logger.info("THOUGHT_LEADER: @%s — %s", handle, text[:80])
            script = _generate_script("THOUGHT_LEADER", {
                "handle": handle,
                "tweet_text": text[:500],
                "context": "Priority Bitcoin thought leader tweet",
            })

            return _make_queue_item(
                "THOUGHT_LEADER", 2, script,
                f"🧠 @{handle.upper()}",
                text[:80],
                120,
            )
    except Exception as e:
        logger.warning("Thought leader check failed: %s", e)

    return None


def check_space_tap():
    """SPACE_TAP (pri=2): Fresh X Spaces clips."""
    spaces_cache = BASE / "x_spaces_scraper" / "cache"
    if not spaces_cache.exists():
        return None

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for f in sorted(spaces_cache.glob("*.json"), reverse=True):
            if f.name == "last_run.json":
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                continue

            data = json.loads(f.read_text())
            title = data.get("space_title") or data.get("title") or "Live Space"
            transcript = data.get("transcript") or data.get("text") or ""
            if len(transcript) < 50:
                continue

            logger.info("SPACE_TAP: %s", title[:60])
            script = _generate_script("SPACE_TAP", {
                "space_title": title,
                "transcript_excerpt": transcript[:800],
                "context": "We intercepted a live Bitcoin space — here's the key signal.",
            })

            return _make_queue_item(
                "SPACE_TAP", 2, script,
                "🎙️ SPACE TAP",
                title[:80],
                240,
            )
    except Exception as e:
        logger.warning("Space tap check failed: %s", e)

    return None


def check_article_teaser():
    """ARTICLE_TEASER (pri=3): Recent articles from DB."""
    db_path = BASE / "instance" / "protocol_pulse.db"
    if not db_path.exists():
        return None

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        row = conn.execute(
            "SELECT title, summary FROM articles WHERE created_at > ? ORDER BY RANDOM() LIMIT 1",
            (cutoff,)
        ).fetchone()
        conn.close()

        if not row:
            return None

        title = row["title"]
        summary = row["summary"] or ""
        logger.info("ARTICLE_TEASER: %s", title[:60])

        script = _generate_script("ARTICLE_TEASER", {
            "article_title": title,
            "article_summary": summary,
            "context": "Fresh from our editorial desk — tease this article without giving everything away.",
        })

        return _make_queue_item(
            "ARTICLE_TEASER", 3, script,
            "📰 FRESH INTEL",
            title[:80],
            240,
        )
    except Exception as e:
        logger.warning("Article teaser check failed: %s", e)
        return None


def check_metrics_pulse(btc_data):
    """METRICS_PULSE (pri=3): Network metrics every 20+ minutes."""
    if METRICS_CACHE.exists():
        try:
            cached = json.loads(METRICS_CACHE.read_text())
            last_ts = datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_ts < timedelta(minutes=20):
                return None
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    hashrate = _fetch_hashrate()
    fng = _fetch_fear_greed()
    mempool = _fetch_mempool()
    block_height = _fetch_block_height()

    if not any([hashrate, fng, mempool]):
        return None

    metrics = {
        "btc_price": btc_data["price"] if btc_data else 0,
        "change_24h": btc_data["change_24h"] if btc_data else 0,
        "hashrate_eh": hashrate["hashrate_eh"] if hashrate else 0,
        "fng_value": fng["value"] if fng else 50,
        "fng_label": fng["label"] if fng else "Neutral",
        "fastest_fee": mempool["fastest_fee"] if mempool else 0,
        "tx_count": mempool["tx_count"] if mempool else 0,
        "block_height": block_height,
    }

    METRICS_CACHE.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **metrics,
    }))

    logger.info("METRICS_PULSE: BTC $%s, FNG %s, Hash %s EH/s",
                f"{metrics['btc_price']:,.0f}", metrics["fng_value"], metrics["hashrate_eh"])

    script = _generate_script("METRICS_PULSE", metrics)

    return _make_queue_item(
        "METRICS_PULSE", 3, script,
        "📊 METRICS PULSE",
        f"BTC ${metrics['btc_price']:,.0f} · FNG {metrics['fng_value']} · {metrics['hashrate_eh']} EH/s",
        240,
    )


def check_nostr_signal():
    """NOSTR_SIGNAL (pri=4): Narrative from Nostr discourse."""
    narrative_path = BASE / "video_pipeline_v3" / "data" / "intelligence" / "narrative_context.json"
    if not narrative_path.exists():
        return None

    try:
        data = json.loads(narrative_path.read_text())
        narrative = data.get("dominant_narrative") or data.get("narrative") or ""
        if not narrative:
            return None

        updated = data.get("updated_at") or data.get("generated_at") or ""
        if updated:
            try:
                update_time = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - update_time > timedelta(hours=4):
                    return None
            except (ValueError, TypeError):
                pass

        logger.info("NOSTR_SIGNAL: %s", narrative[:60])
        script = _generate_script("NOSTR_SIGNAL", {
            "dominant_narrative": narrative,
            "themes": data.get("themes", []),
            "context": "This is the dominant discourse emerging from Bitcoin Nostr relays right now.",
        })

        return _make_queue_item(
            "NOSTR_SIGNAL", 4, script,
            "⚡ NOSTR SIGNAL",
            narrative[:80],
            240,
        )
    except Exception as e:
        logger.warning("Nostr signal check failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Filler Insights (20 pre-written, never repeat consecutively)
# ---------------------------------------------------------------------------

FILLER_INSIGHTS = [
    "Bitcoin is the only monetary network in history that operates with zero counterparty risk. Every ten minutes, a new block confirms that no single entity controls the ledger. That's not a feature — that's a paradigm shift in how humans coordinate value across trust boundaries.",
    "The Lightning Network processed more transactions last month than the entire Bitcoin base layer did in its first four years. Layer-two scaling isn't theoretical anymore — it's quietly becoming the rails for instant, near-free payments worldwide.",
    "Satoshi Nakamoto's last known communication was in December 2010. Fifteen years later, the protocol runs exactly as designed. No CEO, no board meetings, no emergency patches. The code is the constitution.",
    "Hash rate is the most honest signal in Bitcoin. Miners don't speculate — they commit capital, electricity, and hardware. When hash rate climbs to all-time highs, it means serious operators are betting their balance sheets on Bitcoin's future.",
    "There are only 21 million bitcoin. That's not a soft cap, not a target — it's a mathematical certainty enforced by every node on the network. In a world of infinite money printing, scarcity is the ultimate signal.",
    "The mempool is Bitcoin's waiting room. When fees spike, it means demand for block space exceeds supply. That's not a bug — it's proof that people value the security of final settlement enough to pay for it.",
    "Every four years, the block subsidy cuts in half. This halving mechanism is the most predictable monetary policy in human history. No central banker can override it. No politician can delay it.",
    "Running a full node costs less than a streaming subscription. For that price, you independently verify every transaction since the genesis block. That's sovereignty you can run on a Raspberry Pi.",
    "Bitcoin's difficulty adjustment is an engineering marvel. Every 2,016 blocks, the network recalibrates to maintain ten-minute block intervals regardless of how much hash power joins or leaves. Self-regulating monetary infrastructure.",
    "The Bitcoin network has been operational for over 99.98 percent of its existence. No bank, no government system, no tech company can match that uptime. Decentralization isn't just philosophy — it's resilience.",
    "Multisig wallets eliminate single points of failure. A two-of-three setup means no single key compromise can drain your funds. This is how institutions are beginning to custody billions in bitcoin.",
    "Bitcoin mining is increasingly powered by stranded energy — gas flares, excess hydro, curtailed wind and solar. Miners are becoming the buyer of last resort for energy that would otherwise be wasted.",
    "The UTXO model is Bitcoin's secret weapon for privacy and scalability. Unlike account-based systems, every transaction output is independent — enabling parallel validation and coin-level audit trails.",
    "Nostr is building the decentralized social layer that Bitcoin's monetary layer always needed. Censorship-resistant communication plus censorship-resistant money — that's the full stack of digital sovereignty.",
    "Time-chain analysis shows that long-term holders — wallets dormant for one year or more — consistently hold over sixty percent of all bitcoin supply. The conviction of this network's participants is unprecedented.",
    "Bitcoin script is intentionally limited. No Turing completeness, no complex smart contracts on the base layer. This constraint is a security feature — the monetary layer should be boring and bulletproof.",
    "The genesis block contains a Times headline about bank bailouts. Satoshi didn't just build software — they embedded a permanent protest against monetary manipulation into the first block ever mined.",
    "Coinjoin transactions are growing month over month. Privacy isn't optional in a sound money system — it's essential. Financial surveillance is incompatible with individual sovereignty.",
    "Bitcoin's energy consumption is a feature, not a bug. Proof of work converts physical energy into digital security. The cost of attacking the network must always exceed the cost of defending it.",
    "Every bitcoin transaction is a voluntary exchange. No chargebacks, no intermediaries, no permission required. For the first time in digital history, we have bearer assets that move at the speed of light.",
]


def get_filler_insight():
    """Get next filler insight, rotating through the list."""
    last_idx = -1
    if FILLER_STATE.exists():
        try:
            last_idx = json.loads(FILLER_STATE.read_text()).get("idx", -1)
        except (json.JSONDecodeError, IOError):
            pass

    next_idx = (last_idx + 1) % len(FILLER_INSIGHTS)
    FILLER_STATE.write_text(json.dumps({"idx": next_idx}))

    script = FILLER_INSIGHTS[next_idx]
    return _make_queue_item(
        "FILLER_INSIGHT", 5, script,
        "💡 INSIGHT",
        script[:80],
        240,
    )


def generate_filler_live():
    """Generate a filler insight for immediate use (called by consume endpoint)."""
    return get_filler_insight()


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run():
    """Main broadcast service run — called by cron every 5 minutes."""
    t0 = time.time()
    logger.info("=" * 50)
    logger.info("BROADCAST SERVICE RUN — %s", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("=" * 50)

    # Clean expired items first
    items = _read_queue()
    items = _cleanup_queue(items)
    _write_queue(items)
    logger.info("Queue depth after cleanup: %d", len(items))

    # Fetch BTC price (shared across checks)
    btc_data = _fetch_btc_price()

    # Run signal checks in priority order
    new_items = 0

    # 1. PRICE_ALERT (pri=1)
    try:
        item = check_price_alert(btc_data)
        if item:
            _add_to_queue(item)
            new_items += 1
    except Exception as e:
        logger.error("Price alert check error: %s", e)

    # 2. THOUGHT_LEADER (pri=2) — max 1 per run
    try:
        item = check_thought_leader()
        if item:
            _add_to_queue(item)
            new_items += 1
    except Exception as e:
        logger.error("Thought leader check error: %s", e)

    # 3. SPACE_TAP (pri=2)
    try:
        item = check_space_tap()
        if item:
            _add_to_queue(item)
            new_items += 1
    except Exception as e:
        logger.error("Space tap check error: %s", e)

    # 4. ARTICLE_TEASER (pri=3)
    try:
        item = check_article_teaser()
        if item:
            _add_to_queue(item)
            new_items += 1
    except Exception as e:
        logger.error("Article teaser check error: %s", e)

    # 5. METRICS_PULSE (pri=3)
    try:
        item = check_metrics_pulse(btc_data)
        if item:
            _add_to_queue(item)
            new_items += 1
    except Exception as e:
        logger.error("Metrics pulse check error: %s", e)

    # 6. NOSTR_SIGNAL (pri=4)
    try:
        item = check_nostr_signal()
        if item:
            _add_to_queue(item)
            new_items += 1
    except Exception as e:
        logger.error("Nostr signal check error: %s", e)

    # 7. FILLER_INSIGHT (pri=5) — add if queue has <2 items
    final_queue = _read_queue()
    final_queue = _cleanup_queue(final_queue)
    if len(final_queue) < 2:
        filler = get_filler_insight()
        _add_to_queue(filler)
        new_items += 1
        logger.info("Added filler insight (queue was thin)")

    final_queue = _read_queue()
    final_queue = _cleanup_queue(final_queue)
    elapsed = round(time.time() - t0, 1)
    logger.info("Run complete in %ss — %d new items, queue depth: %d",
                elapsed, new_items, len(final_queue))

    return len(final_queue)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    depth = run()
    print(f"Queue depth: {depth}")
    sys.exit(0)
