#!/usr/bin/env python3
"""
fetch_signal_cache.py — Async Nostr relay fetcher for Signal Active segment.

Parallel-connects to 5 relays, pulls kind=1 notes tagged #bitcoin/#btc,
scores by zaps and authority, saves to cache/active_signal.json.

Cron: */15 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 fetch_signal_cache.py >> /tmp/signal_cache.log 2>&1
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [signal_cache] %(levelname)s %(message)s",
)
log = logging.getLogger("signal_cache")

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "active_signal.json")

RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.nostr.band",
    "wss://purplepag.es",
    "wss://relay.primal.net",
]

RELAY_TIMEOUT = 5  # seconds per relay

# Authority figures — boost score if space_title or content mentions them
AUTHORITY_NAMES = ["saylor", "alden", "pysh", "brunell", "lopp"]

# npub display: first8 + "..." + last6
def npub_display(pubkey_hex: str) -> str:
    """Convert hex pubkey to npub-style display: npub1abc...xyz123"""
    if not pubkey_hex or len(pubkey_hex) < 14:
        return f"npub1{pubkey_hex[:8]}...{pubkey_hex[-6:]}" if pubkey_hex else "npub1unknown"
    return f"npub1{pubkey_hex[:8]}...{pubkey_hex[-6:]}"


async def fetch_from_relay(relay_url: str, since: int) -> dict:
    """Connect to a single relay, fetch kind=1 bitcoin-tagged notes. Returns {events, stats}."""
    import websockets

    events = []
    stats = {"relay": relay_url, "connected": False, "events_raw": 0, "events_filtered": 0, "error": None}
    sub_id = f"pp_signal_{int(time.time()) % 100000}"

    req = json.dumps([
        "REQ", sub_id,
        {
            "kinds": [1],
            "#t": ["bitcoin", "btc", "Bitcoin", "BTC"],
            "since": since,
            "limit": 100,
        },
    ])

    try:
        async with websockets.connect(relay_url, open_timeout=RELAY_TIMEOUT, close_timeout=2) as ws:
            stats["connected"] = True
            await ws.send(req)

            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=RELAY_TIMEOUT)
                    msg = json.loads(raw)
                    if not isinstance(msg, list):
                        continue

                    if msg[0] == "EVENT" and len(msg) >= 3:
                        event = msg[2]
                        stats["events_raw"] += 1
                        content = event.get("content", "").strip()

                        # Skip too short, too long, or URL-only
                        if len(content) < 20 or len(content) > 1000:
                            continue
                        if content.startswith("http") and " " not in content:
                            continue

                        # Check for zap tags
                        tags = event.get("tags", [])
                        has_zap = any(t[0] == "zap" for t in tags if len(t) > 0)

                        events.append({
                            "text": content,
                            "pubkey": event.get("pubkey", ""),
                            "created_at": event.get("created_at", 0),
                            "relay": relay_url,
                            "has_zap": has_zap,
                            "tags": [t for t in tags if t[0] in ("t", "p", "e", "zap")],
                        })
                        stats["events_filtered"] += 1

                    elif msg[0] == "EOSE":
                        break

                except asyncio.TimeoutError:
                    log.debug("Timeout reading from %s", relay_url)
                    break

            # Close subscription
            try:
                await ws.send(json.dumps(["CLOSE", sub_id]))
            except Exception:
                pass

    except Exception as e:
        stats["error"] = str(e)
        log.warning("Relay %s failed: %s", relay_url, e)

    return {"events": events, "stats": stats}


def score_event(event: dict) -> int:
    """Score a Nostr event. Base score by content quality, +20 for zap, +50 for authority."""
    text = event.get("text", "")
    score = 0

    # Word count quality (longer = more substantive)
    words = len(text.split())
    if words < 8:
        return 0
    score += min(words, 50)

    # Bitcoin keyword density
    import re
    btc_keywords = re.findall(
        r"\b(bitcoin|btc|satoshi|mining|halving|hashrate|etf|mempool|"
        r"lightning|taproot|ordinals|hodl|sats|layer.2|proof.of.work|nostr)\b",
        text.lower(),
    )
    score += len(set(btc_keywords)) * 10

    # Zap boost
    if event.get("has_zap"):
        score += 20

    # Authority boost — check content for known names
    text_lower = text.lower()
    for name in AUTHORITY_NAMES:
        if name in text_lower:
            score += 50
            break

    return score


def deduplicate_events(events: list) -> list:
    """Deduplicate by content hash, keep highest scored."""
    seen = {}
    for ev in events:
        key = hashlib.md5(ev["text"][:100].encode()).hexdigest()
        if key not in seen or ev.get("_score", 0) > seen[key].get("_score", 0):
            seen[key] = ev
    return list(seen.values())


async def fetch_all():
    """Parallel fetch from all relays, score, deduplicate, save cache."""
    since = int(time.time()) - 86400  # last 24h

    log.info("Fetching from %d relays (24h lookback, 5s timeout each)", len(RELAYS))

    tasks = [fetch_from_relay(url, since) for url in RELAYS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_events = []
    relay_stats = []

    for r in results:
        if isinstance(r, Exception):
            relay_stats.append({"relay": "unknown", "error": str(r)})
            continue
        all_events.extend(r["events"])
        relay_stats.append(r["stats"])

    log.info("Raw events: %d from %d relays", len(all_events), len(RELAYS))

    # Score all events
    for ev in all_events:
        ev["_score"] = score_event(ev)

    # Filter zero-score
    all_events = [ev for ev in all_events if ev["_score"] > 0]

    # Deduplicate
    all_events = deduplicate_events(all_events)

    # Sort by score descending
    all_events.sort(key=lambda x: x["_score"], reverse=True)

    # Format for cache — top 20 posts
    nostr_posts = []
    for ev in all_events[:20]:
        nostr_posts.append({
            "text": ev["text"],
            "pubkey": ev["pubkey"],
            "display_name": npub_display(ev["pubkey"]),
            "created_at": ev["created_at"],
            "relay": ev["relay"],
            "score": ev["_score"],
            "has_zap": ev.get("has_zap", False),
        })

    cache_data = {
        "fetched_at": time.time(),
        "fetched_at_iso": datetime.now(timezone.utc).isoformat(),
        "relay_stats": relay_stats,
        "nostr_posts": nostr_posts,
        "total_raw": sum(s.get("events_raw", 0) for s in relay_stats),
        "total_filtered": sum(s.get("events_filtered", 0) for s in relay_stats),
        "total_scored": len(nostr_posts),
    }

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=2)

    log.info("Cache saved: %s (%d posts, %d raw events)",
             CACHE_FILE, len(nostr_posts), cache_data["total_raw"])

    # Print relay stats
    for s in relay_stats:
        status = "OK" if s.get("connected") else "FAIL"
        err = f" ({s['error']})" if s.get("error") else ""
        log.info("  %s: %s — %d raw, %d filtered%s",
                 s["relay"], status, s.get("events_raw", 0), s.get("events_filtered", 0), err)

    return cache_data


if __name__ == "__main__":
    data = asyncio.run(fetch_all())
    print(f"\nCache written: {CACHE_FILE}")
    print(f"Posts: {data['total_scored']} | Raw: {data['total_raw']} | Relays: {len(data['relay_stats'])}")
    if data["nostr_posts"]:
        print(f"\nTop 3 posts:")
        for p in data["nostr_posts"][:3]:
            print(f"  [{p['display_name']}] (score:{p['score']}) {p['text'][:100]}...")
