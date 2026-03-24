# CONSENSUS REPORT — ORACLE-SPEAK-REVERT — CYCLE 2
Generated: 2026-03-24 14:53
Models: grok, gemini (+1 failed: gpt4o — TPM rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | 40 | N/A (failed) | 62 | **51** |
| Error Handling | 45 | N/A (failed) | 58 | **52** |
| Security | 30 | N/A (failed) | 45 | **38** |
| Performance | 50 | N/A (failed) | 55 | **53** |
| World-Class Gap | 35 | N/A (failed) | 40 | **38** |
| **OVERALL** | **40** | **~59** *(C1 only)* | **52** | **44** |

> **Note:** GPT-4o failed in Cycle 2 due to token limits. Its Cycle 1 score of ~59 is included for trend context only and is excluded from Cycle 2 consensus arithmetic. Gemini's dramatic score reduction (63→40) after seeing the full picture is treated as a recalibration signal, not an outlier, and is weighted accordingly.

---

## UNANIMOUS FINDINGS
*(Both active models agree — implement unconditionally)*

---

### U1 — No Rate Limiting on Any Endpoint
**File:** `oracle/avatar_server.py` — Lines 833, 1055, 1500, 1627, 1747 (and all expensive routes)
**What it is:** Zero rate limiting exists on any endpoint, including GPU-intensive `/generate`, AI-expensive `/oracle/chat`, `/oracle/speak`, `/oracle/voice`, and `/vision/analyze`. A single bad actor or runaway client can exhaust GPU slots, consume ElevenLabs/Anthropic/Gemini API quotas, and functionally DoS the service.
**What to change:** Install `flask-limiter` with a Redis backend (consistent with the persistent-state fix in U3). Apply per-IP and per-API-key limits. Suggested defaults:
- `/generate`: 10 req/min per IP, 60 req/hour
- `/oracle/chat`, `/oracle/speak`, `/oracle/voice`: 30 req/min per IP
- `/vision/analyze`: 20 req/min per IP
- `/reload-avatar`: 5 req/min, admin-auth required

---

### U2 — No Authentication on Sensitive and Expensive Routes
**File:** `oracle/avatar_server.py` — Lines 833, 1021, 1055, 1627, 1747
**What it is:** All endpoints, including the admin-level `/reload-avatar` (line 1021) and all GPU/LLM-consuming routes, are completely unauthenticated. Anyone who can reach the server can invoke expensive operations or modify server state.
**What to change:** Implement mandatory API key authentication via a request header (`X-API-Key`). A decorator pattern is cleanest:
```python
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not key or not _validate_api_key(key):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
```
Apply to all non-health-check routes. `/reload-avatar` should additionally require an admin-tier key.

---

### U3 — No Retry Logic on External API Calls
**File:** `oracle/avatar_server.py` — Lines 717–730 (ElevenLabs), 1282–1295 (Anthropic), and all other external API calls
**What it is:** Every external API call — ElevenLabs TTS, Anthropic Claude, Gemini Vision — is a single-shot attempt with no retry on transient 5xx errors, network timeouts, or rate-limit responses (429). One blip kills the request.
**What to change:** Wrap all external calls with exponential backoff using `tenacity` or a manual implementation:
```python
@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3),
       retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)))
def _call_elevenlabs(...): ...
```
Respect `Retry-After` headers from 429 responses. Log each retry at WARNING level with attempt count.

---

### U4 — In-Memory State Lost on Restart (Architectural Flaw)
**File:** `oracle/avatar_server.py` — Lines 206 (`_render_jobs`), 1203 (`_stream_sessions`), `_chunk_sessions`, `oracle_dialogue_engine._sessions`
**What it is:** The entire async job and session state lives in global Python dictionaries. Any server restart, crash, or process recycle by Gunicorn/uWSGI silently wipes all in-flight jobs and active sessions. Clients polling `/oracle/job/<job_id>` receive 404. Conversation history is lost. This makes the async job system contractually broken.
**What to change:** Migrate all state to Redis. Use a consistent key schema:
- `job:{job_id}` → serialized job state with TTL matching current GC policy
- `session:{session_id}` → conversation + chunk state
- `stream:{stream_id}` → stream session state

This also unblocks horizontal scaling (see World-Class Gap section).

---

### U5 — Race Condition in Garbage Collector (`_gc_worker`)
**File:** `oracle/avatar_server.py` — Lines 222–273
**What it is:** `_gc_worker` can call `shutil.rmtree` on a session directory (lines 237, 251) while an active worker thread is still writing frames or encoding video into that directory. This produces `FileNotFoundError` exceptions in active workers and potentially corrupted output. The GC makes its deletion decision based on time elapsed, not terminal state.
**What to change:** GC must only clean up sessions confirmed to be in a terminal state (`"complete"` or `"error"`) AND past their TTL. Add a `state` field to every session dict; GC checks `session["state"] in ("complete", "error")` before any deletion. Active sessions should never be touched regardless of age.

---

### U6 — CORS Check Allows Malicious Lookalike Origins
**File:** `oracle/avatar_server.py` — Line 185
**What it is:** `origin.startswith("http://localhost")` incorrectly permits `http://localhost.evil.com`, `http://localhosted.com`, etc. This is a textbook CORS bypass allowing cross-origin requests from attacker-controlled domains.
**What to change:**
```python
# Replace:
if origin.startswith("http://localhost"):

# With:
import re
if re.match(r'^http://localhost(:\d+)?$', origin):
```
Or use an explicit allowlist: `ALLOWED_ORIGINS = {"http://localhost:3000", "http://localhost:5173", ...}` and check `origin in ALLOWED_ORIGINS`.

---

## MAJORITY FINDINGS
*(2 of 2 active models agree)*

Since both active models agreed on all findings above (U1–U6), this section captures strong findings where both models raised the issue but with differing emphasis or framing.

---

### M1 — Generic 503 "GPU Busy" with No Queue Context
**Models:** Grok (primary), Gemini (supporting)
**File:** `oracle/avatar_server.py` — Lines 934, 1563–1564
**What it is:** When the GPU semaphore is exhausted, clients receive a bare 503 with no `Retry-After` header, no queue position, and no wait-time estimate. This causes blind exponential retries and "thundering herd" load spikes — the exact condition the semaphore is meant to prevent.
**What to change:** Return a structured 503 with actionable metadata:
```python
return jsonify({
    "error": "gpu_busy",
    "queue_depth": _render_semaphore._value,  # approx
    "retry_after_seconds": 15
}), 503, {"Retry-After": "15"}
```
Note: `_render_semaphore._value` is a non-atomic read (see Unique Insights); replace with an explicit atomic counter.

---

### M2 — Unsafe Fire-and-Forget Threading for Async Jobs
**Models:** Gemini (primary), Grok (supporting via "in-memory state" framing)
**File:** `oracle/avatar_server.py` — Lines 1846–1917
**What it is:** Background jobs are launched via `threading.Thread(...).start()` inside a WSGI handler. Process managers kill these threads without notice during recycles. Jobs vanish silently. This is the mechanism-level expression of the state-loss problem (U4).
**What to change:** Replace with a proper task queue. Celery + Redis is the production-standard choice and integrates naturally with the Redis migration in U4. Dramatiq is a lighter alternative. At minimum, if threading is retained temporarily, jobs must be logged to Redis before the thread starts so they can be detected as "orphaned" after a restart.

---

### M3 — Insufficient Concurrency for 1000-User Target
**Models:** Grok (primary), Gemini (supporting via scalability anti-pattern finding)
**File:** `oracle/avatar_server.py` — Line 211 (`_render_semaphore = threading.Semaphore(2)`)
**What it is:** Two concurrent renders is appropriate for a single GPU but the architecture cannot scale horizontally (single-process state). The spec targets ~1000 concurrent users. This is structurally impossible until U4 (Redis state) and M2 (Celery queue) are resolved.
**What to change:** Semaphore value of 2 is correct for one GPU instance. The fix is horizontal: once state is in Redis and jobs go through Celery, multiple worker processes can each hold a semaphore of 2, scaling linearly with GPU count. Document this dependency chain explicitly.

---

## UNIQUE INSIGHTS
*(Single-model observations — evaluated individually)*

---

### UI-1 — Thundering Herd on Avatar Face Cache Load
**Model:** Grok
**File:** `oracle/avatar_server.py` — Lines 85, 132–164, 156
**What it is:** Multiple concurrent requests for the same uncached avatar will all miss the cache simultaneously, each triggering the expensive `_detect_face_cpu` call before any of them writes to the cache. The lock prevents corruption but not duplicated work.
**Assessment: IMPLEMENT.** This is a real and reproducible inefficiency. The fix is a double-checked locking pattern:
```python
if avatar_id not in _avatar_face_cache:
    with _avatar_face_cache_lock:
        if avatar_id not in _avatar_face_cache:  # second check under lock
            _avatar_face_cache[avatar_id] = _detect_face_cpu(...)
```

---

### UI-2 — Hardcoded Limits Not Configurable via Environment
**Model:** Grok
**File:** `oracle/avatar_server.py` — Lines 847–848 (`MAX_TEXT_LEN = 2000`, `MAX_AUDIO_B64_LEN = 2_000_000`)
**What it is:** Operational limits are hardcoded constants, not configurable via environment variables. Operators cannot tune them without code changes.
**Assessment: IMPLEMENT (low effort, high value).** Wrap in `int(os.getenv("MAX_TEXT_LEN", 2000))`. Apply to all configurable operational limits (batch sizes, semaphore counts, TTLs). This is a 20-minute change with meaningful operational flexibility.

---

### UI-3 — No Timeout on `frames_to_video` ffmpeg Subprocess
**Model:** Grok
**File:** `oracle/avatar_server.py` — Lines 481–537, specifically lines 500, 515
**What it is:** The `frames_to_video` ffmpeg subprocess runs without a `timeout=` argument. A malformed frame sequence or degenerate input could cause indefinite hang, blocking a worker thread permanently.
**Assessment: IMPLEMENT.** Add `timeout=120` (or a configurable env var) to all `subprocess.run` calls in this function. Catch `subprocess.TimeoutExpired` and return an error response.

---

### UI-4 — Duplicated Secret Loading Logic
**Model:** Gemini
**File:** `oracle/avatar_server.py` — Lines 710–715, 1211–1216
**What it is:** `.env` file reading and API key extraction is copy-pasted in at least two places. A bug fix or key rotation in one location will not propagate to the other.
**Assessment: IMPLEMENT.** Extract into a single `_get_api_key(key_name: str) -> str` utility. This is a one-cycle refactor with zero behavioral change and eliminates a maintenance landmine.

---

### UI-5 — Information Disclosure via `/health` Endpoint
**Model:** Gemini
**File:** `oracle/avatar_server.py` — Line 737
**What it is:** The public `/health` endpoint exposes VRAM statistics, model names, and internal implementation details. This fingerprints the server for attackers.
**Assessment: IMPLEMENT (simple split).** `/health` returns `{"status": "ok", "ts": ...}` only. Create `/debug/status` (authenticated, admin-key) for full diagnostics. Two-line behavioral change.

---

### UI-6 — TTS Input Not Sanitized Against SSML/Injection
**Model:** Grok
**File:** `oracle/avatar_server.py` — Lines 557–616 (`_preprocess_tts_text`)
**What it is:** TTS text preprocessing handles numbers and symbols but does not strip SSML tags or pathological inputs (e.g., thousands of repeated characters) that could crash ElevenLabs/Kokoro or generate unexpectedly large/long audio.
**Assessment: INVESTIGATE FURTHER.** The risk depends on whether ElevenLabs accepts raw SSML. If yes, an attacker could inject `<break time="10s"/>` repeated to generate a 10-minute audio file and exhaust quota. Verify ElevenLabs behavior and add a `re.sub(r'<[^>]+>', '', text)` SSML strip as a precaution.

---

### UI-7 — Adaptive Batch Size Threshold Unjustified and Non-Configurable
**Model:** Grok
**File:** `oracle/avatar_server.py` — Lines 338–339
**What it is:** Batch size adapts based on a hardcoded `<60 mel frames` threshold with no documented justification. Wrong values cause VRAM exhaustion or underutilization.
**Assessment: INVESTIGATE FURTHER.** Flag for the ML/infra owner to validate the threshold against actual VRAM profiles. Add an environment variable override in the interim.

---

## CONFLICTS
*(Areas of model disagreement)*

**Conflict 1 — Severity of Silent `loudnorm` Failure**
- Grok: LOW priority, acceptable fallback
- Gemini: MEDIUM priority, hides configuration issues

**Tiebreaker: Gemini is right on principle, Grok is right on priority.** The fallback behavior is correct — unnormalized audio is better than a crash. However, a silent failure with no log entry is bad operational practice. The fix is trivial: add a `logger.warning("loudnorm failed, using raw audio: %s", result.returncode)` at lines 666–672. This costs nothing and improves debuggability. **Implement at P2.**

**Conflict 2 — Score Calibration**
- Gemini revised overall from 63→40 (aggressive downgrade)
- Grok settled around 52

**Tiebreaker:** Gemini's post-synthesis recalibration is more credible because it explicitly accounts for the architectural state-loss finding it initially missed. The consensus score of 44 reflects that this code is a functional prototype with serious production blockers, not a near-production system. Grok's 52 underweights the architectural severity. **Consensus adopts 44.**

---

## VALIDATED STRENGTHS
*(Both models confirmed — do NOT change in the second pass)*

1. **ElevenLabs Voice Settings Compliance:** `stability=0.45, similarity_boost=0.75, style=0.20` (line 724) — correctly implemented per LAW 3. Do not touch.
2. **API Key Source Hygiene:** API keys are sourced from environment variables / `.env` files, not hardcoded in source. This pattern is correct and should be preserved (and extended to the deduplication fix in UI-4).
3. **Render Semaphore Value:** `threading.Semaphore(2)` at line 211 is the correct limit for a single-GPU deployment. Do not increase this value without a corresponding GPU infrastructure change.
4. **Input Length Rejection Logic:** The hard rejection of audio >30s (lines 923–929) and text >2000 chars (lines 847–848) is correct behavior — make the limits configurable (UI-2) but do not remove the guards.
5. **TTS Fallback Chain (Kokoro → ElevenLabs):** The two-provider fallback pattern for TTS is architecturally sound. The fallback structure should be preserved; only the error logging and retry logic around it need improvement.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Finding |
|---|---|---|
| LAW 3: Jessica voice settings (stability=0.45, similarity\_boost=0.75, style=0.20) | ✅ **COMPLIANT** | Line 724 correctly implements all three parameters. Both models confirmed. |
| Implicit Law — Python 3.12, Flask, SQLAlchemy/SQLite stack | ✅ **COMPLIANT** | Technology stack matches. |
| Implicit Law — DB index requirement on sort/filter columns | ⚠️ **UNVERIFIABLE** | No explicit DB queries visible in this file. Must be verified at the schema/migration level. |
| Implicit Law — ~1000 concurrent user support | ❌ **VIOLATED** | Single-process in-memory architecture structurally prevents this. Blocked until U4 + M2 + M3 are resolved. |

---

## SECURITY CONSENSUS

Priority-ordered security issues both/all models flagged:

| Priority | Issue | Line(s) | Severity |
|---|---|---|---|
| P0 | No authentication on any route | Global | Critical |
| P0 | No rate limiting on expensive endpoints | 833, 1055, 1627, 1747 | Critical |
| P1 | CORS bypass via prefix match | 185 | High |
| P1 | TTS input not sanitized against SSML injection | 557–616 | High (investigate) |
| P2 | `/health` information disclosure | 737 | Low |
| P2 | Secrets loading duplicated (rotation risk) | 710–715, 1211–1216 | Low |

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned)*

