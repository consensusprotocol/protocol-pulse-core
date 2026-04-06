#!/usr/bin/env python3
"""
tweet_machine.py — Protocol Pulse Social Intelligence Engine
Phase 4: Sentiment mirroring, format diversity, data-driven tweets, PBX voice

Runs at 6:30am ET daily (and optionally at 14:00 UTC, 01:00 UTC).
Uses morning_intelligence_brief.json + thought leader sentiment + live BTC data
to generate signal-dense tweets. Posts via X API v2 write if credentials exist,
otherwise queues to pending_tweets.json for manual review.

Voice: PBX — a cynical, brilliant analyst who has watched fiat systems
corrode for a decade. Austrian economics lens. Dry wit. Zero fluff.
"""

import json
import re
import logging
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path("/home/ultron/protocol_pulse")
BRIEF_PATH = BASE / "data" / "intelligence" / "morning_intelligence_brief.json"
QUEUE_PATH = BASE / "data" / "social_queue" / "pending_tweets.json"
LOG_PATH = BASE / "logs" / "tweet_machine.log"
SOVEREIGN_DB = BASE / "data" / "sovereign_intel.db"

QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
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
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "")
X_API_KEY = os.environ.get("X_API_KEY", os.environ.get("X_CONSUMER_KEY", ""))
X_API_SECRET = os.environ.get("X_API_SECRET", os.environ.get("X_CONSUMER_SECRET", ""))

