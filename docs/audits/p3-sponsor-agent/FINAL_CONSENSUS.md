# CONSENSUS REPORT — P3-SPONSOR-AGENT — CYCLE 2
Generated: 2026-03-09 14:18
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 2/10 | 3/10 | 3/10 | **2.7/10** |
| Law Compliance | 0/10 | 0/10 | 0/10 | **0/10** |
| Security | 6/10 | 6/10 | 5/10 | **5.7/10** |
| Frontend Quality | 3/10 | 4/10 | 4/10 | **3.7/10** |
| Backend Quality | 3/10 | 4/10 | 4/10 | **3.7/10** |
| World-Class Gap | 2/10 | 3/10 | 3/10 | **2.7/10** |
| **Overall** | **2.7/10** | **3.3/10** | **3.2/10** | **3.1/10** |

> **Consensus note:** Gemini scored most harshly overall, driven by the confirmed canvas spec violation and cache invalidation bug. GPT-4o and Grok converged tightly. The 3.1 overall is a meaningful downgrade from initial impressions and reflects two irreducible facts: (1) the feature is not implemented, (2) the code that does exist has a P0 desync bug in its primary output.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — CLIP Entry Audio Desynchronization
**What it is:** When a script entry has `host == "CLIP"`, both TTS files record metadata about the clip but skip appending any audio (silence placeholder) and fail to advance `current_time`. The result: all spoken audio after the first CLIP plays too early, permanently breaking subtitle/video timeline alignment.

**Files/Lines:**
- `video_pipeline_v3/dual_host_tts.py:292–303`
- `video_pipeline_v3/tts_engine.py:326–337` (additionally stores `duration: 0.0`, compounding the error)

**What to change:**
1. Generate silence audio of `clip_dur` seconds (via ffmpeg or equivalent).
2. Append that silence to `parts_for_concat`.
3. Advance `current_time += clip_dur`.
4. In `tts_engine.py`, record the actual duration, not `0.0`.

---

### U2 — Redundant Duplicate TTS Engines
**What it is:** `dual_host_tts.py` and `tts_engine.py` are near-identical files. `tts_engine.py` is the superset (adds caching, voice modes, better fallback handling). Keeping both guarantees that bug fixes applied to one will be missed in the other, as already demonstrated by the inconsistent `duration: 0.0` in `tts_engine.py`.

**Files/Lines:**
- `video_pipeline_v3/dual_host_tts.py` — entire file

**What to change:**
1. Audit all callers of `dual_host_tts.py`.
2. Migrate each caller to use `tts_engine.py` equivalents.
3. Delete `video_pipeline_v3/dual_host_tts.py`.
4. Add a single-line tombstone comment in `tts_engine.py`: `# Supersedes dual_host_tts.py (removed YYYY-MM-DD)`.

---

### U3 — All Four Governing Laws Entirely Unimplemented
**What it is:** The submitted codebase (`media_unified.html`, `dual_host_tts.py`, `tts_engine.py`) is a media hub + TTS pipeline. It contains zero implementation of the `p3-sponsor-agent` feature as defined by the governing laws. This is a catastrophic scope mismatch: the wrong code was audited against the wrong spec.

**Laws violated:**
- LAW 1 — No Grok-3 prospect research, no `sponsors` table writes.
- LAW 2 — No hyper-personalized outreach, no Claude Sonnet draft generation.
- LAW 3 — No pipeline persistence, no `sponsor_activity_log`, no soft-delete.
- LAW 4 — No Resend email integration, no deliverability tracking.

**What to change:** Before any other fix is meaningful for this feature label, the actual sponsor agent must be built or the correct files must be submitted for audit. This is the single highest-priority blocker in this entire report.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Weak Email Validation / No In-Flight Guard on Newsletter Subscribe
**Models:** Grok + GPT-4o
**File/Line:** `templates/media_unified.html:468–480`
**What to change:**
- Replace the `'@'` check with a proper regex or HTML5 `type="email"` + `reportValidity()` pattern.
- Disable the submit button on first click; re-enable on response completion to prevent request spamming.
- Verify whether the endpoint requires CSRF token and add one if so.

---

