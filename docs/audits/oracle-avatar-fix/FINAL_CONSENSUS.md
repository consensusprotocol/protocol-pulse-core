# CONSENSUS REPORT — ORACLE-AVATAR-FIX — CYCLE 2
Generated: 2026-03-24 12:02
Models: gemini, grok (+1 failed: gpt4o rate-limited)

---

## SCORES

| Subsystem       | Gemini  | GPT-4o | Grok   | Consensus |
|-----------------|---------|--------|--------|-----------|
| Backend Logic   | 50/100  | N/A    | 70/100 | **60/100** |
| Frontend/UI     | N/A     | N/A    | N/A    | **N/A**    |
| Error Handling  | 45/100  | N/A    | 55/100 | **50/100** |
| Security        | 20/100  | N/A    | 50/100 | **35/100** |
| Performance     | 40/100  | N/A    | 60/100 | **50/100** |
| Law Compliance  | 75/100  | N/A    | 75/100 | **75/100** |
| World-Class Gap | 30/100  | N/A    | 55/100 | **42/100** |
| **OVERALL**     | **43/100** | N/A | **61/100** | **52/100** |

> **Scoring Note:** Gemini's deeper synthesis produced significantly lower scores, particularly on security (20 vs. 50) and world-class gap (30 vs. 55). The consensus leans toward Gemini's more conservative assessment on security, as the reasoning is more specific and the risks more thoroughly enumerated. The overall consensus of **52/100** reflects a system that is technically functional but structurally unfit for production.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### 1. No Rate Limiting on Any Endpoint
- **What:** Every endpoint — `/generate`, `/oracle/chat`, `/vision/analyze`, etc. — is unprotected against volumetric abuse. GPU-bound and paid-API-consuming operations can be triggered without restriction.
- **File/Line:** `oracle/avatar_server.py` — Lines `762`, `1651`, `961`, `1406`
- **Fix:** Implement per-IP rate limiting using Flask-Limiter or a Redis token-bucket. Set strict limits on expensive endpoints (e.g., 5 req/min per IP for `/generate`, 20 req/min for chat endpoints).

### 2. No Authentication on Sensitive Endpoints
- **What:** Endpoints that consume GPU resources and paid third-party APIs (ElevenLabs, Anthropic) have zero authentication. Any actor with network access can drain compute budget and incur costs.
- **File/Line:** `oracle/avatar_server.py` — Lines `762`, `1535`, `1651`
- **Fix:** Add bearer token or API key validation middleware. At minimum, a static secret checked against `Authorization` header is required before any endpoint is production-exposed.

### 3. Silent Exception Swallowing (`except Exception: pass`)
- **What:** Multiple critical paths silently swallow exceptions with no logging, making failures invisible in production monitoring.
  - Line `113`: Eye landmark detection in `_detect_face_cpu`
  - Lines `397–399`: Blink post-processing in `post_process_frames`
  - Lines `1157–1159`: Frame sharpening in `_generate_chunk`
- **File/Line:** `oracle/avatar_server.py` — Lines `113`, `397`, `1157`
- **Fix:** Replace every `except Exception: pass` with `logger.error("Context message", exc_info=True)` at minimum. For non-fatal paths, degrade gracefully but always log.

### 4. Unvalidated User Input in `/generate`
- **What:** The `audio_base64` field is decoded and passed to downstream processing without validation of size, encoding correctness, or content type. The `text` field has no length or content guards.
- **File/Line:** `oracle/avatar_server.py` — Lines `762–919`
- **Fix:** Validate `audio_base64` is valid base64 before decoding. Enforce max lengths for `text` (e.g., 2000 chars). Reject malformed inputs with a `400` before any processing begins.

### 5. Race Condition in `_load_avatar_face` (Double-Checked Locking Flaw)
- **What:** Two concurrent requests for the same new avatar both miss the initial cache check (line `132`), proceed to load the image from disk and run expensive CPU face detection *outside* the lock, then both write to cache. This is a thundering herd problem that causes redundant CPU spikes.
- **File/Line:** `oracle/avatar_server.py` — Lines `131–156`
- **Fix:** Move the image load and `_detect_face_cpu` call *inside* the lock block. Check the cache a second time inside the lock before doing the work (true double-checked locking pattern).

