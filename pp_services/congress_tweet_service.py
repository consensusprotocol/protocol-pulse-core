#!/usr/bin/env python3
"""
Congress Tweet Service — Auto-tweet on congressional crypto purchases/sales.

Monitors STOCK Act disclosures via panopticon_service, applies strict signal
filters (ticker whitelist, amount threshold, notable politician boost),
rate-limits to max 3/day, and posts via tweet_machine's X API.

Template-based (no LLM) — deterministic, fast, zero API cost.

Cron: */30 * * * * cd ~/protocol_pulse && python3 -m services.congress_tweet_service >> logs/congress_tweet.log 2>&1
"""

import json
import logging
import os
import re
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


# ── Signal Filters ───────────────────────────────────────────────────────────

# ONLY these tickers are tweet-worthy
SIGNAL_TICKERS = {
    # Bitcoin spot ETFs
    "IBIT", "FBTC", "GBTC", "ARKB", "BITB", "HODL", "BTCO", "EZBC", "BRRR", "BTCW",
    # Bitcoin treasury
    "MSTR",
    # Bitcoin miners (major only)
    "MARA", "RIOT", "CLSK", "HUT",
    # Ethereum ETFs
    "ETHE", "ETHA",
    # Crypto exchange (Coinbase only)
    "COIN",
}

NOTABLE_POLITICIANS = {
    "Cynthia Lummis", "Michael Saylor", "Nancy Pelosi", "Paul Pelosi",
    "Tim Scott", "Patrick McHenry", "Ritchie Torres", "Ro Khanna",
    "Tommy Tuberville", "Dan Crenshaw", "Ted Cruz", "Marjorie Taylor Greene",
    "Michael McCaul", "French Hill", "Tom Emmer", "Warren Davidson",
}

# Rate limit: max tweets per calendar day (UTC)
MAX_TWEETS_PER_DAY = 3

# Amount thresholds
MIN_AMOUNT_DEFAULT = 15001
MIN_AMOUNT_NOTABLE = 1001


# ── Dedup + Rate Limit ───────────────────────────────────────────────────────

def _load_seen() -> dict:
    """Load dedup + rate limit state."""
    if SEEN_PATH.exists():
        try:
            data = json.loads(SEEN_PATH.read_text())
            # Ensure all required keys exist
            data.setdefault("seen_ids", [])
            data.setdefault("tweets", [])
            data.setdefault("daily_counts", {})
            return data
        except Exception:
            pass
    return {"seen_ids": [], "tweets": [], "daily_counts": {}}


def _save_seen(data: dict) -> None:
    """Atomic write of seen data."""
    tmp = SEEN_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.rename(SEEN_PATH)


def _make_dedup_key(d: dict) -> str:
    """Create unique key: entity + ticker + trade_type + date_traded."""
    entity = d.get("entity", "")
    return f"{entity}|{d.get('ticker', '')}|{d.get('trade_type', '')}|{d.get('date_traded', '')}"


def _get_today_key() -> str:
    """UTC date string for rate limiting."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _tweets_today(data: dict) -> int:
    """How many congress tweets have been posted today (UTC)."""
    today = _get_today_key()
    return data.get("daily_counts", {}).get(today, 0)


def _increment_daily_count(data: dict) -> None:
    """Bump today's tweet count."""
    today = _get_today_key()
    counts = data.setdefault("daily_counts", {})
    counts[today] = counts.get(today, 0) + 1
    # Prune old daily counts (keep last 30 days)
    if len(counts) > 30:
        sorted_keys = sorted(counts.keys())
        for old_key in sorted_keys[:-30]:
            del counts[old_key]


# ── Amount Parsing ───────────────────────────────────────────────────────────

def _parse_lower_bound(amount_range: str) -> int:
    """Extract lower bound from amount range string like '$1,001 - $15,000'.

    Returns 0 if unparseable.
    """
    if not amount_range:
        return 0
    # Match the first dollar amount in the string
    match = re.search(r"\$?([\d,]+)", amount_range)
    if not match:
        return 0
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return 0


# ── Notable Politician Detection ─────────────────────────────────────────────

def _is_notable(entity: str) -> bool:
    """Check if any notable politician name appears in the entity string."""
    for name in NOTABLE_POLITICIANS:
        if name in entity:
            return True
    return False


# ── Qualification Filter ─────────────────────────────────────────────────────

def _qualifies(d: dict) -> tuple[bool, str]:
    """Check if a disclosure qualifies for tweeting.

    Returns (qualifies: bool, reason: str).
    """
    entity = d.get("entity", "").strip()
    if not entity:
        return False, "empty entity"

    ticker = d.get("ticker", "")
    if ticker not in SIGNAL_TICKERS:
        return False, f"ticker {ticker} not in SIGNAL_TICKERS"

    amount_range = d.get("amount_range", "")
    lower_bound = _parse_lower_bound(amount_range)

    notable = _is_notable(entity)
    threshold = MIN_AMOUNT_NOTABLE if notable else MIN_AMOUNT_DEFAULT

    if lower_bound < threshold:
        notable_str = " (notable)" if notable else ""
        return False, f"amount {amount_range} below ${threshold:,} threshold{notable_str}"

    return True, "qualified"


# ── Tweet Templates ──────────────────────────────────────────────────────────

