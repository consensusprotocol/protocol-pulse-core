# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: oracle-speak-revert
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
### SECTION 1: CORRECTNESS

1. **Logic Errors and Variable Issues**: The code appears to handle the main user flow as intended, with functions for generating videos from text or audio, managing sessions, and handling TTS. However, there are potential issues:
   - The `_avatar_tts` function (lines 619-703) has a fallback mechanism that might not handle all edge cases, especially if both Kokoro and ElevenLabs fail.
   - The `generate_inline` function (lines 1541-1611) assumes that audio conversion will always succeed, which might not be the case.

2. **Race Conditions**: There are potential race conditions with shared resources like `_render_jobs` and `_stream_sessions` due to concurrent access without proper locking mechanisms in some cases.

3. **Edge Cases**: 
   - The handling of empty or invalid input is generally robust, but there are areas where exceptions might not be caught, such as in the `wav2lip_generate` function (lines 292-391).

### SECTION 2: LAW COMPLIANCE

- **COMPLIANT**: The code uses Python 3.12, Flask, and SQLite via SQLAlchemy, which aligns with the technology stack.
- **PARTIAL**: The requirement for every DB query on a sort/filter column to have an index is not verifiable from the provided code as there are no explicit DB queries shown.
- **VIOLATION**: The code does not explicitly handle the load for ~1000 concurrent users, especially in terms of rate limiting and resource management.

### SECTION 3: SECURITY

1. **SQL Injection**: Not applicable as there are no raw SQL queries shown.
2. **Authentication Bypasses**: The code does not seem to implement any authentication checks for sensitive operations.
3. **Rate Limiting**: There is no evidence of rate limiting, which could lead to API abuse.
4. **Secrets in Code**: API keys are fetched from the environment or `.env` files, which is good practice.
5. **Unvalidated Input**: The code does validate input to some extent, but there are areas where more rigorous checks could be beneficial, especially for file operations.

### SECTION 4: FRONTEND QUALITY

- The code primarily focuses on backend operations and does not provide details on UI layout or frontend logic.
- There is no indication of how the frontend handles loading, error, or empty states for async operations.

### SECTION 5: BACKEND QUALITY

1. **DB Operations**: Not applicable as there are no explicit DB operations shown.
2. **External API Calls**: Some API calls have timeouts, but there is no retry mechanism or graceful degradation strategy.
3. **Cron Jobs**: Not applicable as there are no cron jobs mentioned.
4. **Memory Leaks**: Potential memory leaks could occur with large objects like video frames if not properly managed.
5. **Logging**: Errors are logged with context, but more detailed logging could be beneficial for debugging.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

- **Missing Features**: The system lacks robust error handling and user authentication, which are critical for a professional-grade application.
- **Performance Optimization**: The code could benefit from more efficient resource management and concurrency handling to support high user loads.
- **User Experience**: A more comprehensive frontend with clear user feedback and error handling would enhance the overall experience.

### SECTION 7: SCORES (0-100 each)

- Backend logic:    70/100
- Frontend/UI:      50/100
- Error handling:   60/100
- Security:         55/100
- Performance:      65/100
- Law compliance:   70/100
- World-class gap:  60/100
- OVERALL:          62/100

### SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Implement rate limiting | [global] | Prevents API abuse and ensures fair resource allocation.
P1 HIGH     | Add authentication checks | [global] | Secures sensitive operations and data access.
P1 HIGH     | Improve error handling in TTS and video generation | [lines 619-703, 1541-1611] | Ensures robustness against failures.
P2 MEDIUM   | Enhance logging for better debugging | [global] | Provides more context for production issues.
P2 MEDIUM   | Optimize concurrency handling | [global] | Supports high user loads efficiently.
P3 LOW      | Refactor code for readability and maintainability | [global] | Improves long-term code quality.

### SECTION 9: THE ONE THING

Implement robust error handling and user authentication to enhance security and reliability.

### SECTION 10: FINAL VERDICT

The code is not ready for production due to critical gaps in security and error handling. Addressing these issues, along with implementing rate limiting and improving concurrency management, should be prioritized to ensure a stable and secure deployment.

## GROK — CYCLE 1 OUTPUT
### CODE REVIEW: ORACLE AVATAR SERVER v3 (oracle/avatar_server.py)

I have conducted a thorough forensic review of the provided code for the Oracle Avatar Server. Below are my findings across the specified sections, with detailed analysis, line references, and actionable recommendations. My goal is to ensure the highest quality for Protocol Pulse, a premium Bitcoin intelligence product.

---

### SECTION 1: CORRECTNESS

**Main User Flow Analysis (Text-to-Video Generation via /generate):**
1. **Flow Overview**: The user submits text or audio via `/generate` (line 833). The system processes text through TTS (Kokoro or ElevenLabs fallback, line 879-880), converts audio to 16kHz WAV (line 902-904), generates lip-synced frames using Wav2Lip (line 937), applies post-processing (sharpening, blinks, head movement, lines 942-955), encodes to MP4 (line 963), and returns the video (line 994).
2. **Logic Errors**:
   - **Silent Audio Duration Failure**: If `ffprobe` fails to determine audio duration (line 908-911), the code sets `audio_duration_sec = 0.0` and rejects the input (line 919-921). However, it doesn't log the specific error output from `ffprobe`, which could hinder debugging in production (line 916).
   - **Batch Size Assumption**: The adaptive batch size logic (line 338-339) assumes short audio (<60 mel frames) needs a smaller batch size, but this threshold isn't justified or configurable, risking VRAM issues on edge cases with slightly longer audio.
3. **Race Conditions**:
   - **Render Semaphore**: The `_render_semaphore` (line 211) limits concurrent Wav2Lip renders to 2, but there's no queue position tracking in `/generate` beyond a basic check (line 1563-1564 in `generate_inline`). Multiple requests can timeout (line 934) without clear feedback on queue status, leading to client retries and server load spikes.
   - **Avatar Face Cache**: The `_avatar_face_cache_lock` (line 85) protects face loading (line 132-164), but if multiple threads load the same non-default avatar simultaneously, they might redundantly perform CPU face detection (line 156) before the cache is populated, wasting resources.
4. **Edge Cases**:
   - **Empty Audio Input**: If audio input is empty or corrupt (line 313-314), the code raises a `ValueError`, but the error message is generic and not user-friendly when returned via API (line 1010).
   - **Long Audio Chunking**: While audio longer than 30s is rejected (line 923-929), there's no mechanism to split long text inputs into chunks before TTS, risking Kokoro/ElevenLabs timeouts or memory issues for very long texts (line 849 limit is 2000 chars, but not duration-based).
   - **GPU Timeout**: If the GPU lock timeout is hit (line 934), the response is a 503 with a generic "GPU busy" message, but no retry-after header includes queue depth or estimated wait time, leading to blind client retries.

**Summary**: The core flow works as intended for typical inputs, but silent failures (ffprobe), race conditions (semaphore without queue feedback), and unhandled edge cases (long text, empty audio specifics) risk production issues.

---

### SECTION 2: LAW COMPLIANCE

**Note**: The provided spec lists no specific "GOVERNING LAWS" under the section header. I will assume compliance requirements based on the TECHNOLOGY STACK and implied standards (e.g., performance, indexing, UI constraints). If specific laws were intended, they are missing from the input.

- **Law 1: Every DB query on a sort/filter column MUST have an index**  
  **COMPLIANT**: No direct DB queries are present in the code (SQLite via SQLAlchemy is mentioned in the stack but not used in this file). If ORM queries exist in imported modules (e.g., `oracle_memory`, line 1760), indexing cannot be verified here.
- **Law 2: All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas**  
  **COMPLIANT**: This file is backend-only (`avatar_server.py`). No UI code or references to Three.js, WebGL, or Canvas are present.
- **Law 3: ~1000 concurrent users at peak — every route must handle load**  
  **PARTIAL**: The code uses a semaphore to limit concurrent renders to 2 (line 211), with a timeout (line 934), which helps manage GPU load. However, there's no proper queuing system or load balancing for high concurrency (line 1563-1564 lacks queue depth feedback), risking 503 errors under peak load without graceful degradation or retry guidance.
- **Law 4: Jessica voice settings — stability=0.45, similarity_boost=0.75, style=0.20 (ElevenLabs)**  
  **COMPLIANT**: Explicitly set in line 724 for ElevenLabs TTS calls.

**Summary**: Compliance is mostly achieved where applicable, but concurrency handling for 1000 users is partial due to inadequate queue management and feedback mechanisms.

---

### SECTION 3: SECURITY

1. **SQL Injection**:  
   - No direct SQL queries or ORM usage in this file. If `oracle_memory` or other imports (line 1760) handle user input in DB operations, they are not visible here. **No issues found in scope.**
2. **Auth

## GEMINI — CYCLE 1 OUTPUT
Here is a forensic code review for the `oracle-speak-revert` feature.

### SECTION 1: CORRECTNESS

The code is complex and feature-rich, but several correctness issues exist, primarily related to state management and concurrency.

*   **MAJOR: In-memory state will be lost on restart.** All job, stream, and chunk session data is stored in global Python dictionaries (`_render_jobs`, `_stream_sessions`, `_chunk_sessions`, `oracle_dialogue_engine._sessions`). If the server restarts or crashes for any reason, all pending jobs, active user sessions, and conversation history will be permanently lost. A client polling for a job result at `/oracle/job/<job_id>` will receive a 404, creating a broken user experience. This violates the contract of an asynchronous job system and contradicts the spec's mention of a database layer.
*   **Race Condition in Garbage Collection:** The `_gc_worker` (line 222) can race with active worker threads. A worker thread might be writing to a file within a session directory (e.g., `_generate_chunk` on line 1225) at the exact moment the GC thread decides the session is stale and calls `shutil.rmtree` on that directory (lines 237, 251). This could lead to `FileNotFoundError` exceptions in the worker or corrupted files. The GC should only clean up directories for sessions that are in a terminal state (e.g., "complete", "error") and have passed their TTL, not just based on creation time.
*   **Bug in CORS Logic:** The CORS logic on line 185 uses `origin.startswith("http://localhost")`. This would incorrectly allow an origin like `http://localhost.malicious.com`. The check should be more specific, like `origin.startswith("http://localhost:")` or a regex match for `http://localhost(:\d+)?$`.
*   **Silent Failure in `_avatar_tts`:** The `ffmpeg` loudnorm process (lines 666-672) fails silently. If the command fails, it logs nothing and proceeds with the unnormalized audio. While this is a reasonable fallback, it hides potential configuration or data issues and could lead to inconsistent audio quality. The `subprocess.run` call should have `check=True` or the return code should be explicitly checked and logged as a warning.
*   **Racy Queue Position Check:** The code in `generate_inline` at line 1563 attempts to check the queue position. However, it reads `_render_semaphore._value` without holding a lock. This value could change immediately after being read, making the `queue_position` value unreliable and potentially misleading in logs or error messages.

### SECTION 2: LAW COMPLIANCE

The "GOVERNING LAWS" section of the specification was empty.