### 6. Resource Leaks: `_stream_sessions` and `_chunk_sessions`
- **What:** These global dictionaries are populated when clients start stream/chunk sessions but are never cleaned up. Abandoned sessions accumulate indefinitely, consuming memory and leaving orphaned temp directories on disk. This is a guaranteed server crash over time.
- **File/Line:** `oracle/avatar_server.py` — Lines `1109`, `1983`
- **Fix:** Implement a background cleanup thread (daemon, runs every 60–300 seconds) that evicts entries older than a configurable TTL (e.g., 10 minutes). On eviction, delete associated temp files/directories.

---

## MAJORITY FINDINGS (both models agree — same threshold at 2/2)

> *Note: With only two functioning models this cycle, all unanimous findings above represent majority findings as well. The items below are findings where both models flagged the category but with meaningful differences in framing or specificity.*

### 7. `_render_jobs` Memory Leak
- **What:** The `_render_jobs` dictionary (line `198`) holds job results — potentially large video byte arrays — indefinitely. It is only cleaned up if the client polls the status endpoint. A fire-and-forget client leaks unboundedly.
- **File/Line:** `oracle/avatar_server.py` — Line `198`
- **Fix:** Apply the same TTL cleanup mechanism as `_stream_sessions`. Evict completed/failed job entries after a configurable retention period (e.g., 5 minutes post-completion).

### 8. Inefficient Semaphore Usage in `generate_inline`
- **What:** The code acquires the semaphore, immediately releases it to check GPU availability, then re-acquires it for actual work. This creates a race window where another request can grab the semaphore between the check and the work.
- **File/Line:** `oracle/avatar_server.py` — Lines `1439–1442`
- **Fix:** Acquire the semaphore once and hold it for the full critical section. Remove the non-blocking "check" pattern; use a direct blocking acquire with a timeout instead.

### 9. No Retry Logic on External API Calls
- **What:** External API calls (ElevenLabs at line `655`, Anthropic at line `1651`) have no retry logic. Transient network errors cause immediate failures that propagate to the user with no recovery attempt.
- **File/Line:** `oracle/avatar_server.py` — Lines `655`, `1651`
- **Fix:** Wrap external API calls with exponential backoff retry (2–3 attempts, starting at 500ms). Use `tenacity` or a manual implementation. Do not retry on 4xx client errors.

### 10. Audio Duration `ffprobe` Failure Defaults to 0.0 Silently
- **What:** If `ffprobe` fails or returns empty output during the audio duration check, `audio_duration_sec` defaults to `0.0` with no error response. This allows malformed audio to proceed into the Wav2Lip pipeline.
- **File/Line:** `oracle/avatar_server.py` — Lines `817–829`
- **Fix:** If `ffprobe` fails or returns a non-parseable result, return a `400` error to the client explaining the audio could not be validated. Do not proceed with `duration == 0.0`.

---

## UNIQUE INSIGHTS (single-model findings — evaluated individually)

### From Gemini Only:

**A. Inconsistent & Leaky File Management Across All Endpoints**
- **What:** `/generate` uses both `finally` and `@after_this_request` for cleanup (lines `919`, `890`), creating confusion and potential video file leaks on mid-request errors. `_generate_chunk` has no cleanup for intermediate audio files on error.
- **Assessment:** **IMPLEMENT.** This is a real and specific defect, not theoretical. The inconsistency across request handlers is a maintenance liability and an active resource leak vector. Standardize on a context-manager or `finally`-only cleanup pattern across all routes.

**B. Concurrency Model Contradiction: `audio_first` Jobs vs. Synchronous `/generate`**
- **What:** Conversational `audio_first` jobs from `/oracle/chat` queue behind long-running synchronous `/generate` requests on the same `_render_semaphore`. A user in a live chat can wait minutes because a video generation job holds the semaphore.
- **Assessment:** **IMPLEMENT.** This is an architectural flaw that will directly degrade the perceived quality of the conversational feature. At minimum, use two separate semaphores (or a priority queue) — one for interactive/chat paths and one for batch video generation.

