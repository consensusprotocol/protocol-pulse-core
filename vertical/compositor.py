#!/usr/bin/env python3
"""vertical.compositor -- Per-shot composition engine for 9:16 vertical reframing.

Takes shots from shotmap and composes each to 1080x1920 vertical format.
Harvests composition logic from render_v13_vertical.py but is fully decoupled
from segment_v1 paths.

Four composition rules (Law 18/19 v3):
  1-face  -> fixed face-centered 9:16 crop
  2-face  -> two stacked bands with orange divider
  3-face  -> three stacked bands with orange gutters
  4+/grid -> full 16:9 letterbox top + enlarged guest column bottom

GPU 0 only (set via vertical/__init__.py).
NEVER import cv2.rectangle, cv2.putText, cv2.circle, or PIL ImageDraw here.
Debug drawing lives ONLY in debug.py.
"""
import json
import logging
import math
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageFilter

from vertical import (
    ACCENT_COLOR,
    BASE,
    DIVIDER_H,
    FPS,
    GUTTER_H,
    VERT_H,
    VERT_W,
)

log = logging.getLogger("vertical.compositor")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FACE_MODEL = "/home/ultron/protocol_pulse/segment_v1/qa_v6/blaze_face_short_range.tflite"

# Band heights (derived from VERT_H and divider/gutter sizes)
BAND_2_H = (VERT_H - DIVIDER_H) // 2          # 958 each
BAND_3_H = 607                                  # 3 * 607 + 2 * 12 = 1845
BAND_3_TOTAL = 3 * BAND_3_H + 2 * GUTTER_H    # 1845
BAND_3_PAD_TOP = (VERT_H - BAND_3_TOTAL) // 2  # 37

# Top zone for grid layout: 16:9 frame scaled to 1080 wide
GRID_TOP_H = int(VERT_W * 9 / 16)  # 607
GRID_BOT_H = VERT_H - GRID_TOP_H - DIVIDER_H  # 1309

# Encoder defaults (h264_nvenc, GPU 0)
ENC_ARGS = [
    "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
    "-pix_fmt", "yuv420p",
]
AUDIO_ARGS = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]

# Dark background fill (from PIPELINE_LAWS: #0A0A0F)
BG_DARK = (10, 10, 15)

# Blur radius for blurred-fill backgrounds
BLUR_RADIUS = 40