### M2 — XSS Risk Pattern in Dynamic Content Rendering
**Models:** Grok + GPT-4o (GPT-4o specifically flagged `innerHTML` string concatenation at health strip `780–789`)
**File/Line:** `templates/media_unified.html:780–789` (health strip); also Nostr feed dynamic injection
**What to change:**
- Audit every `innerHTML` assignment that incorporates any non-literal string.
- Replace with `textContent` for text values, or use a sanitizer for HTML.
- Even if current values are constants, the pattern is exploitable the moment any field becomes API-driven — establish the correct pattern now.

---

### M3 — NaN Propagation in Signal Gauge Computation
**Models:** Gemini + GPT-4o
**File/Line:** `templates/media_unified.html:626–633`, `746–748`
**What to change:**
```javascript
// Before
const sentScore = parseFloat(sentData.composite_score);
// After
const sentScore = parseFloat(sentData?.composite_score) || 0;
```
Guard all `parseFloat` calls feeding into `computeSignalStrength()` and `renderSignalGauge()`. Add a final `isNaN(score) ? 0 : score` guard before DOM write.

---

### M4 — Invalid HTML: `<button>` Nested Inside `<a>`
**Models:** Gemini + GPT-4o
**File/Line:** `templates/media_unified.html:404–412`
**What to change:**
- Replace `<a href="..."><button>...</button></a>` with either:
  - `<a href="..." role="button" class="...">...</a>` styled as a button, or
  - `<button onclick="window.location='...'">...</button>` if navigation is JS-driven.
- This is invalid per HTML spec and breaks keyboard/screen-reader behavior.

---

### M5 — HEAD Requests for Health Checks Are Fragile in Production
**Models:** GPT-4o + Grok
**File/Line:** `templates/media_unified.html:755–790`
**What to change:**
- Change health check requests from `HEAD` to `GET` (or add `GET` as fallback on fetch failure).
- For cross-origin endpoints, ensure CORS allows the check or proxy through the backend.
- Add a `signal: AbortController` timeout (~3s) to prevent health checks from hanging indefinitely.

---

### M6 — `setInterval` Polling Creates Request Dogpiling Risk
**Models:** Gemini + Grok
**File/Line:** `templates/media_unified.html:793–803`
**What to change:**
Replace `setInterval` with chained `setTimeout`:
```javascript
// Before
setInterval(updateTelemetry, 30000);

// After
async function scheduleTelemetry() {
  await updateTelemetry();
  setTimeout(scheduleTelemetry, 30000);
}
scheduleTelemetry();
```
Apply the same pattern to `syncRelayStatusBar` and `updateHealthStrip`. This ensures the next call never fires until the previous one completes, preventing concurrent hammering on slow networks.

---

### M7 — Silent Fallback Degradation Without Logging
**Models:** Grok + GPT-4o
**File/Line:** `video_pipeline_v3/tts_engine.py:238–258`
**What to change:**
- Add explicit `logging.warning()` calls at each fallback tier: `"ElevenLabs failed — falling back to pyttsx3"` and `"pyttsx3 failed — falling back to silence"`.
- Increment a metric counter (even a simple file-based counter or statsd call) so operators can detect systemic API degradation.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X1 — Canvas Spec Violation (Gemini only)
**Verdict: IMPLEMENT**
`<canvas>` elements are present at `templates/media_unified.html:24, 33, 42` for sparklines. If "NO Canvas" is a hard stack rule, this is a direct violation regardless of severity. Replace with SVG-based sparklines (lightweight, accessible, zero additional dependencies). If the rule is not formally documented, confirm with the team and document it.

---

### X2 — TTS Cache Key Does Not Include Voice Settings (Gemini only)
**Verdict: IMPLEMENT**
**File/Line:** `video_pipeline_v3/tts_engine.py:114`
The cache key hashes `text + voice_id + segment_type` but excludes `stability`, `style`, `speed`. Tuning voice parameters will silently serve stale audio until manual cache bust.
```python
# Add to cache key generation:
settings_hash = hashlib.md5(
    json.dumps(voice_settings, sort_keys=True).encode()
).hexdigest()[:8]
cache_key = f"{text_hash}_{voice_id}_{segment_type}_{settings_hash}"
```