**C. Dynamic `sys.path` Manipulation Inside Functions**
- **What:** `sys.path` is modified inside function bodies (lines `92–94`, `237–239`) to enable imports. This obscures dependencies, can cause import ordering issues, and is slower than top-level imports.
- **Assessment:** **IMPLEMENT (P2).** Not a blocker, but it is a code quality debt that will cause confusion. Refactor imports to the module top level or use proper package installation.

### From Grok Only:

**D. Hardcoded Audio-Video Sync Offset (`-itsoffset 0.08`)**
- **What:** The A/V sync offset in `frames_to_video` is hardcoded. Different TTS engines produce different latencies, so a single hardcoded value will produce visible sync drift on some providers.
- **Assessment:** **INVESTIGATE FURTHER.** This likely works acceptably for the primary TTS path but will degrade quality when ElevenLabs is used as fallback vs. Kokoro. Make it a configurable constant per TTS provider rather than a global hardcoded value.

**E. No Validation of Avatar Source File Path**
- **What:** File paths in `AVATAR_SOURCES` are used without sanitization before file read in `_load_avatar_face` (line `138`). A misconfigured or attacker-controlled source could trigger path traversal.
- **Assessment:** **IMPLEMENT.** Validate that resolved paths are within an expected base directory using `os.path.realpath` and a prefix check before any file operation.

**F. No Timeout on Long-Running Background Threads (`render_async`)**
- **What:** Background rendering threads (line `1821`) have no explicit timeout. A hung thread (stalled ffmpeg, dead API connection) accumulates silently and exhausts the thread pool.
- **Assessment:** **IMPLEMENT.** Add a maximum wall-clock timeout to `render_async`. On timeout, cancel the job, clean up temp files, and update the job status to `failed` so the client can receive a meaningful error on next poll.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1: Security Severity Score (Gemini: 20/100 vs. Grok: 50/100)
- **Gemini's position:** No auth + no rate limiting on GPU/paid endpoints = P0 critical, scores security at 20/100.
- **Grok's position:** Same issues flagged but scored 50/100, implying moderate rather than critical severity.
- **Tiebreaker:** **Gemini is correct.** A service that exposes GPU compute and paid API calls (ElevenLabs, Anthropic) to anonymous, unlimited traffic on the public internet cannot score above 25/100 on security. The potential for financial abuse alone constitutes a critical vulnerability. This is not a theoretical risk — it is an immediate, exploitable condition. Grok's 50/100 materially underrepresents the severity.

### Conflict 2: Overall Score (Gemini: 43/100 vs. Grok: 61/100)
- **Gemini's position:** Resource leaks + auth gaps + concurrency flaws = 43/100.
- **Grok's position:** Functional pipeline despite the gaps = 61/100.
- **Tiebreaker:** **Gemini's framing is more appropriate for a production readiness assessment.** The question is not "does this work in a demo?" but "can this be shipped safely?" A server guaranteed to crash from resource leaks and exploitable from day one for financial abuse scores below 50. Consensus overall: **52/100** as a balanced midpoint, with the understanding that a P0 security fix should move it to ~70.

---

## VALIDATED STRENGTHS (confirmed by both models — do NOT change)

1. **TTS Provider Fallback Architecture:** The Kokoro → ElevenLabs fallback chain is structurally sound. Both models found the intent correct, with only the error messaging needing improvement — not the pattern itself.

2. **Environment Variable Secret Management:** API keys are loaded from environment variables, not hardcoded. Both models confirmed this as correct practice.

3. **`_render_semaphore` Concurrency Concept:** The idea of limiting concurrent GPU renders with a semaphore is architecturally correct. The implementation details (count, fairness) need work, but the pattern is right.

