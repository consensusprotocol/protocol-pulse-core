#!/usr/bin/env python3
"""
nitter_scraper.py — Protocol Pulse Social Intelligence Layer
Phase 1: Fresh tweet data via Nitter RSS (no X API quota used)

RSS endpoint: https://nitter.net/{handle}/rss
Runs every 6 hours via cron. Appends fresh tweets to raw_tweets.json (deduped by id).
"""

import json
import logging
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path("/home/ultron/protocol_pulse")
SOCIAL_TARGETS_PATH = BASE / "config" / "social_targets.json"
RAW_TWEETS_PATH = BASE / "data" / "tweet_study" / "raw_tweets.json"
LOG_PATH = BASE / "logs" / "nitter_scraper.log"

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[nitter] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("nitter_scraper")

# ── Nitter instances (primary first, fallbacks after) ────────────────────────
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://nitter.cz",
    "https://xcancel.com",
]

# ── Bitcoin/freedom keyword filter ───────────────────────────────────────────
RELEVANT_KEYWORDS = {
    "bitcoin", "btc", "sats", "satoshi", "lightning", "sovereignty",
    "hodl", "self-custody", "multisig", "halving", "mempool", "taproot",
    "ordinals", "nostr", "zap", "cypherpunk", "freedom", "money",
    "inflation", "fed", "treasury", "gold", "dollar", "currency",
    "debasement", "sound money", "hard money", "fiat", "miner", "mining",
    "hash", "blockchain", "node", "wallet", "exchange", "sec", "etf",
    "gbtc", "coinbase", "blackrock", "microstrategy", "strategy", "mstr",
    "hyperbitcoinization", "stack", "stacking", "price", "market",
    "macro", "interest rate", "monetary", "central bank", "cbdc",
    "regulation", "policy", "financial", "network", "protocol",
}

# Tier mapping from priority
TIER_MAP = {1: "conviction_data", 2: "signal", 3: "noise"}

# Request delay between handles (be polite to nitter)
REQUEST_DELAY_SECS = 2.5
RETRY_DELAY_SECS = 5.0
MAX_ITEMS_PER_HANDLE = 20


def is_relevant(text: str) -> bool:
    """Return True if tweet text contains Bitcoin/freedom-relevant keywords."""
    lower = text.lower()
    return any(kw in lower for kw in RELEVANT_KEYWORDS)


def _parse_count(text: str) -> int:
    """Parse engagement count string like '12.4K', '1.2M', '350' to int."""
    text = text.strip().replace(",", "")
    if not text:
        return 0
    try:
        if text.upper().endswith("K"):
            return int(float(text[:-1]) * 1000)
        elif text.upper().endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        else:
            return int(text) if text.isdigit() else 0
    except (ValueError, IndexError):
        return 0


def fetch_engagement(tweet_id: str, instance: str, timeout: int = 8) -> dict:
    """BUG 4 FIX: Best-effort engagement fetch from Nitter HTML for a single tweet.

    Returns {"likes": int, "retweets": int} or empty dict on failure.
    """
    url = f"{instance}/i/status/{tweet_id}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; RSS reader; +https://protocolpulse.io)",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return {}

    likes = 0
    retweets = 0
    # Nitter renders stats as: <span class="tweet-stat">...<div class="icon-heart"/>...<span>12.4K</span>
    # or <span class="icon-retweet"/>...<span>350</span>
    # Parse with regex since we don't want to require BeautifulSoup
    for m in re.finditer(
        r'class="tweet-stat[^"]*"[^>]*>.*?class="icon-(heart|retweet|comment|quote)[^"]*".*?'
        r'<span[^>]*>\s*(\d[\d.,]*[KkMm]?)\s*</span>',
        html, re.DOTALL
    ):
        icon_type = m.group(1)
        count = _parse_count(m.group(2))
        if "heart" in icon_type or "like" in icon_type:
            likes = count
        elif "retweet" in icon_type:
            retweets = count
    # Alternate pattern: Nitter may use stat-count class
    if likes == 0 and retweets == 0:
        for m in re.finditer(
            r'icon-(heart|retweet)[^"]*"[^<]*</[^>]+>\s*(\d[\d.,]*[KkMm]?)',
            html, re.DOTALL
        ):
            icon_type = m.group(1)
            count = _parse_count(m.group(2))
            if "heart" in icon_type:
                likes = count
            elif "retweet" in icon_type:
                retweets = count

    return {"likes": likes, "retweets": retweets} if (likes or retweets) else {}


