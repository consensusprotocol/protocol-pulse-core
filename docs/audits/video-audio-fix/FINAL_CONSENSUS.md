# CONSENSUS REPORT — VIDEO-AUDIO-FIX — CYCLE 2
Generated: 2026-03-09 14:07
Models: grok, gpt4o (+1 failed: gemini — 403 PERMISSION_DENIED, leaked API key)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | N/A | 4/10 | 4/10 | **4/10** |
| Law Compliance | N/A | 1/10 | 1/10 | **1/10** |
| Security | N/A | 5/10 | 5/10 | **5/10** |
| Frontend Quality | N/A | 4/10 | 4/10 | **4/10** |
| Backend / Pipeline Quality | N/A | 3/10 | 3/10 | **3/10** |
| **Overall** | N/A | **3.5/10** | **3.8/10** | **3.6/10** |

> ⚠️ Gemini failed due to leaked API key — scores reflect 2-model consensus only. Confidence in findings is still high; both remaining models independently converged on identical severity assessments.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — Missing Post-Render Forensic Checks
**What it is:** Neither TTS pipeline runs `blackdetect`, `silencedetect`, or `ebur128` (loudness) analysis after rendering audio. The stated laws explicitly require post-render forensic validation.
**Files:**
- `video_pipeline_v3/dual_host_tts.py:350-359`
- `video_pipeline_v3/tts_engine.py:388-397`

**What to change:** After final `ffmpeg` concatenation, invoke `ffprobe`/`ffmpeg` with `silencedetect`, `blackdetect` (if video), and `ebur128` filter. Log results. Abort or flag if silent audio exceeds threshold. Emit structured warning to upstream if quality degrades.

---

### U2 — No Loudness Normalization (-14 LUFS / -1 dBTP)
**What it is:** Neither TTS engine applies loudness normalization to output audio. Industry standard for streaming is -14 LUFS integrated, -1 dBTP true peak. This is both a law violation and a broadcast quality failure.
**Files:**
- `video_pipeline_v3/dual_host_tts.py` (post-concatenation step, no normalization pass)
- `video_pipeline_v3/tts_engine.py` (same)

**What to change:** Add a `ffmpeg loudnorm` two-pass normalization step after concatenation: `ffmpeg -i input.m4a -af loudnorm=I=-14:TP=-1:LRA=11 -ar 48000 output.m4a`. This must be the final audio output step before file is handed off.

---

### U3 — CLIP Timeline / Render Mismatch (Critical AV Sync Bug)
**What it is:** CLIP entries are logged in metadata but (a) `current_time` is never advanced for them, (b) `tts_engine.py` records CLIP duration as `0.0` while `dual_host_tts.py` records actual duration — creating inconsistent metadata between the two engines, and (c) no audio placeholder/silence is appended to `parts_for_concat` for CLIP duration, so the rendered full audio is shorter than the semantic script timeline.
**Files:**
- `video_pipeline_v3/dual_host_tts.py:292-303, 336-345`
- `video_pipeline_v3/tts_engine.py:326-337, 374-383`

**What to change:**
1. Both engines must advance `current_time` by the CLIP duration after each CLIP entry.
2. Both engines must record CLIP duration consistently (actual duration, not `0.0`).
3. Append a silence audio segment of the appropriate CLIP duration to `parts_for_concat` so the rendered full audio timeline matches the semantic script timeline.
4. Standardize CLIP handling into a shared utility if both engines must coexist.

---

### U4 — ElevenLabs Fallback Contract Contradiction
**What it is:** `tts_elevenlabs()` in both engines can fall back gracefully without an API key, but `generate_dialogue_audio()` in both engines hard-fails if the key is missing. This is a contradictory contract — the inner function handles missing keys, but the outer function refuses to proceed.
**Files:**
- `video_pipeline_v3/dual_host_tts.py:277-279`
- `video_pipeline_v3/tts_engine.py:311-313`

