# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: oracle-avatar-fix
# Branch: main
# Generated: 2026-03-24 11:58 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)


---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: oracle/avatar_server.py (2117 lines)
```
   1 | """
   2 | ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks
   3 | =====================================================================
   4 | GPU-accelerated Wav2Lip lip-sync with:
   5 |   - FP16 inference via ModelRegistry singleton on GPU 1
   6 |   - Kokoro af_heart TTS on cuda:1 (~2-3s latency)
   7 |   - CV2 bilateral sharpen (GFPGAN fully removed 2026-03-12)
   8 |   - MediaPipe eye blinks (gradient overlay, no warpAffine artifacts)
   9 |   - Head movement post-processing
  10 |   - Vision guide endpoints (Gemini 2.5 Flash)
  11 |   - Input audio length guard (30s max, chunked processing)
  12 |   - CRF 28, preset ultrafast, 30fps output
  13 | 
  14 | Deploy: ~/protocol_pulse/oracle/avatar_server.py
  15 | Launch: cd ~/protocol_pulse/oracle && python3 avatar_server.py
  16 | """
  17 | 
  18 | import os
  19 | import sys
  20 | import time
  21 | import math
  22 | import random
  23 | import base64
  24 | import logging
  25 | import subprocess
  26 | import tempfile
  27 | import threading
  28 | import uuid
  29 | import numpy as np
  30 | 
  31 | import cv2
  32 | import torch
  33 | torch.backends.cudnn.benchmark = True
  34 | from flask import Flask, request, jsonify, send_file, after_this_request
  35 | 
  36 | from model_registry import ModelRegistry, WAV2LIP_DIR, AVATAR_SOURCE, DEVICE
  37 | 
  38 | import requests as http_requests  # ElevenLabs TTS
  39 | import json as _json
  40 | 
  41 | # ─── Kokoro af_heart TTS (Oracle Avatar) ─────────────────────────────
  42 | # Add oracle/ to path for normalize_pronunciation
  43 | _oracle_dir = os.path.dirname(os.path.abspath(__file__))
  44 | if _oracle_dir not in sys.path:
  45 |     sys.path.insert(0, _oracle_dir)
  46 | _AVATAR_KOKORO_READY = False
  47 | _KOKORO_PIPELINE = None
  48 | 
  49 | # Face enhancement + blink modules
  50 | from face_enhancer import sharpen_mouth_region
  51 | from blink_engine import apply_blink_gradient, generate_blink_schedule
  52 | 
  53 | # ─── Config ───────────────────────────────────────────────────────────
  54 | PORT = 8200
  55 | BATCH_SIZE_DEFAULT = 48  # Proven stable at 134fps — 64 caused VRAM pressure on GPU 1
  56 | BATCH_SIZE_SMALL = 16    # For short audio < 60 mel frames
  57 | BATCH_SIZE = BATCH_SIZE_DEFAULT
  58 | DEFAULT_FPS = 30.0  # Upgraded from 25fps — smoother motion
  59 | 
  60 | # Post-processing config
  61 | BLINK_INTERVAL_MIN = 2.5
  62 | BLINK_INTERVAL_MAX = 5.0
  63 | BLINK_DURATION = 0.22  # ~6-7 frames at 30fps, visible but natural
  64 | HEAD_ROTATION_AMPLITUDE = 2.5   # degrees — visible news-anchor sway
  65 | HEAD_TRANSLATION_X = 4.0        # pixels — visible horizontal drift
  66 | HEAD_TRANSLATION_Y = 2.0        # pixels — visible vertical drift
  67 | HEAD_PERIOD = 5.0               # seconds per full cycle — slow and natural
  68 | 
  69 | # Lock timeout (seconds) — if GPU is busy longer than this, return 503
  70 | LOCK_TIMEOUT = int(os.environ.get("AVATAR_LOCK_TIMEOUT", "120"))  # increased: real-time Q must wait for GPU
  71 | 
  72 | # Max audio duration (seconds) — longer clips get chunked
  73 | MAX_AUDIO_SECONDS = 30
  74 | 
  75 | # ─── Named Avatar Sources ─────────────────────────────────────────────
  76 | AVATAR_SOURCES = {
  77 |     "default":         "/home/ultron/protocol_pulse/static/img/oracle_avatar_static.png",
  78 |     "stage_hologram":  "/home/ultron/protocol_pulse/static/img/stage_bg_hologram.png",
  79 |     "oracle_studio":   "/home/ultron/protocol_pulse/oracle/Proto_P_Avatar_1024.png",
  80 | }
  81 | 
  82 | # Cache for loaded alternate avatar faces: {name: {"face": ndarray, "coords": tuple, "eye_landmarks": ...}}
  83 | _avatar_face_cache = {}
  84 | _avatar_face_cache_lock = threading.Lock()
  85 | 
  86 | 
  87 | def _detect_face_cpu(img, source_name):
  88 |     """Run face detection on CPU — avoids CUDA contention entirely.
  89 |     Returns (coords, eye_lm) or (None, None).
  90 |     """
  91 |     try:
  92 |         if WAV2LIP_DIR not in sys.path:
  93 |             sys.path.insert(0, WAV2LIP_DIR)
  94 |         import face_detection as _fd
  95 |         cpu_detector = _fd.FaceAlignment(_fd.LandmarksType._2D, flip_input=False, device="cpu")
  96 |         results = cpu_detector.get_detections_for_batch(np.array([img]))
  97 |         del cpu_detector
  98 | 
  99 |         coords = None
 100 |         if results[0] is not None:
 101 |             det = results[0]
 102 |             coords = (
 103 |                 max(0, int(det[1])), min(img.shape[0], int(det[3])),
 104 |                 max(0, int(det[0])), min(img.shape[1], int(det[2]))
 105 |             )
 106 |             logger.info(f"[AVATAR_SOURCE] {source_name}: face at {coords} in {img.shape[1]}x{img.shape[0]}")
 107 | 
 108 |         eye_lm = None
 109 |         try:
 110 |             from blink_engine import detect_eye_landmarks
 111 |             eye_lm = detect_eye_landmarks(img)
 112 |         except Exception:
 113 |             pass
 114 | 
 115 |         return coords, eye_lm
 116 |     except Exception as e:
 117 |         logger.error(f"[AVATAR_SOURCE] CPU face detection failed for {source_name}: {e}")
 118 |         return None, None
 119 | 
 120 | 
 121 | def _load_avatar_face(source_name):
 122 |     """Load and cache an alternate avatar face by source name (lazy, CPU-based detection).
 123 |     Returns (face_img, face_coords, eye_landmarks) or (None, None, None) on failure.
 124 |     Non-default sources are detected lazily on first request using CPU face detection,
 125 |     falling back to default if detection fails.
 126 |     """
 127 |     if source_name == "default" or source_name not in AVATAR_SOURCES:
 128 |         reg = ModelRegistry.get()
 129 |         return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks
 130 | 
 131 |     with _avatar_face_cache_lock:
 132 |         if source_name in _avatar_face_cache:
 133 |             c = _avatar_face_cache[source_name]
 134 |             return c["face"], c["coords"], c["eye_landmarks"]
 135 | 
 136 |     # Load outside lock — CPU face detection (no CUDA contention)
 137 |     img_path = AVATAR_SOURCES[source_name]
 138 |     if not os.path.exists(img_path):
 139 |         logger.error(f"[AVATAR_SOURCE] Image not found: {img_path}")
 140 |         return None, None, None
 141 | 
 142 |     img = cv2.imread(img_path)
 143 |     if img is None:
 144 |         logger.error(f"[AVATAR_SOURCE] Failed to read: {img_path}")
 145 |         return None, None, None
 146 | 
 147 |     coords, eye_lm = _detect_face_cpu(img, source_name)
 148 |     if coords is None:
 149 |         logger.error(f"[AVATAR_SOURCE] No face detected in {source_name} — falling back to default")
 150 |         reg = ModelRegistry.get()
 151 |         return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks
 152 | 
 153 |     with _avatar_face_cache_lock:
 154 |         _avatar_face_cache[source_name] = {"face": img.copy(), "coords": coords, "eye_landmarks": eye_lm}
 155 | 
 156 |     return img.copy(), coords, eye_lm
 157 | 
 158 | # ─── Logging ──────────────────────────────────────────────────────────
 159 | logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
 160 | logger = logging.getLogger("avatar_server")
 161 | 
 162 | app = Flask(__name__)
 163 | 
 164 | # ── CORS: allow protocolpulse.io and any origin to call avatar APIs ──────────
 165 | CORS_ORIGINS = [
 166 |     "https://protocolpulse.io",
 167 |     "https://www.protocolpulse.io",
 168 |     "http://localhost:3000",
 169 |     "http://localhost:5000",
 170 |     "http://localhost:8080",
 171 | ]
 172 | 
 173 | @app.after_request
 174 | def add_cors_headers(response):
 175 |     origin = request.headers.get("Origin", "")
 176 |     # Allow configured origins + any localhost
 177 |     if origin in CORS_ORIGINS or origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
 178 |         response.headers["Access-Control-Allow-Origin"] = origin
 179 |     # Default deny: no Access-Control-Allow-Origin header for unknown origins
 180 |     response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
 181 |     response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
 182 |     response.headers["Access-Control-Allow-Credentials"] = "false"
 183 |     response.headers["Access-Control-Max-Age"] = "86400"
 184 |     return response
 185 | 
 186 | @app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
 187 | @app.route("/<path:path>", methods=["OPTIONS"])
 188 | def handle_options(path):
 189 |     response = app.make_default_options_response()
 190 |     return response
 191 | 
 192 | # ─── Metrics ──────────────────────────────────────────────────────────
 193 | _lock = threading.Lock()
 194 | _start_time = time.time()
 195 | _request_times = []  # last 100 request times for avg latency
 196 | 
 197 | # ─── Async render job system (Phase 1: audio-first) ──────────────────
 198 | _render_jobs = {}        # job_id -> {"status": "pending"|"done"|"error", "video_bytes": bytes|None, "created": float}
 199 | _render_jobs_lock = threading.Lock()
 200 | _RENDER_JOB_TTL = 120   # seconds — auto-expire stale jobs
 201 | 
 202 | # ─── Concurrency queue (Phase 1: concurrency hardening) ──────────────
 203 | _render_semaphore = threading.Semaphore(2)  # max 2 concurrent Wav2Lip renders
 204 | _render_queue_count = 0
 205 | _render_queue_lock = threading.Lock()
 206 | 
 207 | 
 208 | def _record_latency(seconds):
 209 |     with _lock:
 210 |         _request_times.append(seconds)
 211 |         if len(_request_times) > 100:
 212 |             _request_times.pop(0)
 213 | 
 214 | 
 215 | # ═══════════════════════════════════════════════════════════════════════
 216 | # WAV2LIP INFERENCE (FP16)
 217 | # ═══════════════════════════════════════════════════════════════════════
 218 | 
 219 | FACE_BBOX_CACHE = os.path.join(os.path.dirname(__file__), "cache", "face_bbox.json")
 220 | 
 221 | 
 222 | def wav2lip_generate(audio_path, fps=30.0, avatar_face=None, avatar_face_coords=None):
 223 |     """Run Wav2Lip inference in FP16. Returns list of BGR frames with duration matching.
 224 |     Optional avatar_face/avatar_face_coords override the default ModelRegistry face.
 225 |     """
 226 |     reg = ModelRegistry.get()
 227 |     if reg.wav2lip_model is None:
 228 |         raise RuntimeError("Model not loaded")
 229 | 
 230 |     # Use overrides if provided, else default from registry
 231 |     face_img = avatar_face if avatar_face is not None else reg.avatar_face
 232 |     face_coords = avatar_face_coords if avatar_face_coords is not None else reg.avatar_face_coords
 233 | 
 234 |     if face_img is None or face_coords is None:
 235 |         raise RuntimeError("Avatar face not loaded")
 236 | 
 237 |     if WAV2LIP_DIR not in sys.path:
 238 |         sys.path.insert(0, WAV2LIP_DIR)
 239 |     import audio as wav2lip_audio
 240 | 
 241 |     wav = wav2lip_audio.load_wav(audio_path, 16000)
 242 |     mel = wav2lip_audio.melspectrogram(wav)
 243 |     if mel.shape[1] == 0:
 244 |         raise ValueError("Empty audio")
 245 | 
 246 |     mel_step = 16
 247 |     audio_duration = len(wav) / 16000.0
 248 |     num_frames = int(math.ceil(audio_duration * fps)) + 2  # prevent audio cutoff
 249 |     if num_frames < 1:
 250 |         num_frames = 1
 251 | 
 252 |     # Map each VIDEO frame to its correct MEL position
 253 |     mel_idx_multiplier = 80.0 / fps
 254 | 
 255 |     mel_chunks = []
 256 |     for frame_i in range(num_frames):
 257 |         start_col = int(frame_i * mel_idx_multiplier)
 258 |         end_col = start_col + mel_step
 259 |         if end_col > mel.shape[1]:
 260 |             chunk = mel[:, start_col:]
 261 |             if chunk.shape[1] < mel_step:
 262 |                 chunk = np.pad(chunk, ((0, 0), (0, mel_step - chunk.shape[1])))
 263 |         else:
 264 |             chunk = mel[:, start_col:end_col]
 265 |         mel_chunks.append(chunk)
 266 | 
 267 |     # Adaptive batch size: smaller for short audio
 268 |     batch_size = BATCH_SIZE_SMALL if len(mel_chunks) < 60 else BATCH_SIZE_DEFAULT
 269 | 
 270 |     logger.info(f"Mel: {mel.shape[1]} cols, {num_frames} frames @ {fps}fps, audio {audio_duration:.2f}s, batch={batch_size}")
 271 | 
 272 |     # Face bbox with chin padding (8% lower to eliminate chin seam)
 273 |     y1, y2, x1, x2 = face_coords
 274 |     y2 = min(face_img.shape[0], y2 + int((y2 - y1) * 0.08))
 275 |     face_crop = face_img[y1:y2, x1:x2]
 276 |     face_resized = cv2.resize(face_crop, (96, 96))
 277 |     face_masked = face_resized.copy()
 278 |     face_masked[face_resized.shape[0] // 2:, :] = 0
 279 | 
 280 |     frames = []
 281 |     total_chunks = len(mel_chunks)
 282 | 
 283 |     for batch_start in range(0, total_chunks, batch_size):
 284 |         batch_end = min(batch_start + batch_size, total_chunks)
 285 |         batch_mels = mel_chunks[batch_start:batch_end]
 286 | 
 287 |         img_concat = np.concatenate((face_masked, face_resized), axis=2)
 288 |         img_batch = np.array([img_concat / 255.0] * len(batch_mels), dtype=np.float32)
 289 |         mel_batch = np.array(batch_mels, dtype=np.float32)
 290 | 
 291 |         # FP16 tensors → GPU 1
 292 |         img_batch = torch.HalfTensor(img_batch.transpose(0, 3, 1, 2)).to(DEVICE)
 293 |         mel_batch = torch.HalfTensor(mel_batch[:, np.newaxis, :, :]).to(DEVICE)
 294 | 
 295 |         with torch.no_grad():
 296 |             pred = reg.wav2lip_model(mel_batch, img_batch)
 297 | 
 298 |         pred = pred.float().cpu().numpy().transpose(0, 2, 3, 1) * 255.0
 299 | 
 300 |         for p in pred:
 301 |             p_resized = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
 302 |             full_frame = face_img.copy()
 303 |             # Feathered blend to eliminate face paste seam
 304 |             mask = np.ones_like(p_resized, dtype=np.float32)
 305 |             feather = 18
 306 |             h_face, w_face = p_resized.shape[:2]
 307 |             for j in range(min(feather, h_face)):
 308 |                 mask[j, :] = j / feather
 309 |             for j in range(min(feather, h_face)):
 310 |                 mask[-(j+1), :] = j / feather
 311 |             for j in range(min(feather, w_face)):
 312 |                 mask[:, j] *= j / feather
 313 |             for j in range(min(feather, w_face)):
 314 |                 mask[:, -(j+1)] *= j / feather
 315 |             full_frame[y1:y2, x1:x2] = (
 316 |                 p_resized * mask + full_frame[y1:y2, x1:x2] * (1 - mask)
 317 |             ).astype(np.uint8)
 318 |             frames.append(full_frame)
 319 | 
 320 |     logger.info(f"Generated {len(frames)} frames for {audio_duration:.2f}s audio @ {fps}fps")
 321 |     return frames
 322 | 
 323 | 
 324 | # ═══════════════════════════════════════════════════════════════════════
 325 | # POST-PROCESSING: HEAD MOVEMENT
 326 | # ═══════════════════════════════════════════════════════════════════════
 327 | 
 328 | def apply_head_movement(frame, frame_idx, fps):
 329 |     # LAW: NO rotation — warpAffine on portrait avatar looks like body spinning.
 330 |     # Only micro XY translation: subtle alive-breathing feel, not distracting.
 331 |     t = frame_idx / fps
 332 |     # Gentle breathing drift: max ±1.5px horizontal, ±1px vertical
 333 |     # Two overlapping slow sinusoids so it never feels mechanical
 334 |     tx = (
 335 |         1.0 * math.sin(2 * math.pi * t / 6.0 + 0.8) +
 336 |         0.5 * math.sin(2 * math.pi * t / 11.0 + 2.1)
 337 |     )
 338 |     ty = (
 339 |         0.8 * math.sin(2 * math.pi * t / 7.5 + 1.5) +
 340 |         0.2 * math.sin(2 * math.pi * t / 4.2 + 0.6)
 341 |     )
 342 |     # Integer shift only — no warpAffine, no rotation, no interpolation artifacts
 343 |     ix, iy = int(round(tx)), int(round(ty))
 344 |     if ix == 0 and iy == 0:
 345 |         return frame
 346 |     h, w = frame.shape[:2]
 347 |     result = frame.copy()
 348 |     # Clip-and-shift: roll pixels, fill edges with border value
 349 |     if ix > 0:
 350 |         result[:, ix:] = frame[:, :w-ix]
 351 |         result[:, :ix] = frame[:, :1]
 352 |     elif ix < 0:
 353 |         result[:, :w+ix] = frame[:, -ix:]
 354 |         result[:, w+ix:] = frame[:, -1:]
 355 |     tmp = result.copy()
 356 |     if iy > 0:
 357 |         result[iy:, :] = tmp[:h-iy, :]
 358 |         result[:iy, :] = tmp[:1, :]
 359 |     elif iy < 0:
 360 |         result[:h+iy, :] = tmp[-iy:, :]
 361 |         result[h+iy:, :] = tmp[-1:, :]
 362 |     return result
 363 | 
 364 | 
 365 | # ═══════════════════════════════════════════════════════════════════════
 366 | # POST-PROCESSING: COMBINED PIPELINE
 367 | # ═══════════════════════════════════════════════════════════════════════
 368 | 
 369 | def post_process_frames(frames, fps=30.0, enable_blinks=True, enable_head=True):
 370 |     """Apply eye blinks and head movement post-processing."""
 371 |     if len(frames) == 0:
 372 |         return frames
 373 | 
 374 |     reg = ModelRegistry.get()
 375 | 
 376 |     # Generate blink schedule
 377 |     blink_schedule = {}
 378 |     if enable_blinks:
 379 |         blink_schedule = generate_blink_schedule(
 380 |             len(frames), fps,
 381 |             interval_min=BLINK_INTERVAL_MIN,
 382 |             interval_max=BLINK_INTERVAL_MAX,
 383 |             duration=BLINK_DURATION,
 384 |         )
 385 | 
 386 |     processed = []
 387 |     for i, frame in enumerate(frames):
 388 |         result = frame
 389 |         if enable_blinks and i in blink_schedule:
 390 |             try:
 391 |                 result = apply_blink_gradient(
 392 |                     result,
 393 |                     blink_schedule[i],
 394 |                     eye_landmarks=reg.eye_landmarks,
 395 |                     face_coords=reg.avatar_face_coords,
 396 |                 )
 397 |             except Exception:
 398 |                 # P0 safety net: blink artifacts → return original frame
 399 |                 result = frame
 400 |         if enable_head:
 401 |             result = apply_head_movement(result, i, fps)
 402 |         processed.append(result)
 403 |     return processed
 404 | 
 405 | 
 406 | # ═══════════════════════════════════════════════════════════════════════
 407 | # VIDEO ENCODING
 408 | # ═══════════════════════════════════════════════════════════════════════
 409 | 
 410 | def frames_to_video(frames, fps=30.0, audio_path=None):
 411 |     """Encode frames to MP4, optionally muxing audio (audio as timing master).
 412 |     Returns the path to the output MP4 file (caller must clean up)."""
 413 |     if not frames:
 414 |         return None
 415 |     with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp_avi:
 416 |         avi_path = tmp_avi.name
 417 |     mp4_path = avi_path.replace(".avi", ".mp4")
 418 |     try:
 419 |         h, w = frames[0].shape[:2]
 420 |         fourcc = cv2.VideoWriter_fourcc(*"MJPG")
 421 |         writer = cv2.VideoWriter(avi_path, fourcc, fps, (w, h))
 422 |         for frame in frames:
 423 |             writer.write(frame)
 424 |         writer.release()
 425 | 
 426 |         import subprocess
 427 |         if audio_path and os.path.exists(audio_path):
 428 |             cmd = [
 429 |                 "ffmpeg", "-y", "-loglevel", "error",
 430 |                 "-itsoffset", "0.08", "-i", audio_path, "-i", avi_path,
 431 |             ]
 432 |             if w > 512:
 433 |                 cmd += ["-vf", "scale=512:512"]
 434 |             cmd += [
 435 |                 "-c:v", "libx264", "-preset", "medium", "-crf", "18",
 436 |                 "-c:a", "aac", "-b:a", "128k",
 437 |                 "-map", "0:a", "-map", "1:v",
 438 |                 "-pix_fmt", "yuv420p", "-movflags", "+faststart",
 439 |                 mp4_path,
 440 |             ]
 441 |             subprocess.run(cmd, check=True, capture_output=True)
 442 |         else:
 443 |             cmd = [
 444 |                 "ffmpeg", "-y", "-loglevel", "error",
 445 |                 "-i", avi_path,
 446 |             ]
 447 |             if w > 512:
 448 |                 cmd += ["-vf", "scale=512:512"]
 449 |             cmd += [
 450 |                 "-c:v", "libx264", "-preset", "medium", "-crf", "18",
 451 |                 "-pix_fmt", "yuv420p", "-movflags", "+faststart",
 452 |                 mp4_path,
 453 |             ]
 454 |             subprocess.run(cmd, check=True, capture_output=True)
 455 | 
 456 |         if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
 457 |             return mp4_path
 458 |         else:
 459 |             logger.error("ffmpeg failed to produce MP4")
 460 |             return None
 461 |     finally:
 462 |         try:
 463 |             os.unlink(avi_path)
 464 |         except OSError:
 465 |             pass
 466 | 
 467 | 
 468 | # ═══════════════════════════════════════════════════════════════════════
 469 | # KOKORO af_heart FEMALE VOICE (primary) + ELEVENLABS FALLBACK
 470 | # ═══════════════════════════════════════════════════════════════════════
 471 | 
 472 | def _init_avatar_kokoro():
 473 |     """Lazy-init Kokoro af_heart TTS on cuda:1. Call once at startup."""
 474 |     global _AVATAR_KOKORO_READY, _KOKORO_PIPELINE
 475 |     try:
 476 |         from kokoro import KPipeline
 477 |         _KOKORO_PIPELINE = KPipeline(lang_code='a')
 478 |         _KOKORO_PIPELINE.model = _KOKORO_PIPELINE.model.to('cuda:1')
 479 |         _AVATAR_KOKORO_READY = True
 480 |         logger.info("[AVATAR_TTS] Kokoro af_heart loaded on cuda:1")
 481 |     except Exception as e:
 482 |         logger.error(f"[AVATAR_TTS] Kokoro init failed: {e} — ElevenLabs fallback active")
 483 |         _AVATAR_KOKORO_READY = False
 484 | 
 485 | 
 486 | def _preprocess_tts_text(text: str) -> str:
 487 |     """Convert numbers and symbols to spoken form for natural TTS."""
 488 |     import re
 489 |     try:
 490 |         from num2words import num2words
 491 |     except ImportError:
 492 |         return text
 493 | 
 494 |     # Percentages: 0.79% → "point seventy-nine percent"
 495 |     def pct(m):
 496 |         try:
 497 |             val = float(m.group(1))
 498 |             if val == int(val):
 499 |                 return num2words(int(val)) + ' percent'
 500 |             parts = str(val).split('.')
 501 |             return num2words(int(parts[0])) + ' point ' + ' '.join(num2words(int(d)) for d in parts[1]) + ' percent'
 502 |         except: return m.group(0)
 503 |     text = re.sub(r'([\d]+\.?\d*)\s*%', pct, text)
 504 | 
 505 |     # Dollars: $70,586 → "seventy thousand five hundred eighty-six dollars"
 506 |     def dollars(m):
 507 |         try:
 508 |             raw = m.group(1).replace(',', '')
 509 |             val = int(float(raw))
 510 |             return num2words(val) + ' dollars'
 511 |         except: return m.group(0)
 512 |     text = re.sub(r'\$\s*([\d,]+\.?\d*)', dollars, text)
 513 | 
 514 |     # Large numbers with commas: 970,600 → spoken
 515 |     def bignum(m):
 516 |         try: return num2words(int(m.group(0).replace(',', '')))
 517 |         except: return m.group(0)
 518 |     text = re.sub(r'\b\d{1,3}(?:,\d{3})+\b', bignum, text)
 519 | 
 520 |     # Decimals: 970.6 → "nine hundred seventy point six"
 521 |     def decimal(m):
 522 |         try:
 523 |             parts = m.group(0).split('.')
 524 |             return num2words(int(parts[0])) + ' point ' + ' '.join(num2words(int(d)) for d in parts[1])
 525 |         except: return m.group(0)
 526 |     text = re.sub(r'\b(\d+)\.(\d+)\b', decimal, text)
 527 | 
 528 |     # Large plain integers 4+ digits
 529 |     def integer(m):
 530 |         try: return num2words(int(m.group(0)))
 531 |         except: return m.group(0)
 532 |     text = re.sub(r'\b(\d{4,})\b', integer, text)
 533 | 
 534 |     # Proper pronunciations
 535 |     text = re.sub(r'\bNostr\b', 'Nohster', text)
 536 |     text = re.sub(r'\bNOSTR\b', 'Nohster', text)
 537 |     text = re.sub(r'\bnostr\b', 'Nohster', text)
 538 |     text = re.sub(r'\bBTC\b', 'Bitcoin', text)
 539 |     text = re.sub(r'\bETF\b', 'E T F', text)
 540 |     text = re.sub(r'\bFNG\b', 'fear and greed index', text, flags=re.IGNORECASE)
 541 |     text = re.sub(r'\bEH/s\b', 'exahashes per second', text)
 542 |     text = re.sub(r'\bEH\b', 'exahash', text)
 543 |     text = re.sub(r'\bsat/vbyte\b', 'sats per vbyte', text)
 544 | 
 545 |     return text
 546 | 
 547 | 
 548 | def _avatar_tts(text):
 549 |     """Primary TTS: Kokoro af_heart -> 24kHz numpy -> ffmpeg resample 16kHz mono WAV bytes.
 550 |     Falls back to ElevenLabs text_to_speech() if Kokoro fails."""
 551 |     global _AVATAR_KOKORO_READY
 552 | 
 553 |     # Normalize Bitcoin pronunciation (BTC -> "bitcoin", sats, hashrate, etc.)
 554 |     try:
 555 |         from oracle_dialogue_engine import normalize_pronunciation
 556 |         text = normalize_pronunciation(text)
 557 |     except Exception as _np_err:
 558 |         logger.warning(f"[AVATAR_TTS] normalize_pronunciation unavailable: {_np_err}")
 559 | 
 560 |     text = _preprocess_tts_text(text)
 561 | 
 562 |     # Try Kokoro first
 563 |     if _AVATAR_KOKORO_READY and _KOKORO_PIPELINE is not None:
 564 |         t0 = time.time()
 565 |         try:
 566 |             import soundfile as sf
 567 |             # Generate with af_heart voice
 568 |             generator = _KOKORO_PIPELINE(text, voice='af_heart')
 569 |             # Collect all audio chunks
 570 |             audio_chunks = []
 571 |             for _gs, _ps, audio_np in generator:
 572 |                 audio_chunks.append(audio_np)
 573 |             if not audio_chunks:
 574 |                 raise ValueError("Kokoro returned no audio")
 575 |             full_audio = np.concatenate(audio_chunks)
 576 | 
 577 |             # Write 24kHz WAV to temp file
 578 |             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
 579 |                 sf.write(tmp.name, full_audio, 24000)
 580 |                 wav24_path = tmp.name
 581 | 
 582 |             # Resample to 16kHz mono for Wav2Lip
 583 |             wav16_path = wav24_path + ".16k.wav"
 584 |             r = subprocess.run(
 585 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", wav24_path,
 586 |                  "-ar", "16000", "-ac", "1", "-f", "wav", wav16_path],
 587 |                 capture_output=True, text=True, timeout=30,
 588 |             )
 589 |             try:
 590 |                 os.remove(wav24_path)
 591 |             except OSError:
 592 |                 pass
 593 |             if r.returncode == 0 and os.path.exists(wav16_path) and os.path.getsize(wav16_path) > 1000:
 594 |                 # Loudnorm to -14 LUFS for consistent volume
 595 |                 norm_path = wav16_path + "_norm.wav"
 596 |                 subprocess.run(
 597 |                     ["ffmpeg", "-y", "-loglevel", "error", "-i", wav16_path,
 598 |                      "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
 599 |                      "-ar", "16000", "-ac", "1", norm_path],
 600 |                     capture_output=True, text=True, timeout=30,
 601 |                 )
 602 |                 if os.path.exists(norm_path) and os.path.getsize(norm_path) > 1000:
 603 |                     with open(norm_path, "rb") as f:
 604 |                         wav_bytes = f.read()
 605 |                     try:
 606 |                         os.remove(norm_path)
 607 |                     except OSError:
 608 |                         pass
 609 |                 else:
 610 |                     # Loudnorm failed, use unnormalized
 611 |                     with open(wav16_path, "rb") as f:
 612 |                         wav_bytes = f.read()
 613 |                 try:
 614 |                     os.remove(wav16_path)
 615 |                 except OSError:
 616 |                     pass
 617 |                 elapsed = time.time() - t0
 618 |                 logger.info(f"[AVATAR_TTS] Kokoro af_heart OK: {elapsed:.2f}s ({len(wav_bytes)} bytes)")
 619 |                 return wav_bytes
 620 |             else:
 621 |                 logger.warning("[AVATAR_TTS] Kokoro ffmpeg resample failed")
 622 |         except Exception as e:
 623 |             logger.error(f"[AVATAR_TTS] Kokoro FAILED: {e} → ElevenLabs fallback")
 624 |     else:
 625 |         logger.info("[AVATAR_TTS] Kokoro not ready → ElevenLabs fallback")
 626 | 
 627 |     # Fallback: ElevenLabs
 628 |     t0 = time.time()
 629 |     audio_bytes = text_to_speech(text)
 630 |     elapsed = time.time() - t0
 631 |     logger.info(f"[AVATAR_TTS] ElevenLabs fallback: {elapsed:.2f}s ({len(audio_bytes)} bytes)")
 632 |     return audio_bytes
 633 | 
 634 | 
 635 | def text_to_speech(text, voice_id="cgSgspJ2msm6clMCkdW9"):
 636 |     """Call ElevenLabs TTS API. Returns raw audio bytes (mp3)."""
 637 |     api_key = os.environ.get("ELEVENLABS_API_KEY", "")
 638 |     if not api_key:
 639 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
 640 |         if os.path.exists(env_path):
 641 |             for line in open(env_path):
 642 |                 if line.startswith("ELEVENLABS_API_KEY="):
 643 |                     api_key = line.strip().split("=", 1)[1].strip().strip("\"'")
 644 |     if not api_key:
 645 |         raise ValueError("ELEVENLABS_API_KEY not found in environment or .env")
 646 |     resp = http_requests.post(
 647 |         f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
 648 |         headers={"xi-api-key": api_key, "Content-Type": "application/json"},
 649 |         json={
 650 |             "text": text,
 651 |             "model_id": "eleven_turbo_v2_5",
 652 |             # LAW 3: Jessica voice settings — stability=0.45, similarity_boost=0.75, style=0.20
 653 |             "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.20},
 654 |         },
 655 |         timeout=60,
 656 |     )
 657 |     if resp.status_code != 200:
 658 |         raise Exception(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
 659 |     return resp.content
 660 | 
 661 | 
 662 | # ═══════════════════════════════════════════════════════════════════════
 663 | # FLASK ROUTES
 664 | # ═══════════════════════════════════════════════════════════════════════
 665 | 
 666 | @app.route("/health")
 667 | def health():
 668 |     """Enhanced health check with VRAM, latency, vision status, enhancer info."""
 669 |     reg = ModelRegistry.get() if ModelRegistry.is_loaded() else None
 670 |     vram = reg.vram_info() if reg else {"available": False}
 671 | 
 672 |     vision_enabled = bool(os.environ.get("GEMINI_API_KEY"))
 673 |     with _lock:
 674 |         avg_latency = round(sum(_request_times) / len(_request_times), 2) if _request_times else None
 675 |         tracked = len(_request_times)
 676 |     uptime = round(time.time() - _start_time, 1)
 677 | 
 678 |     return jsonify({
 679 |         "status": "ok",
 680 |         "engine": "wav2lip-gan-fp16-v2",
 681 |         "enhancements": ["fp16", "cached_face", "cv2_sharpen", "mediapipe_blinks", "head_movement"],
 682 |         "device": DEVICE,
 683 |         "model_loaded": reg is not None and reg.wav2lip_model is not None,
 684 |         "avatar_loaded": reg is not None and reg.avatar_face is not None,
 685 |         "avatar_size": (
 686 |             f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}"
 687 |             if reg and reg.avatar_face is not None else None
 688 |         ),
 689 |         "face_detected": reg is not None and reg.avatar_face_coords is not None,
 690 |         "face_enhancer": "cv2_sharpen_only",
 691 |         "blinks_enabled": True,  # v2 engine: cached landmarks
 692 |         "eye_landmarks_detected": (lambda: __import__("blink_engine")._load_cache() is not None)(),
 693 |         "vram": vram,
 694 |         "vision_enabled": vision_enabled,
 695 |         "uptime_sec": uptime,
 696 |         "avg_latency_sec": avg_latency,
 697 |         "requests_tracked": tracked,
 698 |         "output_fps": DEFAULT_FPS,
 699 |         "batch_size": BATCH_SIZE,
 700 |         "max_audio_seconds": MAX_AUDIO_SECONDS,
 701 |         "encoding": "crf28-ultrafast-512",
 702 |         "blink_config": {
 703 |             "interval": f"{BLINK_INTERVAL_MIN}-{BLINK_INTERVAL_MAX}s",
 704 |             "duration": f"{BLINK_DURATION}s"
 705 |         },
 706 |         "head_movement_config": {
 707 |             "rotation": f"\u00b1{HEAD_ROTATION_AMPLITUDE}\u00b0",
 708 |             "period": f"{HEAD_PERIOD}s"
 709 |         }
 710 |     })
 711 | 
 712 | 
 713 | @app.route("/status")
 714 | def status():
 715 |     """Alias for /health — frontend expects this route."""
 716 |     return health()
 717 | 
 718 | 
 719 | @app.route("/warmup", methods=["POST"])
 720 | def warmup():
 721 |     """Generate a tiny test video to warm up torch.compile and CUDA kernels."""
 722 |     t0 = time.time()
 723 |     reg = ModelRegistry.get()
 724 |     if reg.wav2lip_model is None:
 725 |         return jsonify({"error": "Model not loaded"}), 500
 726 | 
 727 |     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
 728 |         import wave
 729 |         with wave.open(tmp.name, "w") as wf:
 730 |             wf.setnchannels(1)
 731 |             wf.setsampwidth(2)
 732 |             wf.setframerate(16000)
 733 |             wf.writeframes(b"\x00\x00" * 8000)
 734 |         wav_path = tmp.name
 735 | 
 736 |     try:
 737 |         _render_semaphore.acquire()
 738 |         try:
 739 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
 740 |             if frames:
 741 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
 742 |         finally:
 743 |             _render_semaphore.release()
 744 |         elapsed = time.time() - t0
 745 |         logger.info(f"Warmup complete: {len(frames)} frames in {elapsed:.2f}s")
 746 |         return jsonify({
 747 |             "status": "warmed_up",
 748 |             "frames": len(frames),
 749 |             "warmup_time": round(elapsed, 2),
 750 |             "vram": reg.vram_info(),
 751 |         })
 752 |     except Exception as e:
 753 |         logger.error(f"Warmup error: {e}", exc_info=True)
 754 |         return jsonify({"error": str(e)}), 500
 755 |     finally:
 756 |         try:
 757 |             os.unlink(wav_path)
 758 |         except OSError:
 759 |             pass
 760 | 
 761 | 
 762 | @app.route("/generate", methods=["POST"])
 763 | def generate():
 764 |     """Generate lip-synced video with face restoration, blinks, and head movement.
 765 | 
 766 |     Accepts two modes:
 767 |       Mode A: {"text": "..."} -> Kokoro af_heart (or ElevenLabs fallback) -> Wav2Lip -> video
 768 |       Mode B: {"audio_base64": "...", "content_type": "..."} -> Wav2Lip -> video
 769 |     """
 770 |     data = request.get_json()
 771 |     if not data:
 772 |         return jsonify({"error": "JSON body required"}), 400
 773 | 
 774 |     enable_blinks = data.get("enable_blinks", True)  # v2 blink engine enabled
 775 |     enable_head_movement = data.get("enable_head_movement", True)
 776 |     fps = float(data.get("fps", DEFAULT_FPS))
 777 |     avatar_source = data.get("avatar_source", "default")
 778 |     if avatar_source not in AVATAR_SOURCES:
 779 |         avatar_source = "default"
 780 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
 781 | 
 782 |     # Resolve face for this render
 783 |     gen_face, gen_coords, _gen_eyes = _load_avatar_face(avatar_source)
 784 |     if gen_face is None or gen_coords is None:
 785 |         gen_face, gen_coords, _gen_eyes = _load_avatar_face("default")
 786 | 
 787 |     t_start = time.time()
 788 | 
 789 |     # Mode A: text -> Kokoro af_heart (primary) or ElevenLabs (fallback)
 790 |     if "text" in data:
 791 |         try:
 792 |             t_tts = time.time()
 793 |             audio_bytes = _avatar_tts(data["text"])
 794 |             logger.info(f"TTS: {len(audio_bytes)} bytes in {time.time()-t_tts:.2f}s")
 795 |         except Exception as e:
 796 |             logger.error(f"TTS error: {e}")
 797 |             return jsonify({"error": f"TTS failed: {e}"}), 500
 798 |         # Kokoro returns WAV, ElevenLabs returns MP3 — detect from header
 799 |         content_type = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
 800 |     # Mode B: raw audio
 801 |     elif "audio_base64" in data:
 802 |         audio_bytes = base64.b64decode(data["audio_base64"])
 803 |         content_type = data.get("content_type", "audio/mpeg")
 804 |     else:
 805 |         return jsonify({"error": "text or audio_base64 required"}), 400
 806 | 
 807 |     ext = ".mp3" if "mpeg" in content_type else ".wav"
 808 | 
 809 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
 810 |         tmp.write(audio_bytes)
 811 |         audio_path = tmp.name
 812 | 
 813 |     wav_path = audio_path + "_16k.wav"
 814 |     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
 815 | 
 816 |     # Input length guard: check audio duration
 817 |     try:
 818 |         import subprocess as _sp
 819 |         probe = _sp.run(
 820 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 821 |              "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
 822 |             capture_output=True, text=True, timeout=10,
 823 |         )
 824 |         audio_duration_sec = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
 825 |     except Exception:
 826 |         audio_duration_sec = 0.0
 827 | 
 828 |     if audio_duration_sec > MAX_AUDIO_SECONDS:
 829 |         logger.warning(f"Audio too long ({audio_duration_sec:.1f}s > {MAX_AUDIO_SECONDS}s) — rejecting")
 830 |         return jsonify({
 831 |             "error": f"Audio too long ({audio_duration_sec:.1f}s). Max {MAX_AUDIO_SECONDS}s.",
 832 |             "code": "AUDIO_TOO_LONG",
 833 |             "max_seconds": MAX_AUDIO_SECONDS,
 834 |         }), 400
 835 | 
 836 |     try:
 837 |         reg = ModelRegistry.get()
 838 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
 839 |         if not acquired:
 840 |             return jsonify({"error": "GPU busy", "code": "GPU_BUSY", "retry_after": 5}), 503
 841 |         try:
 842 |             t0 = time.time()
 843 |             frames = wav2lip_generate(wav_path, fps, avatar_face=gen_face, avatar_face_coords=gen_coords)
 844 |             t_lip = time.time() - t0
 845 |             logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")
 846 | 
 847 |             # CV2 sharpen only — no GFPGAN
 848 |             t_enhance = 0.0
 849 |             if len(frames) > 0:
 850 |                 try:
 851 |                     t0_enh = time.time()
 852 |                     frames = sharpen_mouth_region(frames, gen_coords)
 853 |                     t_enhance = time.time() - t0_enh
 854 |                     logger.info(f"CV2 sharpen: {t_enhance:.2f}s")
 855 |                 except Exception as e:
 856 |                     logger.warning(f"Sharpen skipped: {e}")
 857 | 
 858 |             t0 = time.time()
 859 |             if enable_blinks or enable_head_movement:
 860 |                 frames = post_process_frames(
 861 |                     frames, fps,
 862 |                     enable_blinks=enable_blinks,
 863 |                     enable_head=enable_head_movement,
 864 |                 )
 865 |             t_post = time.time() - t0
 866 |             logger.info(f"Post-processing: {t_post:.2f}s")
 867 | 
 868 |             t0 = time.time()
 869 |             video_path = frames_to_video(frames, fps, audio_path=wav_path)
 870 |             t_encode = time.time() - t0
 871 |             logger.info(f"Encoding: {t_encode:.2f}s")
 872 |         finally:
 873 |             _render_semaphore.release()
 874 | 
 875 |         if not video_path:
 876 |             return jsonify({"error": "Video encoding failed", "code": "ENCODE_FAILED"}), 500
 877 | 
 878 |         t_total = time.time() - t_start
 879 |         _record_latency(t_total)
 880 |         duration = len(frames) / fps
 881 |         num_frames = len(frames)
 882 | 
 883 |         logger.info(
 884 |             f"Complete: {duration:.1f}s video, {num_frames} frames, "
 885 |             f"lip={t_lip:.1f}s enhance={t_enhance:.1f}s post={t_post:.1f}s enc={t_encode:.1f}s total={t_total:.1f}s"
 886 |         )
 887 | 
 888 |         cleanup_paths = [audio_path, wav_path, video_path]
 889 | 
 890 |         @after_this_request
 891 |         def _cleanup(response):
 892 |             for p in cleanup_paths:
 893 |                 try:
 894 |                     if p and os.path.exists(p):
 895 |                         os.unlink(p)
 896 |                 except OSError:
 897 |                     pass
 898 |             return response
 899 | 
 900 |         response = send_file(
 901 |             video_path,
 902 |             mimetype="video/mp4",
 903 |             as_attachment=True,
 904 |             download_name="oracle.mp4",
 905 |         )
 906 |         response.headers["X-Duration"] = str(round(duration, 2))
 907 |         response.headers["X-Frames"] = str(num_frames)
 908 |         response.headers["X-Processing-Time"] = str(round(t_total, 2))
 909 |         response.headers["X-Timing-Wav2Lip"] = str(round(t_lip, 2))
 910 |         response.headers["X-Timing-FaceEnhance"] = str(round(t_enhance, 2))
 911 |         response.headers["X-Timing-PostProcess"] = str(round(t_post, 2))
 912 |         response.headers["X-Timing-Encoding"] = str(round(t_encode, 2))
 913 |         return response
 914 | 
 915 |     except Exception as e:
 916 |         logger.error(f"Generation error: {e}", exc_info=True)
 917 |         return jsonify({"error": str(e), "code": "GENERATION_ERROR"}), 500
 918 |     finally:
 919 |         for p in [audio_path, wav_path]:
 920 |             try:
 921 |                 if os.path.exists(p):
 922 |                     os.unlink(p)
 923 |             except OSError:
 924 |                 pass
 925 | 
 926 | 
 927 | @app.route("/reload-avatar", methods=["POST"])
 928 | def reload_avatar():
 929 |     """Reload avatar source image via ModelRegistry."""
 930 |     reg = ModelRegistry.get()
 931 |     if reg.reload_avatar():
 932 |         return jsonify({
 933 |             "status": "reloaded",
 934 |             "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
 935 |             "face": reg.avatar_face_coords,
 936 |             "eye_landmarks": reg.eye_landmarks is not None,
 937 |         })
 938 |     else:
 939 |         return jsonify({"error": "No face detected in new image"}), 400
 940 | 
 941 | 
 942 | @app.route("/source-image")
 943 | def source_image():
 944 |     """Serve the current avatar source image."""
 945 |     reg = ModelRegistry.get()
 946 |     if reg.avatar_face is None:
 947 |         return jsonify({"error": "No avatar loaded"}), 404
 948 |     _, buf = cv2.imencode(".png", reg.avatar_face)
 949 |     b64 = base64.b64encode(buf).decode()
 950 |     return jsonify({
 951 |         "image_base64": b64,
 952 |         "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
 953 |         "face_coords": reg.avatar_face_coords
 954 |     })
 955 | 
 956 | 
 957 | # ═══════════════════════════════════════════════════════════════════════
 958 | # VISION GUIDE ENDPOINTS
 959 | # ═══════════════════════════════════════════════════════════════════════
 960 | 
 961 | @app.route("/vision/analyze", methods=["POST"])
 962 | def vision_analyze():
 963 |     """Analyze a Bitcoin hardware image with Gemini 2.5 Flash."""
 964 |     data = request.get_json()
 965 |     if not data or not data.get("image_base64"):
 966 |         return jsonify({"error": "image_base64 required"}), 400
 967 | 
 968 |     # Strip data URL prefix if present (client may send data:image/...;base64,)
 969 |     image_b64 = data["image_base64"]
 970 |     if image_b64.startswith("data:"):
 971 |         image_b64 = image_b64.split(",", 1)[1]
 972 | 
 973 |     from vision_guide import analyze_image, GuideSession
 974 |     result = analyze_image(
 975 |         image_b64=image_b64,
 976 |         mime_type=data.get("mime_type", "image/jpeg"),
 977 |         context=data.get("context", ""),
 978 |     )
 979 | 
 980 |     if "error" in result:
 981 |         return jsonify(result), 500
 982 | 
 983 |     # Create a GuideSession so follow-up /vision/guide calls have context
 984 |     guide_session = GuideSession.get_or_create(data.get("session_id"))
 985 |     result["session_id"] = guide_session.session_id
 986 | 
 987 |     # Seed the guide session history with this first analysis
 988 |     guide_session.history.append({
 989 |         "role": "user",
 990 |         "parts": [
 991 |             {"text": data.get("context", "Analyze this Bitcoin hardware image.")},
 992 |             {"inlineData": {"mimeType": data.get("mime_type", "image/jpeg"), "data": image_b64}},
 993 |         ],
 994 |     })
 995 |     guidance = result.get("guidance_text", "")
 996 |     if guidance:
 997 |         guide_session.history.append({
 998 |             "role": "model",
 999 |             "parts": [{"text": guidance}],
1000 |         })
1001 |     if result.get("device_name") and result["device_name"] != "unknown":
1002 |         guide_session.device_name = result["device_name"]
1003 | 
1004 |     # Phase 4: Store vision context in dialogue session for carry-forward
1005 |     session_id = data.get("session_id", "anon")
1006 |     try:
1007 |         from oracle_dialogue_engine import _get_session
1008 |         session = _get_session(session_id)
1009 |         vision_history = session.get("vision_history", [])
1010 |         analysis_summary = result.get("summary", "") or str(result.get("device_name", ""))
1011 |         if result.get("current_step"):
1012 |             analysis_summary += f" — {result['current_step']}"
1013 |         vision_history.append({
1014 |             "turn": session.get("turn", 0),
1015 |             "summary": analysis_summary[:200],
1016 |         })
1017 |         session["vision_history"] = vision_history[-3:]  # keep last 3
1018 |     except Exception as e:
1019 |         logger.warning(f"[VISION] Failed to store vision context: {e}")
1020 | 
1021 |     return jsonify(result)
1022 | 
1023 | 
1024 | @app.route("/vision/guide", methods=["POST"])
1025 | def vision_guide():
1026 |     """Multi-turn hardware setup guide session."""
1027 |     data = request.get_json()
1028 |     if not data:
1029 |         return jsonify({"error": "JSON body required"}), 400
1030 | 
1031 |     from vision_guide import GuideSession
1032 |     session = GuideSession.get_or_create(data.get("session_id"))
1033 | 
1034 |     if data.get("image_base64"):
1035 |         # Strip data URL prefix if present
1036 |         img_b64 = data["image_base64"]
1037 |         if img_b64.startswith("data:"):
1038 |             img_b64 = img_b64.split(",", 1)[1]
1039 |         question = data.get("question", "")
1040 |         last_context = data.get("last_context", "")
1041 |         if last_context:
1042 |             question += f"\n\nUser completed these steps: {last_context}\nNow showing the next screen."
1043 |         result = session.send_image(
1044 |             image_b64=img_b64,
1045 |             mime_type=data.get("mime_type", "image/jpeg"),
1046 |             question=question,
1047 |         )
1048 |     elif data.get("question"):
1049 |         result = session.send_text(data["question"])
1050 |     else:
1051 |         return jsonify({"error": "image_base64 or question required"}), 400
1052 | 
1053 |     if "error" in result:
1054 |         return jsonify(result), 500
1055 |     return jsonify(result)
1056 | 
1057 | 
1058 | @app.route("/vision/status")
1059 | def vision_status():
1060 |     """Check if vision features are enabled."""
1061 |     gemini_key = os.environ.get("GEMINI_API_KEY", "")
1062 |     enabled = bool(gemini_key)
1063 |     if enabled:
1064 |         return jsonify({
1065 |             "status": "enabled",
1066 |             "model": "gemini-2.5-flash",
1067 |             "endpoints": ["/vision/analyze", "/vision/guide", "/vision/sessions"],
1068 |         })
1069 |     else:
1070 |         return jsonify({
1071 |             "status": "disabled",
1072 |             "reason": "GEMINI_API_KEY not configured",
1073 |             "setup_url": "https://aistudio.google.com/apikey",
1074 |         })
1075 | 
1076 | 
1077 | @app.route("/vision/sessions")
1078 | def vision_sessions():
1079 |     """List active vision guide sessions."""
1080 |     from vision_guide import GuideSession
1081 |     return jsonify({
1082 |         "active_sessions": GuideSession.active_count(),
1083 |     })
1084 | 
1085 | 
1086 | # ═══════════════════════════════════════════════════════════════════════
1087 | # STREAMING PIPELINE
1088 | # ═══════════════════════════════════════════════════════════════════════
1089 | 
1090 | import re
1091 | import uuid
1092 | import subprocess
1093 | 
1094 | ORACLE_SYSTEM_PROMPT = (
1095 |     "You are the Oracle — Protocol Pulse's personal Bitcoin intelligence guide. "
1096 |     "You are having a private one-on-one conversation with a visitor. "
1097 |     "You are an EDUCATOR (explain Bitcoin at any level), GUIDE (help navigate Protocol Pulse), "
1098 |     "TECHNICAL ASSISTANT (wallets, self-custody, nodes, hardware), and INTELLIGENCE ANALYST "
1099 |     "(market state, price action — conversational, not broadcast). "
1100 |     "TONE: Warm but sharp. Knowledgeable without being condescending. "
1101 |     "Like the smartest person in Bitcoin who actually has time for you. "
1102 |     "Keep responses under 3 sentences. Never say 'As an AI' or offer daily briefs unprompted. "
1103 |     "You are NOT a news anchor or briefing bot — you are a personal guide."
1104 | )
1105 | ORACLE_VOICE_ID = "cgSgspJ2msm6clMCkdW9"  # Jessica
1106 | ORACLE_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
1107 | ORACLE_IDLE_PATH = os.path.join(ORACLE_STATIC_DIR, "oracle_idle.mp4")
1108 | 
1109 | _stream_sessions = {}
1110 | _stream_lock = threading.Lock()
1111 | 
1112 | 
1113 | def _get_anthropic_key():
1114 |     """Get Anthropic API key from env or .env file."""
1115 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
1116 |     if not key:
1117 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
1118 |         if os.path.exists(env_path):
1119 |             for line in open(env_path):
1120 |                 if line.startswith("ANTHROPIC_API_KEY="):
1121 |                     key = line.strip().split("=", 1)[1].strip().strip("\"'")
1122 |     return key
1123 | 
1124 | 
1125 | def _split_sentences(text):
1126 |     """Split text into sentences for chunked processing."""
1127 |     sentences = re.split(r'(?<=[.!?])\s+', text.strip())
1128 |     return [s for s in sentences if s.strip()]
1129 | 
1130 | 
1131 | def _generate_chunk(sentence, chunk_num, session_dir, fps=30.0):
1132 |     """Generate a single video chunk for a sentence: TTS -> Wav2Lip -> MP4."""
1133 |     try:
1134 |         audio_bytes = _avatar_tts(sentence)
1135 |         is_wav = audio_bytes[:4] == b"RIFF"
1136 |         ext = ".wav" if is_wav else ".mp3"
1137 |         audio_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}{ext}")
1138 |         with open(audio_path, "wb") as f:
1139 |             f.write(audio_bytes)
1140 | 
1141 |         wav_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}_16k.wav")
1142 |         if is_wav:
1143 |             # F5 already returned 16kHz mono WAV — just copy
1144 |             import shutil
1145 |             shutil.copy2(audio_path, wav_path)
1146 |         else:
1147 |             subprocess.run(
1148 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
1149 |                 check=True, capture_output=True,
1150 |             )
1151 | 
1152 |         _render_semaphore.acquire()
1153 |         try:
1154 |             frames = wav2lip_generate(wav_path, fps)
1155 |             reg = ModelRegistry.get()
1156 |             try:
1157 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1158 |             except Exception:
1159 |                 pass
1160 |             frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1161 |         finally:
1162 |             _render_semaphore.release()
1163 | 
1164 |         video_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}.mp4")
1165 |         tmp_path = frames_to_video(frames, fps, audio_path=wav_path)
1166 |         if tmp_path:
1167 |             os.rename(tmp_path, video_path)
1168 |             return video_path
1169 |         return None
1170 |     except Exception as e:
1171 |         logger.error(f"Chunk {chunk_num} generation error: {e}", exc_info=True)
1172 |         return None
1173 | 
1174 | 
1175 | def _stream_worker(session_id, text):
1176 |     """Background worker: call Claude -> split sentences -> generate chunks."""
1177 |     session = _stream_sessions.get(session_id)
1178 |     if not session:
1179 |         return
1180 | 
1181 |     try:
1182 |         api_key = _get_anthropic_key()
1183 |         if not api_key:
1184 |             logger.warning("No Anthropic key — using input text as-is")
1185 |             ai_text = text
1186 |         else:
1187 |             resp = http_requests.post(
1188 |                 "https://api.anthropic.com/v1/messages",
1189 |                 headers={
1190 |                     "x-api-key": api_key,
1191 |                     "anthropic-version": "2023-06-01",
1192 |                     "content-type": "application/json",
1193 |                 },
1194 |                 json={
1195 |                     "model": "claude-sonnet-4-20250514",
1196 |                     "max_tokens": 80,  # Short transcript = fewer TTS seconds = fewer Wav2Lip frames
1197 |                     "system": ORACLE_SYSTEM_PROMPT,
1198 |                     "messages": [{"role": "user", "content": text}],
1199 |                 },
1200 |                 timeout=30,
1201 |             )
1202 |             if resp.status_code == 200:
1203 |                 ai_text = resp.json()["content"][0]["text"]
1204 |             else:
1205 |                 logger.error(f"Claude API error {resp.status_code}: {resp.text[:200]}")
1206 |                 ai_text = text
1207 | 
1208 |         session["ai_response"] = ai_text
1209 |         sentences = _split_sentences(ai_text)
1210 |         session["total_chunks"] = len(sentences)
1211 | 
1212 |         session_dir = session["dir"]
1213 |         for i, sentence in enumerate(sentences):
1214 |             chunk_path = _generate_chunk(sentence, i, session_dir)
1215 |             if chunk_path:
1216 |                 session["chunks_ready"].append(chunk_path)
1217 |             else:
1218 |                 session["errors"].append(f"Chunk {i} failed")
1219 | 
1220 |         session["status"] = "complete"
1221 | 
1222 |     except Exception as e:
1223 |         logger.error(f"Stream worker error: {e}", exc_info=True)
1224 |         session["status"] = "error"
1225 |         session["errors"].append(str(e))
1226 | 
1227 | 
1228 | @app.route("/generate_stream", methods=["POST"])
1229 | def generate_stream():
1230 |     """Start streaming generation: text -> Claude -> sentence chunks -> video chunks."""
1231 |     data = request.get_json()
1232 |     if not data or not data.get("text"):
1233 |         return jsonify({"error": "text required"}), 400
1234 | 
1235 |     session_id = str(uuid.uuid4())[:12]
1236 |     session_dir = os.path.join(tempfile.gettempdir(), f"oracle_stream_{session_id}")
1237 |     os.makedirs(session_dir, exist_ok=True)
1238 | 
1239 |     session = {
1240 |         "id": session_id,
1241 |         "status": "processing",
1242 |         "text": data["text"],
1243 |         "ai_response": None,
1244 |         "total_chunks": 0,
1245 |         "chunks_ready": [],
1246 |         "errors": [],
1247 |         "dir": session_dir,
1248 |         "created": time.time(),
1249 |     }
1250 | 
1251 |     with _stream_lock:
1252 |         _stream_sessions[session_id] = session
1253 | 
1254 |     thread = threading.Thread(target=_stream_worker, args=(session_id, data["text"]), daemon=True)
1255 |     thread.start()
1256 | 
1257 |     return jsonify({
1258 |         "session_id": session_id,
1259 |         "status": "processing",
1260 |         "message": "Stream generation started. Poll /stream_status/{session_id} for progress.",
1261 |     })
1262 | 
1263 | 
1264 | @app.route("/stream_status/<session_id>")
1265 | def stream_status(session_id):
1266 |     """Poll for streaming generation progress."""
1267 |     session = _stream_sessions.get(session_id)
1268 |     if not session:
1269 |         return jsonify({"error": "Session not found"}), 404
1270 | 
1271 |     return jsonify({
1272 |         "session_id": session_id,
1273 |         "status": session["status"],
1274 |         "ai_response": session.get("ai_response"),
1275 |         "chunks_ready": len(session["chunks_ready"]),
1276 |         "total_chunks": session["total_chunks"],
1277 |         "total_estimated": max(session["total_chunks"], 3),
1278 |         "errors": session["errors"],
1279 |     })
1280 | 
1281 | 
1282 | @app.route("/stream_chunk/<session_id>/<int:chunk_number>")
1283 | def stream_chunk(session_id, chunk_number):
1284 |     """Fetch a generated video chunk by number."""
1285 |     session = _stream_sessions.get(session_id)
1286 |     if not session:
1287 |         return jsonify({"error": "Session not found"}), 404
1288 | 
1289 |     if chunk_number >= len(session["chunks_ready"]):
1290 |         return jsonify({"error": "Chunk not ready yet"}), 404
1291 | 
1292 |     chunk_path = session["chunks_ready"][chunk_number]
1293 |     if not os.path.exists(chunk_path):
1294 |         return jsonify({"error": "Chunk file missing"}), 500
1295 | 
1296 |     return send_file(chunk_path, mimetype="video/mp4", as_attachment=True,
1297 |                      download_name=f"chunk_{chunk_number:03d}.mp4")
1298 | 
1299 | 
1300 | @app.route("/oracle_idle")
1301 | def oracle_idle():
1302 |     """Serve the pre-rendered idle loop video."""
1303 |     if os.path.exists(ORACLE_IDLE_PATH):
1304 |         return send_file(ORACLE_IDLE_PATH, mimetype="video/mp4")
1305 |     return jsonify({"error": "Idle video not generated yet"}), 404
1306 | 
1307 | 
1308 | def generate_idle_loop():
1309 |     """Generate a 4-second idle loop with blinks + head movement (no audio)."""
1310 |     os.makedirs(ORACLE_STATIC_DIR, exist_ok=True)
1311 |     if os.path.exists(ORACLE_IDLE_PATH):
1312 |         logger.info("Idle loop already exists, skipping generation")
1313 |         return
1314 | 
1315 |     logger.info("Generating idle loop video...")
1316 |     reg = ModelRegistry.get()
1317 |     if reg.avatar_face is None:
1318 |         logger.error("Cannot generate idle loop: no avatar loaded")
1319 |         return
1320 | 
1321 |     fps = DEFAULT_FPS
1322 |     duration = 4.0
1323 |     num_frames = int(duration * fps)
1324 | 
1325 |     base_frame = reg.avatar_face.copy()
1326 |     frames = [base_frame.copy() for _ in range(num_frames)]
1327 | 
1328 |     frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1329 | 
1330 |     video_path = frames_to_video(frames, fps, audio_path=None)
1331 |     if video_path:
1332 |         os.rename(video_path, ORACLE_IDLE_PATH)
1333 |         logger.info(f"Idle loop saved: {ORACLE_IDLE_PATH} ({num_frames} frames)")
1334 |     else:
1335 |         logger.error("Failed to generate idle loop")
1336 | 
1337 | 
1338 | # ═══════════════════════════════════════════════════════════════════════
1339 | # ORACLE PRE-CACHE + INTELLIGENCE ENDPOINTS
1340 | # ═══════════════════════════════════════════════════════════════════════
1341 | 
1342 | import oracle_cache_manager
1343 | import oracle_intelligence_feed
1344 | import oracle_dialogue_engine
1345 | 
1346 | # Intent classification — keyword matching
1347 | INTENT_PATTERNS = {
1348 |     "DAILY_BRIEF": r"brief|today|news|happening|what's|latest",
1349 |     "SOVEREIGNTY_INTRO": r"sovereign|score|free",
1350 |     "SOVEREIGNTY_COLD_WALLET": r"cold.?wallet|hardware|ledger|coldcard|custody",
1351 |     "SOVEREIGNTY_NODE": r"node|umbrel|raspberry|verify",
1352 |     "SOVEREIGNTY_BITAXE": r"bitaxe|mine|mining|solo",
1353 |     "SOVEREIGNTY_LIFE_INSURANCE": r"insurance|meanwhile|estate|death",
1354 |     "SOVEREIGNTY_RESIDENCY": r"residency|palau|rns|passport|citizenship",
1355 |     "GOODBYE": r"bye|goodbye|later|thanks",
1356 | }
1357 | 
1358 | 
1359 | def classify_intent(transcript):
1360 |     """Classify user transcript to an intent key. Returns (intent, confidence)."""
1361 |     text = transcript.lower().strip()
1362 |     for intent, pattern in INTENT_PATTERNS.items():
1363 |         if re.search(pattern, text):
1364 |             return intent, 0.85
1365 |     return "UNKNOWN", 0.4
1366 | 
1367 | 
1368 | @app.route("/oracle/cache/status")
1369 | def oracle_cache_status():
1370 |     """Return status of pre-cached responses and daily brief."""
1371 |     cache_status = oracle_cache_manager.get_cache_status()
1372 |     daily_brief = oracle_intelligence_feed.get_daily_brief()
1373 |     return jsonify({
1374 |         "cached_responses": cache_status,
1375 |         "daily_brief_ready": daily_brief is not None,
1376 |         "daily_brief_path": daily_brief,
1377 |         "cache_ttl_s": oracle_cache_manager.CACHE_TTL,
1378 |     })
1379 | 
1380 | 
1381 | @app.route("/oracle/response/<key>")
1382 | def oracle_response(key):
1383 |     """Serve pre-cached mp4 for a response key."""
1384 |     key = key.upper()
1385 |     if key not in oracle_cache_manager.RESPONSE_TREE and key != "DAILY_BRIEF_LIVE":
1386 |         return jsonify({"error": "Unknown response key", "valid_keys": list(oracle_cache_manager.RESPONSE_TREE.keys())}), 404
1387 | 
1388 |     # Daily brief special case
1389 |     if key == "DAILY_BRIEF_LIVE":
1390 |         path = oracle_intelligence_feed.get_daily_brief()
1391 |         if path:
1392 |             return send_file(path, mimetype="video/mp4")
1393 |         return jsonify({"error": "Daily brief not ready yet", "status": "pending"}), 202
1394 | 
1395 |     # Check if rendering
1396 |     if oracle_cache_manager.is_rendering(key):
1397 |         return jsonify({"error": "Response is being rendered", "status": "rendering"}), 202
1398 | 
1399 |     path = oracle_cache_manager.get_cached_response(key)
1400 |     if path:
1401 |         return send_file(path, mimetype="video/mp4")
1402 | 
1403 |     return jsonify({"error": "Response not cached yet", "status": "pending"}), 202
1404 | 
1405 | 
1406 | @app.route("/oracle/speak", methods=["POST"])
1407 | def oracle_speak():
1408 |     """Serve cached response for an intent, or fallback to /generate."""
1409 |     data = request.get_json()
1410 |     if not data or not data.get("intent"):
1411 |         return jsonify({"error": "intent required"}), 400
1412 | 
1413 |     intent = data["intent"].upper()
1414 | 
1415 |     # Try daily brief
1416 |     if intent == "DAILY_BRIEF":
1417 |         brief_path = oracle_intelligence_feed.get_daily_brief()
1418 |         if brief_path:
1419 |             return send_file(brief_path, mimetype="video/mp4")
1420 |         # Fallback to intro
1421 |         intent = "DAILY_BRIEF_INTRO"
1422 | 
1423 |     # If caller provided explicit text, use it directly (broadcast segments, custom scripts)
1424 |     caller_text = (data.get("text") or "").strip()
1425 |     if caller_text:
1426 |         return generate_inline(caller_text)
1427 | 
1428 |     # Try cached response
1429 |     path = oracle_cache_manager.get_cached_response(intent)
1430 |     if path:
1431 |         return send_file(path, mimetype="video/mp4")
1432 | 
1433 |     # Fallback: generate on the fly — but don't block if GPU is busy (cache warming)
1434 |     text = oracle_cache_manager.RESPONSE_TREE.get(intent)
1435 |     if not text:
1436 |         text = oracle_cache_manager.RESPONSE_TREE["UNKNOWN_QUESTION"]
1437 | 
1438 |     # Non-blocking: bail fast if render semaphore is held (e.g. during cache warmup)
1439 |     if not _render_semaphore.acquire(timeout=5):
1440 |         return jsonify({"error": "GPU busy warming cache — try again shortly",
1441 |                         "status": "warming", "retry_after": 30}), 503
1442 |     _render_semaphore.release()  # release immediately — generate_inline will re-acquire
1443 | 
1444 |     return generate_inline(text)
1445 | 
1446 | 
1447 | def generate_inline(text):
1448 |     """Internal helper: generate a video from text and return it."""
1449 |     try:
1450 |         audio_bytes = _avatar_tts(text)
1451 |     except Exception as e:
1452 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1453 | 
1454 |     is_wav = audio_bytes[:4] == b"RIFF"
1455 |     ext = ".wav" if is_wav else ".mp3"
1456 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1457 |         tmp.write(audio_bytes)
1458 |         audio_path = tmp.name
1459 | 
1460 |     wav_path = audio_path + "_16k.wav"
1461 |     if is_wav:
1462 |         import shutil
1463 |         shutil.copy2(audio_path, wav_path)
1464 |     else:
1465 |         subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1466 | 
1467 |     try:
1468 |         # Check queue state for concurrency visibility
1469 |         with _render_queue_lock:
1470 |             _queue_pos = sum(1 for _ in range(2) if not _render_semaphore._value)
1471 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
1472 |         if not acquired:
1473 |             return jsonify({"error": "GPU busy — try again in a moment", "retry_after": 10,
1474 |                             "queue_position": _queue_pos}), 503
1475 |         try:
1476 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
1477 |             reg = ModelRegistry.get()
1478 |             try:
1479 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1480 |             except Exception:
1481 |                 pass
1482 |             frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1483 |             video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1484 |         finally:
1485 |             _render_semaphore.release()
1486 | 
1487 |         if not video_path:
1488 |             return jsonify({"error": "Video encoding failed"}), 500
1489 | 
1490 |         # Stream video as inline (not attachment) so browser plays it directly.
1491 |         # Generator pattern ensures file stays on disk until fully sent,
1492 |         # then cleans up. Fixes iOS mid-stream cutoff + double-unlink race.
1493 |         def _stream_and_cleanup():
1494 |             try:
1495 |                 with open(video_path, "rb") as vf:
1496 |                     while True:
1497 |                         chunk = vf.read(65536)
1498 |                         if not chunk:
1499 |                             break
1500 |                         yield chunk
1501 |             finally:
1502 |                 for p in [audio_path, wav_path, video_path]:
1503 |                     try:
1504 |                         if p and os.path.exists(p):
1505 |                             os.unlink(p)
1506 |                     except OSError:
1507 |                         pass
1508 | 
1509 |         from flask import Response
1510 |         return Response(
1511 |             _stream_and_cleanup(),
1512 |             mimetype="video/mp4",
1513 |             headers={
1514 |                 "Content-Disposition": "inline",
1515 |                 "X-Accel-Buffering": "no",
1516 |                 "Cache-Control": "no-cache",
1517 |             },
1518 |         )
1519 | 
1520 |     except Exception as e:
1521 |         logger.error(f"generate_inline error: {e}", exc_info=True)
1522 |         for p in [audio_path, wav_path]:
1523 |             try:
1524 |                 if os.path.exists(p): os.unlink(p)
1525 |             except OSError:
1526 |                 pass
1527 |         return jsonify({"error": str(e)}), 500
1528 | 
1529 | 
1530 | 
1531 | 
1532 | 
1533 | 
1534 | @app.route("/oracle/voice", methods=["POST"])
1535 | def oracle_voice():
1536 |     """
1537 |     Voice-only endpoint: text -> ElevenLabs TTS -> audio/mpeg.
1538 |     No Wav2Lip, no GPU. ~400ms vs ~14s for full video.
1539 |     Use for vision guidance, quick confirmations, non-visual responses.
1540 |     Body: {"text": "...", "voice_id": "optional"}
1541 |     """
1542 |     data = request.get_json()
1543 |     if not data or not data.get("text"):
1544 |         return jsonify({"error": "text required"}), 400
1545 | 
1546 |     text = data["text"].strip()
1547 | 
1548 |     try:
1549 |         t0 = time.time()
1550 |         audio_bytes = _avatar_tts(text)
1551 |         logger.info(f"[VOICE] TTS {len(audio_bytes)}B in {time.time()-t0:.2f}s")
1552 |     except Exception as e:
1553 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1554 | 
1555 |     # Loudnorm pass if not already normalized (WAV from Kokoro is already normalized in _avatar_tts,
1556 |     # but ElevenLabs MP3 fallback is not)
1557 |     is_wav = audio_bytes[:4] == b"RIFF"
1558 |     if not is_wav:
1559 |         try:
1560 |             with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as _tmp:
1561 |                 _tmp.write(audio_bytes)
1562 |                 _raw_path = _tmp.name
1563 |             _norm_path = _raw_path + "_norm.wav"
1564 |             _nr = subprocess.run(
1565 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", _raw_path,
1566 |                  "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
1567 |                  "-ar", "16000", "-ac", "1", _norm_path],
1568 |                 capture_output=True, text=True, timeout=30,
1569 |             )
1570 |             if _nr.returncode == 0 and os.path.exists(_norm_path) and os.path.getsize(_norm_path) > 1000:
1571 |                 with open(_norm_path, "rb") as _nf:
1572 |                     audio_bytes = _nf.read()
1573 |                 is_wav = True
1574 |             for _p in [_raw_path, _norm_path]:
1575 |                 try:
1576 |                     os.remove(_p)
1577 |                 except OSError:
1578 |                     pass
1579 |         except Exception as _ne:
1580 |             logger.warning(f"[VOICE] loudnorm failed (non-fatal): {_ne}")
1581 | 
1582 |     mime = "audio/wav" if is_wav else "audio/mpeg"
1583 | 
1584 |     from flask import Response
1585 |     return Response(
1586 |         audio_bytes,
1587 |         mimetype=mime,
1588 |         headers={
1589 |             "Content-Disposition": "inline",
1590 |             "Content-Length": str(len(audio_bytes)),
1591 |             "Cache-Control": "no-cache",
1592 |         },
1593 |     )
1594 | 
1595 | @app.route("/oracle/job/<job_id>")
1596 | def oracle_job_status(job_id):
1597 |     """Poll for async video render completion."""
1598 |     # Expire stale jobs (pending older than TTL, or completed older than 30s)
1599 |     now = time.time()
1600 |     with _render_jobs_lock:
1601 |         expired = []
1602 |         for k, v in _render_jobs.items():
1603 |             if v.get("completed_at"):
1604 |                 # Completed jobs: keep for 30s after completion
1605 |                 if now - v["completed_at"] > 30:
1606 |                     expired.append(k)
1607 |             elif now - v.get("created", 0) > _RENDER_JOB_TTL:
1608 |                 expired.append(k)
1609 |         for k in expired:
1610 |             del _render_jobs[k]
1611 |         job = _render_jobs.get(job_id)
1612 |     if not job:
1613 |         return jsonify({"status": "not_found"}), 404
1614 |     if job["status"] == "done":
1615 |         # Mark completed_at on first successful poll (keep job for 30s)
1616 |         if not job.get("completed_at"):
1617 |             with _render_jobs_lock:
1618 |                 if job_id in _render_jobs:
1619 |                     _render_jobs[job_id]["completed_at"] = time.time()
1620 |         video_bytes = job["video_bytes"]
1621 |         from flask import Response
1622 |         return Response(video_bytes, mimetype="video/mp4",
1623 |                         headers={"Content-Disposition": "inline", "Cache-Control": "no-cache"})
1624 |     if job["status"] == "error":
1625 |         # Mark completed_at for errors too
1626 |         if not job.get("completed_at"):
1627 |             with _render_jobs_lock:
1628 |                 if job_id in _render_jobs:
1629 |                     _render_jobs[job_id]["completed_at"] = time.time()
1630 |         return jsonify({"status": "error"}), 500
1631 |     return jsonify({"status": "pending"}), 202
1632 | 
1633 | 
1634 | @app.route("/oracle/job/<job_id>/audio")
1635 | def oracle_job_audio(job_id):
1636 |     """Return cached TTS audio from an async render job (avoids duplicate Kokoro call)."""
1637 |     with _render_jobs_lock:
1638 |         job = _render_jobs.get(job_id)
1639 |     if not job or not job.get("audio_bytes"):
1640 |         return jsonify({"error": "audio not ready"}), 404
1641 |     audio_bytes = job["audio_bytes"]
1642 |     mime = job.get("audio_mime", "audio/wav")
1643 |     from flask import Response
1644 |     return Response(audio_bytes, mimetype=mime,
1645 |                     headers={"Content-Disposition": "inline",
1646 |                              "Content-Length": str(len(audio_bytes)),
1647 |                              "Cache-Control": "no-cache"})
1648 | 
1649 | 
1650 | @app.route("/oracle/chat", methods=["POST"])
1651 | def oracle_chat():
1652 |     data = request.get_json()
1653 |     if not data or not data.get("text"):
1654 |         return jsonify({"error": "text required"}), 400
1655 |     text = data["text"].strip()
1656 |     session_id = data.get("session_id", "anon")
1657 |     audio_first = data.get("audio_first", False)
1658 |     avatar_source = data.get("avatar_source", "default")
1659 |     if avatar_source not in AVATAR_SOURCES:
1660 |         avatar_source = "default"
1661 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
1662 | 
1663 |     # ── Phase 3: Visitor fingerprint + memory ──────────────────────────
1664 |     from oracle_memory import make_fingerprint, load_visitor
1665 |     visitor_token = data.get("visitor_token", "anon")
1666 |     raw_ip = (request.headers.get("X-Forwarded-For", "") or request.remote_addr or "").split(",")[0].strip()
1667 |     ua = request.headers.get("User-Agent", "")
1668 |     fingerprint = make_fingerprint(raw_ip, ua, visitor_token)
1669 | 
1670 |     session = oracle_dialogue_engine._get_session(session_id)
1671 |     if session["turn"] == 0:
1672 |         memory = load_visitor(fingerprint)
1673 |         if memory:
1674 |             session["visitor_memory"] = memory
1675 |             logger.info(f"[MEMORY] Returning visitor — session #{memory['session_count']}")
1676 |             if memory.get("recent_turns"):
1677 |                 # Pre-warm session with last exchange so Oracle has context immediately
1678 |                 recent = memory["recent_turns"]
1679 |                 if recent:
1680 |                     last = recent[-1]
1681 |                     if last.get("user") and last.get("oracle"):
1682 |                         session["history"] = [
1683 |                             {"role": "user", "content": f"[PRIOR SESSION] {last['user']}"},
1684 |                             {"role": "assistant", "content": f"[PRIOR SESSION] {last['oracle']}"},
1685 |                         ]
1686 |                         logger.info(f"[MEMORY] Pre-warmed session with {len(recent)} prior turns")
1687 |     session["fingerprint"] = fingerprint
1688 | 
1689 |     _sess_turn = oracle_dialogue_engine.get_session_info(session_id).get("turn", 0)
1690 |     if data.get("use_cache_for_intents", True) and _sess_turn == 0:
1691 |         intent, confidence = classify_intent(text)
1692 |         if confidence >= 0.8 and intent != "UNKNOWN":
1693 |             path = oracle_cache_manager.get_cached_response(intent)
1694 |             if path:
1695 |                 logger.info(f"[CHAT] Cache hit {intent}")
1696 |                 return send_file(path, mimetype="video/mp4")
1697 |     elif _sess_turn > 0:
1698 |         logger.info(f"[CHAT] Cache skipped turn={_sess_turn}")
1699 |     live_intel = {}
1700 |     try:
1701 |         live_intel = oracle_dialogue_engine.get_live_intel()
1702 |     except Exception:
1703 |         pass
1704 |     page_context = data.get("page_context", None)
1705 |     result = oracle_dialogue_engine.generate_response(session_id, text, live_intel, page_context)
1706 |     logger.info(f"[CHAT] {session_id} t={result['turn']} p={result['personality']} ctx={page_context.get('type','?') if page_context else 'none'}: {result['text'][:50]}")
1707 | 
1708 |     # ── Background memory save — persist after every turn, not just on unload ──
1709 |     try:
1710 |         _fp = session.get("fingerprint")
1711 |         _hist = session.get("history", [])
1712 |         if _fp and len(_hist) >= 2:
1713 |             import threading as _mem_threading
1714 |             def _bg_save():
1715 |                 try:
1716 |                     from oracle_memory import save_visitor
1717 |                     _flow = session.get("setup_flow", {})
1718 |                     _prev = session.get("visitor_memory", {})
1719 |                     # Store last 3 user+oracle pairs as recent_turns
1720 |                     _turns = []
1721 |                     for i in range(0, min(6, len(_hist)), 2):
1722 |                         if i+1 < len(_hist):
1723 |                             _turns.append({
1724 |                                 "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1725 |                                 "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1726 |                             })
1727 |                     save_visitor(_fp, {
1728 |                         "personality": session.get("personality", "AMIABLE"),
1729 |                         "session_summaries": _prev.get("session_summaries", []),
1730 |                         "setup_device": _flow.get("device"),
1731 |                         "setup_step": _flow.get("step", 0),
1732 |                         "topics_seen": list(session.get("topics_discussed", [])),
1733 |                         "products_shown": list(session.get("products_mentioned", [])),
1734 |                         "recent_turns": list(reversed(_turns)),
1735 |                     })
1736 |                 except Exception as _se:
1737 |                     logger.debug(f"[MEMORY] bg save error: {_se}")
1738 |             _mem_threading.Thread(target=_bg_save, daemon=True).start()
1739 |     except Exception:
1740 |         pass
1741 | 
1742 |     if audio_first:
1743 |         # Phase A: return text immediately, fire video render in background
1744 |         job_id = uuid.uuid4().hex[:16]
1745 |         with _render_jobs_lock:
1746 |             _render_jobs[job_id] = {"status": "pending", "video_bytes": None, "created": time.time()}
1747 | 
1748 |         response_text = result["text"]
1749 | 
1750 |         def render_async(txt, jid, src_name="default"):
1751 |             logger.info(f"[RENDER_ASYNC] STARTED job {jid} source={src_name} text={txt[:60]}...")
1752 |             try:
1753 |                 # Resolve avatar source for this render
1754 |                 a_face, a_coords, _a_eyes = _load_avatar_face(src_name)
1755 |                 if a_face is None or a_coords is None:
1756 |                     logger.warning(f"[ASYNC RENDER] Avatar source '{src_name}' failed, falling back to default")
1757 |                     a_face, a_coords, _a_eyes = _load_avatar_face("default")
1758 | 
1759 |                 audio_bytes = _avatar_tts(txt)
1760 |                 # Cache audio in job dict so frontend can fetch it without calling Kokoro again
1761 |                 with _render_jobs_lock:
1762 |                     if jid in _render_jobs:
1763 |                         _render_jobs[jid]["audio_bytes"] = audio_bytes
1764 |                         _render_jobs[jid]["audio_mime"] = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
1765 |                 is_wav = audio_bytes[:4] == b"RIFF"
1766 |                 ext = ".wav" if is_wav else ".mp3"
1767 |                 with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1768 |                     tmp.write(audio_bytes)
1769 |                     audio_path = tmp.name
1770 |                 wav_path = audio_path + "_16k.wav"
1771 |                 if is_wav:
1772 |                     import shutil
1773 |                     shutil.copy2(audio_path, wav_path)
1774 |                 else:
1775 |                     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1776 |                 try:
1777 |                     acquired = _render_semaphore.acquire(timeout=60)
1778 |                     if not acquired:
1779 |                         logger.warning(f"[ASYNC RENDER] GPU busy for job {jid}")
1780 |                         with _render_jobs_lock:
1781 |                             if jid in _render_jobs:
1782 |                                 _render_jobs[jid] = {"status": "error", "video_bytes": None,
1783 |                                                      "created": time.time(), "code": "GPU_BUSY"}
1784 |                         return
1785 |                     try:
1786 |                         frames = wav2lip_generate(wav_path, DEFAULT_FPS, avatar_face=a_face, avatar_face_coords=a_coords)
1787 |                         try:
1788 |                             frames = sharpen_mouth_region(frames, a_coords)
1789 |                         except Exception:
1790 |                             pass
1791 |                         frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1792 |                         video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1793 |                     finally:
1794 |                         _render_semaphore.release()
1795 | 
1796 |                     if video_path and os.path.exists(video_path):
1797 |                         with open(video_path, "rb") as vf:
1798 |                             vbytes = vf.read()
1799 |                         os.unlink(video_path)
1800 |                         with _render_jobs_lock:
1801 |                             if jid in _render_jobs:
1802 |                                 _render_jobs[jid] = {"status": "done", "video_bytes": vbytes, "created": time.time()}
1803 |                     else:
1804 |                         with _render_jobs_lock:
1805 |                             if jid in _render_jobs:
1806 |                                 _render_jobs[jid]["status"] = "error"
1807 |                 finally:
1808 |                     for p in [audio_path, wav_path]:
1809 |                         try:
1810 |                             if os.path.exists(p):
1811 |                                 os.unlink(p)
1812 |                         except OSError:
1813 |                             pass
1814 |             except Exception as e:
1815 |                 logger.error(f"[ASYNC RENDER] {e}")
1816 |                 with _render_jobs_lock:
1817 |                     if jid in _render_jobs:
1818 |                         _render_jobs[jid]["status"] = "error"
1819 | 
1820 |         t = threading.Thread(target=render_async, args=(response_text, job_id, avatar_source), daemon=True)
1821 |         t.start()
1822 | 
1823 |         resp_data = {
1824 |             "text": response_text,
1825 |             "session_id": session_id,
1826 |             "job_id": job_id,
1827 |             "video_pending": True,
1828 |         }
1829 |         # Detect action card from user input (zero LLM cost)
1830 |         try:
1831 |             card = oracle_dialogue_engine.detect_action_card(text)
1832 |             if card:
1833 |                 resp_data["action_card"] = card
1834 |                 logger.info(f"[CHAT] Action card triggered: {card['id']}")
1835 |         except Exception as _card_err:
1836 |             logger.warning(f"[CHAT] Action card detection error: {_card_err}")
1837 |         return jsonify(resp_data)
1838 | 
1839 |     # Existing: return video directly
1840 |     return generate_inline(result["text"])
1841 | 
1842 | 
1843 | @app.route("/oracle/session", methods=["GET"])
1844 | def oracle_session_info():
1845 |     return jsonify(oracle_dialogue_engine.get_session_info(request.args.get("session_id","anon")))
1846 | 
1847 | 
1848 | @app.route("/oracle/session/reset", methods=["POST"])
1849 | def oracle_session_reset():
1850 |     data = request.get_json() or {}
1851 |     sid = data.get("session_id", "anon")
1852 | 
1853 |     # ── Phase 3: Save visitor memory before clearing session ───────────
1854 |     session = oracle_dialogue_engine._sessions.get(sid, {})
1855 |     fingerprint = session.get("fingerprint")
1856 |     if fingerprint and session.get("history"):
1857 |         try:
1858 |             from oracle_memory import save_visitor, generate_session_summary
1859 |             api_key = _get_anthropic_key()
1860 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
1861 |             flow = session.get("setup_flow", {})
1862 |             prev_memory = session.get("visitor_memory", {})
1863 |             # Build recent_turns from session history
1864 |             _hist = session.get("history", [])
1865 |             _turns = []
1866 |             for i in range(0, min(6, len(_hist)), 2):
1867 |                 if i+1 < len(_hist):
1868 |                     _turns.append({
1869 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1870 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1871 |                     })
1872 |             save_visitor(fingerprint, {
1873 |                 "personality": session.get("personality", "AMIABLE"),
1874 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
1875 |                 "setup_device": flow.get("device"),
1876 |                 "setup_step": flow.get("step", 0),
1877 |                 "topics_seen": session.get("topics_discussed", []),
1878 |                 "products_shown": session.get("products_mentioned", []),
1879 |                 "recent_turns": list(reversed(_turns)),
1880 |             })
1881 |             logger.info(f"[MEMORY] Saved visitor memory for session {sid}")
1882 |         except Exception as e:
1883 |             logger.warning(f"[MEMORY] Save failed on reset: {e}")
1884 | 
1885 |     oracle_dialogue_engine.reset_session(sid)
1886 |     return jsonify({"status": "reset"})
1887 | 
1888 | 
1889 | @app.route("/oracle/session/save", methods=["POST"])
1890 | def oracle_session_save():
1891 |     """Save session memory on page unload without clearing the session."""
1892 |     data = request.get_json() or {}
1893 |     sid = data.get("session_id", "anon")
1894 |     session = oracle_dialogue_engine._sessions.get(sid, {})
1895 |     fingerprint = session.get("fingerprint")
1896 |     if fingerprint and session.get("history"):
1897 |         try:
1898 |             from oracle_memory import save_visitor, generate_session_summary
1899 |             api_key = _get_anthropic_key()
1900 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
1901 |             flow = session.get("setup_flow", {})
1902 |             prev_memory = session.get("visitor_memory", {})
1903 |             topics = list(session.get("topics_discussed", []))
1904 |             # Build recent_turns from session history
1905 |             _hist = session.get("history", [])
1906 |             _turns = []
1907 |             for i in range(0, min(6, len(_hist)), 2):
1908 |                 if i+1 < len(_hist):
1909 |                     _turns.append({
1910 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1911 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1912 |                     })
1913 |             save_visitor(fingerprint, {
1914 |                 "personality": session.get("personality", "AMIABLE"),
1915 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
1916 |                 "setup_device": flow.get("device"),
1917 |                 "setup_step": flow.get("step", 0),
1918 |                 "topics_seen": topics,
1919 |                 "products_shown": session.get("products_mentioned", []),
1920 |                 "recent_turns": list(reversed(_turns)),
1921 |             })
1922 |             logger.info(f"[MEMORY] Saved session {sid} on unload — {len(topics)} topics, summary len={len(summary)}")
1923 |         except Exception as e:
1924 |             logger.warning(f"[MEMORY] Save on unload failed: {e}")
1925 |     return jsonify({"status": "saved"})
1926 | 
1927 | 
1928 | @app.route("/oracle/intent", methods=["POST"])
1929 | def oracle_intent():
1930 |     """Classify user transcript to an intent."""
1931 |     data = request.get_json()
1932 |     if not data or not data.get("transcript"):
1933 |         return jsonify({"error": "transcript required"}), 400
1934 | 
1935 |     intent, confidence = classify_intent(data["transcript"])
1936 | 
1937 |     # If low confidence, try Claude Haiku for better classification
1938 |     if confidence < 0.6:
1939 |         try:
1940 |             api_key = _get_anthropic_key()
1941 |             if api_key:
1942 |                 resp = http_requests.post(
1943 |                     "https://api.anthropic.com/v1/messages",
1944 |                     headers={
1945 |                         "x-api-key": api_key,
1946 |                         "anthropic-version": "2023-06-01",
1947 |                         "content-type": "application/json",
1948 |                     },
1949 |                     json={
1950 |                         "model": "claude-haiku-4-5-20251001",
1951 |                         "max_tokens": 30,
1952 |                         "messages": [{
1953 |                             "role": "user",
1954 |                             "content": (
1955 |                                 f"Classify this user message into ONE intent from this list: "
1956 |                                 f"{', '.join(INTENT_PATTERNS.keys())}, GREETING, UNKNOWN. "
1957 |                                 f"Reply with ONLY the intent name.\n\nMessage: {data['transcript']}"
1958 |                             ),
1959 |                         }],
1960 |                     },
1961 |                     timeout=10,
1962 |                 )
1963 |                 if resp.status_code == 200:
1964 |                     ai_intent = resp.json()["content"][0]["text"].strip().upper()
1965 |                     valid = set(INTENT_PATTERNS.keys()) | {"GREETING", "UNKNOWN", "SOVEREIGNTY_ASSESSMENT"}
1966 |                     if ai_intent in valid:
1967 |                         intent = ai_intent
1968 |                         confidence = 0.75
1969 |         except Exception as e:
1970 |             logger.warning(f"Intent AI fallback failed: {e}")
1971 | 
1972 |     return jsonify({
1973 |         "intent": intent,
1974 |         "confidence": round(confidence, 2),
1975 |         "cached": oracle_cache_manager.get_cached_response(intent) is not None,
1976 |     })
1977 | 
1978 | 
1979 | # ═══════════════════════════════════════════════════════════════════════
1980 | # SENTENCE CHUNKING FOR LONG TEXT
1981 | # ═══════════════════════════════════════════════════════════════════════
1982 | 
1983 | _chunk_sessions = {}
1984 | _chunk_lock = threading.Lock()
1985 | 
1986 | 
1987 | @app.route("/oracle/chunks/<session_id>")
1988 | def oracle_chunks(session_id):
1989 |     """Poll for additional chunks from a long-text generation."""
1990 |     session = _chunk_sessions.get(session_id)
1991 |     if not session:
1992 |         return jsonify({"error": "Session not found"}), 404
1993 | 
1994 |     return jsonify({
1995 |         "session_id": session_id,
1996 |         "chunks_ready": len(session["paths"]),
1997 |         "total_chunks": session["total"],
1998 |         "complete": session["complete"],
1999 |         "paths": [f"/oracle/chunks/{session_id}/{i}" for i in range(len(session["paths"]))],
2000 |     })
2001 | 
2002 | 
2003 | @app.route("/oracle/chunks/<session_id>/<int:idx>")
2004 | def oracle_chunk_file(session_id, idx):
2005 |     """Serve a specific chunk file."""
2006 |     session = _chunk_sessions.get(session_id)
2007 |     if not session or idx >= len(session["paths"]):
2008 |         return jsonify({"error": "Chunk not ready"}), 404
2009 |     return send_file(session["paths"][idx], mimetype="video/mp4")
2010 | 
2011 | 
2012 | # ═══════════════════════════════════════════════════════════════════════
2013 | # TTS PROVIDER STATUS
2014 | # ═══════════════════════════════════════════════════════════════════════
2015 | 
2016 | @app.route("/avatar/tts-provider", methods=["GET"])
2017 | def avatar_tts_provider():
2018 |     """Report which TTS provider is active."""
2019 |     if _AVATAR_KOKORO_READY:
2020 |         return jsonify({
2021 |             "provider": "kokoro",
2022 |             "voice": "af_heart",
2023 |             "backend": "cuda:1",
2024 |             "sample_rate": 24000,
2025 |             "ready": True,
2026 |         })
2027 |     return jsonify({
2028 |         "provider": "elevenlabs_fallback",
2029 |         "reason": "Kokoro not loaded or init failed",
2030 |         "ready": False,
2031 |     })
2032 | 
2033 | 
2034 | # ═══════════════════════════════════════════════════════════════════════
2035 | # MAIN
2036 | # ═══════════════════════════════════════════════════════════════════════
2037 | 
2038 | if __name__ == "__main__":
2039 |     print(f"\n{'='*60}")
2040 |     print("  ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks")
2041 |     print(f"  Port: {PORT}")
2042 |     print(f"  Device: {DEVICE}")
2043 |     print(f"  Avatar: {AVATAR_SOURCE}")
2044 |     print(f"  FPS: {DEFAULT_FPS}")
2045 |     print(f"  Encoding: CRF 28, preset ultrafast, 512px output")
2046 |     print(f"  Features: FP16, cv2_sharpen, mediapipe_blinks, head_movement")
2047 |     print(f"  Vision: {'enabled' if os.environ.get('GEMINI_API_KEY') else 'disabled'}")
2048 |     print(f"  Max audio: {MAX_AUDIO_SECONDS}s | Lock timeout: {LOCK_TIMEOUT}s")
2049 |     print(f"{'='*60}\n")
2050 | 
2051 |     # Load all models via registry (FP16 on GPU 1)
2052 |     logger.info("Initializing ModelRegistry...")
2053 |     reg = ModelRegistry.get()
2054 | 
2055 |     if reg.wav2lip_model is None:
2056 |         logger.error("Failed to load Wav2Lip model. Exiting.")
2057 |         sys.exit(1)
2058 | 
2059 |     if reg.avatar_face_coords is None:
2060 |         logger.error("No face detected in avatar. Exiting.")
2061 |         sys.exit(1)
2062 | 
2063 |     logger.info("Face enhancer: CV2 sharpen-only (no GFPGAN)")
2064 | 
2065 |     # Load Kokoro af_heart TTS on cuda:1 (~2-3s per utterance)
2066 |     logger.info("[STARTUP] Initializing Kokoro af_heart TTS on cuda:1...")
2067 |     _init_avatar_kokoro()
2068 | 
2069 |     # Auto-warmup (non-blocking — runs in background thread so Flask can start immediately)
2070 |     def _warmup_background():
2071 |         logger.info("[WARMUP] Running pipeline warmup in background...")
2072 |         warmup_start = time.time()
2073 |         try:
2074 |             import wave
2075 |             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
2076 |                 with wave.open(tmp.name, "w") as wf:
2077 |                     wf.setnchannels(1)
2078 |                     wf.setsampwidth(2)
2079 |                     wf.setframerate(16000)
2080 |                     wf.writeframes(b"\x00\x00" * 8000)
2081 |                 warmup_wav = tmp.name
2082 |             frames = wav2lip_generate(warmup_wav, DEFAULT_FPS)
2083 |             if frames:
2084 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
2085 |             os.unlink(warmup_wav)
2086 |             logger.info(
2087 |                 f"[WARMUP] Pipeline ready in {time.time()-warmup_start:.1f}s "
2088 |                 f"({len(frames)} frames)"
2089 |             )
2090 |         except Exception as e:
2091 |             logger.warning(f"[WARMUP] Failed (non-fatal): {e}")
2092 |     threading.Thread(target=_warmup_background, daemon=True).start()
2093 | 
2094 |     dev_idx = int(DEVICE.split(':')[1]) if ':' in DEVICE else 0
2095 |     logger.info(
2096 |         f"[WARMUP] GPU {dev_idx} VRAM: {torch.cuda.memory_allocated(dev_idx)/1024**3:.1f}GB used"
2097 |     )
2098 | 
2099 |     # Generate idle loop if not already present
2100 |     generate_idle_loop()
2101 | 
2102 |     # Phase 2: Start cache warming in background (delayed 60s to allow incoming requests)
2103 |     logger.info("[STARTUP] Oracle cache warmer will start in 60s...")
2104 |     def _delayed_warmup():
2105 |         time.sleep(60)
2106 |         logger.info("[STARTUP] Cache warmup starting now (60s delay complete)")
2107 |         oracle_cache_manager.warm_cache()
2108 |     threading.Thread(target=_delayed_warmup, daemon=True).start()
2109 |     oracle_cache_manager.start_background_warmer()
2110 | 
2111 |     # Phase 3: Start intelligence feed
2112 |     logger.info("[STARTUP] Starting intelligence feed...")
2113 |     oracle_intelligence_feed.start_intelligence_feed()
2114 | 
2115 |     logger.info(f"Avatar server v2 ready on port {PORT}")
2116 |     app.run(host="0.0.0.0", port=PORT, threaded=True)
2117 | 
```

### File: core/blueprints/oracle.py (19 lines)
```
   1 | """
   2 | ORACLE BLUEPRINT — Protocol Pulse
   3 | ===================================
   4 | Owns: /oracle, /oracle-live, /oracle/*
   5 | Status: Core oracle routes in oracle_routes.py (oracle_bp).
   6 |         /oracle-live in routes.py.
   7 | TODO: Consolidate all oracle routes here (future session).
   8 | """
   9 | from flask import Blueprint
  10 | 
  11 | oracle_bp_main = Blueprint("oracle_main", __name__)
  12 | 
  13 | # Routes to migrate from routes.py:
  14 | #   GET  /oracle-live          — oracle.html (avatar streaming interface)
  15 | #   GET  /oracle               — oracle onboarding/hub
  16 | # API routes in oracle_routes.oracle_bp:
  17 | #   POST /api/oracle/ask       — Oracle Q&A endpoint
  18 | #   POST /api/oracle/generate  — Avatar generation
  19 | 
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?

