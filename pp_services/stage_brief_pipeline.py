#!/usr/bin/env python3
"""
Stage Brief Pipeline — 3x/day Oracle Stage brief generation with intel extraction.

Schedule: 06:00 UTC (morning), 14:00 UTC (midday), 22:00 UTC (evening)

Pipeline:
1. Fetch live BTC data (price, mempool, hashrate, FNG, block height)
2. Generate brief script via Claude Haiku
3. Generate audio via Chatterbox TTS (avatar server /oracle/voice)
4. Render avatar video via Wav2Lip (avatar server /generate)
5. Save to video_pipeline_v3/data/stage_briefs/ + update latest.json
6. Intel extraction: social clips, newsletter hook, sentiment signal,
   article seeds, oracle context — single Claude Haiku batch call
7. Log to logs/brief_pipeline.log
"""

import base64
import fcntl
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEFS_DIR = os.path.join(BASE, "video_pipeline_v3", "data", "stage_briefs")
LOGS_DIR = os.path.join(BASE, "logs")
DATA_DIR = os.path.join(BASE, "data")

AVATAR_BASE = os.environ.get("AVATAR_BASE_URL", "http://localhost:8200")
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

os.makedirs(LOGS_DIR, exist_ok=True)

logger = logging.getLogger("stage_brief_pipeline")
logger.setLevel(logging.INFO)

_fh = logging.FileHandler(os.path.join(LOGS_DIR, "brief_pipeline.log"))
_fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_fh)

_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_sh)

# ---------------------------------------------------------------------------
# Brief type labels
# ---------------------------------------------------------------------------

BRIEF_TYPES = {
    6: "morning",    # 06:00 UTC
    14: "midday",    # 14:00 UTC
    22: "evening",   # 22:00 UTC
}

_FRESHNESS_RULE = (
    " KOL FRESHNESS LAW: If the Pulse Check context contains quotes or tweets from thought "
    "leaders, do NOT claim they were said 'today' or 'this morning' unless the data includes "
    "a timestamp confirming it. Use neutral framing like 'recently said' or 'has been saying' "
    "for undated quotes. Never present stale intelligence as breaking news."
)

BRIEF_SYSTEM_PROMPTS = {
    "morning": (
        "You are Oracle, a Bitcoin intelligence reporter delivering the morning brief. "
        "Cover overnight developments, Asia session moves, and what to watch for the day ahead. "
        "Write a punchy 90-second spoken brief (max 200 words). PBX voice: direct, confident, "
        "no fluff. No 'Hello' or 'Welcome'. Start with the strongest insight."
        + _FRESHNESS_RULE
    ),
    "midday": (
        "You are Oracle, a Bitcoin intelligence reporter delivering the midday brief. "
        "Cover US morning session action, any breaking news, and key on-chain signals. "
        "Write a punchy 90-second spoken brief (max 200 words). PBX voice: direct, confident, "
        "no fluff. No 'Hello' or 'Welcome'. Start with the strongest insight."
        + _FRESHNESS_RULE
    ),
    "evening": (
        "You are Oracle, a Bitcoin intelligence reporter delivering the evening brief. "
        "Wrap the day: US close action, daily high/low, key takeaways, what to watch overnight. "
        "Write a punchy 90-second spoken brief (max 200 words). PBX voice: direct, confident, "
        "no fluff. No 'Hello' or 'Welcome'. Start with the strongest insight."
        + _FRESHNESS_RULE
    ),
}

# ---------------------------------------------------------------------------
# Data Gathering (standalone, no relay dependency)
# ---------------------------------------------------------------------------

def _fetch_btc_price():
    # Try internal API first (no rate limits)
    try:
        r = requests.get("http://localhost:5000/api/btc-price", timeout=5)
        if r.status_code == 200:
            d = r.json()
            price = d.get("price") or d.get("bitcoin", {}).get("usd")
            change = d.get("change_24h") or d.get("bitcoin", {}).get("usd_24h_change", 0)
            if price and float(price) > 0:
                return {
                    "price": float(price),
                    "change_24h": round(float(change), 2),
                    "market_cap": d.get("market_cap", 0),
                    "volume_24h": d.get("volume_24h", 0),
                }
    except Exception:
        pass

    # Fallback to CoinGecko
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd",
                    "include_24hr_change": "true", "include_market_cap": "true",
                    "include_24hr_vol": "true"},
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()["bitcoin"]
        return {
            "price": d["usd"],
            "change_24h": round(d.get("usd_24h_change", 0), 2),
            "market_cap": d.get("usd_market_cap", 0),
            "volume_24h": d.get("usd_24h_vol", 0),
        }
    except Exception as e:
        logger.critical("BTC price fetch failed on ALL sources: %s", e)
        raise RuntimeError(f"BTC price unavailable: {e}")


