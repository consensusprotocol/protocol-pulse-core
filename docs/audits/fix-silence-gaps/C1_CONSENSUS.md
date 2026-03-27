# CONSENSUS REPORT — FIX-SILENCE-GAPS — CYCLE 1
Generated: 2026-03-22 16:21
Models: grok, gpt4o (+1 failed — Gemini 2.5 Pro, API key leaked/revoked)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | ❌ N/A | 58/100 | 75/100 | **66/100** |
| Frontend/UI | ❌ N/A | N/A | N/A | **N/A** |
| Error Handling | ❌ N/A | 40/100 | 60/100 | **50/100** |
| Security | ❌ N/A | 45/100 | 50/100 | **47/100** |
| Performance | ❌ N/A | 45/100 | 55/100 | **50/100** |
| Law Compliance | ❌ N/A | 65/100 | 40/100 | **52/100** |
| **Overall** | ❌ N/A | **51/100** | **55/100** | **53/100** |

> ⚠️ **Scoring confidence is reduced.** Gemini failed (403 — leaked API key). Scores are derived from 2 of 3 models. The consensus average skews optimistic compared to what a 3-model agreement would likely produce. Treat the 53/100 overall as a ceiling, not a floor.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

---

### U1 — Silence Fallback Defeats Its Own Hard-Fail Policy
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 756–767, 1259–1267
**What it is:** `_tts_generate_silence_fallback()` raises an exception explicitly to prevent silent renders. However, `generate_dialogue_audio()` catches `_tts_ok == False` and writes 3 seconds of silence *anyway*, completely nullifying the guard.
**What to change:** Remove the silence-write fallback block at lines 1259–1267 entirely. On TTS failure, either raise immediately (hard-fail) or enqueue a retry — do not generate synthetic silence and continue. The current behavior guarantees corrupted podcast episodes reach downstream render with no warning.

---

### U2 — Non-Atomic Cache Writes Allow Race Conditions and Corrupt Reads
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 729–754 (`_tts_cache_get`, `_tts_cache_put`)
**What it is:** Cache writes copy files directly without locking. Under concurrent requests, two writers can race producing partial files; a reader can copy a half-written file and serve corrupted audio for the lifetime of the cache entry.
**What to change:** Write to a `.tmp` file first, then `os.replace()` (atomic on POSIX). Add a per-key `threading.Lock()` or use `fcntl.flock()` around the critical section. At minimum: write-to-temp + atomic rename.

---

### U3 — ffmpeg Subprocess Return Codes Routinely Ignored
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 226–235, 1164–1168, 1294–1298
**What it is:** Both models independently flagged that ffmpeg/ffprobe subprocess calls do not check return codes before downstream operations consume their output. A failed ffmpeg concat at line 1294 still produces a `full_path` reference in the returned metadata; `_mp3_to_m4a()` at line 1169 receives a nonexistent input after a failed concat at 1164–1168.
**What to change:** After every `subprocess.run()` call involving ffmpeg/ffprobe: check `returncode != 0`, log stderr, and raise or return a structured failure. Never pass ffmpeg output paths to downstream functions without verifying the file exists and has non-zero size.

---

### U4 — Global Module-Level State Is Not Thread-Safe
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 21–27, 215 (`_KOKORO_*`, `_F5_MODEL`, `_BIGVGAN_MODEL`, `_CHATTERBOX_MODEL`, `_KEY_CACHE`, `_PROSODY_CACHE`)
**What it is:** All heavyweight model globals and caches are initialized lazily without locks. Under a multi-threaded Flask server with ~1000 concurrent users, multiple threads can race during initialization, double-load multi-GB GPU models, or corrupt shared cache dicts simultaneously.
**What to change:** Wrap every lazy-init block in a `threading.Lock()` (one per model). Use `threading.local()` for request-scoped state. For production, consider initializing all models at server startup (not lazily) so the race window is eliminated entirely.

---