4. **`generate_inline` Generator Pattern for File Cleanup:** The generator-based cleanup pattern in `generate_inline` (line `1493`) was identified by Gemini as the most robust cleanup approach in the codebase. This pattern should be *expanded* to other routes, not replaced.

5. **Wav2Lip Adaptive Batch Size:** The adaptive batch size logic for short vs. long audio (line `268`) is a correct performance optimization and was not challenged by either model.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|-----|--------|-------|
| LAW 1: Technology Stack (Python 3.12, Flask, SQLAlchemy) | **COMPLIANT** | Both models confirmed. No violations observed. |
| LAW 2: Database Indexing | **UNVERIFIABLE** | No DB queries visible in reviewed code. Cannot confirm or deny. Flag for separate review. |
| LAW 3: UI Technology Restrictions (no Three.js/WebGL/Canvas) | **COMPLIANT** | No frontend code in scope. Backend confirmed clean. |

**Final Determination:** No confirmed law violations. LAW 2 compliance requires a separate audit of the database access layer, which was not in scope for this review.

---

## SECURITY CONSENSUS

Priority order of confirmed security issues (both models):

1. **[P0] No Authentication** — All endpoints publicly accessible. Financial and compute abuse is trivially possible today.
2. **[P0] No Rate Limiting** — Unlimited requests to GPU-bound and paid-API endpoints. One actor can starve all other users and drain API budget.
3. **[P1] Unvalidated User Input** — `audio_base64`, `text`, and avatar paths are processed without sanitization. Risk of crashes, path traversal, and resource exhaustion.
4. **[P1] Avatar Path Traversal** — File paths read without prefix validation (Grok, unique). Risk of reading arbitrary files from the server filesystem.
5. **[P2] Secrets in `.env` File** — Fallback to `.env` file reading noted by GPT-4o (Cycle 1). The file must be secured with appropriate filesystem permissions and excluded from any container image layers.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a production-quality service:

1. **Session/Resource Lifecycle Management:** Both models flagged the absence of TTL-based cleanup for sessions, jobs, and temp files. A world-class service never leaks resources and has explicit lifecycle contracts for every stateful object.

2. **Observability and Debuggability:** Both models flagged silent exception swallowing. A world-class service has structured logging with correlation IDs, exception traces, and metrics on every error path. You cannot operate what you cannot observe.

3. **Graceful Degradation Under Load:** Both models flagged the lack of queuing, fair scheduling, and user feedback when the GPU semaphore is saturated. A world-class service tells users their position in queue, provides estimated wait times, and does not silently timeout.

4. **Consistent Error Response Contracts:** Both models noted inconsistent error handling across routes (some return JSON, behavior varies mid-request). A world-class API has a uniform error response schema for every failure mode.

5. **Retry Resilience on External Dependencies:** Both models noted the lack of retries on ElevenLabs and Anthropic calls. A world-class service treats external dependencies as unreliable and builds retry, circuit-breaking, and fallback logic accordingly.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Add authentication (bearer token / API key) to all endpoints
            | oracle/avatar_server.py:762,1651,961,1406,1535
            | models: both | Without this, any actor can drain compute and API budget today.

P0 CRITICAL | Implement per-IP rate limiting on all endpoints (Flask-Limiter or Redis)
            | oracle/avatar_server.py:762,1651,961,1406
            | models: both | GPU + paid API endpoints are fully open to volumetric abuse.

P0 CRITICAL | Implement TTL-based garbage collection for _stream_sessions, _chunk_sessions, _render_jobs
            | oracle/avatar_server.py:1109,1983,198
            | models: both (Gemini primary) | Guaranteed memory/disk exhaustion → server crash over time.

P1 HIGH     | Fix _load_avatar_face race condition — move image load + face detect inside lock
            | oracle/avatar_server.py:131-156
            | models: both | Thundering herd on new avatar loads; negates cache benefit under concurrent load.

P1 HIGH     | Replace all `except Exception: pass` with `logger.error(..., exc_info=True)`
            | oracle/avatar_server.py:113,397,1157
            | models: both | Silent failures make production debugging impossible.

