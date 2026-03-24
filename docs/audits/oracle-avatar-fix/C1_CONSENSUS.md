# CONSENSUS REPORT — ORACLE-AVATAR-FIX — CYCLE 1
Generated: 2026-03-24 11:59
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | ~70 | 75 | ~72 | **72/100** |
| Frontend/UI | N/A | N/A | N/A | **N/A** |
| Error Handling | ~55 | 70 | ~60 | **62/100** |
| Security | ~45 | 60 | ~50 | **52/100** |
| Performance | ~60 | 65 | ~58 | **61/100** |
| Law Compliance | ~75 | 80 | ~70 | **75/100** |
| World-Class Gap | ~50 | 60 | ~55 | **55/100** |
| **OVERALL** | **~59** | **68** | **~61** | **63/100** |

> *Gemini and Grok did not emit explicit numeric scores for all subsystems; estimates are derived from their written severity assessments and mapped to the same 0-100 scale for consistency.*

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### 1. No Rate Limiting on Any Endpoint
- **What:** Zero rate limiting on `/generate`, `/oracle/chat`, `/oracle/voice`, and all other endpoints. GPU-intensive and paid-API-consuming routes are fully open.
- **File/Line:** `oracle/avatar_server.py` — routes starting at lines 762, 1535, 1651
- **Fix:** Implement per-IP and per-session rate limiting using Flask-Limiter or a Redis-backed token bucket. At minimum: `/generate` ≤ 5 req/min/IP, `/oracle/chat` ≤ 20 req/min/IP.

### 2. No Authentication on Sensitive Endpoints
- **What:** All three models flagged that routes calling expensive external APIs (ElevenLabs, Anthropic, Gemini) and GPU resources have zero authentication or session validation.
- **File/Line:** `oracle/avatar_server.py:762`, `1535`, `1651`
- **Fix:** Add at minimum a bearer-token or session-cookie auth guard on all routes that trigger API spend or GPU work. Even a simple shared-secret header is better than nothing.

### 3. Unvalidated / Insufficiently Validated User Input
- **What:** `text` and `audio_base64` inputs in `/generate` are passed into TTS pipelines, `ffmpeg` subprocess calls, and base64 decoders without sanitization. All three models flagged this as a high-severity issue.
- **File/Line:** `oracle/avatar_server.py:762-919`, specifically lines ~802 (base64 decode), ~814 (ffmpeg call)
- **Fix:** Validate `audio_base64` length and charset before decoding; enforce max text length; whitelist/reject suspicious characters before any subprocess or file write.

### 4. Silent Exception Swallowing
- **What:** Multiple `except Exception: pass` blocks suppress errors entirely, making production debugging nearly impossible. All three models noted specific instances.
- **File/Lines:**
  - Line 113 — `_detect_face_cpu` eye landmark failure
  - Line 397-399 — `post_process_frames` blink failure
  - Line 1157-1159 — `_generate_chunk` sharpening failure
- **Fix:** Replace every bare `except Exception: pass` with at minimum `logger.warning("...", exc_info=True)`. The exception should be surfaced in logs even if execution continues.

### 5. No Retry Logic on External API Calls
- **What:** ElevenLabs, Anthropic, and other HTTP calls have timeouts but zero retry logic. A single network blip causes a hard failure.
- **File/Line:** `oracle/avatar_server.py:655` (ElevenLabs), `~1200` (Anthropic)
- **Fix:** Wrap all external HTTP calls with `tenacity` or equivalent: 3 retries, exponential backoff starting at 1s, retry only on 429/5xx/timeout.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### 6. Race Condition in `_load_avatar_face` Cache Population (Gemini + Grok)
- **What:** Two concurrent requests for the same new avatar both miss the cache check, both run expensive CPU face detection outside the lock, then both write to the cache. Work is redundant; under high load this wastes significant CPU.
- **File/Line:** `oracle/avatar_server.py:131-149`
- **Fix:** Implement proper double-checked locking: acquire lock → recheck cache → load if still absent → release. Use a `dict` of per-avatar `threading.Event` objects so the second thread waits for the first to finish rather than running detection twice.

