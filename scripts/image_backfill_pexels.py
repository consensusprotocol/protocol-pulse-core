#!/usr/bin/env python3
"""
Protocol Pulse — Article Image Backfill (Pexels)
Finds articles with NULL cover_image_url and assigns Pexels stock photos.
Articles with named people/brands are logged separately for Grok processing.

Usage: python3 scripts/image_backfill_pexels.py
"""

import os
import re
import sys
import json
import time
import hashlib
import logging
import requests
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "zS71r9kFEhJTBw4ugRVfYH0phEyT8hfMOXxIb1BlwRniyvLWMlK3c7Dc")
REPLIT_RELAY_URL = "https://protocolpulse.replit.app/api/admin/exec"
REPLIT_TOKEN = "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"

RATE_LIMIT_DELAY = 2.0  # seconds between Pexels API calls
BATCH_SIZE = 20          # articles per relay DB update call

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ─── LOGGING ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "image_backfill.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("image_backfill")

# ─── GROK CANDIDATE DETECTION ────────────────────────────────────────
TOP_ARTICLE_INDICATORS = [
    'michael saylor', 'saylor', 'elon musk', 'trump', 'biden', 'powell',
    'gensler', 'blackrock', 'fidelity', 'jpmorgan', 'goldman sachs',
    'sec ', 'fed ', 'federal reserve', 'congress', 'senate', 'white house',
    'breaking:', 'exclusive:', 'just in:',
]

def is_grok_candidate(title):
    """Check if article has named people/brands → needs Grok, not Pexels."""
    lower = title.lower()
    return any(indicator in lower for indicator in TOP_ARTICLE_INDICATORS)

# ─── PEXELS QUERY BUILDER ────────────────────────────────────────────
TOPIC_QUERIES = {
    'mining': ['bitcoin mining facility', 'data center servers'],
    'hashrate': ['data center computing', 'server rack technology'],
    'hash rate': ['data center computing', 'server rack technology'],
    'etf': ['stock market trading floor', 'wall street financial'],
    'regulation': ['government capitol building', 'legal gavel courtroom'],
    'lightning': ['digital network connections', 'fiber optic cables'],
    'defi': ['blockchain technology abstract', 'digital finance network'],
    'whale': ['financial trading screens', 'stock market data'],
    'fed ': ['federal reserve building', 'monetary policy finance'],
    'inflation': ['economic charts data', 'currency money finance'],
    'adoption': ['global technology innovation', 'digital transformation'],
    'security': ['cybersecurity digital lock', 'encrypted data protection'],
    'energy': ['renewable energy solar', 'power grid electricity'],
    'ai ': ['artificial intelligence technology', 'futuristic computer'],
    'quantum': ['quantum computing technology', 'advanced processor chip'],
    'cbdc': ['central bank digital', 'government finance technology'],
    'halving': ['bitcoin gold scarcity', 'precious metals vault'],
    'difficulty': ['data center technology', 'computer processing power'],
    'miner': ['bitcoin mining facility', 'industrial computing hardware'],
    'exodus': ['migration journey', 'transition change movement'],
    'capitulation': ['financial crisis market', 'economic downturn graph'],
    'network': ['digital network abstract', 'connected technology nodes'],
    'resilience': ['strength endurance abstract', 'fortress architecture'],
    'wall street': ['wall street new york', 'stock exchange trading'],
    'surge': ['financial growth chart', 'upward trend markets'],
    'bull': ['bull market finance', 'stock market rally green'],
    'crisis': ['financial crisis market', 'economic turmoil abstract'],
    'war': ['geopolitical conflict map', 'military defense strategy'],
    'oil': ['oil barrel petroleum', 'energy industry pipeline'],
    'strait': ['ocean shipping vessels', 'maritime trade route'],
}

CATEGORY_QUERIES = {
    'bitcoin': 'cryptocurrency digital technology dark',
    'breakingbitcoin': 'cryptocurrency digital technology dark',
    'opinion': 'editorial newspaper analysis',
    'sentiment': 'social media digital conversation',
    'macro': 'global economy financial markets',
}

FALLBACK_QUERIES = [
    'financial technology dark',
    'digital economy abstract',
    'modern technology dark background',
]

