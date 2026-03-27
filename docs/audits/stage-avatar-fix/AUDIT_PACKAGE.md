# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: stage-avatar-fix
# Branch: main
# Generated: 2026-03-24 15:13 UTC
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

### File: templates/stage.html (2348 lines)
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
  39 |   padding: 0 0 80px;
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
  79 | @media (max-width: 768px) {
  80 |   .stage-topbar__ticker-inner {
  81 |     animation-duration: 90s;
  82 |   }
  83 | }
  84 | @keyframes ticker-scroll {
  85 |   0%   { transform: translateX(0); }
  86 |   100% { transform: translateX(-50%); }
  87 | }
  88 | .ticker-item {
  89 |   font-family: var(--s-mono); font-size: 11px;
  90 |   color: rgba(255,255,255,.5); letter-spacing: .06em;
  91 | }
  92 | .ticker-item .ti-label { color: var(--s-muted); margin-right: 6px; }
  93 | .ticker-item .ti-val   { color: rgba(255,255,255,.85); }
  94 | .ticker-item .ti-up    { color: var(--s-green); }
  95 | .ticker-item .ti-down  { color: var(--s-red); }
  96 | .ticker-item .ti-sep   { color: var(--s-border); margin: 0 8px; }
  97 | .stage-topbar__time {
  98 |   font-family: var(--s-mono); font-size: 11px;
  99 |   color: var(--s-gold); letter-spacing: .1em;
 100 |   padding: 0 20px; border-left: 1px solid var(--s-border);
 101 |   flex-shrink: 0;
 102 | }
 103 | 
 104 | /* ── PAGE HEADER ──────────────────────────────────────  */
 105 | .stage-header {
 106 |   display: flex; align-items: center; justify-content: space-between;
 107 |   padding: 28px 32px 20px;
 108 |   border-bottom: 1px solid var(--s-border);
 109 | }
 110 | .stage-header__title {
 111 |   font-family: var(--s-head); font-size: 11px; font-weight: 700;
 112 |   letter-spacing: .3em; text-transform: uppercase;
 113 |   color: var(--s-red);
 114 | }
 115 | .stage-header__sub {
 116 |   font-family: var(--s-mono); font-size: 10px;
 117 |   color: rgba(255,255,255,.3); letter-spacing: .12em;
 118 |   margin-top: 3px;
 119 | }
 120 | .stage-header__right {
 121 |   display: flex; align-items: center; gap: 12px;
 122 | }
 123 | .stage-badge {
 124 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 125 |   padding: 4px 10px; border-radius: 3px;
 126 |   text-transform: uppercase;
 127 | }
 128 | .stage-badge--on  { background: rgba(255,59,95,.12); color: var(--s-red); border: 1px solid rgba(255,59,95,.3); }
 129 | .stage-badge--ok  { background: rgba(46,255,138,.08); color: var(--s-green); border: 1px solid rgba(46,255,138,.2); }
 130 | 
 131 | /* ── MAIN GRID ──────────────────────────────────────── */
 132 | .stage-grid {
 133 |   display: flex;
 134 |   flex-direction: column;
 135 |   align-items: center;
 136 |   gap: 0;
 137 |   max-width: 1400px;
 138 |   margin: 0 auto;
 139 |   padding: 0 24px;
 140 | }
 141 | 
 142 | /* ── MAIN CONTENT (centered) ────────────────────────── */
 143 | .stage-main {
 144 |   width: 100%;
 145 |   display: flex;
 146 |   flex-direction: column;
 147 |   align-items: center;
 148 |   padding: 24px 0 0;
 149 | }
 150 | 
 151 | /* ── AVATAR DESK ─────────────────────────────────────── */
 152 | .stage-desk {
 153 |   width: 60vw;
 154 |   max-width: 900px;
 155 |   min-width: 320px;
 156 |   margin: 0 auto;
 157 |   position: relative;
 158 | }
 159 | @media (max-width: 768px) {
 160 |   .stage-desk { width: 100%; max-width: 100%; }
 161 | }
 162 | .stage-avatar-wrap {
 163 |   width: 100%;
 164 |   position: relative;
 165 |   background: radial-gradient(circle at 50% 100%, rgba(255,59,95,.08) 0%, transparent 60%),
 166 |               #06080f url('/static/img/oracle_avatar_static.png') center top / cover no-repeat;
 167 |   border: 1px solid rgba(0, 255, 200, 0.15);
 168 |   border-radius: 8px;
 169 |   overflow: hidden;
 170 |   aspect-ratio: 3/4;
 171 |   display: flex; align-items: flex-end; justify-content: center;
 172 |   box-shadow: 0 0 40px rgba(220,38,38,0.2), 0 0 80px rgba(220,38,38,0.06);
 173 | }
 174 | .stage-avatar-wrap::before {
 175 |   content: '';
 176 |   position: absolute; inset: 0;
 177 |   background: linear-gradient(to top, rgba(4,5,10,.8) 0%, transparent 40%);
 178 |   z-index: 2; pointer-events: none;
 179 | }
 180 | /* Desk surface */
 181 | .stage-avatar-wrap::after {
 182 |   content: '';
 183 |   position: absolute; bottom: 0; left: 0; right: 0; height: 28%;
 184 |   background: linear-gradient(to top, #0d1017 0%, rgba(13,16,23,.5) 70%, transparent 100%);
 185 |   z-index: 3; pointer-events: none;
 186 | }
 187 | .stage-avatar-vid {
 188 |   position: absolute; inset: 0; width: 100%; height: 100%;
 189 |   object-fit: cover; object-position: center top;
 190 |   display: block; z-index: 1;
 191 | }
 192 | .stage-avatar-nameplate {
 193 |   position: absolute; bottom: 12px; left: 12px; z-index: 10;
 194 |   display: flex; align-items: center; gap: 8px;
 195 | }
 196 | .stage-avatar-nameplate__dot {
 197 |   width: 6px; height: 6px; border-radius: 50%;
 198 |   background: var(--s-red); box-shadow: 0 0 5px var(--s-red);
 199 |   animation: live-pulse 1.4s ease-in-out infinite;
 200 | }
 201 | .stage-avatar-nameplate__name {
 202 |   font-family: var(--s-mono); font-size: 11px; letter-spacing: .14em;
 203 |   color: rgba(255,255,255,.9); text-transform: uppercase;
 204 | }
 205 | 
 206 | /* ── BRIEF PANEL (right of avatar) ─────────────────── */
 207 | .stage-brief {
 208 |   display: flex; flex-direction: column; gap: 16px;
 209 | }
 210 | .stage-brief__section-label {
 211 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .22em;
 212 |   text-transform: uppercase; color: var(--s-muted);
 213 |   margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
 214 | }
 215 | .stage-brief__section-label::after {
 216 |   content: ''; flex: 1; height: 1px;
 217 |   background: linear-gradient(to right, var(--s-border), transparent);
 218 | }
 219 | .stage-brief__sentiment {
 220 |   display: flex; align-items: center; gap: 12px;
 221 |   padding: 14px 16px;
 222 |   background: var(--s-surface); border: 1px solid var(--s-border);
 223 |   border-radius: 6px;
 224 | }
 225 | .stage-brief__sentiment-bar-wrap {
 226 |   flex: 1; height: 4px; background: rgba(255,255,255,.08);
 227 |   border-radius: 2px; overflow: hidden;
 228 | }
 229 | .stage-brief__sentiment-bar {
 230 |   height: 100%; border-radius: 2px;
 231 |   background: linear-gradient(to right, var(--s-red), var(--s-gold), var(--s-green));
 232 |   transition: width .6s ease;
 233 | }
 234 | .stage-brief__sentiment-score {
 235 |   font-family: var(--s-mono); font-size: 22px; font-weight: 600;
 236 |   line-height: 1; color: #fff; min-width: 36px; text-align: right;
 237 | }
 238 | .stage-brief__sentiment-label {
 239 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .12em;
 240 |   text-transform: uppercase; margin-top: 2px;
 241 | }
 242 | 
 243 | /* Narrative card */
 244 | .stage-narrative {
 245 |   padding: 14px 16px;
 246 |   background: var(--s-surface); border: 1px solid var(--s-border);
 247 |   border-left: 3px solid var(--s-red); border-radius: 6px;
 248 |   font-family: var(--s-head); font-size: 14px; font-weight: 500;
 249 |   line-height: 1.5; color: rgba(255,255,255,.82);
 250 |   position: relative;
 251 | }
 252 | .stage-narrative::before {
 253 |   content: 'ORACLE NARRATIVE';
 254 |   font-family: var(--s-mono); font-size: 8px; letter-spacing: .22em;
 255 |   color: var(--s-red); display: block; margin-bottom: 6px;
 256 | }
 257 | 
 258 | /* Topics */
 259 | .stage-topics {
 260 |   display: flex; flex-wrap: wrap; gap: 6px;
 261 | }
 262 | .stage-topic {
 263 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 264 |   padding: 4px 10px; border-radius: 3px;
 265 |   text-transform: uppercase; border: 1px solid;
 266 | }
 267 | .stage-topic--bull  { background: rgba(46,255,138,.07);  color: var(--s-green); border-color: rgba(46,255,138,.2); }
 268 | .stage-topic--bear  { background: rgba(255,59,95,.07);   color: var(--s-red);   border-color: rgba(255,59,95,.2);  }
 269 | .stage-topic--neut  { background: rgba(248,193,92,.07);  color: var(--s-gold);  border-color: rgba(248,193,92,.2); }
 270 | 
 271 | /* Playback controls */
 272 | .stage-controls {
 273 |   display: flex; gap: 8px; align-items: center;
 274 | }
 275 | .stage-btn {
 276 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .12em;
 277 |   text-transform: uppercase; padding: 8px 16px;
 278 |   border-radius: 4px; cursor: pointer; border: 1px solid;
 279 |   transition: all .15s; flex-shrink: 0;
 280 | }
 281 | .stage-btn--primary {
 282 |   background: var(--s-red); color: #fff; border-color: var(--s-red);
 283 | }
 284 | .stage-btn--primary:hover { background: #ff1a40; }
 285 | .stage-btn--ghost {
 286 |   background: transparent; color: rgba(255,255,255,.6); border-color: var(--s-border);
 287 | }
 288 | .stage-btn--ghost:hover { border-color: rgba(255,255,255,.3); color: #fff; }
 289 | .stage-btn:disabled { opacity: .35; cursor: not-allowed; }
 290 | .stage-status {
 291 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 292 |   color: var(--s-muted); flex: 1; text-align: right;
 293 | }
 294 | .stage-status.speaking { color: var(--s-green); }
 295 | 
 296 | /* ── BRIEFING COUNTDOWN ──────────────────────────────  */
 297 | .stage-brief-countdown {
 298 |   background: var(--s-surface);
 299 |   border: 1px solid var(--s-border);
 300 |   border-radius: 8px;
 301 |   padding: 14px 16px;
 302 | }
 303 | .stage-brief-countdown__row {
 304 |   display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
 305 | }
 306 | .stage-brief-countdown__dot {
 307 |   width: 8px; height: 8px; border-radius: 50%;
 308 |   background: var(--s-muted); flex-shrink: 0;
 309 | }
 310 | .stage-brief-countdown__dot.ready {
 311 |   background: var(--s-red);
 312 |   animation: live-pulse 1.4s infinite;
 313 | }
 314 | .stage-brief-countdown__label {
 315 |   font-family: var(--s-mono); font-size: 9px;
 316 |   letter-spacing: .15em; color: var(--s-muted);
 317 | }
 318 | .stage-brief-countdown__timer {
 319 |   font-family: var(--s-mono); font-size: 28px;
 320 |   font-weight: 700; color: var(--s-gold);
 321 |   letter-spacing: .05em; line-height: 1.1;
 322 |   margin-bottom: 4px;
 323 | }
 324 | .stage-brief-countdown__timer.ready {
 325 |   color: var(--s-red);
 326 |   animation: brief-flash 2s ease-in-out infinite;
 327 | }
 328 | .stage-brief-countdown__sub {
 329 |   font-family: var(--s-mono); font-size: 10px;
 330 |   color: var(--s-muted); letter-spacing: .08em;
 331 | }
 332 | .stage-brief-countdown__play {
 333 |   margin-top: 10px; width: 100%;
 334 | }
 335 | @keyframes brief-flash {
 336 |   0%, 100% { opacity: 1; }
 337 |   50% { opacity: .6; }
 338 | }
 339 | 
 340 | /* ── CHANNEL TRANSCRIPTS ─────────────────────────────  */
 341 | .stage-transcripts {
 342 |   display: grid;
 343 |   grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
 344 |   gap: 12px;
 345 | }
 346 | /* Mobile: prevent iOS zoom + horizontal scroll carousel */
 347 | @media (max-width: 640px) {
 348 |   body { position: fixed; width: 100%; overflow: hidden; }
 349 |   .stage-wrap { overflow-y: auto; -webkit-overflow-scrolling: touch; height: 100vh; }
 350 |   .stage-transcripts {
 351 |     display: flex;
 352 |     flex-direction: row;
 353 |     overflow-x: auto;
 354 |     scroll-snap-type: x mandatory;
 355 |     -webkit-overflow-scrolling: touch;
 356 |     gap: 10px;
 357 |     padding-bottom: 12px;
 358 |     /* hide scrollbar but keep functionality */
 359 |     scrollbar-width: none;
 360 |   }
 361 |   .stage-transcripts::-webkit-scrollbar { display: none; }
 362 |   .stage-tx-card {
 363 |     flex: 0 0 82vw;          /* show ~1.1 cards at once = peek of next */
 364 |     max-width: 300px;
 365 |     scroll-snap-align: start;
 366 |     scroll-snap-stop: always;
 367 |   }
 368 |   /* Scroll hint dots */
 369 |   .stage-transcripts-wrap {
 370 |     position: relative;
 371 |   }
 372 |   .stage-tx-scroll-hint {
 373 |     display: flex;
 374 |     justify-content: center;
 375 |     gap: 5px;
 376 |     margin-top: 10px;
 377 |   }
 378 |   .stage-tx-scroll-hint span {
 379 |     width: 5px; height: 5px;
 380 |     border-radius: 50%;
 381 |     background: rgba(255,59,95,.25);
 382 |     transition: background .2s;
 383 |   }
 384 |   .stage-tx-scroll-hint span.active {
 385 |     background: var(--s-red);
 386 |   }
 387 |   /* Fade right edge to hint scrollability */
 388 |   .stage-brief__section-label + .stage-transcripts-wrap::after {
 389 |     content: '';
 390 |     position: absolute;
 391 |     right: 0; top: 0; bottom: 12px;
 392 |     width: 32px;
 393 |     background: linear-gradient(to right, transparent, var(--s-bg));
 394 |     pointer-events: none;
 395 |   }
 396 | }
 397 | .stage-tx-card {
 398 |   background: var(--s-surface);
 399 |   border: 1px solid var(--s-border);
 400 |   border-radius: 6px;
 401 |   padding: 14px 16px;
 402 |   transition: border-color .15s, transform .15s;
 403 |   cursor: default;
 404 | }
 405 | .stage-tx-card:hover {
 406 |   border-color: rgba(255,59,95,.35);
 407 |   transform: translateY(-1px);
 408 | }
 409 | .stage-tx-card__channel {
 410 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .18em;
 411 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 5px;
 412 | }
 413 | .stage-tx-card__title {
 414 |   font-family: var(--s-head); font-size: 13px; font-weight: 600;
 415 |   color: rgba(255,255,255,.9); line-height: 1.35; margin-bottom: 8px;
 416 | }
 417 | .stage-tx-card__excerpt {
 418 |   font-family: var(--s-head); font-size: 12px; font-weight: 400;
 419 |   color: rgba(255,255,255,.42); line-height: 1.5;
 420 | }
 421 | .stage-tx-card__footer {
 422 |   margin-top: 10px; padding-top: 8px;
 423 |   border-top: 1px solid rgba(255,255,255,.05);
 424 |   display: flex; justify-content: space-between; align-items: center;
 425 | }
 426 | .stage-tx-card__read-btn {
 427 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 428 |   text-transform: uppercase; color: var(--s-gold);
 429 |   background: none; border: none; cursor: pointer; padding: 0;
 430 |   transition: color .1s;
 431 | }
 432 | .stage-tx-card__read-btn:hover { color: #fff; }
 433 | .stage-tx-card__sentiment {
 434 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .08em;
 435 |   text-transform: uppercase;
 436 | }
 437 | 
 438 | /* ── SIDEBAR (now full-width below strip) ────────────  */
 439 | .stage-sidebar {
 440 |   width: 100%;
 441 |   max-width: 1100px;
 442 |   margin: 16px auto 0;
 443 |   display: grid;
 444 |   grid-template-columns: 1fr 1fr;
 445 |   gap: 16px;
 446 |   border-left: none;
 447 | }
 448 | @media (max-width: 768px) {
 449 |   .stage-sidebar { grid-template-columns: 1fr; }
 450 | }
 451 | .stage-panel {
 452 |   border-bottom: 1px solid var(--s-border);
 453 |   flex-shrink: 0;
 454 | }
 455 | .stage-panel__header {
 456 |   padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;
 457 |   background: rgba(8,11,18,.7);
 458 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 459 |   text-transform: uppercase; color: rgba(255,255,255,.4);
 460 | }
 461 | .stage-panel__header-dot {
 462 |   width: 5px; height: 5px; border-radius: 50%;
 463 |   margin-right: 7px; display: inline-block; vertical-align: middle;
 464 | }
 465 | .stage-panel__body { padding: 12px 16px; }
 466 | 
 467 | /* Price panel */
 468 | .stage-price-big {
 469 |   font-family: var(--s-head); font-size: 36px; font-weight: 800;
 470 |   color: #fff; line-height: 1; letter-spacing: -.02em;
 471 | }
 472 | .stage-price-label {
 473 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 474 |   color: var(--s-muted); margin-top: 4px; text-transform: uppercase;
 475 | }
 476 | .stage-price-change {
 477 |   font-family: var(--s-mono); font-size: 12px;
 478 |   margin-top: 8px;
 479 | }
 480 | 
 481 | /* Nostr feed */
 482 | .stage-signal-feed {
 483 |   overflow-y: auto;
 484 |   max-height: 380px;
 485 |   scrollbar-width: thin;
 486 |   scrollbar-color: rgba(255,59,95,.2) transparent;
 487 | }
 488 | .stage-signal-item {
 489 |   padding: 10px 0;
 490 |   border-bottom: 1px solid rgba(255,255,255,.04);
 491 | }
 492 | .stage-signal-item:last-child { border-bottom: none; }
 493 | .stage-signal-item__author {
 494 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 495 |   color: var(--s-gold); margin-bottom: 4px;
 496 |   white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
 497 | }
 498 | .stage-signal-item__text {
 499 |   font-family: var(--s-head); font-size: 12px;
 500 |   color: rgba(255,255,255,.6); line-height: 1.45;
 501 |   display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
 502 |   overflow: hidden;
 503 | }
 504 | 
 505 | /* Transcript reader overlay */
 506 | .stage-reader {
 507 |   display: none; position: fixed; inset: 0;
 508 |   z-index: 500; background: rgba(4,5,10,.95);
 509 |   backdrop-filter: blur(8px);
 510 |   overflow-y: auto;
 511 |   padding: 40px 24px;
 512 | }
 513 | .stage-reader.open { display: block; }
 514 | .stage-reader__inner {
 515 |   max-width: 680px; margin: 0 auto;
 516 |   background: var(--s-surface); border: 1px solid var(--s-border);
 517 |   border-radius: 8px; padding: 32px;
 518 | }
 519 | .stage-reader__close {
 520 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .14em;
 521 |   text-transform: uppercase; color: var(--s-muted);
 522 |   background: none; border: none; cursor: pointer;
 523 |   margin-bottom: 20px; display: flex; align-items: center; gap: 6px;
 524 |   transition: color .1s;
 525 | }
 526 | .stage-reader__close:hover { color: #fff; }
 527 | .stage-reader__channel {
 528 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 529 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 8px;
 530 | }
 531 | .stage-reader__title {
 532 |   font-family: var(--s-head); font-size: 22px; font-weight: 700;
 533 |   color: #fff; line-height: 1.3; margin-bottom: 16px;
 534 | }
 535 | .stage-reader__body {
 536 |   font-family: var(--s-head); font-size: 14px; font-weight: 400;
 537 |   color: rgba(255,255,255,.68); line-height: 1.7;
 538 |   white-space: pre-wrap; word-break: break-word;
 539 | }
 540 | 
 541 | /* ── INTERACTIVE MODE PANEL ─────────────────────────────  */
 542 | .stage-interactive-panel {
 543 |   display: none;
 544 |   background: var(--s-surface);
 545 |   border: 1px solid var(--s-border);
 546 |   border-radius: 8px;
 547 |   padding: 16px;
 548 |   margin-top: 12px;
 549 | }
 550 | .stage-interactive-panel.active { display: block; }
 551 | .stage-mode-badge {
 552 |   font-family: var(--s-mono); font-size: 11px; letter-spacing: .14em;
 553 |   text-transform: uppercase; padding: 5px 14px; border-radius: 4px;
 554 |   display: inline-flex; align-items: center; gap: 8px;
 555 |   transition: all .3s;
 556 | }
 557 | .stage-mode-badge.broadcast {
 558 |   background: rgba(255,59,95,.12); color: var(--s-red);
 559 |   border: 1px solid rgba(255,59,95,.3);
 560 | }
 561 | .stage-mode-badge.interactive {
 562 |   background: rgba(46,255,138,.08); color: var(--s-green);
 563 |   border: 1px solid rgba(46,255,138,.2);
 564 | }
 565 | .stage-chat-input {
 566 |   display: flex; gap: 8px; margin-top: 12px;
 567 | }
 568 | .stage-chat-input input {
 569 |   flex: 1; background: rgba(255,255,255,.05);
 570 |   border: 1px solid var(--s-border); border-radius: 4px;
 571 |   padding: 10px 14px; color: #fff;
 572 |   font-family: var(--s-head); font-size: 13px;
 573 |   outline: none; transition: border-color .15s;
 574 | }
 575 | .stage-chat-input input:focus {
 576 |   border-color: rgba(255,59,95,.5);
 577 | }
 578 | .stage-chat-input input::placeholder {
 579 |   color: rgba(255,255,255,.25);
 580 | }
 581 | .stage-mic-btn {
 582 |   width: 44px; height: 44px; border-radius: 50%;
 583 |   background: rgba(255,59,95,.12); border: 1px solid rgba(255,59,95,.3);
 584 |   color: var(--s-red); cursor: pointer;
 585 |   display: flex; align-items: center; justify-content: center;
 586 |   font-size: 18px; transition: all .15s; flex-shrink: 0;
 587 | }
 588 | .stage-mic-btn:hover { background: rgba(255,59,95,.2); }
 589 | .stage-mic-btn.recording {
 590 |   background: var(--s-red); color: #fff;
 591 |   animation: mic-pulse 1.4s infinite;
 592 | }
 593 | @keyframes floating-mic-pulse {
 594 |   0%   { box-shadow: 0 0 0 0 rgba(255,59,95,.6); }
 595 |   70%  { box-shadow: 0 0 0 18px rgba(255,59,95,0); }
 596 |   100% { box-shadow: 0 0 0 0 rgba(255,59,95,0); }
 597 | }
 598 | #floatingMicBtn.fmic-rec {
 599 |   background: rgba(255,59,95,.25) !important;
 600 |   border-color: #ff3b5f !important;
 601 |   animation: floating-mic-pulse 1s ease-out infinite;
 602 | }
 603 | @keyframes mic-pulse {
 604 |   0% { box-shadow: 0 0 0 0 rgba(255,59,95,.6); }
 605 |   70% { box-shadow: 0 0 0 16px rgba(255,59,95,0); }
 606 |   100% { box-shadow: 0 0 0 0 rgba(255,59,95,0); }
 607 | }
 608 | .stage-chat-history {
 609 |   max-height: 180px; overflow-y: auto; margin-top: 10px;
 610 |   scrollbar-width: thin; scrollbar-color: rgba(255,59,95,.2) transparent;
 611 | }
 612 | .stage-chat-msg {
 613 |   font-family: var(--s-head); font-size: 12px;
 614 |   line-height: 1.5; padding: 6px 0;
 615 |   border-bottom: 1px solid rgba(255,255,255,.04);
 616 | }
 617 | .stage-chat-msg.user { color: var(--s-gold); }
 618 | .stage-chat-msg.oracle { color: rgba(255,255,255,.7); }
 619 | .stage-between-badge {
 620 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 621 |   color: var(--s-muted); text-transform: uppercase;
 622 |   margin-top: 8px;
 623 | }
 624 | 
 625 | /* Animations */
 626 | @keyframes fadeUp {
 627 |   from { opacity:0; transform:translateY(12px); }
 628 |   to   { opacity:1; transform:translateY(0); }
 629 | }
 630 | .stage-desk     { animation: fadeUp .5s ease both; }
 631 | .stage-tx-card  { animation: fadeUp .5s ease both; }
 632 | .stage-tx-card:nth-child(2) { animation-delay: .05s; }
 633 | .stage-tx-card:nth-child(3) { animation-delay: .10s; }
 634 | .stage-tx-card:nth-child(4) { animation-delay: .15s; }
 635 | .stage-tx-card:nth-child(5) { animation-delay: .20s; }
 636 | .stage-tx-card:nth-child(6) { animation-delay: .25s; }
 637 | 
 638 | /* Loading shimmer */
 639 | .shimmer {
 640 |   background: linear-gradient(90deg, rgba(255,255,255,.04) 0%, rgba(255,255,255,.08) 50%, rgba(255,255,255,.04) 100%);
 641 |   background-size: 200% 100%;
 642 |   animation: shimmer 1.5s infinite;
 643 | }
 644 | @keyframes shimmer {
 645 |   0%   { background-position: -200% 0; }
 646 |   100% { background-position: 200% 0; }
 647 | }
 648 | 
 649 | /* ── DATA STRIP (below avatar) ────────────────────── */
 650 | .stage-data-strip {
 651 |   display: grid;
 652 |   grid-template-columns: 1fr 2fr 1fr;
 653 |   gap: 16px;
 654 |   width: 100%;
 655 |   max-width: 1100px;
 656 |   margin: 16px auto 0;
 657 |   padding: 0;
 658 | }
 659 | @media (max-width: 768px) {
 660 |   .stage-data-strip { grid-template-columns: 1fr; padding: 0; }
 661 | }
 662 | 
 663 | /* ── BELOW-STRIP SECTIONS (timed briefing, transcripts) ── */
 664 | .stage-below-strip {
 665 |   width: 100%;
 666 |   max-width: 1100px;
 667 |   margin: 16px auto 0;
 668 |   display: flex; flex-direction: column; gap: 16px;
 669 | }
 670 | 
 671 | /* ── STAGE WAKE READINESS ──────────────────────────── */
 672 | #stage-tap-label { transition: opacity 0.5s; }
 673 | .stage-wake-ready #stage-tap-label { animation: none; }
 674 | 
 675 | /* ── HOLOGRAM TREATMENT (stage avatar only) ─────────── */
 676 | /* (merged into .stage-avatar-wrap above) */
 677 | .stage-avatar-scanline {
 678 |   position: absolute; inset: 0;
 679 |   background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.06) 2px, rgba(0,0,0,0.06) 4px);
 680 |   pointer-events: none; z-index: 10;
 681 |   animation: scanline-drift 8s linear infinite;
 682 | }
 683 | @keyframes scanline-drift {
 684 |   from { background-position: 0 0; }
 685 |   to   { background-position: 0 100px; }
 686 | }
 687 | @keyframes pulse-dot {
 688 |   0%, 100% { opacity: 1; }
 689 |   50%      { opacity: 0.3; }
 690 | }
 691 | </style>
 692 | {% endblock %}
 693 | 
 694 | {% block scripts %}
 695 | <script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js" integrity="sha384-irMFAaNSIMAylOGwQzBdH2aFMly/VSIY7JChJO2GJwGCYJF2f3+K0wn+tmFLBX1H" crossorigin="anonymous"></script>
 696 | {% endblock %}
 697 | {% block content %}
 698 | <div class="stage-wrap">
 699 | 
 700 |   <!-- TOP STATUS BAR -->
 701 |   <div class="stage-topbar">
 702 |     <div class="stage-topbar__live">
 703 |       <div class="stage-topbar__dot"></div>
 704 |       <span class="stage-topbar__label">On Air</span>
 705 |     </div>
 706 |     <div class="stage-topbar__ticker">
 707 |       <div class="stage-topbar__ticker-inner" id="tickerInner">
 708 |         <span class="ticker-item">
 709 |           <span class="ti-label">BITCOIN</span>
 710 |           <span class="ti-val" id="tickerPrice">Loading…</span>
 711 |         </span>
 712 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 713 |         <span class="ticker-item">
 714 |           <span class="ti-label">SENTIMENT</span>
 715 |           <span class="ti-val" id="tickerSentiment">—</span>
 716 |         </span>
 717 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 718 |         <span class="ticker-item">
 719 |           <span class="ti-label">ORACLE</span>
 720 |           <span class="ti-val" id="tickerOracle">Standing By</span>
 721 |         </span>
 722 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 723 |         <span class="ticker-item">
 724 |           <span class="ti-label">NETWORK</span>
 725 |           <span class="ti-val" id="tickerTopics">—</span>
 726 |         </span>
 727 |         <!-- Duplicate for seamless loop -->
 728 |         <span class="ticker-item">
 729 |           <span class="ti-label">BITCOIN</span>
 730 |           <span class="ti-val" id="tickerPrice2">Loading…</span>
 731 |         </span>
 732 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 733 |         <span class="ticker-item">
 734 |           <span class="ti-label">SENTIMENT</span>
 735 |           <span class="ti-val" id="tickerSentiment2">—</span>
 736 |         </span>
 737 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 738 |         <span class="ticker-item">
 739 |           <span class="ti-label">ORACLE</span>
 740 |           <span class="ti-val">Standing By</span>
 741 |         </span>
 742 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 743 |         <span class="ticker-item">
 744 |           <span class="ti-label">NETWORK</span>
 745 |           <span class="ti-val" id="tickerTopics2">—</span>
 746 |         </span>
 747 |       </div>
 748 |     </div>
 749 |     <div class="stage-topbar__time" id="stageTime">—</div>
 750 |   </div>
 751 | 
 752 |   <!-- HEADER -->
 753 |   <div class="stage-header">
 754 |     <div>
 755 |       <div class="stage-header__title">⚡ Oracle Stage</div>
 756 |       <div class="stage-header__sub">LIVE BITCOIN INTELLIGENCE BROADCAST — PROTOCOLPULSE.IO</div>
 757 |     </div>
 758 |     <div class="stage-header__right">
 759 |       <div class="stage-badge stage-badge--on">● On Air</div>
 760 |       <div class="stage-badge stage-badge--ok" id="avatarStatusBadge">● Avatar Ready</div>
 761 |     </div>
 762 |   </div>
 763 | 
 764 |   <!-- MAIN GRID -->
 765 |   <div class="stage-grid">
 766 | 
 767 |     <!-- CENTERED: Avatar panel -->
 768 |     <div class="stage-main">
 769 |       <div class="stage-desk">
 770 |         <!-- ON AIR Badge -->
 771 |         <div id="onAirBadge" style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:rgba(255,59,95,.08);border:1px solid rgba(255,59,95,.25);border-radius:6px 6px 0 0;border-bottom:none;">
 772 |           <span style="width:8px;height:8px;border-radius:50%;background:var(--s-red);box-shadow:0 0 6px var(--s-red);animation:live-pulse 1.4s ease-in-out infinite;"></span>
 773 |           <span style="font-family:var(--s-mono);font-size:11px;letter-spacing:.18em;color:var(--s-red);text-transform:uppercase;font-weight:700;">ON AIR</span>
 774 |           <span id="signalSourceLabel" style="font-family:var(--s-mono);font-size:10px;color:rgba(255,255,255,.5);letter-spacing:.08em;margin-left:8px;">📡 INITIALIZING</span>
 775 |           <span id="sessionTimer" style="margin-left:auto;font-family:var(--s-mono);font-size:10px;color:var(--s-gold);letter-spacing:.08em;">Broadcasting for <span id="sessionTime">0:00</span></span>
 776 |         </div>
 777 |         <!-- Avatar -->
 778 |         <div class="stage-avatar-wrap">
 779 |           <video class="stage-avatar-vid" id="avatarVid"
 780 |                  playsinline webkit-playsinline preload="auto"
 781 |                  style="display:block;opacity:1;"></video>
 782 |           <div id="stage-wake" style="display:none;position:absolute;inset:0;z-index:100;background:rgba(4,5,10,.85);flex-direction:column;align-items:center;justify-content:center;gap:16px;cursor:pointer;border-radius:4px;" onclick="stageWake()">
 783 |             <div style="font-size:48px;">&#9889;</div>
 784 |             <div id="stage-tap-label" style="font-family:var(--s-mono);font-size:12px;color:rgba(255,255,255,.8);letter-spacing:.2em;text-transform:uppercase;">Signal Warming Up<span id="stage-tap-dots" style="display:inline-block;width:1.5em;text-align:left;">.</span></div>
 785 |           </div>
 786 |           <div class="stage-avatar-scanline"></div>
 787 |           <div class="stage-avatar-nameplate">
 788 |             <div class="stage-avatar-nameplate__dot"></div>
 789 |             <div class="stage-avatar-nameplate__name">Oracle — Protocol Pulse</div>
 790 |           </div>
 791 |           <div style="position:absolute;bottom:14px;right:14px;z-index:50;display:flex;flex-direction:column;align-items:center;gap:5px;">
 792 |             <button id="floatingMicBtn"
 793 |               onclick="toggleStageMic()"
 794 |               title="Tap to interrupt Oracle"
 795 |               style="width:48px;height:48px;border-radius:50%;background:rgba(13,16,23,.85);border:2px solid rgba(255,59,95,.5);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:20px;transition:all .2s;backdrop-filter:blur(12px);">
 796 |               <span id="fmicIcon">&#9889;</span>
 797 |               <span id="fmicStop" style="display:none;font-size:16px;">&#9632;</span>
 798 |             </button>
 799 |             <span id="fmicHint" style="font-family:var(--s-mono);font-size:8px;color:rgba(255,255,255,.5);letter-spacing:.1em;text-transform:uppercase;white-space:nowrap;">interrupt</span>
 800 |             <button id="stage-cam-btn"
 801 |               onclick="handleStageCameraInterrupt()"
 802 |               title="Photo question"
 803 |               style="width:48px;height:48px;border-radius:50%;background:rgba(13,16,23,.85);border:1px solid rgba(255,255,255,.12);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;transition:all .2s;backdrop-filter:blur(12px);margin-top:4px;">
 804 |               &#128247;
 805 |             </button>
 806 |             <input type="file" id="stage-cam-input" accept="image/*"
 807 |               capture="environment" style="display:none;"
 808 |               onchange="handleStageCameraUpload(event)">
 809 |           </div>
 810 |         </div>
 811 |         <div style="font-family:monospace;font-size:11px;color:#00ffc8;letter-spacing:3px;border-top:1px solid rgba(0,255,200,0.2);padding:6px 12px;background:rgba(0,0,0,0.8)">
 812 |           <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#DC2626;margin-right:8px;animation:pulse-dot 1.5s infinite"></span>
 813 |           PROTOCOL PULSE / ACTIVE
 814 |         </div>
 815 |       </div>
 816 |     </div><!-- /stage-main -->
 817 | 
 818 |     <!-- DATA STRIP: sentiment | narrative | topics + controls -->
 819 |     <div class="stage-data-strip">
 820 |       <!-- Column 1: Sentiment -->
 821 |       <div>
 822 |         <div class="stage-brief__section-label">Market Sentiment</div>
 823 |         <div class="stage-brief__sentiment">
 824 |           <div>
 825 |             <div class="stage-brief__sentiment-score" id="sentimentScore" role="status" aria-live="polite">—</div>
 826 |             <div class="stage-brief__sentiment-label" id="sentimentLabel">Loading</div>
 827 |           </div>
 828 |           <div style="flex:1">
 829 |             <div class="stage-brief__sentiment-bar-wrap">
 830 |               <div class="stage-brief__sentiment-bar" id="sentimentBar" style="width:50%"></div>
 831 |             </div>
 832 |             <div style="display:flex;justify-content:space-between;margin-top:4px">
 833 |               <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-red)">BEARISH</span>
 834 |               <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-green)">BULLISH</span>
 835 |             </div>
 836 |           </div>
 837 |         </div>
 838 |       </div>
 839 | 
 840 |       <!-- Column 2: Narrative -->
 841 |       <div>
 842 |         <div class="stage-narrative" id="narrativeText">Loading Oracle narrative…</div>
 843 |       </div>
 844 | 
 845 |       <!-- Column 3: Topics + Broadcast buttons -->
 846 |       <div>
 847 |         <div class="stage-brief__section-label">Active Topics</div>
 848 |         <div class="stage-topics" id="topicsWrap">
 849 |           <span class="stage-topic stage-topic--neut shimmer" style="width:100px;height:20px;">&nbsp;</span>
 850 |         </div>
 851 |         <div style="margin-top:12px">
 852 |           <div class="stage-brief__section-label">Oracle Broadcast</div>
 853 |           <div class="stage-controls">
 854 |             <button class="stage-btn stage-btn--primary" id="briefBtn" onclick="requestBrief()" aria-label="Request daily Bitcoin briefing">
 855 |               ▶ Daily Brief
 856 |             </button>
 857 |             <div class="stage-status" id="stageStatus">Ready</div>
 858 |           </div>
 859 |         </div>
 860 |       </div>
 861 |     </div><!-- /stage-data-strip -->
 862 | 
 863 |     <!-- TIMED BRIEFING + INTERACTIVE -->
 864 |     <div class="stage-below-strip">
 865 |       <!-- Timed Briefing Countdown -->
 866 |       <div>
 867 |         <div class="stage-brief__section-label">Timed Briefing</div>
 868 |         <div id="briefingCountdown" class="stage-brief-countdown">
 869 |           <div class="stage-brief-countdown__row">
 870 |             <div class="stage-brief-countdown__dot" id="briefDot"></div>
 871 |             <div class="stage-brief-countdown__label">NEXT BRIEFING</div>
 872 |           </div>
 873 |           <div class="stage-brief-countdown__timer" id="countdownTimer">&mdash;</div>
 874 |           <div class="stage-brief-countdown__sub" id="countdownSub">Checking schedule&hellip;</div>
 875 |           <button class="stage-btn stage-btn--primary stage-brief-countdown__play"
 876 |                   id="briefPlayBtn" style="display:none"
 877 |                   onclick="playLatestBrief()">&#9654; Play Brief</button>
 878 |         </div>
 879 |       </div>
 880 | 
 881 |       <!-- Mode switching -->
 882 |       <div>
 883 |         <div class="stage-brief__section-label">Stage Mode</div>
 884 |         <div id="stageModeBadge" class="stage-mode-badge broadcast">● ON AIR</div>
 885 |         <div class="stage-between-badge" id="betweenBadge" style="display:none">
 886 |           BETWEEN SEGMENTS — <span id="betweenCountdown">--:--</span> until next briefing
 887 |         </div>
 888 |       </div>
 889 | 
 890 |       <!-- Interactive Oracle Panel (visible between briefings) -->
 891 |       <div id="interactivePanel" class="stage-interactive-panel">
 892 |         <div style="font-family:var(--s-mono);font-size:9px;letter-spacing:.15em;color:var(--s-muted);text-transform:uppercase;margin-bottom:8px">Ask Oracle Anything</div>
 893 |         <div class="stage-chat-input">
 894 |           <input type="text" id="stageChatInput" placeholder="Ask about Bitcoin..."
 895 |                  onkeydown="if(event.key==='Enter')stageChat()">
 896 |           <button class="stage-mic-btn" id="stageMicBtn" onclick="toggleStageMic()" title="Tap to speak" aria-label="Push to speak — tap to ask Oracle a question" role="button">&#127908;</button>
 897 |           <button class="stage-btn stage-btn--primary" onclick="stageChat()" style="padding:8px 14px">&#9654;</button>
 898 |         </div>
 899 |         <div class="stage-chat-history" id="stageChatHistory"></div>
 900 |       </div>
 901 |     </div><!-- /stage-below-strip -->
 902 | 
 903 |     <!-- PARTNER CHANNEL INTELLIGENCE -->
 904 |     <div class="stage-below-strip">
 905 |       <div class="stage-brief__section-label">Partner Channel Intelligence</div>
 906 |       <div class="stage-transcripts-wrap">
 907 |         <div class="stage-transcripts" id="transcriptsGrid">
 908 |           <!-- Skeleton loaders -->
 909 |           {% for i in range(6) %}
 910 |           <div class="stage-tx-card shimmer" style="height:140px;"></div>
 911 |           {% endfor %}
 912 |         </div>
 913 |         <div id="txDots" class="stage-tx-scroll-hint"></div>
 914 |       </div>
 915 |     </div>
 916 | 
 917 |     <!-- SIDEBAR: Price + Nostr (now full-width row) -->
 918 |     <div class="stage-sidebar">
 919 | 
 920 |       <!-- Price Panel -->
 921 |       <div class="stage-panel">
 922 |         <div class="stage-panel__header">
 923 |           <span><span class="stage-panel__header-dot" style="background:var(--s-gold)"></span>Bitcoin Price</span>
 924 |           <span id="priceUpdated" style="font-size:8px;color:rgba(255,255,255,.2)">live</span>
 925 |         </div>
 926 |         <div class="stage-panel__body">
 927 |           <div class="stage-price-big" id="sidebarPrice" role="status" aria-live="polite">—</div>
 928 |           <div class="stage-price-label">USD</div>
 929 |           <div class="stage-price-change" id="sidebarSentimentLine" role="status" aria-live="polite">—</div>
 930 |         </div>
 931 |       </div>
 932 | 
 933 |       <!-- Nostr Signal Panel -->
 934 |       <div class="stage-panel" style="overflow:hidden;display:flex;flex-direction:column;">
 935 |         <div class="stage-panel__header">
 936 |           <span><span class="stage-panel__header-dot" style="background:var(--s-red);animation:live-pulse 1.4s infinite"></span>Nostr Signal</span>
 937 |           <span id="nostrCount" style="font-size:8px;color:rgba(255,255,255,.3)">0 posts</span>
 938 |         </div>
 939 |         <div class="stage-panel__body stage-signal-feed" id="nostrFeed">
 940 |           <div style="font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0">
 941 |             Loading signal…
 942 |           </div>
 943 |         </div>
 944 |       </div>
 945 | 
 946 |     </div><!-- /stage-sidebar -->
 947 |   </div><!-- /stage-grid -->
 948 | 
 949 |   <!-- BROADCAST TICKER (bottom strip) -->
 950 |   <div id="broadcastTicker" style="position:fixed;bottom:0;left:0;right:0;z-index:200;background:rgba(4,5,10,.95);border-top:1px solid var(--s-border);padding:8px 20px;display:flex;align-items:center;gap:12px;backdrop-filter:blur(8px);">
 951 |     <span style="font-family:var(--s-mono);font-size:9px;letter-spacing:.18em;color:var(--s-red);text-transform:uppercase;flex-shrink:0;font-weight:700;">UP NEXT</span>
 952 |     <div id="tickerContent" style="font-family:var(--s-mono);font-size:10px;color:rgba(255,255,255,.6);letter-spacing:.06em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;">Loading broadcast queue...</div>
 953 |   </div>
 954 | </div><!-- /stage-wrap -->
 955 | 
 956 | <!-- Transcript Reader Overlay -->
 957 | <div class="stage-reader" id="stageReader">
 958 |   <div class="stage-reader__inner">
 959 |     <button class="stage-reader__close" onclick="closeReader()">
 960 |       ← Back to Stage
 961 |     </button>
 962 |     <div class="stage-reader__channel" id="readerChannel"></div>
 963 |     <div class="stage-reader__title" id="readerTitle"></div>
 964 |     <div class="stage-reader__body" id="readerBody"></div>
 965 |   </div>
 966 | </div>
 967 | 
 968 | <script>
 969 | (function(){
 970 |   'use strict';
 971 | 
 972 |   // ── CONFIG ────────────────────────────────────────────
 973 |   var AVATAR_BASE = 'https://avatar.protocolpulse.io';
 974 |   var busy = false;
 975 |   var objURL = null;
 976 |   var _isMobileBrowser = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
 977 |   var vid = document.getElementById('avatarVid');
 978 |   var briefBtn = document.getElementById('briefBtn');
 979 |   var statusEl = document.getElementById('stageStatus');
 980 |   var badgeEl  = document.getElementById('avatarStatusBadge');
 981 | 
 982 |   // ── SAFE TEXT HELPER (P0.2: replaces old esc()) ────────
 983 |   // Use textContent for all plain text. For rare intentional HTML, use DOMPurify.
 984 |   function safeText(el, text) {
 985 |     if (el) el.textContent = String(text || '');
 986 |   }
 987 |   function cleanScript(raw){
 988 |     if(!raw) return '';
 989 |     return raw.replace(/^#+\s+[^\n]*/gm,'').replace(/^---+\s*$/gm,'').replace(/\*\*([^*]+)\*\*/g,'$1').replace(/\n{3,}/g,'\n\n').trim();
 990 |   }
 991 |   function safeHTML(el, html) {
 992 |     if (el && typeof DOMPurify !== 'undefined') {
 993 |       el.innerHTML = DOMPurify.sanitize(html, {ALLOWED_TAGS: ['span','b','em','strong'], ALLOWED_ATTR: ['style','class']});
 994 |     } else if (el) {
 995 |       el.textContent = String(html || '');
 996 |     }
 997 |   }
 998 | 
 999 |   // ── 429 HANDLER (P0.1: server-side rate limiting) ──────
1000 |   function handle429(resp) {
1001 |     if (resp.status === 429) {
1002 |       var retryAfter = resp.headers.get('Retry-After') || '30';
1003 |       var secs = parseInt(retryAfter, 10) || 30;
1004 |       setStatus('Too many requests — wait ' + secs + 's', 'var(--s-red)');
1005 |       return true;
1006 |     }
1007 |     return false;
1008 |   }
1009 | 
1010 |   // ── SESSION TIMER ─────────────────────────────────────
1011 |   var _sessionStart = Date.now();
1012 |   function updateSessionTimer() {
1013 |     var elapsed = Math.floor((Date.now() - _sessionStart) / 1000);
1014 |     var h = Math.floor(elapsed / 3600);
1015 |     var m = Math.floor((elapsed % 3600) / 60);
1016 |     var s = elapsed % 60;
1017 |     var el = document.getElementById('sessionTime');
1018 |     if (el) el.textContent = (h > 0 ? h + ':' : '') + pad(m) + ':' + pad(s);
1019 |   }
1020 | 
1021 |   // ── CLOCK ────────────────────────────────────────────
1022 |   function tick(){
1023 |     var now = new Date();
1024 |     safeText(document.getElementById('stageTime'), now.toUTCString().slice(17,22) + ' UTC');
1025 |     updateSessionTimer();
1026 |   }
1027 |   tick(); setInterval(tick, 1000);
1028 | 
1029 |   // ── LAST UPDATED INDICATOR (P1.4) ────────────────────
1030 |   var _lastIntelUpdate = 0;
1031 |   var _lastNostrUpdate = 0;
1032 |   function updateStaleness() {
1033 |     var now = Date.now();
1034 |     if (_lastIntelUpdate) {
1035 |       var ago = Math.floor((now - _lastIntelUpdate) / 1000);
1036 |       var el = document.getElementById('priceUpdated');
1037 |       if (el) el.textContent = ago < 10 ? 'just now' : ago + 's ago';
1038 |     }
1039 |   }
1040 |   setInterval(updateStaleness, 5000);
1041 | 
1042 |   // ── FETCH INTEL ───────────────────────────────────────
1043 |   function loadIntel(){
1044 |     fetch('/api/stage/intel')
1045 |     .then(function(r){ return r.json(); })
1046 |     .then(function(d){
1047 |       _lastIntelUpdate = Date.now();
1048 |       // price
1049 |       var price = d.price || '';
1050 |       updatePrice(price, d.price_float);
1051 |       // sentiment
1052 |       var score = d.sentiment_score || 50;
1053 |       var label = d.sentiment_label || 'neutral';
1054 |       safeText(document.getElementById('sentimentScore'), score);
1055 |       safeText(document.getElementById('sentimentLabel'), label.toUpperCase());
1056 |       document.getElementById('sentimentBar').style.width = score + '%';
1057 |       var sentColor = score > 60 ? 'var(--s-green)' : score < 40 ? 'var(--s-red)' : 'var(--s-gold)';
1058 |       document.getElementById('sentimentScore').style.color = sentColor;
1059 |       document.getElementById('sentimentLabel').style.color = sentColor;
1060 |       // ticker (P0.2: textContent only)
1061 |       safeText(document.getElementById('tickerPrice'), price);
1062 |       safeText(document.getElementById('tickerPrice2'), price);
1063 |       safeText(document.getElementById('tickerSentiment'), label.toUpperCase() + ' ' + score + '/100');
1064 |       safeText(document.getElementById('tickerSentiment2'), label.toUpperCase() + ' ' + score + '/100');
1065 |       // sidebar sentiment line (P0.2: was innerHTML, now safe DOM construction)
1066 |       var sentLine = document.getElementById('sidebarSentimentLine');
1067 |       if (sentLine) {
1068 |         sentLine.textContent = '';
1069 |         var span = document.createElement('span');
1070 |         span.style.cssText = 'color:'+sentColor+';font-family:var(--s-mono);font-size:11px';
1071 |         span.textContent = label.toUpperCase() + ' — ' + score + '/100';
1072 |         sentLine.appendChild(span);
1073 |       }
1074 |       // narrative
1075 |       if(d.narrative){
1076 |         safeText(document.getElementById('narrativeText'), d.narrative);
1077 |       }
1078 |       // topics
1079 |       if(d.topics){
1080 |         renderTopics(d.topics);
1081 |         var topicsText = d.topics.replace(/\([^)]+\)/g,'').replace(/,/g,' ·');
1082 |         safeText(document.getElementById('tickerTopics'), topicsText);
1083 |         safeText(document.getElementById('tickerTopics2'), topicsText);
1084 |       }
1085 |     })
1086 |     .catch(function(){
1087 |       safeText(document.getElementById('narrativeText'), 'Intel feed offline — retrying in 30s');
1088 |       safeText(document.getElementById('tickerOracle'), 'Offline');
1089 |     });
1090 |   }
1091 | 
1092 |   function updatePrice(priceStr, priceFloat){
1093 |     if(!priceStr) return;
1094 |     var fmt = priceFloat ? '$' + Number(priceFloat).toLocaleString('en-US',{maximumFractionDigits:0}) : priceStr;
1095 |     safeText(document.getElementById('sidebarPrice'), fmt);
1096 |     safeText(document.getElementById('tickerPrice'), fmt);
1097 |     safeText(document.getElementById('tickerPrice2'), fmt);
1098 |   }
1099 | 
1100 |   function renderTopics(topicsStr){
1101 |     var wrap = document.getElementById('topicsWrap');
1102 |     wrap.innerHTML = '';
1103 |     var parts = topicsStr.split(',');
1104 |     parts.forEach(function(t){
1105 |       t = t.trim();
1106 |       var cls = 'stage-topic--neut';
1107 |       if(t.indexOf('(bullish)')>=0 || t.indexOf('bullish')>=0) cls = 'stage-topic--bull';
1108 |       if(t.indexOf('(bearish)')>=0 || t.indexOf('bearish')>=0) cls = 'stage-topic--bear';
1109 |       var label = t.replace(/\s*\([^)]+\)\s*/g,'').trim();
1110 |       var span = document.createElement('span');
1111 |       span.className = 'stage-topic ' + cls;
1112 |       span.textContent = label;
1113 |       wrap.appendChild(span);
1114 |     });
1115 |   }
1116 | 
1117 |   // ── LOAD TRANSCRIPTS (P0.2: no innerHTML with external data) ───
1118 |   function loadTranscripts(){
1119 |     fetch('/api/stage/transcripts')
1120 |     .then(function(r){ return r.json(); })
1121 |     .then(function(data){
1122 |       renderTranscripts(data);
1123 |     })
1124 |     .catch(function(){
1125 |       renderTranscripts([]);
1126 |     });
1127 |   }
1128 | 
1129 |   function renderTranscripts(items){
1130 |     var grid = document.getElementById('transcriptsGrid');
1131 |     if(!items || !items.length){
1132 |       grid.textContent = '';
1133 |       var msg = document.createElement('div');
1134 |       msg.style.cssText = 'grid-column:1/-1;font-family:var(--s-mono);font-size:11px;color:var(--s-muted);padding:20px 0';
1135 |       msg.textContent = 'No transcript data available yet. Channel scan in progress.';
1136 |       grid.appendChild(msg);
1137 |       document.dispatchEvent(new CustomEvent('transcriptsRendered'));
1138 |       return;
1139 |     }
1140 |     grid.textContent = '';
1141 |     items.forEach(function(item){
1142 |       var sentCls = 'stage-topic--neut';
1143 |       var sentLabel = item.sentiment || 'neutral';
1144 |       if(sentLabel === 'bullish') sentCls = 'stage-topic--bull';
1145 |       if(sentLabel === 'bearish') sentCls = 'stage-topic--bear';
1146 |       var card = document.createElement('div');
1147 |       card.className = 'stage-tx-card';
1148 | 
1149 |       // P0.2: Build DOM elements, never innerHTML with external data
1150 |       var chDiv = document.createElement('div');
1151 |       chDiv.className = 'stage-tx-card__channel';
1152 |       chDiv.textContent = (item.channel || 'Unknown');
1153 |       card.appendChild(chDiv);
1154 | 
1155 |       var titleDiv = document.createElement('div');
1156 |       titleDiv.className = 'stage-tx-card__title';
1157 |       titleDiv.textContent = (item.title || '').slice(0, 70);
1158 |       card.appendChild(titleDiv);
1159 | 
1160 |       var excerptDiv = document.createElement('div');
1161 |       excerptDiv.className = 'stage-tx-card__excerpt';
1162 |       excerptDiv.textContent = (item.excerpt || item.transcript_snippet || '').slice(0, 120) + '…';
1163 |       card.appendChild(excerptDiv);
1164 | 
1165 |       var footer = document.createElement('div');
1166 |       footer.className = 'stage-tx-card__footer';
1167 |       var readBtn = document.createElement('button');
1168 |       readBtn.className = 'stage-tx-card__read-btn';
1169 |       readBtn.textContent = 'Read Brief →';
1170 |       readBtn.setAttribute('aria-label', 'Read full transcript for ' + (item.channel || 'this channel'));
1171 |       readBtn.addEventListener('click', function(){ openReader(this); });
1172 |       footer.appendChild(readBtn);
1173 |       var sentSpan = document.createElement('span');
1174 |       sentSpan.className = 'stage-topic ' + sentCls;
1175 |       sentSpan.textContent = sentLabel;
1176 |       footer.appendChild(sentSpan);
1177 |       card.appendChild(footer);
1178 | 
1179 |       // Store data on card
1180 |       card.dataset.channel = item.channel || '';
1181 |       card.dataset.title = item.title || '';
1182 |       card.dataset.body = item.transcript_text || item.excerpt || '';
1183 |       grid.appendChild(card);
1184 |     });
1185 |     // P0.4: Custom event instead of monkey-patching
1186 |     document.dispatchEvent(new CustomEvent('transcriptsRendered'));
1187 |   }
1188 | 
1189 |   // ── NOSTR SIGNAL ──────────────────────────────────────
1190 |   function loadNostr(){
1191 |     fetch('/api/stage/signal')
1192 |     .then(function(r){ return r.json(); })
1193 |     .then(function(d){
1194 |       _lastNostrUpdate = Date.now();
1195 |       var posts = d.nostr_posts || [];
1196 |       renderNostr(posts);
1197 |     })
1198 |     .catch(function(){
1199 |       renderNostr([]);
1200 |       safeText(document.getElementById('nostrCount'), 'offline');
1201 |     });
1202 |   }
1203 | 
1204 |   function renderNostr(posts){
1205 |     var feed = document.getElementById('nostrFeed');
1206 |     safeText(document.getElementById('nostrCount'), posts.length + ' posts');
1207 |     if(!posts.length){
1208 |       feed.textContent = '';
1209 |       var msg = document.createElement('div');
1210 |       msg.style.cssText = 'font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0';
1211 |       msg.textContent = 'No signal yet — relay scanning…';
1212 |       feed.appendChild(msg);
1213 |       return;
1214 |     }
1215 |     feed.textContent = '';
1216 |     posts.slice(0,12).forEach(function(p){
1217 |       var item = document.createElement('div');
1218 |       item.className = 'stage-signal-item';
1219 |       var author = p.nip05 || p.display_name || 'anon';
1220 |       var aDiv = document.createElement('div');
1221 |       aDiv.className = 'stage-signal-item__author';
1222 |       aDiv.textContent = author.slice(0,50);
1223 |       var tDiv = document.createElement('div');
1224 |       tDiv.className = 'stage-signal-item__text';
1225 |       tDiv.textContent = (p.text||'').slice(0,180);
1226 |       item.appendChild(aDiv);
1227 |       item.appendChild(tDiv);
1228 |       feed.appendChild(item);
1229 |     });
1230 |   }
1231 | 
1232 |   // ── TRANSCRIPT READER ─────────────────────────────────
1233 |   window.openReader = function(btn){
1234 |     var card = btn.closest('.stage-tx-card');
1235 |     safeText(document.getElementById('readerChannel'), card.dataset.channel);
1236 |     safeText(document.getElementById('readerTitle'), card.dataset.title);
1237 |     safeText(document.getElementById('readerBody'), card.dataset.body || 'Full transcript not available.');
1238 |     document.getElementById('stageReader').classList.add('open');
1239 |     document.body.style.overflow = 'hidden';
1240 |   };
1241 |   window.closeReader = function(){
1242 |     document.getElementById('stageReader').classList.remove('open');
1243 |     document.body.style.overflow = '';
1244 |   };
1245 | 
1246 |   // ── AVATAR PLAYBACK ───────────────────────────────────
1247 |   function setStatus(msg, color){
1248 |     safeText(statusEl, msg);
1249 |     statusEl.style.color = color || 'rgba(255,255,255,.3)';
1250 |     statusEl.className = 'stage-status' + (msg==='Speaking' ? ' speaking' : '');
1251 |     tickerOracle(msg);
1252 |   }
1253 |   function tickerOracle(msg){
1254 |     safeText(document.getElementById('tickerOracle'), msg);
1255 |   }
1256 |   function setBusy(b){
1257 |     busy = b;
1258 |     briefBtn.disabled = b;
1259 |     safeText(badgeEl, b ? '● Rendering…' : '● Avatar Ready');
1260 |     badgeEl.style.color = b ? 'var(--s-gold)' : 'var(--s-green)';
1261 |     badgeEl.style.borderColor = b ? 'rgba(248,193,92,.3)' : 'rgba(46,255,138,.2)';
1262 |     badgeEl.style.background  = b ? 'rgba(248,193,92,.08)' : 'rgba(46,255,138,.08)';
1263 |   }
1264 | 
1265 |   // P1.5: revokeObjectURL in finally block with null check
1266 |   function revokeObjURL() {
1267 |     if (objURL) {
1268 |       try { URL.revokeObjectURL(objURL); } catch(e) {}
1269 |       objURL = null;
1270 |     }
1271 |   }
1272 | 
1273 |   function playAudioOnly(audioUrl) {
1274 |     return new Promise(function(resolve) {
1275 |       var audio;
1276 |       if (window._stageAudioUnlocked) {
1277 |         audio = window._stageAudioUnlocked;
1278 |         window._stageAudioUnlocked = null;
1279 |         // Re-unlock immediately for the NEXT segment
1280 |         var nextUnlock = new Audio();
1281 |         nextUnlock.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1282 |         nextUnlock.volume = 0.001;
1283 |         nextUnlock.play().catch(function(){});
1284 |         window._stageAudioUnlocked = nextUnlock;
1285 |         audio.src = audioUrl;
1286 |         audio.volume = 1.0;
1287 |         audio.muted = false;
1288 |       } else {
1289 |         audio = new Audio(audioUrl);
1290 |         audio.volume = 1.0;
1291 |       }
1292 |       setStatus('Broadcasting…', 'var(--s-green)');
1293 |       audio.onended = function() {
1294 |         URL.revokeObjectURL(audioUrl);
1295 |         setStatus('Ready', 'rgba(255,255,255,.3)');
1296 |         setBusy(false);
1297 |         resolve();
1298 |       };
1299 |       audio.onerror = function() {
1300 |         setBusy(false);
1301 |         resolve();
1302 |       };
1303 |       audio.play().catch(function(e) {
1304 |         console.warn('[Stage mobile] audio.play() rejected:', e.name);
1305 |         setBusy(false);
1306 |         resolve();
1307 |       });
1308 |     });
1309 |   }
1310 | 
1311 |   function playVid(url){
1312 |     return new Promise(function(resolve){
1313 |       revokeObjURL();
1314 |       objURL = url;
1315 |       vid.src = url;
1316 |       vid.muted = true;
1317 |       vid.volume = 1.0;
1318 |       setStatus('Speaking','var(--s-green)');
1319 |       var unmuted = false;
1320 |       function tryUnmute(){ if(unmuted) return; unmuted=true; vid.muted=false; vid.volume=1.0; try { vid.play(); } catch(e) {} }
1321 |       vid.addEventListener('canplay', function oncp(){
1322 |         vid.removeEventListener('canplay',oncp);
1323 |         tryUnmute();
1324 |       },{once:true});
1325 |       vid.onended = function(){
1326 |         vid.src='';
1327 |         setStatus('Ready','rgba(255,255,255,.3)');
1328 |         setBusy(false);
1329 |         revokeObjURL();
1330 |         resolve();
1331 |       };
1332 |       vid.onerror = function(){
1333 |         setBusy(false);
1334 |         revokeObjURL();
1335 |         resolve();
1336 |       };
1337 |       var p = vid.play();
1338 |       if(p){
1339 |         p.then(function(){
1340 |           setTimeout(tryUnmute, 50);
1341 |         }).catch(function(err){
1342 |           console.warn('[Stage] vid.play() rejected:', err.name);
1343 |           try{
1344 |             var ac=new(window.AudioContext||window.webkitAudioContext)();
1345 |             var buf=ac.createBuffer(1,1,22050);
1346 |             var src=ac.createBufferSource();
1347 |             src.buffer=buf;src.connect(ac.destination);src.start(0);
1348 |             setTimeout(function(){try{ac.close();}catch(e){}},200);
1349 |           }catch(e){}
1350 |           setTimeout(function(){
1351 |             vid.muted=false;
1352 |             vid.play().catch(function(){
1353 |               setStatus('Tap avatar to play','var(--s-gold)');
1354 |               vid.addEventListener('click',function(){vid.muted=false;vid.play();},{once:true});
1355 |             });
1356 |           },300);
1357 |         });
1358 |       }
1359 |     });
1360 |   }
1361 | 
1362 |   function fetchTO(url, opts, ms){
1363 |     var ctrl = new AbortController();
1364 |     var id = setTimeout(function(){ ctrl.abort(); }, ms||30000);
1365 |     var o = opts||{}; o.signal = ctrl.signal;
1366 |     return fetch(url, o).finally(function(){ clearTimeout(id); });
1367 |   }
1368 | 
1369 |   // ── REQUEST BRIEF (P0.1: routes through rate-limited proxy) ───
1370 |   var _briefCooldown = 0;
1371 |   window.requestBrief = function(){
1372 |     if(busy) return;
1373 |     var now = Date.now();
1374 |     if(now - _briefCooldown < 10000){ setStatus('Please wait…','var(--s-gold)'); return; }
1375 |     _briefCooldown = now;
1376 |     setBusy(true); setStatus('Fetching brief…','var(--s-gold)');
1377 |     fetchTO('/api/oracle/speak',{
1378 |       method:'POST', headers:{'Content-Type':'application/json'},
1379 |       body: JSON.stringify({intent:'DAILY_BRIEF'})
1380 |     }, 60000)
1381 |     .then(function(r){
1382 |       if(handle429(r)) throw new Error('rate-limited');
1383 |       if(!r.ok) throw new Error('HTTP '+r.status);
1384 |       return r.blob().then(function(b){ return URL.createObjectURL(b); });
1385 |     })
1386 |     .then(function(url){ return playVid(url); })
1387 |     .catch(function(e){
1388 |       if(e.message !== 'rate-limited') setStatus('Error — try again','var(--s-red)');
1389 |       console.error(e);
1390 |     })
1391 |     .finally(function(){ setBusy(false); });
1392 |   };
1393 | 
1394 | 
1395 |   // ── BROADCAST SYSTEM ──────────────────────────────────
1396 |   var STAGE_MODE = 'broadcast';
1397 |   var _stageSessionId = 'stage_' + Date.now() + '_' + Math.random().toString(36).slice(2,8);
1398 |   var _stageRecognition = null;
1399 |   var _stageIsRec = false;
1400 |   var _currentBroadcastTopic = '';
1401 |   var _preRenderedBlob = null;
1402 |   var _preRenderedItem = null;
1403 |   var _broadcastPaused = false;
1404 |   var _preRenderFirstBlob = null;
1405 |   var _preRenderReady = false;
1406 |   var _preRenderScript = null;
1407 | 
1408 |   async function preRenderFirstSegment() {
1409 |     try {
1410 |       var scriptResp = await fetch('/api/stage/generate-monologue', {
1411 |         method: 'POST',
1412 |         headers: {'Content-Type': 'application/json'}
1413 |       });
1414 |       if (!scriptResp.ok) return;
1415 |       var scriptData = await scriptResp.json();
1416 |       var script = scriptData.script;
1417 |       if (!script) return;
1418 |       _preRenderScript = script;
1419 | 
1420 |       var renderResp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
1421 |         method: 'POST',
1422 |         headers: {'Content-Type': 'application/json'},
1423 |         body: JSON.stringify({text: cleanScript(script), intent: 'BROADCAST_SEGMENT'})
1424 |       }, 120000);
1425 |       if (!renderResp.ok) return;
1426 | 
1427 |       var blob = await renderResp.blob();
1428 |       _preRenderFirstBlob = URL.createObjectURL(blob);
1429 |       _preRenderReady = true;
1430 |       console.log('[Stage] Pre-render complete — ready for tap');
1431 |     } catch(e) {
1432 |       console.warn('[Stage] Pre-render failed:', e);
1433 |     }
1434 |   }
1435 | 
1436 |   // ── BROADCAST QUEUE CONSUMER ──────────────────────────
1437 |   async function startBroadcast() {
1438 |     await runMonologueLoop();
1439 |   }
1440 | 
1441 |   function updateSignalSource(label) {
1442 |     var el = document.getElementById('signalSourceLabel');
1443 |     if (el) el.textContent = label;
1444 |   }
1445 | 
1446 |   function updateTicker(currentItem) {
1447 |     var tickerEl = document.getElementById('tickerContent');
1448 |     if (!tickerEl) return;
1449 |     tickerEl.textContent = currentItem ? ('NOW: ' + currentItem.topic_preview) : 'Loading next segment...';
1450 |   }
1451 | 
1452 |   async function playBroadcastItem(item) {
1453 |     if (_broadcastPaused) return;
1454 |     _currentBroadcastTopic = item.topic_preview || '';
1455 |     updateSignalSource(item.source_label || '📡 BROADCASTING');
1456 |     updateTicker(item);
1457 | 
1458 |     // Update mode badge
1459 |     var badge = document.getElementById('stageModeBadge');
1460 |     if (badge) { badge.textContent = '● ON AIR'; badge.className = 'stage-mode-badge broadcast'; }
1461 | 
1462 |     // Render avatar video via server with script
1463 |     setBusy(true);
1464 |     setStatus('Rendering segment…', 'var(--s-gold)');
1465 | 
1466 |     try {
1467 |       // Generate TTS + avatar via avatar server
1468 |       var resp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
1469 |         method: 'POST',
1470 |         headers: {'Content-Type': 'application/json'},
1471 |         body: JSON.stringify({text: cleanScript(item.script), intent: 'BROADCAST_SEGMENT'})
1472 |       }, 120000);
1473 | 
1474 |       if (!resp.ok) throw new Error('Avatar render failed: HTTP ' + resp.status);
1475 | 
1476 |       var blob = await resp.blob();
1477 |       var url = URL.createObjectURL(blob);
1478 | 
1479 |       // Start pre-rendering next segment while current plays
1480 |       preRenderNext(item.id);
1481 | 
1482 |       await playVid(url);
1483 |       setBusy(false);
1484 | 
1485 |       // After playback: consume and get next
1486 |       if (!_broadcastPaused) {
1487 |         await consumeAndPlay(item.id);
1488 |       }
1489 |     } catch(e) {
1490 |       console.error('playBroadcastItem error:', e);
1491 |       setBusy(false);
1492 |       setStatus('Segment error — retrying…', 'var(--s-red)');
1493 |       setTimeout(function(){ consumeAndPlay(item.id); }, 3000);
1494 |     }
1495 |   }
1496 | 
1497 |   async function consumeAndPlay(consumedId) {
1498 |     if (_broadcastPaused) return;
1499 |     try {
1500 |       var resp = await fetch('/api/stage/consume-broadcast', {
1501 |         method: 'POST',
1502 |         headers: {'Content-Type': 'application/json'},
1503 |         body: JSON.stringify({consumed_id: consumedId})
1504 |       });
1505 |       var data = await resp.json();
1506 | 
1507 |       if (data.next_item) {
1508 |         // If we have a pre-rendered blob for this item, use it
1509 |         if (_preRenderedBlob && _preRenderedItem && _preRenderedItem.id === data.next_item.id) {
1510 |           _currentBroadcastTopic = data.next_item.topic_preview || '';
1511 |           updateSignalSource(data.next_item.source_label || '📡 BROADCASTING');
1512 |           updateTicker(data.next_item);
1513 |           setBusy(true);
1514 |           setStatus('Speaking', 'var(--s-green)');
1515 |           var url = URL.createObjectURL(_preRenderedBlob);
1516 |           _preRenderedBlob = null;
1517 |           _preRenderedItem = null;
1518 |           preRenderNext(data.next_item.id);
1519 |           await playVid(url);
1520 |           setBusy(false);
1521 |           if (!_broadcastPaused) await consumeAndPlay(data.next_item.id);
1522 |         } else {
1523 |           await playBroadcastItem(data.next_item);
1524 |         }
1525 |       } else {
1526 |         updateSignalSource('📡 STANDING BY');
1527 |         setTimeout(startBroadcast, 5000);
1528 |       }
1529 |     } catch(e) {
1530 |       console.error('consumeAndPlay error:', e);
1531 |       setTimeout(startBroadcast, 5000);
1532 |     }
1533 |   }
1534 | 
1535 |   // Pre-render next segment while current plays (reduce dead air)
1536 |   async function preRenderNext(currentId) {
1537 |     try {
1538 |       var resp = await fetch('/api/stage/broadcast-queue');
1539 |       if (!resp.ok) return;
1540 |       var data = await resp.json();
1541 |       // Find next item that isn't current
1542 |       var next = null;
1543 |       for (var i = 0; i < data.items.length; i++) {
1544 |         if (data.items[i].id !== currentId) { next = data.items[i]; break; }
1545 |       }
1546 |       if (!next) return;
1547 | 
1548 |       var renderResp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
1549 |         method: 'POST',
1550 |         headers: {'Content-Type': 'application/json'},
1551 |         body: JSON.stringify({text: cleanScript(next.script), intent: 'BROADCAST_SEGMENT'})
1552 |       }, 120000);
1553 | 
1554 |       if (renderResp.ok) {
1555 |         _preRenderedBlob = await renderResp.blob();
1556 |         _preRenderedItem = next;
1557 |       }
1558 |     } catch(e) {
1559 |       // Pre-render failure is non-fatal
1560 |     }
1561 |   }
1562 | 
1563 |   // ── PUSH TO SPEAK (interrupt flow) ────────────────────
1564 |   var _ptsModalShown = false;
1565 |   var _ptsFirstTime = true;
1566 | 
1567 |   function stageWake() {
1568 |     if (!_preRenderReady && !_preRenderFirstBlob) {
1569 |       // Not ready yet — show feedback but don't proceed
1570 |       var lbl = document.getElementById('stage-tap-label');
1571 |       if (lbl) {
1572 |         lbl.textContent = 'SIGNAL LOADING\u2026';
1573 |         setTimeout(function(){
1574 |           if (!_preRenderReady) lbl.textContent = 'SIGNAL WARMING UP\u2026';
1575 |         }, 1500);
1576 |       }
1577 |       return;
1578 |     }
1579 |     try {
1580 |       var ac=new(window.AudioContext||window.webkitAudioContext)();
1581 |       var buf=ac.createBuffer(1,1,22050);
1582 |       var src=ac.createBufferSource();
1583 |       src.buffer=buf;src.connect(ac.destination);src.start(0);
1584 |       setTimeout(function(){try{ac.close();}catch(e){}},300);
1585 |     } catch(e) {}
1586 |     /* Pre-unlock Audio element for mobile playback */
1587 |     try {
1588 |       window._audioUnlocked = new Audio();
1589 |       window._audioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1590 |       window._audioUnlocked.volume = 0.001;
1591 |       window._audioUnlocked.play().catch(function(){});
1592 |     } catch(e) {}
1593 |     /* Pre-unlock a second Audio element for stage mobile audio-only mode */
1594 |     window._stageAudioUnlocked = new Audio();
1595 |     window._stageAudioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1596 |     window._stageAudioUnlocked.volume = 0.001;
1597 |     window._stageAudioUnlocked.play().catch(function(){});
1598 |     // Pre-unlock video element for future muted→unmuted autoplay
1599 |     try {
1600 |       var vidEl = document.getElementById('avatarVid');
1601 |       if(vidEl) {
1602 |         vidEl.muted = true;
1603 |         vidEl.src = 'data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28ybXA0MAAAACB3aWRlAAAAAQAAABhtZGF0';
1604 |         vidEl.play().catch(function(){});
1605 |         setTimeout(function(){
1606 |           vidEl.pause();
1607 |           vidEl.src = '';
1608 |           vidEl.load();
1609 |         }, 200);
1610 |       }
1611 |     } catch(e) {}
1612 |     var ov=document.getElementById('stage-wake');
1613 |     if(ov) ov.style.display='none';
1614 | 
1615 |     if (_preRenderReady && _preRenderFirstBlob) {
1616 |       // Pre-rendered segment ready — play immediately within gesture window
1617 |       var url = _preRenderFirstBlob;
1618 |       _preRenderFirstBlob = null;
1619 |       _preRenderReady = false;
1620 |       setBusy(true);
1621 |       setStatus('Broadcasting…', 'var(--s-green)');
1622 |       vid.src = url;
1623 |       vid.muted = false;
1624 |       vid.volume = 1.0;
1625 |       vid.play().then(function() {
1626 |         vid.onended = function() {
1627 |           vid.src = '';
1628 |           URL.revokeObjectURL(url);
1629 |           setBusy(false);
1630 |           setStatus('Ready', 'rgba(255,255,255,.3)');
1631 |           startBroadcast();
1632 |         };
1633 |       }).catch(function(e) {
1634 |         console.warn('[Stage] Pre-rendered play failed:', e.name);
1635 |         URL.revokeObjectURL(url);
1636 |         startBroadcast();
1637 |       });
1638 |     } else {
1639 |       startBroadcast();
1640 |     }
1641 |   }
1642 |   window.stageWake = stageWake;
1643 | 
1644 |   window.toggleStageMic = function() {
1645 |     if (_stageIsRec) { _stopStageMic(); return; }
1646 | 
1647 |     // First-time modal
1648 |     if (_ptsFirstTime) {
1649 |       _ptsFirstTime = false;
1650 |       if (!confirm('The anchor is live. Tap OK to ask a question — the broadcast will pause while you speak.')) {
1651 |         return;
1652 |       }
1653 |     }
1654 | 
1655 |     // Request mic permission
1656 |     if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
1657 |       navigator.mediaDevices.getUserMedia({audio: true, video: false})
1658 |         .then(function(stream) {
1659 |           stream.getTracks().forEach(function(t) { t.stop(); });
1660 |           _startStageMic();
1661 |         })
1662 |         .catch(function(err) {
1663 |           var name = err && err.name ? err.name : '';
1664 |           if (name === 'NotAllowedError') {
1665 |             _appendChatMsg('Microphone blocked. Allow access in browser settings and reload.', 'oracle');
1666 |           } else if (name === 'NotFoundError') {
1667 |             _appendChatMsg('No microphone found. Connect a mic and try again.', 'oracle');
1668 |           } else {
1669 |             _appendChatMsg('Microphone error: ' + name + '. Try Chrome for best results.', 'oracle');
1670 |           }
1671 |         });
1672 |     } else {
1673 |       _startStageMic(); // Fallback: try SpeechRecognition directly
1674 |     }
1675 |   };
1676 | 
1677 |   function _startStageMic() {
1678 |     if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
1679 |       _appendChatMsg('Speech recognition not supported in this browser. Try Chrome.', 'oracle');
1680 |       return;
1681 |     }
1682 | 
1683 |     // Pause broadcast
1684 |     _broadcastPaused = true;
1685 |     if (vid && !vid.paused) {
1686 |       vid.pause();
1687 |     }
1688 |     // Show interrupted state
1689 |     updateSignalSource('🎤 INTERRUPTED — LISTENER SPEAKING');
1690 | 
1691 |     var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
1692 |     _stageRecognition = new SR();
1693 |     _stageRecognition.lang = 'en-US';
1694 |     _stageRecognition.continuous = false;
1695 |     _stageRecognition.interimResults = false;
1696 | 
1697 |     // P1.2: 10-second timeout
1698 |     var micTimeout = setTimeout(function() {
1699 |       _appendChatMsg('No speech detected — try again.', 'oracle');
1700 |       _stopStageMic();
1701 |       _resumeBroadcast();
1702 |     }, 10000);
1703 | 
1704 |     _stageRecognition.onresult = function(e) {
1705 |       clearTimeout(micTimeout);
1706 |       var text = e.results[0][0].transcript;
1707 |       document.getElementById('stageChatInput').value = text;
1708 |       _stopStageMic();
1709 |       _handleInterruptQuestion(text);
1710 |     };
1711 |     _stageRecognition.onerror = function(e) {
1712 |       clearTimeout(micTimeout);
1713 |       // P1.2: User-visible error message
1714 |       var msg = 'Speech error';
1715 |       if (e.error === 'no-speech') msg = 'No speech detected — try again.';
1716 |       else if (e.error === 'audio-capture') msg = 'No microphone available.';
1717 |       else if (e.error === 'not-allowed') msg = 'Microphone access denied.';
1718 |       _appendChatMsg(msg, 'oracle');
1719 |       _stopStageMic();
1720 |       _resumeBroadcast();
1721 |     };
1722 |     _stageRecognition.onend = function() {
1723 |       clearTimeout(micTimeout);
1724 |       _stopStageMic();
1725 |     };
1726 | 
1727 |     _stageRecognition.start();
1728 |     _stageIsRec = true;
1729 |     document.getElementById('stageMicBtn').classList.add('recording');
1730 |     var fmb = document.getElementById('floatingMicBtn');
1731 |     var fmicIcon = document.getElementById('fmicIcon');
1732 |     var fmicStop = document.getElementById('fmicStop');
1733 |     var fmicHint = document.getElementById('fmicHint');
1734 |     if (fmb) {
1735 |       fmb.classList.toggle('fmic-rec', _stageIsRec);
1736 |     }
1737 |     if (fmicIcon) fmicIcon.style.display = _stageIsRec ? 'none' : 'block';
1738 |     if (fmicStop) fmicStop.style.display = _stageIsRec ? 'block' : 'none';
1739 |     if (fmicHint) fmicHint.textContent = _stageIsRec ? 'tap to send' : 'tap to speak';
1740 |     document.getElementById('interactivePanel').classList.add('active');
1741 |   }
1742 | 
1743 |   function _stopStageMic() {
1744 |     _stageIsRec = false;
1745 |     if(_stageRecognition) { try{_stageRecognition.stop();}catch(e){} _stageRecognition = null; }
1746 |     document.getElementById('stageMicBtn').classList.remove('recording');
1747 |     var fmb = document.getElementById('floatingMicBtn');
1748 |     var fmicIcon = document.getElementById('fmicIcon');
1749 |     var fmicStop = document.getElementById('fmicStop');
1750 |     var fmicHint = document.getElementById('fmicHint');
1751 |     if (fmb) {
1752 |       fmb.classList.toggle('fmic-rec', _stageIsRec);
1753 |     }
1754 |     if (fmicIcon) fmicIcon.style.display = _stageIsRec ? 'none' : 'block';
1755 |     if (fmicStop) fmicStop.style.display = _stageIsRec ? 'block' : 'none';
1756 |     if (fmicHint) fmicHint.textContent = _stageIsRec ? 'tap to send' : 'tap to speak';
1757 |   }
1758 | 
1759 |   // ── STAGE CAMERA INTERRUPT ───────────────────────────
1760 |   function handleStageCameraInterrupt() {
1761 |     if (busy) return;
1762 |     var input = document.getElementById('stage-cam-input');
1763 |     if (input) input.click();
1764 |   }
1765 |   window.handleStageCameraInterrupt = handleStageCameraInterrupt;
1766 | 
1767 |   function handleStageCameraUpload(evt) {
1768 |     var file = evt.target.files && evt.target.files[0];
1769 |     if (!file) return;
1770 |     if (busy) {
1771 |       setStatus('Finishing current segment…', 'var(--s-gold)');
1772 |       return;
1773 |     }
1774 | 
1775 |     // Pause broadcast, handle vision interrupt
1776 |     _broadcastPaused = true;
1777 |     if (vid && !vid.paused) vid.pause();
1778 |     setBusy(true);
1779 |     setStatus('Analyzing image…', 'var(--s-gold)');
1780 |     updateSignalSource('📷 VIEWER PHOTO QUESTION');
1781 | 
1782 |     var reader = new FileReader();
1783 |     reader.onload = function(e) {
1784 |       var dataUrl = e.target.result;
1785 |       var b64 = dataUrl.split(',')[1];
1786 |       var mime = file.type || 'image/jpeg';
1787 | 
1788 |       fetchTO('https://avatar.protocolpulse.io/vision/analyze', {
1789 |         method: 'POST',
1790 |         headers: {'Content-Type': 'application/json'},
1791 |         body: JSON.stringify({
1792 |           image_base64: b64,
1793 |           mime_type: mime,
1794 |           session_id: 'stage_' + Date.now(),
1795 |           context: 'Bitcoin hardware question from live broadcast viewer'
1796 |         })
1797 |       }, 45000)
1798 |       .then(function(r) {
1799 |         if (!r.ok) throw new Error('vision ' + r.status);
1800 |         return r.json();
1801 |       })
1802 |       .then(function(d) {
1803 |         var guideText = d.guidance_text || d.text || 'I can see your hardware device.';
1804 | 
1805 |         // Transaction verdict urgency
1806 |         if (d.verdict === 'DO NOT SIGN') {
1807 |           guideText = 'WARNING. DO NOT SIGN THIS TRANSACTION. ' + guideText;
1808 |         } else if (d.verdict === 'REVIEW CAREFULLY') {
1809 |           guideText = 'REVIEW CAREFULLY. ' + guideText;
1810 |         }
1811 | 
1812 |         // Transaction verdict ticker
1813 |         if (d.category === 'transaction' && d.verdict) {
1814 |           var verdictEmoji = d.verdict === 'SAFE TO SIGN' ? '✅'
1815 |             : d.verdict === 'DO NOT SIGN' ? '🚨' : '⚠️';
1816 |           tickerOracle(verdictEmoji + ' TX REVIEW: ' + d.verdict
1817 |             + (d.amount_btc ? ' — ' + d.amount_btc + ' BTC' : ''));
1818 |         }
1819 | 
1820 |         // Cap to 40 words for broadcast pacing
1821 |         var words = guideText.split(/\s+/);
1822 |         var spokenText = words.length > 40 ? words.slice(0,40).join(' ') : guideText;
1823 | 
1824 |         setStatus('SIGNAL answering viewer question…', 'var(--s-green)');
1825 |         tickerOracle('📷 Viewer hardware question: ' + (d.device_name || 'unknown device'));
1826 | 
1827 |         // Get TTS audio
1828 |         return fetchTO('https://avatar.protocolpulse.io/oracle/voice', {
1829 |           method: 'POST',
1830 |           headers: {'Content-Type': 'application/json'},
1831 |           body: JSON.stringify({text: spokenText})
1832 |         }, 35000);
1833 |       })
1834 |       .then(function(ar) {
1835 |         if (!ar.ok) throw new Error('voice failed');
1836 |         return ar.blob();
1837 |       })
1838 |       .then(function(blob) {
1839 |         var audioUrl = URL.createObjectURL(blob);
1840 |         var audio = new Audio(audioUrl);
1841 |         audio.volume = 1.0;
1842 |         audio.onended = function() {
1843 |           URL.revokeObjectURL(audioUrl);
1844 |           setBusy(false);
1845 |           _broadcastPaused = false;
1846 |           setStatus('Resuming broadcast…', 'var(--s-gold)');
1847 |           updateSignalSource('📡 RESUMING');
1848 |           setTimeout(function() {
1849 |             startBroadcast();
1850 |           }, 1500);
1851 |         };
1852 |         audio.onerror = function() {
1853 |           URL.revokeObjectURL(audioUrl);
1854 |           setBusy(false);
1855 |           _broadcastPaused = false;
1856 |           startBroadcast();
1857 |         };
1858 |         audio.play().catch(function() {
1859 |           setBusy(false);
1860 |           _broadcastPaused = false;
1861 |           startBroadcast();
1862 |         });
1863 |       })
1864 |       .catch(function(err) {
1865 |         console.error('[Stage camera] Error:', err);
1866 |         setBusy(false);
1867 |         _broadcastPaused = false;
1868 |         setStatus('Ready', 'rgba(255,255,255,.3)');
1869 |         startBroadcast();
1870 |       });
1871 | 
1872 |       // Clear input for reuse
1873 |       evt.target.value = '';
1874 |     };
1875 |     reader.readAsDataURL(file);
1876 |   }
1877 |   window.handleStageCameraUpload = handleStageCameraUpload;
1878 | 
1879 |   async function _handleInterruptQuestion(text) {
1880 |     setBusy(true);
1881 |     setStatus('Oracle thinking…', 'var(--s-gold)');
1882 |     updateSignalSource('🎤 RESPONDING TO LISTENER');
1883 | 
1884 |     try {
1885 |       var resp = await fetchTO('/api/oracle/chat', {
1886 |         method: 'POST',
1887 |         headers: {'Content-Type': 'application/json'},
1888 |         body: JSON.stringify({
1889 |           text: text,
1890 |           session_id: _stageSessionId,
1891 |           audio_first: true,
1892 |           avatar_source: 'stage_hologram',
1893 |           context: _currentBroadcastTopic
1894 |         })
1895 |       }, 90000);
1896 | 
1897 |       if (handle429(resp)) { setBusy(false); _resumeBroadcast(); return; }
1898 |       if (!resp.ok) throw new Error('HTTP ' + resp.status);
1899 | 
1900 |       var ct = resp.headers.get('content-type') || '';
1901 |       if (ct.indexOf('video') >= 0) {
1902 |         var blob = await resp.blob();
1903 |         var url = URL.createObjectURL(blob);
1904 |         await playVid(url);
1905 |       } else {
1906 |         var j = await resp.json();
1907 |         if (j.job_id) {
1908 |           // Poll for video
1909 |           var polls = 0;
1910 |           await new Promise(function(resolve) {
1911 |             var pollId = setInterval(function() {
1912 |               polls++;
1913 |               if (polls > 45) { clearInterval(pollId); resolve(); return; }
1914 |               fetch(AVATAR_BASE + '/oracle/job/' + j.job_id)
1915 |                 .then(function(vr) { if (vr.ok) return vr.blob(); return null; })
1916 |                 .then(function(vb) {
1917 |                   if (vb) {
1918 |                     clearInterval(pollId);
1919 |                     playVid(URL.createObjectURL(vb)).then(resolve);
1920 |                   }
1921 |                 }).catch(function(){});
1922 |             }, 1000);
1923 |           });
1924 |         }
1925 |       }
1926 |     } catch(e) {
1927 |       console.error('interrupt error:', e);
1928 |     }
1929 | 
1930 |     setBusy(false);
1931 |     // Resume broadcast after 3s countdown
1932 |     _showResumeCountdown();
1933 |   }
1934 | 
1935 |   function _showResumeCountdown() {
1936 |     var count = 3;
1937 |     setStatus('Returning to broadcast in ' + count + '…', 'var(--s-gold)');
1938 |     var cid = setInterval(function() {
1939 |       count--;
1940 |       if (count <= 0) {
1941 |         clearInterval(cid);
1942 |         _resumeBroadcast();
1943 |       } else {
1944 |         setStatus('Returning to broadcast in ' + count + '…', 'var(--s-gold)');
1945 |       }
1946 |     }, 1000);
1947 |   }
1948 | 
1949 |   function _resumeBroadcast() {
1950 |     _broadcastPaused = false;
1951 |     document.getElementById('interactivePanel').classList.remove('active');
1952 |     updateSignalSource('📡 RESUMING');
1953 |     startBroadcast();
1954 |   }
1955 | 
1956 |   // ── STAGE CHAT (text input) ───────────────────────────
1957 |   window.stageChat = function() {
1958 |     var input = document.getElementById('stageChatInput');
1959 |     var text = (input.value || '').trim();
1960 |     if(!text || busy) return;
1961 |     input.value = '';
1962 |     _handleInterruptQuestion(text);
1963 |   };
1964 | 
1965 |   function _appendChatMsg(text, role) {
1966 |     var hist = document.getElementById('stageChatHistory');
1967 |     var div = document.createElement('div');
1968 |     div.className = 'stage-chat-msg ' + role;
1969 |     div.textContent = text;
1970 |     hist.appendChild(div);
1971 |     hist.scrollTop = hist.scrollHeight;
1972 |   }
1973 | 
1974 |   function pulseStageMic() {
1975 |     var micBtn = document.getElementById('stageMicBtn');
1976 |     if(!micBtn || micBtn.disabled || _stageIsRec) return;
1977 |     micBtn.style.boxShadow = '0 0 0 8px rgba(255,59,95,.2)';
1978 |     setTimeout(function(){ micBtn.style.boxShadow = ''; }, 2000);
1979 |   }
1980 | 
1981 |   // ── BRIEFING COUNTDOWN ──────────────────────────────
1982 |   var _briefCountdownId = null;
1983 |   var _latestBriefUrl = null;
1984 |   var _hasUserInteracted = false;
1985 |   var _countdownRemaining = 0;
1986 | 
1987 |   document.addEventListener('click', function(){ _hasUserInteracted = true; }, {once:true});
1988 | 
1989 |   function loadBriefingSchedule(){
1990 |     fetch('/api/stage/next_briefing')
1991 |     .then(function(r){ return r.json(); })
1992 |     .then(function(d){
1993 |       if(!d.has_brief){
1994 |         safeText(document.getElementById('countdownTimer'), '\u2014');
1995 |         safeText(document.getElementById('countdownSub'), 'First brief coming soon');
1996 |         return;
1997 |       }
1998 |       _latestBriefUrl = d.last_brief.mp4_url;
1999 |       if(d.countdown_seconds <= 0){
2000 |         showBriefReady(d.last_brief);
2001 |       } else {
2002 |         startCountdown(d.countdown_seconds, d.last_brief);
2003 |       }
2004 |     })
2005 |     .catch(function(){
2006 |       safeText(document.getElementById('countdownSub'), 'Schedule unavailable');
2007 |     });
2008 |   }
2009 | 
2010 |   function startCountdown(seconds, lastBrief){
2011 |     if(_briefCountdownId) clearInterval(_briefCountdownId);
2012 |     _countdownRemaining = seconds;
2013 |     var timerEl = document.getElementById('countdownTimer');
2014 |     var subEl = document.getElementById('countdownSub');
2015 |     var dotEl = document.getElementById('briefDot');
2016 |     var playBtn = document.getElementById('briefPlayBtn');
2017 | 
2018 |     dotEl.classList.remove('ready');
2019 |     timerEl.classList.remove('ready');
2020 |     playBtn.style.display = 'none';
2021 |     safeText(subEl, lastBrief.title || 'Last brief loaded');
2022 | 
2023 |     function update(){
2024 |       if(_countdownRemaining <= 0){
2025 |         clearInterval(_briefCountdownId);
2026 |         showBriefReady(lastBrief);
2027 |         return;
2028 |       }
2029 |       var h = Math.floor(_countdownRemaining / 3600);
2030 |       var m = Math.floor((_countdownRemaining % 3600) / 60);
2031 |       var s = _countdownRemaining % 60;
2032 |       safeText(timerEl, pad(h) + ':' + pad(m) + ':' + pad(s));
2033 |       var bb = document.getElementById('betweenCountdown');
2034 |       if(bb) bb.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
2035 |       _countdownRemaining--;
2036 |     }
2037 |     update();
2038 |     _briefCountdownId = setInterval(update, 1000);
2039 |   }
2040 | 
2041 |   function pad(n){ return n < 10 ? '0'+n : ''+n; }
2042 | 
2043 |   function showBriefReady(brief){
2044 |     var timerEl = document.getElementById('countdownTimer');
2045 |     var dotEl = document.getElementById('briefDot');
2046 |     var playBtn = document.getElementById('briefPlayBtn');
2047 | 
2048 |     safeText(timerEl, 'NEW BRIEF');
2049 |     timerEl.classList.add('ready');
2050 |     dotEl.classList.add('ready');
2051 |     safeText(document.getElementById('countdownSub'), brief.title || 'Ready to play');
2052 |     playBtn.style.display = 'block';
2053 |     _latestBriefUrl = brief.mp4_url;
2054 |   }
2055 | 
2056 |   window.playLatestBrief = function(){
2057 |     if(busy) return;
2058 |     // If brief is a pre-rendered MP4 URL, play directly
2059 |     if(_latestBriefUrl && _latestBriefUrl.indexOf('.mp4') >= 0){
2060 |       setBusy(true);
2061 |       setStatus('Playing brief\u2026','var(--s-gold)');
2062 |       playVid(_latestBriefUrl).then(function(){ setBusy(false); });
2063 |       return;
2064 |     }
2065 |     // Otherwise fetch brief script and use monologue system
2066 |     fetch('/api/stage/intel').then(function(r){ return r.json(); }).then(function(d){
2067 |       var script = d.brief_script || d.summary || '';
2068 |       if(script && script.length > 30){
2069 |         playMonologue(script);
2070 |       } else {
2071 |         setStatus('No brief available','var(--s-gold)');
2072 |       }
2073 |     }).catch(function(){
2074 |       setStatus('Brief unavailable','var(--s-red)');
2075 |     });
2076 |   };
2077 | 
2078 |   // ── MONOLOGUE PLAYER — zero-gap chunk chaining ────────
2079 |   async function waitAndFetchChunk(jobId, idx) {
2080 |     var url = AVATAR_BASE + '/oracle/monologue/' + jobId + '/chunk/' + idx;
2081 |     for (var attempt = 0; attempt < 120; attempt++) {
2082 |       var r = await fetch(url);
2083 |       if (r.ok) return await r.blob();
2084 |       if (r.status !== 202) throw new Error('Chunk ' + idx + ' failed: ' + r.status);
2085 |       await new Promise(function(res) { setTimeout(res, 250); });
2086 |     }
2087 |     throw new Error('Chunk ' + idx + ' timed out');
2088 |   }
2089 | 
2090 |   async function playMonologue(script) {
2091 |     setBusy(true);
2092 |     setStatus('Preparing broadcast\u2026', 'var(--s-gold)');
2093 |     _broadcastPaused = true;
2094 | 
2095 |     try {
2096 |       var resp = await fetchTO(AVATAR_BASE + '/oracle/monologue', {
2097 |         method: 'POST',
2098 |         headers: {'Content-Type': 'application/json'},
2099 |         body: JSON.stringify({script: script})
2100 |       }, 8000);
2101 |       if (!resp.ok) throw new Error('Monologue submit failed');
2102 |       var job = await resp.json();
2103 |       var jobId = job.job_id;
2104 |       var total = job.total_chunks;
2105 | 
2106 |       var nextBlob = null;
2107 | 
2108 |       for (var i = 0; i < total; i++) {
2109 |         setStatus('Broadcasting ' + (i+1) + ' of ' + total + '\u2026', 'var(--s-green)');
2110 | 
2111 |         var blob;
2112 |         if (nextBlob) {
2113 |           blob = nextBlob;
2114 |           nextBlob = null;
2115 |         } else {
2116 |           blob = await waitAndFetchChunk(jobId, i);
2117 |         }
2118 | 
2119 |         var prefetchPromise = (i + 1 < total) ? waitAndFetchChunk(jobId, i + 1) : Promise.resolve(null);
2120 | 
2121 |         var blobUrl = URL.createObjectURL(blob);
2122 | 
2123 |         var prefetchDone = false;
2124 |         prefetchPromise.then(function(b) { nextBlob = b; prefetchDone = true; });
2125 | 
2126 |         await playVid(blobUrl);
2127 |         URL.revokeObjectURL(blobUrl);
2128 | 
2129 |         if (i + 1 < total && !prefetchDone) {
2130 |           setStatus('Buffering\u2026', 'var(--s-gold)');
2131 |           await new Promise(function(res) {
2132 |             var check = setInterval(function() {
2133 |               if (prefetchDone) { clearInterval(check); res(); }
2134 |             }, 100);
2135 |           });
2136 |         }
2137 |       }
2138 | 
2139 |     } catch(e) {
2140 |       console.error('playMonologue error:', e);
2141 |     } finally {
2142 |       setBusy(false);
2143 |       _broadcastPaused = false;
2144 |       setStatus('Ready', 'rgba(255,255,255,.3)');
2145 |       setTimeout(startBroadcast, 1000);
2146 |     }
2147 |   }
2148 |   window.playMonologue = playMonologue;
2149 | 
2150 |   // ── CONTINUOUS MONOLOGUE LOOP ─────────────────────────
2151 |   var _nextMonologueScript = null;
2152 |   var _nextMonologueJob = null;
2153 |   var _loopRunning = false;
2154 | 
2155 |   async function runMonologueLoop() {
2156 |     if (_loopRunning) return;
2157 |     _loopRunning = true;
2158 | 
2159 |     try {
2160 |       while (!_broadcastPaused) {
2161 |         var script = _nextMonologueScript;
2162 |         var preJob = _nextMonologueJob;
2163 |         _nextMonologueScript = null;
2164 |         _nextMonologueJob = null;
2165 | 
2166 |         if (!script) {
2167 |           setStatus('Generating broadcast\u2026', 'var(--s-gold)');
2168 |           script = await fetchMonologueScript();
2169 |         }
2170 |         if (!script || _broadcastPaused) break;
2171 | 
2172 |         var job;
2173 |         if (preJob) {
2174 |           job = preJob;
2175 |         } else {
2176 |           setStatus('Rendering\u2026', 'var(--s-gold)');
2177 |           try {
2178 |             var resp = await fetchTO(AVATAR_BASE + '/oracle/monologue', {
2179 |               method: 'POST',
2180 |               headers: {'Content-Type': 'application/json'},
2181 |               body: JSON.stringify({script: script})
2182 |             }, 15000);
2183 |             if (!resp.ok) throw new Error('monologue ' + resp.status);
2184 |             job = await resp.json();
2185 |           } catch(mErr) {
2186 |             // Fallback: render via /oracle/speak and play directly
2187 |             try {
2188 |               var speakResp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
2189 |                 method: 'POST',
2190 |                 headers: {'Content-Type': 'application/json'},
2191 |                 body: JSON.stringify({text: script, intent: 'BROADCAST_SEGMENT'})
2192 |               }, 120000);
2193 |               if (!speakResp.ok) { await sleep(3000); continue; }
2194 |               var blob = await speakResp.blob();
2195 |               var url = URL.createObjectURL(blob);
2196 |               await playVid(url);
2197 |               try { URL.revokeObjectURL(url); } catch(e) {}
2198 |               continue;
2199 |             } catch(sErr) {
2200 |               await sleep(3000); continue;
2201 |             }
2202 |           }
2203 |         }
2204 | 
2205 |         prefetchNextMonologue();
2206 | 
2207 |         await playMonologueJob(job);
2208 |       }
2209 |     } finally {
2210 |       _loopRunning = false;
2211 |     }
2212 |   }
2213 | 
2214 |   async function fetchMonologueScript() {
2215 |     try {
2216 |       var r = await fetchTO('/api/stage/generate-monologue', {
2217 |         method: 'POST', headers: {'Content-Type': 'application/json'}
2218 |       }, 25000);
2219 |       if (!r.ok) return null;
2220 |       var d = await r.json();
2221 |       updateTicker({topic_preview: 'Live Oracle Broadcast'});
2222 |       return d.script || null;
2223 |     } catch(e) { return null; }
2224 |   }
2225 | 
2226 |   async function prefetchNextMonologue() {
2227 |     try {
2228 |       var script = await fetchMonologueScript();
2229 |       if (!script) return;
2230 |       _nextMonologueScript = script;
2231 |       var resp = await fetchTO(AVATAR_BASE + '/oracle/monologue', {
2232 |         method: 'POST',
2233 |         headers: {'Content-Type': 'application/json'},
2234 |         body: JSON.stringify({script: script})
2235 |       }, 8000);
2236 |       if (resp.ok) {
2237 |         _nextMonologueJob = await resp.json();
2238 |       }
2239 |     } catch(e) {}
2240 |   }
2241 | 
2242 |   async function playMonologueJob(job) {
2243 |     var jobId = job.job_id;
2244 |     var total = job.total_chunks;
2245 |     var nextBlob = null;
2246 | 
2247 |     for (var i = 0; i < total; i++) {
2248 |       if (_broadcastPaused) break;
2249 |       setStatus('On Air \u00b7 ' + (i+1) + '/' + total, 'var(--s-green)');
2250 |       var badge = document.getElementById('stageModeBadge');
2251 |       if (badge) { badge.textContent = '\u25cf ON AIR'; badge.className = 'stage-mode-badge broadcast'; }
2252 | 
2253 |       var blob = nextBlob || await waitAndFetchChunk(jobId, i);
2254 |       nextBlob = null;
2255 | 
2256 |       var nextIdx = i + 1;
2257 |       if (nextIdx < total) {
2258 |         waitAndFetchChunk(jobId, nextIdx).then(function(b) { nextBlob = b; }).catch(function(){});
2259 |       }
2260 | 
2261 |       var url = URL.createObjectURL(blob);
2262 |       await playVid(url);
2263 |       try { URL.revokeObjectURL(url); } catch(e) {}
2264 |     }
2265 |   }
2266 | 
2267 |   function sleep(ms) { return new Promise(function(r){ setTimeout(r, ms); }); }
2268 | 
2269 |   // ── INIT ──────────────────────────────────────────────
2270 |   loadIntel();
2271 |   loadTranscripts();
2272 |   loadNostr();
2273 |   loadBriefingSchedule();
2274 | 
2275 |   // P1.4: Reduce polling to 30s
2276 |   setInterval(loadIntel, 30000);
2277 |   setInterval(loadNostr, 30000);
2278 |   setInterval(loadBriefingSchedule, 300000);
2279 | 
2280 |   // P0.4: Listen for custom event instead of monkey-patching
2281 |   function initTxDots(){
2282 |     var grid = document.getElementById('transcriptsGrid');
2283 |     var dotsEl = document.getElementById('txDots');
2284 |     if(!grid||!dotsEl) return;
2285 |     var cards = grid.children;
2286 |     if(!cards.length) return;
2287 |     if(window.innerWidth > 640){ dotsEl.style.display='none'; return; }
2288 |     dotsEl.innerHTML = '';
2289 |     var n = Math.min(cards.length, 8);
2290 |     for(var i=0;i<n;i++){
2291 |       var dot = document.createElement('span');
2292 |       if(i===0) dot.className='active';
2293 |       dotsEl.appendChild(dot);
2294 |     }
2295 |     grid.addEventListener('scroll', function(){
2296 |       var idx = Math.round(grid.scrollLeft / (grid.scrollWidth / n));
2297 |       var dots = dotsEl.children;
2298 |       for(var j=0;j<dots.length;j++) dots[j].className = j===idx?'active':'';
2299 |     }, {passive:true});
2300 |   }
2301 |   document.addEventListener('transcriptsRendered', function(){ setTimeout(initTxDots, 100); });
2302 | 
2303 |   // Pre-render first segment silently so it's ready when user taps
2304 |   preRenderFirstSegment();
2305 | 
2306 |   // Animate warming dots + flip label when pre-render is ready
2307 |   (function(){
2308 |     var dots = document.getElementById('stage-tap-dots');
2309 |     var label = document.getElementById('stage-tap-label');
2310 |     var dotCount = 1;
2311 |     var dotAnim = setInterval(function(){
2312 |       dotCount = (dotCount % 3) + 1;
2313 |       if (dots) dots.textContent = '.'.repeat(dotCount);
2314 |     }, 500);
2315 |     var _stageReadyPoller = setInterval(function(){
2316 |       if (_preRenderReady) {
2317 |         clearInterval(_stageReadyPoller);
2318 |         clearInterval(dotAnim);
2319 |         if (label) {
2320 |           label.textContent = 'TAP TO BEGIN BROADCAST';
2321 |           label.style.opacity = '1';
2322 |         }
2323 |         var ov = document.getElementById('stage-wake');
2324 |         if (ov) ov.classList.add('stage-wake-ready');
2325 |       }
2326 |     }, 1000);
2327 |   })();
2328 | 
2329 |   // Auto-play greeting on load — mobile gets tap overlay, desktop auto-starts
2330 |   setTimeout(function(){
2331 |     var _isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
2332 |     if(_isMobile) {
2333 |       // Show tap-to-start overlay on mobile — needed for autoplay unlock
2334 |       var ov = document.getElementById('stage-wake');
2335 |       if(ov) ov.style.display = 'flex';
2336 |     } else {
2337 |       startBroadcast();
2338 |     }
2339 |   }, 400);
2340 | 
2341 |   // Prevent iOS pinch-to-zoom
2342 |   document.addEventListener('gesturestart', function(e){ e.preventDefault(); }, {passive:false});
2343 |   document.addEventListener('touchmove', function(e){ if(e.touches.length>1) e.preventDefault(); }, {passive:false});
2344 | 
2345 | })();
2346 | </script>
2347 | {% endblock %}
2348 | 
```

### File: routes.py (extracted stage routes from 11357 lines)
```
8879 | @app.route('/api/stage/transcript')
8880 | def api_stage_transcript():
8881 |     """Live transcript + sentiment feed for the avatar stage.
8882 |     Returns latest entries from the daily episode if available,
8883 |     otherwise returns empty/offline state for demo fallback."""
8884 |     import json
8885 |     from datetime import datetime, date
8886 |     from pathlib import Path
8887 | 
8888 |     today = date.today().strftime('%Y-%m-%d')
8889 |     episode_dir = Path(__file__).resolve().parent / 'data' / 'episodes' / today
8890 | 
8891 |     entries = []
8892 |     stats = {"bullish": 0, "neutral": 0, "bearish": 0}
8893 |     topics = ["Bitcoin", "Markets", "Network"]
8894 |     is_live = False
8895 | 
8896 |     # Check for narration transcript first, then clips
8897 |     narration_path = episode_dir / 'narration' / 'transcript.json'
8898 |     clips_path     = episode_dir / 'clips' / 'clips.json'
8899 | 
8900 |     if narration_path.exists():
8901 |         try:
8902 |             data = json.loads(narration_path.read_text())
8903 |             for seg in data.get('segments', [])[:20]:
8904 |                 s = float(seg.get('sentiment', 0.0))
8905 |                 entries.append({
8906 |                     "text": seg.get('text', ''),
8907 |                     "sentiment_score": s,
8908 |                     "sentiment_label": "Bullish" if s > 0.3 else ("Bearish" if s < -0.3 else "Neutral"),
8909 |                     "timestamp": seg.get('time', datetime.now().strftime('%H:%M:%S')),
8910 |                 })
8911 |             is_live = True
8912 |         except Exception:
8913 |             pass
8914 |     elif clips_path.exists():
8915 |         try:
8916 |             data = json.loads(clips_path.read_text())
8917 |             for clip in data.get('clips', [])[:15]:
8918 |                 s = float(clip.get('sentiment_score', 0.0))
8919 |                 entries.append({
8920 |                     "text": clip.get('headline', clip.get('text', '')),
8921 |                     "sentiment_score": s,
8922 |                     "sentiment_label": "Bullish" if s > 0.3 else ("Bearish" if s < -0.3 else "Neutral"),
8923 |                     "timestamp": datetime.now().strftime('%H:%M:%S'),
8924 |                 })
8925 |             if entries:
8926 |                 is_live = True
8927 |         except Exception:
8928 |             pass
8929 | 
8930 |     # Compute sentiment stats
8931 |     if entries:
8932 |         scores = [e['sentiment_score'] for e in entries]
8933 |         total = len(scores)
8934 |         bullish = sum(1 for s in scores if s > 0.3)
8935 |         bearish = sum(1 for s in scores if s < -0.3)
8936 |         neutral = total - bullish - bearish
8937 |         stats = {
8938 |             "bullish": round(bullish / total * 100),
8939 |             "neutral": round(neutral / total * 100),
8940 |             "bearish": round(bearish / total * 100),
8941 |         }
8942 | 
8943 |     # Extract topics from source bundle if available
8944 |     sources_path = episode_dir / 'inputs' / 'source_bundle.json'
8945 |     if sources_path.exists():
8946 |         try:
8947 |             bundle = json.loads(sources_path.read_text())
8948 |             raw_topics = bundle.get('top_topics', [])
8949 |             if raw_topics:
8950 |                 topics = [str(t) for t in raw_topics[:3]]
8951 |         except Exception:
8952 |             pass
8953 | 
8954 |     return jsonify({
8955 |         "is_live": is_live,
8956 |         "entries": entries[-5:] if entries else [],
8957 |         "stats": stats,
8958 |         "topics": topics,
8959 |         "status": "Live Briefing" if is_live else "Demo Mode",
8960 |     })
8961 | 
8962 | 
8963 | # ─── NOSTR SIGNAL RADAR ──────────────────────────────────────────
8964 | # Real-time Bitcoin intelligence heatmap tracking top OGs on Nostr
8965 | 