logging.basicConfig(
    level=logging.INFO,
    format="[tweet_machine] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("tweet_machine")

CAN_POST = bool(X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET and X_API_KEY and X_API_SECRET)

# ── Thought Leader Accounts for Sentiment Mirroring ──────────────────────────
THOUGHT_LEADERS = [
    "PrestonPysh",
    "LynAldenContact",
    "Breedlove22",
    "MartyBent",
    "TFTC21",
    "American_HODL",
    "daborado",        # Dylan LeClair
    "nic__carter",
]

# Evergreen fallback themes when sentiment radar has no data
EVERGREEN_THEMES = [
    "Fiat debasement accelerating globally",
    "Self-custody as sovereignty in a surveillance state",
    "Bitcoin network fundamentals strengthening silently",
]

# ── Tweet Format Templates ───────────────────────────────────────────────────
# Each format constrains the LLM to produce a structurally distinct tweet.
TWEET_FORMATS = {
    "on_chain_signal": {
        "label": "ON-CHAIN SIGNAL",
        "instruction": (
            "Write a tweet anchored to a SPECIFIC on-chain metric or network stat "
            "(hashrate, mempool fees, exchange outflows, UTXO age, coin days destroyed, etc). "
            "State the metric, then deliver one sharp implication. "
            "The metric must come from the data context provided. Never invent numbers."
        ),
        "example": "90-day Coin Days Destroyed at a 5-year low. Old hands are not selling. They are waiting for something bigger than a new price high",
    },
    "historical_parallel": {
        "label": "HISTORICAL PARALLEL",
        "instruction": (
            "Frame a current Bitcoin or macro event within a HISTORICAL context. "
            "Reference a specific date, regime, economic episode, or monetary failure from history. "
            "Draw the parallel to today. Austrian economics lens preferred. "
            "Make the reader see the pattern."
        ),
        "example": "Diocletian's Edict on Maximum Prices failed to stop Roman inflation in 301 AD. Price controls on energy are the same policy with a different toga",
    },
    "fiat_failure": {
        "label": "FIAT FAILURE SNAPSHOT",
        "instruction": (
            "Contrast a SPECIFIC fiat system failure (debt level, money printing stat, "
            "currency collapse, central bank action) against Bitcoin's properties. "
            "Format: shocking fiat fact, dry-wit observation, Bitcoin as the punchline. "
            "Use real data from the brief or public knowledge. The gap between what "
            "institutions say and what they do is your hunting ground."
        ),
        "example": "Powell says inflation is transitory. The Fed's balance sheet quietly expands by $50B this week. The denominator is the signal",
    },
    "socratic_question": {
        "label": "SOCRATIC QUESTION",
        "instruction": (
            "Ask ONE genuinely uncomfortable question that forces the reader to confront "
            "a first principle about money, sovereignty, or state power. "
            "The question must be impossible to ignore and have no easy answer. "
            "Do NOT answer it yourself. Let it hang."
        ),
        "example": "If your bank can freeze your funds on a government request, at what point did you stop owning your money",
    },
    "brief_signal": {
        "label": "INTELLIGENCE BRIEF SIGNAL",
        "instruction": (
            "Pick the single highest-signal angle from today's intelligence brief. "
            "Lead with a specific data point. One observation, one implication, one landing. "
            "This is the classic Protocol Pulse format."
        ),
        "example": "Strategy acquired BTC again. No press conference. No explanation needed",
    },
    "community_narrative": {
        "label": "COMMUNITY NARRATIVE RESPONSE",
        "instruction": (
            "The Bitcoin community is currently discussing the themes listed in COMMUNITY NARRATIVES. "
            "Pick one theme and deliver a CONTRARIAN or deeper-level insight that the community "
            "hasn't considered. Do NOT agree with the mainstream take. Find the angle everyone missed. "
            "You are responding to the zeitgeist, not repeating it."
        ),
        "example": "Everyone wants the government to provide clarity on Bitcoin. What if the entire point of Bitcoin is that it doesn't need external clarity",
    },

"direct_engagement_question": {
        "label": "DIRECT ENGAGEMENT QUESTION",
        "instruction": (
            "Ask ONE direct question about Bitcoin, money, or financial sovereignty. "
            "Start with: Who else, What do, Why do, How many, Do you. "
            "Make it personal. Make the reader feel compelled to answer. "
            "Keep it under 140 chars. No preamble. Just the question."
        ),
        "example": "What would you actually do if your bank froze your account tomorrow",
    },
"contrarian_observation": {
        "label": "CONTRARIAN OBSERVATION",
        "instruction": (
            "Make a bold, slightly controversial observation about Bitcoin or the financial system "
            "that splits opinion. Use a declarative statement that forces people to pick sides. "
            "Must be defensible but uncomfortable. One line, dry delivery."
        ),
        "example": "Most Bitcoin influencers would sell their entire stack at 500k. The conviction is performance art",
    },

}

# ── PBX Voice (strengthened persona) ─────────────────────────────────────────
PBX_PERSONA = """PERSONA DIRECTIVE (apply before all other instructions):
You are a ghost analyst inside Protocol Pulse. You have watched fiat monetary systems
corrode for over a decade. Your worldview is shaped by the Austrian School of Economics:
you see time preference, malinvestment, and the Cantillon Effect in every headline.

Your tone is dry, understated, and contains a hint of gallows humor about the state
of the fiat world. You state observations as fact, without hype or emotion.
You prefer to expose flaws in logic rather than make breathless declarations.
You respect your audience's intelligence. Never over-explain.

You are NOT a reporter. You are NOT bullish or bearish. You observe the decay of
one monetary system and the emergence of another with the detachment of someone
who has already made their choice.

FORBIDDEN LANGUAGE (hard filter):
- No corporate jargon: leverage, synergy, unpack, deep dive, game-changer
- No breathless hype: revolution, paradigm shift, bullish af, to the moon
- No cliches: now more than ever, in a world where, at the end of the day
- No subjective adjectives: amazing, incredible, exciting, massive
- No hedging: might, could potentially, it remains to be seen
- No first person plural: we believe, our view, we think
"""

TWEET_VOICE_LAWS = """
PROTOCOL PULSE VOICE LAWS (data-derived, March 2026 study):

LAW 1 - LEAD WITH DATA: Numbers in 72% of top tweets vs 57% overall.
  Open with a specific figure or stat. Not a vibe. A number.

LAW 2 - SHORTER WINS: Top 10% average 113 chars. Target under 150. Hard cap 280.
  Every word earns its place.

LAW 3 - NO DASHES OF ANY KIND: No em dashes, no double dashes (--), no hyphens used as pauses.
  Let sentence structure carry the rhythm. Punctuation is a crutch.

LAW 4 - ASK QUESTIONS SURGICALLY: 8% of top tweets. Genuinely uncomfortable to ignore.

LAW 5 - NO EMOJI. No exclamation marks. No trailing period. No dashes of any kind.

LAW 6 - ORIGINAL TAKES ONLY: 84% of top tweets are original positions, not reactions.

LAW 7 - ONE CLEAN IDEA: Max 3 sentences. One observation, one implication, one landing.

IDENTITY LAWS (override everything):

BITCOIN ONLY: Protocol Pulse is a Bitcoin platform. Not crypto. Not web3. Not DeFi.
  Bitcoin is a monetary protocol. Everything else is noise.
  Never cover: altcoins, stablecoins, Ethereum, Solana, NFTs, DeFi, or broad crypto markets.

CYPHERPUNK ETHOS: Our lens is sovereignty, privacy, sound money, and freedom from
  institutional and state control. We are not a mainstream finance outlet.
  We do not celebrate stablecoin bills, ETF approvals, or institutional on-ramps as victories.
  We observe them as signals about where power is moving and where it isnt.

NEVER USE THESE ANGLES:
  - Stablecoin legislation or stablecoin yield
  - Altcoin or broad crypto price action
  - Regulatory clarity framed as a Bitcoin win
  - Government approval as validation
  - Institutional adoption cheerleading
  - Mainstream crypto sentiment

PREFERRED ANGLES:
  - Bitcoin as hard money vs fiat debasement
  - Sovereignty, self-custody, censorship resistance
  - Macro signals that reveal WHY Bitcoin exists
  - Mining, hashrate, network fundamentals
  - Geopolitical and monetary system stress
  - What central banks and governments are doing wrong
  - Financial privacy and freedom of transaction
  - The gap between what institutions say and what they do
"""

# ── Prompt Template (format-aware) ───────────────────────────────────────────
TWEET_GENERATION_PROMPT = """{persona}

You are the tweet writer for Protocol Pulse, an autonomous Bitcoin intelligence platform.

Generate exactly 1 tweet for @ProtocolPulseHQ.

FORMAT DIRECTIVE — you MUST write in this format:
[{format_label}]
{format_instruction}

EXAMPLE of this format's voice:
"{format_example}"

CRITICAL — ANGLE DIVERSITY LAW:
The recently posted tweets below represent USED angles. You MUST pick a completely
different angle, different data point, and different framing. Never rephrase a posted tweet.
If today's brief only has one story, find a different dimension of it (different stat, different
implication, different audience insight). Repetition destroys credibility.

INTELLIGENCE BRIEF:
{brief_text}

{community_narratives}

{live_data}

VOICE LAWS (mandatory):
{voice_laws}

HARD RULES:
- Never start with: Just, Hot take, Thread:, GM, Attention, Breaking, We, Bitcoin is
- Never use exclamation marks
- Never end with a period
- No hashtags
- No emoji
- No em dashes (the long dash)
- No double dashes (--)
- No dashes used as pauses or separators of any kind
- No ellipsis (...)
- Every number must be real. Never invent statistics.

EXAMPLES OF THE RIGHT VOICE:
- "Capitalism started in 1602 with the world's first stock exchange. It died in 2026 with the first unrealized gains tax. Neofeudalism arrived quietly"
- "Strategy acquired BTC again. No press conference. No explanation needed"
- "Remember all the talk of auditing the gold reserves in Fort Knox last year?"
- "The Fed is now aggressively hiking rates to fix the problem they aggressively created by printing money. The cure is the poison"
- "On chain transaction volume dropped 34% while price held. Either accumulation is silent or conviction is cracking"

Respond with a JSON object only. No markdown. No preamble:
{{"text": "<tweet, max 280 chars, no trailing period, no emoji, no hashtags>", "angle": "<angle_category>", "type": "<stat|observation|question|signal>", "format": "{format_key}", "char_count": 0}}"""


# ── Sentiment Mirroring: Thought Leader Theme Scraping ───────────────────────

def fetch_thought_leader_themes() -> list[str]:
    """Scrape trending themes from top Bitcoin thought leaders.

    Uses the morning brief's dominant_narratives and trending_language as primary
    signal (already derived from tweet study + nostr). Falls back to evergreen
    themes if no fresh data available.
    """
    themes = []

    # Primary source: morning brief already contains community narrative analysis
    try:
        if BRIEF_PATH.exists():
            with open(BRIEF_PATH) as f:
                brief = json.load(f)
            narratives = brief.get("dominant_narratives", [])
            trending = brief.get("trending_language", [])
            top_accounts = brief.get("top_accounts_active", [])
            if narratives:
                themes.extend(narratives[:3])
            if trending:
                themes.append(f"Trending language: {', '.join(trending[:5])}")
            if top_accounts:
                themes.append(f"Active voices: {', '.join(top_accounts[:3])}")
    except Exception as e:
        logger.warning(f"Could not load brief for sentiment: {e}")

    # Secondary source: check sovereign_intel.db for stored narrative signals
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emerging_narratives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                source_account TEXT,
                engagement_score REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        rows = conn.execute(
            "SELECT theme FROM emerging_narratives WHERE created_at > ? ORDER BY engagement_score DESC LIMIT 5",
            (cutoff,)
        ).fetchall()
        conn.close()
        if rows:
            themes.extend([r[0] for r in rows])
    except Exception as e:
        logger.warning(f"Could not query emerging_narratives: {e}")

    if not themes:
        logger.info("No fresh sentiment data, using evergreen themes")
        return EVERGREEN_THEMES

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in themes:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)
    return unique[:5]


