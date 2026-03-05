#!/usr/bin/env python3
"""Tweet Screenshot Capture — Playwright-based tweet screenshotting.

Captures a screenshot of a tweet element for use as a social segment
card visual instead of Remotion text cards.
"""

import logging
import os

from playwright.sync_api import sync_playwright

logger = logging.getLogger("TweetScreenshot")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[tweet_screenshot] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def capture_tweet(tweet_url: str, output_path: str) -> bool:
    """Capture a screenshot of a tweet.

    Args:
        tweet_url: Full URL to the tweet (x.com or twitter.com)
        output_path: Path to save the PNG screenshot

    Returns:
        True if screenshot was captured, False on failure
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1024})

            logger.info(f"Navigating to {tweet_url}")
            page.goto(tweet_url, wait_until="networkidle", timeout=15000)

            # Wait for tweet to render
            try:
                page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                tweet = page.query_selector('article[data-testid="tweet"]')
                if tweet:
                    tweet.screenshot(path=output_path)
                    logger.info(f"Tweet element captured: {output_path}")
                    browser.close()
                    return True
            except Exception:
                logger.warning("Tweet selector not found, falling back to viewport crop")

            # Fallback: screenshot the visible area
            page.screenshot(
                path=output_path,
                clip={"x": 0, "y": 0, "width": 800, "height": 600},
            )
            logger.info(f"Fallback screenshot captured: {output_path}")
            browser.close()
            return True

    except Exception as e:
        logger.error(f"Failed to capture tweet: {e}")
        return False


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://x.com/saylor/status/1886847694068080989"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/test_tweet.png"
    result = capture_tweet(url, out)
    print(f"Capture {'succeeded' if result else 'failed'}: {out}")
    if result:
        size = os.path.getsize(out)
        print(f"File size: {size} bytes")