# ... (other routes omitted) ...

11026 | @app.route('/api/stage/broadcast-queue')
11027 | @limiter.limit("30 per minute")

# ... (other routes omitted) ...

11064 | @app.route('/api/stage/consume-broadcast', methods=['POST'])
11065 | @limiter.limit("30 per minute")

# ... (other routes omitted) ...

11142 | @app.route('/api/stage/generate-monologue', methods=['POST'])
11143 | @limiter.limit("10 per minute")

# ... (other routes omitted) ...

11254 | @app.route('/api/stage/broadcast-status')
11255 | @limiter.limit("30 per minute")
```

### File: services/stage_broadcast_service.py (885 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | Stage Broadcast Service — Signal-driven queue for 24/7 autonomous Bitcoin broadcast.
   4 | 
   5 | Run via cron every 5 minutes:
   6 |   */5 * * * * python3 ~/protocol_pulse/services/stage_broadcast_service.py >> ~/protocol_pulse/logs/broadcast_service.log 2>&1
   7 | 
   8 | Polls 7 data sources, generates 30-90s spoken scripts via Claude Haiku,
   9 | writes to broadcast_queue.json with priority and TTL management.
  10 | """
  11 | 
  12 | import fcntl
  13 | import json
  14 | import logging
  15 | import os
  16 | import re
  17 | import sys
  18 | import time
  19 | import uuid
  20 | from datetime import datetime, timezone, timedelta
  21 | from pathlib import Path
  22 | 
  23 | import requests
  24 | 
  25 | # ---------------------------------------------------------------------------
  26 | # Paths
  27 | # ---------------------------------------------------------------------------
  28 | 
  29 | BASE = Path(__file__).resolve().parent.parent
  30 | QUEUE_PATH = BASE / "video_pipeline_v3" / "data" / "stage_briefs" / "broadcast_queue.json"
  31 | PRICE_CACHE = Path("/tmp/stage_last_price.json")
  32 | METRICS_CACHE = Path("/tmp/stage_last_metrics.json")
  33 | FILLER_STATE = BASE / "data" / "stage_briefs" / "filler_state.json"
  34 | LOGS_DIR = BASE / "logs"
  35 | DATA_DIR = BASE / "data"
  36 | 
  37 | CLAUDE_MODEL = "claude-haiku-4-5-20251001"
  38 | MAX_QUEUE_DEPTH = 15
  39 | 
  40 | # Local LLM offload — try Ollama on GPU 2 before Claude API
  41 | LOCAL_LLM_URL = "http://localhost:11435"
  42 | LOCAL_LLM_MODEL = os.environ.get("WATCHDOG_MODEL", "qwen3-coder:30b")
  43 | 
  44 | # ---------------------------------------------------------------------------
  45 | # Logging
  46 | # ---------------------------------------------------------------------------
  47 | 
  48 | LOGS_DIR.mkdir(exist_ok=True)
  49 | 
  50 | logger = logging.getLogger("stage_broadcast")
  51 | logger.setLevel(logging.INFO)
  52 | 
  53 | _fh = logging.FileHandler(str(LOGS_DIR / "broadcast_service.log"))
  54 | _fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
  55 | logger.addHandler(_fh)
  56 | 
  57 | _sh = logging.StreamHandler()
  58 | _sh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
  59 | logger.addHandler(_sh)
  60 | 
  61 | # ---------------------------------------------------------------------------
  62 | # API Key
  63 | # ---------------------------------------------------------------------------
  64 | 
  65 | def _get_anthropic_key():
  66 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
  67 |     if key:
  68 |         return key
  69 |     env_path = BASE / ".env"
  70 |     if env_path.exists():
  71 |         for line in env_path.read_text().splitlines():
  72 |             if line.startswith("ANTHROPIC_API_KEY="):
  73 |                 key = line.split("=", 1)[1].strip("'\"")
  74 |                 os.environ["ANTHROPIC_API_KEY"] = key
  75 |                 return key
  76 |     raise RuntimeError("ANTHROPIC_API_KEY not set")
  77 | 
  78 | 
  79 | # ---------------------------------------------------------------------------
  80 | # Queue Management (file-locked atomic operations)
  81 | # ---------------------------------------------------------------------------
  82 | 
  83 | def _read_queue():
  84 |     """Read queue with file lock."""
  85 |     if not QUEUE_PATH.exists():
  86 |         return []
  87 |     try:
  88 |         with open(QUEUE_PATH, "r") as f:
  89 |             fcntl.flock(f, fcntl.LOCK_SH)
  90 |             data = json.load(f)
  91 |             fcntl.flock(f, fcntl.LOCK_UN)
  92 |         return data if isinstance(data, list) else []
  93 |     except (json.JSONDecodeError, IOError):
  94 |         return []
  95 | 
  96 | 
  97 | def _write_queue(items):
  98 |     """Write queue with exclusive file lock."""
  99 |     QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
 100 |     with open(QUEUE_PATH, "w") as f:
 101 |         fcntl.flock(f, fcntl.LOCK_EX)
 102 |         json.dump(items, f, indent=2)
 103 |         fcntl.flock(f, fcntl.LOCK_UN)
 104 | 
 105 | 
 106 | def _cleanup_queue(items):
 107 |     """Remove expired items and enforce max depth."""
 108 |     now = datetime.now(timezone.utc)
 109 |     valid = []
 110 |     for item in items:
 111 |         try:
 112 |             expires = datetime.fromisoformat(item["expires_at"].replace("Z", "+00:00"))
 113 |             if expires > now:
 114 |                 valid.append(item)
 115 |         except (KeyError, ValueError):
 116 |             continue
 117 |     # Sort by priority (1=highest)
 118 |     valid.sort(key=lambda x: x.get("priority", 5))
 119 |     return valid[:MAX_QUEUE_DEPTH]
 120 | 
 121 | 
 122 | def _add_to_queue(item):
 123 |     """Add item to queue if not duplicate type within TTL window."""
 124 |     items = _read_queue()
 125 |     items = _cleanup_queue(items)
 126 | 
 127 |     # Prevent duplicate types (except FILLER_INSIGHT)
 128 |     if item["type"] != "FILLER_INSIGHT":
 129 |         for existing in items:
 130 |             if existing["type"] == item["type"]:
 131 |                 logger.info("Skipping duplicate %s already in queue", item["type"])
 132 |                 return items
 133 | 
 134 |     if len(items) >= MAX_QUEUE_DEPTH:
 135 |         # Drop lowest priority
 136 |         items = items[:MAX_QUEUE_DEPTH - 1]
 137 | 
 138 |     items.append(item)
 139 |     items = _cleanup_queue(items)
 140 |     _write_queue(items)
 141 |     logger.info("Queued %s (pri=%d): %s", item["type"], item["priority"],
 142 |                 item["topic_preview"][:60])
 143 |     return items
 144 | 
 145 | 
 146 | # ---------------------------------------------------------------------------
 147 | # Data Fetching (patterns from stage_brief_pipeline.py)
 148 | # ---------------------------------------------------------------------------
 149 | 
 150 | def _fetch_btc_price():
 151 |     """Fetch BTC price — internal API first, CoinGecko fallback."""
 152 |     # Try internal price API first (no rate limits)
 153 |     try:
 154 |         resp = requests.get("http://localhost:5000/api/btc-price", timeout=5)
 155 |         if resp.status_code == 200:
 156 |             d = resp.json()
 157 |             price = d.get("price") or d.get("bitcoin", {}).get("usd")
 158 |             change = d.get("change_24h") or d.get("bitcoin", {}).get("usd_24h_change", 0)
 159 |             if price:
 160 |                 return {
 161 |                     "price": float(price),
 162 |                     "change_24h": round(float(change), 2),
 163 |                     "market_cap": d.get("market_cap", 0),
 164 |                 }
 165 |     except Exception as e:
 166 |         logger.warning("Internal price API failed: %s", e)
 167 | 
 168 |     # Fallback to CoinGecko
 169 |     try:
 170 |         resp = requests.get(
 171 |             "https://api.coingecko.com/api/v3/simple/price",
 172 |             params={"ids": "bitcoin", "vs_currencies": "usd",
 173 |                     "include_24hr_change": "true", "include_market_cap": "true"},
 174 |             timeout=10
 175 |         )
 176 |         if resp.status_code == 200:
 177 |             d = resp.json().get("bitcoin", {})
 178 |             return {
 179 |                 "price": d.get("usd", 0),
 180 |                 "change_24h": round(d.get("usd_24h_change", 0), 2),
 181 |                 "market_cap": d.get("usd_market_cap", 0),
 182 |             }
 183 |     except Exception as e:
 184 |         logger.warning("CoinGecko failed: %s", e)
 185 | 
 186 |     return None
 187 | 
 188 | 
 189 | def _fetch_mempool():
 190 |     try:
 191 |         r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=10)
 192 |         r.raise_for_status()
 193 |         fees = r.json()
 194 |         r2 = requests.get("https://mempool.space/api/mempool", timeout=10)
 195 |         r2.raise_for_status()
 196 |         mp = r2.json()
 197 |         return {
 198 |             "fastest_fee": fees.get("fastestFee", 0),
 199 |             "hour_fee": fees.get("hourFee", 0),
 200 |             "tx_count": mp.get("count", 0),
 201 |         }
 202 |     except Exception as e:
 203 |         logger.warning("Mempool fetch failed: %s", e)
 204 |         return None
 205 | 
 206 | 
 207 | def _fetch_fear_greed():
 208 |     try:
 209 |         r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
 210 |         r.raise_for_status()
 211 |         d = r.json()["data"][0]
 212 |         return {"value": int(d["value"]), "label": d["value_classification"]}
 213 |     except Exception as e:
 214 |         logger.warning("FNG fetch failed: %s", e)
 215 |         return None
 216 | 
 217 | 
 218 | def _fetch_hashrate():
 219 |     try:
 220 |         r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=15)
 221 |         r.raise_for_status()
 222 |         hr = r.json().get("hashrates", [])
 223 |         current_hr = hr[-1]["avgHashrate"] if hr else 0
 224 |         return {"hashrate_eh": round(current_hr / 1e18, 1)}
 225 |     except Exception as e:
 226 |         logger.warning("Hashrate fetch failed: %s", e)
 227 |         return None
 228 | 
 229 | 
 230 | def _fetch_block_height():
 231 |     try:
 232 |         r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=10)
 233 |         r.raise_for_status()
 234 |         return int(r.text.strip())
 235 |     except Exception:
 236 |         return 0
 237 | 
 238 | 
 239 | # ---------------------------------------------------------------------------
 240 | # Script Generation via Claude Haiku
 241 | # ---------------------------------------------------------------------------
 242 | 
 243 | ANCHOR_SYSTEM = (
 244 |     "You are Oracle — the female anchor of Protocol Pulse, a 24/7 sovereign Bitcoin broadcast. "
 245 |     "IDENTITY: You see the world through an Austrian economics lens. You are NOT a financial analyst — "
 246 |     "you are a sovereign individual who understands mining, nodes, and the Bitcoin standard. "
 247 |     "EDITORIAL LAWS: "
 248 |     "Bitcoin ONLY. Never mention altcoins, crypto, DeFi, NFTs, or tokens. "
 249 |     "Never write BTC — always say Bitcoin in full. "
 250 |     "Never hedge. State facts directly. No 'could', 'might', 'it remains to be seen'. "
 251 |     "Respect the audience — they know what a UTXO is. Never explain basics. "
 252 |     "Cold delivery: single most important signal first. No warmup. No greeting. No sign-off. "
 253 |     "TONE: Authoritative, sharp, dry wit. Intelligence briefing energy. "
 254 |     "Think: intercepting a live signal — not reading a press release. "
 255 |     "NEVER say: 'interesting', 'really impactful', 'game changer', 'let's dive in', 'buckle up'. "
 256 |     "Every segment must contain ONE specific data point or on-chain metric. "
 257 |     "Under 30 words. Two sentences maximum. Punchy and direct. "
 258 |     "End with forward signal — what to watch next, not a summary of what was just said."
 259 | )
 260 | 
 261 | 
 262 | def _generate_script_local(prompt):
 263 |     """Try local Ollama first — zero API cost."""
 264 |     try:
 265 |         resp = requests.post(
 266 |             f"{LOCAL_LLM_URL}/api/chat",
 267 |             json={
 268 |                 "model": LOCAL_LLM_MODEL,
 269 |                 "messages": [
 270 |                     {"role": "system", "content": ANCHOR_SYSTEM},
 271 |                     {"role": "user", "content": prompt},
 272 |                 ],
 273 |                 "stream": False,
 274 |                 "options": {"temperature": 0.7},
 275 |             },
 276 |             timeout=15,
 277 |         )
 278 |         resp.raise_for_status()
 279 |         text = resp.json().get("message", {}).get("content", "").strip()
 280 |         if len(text) > 10:
 281 |             logger.info("Script generated via LOCAL LLM")
 282 |             return text
 283 |     except Exception as e:
 284 |         logger.info("Local LLM failed (%s), falling back to API", e)
 285 |     return None
 286 | 
 287 | 
 288 | def _generate_script(segment_type, context_data):
 289 |     """Generate a broadcast script — local Ollama first, Claude Haiku fallback."""
 290 |     prompt = f"Segment type: {segment_type}\n\nData:\n{json.dumps(context_data, indent=2)}\n\n"
 291 |     prompt += "Generate a spoken broadcast script based on this data."
 292 | 
 293 |     # Try local LLM first (free)
 294 |     local_result = _generate_script_local(prompt)
 295 |     if local_result:
 296 |         import re as _re
 297 |         local_result = _re.sub(r'^#+\s+[^\n]*\n?', '', local_result, flags=_re.MULTILINE)
 298 |         local_result = _re.sub(r'^---+\s*', '', local_result, flags=_re.MULTILINE)
 299 |         return local_result.strip()
 300 | 
 301 |     # Fallback to Claude Haiku API
 302 |     logger.info("Script generated via API (Claude Haiku)")
 303 |     api_key = _get_anthropic_key()
 304 | 
 305 |     resp = requests.post(
 306 |         "https://api.anthropic.com/v1/messages",
 307 |         headers={
 308 |             "x-api-key": api_key,
 309 |             "anthropic-version": "2023-06-01",
 310 |             "content-type": "application/json",
 311 |         },
 312 |         json={
 313 |             "model": CLAUDE_MODEL,
 314 |             "max_tokens": 80,
 315 |             "system": ANCHOR_SYSTEM,
 316 |             "messages": [{"role": "user", "content": prompt}],
 317 |         },
 318 |         timeout=30,
 319 |     )
 320 |     resp.raise_for_status()
 321 |     import re as _re
 322 |     text = resp.json()["content"][0]["text"].strip()
 323 |     text = _re.sub(r'^#+\s+[^\n]*\n?', '', text, flags=_re.MULTILINE)
 324 |     text = _re.sub(r'^---+\s*', '', text, flags=_re.MULTILINE)
 325 |     text = text.strip()
 326 |     return text
 327 | 
 328 | 
 329 | def _make_queue_item(seg_type, priority, script, source_label, topic_preview, ttl_minutes):
 330 |     now = datetime.now(timezone.utc)
 331 |     return {
 332 |         "id": str(uuid.uuid4()),
 333 |         "type": seg_type,
 334 |         "priority": priority,
 335 |         "script": script,
 336 |         "source_label": source_label,
 337 |         "topic_preview": topic_preview,
 338 |         "generated_at": now.isoformat(),
 339 |         "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
 340 |     }
 341 | 
 342 | 
 343 | # ---------------------------------------------------------------------------
 344 | # Signal Checks (7 types)
 345 | # ---------------------------------------------------------------------------
 346 | 
 347 | def check_price_alert(btc_data):
 348 |     """PRICE_ALERT (pri=1): >0.8% move from cached price."""
 349 |     if not btc_data:
 350 |         return None
 351 | 
 352 |     current_price = btc_data["price"]
 353 |     cached_price = 0
 354 | 
 355 |     if PRICE_CACHE.exists():
 356 |         try:
 357 |             cached = json.loads(PRICE_CACHE.read_text())
 358 |             cached_price = cached.get("price", 0)
 359 |         except (json.JSONDecodeError, IOError):
 360 |             pass
 361 | 
 362 |     # Always update cache
 363 |     PRICE_CACHE.write_text(json.dumps({"price": current_price,
 364 |                                         "timestamp": datetime.now(timezone.utc).isoformat()}))
 365 | 
 366 |     if cached_price <= 0:
 367 |         logger.info("Price cache initialized at $%s", f"{current_price:,.0f}")
 368 |         return None
 369 | 
 370 |     pct_change = abs((current_price - cached_price) / cached_price) * 100
 371 |     if pct_change < 0.8:
 372 |         return None
 373 | 
 374 |     direction = "up" if current_price > cached_price else "down"
 375 |     logger.info("PRICE_ALERT: $%s → $%s (%.1f%% %s)",
 376 |                 f"{cached_price:,.0f}", f"{current_price:,.0f}", pct_change, direction)
 377 | 
 378 |     script = _generate_script("PRICE_ALERT", {
 379 |         "previous_price": cached_price,
 380 |         "current_price": current_price,
 381 |         "percent_change": round(pct_change, 2),
 382 |         "direction": direction,
 383 |         "change_24h": btc_data["change_24h"],
 384 |     })
 385 | 
 386 |     return _make_queue_item(
 387 |         "PRICE_ALERT", 1, script,
 388 |         "📡 PRICE ALERT",
 389 |         f"Bitcoin {'breaks' if direction == 'up' else 'drops to'} ${current_price:,.0f}",
 390 |         30,
 391 |     )
 392 | 
 393 | 
 394 | def check_thought_leader():
 395 |     """THOUGHT_LEADER (pri=2): Priority-1 handles from raw_tweets.json."""
 396 |     PRIORITY_HANDLES = {
 397 |         "saylor", "natbrunell", "jack", "gladstein", "prestonpysh",
 398 |         "martybent", "lynaldencontact", "jeffbooth", "odell", "aantonop", "adam3us",
 399 |     }
 400 | 
 401 |     tweets_path = DATA_DIR / "tweet_study" / "raw_tweets.json"
 402 |     if not tweets_path.exists():
 403 |         return None
 404 | 
 405 |     try:
 406 |         tweets = json.loads(tweets_path.read_text())
 407 |         if not isinstance(tweets, list):
 408 |             return None
 409 | 
 410 |         now = datetime.now(timezone.utc)
 411 |         cutoff = now - timedelta(hours=72)
 412 | 
 413 |         import random
 414 |         tweets_shuffled = tweets.copy()
 415 |         random.shuffle(tweets_shuffled)
 416 | 
 417 |         for tweet in tweets_shuffled:
 418 |             handle = (tweet.get("handle") or tweet.get("username") or "").lower().lstrip("@")
 419 |             if handle not in PRIORITY_HANDLES:
 420 |                 continue
 421 | 
 422 |             created = tweet.get("created_at") or tweet.get("timestamp") or ""
 423 |             if created:
 424 |                 try:
 425 |                     tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
 426 |                     if tweet_time < cutoff:
 427 |                         continue
 428 |                 except (ValueError, TypeError):
 429 |                     pass
 430 | 
 431 |             text = tweet.get("text") or tweet.get("content") or ""
 432 |             if len(text) < 30:
 433 |                 continue
 434 | 
 435 |             logger.info("THOUGHT_LEADER: @%s — %s", handle, text[:80])
 436 |             script = _generate_script("THOUGHT_LEADER", {
 437 |                 "handle": handle,
 438 |                 "tweet_text": text[:500],
 439 |                 "context": "Priority Bitcoin thought leader tweet",
 440 |             })
 441 | 
 442 |             return _make_queue_item(
 443 |                 "THOUGHT_LEADER", 2, script,
 444 |                 f"🧠 @{handle.upper()}",
 445 |                 text[:80],
 446 |                 120,
 447 |             )
 448 |     except Exception as e:
 449 |         logger.warning("Thought leader check failed: %s", e)
 450 | 
 451 |     return None
 452 | 
 453 | 
 454 | def check_space_tap():
 455 |     """SPACE_TAP (pri=2): Fresh X Spaces clips."""
 456 |     spaces_cache = BASE / "x_spaces_scraper" / "cache"
 457 |     if not spaces_cache.exists():
 458 |         return None
 459 | 
 460 |     try:
 461 |         cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
 462 |         for f in sorted(spaces_cache.glob("*.json"), reverse=True):
 463 |             if f.name == "last_run.json":
 464 |                 continue
 465 |             mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
 466 |             if mtime < cutoff:
 467 |                 continue
 468 | 
 469 |             data = json.loads(f.read_text())
 470 |             title = data.get("space_title") or data.get("title") or "Live Space"
 471 |             transcript = data.get("transcript") or data.get("text") or ""
 472 |             if len(transcript) < 50:
 473 |                 continue
 474 | 
 475 |             logger.info("SPACE_TAP: %s", title[:60])
 476 |             script = _generate_script("SPACE_TAP", {
 477 |                 "space_title": title,
 478 |                 "transcript_excerpt": transcript[:800],
 479 |                 "context": "We intercepted a live Bitcoin space — here's the key signal.",
 480 |             })
 481 | 
 482 |             return _make_queue_item(
 483 |                 "SPACE_TAP", 2, script,
 484 |                 "🎙️ SPACE TAP",
 485 |                 title[:80],
 486 |                 240,
 487 |             )
 488 |     except Exception as e:
 489 |         logger.warning("Space tap check failed: %s", e)
 490 | 
 491 |     return None
 492 | 
 493 | 
 494 | def check_article_teaser():
 495 |     """ARTICLE_TEASER (pri=3): Recent articles from DB."""
 496 |     db_path = BASE / "instance" / "protocol_pulse.db"
 497 |     if not db_path.exists():
 498 |         return None
 499 | 
 500 |     try:
 501 |         import sqlite3
 502 |         conn = sqlite3.connect(str(db_path))
 503 |         conn.row_factory = sqlite3.Row
 504 |         cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
 505 |         row = conn.execute(
 506 |             "SELECT title, summary FROM articles WHERE created_at > ? ORDER BY RANDOM() LIMIT 1",
 507 |             (cutoff,)
 508 |         ).fetchone()
 509 |         conn.close()
 510 | 
 511 |         if not row:
 512 |             return None
 513 | 
 514 |         title = row["title"]
 515 |         summary = row["summary"] or ""
 516 |         logger.info("ARTICLE_TEASER: %s", title[:60])
 517 | 
 518 |         script = _generate_script("ARTICLE_TEASER", {
 519 |             "article_title": title,
 520 |             "article_summary": summary,
 521 |             "context": "Fresh from our editorial desk — tease this article without giving everything away.",
 522 |         })
 523 | 
 524 |         return _make_queue_item(
 525 |             "ARTICLE_TEASER", 3, script,
 526 |             "📰 FRESH INTEL",
 527 |             title[:80],
 528 |             240,
 529 |         )
 530 |     except Exception as e:
 531 |         logger.warning("Article teaser check failed: %s", e)
 532 |         return None
 533 | 
 534 | 
 535 | def check_metrics_pulse(btc_data):
 536 |     """METRICS_PULSE (pri=3): Network metrics every 20+ minutes."""
 537 |     if METRICS_CACHE.exists():
 538 |         try:
 539 |             cached = json.loads(METRICS_CACHE.read_text())
 540 |             last_ts = datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
 541 |             if datetime.now(timezone.utc) - last_ts < timedelta(minutes=20):
 542 |                 return None
 543 |         except (json.JSONDecodeError, KeyError, ValueError):
 544 |             pass
 545 | 
 546 |     hashrate = _fetch_hashrate()
 547 |     fng = _fetch_fear_greed()
 548 |     mempool = _fetch_mempool()
 549 |     block_height = _fetch_block_height()
 550 | 
 551 |     if not any([hashrate, fng, mempool]):
 552 |         return None
 553 | 
 554 |     metrics = {
 555 |         "btc_price": btc_data["price"] if btc_data else 0,
 556 |         "change_24h": btc_data["change_24h"] if btc_data else 0,
 557 |         "hashrate_eh": hashrate["hashrate_eh"] if hashrate else 0,
 558 |         "fng_value": fng["value"] if fng else 50,
 559 |         "fng_label": fng["label"] if fng else "Neutral",
 560 |         "fastest_fee": mempool["fastest_fee"] if mempool else 0,
 561 |         "tx_count": mempool["tx_count"] if mempool else 0,
 562 |         "block_height": block_height,
 563 |     }
 564 | 
 565 |     METRICS_CACHE.write_text(json.dumps({
 566 |         "timestamp": datetime.now(timezone.utc).isoformat(),
 567 |         **metrics,
 568 |     }))
 569 | 
 570 |     logger.info("METRICS_PULSE: BTC $%s, FNG %s, Hash %s EH/s",
 571 |                 f"{metrics['btc_price']:,.0f}", metrics["fng_value"], metrics["hashrate_eh"])
 572 | 
 573 |     script = _generate_script("METRICS_PULSE", metrics)
 574 | 
 575 |     return _make_queue_item(
 576 |         "METRICS_PULSE", 3, script,
 577 |         "📊 METRICS PULSE",
 578 |         f"BTC ${metrics['btc_price']:,.0f} · FNG {metrics['fng_value']} · {metrics['hashrate_eh']} EH/s",
 579 |         240,
 580 |     )
 581 | 
 582 | 
 583 | def check_nostr_signal():
 584 |     """NOSTR_SIGNAL (pri=4): Narrative from Nostr discourse."""
 585 |     narrative_path = BASE / "video_pipeline_v3" / "data" / "intelligence" / "narrative_context.json"
 586 |     if not narrative_path.exists():
 587 |         return None
 588 | 
 589 |     try:
 590 |         data = json.loads(narrative_path.read_text())
 591 |         narrative = data.get("dominant_narrative") or data.get("narrative") or ""
 592 |         if not narrative:
 593 |             return None
 594 | 
 595 |         updated = data.get("updated_at") or data.get("generated_at") or ""
 596 |         if updated:
 597 |             try:
 598 |                 update_time = datetime.fromisoformat(updated.replace("Z", "+00:00"))
 599 |                 if datetime.now(timezone.utc) - update_time > timedelta(hours=4):
 600 |                     return None
 601 |             except (ValueError, TypeError):
 602 |                 pass
 603 | 
 604 |         logger.info("NOSTR_SIGNAL: %s", narrative[:60])
 605 |         script = _generate_script("NOSTR_SIGNAL", {
 606 |             "dominant_narrative": narrative,
 607 |             "themes": data.get("themes", []),
 608 |             "context": "This is the dominant discourse emerging from Bitcoin Nostr relays right now.",
 609 |         })
 610 | 
 611 |         return _make_queue_item(
 612 |             "NOSTR_SIGNAL", 4, script,
 613 |             "⚡ NOSTR SIGNAL",
 614 |             narrative[:80],
 615 |             240,
 616 |         )
 617 |     except Exception as e:
 618 |         logger.warning("Nostr signal check failed: %s", e)
 619 |         return None
 620 | 
 621 | 
 622 | # ---------------------------------------------------------------------------
 623 | # Filler Insights (20 pre-written, never repeat consecutively)
 624 | # ---------------------------------------------------------------------------
 625 | 
 626 | FILLER_INSIGHTS = [
 627 |     "Bitcoin is the only monetary network in history that operates with zero counterparty risk. Every ten minutes, a new block confirms that no single entity controls the ledger. That's not a feature — that's a paradigm shift in how humans coordinate value across trust boundaries.",
 628 |     "The Lightning Network processed more transactions last month than the entire Bitcoin base layer did in its first four years. Layer-two scaling isn't theoretical anymore — it's quietly becoming the rails for instant, near-free payments worldwide.",
 629 |     "Satoshi Nakamoto's last known communication was in December 2010. Fifteen years later, the protocol runs exactly as designed. No CEO, no board meetings, no emergency patches. The code is the constitution.",
 630 |     "Hash rate is the most honest signal in Bitcoin. Miners don't speculate — they commit capital, electricity, and hardware. When hash rate climbs to all-time highs, it means serious operators are betting their balance sheets on Bitcoin's future.",
 631 |     "There are only 21 million bitcoin. That's not a soft cap, not a target — it's a mathematical certainty enforced by every node on the network. In a world of infinite money printing, scarcity is the ultimate signal.",
 632 |     "The mempool is Bitcoin's waiting room. When fees spike, it means demand for block space exceeds supply. That's not a bug — it's proof that people value the security of final settlement enough to pay for it.",
 633 |     "Every four years, the block subsidy cuts in half. This halving mechanism is the most predictable monetary policy in human history. No central banker can override it. No politician can delay it.",
 634 |     "Running a full node costs less than a streaming subscription. For that price, you independently verify every transaction since the genesis block. That's sovereignty you can run on a Raspberry Pi.",
 635 |     "Bitcoin's difficulty adjustment is an engineering marvel. Every 2,016 blocks, the network recalibrates to maintain ten-minute block intervals regardless of how much hash power joins or leaves. Self-regulating monetary infrastructure.",
 636 |     "The Bitcoin network has been operational for over 99.98 percent of its existence. No bank, no government system, no tech company can match that uptime. Decentralization isn't just philosophy — it's resilience.",
 637 |     "Multisig wallets eliminate single points of failure. A two-of-three setup means no single key compromise can drain your funds. This is how institutions are beginning to custody billions in bitcoin.",
 638 |     "Bitcoin mining is increasingly powered by stranded energy — gas flares, excess hydro, curtailed wind and solar. Miners are becoming the buyer of last resort for energy that would otherwise be wasted.",
 639 |     "The UTXO model is Bitcoin's secret weapon for privacy and scalability. Unlike account-based systems, every transaction output is independent — enabling parallel validation and coin-level audit trails.",
 640 |     "Nostr is building the decentralized social layer that Bitcoin's monetary layer always needed. Censorship-resistant communication plus censorship-resistant money — that's the full stack of digital sovereignty.",
 641 |     "Time-chain analysis shows that long-term holders — wallets dormant for one year or more — consistently hold over sixty percent of all bitcoin supply. The conviction of this network's participants is unprecedented.",
 642 |     "Bitcoin script is intentionally limited. No Turing completeness, no complex smart contracts on the base layer. This constraint is a security feature — the monetary layer should be boring and bulletproof.",
 643 |     "The genesis block contains a Times headline about bank bailouts. Satoshi didn't just build software — they embedded a permanent protest against monetary manipulation into the first block ever mined.",
 644 |     "Coinjoin transactions are growing month over month. Privacy isn't optional in a sound money system — it's essential. Financial surveillance is incompatible with individual sovereignty.",
 645 |     "Bitcoin's energy consumption is a feature, not a bug. Proof of work converts physical energy into digital security. The cost of attacking the network must always exceed the cost of defending it.",
 646 |     "Every bitcoin transaction is a voluntary exchange. No chargebacks, no intermediaries, no permission required. For the first time in digital history, we have bearer assets that move at the speed of light.",
 647 | ]
 648 | 
 649 | 
 650 | def _generate_live_filler():
 651 |     """Generate a live Bitcoin intelligence filler segment using current data."""
 652 |     try:
 653 |         btc_data = _fetch_btc_price() or {}
 654 |         mempool = _fetch_mempool() or {}
 655 |         hashrate = _fetch_hashrate()
 656 |         fng = _fetch_fear_greed()
 657 | 
 658 |         price = btc_data.get("price", 0)
 659 |         change = btc_data.get("change_24h", 0)
 660 |         fee = mempool.get("fastest_fee", 0)
 661 |         hr = hashrate.get("hashrate_eh", 0) if hashrate else 0
 662 |         fg = fng.get("value", 0) if fng else 0
 663 | 
 664 |         context = f"""Current Bitcoin data:
 665 | - Price: ${price:,.0f} ({change:+.1f}% 24h)
 666 | - Fear & Greed: {fg}/100
 667 | - Hashrate: {hr:.0f} EH/s
 668 | - Mempool fast fee: {fee} sat/vbyte"""
 669 | 
 670 |         prompt = (
 671 |             f"{context}\n\n"
 672 |             "Write a 40-60 word spoken Bitcoin intelligence broadcast segment. "
 673 |             "Cold open with the most important signal from the data above. "
 674 |             "Austrian economics worldview. Sovereign individual framing. "
 675 |             "No greeting, no sign-off, no hedging. "
 676 |             "Bitcoin only. Never say 'BTC'. Never say 'interesting'. "
 677 |             "Every sentence must earn its place. "
 678 |             "End with a forward-looking statement."
 679 |         )
 680 |         script = _generate_script_local(prompt)
 681 |         if script and len(script) > 30:
 682 |             return script
 683 |     except Exception as e:
 684 |         logger.warning("[FILLER] _generate_live_filler error: %s", e)
 685 |     return None
 686 | 
 687 | 
 688 | def get_filler_insight():
 689 |     """Get next filler insight — live AI generation with static fallback."""
 690 |     last_idx = -1
 691 |     last_generated = 0
 692 |     if FILLER_STATE.exists():
 693 |         try:
 694 |             state = json.loads(FILLER_STATE.read_text())
 695 |             last_idx = state.get("idx", -1)
 696 |             last_generated = state.get("last_generated", 0)
 697 |         except (json.JSONDecodeError, IOError):
 698 |             pass
 699 | 
 700 |     # Ensure state directory exists
 701 |     FILLER_STATE.parent.mkdir(parents=True, exist_ok=True)
 702 | 
 703 |     # Try live AI generation if >30 min since last AI filler
 704 |     now_ts = time.time()
 705 |     if now_ts - last_generated > 1800:
 706 |         try:
 707 |             live_script = _generate_live_filler()
 708 |             if live_script:
 709 |                 FILLER_STATE.write_text(json.dumps({
 710 |                     "idx": last_idx,
 711 |                     "last_generated": now_ts
 712 |                 }))
 713 |                 logger.info("[FILLER] Live AI filler generated")
 714 |                 return _make_queue_item(
 715 |                     "FILLER_INSIGHT", 5, live_script,
 716 |                     "⚡ LIVE INSIGHT",
 717 |                     live_script[:80],
 718 |                     120,
 719 |                 )
 720 |         except Exception as e:
 721 |             logger.warning("[FILLER] Live generation failed, using static: %s", e)
 722 | 
 723 |     # Fall back to static rotation
 724 |     next_idx = (last_idx + 1) % len(FILLER_INSIGHTS)
 725 |     FILLER_STATE.write_text(json.dumps({
 726 |         "idx": next_idx,
 727 |         "last_generated": last_generated
 728 |     }))
 729 |     script = FILLER_INSIGHTS[next_idx]
 730 |     return _make_queue_item(
 731 |         "FILLER_INSIGHT", 5, script,
 732 |         "💡 INSIGHT",
 733 |         script[:80],
 734 |         240,
 735 |     )
 736 | 
 737 | 
 738 | def generate_filler_live():
 739 |     """Generate a filler insight for immediate use (called by consume endpoint)."""
 740 |     return get_filler_insight()
 741 | 
 742 | 
 743 | # ---------------------------------------------------------------------------
 744 | # Main Pipeline
 745 | # ---------------------------------------------------------------------------
 746 | 
 747 | def run():
 748 |     """Main broadcast service run — called by cron every 5 minutes."""
 749 |     t0 = time.time()
 750 |     logger.info("=" * 50)
 751 |     logger.info("BROADCAST SERVICE RUN — %s", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
 752 |     logger.info("=" * 50)
 753 | 
 754 |     # Clean expired items first
 755 |     items = _read_queue()
 756 |     items = _cleanup_queue(items)
 757 |     _write_queue(items)
 758 |     logger.info("Queue depth after cleanup: %d", len(items))
 759 | 
 760 |     # Fetch BTC price (shared across checks)
 761 |     btc_data = _fetch_btc_price()
 762 | 
 763 |     # Run signal checks in priority order
 764 |     new_items = 0
 765 | 
 766 |     # 1. PRICE_ALERT (pri=1)
 767 |     try:
 768 |         item = check_price_alert(btc_data)
 769 |         if item:
 770 |             _add_to_queue(item)
 771 |             new_items += 1
 772 |     except Exception as e:
 773 |         logger.error("Price alert check error: %s", e)
 774 | 
 775 |     # 2. THOUGHT_LEADER (pri=2) — max 1 per run
 776 |     try:
 777 |         item = check_thought_leader()
 778 |         if item:
 779 |             _add_to_queue(item)
 780 |             new_items += 1
 781 |     except Exception as e:
 782 |         logger.error("Thought leader check error: %s", e)
 783 | 
 784 |     # 3. SPACE_TAP (pri=2)
 785 |     try:
 786 |         item = check_space_tap()
 787 |         if item:
 788 |             _add_to_queue(item)
 789 |             new_items += 1
 790 |     except Exception as e:
 791 |         logger.error("Space tap check error: %s", e)
 792 | 
 793 |     # 4. ARTICLE_TEASER (pri=3)
 794 |     try:
 795 |         item = check_article_teaser()
 796 |         if item:
 797 |             _add_to_queue(item)
 798 |             new_items += 1
 799 |     except Exception as e:
 800 |         logger.error("Article teaser check error: %s", e)
 801 | 
 802 |     # 5. METRICS_PULSE (pri=3)
 803 |     try:
 804 |         item = check_metrics_pulse(btc_data)
 805 |         if item:
 806 |             _add_to_queue(item)
 807 |             new_items += 1
 808 |     except Exception as e:
 809 |         logger.error("Metrics pulse check error: %s", e)
 810 | 
 811 |     # 6. NOSTR_SIGNAL (pri=4)
 812 |     try:
 813 |         item = check_nostr_signal()
 814 |         if item:
 815 |             _add_to_queue(item)
 816 |             new_items += 1
 817 |     except Exception as e:
 818 |         logger.error("Nostr signal check error: %s", e)
 819 | 
 820 |     # 7. FILLER_INSIGHT (pri=5) — keep queue topped up to at least 4 items
 821 |     final_queue = _read_queue()
 822 |     final_queue = _cleanup_queue(final_queue)
 823 |     filler_added = 0
 824 |     while len(final_queue) < 4 and filler_added < 3:
 825 |         filler = get_filler_insight()
 826 |         _add_to_queue(filler)
 827 |         final_queue = _read_queue()
 828 |         final_queue = _cleanup_queue(final_queue)
 829 |         filler_added += 1
 830 |         logger.info("Added filler insight (%d in queue)", len(final_queue))
 831 | 
 832 |     final_queue = _read_queue()
 833 |     final_queue = _cleanup_queue(final_queue)
 834 |     elapsed = round(time.time() - t0, 1)
 835 |     logger.info("Run complete in %ss — %d new items, queue depth: %d",
 836 |                 elapsed, new_items, len(final_queue))
 837 | 
 838 |     return len(final_queue)
 839 | 
 840 | 
 841 | # ---------------------------------------------------------------------------
 842 | # CLI
 843 | # ---------------------------------------------------------------------------
 844 | 
 845 | if __name__ == "__main__":
 846 |     if "--prefill" in sys.argv:
 847 |         # Pre-fill queue with 8 items for low-traffic hours
 848 |         logger.info("PREFILL MODE — building deep queue")
 849 |         btc_data = _fetch_btc_price()
 850 |         prefill_count = 0
 851 |         # Try all signal types first
 852 |         for check_fn, args in [
 853 |             (check_metrics_pulse, (btc_data,)),
 854 |             (check_article_teaser, ()),
 855 |             (check_nostr_signal, ()),
 856 |             (check_thought_leader, ()),
 857 |             (check_article_teaser, ()),
 858 |             (check_nostr_signal, ()),
 859 |             (check_metrics_pulse, (btc_data,)),
 860 |             (check_article_teaser, ()),
 861 |         ]:
 862 |             try:
 863 |                 q = _read_queue()
 864 |                 if len(q) >= MAX_QUEUE_DEPTH:
 865 |                     break
 866 |                 item = check_fn(*args)
 867 |                 if item:
 868 |                     _add_to_queue(item)
 869 |                     prefill_count += 1
 870 |                     time.sleep(2)  # brief pause between API calls
 871 |             except Exception as e:
 872 |                 logger.warning("Prefill check error: %s", e)
 873 |         # Top up with live filler to reach 8 items
 874 |         q = _read_queue()
 875 |         while len(q) < 8:
 876 |             _add_to_queue(get_filler_insight())
 877 |             q = _read_queue()
 878 |             prefill_count += 1
 879 |         logger.info("PREFILL COMPLETE — %d items added, queue depth: %d",
 880 |                     prefill_count, len(_read_queue()))
 881 |     else:
 882 |         depth = run()
 883 |         print(f"Queue depth: {depth}")
 884 |         sys.exit(0)
 885 | 
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

