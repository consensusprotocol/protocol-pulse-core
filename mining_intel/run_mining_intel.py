#!/usr/bin/env python3
"""
Mining Intel Pipeline — Multi-Source Orchestrator
===================================================
Fetches mining intel from Blockware Intelligence, Hashrate Index, and
Compass Mining RSS feeds. Generates PP-style articles via Claude API.
Publishes to Protocol Pulse database.

Usage:
    python3 run_mining_intel.py                # Full pipeline: fetch → generate → publish
    python3 run_mining_intel.py --dry-run      # Fetch + generate, do NOT publish
    python3 run_mining_intel.py --dry-run -v   # Verbose dry run
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Ensure sibling imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetcher import fetch_all, mark_processed
from newsletter_monitor import fetch_mempool_data, fetch_btc_price, fetch_fear_greed_index, fetch_mining_pools

BASE_DIR = Path(__file__).parent
LOG_DIR = Path.home() / "protocol_pulse" / "logs"
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("mining_intel")


def _get_anthropic_key() -> str:
    """Resolve Anthropic API key from env or oracle_briefing .env."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    # Fallback: read from oracle_briefing .env
    env_file = Path.home() / "protocol_pulse" / "oracle_briefing" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def _generate_article_from_posts(posts: list[dict], mempool: dict, btc_price: dict,
                                  fng: dict, pools: dict) -> dict | None:
    """
    Use Claude API to generate a PP-style Mining Intel article
    from fetched post metadata + scraped content.
    """
    import requests as req

    api_key = _get_anthropic_key()
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found — cannot generate article")
        return None

    # Build source material block
    source_blocks = []
    for p in posts:
        block = f"### {p['title']}\n"
        block += f"Source: {p['source_name']} | Date: {p['published_date'][:10]}\n"
        block += f"URL: {p['url']}\n"
        if p.get("full_text"):
            text = p["full_text"][:4000]
            block += f"\nContent:\n{text}\n"
        elif p.get("summary"):
            block += f"\nSummary: {p['summary']}\n"
        source_blocks.append(block)

    sources_text = "\n---\n".join(source_blocks)
    source_names = list({p["source_name"] for p in posts})

    # Live data block
    live_lines = []
    hr = mempool.get("hashrate", {})
    if hr.get("ehs"):
        live_lines.append(f"- Network Hashrate: {hr['ehs']} EH/s")
    diff = mempool.get("difficulty", {})
    if diff.get("trillion"):
        live_lines.append(f"- Difficulty: {diff['trillion']}T")
    adj = mempool.get("difficulty_adjustment", {})
    if adj.get("estimated_change_pct") is not None:
        live_lines.append(f"- Next Difficulty Adjustment: {adj['estimated_change_pct']:+.2f}%")
    if adj.get("remaining_blocks"):
        live_lines.append(f"- Blocks Until Adjustment: {adj['remaining_blocks']}")
    fees = mempool.get("avg_fee", {})
    if fees.get("hour"):
        live_lines.append(f"- Avg Fee: {fees['hour']} sat/vB (fastest: {fees.get('fastest', '?')})")
    mp = mempool.get("mempool_size", {})
    if mp.get("count"):
        live_lines.append(f"- Mempool: {mp['count']:,} unconfirmed txs")
    live_data_text = "\n".join(live_lines) if live_lines else "No live data available"

    # Pool data
    pool_lines = []
    for p in pools.get("pools", [])[:7]:
        pool_lines.append(f"- {p['name']}: {p['blocks']} blocks ({p['share_pct']}%)")
    pools_text = "\n".join(pool_lines) if pool_lines else "No pool data"

    system_prompt = """You are a senior Bitcoin mining analyst writing for Protocol Pulse — a Bitcoin intelligence platform read by sophisticated miners, traders, and institutional investors.

VOICE: Sharp, analytical, slightly provocative. Data-first. No hand-holding, no "what is Bitcoin mining." Your readers run mining operations, manage hashrate, and trade based on mining economics.

STYLE RULES:
- Lead with the most surprising or important data point
- Every claim backed by a specific number
- Include at least one insight the source data DIDN'T explicitly state
- Reference Protocol Pulse's own perspective
- Mention data sources naturally: "According to Blockware Intelligence..." or "Hashrate Index data shows..."
- NEVER copy sentences from source articles — write ORIGINAL analysis
- Connect mining metrics to broader market implications
- Focus: hashrate trends, miner economics, ASIC market, energy costs, post-halving dynamics

MANDATORY 6-SECTION STRUCTURE:
1. <div class="tldr-section"><h3>TL;DR</h3><ul><li>Bullet 1</li><li>Bullet 2</li><li>Bullet 3</li></ul></div>
2. <h2>The Report</h2> — Lead with key data, 300-400 words
3. <h2>Exclusive Data Analysis</h2> — Mining economics deep-dive, 100-200 words
4. <h2>The Bitcoin Lens</h2> — Sovereignty/freedom angle on mining, 80-120 words
5. <h2>Transactor Intelligence</h2> — Actionable insights for miners and traders, 80-100 words
6. <h2>Sources</h2> — List of data sources used with links

TARGET: 500-700 words total. Cite original sources."""

    user_prompt = f"""Write a "Mining Intel" article for Protocol Pulse based on the following source material.

TODAY'S DATE: {datetime.now(timezone.utc).strftime("%B %d, %Y")}

=== SOURCE MATERIAL ({len(posts)} articles from {', '.join(source_names)}) ===
{sources_text}

=== VERIFIED LIVE NETWORK DATA ===
{live_data_text}

=== MARKET CONTEXT ===
- BTC Price: ${btc_price.get('usd', 0):,.0f} ({btc_price.get('change_24h_pct', 0):+.1f}% 24h)
- Fear & Greed Index: {fng.get('value', 50)} ({fng.get('classification', 'Neutral')})
- Block Height: {mempool.get('block_height', 'N/A'):,}

=== TOP MINING POOLS (7-day) ===
{pools_text}

REQUIREMENTS:
1. Headline: Punchy, specific, number-driven. Max 80 characters.
2. Body: Full HTML article in the 6-section structure. 500-700 words.
3. Category: "Mining Intel"
4. ALWAYS cite original source by name and include source URLs
5. Include current hashrate context and difficulty context
6. Tags: relevant mining topics

Respond in JSON:
{{
    "title": "Headline",
    "body": "Full HTML article (all 6 sections)",
    "tags": ["mining", "hashrate", ...],
    "source_url": "primary source URL",
    "category": "Mining Intel",
    "seo_title": "SEO title (max 60 chars)",
    "seo_description": "SEO description (max 155 chars)",
    "cover_image_query": "Pexels search query for cover image"
}}"""

    try:
        resp = req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 4000,
                "temperature": 0.7,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=90,
        )

        if resp.status_code != 200:
            logger.error(f"Claude API error: {resp.status_code} {resp.text[:300]}")
            return None

        content_text = resp.json()["content"][0]["text"]

        # Parse JSON from response
        if "```" in content_text:
            content_text = content_text.split("```")[1]
            if content_text.startswith("json"):
                content_text = content_text[4:]
            content_text = content_text.strip()

        article = json.loads(content_text)

        # Validate
        if not article.get("title") or not article.get("body"):
            logger.error("Generated article missing title or body")
            return None

        word_count = len(article["body"].split())
        article["word_count"] = word_count
        article["generated_at"] = datetime.now(timezone.utc).isoformat()
        article.setdefault("tags", ["mining", "hashrate"])
        article.setdefault("category", "Mining Intel")
        article.setdefault("cover_image_query", "bitcoin mining facility")

        logger.info(f"Generated: '{article['title']}' ({word_count} words)")
        return article

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Article generation error: {e}")
        return None


