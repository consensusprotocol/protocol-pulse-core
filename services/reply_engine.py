#!/usr/bin/env python3
"""
reply_engine.py — Protocol Pulse Social Intelligence Layer
Phase 3: Reply/engagement engine — drafts replies, optional auto-post

Monitors X API for replies to @ProtocolPulse. Drafts signal-adding responses
via Claude Haiku. Queues all drafts to x_reply_draft table.
When ENABLE_AUTO_REPLY is True, auto-posts with rate limits (max 5/day, 30min gap).
"""

import json
import logging
import os
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
LOG_PATH = BASE / "logs" / "reply_engine.log"
SOVEREIGN_DB = BASE / "data" / "sovereign_intel.db"

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")
PP_USER_ID = os.environ.get("PP_X_USER_ID", "")  # @ProtocolPulse X user ID

logging.basicConfig(
    level=logging.INFO,
    format="[reply_engine] %(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
logger = logging.getLogger("reply_engine")

REPLY_DRAFT_PROMPT = """You are the voice of Protocol Pulse — Bitcoin intelligence platform.
A user replied to one of our posts. Draft a signal-adding reply.

ORIGINAL TWEET: {original}
REPLY FROM @{user}: {reply_text}

Requirements:
- Add signal, not noise. Contribute information or a sharper frame.
- Authoritative, cypherpunk voice. Under 240 chars.
- Never agree/disagree with opinion — add data or perspective.
- Never be defensive or promotional.
- If the reply is spam or off-topic, respond with null.

Respond with JSON only: {{"draft": "<reply text or null>", "reasoning": "<why this angle>"}}"""


def init_db():
    """Initialize x_reply_draft table if needed."""
    conn = sqlite3.connect(str(SOVEREIGN_DB))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS x_reply_draft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_tweet_id TEXT,
            original_text TEXT,
            reply_tweet_id TEXT,
            reply_user TEXT,
            reply_text TEXT,
            draft_reply TEXT,
            reasoning TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            reviewed_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def fetch_mentions() -> list:
    """Fetch recent mentions/replies via X API v2 Bearer token."""
    if not TWITTER_BEARER_TOKEN:
        logger.warning("No TWITTER_BEARER_TOKEN — cannot fetch mentions")
        return []
    if not PP_USER_ID:
        logger.warning("PP_X_USER_ID not set in .env — skipping mention fetch")
        return []
    url = f"https://api.twitter.com/2/users/{PP_USER_ID}/mentions?tweet.fields=conversation_id,author_id,text,created_at&expansions=author_id&max_results=10"
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
                    "User-Agent": "ProtocolPulse/1.0",
                },
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            return data.get("data", [])
        except Exception as e:
            if attempt == 2:
                logger.warning(f"Mention fetch failed after 3 attempts: {e}")
                return []
            logger.debug(f"Mention fetch attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)


def draft_reply(original_text: str, reply_user: str, reply_text: str) -> dict:
    """Use Claude Haiku to draft a reply."""
    if not ANTHROPIC_API_KEY:
        return {"draft": None, "reasoning": "No API key"}
    prompt = REPLY_DRAFT_PROMPT.format(
        original=original_text[:280],
        user=reply_user,
        reply_text=reply_text[:280],
    )
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
            )
            resp = urllib.request.urlopen(req, timeout=20)
            content = json.loads(resp.read()).get("content", [{}])[0].get("text", "").strip()
            if content.startswith("```"):
                content = content.split("```", 2)[1].lstrip("json").strip().rsplit("```", 1)[0].strip()
            return json.loads(content)
        except Exception as e:
            if attempt == 2:
                logger.warning(f"Draft failed after 3 attempts: {e}")
                return {"draft": None, "reasoning": str(e)}
            logger.debug(f"Draft attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)


def save_draft(original_id: str, original_text: str, reply: dict, result: dict):
    """Save draft reply to DB for human review."""
    conn = sqlite3.connect(str(SOVEREIGN_DB))
    c = conn.cursor()
    c.execute(
        """INSERT INTO x_reply_draft
           (original_tweet_id, original_text, reply_tweet_id, reply_user, reply_text,
            draft_reply, reasoning, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            original_id,
            original_text,
            reply.get("id", ""),
            reply.get("author_id", ""),
            reply.get("text", ""),
            result.get("draft"),
            result.get("reasoning", ""),
            "pending",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ── Auto-Post Logic ──────────────────────────────────────────────────────────

MAX_AUTO_REPLIES_PER_DAY = 5
MIN_REPLY_GAP_MINUTES = 30


def is_auto_reply_enabled() -> bool:
    """Check the ENABLE_AUTO_REPLY feature flag."""
    try:
        from services.feature_flags import is_enabled
        return is_enabled("ENABLE_AUTO_REPLY")
    except ImportError:
        return os.environ.get("ENABLE_AUTO_REPLY", "false").lower() in {"1", "true", "yes", "on"}


def _count_auto_replies_today() -> int:
    """Count how many auto-replies were posted today."""
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
        count = conn.execute(
            "SELECT COUNT(*) FROM x_reply_draft WHERE status = 'auto_posted' AND reviewed_at >= ?",
            (today_start,)
        ).fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def _last_auto_reply_time() -> datetime:
    """Get the timestamp of the most recent auto-posted reply."""
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        row = conn.execute(
            "SELECT reviewed_at FROM x_reply_draft WHERE status = 'auto_posted' ORDER BY reviewed_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row and row[0]:
            ts = datetime.fromisoformat(row[0])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
    except Exception:
        pass
    return datetime.min.replace(tzinfo=timezone.utc)


def can_auto_post() -> tuple:
    """Check rate limits for auto-posting. Returns (allowed, reason)."""
    count = _count_auto_replies_today()
    if count >= MAX_AUTO_REPLIES_PER_DAY:
        return False, f"Daily limit reached ({count}/{MAX_AUTO_REPLIES_PER_DAY})"

    last = _last_auto_reply_time()
    gap = datetime.now(timezone.utc) - last
    if gap < timedelta(minutes=MIN_REPLY_GAP_MINUTES):
        remaining = MIN_REPLY_GAP_MINUTES - (gap.total_seconds() / 60)
        return False, f"Too soon since last reply ({remaining:.0f}min remaining)"

    return True, "OK"


def auto_post_reply(draft_id: int, draft_text: str, reply_to_tweet_id: str) -> dict:
    """Post a draft reply to X and mark it as auto_posted."""
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=os.environ.get("X_API_KEY", os.environ.get("X_CONSUMER_KEY", "")),
            consumer_secret=os.environ.get("X_API_SECRET", os.environ.get("X_CONSUMER_SECRET", "")),
            access_token=os.environ.get("X_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("X_ACCESS_TOKEN_SECRET", ""),
        )
        response = client.create_tweet(
            text=draft_text,
            in_reply_to_tweet_id=reply_to_tweet_id,
        )
        tweet_id = response.data["id"]
        logger.info(f"Auto-posted reply {tweet_id}: {draft_text[:60]}...")

        # Mark as auto_posted in DB
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        conn.execute(
            "UPDATE x_reply_draft SET status = 'auto_posted', reviewed_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), draft_id),
        )
        conn.commit()
        conn.close()

        return {"success": True, "tweet_id": tweet_id}
    except ImportError:
        logger.error("tweepy not installed")
        return {"success": False, "error": "tweepy not installed"}
    except Exception as e:
        logger.error(f"Auto-post failed: {e}")
        return {"success": False, "error": str(e)}


def get_pending_drafts(limit: int = 20) -> list:
    """Return latest pending drafts for admin review."""
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM x_reply_draft WHERE status = 'pending' ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch drafts: {e}")
        return []


def approve_and_post_draft(draft_id: int) -> dict:
    """Admin approves a specific draft for immediate posting."""
    try:
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM x_reply_draft WHERE id = ? AND status = 'pending'",
            (draft_id,)
        ).fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": "Draft not found or already processed"}

        draft = dict(row)
        reply_to_id = draft.get("reply_tweet_id") or draft.get("original_tweet_id")
        draft_text = draft.get("draft_reply", "")

        if not draft_text or not reply_to_id:
            return {"success": False, "error": "Draft has no text or reply target"}

        return auto_post_reply(draft_id, draft_text, reply_to_id)
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    auto_mode = is_auto_reply_enabled()
    logger.info("=" * 60)
    logger.info(f"Reply Engine starting (auto-post: {'ON' if auto_mode else 'OFF'})")
    logger.info("=" * 60)

    init_db()

    mentions = fetch_mentions()
    logger.info(f"Found {len(mentions)} mentions")

    if not mentions:
        logger.info("No mentions to process.")
        return

    for mention in mentions:
        reply_text = mention.get("text", "")
        mention_id = mention.get("id", "")
        author_id = mention.get("author_id", "")
        logger.info(f"Processing mention {mention_id} from {author_id}")

        result = draft_reply(
            original_text="[original post context not available]",
            reply_user=author_id,
            reply_text=reply_text,
        )

        if result.get("draft"):
            save_draft(mention_id, reply_text, mention, result)
            logger.info(f"Draft saved: {result['draft'][:60]}...")

            # Auto-post if enabled and within rate limits
            if auto_mode:
                allowed, reason = can_auto_post()
                if allowed:
                    # Get the draft ID we just saved
                    try:
                        conn = sqlite3.connect(str(SOVEREIGN_DB))
                        row = conn.execute(
                            "SELECT id FROM x_reply_draft ORDER BY id DESC LIMIT 1"
                        ).fetchone()
                        conn.close()
                        if row:
                            post_result = auto_post_reply(row[0], result["draft"], mention_id)
                            if post_result.get("success"):
                                logger.info(f"Auto-posted reply to {mention_id}")
                            else:
                                logger.warning(f"Auto-post failed: {post_result.get('error')}")
                    except Exception as e:
                        logger.warning(f"Auto-post error: {e}")
                else:
                    logger.info(f"Auto-post skipped: {reason}")
        else:
            logger.info(f"No draft generated (spam/off-topic): {reply_text[:50]}")

    logger.info("Done.")


if __name__ == "__main__":
    main()