**What to change:** Either (a) make `generate_dialogue_audio()` consistent with the fallback behavior of `tts_elevenlabs()` by allowing graceful degradation with a logged warning, or (b) remove fallback logic from `tts_elevenlabs()` and make the hard-fail the single, honest behavior at the top level. Pick one contract and enforce it consistently throughout.

---

### U5 — Hero Episode Numbering Bug (Frontend)
**What it is:** `loop` is not defined in the hero section context. The Jinja2 expression `{{ loop.index if loop is defined else podcast_count }}` always falls back to `podcast_count`, which is the total episode count — not the episode number of `latest_episodes[0]`. Users see incorrect metadata.
**File:** `templates/media_unified.html:113`

**What to change:** Replace with the actual episode number field from the episode object: `{{ latest_episodes[0].episode_number }}` or the appropriate model attribute. Do not reference `loop` outside a `for` block.

---

### U6 — No Upstream Notification When Fallback Degradation Occurs
**What it is:** When ElevenLabs is unavailable and the pipeline falls back to pyttsx3 or silence, there is no structured signal emitted to upstream processes, orchestration layers, or monitoring. Degraded audio ships silently.
**Files:**
- `video_pipeline_v3/dual_host_tts.py:238-258` (fallback chain)
- `video_pipeline_v3/tts_engine.py:238-258` (fallback chain)

**What to change:** Emit a structured log entry (e.g., `{"event": "tts_fallback", "reason": "elevenlabs_unavailable", "engine": "pyttsx3|silence", "segment": ...}`) at WARNING level. Accumulate fallback counts and include in final return metadata so callers can inspect quality degradation.

---

### U7 — Silence Duration Fallback Estimate Is Inaccurate
**What it is:** When generating silence as a fallback, both engines estimate duration using `len(text) / 12.5`, a crude character-count heuristic. This is inaccurate across languages, punctuation density, and speaker rate variation, causing AV desync.
**Files:**
- `video_pipeline_v3/dual_host_tts.py:132-140`
- `video_pipeline_v3/tts_engine.py:141-155`

**What to change:** Use `pyttsx3`'s actual rendered duration when pyttsx3 is available, or use a calibrated word-count-based estimate (`len(text.split()) / 2.5` seconds at 150 wpm) rather than raw character count. Document the assumption explicitly.

---

## MAJORITY FINDINGS (2 of 2 models agree)

> Since only 2 models produced output, all findings where both agreed are listed as Unanimous above. The following were raised by one model and explicitly validated/confirmed by the other's Cycle 2 response.

### M1 — Fragile YouTube ID Extraction
**What it is:** The template assumes `ep.audio_url` is always a YouTube watch URL containing `v=`. CDN audio URLs, `youtu.be` shortlinks, embed URLs, and non-YouTube podcasts all produce `vid_id = ''`, breaking thumbnail and link rendering.
**File:** `templates/media_unified.html:120, 295-299`

**What to change:** Write a robust `extract_youtube_id(url)` helper that handles `watch?v=`, `youtu.be/`, `/embed/`, and returns `None` explicitly for non-YouTube URLs. Render thumbnail/link sections conditionally: `{% if vid_id %}...{% endif %}`.

---

### M2 — Signal Gauge Parameter Naming Mismatch
**What it is:** `renderSignalGauge()` is documented/named as accepting `spacesScore` but the caller passes `spacesCount`. The renderer then multiplies by 10 again, producing a "correct" result only by accident. If caller ever passes actual score, displayed value doubles.
**File:** `templates/media_unified.html:635-654, 745-748`

**What to change:** Either rename the parameter to `spacesCount` and document that the function converts internally, or have the caller pass `spacesScore` consistently. Eliminate the accidental double-multiplication. Add a comment explaining the expected unit of each argument.

---