def _fetch_pexels_cover(query: str) -> str:
    """Fetch a cover image from Pexels API."""
    import hashlib
    api_key = os.environ.get("PEXELS_API_KEY", "")
    fallback = "https://images.pexels.com/photos/844124/pexels-photo-844124.jpeg?auto=compress&cs=tinysrgb&h=650&w=940"

    if not api_key:
        # Try relay
        try:
            from relay import get_key
            api_key = get_key("PEXELS_API_KEY")
        except Exception:
            pass

    if not api_key:
        logger.warning("PEXELS_API_KEY not available — using fallback image")
        return fallback

    try:
        import requests as req
        r = req.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
            headers={"Authorization": api_key},
            timeout=10,
        )
        photos = r.json().get("photos", [])
        if photos:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            idx = int(hashlib.md5(today.encode()).hexdigest(), 16) % len(photos)
            return photos[idx]["src"]["large"]
    except Exception as e:
        logger.warning(f"Pexels fetch failed: {e}")

    return fallback


def _publish_to_db(article: dict) -> dict:
    """Publish article to Protocol Pulse DB via Replit relay."""
    try:
        from relay import run as relay_run
        import base64

        title = article.get("title", "")
        body = article.get("body", "")
        tags = ",".join(article.get("tags", ["mining"]))
        cover_url = article.get("cover_image_url", "")
        seo_title = article.get("seo_title", title[:60])
        seo_desc = article.get("seo_description", "")[:155]
        source_url = article.get("source_url", "")

        script = f"""
import json, sys
sys.path.insert(0, '.')
from app import app, db
from models import Article
from datetime import datetime

with app.app_context():
    a = Article(
        title={json.dumps(title)},
        content={json.dumps(body)},
        summary="",
        author="Protocol Pulse Intelligence",
        category="Mining Intel",
        tags={json.dumps(tags)},
        source_url={json.dumps(source_url)},
        source_type="mining_intel",
        published=True,
        published_at=datetime.utcnow(),
        cover_image_url={json.dumps(cover_url)},
        seo_title={json.dumps(seo_title)},
        seo_description={json.dumps(seo_desc)}
    )
    db.session.add(a)
    db.session.commit()
    print(json.dumps({{"id": a.id, "title": a.title, "published": True}}))
"""
        script_b64 = base64.b64encode(script.encode()).decode()
        cmd = f"python3 -c \"import base64;exec(base64.b64decode('{script_b64}').decode())\""
        result = relay_run(cmd, timeout=30)

        if result:
            try:
                pub = json.loads(result)
                logger.info(f"Published article #{pub.get('id')}: {pub.get('title')}")
                return {"success": True, "article_id": pub.get("id"), "result": pub}
            except json.JSONDecodeError:
                if result.strip():
                    return {"success": True, "result": result}

        logger.error(f"Publish failed — relay returned: {result}")
        return {"success": False, "error": result or "Empty relay response"}

    except Exception as e:
        logger.error(f"Publish error: {e}")
        return {"success": False, "error": str(e)}