### U5 — ElevenLabs API Has No Application-Level Rate Limiting
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 1107–1133
**What it is:** Retry logic exists for 429 responses, but there is no global rate limiter or quota tracker at the application level. A burst from ~1000 concurrent users will hammer ElevenLabs simultaneously; retries amplify the problem by replaying failed requests. One traffic spike can exhaust the entire paid quota and cause service-wide TTS failure.
**What to change:** Implement a token-bucket or leaky-bucket rate limiter (e.g., `ratelimit` library or a Redis-backed counter) around all ElevenLabs calls. Add a circuit breaker (e.g., `pybreaker`) that trips after N consecutive 429/5xx responses and fast-fails for a configurable cooldown period instead of retrying indefinitely.

---

### U6 — `host_stats["ok"]` Validation Is Broken — Counts Silence as Success
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 1259–1267, 1325–1326
**What it is:** Failed TTS lines are replaced with generated silence files. The per-host success validator then checks if the output file exists — which it always does (it's the silence file) — and counts it as a successful render. The "silent host" guard is therefore completely ineffective and will never catch a host with 100% TTS failures.
**What to change:** Track success separately from file existence. Add a `success` flag or use a distinct filename suffix for silence-fallback files. `host_stats["ok"]` must count only lines where actual TTS audio was generated, not synthetic silence. (This also depends on resolving U1.)

---

## MAJORITY FINDINGS
*(2 of 2 models — implement unless compelling reason not to)*

> All findings are unanimous given only 2 models participated. See Unanimous Findings above. The items below were flagged with varying emphasis but both models cited them.

---

### M1 — Docstrings and Comments Are Materially False
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 917–918, 990, 1053
**What it is:**
- Docstring at 917–918 says host2 uses `Chatterbox PBX → Kokoro am_adam → ElevenLabs PBX` but code uses `Kokoro am_onyx → F5 → ElevenLabs`.
- Comment at 990 says `am_adam`; config says `am_onyx`.
- Docstring at 1053 says "Falls back to pyttsx3 system TTS, then silence" — pyttsx3 is nowhere in the file; the actual behavior is hard-fail.
**What to change:** All three must be corrected to match actual behavior. False docstrings cause operators to debug the wrong paths during production incidents.

---

### M2 — `sys.path` Mutation at Request Time Is Globally Dangerous
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 927–930
**What it is:** `tts_local()` mutates `sys.path` dynamically on every call. In a multi-threaded server, `sys.path` is global process state. Concurrent requests can corrupt each other's import environment mid-execution.
**What to change:** Move all `sys.path` mutations to module load time (top of file or `__init__`) or application startup. Never mutate `sys.path` inside a request-handling function.

---

### M3 — TTS Cache Key Is Incomplete — Stale Audio Served After Config Changes
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 722–726, 935
**What it is:** Cache key is `SHA256(text + voice + segment_type)` but excludes: backend type (pytorch/onnx), actual voice name, speed, model version, and normalization logic version. Local cache uses only `local_h{host}`. Changing `KOKORO_HOST2_VOICE`, speed, or pronunciation maps silently serves stale audio.
**What to change:** Include in the cache key: voice model name, backend identifier, speed parameter, and a normalization version hash (or a manually bumped `CACHE_VERSION` constant). Consider a cache-busting environment variable for forced invalidation on deploy.

---

### M4 — No Cache Eviction or Size Control
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 501, 750–753
**What it is:** `tts_cache` directory grows without bound. On a production server with continuous operation, this will eventually exhaust disk space and fail unpredictably.
**What to change:** Implement LRU eviction based on access time and a configurable `MAX_CACHE_SIZE_GB`. Use `os.stat().st_atime` or a SQLite manifest file tracking access times. Alternatively, use a caching library (`diskcache`, `joblib.Memory`) that handles eviction natively.

---

### M5 — Predictable Temp File Names Enable Collision Under Concurrency
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 779
**What it is:** Temp files use patterns like `output_path + ".kokoro.wav"` — deterministic and shared. Concurrent requests for the same or different audio can overwrite each other's temp files mid-generation.
**What to change:** Use `tempfile.NamedTemporaryFile(delete=False)` or incorporate a UUID/request-ID into every temp file name. Clean up explicitly in a `finally` block.

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluated individually)*

