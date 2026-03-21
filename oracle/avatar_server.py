"""
ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks
=====================================================================
GPU-accelerated Wav2Lip lip-sync with:
  - FP16 inference via ModelRegistry singleton on GPU 1
  - Kokoro af_heart TTS on cuda:1 (~2-3s latency)
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
import subprocess
import tempfile
import threading
import uuid
import numpy as np

import cv2
import torch
torch.backends.cudnn.benchmark = True
from flask import Flask, request, jsonify, send_file, after_this_request

from model_registry import ModelRegistry, WAV2LIP_DIR, AVATAR_SOURCE, DEVICE

import requests as http_requests  # ElevenLabs TTS
import json as _json

# ─── Kokoro af_heart TTS (Oracle Avatar) ─────────────────────────────
# Add oracle/ to path for normalize_pronunciation
_oracle_dir = os.path.dirname(os.path.abspath(__file__))
if _oracle_dir not in sys.path:
    sys.path.insert(0, _oracle_dir)
_AVATAR_KOKORO_READY = False
_KOKORO_PIPELINE = None

# Face enhancement + blink modules
from face_enhancer import sharpen_mouth_region
from blink_engine import apply_blink_gradient, generate_blink_schedule

# ─── Config ───────────────────────────────────────────────────────────
PORT = 8200
BATCH_SIZE_DEFAULT = 48  # Proven stable at 134fps — 64 caused VRAM pressure on GPU 1
BATCH_SIZE_SMALL = 16    # For short audio < 60 mel frames
BATCH_SIZE = BATCH_SIZE_DEFAULT

import threading as _threading_mod
_TTS_LOCK = _threading_mod.Semaphore(1)
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
LOCK_TIMEOUT = int(os.environ.get("AVATAR_LOCK_TIMEOUT", "120"))  # increased: real-time Q must wait for GPU

# Max audio duration (seconds) — longer clips get chunked
MAX_AUDIO_SECONDS = 30

# ─── Named Avatar Sources ─────────────────────────────────────────────
AVATAR_SOURCES = {
    "default":         "/home/ultron/protocol_pulse/static/img/oracle_avatar_static.png",
    "stage_hologram":  "/home/ultron/protocol_pulse/static/img/stage_bg_hologram.png",
    "oracle_studio":   "/home/ultron/protocol_pulse/oracle/Proto_P_Avatar_1024.png",
}

# Cache for loaded alternate avatar faces: {name: {"face": ndarray, "coords": tuple, "eye_landmarks": ...}}
_avatar_face_cache = {}
_avatar_face_cache_lock = threading.Lock()


def _detect_face_cpu(img, source_name):
    """Run face detection on CPU — avoids CUDA contention entirely.
    Returns (coords, eye_lm) or (None, None).
    """
    try:
        if WAV2LIP_DIR not in sys.path:
            sys.path.insert(0, WAV2LIP_DIR)
        import face_detection as _fd
        cpu_detector = _fd.FaceAlignment(_fd.LandmarksType._2D, flip_input=False, device="cpu")
        results = cpu_detector.get_detections_for_batch(np.array([img]))
        del cpu_detector

        coords = None
        if results[0] is not None:
            det = results[0]
            coords = (
                max(0, int(det[1])), min(img.shape[0], int(det[3])),
                max(0, int(det[0])), min(img.shape[1], int(det[2]))
            )
            logger.info(f"[AVATAR_SOURCE] {source_name}: face at {coords} in {img.shape[1]}x{img.shape[0]}")

        eye_lm = None
        try:
            from blink_engine import detect_eye_landmarks
            eye_lm = detect_eye_landmarks(img)
        except Exception:
            pass

        return coords, eye_lm
    except Exception as e:
        logger.error(f"[AVATAR_SOURCE] CPU face detection failed for {source_name}: {e}")
        return None, None


def _load_avatar_face(source_name):
    """Load and cache an alternate avatar face by source name (lazy, CPU-based detection).
    Returns (face_img, face_coords, eye_landmarks) or (None, None, None) on failure.
    Non-default sources are detected lazily on first request using CPU face detection,
    falling back to default if detection fails.
    """
    if source_name == "default" or source_name not in AVATAR_SOURCES:
        reg = ModelRegistry.get()
        return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks

    with _avatar_face_cache_lock:
        if source_name in _avatar_face_cache:
            c = _avatar_face_cache[source_name]
            return c["face"], c["coords"], c["eye_landmarks"]

    # Load outside lock — CPU face detection (no CUDA contention)
    img_path = AVATAR_SOURCES[source_name]
    if not os.path.exists(img_path):
        logger.error(f"[AVATAR_SOURCE] Image not found: {img_path}")
        return None, None, None

    img = cv2.imread(img_path)
    if img is None:
        logger.error(f"[AVATAR_SOURCE] Failed to read: {img_path}")
        return None, None, None

    coords, eye_lm = _detect_face_cpu(img, source_name)
    if coords is None:
        logger.error(f"[AVATAR_SOURCE] No face detected in {source_name} — falling back to default")
        reg = ModelRegistry.get()
        return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks

    with _avatar_face_cache_lock:
        _avatar_face_cache[source_name] = {"face": img.copy(), "coords": coords, "eye_landmarks": eye_lm}

    return img.copy(), coords, eye_lm

# ─── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("avatar_server")

app = Flask(__name__)

# ── CORS: allow protocolpulse.io and any origin to call avatar APIs ──────────
CORS_ORIGINS = [
    "https://protocolpulse.io",
    "https://www.protocolpulse.io",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:8080",
]

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    # Allow configured origins + any localhost
    if origin in CORS_ORIGINS or origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
        response.headers["Access-Control-Allow-Origin"] = origin
    # Default deny: no Access-Control-Allow-Origin header for unknown origins
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Credentials"] = "false"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    response = app.make_default_options_response()
    return response

# ─── Metrics ──────────────────────────────────────────────────────────
_lock = threading.Lock()
_start_time = time.time()
_request_times = []  # last 100 request times for avg latency

# ─── Async render job system (Phase 1: audio-first) ──────────────────
_render_jobs = {}        # job_id -> {"status": "pending"|"done"|"error", "video_bytes": bytes|None, "created": float}
_render_jobs_lock = threading.Lock()
_RENDER_JOB_TTL = 120   # seconds — auto-expire stale jobs

# ─── Concurrency queue (Phase 1: concurrency hardening) ──────────────
_render_semaphore = threading.Semaphore(2)  # max 2 concurrent Wav2Lip renders
_render_queue_count = 0
_render_queue_lock = threading.Lock()


def _record_latency(seconds):
    with _lock:
        _request_times.append(seconds)
        if len(_request_times) > 100:
            _request_times.pop(0)


# ═══════════════════════════════════════════════════════════════════════
# WAV2LIP INFERENCE (FP16)
# ═══════════════════════════════════════════════════════════════════════

FACE_BBOX_CACHE = os.path.join(os.path.dirname(__file__), "cache", "face_bbox.json")


def wav2lip_generate(audio_path, fps=30.0, avatar_face=None, avatar_face_coords=None):
    """Run Wav2Lip inference in FP16. Returns list of BGR frames with duration matching.
    Optional avatar_face/avatar_face_coords override the default ModelRegistry face.
    """
    reg = ModelRegistry.get()
    if reg.wav2lip_model is None:
        raise RuntimeError("Model not loaded")

    # Use overrides if provided, else default from registry
    face_img = avatar_face if avatar_face is not None else reg.avatar_face
    face_coords = avatar_face_coords if avatar_face_coords is not None else reg.avatar_face_coords

    if face_img is None or face_coords is None:
        raise RuntimeError("Avatar face not loaded")

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

    # Face bbox with chin padding (8% lower to eliminate chin seam)
    y1, y2, x1, x2 = face_coords
    y2 = min(face_img.shape[0], y2 + int((y2 - y1) * 0.08))
    face_crop = face_img[y1:y2, x1:x2]
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
            full_frame = face_img.copy()
            h_face, w_face = p_resized.shape[:2]
            # Only paste lower 55% of face — preserves eyes/nose from original
            # Wav2Lip only predicts mouth movement; upper face is lower quality upscale
            mouth_start = int(h_face * 0.45)
            feather = 18
            mask = np.zeros_like(p_resized, dtype=np.float32)
            # Build mask only for lower portion
            for row in range(mouth_start, h_face):
                blend_row = row - mouth_start
                # Fade in over feather rows at the top of the mouth region
                top_fade = min(blend_row / feather, 1.0)
                # Fade out at bottom edge
                bottom_fade = min((h_face - row) / feather, 1.0)
                row_alpha = top_fade * bottom_fade
                mask[row, :] = row_alpha
            # Side feathering
            for j in range(min(feather, w_face)):
                mask[:, j] *= j / feather
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
    # LAW: NO rotation — warpAffine on portrait avatar looks like body spinning.
    # Only micro XY translation: subtle alive-breathing feel, not distracting.
    t = frame_idx / fps
    # Gentle breathing drift: max ±1.5px horizontal, ±1px vertical
    # Two overlapping slow sinusoids so it never feels mechanical
    tx = (
        1.0 * math.sin(2 * math.pi * t / 6.0 + 0.8) +
        0.5 * math.sin(2 * math.pi * t / 11.0 + 2.1)
    )
    ty = (
        0.8 * math.sin(2 * math.pi * t / 7.5 + 1.5) +
        0.2 * math.sin(2 * math.pi * t / 4.2 + 0.6)
    )
    # Integer shift only — no warpAffine, no rotation, no interpolation artifacts
    ix, iy = int(round(tx)), int(round(ty))
    if ix == 0 and iy == 0:
        return frame
    h, w = frame.shape[:2]
    result = frame.copy()
    # Clip-and-shift: roll pixels, fill edges with border value
    if ix > 0:
        result[:, ix:] = frame[:, :w-ix]
        result[:, :ix] = frame[:, :1]
    elif ix < 0:
        result[:, :w+ix] = frame[:, -ix:]
        result[:, w+ix:] = frame[:, -1:]
    tmp = result.copy()
    if iy > 0:
        result[iy:, :] = tmp[:h-iy, :]
        result[:iy, :] = tmp[:1, :]
    elif iy < 0:
        result[:h+iy, :] = tmp[-iy:, :]
        result[h+iy:, :] = tmp[-1:, :]
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
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
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
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
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
# KOKORO af_heart FEMALE VOICE (primary) + ELEVENLABS FALLBACK
# ═══════════════════════════════════════════════════════════════════════

def _init_avatar_kokoro():
    """Lazy-init Kokoro af_heart TTS on cuda:1. Call once at startup."""
    global _AVATAR_KOKORO_READY, _KOKORO_PIPELINE
    try:
        from kokoro import KPipeline
        _KOKORO_PIPELINE = KPipeline(lang_code='a')
        _KOKORO_PIPELINE.model = _KOKORO_PIPELINE.model.to('cuda:1')
        _AVATAR_KOKORO_READY = True
        logger.info("[AVATAR_TTS] Kokoro af_heart loaded on cuda:1")
    except Exception as e:
        logger.error(f"[AVATAR_TTS] Kokoro init failed: {e} — ElevenLabs fallback active")
        _AVATAR_KOKORO_READY = False


def _avatar_tts(text):
    """Primary TTS: Kokoro af_heart -> 24kHz numpy -> ffmpeg resample 16kHz mono WAV bytes.
    Falls back to ElevenLabs text_to_speech() if Kokoro fails."""
    global _AVATAR_KOKORO_READY

    # Normalize Bitcoin pronunciation (BTC -> "bitcoin", sats, hashrate, etc.)
    try:
        from oracle_dialogue_engine import normalize_pronunciation
        text = normalize_pronunciation(text)
    except Exception as _np_err:
        logger.warning(f"[AVATAR_TTS] normalize_pronunciation unavailable: {_np_err}")

    # Serialize TTS calls — concurrent Kokoro thrashes GPU (30s+ instead of 1-2s)
    _TTS_LOCK.acquire()
    try:
        return _avatar_tts_inner(text)
    finally:
        _TTS_LOCK.release()


def _avatar_tts_inner(text):
    """Inner TTS logic — called under _TTS_LOCK."""
    global _AVATAR_KOKORO_READY

    # Try Kokoro first
    if _AVATAR_KOKORO_READY and _KOKORO_PIPELINE is not None:
        t0 = time.time()
        try:
            import soundfile as sf
            # Generate with af_heart voice
            generator = _KOKORO_PIPELINE(text, voice='af_heart')
            # Collect all audio chunks
            audio_chunks = []
            for _gs, _ps, audio_np in generator:
                audio_chunks.append(audio_np)
            if not audio_chunks:
                raise ValueError("Kokoro returned no audio")
            full_audio = np.concatenate(audio_chunks)

            # Write 24kHz WAV to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, full_audio, 24000)
                wav24_path = tmp.name

            # Resample to 16kHz mono for Wav2Lip
            wav16_path = wav24_path + ".16k.wav"
            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", wav24_path,
                 "-ar", "16000", "-ac", "1", "-f", "wav", wav16_path],
                capture_output=True, text=True, timeout=30,
            )
            try:
                os.remove(wav24_path)
            except OSError:
                pass
            if r.returncode == 0 and os.path.exists(wav16_path) and os.path.getsize(wav16_path) > 1000:
                # Loudnorm to -14 LUFS for consistent volume
                norm_path = wav16_path + "_norm.wav"
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", wav16_path,
                     "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                     "-ar", "16000", "-ac", "1", norm_path],
                    capture_output=True, text=True, timeout=30,
                )
                if os.path.exists(norm_path) and os.path.getsize(norm_path) > 1000:
                    with open(norm_path, "rb") as f:
                        wav_bytes = f.read()
                    try:
                        os.remove(norm_path)
                    except OSError:
                        pass
                else:
                    # Loudnorm failed, use unnormalized
                    with open(wav16_path, "rb") as f:
                        wav_bytes = f.read()
                try:
                    os.remove(wav16_path)
                except OSError:
                    pass
                elapsed = time.time() - t0
                logger.info(f"[AVATAR_TTS] Kokoro af_heart OK: {elapsed:.2f}s ({len(wav_bytes)} bytes)")
                return wav_bytes
            else:
                logger.warning("[AVATAR_TTS] Kokoro ffmpeg resample failed")
        except Exception as e:
            logger.error(f"[AVATAR_TTS] Kokoro FAILED: {e} → ElevenLabs fallback")
    else:
        logger.info("[AVATAR_TTS] Kokoro not ready → ElevenLabs fallback")

    # Fallback: ElevenLabs
    t0 = time.time()
    audio_bytes = text_to_speech(text)
    elapsed = time.time() - t0
    logger.info(f"[AVATAR_TTS] ElevenLabs fallback: {elapsed:.2f}s ({len(audio_bytes)} bytes)")
    return audio_bytes


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
    with _lock:
        avg_latency = round(sum(_request_times) / len(_request_times), 2) if _request_times else None
        tracked = len(_request_times)
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
        "blinks_enabled": True,  # v2 engine: cached landmarks
        "eye_landmarks_detected": (lambda: __import__("blink_engine")._load_cache() is not None)(),
        "vram": vram,
        "vision_enabled": vision_enabled,
        "uptime_sec": uptime,
        "avg_latency_sec": avg_latency,
        "requests_tracked": tracked,
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
        _render_semaphore.acquire()
        try:
            frames = wav2lip_generate(wav_path, DEFAULT_FPS)
            if frames:
                frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
        finally:
            _render_semaphore.release()
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
      Mode A: {"text": "..."} -> Kokoro af_heart (or ElevenLabs fallback) -> Wav2Lip -> video
      Mode B: {"audio_base64": "...", "content_type": "..."} -> Wav2Lip -> video
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    enable_blinks = data.get("enable_blinks", True)  # v2 blink engine enabled
    enable_head_movement = data.get("enable_head_movement", True)
    fps = float(data.get("fps", DEFAULT_FPS))
    avatar_source = data.get("avatar_source", "default")
    if avatar_source not in AVATAR_SOURCES:
        avatar_source = "default"
    logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")

    # Resolve face for this render
    gen_face, gen_coords, _gen_eyes = _load_avatar_face(avatar_source)
    if gen_face is None or gen_coords is None:
        gen_face, gen_coords, _gen_eyes = _load_avatar_face("default")

    t_start = time.time()

    # Mode A: text -> Kokoro af_heart (primary) or ElevenLabs (fallback)
    if "text" in data:
        try:
            t_tts = time.time()
            audio_bytes = _avatar_tts(data["text"])
            logger.info(f"TTS: {len(audio_bytes)} bytes in {time.time()-t_tts:.2f}s")
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return jsonify({"error": f"TTS failed: {e}"}), 500
        # Kokoro returns WAV, ElevenLabs returns MP3 — detect from header
        content_type = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
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
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)

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
        acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
        if not acquired:
            return jsonify({"error": "GPU busy", "code": "GPU_BUSY", "retry_after": 5}), 503
        try:
            t0 = time.time()
            frames = wav2lip_generate(wav_path, fps, avatar_face=gen_face, avatar_face_coords=gen_coords)
            t_lip = time.time() - t0
            logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")

            # CV2 sharpen only — no GFPGAN
            t_enhance = 0.0
            if len(frames) > 0:
                try:
                    t0_enh = time.time()
                    frames = sharpen_mouth_region(frames, gen_coords)
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
            _render_semaphore.release()

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

    # Phase 4: Store vision context in session for carry-forward
    session_id = data.get("session_id", "anon")
    try:
        from oracle_dialogue_engine import _get_session
        session = _get_session(session_id)
        vision_history = session.get("vision_history", [])
        # Build summary from analysis result
        analysis_summary = result.get("summary", "") or str(result.get("device_name", ""))
        if result.get("current_step"):
            analysis_summary += f" — {result['current_step']}"
        vision_history.append({
            "turn": session.get("turn", 0),
            "summary": analysis_summary[:200],
        })
        session["vision_history"] = vision_history[-3:]  # keep last 3
    except Exception as e:
        logger.warning(f"[VISION] Failed to store vision context: {e}")

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
    "You are the Oracle — Protocol Pulse's personal Bitcoin intelligence guide. "
    "You are having a private one-on-one conversation with a visitor. "
    "You are an EDUCATOR (explain Bitcoin at any level), GUIDE (help navigate Protocol Pulse), "
    "TECHNICAL ASSISTANT (wallets, self-custody, nodes, hardware), and INTELLIGENCE ANALYST "
    "(market state, price action — conversational, not broadcast). "
    "TONE: Warm but sharp. Knowledgeable without being condescending. "
    "Like the smartest person in Bitcoin who actually has time for you. "
    "Keep responses under 3 sentences. Never say 'As an AI' or offer daily briefs unprompted. "
    "You are NOT a news anchor or briefing bot — you are a personal guide."
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
    return key


def _split_sentences(text):
    """Split text into sentences for chunked processing."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def _generate_chunk(sentence, chunk_num, session_dir, fps=30.0):
    """Generate a single video chunk for a sentence: TTS -> Wav2Lip -> MP4."""
    try:
        audio_bytes = _avatar_tts(sentence)
        is_wav = audio_bytes[:4] == b"RIFF"
        ext = ".wav" if is_wav else ".mp3"
        audio_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}{ext}")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        wav_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}_16k.wav")
        if is_wav:
            # F5 already returned 16kHz mono WAV — just copy
            import shutil
            shutil.copy2(audio_path, wav_path)
        else:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
                check=True, capture_output=True,
            )

        _render_semaphore.acquire()
        try:
            frames = wav2lip_generate(wav_path, fps)
            reg = ModelRegistry.get()
            try:
                frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
            except Exception:
                pass
            frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
        finally:
            _render_semaphore.release()

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

    frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)

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
import oracle_dialogue_engine

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

    # If caller provided explicit text, use it directly (broadcast segments, custom scripts)
    caller_text = (data.get("text") or "").strip()
    if caller_text:
        return generate_inline(caller_text)

    # Try cached response
    path = oracle_cache_manager.get_cached_response(intent)
    if path:
        return send_file(path, mimetype="video/mp4")

    # Fallback: generate on the fly using the response tree text
    text = oracle_cache_manager.RESPONSE_TREE.get(intent)
    if not text:
        text = oracle_cache_manager.RESPONSE_TREE["UNKNOWN_QUESTION"]

    return generate_inline(text)


