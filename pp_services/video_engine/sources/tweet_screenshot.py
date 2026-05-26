"""
Tweet Screenshot — Enhanced Tweet Card Renderer
=================================================
Generates cinematic 1920x1080 tweet cards for video overlay.

Priority: Playwright real screenshot → Enhanced Pillow render → Simple fallback
"""
import logging
import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("TweetScreenshot")

# Design constants
W, H = 1920, 1080
BG_COLOR = (10, 12, 16)
CARD_BG = (22, 24, 30)
RED = (204, 34, 34)
WHITE = (255, 255, 255)
GRAY = (156, 163, 175)
DARK_GRAY = (100, 100, 110)
BLUE_LINK = (29, 155, 240)

FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def capture_tweet(tweet: dict, output_path: str, index: int = 0) -> Optional[str]:
    """
    Render a tweet card to a 1920x1080 PNG.
    Tries Playwright first, falls back to enhanced Pillow.

    Args:
        tweet: dict with author_name, author_handle, text, likes, retweets, tweet_id
        output_path: where to save the PNG
        index: tweet index for filename uniqueness
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Try Playwright screenshot of actual tweet
    if tweet.get("tweet_id") or tweet.get("url"):
        result = _capture_playwright(tweet, output_path)
        if result:
            return result

    # Enhanced Pillow render
    return _render_enhanced(tweet, output_path)


def _capture_playwright(tweet: dict, output_path: str) -> Optional[str]:
    """Capture real tweet via Playwright headless browser."""
    try:
        from playwright.sync_api import sync_playwright

        url = tweet.get("url", "")
        if not url and tweet.get("tweet_id"):
            handle = tweet.get("author_handle", "").lstrip("@")
            url = f"https://x.com/{handle}/status/{tweet['tweet_id']}"

        if not url:
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(3000)

            # Screenshot the full page
            raw_path = output_path.replace(".png", "_raw.png")
            page.screenshot(path=raw_path)
            browser.close()

        if Path(raw_path).exists():
            # Add branding frame
            _add_brand_frame(raw_path, output_path)
            Path(raw_path).unlink(missing_ok=True)
            logger.info(f"  Tweet screenshot (Playwright): {Path(output_path).name}")
            return output_path

    except Exception as e:
        logger.debug(f"  Playwright screenshot failed: {e}")
    return None


def _add_brand_frame(raw_path: str, output_path: str):
    """Add dark frame + branding to a raw screenshot."""
    raw = Image.open(raw_path)

    # Create branded canvas
    canvas = Image.new("RGB", (W, H), BG_COLOR)

    # Scale screenshot to fit with padding
    max_w, max_h = W - 200, H - 160
    raw.thumbnail((max_w, max_h), Image.LANCZOS)
    x = (W - raw.width) // 2
    y = (H - raw.height) // 2
    canvas.paste(raw, (x, y))

    # Red accent lines
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, W, 3], fill=RED)
    draw.rectangle([0, H - 3, W, H], fill=RED)

    # Watermark
    font_wm = _font(FONT_MONO, 18)
    draw.text((W - 220, H - 35), "PULSE CHECK", font=font_wm, fill=(40, 40, 50))

    canvas.save(output_path)


def _render_enhanced(tweet: dict, output_path: str) -> Optional[str]:
    """Enhanced Pillow-rendered tweet card with proper typography."""
    try:
        img = Image.new("RGB", (W, H), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Card background (centered, slightly lighter)
        card_x, card_y = 200, 120
        card_w, card_h = W - 400, H - 240
        _draw_rounded_rect(draw, card_x, card_y, card_x + card_w, card_y + card_h,
                          radius=20, fill=CARD_BG)

        # Red accent line at top of card
        draw.rectangle([card_x, card_y, card_x + card_w, card_y + 4], fill=RED)

        # Author name
        font_name = _font(FONT_SANS_BOLD, 44)
        font_handle = _font(FONT_SANS, 30)
        font_text = _font(FONT_SANS, 38)
        font_stats = _font(FONT_SANS, 26)
        font_wm = _font(FONT_MONO, 18)

        author = tweet.get("author_name", "Unknown")
        handle = tweet.get("author_handle", "@unknown")
        if not handle.startswith("@"):
            handle = f"@{handle}"

        y = card_y + 50
        draw.text((card_x + 60, y), author, font=font_name, fill=WHITE)

        # Verified badge (blue dot next to name)
        name_bbox = font_name.getbbox(author)
        badge_x = card_x + 60 + name_bbox[2] - name_bbox[0] + 15
        draw.ellipse([badge_x, y + 12, badge_x + 22, y + 34], fill=BLUE_LINK)

        y += 55
        draw.text((card_x + 60, y), handle, font=font_handle, fill=GRAY)
        y += 60

        # Divider line
        draw.rectangle([card_x + 60, y, card_x + card_w - 60, y + 1], fill=(40, 42, 50))
        y += 25

        # Tweet text with proper wrapping
        text = tweet.get("text", "")
        wrapped = textwrap.fill(text, width=50)
        lines = wrapped.split("\n")[:8]

        for line in lines:
            draw.text((card_x + 60, y), line, font=font_text, fill=WHITE)
            y += 52

        # Engagement stats
        y = card_y + card_h - 80
        likes = tweet.get("likes", 0)
        rts = tweet.get("retweets", 0)
        replies = tweet.get("replies", 0)

        stats_parts = []
        if likes:
            stats_parts.append(f"{_format_count(likes)} likes")
        if rts:
            stats_parts.append(f"{_format_count(rts)} reposts")
        if replies:
            stats_parts.append(f"{_format_count(replies)} replies")

        stats_text = "  ·  ".join(stats_parts) if stats_parts else ""
        draw.text((card_x + 60, y), stats_text, font=font_stats, fill=GRAY)

        # "via X" badge
        draw.text((card_x + card_w - 120, card_y + 50), "𝕏", font=font_name, fill=GRAY)

        # Red accent lines top/bottom of frame
        draw.rectangle([0, 0, W, 3], fill=RED)
        draw.rectangle([0, H - 3, W, H], fill=RED)

        # Watermark
        draw.text((W - 220, H - 35), "PULSE CHECK", font=font_wm, fill=(40, 40, 50))

        img.save(output_path)
        logger.info(f"  Tweet card rendered (enhanced): {Path(output_path).name}")
        return output_path

    except Exception as e:
        logger.error(f"  Enhanced render failed: {e}")
        return None


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, x1: int, y1: int,
                       x2: int, y2: int, radius: int = 10,
                       fill: tuple = (0, 0, 0)):
    """Draw a rounded rectangle."""
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.pieslice([x1, y1, x1 + 2 * radius, y1 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * radius, y1, x2, y1 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * radius, x1 + 2 * radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * radius, y2 - 2 * radius, x2, y2], 0, 90, fill=fill)


def _format_count(n: int) -> str:
    """Format large numbers: 1500 → 1.5K, 1500000 → 1.5M."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