# MediaPipe detection confidence
FACE_MIN_CONF = 0.4
FACE_SAMPLE_COUNT = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_duration(path: str) -> float:
    """Return duration in seconds via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10,
    )
    return float(r.stdout.strip())


def _run_ffmpeg(args: list, timeout: int = 300, label: str = "ffmpeg") -> bool:
    """Run ffmpeg with error logging. Returns True on success."""
    r = subprocess.run(
        ["ffmpeg", "-y"] + args,
        capture_output=True, timeout=timeout,
    )
    if r.returncode != 0:
        stderr = r.stderr.decode(errors="replace")[-500:]
        log.error("%s failed (rc=%d): %s", label, r.returncode, stderr)
        return False
    return True


def _make_detector():
    """Create a MediaPipe FaceDetector from the frozen model."""
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    if not os.path.isfile(FACE_MODEL):
        raise FileNotFoundError(f"Face model not found: {FACE_MODEL}")

    base_opts = mp_base_options.BaseOptions(model_asset_path=FACE_MODEL)
    return vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(
            base_options=base_opts,
            min_detection_confidence=FACE_MIN_CONF,
        )
    )


def _detect_faces_mp(frame_rgb: np.ndarray, detector) -> list:
    """Run MediaPipe detection on a single RGB frame. Returns list of (cx, cy, w, h)."""
    import mediapipe as mp_lib
    mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=frame_rgb)
    results = detector.detect(mp_image)
    faces = []
    for d in results.detections:
        bb = d.bounding_box
        cx = bb.origin_x + bb.width // 2
        cy = bb.origin_y + bb.height // 2
        faces.append((cx, cy, bb.width, bb.height))
    return faces


def _sample_face_centroids(
    cap: cv2.VideoCapture,
    frame_in: int,
    frame_out: int,
    n_samples: int = FACE_SAMPLE_COUNT,
) -> Tuple[List[int], int, int]:
    """Sample n_samples frames across [frame_in, frame_out), detect faces,
    return (list_of_median_face_cx_per_cluster, src_w, src_h).
    Each entry is the median cx of one stable face position, sorted left-to-right.
    """
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    span = max(frame_out - frame_in, 1)

    sample_frames = [
        frame_in + int(span * (i + 0.5) / n_samples)
        for i in range(n_samples)
    ]

    detector = _make_detector()
    all_cx: List[int] = []

    for fi in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ret, bgr = cap.read()
        if not ret:
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        faces = _detect_faces_mp(rgb, detector)
        for cx, _, _, _ in faces:
            all_cx.append(cx)

    if not all_cx:
        return [src_w // 2], src_w, src_h

    # Cluster by x proximity (200px threshold)
    all_cx_sorted = sorted(all_cx)
    clusters: List[List[int]] = [[all_cx_sorted[0]]]
    for cx in all_cx_sorted[1:]:
        if cx - clusters[-1][-1] < 200:
            clusters[-1].append(cx)
        else:
            clusters.append([cx])

    medians = sorted(int(np.median(c)) for c in clusters)
    return medians, src_w, src_h


def _make_blurred_bg(frame_rgb: np.ndarray, target_w: int, target_h: int,
                     blur_radius: int = BLUR_RADIUS) -> Image.Image:
    """Create a blurred background tile from a source frame."""
    bg = Image.fromarray(frame_rgb).resize((target_w, target_h), Image.LANCZOS)
    return bg.filter(ImageFilter.GaussianBlur(blur_radius))


def _get_mid_frame_pil(cap: cv2.VideoCapture, frame_in: int,
                       frame_out: int) -> Image.Image:
    """Seek to mid-shot frame, return as PIL RGB Image."""
    mid = (frame_in + frame_out) // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
    ret, bgr = cap.read()
    if ret:
        return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return Image.new("RGB", (w, h), BG_DARK)


def _resolve_time_range(shot: Dict[str, Any], src_fps: float) -> Tuple[int, int, float, float]:
    """Derive frame_in, frame_out, t_in, duration from shot dict.

    When edl_t_in/edl_t_out are set (injected by reframe.py from the EDL),
    use them as the authoritative source of truth and convert to frame numbers
    using the *actual* source fps.  This avoids the fps mismatch when shotmap
    was run on a 30fps re-encoded window but the master source is 29.97fps.

    Returns (frame_in, frame_out, t_in, duration).
    """
    if "edl_t_in" in shot and "edl_t_out" in shot:
        t_in = shot["edl_t_in"]
        t_out = shot["edl_t_out"]
        duration = t_out - t_in
        frame_in = int(t_in * src_fps)
        frame_out = int(t_out * src_fps)
    else:
        frame_in = shot["frame_in"]
        frame_out = shot["frame_out"]
        t_in = frame_in / src_fps
        duration = (frame_out - frame_in) / src_fps
    return frame_in, frame_out, t_in, duration


def _compute_face_crop(face_cx: int, face_cy: int, face_w: int, face_h: int,
                       target_aspect: float, src_w: int, src_h: int,
                       padding_mult: float = 1.5,
                       min_padding: int = 300) -> Dict[str, int]:
    """Compute a crop rectangle centered on a face with the given target aspect ratio.
    Returns dict with keys: x, y, w, h."""
    face_pad = max(int(face_h * padding_mult), min_padding)
    crop_h = min(int(face_h + face_pad * 2), src_h)
    crop_w = int(crop_h * target_aspect)

    if crop_w > src_w:
        crop_w = src_w
        crop_h = int(crop_w / target_aspect)

    crop_x = max(0, min(src_w - crop_w, face_cx - crop_w // 2))
    crop_y = max(0, min(src_h - crop_h, face_cy - crop_h // 2))

    return {"x": crop_x, "y": crop_y, "w": crop_w, "h": crop_h}


def _pipe_frames_to_ffmpeg(
    frames_iter,
    out_path: str,
    width: int,
    height: int,
    audio_src: Optional[str] = None,
    duration: Optional[float] = None,
    timeout: int = 600,
) -> bool:
    """Pipe raw RGB24 frames from an iterator to ffmpeg via stdin.
    Optionally mux audio from audio_src. Returns True on success.

    duration: if set, hard-limits the output to this many seconds via -t.
              This replaces -shortest which overshoots with nvenc pipe input.
    """

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(FPS),
        "-i", "pipe:0",
    ]
    if audio_src:
        cmd += ["-i", audio_src, "-map", "0:v", "-map", "1:a"]

    cmd += [
        "-vf", "setsar=1:1",
    ] + ENC_ARGS + AUDIO_ARGS

    if duration is not None:
        cmd += ["-t", str(duration)]
    elif audio_src:
        cmd += ["-shortest"]
    cmd += ["-movflags", "+faststart", out_path]

    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    try:
        for frame_rgb in frames_iter:
            proc.stdin.write(frame_rgb.tobytes())
        proc.stdin.close()
        _, stderr = proc.communicate(timeout=timeout)
    except BrokenPipeError:
        # -shortest causes ffmpeg to close stdin when the audio track ends.
        # Source is 30fps but output is 24fps, so extra frames are expected.
        # Let ffmpeg finish and check the output file.
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            stdout_data, stderr = proc.stdout.read(), proc.stderr.read()
        except Exception:
            stdout_data, stderr = b"", b""
        proc.wait(timeout=timeout)
        if proc.returncode == 0:
            log.info("pipe closed by -shortest (audio ended before all frames sent)")
        else:
            log.error("ffmpeg failed after -shortest pipe close (rc=%d): %s",
                      proc.returncode, stderr.decode(errors="replace")[-500:])
            return False
    except Exception as exc:
        proc.kill()
        log.error("pipe encode error: %s", exc)
        return False

    if proc.returncode != 0:
        log.error("ffmpeg pipe encode failed (rc=%d): %s",
                  proc.returncode, stderr.decode(errors="replace")[-500:])
        return False

    return os.path.isfile(out_path) and os.path.getsize(out_path) > 1000


def _validate_output(path: str, label: str) -> bool:
    """Check output file exists and has non-trivial size."""
    if not os.path.isfile(path) or os.path.getsize(path) < 1000:
        log.error("%s: output missing or empty: %s", label, path)
        return False
    dur = _get_duration(path)
    log.info("%s: %.2fs -> %s", label, dur, path)
    return True


# ---------------------------------------------------------------------------
# Composition functions
# ---------------------------------------------------------------------------

def compose_1face(
    shot: Dict[str, Any],
    master_path: str,
    out_path: str,
    work_dir: str,
) -> bool:
    """1 face -> fixed face-centered 9:16 crop (no panning).

    Samples ~10 frames across the shot via MediaPipe to find the median face cx,
    then applies a single ffmpeg crop+scale for the entire shot duration.
    """
    label = shot.get("id", "1face")
    log.info("compose_1face [%s]", label)

    cap = cv2.VideoCapture(master_path)
    if not cap.isOpened():
        log.error("Cannot open master: %s", master_path)
        return False

    src_fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_in, frame_out, t_in, duration = _resolve_time_range(shot, src_fps)
    log.info("  frames %d-%d, t=%.3f-%.3f (%.3fs)", frame_in, frame_out, t_in, t_in + duration, duration)

    # 9:16 crop width from source height: crop_w / src_h = VERT_W / VERT_H
    crop_w = int(src_h * VERT_W / VERT_H)
    crop_w = min(crop_w, src_w)  # clamp to source width

    # Sample face centroids
    centroids, _, _ = _sample_face_centroids(cap, frame_in, frame_out)
    cap.release()

    # Use the single dominant cluster (largest face)
    if centroids:
        face_cx = centroids[0] if len(centroids) == 1 else centroids[len(centroids) // 2]
    else:
        face_cx = src_w // 2

    crop_x = max(0, min(src_w - crop_w, face_cx - crop_w // 2))

    log.info("  face_cx=%d crop_w=%d crop_x=%d (src %dx%d)", face_cx, crop_w, crop_x, src_w, src_h)

    ok = _run_ffmpeg([
        "-ss", str(t_in), "-t", str(duration), "-i", master_path,
        "-vf", (f"crop={crop_w}:{src_h}:{crop_x}:0,"
                f"scale={VERT_W}:{VERT_H}:flags=lanczos,setsar=1:1"),
        *ENC_ARGS, "-r", str(FPS),
        *AUDIO_ARGS,
        "-t", str(duration),
        "-movflags", "+faststart", out_path,
    ], timeout=300, label=f"1face:{label}")

    return ok and _validate_output(out_path, f"1face:{label}")


def compose_2face(
    shot: Dict[str, Any],
    master_path: str,
    out_path: str,
    work_dir: str,
    speaker_tile: int = -1,
    speaker_confidence: float = 0.0,
) -> bool:
    """2 faces -> two stacked bands with orange divider.

    Each band: crop around one face from source, scaled to 1080 wide.
    Law 18b: when speaker_confidence >= 0.35, the speaker's band takes ~60% height.
    Otherwise equal bands: (VERT_H - DIVIDER_H) // 2 = 958 px each.
    Blurred-fill sides if face crop is narrower than 1080.
    Bands ordered left-to-right from source (leftmost face = top band).
    """
    label = shot.get("id", "2face")
    face_info = shot.get("faces", [])

    # Law 18b: speaker-dominant bands
    usable_h = VERT_H - DIVIDER_H  # 1916
    if speaker_confidence >= 0.35 and 0 <= speaker_tile <= 1:
        big_h = int(usable_h * 0.6)   # ~1150
        small_h = usable_h - big_h    # ~766
        band_heights = [big_h if i == speaker_tile else small_h for i in range(2)]
        mode = "dominant"
    else:
        band_heights = [BAND_2_H, BAND_2_H]
        mode = "equal"

    cap = cv2.VideoCapture(master_path)
    if not cap.isOpened():
        log.error("Cannot open master: %s", master_path)
        return False

    src_fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_in, frame_out, t_in, duration = _resolve_time_range(shot, src_fps)
    log.info("compose_2face [%s]: frames %d-%d, t=%.3f-%.3f (%.3fs), %d faces, mode=%s, bands=%s",
             label, frame_in, frame_out, t_in, t_in + duration, duration,
             len(face_info), mode, band_heights)

    # If face_info not pre-populated, detect now
    if len(face_info) < 2:
        centroids, src_w, src_h = _sample_face_centroids(cap, frame_in, frame_out)
        face_info = [{"cx": cx, "cy": src_h // 2, "w": 200, "h": 200} for cx in centroids[:2]]
        if len(face_info) < 2:
            log.warning("Only %d faces found for 2face layout, falling back to 1face", len(face_info))
            cap.release()
            return compose_1face(shot, master_path, out_path, work_dir)

    # Sort faces left-to-right (leftmost = top band)
    face_info = sorted(face_info, key=lambda f: f["cx"])

    # Actual band heights (ensure even for yuv420p)
    band_heights = [h - (h % 2) for h in band_heights]

    # Compute crop rectangles for each face (use per-band height for aspect)
    face_crops = []
    for i, fi in enumerate(face_info[:2]):
        bh = band_heights[i]
        crop_aspect = VERT_W / bh
        crop = _compute_face_crop(
            fi["cx"], fi.get("cy", src_h // 2),
            fi.get("w", 200), fi.get("h", 200),
            target_aspect=crop_aspect,
            src_w=src_w, src_h=src_h,
            padding_mult=1.5, min_padding=300,
        )
        face_crops.append(crop)
        log.info("  face_%d: crop %dx%d @ (%d,%d) band_h=%d", i, crop["w"], crop["h"], crop["x"], crop["y"], bh)

    # Get mid-frame for blurred background
    mid_pil = _get_mid_frame_pil(cap, frame_in, frame_out)

    # Pre-build divider strip
    divider_strip = Image.new("RGB", (VERT_W, DIVIDER_H), ACCENT_COLOR)

    log.info("  Layout: 2 bands %s, divider=%dpx, mode=%s", band_heights, DIVIDER_H, mode)

    # Pre-compute blurred backgrounds (one per band, from mid-frame)
    bg_blurred_bands = []
    for idx, crop in enumerate(face_crops):
        bh = band_heights[idx]
        bg_region = mid_pil.crop((crop["x"], crop["y"],
                                  crop["x"] + crop["w"],
                                  crop["y"] + crop["h"]))
        bg_blurred = bg_region.resize((VERT_W, bh), Image.LANCZOS)
        bg_blurred = bg_blurred.filter(ImageFilter.GaussianBlur(radius=20))
        bg_blurred_bands.append(bg_blurred)

    # Frame-by-frame compositing via pipe
    def frame_generator():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_in)
        for fi in range(frame_in, frame_out):
            ret, bgr = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(rgb)
            canvas = Image.new("RGB", (VERT_W, VERT_H), BG_DARK)

            y_cursor = 0
            for band_idx, crop in enumerate(face_crops):
                bh = band_heights[band_idx]
                face_region = pil_frame.crop((crop["x"], crop["y"],
                                              crop["x"] + crop["w"],
                                              crop["y"] + crop["h"]))

                # Scale to fill band width
                scale = VERT_W / crop["w"]
                scaled_h = int(crop["h"] * scale)
                face_scaled = face_region.resize((VERT_W, scaled_h), Image.LANCZOS)

                # Start with blurred background
                band = bg_blurred_bands[band_idx].copy()

                # Center face vertically in band
                y_off = (bh - scaled_h) // 2
                if y_off < 0:
                    face_cropped = face_scaled.crop((0, -y_off, VERT_W, -y_off + bh))
                    band.paste(face_cropped, (0, 0))
                else:
                    band.paste(face_scaled, (0, y_off))

                canvas.paste(band, (0, y_cursor))
                y_cursor += bh

                # Orange divider after first band
                if band_idx == 0:
                    canvas.paste(divider_strip, (0, y_cursor))
                    y_cursor += DIVIDER_H

            yield np.array(canvas)
        cap.release()

    # Extract audio for the shot range (t_in/duration set by _resolve_time_range)
    audio_tmp = os.path.join(work_dir, f"{label}_audio.wav")
    _run_ffmpeg([
        "-ss", str(t_in), "-t", str(duration), "-i", master_path,
        "-vn", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", audio_tmp,
    ], timeout=60, label=f"2face_audio:{label}")

    audio_src = audio_tmp if os.path.isfile(audio_tmp) else None
    ok = _pipe_frames_to_ffmpeg(
        frame_generator(), out_path, VERT_W, VERT_H,
        audio_src=audio_src, duration=duration, timeout=600,
    )

    # Cleanup temp audio
    if audio_src and os.path.isfile(audio_src):
        os.remove(audio_src)

    return ok and _validate_output(out_path, f"2face:{label}")


def compose_3face(
    shot: Dict[str, Any],
    master_path: str,
    out_path: str,
    work_dir: str,
) -> bool:
    """3 faces -> three stacked bands 1080x607 each.

    3*607 + 2*12 = 1845, centered vertically in 1920 -> pad_top=37, pad_bottom=38.
    Each band: crop face region from source tile, scale to 1080x607.
    Blurred-fill sides for narrow tiles. Orange gutter between bands.
    """
    label = shot.get("id", "3face")
    face_info = shot.get("faces", [])

    cap = cv2.VideoCapture(master_path)
    if not cap.isOpened():
        log.error("Cannot open master: %s", master_path)
        return False

    src_fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_in, frame_out, t_in, duration = _resolve_time_range(shot, src_fps)
    log.info("compose_3face [%s]: frames %d-%d, t=%.3f-%.3f (%.3fs), %d faces",
             label, frame_in, frame_out, t_in, t_in + duration, duration, len(face_info))

    # If face_info not pre-populated, detect now
    if len(face_info) < 3:
        centroids, src_w, src_h = _sample_face_centroids(cap, frame_in, frame_out)
        face_info = [{"cx": cx, "cy": src_h // 2, "w": 200, "h": 200} for cx in centroids[:3]]
        if len(face_info) < 3:
            log.warning("Only %d faces for 3face layout, falling back to 2face/1face",
                        len(face_info))
            cap.release()
            if len(face_info) == 2:
                shot_copy = dict(shot, faces=face_info)
                return compose_2face(shot_copy, master_path, out_path, work_dir)
            return compose_1face(shot, master_path, out_path, work_dir)

    # Sort faces left-to-right (leftmost = top band)
    face_info = sorted(face_info, key=lambda f: f["cx"])

    band_h = BAND_3_H  # 607
    top_pad = BAND_3_PAD_TOP  # 37

    crop_aspect = VERT_W / band_h  # ~1.779

    face_crops = []
    for i, fi in enumerate(face_info[:3]):
        crop = _compute_face_crop(
            fi["cx"], fi.get("cy", src_h // 2),
            fi.get("w", 200), fi.get("h", 200),
            target_aspect=crop_aspect,
            src_w=src_w, src_h=src_h,
            padding_mult=1.2, min_padding=200,
        )
        face_crops.append(crop)
        log.info("  face_%d: crop %dx%d @ (%d,%d)", i, crop["w"], crop["h"], crop["x"], crop["y"])

    # Mid-frame for blurred backgrounds
    mid_pil = _get_mid_frame_pil(cap, frame_in, frame_out)

    # Pre-build gutter strip
    gutter_strip = Image.new("RGB", (VERT_W, GUTTER_H), ACCENT_COLOR)

    log.info("  Layout: 3 x %dx%d, gutters=%dpx, pad_top=%dpx",
             VERT_W, band_h, GUTTER_H, top_pad)

    # Pre-compute blurred backgrounds
    bg_blurred_bands = []
    for crop in face_crops:
        bg_region = mid_pil.crop((crop["x"], crop["y"],
                                  crop["x"] + crop["w"],
                                  crop["y"] + crop["h"]))
        bg_blurred = bg_region.resize((VERT_W, band_h), Image.LANCZOS)
        bg_blurred = bg_blurred.filter(ImageFilter.GaussianBlur(radius=20))
        bg_blurred_bands.append(bg_blurred)

    def frame_generator():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_in)
        for fi in range(frame_in, frame_out):
            ret, bgr = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(rgb)
            canvas = Image.new("RGB", (VERT_W, VERT_H), BG_DARK)

            for band_idx, crop in enumerate(face_crops):
                face_region = pil_frame.crop((crop["x"], crop["y"],
                                              crop["x"] + crop["w"],
                                              crop["y"] + crop["h"]))
                scale = VERT_W / crop["w"]
                scaled_h = int(crop["h"] * scale)
                face_scaled = face_region.resize((VERT_W, scaled_h), Image.LANCZOS)

                band = bg_blurred_bands[band_idx].copy()
                y_off = (band_h - scaled_h) // 2
                if y_off < 0:
                    face_cropped = face_scaled.crop((0, -y_off, VERT_W, -y_off + band_h))
                    band.paste(face_cropped, (0, 0))
                else:
                    band.paste(face_scaled, (0, y_off))

                band_y = top_pad + band_idx * (band_h + GUTTER_H)
                canvas.paste(band, (0, band_y))

            # Orange gutters between bands
            canvas.paste(gutter_strip, (0, top_pad + band_h))
            canvas.paste(gutter_strip, (0, top_pad + 2 * band_h + GUTTER_H))

            yield np.array(canvas)
        cap.release()

    # Extract audio (t_in/duration set by _resolve_time_range)
    audio_tmp = os.path.join(work_dir, f"{label}_audio.wav")
    _run_ffmpeg([
        "-ss", str(t_in), "-t", str(duration), "-i", master_path,
        "-vn", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", audio_tmp,
    ], timeout=60, label=f"3face_audio:{label}")

    audio_src = audio_tmp if os.path.isfile(audio_tmp) else None
    ok = _pipe_frames_to_ffmpeg(
        frame_generator(), out_path, VERT_W, VERT_H,
        audio_src=audio_src, duration=duration, timeout=600,
    )

    if audio_src and os.path.isfile(audio_src):
        os.remove(audio_src)

    return ok and _validate_output(out_path, f"3face:{label}")


def compose_grid(
    shot: Dict[str, Any],
    master_path: str,
    out_path: str,
    work_dir: str,
) -> bool:
    """4+ faces or screen-share -> full 16:9 frame letterboxed on top +
    enlarged guest column below.

    TOP:    entire original 16:9 frame scaled to 1080 wide -> 607px tall.
    BOTTOM: face region(s) cropped and scaled to fill remaining 1309px.
    Orange accent divider between top and bottom.
    Blurred-fill for any gaps.
    """
    label = shot.get("id", "grid")
    face_info = shot.get("faces", [])

    cap = cv2.VideoCapture(master_path)
    if not cap.isOpened():
        log.error("Cannot open master: %s", master_path)
        return False

    src_fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_in, frame_out, t_in, duration = _resolve_time_range(shot, src_fps)
    log.info("compose_grid [%s]: frames %d-%d, t=%.3f-%.3f (%.3fs), %d faces",
             label, frame_in, frame_out, t_in, t_in + duration, duration, len(face_info))

    # Detect faces if not provided
    if not face_info:
        centroids, src_w, src_h = _sample_face_centroids(cap, frame_in, frame_out)
        face_info = [{"cx": cx, "cy": src_h // 2, "w": 200, "h": 200} for cx in centroids]

    # Sort left-to-right
    face_info = sorted(face_info, key=lambda f: f["cx"])

    # Mid-frame for blurred background
    mid_pil = _get_mid_frame_pil(cap, frame_in, frame_out)

    # Compute guest column crop: bounding box around all faces
    if face_info:
        min_cx = min(f["cx"] for f in face_info)
        max_cx = max(f["cx"] for f in face_info)
        max_fw = max(f.get("w", 200) for f in face_info)
        # Pad generously around the face cluster
        guest_x1 = max(0, min_cx - max_fw)
        guest_x2 = min(src_w, max_cx + max_fw)
        guest_y1 = 0
        guest_y2 = src_h
    else:
        # No faces: use center half
        guest_x1 = src_w // 4
        guest_x2 = 3 * src_w // 4
        guest_y1 = 0
        guest_y2 = src_h

    guest_crop_w = guest_x2 - guest_x1
    guest_crop_h = guest_y2 - guest_y1

    # Target bottom zone aspect
    bot_aspect = VERT_W / GRID_BOT_H  # ~0.825

    divider_strip = Image.new("RGB", (VERT_W, DIVIDER_H), ACCENT_COLOR)

    log.info("  Layout: top=%dx%d, divider=%dpx, bottom=%dx%d",
             VERT_W, GRID_TOP_H, DIVIDER_H, VERT_W, GRID_BOT_H)
    log.info("  Guest crop: %dx%d @ (%d,%d)",
             guest_crop_w, guest_crop_h, guest_x1, guest_y1)

    # Pre-compute blurred BG for bottom zone
    bg_bot_blurred = _make_blurred_bg(
        np.array(mid_pil), VERT_W, GRID_BOT_H, blur_radius=25,
    )

    def frame_generator():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_in)
        for fi in range(frame_in, frame_out):
            ret, bgr = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(rgb)
            canvas = Image.new("RGB", (VERT_W, VERT_H), BG_DARK)

            # TOP: full 16:9 frame scaled to 1080 wide
            top_scaled = pil_frame.resize((VERT_W, GRID_TOP_H), Image.LANCZOS)
            canvas.paste(top_scaled, (0, 0))

            # DIVIDER
            canvas.paste(divider_strip, (0, GRID_TOP_H))

            # BOTTOM: guest column crop, scaled to fill
            guest_region = pil_frame.crop((guest_x1, guest_y1,
                                           guest_x2, guest_y2))

            # Scale to fill bottom zone width, maintaining aspect
            scale = VERT_W / guest_crop_w
            scaled_h = int(guest_crop_h * scale)
            guest_scaled = guest_region.resize((VERT_W, scaled_h), Image.LANCZOS)

            # Blurred background for bottom zone
            bot_band = bg_bot_blurred.copy()

            # Center guest crop vertically in bottom zone
            y_off = (GRID_BOT_H - scaled_h) // 2
            if y_off < 0:
                # Guest taller than bottom zone: center-crop
                guest_cropped = guest_scaled.crop((0, -y_off, VERT_W, -y_off + GRID_BOT_H))
                bot_band.paste(guest_cropped, (0, 0))
            else:
                bot_band.paste(guest_scaled, (0, y_off))

            canvas.paste(bot_band, (0, GRID_TOP_H + DIVIDER_H))

            yield np.array(canvas)
        cap.release()

    # Extract audio (t_in/duration set by _resolve_time_range)
    audio_tmp = os.path.join(work_dir, f"{label}_audio.wav")
    _run_ffmpeg([
        "-ss", str(t_in), "-t", str(duration), "-i", master_path,
        "-vn", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", audio_tmp,
    ], timeout=60, label=f"grid_audio:{label}")

    audio_src = audio_tmp if os.path.isfile(audio_tmp) else None
    ok = _pipe_frames_to_ffmpeg(
        frame_generator(), out_path, VERT_W, VERT_H,
        audio_src=audio_src, duration=duration, timeout=600,
    )

    if audio_src and os.path.isfile(audio_src):
        os.remove(audio_src)

    return ok and _validate_output(out_path, f"grid:{label}")


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_COMPOSE_DISPATCH = {
    1: compose_1face,
    2: compose_2face,
    3: compose_3face,
}


def _classify_shot(shot: Dict[str, Any]) -> int:
    """Return the face count classification for dispatch.
    Returns 1, 2, 3, or 4 (meaning 4+ / grid)."""
    if shot.get("has_screenshare", False):
        return 4
    n = shot.get("face_count", 1)
    if n >= 4:
        return 4
    return max(1, n)


def compose_all(
    shot_map: List[Dict[str, Any]],
    master_path: str,
    out_dir: str,
    work_dir: str,
) -> List[Dict[str, Any]]:
    """Iterate all shots in shot_map, dispatch to the correct compose function.

    Each shot dict should contain at minimum:
        id:             str     - unique shot identifier
        frame_in:       int     - first frame (inclusive)
        frame_out:      int     - last frame (exclusive)
        face_count:     int     - number of detected faces
        faces:          list    - list of {cx, cy, w, h} dicts (optional)
        has_screenshare: bool   - True if screen-share detected (optional)

    Returns a list of metadata dicts, one per shot:
        id, layout, out_path, duration, ok
    """
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)

    results: List[Dict[str, Any]] = []
    total_t0 = time.time()

    for idx, shot in enumerate(shot_map):
        shot_id = shot.get("id", f"shot_{idx:03d}")
        classification = _classify_shot(shot)
        layout_name = {1: "1face", 2: "2face", 3: "3face", 4: "grid"}[classification]

        out_path = os.path.join(out_dir, f"{shot_id}_vert.mp4")
        log.info("--- Shot %d/%d [%s] -> %s ---",
                 idx + 1, len(shot_map), layout_name, shot_id)

        t0 = time.time()

        compose_fn = _COMPOSE_DISPATCH.get(classification, compose_grid)
        ok = compose_fn(shot, master_path, out_path, work_dir)

        elapsed = time.time() - t0
        duration = _get_duration(out_path) if ok and os.path.isfile(out_path) else 0.0

        results.append({
            "id": shot_id,
            "layout": layout_name,
            "face_count": shot.get("face_count", classification),
            "out_path": out_path,
            "duration": duration,
            "ok": ok,
            "elapsed": round(elapsed, 2),
        })

        if ok:
            log.info("  OK: %.2fs rendered in %.1fs", duration, elapsed)
        else:
            log.error("  FAIL: shot %s (%s)", shot_id, layout_name)

    total_elapsed = time.time() - total_t0
    n_ok = sum(1 for r in results if r["ok"])
    log.info("compose_all: %d/%d shots OK in %.1fs", n_ok, len(results), total_elapsed)

    return results


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def assemble(
    composed_shots: List[Dict[str, Any]],
    out_path: str,
    fps: int = FPS,
) -> bool:
    """Concatenate composed shot videos into final output using ffmpeg concat demuxer.

    composed_shots: list of dicts from compose_all (must have "out_path" and "ok" keys).
    Skips any shot where ok=False.
    """
    valid = [s for s in composed_shots if s.get("ok") and os.path.isfile(s["out_path"])]
    if not valid:
        log.error("assemble: no valid shots to concatenate")
        return False

    # Write concat list
    work_dir = os.path.dirname(out_path) or "."
    concat_list = os.path.join(work_dir, "vert_concat_list.txt")
    with open(concat_list, "w") as f:
        for s in valid:
            f.write(f"file '{os.path.abspath(s['out_path'])}'\n")

    log.info("assemble: %d shots -> %s", len(valid), out_path)
    for s in valid:
        log.info("  %s [%s] %.2fs", s["id"], s["layout"], s["duration"])

    ok = _run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-vf", "setpts=PTS-STARTPTS,setsar=1:1",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        *ENC_ARGS,
        "-qp", "18",  # Slightly higher quality for final output
        "-r", str(fps),
        *AUDIO_ARGS,
        "-movflags", "+faststart", out_path,
    ], timeout=600, label="assemble")

    # Cleanup concat list
    if os.path.isfile(concat_list):
        os.remove(concat_list)

    if ok and _validate_output(out_path, "assemble"):
        total_dur = _get_duration(out_path)
        log.info("assemble: final output %.2fs -> %s", total_dur, out_path)
        return True
    return False