def run_pipeline(dry_run: bool = False, verbose: bool = False):
    """
    Full pipeline: fetch → generate → publish.
    """
    start = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info(f"Mining Intel Pipeline — {start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE PUBLISH'}")
    logger.info("=" * 60)

    # ── Step 1: Fetch RSS sources ──────────────────────────────
    logger.info("Step 1: Fetching RSS sources (last 7 days)...")
    posts = fetch_all(days=7)

    if not posts:
        logger.info("No new posts found across all sources. Nothing to do.")
        return None

    logger.info(f"  Found {len(posts)} new posts:")
    for p in posts:
        logger.info(f"    [{p['source_name']}] {p['title'][:60]}")

    # ── Step 2: Fetch live network data ────────────────────────
    logger.info("Step 2: Fetching live network data...")
    mempool = fetch_mempool_data()
    btc_price = fetch_btc_price()
    fng = fetch_fear_greed_index()
    pools = fetch_mining_pools()

    logger.info(f"  BTC: ${btc_price.get('usd', 0):,.0f}")
    logger.info(f"  Hashrate: {mempool.get('hashrate', {}).get('ehs', '?')} EH/s")
    logger.info(f"  Difficulty: {mempool.get('difficulty', {}).get('trillion', '?')}T")
    logger.info(f"  Fear & Greed: {fng.get('value', '?')} ({fng.get('classification', '?')})")

    # ── Step 3: Generate article ───────────────────────────────
    logger.info("Step 3: Generating Mining Intel article via Claude...")
    article = _generate_article_from_posts(posts, mempool, btc_price, fng, pools)

    if not article:
        logger.error("Article generation FAILED — aborting")
        return None

    logger.info(f"  Title: {article['title']}")
    logger.info(f"  Words: {article.get('word_count', '?')}")

    # ── Step 4: Cover image ────────────────────────────────────
    logger.info("Step 4: Fetching cover image...")
    query = article.get("cover_image_query", "bitcoin mining facility")
    article["cover_image_url"] = _fetch_pexels_cover(query)
    logger.info(f"  Cover: {article['cover_image_url'][:80]}...")

    # ── Step 5: Publish or dry-run ─────────────────────────────
    if dry_run:
        logger.info("Step 5: DRY RUN — saving to output/ (not publishing)")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_file = OUTPUT_DIR / f"dryrun_mining_intel_{ts}.json"
        out_file.write_text(json.dumps(article, indent=2, default=str))
        logger.info(f"  Saved: {out_file}")

        print("\n" + "=" * 60)
        print("MINING INTEL — DRY RUN OUTPUT")
        print("=" * 60)
        print(f"Title: {article['title']}")
        print(f"Category: {article.get('category', '')}")
        print(f"Tags: {article.get('tags', [])}")
        print(f"Words: {article.get('word_count', '?')}")
        print(f"Cover: {article.get('cover_image_url', 'N/A')}")
        print(f"Source URL: {article.get('source_url', 'N/A')}")
        print(f"SEO Title: {article.get('seo_title', '')}")
        print(f"SEO Desc: {article.get('seo_description', '')}")
        print("-" * 60)
        body = article.get("body", "")
        print(body[:2000])
        if len(body) > 2000:
            print(f"\n... [{len(body) - 2000} more characters]")
        print("=" * 60)

        # Still mark URLs as processed to avoid re-fetching
        mark_processed([p["url"] for p in posts])
    else:
        logger.info("Step 5: Publishing to Protocol Pulse...")
        result = _publish_to_db(article)
        if result.get("success"):
            logger.info(f"  Published! Article ID: {result.get('article_id', 'N/A')}")
            mark_processed([p["url"] for p in posts])
        else:
            logger.error(f"  Publish FAILED: {result.get('error', 'Unknown')}")
            # Save for retry
            fail_file = OUTPUT_DIR / f"failed_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            fail_file.write_text(json.dumps(article, indent=2, default=str))
            logger.info(f"  Saved for retry: {fail_file}")
            return None

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"Pipeline complete in {elapsed:.1f}s")
    return article


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mining Intel Pipeline — Multi-Source")
    parser.add_argument("--dry-run", action="store_true", help="Fetch + generate, do NOT publish")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO

    # File + console logging
    log_file = LOG_DIR / "mining_intel.log"
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(log_file, mode="a"),
    ]
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        handlers=handlers,
    )

    logger.info(f"Logging to {log_file}")
    result = run_pipeline(dry_run=args.dry_run, verbose=args.verbose)
    sys.exit(0 if result else 1)