def _format_tweet(d: dict) -> str:
    """Generate template-based tweet. PBX voice — dry, factual, signal-focused."""
    entity = d.get("entity", "")
    trade_type = d.get("trade_type", "disclosure")
    ticker = d.get("ticker", "")
    asset_name = d.get("asset", "") or d.get("asset_name", "") or ticker
    amount_range = d.get("amount_range", "undisclosed")
    days_to_file = d.get("days_to_file")
    conviction = d.get("conviction")
    notable = _is_notable(entity)

    amt_display = amount_range if amount_range.startswith("$") else f"${amount_range}"

    # Notable politicians with high conviction get BREAKING format
    if notable and conviction and conviction > 60:
        pattern_line = ""
        if days_to_file is not None and days_to_file > 30:
            pattern_line = f" Filed {days_to_file}d after trade."
        tweet = (
            f"BREAKING: {entity} just filed a {trade_type} of {asset_name} "
            f"— {amt_display}. Conviction: {conviction}%.{pattern_line}"
        )
    else:
        # Standard format
        if trade_type == "purchase":
            action = "bought"
        elif trade_type == "sale":
            action = "sold"
        else:
            action = "disclosed a position in"

        filing_note = ""
        if days_to_file is not None:
            filing_note = f" Filed {days_to_file}d after trade."

        if trade_type == "purchase":
            closer = " The signal is in the filing."
        elif trade_type == "sale":
            closer = " Watch the exits."
        else:
            closer = " The filing speaks."

        tweet = (
            f"STOCK ACT FILING: {entity} {action} {amt_display} of "
            f"{asset_name} ({ticker}).{filing_note}{closer}"
        )

    # Enforce 280 char limit
    if len(tweet) > 280:
        tweet = tweet[:277].rsplit(".", 1)[0] + "."

    return tweet


# ── Core ─────────────────────────────────────────────────────────────────────

def check_and_tweet(dry_run: bool = False) -> list[dict]:
    """Check for new crypto-related congressional trades and tweet them.

    Applies strict filtering:
    1. Entity must be present (no "Unknown")
    2. Ticker must be in SIGNAL_TICKERS
    3. Amount lower bound >= $15,001 (or $1,001 for notable politicians)
    4. Max 3 tweets per day
    5. Dedup on entity+ticker+trade_type+date_traded

    Returns list of tweets generated.
    """
    sys.path.insert(0, str(BASE))
    from pp_services.panopticon_service import fetch_stock_act_disclosures

    disclosures = fetch_stock_act_disclosures(limit=50)
    if not disclosures:
        logger.info("No disclosures found")
        return []

    seen_data = _load_seen()
    seen_ids = set(seen_data.get("seen_ids", []))

    new_tweets = []
    skipped = {"no_entity": 0, "bad_ticker": 0, "low_amount": 0, "dedup": 0, "rate_limit": 0}

    for d in disclosures:
        # 1. Dedup check
        key = _make_dedup_key(d)
        if key in seen_ids:
            skipped["dedup"] += 1
            continue

        # 2. Qualification filter
        qualifies, reason = _qualifies(d)
        if not qualifies:
            if "empty entity" in reason:
                skipped["no_entity"] += 1
            elif "not in SIGNAL_TICKERS" in reason:
                skipped["bad_ticker"] += 1
            else:
                skipped["low_amount"] += 1
            logger.debug(f"Skipped: {reason} — {d.get('entity', '?')} {d.get('ticker', '?')}")
            # Mark as seen so we don't re-evaluate next run
            seen_ids.add(key)
            continue

        # 3. Rate limit check
        if not dry_run and _tweets_today(seen_data) >= MAX_TWEETS_PER_DAY:
            skipped["rate_limit"] += 1
            logger.info(f"Rate limited (max {MAX_TWEETS_PER_DAY}/day): {key}")
            continue

        # 4. Format and post
        tweet_text = _format_tweet(d)
        logger.info(f"Qualifying disclosure: {key}")
        logger.info(f"Tweet ({len(tweet_text)} chars): {tweet_text}")

        result = {"text": tweet_text, "disclosure": d, "key": key, "posted": False}

        if not dry_run:
            try:
                from pp_services.social_broadcaster import broadcast
                from pp_services.tweet_machine import log_to_db
                bcast = broadcast(tweet_text, platforms=["x", "nostr"])
                x_result = bcast.get("x", {})
                result["posted"] = x_result.get("success", False)
                result["tweet_id"] = x_result.get("tweet_id")
                result["nostr"] = bcast.get("nostr", {})
                if result["posted"]:
                    logger.info(f"Posted tweet {result['tweet_id']}")
                    _increment_daily_count(seen_data)
                    log_to_db(
                        {"text": tweet_text, "type": "congress_filing",
                         "angle": "stock_act", "format": "congress"},
                        posted=True, tweet_id=result.get("tweet_id")
                    )
                else:
                    logger.warning(f"X post failed: {x_result.get('error')}")
                nostr_ok = bcast.get("nostr", {}).get("success")
                logger.info(f"Nostr: {'OK' if nostr_ok else 'FAIL'}")
            except Exception as e:
                logger.error(f"Failed to post: {e}")

        # Mark as seen
        seen_ids.add(key)
        new_tweets.append(result)

        seen_data["tweets"].append({
            "key": key,
            "text": tweet_text,
            "posted": result.get("posted", False),
            "tweet_id": result.get("tweet_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Update seen_ids and save
    seen_data["seen_ids"] = list(seen_ids)
    # Keep only last 500 tweet records
    if len(seen_data["tweets"]) > 500:
        seen_data["tweets"] = seen_data["tweets"][-500:]
    _save_seen(seen_data)

    # Summary log
    total_skipped = sum(skipped.values())
    logger.info(
        f"Results: {len(new_tweets)} qualifying, {total_skipped} filtered "
        f"(dedup={skipped['dedup']}, ticker={skipped['bad_ticker']}, "
        f"amount={skipped['low_amount']}, entity={skipped['no_entity']}, "
        f"rate_limit={skipped['rate_limit']})"
    )

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
        print(f"[{status}] {t['text']}")
    if not tweets:
        print("No qualifying disclosures found")
    logger.info(f"=== Done. {len(tweets)} tweet(s) processed ===")