*   A specific "LAW" is mentioned in a comment: `LAW 3: Jessica voice settings — stability=0.45, similarity_boost=0.75, style=0.20`
    *   **STATUS: COMPLIANT**
    *   **Line 724:** The call to the ElevenLabs API correctly includes the specified `voice_settings`, fulfilling this requirement.

### SECTION 3: SECURITY

The code demonstrates good awareness of some security vectors but has a critical omission.

*   **CRITICAL: Missing Rate Limiting.** There are no rate limits on any of the expensive, GPU-intensive, or paid API endpoints (`/generate`, `/oracle/chat`, `/vision/analyze`). A single malicious user or a simple script could submit requests in a loop, monopolizing both GPUs and exhausting the API quotas/budgets for ElevenLabs, Anthropic, and Gemini. This is a denial-of-service and financial vulnerability.
*   **GOOD: Secrets Management.** API keys are correctly loaded from environment variables or a `.env` file (e.g., lines 708, 1207). There are no hardcoded secrets in the source code.
*   **GOOD: Path Traversal Prevention.** The `_load_avatar_face` function at lines 141-144 correctly uses `os.path.realpath` to validate that alternate avatar image paths are within the project directory, preventing path traversal attacks.
*   **GOOD: Shell Injection Prevention.** All calls to external commands like `ffmpeg` and `ffprobe` use `subprocess.run` with a list of arguments (e.g., line 500, 903). This correctly avoids passing user input through a shell, preventing command injection vulnerabilities.
*   **Minor: Information Disclosure in `/health`.** The `/health` endpoint (line 737) returns detailed information about the internal configuration, including VRAM stats, model names, and enabled features. While useful for debugging, this could provide attackers with information about the system architecture. Consider having a separate, more restricted `/status` endpoint for public consumption and a protected `/debug/health` endpoint for internal use.

### SECTION 4: FRONTEND QUALITY

The provided code is exclusively backend. A review of frontend quality is not possible.

### SECTION 5: BACKEND QUALITY

The backend is a sophisticated but brittle monolith.

*   **External API Calls:** API calls include timeouts (e.g., line 726), which is good. However, there is no retry logic for transient network errors or API-side 5xx errors. For a production service, a simpl

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — ORACLE-SPEAK-REVERT — CYCLE 1
Generated: 2026-03-24 14:50
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok | Consensus |
|------------------|--------|--------|------|-----------|
| Backend Logic    | ~65    | 70     | 68   | **68**    |
| Frontend/UI      | N/A    | 50     | N/A  | **50**    |
| Error Handling   | ~55    | 60     | 62   | **59**    |
| Security         | ~45    | 55     | 50   | **50**    |
| Performance      | ~55    | 65     | 60   | **60**    |
| Law Compliance   | ~70    | 70     | 72   | **71**    |
| World-Class Gap  | ~40    | 60     | 55   | **52**    |
| **OVERALL**      | ~55    | 62     | 60   | **59**    |

> Note: Gemini did not produce explicit numeric scores; estimates are derived from qualitative language ("brittle monolith", "impressive but…") calibrated against GPT-4o and Grok scoring distributions.

---

## UNANIMOUS FINDINGS
*(All 3 models flagged — implement unconditionally)*

### U1 — Missing Rate Limiting on All Endpoints
- **What**: No rate limiting exists on any endpoint. `/generate`, `/oracle/chat`, `/oracle/voice`, `/vision/analyze` are all unbounded.
- **File/Line**: `oracle/avatar_server.py` — all route definitions (lines ~833, ~1627, ~1747, ~1055)
- **Fix**: Implement `flask-limiter` with Redis backend. At minimum: `/generate` → 5 req/min/IP; `/oracle/chat` → 20 req/min/IP; `/vision/analyze` → 10 req/min/IP. Return `429` with `Retry-After` header.
- **Why unanimous**: GPU exhaustion, ElevenLabs/Anthropic/Gemini API budget drain, and DoS are all independently identified by every model as the single most exploitable gap.

### U2 — No Authentication on Sensitive/Expensive Routes
- **What**: Routes including `/reload-avatar`, `/generate`, `/oracle/chat`, and vision endpoints have zero access control.
- **File/Line**: `oracle/avatar_server.py` — lines ~1021, ~833, ~1747, ~1055
- **Fix**: Add API key header auth (`X-API-Key`) validated against a hashed environment secret at minimum. For `/reload-avatar` specifically, require admin-level auth. Use a decorator to keep it DRY.
- **Why unanimous**: All three models called out authentication absence, with Grok specifically noting `/reload-avatar` as a critical unprotected admin action.

### U3 — No Retry Logic on External API Calls
- **What**: ElevenLabs, Anthropic, Gemini calls have timeouts but no retry-with-backoff on transient failures (5xx, network blips).
- **File/Line**: `oracle/avatar_server.py` — lines ~717–730 (ElevenLabs), ~1067 (Gemini), ~1207–1216 (Anthropic)
- **Fix**: Wrap all external API calls with `tenacity` (or equivalent): 3 retries, exponential backoff starting at 1s, retry on `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout`, and HTTP 5xx. Do not retry on 4xx (including 429 — surface that as a quota alert).
- **Why unanimous**: All three models flagged zero retry logic as a reliability gap for a production service.

---

