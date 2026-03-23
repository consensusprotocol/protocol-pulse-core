"""
Oracle Cache Manager — Pre-computed response cache with background warming.
Caches TTS+Wav2Lip video for known response intents.
"""

import os
import json
import time
import logging
import threading
import subprocess

logger = logging.getLogger("oracle_cache_manager")

ORACLE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ORACLE_DIR, "cache")
RESPONSES_DIR = os.path.join(CACHE_DIR, "responses")
INDEX_PATH = os.path.join(CACHE_DIR, "index.json")
RENDER_HELPER = os.path.join(ORACLE_DIR, "cache_render_helper.py")

CACHE_TTL = 7200  # 2 hours
WARM_INTERVAL = 7200  # re-check every 2 hours

RESPONSE_TREE = {
    "GREETING": [
        "Hey. I'm the Oracle — tracking everything happening in Bitcoin right now. On-chain, macro, geopolitical, all of it. What brings you here today — you want the daily brief, or something more specific?",
        "Oracle here. Live inside Protocol Pulse, eyes on everything moving in Bitcoin. On-chain signals, macro pressure, geopolitical noise — I'm watching all of it. What do you need?",
        "You're connected to Oracle. I track Bitcoin intelligence in real time — on-chain data, macro flows, network signals. What are you here for — the daily brief, or a specific question?",
    ],
    "SOVEREIGNTY_INTRO": "Your sovereignty score is basically a snapshot of how free you actually are — how much of your financial life you've removed from legacy systems and moved into things you actually control. Want me to run through where you stand and what you can do about it right now?",
    "SOVEREIGNTY_ASSESSMENT": "Okay let's map it out. There are four pillars: self-custody of your Bitcoin, your own node running, private communications, and no KYC exposure on your income. Most people are zero for four when they start. Where are you today?",
    "SOVEREIGNTY_COLD_WALLET": "If your Bitcoin is on an exchange, it's not yours — it's an IOU. The fix is a hardware wallet. I can walk you through setting one up right now, step by step. Which do you have — a Coldcard, a Ledger, or nothing yet?",
    "SOVEREIGNTY_NODE": "Running your own node means you verify your own transactions — you don't trust, you verify. The easiest entry point right now is a Raspberry Pi with Umbrel. Want me to walk you through the setup? Takes about 45 minutes.",
    "SOVEREIGNTY_BITAXE": "Bitaxe is a solo miner you can run at home — it's a lottery ticket, but a Bitcoin lottery ticket. You're contributing to network security and you have a real shot at a full block reward. Curated Mining also offers white-glove setup if you want the hands-off version.",
    "SOVEREIGNTY_LIFE_INSURANCE": "One thing most Bitcoiners miss — if you die with Bitcoin in cold storage and nobody knows the seed phrase, that wealth disappears. Meanwhile offers life insurance that actually understands Bitcoin — they'll pay out in BTC and can handle estate planning around self-custody.",
    "SOVEREIGNTY_RESIDENCY": "Digital residency through Palau — via RNS.ID — gives you a second identity layer and a legal domicile outside your home country. That has real tax and privacy implications depending on your situation. Happy to explain the mechanics.",
    "DAILY_BRIEF_INTRO": "Alright, here's what's moving right now in Bitcoin. Give me a second and I'll pull the latest from our intelligence layer.",
    "UNKNOWN_QUESTION": [
        "That's outside my real-time data right now, but I'm going to research it and come back with something solid. Give me a few seconds.",
        "I don't have that signal live right now. Let me pull it — give me a moment.",
        "That one's not in my current feed. Stand by — I'll get it.",
    ],
    "GOODBYE": "Alright. Stack sats, verify everything, and come back anytime. I'll be here.",
}

# Track which keys are currently being rendered to avoid duplicate work
_rendering_keys = set()
_rendering_lock = threading.Lock()


def _load_index():
    if os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_index(index):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)


