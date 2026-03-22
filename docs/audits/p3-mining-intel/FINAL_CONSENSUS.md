# CONSENSUS REPORT — P3-MINING-INTEL — CYCLE 2
Generated: 2026-03-09 14:13
Models: Gemini, GPT-4o, Grok

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 2/10 | 3/10 | 3/10 | **2.7/10** |
| Law Compliance | 1/10 | 2/10 | 2/10 | **1.7/10** |
| Security | 5/10 | 5/10 | 5/10 | **5.0/10** |
| Frontend Quality | 3/10 | 4/10 | 4/10 | **3.7/10** |
| Backend Quality | 2/10 | 4/10 | 3/10 | **3.0/10** |
| **Overall** | **2.6/10** | **3.6/10** | **3.4/10** | **3.2/10** |

> **Scoring note:** Grok's Cycle 2 output was truncated; backend/frontend subscores were inferred from its narrative and its stated Cycle 1 assumed baselines. Gemini gave the harshest grades (appropriate given the severity of compliance failures). GPT-4o was most granular and methodical. All three converge on a range of 2.6–3.6, confirming this codebase is **not production-ready**.

---

## UNANIMOUS FINDINGS
*All 3 models agree — implement unconditionally.*

---

### U1 — mempool.space WebSocket is completely absent
- **All models:** Gemini, GPT-4o, Grok
- **File:** `templates/media_unified.html:796`
- **What it is:** The live hashrate data is fetched via `setInterval` polling every 30 seconds. There is zero evidence of a WebSocket connection to `wss://mempool.space/api/v1/ws` anywhere in the codebase. LAW 2 explicitly mandates this WebSocket as the required transport, not polling.
- **What to change:** Remove the polling loop for hashrate. Implement a persistent WebSocket client connecting to `wss://mempool.space/api/v1/ws`, send the required subscription payload (`{"action":"want","data":["blocks","stats","mempool-blocks"]}`), and update the telemetry ribbon reactively on each incoming message. Implement reconnect logic with exponential backoff.

---

### U2 — ASIC profitability calculator is entirely absent
- **All models:** Gemini, GPT-4o, Grok
- **File:** No file — feature is missing entirely
- **What it is:** LAW 3 mandates a user-configurable ASIC profitability calculator. There are no inputs for electricity cost, ASIC model, hashrate draw, or power consumption. There are no computed outputs for daily/monthly profit, break-even BTC price, or payback period. This is a named core feature of the `p3-mining-intel` branch and it does not exist.
- **What to change:** Build the calculator end-to-end. Frontend: form inputs for ASIC model (dropdown), hashrate (TH/s), power (W), electricity rate ($/kWh). Backend: endpoint consuming current network difficulty + BTC price + fee revenue to compute revenue, cost, and net profit. Render results in a responsive table and/or chart (CSS/SVG only — no Canvas).

---

### U3 — Required mining article fields are absent from UI
- **All models:** Gemini, GPT-4o, Grok
- **File:** `templates/media_unified.html` — no lines, fields are entirely missing
- **What it is:** LAW 1 mandates that every article in this feature MUST display: current network hashrate, current difficulty, BTC price, and miner revenue. None of these data points have UI elements, data bindings, or API hooks anywhere in the template. The telemetry ribbon exists but does not expose these specific required fields.
- **What to change:** Add a dedicated mining telemetry section to the template with live-bound elements for all four required fields. Wire them to the mempool.space WebSocket data (U1) and appropriate price feeds. Apply clear labels and units (EH/s, T, USD, BTC/block).

---

### U4 — `<canvas>` elements violate the explicit technology stack constraint
- **All models:** Gemini, GPT-4o, Grok
- **File:** `templates/media_unified.html:24, 33, 42`
- **What it is:** The project's governing technology rules state "NO Canvas." Three `<canvas>` elements are used for sparklines. This is a direct, unconditional violation regardless of whether the sparklines function correctly.
- **What to change:** Remove all three `<canvas>` elements. Replace each sparkline with an inline SVG `<polyline>` or a CSS-only bar visualization. Data points should be injected via JavaScript by setting SVG `points` attributes or CSS custom properties. No third-party charting library that uses Canvas as its backend is acceptable as a replacement.

