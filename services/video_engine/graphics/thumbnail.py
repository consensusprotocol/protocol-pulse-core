"""
Thumbnail Generator
====================
YouTube-style thumbnails that get clicks.
Horizontal (1920x1080) + Vertical (1080x1920) for shorts.
"""
import logging
import textwrap
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("Thumbnail")

# Design
BG_COLOR = (10, 15, 10)
RED = (204, 34, 34)
DARK_RED = (120, 20, 20)
WHITE = (255, 255, 255)
GRAY = (156, 163, 175)
DARK_GRAY = (60, 65, 60)

FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def generate_thumbnail(headline: str, channel_names: List[str],
                       date_str: str, output_path: str,
                       btc_price: str = "") -> str:
    """
    Generate a 1920x1080 YouTube thumbnail.

    Args:
        headline: Bold text (2-5 words max)
        channel_names: Source channels featured
        date_str: e.g. "2026-03-03"
        output_path: where to save PNG
        btc_price: optional BTC price string
    """
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Subtle grid background
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=(15, 20, 15), width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=(15, 20, 15), width=1)

    # Dramatic diagonal red gradient (right side)
    for y in range(H):
        for x in range(W - 400, W):
            alpha = (x - (W - 400)) / 400.0
            fade = 1 - (y / H)
            r = int(10 + 60 * alpha * fade)
            g = int(15 + 5 * alpha * fade)
            draw.point((x, y), fill=(r, g, 10))

    # Red accent bars
    draw.rectangle([0, 0, W, 5], fill=RED)
    draw.rectangle([0, H - 5, W, H], fill=RED)
    draw.rectangle([0, 0, 8, H], fill=RED)

    # PULSE CHECK badge (top-left)
    font_badge = _font(FONT_SANS_BOLD, 36)
    badge_text = "  PULSE CHECK  "
    bbox = font_badge.getbbox(badge_text)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    draw.rectangle([40, 40, 40 + bw + 20, 40 + bh + 20], fill=RED)
    draw.text((50, 45), badge_text, font=font_badge, fill=WHITE)

    # Date (top-right)
    font_date = _font(FONT_MONO, 28)
    draw.text((W - 300, 50), date_str, font=font_date, fill=GRAY)

    # Main headline — massive, uppercase
    font_headline = _font(FONT_SANS_BOLD, 120)
    headline_upper = headline.upper()

    # Word-wrap headline
    words = headline_upper.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        test_bbox = font_headline.getbbox(test)
        if test_bbox[2] - test_bbox[0] > W - 160:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    # Draw headline centered
    line_height = 140
    total_h = len(lines) * line_height
    start_y = max(180, (H - total_h) // 2 - 40)

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        # Shadow
        draw.text((82, y + 4), line, font=font_headline, fill=(20, 25, 20))
        # Main text
        draw.text((80, y), line, font=font_headline, fill=WHITE)

    # Red underline below headline
    underline_y = start_y + len(lines) * line_height + 10
    draw.rectangle([80, underline_y, W - 80, underline_y + 6], fill=RED)

    # Source channels along bottom
    if channel_names:
        font_sources = _font(FONT_SANS, 24)
        sources_text = " · ".join(channel_names[:5])
        draw.text((80, H - 100), f"Sources: {sources_text}",
                  font=font_sources, fill=GRAY)

    # BTC price badge (bottom-right)
    if btc_price:
        font_price = _font(FONT_MONO, 32)
        price_text = f"BTC {btc_price}"
        pbbox = font_price.getbbox(price_text)
        pw = pbbox[2] - pbbox[0]
        draw.rectangle([W - pw - 80, H - 110, W - 40, H - 60], fill=DARK_RED)
        draw.text((W - pw - 60, H - 108), price_text, font=font_price, fill=WHITE)

    # Watermark
    font_wm = _font(FONT_MONO, 18)
    draw.text((W - 250, H - 40), "PROTOCOL PULSE", font=font_wm, fill=(25, 30, 25))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    logger.info(f"  Thumbnail: {Path(output_path).name} (1920x1080)")
    return output_path


def generate_vertical_thumbnail(headline: str, output_path: str,
                                date_str: str = "",
                                btc_price: str = "") -> str:
    """
    Generate a 1080x1920 vertical thumbnail for shorts.
    """
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Grid
    for x in range(0, W, 50):
        draw.line([(x, 0), (x, H)], fill=(15, 20, 15), width=1)
    for y in range(0, H, 50):
        draw.line([(0, y), (W, y)], fill=(15, 20, 15), width=1)

    # Red accents
    draw.rectangle([0, 0, W, 5], fill=RED)
    draw.rectangle([0, H - 5, W, H], fill=RED)

    # PULSE CHECK badge (top center)
    font_badge = _font(FONT_SANS_BOLD, 32)
    badge_text = "  PULSE CHECK  "
    bbox = font_badge.getbbox(badge_text)
    bw = bbox[2] - bbox[0]
    badge_x = (W - bw) // 2
    draw.rectangle([badge_x - 10, 60, badge_x + bw + 10, 110], fill=RED)
    draw.text((badge_x, 65), badge_text, font=font_badge, fill=WHITE)

    # Main headline — centered vertically
    font_headline = _font(FONT_SANS_BOLD, 88)
    headline_upper = headline.upper()

    words = headline_upper.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        test_bbox = font_headline.getbbox(test)
        if test_bbox[2] - test_bbox[0] > W - 120:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    line_height = 110
    total_h = len(lines) * line_height
    start_y = (H - total_h) // 2 - 60

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        lbbox = font_headline.getbbox(line)
        lw = lbbox[2] - lbbox[0]
        x = (W - lw) // 2
        draw.text((x + 3, y + 3), line, font=font_headline, fill=(20, 25, 20))
        draw.text((x, y), line, font=font_headline, fill=WHITE)

    # Red line below headline
    underline_y = start_y + len(lines) * line_height + 15
    draw.rectangle([60, underline_y, W - 60, underline_y + 5], fill=RED)

    # Date
    if date_str:
        font_date = _font(FONT_MONO, 26)
        dbbox = font_date.getbbox(date_str)
        dw = dbbox[2] - dbbox[0]
        draw.text(((W - dw) // 2, underline_y + 30), date_str,
                  font=font_date, fill=GRAY)

    # BTC price
    if btc_price:
        font_price = _font(FONT_MONO, 28)
        price_text = f"BTC {btc_price}"
        pbbox = font_price.getbbox(price_text)
        pw = pbbox[2] - pbbox[0]
        draw.rectangle([(W - pw) // 2 - 15, H - 140, (W + pw) // 2 + 15, H - 95],
                       fill=DARK_RED)
        draw.text(((W - pw) // 2, H - 138), price_text,
                  font=font_price, fill=WHITE)

    # Watermark
    font_wm = _font(FONT_MONO, 16)
    draw.text((W - 200, H - 40), "PROTOCOL PULSE", font=font_wm, fill=(25, 30, 25))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    logger.info(f"  Vertical thumbnail: {Path(output_path).name} (1080x1920)")
    return output_path