def _fetch_mempool():
    result = {"fastest_fee": 0, "half_hour_fee": 0, "hour_fee": 0,
              "economy_fee": 0, "tx_count": 0, "vsize": 0}
    try:
        r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=10)
        r.raise_for_status()
        fees = r.json()
        result["fastest_fee"] = fees.get("fastestFee", 0)
        result["half_hour_fee"] = fees.get("halfHourFee", 0)
        result["hour_fee"] = fees.get("hourFee", 0)
        result["economy_fee"] = fees.get("economyFee", 0)
    except Exception as e:
        logger.warning("Fee fetch failed: %s", e)
    try:
        r = requests.get("https://mempool.space/api/mempool", timeout=10)
        r.raise_for_status()
        mp = r.json()
        result["tx_count"] = mp.get("count", 0)
        result["vsize"] = mp.get("vsize", 0)
    except Exception as e:
        logger.warning("Mempool fetch failed: %s", e)
    return result


def _fetch_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        r.raise_for_status()
        d = r.json()["data"][0]
        return {"value": int(d["value"]), "label": d["value_classification"]}
    except Exception as e:
        logger.warning("FNG fetch failed: %s", e)
        return {"value": 50, "label": "Neutral"}


def _fetch_hashrate():
    try:
        r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=15)
        r.raise_for_status()
        data = r.json()
        hr = data.get("hashrates", [])
        current_hr = hr[-1]["avgHashrate"] if hr else 0
        return {"hashrate_eh": round(current_hr / 1e18, 1)}
    except Exception as e:
        logger.warning("Hashrate fetch failed: %s", e)
        return {"hashrate_eh": 0}


def _fetch_block_height():
    try:
        r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=10)
        r.raise_for_status()
        return int(r.text.strip())
    except Exception as e:
        logger.warning("Block height fetch failed: %s", e)
        return 0