### M3 — Invalid HTML: `<button>` Nested Inside `<a>`
**What it is:** A `<button>` is nested inside an `<a>` tag, which is invalid per HTML5 spec (interactive content cannot be nested). Behavior is undefined and varies by browser and assistive technology.
**File:** `templates/media_unified.html:404-412`

**What to change:** Restructure so the `<button>` and `<a>` are siblings, or convert one to a non-interactive element with JS event handling. Use `<div role="button" tabindex="0">` if button-like behavior is needed inside a link container.

---

### M4 — No `regression_test.sh` Integration / Gate
**What it is:** Neither TTS pipeline triggers or integrates with `regression_test.sh`. Per the project's stated laws, the regression gate must pass before a build is considered shippable. No evidence of this gate running.
**Files:**
- `video_pipeline_v3/dual_host_tts.py`
- `video_pipeline_v3/tts_engine.py`
- CI/CD pipeline configuration (not reviewed but implied missing)

**What to change:** Ensure `regression_test.sh` is called as part of the post-render validation step, or confirmed to run in CI. The `generate_dialogue_audio()` return value should include a `regression_gate_passed: bool` field or the pipeline should fail explicitly if the gate fails.

---

### M5 — TTS Cache Key Omits Voice Settings
**What it is:** The cache key in `tts_engine.py` uses only `text + voice_id + segment_type`. If ElevenLabs voice settings (stability, similarity boost, speed mode) change, the cache will silently serve stale audio with old characteristics.
**File:** `video_pipeline_v3/tts_engine.py:114-118, 184-206`

**What to change:** Include a hash of the full voice settings dict (stability, similarity_boost, style, use_speaker_boost, model_id) in the cache key. Add cache version invalidation on settings changes.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### From GPT-4o

**N1 — CLIP Durations Not Included in Concatenated Audio (silence placeholder absent)**
- **Assessment: IMPLEMENT — HIGH PRIORITY (promotes to P0 alongside U3)**
- Reinforces and deepens U3. Even if metadata were fixed, `full_dialogue.m4a` excludes CLIP time entirely. This is not just a metadata bug — it's a rendered artifact defect. The audio file is physically shorter than the script timeline.
- **File:** `dual_host_tts.py:292-303, 336-345` | `tts_engine.py:326-337, 374-383`

**N2 — Silence Gap Added After Spoken Line Even When Next Entry Is CLIP**
- **Assessment: IMPLEMENT — MEDIUM PRIORITY**
- Combining with CLIP placeholder insertion (N1/U3 fix), this creates double dead air before clips. The silence gap logic needs to be conditional on the *type* of the next entry.
- **File:** `dual_host_tts.py:323-325` | `tts_engine.py:359-362`

**N3 — Fetch Helpers Don't Check `response.ok` Before Parsing JSON**
- **Assessment: IMPLEMENT — HIGH PRIORITY**
- `fetchSentiment`, `fetchSpaces`, `fetchTradfi` all call `.json()` on potentially non-2xx responses. HTML error bodies will throw parse exceptions and collapse into silent fallback behavior, completely obscuring service failures from observability.
- **File:** `templates/media_unified.html:592-605, 616-617`
- **Fix:** Add `if (!r.ok) throw new Error(\`HTTP ${r.status}\`);` before every `.json()` call.

**N4 — Health Dot Classes Can Accumulate Stale States**
- **Assessment: IMPLEMENT — LOW EFFORT, MEDIUM IMPACT**
- The health dot element may retain `connected` class while `error` class is added (or vice versa), creating ambiguous visual state if CSS specificity doesn't predictably resolve the conflict.
- **File:** `templates/media_unified.html:718-720`
- **Fix:** Before adding the new state class, call `el.classList.remove('connected', 'error', 'loading')` then add the correct one.

**N5 — `countEl` Queried But Never Used in Relay Socket Loop**
- **Assessment: INVESTIGATE — LOW PRIORITY**
- Dead code indicating incomplete implementation. Could mask an intended relay count display that was cut. Low severity but should be resolved (either implement or remove).
- **File:** `templates/media_unified.html:669`

