#!/usr/bin/env python3
"""Generate lower-third PNGs for each clip in the EDL.
Libre Franklin, white text on 60% black bar, bottom-left, 1920x1080 with alpha."""
import json
import os
from PIL import Image, ImageDraw, ImageFont

BASE = "/home/ultron/protocol_pulse/segment_v1"
EDL_FILE = os.path.join(BASE, "edl_v2.json")
OUT_DIR = os.path.join(BASE, "lower_thirds")
os.makedirs(OUT_DIR, exist_ok=True)

# Try to find Libre Franklin; fall back to DejaVu Sans
FONT_PATHS = [
    "/usr/share/fonts/truetype/libre-franklin/LibreFranklin-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_PATH = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        FONT_PATH = fp
        break

FONT_REG_PATHS = [
    "/usr/share/fonts/truetype/libre-franklin/LibreFranklin-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_REG = None
for fp in FONT_REG_PATHS:
    if os.path.exists(fp):
        FONT_REG = fp
        break


def make_lower_third(channel_name, video_title, output_path, w=1920, h=1080):
    """Create a 1920x1080 RGBA PNG with a lower-third bar."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Bar dimensions
    bar_h = 80
    bar_y = h - bar_h - 60  # 60px from bottom
    bar_x = 40
    bar_w = min(len(channel_name) * 22 + len(video_title[:50]) * 11 + 120, w - 80)
    bar_w = max(bar_w, 600)
    bar_w = min(bar_w, w - 80)

    # Draw semi-transparent black bar (60% opacity = 153/255)
    bar = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 153))
    img.paste(bar, (bar_x, bar_y), bar)

    # Channel name (bold, larger)
    font_bold = ImageFont.truetype(FONT_PATH, 28) if FONT_PATH else ImageFont.load_default()
    font_reg = ImageFont.truetype(FONT_REG, 20) if FONT_REG else ImageFont.load_default()

    # Channel name
    draw.text((bar_x + 20, bar_y + 10), channel_name, fill=(255, 255, 255, 255), font=font_bold)

    # Video title (truncated, smaller)
    title_truncated = video_title[:55] + ("..." if len(video_title) > 55 else "")
    draw.text((bar_x + 20, bar_y + 44), title_truncated, fill=(220, 220, 220, 230), font=font_reg)

    img.save(output_path, "PNG")
    return output_path


def generate_all():
    with open(EDL_FILE) as f:
        edl = json.load(f)

    paths = []

    # Hook lower third
    if edl.get("hook") and edl["hook"].get("channel"):
        h = edl["hook"]
        p = os.path.join(OUT_DIR, "lt_hook.png")
        make_lower_third(h["channel"], h.get("video_title", ""), p)
        paths.append(("hook", p))
        print(f"  hook: {h['channel']} -> {p}")

    # Clip lower thirds
    for clip in edl.get("clips", []):
        idx = clip["index"]
        p = os.path.join(OUT_DIR, f"lt_clip_{idx:02d}.png")
        make_lower_third(clip["channel"], clip.get("video_title", ""), p)
        paths.append((f"clip_{idx}", p))
        print(f"  clip {idx}: {clip['channel']} -> {p}")

    print(f"\nGenerated {len(paths)} lower-third PNGs in {OUT_DIR}")
    return paths


if __name__ == "__main__":
    print("=== GENERATING LOWER-THIRD PNGs ===")
    generate_all()
