#!/usr/bin/env python3
"""
Mining Intel Scheduler — Orchestrator
=======================================
Main entry point for the Mining Intel pipeline.
Fetches data, extracts intelligence, generates articles,
fact-checks with Grok, and publishes to Protocol Pulse.

Usage:
    python3 mining_intel_scheduler.py              # Normal run (needs new newsletter)
    python3 mining_intel_scheduler.py --test       # Generate but do NOT publish
    python3 mining_intel_scheduler.py --force      # Generate even without new newsletter
    python3 mining_intel_scheduler.py --test --force  # Test with forced generation
    python3 mining_intel_scheduler.py --snapshot-only  # Daily snapshot (no newsletter needed)
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Ensure we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from newsletter_monitor import (
    check_for_new_newsletter,
    fetch_mempool_data,
    fetch_btc_price,
    fetch_fear_greed_index,
    fetch_mining_pools,
    gather_all_data
)
from data_extractor import extract_from_newsletter, enrich_with_live_data
from article_generator import generate_article, generate_snapshot_article
from publisher import fetch_pexels_cover, fact_check_with_grok, check_duplicate, publish_article

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("mining_intel")


def run(test: bool = False, force: bool = False, snapshot_only: bool = False):
    """
    Main pipeline orchestrator.

    Args:
        test: If True, generate article but do NOT publish. Save to output/
        force: If True, generate even without a new newsletter
        snapshot_only: If True, generate a short snapshot using live data only
    """
    start = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info(f"Mining Intel Pipeline — {start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"Mode: {'TEST' if test else 'LIVE'} | Force: {force} | Snapshot: {snapshot_only}")
    logger.info("=" * 60)

    # ── Step 1: Gather data ──────────────────────────────────────
    logger.info("Step 1: Gathering mining data...")

    if snapshot_only:
        # Snapshot mode: skip newsletter, just use live data
        newsletter = None
        mempool = fetch_mempool_data()
        btc_price = fetch_btc_price()
        fng = fetch_fear_greed_index()
        pools = fetch_mining_pools()
    else:
        # Full mode: check for newsletter + live data
        newsletter = check_for_new_newsletter()
        if not newsletter and not force:
            logger.info("No new Blockware newsletter. Use --force to generate anyway.")
            logger.info("Tip: Use --snapshot-only for a daily update without newsletter.")
            return None

        mempool = fetch_mempool_data()
        btc_price = fetch_btc_price()
        fng = fetch_fear_greed_index()
        pools = fetch_mining_pools()

    logger.info(f"  Newsletter: {'YES — ' + (newsletter or {}).get('title', '') if newsletter else 'None'}")
    logger.info(f"  BTC Price: ${btc_price.get('usd', 0):,.0f}")
    logger.info(f"  Hashrate: {mempool.get('hashrate', {}).get('ehs', '?')} EH/s")
    logger.info(f"  Fear & Greed: {fng.get('value', '?')} ({fng.get('classification', '?')})")

    # ── Step 2: Extract intelligence ─────────────────────────────
    logger.info("Step 2: Extracting intelligence...")

    if newsletter:
        extracted = extract_from_newsletter(newsletter)
        logger.info(f"  Extracted {len(extracted.get('key_insights', []))} insights from newsletter")
    else:
        extracted = {
            "metrics": {},
            "key_insights": [],
            "market_structure": {},
            "notable_events": [],
            "data_quality": "low",
            "source": None
        }

    intel = enrich_with_live_data(extracted, mempool, btc_price, fng, pools)
    logger.info(f"  Data quality: {intel.get('data_quality', 'unknown')}")

    # ── Step 3: Generate article ─────────────────────────────────
    logger.info("Step 3: Generating article...")

    if snapshot_only:
        article = generate_snapshot_article(intel)
    else:
        article = generate_article(intel)

    if not article:
        logger.error("Article generation FAILED — aborting")
        return None

    logger.info(f"  Title: {article['title']}")
    logger.info(f"  Words: {article.get('word_count', '?')}")

    # ── Step 4: Fetch cover image ────────────────────────────────
    logger.info("Step 4: Fetching cover image from Pexels...")

    cover_query = article.get("cover_image_query", "bitcoin mining facility")
    cover_url = fetch_pexels_cover(cover_query)
    article["cover_image_url"] = cover_url
    logger.info(f"  Cover: {cover_url[:80]}...")

    # ── Step 5: Duplicate check ──────────────────────────────────
    logger.info("Step 5: Checking for duplicates...")

    if check_duplicate(article["title"]):
        logger.warning("Duplicate detected — aborting to prevent repeat content")
        if test:
            logger.info("(Test mode — saving anyway for review)")
        else:
            return None

    # ── Step 6: Grok fact-check ──────────────────────────────────
    logger.info("Step 6: Fact-checking with Grok...")

    article = fact_check_with_grok(article)
    fc = article.get("fact_check_result", {})
    logger.info(f"  Decision: {fc.get('decision', 'UNKNOWN')} (score: {fc.get('score', 0)})")

    if fc.get("critical_errors"):
        for err in fc["critical_errors"]:
            logger.warning(f"  CRITICAL: {err}")

    if not fc.get("approved", False) and fc.get("decision") != "SKIP":
        logger.warning("Article REJECTED by Grok fact-check")
        if not test:
            # Save rejected article for manual review
            reject_file = OUTPUT_DIR / f"rejected_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            reject_file.write_text(json.dumps(article, indent=2, default=str))
            logger.info(f"  Saved rejected article to {reject_file}")
            return None

    # ── Step 7: Publish or save ──────────────────────────────────
    if test:
        logger.info("Step 7: TEST MODE — saving to output/ (not publishing)")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_file = OUTPUT_DIR / f"test_mining_intel_{ts}.json"
        out_file.write_text(json.dumps(article, indent=2, default=str))
        logger.info(f"  Saved: {out_file}")

        # Print article summary
        print("\n" + "=" * 60)
        print("MINING INTEL — TEST OUTPUT")
        print("=" * 60)
        print(f"Title: {article['title']}")
        print(f"Subtitle: {article.get('subtitle', '')}")
        print(f"Category: {article.get('category', '')}")
        print(f"Tags: {article.get('tags', [])}")
        print(f"Words: {article.get('word_count', '?')}")
        print(f"Cover: {article.get('cover_image_url', 'N/A')}")
        print(f"Sources: {article.get('sources', [])}")
        print(f"Fact-check: {fc.get('decision', 'N/A')} (score: {fc.get('score', 0)})")
        print(f"SEO Title: {article.get('seo_title', '')}")
        print(f"SEO Desc: {article.get('seo_description', '')}")
        print("-" * 60)
        # Print first 2000 chars of body
        body = article.get("body_html", "")
        print(body[:2000])
        if len(body) > 2000:
            print(f"\n... [{len(body) - 2000} more characters]")
        print("=" * 60)
    else:
        logger.info("Step 7: Publishing to Protocol Pulse...")
        result = publish_article(article)
        if result.get("success"):
            logger.info(f"  Published successfully! Article ID: {result.get('article_id', 'N/A')}")
        else:
            logger.error(f"  Publish FAILED: {result.get('error', 'Unknown')}")
            # Save for retry
            fail_file = OUTPUT_DIR / f"failed_publish_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            fail_file.write_text(json.dumps(article, indent=2, default=str))
            logger.info(f"  Saved for retry: {fail_file}")

    # ── Done ─────────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"Pipeline complete in {elapsed:.1f}s")

    return article


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mining Intel Pipeline")
    parser.add_argument("--test", action="store_true", help="Generate but do not publish")
    parser.add_argument("--force", action="store_true", help="Generate even without new newsletter")
    parser.add_argument("--snapshot-only", action="store_true", help="Daily snapshot (live data only)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        handlers=[logging.StreamHandler()]
    )

    result = run(test=args.test, force=args.force, snapshot_only=args.snapshot_only)
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