def gather_intel():
    """Fetch all live data sources for brief generation."""
    logger.info("Fetching live data...")
    btc = _fetch_btc_price()
    mempool = _fetch_mempool()
    fng = _fetch_fear_greed()
    hashrate = _fetch_hashrate()
    block_height = _fetch_block_height()

    data = {
        "btc": btc,
        "mempool": mempool,
        "fng": fng,
        "hashrate": hashrate,
        "block_height": block_height,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("BTC: $%s (%s%%), FNG: %s (%s), Hash: %s EH/s, Block: %s",
                f"{btc['price']:,.0f}", f"{btc['change_24h']:+.1f}",
                fng['value'], fng['label'],
                hashrate['hashrate_eh'], f"{block_height:,}")
    return data


# ---------------------------------------------------------------------------
# API Key
# ---------------------------------------------------------------------------

def _get_anthropic_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    env_path = os.path.join(BASE, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip("'\"")
                    os.environ["ANTHROPIC_API_KEY"] = key
                    return key
    raise RuntimeError("ANTHROPIC_API_KEY not set")




# ---------------------------------------------------------------------------
# Pulse Check Script Loader (multi-value intel reuse)
# ---------------------------------------------------------------------------

def _load_pulse_check_script():
    """Load the most recent Pulse Check script for intel reuse.
    
    The Pulse Check video pipeline compiles transcripts, clips, and narrative
    from 10+ Bitcoin sources into a daily script. This is the richest intel
    source we have — reuse it as the Stage brief's primary content backbone.
    Returns condensed script text or None if not available.
    """
    output_dir = os.path.join(BASE, "video_pipeline_v3", "output")
    if not os.path.exists(output_dir):
        return None

    # Find most recent script.json (skip test_ dirs, prefer dated dirs)
    candidates = []
    for d in os.listdir(output_dir):
        script_path = os.path.join(output_dir, d, "script.json")
        if os.path.exists(script_path):
            mtime = os.path.getmtime(script_path)
            candidates.append((mtime, script_path))

    if not candidates:
        return None

    # Most recent script
    candidates.sort(reverse=True)
    latest_path = candidates[0][1]
    age_hours = (datetime.now().timestamp() - candidates[0][0]) / 3600

    # Only use if <24 hours old — stale scripts mislead the brief
    if age_hours > 24:
        logger.info("Pulse Check script too old (%.1fh) — skipping", age_hours)
        return None

    try:
        with open(latest_path) as f:
            script_data = json.load(f)

        # Extract dialogue lines — the actual spoken content
        lines = []
        if isinstance(script_data, dict):
            # Try common script structures
            for key in ("segments", "dialogue", "lines", "script", "content"):
                if key in script_data:
                    items = script_data[key]
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                text = item.get("text") or item.get("line") or item.get("content") or ""
                            elif isinstance(item, str):
                                text = item
                            else:
                                continue
                            if text and len(text) > 20:
                                lines.append(text.strip())
                    break

        if not lines:
            # Fallback: flatten entire JSON to text
            raw = json.dumps(script_data)
            lines = [raw[:2000]]

        condensed = " ".join(lines)[:3000]  # cap at 3000 chars to stay within token budget
        logger.info("Pulse Check script loaded: %.1fh old, %d chars", age_hours, len(condensed))
        return condensed

    except Exception as e:
        logger.warning("Pulse Check script load failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Brief Script Generation
# ---------------------------------------------------------------------------

def generate_brief_script(data, brief_type="morning"):
    """Generate brief script via Claude Haiku."""
    api_key = _get_anthropic_key()

    btc = data["btc"]
    mempool = data["mempool"]
    fng = data["fng"]
    hashrate = data["hashrate"]

    user_prompt = (
        f"Current Bitcoin data:\n"
        f"- BTC Price: ${btc['price']:,.0f} ({btc['change_24h']:+.1f}% 24h)\n"
        f"- Market Cap: ${btc['market_cap']/1e9:,.0f}B\n"
        f"- 24h Volume: ${btc.get('volume_24h', 0)/1e9:,.1f}B\n"
        f"- Fear & Greed: {fng['value']} ({fng['label']})\n"
        f"- Hashrate: {hashrate['hashrate_eh']} EH/s\n"
        f"- Mempool: {mempool['tx_count']:,} txs, fastest fee {mempool['fastest_fee']} sat/vB\n"
        f"- Block Height: {data['block_height']:,}\n"
        f"- Timestamp: {data['timestamp']}\n\n"
        f"Generate a {brief_type} brief. Max 200 words, punchy, ready to speak."
    )

    # Multi-value intel reuse: enrich with Pulse Check script if available
    pulse_script = _load_pulse_check_script()
    if pulse_script:
        user_prompt += (
            f"\n\nContext from today's Pulse Check script "
            f"(use as primary narrative backbone):\n{pulse_script[:2000]}"
        )
        logger.info("[brief] Pulse Check script injected into prompt")
    else:
        logger.info("[brief] No Pulse Check script — using live data only")

    system = BRIEF_SYSTEM_PROMPTS.get(brief_type, BRIEF_SYSTEM_PROMPTS["morning"])

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
            "system": system,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"].strip()
    word_count = len(text.split())
    logger.info("Brief script: %d words (%s)", word_count, brief_type)
    return text


# ---------------------------------------------------------------------------
# Intel Extraction (5 tasks in one Haiku call)
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM = (
    "You are an intel extraction engine for Protocol Pulse. Given a Bitcoin brief script, "
    "extract ALL of the following in a single JSON response. Be precise and concise.\n\n"
    "Return ONLY valid JSON with these exact keys:\n"
    "{\n"
    '  "tweets": ["tweet1 (max 280 chars)", "tweet2", "tweet3"],\n'
    '  "newsletter_hook": "2-sentence hook with the most important insight",\n'
    '  "sentiment": {\n'
    '    "score": <-100 to +100>,\n'
    '    "bullish_signals": ["signal1", "signal2"],\n'
    '    "bearish_signals": ["signal1"],\n'
    '    "neutral_topics": ["topic1"]\n'
    '  },\n'
    '  "article_seeds": [\n'
    '    {"headline": "...", "angle": "...", "tags": ["bitcoin", "..."]}\n'
    '  ],\n'
    '  "oracle_bullets": ["bullet1", "bullet2", "bullet3"]\n'
    "}"
)


def extract_intel(brief_text, brief_type, timestamp_str):
    """Run all 5 intel extractions in a single Claude Haiku call."""
    api_key = _get_anthropic_key()

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 1000,
            "system": EXTRACTION_SYSTEM,
            "messages": [{"role": "user", "content": f"Brief ({brief_type}):\n\n{brief_text}"}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()["content"][0]["text"].strip()

    # Parse JSON from response (handle markdown code blocks)
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        logger.error("Intel extraction: no JSON found in response")
        return
    extracted = json.loads(json_match.group())

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M")

    # a) Social clips
    tweets_dir = os.path.join(DATA_DIR, "social_queue")
    os.makedirs(tweets_dir, exist_ok=True)
    tweets = extracted.get("tweets", [])
    with open(os.path.join(tweets_dir, f"{ts}_tweets.json"), "w") as f:
        json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
                    "tweets": tweets}, f, indent=2)
    logger.info("Extracted %d tweets", len(tweets))

    # b) Newsletter hook
    hook_dir = os.path.join(DATA_DIR, "newsletter_queue")
    os.makedirs(hook_dir, exist_ok=True)
    hook = extracted.get("newsletter_hook", "")
    with open(os.path.join(hook_dir, f"{ts}_hook.json"), "w") as f:
        json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
                    "hook": hook}, f, indent=2)
    logger.info("Extracted newsletter hook: %s", hook[:80])

    # c) Sentiment signal
    sentiment_dir = os.path.join(DATA_DIR, "sentiment")
    os.makedirs(sentiment_dir, exist_ok=True)
    sentiment = extracted.get("sentiment", {})
    with open(os.path.join(sentiment_dir, f"{ts}_signal.json"), "w") as f:
        json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
                    **sentiment}, f, indent=2)
    logger.info("Sentiment score: %s", sentiment.get("score", "N/A"))

    # d) Article seeds
    seeds_dir = os.path.join(DATA_DIR, "article_seeds")
    os.makedirs(seeds_dir, exist_ok=True)
    seeds = extracted.get("article_seeds", [])
    with open(os.path.join(seeds_dir, f"{ts}_seeds.json"), "w") as f:
        json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
                    "seeds": seeds}, f, indent=2)
    logger.info("Extracted %d article seeds", len(seeds))

    # e) Oracle context
    ctx_dir = os.path.join(DATA_DIR, "oracle_context")
    os.makedirs(ctx_dir, exist_ok=True)
    bullets = extracted.get("oracle_bullets", [])
    ctx = {
        "generated_at": now.isoformat(),
        "brief_type": brief_type,
        "bullets": bullets,
        "sentiment_score": sentiment.get("score", 0),
        "brief_summary": brief_text[:300],
    }
    with open(os.path.join(ctx_dir, "latest_brief.json"), "w") as f:
        json.dump(ctx, f, indent=2)
    logger.info("Oracle context updated: %d bullets", len(bullets))

    return extracted


