"""
BLINK ENGINE v2 — Realistic eye blinks using cached MediaPipe landmarks.

Approach:
  - ONE-TIME landmark detection on source PNG using MediaPipe 0.10 Tasks API
  - Cached eyelid polygon coords + skin texture patches saved to cache/eye_landmarks.json
  - Per-frame: fill eyelid polygon with skin texture, soft feathered edges
  - NO warpAffine, NO oval overlay, NO global rotation artifacts
  - Upper lid moves DOWN, lower lid rises slightly at full close

Performance: ~0.3ms per frame (pure NumPy/OpenCV, no ML inference per frame)

LAW: apply_blink_gradient() is the only public function. Called from post_process_frames().
"""

import os
import cv2
import json
import math
import random
import base64
import logging
import threading
import numpy as np

logger = logging.getLogger("blink_engine")

ORACLE_DIR = os.path.dirname(os.path.abspath(__file__))
LANDMARKS_PATH = os.path.join(ORACLE_DIR, "cache", "eye_landmarks.json")
MODEL_PATH = "/tmp/face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# Indices for full eye contours
L_UPPER = [246, 161, 160, 159, 158, 157, 173, 133]
L_LOWER = [33,  7,   163, 144, 145, 153, 154, 155, 133]
R_UPPER = [466, 388, 387, 386, 385, 384, 398, 362]
R_LOWER = [263, 249, 390, 373, 374, 380, 381, 382, 362]

# ── Cache ─────────────────────────────────────────────────────────────────
_cache = None
_cache_lock = threading.Lock()