**N6 — `_mp3_to_m4a()` Helper Is Misnamed / Semantically Misleading**
- **Assessment: IMPLEMENT — LOW EFFORT**
- The function name implies MP3→M4A conversion but may perform a different operation. Misleading names cause silent bugs in maintenance. Rename to reflect actual behavior.
- **File:** `video_pipeline_v3/tts_engine.py` (helper function)

### From Grok

**G1 — No Cache Expiration / Invalidation Logic in TTS Cache**
- **Assessment: IMPLEMENT — pairs with M5**
- Grok identified the absence of TTL or invalidation on the TTS cache. Combined with GPT-4o's finding that cache keys omit voice settings, this means stale audio can persist indefinitely. These two findings together constitute a cache correctness P1.
- **File:** `video_pipeline_v3/tts_engine.py:111-138`

**G2 — No Error Logging for `ffmpeg` Concatenation Failures**
- **Assessment: IMPLEMENT — MEDIUM PRIORITY**
- If `ffmpeg` fails during concatenation, the pipeline produces no output silently and falls back to `current_time` as total duration. This masks critical failures.
- **File:** `dual_host_tts.py:339-350` | `tts_engine.py:376-386`
- **Fix:** Wrap `ffmpeg` subprocess call in try/except, log stderr, raise or return structured error if exit code is non-zero.

**G3 — Hardcoded 5-Second Health Check Timeout**
- **Assessment: INVESTIGATE — LOW PRIORITY**
- 5 seconds may be appropriate; this is environment-dependent. Make it a named constant or config value at minimum. Not a blocker.
- **File:** `templates/media_unified.html:768`

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1 — Severity of Race Condition in `syncRelayStatusBar`
**Grok** called this a race condition requiring synchronization.
**GPT-4o** called it "brittle global coupling / consistency risk" rather than a true race condition, noting lower severity.

**Tiebreaker — GPT-4o is more precise here.** In a single-threaded JS event loop, true race conditions in the classical sense don't occur. The actual risk is stale reads of `window.relayManager.sockets` between polling intervals, which is a consistency/coupling concern. Rename the finding to "global state coupling in relay status polling" and treat it as P2. Synchronization primitives are not the right fix — the right fix is encapsulating relay state access behind a getter or observable pattern.

---

### Conflict 2 — Client-Side Newsletter Duplicate/Rate-Limit Handling
**Grok** flagged this as a client-side correctness issue.
**GPT-4o** classified it as "primarily server-side" responsibility.

**Tiebreaker — GPT-4o is correct.** Deduplication and rate limiting are server-side guarantees that cannot be enforced client-side. Client-side debouncing of the submit button (disable after click, re-enable on response) is appropriate UX hardening but is not a correctness fix. Treat as P2 UX polish.

---

### Conflict 3 — HEAD Request Health Checks (Severity)
**Grok** raised this as a potential false-negative issue.
**GPT-4o** agreed but noted it is endpoint-specific and unconfirmed.

**Tiebreaker — Both are right at different confidence levels.** The safe engineering default is: use `GET` for health checks unless you control the endpoint and have confirmed `HEAD` support. Switch to `GET` requests with a short timeout and discard the response body. This eliminates the risk at zero cost. Treat as P1.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

> Neither model identified areas of unambiguous strength to preserve. This is itself a signal: the codebase lacks areas of exemplary quality in the reviewed files. The closest to "validated" is:

- **ElevenLabs → pyttsx3 → silence fallback chain structure** — the *intent* of multi-tier fallback is correct and appropriate for production resilience. The *implementation* has bugs (see U4, U6, U7), but the architectural pattern should be preserved and fixed, not replaced.
- **`Promise.allSettled` usage for telemetry API calls** — using `allSettled` instead of `Promise.all` is the correct choice to prevent one API failure from collapsing all telemetry. The issue is in the failure-state rendering, not the choice of combinator.