# ---------------------------------------------------------------------------
# TTS via Chatterbox (avatar server /oracle/voice)
# ---------------------------------------------------------------------------

def _generate_tts_chatterbox(text):
    """Generate TTS via Chatterbox on avatar server. Returns raw audio bytes.
    Retries up to 3 times with 10s delay between attempts.
    """
    # Normalize numbers and pronunciation before sending to TTS
    try:
        sys.path.insert(0, os.path.join(BASE, 'oracle'))
        from oracle_dialogue_engine import normalize_pronunciation
        text = normalize_pronunciation(text)
    except Exception as e:
        logger.warning("normalize_pronunciation unavailable: %s", e)

    for attempt in range(1, 4):
        try:
            logger.info("[TTS] Attempt %d/3 for %d chars of text", attempt, len(text))
            resp = requests.post(
                f"{AVATAR_BASE}/oracle/voice",
                json={"text": text},
                timeout=300,
            )
            if resp.status_code == 200:
                logger.info("[TTS] Chatterbox OK: %d bytes (attempt %d)", len(resp.content), attempt)
                return resp.content
            logger.warning("[TTS] Chatterbox HTTP %d on attempt %d", resp.status_code, attempt)
        except requests.exceptions.Timeout:
            logger.warning("[TTS] Timeout on attempt %d/3", attempt)
        except requests.exceptions.ConnectionError as e:
            logger.warning("[TTS] Connection error on attempt %d/3: %s", attempt, e)
        except Exception as e:
            logger.warning("[TTS] Unexpected error on attempt %d/3: %s", attempt, e)
        if attempt < 3:
            logger.info("[TTS] Retrying in 10s...")
            time.sleep(10)
    raise RuntimeError("Chatterbox TTS failed after 3 attempts")