def generate_inline(text):
    """Internal helper: generate a video from text and return it."""
    try:
        audio_bytes = _avatar_tts(text)
    except Exception as e:
        return jsonify({"error": f"TTS failed: {e}"}), 500

    is_wav = audio_bytes[:4] == b"RIFF"
    ext = ".wav" if is_wav else ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name

    wav_path = audio_path + "_16k.wav"
    if is_wav:
        import shutil
        shutil.copy2(audio_path, wav_path)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)

    try:
        # Check queue state for concurrency visibility
        with _render_queue_lock:
            _queue_pos = sum(1 for _ in range(2) if not _render_semaphore._value)
        acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
        if not acquired:
            return jsonify({"error": "GPU busy — try again in a moment", "retry_after": 10,
                            "queue_position": _queue_pos}), 503
        try:
            frames = wav2lip_generate(wav_path, DEFAULT_FPS)
            reg = ModelRegistry.get()
            try:
                frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
            except Exception:
                pass
            frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
            video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
        finally:
            _render_semaphore.release()

        if not video_path:
            return jsonify({"error": "Video encoding failed"}), 500

        # Stream video as inline (not attachment) so browser plays it directly.
        # Generator pattern ensures file stays on disk until fully sent,
        # then cleans up. Fixes iOS mid-stream cutoff + double-unlink race.
        def _stream_and_cleanup():
            try:
                with open(video_path, "rb") as vf:
                    while True:
                        chunk = vf.read(65536)
                        if not chunk:
                            break
                        yield chunk
            finally:
                for p in [audio_path, wav_path, video_path]:
                    try:
                        if p and os.path.exists(p):
                            os.unlink(p)
                    except OSError:
                        pass

        from flask import Response
        return Response(
            _stream_and_cleanup(),
            mimetype="video/mp4",
            headers={
                "Content-Disposition": "inline",
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )

    except Exception as e:
        logger.error(f"generate_inline error: {e}", exc_info=True)
        for p in [audio_path, wav_path]:
            try:
                if os.path.exists(p): os.unlink(p)
            except OSError:
                pass
        return jsonify({"error": str(e)}), 500


def generate_inline_to_file(text, output_path):
    """Like generate_inline but writes to a file path instead of HTTP response."""
    audio_bytes = _avatar_tts(text)
    is_wav = audio_bytes[:4] == b"RIFF"
    ext = ".wav" if is_wav else ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name
    wav_path = audio_path + "_16k.wav"
    if is_wav:
        import shutil
        shutil.copy2(audio_path, wav_path)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path,
                       "-ar", "16000", "-ac", "1", wav_path],
                      check=True, capture_output=True, timeout=30)
    try:
        _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
        try:
            frames = wav2lip_generate(wav_path, DEFAULT_FPS)
            try:
                frames = sharpen_mouth_region(frames, ModelRegistry.get().avatar_face_coords)
            except Exception:
                pass
            frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
            video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
        finally:
            _render_semaphore.release()
        if video_path:
            import shutil as _sh
            _sh.move(video_path, output_path)
    finally:
        for p in [audio_path, wav_path]:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except OSError:
                pass
    return output_path


