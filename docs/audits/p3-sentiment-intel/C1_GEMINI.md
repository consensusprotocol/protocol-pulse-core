Here is your forensic code review of the `p3-sentiment-intel` feature.

### SECTION 1: CORRECTNESS

The code contains several logic errors and incorrect implementations that will lead to bugs in production.

*   **Logic Error in Signal Strength UI:** In `media_unified.html`, the `renderSignalGauge` function (line 635) receives `spacesCount` as its third argument (line 748) but names it `spacesScore`. It then re-calculates the spaces score on line 653 using `Math.min((spacesScore||0)*10,100)`, which is correct given the input is a count. However, the *actual* `spacesScore` calculated in `computeSignalStrength` (line 631) is never used for the UI breakdown. This is confusing, redundant, and error-prone. The `spacesScore` variable from `computeSignalStrength` should be passed to and used by `renderSignalGauge` directly.
*   **Incorrect TTS Timeline for Video Clips:** In both `dual_host_tts.py` (lines 292-303) and `tts_engine.py` (lines 327-337), when a `"CLIP"` entry is encountered, its metadata is recorded, but the script fails to increment `current_time` by the clip's duration. This means the `start` time for all subsequent dialogue lines will be incorrect, and the `total_duration` will be wrong. This will break the video editing process which relies on this timing data.
*   **Broken TTS Fallback Logic:** In `tts_engine.py` (and its predecessor), the fallback to `pyttsx3` is inside a loop that processes text chunks (lines 237-258). If the ElevenLabs API fails on the *first* chunk, the code attempts to generate that single chunk with `pyttsx3`. If successful, it `return ok` (line 254), exiting the entire `tts_elevenlabs` function. The remaining chunks of the text are never processed, resulting in incomplete audio for that line.
*   **Redundant Code / Maintenance Hazard:** The files `video_pipeline_v3/dual_host_tts.py` and `video_pipeline_v3/tts_engine.py` are nearly identical. `tts_engine.py` appears to be a newer version with caching. Maintaining two such similar files is a recipe for confusion and bugs, where fixes are applied to one but not the other. The older file should be removed.

### SECTION 2: LAW COMPLIANCE

The feature has major violations against the governing laws.

*   **LAW 1: Sentiment is calculated from real articles...**
    *   **STATUS: CANNOT VERIFY.** The provided code only shows the frontend consuming an API endpoint (`/api/media/sentiment`). None of the backend logic for article fetching, sentiment classification, model usage (`claude-haiku-4-5`), or database storage is present for review.

*   **LAW 2: SSE for real-time sentiment stream — not polling**
    *   **STATUS: VIOLATION.** The law explicitly forbids polling. The frontend code in `media_unified.html` uses `setInterval(updateTelemetry, 30000)` (line 796) to poll API endpoints, including the sentiment API, every 30 seconds. This is a direct and clear violation. An SSE (Server-Sent Events) implementation is required.

*   **LAW 3: Narrative intelligence is the key differentiator**
    *   **STATUS: PARTIAL VIOLATION.** The law requires identifying the *narrative* driving sentiment. The frontend HTML contains an element for this (`<div class="mu-sentiment-why" id="sentiment-why">` at line 83), but the accompanying JavaScript never populates it. The "key differentiator" feature is architected in the HTML but is not actually implemented, making it invisible to the user.

*   **LAW 4: Anomaly detection fires loud**
    *   **STATUS: VIOLATION.** The law requires logging sentiment anomalies and displaying a banner alert. No backend code for anomaly detection was provided. More importantly, the frontend in `media_unified.html` has no mechanism to listen for or display such an alert. This critical feature is completely missing from the implementation.

### SECTION 3: SECURITY

The code demonstrates good security practices in the areas visible, but the lack of backend code leaves major areas unverified.

*   **Secrets Management:** **GOOD.** Both TTS scripts use `get_key("ELEVENLABS_API_KEY")` (e.g., `tts_engine.py:170`), correctly abstracting secret retrieval rather than hardcoding keys.
*   **Command Injection:** **GOOD.** Subprocess calls to `ffmpeg`/`ffprobe` are made using argument lists (e.g., `tts_engine.py:62-65`), which prevents shell injection vulnerabilities. User-provided text is not passed into shell commands.
*   **Rate Limiting:** **PARTIAL.** The TTS scripts include a retry-with-backoff mechanism for `429 Too Many Requests` errors from the ElevenLabs API (e.g., `tts_engine.py:218-221`). This is good. However, there is no application-level rate limiting on the endpoint that triggers TTS generation, meaning a single user or a bug could still exhaust the entire API quota.
*   **Unvalidated Input:** **CANNOT VERIFY.** No backend routes that accept user input were provided, so risks like SQL Injection or filesystem traversal cannot be assessed.

### SECTION 4: FRONTEND QUALITY

The frontend has a professional aesthetic but is undermined by a critical implementation choice and missing features.

