"""
mining_intel_monitor.py — Protocol Pulse Mining Intelligence Monitor
Monitors RSS feeds from Blockware Intelligence, Hashrate Index, and others.
Generates original Protocol Pulse mining analysis articles enriched with live data.

Run: python3 -m services.mining_intel_monitor
Cron: 0 */6 * * * source ~/protocol_pulse/.env && python3 -m services.mining_intel_monitor >> logs/mining_intel.log 2>&1
"""

import os
import sys
import logging
import hashlib
import sqlite3
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import requests
import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] mining_intel: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

RSS_SOURCES = [
    {
        "name": "Blockware Intelligence",
        "url": "https://blockwareintelligence.substack.com/feed",
    },
    {
        "name": "Hashrate Index",
        "url": "https://hashrateindex.com/blog/rss.xml",
    },
]

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "instance", "protocol_pulse.db"),
)

REQUEST_TIMEOUT = 12
MAX_ARTICLES_PER_RUN = 3  # Respect API quota; generate at most 3 new articles per run


# ── Database helpers ──────────────────────────────────────────────────────────

def _get_db_conn() -> sqlite3.Connection:
    """Open a connection to the production SQLite database."""
    db_path = os.path.normpath(DB_PATH)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_seen_table(conn: sqlite3.Connection) -> None:
    """Create mining_intel_seen table if it doesn't exist (migration-safe)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mining_intel_seen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT UNIQUE NOT NULL,
            source_title TEXT,
            source_name TEXT,
            article_id_generated INTEGER,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _is_seen(conn: sqlite3.Connection, source_url: str) -> bool:
    row = conn.execute(
        "SELECT id FROM mining_intel_seen WHERE source_url = ?", (source_url,)
    ).fetchone()
    return row is not None


def _mark_seen(
    conn: sqlite3.Connection,
    source_url: str,
    source_title: str,
    source_name: str,
    article_id: Optional[int],
) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO mining_intel_seen
           (source_url, source_title, source_name, article_id_generated, processed_at)
           VALUES (?, ?, ?, ?, ?)""",
        (source_url, source_title, source_name, article_id, datetime.utcnow().isoformat()),
    )
    conn.commit()


