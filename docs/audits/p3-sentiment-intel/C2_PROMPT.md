# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: p3-sentiment-intel
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REPORT: p3-sentiment-intel

Below is a detailed forensic review of the provided code for the `p3-sentiment-intel` feature of Protocol Pulse. I have analyzed the code against the specified requirements, laws, and quality standards with a focus on correctness, compliance, security, and overall excellence.

---

### SECTION 1: CORRECTNESS
**User Flow Analysis:**
- **Main Flow (Sentiment Stream and Display):** The primary user flow involves real-time sentiment updates via Server-Sent Events (SSE) and displaying them in the UI with animations. In `templates/media_unified.html`, the sentiment track and related elements are defined (lines 75-83), and JavaScript in lines 590-599 fetches sentiment data from `/api/media/sentiment`. However, there is no explicit SSE implementation in the provided code for `/api/stream/sentiment` as required by LAW 2. This suggests a critical gap in real-time updates.
- **Logic Errors:** In `media_unified.html` (lines 625-633), the `computeSignalStrength` function uses a fallback value of 50 for sentiment score if data is unavailable, which could mask failures and mislead users about actual sentiment. This is not a robust error handling strategy.
- **Race Conditions:** The telemetry update function (`updateTelemetry`, lines 731-752) polls every 30 seconds without any synchronization mechanism. Concurrent requests could overwrite cached data (`_cache` in line 587) if multiple tabs or users access the same client-side state, leading to inconsistent UI updates.
- **N+1 Query Problems:** Not directly visible in the provided frontend code, as backend database operations are not included. However, the lack of backend code for sentiment classification and storage raises concerns about potential inefficiencies if implemented poorly (e.g., querying articles individually rather than in batches).
- **Edge Cases:** 
  - Empty or null responses from `/api/media/sentiment` are partially handled by caching (line 598), but there's no UI feedback for persistent failures (e.g., no "offline" state beyond initial load).
  - In `tts_engine.py` and `dual_host_tts.py`, long text inputs exceeding `MAX_CHUNK_CHARS` (line 48 in `tts_engine.py`) are chunked, but there's no validation for extremely long single sentences that might exceed API limits even after chunking, risking silent failures.

**Verdict:** The code partially implements the user flow but lacks critical components like SSE for real-time updates. Edge cases and race conditions are not adequately addressed.

---

### SECTION 2: LAW COMPLIANCE
- **LAW 1: Sentiment is calculated from real articles — never fake or static**
  - **PARTIAL COMPLIANCE**: The provided code does not include backend logic for sentiment classification or storage in the `articles` table (required fields: `sentiment`, `sentiment_confidence`, `sentiment_at`). There is a placeholder for fetching sentiment data (line 590 in `media_unified.html`), but no evidence of real-time classification within 60s of article creation or batch re-classification on restart. Additionally, no mention of using `claude-haiku-4-5` as specified.
  - **Violation Reference**: Missing backend implementation for LAW 1 requirements.
- **LAW 2: SSE for real-time sentiment stream — not polling**
  - **VIOLATION**: The code uses polling every 30 seconds (line 796 in `media_unified.html`) instead of SSE for `/api/stream/sentiment`. There is no implementation of SSE or smooth CSS fade-in animations for sentiment badges as required.
  - **Violation Reference**: Lines 731-752 (polling instead of SSE).
- **LAW 3: Narrative intelligence is the key differentiator**
  - **VIOLATION**: There is no implementation of narrative extraction (e.g., "ETF flows", "halving cycle") in the provided code. Sentiment display in the UI (lines 75-83 in `media_unified.html`) shows only a numerical score and "FEAR/GREED" labels without narrative context.
  - **Violation Reference**: Missing backend logic for narrative extraction.
- **LAW 4: Anomaly detection fires loud**
  - **VIOLATION**: No implementation of anomaly detection for sentiment shifts (>20 points in 2 hours), logging to `intelligence_events` table, or displaying banner alerts in the UI.
  - **Violation Reference**: Missing logic for anomaly detection and alerts.

**Verdict:** The code violates or partially complies with all laws due to missing backend implementations and reliance on polling instead of SSE.

---

### SECTION 3: SECURITY
- **SQL Injection:** No raw SQL queries or ORM operations are visible in the provided code, as backend logic is absent. However, this is a gap since user input handling for sentiment or API endpoints is not shown.
- **Authentication Bypasses:** No authentication checks are visible in the frontend code or API calls (e.g., `/api/media/sentiment` in line 592 of `media_unified.html`). If backend routes are unprotected, this could allow unauthorized access to sensitive data.
- **Rate Limiting Gaps:** In `tts_engine.py` and `dual_hos

## GEMINI — CYCLE 1 OUTPUT
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

The frontend has a professional aesthetic but i

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main user flow walkthrough

#### 1) Media page loads
- `templates/media_unified.html` renders a large dashboard with telemetry, feeds, gauge, newsletter, etc.
- Initial SSR content exists for some sections (`latest_episodes`, `ssr_highlights`, `series_list`, `all_books`), so the page won’t be blank if JS fails. That’s good.

#### 2) Frontend boot sequence
- On `DOMContentLoaded`, the inline runtime calls:
  - `updateTelemetry()` immediately and every 30s (`templates/media_unified.html:793-797`)
  - `syncRelayStatusBar()` every 5s (`798-799`)
  - `updateHealthStrip()` immediately and every 60s (`801-803`)

This means the “live” sentiment/X Spaces behavior is implemented via polling, not SSE.

#### 3) Sentiment fetch
- `fetchSentiment()` calls `/api/media/sentiment` and caches the JSON (`590-600`).
- If fetch fails, it returns cached data or `{ composite_score: null, label: 'OFFLINE' }`.

**Correctness issue:** the code assumes the sentiment payload has `composite_score`, but the governing laws require per-article sentiment classification and real-time streaming of new classifications. This page is consuming an aggregate endpoint, not article-level classification events. There is no evidence here that new article badges appear when classification completes.

#### 4) X Spaces fetch
- `fetchSpaces()` calls `/api/spaces/live` (`602-612`).
- `updateXSpacesTelemetry()` updates score/label and health dot (`703-728`).

This is functionally okay for a telemetry widget, but again it is polling.

#### 5) Signal strength gauge
- `computeSignalStrength()` computes:
  - sentiment score from `sentData.composite_score`
  - spaces score from `spacesData.spaces.length * 10`, capped at 100 (`626-633`)
- `renderSignalGauge()` then renders the gauge and breakdown (`635-655`).

**Logic bug:** `renderSignalGauge()` expects `spacesScore` to be a score, but `updateTelemetry()` passes `spacesCount` instead:
- `spacesCount = spacesData.spaces.length` (`745`)
- `renderSignalGauge(score, sentScore, spacesCount)` (`748`)
- Inside renderer, breakdown does `Math.min((spacesScore||0)*10,100)` (`653`)

So the displayed X Spaces breakdown is derived from count *again*, while `computeSignalStrength()` already did that conversion. The naming is misleading and easy to break. It happens to display the same intended value only because of this double convention mismatch. This is fragile and not clean.

#### 6) Relay status bar
- `syncRelayStatusBar()` inspects `window.relayManager.sockets` and `window.state.nostrNotes` (`659-700`).

**Potential runtime fragility:**
- It assumes `window.relayManager.sockets` is an object of WebSocket-like instances with `readyState`.
- It assumes `window.state.nostrNotes` is an array.
- It silently returns if not present, so the UI may remain permanently stale with no user-facing error.

**Minor bug:** `countEl` is queried at `669` but not used in the first half of the function.

#### 7) Health strip
- `updateHealthStrip()` HEAD-checks several services (`755-790`).

**Correctness / compatibility issue:**
- It uses `fetch(..., { method: 'HEAD' })` for all services (`767`).
- Many app endpoints do not implement HEAD correctly, especially JSON routes like `/api/spaces/live` and `/api/tradfi/signals`.
- This can falsely mark healthy services as DOWN/DEGRADED.

#### 8) Newsletter subscribe
- `subscribeNewsletter()` POSTs raw email JSON to `/api/newsletter/subscribe` (`468-480`).

**Correctness/security concern:** only client-side validation is `email.includes('@')` (`470`). That is not meaningful validation. If backend is weak, junk input will flood the endpoint.

---

### TTS modules walkthrough

These two Python files are not sentiment-intel code. They appear unrelated to the feature under review.

#### `video_pipeline_v3/dual_host_tts.py`
- Generates line-by-line TTS via ElevenLabs.
- Fallback chain: ElevenLabs → `pyttsx3` → silence.
- Concatenates output via ffmpeg.

**Critical correctness bug:** `_mp3_to_m4a()` is used to convert a WAV file generated by `pyttsx3`:
- WAV temp created at `209-211`
- Then `_mp3_to_m4a(wav_tmp, output_path)` called at `213`

Despite the function name, ffmpeg can still convert WAV input because it just uses `-i <path>`. So this is ugly naming, not necessarily broken.

**More serious bug:** `generate_dialogue_audio()` hard-fails if `ELEVENLABS_API_KEY` is missing:
- `277-279` raises `RuntimeError`
- But `tts_elevenlabs()` itself already supports fallback to silence when key is missing (`151-153`)
- So the top-level function defeats its own graceful degradation path.

Same issue exists in `video_pipeline_v3/tts_engine.py`:
- `311-313` raises before fallback can happen.

**Timing bug with CLIP entries in both TTS files:**
- In `dual_host_tts.py`, CLIP entries append metadata with `duration=clip_dur` but do **not** advance `current_time` (`292-303`).
- In `tts_engine.py`, CLIP entries are recorded with `duration: 0.0` and also do **not** advance `current_time` 

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — P3-SENTIMENT-INTEL — CYCLE 1
Generated: 2026-03-09 14:11
Models: grok, gemini, gpt4o

---

## SCORES

*Note: No model provided explicit numeric scores. Scores below are synthesized from the qualitative assessments across each model's section verdicts, using a 0–10 scale.*

| Subsystem         | Gemini | GPT-4o | Grok | Consensus |
|-------------------|--------|--------|------|-----------|
| Correctness       | 3/10   | 3/10   | 3/10 | **3/10**  |
| Law Compliance    | 1/10   | 1/10   | 1/10 | **1/10**  |
| Security          | 5/10   | 4/10   | 4/10 | **4/10**  |
| Frontend Quality  | 5/10   | 4/10   | 5/10 | **5/10**  |
| Backend Quality   | 4/10   | 4/10   | 2/10 | **3/10**  |
| Overall           | 3/10   | 3/10   | 3/10 | **3/10**  |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Polling instead of SSE (LAW 2 Violation)
- **What:** Frontend uses `setInterval(updateTelemetry, 30000)` to poll sentiment data every 30 seconds. LAW 2 explicitly mandates SSE via `/api/stream/sentiment`. No `EventSource` implementation exists anywhere in the codebase.
- **File/Line:** `templates/media_unified.html:793-797`
- **Change:** Remove the polling interval for sentiment. Implement `EventSource('/api/stream/sentiment')` that pushes on every new article classification. Create the corresponding backend SSE endpoint. Wire pushed events to update article sentiment badges in real time.

### U2 — Missing Backend Sentiment Classification Pipeline (LAW 1 Violation)
- **What:** All three models confirmed zero backend code exists for article sentiment classification. No `claude-haiku-4-5` usage, no 60-second classification SLA, no batch re-classification on restart, no writes to `articles.sentiment`, `articles.sentiment_confidence`, or `articles.sentiment_at`.
- **File/Line:** Backend routes (not present in reviewed code — must be created)
- **Change:** Implement the full classification pipeline: worker that processes new articles within 60s, restart catch-up for last 100 articles, model set to `claude-haiku-4-5`, DB writes to the required schema fields.

### U3 — Narrative Intelligence Absent from UI (LAW 3 Violation)
- **What:** LAW 3 designates narrative extraction as the key product differentiator. All three models confirmed the `<div class="mu-sentiment-why" id="sentiment-why">` element exists in HTML but is never populated by JavaScript. The narrative feature is architected but completely dead. No backend narrative extraction logic is present.
- **File/Line:** `templates/media_unified.html:83` (HTML element); JavaScript section around lines 590–655 (never writes to `#sentiment-why`)
- **Change:** Implement narrative extraction on the backend (identify labels like "ETF FLOWS", "HALVING CYCLE", "REGULATORY CLARITY" from article body). Surface the dominant narrative prominently in `#sentiment-why`. This is the feature that differentiates the product — treat it with corresponding priority.