# ── Monologue pre-render system ───────────────────────────────────────
_MONOLOGUE_JOBS = {}


@app.route("/oracle/monologue", methods=["POST"])
def oracle_monologue():
    """Split a long script into chunks, pre-render all, return manifest immediately."""
    data = request.get_json()
    if not data or not data.get("script"):
        return jsonify({"error": "script required"}), 400

    script = data["script"].strip()
    job_id = str(uuid.uuid4())[:8]

    # Split into sentence chunks targeting ~20 words each
    import re as _re
    sentences = _re.split(r'(?<=[.!?])\s+', script)
    chunks = []
    current = []
    current_words = 0
    for sent in sentences:
        words = len(sent.split())
        if current_words + words > 12 and current:
            chunks.append(' '.join(current))
            current = [sent]
            current_words = words
        else:
            current.append(sent)
            current_words += words
    if current:
        chunks.append(' '.join(current))

    chunk_dir = os.path.join(os.path.dirname(__file__), "cache", "monologues", job_id)
    os.makedirs(chunk_dir, exist_ok=True)

    job = {
        "id": job_id,
        "total": len(chunks),
        "chunks": {i: {"status": "pending", "path": None} for i in range(len(chunks))},
        "texts": chunks,
    }
    _MONOLOGUE_JOBS[job_id] = job

    def render_chunk(idx, txt):
        try:
            result = generate_inline_to_file(txt, os.path.join(chunk_dir, f"chunk_{idx}.mp4"))
            job["chunks"][idx] = {"status": "ready", "path": result}
        except Exception as e:
            job["chunks"][idx] = {"status": "error", "error": str(e)}

    # Render ALL chunks in background — client polls for readiness
    for i, txt in enumerate(chunks):
        _threading_mod.Thread(target=render_chunk, args=(i, txt), daemon=True).start()

    return jsonify({
        "job_id": job_id,
        "total_chunks": len(chunks),
        "chunk_texts": chunks,
        "poll_url": f"/oracle/monologue/{job_id}/status",
    })