---

### UI1 — `dur` Variable Can Be Uninitialized (GPT-4o only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 1255–1273
**What it is:** GPT-4o identified that for very short valid text (≤10 chars like "Yes."), `_tts_ok` is True, file exists, size ≥ 1000, but the `dur < 0.5` validation branch is skipped, meaning `dur` may be appended to `lines` before being assigned in some code paths.
**Assessment: IMPLEMENT.** This is a real Python bug — `UnboundLocalError` or stale-value corruption depending on execution path. Initialize `dur = 0.0` at the top of the per-line loop block unconditionally.

---

### UI2 — `validate_tts_output()` Has Inconsistent Interface — Returns Bool But Can Raise (GPT-4o only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 958–961, 1152–1156, 1176–1179
**What it is:** Functions declared as returning `bool` actually raise `RuntimeError` in some branches. Call sites expect boolean return and don't catch exceptions, so validation errors abort the entire dialogue generation loop.
**Assessment: IMPLEMENT.** Either make validation consistently raise (and update all callers to handle it) or make it consistently return bool (and remove internal raises). The current mixed contract is a latent crash. Consistent exception-based error handling is the cleaner choice here.

---

### UI3 — `expand_numbers_for_tts()` Removes ALL "and" — Including Legitimate Prose (GPT-4o only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 428–431
**What it is:** The function removes every standalone "and" in the text to clean up num2words output like "one hundred and twenty." This mutilates normal prose: "Bitcoin and gold" → "Bitcoin gold". Audio output will sound broken for any compound sentence.
**Assessment: IMPLEMENT.** Scope the "and" removal strictly to numeric contexts using lookahead/lookbehind: only remove "and" when immediately preceded by a digit word or preceded/followed by another number word. A simple regex like `(?<=\d)\s+and\s+(?=\d)` on the pre-conversion numeral form is safer.

---

### UI4 — Pronunciation Regex Boundaries Unreliable for Tokens Containing `/` (GPT-4o only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 589–591, 676–677
**What it is:** Entries like `EH/s`, `TH/s`, `PH/s` use `\b...\b` word-boundary anchors. `\b` is a zero-width assertion between `\w` and `\W` characters. The `/` in these tokens means `\b` fires at the wrong positions and the substitution either fails silently or substitutes incorrectly.
**Assessment: IMPLEMENT.** For tokens containing punctuation, use explicit boundary patterns: `(?<!\w)EH/s(?!\w)` or escape the `/` and test boundary conditions with `(?:^|[\s,.()])`. Add unit tests for each special token.

---

### UI5 — `tts_chatterbox()` Exists But Is Never Called (GPT-4o only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 813–855
**What it is:** `tts_chatterbox()` is implemented but the docstring's described fallback chain doesn't match actual code and Chatterbox is never invoked anywhere in the live path.
**Assessment: INVESTIGATE FURTHER.** If Chatterbox is part of the product roadmap, it is dead code with a false interface contract. If it was intentionally removed, delete it and clean up the docstring. Do not leave unreachable production code with documented interfaces — it confuses operators and adds GPU memory risk (if it loads a model on import).

---

### UI6 — CLIP Entries Advance Timeline Without Silence Gap — Timing Discontinuities Possible (GPT-4o only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 1218–1231, 1281–1285
**What it is:** CLIP entries advance timeline by `clip_duration` but no silence padding is added before or after them, while all spoken-line pairs get 0.3s gaps. The downstream assembler may produce audio/video timing discontinuities at clip boundaries.
**Assessment: INVESTIGATE FURTHER.** Depends on downstream assembler behavior. If the assembler handles clip boundaries independently, this is fine. If it expects uniform inter-segment gaps, CLIP transitions will be tight. Requires assembler spec review before changing.

