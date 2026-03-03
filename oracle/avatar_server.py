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
from flask import Flask, request, jsonify, send_file, after_this_request

from model_registry import ModelRegistry, WAV2LIP_DIR, AVATAR_SOURCE

import requests as http_requests  # ElevenLabs TTS

# ─── Config ───────────────────────────────────────────────────────────
PORT = 8200
BATCH_SIZE = 48  # Optimal for RTX 4090
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

# Post-processing config
BLINK_INTERVAL_MIN = 2.5
BLINK_INTERVAL_MAX = 5.0
BLINK_DURATION = 0.22  # ~5 frames at 25fps, visible but natural
HEAD_ROTATION_AMPLITUDE = 2.5   # degrees — visible news-anchor sway
HEAD_TRANSLATION_X = 4.0        # pixels — visible horizontal drift
HEAD_TRANSLATION_Y = 2.0        # pixels — visible vertical drift
HEAD_PERIOD = 5.0               # seconds per full cycle — slow and natural

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

def wav2lip_generate(audio_path, fps=25.0):
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
    num_frames = int(__import__('math').ceil(audio_duration * fps)) + 2  # FIXED: prevent audio cutoff
    if num_frames < 1:
        num_frames = 1

    # Map each VIDEO frame to its correct MEL position
    # Mel has 80 columns per second of audio (16kHz / hop_size 200)
    mel_idx_multiplier = 80.0 / fps  # ~3.2 for 25fps

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

    logger.info(f"Mel: {mel.shape[1]} cols, {num_frames} frames @ {fps}fps, audio {audio_duration:.2f}s")

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
            # Feathered blend to eliminate face paste seam
            mask = np.ones_like(p_resized, dtype=np.float32)
            feather = 8  # pixels of blend
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
    """DISABLED: Was causing rectangular/oval artifacts over eyes."""
    return frame  # No-op — blink effect permanently disabled


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
    # Subtle breathing: slight scale oscillation (~0.4%) at 1.5s period
    breath_scale = 1.0  # Disabled breathing: causes micro-jitter
    h, w = frame.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, rot_angle, breath_scale)
    M[0, 2] += tx
    M[1, 2] += ty
    result = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    # Subtle ambient light variation — additive for uniform effect on dark backgrounds
    ambient_add = 0  # Disabled: looked unnatural
    ambient_mul = 1.0  # Disabled: looked unnatural
    result = np.clip(result.astype(np.float32) * ambient_mul + ambient_add, 0, 255).astype(np.uint8)
    return result


# ═══════════════════════════════════════════════════════════════════════
# POST-PROCESSING: COMBINED PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def post_process_frames(frames, fps=25.0, enable_blinks=False, enable_head=True):
    """Apply eye blinks and head movement post-processing."""
    if len(frames) == 0:
        return frames

    reg = ModelRegistry.get()
    blink_schedule = {}
    if False:  # BLINKS PERMANENTLY DISABLED
        blink_schedule = generate_blink_schedule(len(frames), fps)

    processed = []
    for i, frame in enumerate(frames):
        result = frame
        if enable_blinks and i in blink_schedule:
            result = apply_blink(result, blink_schedule[i], reg.avatar_face_coords)
        if enable_head:
            result = apply_head_movement(result, i, fps)
        processed.append(result)
    return processed


# ═══════════════════════════════════════════════════════════════════════
# VIDEO ENCODING
# ═══════════════════════════════════════════════════════════════════════