---

### U5 — TTS `CLIP` entries do not advance `current_time` / record correct duration
- **All models:** Gemini, GPT-4o, Grok
- **File:** `dual_host_tts.py:292-303`, `tts_engine.py:326-337`
- **What it is:** In `dual_host_tts.py`, when a dialogue entry is a CLIP, the code appends its metadata and `continue`s without advancing `current_time`. This means every subsequent line's timestamp is calculated as if the clip never happened. In `tts_engine.py`, CLIP duration is hardcoded to `0.0`. Both bugs corrupt all downstream timing metadata used for subtitle alignment, lipsync, and video timeline editing.
- **What to change:** In both files, when processing a CLIP entry: (1) record the clip start as `current_time`, (2) add the clip's actual duration to `current_time`, (3) emit the correct duration in the metadata entry. Also insert the `SILENCE_GAP` before the next spoken line as the surrounding non-CLIP logic does.

---

### U6 — TTS code is fatally duplicated across two nearly identical files
- **All models:** Gemini, GPT-4o, Grok
- **File:** `dual_host_tts.py` (entire file), `tts_engine.py` (entire file)
- **What it is:** Both files implement the same TTS pipeline. `tts_engine.py` is a superset with caching and voice modes. Both are in active use or ambiguously available. Any bug fix or feature applied to one will be missed in the other. The CLIP timing bug (U5) exists in both files precisely because of this duplication.
- **What to change:** Delete `dual_host_tts.py` entirely. Audit all callers and pipeline scripts that import or invoke it and redirect them to `tts_engine.py`. Confirm `tts_engine.py` supports all voice modes and fallback scenarios previously handled by `dual_host_tts.py`. After migration, add a module-level docstring to `tts_engine.py` marking it as the single authoritative TTS engine.

---

### U7 — Top-level `generate_dialogue_audio` raises on missing API key, making graceful fallbacks unreachable
- **All models:** Gemini, GPT-4o, Grok
- **File:** `dual_host_tts.py:277-280`, `tts_engine.py:311-314`
- **What it is:** Both top-level entry points raise `RuntimeError` if `ELEVENLABS_API_KEY` is not present. However, the inner `tts_elevenlabs()` function contains explicit, tested fallback logic to `pyttsx3` or silence when the key is absent. The `RuntimeError` at the entry point means those fallbacks are dead code for the most common failure mode (missing key). The pipeline crashes where it was designed to degrade gracefully.
- **What to change:** Remove the `raise RuntimeError` guard on missing key from `generate_dialogue_audio`. Instead, allow execution to fall through to `tts_elevenlabs()` which already handles the missing-key case. If you want to log a warning that TTS quality will be degraded, do so with `logger.warning`, not by raising. Reserve `RuntimeError` for truly unrecoverable states (e.g., output directory not writable).

---

## MAJORITY FINDINGS
*2 of 3 models agree — implement unless there is a compelling reason not to.*

---

### M1 — Signal gauge variable naming causes a double-multiply math bug
- **Models:** Gemini, GPT-4o (Grok noted it as a new finding with slightly different framing)
- **File:** `templates/media_unified.html:626-633, 745-748, 652-654`
- **What it is:** `computeSignalStrength()` calculates `spacesScore = Math.min(spacesCount * 10, 100)`. Then `renderSignalGauge(score, sentScore, spacesCount)` is called with the raw **count**, not the score. Inside `renderSignalGauge`, the parameter is bound to a local variable also named `spacesScore`, and the display line applies `Math.min((spacesScore||0)*10, 100)` again — re-multiplying the count by 10. The value displayed in the breakdown is mathematically inconsistent with the value used in the composite total. It works accidentally today but will silently produce wrong values if the API ever returns a normalized score instead of a raw count.
- **What to change:** Either pass the pre-computed `spacesScore` (not `spacesCount`) to `renderSignalGauge` and remove the inner multiply, or rename the parameter in `renderSignalGauge` to `spacesCount` and document that it applies the transform internally. Pick one source of truth. Add a comment explaining the 10x scaling factor.