def _decode_patch(b64_str):
    buf = base64.b64decode(b64_str)
    arr = np.frombuffer(buf, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _load_cache():
    global _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
        if os.path.exists(LANDMARKS_PATH):
            try:
                with open(LANDMARKS_PATH) as f:
                    raw = json.load(f)
                _cache = {
                    "left_upper":  [tuple(p) for p in raw["left_upper"]],
                    "left_lower":  [tuple(p) for p in raw["left_lower"]],
                    "right_upper": [tuple(p) for p in raw["right_upper"]],
                    "right_lower": [tuple(p) for p in raw["right_lower"]],
                    "left_top_y":  raw["left_top_y"],
                    "left_bot_y":  raw["left_bot_y"],
                    "right_top_y": raw["right_top_y"],
                    "right_bot_y": raw["right_bot_y"],
                    "left_patch":  _decode_patch(raw["left_patch_b64"])  if raw.get("left_patch_b64")  else None,
                    "right_patch": _decode_patch(raw["right_patch_b64"]) if raw.get("right_patch_b64") else None,
                    "left_skin":   np.array(raw.get("left_skin_mean",  [50, 70, 110]), dtype=np.float32),
                    "right_skin":  np.array(raw.get("right_skin_mean", [65, 88, 130]), dtype=np.float32),
                    "left_rect":   raw.get("left_eye_rect",  [350, 404, 445, 457]),
                    "right_rect":  raw.get("right_eye_rect", [505, 392, 610, 445]),
                }
                logger.info("[BLINK] Eye landmarks loaded from cache")
                return _cache
            except Exception as e:
                logger.error(f"[BLINK] Cache load error: {e}")
        # No cache — try to build it
        _build_landmark_cache()
        return _cache


def _download_model():
    """Download MediaPipe face landmarker model if not present."""
    if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 1000000:
        return True
    try:
        import urllib.request
        logger.info("[BLINK] Downloading face landmarker model...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        logger.info(f"[BLINK] Model downloaded: {os.path.getsize(MODEL_PATH)} bytes")
        return True
    except Exception as e:
        logger.error(f"[BLINK] Model download failed: {e}")
        return False


def _build_landmark_cache():
    """Run MediaPipe on source PNG once, save landmarks + skin patches."""
    global _cache
    avatar_path = os.path.join(ORACLE_DIR, "Proto_P_Avatar_1024.png")
    if not os.path.exists(avatar_path):
        logger.error(f"[BLINK] Avatar not found: {avatar_path}")
        return

    if not _download_model():
        return

    try:
        import mediapipe as mp
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.vision import (
            FaceLandmarker, FaceLandmarkerOptions, RunningMode
        )

        opts = FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.3,
            min_face_presence_confidence=0.3,
        )
        landmarker = FaceLandmarker.create_from_options(opts)

        img_bgr = cv2.imread(avatar_path)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        result = landmarker.detect(mp_image)

        if not result.face_landmarks:
            logger.error("[BLINK] No face detected in source PNG")
            return

        lm = result.face_landmarks[0]
        h, w = img_bgr.shape[:2]

        def get_pts(indices):
            return [[int(lm[i].x * w), int(lm[i].y * h)] for i in indices]

        # Skin patches: strip 15px above the upper eyelid
        l_top = int(lm[159].y * h)
        r_top = int(lm[386].y * h)
        l_x1 = min(p[0] for p in get_pts(L_UPPER)) - 10
        l_x2 = max(p[0] for p in get_pts(L_UPPER)) + 10
        r_x1 = min(p[0] for p in get_pts(R_UPPER)) - 10
        r_x2 = max(p[0] for p in get_pts(R_UPPER)) + 10

        l_patch = img_bgr[max(0, l_top - 18):max(1, l_top - 3), l_x1:l_x2]
        r_patch = img_bgr[max(0, r_top - 18):max(1, r_top - 3), r_x1:r_x2]

        def encode_patch(p):
            _, buf = cv2.imencode(".png", p)
            return base64.b64encode(buf).decode()

        cache_data = {
            "image_size": [w, h],
            "left_upper":  get_pts(L_UPPER),
            "left_lower":  get_pts(L_LOWER),
            "right_upper": get_pts(R_UPPER),
            "right_lower": get_pts(R_LOWER),
            "left_top_y":  l_top,
            "left_bot_y":  int(lm[145].y * h),
            "right_top_y": r_top,
            "right_bot_y": int(lm[374].y * h),
            "left_patch_b64":  encode_patch(l_patch),
            "right_patch_b64": encode_patch(r_patch),
            "left_skin_mean":  l_patch.reshape(-1, 3).mean(axis=0).astype(int).tolist(),
            "right_skin_mean": r_patch.reshape(-1, 3).mean(axis=0).astype(int).tolist(),
            "left_eye_rect":   [l_x1, l_top - 18, l_x2, int(lm[145].y * h) + 5],
            "right_eye_rect":  [r_x1, r_top - 18, r_x2, int(lm[374].y * h) + 5],
        }

        os.makedirs(os.path.dirname(LANDMARKS_PATH), exist_ok=True)
        with open(LANDMARKS_PATH, "w") as f:
            json.dump(cache_data, f)
        logger.info("[BLINK] Eye landmark cache built and saved")

        # Now load it
        _load_cache()

    except Exception as e:
        logger.error(f"[BLINK] Landmark build error: {e}")
        import traceback
        traceback.print_exc()


# ── Per-frame blink application ───────────────────────────────────────────

def _apply_one_eye(frame, upper_pts, lower_pts, patch, skin_color, intensity, is_right=False):
    """
    Apply closing eyelid to one eye.
    upper_pts / lower_pts: list of (x, y) tuples from landmark cache
    patch: skin texture patch from source image (or None)
    intensity: 0.0 = open, 1.0 = fully closed
    """
    if intensity < 0.02:
        return frame

    h_f, w_f = frame.shape[:2]

    # Compute eyelid travel
    top_y = min(p[1] for p in upper_pts)
    bot_y = max(p[1] for p in lower_pts)
    eye_h = max(1, bot_y - top_y)

    # Upper lid drops DOWN
    lid_drop = int(intensity * eye_h)

    # Build the closing polygon:
    # Original upper arc + the same arc shifted down by lid_drop
    shifted = [(p[0], min(p[1] + lid_drop, bot_y)) for p in upper_pts]
    poly = np.array(list(upper_pts) + list(shifted[::-1]), dtype=np.int32)

    # Soft alpha mask
    mask = np.zeros((h_f, w_f), dtype=np.float32)
    cv2.fillPoly(mask, [poly], 1.0)
    # Feather edges inward
    ksize = 7
    mask = cv2.GaussianBlur(mask, (ksize, ksize), 2.0)
    mask3 = mask[:, :, np.newaxis]

    # Eyelid fill: use scaled skin patch if available, else solid color
    x_min = max(0, min(p[0] for p in upper_pts) - 8)
    x_max = min(w_f, max(p[0] for p in upper_pts) + 8)
    fill_w = x_max - x_min
    fill_h = lid_drop + 6

    result = frame.astype(np.float32)

    if patch is not None and fill_h > 1 and fill_w > 1:
        try:
            scaled = cv2.resize(patch, (fill_w, fill_h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
            # Paste into result before blending
            fill = result.copy()
            py1 = max(0, top_y - 2)
            py2 = min(h_f, py1 + fill_h)
            px1, px2 = x_min, x_max
            s_crop = scaled[:py2 - py1, :px2 - px1]
            if s_crop.shape[0] > 0 and s_crop.shape[1] > 0 and s_crop.shape == fill[py1:py2, px1:px2].shape:
                fill[py1:py2, px1:px2] = s_crop
            result = result * (1.0 - mask3) + fill * mask3
        except Exception:
            result = result * (1.0 - mask3) + skin_color * mask3
    else:
        result = result * (1.0 - mask3) + skin_color * mask3

    # Lower lid rises slightly at intensity > 0.6
    if intensity > 0.6:
        rise = int((intensity - 0.6) / 0.4 * eye_h * 0.2)
        shifted_low = [(p[0], max(p[1] - rise, top_y)) for p in lower_pts]
        poly_low = np.array(list(lower_pts) + list(shifted_low[::-1]), dtype=np.int32)
        mask_low = np.zeros((h_f, w_f), dtype=np.float32)
        cv2.fillPoly(mask_low, [poly_low], 1.0)
        mask_low = cv2.GaussianBlur(mask_low, (5, 5), 1.5)[:, :, np.newaxis]
        result = result * (1.0 - mask_low) + skin_color * mask_low

    return result.clip(0, 255).astype(np.uint8)


def apply_blink_gradient(frame, intensity, eye_landmarks=None, face_coords=None):
    """
    Public API — called from post_process_frames().
    Uses cached eye landmarks + skin patches for natural eyelid closure.
    """
    cache = _load_cache()
    if cache is None:
        return frame

    result = _apply_one_eye(
        frame,
        cache["left_upper"], cache["left_lower"],
        cache["left_patch"], cache["left_skin"],
        intensity,
    )
    result = _apply_one_eye(
        result,
        cache["right_upper"], cache["right_lower"],
        cache["right_patch"], cache["right_skin"],
        intensity,
        is_right=True,
    )
    return result


def generate_blink_schedule(n_frames, fps, interval_min=2.5, interval_max=5.0, duration=0.22):
    """
    Generate a dict mapping frame_index -> intensity (0..1).
    Blink curve: fast close (40% of duration), fast open (60%).
    Eyes blink together naturally.
    """
    schedule = {}
    dur_frames = max(3, int(duration * fps))
    t = random.uniform(interval_min * fps, interval_max * fps)

    while t < n_frames - dur_frames:
        start = int(t)
        for i in range(dur_frames):
            pct = i / dur_frames
            # Fast close first 40%, fast open last 60%
            if pct < 0.4:
                intensity = pct / 0.4
            else:
                intensity = 1.0 - (pct - 0.4) / 0.6
            # Smooth with sine
            intensity = math.sin(intensity * math.pi * 0.5) ** 2
            frame_i = start + i
            if frame_i < n_frames:
                schedule[frame_i] = intensity
        t += random.uniform(interval_min * fps, interval_max * fps)

    return schedule


def detect_eye_landmarks(frame):
    """
    Stub for model_registry.py compatibility.
    v2 engine uses pre-cached landmarks from eye_landmarks.json — no per-frame detection needed.
    """
    return None  # v2: cache-based, no per-frame detection
