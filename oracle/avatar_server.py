"""
ORACLE AVATAR SERVER — GPU-Cached FP16 + Vision Guide
=======================================================
GPU-accelerated Wav2Lip lip-sync with:
  - FP16 inference via ModelRegistry singleton
  - torch.compile(reduce-overhead) fused kernels
  - Pre-cached reference face (detect once, reuse forever)
  - Eye blinks + head movement post-processing
  - Vision guide endpoints (Gemini 2.5 Flash)

Deploy: ~/protocol_pulse/oracle/avatar_server.py
Launch: cd ~/protocol_pulse/oracle && python3 avatar_server.py
"""

import os
import sys
import time
import math
import random
import base64
import logging
import tempfile
import threading
import numpy as np

import cv2
import torch
from flask import Flask, request, jsonify

from model_registry import ModelRegistry, WAV2LIP_DIR, AVATAR_SOURCE

# ─── Config ───────────────────────────────────────────────────────────
PORT = 8200
BATCH_SIZE = 48  # Optimal for RTX 4090
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

# Post-processing config
BLINK_INTERVAL_MIN = 3.0
BLINK_INTERVAL_MAX = 4.0
BLINK_DURATION = 0.15
HEAD_ROTATION_AMPLITUDE = 1.0
HEAD_TRANSLATION_X = 1.5
HEAD_TRANSLATION_Y = 1.0
HEAD_PERIOD = 4.0

# ─── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("avatar_server")

app = Flask(__name__)

# ─── Metrics ──────────────────────────────────────────────────────────
_lock = threading.Lock()
_start_time = time.time()
_request_times = []  # last 100 request times for avg latency


def _record_latency(seconds):
    _request_times.append(seconds)
    if len(_request_times) > 100:
        _request_times.pop(0)


# ═══════════════════════════════════════════════════════════════════════
# WAV2LIP INFERENCE (FP16)
# ═══════════════════════════════════════════════════════════════════════