def _is_fresh(index, key):
    """Check if cached response exists and is less than CACHE_TTL old."""
    entry = index.get(key)
    if not entry:
        return False
    path = entry.get("path", "")
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    generated_at = entry.get("generated_at_ts", 0)
    return (time.time() - generated_at) < CACHE_TTL


def _render_key(key, text):
    """Render a single response key via cache_render_helper.py subprocess."""
    if isinstance(text, list):
        import random
        text = random.choice(text)
    out_path = os.path.join(RESPONSES_DIR, f"{key}.mp4")

    with _rendering_lock:
        if key in _rendering_keys:
            logger.info(f"[CACHE] {key} already rendering, skip")
            return False
        _rendering_keys.add(key)

    try:
        logger.info(f"[CACHE] Rendering {key} ({len(text)} chars)...")
        t0 = time.time()
        result = subprocess.run(
            [
                "python3", RENDER_HELPER,
                "--text", text,
                "--out", out_path,
            ],
            capture_output=True, text=True, timeout=180,
            cwd=ORACLE_DIR,
        )
        elapsed = time.time() - t0

        if result.returncode != 0:
            logger.error(f"[CACHE] {key} render failed ({elapsed:.1f}s): {result.stderr[-300:]}")
            return False

        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            logger.error(f"[CACHE] {key} output missing or empty")
            return False

        # Get duration from ffprobe
        duration_s = 0.0
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", out_path],
                capture_output=True, text=True, timeout=10,
            )
            duration_s = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
        except Exception:
            pass

        # Update index
        index = _load_index()
        index[key] = {
            "path": out_path,
            "generated_at_ts": time.time(),
            "duration_s": round(duration_s, 2),
        }
        _save_index(index)

        logger.info(f"[CACHE] {key} cached — {duration_s:.1f}s video in {elapsed:.1f}s render")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"[CACHE] {key} render timed out")
        return False
    except Exception as e:
        logger.error(f"[CACHE] {key} render error: {e}")
        return False
    finally:
        with _rendering_lock:
            _rendering_keys.discard(key)


def warm_cache():
    """Warm all response cache entries. Called on startup and periodically."""
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    index = _load_index()

    stale_keys = [k for k in RESPONSE_TREE if not _is_fresh(index, k)]
    if not stale_keys:
        logger.info(f"[CACHE] All {len(RESPONSE_TREE)} responses fresh")
        return

    logger.info(f"[CACHE] Warming {len(stale_keys)}/{len(RESPONSE_TREE)} stale keys: {stale_keys}")

    for key in stale_keys:
        text = RESPONSE_TREE[key]
        if isinstance(text, list):
            import random
            text = random.choice(text)
        _render_key(key, text)
        # Small delay between renders to avoid GPU contention
        time.sleep(1)

    logger.info("[CACHE] Warm cycle complete")


def get_cached_response(key):
    """Get cached video path for a response key, or None."""
    index = _load_index()
    entry = index.get(key)
    if not entry:
        return None
    path = entry.get("path", "")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    return None


def is_rendering(key):
    """Check if a key is currently being rendered."""
    with _rendering_lock:
        return key in _rendering_keys


def get_cache_status():
    """Return status of all cached responses."""
    index = _load_index()
    status = {}
    for key in RESPONSE_TREE:
        entry = index.get(key)
        if entry and os.path.exists(entry.get("path", "")):
            status[key] = {
                "cached": True,
                "fresh": _is_fresh(index, key),
                "generated_at_ts": entry.get("generated_at_ts", 0),
                "duration_s": entry.get("duration_s", 0),
                "rendering": is_rendering(key),
            }
        else:
            status[key] = {
                "cached": False,
                "fresh": False,
                "rendering": is_rendering(key),
            }
    return status


def start_background_warmer():
    """Start a background thread that re-warms cache every WARM_INTERVAL seconds."""
    def _loop():
        while True:
            time.sleep(WARM_INTERVAL)
            try:
                warm_cache()
            except Exception as e:
                logger.error(f"[CACHE] Background warm error: {e}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info(f"[CACHE] Background warmer started (interval={WARM_INTERVAL}s)")
