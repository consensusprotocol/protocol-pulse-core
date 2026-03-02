#!/usr/bin/env python3
"""Oracle Briefing Thumbnail Generator.

Generates a 1280x720 thumbnail with:
- Proto_P avatar face on left
- Headline + BTC metric on right
- "ORACLE BRIEFING" branding badge
"""

import os
from PIL import Image, ImageDraw, ImageFont


# Dimensions
W, H = 1280, 720

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Colors
BG = (10, 10, 10)
RED = (204, 0, 0)
WHITE = (255, 255, 255)
GRAY = (102, 102, 102)
GREEN = (0, 204, 102)
RED_ACCENT = (255, 51, 51)


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def generate_briefing_thumbnail(script, output_path):
    """Generate 1280x720 thumbnail with avatar face + headline + BTC price."""
    img = Image.new("RGB", (W, H), color=BG)
    draw = ImageDraw.Draw(img)

    font_big = _load_font(FONT_BOLD, 56)
    font_med = _load_font(FONT_BOLD, 36)
    font_sm = _load_font(FONT_MONO, 28)

    # Load avatar
    avatar_path = os.path.join(os.path.dirname(__file__), "..", "oracle", "Proto_P_Avatar_512.png")
    if os.path.exists(avatar_path):
        try:
            avatar = Image.open(avatar_path).convert("RGBA")
            avatar = avatar.resize((360, 360), Image.LANCZOS)
            img.paste(avatar, (40, (H - 360) // 2), avatar)
        except Exception as e:
            print(f"[thumb] Avatar load error: {e}")

    # Red accent bar
    draw.rectangle([(430, 140), (436, 580)], fill=RED)

    # Headline text (word-wrapped)
    headline = script.get("thumbnail_headline", "ORACLE BRIEFING")
    words = headline.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_big)
        if bbox[2] - bbox[0] > 760:
            if current:
                lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)

    y = 160
    for line in lines[:3]:
        draw.text((460, y), line.upper(), fill=WHITE, font=font_big)
        y += 70

    # BTC price + change
    btc_data = script.get("data", {}).get("btc", {})
    price = btc_data.get("price", 0)
    change = btc_data.get("change_24h", 0)
    if price > 0:
        price_str = f"BTC ${price:,.0f}"
        change_color = GREEN if change >= 0 else RED_ACCENT
        change_str = f"{change:+.1f}%"
        draw.text((460, y + 30), price_str, fill=WHITE, font=font_med)
        price_width = draw.textlength(price_str, font=font_med)
        draw.text((460 + int(price_width) + 20, y + 35), change_str, fill=change_color, font=font_sm)

    # "ORACLE BRIEFING" badge
    draw.rectangle([(460, y + 100), (730, y + 140)], fill=RED)
    draw.text((470, y + 105), "ORACLE BRIEFING", fill=WHITE, font=font_sm)

    # Bottom branding
    draw.text((W - 300, H - 40), "PROTOCOL PULSE", fill=GRAY, font=font_sm)

    img.save(output_path, "JPEG", quality=92)
    print(f"[thumb] Thumbnail: {output_path}")
    return True


if __name__ == "__main__":
    # Quick test with sample data
    sample_script = {
        "thumbnail_headline": "Bitcoin Breaks Through Resistance",
        "data": {
            "btc": {"price": 87432, "change_24h": 2.4},
        },
    }
    os.makedirs("output", exist_ok=True)
    generate_briefing_thumbnail(sample_script, "output/test_thumbnail.jpg")
    print("Done — output/test_thumbnail.jpg")