@app.route("/oracle/monologue/<job_id>/status")
def oracle_monologue_status(job_id):
    job = _MONOLOGUE_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    ready = [i for i, c in job["chunks"].items() if c["status"] == "ready"]
    return jsonify({
        "job_id": job_id,
        "total": job["total"],
        "ready": ready,
        "complete": len(ready) == job["total"],
    })


@app.route("/oracle/monologue/<job_id>/chunk/<int:chunk_idx>")
def oracle_monologue_chunk(job_id, chunk_idx):
    job = _MONOLOGUE_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    chunk = job["chunks"].get(chunk_idx, {})
    if chunk.get("status") != "ready":
        return jsonify({"error": "not ready", "status": chunk.get("status", "pending")}), 202
    return send_file(chunk["path"], mimetype="video/mp4")




@app.route("/oracle/voice", methods=["POST"])
def oracle_voice():
    """
    Voice-only endpoint: text -> ElevenLabs TTS -> audio/mpeg.
    No Wav2Lip, no GPU. ~400ms vs ~14s for full video.
    Use for vision guidance, quick confirmations, non-visual responses.
    Body: {"text": "...", "voice_id": "optional"}
    """
    data = request.get_json()
    if not data or not data.get("text"):
        return jsonify({"error": "text required"}), 400

    text = data["text"].strip()

    try:
        t0 = time.time()
        audio_bytes = _avatar_tts(text)
        logger.info(f"[VOICE] TTS {len(audio_bytes)}B in {time.time()-t0:.2f}s")
    except Exception as e:
        return jsonify({"error": f"TTS failed: {e}"}), 500

    # Loudnorm pass if not already normalized (WAV from Kokoro is already normalized in _avatar_tts,
    # but ElevenLabs MP3 fallback is not)
    is_wav = audio_bytes[:4] == b"RIFF"
    if not is_wav:
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as _tmp:
                _tmp.write(audio_bytes)
                _raw_path = _tmp.name
            _norm_path = _raw_path + "_norm.wav"
            _nr = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", _raw_path,
                 "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                 "-ar", "16000", "-ac", "1", _norm_path],
                capture_output=True, text=True, timeout=30,
            )
            if _nr.returncode == 0 and os.path.exists(_norm_path) and os.path.getsize(_norm_path) > 1000:
                with open(_norm_path, "rb") as _nf:
                    audio_bytes = _nf.read()
                is_wav = True
            for _p in [_raw_path, _norm_path]:
                try:
                    os.remove(_p)
                except OSError:
                    pass
        except Exception as _ne:
            logger.warning(f"[VOICE] loudnorm failed (non-fatal): {_ne}")

    mime = "audio/wav" if is_wav else "audio/mpeg"

    from flask import Response
    return Response(
        audio_bytes,
        mimetype=mime,
        headers={
            "Content-Disposition": "inline",
            "Content-Length": str(len(audio_bytes)),
            "Cache-Control": "no-cache",
        },
    )