1. **Persistent, distributed job state** — Both models. The most fundamental gap. A world-class async media generation service uses Redis + Celery (or equivalent). In-memory dicts are a prototype pattern.

2. **Horizontal scalability** — Both models. The architecture assumes exactly one process on exactly one machine. World-class services are stateless and scale behind a load balancer. This is impossible until gap #1 is resolved.

3. **Structured error codes in API responses** — Both models (different framing). `str(e)` in error responses is not acceptable for a client-integrated API. Every error should have a machine-readable `error_code`, human-readable `message`, and optional `detail`. A proper error taxonomy should be documented.

4. **Proper task queue (Celery/Dramatiq)** — Both models. Fire-and-forget threads in a WSGI context are not a job queue. A world-class service separates web workers (request/response) from job workers (async compute) via a durable message broker.

5. **Observability** — Both models (implied). No structured logging format, no distributed tracing, no metrics emission (Prometheus/StatsD). World-class services emit `job_id`-tagged structured logs and expose latency/error-rate metrics.

---

## FINAL ACTION PLAN

*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Implement API key authentication on all non-health routes; admin-tier key for `/reload-avatar` | `oracle/avatar_server.py` — global | Both | Unauthenticated GPU/LLM access is an open exploit |
| **P0 CRITICAL** | Implement rate limiting via `flask-limiter` + Redis on all expensive endpoints | Lines 833, 1055, 1500, 1627, 1747 | Both | DoS and quota drain risk; financial and availability threat |
| **P0 CRITICAL** | Migrate all in-memory state (`_render_jobs`, `_stream_sessions`, `_chunk_sessions`, dialogue sessions) to Redis | Lines 206, 1203, global | Both | State loss on any restart; async job contract is broken |
| **P0 CRITICAL** | Fix GC race condition: only delete sessions in confirmed terminal state (`"complete"` / `"error"`) | Lines 222–273 | Both | Active workers get `FileNotFoundError`; data corruption in production |
| **P0 CRITICAL** | Fix CORS check to use exact regex or allowlist | Line 185 | Both | Malicious lookalike origins bypass CORS |
| **P1 HIGH** | Add retry + exponential backoff to all external API calls (ElevenLabs, Anthropic, Gemini) | Lines 717–730, 1282–1295 | Both | Single transient failure kills user request; production brittleness |
| **P1 HIGH** | Replace fire-and-forget threads with Celery task queue | Lines 1846–1917 | Both | WSGI process recycle silently kills jobs; reinforces state-loss problem |
| **P1 HIGH** | Return structured 503 with `Retry-After` and queue depth when GPU semaphore exhausted | Lines 934, 1563–1564 | Both | Blind retries cause thundering herd; semaphore defeats itself |
| **P1 HIGH** | Add `timeout=` to all `subprocess.run` calls in `frames_to_video` | Lines 481–537 (500, 515) | Grok (unique) | Malformed input can hang worker thread indefinitely |
| **P1 HIGH** | Apply double-checked locking pattern to avatar face cache loading | Lines 85, 132–164, 156 | Grok (unique) | Concurrent cache misses waste CPU on repeated face detection |
| **P2 MEDIUM** | Make `MAX_TEXT_LEN`, `MAX_AUDIO_B64_LEN`, semaphore count, TTLs configurable via env vars | Lines 847–848, 211 | Grok (unique) | Hardcoded operational limits require code changes to tune |
| **P2 MEDIUM** | Extract secret/key loading into single `_get_api_key()` utility | Lines 710–715, 1211–1216 | Gemini (unique) | DRY violation; key rotation bug risk |
| **P2 MEDIUM** | Split `/health` into public `{"status":"ok"}` and authenticated `/debug/status` | Line 737 | Gemini (unique) | Internal implementation fingerprinting |
| **P2 MEDIUM** | Log warning when `loudnorm` ffmpeg step fails | Lines 666–672 | Both (dispute on priority) | Silent failure hides audio quality degradation |
| **P2 MEDIUM** | Replace `str(e)` in error responses with structured `{error_code, message, detail}` | Line 1010 and global | Both | Unstructured errors are unusable by API clients |
| **P2 MEDIUM** | Investigate SSML injection via TTS text input; add strip as precaution | Lines 557–616 | Grok (unique) | Potential quota drain via injected long pauses |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY.**