---

### X3 — `generate_dialogue_audio()` Hard-Fails Before Fallback Can Execute (GPT-4o only)
**Verdict: IMPLEMENT**
**File/Line:** `video_pipeline_v3/dual_host_tts.py:277–279`, `video_pipeline_v3/tts_engine.py:311–313`
The orchestrator raises immediately if the API key is missing, making the documented pyttsx3 fallback path unreachable. If fallback mode is intended for offline/dev use, move the key check inside `tts_elevenlabs()` only (where it already exists) and remove the early raise from the orchestrator. If fallback is NOT intended, remove the fallback code and document the hard requirement.

---

### X4 — `_mp3_to_m4a()` Used to Convert WAV Output (GPT-4o only)
**Verdict: INVESTIGATE FURTHER**
**File/Line:** `video_pipeline_v3/dual_host_tts.py:213`, `video_pipeline_v3/tts_engine.py:247`
pyttsx3 fallback writes a `.wav` file, then calls `_mp3_to_m4a()`. ffmpeg will handle this by format inference, so it likely works, but the abstraction is misleading and fragile. Rename to `_audio_to_m4a()` and add a comment explaining the format agnosticism. Low severity but a real maintenance trap.

---

### X5 — Silence Gap Added Before CLIP May Double-Count Duration (GPT-4o only)
**Verdict: INVESTIGATE FURTHER**
**File/Line:** `video_pipeline_v3/dual_host_tts.py:323–325`, `video_pipeline_v3/tts_engine.py:359–362`
After fixing U1, verify whether the standard inter-line silence gap should be suppressed when the next entry is a CLIP. If CLIP duration already accounts for the full transition, the extra 0.3s gap produces a doubled pause. Review with the video editor spec before finalizing the U1 fix.

---

### X6 — `fetchTradfi()` Is Dead Work Every 30 Seconds (GPT-4o only)
**Verdict: IMPLEMENT**
**File/Line:** `templates/media_unified.html:614–623`, `731–748`
`fetchTradfi()` is called and cached but its result is never used in `updateTelemetry()` or anywhere in the UI. Either wire it to a UI element or remove the call. Gratuitous network load on every client every 30 seconds with zero benefit.

---

### X7 — Relay URL Parsing Is Brittle (Gemini only)
**Verdict: INVESTIGATE FURTHER**
**File/Line:** `templates/media_unified.html:664, 693`
`url.replace('wss://','').split('/')[0]` will silently mismap relays with ports (`relay.example.com:8080`) or non-standard paths. Use `new URL(url).hostname` for robust parsing. Low risk if current relay set is stable; high risk if relay configuration becomes dynamic.

---

### X8 — Hardcoded Speed Value Inconsistency Between TTS Files (Grok only)
**Verdict: SKIP (until U2 resolved)**
`dual_host_tts.py` hardcodes `speed: 1.10` while `tts_engine.py` applies speed conditionally per segment type. This inconsistency is resolved by deleting `dual_host_tts.py` per U2. No separate fix needed.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Severity of CORS/HEAD Health Check Issue
- **GPT-4o:** Production blocker — will show false DOWN states.
- **Grok:** P2 medium — GET fallback is available.
- **Gemini:** P1 high — production risk.

**Tiebreaker: GPT-4o and Gemini are correct.** Health checks showing false DOWN states undermine operational trust and could trigger unnecessary incident response. Classify as **P1**. The fix is trivial (change `HEAD` to `GET`, add timeout), so the cost/benefit favors fixing it before ship.

---

### C2 — Severity of Global Shim `window._ppBlendXSpaces`
- **Gemini:** Brittle, non-modular, maintainability smell.
- **GPT-4o:** Partially agree — classify as smell, not blocker.
- **Grok:** Not flagged.

**Tiebreaker: GPT-4o is correct.** This is a maintainability concern, not a correctness or security bug. Classify as **P2**. Document the shim's contract with a comment and add it to the refactor backlog, but do not block ship on it.

---

### C3 — Whether to Delete `dual_host_tts.py` Immediately vs. Freeze-and-Migrate
- **Gemini:** Delete immediately.
- **GPT-4o:** Freeze, migrate callers, then delete (phased).
- **Grok:** Delete immediately.