## MAJORITY FINDINGS
*(2 of 3 models agr

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: oracle/avatar_server.py (2213 lines)
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
 506 |                 "-c:v", "libx264", "-preset", "medium", "-crf", "18",
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
 521 |                 "-c:v", "libx264", "-preset", "medium", "-crf", "18",
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
 653 |             # Resample to 16kHz mono for Wav2Lip
 654 |             wav16_path = wav24_path + ".16k.wav"
 655 |             r = subprocess.run(
 656 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", wav24_path,
 657 |                  "-ar", "16000", "-ac", "1", "-f", "wav", wav16_path],
 658 |                 capture_output=True, text=True, timeout=30,
 659 |             )
 660 |             try:
 661 |                 os.remove(wav24_path)
 662 |             except OSError:
 663 |                 pass
 664 |             if r.returncode == 0 and os.path.exists(wav16_path) and os.path.getsize(wav16_path) > 1000:
 665 |                 # Loudnorm to -14 LUFS for consistent volume
 666 |                 norm_path = wav16_path + "_norm.wav"
 667 |                 subprocess.run(
 668 |                     ["ffmpeg", "-y", "-loglevel", "error", "-i", wav16_path,
 669 |                      "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
 670 |                      "-ar", "16000", "-ac", "1", norm_path],
 671 |                     capture_output=True, text=True, timeout=30,
 672 |                 )
 673 |                 if os.path.exists(norm_path) and os.path.getsize(norm_path) > 1000:
 674 |                     with open(norm_path, "rb") as f:
 675 |                         wav_bytes = f.read()
 676 |                     try:
 677 |                         os.remove(norm_path)
 678 |                     except OSError:
 679 |                         pass
 680 |                 else:
 681 |                     # Loudnorm failed, use unnormalized
 682 |                     with open(wav16_path, "rb") as f:
 683 |                         wav_bytes = f.read()
 684 |                 try:
 685 |                     os.remove(wav16_path)
 686 |                 except OSError:
 687 |                     pass
 688 |                 elapsed = time.time() - t0
 689 |                 logger.info(f"[AVATAR_TTS] Kokoro af_heart OK: {elapsed:.2f}s ({len(wav_bytes)} bytes)")
 690 |                 return wav_bytes
 691 |             else:
 692 |                 logger.warning("[AVATAR_TTS] Kokoro ffmpeg resample failed")
 693 |         except Exception as e:
 694 |             logger.error(f"[AVATAR_TTS] Kokoro FAILED: {e} → ElevenLabs fallback")
 695 |     else:
 696 |         logger.info("[AVATAR_TTS] Kokoro not ready → ElevenLabs fallback")
 697 | 
 698 |     # Fallback: ElevenLabs
 699 |     t0 = time.time()
 700 |     audio_bytes = text_to_speech(text)
 701 |     elapsed = time.time() - t0
 702 |     logger.info(f"[AVATAR_TTS] ElevenLabs fallback: {elapsed:.2f}s ({len(audio_bytes)} bytes)")
 703 |     return audio_bytes
 704 | 
 705 | 
 706 | def text_to_speech(text, voice_id="cgSgspJ2msm6clMCkdW9"):
 707 |     """Call ElevenLabs TTS API. Returns raw audio bytes (mp3)."""
 708 |     api_key = os.environ.get("ELEVENLABS_API_KEY", "")
 709 |     if not api_key:
 710 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
 711 |         if os.path.exists(env_path):
 712 |             for line in open(env_path):
 713 |                 if line.startswith("ELEVENLABS_API_KEY="):
 714 |                     api_key = line.strip().split("=", 1)[1].strip().strip("\"'")
 715 |     if not api_key:
 716 |         raise ValueError("ELEVENLABS_API_KEY not found in environment or .env")
 717 |     resp = http_requests.post(
 718 |         f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
 719 |         headers={"xi-api-key": api_key, "Content-Type": "application/json"},
 720 |         json={
 721 |             "text": text,
 722 |             "model_id": "eleven_turbo_v2_5",
 723 |             # LAW 3: Jessica voice settings — stability=0.45, similarity_boost=0.75, style=0.20
 724 |             "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.20},
 725 |         },
 726 |         timeout=60,
 727 |     )
 728 |     if resp.status_code != 200:
 729 |         raise Exception(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
 730 |     return resp.content
 731 | 
 732 | 
 733 | # ═══════════════════════════════════════════════════════════════════════
 734 | # FLASK ROUTES
 735 | # ═══════════════════════════════════════════════════════════════════════
 736 | 
 737 | @app.route("/health")
 738 | def health():
 739 |     """Enhanced health check with VRAM, latency, vision status, enhancer info."""
 740 |     reg = ModelRegistry.get() if ModelRegistry.is_loaded() else None
 741 |     vram = reg.vram_info() if reg else {"available": False}
 742 | 
 743 |     vision_enabled = bool(os.environ.get("GEMINI_API_KEY"))
 744 |     with _lock:
 745 |         avg_latency = round(sum(_request_times) / len(_request_times), 2) if _request_times else None
 746 |         tracked = len(_request_times)
 747 |     uptime = round(time.time() - _start_time, 1)
 748 | 
 749 |     return jsonify({
 750 |         "status": "ok",
 751 |         "engine": "wav2lip-gan-fp16-v2",
 752 |         "enhancements": ["fp16", "cached_face", "cv2_sharpen", "mediapipe_blinks", "head_movement"],
 753 |         "device": DEVICE,
 754 |         "model_loaded": reg is not None and reg.wav2lip_model is not None,
 755 |         "avatar_loaded": reg is not None and reg.avatar_face is not None,
 756 |         "avatar_size": (
 757 |             f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}"
 758 |             if reg and reg.avatar_face is not None else None
 759 |         ),
 760 |         "face_detected": reg is not None and reg.avatar_face_coords is not None,
 761 |         "face_enhancer": "cv2_sharpen_only",
 762 |         "blinks_enabled": True,  # v2 engine: cached landmarks
 763 |         "eye_landmarks_detected": (lambda: __import__("blink_engine")._load_cache() is not None)(),
 764 |         "vram": vram,
 765 |         "vision_enabled": vision_enabled,
 766 |         "uptime_sec": uptime,
 767 |         "avg_latency_sec": avg_latency,
 768 |         "requests_tracked": tracked,
 769 |         "output_fps": DEFAULT_FPS,
 770 |         "batch_size": BATCH_SIZE,
 771 |         "max_audio_seconds": MAX_AUDIO_SECONDS,
 772 |         "encoding": "crf28-ultrafast-512",
 773 |         "blink_config": {
 774 |             "interval": f"{BLINK_INTERVAL_MIN}-{BLINK_INTERVAL_MAX}s",
 775 |             "duration": f"{BLINK_DURATION}s"
 776 |         },
 777 |         "head_movement_config": {
 778 |             "rotation": f"\u00b1{HEAD_ROTATION_AMPLITUDE}\u00b0",
 779 |             "period": f"{HEAD_PERIOD}s"
 780 |         }
 781 |     })
 782 | 
 783 | 
 784 | @app.route("/status")
 785 | def status():
 786 |     """Alias for /health — frontend expects this route."""
 787 |     return health()
 788 | 
 789 | 
 790 | @app.route("/warmup", methods=["POST"])
 791 | def warmup():
 792 |     """Generate a tiny test video to warm up torch.compile and CUDA kernels."""
 793 |     t0 = time.time()
 794 |     reg = ModelRegistry.get()
 795 |     if reg.wav2lip_model is None:
 796 |         return jsonify({"error": "Model not loaded"}), 500
 797 | 
 798 |     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
 799 |         import wave
 800 |         with wave.open(tmp.name, "w") as wf:
 801 |             wf.setnchannels(1)
 802 |             wf.setsampwidth(2)
 803 |             wf.setframerate(16000)
 804 |             wf.writeframes(b"\x00\x00" * 8000)
 805 |         wav_path = tmp.name
 806 | 
 807 |     try:
 808 |         _render_semaphore.acquire()
 809 |         try:
 810 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
 811 |             if frames:
 812 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
 813 |         finally:
 814 |             _render_semaphore.release()
 815 |         elapsed = time.time() - t0
 816 |         logger.info(f"Warmup complete: {len(frames)} frames in {elapsed:.2f}s")
 817 |         return jsonify({
 818 |             "status": "warmed_up",
 819 |             "frames": len(frames),
 820 |             "warmup_time": round(elapsed, 2),
 821 |             "vram": reg.vram_info(),
 822 |         })
 823 |     except Exception as e:
 824 |         logger.error(f"Warmup error: {e}", exc_info=True)
 825 |         return jsonify({"error": str(e)}), 500
 826 |     finally:
 827 |         try:
 828 |             os.unlink(wav_path)
 829 |         except OSError:
 830 |             pass
 831 | 
 832 | 
 833 | @app.route("/generate", methods=["POST"])
 834 | def generate():
 835 |     """Generate lip-synced video with face restoration, blinks, and head movement.
 836 | 
 837 |     Accepts two modes:
 838 |       Mode A: {"text": "..."} -> Kokoro af_heart (or ElevenLabs fallback) -> Wav2Lip -> video
 839 |       Mode B: {"audio_base64": "...", "content_type": "..."} -> Wav2Lip -> video
 840 |     """
 841 |     data = request.get_json()
 842 |     if not data:
 843 |         return jsonify({"error": "JSON body required"}), 400
 844 | 
 845 |     # Input validation
 846 |     MAX_TEXT_LEN = 2000
 847 |     MAX_AUDIO_B64_LEN = 2_000_000  # ~1.5MB decoded
 848 |     if "text" in data:
 849 |         if not isinstance(data["text"], str) or len(data["text"]) > MAX_TEXT_LEN:
 850 |             return jsonify({"error": f"text must be a string under {MAX_TEXT_LEN} chars", "code": "INVALID_INPUT"}), 400
 851 |         if not data["text"].strip():
 852 |             return jsonify({"error": "text cannot be empty", "code": "INVALID_INPUT"}), 400
 853 |     elif "audio_base64" in data:
 854 |         if not isinstance(data["audio_base64"], str) or len(data["audio_base64"]) > MAX_AUDIO_B64_LEN:
 855 |             return jsonify({"error": "audio_base64 too large or invalid", "code": "INVALID_INPUT"}), 400
 856 |         try:
 857 |             base64.b64decode(data["audio_base64"], validate=True)
 858 |         except Exception:
 859 |             return jsonify({"error": "audio_base64 is not valid base64", "code": "INVALID_INPUT"}), 400
 860 |     else:
 861 |         return jsonify({"error": "text or audio_base64 required"}), 400
 862 | 
 863 |     enable_blinks = data.get("enable_blinks", True)  # v2 blink engine enabled
 864 |     enable_head_movement = data.get("enable_head_movement", True)
 865 |     fps = float(data.get("fps", DEFAULT_FPS))
 866 |     avatar_source = data.get("avatar_source", "default")
 867 |     if avatar_source not in AVATAR_SOURCES:
 868 |         avatar_source = "default"
 869 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
 870 | 
 871 |     # Resolve face for this render
 872 |     gen_face, gen_coords, _gen_eyes = _load_avatar_face(avatar_source)
 873 |     if gen_face is None or gen_coords is None:
 874 |         gen_face, gen_coords, _gen_eyes = _load_avatar_face("default")
 875 | 
 876 |     t_start = time.time()
 877 | 
 878 |     # Mode A: text -> Kokoro af_heart (primary) or ElevenLabs (fallback)
 879 |     if "text" in data:
 880 |         try:
 881 |             t_tts = time.time()
 882 |             audio_bytes = _avatar_tts(data["text"])
 883 |             logger.info(f"TTS: {len(audio_bytes)} bytes in {time.time()-t_tts:.2f}s")
 884 |         except Exception as e:
 885 |             logger.error(f"TTS error: {e}")
 886 |             return jsonify({"error": f"TTS failed: {e}"}), 500
 887 |         # Kokoro returns WAV, ElevenLabs returns MP3 — detect from header
 888 |         content_type = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
 889 |     # Mode B: raw audio
 890 |     elif "audio_base64" in data:
 891 |         audio_bytes = base64.b64decode(data["audio_base64"])
 892 |         content_type = data.get("content_type", "audio/mpeg")
 893 |     else:
 894 |         return jsonify({"error": "text or audio_base64 required"}), 400
 895 | 
 896 |     ext = ".mp3" if "mpeg" in content_type else ".wav"
 897 | 
 898 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
 899 |         tmp.write(audio_bytes)
 900 |         audio_path = tmp.name
 901 | 
 902 |     wav_path = audio_path + "_16k.wav"
 903 |     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
 904 | 
 905 |     # Input length guard: check audio duration
 906 |     try:
 907 |         import subprocess as _sp
 908 |         probe = _sp.run(
 909 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 910 |              "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
 911 |             capture_output=True, text=True, timeout=10,
 912 |         )
 913 |         audio_duration_sec = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
 914 |     except Exception as e:
 915 |         logger.error(f"[GENERATE] ffprobe failed: {e}", exc_info=True)
 916 |         audio_duration_sec = 0.0
 917 | 
 918 |     if audio_duration_sec == 0.0:
 919 |         logger.warning("[GENERATE] Audio duration is 0 — possible corrupt file")
 920 |         return jsonify({"error": "Audio validation failed: could not determine duration", "code": "INVALID_AUDIO"}), 400
 921 | 
 922 |     if audio_duration_sec > MAX_AUDIO_SECONDS:
 923 |         logger.warning(f"Audio too long ({audio_duration_sec:.1f}s > {MAX_AUDIO_SECONDS}s) — rejecting")
 924 |         return jsonify({
 925 |             "error": f"Audio too long ({audio_duration_sec:.1f}s). Max {MAX_AUDIO_SECONDS}s.",
 926 |             "code": "AUDIO_TOO_LONG",
 927 |             "max_seconds": MAX_AUDIO_SECONDS,
 928 |         }), 400
 929 | 
 930 |     try:
 931 |         reg = ModelRegistry.get()
 932 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
 933 |         if not acquired:
 934 |             return jsonify({"error": "GPU busy", "code": "GPU_BUSY", "retry_after": 5}), 503
 935 |         try:
 936 |             t0 = time.time()
 937 |             frames = wav2lip_generate(wav_path, fps, avatar_face=gen_face, avatar_face_coords=gen_coords)
 938 |             t_lip = time.time() - t0
 939 |             logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")
 940 | 
 941 |             # CV2 sharpen only — no GFPGAN
 942 |             t_enhance = 0.0
 943 |             if len(frames) > 0:
 944 |                 try:
 945 |                     t0_enh = time.time()
 946 |                     frames = sharpen_mouth_region(frames, gen_coords)
 947 |                     t_enhance = time.time() - t0_enh
 948 |                     logger.info(f"CV2 sharpen: {t_enhance:.2f}s")
 949 |                 except Exception as e:
 950 |                     logger.warning(f"Sharpen skipped: {e}")
 951 | 
 952 |             t0 = time.time()
 953 |             if enable_blinks or enable_head_movement:
 954 |                 frames = post_process_frames(
 955 |                     frames, fps,
 956 |                     enable_blinks=enable_blinks,
 957 |                     enable_head=enable_head_movement,
 958 |                 )
 959 |             t_post = time.time() - t0
 960 |             logger.info(f"Post-processing: {t_post:.2f}s")
 961 | 
 962 |             t0 = time.time()
 963 |             video_path = frames_to_video(frames, fps, audio_path=wav_path)
 964 |             t_encode = time.time() - t0
 965 |             logger.info(f"Encoding: {t_encode:.2f}s")
 966 |         finally:
 967 |             _render_semaphore.release()
 968 | 
 969 |         if not video_path:
 970 |             return jsonify({"error": "Video encoding failed", "code": "ENCODE_FAILED"}), 500
 971 | 
 972 |         t_total = time.time() - t_start
 973 |         _record_latency(t_total)
 974 |         duration = len(frames) / fps
 975 |         num_frames = len(frames)
 976 | 
 977 |         logger.info(
 978 |             f"Complete: {duration:.1f}s video, {num_frames} frames, "
 979 |             f"lip={t_lip:.1f}s enhance={t_enhance:.1f}s post={t_post:.1f}s enc={t_encode:.1f}s total={t_total:.1f}s"
 980 |         )
 981 | 
 982 |         cleanup_paths = [audio_path, wav_path, video_path]
 983 | 
 984 |         @after_this_request
 985 |         def _cleanup(response):
 986 |             for p in cleanup_paths:
 987 |                 try:
 988 |                     if p and os.path.exists(p):
 989 |                         os.unlink(p)
 990 |                 except OSError:
 991 |                     pass
 992 |             return response
 993 | 
 994 |         response = send_file(
 995 |             video_path,
 996 |             mimetype="video/mp4",
 997 |             as_attachment=True,
 998 |             download_name="oracle.mp4",
 999 |         )