@app.route("/oracle/job/<job_id>")
def oracle_job_status(job_id):
    """Poll for async video render completion."""
    # Expire stale jobs (pending older than TTL, or completed older than 30s)
    now = time.time()
    with _render_jobs_lock:
        expired = []
        for k, v in _render_jobs.items():
            if v.get("completed_at"):
                # Completed jobs: keep for 30s after completion
                if now - v["completed_at"] > 30:
                    expired.append(k)
            elif now - v.get("created", 0) > _RENDER_JOB_TTL:
                expired.append(k)
        for k in expired:
            del _render_jobs[k]
        job = _render_jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    if job["status"] == "done":
        # Mark completed_at on first successful poll (keep job for 30s)
        if not job.get("completed_at"):
            with _render_jobs_lock:
                if job_id in _render_jobs:
                    _render_jobs[job_id]["completed_at"] = time.time()
        video_bytes = job["video_bytes"]
        from flask import Response
        return Response(video_bytes, mimetype="video/mp4",
                        headers={"Content-Disposition": "inline", "Cache-Control": "no-cache"})
    if job["status"] == "error":
        # Mark completed_at for errors too
        if not job.get("completed_at"):
            with _render_jobs_lock:
                if job_id in _render_jobs:
                    _render_jobs[job_id]["completed_at"] = time.time()
        return jsonify({"status": "error"}), 500
    return jsonify({"status": "pending"}), 202


