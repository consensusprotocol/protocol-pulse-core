#!/usr/bin/env python3
"""Thumbnail Generator V5 — MMA Central / ESPN style thumbnails.

Features:
- Avatar face prominently on right side
- Bold, thick white text with drop shadow on left
- Red accent color for emphasis words
- Dark cinematic background with gradient
- Asymmetric layout (text 40%, image 60%)
- BTC price badge in corner
- "PROTOCOL PULSE" branding
"""
import os

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Brand colors
BG_DARK = (8, 8, 8)
RED = (204, 0, 0)
RED_BRIGHT = (255, 51, 51)
WHITE = (255, 255, 255)
GRAY = (120, 120, 120)
LIGHT_GRAY = (180, 180, 180)

# Default avatar path (from model_registry)
AVATAR_PATH = os.path.expanduser("~/protocol_pulse/oracle/Proto_P_Avatar_512.png")


def generate_thumbnail(headline: str, subtext: str = "",
                       output_path: str = "thumbnail.png",
                       btc_price: str = "",
                       avatar_path: str = None,
                       top_quote: str = "") -> str:
    """Generate a 1280x720 MMA Central style YouTube thumbnail.

    Args:
        headline: Bold main text (5-8 words)
        subtext: Secondary line
        output_path: Where to save
        btc_price: BTC price for badge
        avatar_path: Path to avatar/face image
        top_quote: Optional quote text for additional context

    Returns:
        Path to generated thumbnail, or "" on failure.
    """
    if not HAS_PIL:
        print("  [thumb] Pillow not installed, skipping thumbnail")
        return ""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    W, H = 1280, 720
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # ── Background: dark cinematic gradient ──────────────────────────────
    for y in range(H):
        for x in range(W):
            # Diagonal gradient: dark to slightly lighter
            factor = (x / W * 0.3 + y / H * 0.7)
            r = int(8 + 15 * factor)
            g = int(5 + 5 * factor)
            b = int(5 + 5 * factor)
            draw.point((x, y), fill=(r, g, b))

    # Red accent glow behind where face will be (right side)
    for y in range(H):
        for x in range(max(0, W - 500), W):
            alpha = (x - (W - 500)) / 500.0
            gy = 1.0 - abs(y / H - 0.5) * 2
            intensity = alpha * gy * 0.15
            r = int(8 + 200 * intensity)
            g = int(5 + 10 * intensity)
            b = int(5 + 10 * intensity)
            draw.point((x, y), fill=(r, g, b))

    # ── Avatar / face image (right 60%) ──────────────────────────────────
    face_path = avatar_path or AVATAR_PATH
    if os.path.exists(face_path):
        try:
            face_img = Image.open(face_path).convert("RGBA")
            # Scale to fit right portion, vertically centered
            face_h = H
            face_w = int(face_img.width * face_h / face_img.height)
            face_img = face_img.resize((face_w, face_h), Image.LANCZOS)

            # Enhance: slightly more contrast for dramatic look
            enhancer = ImageEnhance.Contrast(face_img)
            face_img = enhancer.enhance(1.2)
            enhancer = ImageEnhance.Brightness(face_img)
            face_img = enhancer.enhance(0.85)

            # Create gradient mask for left-edge fade
            mask = Image.new("L", (face_w, face_h), 255)
            mask_draw = ImageDraw.Draw(mask)
            fade_width = face_w // 3
            for x in range(fade_width):
                alpha = int(255 * (x / fade_width))
                mask_draw.line([(x, 0), (x, face_h)], fill=alpha)

            # Position on right side
            face_x = W - face_w + 50
            img.paste(face_img, (face_x, 0), mask)
        except Exception as e:
            print(f"  [thumb] Avatar load error: {e}")

    draw = ImageDraw.Draw(img)  # Refresh draw after paste

    # ── Red accent bars ──────────────────────────────────────────────────
    draw.rectangle([(0, 0), (6, H)], fill=RED)  # Left edge
    draw.rectangle([(0, 380), (520, 384)], fill=RED)  # Horizontal accent

    # ── "PULSE CHECK" show name (top-left) ───────────────────────────────
    try:
        font_show = ImageFont.truetype(FONT_BOLD, 26)
    except Exception:
        font_show = ImageFont.load_default()
    draw.text((25, 22), "PULSE CHECK", fill=RED_BRIGHT, font=font_show)

    # ── Main headline (left 45% of frame) ────────────────────────────────
    try:
        font_headline = ImageFont.truetype(FONT_BOLD, 68)
    except Exception:
        font_headline = ImageFont.load_default()

    max_text_width = int(W * 0.48)
    words = headline.upper().split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_headline)
        if bbox[2] - bbox[0] > max_text_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    # Draw headline with drop shadow
    line_height = 78
    total_height = len(lines) * line_height
    start_y = max(80, (340 - total_height) // 2 + 60)

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        # Shadow (offset)
        draw.text((27, y + 4), line, fill=(20, 20, 20), font=font_headline)
        draw.text((28, y + 3), line, fill=(30, 30, 30), font=font_headline)
        # Main text
        draw.text((25, y), line, fill=WHITE, font=font_headline)

    # ── Subtext below accent line ────────────────────────────────────────
    if subtext:
        try:
            font_sub = ImageFont.truetype(FONT_BOLD, 32)
        except Exception:
            font_sub = ImageFont.load_default()
        draw.text((25, 405), subtext.upper(), fill=LIGHT_GRAY, font=font_sub)

    # ── Quote (if provided) ──────────────────────────────────────────────
    if top_quote:
        try:
            font_quote = ImageFont.truetype(FONT_MONO, 18)
        except Exception:
            font_quote = ImageFont.load_default()
        quote_text = f'"{top_quote[:80]}"'
        draw.text((25, 450), quote_text, fill=GRAY, font=font_quote)

    # ── BTC price badge (bottom-left) ────────────────────────────────────
    if btc_price:
        try:
            font_btc = ImageFont.truetype(FONT_BOLD, 28)
            font_btc_label = ImageFont.truetype(FONT_MONO, 16)
        except Exception:
            font_btc = font_btc_label = ImageFont.load_default()

        # Badge background
        badge_w, badge_h = 200, 55
        badge_x, badge_y = 25, H - 75
        draw.rectangle(
            [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
            fill=(15, 15, 15), outline=RED, width=2,
        )
        # BTC icon (circle)
        draw.ellipse(
            [(badge_x + 8, badge_y + 12), (badge_x + 38, badge_y + 42)],
            fill=RED,
        )
        draw.text((badge_x + 16, badge_y + 14), "B", fill=WHITE, font=font_btc_label)
        # Price text
        draw.text((badge_x + 48, badge_y + 12), btc_price, fill=WHITE, font=font_btc)

    # ── "PROTOCOL PULSE" branding (bottom-right) ────────────────────────
    try:
        font_brand = ImageFont.truetype(FONT_MONO, 16)
    except Exception:
        font_brand = ImageFont.load_default()
    draw.text((W - 200, H - 35), "PROTOCOL PULSE", fill=GRAY, font=font_brand)

    img.save(output_path, "PNG", quality=95)
    sz = os.path.getsize(output_path) // 1024
    print(f"  [thumb] Generated: {output_path} ({W}x{H}, {sz}KB)")
    return output_path


if __name__ == "__main__":
    out = os.path.join(BASE, "output", "test_thumbnail_v5.png")
    generate_thumbnail(
        "HASH RATE BREAKS ALL RECORDS",
        "Nations are stacking",
        out,
        btc_price="$97,234",
        top_quote="When the entities that print fiat start hoarding the exit asset...",
    )