def wav2lip_generate(audio_path):
    """Run Wav2Lip inference in FP16. Returns list of BGR frames."""
    reg = ModelRegistry.get()
    if reg.wav2lip_model is None or reg.avatar_face is None or reg.avatar_face_coords is None:
        raise RuntimeError("Model or avatar not loaded")

    if WAV2LIP_DIR not in sys.path:
        sys.path.insert(0, WAV2LIP_DIR)
    import audio as wav2lip_audio

    wav = wav2lip_audio.load_wav(audio_path, 16000)
    mel = wav2lip_audio.melspectrogram(wav)
    if mel.shape[1] == 0:
        raise ValueError("Empty audio")

    mel_chunks = []
    mel_step = 16
    i = 0
    while i < mel.shape[1]:
        chunk = mel[:, i:i + mel_step]
        if chunk.shape[1] < mel_step:
            chunk = np.pad(chunk, ((0, 0), (0, mel_step - chunk.shape[1])))
        mel_chunks.append(chunk)
        i += mel_step

    y1, y2, x1, x2 = reg.avatar_face_coords
    face_crop = reg.avatar_face[y1:y2, x1:x2]
    face_resized = cv2.resize(face_crop, (96, 96))
    face_masked = face_resized.copy()
    face_masked[face_resized.shape[0] // 2:, :] = 0

    frames = []
    total_chunks = len(mel_chunks)

    for batch_start in range(0, total_chunks, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_chunks)
        batch_mels = mel_chunks[batch_start:batch_end]

        img_concat = np.concatenate((face_masked, face_resized), axis=2)
        img_batch = np.array([img_concat / 255.0] * len(batch_mels), dtype=np.float32)
        mel_batch = np.array(batch_mels, dtype=np.float32)

        # FP16 tensors → GPU
        img_batch = torch.HalfTensor(img_batch.transpose(0, 3, 1, 2)).to(DEVICE)
        mel_batch = torch.HalfTensor(mel_batch[:, np.newaxis, :, :]).to(DEVICE)

        with torch.no_grad():
            pred = reg.wav2lip_model(mel_batch, img_batch)

        pred = pred.float().cpu().numpy().transpose(0, 2, 3, 1) * 255.0

        for p in pred:
            p_resized = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
            full_frame = reg.avatar_face.copy()
            full_frame[y1:y2, x1:x2] = p_resized
            frames.append(full_frame)

    return frames


# ═══════════════════════════════════════════════════════════════════════
# POST-PROCESSING: EYE BLINKS
# ═══════════════════════════════════════════════════════════════════════

def generate_blink_schedule(num_frames, fps):
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
                progress = abs(offset) / max(blink_half_frames, 1)
                intensity = 0.5 * (1 + math.cos(math.pi * progress))
                blink_frames[frame_idx] = max(blink_frames.get(frame_idx, 0), intensity)
        t += BLINK_DURATION + random.uniform(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
    return blink_frames


def apply_blink(frame, intensity, face_coords):
    if face_coords is None or intensity <= 0.01:
        return frame
    y1, y2, x1, x2 = face_coords
    face_h = y2 - y1
    face_w = x2 - x1
    eye_y1 = y1 + int(face_h * 0.22)
    eye_y2 = y1 + int(face_h * 0.42)
    eye_x1 = x1 + int(face_w * 0.08)
    eye_x2 = x2 - int(face_w * 0.08)
    h, w = frame.shape[:2]
    eye_y1 = max(0, min(eye_y1, h - 1))
    eye_y2 = max(eye_y1 + 1, min(eye_y2, h))
    eye_x1 = max(0, min(eye_x1, w - 1))
    eye_x2 = max(eye_x1 + 1, min(eye_x2, w))
    result = frame.copy()
    eye_region = result[eye_y1:eye_y2, eye_x1:eye_x2].copy()
    skin_sample_y = max(0, eye_y1 - int(face_h * 0.05))
    skin_sample = frame[skin_sample_y:eye_y1, eye_x1:eye_x2]
    if skin_sample.size > 0:
        skin_color = skin_sample.mean(axis=(0, 1)).astype(np.uint8)
    else:
        skin_color = np.array([140, 130, 125], dtype=np.uint8)
    eyelid = np.full_like(eye_region, skin_color)
    rows = eye_region.shape[0]
    close_rows = int(rows * intensity * 0.7)
    if close_rows > 0:
        alpha_top = np.zeros((rows, 1, 1), dtype=np.float32)
        for r in range(min(close_rows, rows)):
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
    t = frame_idx / fps
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
    return cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


# ═══════════════════════════════════════════════════════════════════════
# POST-PROCESSING: COMBINED PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def post_process_frames(frames, fps=25.0):
    reg = ModelRegistry.get()
    num_frames = len(frames)
    if num_frames == 0:
        return frames
    blink_schedule = generate_blink_schedule(num_frames, fps)
    processed = []
    for i, frame in enumerate(frames):
        result = apply_head_movement(frame, i, fps)
        blink_intensity = blink_schedule.get(i, 0)
        if blink_intensity > 0.01:
            result = apply_blink(result, blink_intensity, reg.avatar_face_coords)
        processed.append(result)
    return processed


# ═══════════════════════════════════════════════════════════════════════
# VIDEO ENCODING
# ═══════════════════════════════════════════════════════════════════════

def frames_to_video(frames, fps=25.0):
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
    """Enhanced health check with VRAM, latency, vision status."""
    reg = ModelRegistry.get() if ModelRegistry.is_loaded() else None
    vram = reg.vram_info() if reg else {"available": False}

    # Vision status
    vision_enabled = bool(os.environ.get("GEMINI_API_KEY"))

    avg_latency = round(sum(_request_times) / len(_request_times), 2) if _request_times else None
    uptime = round(time.time() - _start_time, 1)

    return jsonify({
        "status": "ok",
        "engine": "wav2lip-gan-fp16",
        "enhancements": ["eye_blinks", "head_movement", "fp16", "cached_face"],
        "device": DEVICE,
        "model_loaded": reg is not None and reg.wav2lip_model is not None,
        "avatar_loaded": reg is not None and reg.avatar_face is not None,
        "avatar_size": (
            f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}"
            if reg and reg.avatar_face is not None else None
        ),
        "face_detected": reg is not None and reg.avatar_face_coords is not None,
        "vram": vram,
        "vision_enabled": vision_enabled,
        "uptime_sec": uptime,
        "avg_latency_sec": avg_latency,
        "requests_tracked": len(_request_times),
        "blink_config": {
            "interval": f"{BLINK_INTERVAL_MIN}-{BLINK_INTERVAL_MAX}s",
            "duration": f"{BLINK_DURATION}s"
        },
        "head_movement_config": {
            "rotation": f"\u00b1{HEAD_ROTATION_AMPLITUDE}\u00b0",
            "period": f"{HEAD_PERIOD}s"
        }
    })


@app.route("/warmup", methods=["POST"])
def warmup():
    """Generate a tiny test video to warm up torch.compile and CUDA kernels."""
    t0 = time.time()
    reg = ModelRegistry.get()
    if reg.wav2lip_model is None:
        return jsonify({"error": "Model not loaded"}), 500

    # Create a short silent audio (0.5s of silence at 16kHz)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        import wave
        with wave.open(tmp.name, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 8000)  # 0.5s silence
        wav_path = tmp.name

    try:
        with _lock:
            frames = wav2lip_generate(wav_path)
            if frames:
                frames = post_process_frames(frames[:5], 25.0)
        elapsed = time.time() - t0
        logger.info(f"Warmup complete: {len(frames)} frames in {elapsed:.2f}s")
        return jsonify({
            "status": "warmed_up",
            "frames": len(frames),
            "warmup_time": round(elapsed, 2),
            "vram": reg.vram_info(),
        })
    except Exception as e:
        logger.error(f"Warmup error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


@app.route("/generate", methods=["POST"])
def generate():
    """Generate lip-synced video with blinks and head movement (FP16)."""
    data = request.get_json()
    if not data or not data.get("audio_base64"):
        return jsonify({"error": "audio_base64 required"}), 400

    enable_blinks = data.get("enable_blinks", True)
    enable_head_movement = data.get("enable_head_movement", True)
    fps = float(data.get("fps", 25.0))

    t_start = time.time()

    audio_bytes = base64.b64decode(data["audio_base64"])
    content_type = data.get("content_type", "audio/mpeg")
    ext = ".mp3" if "mpeg" in content_type else ".wav"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name

    wav_path = audio_path + "_16k.wav"
    os.system(f'ffmpeg -y -loglevel error -i {audio_path} -ar 16000 -ac 1 {wav_path}')

    try:
        reg = ModelRegistry.get()
        with _lock:
            t0 = time.time()
            frames = wav2lip_generate(wav_path)
            t_lip = time.time() - t0
            logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")

            t0 = time.time()
            if enable_blinks or enable_head_movement:
                if enable_blinks and enable_head_movement:
                    frames = post_process_frames(frames, fps)
                elif enable_blinks:
                    blink_schedule = generate_blink_schedule(len(frames), fps)
                    frames = [
                        apply_blink(f, blink_schedule.get(i, 0), reg.avatar_face_coords)
                        for i, f in enumerate(frames)
                    ]
                elif enable_head_movement:
                    frames = [apply_head_movement(f, i, fps) for i, f in enumerate(frames)]
            t_post = time.time() - t0
            logger.info(f"Post-processing: {t_post:.2f}s")

            t0 = time.time()
            video_b64 = frames_to_video(frames, fps)
            t_encode = time.time() - t0
            logger.info(f"Encoding: {t_encode:.2f}s")

        if not video_b64:
            return jsonify({"error": "Video encoding failed"}), 500

        t_total = time.time() - t_start
        _record_latency(t_total)
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
    """Reload avatar source image via ModelRegistry."""
    reg = ModelRegistry.get()
    if reg.reload_avatar():
        return jsonify({
            "status": "reloaded",
            "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
            "face": reg.avatar_face_coords
        })
    else:
        return jsonify({"error": "No face detected in new image"}), 400


@app.route("/source-image")
def source_image():
    """Serve the current avatar source image."""
    reg = ModelRegistry.get()
    if reg.avatar_face is None:
        return jsonify({"error": "No avatar loaded"}), 404
    _, buf = cv2.imencode(".png", reg.avatar_face)
    b64 = base64.b64encode(buf).decode()
    return jsonify({
        "image_base64": b64,
        "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
        "face_coords": reg.avatar_face_coords
    })


# ═══════════════════════════════════════════════════════════════════════
# VISION GUIDE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/vision/analyze", methods=["POST"])
def vision_analyze():
    """Analyze a Bitcoin hardware image with Gemini 2.5 Flash.

    POST JSON:
        image_base64: base64-encoded image
        mime_type: image MIME type (default: image/jpeg)
        context: optional user question/context
    """
    data = request.get_json()
    if not data or not data.get("image_base64"):
        return jsonify({"error": "image_base64 required"}), 400

    from vision_guide import analyze_image
    result = analyze_image(
        image_b64=data["image_base64"],
        mime_type=data.get("mime_type", "image/jpeg"),
        context=data.get("context", ""),
    )

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route("/vision/guide", methods=["POST"])
def vision_guide():
    """Multi-turn hardware setup guide session.

    POST JSON:
        session_id: optional (creates new if omitted)
        image_base64: optional image for this turn
        mime_type: image MIME type (default: image/jpeg)
        question: text question (used with or without image)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    from vision_guide import GuideSession
    session = GuideSession.get_or_create(data.get("session_id"))

    if data.get("image_base64"):
        result = session.send_image(
            image_b64=data["image_base64"],
            mime_type=data.get("mime_type", "image/jpeg"),
            question=data.get("question", ""),
        )
    elif data.get("question"):
        result = session.send_text(data["question"])
    else:
        return jsonify({"error": "image_base64 or question required"}), 400

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route("/vision/sessions")
def vision_sessions():
    """List active vision guide sessions."""
    from vision_guide import GuideSession
    return jsonify({
        "active_sessions": GuideSession.active_count(),
    })


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  ORACLE AVATAR SERVER — GPU-Cached FP16 + Vision")
    print(f"  Port: {PORT}")
    print(f"  Device: {DEVICE}")
    print(f"  Avatar: {AVATAR_SOURCE}")
    print(f"  Features: FP16, cached_face, eye_blinks, head_movement")
    print(f"  Vision: {'enabled' if os.environ.get('GEMINI_API_KEY') else 'disabled'}")
    print(f"{'='*60}\n")

    # Load all models via registry (FP16 + torch.compile)
    logger.info("Initializing ModelRegistry...")
    reg = ModelRegistry.get()

    if reg.wav2lip_model is None:
        logger.error("Failed to load Wav2Lip model. Exiting.")
        sys.exit(1)

    if reg.avatar_face_coords is None:
        logger.error("No face detected in avatar. Exiting.")
        sys.exit(1)

    logger.info(f"Avatar server ready on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
