# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: oracle-phase2
# Branch: main
# Generated: 2026-03-24 18:56 UTC
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

### File: oracle/avatar_server.py (2199 lines)
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
  12 |   - CRF 23, preset ultrafast, 30fps output
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
 112 |         except Exception as e:
 113 |             logger.warning(f"[AVATAR_SOURCE] Eye landmark detection failed for {source_name}: {e}", exc_info=True)
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
 126 |     Thread-safe: all work happens inside the lock to prevent thundering herd.
 127 |     """
 128 |     if source_name == "default" or source_name not in AVATAR_SOURCES:
 129 |         reg = ModelRegistry.get()
 130 |         return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks
 131 | 
 132 |     with _avatar_face_cache_lock:
 133 |         # Check cache inside lock — prevents thundering herd
 134 |         if source_name in _avatar_face_cache:
 135 |             c = _avatar_face_cache[source_name]
 136 |             return c["face"], c["coords"], c["eye_landmarks"]
 137 | 
 138 |         # Load and detect inside lock — only one thread does the work
 139 |         img_path = AVATAR_SOURCES[source_name]
 140 |         # Validate path is within expected directory
 141 |         real_path = os.path.realpath(img_path)
 142 |         allowed_base = os.path.realpath("/home/ultron/protocol_pulse")
 143 |         if not real_path.startswith(allowed_base + os.sep):
 144 |             logger.error(f"[AVATAR_SOURCE] Path traversal blocked: {img_path} -> {real_path}")
 145 |             return None, None, None
 146 | 
 147 |         if not os.path.exists(img_path):
 148 |             logger.error(f"[AVATAR_SOURCE] Image not found: {img_path}")
 149 |             return None, None, None
 150 | 
 151 |         img = cv2.imread(img_path)
 152 |         if img is None:
 153 |             logger.error(f"[AVATAR_SOURCE] Failed to read: {img_path}")
 154 |             return None, None, None
 155 | 
 156 |         coords, eye_lm = _detect_face_cpu(img, source_name)
 157 |         if coords is None:
 158 |             logger.error(f"[AVATAR_SOURCE] No face detected in {source_name} — falling back to default")
 159 |             reg = ModelRegistry.get()
 160 |             return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks
 161 | 
 162 |         _avatar_face_cache[source_name] = {"face": img.copy(), "coords": coords, "eye_landmarks": eye_lm}
 163 | 
 164 |     return img.copy(), coords, eye_lm
 165 | 
 166 | # ─── Logging ──────────────────────────────────────────────────────────
 167 | logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
 168 | logger = logging.getLogger("avatar_server")
 169 | 
 170 | app = Flask(__name__)
 171 | 
 172 | # ── CORS: allow protocolpulse.io and any origin to call avatar APIs ──────────
 173 | CORS_ORIGINS = [
 174 |     "https://protocolpulse.io",
 175 |     "https://www.protocolpulse.io",
 176 |     "http://localhost:3000",
 177 |     "http://localhost:5000",
 178 |     "http://localhost:8080",
 179 | ]
 180 | 
 181 | @app.after_request
 182 | def add_cors_headers(response):
 183 |     origin = request.headers.get("Origin", "")
 184 |     # Allow configured origins + any localhost
 185 |     if origin in CORS_ORIGINS or origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
 186 |         response.headers["Access-Control-Allow-Origin"] = origin
 187 |     # Default deny: no Access-Control-Allow-Origin header for unknown origins
 188 |     response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
 189 |     response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
 190 |     response.headers["Access-Control-Allow-Credentials"] = "false"
 191 |     response.headers["Access-Control-Max-Age"] = "86400"
 192 |     return response
 193 | 
 194 | @app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
 195 | @app.route("/<path:path>", methods=["OPTIONS"])
 196 | def handle_options(path):
 197 |     response = app.make_default_options_response()
 198 |     return response
 199 | 
 200 | # ─── Metrics ──────────────────────────────────────────────────────────
 201 | _lock = threading.Lock()
 202 | _start_time = time.time()
 203 | _request_times = []  # last 100 request times for avg latency
 204 | 
 205 | # ─── Async render job system (Phase 1: audio-first) ──────────────────
 206 | _render_jobs = {}        # job_id -> {"status": "pending"|"done"|"error", "video_bytes": bytes|None, "created": float}
 207 | _render_jobs_lock = threading.Lock()
 208 | _RENDER_JOB_TTL = 120   # seconds — auto-expire stale jobs
 209 | 
 210 | # ─── Concurrency queue (Phase 1: concurrency hardening) ──────────────
 211 | _render_semaphore = threading.Semaphore(2)  # max 2 concurrent Wav2Lip renders
 212 | _render_queue_count = 0
 213 | _render_queue_lock = threading.Lock()
 214 | 
 215 | 
 216 | _GC_INTERVAL = 60        # seconds between garbage collection sweeps
 217 | _SESSION_TTL = 300       # seconds — evict stream/chunk sessions after 5min of inactivity
 218 | _JOB_TTL_COMPLETED = 300 # seconds — evict completed/failed render jobs after 5min
 219 | _MAX_RENDER_JOBS = 50    # hard cap on concurrent render jobs
 220 | 
 221 | 
 222 | def _gc_worker():
 223 |     """Background daemon: evict stale sessions, jobs, and their temp files."""
 224 |     import shutil
 225 |     while True:
 226 |         time.sleep(_GC_INTERVAL)
 227 |         now = time.time()
 228 |         try:
 229 |             # Clean _stream_sessions
 230 |             with _stream_lock:
 231 |                 expired = [sid for sid, s in _stream_sessions.items()
 232 |                            if now - s.get("created", 0) > _SESSION_TTL]
 233 |                 for sid in expired:
 234 |                     s = _stream_sessions.pop(sid, None)
 235 |                     if s and s.get("dir"):
 236 |                         try:
 237 |                             shutil.rmtree(s["dir"], ignore_errors=True)
 238 |                         except Exception:
 239 |                             pass
 240 |             if expired:
 241 |                 logger.info(f"[GC] Evicted {len(expired)} stream sessions")
 242 | 
 243 |             # Clean _chunk_sessions
 244 |             with _chunk_lock:
 245 |                 expired_chunks = [sid for sid, s in _chunk_sessions.items()
 246 |                                   if now - s.get("created", 0) > _SESSION_TTL]
 247 |                 for sid in expired_chunks:
 248 |                     s = _chunk_sessions.pop(sid, None)
 249 |                     if s and s.get("dir"):
 250 |                         try:
 251 |                             shutil.rmtree(s["dir"], ignore_errors=True)
 252 |                         except Exception:
 253 |                             pass
 254 |             if expired_chunks:
 255 |                 logger.info(f"[GC] Evicted {len(expired_chunks)} chunk sessions")
 256 | 
 257 |             # Clean _render_jobs (completed/failed older than TTL, or pending older than _RENDER_JOB_TTL)
 258 |             with _render_jobs_lock:
 259 |                 expired_jobs = []
 260 |                 for jid, job in _render_jobs.items():
 261 |                     if job["status"] in ("done", "error"):
 262 |                         completed_at = job.get("completed_at", job.get("created", 0))
 263 |                         if now - completed_at > _JOB_TTL_COMPLETED:
 264 |                             expired_jobs.append(jid)
 265 |                     elif now - job.get("created", 0) > _RENDER_JOB_TTL:
 266 |                         expired_jobs.append(jid)
 267 |                 for jid in expired_jobs:
 268 |                     del _render_jobs[jid]
 269 |             if expired_jobs:
 270 |                 logger.info(f"[GC] Evicted {len(expired_jobs)} render jobs")
 271 |         except Exception as e:
 272 |             logger.error(f"[GC] Error during cleanup: {e}", exc_info=True)
 273 | 
 274 | 
 275 | threading.Thread(target=_gc_worker, daemon=True, name="gc_worker").start()
 276 | 
 277 | 
 278 | def _record_latency(seconds):
 279 |     with _lock:
 280 |         _request_times.append(seconds)
 281 |         if len(_request_times) > 100:
 282 |             _request_times.pop(0)
 283 | 
 284 | 
 285 | # ═══════════════════════════════════════════════════════════════════════
 286 | # WAV2LIP INFERENCE (FP16)
 287 | # ═══════════════════════════════════════════════════════════════════════
 288 | 
 289 | FACE_BBOX_CACHE = os.path.join(os.path.dirname(__file__), "cache", "face_bbox.json")
 290 | 
 291 | 
 292 | def wav2lip_generate(audio_path, fps=30.0, avatar_face=None, avatar_face_coords=None):
 293 |     """Run Wav2Lip inference in FP16. Returns list of BGR frames with duration matching.
 294 |     Optional avatar_face/avatar_face_coords override the default ModelRegistry face.
 295 |     """
 296 |     reg = ModelRegistry.get()
 297 |     if reg.wav2lip_model is None:
 298 |         raise RuntimeError("Model not loaded")
 299 | 
 300 |     # Use overrides if provided, else default from registry
 301 |     face_img = avatar_face if avatar_face is not None else reg.avatar_face
 302 |     face_coords = avatar_face_coords if avatar_face_coords is not None else reg.avatar_face_coords
 303 | 
 304 |     if face_img is None or face_coords is None:
 305 |         raise RuntimeError("Avatar face not loaded")
 306 | 
 307 |     if WAV2LIP_DIR not in sys.path:
 308 |         sys.path.insert(0, WAV2LIP_DIR)
 309 |     import audio as wav2lip_audio
 310 | 
 311 |     wav = wav2lip_audio.load_wav(audio_path, 16000)
 312 |     mel = wav2lip_audio.melspectrogram(wav)
 313 |     if mel.shape[1] == 0:
 314 |         raise ValueError("Empty audio")
 315 | 
 316 |     mel_step = 16
 317 |     audio_duration = len(wav) / 16000.0
 318 |     num_frames = int(math.ceil(audio_duration * fps)) + 2  # prevent audio cutoff
 319 |     if num_frames < 1:
 320 |         num_frames = 1
 321 | 
 322 |     # Map each VIDEO frame to its correct MEL position
 323 |     mel_idx_multiplier = 80.0 / fps
 324 | 
 325 |     mel_chunks = []
 326 |     for frame_i in range(num_frames):
 327 |         start_col = int(frame_i * mel_idx_multiplier)
 328 |         end_col = start_col + mel_step
 329 |         if end_col > mel.shape[1]:
 330 |             chunk = mel[:, start_col:]
 331 |             if chunk.shape[1] < mel_step:
 332 |                 chunk = np.pad(chunk, ((0, 0), (0, mel_step - chunk.shape[1])))
 333 |         else:
 334 |             chunk = mel[:, start_col:end_col]
 335 |         mel_chunks.append(chunk)
 336 | 
 337 |     # Adaptive batch size: smaller for short audio
 338 |     batch_size = BATCH_SIZE_SMALL if len(mel_chunks) < 60 else BATCH_SIZE_DEFAULT
 339 | 
 340 |     logger.info(f"Mel: {mel.shape[1]} cols, {num_frames} frames @ {fps}fps, audio {audio_duration:.2f}s, batch={batch_size}")
 341 | 
 342 |     # Face bbox with chin padding (8% lower to eliminate chin seam)
 343 |     y1, y2, x1, x2 = face_coords
 344 |     y2 = min(face_img.shape[0], y2 + int((y2 - y1) * 0.08))
 345 |     face_crop = face_img[y1:y2, x1:x2]
 346 |     face_resized = cv2.resize(face_crop, (96, 96))
 347 |     face_masked = face_resized.copy()
 348 |     face_masked[face_resized.shape[0] // 2:, :] = 0
 349 | 
 350 |     frames = []
 351 |     total_chunks = len(mel_chunks)
 352 | 
 353 |     for batch_start in range(0, total_chunks, batch_size):
 354 |         batch_end = min(batch_start + batch_size, total_chunks)
 355 |         batch_mels = mel_chunks[batch_start:batch_end]
 356 | 
 357 |         img_concat = np.concatenate((face_masked, face_resized), axis=2)
 358 |         img_batch = np.array([img_concat / 255.0] * len(batch_mels), dtype=np.float32)
 359 |         mel_batch = np.array(batch_mels, dtype=np.float32)
 360 | 
 361 |         # FP16 tensors → GPU 1
 362 |         img_batch = torch.HalfTensor(img_batch.transpose(0, 3, 1, 2)).to(DEVICE)
 363 |         mel_batch = torch.HalfTensor(mel_batch[:, np.newaxis, :, :]).to(DEVICE)
 364 | 
 365 |         with torch.no_grad():
 366 |             pred = reg.wav2lip_model(mel_batch, img_batch)
 367 | 
 368 |         pred = pred.float().cpu().numpy().transpose(0, 2, 3, 1) * 255.0
 369 | 
 370 |         for p in pred:
 371 |             p_resized = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
 372 |             full_frame = face_img.copy()
 373 |             # Feathered blend to eliminate face paste seam
 374 |             mask = np.ones_like(p_resized, dtype=np.float32)
 375 |             feather = 18
 376 |             h_face, w_face = p_resized.shape[:2]
 377 |             for j in range(min(feather, h_face)):
 378 |                 mask[j, :] = j / feather
 379 |             for j in range(min(feather, h_face)):
 380 |                 mask[-(j+1), :] = j / feather
 381 |             for j in range(min(feather, w_face)):
 382 |                 mask[:, j] *= j / feather
 383 |             for j in range(min(feather, w_face)):
 384 |                 mask[:, -(j+1)] *= j / feather
 385 |             full_frame[y1:y2, x1:x2] = (
 386 |                 p_resized * mask + full_frame[y1:y2, x1:x2] * (1 - mask)
 387 |             ).astype(np.uint8)
 388 |             frames.append(full_frame)
 389 | 
 390 |     logger.info(f"Generated {len(frames)} frames for {audio_duration:.2f}s audio @ {fps}fps")
 391 |     return frames
 392 | 
 393 | 
 394 | # ═══════════════════════════════════════════════════════════════════════
 395 | # POST-PROCESSING: HEAD MOVEMENT
 396 | # ═══════════════════════════════════════════════════════════════════════
 397 | 
 398 | def apply_head_movement(frame, frame_idx, fps):
 399 |     # LAW: NO rotation — warpAffine on portrait avatar looks like body spinning.
 400 |     # Only micro XY translation: subtle alive-breathing feel, not distracting.
 401 |     t = frame_idx / fps
 402 |     # Gentle breathing drift: max ±1.5px horizontal, ±1px vertical
 403 |     # Two overlapping slow sinusoids so it never feels mechanical
 404 |     tx = (
 405 |         1.0 * math.sin(2 * math.pi * t / 6.0 + 0.8) +
 406 |         0.5 * math.sin(2 * math.pi * t / 11.0 + 2.1)
 407 |     )
 408 |     ty = (
 409 |         0.8 * math.sin(2 * math.pi * t / 7.5 + 1.5) +
 410 |         0.2 * math.sin(2 * math.pi * t / 4.2 + 0.6)
 411 |     )
 412 |     # Integer shift only — no warpAffine, no rotation, no interpolation artifacts
 413 |     ix, iy = int(round(tx)), int(round(ty))
 414 |     if ix == 0 and iy == 0:
 415 |         return frame
 416 |     h, w = frame.shape[:2]
 417 |     result = frame.copy()
 418 |     # Clip-and-shift: roll pixels, fill edges with border value
 419 |     if ix > 0:
 420 |         result[:, ix:] = frame[:, :w-ix]
 421 |         result[:, :ix] = frame[:, :1]
 422 |     elif ix < 0:
 423 |         result[:, :w+ix] = frame[:, -ix:]
 424 |         result[:, w+ix:] = frame[:, -1:]
 425 |     tmp = result.copy()
 426 |     if iy > 0:
 427 |         result[iy:, :] = tmp[:h-iy, :]
 428 |         result[:iy, :] = tmp[:1, :]
 429 |     elif iy < 0:
 430 |         result[:h+iy, :] = tmp[-iy:, :]
 431 |         result[h+iy:, :] = tmp[-1:, :]
 432 |     return result
 433 | 
 434 | 
 435 | # ═══════════════════════════════════════════════════════════════════════
 436 | # POST-PROCESSING: COMBINED PIPELINE
 437 | # ═══════════════════════════════════════════════════════════════════════
 438 | 
 439 | def post_process_frames(frames, fps=30.0, enable_blinks=True, enable_head=True):
 440 |     """Apply eye blinks and head movement post-processing."""
 441 |     if len(frames) == 0:
 442 |         return frames
 443 | 
 444 |     reg = ModelRegistry.get()
 445 | 
 446 |     # Generate blink schedule
 447 |     blink_schedule = {}
 448 |     if enable_blinks:
 449 |         blink_schedule = generate_blink_schedule(
 450 |             len(frames), fps,
 451 |             interval_min=BLINK_INTERVAL_MIN,
 452 |             interval_max=BLINK_INTERVAL_MAX,
 453 |             duration=BLINK_DURATION,
 454 |         )
 455 | 
 456 |     processed = []
 457 |     for i, frame in enumerate(frames):
 458 |         result = frame
 459 |         if enable_blinks and i in blink_schedule:
 460 |             try:
 461 |                 result = apply_blink_gradient(
 462 |                     result,
 463 |                     blink_schedule[i],
 464 |                     eye_landmarks=reg.eye_landmarks,
 465 |                     face_coords=reg.avatar_face_coords,
 466 |                 )
 467 |             except Exception as e:
 468 |                 # P0 safety net: blink artifacts → return original frame, but log
 469 |                 logger.error(f"[POST] Blink post-process failed on frame {i}: {e}", exc_info=True)
 470 |                 result = frame
 471 |         if enable_head:
 472 |             result = apply_head_movement(result, i, fps)
 473 |         processed.append(result)
 474 |     return processed
 475 | 
 476 | 
 477 | # ═══════════════════════════════════════════════════════════════════════
 478 | # VIDEO ENCODING
 479 | # ═══════════════════════════════════════════════════════════════════════
 480 | 
 481 | def frames_to_video(frames, fps=30.0, audio_path=None):
 482 |     """Encode frames to MP4, optionally muxing audio (audio as timing master).
 483 |     Returns the path to the output MP4 file (caller must clean up)."""
 484 |     if not frames:
 485 |         return None
 486 |     with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp_avi:
 487 |         avi_path = tmp_avi.name
 488 |     mp4_path = avi_path.replace(".avi", ".mp4")
 489 |     try:
 490 |         h, w = frames[0].shape[:2]
 491 |         fourcc = cv2.VideoWriter_fourcc(*"MJPG")
 492 |         writer = cv2.VideoWriter(avi_path, fourcc, fps, (w, h))
 493 |         for frame in frames:
 494 |             writer.write(frame)
 495 |         writer.release()
 496 | 
 497 |         import subprocess
 498 |         if audio_path and os.path.exists(audio_path):
 499 |             cmd = [
 500 |                 "ffmpeg", "-y", "-loglevel", "error",
 501 |                 "-itsoffset", "0.08", "-i", audio_path, "-i", avi_path,
 502 |             ]
 503 |             if w > 512:
 504 |                 cmd += ["-vf", "scale=512:512"]
 505 |             cmd += [
 506 |                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
 507 |                 "-c:a", "aac", "-b:a", "128k",
 508 |                 "-map", "0:a", "-map", "1:v",
 509 |                 "-pix_fmt", "yuv420p", "-movflags", "+faststart",
 510 |                 mp4_path,
 511 |             ]
 512 |             subprocess.run(cmd, check=True, capture_output=True)
 513 |         else:
 514 |             cmd = [
 515 |                 "ffmpeg", "-y", "-loglevel", "error",
 516 |                 "-i", avi_path,
 517 |             ]
 518 |             if w > 512:
 519 |                 cmd += ["-vf", "scale=512:512"]
 520 |             cmd += [
 521 |                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
 522 |                 "-pix_fmt", "yuv420p", "-movflags", "+faststart",
 523 |                 mp4_path,
 524 |             ]
 525 |             subprocess.run(cmd, check=True, capture_output=True)
 526 | 
 527 |         if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
 528 |             return mp4_path
 529 |         else:
 530 |             logger.error("ffmpeg failed to produce MP4")
 531 |             return None
 532 |     finally:
 533 |         try:
 534 |             os.unlink(avi_path)
 535 |         except OSError:
 536 |             pass
 537 | 
 538 | 
 539 | # ═══════════════════════════════════════════════════════════════════════
 540 | # KOKORO af_heart FEMALE VOICE (primary) + ELEVENLABS FALLBACK
 541 | # ═══════════════════════════════════════════════════════════════════════
 542 | 
 543 | def _init_avatar_kokoro():
 544 |     """Lazy-init Kokoro af_heart TTS on cuda:1. Call once at startup."""
 545 |     global _AVATAR_KOKORO_READY, _KOKORO_PIPELINE
 546 |     try:
 547 |         from kokoro import KPipeline
 548 |         _KOKORO_PIPELINE = KPipeline(lang_code='a')
 549 |         _KOKORO_PIPELINE.model = _KOKORO_PIPELINE.model.to('cuda:1')
 550 |         _AVATAR_KOKORO_READY = True
 551 |         logger.info("[AVATAR_TTS] Kokoro af_heart loaded on cuda:1")
 552 |     except Exception as e:
 553 |         logger.error(f"[AVATAR_TTS] Kokoro init failed: {e} — ElevenLabs fallback active")
 554 |         _AVATAR_KOKORO_READY = False
 555 | 
 556 | 
 557 | def _preprocess_tts_text(text: str) -> str:
 558 |     """Convert numbers and symbols to spoken form for natural TTS."""
 559 |     import re
 560 |     try:
 561 |         from num2words import num2words
 562 |     except ImportError:
 563 |         return text
 564 | 
 565 |     # Percentages: 0.79% → "point seventy-nine percent"
 566 |     def pct(m):
 567 |         try:
 568 |             val = float(m.group(1))
 569 |             if val == int(val):
 570 |                 return num2words(int(val)) + ' percent'
 571 |             parts = str(val).split('.')
 572 |             return num2words(int(parts[0])) + ' point ' + ' '.join(num2words(int(d)) for d in parts[1]) + ' percent'
 573 |         except: return m.group(0)
 574 |     text = re.sub(r'([\d]+\.?\d*)\s*%', pct, text)
 575 | 
 576 |     # Dollars: $70,586 → "seventy thousand five hundred eighty-six dollars"
 577 |     def dollars(m):
 578 |         try:
 579 |             raw = m.group(1).replace(',', '')
 580 |             val = int(float(raw))
 581 |             return num2words(val) + ' dollars'
 582 |         except: return m.group(0)
 583 |     text = re.sub(r'\$\s*([\d,]+\.?\d*)', dollars, text)
 584 | 
 585 |     # Large numbers with commas: 970,600 → spoken
 586 |     def bignum(m):
 587 |         try: return num2words(int(m.group(0).replace(',', '')))
 588 |         except: return m.group(0)
 589 |     text = re.sub(r'\b\d{1,3}(?:,\d{3})+\b', bignum, text)
 590 | 
 591 |     # Decimals: 970.6 → "nine hundred seventy point six"
 592 |     def decimal(m):
 593 |         try:
 594 |             parts = m.group(0).split('.')
 595 |             return num2words(int(parts[0])) + ' point ' + ' '.join(num2words(int(d)) for d in parts[1])
 596 |         except: return m.group(0)
 597 |     text = re.sub(r'\b(\d+)\.(\d+)\b', decimal, text)
 598 | 
 599 |     # Large plain integers 4+ digits
 600 |     def integer(m):
 601 |         try: return num2words(int(m.group(0)))
 602 |         except: return m.group(0)
 603 |     text = re.sub(r'\b(\d{4,})\b', integer, text)
 604 | 
 605 |     # Proper pronunciations
 606 |     text = re.sub(r'\bNostr\b', 'Nohster', text)
 607 |     text = re.sub(r'\bNOSTR\b', 'Nohster', text)
 608 |     text = re.sub(r'\bnostr\b', 'Nohster', text)
 609 |     text = re.sub(r'\bBTC\b', 'Bitcoin', text)
 610 |     text = re.sub(r'\bETF\b', 'E T F', text)
 611 |     text = re.sub(r'\bFNG\b', 'fear and greed index', text, flags=re.IGNORECASE)
 612 |     text = re.sub(r'\bEH/s\b', 'exahashes per second', text)
 613 |     text = re.sub(r'\bEH\b', 'exahash', text)
 614 |     text = re.sub(r'\bsat/vbyte\b', 'sats per vbyte', text)
 615 | 
 616 |     return text
 617 | 
 618 | 
 619 | def _avatar_tts(text):
 620 |     """Primary TTS: Kokoro af_heart -> 24kHz numpy -> ffmpeg resample 16kHz mono WAV bytes.
 621 |     Falls back to ElevenLabs text_to_speech() if Kokoro fails."""
 622 |     global _AVATAR_KOKORO_READY
 623 | 
 624 |     # Normalize Bitcoin pronunciation (BTC -> "bitcoin", sats, hashrate, etc.)
 625 |     try:
 626 |         from oracle_dialogue_engine import normalize_pronunciation
 627 |         text = normalize_pronunciation(text)
 628 |     except Exception as _np_err:
 629 |         logger.warning(f"[AVATAR_TTS] normalize_pronunciation unavailable: {_np_err}")
 630 | 
 631 |     text = _preprocess_tts_text(text)
 632 | 
 633 |     # Try Kokoro first
 634 |     if _AVATAR_KOKORO_READY and _KOKORO_PIPELINE is not None:
 635 |         t0 = time.time()
 636 |         try:
 637 |             import soundfile as sf
 638 |             # Generate with af_heart voice
 639 |             generator = _KOKORO_PIPELINE(text, voice='af_heart')
 640 |             # Collect all audio chunks
 641 |             audio_chunks = []
 642 |             for _gs, _ps, audio_np in generator:
 643 |                 audio_chunks.append(audio_np)
 644 |             if not audio_chunks:
 645 |                 raise ValueError("Kokoro returned no audio")
 646 |             full_audio = np.concatenate(audio_chunks)
 647 | 
 648 |             # Write 24kHz WAV to temp file
 649 |             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
 650 |                 sf.write(tmp.name, full_audio, 24000)
 651 |                 wav24_path = tmp.name
 652 | 
 653 |             # Resample to 16kHz mono + loudnorm in single ffmpeg call
 654 |             wav16_path = wav24_path + ".16k.wav"
 655 |             r = subprocess.run(
 656 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", wav24_path,
 657 |                  "-af", "aresample=16000,loudnorm=I=-14:TP=-1.5:LRA=11",
 658 |                  "-ac", "1", "-f", "wav", wav16_path],
 659 |                 capture_output=True, text=True, timeout=30,
 660 |             )
 661 |             try:
 662 |                 os.remove(wav24_path)
 663 |             except OSError:
 664 |                 pass
 665 |             if r.returncode == 0 and os.path.exists(wav16_path) and os.path.getsize(wav16_path) > 1000:
 666 |                 with open(wav16_path, "rb") as f:
 667 |                     wav_bytes = f.read()
 668 |                 try:
 669 |                     os.remove(wav16_path)
 670 |                 except OSError:
 671 |                     pass
 672 |                 elapsed = time.time() - t0
 673 |                 logger.info(f"[AVATAR_TTS] Kokoro af_heart OK: {elapsed:.2f}s ({len(wav_bytes)} bytes)")
 674 |                 return wav_bytes
 675 |             else:
 676 |                 logger.warning("[AVATAR_TTS] Kokoro ffmpeg resample failed")
 677 |         except Exception as e:
 678 |             logger.error(f"[AVATAR_TTS] Kokoro FAILED: {e} → ElevenLabs fallback")
 679 |     else:
 680 |         logger.info("[AVATAR_TTS] Kokoro not ready → ElevenLabs fallback")
 681 | 
 682 |     # Fallback: ElevenLabs
 683 |     t0 = time.time()
 684 |     audio_bytes = text_to_speech(text)
 685 |     elapsed = time.time() - t0
 686 |     logger.info(f"[AVATAR_TTS] ElevenLabs fallback: {elapsed:.2f}s ({len(audio_bytes)} bytes)")
 687 |     return audio_bytes
 688 | 
 689 | 
 690 | def text_to_speech(text, voice_id="cgSgspJ2msm6clMCkdW9"):
 691 |     """Call ElevenLabs TTS API. Returns raw audio bytes (mp3)."""
 692 |     api_key = os.environ.get("ELEVENLABS_API_KEY", "")
 693 |     if not api_key:
 694 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
 695 |         if os.path.exists(env_path):
 696 |             for line in open(env_path):
 697 |                 if line.startswith("ELEVENLABS_API_KEY="):
 698 |                     api_key = line.strip().split("=", 1)[1].strip().strip("\"'")
 699 |     if not api_key:
 700 |         raise ValueError("ELEVENLABS_API_KEY not found in environment or .env")
 701 |     resp = http_requests.post(
 702 |         f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
 703 |         headers={"xi-api-key": api_key, "Content-Type": "application/json"},
 704 |         json={
 705 |             "text": text,
 706 |             "model_id": "eleven_turbo_v2_5",
 707 |             # LAW 3: Jessica voice settings — stability=0.45, similarity_boost=0.75, style=0.20
 708 |             "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.20},
 709 |         },
 710 |         timeout=60,
 711 |     )
 712 |     if resp.status_code != 200:
 713 |         raise Exception(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
 714 |     return resp.content
 715 | 
 716 | 
 717 | # ═══════════════════════════════════════════════════════════════════════
 718 | # FLASK ROUTES
 719 | # ═══════════════════════════════════════════════════════════════════════
 720 | 
 721 | @app.route("/health")
 722 | def health():
 723 |     """Enhanced health check with VRAM, latency, vision status, enhancer info."""
 724 |     reg = ModelRegistry.get() if ModelRegistry.is_loaded() else None
 725 |     vram = reg.vram_info() if reg else {"available": False}
 726 | 
 727 |     vision_enabled = bool(os.environ.get("GEMINI_API_KEY"))
 728 |     with _lock:
 729 |         avg_latency = round(sum(_request_times) / len(_request_times), 2) if _request_times else None
 730 |         tracked = len(_request_times)
 731 |     uptime = round(time.time() - _start_time, 1)
 732 | 
 733 |     return jsonify({
 734 |         "status": "ok",
 735 |         "engine": "wav2lip-gan-fp16-v2",
 736 |         "enhancements": ["fp16", "cached_face", "cv2_sharpen", "mediapipe_blinks", "head_movement"],
 737 |         "device": DEVICE,
 738 |         "model_loaded": reg is not None and reg.wav2lip_model is not None,
 739 |         "avatar_loaded": reg is not None and reg.avatar_face is not None,
 740 |         "avatar_size": (
 741 |             f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}"
 742 |             if reg and reg.avatar_face is not None else None
 743 |         ),
 744 |         "face_detected": reg is not None and reg.avatar_face_coords is not None,
 745 |         "face_enhancer": "cv2_sharpen_only",
 746 |         "blinks_enabled": True,  # v2 engine: cached landmarks
 747 |         "eye_landmarks_detected": (lambda: __import__("blink_engine")._load_cache() is not None)(),
 748 |         "vram": vram,
 749 |         "vision_enabled": vision_enabled,
 750 |         "uptime_sec": uptime,
 751 |         "avg_latency_sec": avg_latency,
 752 |         "requests_tracked": tracked,
 753 |         "output_fps": DEFAULT_FPS,
 754 |         "batch_size": BATCH_SIZE,
 755 |         "max_audio_seconds": MAX_AUDIO_SECONDS,
 756 |         "encoding": "crf23-ultrafast-512",
 757 |         "blink_config": {
 758 |             "interval": f"{BLINK_INTERVAL_MIN}-{BLINK_INTERVAL_MAX}s",
 759 |             "duration": f"{BLINK_DURATION}s"
 760 |         },
 761 |         "head_movement_config": {
 762 |             "rotation": f"\u00b1{HEAD_ROTATION_AMPLITUDE}\u00b0",
 763 |             "period": f"{HEAD_PERIOD}s"
 764 |         }
 765 |     })
 766 | 
 767 | 
 768 | @app.route("/status")
 769 | def status():
 770 |     """Alias for /health — frontend expects this route."""
 771 |     return health()
 772 | 
 773 | 
 774 | @app.route("/warmup", methods=["POST"])
 775 | def warmup():
 776 |     """Generate a tiny test video to warm up torch.compile and CUDA kernels."""
 777 |     t0 = time.time()
 778 |     reg = ModelRegistry.get()
 779 |     if reg.wav2lip_model is None:
 780 |         return jsonify({"error": "Model not loaded"}), 500
 781 | 
 782 |     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
 783 |         import wave
 784 |         with wave.open(tmp.name, "w") as wf:
 785 |             wf.setnchannels(1)
 786 |             wf.setsampwidth(2)
 787 |             wf.setframerate(16000)
 788 |             wf.writeframes(b"\x00\x00" * 8000)
 789 |         wav_path = tmp.name
 790 | 
 791 |     try:
 792 |         _render_semaphore.acquire()
 793 |         try:
 794 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
 795 |             if frames:
 796 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
 797 |         finally:
 798 |             _render_semaphore.release()
 799 |         elapsed = time.time() - t0
 800 |         logger.info(f"Warmup complete: {len(frames)} frames in {elapsed:.2f}s")
 801 |         return jsonify({
 802 |             "status": "warmed_up",
 803 |             "frames": len(frames),
 804 |             "warmup_time": round(elapsed, 2),
 805 |             "vram": reg.vram_info(),
 806 |         })
 807 |     except Exception as e:
 808 |         logger.error(f"Warmup error: {e}", exc_info=True)
 809 |         return jsonify({"error": str(e)}), 500
 810 |     finally:
 811 |         try:
 812 |             os.unlink(wav_path)
 813 |         except OSError:
 814 |             pass
 815 | 
 816 | 
 817 | @app.route("/generate", methods=["POST"])
 818 | def generate():
 819 |     """Generate lip-synced video with face restoration, blinks, and head movement.
 820 | 
 821 |     Accepts two modes:
 822 |       Mode A: {"text": "..."} -> Kokoro af_heart (or ElevenLabs fallback) -> Wav2Lip -> video
 823 |       Mode B: {"audio_base64": "...", "content_type": "..."} -> Wav2Lip -> video
 824 |     """
 825 |     data = request.get_json()
 826 |     if not data:
 827 |         return jsonify({"error": "JSON body required"}), 400
 828 | 
 829 |     # Input validation
 830 |     MAX_TEXT_LEN = 2000
 831 |     MAX_AUDIO_B64_LEN = 2_000_000  # ~1.5MB decoded
 832 |     if "text" in data:
 833 |         if not isinstance(data["text"], str) or len(data["text"]) > MAX_TEXT_LEN:
 834 |             return jsonify({"error": f"text must be a string under {MAX_TEXT_LEN} chars", "code": "INVALID_INPUT"}), 400
 835 |         if not data["text"].strip():
 836 |             return jsonify({"error": "text cannot be empty", "code": "INVALID_INPUT"}), 400
 837 |     elif "audio_base64" in data:
 838 |         if not isinstance(data["audio_base64"], str) or len(data["audio_base64"]) > MAX_AUDIO_B64_LEN:
 839 |             return jsonify({"error": "audio_base64 too large or invalid", "code": "INVALID_INPUT"}), 400
 840 |         try:
 841 |             base64.b64decode(data["audio_base64"], validate=True)
 842 |         except Exception:
 843 |             return jsonify({"error": "audio_base64 is not valid base64", "code": "INVALID_INPUT"}), 400
 844 |     else:
 845 |         return jsonify({"error": "text or audio_base64 required"}), 400
 846 | 
 847 |     enable_blinks = data.get("enable_blinks", True)  # v2 blink engine enabled
 848 |     enable_head_movement = data.get("enable_head_movement", True)
 849 |     fps = float(data.get("fps", DEFAULT_FPS))
 850 |     avatar_source = data.get("avatar_source", "default")
 851 |     if avatar_source not in AVATAR_SOURCES:
 852 |         avatar_source = "default"
 853 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
 854 | 
 855 |     # Resolve face for this render
 856 |     gen_face, gen_coords, _gen_eyes = _load_avatar_face(avatar_source)
 857 |     if gen_face is None or gen_coords is None:
 858 |         gen_face, gen_coords, _gen_eyes = _load_avatar_face("default")
 859 | 
 860 |     t_start = time.time()
 861 | 
 862 |     # Mode A: text -> Kokoro af_heart (primary) or ElevenLabs (fallback)
 863 |     if "text" in data:
 864 |         try:
 865 |             t_tts = time.time()
 866 |             audio_bytes = _avatar_tts(data["text"])
 867 |             logger.info(f"TTS: {len(audio_bytes)} bytes in {time.time()-t_tts:.2f}s")
 868 |         except Exception as e:
 869 |             logger.error(f"TTS error: {e}")
 870 |             return jsonify({"error": f"TTS failed: {e}"}), 500
 871 |         # Kokoro returns WAV, ElevenLabs returns MP3 — detect from header
 872 |         content_type = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
 873 |     # Mode B: raw audio
 874 |     elif "audio_base64" in data:
 875 |         audio_bytes = base64.b64decode(data["audio_base64"])
 876 |         content_type = data.get("content_type", "audio/mpeg")
 877 |     else:
 878 |         return jsonify({"error": "text or audio_base64 required"}), 400
 879 | 
 880 |     ext = ".mp3" if "mpeg" in content_type else ".wav"
 881 | 
 882 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
 883 |         tmp.write(audio_bytes)
 884 |         audio_path = tmp.name
 885 | 
 886 |     wav_path = audio_path + "_16k.wav"
 887 |     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
 888 | 
 889 |     # Input length guard: check audio duration
 890 |     try:
 891 |         import subprocess as _sp
 892 |         probe = _sp.run(
 893 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 894 |              "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
 895 |             capture_output=True, text=True, timeout=10,
 896 |         )
 897 |         audio_duration_sec = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
 898 |     except Exception as e:
 899 |         logger.error(f"[GENERATE] ffprobe failed: {e}", exc_info=True)
 900 |         audio_duration_sec = 0.0
 901 | 
 902 |     if audio_duration_sec == 0.0:
 903 |         logger.warning("[GENERATE] Audio duration is 0 — possible corrupt file")
 904 |         return jsonify({"error": "Audio validation failed: could not determine duration", "code": "INVALID_AUDIO"}), 400
 905 | 
 906 |     if audio_duration_sec > MAX_AUDIO_SECONDS:
 907 |         logger.warning(f"Audio too long ({audio_duration_sec:.1f}s > {MAX_AUDIO_SECONDS}s) — rejecting")
 908 |         return jsonify({
 909 |             "error": f"Audio too long ({audio_duration_sec:.1f}s). Max {MAX_AUDIO_SECONDS}s.",
 910 |             "code": "AUDIO_TOO_LONG",
 911 |             "max_seconds": MAX_AUDIO_SECONDS,
 912 |         }), 400
 913 | 
 914 |     try:
 915 |         reg = ModelRegistry.get()
 916 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
 917 |         if not acquired:
 918 |             return jsonify({"error": "GPU busy", "code": "GPU_BUSY", "retry_after": 5}), 503
 919 |         try:
 920 |             t0 = time.time()
 921 |             frames = wav2lip_generate(wav_path, fps, avatar_face=gen_face, avatar_face_coords=gen_coords)
 922 |             t_lip = time.time() - t0
 923 |             logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")
 924 | 
 925 |             # CV2 sharpen only — no GFPGAN
 926 |             t_enhance = 0.0
 927 |             if len(frames) > 0:
 928 |                 try:
 929 |                     t0_enh = time.time()
 930 |                     frames = sharpen_mouth_region(frames, gen_coords)
 931 |                     t_enhance = time.time() - t0_enh
 932 |                     logger.info(f"CV2 sharpen: {t_enhance:.2f}s")
 933 |                 except Exception as e:
 934 |                     logger.warning(f"Sharpen skipped: {e}")
 935 | 
 936 |             t0 = time.time()
 937 |             if enable_blinks or enable_head_movement:
 938 |                 frames = post_process_frames(
 939 |                     frames, fps,
 940 |                     enable_blinks=enable_blinks,
 941 |                     enable_head=enable_head_movement,
 942 |                 )
 943 |             t_post = time.time() - t0
 944 |             logger.info(f"Post-processing: {t_post:.2f}s")
 945 | 
 946 |             t0 = time.time()
 947 |             video_path = frames_to_video(frames, fps, audio_path=wav_path)
 948 |             t_encode = time.time() - t0
 949 |             logger.info(f"Encoding: {t_encode:.2f}s")
 950 |         finally:
 951 |             _render_semaphore.release()
 952 | 
 953 |         if not video_path:
 954 |             return jsonify({"error": "Video encoding failed", "code": "ENCODE_FAILED"}), 500
 955 | 
 956 |         t_total = time.time() - t_start
 957 |         _record_latency(t_total)
 958 |         duration = len(frames) / fps
 959 |         num_frames = len(frames)
 960 | 
 961 |         logger.info(
 962 |             f"Complete: {duration:.1f}s video, {num_frames} frames, "
 963 |             f"lip={t_lip:.1f}s enhance={t_enhance:.1f}s post={t_post:.1f}s enc={t_encode:.1f}s total={t_total:.1f}s"
 964 |         )
 965 | 
 966 |         cleanup_paths = [audio_path, wav_path, video_path]
 967 | 
 968 |         @after_this_request
 969 |         def _cleanup(response):
 970 |             for p in cleanup_paths:
 971 |                 try:
 972 |                     if p and os.path.exists(p):
 973 |                         os.unlink(p)
 974 |                 except OSError:
 975 |                     pass
 976 |             return response
 977 | 
 978 |         response = send_file(
 979 |             video_path,
 980 |             mimetype="video/mp4",
 981 |             as_attachment=True,
 982 |             download_name="oracle.mp4",
 983 |         )
 984 |         response.headers["X-Duration"] = str(round(duration, 2))
 985 |         response.headers["X-Frames"] = str(num_frames)
 986 |         response.headers["X-Processing-Time"] = str(round(t_total, 2))
 987 |         response.headers["X-Timing-Wav2Lip"] = str(round(t_lip, 2))
 988 |         response.headers["X-Timing-FaceEnhance"] = str(round(t_enhance, 2))
 989 |         response.headers["X-Timing-PostProcess"] = str(round(t_post, 2))
 990 |         response.headers["X-Timing-Encoding"] = str(round(t_encode, 2))
 991 |         return response
 992 | 
 993 |     except Exception as e:
 994 |         logger.error(f"Generation error: {e}", exc_info=True)
 995 |         return jsonify({"error": str(e), "code": "GENERATION_ERROR"}), 500
 996 |     finally:
 997 |         for p in [audio_path, wav_path]:
 998 |             try:
 999 |                 if os.path.exists(p):
1000 |                     os.unlink(p)
1001 |             except OSError:
1002 |                 pass
1003 | 
1004 | 
1005 | @app.route("/reload-avatar", methods=["POST"])
1006 | def reload_avatar():
1007 |     """Reload avatar source image via ModelRegistry."""
1008 |     reg = ModelRegistry.get()
1009 |     if reg.reload_avatar():
1010 |         return jsonify({
1011 |             "status": "reloaded",
1012 |             "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
1013 |             "face": reg.avatar_face_coords,
1014 |             "eye_landmarks": reg.eye_landmarks is not None,
1015 |         })
1016 |     else:
1017 |         return jsonify({"error": "No face detected in new image"}), 400
1018 | 
1019 | 
1020 | @app.route("/source-image")
1021 | def source_image():
1022 |     """Serve the current avatar source image."""
1023 |     reg = ModelRegistry.get()
1024 |     if reg.avatar_face is None:
1025 |         return jsonify({"error": "No avatar loaded"}), 404
1026 |     _, buf = cv2.imencode(".png", reg.avatar_face)
1027 |     b64 = base64.b64encode(buf).decode()
1028 |     return jsonify({
1029 |         "image_base64": b64,
1030 |         "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
1031 |         "face_coords": reg.avatar_face_coords
1032 |     })
1033 | 
1034 | 
1035 | # ═══════════════════════════════════════════════════════════════════════
1036 | # VISION GUIDE ENDPOINTS
1037 | # ═══════════════════════════════════════════════════════════════════════
1038 | 
1039 | @app.route("/vision/analyze", methods=["POST"])
1040 | def vision_analyze():
1041 |     """Analyze a Bitcoin hardware image with Gemini 2.5 Flash."""
1042 |     data = request.get_json()
1043 |     if not data or not data.get("image_base64"):
1044 |         return jsonify({"error": "image_base64 required"}), 400
1045 | 
1046 |     # Strip data URL prefix if present (client may send data:image/...;base64,)
1047 |     image_b64 = data["image_base64"]
1048 |     if image_b64.startswith("data:"):
1049 |         image_b64 = image_b64.split(",", 1)[1]
1050 | 
1051 |     from vision_guide import analyze_image, GuideSession
1052 |     result = analyze_image(
1053 |         image_b64=image_b64,
1054 |         mime_type=data.get("mime_type", "image/jpeg"),
1055 |         context=data.get("context", ""),
1056 |     )
1057 | 
1058 |     if "error" in result:
1059 |         return jsonify(result), 500
1060 | 
1061 |     # Create a GuideSession so follow-up /vision/guide calls have context
1062 |     guide_session = GuideSession.get_or_create(data.get("session_id"))
1063 |     result["session_id"] = guide_session.session_id
1064 | 
1065 |     # Seed the guide session history with this first analysis
1066 |     guide_session.history.append({
1067 |         "role": "user",
1068 |         "parts": [
1069 |             {"text": data.get("context", "Analyze this Bitcoin hardware image.")},
1070 |             {"inlineData": {"mimeType": data.get("mime_type", "image/jpeg"), "data": image_b64}},
1071 |         ],
1072 |     })
1073 |     guidance = result.get("guidance_text", "")
1074 |     if guidance:
1075 |         guide_session.history.append({
1076 |             "role": "model",
1077 |             "parts": [{"text": guidance}],
1078 |         })
1079 |     if result.get("device_name") and result["device_name"] != "unknown":
1080 |         guide_session.device_name = result["device_name"]
1081 | 
1082 |     # Phase 4: Store vision context in dialogue session for carry-forward
1083 |     session_id = data.get("session_id", "anon")
1084 |     try:
1085 |         from oracle_dialogue_engine import _get_session
1086 |         session = _get_session(session_id)
1087 |         vision_history = session.get("vision_history", [])
1088 |         analysis_summary = result.get("summary", "") or str(result.get("device_name", ""))
1089 |         if result.get("current_step"):
1090 |             analysis_summary += f" — {result['current_step']}"
1091 |         vision_history.append({
1092 |             "turn": session.get("turn", 0),
1093 |             "summary": analysis_summary[:200],
1094 |         })
1095 |         session["vision_history"] = vision_history[-3:]  # keep last 3
1096 |     except Exception as e:
1097 |         logger.warning(f"[VISION] Failed to store vision context: {e}")
1098 | 
1099 |     return jsonify(result)
1100 | 
1101 | 
1102 | @app.route("/vision/guide", methods=["POST"])
1103 | def vision_guide():
1104 |     """Multi-turn hardware setup guide session."""
1105 |     data = request.get_json()
1106 |     if not data:
1107 |         return jsonify({"error": "JSON body required"}), 400
1108 | 
1109 |     from vision_guide import GuideSession
1110 |     session = GuideSession.get_or_create(data.get("session_id"))
1111 | 
1112 |     if data.get("image_base64"):
1113 |         # Strip data URL prefix if present
1114 |         img_b64 = data["image_base64"]
1115 |         if img_b64.startswith("data:"):
1116 |             img_b64 = img_b64.split(",", 1)[1]
1117 |         question = data.get("question", "")
1118 |         last_context = data.get("last_context", "")
1119 |         if last_context:
1120 |             question += f"\n\nUser completed these steps: {last_context}\nNow showing the next screen."
1121 |         result = session.send_image(
1122 |             image_b64=img_b64,
1123 |             mime_type=data.get("mime_type", "image/jpeg"),
1124 |             question=question,
1125 |         )
1126 |     elif data.get("question"):
1127 |         result = session.send_text(data["question"])
1128 |     else:
1129 |         return jsonify({"error": "image_base64 or question required"}), 400
1130 | 
1131 |     if "error" in result:
1132 |         return jsonify(result), 500
1133 |     return jsonify(result)
1134 | 
1135 | 
1136 | @app.route("/vision/status")
1137 | def vision_status():
1138 |     """Check if vision features are enabled."""
1139 |     gemini_key = os.environ.get("GEMINI_API_KEY", "")
1140 |     enabled = bool(gemini_key)
1141 |     if enabled:
1142 |         return jsonify({
1143 |             "status": "enabled",
1144 |             "model": "gemini-2.5-flash",
1145 |             "endpoints": ["/vision/analyze", "/vision/guide", "/vision/sessions"],
1146 |         })
1147 |     else:
1148 |         return jsonify({
1149 |             "status": "disabled",
1150 |             "reason": "GEMINI_API_KEY not configured",
1151 |             "setup_url": "https://aistudio.google.com/apikey",
1152 |         })
1153 | 
1154 | 
1155 | @app.route("/vision/sessions")
1156 | def vision_sessions():
1157 |     """List active vision guide sessions."""
1158 |     from vision_guide import GuideSession
1159 |     return jsonify({
1160 |         "active_sessions": GuideSession.active_count(),
1161 |     })
1162 | 
1163 | 
1164 | # ═══════════════════════════════════════════════════════════════════════
1165 | # STREAMING PIPELINE
1166 | # ═══════════════════════════════════════════════════════════════════════
1167 | 
1168 | import re
1169 | import uuid
1170 | import subprocess
1171 | 
1172 | ORACLE_SYSTEM_PROMPT = (
1173 |     "You are the Oracle — Protocol Pulse's personal Bitcoin intelligence guide. "
1174 |     "You are having a private one-on-one conversation with a visitor. "
1175 |     "You are an EDUCATOR (explain Bitcoin at any level), GUIDE (help navigate Protocol Pulse), "
1176 |     "TECHNICAL ASSISTANT (wallets, self-custody, nodes, hardware), and INTELLIGENCE ANALYST "
1177 |     "(market state, price action — conversational, not broadcast). "
1178 |     "TONE: Warm but sharp. Knowledgeable without being condescending. "
1179 |     "Like the smartest person in Bitcoin who actually has time for you. "
1180 |     "Keep responses under 3 sentences. Never say 'As an AI' or offer daily briefs unprompted. "
1181 |     "You are NOT a news anchor or briefing bot — you are a personal guide."
1182 | )
1183 | ORACLE_VOICE_ID = "cgSgspJ2msm6clMCkdW9"  # Jessica
1184 | ORACLE_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
1185 | ORACLE_IDLE_PATH = os.path.join(ORACLE_STATIC_DIR, "oracle_idle.mp4")
1186 | 
1187 | _stream_sessions = {}
1188 | _stream_lock = threading.Lock()
1189 | 
1190 | 
1191 | def _get_anthropic_key():
1192 |     """Get Anthropic API key from env or .env file."""
1193 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
1194 |     if not key:
1195 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
1196 |         if os.path.exists(env_path):
1197 |             for line in open(env_path):
1198 |                 if line.startswith("ANTHROPIC_API_KEY="):
1199 |                     key = line.strip().split("=", 1)[1].strip().strip("\"'")
1200 |     return key
1201 | 
1202 | 
1203 | def _split_sentences(text):
1204 |     """Split text into sentences for chunked processing."""
1205 |     sentences = re.split(r'(?<=[.!?])\s+', text.strip())
1206 |     return [s for s in sentences if s.strip()]
1207 | 
1208 | 
1209 | def _generate_chunk(sentence, chunk_num, session_dir, fps=30.0):
1210 |     """Generate a single video chunk for a sentence: TTS -> Wav2Lip -> MP4."""
1211 |     try:
1212 |         audio_bytes = _avatar_tts(sentence)
1213 |         is_wav = audio_bytes[:4] == b"RIFF"
1214 |         ext = ".wav" if is_wav else ".mp3"
1215 |         audio_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}{ext}")
1216 |         with open(audio_path, "wb") as f:
1217 |             f.write(audio_bytes)
1218 | 
1219 |         wav_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}_16k.wav")
1220 |         if is_wav:
1221 |             # F5 already returned 16kHz mono WAV — just copy
1222 |             import shutil
1223 |             shutil.copy2(audio_path, wav_path)
1224 |         else:
1225 |             subprocess.run(
1226 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
1227 |                 check=True, capture_output=True,
1228 |             )
1229 | 
1230 |         _render_semaphore.acquire()
1231 |         try:
1232 |             frames = wav2lip_generate(wav_path, fps)
1233 |             reg = ModelRegistry.get()
1234 |             try:
1235 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1236 |             except Exception as e:
1237 |                 logger.warning(f"[CHUNK] Sharpening failed on chunk {chunk_num}: {e}", exc_info=True)
1238 |             frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1239 |         finally:
1240 |             _render_semaphore.release()
1241 | 
1242 |         video_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}.mp4")
1243 |         tmp_path = frames_to_video(frames, fps, audio_path=wav_path)
1244 |         if tmp_path:
1245 |             os.rename(tmp_path, video_path)
1246 |             return video_path
1247 |         return None
1248 |     except Exception as e:
1249 |         logger.error(f"Chunk {chunk_num} generation error: {e}", exc_info=True)
1250 |         return None
1251 | 
1252 | 
1253 | def _stream_worker(session_id, text):
1254 |     """Background worker: call Claude -> split sentences -> generate chunks."""
1255 |     session = _stream_sessions.get(session_id)
1256 |     if not session:
1257 |         return
1258 | 
1259 |     try:
1260 |         api_key = _get_anthropic_key()
1261 |         if not api_key:
1262 |             logger.warning("No Anthropic key — using input text as-is")
1263 |             ai_text = text
1264 |         else:
1265 |             resp = http_requests.post(
1266 |                 "https://api.anthropic.com/v1/messages",
1267 |                 headers={
1268 |                     "x-api-key": api_key,
1269 |                     "anthropic-version": "2023-06-01",
1270 |                     "content-type": "application/json",
1271 |                 },
1272 |                 json={
1273 |                     "model": "claude-sonnet-4-20250514",
1274 |                     "max_tokens": 80,  # Short transcript = fewer TTS seconds = fewer Wav2Lip frames
1275 |                     "system": ORACLE_SYSTEM_PROMPT,
1276 |                     "messages": [{"role": "user", "content": text}],
1277 |                 },
1278 |                 timeout=30,
1279 |             )
1280 |             if resp.status_code == 200:
1281 |                 ai_text = resp.json()["content"][0]["text"]
1282 |             else:
1283 |                 logger.error(f"Claude API error {resp.status_code}: {resp.text[:200]}")
1284 |                 ai_text = text
1285 | 
1286 |         session["ai_response"] = ai_text
1287 |         sentences = _split_sentences(ai_text)
1288 |         session["total_chunks"] = len(sentences)
1289 | 
1290 |         session_dir = session["dir"]
1291 |         for i, sentence in enumerate(sentences):
1292 |             chunk_path = _generate_chunk(sentence, i, session_dir)
1293 |             if chunk_path:
1294 |                 session["chunks_ready"].append(chunk_path)
1295 |             else:
1296 |                 session["errors"].append(f"Chunk {i} failed")
1297 | 
1298 |         session["status"] = "complete"
1299 | 
1300 |     except Exception as e:
1301 |         logger.error(f"Stream worker error: {e}", exc_info=True)
1302 |         session["status"] = "error"
1303 |         session["errors"].append(str(e))
1304 | 
1305 | 
1306 | @app.route("/generate_stream", methods=["POST"])
1307 | def generate_stream():
1308 |     """Start streaming generation: text -> Claude -> sentence chunks -> video chunks."""
1309 |     data = request.get_json()
1310 |     if not data or not data.get("text"):
1311 |         return jsonify({"error": "text required"}), 400
1312 | 
1313 |     session_id = str(uuid.uuid4())[:12]
1314 |     session_dir = os.path.join(tempfile.gettempdir(), f"oracle_stream_{session_id}")
1315 |     os.makedirs(session_dir, exist_ok=True)
1316 | 
1317 |     session = {
1318 |         "id": session_id,
1319 |         "status": "processing",
1320 |         "text": data["text"],
1321 |         "ai_response": None,
1322 |         "total_chunks": 0,
1323 |         "chunks_ready": [],
1324 |         "errors": [],
1325 |         "dir": session_dir,
1326 |         "created": time.time(),
1327 |     }
1328 | 
1329 |     with _stream_lock:
1330 |         _stream_sessions[session_id] = session
1331 | 
1332 |     thread = threading.Thread(target=_stream_worker, args=(session_id, data["text"]), daemon=True)
1333 |     thread.start()
1334 | 
1335 |     return jsonify({
1336 |         "session_id": session_id,
1337 |         "status": "processing",
1338 |         "message": "Stream generation started. Poll /stream_status/{session_id} for progress.",
1339 |     })
1340 | 
1341 | 
1342 | @app.route("/stream_status/<session_id>")
1343 | def stream_status(session_id):
1344 |     """Poll for streaming generation progress."""
1345 |     session = _stream_sessions.get(session_id)
1346 |     if not session:
1347 |         return jsonify({"error": "Session not found"}), 404
1348 | 
1349 |     return jsonify({
1350 |         "session_id": session_id,
1351 |         "status": session["status"],
1352 |         "ai_response": session.get("ai_response"),
1353 |         "chunks_ready": len(session["chunks_ready"]),
1354 |         "total_chunks": session["total_chunks"],
1355 |         "total_estimated": max(session["total_chunks"], 3),
1356 |         "errors": session["errors"],
1357 |     })
1358 | 
1359 | 
1360 | @app.route("/stream_chunk/<session_id>/<int:chunk_number>")
1361 | def stream_chunk(session_id, chunk_number):
1362 |     """Fetch a generated video chunk by number."""
1363 |     session = _stream_sessions.get(session_id)
1364 |     if not session:
1365 |         return jsonify({"error": "Session not found"}), 404
1366 | 
1367 |     if chunk_number >= len(session["chunks_ready"]):
1368 |         return jsonify({"error": "Chunk not ready yet"}), 404
1369 | 
1370 |     chunk_path = session["chunks_ready"][chunk_number]
1371 |     if not os.path.exists(chunk_path):
1372 |         return jsonify({"error": "Chunk file missing"}), 500
1373 | 
1374 |     return send_file(chunk_path, mimetype="video/mp4", as_attachment=True,
1375 |                      download_name=f"chunk_{chunk_number:03d}.mp4")
1376 | 
1377 | 
1378 | @app.route("/oracle_idle")
1379 | def oracle_idle():
1380 |     """Serve the pre-rendered idle loop video."""
1381 |     if os.path.exists(ORACLE_IDLE_PATH):
1382 |         return send_file(ORACLE_IDLE_PATH, mimetype="video/mp4")
1383 |     return jsonify({"error": "Idle video not generated yet"}), 404
1384 | 
1385 | 
1386 | def generate_idle_loop():
1387 |     """Generate a 4-second idle loop with blinks + head movement (no audio)."""
1388 |     os.makedirs(ORACLE_STATIC_DIR, exist_ok=True)
1389 |     if os.path.exists(ORACLE_IDLE_PATH):
1390 |         logger.info("Idle loop already exists, skipping generation")
1391 |         return
1392 | 
1393 |     logger.info("Generating idle loop video...")
1394 |     reg = ModelRegistry.get()
1395 |     if reg.avatar_face is None:
1396 |         logger.error("Cannot generate idle loop: no avatar loaded")
1397 |         return
1398 | 
1399 |     fps = DEFAULT_FPS
1400 |     duration = 4.0
1401 |     num_frames = int(duration * fps)
1402 | 
1403 |     base_frame = reg.avatar_face.copy()
1404 |     frames = [base_frame.copy() for _ in range(num_frames)]
1405 | 
1406 |     frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1407 | 
1408 |     video_path = frames_to_video(frames, fps, audio_path=None)
1409 |     if video_path:
1410 |         os.rename(video_path, ORACLE_IDLE_PATH)
1411 |         logger.info(f"Idle loop saved: {ORACLE_IDLE_PATH} ({num_frames} frames)")
1412 |     else:
1413 |         logger.error("Failed to generate idle loop")
1414 | 
1415 | 
1416 | # ═══════════════════════════════════════════════════════════════════════
1417 | # ORACLE PRE-CACHE + INTELLIGENCE ENDPOINTS
1418 | # ═══════════════════════════════════════════════════════════════════════
1419 | 
1420 | import oracle_cache_manager
1421 | import oracle_intelligence_feed
1422 | import oracle_dialogue_engine
1423 | 
1424 | # Intent classification — keyword matching
1425 | INTENT_PATTERNS = {
1426 |     "DAILY_BRIEF": r"brief|today|news|happening|what's|latest",
1427 |     "SOVEREIGNTY_INTRO": r"sovereign|score|free",
1428 |     "SOVEREIGNTY_COLD_WALLET": r"cold.?wallet|hardware|ledger|coldcard|custody",
1429 |     "SOVEREIGNTY_NODE": r"node|umbrel|raspberry|verify",
1430 |     "SOVEREIGNTY_BITAXE": r"bitaxe|mine|mining|solo",
1431 |     "SOVEREIGNTY_LIFE_INSURANCE": r"insurance|meanwhile|estate|death",
1432 |     "SOVEREIGNTY_RESIDENCY": r"residency|palau|rns|passport|citizenship",
1433 |     "GOODBYE": r"bye|goodbye|later|thanks",
1434 | }
1435 | 
1436 | 
1437 | def classify_intent(transcript):
1438 |     """Classify user transcript to an intent key. Returns (intent, confidence)."""
1439 |     text = transcript.lower().strip()
1440 |     for intent, pattern in INTENT_PATTERNS.items():
1441 |         if re.search(pattern, text):
1442 |             return intent, 0.85
1443 |     return "UNKNOWN", 0.4
1444 | 
1445 | 
1446 | @app.route("/oracle/cache/status")
1447 | def oracle_cache_status():
1448 |     """Return status of pre-cached responses and daily brief."""
1449 |     cache_status = oracle_cache_manager.get_cache_status()
1450 |     daily_brief = oracle_intelligence_feed.get_daily_brief()
1451 |     return jsonify({
1452 |         "cached_responses": cache_status,
1453 |         "daily_brief_ready": daily_brief is not None,
1454 |         "daily_brief_path": daily_brief,
1455 |         "cache_ttl_s": oracle_cache_manager.CACHE_TTL,
1456 |     })
1457 | 
1458 | 
1459 | @app.route("/oracle/response/<key>")
1460 | def oracle_response(key):
1461 |     """Serve pre-cached mp4 for a response key."""
1462 |     key = key.upper()
1463 |     if key not in oracle_cache_manager.RESPONSE_TREE and key != "DAILY_BRIEF_LIVE":
1464 |         return jsonify({"error": "Unknown response key", "valid_keys": list(oracle_cache_manager.RESPONSE_TREE.keys())}), 404
1465 | 
1466 |     # Daily brief special case
1467 |     if key == "DAILY_BRIEF_LIVE":
1468 |         path = oracle_intelligence_feed.get_daily_brief()
1469 |         if path:
1470 |             return send_file(path, mimetype="video/mp4")
1471 |         return jsonify({"error": "Daily brief not ready yet", "status": "pending"}), 202
1472 | 
1473 |     # Check if rendering
1474 |     if oracle_cache_manager.is_rendering(key):
1475 |         return jsonify({"error": "Response is being rendered", "status": "rendering"}), 202
1476 | 
1477 |     path = oracle_cache_manager.get_cached_response(key)
1478 |     if path:
1479 |         return send_file(path, mimetype="video/mp4")
1480 | 
1481 |     return jsonify({"error": "Response not cached yet", "status": "pending"}), 202
1482 | 
1483 | 
1484 | @app.route("/oracle/speak", methods=["POST"])
1485 | def oracle_speak():
1486 |     """Serve cached response for an intent, or fallback to /generate."""
1487 |     data = request.get_json()
1488 |     if not data or not data.get("intent"):
1489 |         return jsonify({"error": "intent required"}), 400
1490 | 
1491 |     intent = data["intent"].upper()
1492 | 
1493 |     # Try daily brief
1494 |     if intent == "DAILY_BRIEF":
1495 |         brief_path = oracle_intelligence_feed.get_daily_brief()
1496 |         if brief_path:
1497 |             return send_file(brief_path, mimetype="video/mp4")
1498 |         # Fallback to intro
1499 |         intent = "DAILY_BRIEF_INTRO"
1500 | 
1501 |     # If caller provided explicit text, use it directly (broadcast segments, custom scripts)
1502 |     caller_text = (data.get("text") or "").strip()
1503 |     if caller_text:
1504 |         return generate_inline(caller_text)
1505 | 
1506 |     # Try cached response
1507 |     path = oracle_cache_manager.get_cached_response(intent)
1508 |     if path:
1509 |         return send_file(path, mimetype="video/mp4")
1510 | 
1511 |     # Fallback: generate on the fly — but don't block if GPU is busy (cache warming)
1512 |     text = oracle_cache_manager.RESPONSE_TREE.get(intent)
1513 |     if not text:
1514 |         text = oracle_cache_manager.RESPONSE_TREE["UNKNOWN_QUESTION"]
1515 | 
1516 |     # Check GPU availability — thread-safe acquire then release before generate_inline re-acquires
1517 |     acquired = _render_semaphore.acquire(timeout=5)
1518 |     if not acquired:
1519 |         return jsonify({"error": "GPU busy warming cache — try again shortly",
1520 |                         "status": "warming", "retry_after": 30}), 503
1521 |     _render_semaphore.release()  # release immediately, generate_inline re-acquires
1522 | 
1523 |     return generate_inline(text)
1524 | 
1525 | 
1526 | def generate_inline(text):
1527 |     """Internal helper: generate a video from text and return it."""
1528 |     try:
1529 |         audio_bytes = _avatar_tts(text)
1530 |     except Exception as e:
1531 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1532 | 
1533 |     is_wav = audio_bytes[:4] == b"RIFF"
1534 |     ext = ".wav" if is_wav else ".mp3"
1535 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1536 |         tmp.write(audio_bytes)
1537 |         audio_path = tmp.name
1538 | 
1539 |     wav_path = audio_path + "_16k.wav"
1540 |     if is_wav:
1541 |         import shutil
1542 |         shutil.copy2(audio_path, wav_path)
1543 |     else:
1544 |         subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1545 | 
1546 |     try:
1547 |         # Check queue state for concurrency visibility
1548 |         with _render_queue_lock:
1549 |             _queue_pos = _render_queue_count
1550 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
1551 |         if not acquired:
1552 |             return jsonify({"error": "GPU busy — try again in a moment", "retry_after": 10,
1553 |                             "queue_position": _queue_pos}), 503
1554 |         try:
1555 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
1556 |             reg = ModelRegistry.get()
1557 |             try:
1558 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1559 |             except Exception as e:
1560 |                 logger.warning(f"[INLINE] Sharpening failed: {e}", exc_info=True)
1561 |             frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1562 |             video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1563 |         finally:
1564 |             _render_semaphore.release()
1565 | 
1566 |         if not video_path:
1567 |             return jsonify({"error": "Video encoding failed"}), 500
1568 | 
1569 |         # Stream video as inline (not attachment) so browser plays it directly.
1570 |         # Generator pattern ensures file stays on disk until fully sent,
1571 |         # then cleans up. Fixes iOS mid-stream cutoff + double-unlink race.
1572 |         def _stream_and_cleanup():
1573 |             try:
1574 |                 with open(video_path, "rb") as vf:
1575 |                     while True:
1576 |                         chunk = vf.read(65536)
1577 |                         if not chunk:
1578 |                             break
1579 |                         yield chunk
1580 |             finally:
1581 |                 for p in [audio_path, wav_path, video_path]:
1582 |                     try:
1583 |                         if p and os.path.exists(p):
1584 |                             os.unlink(p)
1585 |                     except OSError:
1586 |                         pass
1587 | 
1588 |         from flask import Response
1589 |         return Response(
1590 |             _stream_and_cleanup(),
1591 |             mimetype="video/mp4",
1592 |             headers={
1593 |                 "Content-Disposition": "inline",
1594 |                 "X-Accel-Buffering": "no",
1595 |                 "Cache-Control": "no-cache",
1596 |             },
1597 |         )
1598 | 
1599 |     except Exception as e:
1600 |         logger.error(f"generate_inline error: {e}", exc_info=True)
1601 |         for p in [audio_path, wav_path]:
1602 |             try:
1603 |                 if os.path.exists(p): os.unlink(p)
1604 |             except OSError:
1605 |                 pass
1606 |         return jsonify({"error": str(e)}), 500
1607 | 
1608 | 
1609 | 
1610 | 
1611 | 
1612 | 
1613 | @app.route("/oracle/voice", methods=["POST"])
1614 | def oracle_voice():
1615 |     """
1616 |     Voice-only endpoint: text -> ElevenLabs TTS -> audio/mpeg.
1617 |     No Wav2Lip, no GPU. ~400ms vs ~14s for full video.
1618 |     Use for vision guidance, quick confirmations, non-visual responses.
1619 |     Body: {"text": "...", "voice_id": "optional"}
1620 |     """
1621 |     data = request.get_json()
1622 |     if not data or not data.get("text"):
1623 |         return jsonify({"error": "text required"}), 400
1624 | 
1625 |     text = data["text"].strip()
1626 | 
1627 |     try:
1628 |         t0 = time.time()
1629 |         audio_bytes = _avatar_tts(text)
1630 |         logger.info(f"[VOICE] TTS {len(audio_bytes)}B in {time.time()-t0:.2f}s")
1631 |     except Exception as e:
1632 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1633 | 
1634 |     # Loudnorm pass if not already normalized (WAV from Kokoro is already normalized in _avatar_tts,
1635 |     # but ElevenLabs MP3 fallback is not)
1636 |     is_wav = audio_bytes[:4] == b"RIFF"
1637 |     if not is_wav:
1638 |         try:
1639 |             with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as _tmp:
1640 |                 _tmp.write(audio_bytes)
1641 |                 _raw_path = _tmp.name
1642 |             _norm_path = _raw_path + "_norm.wav"
1643 |             _nr = subprocess.run(
1644 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", _raw_path,
1645 |                  "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
1646 |                  "-ar", "16000", "-ac", "1", _norm_path],
1647 |                 capture_output=True, text=True, timeout=30,
1648 |             )
1649 |             if _nr.returncode == 0 and os.path.exists(_norm_path) and os.path.getsize(_norm_path) > 1000:
1650 |                 with open(_norm_path, "rb") as _nf:
1651 |                     audio_bytes = _nf.read()
1652 |                 is_wav = True
1653 |             for _p in [_raw_path, _norm_path]:
1654 |                 try:
1655 |                     os.remove(_p)
1656 |                 except OSError:
1657 |                     pass
1658 |         except Exception as _ne:
1659 |             logger.warning(f"[VOICE] loudnorm failed (non-fatal): {_ne}")
1660 | 
1661 |     mime = "audio/wav" if is_wav else "audio/mpeg"
1662 | 
1663 |     from flask import Response
1664 |     return Response(
1665 |         audio_bytes,
1666 |         mimetype=mime,
1667 |         headers={
1668 |             "Content-Disposition": "inline",
1669 |             "Content-Length": str(len(audio_bytes)),
1670 |             "Cache-Control": "no-cache",
1671 |         },
1672 |     )
1673 | 
1674 | @app.route("/oracle/job/<job_id>")
1675 | def oracle_job_status(job_id):
1676 |     """Poll for async video render completion."""
1677 |     # Expire stale jobs (pending older than TTL, or completed older than 30s)
1678 |     now = time.time()
1679 |     with _render_jobs_lock:
1680 |         expired = []
1681 |         for k, v in _render_jobs.items():
1682 |             if v.get("completed_at"):
1683 |                 # Completed jobs: keep for 30s after completion
1684 |                 if now - v["completed_at"] > 30:
1685 |                     expired.append(k)
1686 |             elif now - v.get("created", 0) > _RENDER_JOB_TTL:
1687 |                 expired.append(k)
1688 |         for k in expired:
1689 |             del _render_jobs[k]
1690 |         job = _render_jobs.get(job_id)
1691 |     if not job:
1692 |         return jsonify({"status": "not_found"}), 404
1693 |     if job["status"] == "done":
1694 |         # Mark completed_at on first successful poll (keep job for 30s)
1695 |         if not job.get("completed_at"):
1696 |             with _render_jobs_lock:
1697 |                 if job_id in _render_jobs:
1698 |                     _render_jobs[job_id]["completed_at"] = time.time()
1699 |         video_bytes = job["video_bytes"]
1700 |         from flask import Response
1701 |         return Response(video_bytes, mimetype="video/mp4",
1702 |                         headers={"Content-Disposition": "inline", "Cache-Control": "no-cache"})
1703 |     if job["status"] == "error":
1704 |         # Mark completed_at for errors too
1705 |         if not job.get("completed_at"):
1706 |             with _render_jobs_lock:
1707 |                 if job_id in _render_jobs:
1708 |                     _render_jobs[job_id]["completed_at"] = time.time()
1709 |         return jsonify({"status": "error"}), 500
1710 |     return jsonify({"status": "pending"}), 202
1711 | 
1712 | 
1713 | @app.route("/oracle/job/<job_id>/audio")
1714 | def oracle_job_audio(job_id):
1715 |     """Return cached TTS audio from an async render job (avoids duplicate Kokoro call)."""
1716 |     with _render_jobs_lock:
1717 |         job = _render_jobs.get(job_id)
1718 |     if not job:
1719 |         return jsonify({"status": "not_found"}), 404
1720 |     if not job.get("audio_bytes"):
1721 |         # Audio not yet generated — tell client to poll again
1722 |         return jsonify({"status": "pending", "retry_after": 2}), 202
1723 |     audio_bytes = job["audio_bytes"]
1724 |     mime = job.get("audio_mime", "audio/wav")
1725 |     from flask import Response
1726 |     return Response(audio_bytes, mimetype=mime,
1727 |                     headers={"Content-Disposition": "inline",
1728 |                              "Content-Length": str(len(audio_bytes)),
1729 |                              "Cache-Control": "no-cache"})
1730 | 
1731 | 
1732 | @app.route("/oracle/chat", methods=["POST"])
1733 | def oracle_chat():
1734 |     data = request.get_json()
1735 |     if not data or not data.get("text"):
1736 |         return jsonify({"error": "text required"}), 400
1737 |     text = data["text"].strip()
1738 |     session_id = data.get("session_id", "anon")
1739 |     audio_first = data.get("audio_first", False)
1740 |     avatar_source = data.get("avatar_source", "default")
1741 |     if avatar_source not in AVATAR_SOURCES:
1742 |         avatar_source = "default"
1743 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
1744 | 
1745 |     # ── Phase 3: Visitor fingerprint + memory ──────────────────────────
1746 |     from oracle_memory import make_fingerprint, load_visitor
1747 |     visitor_token = data.get("visitor_token", "anon")
1748 |     raw_ip = (request.headers.get("X-Forwarded-For", "") or request.remote_addr or "").split(",")[0].strip()
1749 |     ua = request.headers.get("User-Agent", "")
1750 |     fingerprint = make_fingerprint(raw_ip, ua, visitor_token)
1751 | 
1752 |     session = oracle_dialogue_engine._get_session(session_id)
1753 |     if session["turn"] == 0:
1754 |         memory = load_visitor(fingerprint)
1755 |         if memory:
1756 |             session["visitor_memory"] = memory
1757 |             logger.info(f"[MEMORY] Returning visitor — session #{memory['session_count']}")
1758 |             if memory.get("recent_turns"):
1759 |                 # Pre-warm session with last exchange so Oracle has context immediately
1760 |                 recent = memory["recent_turns"]
1761 |                 if recent:
1762 |                     last = recent[-1]
1763 |                     if last.get("user") and last.get("oracle"):
1764 |                         session["history"] = [
1765 |                             {"role": "user", "content": f"[PRIOR SESSION] {last['user']}"},
1766 |                             {"role": "assistant", "content": f"[PRIOR SESSION] {last['oracle']}"},
1767 |                         ]
1768 |                         logger.info(f"[MEMORY] Pre-warmed session with {len(recent)} prior turns")
1769 |     session["fingerprint"] = fingerprint
1770 | 
1771 |     _sess_turn = oracle_dialogue_engine.get_session_info(session_id).get("turn", 0)
1772 |     if data.get("use_cache_for_intents", True) and _sess_turn == 0:
1773 |         intent, confidence = classify_intent(text)
1774 |         if confidence >= 0.8 and intent != "UNKNOWN":
1775 |             path = oracle_cache_manager.get_cached_response(intent)
1776 |             if path:
1777 |                 logger.info(f"[CHAT] Cache hit {intent}")
1778 |                 return send_file(path, mimetype="video/mp4")
1779 |     elif _sess_turn > 0:
1780 |         logger.info(f"[CHAT] Cache skipped turn={_sess_turn}")
1781 |     live_intel = {}
1782 |     try:
1783 |         live_intel = oracle_dialogue_engine.get_live_intel()
1784 |     except Exception:
1785 |         pass
1786 |     page_context = data.get("page_context", None)
1787 |     result = oracle_dialogue_engine.generate_response(session_id, text, live_intel, page_context)
1788 |     logger.info(f"[CHAT] {session_id} t={result['turn']} p={result['personality']} ctx={page_context.get('type','?') if page_context else 'none'}: {result['text'][:50]}")
1789 | 
1790 |     # ── Background memory save — persist after every turn, not just on unload ──
1791 |     try:
1792 |         _fp = session.get("fingerprint")
1793 |         _hist = session.get("history", [])
1794 |         if _fp and len(_hist) >= 2:
1795 |             import threading as _mem_threading
1796 |             def _bg_save():
1797 |                 try:
1798 |                     from oracle_memory import save_visitor
1799 |                     _flow = session.get("setup_flow", {})
1800 |                     _prev = session.get("visitor_memory", {})
1801 |                     # Store last 3 user+oracle pairs as recent_turns
1802 |                     _turns = []
1803 |                     for i in range(0, min(6, len(_hist)), 2):
1804 |                         if i+1 < len(_hist):
1805 |                             _turns.append({
1806 |                                 "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1807 |                                 "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1808 |                             })
1809 |                     save_visitor(_fp, {
1810 |                         "personality": session.get("personality", "AMIABLE"),
1811 |                         "session_summaries": _prev.get("session_summaries", []),
1812 |                         "setup_device": _flow.get("device"),
1813 |                         "setup_step": _flow.get("step", 0),
1814 |                         "topics_seen": list(session.get("topics_discussed", [])),
1815 |                         "products_shown": list(session.get("products_mentioned", [])),
1816 |                         "recent_turns": list(reversed(_turns)),
1817 |                     })
1818 |                 except Exception as _se:
1819 |                     logger.debug(f"[MEMORY] bg save error: {_se}")
1820 |             _mem_threading.Thread(target=_bg_save, daemon=True).start()
1821 |     except Exception:
1822 |         pass
1823 | 
1824 |     if audio_first:
1825 |         # Phase A: return text immediately, fire video render in background
1826 |         job_id = uuid.uuid4().hex[:16]
1827 |         with _render_jobs_lock:
1828 |             _render_jobs[job_id] = {"status": "pending", "video_bytes": None, "created": time.time()}
1829 | 
1830 |         response_text = result["text"]
1831 | 
1832 |         def render_async(txt, jid, src_name="default"):
1833 |             logger.info(f"[RENDER_ASYNC] STARTED job {jid} source={src_name} text={txt[:60]}...")
1834 |             try:
1835 |                 # Resolve avatar source for this render
1836 |                 a_face, a_coords, _a_eyes = _load_avatar_face(src_name)
1837 |                 if a_face is None or a_coords is None:
1838 |                     logger.warning(f"[ASYNC RENDER] Avatar source '{src_name}' failed, falling back to default")
1839 |                     a_face, a_coords, _a_eyes = _load_avatar_face("default")
1840 | 
1841 |                 audio_bytes = _avatar_tts(txt)
1842 |                 # Cache audio in job dict so frontend can fetch it without calling Kokoro again
1843 |                 with _render_jobs_lock:
1844 |                     if jid in _render_jobs:
1845 |                         _render_jobs[jid]["audio_bytes"] = audio_bytes
1846 |                         _render_jobs[jid]["audio_mime"] = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
1847 |                 is_wav = audio_bytes[:4] == b"RIFF"
1848 |                 ext = ".wav" if is_wav else ".mp3"
1849 |                 with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1850 |                     tmp.write(audio_bytes)
1851 |                     audio_path = tmp.name
1852 |                 wav_path = audio_path + "_16k.wav"
1853 |                 if is_wav:
1854 |                     import shutil
1855 |                     shutil.copy2(audio_path, wav_path)
1856 |                 else:
1857 |                     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1858 |                 try:
1859 |                     acquired = _render_semaphore.acquire(timeout=60)
1860 |                     if not acquired:
1861 |                         logger.warning(f"[ASYNC RENDER] GPU busy for job {jid}")
1862 |                         with _render_jobs_lock:
1863 |                             if jid in _render_jobs:
1864 |                                 _render_jobs[jid] = {"status": "error", "video_bytes": None,
1865 |                                                      "created": time.time(), "code": "GPU_BUSY"}
1866 |                         return
1867 |                     try:
1868 |                         frames = wav2lip_generate(wav_path, DEFAULT_FPS, avatar_face=a_face, avatar_face_coords=a_coords)
1869 |                         try:
1870 |                             frames = sharpen_mouth_region(frames, a_coords)
1871 |                         except Exception as e:
1872 |                             logger.warning(f"[ASYNC RENDER] Sharpening failed for job {jid}: {e}", exc_info=True)
1873 |                         frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1874 |                         video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1875 |                     finally:
1876 |                         _render_semaphore.release()
1877 | 
1878 |                     if video_path and os.path.exists(video_path):
1879 |                         with open(video_path, "rb") as vf:
1880 |                             vbytes = vf.read()
1881 |                         os.unlink(video_path)
1882 |                         with _render_jobs_lock:
1883 |                             if jid in _render_jobs:
1884 |                                 _render_jobs[jid] = {"status": "done", "video_bytes": vbytes, "created": time.time()}
1885 |                     else:
1886 |                         with _render_jobs_lock:
1887 |                             if jid in _render_jobs:
1888 |                                 _render_jobs[jid]["status"] = "error"
1889 |                 finally:
1890 |                     for p in [audio_path, wav_path]:
1891 |                         try:
1892 |                             if os.path.exists(p):
1893 |                                 os.unlink(p)
1894 |                         except OSError:
1895 |                             pass
1896 |             except Exception as e:
1897 |                 logger.error(f"[ASYNC RENDER] {e}")
1898 |                 with _render_jobs_lock:
1899 |                     if jid in _render_jobs:
1900 |                         _render_jobs[jid]["status"] = "error"
1901 | 
1902 |         t = threading.Thread(target=render_async, args=(response_text, job_id, avatar_source), daemon=True)
1903 |         t.start()
1904 | 
1905 |         resp_data = {
1906 |             "text": response_text,
1907 |             "session_id": session_id,
1908 |             "job_id": job_id,
1909 |             "video_pending": True,
1910 |         }
1911 |         # Detect action card from user input (zero LLM cost)
1912 |         try:
1913 |             card = oracle_dialogue_engine.detect_action_card(text)
1914 |             if card:
1915 |                 resp_data["action_card"] = card
1916 |                 logger.info(f"[CHAT] Action card triggered: {card['id']}")
1917 |         except Exception as _card_err:
1918 |             logger.warning(f"[CHAT] Action card detection error: {_card_err}")
1919 |         return jsonify(resp_data)
1920 | 
1921 |     # Existing: return video directly
1922 |     return generate_inline(result["text"])
1923 | 
1924 | 
1925 | @app.route("/oracle/session", methods=["GET"])
1926 | def oracle_session_info():
1927 |     return jsonify(oracle_dialogue_engine.get_session_info(request.args.get("session_id","anon")))
1928 | 
1929 | 
1930 | @app.route("/oracle/session/reset", methods=["POST"])
1931 | def oracle_session_reset():
1932 |     data = request.get_json() or {}
1933 |     sid = data.get("session_id", "anon")
1934 | 
1935 |     # ── Phase 3: Save visitor memory before clearing session ───────────
1936 |     session = oracle_dialogue_engine._sessions.get(sid, {})
1937 |     fingerprint = session.get("fingerprint")
1938 |     if fingerprint and session.get("history"):
1939 |         try:
1940 |             from oracle_memory import save_visitor, generate_session_summary
1941 |             api_key = _get_anthropic_key()
1942 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
1943 |             flow = session.get("setup_flow", {})
1944 |             prev_memory = session.get("visitor_memory", {})
1945 |             # Build recent_turns from session history
1946 |             _hist = session.get("history", [])
1947 |             _turns = []
1948 |             for i in range(0, min(6, len(_hist)), 2):
1949 |                 if i+1 < len(_hist):
1950 |                     _turns.append({
1951 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1952 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1953 |                     })
1954 |             save_visitor(fingerprint, {
1955 |                 "personality": session.get("personality", "AMIABLE"),
1956 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
1957 |                 "setup_device": flow.get("device"),
1958 |                 "setup_step": flow.get("step", 0),
1959 |                 "topics_seen": session.get("topics_discussed", []),
1960 |                 "products_shown": session.get("products_mentioned", []),
1961 |                 "recent_turns": list(reversed(_turns)),
1962 |             })
1963 |             logger.info(f"[MEMORY] Saved visitor memory for session {sid}")
1964 |         except Exception as e:
1965 |             logger.warning(f"[MEMORY] Save failed on reset: {e}")
1966 | 
1967 |     oracle_dialogue_engine.reset_session(sid)
1968 |     return jsonify({"status": "reset"})
1969 | 
1970 | 
1971 | @app.route("/oracle/session/save", methods=["POST"])
1972 | def oracle_session_save():
1973 |     """Save session memory on page unload without clearing the session."""
1974 |     data = request.get_json() or {}
1975 |     sid = data.get("session_id", "anon")
1976 |     session = oracle_dialogue_engine._sessions.get(sid, {})
1977 |     fingerprint = session.get("fingerprint")
1978 |     if fingerprint and session.get("history"):
1979 |         try:
1980 |             from oracle_memory import save_visitor, generate_session_summary
1981 |             api_key = _get_anthropic_key()
1982 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
1983 |             flow = session.get("setup_flow", {})
1984 |             prev_memory = session.get("visitor_memory", {})
1985 |             topics = list(session.get("topics_discussed", []))
1986 |             # Build recent_turns from session history
1987 |             _hist = session.get("history", [])
1988 |             _turns = []
1989 |             for i in range(0, min(6, len(_hist)), 2):
1990 |                 if i+1 < len(_hist):
1991 |                     _turns.append({
1992 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1993 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1994 |                     })
1995 |             save_visitor(fingerprint, {
1996 |                 "personality": session.get("personality", "AMIABLE"),
1997 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
1998 |                 "setup_device": flow.get("device"),
1999 |                 "setup_step": flow.get("step", 0),
2000 |                 "topics_seen": topics,
2001 |                 "products_shown": session.get("products_mentioned", []),
2002 |                 "recent_turns": list(reversed(_turns)),
2003 |             })
2004 |             logger.info(f"[MEMORY] Saved session {sid} on unload — {len(topics)} topics, summary len={len(summary)}")
2005 |         except Exception as e:
2006 |             logger.warning(f"[MEMORY] Save on unload failed: {e}")
2007 |     return jsonify({"status": "saved"})
2008 | 
2009 | 
2010 | @app.route("/oracle/intent", methods=["POST"])
2011 | def oracle_intent():
2012 |     """Classify user transcript to an intent."""
2013 |     data = request.get_json()
2014 |     if not data or not data.get("transcript"):
2015 |         return jsonify({"error": "transcript required"}), 400
2016 | 
2017 |     intent, confidence = classify_intent(data["transcript"])
2018 | 
2019 |     # If low confidence, try Claude Haiku for better classification
2020 |     if confidence < 0.6:
2021 |         try:
2022 |             api_key = _get_anthropic_key()
2023 |             if api_key:
2024 |                 resp = http_requests.post(
2025 |                     "https://api.anthropic.com/v1/messages",
2026 |                     headers={
2027 |                         "x-api-key": api_key,
2028 |                         "anthropic-version": "2023-06-01",
2029 |                         "content-type": "application/json",
2030 |                     },
2031 |                     json={
2032 |                         "model": "claude-haiku-4-5-20251001",
2033 |                         "max_tokens": 30,
2034 |                         "messages": [{
2035 |                             "role": "user",
2036 |                             "content": (
2037 |                                 f"Classify this user message into ONE intent from this list: "
2038 |                                 f"{', '.join(INTENT_PATTERNS.keys())}, GREETING, UNKNOWN. "
2039 |                                 f"Reply with ONLY the intent name.\n\nMessage: {data['transcript']}"
2040 |                             ),
2041 |                         }],
2042 |                     },
2043 |                     timeout=10,
2044 |                 )
2045 |                 if resp.status_code == 200:
2046 |                     ai_intent = resp.json()["content"][0]["text"].strip().upper()
2047 |                     valid = set(INTENT_PATTERNS.keys()) | {"GREETING", "UNKNOWN", "SOVEREIGNTY_ASSESSMENT"}
2048 |                     if ai_intent in valid:
2049 |                         intent = ai_intent
2050 |                         confidence = 0.75
2051 |         except Exception as e:
2052 |             logger.warning(f"Intent AI fallback failed: {e}")
2053 | 
2054 |     return jsonify({
2055 |         "intent": intent,
2056 |         "confidence": round(confidence, 2),
2057 |         "cached": oracle_cache_manager.get_cached_response(intent) is not None,
2058 |     })
2059 | 
2060 | 
2061 | # ═══════════════════════════════════════════════════════════════════════
2062 | # SENTENCE CHUNKING FOR LONG TEXT
2063 | # ═══════════════════════════════════════════════════════════════════════
2064 | 
2065 | _chunk_sessions = {}
2066 | _chunk_lock = threading.Lock()
2067 | 
2068 | 
2069 | @app.route("/oracle/chunks/<session_id>")
2070 | def oracle_chunks(session_id):
2071 |     """Poll for additional chunks from a long-text generation."""
2072 |     session = _chunk_sessions.get(session_id)
2073 |     if not session:
2074 |         return jsonify({"error": "Session not found"}), 404
2075 | 
2076 |     return jsonify({
2077 |         "session_id": session_id,
2078 |         "chunks_ready": len(session["paths"]),
2079 |         "total_chunks": session["total"],
2080 |         "complete": session["complete"],
2081 |         "paths": [f"/oracle/chunks/{session_id}/{i}" for i in range(len(session["paths"]))],
2082 |     })
2083 | 
2084 | 
2085 | @app.route("/oracle/chunks/<session_id>/<int:idx>")
2086 | def oracle_chunk_file(session_id, idx):
2087 |     """Serve a specific chunk file."""
2088 |     session = _chunk_sessions.get(session_id)
2089 |     if not session or idx >= len(session["paths"]):
2090 |         return jsonify({"error": "Chunk not ready"}), 404
2091 |     return send_file(session["paths"][idx], mimetype="video/mp4")
2092 | 
2093 | 
2094 | # ═══════════════════════════════════════════════════════════════════════
2095 | # TTS PROVIDER STATUS
2096 | # ═══════════════════════════════════════════════════════════════════════
2097 | 
2098 | @app.route("/avatar/tts-provider", methods=["GET"])
2099 | def avatar_tts_provider():
2100 |     """Report which TTS provider is active."""
2101 |     if _AVATAR_KOKORO_READY:
2102 |         return jsonify({
2103 |             "provider": "kokoro",
2104 |             "voice": "af_heart",
2105 |             "backend": "cuda:1",
2106 |             "sample_rate": 24000,
2107 |             "ready": True,
2108 |         })
2109 |     return jsonify({
2110 |         "provider": "elevenlabs_fallback",
2111 |         "reason": "Kokoro not loaded or init failed",
2112 |         "ready": False,
2113 |     })
2114 | 
2115 | 
2116 | # ═══════════════════════════════════════════════════════════════════════
2117 | # MAIN
2118 | # ═══════════════════════════════════════════════════════════════════════
2119 | 
2120 | if __name__ == "__main__":
2121 |     print(f"\n{'='*60}")
2122 |     print("  ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks")
2123 |     print(f"  Port: {PORT}")
2124 |     print(f"  Device: {DEVICE}")
2125 |     print(f"  Avatar: {AVATAR_SOURCE}")
2126 |     print(f"  FPS: {DEFAULT_FPS}")
2127 |     print(f"  Encoding: CRF 23, preset ultrafast, 512px output")
2128 |     print(f"  Features: FP16, cv2_sharpen, mediapipe_blinks, head_movement")
2129 |     print(f"  Vision: {'enabled' if os.environ.get('GEMINI_API_KEY') else 'disabled'}")
2130 |     print(f"  Max audio: {MAX_AUDIO_SECONDS}s | Lock timeout: {LOCK_TIMEOUT}s")
2131 |     print(f"{'='*60}\n")
2132 | 
2133 |     # Load all models via registry (FP16 on GPU 1)
2134 |     logger.info("Initializing ModelRegistry...")
2135 |     reg = ModelRegistry.get()
2136 | 
2137 |     if reg.wav2lip_model is None:
2138 |         logger.error("Failed to load Wav2Lip model. Exiting.")
2139 |         sys.exit(1)
2140 | 
2141 |     if reg.avatar_face_coords is None:
2142 |         logger.error("No face detected in avatar. Exiting.")
2143 |         sys.exit(1)
2144 | 
2145 |     logger.info("Face enhancer: CV2 sharpen-only (no GFPGAN)")
2146 | 
2147 |     # Load Kokoro af_heart TTS on cuda:1 (~2-3s per utterance)
2148 |     logger.info("[STARTUP] Initializing Kokoro af_heart TTS on cuda:1...")
2149 |     _init_avatar_kokoro()
2150 | 
2151 |     # Auto-warmup (non-blocking — runs in background thread so Flask can start immediately)
2152 |     def _warmup_background():
2153 |         logger.info("[WARMUP] Running pipeline warmup in background...")
2154 |         warmup_start = time.time()
2155 |         try:
2156 |             import wave
2157 |             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
2158 |                 with wave.open(tmp.name, "w") as wf:
2159 |                     wf.setnchannels(1)
2160 |                     wf.setsampwidth(2)
2161 |                     wf.setframerate(16000)
2162 |                     wf.writeframes(b"\x00\x00" * 8000)
2163 |                 warmup_wav = tmp.name
2164 |             frames = wav2lip_generate(warmup_wav, DEFAULT_FPS)
2165 |             if frames:
2166 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
2167 |             os.unlink(warmup_wav)
2168 |             logger.info(
2169 |                 f"[WARMUP] Pipeline ready in {time.time()-warmup_start:.1f}s "
2170 |                 f"({len(frames)} frames)"
2171 |             )
2172 |         except Exception as e:
2173 |             logger.warning(f"[WARMUP] Failed (non-fatal): {e}")
2174 |     threading.Thread(target=_warmup_background, daemon=True).start()
2175 | 
2176 |     dev_idx = int(DEVICE.split(':')[1]) if ':' in DEVICE else 0
2177 |     logger.info(
2178 |         f"[WARMUP] GPU {dev_idx} VRAM: {torch.cuda.memory_allocated(dev_idx)/1024**3:.1f}GB used"
2179 |     )
2180 | 
2181 |     # Generate idle loop if not already present
2182 |     generate_idle_loop()
2183 | 
2184 |     # Phase 2: Start cache warming in background (delayed 60s to allow incoming requests)
2185 |     logger.info("[STARTUP] Oracle cache warmer will start in 60s...")
2186 |     def _delayed_warmup():
2187 |         time.sleep(60)
2188 |         logger.info("[STARTUP] Cache warmup starting now (60s delay complete)")
2189 |         oracle_cache_manager.warm_cache()
2190 |     threading.Thread(target=_delayed_warmup, daemon=True).start()
2191 |     oracle_cache_manager.start_background_warmer()
2192 | 
2193 |     # Phase 3: Start intelligence feed
2194 |     logger.info("[STARTUP] Starting intelligence feed...")
2195 |     oracle_intelligence_feed.start_intelligence_feed()
2196 | 
2197 |     logger.info(f"Avatar server v2 ready on port {PORT}")
2198 |     app.run(host="0.0.0.0", port=PORT, threaded=True)
2199 | 
```

### File: oracle/oracle_cache_manager.py (233 lines)
```
   1 | """
   2 | Oracle Cache Manager — Pre-computed response cache with background warming.
   3 | Caches TTS+Wav2Lip video for known response intents.
   4 | """
   5 | 
   6 | import os
   7 | import json
   8 | import time
   9 | import logging
  10 | import threading
  11 | import subprocess
  12 | 
  13 | logger = logging.getLogger("oracle_cache_manager")
  14 | 
  15 | ORACLE_DIR = os.path.dirname(os.path.abspath(__file__))
  16 | CACHE_DIR = os.path.join(ORACLE_DIR, "cache")
  17 | RESPONSES_DIR = os.path.join(CACHE_DIR, "responses")
  18 | INDEX_PATH = os.path.join(CACHE_DIR, "index.json")
  19 | RENDER_HELPER = os.path.join(ORACLE_DIR, "cache_render_helper.py")
  20 | 
  21 | CACHE_TTL = 7200  # 2 hours
  22 | WARM_INTERVAL = 7200  # re-check every 2 hours
  23 | 
  24 | RESPONSE_TREE = {
  25 |     "GREETING": [
  26 |         "Hey. I'm the Oracle — tracking everything happening in Bitcoin right now. On-chain, macro, geopolitical, all of it. What brings you here today — you want the daily brief, or something more specific?",
  27 |         "Oracle here. Live inside Protocol Pulse, eyes on everything moving in Bitcoin. On-chain signals, macro pressure, geopolitical noise — I'm watching all of it. What do you need?",
  28 |         "You're connected to Oracle. I track Bitcoin intelligence in real time — on-chain data, macro flows, network signals. What are you here for — the daily brief, or a specific question?",
  29 |     ],
  30 |     "SOVEREIGNTY_INTRO": "Your sovereignty score is basically a snapshot of how free you actually are — how much of your financial life you've removed from legacy systems and moved into things you actually control. Want me to run through where you stand and what you can do about it right now?",
  31 |     "SOVEREIGNTY_ASSESSMENT": "Okay let's map it out. There are four pillars: self-custody of your Bitcoin, your own node running, private communications, and no KYC exposure on your income. Most people are zero for four when they start. Where are you today?",
  32 |     "SOVEREIGNTY_COLD_WALLET": "If your Bitcoin is on an exchange, it's not yours — it's an IOU. The fix is a hardware wallet. I can walk you through setting one up right now, step by step. Which do you have — a Coldcard, a Ledger, or nothing yet?",
  33 |     "SOVEREIGNTY_NODE": "Running your own node means you verify your own transactions — you don't trust, you verify. The easiest entry point right now is a Raspberry Pi with Umbrel. Want me to walk you through the setup? Takes about 45 minutes.",
  34 |     "SOVEREIGNTY_BITAXE": "Bitaxe is a solo miner you can run at home — it's a lottery ticket, but a Bitcoin lottery ticket. You're contributing to network security and you have a real shot at a full block reward. Curated Mining also offers white-glove setup if you want the hands-off version.",
  35 |     "SOVEREIGNTY_LIFE_INSURANCE": "One thing most Bitcoiners miss — if you die with Bitcoin in cold storage and nobody knows the seed phrase, that wealth disappears. Meanwhile offers life insurance that actually understands Bitcoin — they'll pay out in BTC and can handle estate planning around self-custody.",
  36 |     "SOVEREIGNTY_RESIDENCY": "Digital residency through Palau — via RNS.ID — gives you a second identity layer and a legal domicile outside your home country. That has real tax and privacy implications depending on your situation. Happy to explain the mechanics.",
  37 |     "DAILY_BRIEF_INTRO": "Alright, here's what's moving right now in Bitcoin. Give me a second and I'll pull the latest from our intelligence layer.",
  38 |     "UNKNOWN_QUESTION": [
  39 |         "That's outside my real-time data right now, but I'm going to research it and come back with something solid. Give me a few seconds.",
  40 |         "I don't have that signal live right now. Let me pull it — give me a moment.",
  41 |         "That one's not in my current feed. Stand by — I'll get it.",
  42 |     ],
  43 |     "GOODBYE": "Alright. Stack sats, verify everything, and come back anytime. I'll be here.",
  44 | }
  45 | 
  46 | # Track which keys are currently being rendered to avoid duplicate work
  47 | _rendering_keys = set()
  48 | _WARMER_SEMAPHORE = threading.Semaphore(1)  # max 1 cache render at a time, preserves 1 slot for interactive
  49 | _rendering_lock = threading.Lock()
  50 | 
  51 | 
  52 | def _load_index():
  53 |     if os.path.exists(INDEX_PATH):
  54 |         try:
  55 |             with open(INDEX_PATH) as f:
  56 |                 return json.load(f)
  57 |         except (json.JSONDecodeError, IOError):
  58 |             pass
  59 |     return {}
  60 | 
  61 | 
  62 | def _save_index(index):
  63 |     os.makedirs(CACHE_DIR, exist_ok=True)
  64 |     with open(INDEX_PATH, "w") as f:
  65 |         json.dump(index, f, indent=2)
  66 | 
  67 | 
  68 | def _is_fresh(index, key):
  69 |     """Check if cached response exists and is less than CACHE_TTL old."""
  70 |     entry = index.get(key)
  71 |     if not entry:
  72 |         return False
  73 |     path = entry.get("path", "")
  74 |     if not os.path.exists(path) or os.path.getsize(path) == 0:
  75 |         return False
  76 |     generated_at = entry.get("generated_at_ts", 0)
  77 |     return (time.time() - generated_at) < CACHE_TTL
  78 | 
  79 | 
  80 | def _render_key(key, text):
  81 |     """Render a single response key via cache_render_helper.py subprocess."""
  82 |     if isinstance(text, list):
  83 |         import random
  84 |         text = random.choice(text)
  85 |     out_path = os.path.join(RESPONSES_DIR, f"{key}.mp4")
  86 | 
  87 |     # Acquire warmer slot - keeps 1 GPU slot free for interactive requests
  88 |     if not _WARMER_SEMAPHORE.acquire(timeout=15):
  89 |         logger.info(f"[CACHE] {key} deferred - interactive request has GPU priority")
  90 |         return
  91 |     with _rendering_lock:
  92 |         if key in _rendering_keys:
  93 |             logger.info(f"[CACHE] {key} already rendering, skip")
  94 |             return False
  95 |         _rendering_keys.add(key)
  96 | 
  97 |     try:
  98 |         logger.info(f"[CACHE] Rendering {key} ({len(text)} chars)...")
  99 |         t0 = time.time()
 100 |         result = subprocess.run(
 101 |             [
 102 |                 "python3", RENDER_HELPER,
 103 |                 "--text", text,
 104 |                 "--out", out_path,
 105 |             ],
 106 |             capture_output=True, text=True, timeout=300,
 107 |             cwd=ORACLE_DIR,
 108 |         )
 109 |         elapsed = time.time() - t0
 110 | 
 111 |         if result.returncode != 0:
 112 |             logger.error(f"[CACHE] {key} render failed ({elapsed:.1f}s): {result.stderr[-300:]}")
 113 |             return False
 114 | 
 115 |         if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
 116 |             logger.error(f"[CACHE] {key} output missing or empty")
 117 |             return False
 118 | 
 119 |         # Get duration from ffprobe
 120 |         duration_s = 0.0
 121 |         try:
 122 |             probe = subprocess.run(
 123 |                 ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 124 |                  "-of", "default=noprint_wrappers=1:nokey=1", out_path],
 125 |                 capture_output=True, text=True, timeout=10,
 126 |             )
 127 |             duration_s = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
 128 |         except Exception:
 129 |             pass
 130 | 
 131 |         # Update index
 132 |         index = _load_index()
 133 |         index[key] = {
 134 |             "path": out_path,
 135 |             "generated_at_ts": time.time(),
 136 |             "duration_s": round(duration_s, 2),
 137 |         }
 138 |         _save_index(index)
 139 | 
 140 |         logger.info(f"[CACHE] {key} cached — {duration_s:.1f}s video in {elapsed:.1f}s render")
 141 |         return True
 142 | 
 143 |     except subprocess.TimeoutExpired:
 144 |         logger.error(f"[CACHE] {key} render timed out")
 145 |         return False
 146 |     except Exception as e:
 147 |         logger.error(f"[CACHE] {key} render error: {e}")
 148 |         return False
 149 |     finally:
 150 |         with _rendering_lock:
 151 |             _rendering_keys.discard(key)
 152 |     _WARMER_SEMAPHORE.release()
 153 | 
 154 | 
 155 | def warm_cache():
 156 |     """Warm all response cache entries. Called on startup and periodically."""
 157 |     os.makedirs(RESPONSES_DIR, exist_ok=True)
 158 |     index = _load_index()
 159 | 
 160 |     stale_keys = [k for k in RESPONSE_TREE if not _is_fresh(index, k)]
 161 |     if not stale_keys:
 162 |         logger.info(f"[CACHE] All {len(RESPONSE_TREE)} responses fresh")
 163 |         return
 164 | 
 165 |     logger.info(f"[CACHE] Warming {len(stale_keys)}/{len(RESPONSE_TREE)} stale keys: {stale_keys}")
 166 | 
 167 |     for key in stale_keys:
 168 |         text = RESPONSE_TREE[key]
 169 |         if isinstance(text, list):
 170 |             import random
 171 |             text = random.choice(text)
 172 |         _render_key(key, text)
 173 |         # Small delay between renders to avoid GPU contention
 174 |         time.sleep(5)  # longer gap gives interactive requests GPU access
 175 | 
 176 |     logger.info("[CACHE] Warm cycle complete")
 177 | 
 178 | 
 179 | def get_cached_response(key):
 180 |     """Get cached video path for a response key, or None."""
 181 |     index = _load_index()
 182 |     entry = index.get(key)
 183 |     if not entry:
 184 |         return None
 185 |     path = entry.get("path", "")
 186 |     if os.path.exists(path) and os.path.getsize(path) > 0:
 187 |         return path
 188 |     return None
 189 | 
 190 | 
 191 | def is_rendering(key):
 192 |     """Check if a key is currently being rendered."""
 193 |     with _rendering_lock:
 194 |         return key in _rendering_keys
 195 | 
 196 | 
 197 | def get_cache_status():
 198 |     """Return status of all cached responses."""
 199 |     index = _load_index()
 200 |     status = {}
 201 |     for key in RESPONSE_TREE:
 202 |         entry = index.get(key)
 203 |         if entry and os.path.exists(entry.get("path", "")):
 204 |             status[key] = {
 205 |                 "cached": True,
 206 |                 "fresh": _is_fresh(index, key),
 207 |                 "generated_at_ts": entry.get("generated_at_ts", 0),
 208 |                 "duration_s": entry.get("duration_s", 0),
 209 |                 "rendering": is_rendering(key),
 210 |             }
 211 |         else:
 212 |             status[key] = {
 213 |                 "cached": False,
 214 |                 "fresh": False,
 215 |                 "rendering": is_rendering(key),
 216 |             }
 217 |     return status
 218 | 
 219 | 
 220 | def start_background_warmer():
 221 |     """Start a background thread that re-warms cache every WARM_INTERVAL seconds."""
 222 |     def _loop():
 223 |         while True:
 224 |             time.sleep(WARM_INTERVAL)
 225 |             try:
 226 |                 warm_cache()
 227 |             except Exception as e:
 228 |                 logger.error(f"[CACHE] Background warm error: {e}")
 229 | 
 230 |     t = threading.Thread(target=_loop, daemon=True)
 231 |     t.start()
 232 |     logger.info(f"[CACHE] Background warmer started (interval={WARM_INTERVAL}s)")
 233 | 
```

### File: templates/oracle_live.html (2020 lines)
```
   1 | <!DOCTYPE html>
   2 | <html lang="en">
   3 | <head>
   4 | <meta charset="UTF-8">
   5 | <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover,interactive-widget=resizes-content">
   6 | <meta name="theme-color" content="#000">
   7 | <meta name="apple-mobile-web-app-capable" content="yes">
   8 | <meta name="apple-mobile-web-app-status-bar-style" content="black">
   9 | <meta http-equiv="Permissions-Policy" content="microphone=*, camera=*">
  10 | <title>Oracle · Protocol Pulse</title>
  11 | <link rel="preconnect" href="https://fonts.googleapis.com">
  12 | <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  13 | <style>
  14 | *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
  15 | html,body{height:100%;width:100%;background:#000;overflow:hidden;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}
  16 | 
  17 | /* ─── KEYFRAMES ─────────────────────────────────────────── */
  18 | @keyframes orbit{to{transform:rotate(360deg)}}
  19 | @keyframes orbit-rev{to{transform:rotate(-360deg)}}
  20 | @keyframes breathe{0%,100%{opacity:.6;transform:scale(1)}50%{opacity:1;transform:scale(1.04)}}
  21 | @keyframes scan{0%{top:-4px}100%{top:100%}}
  22 | @keyframes live-blink{0%,100%{opacity:1}49%{opacity:1}50%,99%{opacity:.15}}
  23 | @keyframes fade-up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
  24 | @keyframes mic-pulse{0%{box-shadow:0 0 0 0 rgba(255,59,95,.6)}70%{box-shadow:0 0 0 22px rgba(255,59,95,0)}100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}}
  25 | @keyframes mic-idle-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}50%{box-shadow:0 0 0 14px rgba(255,59,95,.22),0 0 18px 4px rgba(255,59,95,.12)}}
  26 | @keyframes spin{to{transform:rotate(360deg)}}
  27 | @keyframes card-up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  28 | @keyframes hex-glow{0%,100%{filter:drop-shadow(0 0 8px rgba(255,59,95,.4))}50%{filter:drop-shadow(0 0 22px rgba(255,59,95,.9))}}
  29 | 
  30 | /* ─── ROOT ──────────────────────────────────────────────── */
  31 | #root{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden}
  32 | 
  33 | /* ─── BACKGROUND GRID ───────────────────────────────────── */
  34 | #root::before{
  35 |   content:'';position:absolute;inset:0;
  36 |   background-image:linear-gradient(rgba(255,59,95,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,59,95,.04) 1px,transparent 1px);
  37 |   background-size:40px 40px;
  38 |   mask-image:radial-gradient(ellipse 80% 80% at 50% 50%,black 40%,transparent 100%);
  39 |   pointer-events:none;
  40 | }
  41 | 
  42 | /* ═══════════════════════════════════════════════════════════
  43 |    GATE SCREEN
  44 | ═══════════════════════════════════════════════════════════ */
  45 | #gate{
  46 |   display:flex;flex-direction:column;align-items:center;
  47 |   gap:clamp(18px,4vw,28px);
  48 |   padding:clamp(24px,5vw,48px) clamp(24px,5vw,48px);
  49 |   width:100%;max-width:520px;
  50 |   transition:opacity .35s ease;
  51 | }
  52 | 
  53 | /* Oracle sigil */
  54 | .sigil-wrap{
  55 |   position:relative;
  56 |   width:clamp(140px,38vw,200px);
  57 |   height:clamp(140px,38vw,200px);
  58 |   flex-shrink:0;
  59 | }
  60 | /* Rotating rings */
  61 | .ring{
  62 |   position:absolute;inset:0;
  63 |   border-radius:50%;
  64 |   border:1px solid rgba(255,59,95,.25);
  65 | }
  66 | .ring-1{animation:orbit 12s linear infinite}
  67 | .ring-1::before{
  68 |   content:'';position:absolute;
  69 |   width:6px;height:6px;background:#ff3b5f;border-radius:50%;
  70 |   top:-3px;left:50%;transform:translateX(-50%);
  71 |   box-shadow:0 0 8px #ff3b5f;
  72 | }
  73 | .ring-2{
  74 |   inset:12%;border-color:rgba(255,180,50,.2);
  75 |   animation:orbit-rev 8s linear infinite;
  76 | }
  77 | .ring-2::before{
  78 |   content:'';position:absolute;
  79 |   width:4px;height:4px;background:#f8c15c;border-radius:50%;
  80 |   bottom:-2px;left:50%;transform:translateX(-50%);
  81 |   box-shadow:0 0 6px #f8c15c;
  82 | }
  83 | /* Avatar in center */
  84 | .sigil-avatar{
  85 |   position:absolute;
  86 |   inset:18%;
  87 |   border-radius:50%;
  88 |   overflow:hidden;
  89 |   background:radial-gradient(circle,#1a0608 0%,#050203 100%);
  90 |   border:1px solid rgba(255,59,95,.3);
  91 |   animation:breathe 3.5s ease-in-out infinite;
  92 | }
  93 | .sigil-avatar img{width:100%;height:100%;object-fit:cover;display:block;border-radius:50%}
  94 | .sigil-fallback{
  95 |   width:100%;height:100%;border-radius:50%;
  96 |   display:flex;align-items:center;justify-content:center;
  97 |   font-size:clamp(28px,8vw,44px);
  98 |   background:radial-gradient(circle,#2a0810 0%,#080205 100%);
  99 | }
 100 | /* Scan line */
 101 | .sigil-scan{
 102 |   position:absolute;inset:18%;border-radius:50%;overflow:hidden;pointer-events:none;
 103 | }
 104 | .sigil-scan::after{
 105 |   content:'';position:absolute;left:0;right:0;height:2px;
 106 |   background:linear-gradient(90deg,transparent,rgba(255,59,95,.6),transparent);
 107 |   animation:scan 2.5s ease-in-out infinite;
 108 | }
 109 | 
 110 | /* Wordmark */
 111 | .gate-brand{
 112 |   font-size:10px;font-weight:700;
 113 |   letter-spacing:.4em;color:rgba(255,59,95,.7);
 114 |   text-transform:uppercase;
 115 | }
 116 | 
 117 | /* Title */
 118 | .gate-title{
 119 |   font-size:clamp(32px,9vw,52px);
 120 |   font-weight:900;color:#fff;
 121 |   letter-spacing:-.03em;line-height:1;
 122 |   text-align:center;
 123 | }
 124 | .gate-title span{color:#ff3b5f}
 125 | 
 126 | /* Sub */
 127 | .gate-sub{
 128 |   font-size:clamp(13px,3.5vw,15px);
 129 |   color:#556;
 130 |   text-align:center;line-height:1.6;
 131 |   max-width:300px;
 132 |   font-weight:400;
 133 | }
 134 | 
 135 | /* ─── THE BUTTON ─────────────────────────────────────────── */
 136 | #gate-btn{
 137 |   position:relative;
 138 |   background:transparent;
 139 |   border:none;cursor:pointer;
 140 |   padding:0;
 141 |   width:clamp(200px,55vw,280px);
 142 |   -webkit-appearance:none;
 143 |   touch-action:manipulation;
 144 | }
 145 | #gate-btn:disabled{opacity:.4;cursor:not-allowed}
 146 | #gate-btn:active .btn-inner{transform:scale(.97)}
 147 | 
 148 | .btn-inner{
 149 |   position:relative;overflow:hidden;
 150 |   background:linear-gradient(135deg,#1a0508 0%,#0d0203 100%);
 151 |   border:1px solid rgba(255,59,95,.5);
 152 |   border-radius:4px;
 153 |   padding:clamp(14px,4vw,18px) clamp(20px,5vw,32px);
 154 |   transition:transform .1s,border-color .2s;
 155 |   display:flex;flex-direction:column;align-items:center;gap:6px;
 156 | }
 157 | #gate-btn:not(:disabled):hover .btn-inner{border-color:rgba(255,59,95,.9)}
 158 | 
 159 | /* Top label */
 160 | .btn-label{
 161 |   font-family:'JetBrains Mono',monospace;
 162 |   font-size:9px;letter-spacing:.35em;
 163 |   color:rgba(255,59,95,.6);text-transform:uppercase;
 164 | }
 165 | /* Main text */
 166 | .btn-text{
 167 |   font-size:clamp(13px,4vw,16px);font-weight:700;
 168 |   color:#fff;letter-spacing:.05em;text-transform:uppercase;
 169 |   display:flex;align-items:center;gap:10px;
 170 | }
 171 | .btn-mic-icon{
 172 |   width:16px;height:16px;flex-shrink:0;
 173 |   opacity:.9;
 174 | }
 175 | /* Corner accents */
 176 | .btn-inner::before,.btn-inner::after{
 177 |   content:'';position:absolute;width:8px;height:8px;
 178 |   border-color:rgba(255,59,95,.6);border-style:solid;
 179 | }
 180 | .btn-inner::before{top:4px;left:4px;border-width:1px 0 0 1px}
 181 | .btn-inner::after{bottom:4px;right:4px;border-width:0 1px 1px 0}
 182 | /* Glow sweep on hover */
 183 | .btn-sweep{
 184 |   position:absolute;inset:0;
 185 |   background:linear-gradient(105deg,transparent 40%,rgba(255,59,95,.06) 50%,transparent 60%);
 186 |   transform:translateX(-100%);
 187 |   transition:transform .5s ease;
 188 | }
 189 | #gate-btn:not(:disabled):hover .btn-sweep{transform:translateX(100%)}
 190 | 
 191 | /* Status line below btn */
 192 | #gate-status{
 193 |   font-family:'JetBrains Mono',monospace;
 194 |   font-size:11px;color:#334;letter-spacing:.08em;
 195 |   min-height:16px;text-align:center;
 196 | }
 197 | #gate-error{
 198 |   display:none;font-size:12px;color:#ff3b5f;
 199 |   text-align:center;line-height:1.5;max-width:280px;
 200 |   background:rgba(255,59,95,.06);border:1px solid rgba(255,59,95,.15);
 201 |   border-radius:4px;padding:8px 12px;
 202 | }
 203 | 
 204 | /* ═══════════════════════════════════════════════════════════
 205 |    LIVE STAGE
 206 | ═══════════════════════════════════════════════════════════ */
 207 | #stage{
 208 |   display:none;flex-direction:column;align-items:center;
 209 |   position:relative;
 210 |   width:100%;height:100%;
 211 |   padding:clamp(8px,2.5vw,14px) clamp(12px,3.5vw,20px) clamp(10px,3vw,16px);
 212 |   gap:clamp(6px,1.5vw,10px);
 213 |   overflow-y:auto;-webkit-overflow-scrolling:touch;
 214 |   animation:fade-up .4s ease;
 215 | }
 216 | 
 217 | /* Top bar */
 218 | .topbar{
 219 |   width:100%;display:flex;align-items:center;
 220 |   justify-content:space-between;flex-shrink:0;
 221 | }
 222 | /* Exit and minimize buttons */
 223 | .stage-controls{display:flex;align-items:center;gap:8px}
 224 | #minimize-btn,#exit-btn{
 225 |   width:28px;height:28px;border-radius:50%;
 226 |   background:transparent;border:1px solid #1e2235;
 227 |   cursor:pointer;display:flex;align-items:center;justify-content:center;
 228 |   transition:border-color .15s,background .15s;
 229 |   -webkit-appearance:none;touch-action:manipulation;flex-shrink:0;
 230 |   opacity:0.5;
 231 | }
 232 | #minimize-btn:hover,#exit-btn:hover{opacity:1;border-color:#556;background:#0f1117}
 233 | #exit-btn:hover{border-color:rgba(255,59,95,.5)}
 234 | 
 235 | /* ── FLOATING MINI MODE ─────────────────────────────────────────── */
 236 | @keyframes mini-in{from{opacity:0;transform:scale(.6) translateY(20px)}to{opacity:1;transform:scale(1) translateY(0)}}
 237 | @keyframes mini-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,.4)}70%{box-shadow:0 0 0 8px rgba(255,59,95,0)}}
 238 | 
 239 | #oracle-float{
 240 |   position:fixed;bottom:24px;right:24px;
 241 |   width:72px;height:72px;border-radius:50%;
 242 |   background:#0a0b0f;border:2px solid rgba(255,59,95,.6);
 243 |   cursor:pointer;z-index:9999;
 244 |   display:none;align-items:center;justify-content:center;
 245 |   animation:mini-in .3s ease, mini-pulse 2s ease-in-out infinite;
 246 |   box-shadow:0 4px 20px rgba(0,0,0,.6);
 247 |   overflow:hidden;transition:transform .15s;
 248 | }
 249 | #oracle-float:hover{transform:scale(1.08)}
 250 | #oracle-float:active{transform:scale(.95)}
 251 | #oracle-float img{width:100%;height:100%;object-fit:cover;border-radius:50%}
 252 | #oracle-float-fallback{font-size:28px}
 253 | /* Speaking ring on float */
 254 | #oracle-float.speaking{border-color:#6cff9f;animation:mini-pulse 0.8s ease-in-out infinite}
 255 | /* Tooltip */
 256 | #oracle-float::after{
 257 |   content:"Talk to Oracle";
 258 |   position:absolute;right:80px;
 259 |   background:#0f1117;border:1px solid #1e2235;border-radius:4px;
 260 |   padding:4px 8px;font-family:'JetBrains Mono',monospace;font-size:10px;
 261 |   color:#b8c2d9;white-space:nowrap;pointer-events:none;
 262 |   opacity:0;transition:opacity .2s;
 263 | }
 264 | #oracle-float:hover::after{opacity:1}
 265 | .topbar-brand{
 266 |   font-family:'JetBrains Mono',monospace;
 267 |   font-size:10px;font-weight:500;
 268 |   letter-spacing:.3em;color:rgba(255,59,95,.7);text-transform:uppercase;
 269 | }
 270 | .live-pill{
 271 |   display:flex;align-items:center;gap:5px;
 272 |   background:rgba(74,222,128,.06);
 273 |   border:1px solid rgba(74,222,128,.2);
 274 |   border-radius:20px;padding:3px 8px;
 275 | }
 276 | .live-dot{
 277 |   width:5px;height:5px;border-radius:50%;background:#4ade80;
 278 |   animation:live-blink 2s step-end infinite;
 279 | }
 280 | .live-text{
 281 |   font-family:'JetBrains Mono',monospace;
 282 |   font-size:9px;font-weight:500;color:#4ade80;letter-spacing:.15em;
 283 | }
 284 | 
 285 | /* Video */
 286 | .video-wrap{
 287 |   position:relative;
 288 |   width:100%;
 289 |   max-width:min(440px,calc(100vw - 24px));
 290 |   aspect-ratio:1/1;
 291 |   border-radius:8px;overflow:hidden;
 292 |   background: #050508 url('/static/oracle_avatar.png') center/cover no-repeat;
 293 |   overflow: hidden;
 294 |   flex-shrink:0;
 295 |   min-height: min(440px, calc(100vw - 24px));
 296 | }
 297 | /* Corner brackets */
 298 | .video-wrap::before,.video-wrap::after{
 299 |   content:'';position:absolute;width:16px;height:16px;
 300 |   border-color:rgba(255,59,95,.4);border-style:solid;z-index:2;
 301 | }
 302 | .video-wrap::before{top:6px;left:6px;border-width:1px 0 0 1px}
 303 | .video-wrap::after{bottom:6px;right:6px;border-width:0 1px 1px 0}
 304 | 
 305 | #vid{width:100%;height:100%;object-fit:cover;object-position:center top;display:block}
 306 | /* Subtitle */
 307 | #subtitle{
 308 |   width:100%;
 309 |   font-family:'JetBrains Mono',monospace;
 310 |   font-size:clamp(11px,3vw,13px);color:#f8c15c;
 311 |   line-height:1.55;text-align:center;
 312 |   min-height:34px;
 313 |   opacity:0;transition:opacity .3s;
 314 |   display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
 315 |   overflow:hidden;padding:0 4px;
 316 | }
 317 | #subtitle.on{opacity:1}
 318 | 
 319 | /* Status */
 320 | #stat{
 321 |   font-family:'JetBrains Mono',monospace;
 322 |   font-size:clamp(10px,2.8vw,12px);
 323 |   color:#334;display:flex;align-items:center;gap:6px;
 324 |   height:18px;transition:color .2s;flex-shrink:0;
 325 | }
 326 | .spin{width:12px;height:12px;border:1.5px solid currentColor;border-top-color:transparent;border-radius:50%;display:none;animation:spin .6s linear infinite;flex-shrink:0}
 327 | 
 328 | /* Transcript */
 329 | #tx{
 330 |   font-family:'JetBrains Mono',monospace;
 331 |   font-size:clamp(10px,2.8vw,11px);color:#445;font-style:italic;
 332 |   min-height:16px;text-align:center;
 333 |   opacity:0;transition:opacity .2s;
 334 |   width:100%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;
 335 | }
 336 | #tx.on{opacity:1}
 337 | 
 338 | /* Mic */
 339 | .mic-area{display:flex;flex-direction:column;align-items:center;gap:7px;flex-shrink:0}
 340 | #mic{
 341 |   width:clamp(60px,15vw,72px);height:clamp(60px,15vw,72px);
 342 |   border-radius:50%;
 343 |   background:#0a0c12;
 344 |   border:1.5px solid #ff3b5f;
 345 |   cursor:pointer;
 346 |   display:flex;align-items:center;justify-content:center;
 347 |   transition:background .15s,transform .1s;
 348 |   -webkit-appearance:none;touch-action:manipulation;
 349 |   flex-shrink:0;
 350 | }
 351 | #mic:active:not(:disabled){transform:scale(.92)}
 352 | #mic:disabled{opacity:.2;cursor:not-allowed}
 353 | #mic.rec{background:#ff3b5f;animation:mic-pulse 1s ease-out infinite}
 354 | #mic.idle-pulse{border-color:#ff3b5f;border-width:2px;animation:mic-idle-pulse 1.8s ease-in-out 3}
 355 | .mic-hint{font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.12em;text-transform:uppercase}
 356 | #cam-btn{
 357 |   width:42px;height:42px;border-radius:50%;background:#0a0c12;
 358 |   border:1.5px solid #334;cursor:pointer;
 359 |   display:flex;align-items:center;justify-content:center;
 360 |   transition:border-color .15s;-webkit-appearance:none;touch-action:manipulation;
 361 |   flex-shrink:0;
 362 | }
 363 | #cam-btn:hover{border-color:#f8c15c}
 364 | #cam-btn.active{border-color:#f8c15c;background:#1a1500}
 365 | #cam-input{display:none}
 366 | #vision-status{
 367 |   font-family:'JetBrains Mono',monospace;font-size:10px;color:#f8c15c;
 368 |   text-align:center;opacity:0;transition:opacity .3s;min-height:14px;
 369 | }
 370 | #vision-status.on{opacity:1}
 371 | 
 372 | /* Sovereignty cards */
 373 | #cards{display:none;grid-template-columns:1fr 1fr;gap:8px;width:100%;animation:card-up .35s ease;position:relative;z-index:0}
 374 | #cards.on{display:grid}
 375 | .card{
 376 |   background:#080a0f;
 377 |   border:1px solid #141824;
 378 |   border-radius:6px;
 379 |   padding:clamp(10px,2.5vw,13px);
 380 |   cursor:pointer;
 381 |   transition:border-color .15s,background .15s;
 382 |   display:flex;flex-direction:column;gap:5px;
 383 |   touch-action:manipulation;
 384 | }
 385 | .card:active{background:#100610;border-color:rgba(255,59,95,.5)}
 386 | .card-title{font-size:clamp(11px,3.2vw,13px);font-weight:600;color:#ccd;line-height:1.3}
 387 | .card-link{font-family:'JetBrains Mono',monospace;font-size:clamp(9px,2.5vw,10px);color:rgba(255,59,95,.7);text-decoration:none;letter-spacing:.03em}
 388 | 
 389 | /* ═══════════════════════════════════════════════════════════
 390 |    MOBILE — max-width 640px
 391 | ═══════════════════════════════════════════════════════════ */
 392 | /* ═══════════════════════════════════════════════════════════
 393 |    TABLET — max-width 768px
 394 | ═══════════════════════════════════════════════════════════ */
 395 | @media(max-width:768px){
 396 |   body{padding-top:48px}
 397 |   .video-wrap{
 398 |     max-width:100%;
 399 |     margin:0 auto;
 400 |   }
 401 |   #vid{
 402 |     width:100%;
 403 |     max-width:100%;
 404 |     display:block;
 405 |     margin:0 auto;
 406 |   }
 407 |   #cards{grid-template-columns:1fr 1fr}
 408 |   .card{min-height:48px}
 409 |   #mic{min-width:48px;min-height:48px}
 410 |   #cam-btn{min-width:48px;min-height:48px}
 411 |   #gate-btn{min-height:48px}
 412 |   #root{padding-bottom:80px}
 413 | }
 414 | 
 415 | @media(max-width:640px){
 416 |   body{position:fixed;width:100%;overflow:hidden}
 417 |   #root{position:relative;height:100dvh}
 418 |   /* Stage: full viewport, vertical stack, no overflow leak */
 419 |   #stage{
 420 |     height:100vh;height:100dvh;
 421 |     padding:8px 10px 0;
 422 |     gap:6px;
 423 |     overflow:hidden;
 424 |     display:none;flex-direction:column;
 425 |   }
 426 | 
 427 |   /* Topbar: compact for 375px screens */
 428 |   .topbar{
 429 |     padding:0;
 430 |     min-height:28px;
 431 |     flex-shrink:0;
 432 |   }
 433 |   .topbar-brand{font-size:9px;letter-spacing:.25em}
 434 |   .live-pill{padding:2px 6px}
 435 |   .live-text{font-size:8px}
 436 |   .stage-controls{gap:4px}
 437 |   #minimize-btn,#exit-btn{width:26px;height:26px}
 438 | 
 439 |   /* Video: constrain to 60vh max, centered */
 440 |   .video-wrap{
 441 |     max-height:60vh;
 442 |     max-width:calc(100vw - 20px);
 443 |     width:100%;
 444 |     aspect-ratio:1/1;
 445 |     margin:0 auto;
 446 |     flex-shrink:1;
 447 |     min-height:0;
 448 |   }
 449 |   #vid{
 450 |     width:100%;
 451 |     height:100%;
 452 |     max-width:340px;
 453 |     margin:0 auto;
 454 |     display:block;
 455 |     border-radius:8px;
 456 |     object-fit:cover;
 457 |   }
 458 | 
 459 |   /* Subtitle: tighter */
 460 |   #subtitle{
 461 |     font-size:11px;
 462 |     min-height:28px;
 463 |     padding:0 2px;
 464 |     flex-shrink:0;
 465 |   }
 466 | 
 467 |   /* Status + transcript: compact */
 468 |   #stat{font-size:10px;height:16px;flex-shrink:0}
 469 |   #tx{font-size:10px;min-height:14px;flex-shrink:0}
 470 | 
 471 |   /* Mic area + input controls: sticky to bottom, full width, tap-friendly */
 472 |   .mic-area{
 473 |     width:100%;
 474 |     flex-shrink:0;
 475 |     padding-bottom:env(safe-area-inset-bottom,8px);
 476 |     margin-top:auto;
 477 |   }
 478 |   #mic{
 479 |     width:60px;height:60px;
 480 |     min-width:48px;min-height:48px;
 481 |   }
 482 |   .mic-hint{font-size:9px}
 483 | 
 484 |   /* Camera button: 48px touch target */
 485 |   #cam-btn{
 486 |     width:48px;height:48px;
 487 |     min-width:48px;min-height:48px;
 488 |   }
 489 | 
 490 |   /* Vision status */
 491 |   #vision-status{font-size:9px;min-height:12px}
 492 | 
 493 |   /* Cards grid: 1 column on mobile */
 494 |   #cards{grid-template-columns:1fr}
 495 |   #cards.on{
 496 |     display:grid;
 497 |     max-height:30vh;
 498 |     overflow-y:auto;
 499 |     -webkit-overflow-scrolling:touch;
 500 |   }
 501 |   .card{
 502 |     padding:10px;
 503 |     min-height:48px;
 504 |     display:flex;flex-direction:row;align-items:center;
 505 |     gap:8px;
 506 |   }
 507 |   .card-title{font-size:13px}
 508 |   .card-link{font-size:10px}
 509 | 
 510 |   /* Gate: ensure it fits small screens */
 511 |   #gate{
 512 |     padding:20px 16px;
 513 |     gap:16px;
 514 |   }
 515 |   .sigil-wrap{width:130px;height:130px}
 516 |   .gate-title{font-size:32px}
 517 |   .gate-sub{font-size:13px;max-width:260px}
 518 |   #gate-btn{width:220px}
 519 |   .btn-inner{padding:14px 20px}
 520 |   #gate-status{font-size:10px}
 521 |   #gate-error{font-size:11px;max-width:260px}
 522 | 
 523 |   /* Float bubble: smaller on mobile */
 524 |   #oracle-float{
 525 |     width:56px;height:56px;
 526 |     bottom:16px;right:16px;
 527 |   }
 528 | }
 529 | 
 530 | /* ── STUDIO TREATMENT (oracle-live only) ─────────── */
 531 | .video-wrap {
 532 |   border: 2px solid rgba(220,38,38,0.4);
 533 |   box-shadow: 0 0 40px rgba(220,38,38,0.15);
 534 | }
 535 | #oracle-matrix { pointer-events: none; }
 536 | 
 537 | /* ── VISION TRANSCRIPT ─────────────────────────── */
 538 | .vision-entry {
 539 |   padding: 10px 14px;
 540 |   border-bottom: 1px solid rgba(255,255,255,.04);
 541 |   cursor: pointer;
 542 | }
 543 | .vision-entry:hover { background: rgba(255,255,255,.03); }
 544 | .vision-entry:last-child { border-bottom: none; }
 545 | .vision-entry-device {
 546 |   font-family: monospace;
 547 |   font-size: 10px;
 548 |   letter-spacing: .1em;
 549 |   color: rgba(255,59,95,.7);
 550 |   text-transform: uppercase;
 551 |   margin-bottom: 4px;
 552 | }
 553 | .vision-entry-step {
 554 |   font-size: 0.8rem;
 555 |   color: rgba(255,255,255,.7);
 556 |   line-height: 1.5;
 557 |   margin: 2px 0;
 558 | }
 559 | .vision-entry-time {
 560 |   font-family: monospace;
 561 |   font-size: 9px;
 562 |   color: rgba(255,255,255,.2);
 563 |   margin-top: 4px;
 564 | }
 565 | </style>
 566 | </head>
 567 | <body>
 568 | <div id="vision-security-overlay" style="display:none;position:fixed;inset:0;
 569 | z-index:99999;background:rgba(180,0,0,0.97);flex-direction:column;
 570 | align-items:center;justify-content:center;padding:32px;text-align:center;">
 571 |   <div style="font-size:64px;margin-bottom:16px;">⚠️</div>
 572 |   <div style="font-family:monospace;font-size:13px;letter-spacing:.12em;
 573 | color:rgba(255,255,255,.6);margin-bottom:8px;text-transform:uppercase;">
 574 | SECURITY ALERT</div>
 575 |   <div id="vision-security-msg" style="font-size:1.2rem;font-weight:700;
 576 | color:#fff;margin-bottom:32px;line-height:1.5;max-width:340px;"></div>
 577 |   <button id="vision-security-dismiss"
 578 |     style="background:#fff;color:#b40000;font-family:monospace;font-weight:800;
 579 | font-size:14px;letter-spacing:.1em;border:none;border-radius:8px;
 580 | padding:16px 32px;cursor:pointer;text-transform:uppercase;
 581 | min-height:56px;width:100%;max-width:320px;">
 582 |     ✓ GOT IT — COVER NOW
 583 |   </button>
 584 |   <div id="vision-recovery-panel" style="display:none;width:100%;
 585 | max-width:340px;margin-top:24px;">
 586 |     <div style="font-family:monospace;font-size:11px;letter-spacing:.12em;
 587 | color:rgba(255,255,255,.5);margin-bottom:12px;text-transform:uppercase;">
 588 | YOUR FUNDS MAY BE AT RISK — ACT NOW</div>
 589 |     <div id="vision-recovery-step-label" style="font-family:monospace;
 590 | font-size:11px;color:rgba(255,200,0,.8);letter-spacing:.1em;
 591 | margin-bottom:8px;text-transform:uppercase;">STEP 1 OF 3</div>
 592 |     <div id="vision-recovery-step-text" style="font-size:1rem;
 593 | font-weight:600;color:#fff;line-height:1.6;margin-bottom:24px;"></div>
 594 |     <button id="vision-recovery-next"
 595 |       style="background:rgba(255,255,255,.15);color:#fff;
 596 | font-family:monospace;font-weight:700;font-size:13px;
 597 | letter-spacing:.08em;border:2px solid rgba(255,255,255,.3);
 598 | border-radius:8px;padding:14px 24px;cursor:pointer;
 599 | text-transform:uppercase;min-height:52px;width:100%;">
 600 |       NEXT STEP →
 601 |     </button>
 602 |     <button id="vision-recovery-help"
 603 |       style="display:none;background:#fff;color:#b40000;
 604 | font-family:monospace;font-weight:800;font-size:13px;
 605 | letter-spacing:.08em;border:none;border-radius:8px;
 606 | padding:14px 24px;cursor:pointer;text-transform:uppercase;
 607 | min-height:52px;width:100%;margin-top:8px;">
 608 |       HELP ME SET UP NEW WALLET
 609 |     </button>
 610 |     <button id="vision-recovery-close"
 611 |       style="display:none;background:none;color:rgba(255,255,255,.4);
 612 | font-family:monospace;font-size:11px;letter-spacing:.08em;
 613 | border:none;padding:12px;cursor:pointer;text-transform:uppercase;
 614 | width:100%;margin-top:4px;">
 615 |       I UNDERSTAND THE RISK — CLOSE
 616 |     </button>
 617 |   </div>
 618 | </div>
 619 | <div id="mobile-nav-bar" style="display:none;position:fixed;top:0;left:0;right:0;z-index:9998;background:rgba(4,5,10,.95);padding:10px 16px;border-bottom:1px solid rgba(255,59,95,.15);align-items:center;gap:12px;">
 620 |   <button onclick="window.history.back()" style="background:none;border:1px solid rgba(255,255,255,.15);color:rgba(255,255,255,.6);padding:6px 14px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;letter-spacing:.08em;">&larr; BACK</button>
 621 |   <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:rgba(255,59,95,.8);letter-spacing:.15em;">ORACLE &mdash; PROTOCOL PULSE</span>
 622 | </div>
 623 | <div id="root">
 624 | 
 625 | <!-- ══ GATE ══ -->
 626 | <div id="gate">
 627 |   <div class="gate-brand">Protocol Pulse</div>
 628 | 
 629 |   <div class="sigil-wrap">
 630 |     <div class="ring ring-1"></div>
 631 |     <div class="ring ring-2"></div>
 632 |     <div class="sigil-avatar">
 633 |       <img src="/static/oracle_avatar.png" alt="Oracle"
 634 |            onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
 635 |       <div class="sigil-fallback" style="display:none">⚡</div>
 636 |     </div>
 637 |     <div class="sigil-scan"></div>
 638 |   </div>
 639 | 
 640 |   <h1 class="gate-title">THE <span>ORACLE</span></h1>
 641 |   <p class="gate-sub">Sovereign Bitcoin intelligence.<br>Ask anything, in real time.</p>
 642 | 
 643 |   <button id="gate-btn" onclick="requestMic()">
 644 |     <div class="btn-sweep"></div>
 645 |     <div class="btn-inner">
 646 |       <div class="btn-label">Protocol Pulse Intelligence</div>
 647 |       <div class="btn-text">
 648 |         <svg class="btn-mic-icon" viewBox="0 0 24 24" fill="none">
 649 |           <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 650 |           <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 651 |           <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 652 |         </svg>
 653 |         Speak to the Oracle
 654 |       </div>
 655 |     </div>
 656 |   </button>
 657 | 
 658 |   <div id="gate-status">— tap to activate —</div>
 659 |   <div id="gate-error"></div>
 660 | </div>
 661 | 
 662 | <!-- ══ LIVE STAGE ══ -->
 663 | <div id="stage">
 664 | 
 665 |   <div class="topbar">
 666 |     <span class="topbar-brand">Oracle</span>
 667 |     <div class="live-pill"><div class="live-dot"></div><span class="live-text">LIVE</span></div>
 668 |     <a href="/" style="margin-left:auto;color:rgba(255,255,255,0.3);font-size:22px;text-decoration:none;padding:4px 10px;line-height:1;transition:color 0.2s;" onmouseover="this.style.color='rgba(255,255,255,0.8)'" onmouseout="this.style.color='rgba(255,255,255,0.3)'" aria-label="Exit Oracle" title="Go to homepage">&times;</a>
 669 |   </div>
 670 | 
 671 |   <canvas id="bg-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;will-change:transform;"></canvas>
 672 | 
 673 |   <div class="video-wrap" style="position:relative;z-index:1;">
 674 |     <canvas id="oracle-matrix" style="position:absolute;inset:0;width:100%;height:100%;z-index:1;opacity:1;transition:opacity 0.5s;"></canvas>
 675 |     <video id="vid" playsinline webkit-playsinline x-webkit-airplay="allow" preload="auto" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;z-index:2;"></video>
 676 |   </div>
 677 | 
 678 |   <div id="subtitle"></div>
 679 |   <div id="oracle-action-card" style="display:none;margin-top:12px;max-width:min(440px,calc(100vw - 24px));width:100%;"></div>
 680 | 
 681 |   <div id="stat">
 682 |     <span class="spin" id="spin"></span>
 683 |     <span id="stat-text">Ready</span>
 684 |   </div>
 685 | 
 686 |   <div id="tx"></div>
 687 | 
 688 |   <div class="mic-area">
 689 |     <button id="mic" disabled onclick="toggleMic()">
 690 |       <svg id="i-mic" width="24" height="24" viewBox="0 0 24 24" fill="none">
 691 |         <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 692 |         <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 693 |         <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 694 |         <line x1="9" y1="22" x2="15" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 695 |       </svg>
 696 |       <svg id="i-stop" width="24" height="24" viewBox="0 0 24 24" fill="none" style="display:none">
 697 |         <rect x="6" y="6" width="12" height="12" rx="2" fill="#fff"/>
 698 |       </svg>
 699 |     </button>
 700 |     <span class="mic-hint" id="mic-hint">tap to speak</span>
 701 |   </div>
 702 | 
 703 |   <!-- Vision status + Camera button -->
 704 |   <div id="vision-status"></div>
 705 |   <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:4px">
 706 |     <button id="cam-btn" onclick="triggerCamera()" title="Show Oracle your screen — it will guide you step by step">
 707 |       <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
 708 |         <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke="#556" stroke-width="1.5" stroke-linecap="round"/>
 709 |         <circle cx="12" cy="13" r="4" stroke="#556" stroke-width="1.5"/>
 710 |       </svg>
 711 |     </button>
 712 |     <span id="cam-btn-label" style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.08em">ANALYZE HARDWARE</span>
 713 |   </div>
 714 |   <div id="vision-transcript-panel" style="display:none;
 715 |   width:100%;max-width:min(440px,calc(100vw - 24px));
 716 |   margin:12px auto 0;background:rgba(6,7,14,.9);
 717 |   border:1px solid rgba(255,59,95,.15);border-radius:8px;
 718 |   overflow:hidden;">
 719 |     <div style="display:flex;align-items:center;justify-content:space-between;
 720 |   padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.06);">
 721 |       <span style="font-family:monospace;font-size:10px;letter-spacing:.12em;
 722 |   color:rgba(255,59,95,.8);text-transform:uppercase;">SESSION LOG</span>
 723 |       <button id="vision-transcript-clear"
 724 |         style="background:none;border:none;color:rgba(255,255,255,.3);
 725 |   font-family:monospace;font-size:9px;letter-spacing:.08em;
 726 |   cursor:pointer;text-transform:uppercase;padding:2px 6px;">
 727 |         CLEAR
 728 |       </button>
 729 |     </div>
 730 |     <div id="vision-transcript-entries" style="max-height:280px;
 731 |   overflow-y:auto;padding:8px 0;"></div>
 732 |   </div>
 733 | 
 734 |   <input type="file" id="cam-input" accept="image/*" capture="environment" onchange="handleVisionUpload(event)">
 735 | 
 736 |   <div id="cards">
 737 |     <div class="card" onclick="si('SOVEREIGNTY_COLD_WALLET')">
 738 |       <div class="card-title">&#128272; Self-Custody</div>
 739 |       <a class="card-link" href="https://coldcard.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">coldcard.com &#8594;</a>
 740 |     </div>
 741 |     <div class="card" onclick="si('SOVEREIGNTY_NODE')">
 742 |       <div class="card-title">&#9889; Run a Node</div>
 743 |       <a class="card-link" href="https://getumbrel.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">getumbrel.com &#8594;</a>
 744 |     </div>
 745 |     <div class="card" onclick="si('SOVEREIGNTY_BITAXE')">
 746 |       <div class="card-title">&#9935; Solo Mining</div>
 747 |       <a class="card-link" href="https://curatedmining.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">curatedmining.com &#8594;</a>
 748 |     </div>
 749 |     <div class="card" onclick="si('SOVEREIGNTY_LIFE_INSURANCE')">
 750 |       <div class="card-title">&#128737; BTC Insurance</div>
 751 |       <a class="card-link" href="https://application.meanwhile.bm/start?referralCode=KKM73K" target="_blank" rel="noopener" onclick="event.stopPropagation()">meanwhile.bm &#8594;</a>
 752 |     </div>
 753 |   </div>
 754 | 
 755 | </div><!-- /stage -->
 756 | </div><!-- /root -->
 757 | 
 758 | <script>
 759 | 'use strict';
 760 | /* ── iOS zoom prevention ── */
 761 | document.addEventListener('gesturestart',function(e){e.preventDefault();},{passive:false});
 762 | document.addEventListener('touchmove',function(e){if(e.touches.length>1)e.preventDefault();},{passive:false});
 763 | var A='https://avatar.protocolpulse.io';
 764 | var S={
 765 |   GREETING:"Hey. I'm the Oracle — tracking everything happening in Bitcoin right now. On-chain, macro, geopolitical. What brings you here?",
 766 |   SOVEREIGNTY_INTRO:"Your sovereignty score is a snapshot of how free you actually are — how much of your financial life you've pulled out of legacy systems.",
 767 |   SOVEREIGNTY_ASSESSMENT:"Four pillars: self-custody of your Bitcoin, your own node, private comms, and no KYC on your income. Where are you today?",
 768 |   SOVEREIGNTY_COLD_WALLET:"If your Bitcoin is on an exchange, it's not yours — it's an IOU. A hardware wallet fixes that. I can walk you through it.",
 769 |   SOVEREIGNTY_NODE:"Running your own node means you verify your own transactions. You don't trust, you verify. Umbrel on a Pi is the easiest path.",
 770 |   SOVEREIGNTY_BITAXE:"Bitaxe is a solo miner you can run at home. A Bitcoin lottery ticket. Curated Mining also does white-glove setup.",
 771 |   SOVEREIGNTY_LIFE_INSURANCE:"If you die with Bitcoin in cold storage and nobody knows the seed phrase, it's gone. Meanwhile offers life insurance that actually understands Bitcoin.",
 772 |   SOVEREIGNTY_RESIDENCY:"Digital residency through Palau via RNS.ID gives you a second legal identity outside your home country. Real tax and privacy implications.",
 773 |   DAILY_BRIEF_INTRO:"Here's what's moving in Bitcoin right now. Pulling the latest from our intelligence layer...",
 774 |   DAILY_BRIEF_LIVE:"Here's today's Bitcoin intelligence brief.",
 775 |   UNKNOWN_QUESTION:"I'm researching that now. One moment.",
 776 |   GOODBYE:"Stack sats, verify everything, and come back anytime."
 777 | };
 778 | 
 779 | var busy=false,isRec=false,pending='',objURL=null,recognition=null;
 780 | var _greeted=false;
 781 | 
 782 | /* ── ORACLE STATE MACHINE ──
 783 |    States: WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING
 784 |    Every state shows the avatar face (never black screen).
 785 |    LISTENING: mic active, avatar static idle visible, status "Ready"
 786 |    PROCESSING: mic off, spinner, avatar idle visible
 787 |    RESPONDING: video playing over idle bg, mic off
 788 | */
 789 | var ORACLE_STATE = 'IDLE'; /* IDLE, WELCOME, LISTENING, PROCESSING, RESPONDING */
 790 | function setOracleState(state){
 791 |   ORACLE_STATE = state;
 792 |   console.log('[Oracle] State →', state);
 793 |   switch(state){
 794 |     case 'LISTENING':
 795 |       mic.disabled=false;
 796 |       setStat('Ready','#334',false);
 797 |       /* Ensure avatar idle is visible (video-wrap bg shows through when vid is transparent) */
 798 |       vid.style.opacity='0';
 799 |       break;
 800 |     case 'PROCESSING':
 801 |       mic.disabled=true;
 802 |       if(isRec) stopRec();
 803 |       break;
 804 |     case 'RESPONDING':
 805 |       mic.disabled=true;
 806 |       if(isRec) stopRec();
 807 |       break;
 808 |     case 'WELCOME':
 809 |       mic.disabled=true;
 810 |       break;
 811 |   }
 812 | }
 813 | 
 814 | var VISION_SPONSOR_MAP = {
 815 |   'trezor':   { category:'amazon', title:'Trezor Hardware Wallet', id:'vision_trezor',
 816 |     description:'The original Bitcoin hardware wallet. Battle-tested since 2014.',
 817 |     url:'https://amzn.to/trezor', cta:'View on Amazon' },
 818 |   'coldcard': { category:'affiliate', title:'Coldcard Mk4', id:'vision_coldcard',
 819 |     description:'The most secure Bitcoin signing device. Air-gapped by default.',
 820 |     url:'https://coldcard.com', cta:'Get Coldcard' },
 821 |   'ledger':   { category:'amazon', title:'Ledger Hardware Wallet', id:'vision_ledger',
 822 |     description:'Secure your Bitcoin with industry-leading hardware security.',
 823 |     url:'https://amzn.to/ledger', cta:'View on Amazon' },
 824 |   'bitaxe':   { category:'affiliate', title:'BitAxe Solo Miner', id:'vision_bitaxe',
 825 |     description:'Open-source Bitcoin miner. Stack sats from your home.',
 826 |     url:'https://bitaxe.org', cta:'Get BitAxe' },
 827 |   'umbrel':   { category:'affiliate', title:'Umbrel Home Server', id:'vision_umbrel',
 828 |     description:'Run your own Bitcoin node. Your keys, your coins.',
 829 |     url:'https://umbrel.com', cta:'Run Umbrel' },
 830 |   'start9':   { category:'affiliate', title:'Start9 Embassy', id:'vision_start9',
 831 |     description:'Sovereign computing for the sovereign individual.',
 832 |     url:'https://start9.com', cta:'Get Embassy' },
 833 |   'seedsigner':{ category:'affiliate', title:'SeedSigner', id:'vision_seedsigner',
 834 |     description:'Air-gapped signing device. Build your own or buy assembled.',
 835 |     url:'https://seedsigner.com', cta:'Learn More' },
 836 |   'passport': { category:'affiliate', title:'Foundation Passport', id:'vision_passport',
 837 |     description:'Open-source, air-gapped Bitcoin hardware wallet.',
 838 |     url:'https://foundationdevices.com', cta:'Get Passport' },
 839 |   'jade':     { category:'affiliate', title:'Blockstream Jade', id:'vision_jade',
 840 |     description:'Open-source hardware wallet with air-gapped signing.',
 841 |     url:'https://store.blockstream.com', cta:'Get Jade' }
 842 | };
 843 | 
 844 | function pulseMic(){
 845 |   if(!mic||mic.disabled||isRec)return;
 846 |   mic.classList.remove('idle-pulse');
 847 |   void mic.offsetWidth;
 848 |   mic.classList.add('idle-pulse');
 849 |   setStat('Tap mic to respond','#ff3b5f',false);
 850 |   setTimeout(function(){mic.classList.remove('idle-pulse');setStat('Ready','#334',false);},6000);
 851 | }
 852 | 
 853 | // ── VISITOR FINGERPRINT ───────────────────────────────────
 854 | // Generates a stable browser fingerprint — no cookies, no login
 855 | // Used server-side to recognize returning visitors
 856 | (function() {
 857 |   try {
 858 |     var fp = '';
 859 |     // Canvas fingerprint
 860 |     var canvas = document.createElement('canvas');
 861 |     var ctx = canvas.getContext('2d');
 862 |     ctx.textBaseline = 'top';
 863 |     ctx.font = '14px Arial';
 864 |     ctx.fillText('Oracle fp', 2, 2);
 865 |     fp += canvas.toDataURL().slice(-20);
 866 |     // Screen + timezone
 867 |     fp += screen.width + 'x' + screen.height + Intl.DateTimeFormat().resolvedOptions().timeZone;
 868 |     // Hash it (simple djb2)
 869 |     var hash = 5381;
 870 |     for (var i = 0; i < fp.length; i++) {
 871 |       hash = ((hash << 5) + hash) + fp.charCodeAt(i);
 872 |       hash = hash & hash; // 32-bit int
 873 |     }
 874 |     window._visitorToken = Math.abs(hash).toString(36);
 875 |   } catch(e) {
 876 |     window._visitorToken = 'anon';
 877 |   }
 878 | })();
 879 | 
 880 | // Read session_id and page context from URL params (injected by widget)
 881 | var _urlParams = new URLSearchParams(window.location.search);
 882 | var SESSION_ID = _urlParams.get('session_id') || ('sess_'+Date.now()+'_'+Math.random().toString(36).slice(2,8));
 883 | window.ORACLE_FINGERPRINT_MATCH = false;
 884 | var PAGE_CONTEXT = {
 885 |   type: _urlParams.get('page_type') || 'general',
 886 |   path: _urlParams.get('page_path') || window.location.pathname,
 887 |   content: null,
 888 |   url: document.referrer || window.location.href,
 889 | };
 890 | 
 891 | // Receive richer context from parent widget via postMessage
 892 | window.addEventListener('message', function(e) {
 893 |   if (!e.data || typeof e.data !== 'object') return;
 894 |   var d = e.data;
 895 |   if (d.type === 'oracle:context') {
 896 |     // Parent widget sent full page context
 897 |     if (d.sessionId) SESSION_ID = d.sessionId;
 898 |     if (d.pageContext) PAGE_CONTEXT = d.pageContext;
 899 |   }
 900 | });
 901 | 
 902 | // Tell parent we want context (in case we loaded before message was sent)
 903 | setTimeout(function(){
 904 |   try{ if(window.parent!==window) window.parent.postMessage({type:'oracle:context_request'},'*'); }catch(e){}
 905 | },300);
 906 | 
 907 | /* DOM */
 908 | var gate=document.getElementById('gate');
 909 | var stage=document.getElementById('stage');
 910 | var gBtn=document.getElementById('gate-btn');
 911 | var gStatus=document.getElementById('gate-status');
 912 | var gErr=document.getElementById('gate-error');
 913 | var vid=document.getElementById('vid');
 914 | var sub=document.getElementById('subtitle');
 915 | var statEl=document.getElementById('stat-text');
 916 | var spinEl=document.getElementById('spin');
 917 | var txEl=document.getElementById('tx');
 918 | var mic=document.getElementById('mic');
 919 | var micHint=document.getElementById('mic-hint');
 920 | var iMic=document.getElementById('i-mic');
 921 | var iStop=document.getElementById('i-stop');
 922 | var cards=document.getElementById('cards');
 923 | 
 924 | /* ── MIC REQUEST ── */
 925 | function requestMic(){
 926 |   gBtn.disabled=true;
 927 |   gStatus.textContent='Requesting microphone...';
 928 |   gErr.style.display='none';
 929 | 
 930 |   /* CRITICAL: unlock audio context immediately on this user gesture */
 931 |   try{
 932 |     var _unlockAc=new(window.AudioContext||window.webkitAudioContext)();
 933 |     var _unlockBuf=_unlockAc.createBuffer(1,1,22050);
 934 |     var _unlockSrc=_unlockAc.createBufferSource();
 935 |     _unlockSrc.buffer=_unlockBuf;_unlockSrc.connect(_unlockAc.destination);_unlockSrc.start(0);
 936 |     setTimeout(function(){try{_unlockAc.close();}catch(e){}},300);
 937 |   }catch(e){}
 938 | 
 939 |   try{
 940 |     var ac=new(window.AudioContext||window.webkitAudioContext)();
 941 |     var buf=ac.createBuffer(1,1,22050);
 942 |     var src=ac.createBufferSource();
 943 |     src.buffer=buf;src.connect(ac.destination);src.start(0);
 944 |     setTimeout(function(){try{ac.close();}catch(e){}},500);
 945 |   }catch(e){}
 946 | 
 947 |   /* Also "unlock" video element immediately */
 948 |   vid.muted=true;
 949 |   vid.play().catch(function(){});
 950 | 
 951 |   /* Pre-unlock Audio element for PATH B (chat responses) */
 952 |   window._audioUnlocked = new Audio();
 953 |   window._audioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
 954 |   window._audioUnlocked.volume = 0.001;
 955 |   window._audioUnlocked.play().catch(function(){});
 956 | 
 957 |   window._chatAudioPlaying = false;
 958 | 
 959 |   navigator.mediaDevices.getUserMedia({audio:true,video:false})
 960 |     .then(function(stream){
 961 |       stream.getTracks().forEach(function(t){t.stop();}); /* don't need stream, just the gesture */
 962 |       gStatus.textContent='';
 963 |       go();
 964 |     })
 965 |     .catch(function(err){
 966 |       console.warn('[Oracle mic error]', err);
 967 |       gBtn.disabled=false;
 968 |       gStatus.textContent='';
 969 |       gErr.style.display='block';
 970 |       var name = err && err.name ? err.name : '';
 971 |       if(name === 'NotAllowedError' || name === 'PermissionDeniedError'){
 972 |         gErr.innerHTML='&#9888;&#xFE0F; Microphone blocked. Click the camera/mic icon in your browser address bar and allow access, then <a href="javascript:location.reload()" style="color:#ff3b5f;text-decoration:underline;">reload</a>.';
 973 |       } else if(name === 'NotReadableError' || name === 'TrackStartError'){
 974 |         gErr.innerHTML='&#9888;&#xFE0F; Microphone is in use by another app. Close other tabs or apps using the mic, then <button onclick="requestMic()" style="background:none;border:none;color:#ff3b5f;text-decoration:underline;cursor:pointer;padding:0;font-size:inherit;">try again</button>.';
 975 |       } else if(name === 'NotFoundError'){
 976 |         gErr.innerHTML='&#9888;&#xFE0F; No microphone found. Connect a microphone and <button onclick="requestMic()" style="background:none;border:none;color:#ff3b5f;text-decoration:underline;cursor:pointer;padding:0;font-size:inherit;">try again</button>.';
 977 |       } else {
 978 |         gErr.innerHTML='&#9888;&#xFE0F; Microphone unavailable ('+name+'). Try clicking <button onclick="requestMic()" style="background:none;border:none;color:#ff3b5f;text-decoration:underline;cursor:pointer;padding:0;font-size:inherit;">here to retry</button> or check browser settings.';
 979 |       }
 980 |     });
 981 | }
 982 | 
 983 | /* ── TRANSITION ── */
 984 | function go(){
 985 |   gate.style.opacity='0';
 986 |   setTimeout(function(){
 987 |     gate.style.display='none';
 988 |     stage.style.display='flex';
 989 |     stage.style.opacity='0';
 990 |     setTimeout(function(){
 991 |       stage.style.transition='opacity .45s';
 992 |       stage.style.opacity='1';
 993 |       initSR();
 994 |       setOracleState('WELCOME');
 995 |       playIntent('GREETING');
 996 |     },30);
 997 |   },350);
 998 | }
 999 | 
1000 | /* ── PLAY CACHED INTENT ── */
1001 | function playIntent(intent){
1002 |   if(busy&&intent!=='GREETING')return;
1003 |   if(intent.indexOf('DAILY_BRIEF')===0&&window._briefFetched)return;
1004 |   setBusy(true);
1005 |   setStat('Oracle loading...','#f4c46f',true);
1006 |   // Progress messages so user knows it's working, not broken
1007 |   var _loadMsgs = ['Initializing...','Rendering response...','Almost ready...'];
1008 |   var _loadIdx = 0;
1009 |   var _loadTimer = setInterval(function(){
1010 |     _loadIdx++;
1011 |     if(_loadIdx < _loadMsgs.length) setStat(_loadMsgs[_loadIdx],'#f4c46f',true);
1012 |     else clearInterval(_loadTimer);
1013 |   }, 6000);
1014 |   var _clearTimer = function(){ clearInterval(_loadTimer); };
1015 |   showSub(S[intent]||'');
1016 |   fetchTO(A+'/oracle/speak',{
1017 |     method:'POST',
1018 |     headers:{'Content-Type':'application/json'},
1019 |     body:JSON.stringify({intent:intent})
1020 |   },30000)
1021 |   .then(function(r){
1022 |     if(!r.ok)throw new Error('HTTP '+r.status);
1023 |     var ct=r.headers.get('content-type')||'';
1024 |     if(ct.indexOf('video')>=0)return r.blob().then(blobURL);
1025 |     return r.json().then(function(j){
1026 |       return fetchTO(A+j.video_url,{},20000).then(function(r2){return r2.blob().then(blobURL);});
1027 |     });
1028 |   })
1029 |   .then(function(url){ if(typeof _clearTimer=='function') _clearTimer(); return playVid(url);})
1030 |   .then(function(){
1031 |     if(intent==='SOVEREIGNTY_ASSESSMENT')showCards();
1032 |     if(intent==='GREETING'){
1033 |       window._briefFetched=false;
1034 |       _greeted=true;
1035 |       /* State machine: welcome done → LISTENING. Always activate mic. */
1036 |       setOracleState('LISTENING');
1037 |       setTimeout(function(){
1038 |         if(!busy&&!isRec&&mic){
1039 |           mic.disabled=false;
1040 |           startRec();
1041 |           setStat('Listening…','#6cff9f',false);
1042 |         }
1043 |       },400);
1044 |     }
1045 |   })
1046 |   .catch(function(e){
1047 |     if(e&&e.message&&e.message.indexOf('HTTP')>=0)
1048 |       setStat('Oracle error — try again.','#ff3b5f',false);
1049 |   })
1050 |   .finally(function(){
1051 |     setBusy(false);
1052 |     setOracleState('LISTENING');
1053 |     setTimeout(pulseMic,500);
1054 |   });
1055 | }
1056 | 
1057 | function si(intent){if(busy)return;hideCards();playIntent(intent);}
1058 | 
1059 | /* ── PROCESS SPEECH (two-phase: audio-first + async video) ── */
1060 | function process(text){
1061 |   if(!text.trim()||busy)return;
1062 |   // Guard: mark brief as fetched to prevent double-play with DAILY_BRIEF_INTRO
1063 |   if(/daily\s*brief/i.test(text)) window._briefFetched=true;
1064 |   setOracleState('PROCESSING');
1065 |   setBusy(true);hideCards();hideActionCard();showTX(text);
1066 |   setStat('Oracle thinking...','#f4c46f',true);
1067 | 
1068 |   // Re-unlock audio context on every user interaction
1069 |   try{
1070 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1071 |     if(_ac.state==='suspended') _ac.resume();
1072 |     var _buf=_ac.createBuffer(1,1,22050);
1073 |     var _src=_ac.createBufferSource();
1074 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1075 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1076 |   }catch(e){}
1077 | 
1078 |   var pendingVideoUrl=null;
1079 |   var _audioFinished=false;
1080 | 
1081 |   fetchTO(A+'/oracle/chat',{
1082 |     method:'POST',headers:{'Content-Type':'application/json'},
1083 |     body:JSON.stringify({text:text,session_id:SESSION_ID,visitor_token:window._visitorToken||'anon',use_cache_for_intents:true,page_context:PAGE_CONTEXT,audio_first:true,avatar_source:"oracle_studio"})
1084 |   },90000)
1085 |   .then(function(r){
1086 |     if(!r.ok) throw new Error('HTTP '+r.status);
1087 |     var ct=r.headers.get('content-type')||'';
1088 |     if(ct.indexOf('video')>=0){
1089 |       // Cache hit — video came back immediately
1090 |       return r.blob().then(blobURL).then(function(url){ return playVid(url); });
1091 |     }
1092 |     // Audio-first JSON response
1093 |     return r.json().then(function(j){
1094 |       var responseText=j.text;
1095 |       var videoJobId=j.job_id;
1096 |       var _pendingCard = j.action_card || null;
1097 | 
1098 |       // Play audio: try cached job audio first (no duplicate Kokoro), fallback to /oracle/voice
1099 |       var audioFetch;
1100 |       if(videoJobId){
1101 |         audioFetch=fetchTO(A+'/oracle/job/'+videoJobId+'/audio',{},35000)
1102 |           .then(function(ar){
1103 |             if(!ar.ok) throw new Error('no cached audio');
1104 |             return ar.blob();
1105 |           })
1106 |           .catch(function(){
1107 |             return fetchTO(A+'/oracle/voice',{
1108 |               method:'POST',headers:{'Content-Type':'application/json'},
1109 |               body:JSON.stringify({text:responseText})
1110 |             },35000).then(function(ar){
1111 |               if(!ar.ok) throw new Error('audio failed');
1112 |               return ar.blob();
1113 |             });
1114 |           });
1115 |       } else {
1116 |         audioFetch=fetchTO(A+'/oracle/voice',{
1117 |           method:'POST',headers:{'Content-Type':'application/json'},
1118 |           body:JSON.stringify({text:responseText})
1119 |         },35000).then(function(ar){
1120 |           if(!ar.ok) throw new Error('audio failed');
1121 |           return ar.blob();
1122 |         });
1123 |       }
1124 |       return audioFetch
1125 |       .then(function(b){
1126 |         return new Blob([b], {type: b.type || 'audio/wav'});
1127 |       })
1128 |       .then(function(audioBlob){
1129 |         var audioUrl=URL.createObjectURL(audioBlob);
1130 |         var audio;
1131 |         if(window._audioUnlocked){
1132 |           audio=window._audioUnlocked;
1133 |           window._audioUnlocked=null;
1134 |           audio.src=audioUrl;
1135 |           audio.volume=1.0;
1136 |           audio.muted=false;
1137 |         } else {
1138 |           audio=new Audio(audioUrl);
1139 |           audio.volume=1.0;
1140 |         }
1141 |         window._chatAudioPlaying=true;
1142 |         var playPromise = audio.play();
1143 |         if(playPromise !== undefined){
1144 |           playPromise.then(function(){
1145 |             setStat('Speaking','#6cff9f',false);
1146 |           }).catch(function(err){
1147 |             console.warn('[Oracle] audio.play() rejected:', err.name);
1148 |             // On mobile, audio may be blocked — set volume via user gesture retry
1149 |             audio.muted = false;
1150 |             audio.volume = 1.0;
1151 |             setTimeout(function(){
1152 |               audio.play().catch(function(e2){
1153 |                 console.warn('[Oracle] retry failed:', e2.name);
1154 |                 if(audio.onended) audio.onended();
1155 |               });
1156 |             }, 100);
1157 |           });
1158 |         }
1159 | 
1160 |         return new Promise(function(resolve){
1161 |           audio.onended=function(){
1162 |             _audioFinished=true;
1163 |             if(_pendingCard){ showActionCard(_pendingCard); _pendingCard=null; }
1164 |             window._chatAudioPlaying=false;
1165 |             URL.revokeObjectURL(audioUrl);
1166 |             // Audio finished — unmute video if it's playing lip sync
1167 |             try{ if(!vid.paused){ vid.muted=false; vid.volume=1.0; } }catch(e){}
1168 |             // Don't replay lip-sync video after audio already finished — just resolve
1169 |             if(pendingVideoUrl){
1170 |               try { URL.revokeObjectURL(pendingVideoUrl); } catch(e) {}
1171 |             }
1172 |             resolve();
1173 |           };
1174 | 
1175 |           // Poll for video completion in parallel
1176 |           if(videoJobId){
1177 |             var pollAttempts=0,maxPollAttempts=60;
1178 |             var pollVideo=setInterval(function(){
1179 |               pollAttempts++;
1180 |               fetch(A+'/oracle/job/'+videoJobId)
1181 |                 .then(function(vr){
1182 |                   if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1183 |                     return vr.blob();
1184 |                   }
1185 |                   return null;
1186 |                 })
1187 |                 .then(function(vb){
1188 |                   if(vb){
1189 |                     clearInterval(pollVideo);
1190 |                     pendingVideoUrl=blobURL(vb);
1191 |                     // Only play lip-sync video if audio has already finished
1192 |                     if (_audioFinished) {
1193 |                       vid.style.opacity='1';
1194 |                       playVid(pendingVideoUrl);
1195 |                     }
1196 |                     // If audio not done yet, skip the video — audio was the response
1197 |                   }
1198 |                 })
1199 |                 .catch(function(){});
1200 |               if(pollAttempts>=maxPollAttempts){
1201 |                 clearInterval(pollVideo);
1202 |                 setBusy(false);mic.disabled=false;
1203 |               }
1204 |             },2000);
1205 |           }
1206 |         });
1207 |       });
1208 |     });
1209 |   })
1210 |   .then(function(){
1211 |     setTimeout(pulseMic,500);
1212 |   })
1213 |   .catch(function(e){
1214 |     console.error('process error:',e);
1215 |     if(e&&(e.message||'').indexOf('timeout')>=0){
1216 |       setStat('','#334',false);
1217 |     } else if(e&&e.message&&e.message.indexOf('HTTP')>=0){
1218 |       setStat('Oracle error — try again.','#ff3b5f',false);
1219 |     }
1220 |   })
1221 |   .finally(function(){
1222 |     setBusy(false);hideTX();
1223 |     setOracleState('LISTENING');
1224 |   });
1225 | }
1226 | 
1227 | function blobURL(b){
1228 |   if(objURL)try{URL.revokeObjectURL(objURL);}catch(e){}
1229 |   objURL=URL.createObjectURL(b);
1230 |   return objURL;
1231 | }
1232 | 
1233 | /* ── PLAY VIDEO ── */
1234 | function playVid(url){
1235 |   return new Promise(function(res){
1236 |     setOracleState('RESPONDING');
1237 |     vid.loop=false;
1238 |     vid.src=url;
1239 |     vid.style.opacity='1';
1240 |     if(window._matrixHide) window._matrixHide();
1241 |     var _safetyTimer = setTimeout(function(){
1242 |       if(busy){
1243 |         console.warn('[Oracle] Safety timeout — forcing mic unlock after 60s');
1244 |         setBusy(false);
1245 |         setOracleState('LISTENING');
1246 |       }
1247 |     }, 60000);
1248 |     try{if(window.parent!==window) window.parent.postMessage({type:'oracle:speaking'},'*');}catch(e){}
1249 |     vid.onended=function(){
1250 |       clearTimeout(_safetyTimer);
1251 |       vid.src='';
1252 |       /* Keep avatar visible: video-wrap has background-image of oracle_avatar.png */
1253 |       vid.style.opacity='0';
1254 |       if(window._matrixShow) window._matrixShow();
1255 |       hideSub();
1256 |       setBusy(false);
1257 |       setOracleState('LISTENING');
1258 |       res();
1259 |       try{if(window.parent!==window) window.parent.postMessage({type:'oracle:idle'},'*');}catch(e){}
1260 |     };
1261 |     vid.onerror=function(){
1262 |       clearTimeout(_safetyTimer);
1263 |       vid.style.opacity='0';
1264 |       setBusy(false);
1265 |       setOracleState('LISTENING');
1266 |       setStat('Video error','#ff3b5f',false);res();
1267 |     };
1268 |     vid.muted=true;
1269 |     vid.volume=1.0;
1270 |     var unmuted=false;
1271 |     function tryUnmute(){
1272 |       if(unmuted)return; unmuted=true;
1273 |       vid.muted=false;
1274 |       vid.volume=1.0;
1275 |     }
1276 |     vid.addEventListener('canplay',function oncp(){
1277 |       vid.removeEventListener('canplay',oncp);
1278 |       setStat('Speaking','#6cff9f',false);
1279 |       if(!window._chatAudioPlaying){
1280 |         tryUnmute();
1281 |       }
1282 |     },{once:true});
1283 |     var p=vid.play();
1284 |     if(p){
1285 |       p.then(function(){}).catch(function(){
1286 |         setStat('Tap to play','#f4c46f',false);
1287 |         vid.addEventListener('click',function(){vid.muted=false;vid.play();},{once:true});
1288 |       });
1289 |     }
1290 |   });
1291 | }
1292 | 
1293 | /* ── SPEECH RECOGNITION ── */
1294 | function initSR(){
1295 |   var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
1296 |   if(!SR){micHint.textContent='no speech api';return;}
1297 |   recognition=new SR();
1298 |   recognition.continuous=false;recognition.interimResults=true;recognition.lang='en-US';
1299 |   recognition.onresult=function(e){
1300 |     var fin='',int='';
1301 |     for(var i=0;i<e.results.length;i++){
1302 |       if(e.results[i].isFinal)fin+=e.results[i][0].transcript;
1303 |       else int+=e.results[i][0].transcript;
1304 |     }
1305 |     showTX(fin||int);if(fin)pending=fin;
1306 |   };
1307 |   recognition.onend=function(){
1308 |     if(isRec){setRec(false);if(pending.trim())process(pending);pending='';}
1309 |   };
1310 |   recognition.onerror=function(e){console.warn(e.error);setRec(false);};
1311 | }
1312 | 
1313 | function toggleMic(){if(busy)return;isRec?stopRec():startRec();}
1314 | function startRec(){
1315 |   if(!recognition){setStat('No speech API','#ff3b5f',false);return;}
1316 |   pending='';isRec=true;setRec(true);setStat('\ud83c\udf99 Listening...','#66d9ff',false);
1317 |   try{recognition.start();}catch(e){console.warn(e);}
1318 | }
1319 | function stopRec(){isRec=false;setRec(false);if(recognition)try{recognition.stop();}catch(e){}}
1320 | function setRec(on){
1321 |   mic.classList.toggle('rec',on);
1322 |   iMic.style.display=on?'none':'block';
1323 |   iStop.style.display=on?'block':'none';
1324 |   micHint.textContent=on?'tap to send':'tap to speak';
1325 | }
1326 | 
1327 | /* ── HELPERS ── */
1328 | function setStat(t,c,sp){statEl.textContent=t;statEl.style.color=c||'#334';spinEl.style.display=sp?'block':'none';spinEl.style.color=c||'#334';}
1329 | function setBusy(b){busy=b;if(b){mic.disabled=true;if(isRec)stopRec();}}
1330 | function showSub(t){sub.textContent=t;sub.classList.add('on');}
1331 | function hideSub(){sub.classList.remove('on');}
1332 | function showTX(t){txEl.textContent=t;txEl.classList.add('on');}
1333 | function hideTX(){txEl.classList.remove('on');}
1334 | function showCards(){cards.classList.add('on');}
1335 | function hideCards(){cards.classList.remove('on');}
1336 | /* ── GEMINI VISION ── */
1337 | var _visionSessionId = null;
1338 | 
1339 | function updateCameraButtonState() {
1340 |   var lbl = document.getElementById('cam-btn-label');
1341 |   if (!lbl) return;
1342 |   lbl.textContent = _visionSessionId
1343 |     ? 'FOLLOW-UP PHOTO'
1344 |     : 'ANALYZE HARDWARE';
1345 | }
1346 | 
1347 | function triggerCamera(){
1348 |   document.getElementById("cam-input").click();
1349 | }
1350 | 
1351 | function handleVisionUpload(evt){
1352 |   var file = evt.target.files[0];
1353 |   if(!file) return;
1354 |   if (busy) {
1355 |     showVisionStatus('Oracle is speaking — wait a moment');
1356 |     setTimeout(hideVisionStatus, 2000);
1357 |     evt.target.value = "";
1358 |     return;
1359 |   }
1360 |   evt.target.value = "";
1361 |   
1362 |   var reader = new FileReader();
1363 |   reader.onload = function(e){
1364 |     var b64 = e.target.result.split(",")[1];
1365 |     var mime = file.type || "image/jpeg";
1366 |     sendVisionImage(b64, mime);
1367 |   };
1368 |   reader.readAsDataURL(file);
1369 | }
1370 | 
1371 | var SEED_RECOVERY_STEPS = [
1372 |   {
1373 |     label: 'STEP 1 OF 3 — STOP IMMEDIATELY',
1374 |     text: 'Do NOT send any Bitcoin from this wallet until you have moved your funds. Anyone who saw this seed phrase can access your Bitcoin right now.',
1375 |     speak: 'Stop. Do not send any Bitcoin from this wallet. Anyone who saw this seed phrase can steal your funds right now.'
1376 |   },
1377 |   {
1378 |     label: 'STEP 2 OF 3 — MOVE YOUR FUNDS',
1379 |     text: 'On a different device, create a brand new wallet. Generate a NEW seed phrase — write it down on paper only, never photograph it. Transfer ALL funds to the new wallet address immediately.',
1380 |     speak: 'On a different device, create a new wallet with a new seed phrase. Write it on paper only. Transfer all your funds to the new wallet immediately.'
1381 |   },
1382 |   {
1383 |     label: 'STEP 3 OF 3 — SECURE THE NEW WALLET',
1384 |     text: 'Once funds are transferred, the old wallet is abandoned. Store your new seed phrase in a metal backup, split across two secure locations. Never store seed phrases digitally.',
1385 |     speak: 'Once funds are moved, abandon the old wallet. Store your new seed phrase in metal, split across two secure locations. Never store seed phrases digitally.'
1386 |   }
1387 | ];
1388 | 
1389 | function showSecurityAlert(msg, onDismiss) {
1390 |   var overlay = document.getElementById('vision-security-overlay');
1391 |   var msgEl = document.getElementById('vision-security-msg');
1392 |   var dismissBtn = document.getElementById('vision-security-dismiss');
1393 |   var recoveryPanel = document.getElementById('vision-recovery-panel');
1394 |   if (!overlay || !msgEl) return;
1395 | 
1396 |   msgEl.textContent = msg;
1397 |   overlay.style.display = 'flex';
1398 | 
1399 |   // Speak the initial alert urgently
1400 |   function speakText(text) {
1401 |     fetchTO(A+'/oracle/voice', {
1402 |       method: 'POST',
1403 |       headers: {'Content-Type': 'application/json'},
1404 |       body: JSON.stringify({text: text})
1405 |     }, 20000).then(function(r) {
1406 |       if (!r.ok) return;
1407 |       return r.blob();
1408 |     }).then(function(blob) {
1409 |       if (!blob) return;
1410 |       var alertAudio = new Audio(URL.createObjectURL(blob));
1411 |       alertAudio.volume = 1.0;
1412 |       alertAudio.play().catch(function(){});
1413 |     }).catch(function(){});
1414 |   }
1415 | 
1416 |   speakText('SECURITY ALERT. ' + msg +
1417 |     ' Your seed phrase may be compromised. Do not send Bitcoin until you hear the recovery steps.');
1418 | 
1419 |   // Dismiss transitions to recovery steps
1420 |   dismissBtn.onclick = function() {
1421 |     dismissBtn.style.display = 'none';
1422 |     msgEl.style.fontSize = '0.9rem';
1423 |     msgEl.style.opacity = '0.7';
1424 |     recoveryPanel.style.display = 'block';
1425 |     _showRecoveryStep(0, speakText);
1426 |   };
1427 | }
1428 | 
1429 | function _showRecoveryStep(idx, speakFn) {
1430 |   var steps = SEED_RECOVERY_STEPS;
1431 |   var stepLabel = document.getElementById('vision-recovery-step-label');
1432 |   var stepText = document.getElementById('vision-recovery-step-text');
1433 |   var nextBtn = document.getElementById('vision-recovery-next');
1434 |   var helpBtn = document.getElementById('vision-recovery-help');
1435 |   var closeBtn = document.getElementById('vision-recovery-close');
1436 | 
1437 |   if (!stepLabel || !stepText) return;
1438 | 
1439 |   stepLabel.textContent = steps[idx].label;
1440 |   stepText.textContent = steps[idx].text;
1441 |   speakFn(steps[idx].speak);
1442 | 
1443 |   var isLast = (idx === steps.length - 1);
1444 |   nextBtn.style.display = isLast ? 'none' : 'block';
1445 |   helpBtn.style.display = isLast ? 'block' : 'none';
1446 |   closeBtn.style.display = isLast ? 'block' : 'none';
1447 | 
1448 |   nextBtn.onclick = function() {
1449 |     if (idx < steps.length - 1) _showRecoveryStep(idx + 1, speakFn);
1450 |   };
1451 | 
1452 |   helpBtn.onclick = function() {
1453 |     // Close overlay and trigger Oracle to help set up new wallet
1454 |     var overlay = document.getElementById('vision-security-overlay');
1455 |     if (overlay) overlay.style.display = 'none';
1456 |     // Inject a vision guidance request for new wallet setup
1457 |     sendVisionImage(null, null, 'help me set up a new hardware wallet safely');
1458 |   };
1459 | 
1460 |   closeBtn.onclick = function() {
1461 |     var overlay = document.getElementById('vision-security-overlay');
1462 |     if (overlay) overlay.style.display = 'none';
1463 |   };
1464 | }
1465 | 
1466 | function _speakVisionGuidance(d) {
1467 |   var raw = d.guidance_text || d.guidance || d.analysis || d.response
1468 |     || "I can see your hardware. Let me walk you through the next step.";
1469 |   // Hard 30-word cap for TTS speed
1470 |   var words = raw.split(/\s+/);
1471 |   var guideText = words.length > 30 ? words.slice(0,30).join(" ") : raw;
1472 | 
1473 |   // Urgent spoken prefix for transaction verdicts
1474 |   if (d.verdict === 'DO NOT SIGN') {
1475 |     guideText = 'WARNING. DO NOT SIGN THIS TRANSACTION. ' + guideText;
1476 |   } else if (d.verdict === 'REVIEW CAREFULLY' && d.red_flags && d.red_flags.length) {
1477 |     guideText = 'REVIEW CAREFULLY. ' + guideText;
1478 |   }
1479 | 
1480 |   showVisionStatus("Speaking...");
1481 |   showSub(guideText);
1482 | 
1483 |   // Transaction review verdict card
1484 |   if (d.category === 'transaction' && d.verdict) {
1485 |     var verdictColor = d.verdict === 'SAFE TO SIGN'
1486 |       ? '#00d4aa'
1487 |       : d.verdict === 'DO NOT SIGN'
1488 |       ? '#ff3b5f'
1489 |       : '#f5a623';
1490 | 
1491 |     var verdictHtml = '<div style="background:rgba(0,0,0,.4);' +
1492 |       'border:2px solid ' + verdictColor + ';border-radius:8px;' +
1493 |       'padding:12px 16px;margin-bottom:12px;">' +
1494 |       '<div style="font-family:monospace;font-size:10px;' +
1495 |       'letter-spacing:.12em;color:' + verdictColor + ';' +
1496 |       'text-transform:uppercase;margin-bottom:6px;">' +
1497 |       '\u26A1 TRANSACTION ANALYSIS</div>' +
1498 |       '<div style="font-size:1.1rem;font-weight:800;' +
1499 |       'color:' + verdictColor + ';margin-bottom:8px;">' +
1500 |       d.verdict + '</div>';
1501 | 
1502 |     if (d.recipient_address) {
1503 |       verdictHtml += '<div style="font-family:monospace;font-size:10px;' +
1504 |         'color:rgba(255,255,255,.5);word-break:break-all;">' +
1505 |         'TO: ' + d.recipient_address + '</div>';
1506 |     }
1507 |     if (d.amount_btc) {
1508 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1509 |         'color:rgba(255,255,255,.7);margin-top:4px;">' +
1510 |         'AMOUNT: ' + d.amount_btc + ' BTC</div>';
1511 |     }
1512 |     if (d.fee_sats) {
1513 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1514 |         'color:rgba(255,255,255,.6);">' +
1515 |         'FEE: ' + d.fee_sats + ' sats</div>';
1516 |     }
1517 |     if (d.red_flags && d.red_flags.length) {
1518 |       verdictHtml += '<div style="margin-top:8px;">';
1519 |       d.red_flags.forEach(function(flag) {
1520 |         verdictHtml += '<div style="font-family:monospace;font-size:9px;' +
1521 |           'color:#f5a623;letter-spacing:.06em;">\u26A0 ' + flag + '</div>';
1522 |       });
1523 |       verdictHtml += '</div>';
1524 |     }
1525 |     verdictHtml += '</div>';
1526 | 
1527 |     var vsEl = document.getElementById('vision-status');
1528 |     if (vsEl) {
1529 |       vsEl.innerHTML = verdictHtml + (vsEl.innerHTML || '');
1530 |       vsEl.classList.add('on');
1531 |     }
1532 |   }
1533 | 
1534 |   // Show steps in vision-status area if present
1535 |   if(d.steps && d.steps.length){
1536 |     var stepsHtml = d.steps.map(function(s,i){ return (i+1)+". "+s; }).join("<br>");
1537 |     var el=document.getElementById("vision-status");
1538 |     el.innerHTML = (d.device_name && d.device_name!=="unknown" ? "<b>"+d.device_name+"</b><br>" : "") + stepsHtml;
1539 |     el.classList.add("on");
1540 |   }
1541 | 
1542 |   // Add to session transcript
1543 |   _addVisionEntry(d.device_name, d.steps || [], guideText);
1544 | 
1545 |   // VOICE-ONLY: /oracle/voice is ElevenLabs-only, no GPU, ~400ms vs 14s
1546 |   fetchTO(A+"/oracle/voice",{method:"POST",
1547 |     headers:{"Content-Type":"application/json"},
1548 |     body:JSON.stringify({text:guideText})},15000)
1549 |   .then(function(ar){
1550 |     if(!ar.ok) throw new Error("voice "+ar.status);
1551 |     return ar.blob();
1552 |   })
1553 |   .then(function(audioBlob){
1554 |     hideVisionStatus();
1555 |     var audioURL = URL.createObjectURL(audioBlob);
1556 |     var audio;
1557 |     if(window._audioUnlocked){
1558 |       audio=window._audioUnlocked;
1559 |       window._audioUnlocked=null;
1560 |       audio.src=audioURL;
1561 |       audio.volume=1.0;
1562 |       audio.muted=false;
1563 |     } else {
1564 |       audio = new Audio(audioURL);
1565 |       audio.volume = 1.0;
1566 |     }
1567 |     return new Promise(function(res){
1568 |       audio.onended = function(){
1569 |         URL.revokeObjectURL(audioURL);
1570 |         setStat("Ready","#334",false);
1571 |         hideSub();
1572 |         if(d.device_name){
1573 |           setTimeout(function(){ showVisionSponsor(d.device_name); },800);
1574 |         }
1575 |         // Prompt for follow-up photo if session is active
1576 |         if (_visionSessionId) {
1577 |           showVisionStatus('Tap camera to show next screen \u2192');
1578 |           setTimeout(function() {
1579 |             hideVisionStatus();
1580 |           }, 4000);
1581 |         }
1582 |         res();
1583 |       };
1584 |       audio.onerror = function(){ URL.revokeObjectURL(audioURL); res(); };
1585 |       var vp = audio.play();
1586 |       if(vp !== undefined){
1587 |         vp.then(function(){ setStat("Speaking","#6cff9f",false); }).catch(function(){ res(); });
1588 |       }
1589 |     });
1590 |   })
1591 |   .catch(function(){
1592 |     showVisionStatus("Ready");
1593 |     setBusy(false);
1594 |     mic.disabled = false;
1595 |   });
1596 | }
1597 | 
1598 | function sendVisionImage(b64, mimeType, textOverride){
1599 |   // Text-only mode: no image, just a guided question
1600 |   if (!b64 && textOverride) {
1601 |     setBusy(true);
1602 |     showVisionStatus('Preparing guidance...');
1603 |     _speakVisionGuidance({
1604 |       guidance_text: 'I can guide you through setting up a new hardware wallet securely. First, choose a wallet: Coldcard for maximum security, Trezor for ease of use, or SeedSigner for open-source air-gapped signing. Which would you like help with?',
1605 |       device_name: 'new_wallet_setup',
1606 |       steps: [
1607 |         'Choose your hardware wallet: Coldcard, Trezor, or SeedSigner',
1608 |         'Purchase only from official manufacturer websites — never third party',
1609 |         'On first boot, generate a new seed phrase on the device itself',
1610 |         'Write seed phrase on paper only — never photograph or type it',
1611 |         'Test recovery before sending any funds'
1612 |       ]
1613 |     });
1614 |     setBusy(false);
1615 |     return;
1616 |   }
1617 | 
1618 |   setBusy(true);
1619 |   showVisionStatus("Analyzing your screen...");
1620 | 
1621 |   var endpoint = _visionSessionId ? A+"/vision/guide" : A+"/vision/analyze";
1622 |   var body = {image_base64:b64, mime_type:mimeType,
1623 |     context:"User needs Bitcoin hardware setup guidance"};
1624 |   if(_visionSessionId){
1625 |     body.session_id = _visionSessionId;
1626 |     body.question = "What step am I at and what should I do next?";
1627 |     body.last_context = _visionTranscript.length > 0
1628 |       ? _visionTranscript[_visionTranscript.length - 1].steps.join('; ')
1629 |       : '';
1630 |   }
1631 | 
1632 |   fetchTO(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},
1633 |     body:JSON.stringify(body)},20000)
1634 |   .then(function(r){
1635 |     if(!r.ok) throw new Error("vision "+r.status);
1636 |     return r.json();
1637 |   })
1638 |   .then(function(d){
1639 |     _visionSessionId = d.session_id || _visionSessionId;
1640 |     updateCameraButtonState();
1641 | 
1642 |     // Security alert takes absolute priority — recovery flow keeps overlay open
1643 |     if (d.security_alert) {
1644 |       showSecurityAlert(d.security_alert);
1645 |       return;
1646 |     }
1647 |     _speakVisionGuidance(d);
1648 |   })
1649 |   .catch(function(e){
1650 |     console.error("Vision error:", e);
1651 |     showVisionStatus("Vision error — try again.");
1652 |     setTimeout(hideVisionStatus, 3000);
1653 |   })
1654 |   .finally(function(){ setBusy(false); mic.disabled=false; });
1655 | }
1656 | 
1657 | function showVisionStatus(msg){ 
1658 |   var el=document.getElementById("vision-status");
1659 |   el.textContent=msg; el.classList.add("on");
1660 | }
1661 | function hideVisionStatus(){
1662 |   var el=document.getElementById("vision-status");
1663 |   el.classList.remove("on");
1664 | }
1665 | 
1666 | /* ── VISION SESSION TRANSCRIPT ── */
1667 | var _visionTranscript = [];
1668 | 
1669 | function _addVisionEntry(deviceName, steps, guidanceText) {
1670 |   var panel = document.getElementById('vision-transcript-panel');
1671 |   var entries = document.getElementById('vision-transcript-entries');
1672 |   if (!entries) return;
1673 | 
1674 |   if (panel && _visionTranscript.length === 0) {
1675 |     panel.style.display = 'block';
1676 |   }
1677 | 
1678 |   var entry = {
1679 |     device: deviceName || 'Unknown Device',
1680 |     steps: steps || [],
1681 |     guidance: guidanceText || '',
1682 |     time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})
1683 |   };
1684 |   _visionTranscript.push(entry);
1685 | 
1686 |   var el = document.createElement('div');
1687 |   el.className = 'vision-entry';
1688 | 
1689 |   var deviceEl = document.createElement('div');
1690 |   deviceEl.className = 'vision-entry-device';
1691 |   deviceEl.textContent = entry.device.toUpperCase();
1692 |   el.appendChild(deviceEl);
1693 | 
1694 |   if (entry.steps.length) {
1695 |     entry.steps.forEach(function(s, i) {
1696 |       var stepEl = document.createElement('div');
1697 |       stepEl.className = 'vision-entry-step';
1698 |       stepEl.textContent = (i+1) + '. ' + s;
1699 |       el.appendChild(stepEl);
1700 |     });
1701 |   } else if (entry.guidance) {
1702 |     var guidEl = document.createElement('div');
1703 |     guidEl.className = 'vision-entry-step';
1704 |     guidEl.textContent = entry.guidance.substring(0, 120) +
1705 |       (entry.guidance.length > 120 ? '…' : '');
1706 |     el.appendChild(guidEl);
1707 |   }
1708 | 
1709 |   var timeEl = document.createElement('div');
1710 |   timeEl.className = 'vision-entry-time';
1711 |   timeEl.textContent = entry.time + ' — tap to re-read';
1712 |   el.appendChild(timeEl);
1713 | 
1714 |   el.onclick = function() {
1715 |     var text = entry.steps.length
1716 |       ? entry.device + '. ' + entry.steps.join('. ')
1717 |       : entry.guidance;
1718 |     fetchTO(A+'/oracle/voice', {
1719 |       method: 'POST',
1720 |       headers: {'Content-Type': 'application/json'},
1721 |       body: JSON.stringify({text: text.substring(0, 200)})
1722 |     }, 20000).then(function(r) {
1723 |       return r.ok ? r.blob() : null;
1724 |     }).then(function(blob) {
1725 |       if (!blob) return;
1726 |       var a = new Audio(URL.createObjectURL(blob));
1727 |       a.volume = 1.0;
1728 |       a.play().catch(function(){});
1729 |     }).catch(function(){});
1730 |   };
1731 | 
1732 |   entries.appendChild(el);
1733 |   entries.scrollTop = entries.scrollHeight;
1734 | }
1735 | 
1736 | document.addEventListener('DOMContentLoaded', function() {
1737 |   var clearBtn = document.getElementById('vision-transcript-clear');
1738 |   if (clearBtn) {
1739 |     clearBtn.onclick = function() {
1740 |       _visionTranscript = [];
1741 |       var entries = document.getElementById('vision-transcript-entries');
1742 |       if (entries) entries.innerHTML = '';
1743 |       var panel = document.getElementById('vision-transcript-panel');
1744 |       if (panel) panel.style.display = 'none';
1745 |       _visionSessionId = null;
1746 |       updateCameraButtonState();
1747 |     };
1748 |   }
1749 | });
1750 | 
1751 | /* ── MINIMIZE / EXIT / FLOAT ── */
1752 | var _oracleMinimized = false;
1753 | 
1754 | function minimizeOracle(){
1755 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
1756 |   if(inIframe){
1757 |     try{ window.parent.postMessage({type:'oracle:minimize'},'*'); }catch(e){}
1758 |     return;
1759 |   }
1760 |   // Standalone: shrink to float bubble
1761 |   _oracleMinimized = true;
1762 |   document.getElementById("oracle-root").style.display = "none";
1763 |   var f = document.getElementById("oracle-float");
1764 |   if(f){ f.style.display = "flex"; if(busy) f.classList.add("speaking"); }
1765 | }
1766 | 
1767 | function restoreOracle(){
1768 |   _oracleMinimized = false;
1769 |   document.getElementById("oracle-float").style.display = "none";
1770 |   document.getElementById("oracle-root").style.display = "flex";
1771 |   document.getElementById("oracle-float").classList.remove("speaking");
1772 | }
1773 | 
1774 | function exitOracle(){
1775 |   // If running inside widget iframe — tell parent to close
1776 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
1777 |   if(inIframe){
1778 |     try{ window.parent.postMessage({type:'oracle:close'},'*'); }catch(e){}
1779 |     return;
1780 |   }
1781 |   // Standalone page — return to gate screen
1782 |   _oracleMinimized = false;
1783 |   // Stop any playing audio/video
1784 |   vid.pause(); vid.src="";
1785 |   if(isRec) stopRec();
1786 |   // Reset session on server
1787 |   fetch(A+"/oracle/session/reset",{method:"POST",
1788 |     headers:{"Content-Type":"application/json"},
1789 |     body:JSON.stringify({session_id:SESSION_ID})}).catch(function(){});
1790 |   // Hide everything
1791 |   document.getElementById("oracle-float").style.display = "none";
1792 |   document.getElementById("live-stage").style.display = "none";
1793 |   document.getElementById("oracle-root").style.display = "flex";
1794 |   // Show gate again
1795 |   var g = document.getElementById("gate");
1796 |   g.style.display = "flex";
1797 |   g.style.opacity = "1";
1798 |   g.style.transition = "opacity .3s";
1799 |   // Reset state
1800 |   busy = false; window._briefFetched = false;
1801 |   setStat("Ready","#334",false);
1802 |   hideSub(); hideTranscript && hideTX();
1803 | }
1804 | 
1805 | // Keep float speaking indicator in sync
1806 | var _origSetStat = setStat;
1807 | setStat = function(msg, color, spin){
1808 |   _origSetStat(msg, color, spin);
1809 |   var f = document.getElementById("oracle-float");
1810 |   if(f && _oracleMinimized){
1811 |     if(msg === "Speaking") f.classList.add("speaking");
1812 |     else f.classList.remove("speaking");
1813 |   }
1814 | };
1815 | 
1816 | /* ── ORACLE IDLE MATRIX ANIMATION ── */
1817 | (function(){
1818 |   var canvas = document.getElementById('oracle-matrix');
1819 |   if (!canvas) return;
1820 |   var ctx = canvas.getContext('2d');
1821 |   var chars = '01₿⚡∆Ω█▓░10₿Ξ∞◆'.split('');
1822 |   var cols, drops;
1823 | 
1824 |   function resize() {
1825 |     canvas.width = canvas.offsetWidth;
1826 |     canvas.height = canvas.offsetHeight;
1827 |     cols = Math.floor(canvas.width / 14);
1828 |     drops = Array(cols).fill(1);
1829 |   }
1830 |   resize();
1831 |   window.addEventListener('resize', resize);
1832 | 
1833 |   function draw() {
1834 |     ctx.fillStyle = 'rgba(4,5,8,0.05)';
1835 |     ctx.fillRect(0, 0, canvas.width, canvas.height);
1836 |     ctx.font = '11px monospace';
1837 |     for (var i = 0; i < drops.length; i++) {
1838 |       var char = chars[Math.floor(Math.random() * chars.length)];
1839 |       var alpha = Math.random() * 0.4 + 0.05;
1840 |       var cx = canvas.width / 2;
1841 |       var dist = Math.abs(i * 14 - cx) / cx;
1842 |       var r = Math.floor(180 + (1 - dist) * 75);
1843 |       var g = Math.floor(20 + (1 - dist) * 30);
1844 |       var b = Math.floor(40 + (1 - dist) * 20);
1845 |       ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
1846 |       ctx.fillText(char, i * 14, drops[i] * 14);
1847 |       if (drops[i] * 14 > canvas.height && Math.random() > 0.975) drops[i] = 0;
1848 |       drops[i]++;
1849 |     }
1850 |   }
1851 | 
1852 |   var _matrixInterval = setInterval(draw, 50);
1853 | 
1854 |   window._matrixHide = function() {
1855 |     canvas.style.opacity = '0';
1856 |   };
1857 |   window._matrixShow = function() {
1858 |     canvas.style.opacity = '1';
1859 |   };
1860 | })();
1861 | 
1862 | /* ── CYBERPUNK MATRIX BACKGROUND ── */
1863 | (function(){
1864 |   var cvs=document.getElementById('bg-canvas');
1865 |   if(!cvs)return;
1866 |   var ctx=cvs.getContext('2d');
1867 |   var W,H,cols,drops,hexFrags=[];
1868 |   var matrixChars='0123456789ABCDEFabcdef₿⚡∆Ω█▓░▒╔╗╚╝║═';
1869 |   var fontSize=14;
1870 |   var scanY=-2,scanDir=1,scanTimer=0,scanInterval=15000;
1871 | 
1872 |   function resize(){
1873 |     W=cvs.width=cvs.offsetWidth;
1874 |     H=cvs.height=cvs.offsetHeight;
1875 |     cols=Math.floor(W/fontSize);
1876 |     drops=new Array(cols);
1877 |     for(var i=0;i<cols;i++) drops[i]=Math.random()*(-H/fontSize);
1878 |   }
1879 |   resize();
1880 |   window.addEventListener('resize',resize);
1881 | 
1882 |   // Hex fragments: random hex strings that fade in/out
1883 |   function spawnHex(){
1884 |     if(hexFrags.length>6) return;
1885 |     hexFrags.push({
1886 |       x:Math.random()*W,
1887 |       y:Math.random()*H,
1888 |       text:'0x'+Math.random().toString(16).substr(2,6).toUpperCase(),
1889 |       alpha:0,phase:0, // 0=fade in, 1=hold, 2=fade out
1890 |       speed:0.003+Math.random()*0.005,
1891 |       holdTime:2000+Math.random()*3000,
1892 |       holdStart:0
1893 |     });
1894 |   }
1895 | 
1896 |   var lastTime=0;
1897 |   function frame(ts){
1898 |     requestAnimationFrame(frame);
1899 |     if(!lastTime) lastTime=ts;
1900 |     var dt=ts-lastTime;
1901 |     lastTime=ts;
1902 | 
1903 |     ctx.clearRect(0,0,W,H);
1904 | 
1905 |     // 1. Falling matrix characters (sparse)
1906 |     ctx.font=fontSize+'px JetBrains Mono,monospace';
1907 |     for(var i=0;i<cols;i++){
1908 |       if(Math.random()>0.06) { // sparse: only 6% of columns draw per frame
1909 |         if(drops[i]>0){
1910 |           ctx.fillStyle='rgba(255,59,95,0.15)';
1911 |           var ch=matrixChars[Math.floor(Math.random()*matrixChars.length)];
1912 |           ctx.fillText(ch,i*fontSize,drops[i]*fontSize);
1913 |         }
1914 |       }
1915 |       drops[i]+=0.3;
1916 |       if(drops[i]*fontSize>H && Math.random()>0.98){
1917 |         drops[i]=0;
1918 |       }
1919 |     }
1920 | 
1921 |     // 2. Scan line sweep every 15s
1922 |     scanTimer+=dt;
1923 |     if(scanTimer>=scanInterval){
1924 |       scanTimer=0;
1925 |       scanY=-2;
1926 |       scanDir=1;
1927 |     }
1928 |     if(scanY>=0 && scanY<=H){
1929 |       var grad=ctx.createLinearGradient(0,scanY-8,0,scanY+8);
1930 |       grad.addColorStop(0,'rgba(255,59,95,0)');
1931 |       grad.addColorStop(0.5,'rgba(255,59,95,0.12)');
1932 |       grad.addColorStop(1,'rgba(255,59,95,0)');
1933 |       ctx.fillStyle=grad;
1934 |       ctx.fillRect(0,scanY-8,W,16);
1935 |     }
1936 |     if(scanY>=-2 && scanY<=H+10) scanY+=2;
1937 | 
1938 |     // 3. Hex fragments fade in/out
1939 |     if(Math.random()<0.008) spawnHex();
1940 |     for(var h=hexFrags.length-1;h>=0;h--){
1941 |       var frag=hexFrags[h];
1942 |       if(frag.phase===0){
1943 |         frag.alpha+=frag.speed*dt;
1944 |         if(frag.alpha>=0.2){frag.alpha=0.2;frag.phase=1;frag.holdStart=ts;}
1945 |       } else if(frag.phase===1){
1946 |         if(ts-frag.holdStart>frag.holdTime) frag.phase=2;
1947 |       } else {
1948 |         frag.alpha-=frag.speed*dt;
1949 |         if(frag.alpha<=0){hexFrags.splice(h,1);continue;}
1950 |       }
1951 |       ctx.fillStyle='rgba(255,59,95,'+frag.alpha.toFixed(3)+')';
1952 |       ctx.font='10px JetBrains Mono,monospace';
1953 |       ctx.fillText(frag.text,frag.x,frag.y);
1954 |     }
1955 |   }
1956 |   requestAnimationFrame(frame);
1957 | })();
1958 | 
1959 | function fetchTO(url,opts,ms){
1960 |   var ctrl=new AbortController();
1961 |   var id=setTimeout(function(){ctrl.abort();},ms);
1962 |   var o=opts||{};o.signal=ctrl.signal;
1963 |   return fetch(url,o).finally(function(){clearTimeout(id);})
1964 |     .catch(function(e){if(e.name==='AbortError')throw new Error('timeout');throw e;});
1965 | }
1966 | /* ── ACTION CARDS ── */
1967 | function showActionCard(card){
1968 |   var el=document.getElementById('oracle-action-card');
1969 |   var catColor = card.category==='amazon' ? '#FF9900' : card.category==='internal' ? '#6cff9f' : '#ff3b5f';
1970 |   el.innerHTML='<a href="'+card.url+'" target="_blank" rel="noopener" onclick="trackCardClick(\''+card.id+'\')" style="display:block;background:#0d0f14;border:1px solid '+catColor+';border-radius:8px;padding:14px 16px;text-decoration:none;transition:border-color 0.2s;">'
1971 |     +'<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;letter-spacing:.1em;color:'+catColor+';margin-bottom:4px;">'+card.category.toUpperCase()+'</div>'
1972 |     +'<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:4px;">'+card.title+'</div>'
1973 |     +'<div style="font-size:11px;color:rgba(255,255,255,0.55);margin-bottom:10px;">'+card.description+'</div>'
1974 |     +'<div style="font-size:11px;font-weight:600;color:'+catColor+';">'+card.cta+'</div>'
1975 |     +'</a>';
1976 |   el.style.display='block';
1977 |   el.style.opacity='0';
1978 |   setTimeout(function(){el.style.transition='opacity 0.4s';el.style.opacity='1';},100);
1979 |   setTimeout(function(){hideActionCard();},45000);
1980 | }
1981 | function showVisionSponsor(deviceName){
1982 |   if(!deviceName || deviceName==='unknown') return;
1983 |   var key=deviceName.toLowerCase();
1984 |   var match=null;
1985 |   Object.keys(VISION_SPONSOR_MAP).forEach(function(k){
1986 |     if(!match && key.indexOf(k)>=0) match=VISION_SPONSOR_MAP[k];
1987 |   });
1988 |   if(!match) return;
1989 |   showActionCard(match);
1990 | }
1991 | function hideActionCard(){
1992 |   var el=document.getElementById('oracle-action-card');
1993 |   el.style.opacity='0';
1994 |   setTimeout(function(){el.style.display='none';el.innerHTML='';},400);
1995 | }
1996 | function trackCardClick(id){
1997 |   fetch('/api/telemetry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event:'oracle_card_clicked',properties:{card_id:id,fingerprint:window._visitorToken||'anon'}})}).catch(function(){});
1998 | }
1999 | 
2000 | /* ── MOBILE NAV BAR ── */
2001 | (function(){
2002 |   var isMobile=/iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
2003 |   if(isMobile){
2004 |     var nb=document.getElementById('mobile-nav-bar');
2005 |     if(nb) nb.style.display='flex';
2006 |   }
2007 | })();
2008 | 
2009 | window.addEventListener('beforeunload',function(){
2010 |   try{
2011 |     var xhr=new XMLHttpRequest();
2012 |     xhr.open('POST',A+'/oracle/session/save',false);
2013 |     xhr.setRequestHeader('Content-Type','application/json');
2014 |     xhr.send(JSON.stringify({session_id:SESSION_ID}));
2015 |   }catch(e){}
2016 | });
2017 | </script>
2018 | </body>
2019 | </html>
2020 | 
```

---

## YOUR REVIEW TASK — ORACLE PHASE 2: THINKING VIDEO + SSE PUSH (4 QUESTIONS)

You are auditing the Oracle avatar system for Phase 2 optimizations.
Phase 1 (commit 6898d3d7) fixed encoding preset and ffmpeg post-processing.
Phase 2 adds: (1) pre-rendered "thinking" video loop, (2) SSE push replacing 2s polling.
Target: 8-15s perceived latency → 4-8s perceived latency.

### Q1 — THINKING VIDEO ARCHITECTURE
Where in oracle_live.html does the video element exist?
When /oracle/chat returns a job_id, what does the frontend currently do while waiting?
What is the minimal change to make it play a looping "thinking" video immediately on chat submit,
then cross-fade to the real video when job completes?
The thinking video should be a 3-4s loop of the avatar with neutral animation
(head movement, blinks) — no mouth movement, no audio. Where should it be generated and stored?

### Q2 — SSE ARCHITECTURE FOR FLASK
Flask threaded mode with long-lived SSE connections: what is the correct implementation pattern?
generator + Response with mimetype text/event-stream? What are the thread-safety concerns
with per-job event queues? How does render_async (which runs in a thread pool) push events
to the SSE generator? Specifically: threading.Event per job, or a queue.Queue?

### Q3 — SSE PAYLOAD DESIGN
What events should the SSE stream send?
  - audio_ready: triggers client to fetch /oracle/job/<id>/audio
  - video_ready: triggers client to fetch /oracle/job/<id>
  - error: render failed
What should happen if client disconnects mid-stream?
How long should the SSE connection stay open?

### Q4 — FRONTEND CROSS-FADE
In oracle_live.html, how should the cross-fade from thinking video to real video work
without glitching? CSS opacity transition? Two overlapping video elements?
What is the minimum thinking video duration before real video arrives that makes the UX
feel responsive vs jarring?

### RESPONSE FORMAT
For each question (Q1-Q4):
- DETAILED ANALYSIS with line number citations from the provided files
- SPECIFIC RECOMMENDATION with expected latency savings (ms)
- IMPLEMENTATION RISK: LOW / MEDIUM / HIGH
- POTENTIAL GOTCHAS that could cause production issues