def load_social_targets() -> list:
    """Load social targets from config file."""
    with open(SOCIAL_TARGETS_PATH) as f:
        data = json.load(f)
    targets = data.get("targets", [])
    # Sort by priority (1=highest)
    return sorted(targets, key=lambda t: t.get("priority", 3))


def load_existing_tweets() -> dict:
    """Load existing raw_tweets.json, return as dict keyed by tweet id."""
    if not RAW_TWEETS_PATH.exists():
        return {}
    with open(RAW_TWEETS_PATH) as f:
        raw = f.read()
        try:
            tweets = json.loads(raw)
        except json.JSONDecodeError:
            # Recover from appended/corrupt JSON
            decoder = json.JSONDecoder()
            tweets, _ = decoder.raw_decode(raw)
            logger.warning(f'Recovered {len(tweets)} tweets from corrupt JSON')
    return {str(t.get("id", "")): t for t in tweets if t.get("id")}


def fetch_rss(handle: str, instance: str, timeout: int = 12) -> bytes | None:
    """Fetch RSS feed for a handle from the given nitter instance."""
    url = f"{instance}/{handle}/rss"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RSS reader; +https://protocolpulse.io)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = resp.read()
        if len(data) < 100:
            logger.debug(f"Empty response from {url} ({len(data)} bytes)")
            return None
        return data
    except Exception as e:
        logger.debug(f"RSS fetch failed {url}: {e}")
        return None


