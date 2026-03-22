# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: oracle-stage
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REVIEW: ORACLE-STAGE FEATURE

Below is a detailed forensic review of the provided code for the `oracle-stage` feature of Protocol Pulse. I have analyzed the code with a focus on correctness, compliance, security, quality, and alignment with world-class standards. My feedback is direct and prioritizes quality over all else, citing specific line numbers for clarity.

---

### SECTION 1: CORRECTNESS

**Main User Flow Analysis:**
1. **Loading the Stage Page (templates/stage.html):**
   - The page loads with a ticker, avatar, sentiment data, transcripts, and Nostr posts. Initial data is fetched via `loadIntel()`, `loadTranscripts()`, and `loadNostr()` (lines 954-956). This works as intended for the happy path.
   - **Issue:** Silent failures in data fetching. If `/api/oracle/ask` fails (line 690), a fallback to `/health` is attempted (line 732), but no user feedback is provided if both fail. Users see "Loading…" indefinitely (e.g., line 474).
   - **Issue:** Ticker duplication for seamless scrolling (lines 494-512) assumes content length, but if API responses are empty or malformed, the animation breaks without fallback (line 78).

2. **Avatar Playback (requestBrief() and requestGreet()):**
   - Clicking "Daily Brief" or "Greet" triggers video playback from an external service (lines 917-933, 938-946). The logic handles playback and status updates correctly.
   - **Issue:** No cleanup of old `objURL` if multiple videos are requested quickly. `URL.revokeObjectURL()` is called (line 881), but `objURL` isn’t cleared if a new request starts before the old one ends, risking memory leaks.
   - **Issue:** Race condition in `setBusy()` (line 869). If two users click buttons simultaneously, `busy` state isn’t atomic, potentially allowing overlapping requests.

3. **Transcript Reader (openReader() and closeReader()):**
   - Clicking "Read Brief" on a transcript card opens a modal with full text (lines 846-857). This works as expected.
   - **Issue:** No sanitization of `dataset` content beyond basic escaping (line 808). If API data includes malicious HTML, it could render in the modal (line 850).

4. **API Endpoints (routes.py):**
   - `/api/stage/transcripts` (line 10803) fetches channel data from files. It handles empty or malformed files with basic error catching (line 10826).
   - **Issue:** No pagination or limit enforcement. If `results` grows large (line 10845), response size could overwhelm clients or server memory.
   - **Issue:** N+1-like problem in file reading (lines 10829-10844). Each directory and file is read sequentially without batching, risking performance issues with many channels.

**Edge Cases:**
- **Empty DB or API Failure:** No fallback UI for when all APIs fail (e.g., line 781). Users see skeleton loaders or "Loading…" forever.
- **API Timeout:** `fetchTO()` implements a timeout (line 908), but fallback behavior is minimal (line 929), often just logging an error without user notification.
- **Bad Input:** Transcript data isn’t validated for length or format (line 10821). Very long strings could break UI rendering or cause memory issues.

---

### SECTION 2: LAW COMPLIANCE

Since no specific "Governing Laws" were provided in the spec under the "GOVERNING LAWS" section (it’s empty), I’ll assume compliance with general best practices and the technology stack requirements mentioned. If specific laws were intended, they should be explicitly listed for evaluation.

- **Technology Stack Compliance (Python 3.12, Flask 3.x, SQLite via SQLAlchemy, etc.):** COMPLIANT
  - The code uses Flask and SQLAlchemy as required (e.g., line 9806 in `routes.py` for ORM queries).
- **UI Animations (CSS/SVG only, no Three.js/WebGL/Canvas):** COMPLIANT
  - All animations are CSS-based (e.g., lines 61-64, 78-80 in `stage.html`).
- **Concurrent Users (~1000 at peak, every route must handle load):** PARTIAL
  - No explicit rate limiting or caching on API routes (e.g., line 10803). Under high load, file I/O (line 10829) and external API calls (line 917) could bottleneck.
- **DB Query Indexing (every sort/filter column must have an index):** PARTIAL
  - `OracleSession.query.order_by()` (line 9807) sorts by `created_at`, but no evidence of an index is provided in the code snippet. Without an index, this query scales poorly with data size.

---

### SECTION 3: SECURITY

- **SQL Injection:** LOW RISK
  - No raw SQL queries are present; SQLAlchemy ORM is used (line 9806), which mitigates injection risks by default. However, without seeing the full schema or query construction, I can’t confirm if dynamic filters are safe.
- **Authentication Bypasses:** HIGH RISK
  - None of the API routes (`/api/stage/transcripts`, `/api/oracle/recent`, etc.) check for authentication (e.g., line 10803, 9801). If these endpoints expose sensitive data, they’re accessible to anyone, violating basic security principles.
