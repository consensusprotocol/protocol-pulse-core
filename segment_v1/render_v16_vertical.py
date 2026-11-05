#!/usr/bin/env python3
"""Render segment_v16_vertical.mp4 (9:16, 1080x1920, 24fps, full program parity).

Changes from v15:
  1. Full program parity: ALL 9 segments from horizontal, same order, same audio
  2. Audio extracted from horizontal out/segment_v12.mp4 — identical by construction
  3. Three layouts by hand table: single, stack2, grid
  4. stack2: two source rects each scaled to 1080x960, speaker TOP, second BOTTOM
  5. G11 parity gate: duration within 0.25s AND same segment count as horizontal
  6. G10 chyron-safe: CoinDesk clip_02 excludes bottom 110px of source
"""
import json, os, subprocess, sys, time, math, struct, wave, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = "/home/ultron/protocol_pulse/segment_v1"
QA = os.path.join(BASE, "qa_v16")
QA_V3 = os.path.join(BASE, "qa_v3")
QA_V7 = os.path.join(BASE, "qa_v7")
OUT = os.path.join(BASE, "out")
VO_DIR = os.path.join(BASE, "vo_audio")
SOURCES = os.path.join(BASE, "sources")
PP_MARK = os.path.join(BASE, "brand", "2026-11", "pp_mark_wave_alpha.png")
HORIZ_MP4 = os.path.join(OUT, "segment_v12.mp4")
HORIZ_MANIFEST = os.path.join(BASE, "qa_v12", "concat_manifest_16x9.json")