**Tiebreaker: GPT-4o's phased approach is operationally safer**, but the outcome must be the same: deletion. The freeze-migrate-delete sequence is the correct engineering process. However, given the code is pre-ship and not in production, the migration can happen in the same PR as the deletion. Classify the deletion as **P0** with the caveat that caller migration must be verified by tests before merge.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> **Honest assessment:** The three-model consensus found no subsystem to validate as excellent. The closest observations:

- **Graceful cache fallback in `fetchSentiment()` and `fetchSpaces()`** — all models noted that cached fallback data on API failure is a reasonable pattern. Do not remove it. Do harden it per M5/M6.
- **pyttsx3 fallback chain concept** — the *intent* of multi-tier fallback in `tts_engine.py` is architecturally sound. The *execution* needs the logging fix (M7) and the hard-fail fix (X3), but the design principle is correct. Do not remove the fallback chain.
- **Modular fetch functions (`fetchSentiment`, `fetchSpaces`, `fetchTradfi`)** — separating polling concerns into named functions is good structure. Extend this pattern, don't flatten it.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Finding |
|---|---|---|
| LAW 1 — Grok Deep Research, never hallucinate | 🔴 **VIOLATED** | Zero implementation. No Grok-3 calls, no `sponsors` table, no intelligence storage. |
| LAW 2 — Hyper-personalized outreach, never generic | 🔴 **VIOLATED** | Zero implementation. No Claude Sonnet drafts, no `sponsorship_metrics_service.py` integration. |
| LAW 3 — Pipeline is sacred, no data loss | 🔴 **VIOLATED** | Zero implementation. No `sponsor_activity_log`, no soft-delete, no backup. |
| LAW 4 — Email via Resend | 🔴 **VIOLATED** | Zero implementation. No Resend SDK usage, no deliverability tracking. |

**Final determination: 0/4 laws compliant. This is not a partial implementation — it is a complete absence of the feature.** The reviewed code serves a different subsystem entirely. The audit cannot certify this codebase as `p3-sponsor-agent` compliant under any interpretation.

---

## SECURITY CONSENSUS

| Priority | Issue | Models | File/Line |
|---|---|---|---|
| S1 | XSS via `innerHTML` with dynamic/API-derived strings | Grok, GPT-4o | `media_unified.html:780–789` |
| S2 | No CSRF protection on newsletter subscribe | GPT-4o | `media_unified.html:468–480` |
| S3 | No rate limiting on ElevenLabs API retries | Grok | `tts_engine.py:220–221` |
| S4 | No in-flight guard on repeated newsletter submit clicks | GPT-4o, Grok | `media_unified.html:468–480` |
| S5 | API keys retrieved at runtime — no validation of key format before use | All (implied) | `tts_engine.py: key retrieval` |

**No critical, immediately exploitable vulnerabilities were identified in the reviewed code.** The XSS pattern (S1) is the highest-urgency item because it is one API schema change away from becoming a live exploit. Fix S1 and S2 before exposing this interface to untrusted users.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as separating this code from a world-class standard:

1. **The feature doesn't exist** (all 3 models): A world-class sponsor agent would have Grok-3 research, Claude-personalized outreach, a durable pipeline with audit logs, and Resend-based email with tracking. None of this is present.

2. **Duplicated core logic as an architectural pattern** (Gemini + GPT-4o): World-class codebases have a single authoritative implementation of each capability. Two parallel TTS engines signal a codebase that has grown by accretion rather than design.

3. **Frontend polling architecture** (Gemini + Grok): World-class real-time dashboards use WebSockets or SSE, not `setInterval` with unguarded fetch calls. The current approach creates unnecessary load and unpredictable UX under degraded network conditions.

4. **No observability for fallback degradation** (Grok + GPT-4o): World-class audio pipelines emit metrics at every fallback tier. Operators should be paged when ElevenLabs degrades, not discover it from user complaints.