1000 |         response.headers["X-Duration"] = str(round(duration, 2))
1001 |         response.headers["X-Frames"] = str(num_frames)
1002 |         response.headers["X-Processing-Time"] = str(round(t_total, 2))
1003 |         response.headers["X-Timing-Wav2Lip"] = str(round(t_lip, 2))
1004 |         response.headers["X-Timing-FaceEnhance"] = str(round(t_enhance, 2))
1005 |         response.headers["X-Timing-PostProcess"] = str(round(t_post, 2))
1006 |         response.headers["X-Timing-Encoding"] = str(round(t_encode, 2))
1007 |         return response
1008 | 
1009 |     except Exception as e:
1010 |         logger.error(f"Generation error: {e}", exc_info=True)
1011 |         return jsonify({"error": str(e), "code": "GENERATION_ERROR"}), 500
1012 |     finally:
1013 |         for p in [audio_path, wav_path]:
1014 |             try:
1015 |                 if os.path.exists(p):
1016 |                     os.unlink(p)
1017 |             except OSError:
1018 |                 pass
1019 | 
1020 | 
1021 | @app.route("/reload-avatar", methods=["POST"])
1022 | def reload_avatar():
1023 |     """Reload avatar source image via ModelRegistry."""
1024 |     reg = ModelRegistry.get()
1025 |     if reg.reload_avatar():
1026 |         return jsonify({
1027 |             "status": "reloaded",
1028 |             "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
1029 |             "face": reg.avatar_face_coords,
1030 |             "eye_landmarks": reg.eye_landmarks is not None,
1031 |         })
1032 |     else:
1033 |         return jsonify({"error": "No face detected in new image"}), 400
1034 | 
1035 | 
1036 | @app.route("/source-image")
1037 | def source_image():
1038 |     """Serve the current avatar source image."""
1039 |     reg = ModelRegistry.get()
1040 |     if reg.avatar_face is None:
1041 |         return jsonify({"error": "No avatar loaded"}), 404
1042 |     _, buf = cv2.imencode(".png", reg.avatar_face)
1043 |     b64 = base64.b64encode(buf).decode()
1044 |     return jsonify({
1045 |         "image_base64": b64,
1046 |         "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
1047 |         "face_coords": reg.avatar_face_coords
1048 |     })
1049 | 
1050 | 
1051 | # ═══════════════════════════════════════════════════════════════════════
1052 | # VISION GUIDE ENDPOINTS
1053 | # ═══════════════════════════════════════════════════════════════════════
1054 | 
1055 | @app.route("/vision/analyze", methods=["POST"])
1056 | def vision_analyze():
1057 |     """Analyze a Bitcoin hardware image with Gemini 2.5 Flash."""
1058 |     data = request.get_json()
1059 |     if not data or not data.get("image_base64"):
1060 |         return jsonify({"error": "image_base64 required"}), 400
1061 | 
1062 |     # Strip data URL prefix if present (client may send data:image/...;base64,)
1063 |     image_b64 = data["image_base64"]
1064 |     if image_b64.startswith("data:"):
1065 |         image_b64 = image_b64.split(",", 1)[1]
1066 | 
1067 |     from vision_guide import analyze_image, GuideSession
1068 |     result = analyze_image(
1069 |         image_b64=image_b64,
1070 |         mime_type=data.get("mime_type", "image/jpeg"),
1071 |         context=data.get("context", ""),
1072 |     )
1073 | 
1074 |     if "error" in result:
1075 |         return jsonify(result), 500
1076 | 
1077 |     # Create a GuideSession so follow-up /vision/guide calls have context
1078 |     guide_session = GuideSession.get_or_create(data.get("session_id"))
1079 |     result["session_id"] = guide_session.session_id
1080 | 
1081 |     # Seed the guide session history with this first analysis
1082 |     guide_session.history.append({
1083 |         "role": "user",
1084 |         "parts": [
1085 |             {"text": data.get("context", "Analyze this Bitcoin hardware image.")},
1086 |             {"inlineData": {"mimeType": data.get("mime_type", "image/jpeg"), "data": image_b64}},
1087 |         ],
1088 |     })
1089 |     guidance = result.get("guidance_text", "")
1090 |     if guidance:
1091 |         guide_session.history.append({
1092 |             "role": "model",
1093 |             "parts": [{"text": guidance}],
1094 |         })
1095 |     if result.get("device_name") and result["device_name"] != "unknown":
1096 |         guide_session.device_name = result["device_name"]
1097 | 
1098 |     # Phase 4: Store vision context in dialogue session for carry-forward
1099 |     session_id = data.get("session_id", "anon")
1100 |     try:
1101 |         from oracle_dialogue_engine import _get_session
1102 |         session = _get_session(session_id)
1103 |         vision_history = session.get("vision_history", [])
1104 |         analysis_summary = result.get("summary", "") or str(result.get("device_name", ""))
1105 |         if result.get("current_step"):
1106 |             analysis_summary += f" — {result['current_step']}"
1107 |         vision_history.append({
1108 |             "turn": session.get("turn", 0),
1109 |             "summary": analysis_summary[:200],
1110 |         })
1111 |         session["vision_history"] = vision_history[-3:]  # keep last 3
1112 |     except Exception as e:
1113 |         logger.warning(f"[VISION] Failed to store vision context: {e}")
1114 | 
1115 |     return jsonify(result)
1116 | 
1117 | 
1118 | @app.route("/vision/guide", methods=["POST"])
1119 | def vision_guide():
1120 |     """Multi-turn hardware setup guide session."""
1121 |     data = request.get_json()
1122 |     if not data:
1123 |         return jsonify({"error": "JSON body required"}), 400
1124 | 
1125 |     from vision_guide import GuideSession
1126 |     session = GuideSession.get_or_create(data.get("session_id"))
1127 | 
1128 |     if data.get("image_base64"):
1129 |         # Strip data URL prefix if present
1130 |         img_b64 = data["image_base64"]
1131 |         if img_b64.startswith("data:"):
1132 |             img_b64 = img_b64.split(",", 1)[1]
1133 |         question = data.get("question", "")
1134 |         last_context = data.get("last_context", "")
1135 |         if last_context:
1136 |             question += f"\n\nUser completed these steps: {last_context}\nNow showing the next screen."
1137 |         result = session.send_image(
1138 |             image_b64=img_b64,
1139 |             mime_type=data.get("mime_type", "image/jpeg"),
1140 |             question=question,
1141 |         )
1142 |     elif data.get("question"):
1143 |         result = session.send_text(data["question"])
1144 |     else:
1145 |         return jsonify({"error": "image_base64 or question required"}), 400
1146 | 
1147 |     if "error" in result:
1148 |         return jsonify(result), 500
1149 |     return jsonify(result)
1150 | 
1151 | 
1152 | @app.route("/vision/status")
1153 | def vision_status():
1154 |     """Check if vision features are enabled."""
1155 |     gemini_key = os.environ.get("GEMINI_API_KEY", "")
1156 |     enabled = bool(gemini_key)
1157 |     if enabled:
1158 |         return jsonify({
1159 |             "status": "enabled",
1160 |             "model": "gemini-2.5-flash",
1161 |             "endpoints": ["/vision/analyze", "/vision/guide", "/vision/sessions"],
1162 |         })
1163 |     else:
1164 |         return jsonify({
1165 |             "status": "disabled",
1166 |             "reason": "GEMINI_API_KEY not configured",
1167 |             "setup_url": "https://aistudio.google.com/apikey",
1168 |         })
1169 | 
1170 | 
1171 | @app.route("/vision/sessions")
1172 | def vision_sessions():
1173 |     """List active vision guide sessions."""
1174 |     from vision_guide import GuideSession
1175 |     return jsonify({
1176 |         "active_sessions": GuideSession.active_count(),
1177 |     })
1178 | 
1179 | 
1180 | # ═══════════════════════════════════════════════════════════════════════
1181 | # STREAMING PIPELINE
1182 | # ═══════════════════════════════════════════════════════════════════════
1183 | 
1184 | import re
1185 | import uuid
1186 | import subprocess
1187 | 
1188 | ORACLE_SYSTEM_PROMPT = (
1189 |     "You are the Oracle — Protocol Pulse's personal Bitcoin intelligence guide. "
1190 |     "You are having a private one-on-one conversation with a visitor. "
1191 |     "You are an EDUCATOR (explain Bitcoin at any level), GUIDE (help navigate Protocol Pulse), "
1192 |     "TECHNICAL ASSISTANT (wallets, self-custody, nodes, hardware), and INTELLIGENCE ANALYST "
1193 |     "(market state, price action — conversational, not broadcast). "
1194 |     "TONE: Warm but sharp. Knowledgeable without being condescending. "
1195 |     "Like the smartest person in Bitcoin who actually has time for you. "
1196 |     "Keep responses under 3 sentences. Never say 'As an AI' or offer daily briefs unprompted. "
1197 |     "You are NOT a news anchor or briefing bot — you are a personal guide."
1198 | )
1199 | ORACLE_VOICE_ID = "cgSgspJ2msm6clMCkdW9"  # Jessica
1200 | ORACLE_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
1201 | ORACLE_IDLE_PATH = os.path.join(ORACLE_STATIC_DIR, "oracle_idle.mp4")
1202 | 
1203 | _stream_sessions = {}
1204 | _stream_lock = threading.Lock()
1205 | 
1206 | 
1207 | def _get_anthropic_key():
1208 |     """Get Anthropic API key from env or .env file."""
1209 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
1210 |     if not key:
1211 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
1212 |         if os.path.exists(env_path):
1213 |             for line in open(env_path):
1214 |                 if line.startswith("ANTHROPIC_API_KEY="):
1215 |                     key = line.strip().split("=", 1)[1].strip().strip("\"'")
1216 |     return key
1217 | 
1218 | 
1219 | def _split_sentences(text):
1220 |     """Split text into sentences for chunked processing."""
1221 |     sentences = re.split(r'(?<=[.!?])\s+', text.strip())
1222 |     return [s for s in sentences if s.strip()]
1223 | 
1224 | 
1225 | def _generate_chunk(sentence, chunk_num, session_dir, fps=30.0):
1226 |     """Generate a single video chunk for a sentence: TTS -> Wav2Lip -> MP4."""
1227 |     try:
1228 |         audio_bytes = _avatar_tts(sentence)
1229 |         is_wav = audio_bytes[:4] == b"RIFF"
1230 |         ext = ".wav" if is_wav else ".mp3"
1231 |         audio_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}{ext}")
1232 |         with open(audio_path, "wb") as f:
1233 |             f.write(audio_bytes)
1234 | 
1235 |         wav_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}_16k.wav")
1236 |         if is_wav:
1237 |             # F5 already returned 16kHz mono WAV — just copy
1238 |             import shutil
1239 |             shutil.copy2(audio_path, wav_path)
1240 |         else:
1241 |             subprocess.run(
1242 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
1243 |                 check=True, capture_output=True,
1244 |             )
1245 | 
1246 |         _render_semaphore.acquire()
1247 |         try:
1248 |             frames = wav2lip_generate(wav_path, fps)
1249 |             reg = ModelRegistry.get()
1250 |             try:
1251 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1252 |             except Exception as e:
1253 |                 logger.warning(f"[CHUNK] Sharpening failed on chunk {chunk_num}: {e}", exc_info=True)
1254 |             frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1255 |         finally:
1256 |             _render_semaphore.release()
1257 | 
1258 |         video_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}.mp4")
1259 |         tmp_path = frames_to_video(frames, fps, audio_path=wav_path)
1260 |         if tmp_path:
1261 |             os.rename(tmp_path, video_path)
1262 |             return video_path
1263 |         return None
1264 |     except Exception as e:
1265 |         logger.error(f"Chunk {chunk_num} generation error: {e}", exc_info=True)
1266 |         return None
1267 | 
1268 | 
1269 | def _stream_worker(session_id, text):
1270 |     """Background worker: call Claude -> split sentences -> generate chunks."""
1271 |     session = _stream_sessions.get(session_id)
1272 |     if not session:
1273 |         return
1274 | 
1275 |     try:
1276 |         api_key = _get_anthropic_key()
1277 |         if not api_key:
1278 |             logger.warning("No Anthropic key — using input text as-is")
1279 |             ai_text = text
1280 |         else:
1281 |             resp = http_requests.post(
1282 |                 "https://api.anthropic.com/v1/messages",
1283 |                 headers={
1284 |                     "x-api-key": api_key,
1285 |                     "anthropic-version": "2023-06-01",
1286 |                     "content-type": "application/json",
1287 |                 },
1288 |                 json={
1289 |                     "model": "claude-sonnet-4-20250514",
1290 |                     "max_tokens": 80,  # Short transcript = fewer TTS seconds = fewer Wav2Lip frames
1291 |                     "system": ORACLE_SYSTEM_PROMPT,
1292 |                     "messages": [{"role": "user", "content": text}],
1293 |                 },
1294 |                 timeout=30,
1295 |             )
1296 |             if resp.status_code == 200:
1297 |                 ai_text = resp.json()["content"][0]["text"]
1298 |             else:
1299 |                 logger.error(f"Claude API error {resp.status_code}: {resp.text[:200]}")
1300 |                 ai_text = text
1301 | 
1302 |         session["ai_response"] = ai_text
1303 |         sentences = _split_sentences(ai_text)
1304 |         session["total_chunks"] = len(sentences)
1305 | 
1306 |         session_dir = session["dir"]
1307 |         for i, sentence in enumerate(sentences):
1308 |             chunk_path = _generate_chunk(sentence, i, session_dir)
1309 |             if chunk_path:
1310 |                 session["chunks_ready"].append(chunk_path)
1311 |             else:
1312 |                 session["errors"].append(f"Chunk {i} failed")
1313 | 
1314 |         session["status"] = "complete"
1315 | 
1316 |     except Exception as e:
1317 |         logger.error(f"Stream worker error: {e}", exc_info=True)
1318 |         session["status"] = "error"
1319 |         session["errors"].append(str(e))
1320 | 
1321 | 
1322 | @app.route("/generate_stream", methods=["POST"])
1323 | def generate_stream():
1324 |     """Start streaming generation: text -> Claude -> sentence chunks -> video chunks."""
1325 |     data = request.get_json()
1326 |     if not data or not data.get("text"):
1327 |         return jsonify({"error": "text required"}), 400
1328 | 
1329 |     session_id = str(uuid.uuid4())[:12]
1330 |     session_dir = os.path.join(tempfile.gettempdir(), f"oracle_stream_{session_id}")
1331 |     os.makedirs(session_dir, exist_ok=True)
1332 | 
1333 |     session = {
1334 |         "id": session_id,
1335 |         "status": "processing",
1336 |         "text": data["text"],
1337 |         "ai_response": None,
1338 |         "total_chunks": 0,
1339 |         "chunks_ready": [],
1340 |         "errors": [],
1341 |         "dir": session_dir,
1342 |         "created": time.time(),
1343 |     }
1344 | 
1345 |     with _stream_lock:
1346 |         _stream_sessions[session_id] = session
1347 | 
1348 |     thread = threading.Thread(target=_stream_worker, args=(session_id, data["text"]), daemon=True)
1349 |     thread.start()
1350 | 
1351 |     return jsonify({
1352 |         "session_id": session_id,
1353 |         "status": "processing",
1354 |         "message": "Stream generation started. Poll /stream_status/{session_id} for progress.",
1355 |     })
1356 | 
1357 | 
1358 | @app.route("/stream_status/<session_id>")
1359 | def stream_status(session_id):
1360 |     """Poll for streaming generation progress."""
1361 |     session = _stream_sessions.get(session_id)
1362 |     if not session:
1363 |         return jsonify({"error": "Session not found"}), 404
1364 | 
1365 |     return jsonify({
1366 |         "session_id": session_id,
1367 |         "status": session["status"],
1368 |         "ai_response": session.get("ai_response"),
1369 |         "chunks_ready": len(session["chunks_ready"]),
1370 |         "total_chunks": session["total_chunks"],
1371 |         "total_estimated": max(session["total_chunks"], 3),
1372 |         "errors": session["errors"],
1373 |     })
1374 | 
1375 | 
1376 | @app.route("/stream_chunk/<session_id>/<int:chunk_number>")
1377 | def stream_chunk(session_id, chunk_number):
1378 |     """Fetch a generated video chunk by number."""
1379 |     session = _stream_sessions.get(session_id)
1380 |     if not session:
1381 |         return jsonify({"error": "Session not found"}), 404
1382 | 
1383 |     if chunk_number >= len(session["chunks_ready"]):
1384 |         return jsonify({"error": "Chunk not ready yet"}), 404
1385 | 
1386 |     chunk_path = session["chunks_ready"][chunk_number]
1387 |     if not os.path.exists(chunk_path):
1388 |         return jsonify({"error": "Chunk file missing"}), 500
1389 | 
1390 |     return send_file(chunk_path, mimetype="video/mp4", as_attachment=True,
1391 |                      download_name=f"chunk_{chunk_number:03d}.mp4")
1392 | 
1393 | 
1394 | @app.route("/oracle_idle")
1395 | def oracle_idle():
1396 |     """Serve the pre-rendered idle loop video."""
1397 |     if os.path.exists(ORACLE_IDLE_PATH):
1398 |         return send_file(ORACLE_IDLE_PATH, mimetype="video/mp4")
1399 |     return jsonify({"error": "Idle video not generated yet"}), 404
1400 | 
1401 | 
1402 | def generate_idle_loop():
1403 |     """Generate a 4-second idle loop with blinks + head movement (no audio)."""
1404 |     os.makedirs(ORACLE_STATIC_DIR, exist_ok=True)
1405 |     if os.path.exists(ORACLE_IDLE_PATH):
1406 |         logger.info("Idle loop already exists, skipping generation")
1407 |         return
1408 | 
1409 |     logger.info("Generating idle loop video...")
1410 |     reg = ModelRegistry.get()
1411 |     if reg.avatar_face is None:
1412 |         logger.error("Cannot generate idle loop: no avatar loaded")
1413 |         return
1414 | 
1415 |     fps = DEFAULT_FPS
1416 |     duration = 4.0
1417 |     num_frames = int(duration * fps)
1418 | 
1419 |     base_frame = reg.avatar_face.copy()
1420 |     frames = [base_frame.copy() for _ in range(num_frames)]
1421 | 
1422 |     frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1423 | 
1424 |     video_path = frames_to_video(frames, fps, audio_path=None)
1425 |     if video_path:
1426 |         os.rename(video_path, ORACLE_IDLE_PATH)
1427 |         logger.info(f"Idle loop saved: {ORACLE_IDLE_PATH} ({num_frames} frames)")
1428 |     else:
1429 |         logger.error("Failed to generate idle loop")
1430 | 
1431 | 
1432 | # ═══════════════════════════════════════════════════════════════════════
1433 | # ORACLE PRE-CACHE + INTELLIGENCE ENDPOINTS
1434 | # ═══════════════════════════════════════════════════════════════════════
1435 | 
1436 | import oracle_cache_manager
1437 | import oracle_intelligence_feed
1438 | import oracle_dialogue_engine
1439 | 
1440 | # Intent classification — keyword matching
1441 | INTENT_PATTERNS = {
1442 |     "DAILY_BRIEF": r"brief|today|news|happening|what's|latest",
1443 |     "SOVEREIGNTY_INTRO": r"sovereign|score|free",
1444 |     "SOVEREIGNTY_COLD_WALLET": r"cold.?wallet|hardware|ledger|coldcard|custody",
1445 |     "SOVEREIGNTY_NODE": r"node|umbrel|raspberry|verify",
1446 |     "SOVEREIGNTY_BITAXE": r"bitaxe|mine|mining|solo",
1447 |     "SOVEREIGNTY_LIFE_INSURANCE": r"insurance|meanwhile|estate|death",
1448 |     "SOVEREIGNTY_RESIDENCY": r"residency|palau|rns|passport|citizenship",
1449 |     "GOODBYE": r"bye|goodbye|later|thanks",
1450 | }
1451 | 
1452 | 
1453 | def classify_intent(transcript):
1454 |     """Classify user transcript to an intent key. Returns (intent, confidence)."""
1455 |     text = transcript.lower().strip()
1456 |     for intent, pattern in INTENT_PATTERNS.items():
1457 |         if re.search(pattern, text):
1458 |             return intent, 0.85
1459 |     return "UNKNOWN", 0.4
1460 | 
1461 | 
1462 | @app.route("/oracle/cache/status")
1463 | def oracle_cache_status():
1464 |     """Return status of pre-cached responses and daily brief."""
1465 |     cache_status = oracle_cache_manager.get_cache_status()
1466 |     daily_brief = oracle_intelligence_feed.get_daily_brief()
1467 |     return jsonify({
1468 |         "cached_responses": cache_status,
1469 |         "daily_brief_ready": daily_brief is not None,
1470 |         "daily_brief_path": daily_brief,
1471 |         "cache_ttl_s": oracle_cache_manager.CACHE_TTL,
1472 |     })
1473 | 
1474 | 
1475 | @app.route("/oracle/response/<key>")
1476 | def oracle_response(key):
1477 |     """Serve pre-cached mp4 for a response key."""
1478 |     key = key.upper()
1479 |     if key not in oracle_cache_manager.RESPONSE_TREE and key != "DAILY_BRIEF_LIVE":
1480 |         return jsonify({"error": "Unknown response key", "valid_keys": list(oracle_cache_manager.RESPONSE_TREE.keys())}), 404
1481 | 
1482 |     # Daily brief special case
1483 |     if key == "DAILY_BRIEF_LIVE":
1484 |         path = oracle_intelligence_feed.get_daily_brief()
1485 |         if path:
1486 |             return send_file(path, mimetype="video/mp4")
1487 |         return jsonify({"error": "Daily brief not ready yet", "status": "pending"}), 202
1488 | 
1489 |     # Check if rendering
1490 |     if oracle_cache_manager.is_rendering(key):
1491 |         return jsonify({"error": "Response is being rendered", "status": "rendering"}), 202
1492 | 
1493 |     path = oracle_cache_manager.get_cached_response(key)
1494 |     if path:
1495 |         return send_file(path, mimetype="video/mp4")
1496 | 
1497 |     return jsonify({"error": "Response not cached yet", "status": "pending"}), 202
1498 | 
1499 | 
1500 | @app.route("/oracle/speak", methods=["POST"])
1501 | def oracle_speak():
1502 |     """Serve cached response for an intent, or fallback to /generate."""
1503 |     data = request.get_json()
1504 |     if not data or not data.get("intent"):
1505 |         return jsonify({"error": "intent required"}), 400
1506 | 
1507 |     intent = data["intent"].upper()
1508 | 
1509 |     # Try daily brief
1510 |     if intent == "DAILY_BRIEF":
1511 |         brief_path = oracle_intelligence_feed.get_daily_brief()
1512 |         if brief_path:
1513 |             return send_file(brief_path, mimetype="video/mp4")
1514 |         # Fallback to intro
1515 |         intent = "DAILY_BRIEF_INTRO"
1516 | 
1517 |     # If caller provided explicit text, use it directly (broadcast segments, custom scripts)
1518 |     caller_text = (data.get("text") or "").strip()
1519 |     if caller_text:
1520 |         return generate_inline(caller_text)
1521 | 
1522 |     # Try cached response
1523 |     path = oracle_cache_manager.get_cached_response(intent)
1524 |     if path:
1525 |         return send_file(path, mimetype="video/mp4")
1526 | 
1527 |     # Fallback: generate on the fly — but don't block if GPU is busy (cache warming)
1528 |     text = oracle_cache_manager.RESPONSE_TREE.get(intent)
1529 |     if not text:
1530 |         text = oracle_cache_manager.RESPONSE_TREE["UNKNOWN_QUESTION"]
1531 | 
1532 |     # Check GPU availability without acquire-release-reacquire race
1533 |     if _render_semaphore._value == 0:
1534 |         return jsonify({"error": "GPU busy warming cache — try again shortly",
1535 |                         "status": "warming", "retry_after": 30}), 503
1536 | 
1537 |     return generate_inline(text)
1538 | 
1539 | 
1540 | def generate_inline(text):
1541 |     """Internal helper: generate a video from text and return it."""
1542 |     try:
1543 |         audio_bytes = _avatar_tts(text)
1544 |     except Exception as e:
1545 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1546 | 
1547 |     is_wav = audio_bytes[:4] == b"RIFF"
1548 |     ext = ".wav" if is_wav else ".mp3"
1549 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1550 |         tmp.write(audio_bytes)
1551 |         audio_path = tmp.name
1552 | 
1553 |     wav_path = audio_path + "_16k.wav"
1554 |     if is_wav:
1555 |         import shutil
1556 |         shutil.copy2(audio_path, wav_path)
1557 |     else:
1558 |         subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1559 | 
1560 |     try:
1561 |         # Check queue state for concurrency visibility
1562 |         with _render_queue_lock:
1563 |             _queue_pos = sum(1 for _ in range(2) if not _render_semaphore._value)
1564 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
1565 |         if not acquired:
1566 |             return jsonify({"error": "GPU busy — try again in a moment", "retry_after": 10,
1567 |                             "queue_position": _queue_pos}), 503
1568 |         try:
1569 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
1570 |             reg = ModelRegistry.get()
1571 |             try:
1572 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1573 |             except Exception as e:
1574 |                 logger.warning(f"[INLINE] Sharpening failed: {e}", exc_info=True)
1575 |             frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1576 |             video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1577 |         finally:
1578 |             _render_semaphore.release()
1579 | 
1580 |         if not video_path:
1581 |             return jsonify({"error": "Video encoding failed"}), 500
1582 | 
1583 |         # Stream video as inline (not attachment) so browser plays it directly.
1584 |         # Generator pattern ensures file stays on disk until fully sent,
1585 |         # then cleans up. Fixes iOS mid-stream cutoff + double-unlink race.
1586 |         def _stream_and_cleanup():
1587 |             try:
1588 |                 with open(video_path, "rb") as vf:
1589 |                     while True:
1590 |                         chunk = vf.read(65536)
1591 |                         if not chunk:
1592 |                             break
1593 |                         yield chunk
1594 |             finally:
1595 |                 for p in [audio_path, wav_path, video_path]:
1596 |                     try:
1597 |                         if p and os.path.exists(p):
1598 |                             os.unlink(p)
1599 |                     except OSError:
1600 |                         pass
1601 | 
1602 |         from flask import Response
1603 |         return Response(
1604 |             _stream_and_cleanup(),
1605 |             mimetype="video/mp4",
1606 |             headers={
1607 |                 "Content-Disposition": "inline",
1608 |                 "X-Accel-Buffering": "no",
1609 |                 "Cache-Control": "no-cache",
1610 |             },
1611 |         )
1612 | 
1613 |     except Exception as e:
1614 |         logger.error(f"generate_inline error: {e}", exc_info=True)
1615 |         for p in [audio_path, wav_path]:
1616 |             try:
1617 |                 if os.path.exists(p): os.unlink(p)
1618 |             except OSError:
1619 |                 pass
1620 |         return jsonify({"error": str(e)}), 500
1621 | 
1622 | 
1623 | 
1624 | 
1625 | 
1626 | 
1627 | @app.route("/oracle/voice", methods=["POST"])
1628 | def oracle_voice():
1629 |     """
1630 |     Voice-only endpoint: text -> ElevenLabs TTS -> audio/mpeg.
1631 |     No Wav2Lip, no GPU. ~400ms vs ~14s for full video.
1632 |     Use for vision guidance, quick confirmations, non-visual responses.
1633 |     Body: {"text": "...", "voice_id": "optional"}
1634 |     """
1635 |     data = request.get_json()
1636 |     if not data or not data.get("text"):
1637 |         return jsonify({"error": "text required"}), 400
1638 | 
1639 |     text = data["text"].strip()
1640 | 
1641 |     try:
1642 |         t0 = time.time()
1643 |         audio_bytes = _avatar_tts(text)
1644 |         logger.info(f"[VOICE] TTS {len(audio_bytes)}B in {time.time()-t0:.2f}s")
1645 |     except Exception as e:
1646 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1647 | 
1648 |     # Loudnorm pass if not already normalized (WAV from Kokoro is already normalized in _avatar_tts,
1649 |     # but ElevenLabs MP3 fallback is not)
1650 |     is_wav = audio_bytes[:4] == b"RIFF"
1651 |     if not is_wav:
1652 |         try:
1653 |             with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as _tmp:
1654 |                 _tmp.write(audio_bytes)
1655 |                 _raw_path = _tmp.name
1656 |             _norm_path = _raw_path + "_norm.wav"
1657 |             _nr = subprocess.run(
1658 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", _raw_path,
1659 |                  "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
1660 |                  "-ar", "16000", "-ac", "1", _norm_path],
1661 |                 capture_output=True, text=True, timeout=30,
1662 |             )
1663 |             if _nr.returncode == 0 and os.path.exists(_norm_path) and os.path.getsize(_norm_path) > 1000:
1664 |                 with open(_norm_path, "rb") as _nf:
1665 |                     audio_bytes = _nf.read()
1666 |                 is_wav = True
1667 |             for _p in [_raw_path, _norm_path]:
1668 |                 try:
1669 |                     os.remove(_p)
1670 |                 except OSError:
1671 |                     pass
1672 |         except Exception as _ne:
1673 |             logger.warning(f"[VOICE] loudnorm failed (non-fatal): {_ne}")
1674 | 
1675 |     mime = "audio/wav" if is_wav else "audio/mpeg"
1676 | 
1677 |     from flask import Response
1678 |     return Response(
1679 |         audio_bytes,
1680 |         mimetype=mime,
1681 |         headers={
1682 |             "Content-Disposition": "inline",
1683 |             "Content-Length": str(len(audio_bytes)),
1684 |             "Cache-Control": "no-cache",
1685 |         },
1686 |     )
1687 | 
1688 | @app.route("/oracle/job/<job_id>")
1689 | def oracle_job_status(job_id):
1690 |     """Poll for async video render completion."""
1691 |     # Expire stale jobs (pending older than TTL, or completed older than 30s)
1692 |     now = time.time()
1693 |     with _render_jobs_lock:
1694 |         expired = []
1695 |         for k, v in _render_jobs.items():
1696 |             if v.get("completed_at"):
1697 |                 # Completed jobs: keep for 30s after completion
1698 |                 if now - v["completed_at"] > 30:
1699 |                     expired.append(k)
1700 |             elif now - v.get("created", 0) > _RENDER_JOB_TTL:
1701 |                 expired.append(k)
1702 |         for k in expired:
1703 |             del _render_jobs[k]
1704 |         job = _render_jobs.get(job_id)
1705 |     if not job:
1706 |         return jsonify({"status": "not_found"}), 404
1707 |     if job["status"] == "done":
1708 |         # Mark completed_at on first successful poll (keep job for 30s)
1709 |         if not job.get("completed_at"):
1710 |             with _render_jobs_lock:
1711 |                 if job_id in _render_jobs:
1712 |                     _render_jobs[job_id]["completed_at"] = time.time()
1713 |         video_bytes = job["video_bytes"]
1714 |         from flask import Response
1715 |         return Response(video_bytes, mimetype="video/mp4",
1716 |                         headers={"Content-Disposition": "inline", "Cache-Control": "no-cache"})
1717 |     if job["status"] == "error":
1718 |         # Mark completed_at for errors too
1719 |         if not job.get("completed_at"):
1720 |             with _render_jobs_lock:
1721 |                 if job_id in _render_jobs:
1722 |                     _render_jobs[job_id]["completed_at"] = time.time()
1723 |         return jsonify({"status": "error"}), 500
1724 |     return jsonify({"status": "pending"}), 202
1725 | 
1726 | 
1727 | @app.route("/oracle/job/<job_id>/audio")
1728 | def oracle_job_audio(job_id):
1729 |     """Return cached TTS audio from an async render job (avoids duplicate Kokoro call)."""
1730 |     with _render_jobs_lock:
1731 |         job = _render_jobs.get(job_id)
1732 |     if not job:
1733 |         return jsonify({"status": "not_found"}), 404
1734 |     if not job.get("audio_bytes"):
1735 |         # Audio not yet generated — tell client to poll again
1736 |         return jsonify({"status": "pending", "retry_after": 2}), 202
1737 |     audio_bytes = job["audio_bytes"]
1738 |     mime = job.get("audio_mime", "audio/wav")
1739 |     from flask import Response
1740 |     return Response(audio_bytes, mimetype=mime,
1741 |                     headers={"Content-Disposition": "inline",
1742 |                              "Content-Length": str(len(audio_bytes)),
1743 |                              "Cache-Control": "no-cache"})
1744 | 
1745 | 
1746 | @app.route("/oracle/chat", methods=["POST"])
1747 | def oracle_chat():
1748 |     data = request.get_json()
1749 |     if not data or not data.get("text"):
1750 |         return jsonify({"error": "text required"}), 400
1751 |     text = data["text"].strip()
1752 |     session_id = data.get("session_id", "anon")
1753 |     audio_first = data.get("audio_first", False)
1754 |     avatar_source = data.get("avatar_source", "default")
1755 |     if avatar_source not in AVATAR_SOURCES:
1756 |         avatar_source = "default"
1757 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
1758 | 
1759 |     # ── Phase 3: Visitor fingerprint + memory ──────────────────────────
1760 |     from oracle_memory import make_fingerprint, load_visitor
1761 |     visitor_token = data.get("visitor_token", "anon")
1762 |     raw_ip = (request.headers.get("X-Forwarded-For", "") or request.remote_addr or "").split(",")[0].strip()
1763 |     ua = request.headers.get("User-Agent", "")
1764 |     fingerprint = make_fingerprint(raw_ip, ua, visitor_token)
1765 | 
1766 |     session = oracle_dialogue_engine._get_session(session_id)
1767 |     if session["turn"] == 0:
1768 |         memory = load_visitor(fingerprint)
1769 |         if memory:
1770 |             session["visitor_memory"] = memory
1771 |             logger.info(f"[MEMORY] Returning visitor — session #{memory['session_count']}")
1772 |             if memory.get("recent_turns"):
1773 |                 # Pre-warm session with last exchange so Oracle has context immediately
1774 |                 recent = memory["recent_turns"]
1775 |                 if recent:
1776 |                     last = recent[-1]
1777 |                     if last.get("user") and last.get("oracle"):
1778 |                         session["history"] = [
1779 |                             {"role": "user", "content": f"[PRIOR SESSION] {last['user']}"},
1780 |                             {"role": "assistant", "content": f"[PRIOR SESSION] {last['oracle']}"},
1781 |                         ]
1782 |                         logger.info(f"[MEMORY] Pre-warmed session with {len(recent)} prior turns")
1783 |     session["fingerprint"] = fingerprint
1784 | 
1785 |     _sess_turn = oracle_dialogue_engine.get_session_info(session_id).get("turn", 0)
1786 |     if data.get("use_cache_for_intents", True) and _sess_turn == 0:
1787 |         intent, confidence = classify_intent(text)
1788 |         if confidence >= 0.8 and intent != "UNKNOWN":
1789 |             path = oracle_cache_manager.get_cached_response(intent)
1790 |             if path:
1791 |                 logger.info(f"[CHAT] Cache hit {intent}")
1792 |                 return send_file(path, mimetype="video/mp4")
1793 |     elif _sess_turn > 0:
1794 |         logger.info(f"[CHAT] Cache skipped turn={_sess_turn}")
1795 |     live_intel = {}
1796 |     try:
1797 |         live_intel = oracle_dialogue_engine.get_live_intel()
1798 |     except Exception:
1799 |         pass
1800 |     page_context = data.get("page_context", None)
1801 |     result = oracle_dialogue_engine.generate_response(session_id, text, live_intel, page_context)
1802 |     logger.info(f"[CHAT] {session_id} t={result['turn']} p={result['personality']} ctx={page_context.get('type','?') if page_context else 'none'}: {result['text'][:50]}")
1803 | 
1804 |     # ── Background memory save — persist after every turn, not just on unload ──
1805 |     try:
1806 |         _fp = session.get("fingerprint")
1807 |         _hist = session.get("history", [])
1808 |         if _fp and len(_hist) >= 2:
1809 |             import threading as _mem_threading
1810 |             def _bg_save():
1811 |                 try:
1812 |                     from oracle_memory import save_visitor
1813 |                     _flow = session.get("setup_flow", {})
1814 |                     _prev = session.get("visitor_memory", {})
1815 |                     # Store last 3 user+oracle pairs as recent_turns
1816 |                     _turns = []
1817 |                     for i in range(0, min(6, len(_hist)), 2):
1818 |                         if i+1 < len(_hist):
1819 |                             _turns.append({
1820 |                                 "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1821 |                                 "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1822 |                             })
1823 |                     save_visitor(_fp, {
1824 |                         "personality": session.get("personality", "AMIABLE"),
1825 |                         "session_summaries": _prev.get("session_summaries", []),
1826 |                         "setup_device": _flow.get("device"),
1827 |                         "setup_step": _flow.get("step", 0),
1828 |                         "topics_seen": list(session.get("topics_discussed", [])),
1829 |                         "products_shown": list(session.get("products_mentioned", [])),
1830 |                         "recent_turns": list(reversed(_turns)),
1831 |                     })
1832 |                 except Exception as _se:
1833 |                     logger.debug(f"[MEMORY] bg save error: {_se}")
1834 |             _mem_threading.Thread(target=_bg_save, daemon=True).start()
1835 |     except Exception:
1836 |         pass
1837 | 
1838 |     if audio_first:
1839 |         # Phase A: return text immediately, fire video render in background
1840 |         job_id = uuid.uuid4().hex[:16]
1841 |         with _render_jobs_lock:
1842 |             _render_jobs[job_id] = {"status": "pending", "video_bytes": None, "created": time.time()}
1843 | 
1844 |         response_text = result["text"]
1845 | 
1846 |         def render_async(txt, jid, src_name="default"):
1847 |             logger.info(f"[RENDER_ASYNC] STARTED job {jid} source={src_name} text={txt[:60]}...")
1848 |             try:
1849 |                 # Resolve avatar source for this render
1850 |                 a_face, a_coords, _a_eyes = _load_avatar_face(src_name)
1851 |                 if a_face is None or a_coords is None:
1852 |                     logger.warning(f"[ASYNC RENDER] Avatar source '{src_name}' failed, falling back to default")
1853 |                     a_face, a_coords, _a_eyes = _load_avatar_face("default")
1854 | 
1855 |                 audio_bytes = _avatar_tts(txt)
1856 |                 # Cache audio in job dict so frontend can fetch it without calling Kokoro again
1857 |                 with _render_jobs_lock:
1858 |                     if jid in _render_jobs:
1859 |                         _render_jobs[jid]["audio_bytes"] = audio_bytes
1860 |                         _render_jobs[jid]["audio_mime"] = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
1861 |                 is_wav = audio_bytes[:4] == b"RIFF"
1862 |                 ext = ".wav" if is_wav else ".mp3"
1863 |                 with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1864 |                     tmp.write(audio_bytes)
1865 |                     audio_path = tmp.name
1866 |                 wav_path = audio_path + "_16k.wav"
1867 |                 if is_wav:
1868 |                     import shutil
1869 |                     shutil.copy2(audio_path, wav_path)
1870 |                 else:
1871 |                     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1872 |                 try:
1873 |                     acquired = _render_semaphore.acquire(timeout=60)
1874 |                     if not acquired:
1875 |                         logger.warning(f"[ASYNC RENDER] GPU busy for job {jid}")
1876 |                         with _render_jobs_lock:
1877 |                             if jid in _render_jobs:
1878 |                                 _render_jobs[jid] = {"status": "error", "video_bytes": None,
1879 |                                                      "created": time.time(), "code": "GPU_BUSY"}
1880 |                         return
1881 |                     try:
1882 |                         frames = wav2lip_generate(wav_path, DEFAULT_FPS, avatar_face=a_face, avatar_face_coords=a_coords)
1883 |                         try:
1884 |                             frames = sharpen_mouth_region(frames, a_coords)
1885 |                         except Exception as e:
1886 |                             logger.warning(f"[ASYNC RENDER] Sharpening failed for job {jid}: {e}", exc_info=True)
1887 |                         frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1888 |                         video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1889 |                     finally:
1890 |                         _render_semaphore.release()
1891 | 
1892 |                     if video_path and os.path.exists(video_path):
1893 |                         with open(video_path, "rb") as vf:
1894 |                             vbytes = vf.read()
1895 |                         os.unlink(video_path)
1896 |                         with _render_jobs_lock:
1897 |                             if jid in _render_jobs:
1898 |                                 _render_jobs[jid] = {"status": "done", "video_bytes": vbytes, "created": time.time()}
1899 |                     else:
1900 |                         with _render_jobs_lock:
1901 |                             if jid in _render_jobs:
1902 |                                 _render_jobs[jid]["status"] = "error"
1903 |                 finally:
1904 |                     for p in [audio_path, wav_path]:
1905 |                         try:
1906 |                             if os.path.exists(p):
1907 |                                 os.unlink(p)
1908 |                         except OSError:
1909 |                             pass
1910 |             except Exception as e:
1911 |                 logger.error(f"[ASYNC RENDER] {e}")
1912 |                 with _render_jobs_lock:
1913 |                     if jid in _render_jobs:
1914 |                         _render_jobs[jid]["status"] = "error"
1915 | 
1916 |         t = threading.Thread(target=render_async, args=(response_text, job_id, avatar_source), daemon=True)
1917 |         t.start()
1918 | 
1919 |         resp_data = {
1920 |             "text": response_text,
1921 |             "session_id": session_id,
1922 |             "job_id": job_id,
1923 |             "video_pending": True,
1924 |         }
1925 |         # Detect action card from user input (zero LLM cost)
1926 |         try:
1927 |             card = oracle_dialogue_engine.detect_action_card(text)
1928 |             if card:
1929 |                 resp_data["action_card"] = card
1930 |                 logger.info(f"[CHAT] Action card triggered: {card['id']}")
1931 |         except Exception as _card_err:
1932 |             logger.warning(f"[CHAT] Action card detection error: {_card_err}")
1933 |         return jsonify(resp_data)
1934 | 
1935 |     # Existing: return video directly
1936 |     return generate_inline(result["text"])
1937 | 
1938 | 
1939 | @app.route("/oracle/session", methods=["GET"])
1940 | def oracle_session_info():
1941 |     return jsonify(oracle_dialogue_engine.get_session_info(request.args.get("session_id","anon")))
1942 | 
1943 | 
1944 | @app.route("/oracle/session/reset", methods=["POST"])
1945 | def oracle_session_reset():
1946 |     data = request.get_json() or {}
1947 |     sid = data.get("session_id", "anon")
1948 | 
1949 |     # ── Phase 3: Save visitor memory before clearing session ───────────
1950 |     session = oracle_dialogue_engine._sessions.get(sid, {})
1951 |     fingerprint = session.get("fingerprint")
1952 |     if fingerprint and session.get("history"):
1953 |         try:
1954 |             from oracle_memory import save_visitor, generate_session_summary
1955 |             api_key = _get_anthropic_key()
1956 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
1957 |             flow = session.get("setup_flow", {})
1958 |             prev_memory = session.get("visitor_memory", {})
1959 |             # Build recent_turns from session history
1960 |             _hist = session.get("history", [])
1961 |             _turns = []
1962 |             for i in range(0, min(6, len(_hist)), 2):
1963 |                 if i+1 < len(_hist):
1964 |                     _turns.append({
1965 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1966 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1967 |                     })
1968 |             save_visitor(fingerprint, {
1969 |                 "personality": session.get("personality", "AMIABLE"),
1970 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
1971 |                 "setup_device": flow.get("device"),
1972 |                 "setup_step": flow.get("step", 0),
1973 |                 "topics_seen": session.get("topics_discussed", []),
1974 |                 "products_shown": session.get("products_mentioned", []),
1975 |                 "recent_turns": list(reversed(_turns)),
1976 |             })
1977 |             logger.info(f"[MEMORY] Saved visitor memory for session {sid}")
1978 |         except Exception as e:
1979 |             logger.warning(f"[MEMORY] Save failed on reset: {e}")
1980 | 
1981 |     oracle_dialogue_engine.reset_session(sid)
1982 |     return jsonify({"status": "reset"})
1983 | 
1984 | 
1985 | @app.route("/oracle/session/save", methods=["POST"])
1986 | def oracle_session_save():
1987 |     """Save session memory on page unload without clearing the session."""
1988 |     data = request.get_json() or {}
1989 |     sid = data.get("session_id", "anon")
1990 |     session = oracle_dialogue_engine._sessions.get(sid, {})
1991 |     fingerprint = session.get("fingerprint")
1992 |     if fingerprint and session.get("history"):
1993 |         try:
1994 |             from oracle_memory import save_visitor, generate_session_summary
1995 |             api_key = _get_anthropic_key()
1996 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
1997 |             flow = session.get("setup_flow", {})
1998 |             prev_memory = session.get("visitor_memory", {})
1999 |             topics = list(session.get("topics_discussed", []))
2000 |             # Build recent_turns from session history
2001 |             _hist = session.get("history", [])
2002 |             _turns = []
2003 |             for i in range(0, min(6, len(_hist)), 2):
2004 |                 if i+1 < len(_hist):
2005 |                     _turns.append({
2006 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
2007 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
2008 |                     })
2009 |             save_visitor(fingerprint, {
2010 |                 "personality": session.get("personality", "AMIABLE"),
2011 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
2012 |                 "setup_device": flow.get("device"),
2013 |                 "setup_step": flow.get("step", 0),
2014 |                 "topics_seen": topics,
2015 |                 "products_shown": session.get("products_mentioned", []),
2016 |                 "recent_turns": list(reversed(_turns)),
2017 |             })
2018 |             logger.info(f"[MEMORY] Saved session {sid} on unload — {len(topics)} topics, summary len={len(summary)}")
2019 |         except Exception as e:
2020 |             logger.warning(f"[MEMORY] Save on unload failed: {e}")
2021 |     return jsonify({"status": "saved"})
2022 | 
2023 | 
2024 | @app.route("/oracle/intent", methods=["POST"])
2025 | def oracle_intent():
2026 |     """Classify user transcript to an intent."""
2027 |     data = request.get_json()
2028 |     if not data or not data.get("transcript"):
2029 |         return jsonify({"error": "transcript required"}), 400
2030 | 
2031 |     intent, confidence = classify_intent(data["transcript"])
2032 | 
2033 |     # If low confidence, try Claude Haiku for better classification
2034 |     if confidence < 0.6:
2035 |         try:
2036 |             api_key = _get_anthropic_key()
2037 |             if api_key:
2038 |                 resp = http_requests.post(
2039 |                     "https://api.anthropic.com/v1/messages",
2040 |                     headers={
2041 |                         "x-api-key": api_key,
2042 |                         "anthropic-version": "2023-06-01",
2043 |                         "content-type": "application/json",
2044 |                     },
2045 |                     json={
2046 |                         "model": "claude-haiku-4-5-20251001",
2047 |                         "max_tokens": 30,
2048 |                         "messages": [{
2049 |                             "role": "user",
2050 |                             "content": (
2051 |                                 f"Classify this user message into ONE intent from this list: "
2052 |                                 f"{', '.join(INTENT_PATTERNS.keys())}, GREETING, UNKNOWN. "
2053 |                                 f"Reply with ONLY the intent name.\n\nMessage: {data['transcript']}"
2054 |                             ),
2055 |                         }],
2056 |                     },
2057 |                     timeout=10,
2058 |                 )
2059 |                 if resp.status_code == 200:
2060 |                     ai_intent = resp.json()["content"][0]["text"].strip().upper()
2061 |                     valid = set(INTENT_PATTERNS.keys()) | {"GREETING", "UNKNOWN", "SOVEREIGNTY_ASSESSMENT"}
2062 |                     if ai_intent in valid:
2063 |                         intent = ai_intent
2064 |                         confidence = 0.75
2065 |         except Exception as e:
2066 |             logger.warning(f"Intent AI fallback failed: {e}")
2067 | 
2068 |     return jsonify({
2069 |         "intent": intent,
2070 |         "confidence": round(confidence, 2),
2071 |         "cached": oracle_cache_manager.get_cached_response(intent) is not None,
2072 |     })
2073 | 
2074 | 
2075 | # ═══════════════════════════════════════════════════════════════════════
2076 | # SENTENCE CHUNKING FOR LONG TEXT
2077 | # ═══════════════════════════════════════════════════════════════════════
2078 | 
2079 | _chunk_sessions = {}
2080 | _chunk_lock = threading.Lock()
2081 | 
2082 | 
2083 | @app.route("/oracle/chunks/<session_id>")
2084 | def oracle_chunks(session_id):
2085 |     """Poll for additional chunks from a long-text generation."""
2086 |     session = _chunk_sessions.get(session_id)
2087 |     if not session:
2088 |         return jsonify({"error": "Session not found"}), 404
2089 | 
2090 |     return jsonify({
2091 |         "session_id": session_id,
2092 |         "chunks_ready": len(session["paths"]),
2093 |         "total_chunks": session["total"],
2094 |         "complete": session["complete"],
2095 |         "paths": [f"/oracle/chunks/{session_id}/{i}" for i in range(len(session["paths"]))],
2096 |     })
2097 | 
2098 | 
2099 | @app.route("/oracle/chunks/<session_id>/<int:idx>")
2100 | def oracle_chunk_file(session_id, idx):
2101 |     """Serve a specific chunk file."""
2102 |     session = _chunk_sessions.get(session_id)
2103 |     if not session or idx >= len(session["paths"]):
2104 |         return jsonify({"error": "Chunk not ready"}), 404
2105 |     return send_file(session["paths"][idx], mimetype="video/mp4")
2106 | 
2107 | 
2108 | # ═══════════════════════════════════════════════════════════════════════
2109 | # TTS PROVIDER STATUS
2110 | # ═══════════════════════════════════════════════════════════════════════
2111 | 
2112 | @app.route("/avatar/tts-provider", methods=["GET"])
2113 | def avatar_tts_provider():
2114 |     """Report which TTS provider is active."""
2115 |     if _AVATAR_KOKORO_READY:
2116 |         return jsonify({
2117 |             "provider": "kokoro",
2118 |             "voice": "af_heart",
2119 |             "backend": "cuda:1",
2120 |             "sample_rate": 24000,
2121 |             "ready": True,
2122 |         })
2123 |     return jsonify({
2124 |         "provider": "elevenlabs_fallback",
2125 |         "reason": "Kokoro not loaded or init failed",
2126 |         "ready": False,
2127 |     })
2128 | 
2129 | 
2130 | # ═══════════════════════════════════════════════════════════════════════
2131 | # MAIN
2132 | # ═══════════════════════════════════════════════════════════════════════
2133 | 
2134 | if __name__ == "__main__":
2135 |     print(f"\n{'='*60}")
2136 |     print("  ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks")
2137 |     print(f"  Port: {PORT}")
2138 |     print(f"  Device: {DEVICE}")
2139 |     print(f"  Avatar: {AVATAR_SOURCE}")
2140 |     print(f"  FPS: {DEFAULT_FPS}")
2141 |     print(f"  Encoding: CRF 28, preset ultrafast, 512px output")
2142 |     print(f"  Features: FP16, cv2_sharpen, mediapipe_blinks, head_movement")
2143 |     print(f"  Vision: {'enabled' if os.environ.get('GEMINI_API_KEY') else 'disabled'}")
2144 |     print(f"  Max audio: {MAX_AUDIO_SECONDS}s | Lock timeout: {LOCK_TIMEOUT}s")
2145 |     print(f"{'='*60}\n")
2146 | 
2147 |     # Load all models via registry (FP16 on GPU 1)
2148 |     logger.info("Initializing ModelRegistry...")
2149 |     reg = ModelRegistry.get()
2150 | 
2151 |     if reg.wav2lip_model is None:
2152 |         logger.error("Failed to load Wav2Lip model. Exiting.")
2153 |         sys.exit(1)
2154 | 
2155 |     if reg.avatar_face_coords is None:
2156 |         logger.error("No face detected in avatar. Exiting.")
2157 |         sys.exit(1)
2158 | 
2159 |     logger.info("Face enhancer: CV2 sharpen-only (no GFPGAN)")
2160 | 
2161 |     # Load Kokoro af_heart TTS on cuda:1 (~2-3s per utterance)
2162 |     logger.info("[STARTUP] Initializing Kokoro af_heart TTS on cuda:1...")
2163 |     _init_avatar_kokoro()
2164 | 
2165 |     # Auto-warmup (non-blocking — runs in background thread so Flask can start immediately)
2166 |     def _warmup_background():
2167 |         logger.info("[WARMUP] Running pipeline warmup in background...")
2168 |         warmup_start = time.time()
2169 |         try:
2170 |             import wave
2171 |             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
2172 |                 with wave.open(tmp.name, "w") as wf:
2173 |                     wf.setnchannels(1)
2174 |                     wf.setsampwidth(2)
2175 |                     wf.setframerate(16000)
2176 |                     wf.writeframes(b"\x00\x00" * 8000)
2177 |                 warmup_wav = tmp.name
2178 |             frames = wav2lip_generate(warmup_wav, DEFAULT_FPS)
2179 |             if frames:
2180 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
2181 |             os.unlink(warmup_wav)
2182 |             logger.info(
2183 |                 f"[WARMUP] Pipeline ready in {time.time()-warmup_start:.1f}s "
2184 |                 f"({len(frames)} frames)"
2185 |             )
2186 |         except Exception as e:
2187 |             logger.warning(f"[WARMUP] Failed (non-fatal): {e}")
2188 |     threading.Thread(target=_warmup_background, daemon=True).start()
2189 | 
2190 |     dev_idx = int(DEVICE.split(':')[1]) if ':' in DEVICE else 0
2191 |     logger.info(
2192 |         f"[WARMUP] GPU {dev_idx} VRAM: {torch.cuda.memory_allocated(dev_idx)/1024**3:.1f}GB used"
2193 |     )
2194 | 
2195 |     # Generate idle loop if not already present
2196 |     generate_idle_loop()
2197 | 
2198 |     # Phase 2: Start cache warming in background (delayed 60s to allow incoming requests)
2199 |     logger.info("[STARTUP] Oracle cache warmer will start in 60s...")
2200 |     def _delayed_warmup():
2201 |         time.sleep(60)
2202 |         logger.info("[STARTUP] Cache warmup starting now (60s delay complete)")
2203 |         oracle_cache_manager.warm_cache()
2204 |     threading.Thread(target=_delayed_warmup, daemon=True).start()
2205 |     oracle_cache_manager.start_background_warmer()
2206 | 
2207 |     # Phase 3: Start intelligence feed
2208 |     logger.info("[STARTUP] Starting intelligence feed...")
2209 |     oracle_intelligence_feed.start_intelligence_feed()
2210 | 
2211 |     logger.info(f"Avatar server v2 ready on port {PORT}")
2212 |     app.run(host="0.0.0.0", port=PORT, threaded=True)
2213 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
