#!/usr/bin/env python3
"""
morning_brief.py — Protocol Pulse Social Intelligence Layer
Phase 2: Daily LLM Intelligence Brief via Claude Haiku

Runs daily at 6am ET. Reads all fresh signals, produces:
~/protocol_pulse/data/intelligence/morning_intelligence_brief.json
"""

import json
import logging
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path("/home/ultron/protocol_pulse")
RAW_TWEETS_PATH = BASE / "data" / "tweet_study" / "raw_tweets.json"
NOSTR_SIGNAL_DB = BASE / "data" / "nostr_signal.db"
NARRATIVE_CONTEXT_PATH = BASE / "video_pipeline_v3" / "data" / "intelligence" / "narrative_context.json"
OUTPUT_DIR = BASE / "data" / "intelligence"
OUTPUT_PATH = OUTPUT_DIR / "morning_intelligence_brief.json"
LOG_PATH = BASE / "logs" / "morning_brief.log"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Load .env
def load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

logging.basicConfig(
    level=logging.INFO,
    format="[morning_brief] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("morning_brief")


def load_recent_tweets(hours: int = 24) -> list:
    """Load tweets from last N hours from raw_tweets.json."""
    if not RAW_TWEETS_PATH.exists():
        logger.warning("raw_tweets.json not found")
        return []
    try:
        with open(RAW_TWEETS_PATH) as f:
            all_tweets = json.load(f)
    except json.JSONDecodeError:
        # Handle corrupted/appended JSON — use raw_decode to get first valid array
        with open(RAW_TWEETS_PATH) as f:
            raw = f.read()
        try:
            decoder = json.JSONDecoder()
            all_tweets, _ = decoder.raw_decode(raw)
            logger.warning(f"raw_tweets.json had extra data, recovered {len(all_tweets)} tweets")
        except json.JSONDecodeError:
            logger.error("raw_tweets.json is corrupt beyond recovery")
            return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    for t in all_tweets:
        try:
            ts_str = t.get("created_at", "").replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts > cutoff:
                recent.append(t)
        except Exception:
            continue
    logger.info(f"Loaded {len(recent)} tweets from last {hours}h")
    return recent


def load_nostr_signals(hours: int = 24) -> list:
    """Load recent signals from nostr_signal.db."""
    if not NOSTR_SIGNAL_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(NOSTR_SIGNAL_DB))
        c = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        c.execute(
            "SELECT og_name, content, classification, created_at FROM signals "
            "WHERE created_at > ? ORDER BY created_at DESC LIMIT 50",
            (cutoff,),
        )
        rows = c.fetchall()
        conn.close()
        signals = [
            {"name": r[0], "content": r[1], "classification": r[2], "created_at": r[3]}
            for r in rows
        ]
        logger.info(f"Loaded {len(signals)} nostr signals")
        return signals
    except Exception as e:
        logger.warning(f"Nostr DB error: {e}")
        return []


def _load_kol_digest_for_prompt() -> str:
    """Load KOL transcript digest for morning brief prompt context."""
    try:
        digest_path = BASE / "data" / "intelligence" / "kol_transcript_digest.json"
        if not digest_path.exists():
            return "No KOL transcript data available."
        data = json.loads(digest_path.read_text())
        parts = []
        if data.get("summary"):
            parts.append(f"Summary: {data['summary']}")
        if data.get("dominant_sentiment"):
            parts.append(f"Dominant sentiment: {data['dominant_sentiment']} (avg score: {data.get('avg_sentiment_score', 50)}/100)")
        for t in data.get("trending_themes", [])[:5]:
            parts.append(f"- {t['topic']}: discussed by {t['creator_count']} creators (avg {t['avg_sentiment_score']}/100)")
        for c in data.get("top_creators", [])[:3]:
            parts.append(f"- {c['channel']}: {c.get('thesis', 'N/A')[:100]}")
        return "\n".join(parts) if parts else "No KOL transcript data available."
    except Exception:
        return "KOL transcript digest unavailable."


def load_narrative_context() -> dict:
    """Load existing narrative context if available."""
    if not NARRATIVE_CONTEXT_PATH.exists():
        return {}
    try:
        with open(NARRATIVE_CONTEXT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}



def load_sovereign_context() -> dict:
    """Load sovereign_context/latest.json for rich signal data."""
    ctx_path = BASE / "data" / "sovereign_context" / "latest.json"
    if not ctx_path.exists():
        return {}
    try:
        with open(ctx_path) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"sovereign_context load failed: {e}")
        return {}