@app.route("/oracle/job/<job_id>/audio")
def oracle_job_audio(job_id):
    """Return cached TTS audio from an async render job (avoids duplicate Kokoro call)."""
    with _render_jobs_lock:
        job = _render_jobs.get(job_id)
    if not job or not job.get("audio_bytes"):
        return jsonify({"error": "audio not ready"}), 404
    audio_bytes = job["audio_bytes"]
    mime = job.get("audio_mime", "audio/wav")
    from flask import Response
    return Response(audio_bytes, mimetype=mime,
                    headers={"Content-Disposition": "inline",
                             "Content-Length": str(len(audio_bytes)),
                             "Cache-Control": "no-cache"})


@app.route("/oracle/chat", methods=["POST"])
def oracle_chat():
    data = request.get_json()
    if not data or not data.get("text"):
        return jsonify({"error": "text required"}), 400
    text = data["text"].strip()
    session_id = data.get("session_id", "anon")
    audio_first = data.get("audio_first", False)
    avatar_source = data.get("avatar_source", "default")
    if avatar_source not in AVATAR_SOURCES:
        avatar_source = "default"
    logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")

    # ── Phase 3: Visitor fingerprint + memory ──────────────────────────
    from oracle_memory import make_fingerprint, load_visitor
    visitor_token = data.get("visitor_token", "anon")
    raw_ip = (request.headers.get("X-Forwarded-For", "") or request.remote_addr or "").split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")
    fingerprint = make_fingerprint(raw_ip, ua, visitor_token)

    session = oracle_dialogue_engine._get_session(session_id)
    if session["turn"] == 0:
        memory = load_visitor(fingerprint)
        if memory:
            session["visitor_memory"] = memory
            logger.info(f"[MEMORY] Returning visitor — session #{memory['session_count']}")
    session["fingerprint"] = fingerprint

    _sess_turn = oracle_dialogue_engine.get_session_info(session_id).get("turn", 0)
    if data.get("use_cache_for_intents", True) and _sess_turn == 0:
        intent, confidence = classify_intent(text)
        if confidence >= 0.8 and intent != "UNKNOWN":
            path = oracle_cache_manager.get_cached_response(intent)
            if path:
                logger.info(f"[CHAT] Cache hit {intent}")
                return send_file(path, mimetype="video/mp4")
    elif _sess_turn > 0:
        logger.info(f"[CHAT] Cache skipped turn={_sess_turn}")
    live_intel = {}
    try:
        live_intel = oracle_dialogue_engine.get_live_intel()
    except Exception:
        pass
    page_context = data.get("page_context", None)
    result = oracle_dialogue_engine.generate_response(session_id, text, live_intel, page_context)
    logger.info(f"[CHAT] {session_id} t={result['turn']} p={result['personality']} ctx={page_context.get('type','?') if page_context else 'none'}: {result['text'][:50]}")

    if audio_first:
        # Phase A: return text immediately, fire video render in background
        job_id = uuid.uuid4().hex[:16]
        with _render_jobs_lock:
            _render_jobs[job_id] = {"status": "pending", "video_bytes": None, "created": time.time()}

        response_text = result["text"]

        def render_async(txt, jid, src_name="default"):
            logger.info(f"[RENDER_ASYNC] STARTED job {jid} source={src_name} text={txt[:60]}...")
            try:
                # Resolve avatar source for this render
                a_face, a_coords, _a_eyes = _load_avatar_face(src_name)
                if a_face is None or a_coords is None:
                    logger.warning(f"[ASYNC RENDER] Avatar source '{src_name}' failed, falling back to default")
                    a_face, a_coords, _a_eyes = _load_avatar_face("default")

                audio_bytes = _avatar_tts(txt)
                # Cache audio in job dict so frontend can fetch it without calling Kokoro again
                with _render_jobs_lock:
                    if jid in _render_jobs:
                        _render_jobs[jid]["audio_bytes"] = audio_bytes
                        _render_jobs[jid]["audio_mime"] = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
                is_wav = audio_bytes[:4] == b"RIFF"
                ext = ".wav" if is_wav else ".mp3"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(audio_bytes)
                    audio_path = tmp.name
                wav_path = audio_path + "_16k.wav"
                if is_wav:
                    import shutil
                    shutil.copy2(audio_path, wav_path)
                else:
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
                try:
                    acquired = _render_semaphore.acquire(timeout=60)
                    if not acquired:
                        logger.warning(f"[ASYNC RENDER] GPU busy for job {jid}")
                        with _render_jobs_lock:
                            if jid in _render_jobs:
                                _render_jobs[jid] = {"status": "error", "video_bytes": None,
                                                     "created": time.time(), "code": "GPU_BUSY"}
                        return
                    try:
                        frames = wav2lip_generate(wav_path, DEFAULT_FPS, avatar_face=a_face, avatar_face_coords=a_coords)
                        try:
                            frames = sharpen_mouth_region(frames, a_coords)
                        except Exception:
                            pass
                        frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
                        video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
                    finally:
                        _render_semaphore.release()

                    if video_path and os.path.exists(video_path):
                        with open(video_path, "rb") as vf:
                            vbytes = vf.read()
                        os.unlink(video_path)
                        with _render_jobs_lock:
                            if jid in _render_jobs:
                                _render_jobs[jid] = {"status": "done", "video_bytes": vbytes, "created": time.time()}
                    else:
                        with _render_jobs_lock:
                            if jid in _render_jobs:
                                _render_jobs[jid]["status"] = "error"
                finally:
                    for p in [audio_path, wav_path]:
                        try:
                            if os.path.exists(p):
                                os.unlink(p)
                        except OSError:
                            pass
            except Exception as e:
                logger.error(f"[ASYNC RENDER] {e}")
                with _render_jobs_lock:
                    if jid in _render_jobs:
                        _render_jobs[jid]["status"] = "error"

        t = threading.Thread(target=render_async, args=(response_text, job_id, avatar_source), daemon=True)
        t.start()

        resp_data = {
            "text": response_text,
            "session_id": session_id,
            "job_id": job_id,
            "video_pending": True,
        }
        # Detect action card from user input (zero LLM cost)
        try:
            card = oracle_dialogue_engine.detect_action_card(text)
            if card:
                resp_data["action_card"] = card
                logger.info(f"[CHAT] Action card triggered: {card['id']}")
        except Exception as _card_err:
            logger.warning(f"[CHAT] Action card detection error: {_card_err}")
        return jsonify(resp_data)

    # Existing: return video directly
    return generate_inline(result["text"])


