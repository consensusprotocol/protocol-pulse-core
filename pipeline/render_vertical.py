#!/usr/bin/env python3
"""pipeline/render_vertical.py — Parameterised 9:16 vertical renderer.

Architecture mirrors render16.py but outputs 1080x1920.
Clip reframing uses mediapipe face-centred crop from render_v12_vertical.py.

Usage:
    python3 render_vertical.py <segment_dir> [--qa-version qa_v1] [--output-name name.mp4]
    python3 -m pipeline.render_vertical --segment <segment_dir> [--qa-version N]
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

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)
from config import verify_vo_voice
from config import (FPS, PRE_ROLL, WIDTH, HEIGHT, VERT_W, VERT_H,
                    ACCENT_COLOR, NVENC_QP_FINAL, NVENC_QP_INTERMEDIATE,
                    resolve_paths, resolve_brand, resolve_bgm,
                    conform_outro)

# Import shoutout builder from pipeline (parameterised)
from shoutout import build_shoutout

# Import relay for API keys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))   # this checkout, never a fixed path (Claude-gates C4)
from relay import get_key

# ── Vertical-specific constants ──
CROP_W = 607   # 9:16 crop width from 1920x1080 source
CROP_H = 1080  # full source height
BLAZE_FACE_MODEL = "/home/ultron/protocol_pulse/segment_v1/qa_v6/blaze_face_short_range.tflite"


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def ease_in_out(t):
    return 0.5 * (1 - math.cos(math.pi * t))


# ==============================================================
# REFRAME: face-centred 9:16 crop (from v12 render_v12_vertical.py)
# ==============================================================

def reframe_fixed_crop(seg_path, output_path, seg_label):
    """Fixed 9:16 crop per clip. Detect faces via mediapipe, use median centre X.
    Falls back to centre crop if no faces detected.
    Returns (success: bool, crop_rect: str)."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    print(f"    Reframe fixed crop: {seg_label}")

    base_opts = mp_base_options.BaseOptions(model_asset_path=BLAZE_FACE_MODEL)
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=base_opts, min_detection_confidence=0.3))

    cap = cv2.VideoCapture(seg_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    face_cx_values = []
    sample_interval = max(1, frame_count // 40)
    for fi in range(0, frame_count, sample_interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ret, frame_bgr = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=frame_rgb)
        results = detector.detect(mp_image)
        if results.detections:
            best = max(results.detections,
                       key=lambda d: d.bounding_box.width * d.bounding_box.height)
            cx = best.bounding_box.origin_x + best.bounding_box.width // 2
            face_cx_values.append(cx)
    cap.release()

    if face_cx_values:
        median_cx = int(np.median(face_cx_values))
    else:
        median_cx = src_w // 2
        print(f"      No faces detected, using centre crop")

    crop_x = max(0, min(src_w - CROP_W, median_cx - CROP_W // 2))
    crop_rect = f"{crop_x},0,{CROP_W},{CROP_H}"
    print(f"      Median face cx={median_cx}, crop x={crop_x}, rect={crop_rect}")

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", f"crop={CROP_W}:{CROP_H}:{crop_x}:0,scale={VERT_W}:{VERT_H}:flags=lanczos,setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)
    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-300:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True, crop_rect
    print(f"      ERROR: reframe failed")
    return False, crop_rect


# ==============================================================
# REFRAME: stack2 — two-person 2-up (e.g. BMTV podcast)
# ==============================================================

def reframe_stack2(seg_path, output_path, seg_label, layout_cfg):
    """Stack2: speaker rect on TOP, other person rect on BOTTOM.
    Each rect cropped from source, scaled to 1080 wide, placed in 1080x960 slot.
    layout_cfg keys: speaker_rect (x,y,w,h), other_rect (x,y,w,h)."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    import cv2
    print(f"    Reframe stack2: {seg_label}")

    speaker = layout_cfg["speaker_rect"]  # [x, y, w, h]
    other = layout_cfg["other_rect"]      # [x, y, w, h]
    slot_h = VERT_H // 2  # 960

    cap = cv2.VideoCapture(seg_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Scale rects to match actual source dimensions (rects may be for 1920x1080)
    sx = src_w / 1920.0
    sy = src_h / 1080.0

    def scale_rect(r):
        return [int(r[0]*sx), int(r[1]*sy), int(r[2]*sx), int(r[3]*sy)]

    sp = scale_rect(speaker)
    ot = scale_rect(other)

    # Build ffmpeg filter: crop both rects, scale to 1080 wide maintaining AR,
    # pad to 1080x960, then vstack
    # Speaker on top, other on bottom
    vf = (
        f"split=2[a][b];"
        f"[a]crop={sp[2]}:{sp[3]}:{sp[0]}:{sp[1]},"
        f"scale={VERT_W}:{slot_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={VERT_W}:{slot_h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1:1[top];"
        f"[b]crop={ot[2]}:{ot[3]}:{ot[0]}:{ot[1]},"
        f"scale={VERT_W}:{slot_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={VERT_W}:{slot_h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1:1[bot];"
        f"[top][bot]vstack=inputs=2"
    )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", vf,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)
    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True, "stack2"
    print(f"      ERROR: reframe_stack2 failed")
    return False, "stack2"


# ==============================================================
# REFRAME: grid — face-cam on top, chart on bottom (e.g. TBL)
# ==============================================================

def reframe_grid(seg_path, output_path, seg_label, layout_cfg):
    """Grid: face rect on TOP slot, chart rect on BOTTOM slot.
    layout_cfg keys: face_rect (x,y,w,h), chart_rect (x,y,w,h),
                     top_slot_h (default 810), bottom_slot_h (default 1110)."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    import cv2
    print(f"    Reframe grid: {seg_label}")

    face = layout_cfg["face_rect"]    # [x, y, w, h]
    chart = layout_cfg["chart_rect"]  # [x, y, w, h]
    top_h = layout_cfg.get("top_slot_h", 810)
    bot_h = VERT_H - top_h  # 1110

    cap = cv2.VideoCapture(seg_path)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Scale rects if source isn't 1920x1080
    sx = src_w / 1920.0
    sy = src_h / 1080.0
    # If source is already at native res, check if rects are specified for that res
    if src_w < 1920:
        # Rects might already be in source coords — check if face_rect fits
        if face[0] + face[2] <= src_w and face[1] + face[3] <= src_h:
            sx, sy = 1.0, 1.0  # rects are in source coords

    def scale_rect(r):
        return [int(r[0]*sx), int(r[1]*sy), int(r[2]*sx), int(r[3]*sy)]

    fc = scale_rect(face)
    ch = scale_rect(chart)

    vf = (
        f"split=2[a][b];"
        f"[a]crop={fc[2]}:{fc[3]}:{fc[0]}:{fc[1]},"
        f"scale={VERT_W}:{top_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={VERT_W}:{top_h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1:1[top];"
        f"[b]crop={ch[2]}:{ch[3]}:{ch[0]}:{ch[1]},"
        f"scale={VERT_W}:{bot_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={VERT_W}:{bot_h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1:1[bot];"
        f"[top][bot]vstack=inputs=2"
    )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", vf,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)
    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True, "grid"
    print(f"      ERROR: reframe_grid failed")
    return False, "grid"


# ==============================================================
# REFRAME: single — one person, crop rect to 9:16
# ==============================================================

def reframe_single(seg_path, output_path, seg_label, layout_cfg):
    """Single: crop one rect from source, scale to 1080 wide, pad to 1920 tall (centred)."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    print(f"    Reframe single: {seg_label}")

    rect = layout_cfg["rect"]  # [x, y, w, h]

    vf = (
        f"crop={rect[2]}:{rect[3]}:{rect[0]}:{rect[1]},"
        f"scale={VERT_W}:{VERT_H}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={VERT_W}:{VERT_H}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1:1"
    )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", vf,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)
    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True, "single"
    print(f"      ERROR: reframe_single failed")
    return False, "single"


# ==============================================================
# LETTERBOX (M21): unapproved channels — full 16:9 on blurred bg
# ==============================================================

def reframe_letterbox(seg_path, output_path, seg_label, layout_cfg=None):
    """M21 Letterbox: full 16:9 frame scaled to 1080 wide, centred on a blurred,
    darkened (-35%), 1.25x zoomed copy of the same frame. No crop.

    Returns (success: bool, layout_name: str)."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    print(f"    Reframe letterbox: {seg_label}")

    # Full 16:9 frame scaled to 1080 wide = 1080x608 (at 16:9 ratio)
    # Centred on 1080x1920 canvas with blurred+darkened background
    # Background: scale so height >= 1920*1.25 = 2400, then crop 1080x1920
    # (16:9 source is wider than tall — scale by HEIGHT to fill vertical canvas)
    vf = (
        # Split into two streams
        "split[main][bg];"
        # Background: scale up so height=2400 (1.25x of 1920), blur heavily, darken
        "[bg]scale=-2:2400:flags=lanczos,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        "boxblur=20:5,"
        f"colorlevels=rimax=0.65:gimax=0.65:bimax=0.65"  # -35% brightness
        "[bgout];"
        # Main: scale full 16:9 to 1080 wide, maintain aspect
        f"[main]scale={VERT_W}:-2:flags=lanczos[mainout];"
        # Overlay main centred on bg
        f"[bgout][mainout]overlay=(W-w)/2:(H-h)/2,"
        f"setsar=1:1"
    )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", vf,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)
    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s (letterbox)")
        return True, "letterbox"
    print(f"      ERROR: reframe_letterbox failed")
    return False, "letterbox"


# ==============================================================
# AUTO (DEC-2/DEC-5, 2026-11-11): per-shot plan from vertical_layout.classify
# ==============================================================

LETTERBOX_VF = ("split[main][bg];[bg]scale=-2:2400:flags=lanczos,crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
                "boxblur=20:5,colorlevels=rimax=0.65:gimax=0.65:bimax=0.65[bgout];"
                f"[main]scale={VERT_W}:-2:flags=lanczos[mainout];[bgout][mainout]overlay=(W-w)/2:(H-h)/2")
# colorlevels runs in RGB: ffmpeg 4.4's round trip keeps the YUV values but drops the matrix tag, so a 9:16 part
# opening on a safe frame came out color_space=unknown (Nov 11 recut: decoders read it as BT.601, G9 luma 14.47
# instead of 14.74). reframe_auto re-declares the input's own matrix after the safe frame (metadata only).
_KNOWN_MATRICES = {"bt709", "bt470bg", "smpte170m", "bt2020nc", "bt2020c", "smpte240m", "fcc"}


def _input_matrix(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_space",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    m = r.stdout.strip()
    return m if m in _KNOWN_MATRICES else None


def _shot_vf(shot, src_w, src_h):
    """Filter for one shot of a 1920x1080 prepared clip -> 1080x1920 (approved filters reused)."""
    cls = shot["class"]
    if cls == "single":                                   # v2f fixed speaker-centred crop (Law 18a)
        x = max(0, min(src_w - CROP_W, int(shot["face_cx"]) - CROP_W // 2))
        return f"crop={CROP_W}:{CROP_H}:{x}:0,scale={VERT_W}:{VERT_H}:flags=lanczos"
    if cls in ("stack2", "stack3"):                       # equal bands, left to right (Law 18b equal mode)
        n = int(cls[-1])
        bh = VERT_H // n
        cw = src_w // n
        ch = int(round(cw * bh / VERT_W))
        parts = [f"split={n}" + "".join(f"[b{i}]" for i in range(n)) + ";"]
        for i, (cx, cy) in enumerate(zip(shot["band_cx"], shot["band_cy"])):   # each face at 40 % of its band
            x = max(0, min(src_w - cw, int(cx) - cw // 2))
            y = max(0, min(src_h - ch, int(cy) - int(ch * 0.4)))
            parts.append(f"[b{i}]crop={cw}:{ch}:{x}:{y},scale={VERT_W}:{bh}:flags=lanczos[s{i}];")
        return "".join(parts) + "".join(f"[s{i}]" for i in range(n)) + f"vstack=inputs={n},pad={VERT_W}:{VERT_H}"
    return LETTERBOX_VF                                   # screen / uncertain: safe frame (flagged)


def reframe_auto(seg_path, output_path, seg_label, plan):
    """Per-shot 9:16 from the PREPARED clip (lead-in pad and fades identical to 16:9). Video only is
    re-composed; the clip's audio is copied unchanged. Returns (ok, layout_summary)."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    fps = plan["fps"]
    graph, labels = [], []
    matrix = _input_matrix(seg_path)
    for k, shot in enumerate(plan["shots"]):
        a, b = int(round(shot["start"] * fps)), int(round(shot["end"] * fps))
        vf = _shot_vf(shot, plan["width"], plan["height"])
        if vf == LETTERBOX_VF and matrix:              # keep the input's declared matrix through the safe frame
            vf += f",setparams=colorspace={matrix}"
        graph.append(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,"
                     f"{vf},setsar=1:1[v{k}]")
        labels.append(f"[v{k}]")
    graph.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[vout]")
    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path, "-filter_complex", ";".join(graph),
        "-map", "[vout]", "-map", "0:a", "-r", str(FPS),
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=600)
    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")
        return False, "auto"
    summary = "+".join(f"{s['class']}[{s['start']:.2f}-{s['end']:.2f}]" for s in plan["shots"])
    print(f"    Reframe auto {seg_label}: {summary}")
    return True, f"auto:{summary}"


# ==============================================================
# VO VISUAL (native 9:16) — face-crop BG from preceding clip
# ==============================================================

def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4, label, qa_dir):
    """R5 native 9:16 VO visual: face-crop BG, blur, 1.0x->1.08x zoom, waveform.
    Returns the path to the assembled VO WAV (silence + stem) for G6 measurement."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    print(f"  Rendering VO visual (9:16): {os.path.basename(output_mp4)}")

    vo_dur = get_duration(vo_wav)
    total_dur = PRE_ROLL + vo_dur
    total_frames = int(total_dur * FPS)
    preroll_frames = int(PRE_ROLL * FPS)

    print(f"    VO: {vo_dur:.2f}s + {PRE_ROLL}s pre-roll = {total_dur:.2f}s ({total_frames} frames)")

    # Extract BG frame from preceding clip (use the VERTICAL composited frame,
    # chyron-safe by construction — Law 23 VO-visual rule)
    bg_png = os.path.join(qa_dir, f"vo_vert_bg_{label}.png")
    frame_ts = max(0, preceding_cut_out - 0.1)
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(frame_ts), "-i", preceding_src,
        "-vframes", "1", "-q:v", "2", bg_png,
    ], capture_output=True, timeout=30)

    bg_full = Image.open(bg_png).convert("RGB")
    src_w, src_h = bg_full.size

    if src_h > src_w:
        # Source is already 9:16 (vertical composited clip).
        # S7: detect black-band letterbox (stack2/single/grid layouts leave bands).
        # If >20% of rows are black at top or bottom, extract content region
        # and scale to fill the full canvas before blurring.
        bg_arr = np.array(bg_full)
        row_means = bg_arr.mean(axis=(1, 2))
        top_black = 0
        for y in range(src_h):
            if row_means[y] > 20:
                top_black = y
                break
        bot_black = 0
        for y in range(src_h - 1, -1, -1):
            if row_means[y] > 20:
                bot_black = src_h - 1 - y
                break
        black_frac = (top_black + bot_black) / src_h
        if black_frac > 0.20:
            # Crop to content region, then scale to fill full canvas
            bg_content = bg_full.crop((0, top_black, src_w, src_h - bot_black))
            bg_vert = bg_content.resize((VERT_W, VERT_H), Image.LANCZOS)
            print(f"    S7: black bands detected ({black_frac:.0%}), cropped rows {top_black}-{src_h - bot_black} -> full-bleed")
        else:
            bg_vert = bg_full.resize((VERT_W, VERT_H), Image.LANCZOS)
    else:
        # Source is 16:9 — face-centred crop to 9:16 (legacy path)
        bg_arr = np.array(bg_full)
        base_opts = mp_base_options.BaseOptions(model_asset_path=BLAZE_FACE_MODEL)
        detector = vision.FaceDetector.create_from_options(
            vision.FaceDetectorOptions(base_options=base_opts, min_detection_confidence=0.4))
        mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=bg_arr)
        results = detector.detect(mp_image)
        face_cx = src_w // 2
        if results.detections:
            best = max(results.detections, key=lambda d: d.bounding_box.width * d.bounding_box.height)
            face_cx = best.bounding_box.origin_x + best.bounding_box.width // 2
        crop_x = max(0, min(src_w - CROP_W, face_cx - CROP_W // 2))
        bg_crop = bg_full.crop((crop_x, 0, crop_x + CROP_W, src_h))
        bg_vert = bg_crop.resize((VERT_W, VERT_H), Image.LANCZOS)

    bg_blurred = bg_vert.filter(ImageFilter.GaussianBlur(radius=6))

    # Audio RMS for waveform visualisation
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

    # Waveform bar layout (adjusted for vertical)
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

    # Audio: silence + VO stem
    silence_wav = os.path.join(qa_dir, f"vo_vert_silence_{label}.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(PRE_ROLL), "-c:a", "pcm_s16le", silence_wav,
    ], capture_output=True, timeout=10, check=True)

    # R2-06: Resample VO stem to 48000 Hz stereo BEFORE concat
    resampled_wav = os.path.join(qa_dir, f"vo_vert_stem_48k_{label}.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", os.path.abspath(vo_wav),
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", resampled_wav,
    ], capture_output=True, timeout=30, check=True)

    combined_wav = os.path.join(qa_dir, f"vo_vert_assembled_{label}.wav")
    audio_list = os.path.join(qa_dir, f"vo_vert_audio_list_{label}.txt")
    with open(audio_list, "w") as f:
        f.write(f"file '{silence_wav}'\n")
        f.write(f"file '{resampled_wav}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list,
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", combined_wav,
    ], capture_output=True, timeout=30, check=True)

    # Encode frames + audio
    gpu0.raise_if_oom(subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", combined_wav,
        "-vf", "setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120), "render_vertical nvenc")

    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        dur = get_duration(output_mp4)
        print(f"    Output: {dur:.2f}s")
        shutil.rmtree(frames_dir)
        return combined_wav
    print("    ERROR: VO render failed")
    return None


# ==============================================================
# WATERMARK (alpha, positioned for vertical)
# ==============================================================

def apply_watermark_alpha_vert(input_mp4, output_mp4, mark_path, mark_px, margin,
                               opacity, fade_in_dur, shoutout_start):
    """Overlay alpha watermark on vertical concat. Bottom-right, smaller for 9:16."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    overlay_expr = (
        f"[1:v]scale={mark_px}:-1,format=rgba,"
        f"colorchannelmixer=aa={opacity},"
        f"fade=t=in:d={fade_in_dur}:alpha=1[wm];"
        f"[0:v][wm]overlay=W-w-{margin}:H-h-{margin}:"
        f"enable='between(t,0,{shoutout_start:.3f})':"
        f"shortest=1[vout]"
    )

    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", input_mp4,
        "-loop", "1", "-i", mark_path,
        "-filter_complex", overlay_expr,
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "copy",
        "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=600)
    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"

    if r.returncode != 0:
        print(f"    ffmpeg watermark stderr: {r.stderr.decode()[-500:]}")

    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 10000


# ==============================================================
# MAIN RENDER PIPELINE
# ==============================================================

def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4",
                alimiter_dbfs=-3.0):
    """Full 9:16 vertical render pipeline.
    Returns (final_path, manifest_path, vo_assembled_tracks) or raises."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    t0 = time.time()
    print("=== RENDER 9:16 ===\n")

    paths = resolve_paths(segment_dir, qa_version)
    qa_dir = paths["qa_dir"]
    out_dir = paths["out_dir"]

    # Load data files
    with open(paths["edl_json"]) as f:
        edl = json.load(f)
    with open(paths["cuts_json"]) as f:
        cuts = json.load(f)
    with open(paths["vo_manifest"]) as f:
        vo_manifest = json.load(f)

    pp_mark = resolve_brand(segment_dir)
    bgm_track = resolve_bgm(segment_dir)

    # ========== STEP 1: Verify voice ==========
    print("=== STEP 1: VERIFY VOICE ===")
    voice_id, model_id = verify_vo_voice(vo_manifest)
    print(f"  voice_id: {voice_id}")
    print(f"  model: {model_id}")

    # ========== STEP 2: Reframe clips to 9:16 ==========
    print("\n=== STEP 2: REFRAME CLIPS ===")

    # Load vertical layout overrides if present
    overrides_path = os.path.join(paths["segment_dir"], "vertical_overrides.json")
    vert_overrides = {}
    if os.path.exists(overrides_path):
        with open(overrides_path) as f:
            vert_overrides = json.load(f)
        print(f"  Loaded {len(vert_overrides)} layout overrides")

    reframed = {}   # clip_id -> reframed_path
    crop_rects = {} # clip_id -> crop_rect string

    for cut in cuts:
        clip_id = cut["clip_id"]
        vert_path = os.path.join(qa_dir, f"vert_{clip_id}.mp4")

        override = vert_overrides.get(clip_id, {})

        # Shot-level splitting: override may have "shots" array instead of a single layout
        if "shots" in override:
            shots = override["shots"]
            raw_src = os.path.join(paths["sources_dir"], f"{cut['video_id']}.mp4")
            shot_parts = []
            all_shots_ok = True
            for si, shot in enumerate(shots):
                shot_trimmed = os.path.join(qa_dir, f"raw_{clip_id}_shot{si}.mp4")
                shot_out = os.path.join(qa_dir, f"vert_{clip_id}_shot{si}.mp4")
                s_start = shot["source_start"]
                s_end = shot["source_end"]
                s_dur = s_end - s_start
                gpu0.raise_if_oom(subprocess.run([
                    "ffmpeg", "-y", "-ss", str(s_start), "-i", raw_src, "-t", str(s_dur),
                    "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
                    "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", shot_trimmed,
                ], capture_output=True, timeout=300), "render_vertical nvenc")
                s_layout = shot.get("layout", "crop")
                if s_layout == "stack2":
                    s_ok, _ = reframe_stack2(shot_trimmed, shot_out, f"{clip_id}_shot{si}", shot)
                elif s_layout == "grid":
                    s_ok, _ = reframe_grid(shot_trimmed, shot_out, f"{clip_id}_shot{si}", shot)
                elif s_layout == "single":
                    s_ok, _ = reframe_single(shot_trimmed, shot_out, f"{clip_id}_shot{si}", shot)
                else:
                    s_ok, _ = reframe_fixed_crop(shot_trimmed, shot_out, f"{clip_id}_shot{si}")
                if s_ok:
                    shot_parts.append(shot_out)
                else:
                    all_shots_ok = False
            # Concat shot parts
            if all_shots_ok and len(shot_parts) > 1:
                concat_list = os.path.join(qa_dir, f"concat_{clip_id}_shots.txt")
                with open(concat_list, "w") as clf:
                    for sp in shot_parts:
                        clf.write(f"file '{sp}'\n")
                gpu0.raise_if_oom(subprocess.run([
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                    "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
                    "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", vert_path,
                ], capture_output=True, timeout=300), "render_vertical nvenc")
                ok = os.path.exists(vert_path) and os.path.getsize(vert_path) > 1000
                crop_rect = "shots"
            elif all_shots_ok and len(shot_parts) == 1:
                import shutil
                shutil.copy2(shot_parts[0], vert_path)
                ok, crop_rect = True, "shots"
            else:
                ok, crop_rect = False, "shots"

        else:
            layout = override.get("layout", "crop")

            if layout in ("stack2", "grid", "single"):
                # Custom layouts use the RAW source file (rects are in source coords),
                # trimmed to the cut boundaries, not the QA-rendered 1920x1080 clip.
                raw_src = os.path.join(paths["sources_dir"], f"{cut['video_id']}.mp4")
                cut_in = cut.get("cut_in", 0)
                cut_dur = cut.get("cut_duration", 15)
                trimmed = os.path.join(qa_dir, f"raw_{clip_id}.mp4")
                gpu0.raise_if_oom(subprocess.run([
                    "ffmpeg", "-y", "-ss", str(cut_in), "-i", raw_src, "-t", str(cut_dur),
                    "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
                    "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", trimmed,
                ], capture_output=True, timeout=300), "render_vertical nvenc")
                if layout == "stack2":
                    ok, crop_rect = reframe_stack2(trimmed, vert_path, clip_id, override)
                elif layout == "grid":
                    ok, crop_rect = reframe_grid(trimmed, vert_path, clip_id, override)
                else:
                    ok, crop_rect = reframe_single(trimmed, vert_path, clip_id, override)
            elif layout == "auto":
                # DEC-2/DEC-5: per-shot plan measured on the prepared clip (vertical_layout.classify)
                src_clip = _find_clip_file(qa_dir, clip_id, cuts, paths["sources_dir"])
                ok, crop_rect = reframe_auto(src_clip, vert_path, clip_id, override["plan"])
            elif layout == "letterbox":
                # M21: Full 16:9 letterbox for unapproved channels
                src_clip = _find_clip_file(qa_dir, clip_id, cuts, paths["sources_dir"])
                ok, crop_rect = reframe_letterbox(src_clip, vert_path, clip_id, override)
            else:
                src_clip = _find_clip_file(qa_dir, clip_id, cuts, paths["sources_dir"])
                ok, crop_rect = reframe_fixed_crop(src_clip, vert_path, clip_id)

        if not ok:
            # M12 fail closed (2026-11-11): never drop a 16:9 clip into the 9:16 timeline
            raise RuntimeError(f"STOP: vertical reframe failed for {clip_id} (layout {crop_rect})")
        reframed[clip_id] = vert_path
        crop_rects[clip_id] = crop_rect

    print(f"\n  Reframed: {list(reframed.keys())}")

    # ========== STEP 3: Render VO visuals (R5, 9:16) ==========
    print("\n=== STEP 3: RENDER VO VISUALS ===")

    vo_assembled_tracks = {}
    sources_dir = paths["sources_dir"]

    # Render intro VO visual — BG from the VERTICAL's own reframed hook (chyron-safe)
    if "intro" in vo_manifest and "stem_wav" in vo_manifest["intro"]:
        hook_vert = reframed.get("hook")
        if hook_vert:
            hook_dur = get_duration(hook_vert)
            vo_intro_wav = os.path.join(paths["vo_dir"], vo_manifest["intro"]["stem_wav"])
            vo_intro_mp4 = os.path.join(qa_dir, "vo_vert_intro.mp4")
            assembled = render_vo_visual_vert(
                vo_intro_wav, hook_vert, hook_dur, vo_intro_mp4, "vo_intro", qa_dir)
            if assembled:
                vo_assembled_tracks["vo_intro"] = assembled

    # Render bridge VO visuals — BG from the VERTICAL's own reframed preceding clip
    edl_bridges = edl.get("vo", {}).get("bridges", [])
    bridge_keys = sorted([k for k in vo_manifest if k.startswith("bridge_")])
    for bi, bkey in enumerate(bridge_keys):
        bridge_data = vo_manifest[bkey]
        if "stem_wav" not in bridge_data:
            continue

        # Determine preceding clip from EDL after_clip
        if bi < len(edl_bridges) and "after_clip" in edl_bridges[bi]:
            after_clip_idx = edl_bridges[bi]["after_clip"]
        else:
            after_clip_idx = int(bkey.split("_")[1])
        preceding_clip_id = f"clip_{after_clip_idx:02d}"

        # Use the VERTICAL reframed clip (chyron-safe by construction)
        preceding_vert = reframed.get(preceding_clip_id)
        if not preceding_vert:
            preceding_vert = reframed.get("hook", list(reframed.values())[0])
        preceding_dur = get_duration(preceding_vert)

        vo_bridge_wav = os.path.join(paths["vo_dir"], bridge_data["stem_wav"])
        vo_bridge_mp4 = os.path.join(qa_dir, f"vo_vert_{bkey}.mp4")
        assembled = render_vo_visual_vert(
            vo_bridge_wav, preceding_vert, preceding_dur, vo_bridge_mp4, f"vo_{bkey}", qa_dir)
        if assembled:
            vo_assembled_tracks[f"vo_{bkey}"] = assembled

    print(f"\n  Assembled VO tracks: {list(vo_assembled_tracks.keys())}")

    # ========== STEP 4: Build segment list ==========
    print("\n=== STEP 4: SEGMENT LIST ===")

    segments = []

    # Hook (reframed) — fail-closed: hook is required
    if "hook" not in reframed:
        raise RuntimeError("STOP: hook missing from reframed clips")
    segments.append(("hook", reframed["hook"], "talking_head"))

    # Intro VO — fail-closed when the EDL has an intro (mirrors 16:9).
    # A legitimately intro-less EDL (Law 27/M20) gets no intro segment.
    vo_intro_mp4 = os.path.join(qa_dir, "vo_vert_intro.mp4")
    if edl.get("vo", {}).get("intro"):
        if not os.path.exists(vo_intro_mp4):
            raise RuntimeError(f"STOP: intro VO missing: {vo_intro_mp4}")
        segments.append(("vo_intro", vo_intro_mp4, "vo"))

    # Build bridge placement map: clip_index -> bridge manifest key
    bridge_after_map = {}
    for bi, bkey in enumerate(bridge_keys):
        if bi < len(edl_bridges) and "after_clip" in edl_bridges[bi]:
            bridge_after_map[edl_bridges[bi]["after_clip"]] = bkey
        else:
            bridge_after_map[int(bkey.split("_")[1])] = bkey

    # Clips and bridges interleaved per EDL
    clip_ids = sorted([c["clip_id"] for c in cuts if c["clip_id"].startswith("clip_")])
    for clip_id in clip_ids:
        if clip_id in reframed:
            segments.append((clip_id, reframed[clip_id], "talking_head"))
        else:
            clip_file = _find_clip_file(qa_dir, clip_id, cuts, sources_dir)
            segments.append((clip_id, clip_file, "talking_head"))

        # Check if a bridge follows this clip — fail-closed
        clip_idx = int(clip_id.split("_")[1])
        if clip_idx in bridge_after_map:
            bkey = bridge_after_map[clip_idx]
            vo_bridge_mp4 = os.path.join(qa_dir, f"vo_vert_{bkey}.mp4")
            if not os.path.exists(vo_bridge_mp4):
                raise RuntimeError(f"STOP: bridge VO missing: {vo_bridge_mp4}")
            segments.append((f"vo_{bkey}", vo_bridge_mp4, "vo"))

    # Shoutout — fail-closed: shoutout is required
    shoutout_path = _find_shoutout_vert(qa_dir, segment_dir)
    if not shoutout_path:
        # Render shoutout at 9:16 via pipeline shoutout builder
        print("  No 9:16 shoutout found, rendering...")
        shoutout_path = build_shoutout(segment_dir, qa_version, fmt="9x16")
    if not shoutout_path:
        raise RuntimeError("STOP: shoutout not found and could not be rendered")
    segments.append(("shoutout", shoutout_path, "shoutout"))

    # Outro — fail-closed: outro is required
    outro_path = _find_outro_vert(qa_dir, segment_dir)
    if not outro_path:
        raise RuntimeError("STOP: outro not found")
    segments.append(("outro", outro_path, "outro"))

    for label, path, _ in segments:
        assert os.path.exists(path), f"MISSING: {path}"
        dur = get_duration(path)
        print(f"  {label}: {dur:.2f}s  ({path})")

    total_seg_dur = sum(get_duration(p) for _, p, _ in segments)
    print(f"\n  Total: {total_seg_dur:.1f}s")

    # ========== STEP 5: Concat ==========
    print("\n=== STEP 5: CONCAT ===")

    filelist = os.path.join(qa_dir, "filelist_vert.txt")
    with open(filelist, "w") as f:
        for label, path, _ in segments:
            f.write(f"file '{path}'\n")

    concat_raw = os.path.join(qa_dir, "concat_raw_vert.mp4")
    from render16 import _transition_concat
    timeline = _transition_concat(segment_dir, segments, concat_raw, VERT_W, VERT_H, qa_dir)
    if timeline is None:                     # no TRANSITIONS.json: the frozen hard-cut concat (v2f)
        r = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
            "-vf", "setpts=PTS-STARTPTS",
            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", concat_raw,
        ], capture_output=True, timeout=600)
        gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
        if r.returncode != 0:
            print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
    concat_dur = get_duration(concat_raw)
    print(f"  Concat: {concat_dur:.2f}s")

    # ========== STEP 6: Watermark (alpha, vertical placement) ==========
    print("\n=== STEP 6: ALPHA WATERMARK ===")

    cumulative = 0
    shoutout_start = 0
    for label, path, _ in segments:
        dur = get_duration(path)
        if label == "shoutout":
            shoutout_start = cumulative
            break
        cumulative += dur
    if timeline is not None:
        shoutout_start = next((e["start"] for e in timeline if e["label"] == "shoutout"), shoutout_start)

    print(f"  Watermark: 0 -> {shoutout_start:.2f}s")

    concat_wm = os.path.join(qa_dir, "concat_wm_vert.mp4")
    ok = apply_watermark_alpha_vert(concat_raw, concat_wm, pp_mark,
                                    mark_px=72, margin=30, opacity=0.6,
                                    fade_in_dur=0.4, shoutout_start=shoutout_start)
    if not ok:
        print("FATAL: Watermark overlay failed")
        sys.exit(1)
    print(f"  Watermarked: {get_duration(concat_wm):.2f}s")

    # ========== STEP 7: BGM mix ==========
    print("\n=== STEP 7: BGM MIX ===")

    bgm_path = os.path.join(qa_dir, "bgm_vert.mp4")
    wm_dur = get_duration(concat_wm)
    bgm_fade_out_start = wm_dur - 1.5

    subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_wm,
        "-stream_loop", "-1", "-i", bgm_track,
        "-filter_complex",
        f"[1:a]volume=-26dB,afade=t=in:d=1.0,afade=t=out:st={bgm_fade_out_start:.1f}:d=1.5[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", bgm_path,
    ], capture_output=True, timeout=300)
    print(f"  BGM mix: {get_duration(bgm_path):.2f}s")

    # ========== STEP 8: Loudnorm 2-pass + alimiter ==========
    print("\n=== STEP 8: LOUDNORM + ALIMITER ===")

    r = subprocess.run([
        "ffmpeg", "-y", "-i", bgm_path,
        "-af", "loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True, timeout=300)

    mi = None
    try:
        stderr = r.stderr
        js = stderr[stderr.rfind("{"):stderr.rfind("}") + 1]
        stats = json.loads(js)
        mi = stats["input_i"]
        mtp = stats["input_tp"]
        mlra = stats["input_lra"]
        mt = stats["input_thresh"]
        off = stats["target_offset"]
        print(f"  Measured: I={mi} TP={mtp} LRA={mlra}")
    except Exception as e:
        print(f"  WARNING: loudnorm parse error: {e}")

    normed_wav = os.path.join(qa_dir, "normed_vert.wav")
    if mi:
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-af", f"loudnorm=I=-14:TP=-2.0:LRA=11:"
                   f"measured_I={mi}:measured_TP={mtp}:"
                   f"measured_LRA={mlra}:measured_thresh={mt}:"
                   f"offset={off}:linear=true",
            "-ar", "48000", "-ac", "2", normed_wav,
        ], capture_output=True, timeout=300)
    else:
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-af", "loudnorm=I=-14:TP=-2.0:LRA=11",
            "-ar", "48000", "-ac", "2", normed_wav,
        ], capture_output=True, timeout=300)

    final_path = os.path.join(out_dir, output_name)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", bgm_path,
        "-i", normed_wav,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-af", f"alimiter=limit={10 ** (alimiter_dbfs / 20):.6f}:level=false",  # {alimiter_dbfs} dBFS
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", final_path,
    ], capture_output=True, timeout=300)

    if not os.path.exists(final_path) or os.path.getsize(final_path) < 10000:
        print("FATAL: 9:16 render failed")
        sys.exit(1)

    # ========== STEP 9: Build concat manifest for qa_gates ==========
    print("\n=== STEP 9: CONCAT MANIFEST ===")

    edl_map = {}
    for c in cuts:
        edl_map[c["clip_id"]] = c
    for clip_edl in edl.get("clips", []):
        idx = clip_edl["index"]
        cid = f"clip_{idx:02d}"
        if cid not in edl_map:
            continue
        edl_map[cid]["first_word_edl"] = clip_edl.get("first_word", "")
        edl_map[cid]["last_word_edl"] = clip_edl.get("last_word", "")
    hook_edl = edl.get("hook", {})
    if "hook" in edl_map:
        edl_map["hook"]["first_word_edl"] = hook_edl.get("first_word", "")
        edl_map["hook"]["last_word_edl"] = hook_edl.get("last_word", "")

    cumul = 0.0
    manifest_segments = []
    tl = {e["label"]: e for e in timeline} if timeline is not None else {}
    for label, path, seg_type in (segments if timeline is None else
                                  [(e["label"], None, e["type"]) for e in timeline]):
        dur = get_duration(path) if timeline is None else tl[label]["end"] - tl[label]["start"]
        start = cumul if timeline is None else tl[label]["start"]
        seg_entry = {
            "label": label,
            "start": round(start, 3),
            "end": round(start + dur, 3),
            "type": seg_type,
        }

        if seg_type == "talking_head":
            clip_id = label
            if clip_id in edl_map:
                seg_entry["first_word"] = edl_map[clip_id].get("first_word_edl", "")
                seg_entry["last_word"] = edl_map[clip_id].get("last_word_edl", "")
        elif seg_type == "vo":
            role_key = "intro" if "intro" in label else label.replace("vo_", "")
            if "signoff" in label:
                role_key = "signoff"
            seg_entry["text"] = vo_manifest.get(role_key, {}).get("text", "")

        manifest_segments.append(seg_entry)
        cumul += dur

    manifest_data = {
        "format": "9x16",
        "segments": manifest_segments,
        "shoutout_start": shoutout_start,
    }
    manifest_path = os.path.join(qa_dir, "concat_manifest_9x16.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"  Manifest: {manifest_path}")

    # Save assembled VO tracks map for qa_gates
    vo_tracks_path = os.path.join(qa_dir, "vo_assembled_tracks_vert.json")
    with open(vo_tracks_path, "w") as f:
        json.dump(vo_assembled_tracks, f, indent=2)
    print(f"  VO assembled tracks: {vo_tracks_path}")

    final_dur = get_duration(final_path)
    final_size = os.path.getsize(final_path)
    elapsed = time.time() - t0
    print(f"\n=== 9:16 COMPLETE ===")
    print(f"  File: {final_path}")
    print(f"  Duration: {final_dur:.3f}s")
    print(f"  Size: {final_size:,} bytes ({final_size / 1024 / 1024:.1f} MB)")
    print(f"  Render time: {elapsed:.0f}s ({elapsed / 60:.1f}min)")

    return final_path, manifest_path, vo_assembled_tracks


# ── Helpers for finding pre-rendered clip files ──

def _find_clip_file(qa_dir, clip_id, cuts=None, sources_dir=None):
    """Find the pre-rendered clip file in CURRENT qa_dir only (M12: no cross-qa, no raw fallback)."""
    import glob as _glob
    pattern = os.path.join(qa_dir, f"final_{clip_id}*.mp4")
    best = None
    best_version = -1
    for hit in _glob.glob(pattern):
        basename = os.path.basename(hit)
        name_no_ext = basename.replace("final_", "").replace(".mp4", "")
        if not name_no_ext.startswith(clip_id):
            continue
        rest = name_no_ext[len(clip_id):]
        if rest == "":
            version = 0
        elif rest.startswith("_v") and rest[2:].isdigit():
            version = int(rest[2:])
        else:
            continue
        if version > best_version:
            best = hit
            best_version = version
    if best:
        return best
    raise FileNotFoundError(f"STOP: clip file for '{clip_id}' not found in {qa_dir}")


def _find_shoutout_vert(qa_dir, segment_dir=None):
    """Find 9:16 shoutout in CURRENT qa_dir only (M12: no cross-qa scanning)."""
    candidate = os.path.join(qa_dir, "shoutout_9x16.mp4")
    if os.path.exists(candidate):
        return candidate
    raise FileNotFoundError(f"STOP: 9:16 shoutout not found in {qa_dir}")


def _find_outro_vert(qa_dir, segment_dir=None):
    """Find 9:16 outro. Prefers PBX native 9:16 outro (Amendment 1 §2),
    falls back to qa_dir pre-rendered versions."""
    # Amendment 1 §2: each aspect gets ITS OWN native outro (no cross-aspect use)
    try:
        return conform_outro("9x16")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        import gpu0
        if gpu0.is_oom(e):           # L-r: an NVENC out-of-memory is never a fallback (E-FAIL-052)
            raise gpu0.GpuOOM(f"outro conform: CUDA/NVENC out of memory ({e})") from e
        print(f"  PBX 9:16 outro conform failed ({e}), falling back to qa_dir")

    # Fallback: pre-rendered vertical outro in qa_dir
    for name in ["final_outro_vert.mp4", "vert_outro.mp4", "vert_outro_from16x9.mp4"]:
        candidate = os.path.join(qa_dir, name)
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"STOP: 9:16 outro not found in {qa_dir}")


def main():
    p = argparse.ArgumentParser(description="Parameterised 9:16 vertical renderer")
    p.add_argument("segment_dir", nargs="?", help="Segment directory (positional)")
    p.add_argument("--segment", default=None, help="Segment directory (named)")
    p.add_argument("--qa-version", default=None, help="QA version (e.g. qa_v1 or 1)")
    p.add_argument("--output-name", default="segment_vertical.mp4", help="Output filename")
    args = p.parse_args()

    segment_dir = args.segment_dir or args.segment
    if not segment_dir:
        print("ERROR: segment_dir required (positional or --segment)")
        sys.exit(1)

    render_9x16(segment_dir, args.qa_version, args.output_name)


if __name__ == "__main__":
    main()