### 7. Memory/Disk Leak in Session Dictionaries (Gemini + Grok)
- **What:** `_stream_sessions` (line 1109) and `_chunk_sessions` (line 1983) accumulate entries and temp files for abandoned sessions indefinitely. No TTL, no eviction, no cleanup. This will crash the server over time.
- **File/Line:** `oracle/avatar_server.py:1109`, `1983`
- **Fix:** Add a background cleanup thread (or APScheduler job) that evicts entries older than N minutes (e.g., 15 min) and calls `shutil.rmtree` on their temp directories. Use `threading.Timer` or a simple daemon thread with a sleep loop.

### 8. Semaphore Check/Acquire Pattern in `generate_inline` (Gemini + Grok)
- **What:** The semaphore is acquired non-blockingly just to check availability, then immediately released, then re-acquired for actual work. Creates a TOCTOU window where another request steals the slot between check and real acquire.
- **File/Line:** `oracle/avatar_server.py:1442`
- **Fix:** Remove the speculative non-blocking acquire. Do a single blocking acquire with timeout for the actual work. If the semaphore cannot be acquired, return 503 immediately without the double-acquire dance.

### 9. `audio_base64` Empty/Malformed Not Caught Early (GPT-4o + Grok)
- **What:** Empty or malformed `audio_base64` passes into processing and only fails deep in the pipeline with a vague 500, not at input validation time.
- **File/Line:** `oracle/avatar_server.py:802`, `~916`
- **Fix:** Add an explicit check immediately after decoding: if `len(audio_bytes) == 0` return a 400 with a descriptive message. Validate base64 charset before attempting decode.

### 10. `ffprobe` Duration Failure Silently Defaults to 0.0 (GPT-4o + Grok)
- **What:** If `ffprobe` fails or returns empty output, `audio_duration_sec` silently defaults to `0.0`, allowing malformed audio to proceed through the entire pipeline.
- **File/Line:** `oracle/avatar_server.py:819-826`
- **Fix:** If `ffprobe` fails or returns `0.0`, return a 400 to the caller immediately rather than continuing with invalid duration state.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1. Path Traversal via `session_id` in Stream URLs — **GEMINI ONLY**
- **Assessment: IMPLEMENT**
- `/stream_chunk/<session_id>/<int:chunk_number>` uses the `session_id` directly in filesystem path construction. Even though Flask routing offers partial protection, a crafted payload (e.g., `../../etc/passwd`) could bypass it. Validate `session_id` strictly against `^[a-f0-9\-]{36}$` (UUID format) before any `os.path.join` usage. This is a genuine vulnerability class — medium severity but trivially fixable.
- **File/Line:** `oracle/avatar_server.py:1236`

### U2. Health Check Re-imports Module on Every Request — **GEMINI ONLY**
- **Assessment: IMPLEMENT**
- `(lambda: __import__("blink_engine")._load_cache() is not None)()` in the health check (line 692) forces a module re-import on every health check ping. This is unnecessary overhead. Replace with a direct call to the already-imported module.
- **File/Line:** `oracle/avatar_server.py:692`

### U3. Hardcoded `-itsoffset 0.08` A/V Sync — **GEMINI ONLY**
- **Assessment: INVESTIGATE FURTHER**
- The hardcoded 80ms A/V offset in `frames_to_video` (line 430) may be calibrated for Kokoro TTS specifically. If ElevenLabs or another TTS engine is used, this offset could cause noticeable sync drift. Recommend making this a config constant (`AV_SYNC_OFFSET_SEC`) exposed via environment variable, and documenting why 0.08s was chosen.
- **File/Line:** `oracle/avatar_server.py:430`