- **Rate Limiting Gaps:** HIGH RISK
  - No rate limiting on any endpoint or client-side action (e.g., `requestBrief()` at 

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — ORACLE-STAGE — CYCLE 1
Generated: 2026-03-17 01:57
Models: grok (+2 failed — Gemini 403 PERMISSION_DENIED leaked key; GPT-4o 429 quota exhausted)

---

## SCORES

> **Note:** Only Grok-3 produced output. Gemini and GPT-4o failed at the API level before generating reviews. Scores are derived solely from Grok's assessment. Consensus column reflects single-model confidence, not triangulated agreement. All findings below carry **reduced confidence** and should be treated as a single expert review, not a true multi-model consensus. Cycle 2 should retry with repaired API credentials before treating any "Unanimous" findings as fully validated.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | — | — | 5.5 / 10 | 5.5 / 10 ⚠️ |
| Law Compliance | — | — | 6.0 / 10 | 6.0 / 10 ⚠️ |
| Security | — | — | 4.5 / 10 | 4.5 / 10 ⚠️ |
| Frontend Quality | — | — | 6.0 / 10 | 6.0 / 10 ⚠️ |
| Backend Quality | — | — | 5.5 / 10 | 5.5 / 10 ⚠️ |
| **Overall** | — | — | **5.5 / 10** | **5.5 / 10** |

*Scores inferred from Grok's severity language ("HIGH RISK", "MODERATE", "PARTIAL", "COMPLIANT") mapped to numeric values. ⚠️ = single-model only.*

---

## UNANIMOUS FINDINGS (all 1 models agree — implement unconditionally)

With only one model available, "unanimous" means Grok flagged these with HIGH RISK or as structural violations. They represent the highest-confidence issues from the available review and should be treated as mandatory.

---

**U1 — No Authentication on API Routes**
- **What:** `/api/stage/transcripts`, `/api/oracle/recent`, and related endpoints have zero authentication checks. Any unauthenticated actor can query them.
- **File/Line:** `routes.py` lines ~10803, ~9801
- **Change:** Add `@login_required` decorator (or equivalent session/token check) to every route that returns oracle, transcript, or session data. If public access is intentional, document it explicitly in the gospel and add read-only rate limiting regardless.

---

**U2 — No Rate Limiting on Any Endpoint or Client Action**
- **What:** `requestBrief()` and `requestGreet()` on the frontend, plus all backend API routes, have no rate limiting. A single client can spam external `avatar.protocolpulse.io` calls, exhausting paid API quotas and potentially DOSing the service.
- **File/Line:** `stage.html` line ~915 (client); `routes.py` lines ~10803, ~9801 (server)
- **Change:** Implement Flask-Limiter on all `/api/oracle/*` and `/api/stage/*` routes (e.g., `@limiter.limit("10/minute")`). On the client, enforce a cooldown lock on avatar request buttons — `setBusy()` exists but is insufficient alone.

---

**U3 — Silent Failures / No Error State UI**
- **What:** When `/api/oracle/ask` fails and the `/health` fallback also fails, users see "Loading…" indefinitely. Error states are logged to console but never surfaced in the UI.
- **File/Line:** `stage.html` lines ~690 (primary fetch), ~732 (fallback), ~474 (loading text), ~929 (error log)
- **

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: templates/stage.html (966 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Oracle Stage — Protocol Pulse Live{% endblock %}
   4 | {% block meta_description %}Bitcoin intelligence. Live. Oracle reports in real time on price, on-chain signals, partner channel transcripts, and Nostr discourse.{% endblock %}
   5 | 
   6 | {% block head %}
   7 | <style>
   8 | /* ══════════════════════════════════════════════════════
   9 |    ORACLE STAGE — Broadcast Desk Layout
  10 |    Aesthetic: News control room meets Bitcoin terminal.
  11 |    Obsidian base, signal-red accents, gold data rails,
  12 |    Syne Mono headlines for that teletype authority.
  13 |    ══════════════════════════════════════════════════════ */
  14 | @import url('https://fonts.googleapis.com/css2?family=Syne+Mono&family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  15 | 
  16 | :root {
  17 |   --s-bg:        #04050a;
  18 |   --s-surface:   #080b12;
  19 |   --s-border:    rgba(255,59,95,.18);
  20 |   --s-red:       #ff3b5f;
  21 |   --s-gold:      #f8c15c;
  22 |   --s-green:     #2eff8a;
  23 |   --s-muted:     rgba(255,255,255,.28);
  24 |   --s-mono:      'Syne Mono', 'JetBrains Mono', monospace;
  25 |   --s-head:      'Syne', sans-serif;
  26 | }
  27 | 
  28 | /* Page shell */
  29 | body { background: var(--s-bg); }
  30 | .stage-wrap {
  31 |   min-height: 100vh;
  32 |   background: var(--s-bg);
  33 |   background-image:
  34 |     radial-gradient(ellipse 60% 40% at 20% 10%, rgba(255,59,95,.07) 0%, transparent 60%),
  35 |     radial-gradient(ellipse 50% 35% at 80% 80%, rgba(248,193,92,.04) 0%, transparent 60%),
  36 |     repeating-linear-gradient(0deg,   rgba(255,59,95,.025) 0px, transparent 1px, transparent 39px, rgba(255,59,95,.025) 40px),
  37 |     repeating-linear-gradient(90deg,  rgba(255,59,95,.025) 0px, transparent 1px, transparent 39px, rgba(255,59,95,.025) 40px);
  38 |   padding: 0 0 60px;
  39 | }
  40 | 
  41 | /* ── TOP STATUS BAR ─────────────────────────────────── */
  42 | .stage-topbar {
  43 |   position: sticky; top: 0; z-index: 200;
  44 |   background: rgba(4,5,10,.92);
  45 |   backdrop-filter: blur(16px);
  46 |   border-bottom: 1px solid var(--s-border);
  47 |   display: flex; align-items: center; gap: 0;
  48 |   height: 42px; overflow: hidden;
  49 | }
  50 | .stage-topbar__live {
  51 |   display: flex; align-items: center; gap: 8px;
  52 |   padding: 0 20px; border-right: 1px solid var(--s-border);
  53 |   flex-shrink: 0;
  54 | }
  55 | .stage-topbar__dot {
  56 |   width: 8px; height: 8px; border-radius: 50%;
  57 |   background: var(--s-red);
  58 |   box-shadow: 0 0 6px var(--s-red);
  59 |   animation: live-pulse 1.4s ease-in-out infinite;
  60 | }
  61 | @keyframes live-pulse {
  62 |   0%,100% { opacity:1; box-shadow: 0 0 6px var(--s-red); }
  63 |   50%      { opacity:.5; box-shadow: 0 0 14px var(--s-red); }
  64 | }
  65 | .stage-topbar__label {
  66 |   font-family: var(--s-mono); font-size: 11px; letter-spacing:.18em;
  67 |   color: var(--s-red); text-transform: uppercase;
  68 | }
  69 | .stage-topbar__ticker {
  70 |   flex: 1; overflow: hidden; display: flex; align-items: center;
  71 |   padding: 0 16px;
  72 | }
  73 | .stage-topbar__ticker-inner {
  74 |   display: flex; gap: 40px; white-space: nowrap;
  75 |   animation: ticker-scroll 40s linear infinite;
  76 | }
  77 | .stage-topbar__ticker-inner:hover { animation-play-state: paused; }
  78 | @keyframes ticker-scroll {
  79 |   0%   { transform: translateX(0); }
  80 |   100% { transform: translateX(-50%); }
  81 | }
  82 | .ticker-item {
  83 |   font-family: var(--s-mono); font-size: 11px;
  84 |   color: rgba(255,255,255,.5); letter-spacing: .06em;
  85 | }
  86 | .ticker-item .ti-label { color: var(--s-muted); margin-right: 6px; }
  87 | .ticker-item .ti-val   { color: rgba(255,255,255,.85); }
  88 | .ticker-item .ti-up    { color: var(--s-green); }
  89 | .ticker-item .ti-down  { color: var(--s-red); }
  90 | .ticker-item .ti-sep   { color: var(--s-border); margin: 0 8px; }
  91 | .stage-topbar__time {
  92 |   font-family: var(--s-mono); font-size: 11px;
  93 |   color: var(--s-gold); letter-spacing: .1em;
  94 |   padding: 0 20px; border-left: 1px solid var(--s-border);
  95 |   flex-shrink: 0;
  96 | }
  97 | 
  98 | /* ── PAGE HEADER ──────────────────────────────────────  */
  99 | .stage-header {
 100 |   display: flex; align-items: center; justify-content: space-between;
 101 |   padding: 28px 32px 20px;
 102 |   border-bottom: 1px solid var(--s-border);
 103 | }
 104 | .stage-header__title {
 105 |   font-family: var(--s-head); font-size: 11px; font-weight: 700;
 106 |   letter-spacing: .3em; text-transform: uppercase;
 107 |   color: var(--s-red);
 108 | }
 109 | .stage-header__sub {
 110 |   font-family: var(--s-mono); font-size: 10px;
 111 |   color: rgba(255,255,255,.3); letter-spacing: .12em;
 112 |   margin-top: 3px;
 113 | }
 114 | .stage-header__right {
 115 |   display: flex; align-items: center; gap: 12px;
 116 | }
 117 | .stage-badge {
 118 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 119 |   padding: 4px 10px; border-radius: 3px;
 120 |   text-transform: uppercase;
 121 | }
 122 | .stage-badge--on  { background: rgba(255,59,95,.12); color: var(--s-red); border: 1px solid rgba(255,59,95,.3); }
 123 | .stage-badge--ok  { background: rgba(46,255,138,.08); color: var(--s-green); border: 1px solid rgba(46,255,138,.2); }
 124 | 
 125 | /* ── MAIN GRID ──────────────────────────────────────── */
 126 | .stage-grid {
 127 |   display: grid;
 128 |   grid-template-columns: 1fr 340px;
 129 |   grid-template-rows: auto;
 130 |   gap: 0;
 131 |   min-height: calc(100vh - 140px);
 132 | }
 133 | @media (max-width: 900px) {
 134 |   .stage-grid { grid-template-columns: 1fr; }
 135 |   .stage-sidebar { border-left: none; border-top: 1px solid var(--s-border); }
 136 | }
 137 | 
 138 | /* ── MAIN CONTENT (left) ────────────────────────────── */
 139 | .stage-main {
 140 |   padding: 24px 32px;
 141 |   border-right: 1px solid var(--s-border);
 142 |   display: flex; flex-direction: column; gap: 28px;
 143 | }
 144 | 
 145 | /* ── AVATAR DESK ─────────────────────────────────────── */
 146 | .stage-desk {
 147 |   display: grid;
 148 |   grid-template-columns: 280px 1fr;
 149 |   gap: 24px;
 150 |   align-items: start;
 151 | }
 152 | @media (max-width: 700px) {
 153 |   .stage-desk { grid-template-columns: 1fr; }
 154 | }
 155 | .stage-avatar-wrap {
 156 |   position: relative;
 157 |   background: radial-gradient(circle at 50% 100%, rgba(255,59,95,.08) 0%, transparent 60%),
 158 |               #06080f;
 159 |   border: 1px solid var(--s-border);
 160 |   border-radius: 8px;
 161 |   overflow: hidden;
 162 |   aspect-ratio: 3/4;
 163 |   display: flex; align-items: flex-end; justify-content: center;
 164 | }
 165 | .stage-avatar-wrap::before {
 166 |   content: '';
 167 |   position: absolute; inset: 0;
 168 |   background: linear-gradient(to top, rgba(4,5,10,.8) 0%, transparent 40%);
 169 |   z-index: 2; pointer-events: none;
 170 | }
 171 | /* Desk surface */
 172 | .stage-avatar-wrap::after {
 173 |   content: '';
 174 |   position: absolute; bottom: 0; left: 0; right: 0; height: 28%;
 175 |   background: linear-gradient(to top, #0d1017 0%, rgba(13,16,23,.5) 70%, transparent 100%);
 176 |   z-index: 3; pointer-events: none;
 177 | }
 178 | .stage-avatar-img {
 179 |   position: absolute; inset: 0; width: 100%; height: 100%;
 180 |   object-fit: cover; object-position: center top;
 181 |   filter: brightness(.9) contrast(1.08);
 182 | }
 183 | .stage-avatar-vid {
 184 |   position: absolute; inset: 0; width: 100%; height: 100%;
 185 |   object-fit: cover; object-position: center top;
 186 |   display: none; z-index: 1;
 187 | }
 188 | .stage-avatar-vid.active { display: block; }
 189 | .stage-avatar-nameplate {
 190 |   position: absolute; bottom: 12px; left: 12px; z-index: 10;
 191 |   display: flex; align-items: center; gap: 8px;
 192 | }
 193 | .stage-avatar-nameplate__dot {
 194 |   width: 6px; height: 6px; border-radius: 50%;
 195 |   background: var(--s-red); box-shadow: 0 0 5px var(--s-red);
 196 |   animation: live-pulse 1.4s ease-in-out infinite;
 197 | }
 198 | .stage-avatar-nameplate__name {
 199 |   font-family: var(--s-mono); font-size: 11px; letter-spacing: .14em;
 200 |   color: rgba(255,255,255,.9); text-transform: uppercase;
 201 | }
 202 | 
 203 | /* ── BRIEF PANEL (right of avatar) ─────────────────── */
 204 | .stage-brief {
 205 |   display: flex; flex-direction: column; gap: 16px;
 206 | }
 207 | .stage-brief__section-label {
 208 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .22em;
 209 |   text-transform: uppercase; color: var(--s-muted);
 210 |   margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
 211 | }
 212 | .stage-brief__section-label::after {
 213 |   content: ''; flex: 1; height: 1px;
 214 |   background: linear-gradient(to right, var(--s-border), transparent);
 215 | }
 216 | .stage-brief__sentiment {
 217 |   display: flex; align-items: center; gap: 12px;
 218 |   padding: 14px 16px;
 219 |   background: var(--s-surface); border: 1px solid var(--s-border);
 220 |   border-radius: 6px;
 221 | }
 222 | .stage-brief__sentiment-bar-wrap {
 223 |   flex: 1; height: 4px; background: rgba(255,255,255,.08);
 224 |   border-radius: 2px; overflow: hidden;
 225 | }
 226 | .stage-brief__sentiment-bar {
 227 |   height: 100%; border-radius: 2px;
 228 |   background: linear-gradient(to right, var(--s-red), var(--s-gold), var(--s-green));
 229 |   transition: width .6s ease;
 230 | }
 231 | .stage-brief__sentiment-score {
 232 |   font-family: var(--s-mono); font-size: 22px; font-weight: 600;
 233 |   line-height: 1; color: #fff; min-width: 36px; text-align: right;
 234 | }
 235 | .stage-brief__sentiment-label {
 236 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .12em;
 237 |   text-transform: uppercase; margin-top: 2px;
 238 | }
 239 | 
 240 | /* Narrative card */
 241 | .stage-narrative {
 242 |   padding: 14px 16px;
 243 |   background: var(--s-surface); border: 1px solid var(--s-border);
 244 |   border-left: 3px solid var(--s-red); border-radius: 6px;
 245 |   font-family: var(--s-head); font-size: 14px; font-weight: 500;
 246 |   line-height: 1.5; color: rgba(255,255,255,.82);
 247 |   position: relative;
 248 | }
 249 | .stage-narrative::before {
 250 |   content: 'ORACLE NARRATIVE';
 251 |   font-family: var(--s-mono); font-size: 8px; letter-spacing: .22em;
 252 |   color: var(--s-red); display: block; margin-bottom: 6px;
 253 | }
 254 | 
 255 | /* Topics */
 256 | .stage-topics {
 257 |   display: flex; flex-wrap: wrap; gap: 6px;
 258 | }
 259 | .stage-topic {
 260 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 261 |   padding: 4px 10px; border-radius: 3px;
 262 |   text-transform: uppercase; border: 1px solid;
 263 | }
 264 | .stage-topic--bull  { background: rgba(46,255,138,.07);  color: var(--s-green); border-color: rgba(46,255,138,.2); }
 265 | .stage-topic--bear  { background: rgba(255,59,95,.07);   color: var(--s-red);   border-color: rgba(255,59,95,.2);  }
 266 | .stage-topic--neut  { background: rgba(248,193,92,.07);  color: var(--s-gold);  border-color: rgba(248,193,92,.2); }
 267 | 
 268 | /* Playback controls */
 269 | .stage-controls {
 270 |   display: flex; gap: 8px; align-items: center;
 271 | }
 272 | .stage-btn {
 273 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .12em;
 274 |   text-transform: uppercase; padding: 8px 16px;
 275 |   border-radius: 4px; cursor: pointer; border: 1px solid;
 276 |   transition: all .15s; flex-shrink: 0;
 277 | }
 278 | .stage-btn--primary {
 279 |   background: var(--s-red); color: #fff; border-color: var(--s-red);
 280 | }
 281 | .stage-btn--primary:hover { background: #ff1a40; }
 282 | .stage-btn--ghost {
 283 |   background: transparent; color: rgba(255,255,255,.6); border-color: var(--s-border);
 284 | }
 285 | .stage-btn--ghost:hover { border-color: rgba(255,255,255,.3); color: #fff; }
 286 | .stage-btn:disabled { opacity: .35; cursor: not-allowed; }
 287 | .stage-status {
 288 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 289 |   color: var(--s-muted); flex: 1; text-align: right;
 290 | }
 291 | .stage-status.speaking { color: var(--s-green); }
 292 | 
 293 | /* ── CHANNEL TRANSCRIPTS ─────────────────────────────  */
 294 | .stage-transcripts {
 295 |   display: grid;
 296 |   grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
 297 |   gap: 12px;
 298 | }
 299 | .stage-tx-card {
 300 |   background: var(--s-surface);
 301 |   border: 1px solid var(--s-border);
 302 |   border-radius: 6px;
 303 |   padding: 14px 16px;
 304 |   transition: border-color .15s, transform .15s;
 305 |   cursor: default;
 306 | }
 307 | .stage-tx-card:hover {
 308 |   border-color: rgba(255,59,95,.35);
 309 |   transform: translateY(-1px);
 310 | }
 311 | .stage-tx-card__channel {
 312 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .18em;
 313 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 5px;
 314 | }
 315 | .stage-tx-card__title {
 316 |   font-family: var(--s-head); font-size: 13px; font-weight: 600;
 317 |   color: rgba(255,255,255,.9); line-height: 1.35; margin-bottom: 8px;
 318 | }
 319 | .stage-tx-card__excerpt {
 320 |   font-family: var(--s-head); font-size: 12px; font-weight: 400;
 321 |   color: rgba(255,255,255,.42); line-height: 1.5;
 322 | }
 323 | .stage-tx-card__footer {
 324 |   margin-top: 10px; padding-top: 8px;
 325 |   border-top: 1px solid rgba(255,255,255,.05);
 326 |   display: flex; justify-content: space-between; align-items: center;
 327 | }
 328 | .stage-tx-card__read-btn {
 329 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 330 |   text-transform: uppercase; color: var(--s-gold);
 331 |   background: none; border: none; cursor: pointer; padding: 0;
 332 |   transition: color .1s;
 333 | }
 334 | .stage-tx-card__read-btn:hover { color: #fff; }
 335 | .stage-tx-card__sentiment {
 336 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .08em;
 337 |   text-transform: uppercase;
 338 | }
 339 | 
 340 | /* ── SIDEBAR (right) ─────────────────────────────────  */
 341 | .stage-sidebar {
 342 |   border-left: 1px solid var(--s-border);
 343 |   display: flex; flex-direction: column;
 344 |   height: fit-content; position: sticky; top: 42px;
 345 |   max-height: calc(100vh - 42px); overflow: hidden;
 346 | }
 347 | .stage-panel {
 348 |   border-bottom: 1px solid var(--s-border);
 349 |   flex-shrink: 0;
 350 | }
 351 | .stage-panel__header {
 352 |   padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;
 353 |   background: rgba(8,11,18,.7);
 354 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 355 |   text-transform: uppercase; color: rgba(255,255,255,.4);
 356 | }
 357 | .stage-panel__header-dot {
 358 |   width: 5px; height: 5px; border-radius: 50%;
 359 |   margin-right: 7px; display: inline-block; vertical-align: middle;
 360 | }
 361 | .stage-panel__body { padding: 12px 16px; }
 362 | 
 363 | /* Price panel */
 364 | .stage-price-big {
 365 |   font-family: var(--s-head); font-size: 36px; font-weight: 800;
 366 |   color: #fff; line-height: 1; letter-spacing: -.02em;
 367 | }
 368 | .stage-price-label {
 369 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 370 |   color: var(--s-muted); margin-top: 4px; text-transform: uppercase;
 371 | }
 372 | .stage-price-change {
 373 |   font-family: var(--s-mono); font-size: 12px;
 374 |   margin-top: 8px;
 375 | }
 376 | 
 377 | /* Nostr feed */
 378 | .stage-signal-feed {
 379 |   overflow-y: auto;
 380 |   max-height: 380px;
 381 |   scrollbar-width: thin;
 382 |   scrollbar-color: rgba(255,59,95,.2) transparent;
 383 | }
 384 | .stage-signal-item {
 385 |   padding: 10px 0;
 386 |   border-bottom: 1px solid rgba(255,255,255,.04);
 387 | }
 388 | .stage-signal-item:last-child { border-bottom: none; }
 389 | .stage-signal-item__author {
 390 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 391 |   color: var(--s-gold); margin-bottom: 4px;
 392 |   white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
 393 | }
 394 | .stage-signal-item__text {
 395 |   font-family: var(--s-head); font-size: 12px;
 396 |   color: rgba(255,255,255,.6); line-height: 1.45;
 397 |   display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
 398 |   overflow: hidden;
 399 | }
 400 | 
 401 | /* Transcript reader overlay */
 402 | .stage-reader {
 403 |   display: none; position: fixed; inset: 0;
 404 |   z-index: 500; background: rgba(4,5,10,.95);
 405 |   backdrop-filter: blur(8px);
 406 |   overflow-y: auto;
 407 |   padding: 40px 24px;
 408 | }
 409 | .stage-reader.open { display: block; }
 410 | .stage-reader__inner {
 411 |   max-width: 680px; margin: 0 auto;
 412 |   background: var(--s-surface); border: 1px solid var(--s-border);
 413 |   border-radius: 8px; padding: 32px;
 414 | }
 415 | .stage-reader__close {
 416 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .14em;
 417 |   text-transform: uppercase; color: var(--s-muted);
 418 |   background: none; border: none; cursor: pointer;
 419 |   margin-bottom: 20px; display: flex; align-items: center; gap: 6px;
 420 |   transition: color .1s;
 421 | }
 422 | .stage-reader__close:hover { color: #fff; }
 423 | .stage-reader__channel {
 424 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 425 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 8px;
 426 | }
 427 | .stage-reader__title {
 428 |   font-family: var(--s-head); font-size: 22px; font-weight: 700;
 429 |   color: #fff; line-height: 1.3; margin-bottom: 16px;
 430 | }
 431 | .stage-reader__body {
 432 |   font-family: var(--s-head); font-size: 14px; font-weight: 400;
 433 |   color: rgba(255,255,255,.68); line-height: 1.7;
 434 |   white-space: pre-wrap; word-break: break-word;
 435 | }
 436 | 
 437 | /* Animations */
 438 | @keyframes fadeUp {
 439 |   from { opacity:0; transform:translateY(12px); }
 440 |   to   { opacity:1; transform:translateY(0); }
 441 | }
 442 | .stage-desk     { animation: fadeUp .5s ease both; }
 443 | .stage-tx-card  { animation: fadeUp .5s ease both; }
 444 | .stage-tx-card:nth-child(2) { animation-delay: .05s; }
 445 | .stage-tx-card:nth-child(3) { animation-delay: .10s; }
 446 | .stage-tx-card:nth-child(4) { animation-delay: .15s; }
 447 | .stage-tx-card:nth-child(5) { animation-delay: .20s; }
 448 | .stage-tx-card:nth-child(6) { animation-delay: .25s; }
 449 | 
 450 | /* Loading shimmer */
 451 | .shimmer {
 452 |   background: linear-gradient(90deg, rgba(255,255,255,.04) 0%, rgba(255,255,255,.08) 50%, rgba(255,255,255,.04) 100%);
 453 |   background-size: 200% 100%;
 454 |   animation: shimmer 1.5s infinite;
 455 | }
 456 | @keyframes shimmer {
 457 |   0%   { background-position: -200% 0; }
 458 |   100% { background-position: 200% 0; }
 459 | }
 460 | </style>
 461 | {% endblock %}
 462 | 
 463 | {% block content %}
 464 | <div class="stage-wrap">
 465 | 
 466 |   <!-- TOP STATUS BAR -->
 467 |   <div class="stage-topbar">
 468 |     <div class="stage-topbar__live">
 469 |       <div class="stage-topbar__dot"></div>
 470 |       <span class="stage-topbar__label">On Air</span>
 471 |     </div>
 472 |     <div class="stage-topbar__ticker">
 473 |       <div class="stage-topbar__ticker-inner" id="tickerInner">
 474 |         <span class="ticker-item">
 475 |           <span class="ti-label">BITCOIN</span>
 476 |           <span class="ti-val" id="tickerPrice">Loading…</span>
 477 |         </span>
 478 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 479 |         <span class="ticker-item">
 480 |           <span class="ti-label">SENTIMENT</span>
 481 |           <span class="ti-val" id="tickerSentiment">—</span>
 482 |         </span>
 483 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 484 |         <span class="ticker-item">
 485 |           <span class="ti-label">ORACLE</span>
 486 |           <span class="ti-val" id="tickerOracle">Standing By</span>
 487 |         </span>
 488 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 489 |         <span class="ticker-item">
 490 |           <span class="ti-label">NETWORK</span>
 491 |           <span class="ti-val" id="tickerTopics">—</span>
 492 |         </span>
 493 |         <!-- Duplicate for seamless loop -->
 494 |         <span class="ticker-item">
 495 |           <span class="ti-label">BITCOIN</span>
 496 |           <span class="ti-val" id="tickerPrice2">Loading…</span>
 497 |         </span>
 498 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 499 |         <span class="ticker-item">
 500 |           <span class="ti-label">SENTIMENT</span>
 501 |           <span class="ti-val" id="tickerSentiment2">—</span>
 502 |         </span>
 503 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 504 |         <span class="ticker-item">
 505 |           <span class="ti-label">ORACLE</span>
 506 |           <span class="ti-val">Standing By</span>
 507 |         </span>
 508 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 509 |         <span class="ticker-item">
 510 |           <span class="ti-label">NETWORK</span>
 511 |           <span class="ti-val" id="tickerTopics2">—</span>
 512 |         </span>
 513 |       </div>
 514 |     </div>
 515 |     <div class="stage-topbar__time" id="stageTime">—</div>
 516 |   </div>
 517 | 
 518 |   <!-- HEADER -->
 519 |   <div class="stage-header">
 520 |     <div>
 521 |       <div class="stage-header__title">⚡ Oracle Stage</div>
 522 |       <div class="stage-header__sub">LIVE BITCOIN INTELLIGENCE BROADCAST — PROTOCOLPULSE.IO</div>
 523 |     </div>
 524 |     <div class="stage-header__right">
 525 |       <div class="stage-badge stage-badge--on">● On Air</div>
 526 |       <div class="stage-badge stage-badge--ok" id="avatarStatusBadge">● Avatar Ready</div>
 527 |     </div>
 528 |   </div>
 529 | 
 530 |   <!-- MAIN GRID -->
 531 |   <div class="stage-grid">
 532 | 
 533 |     <!-- LEFT: Main content -->
 534 |     <div class="stage-main">
 535 | 
 536 |       <!-- AVATAR DESK -->
 537 |       <div>
 538 |         <div class="stage-brief__section-label">Oracle Desk</div>
 539 |         <div class="stage-desk">
 540 | 
 541 |           <!-- Avatar -->
 542 |           <div class="stage-avatar-wrap">
 543 |             <img class="stage-avatar-img" id="avatarStill"
 544 |                  src="/static/oracle_avatar.png" alt="Oracle Avatar"
 545 |                  onerror="this.style.display='none'">
 546 |             <video class="stage-avatar-vid" id="avatarVid"
 547 |                    playsinline webkit-playsinline muted autoplay></video>
 548 |             <div class="stage-avatar-nameplate">
 549 |               <div class="stage-avatar-nameplate__dot"></div>
 550 |               <div class="stage-avatar-nameplate__name">Oracle — Protocol Pulse</div>
 551 |             </div>
 552 |           </div>
 553 | 
 554 |           <!-- Brief panels -->
 555 |           <div class="stage-brief">
 556 | 
 557 |             <!-- Sentiment -->
 558 |             <div>
 559 |               <div class="stage-brief__section-label">Market Sentiment</div>
 560 |               <div class="stage-brief__sentiment">
 561 |                 <div>
 562 |                   <div class="stage-brief__sentiment-score" id="sentimentScore">—</div>
 563 |                   <div class="stage-brief__sentiment-label" id="sentimentLabel">Loading</div>
 564 |                 </div>
 565 |                 <div style="flex:1">
 566 |                   <div class="stage-brief__sentiment-bar-wrap">
 567 |                     <div class="stage-brief__sentiment-bar" id="sentimentBar" style="width:50%"></div>
 568 |                   </div>
 569 |                   <div style="display:flex;justify-content:space-between;margin-top:4px">
 570 |                     <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-red)">BEARISH</span>
 571 |                     <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-green)">BULLISH</span>
 572 |                   </div>
 573 |                 </div>
 574 |               </div>
 575 |             </div>
 576 | 
 577 |             <!-- Narrative -->
 578 |             <div>
 579 |               <div class="stage-narrative" id="narrativeText">Loading Oracle narrative…</div>
 580 |             </div>
 581 | 
 582 |             <!-- Topics -->
 583 |             <div>
 584 |               <div class="stage-brief__section-label">Active Topics</div>
 585 |               <div class="stage-topics" id="topicsWrap">
 586 |                 <span class="stage-topic stage-topic--neut shimmer" style="width:100px;height:20px;">&nbsp;</span>
 587 |               </div>
 588 |             </div>
 589 | 
 590 |             <!-- Playback controls -->
 591 |             <div>
 592 |               <div class="stage-brief__section-label">Oracle Broadcast</div>
 593 |               <div class="stage-controls">
 594 |                 <button class="stage-btn stage-btn--primary" id="briefBtn" onclick="requestBrief()">
 595 |                   ▶ Daily Brief
 596 |                 </button>
 597 |                 <button class="stage-btn stage-btn--ghost" id="greetBtn" onclick="requestGreet()">
 598 |                   👋 Greet
 599 |                 </button>
 600 |                 <div class="stage-status" id="stageStatus">Ready</div>
 601 |               </div>
 602 |             </div>
 603 | 
 604 |           </div><!-- /stage-brief -->
 605 |         </div><!-- /stage-desk -->
 606 |       </div>
 607 | 
 608 |       <!-- CHANNEL TRANSCRIPTS -->
 609 |       <div>
 610 |         <div class="stage-brief__section-label">Partner Channel Intelligence</div>
 611 |         <div class="stage-transcripts" id="transcriptsGrid">
 612 |           <!-- Skeleton loaders -->
 613 |           {% for i in range(6) %}
 614 |           <div class="stage-tx-card shimmer" style="height:140px;"></div>
 615 |           {% endfor %}
 616 |         </div>
 617 |       </div>
 618 | 
 619 |     </div><!-- /stage-main -->
 620 | 
 621 |     <!-- RIGHT: Sidebar -->
 622 |     <div class="stage-sidebar">
 623 | 
 624 |       <!-- Price Panel -->
 625 |       <div class="stage-panel">
 626 |         <div class="stage-panel__header">
 627 |           <span><span class="stage-panel__header-dot" style="background:var(--s-gold)"></span>Bitcoin Price</span>
 628 |           <span id="priceUpdated" style="font-size:8px;color:rgba(255,255,255,.2)">live</span>
 629 |         </div>
 630 |         <div class="stage-panel__body">
 631 |           <div class="stage-price-big" id="sidebarPrice">—</div>
 632 |           <div class="stage-price-label">USD · Real-Time</div>
 633 |           <div class="stage-price-change" id="sidebarSentimentLine">—</div>
 634 |         </div>
 635 |       </div>
 636 | 
 637 |       <!-- Nostr Signal Panel -->
 638 |       <div class="stage-panel" style="flex:1;overflow:hidden;display:flex;flex-direction:column;">
 639 |         <div class="stage-panel__header">
 640 |           <span><span class="stage-panel__header-dot" style="background:var(--s-red);animation:live-pulse 1.4s infinite"></span>Nostr Signal</span>
 641 |           <span id="nostrCount" style="font-size:8px;color:rgba(255,255,255,.3)">0 posts</span>
 642 |         </div>
 643 |         <div class="stage-panel__body stage-signal-feed" id="nostrFeed">
 644 |           <div style="font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0">
 645 |             Loading signal…
 646 |           </div>
 647 |         </div>
 648 |       </div>
 649 | 
 650 |     </div><!-- /stage-sidebar -->
 651 |   </div><!-- /stage-grid -->
 652 | </div><!-- /stage-wrap -->
 653 | 
 654 | <!-- Transcript Reader Overlay -->
 655 | <div class="stage-reader" id="stageReader">
 656 |   <div class="stage-reader__inner">
 657 |     <button class="stage-reader__close" onclick="closeReader()">
 658 |       ← Back to Stage
 659 |     </button>
 660 |     <div class="stage-reader__channel" id="readerChannel"></div>
 661 |     <div class="stage-reader__title" id="readerTitle"></div>
 662 |     <div class="stage-reader__body" id="readerBody"></div>
 663 |   </div>
 664 | </div>
 665 | 
 666 | <script>
 667 | (function(){
 668 |   'use strict';
 669 | 
 670 |   var AVATAR_BASE = 'https://avatar.protocolpulse.io';
 671 |   var busy = false;
 672 |   var objURL = null;
 673 |   var vid = document.getElementById('avatarVid');
 674 |   var still = document.getElementById('avatarStill');
 675 |   var briefBtn = document.getElementById('briefBtn');
 676 |   var greetBtn = document.getElementById('greetBtn');
 677 |   var statusEl = document.getElementById('stageStatus');
 678 |   var badgeEl  = document.getElementById('avatarStatusBadge');
 679 | 
 680 |   // ── CLOCK ────────────────────────────────────────────
 681 |   function tick(){
 682 |     var now = new Date();
 683 |     document.getElementById('stageTime').textContent =
 684 |       now.toUTCString().slice(17,22) + ' UTC';
 685 |   }
 686 |   tick(); setInterval(tick, 1000);
 687 | 
 688 |   // ── FETCH INTEL ───────────────────────────────────────
 689 |   function loadIntel(){
 690 |     fetch('/api/oracle/ask', {
 691 |       method:'POST',
 692 |       headers:{'Content-Type':'application/json'},
 693 |       body: JSON.stringify({question:'stage_intel_refresh'})
 694 |     })
 695 |     .then(function(r){ return r.json(); })
 696 |     .then(function(d){
 697 |       // price
 698 |       var price = d.price || '';
 699 |       updatePrice(price, d.price_float);
 700 |       // sentiment
 701 |       var score = d.sentiment_score || 50;
 702 |       var label = d.sentiment_label || 'neutral';
 703 |       document.getElementById('sentimentScore').textContent = score;
 704 |       document.getElementById('sentimentLabel').textContent = label.toUpperCase();
 705 |       document.getElementById('sentimentBar').style.width = score + '%';
 706 |       var sentColor = score > 60 ? 'var(--s-green)' : score < 40 ? 'var(--s-red)' : 'var(--s-gold)';
 707 |       document.getElementById('sentimentScore').style.color = sentColor;
 708 |       document.getElementById('sentimentLabel').style.color = sentColor;
 709 |       // ticker
 710 |       document.getElementById('tickerPrice').textContent = price;
 711 |       document.getElementById('tickerPrice2').textContent = price;
 712 |       document.getElementById('tickerSentiment').textContent = label.toUpperCase() + ' ' + score + '/100';
 713 |       document.getElementById('tickerSentiment2').textContent = label.toUpperCase() + ' ' + score + '/100';
 714 |       // sidebar sentiment line
 715 |       document.getElementById('sidebarSentimentLine').innerHTML =
 716 |         '<span style="color:'+sentColor+';font-family:var(--s-mono);font-size:11px">' +
 717 |         label.toUpperCase() + ' — ' + score + '/100</span>';
 718 |       // narrative
 719 |       if(d.narrative){
 720 |         document.getElementById('narrativeText').textContent = d.narrative;
 721 |       }
 722 |       // topics
 723 |       if(d.topics){
 724 |         renderTopics(d.topics);
 725 |         var topicsText = d.topics.replace(/\([^)]+\)/g,'').replace(/,/g,' ·');
 726 |         document.getElementById('tickerTopics').textContent = topicsText;
 727 |         document.getElementById('tickerTopics2').textContent = topicsText;
 728 |       }
 729 |     })
 730 |     .catch(function(){
 731 |       // Fallback: try oracle health endpoint for price
 732 |       fetch(AVATAR_BASE + '/health')
 733 |         .then(function(r){ return r.json(); })
 734 |         .catch(function(){});
 735 |     });
 736 |   }
 737 | 
 738 |   function updatePrice(priceStr, priceFloat){
 739 |     if(!priceStr) return;
 740 |     var fmt = priceFloat ? '$' + Number(priceFloat).toLocaleString('en-US',{maximumFractionDigits:0}) : priceStr;
 741 |     document.getElementById('sidebarPrice').textContent = fmt;
 742 |     document.getElementById('tickerPrice').textContent = fmt;
 743 |     document.getElementById('tickerPrice2').textContent = fmt;
 744 |     document.getElementById('priceUpdated').textContent = new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
 745 |   }
 746 | 
 747 |   function renderTopics(topicsStr){
 748 |     var wrap = document.getElementById('topicsWrap');
 749 |     wrap.innerHTML = '';
 750 |     var parts = topicsStr.split(',');
 751 |     parts.forEach(function(t){
 752 |       t = t.trim();
 753 |       var cls = 'stage-topic--neut';
 754 |       if(t.indexOf('(bullish)')>=0 || t.indexOf('bullish')>=0) cls = 'stage-topic--bull';
 755 |       if(t.indexOf('(bearish)')>=0 || t.indexOf('bearish')>=0) cls = 'stage-topic--bear';
 756 |       var label = t.replace(/\s*\([^)]+\)\s*/g,'').trim();
 757 |       var span = document.createElement('span');
 758 |       span.className = 'stage-topic ' + cls;
 759 |       span.textContent = label;
 760 |       wrap.appendChild(span);
 761 |     });
 762 |   }
 763 | 
 764 |   // ── LOAD TRANSCRIPTS ──────────────────────────────────
 765 |   function loadTranscripts(){
 766 |     fetch('/api/stage/transcripts')
 767 |     .then(function(r){ return r.json(); })
 768 |     .then(function(data){
 769 |       renderTranscripts(data);
 770 |     })
 771 |     .catch(function(){
 772 |       // Fallback: show placeholder cards
 773 |       renderTranscripts([]);
 774 |     });
 775 |   }
 776 | 
 777 |   function renderTranscripts(items){
 778 |     var grid = document.getElementById('transcriptsGrid');
 779 |     if(!items || !items.length){
 780 |       grid.innerHTML = '<div style="grid-column:1/-1;font-family:var(--s-mono);font-size:11px;color:var(--s-muted);padding:20px 0">No transcript data available yet. Channel scan in progress.</div>';
 781 |       return;
 782 |     }
 783 |     grid.innerHTML = '';
 784 |     items.forEach(function(item){
 785 |       var sentCls = 'stage-topic--neut';
 786 |       var sentLabel = item.sentiment || 'neutral';
 787 |       if(sentLabel === 'bullish') sentCls = 'stage-topic--bull';
 788 |       if(sentLabel === 'bearish') sentCls = 'stage-topic--bear';
 789 |       var card = document.createElement('div');
 790 |       card.className = 'stage-tx-card';
 791 |       card.innerHTML = [
 792 |         '<div class="stage-tx-card__channel">' + esc(item.channel||'Unknown') + '</div>',
 793 |         '<div class="stage-tx-card__title">' + esc((item.title||'').slice(0,70)) + '</div>',
 794 |         '<div class="stage-tx-card__excerpt">' + esc((item.excerpt||item.transcript_snippet||'').slice(0,120)) + '…</div>',
 795 |         '<div class="stage-tx-card__footer">',
 796 |           '<button class="stage-tx-card__read-btn" onclick="openReader(this)">Read Brief →</button>',
 797 |           '<span class="stage-topic ' + sentCls + '">' + esc(sentLabel) + '</span>',
 798 |         '</div>',
 799 |       ].join('');
 800 |       // Store full data on card
 801 |       card.dataset.channel  = item.channel || '';
 802 |       card.dataset.title    = item.title   || '';
 803 |       card.dataset.body     = item.transcript_text || item.excerpt || '';
 804 |       grid.appendChild(card);
 805 |     });
 806 |   }
 807 | 
 808 |   function esc(s){
 809 |     return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
 810 |   }
 811 | 
 812 |   // ── NOSTR SIGNAL ──────────────────────────────────────
 813 |   function loadNostr(){
 814 |     fetch('/api/oracle/recent')
 815 |     .then(function(r){ return r.json(); })
 816 |     .then(function(d){
 817 |       var posts = d.nostr_posts || [];
 818 |       renderNostr(posts);
 819 |     })
 820 |     .catch(function(){
 821 |       renderNostr([]);
 822 |     });
 823 |   }
 824 | 
 825 |   function renderNostr(posts){
 826 |     var feed = document.getElementById('nostrFeed');
 827 |     document.getElementById('nostrCount').textContent = posts.length + ' posts';
 828 |     if(!posts.length){
 829 |       feed.innerHTML = '<div style="font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0">No signal yet — relay scanning…</div>';
 830 |       return;
 831 |     }
 832 |     feed.innerHTML = '';
 833 |     posts.slice(0,12).forEach(function(p){
 834 |       var item = document.createElement('div');
 835 |       item.className = 'stage-signal-item';
 836 |       var author = p.nip05 || p.display_name || (p.pubkey ? p.pubkey.slice(0,12)+'…' : 'anon');
 837 |       item.innerHTML = [
 838 |         '<div class="stage-signal-item__author">' + esc(author) + '</div>',
 839 |         '<div class="stage-signal-item__text">' + esc((p.text||'').slice(0,180)) + '</div>',
 840 |       ].join('');
 841 |       feed.appendChild(item);
 842 |     });
 843 |   }
 844 | 
 845 |   // ── TRANSCRIPT READER ─────────────────────────────────
 846 |   window.openReader = function(btn){
 847 |     var card = btn.closest('.stage-tx-card');
 848 |     document.getElementById('readerChannel').textContent = card.dataset.channel;
 849 |     document.getElementById('readerTitle').textContent   = card.dataset.title;
 850 |     document.getElementById('readerBody').textContent    = card.dataset.body || 'Full transcript not available.';
 851 |     document.getElementById('stageReader').classList.add('open');
 852 |     document.body.style.overflow = 'hidden';
 853 |   };
 854 |   window.closeReader = function(){
 855 |     document.getElementById('stageReader').classList.remove('open');
 856 |     document.body.style.overflow = '';
 857 |   };
 858 | 
 859 |   // ── AVATAR PLAYBACK ───────────────────────────────────
 860 |   function setStatus(msg, color, spin){
 861 |     statusEl.textContent = msg;
 862 |     statusEl.style.color = color || 'rgba(255,255,255,.3)';
 863 |     statusEl.className   = 'stage-status' + (msg==='Speaking' ? ' speaking' : '');
 864 |     tickerOracle(msg);
 865 |   }
 866 |   function tickerOracle(msg){
 867 |     document.getElementById('tickerOracle').textContent = msg;
 868 |   }
 869 |   function setBusy(b){
 870 |     busy = b;
 871 |     briefBtn.disabled = b;
 872 |     greetBtn.disabled = b;
 873 |     badgeEl.textContent = b ? '● Rendering…' : '● Avatar Ready';
 874 |     badgeEl.style.color = b ? 'var(--s-gold)' : 'var(--s-green)';
 875 |     badgeEl.style.borderColor = b ? 'rgba(248,193,92,.3)' : 'rgba(46,255,138,.2)';
 876 |     badgeEl.style.background  = b ? 'rgba(248,193,92,.08)' : 'rgba(46,255,138,.08)';
 877 |   }
 878 | 
 879 |   function playVid(url){
 880 |     return new Promise(function(resolve){
 881 |       if(objURL) try{ URL.revokeObjectURL(objURL); }catch(e){}
 882 |       objURL = url;
 883 |       vid.src = url;
 884 |       vid.muted = true;
 885 |       vid.volume = 1.0;
 886 |       still.style.opacity = '0';
 887 |       vid.classList.add('active');
 888 |       setStatus('Speaking','var(--s-green)');
 889 |       var unmuted = false;
 890 |       function tryUnmute(){ if(unmuted) return; unmuted=true; vid.muted=false; vid.volume=1.0; }
 891 |       vid.addEventListener('canplay', function oncp(){ vid.removeEventListener('canplay',oncp); tryUnmute(); }, {once:true});
 892 |       vid.onended = function(){
 893 |         vid.classList.remove('active');
 894 |         still.style.opacity = '1';
 895 |         setStatus('Ready','rgba(255,255,255,.3)');
 896 |         resolve();
 897 |       };
 898 |       vid.onerror = function(){ vid.classList.remove('active'); still.style.opacity='1'; resolve(); };
 899 |       var p = vid.play();
 900 |       if(p){ p.then(function(){ setTimeout(tryUnmute,50); }).catch(function(){
 901 |         setStatus('Tap to play','var(--s-gold)');
 902 |         vid.addEventListener('click', function(){ vid.muted=false; vid.play(); }, {once:true});
 903 |       }); }
 904 |     });
 905 |   }
 906 | 
 907 |   function fetchTO(url, opts, ms){
 908 |     var ctrl = new AbortController();
 909 |     var id = setTimeout(function(){ ctrl.abort(); }, ms||30000);
 910 |     var o = opts||{}; o.signal = ctrl.signal;
 911 |     return fetch(url, o).finally(function(){ clearTimeout(id); });
 912 |   }
 913 | 
 914 |   window.requestBrief = function(){
 915 |     if(busy) return;
 916 |     setBusy(true); setStatus('Fetching brief…','var(--s-gold)');
 917 |     fetchTO(AVATAR_BASE + '/oracle/speak',{
 918 |       method:'POST', headers:{'Content-Type':'application/json'},
 919 |       body: JSON.stringify({intent:'DAILY_BRIEF'})
 920 |     }, 60000)
 921 |     .then(function(r){
 922 |       if(!r.ok) throw new Error('HTTP '+r.status);
 923 |       return r.blob().then(function(b){
 924 |         return URL.createObjectURL(b);
 925 |       });
 926 |     })
 927 |     .then(function(url){ return playVid(url); })
 928 |     .catch(function(e){
 929 |       setStatus('Error — try again','var(--s-red)');
 930 |       console.error(e);
 931 |     })
 932 |     .finally(function(){ setBusy(false); });
 933 |   };
 934 | 
 935 |   window.requestGreet = function(){
 936 |     if(busy) return;
 937 |     setBusy(true); setStatus('Loading…','var(--s-gold)');
 938 |     fetchTO(AVATAR_BASE + '/oracle/response/GREETING',{},15000)
 939 |     .then(function(r){
 940 |       if(!r.ok) throw new Error('HTTP '+r.status);
 941 |       return r.blob().then(function(b){ return URL.createObjectURL(b); });
 942 |     })
 943 |     .then(function(url){ return playVid(url); })
 944 |     .catch(function(e){ setStatus('Error','var(--s-red)'); console.error(e); })
 945 |     .finally(function(){ setBusy(false); });
 946 |   };
 947 | 
 948 |   // Auto-play greeting on load
 949 |   setTimeout(function(){
 950 |     requestGreet();
 951 |   }, 800);
 952 | 
 953 |   // ── INIT DATA ─────────────────────────────────────────
 954 |   loadIntel();
 955 |   loadTranscripts();
 956 |   loadNostr();
 957 | 
 958 |   // Refresh intel every 3 minutes
 959 |   setInterval(loadIntel, 180000);
 960 |   // Refresh Nostr every 2 minutes
 961 |   setInterval(loadNostr, 120000);
 962 | 
 963 | })();
 964 | </script>
 965 | {% endblock %}
 966 | 
```

### File: routes.py (extracted stage routes from 10847 lines)
```
8821 | @app.route('/api/stage/transcript')
8822 | def api_stage_transcript():
8823 |     """Live transcript + sentiment feed for the avatar stage.
8824 |     Returns latest entries from the daily episode if available,
8825 |     otherwise returns empty/offline state for demo fallback."""
8826 |     import json
8827 |     from datetime import datetime, date
8828 |     from pathlib import Path
8829 | 
8830 |     today = date.today().strftime('%Y-%m-%d')
8831 |     episode_dir = Path(__file__).resolve().parent / 'data' / 'episodes' / today
8832 | 
8833 |     entries = []
8834 |     stats = {"bullish": 0, "neutral": 0, "bearish": 0}
8835 |     topics = ["Bitcoin", "Markets", "Network"]
8836 |     is_live = False
8837 | 
8838 |     # Check for narration transcript first, then clips
8839 |     narration_path = episode_dir / 'narration' / 'transcript.json'
8840 |     clips_path     = episode_dir / 'clips' / 'clips.json'
8841 | 
8842 |     if narration_path.exists():
8843 |         try:
8844 |             data = json.loads(narration_path.read_text())
8845 |             for seg in data.get('segments', [])[:20]:
8846 |                 s = float(seg.get('sentiment', 0.0))
8847 |                 entries.append({
8848 |                     "text": seg.get('text', ''),
8849 |                     "sentiment_score": s,
8850 |                     "sentiment_label": "Bullish" if s > 0.3 else ("Bearish" if s < -0.3 else "Neutral"),
8851 |                     "timestamp": seg.get('time', datetime.now().strftime('%H:%M:%S')),
8852 |                 })
8853 |             is_live = True
8854 |         except Exception:
8855 |             pass
8856 |     elif clips_path.exists():
8857 |         try:
8858 |             data = json.loads(clips_path.read_text())
8859 |             for clip in data.get('clips', [])[:15]:
8860 |                 s = float(clip.get('sentiment_score', 0.0))
8861 |                 entries.append({
8862 |                     "text": clip.get('headline', clip.get('text', '')),
8863 |                     "sentiment_score": s,
8864 |                     "sentiment_label": "Bullish" if s > 0.3 else ("Bearish" if s < -0.3 else "Neutral"),
8865 |                     "timestamp": datetime.now().strftime('%H:%M:%S'),
8866 |                 })
8867 |             if entries:
8868 |                 is_live = True
8869 |         except Exception:
8870 |             pass
8871 | 
8872 |     # Compute sentiment stats
8873 |     if entries:
8874 |         scores = [e['sentiment_score'] for e in entries]
8875 |         total = len(scores)
8876 |         bullish = sum(1 for s in scores if s > 0.3)
8877 |         bearish = sum(1 for s in scores if s < -0.3)
8878 |         neutral = total - bullish - bearish
8879 |         stats = {
8880 |             "bullish": round(bullish / total * 100),
8881 |             "neutral": round(neutral / total * 100),
8882 |             "bearish": round(bearish / total * 100),
8883 |         }
8884 | 
8885 |     # Extract topics from source bundle if available
8886 |     sources_path = episode_dir / 'inputs' / 'source_bundle.json'
8887 |     if sources_path.exists():
8888 |         try:
8889 |             bundle = json.loads(sources_path.read_text())
8890 |             raw_topics = bundle.get('top_topics', [])
8891 |             if raw_topics:
8892 |                 topics = [str(t) for t in raw_topics[:3]]
8893 |         except Exception:
8894 |             pass
8895 | 
8896 |     return jsonify({
8897 |         "is_live": is_live,
8898 |         "entries": entries[-5:] if entries else [],
8899 |         "stats": stats,
8900 |         "topics": topics,
8901 |         "status": "Live Briefing" if is_live else "Demo Mode",
8902 |     })
8903 | 
8904 | 
8905 | # ─── NOSTR SIGNAL RADAR ──────────────────────────────────────────
8906 | # Real-time Bitcoin intelligence heatmap tracking top OGs on Nostr
8907 | 

# ... (other routes omitted) ...

9801 | @app.route('/api/oracle/recent')
9802 | def oracle_recent():
9803 |     """Return the 5 most recent Oracle sessions (questions + transcripts)."""
9804 |     try:
9805 |         sessions = (
9806 |             OracleSession.query
9807 |             .order_by(OracleSession.created_at.desc())
9808 |             .limit(5)
9809 |             .all()
9810 |         )
9811 |         return jsonify([{
9812 |             'question': s.question,
9813 |             'transcript': s.transcript,
9814 |             'video_url': s.video_url,
9815 |             'created_at': s.created_at.isoformat() if s.created_at else None,
9816 |         } for s in sessions])
9817 |     except Exception as e:
9818 |         logging.warning(f'Oracle recent fetch failed: {e}')
9819 |         return jsonify([])
9820 | 
9821 | # ═══════════════════════════════════════════════════════════════════════════════
9822 | # F6 MARKETING OS — LAUNCH GATE + MILESTONE BANNER + PERFORMANCE METRICS API
9823 | # ═══════════════════════════════════════════════════════════════════════════════
9824 | 
9825 | @app.context_processor

# ... (other routes omitted) ...

10803 | @app.route('/api/stage/transcripts')
10804 | def api_stage_transcripts():
10805 |     import glob, os, json as _j
10806 |     from pathlib import Path
10807 |     BASE = Path(__file__).resolve().parent / 'video_pipeline_v3'
10808 |     results = []
10809 |     seen = set()
10810 |     # Fresh scrape first
10811 |     scrapes = sorted(glob.glob(str(BASE / 'data/channel_archive/fresh_scrape_*.json')), reverse=True)
10812 |     if scrapes:
10813 |         try:
10814 |             fresh = _j.load(open(scrapes[0]))
10815 |             for v in fresh[:40]:
10816 |                 ch = v.get('channel','')
10817 |                 if ch in seen or ch.startswith('fresh'): continue
10818 |                 t = v.get('transcript_text','')
10819 |                 if not t or len(t) < 80: continue
10820 |                 seen.add(ch)
10821 |                 lines = [l.strip() for l in t.replace('. ',' . ').split('. ') if len(l.strip()) > 40]
10822 |                 excerpt = lines[0][:200] if lines else t[:200]
10823 |                 results.append({'channel':ch,'title':(v.get('title') or '')[:80],
10824 |                     'excerpt':excerpt,'transcript_text':t[:2500],
10825 |                     'sentiment':v.get('sentiment','neutral'),'url':v.get('url','')})
10826 |         except Exception as e:
10827 |             app.logger.warning('stage transcripts err: %s', e)
10828 |     # Channel archive fallback
10829 |     for d in sorted(glob.glob(str(BASE / 'data/channel_archive/*/'))):
10830 |         ch = os.path.basename(d.rstrip('/'))
10831 |         if ch in seen or 'fresh' in ch: continue
10832 |         files = sorted(glob.glob(os.path.join(d,'*.json')), reverse=True)
10833 |         if not files: continue
10834 |         try:
10835 |             v = _j.load(open(files[0]))
10836 |             t = v.get('transcript_text','')
10837 |             if not t or len(t) < 80: continue
10838 |             seen.add(ch)
10839 |             lines = [l.strip() for l in t.replace('. ',' . ').split('. ') if len(l.strip()) > 40]
10840 |             excerpt = lines[0][:200] if lines else t[:200]
10841 |             results.append({'channel':v.get('channel',ch),'title':(v.get('title') or '')[:80],
10842 |                 'excerpt':excerpt,'transcript_text':t[:2500],
10843 |                 'sentiment':v.get('sentiment','neutral'),'url':v.get('url','')})
10844 |         except Exception: continue
10845 |         if len(results) >= 12: break
10846 |     return jsonify(results)
10847 | 
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