---

### UI7 — Bracket Stripping Only Removes First Leading Tag (GPT-4o only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 921, 1065
**What it is:** `re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text)` only strips a single leading `[TAG]`. Mid-sentence tags, trailing tags, and mixed-case tags pass through to TTS engines.
**Assessment: IMPLEMENT.** Change to `re.sub(r'\s*\[[A-Z_]+\]\s*', '', text)` (remove `^` anchor) to strip all instances. If mixed-case tags are intentional, document explicitly. Otherwise extend the character class.

---

### UI8 — API Key In-Memory Caching Without Encryption (Grok only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 217–223
**What it is:** API keys are fetched dynamically and cached in a plain dict in memory. No encryption or secure storage integration.
**Assessment: SKIP for now.** In-memory caching of env-var-derived keys is standard practice and does not represent a meaningful security regression vs. the env var itself. The real risk is the leaked key that killed Gemini — that's an operational/secret-management problem outside this file. Address via secrets manager (Vault, AWS Secrets Manager) at the infrastructure level, not in application code.

---

### UI9 — Bad Unicode Input Not Sanitized Before TTS or ffmpeg (Grok only)
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 920, 795
**What it is:** Text with invalid/unprintable Unicode characters passes directly to TTS engines and ffmpeg subprocess args without sanitization.
**Assessment: IMPLEMENT (lightweight).** Add `text = text.encode('utf-8', errors='replace').decode('utf-8')` or a `unicodedata.normalize('NFKC', text)` pass before any TTS call. For ffmpeg args, ensure filenames go through `shlex.quote()` or are passed as list args (not shell strings) to prevent injection.

---

## CONFLICTS
*(Models gave contradictory assessments)*

---

### C1 — Severity of Silent Failures / Overall Code Quality
**Grok** scored backend logic 75/100, calling the multi-TTS fallback strategy "robust." **GPT-4o** scored it 58/100, arguing that the silence-fallback bypass of the hard-fail policy is a "fatal contradiction" making the robustness illusory.

**Tiebreaker: GPT-4o is correct.** A fallback chain that appears robust but silently produces garbage audio is worse than one that fails loudly. The 3-second silence escape hatch at lines 1259–1267 means every defensive mechanism above it is decorative. Until U1 is fixed, the system's stated reliability guarantees are invalid. Score 58/100 is the more honest assessment.

---