### U4. `render_async` Background Thread Subject to Same Cache Race — **GEMINI ONLY**
- **Assessment: IMPLEMENT (subsumed by fix for Finding #6)**
- Background render threads call `_load_avatar_face` without any additional coordination. Once Finding #6 is fixed with proper per-avatar locking, this is automatically resolved.
- **File/Line:** `oracle/avatar_server.py:1750`

### U5. `generate_inline` Cleanup More Robust Than `/generate` — **GEMINI ONLY**
- **Assessment: IMPLEMENT**
- The generator-pattern cleanup in `generate_inline` is more leak-resistant than the mixed `finally`+`@after_this_request` pattern in `/generate`. If an error occurs after `video_path` is created in `/generate`, the file may be leaked. Standardize on the generator/context-manager pattern.
- **File/Line:** `oracle/avatar_server.py:890`, `919`, `1493`

### U6. Long Audio Has No Chunking Path — **GROK ONLY**
- **Assessment: INVESTIGATE FURTHER**
- Audio longer than `MAX_AUDIO_SECONDS` is rejected with a hard error. No chunking or splitting is offered. For a production service, rejecting long inputs without a fallback path is a UX gap. Consider adding a chunked processing mode or at minimum returning a descriptive error with the actual limit stated.
- **File/Line:** `oracle/avatar_server.py:829`

### U7. GPU Timeout Returns 503 With No Queue Position — **GROK ONLY**
- **Assessment: IMPLEMENT (P2)**
- When `_render_semaphore` times out, the 503 response gives no information about system load or expected wait. Adding an `X-Queue-Depth` header or a `retry_after` field in the JSON response would allow clients to implement intelligent backoff.
- **File/Line:** `oracle/avatar_server.py:839-840`

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1: Severity of Authentication Gap
- **GPT-4o** called this a concern but did not label it P0. **Grok** and **Gemini** both labeled it HIGH RISK or production showstopper.
- **Ruling: Grok/Gemini are correct.** Any endpoint that calls a paid third-party API without authentication is a critical financial and operational risk in production. Treat as P0 alongside rate limiting.

### Conflict 2: `_render_semaphore` Count Adequacy
- **GPT-4o** flagged the semaphore count as potentially too low for peak load. **Grok** noted it but focused more on fairness. **Gemini** did not flag the count itself.
- **Ruling: GPT-4o and Grok have the more complete picture.** The count is a tuning parameter (not a bug), but the lack of a request queue and the TOCTOU issue in `generate_inline` are real. Fix the TOCTOU (Finding #8) and document the semaphore count as a deployment-time tunable.

### Conflict 3: Overall Code Quality Assessment
- **GPT-4o** gave 68/100 overall, relatively charitable. **Gemini** characterized it as "functionally impressive but architecturally a prototype." **Grok** was somewhere between.
- **Ruling: Gemini's framing is the most accurate.** The core video-generation logic is sophisticated and works, but the surrounding production infrastructure (auth, rate limiting, session cleanup, retry logic) is essentially absent. 63/100 consensus score is appropriate.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **API Keys from Environment Variables** — All three models confirmed: no hardcoded secrets, keys loaded from env vars or `.env` file. Pattern is correct. Do not change.

2. **`subprocess.run` with Argument Lists (No `shell=True`)** — Gemini explicitly confirmed, others implicitly confirmed via low SQL/shell injection ratings. All `ffmpeg`/`ffprobe` calls pass arguments as lists, preventing shell injection. Do not change.

3. **Timeouts on All External HTTP Calls** — All three models noted this as correct behavior. Every `requests` call includes an explicit timeout. Do not change this pattern; only add retry logic on top of it.

4. **Kokoro → ElevenLabs TTS Fallback** — Gemini explicitly called this "excellent graceful degradation." Grok and GPT-4o acknowledged the fallback exists. The pattern is sound. Do not remove or restructure it.

5. **Threading Locks on `_avatar_face_cache`** — All models acknowledged the lock usage is correct in principle (the race condition is in the load logic, not the lock itself). The lock exists and is used. Do not remove it.

6. **ElevenLabs Voice Settings Constants (Line 652)** — Gemini confirmed these match the documented LAW exactly. Do not change the voice stability/similarity/style values.

7. **`exc_info=True` in Key Exception Handlers** — Gemini noted this positively (e.g., line 916). This pattern is already in place in the right locations. Extend it to the silent-failure locations but do not remove it from where it already exists.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|---|---|---|
| Technology Stack (Python 3.12, Flask 3.x, SQLite/SQLAlchemy) | ✅ COMPLIANT | All three models confirmed. |
| Ubuntu 24.04 deployment target | ✅ COMPLIANT | Consistent with deployment env. |
| UI Animations (CSS/SVG only, no Three.js/WebGL/Canvas) | ⚠️ CANNOT ASSESS | No frontend code provided. Must be verified separately. |
| No rotation in head movement (`warpAffine` prohibition) | ✅ COMPLIANT | Gemini confirmed XY translation only, per documented internal LAW line 329. |
| ElevenLabs voice settings (LAW 3: stability=0.45, similarity=0.75, style=0.20) | ✅ COMPLIANT | Gemini confirmed exact match at line 653. |
| DB query indexing on sort/filter columns | ⚠️ CANNOT ASSESS | No DB query code in reviewed files. |
| ~1000 concurrent users at peak | ❌ NON-COMPLIANT | Semaphore of 2, no queuing, no auth, no rate limiting = will collapse at scale. |
| HeyGen avatar integration | ❌ GAP | Grok noted HeyGen is not referenced anywhere in the code. |

---

## SECURITY CONSENSUS

Priority order (all items flagged by 2+ models unless noted):

| Priority | Issue | Models |
|---|---|---|
| 🔴 P0 | No rate limiting on GPU/paid-API endpoints | All 3 |
| 🔴 P0 | No authentication on any route | All 3 |
| 🔴 P0 | Unvalidated user input into subprocess and decoders | All 3 |
| 🟠 P1 | `audio_base64` size/content not validated before decode | GPT-4o + Grok |
| 🟠 P1 | Path traversal via `session_id` in stream routes | Gemini only — but high confidence, implement |
| 🟡 P2 | Error logs may expose partial API error messages if not secured | Grok |
| 🟡 P2 | `.env` file must be excluded from version control and secured on disk | GPT-4o |

---

## WORLD-CLASS GAP CONSENSUS

Items identified by 2+ models as separating this from a truly production-grade service:

1. **No operational infrastructure** (rate limiting, auth, queuing) — All 3 models. The core generation pipeline is sophisticated; the surrounding infrastructure is prototype-grade.

2. **No retry/resilience layer on external dependencies** — All 3 models. A world-class service degrades gracefully when ElevenLabs or Anthropic has a bad minute. This one crashes.

3. **Session/resource lifecycle management is absent** — Gemini + Grok. Abandoned sessions accumulate forever. World-class services implement TTL-based cleanup as a first-class concern, not an afterthought.

4. **No observability beyond basic logging** — GPT-4o + Grok. No metrics, no distributed tracing, no alerting on GPU saturation or API quota burn rate. A world-class service would have dashboards for render queue depth, TTS latency p95, and API spend rate.

5. **Concurrency model is blocking** — GPT-4o + Grok. Synchronous Flask with threading is a ceiling, not a scalable foundation. Async I/O (FastAPI + asyncio) or a proper task queue (Celery + Redis) is standard for GPU-serving workloads at scale.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Implement rate limiting (Flask-Limiter, per-IP)                    | avatar_server.py:762,1535,1651        | models: all 3    | Open API + paid services = financial DoS vector
P0 CRITICAL | Add authentication guard on all routes triggering API spend or GPU  | avatar_server.py:762,1535,1651        | models: all 3    | Any anonymous user can exhaust GPU and API budget
P0 CRITICAL | Validate and sanitize all user inputs before subprocess/decode      | avatar_server.py:802,814              | models: all 3    | Base64 size bomb + potential command injection path
P0 CRITICAL | Replace all bare `except Exception: pass` with logged warnings       | avatar_server.py:113,397,1157         | models: all 3    | Silent failures make production debugging impossible
P0 CRITICAL | Add TTL-based cleanup for _stream_sessions and _chunk_sessions      | avatar_server.py:1109,1983            | models: gemini+grok | Memory/disk leak will crash server over time
P1 HIGH     | Add retry logic with exponential backoff on all external API calls  | avatar_server.py:655,~1200            | models: all 3    | Single network blip causes hard failure
P1 HIGH     | Fix TOCTOU double-acquire pattern in generate_inline semaphore      | avatar_server.py:1442                 | models: gemini+grok | Race window allows slot theft between check and use
P1 HIGH     | Fix double-checked locking race in _load_avatar_face               | avatar_server.py:131-149              | models: gemini+grok | Redundant expensive CPU face detection under load
P1 HIGH     | Return 400 immediately if audio_base64 is empty or ffprobe fails    | avatar_server.py:802,819-826          | models: gpt4o+grok  | Malformed audio propagates deep into pipeline
P1 HIGH     | Validate session_id against UUID regex before filesystem use        | avatar_server.py:1236                 | models: gemini (unique but high confidence) | Path traversal vulnerability class
P2 MEDIUM   | Standardize file cleanup to generator/context-manager pattern       | avatar_server.py:890,919              | models: gemini   | Mixed finally+after_this_request can leak video files on error
P2 MEDIUM   | Make AV sync offset configurable (env var, not hardcoded)          | avatar_server.py:430                  | models: gemini   | 80ms offset may be wrong for non-Kokoro TTS engines
P2 MEDIUM   | Add X-Queue-Depth / retry_after to 503 GPU-busy responses          | avatar_server.py:839-840              | models: grok     | Enables client-side intelligent backoff
P2 MEDIUM   | Replace health check module re-import with direct function call     | avatar_server.py:692                  | models: gemini   | Unnecessary overhead on every health ping
P2 MEDIUM   | Add structured metrics/observability (render queue depth, API spend)| avatar_server.py (global)             | models: gpt4o+grok | Required for production capacity management
P3 LOW      | Investigate long-audio chunking path vs hard rejection             | avatar_server.py:829                  | models: grok     | UX gap — users get hard error with no alternative
P3 LOW      | Investigate HeyGen avatar integration gap                          | avatar_server.py (global)             | models: grok     | Spec references HeyGen; code has no reference to it
```

---

## CYCLE 1 VERDICT

**NOT READY for a direct second build pass without triage of the P0 items.**

The core generation pipeline — Wav2Lip, TTS fallback, blink/head-movement post-processing, mel spectrogram handling — is genuinely sophisticated and largely correct. The three models converge on this being competent GPU-serving code. However, the production infrastructure surrounding it (authentication, rate limiting, session lifecycle, error surfacing) is at prototype quality. Five P0 items exist, two of which (no auth, no rate limiting) are financial and operational liabilities that would be exploited within hours of a public deployment.

**Recommended path:** Fix all P0 items before the second pass. The P1 items should be bundled into the same pass. The code is close — this is infrastructure scaffolding work, not a fundamental rework of the generation logic.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/oracle-avatar-fix_CONSENSUS_C1.md.

This is the SECOND PASS for oracle-avatar-fix.
The first build was reviewed by 3 independent AI models (Gemini 2.5 Pro, GPT-4o,
Grok-3) across 1 cycle. Implement every P0 and P1 item from the consensus report.
Use judgment on P2 items — implement if the change is self-contained and low-risk.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement per-IP rate limiting via Flask-Limiter
            | oracle/avatar_server.py:762,1535,1651
            | /generate ≤ 5 req/min/IP; /oracle/chat ≤ 20 req/min/IP; /oracle/voice ≤ 10 req/min/IP

P0 CRITICAL | Add authentication guard (bearer token or session cookie) on all
            | routes that trigger GPU work or paid API calls
            | oracle/avatar_server.py:762,1535,1651

P0 CRITICAL | Validate and sanitize user inputs before any subprocess call or
            | base64 decode: enforce max text length, validate base64 charset,
            | enforce max audio_base64 byte size before decoding
            | oracle/avatar_server.py:802,814

P0 CRITICAL | Replace all bare `except Exception: pass` blocks with at minimum
            | logger.warning("...", exc_info=True) so silent failures surface in logs
            | oracle/avatar_server.py:113,397-399,1157-1159

P0 CRITICAL | Add TTL-based background cleanup (daemon thread, 15-min TTL) for
            | _stream_sessions