*   **UI/Spec Mismatch:** The spec requires a "Smooth CSS fade-in animation on new sentiment badges". The provided code does not contain the CSS or JS logic to implement this animation upon receiving new data.
*   **Hardcoded Content:** The "Library" section, including the Leaderboard, Rising Stars, and Learning Paths (`media_unified.html:322-397`), is entirely hardcoded HTML. This content should be dynamic and rendered from a database.
*   **Loading/Error States:** **GOOD.** The UI correctly handles initial loading states by displaying `--` or `Loading...`. The JavaScript `fetch` calls gracefully handle network errors by using cached data where available, preventing a broken UI on transient failures. Health dots also correctly reflect loading, connected, and error states.
*   **Overall Impression:** The design aesthetic, based on class names and font choices, appears clean, modern, and professional, fitting the "intelligence terminal" theme. However, the use of polling instead of real-time push updates makes it *feel* less like a world-class live product. The `innerHTML` updates (e.g., `media_unified.html:640`) are inefficient for frequent changes and can cause UI flickering.

### SECTION 5: BACKEND QUALITY

The provided Python scripts show a mix of robust patterns and areas for improvement.

*   **External API Handling:** **GOOD.** The `tts_engine.py` script demonstrates excellent practices for external API calls: it sets a timeout, retries on failure with exponential backoff, and has a graceful degradation path (fallback to `pyttsx3`, then silence) if the primary service fails.
*   **Logging:** **POOR.** The scripts exclusively use `print()` for logging (e.g., `tts_engine.py:345`). In a production environment, this is insufficient. Structured logging using Python's `logging` module is necessary for proper log levels, context, and aggregation in monitoring tools.
*   **Code Duplication:** **POOR.** As noted in Correctness, the existence of both `dual_host_tts.py` and `tts_engine.py` is a major code quality issue that will impede maintenance and introduce bugs.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

To compete with top-tier financial intelligence products, this feature needs significant enhancements.

*   **True Real-Time Experience:** The 30-second polling interval is the single largest gap. Professional terminals push data instantly. The failure to use SSE or WebSockets as mandated by LAW 2 makes the product feel dated and unresponsive compared to competitors.
*   **Surface the Differentiator (Narrative Intel):** LAW 3 states narrative intelligence is the key differentiator, yet it's completely absent from the UI. A world-class implementation would feature the current dominant narrative (`"ETF FLOWS"`, `"REGULATORY CLARITY"`) prominently, perhaps even more so than the numeric score. The score is the "what"; the narrative is the "why," which is what professionals pay for.
*   **Data Interactivity:** The dashboard is a static display. A professional user expects to interact with the data. Clicking the sentiment score should reveal the top articles driving that sentiment. The news feed should be filterable by narrative. The lack of drill-down capability makes the dashboard a superficial overview rather than a powerful analysis tool.
*   **Degradation vs. Failure:** The TTS fallback from a premium voice (ElevenLabs) to a robotic system voice (`pyttsx3`) or silence is not graceful degradation; it's a catastrophic quality failure. A world-class system would have a secondary premium TTS provider as a fallback or, at minimum, trigger high-priority alerts to operations when the primary TTS service fails, rather than shipping a broken product.

### SECTION 7: SCORES (0-100 each)

*   **Backend logic:** 60/100
*   **Frontend/UI:** 50/100
*   **Error handling:** 75/100
*   **Security:** 90/100
*   **Performance:** 65/100
*   **Law compliance:** 20/100
*   **World-class gap:** 30/100
*   **OVERALL:** **55/100**

### SECTION 8: PRIORITY ACTION PLAN

*   **P0 CRITICAL** | Replace frontend polling with an SSE implementation | `media_unified.html:796` | Direct violation of LAW 2; fails the "real-time" promise of the product.
*   **P0 CRITICAL** | Implement anomaly detection and frontend banner alert | N/A (missing code) | Direct violation of LAW 4; a critical, required feature is entirely absent.
*   **P0 CRITICAL** | Fix TTS timeline logic for video clips | `tts_engine.py:327` | Generates incorrect timing data, which will break the entire video production pipeline.
*   **P0 CRITICAL** | Fix broken TTS fallback logic for chunked text | `tts_engine.py:254` | Causes silent generation of incomplete audio, creating unusable video assets.
*   **P1 HIGH** | Implement Narrative Intelligence display in UI | `media_unified.html:83` | Violation of LAW 3; the product's "key differentiator" is not visible to users.
*   **P1 HIGH** | Remove the redundant `dual_host_tts.py` file | `video_pipeline_v3/dual_host_tts.py` | High risk of maintenance errors and deployment of incorrect code.
*   **P1 HIGH** | Fix Signal Strength UI calculation | `media_unified.html:748` | Displays incorrect component scores in the signal breakdown, misleading the user.
*   **P2 MEDIUM** | Replace `print()` with structured logging | `tts_engine.py` (all) | Lack of proper logging will make debugging production issues nearly impossible.
*   **P2 MEDIUM** | Make the Library section content dynamic | `media_unified.html:322-416` | Hardcoded content is brittle and requires a code deploy for simple content changes.
*   **P3 LOW** | Refactor JS to use targeted DOM updates instead of `innerHTML` | `media_unified.html:640, 780` | `innerHTML` is inefficient for frequent updates and can cause UI flicker/blips.

### SECTION 9: THE ONE THING

You must replace the 30-second polling with a real-time Server-Sent Events stream, as this is a direct violation of the governing laws and completely undermines the product's core promise of being a "live" intelligence terminal.

### SECTION 10: FINAL VERDICT

This code is **not ready for production**. It has critical violations of three of the four governing laws, including a failure to implement the core real-time architecture (LAW 2) and the key business differentiator (LAW 3). Furthermore, it contains show-stopper bugs in the video pipeline's TTS generation that will produce corrupted or unusable video assets. The polling architecture and logic bugs must be fixed before this feature can be merged.