---

## LAW COMPLIANCE CONSENSUS

### Violated Laws (both models confirm)

| Law | Violation | Severity |
|---|---|---|
| Post-render forensic validation (`silencedetect`, `blackdetect`, `ebur128`) | Neither TTS engine runs any post-render forensic checks | **Critical** |
| Loudness normalization (-14 LUFS / -1 dBTP) | No normalization pass in either engine | **Critical** |
| AV sync integrity | CLIP timeline not reflected in rendered audio; `current_time` not advanced | **Critical** |
| Regression gate (`regression_test.sh`) | No evidence of integration in pipeline or CI | **Critical** |
| Upstream degradation signaling | Silent fallback without structured notification | **High** |

### Compliant Laws
- None confirmed fully compliant in reviewed files.

### Final Determination
**The codebase is in active violation of at minimum 4 explicit protocol laws. Law Compliance score: 1/10. This code cannot ship in its current state.**

---

## SECURITY CONSENSUS

Both models scored security at **5/10**. No critical CVEs were identified in the reviewed code, but the following issues were flagged by both:

1. **No client-side rate limiting on newsletter subscription endpoint** — potential spam vector; server must enforce, but client has no debounce protection. (`media_unified.html:468-480`)
2. **API key management** — ElevenLabs key handling relies on environment variable presence without any validation or rotation mechanism. (`tts_engine.py:111`, `dual_host_tts.py` equivalent)
3. **Fetch error responses not checked before JSON parsing** — could expose internal error messages or cause unhandled exceptions that leak state information to browser console. (`media_unified.html:592-617`)
4. **No CSP or subresource integrity evidence** in the reviewed template — external script `media_unified_v5.js` loaded without integrity hash.

**Priority order:**
1. Validate `response.ok` before parsing fetch responses (N3) — prevent error body exposure
2. Add submit button debounce to newsletter form — prevent spam
3. Audit ElevenLabs key validation at startup — fail fast on misconfiguration
4. Add SRI hash to external JS include

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by both models that separate this from a world-class pipeline:

### Gap 1 — No Observability / Telemetry on Pipeline Quality
Both models noted silent failures throughout the TTS pipeline. A world-class audio pipeline emits structured telemetry for every render: duration rendered, fallback engine used, loudness measured, forensic check results, cache hit/miss ratio. None of this exists. Operators are flying blind.

### Gap 2 — No Unified CLIP/Timeline Abstraction
Both models identified that CLIP handling is an afterthought bolted onto two divergent engines. A world-class pipeline has a single canonical `Timeline` object that all engines write to, with CLIP, SPEECH, and SILENCE as first-class timeline segment types. The rendered audio is derived from the timeline, not the other way around.

### Gap 3 — Dual Engine Divergence Without Reconciliation
Having `dual_host_tts.py` and `tts_engine.py` implement the same pipeline with subtle behavioral differences (CLIP duration, cache keys, fallback contracts) is a world-class quality failure. A production codebase has one implementation or a shared base class with validated overrides. Divergence guarantees bugs accumulate silently.