---

### M2 — `window.relayManager` is an undeclared global dependency
- **Models:** Gemini, GPT-4o
- **File:** `templates/media_unified.html:659`
- **What it is:** `syncRelayStatusBar()` depends on `window.relayManager` being initialized by an external script (`media_unified_v5.js`). If that script is slow, fails to load, or is removed, the function degrades silently. GPT-4o notes the function does guard with `if (!window.relayManager || !window.relayManager.sockets) return;` — so it will not throw in the base case. However the coupling is invisible and fragile.
- **What to change:** At minimum, add a `console.warn` when `relayManager` is absent so developers know the dependency is unfulfilled. Better: define a stub `window.relayManager = { sockets: [] }` as a default in this file so the guard condition is always defined, and the external script overwrites it if/when it loads.

---

### M3 — YouTube ID extraction fails for common URL formats
- **Models:** GPT-4o, Gemini (implicit — brittle parsing theme)
- **File:** `templates/media_unified.html:120, 295`
- **What it is:** The YouTube URL parser only handles `?v=` query parameter format. It breaks silently for `youtu.be/<id>`, `/embed/<id>`, and `/shorts/<id>` formats, resulting in empty `data-vid` attributes, broken thumbnails, and broken links.
- **What to change:** Replace the current single-pattern extraction with a regex that handles all known YouTube URL patterns. Recommended: `/(?:youtu\.be\/|youtube\.com\/(?:embed\/|shorts\/|watch\?v=|v\/))([A-Za-z0-9_-]{11})/`. Test against all four format types.

---

### M4 — Invalid HTML: `<button>` nested inside `<a>` in library cards
- **Models:** GPT-4o, Gemini (implicit via frontend quality score)
- **File:** `templates/media_unified.html:404-412`
- **What it is:** `<button class="mu-vote-btn">` is nested directly inside `<a class="mu-lib-book">`. This is invalid per the HTML5 spec (interactive content may not be nested inside other interactive content). Browsers handle it inconsistently; mobile devices and screen readers often break click/focus behavior.
- **What to change:** Restructure the card so the anchor and button are siblings, not parent/child. Wrap both in a `<div class="mu-lib-book">`. Use `event.stopPropagation()` on the button click handler to prevent navigation when the vote button is clicked. Validate with an HTML linter.

---

### M5 — Stale cached data displayed with no staleness indicator
- **Models:** GPT-4o, Grok
- **File:** `templates/media_unified.html:597, 608`
- **What it is:** When API calls fail, the code silently falls back to the last cached value. There is no visual indicator, no timestamp, and no user-facing warning that the data may be stale. For a "live mining intelligence" product, displaying hours-old hashrate or fee data as if it were current is actively misleading.
- **What to change:** Track `lastSuccessfulFetch` timestamps per data type. If data is older than 2× the polling interval, render a visible "Data as of HH:MM — live feed unavailable" indicator in the telemetry ribbon. Style it with a muted warning color to distinguish it from live data.

---

### M6 — Episode numbering uses `loop.index` outside a loop context
- **Models:** GPT-4o, Grok (implicit via UX correctness)
- **File:** `templates/media_unified.html:113`
- **What it is:** Inside the `if latest_episodes` block (which is not a `for` loop), the template renders `EP {{ loop.index if loop is defined else podcast_count }}`. Since there is no loop, `loop` is not defined, so this always falls through to `podcast_count`. The displayed episode number is wrong for every card.
- **What to change:** Wrap the episodes block in a proper `{% for episode in latest_episodes %}` loop. Use `{{ loop.index }}` or a field from the episode object (`episode.number`) for accurate numbering. Remove the `if loop is defined` guard — it was papering over the missing loop.

