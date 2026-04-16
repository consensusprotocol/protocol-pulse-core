# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: panopticon_design
# Branch: main
# Generated: 2026-04-15 21:34 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS

### LAW 1: BRAND PALETTE
- Primary Red: #CC2222 (accent, borders, kickers)
- FFmpeg Red: #FF3333 (drawtext/drawbox fallback — closest FFmpeg-safe)
- Background: #0A0A0F (dark navy, never pure black)
- White: #FFFFFF (primary text)
- Gold: #F8C15C (info rail, price displays)
- Mono Font: JetBrains Mono (data, kickers, code)

### LAW 2: PIXEL ZONES
- Full canvas: 1920×1080
- Left panel (PiP): 0–960px wide, full 1080 height
- Right panel (PiP video): 960–1920px
- PiP zone: top-right quadrant x=960-1880, y=0-540
- Subtitle band: y=778-885, full width, dark glass bg
- Info rail: bottom y≈1032-1080, gold text

### LAW 3: TYPOGRAPHY
- Headlines: Bold, white, large (fontsize 42-56)
- Kickers: Red monospace, uppercase, fontsize 24-28
- Body: White, fontsize 28-32
- Sponsor text: White monospace, fontsize 22-26

### LAW 4: COMPONENT PATTERNS
- Cards: Dark bg (#111), red left accent border (3px), white text
- Glass panels: rgba(0,0,0,0.82) fill, subtle border
- Sponsor carousel: 3 rotating cards, 8s per card, FFmpeg enable= timing
- Episode title: Large white bold, "PULSE CHECK" red kicker above

### LAW 5: ANIMATION
- Sponsor rotation: enable='between(t,START,END)' pattern
- Smooth transitions preferred, hard cuts acceptable for data cards
- No debug overlays in production



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: templates/panopticon.html (3906 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}PANOPTICON — Congressional Intelligence | Protocol Pulse
   4 | <script src="/static/js/panopticon_stream.js"></script>
   5 | {% endblock %}
   6 | {% block meta_description %}Real-time intelligence dashboard tracking congressional disclosures, whale wallet movements, and geopolitical financial signals cross-referenced with Bitcoin data.{% endblock %}
   7 | 
   8 | {% block head %}
   9 | <link rel="preconnect" href="https://fonts.googleapis.com">
  10 | <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  11 | <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  12 | <style>
  13 | /* ── FONT FALLBACK — readable text before web fonts load ── */
  14 | body { font-family: 'JetBrains Mono', 'Courier New', monospace; }
  15 | /* ═══════════════════════════════════════════════════════════════════════
  16 |    PANOPTICON — "They watch us. Now we watch them."
  17 |    Surveillance Grid × Bloomberg Terminal
  18 |    ═══════════════════════════════════════════════════════════════════════ */
  19 | :root {
  20 |     --pn-bg: #000;
  21 |     --pn-surface: #0a0a0a;
  22 |     --pn-surface-2: #111;
  23 |     --pn-border: #1a1a1a;
  24 |     --pn-border-active: #333;
  25 |     --pn-text: #fff;
  26 |     --pn-text-secondary: #888;
  27 |     --pn-muted: #555;
  28 |     --pn-red: #ff3b5f;
  29 |     --pn-red-dim: rgba(255,59,95,0.12);
  30 |     --pn-gold: #f8c15c;
  31 |     --pn-white: #fff;
  32 | }
  33 | 
  34 | * { box-sizing: border-box; }
  35 | 
  36 | body.panopticon-body {
  37 |     background: var(--pn-bg) !important;
  38 |     color: var(--pn-text);
  39 |     font-family: 'Inter', -apple-system, sans-serif;
  40 |     margin: 0;
  41 |     padding: 0;
  42 |     overflow-x: hidden;
  43 |     -webkit-font-smoothing: antialiased;
  44 | }
  45 | body.panopticon-body nav,
  46 | body.panopticon-body .navbar,
  47 | body.panopticon-body footer,
  48 | body.panopticon-body .site-footer,
  49 | body.panopticon-body .pp-nav,
  50 | body.panopticon-body .pp-footer { display: none !important; }
  51 | 
  52 | /* ── HERO SECTION — RADAR SWEEP ─────────────────────────────── */
  53 | .pn-hero {
  54 |     position: relative;
  55 |     width: 100%;
  56 |     height: clamp(320px, 18vh, 400px);
  57 |     min-height: 320px;
  58 |     overflow: hidden;
  59 |     display: flex;
  60 |     align-items: center;
  61 |     justify-content: center;
  62 |     flex-direction: column;
  63 |     border-bottom: 1px solid var(--pn-border);
  64 | }
  65 | .pn-hero-radar {
  66 |     position: absolute;
  67 |     inset: 0;
  68 |     overflow: hidden;
  69 | }
  70 | /* Radar concentric rings */
  71 | .pn-radar-rings {
  72 |     position: absolute;
  73 |     top: 50%;
  74 |     left: 50%;
  75 |     width: 600px;
  76 |     height: 600px;
  77 |     transform: translate(-50%, -50%);
  78 | }
  79 | .pn-radar-ring {
  80 |     position: absolute;
  81 |     top: 50%;
  82 |     left: 50%;
  83 |     border: 1px solid rgba(255,59,95,0.06);
  84 |     border-radius: 50%;
  85 | }
  86 | .pn-radar-ring:nth-child(1) { width: 150px; height: 150px; transform: translate(-50%,-50%); }
  87 | .pn-radar-ring:nth-child(2) { width: 300px; height: 300px; transform: translate(-50%,-50%); }
  88 | .pn-radar-ring:nth-child(3) { width: 450px; height: 450px; transform: translate(-50%,-50%); }
  89 | .pn-radar-ring:nth-child(4) { width: 600px; height: 600px; transform: translate(-50%,-50%); }
  90 | /* Crosshairs */
  91 | .pn-radar-cross {
  92 |     position: absolute;
  93 |     top: 50%;
  94 |     left: 50%;
  95 |     width: 600px;
  96 |     height: 600px;
  97 |     transform: translate(-50%,-50%);
  98 | }
  99 | .pn-radar-cross::before,
 100 | .pn-radar-cross::after {
 101 |     content: '';
 102 |     position: absolute;
 103 |     background: rgba(255,59,95,0.04);
 104 | }
 105 | .pn-radar-cross::before {
 106 |     top: 0;
 107 |     left: 50%;
 108 |     width: 1px;
 109 |     height: 100%;
 110 | }
 111 | .pn-radar-cross::after {
 112 |     top: 50%;
 113 |     left: 0;
 114 |     width: 100%;
 115 |     height: 1px;
 116 | }
 117 | /* Rotating sweep beam */
 118 | .pn-radar-sweep {
 119 |     position: absolute;
 120 |     top: 50%;
 121 |     left: 50%;
 122 |     width: 300px;
 123 |     height: 300px;
 124 |     transform-origin: 0 0;
 125 |     animation: radarSweep 6s linear infinite;
 126 |     background: conic-gradient(
 127 |         from 0deg,
 128 |         transparent 0deg,
 129 |         rgba(255,59,95,0.15) 10deg,
 130 |         rgba(255,59,95,0.08) 30deg,
 131 |         transparent 60deg
 132 |     );
 133 |     border-radius: 0 300px 0 0;
 134 |     pointer-events: none;
 135 | }
 136 | @keyframes radarSweep {
 137 |     from { transform: rotate(0deg); }
 138 |     to { transform: rotate(360deg); }
 139 | }
 140 | /* Scan lines */
 141 | .pn-scanlines {
 142 |     position: absolute;
 143 |     inset: 0;
 144 |     background: repeating-linear-gradient(
 145 |         to bottom,
 146 |         transparent 0px,
 147 |         transparent 2px,
 148 |         rgba(255,59,95,0.015) 2px,
 149 |         rgba(255,59,95,0.015) 4px
 150 |     );
 151 |     pointer-events: none;
 152 | }
 153 | /* Hero content */
 154 | .pn-hero-content {
 155 |     position: relative;
 156 |     z-index: 2;
 157 |     text-align: center;
 158 | }
 159 | .pn-hero-title {
 160 |     font-family: 'JetBrains Mono', monospace;
 161 |     font-weight: 800;
 162 |     font-size: clamp(32px, 3vw, 52px);
 163 |     letter-spacing: clamp(6px, 0.7vw, 14px);
 164 |     text-transform: uppercase;
 165 |     color: var(--pn-red);
 166 |     margin: 0 0 10px;
 167 |     text-shadow: 0 0 40px rgba(255,59,95,0.3);
 168 | }
 169 | .pn-hero-tagline {
 170 |     font-family: 'JetBrains Mono', monospace;
 171 |     font-size: clamp(12px, 0.9vw, 15px);
 172 |     letter-spacing: clamp(4px, 0.4vw, 7px);
 173 |     text-transform: uppercase;
 174 |     color: var(--pn-text-secondary);
 175 |     margin: 0 0 28px;
 176 | }
 177 | .pn-hero-stats {
 178 |     display: flex;
 179 |     gap: clamp(24px, 2.5vw, 48px);
 180 |     justify-content: center;
 181 |     align-items: center;
 182 |     min-height: clamp(60px, 6vh, 84px);
 183 |     padding: 0 clamp(16px, 2vw, 32px);
 184 |     flex-wrap: wrap;
 185 | }
 186 | .pn-hero-stat {
 187 |     text-align: center;
 188 |     min-width: 92px;
 189 | }
 190 | .pn-hero-stat-val {
 191 |     font-family: 'JetBrains Mono', monospace;
 192 |     font-size: clamp(22px, 1.9vw, 32px);
 193 |     font-weight: 700;
 194 |     color: var(--pn-white);
 195 |     line-height: 1.1;
 196 | }
 197 | .pn-hero-stat-label {
 198 |     font-family: 'JetBrains Mono', monospace;
 199 |     font-size: clamp(10px, 0.7vw, 13px);
 200 |     letter-spacing: clamp(1.5px, 0.15vw, 2.5px);
 201 |     text-transform: uppercase;
 202 |     color: var(--pn-muted);
 203 |     margin-top: 6px;
 204 | }
 205 | .pn-hero-stat-sep {
 206 |     width: 1px;
 207 |     height: clamp(28px, 2.5vh, 44px);
 208 |     background: var(--pn-border);
 209 | }
 210 | /* Header bar */
 211 | .pn-topbar {
 212 |     position: sticky;
 213 |     top: 0;
 214 |     z-index: 100;
 215 |     display: flex;
 216 |     align-items: center;
 217 |     justify-content: space-between;
 218 |     padding: 8px 16px;
 219 |     background: rgba(0,0,0,0.92);
 220 |     backdrop-filter: blur(12px);
 221 |     -webkit-backdrop-filter: blur(12px);
 222 |     border-bottom: 1px solid var(--pn-border);
 223 | }
 224 | .pn-topbar-left {
 225 |     display: flex;
 226 |     align-items: center;
 227 |     gap: 16px;
 228 | }
 229 | .pn-topbar-logo {
 230 |     font-family: 'JetBrains Mono', monospace;
 231 |     font-weight: 800;
 232 |     font-size: 12px;
 233 |     letter-spacing: 3px;
 234 |     color: var(--pn-red);
 235 | }
 236 | .pn-topbar-status {
 237 |     display: flex;
 238 |     align-items: center;
 239 |     gap: 6px;
 240 |     font-family: 'JetBrains Mono', monospace;
 241 |     font-size: 10px;
 242 |     color: var(--pn-red);
 243 |     letter-spacing: 1px;
 244 | }
 245 | .pn-topbar-dot {
 246 |     width: 6px;
 247 |     height: 6px;
 248 |     border-radius: 50%;
 249 |     background: var(--pn-red);
 250 |     animation: pnPulse 2s ease-in-out infinite;
 251 | }
 252 | @keyframes pnPulse {
 253 |     0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(255,59,95,0.5); }
 254 |     50% { opacity: 0.4; box-shadow: 0 0 0 4px rgba(255,59,95,0); }
 255 | }
 256 | .pn-topbar-right {
 257 |     display: flex;
 258 |     align-items: center;
 259 |     gap: 20px;
 260 | }
 261 | .pn-topbar-clock {
 262 |     font-family: 'JetBrains Mono', monospace;
 263 |     font-size: 13px;
 264 |     font-weight: 500;
 265 |     color: var(--pn-white);
 266 |     letter-spacing: 1px;
 267 | }
 268 | .pn-topbar-btc {
 269 |     font-family: 'JetBrains Mono', monospace;
 270 |     font-size: 13px;
 271 |     font-weight: 700;
 272 |     color: var(--pn-gold);
 273 | }
 274 | .pn-topbar-back {
 275 |     color: var(--pn-muted);
 276 |     text-decoration: none;
 277 |     font-family: 'JetBrains Mono', monospace;
 278 |     font-size: 10px;
 279 |     letter-spacing: 1px;
 280 |     transition: color 0.2s;
 281 | }
 282 | .pn-topbar-back:hover { color: var(--pn-white); }
 283 | 
 284 | /* ── LIVE TICKER ─────────────────────────────────────────────── */
 285 | .pn-ticker {
 286 |     display: flex;
 287 |     align-items: center;
 288 |     padding: clamp(8px, 0.8vw, 12px) clamp(16px, 1.5vw, 24px);
 289 |     border-bottom: 1px solid var(--pn-border);
 290 |     background: var(--pn-surface);
 291 |     gap: clamp(12px, 1.2vw, 18px);
 292 |     overflow: hidden;
 293 |     min-height: clamp(36px, 3vh, 44px);
 294 | }
 295 | .pn-ticker-tag {
 296 |     font-family: 'JetBrains Mono', monospace;
 297 |     font-size: clamp(10px, 0.7vw, 12px);
 298 |     font-weight: 800;
 299 |     letter-spacing: clamp(1.5px, 0.15vw, 2.5px);
 300 |     text-transform: uppercase;
 301 |     color: var(--pn-red);
 302 |     padding: 3px 10px;
 303 |     border: 1px solid rgba(255,59,95,0.3);
 304 |     background: rgba(255,59,95,0.06);
 305 |     white-space: nowrap;
 306 |     flex-shrink: 0;
 307 | }
 308 | .pn-ticker-scroll {
 309 |     flex: 1;
 310 |     overflow: hidden;
 311 |     position: relative;
 312 |     height: clamp(18px, 1.4vh, 22px);
 313 | }
 314 | .pn-ticker-text {
 315 |     font-family: 'JetBrains Mono', monospace;
 316 |     font-size: clamp(11px, 0.8vw, 13px);
 317 |     color: var(--pn-text-secondary);
 318 |     white-space: nowrap;
 319 |     position: absolute;
 320 |     animation: tickerScroll 40s linear infinite;
 321 | }
 322 | @keyframes tickerScroll {
 323 |     0% { transform: translateX(0); }
 324 |     100% { transform: translateX(-50%); }
 325 | }
 326 | 
 327 | /* ── MAIN GRID — 2-ZONE LAYOUT (evidence left, intel right) ─── */
 328 | .pn-main {
 329 |     max-width: clamp(1280px, 94vw, 2400px);
 330 |     margin: 0 auto;
 331 |     padding: 0 clamp(0px, 1vw, 24px);
 332 | }
 333 | .pn-grid {
 334 |     display: grid;
 335 |     grid-template-columns: 65fr 35fr;
 336 |     gap: clamp(16px, 1.5vw, 28px);
 337 |     background: transparent;
 338 |     min-height: calc(100vh - 420px);
 339 |     padding: clamp(16px, 1.5vw, 28px) 0;
 340 |     align-items: start;
 341 | }
 342 | .pn-grid > .pn-right-rail {
 343 |     position: sticky;
 344 |     top: 52px;
 345 |     max-height: calc(100vh - 64px);
 346 |     overflow-y: auto;
 347 |     scrollbar-width: thin;
 348 |     scrollbar-color: rgba(255,59,95,0.25) transparent;
 349 | }
 350 | .pn-grid > .pn-right-rail::-webkit-scrollbar { width: 3px; }
 351 | .pn-grid > .pn-right-rail::-webkit-scrollbar-thumb { background: rgba(255,59,95,0.25); border-radius: 2px; }
 352 | @media (max-width: 1100px) {
 353 |     .pn-grid { grid-template-columns: 1fr; }
 354 |     .pn-grid > .pn-right-rail { position: static; max-height: none; }
 355 | }
 356 | @media (max-width: 768px) {
 357 |     .pn-grid { grid-template-columns: 1fr; gap: 12px; padding: 12px 0; }
 358 |     .pn-hero { height: 240px; min-height: 240px; }
 359 |     .pn-hero-title { font-size: 24px; letter-spacing: 6px; }
 360 |     .pn-hero-tagline { font-size: 11px; letter-spacing: 3px; }
 361 |     .pn-hero-stats { flex-wrap: wrap; gap: 16px; min-height: 0; }
 362 |     .pn-hero-stat-val { font-size: 18px; }
 363 |     .pn-hero-stat-label { font-size: 10px; }
 364 | }
 365 | 
 366 | /* ── PANEL ────────────────────────────────────────────────────── */
 367 | .pn-panel {
 368 |     background: var(--pn-bg);
 369 |     padding: clamp(20px, 2vw, 32px) clamp(16px, 1.5vw, 24px);
 370 |     position: relative;
 371 |     overflow-y: auto;
 372 |     max-height: calc(100vh - 200px);
 373 |     border: 1px solid var(--pn-border);
 374 |     border-radius: 6px;
 375 | }
 376 | .pn-panel-head {
 377 |     font-family: 'JetBrains Mono', monospace;
 378 |     font-size: clamp(12px, 0.85vw, 15px);
 379 |     font-weight: 700;
 380 |     text-transform: uppercase;
 381 |     letter-spacing: clamp(1.5px, 0.18vw, 2.5px);
 382 |     margin-bottom: clamp(16px, 1.4vw, 22px);
 383 |     padding-bottom: clamp(10px, 1vw, 14px);
 384 |     padding-left: 12px;
 385 |     border-bottom: 1px solid var(--pn-border);
 386 |     display: flex;
 387 |     align-items: center;
 388 |     gap: 10px;
 389 |     flex-wrap: wrap;
 390 | }
 391 | /* Mission-control left accent on panel headers */
 392 | .pn-tier-confirmed .pn-panel-head { border-left: 2px solid var(--pn-red); }
 393 | .pn-tier-flagged .pn-panel-head { border-left: 2px solid var(--pn-gold); }
 394 | .pn-tier-feed .pn-panel-head { border-left: 2px solid var(--pn-white); }
 395 | /* Animated pulse dot for TIER 1 header */
 396 | .pn-tier-confirmed .pn-panel-head .tier-dot {
 397 |     animation: pnPulse 2s ease-in-out infinite;
 398 | }
 399 | .pn-panel-head .tier-dot {
 400 |     width: 8px;
 401 |     height: 8px;
 402 |     border-radius: 50%;
 403 |     flex-shrink: 0;
 404 | }
 405 | .pn-panel-head .tier-label {
 406 |     flex: 1;
 407 | }
 408 | .pn-panel-head .tier-count {
 409 |     font-size: clamp(10px, 0.7vw, 12px);
 410 |     color: var(--pn-muted);
 411 |     font-weight: 500;
 412 | }
 413 | .pn-tier-confirmed .tier-dot { background: var(--pn-red); box-shadow: 0 0 8px rgba(255,59,95,0.4); }
 414 | .pn-tier-confirmed .pn-panel-head { color: var(--pn-red); }
 415 | .pn-tier-flagged .tier-dot { background: var(--pn-gold); box-shadow: 0 0 8px rgba(248,193,92,0.4); }
 416 | .pn-tier-flagged .pn-panel-head { color: var(--pn-gold); }
 417 | .pn-tier-feed .tier-dot { background: var(--pn-white); box-shadow: 0 0 8px rgba(255,255,255,0.3); }
 418 | .pn-tier-feed .pn-panel-head { color: var(--pn-white); }
 419 | 
 420 | .pn-section-label {
 421 |     font-family: 'JetBrains Mono', monospace;
 422 |     font-size: clamp(11px, 0.75vw, 13px);
 423 |     font-weight: 700;
 424 |     letter-spacing: clamp(1.5px, 0.18vw, 2.5px);
 425 |     text-transform: uppercase;
 426 |     color: var(--pn-muted);
 427 |     margin: clamp(24px, 2vw, 36px) 0 clamp(14px, 1.2vw, 18px);
 428 |     padding: clamp(16px, 1.4vw, 20px) 0 0 12px;
 429 |     border-top: 1px solid var(--pn-border);
 430 |     border-left: 2px solid rgba(255,59,95,0.3);
 431 | }
 432 | 
 433 | /* ── DISCLOSURE CARDS — elevated with party-colored borders ─── */
 434 | .pn-disc-card {
 435 |     background: var(--pn-surface);
 436 |     border: 1px solid var(--pn-border);
 437 |     border-left: 3px solid var(--pn-red);
 438 |     padding: 14px 16px;
 439 |     margin-bottom: clamp(10px, 1vw, 14px);
 440 |     border-radius: 4px;
 441 |     transition: border-color 0.3s, transform 0.3s;
 442 |     opacity: 0;
 443 |     transform: translateX(-8px);
 444 |     animation: cardEnter 0.4s ease forwards;
 445 |     position: relative;
 446 | }
 447 | /* Party-colored left border */
 448 | .pn-disc-card[data-party="R"] { border-left-color: var(--pn-red); }
 449 | .pn-disc-card[data-party="D"] { border-left-color: #3b82f6; }
 450 | .pn-disc-card[data-party="I"] { border-left-color: #888; }
 451 | /* Gradient separator between cards */
 452 | .pn-disc-card + .pn-disc-card::before {
 453 |     content: '';
 454 |     display: block;
 455 |     position: absolute;
 456 |     top: -6px;
 457 |     left: 10%;
 458 |     right: 10%;
 459 |     height: 1px;
 460 |     background: linear-gradient(90deg, transparent, rgba(255,59,95,0.12), transparent);
 461 | }
 462 | .pn-disc-card:nth-child(1) { animation-delay: 0.1s; }
 463 | .pn-disc-card:nth-child(2) { animation-delay: 0.2s; }
 464 | .pn-disc-card:nth-child(3) { animation-delay: 0.3s; }
 465 | .pn-disc-card:nth-child(4) { animation-delay: 0.4s; }
 466 | .pn-disc-card:nth-child(5) { animation-delay: 0.5s; }
 467 | @keyframes cardEnter {
 468 |     to { opacity: 1; transform: translateX(0); }
 469 | }
 470 | .pn-disc-card:hover { border-color: var(--pn-red); }
 471 | .pn-disc-head {
 472 |     display: flex;
 473 |     justify-content: space-between;
 474 |     align-items: center;
 475 |     margin-bottom: 10px;
 476 |     gap: 8px;
 477 | }
 478 | /* Amount range tag — subtle right-aligned */
 479 | .pn-disc-amount-tag {
 480 |     font-family: 'JetBrains Mono', monospace;
 481 |     font-size: 9px;
 482 |     color: var(--pn-text-secondary);
 483 |     background: rgba(255,255,255,0.03);
 484 |     border: 1px solid var(--pn-border);
 485 |     padding: 2px 8px;
 486 |     border-radius: 3px;
 487 |     white-space: nowrap;
 488 |     flex-shrink: 0;
 489 | }
 490 | .pn-disc-entity {
 491 |     font-size: 13px;
 492 |     font-weight: 700;
 493 |     color: var(--pn-white);
 494 |     overflow: hidden;
 495 |     white-space: nowrap;
 496 |     text-overflow: ellipsis;
 497 |     line-height: 1.35;
 498 | }
 499 | /* Typewriter effect for entity names */
 500 | .pn-disc-entity.typewriter {
 501 |     border-right: 2px solid var(--pn-red);
 502 |     animation: typewriterBlink 0.7s step-end infinite;
 503 |     width: 0;
 504 |     display: inline-block;
 505 | }
 506 | @keyframes typewriterBlink {
 507 |     50% { border-color: transparent; }
 508 | }
 509 | .pn-disc-party {
 510 |     font-family: 'JetBrains Mono', monospace;
 511 |     font-size: 8px;
 512 |     font-weight: 700;
 513 |     padding: 2px 8px;
 514 |     letter-spacing: 1px;
 515 |     flex-shrink: 0;
 516 |     border-radius: 10px;
 517 | }
 518 | .pn-disc-party.R { background: rgba(255,59,95,0.15); color: var(--pn-red); border: 1px solid rgba(255,59,95,0.3); }
 519 | .pn-disc-party.D { background: rgba(59,130,246,0.12); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); }
 520 | .pn-disc-party.I { background: rgba(255,255,255,0.05); color: var(--pn-muted); border: 1px solid rgba(255,255,255,0.1); }
 521 | .pn-disc-fields {
 522 |     display: grid;
 523 |     grid-template-columns: 1fr 1fr;
 524 |     gap: clamp(8px, 0.8vw, 14px);
 525 | }
 526 | .pn-disc-field-label {
 527 |     font-family: 'JetBrains Mono', monospace;
 528 |     font-size: clamp(10px, 0.7vw, 11px);
 529 |     font-weight: 700;
 530 |     letter-spacing: clamp(1.2px, 0.12vw, 1.8px);
 531 |     text-transform: uppercase;
 532 |     color: var(--pn-muted);
 533 |     margin-bottom: 3px;
 534 | }
 535 | .pn-disc-field-val {
 536 |     font-family: 'JetBrains Mono', monospace;
 537 |     font-size: 12px;
 538 |     font-weight: 500;
 539 |     color: var(--pn-white);
 540 |     line-height: 1.35;
 541 | }
 542 | /* Asset name in gold, Type in small caps */
 543 | .pn-disc-field-val.asset-val { color: var(--pn-gold); font-size: 11px; }
 544 | .pn-disc-field-val.type-val { font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; }
 545 | .pn-disc-field-val.buy { color: #89ffb8; }
 546 | .pn-disc-field-val.sell { color: var(--pn-red); }
 547 | .pn-disc-correlation {
 548 |     margin-top: 10px;
 549 |     padding: 8px 10px;
 550 |     background: rgba(255,59,95,0.04);
 551 |     border: 1px solid rgba(255,59,95,0.12);
 552 |     font-family: 'JetBrains Mono', monospace;
 553 |     font-size: 10px;
 554 |     color: var(--pn-red);
 555 |     line-height: 1.4;
 556 |     position: relative;
 557 |     overflow: hidden;
 558 | }
 559 | .pn-disc-correlation::before {
 560 |     content: "PATTERN DETECTED";
 561 |     display: block;
 562 |     font-size: 8px;
 563 |     font-weight: 800;
 564 |     letter-spacing: 2px;
 565 |     margin-bottom: 4px;
 566 |     opacity: 0.7;
 567 | }
 568 | /* Red ripple pulse on PATTERN DETECTED */
 569 | .pn-disc-correlation::after {
 570 |     content: '';
 571 |     position: absolute;
 572 |     top: 50%;
 573 |     left: 50%;
 574 |     width: 200%;
 575 |     height: 200%;
 576 |     transform: translate(-50%,-50%) scale(0);
 577 |     background: radial-gradient(circle, rgba(255,59,95,0.08) 0%, transparent 70%);
 578 |     animation: patternPulse 3s ease-out infinite;
 579 |     pointer-events: none;
 580 | }
 581 | @keyframes patternPulse {
 582 |     0% { transform: translate(-50%,-50%) scale(0); opacity: 1; }
 583 |     100% { transform: translate(-50%,-50%) scale(1); opacity: 0; }
 584 | }
 585 | .pn-disc-source {
 586 |     margin-top: 8px;
 587 |     font-family: 'JetBrains Mono', monospace;
 588 |     font-size: 9px;
 589 |     color: var(--pn-muted);
 590 | }
 591 | .pn-disc-source a { color: var(--pn-text-secondary); text-decoration: none; }
 592 | .pn-disc-source a:hover { color: var(--pn-red); }
 593 | 
 594 | /* ── TIER BADGE ANIMATION ─────────────────────────────────────── */
 595 | .pn-tier-badge {
 596 |     font-family: 'JetBrains Mono', monospace;
 597 |     font-size: 8px;
 598 |     font-weight: 800;
 599 |     letter-spacing: 2px;
 600 |     padding: 3px 10px;
 601 |     text-transform: uppercase;
 602 |     opacity: 0;
 603 |     transform: scale(0.8);
 604 |     animation: badgeReveal 0.4s ease forwards;
 605 | }
 606 | .pn-tier-badge.tier-1 {
 607 |     background: rgba(255,59,95,0.12);
 608 |     color: var(--pn-red);
 609 |     border: 1px solid rgba(255,59,95,0.25);
 610 |     animation-delay: 0.6s;
 611 | }
 612 | .pn-tier-badge.tier-2 {
 613 |     background: rgba(248,193,92,0.12);
 614 |     color: var(--pn-gold);
 615 |     border: 1px solid rgba(248,193,92,0.25);
 616 |     animation-delay: 0.7s;
 617 | }
 618 | @keyframes badgeReveal {
 619 |     to { opacity: 1; transform: scale(1); }
 620 | }
 621 | 
 622 | /* ── CORRELATION TIMELINE SVG ─────────────────────────────────── */
 623 | .pn-corr-timeline {
 624 |     margin: 12px 0;
 625 |     padding: 16px;
 626 |     background: var(--pn-surface);
 627 |     border: 1px solid var(--pn-border);
 628 |     overflow-x: auto;
 629 | }
 630 | .pn-corr-timeline svg {
 631 |     display: block;
 632 |     margin: 0 auto;
 633 |     overflow: visible;
 634 | }
 635 | .pn-corr-node {
 636 |     cursor: default;
 637 | }
 638 | .pn-corr-node circle {
 639 |     transition: r 0.3s ease;
 640 | }
 641 | .pn-corr-node:hover circle {
 642 |     r: 14;
 643 | }
 644 | .pn-corr-path {
 645 |     fill: none;
 646 |     stroke-linecap: round;
 647 |     animation: pathDraw 1.5s ease forwards;
 648 |     stroke-dasharray: 300;
 649 |     stroke-dashoffset: 300;
 650 | }
 651 | @keyframes pathDraw {
 652 |     to { stroke-dashoffset: 0; }
 653 | }
 654 | .pn-corr-summary {
 655 |     font-family: 'Inter', sans-serif;
 656 |     font-size: 12px;
 657 |     color: var(--pn-text-secondary);
 658 |     line-height: 1.5;
 659 |     margin: 10px 0;
 660 | }
 661 | .pn-corr-event-row {
 662 |     display: flex;
 663 |     align-items: center;
 664 |     gap: 8px;
 665 |     padding: 6px 10px;
 666 |     background: rgba(255,255,255,0.02);
 667 |     margin-bottom: 4px;
 668 |     font-family: 'JetBrains Mono', monospace;
 669 |     font-size: 10px;
 670 |     color: var(--pn-text-secondary);
 671 | }
 672 | .pn-corr-event-tag {
 673 |     font-size: 8px;
 674 |     font-weight: 800;
 675 |     letter-spacing: 1px;
 676 |     padding: 2px 6px;
 677 |     text-transform: uppercase;
 678 |     flex-shrink: 0;
 679 | }
 680 | .pn-corr-event-tag.disclosure { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 681 | .pn-corr-event-tag.whale { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 682 | .pn-corr-event-tag.geo { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
 683 | 
 684 | .pn-disclaimer-note {
 685 |     margin-bottom: 12px;
 686 |     padding: 8px 12px;
 687 |     background: rgba(255,59,95,0.03);
 688 |     border: 1px solid rgba(255,59,95,0.08);
 689 |     font-family: 'JetBrains Mono', monospace;
 690 |     font-size: 9px;
 691 |     color: var(--pn-muted);
 692 |     letter-spacing: 0.5px;
 693 |     line-height: 1.5;
 694 | }
 695 | 
 696 | /* ── WHALE CASCADE FEED ──────────────────────────────────────── */
 697 | .pn-whale-item {
 698 |     background: var(--pn-surface);
 699 |     border: 1px solid var(--pn-border);
 700 |     padding: 12px 14px;
 701 |     margin-bottom: 6px;
 702 |     position: relative;
 703 |     opacity: 0;
 704 |     transform: translateY(-20px);
 705 |     animation: whaleDrop 0.5s ease forwards;
 706 | }
 707 | .pn-whale-item:nth-child(1) { animation-delay: 0.1s; }
 708 | .pn-whale-item:nth-child(2) { animation-delay: 0.25s; }
 709 | .pn-whale-item:nth-child(3) { animation-delay: 0.4s; }
 710 | .pn-whale-item:nth-child(4) { animation-delay: 0.55s; }
 711 | .pn-whale-item:nth-child(5) { animation-delay: 0.7s; }
 712 | @keyframes whaleDrop {
 713 |     to { opacity: 1; transform: translateY(0); }
 714 | }
 715 | .pn-whale-item.inflow { border-left: 3px solid var(--pn-red); }
 716 | .pn-whale-item.outflow { border-left: 3px solid var(--pn-white); }
 717 | .pn-whale-row {
 718 |     display: flex;
 719 |     justify-content: space-between;
 720 |     align-items: center;
 721 |     margin-bottom: 4px;
 722 | }
 723 | .pn-whale-entity {
 724 |     font-size: 12px;
 725 |     font-weight: 600;
 726 |     color: var(--pn-white);
 727 | }
 728 | .pn-whale-type-tag {
 729 |     font-family: 'JetBrains Mono', monospace;
 730 |     font-size: 8px;
 731 |     font-weight: 700;
 732 |     letter-spacing: 1px;
 733 |     text-transform: uppercase;
 734 |     padding: 2px 6px;
 735 | }
 736 | .pn-whale-type-tag.inflow { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 737 | .pn-whale-type-tag.outflow { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 738 | .pn-whale-amt {
 739 |     font-family: 'JetBrains Mono', monospace;
 740 |     font-size: 20px;
 741 |     font-weight: 700;
 742 | }
 743 | .pn-whale-amt.inflow { color: var(--pn-red); }
 744 | .pn-whale-amt.outflow { color: var(--pn-white); }
 745 | .pn-whale-usd {
 746 |     font-family: 'JetBrains Mono', monospace;
 747 |     font-size: 11px;
 748 |     color: var(--pn-text-secondary);
 749 |     margin-bottom: 6px;
 750 | }
 751 | .pn-whale-meta {
 752 |     display: flex;
 753 |     justify-content: space-between;
 754 |     font-family: 'JetBrains Mono', monospace;
 755 |     font-size: 9px;
 756 |     color: var(--pn-muted);
 757 | }
 758 | .pn-whale-meta a { color: var(--pn-text-secondary); text-decoration: none; }
 759 | .pn-whale-meta a:hover { color: var(--pn-red); }
 760 | /* Whale size indicator (logarithmic glow bar) */
 761 | .pn-whale-size-bar {
 762 |     height: 2px;
 763 |     background: var(--pn-red);
 764 |     margin-top: 8px;
 765 |     border-radius: 1px;
 766 |     box-shadow: 0 0 6px rgba(255,59,95,0.4);
 767 |     transition: width 0.6s ease;
 768 | }
 769 | 
 770 | /* ── POLYMARKET ──────────────────────────────────────────────── */
 771 | .pn-poly-item {
 772 |     background: var(--pn-surface);
 773 |     border: 1px solid var(--pn-border);
 774 |     padding: 12px 14px;
 775 |     margin-bottom: 6px;
 776 | }
 777 | .pn-poly-question {
 778 |     font-size: 11px;
 779 |     font-weight: 600;
 780 |     color: var(--pn-white);
 781 |     margin-bottom: 8px;
 782 |     line-height: 1.3;
 783 | }
 784 | .pn-poly-row {
 785 |     display: flex;
 786 |     align-items: center;
 787 |     gap: 8px;
 788 |     margin-bottom: 6px;
 789 | }
 790 | .pn-poly-pct {
 791 |     font-family: 'JetBrains Mono', monospace;
 792 |     font-size: 20px;
 793 |     font-weight: 700;
 794 | }
 795 | /* Colored percentage — green >60, red <40, gold else */
 796 | .pn-poly-pct.pct-high { color: #22c55e; }
 797 | .pn-poly-pct.pct-low { color: var(--pn-red); }
 798 | .pn-poly-pct.pct-mid { color: var(--pn-gold); }
 799 | .pn-poly-yes {
 800 |     font-family: 'JetBrains Mono', monospace;
 801 |     font-size: 9px;
 802 |     color: var(--pn-muted);
 803 |     text-transform: uppercase;
 804 | }
 805 | .pn-poly-signal {
 806 |     margin-left: auto;
 807 |     font-family: 'JetBrains Mono', monospace;
 808 |     font-size: 9px;
 809 |     font-weight: 700;
 810 |     letter-spacing: 1px;
 811 |     padding: 2px 6px;
 812 |     text-transform: uppercase;
 813 | }
 814 | .pn-poly-signal.bullish { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 815 | .pn-poly-signal.bearish { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 816 | .pn-poly-signal.neutral { background: rgba(255,255,255,0.03); color: var(--pn-muted); }
 817 | .pn-poly-bar {
 818 |     height: 3px;
 819 |     background: var(--pn-border);
 820 |     margin-bottom: 8px;
 821 |     overflow: hidden;
 822 | }
 823 | .pn-poly-bar-fill {
 824 |     height: 100%;
 825 |     transition: width 0.8s ease;
 826 | }
 827 | .pn-poly-bar-fill.bullish { background: var(--pn-white); }
 828 | .pn-poly-bar-fill.bearish { background: var(--pn-red); }
 829 | .pn-poly-bar-fill.neutral { background: var(--pn-muted); }
 830 | .pn-poly-meta {
 831 |     display: flex;
 832 |     gap: 12px;
 833 |     font-family: 'JetBrains Mono', monospace;
 834 |     font-size: 9px;
 835 |     color: var(--pn-muted);
 836 | }
 837 | .pn-poly-meta a { color: var(--pn-text-secondary); text-decoration: none; }
 838 | .pn-poly-meta a:hover { color: var(--pn-red); }
 839 | 
 840 | /* ── FOREX / NATION-STATE ────────────────────────────────────── */
 841 | .pn-forex-item {
 842 |     display: flex;
 843 |     justify-content: space-between;
 844 |     align-items: center;
 845 |     padding: 8px 12px;
 846 |     background: var(--pn-surface);
 847 |     border: 1px solid var(--pn-border);
 848 |     margin-bottom: 4px;
 849 | }
 850 | .pn-forex-pair {
 851 |     font-family: 'JetBrains Mono', monospace;
 852 |     font-size: 12px;
 853 |     font-weight: 700;
 854 |     color: var(--pn-white);
 855 | }
 856 | .pn-forex-rate {
 857 |     font-family: 'JetBrains Mono', monospace;
 858 |     font-size: 14px;
 859 |     font-weight: 700;
 860 |     color: var(--pn-gold);
 861 | }
 862 | 
 863 | /* ── GEOPOLITICAL ────────────────────────────────────────────── */
 864 | .pn-geo-item {
 865 |     background: var(--pn-surface);
 866 |     border: 1px solid var(--pn-border);
 867 |     padding: 12px 14px;
 868 |     margin-bottom: 6px;
 869 | }
 870 | .pn-geo-headline {
 871 |     font-size: 13px;
 872 |     font-weight: 600;
 873 |     color: var(--pn-white);
 874 |     margin-bottom: 8px;
 875 |     line-height: 1.3;
 876 | }
 877 | .pn-geo-signal-tag {
 878 |     display: inline-flex;
 879 |     align-items: center;
 880 |     gap: 4px;
 881 |     font-family: 'JetBrains Mono', monospace;
 882 |     font-size: 9px;
 883 |     font-weight: 700;
 884 |     letter-spacing: 1px;
 885 |     padding: 2px 8px;
 886 |     text-transform: uppercase;
 887 |     margin-bottom: 6px;
 888 | }
 889 | .pn-geo-signal-tag.bullish { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 890 | .pn-geo-signal-tag.bearish { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 891 | .pn-geo-signal-tag.neutral { background: rgba(255,255,255,0.03); color: var(--pn-muted); }
 892 | .pn-geo-rationale {
 893 |     font-family: 'JetBrains Mono', monospace;
 894 |     font-size: 10px;
 895 |     color: var(--pn-text-secondary);
 896 |     line-height: 1.4;
 897 |     margin-top: 6px;
 898 | }
 899 | .pn-geo-meta {
 900 |     margin-top: 8px;
 901 |     font-family: 'JetBrains Mono', monospace;
 902 |     font-size: 9px;
 903 |     color: var(--pn-muted);
 904 |     display: flex;
 905 |     justify-content: space-between;
 906 | }
 907 | 
 908 | /* ── WATCHLIST ────────────────────────────────────────────────── */
 909 | .pn-watchlist-item {
 910 |     display: flex;
 911 |     align-items: center;
 912 |     gap: 12px;
 913 |     padding: 8px 12px;
 914 |     background: var(--pn-surface);
 915 |     border: 1px solid var(--pn-border);
 916 |     margin-bottom: 4px;
 917 | }
 918 | .pn-watchlist-name {
 919 |     font-size: 12px;
 920 |     font-weight: 600;
 921 |     color: var(--pn-white);
 922 |     min-width: 120px;
 923 | }
 924 | .pn-watchlist-note {
 925 |     font-family: 'JetBrains Mono', monospace;
 926 |     font-size: 10px;
 927 |     color: var(--pn-text-secondary);
 928 |     flex: 1;
 929 | }
 930 | 
 931 | /* ── MAKE THE BITCOIN CASE ───────────────────────────────────── */
 932 | .pn-btc-case-btn {
 933 |     display: inline-flex;
 934 |     align-items: center;
 935 |     gap: 6px;
 936 |     background: transparent;
 937 |     border: 1px solid var(--pn-red);
 938 |     color: var(--pn-red);
 939 |     font-family: 'JetBrains Mono', monospace;
 940 |     font-size: 10px;
 941 |     font-weight: 700;
 942 |     letter-spacing: 1px;
 943 |     padding: 8px 16px;
 944 |     cursor: pointer;
 945 |     margin-top: 10px;
 946 |     transition: all 0.2s;
 947 |     text-transform: uppercase;
 948 | }
 949 | .pn-btc-case-btn:hover {
 950 |     background: rgba(255,59,95,0.08);
 951 | }
 952 | .pn-btc-case-btn:disabled {
 953 |     opacity: 0.5;
 954 |     cursor: not-allowed;
 955 | }
 956 | .pn-btc-case-output {
 957 |     display: none;
 958 |     margin-top: 10px;
 959 |     padding: 14px;
 960 |     background: var(--pn-surface);
 961 |     border: 1px solid rgba(248,193,92,0.15);
 962 |     font-family: 'JetBrains Mono', monospace;
 963 |     font-size: 11px;
 964 |     color: var(--pn-gold);
 965 |     line-height: 1.6;
 966 | }
 967 | .pn-btc-case-output.visible { display: block; }
 968 | .pn-btc-case-label {
 969 |     font-size: 8px;
 970 |     font-weight: 800;
 971 |     letter-spacing: 2px;
 972 |     color: var(--pn-gold);
 973 |     margin-bottom: 8px;
 974 |     opacity: 0.6;
 975 | }
 976 | .pn-typewriter-cursor {
 977 |     display: inline-block;
 978 |     width: 2px;
 979 |     height: 14px;
 980 |     background: var(--pn-gold);
 981 |     margin-left: 1px;
 982 |     animation: cursorBlink 0.5s step-end infinite;
 983 |     vertical-align: text-bottom;
 984 | }
 985 | @keyframes cursorBlink {
 986 |     50% { opacity: 0; }
 987 | }
 988 | .pn-btc-case-model {
 989 |     margin-top: 8px;
 990 |     font-size: 9px;
 991 |     color: var(--pn-muted);
 992 | }
 993 | 
 994 | /* ── CLASSIFIED OVERLAY ──────────────────────────────────────── */
 995 | .pn-classified-overlay {
 996 |     position: absolute;
 997 |     inset: 0;
 998 |     z-index: 10;
 999 |     backdrop-filter: blur(12px);
1000 |     -webkit-backdrop-filter: blur(12px);
1001 |     background: rgba(0,0,0,0.6);
1002 |     display: flex;
1003 |     flex-direction: column;
1004 |     align-items: center;
1005 |     justify-content: center;
1006 |     gap: 12px;
1007 | }
1008 | .pn-classified-stamp {
1009 |     font-family: 'JetBrains Mono', monospace;
1010 |     font-size: 28px;
1011 |     font-weight: 800;
1012 |     letter-spacing: 8px;
1013 |     color: var(--pn-red);
1014 |     text-transform: uppercase;
1015 |     transform: rotate(-8deg);
1016 |     border: 3px solid var(--pn-red);
1017 |     padding: 8px 24px;
1018 |     opacity: 0.85;
1019 |     text-shadow: 0 0 20px rgba(255,59,95,0.4);
1020 | }
1021 | .pn-classified-sub {
1022 |     font-family: 'JetBrains Mono', monospace;
1023 |     font-size: 11px;
1024 |     color: var(--pn-text-secondary);
1025 |     letter-spacing: 2px;
1026 | }
1027 | .pn-upgrade-btn {
1028 |     display: inline-block;
1029 |     padding: 10px 24px;
1030 |     background: var(--pn-red);
1031 |     color: var(--pn-white);
1032 |     font-family: 'JetBrains Mono', monospace;
1033 |     font-size: 11px;
1034 |     font-weight: 700;
1035 |     letter-spacing: 2px;
1036 |     text-transform: uppercase;
1037 |     text-decoration: none;
1038 |     transition: all 0.2s;
1039 |     margin-top: 4px;
1040 | }
1041 | .pn-upgrade-btn:hover {
1042 |     background: #e0304f;
1043 |     box-shadow: 0 0 20px rgba(255,59,95,0.3);
1044 | }
1045 | 
1046 | /* ── FALLBACK BANNER ─────────────────────────────────────────── */
1047 | .pn-fallback-banner {
1048 |     background: rgba(255,59,95,0.04);
1049 |     border: 1px solid rgba(255,59,95,0.15);
1050 |     padding: 10px 14px;
1051 |     margin-bottom: 12px;
1052 |     font-family: 'JetBrains Mono', monospace;
1053 |     font-size: 10px;
1054 |     color: var(--pn-red);
1055 |     letter-spacing: 0.5px;
1056 | }
1057 | 
1058 | /* ── EMPTY / LOADING ─────────────────────────────────────────── */
1059 | .pn-empty {
1060 |     font-family: 'JetBrains Mono', monospace;
1061 |     font-size: 11px;
1062 |     color: var(--pn-muted);
1063 |     padding: 20px;
1064 |     text-align: center;
1065 | }
1066 | .pn-loading {
1067 |     display: flex;
1068 |     align-items: center;
1069 |     justify-content: center;
1070 |     gap: 6px;
1071 |     font-family: 'JetBrains Mono', monospace;
1072 |     font-size: 10px;
1073 |     color: var(--pn-muted);
1074 |     padding: 20px;
1075 | }
1076 | .pn-loading-dot {
1077 |     width: 4px;
1078 |     height: 4px;
1079 |     border-radius: 50%;
1080 |     background: var(--pn-red);
1081 |     animation: loadDot 1.2s ease-in-out infinite;
1082 | }
1083 | .pn-loading-dot:nth-child(2) { animation-delay: 0.2s; }
1084 | .pn-loading-dot:nth-child(3) { animation-delay: 0.4s; }
1085 | @keyframes loadDot {
1086 |     0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
1087 |     40% { opacity: 1; transform: scale(1.2); }
1088 | }
1089 | 
1090 | /* ── HISTORICAL PRECEDENTS TIMELINE (GLASSMORPHIC REBUILD) ─── */
1091 | .pn-history {
1092 |     max-width: 1800px;
1093 |     margin: 0 auto;
1094 |     padding: 32px 16px 40px;
1095 |     position: relative;
1096 | }
1097 | .pn-history-header {
1098 |     font-family: 'JetBrains Mono', monospace;
1099 |     font-size: 13px;
1100 |     font-weight: 700;
1101 |     letter-spacing: 0.3em;
1102 |     text-transform: uppercase;
1103 |     color: var(--pn-red);
1104 |     margin-bottom: 6px;
1105 | }
1106 | .pn-history-subhead {
1107 |     font-family: 'Inter', sans-serif;
1108 |     font-size: 12px;
1109 |     color: var(--pn-muted);
1110 |     margin-bottom: 24px;
1111 |     line-height: 1.6;
1112 | }
1113 | .pn-timeline-scroll {
1114 |     overflow-x: auto;
1115 |     overflow-y: visible;
1116 |     -webkit-overflow-scrolling: touch;
1117 |     padding-bottom: 16px;
1118 |     scrollbar-width: thin;
1119 |     scrollbar-color: rgba(255,59,95,0.3) transparent;
1120 | }
1121 | .pn-timeline-scroll::-webkit-scrollbar { height: 4px; }
1122 | .pn-timeline-scroll::-webkit-scrollbar-thumb { background: rgba(255,59,95,0.3); border-radius: 2px; }
1123 | .pn-timeline {
1124 |     display: flex;
1125 |     align-items: center;
1126 |     position: relative;
1127 |     min-width: max-content;
1128 |     padding: 140px 40px 140px;
1129 | }
1130 | /* Glowing red timeline line */
1131 | .pn-timeline::before {
1132 |     content: '';
1133 |     position: absolute;
1134 |     top: 50%;
1135 |     left: 20px;
1136 |     right: 20px;
1137 |     height: 1px;
1138 |     background: var(--pn-red);
1139 |     opacity: 0.6;
1140 |     transform: translateY(-50%);
1141 |     animation: tlGlow 3s ease-in-out infinite;
1142 | }
1143 | @keyframes tlGlow {
1144 |     0%, 100% { box-shadow: 0 0 4px rgba(255,59,95,0.4); }
1145 |     50% { box-shadow: 0 0 12px rgba(255,59,95,0.6); }
1146 | }
1147 | /* Timeline node container */
1148 | .pn-tl-node {
1149 |     position: relative;
1150 |     flex: 0 0 auto;
1151 |     min-width: 110px;
1152 |     text-align: center;
1153 |     display: flex;
1154 |     flex-direction: column;
1155 |     align-items: center;
1156 | }
1157 | /* Above-line events: label on top, dot connects to line */
1158 | .pn-tl-node.tl-above {
1159 |     flex-direction: column-reverse;
1160 |     margin-bottom: 0;
1161 |     margin-top: -120px;
1162 | }
1163 | /* Below-line events */
1164 | .pn-tl-node.tl-below {
1165 |     margin-top: 120px;
1166 | }
1167 | /* Year label */
1168 | .pn-tl-year {
1169 |     font-family: 'JetBrains Mono', monospace;
1170 |     font-size: 11px;
1171 |     font-weight: 800;
1172 |     color: var(--pn-red);
1173 |     margin-bottom: 2px;
1174 |     white-space: nowrap;
1175 | }
1176 | .tl-above .pn-tl-year { margin-bottom: 0; margin-top: 2px; }
1177 | /* Event name */
1178 | .pn-tl-name {
1179 |     font-family: 'Inter', sans-serif;
1180 |     font-size: 10px;
1181 |     font-weight: 600;
1182 |     color: var(--pn-white);
1183 |     line-height: 1.3;
1184 |     max-width: 100px;
1185 |     margin-bottom: 6px;
1186 |     opacity: 0.85;
1187 | }
1188 | .tl-above .pn-tl-name { margin-bottom: 0; margin-top: 6px; }
1189 | /* Stem connecting dot to label area */
1190 | .pn-tl-stem {
1191 |     width: 1px;
1192 |     height: 30px;
1193 |     background: linear-gradient(to bottom, rgba(255,59,95,0.5), rgba(255,59,95,0.1));
1194 | }
1195 | .tl-above .pn-tl-stem {
1196 |     background: linear-gradient(to top, rgba(255,59,95,0.5), rgba(255,59,95,0.1));
1197 | }
1198 | /* The clickable pin dot */
1199 | .pn-tl-dot {
1200 |     width: 16px;
1201 |     height: 16px;
1202 |     border-radius: 50%;
1203 |     background: var(--pn-red);
1204 |     cursor: pointer;
1205 |     position: relative;
1206 |     flex-shrink: 0;
1207 |     transition: transform 0.2s, box-shadow 0.2s;
1208 |     box-shadow: 0 0 6px rgba(255,59,95,0.4);
1209 |     animation: pinPulse 2s ease-in-out infinite;
1210 |     z-index: 2;
1211 | }
1212 | @keyframes pinPulse {
1213 |     0%, 100% { box-shadow: 0 0 6px rgba(255,59,95,0.4), 0 0 0 0 rgba(255,59,95,0.3); }
1214 |     50% { box-shadow: 0 0 8px rgba(255,59,95,0.6), 0 0 0 6px rgba(255,59,95,0); }
1215 | }
1216 | .pn-tl-dot:hover {
1217 |     transform: scale(1.3);
1218 |     box-shadow: 0 0 14px rgba(255,59,95,0.7);
1219 | }
1220 | .pn-tl-dot.active {
1221 |     background: #fff;
1222 |     box-shadow: 0 0 16px rgba(255,59,95,0.8);
1223 |     animation: none;
1224 | }
1225 | /* Glassmorphic info card — fixed position to avoid clipping */
1226 | .pn-tl-card {
1227 |     position: fixed;
1228 |     max-width: 340px;
1229 |     min-width: 280px;
1230 |     background: rgba(0,0,0,0.88);
1231 |     backdrop-filter: blur(20px) saturate(180%);
1232 |     -webkit-backdrop-filter: blur(20px) saturate(180%);
1233 |     border: 1px solid rgba(255,59,95,0.4);
1234 |     border-radius: 12px;
1235 |     padding: 20px;
1236 |     text-align: left;
1237 |     opacity: 0;
1238 |     pointer-events: none;
1239 |     transform: translateY(-8px);
1240 |     transition: opacity 0.25s ease, transform 0.25s ease;
1241 |     z-index: 10000;
1242 |     box-shadow: 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05);
1243 | }
1244 | .pn-tl-card.active {
1245 |     opacity: 1;
1246 |     pointer-events: auto;
1247 |     transform: translateY(0);
1248 | }
1249 | .pn-tl-card-close {
1250 |     position: absolute;
1251 |     top: 10px;
1252 |     right: 12px;
1253 |     background: none;
1254 |     border: none;
1255 |     color: var(--pn-muted);
1256 |     font-size: 16px;
1257 |     cursor: pointer;
1258 |     padding: 2px 6px;
1259 |     line-height: 1;
1260 |     transition: color 0.2s;
1261 | }
1262 | .pn-tl-card-close:hover { color: var(--pn-white); }
1263 | .pn-tl-card-header {
1264 |     font-family: 'JetBrains Mono', monospace;
1265 |     font-size: 11px;
1266 |     font-weight: 700;
1267 |     color: var(--pn-red);
1268 |     text-transform: uppercase;
1269 |     letter-spacing: 1px;
1270 |     margin-bottom: 4px;
1271 |     padding-right: 24px;
1272 | }
1273 | .pn-tl-card-short {
1274 |     font-family: 'Inter', sans-serif;
1275 |     font-size: 13px;
1276 |     color: var(--pn-white);
1277 |     line-height: 1.7;
1278 |     margin-bottom: 10px;
1279 | }
1280 | .pn-tl-card-detail {
1281 |     font-family: 'Inter', sans-serif;
1282 |     font-size: 12px;
1283 |     color: rgba(255,255,255,0.7);
1284 |     line-height: 1.7;
1285 |     margin-bottom: 12px;
1286 | }
1287 | .pn-tl-card-btc {
1288 |     font-family: 'JetBrains Mono', monospace;
1289 |     font-size: 10px;
1290 |     color: var(--pn-red);
1291 |     padding: 8px 10px;
1292 |     background: rgba(255,59,95,0.08);
1293 |     border-left: 2px solid var(--pn-red);
1294 |     border-radius: 0 6px 6px 0;
1295 |     line-height: 1.5;
1296 | }
1297 | .pn-history-coda {
1298 |     font-family: 'JetBrains Mono', monospace;
1299 |     font-size: 11px;
1300 |     color: var(--pn-red);
1301 |     margin-top: 24px;
1302 |     line-height: 1.6;
1303 |     max-width: 800px;
1304 |     font-style: italic;
1305 |     opacity: 0.85;
1306 | }
1307 | 
1308 | /* ── DISCLAIMER ──────────────────────────────────────────────── */
1309 | .pn-disclaimer {
1310 |     padding: 20px 16px;
1311 |     font-family: 'JetBrains Mono', monospace;
1312 |     font-size: 9px;
1313 |     color: var(--pn-muted);
1314 |     line-height: 1.6;
1315 |     max-width: 1800px;
1316 |     margin: 0 auto;
1317 |     border-top: 1px solid var(--pn-border);
1318 | }
1319 | 
1320 | /* ── STATUS CHIP ─────────────────────────────────────────────── */
1321 | .pn-status-chip {
1322 |     font-family: 'JetBrains Mono', monospace;
1323 |     font-size: 8px;
1324 |     font-weight: 700;
1325 |     letter-spacing: 1px;
1326 |     text-transform: uppercase;
1327 |     padding: 2px 8px;
1328 | }
1329 | .pn-status-chip.loading { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
1330 | 
1331 | /* ── CONVICTION SCORE ────────────────────────────────────────── */
1332 | .pn-conviction {
1333 |     display: flex;
1334 |     align-items: center;
1335 |     gap: 6px;
1336 |     margin-top: 8px;
1337 |     padding: 6px 10px;
1338 |     background: rgba(255,255,255,0.02);
1339 |     border: 1px solid var(--pn-border);
1340 | }
1341 | .pn-conviction-label {
1342 |     font-family: 'JetBrains Mono', monospace;
1343 |     font-size: 8px;
1344 |     font-weight: 800;
1345 |     letter-spacing: 1.5px;
1346 |     text-transform: uppercase;
1347 |     color: var(--pn-muted);
1348 | }
1349 | .pn-conviction-score {
1350 |     font-family: 'JetBrains Mono', monospace;
1351 |     font-size: 14px;
1352 |     font-weight: 700;
1353 | }
1354 | .pn-conviction-score.high { color: var(--pn-red); }
1355 | .pn-conviction-score.medium { color: var(--pn-gold); }
1356 | .pn-conviction-score.low { color: var(--pn-muted); }
1357 | .pn-conviction-tag {
1358 |     font-family: 'JetBrains Mono', monospace;
1359 |     font-size: 8px;
1360 |     font-weight: 700;
1361 |     letter-spacing: 1px;
1362 |     padding: 2px 6px;
1363 |     text-transform: uppercase;
1364 | }
1365 | .pn-conviction-tag.high { background: rgba(255,59,95,0.2); color: var(--pn-red); border: 1px solid rgba(255,59,95,0.4); }
1366 | .pn-conviction-tag.medium { background: rgba(248,193,92,0.18); color: var(--pn-gold); border: 1px solid rgba(248,193,92,0.35); }
1367 | .pn-conviction-tag.low { background: transparent; color: var(--pn-muted); border: 1px solid rgba(255,255,255,0.12); }
1368 | .pn-conviction-bar {
1369 |     flex: 1;
1370 |     height: 3px;
1371 |     background: var(--pn-border);
1372 |     overflow: hidden;
1373 | }
1374 | .pn-conviction-bar-fill {
1375 |     height: 100%;
1376 |     transition: width 0.8s ease;
1377 | }
1378 | .pn-conviction-bar-fill.high { background: var(--pn-red); box-shadow: 0 0 6px rgba(255,59,95,0.4); }
1379 | .pn-conviction-bar-fill.medium { background: var(--pn-gold); }
1380 | .pn-conviction-bar-fill.low { background: var(--pn-muted); }
1381 | 
1382 | /* ── WHALE FLOW CLASSIFICATION ───────────────────────────────── */
1383 | .pn-whale-flow {
1384 |     margin-top: 6px;
1385 |     padding: 6px 10px;
1386 |     font-family: 'JetBrains Mono', monospace;
1387 |     font-size: 10px;
1388 |     line-height: 1.4;
1389 |     border-left: 2px solid var(--pn-border);
1390 | }
1391 | .pn-whale-flow.bullish {
1392 |     background: rgba(137,255,184,0.04);
1393 |     border-left-color: #89ffb8;
1394 |     color: #89ffb8;
1395 | }
1396 | .pn-whale-flow.bearish {
1397 |     background: rgba(255,59,95,0.04);
1398 |     border-left-color: var(--pn-red);
1399 |     color: var(--pn-red);
1400 | }
1401 | .pn-whale-flow.neutral {
1402 |     background: rgba(255,255,255,0.02);
1403 |     border-left-color: var(--pn-muted);
1404 |     color: var(--pn-text-secondary);
1405 | }
1406 | .pn-whale-flow-label {
1407 |     font-size: 8px;
1408 |     font-weight: 800;
1409 |     letter-spacing: 1.5px;
1410 |     text-transform: uppercase;
1411 |     margin-bottom: 2px;
1412 |     opacity: 0.7;
1413 | }
1414 | .pn-whale-signal-tag {
1415 |     font-family: 'JetBrains Mono', monospace;
1416 |     font-size: 8px;
1417 |     font-weight: 700;
1418 |     letter-spacing: 1px;
1419 |     padding: 2px 6px;
1420 |     text-transform: uppercase;
1421 |     margin-left: 8px;
1422 | }
1423 | .pn-whale-signal-tag.bullish { background: rgba(137,255,184,0.12); color: #89ffb8; }
1424 | .pn-whale-signal-tag.bearish { background: rgba(255,59,95,0.12); color: var(--pn-red); }
1425 | .pn-whale-signal-tag.neutral { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
1426 | 
1427 | /* ── CORRELATION GAP COLORING ────────────────────────────────── */
1428 | .pn-corr-gap {
1429 |     font-family: 'JetBrains Mono', monospace;
1430 |     font-size: 11px;
1431 |     font-weight: 700;
1432 |     padding: 4px 8px;
1433 |     display: inline-flex;
1434 |     align-items: center;
1435 |     gap: 4px;
1436 |     margin-bottom: 6px;
1437 | }
1438 | .pn-corr-gap.red { background: rgba(255,59,95,0.12); color: var(--pn-red); }
1439 | .pn-corr-gap.orange { background: rgba(248,193,92,0.12); color: var(--pn-gold); }
1440 | .pn-corr-gap.white { background: rgba(255,255,255,0.06); color: var(--pn-white); }
1441 | 
1442 | /* ── POLYMARKET HERO MARKET ──────────────────────────────────── */
1443 | .pn-poly-hero {
1444 |     background: var(--pn-surface);
1445 |     border: 1px solid var(--pn-border);
1446 |     border-left: 3px solid var(--pn-gold);
1447 |     padding: 16px;
1448 |     margin-bottom: 10px;
1449 | }
1450 | .pn-poly-hero .pn-poly-question {
1451 |     font-size: 14px;
1452 |     font-weight: 700;
1453 |     margin-bottom: 10px;
1454 | }
1455 | .pn-poly-hero .pn-poly-pct {
1456 |     font-size: 28px;
1457 | }
1458 | .pn-poly-hero-bar {
1459 |     height: 6px;
1460 |     background: var(--pn-border);
1461 |     overflow: hidden;
1462 |     margin-bottom: 8px;
1463 |     position: relative;
1464 | }
1465 | .pn-poly-hero-bar-fill {
1466 |     height: 100%;
1467 |     background: linear-gradient(90deg, var(--pn-gold), var(--pn-red));
1468 |     transition: width 1.2s ease;
1469 |     position: relative;
1470 | }
1471 | .pn-poly-hero-bar-fill::after {
1472 |     content: '';
1473 |     position: absolute;
1474 |     right: 0;
1475 |     top: -2px;
1476 |     width: 2px;
1477 |     height: 10px;
1478 |     background: var(--pn-white);
1479 |     box-shadow: 0 0 6px rgba(255,255,255,0.6);
1480 |     animation: polyPulse 2s ease-in-out infinite;
1481 | }
1482 | @keyframes polyPulse {
1483 |     0%, 100% { opacity: 1; }
1484 |     50% { opacity: 0.3; }
1485 | }
1486 | .pn-poly-vol-badge {
1487 |     font-family: 'JetBrains Mono', monospace;
1488 |     font-size: 9px;
1489 |     font-weight: 700;
1490 |     color: var(--pn-gold);
1491 |     letter-spacing: 1px;
1492 | }
1493 | </style>
1494 | {% endblock %}
1495 | 
1496 | {% block body_class %}panopticon-body{% endblock %}
1497 | 
1498 | {% block content %}
1499 | 
1500 | <!-- ═══ STICKY TOP BAR ═══ -->
1501 | <div class="pn-topbar">
1502 |     <div class="pn-topbar-left">
1503 |         <span class="pn-topbar-logo">PANOPTICON</span>
1504 |         <div class="pn-topbar-status">
1505 |             <div class="pn-topbar-dot"></div>
1506 |             <span>SCANNING</span>
1507 |         </div>
1508 |     </div>
1509 |     <div class="pn-topbar-right">
1510 |         <span class="pn-topbar-btc" id="pnBtcPrice">
1511 |             {% if data.btc_price %}BTC ${{ "{:,.0f}".format(data.btc_price) }}{% else %}BTC --{% endif %}
1512 |         </span>
1513 |         <span class="pn-topbar-clock" id="pnClock">--:--:-- UTC</span>
1514 |         <a href="/" class="pn-topbar-back">&larr; PROTOCOL PULSE</a>
1515 |     </div>
1516 | </div>
1517 | 
1518 | <!-- ═══ HERO — RADAR SWEEP ═══ -->
1519 | <section class="pn-hero">
1520 |     <div class="pn-hero-radar">
1521 |         <div class="pn-radar-rings">
1522 |             <div class="pn-radar-ring"></div>
1523 |             <div class="pn-radar-ring"></div>
1524 |             <div class="pn-radar-ring"></div>
1525 |             <div class="pn-radar-ring"></div>
1526 |         </div>
1527 |         <div class="pn-radar-cross"></div>
1528 |         <div class="pn-radar-sweep"></div>
1529 |         <div class="pn-scanlines"></div>
1530 |     </div>
1531 |     <div class="pn-hero-content">
1532 |         <h1 class="pn-hero-title">PANOPTICON</h1>
1533 |         <p class="pn-hero-tagline">They watch us. Now we watch them.</p>
1534 | 
1535 |         <div class="pn-hero-stats">
1536 |             <div class="pn-hero-stat">
1537 |                 <div class="pn-hero-stat-val" id="pnStatDisc">{{ data.disclosures|length }}</div>
1538 |                 <div class="pn-hero-stat-label">Disclosures</div>
1539 |             </div>
1540 |             <div class="pn-hero-stat-sep"></div>
1541 |             <div class="pn-hero-stat">
1542 |                 <div class="pn-hero-stat-val" id="pnStatWhales">{{ data.whales|length }}</div>
1543 |                 <div class="pn-hero-stat-label">Whale Moves</div>
1544 |             </div>
1545 |             <div class="pn-hero-stat-sep"></div>
1546 |             <div class="pn-hero-stat">
1547 |                 <div class="pn-hero-stat-val" id="pnStatFlags">{{ data.flagged|length }}</div>
1548 |                 <div class="pn-hero-stat-label">Patterns</div>
1549 |             </div>
1550 |             <div class="pn-hero-stat-sep"></div>
1551 |             <div class="pn-hero-stat">
1552 |                 <div class="pn-hero-stat-val" id="pnStatEvents">{{ data.events_today }}</div>
1553 |                 <div class="pn-hero-stat-label">Events Today</div>
1554 |             </div>
1555 |         </div>
1556 |     </div>
1557 | </section>
1558 | 
1559 | <!-- ═══ LIVE TICKER ═══ -->
1560 | <div class="pn-ticker">
1561 |     <span class="pn-ticker-tag">LIVE FEED</span>
1562 |     <div class="pn-ticker-scroll">
1563 |         <span class="pn-ticker-text">
1564 |             {% if data.whales %}{% for w in data.whales[:3] %}{{ w.entity }}: {{ w.amount_btc }} BTC {{ w.tx_type }} &nbsp;&bull;&nbsp; {% endfor %}{% endif %}{% for d in data.disclosures[:3] %}{{ d.entity }} &mdash; {{ d.asset }} ({{ d.trade_type }}) &nbsp;&bull;&nbsp; {% endfor %}PANOPTICON monitoring {{ data.events_today }} events &nbsp;&bull;&nbsp; All data from public sources &nbsp;&bull;&nbsp; {% if data.whales %}{% for w in data.whales[:3] %}{{ w.entity }}: {{ w.amount_btc }} BTC {{ w.tx_type }} &nbsp;&bull;&nbsp; {% endfor %}{% endif %}{% for d in data.disclosures[:3] %}{{ d.entity }} &mdash; {{ d.asset }} ({{ d.trade_type }}) &nbsp;&bull;&nbsp; {% endfor %}PANOPTICON monitoring {{ data.events_today }} events &nbsp;&bull;&nbsp;
1565 |         </span>
1566 |     </div>
1567 | </div>
1568 | 
1569 | {% if demo_mode %}
1570 | <!-- ═══ CLASSIFIED ALERT BAR ═══ -->
1571 | <div style="display:flex;align-items:center;padding:8px 16px;background:rgba(255,59,95,0.04);border-bottom:1px solid var(--pn-border);gap:12px;">
1572 |     <div style="display:flex;align-items:center;gap:6px;">
1573 |         <div class="pn-topbar-dot"></div>
1574 |         <span style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;color:var(--pn-red);letter-spacing:1px;">CLASSIFIED — COMMANDER ACCESS REQUIRED</span>
1575 |     </div>
1576 |     <a href="/join" style="margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--pn-muted);text-decoration:none;letter-spacing:1px;">Upgrade &rarr;</a>
1577 | </div>
1578 | {% endif %}
1579 | 
1580 | <!-- ═══════════════════════════════════════════════════════════════════════
1581 |      SOVEREIGN SIGNAL v2 — MISSION CONTROL INTELLIGENCE PANEL
1582 |      Replaces the orb/radar. Live data from APIs. Every element is analytical.
1583 |      ════════════════════════════════════════════════════════════════════════ -->
1584 | <div id="ss2-root">
1585 | 
1586 | <!-- ── HEADER ── -->
1587 | <div id="ss2-header">
1588 |   <div>
1589 |     <div class="ss2-overline">PROTOCOL PULSE · INTELLIGENCE SYNTHESIS · LIVE</div>
1590 |     <div class="ss2-title">SOVEREIGN SIGNAL</div>
1591 |   </div>
1592 |   <div id="ss2-composite-block">
1593 |     <div class="ss2-overline" style="text-align:right;">CONVERGENCE INDEX</div>
1594 |     <div id="ss2-score-display">
1595 |       <span id="ss2-score-num">—</span><span class="ss2-score-denom">/100</span>
1596 |     </div>
1597 |     <div id="ss2-verdict">▋ LOADING STREAMS...</div>
1598 |   </div>
1599 | </div>
1600 | 
1601 | <!-- ── SIX ARC GAUGES ── -->
1602 | <div id="ss2-gauges-row">
1603 |   <div class="ss2-gauge-cell" id="gc-congress"   data-stream="congress">
1604 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1605 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1606 |       <path class="ss2-arc-fill" id="ga-congress" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1607 |       <line class="ss2-needle" id="gn-congress" x1="60" y1="65" x2="60" y2="20"/>
1608 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1609 |       <text class="ss2-gauge-score" id="gs-congress" x="60" y="58">—</text>
1610 |     </svg>
1611 |     <div class="ss2-gauge-label">CONGRESS</div>
1612 |     <div class="ss2-gauge-sub" id="gd-congress">IHX · INSIDER TRADES</div>
1613 |     <div class="ss2-gauge-arrow" id="garr-congress">—</div>
1614 |   </div>
1615 |   <div class="ss2-gauge-cell" id="gc-pac" data-stream="pac">
1616 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1617 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1618 |       <path class="ss2-arc-fill" id="ga-pac" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1619 |       <line class="ss2-needle" id="gn-pac" x1="60" y1="65" x2="60" y2="20"/>
1620 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1621 |       <text class="ss2-gauge-score" id="gs-pac" x="60" y="58">—</text>
1622 |     </svg>
1623 |     <div class="ss2-gauge-label">PAC CAPITAL</div>
1624 |     <div class="ss2-gauge-sub" id="gd-pac">FAIRSHAKE · POLITICAL SPEND</div>
1625 |     <div class="ss2-gauge-arrow" id="garr-pac">—</div>
1626 |   </div>
1627 |   <div class="ss2-gauge-cell" id="gc-legislation" data-stream="legislation">
1628 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1629 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1630 |       <path class="ss2-arc-fill" id="ga-legislation" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1631 |       <line class="ss2-needle" id="gn-legislation" x1="60" y1="65" x2="60" y2="20"/>
1632 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1633 |       <text class="ss2-gauge-score" id="gs-legislation" x="60" y="58">—</text>
1634 |     </svg>
1635 |     <div class="ss2-gauge-label">LEGISLATION</div>
1636 |     <div class="ss2-gauge-sub" id="gd-legislation">BILL MOMENTUM · VOTES</div>
1637 |     <div class="ss2-gauge-arrow" id="garr-legislation">—</div>
1638 |   </div>
1639 |   <div class="ss2-gauge-cell" id="gc-onchain" data-stream="onchain">
1640 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1641 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1642 |       <path class="ss2-arc-fill" id="ga-onchain" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1643 |       <line class="ss2-needle" id="gn-onchain" x1="60" y1="65" x2="60" y2="20"/>
1644 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1645 |       <text class="ss2-gauge-score" id="gs-onchain" x="60" y="58">—</text>
1646 |     </svg>
1647 |     <div class="ss2-gauge-label">ON-CHAIN</div>
1648 |     <div class="ss2-gauge-sub" id="gd-onchain">HASHRATE · ACCUMULATION</div>
1649 |     <div class="ss2-gauge-arrow" id="garr-onchain">—</div>
1650 |   </div>
1651 |   <div class="ss2-gauge-cell" id="gc-institutional" data-stream="institutional">
1652 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1653 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1654 |       <path class="ss2-arc-fill" id="ga-institutional" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1655 |       <line class="ss2-needle" id="gn-institutional" x1="60" y1="65" x2="60" y2="20"/>
1656 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1657 |       <text class="ss2-gauge-score" id="gs-institutional" x="60" y="58">—</text>
1658 |     </svg>
1659 |     <div class="ss2-gauge-label">INSTITUTIONAL</div>
1660 |     <div class="ss2-gauge-sub" id="gd-institutional">13F · FORM D · EDGAR</div>
1661 |     <div class="ss2-gauge-arrow" id="garr-institutional">—</div>
1662 |   </div>
1663 |   <div class="ss2-gauge-cell" id="gc-geo" data-stream="geo">
1664 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1665 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1666 |       <path class="ss2-arc-fill" id="ga-geo" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1667 |       <line class="ss2-needle" id="gn-geo" x1="60" y1="65" x2="60" y2="20"/>
1668 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1669 |       <text class="ss2-gauge-score" id="gs-geo" x="60" y="58">—</text>
1670 |     </svg>
1671 |     <div class="ss2-gauge-label">GEOPOLITICAL</div>
1672 |     <div class="ss2-gauge-sub" id="gd-geo">MACRO · NATION-STATE</div>
1673 |     <div class="ss2-gauge-arrow" id="garr-geo">—</div>
1674 |   </div>
1675 | </div>
1676 | 
1677 | <!-- ── HOVER DATA CARD ── -->
1678 | <div id="ss2-datacard">
1679 |   <div id="ss2-dc-header">
1680 |     <div>
1681 |       <div id="ss2-dc-stream" class="ss2-overline"></div>
1682 |       <div id="ss2-dc-title"></div>
1683 |     </div>
1684 |     <div id="ss2-dc-score-wrap">
1685 |       <div id="ss2-dc-score"></div>
1686 |       <div id="ss2-dc-verdict"></div>
1687 |     </div>
1688 |   </div>
1689 |   <div id="ss2-dc-rows"></div>
1690 |   <div id="ss2-dc-insight"></div>
1691 | </div>
1692 | 
1693 | <!-- ── MIDDLE ROW: CORRELATION MAP + SIGNAL BOARD ── -->
1694 | <div id="ss2-middle">
1695 | 
1696 |   <!-- Correlation scatter map -->
1697 |   <div id="ss2-map-wrap">
1698 |     <div class="ss2-overline" style="padding:clamp(14px,1.2vw,18px) clamp(16px,1.4vw,22px) 8px;">SIGNAL CORRELATION MAP  <span style="color:rgba(255,255,255,0.45);font-weight:400;">{% if is_commander %}· HOVER FOR DRILL-DOWN{% else %}· COMMANDER INTELLIGENCE{% endif %}</span></div>
1699 |     <div class="ss2-map-canvas-holder" style="position:relative;flex:1;">
1700 |       <canvas id="ss2-map-canvas" {% if not is_commander %}style="filter:blur(8px);opacity:0.55;pointer-events:none;"{% endif %}></canvas>
1701 |       <div id="ss2-map-tooltip"></div>
1702 |       {% if not is_commander %}
1703 |       <div class="ss2-map-lock">
1704 |         <div class="ss2-map-lock-box">
1705 |           <div class="ss2-map-lock-badge">COMMANDER</div>
1706 |           <div class="ss2-map-lock-title">SIGNAL CORRELATION MAP</div>
1707 |           <div class="ss2-map-lock-sub">Unlock to see live correlation between all 6 sovereign indices — congress, PAC capital, legislation, on-chain, institutional, and geopolitical.</div>
1708 |           <a class="ss2-map-lock-cta" href="/join">UNLOCK COMMANDER →</a>
1709 |         </div>
1710 |       </div>
1711 |       {% endif %}
1712 |     </div>
1713 |     <!-- Axis labels (visible to all tiers — context for free users) -->
1714 |     <div id="ss2-axis-wrap">
1715 |       <div style="font-size:clamp(10px,0.7vw,12px);color:rgba(255,255,255,0.55);letter-spacing:.15em;">← BEARISH &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; BULLISH →</div>
1716 |       <div style="font-size:clamp(10px,0.7vw,12px);color:rgba(255,255,255,0.55);letter-spacing:.15em;">STRENGTH AXIS</div>
1717 |     </div>
1718 |   </div>
1719 | 
1720 |   <!-- Signal Board -->
1721 |   <div id="ss2-board-wrap">
1722 |     <div class="ss2-overline" style="padding:12px 16px 8px;display:flex;justify-content:space-between;">
1723 |       <span>LIVE SIGNAL BOARD</span>
1724 |       <span id="ss2-board-ts" style="color:rgba(255,255,255,0.4);font-weight:400;font-size:clamp(8px,0.6vw,10px);letter-spacing:.1em;"></span>
1725 |     </div>
1726 |     <div id="ss2-signal-board"></div>
1727 |   </div>
1728 | 
1729 | </div>
1730 | 
1731 | <!-- ── BOTTOM: DATA BARS WATERFALL ── -->
1732 | <div id="ss2-waterfall">
1733 |   <div class="ss2-overline" style="padding:10px 16px 8px;">CONVERGENCE WATERFALL  <span style="color:rgba(255,255,255,0.45);font-weight:400;">· CONTRIBUTION TO 74/100</span></div>
1734 |   <div id="ss2-waterfall-bars"></div>
1735 |   <div style="padding:6px 16px 10px;font-size:7px;color:rgba(255,255,255,0.12);font-family:'JetBrains Mono',monospace;">
1736 |     SOURCE: OPENFEC · SEC EDGAR · LEGISCAN CC BY 4.0 · MEMPOOL.SPACE · POLYMARKET &nbsp;·&nbsp; NOT FINANCIAL ADVICE
1737 |   </div>
1738 | </div>
1739 | 
1740 | </div><!-- #ss2-root -->
1741 | 
1742 | <!-- ── STYLES ── -->
1743 | <style>
1744 | #ss2-root {
1745 |   font-family: 'JetBrains Mono', 'Courier New', monospace;
1746 |   background: #030303;
1747 |   border-top: 1px solid rgba(204,0,0,0.25);
1748 |   border-bottom: 1px solid rgba(204,0,0,0.18);
1749 |   color: #fff;
1750 |   position: relative;
1751 |   overflow: hidden;
1752 |   max-width: clamp(1280px, 94vw, 2400px);
1753 |   margin: clamp(16px, 1.5vw, 28px) auto;
1754 |   border-left: 1px solid rgba(204,0,0,0.12);
1755 |   border-right: 1px solid rgba(204,0,0,0.12);
1756 |   border-radius: 6px;
1757 | }
1758 | #ss2-root::before {
1759 |   content: '';
1760 |   position: absolute;
1761 |   inset: 0;
1762 |   background:
1763 |     repeating-linear-gradient(0deg, transparent, transparent 47px, rgba(204,0,0,0.025) 47px, rgba(204,0,0,0.025) 48px),
1764 |     repeating-linear-gradient(90deg, transparent, transparent 47px, rgba(204,0,0,0.025) 47px, rgba(204,0,0,0.025) 48px);
1765 |   pointer-events: none;
1766 |   z-index: 0;
1767 | }
1768 | #ss2-root > * { position: relative; z-index: 1; }
1769 | 
1770 | .ss2-overline {
1771 |   font-size: clamp(10px, 0.7vw, 12px);
1772 |   letter-spacing: .22em;
1773 |   color: rgba(204,0,0,.7);
1774 |   font-weight: 700;
1775 |   text-transform: uppercase;
1776 | }
1777 | .ss2-title {
1778 |   font-size: clamp(22px, 1.8vw, 30px);
1779 |   font-weight: 900;
1780 |   letter-spacing: .12em;
1781 |   color: #fff;
1782 |   line-height: 1;
1783 |   margin-top: 6px;
1784 | }
1785 | 
1786 | /* Header */
1787 | #ss2-header {
1788 |   display: flex;
1789 |   justify-content: space-between;
1790 |   align-items: flex-start;
1791 |   padding: clamp(18px, 1.5vw, 26px) clamp(20px, 1.8vw, 32px) clamp(14px, 1.2vw, 20px);
1792 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1793 |   gap: clamp(16px, 1.5vw, 24px);
1794 |   flex-wrap: wrap;
1795 | }
1796 | #ss2-composite-block { text-align: right; }
1797 | #ss2-score-display {
1798 |   display: flex;
1799 |   align-items: baseline;
1800 |   gap: 3px;
1801 |   justify-content: flex-end;
1802 |   margin-top: 4px;
1803 | }
1804 | #ss2-score-num {
1805 |   font-size: clamp(52px, 4.5vw, 72px);
1806 |   font-weight: 900;
1807 |   line-height: 1;
1808 |   color: #CC0000;
1809 |   text-shadow: 0 0 30px rgba(204,0,0,.55);
1810 |   transition: color .5s;
1811 | }
1812 | .ss2-score-denom { font-size: clamp(16px, 1.2vw, 20px); color: rgba(255,255,255,.2); }
1813 | #ss2-verdict {
1814 |   font-size: clamp(11px, 0.75vw, 13px);
1815 |   letter-spacing: .1em;
1816 |   margin-top: 5px;
1817 |   transition: color .5s;
1818 | }
1819 | 
1820 | /* Gauges row */
1821 | #ss2-gauges-row {
1822 |   display: grid;
1823 |   grid-template-columns: repeat(6, 1fr);
1824 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1825 | }
1826 | .ss2-gauge-cell {
1827 |   padding: clamp(16px, 1.4vw, 24px) clamp(12px, 1.5vw, 22px) clamp(12px, 1.1vw, 18px);
1828 |   border-right: 1px solid rgba(255,255,255,0.04);
1829 |   cursor: pointer;
1830 |   transition: background .15s;
1831 |   position: relative;
1832 | }
1833 | .ss2-gauge-cell:last-child { border-right: none; }
1834 | .ss2-gauge-cell:hover, .ss2-gauge-cell.active { background: rgba(204,0,0,.05); }
1835 | .ss2-gauge-cell.active { background: rgba(204,0,0,.08); }
1836 | 
1837 | .ss2-gauge-svg {
1838 |   width: 100%;
1839 |   height: auto;
1840 |   display: block;
1841 |   margin-bottom: 6px;
1842 |   overflow: visible;
1843 | }
1844 | .ss2-arc-bg {
1845 |   fill: none;
1846 |   stroke: rgba(255,255,255,.06);
1847 |   stroke-width: 5;
1848 |   stroke-linecap: round;
1849 | }
1850 | .ss2-arc-fill {
1851 |   fill: none;
1852 |   stroke-width: 5;
1853 |   stroke-linecap: round;
1854 |   stroke: #f8c15c;
1855 |   transition: stroke-dasharray 1.2s cubic-bezier(.22,.61,.36,1);
1856 | }
1857 | /* Skeleton pulse on gauges before data loads */
1858 | .ss2-arc-fill.skeleton {
1859 |   opacity: 0.3;
1860 |   animation: skeletonPulse 1.5s ease-in-out infinite;
1861 | }
1862 | @keyframes skeletonPulse {
1863 |   0%, 100% { opacity: 0.15; }
1864 |   50% { opacity: 0.35; }
1865 | }
1866 | .ss2-needle {
1867 |   stroke: rgba(255,255,255,.7);
1868 |   stroke-width: 1.5;
1869 |   stroke-linecap: round;
1870 |   transform-origin: 60px 65px;
1871 |   transition: transform 1.4s cubic-bezier(.34,1.56,.64,1);
1872 | }
1873 | .ss2-needle-hub {
1874 |   fill: rgba(255,255,255,.9);
1875 | }
1876 | .ss2-gauge-score {
1877 |   font-family: 'JetBrains Mono', monospace;
1878 |   font-size: 15px;
1879 |   font-weight: 900;
1880 |   text-anchor: middle;
1881 |   fill: #fff;
1882 | }
1883 | .ss2-gauge-label {
1884 |   font-size: clamp(11px, 0.8vw, 14px);
1885 |   font-weight: 700;
1886 |   letter-spacing: .12em;
1887 |   text-align: center;
1888 |   color: rgba(255,255,255,.85);
1889 | }
1890 | .ss2-gauge-sub {
1891 |   font-size: clamp(10px, 0.65vw, 12px);
1892 |   color: rgba(255,255,255,.45);
1893 |   text-align: center;
1894 |   margin-top: 4px;
1895 |   letter-spacing: .04em;
1896 |   line-height: 1.45;
1897 | }
1898 | .ss2-gauge-arrow {
1899 |   font-size: clamp(11px, 0.75vw, 13px);
1900 |   text-align: center;
1901 |   margin-top: 5px;
1902 |   transition: color .5s;
1903 |   letter-spacing: .06em;
1904 | }
1905 | 
1906 | /* Data Card */
1907 | #ss2-datacard {
1908 |   display: none;
1909 |   background: rgba(5,5,5,.97);
1910 |   border: 1px solid rgba(204,0,0,.45);
1911 |   border-radius: 4px;
1912 |   padding: 18px 20px;
1913 |   position: absolute;
1914 |   top: 100px;
1915 |   left: 50%;
1916 |   transform: translateX(-50%);
1917 |   z-index: 50;
1918 |   box-shadow: 0 16px 48px rgba(0,0,0,.85), 0 0 24px rgba(204,0,0,.12);
1919 |   width: 580px;
1920 |   max-width: calc(100% - 40px);
1921 |   animation: ss2FadeIn .15s ease;
1922 | }
1923 | #ss2-datacard.visible { display: block; }
1924 | @keyframes ss2FadeIn { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }
1925 | #ss2-dc-header {
1926 |   display: flex;
1927 |   justify-content: space-between;
1928 |   align-items: flex-start;
1929 |   margin-bottom: 10px;
1930 |   padding-bottom: 10px;
1931 |   border-bottom: 1px solid rgba(255,255,255,.06);
1932 | }
1933 | #ss2-dc-title {
1934 |   font-size: 13px;
1935 |   font-weight: 700;
1936 |   color: #fff;
1937 |   margin-top: 4px;
1938 | }
1939 | #ss2-dc-score { font-size: 32px; font-weight: 900; line-height: 1; }
1940 | #ss2-dc-verdict { font-size: 8px; letter-spacing: .1em; margin-top: 2px; }
1941 | #ss2-dc-rows {
1942 |   display: grid;
1943 |   grid-template-columns: 1fr 1fr;
1944 |   gap: 5px 20px;
1945 |   margin-bottom: 10px;
1946 | }
1947 | .ss2-dc-row {
1948 |   display: flex;
1949 |   justify-content: space-between;
1950 |   align-items: baseline;
1951 |   padding: 5px 0;
1952 |   border-bottom: 1px solid rgba(255,255,255,.04);
1953 |   font-size: clamp(11px, 0.75vw, 13px);
1954 | }
1955 | .ss2-dc-key { color: rgba(255,255,255,.35); }
1956 | .ss2-dc-val { color: rgba(255,255,255,.9); font-weight: 700; }
1957 | .ss2-dc-val.hot { color: #CC0000; }
1958 | .ss2-dc-val.gold { color: #f8c15c; }
1959 | .ss2-dc-val.green { color: #22c55e; }
1960 | #ss2-dc-insight {
1961 |   font-size: clamp(11px, 0.8vw, 13px);
1962 |   color: rgba(255,255,255,.52);
1963 |   line-height: 1.65;
1964 |   border-top: 1px solid rgba(255,255,255,.04);
1965 |   padding-top: 10px;
1966 |   font-style: italic;
1967 | }
1968 | 
1969 | /* Middle row */
1970 | #ss2-middle {
1971 |   display: grid;
1972 |   grid-template-columns: 1fr clamp(380px, 24vw, 520px);
1973 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1974 |   min-height: clamp(340px, 32vh, 440px);
1975 |   position: relative;
1976 | }
1977 | #ss2-map-wrap {
1978 |   border-right: 1px solid rgba(255,255,255,0.04);
1979 |   display: flex;
1980 |   flex-direction: column;
1981 |   position: relative;
1982 | }
1983 | #ss2-map-canvas {
1984 |   display: block;
1985 |   width: 100%;
1986 |   flex: 1;
1987 |   min-height: clamp(300px, 28vh, 400px);
1988 | }
1989 | #ss2-axis-wrap {
1990 |   display: flex;
1991 |   justify-content: space-between;
1992 |   padding: 4px 16px 8px;
1993 | }
1994 | #ss2-map-tooltip {
1995 |   position: absolute;
1996 |   pointer-events: none;
1997 |   opacity: 0;
1998 |   background: rgba(5,5,5,.95);
1999 |   border: 1px solid rgba(204,0,0,.4);
2000 |   border-radius: 3px;
2001 |   padding: 8px 10px;
2002 |   font-size: clamp(10px, 0.7vw, 12px);
2003 |   color: rgba(255,255,255,.8);
2004 |   transition: opacity .12s;
2005 |   z-index: 30;
2006 |   min-width: 140px;
2007 |   line-height: 1.6;
2008 | }
2009 | 
2010 | /* Commander lock overlay (correlation map only — free-tier teaser) */
2011 | .ss2-map-lock {
2012 |   position: absolute;
2013 |   inset: 0;
2014 |   display: flex;
2015 |   align-items: center;
2016 |   justify-content: center;
2017 |   z-index: 20;
2018 |   background: linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.78) 100%);
2019 |   padding: clamp(16px, 2vw, 32px);
2020 | }
2021 | .ss2-map-lock-box {
2022 |   background: rgba(8,8,10,0.92);
2023 |   border: 1px solid rgba(204,0,0,0.55);
2024 |   border-radius: 6px;
2025 |   padding: clamp(20px, 2vw, 32px) clamp(24px, 2.2vw, 36px);
2026 |   max-width: 460px;
2027 |   text-align: center;
2028 |   box-shadow: 0 20px 60px rgba(0,0,0,0.7), 0 0 30px rgba(204,0,0,0.18);
2029 |   backdrop-filter: blur(4px);
2030 | }
2031 | .ss2-map-lock-badge {
2032 |   display: inline-block;
2033 |   font-family: 'JetBrains Mono', monospace;
2034 |   font-size: clamp(10px, 0.75vw, 12px);
2035 |   font-weight: 800;
2036 |   letter-spacing: clamp(2px, 0.2vw, 3.5px);
2037 |   color: #CC0000;
2038 |   padding: 4px 12px;
2039 |   border: 1px solid rgba(204,0,0,0.5);
2040 |   border-radius: 2px;
2041 |   margin-bottom: 14px;
2042 |   background: rgba(204,0,0,0.08);
2043 | }
2044 | .ss2-map-lock-title {
2045 |   font-family: 'JetBrains Mono', monospace;
2046 |   font-size: clamp(16px, 1.3vw, 22px);
2047 |   font-weight: 800;
2048 |   color: #fff;
2049 |   letter-spacing: .08em;
2050 |   line-height: 1.2;
2051 |   margin-bottom: 10px;
2052 | }
2053 | .ss2-map-lock-sub {
2054 |   font-family: 'Inter', -apple-system, sans-serif;
2055 |   font-size: clamp(12px, 0.85vw, 14px);
2056 |   color: rgba(255,255,255,0.65);
2057 |   line-height: 1.55;
2058 |   margin-bottom: 18px;
2059 | }
2060 | .ss2-map-lock-cta {
2061 |   display: inline-block;
2062 |   font-family: 'JetBrains Mono', monospace;
2063 |   font-size: clamp(11px, 0.8vw, 13px);
2064 |   font-weight: 800;
2065 |   letter-spacing: clamp(1.5px, 0.15vw, 2.5px);
2066 |   color: #fff;
2067 |   background: #CC0000;
2068 |   padding: 11px 22px;
2069 |   border-radius: 3px;
2070 |   text-decoration: none;
2071 |   border: 1px solid rgba(255,59,95,0.55);
2072 |   transition: background .2s, transform .15s, box-shadow .2s;
2073 |   text-transform: uppercase;
2074 |   box-shadow: 0 6px 18px rgba(204,0,0,0.28);
2075 | }
2076 | .ss2-map-lock-cta:hover {
2077 |   background: #ff3b5f;
2078 |   transform: translateY(-1px);
2079 |   box-shadow: 0 10px 24px rgba(204,0,0,0.42);
2080 | }
2081 | 
2082 | /* Signal Board */
2083 | #ss2-board-wrap { overflow: hidden; display: flex; flex-direction: column; }
2084 | #ss2-signal-board {
2085 |   padding: 4px 0;
2086 |   overflow-y: auto;
2087 |   flex: 1;
2088 |   max-height: clamp(310px, 32vh, 440px);
2089 | }
2090 | #ss2-signal-board::-webkit-scrollbar { width: 3px; }
2091 | #ss2-signal-board::-webkit-scrollbar-track { background: transparent; }
2092 | #ss2-signal-board::-webkit-scrollbar-thumb { background: rgba(204,0,0,0.3); border-radius: 2px; }
2093 | .ss2-signal-item {
2094 |   display: flex;
2095 |   align-items: flex-start;
2096 |   gap: clamp(10px, 0.8vw, 14px);
2097 |   padding: clamp(10px, 0.9vw, 14px) clamp(16px, 1.2vw, 20px);
2098 |   border-bottom: 1px solid rgba(255,255,255,.04);
2099 |   cursor: default;
2100 |   transition: background .12s;
2101 | }
2102 | .ss2-signal-item:hover { background: rgba(255,255,255,.025); }
2103 | .ss2-si-dot {
2104 |   width: 8px;
2105 |   height: 8px;
2106 |   border-radius: 50%;
2107 |   flex-shrink: 0;
2108 |   margin-top: 5px;
2109 | }
2110 | .ss2-si-body { flex: 1; min-width: 0; }
2111 | .ss2-si-label {
2112 |   font-size: clamp(10px, 0.7vw, 12px);
2113 |   letter-spacing: .14em;
2114 |   margin-bottom: 4px;
2115 |   font-weight: 700;
2116 | }
2117 | .ss2-si-text {
2118 |   font-size: clamp(11px, 0.8vw, 13px);
2119 |   color: rgba(255,255,255,.75);
2120 |   line-height: 1.55;
2121 |   white-space: normal;
2122 | }
2123 | .ss2-si-val {
2124 |   font-size: clamp(12px, 0.85vw, 14px);
2125 |   font-weight: 700;
2126 |   flex-shrink: 0;
2127 |   text-align: right;
2128 |   min-width: 54px;
2129 | }
2130 | 
2131 | /* Waterfall */
2132 | #ss2-waterfall { border-top: 1px solid rgba(255,255,255,0.04); }
2133 | #ss2-waterfall-bars {
2134 |   display: grid;
2135 |   grid-template-columns: repeat(6, 1fr);
2136 |   gap: 1px;
2137 |   padding: clamp(4px, 0.5vw, 8px) clamp(20px, 1.8vw, 32px) clamp(16px, 1.4vw, 22px);
2138 | }
2139 | .ss2-wf-col {
2140 |   padding: clamp(6px, 0.6vw, 10px) clamp(10px, 0.9vw, 14px);
2141 |   cursor: pointer;
2142 |   transition: background .12s;
2143 |   border-right: 1px solid rgba(255,255,255,0.03);
2144 | }
2145 | .ss2-wf-col:last-child { border-right: none; }
2146 | .ss2-wf-col:hover { background: rgba(255,255,255,.025); }
2147 | .ss2-wf-bar-wrap {
2148 |   height: clamp(54px, 4.5vh, 78px);
2149 |   display: flex;
2150 |   align-items: flex-end;
2151 |   justify-content: center;
2152 |   margin-bottom: 8px;
2153 |   gap: 2px;
2154 | }
2155 | .ss2-wf-bar {
2156 |   width: 50%;
2157 |   border-radius: 2px 2px 0 0;
2158 |   min-height: 2px;
2159 |   transition: height 1.5s cubic-bezier(.22,.61,.36,1);
2160 | }
2161 | .ss2-wf-score {
2162 |   font-size: clamp(13px, 0.95vw, 16px);
2163 |   font-weight: 900;
2164 |   text-align: center;
2165 |   margin-bottom: 4px;
2166 | }
2167 | .ss2-wf-label {
2168 |   font-size: clamp(10px, 0.7vw, 12px);
2169 |   color: rgba(255,255,255,.55);
2170 |   text-align: center;
2171 |   letter-spacing: .08em;
2172 |   line-height: 1.45;
2173 |   font-weight: 600;
2174 | }
2175 | .ss2-wf-contrib {
2176 |   font-size: clamp(9px, 0.6vw, 11px);
2177 |   color: rgba(255,255,255,.32);
2178 |   text-align: center;
2179 |   margin-top: 4px;
2180 |   letter-spacing: .04em;
2181 | }
2182 | 
2183 | @media(max-width:1100px) {
2184 |   #ss2-middle { grid-template-columns: 1fr 340px; }
2185 | }
2186 | @media(max-width:900px) {
2187 |   #ss2-middle { grid-template-columns: 1fr; min-height: auto; }
2188 |   #ss2-map-canvas { min-height: 220px; }
2189 |   #ss2-board-wrap { border-top: 1px solid rgba(255,255,255,0.04); }
2190 | }
2191 | @media(max-width:768px) {
2192 |   #ss2-gauges-row { grid-template-columns: repeat(3,1fr); }
2193 |   #ss2-waterfall-bars { grid-template-columns: repeat(3,1fr); }
2194 | }
2195 | @media(max-width:480px) {
2196 |   #ss2-gauges-row { grid-template-columns: repeat(2,1fr); }
2197 |   #ss2-waterfall-bars { grid-template-columns: repeat(2,1fr); }
2198 |   #ss2-score-num { font-size: 40px; }
2199 | }
2200 | </style>
2201 | 
2202 | <!-- ── JAVASCRIPT ── -->
2203 | <script>
2204 | (function() {
2205 | 'use strict';
2206 | 
2207 | // ─── Stream definitions ─────────────────────────────────────────────────────
2208 | var STREAMS = {
2209 |   congress:    { label:'CONGRESS',      sub:'IHX · INSIDER TRADES',   color:'#f8c15c', apiKey:'ihx' },
2210 |   pac:         { label:'PAC CAPITAL',   sub:'FAIRSHAKE · SPEND',       color:'#CC0000', apiKey:'pac' },
2211 |   legislation: { label:'LEGISLATION',   sub:'BILL MOMENTUM',           color:'#22c55e', apiKey:'leg' },
2212 |   onchain:     { label:'ON-CHAIN',      sub:'HASHRATE · ACCUM',        color:'#f8c15c', apiKey:'orb' },
2213 |   institutional:{ label:'INSTITUTIONAL',sub:'13F · FORM D',            color:'#22c55e', apiKey:'inst' },
2214 |   geo:         { label:'GEOPOLITICAL',  sub:'MACRO · NATION-STATE',    color:'#22c55e', apiKey:'orb' },
2215 | };
2216 | 
2217 | var streamOrder = ['congress','pac','legislation','onchain','institutional','geo'];
2218 | var liveData = window._pnLiveData = window._pnLiveData || {};   // filled by API calls, shared across scopes
2219 | var scores = {};     // filled after data arrives
2220 | 
2221 | // ─── Gauge arc math ─────────────────────────────────────────────────────────
2222 | var ARC_LEN = 157; // approx circumference of the half-circle path at r=50
2223 | 
2224 | function scoreToArc(score) {
2225 |   return Math.max(0, Math.min(ARC_LEN, (score / 100) * ARC_LEN));
2226 | }
2227 | 
2228 | function scoreToNeedleAngle(score) {
2229 |   // -90deg (full left) to +90deg (full right)
2230 |   return -90 + (score / 100) * 180;
2231 | }
2232 | 
2233 | function scoreToColor(score) {
2234 |   if (score >= 80) return '#CC0000';
2235 |   if (score >= 65) return '#f8c15c';
2236 |   if (score >= 50) return '#22c55e';
2237 |   return 'rgba(255,255,255,0.35)';
2238 | }
2239 | 
2240 | function scoreToVerdict(score) {
2241 |   if (score >= 85) return { label:'▲ STRONG BULL', col:'#CC0000' };
2242 |   if (score >= 70) return { label:'▲ BULLISH', col:'#f8c15c' };
2243 |   if (score >= 55) return { label:'→ NEUTRAL', col:'rgba(255,255,255,0.45)' };
2244 |   return { label:'▼ CAUTION', col:'#888' };
2245 | }
2246 | 
2247 | function animateGauge(streamId, score) {
2248 |   var color = scoreToColor(score);
2249 |   var arcEl = document.getElementById('ga-' + streamId);
2250 |   var needleEl = document.getElementById('gn-' + streamId);
2251 |   var scoreEl = document.getElementById('gs-' + streamId);
2252 |   var arrEl = document.getElementById('garr-' + streamId);
2253 | 
2254 |   if (!arcEl) return;
2255 | 
2256 |   // Remove skeleton state once real data arrives
2257 |   arcEl.classList.remove('skeleton');
2258 | 
2259 |   arcEl.style.stroke = color;
2260 |   arcEl.style.strokeDasharray = scoreToArc(score) + ' ' + ARC_LEN;
2261 | 
2262 |   var angle = scoreToNeedleAngle(score);
2263 |   needleEl.style.transform = 'rotate(' + angle + 'deg)';
2264 |   scoreEl.textContent = score;
2265 |   scoreEl.style.fill = color;
2266 | 
2267 |   var v = scoreToVerdict(score);
2268 |   arrEl.textContent = v.label.split(' ')[0];
2269 |   arrEl.style.color = v.col;
2270 | }
2271 | 
2272 | function updateComposite(allScores) {
2273 |   var vals = Object.values(allScores);
2274 |   if (!vals.length) return;
2275 |   var avg = Math.round(vals.reduce(function(a,b){return a+b;},0)/vals.length);
2276 |   var scoreEl = document.getElementById('ss2-score-num');
2277 |   var verdEl = document.getElementById('ss2-verdict');
2278 |   var v = scoreToVerdict(avg);
2279 |   if (scoreEl) { scoreEl.textContent = avg; scoreEl.style.color = v.col; }
2280 |   if (verdEl) { verdEl.textContent = v.label; verdEl.style.color = v.col; }
2281 |   // Update waterfall heading
2282 |   var wfHead = document.querySelector('#ss2-waterfall .ss2-overline');
2283 |   if (wfHead) wfHead.innerHTML = 'CONVERGENCE WATERFALL &nbsp;<span style="color:rgba(255,255,255,0.2);font-size:6px;">· CONTRIBUTION TO ' + avg + '/100</span>';
2284 |   return avg;
2285 | }
2286 | 
2287 | // ─── API fetches — progressive rendering (no Promise.allSettled gate) ────────
2288 | function progressiveRender() {
2289 |   // Recompute + render whatever data we have so far
2290 |   computeScores();
2291 |   renderAll();
2292 | }
2293 | 
2294 | function fetchAll() {
2295 |   fetch('/api/congress/ihx').then(function(r){return r.json();}).then(function(d){ liveData.ihx = d; progressiveRender(); }).catch(function(){});
2296 |   fetch('/api/donations/pulse').then(function(r){return r.json();}).then(function(d){ liveData.pac = d; progressiveRender(); }).catch(function(){});
2297 |   fetch('/api/panopticon/bills').then(function(r){return r.json();}).then(function(d){ liveData.bills = d; progressiveRender(); }).catch(function(){});
2298 |   fetch('/api/orb').then(function(r){return r.json();}).then(function(d){ liveData.orb = d; progressiveRender(); }).catch(function(){});
2299 |   fetch('/api/panopticon/institutional').then(function(r){return r.json();}).then(function(d){ liveData.inst = d; progressiveRender(); }).catch(function(){});
2300 |   fetch('/api/congress/trades').then(function(r){return r.json();}).then(function(d){ liveData.trades = d; progressiveRender(); }).catch(function(){});
2301 |   fetch('/api/panopticon/pe-datastream').then(function(r){return r.json();}).then(function(d){ liveData.pe = d; progressiveRender(); }).catch(function(){});
2302 | }
2303 | 
2304 | function computeScores() {
2305 |   var ihx = liveData.ihx || {};
2306 |   var pac = liveData.pac || {};
2307 |   var bills = liveData.bills || {};
2308 |   var orb = (liveData.orb || {});
2309 |   var inst = liveData.inst || {};
2310 |   var streams = orb.streams || {};
2311 | 
2312 |   // Congress: IHX score is 0-100
2313 |   scores.congress = ihx.score || 64;
2314 | 
2315 |   // PAC: donation pulse score
2316 |   scores.pac = pac.score || 88;
2317 | 
2318 |   // Legislation: weight GENIUS (passed=+25), bill bullish count, bills_with_votes
2319 |   var legBase = 50;
2320 |   var billsWithVotes = bills.bills_with_votes || 0;
2321 |   var bullish = bills.bullish_count || 0;
2322 |   legBase += Math.min(30, billsWithVotes * 6);
2323 |   legBase += Math.min(10, bullish * 5);
2324 |   legBase += 15; // GENIUS Act supermajority permanent bonus
2325 |   scores.legislation = Math.min(100, legBase);
2326 | 
2327 |   // On-chain: blend ORB streams (hashrate, accum, exchange_flow, whale)
2328 |   var hashrate = streams.hashrate || 83;
2329 |   var accum = streams.accum || 65;
2330 |   var exchFlow = streams.exchange_flow || 50;
2331 |   var whale = streams.whale || 90;
2332 |   scores.onchain = Math.round((hashrate * 0.3 + accum * 0.3 + exchFlow * 0.2 + whale * 0.2));
2333 | 
2334 |   // Institutional: filers + coalition signal
2335 |   var filers = inst.total_institutional_filers || 20;
2336 |   var coalition = (inst.coalition_summary || {}).count || 0;
2337 |   scores.institutional = Math.min(100, Math.round(40 + filers * 1.2 + coalition * 0.5));
2338 | 
2339 |   // Geo: macro_corr + polymarket blend from ORB
2340 |   var macro = streams.macro_corr || 69.8;
2341 |   var poly = streams.polymarket || 74;
2342 |   var putcall = streams.put_call || 70;
2343 |   scores.geo = Math.round((macro * 0.4 + poly * 0.3 + putcall * 0.3));
2344 | }
2345 | 
2346 | // ─── Render all elements ─────────────────────────────────────────────────────
2347 | function renderAll() {
2348 |   streamOrder.forEach(function(id) {
2349 |     animateGauge(id, scores[id] || 50);
2350 |     // Update gauge sub-label with live key stat
2351 |     var subEl = document.getElementById('gd-' + id);
2352 |     if (subEl) subEl.textContent = getLiveSubLabel(id);
2353 |   });
2354 |   var avg = updateComposite(scores);
2355 |   renderSignalBoard();
2356 |   renderCorrelationMap();
2357 |   renderWaterfall();
2358 |   document.getElementById('ss2-board-ts').textContent = new Date().toLocaleTimeString() + ' LOCAL';
2359 | }
2360 | 
2361 | function getLiveSubLabel(id) {
2362 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {}, orb = liveData.orb || {};
2363 |   var inst = liveData.inst || {}, bills = liveData.bills || {};
2364 |   var streams = orb.streams || {};
2365 |   switch(id) {
2366 |     case 'congress':     return 'IHX ' + (ihx.score||'—') + ' · ' + (ihx.buy_count||0) + 'B/' + (ihx.sell_count||0) + 'S · ' + (ihx.crypto_trades||0) + ' crypto';
2367 |     case 'pac':          return '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M raised · $' + ((pac.fairshake_spend||0)/1e6).toFixed(1) + 'M spent';
2368 |     case 'legislation':  return (bills.bills_with_votes||0) + ' with votes · GENIUS 66–32';
2369 |     case 'onchain':      return 'HR ' + (streams.hashrate||0) + ' · ACCUM ' + (streams.accum||0) + ' · WHALE ' + (streams.whale||0);
2370 |     case 'institutional':return (inst.total_institutional_filers||0) + ' filers · ' + ((inst.coalition_summary||{}).count||0) + ' coalition';
2371 |     case 'geo':          return 'MACRO ' + Math.round(streams.macro_corr||0) + ' · POLY ' + (streams.polymarket||0) + ' · P/C ' + Math.round(streams.put_call||0);
2372 |   }
2373 |   return '';
2374 | }
2375 | 
2376 | // ─── Data card (expanded on gauge click) ────────────────────────────────────
2377 | var activeGauge = null;
2378 | document.addEventListener('click', function(e) {
2379 |   var cell = e.target.closest('.ss2-gauge-cell');
2380 |   if (cell) {
2381 |     var sid = cell.getAttribute('data-stream');
2382 |     if (activeGauge === sid) {
2383 |       closeCard();
2384 |     } else {
2385 |       openCard(sid, cell);
2386 |     }
2387 |     return;
2388 |   }
2389 |   if (!e.target.closest('#ss2-datacard')) closeCard();
2390 | });
2391 | 
2392 | function closeCard() {
2393 |   var card = document.getElementById('ss2-datacard');
2394 |   card.classList.remove('visible');
2395 |   if (activeGauge) {
2396 |     document.getElementById('gc-' + activeGauge).classList.remove('active');
2397 |   }
2398 |   activeGauge = null;
2399 | }
2400 | 
2401 | function openCard(sid, cell) {
2402 |   if (activeGauge) document.getElementById('gc-' + activeGauge).classList.remove('active');
2403 |   activeGauge = sid;
2404 |   cell.classList.add('active');
2405 | 
2406 |   var card = document.getElementById('ss2-datacard');
2407 |   var score = scores[sid] || 50;
2408 |   var v = scoreToVerdict(score);
2409 | 
2410 |   document.getElementById('ss2-dc-stream').textContent = STREAMS[sid].label + ' STREAM';
2411 |   document.getElementById('ss2-dc-title').textContent = STREAMS[sid].sub;
2412 |   document.getElementById('ss2-dc-score').textContent = score;
2413 |   document.getElementById('ss2-dc-score').style.color = scoreToColor(score);
2414 |   document.getElementById('ss2-dc-verdict').textContent = v.label;
2415 |   document.getElementById('ss2-dc-verdict').style.color = v.col;
2416 | 
2417 |   var rows = getCardRows(sid);
2418 |   var rowsEl = document.getElementById('ss2-dc-rows');
2419 |   rowsEl.innerHTML = rows.map(function(r) {
2420 |     return '<div class="ss2-dc-row"><span class="ss2-dc-key">' + r.k + '</span><span class="ss2-dc-val ' + (r.cls||'') + '">' + r.v + '</span></div>';
2421 |   }).join('');
2422 | 
2423 |   document.getElementById('ss2-dc-insight').textContent = getInsight(sid);
2424 | 
2425 |   // Position card below the clicked gauge row
2426 |   var rect = cell.getBoundingClientRect();
2427 |   var rootRect = document.getElementById('ss2-root').getBoundingClientRect();
2428 |   card.style.top = (rect.bottom - rootRect.top + 8) + 'px';
2429 |   card.classList.add('visible');
2430 | }
2431 | 
2432 | function getCardRows(sid) {
2433 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {}, bills = liveData.bills || {};
2434 |   var orb = liveData.orb || {}, streams = (orb.streams || {}), inst = liveData.inst || {};
2435 |   var pe = liveData.pe || {}, trades = liveData.trades || {};
2436 |   switch(sid) {
2437 |     case 'congress': return [
2438 |       { k:'IHX Score',        v: ihx.score + '/100',                    cls: ihx.score>=70?'green':ihx.score>=50?'gold':'hot' },
2439 |       { k:'Buy / Sell',       v: (ihx.buy_count||0) + ' buys / ' + (ihx.sell_count||0) + ' sells' },
2440 |       { k:'Crypto Trades',    v: (ihx.crypto_trades||0) + ' / 8 total' },
2441 |       { k:'Signal',           v: (ihx.signal||'neutral').toUpperCase() },
2442 |       { k:'Top buy',          v: 'McCormick — Bitwise BTC ETF',         cls:'green' },
2443 |       { k:'Top sell',         v: 'Tim Moore — COIN (2-day filing)',      cls:'hot' },
2444 |       { k:'Conviction peak',  v: '95% — Moore COIN, 80-95% — McCormick' },
2445 |       { k:'Net positioning',  v: ihx.buy_count > ihx.sell_count ? 'BULLISH BIAS' : 'MIXED', cls:'gold' },
2446 |     ];
2447 |     case 'pac': var exps = pac.fairshake_expenditures || []; return [
2448 |       { k:'Fairshake raised',  v: '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M (2026 cycle)', cls:'hot' },
2449 |       { k:'Deployed',          v: '$' + ((pac.fairshake_spend||0)/1e6).toFixed(1) + 'M' },
2450 |       { k:'Pulse score',       v: (pac.score||88) + '/100 ' + (pac.label||'HIGH') },
2451 |       { k:'Crypto PACs',       v: (pac.crypto_committees||0) + ' active committees' },
2452 |       { k:'Top donor',         v: 'a16z (AH Capital) — $23.8M',         cls:'gold' },
2453 |       { k:'#2 donor',          v: 'Ben Horowitz — $11.9M' },
2454 |       { k:'#3 donor',          v: 'Marc Andreessen — $11.9M' },
2455 |       { k:'Biggest OPPOSE',    v: (exps[0] ? (exps[0].candidate||'?').substring(0,28) + ' $' + ((exps[0].amount||0)/1e6).toFixed(1)+'M' : '—'), cls:'hot' },
2456 |     ];
2457 |     case 'legislation': var blist = (bills.bills||[]).filter(function(b){return b.congress_score>50;}).slice(0,4); return [
2458 |       { k:'Bills tracked',     v: ((bills.bills||[]).length || 18) + ' total' },
2459 |       { k:'With floor votes',  v: (bills.bills_with_votes||0) + ' bills' },
2460 |       { k:'GENIUS Act',        v: 'PASSED 66–32 Senate',                 cls:'green' },
2461 |       { k:'Market Clarity',    v: '69% congressional support',           cls:'green' },
2462 |       { k:'Anti-CBDC',         v: 'Introduced — Tom Emmer',              cls:'gold' },
2463 |       { k:'BTC Reserve Act',   v: 'Introduced — Tim Burchett',           cls:'gold' },
2464 |       { k:'STABLE Act',        v: 'Introduced — Bryan Steil' },
2465 |       { k:'Bullish vs bearish',v: (bills.bullish_count||0) + 'B / ' + (bills.bearish_count||0) + 'B gap' },
2466 |     ];
2467 |     case 'onchain': return [
2468 |       { k:'Hashrate signal',   v: (streams.hashrate||0) + '/100',         cls: streams.hashrate>=80?'green':'gold' },
2469 |       { k:'Accumulation',      v: (streams.accum||0) + '/100' },
2470 |       { k:'Exchange flow',     v: (streams.exchange_flow||0) + '/100' },
2471 |       { k:'Whale signal',      v: (streams.whale||0) + '/100',            cls: streams.whale>=80?'green':'gold' },
2472 |       { k:'Fear & Greed',      v: (streams.fear_greed||0) + '/100 (FEAR)',cls: streams.fear_greed<=30?'hot':'' },
2473 |       { k:'Fee signal',        v: (streams.fees||0) + '/100',             cls: streams.fees>=90?'green':'' },
2474 |       { k:'SOPR',              v: '0.15 — capitulation zone',             cls:'hot' },
2475 |       { k:'Puell Multiple',    v: 'Green accumulation band',              cls:'green' },
2476 |     ];
2477 |     case 'institutional': return [
2478 |       { k:'Total 13F filers',  v: (inst.total_institutional_filers||0),  cls:'green' },
2479 |       { k:'Coalition detected',v: ((inst.coalition_summary||{}).count||0) + ' coordinated', cls:'hot' },
2480 |       { k:'PE Form D rounds',  v: (pe.pe_count||0) + ' active raises' },
2481 |       { k:'Top filer',         v: 'ParaFi Capital LP — hedge fund',       cls:'gold' },
2482 |       { k:'#2 filer',          v: 'Avenir Tech Ltd — hedge fund' },
2483 |       { k:'#3 filer',          v: 'Galaxy Institutional Bitcoin Fund' },
2484 |       { k:'Coalition signal',  v: (inst.coalition_summary||{}).detected ? 'ACTIVE — coordinated accumulation' : 'None', cls:(inst.coalition_summary||{}).detected?'hot':'' },
2485 |       { k:'Form 4 insiders',   v: 'Coinbase exec cluster buying',         cls:'green' },
2486 |     ];
2487 |     case 'geo': return [
2488 |       { k:'Macro correlation', v: Math.round(streams.macro_corr||0) + '/100',   cls: streams.macro_corr>=65?'green':'' },
2489 |       { k:'Polymarket signal', v: (streams.polymarket||0) + '/100' },
2490 |       { k:'Put/Call ratio',    v: Math.round(streams.put_call||0) + '/100',      cls:'green' },
2491 |       { k:'US Strategic Res.', v: 'EO 14233 — BTC stockpile active',     cls:'green' },
2492 |       { k:'Fed rate (Apr)',    v: '98.2% NO CHANGE (Polymarket)',          cls:'green' },
2493 |       { k:'10Y Treasury',      v: '3.21%' },
2494 |       { k:'JPY pressure',      v: 'Yen debasement accelerating',          cls:'gold' },
2495 |       { k:'EU MiCA',           v: 'Full implementation — neutral' },
2496 |     ];
2497 |   }
2498 |   return [];
2499 | }
2500 | 
2501 | function getInsight(sid) {
2502 |   var insights = {
2503 |     congress:    'IHX at 64 (neutral) with 6/8 crypto-adjacent. McCormick buying Bitwise BTC ETF at 80-95% conviction while Tim Moore\'s 2-day COIN filing speed signals insider awareness. Net positioning: informed bifurcation between senators and representatives.',
2504 |     pac:         'Fairshake 2026 is the largest crypto political operation in US history. a16z, Horowitz, Andreessen coordinating $134M to reshape the congressional map — primarily opposing anti-crypto incumbents. This capital velocity is unprecedented and structurally bullish for regulatory outcomes.',
2505 |     legislation: 'GENIUS Act passing 66-32 was the first major crypto legislation through the Senate. Digital Asset Market Clarity at 69% support signals bipartisan floor momentum. The regulatory moat is forming faster than previous cycles.',
2506 |     onchain:     'SOPR at 0.15 is a deep loss-realization signal. Historical analogue: sub-0.2 SOPR in Q4 2018 preceded +312% over 18 months. Puell Multiple in green band + ATH hashrate (miners not selling) = smart money accumulation concurrent with retail capitulation.',
2507 |     institutional:'Coalition of 18 institutions with coordinated accumulation windows. Galaxy, ParaFi, Coinbase insiders buying via separate channels. Classic informed money vs uninformed market divergence.',
2508 |     geo:         'US Strategic Bitcoin Reserve (EO 14233) represents sovereign demand. 98.2% Polymarket probability of Fed hold removes tail risk. Yen debasement creates structural Bitcoin demand from Japanese capital. Macro backdrop is the most constructive since 2020.',
2509 |   };
2510 |   return insights[sid] || '';
2511 | }
2512 | 
2513 | // ─── Correlation map (canvas) ────────────────────────────────────────────────
2514 | function renderCorrelationMap() {
2515 |   var canvas = document.getElementById('ss2-map-canvas');
2516 |   if (!canvas) return;
2517 |   var wrap = canvas.parentElement;
2518 |   var W = wrap.clientWidth || 400;
2519 |   var H = Math.max(canvas.clientHeight || 0, 280);
2520 |   canvas.width = W * (window.devicePixelRatio||1);
2521 |   canvas.height = H * (window.devicePixelRatio||1);
2522 |   canvas.style.width = W + 'px';
2523 |   canvas.style.height = H + 'px';
2524 |   var ctx = canvas.getContext('2d');
2525 |   ctx.scale(window.devicePixelRatio||1, window.devicePixelRatio||1);
2526 | 
2527 |   // Background
2528 |   ctx.fillStyle = '#050505';
2529 |   ctx.fillRect(0, 0, W, H);
2530 | 
2531 |   // Grid
2532 |   ctx.strokeStyle = 'rgba(255,255,255,0.04)';
2533 |   ctx.lineWidth = 0.5;
2534 |   for (var x=0; x<=W; x+=W/4) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }
2535 |   for (var y=0; y<=H; y+=H/3) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }
2536 | 
2537 |   // Axes
2538 |   ctx.strokeStyle = 'rgba(255,255,255,0.12)';
2539 |   ctx.lineWidth = 1;
2540 |   ctx.beginPath(); ctx.moveTo(W/2,0); ctx.lineTo(W/2,H); ctx.stroke();
2541 |   ctx.beginPath(); ctx.moveTo(0,H/2); ctx.lineTo(W,H/2); ctx.stroke();
2542 | 
2543 |   // Quadrant labels
2544 |   ctx.fillStyle = 'rgba(255,255,255,0.06)';
2545 |   ctx.font = '9px JetBrains Mono';
2546 |   ctx.textAlign = 'center';
2547 |   ctx.fillText('HIGH STRENGTH', W*0.75, 14);
2548 |   ctx.fillText('GAINING MOMENTUM', W*0.75, 26);
2549 |   ctx.fillText('LOW STRENGTH', W*0.25, 14);
2550 |   ctx.fillText('LOSING MOMENTUM', W*0.25, H-8);
2551 | 
2552 |   // Map each stream to X (direction: 0=bearish, 100=bullish) and Y (strength)
2553 |   // X = derived from signal direction  Y = score
2554 |   var mapData = {
2555 |     congress:     { x: 55, y: scores.congress || 64,  color:'#f8c15c' },
2556 |     pac:          { x: 85, y: scores.pac || 88,        color:'#CC0000' },
2557 |     legislation:  { x: 75, y: scores.legislation || 75,color:'#22c55e' },
2558 |     onchain:      { x: 62, y: scores.onchain || 74,    color:'#f8c15c' },
2559 |     institutional:{ x: 70, y: scores.institutional||70,color:'#22c55e' },
2560 |     geo:          { x: 68, y: scores.geo || 70,        color:'#22c55e' },
2561 |   };
2562 | 
2563 |   streamOrder.forEach(function(sid) {
2564 |     var d = mapData[sid];
2565 |     var px = (d.x / 100) * W;
2566 |     var py = H - (d.y / 100) * H;
2567 |     var r = 10 + (d.y / 100) * 12;
2568 | 
2569 |     // Glow
2570 |     var grd = ctx.createRadialGradient(px, py, 0, px, py, r*2);
2571 |     grd.addColorStop(0, d.color + '40');
2572 |     grd.addColorStop(1, d.color + '00');
2573 |     ctx.beginPath(); ctx.arc(px, py, r*2, 0, Math.PI*2);
2574 |     ctx.fillStyle = grd; ctx.fill();
2575 | 
2576 |     // Circle
2577 |     ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI*2);
2578 |     ctx.fillStyle = d.color + '25';
2579 |     ctx.fill();
2580 |     ctx.strokeStyle = d.color;
2581 |     ctx.lineWidth = 1.5;
2582 |     ctx.stroke();
2583 | 
2584 |     // Score label
2585 |     ctx.fillStyle = '#fff';
2586 |     ctx.font = 'bold 9px JetBrains Mono';
2587 |     ctx.textAlign = 'center';
2588 |     ctx.fillText(d.y, px, py + 3);
2589 | 
2590 |     // Stream label below
2591 |     ctx.fillStyle = 'rgba(255,255,255,0.5)';
2592 |     ctx.font = '6px JetBrains Mono';
2593 |     ctx.fillText(STREAMS[sid].label, px, py + r + 10);
2594 |   });
2595 | 
2596 |   // Hover
2597 |   var tooltip = document.getElementById('ss2-map-tooltip');
2598 |   canvas.onmousemove = function(e) {
2599 |     var rect = canvas.getBoundingClientRect();
2600 |     var mx = e.clientX - rect.left, my = e.clientY - rect.top;
2601 |     var hit = null;
2602 |     streamOrder.forEach(function(sid) {
2603 |       var d = mapData[sid];
2604 |       var px = (d.x / 100) * W;
2605 |       var py = H - (d.y / 100) * H;
2606 |       var r = 10 + (d.y / 100) * 12;
2607 |       if (Math.hypot(mx-px, my-py) < r + 8) hit = { sid:sid, d:d, px:px, py:py };
2608 |     });
2609 |     if (hit) {
2610 |       tooltip.style.opacity = '1';
2611 |       tooltip.style.left = (hit.px + 16) + 'px';
2612 |       tooltip.style.top = (hit.py - 20) + 'px';
2613 |       tooltip.innerHTML = '<div style="color:' + hit.d.color + ';font-size:7px;letter-spacing:.15em;margin-bottom:3px;">' + STREAMS[hit.sid].label + '</div>'
2614 |         + '<div style="font-size:11px;font-weight:700;">' + hit.d.y + '/100</div>'
2615 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.5);margin-top:3px;">' + getLiveSubLabel(hit.sid) + '</div>'
2616 |         + '<div style="font-size:7px;color:rgba(255,255,255,0.3);margin-top:4px;">Click gauge above for full breakdown</div>';
2617 |     } else {
2618 |       tooltip.style.opacity = '0';
2619 |     }
2620 |   };
2621 |   canvas.onmouseleave = function() { tooltip.style.opacity = '0'; };
2622 | }
2623 | 
2624 | // ─── Signal board ────────────────────────────────────────────────────────────
2625 | function renderSignalBoard() {
2626 |   var board = document.getElementById('ss2-signal-board');
2627 |   if (!board) return;
2628 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {};
2629 |   var orb = liveData.orb || {}, streams = orb.streams || {};
2630 |   var inst = liveData.inst || {}, bills = liveData.bills || {};
2631 |   var exps = pac.fairshake_expenditures || [];
2632 | 
2633 |   var items = [
2634 |     // CRITICAL (red)
2635 |     { col:'#CC0000', label:'PAC CAPITAL · CRITICAL', text:'Fairshake PAC raised $' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M — largest crypto political operation in US history', val: '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M' },
2636 |     exps[0] ? { col:'#CC0000', label:'FAIRSHAKE · TOP EXPENDITURE', text:exps[0].candidate + ' — ' + (exps[0].support==='O'?'OPPOSE':'SUPPORT'), val: '$' + ((exps[0].amount||0)/1e6).toFixed(1) + 'M' } : null,
2637 |     // SIGNAL (orange)
2638 |     { col:'#f8c15c', label:'ON-CHAIN · SOPR SIGNAL', text:'SOPR at 0.15 — historical capitulation. Prior sub-0.2 episodes: avg +312% over 18 months', val: '0.15' },
2639 |     streams.hashrate >= 80 ? { col:'#f8c15c', label:'ON-CHAIN · HASHRATE', text:'Hashrate signal at ' + streams.hashrate + '/100 — miners holding, not selling into weakness', val: streams.hashrate + '/100' } : null,
2640 |     { col:'#f8c15c', label:'CONGRESS · IHX', text:'Insider Heat Index ' + (ihx.score||64) + '/100 — ' + (ihx.buy_count||0) + ' buys vs ' + (ihx.sell_count||0) + ' sells, ' + (ihx.crypto_trades||0) + ' crypto-adjacent', val: (ihx.score||64) + '/100' },
2641 |     { col:'#22c55e', label:'LEGISLATION · GENIUS ACT', text:'Passed Senate 66–32. Digital Asset Market Clarity at 69% congressional support. Regulatory moat forming.', val: '66–32' },
2642 |     (inst.total_institutional_filers||0) > 15 ? { col:'#22c55e', label:'INSTITUTIONAL · COALITION', text:((inst.coalition_summary||{}).count||0) + ' institutions in coordinated BTC ETF accumulation windows — ' + (inst.total_institutional_filers||0) + ' total 13F filers', val: (inst.total_institutional_filers||0) + ' filers' } : null,
2643 |     streams.whale >= 80 ? { col:'#22c55e', label:'ON-CHAIN · WHALE SIGNAL', text:'Whale accumulation signal at ' + streams.whale + '/100 — on-chain large wallet flows bullish', val: streams.whale + '/100' } : null,
2644 |     // NOTE (dim)
2645 |     { col:'rgba(255,255,255,0.3)', label:'GEO · FED RATE', text:'98.2% Polymarket probability of no rate change in April — macro tail risk removed for current cycle', val: '98.2%' },
2646 |     { col:'rgba(255,255,255,0.3)', label:'GEO · US STRATEGIC RESERVE', text:'Executive Order 14233 establishes national Bitcoin stockpile — sovereign demand signal', val: 'EO 14233' },
2647 |   ].filter(Boolean);
2648 | 
2649 |   board.innerHTML = items.map(function(item) {
2650 |     return '<div class="ss2-signal-item">'
2651 |       + '<div class="ss2-si-dot" style="background:' + item.col + ';box-shadow:0 0 4px ' + item.col + ';"></div>'
2652 |       + '<div class="ss2-si-body">'
2653 |       + '<div class="ss2-si-label" style="color:' + item.col + ';">' + item.label + '</div>'
2654 |       + '<div class="ss2-si-text">' + item.text + '</div>'
2655 |       + '</div>'
2656 |       + '<div class="ss2-si-val" style="color:' + item.col + ';">' + item.val + '</div>'
2657 |       + '</div>';
2658 |   }).join('');
2659 | }
2660 | 
2661 | // ─── Waterfall bars ───────────────────────────────────────────────────────────
2662 | function renderWaterfall() {
2663 |   var el = document.getElementById('ss2-waterfall-bars');
2664 |   if (!el) return;
2665 |   var totalScore = 0;
2666 |   streamOrder.forEach(function(id) { totalScore += (scores[id]||0); });
2667 |   var avg = totalScore / streamOrder.length;
2668 | 
2669 |   el.innerHTML = streamOrder.map(function(sid) {
2670 |     var score = scores[sid] || 50;
2671 |     var color = scoreToColor(score);
2672 |     var contrib = Math.round((score / totalScore) * 100);
2673 |     var pct = (score / 100) * 100;
2674 |     return '<div class="ss2-wf-col" onclick="(function(){var cell=document.getElementById(\'gc-\'+\'' + sid + '\');if(cell)cell.click();})();">'
2675 |       + '<div class="ss2-wf-bar-wrap"><div class="ss2-wf-bar" style="height:' + pct + '%;background:' + color + ';box-shadow:0 0 8px ' + color + '44;"></div></div>'
2676 |       + '<div class="ss2-wf-score" style="color:' + color + ';">' + score + '</div>'
2677 |       + '<div class="ss2-wf-label">' + STREAMS[sid].label + '</div>'
2678 |       + '<div class="ss2-wf-contrib">' + contrib + '% weight</div>'
2679 |       + '</div>';
2680 |   }).join('');
2681 | }
2682 | 
2683 | // ─── Init ────────────────────────────────────────────────────────────────────
2684 | // Set skeleton state on all gauge arcs before data arrives
2685 | streamOrder.forEach(function(id) {
2686 |   var arcEl = document.getElementById('ga-' + id);
2687 |   if (arcEl) arcEl.classList.add('skeleton');
2688 | });
2689 | fetchAll();
2690 | setInterval(fetchAll, 120000); // refresh every 2 min
2691 | 
2692 | // Close card when pressing Escape
2693 | document.addEventListener('keydown', function(e) {
2694 |   if (e.key === 'Escape') closeCard();
2695 | });
2696 | 
2697 | })();
2698 | </script>
2699 | 
2700 | 
2701 | <!-- ═══ TWO-ZONE LAYOUT: LEFT EVIDENCE + RIGHT INTEL RAIL ═══ -->
2702 | <div class="pn-main">
2703 |     <div class="pn-grid">
2704 | 
2705 |         <!-- ═══ LEFT MAIN (65%): EVIDENCE — DISCLOSURES + FLAGGED + CORRELATION ═══ -->
2706 |         <div class="pn-left-main">
2707 | 
2708 |         <!-- ═══ TIER 1: CONFIRMED DISCLOSURES ═══ -->
2709 |         <div class="pn-panel pn-tier-confirmed">
2710 |             <div class="pn-panel-head">
2711 |                 <span class="tier-dot"></span>
2712 |                 <span class="tier-label">TIER 1 — CONFIRMED</span>
2713 |                 <span class="pn-tier-badge tier-1">STOCK ACT</span>
2714 |                 <span class="tier-count">{{ data.disclosures|length }} FILED</span>
2715 |             </div>
2716 | 
2717 |             {% if not demo_mode and data.disclosures_live is defined and not data.disclosures_live %}
2718 |             <div class="pn-fallback-banner">
2719 |                 <strong>HISTORICAL DATA</strong> &mdash; Live data from efts.house.gov temporarily unavailable. Displaying documented public examples from {{ data.fallback_as_of|default('recent filings') }}.
2720 |             </div>
2721 |             {% endif %}
2722 | 
2723 |             <div id="pnDisclosures">
2724 |                 {% for d in data.disclosures %}
2725 |                 <div class="pn-disc-card" data-party="{{ d.party|default('') }}">
2726 |                     <div class="pn-disc-head">
2727 |                         <div class="pn-disc-entity">{{ d.entity }}</div>
2728 |                         {% if d.amount_range %}<span class="pn-disc-amount-tag">{{ d.amount_range }}</span>{% endif %}
2729 |                         {% if d.party %}
2730 |                         <span class="pn-disc-party {{ d.party }}">{{ d.party }}</span>
2731 |                         {% endif %}
2732 |                     </div>
2733 |                     <div class="pn-disc-fields">
2734 |                         <div>
2735 |                             <div class="pn-disc-field-label">Asset</div>
2736 |                             <div class="pn-disc-field-val asset-val">{{ d.asset }}</div>
2737 |                         </div>
2738 |                         <div>
2739 |                             <div class="pn-disc-field-label">Type</div>
2740 |                             <div class="pn-disc-field-val type-val {{ 'buy' if d.trade_type == 'purchase' else 'sell' if d.trade_type == 'sale' else '' }}">{{ d.trade_type|upper }}</div>
2741 |                         </div>
2742 |                         <div>
2743 |                             <div class="pn-disc-field-label">Amount</div>
2744 |                             <div class="pn-disc-field-val">{{ d.amount_range }}</div>
2745 |                         </div>
2746 |                         <div>
2747 |                             <div class="pn-disc-field-label">Filed</div>
2748 |                             <div class="pn-disc-field-val">{{ d.date_filed }}</div>
2749 |                         </div>
2750 |                         {% if d.get('days_to_file') %}
2751 |                         <div>
2752 |                             <div class="pn-disc-field-label">Days to File</div>
2753 |                             <div class="pn-disc-field-val">{{ d.days_to_file }}d</div>
2754 |                         </div>
2755 |                         {% endif %}
2756 |                         {% if d.get('committee') %}
2757 |                         <div>
2758 |                             <div class="pn-disc-field-label">Committee</div>
2759 |                             <div class="pn-disc-field-val">{{ d.committee }}</div>
2760 |                         </div>
2761 |                         {% endif %}
2762 |                     </div>
2763 |                     {% if d.get('conviction') and d.conviction.score > 0 %}
2764 |                     <div class="pn-conviction">
2765 |                         <span class="pn-conviction-label">CONVICTION</span>
2766 |                         <span class="pn-conviction-score {{ d.conviction.color }}">{{ d.conviction.score }}%</span>
2767 |                         <span class="pn-conviction-tag {{ d.conviction.color }}">{{ d.conviction.label }}</span>
2768 |                         <div class="pn-conviction-bar">
2769 |                             <div class="pn-conviction-bar-fill {{ d.conviction.color }}" style="width:{{ d.conviction.score }}%"></div>
2770 |                         </div>
2771 |                     </div>
2772 |                     {% endif %}
2773 |                     {% if d.get('correlation_note') %}
2774 |                     <div class="pn-disc-correlation">{{ d.correlation_note }}</div>
2775 |                     {% endif %}
2776 |                     {% if d.get('status') == 'loading' %}
2777 |                     <div style="margin-top:8px;">
2778 |                         <span class="pn-status-chip loading">Awaiting Live Data</span>
2779 |                     </div>
2780 |                     {% endif %}
2781 |                     <div class="pn-disc-source">
2782 |                         Source: <a href="{{ d.source_url }}" target="_blank" rel="noopener">Public Financial Disclosure</a>
2783 |                     </div>
2784 |                 </div>
2785 |                 {% endfor %}
2786 |                 {% if not data.disclosures %}
2787 |                 <div class="pn-empty">No crypto-related disclosures in current window</div>
2788 |                 {% endif %}
2789 |             </div>
2790 | 
2791 |             <!-- WATCH LIST -->
2792 |             {% if data.watch_list %}
2793 |             <div class="pn-section-label">TIER 3 — WATCH LIST</div>
2794 |             {% for w in data.watch_list %}
2795 |             <div class="pn-watchlist-item">
2796 |                 <div class="pn-watchlist-name">
2797 |                     {{ w.name }}
2798 |                     <span class="pn-disc-party {{ w.party }}" style="margin-left:4px;font-size:8px;">{{ w.party }}</span>
2799 |                 </div>
2800 |                 <div class="pn-watchlist-note">{{ w.note }}</div>
2801 |             </div>
2802 |             {% endfor %}
2803 |             {% endif %}
2804 |         </div>
2805 | 
2806 |         <!-- ═══ TIER 2: FLAGGED — PATTERN DETECTION ═══ -->
2807 |         <div class="pn-panel pn-tier-flagged">
2808 |             <div class="pn-panel-head">
2809 |                 <span class="tier-dot"></span>
2810 |                 <span class="tier-label">TIER 2 — FLAGGED</span>
2811 |                 <span class="pn-tier-badge tier-2">PATTERNS</span>
2812 |                 <span class="tier-count">{{ data.flagged|length }} DETECTED</span>
2813 |             </div>
2814 | 
2815 |             {% if demo_mode %}
2816 |             <div class="pn-classified-overlay">
2817 |                 <div class="pn-classified-stamp">CLASSIFIED</div>
2818 |                 <div class="pn-classified-sub">Commander Access Required</div>
2819 |                 <a href="/join" class="pn-upgrade-btn">Unlock Intelligence</a>
2820 |             </div>
2821 |             {% endif %}
2822 | 
2823 |             <div class="pn-disclaimer-note">
2824 |                 PATTERN FOR RESEARCH &mdash; NOT VERIFIED. Statistical correlations shown for independent research purposes only. These are computed patterns, not accusations.
2825 |             </div>
2826 | 
2827 |             <!-- Correlation Timeline SVG -->
2828 |             <div class="pn-section-label">CORRELATION TIMELINE</div>
2829 |             <div id="pnCorrelations">
2830 |                 {% for c in data.correlations %}
2831 |                 <div class="pn-corr-timeline" data-idx="{{ loop.index }}">
2832 |                     <!-- Gap indicator -->
2833 |                     {% set gap = c.get('gap_days', 0) %}
2834 |                     {% set gap_color = 'red' if gap < 7 else ('orange' if gap < 30 else 'white') %}
2835 |                     <div class="pn-corr-gap {{ c.get('gap_color', gap_color) }}">
2836 |                         {% if gap < 7 %}&#9888;{% elif gap < 30 %}&#9679;{% else %}&#9675;{% endif %}
2837 |                         {{ gap }} DAY GAP
2838 |                     </div>
2839 | 
2840 |                     <!-- SVG Timeline: Trade Date → Event Date -->
2841 |                     <svg width="100%" height="90" viewBox="0 0 500 90" preserveAspectRatio="xMidYMid meet">
2842 |                         <!-- Trade node -->
2843 |                         <g class="pn-corr-node" transform="translate(60,40)">
2844 |                             <circle r="10" fill="{{ '#ff3b5f' if gap < 7 else ('#f8c15c' if gap < 30 else '#fff') }}" opacity="0.9"/>
2845 |                             <text y="-16" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">TRADE</text>
2846 |                             <text y="28" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7">{{ c.disclosure.date[:10] if c.disclosure else '' }}</text>
2847 |                         </g>
2848 |                         <!-- Connecting line with gap label -->
2849 |                         <path class="pn-corr-path" d="M70,40 L230,40" stroke="{{ '#ff3b5f' if gap < 7 else ('#f8c15c' if gap < 30 else '#555') }}" stroke-width="2" style="animation-delay:0.2s"/>
2850 |                         <text x="150" y="32" text-anchor="middle" fill="{{ '#ff3b5f' if gap < 7 else '#f8c15c' }}" font-family="JetBrains Mono" font-size="10" font-weight="700">{{ gap }}d</text>
2851 |                         <!-- Event node -->
2852 |                         <g class="pn-corr-node" transform="translate(240,40)">
2853 |                             <circle r="10" fill="#fff" opacity="0.7"/>
2854 |                             <text y="-16" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">EVENT</text>
2855 |                         </g>
2856 |                         <!-- Score -->
2857 |                         <path class="pn-corr-path" d="M250,40 L400,40" stroke="var(--pn-gold)" stroke-width="1.5" style="animation-delay:0.6s"/>
2858 |                         <g class="pn-corr-node" transform="translate(420,40)">
2859 |                             <circle r="14" fill="none" stroke="{{ '#ff3b5f' if c.correlation_score > 0.8 else '#f8c15c' }}" stroke-width="2" opacity="0.8"/>
2860 |                             <text y="4" text-anchor="middle" fill="{{ '#ff3b5f' if c.correlation_score > 0.8 else '#f8c15c' }}" font-family="JetBrains Mono" font-size="10" font-weight="700">{{ "%.0f"|format(c.correlation_score * 100) }}%</text>
2861 |                             <text y="28" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">SCORE</text>
2862 |                         </g>
2863 |                     </svg>
2864 | 
2865 |                     <div class="pn-corr-summary">{{ c.timeline_summary }}</div>
2866 | 
2867 |                     <div>
2868 |                         {% if c.disclosure %}
2869 |                         <div class="pn-corr-event-row">
2870 |                             <span class="pn-corr-event-tag disclosure">DISCLOSURE</span>
2871 |                             {{ c.disclosure.entity }} &mdash; {{ c.disclosure.asset }} ({{ c.disclosure.trade_type }})
2872 |                         </div>
2873 |                         {% endif %}
2874 |                         {% for w in c.related_whales %}
2875 |                         <div class="pn-corr-event-row">
2876 |                             <span class="pn-corr-event-tag whale">WHALE</span>
2877 |                             {{ w.entity }} &mdash; {{ w.amount }} {{ w.direction }}
2878 |                         </div>
2879 |                         {% endfor %}
2880 |                         {% for g in c.related_geo %}
2881 |                         <div class="pn-corr-event-row">
2882 |                             <span class="pn-corr-event-tag geo">GEO</span>
2883 |                             {{ g.headline[:80] }}{% if g.headline|length > 80 %}...{% endif %}
2884 |                         </div>
2885 |                         {% endfor %}
2886 |                     </div>
2887 | 
2888 |                     {% if not demo_mode %}
2889 |                     <button class="pn-btc-case-btn" onclick="makeBitcoinCase(this, '{{ c.timeline_summary|e }}')" data-idx="{{ loop.index }}">
2890 |                         &#x20BF; Make the Bitcoin Case
2891 |                     </button>
2892 |                     <div class="pn-btc-case-output" id="btcCase{{ loop.index }}"></div>
2893 |                     {% endif %}
2894 |                 </div>
2895 |                 {% endfor %}
2896 |                 {% if not data.correlations %}
2897 |                 <div class="pn-empty">Awaiting correlated events...</div>
2898 |                 {% endif %}
2899 |             </div>
2900 | 
2901 |             <!-- Flagged Trades -->
2902 |             <div class="pn-section-label">FLAGGED TRADES</div>
2903 |             {% for f in data.flagged %}
2904 |             <div class="pn-disc-card" style="border-left-color:var(--pn-gold);">
2905 |                 <div class="pn-disc-head">
2906 |                     <div class="pn-disc-entity">{{ f.entity }}</div>
2907 |                     {% if f.party %}
2908 |                     <span class="pn-disc-party {{ f.party }}">{{ f.party }}</span>
2909 |                     {% endif %}
2910 |                 </div>
2911 |                 <div class="pn-disc-fields">
2912 |                     <div>
2913 |                         <div class="pn-disc-field-label">Asset</div>
2914 |                         <div class="pn-disc-field-val">{{ f.asset }}</div>
2915 |                     </div>
2916 |                     <div>
2917 |                         <div class="pn-disc-field-label">Score</div>
2918 |                         <div class="pn-disc-field-val" style="color:var(--pn-gold)">{{ "%.0f"|format(f.correlation_score * 100) }}%</div>
2919 |                     </div>
2920 |                 </div>
2921 |                 <div class="pn-disc-correlation" style="border-color:rgba(248,193,92,0.15);color:var(--pn-gold);">{{ f.flag_reason }}</div>
2922 |             </div>
2923 |             {% endfor %}
2924 |             {% if not data.flagged %}
2925 |             <div class="pn-empty">No statistical patterns detected in current window</div>
2926 |             {% endif %}
2927 |         </div>
2928 | 
2929 |         </div><!-- end .pn-left-main -->
2930 | 
2931 |         <!-- ═══ RIGHT RAIL (35%): INTEL — SIGNALS + MARKETS + GEO ═══ -->
2932 |         <div class="pn-right-rail">
2933 |         <div class="pn-panel pn-tier-feed">
2934 |             <div class="pn-panel-head">
2935 |                 <span class="tier-dot"></span>
2936 |                 <span class="tier-label">REAL-TIME FEED</span>
2937 |                 <span class="tier-count">WHALE + MARKET + GEO</span><span style="display:inline-flex;align-items:center;gap:5px;margin-left:10px;"><span id="pnStreamDot" style="width:7px;height:7px;border-radius:50%;background:#888;display:inline-block;"></span><span id="pnStreamLabel" style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.12em;color:#888;">CONNECTING</span></span>
2938 |             </div>
2939 | 
2940 |             <!-- Whale Tracker -->
2941 |             <div class="pn-section-label">WHALE TRACKER</div>
2942 |             <div id="pnWhales">
2943 |                 {% for w in data.whales %}
2944 |                 <div class="pn-whale-item {{ w.tx_type }}">
2945 |                     <div class="pn-whale-row">
2946 |                         <div class="pn-whale-entity">{{ w.entity }}</div>
2947 |                         <span class="pn-whale-type-tag {{ w.tx_type }}">{{ w.tx_type|upper }}</span>
2948 |                         {% if w.get('flow_signal') %}
2949 |                         <span class="pn-whale-signal-tag {{ w.flow_signal }}">{{ w.flow_signal|upper }}</span>
2950 |                         {% endif %}
2951 |                     </div>
2952 |                     <div class="pn-whale-amt {{ w.tx_type }}">
2953 |                         {% if w.tx_type == 'inflow' %}+{% else %}-{% endif %}{{ w.amount_btc }} BTC
2954 |                     </div>
2955 |                     {% if w.amount_usd %}
2956 |                     <div class="pn-whale-usd">${{ "{:,.0f}".format(w.amount_usd) }} USD</div>
2957 |                     {% endif %}
2958 |                     {% if w.get('flow_context') %}
2959 |                     <div class="pn-whale-flow {{ w.flow_signal|default('neutral') }}">
2960 |                         <div class="pn-whale-flow-label">{{ w.flow_label|default('TRANSFER') }}</div>
2961 |                         {{ w.flow_context }}
2962 |                     </div>
2963 |                     {% endif %}
2964 |                     <div class="pn-whale-size-bar" style="width:{{ [w.amount_btc / 10, 100]|min }}%"></div>
2965 |                     <div class="pn-whale-meta">
2966 |                         <span>{{ w.address }}</span>
2967 |                         <a href="{{ w.source_url }}" target="_blank" rel="noopener">View TX &rarr;</a>
2968 |                     </div>
2969 |                 </div>
2970 |                 {% endfor %}
2971 |                 {% if not data.whales %}
2972 |                 <div class="pn-loading">
2973 |                     <div class="pn-loading-dot"></div>
2974 |                     <div class="pn-loading-dot"></div>
2975 |                     <div class="pn-loading-dot"></div>
2976 |                     Scanning whale wallets...
2977 |                 </div>
2978 |                 {% endif %}
2979 |             </div>
2980 | 
2981 |             <!-- Polymarket -->
2982 |             <div class="pn-section-label">BITCOIN PREDICTION MARKETS</div>
2983 |             <div id="pnPolymarket">
2984 |                 {% if data.polymarket %}
2985 |                 <!-- Hero market: highest volume -->
2986 |                 {% set hero = data.polymarket[0] %}
2987 |                 <div class="pn-poly-hero">
2988 |                     {% if hero.get('event_title') %}
2989 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--pn-gold);margin-bottom:6px;">TOP MARKET</div>
2990 |                     {% endif %}
2991 |                     <div class="pn-poly-question">{{ hero.question }}</div>
2992 |                     <div class="pn-poly-row">
2993 |                         {% if hero.yes_price %}
2994 |                         <span class="pn-poly-pct">{{ hero.yes_price }}%</span>
2995 |                         <span class="pn-poly-yes">YES</span>
2996 |                         {% else %}
2997 |                         <span class="pn-poly-pct" style="color:var(--pn-muted)">--</span>
2998 |                         {% endif %}
2999 |                         <span class="pn-poly-signal {{ hero.btc_signal }}">
3000 |                             {% if hero.btc_signal == 'bullish' %}&#9650;{% elif hero.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
3001 |                             {{ hero.btc_signal|upper }}
3002 |                         </span>
3003 |                     </div>
3004 |                     {% if hero.yes_price %}
3005 |                     <div class="pn-poly-hero-bar">
3006 |                         <div class="pn-poly-hero-bar-fill" style="width:{{ hero.yes_price }}%"></div>
3007 |                     </div>
3008 |                     {% endif %}
3009 |                     <div class="pn-poly-meta">
3010 |                         {% if hero.volume %}<span class="pn-poly-vol-badge">${{ "{:,.0f}".format(hero.volume) }} TOTAL VOL</span>{% endif %}
3011 |                         {% if hero.volume_24h %}<span>${{ "{:,.0f}".format(hero.volume_24h) }} 24h</span>{% endif %}
3012 |                         {% if hero.end_date %}<span>Expires {{ hero.end_date[:10] }}</span>{% endif %}
3013 |                         {% if hero.source_url %}<a href="{{ hero.source_url }}" target="_blank" rel="noopener">Polymarket &rarr;</a>{% endif %}
3014 |                     </div>
3015 |                 </div>
3016 | 
3017 |                 <!-- Remaining markets -->
3018 |                 {% for p in data.polymarket[1:] %}
3019 |                 <div class="pn-poly-item">
3020 |                     <div class="pn-poly-question">{{ p.question }}</div>
3021 |                     <div class="pn-poly-row">
3022 |                         {% if p.yes_price %}
3023 |                         <span class="pn-poly-pct">{{ p.yes_price }}%</span>
3024 |                         <span class="pn-poly-yes">YES</span>
3025 |                         {% else %}
3026 |                         <span class="pn-poly-pct" style="color:var(--pn-muted)">--</span>
3027 |                         {% endif %}
3028 |                         <span class="pn-poly-signal {{ p.btc_signal }}">
3029 |                             {% if p.btc_signal == 'bullish' %}&#9650;{% elif p.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
3030 |                             {{ p.btc_signal|upper }}
3031 |                         </span>
3032 |                     </div>
3033 |                     {% if p.yes_price %}
3034 |                     <div class="pn-poly-bar">
3035 |                         <div class="pn-poly-bar-fill {{ p.btc_signal }}" style="width:{{ p.yes_price }}%"></div>
3036 |                     </div>
3037 |                     {% endif %}
3038 |                     <div class="pn-poly-meta">
3039 |                         {% if p.volume %}<span>${{ "{:,.0f}".format(p.volume) }} vol</span>{% endif %}
3040 |                         {% if p.volume_24h %}<span>${{ "{:,.0f}".format(p.volume_24h) }} 24h</span>{% endif %}
3041 |                         {% if p.end_date %}<span>Expires {{ p.end_date[:10] }}</span>{% endif %}
3042 |                         {% if p.source_url %}<a href="{{ p.source_url }}" target="_blank" rel="noopener">Polymarket &rarr;</a>{% endif %}
3043 |                     </div>
3044 |                 </div>
3045 |                 {% endfor %}
3046 |                 {% else %}
3047 |                 <div class="pn-loading">
3048 |                     <div class="pn-loading-dot"></div>
3049 |                     <div class="pn-loading-dot"></div>
3050 |                     <div class="pn-loading-dot"></div>
3051 |                     Fetching prediction markets...
3052 |                 </div>
3053 |                 {% endif %}
3054 |             </div>
3055 | 
3056 |             <!-- Nation-State / Forex -->
3057 |             {% if data.forex %}
3058 |             <div class="pn-section-label">NATION-STATE SIGNALS</div>
3059 |             <div id="pnForex">
3060 |                 {% for f in data.forex %}
3061 |                 <div class="pn-forex-item">
3062 |                     <span class="pn-forex-pair">{{ f.pair }}</span>
3063 |                     {% if f.rate %}<span class="pn-forex-rate">{{ f.rate }}</span>{% endif %}
3064 |                 </div>
3065 |                 {% endfor %}
3066 |             </div>
3067 |             {% endif %}
3068 | 
3069 |             <!-- Geopolitical Feed -->
3070 |             <div class="pn-section-label">GEOPOLITICAL ALERT FEED</div>
3071 |             <div id="pnGeo">
3072 |                 {% for g in data.geopolitical %}
3073 |                 <div class="pn-geo-item">
3074 |                     <div class="pn-geo-headline">{{ g.headline }}</div>
3075 |                     <span class="pn-geo-signal-tag {{ g.btc_signal }}">
3076 |                         {% if g.btc_signal == 'bullish' %}&#9650;{% elif g.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
3077 |                         BTC {{ g.btc_signal|upper }}
3078 |                     </span>
3079 |                     <div class="pn-geo-rationale">{{ g.btc_rationale }}</div>
3080 |                     <div class="pn-geo-meta">
3081 |                         <span>{{ g.source }}</span>
3082 |                         <span>{{ g.timestamp[:10] if g.timestamp else '' }}</span>
3083 |                     </div>
3084 |                 </div>
3085 |                 {% endfor %}
3086 |                 {% if not data.geopolitical %}
3087 |                 <div class="pn-empty">No geopolitical signals in current window</div>
3088 |                 {% endif %}
3089 |             </div>
3090 | 
3091 |             <!-- Political Donation Pulse -->
3092 |             <div class="pn-section-label">POLITICAL DONATION PULSE</div>
3093 |             <div id="pnDonations" style="padding:12px;">
3094 |                 <div style="color:rgba(255,255,255,0.15);font-size:9px;font-family:'JetBrains Mono',monospace;padding:4px 0;">Loading PAC intelligence...</div>
3095 |             <!-- ═══ PRIVATE EQUITY & INSTITUTIONAL INTELLIGENCE ═══ -->
3096 |             <div class="pn-section-label">INSTITUTIONAL ACCUMULATION</div>
3097 |             <div id="pnInstitutional" style="padding:8px 12px;">
3098 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">
3099 |                     Loading institutional data...
3100 |                 </div>
3101 |             </div>
3102 | 
3103 |             <!-- Coalition Detected Banner (hidden until data loads) -->
3104 |             <div id="pnCoalitionBanner" style="display:none;margin:0 12px 8px;padding:10px 14px;
3105 |                 background:rgba(204,0,0,0.1);border:1px solid rgba(204,0,0,0.4);border-radius:6px;">
3106 |                 <div style="display:flex;align-items:center;gap:8px;">
3107 |                     <div style="width:8px;height:8px;border-radius:50%;background:#cc0000;
3108 |                         animation:pn-pulse 1s ease-in-out infinite;flex-shrink:0;"></div>
3109 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
3110 |                         letter-spacing:.15em;color:#cc0000;font-weight:700;">COALITION SIGNAL DETECTED</div>
3111 |                 </div>
3112 |                 <div id="pnCoalitionNote" style="font-family:'DM Sans',sans-serif;font-size:11px;
3113 |                     color:rgba(255,255,255,0.7);margin-top:6px;line-height:1.5;"></div>
3114 |             </div>
3115 | 
3116 |             <div class="pn-section-label">PRIVATE EQUITY DATASTREAM</div>
3117 |             <div id="pnPEDatastream" style="padding:8px 12px;">
3118 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">
3119 |                     Loading PE fundraising data...
3120 |                 </div>
3121 |             </div>
3122 | 
3123 | 
3124 |             <!-- ═══ BITCOIN BILL GAP TRACKER ═══ -->
3125 |             <div class="pn-section-label" style="display:flex;justify-content:space-between;align-items:center;">
3126 |                 <span>BITCOIN BILL TRACKER</span>
3127 |                 <span style="font-family:'JetBrains Mono',monospace;font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:.08em;">Source: LegiScan · CC BY 4.0</span>
3128 |             </div>
3129 |             <div id="pnBillTracker" style="padding:8px 12px;">
3130 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">Loading congressional bill data...</div>
3131 |             </div>
3132 | 
3133 |             <!-- Congressional Trading — STOCK Act -->
3134 |             <div class="pn-section-label" style="display:flex;justify-content:space-between;align-items:center;"><span>CONGRESSIONAL STOCK TRADES</span><span id="pnLastUpdate" style="font-family:'JetBrains Mono',monospace;font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:.06em;"></span></div>
3135 |             <div id="pnCongress" style="padding:8px 12px;">
3136 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Loading STOCK Act filings...</div>
3137 |             </div>
3138 | 
3139 |             <!-- Party Breakdown -->
3140 |             <div class="pn-section-label">PARTY TRADING BREAKDOWN</div>
3141 |             <div id="pnPartyBreakdown" style="padding:8px 12px;">
3142 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Analyzing party patterns...</div>
3143 |             </div>
3144 | 
3145 |             <!-- IHX Score -->
3146 |             <div class="pn-section-label">INSIDER HEAT INDEX (IHX)</div>
3147 |             <div id="pnIHX" style="padding:12px;">
3148 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Computing insider heat...</div>
3149 |             </div>
3150 | 
3151 |                     </div>
3152 |                     <div>
3153 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;color:var(--pn-white);" id="donCommittees">--</div>
3154 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--pn-muted);margin-top:4px;">CRYPTO COMMITTEES</div>
3155 |                     </div>
3156 |                     <div>
3157 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;color:var(--pn-gold);" id="donStates">--</div>
3158 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--pn-muted);margin-top:4px;">STATES ACTIVE</div>
3159 |                     </div>
3160 |                 </div>
3161 |                 <div style="margin-top:12px;text-align:center;">
3162 |                     <span id="donLabel" style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:2px;padding:4px 12px;border:1px solid var(--pn-border);background:rgba(255,59,95,0.04);color:var(--pn-muted);">LOADING</span>
3163 |                 </div>
3164 |             </div>
3165 |         </div>
3166 |         </div><!-- end .pn-right-rail -->
3167 | 
3168 |     </div>
3169 | </div>
3170 | 
3171 | 
3172 | 
3173 | 
3174 | <!-- ═══ HISTORICAL PRECEDENTS TIMELINE (GLASSMORPHIC) ═══ -->
3175 | <div class="pn-history">
3176 |     <div class="pn-history-header">HISTORICAL PRECEDENTS</div>
3177 |     <div class="pn-history-subhead">Documented cases of government financial overreach — the pattern Bitcoin was engineered to break.</div>
3178 | 
3179 |     <div class="pn-timeline-scroll">
3180 |         <div class="pn-timeline" id="pn-timeline">
3181 | 
3182 |             <!-- 1: 60 AD — Roman Coin Debasement (ABOVE) -->
3183 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3184 |                 <div class="pn-tl-year">60 AD</div>
3185 |                 <div class="pn-tl-name">Roman Coin Debasement</div>
3186 |                 <div class="pn-tl-stem"></div>
3187 |                 <div class="pn-tl-dot" data-evt="0" onclick="tlToggle(this)"></div>
3188 |             </div>
3189 | 
3190 |             <!-- 2: 1544 — Henry VIII (BELOW) -->
3191 |             <div class="pn-tl-node tl-below" style="margin-right:40px">
3192 |                 <div class="pn-tl-dot" data-evt="1" onclick="tlToggle(this)"></div>
3193 |                 <div class="pn-tl-stem"></div>
3194 |                 <div class="pn-tl-year">1544</div>
3195 |                 <div class="pn-tl-name">Henry VIII Great Debasement</div>
3196 |             </div>
3197 | 
3198 |             <!-- 3: 1789 — French Assignats (ABOVE) -->
3199 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3200 |                 <div class="pn-tl-year">1789</div>
3201 |                 <div class="pn-tl-name">French Assignat Hyperinflation</div>
3202 |                 <div class="pn-tl-stem"></div>
3203 |                 <div class="pn-tl-dot" data-evt="2" onclick="tlToggle(this)"></div>
3204 |             </div>
3205 | 
3206 |             <!-- 4: 1921 — Weimar (BELOW) -->
3207 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3208 |                 <div class="pn-tl-dot" data-evt="3" onclick="tlToggle(this)"></div>
3209 |                 <div class="pn-tl-stem"></div>
3210 |                 <div class="pn-tl-year">1921</div>
3211 |                 <div class="pn-tl-name">Weimar Hyperinflation</div>
3212 |             </div>
3213 | 
3214 |             <!-- 5: 1933 — FDR Gold Seizure (ABOVE) -->
3215 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3216 |                 <div class="pn-tl-year">1933</div>
3217 |                 <div class="pn-tl-name">FDR Gold Seizure</div>
3218 |                 <div class="pn-tl-stem"></div>
3219 |                 <div class="pn-tl-dot" data-evt="4" onclick="tlToggle(this)"></div>
3220 |             </div>
3221 | 
3222 |             <!-- 6: 1944 — Bretton Woods (BELOW) -->
3223 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3224 |                 <div class="pn-tl-dot" data-evt="5" onclick="tlToggle(this)"></div>
3225 |                 <div class="pn-tl-stem"></div>
3226 |                 <div class="pn-tl-year">1944</div>
3227 |                 <div class="pn-tl-name">Bretton Woods Dollar Peg</div>
3228 |             </div>
3229 | 
3230 |             <!-- 7: 1946 — Hungary (ABOVE) -->
3231 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3232 |                 <div class="pn-tl-year">1946</div>
3233 |                 <div class="pn-tl-name">Hungarian Hyperinflation</div>
3234 |                 <div class="pn-tl-stem"></div>
3235 |                 <div class="pn-tl-dot" data-evt="6" onclick="tlToggle(this)"></div>
3236 |             </div>
3237 | 
3238 |             <!-- 8: 1971 — Nixon Shock (BELOW) -->
3239 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3240 |                 <div class="pn-tl-dot" data-evt="7" onclick="tlToggle(this)"></div>
3241 |                 <div class="pn-tl-stem"></div>
3242 |                 <div class="pn-tl-year">1971</div>
3243 |                 <div class="pn-tl-name">Nixon Shock</div>
3244 |             </div>
3245 | 
3246 |             <!-- 9: 1980s — S&L Crisis (ABOVE) -->
3247 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3248 |                 <div class="pn-tl-year">1980s</div>
3249 |                 <div class="pn-tl-name">S&amp;L Crisis</div>
3250 |                 <div class="pn-tl-stem"></div>
3251 |                 <div class="pn-tl-dot" data-evt="8" onclick="tlToggle(this)"></div>
3252 |             </div>
3253 | 
3254 |             <!-- 10: 2001 — Argentina (BELOW) -->
3255 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3256 |                 <div class="pn-tl-dot" data-evt="9" onclick="tlToggle(this)"></div>
3257 |                 <div class="pn-tl-stem"></div>
3258 |                 <div class="pn-tl-year">2001</div>
3259 |                 <div class="pn-tl-name">Argentina Corralito</div>
3260 |             </div>
3261 | 
3262 |             <!-- 11: 2008 — GFC Bailouts (ABOVE) -->
3263 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3264 |                 <div class="pn-tl-year">2008</div>
3265 |                 <div class="pn-tl-name">Global Financial Crisis</div>
3266 |                 <div class="pn-tl-stem"></div>
3267 |                 <div class="pn-tl-dot" data-evt="10" onclick="tlToggle(this)"></div>
3268 |             </div>
3269 | 
3270 |             <!-- 12: 2013 — Cyprus (BELOW) -->
3271 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3272 |                 <div class="pn-tl-dot" data-evt="11" onclick="tlToggle(this)"></div>
3273 |                 <div class="pn-tl-stem"></div>
3274 |                 <div class="pn-tl-year">2013</div>
3275 |                 <div class="pn-tl-name">Cyprus Bail-In</div>
3276 |             </div>
3277 | 
3278 |             <!-- 13: 2016 — India (ABOVE) -->
3279 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3280 |                 <div class="pn-tl-year">2016</div>
3281 |                 <div class="pn-tl-name">India Demonetization</div>
3282 |                 <div class="pn-tl-stem"></div>
3283 |                 <div class="pn-tl-dot" data-evt="12" onclick="tlToggle(this)"></div>
3284 |             </div>
3285 | 
3286 |             <!-- 14: 2020 — COVID (BELOW) -->
3287 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3288 |                 <div class="pn-tl-dot" data-evt="13" onclick="tlToggle(this)"></div>
3289 |                 <div class="pn-tl-stem"></div>
3290 |                 <div class="pn-tl-year">2020</div>
3291 |                 <div class="pn-tl-name">COVID Money Printing</div>
3292 |             </div>
3293 | 
3294 |             <!-- 15: 2022 — Russia SWIFT (ABOVE) -->
3295 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3296 |                 <div class="pn-tl-year">2022</div>
3297 |                 <div class="pn-tl-name">Russia SWIFT Exclusion</div>
3298 |                 <div class="pn-tl-stem"></div>
3299 |                 <div class="pn-tl-dot" data-evt="14" onclick="tlToggle(this)"></div>
3300 |             </div>
3301 | 
3302 |             <!-- 16: 2022 — Canada Truckers (BELOW) -->
3303 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3304 |                 <div class="pn-tl-dot" data-evt="15" onclick="tlToggle(this)"></div>
3305 |                 <div class="pn-tl-stem"></div>
3306 |                 <div class="pn-tl-year">2022</div>
3307 |                 <div class="pn-tl-name">Canada Trucker Freeze</div>
3308 |             </div>
3309 | 
3310 |             <!-- 17: 2023 — US Banking (ABOVE) -->
3311 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3312 |                 <div class="pn-tl-year">2023</div>
3313 |                 <div class="pn-tl-name">U.S. Banking Crisis</div>
3314 |                 <div class="pn-tl-stem"></div>
3315 |                 <div class="pn-tl-dot" data-evt="16" onclick="tlToggle(this)"></div>
3316 |             </div>
3317 | 
3318 |             <!-- 18: NOW — CBDC (BELOW) -->
3319 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3320 |                 <div class="pn-tl-dot" data-evt="17" onclick="tlToggle(this)"></div>
3321 |                 <div class="pn-tl-stem"></div>
3322 |                 <div class="pn-tl-year">NOW</div>
3323 |                 <div class="pn-tl-name">CBDC Push</div>
3324 |             </div>
3325 | 
3326 |         </div>
3327 |     </div>
3328 | 
3329 |     <div class="pn-history-coda">
3330 |         WHY HISTORY MATTERS — These are not conspiracy theories. These are documented events. Bitcoin was built to prevent them.
3331 |     </div>
3332 | </div>
3333 | 
3334 | <!-- Glassmorphic info card (single, repositioned on click) -->
3335 | <div class="pn-tl-card" id="pn-tl-card">
3336 |     <button class="pn-tl-card-close" onclick="tlClose()">&times;</button>
3337 |     <div class="pn-tl-card-header" id="tlCardHeader"></div>
3338 |     <div class="pn-tl-card-short" id="tlCardShort"></div>
3339 |     <div class="pn-tl-card-detail" id="tlCardDetail"></div>
3340 |     <div class="pn-tl-card-btc" id="tlCardBtc"></div>
3341 | </div>
3342 | 
3343 | <script>
3344 | (function(){
3345 | var TL_EVENTS=[
3346 | {year:"60 AD",title:"Roman Coin Debasement",short:"Nero reduces silver content from 90% to near 0% over centuries. Denarius becomes copper-clad.",detail:"Roman emperors starting with Nero systematically reduced silver content in the denarius from ~90% to under 5% to fund wars and government spending. By the Crisis of the Third Century (235\u2013284 AD), 26 emperors ruled in 49 years as the currency collapsed and hyperinflation took hold. The pattern: spend beyond means, debase the money, watch civilization fracture.",btc:"\u26a1 BITCOIN PARALLEL: 21 million coins. No emperor can change that."},
3347 | {year:"1544",title:"Henry VIII Great Debasement",short:"England\u2019s king secretly reduces gold/silver in coins to fund wars. Coins dubbed \u2018Old Coppernose.\u2019",detail:"King Henry VIII reduced gold content from 23 to 20 karat and silver content to just 25% (rest copper) to fund wars with France and Scotland and his lifestyle. Citizens noticed when the copper showed through the silver on the king\u2019s portrait \u2014 the nose turned copper first. Result: Severe inflation, erosion of trust, economic damage lasting decades until reversed by Elizabeth I in 1560.",btc:"\u26a1 BITCOIN PARALLEL: Cryptographically verified. No hidden copper."},
3348 | {year:"1789",title:"French Assignat Hyperinflation",short:"Revolutionary France prints paper money backed by seized church land. Massive over-issue destroys savings.",detail:"The revolutionary government issued paper \u2018assignats\u2019 backed by confiscated church lands, then printed them without restraint to fund wars and deficits. Total issuance: 45 billion livres. Result: Hyperinflation wiped out the middle class, triggered food riots, and contributed to the Reign of Terror. The paper money became so worthless it was burned for heat.",btc:"\u26a1 BITCOIN PARALLEL: Cannot be printed. Supply is fixed at genesis."},
3349 | {year:"1921",title:"Weimar Republic Hyperinflation",short:"Germany prints trillions of marks to pay WWI reparations. A loaf of bread costs 200 billion marks by 1923.",detail:"The German government printed money to pay WWI war reparations imposed by the Treaty of Versailles. By November 1923, a single loaf of bread cost 200 billion marks. Citizens carried cash in wheelbarrows. Middle-class savings were completely destroyed. The resulting economic chaos and resentment directly enabled the rise of extremism. The Reichsbank printed notes so fast new denominations were issued daily.",btc:"\u26a1 BITCOIN PARALLEL: No central bank. No war reparations. 21 million."},
3350 | {year:"1933",title:"FDR Gold Seizure",short:"Executive Order 6102 forces citizens to surrender gold. Penalty: 10 years prison or $10,000 fine.",detail:"President Roosevelt signed Executive Order 6102 requiring all U.S. persons to deliver their gold coins, bullion, and certificates to Federal Reserve banks at $20.67/oz. Days later, the government revalued gold to $35/oz \u2014 an immediate 41% wealth transfer from citizens to the state. Noncompliance carried criminal penalties of up to 10 years imprisonment. This was not a purchase \u2014 it was confiscation.",btc:"\u26a1 BITCOIN PARALLEL: Stored in your head as 12 words. No EO can seize a seed phrase."},
3351 | {year:"1944",title:"Bretton Woods Dollar Peg",short:"USD becomes global reserve currency backed by gold. Seeds Nixon Shock 27 years later.",detail:"44 nations signed the Bretton Woods Agreement making the USD the world reserve currency pegged at $35/oz gold. The U.S. promised to maintain convertibility. For 27 years, the system worked \u2014 until the U.S. printed more dollars than it had gold to back them, setting the stage for Nixon\u2019s 1971 unilateral break.",btc:"\u26a1 BITCOIN PARALLEL: No central peg. No promise of convertibility. It just works."},
3352 | {year:"1946",title:"Hungarian Hyperinflation",short:"Worst hyperinflation in recorded history. Prices doubled every 15 hours. Currency abandoned entirely.",detail:"Post-WWII Hungary experienced the most extreme hyperinflation ever recorded. The Hungarian peng\u0151 lost all value \u2014 at peak, prices doubled every 15.6 hours. The government printed a 100 quintillion peng\u0151 note. Total currency abandoned. A new currency (forint) was introduced, but savings were destroyed absolutely. Workers were paid daily and ran to spend before prices doubled again.",btc:"\u26a1 BITCOIN PARALLEL: Cannot be inflated. Ever."},
3353 | {year:"1971",title:"Nixon Shock",short:"Nixon ends gold convertibility \u2018temporarily.\u2019 54 years later, still temporary.",detail:"On August 15, 1971, President Nixon unilaterally terminated USD convertibility to gold, ending the Bretton Woods system. He called it \u2018temporary.\u2019 Every dollar since has been backed only by government debt. The result: USD has lost 85%+ of its purchasing power since 1971. The move enabled unlimited government spending backed by nothing but future tax obligations and the threat of military force.",btc:"\u26a1 BITCOIN PARALLEL: Born the day Satoshi embedded the bank bailout headline in the genesis block."},
3354 | {year:"1980s",title:"U.S. Savings & Loan Crisis",short:"1,000+ S&Ls fail after deregulation. $160 billion taxpayer bailout. First major \u2018too big to fail.\u2019",detail:"Deregulation of the savings and loan industry combined with government-backed deposit insurance led to reckless lending and outright fraud at over 1,000 institutions. When they failed, taxpayers were forced to cover losses of $124\u2013160 billion. The S&L crisis established the template: privatize profits, socialize losses. Executives faced minimal consequences.",btc:"\u26a1 BITCOIN PARALLEL: No deposit insurance needed. Not your keys, not your coins \u2014 but if it is your keys, no bailout required."},
3355 | {year:"2001",title:"Argentina Corralito",short:"Bank accounts frozen. USD deposits forcibly converted to devalued pesos. Riots in the streets.",detail:"After pegging the peso to the USD, Argentina\u2019s government froze all bank accounts (the \u2018corralito\u2019) limiting withdrawals to $250/week. When the peg broke, USD deposits were forcibly converted to pesos at a rate that immediately lost 70% of value \u2014 wiping out savings overnight. Multiple presidents resigned in weeks. Riots killed dozens. Argentina defaulted on $100 billion in debt.",btc:"\u26a1 BITCOIN PARALLEL: Your wallet. Your keys. No bank holiday can freeze a UTXO."},
3356 | {year:"2008",title:"Global Financial Crisis Bailouts",short:"TARP: $700B. Total Fed backstop: $29 trillion. Banks rescued. Homeowners foreclosed.",detail:"The U.S. government passed TARP ($700B+) and the Federal Reserve provided up to $29 trillion in emergency backstops to rescue banks, AIG, Fannie Mae, Freddie Mac, and the auto industry after the subprime mortgage collapse. While institutions deemed \u2018too big to fail\u2019 were rescued, 10 million Americans lost their homes to foreclosure. The genesis block of Bitcoin was mined January 3, 2009 \u2014 with a newspaper headline about bank bailouts embedded as a timestamp.",btc:"\u26a1 BITCOIN PARALLEL: The genesis block timestamp: \u2018Chancellor on brink of second bailout for banks.\u2019 Satoshi saw this coming."},
3357 | {year:"2013",title:"Cyprus Bail-In",short:"EU forces haircut of 47.5% on deposits over \u20ac100,000. First direct bank account confiscation in modern Europe.",detail:"The European Union forced Cyprus to impose a \u2018bail-in\u2019 as a condition of a \u20ac10B rescue \u2014 directly seizing up to 47.5% of bank deposits over \u20ac100,000. This was the first time in modern history that EU governments explicitly took depositor money to rescue a bank. It established the legal template that deposits are not cash \u2014 they are unsecured loans to the bank.",btc:"\u26a1 BITCOIN PARALLEL: People who held BTC were not subject to the bail-in."},
3358 | {year:"2016",title:"India Demonetization",short:"86% of all currency invalidated overnight. Chaos, queues, economic disruption. Affected 1.3 billion people.",detail:"Indian Prime Minister Modi announced with 4 hours notice that \u20b9500 and \u20b91,000 notes \u2014 86% of all currency in circulation \u2014 were immediately invalid. Citizens had weeks to exchange limited amounts. Result: Cash chaos, severe disruption to the informal economy (which employs 90% of Indians), GDP growth slowed, and the stated goal of eliminating \u2018black money\u2019 largely failed. The demonetization affected 1.3 billion people with near-zero time to prepare.",btc:"\u26a1 BITCOIN PARALLEL: A Bitcoin private key cannot be demonetized by government decree."},
3359 | {year:"2020",title:"COVID Money Printing",short:"$5\u20136 trillion U.S. stimulus + Fed balance sheet to $9T. Highest inflation in 40 years follows.",detail:"The U.S. government passed ~$5\u20136 trillion in fiscal stimulus packages (CARES Act, American Rescue Plan, etc.) while the Federal Reserve doubled its balance sheet from $4T to $9T through quantitative easing. The result: 9.1% inflation in June 2022 \u2014 the highest in 40 years. Purchasing power of savings eroded. Asset owners saw portfolios surge while wage earners fell behind. The Cantillon effect: those closest to the money printer benefit first.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin supply did not change. 21 million. The halving in May 2020 reduced new issuance. Bitcoiners called it."},
3360 | {year:"2022",title:"Russia SWIFT Exclusion",short:"$300B in sovereign reserves frozen. Proof that nation-state assets are weapons.",detail:"Following Russia\u2019s invasion of Ukraine, Western nations froze approximately $300 billion in Russian central bank reserves held in Western financial institutions. This demonstrated that sovereign wealth \u2014 money a country legally owns \u2014 can be weaponized by adversaries with institutional access. No court order, no due process. Every central bank in the world took note.",btc:"\u26a1 BITCOIN PARALLEL: Censorship-resistant by design. No counterparty holds your sats."},
3361 | {year:"2022",title:"Canada Trucker Freeze",short:"Bank accounts frozen without court order. Protesters financially silenced in 48 hours.",detail:"The Canadian government invoked the Emergencies Act to freeze bank accounts of Freedom Convoy protesters and donors without court orders. Financial institutions were directed to freeze accounts based on government lists. Accounts were blocked within 48 hours of the declaration. A peaceful protest was financially neutralized. The act was later found to have been applied unlawfully by a Federal Court, but the damage was done.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin transactions cannot be stopped. A node in your home means no one can freeze your economic activity."},
3362 | {year:"2023",title:"U.S. Banking Crisis",short:"SVB, Signature, Silvergate collapse. Crypto-friendly banks systematically shut down \u2014 Operation Chokepoint 2.0.",detail:"Silicon Valley Bank ($212B), Signature Bank ($110B), and Silvergate Bank collapsed in rapid succession. SVB\u2019s failure was partly triggered by the Fed\u2019s rate hiking cycle destroying its bond portfolio. Signature and Silvergate \u2014 both crypto-friendly banks \u2014 were also shut down by regulators. Critics and a Congressional investigation documented \u2018Operation Chokepoint 2.0\u2019: a coordinated effort to deny banking services to crypto businesses.",btc:"\u26a1 BITCOIN PARALLEL: A bank that cannot be closed. Runs 24/7/365. No bank holiday."},
3363 | {year:"NOW",title:"CBDC Push",short:"130+ countries developing programmable digital currencies. Expiry dates. Spending restrictions. Surveillance.",detail:"As of 2026, 130+ countries (representing 98% of global GDP) are developing or piloting Central Bank Digital Currencies. Unlike cash, CBDCs are programmable: governments can set expiry dates (spend it or lose it), restrict what categories of goods can be purchased, tie spending to social credit scores, and surveil every transaction in real time. China\u2019s digital yuan has already been deployed with regional spending restrictions.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin is the opt-out. Permissionless. Unseizable. 21 million. Forever."}
3364 | ];
3365 | var openDot=null,card=document.getElementById('pn-tl-card');
3366 | function tlToggle(dot){
3367 |     var idx=parseInt(dot.dataset.evt),e=TL_EVENTS[idx];
3368 |     if(openDot===dot){tlClose();return;}
3369 |     if(openDot)openDot.classList.remove('active');
3370 |     dot.classList.add('active');
3371 |     openDot=dot;
3372 |     document.getElementById('tlCardHeader').textContent=e.year+' \u2014 '+e.title;
3373 |     document.getElementById('tlCardShort').textContent=e.short;
3374 |     document.getElementById('tlCardDetail').textContent=e.detail;
3375 |     document.getElementById('tlCardBtc').textContent=e.btc;
3376 |     /* Position card near the dot */
3377 |     var r=dot.getBoundingClientRect(),cw=340;
3378 |     card.style.visibility='hidden';card.style.display='block';
3379 |     var ch=card.offsetHeight||300;
3380 |     card.style.visibility='';card.style.display='';
3381 |     var left=r.left+r.width/2-cw/2;
3382 |     var top=r.top+window.scrollY-ch-16;
3383 |     if(dot.closest('.tl-below'))top=r.bottom+window.scrollY+12;
3384 |     if(left<8)left=8;
3385 |     if(left+cw>window.innerWidth-8)left=window.innerWidth-cw-8;
3386 |     if(top<8)top=r.bottom+window.scrollY+12;
3387 |     card.style.left=left+'px';card.style.top=top+'px';
3388 |     card.classList.add('active');
3389 | }
3390 | function tlClose(){
3391 |     card.classList.remove('active');
3392 |     if(openDot){openDot.classList.remove('active');openDot=null;}
3393 | }
3394 | window.tlToggle=tlToggle;window.tlClose=tlClose;
3395 | /* Close on click outside */
3396 | document.addEventListener('click',function(ev){
3397 |     if(!ev.target.closest('.pn-tl-dot')&&!ev.target.closest('.pn-tl-card'))tlClose();
3398 | });
3399 | /* Close on scroll */
3400 | var scr=document.querySelector('.pn-timeline-scroll');
3401 | if(scr)scr.addEventListener('scroll',tlClose);
3402 | })();
3403 | </script>
3404 | 
3405 | <!-- ═══ DISCLAIMER ═══ -->
3406 | <div class="pn-disclaimer">
3407 |     All data sourced from public filings (STOCK Act, SEC EDGAR), public blockchain explorers (mempool.space), and open APIs.
3408 |     Correlation shown for independent research purposes only. Protocol Pulse does not make accusations of insider trading.
3409 |     "FLAGGED" items are statistical patterns, not verified misconduct. Always consult original sources.
3410 |     <strong>This is not financial, investment, or legal advice.</strong> Nothing on this dashboard constitutes a recommendation to buy, sell, or hold any asset.
3411 |     All information is provided for educational and research purposes only.
3412 | </div>
3413 | 
3414 | {% endblock %}
3415 | 
3416 | {% block scripts %}
3417 | <script>
3418 | (function() {
3419 |     // ── UTC Clock ──
3420 |     function updateClock() {
3421 |         var now = new Date();
3422 |         var h = String(now.getUTCHours()).padStart(2, '0');
3423 |         var m = String(now.getUTCMinutes()).padStart(2, '0');
3424 |         var s = String(now.getUTCSeconds()).padStart(2, '0');
3425 |         var el = document.getElementById('pnClock');
3426 |         if (el) el.textContent = h + ':' + m + ':' + s + ' UTC';
3427 |     }
3428 |     updateClock();
3429 |     setInterval(updateClock, 1000);
3430 | 
3431 |     // ── Whale Tracker: fetch from /api/orb (works for all users) ──
3432 |     (function() {
3433 |         var el = document.getElementById('pnWhales');
3434 |         if (!el) return;
3435 |         function loadWhales() {
3436 |             fetch('/api/orb')
3437 |                 .then(function(r) { return r.json(); })
3438 |                 .then(function(d) {
3439 |                     var raw = d.raw || {};
3440 |                     var whales = raw.whale_alerts_list || [];
3441 |                     if (!whales.length) {
3442 |                         el.innerHTML = '<div class="pn-empty">No whale activity detected</div>';
3443 |                         return;
3444 |                     }
3445 |                     var html = '';
3446 |                     whales.slice(0, 5).forEach(function(w) {
3447 |                         var tierCol = w.tier === 'CRITICAL' ? '#ef4444' : (w.tier === 'WARNING' ? '#f97316' : 'var(--pn-muted)');
3448 |                         var isInflow = (w.message || '').toLowerCase().indexOf('inflow') >= 0;
3449 |                         var flowClass = isInflow ? 'inflow' : 'outflow';
3450 |                         html += '<div class="pn-whale-item ' + flowClass + '">';
3451 |                         html += '<div class="pn-whale-row">';
3452 |                         html += '<div class="pn-whale-entity" style="color:' + tierCol + ';font-weight:700;font-size:9px;letter-spacing:1px;">' + (w.tier || 'NOTE') + '</div>';
3453 |                         html += '</div>';
3454 |                         html += '<div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">' + (w.message || '') + '</div>';
3455 |                         html += '<div class="pn-whale-meta"><span style="color:var(--pn-muted);font-size:10px;">Score: ' + (w.score || 0) + '</span></div>';
3456 |                         html += '</div>';
3457 |                     });
3458 |                     el.innerHTML = html;
3459 |                     var c = document.getElementById('pnStatWhales');
3460 |                     if (c) c.textContent = whales.length;
3461 |                 })
3462 |                 .catch(function() {});
3463 |         }
3464 |         loadWhales();
3465 |         setInterval(loadWhales, 60000);
3466 |     })();
3467 | 
3468 |     // ── Political Donation Pulse (rebuilt) ──
3469 |     (function() {
3470 |         fetch('/api/donations/pulse')
3471 |             .then(function(r) { return r.json(); })
3472 |             .then(function(d) {
3473 |                 var el = document.getElementById('pnDonations');
3474 |                 if (!el) return;
3475 | 
3476 |                 var score    = d.score || 0;
3477 |                 var label    = d.label || 'LOW';
3478 |                 var spend    = d.fairshake_spend || 0;
3479 |                 var nComm    = d.crypto_committees || 0;
3480 |                 var nStates  = d.states_active || 0;
3481 |                 var exps     = d.fairshake_expenditures || [];
3482 |                 var topDons  = d.top_donations || [];
3483 |                 var scoreCol = score > 70 ? '#CC0000' : score > 40 ? '#f8c15c' : 'rgba(255,255,255,0.3)';
3484 |                 var spendFmt = spend >= 1e6 ? '$' + (spend/1e6).toFixed(1) + 'M'
3485 |                              : spend >= 1e3 ? '$' + (spend/1e3).toFixed(0) + 'K' : '$0';
3486 | 
3487 |                 var html = '<div style="display:flex;gap:12px;margin-bottom:10px;align-items:flex-start;">';
3488 | 
3489 |                 // Pulse score
3490 |                 html += '<div style="text-align:center;min-width:64px;">'
3491 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:28px;font-weight:900;color:' + scoreCol + ';">' + score + '</div>'
3492 |                       + '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.3);margin-top:2px;">PULSE SCORE</div>'
3493 |                       + '</div>';
3494 | 
3495 |                 // Stats
3496 |                 html += '<div style="display:flex;flex-direction:column;gap:6px;flex:1;">';
3497 |                 html += '<div style="display:flex;gap:16px;">';
3498 |                 html += '<div style="text-align:center;">'
3499 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:#f8c15c;">' + spendFmt + '</div>'
3500 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">FAIRSHAKE SPEND</div>'
3501 |                       + '</div>';
3502 |                 html += '<div style="text-align:center;">'
3503 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:rgba(255,255,255,0.7);">' + nComm + '</div>'
3504 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">CRYPTO PACs</div>'
3505 |                       + '</div>';
3506 |                 html += '<div style="text-align:center;">'
3507 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:rgba(255,255,255,0.7);">' + nStates + '</div>'
3508 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">STATES ACTIVE</div>'
3509 |                       + '</div>';
3510 |                 html += '</div>'; // stats row
3511 |                 html += '</div></div>'; // right col + header
3512 | 
3513 |                 // Fairshake expenditures
3514 |                 if (exps.length) {
3515 |                     html += '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.25);margin-bottom:4px;">FAIRSHAKE PAC — INDEPENDENT EXPENDITURES</div>';
3516 |                     exps.slice(0,4).forEach(function(e) {
3517 |                         var amtFmt = e.amount >= 1e6 ? '$'+(e.amount/1e6).toFixed(1)+'M'
3518 |                                    : e.amount >= 1e3 ? '$'+(e.amount/1e3).toFixed(0)+'K'
3519 |                                    : '$'+e.amount;
3520 |                         var suppCol = e.support === 'S' ? '#22c55e' : '#ef4444';
3521 |                         var suppTxt = e.support === 'S' ? 'SUPPORT' : 'OPPOSE';
3522 |                         html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3523 |                               + '<div>'
3524 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:rgba(255,255,255,0.8);">' + (e.candidate||'?').substring(0,28) + '</span>'
3525 |                               + '<span style="font-size:7px;color:' + suppCol + ';margin-left:6px;border:1px solid '+suppCol+';padding:1px 4px;border-radius:2px;">' + suppTxt + '</span>'
3526 |                               + '</div>'
3527 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:#f8c15c;">' + amtFmt + '</span>'
3528 |                               + '</div>';
3529 |                     });
3530 |                 }
3531 | 
3532 |                 // Top donations
3533 |                 if (topDons.length) {
3534 |                     html += '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.25);margin:8px 0 4px;">TOP INDIVIDUAL DONATIONS TO CRYPTO PACs</div>';
3535 |                     topDons.slice(0,4).forEach(function(d2) {
3536 |                         var amtFmt = d2.amount >= 1e6 ? '$'+(d2.amount/1e6).toFixed(1)+'M'
3537 |                                    : d2.amount >= 1e3 ? '$'+(d2.amount/1e3).toFixed(0)+'K'
3538 |                                    : '$'+d2.amount;
3539 |                         var loc = d2.city ? d2.city + ', ' + d2.state : d2.state || '';
3540 |                         html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3541 |                               + '<div>'
3542 |                               + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:rgba(255,255,255,0.8);">' + (d2.donor||'Anonymous').substring(0,26) + '</div>'
3543 |                               + '<div style="font-size:7px;color:rgba(255,255,255,0.3);">' + loc + (d2.employer ? ' · ' + d2.employer.substring(0,20) : '') + '</div>'
3544 |                               + '</div>'
3545 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:#CC0000;">' + amtFmt + '</span>'
3546 |                               + '</div>';
3547 |                     });
3548 |                 }
3549 | 
3550 |                 if (!exps.length && !topDons.length) {
3551 |                     html += '<div style="color:rgba(255,255,255,0.2);font-size:9px;font-family:\'JetBrains Mono\',monospace;margin-top:8px;">'
3552 |                           + (d.key_type === 'demo' ? 'Add OPENFEC_API_KEY to .env for live data' : 'No recent expenditure data')
3553 |                           + '</div>';
3554 |                 }
3555 | 
3556 |                 html += '<div style="font-size:7px;color:rgba(255,255,255,0.1);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: OpenFEC Public API · FEC.gov</div>';
3557 |                 el.innerHTML = html;
3558 |             })
3559 |             .catch(function(err) {
3560 |                 var el = document.getElementById('pnDonations');
3561 |                 if (el) el.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:9px;font-family:\'JetBrains Mono\',monospace;">Donation data unavailable</div>';
3562 |             });
3563 |     })();
3564 | 
3565 | 
3566 |     {% if not demo_mode %}
3567 |     // ── Make the Bitcoin Case (typewriter 18ms/char, gold cursor) ──
3568 |     window.makeBitcoinCase = function(btn, eventSummary) {
3569 |         var idx = btn.getAttribute('data-idx');
3570 |         var outputEl = document.getElementById('btcCase' + idx);
3571 |         if (!outputEl) return;
3572 | 
3573 |         btn.disabled = true;
3574 |         btn.textContent = 'GENERATING...';
3575 |         outputEl.innerHTML = '';
3576 |         outputEl.classList.add('visible');
3577 | 
3578 |         fetch('/api/panopticon/make-bitcoin-case', {
3579 |             method: 'POST',
3580 |             headers: {'Content-Type': 'application/json'},
3581 |             body: JSON.stringify({event_summary: eventSummary})
3582 |         })
3583 |         .then(function(r) { return r.json(); })
3584 |         .then(function(data) {
3585 |             if (data.error) {
3586 |                 outputEl.innerHTML = '<span style="color:var(--pn-red)">' + data.error + '</span>';
3587 |                 btn.disabled = false;
3588 |                 btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
3589 |                 return;
3590 |             }
3591 |             var text = data.case_text || '';
3592 |             var model = data.model || '';
3593 |             outputEl.innerHTML = '<div class="pn-btc-case-label">THE BITCOIN CASE</div><span id="typewriter' + idx + '"></span><span class="pn-typewriter-cursor"></span>';
3594 |             var twEl = document.getElementById('typewriter' + idx);
3595 |             var i = 0;
3596 |             function typeChar() {
3597 |                 if (i < text.length) {
3598 |                     twEl.textContent += text.charAt(i);
3599 |                     i++;
3600 |                     setTimeout(typeChar, 18 + Math.random() * 12);
3601 |                 } else {
3602 |                     var cursor = outputEl.querySelector('.pn-typewriter-cursor');
3603 |                     if (cursor) cursor.remove();
3604 |                     outputEl.innerHTML += '<div class="pn-btc-case-model">Model: ' + model + '</div>';
3605 |                     btn.disabled = false;
3606 |                     btn.innerHTML = '&#x20BF; Regenerate Case';
3607 |                 }
3608 |             }
3609 |             typeChar();
3610 |         })
3611 |         .catch(function() {
3612 |             outputEl.innerHTML = '<span style="color:var(--pn-red)">Failed to generate. Try again.</span>';
3613 |             btn.disabled = false;
3614 |             btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
3615 |         });
3616 |     };
3617 | 
3618 |     // ── Auto-refresh every 5 minutes ──
3619 |     function refreshData() {
3620 |         fetch('/api/panopticon/whale-alerts')
3621 |             .then(function(r) { return r.json(); })
3622 |             .then(function(data) {
3623 |                 if (data.alerts && data.alerts.length > 0) {
3624 |                     var c = document.getElementById('pnStatWhales');
3625 |                     if (c) c.textContent = data.alerts.length;
3626 |                 }
3627 |             })
3628 |             .catch(function() {});
3629 | 
3630 |         fetch('/api/panopticon/geopolitical')
3631 |             .then(function(r) { return r.json(); })
3632 |             .then(function(data) {
3633 |                 if (data.geopolitical) {
3634 |                     var c = document.getElementById('pnStatGeo');
3635 |                     if (c) c.textContent = data.geopolitical.length;
3636 |                 }
3637 |             })
3638 |             .catch(function() {});
3639 |     }
3640 |     setInterval(refreshData, 300000);
3641 |     {% endif %}
3642 | })();
3643 | 
3644 | 
3645 | /* ═══ CONGRESSIONAL TRADING ═══ */
3646 | (function(){
3647 |   // Helper: reuse liveData cache from SS2 fetchAll() if available, else fetch once
3648 |   var liveData = window._pnLiveData || {};
3649 |   function getCachedOrFetch(key, url) {
3650 |     if (liveData[key]) return Promise.resolve(liveData[key]);
3651 |     return fetch(url).then(function(r){return r.json();}).then(function(d){ liveData[key] = d; return d; });
3652 |   }
3653 |   // Recent trades (deduped — uses liveData.trades from SS2 fetchAll)
3654 |   getCachedOrFetch('trades', '/api/congress/trades').then(function(d){
3655 |     var el = document.getElementById('pnCongress');
3656 |     if (!el) return;
3657 |     var trades = d.trades || [];
3658 |     if (!trades.length) { el.innerHTML = '<div style="color:#555;font-size:10px;">No trades available</div>'; return; }
3659 |     var html = '';
3660 |     trades.slice(0, 8).forEach(function(t) {
3661 |       var isBuy = (t.transaction || '').toLowerCase().indexOf('purchase') >= 0;
3662 |       var partyCol = t.party === 'D' ? '#3b82f6' : t.party === 'R' ? '#ef4444' : '#888';
3663 |       html += '<div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-family:\'JetBrains Mono\',monospace;font-size:9px;">';
3664 |       html += '<span style="color:' + partyCol + ';font-weight:700;min-width:14px;">' + (t.party || '?') + '</span>';
3665 |       html += '<span style="color:rgba(255,255,255,0.6);min-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + (t.member || 'Unknown') + '</span>';
3666 |       html += '<span style="color:' + (isBuy ? '#22c55e' : '#ef4444') + ';font-weight:600;min-width:45px;">' + (isBuy ? 'BUY' : 'SELL') + '</span>';
3667 |       html += '<span style="color:#f8c15c;font-weight:700;min-width:40px;">' + (t.ticker || '???') + '</span>';
3668 |       html += '<span style="color:rgba(255,255,255,0.3);margin-left:auto;">' + (t.amount || '') + '</span>';
3669 |       html += '</div>';
3670 |     });
3671 |     if (d.trades && d.trades[0] && d.trades[0].source === 'fallback') {
3672 |       html += '<div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;">Source: Public STOCK Act filings (add QUIVER_API_KEY for live data)</div>';
3673 |     }
3674 |     el.innerHTML = html;
3675 |   }).catch(function(e){ console.warn('Congress trades:', e); });
3676 | 
3677 |   // Party breakdown (deduped — reuses liveData.trades)
3678 |   getCachedOrFetch('trades', '/api/congress/trades').then(function(d){
3679 |     var el = document.getElementById('pnPartyBreakdown');
3680 |     if (!el) return;
3681 |     var pb = d.party_breakdown || {};
3682 |     var html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">';
3683 |     [{k:'D',label:'DEMOCRAT',col:'#3b82f6'},{k:'R',label:'REPUBLICAN',col:'#ef4444'},{k:'I',label:'INDEPENDENT',col:'#888'}].forEach(function(p){
3684 |       var data = pb[p.k] || {buys:0,sells:0,total:0};
3685 |       html += '<div style="text-align:center;padding:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);border-radius:4px;">';
3686 |       html += '<div style="font-size:7px;font-weight:700;letter-spacing:0.12em;color:' + p.col + ';">' + p.label + '</div>';
3687 |       html += '<div style="font-size:18px;font-weight:900;color:#fff;margin-top:4px;">' + data.total + '</div>';
3688 |       html += '<div style="font-size:8px;color:rgba(255,255,255,0.3);margin-top:2px;">' + data.buys + ' BUY / ' + data.sells + ' SELL</div>';
3689 |       html += '</div>';
3690 |     });
3691 |     html += '</div>';
3692 |     el.innerHTML = html;
3693 |   }).catch(function(){});
3694 | 
3695 |   // IHX Score (deduped — reuses liveData.ihx)
3696 |   getCachedOrFetch('ihx', '/api/congress/ihx').then(function(d){
3697 |     var el = document.getElementById('pnIHX');
3698 |     if (!el) return;
3699 |     var s = d.score || 50;
3700 |     var col = s > 65 ? '#22c55e' : s < 35 ? '#ef4444' : '#f8c15c';
3701 |     var signal = (d.signal || 'neutral').toUpperCase();
3702 |     el.innerHTML = '<div style="display:flex;align-items:center;gap:12px;">'
3703 |       + '<div style="font-size:28px;font-weight:900;color:' + col + ';">' + s + '</div>'
3704 |       + '<div><div style="font-size:10px;font-weight:700;color:' + col + ';">' + signal + '</div>'
3705 |       + '<div style="font-size:8px;color:rgba(255,255,255,0.4);margin-top:2px;">' + (d.interpretation || '') + '</div></div></div>'
3706 |       + '<div style="height:3px;background:rgba(255,255,255,0.04);border-radius:2px;margin-top:8px;"><div style="height:100%;width:' + s + '%;background:' + col + ';border-radius:2px;"></div></div>'
3707 |       + '<div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:6px;">' + (d.trade_count || 0) + ' trades analyzed • ' + (d.crypto_trades || 0) + ' crypto-adjacent</div>';
3708 |   }).catch(function(){});
3709 | 
3710 |   // ── Institutional Accumulation (SEC EDGAR 13F) ─────────────────
3711 |   getCachedOrFetch('inst', '/api/panopticon/institutional').then(function(d){
3712 |     var el13f = document.getElementById('pnInstitutional');
3713 |     var elBanner = document.getElementById('pnCoalitionBanner');
3714 |     var elNote = document.getElementById('pnCoalitionNote');
3715 |     if (!el13f) return;
3716 | 
3717 |     // Coalition banner
3718 |     if (d.coalition_summary && d.coalition_summary.detected && elBanner) {
3719 |       var months = d.coalition_summary.active_months || {};
3720 |       var monthKeys = Object.keys(months);
3721 |       var bestMonth = monthKeys.length ? months[monthKeys[0]] : null;
3722 |       if (bestMonth) {
3723 |         elNote.textContent = bestMonth.note || (bestMonth.filers + ' institutions in coordinated accumulation window');
3724 |         elBanner.style.display = 'block';
3725 |       }
3726 |     }
3727 | 
3728 |     var filers = d.institutional_13f || [];
3729 |     if (!filers.length) { el13f.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;font-family:\'JetBrains Mono\',monospace;">No 13F data in current window</div>'; return; }
3730 | 
3731 |     var html = '<div style="display:flex;flex-direction:column;gap:6px;">';
3732 |     filers.slice(0,8).forEach(function(f){
3733 |       var score = f.coalition_score || 0;
3734 |       var scoreCol = score >= 80 ? '#ef4444' : score >= 50 ? '#f8c15c' : '#888';
3735 |       var tag = f.coalition_detected ? '<span style="background:rgba(204,0,0,0.15);color:#cc0000;font-size:7px;padding:2px 6px;border-radius:3px;letter-spacing:.08em;margin-left:6px;">COALITION</span>' : '';
3736 |       html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3737 |         + '<div><div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:rgba(255,255,255,0.85);">' + f.entity + tag + '</div>'
3738 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.35);margin-top:2px;">' + f.institution_type + ' · ' + (f.filing_date || '') + ' · 13F-HR</div></div>'
3739 |         + '<div style="font-size:9px;color:#22c55e;font-family:\'JetBrains Mono\',monospace;">BTC ETF ↑</div>'
3740 |         + '</div>';
3741 |     });
3742 |     html += '</div><div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: SEC EDGAR 13F · ' + (d.total_institutional_filers || 0) + ' filers</div>';
3743 |     el13f.innerHTML = html;
3744 |   }).catch(function(){ });
3745 | 
3746 |   // ── Private Equity Datastream (Form D + Coalition) ────────────
3747 |   getCachedOrFetch('pe', '/api/panopticon/pe-datastream').then(function(d){
3748 |     var elPE = document.getElementById('pnPEDatastream');
3749 |     if (!elPE) return;
3750 |     var rounds = d.pe_rounds || [];
3751 |     if (!rounds.length) { elPE.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;font-family:\'JetBrains Mono\',monospace;">No PE rounds in current window</div>'; return; }
3752 | 
3753 |     var html = '';
3754 |     if (d.coalition_active) {
3755 |       html += '<div style="background:rgba(204,0,0,0.08);border-left:3px solid #cc0000;padding:8px 12px;margin-bottom:10px;border-radius:0 4px 4px 0;">'
3756 |         + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:8px;letter-spacing:.15em;color:#cc0000;font-weight:700;">COALITION EFFECT ACTIVE</div>'
3757 |         + '<div style="font-size:10px;color:rgba(255,255,255,0.6);margin-top:4px;">' + (d.insight || '') + '</div>'
3758 |         + '</div>';
3759 |     }
3760 | 
3761 |     html += '<div style="display:flex;flex-direction:column;gap:6px;">';
3762 |     rounds.slice(0,8).forEach(function(r){
3763 |       html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3764 |         + '<div><div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:rgba(255,255,255,0.85);">' + r.entity + '</div>'
3765 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.35);margin-top:2px;">' + (r.filing_date || '') + ' · Form D · Digital Assets</div></div>'
3766 |         + '<div style="font-size:9px;color:#f8c15c;font-family:\'JetBrains Mono\',monospace;">RAISE ↑</div>'
3767 |         + '</div>';
3768 |     });
3769 |     html += '</div><div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: SEC EDGAR Form D · ' + (d.pe_count || 0) + ' rounds</div>';
3770 |     elPE.innerHTML = html;
3771 |   }).catch(function(){ });
3772 | 
3773 | 
3774 |   // ── Bitcoin Bill Gap Tracker ──────────────────────────────────────────────
3775 |   (function loadBillTracker() {
3776 |     var el = document.getElementById('pnBillTracker');
3777 |     if (!el) return;
3778 | 
3779 |     fetch('/api/panopticon/bills')
3780 |       .then(function(r) { return r.json(); })
3781 |       .then(function(data) {
3782 |         var bills = (data.bills || []).slice(0, 12);
3783 |         if (!bills.length) {
3784 |           el.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;">No active Bitcoin legislation found</div>';
3785 |           return;
3786 |         }
3787 | 
3788 |         var html = '<div style="display:flex;flex-direction:column;gap:10px;">';
3789 | 
3790 |         bills.forEach(function(b) {
3791 |           var gap = b.gap_score !== null ? b.gap_score : null;
3792 |           var gapCol = gap === null ? '#888' : gap >= 40 ? '#ef4444' : gap >= 20 ? '#f97316' : '#22c55e';
3793 |           var gapLabel = b.gap_label || 'PENDING';
3794 |           var congPct = b.congress_pct || 0;
3795 |           var pubPct  = b.public_pct  || 50;
3796 |           var hasCongVote = b.vote_tally && b.vote_tally.total > 0;
3797 |           var btcCol = b.btc_signal === 'bullish' ? '#22c55e' : b.btc_signal === 'bearish' ? '#ef4444' : '#888';
3798 |           var cats = (b.categories || []).join(', ').replace(/_/g,' ');
3799 | 
3800 |           html += '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:10px 12px;">';
3801 | 
3802 |           // Header row
3803 |           html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
3804 |             + '<div>'
3805 |             + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:rgba(255,255,255,0.9);">'
3806 |             + b.bill_number + ' — ' + (b.short_title || '').substring(0,40) + '</div>'
3807 |             + '<div style="font-size:7px;color:rgba(255,255,255,0.3);margin-top:2px;text-transform:uppercase;letter-spacing:.06em;">'
3808 |             + cats.substring(0,35) + '</div>'
3809 |             + '</div>'
3810 |             + '<div style="text-align:right;flex-shrink:0;margin-left:8px;">'
3811 |             + (gap !== null ? '<div style="font-family:\'JetBrains Mono\',monospace;font-size:14px;font-weight:900;color:' + gapCol + ';">' + gap + '%</div>'
3812 |                            : '<div style="font-size:8px;color:#888;font-family:\'JetBrains Mono\',monospace;">PENDING</div>')
3813 |             + '<div style="font-size:6px;letter-spacing:.1em;color:' + gapCol + ';font-weight:700;">GAP</div>'
3814 |             + '</div>'
3815 |             + '</div>';
3816 | 
3817 |           // Progress bars
3818 |           html += '<div style="display:flex;flex-direction:column;gap:5px;margin-bottom:6px;">';
3819 | 
3820 |           // Public bar
3821 |           html += '<div style="display:flex;align-items:center;gap:6px;">'
3822 |             + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;flex-shrink:0;font-family:\'JetBrains Mono\',monospace;">PUBLIC</div>'
3823 |             + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;position:relative;">'
3824 |             + '<div style="height:100%;width:' + pubPct + '%;background:linear-gradient(90deg,#22c55e,#16a34a);border-radius:3px;transition:width .8s ease;"></div>'
3825 |             + '</div>'
3826 |             + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;font-weight:700;color:#22c55e;width:30px;text-align:right;">' + pubPct + '%</div>'
3827 |             + '</div>';
3828 | 
3829 |           // Congress bar
3830 |           if (hasCongVote) {
3831 |             var congBarColor = congPct >= 67 ? '#22c55e' : congPct >= 50 ? '#f8c15c' : '#ef4444';
3832 |             var nayPct = 100 - congPct;
3833 |             html += '<div style="display:flex;align-items:center;gap:6px;">'
3834 |               + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;flex-shrink:0;font-family:\'JetBrains Mono\',monospace;">CONGRESS</div>'
3835 |               + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;display:flex;">'
3836 |               + '<div style="height:100%;width:' + congPct + '%;background:' + congBarColor + ';transition:width .8s ease;"></div>'
3837 |               + '<div style="height:100%;width:' + nayPct + '%;background:#ef4444;opacity:0.5;"></div>'
3838 |               + '</div>'
3839 |               + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;font-weight:700;color:' + congBarColor + ';width:30px;text-align:right;">' + congPct + '%</div>'
3840 |               + '</div>';
3841 |           } else {
3842 |             html += '<div style="display:flex;align-items:center;gap:6px;">'
3843 |               + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;font-family:\'JetBrains Mono\',monospace;">CONGRESS</div>'
3844 |               + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.04);border-radius:3px;display:flex;align-items:center;padding-left:8px;">'
3845 |               + '<span style="font-size:7px;color:rgba(255,255,255,0.2);font-family:\'JetBrains Mono\',monospace;">NO VOTE YET</span>'
3846 |               + '</div></div>';
3847 |           }
3848 | 
3849 |           html += '</div>'; // end bars
3850 | 
3851 |           // Footer: status + vote buttons
3852 |           html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">'
3853 |             + '<div>'
3854 |             + '<span style="font-size:7px;color:rgba(255,255,255,0.3);">' + (b.status||'') + '</span>'
3855 |             + (b.sponsor ? '<span style="font-size:7px;color:rgba(255,255,255,0.2);margin-left:8px;">Sponsor: ' + b.sponsor.substring(0,20) + '</span>' : '')
3856 |             + '</div>'
3857 |             + '<div style="display:flex;gap:4px;align-items:center;">'
3858 |             + '<span style="font-size:7px;color:rgba(255,255,255,0.25);font-family:\'JetBrains Mono\',monospace;">SHOULD PASS?</span>'
3859 |             + '<button onclick="castBillVote(' + b.bill_id + ',\'' + b.bill_number + '\',\'yes\')" '
3860 |             +   'style="background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);color:#22c55e;padding:2px 8px;border-radius:3px;font-size:8px;font-family:\'JetBrains Mono\',monospace;cursor:pointer;letter-spacing:.08em;">YES</button>'
3861 |             + '<button onclick="castBillVote(' + b.bill_id + ',\'' + b.bill_number + '\',\'no\')" '
3862 |             +   'style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;padding:2px 8px;border-radius:3px;font-size:8px;font-family:\'JetBrains Mono\',monospace;cursor:pointer;letter-spacing:.08em;">NO</button>'
3863 |             + '</div>'
3864 |             + '</div>';
3865 | 
3866 |           html += '</div>'; // end card
3867 |         });
3868 | 
3869 |         html += '</div>';
3870 |         html += '<div style="font-size:7px;color:rgba(255,255,255,0.15);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">'
3871 |           + 'Source: LegiScan API (CC BY 4.0) · ' + data.total_bills + ' bills tracked'
3872 |           + '</div>';
3873 |         el.innerHTML = html;
3874 |       })
3875 |       .catch(function(e) {
3876 |         if (el) el.innerHTML = '<div style="color:rgba(255,255,255,0.15);font-size:9px;">Bill tracker unavailable</div>';
3877 |       });
3878 |   })();
3879 | 
3880 |   function castBillVote(billId, billNumber, vote) {
3881 |     fetch('/api/panopticon/bills/vote', {
3882 |       method: 'POST',
3883 |       headers: {'Content-Type': 'application/json'},
3884 |       body: JSON.stringify({bill_id: billId, bill_number: billNumber, vote: vote})
3885 |     })
3886 |     .then(function(r) { return r.json(); })
3887 |     .then(function(d) {
3888 |       if (d.success) {
3889 |         // Flash the bill card
3890 |         var cards = document.querySelectorAll('#pnBillTracker > div > div');
3891 |         // Reload the tracker to show updated votes
3892 |         setTimeout(function() {
3893 |           document.getElementById('pnBillTracker').innerHTML =
3894 |             '<div style="color:rgba(34,197,94,0.8);font-size:9px;font-family:\'JetBrains Mono\',monospace;padding:8px;">Vote recorded. Reloading...</div>';
3895 |           setTimeout(function() { loadBillTracker(); }, 1500);
3896 |         }, 300);
3897 |       }
3898 |     })
3899 |     .catch(function() {});
3900 |   }
3901 | 
3902 | })();
3903 | 
3904 | </script>
3905 | {% endblock %}
3906 | 
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?