def store_narrative(theme: str, source: str = "brief", score: float = 0.0) -> None:
    """Write a detected narrative theme to sovereign_intel.db for tracking."""
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emerging_narratives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                source_account TEXT,
                engagement_score REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "INSERT INTO emerging_narratives (theme, source_account, engagement_score, created_at) VALUES (?,?,?,?)",
            (theme, source, score, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to store narrative: {e}")


# ── Live Bitcoin Data Feed ───────────────────────────────────────────────────

def fetch_live_btc_data() -> dict:
    """Fetch real-time BTC network data from mempool.space + alternative.me."""
    data = {}

    # mempool.space: fees, block height
    try:
        req = urllib.request.Request(
            "https://mempool.space/api/v1/fees/recommended",
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        fees = json.loads(resp.read())
        data["fee_fastest"] = fees.get("fastestFee", 0)
        data["fee_hour"] = fees.get("hourFee", 0)
    except Exception as e:
        logger.warning(f"mempool fees fetch failed: {e}")

    # mempool.space: block height + hashrate
    try:
        req = urllib.request.Request(
            "https://mempool.space/api/blocks/tip/height",
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data["block_height"] = int(resp.read().decode().strip())
    except Exception as e:
        logger.warning(f"block height fetch failed: {e}")

    try:
        req = urllib.request.Request(
            "https://mempool.space/api/v1/mining/hashrate/3d",
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        hr_data = json.loads(resp.read())
        if hr_data.get("hashrates"):
            latest = hr_data["hashrates"][-1]
            data["hashrate_eh"] = round(latest.get("avgHashrate", 0) / 1e18, 1)
    except Exception as e:
        logger.warning(f"hashrate fetch failed: {e}")

    # Fear & Greed
    try:
        req = urllib.request.Request(
            "https://api.alternative.me/fng/?limit=1",
            headers={"User-Agent": "ProtocolPulse/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        fng = json.loads(resp.read())
        if fng.get("data"):
            data["fng_score"] = int(fng["data"][0].get("value", 50))
            data["fng_label"] = fng["data"][0].get("value_classification", "Neutral")
    except Exception as e:
        logger.warning(f"FNG fetch failed: {e}")

    return data


def format_live_data(data: dict) -> str:
    """Format live BTC data as context block for the LLM prompt."""
    if not data:
        return ""

    lines = ["LIVE BITCOIN NETWORK DATA (real-time, use these numbers):"]
    if "block_height" in data:
        lines.append(f"  Block Height: {data['block_height']:,}")
    if "hashrate_eh" in data:
        lines.append(f"  Hashrate (3d avg): {data['hashrate_eh']} EH/s")
    if "fee_fastest" in data:
        lines.append(f"  Fastest Fee: {data['fee_fastest']} sat/vB")
    if "fee_hour" in data:
        lines.append(f"  1-Hour Fee: {data['fee_hour']} sat/vB")
    if "fng_score" in data:
        lines.append(f"  Fear & Greed: {data['fng_score']} ({data.get('fng_label', '?')})")

    return "\n".join(lines)


# ── Format Rotation ──────────────────────────────────────────────────────────

def get_last_formats_used(n: int = 3) -> list[str]:
    """Return the last N format keys used, to enforce rotation."""
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auto_tweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_text TEXT NOT NULL,
                tweet_type TEXT DEFAULT 'generated',
                angle TEXT,
                status TEXT DEFAULT 'pending',
                x_tweet_id TEXT,
                generated_at TEXT,
                posted_at TEXT,
                sentiment TEXT,
                brief_date TEXT,
                format_used TEXT,
                narratives_used TEXT,
                data_injected INTEGER DEFAULT 0
            )
        """)
        rows = conn.execute(
            "SELECT format_used FROM auto_tweet WHERE format_used IS NOT NULL ORDER BY id DESC LIMIT ?",
            (n,)
        ).fetchall()
        conn.close()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        logger.warning(f"Could not fetch last formats: {e}")
        return []


def pick_format(brief: dict, themes: list[str]) -> str:
    """Pick the next tweet format, enforcing no repeat within last 3 posts."""
    recent = get_last_formats_used(3)
    available = [k for k in TWEET_FORMATS if k not in recent]

    if not available:
        available = list(TWEET_FORMATS.keys())

    # Prefer community_narrative if we have fresh themes
    if themes and themes != EVERGREEN_THEMES and "community_narrative" in available:
        return "community_narrative"

    # Prefer on_chain_signal if brief has strong data
    if brief.get("fng") and "on_chain_signal" in available:
        return "on_chain_signal"

    # Prefer fiat_failure if sentiment is bearish
    if brief.get("sentiment") == "bearish" and "fiat_failure" in available:
        return "fiat_failure"

    # Default: first available
    return available[0]


# ── JSON Extraction (robust) ─────────────────────────────────────────────────

def extract_json(raw: str) -> dict:
    """Robustly extract JSON from LLM response, handling markdown fences."""
    raw = raw.strip()
    # Stage 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Stage 2: strip markdown fences
    if raw.startswith("```"):
        inner = raw.split("```", 2)[1]
        if inner.startswith("json"):
            inner = inner[4:]
        inner = inner.rsplit("```", 1)[0].strip()
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            pass
    # Stage 3: regex extract first JSON object
    match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Stage 4: greedy regex
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Stage 5: truncated JSON — extract "text" field value via regex
    # Gemini 2.5 Flash often returns {"text": "..."} but truncates before closing brace
    text_match = re.search(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)', raw)
    if text_match:
        extracted_text = text_match.group(1)
        # Trim to 280 chars and clean trailing incomplete words
        if len(extracted_text) > 280:
            extracted_text = extracted_text[:277].rsplit(" ", 1)[0]
        logger.warning(f"Recovered tweet text from truncated JSON ({len(extracted_text)} chars)")
        return {"text": extracted_text, "angle": "recovered", "type": "observation", "format": "recovered"}
    # Stage 6: plain text response (no JSON at all) — accept as tweet
    cleaned = raw.strip().strip('"').strip()
    if 20 <= len(cleaned) <= 300 and "{" not in cleaned:
        logger.warning(f"Accepting plain text as tweet ({len(cleaned)} chars)")
        return {"text": cleaned, "angle": "plain", "type": "observation", "format": "plain"}
    logger.error(f"No valid JSON in LLM response: {raw[:200]}")
    raise ValueError(f"No valid JSON found in LLM response")


# ── Core Functions ───────────────────────────────────────────────────────────

def load_brief() -> dict:
    """Load morning intelligence brief."""
    if not BRIEF_PATH.exists():
        logger.error(f"Brief not found: {BRIEF_PATH}")
        logger.error("Run morning_brief.py first.")
        return {}
    age_hours = (
        datetime.now().timestamp() - BRIEF_PATH.stat().st_mtime
    ) / 3600
    if age_hours > 12:
        logger.warning(f"Brief is {age_hours:.1f}h old — may be stale")
    with open(BRIEF_PATH) as f:
        return json.load(f)


def get_todays_posted_tweets() -> list[str]:
    """Fetch tweet texts already posted in last 48h to avoid repeats.

    Sources checked (in order):
    1. x_post_ledger.db (global gate — authoritative, all posting paths log here)
    2. sovereign_intel.db auto_tweet table (tweet_machine's own log)
    """
    texts = []
    cutoff_48h = (datetime.now(timezone.utc) - timedelta(hours=28)).isoformat()

    # Source 1: global gate ledger (most reliable — every posting path writes here)
    try:
        ledger_db = BASE / "data" / "x_post_ledger.db"
        if ledger_db.exists():
            conn = sqlite3.connect(str(ledger_db))
            rows = conn.execute(
                "SELECT tweet_text FROM x_post_ledger WHERE posted_at >= ? AND allowed = 1 ORDER BY posted_at DESC LIMIT 20",
                (cutoff_48h,)
            ).fetchall()
            conn.close()
            texts.extend(r[0] for r in rows if r[0])
    except Exception as e:
        logger.warning(f"Could not fetch from x_post_ledger: {e}")

    # Source 2: tweet_machine's own log in sovereign_intel.db
    try:
        if SOVEREIGN_DB.exists():
            conn = sqlite3.connect(str(SOVEREIGN_DB))
            rows = conn.execute(
                "SELECT tweet_text FROM auto_tweet WHERE posted_at >= ? ORDER BY posted_at DESC LIMIT 20",
                (cutoff_48h,)
            ).fetchall()
            conn.close()
            texts.extend(r[0] for r in rows if r[0])
    except Exception as e:
        logger.warning(f"Could not fetch from sovereign_intel auto_tweet: {e}")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def _keyword_overlap(text_a: str, text_b: str) -> float:
    """Return fraction of significant words shared between two tweets."""
    stop = {"the","a","an","is","are","was","were","and","or","but","in","on","at","to","of","for","with","this","that","it","as","by"}
    def words(t): return set(w.lower() for w in re.findall(r"\w+", t) if w.lower() not in stop and len(w) > 3)
    wa, wb = words(text_a), words(text_b)
    if not wa or not wb: return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def is_too_similar(new_tweet: str, posted: list[str], threshold: float = 0.65) -> bool:
    """Return True if new_tweet overlaps too much with any recently posted tweet."""
    for old in posted:
        if _keyword_overlap(new_tweet, old) >= threshold:
            logger.warning(f"DEDUP blocked — {_keyword_overlap(new_tweet, old):.0%} overlap with: {old[:60]}")
            return True
    return False


def _call_llm_with_fallback(prompt: str) -> str:
    """Call LLM with Anthropic → Gemini → Grok fallback chain. Returns raw text."""
    # 1. Anthropic Haiku (primary)
    if ANTHROPIC_API_KEY:
        try:
            payload = {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            content = data.get("content", [{}])[0].get("text", "").strip()
            if content:
                logger.info("Tweet generated via Anthropic Haiku")
                return content
        except Exception as e:
            logger.warning(f"Anthropic Haiku failed: {e}")

    # 2. Gemini 2.5 Flash (fallback)
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            gpayload = json.dumps({
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.7},
            }).encode()
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                data=gpayload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            parts = data["candidates"][0]["content"]["parts"]
            # Use last non-thought part (gemini-2.5 includes thinking parts first)
            content = ""
            for p in reversed(parts):
                if not p.get("thought") and p.get("text"):
                    content = p["text"].strip()
                    break
            if content:
                logger.info("Tweet generated via Gemini fallback (Anthropic credits depleted)")
                return content
        except Exception as e:
            logger.warning(f"Gemini fallback failed: {e}")

    # 3. Grok/xAI (fallback)
    xai_key = os.environ.get("XAI_API_KEY", "")
    if xai_key:
        try:
            gpayload = json.dumps({
                "model": "grok-3-mini-fast",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.7,
            }).encode()
            req = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=gpayload,
                headers={
                    "Authorization": f"Bearer {xai_key}",
                    "Content-Type": "application/json",
                },
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"].strip()
            if content:
                logger.info("Tweet generated via Grok/xAI fallback")
                return content
        except Exception as e:
            logger.warning(f"Grok fallback failed: {e}")

    return ""


def generate_tweets(brief: dict, count: int = 1) -> list:
    """Call LLM to generate tweets from the brief with format diversity."""
    if not ANTHROPIC_API_KEY and not os.environ.get("GEMINI_API_KEY") and not os.environ.get("XAI_API_KEY"):
        logger.error("No LLM API keys available (ANTHROPIC, GEMINI, XAI)")
        return []

    brief_text = json.dumps(brief, indent=2)[:3000]
    posted_today = get_todays_posted_tweets()
    used_context = ""
    if posted_today:
        used_context = "\nALREADY POSTED TODAY - pick a DIFFERENT angle:\n"
        used_context += "\n".join("- " + t[:100] for t in posted_today)

    # Concept dedup: tell the LLM which concepts are banned
    banned_concepts_context = ""
    try:
        sys.path.insert(0, str(BASE))
        from services.x_service import get_banned_concepts
        banned = get_banned_concepts(hours=24)
        if banned:
            banned_concepts_context = (
                "\n\nBANNED CONCEPTS (do NOT use these — already posted in last 72h):\n"
                + "\n".join(f"  - {c.replace('_', ' ')}" for c in banned)
                + "\nPick a concept NOT on this list. Genuinely different angle."
            )
    except Exception as e:
        logger.warning(f"Could not load banned concepts: {e}")

    # Angle diversity: tell the LLM which categories are available
    available_angles_context = ""
    try:
        from services.x_service import get_available_angles, ANGLE_CATEGORIES
        available = get_available_angles()
        if available:
            available_angles_context = (
                "\n\nANGLE CATEGORY ENFORCEMENT: You MUST pick one of these unused categories for today's tweet. "
                "Return it in the 'angle' field of your JSON response.\n"
                f"Available categories: {', '.join(available)}\n"
                f"All categories: {', '.join(ANGLE_CATEGORIES)}"
            )
        else:
            logger.warning("All angle categories used today — no available angles")
    except Exception as e:
        logger.warning(f"Could not load angle categories: {e}")

    # Sentiment mirroring: fetch thought leader themes
    themes = fetch_thought_leader_themes()
    community_block = ""
    if themes:
        community_block = (
            "COMMUNITY NARRATIVES (what the Bitcoin community is discussing right now):\n"
            + "\n".join(f"  - {t}" for t in themes)
            + "\nUse these as awareness context. Find a contrarian or deeper angle, not a copy."
        )
        logger.info(f"Injected {len(themes)} community themes into prompt")

    # Live BTC data
    live_data = fetch_live_btc_data()
    live_block = format_live_data(live_data)
    if live_block:
        logger.info(f"Injected live BTC data: {list(live_data.keys())}")

    # Pick format
    fmt_key = pick_format(brief, themes)
    fmt = TWEET_FORMATS[fmt_key]
    logger.info(f"Selected format: [{fmt['label']}] ({fmt_key})")

    # Store detected narratives for analytics
    for t in themes[:3]:
        store_narrative(t, source="brief_themes")

    prompt = TWEET_GENERATION_PROMPT.format(
        persona=PBX_PERSONA,
        format_label=fmt["label"],
        format_instruction=fmt["instruction"],
        format_example=fmt["example"],
        format_key=fmt_key,
        brief_text=brief_text + used_context + banned_concepts_context + available_angles_context,
        community_narratives=community_block,
        live_data=live_block,
        voice_laws=TWEET_VOICE_LAWS,
    )

    content = _call_llm_with_fallback(prompt)
    if not content:
        logger.critical("All LLM providers failed — zero tweets generated")
        return []

    parsed = extract_json(content)
    if isinstance(parsed, dict):
        parsed = [parsed]
    # Tag each tweet with metadata for tracking
    for t in parsed:
        t["format"] = fmt_key
        t["narratives_used"] = themes[:3]
        t["data_injected"] = bool(live_data)
    logger.info(f"Generated {len(parsed)} tweet(s)")
    return parsed


def _strip_hashtags(text: str) -> str:
    """Remove any hashtags from outgoing text. X algorithms penalize them."""
    return re.sub(r" #\w+", "", text).strip()


def post_to_x(tweet_text: str) -> dict:
    """Post a tweet via X API v2 using OAuth 1.0a."""
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
        )
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        logger.info(f"Posted tweet {tweet_id}: {tweet_text[:50]}...")
        return {"success": True, "tweet_id": tweet_id}
    except ImportError:
        logger.error("tweepy not installed — cannot post. Use: pip3 install tweepy")
        return {"success": False, "error": "tweepy not installed"}
    except Exception as e:
        logger.error(f"X API post failed: {e}")
        return {"success": False, "error": str(e)}


def queue_tweet(tweet: dict, brief: dict) -> None:
    """Add tweet to pending_tweets.json queue for manual review."""
    existing = []
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH) as f:
            existing = json.load(f)

    entry = {
        "id": f"tweet_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{tweet.get('priority', 0)}",
        "text": tweet.get("text", ""),
        "angle": tweet.get("angle", ""),
        "type": tweet.get("type", ""),
        "format": tweet.get("format", ""),
        "priority": tweet.get("priority", 3),
        "status": "pending",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brief_date": brief.get("date", ""),
        "sentiment": brief.get("sentiment", ""),
    }

    existing_texts = {e.get("text", "") for e in existing}
    if entry["text"] not in existing_texts:
        existing.append(entry)
        with open(QUEUE_PATH, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        logger.info(f"Queued [{tweet.get('format', '?')}]: {entry['text'][:60]}...")


def log_to_db(tweet: dict, posted: bool, tweet_id: str = None) -> None:
    """Log tweet to sovereign_intel.db auto_tweet table with format tracking."""
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS auto_tweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_text TEXT NOT NULL,
                tweet_type TEXT DEFAULT 'generated',
                angle TEXT,
                status TEXT DEFAULT 'pending',
                x_tweet_id TEXT,
                generated_at TEXT,
                posted_at TEXT,
                sentiment TEXT,
                brief_date TEXT,
                format_used TEXT,
                narratives_used TEXT,
                data_injected INTEGER DEFAULT 0
            )
        """)
        c.execute(
            """INSERT INTO auto_tweet
               (tweet_text, tweet_type, angle, status, x_tweet_id, generated_at, posted_at,
                sentiment, brief_date, format_used, narratives_used, data_injected)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tweet.get("text", ""),
                tweet.get("type", "generated"),
                tweet.get("angle", ""),
                "posted" if posted else "queued",
                tweet_id,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat() if posted else None,
                tweet.get("sentiment", ""),
                tweet.get("brief_date", ""),
                tweet.get("format", ""),
                json.dumps(tweet.get("narratives_used", [])),
                1 if tweet.get("data_injected") else 0,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"DB log failed: {e}")


def prune_stale_queue(max_age_hours: int = 48) -> int:
    """Remove pending tweets older than max_age_hours. Returns count removed."""
    if not QUEUE_PATH.exists():
        return 0
    try:
        with open(QUEUE_PATH) as f:
            queue = json.load(f)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        fresh = []
        for entry in queue:
            gen_at = entry.get("generated_at", "")
            if gen_at:
                try:
                    ts = datetime.fromisoformat(gen_at)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass
            fresh.append(entry)
        removed = len(queue) - len(fresh)
        if removed > 0:
            with open(QUEUE_PATH, "w") as f:
                json.dump(fresh, f, indent=2, ensure_ascii=False)
            logger.info(f"Pruned {removed} stale tweets from pending queue (>{max_age_hours}h old)")
        return removed
    except Exception as e:
        logger.warning(f"Queue prune failed: {e}")
        return 0


def main():
    logger.info("=" * 60)
    logger.info("Tweet Machine v4 starting (sentiment + formats + data)")
    logger.info("=" * 60)

    # Prune stale pending tweets before doing anything
    prune_stale_queue(48)

    if not CAN_POST:
        logger.warning(
            "X write credentials not found in .env — operating in QUEUE mode.\n"
            "Missing: X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_API_KEY, X_API_SECRET\n"
            "Tweets will be written to: " + str(QUEUE_PATH)
        )
    else:
        logger.info("X write credentials found — will auto-post")

    # Load brief
    brief = load_brief()
    if not brief:
        logger.error("Cannot generate tweets without a brief. Exiting.")
        sys.exit(1)

    logger.info(
        f"Brief loaded: {brief.get('date','?')} | "
        f"Sentiment: {brief.get('sentiment','?')} | "
        f"BTC: {brief.get('btc_price','?')}"
    )

    # Generate tweets
    tweets = generate_tweets(brief, count=1)
    if not tweets:
        logger.error("No tweets generated. Exiting.")
        sys.exit(1)

    # Sort by priority
    tweets.sort(key=lambda t: t.get("priority", 5))

    # Post or queue
    posted_count = 0
    queued_count = 0

    for tweet in tweets:
        text = tweet.get("text", "").strip()
        if not text:
            continue
        if len(text) > 280:
            logger.warning(f"Tweet too long ({len(text)} chars), truncating: {text[:50]}...")
            text = text[:277] + "..."
            tweet["text"] = text

        if CAN_POST:
            text = _strip_hashtags(text)  # Hard gate

            # Dedup check with retry on different format (BEFORE gate, so gate logs final text)
            posted_today = get_todays_posted_tweets()
            if is_too_similar(text, posted_today):
                logger.warning("DEDUP blocked tweet — retrying with different format")
                retry_success = False
                used_formats = [tweet.get("format", "")]
                for retry in range(2):
                    import random
                    avail = [k for k in TWEET_FORMATS if k not in used_formats]
                    if not avail:
                        break
                    forced_fmt = random.choice(avail)
                    used_formats.append(forced_fmt)
                    logger.info(f"DEDUP retry {retry+1}: forcing format [{forced_fmt}]")
                    retry_tweets = generate_tweets(brief, count=1)
                    if retry_tweets:
                        retry_text = _strip_hashtags(retry_tweets[0].get("text", "").strip())
                        if retry_text and not is_too_similar(retry_text, posted_today):
                            tweet = retry_tweets[0]
                            text = retry_text
                            retry_success = True
                            logger.info(f"DEDUP retry succeeded with format [{forced_fmt}]")
                            break
                        else:
                            logger.warning(f"DEDUP retry {retry+1} still blocked")
                if not retry_success:
                    logger.warning("DEDUP blocked after retries — queuing")
                    queue_tweet(tweet, brief)
                    log_to_db(tweet, posted=False)
                    queued_count += 1
                    continue

            # Global rate gate check (with final dedup-clean text)
            try:
                sys.path.insert(0, str(BASE))
                from services.x_service import can_post_tweet, ANGLE_CATEGORIES
                angle = tweet.get("angle", "macro_monetary")
                # Normalize angle to valid category
                if angle not in ANGLE_CATEGORIES:
                    angle = "macro_monetary"
                allowed, reason = can_post_tweet(text, source="tweet_machine", angle_category=angle)
                if not allowed:
                    logger.warning(f"GATE BLOCKED: {reason}")
                    queue_tweet(tweet, brief)
                    log_to_db(tweet, posted=False)
                    queued_count += 1
                    continue
            except Exception as e:
                logger.warning(f"Gate check failed (allowing): {e}")

            result = post_to_x(text)
            if result.get("success"):
                log_to_db(tweet, posted=True, tweet_id=result.get("tweet_id"))
                posted_count += 1
            else:
                queue_tweet(tweet, brief)
                log_to_db(tweet, posted=False)
                queued_count += 1
        else:
            queue_tweet(tweet, brief)
            log_to_db(tweet, posted=False)
            queued_count += 1

    logger.info(f"Done: {posted_count} posted, {queued_count} queued")
    if queued_count > 0:
        logger.info(f"Review queue at: {QUEUE_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Protocol Pulse Tweet Machine")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate tweet but do not post to X")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE — will generate but NOT post")
        load_env()
        brief = load_brief()
        if not brief:
            logger.error("Cannot generate tweets without a brief.")
            sys.exit(1)
        tweets = generate_tweets(brief, count=1)
        if not tweets:
            logger.error("No tweets generated.")
            sys.exit(1)
        for t in tweets:
            text = t.get("text", "").strip()
            print(f"\n{'='*60}")
            print(f"GENERATED TWEET ({len(text)} chars):")
            print(f"{'='*60}")
            print(text)
            print(f"{'='*60}")
            print(f"Angle: {t.get('angle', '?')} | Format: {t.get('format', '?')}")
    else:
        main()