### C2 — Law Compliance Score
**Grok** scored 40/100, penalizing heavily for assumed GDPR/WCAG requirements not stated in the spec. **GPT-4o** scored 65/100, noting the file is compliant with the stated Python 3.12/Flask 3.x/SQLAlchemy laws (most of which don't apply to this file).

**Tiebreaker: GPT-4o is more accurate on the stated facts.** This file has no Flask routes, no SQLAlchemy calls, and no PII handling. The GDPR/WCAG concerns Grok raised are legitimate product-level concerns but are not violations attributable to this specific file. Score this file 60–65/100 for law compliance as stated.

---

## VALIDATED STRENGTHS
*(Both models confirmed — do NOT change in second pass)*

---

1. **Multi-TTS Provider Strategy with Fallback Chain** (lines 943–956): The architecture of Kokoro → F5 → ElevenLabs with local-first preference is the correct design pattern for a production TTS pipeline. The intent is sound; only the execution of the fallback silence escape hatch undermines it.

2. **Pronunciation Mapping / Domain Normalization** (lines 508–608): Both models noted this is a thoughtful, domain-specific feature. Crypto-specific pronunciation normalization (BTC, ETH, satoshis, etc.) directly improves audio quality for the use case. The *implementation* of some regex boundaries needs fixing (UI4), but the *design* is valuable and correct.

3. **ElevenLabs Retry Logic Structure** (lines 1107–1133): 5-attempt retry with exponential back-off and 429 detection is the correct skeleton. The gap is application-level rate limiting *before* the API is called (U5), not the retry logic itself — which is well-structured.

4. **SHA256-Based Cache Key Foundation** (lines 722–726): The *concept* of content-addressed caching for TTS is correct and appropriate. The key needs additional fields (M3), but the hashing approach is sound.

5. **90-Second ElevenLabs Timeout** (line 1110): Explicit timeout on external API calls is correct production practice. Do not remove or increase it.

---

## LAW COMPLIANCE CONSENSUS

| Governing Requirement | Status | Finding |
|---|---|---|
| Python 3.12 | ✅ COMPLIANT | No Python 2 constructs observed |
| Flask 3.x | ✅ N/A in this file | No Flask routes in `tts_engine.py` |
| SQLite via SQLAlchemy ORM | ✅ N/A in this file | No DB operations |
| Ubuntu 24.04 / RTX 4090 hardware | ⚠️ PARTIAL | Code assumes single-server GPU; no admission control for GPU memory under concurrent load |
| ~1000 concurrent users target | ❌ VIOLATION | Thread-unsafe globals (U4), no rate limiting (U5), cache races (U2) collectively make this unsafe at target concurrency |
| Data privacy / secrets | ⚠️ PARTIAL | No PII in this file; API key handling is env-var based (acceptable); no vault integration |
| GDPR/WCAG | ⚠️ OUT OF SCOPE for this file | Valid product-level concerns but not attributable to `tts_engine.py` specifically |

**Final Determination:** The code violates the implicit law of supporting ~1000 concurrent users via multiple thread-safety failures. All other stated laws are either compliant or not applicable to this file.

---

## SECURITY CONSENSUS

| Priority | Issue | Both Models | Severity |
|---|---|---|---|
| 1 | No application-level rate limiting on ElevenLabs (U5) | ✅ Both | HIGH — quota exhaustion = service-wide TTS failure |
| 2 | Non-atomic cache writes allow corrupted audio (U2) | ✅ Both | HIGH — silent data corruption in production |
| 3 | Thread-unsafe global state (U4) | ✅ Both | HIGH — double model loads, state corruption |
| 4 | ffmpeg subprocess args not shell-safe (UI9) | ⚠️ 1 model | MEDIUM — potential command injection via malformed filenames |
| 5 | No circuit breaker on external dependencies (U5 related) | ✅ Both | MEDIUM — cascading failure risk |
| 6 | Predictable temp file names (M5) | ✅ Both | MEDIUM — collision under concurrency |
| 7 | Hardcoded voice IDs / model paths | ⚠️ 1 model | LOW — not meaningfully sensitive; use config files |

**No SQL injection or authentication bypass vectors identified** — correct, this file has no DB or auth logic.

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned)*

1. **No Circuit Breaker Pattern** — Both models flagged that retry logic alone is insufficient. Bloomberg, Coinbase, and Blockworks-grade infrastructure uses circuit breakers (e.g., `pybreaker`) that fast-fail during sustained outages rather than queuing retries that amplify load.

2. **No Observability / Metrics** — Both models noted zero telemetry: no Prometheus metrics for TTS success rate, API latency, cache hit ratio, or GPU utilization. A world-class audio pipeline reports on every generation with P50/P95/P99 latencies and alert thresholds.

3. **No Horizontal Scaling Path** — Both models flagged that the architecture is implicitly single-server. A world-class product separates TTS generation into a worker queue (Celery + Redis, or equivalent) so generation jobs can scale across multiple GPU nodes without shared-state races.

4. **Static Silence Gap (0.3s hardcoded)** — Both models noted the 0.3s gap is not content-aware. Production podcast platforms use prosody analysis or at minimum configurable per-show silence profiles. This is a product quality gap, not just a technical one.

5. **No