### Gap 4 — Frontend Runtime Coupling (Inline + External JS Conflict)
Both models flagged the tension between `media_unified_v5.js` and the large inline runtime. A world-class frontend has a single runtime with clear module boundaries. The current approach of "inline script patching an external runtime" is a maintainability and debugging catastrophe waiting to happen.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Fix CLIP timeline: advance `current_time`, unify duration semantics, append silence placeholder to concat list | `dual_host_tts.py:292-345` `tts_engine.py:326-383` | both | Rendered audio shorter than script timeline; direct AV sync failure |
| **P0 CRITICAL** | Add post-render forensic suite: `silencedetect`, `ebur128` after concatenation; abort/flag on failure | `dual_host_tts.py:350-359` `tts_engine.py:388-397` | both | Explicit law violation; silent audio ships undetected |
| **P0 CRITICAL** | Add loudness normalization: `ffmpeg loudnorm` two-pass `-14 LUFS / -1 dBTP` as final output step | `dual_host_tts.py` `tts_engine.py` (post-concat) | both | Explicit law violation; broadcast quality failure |
| **P0 CRITICAL** | Resolve ElevenLabs fallback contract contradiction: pick one consistent behavior at all call sites | `dual_host_tts.py:277-279` `tts_engine.py:311-313` | both | Contradictory API contract causes undefined pipeline behavior |
| **P0 CRITICAL** | Integrate `regression_test.sh` as a pipeline gate; fail build if gate fails | CI config + both TTS scripts | both | Explicit law violation; no quality gate exists |
| **P0 CRITICAL** | Silence gap must be conditional: do not insert gap after spoken line if next entry is CLIP | `dual_host_tts.py:323-325` `tts_engine.py:359-362` | gpt4o (unique, validated) | Creates double dead air when CLIP placeholder fix is applied |
| **P1 HIGH** | Fix hero episode numbering: replace `loop.index` fallback with `latest_episodes[0].episode_number` | `media_unified.html:113` | both | Always displays wrong episode number; user-facing data integrity failure |
| **P1 HIGH** | Add structured fallback degradation signal: log `{"event":"tts_fallback",...}`

---

# WINNER DETERMINATION

WINNER: GPT-4o — It delivered the most precise, line-referenced, technically specific findings in Cycle 1, identifying concrete bugs (hero episode numbering fallback logic, nested `<button>`-in-`<a>` invalidity, YouTube ID extraction fragility, CLIP timeline inconsistency, ElevenLabs API contract contradiction) that were independently confirmed in Cycle 2 by both models, demonstrating superior accuracy and depth; its recommendations were consistently actionable with exact file paths and line numbers, and its Cycle 2 self-correction was honest, structured, and comprehensive rather than performative.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered implementation list based on severity, consensus confidence, and blast radius.

---

## P0 — CRITICAL / BLOCKING (implement before any merge)

**P0-1 — Add Post-Render Forensic Checks (U1)**
- Files: `dual_host_tts.py:350-359`, `tts_engine.py:388-397`
- After final `ffmpeg` concat, run `silencedetect`, `ebur128`, and `blackdetect` (if video output)
- Log structured results; abort pipeline and raise exception if silence exceeds threshold (e.g., >500ms contiguous silence in non-intentional segments)
- Emit upstream warning payload on quality degradation
- Law compliance blocker — do not ship without this

**P0-2 — Add Loudness Normalization Pass (U2)**
- Files: `dual_host_tts.py`, `tts_engine.py` (post-concatenation step)
- Implement `ffmpeg loudnorm` two-pass: `-af loudnorm=I=-14:TP=-1:LRA=11:print_format=json`
- Run analysis pass first, feed measured values into correction pass
- Output must target -14 LUFS integrated / -1 dBTP true peak before delivery
- Broadcast/streaming compliance blocker

**P0-3 — Fix CLIP Timeline Inconsistency**
- Files: `dual_host_tts.py:292-303`, `tts_engine.py:326-337`
- `tts_engine.py` stores CLIP duration as `0.0` while `dual_host_tts.py` stores actual duration
- Fix `tts_engine.py` to record real CLIP duration; verify `current_time` advances correctly for all entry types in both files
- AV sync will silently desync on any timeline with CLIP entries — this is a correctness blocker

**P0-4 — Resolve ElevenLabs Fallback vs. Hard-Fail Contract Contradiction**
- Files: `dual_host_tts.py:277-279`, `tts_engine.py:311-313`
- `tts_elevenlabs()` silently falls back when key is missing; `generate_dialogue_audio()` hard-fails if key is missing
- These are contradictory contracts on the same codepath
- Decision required: pick one strategy, implement consistently, document it explicitly
- Silent fallback to pyttsx3 in production without operator awareness is a data quality risk