def build_pexels_queries(title, category):
    """Build search queries from title + category, most specific → most general."""
    queries = []
    lower = title.lower()

    for keyword, pexels_qs in TOPIC_QUERIES.items():
        if keyword in lower:
            queries.extend(pexels_qs)

    if category and category.lower() in CATEGORY_QUERIES:
        queries.append(CATEGORY_QUERIES[category.lower()])

    queries.extend(FALLBACK_QUERIES)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique[:5]

# ─── PEXELS API ──────────────────────────────────────────────────────
_query_cache = {}  # cache query → URL to avoid duplicate API calls

def fetch_pexels_url(title, category):
    """Fetch a Pexels image URL for the given article title."""
    queries = build_pexels_queries(title, category)

    for query in queries:
        # Check cache first
        if query in _query_cache:
            logger.info(f"  Cache hit: '{query}'")
            # Use title hash to pick different photo from cached results
            cached = _query_cache[query]
            if cached:
                idx = int(hashlib.md5(title.encode()).hexdigest()[:8], 16) % len(cached)
                return cached[idx]
            continue

        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={
                    "query": query,
                    "per_page": 15,
                    "orientation": "landscape",
                    "size": "large",
                },
                timeout=10,
            )

            if resp.status_code == 429:
                logger.warning("Rate limited by Pexels — waiting 60s")
                time.sleep(60)
                continue

            if resp.status_code != 200:
                logger.warning(f"  Pexels {resp.status_code} for '{query}'")
                continue

            photos = resp.json().get("photos", [])
            if not photos:
                logger.info(f"  No results for '{query}'")
                _query_cache[query] = []
                continue

            # Cache all photo URLs for this query
            urls = []
            for p in photos:
                url = p.get("src", {}).get("large2x") or p.get("src", {}).get("large")
                if url:
                    urls.append(url)

            _query_cache[query] = urls

            if urls:
                idx = int(hashlib.md5(title.encode()).hexdigest()[:8], 16) % len(urls)
                return urls[idx]

        except Exception as e:
            logger.error(f"  Pexels error for '{query}': {e}")
            continue

        finally:
            time.sleep(RATE_LIMIT_DELAY)

    return None

# ─── REPLIT RELAY ─────────────────────────────────────────────────────
def relay_exec(cmd, timeout=30):
    """Execute a command on Replit via relay."""
    try:
        resp = requests.post(
            REPLIT_RELAY_URL,
            json={"token": REPLIT_TOKEN, "cmd": cmd},
            timeout=timeout,
        )
        if resp.ok:
            data = resp.json()
            return data.get("stdout", "").strip(), data.get("returncode", -1)
        else:
            logger.error(f"Relay HTTP {resp.status_code}")
            return "", -1
    except Exception as e:
        logger.error(f"Relay error: {e}")
        return "", -1

def fetch_articles_needing_images():
    """Get list of articles with NULL cover_image_url from Replit DB."""
    cmd = (
        "python3 -c \""
        "from app import app, db; from models import Article; "
        "ctx=app.app_context(); ctx.push(); "
        "arts=Article.query.filter(Article.cover_image_url==None).order_by(Article.id).all(); "
        "[print(f'{a.id}|||{a.title}|||{a.category}') for a in arts]"
        "\""
    )
    stdout, rc = relay_exec(cmd, timeout=30)
    if rc != 0 and not stdout:
        logger.error("Failed to fetch articles from Replit")
        return []

    articles = []
    for line in stdout.strip().split("\n"):
        if "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) == 3:
            try:
                articles.append({
                    "id": int(parts[0].strip()),
                    "title": parts[1].strip(),
                    "category": parts[2].strip() if parts[2].strip() != "None" else None,
                })
            except ValueError:
                continue

    return articles