5. **Timeline metadata integrity** (all 3 models on U1): World-class video production pipelines treat timeline metadata as a contract. The CLIP desync bug is a fundamental breach of that contract.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Build the actual `p3-sponsor-agent` feature (Grok-3 research, Claude outreach, pipeline persistence, Resend email) — current code is entirely the wrong scope | Missing files entirely | ALL | 0/4 laws implemented; wrong feature was submitted |
| **P0 CRITICAL** | Fix CLIP desync: append silence of `clip_dur`, advance `current_time`, fix `duration: 0.0` | `dual_host_tts.py:292–303`, `tts_engine.py:326–337` | ALL | Primary output (synchronized audio timeline) is broken |
| **P0 CRITICAL** | Delete `dual_host_tts.py` after migrating all callers to `tts_engine.py`; verify with tests | `dual_host_tts.py` entire file | ALL | Duplicate engines guarantee bug divergence; U1 already demonstrates this |
| **P1 HIGH** | Fix cache key to include voice settings hash | `tts_engine.py:114` | Gemini | Stale audio served silently after voice tuning — correctness failure in disguise |
| **P1 HIGH** | Remove `<canvas>` elements; replace sparklines with SVG | `media_unified.html:24, 33, 42` | Gemini | Direct violation of documented stack constraint |
| **P1 HIGH** | Fix `generate_dialogue_audio()` early raise — either enable fallback properly or remove fallback code and document requirement | `dual_host_tts.py:277–279`, `tts_engine.py:311–313` | GPT-4o | Fallback path is documented but unreachable — false safety net |
| **P1 HIGH** | Replace `setInterval` with chained `setTimeout` for all three polling loops | `media_unified.html:793–803` | Gemini, Grok | Request dogpiling under slow networks; current pattern hammers server concurrently |
| **P1 HIGH** | Add logging/metrics at each TTS fallback tier | `tts_engine.py:238–258` | Grok, GPT-4o | Silent quality degradation is undetectable by operators |
| **P1 HIGH** | Guard all `parseFloat` calls feeding signal gauge; block NaN from reaching DOM | `media_unified.html:626–633, 746–748` | Gemini, GPT-4o | NaN propagates to UI and corrupts signal display |
| **P1 HIGH** | Replace HEAD with GET for health checks; add 3s AbortController timeout | `media_unified.html:755–790` | GPT-4o, Gemini | CORS + HEAD non-support causes false DOWN states in production |
| **P1 HIGH** | Fix invalid HTML: `<button>` inside `<a>` | `media_unified.html:404–412` | Gemini, GPT-4o | Invalid per spec; breaks keyboard navigation and screen readers |
| **P1 HIGH** | Replace XSS-prone `innerHTML` string concatenation with `textContent` or sanitized DOM construction | `media_unified.html:780–789` | Grok, GPT-4o | One API schema change from live XSS; establish correct pattern now |
| **P2 MEDIUM** | Strengthen newsletter email validation; disable button on submit; add CSRF if endpoint uses session auth | `media_unified.html:468–480` | Grok, GPT-4o | Weak validation + repeat-click spam; CSRF risk if cookie auth is used |
| **P2 MEDIUM** | Remove or wire `fetchTradfi()` — currently dead work every 30s on every client | `media_unified.html:614–623, 731–748` | GPT-4o | Gratuitous network load with zero UI benefit |
| **P2 MEDIUM** | Rename `_mp3_to_m4a()` to `_audio_to_m4a()` and document format agnosticism | `tts_engine.py:247` | GPT-

---

# WINNER DETERMINATION

WINNER: GPT-4o — GPT-4o delivered the most forensically precise Cycle 1 analysis, identifying granular, actionable issues (dead `fetchTradfi()` polling, CSRF absence, nested `<a>`/`<button>` invalidity, weak email validation, `<canvas>` spec violation) that neither Grok nor Gemini caught at that depth, and its Cycle 2 self-correction was the most honest and specific, correctly distinguishing the `dual_host_tts.py` deletion risk with a nuanced "not immediately" caveat rather than a blunt recommendation, demonstrating superior judgment over raw finding volume.

---

## FINAL SECOND-PASS PRIORITY LIST

### P0 — Fix Immediately (Breaks Core Output)