---

### M7 — `HEAD`-based health checks can produce false negatives
- **Models:** GPT-4o, Grok
- **File:** `templates/media_unified.html:767`
- **What it is:** The `checkService()` function uses `fetch(url, { method: 'HEAD' })` for health checks. Several internal APIs (especially WebSocket endpoints and streaming endpoints) do not support `HEAD` and will return 405 Method Not Allowed, causing the health strip to permanently display a red error state for a service that is actually healthy.
- **What to change:** Switch health checks to `GET` with a small timeout (e.g., `AbortController` at 3s). For WebSocket endpoints, check connection status from the live WebSocket object rather than HTTP polling. Document which endpoint type each health check targets.

---

## UNIQUE INSIGHTS
*Single-model findings — assessed individually.*

---

### I1 — `fetch()` does not check `r.ok` before caching response
- **Model:** GPT-4o
- **File:** `templates/media_unified.html:592-605, 616-617`
- **Assessment: IMPLEMENT**
- HTTP error responses (4xx, 5xx) that return a JSON body (e.g., `{"error": "rate limited"}`) are parsed and cached as valid data. The UI may then render error payloads as if they were real telemetry, and subsequent requests will serve the cached error as "good data." Add `if (!r.ok) throw new Error(r.status)` immediately after each `await fetch(...)` call, before `.json()`.

---

### I2 — Health dot CSS classes accumulate, can express contradictory states simultaneously
- **Model:** GPT-4o
- **File:** `templates/media_unified.html:718-720`
- **Assessment: IMPLEMENT** (low effort, clear correctness fix)
- The function removes only `loading` before adding `connected` or `error`. After a state transition sequence, an element can carry both `connected` and `error` classes. Fix: remove all three classes (`loading`, `connected`, `error`) before adding the current one. One line change.

---

### I3 — `countEl` is queried but never used in relay status sync
- **Model:** GPT-4o
- **File:** `templates/media_unified.html:669`
- **Assessment: IMPLEMENT** (dead code removal)
- Minor but indicates an incomplete refactor. Remove the dead variable or implement the intended behavior. Either way, clarify intent.

---

### I4 — FFmpeg concat return code is never checked before reporting output path
- **Model:** GPT-4o
- **File:** `dual_host_tts.py:342-348`, `tts_engine.py:380-386`
- **Assessment: IMPLEMENT**
- If the `ffmpeg` concat subprocess fails, the code only checks whether the output file exists (a partial/corrupted file may still be written). It does not inspect the return code or stderr. Add `if result.returncode != 0: raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")` and handle accordingly.

---

### I5 — `_chunk_text()` does not guarantee chunk size for oversized single sentences
- **Model:** GPT-4o (Grok noted this as a gap but less explicitly)
- **File:** `dual_host_tts.py:111-126`, `tts_engine.py:93-108`
- **Assessment: IMPLEMENT**
- A single sentence longer than `MAX_CHUNK_CHARS` is emitted as a single oversized chunk. The API call will fail for that chunk, and there is no sub-sentence splitting fallback. Add a secondary split on punctuation (`, `, `; `) for sentences that exceed the limit. If no split point exists, truncate with a warning log rather than sending an oversized payload.

---

### I6 — Silence file generation return value is ignored before it is added to concat list
- **Model:** GPT-4o
- **File:** `dual_host_tts.py:281-282`, `tts_engine.py:315-316`
- **Assessment: IMPLEMENT**
- `_generate_silence()` can fail. Its return value (the file path, or `None` on failure) is discarded. If silence generation fails and a nonexistent path is added to the concat list, the entire final assembly will fail with an opaque FFmpeg error. Check the return value: `silence = _generate_silence(...); if not silence: logger.error(...); continue`.

---