def batch_update_images(updates):
    """Batch update cover_image_url for multiple articles via single relay call."""
    if not updates:
        return True

    # Build Python script for batch update
    update_lines = []
    for article_id, image_url in updates:
        # Escape single quotes in URL
        safe_url = image_url.replace("'", "\\'")
        update_lines.append(
            f"db.session.execute(db.text(\\\"UPDATE articles SET cover_image_url='{safe_url}' WHERE id={article_id}\\\"))"
        )

    script = (
        "from app import app, db; "
        "ctx=app.app_context(); ctx.push(); "
        + "; ".join(update_lines)
        + "; db.session.commit(); "
        + f"print('Updated {len(updates)} articles')"
    )

    cmd = f'python3 -c "{script}"'
    stdout, rc = relay_exec(cmd, timeout=30)

    if "Updated" in stdout:
        logger.info(f"  DB batch update OK: {len(updates)} articles")
        return True
    else:
        logger.error(f"  DB batch update failed: {stdout}")
        return False

# ─── MAIN ─────────────────────────────────────────────────────────────
def main():
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Protocol Pulse — Image Backfill (Pexels)")
    logger.info("=" * 60)

    # Fetch articles
    logger.info("Fetching articles needing images from Replit DB...")
    articles = fetch_articles_needing_images()
    logger.info(f"Found {len(articles)} articles needing images")

    if not articles:
        logger.info("Nothing to do!")
        return

    # Separate Grok candidates
    grok_candidates = []
    pexels_articles = []
    for a in articles:
        if is_grok_candidate(a["title"]):
            grok_candidates.append(a)
        else:
            pexels_articles.append(a)

    logger.info(f"Pexels candidates: {len(pexels_articles)}")
    logger.info(f"Grok candidates: {len(grok_candidates)}")

    # Log Grok candidates
    grok_log_path = os.path.join(LOG_DIR, "image_backfill_grok.log")
    with open(grok_log_path, "a") as f:
        f.write(f"\n--- {datetime.now().isoformat()} ---\n")
        for a in grok_candidates:
            f.write(f"ID:{a['id']} | {a['title']} | {a['category']}\n")
            logger.info(f"  GROK → ID:{a['id']} {a['title'][:60]}")

    # Process Pexels articles
    success_count = 0
    fail_count = 0
    pending_updates = []

    for i, article in enumerate(pexels_articles):
        aid = article["id"]
        title = article["title"]
        category = article["category"]

        logger.info(f"[{i+1}/{len(pexels_articles)}] ID:{aid} — {title[:70]}")

        url = fetch_pexels_url(title, category)
        if url:
            pending_updates.append((aid, url))
            success_count += 1
            logger.info(f"  ✓ {url[:80]}...")
        else:
            fail_count += 1
            logger.warning(f"  ✗ No image found")

        # Batch commit every BATCH_SIZE articles
        if len(pending_updates) >= BATCH_SIZE:
            batch_update_images(pending_updates)
            pending_updates = []
            logger.info(f"--- Progress: {i+1}/{len(pexels_articles)} "
                        f"({(i+1)*100//len(pexels_articles)}%) ---")

    # Final batch
    if pending_updates:
        batch_update_images(pending_updates)

    # Also assign Pexels fallbacks to Grok candidates (temporary, until Grok runs)
    if grok_candidates:
        logger.info(f"\nAssigning temporary Pexels images to {len(grok_candidates)} Grok candidates...")
        grok_updates = []
        for a in grok_candidates:
            url = fetch_pexels_url(a["title"], a["category"])
            if url:
                grok_updates.append((a["id"], url))
                logger.info(f"  TEMP ID:{a['id']} → {url[:60]}...")
        if grok_updates:
            batch_update_images(grok_updates)
            success_count += len(grok_updates)

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"COMPLETE in {elapsed:.1f}s")
    logger.info(f"  Total processed: {len(articles)}")
    logger.info(f"  Pexels success:  {success_count}")
    logger.info(f"  Failed:          {fail_count}")
    logger.info(f"  Grok candidates: {len(grok_candidates)} (logged to {grok_log_path})")
    logger.info("=" * 60)

    # Write summary report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_articles": len(articles),
        "pexels_success": success_count,
        "failed": fail_count,
        "grok_candidates": len(grok_candidates),
        "grok_ids": [a["id"] for a in grok_candidates],
        "elapsed_seconds": round(elapsed, 1),
    }
    report_path = os.path.join(LOG_DIR, "image_backfill_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
