#!/usr/bin/env python3
"""Shout-out scene: animated channel nodes with avatars, glowing rings, light rays.

render_shoutout(channels, size, vo_wav, out_path)
  - channels: list of dicts [{name, handle, avatar_path}, ...]
  - size: (1920,1080) for 16:9 or (1080,1920) for 9:16
  - vo_wav: path to sign-off VO WAV (1.0s pre-roll silence before VO starts)
  - out_path: output mp4

Scene timing:
  0.00 s        – scene start, BGM continues, black + light rays
  0.25*i s      – node i fade+rise in (0.45s ease-out)
  1.00 s        – VO starts
  vo_end s      – VO ends
  vo_end+0.8 s  – scene end with 0.4s fade to black
"""
import os, sys, subprocess, math, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

FPS = 24
BRAND_RED = (255, 26, 26)  # #FF1A1A
PP_MARK = "/home/ultron/protocol_pulse/brand/2026-11/pp_mark_wave_400.png"

FONT_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_REG_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


LABEL_MIN_GAP = 12      # px at 1080p between neighbouring credit labels on the 16:9 row: the tightest gap PBX approved
                        # (the v2f card, 'The Bitcoin Layer' / 'Bitcoin Magazine', 12 px as drawn)
LABEL_FIT_GAP = 40      # px at 1080p: a card that must change is sized for a clear gap, not the bare minimum
LABEL_MARGIN = 20       # px at 1080p kept between any credit label and the frame edge
LABEL_MIN_SCALE = 0.6   # labels are shrunk no further than this; a card that would need it is refused, never drawn touching


def _ink(font, text, cx):
    """The drawn ink extent [left, right) of `text` centred on cx exactly as render_shoutout draws it."""
    x0, _, x1, _ = font.getbbox(text)
    left = cx - (x1 - x0) // 2 + x0
    return left, left + (x1 - x0)


def fit_label_sizes(names, handles, xs, frame_w, name_size, handle_size, font_bold, font_reg, scale=1.0, row=True):
    """The credits labels never touch and never leave the frame (orchestrator list 2026-11-12: on the 16:9 card
    'Saifedean Ammous' ran into 'What Bitcoin Did'). Returns the largest (name, handle) font sizes, name_size /
    handle_size at most and scaled together, at which every label keeps LABEL_MARGIN * scale inside the frame and, on a
    row (16:9; the 9:16 stack has one label per line), neighbouring labels keep their gap. Labels that keep
    LABEL_MIN_GAP * scale at the original sizes keep those sizes exactly (the protected references render unchanged);
    a card that must change is sized for LABEL_FIT_GAP * scale. Raises RuntimeError when that needs less than
    LABEL_MIN_SCALE: fail closed, never a card with labels touching."""
    margin = LABEL_MARGIN * scale

    def fits(texts, font, gap):
        ex = [_ink(font, t, x) for t, x in zip(texts, xs) if t]
        if any(l < margin or r > frame_w - margin for l, r in ex):
            return False
        return not row or all(b[0] - a[1] >= gap for a, b in zip(ex, ex[1:]))

    if fits(names, ImageFont.truetype(font_bold, name_size), LABEL_MIN_GAP * scale) and \
            fits(handles, ImageFont.truetype(font_reg, handle_size), LABEL_MIN_GAP * scale):
        return name_size, handle_size
    for ns in range(name_size - 1, int(math.ceil(name_size * LABEL_MIN_SCALE)) - 1, -1):
        hs = max(1, int(round(handle_size * ns / name_size)))
        if fits(names, ImageFont.truetype(font_bold, ns), LABEL_FIT_GAP * scale) and \
                fits(handles, ImageFont.truetype(font_reg, hs), LABEL_FIT_GAP * scale):
            return ns, hs
    raise RuntimeError(f"STOP: the credits labels {list(names)} do not fit without touching even at "
                       f"{LABEL_MIN_SCALE:.0%} size")


def _find_font(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def _ease_out(t):
    """Ease-out: decelerating from start."""
    return 1.0 - (1.0 - min(1.0, max(0.0, t))) ** 3


def _circle_mask(diameter):
    """Create a circular alpha mask."""
    mask = Image.new("L", (diameter, diameter), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, diameter - 1, diameter - 1], fill=255)
    return mask


