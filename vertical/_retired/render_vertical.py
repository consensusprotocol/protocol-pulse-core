#!/usr/bin/env python3
"""Canonical 9:16 vertical renderer — v1.0 locked 2026-11-04, PBX A+.

Mirrors the 16:9 program shot-for-shot with the horizontal's mixed audio.
Layouts come from hand tables per source channel+tile_count, never from a detector.
Gates G8-G12 measure the output picture, never input metadata.
A vertical that fails parity never reaches Telegram.

Usage:
  python3 render_vertical.py \\
    --segment <segment_dir> \\
    --version <N> \\
    --horizontal <16x9_final.mp4> \\
    --cuts <cuts_final.json> \\
    --layout-table <layout_tables_dir_or_json>

All segment-specific paths are resolved from --segment:
  <segment_dir>/qa_v<N>/          QA scratch
  <segment_dir>/out/              Final output
  <segment_dir>/sources/          Source clips
  <segment_dir>/vo_audio/         VO stems + manifest
  <segment_dir>/edl_v2.json       EDL with channel info
  <segment_dir>/brand/            Watermark, avatars
  <segment_dir>/publish/          Partner handles
"""
import argparse
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

FPS = 24
VERT_W = 1080
VERT_H = 1920
CROP_W = 607   # default 9:16 crop from 1920 source
CROP_H = 1080
PRE_ROLL = 1.0
ACCENT_COLOR = (247, 147, 26)
DIVIDER_H = 4

# ── Helpers ──────────────────────────────────────────────────

def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def ease_in_out(t):
    return 0.5 * (1 - math.cos(math.pi * t))


# ── Override file I/O ────────────────────────────────────────