@app.route("/oracle/session", methods=["GET"])
def oracle_session_info():
    return jsonify(oracle_dialogue_engine.get_session_info(request.args.get("session_id","anon")))


@app.route("/oracle/session/reset", methods=["POST"])
def oracle_session_reset():
    data = request.get_json() or {}
    sid = data.get("session_id", "anon")

    # ── Phase 3: Save visitor memory before clearing session ───────────
    session = oracle_dialogue_engine._sessions.get(sid, {})
    fingerprint = session.get("fingerprint")
    if fingerprint and session.get("history"):
        try:
            from oracle_memory import save_visitor, generate_session_summary
            api_key = _get_anthropic_key()
            summary = generate_session_summary(session["history"], api_key) if api_key else ""
            flow = session.get("setup_flow", {})
            prev_memory = session.get("visitor_memory", {})
            save_visitor(fingerprint, {
                "personality": session.get("personality", "AMIABLE"),
                "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
                "setup_device": flow.get("device"),
                "setup_step": flow.get("step", 0),
                "topics_seen": session.get("topics_discussed", []),
                "products_shown": session.get("products_mentioned", []),
            })
            logger.info(f"[MEMORY] Saved visitor memory for session {sid}")
        except Exception as e:
            logger.warning(f"[MEMORY] Save failed on reset: {e}")

    oracle_dialogue_engine.reset_session(sid)
    return jsonify({"status": "reset"})