This code is a capable, feature-rich prototype that

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across the 2-cycle audit. Its Cycle 1 findings — in-memory state loss, GC race condition, and the precise CORS `localhost` bypass — were *independently verified correct* by Grok in Cycle 2, confirming accuracy. Its recommendations were specific and immediately actionable (exact line references, concrete fix descriptions), it identified architectural issues that neither GPT-4o nor Grok caught in Cycle 1, and the Cycle 2 consensus report explicitly treated its score reduction as a *calibration signal* rather than noise — meaning its judgment was trusted even when it moved against trend. GPT-4o was surface-level and incomplete; Grok was thorough but derivative, spending Cycle 2 largely crediting Gemini.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: severity × blast radius × implementation cost (lowest cost, highest risk first)

---

## P0 — SHIP BLOCKERS (Fix before any production traffic)

### P0-1 — No Authentication on Sensitive Routes
**File:** `avatar_server.py` — Lines 833, 1021, 1055, 1627, 1747
**Risk:** Unauthenticated access to GPU compute, AI API budget, and admin controls. A single curl command can drain ElevenLabs/Anthropic quota to zero.
**Fix:** Implement bearer token middleware applied as a Flask `before_request` decorator. Admin routes (`/reload-avatar`, `/reload-engine`) require a separate elevated token stored in environment variables. Reject with 401 before any business logic executes.
```python
# Minimal pattern
@app.before_request
def require_auth():
    if request.endpoint in PROTECTED_ROUTES:
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if token != os.environ["API_SECRET_KEY"]:
            abort(401)
```

