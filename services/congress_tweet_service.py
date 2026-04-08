#!/usr/bin/env python3
"""
Congress Tweet Service — Auto-tweet on congressional crypto purchases/sales.

Monitors STOCK Act disclosures via panopticon_service, detects new crypto-related
trades, and posts template-based tweets via tweet_machine's X API.

Template-based (no LLM) — deterministic, fast, zero API cost.

Cron: */30 * * * * cd ~/protocol_pulse && python3 -m services.congress_tweet_service >> logs/congress_tweet.log 2>&1
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path("/home/ultron/protocol_pulse")
SEEN_PATH = BASE / "data" / "congress_tweets_sent.json"
LOG_PATH = BASE / "logs" / "congress_tweet.log"

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[congress_tweet] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("congress_tweet")

# Load .env
_env_path = BASE / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


# ── Dedup ────────────────────────────────────────────────────────────────────

def _load_seen() -> dict:
    """Load set of already-tweeted disclosure IDs."""
    if SEEN_PATH.exists():
        try:
            return json.loads(SEEN_PATH.read_text())
        except Exception:
            pass
    return {"seen_ids": [], "tweets": []}


def _save_seen(data: dict) -> None:
    """Atomic write of seen data."""
    tmp = SEEN_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.rename(SEEN_PATH)


def _make_dedup_key(d: dict) -> str:
    """Create unique key for a disclosure to prevent duplicate tweets."""
    # Panopticon returns 'entity' (e.g. "Rep. John Smith (R)"), not 'representative'
    name = d.get("entity") or d.get("representative", "")
    return f"{name}|{d.get('ticker', '')}|{d.get('date_traded', '')}|{d.get('trade_type', '')}"


# ── Tweet Templates ──────────────────────────────────────────────────────────

def _format_tweet(d: dict) -> str:
    """Generate template-based tweet from a disclosure record.

    Stays under 280 chars. No hashtags. PBX voice — dry, factual, signal-focused.
    """
    # Panopticon returns 'entity' (e.g. "Rep. John Smith (R)") — use directly
    entity = d.get("entity", "")
    if entity:
        # entity already has "Rep." or "Sen." prefix and party suffix
        who = entity
    else:
        title = d.get("title", "Rep.")
        name = d.get("representative", "Unknown")
        who = f"{title} {name}"

    trade_type = d.get("trade_type", "disclosure")
    ticker = d.get("ticker", "")
    asset_name = d.get("asset", "") or d.get("asset_name", "") or ticker
    amount = d.get("amount_range", "undisclosed")
    days_to_file = d.get("days_to_file")

    # Action verb
    if trade_type == "purchase":
        action = "bought"
    elif trade_type == "sale":
        action = "sold"
    else:
        action = "disclosed a position in"

    # Build tweet
    # amount_range from panopticon already includes $ prefix (e.g. "$15,001-$50,000")
    amt_display = amount if amount.startswith("$") else f"${amount}"
    tweet = f"STOCK ACT FILING: {who} just {action} {amt_display} of {asset_name}."

    # Add filing delay context if notable (>30 days is suspicious)
    if days_to_file is not None and days_to_file > 30:
        tweet += f" Filed {days_to_file} days after the trade."

    # Closing signal line — varies by trade type
    if trade_type == "purchase":
        tweet += " The signal is in the filing."
    elif trade_type == "sale":
        tweet += " Watch the exits."
    else:
        tweet += " The filing speaks."

    # Enforce 280 char limit
    if len(tweet) > 280:
        # Trim the closing line
        tweet = tweet[:277].rsplit(".", 1)[0] + "."

    return tweet


# ── Core ─────────────────────────────────────────────────────────────────────

def check_and_tweet(dry_run: bool = False) -> list[dict]:
    """Check for new crypto-related congressional trades and tweet them.

    Returns list of tweets generated (posted or queued).
    """
    # Import panopticon for disclosures
    sys.path.insert(0, str(BASE))
    from services.panopticon_service import fetch_stock_act_disclosures

    disclosures = fetch_stock_act_disclosures(limit=50)
    if not disclosures:
        logger.info("No disclosures found")
        return []

    seen_data = _load_seen()
    seen_ids = set(seen_data.get("seen_ids", []))

    new_tweets = []
    for d in disclosures:
        key = _make_dedup_key(d)
        if key in seen_ids:
            continue

        tweet_text = _format_tweet(d)
        logger.info(f"New disclosure: {key}")
        logger.info(f"Tweet ({len(tweet_text)} chars): {tweet_text}")

        result = {"text": tweet_text, "disclosure": d, "key": key, "posted": False}

        if not dry_run:
            # Post via tweet_machine's post_to_x
            try:
                from services.tweet_machine import post_to_x, log_to_db, CAN_POST
                if CAN_POST:
                    post_result = post_to_x(tweet_text)
                    result["posted"] = post_result.get("success", False)
                    result["tweet_id"] = post_result.get("tweet_id")
                    if result["posted"]:
                        logger.info(f"Posted tweet {result['tweet_id']}")
                        # Log to tweet_machine's DB
                        log_to_db(
                            {"text": tweet_text, "type": "congress_filing",
                             "angle": "stock_act", "format": "congress"},
                            posted=True, tweet_id=result.get("tweet_id")
                        )
                    else:
                        logger.warning(f"Post failed: {post_result.get('error')}")
                else:
                    logger.warning("X API credentials not configured — queueing only")
            except Exception as e:
                logger.error(f"Failed to post: {e}")

        # Mark as seen regardless (prevent retry spam)
        seen_ids.add(key)
        new_tweets.append(result)

        # Record in seen file
        seen_data["seen_ids"] = list(seen_ids)
        seen_data["tweets"].append({
            "key": key,
            "text": tweet_text,
            "posted": result.get("posted", False),
            "tweet_id": result.get("tweet_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep only last 500 entries
        if len(seen_data["tweets"]) > 500:
            seen_data["tweets"] = seen_data["tweets"][-500:]

    _save_seen(seen_data)

    if new_tweets:
        logger.info(f"Processed {len(new_tweets)} new disclosure(s)")
    else:
        logger.info("No new disclosures to tweet")

    return new_tweets


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Congress crypto trade auto-tweeter")
    parser.add_argument("--dry-run", action="store_true", help="Generate tweets without posting")
    args = parser.parse_args()

    logger.info("=== Congress Tweet Service starting ===")
    tweets = check_and_tweet(dry_run=args.dry_run)
    for t in tweets:
        status = "POSTED" if t.get("posted") else "DRY-RUN" if args.dry_run else "QUEUED"
        logger.info(f"[{status}] {t['text'][:80]}...")
    logger.info(f"=== Done. {len(tweets)} tweet(s) processed ===")
