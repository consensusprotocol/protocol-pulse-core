#!/usr/bin/env python3
"""
run_scraper.py — X Spaces Scraper orchestrator for Protocol Pulse.

Pipeline: Find Spaces → Fetch Transcripts → Generate Articles → Publish

Usage:
    python3 run_scraper.py              # Full pipeline (publishes as drafts)
    python3 run_scraper.py --dry-run    # No publish, just log what it would do
    python3 run_scraper.py --publish    # Auto-publish (set published=True)
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from x_spaces_scraper.scraper import XSpacesScraper, SpaceInfo
from x_spaces_scraper.transcript_fetcher import fetch_transcript
from x_spaces_scraper.article_generator import generate_article
from x_spaces_scraper.pp_publisher import publish_article

# ─── Logging setup ──────────────────────────────────────────────────────────

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "x_spaces_scraper.log"


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

    # File handler
    fh = logging.FileHandler(LOG_FILE, mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt))

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)


logger = logging.getLogger("x_spaces_scraper")


# ─── Pipeline ───────────────────────────────────────────────────────────────

def run_pipeline(dry_run: bool = False, auto_publish: bool = False, max_spaces: int = 10):
    """Run the full X Spaces → articles pipeline."""
    start = time.time()
    logger.info("=" * 60)
    logger.info(f"X Spaces Scraper starting | dry_run={dry_run} | auto_publish={auto_publish}")
    logger.info("=" * 60)

    stats = {
        "spaces_found": 0,
        "transcripts_fetched": 0,
        "articles_generated": 0,
        "articles_published": 0,
        "errors": [],
    }

    # ── Step 1: Find Spaces ──────────────────────────────────────────────
    logger.info("Step 1/4: Searching for Bitcoin X Spaces...")
    scraper = XSpacesScraper()
    spaces = scraper.find_spaces(skip_processed=True)
    stats["spaces_found"] = len(spaces)

    if not spaces:
        logger.info("No new Spaces found. Pipeline complete.")
        _log_summary(stats, time.time() - start)
        return stats

    logger.info(f"Found {len(spaces)} new space(s)")
    for s in spaces:
        logger.info(f"  [{s.detected_via}] @{s.host}: {s.title or '(no title)'} ({s.state})")

    # Limit to max_spaces
    spaces = spaces[:max_spaces]

    # ── Step 2: Fetch Transcripts ────────────────────────────────────────
    logger.info(f"\nStep 2/4: Fetching transcripts for {len(spaces)} space(s)...")
    transcripts = {}
    for space in spaces:
        if dry_run:
            logger.info(f"  [DRY RUN] Would fetch transcript for {space.space_id} (@{space.host})")
            continue

        transcript = fetch_transcript(space.space_id, space.url)
        if transcript:
            transcripts[space.space_id] = transcript
            stats["transcripts_fetched"] += 1
            logger.info(
                f"  Transcript OK: {space.space_id} — "
                f"{transcript.get('word_count', 0)} words, "
                f"{transcript.get('duration_s', 0)}s"
            )
        else:
            err = f"Transcript fetch failed for {space.space_id}"
            stats["errors"].append(err)
            logger.warning(f"  {err}")

    if dry_run:
        logger.info(f"[DRY RUN] Would attempt transcription for {len(spaces)} spaces")
        _log_summary(stats, time.time() - start)
        return stats

    if not transcripts:
        logger.warning("No transcripts fetched. Pipeline stopping.")
        _log_summary(stats, time.time() - start)
        return stats

    # ── Step 3: Generate Articles ────────────────────────────────────────
    logger.info(f"\nStep 3/4: Generating articles from {len(transcripts)} transcript(s)...")
    articles = {}
    for space in spaces:
        if space.space_id not in transcripts:
            continue

        transcript = transcripts[space.space_id]
        if transcript.get("word_count", 0) < 100:
            logger.warning(f"  Skipping {space.space_id}: transcript too short ({transcript.get('word_count', 0)} words)")
            continue

        meta = space.to_dict()
        article = generate_article(transcript, meta)
        if article:
            articles[space.space_id] = article
            stats["articles_generated"] += 1
            logger.info(f"  Article OK: \"{article.get('title', '?')}\"")
        else:
            err = f"Article generation failed for {space.space_id}"
            stats["errors"].append(err)
            logger.warning(f"  {err}")

    if not articles:
        logger.warning("No articles generated. Pipeline stopping.")
        _log_summary(stats, time.time() - start)
        return stats

    # ── Step 4: Publish ──────────────────────────────────────────────────
    logger.info(f"\nStep 4/4: Publishing {len(articles)} article(s)...")
    for space_id, article in articles.items():
        article_id = publish_article(article, auto_publish=auto_publish)
        if article_id:
            stats["articles_published"] += 1
            logger.info(f"  Published #{article_id}: \"{article.get('title', '?')}\"")
            # Mark space as processed
            scraper.mark_processed(space_id)
        else:
            err = f"Publish failed for {space_id}"
            stats["errors"].append(err)
            logger.warning(f"  {err}")

    _log_summary(stats, time.time() - start)
    return stats


def _log_summary(stats: dict, elapsed: float):
    """Log final pipeline summary."""
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info(f"  Spaces found:       {stats['spaces_found']}")
    logger.info(f"  Transcripts:        {stats['transcripts_fetched']}")
    logger.info(f"  Articles generated: {stats['articles_generated']}")
    logger.info(f"  Articles published: {stats['articles_published']}")
    logger.info(f"  Errors:             {len(stats['errors'])}")
    if stats["errors"]:
        for e in stats["errors"]:
            logger.info(f"    - {e}")
    logger.info(f"  Elapsed:            {elapsed:.1f}s")
    logger.info("=" * 60)

    # Write summary to JSON for monitoring
    summary_path = Path(__file__).parent / "cache" / "last_run.json"
    summary_path.write_text(json.dumps({
        **stats,
        "timestamp": datetime.utcnow().isoformat(),
        "elapsed_s": round(elapsed, 1),
    }, indent=2))


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="X Spaces Scraper for Protocol Pulse")
    parser.add_argument("--dry-run", action="store_true", help="Log what would happen without executing")
    parser.add_argument("--publish", action="store_true", help="Auto-publish articles (default: save as drafts)")
    parser.add_argument("--max-spaces", type=int, default=10, help="Max spaces to process per run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    stats = run_pipeline(
        dry_run=args.dry_run,
        auto_publish=args.publish,
        max_spaces=args.max_spaces,
    )

    # Exit code: 0 if no errors, 1 if errors
    sys.exit(0 if not stats.get("errors") else 1)


if __name__ == "__main__":
    main()