---

### P0-2 — No Rate Limiting on Any Endpoint
**File:** `avatar_server.py` — Lines 833, 1055, 1500, 1627, 1747
**Risk:** Single bad actor or retry storm exhausts GPU semaphore slots and third-party API quotas. No financial circuit breaker exists.
**Fix:** Install `flask-limiter` with Redis backend (reuse the Redis instance from P1-1). Apply immediately:
```
/generate:           10/min, 60/hour per IP
/oracle/chat|speak:  30/min per IP
/vision/analyze:     20/min per IP
/reload-avatar:      5/min, admin token required (P0-1 prerequisite)
```
Return `429` with `Retry-After` header. Log limit-breach events to your monitoring stack.

---

### P0-3 — CORS Allows Arbitrary `localhost.*` Origins
**File:** `avatar_server.py` — Line 185
**Risk:** `origin.startswith("http://localhost")` permits `http://localhost.attacker.com`. Browsers will honor this and send credentialed cross-origin requests from attacker-controlled pages.
**Fix:** One line change, zero performance cost:
```python
# BEFORE
if origin.startswith("http://localhost"):

# AFTER
import re
_LOCALHOST_RE = re.compile(r'^http://localhost(:\d+)?$')
if _LOCALHOST_RE.match(origin):
```
Apply the same pattern to any other origin-matching logic in the file.

