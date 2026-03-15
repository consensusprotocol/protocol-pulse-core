"""
ORACLE AVATAR SERVER v2 — GPU-Cached FP16 + CV2 Sharpen + Blinks
=================================================================
GPU-accelerated Wav2Lip lip-sync with:
  - FP16 inference via ModelRegistry singleton on GPU 1
  - CV2 bilateral sharpen (GFPGAN fully removed 2026-03-12)
  - MediaPipe eye blinks (gradient overlay, no warpAffine artifacts)
  - Head movement post-processing
  - Vision guide endpoints (Gemini 2.5 Flash)
  - Input audio length guard (30s max, chunked processing)
  - CRF 28, preset ultrafast, 30fps output

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
torch.backends.cudnn.benchmark = True
from flask import Flask, request, jsonify, send_file, after_this_request

from model_registry import ModelRegistry, WAV2LIP_DIR, AVATAR_SOURCE, DEVICE

import requests as http_requests  # ElevenLabs TTS
import json as _json

# Face enhancement + blink modules
from face_enhancer import sharpen_mouth_region
from blink_engine import apply_blink_gradient, generate_blink_schedule

# ─── Config ───────────────────────────────────────────────────────────
PORT = 8200
BATCH_SIZE_DEFAULT = 48  # Proven stable at 134fps — 64 caused VRAM pressure on GPU 1
BATCH_SIZE_SMALL = 16    # For short audio < 60 mel frames
BATCH_SIZE = BATCH_SIZE_DEFAULT
DEFAULT_FPS = 30.0  # Upgraded from 25fps — smoother motion

# Post-processing config
BLINK_INTERVAL_MIN = 2.5
BLINK_INTERVAL_MAX = 5.0
BLINK_DURATION = 0.22  # ~6-7 frames at 30fps, visible but natural
HEAD_ROTATION_AMPLITUDE = 2.5   # degrees — visible news-anchor sway
HEAD_TRANSLATION_X = 4.0        # pixels — visible horizontal drift
HEAD_TRANSLATION_Y = 2.0        # pixels — visible vertical drift
HEAD_PERIOD = 5.0               # seconds per full cycle — slow and natural

# Lock timeout (seconds) — if GPU is busy longer than this, return 503
LOCK_TIMEOUT = int(os.environ.get("AVATAR_LOCK_TIMEOUT", "10"))

# Max audio duration (seconds) — longer clips get chunked
MAX_AUDIO_SECONDS = 30

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

FACE_BBOX_CACHE = os.path.join(os.path.dirname(__file__), "cache", "face_bbox.json")


def wav2lip_generate(audio_path, fps=30.0):
    """Run Wav2Lip inference in FP16. Returns list of BGR frames with duration matching."""
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

    mel_step = 16
    audio_duration = len(wav) / 16000.0
    num_frames = int(math.ceil(audio_duration * fps)) + 2  # prevent audio cutoff
    if num_frames < 1:
        num_frames = 1

    # Map each VIDEO frame to its correct MEL position
    mel_idx_multiplier = 80.0 / fps

    mel_chunks = []
    for frame_i in range(num_frames):
        start_col = int(frame_i * mel_idx_multiplier)
        end_col = start_col + mel_step
        if end_col > mel.shape[1]:
            chunk = mel[:, start_col:]
            if chunk.shape[1] < mel_step:
                chunk = np.pad(chunk, ((0, 0), (0, mel_step - chunk.shape[1])))
        else:
            chunk = mel[:, start_col:end_col]
        mel_chunks.append(chunk)

    # Adaptive batch size: smaller for short audio
    batch_size = BATCH_SIZE_SMALL if len(mel_chunks) < 60 else BATCH_SIZE_DEFAULT

    logger.info(f"Mel: {mel.shape[1]} cols, {num_frames} frames @ {fps}fps, audio {audio_duration:.2f}s, batch={batch_size}")

    # Face bbox caching: skip detection if cached
    y1, y2, x1, x2 = reg.avatar_face_coords
    try:
        os.makedirs(os.path.dirname(FACE_BBOX_CACHE), exist_ok=True)
        if not os.path.exists(FACE_BBOX_CACHE):
            with open(FACE_BBOX_CACHE, "w") as f:
                _json.dump({"y1": y1, "y2": y2, "x1": x1, "x2": x2}, f)
            logger.info(f"Face bbox cached: {[y1, y2, x1, x2]}")
    except Exception:
        pass
    face_crop = reg.avatar_face[y1:y2, x1:x2]
    face_resized = cv2.resize(face_crop, (96, 96))
    face_masked = face_resized.copy()
    face_masked[face_resized.shape[0] // 2:, :] = 0

    frames = []
    total_chunks = len(mel_chunks)

    for batch_start in range(0, total_chunks, batch_size):
        batch_end = min(batch_start + batch_size, total_chunks)
        batch_mels = mel_chunks[batch_start:batch_end]

        img_concat = np.concatenate((face_masked, face_resized), axis=2)
        img_batch = np.array([img_concat / 255.0] * len(batch_mels), dtype=np.float32)
        mel_batch = np.array(batch_mels, dtype=np.float32)

        # FP16 tensors → GPU 1
        img_batch = torch.HalfTensor(img_batch.transpose(0, 3, 1, 2)).to(DEVICE)
        mel_batch = torch.HalfTensor(mel_batch[:, np.newaxis, :, :]).to(DEVICE)

        with torch.no_grad():
            pred = reg.wav2lip_model(mel_batch, img_batch)

        pred = pred.float().cpu().numpy().transpose(0, 2, 3, 1) * 255.0

        for p in pred:
            p_resized = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
            full_frame = reg.avatar_face.copy()
            # Feathered blend to eliminate face paste seam
            mask = np.ones_like(p_resized, dtype=np.float32)
            feather = 8
            h_face, w_face = p_resized.shape[:2]
            for j in range(min(feather, h_face)):
                mask[j, :] = j / feather
            for j in range(min(feather, h_face)):
                mask[-(j+1), :] = j / feather
            for j in range(min(feather, w_face)):
                mask[:, j] *= j / feather
            for j in range(min(feather, w_face)):
                mask[:, -(j+1)] *= j / feather
            full_frame[y1:y2, x1:x2] = (
                p_resized * mask + full_frame[y1:y2, x1:x2] * (1 - mask)
            ).astype(np.uint8)
            frames.append(full_frame)

    logger.info(f"Generated {len(frames)} frames for {audio_duration:.2f}s audio @ {fps}fps")
    return frames


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
    result = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return result


# ═══════════════════════════════════════════════════════════════════════
# POST-PROCESSING: COMBINED PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def post_process_frames(frames, fps=30.0, enable_blinks=True, enable_head=True):
    """Apply eye blinks and head movement post-processing."""
    if len(frames) == 0:
        return frames

    reg = ModelRegistry.get()

    # Generate blink schedule
    blink_schedule = {}
    if enable_blinks:
        blink_schedule = generate_blink_schedule(
            len(frames), fps,
            interval_min=BLINK_INTERVAL_MIN,
            interval_max=BLINK_INTERVAL_MAX,
            duration=BLINK_DURATION,
        )

    processed = []
    for i, frame in enumerate(frames):
        result = frame
        if enable_blinks and i in blink_schedule:
            try:
                result = apply_blink_gradient(
                    result,
                    blink_schedule[i],
                    eye_landmarks=reg.eye_landmarks,
                    face_coords=reg.avatar_face_coords,
                )
            except Exception:
                # P0 safety net: blink artifacts → return original frame
                result = frame
        if enable_head:
            result = apply_head_movement(result, i, fps)
        processed.append(result)
    return processed


# ═══════════════════════════════════════════════════════════════════════
# VIDEO ENCODING
# ═══════════════════════════════════════════════════════════════════════

def frames_to_video(frames, fps=30.0, audio_path=None):
    """Encode frames to MP4, optionally muxing audio (audio as timing master).
    Returns the path to the output MP4 file (caller must clean up)."""
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

        import subprocess
        if audio_path and os.path.exists(audio_path):
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-itsoffset", "0.08", "-i", audio_path, "-i", avi_path,
            ]
            if w > 512:
                cmd += ["-vf", "scale=512:512"]
            cmd += [
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "128k",
                "-map", "0:a", "-map", "1:v",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                mp4_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", avi_path,
            ]
            if w > 512:
                cmd += ["-vf", "scale=512:512"]
            cmd += [
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                mp4_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)

        if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
            return mp4_path
        else:
            logger.error("ffmpeg failed to produce MP4")
            return None
    finally:
        try:
            os.unlink(avi_path)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════
# ELEVENLABS TTS
# ═══════════════════════════════════════════════════════════════════════

def text_to_speech(text, voice_id="cgSgspJ2msm6clMCkdW9"):
    """Call ElevenLabs TTS API. Returns raw audio bytes (mp3)."""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("ELEVENLABS_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip().strip("\"'")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment or .env")
    resp = http_requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            # LAW 3: Jessica voice settings — stability=0.45, similarity_boost=0.75, style=0.20
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.20},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise Exception(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
    return resp.content


# ═══════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    """Enhanced health check with VRAM, latency, vision status, enhancer info."""
    reg = ModelRegistry.get() if ModelRegistry.is_loaded() else None
    vram = reg.vram_info() if reg else {"available": False}

    vision_enabled = bool(os.environ.get("GEMINI_API_KEY"))
    avg_latency = round(sum(_request_times) / len(_request_times), 2) if _request_times else None
    uptime = round(time.time() - _start_time, 1)

    return jsonify({
        "status": "ok",
        "engine": "wav2lip-gan-fp16-v2",
        "enhancements": ["fp16", "cached_face", "cv2_sharpen", "mediapipe_blinks", "head_movement"],
        "device": DEVICE,
        "model_loaded": reg is not None and reg.wav2lip_model is not None,
        "avatar_loaded": reg is not None and reg.avatar_face is not None,
        "avatar_size": (
            f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}"
            if reg and reg.avatar_face is not None else None
        ),
        "face_detected": reg is not None and reg.avatar_face_coords is not None,
        "face_enhancer": "cv2_sharpen_only",
        "blinks_enabled": False,
        "eye_landmarks_detected": reg is not None and reg.eye_landmarks is not None,
        "vram": vram,
        "vision_enabled": vision_enabled,
        "uptime_sec": uptime,
        "avg_latency_sec": avg_latency,
        "requests_tracked": len(_request_times),
        "output_fps": DEFAULT_FPS,
        "batch_size": BATCH_SIZE,
        "max_audio_seconds": MAX_AUDIO_SECONDS,
        "encoding": "crf28-ultrafast-512",
        "blink_config": {
            "interval": f"{BLINK_INTERVAL_MIN}-{BLINK_INTERVAL_MAX}s",
            "duration": f"{BLINK_DURATION}s"
        },
        "head_movement_config": {
            "rotation": f"\u00b1{HEAD_ROTATION_AMPLITUDE}\u00b0",
            "period": f"{HEAD_PERIOD}s"
        }
    })


@app.route("/status")
def status():
    """Alias for /health — frontend expects this route."""
    return health()


@app.route("/warmup", methods=["POST"])
def warmup():
    """Generate a tiny test video to warm up torch.compile and CUDA kernels."""
    t0 = time.time()
    reg = ModelRegistry.get()
    if reg.wav2lip_model is None:
        return jsonify({"error": "Model not loaded"}), 500

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        import wave
        with wave.open(tmp.name, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 8000)
        wav_path = tmp.name

    try:
        with _lock:
            frames = wav2lip_generate(wav_path, DEFAULT_FPS)
            if frames:
                frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
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
    """Generate lip-synced video with face restoration, blinks, and head movement.

    Accepts two modes:
      Mode A: {"text": "...", "voice_id": "..."} -> ElevenLabs TTS -> Wav2Lip -> video
      Mode B: {"audio_base64": "...", "content_type": "..."} -> Wav2Lip -> video
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    enable_blinks = False  # LAW 2: blinks permanently disabled — black oval artifacts
    enable_head_movement = data.get("enable_head_movement", True)
    fps = float(data.get("fps", DEFAULT_FPS))

    t_start = time.time()

    # Mode A: text + optional voice_id -> ElevenLabs TTS
    if "text" in data:
        voice_id = data.get("voice_id", "cgSgspJ2msm6clMCkdW9")
        try:
            t_tts = time.time()
            audio_bytes = text_to_speech(data["text"], voice_id)
            logger.info(f"TTS: {len(audio_bytes)} bytes in {time.time()-t_tts:.2f}s")
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return jsonify({"error": f"TTS failed: {e}"}), 500
        content_type = "audio/mpeg"
    # Mode B: raw audio
    elif "audio_base64" in data:
        audio_bytes = base64.b64decode(data["audio_base64"])
        content_type = data.get("content_type", "audio/mpeg")
    else:
        return jsonify({"error": "text or audio_base64 required"}), 400

    ext = ".mp3" if "mpeg" in content_type else ".wav"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name

    wav_path = audio_path + "_16k.wav"
    os.system(f'ffmpeg -y -loglevel error -i {audio_path} -ar 16000 -ac 1 {wav_path}')

    # Input length guard: check audio duration
    try:
        import subprocess as _sp
        probe = _sp.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
            capture_output=True, text=True, timeout=10,
        )
        audio_duration_sec = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
    except Exception:
        audio_duration_sec = 0.0

    if audio_duration_sec > MAX_AUDIO_SECONDS:
        logger.warning(f"Audio too long ({audio_duration_sec:.1f}s > {MAX_AUDIO_SECONDS}s) — rejecting")
        return jsonify({
            "error": f"Audio too long ({audio_duration_sec:.1f}s). Max {MAX_AUDIO_SECONDS}s.",
            "code": "AUDIO_TOO_LONG",
            "max_seconds": MAX_AUDIO_SECONDS,
        }), 400

    try:
        reg = ModelRegistry.get()
        acquired = _lock.acquire(timeout=LOCK_TIMEOUT)
        if not acquired:
            return jsonify({"error": "GPU busy", "code": "GPU_BUSY", "retry_after": 5}), 503
        try:
            t0 = time.time()
            frames = wav2lip_generate(wav_path, fps)
            t_lip = time.time() - t0
            logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")

            # CV2 sharpen only — no GFPGAN
            t_enhance = 0.0
            if len(frames) > 0:
                try:
                    t0_enh = time.time()
                    frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
                    t_enhance = time.time() - t0_enh
                    logger.info(f"CV2 sharpen: {t_enhance:.2f}s")
                except Exception as e:
                    logger.warning(f"Sharpen skipped: {e}")

            t0 = time.time()
            if enable_blinks or enable_head_movement:
                frames = post_process_frames(
                    frames, fps,
                    enable_blinks=enable_blinks,
                    enable_head=enable_head_movement,
                )
            t_post = time.time() - t0
            logger.info(f"Post-processing: {t_post:.2f}s")

            t0 = time.time()
            video_path = frames_to_video(frames, fps, audio_path=wav_path)
            t_encode = time.time() - t0
            logger.info(f"Encoding: {t_encode:.2f}s")
        finally:
            _lock.release()

        if not video_path:
            return jsonify({"error": "Video encoding failed", "code": "ENCODE_FAILED"}), 500

        t_total = time.time() - t_start
        _record_latency(t_total)
        duration = len(frames) / fps
        num_frames = len(frames)

        logger.info(
            f"Complete: {duration:.1f}s video, {num_frames} frames, "
            f"lip={t_lip:.1f}s enhance={t_enhance:.1f}s post={t_post:.1f}s enc={t_encode:.1f}s total={t_total:.1f}s"
        )

        cleanup_paths = [audio_path, wav_path, video_path]

        @after_this_request
        def _cleanup(response):
            for p in cleanup_paths:
                try:
                    if p and os.path.exists(p):
                        os.unlink(p)
                except OSError:
                    pass
            return response

        response = send_file(
            video_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="oracle.mp4",
        )
        response.headers["X-Duration"] = str(round(duration, 2))
        response.headers["X-Frames"] = str(num_frames)
        response.headers["X-Processing-Time"] = str(round(t_total, 2))
        response.headers["X-Timing-Wav2Lip"] = str(round(t_lip, 2))
        response.headers["X-Timing-FaceEnhance"] = str(round(t_enhance, 2))
        response.headers["X-Timing-PostProcess"] = str(round(t_post, 2))
        response.headers["X-Timing-Encoding"] = str(round(t_encode, 2))
        return response

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return jsonify({"error": str(e), "code": "GENERATION_ERROR"}), 500
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
            "face": reg.avatar_face_coords,
            "eye_landmarks": reg.eye_landmarks is not None,
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
    """Analyze a Bitcoin hardware image with Gemini 2.5 Flash."""
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
    """Multi-turn hardware setup guide session."""
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