---

## P1 — HIGH SEVERITY (implement in same sprint)

**P1-1 — Fix Hero Episode Number Logic Bug**
- File: `templates/media_unified.html:113`
- `loop` is not defined at that render site; always falls back to `podcast_count`
- Replace with `latest_episodes[0].episode_number` or equivalent explicit field
- Visible user-facing correctness bug on every page load

**P1-2 — Harden YouTube ID Extraction**
- Files: `templates/media_unified.html:120, 295-299`
- Current logic assumes `audio_url` is a YouTube watch URL with `?v=` parameter
- Handle: `youtu.be/` shortlinks, `/embed/` URLs, non-YouTube CDN URLs, missing query params
- Fallback gracefully to placeholder thumbnail rather than broken `img` src
- Broken thumbnails and links affect every non-standard episode URL

**P1-3 — Remove Invalid Nested Interactive Elements**
- File: `templates/media_unified.html:404-412`
- `<button>` nested inside `<a>` is invalid HTML per spec
- Refactor: use one element (prefer `<a>` with button styling, or `<button>` with JS navigation)
- Causes inconsistent click behavior and fails accessibility audits (WCAG 4.1.1)

**P1-4 — Fix Signal Gauge Parameter Mismatch**
- File: `templates/media_unified.html:635-654, 745-748`
- `renderSignalGauge()` parameter named `spacesScore` but caller passes `spacesCount`; renderer multiplies by 10 internally
- Currently "works by accident" — will silently break if either side changes
- Rename parameter to match semantic intent; remove implicit ×10 multiplication or make it explicit with a documented constant

---

## P2 — MEDIUM SEVERITY (implement before next release)

**P2-1 — Add Client-Side Rate Limiting to Newsletter Subscription**
- File: `templates/media_unified.html:468-480`
- No duplicate email check or submission debounce on client side
- Add: debounce on submit button (disable after click), localStorage flag to prevent re-submission within session, surface specific error messages from API response rather than generic fallback

**P2-2 — Harden Telemetry Failure State Rendering**
- File: `templates/media_unified.html:731-752` (updateTelemetry)
- `Promise.allSettled` used but rejected states not mapped to UI feedback
- If all API calls fail, show explicit stale-data indicator rather than silently displaying last-known or null values

**P2-3 — Synchronize Relay Status Bar Access**
- File: `templates/media_unified.html:659-700` (syncRelayStatusBar)
- `window.relayManager.sockets` accessed without guard every 5 seconds
- Add null/undefined guard before access; consider debouncing concurrent update triggers

**P2-4 — Audit HEAD-Method Health Checks for False Negatives**
- File: `templates/media_unified.html:763-773`
- Some endpoints do not correctly implement `HEAD` — returns 405 or incorrect status
- Either switch to `GET` with body abort, or maintain an explicit allowlist of endpoints that correctly support `HEAD`

---

## P3 — LOW SEVERITY / HARDENING (next maintenance window)

**P3-1 — Decouple Inline Runtime from External JS Globals**
- File: `templates/media_unified.html:466, 576-807`
- Inline script assumes `window.relayManager`, `window.state.nostrNotes` set by `/static/js/media_unified_v5.js`
- Add explicit guard checks with console warnings if globals are absent at runtime
- Prevents silent breakage if external script load fails or load order changes

**P3-2 — Document Fallback Chain for TTS Engines**
- Files: `dual_host_tts.py`, `tts_engine.py`
- ElevenLabs → pyttsx3 → silence fallback chain is implicit and undocumented
- Add docstring or inline comment explicitly describing fallback order, conditions, and operator visibility expectations

**P3-3 — Add Structured Logging to Pipeline Quality Events**
- Files: `dual_host_tts.py`, `tts_engine.py`
- Quality events (fallback triggered, silence detected, normalization applied) should emit structured log entries consumable by monitoring systems
- Enables alerting without requiring log string parsing