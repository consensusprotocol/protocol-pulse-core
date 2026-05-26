"""
Motion Graphics Engine
=======================
Generates branded video elements using Pillow frame rendering + ffmpeg encoding.
No external dependencies like After Effects — pure code-generated graphics.

Elements:
  - Intro bumper (4s)
  - Outro bumper (3s)
  - Transition sweep (1s)
  - Lower third overlays
  - Story title cards (2s)
"""
import logging
import math
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from pp_services.video_engine.assembly import ffmpeg_ops

logger = logging.getLogger("MotionGraphics")

# ── Design constants ──
BG_COLOR = (10, 15, 10)         # #0a0f0a
RED = (204, 34, 34)             # #CC2222
WHITE = (255, 255, 255)
GRAY = (160, 160, 160)
DARK_SURFACE = (18, 18, 18)     # #121212
FPS = 30
W, H = 1920, 1080

# ── Font paths ──
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_MONO_BOLD = "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if not found."""
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype(FONT_SANS, size)
        except Exception:
            return ImageFont.load_default()


def _ease_in_out(t: float) -> float:
    """Smooth ease-in-out curve (0.0 → 1.0)."""
    return t * t * (3 - 2 * t)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


# ═══════════════════════════════════════════════════════════════
# INTRO BUMPER (4 seconds)
# ═══════════════════════════════════════════════════════════════

