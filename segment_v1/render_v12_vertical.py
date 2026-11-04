#!/usr/bin/env python3
"""Render segment_v12_vertical.mp4 (9:16, 1080x1920, 24fps, <=75s).

Changes from v11:
  1. Gate thresholds restored to law constants (Law 20)
  2. G6 measures onset on assembled VO track (silence + stem, no BGM)
  3. G1 skips 1.0s pre-roll when extracting for resemblyzer
  4. Output: out/segment_v12_vertical.mp4 (never overwrite v11)
"""
import json, os, subprocess, sys, time, math, struct, wave, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scene_shoutout import render_shoutout

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = "/home/ultron/protocol_pulse/segment_v1"
QA = os.path.join(BASE, "qa_v12")
QA_V3 = os.path.join(BASE, "qa_v3")
QA_V7 = os.path.join(BASE, "qa_v7")
OUT = os.path.join(BASE, "out")
VO_DIR = os.path.join(BASE, "vo_audio")
SOURCES = os.path.join(BASE, "sources")
BGM = "/home/ultron/protocol_pulse/video_pipeline_v3/assets/music/confident_02.mp3"
PP_MARK = os.path.join(BASE, "brand", "2026-11", "pp_mark_wave_alpha.png")

os.makedirs(QA, exist_ok=True)

sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
from relay import get_key

FPS = 24
VERT_W = 1080
VERT_H = 1920
CROP_W = 607  # 9:16 crop from 1920 source
CROP_H = 1080
PRE_ROLL = 1.0
MAX_DURATION = 75.0
ACCENT_COLOR = (247, 147, 26)
DIVIDER_H = 4  # lower-third divider height

# Clip_01 source layout (BTC Sessions 5-tile podcast)
CLIP01_PANEL_X = (1544, 1920)


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def ease_in_out(t):
    return 0.5 * (1 - math.cos(math.pi * t))


# ==============================================================
# R1: FIXED CROP (no panning)
# ==============================================================

