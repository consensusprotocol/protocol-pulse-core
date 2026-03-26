# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: value-stream-post-audit
# Branch: main
# Generated: 2026-03-26 14:45 UTC
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

### File: templates/value_stream.html (894 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Value Stream — Proof of Value Content Curation | Protocol Pulse{% endblock %}
   4 | 
   5 | {% block meta_description %}Opt out of engagement farming. Content rises by economic signal — sats zapped, not likes clicked. Your attention is sovereign.{% endblock %}
   6 | 
   7 | {% block extra_head %}
   8 | <style>
   9 |     :root {
  10 |         --vs-red: #ff3b5f;
  11 |         --vs-black: #06070b;
  12 |         --vs-panel: #0d0d0d;
  13 |         --vs-gold: #f8c15c;
  14 |         --vs-text: #eef2ff;
  15 |         --vs-muted: #95a0ba;
  16 |         --vs-glow-red: rgba(255,59,95,0.15);
  17 |     }
  18 | 
  19 |     body { background: var(--vs-black); }
  20 | 
  21 |     /* ── HERO ── */
  22 |     .vs-hero {
  23 |         position: relative;
  24 |         padding: 80px 20px 60px;
  25 |         text-align: center;
  26 |         overflow: hidden;
  27 |         background:
  28 |             radial-gradient(ellipse at 20% 30%, var(--vs-glow-red), transparent 60%),
  29 |             radial-gradient(ellipse at 80% 70%, rgba(93,228,255,0.06), transparent 50%),
  30 |             var(--vs-black);
  31 |     }
  32 |     .vs-hero::after {
  33 |         content: '';
  34 |         position: absolute;
  35 |         inset: 0;
  36 |         background: repeating-linear-gradient(
  37 |             0deg,
  38 |             transparent,
  39 |             transparent 3px,
  40 |             rgba(255,255,255,0.015) 3px,
  41 |             rgba(255,255,255,0.015) 4px
  42 |         );
  43 |         pointer-events: none;
  44 |     }
  45 |     .vs-hero-title {
  46 |         font-family: 'JetBrains Mono', monospace;
  47 |         font-size: clamp(2.4rem, 5vw, 3.6rem);
  48 |         font-weight: 900;
  49 |         color: var(--vs-text);
  50 |         letter-spacing: -0.03em;
  51 |         margin: 0 0 12px;
  52 |         text-shadow: 0 4px 28px rgba(0,0,0,0.4);
  53 |     }
  54 |     .vs-hero-sub {
  55 |         font-family: 'JetBrains Mono', monospace;
  56 |         font-size: clamp(0.7rem, 1.2vw, 0.85rem);
  57 |         color: var(--vs-red);
  58 |         letter-spacing: 0.2em;
  59 |         text-transform: uppercase;
  60 |         font-weight: 700;
  61 |         margin: 0 0 28px;
  62 |     }
  63 |     .vs-manifesto {
  64 |         max-width: 600px;
  65 |         margin: 0 auto 32px;
  66 |         font-size: 13px;
  67 |         line-height: 1.7;
  68 |         color: rgba(255,255,255,0.7);
  69 |     }
  70 |     .vs-manifesto p { margin: 0 0 8px; }
  71 |     .vs-sep {
  72 |         width: 80px;
  73 |         height: 2px;
  74 |         background: var(--vs-red);
  75 |         margin: 0 auto 32px;
  76 |     }
  77 | 
  78 |     /* ── STATS ROW ── */
  79 |     .vs-stats {
  80 |         display: flex;
  81 |         justify-content: center;
  82 |         gap: 40px;
  83 |         flex-wrap: wrap;
  84 |     }
  85 |     .vs-stat {
  86 |         text-align: center;
  87 |     }
  88 |     .vs-stat-label {
  89 |         font-family: 'JetBrains Mono', monospace;
  90 |         font-size: 9px;
  91 |         letter-spacing: 0.18em;
  92 |         text-transform: uppercase;
  93 |         color: var(--vs-muted);
  94 |         font-weight: 800;
  95 |         margin-bottom: 4px;
  96 |     }
  97 |     .vs-stat-value {
  98 |         font-family: 'JetBrains Mono', monospace;
  99 |         font-size: clamp(1.2rem, 2vw, 1.6rem);
 100 |         font-weight: 900;
 101 |         color: var(--vs-text);
 102 |         letter-spacing: -0.03em;
 103 |     }
 104 | 
 105 |     /* ── CONTAINER ── */
 106 |     .vs-container {
 107 |         max-width: 1100px;
 108 |         margin: 0 auto;
 109 |         padding: 0 20px;
 110 |     }
 111 | 
 112 |     /* ── SECTION HEADINGS ── */
 113 |     .vs-section-title {
 114 |         font-family: 'JetBrains Mono', monospace;
 115 |         font-size: 11px;
 116 |         letter-spacing: 0.18em;
 117 |         text-transform: uppercase;
 118 |         color: var(--vs-red);
 119 |         font-weight: 800;
 120 |         margin-bottom: 24px;
 121 |         padding-bottom: 12px;
 122 |         border-bottom: 1px solid rgba(255,59,95,0.2);
 123 |     }
 124 | 
 125 |     /* ── SUBMIT SECTION ── */
 126 |     .vs-submit {
 127 |         padding: 48px 0 40px;
 128 |     }
 129 |     .vs-submit-text {
 130 |         font-size: 13px;
 131 |         color: var(--vs-muted);
 132 |         margin-bottom: 16px;
 133 |     }
 134 |     .vs-submit-row {
 135 |         display: flex;
 136 |         gap: 12px;
 137 |         align-items: stretch;
 138 |     }
 139 |     .vs-url-wrap {
 140 |         flex: 1;
 141 |         position: relative;
 142 |     }
 143 |     .vs-url-input {
 144 |         width: 100%;
 145 |         background: #000;
 146 |         border: 1px solid rgba(255,59,95,0.3);
 147 |         color: var(--vs-text);
 148 |         padding: 14px 16px;
 149 |         font-family: 'JetBrains Mono', monospace;
 150 |         font-size: 14px;
 151 |         border-radius: 4px;
 152 |         outline: none;
 153 |         transition: border-color 0.2s, box-shadow 0.2s;
 154 |         box-sizing: border-box;
 155 |     }
 156 |     .vs-url-input:focus {
 157 |         border-color: var(--vs-red);
 158 |         box-shadow: 0 0 16px rgba(255,59,95,0.15);
 159 |     }
 160 |     .vs-url-input::placeholder { color: rgba(255,255,255,0.25); }
 161 |     .vs-platform-badge {
 162 |         position: absolute;
 163 |         right: 12px;
 164 |         top: 50%;
 165 |         transform: translateY(-50%);
 166 |         font-family: 'JetBrains Mono', monospace;
 167 |         font-size: 9px;
 168 |         font-weight: 800;
 169 |         letter-spacing: 0.12em;
 170 |         padding: 3px 8px;
 171 |         border-radius: 3px;
 172 |         display: none;
 173 |         text-transform: uppercase;
 174 |     }
 175 |     .vs-platform-badge.show { display: inline-block; }
 176 |     .vs-platform-badge.x { background: rgba(29,161,242,0.2); color: #1da1f2; }
 177 |     .vs-platform-badge.youtube { background: rgba(255,0,0,0.2); color: #ff4444; }
 178 |     .vs-platform-badge.nostr { background: rgba(138,43,226,0.2); color: #a855f7; }
 179 |     .vs-platform-badge.reddit { background: rgba(255,69,0,0.2); color: #ff4500; }
 180 |     .vs-platform-badge.stacker { background: rgba(248,193,92,0.2); color: var(--vs-gold); }
 181 |     .vs-submit-btn {
 182 |         background: var(--vs-red);
 183 |         color: #fff;
 184 |         border: none;
 185 |         padding: 14px 24px;
 186 |         font-family: 'JetBrains Mono', monospace;
 187 |         font-size: 12px;
 188 |         font-weight: 700;
 189 |         letter-spacing: 0.06em;
 190 |         cursor: pointer;
 191 |         border-radius: 4px;
 192 |         white-space: nowrap;
 193 |         transition: transform 0.15s, box-shadow 0.15s;
 194 |     }
 195 |     .vs-submit-btn:hover {
 196 |         transform: translateY(-1px);
 197 |         box-shadow: 0 4px 16px rgba(255,59,95,0.3);
 198 |     }
 199 | 
 200 |     /* ── FEED LAYOUT ── */
 201 |     .vs-feed-layout {
 202 |         display: grid;
 203 |         grid-template-columns: 1fr 340px;
 204 |         gap: 40px;
 205 |         padding-bottom: 60px;
 206 |     }
 207 |     @media (max-width: 900px) {
 208 |         .vs-feed-layout { grid-template-columns: 1fr; }
 209 |     }
 210 | 
 211 |     /* ── CONTENT CARDS ── */
 212 |     .vs-card {
 213 |         background: var(--vs-panel);
 214 |         border-left: 2px solid var(--vs-red);
 215 |         padding: 20px 20px 16px;
 216 |         margin-bottom: 16px;
 217 |         transition: transform 0.2s, box-shadow 0.2s;
 218 |         position: relative;
 219 |     }
 220 |     .vs-card:hover {
 221 |         transform: translateY(-4px);
 222 |         box-shadow: 0 8px 32px rgba(255,59,95,0.08);
 223 |     }
 224 |     .vs-card-head {
 225 |         display: flex;
 226 |         align-items: center;
 227 |         justify-content: space-between;
 228 |         margin-bottom: 10px;
 229 |     }
 230 |     .vs-card-platform {
 231 |         font-family: 'JetBrains Mono', monospace;
 232 |         font-size: 9px;
 233 |         font-weight: 800;
 234 |         letter-spacing: 0.12em;
 235 |         text-transform: uppercase;
 236 |         padding: 3px 8px;
 237 |         border-radius: 3px;
 238 |     }
 239 |     .vs-card-platform.x { background: rgba(29,161,242,0.15); color: #1da1f2; }
 240 |     .vs-card-platform.youtube { background: rgba(255,0,0,0.15); color: #ff4444; }
 241 |     .vs-card-platform.nostr { background: rgba(138,43,226,0.15); color: #a855f7; }
 242 |     .vs-card-platform.reddit { background: rgba(255,69,0,0.15); color: #ff4500; }
 243 |     .vs-card-platform.stacker,
 244 |     .vs-card-platform.stacker_news { background: rgba(248,193,92,0.15); color: var(--vs-gold); }
 245 |     .vs-card-platform.web { background: rgba(255,255,255,0.08); color: var(--vs-muted); }
 246 |     .vs-card-time {
 247 |         font-family: 'JetBrains Mono', monospace;
 248 |         font-size: 11px;
 249 |         color: var(--vs-muted);
 250 |     }
 251 |     .vs-card-title {
 252 |         font-size: 15px;
 253 |         font-weight: 700;
 254 |         color: var(--vs-text);
 255 |         margin-bottom: 6px;
 256 |         line-height: 1.35;
 257 |     }
 258 |     .vs-card-title a {
 259 |         color: inherit;
 260 |         text-decoration: none;
 261 |     }
 262 |     .vs-card-title a:hover { color: #fff; }
 263 |     .vs-card-preview {
 264 |         font-size: 13px;
 265 |         color: rgba(255,255,255,0.5);
 266 |         line-height: 1.5;
 267 |         margin-bottom: 14px;
 268 |         display: -webkit-box;
 269 |         -webkit-line-clamp: 2;
 270 |         -webkit-box-orient: vertical;
 271 |         overflow: hidden;
 272 |     }
 273 |     .vs-card-footer {
 274 |         display: flex;
 275 |         align-items: center;
 276 |         justify-content: space-between;
 277 |         flex-wrap: wrap;
 278 |         gap: 10px;
 279 |     }
 280 |     .vs-card-meta {
 281 |         display: flex;
 282 |         align-items: center;
 283 |         gap: 16px;
 284 |     }
 285 |     .vs-sats {
 286 |         font-family: 'JetBrains Mono', monospace;
 287 |         font-size: 13px;
 288 |         font-weight: 700;
 289 |     }
 290 |     .vs-sats.high { color: var(--vs-red); }
 291 |     .vs-sats.mid { color: var(--vs-gold); }
 292 |     .vs-sats.low { color: var(--vs-text); }
 293 |     .vs-zaps {
 294 |         font-family: 'JetBrains Mono', monospace;
 295 |         font-size: 11px;
 296 |         color: var(--vs-muted);
 297 |     }
 298 |     .vs-curator-tag {
 299 |         font-family: 'JetBrains Mono', monospace;
 300 |         font-size: 11px;
 301 |         color: var(--vs-muted);
 302 |     }
 303 |     .vs-curator-tag.top { color: var(--vs-gold); }
 304 | 
 305 |     /* ── ZAP BUTTON ── */
 306 |     .vs-zap-btn {
 307 |         background: transparent;
 308 |         border: 1px solid rgba(255,59,95,0.4);
 309 |         color: var(--vs-red);
 310 |         font-family: 'JetBrains Mono', monospace;
 311 |         font-size: 11px;
 312 |         font-weight: 700;
 313 |         padding: 6px 14px;
 314 |         cursor: pointer;
 315 |         border-radius: 3px;
 316 |         transition: all 0.2s;
 317 |         display: flex;
 318 |         align-items: center;
 319 |         gap: 5px;
 320 |     }
 321 |     .vs-zap-btn:hover {
 322 |         background: var(--vs-red);
 323 |         color: #fff;
 324 |         box-shadow: 0 0 12px rgba(255,59,95,0.3);
 325 |     }
 326 |     .vs-zap-btn .bolt { font-size: 14px; }
 327 |     .vs-zap-btn.zapped {
 328 |         background: var(--vs-red);
 329 |         color: #fff;
 330 |         border-color: var(--vs-red);
 331 |     }
 332 | 
 333 |     /* ── EMPTY STATE ── */
 334 |     .vs-empty {
 335 |         padding: 48px 0;
 336 |         text-align: center;
 337 |     }
 338 |     .vs-empty-headline {
 339 |         font-family: 'JetBrains Mono', monospace;
 340 |         font-size: clamp(1.1rem, 2vw, 1.4rem);
 341 |         color: var(--vs-text);
 342 |         font-weight: 700;
 343 |         margin-bottom: 32px;
 344 |         letter-spacing: -0.02em;
 345 |     }
 346 |     .vs-example-grid {
 347 |         display: grid;
 348 |         grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
 349 |         gap: 16px;
 350 |         margin-bottom: 32px;
 351 |     }
 352 |     .vs-example {
 353 |         background: var(--vs-panel);
 354 |         border-left: 2px solid rgba(255,59,95,0.3);
 355 |         padding: 18px;
 356 |         opacity: 0.6;
 357 |         position: relative;
 358 |     }
 359 |     .vs-example-badge {
 360 |         font-family: 'JetBrains Mono', monospace;
 361 |         font-size: 8px;
 362 |         letter-spacing: 0.16em;
 363 |         color: var(--vs-muted);
 364 |         text-transform: uppercase;
 365 |         font-weight: 800;
 366 |         position: absolute;
 367 |         top: 8px;
 368 |         right: 10px;
 369 |     }
 370 |     .vs-example .vs-card-platform { margin-bottom: 8px; display: inline-block; }
 371 |     .vs-example-title {
 372 |         font-size: 14px;
 373 |         font-weight: 700;
 374 |         color: rgba(255,255,255,0.75);
 375 |         margin-bottom: 6px;
 376 |         line-height: 1.35;
 377 |     }
 378 |     .vs-example-desc {
 379 |         font-size: 12px;
 380 |         color: rgba(255,255,255,0.4);
 381 |         line-height: 1.5;
 382 |     }
 383 |     .vs-example-sats {
 384 |         font-family: 'JetBrains Mono', monospace;
 385 |         font-size: 12px;
 386 |         color: var(--vs-gold);
 387 |         margin-top: 10px;
 388 |     }
 389 |     .vs-cta-link {
 390 |         display: inline-block;
 391 |         font-family: 'JetBrains Mono', monospace;
 392 |         font-size: 13px;
 393 |         color: var(--vs-red);
 394 |         font-weight: 700;
 395 |         text-decoration: none;
 396 |         letter-spacing: 0.04em;
 397 |         transition: color 0.2s;
 398 |     }
 399 |     .vs-cta-link:hover { color: #ff6b85; }
 400 | 
 401 |     /* ── LEADERBOARD ── */
 402 |     .vs-leaderboard {
 403 |         margin-bottom: 40px;
 404 |     }
 405 |     .vs-leader-row {
 406 |         display: flex;
 407 |         align-items: center;
 408 |         justify-content: space-between;
 409 |         padding: 12px 0;
 410 |         border-bottom: 1px solid rgba(255,255,255,0.04);
 411 |         opacity: 0;
 412 |         animation: vs-fade-in 0.3s forwards;
 413 |     }
 414 |     .vs-leader-row:last-child { border-bottom: none; }
 415 |     .vs-leader-left {
 416 |         display: flex;
 417 |         align-items: center;
 418 |         gap: 14px;
 419 |     }
 420 |     .vs-leader-rank {
 421 |         font-family: 'JetBrains Mono', monospace;
 422 |         font-size: 20px;
 423 |         font-weight: 900;
 424 |         color: var(--vs-red);
 425 |         min-width: 32px;
 426 |     }
 427 |     .vs-leader-row:first-child .vs-leader-rank { color: var(--vs-gold); }
 428 |     .vs-leader-row:first-child { border-left: 2px solid var(--vs-gold); padding-left: 12px; }
 429 |     .vs-leader-name {
 430 |         font-size: 14px;
 431 |         font-weight: 600;
 432 |         color: var(--vs-text);
 433 |     }
 434 |     .vs-leader-right {
 435 |         text-align: right;
 436 |     }
 437 |     .vs-leader-sats {
 438 |         font-family: 'JetBrains Mono', monospace;
 439 |         font-size: 14px;
 440 |         font-weight: 700;
 441 |         color: var(--vs-text);
 442 |     }
 443 |     .vs-leader-row:first-child .vs-leader-sats { color: var(--vs-gold); }
 444 |     .vs-leader-score {
 445 |         font-family: 'JetBrains Mono', monospace;
 446 |         font-size: 10px;
 447 |         color: var(--vs-muted);
 448 |     }
 449 | 
 450 |     @keyframes vs-fade-in {
 451 |         from { opacity: 0; transform: translateY(6px); }
 452 |         to { opacity: 1; transform: translateY(0); }
 453 |     }
 454 | 
 455 |     /* ── ANTI-ALGORITHM SECTION ── */
 456 |     .vs-anti {
 457 |         padding: 60px 0;
 458 |         border-top: 1px solid rgba(255,255,255,0.04);
 459 |     }
 460 |     .vs-anti-title {
 461 |         font-family: 'JetBrains Mono', monospace;
 462 |         font-size: clamp(1.4rem, 2.5vw, 1.8rem);
 463 |         font-weight: 900;
 464 |         color: var(--vs-text);
 465 |         text-align: center;
 466 |         margin-bottom: 8px;
 467 |         letter-spacing: -0.03em;
 468 |     }
 469 |     .vs-anti-sub {
 470 |         font-size: 13px;
 471 |         color: var(--vs-muted);
 472 |         text-align: center;
 473 |         margin-bottom: 40px;
 474 |     }
 475 |     .vs-anti-grid {
 476 |         display: grid;
 477 |         grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
 478 |         gap: 16px;
 479 |         margin-bottom: 32px;
 480 |     }
 481 |     .vs-anti-card {
 482 |         background: var(--vs-panel);
 483 |         border: 1px solid rgba(255,59,95,0.12);
 484 |         padding: 24px 20px;
 485 |         transition: border-color 0.2s;
 486 |     }
 487 |     .vs-anti-card:hover {
 488 |         border-color: rgba(255,59,95,0.35);
 489 |     }
 490 |     .vs-anti-card-title {
 491 |         font-family: 'JetBrains Mono', monospace;
 492 |         font-size: 11px;
 493 |         font-weight: 800;
 494 |         letter-spacing: 0.12em;
 495 |         text-transform: uppercase;
 496 |         color: var(--vs-red);
 497 |         margin-bottom: 8px;
 498 |     }
 499 |     .vs-anti-card-desc {
 500 |         font-size: 13px;
 501 |         color: rgba(255,255,255,0.6);
 502 |         line-height: 1.6;
 503 |     }
 504 |     .vs-anti-closing {
 505 |         text-align: center;
 506 |         font-size: 13px;
 507 |         color: rgba(255,255,255,0.5);
 508 |         max-width: 560px;
 509 |         margin: 0 auto;
 510 |         line-height: 1.7;
 511 |     }
 512 | 
 513 |     /* ── NOSTR PANEL ── */
 514 |     .vs-nostr {
 515 |         background: var(--vs-panel);
 516 |         border: 1px solid rgba(138,43,226,0.2);
 517 |         padding: 20px;
 518 |         margin-bottom: 32px;
 519 |     }
 520 |     .vs-nostr-title {
 521 |         font-family: 'JetBrains Mono', monospace;
 522 |         font-size: 10px;
 523 |         font-weight: 800;
 524 |         letter-spacing: 0.14em;
 525 |         text-transform: uppercase;
 526 |         color: #a855f7;
 527 |         margin-bottom: 8px;
 528 |     }
 529 |     .vs-nostr-desc {
 530 |         font-size: 12px;
 531 |         color: var(--vs-muted);
 532 |         line-height: 1.6;
 533 |     }
 534 | 
 535 |     /* ── PLATFORM FILTERS ── */
 536 |     .vs-filters {
 537 |         display: flex;
 538 |         gap: 8px;
 539 |         flex-wrap: wrap;
 540 |         margin-bottom: 24px;
 541 |     }
 542 |     .vs-filter-btn {
 543 |         background: rgba(255,255,255,0.04);
 544 |         border: 1px solid rgba(255,255,255,0.08);
 545 |         color: var(--vs-muted);
 546 |         font-family: 'JetBrains Mono', monospace;
 547 |         font-size: 10px;
 548 |         font-weight: 700;
 549 |         letter-spacing: 0.08em;
 550 |         text-transform: uppercase;
 551 |         padding: 6px 14px;
 552 |         cursor: pointer;
 553 |         transition: all 0.2s;
 554 |         border-radius: 2px;
 555 |         text-decoration: none;
 556 |     }
 557 |     .vs-filter-btn:hover,
 558 |     .vs-filter-btn.active {
 559 |         background: rgba(255,59,95,0.12);
 560 |         border-color: var(--vs-red);
 561 |         color: var(--vs-red);
 562 |     }
 563 | 
 564 |     /* ── MOBILE ── */
 565 |     @media (max-width: 600px) {
 566 |         .vs-hero { padding: 48px 16px 36px; }
 567 |         .vs-stats { gap: 20px; }
 568 |         .vs-submit-row { flex-direction: column; }
 569 |         .vs-submit-btn { width: 100%; text-align: center; }
 570 |         .vs-card { padding: 16px; }
 571 |         .vs-card-footer { flex-direction: column; align-items: flex-start; }
 572 |         .vs-example-grid { grid-template-columns: 1fr; }
 573 |         .vs-anti-grid { grid-template-columns: 1fr; }
 574 |     }
 575 | 
 576 |     /* ── COUNT-UP ANIMATION ── */
 577 |     .vs-count-up {
 578 |         transition: all 0.6s ease-out;
 579 |     }
 580 | </style>
 581 | {% endblock %}
 582 | 
 583 | {% block content %}
 584 | <!-- ═══ HERO ═══ -->
 585 | <section class="vs-hero">
 586 |     <h1 class="vs-hero-title">PROOF OF VALUE</h1>
 587 |     <p class="vs-hero-sub">SAT-WEIGHTED CONTENT CURATION</p>
 588 |     <div class="vs-manifesto">
 589 |         <p>The best content rises based on economic signal &mdash; not engagement farming, not algorithmic manipulation, not infinite scroll dopamine loops.</p>
 590 |         <p>Your sat is your vote. Your attention is sovereign. Spend both deliberately.</p>
 591 |     </div>
 592 |     <div class="vs-sep"></div>
 593 |     <div class="vs-stats">
 594 |         <div class="vs-stat">
 595 |             <div class="vs-stat-label">TOTAL VALUE ZAPPED</div>
 596 |             <div class="vs-stat-value"><span class="vs-count-up" data-target="{{ total_sats }}">0</span> SATS</div>
 597 |         </div>
 598 |         <div class="vs-stat">
 599 |             <div class="vs-stat-label">CONTENT PIECES</div>
 600 |             <div class="vs-stat-value"><span class="vs-count-up" data-target="{{ posts|length }}">0</span></div>
 601 |         </div>
 602 |         <div class="vs-stat">
 603 |             <div class="vs-stat-label">TOP CURATOR EARNED</div>
 604 |             <div class="vs-stat-value"><span class="vs-count-up" data-target="{{ curators[0].total_sats_received if curators else 0 }}">0</span> SATS</div>
 605 |         </div>
 606 |     </div>
 607 | </section>
 608 | 
 609 | <div class="vs-container">
 610 | 
 611 |     <!-- ═══ SUBMIT ═══ -->
 612 |     <section class="vs-submit">
 613 |         <div class="vs-section-title">SIGNAL VALUE</div>
 614 |         <p class="vs-submit-text">Paste any URL. If it's worth a sat, it belongs here.</p>
 615 |         <form id="vs-submit-form" class="vs-submit-row">
 616 |             <div class="vs-url-wrap">
 617 |                 <input type="url" id="vs-url" class="vs-url-input"
 618 |                        placeholder="https://..." required autocomplete="off">
 619 |                 <span id="vs-platform-detect" class="vs-platform-badge"></span>
 620 |             </div>
 621 |             <button type="submit" class="vs-submit-btn">SUBMIT TO THE STREAM</button>
 622 |         </form>
 623 |     </section>
 624 | 
 625 |     <!-- ═══ FEED + SIDEBAR ═══ -->
 626 |     <div class="vs-feed-layout">
 627 |         <div>
 628 |             <!-- Platform Filters -->
 629 |             <div class="vs-filters">
 630 |                 <a href="/value-stream" class="vs-filter-btn {% if not selected_platform %}active{% endif %}">ALL</a>
 631 |                 <a href="/value-stream?platform=x" class="vs-filter-btn {% if selected_platform == 'x' %}active{% endif %}">X</a>
 632 |                 <a href="/value-stream?platform=youtube" class="vs-filter-btn {% if selected_platform == 'youtube' %}active{% endif %}">YOUTUBE</a>
 633 |                 <a href="/value-stream?platform=nostr" class="vs-filter-btn {% if selected_platform == 'nostr' %}active{% endif %}">NOSTR</a>
 634 |                 <a href="/value-stream?platform=reddit" class="vs-filter-btn {% if selected_platform == 'reddit' %}active{% endif %}">REDDIT</a>
 635 |                 <a href="/value-stream?platform=stacker" class="vs-filter-btn {% if selected_platform == 'stacker' %}active{% endif %}">STACKER NEWS</a>
 636 |             </div>
 637 | 
 638 |             {% if posts %}
 639 |                 {% for post in posts %}
 640 |                 <div class="vs-card">
 641 |                     <div class="vs-card-head">
 642 |                         <span class="vs-card-platform {{ post.platform or 'web' }}">{{ (post.platform or 'web')|upper }}</span>
 643 |                         <span class="vs-card-time" data-ts="{{ post.submitted_at.isoformat() if post.submitted_at else '' }}"></span>
 644 |                     </div>
 645 |                     <div class="vs-card-title">
 646 |                         <a href="{{ post.original_url }}" target="_blank" rel="noopener">
 647 |                             {{ post.title or 'Untitled' }}
 648 |                         </a>
 649 |                     </div>
 650 |                     {% if post.content_preview %}
 651 |                     <div class="vs-card-preview">{{ post.content_preview[:200] }}</div>
 652 |                     {% endif %}
 653 |                     <div class="vs-card-footer">
 654 |                         <div class="vs-card-meta">
 655 |                             <span class="vs-sats {% if (post.total_sats or 0) > 1000 %}high{% elif (post.total_sats or 0) > 100 %}mid{% else %}low{% endif %}">
 656 |                                 &#9889; {{ "{:,}".format(post.total_sats or 0) }} sats
 657 |                             </span>
 658 |                             <span class="vs-zaps">{{ post.zap_count or 0 }} zaps</span>
 659 |                             {% if post.curator %}
 660 |                             <span class="vs-curator-tag {% if loop.index <= 10 %}top{% endif %}">@{{ post.curator.display_name }}</span>
 661 |                             {% endif %}
 662 |                         </div>
 663 |                         <button class="vs-zap-btn" data-post-id="{{ post.id }}" data-sats="{{ post.total_sats or 0 }}">
 664 |                             <span class="bolt">&#9889;</span> ZAP
 665 |                         </button>
 666 |                     </div>
 667 |                 </div>
 668 |                 {% endfor %}
 669 |             {% else %}
 670 |                 <!-- ═══ EMPTY STATE ═══ -->
 671 |                 <div class="vs-empty">
 672 |                     <div class="vs-empty-headline">THE STREAM IS WAITING FOR ITS FIRST SIGNAL.</div>
 673 |                     <div class="vs-example-grid">
 674 |                         <div class="vs-example">
 675 |                             <span class="vs-example-badge">EXAMPLE</span>
 676 |                             <span class="vs-card-platform nostr">NOSTR</span>
 677 |                             <div class="vs-example-title">Taproot Assets on Lightning: the technical deep-dive every Bitcoiner should read</div>
 678 |                             <div class="vs-example-desc">A respected researcher breaks down the Taproot Assets protocol and its implications for Lightning-native assets without compromising decentralization.</div>
 679 |                             <div class="vs-example-sats">&#9889; 21,000 sats &middot; 47 zaps</div>
 680 |                         </div>
 681 |                         <div class="vs-example">
 682 |                             <span class="vs-example-badge">EXAMPLE</span>
 683 |                             <span class="vs-card-platform x">X</span>
 684 |                             <div class="vs-example-title">Self-custody is not a feature. It is the entire point.</div>
 685 |                             <div class="vs-example-desc">A sovereignty op-ed that cuts through the noise. No hedging. No disclaimers. Just first-principles thinking about why you hold your own keys.</div>
 686 |                             <div class="vs-example-sats">&#9889; 8,400 sats &middot; 23 zaps</div>
 687 |                         </div>
 688 |                         <div class="vs-example">
 689 |                             <span class="vs-example-badge">EXAMPLE</span>
 690 |                             <span class="vs-card-platform youtube">YOUTUBE</span>
 691 |                             <div class="vs-example-title">Live demo: sending 1 sat across the world in 0.3 seconds</div>
 692 |                             <div class="vs-example-desc">A Lightning Network demonstration showing instant, borderless micropayments. The future of money in real-time.</div>
 693 |                             <div class="vs-example-sats">&#9889; 5,000 sats &middot; 31 zaps</div>
 694 |                         </div>
 695 |                     </div>
 696 |                     <a href="#vs-url" class="vs-cta-link" onclick="document.getElementById('vs-url').focus(); return false;">BE THE FIRST TO SIGNAL VALUE &rarr;</a>
 697 |                 </div>
 698 |             {% endif %}
 699 |         </div>
 700 | 
 701 |         <!-- ═══ SIDEBAR ═══ -->
 702 |         <div>
 703 |             <!-- Leaderboard -->
 704 |             <div class="vs-leaderboard">
 705 |                 <div class="vs-section-title">PROOF OF WORK &mdash; TOP CURATORS</div>
 706 |                 {% if curators %}
 707 |                     {% for curator in curators[:10] %}
 708 |                     <div class="vs-leader-row" style="animation-delay: {{ loop.index * 80 }}ms">
 709 |                         <div class="vs-leader-left">
 710 |                             <span class="vs-leader-rank">{{ loop.index }}</span>
 711 |                             <span class="vs-leader-name">
 712 |                                 {{ curator.display_name }}
 713 |                                 {% if curator.verified %}<span style="color: var(--vs-gold); margin-left: 4px;" title="Verified">&#10003;</span>{% endif %}
 714 |                             </span>
 715 |                         </div>
 716 |                         <div class="vs-leader-right">
 717 |                             <div class="vs-leader-sats">{{ "{:,}".format(curator.total_sats_received or 0) }} sats</div>
 718 |                             <div class="vs-leader-score">score: {{ "%.1f"|format(curator.curator_score or 0) }}</div>
 719 |                         </div>
 720 |                     </div>
 721 |                     {% endfor %}
 722 |                 {% else %}
 723 |                     <div style="text-align: center; padding: 24px 0; color: var(--vs-muted); font-size: 13px;">
 724 |                         Curate content. Earn sats. Climb the board.
 725 |                     </div>
 726 |                 {% endif %}
 727 |             </div>
 728 | 
 729 |             <!-- Nostr Panel -->
 730 |             <div class="vs-nostr">
 731 |                 <div class="vs-nostr-title">NATIVE ON NOSTR</div>
 732 |                 <div class="vs-nostr-desc">
 733 |                     Content submitted here can be bridged as Nostr events (kind:1). Zaps settle natively via Lightning. Connect your Nostr pubkey to claim curator earnings.
 734 |                 </div>
 735 |             </div>
 736 |         </div>
 737 |     </div>
 738 | 
 739 |     <!-- ═══ THE ANTI-ALGORITHM ═══ -->
 740 |     <section class="vs-anti">
 741 |         <h2 class="vs-anti-title">THE ANTI-ALGORITHM</h2>
 742 |         <p class="vs-anti-sub">Content ranked by conviction, not manipulation.</p>
 743 |         <div class="vs-anti-grid">
 744 |             <div class="vs-anti-card">
 745 |                 <div class="vs-anti-card-title">PROOF OF VALUE FEED</div>
 746 |                 <div class="vs-anti-card-desc">Content ranked by sats received, not engagement metrics. No likes. No retweets. No impression farming. Just economic signal.</div>
 747 |             </div>
 748 |             <div class="vs-anti-card">
 749 |                 <div class="vs-anti-card-title">CURATOR ECONOMY</div>
 750 |                 <div class="vs-anti-card-desc">Discover valuable content first and earn 10% of all sats zapped to it. Your taste has a price. Prove it.</div>
 751 |             </div>
 752 |             <div class="vs-anti-card">
 753 |                 <div class="vs-anti-card-title">SOVEREIGN TIMELINE</div>
 754 |                 <div class="vs-anti-card-desc">No algorithmic amplification. No shadow bans. No engagement optimization. Chronological option always available.</div>
 755 |             </div>
 756 |             <div class="vs-anti-card">
 757 |                 <div class="vs-anti-card-title">LIGHTNING NATIVE</div>
 758 |                 <div class="vs-anti-card-desc">Every interaction is a micropayment. Your attention has a price. Value is transferred, not extracted.</div>
 759 |             </div>
 760 |         </div>
 761 |         <p class="vs-anti-closing">
 762 |             The attention economy is the most sophisticated manipulation tool in human history. Value Stream is the opt-out.
 763 |         </p>
 764 |     </section>
 765 | </div>
 766 | 
 767 | <script>
 768 | (function() {
 769 |     // ── COUNT-UP ANIMATION ──
 770 |     document.querySelectorAll('.vs-count-up').forEach(el => {
 771 |         const target = parseInt(el.dataset.target) || 0;
 772 |         if (target === 0) { el.textContent = '0'; return; }
 773 |         const duration = 1200;
 774 |         const start = performance.now();
 775 |         function step(now) {
 776 |             const elapsed = now - start;
 777 |             const progress = Math.min(elapsed / duration, 1);
 778 |             const eased = 1 - Math.pow(1 - progress, 3);
 779 |             el.textContent = Math.floor(target * eased).toLocaleString();
 780 |             if (progress < 1) requestAnimationFrame(step);
 781 |         }
 782 |         requestAnimationFrame(step);
 783 |     });
 784 | 
 785 |     // ── RELATIVE TIMESTAMPS ──
 786 |     document.querySelectorAll('.vs-card-time[data-ts]').forEach(el => {
 787 |         const ts = el.dataset.ts;
 788 |         if (!ts) return;
 789 |         const diff = (Date.now() - new Date(ts + 'Z').getTime()) / 1000;
 790 |         if (diff < 60) el.textContent = 'just now';
 791 |         else if (diff < 3600) el.textContent = Math.floor(diff / 60) + 'm ago';
 792 |         else if (diff < 86400) el.textContent = Math.floor(diff / 3600) + 'h ago';
 793 |         else el.textContent = Math.floor(diff / 86400) + 'd ago';
 794 |     });
 795 | 
 796 |     // ── PLATFORM AUTO-DETECT ──
 797 |     const urlInput = document.getElementById('vs-url');
 798 |     const badge = document.getElementById('vs-platform-detect');
 799 |     if (urlInput && badge) {
 800 |         urlInput.addEventListener('input', function() {
 801 |             const v = this.value.toLowerCase();
 802 |             let p = null;
 803 |             if (v.includes('youtube.com') || v.includes('youtu.be')) p = 'youtube';
 804 |             else if (v.includes('twitter.com') || v.includes('x.com')) p = 'x';
 805 |             else if (v.includes('nostr') || v.includes('njump') || v.includes('snort')) p = 'nostr';
 806 |             else if (v.includes('reddit.com')) p = 'reddit';
 807 |             else if (v.includes('stacker.news')) p = 'stacker';
 808 |             if (p) {
 809 |                 badge.textContent = p.toUpperCase();
 810 |                 badge.className = 'vs-platform-badge show ' + p;
 811 |             } else {
 812 |                 badge.className = 'vs-platform-badge';
 813 |             }
 814 |         });
 815 |     }
 816 | 
 817 |     // ── SUBMIT HANDLER ──
 818 |     const form = document.getElementById('vs-submit-form');
 819 |     if (form) {
 820 |         form.addEventListener('submit', async function(e) {
 821 |             e.preventDefault();
 822 |             const url = document.getElementById('vs-url').value.trim();
 823 |             if (!url) return;
 824 |             const btn = form.querySelector('.vs-submit-btn');
 825 |             const orig = btn.textContent;
 826 |             btn.textContent = 'SUBMITTING...';
 827 |             btn.disabled = true;
 828 |             try {
 829 |                 const resp = await fetch('/api/value-stream/submit', {
 830 |                     method: 'POST',
 831 |                     headers: {'Content-Type': 'application/json'},
 832 |                     body: JSON.stringify({url: url})
 833 |                 });
 834 |                 const data = await resp.json();
 835 |                 if (data.success) {
 836 |                     window.location.reload();
 837 |                 } else {
 838 |                     btn.textContent = data.error || 'FAILED';
 839 |                     setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2000);
 840 |                 }
 841 |             } catch (err) {
 842 |                 btn.textContent = 'ERROR';
 843 |                 setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2000);
 844 |             }
 845 |         });
 846 |     }
 847 | 
 848 |     // ── ZAP HANDLER ──
 849 |     document.querySelectorAll('.vs-zap-btn').forEach(btn => {
 850 |         btn.addEventListener('click', async function() {
 851 |             const postId = this.dataset.postId;
 852 |             const satsEl = this.closest('.vs-card').querySelector('.vs-sats');
 853 | 
 854 |             // Optimistic update
 855 |             if (satsEl) {
 856 |                 const current = parseInt(satsEl.textContent.replace(/[^0-9]/g, '')) || 0;
 857 |                 satsEl.innerHTML = '&#9889; ' + (current + 1000).toLocaleString() + ' sats';
 858 |             }
 859 |             this.classList.add('zapped');
 860 |             this.innerHTML = '<span class="bolt">&#9889;</span> ZAPPED';
 861 | 
 862 |             if (typeof webln !== 'undefined') {
 863 |                 try {
 864 |                     await webln.enable();
 865 |                     const resp = await fetch('/api/value-stream/invoice/' + postId, {
 866 |                         method: 'POST',
 867 |                         headers: {'Content-Type': 'application/json'},
 868 |                         body: JSON.stringify({amount_sats: 1000})
 869 |                     });
 870 |                     const data = await resp.json();
 871 |                     if (data.invoice) {
 872 |                         await webln.sendPayment(data.invoice);
 873 |                     }
 874 |                 } catch (err) {
 875 |                     // Revert on failure
 876 |                     this.classList.remove('zapped');
 877 |                     this.innerHTML = '<span class="bolt">&#9889;</span> ZAP';
 878 |                 }
 879 |             } else {
 880 |                 // No WebLN — show connect prompt
 881 |                 const msg = document.createElement('div');
 882 |                 msg.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#0d0d0d;border:1px solid rgba(255,59,95,0.4);padding:32px;z-index:9999;max-width:380px;text-align:center;font-family:"JetBrains Mono",monospace;';
 883 |                 msg.innerHTML = '<div style="font-size:13px;color:#eef2ff;margin-bottom:12px;">CONNECT LIGHTNING WALLET</div>'
 884 |                     + '<div style="font-size:11px;color:#95a0ba;margin-bottom:16px;line-height:1.6;">Install a WebLN-compatible wallet extension like Alby to zap sats directly from your browser.</div>'
 885 |                     + '<button onclick="this.parentElement.remove()" style="background:#ff3b5f;border:none;color:#fff;padding:8px 20px;cursor:pointer;font-family:\'JetBrains Mono\',monospace;font-size:11px;font-weight:700;">DISMISS</button>';
 886 |                 document.body.appendChild(msg);
 887 |                 setTimeout(() => msg.remove(), 5000);
 888 |             }
 889 |         });
 890 |     });
 891 | })();
 892 | </script>
 893 | {% endblock %}
 894 | 
```

---

## YOUR REVIEW TASK — VALUE STREAM POST-BUILD AUDIT (5 CRITICAL QUESTIONS)

### Q1 — ETHOS COMMUNICATION
Does this implementation successfully communicate the Proof of Value ethos?
Would a Bitcoin maximalist immediately understand what this is and want to participate?

### Q2 — EMPTY STATE
Is the empty state compelling enough to not feel dead?

### Q3 — CURATOR ECONOMY
Does the curator economy incentive feel genuine or gimmicky?

### Q4 — FIRST-TIME USER EXPERIENCE
What single change would most improve the first-time user experience?

### Q5 — COMPETITIVE POSITIONING
Does this feel like a legitimate competitor to Twitter/Nostr for Bitcoin content curation
or does it feel like a toy?

### RESPONSE FORMAT
For each question: DETAILED ANALYSIS + SPECIFIC RECOMMENDATION
### FINAL VERDICT: Top 3 changes needed + PASS / PASS WITH FIXES / FAIL