**1. CLIP Audio Desynchronization (U1)**
- `dual_host_tts.py:292–303` and `tts_engine.py:326–337`
- Generate `clip_dur` seconds of silence via ffmpeg, append to `parts_for_concat`, advance `current_time += clip_dur`
- In `tts_engine.py` specifically: replace hardcoded `duration: 0.0` with actual `clip_dur` value
- Verification: produce a test render with one CLIP entry mid-script, confirm subtitle alignment holds after the clip

**2. Feature Not Implemented — p3-sponsor-agent (Law Compliance: 0/10)**
- No sponsor outreach logic, no pipeline management, no CRM hooks exist anywhere in the reviewed files
- The entire reviewed surface is a media dashboard and TTS pipeline — orthogonal to the stated feature
- Action: create a dedicated implementation sprint scoped strictly to the governing laws before any further audit cycles are meaningful

---

### P1 — Fix Before Next Release (Correctness and Spec Violations)

**3. Canvas Spec Violation**
- `media_unified.html:24, 33, 42`
- Project spec explicitly forbids `<canvas>`; sparkline elements must be replaced with a CSS or SVG equivalent
- Do not ship until resolved — this is a direct law breach, not a style preference

**4. Invalid Nested Interactive Elements**
- `media_unified.html:404–412`
- `<button>` nested inside `<a>` is invalid HTML per spec and breaks assistive technology interaction models
- Fix: convert to a single semantic element, either a styled `<a>` or a `<button>` with a JS navigation handler

**5. Redundant TTS Engine (U2)**
- `dual_host_tts.py` is a functionally inferior near-duplicate of `tts_engine.py`
- Do not delete until all callers are audited and migrated
- Action: enumerate every call site of `dual_host_tts.py`, migrate each to `tts_engine.py`, then delete and add a CI guard preventing re-introduction

---

### P2 — Fix Before Scale (Security and Reliability)

**6. Missing CSRF Token on Newsletter Subscribe**
- `media_unified.html:468–480`
- Any cookie-authenticated session is exposed to cross-site request forgery
- Fix: include CSRF token in the POST body using whatever framework token is available; add server-side validation

**7. HEAD Request Health Checks — CORS Fragility**
- `media_unified.html:755–760, 763–773`
- `HEAD` requests to third-party or cross-origin endpoints will silently fail due to CORS preflight absence, producing false-negative health reads
- Fix: proxy health checks through a backend endpoint that performs the check server-side and returns a normalized status JSON

**8. Silent TTS Fallback Degradation**
- `tts_engine.py:238–258`
- ElevenLabs failure falls through to pyttsx3 then silence with no log entry surfaced to admin
- Fix: emit a structured log event at `WARNING` level on each fallback step; expose a `/api/tts/health` status field so operators can detect degraded audio without listening to output

---

### P3 — Fix Before Production Hardening (Quality and Efficiency)

**9. Dead Polling Work — `fetchTradfi()`**
- `media_unified.html:614–623, 731–748`
- `fetchTradfi()` is called every 30 seconds and cached but its result is never consumed by any rendering path
- Fix: either wire it to a display component or remove the fetch entirely; do not pay network cost for unused data

**10. Weak Email Validation**
- `media_unified.html:470`
- Only checks for presence of `'@'`; accepts `a@` or `@b` as valid
- Fix: use a proper regex or the browser-native `type="email"` constraint with `reportValidity()`; add server-side format validation as the authoritative check

**11. No In-Flight Guard on Newsletter Submit**
- `media_unified.html:468–480`
- Rapid repeated clicks send duplicate requests to the subscribe endpoint
- Fix: disable the button on first click, re-enable on response or timeout

**12. Unhandled NaN in Signal Gauge**
- `media_unified.html:628`
- `parseFloat(sentData.composite_score)` on a null or non-numeric value propagates `NaN` silently through downstream gauge calculations
- Fix: add explicit `isNaN()` guard after parse; substitute a defined default (e.g., `0`) and surface a UI indicator that the score is unavailable

**13. Disk Write Failure in TTS Output — Silent**
- `tts_engine.py:309–310`
- If `output_dir` is unwritable or disk is full, file operations fail without catching or logging `OSError`
- Fix: wrap in `try/except OSError`, log the error with path and errno, and raise to caller rather than continuing as if output succeeded