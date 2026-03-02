"""
ORACLE AVATAR SERVER — Enhanced with Blinks + Head Movement
============================================================
GPU-accelerated Wav2Lip lip-sync with post-processing:
  - Eye blinks: Random intervals (2-6s), natural 150-300ms duration
  - Head movement: Subtle sine-wave rotation + translation
  - Runs on Ultron: 4x RTX 4090, port 8200

Deploy: ~/protocol_pulse/oracle/avatar_server.py
Launch: cd ~/protocol_pulse/oracle && python3 avatar_server.py
"""

import os
import sys
import time
import uuid
import math
import random
import base64
import logging
import tempfile
import threading
import numpy as np
from pathlib import Path
from io import BytesIO

import cv2
import torch
from flask import Flask, request, jsonify

# ─── Config ───────────────────────────────────────────────────────────
PORT = 8200
WAV2LIP_DIR = os.path.expanduser("~/Wav2Lip")
CHECKPOINT = os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth")
AVATAR_SOURCE = os.path.join(os.path.dirname(__file__), "Proto_P_Avatar_512.png")
BATCH_SIZE = 48  # Optimal for RTX 4090
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Post-processing config
BLINK_INTERVAL_MIN = 3.0   # seconds between blinks (centered at 3.5s)
BLINK_INTERVAL_MAX = 4.0
BLINK_DURATION = 0.15      # seconds for a full blink (close + open)
HEAD_ROTATION_AMPLITUDE = 1.0  # degrees max rotation
HEAD_TRANSLATION_X = 1.5   # pixels max horizontal shift
HEAD_TRANSLATION_Y = 1.0   # pixels max vertical shift
HEAD_PERIOD = 4.0           # seconds for one full head movement cycle

# ─── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("avatar_server")

app = Flask(__name__)

# ─── Globals (pre-loaded for speed) ──────────────────────────────────
wav2lip_model = None
face_detector = None
avatar_face = None
avatar_face_coords = None
_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════════
# WAV2LIP LOADING
# ═══════════════════════════════════════════════════════════════════════

def load_wav2lip():
    """Load Wav2Lip model and pre-detect face in avatar source."""
    global wav2lip_model, face_detector, avatar_face, avatar_face_coords

    # Add Wav2Lip to path
    if WAV2LIP_DIR not in sys.path:
        sys.path.insert(0, WAV2LIP_DIR)

    from models import Wav2Lip as Wav2LipModel
    import face_detection

    logger.info(f"Loading Wav2Lip from {CHECKPOINT} on {DEVICE}...")
    model = Wav2LipModel()
    ckpt = torch.load(CHECKPOINT, map_location=DEVICE)
    s = ckpt["state_dict"]
    new_s = {}
    for k, v in s.items():
        new_s[k.replace("module.", "")] = v
    model.load_state_dict(new_s)
    model = model.to(DEVICE).eval()
    wav2lip_model = model
    logger.info("Wav2Lip model loaded.")

    # Face detector
    face_detector = face_detection.FaceAlignment(
        face_detection.LandmarksType._2D,
        flip_input=False,
        device=DEVICE
    )
    logger.info("Face detector loaded.")

    # Pre-load and detect face in avatar
    if not os.path.exists(AVATAR_SOURCE):
        logger.error(f"Avatar source not found: {AVATAR_SOURCE}")
        return

    img = cv2.imread(AVATAR_SOURCE)
    if img is None:
        logger.error(f"Failed to read avatar source: {AVATAR_SOURCE}")
        return

    avatar_face = img.copy()
    results = face_detector.get_detections_for_batch(
        np.array([img])
    )
    if results[0] is not None:
        det = results[0]
        avatar_face_coords = (
            max(0, int(det[1])),  # y1
            min(img.shape[0], int(det[3])),  # y2
            max(0, int(det[0])),  # x1
            min(img.shape[1], int(det[2]))   # x2
        )
        logger.info(f"Face detected at {avatar_face_coords} in {img.shape[1]}x{img.shape[0]} image")
    else:
        logger.error("No face detected in avatar source!")
        avatar_face_coords = None


# ═══════════════════════════════════════════════════════════════════════
# WAV2LIP INFERENCE
# ═══════════════════════════════════════════════════════════════════════

