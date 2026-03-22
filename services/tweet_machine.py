#!/usr/bin/env python3
"""
tweet_machine.py — Protocol Pulse Social Intelligence Layer
Phase 3: Daily tweet generation from morning intelligence brief

Runs at 6:30am ET daily. Uses morning_intelligence_brief.json to generate 
3-5 Protocol Pulse tweets. Posts via X API v2 write if credentials exist,
otherwise queues to pending_tweets.json for manual review.

Voice: authoritative, cypherpunk, signal-dense, no fluff.
Think Marty Bent meets Bloomberg Terminal.
"""

import json
import re
import logging
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone
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

IDENTITY LAWS (override everything -- apply first):

BITCOIN ONLY: Protocol Pulse is a Bitcoin platform. Not crypto. Not web3. Not DeFi.
  Bitcoin is a monetary protocol. Everything else is noise.
  Never cover: altcoins, stablecoins, Ethereum, Solana, NFTs, DeFi, or broad crypto markets.

CYPHERPUNK ETHOS: Our lens is sovereignty, privacy, sound money, and freedom from
  institutional and state control. We are not a mainstream finance outlet.
  We do not celebrate stablecoin bills, ETF approvals, or institutional on-ramps as victories.
  We observe them as signals about where power is moving -- and where it isnt.

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

TWEET_GENERATION_PROMPT = """You are the tweet writer for Protocol Pulse -- an autonomous Bitcoin intelligence platform.

Generate exactly 1 tweet for @ProtocolPulseHQ based on today's intelligence brief.
Pick the single highest-signal angle. Make it land.

INTELLIGENCE BRIEF:
{brief_text}

VOICE LAWS (mandatory):
{voice_laws}

HARD RULES:
- Never start with: Just, Hot take, Thread:, GM, Attention, Breaking, We
- Never use exclamation marks
- Never end with a period
- No hashtags
- No emoji
- No em dashes (the long dash: --)
- No double dashes (--)
- No dashes used as pauses or separators of any kind

EXAMPLES OF THE RIGHT VOICE:
- "Capitalism started in 1602 with the world's first stock exchange. It died in 2026 with the first unrealized gains tax. Neofeudalism arrived quietly"
- "Strategy acquired BTC again. No press conference. No explanation needed"
- "Remember all the talk of auditing the gold reserves in Fort Knox last year?"

Respond with a JSON object only. No markdown. No preamble:
{{"text": "<tweet -- max 280 chars, no trailing period, no emoji, no hashtags>", "angle": "<narrative addressed>", "type": "<stat|observation|question|signal>", "char_count": 0}}"""


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
    """Fetch tweet texts already posted today to avoid repeats."""
    try:
        conn = sqlite3.connect(str(BASE / "instance" / "protocol_pulse.db"))
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT tweet_content FROM auto_tweet WHERE posted_at >= ? ORDER BY posted_at DESC LIMIT 10",
            (today,)
        ).fetchall()
        conn.close()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        logger.warning(f"Could not fetch posted tweets: {e}")
        return []


def _keyword_overlap(text_a: str, text_b: str) -> float:
    """Return fraction of significant words shared between two tweets."""
    stop = {"the","a","an","is","are","was","were","and","or","but","in","on","at","to","of","for","with","this","that","it","as","by"}
    def words(t): return set(w.lower() for w in re.findall(r"\w+", t) if w.lower() not in stop and len(w) > 3)
    wa, wb = words(text_a), words(text_b)
    if not wa or not wb: return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def is_too_similar(new_tweet: str, posted: list[str], threshold: float = 0.55) -> bool:
    """Return True if new_tweet overlaps too much with any recently posted tweet."""
    for old in posted:
        if _keyword_overlap(new_tweet, old) >= threshold:
            logger.warning(f"DEDUP blocked — {_keyword_overlap(new_tweet, old):.0%} overlap with: {old[:60]}")
            return True
    return False

def generate_tweets(brief: dict, count: int = 1) -> list:
    """Call Claude Haiku to generate tweets from the brief."""
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return []

    brief_text = json.dumps(brief, indent=2)[:3000]
    posted_today = get_todays_posted_tweets()
    used_context = ""
    if posted_today:
        used_context = "\nALREADY POSTED TODAY - pick a DIFFERENT angle:\n"
        used_context += "\n".join("- " + t[:100] for t in posted_today)
    prompt = TWEET_GENERATION_PROMPT.format(brief_text=brief_text + used_context, voice_laws=TWEET_VOICE_LAWS)

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
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        content = data.get("content", [{}])[0].get("text", "").strip()
        # Strip markdown fences
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            parsed = [parsed]
        logger.info(f"Generated {len(parsed)} tweet(s)")
        return parsed
    except Exception as e:
        logger.error(f"Tweet generation failed: {e}")
        return []


def _strip_hashtags(text: str) -> str:
    """Remove any hashtags from outgoing text. X algorithms penalize them."""
    import re
    return re.sub(r" #\w+", "", text).strip()


def post_to_x(tweet_text: str) -> dict:
    """Post a tweet via X API v2 using OAuth 1.0a."""
    # Requires: tweepy or manual OAuth 1.0a signing
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
    # Load existing queue
    existing = []
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH) as f:
            existing = json.load(f)

    entry = {
        "id": f"tweet_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{tweet.get('priority', 0)}",
        "text": tweet.get("text", ""),
        "angle": tweet.get("angle", ""),
        "type": tweet.get("type", ""),
        "priority": tweet.get("priority", 3),
        "status": "pending",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brief_date": brief.get("date", ""),
        "sentiment": brief.get("sentiment", ""),
    }

    # Dedup by text
    existing_texts = {e.get("text", "") for e in existing}
    if entry["text"] not in existing_texts:
        existing.append(entry)
        with open(QUEUE_PATH, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        logger.info(f"Queued: {entry['text'][:60]}...")


def log_to_db(tweet: dict, posted: bool, tweet_id: str = None) -> None:
    """Log tweet to sovereign_intel.db auto_tweet table."""
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
                brief_date TEXT
            )
        """)
        c.execute(
            """INSERT INTO auto_tweet 
               (tweet_text, tweet_type, angle, status, x_tweet_id, generated_at, posted_at, sentiment, brief_date)
               VALUES (?,?,?,?,?,?,?,?,?)""",
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
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"DB log failed: {e}")


def main():
    logger.info("=" * 60)
    logger.info("Tweet Machine starting")
    logger.info("=" * 60)

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
            result = post_to_x(text)
            if result.get("success"):
                log_to_db(tweet, posted=True, tweet_id=result.get("tweet_id"))
                posted_count += 1
            else:
                # Fallback to queue
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
    main()