def frames_to_video(frames, fps=25.0, audio_path=None):
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

        if audio_path and os.path.exists(audio_path):
            # Mux with audio as timing master
            import subprocess
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-itsoffset", "0.08", "-i", audio_path, "-i", avi_path,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "128k",
                "-map", "0:a", "-map", "1:v", # "-shortest",  # REMOVED: was clipping final audio
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                mp4_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            # Video only (warmup, etc.)
            os.system(
                f"ffmpeg -y -loglevel error -i {avi_path} "
                f"-c:v libx264 -preset ultrafast -crf 23 "
                f"-pix_fmt yuv420p -movflags +faststart "
                f"{mp4_path}"
            )

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
            "voice_settings": {"stability": 0.6, "similarity_boost": 0.85},
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
        "enhancements": ["fp16", "cached_face", "head_movement"],
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
                frames = post_process_frames(frames[:5], 25.0, enable_blinks=False, enable_head=True)
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
    """Generate lip-synced video with blinks and head movement (FP16).

    Accepts two modes:
      Mode A: {"text": "...", "voice_id": "..."} → ElevenLabs TTS → Wav2Lip → video
      Mode B: {"audio_base64": "...", "content_type": "..."} → Wav2Lip → video
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    enable_blinks = data.get("enable_blinks", False)
    enable_head_movement = data.get("enable_head_movement", True)  # Re-enabled with sync offset
    fps = float(data.get("fps", 25.0))

    t_start = time.time()

    # Mode A: text + optional voice_id → ElevenLabs TTS
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

    try:
        reg = ModelRegistry.get()
        with _lock:
            t0 = time.time()
            frames = wav2lip_generate(wav_path, fps)
            t_lip = time.time() - t0
            logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")

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

        if not video_path:
            return jsonify({"error": "Video encoding failed"}), 500

        t_total = time.time() - t_start
        _record_latency(t_total)
        duration = len(frames) / fps
        num_frames = len(frames)

        logger.info(
            f"Complete: {duration:.1f}s video, {num_frames} frames, "
            f"lip={t_lip:.1f}s post={t_post:.1f}s enc={t_encode:.1f}s total={t_total:.1f}s"
        )

        # Clean up all temp files after response is sent
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
        response.headers["X-Timing-PostProcess"] = str(round(t_post, 2))
        response.headers["X-Timing-Encoding"] = str(round(t_encode, 2))
        return response

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        # Fallback cleanup for error paths (after_this_request handles success path)
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

# In-memory session store for streaming
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
        # Try fetching from Replit relay
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


def _generate_chunk(sentence, chunk_num, session_dir, fps=25.0):
    """Generate a single video chunk for a sentence: TTS → Wav2Lip → MP4."""
    try:
        # TTS
        audio_bytes = text_to_speech(sentence, ORACLE_VOICE_ID)
        audio_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # Convert to wav
        wav_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}_16k.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True, capture_output=True,
        )

        # Wav2Lip
        with _lock:
            frames = wav2lip_generate(wav_path, fps)
            frames = post_process_frames(frames, fps, enable_blinks=False, enable_head=True)

        # Encode
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
    """Background worker: call Claude → split sentences → generate chunks."""
    session = _stream_sessions.get(session_id)
    if not session:
        return

    try:
        # Get AI response
        api_key = _get_anthropic_key()
        if not api_key:
            # Fallback: use the input text directly
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
                    "max_tokens": 300,
                    "system": ORACLE_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": text}],
                },
                timeout=30,
            )
            if resp.status_code == 200:
                ai_text = resp.json()["content"][0]["text"]
            else:
                logger.error(f"Claude API error {resp.status_code}: {resp.text[:200]}")
                ai_text = text  # fallback

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
    """Start streaming generation: text → Claude → sentence chunks → video chunks."""
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

    fps = 25.0
    duration = 4.0
    num_frames = int(duration * fps)

    # Create static frames from the avatar face
    base_frame = reg.avatar_face.copy()
    frames = [base_frame.copy() for _ in range(num_frames)]

    # Apply blinks + head movement
    frames = post_process_frames(frames, fps, enable_blinks=False, enable_head=True)

    # Encode to MP4 (no audio)
    video_path = frames_to_video(frames, fps, audio_path=None)
    if video_path:
        os.rename(video_path, ORACLE_IDLE_PATH)
        logger.info(f"Idle loop saved: {ORACLE_IDLE_PATH} ({num_frames} frames)")
    else:
        logger.error("Failed to generate idle loop")


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

    # ── Auto-warmup: prime CUDA kernels with a test generation ─────
    logger.info("[WARMUP] Running pipeline warmup...")
    warmup_start = time.time()
    try:
        import wave
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            with wave.open(tmp.name, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 8000)  # 0.5s silence
            warmup_wav = tmp.name
        frames = wav2lip_generate(warmup_wav)
        if frames:
            frames = post_process_frames(frames[:5], 25.0, enable_blinks=False, enable_head=True)
        os.unlink(warmup_wav)
        logger.info(
            f"[WARMUP] Pipeline ready in {time.time()-warmup_start:.1f}s "
            f"({len(frames)} frames)"
        )
    except Exception as e:
        logger.warning(f"[WARMUP] Failed (non-fatal): {e}")

    logger.info(
        f"[WARMUP] GPU 0 VRAM: {torch.cuda.memory_allocated(0)/1024**3:.1f}GB used"
    )

    # ── Generate idle loop if not already present ─────
    generate_idle_loop()

    logger.info(f"Avatar server ready on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