P1 HIGH     | Validate and sanitize all user inputs before processing in /generate
            | oracle/avatar_server.py:762-919
            | models: both | Base64, text length, content-type checks required before any downstream work.

P1 HIGH     | Validate avatar source file paths against expected base directory
            | oracle/avatar_server.py:138
            | models: grok (unique, high confidence) | Path traversal risk on misconfigured/attacker-controlled sources.

P1 HIGH     | Fix audio duration check: return 400 on ffprobe failure, do not default to 0.0
            | oracle/avatar_server.py:817-829
            | models: both | Malformed audio proceeds into Wav2Lip pipeline on ffprobe failure.

P1 HIGH     | Fix semaphore usage in generate_inline — single acquire, hold for full critical section
            | oracle/avatar_server.py:1439-1442
            | models: both (Gemini primary) | Race window between check-acquire and work-acquire allows queue bypass.

P1 HIGH     | Add background thread timeout to render_async — update job to 'failed' on timeout
            | oracle/avatar_server.py:1821
            | models: grok (unique, high confidence) | Hung threads accumulate silently, exhausting thread pool.

P1 HIGH     | Add retry with exponential backoff on ElevenLabs and Anthropic API calls
            | oracle/avatar_server.py:655,1651
            | models: both | Transient errors cause immediate user-facing failure with no recovery attempt.

P1 HIGH     | Separate semaphore pools for interactive (chat) vs. batch (video gen) workloads
            | oracle/avatar_server.py:203
            | models: gemini (unique, high confidence) | Live chat blocked by batch renders = severe UX degradation.

P2 MEDIUM   | Standardize file cleanup to generator/context-manager pattern across all routes
            | oracle/avatar_server.py:890,919,1157
            | models: gemini | Mixed finally/after_this_request patterns cause leaks on error paths.

P2 MEDIUM   | Make A/V sync offset (-itsoffset) configurable per TTS provider, not hardcoded
            | oracle/avatar_server.py:430
            | models: grok | Sync drift observable when ElevenLabs vs. Kokoro produces different latencies.

P2 MEDIUM   | Move sys.path manipulations out of function bodies to module-level imports
            | oracle/avatar_server.py:92-94,237-239
            | models: gemini | Obscures dependencies, degrades import performance, maintenance liability.

P2 MEDIUM   | Standardize error response schema (code, message, request_id) across all routes
            | oracle/avatar_server.py: all routes
            | models: both (implied) | Inconsistent error contracts make client-side handling fragile.
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY.**

The code implements a technically impressive and functionally plausible pipeline for lip-synced avatar generation. The core Wav2Lip integration, TTS fallback architecture, and semaphore-based GPU concurrency control are structurally sound starting points.

However, the system has **three absolute blockers** that are not debatable:

1. **It will be exploited immediately.** Zero authentication and zero rate limiting on endpoints that call paid APIs and consume GPU compute is a critical security failure. This is not a theoretical risk — it is an immediate exploit condition the moment the service is internet-accessible.

2. **It will crash within days under real load.** The `_stream_sessions`, `_chunk_sessions`, and `_render_jobs` dictionaries leak memory and disk space with no cleanup mechanism. Under any non-trivial usage, this is a guaranteed crash.

3. **It is unmonitorable in production.** Silent exception swallowing across multiple critical paths means failures will be invisible until user reports surface them. Production operations require observability.

Fix the three P0 items and the P1 security items before any further review. After those are resolved, the system's performance and quality characteristics warrant a fresh audit cycle.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/oracle-avatar-fix_CONSENSUS_C2.md.

This is the FINAL PASS for oracle-avatar-fix.
The feature was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add authentication (bearer token/API key) to all endpoints
            | oracle/avatar_server.py:762,1651,961,1406,1535
            | Any actor can drain GPU and paid API budget today. Block immediately.

P0 CRITICAL | Implement per-IP rate limiting (Flask-Limiter or Redis token bucket)
            | oracle/avatar_server.py:762,1651,961,1406
            | 5 req/min on /generate, 20 req/min on chat endpoints minimum.

