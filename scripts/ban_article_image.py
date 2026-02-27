#!/usr/bin/env python3
"""
ban_article_image.py — Permanently ban an article header image by perceptual hash.

Usage:
    python scripts/ban_article_image.py --path static/images/headers/bad_image.jpg
    python scripts/ban_article_image.py --path bad.jpg --label "generic bitcoin coin"
    python scripts/ban_article_image.py --path bad.jpg --label "stock photo" --maxdist 10
"""

import argparse
import logging
import os
import sys

# Project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Ban an article image permanently by perceptual hash"
    )
    parser.add_argument(
        "--path", required=True, help="Path to the image file to ban"
    )
    parser.add_argument(
        "--label",
        default="manual_ban",
        help="Human-readable label for why this image is banned (default: manual_ban)",
    )
    parser.add_argument(
        "--maxdist",
        type=int,
        default=None,
        help="Max hamming distance for this ban entry (default: uses IMAGE_GUARD_BAN_MAX_DIST env var or 8)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        logger.error("File not found: %s", args.path)
        sys.exit(1)

    from services.articles.image_guard import add_banned_image_file, get_banned_count

    phash = add_banned_image_file(args.path, label=args.label, max_dist=args.maxdist)
    if phash:
        print("Banned successfully.")
        print("  phash:    %s" % phash)
        print("  label:    %s" % args.label)
        print("  maxdist:  %s" % (args.maxdist or "(default)"))
        print("  total banned: %d" % get_banned_count())
    else:
        print("FAILED to ban image. Check logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()