def generate_intro(output_path: str, date_str: str = None, w: int = W, h: int = H) -> str:
    """
    Generate the intro bumper.
    - Black screen
    - Red horizontal line grows from center outward
    - "PULSE CHECK" text fades in
    - "DAILY BITCOIN INTELLIGENCE" subtitle fades in
    - Date stamp
    """
    if date_str is None:
        date_str = datetime.now().strftime("%B %d, %Y").upper()
    else:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            date_str = dt.strftime("%B %d, %Y").upper()
        except Exception:
            pass

    total_frames = 4 * FPS  # 120 frames
    frame_dir = tempfile.mkdtemp(prefix="intro_frames_")

    font_title = _get_font(FONT_MONO_BOLD, 96)
    font_sub = _get_font(FONT_MONO, 36)
    font_date = _get_font(FONT_MONO, 24)

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (w, h), BG_COLOR)
            draw = ImageDraw.Draw(img)

            # Phase 1 (0-30): Red line grows from center
            if f < 30:
                t = _ease_in_out(f / 29)
                line_half_w = int(t * (w // 2 - 100))
                cx, cy = w // 2, h // 2
                draw.rectangle(
                    [cx - line_half_w, cy - 2, cx + line_half_w, cy + 2],
                    fill=RED
                )

            # Phase 2 (30-60): Title fades in + line holds
            elif f < 60:
                # Full line
                cx, cy = w // 2, h // 2
                line_half_w = w // 2 - 100
                draw.rectangle(
                    [cx - line_half_w, cy - 2, cx + line_half_w, cy + 2],
                    fill=RED
                )

                # Title alpha
                alpha = _ease_in_out((f - 30) / 29)
                title_color = tuple(int(c * alpha) for c in WHITE)
                bbox = font_title.getbbox("PULSE CHECK")
                tw = bbox[2] - bbox[0]
                draw.text(((w - tw) // 2, cy - 80), "PULSE CHECK",
                         font=font_title, fill=title_color)

            # Phase 3 (60-90): Subtitle fades in
            elif f < 90:
                cx, cy = w // 2, h // 2
                line_half_w = w // 2 - 100
                draw.rectangle(
                    [cx - line_half_w, cy - 2, cx + line_half_w, cy + 2],
                    fill=RED
                )

                # Title fully visible
                bbox = font_title.getbbox("PULSE CHECK")
                tw = bbox[2] - bbox[0]
                draw.text(((w - tw) // 2, cy - 80), "PULSE CHECK",
                         font=font_title, fill=WHITE)

                # Subtitle fades
                alpha = _ease_in_out((f - 60) / 29)
                sub_color = tuple(int(_lerp(BG_COLOR[i], GRAY[i], alpha)) for i in range(3))
                sub_text = "DAILY BITCOIN INTELLIGENCE"
                bbox_s = font_sub.getbbox(sub_text)
                sw = bbox_s[2] - bbox_s[0]
                draw.text(((w - sw) // 2, cy + 20), sub_text,
                         font=font_sub, fill=sub_color)

                # Date fades with subtitle
                date_color = tuple(int(_lerp(BG_COLOR[i], GRAY[i], alpha * 0.6)) for i in range(3))
                bbox_d = font_date.getbbox(date_str)
                dw = bbox_d[2] - bbox_d[0]
                draw.text(((w - dw) // 2, cy + 70), date_str,
                         font=font_date, fill=date_color)

            # Phase 4 (90-120): Hold
            else:
                cx, cy = w // 2, h // 2
                line_half_w = w // 2 - 100
                draw.rectangle(
                    [cx - line_half_w, cy - 2, cx + line_half_w, cy + 2],
                    fill=RED
                )
                bbox = font_title.getbbox("PULSE CHECK")
                tw = bbox[2] - bbox[0]
                draw.text(((w - tw) // 2, cy - 80), "PULSE CHECK",
                         font=font_title, fill=WHITE)

                sub_text = "DAILY BITCOIN INTELLIGENCE"
                bbox_s = font_sub.getbbox(sub_text)
                sw = bbox_s[2] - bbox_s[0]
                draw.text(((w - sw) // 2, cy + 20), sub_text,
                         font=font_sub, fill=GRAY)

                bbox_d = font_date.getbbox(date_str)
                dw = bbox_d[2] - bbox_d[0]
                draw.text(((w - dw) // 2, cy + 70), date_str,
                         font=font_date, fill=(100, 100, 100))

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        # Encode frames to video with silent audio
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS
        )
        logger.info(f"  Intro bumper generated: {output_path}")
        return output_path

    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# OUTRO BUMPER (3 seconds)
# ═══════════════════════════════════════════════════════════════

def generate_outro(output_path: str, w: int = W, h: int = H) -> str:
    """
    Generate outro bumper.
    - "STAY SOVEREIGN" text center
    - "protocolpulse.io" below
    - Red line shrinks to center
    """
    total_frames = 3 * FPS  # 90 frames
    frame_dir = tempfile.mkdtemp(prefix="outro_frames_")

    font_title = _get_font(FONT_MONO_BOLD, 72)
    font_url = _get_font(FONT_MONO, 28)

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (w, h), BG_COLOR)
            draw = ImageDraw.Draw(img)
            cx, cy = w // 2, h // 2

            if f < 15:
                # Fade in
                alpha = _ease_in_out(f / 14)
                line_half_w = w // 2 - 100
                draw.rectangle(
                    [cx - line_half_w, cy + 30, cx + line_half_w, cy + 34],
                    fill=RED
                )
                title_color = tuple(int(c * alpha) for c in WHITE)
                bbox = font_title.getbbox("STAY SOVEREIGN")
                tw = bbox[2] - bbox[0]
                draw.text(((w - tw) // 2, cy - 50), "STAY SOVEREIGN",
                         font=font_title, fill=title_color)
                url_color = tuple(int(c * alpha) for c in GRAY)
                bbox_u = font_url.getbbox("protocolpulse.io")
                uw = bbox_u[2] - bbox_u[0]
                draw.text(((w - uw) // 2, cy + 50), "protocolpulse.io",
                         font=font_url, fill=url_color)

            elif f < 60:
                # Hold
                line_half_w = w // 2 - 100
                draw.rectangle(
                    [cx - line_half_w, cy + 30, cx + line_half_w, cy + 34],
                    fill=RED
                )
                bbox = font_title.getbbox("STAY SOVEREIGN")
                tw = bbox[2] - bbox[0]
                draw.text(((w - tw) // 2, cy - 50), "STAY SOVEREIGN",
                         font=font_title, fill=WHITE)
                bbox_u = font_url.getbbox("protocolpulse.io")
                uw = bbox_u[2] - bbox_u[0]
                draw.text(((w - uw) // 2, cy + 50), "protocolpulse.io",
                         font=font_url, fill=GRAY)

            else:
                # Line shrinks + fade out
                t = _ease_in_out((f - 60) / 29)
                line_half_w = int((1 - t) * (w // 2 - 100))
                if line_half_w > 0:
                    draw.rectangle(
                        [cx - line_half_w, cy + 30, cx + line_half_w, cy + 34],
                        fill=RED
                    )
                alpha = 1 - t
                title_color = tuple(int(c * alpha) for c in WHITE)
                bbox = font_title.getbbox("STAY SOVEREIGN")
                tw = bbox[2] - bbox[0]
                draw.text(((w - tw) // 2, cy - 50), "STAY SOVEREIGN",
                         font=font_title, fill=title_color)
                url_color = tuple(int(c * alpha) for c in GRAY)
                bbox_u = font_url.getbbox("protocolpulse.io")
                uw = bbox_u[2] - bbox_u[0]
                draw.text(((w - uw) // 2, cy + 50), "protocolpulse.io",
                         font=font_url, fill=url_color)

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS
        )
        logger.info(f"  Outro bumper generated: {output_path}")
        return output_path

    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# TRANSITION SWEEP (1 second)
# ═══════════════════════════════════════════════════════════════

def generate_transition(output_path: str, w: int = W, h: int = H) -> str:
    """
    Quick red line sweep left-to-right (like a scanner).
    1 second, usable between story segments.
    """
    total_frames = FPS  # 30 frames
    frame_dir = tempfile.mkdtemp(prefix="trans_frames_")

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (w, h), BG_COLOR)
            draw = ImageDraw.Draw(img)

            t = f / (total_frames - 1)
            # Red line sweeps left to right
            line_x = int(t * (w + 40)) - 20
            line_w = 8
            draw.rectangle([line_x - line_w, 0, line_x + line_w, h], fill=RED)

            # Subtle trailing glow
            for trail in range(1, 6):
                glow_x = line_x - trail * 30
                if glow_x > 0:
                    alpha = max(0, 1 - trail * 0.25)
                    glow_color = tuple(int(c * alpha * 0.3) for c in RED)
                    draw.rectangle([glow_x - 2, 0, glow_x + 2, h], fill=glow_color)

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS
        )
        logger.info(f"  Transition generated: {output_path}")
        return output_path

    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# LOWER THIRD
# ═══════════════════════════════════════════════════════════════

def render_lower_third(name: str, title: str, output_path: str,
                       w: int = W, h: int = H) -> str:
    """
    Render a lower third overlay as 1920x1080 RGBA PNG.
    Semi-transparent dark bar at bottom with red accent line.
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Lower third bar area
    bar_h = 120
    bar_y = h - bar_h - 40  # 40px from bottom

    # Semi-transparent dark bar
    bar = Image.new("RGBA", (w, bar_h), (10, 10, 10, 200))
    img.paste(bar, (0, bar_y), bar)

    # Red accent line at top of bar
    draw.rectangle([0, bar_y, w, bar_y + 3], fill=(204, 34, 34, 255))

    # Name text
    font_name = _get_font(FONT_SANS_BOLD, 40)
    font_title = _get_font(FONT_SANS, 28)

    draw.text((60, bar_y + 20), name, font=font_name, fill=(255, 255, 255, 255))
    draw.text((60, bar_y + 70), title, font=font_title, fill=(160, 160, 160, 255))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    logger.info(f"  Lower third: {name} | {title}")
    return output_path


# ═══════════════════════════════════════════════════════════════
# STORY TITLE CARD (2 seconds)
# ═══════════════════════════════════════════════════════════════

def render_title_card(headline: str, story_number: int,
                      output_path: str, w: int = W, h: int = H) -> str:
    """
    Render a 2-second story title card video.
    - Story number in large red text
    - Headline in white
    - Subtle grid effect in background
    - Fades in/out
    """
    total_frames = 2 * FPS  # 60 frames
    frame_dir = tempfile.mkdtemp(prefix="title_frames_")

    font_num = _get_font(FONT_MONO_BOLD, 160)
    font_head = _get_font(FONT_SANS_BOLD, 56)

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (w, h), BG_COLOR)
            draw = ImageDraw.Draw(img)

            # Subtle grid
            grid_color = (15, 20, 15)
            for gx in range(0, w, 60):
                draw.line([(gx, 0), (gx, h)], fill=grid_color, width=1)
            for gy in range(0, h, 60):
                draw.line([(0, gy), (w, gy)], fill=grid_color, width=1)

            # Fade alpha
            if f < 15:
                alpha = _ease_in_out(f / 14)
            elif f > total_frames - 15:
                alpha = _ease_in_out((total_frames - 1 - f) / 14)
            else:
                alpha = 1.0

            # Story number
            num_text = f"{story_number:02d}"
            num_color = tuple(int(c * alpha) for c in RED)
            bbox_n = font_num.getbbox(num_text)
            nw = bbox_n[2] - bbox_n[0]
            draw.text(((w - nw) // 2, h // 2 - 140), num_text,
                     font=font_num, fill=num_color)

            # Headline (word-wrap if needed)
            head_color = tuple(int(c * alpha) for c in WHITE)
            _draw_wrapped_text(draw, headline, font_head, head_color,
                             w // 2, h // 2 + 40, max_width=w - 200)

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS
        )
        logger.info(f"  Title card: #{story_number:02d} — {headline}")
        return output_path

    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# SIGNAL vs NOISE CARD
# ═══════════════════════════════════════════════════════════════

def render_signal_noise_card(signal: str, noise: str, wildcard: str,
                             output_path: str, w: int = W, h: int = H) -> str:
    """Render a static card for the Signal vs Noise segment."""
    img = Image.new("RGB", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_header = _get_font(FONT_MONO_BOLD, 48)
    font_label = _get_font(FONT_SANS_BOLD, 32)
    font_body = _get_font(FONT_SANS, 28)

    # Header
    header_text = "SIGNAL vs NOISE"
    bbox = font_header.getbbox(header_text)
    hw = bbox[2] - bbox[0]
    draw.text(((w - hw) // 2, 120), header_text, font=font_header, fill=RED)

    # Divider
    draw.rectangle([w // 2 - 300, 190, w // 2 + 300, 193], fill=RED)

    # Signal
    draw.text((200, 260), "SIGNAL", font=font_label, fill=(34, 204, 34))
    _draw_wrapped_text(draw, signal, font_body, WHITE, w // 2, 320, max_width=w - 400)

    # Noise
    draw.text((200, 480), "NOISE", font=font_label, fill=(204, 34, 34))
    _draw_wrapped_text(draw, noise, font_body, GRAY, w // 2, 540, max_width=w - 400)

    # Wildcard
    draw.text((200, 700), "WILDCARD", font=font_label, fill=(204, 170, 34))
    _draw_wrapped_text(draw, wildcard, font_body, GRAY, w // 2, 760, max_width=w - 400)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


# ═══════════════════════════════════════════════════════════════
# DARK BACKGROUND WITH BRANDING
# ═══════════════════════════════════════════════════════════════

def render_branded_bg(output_path: str, text: str = None,
                      w: int = W, h: int = H) -> str:
    """Render a branded dark background with optional centered text."""
    img = Image.new("RGB", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Subtle grid
    grid_color = (15, 20, 15)
    for gx in range(0, w, 80):
        draw.line([(gx, 0), (gx, h)], fill=grid_color, width=1)
    for gy in range(0, h, 80):
        draw.line([(0, gy), (w, gy)], fill=grid_color, width=1)

    # Thin red line at top
    draw.rectangle([0, 0, w, 3], fill=RED)

    # "PULSE CHECK" watermark bottom-right
    font_wm = _get_font(FONT_MONO, 18)
    draw.text((w - 200, h - 40), "PULSE CHECK", font=font_wm, fill=(40, 40, 40))

    if text:
        font = _get_font(FONT_SANS_BOLD, 42)
        _draw_wrapped_text(draw, text, font, WHITE, w // 2, h // 2, max_width=w - 300)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str,
                       font: ImageFont.FreeTypeFont, color: tuple,
                       center_x: int, top_y: int,
                       max_width: int = 1600, line_spacing: int = 10):
    """Draw text centered, word-wrapping to max_width."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    y = top_y
    for line in lines:
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        draw.text((center_x - lw // 2, y), line, font=font, fill=color)
        y += lh + line_spacing


# ═══════════════════════════════════════════════════════════════
# ANIMATED OVERLAYS — for host dialogue segments
# ═══════════════════════════════════════════════════════════════

def render_stat_overlay(stat_value: str, label: str, output_path: str,
                        w: int = 500, h: int = 120) -> str:
    """Render a stat card as transparent PNG.
    Red accent bar left, big number, smaller label.
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Semi-transparent dark background with rounded feel
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=8, fill=(10, 10, 10, 200))
    # Red accent bar on left
    draw.rectangle([0, 0, 6, h], fill=(204, 34, 34, 255))

    font_big = _get_font(FONT_SANS_BOLD, 48)
    font_small = _get_font(FONT_SANS, 20)

    draw.text((20, 12), stat_value, font=font_big, fill=(255, 255, 255, 255))
    draw.text((20, 72), label.upper(), font=font_small, fill=(160, 160, 160, 255))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


def render_quote_overlay(quote_text: str, attribution: str, output_path: str,
                         w: int = 900, max_h: int = 300) -> str:
    """Render a quote card as transparent PNG.
    Italic-style text with attribution in red.
    """
    font_quote = _get_font(FONT_SANS, 28)
    font_attr = _get_font(FONT_SANS_BOLD, 22)

    # Pre-calculate height needed
    import textwrap
    wrapped = textwrap.fill(quote_text, width=50)
    lines = wrapped.split("\n")
    line_h = 36
    needed_h = min(len(lines) * line_h + 80, max_h)

    img = Image.new("RGBA", (w, needed_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Semi-transparent dark background
    draw.rounded_rectangle([0, 0, w - 1, needed_h - 1], radius=8, fill=(10, 10, 10, 210))
    # Left red accent
    draw.rectangle([0, 8, 4, needed_h - 8], fill=(204, 34, 34, 255))

    # Quote text
    y = 20
    for line in lines:
        draw.text((24, y), f"\u201c{line}\u201d" if line == lines[0] else line,
                  font=font_quote, fill=(220, 220, 220, 255))
        y += line_h

    # Attribution
    if attribution:
        draw.text((w - 30 - len(attribution) * 10, y + 5),
                  f"\u2014 {attribution}",
                  font=font_attr, fill=(204, 34, 34, 255))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


def render_host_lower_third(name: str, title: str, output_path: str,
                             w: int = W, h: int = 160) -> str:
    """Render host lower third as transparent PNG at full frame width.
    Red accent bar, name in bold white, title in gray.
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Semi-transparent bar
    bar = Image.new("RGBA", (500, h), (10, 10, 10, 200))
    img.paste(bar, (0, 0), bar)

    # Red accent line at left edge
    draw.rectangle([0, 0, 5, h], fill=(204, 34, 34, 255))
    # Red top line
    draw.rectangle([0, 0, 500, 3], fill=(204, 34, 34, 255))

    font_name = _get_font(FONT_SANS_BOLD, 40)
    font_title = _get_font(FONT_SANS, 24)
    font_brand = _get_font(FONT_MONO, 16)

    draw.text((20, 20), name, font=font_name, fill=(255, 255, 255, 255))
    draw.text((20, 70), title, font=font_title, fill=(160, 160, 160, 255))
    draw.text((20, 110), "PROTOCOL PULSE", font=font_brand, fill=(100, 100, 100, 255))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


def render_topic_label(topic: str, output_path: str,
                       max_w: int = 500, h: int = 50) -> str:
    """Render topic label as transparent PNG for top-right corner."""
    font = _get_font(FONT_SANS_BOLD, 22)
    bbox = font.getbbox(topic.upper())
    text_w = bbox[2] - bbox[0]
    w = min(text_w + 40, max_w)

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark semi-transparent background
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=4, fill=(10, 10, 10, 180))
    # Red bottom line
    draw.rectangle([0, h - 3, w, h], fill=(204, 34, 34, 255))

    draw.text((20, 12), topic.upper()[:40], font=font, fill=(220, 220, 220, 255))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


def render_watermark_overlay(source_path: str, output_path: str,
                              max_size: int = 80) -> str:
    """Create a semi-transparent watermark PNG from source logo."""
    try:
        wm = Image.open(source_path).convert("RGBA")
        # Scale to max_size maintaining aspect ratio
        ratio = min(max_size / wm.width, max_size / wm.height)
        new_w = int(wm.width * ratio)
        new_h = int(wm.height * ratio)
        wm = wm.resize((new_w, new_h), Image.LANCZOS)

        # Make semi-transparent (40% opacity)
        data = wm.getdata()
        new_data = [(r, g, b, int(a * 0.4)) for r, g, b, a in data]
        wm.putdata(new_data)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        wm.save(output_path)
        return output_path
    except Exception as e:
        logger.warning(f"  Watermark render failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════
# TEXT EXTRACTION — for overlay data
# ═══════════════════════════════════════════════════════════════

def extract_overlay_data(text: str) -> list:
    """Extract numbers, percentages, dollar amounts, and quotes from dialogue text.
    Returns list of overlay descriptors for rendering.
    """
    import re
    overlays = []
    if not text:
        return overlays

    # Dollar amounts: $97,500, $1.2 billion, $500M
    dollars = re.findall(r'\$[\d,.]+\s*(?:billion|million|trillion|B|M|T|K)\b|\$[\d,.]+',
                         text, re.IGNORECASE)
    for d in dollars:
        overlays.append({"type": "stat", "value": d.strip(), "label": "VALUE"})

    # Percentages: 47%, 2.3%, -5%
    pcts = re.findall(r'-?[\d.]+%', text)
    for p in pcts:
        if p not in [d for o in overlays for d in [o.get("value", "")]]:
            overlays.append({"type": "stat", "value": p, "label": "CHANGE"})

    # Large numbers: 2.1 million, 500,000
    big_nums = re.findall(r'[\d,.]+\s*(?:billion|million|trillion)', text, re.IGNORECASE)
    for n in big_nums:
        val = n.strip()
        if val not in [o.get("value", "") for o in overlays]:
            overlays.append({"type": "stat", "value": val, "label": "FIGURE"})

    # Quoted text (for quote overlays)
    quotes = re.findall(r'"([^"]{10,})"', text)
    for q in quotes[:1]:  # Max 1 quote per segment
        overlays.append({"type": "quote", "value": q})

    return overlays