def load_bitcoin_price() -> dict:
    """Fetch current BTC price + FNG from CoinGecko."""
    result = {"price": "N/A", "change_24h": "N/A", "fng": "N/A"}
    # Try sovereign_context first (always fresh, updated every 5 min)
    try:
        ctx = load_sovereign_context()
        btc = ctx.get("btc", {})
        fg = ctx.get("fear_greed", {})
        if btc.get("price"):
            result["price"] = f"${btc['price']:,.0f}"
            result["change_24h"] = f"{btc.get('change_24h', 0):+.1f}%"
        if fg.get("value"):
            result["fng"] = fg.get("label", "Unknown")
            result["fng_score"] = fg.get("value", "?")
        if result["price"] != "N/A":
            return result  # sovereign_context had data
    except Exception:
        pass  # Fall through to CoinGecko
    try:
        req = urllib.request.Request(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read())
        result["price"] = f"${data['bitcoin']['usd']:,.0f}"
        result["change_24h"] = f"{data['bitcoin']['usd_24h_change']:.2f}%"
    except Exception as e:
        logger.debug(f"Price fetch failed: {e}")
    try:
        req2 = urllib.request.Request(
            "https://api.alternative.me/fng/",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp2 = urllib.request.urlopen(req2, timeout=8)
        fng_data = json.loads(resp2.read())
        result["fng"] = fng_data["data"][0]["value_classification"]
        result["fng_score"] = fng_data["data"][0]["value"]
    except Exception as e:
        logger.debug(f"FNG fetch failed: {e}")
    return result


def build_prompt(tweets: list, nostr: list, price_data: dict, narrative_ctx: dict) -> str:
    """Build the prompt for Claude Haiku."""
    # Format tweets for context (top 60 by priority, truncated)
    tweet_lines = []
    for t in tweets[:60]:
        handle = t.get("handle", "?")
        text = t.get("text", "")[:200]
        tier = t.get("tier", "")
        tweet_lines.append(f"@{handle} [{tier}]: {text}")
    tweet_block = "\n".join(tweet_lines) if tweet_lines else "No recent tweets available."

    # Format nostr signals
    nostr_lines = []
    for s in nostr[:20]:
        nostr_lines.append(f"{s.get('name','?')}: {str(s.get('content',''))[:150]}")
    nostr_block = "\n".join(nostr_lines) if nostr_lines else "No nostr signals."

    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    return f"""You are the intelligence analyst for Protocol Pulse — an autonomous Bitcoin intelligence platform with a cypherpunk voice. Analyze today's Bitcoin community signals and produce a structured intelligence brief.

TODAY: {today}
BTC PRICE: {price_data.get('price', 'N/A')} ({price_data.get('change_24h', 'N/A')} 24h)
FEAR & GREED INDEX: {price_data.get('fng', 'N/A')} ({price_data.get('fng_score', '?')}/100)

RECENT TWEETS FROM BITCOIN THOUGHT LEADERS (last 24h):
{tweet_block}

NOSTR SIGNALS (last 24h):
{nostr_block}

KOL VIDEO TRANSCRIPT INTELLIGENCE (what Bitcoin creators are saying):
{_load_kol_digest_for_prompt()}

Based on this data, produce a JSON intelligence brief with EXACTLY this structure (respond with valid JSON only, no markdown, no preamble):
{{
  "generated_at": "<ISO timestamp>",
  "date": "{today}",
  "btc_price": "{price_data.get('price', 'N/A')}",
  "btc_change_24h": "{price_data.get('change_24h', 'N/A')}",
  "fng": "{price_data.get('fng', 'N/A')}",
  "dominant_narratives": ["<narrative 1>", "<narrative 2>", "<narrative 3>"],
  "trending_language": ["<actual phrase resonating today>", "<phrase 2>", "<phrase 3>"],
  "sentiment": "<bullish|bearish|uncertain>",
  "sentiment_reasoning": "<1-2 sentence explanation>",
  "top_accounts_active": ["<handle1>", "<handle2>", "<handle3>"],
  "recommended_tweet_angles": [
    "<specific angle 1 — based on what's trending today>",
    "<specific angle 2>",
    "<specific angle 3>"
  ],
  "topics_to_avoid": ["<topic to avoid today>"],
  "engagement_patterns": "<what language/format/tone is getting traction today>",
  "protocol_pulse_voice_guidance": "<how PP should sound today — specific, data-backed, cypherpunk>",
  "key_stats_today": {{
    "tweets_analyzed": {len(tweets)},
    "nostr_signals": {len(nostr)},
    "unique_handles": {len(set(t.get('handle','') for t in tweets))}
  }}
}}"""


def call_local_llm(prompt: str) -> dict:
    """Call local Qwen3 via Ollama. Returns parsed brief dict or empty dict."""
    import requests
    try:
        resp = requests.post("http://localhost:11435/api/chat", json={
            "model": "qwen3-coder:30b",
            "messages": [
                {"role": "system", "content": "You are a Bitcoin intelligence analyst. Return ONLY valid JSON. No markdown. No preamble. No explanation."},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.3}
        }, timeout=60)
        resp.raise_for_status()
        raw = resp.json().get("message", {}).get("content", "")
        raw = raw.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        result = json.loads(raw.strip())
        logger.info("Brief generated via LOCAL LLM")
        return result
    except Exception as e:
        logger.warning(f"Local LLM brief failed: {e}")
        return {}


def call_claude_haiku(prompt: str) -> dict:
    """Call Claude Haiku via Anthropic API."""
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return {}

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "User-Agent": "ProtocolPulse/1.0",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        content = data.get("content", [{}])[0].get("text", "")
        # Strip markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rsplit("```", 1)[0].strip()
        return json.loads(content)
    except Exception as e:
        logger.error(f"Claude Haiku call failed: {e}")
        return {}


def call_gemini(prompt: str) -> dict:
    """Call Gemini 2.5 Flash via Google API — fallback when Anthropic is down."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if not gemini_key:
        logger.warning("GEMINI_API_KEY not set — skipping Gemini fallback")
        return {}
    try:
        system = "You are a Bitcoin intelligence analyst. Return ONLY valid JSON. No markdown. No preamble. No explanation."
        payload = json.dumps({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.3},
        }).encode()
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Strip markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        result = json.loads(raw.strip())
        logger.info("Brief generated via GEMINI fallback")
        return result
    except Exception as e:
        logger.error(f"Gemini fallback failed: {e}")
        return {}


def main():
    logger.info("=" * 60)
    logger.info("Morning Intelligence Brief generating")
    logger.info("=" * 60)

    # Load all signals
    tweets = load_recent_tweets(hours=24)
    nostr_signals = load_nostr_signals(hours=24)
    narrative_ctx = load_narrative_context()
    price_data = load_bitcoin_price()

    logger.info(
        f"Signals: {len(tweets)} tweets, {len(nostr_signals)} nostr, "
        f"BTC={price_data.get('price','?')}"
    )

    if not tweets and not nostr_signals:
        logger.warning("No signal data available -- enriching from sovereign_context")
        ctx = load_sovereign_context()
        if ctx:
            net = ctx.get("network", {})
            opts = ctx.get("options", {})
            futures = ctx.get("futures", {})
            onchain = ctx.get("on_chain", {})
            tweets = []
            if net.get("hashrate_eh"):
                tweets.append({"text": f"Bitcoin hashrate at {net['hashrate_eh']} EH/s", "handle": "mempool_space"})
            if opts.get("put_call_ratio"):
                tweets.append({"text": f"Options P/C ratio: {opts['put_call_ratio']:.2f}, DVOL: {opts.get('dvol', 'N/A')}", "handle": "deribit"})
            if futures.get("funding_rate") is not None:
                tweets.append({"text": f"Funding: {futures['funding_rate']:.6f}, OI: {futures.get('open_interest', 0):,.0f} BTC", "handle": "binance"})
            if onchain.get("active_addresses_7d"):
                tweets.append({"text": f"Active addresses 7d: {onchain['active_addresses_7d']:,.0f}, NVT: {onchain.get('nvt_ratio', 'N/A')}", "handle": "blockchain"})
            logger.info(f"Enriched with {len(tweets)} sovereign_context signals")
        else:
            tweets = []

    # Build prompt
    prompt = build_prompt(tweets, nostr_signals, price_data, narrative_ctx)

    # Try local LLM first
    logger.info("Calling local Qwen3...")
    brief = call_local_llm(prompt)
    _model_used = "local_llm"

    # Validate required fields
    required = ["dominant_narratives", "trending_language", "sentiment", "recommended_tweet_angles"]
    if not brief or not all(k in brief for k in required):
        logger.warning("Local brief incomplete, falling back to Claude Haiku")
        brief = call_claude_haiku(prompt)
        _model_used = "claude_haiku"

    # Gemini fallback if Haiku also failed
    if not brief or not all(k in brief for k in required):
        logger.warning("Haiku failed/incomplete, falling back to Gemini 2.5 Flash")
        brief = call_gemini(prompt)
        _model_used = "gemini_fallback"

    # Tag which model generated it
    if brief:
        brief["generated_by"] = _model_used

    if not brief:
        logger.error("All LLM providers failed (Qwen + Haiku + Gemini)")
        # Write a minimal fallback brief
        brief = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": "All LLM calls failed",
            "btc_price": price_data.get("price", "N/A"),
            "sentiment": "uncertain",
            "generated_by": "fallback",
        }

    # Ensure timestamp
    brief.setdefault("generated_at", datetime.now(timezone.utc).isoformat())

    # Write output
    tmp = OUTPUT_PATH.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    tmp.replace(OUTPUT_PATH)

    logger.info(f"Brief written to {OUTPUT_PATH}")
    logger.info(f"Sentiment: {brief.get('sentiment', '?')}")
    logger.info(f"Narratives: {brief.get('dominant_narratives', [])}")


if __name__ == "__main__":
    main()

