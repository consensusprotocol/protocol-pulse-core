# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: join-page
# Branch: main
# Generated: 2026-03-26 00:50 UTC
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

### File: templates/join.html (1321 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Join — Sovereign Bitcoin Intelligence | Protocol Pulse{% endblock %}
   4 | {% block meta_description %}Sovereign Bitcoin intelligence for transactors. Free Agent, Commander, and Sovereign tiers. Real-time chain analysis, Oracle AI, and signal terminal access.{% endblock %}
   5 | 
   6 | {% block head %}
   7 | <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
   8 | <style>
   9 | /* ═══════════════════════════════════════════════════════════════════════
  10 |    /join — PROTOCOL PULSE INTELLIGENCE
  11 |    Bloomberg Terminal × Cypherpunk Broadcast — VISUAL_DESIGN_SYSTEM v2
  12 |    ═══════════════════════════════════════════════════════════════════════ */
  13 | 
  14 | :root {
  15 |     --j-bg:      #06070b;
  16 |     --j-panel:   #0d1118;
  17 |     --j-panel2:  #121824;
  18 |     --j-text:    #eef2ff;
  19 |     --j-muted:   #95a0ba;
  20 |     --j-red:     #ff3b5f;
  21 |     --j-gold:    #f8c15c;
  22 |     --j-cyan:    #5de4ff;
  23 |     --j-lime:    #89ffb8;
  24 |     --j-coral:   #ff8ba0;
  25 |     --j-mono:    'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
  26 |     --j-sans:    'Inter', ui-sans-serif, system-ui, sans-serif;
  27 | }
  28 | 
  29 | *, *::before, *::after { box-sizing: border-box; }
  30 | body { background: var(--j-bg) !important; overflow-x: hidden; }
  31 | 
  32 | /* ── ANIMATED BACKGROUND ── */
  33 | .join-bg {
  34 |     position: fixed; inset: 0; z-index: 0; pointer-events: none;
  35 |     background: var(--j-bg);
  36 | }
  37 | .join-bg::before {
  38 |     content: '';
  39 |     position: absolute; inset: 0;
  40 |     background:
  41 |         radial-gradient(ellipse 600px 500px at 15% 20%, rgba(255,59,95,0.14), transparent),
  42 |         radial-gradient(ellipse 500px 400px at 85% 15%, rgba(93,228,255,0.10), transparent),
  43 |         radial-gradient(ellipse 400px 300px at 50% 80%, rgba(248,193,92,0.06), transparent);
  44 |     animation: bgShift 7s ease-in-out infinite alternate;
  45 | }
  46 | @keyframes bgShift {
  47 |     0%   { transform: translate(0, 0); }
  48 |     100% { transform: translate(15px, -10px); }
  49 | }
  50 | .join-bg::after {
  51 |     content: '';
  52 |     position: absolute; inset: 0;
  53 |     background: repeating-linear-gradient(
  54 |         0deg, transparent, transparent 3px, rgba(255,255,255,0.015) 3px, rgba(255,255,255,0.015) 4px
  55 |     );
  56 |     pointer-events: none;
  57 | }
  58 | 
  59 | /* Perspective grid */
  60 | .join-grid {
  61 |     position: fixed; inset: 0; z-index: 0; pointer-events: none;
  62 |     opacity: 0.03;
  63 |     background:
  64 |         repeating-linear-gradient(90deg, rgba(255,255,255,0.3) 0px, transparent 1px, transparent 80px),
  65 |         repeating-linear-gradient(0deg, rgba(255,255,255,0.3) 0px, transparent 1px, transparent 80px);
  66 |     transform: perspective(1200px) rotateX(65deg) translateY(200px) scale(2);
  67 | }
  68 | 
  69 | /* Vignette */
  70 | .join-vignette {
  71 |     position: fixed; inset: 0; z-index: 0; pointer-events: none;
  72 |     background: radial-gradient(ellipse at center, transparent 40%, rgba(6,7,11,0.55) 100%);
  73 | }
  74 | 
  75 | /* Red particle canvas */
  76 | #particleCanvas {
  77 |     position: fixed; inset: 0; z-index: 0; pointer-events: none;
  78 | }
  79 | 
  80 | /* ── PAGE CONTAINER ── */
  81 | .join-page {
  82 |     position: relative; z-index: 1;
  83 |     max-width: 1180px;
  84 |     margin: 0 auto;
  85 |     padding: 0 20px 100px;
  86 |     color: var(--j-text);
  87 |     font-family: var(--j-sans);
  88 | }
  89 | 
  90 | /* ── LIVE TICKER BAR ── */
  91 | .join-ticker {
  92 |     display: flex;
  93 |     align-items: center;
  94 |     justify-content: center;
  95 |     gap: 24px;
  96 |     padding: 10px 24px;
  97 |     background: linear-gradient(90deg, rgba(248,193,92,0.90), rgba(255,219,132,0.94));
  98 |     margin: 0 -20px 0;
  99 |     font-family: var(--j-mono);
 100 |     font-size: 11px;
 101 |     font-weight: 800;
 102 |     color: #141515;
 103 |     letter-spacing: 0.08em;
 104 |     position: sticky;
 105 |     top: 0;
 106 |     z-index: 100;
 107 | }
 108 | .join-ticker-sep {
 109 |     width: 4px; height: 4px;
 110 |     background: rgba(20,21,21,0.3);
 111 |     border-radius: 50%;
 112 |     flex-shrink: 0;
 113 | }
 114 | .join-ticker .ticker-up { color: #0a5c2c; }
 115 | .join-ticker .ticker-down { color: #8b1a1a; }
 116 | .join-ticker-pulse {
 117 |     width: 6px; height: 6px;
 118 |     background: #dc2626;
 119 |     border-radius: 50%;
 120 |     animation: tickerPulse 2s ease-in-out infinite;
 121 |     flex-shrink: 0;
 122 | }
 123 | @keyframes tickerPulse {
 124 |     0%, 100% { opacity: 1; box-shadow: 0 0 4px rgba(220,38,38,0.6); }
 125 |     50% { opacity: 0.4; box-shadow: none; }
 126 | }
 127 | 
 128 | /* ── HERO ── */
 129 | .join-hero {
 130 |     text-align: center;
 131 |     padding: 80px 0 64px;
 132 |     position: relative;
 133 | }
 134 | .join-hero-kicker {
 135 |     font-family: var(--j-mono);
 136 |     font-size: 11px;
 137 |     font-weight: 800;
 138 |     letter-spacing: 0.24em;
 139 |     text-transform: uppercase;
 140 |     color: var(--j-gold);
 141 |     margin-bottom: 20px;
 142 |     display: flex;
 143 |     align-items: center;
 144 |     justify-content: center;
 145 |     gap: 12px;
 146 | }
 147 | .join-hero-kicker::before,
 148 | .join-hero-kicker::after {
 149 |     content: '';
 150 |     width: 40px; height: 1px;
 151 |     background: linear-gradient(90deg, transparent, var(--j-gold));
 152 | }
 153 | .join-hero-kicker::after {
 154 |     background: linear-gradient(90deg, var(--j-gold), transparent);
 155 | }
 156 | .join-hero h1 {
 157 |     font-family: var(--j-sans);
 158 |     font-size: 56px;
 159 |     font-weight: 900;
 160 |     letter-spacing: -0.04em;
 161 |     line-height: 0.94;
 162 |     margin: 0 0 24px;
 163 |     text-shadow: 0 4px 48px rgba(0,0,0,0.5);
 164 | }
 165 | .join-hero h1 .hero-red { color: var(--j-red); }
 166 | .join-hero .join-sub {
 167 |     font-size: 18px;
 168 |     color: #d7def4;
 169 |     max-width: 560px;
 170 |     margin: 0 auto 32px;
 171 |     line-height: 1.55;
 172 |     font-weight: 400;
 173 | }
 174 | 
 175 | /* Animated scan line */
 176 | .join-scanline-wrap {
 177 |     position: relative;
 178 |     width: 280px;
 179 |     height: 3px;
 180 |     margin: 0 auto;
 181 |     background: rgba(255,59,95,0.08);
 182 |     border-radius: 2px;
 183 |     overflow: hidden;
 184 | }
 185 | .join-scanline-track {
 186 |     position: absolute;
 187 |     inset: 0;
 188 |     background: linear-gradient(90deg, transparent 0%, var(--j-red) 50%, transparent 100%);
 189 |     opacity: 0.15;
 190 | }
 191 | .join-scanline-beam {
 192 |     position: absolute;
 193 |     top: 0; bottom: 0;
 194 |     width: 60px;
 195 |     background: linear-gradient(90deg, transparent, var(--j-red), transparent);
 196 |     border-radius: 2px;
 197 |     animation: scanBeam 3s ease-in-out infinite;
 198 |     box-shadow: 0 0 16px rgba(255,59,95,0.5), 0 0 40px rgba(255,59,95,0.2);
 199 | }
 200 | @keyframes scanBeam {
 201 |     0%   { left: -60px; opacity: 0; }
 202 |     8%   { opacity: 1; }
 203 |     92%  { opacity: 1; }
 204 |     100% { left: 280px; opacity: 0; }
 205 | }
 206 | 
 207 | /* ── SECTION DIVIDER ── */
 208 | .join-section-label {
 209 |     text-align: center;
 210 |     margin: 0 0 48px;
 211 |     position: relative;
 212 | }
 213 | .join-section-label::before {
 214 |     content: '';
 215 |     position: absolute;
 216 |     top: 50%;
 217 |     left: 0; right: 0;
 218 |     height: 1px;
 219 |     background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
 220 | }
 221 | .join-section-label span {
 222 |     position: relative;
 223 |     font-family: var(--j-mono);
 224 |     font-size: 10px;
 225 |     font-weight: 800;
 226 |     letter-spacing: 0.20em;
 227 |     text-transform: uppercase;
 228 |     color: var(--j-gold);
 229 |     background: var(--j-bg);
 230 |     padding: 0 20px;
 231 | }
 232 | 
 233 | /* ── PRICING TIERS ── */
 234 | .join-tiers {
 235 |     display: grid;
 236 |     grid-template-columns: repeat(3, 1fr);
 237 |     gap: 20px;
 238 |     margin-bottom: 72px;
 239 |     align-items: start;
 240 | }
 241 | .join-card {
 242 |     position: relative;
 243 |     padding: 32px 28px 28px;
 244 |     background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015));
 245 |     border: 1px solid rgba(255,255,255,0.07);
 246 |     border-radius: 16px;
 247 |     backdrop-filter: blur(20px);
 248 |     -webkit-backdrop-filter: blur(20px);
 249 |     transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
 250 |     overflow: hidden;
 251 | }
 252 | .join-card::before {
 253 |     content: '';
 254 |     position: absolute;
 255 |     top: 0; left: 0; right: 0;
 256 |     height: 2px;
 257 |     border-radius: 16px 16px 0 0;
 258 | }
 259 | .join-card:hover {
 260 |     transform: translateY(-4px);
 261 |     box-shadow: 0 16px 48px rgba(0,0,0,0.3);
 262 | }
 263 | 
 264 | /* FREE tier */
 265 | .join-card--free::before { background: #8895a7; }
 266 | .join-card--free:hover { border-color: rgba(136,149,167,0.20); }
 267 | 
 268 | /* COMMANDER tier (featured) */
 269 | .join-card--commander {
 270 |     border-color: rgba(255,59,95,0.20);
 271 |     background: linear-gradient(180deg, rgba(255,59,95,0.06), rgba(255,255,255,0.015));
 272 |     transform: scale(1.02);
 273 |     box-shadow:
 274 |         0 0 60px rgba(255,59,95,0.08),
 275 |         0 16px 48px rgba(0,0,0,0.35);
 276 | }
 277 | .join-card--commander::before {
 278 |     background: linear-gradient(90deg, var(--j-red), #ff7a4f);
 279 |     height: 3px;
 280 | }
 281 | .join-card--commander:hover {
 282 |     transform: scale(1.02) translateY(-4px);
 283 |     border-color: rgba(255,59,95,0.35);
 284 |     box-shadow:
 285 |         0 0 80px rgba(255,59,95,0.12),
 286 |         0 20px 56px rgba(0,0,0,0.4);
 287 | }
 288 | 
 289 | /* SOVEREIGN tier */
 290 | .join-card--sovereign::before {
 291 |     background: linear-gradient(90deg, var(--j-gold), #ffd166);
 292 | }
 293 | .join-card--sovereign:hover { border-color: rgba(248,193,92,0.20); }
 294 | 
 295 | .join-card-badge {
 296 |     position: absolute;
 297 |     top: 14px; right: 16px;
 298 |     font-family: var(--j-mono);
 299 |     font-size: 9px;
 300 |     font-weight: 800;
 301 |     letter-spacing: 0.14em;
 302 |     text-transform: uppercase;
 303 |     color: var(--j-red);
 304 |     background: rgba(255,59,95,0.10);
 305 |     border: 1px solid rgba(255,59,95,0.20);
 306 |     padding: 4px 10px;
 307 |     border-radius: 4px;
 308 |     animation: badgePulse 3s ease-in-out infinite;
 309 | }
 310 | @keyframes badgePulse {
 311 |     0%, 100% { opacity: 1; }
 312 |     50% { opacity: 0.7; }
 313 | }
 314 | 
 315 | .join-card-kicker {
 316 |     font-family: var(--j-mono);
 317 |     font-size: 10px;
 318 |     font-weight: 800;
 319 |     letter-spacing: 0.20em;
 320 |     text-transform: uppercase;
 321 |     margin-bottom: 14px;
 322 | }
 323 | .join-card--free .join-card-kicker { color: #8895a7; }
 324 | .join-card--commander .join-card-kicker { color: var(--j-red); }
 325 | .join-card--sovereign .join-card-kicker { color: var(--j-gold); }
 326 | 
 327 | .join-card-price {
 328 |     font-family: var(--j-sans);
 329 |     font-size: 48px;
 330 |     font-weight: 900;
 331 |     letter-spacing: -0.04em;
 332 |     color: var(--j-text);
 333 |     margin-bottom: 8px;
 334 |     line-height: 1;
 335 | }
 336 | .join-card-price .price-sub {
 337 |     font-size: 16px;
 338 |     font-weight: 500;
 339 |     color: var(--j-muted);
 340 |     letter-spacing: 0;
 341 | }
 342 | 
 343 | .join-card-desc {
 344 |     font-size: 14px;
 345 |     color: #b8c0d8;
 346 |     line-height: 1.55;
 347 |     margin-bottom: 20px;
 348 | }
 349 | 
 350 | .join-features {
 351 |     list-style: none;
 352 |     padding: 0;
 353 |     margin: 0 0 24px;
 354 | }
 355 | .join-features li {
 356 |     position: relative;
 357 |     padding: 7px 0 7px 22px;
 358 |     font-size: 13px;
 359 |     color: #c8cfe3;
 360 |     line-height: 1.4;
 361 |     border-bottom: 1px solid rgba(255,255,255,0.025);
 362 | }
 363 | .join-features li:last-child { border-bottom: none; }
 364 | .join-features li::before {
 365 |     content: '\25B8';
 366 |     position: absolute;
 367 |     left: 0; top: 7px;
 368 |     font-size: 10px;
 369 | }
 370 | .join-card--free .join-features li::before { color: #8895a7; }
 371 | .join-card--commander .join-features li::before { color: var(--j-red); }
 372 | .join-card--sovereign .join-features li::before { color: var(--j-gold); }
 373 | 
 374 | /* Buttons */
 375 | .join-btn {
 376 |     display: block;
 377 |     width: 100%;
 378 |     padding: 14px 24px;
 379 |     font-family: var(--j-mono);
 380 |     font-size: 12px;
 381 |     font-weight: 800;
 382 |     letter-spacing: 0.10em;
 383 |     text-transform: uppercase;
 384 |     text-align: center;
 385 |     text-decoration: none;
 386 |     border-radius: 8px;
 387 |     cursor: pointer;
 388 |     transition: all 0.15s;
 389 |     border: none;
 390 | }
 391 | .join-btn--ghost {
 392 |     background: rgba(136,149,167,0.08);
 393 |     border: 1px solid rgba(136,149,167,0.25);
 394 |     color: #8895a7;
 395 | }
 396 | .join-btn--ghost:hover {
 397 |     background: rgba(136,149,167,0.14);
 398 |     border-color: rgba(136,149,167,0.40);
 399 |     box-shadow: 0 4px 20px rgba(136,149,167,0.10);
 400 | }
 401 | .join-btn--red {
 402 |     background: var(--j-red);
 403 |     color: #fff;
 404 |     box-shadow: 0 4px 24px rgba(255,59,95,0.3);
 405 | }
 406 | .join-btn--red:hover {
 407 |     background: #e02e4f;
 408 |     box-shadow: 0 6px 32px rgba(255,59,95,0.45);
 409 |     transform: translateY(-2px);
 410 | }
 411 | .join-btn--gold {
 412 |     background: rgba(248,193,92,0.10);
 413 |     border: 1px solid rgba(248,193,92,0.25);
 414 |     color: var(--j-gold);
 415 | }
 416 | .join-btn--gold:hover {
 417 |     background: rgba(248,193,92,0.18);
 418 |     border-color: rgba(248,193,92,0.40);
 419 |     box-shadow: 0 4px 20px rgba(248,193,92,0.10);
 420 | }
 421 | 
 422 | /* ── FEATURE COMPARISON MATRIX ── */
 423 | .join-matrix-section {
 424 |     margin-bottom: 72px;
 425 | }
 426 | .join-matrix-kicker {
 427 |     text-align: center;
 428 |     font-family: var(--j-mono);
 429 |     font-size: 10px;
 430 |     font-weight: 800;
 431 |     letter-spacing: 0.20em;
 432 |     text-transform: uppercase;
 433 |     color: var(--j-gold);
 434 |     margin-bottom: 10px;
 435 | }
 436 | .join-matrix-title {
 437 |     text-align: center;
 438 |     font-family: var(--j-sans);
 439 |     font-size: 28px;
 440 |     font-weight: 900;
 441 |     letter-spacing: -0.03em;
 442 |     color: var(--j-text);
 443 |     margin-bottom: 32px;
 444 | }
 445 | 
 446 | .join-matrix-wrap {
 447 |     background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
 448 |     border: 1px solid rgba(255,255,255,0.06);
 449 |     border-radius: 14px;
 450 |     overflow: hidden;
 451 |     backdrop-filter: blur(18px);
 452 |     -webkit-backdrop-filter: blur(18px);
 453 | }
 454 | .join-matrix {
 455 |     width: 100%;
 456 |     border-collapse: collapse;
 457 |     font-size: 13px;
 458 | }
 459 | .join-matrix thead th {
 460 |     font-family: var(--j-mono);
 461 |     font-size: 10px;
 462 |     font-weight: 800;
 463 |     letter-spacing: 0.14em;
 464 |     text-transform: uppercase;
 465 |     padding: 16px 16px;
 466 |     text-align: center;
 467 |     border-bottom: 1px solid rgba(255,255,255,0.06);
 468 |     background: rgba(255,255,255,0.02);
 469 | }
 470 | .join-matrix thead th:first-child {
 471 |     text-align: left;
 472 |     color: var(--j-muted);
 473 | }
 474 | .join-matrix thead th:nth-child(2) { color: #8895a7; }
 475 | .join-matrix thead th:nth-child(3) { color: var(--j-red); }
 476 | .join-matrix thead th:nth-child(4) { color: var(--j-gold); }
 477 | .join-matrix tbody td {
 478 |     padding: 12px 16px;
 479 |     border-bottom: 1px solid rgba(255,255,255,0.025);
 480 |     text-align: center;
 481 |     color: var(--j-muted);
 482 |     vertical-align: middle;
 483 | }
 484 | .join-matrix tbody td:first-child {
 485 |     text-align: left;
 486 |     color: var(--j-text);
 487 |     font-weight: 500;
 488 | }
 489 | .join-matrix tbody tr:last-child td { border-bottom: none; }
 490 | .join-matrix tbody tr:hover { background: rgba(255,255,255,0.015); }
 491 | .join-matrix .mx-yes {
 492 |     color: var(--j-lime);
 493 |     font-family: var(--j-mono);
 494 |     font-weight: 700;
 495 | }
 496 | .join-matrix .mx-no {
 497 |     color: rgba(149,160,186,0.25);
 498 |     font-size: 11px;
 499 | }
 500 | .join-matrix .mx-val {
 501 |     color: var(--j-text);
 502 |     font-family: var(--j-mono);
 503 |     font-weight: 600;
 504 |     font-size: 12px;
 505 | }
 506 | .join-matrix thead th:nth-child(3),
 507 | .join-matrix tbody td:nth-child(3) {
 508 |     background: rgba(255,59,95,0.03);
 509 | }
 510 | 
 511 | /* ── ACCESS CODE TERMINAL ── */
 512 | .join-promo {
 513 |     max-width: 580px;
 514 |     margin: 0 auto 72px;
 515 |     padding: 0;
 516 |     background: rgba(6,7,11,0.92);
 517 |     border: 1px solid rgba(255,59,95,0.12);
 518 |     border-radius: 12px;
 519 |     position: relative;
 520 |     overflow: hidden;
 521 | }
 522 | 
 523 | /* Terminal title bar */
 524 | .join-promo-titlebar {
 525 |     display: flex;
 526 |     align-items: center;
 527 |     gap: 8px;
 528 |     padding: 10px 16px;
 529 |     background: rgba(255,255,255,0.03);
 530 |     border-bottom: 1px solid rgba(255,255,255,0.05);
 531 | }
 532 | .join-promo-dots {
 533 |     display: flex;
 534 |     gap: 6px;
 535 | }
 536 | .join-promo-dots span {
 537 |     width: 8px; height: 8px;
 538 |     border-radius: 50%;
 539 |     background: rgba(255,255,255,0.1);
 540 | }
 541 | .join-promo-dots span:first-child { background: rgba(255,59,95,0.6); }
 542 | .join-promo-titlebar-text {
 543 |     font-family: var(--j-mono);
 544 |     font-size: 10px;
 545 |     font-weight: 600;
 546 |     color: var(--j-muted);
 547 |     letter-spacing: 0.06em;
 548 |     margin-left: 8px;
 549 | }
 550 | 
 551 | /* Terminal body */
 552 | .join-promo-body {
 553 |     padding: 24px 24px 20px;
 554 |     position: relative;
 555 | }
 556 | .join-promo-body::before {
 557 |     content: '';
 558 |     position: absolute; inset: 0;
 559 |     background: repeating-linear-gradient(
 560 |         0deg, transparent, transparent 2px, rgba(255,59,95,0.015) 2px, rgba(255,59,95,0.015) 4px
 561 |     );
 562 |     pointer-events: none;
 563 |     z-index: 0;
 564 | }
 565 | .join-promo-body > * { position: relative; z-index: 1; }
 566 | 
 567 | .join-promo-header {
 568 |     display: flex;
 569 |     align-items: center;
 570 |     gap: 8px;
 571 |     margin-bottom: 6px;
 572 | }
 573 | .join-promo-dot {
 574 |     width: 6px; height: 6px;
 575 |     background: var(--j-red);
 576 |     border-radius: 50%;
 577 |     animation: promoBlink 2s ease-in-out infinite;
 578 |     box-shadow: 0 0 6px rgba(255,59,95,0.4);
 579 | }
 580 | @keyframes promoBlink {
 581 |     0%, 100% { opacity: 1; }
 582 |     50%      { opacity: 0.3; }
 583 | }
 584 | .join-promo-label {
 585 |     font-family: var(--j-mono);
 586 |     font-size: 10px;
 587 |     font-weight: 800;
 588 |     letter-spacing: 0.18em;
 589 |     text-transform: uppercase;
 590 |     color: var(--j-red);
 591 | }
 592 | .join-promo-sub {
 593 |     font-size: 13px;
 594 |     color: var(--j-muted);
 595 |     margin-bottom: 16px;
 596 |     line-height: 1.5;
 597 | }
 598 | .join-promo-row {
 599 |     display: flex;
 600 |     gap: 8px;
 601 | }
 602 | .join-promo-input {
 603 |     flex: 1;
 604 |     padding: 12px 14px;
 605 |     background: rgba(6,7,11,0.9);
 606 |     border: 1px solid rgba(255,59,95,0.20);
 607 |     border-radius: 6px;
 608 |     color: var(--j-text);
 609 |     font-family: var(--j-mono);
 610 |     font-size: 14px;
 611 |     font-weight: 600;
 612 |     letter-spacing: 0.06em;
 613 |     outline: none;
 614 |     transition: border-color 0.15s, box-shadow 0.15s;
 615 |     caret-color: var(--j-red);
 616 | }
 617 | .join-promo-input::placeholder {
 618 |     color: rgba(149,160,186,0.3);
 619 |     font-weight: 400;
 620 | }
 621 | .join-promo-input:focus {
 622 |     border-color: var(--j-red);
 623 |     box-shadow: 0 0 0 3px rgba(255,59,95,0.08), 0 0 20px rgba(255,59,95,0.06);
 624 | }
 625 | .join-promo-submit {
 626 |     padding: 12px 20px;
 627 |     background: var(--j-red);
 628 |     color: #fff;
 629 |     border: none;
 630 |     border-radius: 6px;
 631 |     font-family: var(--j-mono);
 632 |     font-size: 11px;
 633 |     font-weight: 800;
 634 |     letter-spacing: 0.10em;
 635 |     text-transform: uppercase;
 636 |     cursor: pointer;
 637 |     white-space: nowrap;
 638 |     transition: background 0.15s, box-shadow 0.15s;
 639 | }
 640 | .join-promo-submit:hover {
 641 |     background: #e02e4f;
 642 |     box-shadow: 0 4px 16px rgba(255,59,95,0.3);
 643 | }
 644 | .join-promo-submit:disabled { background: #333; cursor: wait; }
 645 | .join-promo-msg {
 646 |     margin-top: 10px;
 647 |     font-family: var(--j-mono);
 648 |     font-size: 12px;
 649 |     font-weight: 600;
 650 |     display: none;
 651 | }
 652 | .join-promo-msg.error { color: var(--j-red); display: block; }
 653 | .join-promo-msg.success { color: var(--j-lime); display: block; }
 654 | .join-promo-hint {
 655 |     margin-top: 12px;
 656 |     font-family: var(--j-mono);
 657 |     font-size: 11px;
 658 |     color: rgba(149,160,186,0.3);
 659 |     letter-spacing: 0.02em;
 660 | }
 661 | .join-promo-cursor {
 662 |     display: inline-block;
 663 |     width: 2px;
 664 |     height: 14px;
 665 |     background: var(--j-red);
 666 |     margin-left: 2px;
 667 |     vertical-align: middle;
 668 |     animation: cursorBlink 1s step-end infinite;
 669 | }
 670 | @keyframes cursorBlink {
 671 |     0%, 100% { opacity: 1; }
 672 |     50% { opacity: 0; }
 673 | }
 674 | 
 675 | /* ── CLOSING CTA ── */
 676 | .join-closing {
 677 |     text-align: center;
 678 |     padding: 56px 20px;
 679 |     margin-bottom: 40px;
 680 |     position: relative;
 681 | }
 682 | .join-closing::before {
 683 |     content: '';
 684 |     position: absolute;
 685 |     top: 0; left: 50%;
 686 |     transform: translateX(-50%);
 687 |     width: 120px; height: 1px;
 688 |     background: linear-gradient(90deg, transparent, rgba(255,59,95,0.3), transparent);
 689 | }
 690 | .join-closing-kicker {
 691 |     font-family: var(--j-mono);
 692 |     font-size: 10px;
 693 |     font-weight: 800;
 694 |     letter-spacing: 0.20em;
 695 |     text-transform: uppercase;
 696 |     color: var(--j-gold);
 697 |     margin-bottom: 14px;
 698 | }
 699 | .join-closing h2 {
 700 |     font-family: var(--j-sans);
 701 |     font-size: 36px;
 702 |     font-weight: 900;
 703 |     letter-spacing: -0.03em;
 704 |     color: var(--j-text);
 705 |     margin: 0 0 14px;
 706 |     text-shadow: 0 4px 28px rgba(0,0,0,0.4);
 707 | }
 708 | .join-closing h2 .hero-red { color: var(--j-red); }
 709 | .join-closing p {
 710 |     font-size: 16px;
 711 |     color: #d7def4;
 712 |     max-width: 520px;
 713 |     margin: 0 auto 28px;
 714 |     line-height: 1.55;
 715 | }
 716 | .join-closing-btn {
 717 |     display: inline-block;
 718 |     padding: 16px 40px;
 719 |     background: var(--j-red);
 720 |     color: #fff;
 721 |     font-family: var(--j-mono);
 722 |     font-size: 13px;
 723 |     font-weight: 800;
 724 |     letter-spacing: 0.10em;
 725 |     text-transform: uppercase;
 726 |     text-decoration: none;
 727 |     border: none;
 728 |     border-radius: 8px;
 729 |     cursor: pointer;
 730 |     transition: all 0.15s;
 731 |     box-shadow: 0 4px 24px rgba(255,59,95,0.25);
 732 | }
 733 | .join-closing-btn:hover {
 734 |     background: #e02e4f;
 735 |     box-shadow: 0 6px 32px rgba(255,59,95,0.40);
 736 |     transform: translateY(-2px);
 737 | }
 738 | 
 739 | /* Equalizer bars */
 740 | .join-eq {
 741 |     display: flex;
 742 |     justify-content: center;
 743 |     gap: 6px;
 744 |     margin-bottom: 28px;
 745 | }
 746 | .join-eq-bar {
 747 |     width: 4px;
 748 |     border-radius: 2px;
 749 |     background: linear-gradient(180deg, var(--j-red), #ff7a4f);
 750 |     animation: eqBounce 1.4s ease-in-out infinite;
 751 | }
 752 | .join-eq-bar:nth-child(1) { height: 18px; animation-delay: 0s; }
 753 | .join-eq-bar:nth-child(2) { height: 28px; animation-delay: 0.15s; }
 754 | .join-eq-bar:nth-child(3) { height: 40px; animation-delay: 0.3s; }
 755 | .join-eq-bar:nth-child(4) { height: 28px; animation-delay: 0.45s; }
 756 | .join-eq-bar:nth-child(5) { height: 18px; animation-delay: 0.6s; }
 757 | @keyframes eqBounce {
 758 |     0%, 100% { transform: scaleY(0.4); opacity: 0.6; }
 759 |     50%      { transform: scaleY(1); opacity: 1; }
 760 | }
 761 | 
 762 | /* ── SOCIAL PROOF ── */
 763 | .join-proof {
 764 |     text-align: center;
 765 |     padding: 24px 0 0;
 766 |     max-width: 760px;
 767 |     margin: 0 auto 40px;
 768 | }
 769 | .join-proof-kicker {
 770 |     font-family: var(--j-mono);
 771 |     font-size: 10px;
 772 |     font-weight: 800;
 773 |     letter-spacing: 0.18em;
 774 |     text-transform: uppercase;
 775 |     color: var(--j-gold);
 776 |     margin-bottom: 16px;
 777 | }
 778 | .join-proof-grid {
 779 |     display: flex;
 780 |     justify-content: center;
 781 |     flex-wrap: wrap;
 782 |     gap: 20px 32px;
 783 | }
 784 | .join-proof-stat {
 785 |     font-family: var(--j-mono);
 786 |     font-size: 12px;
 787 |     color: var(--j-muted);
 788 |     padding: 8px 16px;
 789 |     background: rgba(255,255,255,0.02);
 790 |     border: 1px solid rgba(255,255,255,0.04);
 791 |     border-radius: 6px;
 792 | }
 793 | .join-proof-stat span {
 794 |     color: var(--j-cyan);
 795 |     font-weight: 800;
 796 | }
 797 | 
 798 | /* ── BOTTOM LINKS ── */
 799 | .join-bottom {
 800 |     text-align: center;
 801 |     margin-top: 24px;
 802 | }
 803 | .join-bottom a {
 804 |     font-size: 13px;
 805 |     color: var(--j-muted);
 806 |     text-decoration: none;
 807 |     transition: color 0.15s;
 808 | }
 809 | .join-bottom a:hover { color: var(--j-cyan); }
 810 | .join-bottom a span { color: var(--j-cyan); }
 811 | 
 812 | /* ── RESPONSIVE ── */
 813 | @media (max-width: 960px) {
 814 |     .join-tiers {
 815 |         grid-template-columns: 1fr;
 816 |         max-width: 500px;
 817 |         margin-left: auto;
 818 |         margin-right: auto;
 819 |     }
 820 |     .join-card--commander {
 821 |         order: -1;
 822 |         transform: none;
 823 |     }
 824 |     .join-card--commander:hover { transform: translateY(-4px); }
 825 |     .join-matrix-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
 826 |     .join-matrix { min-width: 560px; }
 827 | }
 828 | @media (max-width: 600px) {
 829 |     .join-hero { padding: 48px 0 40px; }
 830 |     .join-hero h1 { font-size: 34px; }
 831 |     .join-hero .join-sub { font-size: 15px; }
 832 |     .join-ticker { flex-wrap: wrap; gap: 10px 16px; font-size: 10px; padding: 8px 12px; }
 833 |     .join-card { padding: 24px 20px 22px; }
 834 |     .join-card-price { font-size: 38px; }
 835 |     .join-promo { margin-left: -4px; margin-right: -4px; }
 836 |     .join-promo-body { padding: 20px 16px 16px; }
 837 |     .join-promo-row { flex-direction: column; }
 838 |     .join-promo-submit { width: 100%; padding: 14px; }
 839 |     .join-proof-grid { flex-direction: column; gap: 8px; align-items: center; }
 840 |     .join-closing h2 { font-size: 26px; }
 841 |     .join-scanline-wrap { width: 200px; }
 842 |     @keyframes scanBeam {
 843 |         0%   { left: -60px; opacity: 0; }
 844 |         8%   { opacity: 1; }
 845 |         92%  { opacity: 1; }
 846 |         100% { left: 200px; opacity: 0; }
 847 |     }
 848 |     .join-section-label span { font-size: 9px; }
 849 |     .signup-modal { padding: 28px 20px; margin: 16px; }
 850 | }
 851 | 
 852 | /* Reduced motion support */
 853 | @media (prefers-reduced-motion: reduce) {
 854 |     .join-bg::before,
 855 |     .join-scanline-beam,
 856 |     .join-promo-dot,
 857 |     .join-promo-cursor,
 858 |     .join-eq-bar,
 859 |     .join-card-badge,
 860 |     .join-ticker-pulse { animation: none !important; }
 861 |     .join-card:hover { transform: none; }
 862 |     .join-card--commander { transform: none; }
 863 |     .join-card--commander:hover { transform: none; }
 864 | }
 865 | </style>
 866 | {% endblock %}
 867 | 
 868 | {% block content %}
 869 | <!-- Animated background layers -->
 870 | <div class="join-bg"></div>
 871 | <div class="join-grid"></div>
 872 | <div class="join-vignette"></div>
 873 | <canvas id="particleCanvas"></canvas>
 874 | 
 875 | <div class="join-page">
 876 | 
 877 |     <!-- ═══ GOLD TICKER BAR ═══ -->
 878 |     <div class="join-ticker" role="region" aria-label="Live market intelligence feed">
 879 |         <span class="join-ticker-pulse"></span>
 880 |         <span id="jTicker-btc">BTC ---,---</span>
 881 |         <span class="join-ticker-sep"></span>
 882 |         <span id="jTicker-fng">F&amp;G --</span>
 883 |         <span class="join-ticker-sep"></span>
 884 |         <span id="jTicker-block">BLOCK ---,---</span>
 885 |         <span class="join-ticker-sep"></span>
 886 |         <span>PROTOCOLPULSE.IO</span>
 887 |     </div>
 888 | 
 889 |     <!-- ═══ HERO ═══ -->
 890 |     <div class="join-hero">
 891 |         <div class="join-hero-kicker">CONSENSUS INTELLIGENCE</div>
 892 |         <h1>PROTOCOL PULSE<br><span class="hero-red">INTELLIGENCE</span></h1>
 893 |         <p class="join-sub">
 894 |             Sovereign Bitcoin intelligence. Real-time chain analysis, AI-powered signal detection, zero middlemen. Built on bare metal for transactors who verify, not trust.
 895 |         </p>
 896 |         <div class="join-scanline-wrap" aria-hidden="true">
 897 |             <div class="join-scanline-track"></div>
 898 |             <div class="join-scanline-beam"></div>
 899 |         </div>
 900 |     </div>
 901 | 
 902 |     <!-- ═══ PRICING TIERS ═══ -->
 903 |     <div class="join-section-label"><span>SELECT YOUR TIER</span></div>
 904 | 
 905 |     <div class="join-tiers">
 906 | 
 907 |         <!-- FREE AGENT -->
 908 |         <div class="join-card join-card--free">
 909 |             <div class="join-card-kicker">FREE AGENT</div>
 910 |             <div class="join-card-price">$0<span class="price-sub">/forever</span></div>
 911 |             <div class="join-card-desc">Public intelligence layer. Intel briefs, market overview, and open-source tools. No signup required.</div>
 912 |             <ul class="join-features">
 913 |                 <li>Daily intelligence articles</li>
 914 |                 <li>BTC price, Fear &amp; Greed, market overview</li>
 915 |                 <li>Whale Watcher &mdash; large transaction monitor</li>
 916 |                 <li>Merchant Map &mdash; 10,000+ BTC-accepting businesses</li>
 917 |                 <li>Public charts &amp; mempool explorer</li>
 918 |                 <li>RSS, Atom, and Nostr signal feeds</li>
 919 |                 <li>Solo Slayers &mdash; mining lottery tracker</li>
 920 |             </ul>
 921 |             <a href="/articles" class="join-btn join-btn--ghost">Browse Intel</a>
 922 |         </div>
 923 | 
 924 |         <!-- COMMANDER (featured) -->
 925 |         <div class="join-card join-card--commander">
 926 |             <div class="join-card-badge">FEATURED</div>
 927 |             <div class="join-card-kicker">COMMANDER</div>
 928 |             <div class="join-card-price">$49<span class="price-sub">/mo</span></div>
 929 |             <div class="join-card-desc">Full terminal access. Oracle AI analyst. Daily video briefings. Real-time alerts. Cancel anytime.</div>
 930 |             <ul class="join-features">
 931 |                 <li>Everything in Free Agent</li>
 932 |                 <li>Signal Terminal &mdash; convergence matrix with 8 live feeds</li>
 933 |                 <li>PCAF anomaly detection &mdash; GNN on every block</li>
 934 |                 <li>5-scenario Monte Carlo projection engine</li>
 935 |                 <li>Oracle AI analyst &mdash; ask anything, get signal</li>
 936 |                 <li>Daily video briefings + Avatar Stage</li>
 937 |                 <li>Real-time alert system &mdash; price, whale, narrative</li>
 938 |                 <li>API access &mdash; 1,000 requests/day</li>
 939 |             </ul>
 940 |             <button class="join-btn join-btn--red" id="joinCTA">Access the Terminal &mdash; $49/mo</button>
 941 |         </div>
 942 | 
 943 |         <!-- SOVEREIGN -->
 944 |         <div class="join-card join-card--sovereign">
 945 |             <div class="join-card-kicker">SOVEREIGN</div>
 946 |             <div class="join-card-price">Custom</div>
 947 |             <div class="join-card-desc">White-glove intelligence. Dedicated infrastructure. Team access. For funds, desks, and sovereign individuals.</div>
 948 |             <ul class="join-features">
 949 |                 <li>Everything in Commander</li>
 950 |                 <li>Team seats with admin panel</li>
 951 |                 <li>Unlimited API + webhook delivery</li>
 952 |                 <li>Priority Oracle AI queue &mdash; sub-second</li>
 953 |                 <li>Custom intelligence reports on demand</li>
 954 |                 <li>Dedicated infrastructure allocation</li>
 955 |                 <li>Direct line to the builder</li>
 956 |             </ul>
 957 |             <a href="mailto:sovereign@protocolpulse.io?subject=Sovereign%20Access" class="join-btn join-btn--gold">Contact for Access</a>
 958 |         </div>
 959 | 
 960 |     </div>
 961 | 
 962 |     <!-- ═══ FEATURE COMPARISON MATRIX ═══ -->
 963 |     <div class="join-matrix-section">
 964 |         <div class="join-matrix-kicker">CAPABILITY MATRIX</div>
 965 |         <div class="join-matrix-title">Compare Every Feature</div>
 966 |         <div class="join-matrix-wrap">
 967 |             <table class="join-matrix">
 968 |                 <thead>
 969 |                     <tr>
 970 |                         <th>Feature</th>
 971 |                         <th>Free Agent</th>
 972 |                         <th>Commander</th>
 973 |                         <th>Sovereign</th>
 974 |                     </tr>
 975 |                 </thead>
 976 |                 <tbody>
 977 |                     <tr>
 978 |                         <td>Intelligence articles</td>
 979 |                         <td class="mx-yes">&#10003;</td>
 980 |                         <td class="mx-yes">&#10003;</td>
 981 |                         <td class="mx-yes">&#10003;</td>
 982 |                     </tr>
 983 |                     <tr>
 984 |                         <td>Market overview &amp; charts</td>
 985 |                         <td class="mx-yes">&#10003;</td>
 986 |                         <td class="mx-yes">&#10003;</td>
 987 |                         <td class="mx-yes">&#10003;</td>
 988 |                     </tr>
 989 |                     <tr>
 990 |                         <td>Whale Watcher</td>
 991 |                         <td class="mx-yes">&#10003;</td>
 992 |                         <td class="mx-yes">&#10003;</td>
 993 |                         <td class="mx-yes">&#10003;</td>
 994 |                     </tr>
 995 |                     <tr>
 996 |                         <td>Merchant Map</td>
 997 |                         <td class="mx-yes">&#10003;</td>
 998 |                         <td class="mx-yes">&#10003;</td>
 999 |                         <td class="mx-yes">&#10003;</td>
1000 |                     </tr>
1001 |                     <tr>
1002 |                         <td>RSS / Nostr signal feeds</td>
1003 |                         <td class="mx-yes">&#10003;</td>
1004 |                         <td class="mx-yes">&#10003;</td>
1005 |                         <td class="mx-yes">&#10003;</td>
1006 |                     </tr>
1007 |                     <tr>
1008 |                         <td>Signal Terminal</td>
1009 |                         <td class="mx-no">&#8212;</td>
1010 |                         <td class="mx-yes">&#10003;</td>
1011 |                         <td class="mx-yes">&#10003;</td>
1012 |                     </tr>
1013 |                     <tr>
1014 |                         <td>PCAF anomaly detection</td>
1015 |                         <td class="mx-no">&#8212;</td>
1016 |                         <td class="mx-yes">&#10003;</td>
1017 |                         <td class="mx-yes">&#10003;</td>
1018 |                     </tr>
1019 |                     <tr>
1020 |                         <td>Monte Carlo projections</td>
1021 |                         <td class="mx-no">&#8212;</td>
1022 |                         <td class="mx-yes">&#10003;</td>
1023 |                         <td class="mx-yes">&#10003;</td>
1024 |                     </tr>
1025 |                     <tr>
1026 |                         <td>Oracle AI analyst</td>
1027 |                         <td class="mx-no">&#8212;</td>
1028 |                         <td class="mx-yes">&#10003;</td>
1029 |                         <td class="mx-val">PRIORITY</td>
1030 |                     </tr>
1031 |                     <tr>
1032 |                         <td>Daily video briefings</td>
1033 |                         <td class="mx-no">&#8212;</td>
1034 |                         <td class="mx-yes">&#10003;</td>
1035 |                         <td class="mx-yes">&#10003;</td>
1036 |                     </tr>
1037 |                     <tr>
1038 |                         <td>Real-time alerts</td>
1039 |                         <td class="mx-no">&#8212;</td>
1040 |                         <td class="mx-yes">&#10003;</td>
1041 |                         <td class="mx-val">+ WEBHOOK</td>
1042 |                     </tr>
1043 |                     <tr>
1044 |                         <td>API requests</td>
1045 |                         <td class="mx-val">60/hr</td>
1046 |                         <td class="mx-val">1,000/day</td>
1047 |                         <td class="mx-val">UNLIMITED</td>
1048 |                     </tr>
1049 |                     <tr>
1050 |                         <td>Team seats</td>
1051 |                         <td class="mx-no">&#8212;</td>
1052 |                         <td class="mx-no">&#8212;</td>
1053 |                         <td class="mx-yes">&#10003;</td>
1054 |                     </tr>
1055 |                     <tr>
1056 |                         <td>Custom reports</td>
1057 |                         <td class="mx-no">&#8212;</td>
1058 |                         <td class="mx-no">&#8212;</td>
1059 |                         <td class="mx-yes">&#10003;</td>
1060 |                     </tr>
1061 |                     <tr>
1062 |                         <td>Dedicated infrastructure</td>
1063 |                         <td class="mx-no">&#8212;</td>
1064 |                         <td class="mx-no">&#8212;</td>
1065 |                         <td class="mx-yes">&#10003;</td>
1066 |                     </tr>
1067 |                     <tr>
1068 |                         <td>Direct builder access</td>
1069 |                         <td class="mx-no">&#8212;</td>
1070 |                         <td class="mx-no">&#8212;</td>
1071 |                         <td class="mx-yes">&#10003;</td>
1072 |                     </tr>
1073 |                 </tbody>
1074 |             </table>
1075 |         </div>
1076 |     </div>
1077 | 
1078 |     <!-- ═══ ACCESS CODE TERMINAL ═══ -->
1079 |     <div class="join-section-label"><span>HAVE AN ACCESS CODE?</span></div>
1080 | 
1081 |     <div class="join-promo" id="promoSection">
1082 |         <div class="join-promo-titlebar">
1083 |             <div class="join-promo-dots">
1084 |                 <span></span><span></span><span></span>
1085 |             </div>
1086 |             <span class="join-promo-titlebar-text">sovereign_access_terminal v2.1</span>
1087 |         </div>
1088 |         <div class="join-promo-body">
1089 |             <div class="join-promo-header">
1090 |                 <div class="join-promo-dot" aria-hidden="true"></div>
1091 |                 <div class="join-promo-label">CLASSIFIED ACCESS TERMINAL</div>
1092 |             </div>
1093 |             <div class="join-promo-sub">Team and sovereign access codes unlock premium tiers instantly. Enter your code below.<span class="join-promo-cursor" aria-hidden="true"></span></div>
1094 |             <div class="join-promo-row">
1095 |                 <input type="text" class="join-promo-input" id="promoInput"
1096 |                        placeholder="Enter access code..."
1097 |                        autocomplete="off" spellcheck="false"
1098 |                        aria-label="Sovereign access code">
1099 |                 <button class="join-promo-submit" id="promoSubmit">Unlock Terminal</button>
1100 |             </div>
1101 |             <div class="join-promo-msg" id="promoMsg"></div>
1102 |             <div class="join-promo-hint">Codes are distributed to sovereign-tier teams and early operatives.</div>
1103 |         </div>
1104 |     </div>
1105 | 
1106 |     <!-- ═══ CLOSING CTA ═══ -->
1107 |     <div class="join-closing">
1108 |         <div class="join-eq" aria-hidden="true">
1109 |             <div class="join-eq-bar"></div>
1110 |             <div class="join-eq-bar"></div>
1111 |             <div class="join-eq-bar"></div>
1112 |             <div class="join-eq-bar"></div>
1113 |             <div class="join-eq-bar"></div>
1114 |         </div>
1115 |         <div class="join-closing-kicker">TOMORROW'S BRIEF STARTS NOW</div>
1116 |         <h2>Stop Trusting.<br>Start <span class="hero-red">Verifying.</span></h2>
1117 |         <p>
1118 |             Protocol Pulse runs on sovereign infrastructure &mdash; 4x RTX 4090 GPUs, bare metal, zero cloud. Every signal is computed locally. Every insight is ours.
1119 |         </p>
1120 |         <button class="join-closing-btn" id="joinClosingCTA">Get Commander Access &mdash; $49/mo</button>
1121 |     </div>
1122 | 
1123 |     <!-- ═══ SOCIAL PROOF ═══ -->
1124 |     <div class="join-proof">
1125 |         <div class="join-proof-kicker">BUILT ON ULTRON &mdash; SOVEREIGN INFRASTRUCTURE</div>
1126 |         <div class="join-proof-grid">
1127 |             <div class="join-proof-stat"><span>4x</span> RTX 4090</div>
1128 |             <div class="join-proof-stat"><span>Real-time</span> GNN inference</div>
1129 |             <div class="join-proof-stat"><span>8</span> live data feeds</div>
1130 |             <div class="join-proof-stat"><span>60s</span> sentinel cycle</div>
1131 |             <div class="join-proof-stat"><span>0</span> third-party deps</div>
1132 |             <div class="join-proof-stat"><span>Self-hosted</span> bare metal</div>
1133 |         </div>
1134 |     </div>
1135 | 
1136 |     <!-- ═══ BOTTOM LINKS ═══ -->
1137 |     <div class="join-bottom">
1138 |         <a href="/signal-terminal">Already have access? <span>Open Terminal &rarr;</span></a>
1139 |     </div>
1140 | 
1141 | </div>
1142 | 
1143 | 
1144 | <script>
1145 | (function() {
1146 |     'use strict';
1147 | 
1148 |     /* ── Red particle system ── */
1149 |     var canvas = document.getElementById('particleCanvas');
1150 |     if (canvas) {
1151 |         var ctx = canvas.getContext('2d');
1152 |         var particles = [];
1153 |         var PARTICLE_COUNT = 50;
1154 | 
1155 |         function resizeCanvas() {
1156 |             canvas.width = window.innerWidth;
1157 |             canvas.height = window.innerHeight;
1158 |         }
1159 |         resizeCanvas();
1160 |         window.addEventListener('resize', resizeCanvas);
1161 | 
1162 |         function Particle() {
1163 |             this.reset();
1164 |         }
1165 |         Particle.prototype.reset = function() {
1166 |             this.x = Math.random() * canvas.width;
1167 |             this.y = Math.random() * canvas.height;
1168 |             this.vx = (Math.random() - 0.5) * 0.3;
1169 |             this.vy = -Math.random() * 0.4 - 0.1;
1170 |             this.radius = Math.random() * 1.5 + 0.5;
1171 |             this.opacity = Math.random() * 0.4 + 0.1;
1172 |             this.life = Math.random() * 300 + 100;
1173 |             this.age = 0;
1174 |         };
1175 |         Particle.prototype.update = function() {
1176 |             this.x += this.vx;
1177 |             this.y += this.vy;
1178 |             this.age++;
1179 |             if (this.age > this.life || this.y < -10 || this.x < -10 || this.x > canvas.width + 10) {
1180 |                 this.reset();
1181 |                 this.y = canvas.height + 10;
1182 |             }
1183 |         };
1184 |         Particle.prototype.draw = function() {
1185 |             var fade = 1 - (this.age / this.life);
1186 |             ctx.beginPath();
1187 |             ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
1188 |             ctx.fillStyle = 'rgba(255,59,95,' + (this.opacity * fade).toFixed(3) + ')';
1189 |             ctx.fill();
1190 |         };
1191 | 
1192 |         for (var i = 0; i < PARTICLE_COUNT; i++) {
1193 |             particles.push(new Particle());
1194 |         }
1195 | 
1196 |         function animateParticles() {
1197 |             ctx.clearRect(0, 0, canvas.width, canvas.height);
1198 |             for (var j = 0; j < particles.length; j++) {
1199 |                 particles[j].update();
1200 |                 particles[j].draw();
1201 |             }
1202 |             requestAnimationFrame(animateParticles);
1203 |         }
1204 |         animateParticles();
1205 |     }
1206 | 
1207 |     /* ── Live ticker ── */
1208 |     function fetchTicker() {
1209 |         fetch('/api/intelligence/state/public')
1210 |             .then(function(r) { return r.json(); })
1211 |             .then(function(d) {
1212 |                 if (d.price && d.price.usd) {
1213 |                     var el = document.getElementById('jTicker-btc');
1214 |                     var ch = d.price.change_24h || 0;
1215 |                     var arrow = ch >= 0 ? ' \u25B2' : ' \u25BC';
1216 |                     var cls = ch >= 0 ? 'ticker-up' : 'ticker-down';
1217 |                     el.innerHTML = 'BTC $' + Number(d.price.usd).toLocaleString(undefined, {maximumFractionDigits:0}) +
1218 |                         ' <span class="' + cls + '">' + arrow + ' ' + Math.abs(ch).toFixed(1) + '%</span>';
1219 |                 }
1220 |                 if (d.fng && d.fng.value) {
1221 |                     document.getElementById('jTicker-fng').textContent = 'F&G ' + d.fng.value + ' ' + (d.fng.label || '');
1222 |                 }
1223 |                 if (d.block_height) {
1224 |                     document.getElementById('jTicker-block').textContent = 'BLOCK ' + Number(d.block_height).toLocaleString();
1225 |                 }
1226 |             })
1227 |             .catch(function(err) {
1228 |                 console.error('[ticker] Failed to fetch intelligence state:', err);
1229 |             });
1230 |     }
1231 |     fetchTicker();
1232 |     setInterval(fetchTicker, 30000);
1233 | 
1234 |     /* ── Stripe Commander checkout ── */
1235 |     function startCheckout() {
1236 |         var joinBtn = document.getElementById('joinCTA');
1237 |         var closingBtn = document.getElementById('joinClosingCTA');
1238 |         joinBtn.disabled = true;
1239 |         joinBtn.textContent = 'Redirecting to checkout...';
1240 | 
1241 |         fetch('/api/v1/checkout/create-session', {
1242 |             method: 'POST',
1243 |             headers: { 'Content-Type': 'application/json' },
1244 |             body: JSON.stringify({})
1245 |         })
1246 |         .then(function(r) { return r.json(); })
1247 |         .then(function(data) {
1248 |             if (data.url) {
1249 |                 window.location.href = data.url;
1250 |             } else {
1251 |                 joinBtn.disabled = false;
1252 |                 joinBtn.textContent = 'Access the Terminal \u2014 $49/mo';
1253 |                 closingBtn.textContent = 'Get Commander Access \u2014 $49/mo';
1254 |                 alert(data.error || 'Checkout unavailable. Please try again.');
1255 |             }
1256 |         })
1257 |         .catch(function() {
1258 |             joinBtn.disabled = false;
1259 |             joinBtn.textContent = 'Access the Terminal \u2014 $49/mo';
1260 |             alert('Network error \u2014 please try again.');
1261 |         });
1262 |     }
1263 | 
1264 |     document.getElementById('joinCTA').addEventListener('click', startCheckout);
1265 |     document.getElementById('joinClosingCTA').addEventListener('click', startCheckout);
1266 | 
1267 |     /* ── Promo code ── */
1268 |     var promoInput = document.getElementById('promoInput');
1269 |     var promoSubmit = document.getElementById('promoSubmit');
1270 |     var promoMsg = document.getElementById('promoMsg');
1271 | 
1272 |     function applyPromo() {
1273 |         var code = promoInput.value.trim();
1274 |         if (!code) return;
1275 | 
1276 |         promoMsg.className = 'join-promo-msg';
1277 |         promoMsg.style.display = 'none';
1278 |         promoSubmit.disabled = true;
1279 |         promoSubmit.textContent = 'Verifying...';
1280 | 
1281 |         fetch('/api/apply-promo', {
1282 |             method: 'POST',
1283 |             headers: { 'Content-Type': 'application/json' },
1284 |             body: JSON.stringify({ code: code })
1285 |         })
1286 |         .then(function(r) {
1287 |             if (r.status === 429) {
1288 |                 return { ok: false, data: { error: 'Too many attempts. Please wait and try again.' } };
1289 |             }
1290 |             return r.json().then(function(d) { return { ok: r.ok, data: d }; });
1291 |         })
1292 |         .then(function(res) {
1293 |             if (res.ok && res.data.success) {
1294 |                 promoMsg.textContent = '\u2713 ' + (res.data.message || 'Access unlocked. Redirecting...');
1295 |                 promoMsg.className = 'join-promo-msg success';
1296 |                 setTimeout(function() {
1297 |                     window.location.href = res.data.redirect || '/signal-terminal';
1298 |                 }, 1200);
1299 |             } else {
1300 |                 promoMsg.textContent = res.data.error || 'Invalid access code';
1301 |                 promoMsg.className = 'join-promo-msg error';
1302 |                 promoSubmit.disabled = false;
1303 |                 promoSubmit.textContent = 'Unlock Terminal';
1304 |             }
1305 |         })
1306 |         .catch(function() {
1307 |             promoMsg.textContent = 'Network error \u2014 try again';
1308 |             promoMsg.className = 'join-promo-msg error';
1309 |             promoSubmit.disabled = false;
1310 |             promoSubmit.textContent = 'Unlock Terminal';
1311 |         });
1312 |     }
1313 | 
1314 |     promoSubmit.addEventListener('click', applyPromo);
1315 |     promoInput.addEventListener('keydown', function(e) {
1316 |         if (e.key === 'Enter') { e.preventDefault(); applyPromo(); }
1317 |     });
1318 | })();
1319 | </script>
1320 | {% endblock %}
1321 | 
```

---

## YOUR REVIEW TASK — JOIN PAGE PREMIUM AUDIT (5 CRITICAL QUESTIONS)

You are auditing the /join page for a premium Bitcoin intelligence product ($49/mo Commander tier).
This page is the primary revenue conversion surface. Every pixel matters.

### Q1 — PREMIUM PERCEPTION
Does the page feel premium enough to justify a $49/mo subscription?
Rate the visual hierarchy, glassmorphism quality, typography, color system.

### Q2 — PROMO CODE SECURITY
Is the /api/apply-promo endpoint secure against brute force attacks?
Check: rate limiting, input validation, timing attacks, response enumeration.

### Q3 — STRIPE INTEGRATION
Is the Stripe integration correct for Commander checkout?
Check: STRIPE_PUBLIC_KEY handling, checkout flow, signup modal, error states.

### Q4 — MOBILE LAYOUT
Is the mobile layout production quality?
Check responsive breakpoints (960px, 600px).

### Q5 — VISUAL DESIGN SYSTEM COMPLIANCE
Does the design match the VISUAL_DESIGN_SYSTEM brand standards?
Check: color palette, typography, three-source glow system, glassmorphism.

### RESPONSE FORMAT
For each question (Q1-Q5):
- DETAILED ANALYSIS with line number citations
- SEVERITY: CRITICAL / HIGH / MEDIUM / LOW
- SPECIFIC FIX with code-level recommendation

### FINAL VERDICT
- How many CRITICAL issues found?
- Top 3 changes needed before production
- Overall: PASS / PASS WITH FIXES / FAIL