P0 CRITICAL | Add TTL-based garbage collection background thread for _stream_sessions,
            | _chunk_sessions, _render_jobs — evict after 10min, delete temp files
            | oracle/avatar_server.py:1109,1983,198
            | Guaranteed memory/disk exhaustion without this.

P1 HIGH     | Fix _load_avatar_face race condition: move image load + _detect_face_cpu
            | call INSIDE the lock. Check cache again inside lock before doing work.
            | oracle/avatar_server.py:131-156

P1 HIGH     | Replace every `except Exception: pass` with logger.error(msg, exc_info=True)
            | oracle/avatar_server.py:113,397,1157
            | Degrade gracefully but always log.

P1 HIGH     | Validate all user inputs in /generate before processing:
            | - Verify audio_base64 is valid base64 before decode
            | - Enforce max text length (

---

# WINNER DETERMINATION

# WINNER: **Gemini** — Gemini consistently identified the most severe, production-breaking issues with the greatest specificity, including the memory/disk leak in `_stream_sessions` and `_chunk_sessions`, the `_render_jobs` unbounded growth bug, and the flawed double-checked locking pattern — none of which were surfaced with comparable precision by the other models. The consensus scoring explicitly deferred to Gemini's more conservative and better-enumerated security assessment (20/100 vs Grok's 50/100), validating that Gemini's findings proved most accurate and most consequential in Cycle 2.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered implementation list. Items ranked by: severity × likelihood × blast radius.

---

## 🔴 P0 — IMPLEMENT BEFORE ANY DEPLOYMENT

### 1. Authentication on All Sensitive Endpoints
- **Why first:** Zero auth means any network-accessible actor can consume GPU, ElevenLabs credits, and Anthropic tokens without restriction. This is not a hardening issue — it is a prerequisite for operating.
- **Lines:** `762`, `1651`, `961`, `1406`, `1447`
- **Action:** Add a middleware decorator (e.g., `@require_api_key`) that validates a Bearer token against an environment variable or secrets store. Apply to every route that touches GPU, TTS, or LLM APIs. Return `401` immediately otherwise.

---

### 2. Rate Limiting on GPU/Paid-API Endpoints
- **Why second:** Even with auth, a single authenticated user can exhaust GPU capacity or burn API budgets. This is a separate control plane from auth.
- **Lines:** `762`, `961`, `1406`
- **Action:** Deploy Flask-Limiter with Redis backend. Hard limits: `/generate` → 5 req/min/IP, `/oracle/chat` → 20 req/min/IP, `/vision/analyze` → 10 req/min/IP. Return `429` with `Retry-After` header on breach.

---

### 3. `_stream_sessions` and `_chunk_sessions` Memory + Disk Leak
- **Why third:** Abandoned sessions accumulate forever. Temp directories and in-memory state grow without bound. This is a guaranteed server failure on any production traffic pattern — it is a question of when, not if.
- **Lines:** `1109`, `1983`
- **Action:** Implement a TTL-based eviction thread that runs every 60 seconds. Any session older than `SESSION_TTL` (e.g., 300s) with no recent activity is removed from the dict and its temp directory is deleted via `shutil.rmtree`. Use `threading.Timer` or a lightweight scheduler (APScheduler). Add a max session cap (e.g., 50 concurrent) that returns `503` when exceeded.

---

### 4. `_render_jobs` Unbounded Memory Growth
- **Why fourth:** Completed jobs holding large video byte arrays are never evicted unless the client polls. A fire-and-forget client permanently leaks potentially hundreds of MB per job.
- **Lines:** `198`
- **Action:** Apply the same TTL eviction pattern. Jobs older than 10 minutes after completion are deleted. Add a hard cap on `_render_jobs` size (e.g., 20 entries). When cap is hit, evict oldest completed job before inserting a new one.

---

## 🟠 P1 — IMPLEMENT WITHIN FIRST SPRINT

### 5. Silent Exception Swallowing — Three Locations
- **Why:** Silent `except Exception: pass` blocks are active landmines. They cause symptoms (bad video quality, missing blinks, inconsistent output) with no diagnostic path. These are already causing undetected failures in production-equivalent runs.
- **Lines:** `113`, `397–399`, `1157–1159`
- **Action:**
  - Line `113`: Replace `pass` with `logger.warning("Eye landmark detection failed for avatar %s", avatar_id, exc_info=True)`.
  - Lines `397–399`: Replace `result = frame` bare rescue with `logger.error("Post-process frame failed", exc_info=True); result = frame`.
  - Lines `1157–1159`: Replace `pass` with `logger.warning("Sharpening failed on chunk frame %d", frame_idx, exc_info=True)`.

---

### 6. Thundering Herd in `_load_avatar_face` (Double-Checked Locking Flaw)
- **Why:** Multiple concurrent requests for the same new avatar each independently load from disk and run CPU face detection outside the lock, then redundantly write to cache. Under any real load pattern this causes CPU spikes and latency degradation.
- **Lines:** `131–136`, `153–155`, `1750`
- **Action:** Replace the pattern with a per-avatar `threading.Event` or use a `_loading_avatars` set protected by the existing lock. Any thread finding an avatar "currently being loaded" waits on the event rather than re-executing the detection. Pseudocode:
  ```python
  with _avatar_face_cache_lock:
      if avatar_id in _avatar_face_cache:
          return _avatar_face_cache[avatar_id]
      if avatar_id in _avatar_loading:
          event = _avatar_loading[avatar_id]
      else:
          event = threading.Event()
          _avatar_loading[avatar_id] = event
          event = None  # this thread does the work
  if event:
      event.wait(timeout=30)
      return _avatar_face_cache.get(avatar_id)
  # do the expensive load, then set event
  ```

---

### 7. `ffprobe` Silent Failure Defaulting to Zero Duration
- **Why:** If `ffprobe` fails or returns empty output, `audio_duration_sec` defaults to `0.0` and malformed audio proceeds through the entire pipeline, potentially crashing Wav2Lip downstream in an unrecoverable way.
- **Lines:** `817–829`
- **Action:** If `ffprobe` returns empty or fails to parse, immediately return a `400` response with message: `"Audio validation failed: could not determine duration. File may be corrupt."` Do not allow the pipeline to continue with `duration = 0.0`.

---

### 8. TTS Fallback Fails Without User-Visible Error
- **Why:** If both Kokoro and ElevenLabs fail, the error is logged but the user receives only a generic `500`. This is a poor failure mode for a user-facing API.
- **Lines:** `790–805`
- **Action:** Catch the dual-failure case explicitly. Return a structured `503` response:
  ```json
  {"error": "tts_unavailable", "message": "All TTS providers failed. Try again later.", "retry_after": 30}
  ```

---

## 🟡 P2 — IMPLEMENT WITHIN FIRST MONTH

### 9. Render Semaphore Has No Queue Fairness or Position Visibility
- **Lines:** `203`, `839`
- **Action:** Replace the raw `Semaphore(2)` with a queue-aware wrapper that tracks position. Return queue position in the `202 Accepted` response so clients can implement informed backoff. Add a configurable `MAX_QUEUE_DEPTH` that returns `503` immediately when exceeded rather than silently timing out.

---

### 10. `generate_inline` Semaphore Acquire-Release-Reacquire Pattern
- **Lines:** `1442`
- **Action:** Remove the speculative acquire/release. Check GPU availability via a status flag rather than semaphore probing. This eliminates the race window where another request can steal the semaphore slot between the check and the actual acquire.

---

### 11. `audio_base64` and `audio_bytes` Empty Input Guards
- **Lines:** `762` (generate route), `1447–1528` (generate_inline)
- **Action:** Add explicit guards at function entry:
  ```python
  if not audio_base64 or len(audio_base64) < 10:
      return jsonify({"error": "invalid_audio", "message": "audio_base64 is empty or malformed"}), 400
  ```
  Same pattern for `audio_bytes` post-TTS. Never pass an empty buffer to the pipeline.