def _save_article(
    conn: sqlite3.Connection,
    title: str,
    content: str,
    summary: str,
    tags: str,
) -> int:
    """Insert article into articles table and return new ID."""
    now = datetime.utcnow().isoformat()
    cur = conn.execute(
        """INSERT INTO articles
           (title, content, summary, author, category, tags, source_type,
            published, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            title,
            content,
            summary,
            "Protocol Pulse AI",
            "mining",
            tags,
            "mining_intel",
            1,  # published = True
            now,
            now,
        ),
    )
    conn.commit()
    return cur.lastrowid


# ── RSS parsing (no feedparser dependency) ────────────────────────────────────

def _parse_rss(feed_text: str) -> List[Dict[str, str]]:
    """Minimal RSS/Atom parser — extracts title + link pairs without feedparser."""
    import re
    items = []
    # Try RSS <item> blocks first
    item_blocks = re.findall(r"<item>(.*?)</item>", feed_text, re.DOTALL)
    if not item_blocks:
        # Try Atom <entry> blocks
        item_blocks = re.findall(r"<entry>(.*?)</entry>", feed_text, re.DOTALL)

    for block in item_blocks[:20]:
        title_m = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        link_m = re.search(r"<link[^>]*>(?:<!\[CDATA\[)?(https?://[^\s<]+?)(?:\]\]>)?</link>", block, re.DOTALL)
        if not link_m:
            link_m = re.search(r'<link[^>]+href=["\']([^"\']+)["\']', block, re.DOTALL)
        if title_m and link_m:
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
            url = link_m.group(1).strip()
            if title and url:
                items.append({"title": title, "url": url})
    return items


def fetch_rss_items(source: Dict[str, str]) -> List[Dict[str, str]]:
    """Fetch and parse RSS feed. Returns list of {title, url}."""
    try:
        resp = requests.get(source["url"], timeout=REQUEST_TIMEOUT, headers={
            "User-Agent": "ProtocolPulse/1.0 Mining Intel Monitor"
        })
        resp.raise_for_status()
        items = _parse_rss(resp.text)
        logger.info("RSS %s → %d items", source["name"], len(items))
        return items
    except requests.exceptions.RequestException as e:
        logger.warning("RSS fetch failed for %s: %s", source["name"], e)
        return []


# ── Live data fetcher ──────────────────────────────────────────────────────────

def fetch_live_mining_data() -> Dict[str, Any]:
    """
    Fetch live mining metrics from mempool.space and CoinGecko.
    Returns dict with all key stats. All fields gracefully fall back to None.
    """
    data: Dict[str, Any] = {
        "hashrate_eh": None,
        "difficulty": None,
        "next_adjustment_pct": None,
        "blocks_until_adjustment": None,
        "btc_price_usd": None,
        "block_height": None,
        "hash_price_usd_per_ph": None,
        "block_reward_btc": 3.125,
        "mempool_fee_low": None,
        "mempool_fee_mid": None,
        "mempool_fee_high": None,
    }

    # Hashrate + difficulty
    try:
        r = requests.get(
            "https://mempool.space/api/v1/mining/hashrate/1m",
            timeout=REQUEST_TIMEOUT,
        )
        if r.ok:
            d = r.json()
            raw = d.get("currentHashrate") or 0
            data["hashrate_eh"] = round(raw / 1e18, 2) if raw else None
            data["difficulty"] = d.get("currentDifficulty")
    except Exception as e:
        logger.warning("Hashrate fetch error: %s", e)

    # Difficulty adjustment
    try:
        r = requests.get(
            "https://mempool.space/api/v1/difficulty-adjustment",
            timeout=REQUEST_TIMEOUT,
        )
        if r.ok:
            d = r.json()
            data["next_adjustment_pct"] = round(d.get("difficultyChange", 0), 2)
            data["blocks_until_adjustment"] = d.get("remainingBlocks")
    except Exception as e:
        logger.warning("Difficulty adjustment fetch error: %s", e)

    # Block height
    try:
        r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=REQUEST_TIMEOUT)
        if r.ok:
            data["block_height"] = int(r.text.strip())
    except Exception as e:
        logger.warning("Block height fetch error: %s", e)

    # BTC price (CoinGecko)
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=REQUEST_TIMEOUT,
        )
        if r.ok:
            data["btc_price_usd"] = r.json().get("bitcoin", {}).get("usd")
    except Exception as e:
        logger.warning("BTC price fetch error: %s", e)

    # Hash price = (block_reward * btc_price * 144) / network_hashrate_PH
    if data["hashrate_eh"] and data["btc_price_usd"]:
        hashrate_ph = data["hashrate_eh"] * 1e6  # EH → PH
        daily_btc = data["block_reward_btc"] * 144
        data["hash_price_usd_per_ph"] = round(
            (daily_btc * data["btc_price_usd"]) / hashrate_ph, 4
        )

    # Mempool fee rates
    try:
        r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=REQUEST_TIMEOUT)
        if r.ok:
            fees = r.json()
            data["mempool_fee_low"] = fees.get("economyFee")
            data["mempool_fee_mid"] = fees.get("halfHourFee")
            data["mempool_fee_high"] = fees.get("fastestFee")
    except Exception as e:
        logger.warning("Mempool fees fetch error: %s", e)

    return data


# ── Article generator ──────────────────────────────────────────────────────────

def _build_article_prompt(
    topic_title: str,
    source_name: str,
    live_data: Dict[str, Any],
) -> str:
    hashrate = f"{live_data['hashrate_eh']} EH/s" if live_data.get("hashrate_eh") else "unknown EH/s"
    difficulty = f"{live_data['difficulty']:,.0f}" if live_data.get("difficulty") else "unknown"
    btc_price = f"${live_data['btc_price_usd']:,.0f}" if live_data.get("btc_price_usd") else "unknown"
    hash_price = f"${live_data['hash_price_usd_per_ph']:.4f}/PH/day" if live_data.get("hash_price_usd_per_ph") else "unknown"
    adj_pct = f"{live_data['next_adjustment_pct']:+.1f}%" if live_data.get("next_adjustment_pct") is not None else "unknown"
    height = f"{live_data['block_height']:,}" if live_data.get("block_height") else "unknown"

    return f"""You are the editorial intelligence of Protocol Pulse — a cypherpunk Bitcoin media brand.

Write an original, authoritative 800-1200 word Bitcoin mining analysis article for Protocol Pulse.

TOPIC INSPIRATION (do NOT copy — write your own ORIGINAL analysis inspired by this theme):
"{topic_title}" (from {source_name})

LIVE ON-CHAIN DATA to include naturally in your analysis (use exact numbers):
- Network Hashrate: {hashrate}
- Mining Difficulty: {difficulty}
- BTC Price: {btc_price}
- Hash Price: {hash_price} (USD per PH/day — the key miner profitability metric)
- Next Difficulty Adjustment: {adj_pct}
- Block Height: {height}
- Block Subsidy: 3.125 BTC per block

VOICE: Protocol Pulse cypherpunk — authoritative, precise, slightly adversarial toward legacy finance.
Not sensationalist. Data-first. This is for serious miners and mining investors, not retail.

STRUCTURE:
- Opening: 1-2 sentence hook (no AI clichés — no "in the rapidly evolving landscape")
- Analysis body: 3-4 paragraphs weaving live data into contextual analysis
- Mining implications: What this means for small-scale vs institutional miners
- Protocol Pulse perspective: 1 paragraph of original editorial stance
- Closing: Forward-looking statement (not prediction — framed as "watch for")

RULES:
- Include current hashrate, difficulty, BTC price, and hash price organically in the article
- No plagiarism — this is ORIGINAL Protocol Pulse content
- No stock image references — visuals are handled separately
- No affiliate links, no promotional language
- Return ONLY the article as markdown — title (H1) then body paragraphs
- Do not include meta-commentary like "Here is the article:"
- Do not include a byline or date"""


def generate_article_from_topic(
    topic_title: str,
    source_name: str,
    live_data: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    Call Claude Sonnet to generate an original mining article.
    Returns dict with title, content, summary, tags — or None on failure.
    """
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set — cannot generate article")
        return None

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = _build_article_prompt(topic_title, source_name, live_data)

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        article_text = message.content[0].text.strip()

        # Extract title (first H1) and body
        lines = article_text.split("\n")
        title = topic_title  # fallback
        body_lines = []
        for i, line in enumerate(lines):
            if line.startswith("# "):
                title = line[2:].strip()
                body_lines = lines[i + 1 :]
                break
        else:
            body_lines = lines

        body = "\n".join(body_lines).strip()
        summary = " ".join(body.replace("#", "").split()[:40]) + "..."

        return {
            "title": title,
            "content": article_text,
            "summary": summary,
            "tags": "bitcoin,mining,hashrate,difficulty,asic",
        }

    except anthropic.APIError as e:
        logger.error("Anthropic API error generating mining article: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error generating mining article: %s", e)
        return None


# ── Activity log helper ────────────────────────────────────────────────────────

def _log_activity(conn: sqlite3.Connection, message: str) -> None:
    """Write to activity_log table if it exists."""
    try:
        conn.execute(
            "INSERT OR IGNORE INTO activity_log (event_type, description, created_at) VALUES (?, ?, ?)",
            ("mining_intel", message, datetime.utcnow().isoformat()),
        )
        conn.commit()
    except Exception:
        pass  # activity_log table may not exist — that's fine


# ── Main runner ────────────────────────────────────────────────────────────────

def run_monitor() -> int:
    """
    Main entry point. Checks RSS feeds, generates articles for new items.
    Returns count of articles generated.
    """
    logger.info("Mining Intel Monitor starting...")
    conn = _get_db_conn()
    _ensure_seen_table(conn)

    # Fetch live data once (shared across all articles this run)
    logger.info("Fetching live mining data...")
    live_data = fetch_live_mining_data()
    logger.info(
        "Live data: hashrate=%.1f EH/s, price=$%s, hash_price=$%s/PH/day",
        live_data.get("hashrate_eh") or 0,
        f"{live_data.get('btc_price_usd', 0):,.0f}" if live_data.get("btc_price_usd") else "N/A",
        f"{live_data.get('hash_price_usd_per_ph', 0):.4f}" if live_data.get("hash_price_usd_per_ph") else "N/A",
    )

    articles_generated = 0

    for source in RSS_SOURCES:
        if articles_generated >= MAX_ARTICLES_PER_RUN:
            logger.info("Reached max articles per run (%d), stopping.", MAX_ARTICLES_PER_RUN)
            break

        items = fetch_rss_items(source)
        for item in items:
            if articles_generated >= MAX_ARTICLES_PER_RUN:
                break

            url = item["url"]
            title = item["title"]

            if _is_seen(conn, url):
                continue

            logger.info("New item from %s: %s", source["name"], title[:80])

            # Generate article
            article_data = generate_article_from_topic(title, source["name"], live_data)

            article_id: Optional[int] = None
            if article_data:
                try:
                    article_id = _save_article(
                        conn,
                        article_data["title"],
                        article_data["content"],
                        article_data["summary"],
                        article_data["tags"],
                    )
                    articles_generated += 1
                    logger.info(
                        "Article #%d saved: %s", article_id, article_data["title"][:60]
                    )
                    _log_activity(
                        conn,
                        f"Mining article generated from '{source['name']}': {article_data['title'][:80]}",
                    )
                except Exception as e:
                    logger.error("Failed to save article: %s", e)
                    conn.rollback()

            # Mark as seen regardless (even if article generation failed, don't retry same URL)
            _mark_seen(conn, url, title, source["name"], article_id)

            # Brief pause between Claude API calls
            if articles_generated < MAX_ARTICLES_PER_RUN:
                time.sleep(2)

    conn.close()
    logger.info("Mining Intel Monitor complete. Articles generated: %d", articles_generated)
    return articles_generated


if __name__ == "__main__":
    count = run_monitor()
    sys.exit(0 if count >= 0 else 1)
