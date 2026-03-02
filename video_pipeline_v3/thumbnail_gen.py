#!/usr/bin/env python3
"""Thumbnail generator — 1280x720 YouTube thumbnails using Pillow.
Bold headline + branding + dramatic dark style."""
import os
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Brand colors
BG_COLOR = (10, 10, 10)
RED = (204, 0, 0)
WHITE = (255, 255, 255)
GRAY = (120, 120, 120)


def generate_thumbnail(headline: str, subtext: str = "",
                       output_path: str = "thumbnail.png",
                       style: str = "dramatic") -> str:
    """Generate a 1280x720 YouTube thumbnail.

    Args:
        headline: Bold main text (5-8 words)
        subtext: Secondary line
        output_path: Where to save
        style: "dramatic" (default)

    Returns:
        Path to generated thumbnail, or "" on failure.
    """
    if not HAS_PIL:
        print("  [thumb] Pillow not installed, skipping thumbnail")
        return ""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    W, H = 1280, 720
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Background effects — diagonal red gradient accent
    for y in range(H):
        for x in range(max(0, W - 200), W):
            alpha = (x - (W - 200)) / 200.0
            r = int(10 + 40 * alpha * (1 - y / H))
            draw.point((x, y), fill=(r, 5, 5))

    # Red accent bar (left edge)
    draw.rectangle([(0, 0), (8, H)], fill=RED)

    # Red horizontal line
    draw.rectangle([(0, 400), (W, 404)], fill=RED)

    # Top branding
    try:
        font_brand = ImageFont.truetype(FONT_MONO, 22)
    except Exception:
        font_brand = ImageFont.load_default()
    draw.text((40, 30), "PROTOCOL PULSE", fill=GRAY, font=font_brand)

    # Show name
    try:
        font_show = ImageFont.truetype(FONT_BOLD, 28)
    except Exception:
        font_show = ImageFont.load_default()
    draw.text((40, 60), "PULSE CHECK", fill=RED, font=font_show)

    # Main headline — large, bold, word-wrapped
    try:
        font_headline = ImageFont.truetype(FONT_BOLD, 72)
    except Exception:
        font_headline = ImageFont.load_default()

    # Word-wrap headline
    words = headline.upper().split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_headline)
        if bbox[2] - bbox[0] > W - 100:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    # Draw headline centered vertically
    line_height = 85
    total_text_height = len(lines) * line_height
    start_y = max(120, (350 - total_text_height) // 2 + 80)

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        # Shadow
        draw.text((42, y + 3), line, fill=(30, 30, 30), font=font_headline)
        draw.text((40, y), line, fill=WHITE, font=font_headline)

    # Subtext below red line
    if subtext:
        try:
            font_sub = ImageFont.truetype(FONT_BOLD, 36)
        except Exception:
            font_sub = ImageFont.load_default()
        draw.text((40, 430), subtext.upper(), fill=GRAY, font=font_sub)

    # Bottom-right: BTC indicator dot
    draw.ellipse([(W - 80, H - 60), (W - 50, H - 30)], fill=RED)
    try:
        font_btc = ImageFont.truetype(FONT_MONO, 18)
    except Exception:
        font_btc = ImageFont.load_default()
    draw.text((W - 45, H - 55), "BTC", fill=WHITE, font=font_btc)

    img.save(output_path, "PNG", quality=95)
    sz = os.path.getsize(output_path) // 1024
    print(f"  [thumb] Generated: {output_path} ({W}x{H}, {sz}KB)")
    return output_path


if __name__ == "__main__":
    out = os.path.join(BASE, "output", "test_thumbnail.png")
    generate_thumbnail(
        "HASH RATE BREAKS ALL RECORDS",
        "Nations are stacking",
        out,
    )