---

## P1 — ARCHITECTURAL DEBT (Fix within current sprint)

### P1-1 — All Async State Lives in Memory (Lost on Restart)
**File:** `avatar_server.py` — `_render_jobs`, `_stream_sessions`, `_chunk_sessions`, `oracle_dialogue_engine._sessions`
**Risk:** Any deploy, crash, or OOM kill silently destroys all in-flight jobs and conversation history. Clients polling `/oracle/job/<id>` receive 404 with no explanation. Contradicts the spec's database layer contract.
**Fix:** Migrate job and session state to Redis with TTL-based expiry. Use `redis-py` with a thin wrapper that serializes job state to JSON. Conversation history (dialogue engine sessions) migrates to the existing SQLite/SQLAlchemy layer. Suggested schema:
```
redis key: job:{job_id}         TTL: 3600s
redis key: stream:{session_id}  TTL: 1800s
redis key: chunk:{session_id}   TTL: 1800s
sqlite:    dialogue_sessions table (existing ORM, add session_id + history columns)
```
This also unblocks horizontal scaling — multiple server instances can share state.

---

### P1-2 — GC Worker Races with Active Write Threads
**File:** `avatar_server.py` — Lines 222–273 (GC) vs. Line 1225 (`_generate_chunk`)
**Risk:** `_gc_worker` calls `shutil.rmtree` on session directories based on age alone, not terminal state. A worker thread mid-write receives `FileNotFoundError`, producing a corrupt or missing output with no client notification.
**Fix:** GC must gate deletion on session state, not time alone:
```python
# Only delete sessions in terminal states that have exceeded TTL
TERMINAL_STATES = {"complete", "error", "cancelled"}
for session_id, session in list(_chunk_sessions.items()):
    if (session["status"] in TERMINAL_STATES and
            time.time() - session["created_at"] > SESSION_TTL):
        shutil.rmtree(session["dir"], ignore_errors=True)
        del _chunk_sessions[session_id]
```
After P1-1 lands, this check reads from Redis instead of the in-memory dict.