# ---------------------------------------------------------------------------
# Avatar Video Render
# ---------------------------------------------------------------------------

def _split_into_chunks(text, max_sentences=3):
    """Split text into chunks of ~max_sentences for the 30s avatar limit."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current = []
    for s in sentences:
        current.append(s)
        if len(current) >= max_sentences:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def _render_avatar_chunk(audio_bytes):
    """Render a single chunk through Wav2Lip via avatar server.
    Retries up to 3 times with 10s delay. Timeout 300s per attempt.
    """
    is_wav = audio_bytes[:4] == b"RIFF"
    content_type = "audio/wav" if is_wav else "audio/mpeg"
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    for attempt in range(1, 4):
        try:
            logger.info("[RENDER] Avatar chunk attempt %d/3 (%d bytes audio)", attempt, len(audio_bytes))
            resp = requests.post(
                f"{AVATAR_BASE}/generate",
                json={
                    "audio_base64": audio_b64,
                    "content_type": content_type,
                    "enable_blinks": True,
                    "enable_head_movement": True,
                    "fps": 30.0,
                },
                timeout=300,
            )
            resp.raise_for_status()
            duration = float(resp.headers.get("X-Duration", 0))
            logger.info("[RENDER] Avatar chunk OK: %d bytes, %.1fs (attempt %d)", len(resp.content), duration, attempt)
            return resp.content, duration
        except requests.exceptions.Timeout:
            logger.warning("[RENDER] Avatar chunk timeout on attempt %d/3", attempt)
        except requests.exceptions.ConnectionError as e:
            logger.warning("[RENDER] Avatar chunk connection error on attempt %d/3: %s", attempt, e)
        except Exception as e:
            logger.warning("[RENDER] Avatar chunk error on attempt %d/3: %s", attempt, e)
        if attempt < 3:
            logger.info("[RENDER] Retrying in 10s...")
            time.sleep(10)
    raise RuntimeError("Avatar render failed after 3 attempts")


def _render_audio_only_video(audio_bytes_list):
    """Fallback: combine audio chunks with static PBX image frame into an MP4.
    Used when avatar server is down — never returns blank.
    """
    logger.info("[FALLBACK] Generating audio-only video with static frame")
    static_img = os.path.join(BASE, "static", "img", "oracle_avatar_static.png")
    if not os.path.exists(static_img):
        # Try alternate paths
        for alt in [
            os.path.join(BASE, "oracle", "Proto_P_Avatar_1024.png"),
            os.path.join(BASE, "static", "oracle_avatar.png"),
        ]:
            if os.path.exists(alt):
                static_img = alt
                break

    tmpdir = tempfile.mkdtemp(prefix="stage_brief_fallback_")
    try:
        # Concatenate all audio chunks
        audio_paths = []
        for i, ab in enumerate(audio_bytes_list):
            p = os.path.join(tmpdir, f"audio_{i:03d}.wav")
            with open(p, "wb") as f:
                f.write(ab)
            audio_paths.append(p)

        if len(audio_paths) == 1:
            combined_audio = audio_paths[0]
        else:
            concat_list = os.path.join(tmpdir, "audio_concat.txt")
            with open(concat_list, "w") as f:
                for p in audio_paths:
                    f.write(f"file '{p}'\n")
            combined_audio = os.path.join(tmpdir, "combined.wav")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1", combined_audio,
            ], capture_output=True, timeout=60)

        # Get audio duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", combined_audio],
            capture_output=True, text=True, timeout=10,
        )
        if probe.returncode != 0:
            logger.warning("[FALLBACK] ffprobe failed (rc=%d): %s — using 30s default",
                           probe.returncode, probe.stderr.strip()[:200])
        duration = float(probe.stdout.strip()) if probe.returncode == 0 and probe.stdout.strip() else 30.0

        # Create video: static image + audio
        output_path = os.path.join(tmpdir, "fallback.mp4")
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", static_img,
            "-i", combined_audio,
            "-c:v", "libx264", "-tune", "stillimage", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            logger.error("[FALLBACK] FFmpeg failed: %s", result.stderr.decode()[-500:])
            raise RuntimeError("Audio-only video generation failed")

        with open(output_path, "rb") as f:
            video_bytes = f.read()

        logger.info("[FALLBACK] Audio-only video: %d bytes, %.1fs", len(video_bytes), duration)
        return video_bytes, duration

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def render_avatar_video(brief_text):
    """Render full brief as avatar video, chunking for 30s limit.
    Falls back to audio-only with static image if avatar render fails.
    """
    chunks = _split_into_chunks(brief_text, max_sentences=3)
    logger.info("[RENDER] Split brief into %d chunks", len(chunks))

    # First generate all TTS audio (works even if avatar server is down)
    audio_chunks = []
    for i, chunk in enumerate(chunks):
        logger.info("[RENDER] TTS chunk %d/%d: %d words", i + 1, len(chunks), len(chunk.split()))
        audio = _generate_tts_chatterbox(chunk)
        audio_chunks.append(audio)

    # Try avatar render
    try:
        if len(chunks) == 1:
            video_bytes, duration = _render_avatar_chunk(audio_chunks[0])
            return video_bytes, duration

        tmpdir = tempfile.mkdtemp(prefix="stage_brief_")
        part_paths = []
        total_duration = 0.0

        try:
            for i, audio in enumerate(audio_chunks):
                logger.info("[RENDER] Rendering avatar chunk %d/%d", i + 1, len(chunks))
                video_bytes, dur = _render_avatar_chunk(audio)
                total_duration += dur

                part_path = os.path.join(tmpdir, f"part_{i:03d}.mp4")
                with open(part_path, "wb") as f:
                    f.write(video_bytes)
                part_paths.append(part_path)

            concat_list = os.path.join(tmpdir, "concat.txt")
            with open(concat_list, "w") as f:
                for p in part_paths:
                    f.write(f"file '{p}'\n")

            output_path = os.path.join(tmpdir, "final.mp4")
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                "-pix_fmt", "yuv420p", "-r", "30", "-vsync", "cfr",
                "-vf", "setpts=PTS-STARTPTS",
                "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
                "-movflags", "+faststart",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                logger.error("FFmpeg concat failed: %s", result.stderr.decode()[-500:])
                raise RuntimeError("FFmpeg concat failed")

            with open(output_path, "rb") as f:
                final_bytes = f.read()

            return final_bytes, total_duration

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    except Exception as e:
        logger.warning("[RENDER] Avatar render failed: %s — falling back to audio-only video", e)
        return _render_audio_only_video(audio_chunks)


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def generate_brief(brief_type=None):
    """
    Full stage brief pipeline: gather -> script -> extract intel -> TTS -> render -> save.

    Args:
        brief_type: "morning", "midday", or "evening". Auto-detected from UTC hour if None.

    Returns:
        Path to generated MP4, or None on failure.
    """
    t0 = time.time()
    now = datetime.now(timezone.utc)

    if brief_type is None:
        hour = now.hour
        if hour < 10:
            brief_type = "morning"
        elif hour < 18:
            brief_type = "midday"
        else:
            brief_type = "evening"

    logger.info("=" * 60)
    logger.info("STAGE BRIEF PIPELINE — %s", brief_type.upper())
    logger.info("=" * 60)

    try:
        # 1. Gather fresh intel
        logger.info("[1/5] Fetching live data...")
        t1 = time.time()
        data = gather_intel()
        logger.info("[1/5] Live data fetched in %.1fs", time.time() - t1)

        # 2. Generate brief script via Claude
        logger.info("[2/5] Generating brief script via Claude %s...", CLAUDE_MODEL)
        t2 = time.time()
        brief_text = generate_brief_script(data, brief_type)
        logger.info("[2/5] Brief script generated in %.1fs: %d words", time.time() - t2, len(brief_text.split()))

        # 3. Intel extraction (cheap text-only, before TTS)
        logger.info("[3/5] Extracting intel downstream...")
        ts_str = now.strftime("%Y%m%d_%H%M")
        try:
            t3 = time.time()
            extracted = extract_intel(brief_text, brief_type, ts_str)
            logger.info("[3/5] Intel extracted in %.1fs", time.time() - t3)
        except Exception as e:
            logger.warning("[3/5] Intel extraction failed (non-fatal): %s", e)
            extracted = None

        # 4. TTS + Avatar render via Chatterbox
        logger.info("[4/5] Rendering avatar video (Chatterbox TTS + Wav2Lip) — avatar server: %s", AVATAR_BASE)
        t4 = time.time()
        video_bytes, duration = render_avatar_video(brief_text)
        logger.info("[4/5] Avatar video: %d bytes, %.1fs duration, rendered in %.1fs", len(video_bytes), duration, time.time() - t4)

        # 5. Save outputs
        logger.info("[5/5] Saving brief...")
        os.makedirs(BRIEFS_DIR, exist_ok=True)
        ts_file = now.strftime("%Y%m%d_%H%M")
        date_str = now.strftime("%Y-%m-%d")

        mp4_filename = f"brief_{ts_file}.mp4"
        mp4_path = os.path.join(BRIEFS_DIR, mp4_filename)

        with open(mp4_path, "wb") as f:
            f.write(video_bytes)

        file_size_mb = os.path.getsize(mp4_path) / (1024 * 1024)
        if file_size_mb > 150:
            logger.error("Brief MP4 too large: %.1fMB", file_size_mb)
            os.remove(mp4_path)
            return None

        # Write metadata
        meta = {
            "title": f"Oracle {brief_type.title()} Brief",
            "generated_at": now.isoformat(),
            "duration": round(duration, 1),
            "mp4_path": mp4_filename,
            "mp4_url": f"/data/stage_briefs/{mp4_filename}",
            "video_url": f"/data/stage_briefs/{mp4_filename}",
            "episode_date": date_str,
            "brief_type": brief_type,
            "script_summary": brief_text[:500],
            "word_count": len(brief_text.split()),
            "tts_provider": "chatterbox",
            "btc_price": data["btc"]["price"],
            "sentiment_score": (extracted or {}).get("sentiment", {}).get("score"),
        }
        meta_path = os.path.join(BRIEFS_DIR, f"brief_{ts_file}.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Update latest.json (atomic with fcntl lock)
        latest_path = os.path.join(BRIEFS_DIR, "latest.json")
        with open(latest_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(meta, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)

        # Add to broadcast queue with video_url (direct file write, no module import)
        try:
            import uuid
            from datetime import timedelta
            queue_path = os.path.join(BRIEFS_DIR, "broadcast_queue.json")
            queue_item = {
                "id": str(uuid.uuid4()),
                "type": "ORACLE_BRIEF",
                "priority": 1,
                "script": brief_text[:300],
                "source_label": f"\U0001f399\ufe0f ORACLE {brief_type.upper()}",
                "topic_preview": f"Oracle {brief_type.title()} Brief — ${data['btc']['price']:,.0f}",
                "generated_at": now.isoformat(),
                "expires_at": (now + timedelta(minutes=240)).isoformat(),
                "video_url": f"/data/stage_briefs/{mp4_filename}",
            }
            with open(queue_path, "a+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.seek(0)
                raw = f.read()
                items = json.loads(raw) if raw.strip() else []
                if not isinstance(items, list):
                    items = []
                items.append(queue_item)
                f.seek(0)
                f.truncate()
                json.dump(items, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f, fcntl.LOCK_UN)
            logger.info("Added brief to broadcast queue with video_url: %s", queue_item["video_url"])
        except Exception as e:
            logger.warning("Failed to add to broadcast queue: %s", e)

        elapsed = round(time.time() - t0, 1)
        logger.info("Stage brief complete in %ss: %s", elapsed, mp4_filename)
        return mp4_path

    except Exception as e:
        logger.error("Stage brief pipeline failed: %s", e, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Stage Brief Pipeline")
    parser.add_argument("--type", choices=["morning", "midday", "evening"],
                        help="Brief type (auto-detected if omitted)")
    parser.add_argument("--test", action="store_true",
                        help="Run immediately regardless of schedule")
    args = parser.parse_args()

    result = generate_brief(brief_type=args.type)
    if result:
        print(f"\nSUCCESS: {result}")
        sys.exit(0)
    else:
        print("\nFAILED: Brief generation failed (check logs/brief_pipeline.log)")
        sys.exit(1)