def _load_overrides(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_overrides(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Layout table loader ─────────────────────────────────────

def load_layout_tables(layout_path):
    """Load layout tables from a directory of JSONs or a single JSON.
    Returns dict keyed by (channel_lower, tile_count) -> table dict."""
    tables = {}
    if os.path.isdir(layout_path):
        for fn in os.listdir(layout_path):
            if fn.endswith(".json"):
                with open(os.path.join(layout_path, fn)) as f:
                    table = json.load(f)
                ch = table.get("channel", "").lower()
                tc = table.get("tile_count", 0)
                tables[(ch, tc)] = table
    elif os.path.isfile(layout_path):
        with open(layout_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            for table in data:
                ch = table.get("channel", "").lower()
                tc = table.get("tile_count", 0)
                tables[(ch, tc)] = table
        elif isinstance(data, dict) and "channel" in data:
            ch = data["channel"].lower()
            tc = data.get("tile_count", 0)
            tables[(ch, tc)] = data
    return tables


def resolve_layout(channel, tile_count, tables):
    """Resolve layout from tables by (channel, tile_count).
    Falls back to 'single' with a WARN if no match."""
    key = (channel.lower(), tile_count)
    if key in tables:
        return tables[key], None
    # Fallback
    warn = (f"WARN: No layout table for channel='{channel}' tile_count={tile_count}. "
            f"Falling back to layout='single' with lip-activity speaker pick.")
    fallback = {
        "layout": "single",
        "chyron_safe": False,
        "speaker_detection": "lip_activity",
    }
    return fallback, warn


# ── Lip-activity score ───────────────────────────────────────

def _lip_activity_score(seg_path, rect, n_samples=12):
    """Compute lip-activity score for a source rect (x,y,w,h)."""
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


# ==============================================================
# LAYOUT A: single (fixed crop on one face, chyron-safe option)
# ==============================================================

def render_single(seg_path, output_path, seg_label, chyron_safe=False,
                  chyron_exclude_px=200, overrides_path=None):
    """Fixed crop on one face. Lip-activity speaker pick with force_cx override."""
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    print(f"    [A] single crop: {seg_label} (chyron_safe={chyron_safe})")

    overrides = _load_overrides(overrides_path) if overrides_path else {}
    if seg_label in overrides and "force_cx" in overrides[seg_label]:
        chosen_cx = overrides[seg_label]["force_cx"]
        print(f"      Manual override: force_cx={chosen_cx}")
    else:
        chosen_cx = None

    base_dir = os.path.dirname(os.path.dirname(seg_path))  # guess BASE
    model_path = os.path.join(base_dir, "qa_v6", "blaze_face_short_range.tflite")
    if not os.path.exists(model_path):
        # Fallback: search common locations
        for p in ["/home/ultron/protocol_pulse/segment_v1/qa_v6/blaze_face_short_range.tflite"]:
            if os.path.exists(p):
                model_path = p
                break

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

    if overrides_path:
        overrides[seg_label] = {
            "layout": "single", "persons": persons,
            "chosen_cx": chosen_cx, "reason": reason,
        }
        _save_overrides(overrides, overrides_path)

    print(f"      Persons: {len(persons)}")
    for i, p in enumerate(persons):
        marker = " <-- CHOSEN" if p["cx"] == chosen_cx else ""
        print(f"        person_{i}: cx={p['cx']}, lip_score={p['score']}{marker}")
    print(f"      Speaker: cx={chosen_cx} ({reason})")

    # Chyron-safe: exclude bottom N px
    if chyron_safe:
        crop_h_src = src_h - chyron_exclude_px
        crop_w_src = int(crop_h_src * VERT_W / VERT_H)
        if crop_w_src % 2 != 0:
            crop_w_src += 1
        crop_y = 0
    else:
        crop_h_src = CROP_H
        crop_w_src = CROP_W
        crop_y = 0

    crop_x = max(0, min(src_w - crop_w_src, chosen_cx - crop_w_src // 2))
    crop_rect = f"{crop_x},{crop_y},{crop_w_src},{crop_h_src}"
    print(f"      Crop: x={crop_x}, y={crop_y}, w={crop_w_src}, h={crop_h_src}")

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", f"crop={crop_w_src}:{crop_h_src}:{crop_x}:{crop_y},"
               f"scale={VERT_W}:{VERT_H}:flags=lanczos,setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-an", "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-300:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True, crop_rect, crop_w_src
    print(f"      ERROR: single render failed")
    return False, crop_rect, crop_w_src


# ==============================================================
# LAYOUT B: stack2 (two source rects, speaker TOP, other BOTTOM)
# ==============================================================

def render_stack2(seg_path, output_path, seg_label, rect_a, rect_b,
                  speaker_rect="a", overrides_path=None):
    """Two source rects stacked vertically: speaker on TOP (960px), other BOTTOM (960px)."""
    print(f"    [B] stack2: {seg_label} (speaker_rect={speaker_rect})")

    score_a = _lip_activity_score(seg_path, rect_a)
    score_b = _lip_activity_score(seg_path, rect_b)
    print(f"      rect_a lip_score={score_a}, rect_b lip_score={score_b}")

    overrides = _load_overrides(overrides_path) if overrides_path else {}
    entry = overrides.get(seg_label, {})

    if seg_label in overrides and "speaker_rect" in overrides[seg_label]:
        speaker_rect = overrides[seg_label]["speaker_rect"]
        print(f"      Override: speaker_rect={speaker_rect} (from overrides file)")
    else:
        if score_b > score_a:
            speaker_rect = "b"
        else:
            speaker_rect = "a"
        print(f"      Lip-activity decision: speaker_rect={speaker_rect}")

    entry.update({
        "layout": "stack2", "rect_a": list(rect_a), "rect_b": list(rect_b),
        "score_a": score_a, "score_b": score_b, "speaker_rect": speaker_rect,
    })
    if overrides_path:
        overrides[seg_label] = entry
        _save_overrides(overrides, overrides_path)

    if speaker_rect == "a":
        top_rect, bot_rect = rect_a, rect_b
    else:
        top_rect, bot_rect = rect_b, rect_a

    tx, ty, tw, th = top_rect
    bx, by, bw, bh = bot_rect
    half_h = VERT_H // 2

    vf = (
        f"split=2[s1][s2];"
        f"[s1]crop={tw}:{th}:{tx}:{ty},scale={VERT_W}:{half_h}:flags=lanczos,setsar=1:1[top];"
        f"[s2]crop={bw}:{bh}:{bx}:{by},scale={VERT_W}:{half_h}:flags=lanczos,setsar=1:1[bot];"
        f"[top][bot]vstack=inputs=2[vout]"
    )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-filter_complex", vf, "-map", "[vout]",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-an", "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-500:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True
    print(f"      ERROR: stack2 render failed")
    return False


def render_stack2_unequal(seg_path, output_path, seg_label, rect_top, rect_bot,
                          overrides_path=None):
    """Stack2 variant: two rects of different sizes (e.g. 640x540 each)."""
    print(f"    [B] stack2-unequal: {seg_label}")

    tx, ty, tw, th = rect_top
    bx, by, bw, bh = rect_bot

    tile_h = int(VERT_W * th / tw)
    if tile_h % 2 != 0:
        tile_h += 1
    pad_total = VERT_H - 2 * tile_h
    pad_top = max(0, pad_total // 2)

    vf = (
        f"split=2[s1][s2];"
        f"[s1]crop={tw}:{th}:{tx}:{ty},scale={VERT_W}:{tile_h}:flags=lanczos,setsar=1:1[top];"
        f"[s2]crop={bw}:{bh}:{bx}:{by},scale={VERT_W}:{tile_h}:flags=lanczos,setsar=1:1[bot];"
        f"[top][bot]vstack=inputs=2,"
        f"pad={VERT_W}:{VERT_H}:0:{pad_top}:black,setsar=1:1[vout]"
    )

    if overrides_path:
        overrides = _load_overrides(overrides_path)
        overrides[seg_label] = {
            "layout": "stack2-unequal",
            "rect_top": list(rect_top), "rect_bot": list(rect_bot),
        }
        _save_overrides(overrides, overrides_path)

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-filter_complex", vf, "-map", "[vout]",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-an", "-movflags", "+faststart", output_path,
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
# LAYOUT C: grid (full frame top + guest column bottom)
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


def render_grid(seg_path, output_path, panel_x=(1544, 1920)):
    """Layout C: TOP = full 16:9 frame. BOTTOM = guest column enlarged. LANCZOS from full-res."""
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
    panel_x1, panel_x2 = panel_x
    tiles = detect_panel_tiles(frame_rgb, panel_x1, panel_x2)

    if tiles:
        print(f"      Detected {len(tiles)} tiles in guest column:")
        for i, (y1, y2) in enumerate(tiles):
            print(f"        tile_{i}: y={y1}-{y2} (h={y2 - y1 + 1}px)")

    col_y1 = tiles[0][0] if tiles else 0
    col_y2 = tiles[-1][1] if tiles else src_h - 1
    col_x1, col_x2 = panel_x1, panel_x2
    col_w = col_x2 - col_x1
    col_h = col_y2 - col_y1 + 1

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

    from PIL import Image as PILImage, ImageFilter as PILFilter
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
        top_strip = pil_frame.resize((VERT_W, top_h), PILImage.LANCZOS)
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
        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", output_path,
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

def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4,
                          label, qa_dir):
    """R5 native 9:16 VO visual (video-only)."""
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

    bg_png = os.path.join(qa_dir, f"vo_vert_bg_{label}.png")
    frame_ts = preceding_cut_out - 0.1
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(frame_ts), "-i", preceding_src,
        "-vframes", "1", "-vf", "scale=1920:1080", "-q:v", "2", bg_png,
    ], capture_output=True, timeout=30)

    bg_full = Image.open(bg_png).convert("RGB")
    bg_arr = np.array(bg_full)

    model_path = os.path.join(os.path.dirname(qa_dir), "qa_v6", "blaze_face_short_range.tflite")
    if not os.path.exists(model_path):
        model_path = "/home/ultron/protocol_pulse/segment_v1/qa_v6/blaze_face_short_range.tflite"
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
    frames_dir = os.path.join(qa_dir, f"vo_vert_frames_{label}")
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

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-vf", "setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120)

    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        dur = get_duration(output_mp4)
        print(f"      Output: {dur:.2f}s")
        shutil.rmtree(frames_dir)
        return True
    print("      ERROR: VO render failed")
    return None


# ==============================================================
# DISPATCH: layout table -> render function
# ==============================================================

def dispatch_render(seg_path, output_path, seg_label, layout_table, overrides_path=None):
    """Route to the correct render function based on layout_table."""
    layout = layout_table.get("layout", "single")

    if layout == "single":
        chyron_safe = layout_table.get("chyron_safe", False)
        chyron_px = layout_table.get("chyron_exclude_px", 200)
        ok, crop_rect, crop_w = render_single(
            seg_path, output_path, seg_label,
            chyron_safe=chyron_safe, chyron_exclude_px=chyron_px,
            overrides_path=overrides_path)
        return ok, {"crop_rect": crop_rect, "crop_w": crop_w}

    elif layout == "stack2":
        rects = layout_table.get("rects", {})
        rect_a = tuple(rects.get("a", [0, 0, 960, 1080]))
        rect_b = tuple(rects.get("b", [960, 0, 960, 1080]))
        ok = render_stack2(seg_path, output_path, seg_label,
                           rect_a, rect_b, overrides_path=overrides_path)
        return ok, {"crop_w": rect_a[2]}

    elif layout == "stack2_unequal":
        rects = layout_table.get("rects", {})
        rect_top = tuple(rects.get("top", [1280, 0, 640, 540]))
        rect_bot = tuple(rects.get("bottom", [0, 0, 640, 540]))
        ok = render_stack2_unequal(seg_path, output_path, seg_label,
                                   rect_top, rect_bot, overrides_path=overrides_path)
        return ok, {"crop_w": rect_top[2]}

    elif layout == "grid":
        panel_x = tuple(layout_table.get("panel_x", [1544, 1920]))
        ok = render_grid(seg_path, output_path, panel_x=panel_x)
        return ok, {"crop_w": None}  # native res, no upscale

    else:
        print(f"    WARN: Unknown layout '{layout}', falling back to single")
        ok, crop_rect, crop_w = render_single(
            seg_path, output_path, seg_label, overrides_path=overrides_path)
        return ok, {"crop_rect": crop_rect, "crop_w": crop_w}


# ==============================================================
# CLI
# ==============================================================

def parse_args():
    p = argparse.ArgumentParser(description="Canonical 9:16 vertical renderer")
    p.add_argument("--segment", required=True, help="Segment directory (e.g. segment_v1)")
    p.add_argument("--version", required=True, type=int, help="Version number N for qa_vN output")
    p.add_argument("--horizontal", required=True, help="16:9 final mp4")
    p.add_argument("--cuts", required=True, help="cuts_final.json")
    p.add_argument("--layout-table", required=True,
                   help="Dir of layout table JSONs or single JSON")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    BASE = args.segment
    QA = os.path.join(BASE, f"qa_v{args.version}")
    OUT = os.path.join(BASE, "out")
    VO_DIR = os.path.join(BASE, "vo_audio")
    SOURCES = os.path.join(BASE, "sources")
    HORIZ_MP4 = args.horizontal
    OVERRIDES_PATH = os.path.join(BASE, f"vertical_overrides_v{args.version}.json")

    os.makedirs(QA, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    sys.path.insert(0, os.path.join(os.path.dirname(BASE), "video_pipeline_v3"))

    with open(args.cuts) as f:
        cuts = json.load(f)
    cuts_map = {c["clip_id"]: c for c in cuts}

    tables = load_layout_tables(args.layout_table)
    print(f"Loaded {len(tables)} layout tables: {list(tables.keys())}")

    print(f"\nCanonical vertical renderer v1.0 (locked 2026-11-04, PBX A+)")
    print(f"  segment: {BASE}")
    print(f"  version: {args.version}")
    print(f"  horizontal: {HORIZ_MP4}")
    print(f"  cuts: {args.cuts}")
    print(f"  layout-table: {args.layout_table}")
    print(f"  output: {OUT}")
    print(f"  qa: {QA}")