---

## P2 — RELIABILITY & UX (Fix within next sprint)

### P2-1 — GPU Queue Returns Opaque 503 Without Retry Guidance
**File:** `avatar_server.py` — Lines 933–934 (semaphore timeout), Line 1563 (`generate_inline`)
**Risk:** Client receives `503 GPU busy` with no queue position or retry timing. Clients implement random backoff or fixed polling, causing thundering herd on recovery and amplifying load spikes.
**Fix:** Add `Retry-After` header and queue depth to the 503 response body:
```python
queue_depth = MAX_CONCURRENT_RENDERS - _render_semaphore._value
return jsonify({
    "error": "GPU busy",
    "queue_depth": queue_depth,
    "retry_after_seconds": queue_depth * AVG_RENDER_SECONDS
}), 503, {"Retry-After": str(queue_depth * AVG_RENDER_SECONDS)}
```

---

### P2-2 — Thundering Herd on New Avatar Face Loading
**File:** `avatar_server.py` — `_avatar_face_cache_lock` surrounding face load logic
**Risk:** Multiple concurrent requests for the same uncached avatar all pass the cache-miss check simultaneously, each triggering the expensive face detection pipeline. Results in N redundant GPU operations and potential VRAM exhaustion.
**Fix:** Implement a per-avatar loading lock (double-checked locking pattern):
```python
_avatar_loading_locks: dict[str, threading.Lock] = {}
_avatar_loading_locks_meta = threading.Lock()

def get_avatar_face(avatar_id):
    if avatar_id in _avatar_face_cache:
        return _avatar_face_cache[avatar_id]
    with _avatar_loading_locks_meta:
        if avatar_id not in _avatar_loading_locks:
            _avatar_loading_locks[avatar_id] = threading.Lock()
    with _avatar_loading_locks[avatar_id]:
        if avatar_id not in _avatar_face_cache:  # re-check under lock
            _avatar_face_cache[avatar_id] = _load_face(avatar_id)
    return _avatar_face_cache[avatar_id]
```

---

### P2-3 — `ffmpeg loudnorm` Fails Silently
**File:** `avatar_server.py` — Lines 666–672 (`_avatar_tts`)
**Risk:** Audio normalization failure is swall