@app.route("/oracle/session/save", methods=["POST"])
def oracle_session_save():
    """Save session memory on page unload without clearing the session."""
    data = request.get_json() or {}
    sid = data.get("session_id", "anon")
    session = oracle_dialogue_engine._sessions.get(sid, {})
    fingerprint = session.get("fingerprint")
    if fingerprint and session.get("history"):
        try:
            from oracle_memory import save_visitor, generate_session_summary
            api_key = _get_anthropic_key()
            summary = generate_session_summary(session["history"], api_key) if api_key else ""
            flow = session.get("setup_flow", {})
            prev_memory = session.get("visitor_memory", {})
            topics = list(session.get("topics_discussed", []))
            save_visitor(fingerprint, {
                "personality": session.get("personality", "AMIABLE"),
                "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
                "setup_device": flow.get("device"),
                "setup_step": flow.get("step", 0),
                "topics_seen": topics,
                "products_shown": session.get("products_mentioned", []),
            })
            logger.info(f"[MEMORY] Saved session {sid} on unload — {len(topics)} topics, summary len={len(summary)}")
        except Exception as e:
            logger.warning(f"[MEMORY] Save on unload failed: {e}")
    return jsonify({"status": "saved"})


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
# TTS PROVIDER STATUS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/avatar/tts-provider", methods=["GET"])
def avatar_tts_provider():
    """Report which TTS provider is active."""
    if _AVATAR_KOKORO_READY:
        return jsonify({
            "provider": "kokoro",
            "voice": "af_heart",
            "backend": "cuda:1",
            "sample_rate": 24000,
            "ready": True,
        })
    return jsonify({
        "provider": "elevenlabs_fallback",
        "reason": "Kokoro not loaded or init failed",
        "ready": False,
    })


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks")
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

    # Load Kokoro af_heart TTS on cuda:1 (~2-3s per utterance)
    logger.info("[STARTUP] Initializing Kokoro af_heart TTS on cuda:1...")
    _init_avatar_kokoro()

    # Auto-warmup (non-blocking — runs in background thread so Flask can start immediately)
    def _warmup_background():
        logger.info("[WARMUP] Running pipeline warmup in background...")
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
    threading.Thread(target=_warmup_background, daemon=True).start()

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