### I7 — `Promise.allSettled` around helpers that already catch all errors masks true success/failure distinction
- **Model:** GPT-4o
- **File:** `templates/media_unified.html:732-739`
- **Assessment: INVESTIGATE FURTHER**
- Valid architectural concern: wrapping fully-caught helpers in `allSettled` means you can never distinguish a real API success from a silent fallback. However, changing this requires restructuring the entire telemetry fetch chain. Recommend adding a `lastFetchWasFallback` flag per data source (as a prerequisite to M5) rather than unwinding `allSettled` before understanding all callers.

---

### I8 — TTS cache directory has no size limit or eviction policy
- **Model:** Grok
- **File:** `tts_engine.py:111-138`
- **Assessment: INVESTIGATE FURTHER**
- In high-volume use, the cache directory will grow indefinitely. This is a real operational risk on long-running servers. Implement LRU eviction or a `max_cache_size_mb` config option. Flag for ops review before production deployment rather than blocking the feature.

---

### I9 — Health check endpoints lack rate-limiting or backoff on failure
- **Model:** Grok
- **File:** `templates/media_unified.html:763-773`
- **Assessment: INVESTIGATE FURTHER**
- If a monitored service is degraded, the health checker fires repeatedly without backoff, potentially contributing to the overload it is trying to detect. Implement exponential backoff on consecutive failures before re-flagging an already-known-down service. Non-blocking but worth addressing before production.

---

### I10 — Inconsistent audio sample rates between silence generators (`44100` mono vs `48000` stereo)
- **Model:** Gemini (derived from BUG1 FIX A analysis)
- **File:** `dual_host_tts.py:95, 133`, `tts_engine.py:77, 148`
- **Assessment: IMPLEMENT**
- `_generate_silence()` uses `r=44100:cl=mono`. `_tts_generate_silence_fallback()` uses `r=48000:cl=stereo`. If these are concatenated in the same pipeline, FFmpeg will either fail or silently resample, potentially introducing audio artifacts. Standardize to a single sample rate and channel count across all silence generation functions. Choose `48000:stereo` to match typical ElevenLabs output.

---

## CONFLICTS
*Models gave contradictory signals — tiebreaker applied.*

---

### C1 — Severity of `window.relayManager` TypeError
- **GPT-4o:** Claims the guard `if (!window.relayManager || !window.relayManager.sockets) return;` prevents a thrown `TypeError`.
- **Gemini:** Claims the function "will throw a `TypeError` every 5 seconds."
- **Tiebreaker: GPT-4o is correct** on the narrow technical claim. The guard does prevent an uncaught `TypeError` in the base case. However, Gemini's concern about fragile hidden coupling is valid and actionable. Resolution: Accept GPT-4o's correctness assessment, but implement Gemini's recommended fix (the dependency stub + warning log, per M2) because the coupling risk is real regardless of whether it throws today.

---

### C2 — Whether showing quoted excerpts violates LAW 1 (plagiarism)
- **Gemini:** Flags excerpts from partner channels as a potential plagiarism violation of LAW 1.
- **GPT-4o:** Disagrees — attributed excerpts from partners are not plagiarism, especially if source attribution exists in the template (`191-192`).
- **Tiebreaker: GPT-4o is correct.** Attributed quotation is not plagiarism. The LAW 1 violation is real but the violation is the *absence of required mining metrics* (U3), not the presence of attributed partner content. Do not remove partner highlights. Do add the required mining fields.

---

### C3 — Backend Quality score
- **Gemini:** 2/10
- **GPT-4o:** 4/10
- **Grok:** 3/10
- **Tiebreaker: Consensus at 3/10.** Gemini's harsher score reflects the severity of TTS duplication as a systemic issue. GPT-4o's more moderate score reflects that the TTS code, while duplicated, does implement a recognizable and partially functional pattern. The consensus score of 3/10 is appropriate: the code is not completely broken but is not fit for production in its current state.

---

## VALIDATED STRENGTHS
*All models agree these areas are solid. Do NOT change them in the second pass.*