def strip_html(html_text: str) -> str:
    """Remove HTML tags and decode entities."""
    clean = re.sub(r"<[^>]+>", " ", html_text or "")
    clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    clean = clean.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def parse_rss(xml_data: bytes, handle: str, priority: int, category: str) -> list:
    """Parse nitter RSS XML and return list of tweet dicts."""
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        logger.warning(f"XML parse error for {handle}: {e}")
        return []

    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    channel = root.find("channel")
    if channel is None:
        return []

    tweets = []
    items = channel.findall("item")[:MAX_ITEMS_PER_HANDLE]
    tier = TIER_MAP.get(priority, "noise")

    for item in items:
        try:
            guid = item.findtext("guid", "").strip()
            link = item.findtext("link", "").strip()
            raw_title = item.findtext("title", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            creator = item.findtext("dc:creator", handle, ns).lstrip("@").strip()

            # Determine tweet type
            rt_match = re.match(r"^RT by @\w+: (.+)$", raw_title, re.DOTALL)
            if rt_match:
                tweet_type = "retweet"
                # The original content belongs to dc:creator, not the monitored handle
                actual_handle = creator
                text = rt_match.group(1).strip()
            else:
                tweet_type = "original"
                actual_handle = handle
                text = raw_title

            # Clean up text
            text = text.strip()
            if not text:
                continue

            # Apply keyword filter (but don't filter Priority-1 handles aggressively)
            if priority >= 2 and not is_relevant(text):
                continue

            # Parse timestamp
            try:
                dt = parsedate_to_datetime(pub_date)
                created_at = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            except Exception:
                created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

            # BUG 4 FIX: Extract tweet ID and attempt engagement fetch
            tweet_id = (guid or link.split("/")[-1].replace("#m", "")).split("/")[-1].split("#")[0]

            tweet = {
                "id": tweet_id,
                "handle": actual_handle,
                "monitored_handle": handle,  # The handle we were watching
                "tier": tier,
                "category": category,
                "priority": priority,
                "followers": 0,  # Not available from RSS
                "text": text[:560],  # Allow long tweets
                "created_at": created_at,
                "likes": 0,
                "retweets": 0,
                "replies": 0,
                "quotes": 0,
                "impressions": 0,
                "tweet_type": tweet_type,
                "char_count": len(text),
                "word_count": len(text.split()),
                "has_url": "http" in text.lower(),
                "has_media": False,
                "has_data": any(c.isdigit() for c in text),
                "has_question": "?" in text,
                "has_em_dash": "—" in text or " - " in text,
                "has_profanity": False,
                "has_emoji": bool(re.search(r"[^\x00-\x7F]", text)),
                "raw_engagement": 0,
                "engagement_rate": 0.0,
                "sentence_count": text.count(".") + text.count("!") + text.count("?"),
                "ending_punct": text[-1] if text else "",
                "starts_with_number": text[0].isdigit() if text else False,
                "is_thread_starter": False,
                "source": "nitter_rss",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            tweets.append(tweet)

        except Exception as e:
            logger.debug(f"Error parsing item for {handle}: {e}")
            continue

    return tweets


def scrape_handle(handle: str, priority: int, category: str) -> list:
    """Try all nitter instances for a handle. Return parsed tweets."""
    for instance in NITTER_INSTANCES:
        xml_data = fetch_rss(handle, instance)
        if xml_data:
            tweets = parse_rss(xml_data, handle, priority, category)
            if tweets:
                # BUG 4 FIX: Best-effort engagement stats for top tweets (priority 1 only)
                if priority <= 1:
                    for t in tweets[:5]:  # limit to 5 to avoid rate limiting
                        eng = fetch_engagement(t["id"], instance)
                        if eng:
                            t["likes"] = eng.get("likes", 0)
                            t["retweets"] = eng.get("retweets", 0)
                            t["raw_engagement"] = t["likes"] + t["retweets"] * 2
                            t["engagement_rate"] = t["raw_engagement"] / max(t.get("followers", 0), 1000)
                            logger.debug(f"    {handle}/{t['id']}: {t['likes']} likes, {t['retweets']} RTs")
                            time.sleep(0.3)
                logger.info(f"  {handle}: {len(tweets)} tweets from {instance}")
                return tweets
            logger.debug(f"  {handle}: 0 tweets parsed from {instance}")
        time.sleep(0.5)  # Small delay between instance retries

    logger.warning(f"  {handle}: FAILED all instances")
    return []


def main():
    logger.info("=" * 60)
    logger.info("Nitter RSS scraper starting")
    logger.info("=" * 60)

    # Load targets
    targets = load_social_targets()
    logger.info(f"Loaded {len(targets)} handles to scrape")

    # Load existing tweets for dedup
    existing = load_existing_tweets()
    logger.info(f"Loaded {len(existing)} existing tweets")

    # Scrape all handles
    new_tweets = []
    new_ids = set()
    failed = []
    success = 0

    for i, target in enumerate(targets):
        handle = target.get("handle", "")
        priority = target.get("priority", 3)
        category = target.get("category", "general")

        if not handle:
            continue

        logger.info(f"[{i+1}/{len(targets)}] Scraping @{handle} (P{priority} {category})")
        tweets = scrape_handle(handle, priority, category)

        added = 0
        for tweet in tweets:
            tid = str(tweet.get("id", ""))
            if tid and tid not in existing and tid not in new_ids:
                new_tweets.append(tweet)
                new_ids.add(tid)
                added += 1

        if tweets:
            success += 1
        else:
            failed.append(handle)

        # Rate limit
        if i < len(targets) - 1:
            time.sleep(REQUEST_DELAY_SECS)

    logger.info(f"\n{'='*60}")
    logger.info(f"Scrape complete: {success}/{len(targets)} handles OK")
    logger.info(f"New tweets: {len(new_tweets)}")
    if failed:
        logger.warning(f"Failed handles ({len(failed)}): {', '.join(failed)}")

    if not new_tweets:
        logger.info("No new tweets to write.")
        return

    # Merge: new tweets + existing, sort by created_at desc
    all_tweets = list(existing.values()) + new_tweets
    all_tweets.sort(key=lambda t: t.get("created_at", ""), reverse=True)

    # Write
    RAW_TWEETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = RAW_TWEETS_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w") as f:
        json.dump(all_tweets, f, indent=2, ensure_ascii=False)
    tmp_path.replace(RAW_TWEETS_PATH)

    logger.info(f"Written {len(all_tweets)} total tweets to {RAW_TWEETS_PATH}")
    logger.info(
        f"Date range: {all_tweets[-1].get('created_at','?')} → {all_tweets[0].get('created_at','?')}"
    )


if __name__ == "__main__":
    main()