os.makedirs(QA, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
from relay import get_key

FPS = 24
VERT_W = 1080
VERT_H = 1920
CROP_W = 607  # 9:16 crop from 1920 source
CROP_H = 1080
PRE_ROLL = 1.0
ACCENT_COLOR = (247, 147, 26)
DIVIDER_H = 4
OVERRIDES_PATH = os.path.join(BASE, "vertical_overrides_v16.json")

# Clip_01 source layout (BTC Sessions 5-tile podcast)
CLIP01_PANEL_X = (1544, 1920)


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def ease_in_out(t):
    return 0.5 * (1 - math.cos(math.pi * t))


# ── Override file I/O ───────────────────────────────────────────

def _load_overrides():
    if os.path.exists(OVERRIDES_PATH):
        with open(OVERRIDES_PATH) as f:
            return json.load(f)
    return {}


def _save_overrides(data):
    with open(OVERRIDES_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ==============================================================
# LAYOUT A: single (fixed crop on one face, chyron-safe option)
# ==============================================================

def render_single(seg_path, output_path, seg_label, chyron_safe=False):
    """Fixed crop on one face. Lip-activity speaker pick with force_cx override.
    chyron_safe: exclude bottom 110px of 1080 source (CoinDesk)."""
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    print(f"    [A] single crop: {seg_label} (chyron_safe={chyron_safe})")

    overrides = _load_overrides()
    if seg_label in overrides and "force_cx" in overrides[seg_label]:
        chosen_cx = overrides[seg_label]["force_cx"]
        print(f"      Manual override: force_cx={chosen_cx}")
    else:
        chosen_cx = None

    model_path = os.path.join(BASE, "qa_v6", "blaze_face_short_range.tflite")
    base_opts = mp_base_options.BaseOptions(model_asset_path=model_path)
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=base_opts, min_detection_confidence=0.5))

    cap = cv2.VideoCapture(seg_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    n_samples = 12
    sample_indices = [int(frame_count * (i + 0.5) / n_samples) for i in range(n_samples)]

    CLUSTER_W = 200
    person_frames = {}
    prev_patches = {}

    for si, fi in enumerate(sample_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ret, frame_bgr = cap.read()
        if not ret:
            continue
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        grey = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=frame_rgb)
        results = detector.detect(mp_image)

        for det in results.detections:
            bb = det.bounding_box
            cx = bb.origin_x + bb.width // 2
            cluster_key = (cx // CLUSTER_W) * CLUSTER_W

            lip_top = bb.origin_y + int(bb.height * 0.67)
            lip_bot = min(bb.origin_y + bb.height, src_h)
            lip_left = max(0, bb.origin_x)
            lip_right = min(bb.origin_x + bb.width, src_w)
            if lip_bot <= lip_top or lip_right <= lip_left:
                continue
            patch = grey[lip_top:lip_bot, lip_left:lip_right]

            if cluster_key not in person_frames:
                person_frames[cluster_key] = {"cx_vals": [], "diffs": [], "area": 0}

            person_frames[cluster_key]["cx_vals"].append(cx)
            area = patch.shape[0] * patch.shape[1]
            person_frames[cluster_key]["area"] = max(person_frames[cluster_key]["area"], area)

            if cluster_key in prev_patches:
                prev = prev_patches[cluster_key]
                if prev.shape == patch.shape:
                    diff = np.mean(np.abs(patch.astype(float) - prev.astype(float)))
                    person_frames[cluster_key]["diffs"].append(diff / max(area, 1) * 1000)
            prev_patches[cluster_key] = patch.copy()

    cap.release()

    persons = []
    for key, data in person_frames.items():
        if not data["cx_vals"]:
            continue
        median_cx = int(np.median(data["cx_vals"]))
        score = float(np.mean(data["diffs"])) if data["diffs"] else 0.0
        persons.append({"cx": median_cx, "score": round(score, 4)})
    persons.sort(key=lambda p: -p["score"])

    if chosen_cx is None:
        if persons:
            chosen_cx = persons[0]["cx"]
            reason = "lip-activity"
        else:
            chosen_cx = src_w // 2
            reason = "no-faces-center"
    else:
        reason = "force_cx"

    overrides[seg_label] = {
        "layout": "single",
        "persons": persons,
        "chosen_cx": chosen_cx,
        "reason": reason,
    }
    _save_overrides(overrides)

    print(f"      Persons: {len(persons)}")
    for i, p in enumerate(persons):
        marker = " <-- CHOSEN" if p["cx"] == chosen_cx else ""
        print(f"        person_{i}: cx={p['cx']}, lip_score={p['score']}{marker}")
    print(f"      Speaker: cx={chosen_cx} ({reason})")

    # Chyron-safe: exclude bottom 110px → crop height 970, y_offset 0
    if chyron_safe:
        crop_h_src = 970  # 1080 - 110
        crop_y = 0
    else:
        crop_h_src = CROP_H
        crop_y = 0

    crop_x = max(0, min(src_w - CROP_W, chosen_cx - CROP_W // 2))
    crop_rect = f"{crop_x},{crop_y},{CROP_W},{crop_h_src}"
    print(f"      Crop: x={crop_x}, y={crop_y}, w={CROP_W}, h={crop_h_src}")

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", f"crop={CROP_W}:{crop_h_src}:{crop_x}:{crop_y},"
               f"scale={VERT_W}:{VERT_H}:flags=lanczos,setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-an",  # video only — audio muxed from horizontal later
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-300:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True, crop_rect
    print(f"      ERROR: single render failed")
    return False, crop_rect


# ==============================================================
# LAYOUT B: stack2 (two source rects, speaker TOP, other BOTTOM)
# ==============================================================

def _lip_activity_score(seg_path, rect, n_samples=12):
    """Compute lip-activity score for a given source rect (x,y,w,h).
    Returns mean abs frame-diff in lower third of rect."""
    import cv2
    cap = cv2.VideoCapture(seg_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sample_indices = [int(frame_count * (i + 0.5) / n_samples) for i in range(n_samples)]

    rx, ry, rw, rh = rect
    lip_y0 = ry + int(rh * 0.67)
    lip_y1 = ry + rh
    prev_patch = None
    diffs = []

    for fi in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ret, frame = cap.read()
        if not ret:
            continue
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        patch = grey[lip_y0:lip_y1, rx:rx + rw]
        if patch.size == 0:
            continue
        if prev_patch is not None and prev_patch.shape == patch.shape:
            diff = np.mean(np.abs(patch.astype(float) - prev_patch.astype(float)))
            area = max(patch.shape[0] * patch.shape[1], 1)
            diffs.append(diff / area * 1000)
        prev_patch = patch.copy()

    cap.release()
    return round(float(np.mean(diffs)) if diffs else 0.0, 4)


def render_stack2(seg_path, output_path, seg_label, rect_a, rect_b,
                  speaker_rect="a"):
    """Two source rects stacked vertically: speaker on TOP (960px), other BOTTOM (960px).
    Each rect from source (1920x1080) scaled to 1080x960.
    rect_a, rect_b: (x, y, w, h) in source coordinates.
    speaker_rect: 'a' or 'b' — which rect goes on top."""
    import cv2
    print(f"    [B] stack2: {seg_label} (speaker_rect={speaker_rect})")

    # Lip-activity on both rects
    score_a = _lip_activity_score(seg_path, rect_a)
    score_b = _lip_activity_score(seg_path, rect_b)
    print(f"      rect_a lip_score={score_a}, rect_b lip_score={score_b}")

    overrides = _load_overrides()
    entry = overrides.get(seg_label, {})

    # Check for manual speaker_rect override in existing overrides
    if seg_label in overrides and "speaker_rect" in overrides[seg_label]:
        speaker_rect = overrides[seg_label]["speaker_rect"]
        print(f"      Override: speaker_rect={speaker_rect} (from overrides file)")
    else:
        # Use lip-activity to decide
        if score_b > score_a:
            speaker_rect = "b"
        else:
            speaker_rect = "a"
        print(f"      Lip-activity decision: speaker_rect={speaker_rect}")

    entry.update({
        "layout": "stack2",
        "rect_a": list(rect_a),
        "rect_b": list(rect_b),
        "score_a": score_a,
        "score_b": score_b,
        "speaker_rect": speaker_rect,
    })
    overrides[seg_label] = entry
    _save_overrides(overrides)

    if speaker_rect == "a":
        top_rect, bot_rect = rect_a, rect_b
    else:
        top_rect, bot_rect = rect_b, rect_a

    tx, ty, tw, th = top_rect
    bx, by, bw, bh = bot_rect

    half_h = VERT_H // 2  # 960

    # ffmpeg filter: crop two regions, scale each to 1080x960, vstack
    vf = (
        f"split=2[s1][s2];"
        f"[s1]crop={tw}:{th}:{tx}:{ty},scale={VERT_W}:{half_h}:flags=lanczos,setsar=1:1[top];"
        f"[s2]crop={bw}:{bh}:{bx}:{by},scale={VERT_W}:{half_h}:flags=lanczos,setsar=1:1[bot];"
        f"[top][bot]vstack=inputs=2[vout]"
    )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-filter_complex", vf,
        "-map", "[vout]",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-an",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-500:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True
    print(f"      ERROR: stack2 render failed")
    return False


def render_stack2_unequal(seg_path, output_path, seg_label, rect_top, rect_bot):
    """Stack2 variant for clip_04: two rects of different sizes.
    Each 640x540 → scale to 1080x911, center vertically with black bars.
    TOP and BOTTOM are fixed by the caller (no lip-activity decision)."""
    import cv2
    print(f"    [B] stack2-unequal: {seg_label}")

    tx, ty, tw, th = rect_top
    bx, by, bw, bh = rect_bot

    # Each tile 640x540 → 1080x911 (maintain aspect: 1080/640 = 1.6875, 540*1.6875=911.25)
    tile_h = 911
    # Total = 911 + 911 = 1822, remaining = 1920 - 1822 = 98 → 49px bar top/bottom split
    pad_total = VERT_H - 2 * tile_h  # 98
    pad_top = pad_total // 2  # 49
    pad_mid = 0  # no gap between tiles

    vf = (
        f"split=2[s1][s2];"
        f"[s1]crop={tw}:{th}:{tx}:{ty},scale={VERT_W}:{tile_h}:flags=lanczos,setsar=1:1[top];"
        f"[s2]crop={bw}:{bh}:{bx}:{by},scale={VERT_W}:{tile_h}:flags=lanczos,setsar=1:1[bot];"
        f"[top][bot]vstack=inputs=2,"
        f"pad={VERT_W}:{VERT_H}:0:{pad_top}:black,setsar=1:1[vout]"
    )

    overrides = _load_overrides()
    overrides[seg_label] = {
        "layout": "stack2-unequal",
        "rect_top": list(rect_top),
        "rect_bot": list(rect_bot),
        "speaker_rect": "top (Adam O'Brien — verified from transcript)",
    }
    _save_overrides(overrides)

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-filter_complex", vf,
        "-map", "[vout]",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-an",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-500:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True
    print(f"      ERROR: stack2-unequal failed")
    return False


# ==============================================================
# LAYOUT C: grid (clip_01 only — full frame top + guest column bottom)
# ==============================================================

def detect_panel_tiles(frame_arr, panel_x1, panel_x2, min_gutter_h=4):
    """Detect tile boundaries via horizontal edge projection."""
    panel = frame_arr[:, panel_x1:panel_x2, :]
    row_brightness = panel.mean(axis=(1, 2))
    dark_threshold = 25
    in_dark = row_brightness < dark_threshold

    gutters = []
    start = None
    for i in range(len(in_dark)):
        if in_dark[i] and start is None:
            start = i
        elif not in_dark[i] and start is not None:
            if i - start >= min_gutter_h:
                gutters.append((start, i - 1))
            start = None
    if start is not None and len(in_dark) - start >= min_gutter_h:
        gutters.append((start, len(in_dark) - 1))

    tiles = []
    prev_end = 0
    for g_start, g_end in gutters:
        if g_start - prev_end > 30:
            tiles.append((prev_end, g_start - 1))
        prev_end = g_end + 1
    h = frame_arr.shape[0]
    if h - prev_end > 30:
        tiles.append((prev_end, h - 1))
    return tiles


def render_grid(seg_path, output_path):
    """Layout C: TOP = full 16:9 frame scaled to 1080w. BOTTOM = guest column enlarged.
    LANCZOS from full-res source frame (no downscaled intermediate)."""
    import cv2

    print(f"    [C] grid: full frame top + enlarged guest column bottom")

    cap = cv2.VideoCapture(seg_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)
    ret, frame_bgr = cap.read()
    cap.release()
    if not ret:
        print("      ERROR: cannot read frame")
        return False

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    panel_x1, panel_x2 = CLIP01_PANEL_X
    tiles = detect_panel_tiles(frame_rgb, panel_x1, panel_x2)

    if tiles:
        print(f"      Detected {len(tiles)} tiles in guest column:")
        for i, (y1, y2) in enumerate(tiles):
            print(f"        tile_{i}: y={y1}-{y2} (h={y2 - y1 + 1}px)")

    col_y1 = tiles[0][0] if tiles else 0
    col_y2 = tiles[-1][1] if tiles else src_h - 1
    col_x1 = panel_x1
    col_x2 = panel_x2
    col_w = col_x2 - col_x1
    col_h = col_y2 - col_y1 + 1

    # Layout geometry
    top_h = int(src_h * VERT_W / src_w)
    if top_h % 2 != 0:
        top_h += 1
    bottom_h = VERT_H - top_h - DIVIDER_H
    if bottom_h % 2 != 0:
        bottom_h -= 1

    col_aspect = col_w / col_h
    col_scaled_h = bottom_h
    col_scaled_w = int(col_scaled_h * col_aspect)
    if col_scaled_w > VERT_W:
        col_scaled_w = VERT_W
        col_scaled_h = int(col_scaled_w / col_aspect)
    if col_scaled_w % 2 != 0:
        col_scaled_w += 1
    if col_scaled_h % 2 != 0:
        col_scaled_h += 1

    col_x_offset = (VERT_W - col_scaled_w) // 2
    col_y_offset = (bottom_h - col_scaled_h) // 2

    print(f"      Layout: TOP={VERT_W}x{top_h}, BOTTOM={VERT_W}x{bottom_h}")

    # PIL frame-by-frame compositing — LANCZOS from full-res source
    from PIL import Image as PILImage, ImageFilter as PILFilter

    # Background for bottom panel (blurred column from mid-frame)
    col_region_img = PILImage.fromarray(frame_rgb[col_y1:col_y2 + 1, col_x1:col_x2])
    col_bg_scaled = col_region_img.resize((VERT_W, bottom_h), PILImage.LANCZOS)
    col_bg_blurred = col_bg_scaled.filter(PILFilter.GaussianBlur(radius=25))
    divider_strip = PILImage.new("RGB", (VERT_W, DIVIDER_H), ACCENT_COLOR)

    frames_dir = output_path.replace(".mp4", "_frames")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    cap2 = cv2.VideoCapture(seg_path)
    fi = 0
    while True:
        ret2, frm = cap2.read()
        if not ret2:
            break
        frm_rgb = cv2.cvtColor(frm, cv2.COLOR_BGR2RGB)
        pil_frame = PILImage.fromarray(frm_rgb)

        # TOP: full frame LANCZOS from full-res source
        top_strip = pil_frame.resize((VERT_W, top_h), PILImage.LANCZOS)

        # BOTTOM: column crop LANCZOS from full-res source
        col_crop_pil = pil_frame.crop((col_x1, col_y1, col_x2, col_y2 + 1))
        col_scaled_pil = col_crop_pil.resize((col_scaled_w, col_scaled_h), PILImage.LANCZOS)

        bot_strip = col_bg_blurred.copy()
        bot_strip.paste(col_scaled_pil, (col_x_offset, col_y_offset))

        canvas = PILImage.new("RGB", (VERT_W, VERT_H), (0, 0, 0))
        canvas.paste(top_strip, (0, 0))
        canvas.paste(divider_strip, (0, top_h))
        canvas.paste(bot_strip, (0, top_h + DIVIDER_H))

        canvas.save(os.path.join(frames_dir, f"frame_{fi:05d}.png"), "PNG")
        fi += 1
    cap2.release()
    print(f"      Composited {fi} frames")

    r = subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-vf", "setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=600)

    if r.returncode != 0:
        print(f"      encode error: {r.stderr.decode()[-500:]}")

    shutil.rmtree(frames_dir)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True
    print("      ERROR: grid render failed")
    return False


# ==============================================================
# VO VISUAL (native 9:16, video only)
# ==============================================================

def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4, label):
    """R5 native 9:16 VO visual (video-only). Returns path to assembled VO WAV for G6."""
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    print(f"    [VO] visual (9:16): {os.path.basename(output_mp4)}")

    vo_dur = get_duration(vo_wav)
    total_dur = PRE_ROLL + vo_dur
    total_frames = int(total_dur * FPS)
    preroll_frames = int(PRE_ROLL * FPS)

    print(f"      VO: {vo_dur:.2f}s + {PRE_ROLL}s pre-roll = {total_dur:.2f}s ({total_frames} frames)")

    bg_png = os.path.join(QA, f"vo_vert_bg_{label}.png")
    frame_ts = preceding_cut_out - 0.1
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(frame_ts), "-i", preceding_src,
        "-vframes", "1", "-vf", "scale=1920:1080", "-q:v", "2", bg_png,
    ], capture_output=True, timeout=30)

    bg_full = Image.open(bg_png).convert("RGB")
    bg_arr = np.array(bg_full)

    model_path = os.path.join(BASE, "qa_v6", "blaze_face_short_range.tflite")
    base_opts = mp_base_options.BaseOptions(model_asset_path=model_path)
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=base_opts, min_detection_confidence=0.4))

    mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=bg_arr)
    results = detector.detect(mp_image)

    face_cx = 960
    if results.detections:
        best = max(results.detections, key=lambda d: d.bounding_box.width * d.bounding_box.height)
        face_cx = best.bounding_box.origin_x + best.bounding_box.width // 2

    crop_x = max(0, min(1920 - CROP_W, face_cx - CROP_W // 2))
    bg_crop = bg_full.crop((crop_x, 0, crop_x + CROP_W, 1080))
    bg_vert = bg_crop.resize((VERT_W, VERT_H), Image.LANCZOS)
    bg_blurred = bg_vert.filter(ImageFilter.GaussianBlur(radius=6))

    # Audio RMS for waveform
    vo_frames = total_frames - preroll_frames
    try:
        with wave.open(vo_wav, 'rb') as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
        if wf.getsampwidth() == 2:
            samples = struct.unpack(f"<{n * wf.getnchannels()}h", raw)
        else:
            samples = [0] * n
        nc = wf.getnchannels()
        if nc > 1:
            samples = [samples[i] for i in range(0, len(samples), nc)]
        spf = max(1, len(samples) // max(vo_frames, 1))
        rms_vo = []
        for fi in range(vo_frames):
            start = fi * spf
            end = min(start + spf, len(samples))
            chunk = samples[start:end]
            rms_val = (sum(s * s for s in chunk) / max(len(chunk), 1)) ** 0.5 if chunk else 0
            rms_vo.append(min(1.0, rms_val / 12000))
    except Exception:
        rms_vo = [0.1] * vo_frames

    rms_values = [0.0] * preroll_frames + rms_vo

    frames_dir = os.path.join(QA, f"vo_vert_frames_{label}")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    num_bars = 20
    bar_area_w = int(VERT_W * 0.75)
    bar_max_h = int(VERT_H * 0.06)
    bar_y_center = int(VERT_H * 0.89)
    bar_w = bar_area_w // num_bars - 2
    bar_x_start = (VERT_W - bar_area_w) // 2
    band_top = bar_y_center - bar_max_h - 10
    band_bottom = bar_y_center + bar_max_h + 10

    scale_start, scale_end = 1.00, 1.08

    for fi in range(total_frames):
        t = fi / max(total_frames - 1, 1)
        ease_t = ease_in_out(t)
        scale = scale_start + (scale_end - scale_start) * ease_t
        sw = int(VERT_W * scale)
        sh = int(VERT_H * scale)
        scaled = bg_blurred.resize((sw, sh), Image.LANCZOS)
        left = (sw - VERT_W) // 2
        top = (sh - VERT_H) // 2
        frame = scaled.crop((left, top, left + VERT_W, top + VERT_H))

        overlay = Image.new("RGBA", (VERT_W, VERT_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([0, band_top, VERT_W, band_bottom], fill=(0, 0, 0, 204))

        for i in range(num_bars):
            idx = fi - num_bars // 2 + i
            val = rms_values[idx] if 0 <= idx < len(rms_values) else 0
            bar_h = max(2, int(val * bar_max_h))
            x = bar_x_start + i * (bar_w + 2)
            intensity = min(1.0, val * 2.5)
            alpha = int(153 * max(0.3, intensity))
            color = ACCENT_COLOR + (alpha,)
            draw.rectangle([x, bar_y_center - bar_h, x + bar_w, bar_y_center], fill=color)
            draw.rectangle([x, bar_y_center, x + bar_w, bar_y_center + bar_h], fill=color)

        composited = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
        composited.save(os.path.join(frames_dir, f"frame_{fi:05d}.png"), "PNG")

    # Encode video-only
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-vf", "setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120)

    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        dur = get_duration(output_mp4)
        print(f"      Output: {dur:.2f}s")
        shutil.rmtree(frames_dir)
        return True
    print("      ERROR: VO render failed")
    return None


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    t0 = time.time()
    print("=== SEGMENT V16: 9:16 VERTICAL (FULL PROGRAM PARITY) ===\n")

    # ========== STEP 0: Load configs and verify horizontal ==========
    print("=== STEP 0: VERIFY HORIZONTAL + LOAD CONFIGS ===")

    assert os.path.exists(HORIZ_MP4), f"Missing horizontal: {HORIZ_MP4}"
    horiz_dur = get_duration(HORIZ_MP4)
    print(f"  Horizontal: {horiz_dur:.3f}s")

    with open(HORIZ_MANIFEST) as f:
        horiz_manifest = json.load(f)
    horiz_segments = horiz_manifest["segments"]
    print(f"  Horizontal segments: {len(horiz_segments)}")
    for seg in horiz_segments:
        print(f"    {seg['label']}: {seg['start']:.3f}-{seg['end']:.3f} ({seg['type']})")

    with open(os.path.join(BASE, "edl_v2.json")) as f:
        edl = json.load(f)
    with open(os.path.join(BASE, "cuts_final.json")) as f:
        cuts = json.load(f)
    with open(os.path.join(VO_DIR, "VO_MANIFEST.json")) as f:
        vo_manifest = json.load(f)

    # Build cuts map
    cuts_map = {c["clip_id"]: c for c in cuts}

    # ========== STEP 1: Extract horizontal audio ==========
    print("\n=== STEP 1: EXTRACT HORIZONTAL AUDIO ===")

    horiz_audio = os.path.join(QA, "v16_horiz_audio.aac")
    subprocess.run([
        "ffmpeg", "-y", "-i", HORIZ_MP4,
        "-vn", "-acodec", "copy", horiz_audio,
    ], capture_output=True, timeout=60)
    print(f"  Extracted: {horiz_audio} ({os.path.getsize(horiz_audio):,} bytes)")

    # ========== STEP 2: Render each segment (video-only) ==========
    print("\n=== STEP 2: RENDER ALL SEGMENTS (VIDEO-ONLY) ===")

    # Hand table: segment → layout + params
    # Source files
    hook_seg = os.path.join(QA_V3, "final_hook.mp4")
    clip01_seg = os.path.join(QA_V3, "final_clip_01.mp4")
    clip02_seg = os.path.join(QA_V3, "final_clip_02_v5.mp4")
    clip03_seg = os.path.join(QA_V3, "final_clip_03.mp4")
    clip04_seg = os.path.join(QA_V3, "final_clip_04.mp4")

    timings = {}

    # --- hook: stack2 (left=Ben Perrin, right=Nico) ---
    t_start = time.time()
    vert_hook = os.path.join(QA, "v16_vert_hook.mp4")
    render_stack2(hook_seg, vert_hook, "hook",
                  rect_a=(0, 0, 960, 1080),      # left = Ben Perrin
                  rect_b=(960, 0, 960, 1080))     # right = Nico
    timings["hook"] = round(time.time() - t_start, 1)

    # --- vo_intro: VO visual ---
    t_start = time.time()
    hook_cut = cuts_map["hook"]
    hook_src = os.path.join(SOURCES, f"{hook_cut['video_id']}.mp4")
    vert_vo_intro = os.path.join(QA, "v16_vert_vo_intro.mp4")
    render_vo_visual_vert(
        os.path.join(VO_DIR, vo_manifest["intro"]["stem_wav"]),
        hook_src, hook_cut["cut_out"], vert_vo_intro, "vo_intro")
    timings["vo_intro"] = round(time.time() - t_start, 1)

    # --- clip_01: grid (layout C) ---
    t_start = time.time()
    vert_clip01 = os.path.join(QA, "v16_vert_clip01.mp4")
    render_grid(clip01_seg, vert_clip01)
    timings["clip_01"] = round(time.time() - t_start, 1)

    # --- clip_02: single, chyron-safe (CoinDesk) ---
    t_start = time.time()
    vert_clip02 = os.path.join(QA, "v16_vert_clip02.mp4")
    clip02_ok, clip02_crop = render_single(clip02_seg, vert_clip02, "clip_02",
                                            chyron_safe=True)
    timings["clip_02"] = round(time.time() - t_start, 1)

    # --- clip_03: stack2, same tiles as hook (bSmF = Simply Bitcoin) ---
    t_start = time.time()
    vert_clip03 = os.path.join(QA, "v16_vert_clip03.mp4")
    render_stack2(clip03_seg, vert_clip03, "clip_03",
                  rect_a=(0, 0, 960, 1080),       # left
                  rect_b=(960, 0, 960, 1080))      # right
    timings["clip_03"] = round(time.time() - t_start, 1)

    # --- vo_bridge: VO visual ---
    t_start = time.time()
    clip03_cut = cuts_map["clip_03"]
    clip03_src = os.path.join(SOURCES, f"{clip03_cut['video_id']}.mp4")
    vert_vo_bridge = os.path.join(QA, "v16_vert_vo_bridge.mp4")
    render_vo_visual_vert(
        os.path.join(VO_DIR, vo_manifest["bridge_01"]["stem_wav"]),
        clip03_src, clip03_cut["cut_out"], vert_vo_bridge, "vo_bridge")
    timings["vo_bridge"] = round(time.time() - t_start, 1)

    # --- clip_04: stack2-unequal (Adam O'Brien TOP, Ben BOTTOM) ---
    t_start = time.time()
    vert_clip04 = os.path.join(QA, "v16_vert_clip04.mp4")
    render_stack2_unequal(clip04_seg, vert_clip04, "clip_04",
                          rect_top=(1280, 0, 640, 540),   # Adam O'Brien (speaker)
                          rect_bot=(0, 0, 640, 540))       # Ben
    timings["clip_04"] = round(time.time() - t_start, 1)

    # --- shoutout ---
    shoutout_path = os.path.join(QA_V7, "shoutout_9x16.mp4")
    assert os.path.exists(shoutout_path), f"Missing: {shoutout_path}"
    print(f"    [shoutout] {get_duration(shoutout_path):.2f}s (pre-rendered)")

    # --- outro ---
    outro_16x9 = os.path.join(QA_V3, "final_outro.mp4")
    vert_outro = os.path.join(QA_V7, "vert7_outro.mp4")
    if not os.path.exists(vert_outro):
        subprocess.run([
            "ffmpeg", "-y", "-i", outro_16x9,
            "-vf", f"scale={VERT_W}:{VERT_H}:force_original_aspect_ratio=decrease,"
                   f"pad={VERT_W}:{VERT_H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1:1",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-an",
            "-movflags", "+faststart", vert_outro,
        ], capture_output=True, timeout=120)
    print(f"    [outro] {get_duration(vert_outro):.2f}s (pre-rendered)")

    # ========== STEP 3: Concat video segments (video-only) ==========
    print("\n=== STEP 3: CONCAT VIDEO (9 SEGMENTS, VIDEO-ONLY) ===")

    # Exact horizontal order
    vert_segments = [
        ("hook",       vert_hook,       "talking_head"),
        ("vo_intro",   vert_vo_intro,   "vo"),
        ("clip_01",    vert_clip01,     "talking_head"),
        ("clip_02",    vert_clip02,     "talking_head"),
        ("clip_03",    vert_clip03,     "talking_head"),
        ("vo_bridge",  vert_vo_bridge,  "vo"),
        ("clip_04",    vert_clip04,     "talking_head"),
        ("shoutout",   shoutout_path,   "shoutout"),
        ("outro",      vert_outro,      "outro"),
    ]

    for label, path, _ in vert_segments:
        dur = get_duration(path)
        print(f"  {label}: {dur:.2f}s")

    total_vid_dur = sum(get_duration(p) for _, p, _ in vert_segments)
    print(f"  Total video: {total_vid_dur:.2f}s (horizontal: {horiz_dur:.2f}s)")

    # Need to strip audio from shoutout and outro for concat (they have embedded audio)
    shoutout_vo = os.path.join(QA, "v16_shoutout_vo.mp4")
    outro_vo = os.path.join(QA, "v16_outro_vo.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", shoutout_path, "-an", "-c:v", "copy", shoutout_vo,
    ], capture_output=True, timeout=30)
    subprocess.run([
        "ffmpeg", "-y", "-i", vert_outro, "-an", "-c:v", "copy", outro_vo,
    ], capture_output=True, timeout=30)

    # Update segment list to use video-only versions
    vert_segments_vo = [
        ("hook",       vert_hook,       "talking_head"),
        ("vo_intro",   vert_vo_intro,   "vo"),
        ("clip_01",    vert_clip01,     "talking_head"),
        ("clip_02",    vert_clip02,     "talking_head"),
        ("clip_03",    vert_clip03,     "talking_head"),
        ("vo_bridge",  vert_vo_bridge,  "vo"),
        ("clip_04",    vert_clip04,     "talking_head"),
        ("shoutout",   shoutout_vo,     "shoutout"),
        ("outro",      outro_vo,        "outro"),
    ]

    filelist = os.path.join(QA, "v16_vert_filelist.txt")
    with open(filelist, "w") as f:
        for label, path, _ in vert_segments_vo:
            f.write(f"file '{path}'\n")

    concat_video = os.path.join(QA, "v16_vert_concat_video.mp4")
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS,setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "+faststart", concat_video,
    ], capture_output=True, timeout=600)
    if r.returncode != 0:
        print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
    concat_dur = get_duration(concat_video)
    print(f"  Concat video: {concat_dur:.2f}s")

    # ========== STEP 4: Watermark ==========
    print("\n=== STEP 4: ALPHA WATERMARK ===")

    cumulative = 0
    shoutout_start = 0
    for label, path, _ in vert_segments:
        dur = get_duration(path)
        if label == "shoutout":
            shoutout_start = cumulative
            break
        cumulative += dur

    print(f"  Watermark: 0 -> {shoutout_start:.2f}s")

    concat_wm = os.path.join(QA, "v16_vert_concat_wm.mp4")
    overlay_expr = (
        f"[1:v]scale=72:-1,format=rgba,"
        f"colorchannelmixer=aa=0.6,"
        f"fade=t=in:d=0.4:alpha=1[wm];"
        f"[0:v][wm]overlay=W-w-30:H-h-30:"
        f"enable='between(t,0,{shoutout_start:.3f})':"
        f"shortest=1[vout]"
    )

    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_video,
        "-loop", "1", "-i", PP_MARK,
        "-filter_complex", overlay_expr,
        "-map", "[vout]",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-an",
        "-movflags", "+faststart", concat_wm,
    ], capture_output=True, timeout=600)
    if r.returncode != 0:
        print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
    print(f"  Watermarked: {get_duration(concat_wm):.2f}s")

    # ========== STEP 5: Mux horizontal audio over vertical video ==========
    print("\n=== STEP 5: MUX HORIZONTAL AUDIO ===")

    final_path = os.path.join(OUT, "segment_v16_vertical.mp4")
    wm_dur = get_duration(concat_wm)

    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_wm,
        "-i", HORIZ_MP4,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-t", str(min(wm_dur, horiz_dur)),  # shorter of the two
        "-movflags", "+faststart", final_path,
    ], capture_output=True, timeout=300)
    if r.returncode != 0:
        print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")

    if not os.path.exists(final_path) or os.path.getsize(final_path) < 10000:
        print("FATAL: V16 vertical mux failed")
        sys.exit(1)

    final_dur = get_duration(final_path)
    print(f"  Final: {final_path}")
    print(f"  Duration: {final_dur:.3f}s (horizontal: {horiz_dur:.3f}s, delta: {abs(final_dur - horiz_dur):.3f}s)")

    # ========== STEP 6: Concat manifest ==========
    print("\n=== STEP 6: CONCAT MANIFEST ===")

    edl_map = {}
    for c in cuts:
        edl_map[c["clip_id"]] = c
    for clip_edl in edl.get("clips", []):
        idx = clip_edl["index"]
        cid = f"clip_{idx:02d}"
        if cid in edl_map:
            edl_map[cid]["first_word_edl"] = clip_edl.get("first_word", "")
            edl_map[cid]["last_word_edl"] = clip_edl.get("last_word", "")
    hook_edl_data = edl.get("hook", {})
    if "hook" in edl_map:
        edl_map["hook"]["first_word_edl"] = hook_edl_data.get("first_word", "")
        edl_map["hook"]["last_word_edl"] = hook_edl_data.get("last_word", "")

    cumul = 0.0
    manifest_segments = []
    for label, path, seg_type in vert_segments:
        dur = get_duration(path)
        seg_entry = {
            "label": label,
            "start": round(cumul, 3),
            "end": round(cumul + dur, 3),
            "type": seg_type,
        }
        if seg_type == "talking_head":
            if label in edl_map:
                seg_entry["first_word"] = edl_map[label].get("first_word_edl", "")
                seg_entry["last_word"] = edl_map[label].get("last_word_edl", "")
            if label == "clip_01":
                seg_entry["layout"] = "grid"
            elif label == "clip_02":
                seg_entry["layout"] = "single"
            elif label in ("hook", "clip_03", "clip_04"):
                seg_entry["layout"] = "stack2"
        elif seg_type == "vo":
            role_key = "intro" if "intro" in label else "bridge_01"
            seg_entry["text"] = vo_manifest.get(role_key, {}).get("text", "")

        manifest_segments.append(seg_entry)
        cumul += dur

    manifest_data = {
        "format": "9x16",
        "segments": manifest_segments,
        "shoutout_start": shoutout_start,
    }
    manifest_path = os.path.join(QA, "concat_manifest_9x16.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"  Manifest: {manifest_path}")

    # ========== STEP 7: HARD GATES ==========
    print("\n=== STEP 7: HARD GATES ===")

    sys.path.insert(0, BASE)
    from qa_gates import gate_g2, gate_g8, gate_g9, gate_g10, gate_g11

    gate_results = {}

    # G2: Watermark
    g2_pass, g2_table = gate_g2(final_path, shoutout_start, "9x16")
    gate_results["G2_watermark"] = {"pass": bool(g2_pass), "table": g2_table}

    # G8: Sharpness (R1-upscaled = single crops; stack2 also upscales)
    r1_upscaled = {"hook", "clip_02", "clip_03", "clip_04"}
    g8_pass, g8_table = gate_g8(final_path, manifest_segments, QA,
                                 upscaled_labels=r1_upscaled)
    gate_results["G8_sharpness"] = {"pass": bool(g8_pass), "table": g8_table}

    # G9: Tail
    g9_pass, g9_data = gate_g9(final_path, QA)
    gate_results["G9_tail"] = {"pass": bool(g9_pass), "data": g9_data}

    # G10: Text crop (CoinDesk = clip_02)
    crop_rects = {}
    if clip02_ok:
        crop_rects["clip_02"] = clip02_crop
    coindesk_ids = {"clip_02"}
    g10_pass, g10_data = gate_g10(final_path, manifest_segments, crop_rects, QA,
                                   coindesk_clip_ids=coindesk_ids)
    gate_results["G10_text_crop"] = {"pass": bool(g10_pass), "data": g10_data}

    # G11: Parity
    g11_pass, g11_data = gate_g11(final_path, HORIZ_MP4,
                                   manifest_segments, horiz_segments)
    gate_results["G11_parity"] = {"pass": bool(g11_pass), "data": g11_data}

    all_gates_pass = g2_pass and g8_pass and g9_pass and g10_pass and g11_pass
    gate_results["all_pass"] = bool(all_gates_pass)

    with open(os.path.join(QA, "gate_results_v16.json"), "w") as f:
        json.dump(gate_results, f, indent=2, default=str)

    print(f"\n  G2 Watermark:  {'PASS' if g2_pass else 'FAIL'}")
    print(f"  G8 Sharpness:  {'PASS' if g8_pass else 'FAIL'}")
    print(f"  G9 Tail:       {'PASS' if g9_pass else 'FAIL'}")
    print(f"  G10 Text-crop: {'PASS' if g10_pass else 'FAIL'}")
    print(f"  G11 Parity:    {'PASS' if g11_pass else 'FAIL'}")
    print(f"  ALL GATES:     {'PASS' if all_gates_pass else 'FAIL'}")

    # ========== STEP 8: Contact sheet (fps=1/2, 192px tiles, 10xN) ==========
    print("\n=== STEP 8: CONTACT SHEET ===")

    sheet_path = os.path.join(OUT, "segment_v16_vertical_sheet.jpg")
    sheet_frames_dir = os.path.join(QA, "v16_sheet_frames")
    if os.path.exists(sheet_frames_dir):
        shutil.rmtree(sheet_frames_dir)
    os.makedirs(sheet_frames_dir)

    subprocess.run([
        "ffmpeg", "-y", "-i", final_path,
        "-vf", "fps=1/2,scale=192:-1",
        os.path.join(sheet_frames_dir, "frame_%04d.jpg"),
    ], capture_output=True, timeout=120)

    sheet_frame_files = sorted([f for f in os.listdir(sheet_frames_dir) if f.endswith(".jpg")])
    n_actual = len(sheet_frame_files)
    cols = 10
    rows = max(1, (n_actual + cols - 1) // cols)
    print(f"  Frames: {n_actual} ({cols}x{rows})")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", os.path.join(sheet_frames_dir, "frame_%04d.jpg"),
        "-vf", f"tile={cols}x{rows}:padding=2:color=black",
        "-q:v", "3", sheet_path,
    ], capture_output=True, timeout=60)

    if os.path.exists(sheet_path):
        print(f"  Sheet: {sheet_path} ({os.path.getsize(sheet_path):,} bytes)")

    # ========== STEP 9: Telegram send ==========
    print("\n=== STEP 9: TELEGRAM SEND ===")

    overrides = _load_overrides()
    hook_choice = overrides.get("hook", {})
    clip03_choice = overrides.get("clip_03", {})

    caption_lines = [
        f"v16 vertical (PARITY) | {final_dur:.1f}s",
        f"G2 wm: {'PASS' if g2_pass else 'FAIL'}",
        f"G8 sharp: {'PASS' if g8_pass else 'FAIL'}",
        f"G9 tail: {'PASS' if g9_pass else 'FAIL'}",
        f"G10 text: {'PASS' if g10_pass else 'FAIL'}",
        f"G11 parity: {'PASS' if g11_pass else 'FAIL'} (d={abs(final_dur-horiz_dur):.2f}s)",
        f"hook lip: a={hook_choice.get('score_a','?')} b={hook_choice.get('score_b','?')} -> {hook_choice.get('speaker_rect','?')}",
        f"clip03 lip: a={clip03_choice.get('score_a','?')} b={clip03_choice.get('score_b','?')} -> {clip03_choice.get('speaker_rect','?')}",
    ]
    if not all_gates_pass:
        caption_lines.insert(0, "GATE FAIL — DO NOT SHIP")
    caption = "\n".join(caption_lines)

    if all_gates_pass:
        print("  Sending video to Telegram...")
        r_tg = subprocess.run([
            sys.executable, os.path.join(BASE, "tg_preview.py"),
            final_path, caption,
        ], capture_output=True, text=True, timeout=600)
        print(f"  {r_tg.stdout.strip()}")

        if os.path.exists(sheet_path):
            print("  Sending contact sheet...")
            tg_env = {}
            for line in open(os.path.expanduser('~/protocol_pulse/.env')):
                if '=' in line and not line.startswith('#'):
                    k, v = line.rstrip('\n').split('=', 1)
                    tg_env[k.strip()] = v.strip().strip('"').strip("'")
            tok, chat = tg_env['TELEGRAM_BOT_TOKEN'], tg_env['TELEGRAM_CHAT_ID']
            r_sheet = subprocess.run([
                'curl', '-sS', '-X', 'POST',
                f'https://api.telegram.org/bot{tok}/sendPhoto',
                '-F', f'chat_id={chat}',
                '-F', f'caption=v16 contact sheet ({n_actual} frames, {cols}x{rows})',
                '-F', f'photo=@{sheet_path}',
            ], capture_output=True, text=True, timeout=120)
            tg_resp = json.loads(r_sheet.stdout or '{}')
            print(f"  Sheet sent: ok={tg_resp.get('ok')}")
    else:
        print("  GATES FAILED — skipping Telegram send")

    # ========== SUMMARY ==========
    final_size = os.path.getsize(final_path)
    r = subprocess.run(["md5sum", final_path], capture_output=True, text=True, timeout=30)
    md5 = r.stdout.strip()

    elapsed = time.time() - t0
    print(f"\n=== SEGMENT V16 (9:16 PARITY) COMPLETE ===")
    print(f"  File: {final_path}")
    print(f"  Duration: {final_dur:.3f}s (horizontal: {horiz_dur:.3f}s)")
    print(f"  Size: {final_size:,} bytes ({final_size / 1024 / 1024:.1f} MB)")
    print(f"  Render time: {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    print(f"  md5sum: {md5}")
    print(f"  Gates: {'ALL PASS' if all_gates_pass else 'FAIL'}")
    print(f"  Timings: {json.dumps(timings)}")