def _draw_glow_ring(draw, cx, cy, radius, ring_width, color, glow_alpha):
    """Draw a glowing ring around a point."""
    r, g, b = color
    for offset in range(ring_width + 6, 0, -1):
        alpha = int(glow_alpha * max(0, 1 - (offset / (ring_width + 6))))
        draw.ellipse(
            [cx - radius - offset, cy - radius - offset,
             cx + radius + offset, cy + radius + offset],
            outline=(r, g, b, alpha), width=1)


def _render_light_rays(w, h, frame_idx, total_frames, seed=42):
    """Render drifting diagonal red light rays on black."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = np.random.RandomState(seed)

    r, g, b = BRAND_RED
    for layer in range(2):
        speed = 0.3 + layer * 0.2
        base_alpha = 18 - layer * 5
        num_rays = 6
        for i in range(num_rays):
            angle = rng.uniform(30, 60)
            base_x = rng.uniform(-w * 0.3, w * 1.3)
            drift = frame_idx * speed * (1.5 + layer)
            x = base_x + drift
            x = x % (w * 1.6) - w * 0.3

            ray_w = rng.randint(40, 120)
            for dx in range(-ray_w // 2, ray_w // 2):
                falloff = 1.0 - abs(dx) / (ray_w / 2)
                alpha = int(base_alpha * falloff)
                if alpha < 1:
                    continue
                x1 = int(x + dx)
                y1 = 0
                x2 = int(x + dx + h * math.tan(math.radians(angle)))
                y2 = h
                draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, alpha), width=1)

    return img


def _render_grain(w, h, frame_idx, seed=42):
    """Render animated film grain."""
    rng = np.random.RandomState(seed + frame_idx)
    noise = rng.randint(0, 30, (h, w), dtype=np.uint8)
    grain = Image.fromarray(noise, mode="L").convert("RGBA")
    grain.putalpha(Image.fromarray(noise, mode="L"))
    return grain


def render_shoutout(channels, size=(1920, 1080), vo_wav=None, out_path=None):
    """Render the shout-out scene.

    Args:
        channels: list of dicts with keys: name, handle, avatar_path
        size: (width, height) — (1920,1080) or (1080,1920)
        vo_wav: path to sign-off VO WAV
        out_path: output mp4 path
    Returns:
        True if successful
    """
    w, h = size
    is_vertical = h > w

    vo_dur = _get_duration(vo_wav) if vo_wav else 5.0
    pre_roll = 1.0
    post_hold = 0.8
    fade_dur = 0.4
    total_dur = pre_roll + vo_dur + post_hold
    total_frames = int(total_dur * FPS)

    print(f"  Shoutout: {w}x{h}, {total_dur:.2f}s ({total_frames} frames)")
    print(f"  VO: {vo_dur:.2f}s, pre-roll: {pre_roll}s, post-hold: {post_hold}s")

    # Scale factor relative to 1080p
    scale = min(w, h) / 1080.0

    # Node dimensions
    avatar_diam = int(260 * scale)
    name_size = int(46 * scale)
    handle_size = int(32 * scale)
    ring_width = int(4 * scale)
    ring_gap = int(8 * scale)
    node_spacing_v = int(80 * scale)

    font_bold = _find_font(FONT_BOLD_PATHS)
    font_reg = _find_font(FONT_REG_PATHS)
    name_font = ImageFont.truetype(font_bold, name_size) if font_bold else ImageFont.load_default()
    handle_font = ImageFont.truetype(font_reg, handle_size) if font_reg else ImageFont.load_default()

    # Load avatars, mask to circles
    node_data = []
    for ch in channels:
        avatar = None
        if ch.get("avatar_path") and os.path.exists(ch["avatar_path"]):
            avatar = Image.open(ch["avatar_path"]).convert("RGBA")
            avatar = avatar.resize((avatar_diam, avatar_diam), Image.LANCZOS)
            mask = _circle_mask(avatar_diam)
            # Apply circle mask
            result = Image.new("RGBA", (avatar_diam, avatar_diam), (0, 0, 0, 0))
            result.paste(avatar, (0, 0), mask)
            avatar = result
        else:
            # Fallback: initials in red ring
            avatar = Image.new("RGBA", (avatar_diam, avatar_diam), (0, 0, 0, 0))
            d = ImageDraw.Draw(avatar)
            d.ellipse([ring_width, ring_width, avatar_diam - ring_width - 1, avatar_diam - ring_width - 1],
                       fill=(30, 30, 30, 255))
            d.ellipse([0, 0, avatar_diam - 1, avatar_diam - 1],
                       outline=BRAND_RED + (255,), width=ring_width)
            initials = "".join(word[0].upper() for word in ch["name"].split()[:2])
            init_font = ImageFont.truetype(font_bold, int(avatar_diam * 0.35)) if font_bold else ImageFont.load_default()
            bbox = d.textbbox((0, 0), initials, font=init_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            d.text((avatar_diam // 2 - tw // 2, avatar_diam // 2 - th // 2),
                   initials, fill=(255, 255, 255, 255), font=init_font)
            print(f"  WARNING: Using initials fallback for {ch['name']}")

        node_data.append({"avatar": avatar, "name": ch["name"], "handle": ch["handle"]})

    # Calculate node positions
    n = len(node_data)
    node_height = avatar_diam + 10 + name_size + 5 + handle_size

    if is_vertical:
        # 9:16: stacked vertically in middle third
        total_stack = n * node_height + (n - 1) * node_spacing_v
        start_y = (h - total_stack) // 2
        positions = []
        for i in range(n):
            cx = w // 2
            cy = start_y + i * (node_height + node_spacing_v) + avatar_diam // 2
            positions.append((cx, cy))
    else:
        # 16:9: three in a row, equal spacing
        total_row_w = n * avatar_diam + (n - 1) * int(200 * scale)
        start_x = (w - total_row_w) // 2 + avatar_diam // 2
        cy = h // 2 - int(30 * scale)
        positions = []
        for i in range(n):
            cx = start_x + i * (avatar_diam + int(200 * scale))
            positions.append((cx, cy))

    if font_bold and font_reg:        # labels never touch or leave the frame; unchanged sizes whenever they already fit
        fit = fit_label_sizes([nd["name"] for nd in node_data], [nd["handle"] for nd in node_data],
                              [p[0] for p in positions], w, name_size, handle_size, font_bold, font_reg,
                              scale=scale, row=not is_vertical)
        if fit != (name_size, handle_size):
            print(f"  Labels: {name_size}/{handle_size} px -> {fit[0]}/{fit[1]} px (credits labels must not touch)")
            name_size, handle_size = fit
            name_font = ImageFont.truetype(font_bold, name_size)
            handle_font = ImageFont.truetype(font_reg, handle_size)

    # PP mark
    mark_img = None
    mark_size = int(110 * scale)
    if os.path.exists(PP_MARK):
        mark_img = Image.open(PP_MARK).convert("RGBA")
        mark_img = mark_img.resize((mark_size, mark_size), Image.LANCZOS)
    mark_x = w - mark_size - int(20 * scale)
    mark_y = h - mark_size - int(20 * scale)

    # Animation timing
    # Node i enters at 0.25*i seconds, fade+rise over 0.45s
    node_enter_start = [0.25 * i for i in range(n)]
    node_enter_dur = 0.45  # seconds
    rise_px = int(30 * scale)  # pixels to rise

    # Glow pulse: period 2.4s, phase offset per node
    glow_period = 2.4
    glow_phase_offset = [i * 0.8 for i in range(n)]

    # Fade to black at end
    fade_start_time = total_dur - fade_dur

    # Render frames
    frames_dir = os.path.join(os.path.dirname(out_path), "shoutout_frames_raw")
    os.makedirs(frames_dir, exist_ok=True)

    print(f"  Rendering {total_frames} frames...", end="", flush=True)

    for fi in range(total_frames):
        t = fi / FPS  # current time in seconds

        # Base: black
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 255))

        # Light rays
        rays = _render_light_rays(w, h, fi, total_frames)
        frame = Image.alpha_composite(frame, rays)

        # Film grain
        grain = _render_grain(w, h, fi)
        frame = Image.alpha_composite(frame, grain)

        # Draw nodes
        for i, (cx, cy_base) in enumerate(positions):
            enter_t = (t - node_enter_start[i]) / node_enter_dur
            if enter_t < 0:
                continue  # not yet entered

            # Entry animation: opacity + rise
            entry_alpha = min(1.0, _ease_out(enter_t))
            rise_offset = int(rise_px * (1.0 - min(1.0, _ease_out(enter_t))))
            cy = cy_base + rise_offset

            # Glow pulse
            pulse_t = (t - glow_phase_offset[i]) / glow_period
            glow_intensity = 0.5 + 0.5 * math.sin(2 * math.pi * pulse_t)
            glow_alpha = int(120 * glow_intensity * entry_alpha)

            # Draw glow ring
            ring_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ring_draw = ImageDraw.Draw(ring_layer)
            ring_r = avatar_diam // 2 + ring_gap

            # Outer glow (soft)
            for offset in range(12, 0, -1):
                a = int(glow_alpha * max(0, 1 - offset / 12))
                ring_draw.ellipse(
                    [cx - ring_r - offset, cy - ring_r - offset,
                     cx + ring_r + offset, cy + ring_r + offset],
                    outline=BRAND_RED + (a,), width=1)

            # Core ring
            core_alpha = int(200 * entry_alpha)
            ring_draw.ellipse(
                [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                outline=BRAND_RED + (core_alpha,), width=ring_width)

            frame = Image.alpha_composite(frame, ring_layer)

            # Avatar
            nd = node_data[i]
            av = nd["avatar"].copy()
            if entry_alpha < 1.0:
                av_arr = np.array(av)
                av_arr[:, :, 3] = (av_arr[:, :, 3].astype(float) * entry_alpha).astype(np.uint8)
                av = Image.fromarray(av_arr)
            ax = cx - avatar_diam // 2
            ay = cy - avatar_diam // 2
            frame.paste(av, (ax, ay), av)

            # Name + handle text
            text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_layer)

            name_text = nd["name"]
            name_bbox = text_draw.textbbox((0, 0), name_text, font=name_font)
            name_tw = name_bbox[2] - name_bbox[0]
            name_x = cx - name_tw // 2
            name_y = cy + avatar_diam // 2 + 10 + rise_offset
            text_alpha = int(255 * entry_alpha)
            text_draw.text((name_x, name_y), name_text,
                          fill=(255, 255, 255, text_alpha), font=name_font)

            handle_text = nd["handle"]
            handle_bbox = text_draw.textbbox((0, 0), handle_text, font=handle_font)
            handle_tw = handle_bbox[2] - handle_bbox[0]
            handle_x = cx - handle_tw // 2
            handle_y = name_y + name_size + 5
            text_draw.text((handle_x, handle_y), handle_text,
                          fill=(180, 180, 180, int(text_alpha * 0.85)), font=handle_font)

            frame = Image.alpha_composite(frame, text_layer)

        # PP mark lower-right
        if mark_img:
            mark_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            mark_layer.paste(mark_img, (mark_x, mark_y), mark_img)
            frame = Image.alpha_composite(frame, mark_layer)

        # Fade to black at end
        if t >= fade_start_time:
            fade_progress = (t - fade_start_time) / fade_dur
            fade_alpha = int(255 * min(1.0, fade_progress))
            black = Image.new("RGBA", (w, h), (0, 0, 0, fade_alpha))
            frame = Image.alpha_composite(frame, black)

        # Convert and save
        frame_rgb = frame.convert("RGB")
        frame_path = os.path.join(frames_dir, f"frame_{fi:05d}.png")
        frame_rgb.save(frame_path, "PNG")

        if fi % 24 == 0:
            print(".", end="", flush=True)

    print(f" done")

    # Encode: frames + VO audio (with 1.0s pre-roll silence)
    # Build audio: 1.0s silence + VO
    silence_wav = os.path.join(os.path.dirname(out_path), "shoutout_silence.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(pre_roll), "-c:a", "pcm_s16le", silence_wav,
    ], capture_output=True, timeout=10)

    combined_wav = os.path.join(os.path.dirname(out_path), "shoutout_audio.wav")
    audio_list = os.path.join(os.path.dirname(out_path), "shoutout_audio_list.txt")
    with open(audio_list, "w") as f:
        f.write(f"file '{silence_wav}'\n")
        if vo_wav:
            f.write(f"file '{os.path.abspath(vo_wav)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list,
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", combined_wav,
    ], capture_output=True, timeout=30)

    # Pad audio to total_dur if needed
    padded_wav = os.path.join(os.path.dirname(out_path), "shoutout_audio_padded.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", combined_wav,
        "-af", f"apad=whole_dur={total_dur}",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", padded_wav,
    ], capture_output=True, timeout=30)

    # Encode video
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", padded_wav,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        out_path,
    ], capture_output=True, timeout=300)

    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        dur = _get_duration(out_path)
        print(f"  Output: {out_path} ({dur:.2f}s, {os.path.getsize(out_path):,} bytes)")
        return True

    print(f"  ERROR: Shoutout render failed")
    return False


def save_qa_frames(video_path, output_jpg, num_frames=6):
    """Save tiled QA frames from the shoutout scene."""
    dur = _get_duration(video_path)
    frames_dir = os.path.join(os.path.dirname(output_jpg), "shoutout_qa_frames")
    os.makedirs(frames_dir, exist_ok=True)

    for i in range(num_frames):
        ts = dur * (i + 0.5) / num_frames
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts), "-i", video_path,
            "-vframes", "1", "-q:v", "2",
            os.path.join(frames_dir, f"frame_{i:02d}.jpg"),
        ], capture_output=True, timeout=30)

    cols = 3
    rows = (num_frames + cols - 1) // cols
    subprocess.run([
        "ffmpeg", "-y",
        "-i", os.path.join(frames_dir, "frame_%02d.jpg"),
        "-vf", f"tile={cols}x{rows}:padding=4:color=black",
        "-q:v", "3", output_jpg,
    ], capture_output=True, timeout=30)

    return os.path.exists(output_jpg)


if __name__ == "__main__":
    import json

    BASE = "/home/ultron/protocol_pulse/segment_v1"
    QA = os.path.join(BASE, "qa_v7")
    os.makedirs(QA, exist_ok=True)

    with open(os.path.join(BASE, "publish", "partner_handles.json")) as f:
        partner_handles = json.load(f)

    with open(os.path.join(BASE, "edl_v2.json")) as f:
        edl = json.load(f)

    # Build channel list in EDL order
    seen = []
    seen_names = set()
    hook_ch = edl["hook"]["channel"]
    if hook_ch not in seen_names:
        seen.append(hook_ch)
        seen_names.add(hook_ch)
    for clip in edl["clips"]:
        ch = clip["channel"]
        if ch not in seen_names:
            seen.append(ch)
            seen_names.add(ch)

    channels = []
    for name in seen:
        slug = name.lower().replace(" ", "_")
        avatar_path = os.path.join(BASE, "brand", "avatars", f"{slug}.png")
        handle_info = partner_handles.get(name, {})
        yt_handle = handle_info.get("youtube", f"@{slug}")
        channels.append({
            "name": name,
            "handle": yt_handle,
            "avatar_path": avatar_path,
        })

    vo_wav = os.path.join(BASE, "vo_audio", "vo_signoff_pbx_v2.wav")

    # Render 16:9
    print("\n=== SHOUTOUT 16:9 ===")
    out_16 = os.path.join(QA, "shoutout_16x9.mp4")
    render_shoutout(channels, size=(1920, 1080), vo_wav=vo_wav, out_path=out_16)

    # Render 9:16
    print("\n=== SHOUTOUT 9:16 ===")
    out_9 = os.path.join(QA, "shoutout_9x16.mp4")
    render_shoutout(channels, size=(1080, 1920), vo_wav=vo_wav, out_path=out_9)

    # QA frames
    print("\n=== QA FRAMES ===")
    qa_jpg = os.path.join(QA, "shoutout_frames.jpg")
    save_qa_frames(out_16, qa_jpg)
    if os.path.exists(qa_jpg):
        print(f"  QA tile: {qa_jpg}")