def wav2lip_generate(audio_path):
    """Run Wav2Lip inference. Returns list of BGR frames."""
    if wav2lip_model is None or avatar_face is None or avatar_face_coords is None:
        raise RuntimeError("Model or avatar not loaded")

    import audio as wav2lip_audio

    # Load audio mel spectrogram
    wav = wav2lip_audio.load_wav(audio_path, 16000); mel = wav2lip_audio.melspectrogram(wav)
    if mel.shape[1] == 0:
        raise ValueError("Empty audio")

    mel_chunks = []
    mel_step = 16  # Wav2Lip default
    i = 0
    while i < mel.shape[1]:
        chunk = mel[:, i:i + mel_step]
        if chunk.shape[1] < mel_step:
            chunk = np.pad(chunk, ((0, 0), (0, mel_step - chunk.shape[1])))
        mel_chunks.append(chunk)
        i += mel_step

    # Generate frames
    y1, y2, x1, x2 = avatar_face_coords
    face_crop = avatar_face[y1:y2, x1:x2]
    face_resized = cv2.resize(face_crop, (96, 96))
    face_masked = face_resized.copy()
    face_masked[face_resized.shape[0]//2:, :] = 0

    frames = []
    total_chunks = len(mel_chunks)

    for batch_start in range(0, total_chunks, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_chunks)
        batch_mels = mel_chunks[batch_start:batch_end]

        img_concat = np.concatenate((face_masked, face_resized), axis=2)
        img_batch = np.array([img_concat / 255.0] * len(batch_mels), dtype=np.float32)
        mel_batch = np.array(batch_mels, dtype=np.float32)

        # Wav2Lip expects: img_batch (B, H, W, C) and mel_batch (B, T, mel_dim)
        img_batch = torch.FloatTensor(img_batch.transpose(0, 3, 1, 2)).to(DEVICE)
        mel_batch = torch.FloatTensor(mel_batch[:, np.newaxis, :, :]).to(DEVICE)

        with torch.no_grad():
            pred = wav2lip_model(mel_batch, img_batch)

        pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.0

        for p in pred:
            p_resized = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
            full_frame = avatar_face.copy()
            full_frame[y1:y2, x1:x2] = p_resized
            frames.append(full_frame)

    return frames


# ═══════════════════════════════════════════════════════════════════════
# POST-PROCESSING: EYE BLINKS
# ═══════════════════════════════════════════════════════════════════════

def generate_blink_schedule(num_frames, fps):
    """Generate a schedule of blink events. Returns list of (frame_idx, intensity) tuples.
    intensity: 0.0 = fully open, 1.0 = fully closed."""
    duration_sec = num_frames / fps
    blink_frames = {}

    t = random.uniform(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
    while t < duration_sec - BLINK_DURATION:
        blink_center = t + BLINK_DURATION / 2
        blink_half_frames = int((BLINK_DURATION / 2) * fps)

        center_frame = int(blink_center * fps)
        for offset in range(-blink_half_frames, blink_half_frames + 1):
            frame_idx = center_frame + offset
            if 0 <= frame_idx < num_frames:
                # Cosine curve: 0 -> 1 -> 0
                progress = abs(offset) / max(blink_half_frames, 1)
                intensity = max(0, 1.0 - progress)
                # Use cosine for smoother easing
                intensity = 0.5 * (1 + math.cos(math.pi * progress))
                blink_frames[frame_idx] = max(blink_frames.get(frame_idx, 0), intensity)

        # Next blink
        t += BLINK_DURATION + random.uniform(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)

    return blink_frames


def apply_blink(frame, intensity, face_coords):
    """Apply blink effect by darkening the eye region proportionally to intensity."""
    if face_coords is None or intensity <= 0.01:
        return frame

    y1, y2, x1, x2 = face_coords
    face_h = y2 - y1
    face_w = x2 - x1

    # Eye region: roughly top 25-42% of face, with some padding
    eye_y1 = y1 + int(face_h * 0.22)
    eye_y2 = y1 + int(face_h * 0.42)
    eye_x1 = x1 + int(face_w * 0.08)
    eye_x2 = x2 - int(face_w * 0.08)

    # Clamp to frame bounds
    h, w = frame.shape[:2]
    eye_y1 = max(0, min(eye_y1, h - 1))
    eye_y2 = max(eye_y1 + 1, min(eye_y2, h))
    eye_x1 = max(0, min(eye_x1, w - 1))
    eye_x2 = max(eye_x1 + 1, min(eye_x2, w))

    result = frame.copy()
    eye_region = result[eye_y1:eye_y2, eye_x1:eye_x2].copy()

    # Create a skin-tone colored overlay for the "eyelid"
    # Sample average skin color from just above the eye region
    skin_sample_y = max(0, eye_y1 - int(face_h * 0.05))
    skin_sample = frame[skin_sample_y:eye_y1, eye_x1:eye_x2]
    if skin_sample.size > 0:
        skin_color = skin_sample.mean(axis=(0, 1)).astype(np.uint8)
    else:
        skin_color = np.array([140, 130, 125], dtype=np.uint8)  # fallback

    # Create eyelid overlay
    eyelid = np.full_like(eye_region, skin_color)

    # Vertical gradient: blink closes from top
    rows = eye_region.shape[0]
    close_rows = int(rows * intensity * 0.7)  # How many rows the eyelid covers

    if close_rows > 0:
        # Top eyelid comes down
        alpha_top = np.zeros((rows, 1, 1), dtype=np.float32)
        for r in range(min(close_rows, rows)):
            # Gradient: full opacity at top, fading at edge
            if r < close_rows - 2:
                alpha_top[r] = intensity * 0.85
            else:
                alpha_top[r] = intensity * 0.4

        blended = (eye_region.astype(np.float32) * (1 - alpha_top) +
                    eyelid.astype(np.float32) * alpha_top)
        result[eye_y1:eye_y2, eye_x1:eye_x2] = blended.clip(0, 255).astype(np.uint8)

    return result


# ═══════════════════════════════════════════════════════════════════════
# POST-PROCESSING: HEAD MOVEMENT
# ═══════════════════════════════════════════════════════════════════════

def apply_head_movement(frame, frame_idx, fps):
    """Apply subtle head movement using affine transforms.
    Uses multiple sine waves at different frequencies for natural motion."""
    t = frame_idx / fps

    # Multiple overlapping sine waves for organic movement
    rot_angle = (
        HEAD_ROTATION_AMPLITUDE * 0.6 * math.sin(2 * math.pi * t / HEAD_PERIOD) +
        HEAD_ROTATION_AMPLITUDE * 0.3 * math.sin(2 * math.pi * t / (HEAD_PERIOD * 1.7) + 0.5) +
        HEAD_ROTATION_AMPLITUDE * 0.1 * math.sin(2 * math.pi * t / (HEAD_PERIOD * 0.6) + 1.2)
    )

    tx = (
        HEAD_TRANSLATION_X * 0.6 * math.sin(2 * math.pi * t / (HEAD_PERIOD * 1.3) + 0.8) +
        HEAD_TRANSLATION_X * 0.4 * math.sin(2 * math.pi * t / (HEAD_PERIOD * 2.1) + 2.0)
    )

    ty = (
        HEAD_TRANSLATION_Y * 0.5 * math.sin(2 * math.pi * t / (HEAD_PERIOD * 0.9) + 1.5) +
        HEAD_TRANSLATION_Y * 0.3 * math.sin(2 * math.pi * t / (HEAD_PERIOD * 1.6) + 0.3) +
        HEAD_TRANSLATION_Y * 0.2 * math.sin(2 * math.pi * t / (HEAD_PERIOD * 3.0))
    )

    h, w = frame.shape[:2]
    center = (w / 2, h / 2)

    M = cv2.getRotationMatrix2D(center, rot_angle, 1.0)
    M[0, 2] += tx
    M[1, 2] += ty

    return cv2.warpAffine(
        frame, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE
    )


# ═══════════════════════════════════════════════════════════════════════
# POST-PROCESSING: COMBINED PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def post_process_frames(frames, fps=25.0):
    """Apply blinks and head movement to all frames."""
    num_frames = len(frames)
    if num_frames == 0:
        return frames

    blink_schedule = generate_blink_schedule(num_frames, fps)
    processed = []

    for i, frame in enumerate(frames):
        result = frame

        # Apply head movement
        result = apply_head_movement(result, i, fps)

        # Apply blink
        blink_intensity = blink_schedule.get(i, 0)
        if blink_intensity > 0.01:
            result = apply_blink(result, blink_intensity, avatar_face_coords)

        processed.append(result)

    return processed


# ═══════════════════════════════════════════════════════════════════════
# VIDEO ENCODING
# ═══════════════════════════════════════════════════════════════════════

def frames_to_video(frames, fps=25.0):
    """Encode frames to MP4 using OpenCV + ffmpeg for final encoding."""
    if not frames:
        return None

    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp_avi:
        avi_path = tmp_avi.name

    mp4_path = avi_path.replace(".avi", ".mp4")

    try:
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(avi_path, fourcc, fps, (w, h))

        for frame in frames:
            writer.write(frame)
        writer.release()

        # Convert to MP4 with ffmpeg (H.264, web-compatible)
        os.system(
            f"ffmpeg -y -loglevel error -i {avi_path} "
            f"-c:v libx264 -preset ultrafast -crf 23 "
            f"-pix_fmt yuv420p -movflags +faststart "
            f"{mp4_path}"
        )

        if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
            with open(mp4_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        else:
            logger.error("ffmpeg failed to produce MP4")
            return None
    finally:
        for p in [avi_path, mp4_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    """Health check."""
    gpu_mem = "unknown"
    try:
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) / 1024**3
            total = torch.cuda.get_device_properties(0).total_mem / 1024**3
            gpu_mem = f"{allocated:.1f}GB / {total:.1f}GB"
    except Exception:
        pass

    return jsonify({
        "status": "ok",
        "engine": "wav2lip-gan",
        "enhancements": ["eye_blinks", "head_movement"],
        "device": DEVICE,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none",
        "gpu_memory": gpu_mem,
        "model_loaded": wav2lip_model is not None,
        "avatar_loaded": avatar_face is not None,
        "avatar_size": f"{avatar_face.shape[1]}x{avatar_face.shape[0]}" if avatar_face is not None else None,
        "face_detected": avatar_face_coords is not None,
        "blink_config": {
            "interval": f"{BLINK_INTERVAL_MIN}-{BLINK_INTERVAL_MAX}s",
            "duration": f"{BLINK_DURATION}s"
        },
        "head_movement_config": {
            "rotation": f"±{HEAD_ROTATION_AMPLITUDE}°",
            "period": f"{HEAD_PERIOD}s"
        }
    })


@app.route("/generate", methods=["POST"])
def generate():
    """Generate lip-synced video with blinks and head movement.

    POST JSON:
        audio_base64: base64-encoded audio (mp3/wav)
        content_type: audio MIME type (default: audio/mpeg)
        enable_blinks: bool (default: True)
        enable_head_movement: bool (default: True)
        fps: float (default: 25.0)

    Returns JSON:
        video_base64: base64-encoded MP4
        duration: video duration in seconds
        frames: number of frames
        processing_time: seconds
    """
    data = request.get_json()
    if not data or not data.get("audio_base64"):
        return jsonify({"error": "audio_base64 required"}), 400

    enable_blinks = data.get("enable_blinks", True)
    enable_head_movement = data.get("enable_head_movement", True)
    fps = float(data.get("fps", 25.0))

    t_start = time.time()

    # Decode audio to temp file
    audio_bytes = base64.b64decode(data["audio_base64"])
    content_type = data.get("content_type", "audio/mpeg")
    ext = ".mp3" if "mpeg" in content_type else ".wav"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name

    # Convert to wav if needed (Wav2Lip needs wav)
    wav_path = audio_path + chr(95) + chr(49) + chr(54) + chr(107) + chr(46) + chr(119) + chr(97) + chr(118)
    os.system(f'ffmpeg -y -loglevel error -i {audio_path} -ar 16000 -ac 1 {wav_path}')
    if False and ext == ".mp3":
        wav_path = audio_path.replace(".mp3", ".wav")
        os.system(f"ffmpeg -y -loglevel error -i {audio_path} -ar 16000 -ac 1 {wav_path}")

    try:
        with _lock:
            # Step 1: Wav2Lip inference
            t0 = time.time()
            frames = wav2lip_generate(wav_path)
            t_lip = time.time() - t0
            logger.info(f"Wav2Lip: {len(frames)} frames in {t_lip:.2f}s")

            # Step 2: Post-processing
            t0 = time.time()
            if enable_blinks or enable_head_movement:
                if enable_blinks and enable_head_movement:
                    frames = post_process_frames(frames, fps)
                elif enable_blinks:
                    blink_schedule = generate_blink_schedule(len(frames), fps)
                    frames = [
                        apply_blink(f, blink_schedule.get(i, 0), avatar_face_coords)
                        for i, f in enumerate(frames)
                    ]
                elif enable_head_movement:
                    frames = [
                        apply_head_movement(f, i, fps)
                        for i, f in enumerate(frames)
                    ]
            t_post = time.time() - t0
            logger.info(f"Post-processing: {t_post:.2f}s (blinks={enable_blinks}, head={enable_head_movement})")

            # Step 3: Encode to MP4
            t0 = time.time()
            video_b64 = frames_to_video(frames, fps)
            t_encode = time.time() - t0
            logger.info(f"Encoding: {t_encode:.2f}s")

        if not video_b64:
            return jsonify({"error": "Video encoding failed"}), 500

        t_total = time.time() - t_start
        duration = len(frames) / fps

        logger.info(
            f"Complete: {duration:.1f}s video, {len(frames)} frames, "
            f"lip={t_lip:.1f}s post={t_post:.1f}s enc={t_encode:.1f}s total={t_total:.1f}s"
        )

        return jsonify({
            "video_base64": video_b64,
            "duration": round(duration, 2),
            "frames": len(frames),
            "processing_time": round(t_total, 2),
            "timing": {
                "wav2lip": round(t_lip, 2),
                "post_processing": round(t_post, 2),
                "encoding": round(t_encode, 2),
                "total": round(t_total, 2)
            }
        })

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        for p in [audio_path, wav_path]:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except OSError:
                pass


@app.route("/reload-avatar", methods=["POST"])
def reload_avatar():
    """Reload avatar source image (after updating avatar_source.png)."""
    global avatar_face, avatar_face_coords
    try:
        img = cv2.imread(AVATAR_SOURCE)
        if img is None:
            return jsonify({"error": "Failed to read avatar source"}), 500

        results = face_detector.get_detections_for_batch(
            np.array([img])
        )
        if results[0] is not None:
            det = results[0]
            avatar_face = img.copy()
            avatar_face_coords = (
                max(0, int(det[1])),
                min(img.shape[0], int(det[3])),
                max(0, int(det[0])),
                min(img.shape[1], int(det[2]))
            )
            return jsonify({
                "status": "reloaded",
                "size": f"{img.shape[1]}x{img.shape[0]}",
                "face": avatar_face_coords
            })
        else:
            return jsonify({"error": "No face detected in new image"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/source-image")
def source_image():
    """Serve the current avatar source image (for debugging/sync)."""
    if avatar_face is None:
        return jsonify({"error": "No avatar loaded"}), 404
    _, buf = cv2.imencode(".png", avatar_face)
    b64 = base64.b64encode(buf).decode()
    return jsonify({
        "image_base64": b64,
        "size": f"{avatar_face.shape[1]}x{avatar_face.shape[0]}",
        "face_coords": avatar_face_coords
    })


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  ORACLE AVATAR SERVER — Enhanced")
    print(f"  Port: {PORT}")
    print(f"  Device: {DEVICE}")
    print(f"  Wav2Lip: {CHECKPOINT}")
    print(f"  Avatar: {AVATAR_SOURCE}")
    print(f"  Enhancements: eye_blinks, head_movement")
    print(f"{'='*60}\n")

    load_wav2lip()

    if wav2lip_model is None:
        logger.error("Failed to load Wav2Lip model. Exiting.")
        sys.exit(1)

    if avatar_face_coords is None:
        logger.error("No face detected in avatar. Exiting.")
        sys.exit(1)

    logger.info(f"Avatar server ready on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