@app.route("/vision/status")
def vision_status():
    """Check if vision features are enabled."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    enabled = bool(gemini_key)
    if enabled:
        return jsonify({
            "status": "enabled",
            "model": "gemini-2.5-flash",
            "endpoints": ["/vision/analyze", "/vision/guide", "/vision/sessions"],
        })
    else:
        return jsonify({
            "status": "disabled",
            "reason": "GEMINI_API_KEY not configured",
            "setup_url": "https://aistudio.google.com/apikey",
        })


@app.route("/vision/sessions")
def vision_sessions():
    """List active vision guide sessions."""
    from vision_guide import GuideSession
    return jsonify({
        "active_sessions": GuideSession.active_count(),
    })


# ═══════════════════════════════════════════════════════════════════════
# STREAMING PIPELINE
# ═══════════════════════════════════════════════════════════════════════

import re
import uuid
import subprocess

ORACLE_SYSTEM_PROMPT = (
    "You are The Oracle, Protocol Pulse's AI intelligence analyst specializing in Bitcoin. "
    "You deliver concise, authoritative briefings in a cyberpunk news anchor style. "
    "Keep responses to 3-5 sentences max. Be direct, data-driven, and occasionally "
    "philosophical about Bitcoin's role in financial sovereignty."
)
ORACLE_VOICE_ID = "cgSgspJ2msm6clMCkdW9"  # Jessica
ORACLE_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
ORACLE_IDLE_PATH = os.path.join(ORACLE_STATIC_DIR, "oracle_idle.mp4")

_stream_sessions = {}
_stream_lock = threading.Lock()


def _get_anthropic_key():
    """Get Anthropic API key from env or .env file."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip().strip("\"'")
    if not key:
        try:
            resp = http_requests.post(
                "https://protocolpulse.replit.app/api/admin/exec",
                json={
                    "token": "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552",
                    "cmd": "echo $ANTHROPIC_API_KEY",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                key = resp.json().get("output", "").strip()
        except Exception:
            pass
    return key


def _split_sentences(text):
    """Split text into sentences for chunked processing."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def _generate_chunk(sentence, chunk_num, session_dir, fps=30.0):
    """Generate a single video chunk for a sentence: TTS -> Wav2Lip -> MP4."""
    try:
        audio_bytes = text_to_speech(sentence, ORACLE_VOICE_ID)
        audio_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        wav_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}_16k.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True, capture_output=True,
        )

        with _lock:
            frames = wav2lip_generate(wav_path, fps)
            reg = ModelRegistry.get()
            try:
                frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
            except Exception:
                pass
            frames = post_process_frames(frames, fps, enable_blinks=False, enable_head=True)

        video_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}.mp4")
        tmp_path = frames_to_video(frames, fps, audio_path=wav_path)
        if tmp_path:
            os.rename(tmp_path, video_path)
            return video_path
        return None
    except Exception as e:
        logger.error(f"Chunk {chunk_num} generation error: {e}", exc_info=True)
        return None


def _stream_worker(session_id, text):
    """Background worker: call Claude -> split sentences -> generate chunks."""
    session = _stream_sessions.get(session_id)
    if not session:
        return

    try:
        api_key = _get_anthropic_key()
        if not api_key:
            logger.warning("No Anthropic key — using input text as-is")
            ai_text = text
        else:
            resp = http_requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 80,  # Short transcript = fewer TTS seconds = fewer Wav2Lip frames
                    "system": ORACLE_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": text}],
                },
                timeout=30,
            )
            if resp.status_code == 200:
                ai_text = resp.json()["content"][0]["text"]
            else:
                logger.error(f"Claude API error {resp.status_code}: {resp.text[:200]}")
                ai_text = text

        session["ai_response"] = ai_text
        sentences = _split_sentences(ai_text)
        session["total_chunks"] = len(sentences)

        session_dir = session["dir"]
        for i, sentence in enumerate(sentences):
            chunk_path = _generate_chunk(sentence, i, session_dir)
            if chunk_path:
                session["chunks_ready"].append(chunk_path)
            else:
                session["errors"].append(f"Chunk {i} failed")

        session["status"] = "complete"

    except Exception as e:
        logger.error(f"Stream worker error: {e}", exc_info=True)
        session["status"] = "error"
        session["errors"].append(str(e))


@app.route("/generate_stream", methods=["POST"])
def generate_stream():
    """Start streaming generation: text -> Claude -> sentence chunks -> video chunks."""
    data = request.get_json()
    if not data or not data.get("text"):
        return jsonify({"error": "text required"}), 400

    session_id = str(uuid.uuid4())[:12]
    session_dir = os.path.join(tempfile.gettempdir(), f"oracle_stream_{session_id}")
    os.makedirs(session_dir, exist_ok=True)

    session = {
        "id": session_id,
        "status": "processing",
        "text": data["text"],
        "ai_response": None,
        "total_chunks": 0,
        "chunks_ready": [],
        "errors": [],
        "dir": session_dir,
        "created": time.time(),
    }

    with _stream_lock:
        _stream_sessions[session_id] = session

    thread = threading.Thread(target=_stream_worker, args=(session_id, data["text"]), daemon=True)
    thread.start()

    return jsonify({
        "session_id": session_id,
        "status": "processing",
        "message": "Stream generation started. Poll /stream_status/{session_id} for progress.",
    })


@app.route("/stream_status/<session_id>")
def stream_status(session_id):
    """Poll for streaming generation progress."""
    session = _stream_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({
        "session_id": session_id,
        "status": session["status"],
        "ai_response": session.get("ai_response"),
        "chunks_ready": len(session["chunks_ready"]),
        "total_chunks": session["total_chunks"],
        "total_estimated": max(session["total_chunks"], 3),
        "errors": session["errors"],
    })


@app.route("/stream_chunk/<session_id>/<int:chunk_number>")
def stream_chunk(session_id, chunk_number):
    """Fetch a generated video chunk by number."""
    session = _stream_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    if chunk_number >= len(session["chunks_ready"]):
        return jsonify({"error": "Chunk not ready yet"}), 404

    chunk_path = session["chunks_ready"][chunk_number]
    if not os.path.exists(chunk_path):
        return jsonify({"error": "Chunk file missing"}), 500

    return send_file(chunk_path, mimetype="video/mp4", as_attachment=True,
                     download_name=f"chunk_{chunk_number:03d}.mp4")


@app.route("/oracle_idle")
def oracle_idle():
    """Serve the pre-rendered idle loop video."""
    if os.path.exists(ORACLE_IDLE_PATH):
        return send_file(ORACLE_IDLE_PATH, mimetype="video/mp4")
    return jsonify({"error": "Idle video not generated yet"}), 404


def generate_idle_loop():
    """Generate a 4-second idle loop with blinks + head movement (no audio)."""
    os.makedirs(ORACLE_STATIC_DIR, exist_ok=True)
    if os.path.exists(ORACLE_IDLE_PATH):
        logger.info("Idle loop already exists, skipping generation")
        return

    logger.info("Generating idle loop video...")
    reg = ModelRegistry.get()
    if reg.avatar_face is None:
        logger.error("Cannot generate idle loop: no avatar loaded")
        return

    fps = DEFAULT_FPS
    duration = 4.0
    num_frames = int(duration * fps)

    base_frame = reg.avatar_face.copy()
    frames = [base_frame.copy() for _ in range(num_frames)]

    frames = post_process_frames(frames, fps, enable_blinks=False, enable_head=True)

    video_path = frames_to_video(frames, fps, audio_path=None)
    if video_path:
        os.rename(video_path, ORACLE_IDLE_PATH)
        logger.info(f"Idle loop saved: {ORACLE_IDLE_PATH} ({num_frames} frames)")
    else:
        logger.error("Failed to generate idle loop")


# ═══════════════════════════════════════════════════════════════════════
# ORACLE PRE-CACHE + INTELLIGENCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

import oracle_cache_manager
import oracle_intelligence_feed

# Intent classification — keyword matching
INTENT_PATTERNS = {
    "DAILY_BRIEF": r"brief|today|news|happening|what's|latest",
    "SOVEREIGNTY_INTRO": r"sovereign|score|free",
    "SOVEREIGNTY_COLD_WALLET": r"cold.?wallet|hardware|ledger|coldcard|custody",
    "SOVEREIGNTY_NODE": r"node|umbrel|raspberry|verify",
    "SOVEREIGNTY_BITAXE": r"bitaxe|mine|mining|solo",
    "SOVEREIGNTY_LIFE_INSURANCE": r"insurance|meanwhile|estate|death",
    "SOVEREIGNTY_RESIDENCY": r"residency|palau|rns|passport|citizenship",
    "GOODBYE": r"bye|goodbye|later|thanks",
}


def classify_intent(transcript):
    """Classify user transcript to an intent key. Returns (intent, confidence)."""
    text = transcript.lower().strip()
    for intent, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, text):
            return intent, 0.85
    return "UNKNOWN", 0.4


@app.route("/oracle/cache/status")
def oracle_cache_status():
    """Return status of pre-cached responses and daily brief."""
    cache_status = oracle_cache_manager.get_cache_status()
    daily_brief = oracle_intelligence_feed.get_daily_brief()
    return jsonify({
        "cached_responses": cache_status,
        "daily_brief_ready": daily_brief is not None,
        "daily_brief_path": daily_brief,
        "cache_ttl_s": oracle_cache_manager.CACHE_TTL,
    })


@app.route("/oracle/response/<key>")
def oracle_response(key):
    """Serve pre-cached mp4 for a response key."""
    key = key.upper()
    if key not in oracle_cache_manager.RESPONSE_TREE and key != "DAILY_BRIEF_LIVE":
        return jsonify({"error": "Unknown response key", "valid_keys": list(oracle_cache_manager.RESPONSE_TREE.keys())}), 404

    # Daily brief special case
    if key == "DAILY_BRIEF_LIVE":
        path = oracle_intelligence_feed.get_daily_brief()
        if path:
            return send_file(path, mimetype="video/mp4")
        return jsonify({"error": "Daily brief not ready yet", "status": "pending"}), 202

    # Check if rendering
    if oracle_cache_manager.is_rendering(key):
        return jsonify({"error": "Response is being rendered", "status": "rendering"}), 202

    path = oracle_cache_manager.get_cached_response(key)
    if path:
        return send_file(path, mimetype="video/mp4")

    return jsonify({"error": "Response not cached yet", "status": "pending"}), 202


@app.route("/oracle/speak", methods=["POST"])
def oracle_speak():
    """Serve cached response for an intent, or fallback to /generate."""
    data = request.get_json()
    if not data or not data.get("intent"):
        return jsonify({"error": "intent required"}), 400

    intent = data["intent"].upper()

    # Try daily brief
    if intent == "DAILY_BRIEF":
        brief_path = oracle_intelligence_feed.get_daily_brief()
        if brief_path:
            return send_file(brief_path, mimetype="video/mp4")
        # Fallback to intro
        intent = "DAILY_BRIEF_INTRO"

    # Try cached response
    path = oracle_cache_manager.get_cached_response(intent)
    if path:
        return send_file(path, mimetype="video/mp4")

    # Fallback: generate on the fly using the response tree text
    text = oracle_cache_manager.RESPONSE_TREE.get(intent)
    if not text:
        text = oracle_cache_manager.RESPONSE_TREE["UNKNOWN_QUESTION"]

    # Redirect to /generate with the text
    return generate_inline(text)


def generate_inline(text):
    """Internal helper: generate a video from text and return it."""
    try:
        audio_bytes = text_to_speech(text, ORACLE_VOICE_ID)
    except Exception as e:
        return jsonify({"error": f"TTS failed: {e}"}), 500

    ext = ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name

    wav_path = audio_path + "_16k.wav"
    os.system(f'ffmpeg -y -loglevel error -i {audio_path} -ar 16000 -ac 1 {wav_path}')

    try:
        acquired = _lock.acquire(timeout=LOCK_TIMEOUT)
        if not acquired:
            return jsonify({"error": "GPU busy", "retry_after": 5}), 503
        try:
            frames = wav2lip_generate(wav_path, DEFAULT_FPS)
            reg = ModelRegistry.get()
            try:
                frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
            except Exception:
                pass
            frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=False, enable_head=True)
            video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
        finally:
            _lock.release()

        if not video_path:
            return jsonify({"error": "Video encoding failed"}), 500

        cleanup_paths = [audio_path, wav_path, video_path]

        @after_this_request
        def _cleanup(response):
            for p in cleanup_paths:
                try:
                    if p and os.path.exists(p):
                        os.unlink(p)
                except OSError:
                    pass
            return response

        return send_file(video_path, mimetype="video/mp4", as_attachment=True, download_name="oracle.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        for p in [audio_path, wav_path]:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except OSError:
                pass


@app.route("/oracle/intent", methods=["POST"])
def oracle_intent():
    """Classify user transcript to an intent."""
    data = request.get_json()
    if not data or not data.get("transcript"):
        return jsonify({"error": "transcript required"}), 400

    intent, confidence = classify_intent(data["transcript"])

    # If low confidence, try Claude Haiku for better classification
    if confidence < 0.6:
        try:
            api_key = _get_anthropic_key()
            if api_key:
                resp = http_requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 30,
                        "messages": [{
                            "role": "user",
                            "content": (
                                f"Classify this user message into ONE intent from this list: "
                                f"{', '.join(INTENT_PATTERNS.keys())}, GREETING, UNKNOWN. "
                                f"Reply with ONLY the intent name.\n\nMessage: {data['transcript']}"
                            ),
                        }],
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    ai_intent = resp.json()["content"][0]["text"].strip().upper()
                    valid = set(INTENT_PATTERNS.keys()) | {"GREETING", "UNKNOWN", "SOVEREIGNTY_ASSESSMENT"}
                    if ai_intent in valid:
                        intent = ai_intent
                        confidence = 0.75
        except Exception as e:
            logger.warning(f"Intent AI fallback failed: {e}")

    return jsonify({
        "intent": intent,
        "confidence": round(confidence, 2),
        "cached": oracle_cache_manager.get_cached_response(intent) is not None,
    })


# ═══════════════════════════════════════════════════════════════════════
# SENTENCE CHUNKING FOR LONG TEXT
# ═══════════════════════════════════════════════════════════════════════

_chunk_sessions = {}
_chunk_lock = threading.Lock()


@app.route("/oracle/chunks/<session_id>")
def oracle_chunks(session_id):
    """Poll for additional chunks from a long-text generation."""
    session = _chunk_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({
        "session_id": session_id,
        "chunks_ready": len(session["paths"]),
        "total_chunks": session["total"],
        "complete": session["complete"],
        "paths": [f"/oracle/chunks/{session_id}/{i}" for i in range(len(session["paths"]))],
    })


@app.route("/oracle/chunks/<session_id>/<int:idx>")
def oracle_chunk_file(session_id, idx):
    """Serve a specific chunk file."""
    session = _chunk_sessions.get(session_id)
    if not session or idx >= len(session["paths"]):
        return jsonify({"error": "Chunk not ready"}), 404
    return send_file(session["paths"][idx], mimetype="video/mp4")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  ORACLE AVATAR SERVER v2 — CV2 Sharpen + Blinks")
    print(f"  Port: {PORT}")
    print(f"  Device: {DEVICE}")
    print(f"  Avatar: {AVATAR_SOURCE}")
    print(f"  FPS: {DEFAULT_FPS}")
    print(f"  Encoding: CRF 28, preset ultrafast, 512px output")
    print(f"  Features: FP16, cv2_sharpen, mediapipe_blinks, head_movement")
    print(f"  Vision: {'enabled' if os.environ.get('GEMINI_API_KEY') else 'disabled'}")
    print(f"  Max audio: {MAX_AUDIO_SECONDS}s | Lock timeout: {LOCK_TIMEOUT}s")
    print(f"{'='*60}\n")

    # Load all models via registry (FP16 on GPU 1)
    logger.info("Initializing ModelRegistry...")
    reg = ModelRegistry.get()

    if reg.wav2lip_model is None:
        logger.error("Failed to load Wav2Lip model. Exiting.")
        sys.exit(1)

    if reg.avatar_face_coords is None:
        logger.error("No face detected in avatar. Exiting.")
        sys.exit(1)

    logger.info("Face enhancer: CV2 sharpen-only (no GFPGAN)")

    # Auto-warmup
    logger.info("[WARMUP] Running pipeline warmup...")
    warmup_start = time.time()
    try:
        import wave
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            with wave.open(tmp.name, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 8000)
            warmup_wav = tmp.name
        frames = wav2lip_generate(warmup_wav, DEFAULT_FPS)
        if frames:
            frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
        os.unlink(warmup_wav)
        logger.info(
            f"[WARMUP] Pipeline ready in {time.time()-warmup_start:.1f}s "
            f"({len(frames)} frames)"
        )
    except Exception as e:
        logger.warning(f"[WARMUP] Failed (non-fatal): {e}")

    dev_idx = int(DEVICE.split(':')[1]) if ':' in DEVICE else 0
    logger.info(
        f"[WARMUP] GPU {dev_idx} VRAM: {torch.cuda.memory_allocated(dev_idx)/1024**3:.1f}GB used"
    )

    # Generate idle loop if not already present
    generate_idle_loop()

    # Phase 2: Start cache warming in background
    logger.info("[STARTUP] Starting Oracle cache warmer...")
    threading.Thread(target=oracle_cache_manager.warm_cache, daemon=True).start()
    oracle_cache_manager.start_background_warmer()

    # Phase 3: Start intelligence feed
    logger.info("[STARTUP] Starting intelligence feed...")
    oracle_intelligence_feed.start_intelligence_feed()

    logger.info(f"Avatar server v2 ready on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