- **Jinja empty-state guards:** `templates/media_unified.html:109-129, 188-195` — Jinja `if` guards on `latest_episodes` and `ssr_highlights` blocks are correctly placed and prevent rendering empty sections. Leave these intact.
- **Default Jinja auto-escaping:** Interpolated template values use standard Jinja2 escaping, reducing XSS surface area for server-rendered data. Do not switch to `| safe` without explicit review.
- **TTS inner fallback chain in `tts_elevenlabs()`:** The `tts_elevenlabs()` function's internal fallback logic (ElevenLabs → pyttsx3 → silence) is correctly structured and logged. The bug is at the *entry point* (U7), not inside this function. Do not refactor the fallback chain itself — just remove the entry-point `RuntimeError`.
- **Text chunking logic structure:** The *structure* of `_chunk_text()` (sentence boundary splitting, respecting `MAX_CHUNK_CHARS`) is sound. The bug (I5) is only the missing handling for oversized single sentences. Do not rewrite from scratch.

---

# WINNER DETERMINATION

WINNER: GPT-4o — GPT-4o delivered the most accurate, granular, and actionable analysis across both cycles, correctly identifying the canvas stack violation, the double-multiplication signal gauge math bug with exact line references, the invalid nested HTML, the brittle YouTube ID parsing, and the unreachable TTS fallback logic — all of which were confirmed correct in Cycle 2 by both peer models and the consensus report. Its findings were the most complete in Cycle 1 and its Cycle 2 self-audit was the most methodical, explicitly distinguishing what it missed from what it caught first, making it the highest-utility output for an engineering team.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by: severity × blast radius × compliance obligation

---

### P0 — BLOCKING / COMPLIANCE FAILURES
*Ship nothing until these are resolved.*

**P0-1 — Implement mempool.space WebSocket (U1)**
- File: `templates/media_unified.html:796`
- Remove the 30s polling interval for hashrate entirely
- Open `wss://mempool.space/api/v1/ws`, send `{"action":"want","data":["blocks","stats","mempool-blocks"]}`
- Update telemetry ribbon reactively on each message event
- Add exponential backoff reconnect with a max of 5 retries before surfacing a degraded-mode banner to the user
- LAW 2 violation — non-negotiable

**P0-2 — Build ASIC profitability calculator (U2)**
- File: No file — feature is entirely absent
- Implement user-configurable inputs: hashrate (TH/s), power consumption (W), electricity cost ($/kWh), pool fee (%)
- Pull current network difficulty and block reward from the mempool WebSocket established in P0-1
- Render break-even price, daily/monthly revenue, and margin inline
- LAW 3 violation — non-negotiable

**P0-3 — Fix unreachable TTS fallback logic**
- Files: `dual_host_tts.py:277-279`, `tts_engine.py:311-313`
- `generate_dialogue_audio` raises `RuntimeError` on missing `ELEVENLABS_API_KEY`, making all graceful fallbacks inside `tts_elevenlabs` completely unreachable
- Replace the hard raise with a caught exception that logs a warning and routes to the silence fallback path
- The pipeline must not crash on a missing key; degraded audio output is acceptable, a crashed pipeline is not

**P0-4 — Resolve TTS file authority ambiguity**
- Files: `dual_host_tts.py`, `tts_engine.py`
- These files are near-identical with no clear ownership
- Determine the authoritative file, migrate all unique logic from the other (caching, voice modes) into one canonical module, and delete the duplicate
- Any bug fixed in one currently goes unfixed in the other — this is an active defect multiplier

---

### P1 — CRITICAL CORRECTNESS BUGS
*Must fix before any QA sign-off.*

**P1-1 — Fix CLIP timing bug in both TTS scripts**
- Files: `dual_host_tts.py:292-303`, `tts_engine.py:326-337`
- CLIP entries do not advance `current_time` and `tts_engine.py` records CLIP duration as `0.0`
- This corrupts all downstream timestamp synchronization for video assembly
- Fix: after appending a CLIP entry, advance `current_time` by the actual clip duration retrieved or estimated from the asset metadata