### U4 — Anomaly D

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: templates/media_unified.html (809 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Media Hub — Protocol Pulse Intelligence{% endblock %}
   3 | {% block meta_description %}Live Bitcoin intelligence terminal. Nostr feeds, on-chain data, sentiment analysis, and original podcast content.{% endblock %}
   4 | 
   5 | {% block head %}
   6 | <link rel="preconnect" href="https://fonts.googleapis.com">
   7 | <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   8 | <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Instrument+Serif&family=Geist+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
   9 | <link rel="stylesheet" href="/static/css/media_unified_v5.css">
  10 | {% endblock %}
  11 | 
  12 | {% block body_class %}mu-page{% endblock %}
  13 | 
  14 | {% block content %}
  15 | 
  16 | <!-- ════════════════════════════════════════════════════
  17 |      TELEMETRY RIBBON (sticky below nav)
  18 |      ════════════════════════════════════════════════════ -->
  19 | <div class="mu-telemetry" id="mu-telemetry">
  20 |   <div class="mu-telemetry-inner">
  21 |     <!-- Fee Rate -->
  22 |     <div class="mu-telem-metric">
  23 |       <span class="mu-telem-value" id="telem-fees" data-metric="fees">--</span>
  24 |       <canvas class="mu-sparkline" id="spark-fees" width="40" height="12"></canvas>
  25 |       <span class="mu-telem-label">sat/vB</span>
  26 |     </div>
  27 | 
  28 |     <div class="mu-telem-sep"></div>
  29 | 
  30 |     <!-- Mempool -->
  31 |     <div class="mu-telem-metric">
  32 |       <span class="mu-telem-value" id="telem-mempool" data-metric="mempool">--</span>
  33 |       <canvas class="mu-sparkline" id="spark-mempool" width="40" height="12"></canvas>
  34 |       <span class="mu-telem-label">MB</span>
  35 |     </div>
  36 | 
  37 |     <div class="mu-telem-sep"></div>
  38 | 
  39 |     <!-- Hashrate -->
  40 |     <div class="mu-telem-metric">
  41 |       <span class="mu-telem-value" id="telem-hashrate" data-metric="hashrate">--</span>
  42 |       <canvas class="mu-sparkline" id="spark-hashrate" width="40" height="12"></canvas>
  43 |       <span class="mu-telem-label">EH/s</span>
  44 |     </div>
  45 | 
  46 |     <div class="mu-telem-sep"></div>
  47 | 
  48 |     <!-- Block Height -->
  49 |     <div class="mu-telem-metric">
  50 |       <span class="mu-telem-value mu-telem-btc" id="telem-block" data-metric="block">--</span>
  51 |       <span class="mu-telem-label">BLOCK</span>
  52 |     </div>
  53 | 
  54 |     <div class="mu-telem-sep"></div>
  55 | 
  56 |     <!-- Signal Strength -->
  57 |     <div class="mu-telem-metric mu-telem-signal">
  58 |       <span class="mu-telem-label">SIGNAL</span>
  59 |       <span class="mu-telem-value" id="telem-signal">0</span>
  60 |       <div class="mu-signal-bar">
  61 |         <div class="mu-signal-fill" id="signal-fill"></div>
  62 |       </div>
  63 |     </div>
  64 | 
  65 |     <div class="mu-telem-sep"></div>
  66 | 
  67 |     <!-- X Spaces -->
  68 |     <div class="mu-telem-metric" title="X Spaces Sentiment">
  69 |       <span class="mu-telem-label">X SPACES</span>
  70 |       <span class="mu-telem-value" id="telem-xs-score" style="min-width:24px;">--</span>
  71 |       <span class="mu-telem-label" id="telem-xs-label" style="font-size:0.55rem;"></span>
  72 |     </div>
  73 | 
  74 |     <!-- Sentiment Track -->
  75 |     <div class="mu-sentiment-track-wrap">
  76 |       <span class="mu-sentiment-label-l">FEAR</span>
  77 |       <div class="mu-sentiment-track" id="sentiment-track">
  78 |         <div class="mu-sentiment-dot" id="sentiment-dot"></div>
  79 |       </div>
  80 |       <span class="mu-sentiment-label-r">GREED</span>
  81 |       <span class="mu-sentiment-num" id="sentiment-num">--</span>
  82 |     </div>
  83 |     <div class="mu-sentiment-why" id="sentiment-why"></div>
  84 | 
  85 |     <!-- Health Dots -->
  86 |     <div class="mu-health">
  87 |       <div class="mu-health-dot loading" id="health-nostr" title="Nostr"></div>
  88 |       <div class="mu-health-dot loading" id="health-telemetry" title="Telemetry"></div>
  89 |       <div class="mu-health-dot loading" id="health-sentiment" title="Sentiment"></div>
  90 |       <div class="mu-health-dot loading" id="health-xspaces" title="X Spaces"></div>
  91 |     </div>
  92 | 
  93 |     <!-- Cmd+K -->
  94 |     <div class="mu-cmdk-hint" id="cmd-k-hint">&#x2318;K</div>
  95 |   </div>
  96 | 
  97 |   <!-- Thermal border -->
  98 |   <div class="mu-thermal-border" id="thermal-border"></div>
  99 | </div>
 100 | 
 101 | <!-- ════════════════════════════════════════════════════
 102 |      HERO: Featured Media + Delta Card
 103 |      ════════════════════════════════════════════════════ -->
 104 | <section class="mu-hero">
 105 |   <!-- Featured — text IS the hero -->
 106 |   <div class="mu-featured" id="mu-featured">
 107 |     <div class="mu-featured-text" id="hero-text">
 108 |       <span class="mu-latest-label">LATEST</span>
 109 |       {% if latest_episodes and latest_episodes|length > 0 %}
 110 |         {% set ep = latest_episodes[0] %}
 111 |         <h1 class="mu-hero-title">{{ ep.title }}</h1>
 112 |         <div class="mu-hero-meta">
 113 |           <span>EP {{ loop.index if loop is defined else podcast_count }}</span>
 114 |           <span class="mu-hero-dot">&middot;</span>
 115 |           <span>PROTOCOL PULSE</span>
 116 |           <span class="mu-hero-dot">&middot;</span>
 117 |           <span>{{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}</span>
 118 |         </div>
 119 |         <button class="mu-play-btn" id="hero-play"
 120 |                 data-vid="{{ ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' }}">
 121 |           <span class="mu-play-icon">&#9654;</span>
 122 |           <span>PLAY</span>
 123 |         </button>
 124 |       {% else %}
 125 |         <h1 class="mu-hero-title">Protocol Pulse</h1>
 126 |         <div class="mu-hero-meta">
 127 |           <span>{{ podcast_count }} episodes</span>
 128 |         </div>
 129 |       {% endif %}
 130 |     </div>
 131 |     <!-- YouTube embed appears here on play click -->
 132 |     <div class="mu-featured-embed" id="hero-embed"></div>
 133 |   </div>
 134 | 
 135 |   <!-- Since You Were Gone -->
 136 |   <div class="mu-delta" id="mu-delta">
 137 |     <div class="mu-delta-count" id="delta-count">...</div>
 138 |     <div class="mu-delta-label" id="delta-label">Loading intelligence...</div>
 139 |     <div class="mu-delta-items" id="delta-items"></div>
 140 |     <button class="mu-delta-showme" id="delta-showme">&darr; SHOW ME</button>
 141 |   </div>
 142 | </section>
 143 | 
 144 | <!-- ════════════════════════════════════════════════════
 145 |      SIGNAL DASHBOARD: 2 Columns
 146 |      ════════════════════════════════════════════════════ -->
 147 | <section class="mu-signals" id="mu-signals">
 148 |   <!-- Left: Nostr + X Live -->
 149 |   <div class="mu-col">
 150 |     <div class="mu-col-header">
 151 |       <span class="mu-col-title">NOSTR + X LIVE</span>
 152 |       <span class="mu-col-source"><span class="mu-health-dot" id="health-nostr-col"></span></span>
 153 |     </div>
 154 |     <!-- D4: Relay Status Bar -->
 155 |     <div class="mu-relay-status-bar" id="relay-status-bar">
 156 |       <div class="mu-relay-item" data-relay="relay.damus.io">
 157 |         <div class="mu-relay-dot" style="background:#555"></div>
 158 |         <span class="mu-relay-name">damus</span>
 159 |         <span class="mu-relay-status">OFFLINE</span>
 160 |         <span class="mu-relay-count">0 notes</span>
 161 |       </div>
 162 |       <div class="mu-relay-item" data-relay="nos.lol">
 163 |         <div class="mu-relay-dot" style="background:#555"></div>
 164 |         <span class="mu-relay-name">nos.lol</span>
 165 |         <span class="mu-relay-status">OFFLINE</span>
 166 |         <span class="mu-relay-count">0 notes</span>
 167 |       </div>
 168 |       <div class="mu-relay-item" data-relay="relay.nostr.band">
 169 |         <div class="mu-relay-dot" style="background:#555"></div>
 170 |         <span class="mu-relay-name">nostr.band</span>
 171 |         <span class="mu-relay-status">OFFLINE</span>
 172 |         <span class="mu-relay-count">0 notes</span>
 173 |       </div>
 174 |     </div>
 175 |     <div class="mu-col-feed" id="nostr-feed"></div>
 176 |     <div class="mu-col-count" id="nostr-count">0 notes</div>
 177 |   </div>
 178 | 
 179 |   <div class="mu-col-divider"></div>
 180 | 
 181 |   <!-- Right: Verified Highlights -->
 182 |   <div class="mu-col">
 183 |     <div class="mu-col-header">
 184 |       <span class="mu-col-title">VERIFIED HIGHLIGHTS</span>
 185 |       <span class="mu-col-source">partner channels <span class="mu-health-dot connected" id="health-highlights-col"></span></span>
 186 |     </div>
 187 |     <div class="mu-col-feed" id="highlights-feed">
 188 |       {% if ssr_highlights %}
 189 |         {% for h in ssr_highlights %}
 190 |         <div class="mu-highlight-item">
 191 |           <div class="mu-highlight-quote">&ldquo;{{ h.excerpt[:180] }}&rdquo;</div>
 192 |           <div class="mu-highlight-source">&mdash; {{ h.source }}{% if h.direction == 'bullish' %} <span style="color:#22c55e">BULLISH</span>{% elif h.direction == 'bearish' %} <span style="color:#dc2626">BEARISH</span>{% endif %}</div>
 193 |         </div>
 194 |         {% endfor %}
 195 |       {% endif %}
 196 |     </div>
 197 |   </div>
 198 | </section>
 199 | 
 200 | <!-- ════════════════════════════════════════════════════
 201 |      SIGNAL STRENGTH GAUGE (Phase 2)
 202 |      ════════════════════════════════════════════════════ -->
 203 | <section class="mu-section mu-signal-section" id="mu-signal-section">
 204 |   <div class="mu-section-head">
 205 |     <h2 class="mu-section-title">SIGNAL STRENGTH</h2>
 206 |     <span class="mu-section-sub">Composite intelligence score — live</span>
 207 |   </div>
 208 |   <div class="mu-signal-gauge-wrap">
 209 |     <div id="signal-strength-gauge">
 210 |       <div class="mu-gauge-ring" style="--score:50%;--color:#E67E22">
 211 |         <div class="mu-gauge-inner">
 212 |           <div class="mu-gauge-score">--</div>
 213 |           <div class="mu-gauge-label">SIGNAL</div>
 214 |           <div class="mu-gauge-level">LOADING</div>
 215 |         </div>
 216 |       </div>
 217 |     </div>
 218 |     <div class="mu-signal-breakdown" id="signal-breakdown">
 219 |       <div class="mu-sig-row">
 220 |         <span class="mu-sig-key">SENTIMENT</span>
 221 |         <span class="mu-sig-val" id="sig-sentiment">--</span>
 222 |         <span class="mu-sig-weight">70%</span>
 223 |       </div>
 224 |       <div class="mu-sig-row">
 225 |         <span class="mu-sig-key">X SPACES</span>
 226 |         <span class="mu-sig-val" id="sig-spaces">--</span>
 227 |         <span class="mu-sig-weight">30%</span>
 228 |       </div>
 229 |       <div class="mu-sig-row mu-sig-total">
 230 |         <span class="mu-sig-key">COMPOSITE</span>
 231 |         <span class="mu-sig-val" id="sig-composite">--</span>
 232 |         <span class="mu-sig-weight">&nbsp;</span>
 233 |       </div>
 234 |     </div>
 235 |   </div>
 236 | </section>
 237 | 
 238 | <!-- ════════════════════════════════════════════════════
 239 |      REDDIT PULSE
 240 |      ════════════════════════════════════════════════════ -->
 241 | <section class="mu-section" id="mu-reddit">
 242 |   <div class="mu-section-head">
 243 |     <h2 class="mu-section-title">REDDIT PULSE</h2>
 244 |     <span class="mu-section-sub">r/bitcoin &middot; live</span>
 245 |   </div>
 246 |   <div class="mu-reddit-feed" id="reddit-feed"></div>
 247 | </section>
 248 | 
 249 | <!-- ════════════════════════════════════════════════════
 250 |      PARTNER CHANNELS TODAY
 251 |      ════════════════════════════════════════════════════ -->
 252 | <section class="mu-section" id="mu-partners">
 253 |   <div class="mu-section-head">
 254 |     <h2 class="mu-section-title">PARTNER CHANNELS TODAY</h2>
 255 |     <span class="mu-section-sub">{{ series_count }} channels tracked</span>
 256 |   </div>
 257 |   <div class="mu-partner-rail" id="partner-rail"></div>
 258 | </section>
 259 | 
 260 | <!-- ════════════════════════════════════════════════════
 261 |      ORIGINAL SERIES
 262 |      ════════════════════════════════════════════════════ -->
 263 | <section class="mu-section" id="mu-series">
 264 |   <div class="mu-section-head">
 265 |     <h2 class="mu-section-title">ORIGINAL SERIES</h2>
 266 |   </div>
 267 |   <div class="mu-series-grid">
 268 |     {% for s in series_list %}
 269 |     <a class="mu-series-item" href="https://youtube.com/watch?v={{ s.first_id }}" target="_blank" rel="noopener"
 270 |        data-thumb="https://img.youtube.com/vi/{{ s.first_id }}/maxresdefault.jpg">
 271 |       <div class="mu-series-name">{{ s.title }}</div>
 272 |       <div class="mu-series-sub">{{ s.description|upper if s.description else '' }}</div>
 273 |       <div class="mu-series-count">{{ s.ep_count }} episodes</div>
 274 |     </a>
 275 |     {% endfor %}
 276 |   </div>
 277 | </section>
 278 | 
 279 | <!-- ════════════════════════════════════════════════════
 280 |      LATEST EPISODES
 281 |      ════════════════════════════════════════════════════ -->
 282 | <section class="mu-section" id="mu-episodes">
 283 |   <div class="mu-section-head">
 284 |     <h2 class="mu-section-title">LATEST EPISODES</h2>
 285 |     <span class="mu-section-sub">{{ podcast_count }} episodes</span>
 286 |   </div>
 287 |   <div class="mu-ep-filters">
 288 |     <button class="mu-chip active" data-filter="all">All</button>
 289 |     <button class="mu-chip" data-filter="episodes">Episodes</button>
 290 |     <button class="mu-chip" data-filter="clips">Clips</button>
 291 |     <button class="mu-chip" data-filter="briefings">Briefings</button>
 292 |   </div>
 293 |   <div class="mu-ep-grid">
 294 |     {% for ep in latest_episodes[:12] %}
 295 |     {% set vid_id = ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' %}
 296 |     <a class="mu-ep-item" href="https://youtube.com/watch?v={{ vid_id }}" target="_blank" rel="noopener">
 297 |       <div class="mu-ep-thumb">
 298 |         <img src="https://img.youtube.com/vi/{{ vid_id }}/mqdefault.jpg" alt="{{ ep.title }}" loading="lazy" width="320" height="180">
 299 |       </div>
 300 |       <div class="mu-ep-info">
 301 |         <div class="mu-ep-title">{{ ep.title }}</div>
 302 |         <div class="mu-ep-meta">
 303 |           {{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}
 304 |           {% if ep.host %} &middot; {{ ep.host }}{% endif %}
 305 |         </div>
 306 |       </div>
 307 |     </a>
 308 |     {% endfor %}
 309 |   </div>
 310 | </section>
 311 | 
 312 | <!-- ════════════════════════════════════════════════════
 313 |      THE LIBRARY
 314 |      ════════════════════════════════════════════════════ -->
 315 | <section class="mu-section" id="mu-library">
 316 |   <div class="mu-section-head">
 317 |     <h2 class="mu-section-title">THE LIBRARY</h2>
 318 |     <span class="mu-section-sub">Curated reading for sovereign minds</span>
 319 |   </div>
 320 | 
 321 |   <!-- Leaderboard + Rising Stars -->
 322 |   <div class="mu-lib-top">
 323 |     <div class="mu-lib-leaderboard">
 324 |       <div class="mu-lib-subtitle">LEADERBOARD</div>
 325 |       <div class="mu-lb-item" data-rank="1">
 326 |         <span class="mu-lb-rank">#1</span>
 327 |         <span class="mu-lb-title">The Bitcoin Standard</span>
 328 |         <span class="mu-lb-dot">&middot;</span>
 329 |         <span class="mu-lb-author">Saifedean Ammous</span>
 330 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:100%"></div></div>
 331 |         <button class="mu-vote-btn" data-book="bitcoin-standard">&#128077;</button>
 332 |         <span class="mu-vote-count" data-book="bitcoin-standard">0</span>
 333 |       </div>
 334 |       <div class="mu-lb-item" data-rank="2">
 335 |         <span class="mu-lb-rank">#2</span>
 336 |         <span class="mu-lb-title">Broken Money</span>
 337 |         <span class="mu-lb-dot">&middot;</span>
 338 |         <span class="mu-lb-author">Lyn Alden</span>
 339 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:82%"></div></div>
 340 |         <button class="mu-vote-btn" data-book="broken-money">&#128077;</button>
 341 |         <span class="mu-vote-count" data-book="broken-money">0</span>
 342 |       </div>
 343 |       <div class="mu-lb-item" data-rank="3">
 344 |         <span class="mu-lb-rank">#3</span>
 345 |         <span class="mu-lb-title">The Sovereign Individual</span>
 346 |         <span class="mu-lb-dot">&middot;</span>
 347 |         <span class="mu-lb-author">Davidson &amp; Rees-Mogg</span>
 348 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:68%"></div></div>
 349 |         <button class="mu-vote-btn" data-book="sovereign-individual">&#128077;</button>
 350 |         <span class="mu-vote-count" data-book="sovereign-individual">0</span>
 351 |       </div>
 352 |       <div class="mu-lb-item" data-rank="4">
 353 |         <span class="mu-lb-rank">#4</span>
 354 |         <span class="mu-lb-title">Mastering Bitcoin</span>
 355 |         <span class="mu-lb-dot">&middot;</span>
 356 |         <span class="mu-lb-author">Andreas Antonopoulos</span>
 357 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:55%"></div></div>
 358 |         <button class="mu-vote-btn" data-book="mastering-bitcoin">&#128077;</button>
 359 |         <span class="mu-vote-count" data-book="mastering-bitcoin">0</span>
 360 |       </div>
 361 |     </div>
 362 | 
 363 |     <div class="mu-lib-rising">
 364 |       <div class="mu-lib-subtitle">RISING STARS</div>
 365 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Resistance Money &middot; Andrew M. Bailey</div>
 366 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Bitcoin is Venice &middot; Allen Farrington</div>
 367 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Check Your Financial Privilege &middot; Alex Gladstein</div>
 368 |     </div>
 369 |   </div>
 370 | 
 371 |   <!-- Learning Paths -->
 372 |   <div class="mu-lib-paths">
 373 |     <div class="mu-lib-subtitle">LEARNING PATHS</div>
 374 |     <div class="mu-paths-grid">
 375 |       <div class="mu-path">
 376 |         <div class="mu-path-name">UNDERSTAND MONEY</div>
 377 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1119473861" target="_blank" rel="noopener">The Bitcoin Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 378 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544526474" target="_blank" rel="noopener">The Fiat Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 379 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0CN14FKHF" target="_blank" rel="noopener">Broken Money <span class="mu-path-author">&middot; Lyn Alden</span></a>
 380 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1999257405" target="_blank" rel="noopener">The Price of Tomorrow <span class="mu-path-author">&middot; Jeff Booth</span></a>
 381 |       </div>
 382 |       <div class="mu-path">
 383 |         <div class="mu-path-name">UNDERSTAND BITCOIN</div>
 384 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1098150090" target="_blank" rel="noopener">Mastering Bitcoin <span class="mu-path-author">&middot; Andreas Antonopoulos</span></a>
 385 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B07MWGP64R" target="_blank" rel="noopener">Inventing Bitcoin <span class="mu-path-author">&middot; Yan Pritzker</span></a>
 386 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B08YQMC2WM" target="_blank" rel="noopener">The Blocksize War <span class="mu-path-author">&middot; Jonathan Bier</span></a>
 387 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0B3L61JYN" target="_blank" rel="noopener">The Genesis Book <span class="mu-path-author">&middot; Aaron van Wirdum</span></a>
 388 |       </div>
 389 |       <div class="mu-path">
 390 |         <div class="mu-path-name">UNDERSTAND FREEDOM</div>
 391 |         <a class="mu-path-book" href="https://www.amazon.com/dp/0684832720" target="_blank" rel="noopener">The Sovereign Individual <span class="mu-path-author">&middot; Davidson &amp; Rees-Mogg</span></a>
 392 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544542895" target="_blank" rel="noopener">Softwar <span class="mu-path-author">&middot; Jason Lowery</span></a>
 393 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09C4GLPYX" target="_blank" rel="noopener">Thank God for Bitcoin <span class="mu-path-author">&middot; Jimmy Song et al.</span></a>
 394 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09KLPNBPC" target="_blank" rel="noopener">Bitcoin is Venice <span class="mu-path-author">&middot; Allen Farrington</span></a>
 395 |       </div>
 396 |     </div>
 397 |   </div>
 398 | 
 399 |   <!-- Full Library (collapsed by default) -->
 400 |   <button class="mu-lib-toggle" id="lib-toggle">&darr; VIEW FULL LIBRARY</button>
 401 |   <div class="mu-lib-full" id="lib-full">
 402 |     <div class="mu-lib-grid">
 403 |       {% for book in all_books %}
 404 |       <a class="mu-lib-book" href="{{ book.amazon_url }}" target="_blank" rel="noopener">
 405 |         <div class="mu-lib-cover" style="background:{{ book.color|default('#222') }}">
 406 |           <span>{{ book.title[:40] }}</span>
 407 |         </div>
 408 |         <div class="mu-lib-book-title">{{ book.title }}</div>
 409 |         <div class="mu-lib-book-author">{{ book.author }}</div>
 410 |         <button class="mu-vote-btn" data-book="{{ book.title|lower|replace(' ','-') }}">&#128077;</button>
 411 |         <span class="mu-vote-count" data-book="{{ book.title|lower|replace(' ','-') }}">0</span>
 412 |       </a>
 413 |       {% endfor %}
 414 |     </div>
 415 |   </div>
 416 | </section>
 417 | 
 418 | <!-- ════════════════════════════════════════════════════
 419 |      NEWSLETTER CTA
 420 |      ════════════════════════════════════════════════════ -->
 421 | <section class="mu-newsletter" id="mu-newsletter">
 422 |   <h2 class="mu-nl-title">Sovereign Intel Briefing</h2>
 423 |   <p class="mu-nl-sub">Daily Bitcoin intelligence. No noise. No ads. Delivered before markets open.</p>
 424 |   <div class="mu-nl-form">
 425 |     <input type="email" placeholder="your@email.com" id="newsletter-email" autocomplete="email">
 426 |     <button id="newsletter-submit">Subscribe</button>
 427 |   </div>
 428 | </section>
 429 | 
 430 | <!-- ════════════════════════════════════════════════════
 431 |      COMMAND PALETTE (Cmd+K)
 432 |      ════════════════════════════════════════════════════ -->
 433 | <div class="mu-cmd-overlay" id="cmd-overlay">
 434 |   <div class="mu-cmd-box">
 435 |     <div class="mu-cmd-prompt">
 436 |       <span class="mu-cmd-caret">&gt;</span>
 437 |       <input class="mu-cmd-input" id="cmd-input" placeholder="" autocomplete="off" spellcheck="false">
 438 |     </div>
 439 |     <div class="mu-cmd-results" id="cmd-results"></div>
 440 |     <div class="mu-cmd-footer">Press &uarr;&darr; to navigate &middot; Enter to select &middot; Esc to close</div>
 441 |   </div>
 442 | </div>
 443 | 
 444 | <!-- ════════════════════════════════════════════════════
 445 |      AUDIO BAR (floating, hidden until active)
 446 |      ════════════════════════════════════════════════════ -->
 447 | <div class="mu-audio-bar" id="audio-bar">
 448 |   <button class="mu-ab-play" id="ab-play">&#9654;</button>
 449 |   <span class="mu-ab-info" id="ab-info"></span>
 450 |   <div class="mu-ab-progress">
 451 |     <div class="mu-ab-track">
 452 |       <div class="mu-ab-fill" id="ab-fill"></div>
 453 |       <div class="mu-ab-dot" id="ab-dot"></div>
 454 |     </div>
 455 |   </div>
 456 |   <span class="mu-ab-time" id="ab-time">0:00 / 0:00</span>
 457 |   <button class="mu-ab-speed" id="ab-speed">1&times;</button>
 458 | </div>
 459 | 
 460 | <!-- D5: Health Strip -->
 461 | <div id="health-strip" class="mu-health-strip"></div>
 462 | 
 463 | {% endblock %}
 464 | 
 465 | {% block scripts %}
 466 | <script src="/static/js/media_unified_v5.js"></script>
 467 | <script>
 468 | function subscribeNewsletter() {
 469 |   const email = document.getElementById('newsletter-email').value;
 470 |   if (!email || !email.includes('@')) { alert('Enter a valid email'); return; }
 471 |   fetch('/api/newsletter/subscribe', {
 472 |     method: 'POST',
 473 |     headers: {'Content-Type': 'application/json'},
 474 |     body: JSON.stringify({email: email})
 475 |   }).then(r => r.json()).then(d => {
 476 |     if (d.success) alert('Subscribed! Check your inbox.');
 477 |     else alert(d.message || 'Subscription failed');
 478 |   }).catch(() => alert('Network error — try again'));
 479 | }
 480 | document.getElementById('newsletter-submit')?.addEventListener('click', subscribeNewsletter);
 481 | 
 482 | // Phase 2: X Spaces + telemetry wired in media_p2_init below
 483 | </script>
 484 | 
 485 | <style>
 486 | /* ── D4: Relay Status Bar ─────────────────────── */
 487 | .mu-relay-status-bar {
 488 |   display: flex; gap: 8px; padding: 6px 12px;
 489 |   background: rgba(247,147,26,0.04); border-bottom: 1px solid #1a1a1a;
 490 |   flex-wrap: wrap;
 491 | }
 492 | .mu-relay-item {
 493 |   display: flex; align-items: center; gap: 5px;
 494 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 495 | }
 496 | .mu-relay-dot {
 497 |   width: 7px; height: 7px; border-radius: 50%;
 498 |   animation: mu-pulse 2s infinite;
 499 | }
 500 | .mu-relay-name { color: #888; letter-spacing: 1px; }
 501 | .mu-relay-status { color: #555; font-size: 8px; }
 502 | .mu-relay-count { color: #444; font-size: 8px; }
 503 | 
 504 | /* ── D3: Signal Strength Gauge ────────────────── */
 505 | .mu-signal-section { padding: 24px 0; }
 506 | .mu-signal-gauge-wrap {
 507 |   display: flex; align-items: center; gap: 40px;
 508 |   padding: 20px 0; flex-wrap: wrap;
 509 | }
 510 | #signal-strength-gauge { flex-shrink: 0; }
 511 | .mu-gauge-ring {
 512 |   position: relative; width: 140px; height: 140px;
 513 |   border-radius: 50%;
 514 |   background: conic-gradient(var(--color) var(--score), #1a1a1a 0);
 515 |   display: flex; align-items: center; justify-content: center;
 516 |   box-shadow: 0 0 24px color-mix(in srgb, var(--color) 30%, transparent);
 517 | }
 518 | .mu-gauge-inner {
 519 |   width: 100px; height: 100px; border-radius: 50%;
 520 |   background: #0a0a0a;
 521 |   display: flex; flex-direction: column;
 522 |   align-items: center; justify-content: center; gap: 2px;
 523 | }
 524 | .mu-gauge-score {
 525 |   font-family: 'Geist Mono', monospace; font-size: 30px;
 526 |   font-weight: 900; color: var(--color); line-height: 1;
 527 | }
 528 | .mu-gauge-label {
 529 |   font-family: 'Geist Mono', monospace; font-size: 8px;
 530 |   color: #555; letter-spacing: 2px;
 531 | }
 532 | .mu-gauge-level {
 533 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 534 |   font-weight: 700; color: var(--color);
 535 | }
 536 | .mu-signal-breakdown {
 537 |   display: flex; flex-direction: column; gap: 10px; min-width: 220px;
 538 | }
 539 | .mu-sig-row {
 540 |   display: flex; gap: 8px; align-items: center;
 541 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 542 | }
 543 | .mu-sig-key { color: #555; letter-spacing: 1px; min-width: 90px; }
 544 | .mu-sig-val { color: #F7931A; font-weight: 700; min-width: 32px; }
 545 | .mu-sig-weight { color: #333; font-size: 9px; }
 546 | .mu-sig-total .mu-sig-key { color: #888; }
 547 | .mu-sig-total .mu-sig-val { color: #fff; font-size: 14px; }
 548 | 
 549 | /* ── D5: Health Strip ─────────────────────────── */
 550 | .mu-health-strip {
 551 |   position: fixed; bottom: 0; left: 0; right: 0;
 552 |   height: 30px; background: #050505;
 553 |   border-top: 1px solid #1a1a1a;
 554 |   display: flex; align-items: center;
 555 |   padding: 0 16px; gap: 20px; z-index: 9999;
 556 |   overflow-x: auto; overflow-y: hidden;
 557 | }
 558 | .mu-hs-item { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
 559 | .mu-hs-dot {
 560 |   width: 7px; height: 7px; border-radius: 50%;
 561 |   animation: mu-pulse 2s infinite;
 562 | }
 563 | .mu-hs-name {
 564 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 565 |   color: #555; letter-spacing: 1px;
 566 | }
 567 | .mu-hs-lat {
 568 |   font-family: 'Geist Mono', monospace; font-size: 8px; color: #333;
 569 | }
 570 | @keyframes mu-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
 571 | 
 572 | /* Bottom padding so health strip doesn't cover content */
 573 | .mu-page { padding-bottom: 38px; }
 574 | </style>
 575 | 
 576 | <script>
 577 | // ═══════════════════════════════════════════════════════
 578 | // MEDIA UNIFIED — PHASE 2 RUNTIME
 579 | // D1: Clean API wiring  D2: Live telemetry  D3: Signal gauge
 580 | // D4: Nostr relay panel  D5: Health strip
 581 | // ═══════════════════════════════════════════════════════
 582 | 
 583 | (function() {
 584 |   'use strict';
 585 | 
 586 |   // ── Cache ────────────────────────────────────────────
 587 |   var _cache = { sentiment: null, spaces: null, tradfi: null };
 588 | 
 589 |   // ── D1 + D2: Live Telemetry Wiring ──────────────────
 590 |   async function fetchSentiment() {
 591 |     try {
 592 |       var r = await fetch('/api/media/sentiment');
 593 |       var d = await r.json();
 594 |       _cache.sentiment = d;
 595 |       return d;
 596 |     } catch(e) {
 597 |       console.warn('[P2] sentiment fetch failed:', e);
 598 |       return _cache.sentiment || { composite_score: null, label: 'OFFLINE' };
 599 |     }
 600 |   }
 601 | 
 602 |   async function fetchSpaces() {
 603 |     try {
 604 |       var r = await fetch('/api/spaces/live');
 605 |       var d = await r.json();
 606 |       _cache.spaces = d;
 607 |       return d;
 608 |     } catch(e) {
 609 |       console.warn('[P2] spaces fetch failed:', e);
 610 |       return _cache.spaces || { spaces: [], score: 0, label: 'OFFLINE' };
 611 |     }
 612 |   }
 613 | 
 614 |   async function fetchTradfi() {
 615 |     try {
 616 |       var r = await fetch('/api/tradfi/signals');
 617 |       var d = await r.json();
 618 |       _cache.tradfi = d;
 619 |       return d;
 620 |     } catch(e) {
 621 |       return _cache.tradfi || null;
 622 |     }
 623 |   }
 624 | 
 625 |   // ── D3: Signal Strength Gauge Renderer ──────────────
 626 |   function computeSignalStrength(sentData, spacesData) {
 627 |     var sentScore = (sentData && sentData.composite_score != null)
 628 |       ? parseFloat(sentData.composite_score) : 50;
 629 |     var spacesCount = (spacesData && spacesData.spaces)
 630 |       ? spacesData.spaces.length : 0;
 631 |     var spacesScore = Math.min(spacesCount * 10, 100);
 632 |     return Math.round(sentScore * 0.7 + spacesScore * 0.3);
 633 |   }
 634 | 
 635 |   function renderSignalGauge(score, sentScore, spacesScore) {
 636 |     var el = document.getElementById('signal-strength-gauge');
 637 |     if (!el) return;
 638 |     var level = score >= 70 ? 'HIGH' : score >= 40 ? 'MODERATE' : 'LOW';
 639 |     var color = score >= 70 ? '#F7931A' : score >= 40 ? '#E67E22' : '#666';
 640 |     el.innerHTML =
 641 |       '<div class="mu-gauge-ring" style="--score:' + score + '%;--color:' + color + '">' +
 642 |         '<div class="mu-gauge-inner">' +
 643 |           '<div class="mu-gauge-score">' + score + '</div>' +
 644 |           '<div class="mu-gauge-label">SIGNAL</div>' +
 645 |           '<div class="mu-gauge-level">' + level + '</div>' +
 646 |         '</div>' +
 647 |       '</div>';
 648 |     // Update breakdown
 649 |     var sEl = document.getElementById('sig-sentiment');
 650 |     var spEl = document.getElementById('sig-spaces');
 651 |     var cEl = document.getElementById('sig-composite');
 652 |     if (sEl) sEl.textContent = Math.round(sentScore);
 653 |     if (spEl) spEl.textContent = Math.round(Math.min((spacesScore||0)*10,100));
 654 |     if (cEl) cEl.textContent = score;
 655 |   }
 656 | 
 657 |   // ── D4: Nostr Relay Status Panel Updater ────────────
 658 |   // Hook into the existing RelayManager to sync relay dots
 659 |   function syncRelayStatusBar() {
 660 |     if (!window.relayManager || !window.relayManager.sockets) return;
 661 |     var sockets = window.relayManager.sockets;
 662 |     Object.keys(sockets).forEach(function(url) {
 663 |       var ws = sockets[url];
 664 |       var relayName = url.replace('wss://','').split('/')[0];
 665 |       var el = document.querySelector('[data-relay="' + relayName + '"]');
 666 |       if (!el) return;
 667 |       var dot = el.querySelector('.mu-relay-dot');
 668 |       var statusEl = el.querySelector('.mu-relay-status');
 669 |       var countEl = el.querySelector('.mu-relay-count');
 670 |       if (!dot || !statusEl) return;
 671 |       var rs = ws.readyState;
 672 |       if (rs === 1) { // OPEN
 673 |         dot.style.background = '#F7931A';
 674 |         statusEl.textContent = 'LIVE';
 675 |         statusEl.style.color = '#F7931A';
 676 |       } else if (rs === 0) { // CONNECTING
 677 |         dot.style.background = '#E67E22';
 678 |         statusEl.textContent = 'CONNECTING';
 679 |         statusEl.style.color = '#E67E22';
 680 |       } else {
 681 |         dot.style.background = '#444';
 682 |         statusEl.textContent = 'OFFLINE';
 683 |         statusEl.style.color = '#444';
 684 |       }
 685 |     });
 686 |     // Sync note counts from state
 687 |     if (window.state && window.state.nostrNotes) {
 688 |       var byRelay = {};
 689 |       window.state.nostrNotes.forEach(function(n) {
 690 |         if (n.relay) byRelay[n.relay] = (byRelay[n.relay]||0) + 1;
 691 |       });
 692 |       Object.keys(byRelay).forEach(function(url) {
 693 |         var relayName = url.replace('wss://','').split('/')[0];
 694 |         var el = document.querySelector('[data-relay="' + relayName + '"]');
 695 |         if (!el) return;
 696 |         var countEl = el.querySelector('.mu-relay-count');
 697 |         if (countEl) countEl.textContent = byRelay[url] + ' notes';
 698 |       });
 699 |     }
 700 |   }
 701 | 
 702 |   // ── X Spaces Telemetry Display (D1 replacement) ─────
 703 |   function updateXSpacesTelemetry(spacesData) {
 704 |     var xs = spacesData || {};
 705 |     var xsScore = xs.score != null ? xs.score : (xs.x_spaces ? xs.x_spaces.score : null);
 706 |     var xsLabel = xs.label || (xs.x_spaces ? xs.x_spaces.label : '') || '';
 707 |     var activeCount = xs.spaces ? xs.spaces.length : (xs.active_count || 0);
 708 | 
 709 |     var sc = document.getElementById('telem-xs-score');
 710 |     var lb = document.getElementById('telem-xs-label');
 711 |     var dot = document.getElementById('health-xspaces');
 712 |     if (sc && xsScore != null) sc.textContent = xsScore;
 713 |     if (lb && xsLabel) {
 714 |       lb.textContent = xsLabel;
 715 |       lb.style.color = xsLabel === 'BULLISH' ? '#22c55e'
 716 |                      : xsLabel === 'BEARISH' ? '#ef4444' : '#888';
 717 |     }
 718 |     if (dot) {
 719 |       dot.classList.remove('loading');
 720 |       dot.classList.add(activeCount > 0 ? 'connected' : 'error');
 721 |     }
 722 | 
 723 |     // Provide blend shim to existing signal engine
 724 |     window._ppBlendXSpaces = function(baseScore) {
 725 |       if (xsScore != null) return Math.round(baseScore * 0.7 + xsScore * 0.3);
 726 |       return baseScore;
 727 |     };
 728 |   }
 729 | 
 730 |   // ── D2: Master 30s Telemetry Poll ───────────────────
 731 |   async function updateTelemetry() {
 732 |     var results = await Promise.allSettled([
 733 |       fetchSentiment(),
 734 |       fetchSpaces(),
 735 |       fetchTradfi()
 736 |     ]);
 737 | 
 738 |     var sentData  = results[0].status === 'fulfilled' ? results[0].value : (_cache.sentiment || {});
 739 |     var spacesData = results[1].status === 'fulfilled' ? results[1].value : (_cache.spaces || {});
 740 | 
 741 |     // Update X Spaces display
 742 |     updateXSpacesTelemetry(spacesData);
 743 | 
 744 |     // D3: Compute + render Signal Strength gauge
 745 |     var spacesCount = spacesData.spaces ? spacesData.spaces.length : 0;
 746 |     var sentScore = sentData.composite_score != null ? parseFloat(sentData.composite_score) : 50;
 747 |     var score = computeSignalStrength(sentData, spacesData);
 748 |     renderSignalGauge(score, sentScore, spacesCount);
 749 | 
 750 |     // D4: Sync relay status bar
 751 |     syncRelayStatusBar();
 752 |   }
 753 | 
 754 |   // ── D5: Health Strip ─────────────────────────────────
 755 |   var P2_SERVICES = [
 756 |     { name: 'PIPELINE', url: 'https://relay.protocolpulse.io/health' },
 757 |     { name: 'ORACLE',   url: 'https://avatar.protocolpulse.io/health' },
 758 |     { name: 'REPLIT',   url: '/api/health' },
 759 |     { name: 'SPACES',   url: '/api/spaces/live' },
 760 |     { name: 'TRADFI',   url: '/api/tradfi/signals' },
 761 |   ];
 762 | 
 763 |   async function checkService(svc) {
 764 |     var start = Date.now();
 765 |     try {
 766 |       var r = await Promise.race([
 767 |         fetch(svc.url, { method: 'HEAD', cache: 'no-store' }),
 768 |         new Promise(function(_, rej) { setTimeout(function(){ rej(new Error('timeout')); }, 5000); })
 769 |       ]);
 770 |       return { status: r.ok ? 'UP' : 'DEGRADED', lat: Date.now() - start };
 771 |     } catch(e) {
 772 |       return { status: 'DOWN', lat: null };
 773 |     }
 774 |   }
 775 | 
 776 |   async function updateHealthStrip() {
 777 |     var strip = document.getElementById('health-strip');
 778 |     if (!strip) return;
 779 |     var results = await Promise.allSettled(P2_SERVICES.map(checkService));
 780 |     strip.innerHTML = P2_SERVICES.map(function(svc, i) {
 781 |       var r = (results[i].status === 'fulfilled' ? results[i].value : null) || { status: 'UNKNOWN', lat: null };
 782 |       var color = r.status === 'UP' ? '#27AE60' : r.status === 'DEGRADED' ? '#E67E22' : '#444';
 783 |       var lat = r.lat ? r.lat + 'ms' : '--';
 784 |       return '<div class="mu-hs-item">' +
 785 |         '<div class="mu-hs-dot" style="background:' + color + '"></div>' +
 786 |         '<span class="mu-hs-name">' + svc.name + '</span>' +
 787 |         '<span class="mu-hs-lat">' + lat + '</span>' +
 788 |       '</div>';
 789 |     }).join('');
 790 |   }
 791 | 
 792 |   // ── BOOT ─────────────────────────────────────────────
 793 |   document.addEventListener('DOMContentLoaded', function() {
 794 |     // D2+D3: initial poll + 30s interval
 795 |     updateTelemetry();
 796 |     setInterval(updateTelemetry, 30000);
 797 | 
 798 |     // D4: Relay status sync every 5s
 799 |     setInterval(syncRelayStatusBar, 5000);
 800 | 
 801 |     // D5: Health strip initial + 60s interval
 802 |     updateHealthStrip();
 803 |     setInterval(updateHealthStrip, 60000);
 804 |   });
 805 | 
 806 | })();
 807 | </script>
 808 | {% endblock %}
 809 | 
```

### File: video_pipeline_v3/dual_host_tts.py (372 lines)
```
   1 | #!/usr/bin/env python3
   2 | """dual_host_tts.py — Single-host TTS engine for Pulse Check.
   3 | 
   4 | Generates audio using ElevenLabs TTS.
   5 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) — PBX approved single narrator at 1.10x speed.
   6 | Both host=1 and host=2 entries route to Mark (single voice, no gender swap).
   7 | 
   8 | Usage:
   9 |     from dual_host_tts import generate_dialogue_audio
  10 | 
  11 |     dialogue = [
  12 |         {"host": 1, "text": "So Saylor just dropped another banger..."},
  13 |         {"host": 2, "text": "Let's roll the clip."},
  14 |         {"host": "CLIP", "duration": 30, "source": "@MicroStrategy"},
  15 |         {"host": 2, "text": "Ok here's what blows my mind about this..."},
  16 |         {"host": 1, "text": "Right, and if you think about it..."},
  17 |     ]
  18 | 
  19 |     result = generate_dialogue_audio(dialogue, output_dir="output/")
  20 |     # Returns: {
  21 |     #   "lines": [...],
  22 |     #   "full": "output/full_dialogue.m4a",
  23 |     #   "total_duration": 45.0,
  24 |     # }
  25 | """
  26 | import os
  27 | import sys
  28 | import json
  29 | import subprocess
  30 | import time
  31 | 
  32 | BASE = os.path.dirname(os.path.abspath(__file__))
  33 | sys.path.insert(0, BASE)
  34 | 
  35 | try:
  36 |     import requests
  37 |     HAS_REQUESTS = True
  38 | except ImportError:
  39 |     HAS_REQUESTS = False
  40 | 
  41 | from relay import get_key
  42 | 
  43 | # ── Voice configuration ──────────────────────────────────────────────────────
  44 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST ONLY — Mark at 1.10x speed.
  45 | # Nicole (piTKgcLEGmPE4e6mEKli) and Chris (iP95p4xoKVk53GoZ742B) are BANNED.
  46 | # Both host=1 and host=2 map to Mark.
  47 | 
  48 | _MARK_VOICE = {
  49 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  50 |     "name": "Mark",
  51 |     "model_id": "eleven_turbo_v2_5",
  52 |     "voice_settings": {
  53 |         "stability": 0.55,
  54 |         "similarity_boost": 0.80,
  55 |         "style": 0.15,
  56 |         "use_speaker_boost": True,
  57 |         "speed": 1.10,
  58 |     },
  59 | }
  60 | 
  61 | VOICES = {
  62 |     1: _MARK_VOICE,
  63 |     2: _MARK_VOICE,  # both hosts → Mark (single narrator)
  64 | }
  65 | 
  66 | SILENCE_GAP = 0.3  # seconds between speakers
  67 | MAX_CHUNK_CHARS = 4900
  68 | 
  69 | _KEY_CACHE: dict = {}
  70 | 
  71 | 
  72 | def _get_cached_key(name: str) -> str:
  73 |     if name not in _KEY_CACHE:
  74 |         k = get_key(name)
  75 |         if k:
  76 |             _KEY_CACHE[name] = k.strip()
  77 |     return _KEY_CACHE.get(name, "")
  78 | 
  79 | 
  80 | def ffprobe_duration(path: str) -> float:
  81 |     r = subprocess.run(
  82 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  83 |          "-of", "csv=p=0", path],
  84 |         capture_output=True, text=True,
  85 |     )
  86 |     try:
  87 |         return float(r.stdout.strip())
  88 |     except Exception:
  89 |         return 0.0
  90 | 
  91 | 
  92 | def _generate_silence(output_path: str, duration: float) -> bool:
  93 |     r = subprocess.run(
  94 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  95 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  96 |          "-c:a", "aac", "-b:a", "192k", output_path],
  97 |         capture_output=True, text=True, timeout=30,
  98 |     )
  99 |     return r.returncode == 0 and os.path.exists(output_path)
 100 | 
 101 | 
 102 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
 103 |     r = subprocess.run(
 104 |         ["ffmpeg", "-y", "-i", mp3_path,
 105 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
 106 |         capture_output=True, text=True, timeout=120,
 107 |     )
 108 |     return r.returncode == 0 and os.path.exists(m4a_path)
 109 | 
 110 | 
 111 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
 112 |     if len(text) <= max_chars:
 113 |         return [text]
 114 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
 115 |     sentences = raw.split("\x00")
 116 |     chunks, current = [], ""
 117 |     for sent in sentences:
 118 |         if len(current) + len(sent) + 1 <= max_chars:
 119 |             current = f"{current} {sent}".strip() if current else sent
 120 |         else:
 121 |             if current:
 122 |                 chunks.append(current)
 123 |             current = sent
 124 |     if current:
 125 |         chunks.append(current)
 126 |     return [c for c in chunks if c.strip()]
 127 | 
 128 | 
 129 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 130 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback (quota exhausted)."""
 131 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 132 |     r = subprocess.run([
 133 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 134 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 135 |         output_path,
 136 |     ], capture_output=True, text=True, timeout=15)
 137 |     if r.returncode == 0 and os.path.exists(output_path):
 138 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 139 |         return True
 140 |     return False
 141 | 
 142 | 
 143 | def tts_elevenlabs(text: str, output_path: str, host: int = 1) -> bool:
 144 |     """Generate TTS audio for a single line using the specified host voice.
 145 | 
 146 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 147 |     """
 148 |     if not HAS_REQUESTS:
 149 |         return _tts_generate_silence_fallback(text, output_path)
 150 | 
 151 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 152 |     if not key:
 153 |         return _tts_generate_silence_fallback(text, output_path)
 154 | 
 155 |     voice = VOICES.get(host, VOICES[1])
 156 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 157 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 158 | 
 159 |     chunks = _chunk_text(text)
 160 |     chunk_files = []
 161 | 
 162 |     for ci, chunk in enumerate(chunks):
 163 |         # Extract speed (top-level ElevenLabs param) from voice_settings if present
 164 |         raw_settings = dict(voice["voice_settings"])
 165 |         speed_val = raw_settings.pop("speed", None)
 166 |         body = {
 167 |             "text": chunk,
 168 |             "model_id": voice["model_id"],
 169 |             "voice_settings": raw_settings,
 170 |         }
 171 |         if speed_val is not None:
 172 |             body["speed"] = speed_val
 173 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 174 |         success = False
 175 | 
 176 |         for attempt in range(3):
 177 |             try:
 178 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 179 |                 if r.status_code == 200:
 180 |                     with open(mp3_tmp, "wb") as f:
 181 |                         f.write(r.content)
 182 |                     success = True
 183 |                     break
 184 |                 elif r.status_code == 429:
 185 |                     wait = 2 ** attempt
 186 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 187 |                     time.sleep(wait)
 188 |                 else:
 189 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 190 |                     if attempt < 2:
 191 |                         time.sleep(2 ** attempt)
 192 |             except Exception as e:
 193 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 194 |                 if attempt < 2:
 195 |                     time.sleep(2 ** attempt)
 196 | 
 197 |         if not success:
 198 |             for f in chunk_files:
 199 |                 try:
 200 |                     os.remove(f)
 201 |                 except Exception:
 202 |                     pass
 203 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 204 |             print(f"  [tts] ElevenLabs failed — trying pyttsx3 fallback")
 205 |             try:
 206 |                 import pyttsx3
 207 |                 _engine = pyttsx3.init()
 208 |                 _engine.setProperty("rate", 150)
 209 |                 wav_tmp = output_path + ".pyttsx3.wav"
 210 |                 _engine.save_to_file(chunk, wav_tmp)
 211 |                 _engine.runAndWait()
 212 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 213 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 214 |                     try:
 215 |                         os.remove(wav_tmp)
 216 |                     except Exception:
 217 |                         pass
 218 |                     if ok:
 219 |                         return ok
 220 |             except Exception as pyttsx_err:
 221 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 222 |             return _tts_generate_silence_fallback(text, output_path)
 223 |         chunk_files.append(mp3_tmp)
 224 | 
 225 |     if len(chunk_files) == 1:
 226 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 227 |         try:
 228 |             os.remove(chunk_files[0])
 229 |         except Exception:
 230 |             pass
 231 |         return ok
 232 | 
 233 |     # Multi-chunk concat
 234 |     concat_list = output_path + ".concat.txt"
 235 |     mp3_combined = output_path + ".combined.mp3"
 236 |     with open(concat_list, "w") as f:
 237 |         for p in chunk_files:
 238 |             f.write(f"file '{os.path.abspath(p)}'\n")
 239 |     subprocess.run(
 240 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 241 |          "-c", "copy", mp3_combined],
 242 |         capture_output=True, text=True,
 243 |     )
 244 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 245 |     for f in chunk_files + [concat_list, mp3_combined]:
 246 |         try:
 247 |             if os.path.exists(f):
 248 |                 os.remove(f)
 249 |         except Exception:
 250 |             pass
 251 |     return ok
 252 | 
 253 | 
 254 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 255 |     """Generate audio for the entire dual-host dialogue.
 256 | 
 257 |     Args:
 258 |         dialogue: List of dicts with keys:
 259 |             - host: 1 or 2 (both route to Mark), or "CLIP" (silence placeholder)
 260 |             - text: The line text (or clip description for CLIP)
 261 |             - duration: (CLIP only) silence duration in seconds
 262 |             - source: (CLIP only) source channel name
 263 | 
 264 |     Returns:
 265 |         {
 266 |             "lines": [
 267 |                 {"path": str, "host": int|"CLIP", "duration": float,
 268 |                  "start": float, "text": str},
 269 |                 ...
 270 |             ],
 271 |             "full": str,          # path to concatenated audio
 272 |             "total_duration": float,
 273 |         }
 274 |     """
 275 |     os.makedirs(output_dir, exist_ok=True)
 276 | 
 277 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 278 |     if not key:
 279 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 280 | 
 281 |     silence_path = os.path.join(output_dir, "silence.m4a")
 282 |     _generate_silence(silence_path, SILENCE_GAP)
 283 | 
 284 |     lines = []
 285 |     parts_for_concat = []
 286 |     current_time = 0.0
 287 | 
 288 |     for i, entry in enumerate(dialogue):
 289 |         host = entry.get("host")
 290 |         text = entry.get("text", "")
 291 | 
 292 |         if host == "CLIP":
 293 |             clip_dur = entry.get("duration", 0)
 294 |             lines.append({
 295 |                 "path": None,
 296 |                 "host": "CLIP",
 297 |                 "duration": clip_dur,
 298 |                 "start": current_time,
 299 |                 "source": entry.get("source", ""),
 300 |                 "query": entry.get("query", ""),
 301 |                 "text": text,
 302 |             })
 303 |             continue
 304 | 
 305 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 306 |         voice = VOICES.get(host_num, VOICES[1])
 307 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 308 | 
 309 |         print(f"  [tts] Line {i:02d} ({voice['name']}): {text[:60]}...")
 310 | 
 311 |         if tts_elevenlabs(text, line_path, host_num):
 312 |             dur = ffprobe_duration(line_path)
 313 |             lines.append({
 314 |                 "path": line_path,
 315 |                 "host": host_num,
 316 |                 "duration": dur,
 317 |                 "start": current_time,
 318 |                 "text": text,
 319 |             })
 320 |             parts_for_concat.append(line_path)
 321 |             current_time += dur
 322 | 
 323 |             if i < len(dialogue) - 1:
 324 |                 parts_for_concat.append(silence_path)
 325 |                 current_time += SILENCE_GAP
 326 |         else:
 327 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": host_num,
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "text": text,
 334 |             })
 335 | 
 336 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 337 |     if parts_for_concat:
 338 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 339 |         with open(concat_file, "w") as f:
 340 |             for p in parts_for_concat:
 341 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 342 |         subprocess.run(
 343 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 344 |              "-c", "copy", full_path],
 345 |             capture_output=True, text=True,
 346 |         )
 347 |         if os.path.exists(concat_file):
 348 |             os.remove(concat_file)
 349 | 
 350 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 351 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 352 | 
 353 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 354 | 
 355 |     return {
 356 |         "lines": lines,
 357 |         "full": full_path if os.path.exists(full_path) else None,
 358 |         "total_duration": total_dur,
 359 |     }
 360 | 
 361 | 
 362 | if __name__ == "__main__":
 363 |     from script_writer import generate_script
 364 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 365 |     script = generate_script(style=style)
 366 |     audio_dir = os.path.join(BASE, "output", "audio_test")
 367 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 368 |     print(json.dumps(
 369 |         {k: v for k, v in result.items() if k != "lines"},
 370 |         indent=2,
 371 |     ))
 372 | 
```

### File: video_pipeline_v3/tts_engine.py (420 lines)
```
   1 | #!/usr/bin/env python3
   2 | """TTS Engine V6 — Single-host Mark broadcast voice.
   3 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) at 1.10x speed — PBX approved sole narrator.
   4 | Both host=1 and host=2 route to Mark (no gender swap, no dual-host).
   5 | Generates per-line audio with 0.3s silence gaps."""
   6 | import os, sys, json, subprocess, tempfile, time, struct
   7 | from pathlib import Path
   8 | 
   9 | try:
  10 |     import requests
  11 |     HAS_REQUESTS = True
  12 | except ImportError:
  13 |     HAS_REQUESTS = False
  14 | 
  15 | from relay import get_key
  16 | 
  17 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST — Mark at 1.10x speed.
  18 | # Both host=1 and host=2 map to Mark. Deborah/Brian/Nicole/Chris are all BANNED.
  19 | _MARK_VOICE = {
  20 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  21 |     "name": "Mark",
  22 |     "model_id": "eleven_turbo_v2_5",
  23 |     "speed": 1.10,
  24 |     "voice_settings": {
  25 |         "stability": 0.55,
  26 |         "similarity_boost": 0.80,
  27 |         "style": 0.15,
  28 |         "use_speaker_boost": True,
  29 |     },
  30 | }
  31 | 
  32 | VOICES = {
  33 |     1: _MARK_VOICE,
  34 |     2: _MARK_VOICE,  # single narrator — both hosts are Mark
  35 | }
  36 | 
  37 | # Voice mode overrides for Mark (segment-type tuning)
  38 | VOICE_MODES = {
  39 |     "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18, "speed": 1.10},
  40 |     "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  41 |     "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  42 |     "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18, "speed": 1.10},
  43 |     "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20, "speed": 1.08},
  44 |     "data":            {"stability": 0.60, "similarity_boost": 0.82, "style": 0.12, "speed": 1.10},
  45 | }
  46 | 
  47 | SILENCE_GAP = 0.3  # seconds between speakers
  48 | MAX_CHUNK_CHARS = 4900
  49 | 
  50 | _KEY_CACHE: dict = {}
  51 | 
  52 | 
  53 | def _get_cached_key(name: str) -> str:
  54 |     if name not in _KEY_CACHE:
  55 |         k = get_key(name)
  56 |         if k:
  57 |             _KEY_CACHE[name] = k.strip()
  58 |     return _KEY_CACHE.get(name, "")
  59 | 
  60 | 
  61 | def ffprobe_duration(path: str) -> float:
  62 |     r = subprocess.run(
  63 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  64 |          "-of", "csv=p=0", path],
  65 |         capture_output=True, text=True,
  66 |     )
  67 |     try:
  68 |         return float(r.stdout.strip())
  69 |     except Exception:
  70 |         return 0.0
  71 | 
  72 | 
  73 | def _generate_silence(output_path: str, duration: float) -> bool:
  74 |     """Generate a silent audio file."""
  75 |     r = subprocess.run(
  76 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  77 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  78 |          "-c:a", "aac", "-b:a", "192k", output_path],
  79 |         capture_output=True, text=True, timeout=30,
  80 |     )
  81 |     return r.returncode == 0 and os.path.exists(output_path)
  82 | 
  83 | 
  84 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
  85 |     r = subprocess.run(
  86 |         ["ffmpeg", "-y", "-i", mp3_path,
  87 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
  88 |         capture_output=True, text=True, timeout=120,
  89 |     )
  90 |     return r.returncode == 0 and os.path.exists(m4a_path)
  91 | 
  92 | 
  93 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
  94 |     if len(text) <= max_chars:
  95 |         return [text]
  96 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
  97 |     sentences = raw.split("\x00")
  98 |     chunks, current = [], ""
  99 |     for sent in sentences:
 100 |         if len(current) + len(sent) + 1 <= max_chars:
 101 |             current = f"{current} {sent}".strip() if current else sent
 102 |         else:
 103 |             if current:
 104 |                 chunks.append(current)
 105 |             current = sent
 106 |     if current:
 107 |         chunks.append(current)
 108 |     return [c for c in chunks if c.strip()]
 109 | 
 110 | 
 111 | TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
 112 | 
 113 | 
 114 | def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
 115 |     """SHA256 hash of text+voice+segment_type → stable cache key."""
 116 |     import hashlib
 117 |     payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
 118 |     return hashlib.sha256(payload).hexdigest()[:16]
 119 | 
 120 | 
 121 | def _tts_cache_get(cache_key: str, output_path: str) -> bool:
 122 |     """Check TTS cache and copy to output_path if hit. Returns True on hit."""
 123 |     import shutil
 124 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 125 |     if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000:
 126 |         shutil.copy2(cache_file, output_path)
 127 |         return True
 128 |     return False
 129 | 
 130 | 
 131 | def _tts_cache_put(cache_key: str, audio_path: str) -> None:
 132 |     """Save audio to TTS cache for future runs."""
 133 |     import shutil
 134 |     os.makedirs(TTS_CACHE_DIR, exist_ok=True)
 135 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 136 |     if not os.path.exists(cache_file):
 137 |         shutil.copy2(audio_path, cache_file)
 138 | 
 139 | 
 140 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 141 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback when ElevenLabs quota is exhausted.
 142 | 
 143 |     Estimates duration from text length (~12.5 chars/sec speech rate).
 144 |     Called when both ElevenLabs AND pyttsx3 fail.
 145 |     """
 146 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 147 |     r = subprocess.run([
 148 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 149 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 150 |         output_path,
 151 |     ], capture_output=True, text=True, timeout=15)
 152 |     if r.returncode == 0 and os.path.exists(output_path):
 153 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 154 |         return True
 155 |     return False
 156 | 
 157 | 
 158 | def tts_elevenlabs(text: str, output_path: str, host: int = 1,
 159 |                    segment_type: str = "") -> bool:
 160 |     """Generate TTS for a single line using the specified host voice.
 161 | 
 162 |     Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
 163 |     copies cached audio — no ElevenLabs API call. On miss, generates and caches.
 164 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 165 |     """
 166 |     if not HAS_REQUESTS:
 167 |         # No requests lib — try pyttsx3 or silence
 168 |         return _tts_generate_silence_fallback(text, output_path)
 169 | 
 170 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 171 |     if not key:
 172 |         return _tts_generate_silence_fallback(text, output_path)
 173 | 
 174 |     voice = VOICES.get(host, VOICES[1])
 175 |     # Check TTS cache first — avoid API call if same text+voice was generated before
 176 |     cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
 177 |     if _tts_cache_get(cache_key, output_path):
 178 |         print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
 179 |         return True
 180 | 
 181 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 182 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 183 | 
 184 |     # Apply hybrid voice mode for Mark based on segment type
 185 |     voice_settings = dict(voice["voice_settings"])
 186 |     if host == 1 and segment_type in VOICE_MODES:
 187 |         mode = VOICE_MODES[segment_type]
 188 |         for k, v in mode.items():
 189 |             if k != "speed":
 190 |                 voice_settings[k] = v
 191 | 
 192 |     chunks = _chunk_text(text)
 193 |     chunk_files = []
 194 | 
 195 |     for ci, chunk in enumerate(chunks):
 196 |         body = {
 197 |             "text": chunk,
 198 |             "model_id": voice["model_id"],
 199 |             "voice_settings": voice_settings,
 200 |         }
 201 |         # Add speed parameter — use mode-specific speed for Host 1
 202 |         speed = voice.get("speed", 1.0)
 203 |         if host == 1 and segment_type in VOICE_MODES:
 204 |             speed = VOICE_MODES[segment_type].get("speed", speed)
 205 |         if speed != 1.0:
 206 |             body["speed"] = speed
 207 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 208 |         success = False
 209 | 
 210 |         for attempt in range(3):
 211 |             try:
 212 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 213 |                 if r.status_code == 200:
 214 |                     with open(mp3_tmp, "wb") as f:
 215 |                         f.write(r.content)
 216 |                     success = True
 217 |                     break
 218 |                 elif r.status_code == 429:
 219 |                     wait = 2 ** attempt
 220 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 221 |                     time.sleep(wait)
 222 |                 else:
 223 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 224 |                     if attempt < 2:
 225 |                         time.sleep(2 ** attempt)
 226 |             except Exception as e:
 227 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 228 |                 if attempt < 2:
 229 |                     time.sleep(2 ** attempt)
 230 | 
 231 |         if not success:
 232 |             for f in chunk_files:
 233 |                 try:
 234 |                     os.remove(f)
 235 |                 except Exception:
 236 |                     pass
 237 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 238 |             print(f"  [tts] ElevenLabs failed for chunk {ci} — trying pyttsx3 fallback")
 239 |             try:
 240 |                 import pyttsx3
 241 |                 _engine = pyttsx3.init()
 242 |                 _engine.setProperty("rate", 150)
 243 |                 wav_tmp = output_path + f".pyttsx3.wav"
 244 |                 _engine.save_to_file(chunk, wav_tmp)
 245 |                 _engine.runAndWait()
 246 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 247 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 248 |                     try:
 249 |                         os.remove(wav_tmp)
 250 |                     except Exception:
 251 |                         pass
 252 |                     if ok:
 253 |                         print(f"  [tts] pyttsx3 fallback SUCCESS for chunk {ci}")
 254 |                         return ok
 255 |             except Exception as pyttsx_err:
 256 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 257 |             # Final fallback: generate silence so the segment still renders
 258 |             return _tts_generate_silence_fallback(text, output_path)
 259 |         chunk_files.append(mp3_tmp)
 260 | 
 261 |     # Single chunk
 262 |     if len(chunk_files) == 1:
 263 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 264 |         try:
 265 |             os.remove(chunk_files[0])
 266 |         except Exception:
 267 |             pass
 268 |         if ok and os.path.exists(output_path):
 269 |             _tts_cache_put(cache_key, output_path)
 270 |         return ok
 271 | 
 272 |     # Multi-chunk concat
 273 |     concat_list = output_path + ".concat.txt"
 274 |     mp3_combined = output_path + ".combined.mp3"
 275 |     with open(concat_list, "w") as f:
 276 |         for p in chunk_files:
 277 |             f.write(f"file '{os.path.abspath(p)}'\n")
 278 |     subprocess.run(
 279 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 280 |          "-c", "copy", mp3_combined],
 281 |         capture_output=True, text=True,
 282 |     )
 283 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 284 |     for f in chunk_files + [concat_list, mp3_combined]:
 285 |         try:
 286 |             if os.path.exists(f):
 287 |                 os.remove(f)
 288 |         except Exception:
 289 |             pass
 290 |     if ok and os.path.exists(output_path):
 291 |         _tts_cache_put(cache_key, output_path)
 292 |     return ok
 293 | 
 294 | 
 295 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 296 |     """Generate audio for the entire dual-host dialogue.
 297 | 
 298 |     Args:
 299 |         dialogue: List of {host: 1|2|"CLIP", text: "..."}
 300 |         output_dir: Directory for audio files
 301 | 
 302 |     Returns:
 303 |         {
 304 |             "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
 305 |             "full": str,  # path to concatenated full audio
 306 |             "total_duration": float,
 307 |         }
 308 |     """
 309 |     os.makedirs(output_dir, exist_ok=True)
 310 | 
 311 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 312 |     if not key:
 313 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 314 | 
 315 |     silence_path = os.path.join(output_dir, "silence.m4a")
 316 |     _generate_silence(silence_path, SILENCE_GAP)
 317 | 
 318 |     lines = []
 319 |     parts_for_concat = []
 320 |     current_time = 0.0
 321 | 
 322 |     for i, entry in enumerate(dialogue):
 323 |         host = entry.get("host")
 324 |         text = entry.get("text", "")
 325 | 
 326 |         # Skip CLIP markers — they don't have audio
 327 |         if host == "CLIP":
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": "CLIP",
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "source": entry.get("source", ""),
 334 |                 "query": entry.get("query", ""),
 335 |                 "text": text,
 336 |             })
 337 |             continue
 338 | 
 339 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 340 |         voice = VOICES.get(host_num, VOICES[1])
 341 |         segment_type = entry.get("type", "")
 342 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 343 | 
 344 |         mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
 345 |         print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")
 346 | 
 347 |         if tts_elevenlabs(text, line_path, host_num, segment_type=segment_type):
 348 |             dur = ffprobe_duration(line_path)
 349 |             lines.append({
 350 |                 "path": line_path,
 351 |                 "host": host_num,
 352 |                 "duration": dur,
 353 |                 "start": current_time,
 354 |                 "text": text,
 355 |             })
 356 |             parts_for_concat.append(line_path)
 357 |             current_time += dur
 358 | 
 359 |             # Add silence gap between speakers (not after last line)
 360 |             if i < len(dialogue) - 1:
 361 |                 parts_for_concat.append(silence_path)
 362 |                 current_time += SILENCE_GAP
 363 |         else:
 364 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 365 |             lines.append({
 366 |                 "path": None,
 367 |                 "host": host_num,
 368 |                 "duration": 0.0,
 369 |                 "start": current_time,
 370 |                 "text": text,
 371 |             })
 372 | 
 373 |     # Concatenate all lines into full audio
 374 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 375 |     if parts_for_concat:
 376 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 377 |         with open(concat_file, "w") as f:
 378 |             for p in parts_for_concat:
 379 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 380 |         subprocess.run(
 381 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 382 |              "-c", "copy", full_path],
 383 |             capture_output=True, text=True,
 384 |         )
 385 |         if os.path.exists(concat_file):
 386 |             os.remove(concat_file)
 387 | 
 388 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 389 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 390 | 
 391 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 392 | 
 393 |     return {
 394 |         "lines": lines,
 395 |         "full": full_path if os.path.exists(full_path) else None,
 396 |         "total_duration": total_dur,
 397 |     }
 398 | 
 399 | 
 400 | # Legacy compatibility — V3 pipeline used generate_all_audio
 401 | def generate_all_audio(script: dict, output_dir: str) -> dict:
 402 |     """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
 403 |     if "dialogue" in script:
 404 |         return generate_dialogue_audio(script["dialogue"], output_dir)
 405 |     # V3 fallback
 406 |     raise RuntimeError("V4 pipeline requires dialogue-format script")
 407 | 
 408 | 
 409 | if __name__ == "__main__":
 410 |     from script_writer import generate_script
 411 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 412 |     script = generate_script(style=style)
 413 |     base = os.path.dirname(os.path.abspath(__file__))
 414 |     audio_dir = os.path.join(base, "output", "audio_test")
 415 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 416 |     print(json.dumps(
 417 |         {k: v for k, v in result.items() if k != "lines"},
 418 |         indent=2,
 419 |     ))
 420 | 
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
