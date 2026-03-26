# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: intelligence-terminal
# Branch: main
# Generated: 2026-03-26 01:05 UTC
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

### File: templates/intelligence_page.html (812 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Intelligence Dashboard | Protocol Pulse{% endblock %}
   4 | 
   5 | {% block meta_description %}Bitcoin signal strength composite, trending narratives, entity tracker, and real-time anomaly detection.{% endblock %}
   6 | 
   7 | {% block extra_css %}
   8 | <style>
   9 | /* ── Intelligence Page ── */
  10 | .intel-page {
  11 |   min-height: 100vh;
  12 |   background: #06070b;
  13 |   padding: 100px 24px 80px;
  14 | }
  15 | 
  16 | .intel-container {
  17 |   max-width: 1400px;
  18 |   margin: 0 auto;
  19 | }
  20 | 
  21 | /* ── Header ── */
  22 | .intel-eyebrow {
  23 |   font-family: 'JetBrains Mono', monospace;
  24 |   font-size: 10px;
  25 |   font-weight: 800;
  26 |   letter-spacing: 0.20em;
  27 |   text-transform: uppercase;
  28 |   color: #f8c15c;
  29 |   margin-bottom: 8px;
  30 | }
  31 | 
  32 | .intel-headline {
  33 |   font-size: 2.4rem;
  34 |   font-weight: 900;
  35 |   color: #eef2ff;
  36 |   letter-spacing: -0.03em;
  37 |   line-height: 1.1;
  38 |   margin-bottom: 8px;
  39 | }
  40 | 
  41 | /* ── Glass card ── */
  42 | .g-card {
  43 |   background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  44 |   border: 1px solid rgba(255,255,255,0.08);
  45 |   border-radius: 16px;
  46 |   padding: 24px;
  47 |   height: 100%;
  48 | }
  49 | 
  50 | .g-card.accent-red { border-color: rgba(255,59,95,0.18); }
  51 | .g-card.accent-gold { border-color: rgba(248,193,92,0.15); }
  52 | .g-card.accent-cyan { border-color: rgba(93,228,255,0.12); }
  53 | 
  54 | .g-eyebrow {
  55 |   font-family: 'JetBrains Mono', monospace;
  56 |   font-size: 9px;
  57 |   font-weight: 800;
  58 |   letter-spacing: 0.18em;
  59 |   text-transform: uppercase;
  60 |   color: #f8c15c;
  61 |   margin-bottom: 16px;
  62 |   display: block;
  63 | }
  64 | 
  65 | /* ── Signal Strength Big Number ── */
  66 | .signal-composite {
  67 |   font-family: 'JetBrains Mono', monospace;
  68 |   font-size: 5rem;
  69 |   font-weight: 900;
  70 |   letter-spacing: -0.05em;
  71 |   line-height: 1;
  72 |   transition: color 0.5s ease;
  73 | }
  74 | 
  75 | .signal-label {
  76 |   font-family: 'JetBrains Mono', monospace;
  77 |   font-size: 14px;
  78 |   font-weight: 800;
  79 |   letter-spacing: 0.18em;
  80 |   text-transform: uppercase;
  81 |   margin-top: 6px;
  82 | }
  83 | 
  84 | .signal-trajectory {
  85 |   font-family: 'JetBrains Mono', monospace;
  86 |   font-size: 10px;
  87 |   font-weight: 700;
  88 |   letter-spacing: 0.12em;
  89 |   text-transform: uppercase;
  90 |   color: #95a0ba;
  91 |   margin-top: 8px;
  92 |   display: flex;
  93 |   align-items: center;
  94 |   gap: 6px;
  95 | }
  96 | 
  97 | /* ── Radial gauge for composite ── */
  98 | .signal-gauge-wrap {
  99 |   position: relative;
 100 |   display: flex;
 101 |   flex-direction: column;
 102 |   align-items: center;
 103 | }
 104 | 
 105 | .signal-gauge-svg {
 106 |   width: 180px;
 107 |   height: 180px;
 108 | }
 109 | 
 110 | /* ── Component mini-gauges ── */
 111 | .component-row {
 112 |   display: grid;
 113 |   grid-template-columns: 1fr;
 114 |   gap: 10px;
 115 | }
 116 | 
 117 | .comp-item {
 118 |   display: flex;
 119 |   flex-direction: column;
 120 |   gap: 4px;
 121 | }
 122 | 
 123 | .comp-header {
 124 |   display: flex;
 125 |   justify-content: space-between;
 126 |   align-items: center;
 127 | }
 128 | 
 129 | .comp-label {
 130 |   font-family: 'JetBrains Mono', monospace;
 131 |   font-size: 9px;
 132 |   font-weight: 700;
 133 |   letter-spacing: 0.14em;
 134 |   text-transform: uppercase;
 135 |   color: #95a0ba;
 136 | }
 137 | 
 138 | .comp-score {
 139 |   font-family: 'JetBrains Mono', monospace;
 140 |   font-size: 11px;
 141 |   font-weight: 800;
 142 |   color: #f8c15c;
 143 | }
 144 | 
 145 | .comp-bar-track {
 146 |   height: 4px;
 147 |   background: rgba(255,255,255,0.06);
 148 |   border-radius: 2px;
 149 |   overflow: hidden;
 150 | }
 151 | 
 152 | .comp-bar-fill {
 153 |   height: 100%;
 154 |   border-radius: 2px;
 155 |   transition: width 0.8s ease;
 156 | }
 157 | 
 158 | .comp-desc {
 159 |   font-size: 10px;
 160 |   color: #4a5568;
 161 |   font-family: 'JetBrains Mono', monospace;
 162 | }
 163 | 
 164 | /* ── Topic cloud ── */
 165 | .topic-cloud {
 166 |   display: flex;
 167 |   flex-wrap: wrap;
 168 |   gap: 10px;
 169 |   align-items: center;
 170 |   line-height: 1.6;
 171 | }
 172 | 
 173 | .topic-word {
 174 |   cursor: default;
 175 |   font-family: 'JetBrains Mono', monospace;
 176 |   font-weight: 700;
 177 |   letter-spacing: 0.04em;
 178 |   transition: opacity 0.2s;
 179 |   text-decoration: none;
 180 | }
 181 | 
 182 | .topic-word.bullish { color: #89ffb8; }
 183 | .topic-word.bearish { color: #ff8ba0; }
 184 | .topic-word.neutral { color: #eef2ff; }
 185 | .topic-word:hover { opacity: 0.7; }
 186 | 
 187 | /* ── Entity table ── */
 188 | .entity-table {
 189 |   width: 100%;
 190 |   border-collapse: collapse;
 191 | }
 192 | 
 193 | .entity-table th {
 194 |   font-family: 'JetBrains Mono', monospace;
 195 |   font-size: 9px;
 196 |   font-weight: 800;
 197 |   letter-spacing: 0.14em;
 198 |   text-transform: uppercase;
 199 |   color: #95a0ba;
 200 |   padding: 8px 12px;
 201 |   border-bottom: 1px solid rgba(255,255,255,0.06);
 202 |   text-align: left;
 203 | }
 204 | 
 205 | .entity-table td {
 206 |   padding: 10px 12px;
 207 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 208 |   font-size: 13px;
 209 |   color: #eef2ff;
 210 |   vertical-align: middle;
 211 | }
 212 | 
 213 | .entity-table tr:last-child td { border-bottom: none; }
 214 | 
 215 | .entity-type {
 216 |   font-family: 'JetBrains Mono', monospace;
 217 |   font-size: 9px;
 218 |   font-weight: 700;
 219 |   text-transform: uppercase;
 220 |   letter-spacing: 0.12em;
 221 |   padding: 2px 6px;
 222 |   border-radius: 4px;
 223 |   background: rgba(93,228,255,0.08);
 224 |   color: #5de4ff;
 225 | }
 226 | 
 227 | /* ── Narrative timeline ── */
 228 | .narr-timeline {
 229 |   display: flex;
 230 |   flex-direction: column;
 231 |   gap: 0;
 232 | }
 233 | 
 234 | .narr-day {
 235 |   display: grid;
 236 |   grid-template-columns: 60px 1fr auto;
 237 |   gap: 12px;
 238 |   align-items: center;
 239 |   padding: 10px 0;
 240 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 241 | }
 242 | 
 243 | .narr-day:last-child { border-bottom: none; }
 244 | 
 245 | .narr-date {
 246 |   font-family: 'JetBrains Mono', monospace;
 247 |   font-size: 10px;
 248 |   color: #95a0ba;
 249 |   font-weight: 700;
 250 | }
 251 | 
 252 | .narr-narrative {
 253 |   font-size: 12px;
 254 |   color: #eef2ff;
 255 |   font-weight: 600;
 256 | }
 257 | 
 258 | .narr-score {
 259 |   font-family: 'JetBrains Mono', monospace;
 260 |   font-size: 12px;
 261 |   font-weight: 800;
 262 |   min-width: 32px;
 263 |   text-align: right;
 264 | }
 265 | 
 266 | /* ── Event list ── */
 267 | .evt-item {
 268 |   display: flex;
 269 |   gap: 12px;
 270 |   padding: 12px 0;
 271 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 272 |   align-items: flex-start;
 273 | }
 274 | 
 275 | .evt-item:last-child { border-bottom: none; }
 276 | 
 277 | .evt-badge {
 278 |   font-family: 'JetBrains Mono', monospace;
 279 |   font-size: 9px;
 280 |   font-weight: 800;
 281 |   letter-spacing: 0.10em;
 282 |   text-transform: uppercase;
 283 |   padding: 3px 7px;
 284 |   border-radius: 4px;
 285 |   flex-shrink: 0;
 286 |   margin-top: 1px;
 287 | }
 288 | 
 289 | .evt-badge.critical { background: rgba(255,59,95,0.15); color: #ff8ba0; }
 290 | .evt-badge.warning  { background: rgba(248,193,92,0.12); color: #f8c15c; }
 291 | .evt-badge.info     { background: rgba(93,228,255,0.10); color: #5de4ff; }
 292 | 
 293 | /* ── Fear & Greed widget ── */
 294 | .fg-wrap {
 295 |   text-align: center;
 296 | }
 297 | 
 298 | .fg-value {
 299 |   font-family: 'JetBrains Mono', monospace;
 300 |   font-size: 3.5rem;
 301 |   font-weight: 900;
 302 |   letter-spacing: -0.04em;
 303 |   line-height: 1;
 304 | }
 305 | 
 306 | .fg-label {
 307 |   font-family: 'JetBrains Mono', monospace;
 308 |   font-size: 11px;
 309 |   font-weight: 800;
 310 |   letter-spacing: 0.16em;
 311 |   text-transform: uppercase;
 312 |   margin-top: 6px;
 313 | }
 314 | 
 315 | .fg-history {
 316 |   display: flex;
 317 |   gap: 4px;
 318 |   margin-top: 16px;
 319 |   align-items: flex-end;
 320 |   justify-content: center;
 321 |   height: 40px;
 322 | }
 323 | 
 324 | .fg-bar {
 325 |   width: 24px;
 326 |   border-radius: 2px 2px 0 0;
 327 |   min-height: 4px;
 328 |   transition: height 0.5s ease;
 329 | }
 330 | 
 331 | /* ── Stat pills ── */
 332 | .stat-pill {
 333 |   display: flex;
 334 |   flex-direction: column;
 335 |   align-items: center;
 336 |   padding: 16px;
 337 |   background: rgba(255,255,255,0.03);
 338 |   border: 1px solid rgba(255,255,255,0.06);
 339 |   border-radius: 12px;
 340 |   flex: 1;
 341 |   min-width: 100px;
 342 | }
 343 | 
 344 | .stat-pill-value {
 345 |   font-family: 'JetBrains Mono', monospace;
 346 |   font-size: 1.6rem;
 347 |   font-weight: 900;
 348 |   color: #f8c15c;
 349 |   letter-spacing: -0.03em;
 350 |   line-height: 1;
 351 | }
 352 | 
 353 | .stat-pill-label {
 354 |   font-family: 'JetBrains Mono', monospace;
 355 |   font-size: 9px;
 356 |   font-weight: 800;
 357 |   letter-spacing: 0.16em;
 358 |   text-transform: uppercase;
 359 |   color: #95a0ba;
 360 |   margin-top: 4px;
 361 | }
 362 | 
 363 | /* ── Article stream ── */
 364 | .art-stream-item {
 365 |   display: grid;
 366 |   grid-template-columns: 28px 1fr auto;
 367 |   gap: 12px;
 368 |   padding: 10px 0;
 369 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 370 |   align-items: start;
 371 | }
 372 | 
 373 | .art-stream-item:last-child { border-bottom: none; }
 374 | 
 375 | .art-rank {
 376 |   font-family: 'JetBrains Mono', monospace;
 377 |   font-size: 10px;
 378 |   font-weight: 700;
 379 |   color: #4a5568;
 380 |   padding-top: 2px;
 381 | }
 382 | 
 383 | .art-title {
 384 |   font-size: 13px;
 385 |   font-weight: 600;
 386 |   color: #eef2ff;
 387 |   line-height: 1.4;
 388 |   margin-bottom: 3px;
 389 | }
 390 | 
 391 | .art-meta {
 392 |   display: flex;
 393 |   gap: 6px;
 394 |   flex-wrap: wrap;
 395 |   align-items: center;
 396 | }
 397 | 
 398 | .art-imp {
 399 |   font-family: 'JetBrains Mono', monospace;
 400 |   font-size: 1rem;
 401 |   font-weight: 900;
 402 |   text-align: right;
 403 | }
 404 | 
 405 | /* ── Badges ── */
 406 | .s-badge {
 407 |   display: inline-flex;
 408 |   align-items: center;
 409 |   gap: 4px;
 410 |   padding: 2px 8px;
 411 |   border-radius: 999px;
 412 |   font-family: 'JetBrains Mono', monospace;
 413 |   font-size: 9px;
 414 |   font-weight: 800;
 415 |   letter-spacing: 0.10em;
 416 |   text-transform: uppercase;
 417 | }
 418 | 
 419 | .s-badge.bullish { background: rgba(137,255,184,0.10); color: #89ffb8; }
 420 | .s-badge.bearish { background: rgba(255,139,160,0.10); color: #ff8ba0; }
 421 | .s-badge.neutral { background: rgba(248,193,92,0.10); color: #f8c15c; }
 422 | .s-badge.unclassified { background: rgba(149,160,186,0.08); color: #95a0ba; }
 423 | 
 424 | .narr-chip {
 425 |   font-family: 'JetBrains Mono', monospace;
 426 |   font-size: 9px;
 427 |   font-weight: 700;
 428 |   letter-spacing: 0.08em;
 429 |   text-transform: uppercase;
 430 |   color: #95a0ba;
 431 |   background: rgba(149,160,186,0.07);
 432 |   border-radius: 4px;
 433 |   padding: 2px 5px;
 434 | }
 435 | 
 436 | /* ── Responsive ── */
 437 | @media (max-width: 768px) {
 438 |   .intel-headline { font-size: 1.8rem; }
 439 |   .signal-composite { font-size: 3.5rem; }
 440 |   .intel-page { padding: 90px 16px 60px; }
 441 | }
 442 | 
 443 | @media (max-width: 1200px) {
 444 |   .intel-container { max-width: 100%; }
 445 | }
 446 | </style>
 447 | {% endblock %}
 448 | 
 449 | {% block content %}
 450 | <div class="intel-page">
 451 | <div class="intel-container">
 452 | 
 453 |   <!-- Header -->
 454 |   <div class="mb-4">
 455 |     <div class="intel-eyebrow">SIGNAL INTELLIGENCE • MARKET COMPOSITE</div>
 456 |     <h1 class="intel-headline">Bitcoin Intelligence Dashboard</h1>
 457 |     <p style="color:#95a0ba;font-size:1rem;">
 458 |       Real-time signal strength, narrative tracking, and entity intelligence.
 459 |       <a href="/sentiment" style="color:#f8c15c;text-decoration:none;margin-left:12px;">View Sentiment ↗</a>
 460 |     </p>
 461 |   </div>
 462 | 
 463 |   <!-- Stat Pills Row -->
 464 |   <div class="d-flex gap-3 mb-4 flex-wrap">
 465 |     <div class="stat-pill">
 466 |       <div class="stat-pill-value">{{ article_count_24h }}</div>
 467 |       <div class="stat-pill-label">Articles 24h</div>
 468 |     </div>
 469 |     <div class="stat-pill">
 470 |       {% set fg = signal.components.fear_greed.raw_data if signal.components and signal.components.fear_greed and signal.components.fear_greed.raw_data else None %}
 471 |       <div class="stat-pill-value" style="color:{% if fg and fg.value >= 60 %}#89ffb8{% elif fg and fg.value <= 35 %}#ff8ba0{% else %}#f8c15c{% endif %};">
 472 |         {{ fg.value if fg else '—' }}
 473 |       </div>
 474 |       <div class="stat-pill-label">Fear & Greed</div>
 475 |     </div>
 476 |     <div class="stat-pill">
 477 |       {% set price = signal.btc_price %}
 478 |       <div class="stat-pill-value" style="font-size:1.1rem;">
 479 |         ${{ "{:,.0f}".format(price) if price else '—' }}
 480 |       </div>
 481 |       <div class="stat-pill-label">BTC Price</div>
 482 |     </div>
 483 |     <div class="stat-pill">
 484 |       {% set hash = signal.components.hashrate.value_ehs if signal.components and signal.components.hashrate else None %}
 485 |       <div class="stat-pill-value">{{ "{:.0f}".format(hash) if hash else '—' }}</div>
 486 |       <div class="stat-pill-label">EH/s</div>
 487 |     </div>
 488 |     <div class="stat-pill">
 489 |       <div class="stat-pill-value">{{ intel_events|length }}</div>
 490 |       <div class="stat-pill-label">Events</div>
 491 |     </div>
 492 |   </div>
 493 | 
 494 |   <!-- Row 1: Signal Strength + Components -->
 495 |   <div class="row g-4 mb-4">
 496 |     <!-- Signal composite -->
 497 |     <div class="col-lg-3">
 498 |       <div class="g-card accent-red text-center">
 499 |         <span class="g-eyebrow">Signal Strength</span>
 500 |         <div class="signal-gauge-wrap mb-3">
 501 |           <svg class="signal-gauge-svg" viewBox="0 0 180 180" aria-label="Signal strength gauge">
 502 |             <defs>
 503 |               <linearGradient id="signal-grad" x1="0" y1="1" x2="1" y2="0">
 504 |                 <stop offset="0%" stop-color="#ff3b5f"/>
 505 |                 <stop offset="40%" stop-color="#f8c15c"/>
 506 |                 <stop offset="100%" stop-color="#5de4ff"/>
 507 |               </linearGradient>
 508 |             </defs>
 509 |             <!-- BG circle -->
 510 |             <circle cx="90" cy="90" r="72" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="12"/>
 511 |             <!-- Colored arc -->
 512 |             <circle id="signal-arc" cx="90" cy="90" r="72" fill="none" stroke="url(#signal-grad)"
 513 |                     stroke-width="12" stroke-linecap="round"
 514 |                     stroke-dasharray="452" stroke-dashoffset="452"
 515 |                     transform="rotate(-90 90 90)"/>
 516 |           </svg>
 517 |         </div>
 518 |         <div class="signal-composite" id="signal-num"
 519 |              style="color:{{ signal.color }};">{{ signal.composite|int }}</div>
 520 |         <div class="signal-label" style="color:{{ signal.color }};">{{ signal.label }}</div>
 521 |         <div class="signal-trajectory">
 522 |           {% set traj = signal.trajectory %}
 523 |           {% if 'BULLISH' in traj %}⬆{% elif 'BEARISH' in traj %}⬇{% else %}➡{% endif %}
 524 |           {{ traj|replace('_', ' ') }}
 525 |         </div>
 526 |       </div>
 527 |     </div>
 528 | 
 529 |     <!-- Component breakdown -->
 530 |     <div class="col-lg-4">
 531 |       <div class="g-card">
 532 |         <span class="g-eyebrow">Component Breakdown</span>
 533 |         <div class="component-row">
 534 |           {% if signal.components %}
 535 |           {% for key, comp in signal.components.items() %}
 536 |           {% set score = comp.score|default(50)|float %}
 537 |           {% set barColor = '#89ffb8' if score >= 65 else '#f8c15c' if score >= 45 else '#ff8ba0' %}
 538 |           <div class="comp-item">
 539 |             <div class="comp-header">
 540 |               <span class="comp-label">{{ comp.label|default(key) }} ({{ (comp.weight * 100)|int }}%)</span>
 541 |               <span class="comp-score">{{ score|int }}</span>
 542 |             </div>
 543 |             <div class="comp-bar-track">
 544 |               <div class="comp-bar-fill" style="width:{{ score|int }}%;background:{{ barColor }};"></div>
 545 |             </div>
 546 |             <div class="comp-desc">{{ comp.description|default('')|truncate(60) }}</div>
 547 |           </div>
 548 |           {% endfor %}
 549 |           {% else %}
 550 |           <p class="text-muted small">No component data.</p>
 551 |           {% endif %}
 552 |         </div>
 553 |       </div>
 554 |     </div>
 555 | 
 556 |     <!-- Fear & Greed widget -->
 557 |     <div class="col-lg-2">
 558 |       <div class="g-card accent-gold text-center">
 559 |         <span class="g-eyebrow">Fear & Greed</span>
 560 |         {% set fg = signal.components.fear_greed.raw_data if signal.components and signal.components.fear_greed and signal.components.fear_greed.raw_data else None %}
 561 |         {% if fg %}
 562 |         <div class="fg-wrap">
 563 |           <div class="fg-value"
 564 |                style="color:{% if fg.value >= 75 %}#5de4ff{% elif fg.value >= 55 %}#89ffb8{% elif fg.value >= 45 %}#f8c15c{% elif fg.value >= 25 %}#ff8ba0{% else %}#ff3b5f{% endif %};">
 565 |             {{ fg.value }}
 566 |           </div>
 567 |           <div class="fg-label"
 568 |                style="color:{% if fg.value >= 75 %}#5de4ff{% elif fg.value >= 55 %}#89ffb8{% elif fg.value >= 45 %}#f8c15c{% elif fg.value >= 25 %}#ff8ba0{% else %}#ff3b5f{% endif %};">
 569 |             {{ fg.classification }}
 570 |           </div>
 571 |           {% if fg.history %}
 572 |           <div class="fg-history">
 573 |             {% for h in fg.history|reverse %}
 574 |             {% set hpct = (h.value / 100 * 36)|int %}
 575 |             <div class="fg-bar"
 576 |                  style="height:{{ [hpct, 4]|max }}px;background:{% if h.value >= 55 %}#89ffb8{% elif h.value >= 45 %}#f8c15c{% else %}#ff8ba0{% endif %};opacity:0.7;"></div>
 577 |             {% endfor %}
 578 |           </div>
 579 |           {% endif %}
 580 |         </div>
 581 |         {% else %}
 582 |         <div class="fg-wrap" style="padding:20px 0;">
 583 |           <div class="fg-value" style="color:#95a0ba;">—</div>
 584 |           <div class="fg-label" style="color:#4a5568;">Loading…</div>
 585 |         </div>
 586 |         {% endif %}
 587 |       </div>
 588 |     </div>
 589 | 
 590 |     <!-- Narrative timeline -->
 591 |     <div class="col-lg-3">
 592 |       <div class="g-card">
 593 |         <span class="g-eyebrow">7-Day Narrative Timeline</span>
 594 |         <div class="narr-timeline">
 595 |           {% if narrative_timeline %}
 596 |           {% for day in narrative_timeline %}
 597 |           {% set sc = day.score|float %}
 598 |           <div class="narr-day">
 599 |             <span class="narr-date">{{ day.date }}</span>
 600 |             <span class="narr-narrative">{{ day.dominant_narrative }}</span>
 601 |             <span class="narr-score"
 602 |                   style="color:{% if sc >= 60 %}#89ffb8{% elif sc <= 40 %}#ff8ba0{% else %}#f8c15c{% endif %};">
 603 |               {{ sc|int }}
 604 |             </span>
 605 |           </div>
 606 |           {% endfor %}
 607 |           {% else %}
 608 |           <p class="text-muted small">No narrative data yet.</p>
 609 |           {% endif %}
 610 |         </div>
 611 |       </div>
 612 |     </div>
 613 |   </div>
 614 | 
 615 |   <!-- Row 2: Topic Cloud + Entity Tracker -->
 616 |   <div class="row g-4 mb-4">
 617 |     <!-- Trending Topics Cloud -->
 618 |     <div class="col-lg-5">
 619 |       <div class="g-card accent-cyan">
 620 |         <span class="g-eyebrow">Trending Topics (24h)</span>
 621 |         {% if trending %}
 622 |         <div class="topic-cloud">
 623 |           {% for topic in trending %}
 624 |           <span class="topic-word {{ topic.sentiment }}"
 625 |                 style="font-size:{{ topic.size }}px;"
 626 |                 title="{{ topic.count }} articles — {{ topic.sentiment }}">
 627 |             {{ topic.topic }}
 628 |           </span>
 629 |           {% endfor %}
 630 |         </div>
 631 |         <div class="mt-3 d-flex gap-3" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;">
 632 |           <span style="color:#89ffb8;">● Bullish</span>
 633 |           <span style="color:#ff8ba0;">● Bearish</span>
 634 |           <span style="color:#eef2ff;">● Neutral</span>
 635 |         </div>
 636 |         {% else %}
 637 |         <p class="text-muted small">No trending topics data. Run batch classification to populate.</p>
 638 |         {% endif %}
 639 |       </div>
 640 |     </div>
 641 | 
 642 |     <!-- Entity Tracker -->
 643 |     <div class="col-lg-7">
 644 |       <div class="g-card">
 645 |         <span class="g-eyebrow">Entity Tracker (48h)</span>
 646 |         {% if entities %}
 647 |         <div style="overflow-x:auto;">
 648 |           <table class="entity-table">
 649 |             <thead>
 650 |               <tr>
 651 |                 <th>Entity</th>
 652 |                 <th>Type</th>
 653 |                 <th>Mentions</th>
 654 |                 <th>Sentiment</th>
 655 |                 <th>Trend</th>
 656 |               </tr>
 657 |             </thead>
 658 |             <tbody>
 659 |               {% for ent in entities[:12] %}
 660 |               <tr>
 661 |                 <td style="font-weight:600;">{{ ent.entity }}</td>
 662 |                 <td><span class="entity-type">{{ ent.type }}</span></td>
 663 |                 <td style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f8c15c;">{{ ent.mention_count }}</td>
 664 |                 <td>
 665 |                   <span class="s-badge {{ ent.sentiment }}">
 666 |                     {% if ent.sentiment == 'bullish' %}▲{% elif ent.sentiment == 'bearish' %}▼{% else %}●{% endif %}
 667 |                     {{ ent.sentiment }}
 668 |                   </span>
 669 |                 </td>
 670 |                 <td style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#95a0ba;">
 671 |                   {% if ent.trend == 'up' %}▲ rising{% elif ent.trend == 'down' %}▼ falling{% else %}→ stable{% endif %}
 672 |                 </td>
 673 |               </tr>
 674 |               {% endfor %}
 675 |             </tbody>
 676 |           </table>
 677 |         </div>
 678 |         {% else %}
 679 |         <p class="text-muted small">No entity data. Articles need titles mentioning tracked entities.</p>
 680 |         {% endif %}
 681 |       </div>
 682 |     </div>
 683 |   </div>
 684 | 
 685 |   <!-- Row 3: Intelligence Events + Article Stream -->
 686 |   <div class="row g-4">
 687 |     <!-- Intelligence Events -->
 688 |     <div class="col-lg-4">
 689 |       <div class="g-card accent-red">
 690 |         <span class="g-eyebrow">Intelligence Events</span>
 691 |         {% if intel_events %}
 692 |         {% for evt in intel_events %}
 693 |         <div class="evt-item">
 694 |           <span class="evt-badge {{ evt.severity }}">{{ evt.severity }}</span>
 695 |           <div>
 696 |             <div style="font-size:12px;color:#eef2ff;line-height:1.4;margin-bottom:4px;">{{ evt.description|truncate(140) }}</div>
 697 |             <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#4a5568;">
 698 |               {{ evt.event_type|replace('_', ' ')|upper }} • {{ evt.created_at }}</div>
 699 |           </div>
 700 |         </div>
 701 |         {% endfor %}
 702 |         {% else %}
 703 |         <div class="text-center py-4">
 704 |           <div style="color:#95a0ba;font-size:28px;margin-bottom:8px;">✓</div>
 705 |           <div style="color:#95a0ba;font-size:13px;">No anomalies detected.</div>
 706 |           <div style="color:#4a5568;font-size:11px;margin-top:4px;">All signals within normal range.</div>
 707 |         </div>
 708 |         {% endif %}
 709 |       </div>
 710 |     </div>
 711 | 
 712 |     <!-- Article Stream (by importance) -->
 713 |     <div class="col-lg-8">
 714 |       <div class="g-card">
 715 |         <div class="d-flex align-items-center justify-content-between mb-4">
 716 |           <span class="g-eyebrow" style="margin-bottom:0;">Article Stream — Sorted by Importance</span>
 717 |           <a href="/articles" style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#f8c15c;text-decoration:none;font-weight:700;letter-spacing:0.10em;">ALL ARTICLES ↗</a>
 718 |         </div>
 719 | 
 720 |         {% if top_articles %}
 721 |         {% for art in top_articles %}
 722 |         {% set imp = art.importance_score|default(50)|int %}
 723 |         <div class="art-stream-item">
 724 |           <div class="art-rank">{{ loop.index }}</div>
 725 |           <div>
 726 |             <div class="art-title">
 727 |               <a href="/articles/{{ art.id }}" style="color:inherit;text-decoration:none;">
 728 |                 {{ art.title|truncate(120) }}
 729 |               </a>
 730 |             </div>
 731 |             <div class="art-meta">
 732 |               <span class="s-badge {{ art.sentiment }}">
 733 |                 {% if art.sentiment == 'bullish' %}▲{% elif art.sentiment == 'bearish' %}▼{% else %}●{% endif %}
 734 |                 {{ art.sentiment }}
 735 |               </span>
 736 |               {% if art.narrative_label and art.narrative_label != '—' %}
 737 |               <span class="narr-chip">{{ art.narrative_label }}</span>
 738 |               {% endif %}
 739 |               <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#4a5568;">{{ art.created_at[:10] }}</span>
 740 |             </div>
 741 |           </div>
 742 |           <div style="text-align:right;flex-shrink:0;">
 743 |             <div class="art-imp"
 744 |                  style="color:{% if imp >= 70 %}#f8c15c{% elif imp >= 50 %}#95a0ba{% else %}#4a5568{% endif %};">
 745 |               {{ imp }}
 746 |             </div>
 747 |             <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:0.12em;color:#4a5568;">IMP</div>
 748 |           </div>
 749 |         </div>
 750 |         {% endfor %}
 751 |         {% else %}
 752 |         <div class="text-center py-5">
 753 |           <div style="font-size:2rem;margin-bottom:12px;">📡</div>
 754 |           <div style="color:#95a0ba;font-size:14px;">No articles classified yet.</div>
 755 |           <div style="color:#4a5568;font-size:12px;margin-top:4px;">Run: python -m services.sentiment_analyzer batch --hours=24</div>
 756 |         </div>
 757 |         {% endif %}
 758 |       </div>
 759 |     </div>
 760 |   </div>
 761 | 
 762 | </div><!-- /intel-container -->
 763 | </div><!-- /intel-page -->
 764 | {% endblock %}
 765 | 
 766 | {% block extra_js %}
 767 | <script>
 768 | (function() {
 769 |   'use strict';
 770 | 
 771 |   // ── Signal strength radial gauge ─────────────────────────────────────────
 772 |   const composite = {{ signal.composite|default(50) }};
 773 |   const arcEl = document.getElementById('signal-arc');
 774 | 
 775 |   function animateSignalGauge() {
 776 |     if (!arcEl) return;
 777 |     const circumference = 452;
 778 |     const targetOffset = circumference * (1 - composite / 100);
 779 |     const t0 = performance.now();
 780 |     const dur = 1400;
 781 | 
 782 |     function step(t) {
 783 |       const progress = Math.min((t - t0) / dur, 1);
 784 |       const ease = 1 - Math.pow(1 - progress, 3);
 785 |       arcEl.setAttribute('stroke-dashoffset', circumference - (circumference - targetOffset) * ease);
 786 |       if (progress < 1) requestAnimationFrame(step);
 787 |     }
 788 |     requestAnimationFrame(step);
 789 |   }
 790 | 
 791 |   animateSignalGauge();
 792 | 
 793 |   // ── Auto-refresh signal strength every 5 minutes ─────────────────────────
 794 |   setInterval(async () => {
 795 |     try {
 796 |       const r = await fetch('/api/intelligence/signal');
 797 |       if (!r.ok) return;
 798 |       const data = await r.json();
 799 |       if (!data.success || !data.data) return;
 800 |       const sig = data.data;
 801 |       const numEl = document.getElementById('signal-num');
 802 |       if (numEl) {
 803 |         numEl.textContent = Math.round(sig.composite);
 804 |         numEl.style.color = sig.color;
 805 |       }
 806 |     } catch (e) { /* ignore */ }
 807 |   }, 300000); // 5 minutes
 808 | 
 809 | })();
 810 | </script>
 811 | {% endblock %}
 812 | 
```

### File: services/sovereign_context_engine.py (770 lines)
```
   1 | """
   2 | Sovereign Context Engine — Unified Intelligence Brain
   3 | 
   4 | Reads ALL Protocol Pulse data streams, maintains a world-state snapshot,
   5 | detects cross-stream patterns, and emits SOVEREIGN ALERTS when multiple
   6 | streams confirm the same signal.
   7 | 
   8 | Every downstream system reads from this engine:
   9 |   Oracle briefings, Stage content, article generator,
  10 |   intelligence terminal, PANOPTICON dashboard.
  11 | 
  12 | Usage:
  13 |   python3 services/sovereign_context_engine.py --cycle
  14 | """
  15 | 
  16 | import argparse
  17 | import hashlib
  18 | import json
  19 | import logging
  20 | import os
  21 | import sqlite3
  22 | import sys
  23 | import time
  24 | from datetime import datetime, timezone
  25 | from pathlib import Path
  26 | from typing import Any, Dict, List, Optional
  27 | 
  28 | import requests
  29 | 
  30 | # ---------------------------------------------------------------------------
  31 | # Paths
  32 | # ---------------------------------------------------------------------------
  33 | BASE_DIR = Path(__file__).resolve().parent.parent
  34 | DATA_DIR = BASE_DIR / "data"
  35 | CONTEXT_DIR = DATA_DIR / "sovereign_context"
  36 | LATEST_PATH = CONTEXT_DIR / "latest.json"
  37 | HISTORY_PATH = CONTEXT_DIR / "history.jsonl"
  38 | ALERTS_DB_PATH = DATA_DIR / "sovereign_alerts.db"
  39 | SOVEREIGN_INTEL_DB = DATA_DIR / "sovereign_intel.db"
  40 | SENTINEL_ALERTS_DB = DATA_DIR / "sentinel_alerts.db"
  41 | ACTIVE_SIGNAL_PATH = BASE_DIR / "video_pipeline_v3" / "cache" / "active_signal.json"
  42 | STAGE_BRIEF_PATH = BASE_DIR / "video_pipeline_v3" / "data" / "stage_briefs" / "latest.json"
  43 | PRICE_CACHE_PATH = DATA_DIR / "price_cache.json"
  44 | 
  45 | # ---------------------------------------------------------------------------
  46 | # Logging
  47 | # ---------------------------------------------------------------------------
  48 | logging.basicConfig(
  49 |     level=logging.INFO,
  50 |     format="%(asctime)s [SCE] %(levelname)s %(message)s",
  51 |     datefmt="%Y-%m-%d %H:%M:%S",
  52 | )
  53 | log = logging.getLogger("sovereign_context_engine")
  54 | 
  55 | # ---------------------------------------------------------------------------
  56 | # HTTP helpers
  57 | # ---------------------------------------------------------------------------
  58 | SESSION = requests.Session()
  59 | SESSION.headers.update({"User-Agent": "ProtocolPulse/SovereignContext/1.0"})
  60 | REQ_TIMEOUT = 12
  61 | 
  62 | 
  63 | def _get_json(url: str, timeout: int = REQ_TIMEOUT) -> Optional[dict]:
  64 |     """Safe JSON GET — returns None on any failure."""
  65 |     try:
  66 |         r = SESSION.get(url, timeout=timeout)
  67 |         r.raise_for_status()
  68 |         return r.json()
  69 |     except Exception as exc:
  70 |         log.warning("GET %s failed: %s", url, exc)
  71 |         return None
  72 | 
  73 | 
  74 | def _read_json_file(path: Path) -> Optional[dict]:
  75 |     """Read a local JSON file, return None on failure."""
  76 |     try:
  77 |         if path.exists():
  78 |             return json.loads(path.read_text())
  79 |     except Exception as exc:
  80 |         log.warning("Read %s failed: %s", path, exc)
  81 |     return None
  82 | 
  83 | 
  84 | # ---------------------------------------------------------------------------
  85 | # Alerts DB setup
  86 | # ---------------------------------------------------------------------------
  87 | def _init_alerts_db():
  88 |     """Create sovereign_alerts.db if needed."""
  89 |     conn = sqlite3.connect(str(ALERTS_DB_PATH))
  90 |     conn.execute("""
  91 |         CREATE TABLE IF NOT EXISTS sovereign_alerts (
  92 |             id INTEGER PRIMARY KEY AUTOINCREMENT,
  93 |             ts_utc TEXT NOT NULL,
  94 |             pattern_id TEXT NOT NULL,
  95 |             title TEXT NOT NULL,
  96 |             description TEXT,
  97 |             severity TEXT DEFAULT 'WATCH',
  98 |             data_json TEXT,
  99 |             fingerprint TEXT UNIQUE
 100 |         )
 101 |     """)
 102 |     conn.execute("""
 103 |         CREATE INDEX IF NOT EXISTS idx_sa_ts ON sovereign_alerts(ts_utc DESC)
 104 |     """)
 105 |     conn.commit()
 106 |     conn.close()
 107 | 
 108 | 
 109 | # ===================================================================
 110 | # DATA COLLECTORS — one per stream
 111 | # ===================================================================
 112 | 
 113 | def _fetch_btc_price() -> dict:
 114 |     """BTC price from CoinGecko (same source as price_service.py)."""
 115 |     data = _get_json(
 116 |         "https://api.coingecko.com/api/v3/simple/price"
 117 |         "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
 118 |         "&include_7d_change=true&include_market_cap=true"
 119 |     )
 120 |     if not data or "bitcoin" not in data:
 121 |         return {"price": 0, "change_24h": 0, "change_7d": 0, "market_cap": 0, "dominance": 0}
 122 |     btc = data["bitcoin"]
 123 |     # Dominance from CoinGecko global
 124 |     dom = 0
 125 |     g = _get_json("https://api.coingecko.com/api/v3/global")
 126 |     if g and "data" in g:
 127 |         dom = round(g["data"].get("market_cap_percentage", {}).get("btc", 0), 1)
 128 |     return {
 129 |         "price": btc.get("usd", 0),
 130 |         "change_24h": round(btc.get("usd_24h_change", 0), 2),
 131 |         "change_7d": round(btc.get("usd_7d_change", 0) if "usd_7d_change" in btc else 0, 2),
 132 |         "market_cap": btc.get("usd_market_cap", 0),
 133 |         "dominance": dom,
 134 |     }
 135 | 
 136 | 
 137 | def _fetch_fear_greed() -> dict:
 138 |     """Fear & Greed Index from alternative.me."""
 139 |     data = _get_json("https://api.alternative.me/fng/?limit=1")
 140 |     if not data or "data" not in data:
 141 |         return {"value": 50, "label": "Neutral"}
 142 |     d = data["data"][0]
 143 |     return {"value": int(d.get("value", 50)), "label": d.get("value_classification", "Neutral")}
 144 | 
 145 | 
 146 | def _fetch_mempool() -> dict:
 147 |     """Mempool stats + fee estimates from mempool.space."""
 148 |     stats = _get_json("https://mempool.space/api/mempool") or {}
 149 |     fees = _get_json("https://mempool.space/api/v1/fees/recommended") or {}
 150 |     return {
 151 |         "fee_low": fees.get("economyFee", 0),
 152 |         "fee_mid": fees.get("halfHourFee", 0),
 153 |         "fee_high": fees.get("fastestFee", 0),
 154 |         "unconfirmed": stats.get("count", 0),
 155 |         "size_mb": round(stats.get("vsize", 0) / 1_000_000, 1),
 156 |     }
 157 | 
 158 | 
 159 | def _fetch_network() -> dict:
 160 |     """Hashrate, difficulty, next adjustment from mempool.space."""
 161 |     hr_data = _get_json("https://mempool.space/api/v1/mining/hashrate/3d")
 162 |     diff = _get_json("https://mempool.space/api/v1/difficulty-adjustment") or {}
 163 |     block_height = 0
 164 |     tip = _get_json("https://mempool.space/api/blocks/tip/height")
 165 |     if isinstance(tip, int):
 166 |         block_height = tip
 167 |     elif isinstance(tip, dict):
 168 |         block_height = tip.get("height", 0)
 169 | 
 170 |     hashrate_eh = 0
 171 |     if hr_data and "currentHashrate" in hr_data:
 172 |         hashrate_eh = round(hr_data["currentHashrate"] / 1e18, 1)
 173 |     elif hr_data and "hashrates" in hr_data and hr_data["hashrates"]:
 174 |         last = hr_data["hashrates"][-1]
 175 |         hashrate_eh = round(last.get("avgHashrate", 0) / 1e18, 1)
 176 | 
 177 |     return {
 178 |         "hashrate_eh": hashrate_eh,
 179 |         "difficulty": diff.get("difficulty", 0),
 180 |         "next_adj_pct": round(diff.get("difficultyChange", 0), 2),
 181 |         "next_adj_blocks": diff.get("remainingBlocks", 0),
 182 |         "block_height": block_height,
 183 |     }
 184 | 
 185 | 
 186 | def _fetch_lightning() -> dict:
 187 |     """Lightning Network stats from mempool.space."""
 188 |     data = _get_json("https://mempool.space/api/v1/lightning/statistics/latest")
 189 |     if not data or "latest" not in data:
 190 |         return {"capacity_btc": 0, "channels": 0, "nodes": 0}
 191 |     ln = data["latest"]
 192 |     return {
 193 |         "capacity_btc": round(ln.get("total_capacity", 0) / 1e8, 1),
 194 |         "channels": ln.get("channel_count", 0),
 195 |         "nodes": ln.get("node_count", 0),
 196 |     }
 197 | 
 198 | 
 199 | def _fetch_kol_sentiment() -> dict:
 200 |     """KOL sentiment from kol_pulse_item table (last 50 posts)."""
 201 |     db_path = BASE_DIR / "instance" / "protocol_pulse.db"
 202 |     if not db_path.exists():
 203 |         db_path = BASE_DIR / "protocol_pulse.db"
 204 |     if not db_path.exists():
 205 |         return {"sentiment_score": 50, "top_topics": [], "post_count_24h": 0}
 206 | 
 207 |     try:
 208 |         conn = sqlite3.connect(str(db_path))
 209 |         conn.row_factory = sqlite3.Row
 210 | 
 211 |         # Count posts in last 24h
 212 |         row = conn.execute(
 213 |             "SELECT COUNT(*) as cnt FROM kol_pulse_item "
 214 |             "WHERE created_at > datetime('now', '-1 day')"
 215 |         ).fetchone()
 216 |         count_24h = row["cnt"] if row else 0
 217 | 
 218 |         # Last 50 posts for basic topic extraction
 219 |         rows = conn.execute(
 220 |             "SELECT content FROM kol_pulse_item ORDER BY created_at DESC LIMIT 50"
 221 |         ).fetchall()
 222 |         conn.close()
 223 | 
 224 |         # Simple keyword-based topic extraction
 225 |         topic_counts: Dict[str, int] = {}
 226 |         keywords = {
 227 |             "etf": ["etf", "blackrock", "ishares", "grayscale"],
 228 |             "halving": ["halving", "halvening", "block reward"],
 229 |             "regulation": ["sec", "regulation", "regulatory", "gensler", "congress"],
 230 |             "mining": ["mining", "hashrate", "miner", "asic"],
 231 |             "lightning": ["lightning", "ln", "layer 2", "layer2"],
 232 |             "self-custody": ["self-custody", "self custody", "not your keys", "cold storage"],
 233 |             "macro": ["fed", "inflation", "interest rate", "treasury", "macro"],
 234 |             "stablecoin": ["stablecoin", "usdt", "usdc", "tether"],
 235 |             "defi": ["defi", "dex", "yield", "lending"],
 236 |             "cbdc": ["cbdc", "digital dollar", "digital currency"],
 237 |         }
 238 |         for row in rows:
 239 |             text = (row["content"] or "").lower()
 240 |             for topic, kws in keywords.items():
 241 |                 if any(kw in text for kw in kws):
 242 |                     topic_counts[topic] = topic_counts.get(topic, 0) + 1
 243 | 
 244 |         top_topics = sorted(topic_counts, key=topic_counts.get, reverse=True)[:5]
 245 | 
 246 |         # Rough sentiment: count bullish vs bearish keywords
 247 |         bullish_kw = ["bullish", "moon", "pump", "ath", "accumulate", "buy", "long", "breakout", "green"]
 248 |         bearish_kw = ["bearish", "dump", "crash", "sell", "short", "fear", "capitulation", "red"]
 249 |         bull = sum(1 for r in rows if any(k in (r["content"] or "").lower() for k in bullish_kw))
 250 |         bear = sum(1 for r in rows if any(k in (r["content"] or "").lower() for k in bearish_kw))
 251 |         total = bull + bear
 252 |         sentiment_score = int((bull / total * 100) if total > 0 else 50)
 253 | 
 254 |         return {
 255 |             "sentiment_score": sentiment_score,
 256 |             "top_topics": top_topics,
 257 |             "post_count_24h": count_24h,
 258 |         }
 259 |     except Exception as exc:
 260 |         log.warning("KOL sentiment fetch failed: %s", exc)
 261 |         return {"sentiment_score": 50, "top_topics": [], "post_count_24h": 0}
 262 | 
 263 | 
 264 | def _fetch_article_narrative() -> dict:
 265 |     """Article corpus: last 20 articles, dominant theme, sentiment."""
 266 |     db_path = BASE_DIR / "instance" / "protocol_pulse.db"
 267 |     if not db_path.exists():
 268 |         db_path = BASE_DIR / "protocol_pulse.db"
 269 |     if not db_path.exists():
 270 |         return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}
 271 | 
 272 |     try:
 273 |         conn = sqlite3.connect(str(db_path))
 274 |         conn.row_factory = sqlite3.Row
 275 |         rows = conn.execute(
 276 |             "SELECT title, category, sentiment, narrative_label FROM articles "
 277 |             "ORDER BY created_at DESC LIMIT 20"
 278 |         ).fetchall()
 279 |         conn.close()
 280 | 
 281 |         if not rows:
 282 |             return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}
 283 | 
 284 |         # Dominant theme from narrative_label or category
 285 |         themes: Dict[str, int] = {}
 286 |         sentiments = []
 287 |         for r in rows:
 288 |             label = r["narrative_label"] or r["category"] or "general"
 289 |             themes[label] = themes.get(label, 0) + 1
 290 |             if r["sentiment"]:
 291 |                 sentiments.append(r["sentiment"])
 292 | 
 293 |         dominant = max(themes, key=themes.get) if themes else "unknown"
 294 | 
 295 |         # Aggregate sentiment
 296 |         if sentiments:
 297 |             bull = sum(1 for s in sentiments if s and "bull" in s.lower())
 298 |             bear = sum(1 for s in sentiments if s and "bear" in s.lower())
 299 |             if bull > bear:
 300 |                 agg_sentiment = "bullish"
 301 |             elif bear > bull:
 302 |                 agg_sentiment = "bearish"
 303 |             else:
 304 |                 agg_sentiment = "neutral"
 305 |         else:
 306 |             agg_sentiment = "neutral"
 307 | 
 308 |         return {
 309 |             "dominant_theme": dominant,
 310 |             "sentiment": agg_sentiment,
 311 |             "article_count": len(rows),
 312 |         }
 313 |     except Exception as exc:
 314 |         log.warning("Article narrative fetch failed: %s", exc)
 315 |         return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}
 316 | 
 317 | 
 318 | def _fetch_polymarket() -> dict:
 319 |     """Polymarket crypto/macro sentiment."""
 320 |     try:
 321 |         # Import from existing service
 322 |         sys.path.insert(0, str(BASE_DIR))
 323 |         from services.polymarket_service import (
 324 |             get_bitcoin_markets,
 325 |             get_macro_sentiment_score,
 326 |             get_top_market_by_volume,
 327 |         )
 328 |         top = get_top_market_by_volume()
 329 |         score = get_macro_sentiment_score()
 330 |         return {
 331 |             "macro_sentiment": score,
 332 |             "top_market": top["question"] if top else "N/A",
 333 |             "top_probability": round(max(top["outcomes"].values()), 1) if top and top.get("outcomes") else 0,
 334 |         }
 335 |     except Exception as exc:
 336 |         log.warning("Polymarket fetch failed: %s", exc)
 337 |         return {"macro_sentiment": 50, "top_market": "N/A", "top_probability": 0}
 338 | 
 339 | 
 340 | def _fetch_pcaf_score() -> int:
 341 |     """PCAF anomaly score from active_signal.json (Nostr relay cache)."""
 342 |     data = _read_json_file(ACTIVE_SIGNAL_PATH)
 343 |     if not data:
 344 |         return 0
 345 |     # Score based on filtered post count (higher = more signal activity)
 346 |     return min(data.get("total_scored", 0) * 5, 100)
 347 | 
 348 | 
 349 | def _fetch_exchange_flow() -> str:
 350 |     """Exchange netflow from sentinel_alerts.db or sovereign_intel.db signals."""
 351 |     # Check sovereign_intel signals table for exchange flow direction
 352 |     if SOVEREIGN_INTEL_DB.exists():
 353 |         try:
 354 |             conn = sqlite3.connect(str(SOVEREIGN_INTEL_DB))
 355 |             conn.row_factory = sqlite3.Row
 356 |             row = conn.execute(
 357 |                 "SELECT direction FROM signals "
 358 |                 "WHERE category = 'onchain' AND metric LIKE '%exchange%' "
 359 |                 "ORDER BY ts_utc DESC LIMIT 1"
 360 |             ).fetchone()
 361 |             conn.close()
 362 |             if row:
 363 |                 return row["direction"]
 364 |         except Exception:
 365 |             pass
 366 | 
 367 |     # Check sentinel for whale-related alerts
 368 |     if SENTINEL_ALERTS_DB.exists():
 369 |         try:
 370 |             conn = sqlite3.connect(str(SENTINEL_ALERTS_DB))
 371 |             conn.row_factory = sqlite3.Row
 372 |             row = conn.execute(
 373 |                 "SELECT message FROM alerts "
 374 |                 "WHERE rule LIKE '%exchange%' OR rule LIKE '%whale%' "
 375 |                 "ORDER BY created_at DESC LIMIT 1"
 376 |             ).fetchone()
 377 |             conn.close()
 378 |             if row:
 379 |                 msg = (row["message"] or "").lower()
 380 |                 if "outflow" in msg:
 381 |                     return "outflow"
 382 |                 if "inflow" in msg:
 383 |                     return "inflow"
 384 |         except Exception:
 385 |             pass
 386 | 
 387 |     return "neutral"
 388 | 
 389 | 
 390 | def _fetch_stage_brief() -> dict:
 391 |     """Latest narrative from stage briefs."""
 392 |     data = _read_json_file(STAGE_BRIEF_PATH)
 393 |     if not data:
 394 |         return {"narrative": "N/A", "brief_type": "unknown"}
 395 |     return {
 396 |         "narrative": (data.get("script_summary") or "N/A")[:200],
 397 |         "brief_type": data.get("brief_type", "unknown"),
 398 |     }
 399 | 
 400 | 
 401 | def _fetch_whale_alerts() -> List[dict]:
 402 |     """Recent whale alerts from sentinel_alerts.db."""
 403 |     if not SENTINEL_ALERTS_DB.exists():
 404 |         return []
 405 |     try:
 406 |         conn = sqlite3.connect(str(SENTINEL_ALERTS_DB))
 407 |         conn.row_factory = sqlite3.Row
 408 |         rows = conn.execute(
 409 |             "SELECT tier, rule, message, score, created_at FROM alerts "
 410 |             "ORDER BY created_at DESC LIMIT 5"
 411 |         ).fetchall()
 412 |         conn.close()
 413 |         return [dict(r) for r in rows]
 414 |     except Exception as exc:
 415 |         log.warning("Whale alerts fetch failed: %s", exc)
 416 |         return []
 417 | 
 418 | 
 419 | # ===================================================================
 420 | # PATTERN DETECTION
 421 | # ===================================================================
 422 | 
 423 | class Alert:
 424 |     """A sovereign pattern-match alert."""
 425 | 
 426 |     def __init__(self, pattern_id: str, title: str, description: str,
 427 |                  severity: str = "WATCH", data: Optional[dict] = None):
 428 |         self.pattern_id = pattern_id
 429 |         self.title = title
 430 |         self.description = description
 431 |         self.severity = severity  # CRITICAL, WATCH, NOTE
 432 |         self.data = data or {}
 433 |         self.ts = datetime.now(timezone.utc).isoformat()
 434 | 
 435 |     def fingerprint(self) -> str:
 436 |         """Unique ID per pattern + hour to prevent spam."""
 437 |         hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
 438 |         raw = f"{self.pattern_id}:{hour}"
 439 |         return hashlib.sha256(raw.encode()).hexdigest()[:16]
 440 | 
 441 |     def to_dict(self) -> dict:
 442 |         return {
 443 |             "pattern_id": self.pattern_id,
 444 |             "title": self.title,
 445 |             "description": self.description,
 446 |             "severity": self.severity,
 447 |             "ts": self.ts,
 448 |             "data": self.data,
 449 |         }
 450 | 
 451 | 
 452 | def detect_patterns(ws: dict) -> List[Alert]:
 453 |     """Run all pattern detection rules against the world state."""
 454 |     alerts: List[Alert] = []
 455 | 
 456 |     btc = ws.get("btc", {})
 457 |     fg = ws.get("fear_greed", {})
 458 |     mempool = ws.get("mempool", {})
 459 |     network = ws.get("network", {})
 460 |     lightning = ws.get("lightning", {})
 461 |     kol = ws.get("kol", {})
 462 |     narrative = ws.get("narrative", {})
 463 |     polymarket = ws.get("polymarket", {})
 464 |     exchange_flow = ws.get("exchange_flow", "neutral")
 465 | 
 466 |     fg_val = fg.get("value", 50)
 467 |     change_24h = btc.get("change_24h", 0)
 468 |     hashrate = network.get("hashrate_eh", 0)
 469 |     fee_high = mempool.get("fee_high", 0)
 470 | 
 471 |     # 1. ACCUMULATION SIGNAL
 472 |     # hashrate UP (positive adj) + exchange outflows + FG < 30
 473 |     if (network.get("next_adj_pct", 0) > 0
 474 |             and exchange_flow == "outflow"
 475 |             and fg_val < 30):
 476 |         alerts.append(Alert(
 477 |             "ACCUMULATION",
 478 |             "Stealth accumulation detected",
 479 |             f"Hashrate adj +{network['next_adj_pct']}%, exchange outflows active, "
 480 |             f"Fear & Greed at {fg_val} ({fg.get('label', '')}).",
 481 |             severity="WATCH",
 482 |             data={"fg": fg_val, "adj_pct": network["next_adj_pct"], "flow": exchange_flow},
 483 |         ))
 484 | 
 485 |     # 2. SUPPLY SHOCK PRECURSOR
 486 |     # hashrate UP + price DOWN + miners not capitulating
 487 |     if (network.get("next_adj_pct", 0) > 0
 488 |             and change_24h < -2
 489 |             and hashrate > 0):
 490 |         alerts.append(Alert(
 491 |             "SUPPLY_SHOCK",
 492 |             "Miners not capitulating — supply shock risk",
 493 |             f"Hashrate {hashrate} EH/s (adj +{network['next_adj_pct']}%), "
 494 |             f"price down {change_24h}% — miners holding.",
 495 |             severity="WATCH",
 496 |             data={"hashrate": hashrate, "change_24h": change_24h},
 497 |         ))
 498 | 
 499 |     # 3. NARRATIVE DIVERGENCE
 500 |     # article sentiment BULLISH + KOL sentiment BEARISH (or vice versa)
 501 |     art_sent = narrative.get("sentiment", "neutral")
 502 |     kol_score = kol.get("sentiment_score", 50)
 503 |     if art_sent == "bullish" and kol_score < 35:
 504 |         alerts.append(Alert(
 505 |             "NARRATIVE_DIVERGENCE",
 506 |             "Narrative split — watch for resolution",
 507 |             f"Articles bullish but KOL sentiment at {kol_score}/100 (bearish). "
 508 |             "Divergence often precedes volatility.",
 509 |             severity="WATCH",
 510 |             data={"article_sentiment": art_sent, "kol_score": kol_score},
 511 |         ))
 512 |     elif art_sent == "bearish" and kol_score > 65:
 513 |         alerts.append(Alert(
 514 |             "NARRATIVE_DIVERGENCE",
 515 |             "Narrative split — watch for resolution",
 516 |             f"Articles bearish but KOL sentiment at {kol_score}/100 (bullish). "
 517 |             "Divergence often precedes volatility.",
 518 |             severity="WATCH",
 519 |             data={"article_sentiment": art_sent, "kol_score": kol_score},
 520 |         ))
 521 | 
 522 |     # 4. POLYMARKET CONFIRMATION
 523 |     # Big probability shift + KOL mention overlap
 524 |     poly_sent = polymarket.get("macro_sentiment", 50)
 525 |     if abs(poly_sent - 50) > 20 and kol.get("post_count_24h", 0) > 10:
 526 |         direction = "bullish" if poly_sent > 50 else "bearish"
 527 |         alerts.append(Alert(
 528 |             "POLYMARKET_CONFIRM",
 529 |             "Market consensus shifting",
 530 |             f"Polymarket sentiment {poly_sent}/100 ({direction}), "
 531 |             f"{kol['post_count_24h']} KOL posts in 24h — consensus forming.",
 532 |             severity="WATCH",
 533 |             data={"poly_sentiment": poly_sent, "kol_posts": kol["post_count_24h"]},
 534 |         ))
 535 | 
 536 |     # 5. MEMPOOL PRESSURE
 537 |     # fees > 50 sat/vB + Lightning growing
 538 |     if fee_high > 50 and lightning.get("capacity_btc", 0) > 0:
 539 |         alerts.append(Alert(
 540 |             "MEMPOOL_PRESSURE",
 541 |             "On-chain congestion — Lightning demand increasing",
 542 |             f"Priority fees at {fee_high} sat/vB, Lightning capacity "
 543 |             f"{lightning['capacity_btc']} BTC across {lightning['channels']} channels.",
 544 |             severity="NOTE",
 545 |             data={"fee_high": fee_high, "ln_capacity": lightning["capacity_btc"]},
 546 |         ))
 547 | 
 548 |     # 6. FEAR CAPITULATION
 549 |     # FG < 15 + exchange inflows + price DOWN >5%
 550 |     if fg_val < 15 and exchange_flow == "inflow" and change_24h < -5:
 551 |         alerts.append(Alert(
 552 |             "FEAR_CAPITULATION",
 553 |             "Extreme fear — historically bullish 30-day forward",
 554 |             f"Fear & Greed at {fg_val}, exchange inflows active, "
 555 |             f"price down {change_24h}%. Capitulation pattern detected.",
 556 |             severity="CRITICAL",
 557 |             data={"fg": fg_val, "change_24h": change_24h, "flow": exchange_flow},
 558 |         ))
 559 | 
 560 |     # 7. CROSS-ASSET DIVERGENCE
 561 |     # 3+ signals diverge from their baseline simultaneously
 562 |     divergence_count = 0
 563 |     divergence_details = []
 564 | 
 565 |     if abs(change_24h) > 5:
 566 |         divergence_count += 1
 567 |         divergence_details.append(f"Price {change_24h:+.1f}%")
 568 |     if abs(fg_val - 50) > 25:
 569 |         divergence_count += 1
 570 |         divergence_details.append(f"F&G {fg_val}")
 571 |     if abs(kol_score - 50) > 25:
 572 |         divergence_count += 1
 573 |         divergence_details.append(f"KOL {kol_score}")
 574 |     if abs(poly_sent - 50) > 25:
 575 |         divergence_count += 1
 576 |         divergence_details.append(f"Polymarket {poly_sent}")
 577 |     if fee_high > 100:
 578 |         divergence_count += 1
 579 |         divergence_details.append(f"Fees {fee_high} sat/vB")
 580 | 
 581 |     if divergence_count >= 3:
 582 |         alerts.append(Alert(
 583 |             "CROSS_DIVERGENCE",
 584 |             "DIVERGENCE ALERT — major move probable 24-72h",
 585 |             f"{divergence_count} signals diverging: {', '.join(divergence_details)}. "
 586 |             "Multiple streams confirming unusual activity.",
 587 |             severity="CRITICAL",
 588 |             data={"count": divergence_count, "details": divergence_details},
 589 |         ))
 590 | 
 591 |     return alerts
 592 | 
 593 | 
 594 | # ===================================================================
 595 | # ALERT PERSISTENCE
 596 | # ===================================================================
 597 | 
 598 | def emit_alerts(alerts: List[Alert]):
 599 |     """Write alerts to sovereign_alerts.db (dedup by fingerprint per hour)."""
 600 |     if not alerts:
 601 |         return
 602 |     _init_alerts_db()
 603 |     conn = sqlite3.connect(str(ALERTS_DB_PATH))
 604 |     inserted = 0
 605 |     for a in alerts:
 606 |         try:
 607 |             conn.execute(
 608 |                 "INSERT OR IGNORE INTO sovereign_alerts "
 609 |                 "(ts_utc, pattern_id, title, description, severity, data_json, fingerprint) "
 610 |                 "VALUES (?, ?, ?, ?, ?, ?, ?)",
 611 |                 (a.ts, a.pattern_id, a.title, a.description,
 612 |                  a.severity, json.dumps(a.data), a.fingerprint()),
 613 |             )
 614 |             inserted += 1
 615 |         except sqlite3.IntegrityError:
 616 |             pass  # duplicate fingerprint — already emitted this hour
 617 |     conn.commit()
 618 |     conn.close()
 619 |     if inserted:
 620 |         log.info("Emitted %d new alert(s): %s",
 621 |                  inserted, ", ".join(a.pattern_id for a in alerts))
 622 | 
 623 | 
 624 | # ===================================================================
 625 | # MAIN ENGINE
 626 | # ===================================================================
 627 | 
 628 | class SovereignContextEngine:
 629 |     """The connective brain that unifies all Protocol Pulse data streams."""
 630 | 
 631 |     def build_world_state(self) -> dict:
 632 |         """Assemble everything into one JSON world state."""
 633 |         log.info("Building world state...")
 634 |         t0 = time.monotonic()
 635 | 
 636 |         # Fetch all streams
 637 |         btc = _fetch_btc_price()
 638 |         fg = _fetch_fear_greed()
 639 |         mempool = _fetch_mempool()
 640 |         network = _fetch_network()
 641 |         lightning = _fetch_lightning()
 642 |         kol = _fetch_kol_sentiment()
 643 |         narrative = _fetch_article_narrative()
 644 |         polymarket = _fetch_polymarket()
 645 |         pcaf = _fetch_pcaf_score()
 646 |         exchange_flow = _fetch_exchange_flow()
 647 |         stage = _fetch_stage_brief()
 648 |         whale_alerts = _fetch_whale_alerts()
 649 | 
 650 |         block_height = network.pop("block_height", 0)
 651 | 
 652 |         world_state = {
 653 |             "timestamp": datetime.now(timezone.utc).isoformat(),
 654 |             "block_height": block_height,
 655 |             "btc": btc,
 656 |             "fear_greed": fg,
 657 |             "mempool": mempool,
 658 |             "network": network,
 659 |             "lightning": lightning,
 660 |             "kol": kol,
 661 |             "narrative": narrative,
 662 |             "polymarket": polymarket,
 663 |             "pcaf_score": pcaf,
 664 |             "exchange_flow": exchange_flow,
 665 |             "stage_brief": stage,
 666 |             "whale_alerts": whale_alerts,
 667 |             "active_alerts": [],
 668 |             "pattern_matches": [],
 669 |         }
 670 | 
 671 |         elapsed = time.monotonic() - t0
 672 |         log.info("World state built in %.1fs — BTC $%s, F&G %s, Hashrate %s EH/s",
 673 |                  elapsed, f"{btc['price']:,.0f}", fg["value"], network["hashrate_eh"])
 674 |         return world_state
 675 | 
 676 |     def run_cycle(self) -> dict:
 677 |         """Full cycle: build state → detect patterns → emit alerts → save."""
 678 |         log.info("=== Sovereign Context Cycle Start ===")
 679 |         t0 = time.monotonic()
 680 | 
 681 |         # 1. Build world state
 682 |         ws = self.build_world_state()
 683 | 
 684 |         # 2. Detect patterns
 685 |         alerts = detect_patterns(ws)
 686 |         ws["active_alerts"] = [a.to_dict() for a in alerts]
 687 |         ws["pattern_matches"] = [a.pattern_id for a in alerts]
 688 | 
 689 |         if alerts:
 690 |             log.info("Detected %d pattern(s): %s",
 691 |                      len(alerts), ", ".join(a.pattern_id for a in alerts))
 692 |         else:
 693 |             log.info("No pattern matches this cycle")
 694 | 
 695 |         # 3. Emit alerts to DB
 696 |         emit_alerts(alerts)
 697 | 
 698 |         # 4. Save latest snapshot
 699 |         CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
 700 |         LATEST_PATH.write_text(json.dumps(ws, indent=2, default=str))
 701 |         log.info("Saved latest.json (%d bytes)", LATEST_PATH.stat().st_size)
 702 | 
 703 |         # 5. Append to history
 704 |         with open(HISTORY_PATH, "a") as f:
 705 |             f.write(json.dumps(ws, default=str) + "\n")
 706 | 
 707 |         elapsed = time.monotonic() - t0
 708 |         log.info("=== Cycle complete in %.1fs — %d alerts ===", elapsed, len(alerts))
 709 |         return ws
 710 | 
 711 | 
 712 | # ===================================================================
 713 | # Flask route helper (imported by app.py)
 714 | # ===================================================================
 715 | 
 716 | def get_latest_context() -> Optional[dict]:
 717 |     """Read the latest sovereign context snapshot for API serving."""
 718 |     return _read_json_file(LATEST_PATH)
 719 | 
 720 | 
 721 | def get_recent_alerts(limit: int = 20) -> List[dict]:
 722 |     """Read recent alerts from sovereign_alerts.db."""
 723 |     if not ALERTS_DB_PATH.exists():
 724 |         return []
 725 |     try:
 726 |         conn = sqlite3.connect(str(ALERTS_DB_PATH))
 727 |         conn.row_factory = sqlite3.Row
 728 |         rows = conn.execute(
 729 |             "SELECT ts_utc, pattern_id, title, description, severity, data_json "
 730 |             "FROM sovereign_alerts ORDER BY ts_utc DESC LIMIT ?",
 731 |             (limit,)
 732 |         ).fetchall()
 733 |         conn.close()
 734 |         results = []
 735 |         for r in rows:
 736 |             d = dict(r)
 737 |             d["data"] = json.loads(d.pop("data_json", "{}"))
 738 |             results.append(d)
 739 |         return results
 740 |     except Exception:
 741 |         return []
 742 | 
 743 | 
 744 | # ===================================================================
 745 | # CLI entrypoint
 746 | # ===================================================================
 747 | 
 748 | def main():
 749 |     parser = argparse.ArgumentParser(description="Sovereign Context Engine")
 750 |     parser.add_argument("--cycle", action="store_true", help="Run one full cycle")
 751 |     args = parser.parse_args()
 752 | 
 753 |     if args.cycle:
 754 |         engine = SovereignContextEngine()
 755 |         ws = engine.run_cycle()
 756 |         print(json.dumps({
 757 |             "status": "ok",
 758 |             "btc_price": ws["btc"]["price"],
 759 |             "fear_greed": ws["fear_greed"]["value"],
 760 |             "hashrate_eh": ws["network"]["hashrate_eh"],
 761 |             "alerts": len(ws["active_alerts"]),
 762 |             "patterns": ws["pattern_matches"],
 763 |         }, indent=2))
 764 |     else:
 765 |         parser.print_help()
 766 | 
 767 | 
 768 | if __name__ == "__main__":
 769 |     main()
 770 | 
```

### File: services/polymarket_service.py (122 lines)
```
   1 | """
   2 | Polymarket Intelligence Service — Real-time prediction market data.
   3 | Free API, no auth required. Filters for Bitcoin/crypto/macro markets.
   4 | Feeds directly into Cross-Signal Divergence Engine.
   5 | """
   6 | import requests, logging
   7 | from datetime import datetime
   8 | 
   9 | logger = logging.getLogger('polymarket')
  10 | 
  11 | POLYMARKET_API = 'https://gamma-api.polymarket.com'
  12 | 
  13 | # Bitcoin/macro relevant tags on Polymarket
  14 | RELEVANT_TAGS = ['Crypto', 'Bitcoin', 'Fed', 'Economy', 'Geopolitics', 'US Politics']
  15 | 
  16 | def get_bitcoin_markets(limit=10):
  17 |     """Fetch active Polymarket markets relevant to Bitcoin/macro."""
  18 |     try:
  19 |         # Search for crypto/bitcoin markets
  20 |         resp = requests.get(
  21 |             f'{POLYMARKET_API}/markets',
  22 |             params={
  23 |                 'limit': 50,
  24 |                 'active': 'true',
  25 |                 'closed': 'false',
  26 |             },
  27 |             timeout=8
  28 |         )
  29 |         if not resp.ok:
  30 |             return []
  31 |         
  32 |         markets = resp.json()
  33 |         
  34 |         # Filter for relevant markets
  35 |         keywords = ['bitcoin', 'btc', 'crypto', 'fed', 'rate', 'inflation', 
  36 |                     'etf', 'halving', 'saylor', 'blackrock', 'recession', 'trump']
  37 |         
  38 |         filtered = []
  39 |         for m in markets:
  40 |             q = m.get('question', '').lower()
  41 |             if any(k in q for k in keywords):
  42 |                 filtered.append({
  43 |                     'question': m.get('question', ''),
  44 |                     'slug': m.get('slug', ''),
  45 |                     'volume': float(m.get('volume', 0) or 0),
  46 |                     'liquidity': float(m.get('liquidity', 0) or 0),
  47 |                     'end_date': m.get('endDate', ''),
  48 |                     'outcomes': _parse_outcomes(m),
  49 |                 })
  50 |         
  51 |         # Sort by volume descending
  52 |         filtered.sort(key=lambda x: x['volume'], reverse=True)
  53 |         return filtered[:limit]
  54 |     
  55 |     except Exception as e:
  56 |         logger.error(f'[Polymarket] Fetch failed: {e}')
  57 |         return []
  58 | 
  59 | def _parse_outcomes(market):
  60 |     """Extract Yes/No probabilities from market."""
  61 |     try:
  62 |         tokens = market.get('tokens', [])
  63 |         outcomes = {}
  64 |         for t in tokens:
  65 |             outcome = t.get('outcome', '')
  66 |             price = float(t.get('price', 0) or 0)
  67 |             outcomes[outcome] = round(price * 100, 1)  # Convert to %
  68 |         return outcomes
  69 |     except:
  70 |         return {}
  71 | 
  72 | def get_macro_sentiment_score():
  73 |     """
  74 |     Derive a macro sentiment score (0-100) from Polymarket crypto markets.
  75 |     High score = market expects bullish macro (rate cuts, BTC ETF approval, etc)
  76 |     Low score = market expects bearish macro
  77 |     """
  78 |     try:
  79 |         markets = get_bitcoin_markets(20)
  80 |         if not markets:
  81 |             return 50  # Neutral default
  82 |         
  83 |         bullish_signals = 0
  84 |         bearish_signals = 0
  85 |         
  86 |         for m in markets:
  87 |             outcomes = m.get('outcomes', {})
  88 |             q = m.get('question', '').lower()
  89 |             yes_prob = outcomes.get('Yes', 50)
  90 |             
  91 |             # Classify as bullish or bearish signal
  92 |             bullish_keywords = ['etf', 'approve', 'above', 'higher', 'rate cut', 
  93 |                                'halving', 'saylor', 'blackrock', 'reach', 'exceed']
  94 |             bearish_keywords = ['below', 'crash', 'recession', 'ban', 'hike',
  95 |                                'fail', 'reject', 'regulation']
  96 |             
  97 |             is_bullish_question = any(k in q for k in bullish_keywords)
  98 |             is_bearish_question = any(k in q for k in bearish_keywords)
  99 |             
 100 |             weight = max(1, m['volume'] / 10000)  # Weight by volume
 101 |             
 102 |             if is_bullish_question:
 103 |                 bullish_signals += (yes_prob / 100) * weight
 104 |             elif is_bearish_question:
 105 |                 bearish_signals += (yes_prob / 100) * weight
 106 |         
 107 |         total = bullish_signals + bearish_signals
 108 |         if total == 0:
 109 |             return 50
 110 |         
 111 |         score = (bullish_signals / total) * 100
 112 |         return round(score)
 113 |     
 114 |     except Exception as e:
 115 |         logger.error(f'[Polymarket] Sentiment score failed: {e}')
 116 |         return 50
 117 | 
 118 | def get_top_market_by_volume():
 119 |     """Get single most-traded Bitcoin/crypto market for dashboard widget."""
 120 |     markets = get_bitcoin_markets(5)
 121 |     return markets[0] if markets else None
 122 | 
```

---

## YOUR REVIEW TASK — PREMIUM INTELLIGENCE DASHBOARD COMPETITIVE AUDIT

You are auditing a Bitcoin intelligence dashboard that competes with Bloomberg Terminal ($2000/mo), Glassnode ($500/mo), CryptoQuant ($500/mo), and Santiment ($500/mo). The codebase already collects: BTC price, Fear & Greed, mempool fees, hashrate, lightning stats, KOL sentiment, 1300+ articles with sentiment, exchange flows, whale alerts, Polymarket odds, PCAF anomaly score, and stage brief narratives.

### Q1 — COMPETITIVE GAP ANALYSIS
What specific Bloomberg/Glassnode/CryptoQuant features costing $500-2000/month can we replicate or beat with our existing data? Name exact metrics, charts, and signals.

### Q2 — CROSS-SIGNAL ALPHA
What are the 5 most powerful cross-signal COMBINATIONS from our data that produce predictive alpha? Give specific, backtestable combinations with historical Bitcoin context. Example: hashrate up + exchange outflows + Fear&Greed < 20 = supply shock precursor.

### Q3 — VISUAL INNOVATION
What single visual display would make a hedge fund analyst say "I have never seen this before"? Think beyond standard price charts.

### Q4 — ML MODELS FOR RTX 4090
What open-source ML models (TimeMixer, PatchTST, Chronos, Mamba) can run on RTX 4090 for time-series forecasting without disrupting the render pipeline? Give specific model names, GitHub repos, GPU requirements.

### Q5 — THE $5000/MONTH FEATURE
What is the single feature worth $5000/month that uses ONLY our existing data? Must be technically feasible in one build session and genuinely unique.

### Q6 — DESIGN COMPETITION
What would win a Bloomberg vs Protocol Pulse design competition? Compete on both utility AND visual design. What makes our dashboard look like a $5000/month product vs a free tool?

### RESPONSE FORMAT
For each question: DETAILED ANALYSIS → SPECIFIC RECOMMENDATION → IMPLEMENTATION PRIORITY (P0/P1/P2)

### FINAL SUMMARY
- Top 3 consensus recommendations across all questions
- The single highest-ROI feature to build first
- What to REMOVE as noise