def reframe_fixed_crop(seg_path, output_path, seg_label):
    """R1: ONE fixed crop per shot. Detect faces, median center, single fixed crop."""
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    print(f"    R1 fixed crop: {seg_label}")

    model_path = os.path.join(BASE, "qa_v6", "blaze_face_short_range.tflite")
    base_opts = mp_base_options.BaseOptions(model_asset_path=model_path)
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=base_opts, min_detection_confidence=0.5))

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
        print(f"      No faces detected, using center crop")

    crop_x = max(0, min(src_w - CROP_W, median_cx - CROP_W // 2))
    crop_rect = f"{crop_x},{0},{CROP_W},{CROP_H}"
    print(f"      Median face cx={median_cx}, crop x={crop_x}, rect={crop_rect}")

    r = subprocess.run([
        "ffmpeg", "-y", "-i", seg_path,
        "-vf", f"crop={CROP_W}:{CROP_H}:{crop_x}:0,scale={VERT_W}:{VERT_H}:flags=lanczos,setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, timeout=300)

    if r.returncode != 0:
        print(f"      ffmpeg error: {r.stderr.decode()[-300:]}")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        dur = get_duration(output_path)
        print(f"      Output: {dur:.2f}s")
        return True, crop_rect
    print(f"      ERROR: reframe failed")
    return False, crop_rect


# ==============================================================
# R2 v11: GRID -- FULL FRAME TOP + ENLARGED GUEST COLUMN BOTTOM
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


def render_grid_v12(seg_path, output_path):
    """R2 v11: TOP = full 16:9 frame scaled to 1080w (~607px tall, on black).
    BOTTOM = guest column (all tiles) cropped and enlarged to fill remaining height,
    blurred-fill sides. Lower-third divider between top and bottom."""
    import cv2

    print("    R2 grid: full frame top + enlarged guest column bottom...")

    cap = cv2.VideoCapture(seg_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Detect tiles from mid-frame
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
    print(f"      Column rect: x={col_x1}-{col_x2}, y={col_y1}-{col_y2} ({col_w}x{col_h})")

    # Face detection on column region
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    col_crop = frame_bgr[col_y1:col_y2 + 1, col_x1:col_x2]
    scale_factor = VERT_W / col_w
    col_scaled = cv2.resize(col_crop, (VERT_W, int(col_h * scale_factor)),
                            interpolation=cv2.INTER_LANCZOS4)
    gray_col = cv2.cvtColor(col_scaled, cv2.COLOR_BGR2GRAY)
    faces_in_col = face_cascade.detectMultiScale(gray_col, 1.1, 4, minSize=(30, 30))
    print(f"      Faces in bottom column: {len(faces_in_col)}")

    # Layout geometry
    top_h = int(src_h * VERT_W / src_w)
    if top_h % 2 != 0:
        top_h += 1
    bottom_h = VERT_H - top_h - DIVIDER_H
    if bottom_h % 2 != 0:
        bottom_h -= 1

    print(f"      Layout: TOP={VERT_W}x{top_h}, divider={DIVIDER_H}px, BOTTOM={VERT_W}x{bottom_h}")

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

    print(f"      Column scaled: {col_scaled_w}x{col_scaled_h}, offset=({col_x_offset},{col_y_offset})")

    # PIL frame-by-frame compositing (ffmpeg filter_complex + h264_nvenc crashes)
    print(f"      PIL frame-by-frame compositing ({frame_count} frames)...")

    frames_dir = output_path.replace(".mp4", "_frames")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    from PIL import Image as PILImage, ImageFilter as PILFilter

    col_region_img = PILImage.fromarray(frame_rgb[col_y1:col_y2 + 1, col_x1:col_x2])
    col_bg_scaled = col_region_img.resize((VERT_W, bottom_h), PILImage.LANCZOS)
    col_bg_blurred = col_bg_scaled.filter(PILFilter.GaussianBlur(radius=25))

    divider_strip = PILImage.new("RGB", (VERT_W, DIVIDER_H), (247, 147, 26))

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
        "-i", seg_path,
        "-map", "0:v", "-map", "1:a",
        "-vf", "setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", output_path,
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
# R5: VO VISUAL (native 9:16)
# ==============================================================

def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4, label):
    """R5 native 9:16 VO visual. Returns path to assembled VO WAV for G6."""
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    print(f"    R5 VO visual (9:16): {os.path.basename(output_mp4)}")

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

    # Audio RMS
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

    silence_wav = os.path.join(QA, f"vo_vert_silence_{label}.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(PRE_ROLL), "-c:a", "pcm_s16le", silence_wav,
    ], capture_output=True, timeout=10)

    combined_wav = os.path.join(QA, f"vo_vert_assembled_{label}.wav")
    audio_list = os.path.join(QA, f"vo_vert_audio_list_{label}.txt")
    with open(audio_list, "w") as f:
        f.write(f"file '{silence_wav}'\n")
        f.write(f"file '{os.path.abspath(vo_wav)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list,
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", combined_wav,
    ], capture_output=True, timeout=30)

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", combined_wav,
        "-vf", "setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120)

    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        dur = get_duration(output_mp4)
        print(f"      Output: {dur:.2f}s")
        shutil.rmtree(frames_dir)
        return combined_wav
    print("      ERROR: VO render failed")
    return None


# ==============================================================
# R4: DURATION CUTDOWN
# ==============================================================

def trim_clip_at_sentence_boundary(clip_path, max_dur, qa_dir, label):
    """R4: Trim clip at verified word boundary."""
    clip_dur = get_duration(clip_path)
    if clip_dur <= max_dur:
        return clip_path, None

    print(f"    R4 trimming {label}: {clip_dur:.2f}s -> {max_dur:.2f}s max")

    clip_wav = os.path.join(qa_dir, f"r4_{label}.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", clip_path,
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", clip_wav,
    ], capture_output=True, timeout=30)

    r = subprocess.run([
        "whisper", clip_wav,
        "--model", "base", "--language", "en",
        "--output_format", "json", "--output_dir", qa_dir,
    ], capture_output=True, text=True, timeout=120,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"})

    json_path = os.path.join(qa_dir, f"r4_{label}.json")
    segments_data = []
    if os.path.exists(json_path):
        with open(json_path) as f:
            wdata = json.load(f)
        segments_data = wdata.get("segments", [])

    best_end = max_dur
    dropped_text = ""
    for seg in reversed(segments_data):
        seg_end = seg.get("end", 0)
        if seg_end <= max_dur:
            best_end = seg_end
            for later_seg in segments_data:
                if later_seg.get("start", 0) >= seg_end:
                    dropped_text += later_seg.get("text", "") + " "
            break

    if best_end >= clip_dur - 0.5:
        best_end = max_dur

    print(f"      Trim point: {best_end:.2f}s (from {clip_dur:.2f}s)")
    if dropped_text.strip():
        print(f"      Dropped: \"{dropped_text.strip()[:100]}\"")

    trimmed_path = os.path.join(qa_dir, f"v12_{label}_trimmed.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", clip_path,
        "-t", str(best_end),
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", trimmed_path,
    ], capture_output=True, timeout=300)

    if os.path.exists(trimmed_path) and os.path.getsize(trimmed_path) > 1000:
        new_dur = get_duration(trimmed_path)
        print(f"      Trimmed: {new_dur:.2f}s")
        return trimmed_path, dropped_text.strip() if dropped_text.strip() else None

    return clip_path, None


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    t0 = time.time()
    print("=== SEGMENT V12: 9:16 VERTICAL ===\n")

    with open(os.path.join(BASE, "edl_v2.json")) as f:
        edl = json.load(f)
    with open(os.path.join(BASE, "cuts_v3.json")) as f:
        cuts = json.load(f)
    with open(os.path.join(VO_DIR, "VO_MANIFEST.json")) as f:
        vo_manifest = json.load(f)

    # ========== STEP 1: Verify voice ==========
    print("=== STEP 1: VERIFY VOICE ===")
    voice_id = get_key("ELEVENLABS_VOICE_ID_PP2")
    if not voice_id:
        print("FATAL: ELEVENLABS_VOICE_ID_PP2 not in .env")
        sys.exit(1)
    voice_id = voice_id.strip()
    print(f"  voice_id: {voice_id}")
    assert voice_id == vo_manifest["intro"]["voice_id"], \
        f"voice_id mismatch: .env={voice_id} manifest={vo_manifest['intro']['voice_id']}"
    print(f"  model: {vo_manifest['intro']['model_id']}")

    # ========== STEP 2: Reframe clips (R1/R2) ==========
    print("\n=== STEP 2: REFRAME CLIPS ===")

    hook_cut = next(c for c in cuts if c["clip_id"] == "hook")
    hook_src = os.path.join(SOURCES, f"{hook_cut['video_id']}.mp4")
    hook_seg = os.path.join(QA_V3, "final_hook.mp4")
    vert_hook = os.path.join(QA, "v12_vert_hook.mp4")
    hook_ok, hook_crop = reframe_fixed_crop(hook_seg, vert_hook, "hook")

    clip01_seg = os.path.join(QA_V3, "final_clip_01.mp4")
    vert_clip01 = os.path.join(QA, "v12_vert_clip01.mp4")
    render_grid_v12(clip01_seg, vert_clip01)

    clip04_seg = os.path.join(QA_V3, "final_clip_04.mp4")
    vert_clip04 = os.path.join(QA, "v12_vert_clip04.mp4")
    clip04_ok, clip04_crop = reframe_fixed_crop(clip04_seg, vert_clip04, "clip_04")

    # ========== STEP 3: Render VO visuals (R5) ==========
    print("\n=== STEP 3: VO VISUALS (R5) ===")

    vo_intro_wav = os.path.join(VO_DIR, vo_manifest["intro"]["stem_wav"])
    vert_vo_intro = os.path.join(QA, "v12_vert_vo_intro.mp4")
    vo_intro_assembled = render_vo_visual_vert(
        vo_intro_wav, hook_src, hook_cut["cut_out"], vert_vo_intro, "vo_intro")

    clip01_cut = next(c for c in cuts if c["clip_id"] == "clip_01")
    clip01_src = os.path.join(SOURCES, f"{clip01_cut['video_id']}.mp4")
    vo_bridge_wav = os.path.join(VO_DIR, vo_manifest["bridge_01"]["stem_wav"])
    vert_vo_bridge = os.path.join(QA, "v12_vert_vo_bridge.mp4")
    vo_bridge_assembled = render_vo_visual_vert(
        vo_bridge_wav, clip01_src, clip01_cut["cut_out"], vert_vo_bridge, "vo_bridge")

    # Collect assembled VO tracks for G6
    vo_assembled_tracks = {}
    if vo_intro_assembled:
        vo_assembled_tracks["vo_intro"] = vo_intro_assembled
    if vo_bridge_assembled:
        vo_assembled_tracks["vo_bridge"] = vo_bridge_assembled
    print(f"\n  Assembled VO tracks saved for G6: {list(vo_assembled_tracks.keys())}")

    # ========== STEP 4: Shoutout + outro ==========
    print("\n=== STEP 4: SHOUTOUT + OUTRO ===")

    shoutout_path = os.path.join(QA_V7, "shoutout_9x16.mp4")
    assert os.path.exists(shoutout_path), f"Missing: {shoutout_path}"
    shout_dur = get_duration(shoutout_path)
    print(f"  Shoutout: {shout_dur:.2f}s")

    outro_16x9 = os.path.join(QA_V3, "final_outro.mp4")
    vert_outro = os.path.join(QA_V7, "vert7_outro.mp4")
    if not os.path.exists(vert_outro):
        subprocess.run([
            "ffmpeg", "-y", "-i", outro_16x9,
            "-vf", f"scale={VERT_W}:{VERT_H}:force_original_aspect_ratio=decrease,"
                   f"pad={VERT_W}:{VERT_H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1:1",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", vert_outro,
        ], capture_output=True, timeout=120)
    outro_dur = get_duration(vert_outro)
    print(f"  Outro: {outro_dur:.2f}s")

    # ========== STEP 5: R4 duration cutdown ==========
    print("\n=== STEP 5: R4 DURATION CUTDOWN ===")

    pre_clip4_dur = sum([
        get_duration(vert_hook),
        get_duration(vert_vo_intro),
        get_duration(vert_clip01),
        get_duration(vert_vo_bridge),
    ])
    post_clip4_dur = shout_dur + outro_dur
    clip4_budget = MAX_DURATION - pre_clip4_dur - post_clip4_dur

    print(f"  Pre-clip4: {pre_clip4_dur:.2f}s")
    print(f"  Post-clip4: {post_clip4_dur:.2f}s")
    print(f"  Clip4 budget: {clip4_budget:.2f}s")

    clip4_final = vert_clip04
    dropped_text = None
    if get_duration(vert_clip04) > clip4_budget:
        clip4_final, dropped_text = trim_clip_at_sentence_boundary(
            vert_clip04, clip4_budget, QA, "clip04")
    else:
        print(f"  Clip4 ({get_duration(vert_clip04):.2f}s) fits within budget")

    # ========== STEP 6: Concat ==========
    print("\n=== STEP 6: CONCAT ===")

    vert_segments = [
        ("hook",       vert_hook,       "talking_head"),
        ("vo_intro",   vert_vo_intro,   "vo"),
        ("clip_01",    vert_clip01,     "talking_head"),
        ("vo_bridge",  vert_vo_bridge,  "vo"),
        ("clip_04",    clip4_final,     "talking_head"),
        ("shoutout",   shoutout_path,   "shoutout"),
        ("outro",      vert_outro,      "outro"),
    ]

    for label, path, _ in vert_segments:
        dur = get_duration(path)
        print(f"  {label}: {dur:.2f}s")

    total_dur = sum(get_duration(p) for _, p, _ in vert_segments)
    print(f"  Total: {total_dur:.2f}s (max {MAX_DURATION}s)")

    if total_dur > MAX_DURATION:
        print(f"  WARNING: Total {total_dur:.2f}s exceeds {MAX_DURATION}s!")

    filelist = os.path.join(QA, "v12_vert_filelist.txt")
    with open(filelist, "w") as f:
        for label, path, _ in vert_segments:
            f.write(f"file '{path}'\n")

    concat_raw = os.path.join(QA, "v12_vert_concat_raw.mp4")
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS,setsar=1:1",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", concat_raw,
    ], capture_output=True, timeout=600)
    if r.returncode != 0:
        print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
    concat_dur = get_duration(concat_raw)
    print(f"  Concat: {concat_dur:.2f}s")

    # ========== STEP 7: Watermark (alpha) ==========
    print("\n=== STEP 7: ALPHA WATERMARK ===")

    cumulative = 0
    shoutout_start = 0
    for label, path, _ in vert_segments:
        dur = get_duration(path)
        if label == "shoutout":
            shoutout_start = cumulative
            break
        cumulative += dur

    print(f"  Watermark: 0 -> {shoutout_start:.2f}s")

    concat_wm = os.path.join(QA, "v12_vert_concat_wm.mp4")
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
        "-i", concat_raw,
        "-loop", "1", "-i", PP_MARK,
        "-filter_complex", overlay_expr,
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "copy",
        "-movflags", "+faststart", concat_wm,
    ], capture_output=True, timeout=600)
    if r.returncode != 0:
        print(f"  ffmpeg watermark stderr: {r.stderr.decode()[-500:]}")
    print(f"  Watermarked: {get_duration(concat_wm):.2f}s")

    # ========== STEP 8: BGM mix ==========
    print("\n=== STEP 8: BGM MIX ===")

    bgm_path = os.path.join(QA, "v12_vert_bgm.mp4")
    wm_dur = get_duration(concat_wm)
    bgm_fade_out = wm_dur - 1.5

    subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_wm,
        "-stream_loop", "-1", "-i", BGM,
        "-filter_complex",
        f"[1:a]volume=-26dB,afade=t=in:d=1.0,afade=t=out:st={bgm_fade_out:.1f}:d=1.5[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", bgm_path,
    ], capture_output=True, timeout=300)
    print(f"  BGM mix: {get_duration(bgm_path):.2f}s")

    # ========== STEP 9: Loudnorm 2-pass ==========
    print("\n=== STEP 9: LOUDNORM + ALIMITER ===")

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

    normed_wav = os.path.join(QA, "v12_vert_normed.wav")
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

    final_path = os.path.join(OUT, "segment_v12_vertical.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", bgm_path,
        "-i", normed_wav,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-af", "alimiter=limit=0.707946:level=false",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", final_path,
    ], capture_output=True, timeout=300)

    if not os.path.exists(final_path) or os.path.getsize(final_path) < 10000:
        print("FATAL: V12 vertical render failed")
        sys.exit(1)

    # ========== STEP 10: Concat manifest ==========
    print("\n=== STEP 10: CONCAT MANIFEST ===")

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
            clip_id = label
            if clip_id in edl_map:
                seg_entry["first_word"] = edl_map[clip_id].get("first_word_edl", "")
                seg_entry["last_word"] = edl_map[clip_id].get("last_word_edl", "")
            if label == "clip_01":
                seg_entry["layout"] = "grid"
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

    # Save assembled VO tracks map for qa_gates
    vo_tracks_path = os.path.join(QA, "vo_assembled_tracks_vert.json")
    with open(vo_tracks_path, "w") as f:
        json.dump(vo_assembled_tracks, f, indent=2)
    print(f"  VO assembled tracks: {vo_tracks_path}")

    # Contact sheet (12 frames, 4x3)
    print("\n=== CONTACT SHEET ===")
    contact_path = os.path.join(QA, "v12_vertical_contact.jpg")
    dur = get_duration(final_path)
    cframes_dir = os.path.join(QA, "v12_contact_vert")
    os.makedirs(cframes_dir, exist_ok=True)
    for i in range(12):
        ts = dur * (i + 0.5) / 12
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts), "-i", final_path,
            "-vframes", "1", "-q:v", "2",
            os.path.join(cframes_dir, f"frame_{i:02d}.jpg"),
        ], capture_output=True, timeout=30)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", os.path.join(cframes_dir, "frame_%02d.jpg"),
        "-vf", "tile=4x3:padding=4:color=black",
        "-q:v", "3", contact_path,
    ], capture_output=True, timeout=30)
    print(f"  Saved: {contact_path}")

    v12_dur = get_duration(final_path)
    v12_size = os.path.getsize(final_path)
    r = subprocess.run(["md5sum", final_path], capture_output=True, text=True, timeout=30)
    md5 = r.stdout.strip()

    elapsed = time.time() - t0
    print(f"\n=== SEGMENT V12 (9:16) COMPLETE ===")
    print(f"  File: {final_path}")
    print(f"  Duration: {v12_dur:.3f}s")
    print(f"  Size: {v12_size:,} bytes ({v12_size / 1024 / 1024:.1f} MB)")
    print(f"  Render time: {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    print(f"  md5sum: {md5}")
    if dropped_text:
        print(f"  Dropped from clip4: \"{dropped_text[:100]}\"")
