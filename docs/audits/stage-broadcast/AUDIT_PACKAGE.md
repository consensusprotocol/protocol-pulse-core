# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: stage-broadcast
# Branch: main
# Generated: 2026-03-21 03:07 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)


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

### File: templates/stage.html (1493 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Oracle Stage — Protocol Pulse Live{% endblock %}
   4 | {% block meta_description %}Bitcoin intelligence. Live. Oracle reports in real time on price, on-chain signals, partner channel transcripts, and Nostr discourse.{% endblock %}
   5 | 
   6 | {% block head %}
   7 | <meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover,interactive-widget=resizes-content">
   8 | <style>
   9 | /* ══════════════════════════════════════════════════════
  10 |    ORACLE STAGE — Broadcast Desk Layout
  11 |    Aesthetic: News control room meets Bitcoin terminal.
  12 |    Obsidian base, signal-red accents, gold data rails,
  13 |    Syne Mono headlines for that teletype authority.
  14 |    ══════════════════════════════════════════════════════ */
  15 | @import url('https://fonts.googleapis.com/css2?family=Syne+Mono&family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  16 | 
  17 | :root {
  18 |   --s-bg:        #04050a;
  19 |   --s-surface:   #080b12;
  20 |   --s-border:    rgba(255,59,95,.18);
  21 |   --s-red:       #ff3b5f;
  22 |   --s-gold:      #f8c15c;
  23 |   --s-green:     #2eff8a;
  24 |   --s-muted:     rgba(255,255,255,.28);
  25 |   --s-mono:      'Syne Mono', 'JetBrains Mono', monospace;
  26 |   --s-head:      'Syne', sans-serif;
  27 | }
  28 | 
  29 | /* Page shell */
  30 | body { background: var(--s-bg); }
  31 | .stage-wrap {
  32 |   min-height: 100vh;
  33 |   background: var(--s-bg);
  34 |   background-image:
  35 |     radial-gradient(ellipse 60% 40% at 20% 10%, rgba(255,59,95,.07) 0%, transparent 60%),
  36 |     radial-gradient(ellipse 50% 35% at 80% 80%, rgba(248,193,92,.04) 0%, transparent 60%),
  37 |     repeating-linear-gradient(0deg,   rgba(255,59,95,.025) 0px, transparent 1px, transparent 39px, rgba(255,59,95,.025) 40px),
  38 |     repeating-linear-gradient(90deg,  rgba(255,59,95,.025) 0px, transparent 1px, transparent 39px, rgba(255,59,95,.025) 40px);
  39 |   padding: 0 0 60px;
  40 | }
  41 | 
  42 | /* ── TOP STATUS BAR ─────────────────────────────────── */
  43 | .stage-topbar {
  44 |   position: sticky; top: 0; z-index: 200;
  45 |   background: rgba(4,5,10,.92);
  46 |   backdrop-filter: blur(16px);
  47 |   border-bottom: 1px solid var(--s-border);
  48 |   display: flex; align-items: center; gap: 0;
  49 |   height: 42px; overflow: hidden;
  50 | }
  51 | .stage-topbar__live {
  52 |   display: flex; align-items: center; gap: 8px;
  53 |   padding: 0 20px; border-right: 1px solid var(--s-border);
  54 |   flex-shrink: 0;
  55 | }
  56 | .stage-topbar__dot {
  57 |   width: 8px; height: 8px; border-radius: 50%;
  58 |   background: var(--s-red);
  59 |   box-shadow: 0 0 6px var(--s-red);
  60 |   animation: live-pulse 1.4s ease-in-out infinite;
  61 | }
  62 | @keyframes live-pulse {
  63 |   0%,100% { opacity:1; box-shadow: 0 0 6px var(--s-red); }
  64 |   50%      { opacity:.5; box-shadow: 0 0 14px var(--s-red); }
  65 | }
  66 | .stage-topbar__label {
  67 |   font-family: var(--s-mono); font-size: 11px; letter-spacing:.18em;
  68 |   color: var(--s-red); text-transform: uppercase;
  69 | }
  70 | .stage-topbar__ticker {
  71 |   flex: 1; overflow: hidden; display: flex; align-items: center;
  72 |   padding: 0 16px;
  73 | }
  74 | .stage-topbar__ticker-inner {
  75 |   display: flex; gap: 40px; white-space: nowrap;
  76 |   animation: ticker-scroll 40s linear infinite;
  77 | }
  78 | .stage-topbar__ticker-inner:hover { animation-play-state: paused; }
  79 | @keyframes ticker-scroll {
  80 |   0%   { transform: translateX(0); }
  81 |   100% { transform: translateX(-50%); }
  82 | }
  83 | .ticker-item {
  84 |   font-family: var(--s-mono); font-size: 11px;
  85 |   color: rgba(255,255,255,.5); letter-spacing: .06em;
  86 | }
  87 | .ticker-item .ti-label { color: var(--s-muted); margin-right: 6px; }
  88 | .ticker-item .ti-val   { color: rgba(255,255,255,.85); }
  89 | .ticker-item .ti-up    { color: var(--s-green); }
  90 | .ticker-item .ti-down  { color: var(--s-red); }
  91 | .ticker-item .ti-sep   { color: var(--s-border); margin: 0 8px; }
  92 | .stage-topbar__time {
  93 |   font-family: var(--s-mono); font-size: 11px;
  94 |   color: var(--s-gold); letter-spacing: .1em;
  95 |   padding: 0 20px; border-left: 1px solid var(--s-border);
  96 |   flex-shrink: 0;
  97 | }
  98 | 
  99 | /* ── PAGE HEADER ──────────────────────────────────────  */
 100 | .stage-header {
 101 |   display: flex; align-items: center; justify-content: space-between;
 102 |   padding: 28px 32px 20px;
 103 |   border-bottom: 1px solid var(--s-border);
 104 | }
 105 | .stage-header__title {
 106 |   font-family: var(--s-head); font-size: 11px; font-weight: 700;
 107 |   letter-spacing: .3em; text-transform: uppercase;
 108 |   color: var(--s-red);
 109 | }
 110 | .stage-header__sub {
 111 |   font-family: var(--s-mono); font-size: 10px;
 112 |   color: rgba(255,255,255,.3); letter-spacing: .12em;
 113 |   margin-top: 3px;
 114 | }
 115 | .stage-header__right {
 116 |   display: flex; align-items: center; gap: 12px;
 117 | }
 118 | .stage-badge {
 119 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 120 |   padding: 4px 10px; border-radius: 3px;
 121 |   text-transform: uppercase;
 122 | }
 123 | .stage-badge--on  { background: rgba(255,59,95,.12); color: var(--s-red); border: 1px solid rgba(255,59,95,.3); }
 124 | .stage-badge--ok  { background: rgba(46,255,138,.08); color: var(--s-green); border: 1px solid rgba(46,255,138,.2); }
 125 | 
 126 | /* ── MAIN GRID ──────────────────────────────────────── */
 127 | .stage-grid {
 128 |   display: flex;
 129 |   flex-direction: column;
 130 |   align-items: center;
 131 |   gap: 0;
 132 |   max-width: 1400px;
 133 |   margin: 0 auto;
 134 |   padding: 0 24px;
 135 | }
 136 | 
 137 | /* ── MAIN CONTENT (centered) ────────────────────────── */
 138 | .stage-main {
 139 |   width: 100%;
 140 |   display: flex;
 141 |   flex-direction: column;
 142 |   align-items: center;
 143 |   padding: 24px 0 0;
 144 | }
 145 | 
 146 | /* ── AVATAR DESK ─────────────────────────────────────── */
 147 | .stage-desk {
 148 |   width: 60vw;
 149 |   max-width: 900px;
 150 |   min-width: 320px;
 151 |   margin: 0 auto;
 152 |   position: relative;
 153 | }
 154 | @media (max-width: 768px) {
 155 |   .stage-desk { width: 100%; max-width: 100%; }
 156 | }
 157 | .stage-avatar-wrap {
 158 |   width: 100%;
 159 |   position: relative;
 160 |   background: radial-gradient(circle at 50% 100%, rgba(255,59,95,.08) 0%, transparent 60%),
 161 |               #06080f;
 162 |   border: 1px solid rgba(0, 255, 200, 0.15);
 163 |   border-radius: 8px;
 164 |   overflow: hidden;
 165 |   aspect-ratio: 3/4;
 166 |   display: flex; align-items: flex-end; justify-content: center;
 167 |   box-shadow: 0 0 40px rgba(220,38,38,0.2), 0 0 80px rgba(220,38,38,0.06);
 168 | }
 169 | .stage-avatar-wrap::before {
 170 |   content: '';
 171 |   position: absolute; inset: 0;
 172 |   background: linear-gradient(to top, rgba(4,5,10,.8) 0%, transparent 40%);
 173 |   z-index: 2; pointer-events: none;
 174 | }
 175 | /* Desk surface */
 176 | .stage-avatar-wrap::after {
 177 |   content: '';
 178 |   position: absolute; bottom: 0; left: 0; right: 0; height: 28%;
 179 |   background: linear-gradient(to top, #0d1017 0%, rgba(13,16,23,.5) 70%, transparent 100%);
 180 |   z-index: 3; pointer-events: none;
 181 | }
 182 | .stage-avatar-img {
 183 |   position: absolute; inset: 0; width: 100%; height: 100%;
 184 |   object-fit: cover; object-position: center top;
 185 |   filter: brightness(.9) contrast(1.08);
 186 | }
 187 | .stage-avatar-vid {
 188 |   position: absolute; inset: 0; width: 100%; height: 100%;
 189 |   object-fit: cover; object-position: center top;
 190 |   display: none; z-index: 1;
 191 | }
 192 | .stage-avatar-vid.active { display: block; }
 193 | .stage-avatar-nameplate {
 194 |   position: absolute; bottom: 12px; left: 12px; z-index: 10;
 195 |   display: flex; align-items: center; gap: 8px;
 196 | }
 197 | .stage-avatar-nameplate__dot {
 198 |   width: 6px; height: 6px; border-radius: 50%;
 199 |   background: var(--s-red); box-shadow: 0 0 5px var(--s-red);
 200 |   animation: live-pulse 1.4s ease-in-out infinite;
 201 | }
 202 | .stage-avatar-nameplate__name {
 203 |   font-family: var(--s-mono); font-size: 11px; letter-spacing: .14em;
 204 |   color: rgba(255,255,255,.9); text-transform: uppercase;
 205 | }
 206 | 
 207 | /* ── BRIEF PANEL (right of avatar) ─────────────────── */
 208 | .stage-brief {
 209 |   display: flex; flex-direction: column; gap: 16px;
 210 | }
 211 | .stage-brief__section-label {
 212 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .22em;
 213 |   text-transform: uppercase; color: var(--s-muted);
 214 |   margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
 215 | }
 216 | .stage-brief__section-label::after {
 217 |   content: ''; flex: 1; height: 1px;
 218 |   background: linear-gradient(to right, var(--s-border), transparent);
 219 | }
 220 | .stage-brief__sentiment {
 221 |   display: flex; align-items: center; gap: 12px;
 222 |   padding: 14px 16px;
 223 |   background: var(--s-surface); border: 1px solid var(--s-border);
 224 |   border-radius: 6px;
 225 | }
 226 | .stage-brief__sentiment-bar-wrap {
 227 |   flex: 1; height: 4px; background: rgba(255,255,255,.08);
 228 |   border-radius: 2px; overflow: hidden;
 229 | }
 230 | .stage-brief__sentiment-bar {
 231 |   height: 100%; border-radius: 2px;
 232 |   background: linear-gradient(to right, var(--s-red), var(--s-gold), var(--s-green));
 233 |   transition: width .6s ease;
 234 | }
 235 | .stage-brief__sentiment-score {
 236 |   font-family: var(--s-mono); font-size: 22px; font-weight: 600;
 237 |   line-height: 1; color: #fff; min-width: 36px; text-align: right;
 238 | }
 239 | .stage-brief__sentiment-label {
 240 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .12em;
 241 |   text-transform: uppercase; margin-top: 2px;
 242 | }
 243 | 
 244 | /* Narrative card */
 245 | .stage-narrative {
 246 |   padding: 14px 16px;
 247 |   background: var(--s-surface); border: 1px solid var(--s-border);
 248 |   border-left: 3px solid var(--s-red); border-radius: 6px;
 249 |   font-family: var(--s-head); font-size: 14px; font-weight: 500;
 250 |   line-height: 1.5; color: rgba(255,255,255,.82);
 251 |   position: relative;
 252 | }
 253 | .stage-narrative::before {
 254 |   content: 'ORACLE NARRATIVE';
 255 |   font-family: var(--s-mono); font-size: 8px; letter-spacing: .22em;
 256 |   color: var(--s-red); display: block; margin-bottom: 6px;
 257 | }
 258 | 
 259 | /* Topics */
 260 | .stage-topics {
 261 |   display: flex; flex-wrap: wrap; gap: 6px;
 262 | }
 263 | .stage-topic {
 264 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 265 |   padding: 4px 10px; border-radius: 3px;
 266 |   text-transform: uppercase; border: 1px solid;
 267 | }
 268 | .stage-topic--bull  { background: rgba(46,255,138,.07);  color: var(--s-green); border-color: rgba(46,255,138,.2); }
 269 | .stage-topic--bear  { background: rgba(255,59,95,.07);   color: var(--s-red);   border-color: rgba(255,59,95,.2);  }
 270 | .stage-topic--neut  { background: rgba(248,193,92,.07);  color: var(--s-gold);  border-color: rgba(248,193,92,.2); }
 271 | 
 272 | /* Playback controls */
 273 | .stage-controls {
 274 |   display: flex; gap: 8px; align-items: center;
 275 | }
 276 | .stage-btn {
 277 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .12em;
 278 |   text-transform: uppercase; padding: 8px 16px;
 279 |   border-radius: 4px; cursor: pointer; border: 1px solid;
 280 |   transition: all .15s; flex-shrink: 0;
 281 | }
 282 | .stage-btn--primary {
 283 |   background: var(--s-red); color: #fff; border-color: var(--s-red);
 284 | }
 285 | .stage-btn--primary:hover { background: #ff1a40; }
 286 | .stage-btn--ghost {
 287 |   background: transparent; color: rgba(255,255,255,.6); border-color: var(--s-border);
 288 | }
 289 | .stage-btn--ghost:hover { border-color: rgba(255,255,255,.3); color: #fff; }
 290 | .stage-btn:disabled { opacity: .35; cursor: not-allowed; }
 291 | .stage-status {
 292 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 293 |   color: var(--s-muted); flex: 1; text-align: right;
 294 | }
 295 | .stage-status.speaking { color: var(--s-green); }
 296 | 
 297 | /* ── BRIEFING COUNTDOWN ──────────────────────────────  */
 298 | .stage-brief-countdown {
 299 |   background: var(--s-surface);
 300 |   border: 1px solid var(--s-border);
 301 |   border-radius: 8px;
 302 |   padding: 14px 16px;
 303 | }
 304 | .stage-brief-countdown__row {
 305 |   display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
 306 | }
 307 | .stage-brief-countdown__dot {
 308 |   width: 8px; height: 8px; border-radius: 50%;
 309 |   background: var(--s-muted); flex-shrink: 0;
 310 | }
 311 | .stage-brief-countdown__dot.ready {
 312 |   background: var(--s-red);
 313 |   animation: live-pulse 1.4s infinite;
 314 | }
 315 | .stage-brief-countdown__label {
 316 |   font-family: var(--s-mono); font-size: 9px;
 317 |   letter-spacing: .15em; color: var(--s-muted);
 318 | }
 319 | .stage-brief-countdown__timer {
 320 |   font-family: var(--s-mono); font-size: 28px;
 321 |   font-weight: 700; color: var(--s-gold);
 322 |   letter-spacing: .05em; line-height: 1.1;
 323 |   margin-bottom: 4px;
 324 | }
 325 | .stage-brief-countdown__timer.ready {
 326 |   color: var(--s-red);
 327 |   animation: brief-flash 2s ease-in-out infinite;
 328 | }
 329 | .stage-brief-countdown__sub {
 330 |   font-family: var(--s-mono); font-size: 10px;
 331 |   color: var(--s-muted); letter-spacing: .08em;
 332 | }
 333 | .stage-brief-countdown__play {
 334 |   margin-top: 10px; width: 100%;
 335 | }
 336 | @keyframes brief-flash {
 337 |   0%, 100% { opacity: 1; }
 338 |   50% { opacity: .6; }
 339 | }
 340 | 
 341 | /* ── CHANNEL TRANSCRIPTS ─────────────────────────────  */
 342 | .stage-transcripts {
 343 |   display: grid;
 344 |   grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
 345 |   gap: 12px;
 346 | }
 347 | /* Mobile: prevent iOS zoom + horizontal scroll carousel */
 348 | @media (max-width: 640px) {
 349 |   body { position: fixed; width: 100%; overflow: hidden; }
 350 |   .stage-wrap { overflow-y: auto; -webkit-overflow-scrolling: touch; height: 100vh; }
 351 |   .stage-transcripts {
 352 |     display: flex;
 353 |     flex-direction: row;
 354 |     overflow-x: auto;
 355 |     scroll-snap-type: x mandatory;
 356 |     -webkit-overflow-scrolling: touch;
 357 |     gap: 10px;
 358 |     padding-bottom: 12px;
 359 |     /* hide scrollbar but keep functionality */
 360 |     scrollbar-width: none;
 361 |   }
 362 |   .stage-transcripts::-webkit-scrollbar { display: none; }
 363 |   .stage-tx-card {
 364 |     flex: 0 0 82vw;          /* show ~1.1 cards at once = peek of next */
 365 |     max-width: 300px;
 366 |     scroll-snap-align: start;
 367 |     scroll-snap-stop: always;
 368 |   }
 369 |   /* Scroll hint dots */
 370 |   .stage-transcripts-wrap {
 371 |     position: relative;
 372 |   }
 373 |   .stage-tx-scroll-hint {
 374 |     display: flex;
 375 |     justify-content: center;
 376 |     gap: 5px;
 377 |     margin-top: 10px;
 378 |   }
 379 |   .stage-tx-scroll-hint span {
 380 |     width: 5px; height: 5px;
 381 |     border-radius: 50%;
 382 |     background: rgba(255,59,95,.25);
 383 |     transition: background .2s;
 384 |   }
 385 |   .stage-tx-scroll-hint span.active {
 386 |     background: var(--s-red);
 387 |   }
 388 |   /* Fade right edge to hint scrollability */
 389 |   .stage-brief__section-label + .stage-transcripts-wrap::after {
 390 |     content: '';
 391 |     position: absolute;
 392 |     right: 0; top: 0; bottom: 12px;
 393 |     width: 32px;
 394 |     background: linear-gradient(to right, transparent, var(--s-bg));
 395 |     pointer-events: none;
 396 |   }
 397 | }
 398 | .stage-tx-card {
 399 |   background: var(--s-surface);
 400 |   border: 1px solid var(--s-border);
 401 |   border-radius: 6px;
 402 |   padding: 14px 16px;
 403 |   transition: border-color .15s, transform .15s;
 404 |   cursor: default;
 405 | }
 406 | .stage-tx-card:hover {
 407 |   border-color: rgba(255,59,95,.35);
 408 |   transform: translateY(-1px);
 409 | }
 410 | .stage-tx-card__channel {
 411 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .18em;
 412 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 5px;
 413 | }
 414 | .stage-tx-card__title {
 415 |   font-family: var(--s-head); font-size: 13px; font-weight: 600;
 416 |   color: rgba(255,255,255,.9); line-height: 1.35; margin-bottom: 8px;
 417 | }
 418 | .stage-tx-card__excerpt {
 419 |   font-family: var(--s-head); font-size: 12px; font-weight: 400;
 420 |   color: rgba(255,255,255,.42); line-height: 1.5;
 421 | }
 422 | .stage-tx-card__footer {
 423 |   margin-top: 10px; padding-top: 8px;
 424 |   border-top: 1px solid rgba(255,255,255,.05);
 425 |   display: flex; justify-content: space-between; align-items: center;
 426 | }
 427 | .stage-tx-card__read-btn {
 428 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 429 |   text-transform: uppercase; color: var(--s-gold);
 430 |   background: none; border: none; cursor: pointer; padding: 0;
 431 |   transition: color .1s;
 432 | }
 433 | .stage-tx-card__read-btn:hover { color: #fff; }
 434 | .stage-tx-card__sentiment {
 435 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .08em;
 436 |   text-transform: uppercase;
 437 | }
 438 | 
 439 | /* ── SIDEBAR (now full-width below strip) ────────────  */
 440 | .stage-sidebar {
 441 |   width: 100%;
 442 |   max-width: 1100px;
 443 |   margin: 16px auto 0;
 444 |   display: grid;
 445 |   grid-template-columns: 1fr 1fr;
 446 |   gap: 16px;
 447 |   border-left: none;
 448 | }
 449 | @media (max-width: 768px) {
 450 |   .stage-sidebar { grid-template-columns: 1fr; }
 451 | }
 452 | .stage-panel {
 453 |   border-bottom: 1px solid var(--s-border);
 454 |   flex-shrink: 0;
 455 | }
 456 | .stage-panel__header {
 457 |   padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;
 458 |   background: rgba(8,11,18,.7);
 459 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 460 |   text-transform: uppercase; color: rgba(255,255,255,.4);
 461 | }
 462 | .stage-panel__header-dot {
 463 |   width: 5px; height: 5px; border-radius: 50%;
 464 |   margin-right: 7px; display: inline-block; vertical-align: middle;
 465 | }
 466 | .stage-panel__body { padding: 12px 16px; }
 467 | 
 468 | /* Price panel */
 469 | .stage-price-big {
 470 |   font-family: var(--s-head); font-size: 36px; font-weight: 800;
 471 |   color: #fff; line-height: 1; letter-spacing: -.02em;
 472 | }
 473 | .stage-price-label {
 474 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 475 |   color: var(--s-muted); margin-top: 4px; text-transform: uppercase;
 476 | }
 477 | .stage-price-change {
 478 |   font-family: var(--s-mono); font-size: 12px;
 479 |   margin-top: 8px;
 480 | }
 481 | 
 482 | /* Nostr feed */
 483 | .stage-signal-feed {
 484 |   overflow-y: auto;
 485 |   max-height: 380px;
 486 |   scrollbar-width: thin;
 487 |   scrollbar-color: rgba(255,59,95,.2) transparent;
 488 | }
 489 | .stage-signal-item {
 490 |   padding: 10px 0;
 491 |   border-bottom: 1px solid rgba(255,255,255,.04);
 492 | }
 493 | .stage-signal-item:last-child { border-bottom: none; }
 494 | .stage-signal-item__author {
 495 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 496 |   color: var(--s-gold); margin-bottom: 4px;
 497 |   white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
 498 | }
 499 | .stage-signal-item__text {
 500 |   font-family: var(--s-head); font-size: 12px;
 501 |   color: rgba(255,255,255,.6); line-height: 1.45;
 502 |   display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
 503 |   overflow: hidden;
 504 | }
 505 | 
 506 | /* Transcript reader overlay */
 507 | .stage-reader {
 508 |   display: none; position: fixed; inset: 0;
 509 |   z-index: 500; background: rgba(4,5,10,.95);
 510 |   backdrop-filter: blur(8px);
 511 |   overflow-y: auto;
 512 |   padding: 40px 24px;
 513 | }
 514 | .stage-reader.open { display: block; }
 515 | .stage-reader__inner {
 516 |   max-width: 680px; margin: 0 auto;
 517 |   background: var(--s-surface); border: 1px solid var(--s-border);
 518 |   border-radius: 8px; padding: 32px;
 519 | }
 520 | .stage-reader__close {
 521 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .14em;
 522 |   text-transform: uppercase; color: var(--s-muted);
 523 |   background: none; border: none; cursor: pointer;
 524 |   margin-bottom: 20px; display: flex; align-items: center; gap: 6px;
 525 |   transition: color .1s;
 526 | }
 527 | .stage-reader__close:hover { color: #fff; }
 528 | .stage-reader__channel {
 529 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 530 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 8px;
 531 | }
 532 | .stage-reader__title {
 533 |   font-family: var(--s-head); font-size: 22px; font-weight: 700;
 534 |   color: #fff; line-height: 1.3; margin-bottom: 16px;
 535 | }
 536 | .stage-reader__body {
 537 |   font-family: var(--s-head); font-size: 14px; font-weight: 400;
 538 |   color: rgba(255,255,255,.68); line-height: 1.7;
 539 |   white-space: pre-wrap; word-break: break-word;
 540 | }
 541 | 
 542 | /* ── INTERACTIVE MODE PANEL ─────────────────────────────  */
 543 | .stage-interactive-panel {
 544 |   display: none;
 545 |   background: var(--s-surface);
 546 |   border: 1px solid var(--s-border);
 547 |   border-radius: 8px;
 548 |   padding: 16px;
 549 |   margin-top: 12px;
 550 | }
 551 | .stage-interactive-panel.active { display: block; }
 552 | .stage-mode-badge {
 553 |   font-family: var(--s-mono); font-size: 11px; letter-spacing: .14em;
 554 |   text-transform: uppercase; padding: 5px 14px; border-radius: 4px;
 555 |   display: inline-flex; align-items: center; gap: 8px;
 556 |   transition: all .3s;
 557 | }
 558 | .stage-mode-badge.broadcast {
 559 |   background: rgba(255,59,95,.12); color: var(--s-red);
 560 |   border: 1px solid rgba(255,59,95,.3);
 561 | }
 562 | .stage-mode-badge.interactive {
 563 |   background: rgba(46,255,138,.08); color: var(--s-green);
 564 |   border: 1px solid rgba(46,255,138,.2);
 565 | }
 566 | .stage-chat-input {
 567 |   display: flex; gap: 8px; margin-top: 12px;
 568 | }
 569 | .stage-chat-input input {
 570 |   flex: 1; background: rgba(255,255,255,.05);
 571 |   border: 1px solid var(--s-border); border-radius: 4px;
 572 |   padding: 10px 14px; color: #fff;
 573 |   font-family: var(--s-head); font-size: 13px;
 574 |   outline: none; transition: border-color .15s;
 575 | }
 576 | .stage-chat-input input:focus {
 577 |   border-color: rgba(255,59,95,.5);
 578 | }
 579 | .stage-chat-input input::placeholder {
 580 |   color: rgba(255,255,255,.25);
 581 | }
 582 | .stage-mic-btn {
 583 |   width: 44px; height: 44px; border-radius: 50%;
 584 |   background: rgba(255,59,95,.12); border: 1px solid rgba(255,59,95,.3);
 585 |   color: var(--s-red); cursor: pointer;
 586 |   display: flex; align-items: center; justify-content: center;
 587 |   font-size: 18px; transition: all .15s; flex-shrink: 0;
 588 | }
 589 | .stage-mic-btn:hover { background: rgba(255,59,95,.2); }
 590 | .stage-mic-btn.recording {
 591 |   background: var(--s-red); color: #fff;
 592 |   animation: mic-pulse 1.4s infinite;
 593 | }
 594 | @keyframes mic-pulse {
 595 |   0% { box-shadow: 0 0 0 0 rgba(255,59,95,.6); }
 596 |   70% { box-shadow: 0 0 0 16px rgba(255,59,95,0); }
 597 |   100% { box-shadow: 0 0 0 0 rgba(255,59,95,0); }
 598 | }
 599 | .stage-chat-history {
 600 |   max-height: 180px; overflow-y: auto; margin-top: 10px;
 601 |   scrollbar-width: thin; scrollbar-color: rgba(255,59,95,.2) transparent;
 602 | }
 603 | .stage-chat-msg {
 604 |   font-family: var(--s-head); font-size: 12px;
 605 |   line-height: 1.5; padding: 6px 0;
 606 |   border-bottom: 1px solid rgba(255,255,255,.04);
 607 | }
 608 | .stage-chat-msg.user { color: var(--s-gold); }
 609 | .stage-chat-msg.oracle { color: rgba(255,255,255,.7); }
 610 | .stage-between-badge {
 611 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 612 |   color: var(--s-muted); text-transform: uppercase;
 613 |   margin-top: 8px;
 614 | }
 615 | 
 616 | /* Animations */
 617 | @keyframes fadeUp {
 618 |   from { opacity:0; transform:translateY(12px); }
 619 |   to   { opacity:1; transform:translateY(0); }
 620 | }
 621 | .stage-desk     { animation: fadeUp .5s ease both; }
 622 | .stage-tx-card  { animation: fadeUp .5s ease both; }
 623 | .stage-tx-card:nth-child(2) { animation-delay: .05s; }
 624 | .stage-tx-card:nth-child(3) { animation-delay: .10s; }
 625 | .stage-tx-card:nth-child(4) { animation-delay: .15s; }
 626 | .stage-tx-card:nth-child(5) { animation-delay: .20s; }
 627 | .stage-tx-card:nth-child(6) { animation-delay: .25s; }
 628 | 
 629 | /* Loading shimmer */
 630 | .shimmer {
 631 |   background: linear-gradient(90deg, rgba(255,255,255,.04) 0%, rgba(255,255,255,.08) 50%, rgba(255,255,255,.04) 100%);
 632 |   background-size: 200% 100%;
 633 |   animation: shimmer 1.5s infinite;
 634 | }
 635 | @keyframes shimmer {
 636 |   0%   { background-position: -200% 0; }
 637 |   100% { background-position: 200% 0; }
 638 | }
 639 | 
 640 | /* ── DATA STRIP (below avatar) ────────────────────── */
 641 | .stage-data-strip {
 642 |   display: grid;
 643 |   grid-template-columns: 1fr 2fr 1fr;
 644 |   gap: 16px;
 645 |   width: 100%;
 646 |   max-width: 1100px;
 647 |   margin: 16px auto 0;
 648 |   padding: 0;
 649 | }
 650 | @media (max-width: 768px) {
 651 |   .stage-data-strip { grid-template-columns: 1fr; padding: 0; }
 652 | }
 653 | 
 654 | /* ── BELOW-STRIP SECTIONS (timed briefing, transcripts) ── */
 655 | .stage-below-strip {
 656 |   width: 100%;
 657 |   max-width: 1100px;
 658 |   margin: 16px auto 0;
 659 |   display: flex; flex-direction: column; gap: 16px;
 660 | }
 661 | 
 662 | /* ── HOLOGRAM TREATMENT (stage avatar only) ─────────── */
 663 | /* (merged into .stage-avatar-wrap above) */
 664 | .stage-avatar-scanline {
 665 |   position: absolute; inset: 0;
 666 |   background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.06) 2px, rgba(0,0,0,0.06) 4px);
 667 |   pointer-events: none; z-index: 10;
 668 |   animation: scanline-drift 8s linear infinite;
 669 | }
 670 | @keyframes scanline-drift {
 671 |   from { background-position: 0 0; }
 672 |   to   { background-position: 0 100px; }
 673 | }
 674 | @keyframes pulse-dot {
 675 |   0%, 100% { opacity: 1; }
 676 |   50%      { opacity: 0.3; }
 677 | }
 678 | </style>
 679 | {% endblock %}
 680 | 
 681 | {% block content %}
 682 | <div class="stage-wrap">
 683 | 
 684 |   <!-- TOP STATUS BAR -->
 685 |   <div class="stage-topbar">
 686 |     <div class="stage-topbar__live">
 687 |       <div class="stage-topbar__dot"></div>
 688 |       <span class="stage-topbar__label">On Air</span>
 689 |     </div>
 690 |     <div class="stage-topbar__ticker">
 691 |       <div class="stage-topbar__ticker-inner" id="tickerInner">
 692 |         <span class="ticker-item">
 693 |           <span class="ti-label">BITCOIN</span>
 694 |           <span class="ti-val" id="tickerPrice">Loading…</span>
 695 |         </span>
 696 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 697 |         <span class="ticker-item">
 698 |           <span class="ti-label">SENTIMENT</span>
 699 |           <span class="ti-val" id="tickerSentiment">—</span>
 700 |         </span>
 701 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 702 |         <span class="ticker-item">
 703 |           <span class="ti-label">ORACLE</span>
 704 |           <span class="ti-val" id="tickerOracle">Standing By</span>
 705 |         </span>
 706 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 707 |         <span class="ticker-item">
 708 |           <span class="ti-label">NETWORK</span>
 709 |           <span class="ti-val" id="tickerTopics">—</span>
 710 |         </span>
 711 |         <!-- Duplicate for seamless loop -->
 712 |         <span class="ticker-item">
 713 |           <span class="ti-label">BITCOIN</span>
 714 |           <span class="ti-val" id="tickerPrice2">Loading…</span>
 715 |         </span>
 716 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 717 |         <span class="ticker-item">
 718 |           <span class="ti-label">SENTIMENT</span>
 719 |           <span class="ti-val" id="tickerSentiment2">—</span>
 720 |         </span>
 721 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 722 |         <span class="ticker-item">
 723 |           <span class="ti-label">ORACLE</span>
 724 |           <span class="ti-val">Standing By</span>
 725 |         </span>
 726 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 727 |         <span class="ticker-item">
 728 |           <span class="ti-label">NETWORK</span>
 729 |           <span class="ti-val" id="tickerTopics2">—</span>
 730 |         </span>
 731 |       </div>
 732 |     </div>
 733 |     <div class="stage-topbar__time" id="stageTime">—</div>
 734 |   </div>
 735 | 
 736 |   <!-- HEADER -->
 737 |   <div class="stage-header">
 738 |     <div>
 739 |       <div class="stage-header__title">⚡ Oracle Stage</div>
 740 |       <div class="stage-header__sub">LIVE BITCOIN INTELLIGENCE BROADCAST — PROTOCOLPULSE.IO</div>
 741 |     </div>
 742 |     <div class="stage-header__right">
 743 |       <div class="stage-badge stage-badge--on">● On Air</div>
 744 |       <div class="stage-badge stage-badge--ok" id="avatarStatusBadge">● Avatar Ready</div>
 745 |     </div>
 746 |   </div>
 747 | 
 748 |   <!-- MAIN GRID -->
 749 |   <div class="stage-grid">
 750 | 
 751 |     <!-- CENTERED: Avatar panel -->
 752 |     <div class="stage-main">
 753 |       <div class="stage-desk">
 754 |         <!-- Avatar -->
 755 |         <div class="stage-avatar-wrap">
 756 |           <img class="stage-avatar-img" id="avatarStill"
 757 |                src="/static/oracle_avatar.png" alt="Oracle Avatar"
 758 |                onerror="this.style.display='none'">
 759 |           <video class="stage-avatar-vid" id="avatarVid"
 760 |                  playsinline webkit-playsinline muted autoplay></video>
 761 |           <div class="stage-avatar-scanline"></div>
 762 |           <div class="stage-avatar-nameplate">
 763 |             <div class="stage-avatar-nameplate__dot"></div>
 764 |             <div class="stage-avatar-nameplate__name">Oracle — Protocol Pulse</div>
 765 |           </div>
 766 |         </div>
 767 |         <div style="font-family:monospace;font-size:11px;color:#00ffc8;letter-spacing:3px;border-top:1px solid rgba(0,255,200,0.2);padding:6px 12px;background:rgba(0,0,0,0.8)">
 768 |           <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#DC2626;margin-right:8px;animation:pulse-dot 1.5s infinite"></span>
 769 |           PROTOCOL PULSE / ACTIVE
 770 |         </div>
 771 |       </div>
 772 |     </div><!-- /stage-main -->
 773 | 
 774 |     <!-- DATA STRIP: sentiment | narrative | topics + controls -->
 775 |     <div class="stage-data-strip">
 776 |       <!-- Column 1: Sentiment -->
 777 |       <div>
 778 |         <div class="stage-brief__section-label">Market Sentiment</div>
 779 |         <div class="stage-brief__sentiment">
 780 |           <div>
 781 |             <div class="stage-brief__sentiment-score" id="sentimentScore">—</div>
 782 |             <div class="stage-brief__sentiment-label" id="sentimentLabel">Loading</div>
 783 |           </div>
 784 |           <div style="flex:1">
 785 |             <div class="stage-brief__sentiment-bar-wrap">
 786 |               <div class="stage-brief__sentiment-bar" id="sentimentBar" style="width:50%"></div>
 787 |             </div>
 788 |             <div style="display:flex;justify-content:space-between;margin-top:4px">
 789 |               <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-red)">BEARISH</span>
 790 |               <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-green)">BULLISH</span>
 791 |             </div>
 792 |           </div>
 793 |         </div>
 794 |       </div>
 795 | 
 796 |       <!-- Column 2: Narrative -->
 797 |       <div>
 798 |         <div class="stage-narrative" id="narrativeText">Loading Oracle narrative…</div>
 799 |       </div>
 800 | 
 801 |       <!-- Column 3: Topics + Broadcast buttons -->
 802 |       <div>
 803 |         <div class="stage-brief__section-label">Active Topics</div>
 804 |         <div class="stage-topics" id="topicsWrap">
 805 |           <span class="stage-topic stage-topic--neut shimmer" style="width:100px;height:20px;">&nbsp;</span>
 806 |         </div>
 807 |         <div style="margin-top:12px">
 808 |           <div class="stage-brief__section-label">Oracle Broadcast</div>
 809 |           <div class="stage-controls">
 810 |             <button class="stage-btn stage-btn--primary" id="briefBtn" onclick="requestBrief()">
 811 |               ▶ Daily Brief
 812 |             </button>
 813 |             <button class="stage-btn stage-btn--ghost" id="greetBtn" onclick="requestGreet()">
 814 |               👋 Greet
 815 |             </button>
 816 |             <div class="stage-status" id="stageStatus">Ready</div>
 817 |           </div>
 818 |         </div>
 819 |       </div>
 820 |     </div><!-- /stage-data-strip -->
 821 | 
 822 |     <!-- TIMED BRIEFING + INTERACTIVE -->
 823 |     <div class="stage-below-strip">
 824 |       <!-- Timed Briefing Countdown -->
 825 |       <div>
 826 |         <div class="stage-brief__section-label">Timed Briefing</div>
 827 |         <div id="briefingCountdown" class="stage-brief-countdown">
 828 |           <div class="stage-brief-countdown__row">
 829 |             <div class="stage-brief-countdown__dot" id="briefDot"></div>
 830 |             <div class="stage-brief-countdown__label">NEXT BRIEFING</div>
 831 |           </div>
 832 |           <div class="stage-brief-countdown__timer" id="countdownTimer">&mdash;</div>
 833 |           <div class="stage-brief-countdown__sub" id="countdownSub">Checking schedule&hellip;</div>
 834 |           <button class="stage-btn stage-btn--primary stage-brief-countdown__play"
 835 |                   id="briefPlayBtn" style="display:none"
 836 |                   onclick="playLatestBrief()">&#9654; Play Brief</button>
 837 |         </div>
 838 |       </div>
 839 | 
 840 |       <!-- Mode switching -->
 841 |       <div>
 842 |         <div class="stage-brief__section-label">Stage Mode</div>
 843 |         <div id="stageModeBadge" class="stage-mode-badge broadcast">● ON AIR</div>
 844 |         <div class="stage-between-badge" id="betweenBadge" style="display:none">
 845 |           BETWEEN SEGMENTS — <span id="betweenCountdown">--:--</span> until next briefing
 846 |         </div>
 847 |       </div>
 848 | 
 849 |       <!-- Interactive Oracle Panel (visible between briefings) -->
 850 |       <div id="interactivePanel" class="stage-interactive-panel">
 851 |         <div style="font-family:var(--s-mono);font-size:9px;letter-spacing:.15em;color:var(--s-muted);text-transform:uppercase;margin-bottom:8px">Ask Oracle Anything</div>
 852 |         <div class="stage-chat-input">
 853 |           <input type="text" id="stageChatInput" placeholder="Ask about Bitcoin..."
 854 |                  onkeydown="if(event.key==='Enter')stageChat()">
 855 |           <button class="stage-mic-btn" id="stageMicBtn" onclick="toggleStageMic()" title="Tap to speak">&#127908;</button>
 856 |           <button class="stage-btn stage-btn--primary" onclick="stageChat()" style="padding:8px 14px">&#9654;</button>
 857 |         </div>
 858 |         <div class="stage-chat-history" id="stageChatHistory"></div>
 859 |       </div>
 860 |     </div><!-- /stage-below-strip -->
 861 | 
 862 |     <!-- PARTNER CHANNEL INTELLIGENCE -->
 863 |     <div class="stage-below-strip">
 864 |       <div class="stage-brief__section-label">Partner Channel Intelligence</div>
 865 |       <div class="stage-transcripts-wrap">
 866 |         <div class="stage-transcripts" id="transcriptsGrid">
 867 |           <!-- Skeleton loaders -->
 868 |           {% for i in range(6) %}
 869 |           <div class="stage-tx-card shimmer" style="height:140px;"></div>
 870 |           {% endfor %}
 871 |         </div>
 872 |       </div>
 873 |     </div>
 874 | 
 875 |     <!-- SIDEBAR: Price + Nostr (now full-width row) -->
 876 |     <div class="stage-sidebar">
 877 | 
 878 |       <!-- Price Panel -->
 879 |       <div class="stage-panel">
 880 |         <div class="stage-panel__header">
 881 |           <span><span class="stage-panel__header-dot" style="background:var(--s-gold)"></span>Bitcoin Price</span>
 882 |           <span id="priceUpdated" style="font-size:8px;color:rgba(255,255,255,.2)">live</span>
 883 |         </div>
 884 |         <div class="stage-panel__body">
 885 |           <div class="stage-price-big" id="sidebarPrice">—</div>
 886 |           <div class="stage-price-label">USD · Real-Time</div>
 887 |           <div class="stage-price-change" id="sidebarSentimentLine">—</div>
 888 |         </div>
 889 |       </div>
 890 | 
 891 |       <!-- Nostr Signal Panel -->
 892 |       <div class="stage-panel" style="overflow:hidden;display:flex;flex-direction:column;">
 893 |         <div class="stage-panel__header">
 894 |           <span><span class="stage-panel__header-dot" style="background:var(--s-red);animation:live-pulse 1.4s infinite"></span>Nostr Signal</span>
 895 |           <span id="nostrCount" style="font-size:8px;color:rgba(255,255,255,.3)">0 posts</span>
 896 |         </div>
 897 |         <div class="stage-panel__body stage-signal-feed" id="nostrFeed">
 898 |           <div style="font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0">
 899 |             Loading signal…
 900 |           </div>
 901 |         </div>
 902 |       </div>
 903 | 
 904 |     </div><!-- /stage-sidebar -->
 905 |   </div><!-- /stage-grid -->
 906 | </div><!-- /stage-wrap -->
 907 | 
 908 | <!-- Transcript Reader Overlay -->
 909 | <div class="stage-reader" id="stageReader">
 910 |   <div class="stage-reader__inner">
 911 |     <button class="stage-reader__close" onclick="closeReader()">
 912 |       ← Back to Stage
 913 |     </button>
 914 |     <div class="stage-reader__channel" id="readerChannel"></div>
 915 |     <div class="stage-reader__title" id="readerTitle"></div>
 916 |     <div class="stage-reader__body" id="readerBody"></div>
 917 |   </div>
 918 | </div>
 919 | 
 920 | <script>
 921 | (function(){
 922 |   'use strict';
 923 | 
 924 |   var AVATAR_BASE = 'https://avatar.protocolpulse.io';
 925 |   var busy = false;
 926 |   var objURL = null;
 927 |   var vid = document.getElementById('avatarVid');
 928 |   var still = document.getElementById('avatarStill');
 929 |   var briefBtn = document.getElementById('briefBtn');
 930 |   var greetBtn = document.getElementById('greetBtn');
 931 |   var statusEl = document.getElementById('stageStatus');
 932 |   var badgeEl  = document.getElementById('avatarStatusBadge');
 933 | 
 934 |   // ── CLOCK ────────────────────────────────────────────
 935 |   function tick(){
 936 |     var now = new Date();
 937 |     document.getElementById('stageTime').textContent =
 938 |       now.toUTCString().slice(17,22) + ' UTC';
 939 |   }
 940 |   tick(); setInterval(tick, 1000);
 941 | 
 942 |   // ── FETCH INTEL ───────────────────────────────────────
 943 |   function loadIntel(){
 944 |     fetch('/api/stage/intel')
 945 |     .then(function(r){ return r.json(); })
 946 |     .then(function(d){
 947 |       // price
 948 |       var price = d.price || '';
 949 |       updatePrice(price, d.price_float);
 950 |       // sentiment
 951 |       var score = d.sentiment_score || 50;
 952 |       var label = d.sentiment_label || 'neutral';
 953 |       document.getElementById('sentimentScore').textContent = score;
 954 |       document.getElementById('sentimentLabel').textContent = label.toUpperCase();
 955 |       document.getElementById('sentimentBar').style.width = score + '%';
 956 |       var sentColor = score > 60 ? 'var(--s-green)' : score < 40 ? 'var(--s-red)' : 'var(--s-gold)';
 957 |       document.getElementById('sentimentScore').style.color = sentColor;
 958 |       document.getElementById('sentimentLabel').style.color = sentColor;
 959 |       // ticker
 960 |       document.getElementById('tickerPrice').textContent = price;
 961 |       document.getElementById('tickerPrice2').textContent = price;
 962 |       document.getElementById('tickerSentiment').textContent = label.toUpperCase() + ' ' + score + '/100';
 963 |       document.getElementById('tickerSentiment2').textContent = label.toUpperCase() + ' ' + score + '/100';
 964 |       // sidebar sentiment line
 965 |       document.getElementById('sidebarSentimentLine').innerHTML =
 966 |         '<span style="color:'+sentColor+';font-family:var(--s-mono);font-size:11px">' +
 967 |         label.toUpperCase() + ' — ' + score + '/100</span>';
 968 |       // narrative
 969 |       if(d.narrative){
 970 |         document.getElementById('narrativeText').textContent = d.narrative;
 971 |       }
 972 |       // topics
 973 |       if(d.topics){
 974 |         renderTopics(d.topics);
 975 |         var topicsText = d.topics.replace(/\([^)]+\)/g,'').replace(/,/g,' ·');
 976 |         document.getElementById('tickerTopics').textContent = topicsText;
 977 |         document.getElementById('tickerTopics2').textContent = topicsText;
 978 |       }
 979 |     })
 980 |     .catch(function(){
 981 |       document.getElementById('narrativeText').textContent = 'Intel feed offline — retrying in 60s';
 982 |       document.getElementById('tickerOracle').textContent = 'Offline';
 983 |       setTimeout(loadIntel, 60000);
 984 |     });
 985 |   }
 986 | 
 987 |   function updatePrice(priceStr, priceFloat){
 988 |     if(!priceStr) return;
 989 |     var fmt = priceFloat ? '$' + Number(priceFloat).toLocaleString('en-US',{maximumFractionDigits:0}) : priceStr;
 990 |     document.getElementById('sidebarPrice').textContent = fmt;
 991 |     document.getElementById('tickerPrice').textContent = fmt;
 992 |     document.getElementById('tickerPrice2').textContent = fmt;
 993 |     document.getElementById('priceUpdated').textContent = new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
 994 |   }
 995 | 
 996 |   function renderTopics(topicsStr){
 997 |     var wrap = document.getElementById('topicsWrap');
 998 |     wrap.innerHTML = '';
 999 |     var parts = topicsStr.split(',');
1000 |     parts.forEach(function(t){
1001 |       t = t.trim();
1002 |       var cls = 'stage-topic--neut';
1003 |       if(t.indexOf('(bullish)')>=0 || t.indexOf('bullish')>=0) cls = 'stage-topic--bull';
1004 |       if(t.indexOf('(bearish)')>=0 || t.indexOf('bearish')>=0) cls = 'stage-topic--bear';
1005 |       var label = t.replace(/\s*\([^)]+\)\s*/g,'').trim();
1006 |       var span = document.createElement('span');
1007 |       span.className = 'stage-topic ' + cls;
1008 |       span.textContent = label;
1009 |       wrap.appendChild(span);
1010 |     });
1011 |   }
1012 | 
1013 |   // ── LOAD TRANSCRIPTS ──────────────────────────────────
1014 |   function loadTranscripts(){
1015 |     fetch('/api/stage/transcripts')
1016 |     .then(function(r){ return r.json(); })
1017 |     .then(function(data){
1018 |       renderTranscripts(data);
1019 |     })
1020 |     .catch(function(){
1021 |       // Fallback: show placeholder cards
1022 |       renderTranscripts([]);
1023 |     });
1024 |   }
1025 | 
1026 |   function renderTranscripts(items){
1027 |     var grid = document.getElementById('transcriptsGrid');
1028 |     if(!items || !items.length){
1029 |       grid.innerHTML = '<div style="grid-column:1/-1;font-family:var(--s-mono);font-size:11px;color:var(--s-muted);padding:20px 0">No transcript data available yet. Channel scan in progress.</div>';
1030 |       return;
1031 |     }
1032 |     grid.innerHTML = '';
1033 |     items.forEach(function(item){
1034 |       var sentCls = 'stage-topic--neut';
1035 |       var sentLabel = item.sentiment || 'neutral';
1036 |       if(sentLabel === 'bullish') sentCls = 'stage-topic--bull';
1037 |       if(sentLabel === 'bearish') sentCls = 'stage-topic--bear';
1038 |       var card = document.createElement('div');
1039 |       card.className = 'stage-tx-card';
1040 |       card.innerHTML = [
1041 |         '<div class="stage-tx-card__channel">' + esc(item.channel||'Unknown') + '</div>',
1042 |         '<div class="stage-tx-card__title">' + esc((item.title||'').slice(0,70)) + '</div>',
1043 |         '<div class="stage-tx-card__excerpt">' + esc((item.excerpt||item.transcript_snippet||'').slice(0,120)) + '…</div>',
1044 |         '<div class="stage-tx-card__footer">',
1045 |           '<button class="stage-tx-card__read-btn" onclick="openReader(this)">Read Brief →</button>',
1046 |           '<span class="stage-topic ' + sentCls + '">' + esc(sentLabel) + '</span>',
1047 |         '</div>',
1048 |       ].join('');
1049 |       // Store full data on card
1050 |       card.dataset.channel  = item.channel || '';
1051 |       card.dataset.title    = item.title   || '';
1052 |       card.dataset.body     = item.transcript_text || item.excerpt || '';
1053 |       grid.appendChild(card);
1054 |     });
1055 |   }
1056 | 
1057 |   function esc(s){
1058 |     return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
1059 |   }
1060 | 
1061 |   // ── NOSTR SIGNAL ──────────────────────────────────────
1062 |   function loadNostr(){
1063 |     fetch('/api/stage/signal')
1064 |     .then(function(r){ return r.json(); })
1065 |     .then(function(d){
1066 |       var posts = d.nostr_posts || [];
1067 |       renderNostr(posts);
1068 |     })
1069 |     .catch(function(){
1070 |       renderNostr([]);
1071 |       document.getElementById('nostrCount').textContent = 'offline';
1072 |     });
1073 |   }
1074 | 
1075 |   function renderNostr(posts){
1076 |     var feed = document.getElementById('nostrFeed');
1077 |     document.getElementById('nostrCount').textContent = posts.length + ' posts';
1078 |     if(!posts.length){
1079 |       feed.innerHTML = '<div style="font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0">No signal yet — relay scanning…</div>';
1080 |       return;
1081 |     }
1082 |     feed.innerHTML = '';
1083 |     posts.slice(0,12).forEach(function(p){
1084 |       var item = document.createElement('div');
1085 |       item.className = 'stage-signal-item';
1086 |       var author = p.nip05 || p.display_name || 'anon';
1087 |       // textContent prevents XSS from user-controlled Nostr content
1088 |       var aDiv = document.createElement('div');
1089 |       aDiv.className = 'stage-signal-item__author';
1090 |       aDiv.textContent = author.slice(0,50);
1091 |       var tDiv = document.createElement('div');
1092 |       tDiv.className = 'stage-signal-item__text';
1093 |       tDiv.textContent = (p.text||'').slice(0,180);
1094 |       item.appendChild(aDiv);
1095 |       item.appendChild(tDiv);
1096 |       feed.appendChild(item);
1097 |     });
1098 |   }
1099 | 
1100 |   // ── TRANSCRIPT READER ─────────────────────────────────
1101 |   window.openReader = function(btn){
1102 |     var card = btn.closest('.stage-tx-card');
1103 |     document.getElementById('readerChannel').textContent = card.dataset.channel;
1104 |     document.getElementById('readerTitle').textContent   = card.dataset.title;
1105 |     document.getElementById('readerBody').textContent    = card.dataset.body || 'Full transcript not available.';
1106 |     document.getElementById('stageReader').classList.add('open');
1107 |     document.body.style.overflow = 'hidden';
1108 |   };
1109 |   window.closeReader = function(){
1110 |     document.getElementById('stageReader').classList.remove('open');
1111 |     document.body.style.overflow = '';
1112 |   };
1113 | 
1114 |   // ── AVATAR PLAYBACK ───────────────────────────────────
1115 |   function setStatus(msg, color, spin){
1116 |     statusEl.textContent = msg;
1117 |     statusEl.style.color = color || 'rgba(255,255,255,.3)';
1118 |     statusEl.className   = 'stage-status' + (msg==='Speaking' ? ' speaking' : '');
1119 |     tickerOracle(msg);
1120 |   }
1121 |   function tickerOracle(msg){
1122 |     document.getElementById('tickerOracle').textContent = msg;
1123 |   }
1124 |   function setBusy(b){
1125 |     busy = b;
1126 |     briefBtn.disabled = b;
1127 |     greetBtn.disabled = b;
1128 |     badgeEl.textContent = b ? '● Rendering…' : '● Avatar Ready';
1129 |     badgeEl.style.color = b ? 'var(--s-gold)' : 'var(--s-green)';
1130 |     badgeEl.style.borderColor = b ? 'rgba(248,193,92,.3)' : 'rgba(46,255,138,.2)';
1131 |     badgeEl.style.background  = b ? 'rgba(248,193,92,.08)' : 'rgba(46,255,138,.08)';
1132 |   }
1133 | 
1134 |   function playVid(url){
1135 |     return new Promise(function(resolve){
1136 |       if(objURL){ try{ URL.revokeObjectURL(objURL); }catch(e){} objURL = null; }
1137 |       objURL = url;
1138 |       vid.src = url;
1139 |       vid.muted = true;
1140 |       vid.volume = 1.0;
1141 |       still.style.opacity = '0';
1142 |       vid.classList.add('active');
1143 |       setStatus('Speaking','var(--s-green)');
1144 |       var unmuted = false;
1145 |       function tryUnmute(){ if(unmuted) return; unmuted=true; vid.muted=false; vid.volume=1.0; }
1146 |       vid.addEventListener('canplay', function oncp(){ vid.removeEventListener('canplay',oncp); tryUnmute(); }, {once:true});
1147 |       vid.onended = function(){
1148 |         vid.classList.remove('active');
1149 |         still.style.opacity = '1';
1150 |         setStatus('Ready','rgba(255,255,255,.3)');
1151 |         resolve();
1152 |       };
1153 |       vid.onerror = function(){ vid.classList.remove('active'); still.style.opacity='1'; resolve(); };
1154 |       var p = vid.play();
1155 |       if(p){ p.then(function(){ setTimeout(tryUnmute,50); }).catch(function(){
1156 |         setStatus('Tap to play','var(--s-gold)');
1157 |         vid.addEventListener('click', function(){ vid.muted=false; vid.play(); }, {once:true});
1158 |       }); }
1159 |     });
1160 |   }
1161 | 
1162 |   function fetchTO(url, opts, ms){
1163 |     var ctrl = new AbortController();
1164 |     var id = setTimeout(function(){ ctrl.abort(); }, ms||30000);
1165 |     var o = opts||{}; o.signal = ctrl.signal;
1166 |     return fetch(url, o).finally(function(){ clearTimeout(id); });
1167 |   }
1168 | 
1169 |   var _briefCooldown = 0;
1170 |   window.requestBrief = function(){
1171 |     if(busy) return;
1172 |     var now = Date.now();
1173 |     if(now - _briefCooldown < 10000){ setStatus('Please wait…','var(--s-gold)'); return; }
1174 |     _briefCooldown = now;
1175 |     setBusy(true); setStatus('Fetching brief…','var(--s-gold)');
1176 |     fetchTO(AVATAR_BASE + '/oracle/speak',{
1177 |       method:'POST', headers:{'Content-Type':'application/json'},
1178 |       body: JSON.stringify({intent:'DAILY_BRIEF'})
1179 |     }, 60000)
1180 |     .then(function(r){
1181 |       if(!r.ok) throw new Error('HTTP '+r.status);
1182 |       return r.blob().then(function(b){
1183 |         return URL.createObjectURL(b);
1184 |       });
1185 |     })
1186 |     .then(function(url){ return playVid(url); })
1187 |     .catch(function(e){
1188 |       setStatus('Error — try again','var(--s-red)');
1189 |       console.error(e);
1190 |     })
1191 |     .finally(function(){ setBusy(false); });
1192 |   };
1193 | 
1194 |   var _greetCooldown = 0;
1195 |   window.requestGreet = function(){
1196 |     if(busy) return;
1197 |     var now = Date.now();
1198 |     if(now - _greetCooldown < 5000){ return; }
1199 |     _greetCooldown = now;
1200 |     setBusy(true); setStatus('Loading…','var(--s-gold)');
1201 |     fetchTO(AVATAR_BASE + '/oracle/response/GREETING',{},15000)
1202 |     .then(function(r){
1203 |       if(!r.ok) throw new Error('HTTP '+r.status);
1204 |       return r.blob().then(function(b){ return URL.createObjectURL(b); });
1205 |     })
1206 |     .then(function(url){ return playVid(url); })
1207 |     .catch(function(e){ setStatus('Error','var(--s-red)'); console.error(e); })
1208 |     .finally(function(){ setBusy(false); });
1209 |   };
1210 | 
1211 |   // Auto-play greeting on load
1212 |   setTimeout(function(){
1213 |     requestGreet();
1214 |   }, 800);
1215 | 
1216 |   // ── STAGE MODE: BROADCAST vs INTERACTIVE ──────────────
1217 |   var STAGE_MODE = 'interactive'; // 'broadcast' | 'interactive'
1218 |   var _stageSessionId = 'stage_' + Date.now() + '_' + Math.random().toString(36).slice(2,8);
1219 |   var _stageRecognition = null;
1220 |   var _stageIsRec = false;
1221 | 
1222 |   function enterBroadcast(briefUrl) {
1223 |     STAGE_MODE = 'broadcast';
1224 |     var badge = document.getElementById('stageModeBadge');
1225 |     badge.textContent = '● ON AIR';
1226 |     badge.className = 'stage-mode-badge broadcast';
1227 |     document.getElementById('interactivePanel').classList.remove('active');
1228 |     document.getElementById('betweenBadge').style.display = 'none';
1229 |     // Disable mic during broadcast
1230 |     var micBtn = document.getElementById('stageMicBtn');
1231 |     if(micBtn) micBtn.disabled = true;
1232 |     if(briefUrl) {
1233 |       setBusy(true);
1234 |       setStatus('Playing brief\u2026','var(--s-gold)');
1235 |       playVid(briefUrl).then(function(){
1236 |         enterInteractive();
1237 |         loadBriefingSchedule();
1238 |       }).finally(function(){ setBusy(false); });
1239 |     }
1240 |   }
1241 | 
1242 |   function enterInteractive() {
1243 |     STAGE_MODE = 'interactive';
1244 |     var badge = document.getElementById('stageModeBadge');
1245 |     badge.textContent = 'Ask Oracle anything';
1246 |     badge.className = 'stage-mode-badge interactive';
1247 |     document.getElementById('interactivePanel').classList.add('active');
1248 |     document.getElementById('betweenBadge').style.display = 'block';
1249 |     // Enable mic
1250 |     var micBtn = document.getElementById('stageMicBtn');
1251 |     if(micBtn) micBtn.disabled = false;
1252 |     // Pulse mic hint after 1s
1253 |     setTimeout(pulseStageMic, 1000);
1254 |   }
1255 | 
1256 |   function pulseStageMic() {
1257 |     var micBtn = document.getElementById('stageMicBtn');
1258 |     if(!micBtn || micBtn.disabled || _stageIsRec) return;
1259 |     micBtn.style.boxShadow = '0 0 0 8px rgba(255,59,95,.2)';
1260 |     setTimeout(function(){ micBtn.style.boxShadow = ''; }, 2000);
1261 |   }
1262 | 
1263 |   // ── STAGE CHAT (Oracle dialogue) ────────────────────────
1264 |   window.stageChat = function() {
1265 |     var input = document.getElementById('stageChatInput');
1266 |     var text = (input.value || '').trim();
1267 |     if(!text || busy) return;
1268 |     input.value = '';
1269 |     _appendChatMsg('You: ' + text, 'user');
1270 |     setBusy(true);
1271 |     setStatus('Oracle thinking\u2026','var(--s-gold)');
1272 | 
1273 |     fetchTO(AVATAR_BASE + '/oracle/chat', {
1274 |       method: 'POST',
1275 |       headers: {'Content-Type':'application/json'},
1276 |       body: JSON.stringify({text:text, session_id:_stageSessionId, audio_first:true, avatar_source:"stage_hologram"})
1277 |     }, 90000)
1278 |     .then(function(r){
1279 |       if(!r.ok) throw new Error('HTTP '+r.status);
1280 |       var ct = r.headers.get('content-type') || '';
1281 |       if(ct.indexOf('video') >= 0){
1282 |         return r.blob().then(function(b){ return URL.createObjectURL(b); })
1283 |           .then(function(url){ return playVid(url); });
1284 |       }
1285 |       return r.json().then(function(j){
1286 |         _appendChatMsg('Oracle: ' + j.text, 'oracle');
1287 |         if(j.job_id) {
1288 |           // Poll for video
1289 |           var polls = 0;
1290 |           var pollId = setInterval(function(){
1291 |             polls++;
1292 |             if(polls > 45){ clearInterval(pollId); setBusy(false); return; }
1293 |             fetch(AVATAR_BASE + '/oracle/job/' + j.job_id)
1294 |               .then(function(vr){ if(vr.ok) return vr.blob(); return null; })
1295 |               .then(function(vb){
1296 |                 if(vb){
1297 |                   clearInterval(pollId);
1298 |                   playVid(URL.createObjectURL(vb));
1299 |                 }
1300 |               }).catch(function(){});
1301 |           }, 1000);
1302 |         }
1303 |       });
1304 |     })
1305 |     .catch(function(e){
1306 |       _appendChatMsg('Oracle: Connection error — try again.', 'oracle');
1307 |       console.error('stage chat error:', e);
1308 |     })
1309 |     .finally(function(){ setBusy(false); });
1310 |   };
1311 | 
1312 |   function _appendChatMsg(text, role) {
1313 |     var hist = document.getElementById('stageChatHistory');
1314 |     var div = document.createElement('div');
1315 |     div.className = 'stage-chat-msg ' + role;
1316 |     div.textContent = text;
1317 |     hist.appendChild(div);
1318 |     hist.scrollTop = hist.scrollHeight;
1319 |   }
1320 | 
1321 |   // ── STAGE MIC (speech recognition) ──────────────────────
1322 |   window.toggleStageMic = function() {
1323 |     if(_stageIsRec) { _stopStageMic(); return; }
1324 |     if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
1325 |       _appendChatMsg('Speech recognition not supported in this browser.', 'oracle');
1326 |       return;
1327 |     }
1328 |     var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
1329 |     _stageRecognition = new SR();
1330 |     _stageRecognition.lang = 'en-US';
1331 |     _stageRecognition.continuous = false;
1332 |     _stageRecognition.interimResults = false;
1333 |     _stageRecognition.onresult = function(e) {
1334 |       var text = e.results[0][0].transcript;
1335 |       document.getElementById('stageChatInput').value = text;
1336 |       _stopStageMic();
1337 |       stageChat();
1338 |     };
1339 |     _stageRecognition.onerror = function() { _stopStageMic(); };
1340 |     _stageRecognition.onend = function() { _stopStageMic(); };
1341 |     _stageRecognition.start();
1342 |     _stageIsRec = true;
1343 |     document.getElementById('stageMicBtn').classList.add('recording');
1344 |   };
1345 | 
1346 |   function _stopStageMic() {
1347 |     _stageIsRec = false;
1348 |     if(_stageRecognition) { try{_stageRecognition.stop();}catch(e){} _stageRecognition = null; }
1349 |     document.getElementById('stageMicBtn').classList.remove('recording');
1350 |   }
1351 | 
1352 |   // ── BRIEFING COUNTDOWN ──────────────────────────────
1353 |   var _briefCountdownId = null;
1354 |   var _latestBriefUrl = null;
1355 |   var _hasUserInteracted = false;
1356 |   var _countdownRemaining = 0;
1357 | 
1358 |   document.addEventListener('click', function(){ _hasUserInteracted = true; }, {once:true});
1359 | 
1360 |   function loadBriefingSchedule(){
1361 |     fetch('/api/stage/next_briefing')
1362 |     .then(function(r){ return r.json(); })
1363 |     .then(function(d){
1364 |       if(!d.has_brief){
1365 |         document.getElementById('countdownTimer').textContent = '\u2014';
1366 |         document.getElementById('countdownSub').textContent = 'First brief coming soon';
1367 |         enterInteractive();
1368 |         return;
1369 |       }
1370 |       _latestBriefUrl = d.last_brief.mp4_url;
1371 |       if(d.countdown_seconds <= 0){
1372 |         showBriefReady(d.last_brief);
1373 |       } else {
1374 |         startCountdown(d.countdown_seconds, d.last_brief);
1375 |         // Between briefings = interactive mode
1376 |         if(STAGE_MODE !== 'broadcast') enterInteractive();
1377 |       }
1378 |     })
1379 |     .catch(function(){
1380 |       document.getElementById('countdownSub').textContent = 'Schedule unavailable';
1381 |       enterInteractive();
1382 |     });
1383 |   }
1384 | 
1385 |   function startCountdown(seconds, lastBrief){
1386 |     if(_briefCountdownId) clearInterval(_briefCountdownId);
1387 |     _countdownRemaining = seconds;
1388 |     var timerEl = document.getElementById('countdownTimer');
1389 |     var subEl = document.getElementById('countdownSub');
1390 |     var dotEl = document.getElementById('briefDot');
1391 |     var playBtn = document.getElementById('briefPlayBtn');
1392 | 
1393 |     dotEl.classList.remove('ready');
1394 |     timerEl.classList.remove('ready');
1395 |     playBtn.style.display = 'none';
1396 | 
1397 |     subEl.textContent = lastBrief.title || 'Last brief loaded';
1398 | 
1399 |     function update(){
1400 |       if(_countdownRemaining <= 0){
1401 |         clearInterval(_briefCountdownId);
1402 |         showBriefReady(lastBrief);
1403 |         return;
1404 |       }
1405 |       var h = Math.floor(_countdownRemaining / 3600);
1406 |       var m = Math.floor((_countdownRemaining % 3600) / 60);
1407 |       var s = _countdownRemaining % 60;
1408 |       timerEl.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
1409 |       // Update between-segments badge
1410 |       var bb = document.getElementById('betweenCountdown');
1411 |       if(bb) bb.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
1412 |       _countdownRemaining--;
1413 |     }
1414 |     update();
1415 |     _briefCountdownId = setInterval(update, 1000);
1416 |   }
1417 | 
1418 |   function pad(n){ return n < 10 ? '0'+n : ''+n; }
1419 | 
1420 |   function showBriefReady(brief){
1421 |     var timerEl = document.getElementById('countdownTimer');
1422 |     var subEl = document.getElementById('countdownSub');
1423 |     var dotEl = document.getElementById('briefDot');
1424 |     var playBtn = document.getElementById('briefPlayBtn');
1425 | 
1426 |     timerEl.textContent = 'NEW BRIEF';
1427 |     timerEl.classList.add('ready');
1428 |     dotEl.classList.add('ready');
1429 |     subEl.textContent = brief.title || 'Ready to play';
1430 |     playBtn.style.display = 'block';
1431 |     _latestBriefUrl = brief.mp4_url;
1432 | 
1433 |     // Auto-transition to broadcast when countdown hits 0
1434 |     if(_hasUserInteracted && !busy){
1435 |       enterBroadcast(_latestBriefUrl);
1436 |     }
1437 |   }
1438 | 
1439 |   window.playLatestBrief = function(){
1440 |     if(!_latestBriefUrl || busy) return;
1441 |     enterBroadcast(_latestBriefUrl);
1442 |   };
1443 | 
1444 |   // ── INIT DATA ─────────────────────────────────────────
1445 |   loadIntel();
1446 |   loadTranscripts();
1447 |   loadNostr();
1448 |   loadBriefingSchedule();
1449 | 
1450 |   // Refresh intel every 3 minutes
1451 |   setInterval(loadIntel, 180000);
1452 | 
1453 |   // Scroll-hint dots for mobile transcript carousel
1454 |   function initTxDots(){
1455 |     var grid = document.getElementById('transcriptsGrid');
1456 |     var dotsEl = document.getElementById('txDots');
1457 |     if(!grid||!dotsEl) return;
1458 |     var cards = grid.children;
1459 |     if(!cards.length) return;
1460 |     // Only show on mobile
1461 |     if(window.innerWidth > 640){ dotsEl.style.display='none'; return; }
1462 |     dotsEl.innerHTML = '';
1463 |     var n = Math.min(cards.length, 8);
1464 |     for(var i=0;i<n;i++){
1465 |       var dot = document.createElement('span');
1466 |       if(i===0) dot.className='active';
1467 |       dotsEl.appendChild(dot);
1468 |     }
1469 |     grid.addEventListener('scroll', function(){
1470 |       var idx = Math.round(grid.scrollLeft / (grid.scrollWidth / n));
1471 |       var dots = dotsEl.children;
1472 |       for(var j=0;j<dots.length;j++) dots[j].className = j===idx?'active':'';
1473 |     }, {passive:true});
1474 |   }
1475 |   // Init dots after transcripts load
1476 |   var _origRender = window.renderTranscripts;
1477 |   if(typeof renderTranscripts === 'function'){
1478 |     var _origRT = renderTranscripts;
1479 |     window.renderTranscripts = function(items){ _origRT(items); setTimeout(initTxDots,100); };
1480 |   } else { setTimeout(initTxDots,2000); }
1481 |   // Refresh Nostr every 2 minutes
1482 |   setInterval(loadNostr, 120000);
1483 |   // Refresh briefing schedule every 5 minutes
1484 |   setInterval(loadBriefingSchedule, 300000);
1485 | 
1486 |   // Prevent iOS pinch-to-zoom
1487 |   document.addEventListener('gesturestart', function(e){ e.preventDefault(); }, {passive:false});
1488 |   document.addEventListener('touchmove', function(e){ if(e.touches.length>1) e.preventDefault(); }, {passive:false});
1489 | 
1490 | })();
1491 | </script>
1492 | {% endblock %}
1493 | 
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