**P1-2 — Fix signal gauge double-multiplication**
- Files: `media_unified.html:626-633`, `media_unified.html:745-748`, `media_unified.html:652-654`
- `computeSignalStrength` computes `spacesScore = min(spacesCount * 10, 100)` but `renderSignalGauge` is called with raw `spacesCount`, not `spacesScore`
- Inside render, it multiplies by 10 again, producing values up to 10× too large before the clamp
- Fix: pass `spacesScore` (the already-scaled value) into `renderSignalGauge`, remove the redundant `*10` inside the render function, and rename the parameter to eliminate the score/count confusion

**P1-3 — Remove canvas elements (stack violation)**
- File: `media_unified.html:24,33,42`
- The governing stack explicitly forbids `<canvas>`
- Replace the three sparkline canvas elements with SVG-based or CSS-based equivalents
- Options: inline SVG polyline with a computed `points` attribute, or a lightweight SVG-only charting utility if already in the dependency tree

**P1-4 — Fix episode numbering in hero block**
- File: `media_unified.html:113`
- `loop.index` is referenced outside any Jinja loop context, so it always falls back to `podcast_count` for every card
- Fix: pass an enumerated index from the view function or use `loop.index` correctly inside a `{% for %}` block

---

### P2 — QUALITY AND ROBUSTNESS ISSUES
*Fix in the current sprint before release.*

**P2-1 — Harden YouTube ID extraction**
- Files: `media_unified.html:120,295`
- Current logic only handles `?v=` query parameter format
- Add support for `youtu.be/<id>`, `/embed/<id>`, and `/shorts/<id>` using a consolidated regex or URL-parsing utility function called from one place
- Failure modes: empty `data-vid`, broken thumbnails, broken deep-links

**P2-2 — Fix invalid nested interactive HTML**
- File: `media_unified.html:404-412`
- `<button>` inside `<a>` is invalid HTML per the spec
- Causes unpredictable click event propagation, focus-ring failures, and screen reader confusion
- Fix: either make the outer element a `<div>` with a JS click handler, or restructure so the button and link are siblings with distinct hit areas

**P2-3 — Surface stale data state to users**
- File: `media_unified.html:597,608`
- API failures silently fall back to cached data with no visual indicator
- Add a subtle degraded-mode indicator (e.g., a muted timestamp badge reading "Last updated 4m ago") whenever the live fetch fails and cached data is being served

**P2-4 — Guard against null/malformed API responses**
- File: `media_unified.html:629`
- `spacesData.spaces` is accessed without a null or array check
- If the API returns `null`, `undefined`, or a non-array, `spacesCount` will be `NaN` or wrong, corrupting signal strength
- Fix: `const spacesCount = Array.isArray(spacesData?.spaces) ? spacesData.spaces.length : 0`

**P2-5 — Fix HEAD-based health check false negatives**
- File: `media_unified.html:767`
- HEAD requests are legitimately rejected by some endpoints that serve GET correctly
- Replace with a lightweight GET to a dedicated `/healthz` endpoint that returns `{"ok":true}` and measure response time, or at minimum fall back to GET if HEAD returns 405

**P2-6 — Resolve `window.relayManager` implicit dependency**
- File: `media_unified.html:659`
- `syncRelayStatusBar` references `window.relayManager` which is not defined in this file
- If `media_unified_v5.js` fails to load or initializes late, this throws a `TypeError` every 5 seconds
- Fix: guard with `if (!window.relayManager) return;` at the top of `syncRelayStatusBar` and log a single warning rather than a recurring uncaught exception

---

### P3 — COMPLIANCE GAPS (CONTENT / DATA)
*Required before the feature can be considered law-complete.*

**P3-1 — Add required mining article metadata fields**
- All models confirmed: the feature does not expose the required per-article fields mandated by the governing laws
- Audit the full field list from the spec, add them to the article model, expose them in the template, and verify each is populated by the data pipeline

**P3-2 — Verify and document which TTS voices are mapped