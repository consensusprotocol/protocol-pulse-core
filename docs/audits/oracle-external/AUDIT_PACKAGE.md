# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: oracle-external
# Branch: main
# Generated: 2026-03-25 21:20 UTC
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

### File: templates/oracle_live.html (2379 lines)
```
   1 | <!DOCTYPE html>
   2 | <html lang="en">
   3 | <head>
   4 | <meta charset="UTF-8">
   5 | <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover,interactive-widget=resizes-content">
   6 | <meta name="theme-color" content="#000">
   7 | <meta name="apple-mobile-web-app-capable" content="yes">
   8 | <meta name="apple-mobile-web-app-status-bar-style" content="black">
   9 | <meta http-equiv="Permissions-Policy" content="microphone=*, camera=*">
  10 | <title>Satomi · Protocol Pulse</title>
  11 | <link rel="preconnect" href="https://fonts.googleapis.com">
  12 | <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  13 | <link rel="preload" href="/oracle/thinking" as="video" type="video/mp4">
  14 | <style>
  15 | *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
  16 | html,body{height:100%;width:100%;background:#000;overflow:hidden;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}
  17 | 
  18 | /* ─── KEYFRAMES ─────────────────────────────────────────── */
  19 | @keyframes orbit{to{transform:rotate(360deg)}}
  20 | @keyframes orbit-rev{to{transform:rotate(-360deg)}}
  21 | @keyframes breathe{0%,100%{opacity:.6;transform:scale(1)}50%{opacity:1;transform:scale(1.04)}}
  22 | @keyframes scan{0%{top:-4px}100%{top:100%}}
  23 | @keyframes live-blink{0%,100%{opacity:1}49%{opacity:1}50%,99%{opacity:.15}}
  24 | @keyframes fade-up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
  25 | @keyframes mic-pulse{0%{box-shadow:0 0 0 0 rgba(255,59,95,.6)}70%{box-shadow:0 0 0 22px rgba(255,59,95,0)}100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}}
  26 | @keyframes mic-idle-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}50%{box-shadow:0 0 0 14px rgba(255,59,95,.22),0 0 18px 4px rgba(255,59,95,.12)}}
  27 | @keyframes spin{to{transform:rotate(360deg)}}
  28 | @keyframes card-up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  29 | @keyframes hex-glow{0%,100%{filter:drop-shadow(0 0 8px rgba(255,59,95,.4))}50%{filter:drop-shadow(0 0 22px rgba(255,59,95,.9))}}
  30 | 
  31 | /* ─── ROOT ──────────────────────────────────────────────── */
  32 | #root{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden}
  33 | 
  34 | /* ─── BACKGROUND GRID ───────────────────────────────────── */
  35 | #root::before{
  36 |   content:'';position:absolute;inset:0;
  37 |   background-image:linear-gradient(rgba(255,59,95,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,59,95,.04) 1px,transparent 1px);
  38 |   background-size:40px 40px;
  39 |   mask-image:radial-gradient(ellipse 80% 80% at 50% 50%,black 40%,transparent 100%);
  40 |   pointer-events:none;
  41 | }
  42 | 
  43 | /* ═══════════════════════════════════════════════════════════
  44 |    GATE SCREEN
  45 | ═══════════════════════════════════════════════════════════ */
  46 | #gate{
  47 |   display:flex;flex-direction:column;align-items:center;
  48 |   gap:clamp(18px,4vw,28px);
  49 |   padding:clamp(24px,5vw,48px) clamp(24px,5vw,48px);
  50 |   width:100%;max-width:520px;
  51 |   transition:opacity .35s ease;
  52 | }
  53 | 
  54 | /* Satomi sigil */
  55 | .sigil-wrap{
  56 |   position:relative;
  57 |   width:clamp(140px,38vw,200px);
  58 |   height:clamp(140px,38vw,200px);
  59 |   flex-shrink:0;
  60 | }
  61 | /* Rotating rings */
  62 | .ring{
  63 |   position:absolute;inset:0;
  64 |   border-radius:50%;
  65 |   border:1px solid rgba(255,59,95,.25);
  66 | }
  67 | .ring-1{animation:orbit 12s linear infinite}
  68 | .ring-1::before{
  69 |   content:'';position:absolute;
  70 |   width:6px;height:6px;background:#ff3b5f;border-radius:50%;
  71 |   top:-3px;left:50%;transform:translateX(-50%);
  72 |   box-shadow:0 0 8px #ff3b5f;
  73 | }
  74 | .ring-2{
  75 |   inset:12%;border-color:rgba(255,180,50,.2);
  76 |   animation:orbit-rev 8s linear infinite;
  77 | }
  78 | .ring-2::before{
  79 |   content:'';position:absolute;
  80 |   width:4px;height:4px;background:#f8c15c;border-radius:50%;
  81 |   bottom:-2px;left:50%;transform:translateX(-50%);
  82 |   box-shadow:0 0 6px #f8c15c;
  83 | }
  84 | /* Avatar in center */
  85 | .sigil-avatar{
  86 |   position:absolute;
  87 |   inset:18%;
  88 |   border-radius:50%;
  89 |   overflow:hidden;
  90 |   background:radial-gradient(circle,#1a0608 0%,#050203 100%);
  91 |   border:1px solid rgba(255,59,95,.3);
  92 |   animation:breathe 3.5s ease-in-out infinite;
  93 | }
  94 | .sigil-avatar img{width:100%;height:100%;object-fit:cover;display:block;border-radius:50%}
  95 | .sigil-fallback{
  96 |   width:100%;height:100%;border-radius:50%;
  97 |   display:flex;align-items:center;justify-content:center;
  98 |   font-size:clamp(28px,8vw,44px);
  99 |   background:radial-gradient(circle,#2a0810 0%,#080205 100%);
 100 | }
 101 | /* Scan line */
 102 | .sigil-scan{
 103 |   position:absolute;inset:18%;border-radius:50%;overflow:hidden;pointer-events:none;
 104 | }
 105 | .sigil-scan::after{
 106 |   content:'';position:absolute;left:0;right:0;height:2px;
 107 |   background:linear-gradient(90deg,transparent,rgba(255,59,95,.6),transparent);
 108 |   animation:scan 2.5s ease-in-out infinite;
 109 | }
 110 | 
 111 | /* Wordmark */
 112 | .gate-brand{
 113 |   font-size:10px;font-weight:700;
 114 |   letter-spacing:.4em;color:rgba(255,59,95,.7);
 115 |   text-transform:uppercase;
 116 | }
 117 | 
 118 | /* Title */
 119 | .gate-title{
 120 |   font-size:clamp(32px,9vw,52px);
 121 |   font-weight:900;color:#fff;
 122 |   letter-spacing:-.03em;line-height:1;
 123 |   text-align:center;
 124 | }
 125 | .gate-title span{color:#ff3b5f}
 126 | 
 127 | /* Sub */
 128 | .gate-sub{
 129 |   font-size:clamp(13px,3.5vw,15px);
 130 |   color:#556;
 131 |   text-align:center;line-height:1.6;
 132 |   max-width:300px;
 133 |   font-weight:400;
 134 | }
 135 | 
 136 | /* ─── THE BUTTON ─────────────────────────────────────────── */
 137 | #gate-btn{
 138 |   position:relative;
 139 |   background:transparent;
 140 |   border:none;cursor:pointer;
 141 |   padding:0;
 142 |   width:clamp(200px,55vw,280px);
 143 |   -webkit-appearance:none;
 144 |   touch-action:manipulation;
 145 | }
 146 | #gate-btn:disabled{opacity:.4;cursor:not-allowed}
 147 | #gate-btn:active .btn-inner{transform:scale(.97)}
 148 | 
 149 | .btn-inner{
 150 |   position:relative;overflow:hidden;
 151 |   background:linear-gradient(135deg,#1a0508 0%,#0d0203 100%);
 152 |   border:1px solid rgba(255,59,95,.5);
 153 |   border-radius:4px;
 154 |   padding:clamp(14px,4vw,18px) clamp(20px,5vw,32px);
 155 |   transition:transform .1s,border-color .2s;
 156 |   display:flex;flex-direction:column;align-items:center;gap:6px;
 157 | }
 158 | #gate-btn:not(:disabled):hover .btn-inner{border-color:rgba(255,59,95,.9)}
 159 | 
 160 | /* Top label */
 161 | .btn-label{
 162 |   font-family:'JetBrains Mono',monospace;
 163 |   font-size:9px;letter-spacing:.35em;
 164 |   color:rgba(255,59,95,.6);text-transform:uppercase;
 165 | }
 166 | /* Main text */
 167 | .btn-text{
 168 |   font-size:clamp(13px,4vw,16px);font-weight:700;
 169 |   color:#fff;letter-spacing:.05em;text-transform:uppercase;
 170 |   display:flex;align-items:center;gap:10px;
 171 | }
 172 | .btn-mic-icon{
 173 |   width:16px;height:16px;flex-shrink:0;
 174 |   opacity:.9;
 175 | }
 176 | /* Corner accents */
 177 | .btn-inner::before,.btn-inner::after{
 178 |   content:'';position:absolute;width:8px;height:8px;
 179 |   border-color:rgba(255,59,95,.6);border-style:solid;
 180 | }
 181 | .btn-inner::before{top:4px;left:4px;border-width:1px 0 0 1px}
 182 | .btn-inner::after{bottom:4px;right:4px;border-width:0 1px 1px 0}
 183 | /* Glow sweep on hover */
 184 | .btn-sweep{
 185 |   position:absolute;inset:0;
 186 |   background:linear-gradient(105deg,transparent 40%,rgba(255,59,95,.06) 50%,transparent 60%);
 187 |   transform:translateX(-100%);
 188 |   transition:transform .5s ease;
 189 | }
 190 | #gate-btn:not(:disabled):hover .btn-sweep{transform:translateX(100%)}
 191 | 
 192 | /* Status line below btn */
 193 | #gate-status{
 194 |   font-family:'JetBrains Mono',monospace;
 195 |   font-size:11px;color:#334;letter-spacing:.08em;
 196 |   min-height:16px;text-align:center;
 197 | }
 198 | #gate-error{
 199 |   display:none;font-size:12px;color:#ff3b5f;
 200 |   text-align:center;line-height:1.5;max-width:280px;
 201 |   background:rgba(255,59,95,.06);border:1px solid rgba(255,59,95,.15);
 202 |   border-radius:4px;padding:8px 12px;
 203 | }
 204 | 
 205 | /* ═══════════════════════════════════════════════════════════
 206 |    LIVE STAGE
 207 | ═══════════════════════════════════════════════════════════ */
 208 | #stage{
 209 |   display:none;flex-direction:column;align-items:center;
 210 |   position:relative;
 211 |   width:100%;height:100%;
 212 |   padding:clamp(8px,2.5vw,14px) clamp(12px,3.5vw,20px) clamp(10px,3vw,16px);
 213 |   gap:clamp(6px,1.5vw,10px);
 214 |   overflow-y:auto;-webkit-overflow-scrolling:touch;
 215 |   animation:fade-up .4s ease;
 216 | }
 217 | 
 218 | /* Top bar */
 219 | .topbar{
 220 |   width:100%;display:flex;align-items:center;
 221 |   justify-content:space-between;flex-shrink:0;
 222 | }
 223 | /* Exit and minimize buttons */
 224 | .stage-controls{display:flex;align-items:center;gap:8px}
 225 | #minimize-btn,#exit-btn{
 226 |   width:28px;height:28px;border-radius:50%;
 227 |   background:transparent;border:1px solid #1e2235;
 228 |   cursor:pointer;display:flex;align-items:center;justify-content:center;
 229 |   transition:border-color .15s,background .15s;
 230 |   -webkit-appearance:none;touch-action:manipulation;flex-shrink:0;
 231 |   opacity:0.5;
 232 | }
 233 | #minimize-btn:hover,#exit-btn:hover{opacity:1;border-color:#556;background:#0f1117}
 234 | #exit-btn:hover{border-color:rgba(255,59,95,.5)}
 235 | 
 236 | /* ── FLOATING MINI MODE ─────────────────────────────────────────── */
 237 | @keyframes mini-in{from{opacity:0;transform:scale(.6) translateY(20px)}to{opacity:1;transform:scale(1) translateY(0)}}
 238 | @keyframes mini-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,.4)}70%{box-shadow:0 0 0 8px rgba(255,59,95,0)}}
 239 | 
 240 | #oracle-float{
 241 |   position:fixed;bottom:24px;right:24px;
 242 |   width:72px;height:72px;border-radius:50%;
 243 |   background:#0a0b0f;border:2px solid rgba(255,59,95,.6);
 244 |   cursor:pointer;z-index:9999;
 245 |   display:none;align-items:center;justify-content:center;
 246 |   animation:mini-in .3s ease, mini-pulse 2s ease-in-out infinite;
 247 |   box-shadow:0 4px 20px rgba(0,0,0,.6);
 248 |   overflow:hidden;transition:transform .15s;
 249 | }
 250 | #oracle-float:hover{transform:scale(1.08)}
 251 | #oracle-float:active{transform:scale(.95)}
 252 | #oracle-float img{width:100%;height:100%;object-fit:cover;border-radius:50%}
 253 | #oracle-float-fallback{font-size:28px}
 254 | /* Speaking ring on float */
 255 | #oracle-float.speaking{border-color:#6cff9f;animation:mini-pulse 0.8s ease-in-out infinite}
 256 | /* Tooltip */
 257 | #oracle-float::after{
 258 |   content:"Talk to Satomi";
 259 |   position:absolute;right:80px;
 260 |   background:#0f1117;border:1px solid #1e2235;border-radius:4px;
 261 |   padding:4px 8px;font-family:'JetBrains Mono',monospace;font-size:10px;
 262 |   color:#b8c2d9;white-space:nowrap;pointer-events:none;
 263 |   opacity:0;transition:opacity .2s;
 264 | }
 265 | #oracle-float:hover::after{opacity:1}
 266 | .topbar-brand{
 267 |   font-family:'JetBrains Mono',monospace;
 268 |   font-size:10px;font-weight:500;
 269 |   letter-spacing:.3em;color:rgba(255,59,95,.7);text-transform:uppercase;
 270 | }
 271 | .live-pill{
 272 |   display:flex;align-items:center;gap:5px;
 273 |   background:rgba(74,222,128,.06);
 274 |   border:1px solid rgba(74,222,128,.2);
 275 |   border-radius:20px;padding:3px 8px;
 276 | }
 277 | .live-dot{
 278 |   width:5px;height:5px;border-radius:50%;background:#4ade80;
 279 |   animation:live-blink 2s step-end infinite;
 280 | }
 281 | .live-text{
 282 |   font-family:'JetBrains Mono',monospace;
 283 |   font-size:9px;font-weight:500;color:#4ade80;letter-spacing:.15em;
 284 | }
 285 | 
 286 | /* Video */
 287 | .video-wrap{
 288 |   position:relative;
 289 |   width:100%;
 290 |   max-width:min(440px,calc(100vw - 24px));
 291 |   aspect-ratio:1/1;
 292 |   border-radius:8px;overflow:hidden;
 293 |   background: #050508;
 294 |   overflow: hidden;
 295 |   flex-shrink:0;
 296 |   min-height: min(440px, calc(100vw - 24px));
 297 | }
 298 | /* Corner brackets */
 299 | .video-wrap::before,.video-wrap::after{
 300 |   content:'';position:absolute;width:16px;height:16px;
 301 |   border-color:rgba(255,59,95,.4);border-style:solid;z-index:2;
 302 | }
 303 | .video-wrap::before{top:6px;left:6px;border-width:1px 0 0 1px}
 304 | .video-wrap::after{bottom:6px;right:6px;border-width:0 1px 1px 0}
 305 | 
 306 | #vid{width:100%;height:100%;object-fit:cover;object-position:center top;display:block}
 307 | /* Subtitle */
 308 | #subtitle{
 309 |   width:100%;
 310 |   font-family:'JetBrains Mono',monospace;
 311 |   font-size:clamp(11px,3vw,13px);color:#f8c15c;
 312 |   line-height:1.55;text-align:center;
 313 |   min-height:34px;
 314 |   opacity:0;transition:opacity .3s;
 315 |   display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
 316 |   overflow:hidden;padding:0 4px;
 317 | }
 318 | #subtitle.on{opacity:1}
 319 | 
 320 | /* Status */
 321 | #stat{
 322 |   font-family:'JetBrains Mono',monospace;
 323 |   font-size:clamp(10px,2.8vw,12px);
 324 |   color:#334;display:flex;align-items:center;gap:6px;
 325 |   height:18px;transition:color .2s;flex-shrink:0;
 326 | }
 327 | .spin{width:12px;height:12px;border:1.5px solid currentColor;border-top-color:transparent;border-radius:50%;display:none;animation:spin .6s linear infinite;flex-shrink:0}
 328 | 
 329 | /* Transcript */
 330 | #tx{
 331 |   font-family:'JetBrains Mono',monospace;
 332 |   font-size:clamp(10px,2.8vw,11px);color:#445;font-style:italic;
 333 |   min-height:16px;text-align:center;
 334 |   opacity:0;transition:opacity .2s;
 335 |   width:100%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;
 336 | }
 337 | #tx.on{opacity:1}
 338 | 
 339 | /* Mic */
 340 | .mic-area{display:flex;flex-direction:column;align-items:center;gap:7px;flex-shrink:0}
 341 | #mic{
 342 |   width:clamp(60px,15vw,72px);height:clamp(60px,15vw,72px);
 343 |   border-radius:50%;
 344 |   background:#0a0c12;
 345 |   border:1.5px solid #ff3b5f;
 346 |   cursor:pointer;
 347 |   display:flex;align-items:center;justify-content:center;
 348 |   transition:background .15s,transform .1s;
 349 |   -webkit-appearance:none;touch-action:manipulation;
 350 |   flex-shrink:0;
 351 | }
 352 | #mic:active:not(:disabled){transform:scale(.92)}
 353 | #mic:disabled{opacity:.2;cursor:not-allowed}
 354 | #mic.rec{background:#ff3b5f;animation:mic-pulse 1s ease-out infinite}
 355 | #mic.idle-pulse{border-color:#ff3b5f;border-width:2px;animation:mic-idle-pulse 1.8s ease-in-out 3}
 356 | .mic-hint{font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.12em;text-transform:uppercase}
 357 | #cam-btn{
 358 |   width:42px;height:42px;border-radius:50%;background:#0a0c12;
 359 |   border:1.5px solid #334;cursor:pointer;
 360 |   display:flex;align-items:center;justify-content:center;
 361 |   transition:border-color .15s;-webkit-appearance:none;touch-action:manipulation;
 362 |   flex-shrink:0;
 363 | }
 364 | #cam-btn:hover{border-color:#f8c15c}
 365 | #cam-btn.active{border-color:#f8c15c;background:#1a1500}
 366 | #cam-input{display:none}
 367 | #vision-status{
 368 |   font-family:'JetBrains Mono',monospace;font-size:10px;color:#f8c15c;
 369 |   text-align:center;opacity:0;transition:opacity .3s;min-height:14px;
 370 | }
 371 | #vision-status.on{opacity:1}
 372 | 
 373 | /* Sovereignty cards */
 374 | #cards{display:none;grid-template-columns:1fr 1fr;gap:8px;width:100%;animation:card-up .35s ease;position:relative;z-index:0}
 375 | #cards.on{display:grid}
 376 | .card{
 377 |   background:#080a0f;
 378 |   border:1px solid #141824;
 379 |   border-radius:6px;
 380 |   padding:clamp(10px,2.5vw,13px);
 381 |   cursor:pointer;
 382 |   transition:border-color .15s,background .15s;
 383 |   display:flex;flex-direction:column;gap:5px;
 384 |   touch-action:manipulation;
 385 | }
 386 | .card:active{background:#100610;border-color:rgba(255,59,95,.5)}
 387 | .card-title{font-size:clamp(11px,3.2vw,13px);font-weight:600;color:#ccd;line-height:1.3}
 388 | .card-link{font-family:'JetBrains Mono',monospace;font-size:clamp(9px,2.5vw,10px);color:rgba(255,59,95,.7);text-decoration:none;letter-spacing:.03em}
 389 | 
 390 | /* ═══════════════════════════════════════════════════════════
 391 |    MOBILE — max-width 640px
 392 | ═══════════════════════════════════════════════════════════ */
 393 | /* ═══════════════════════════════════════════════════════════
 394 |    TABLET — max-width 768px
 395 | ═══════════════════════════════════════════════════════════ */
 396 | @media(max-width:768px){
 397 |   body{padding-top:48px}
 398 |   .video-wrap{
 399 |     max-width:100%;
 400 |     margin:0 auto;
 401 |   }
 402 |   #vid{
 403 |     width:100%;
 404 |     max-width:100%;
 405 |     display:block;
 406 |     margin:0 auto;
 407 |   }
 408 |   #cards{grid-template-columns:1fr 1fr}
 409 |   .card{min-height:48px}
 410 |   #mic{min-width:48px;min-height:48px}
 411 |   #cam-btn{min-width:48px;min-height:48px}
 412 |   #gate-btn{min-height:48px}
 413 |   #root{padding-bottom:80px}
 414 | }
 415 | 
 416 | @media(max-width:640px){
 417 |   body{position:fixed;width:100%;overflow:hidden}
 418 |   #root{position:relative;height:100dvh}
 419 |   /* Stage: full viewport, vertical stack, no overflow leak */
 420 |   #stage{
 421 |     height:100vh;height:100dvh;
 422 |     padding:8px 10px 0;
 423 |     gap:6px;
 424 |     overflow:hidden;
 425 |     display:none;flex-direction:column;
 426 |   }
 427 | 
 428 |   /* Topbar: compact for 375px screens */
 429 |   .topbar{
 430 |     padding:0;
 431 |     min-height:28px;
 432 |     flex-shrink:0;
 433 |   }
 434 |   .topbar-brand{font-size:9px;letter-spacing:.25em}
 435 |   .live-pill{padding:2px 6px}
 436 |   .live-text{font-size:8px}
 437 |   .stage-controls{gap:4px}
 438 |   #minimize-btn,#exit-btn{width:26px;height:26px}
 439 | 
 440 |   /* Video: constrain to 60vh max, centered */
 441 |   .video-wrap{
 442 |     max-height:60vh;
 443 |     max-width:calc(100vw - 20px);
 444 |     width:100%;
 445 |     aspect-ratio:1/1;
 446 |     margin:0 auto;
 447 |     flex-shrink:1;
 448 |     min-height:0;
 449 |   }
 450 |   #vid{
 451 |     width:100%;
 452 |     height:100%;
 453 |     max-width:340px;
 454 |     margin:0 auto;
 455 |     display:block;
 456 |     border-radius:8px;
 457 |     object-fit:cover;
 458 |   }
 459 | 
 460 |   /* Subtitle: tighter */
 461 |   #subtitle{
 462 |     font-size:11px;
 463 |     min-height:28px;
 464 |     padding:0 2px;
 465 |     flex-shrink:0;
 466 |   }
 467 | 
 468 |   /* Status + transcript: compact */
 469 |   #stat{font-size:10px;height:16px;flex-shrink:0}
 470 |   #tx{font-size:10px;min-height:14px;flex-shrink:0}
 471 | 
 472 |   /* Mic area + input controls: sticky to bottom, full width, tap-friendly */
 473 |   .mic-area{
 474 |     width:100%;
 475 |     flex-shrink:0;
 476 |     padding-bottom:env(safe-area-inset-bottom,8px);
 477 |     margin-top:auto;
 478 |   }
 479 |   #mic{
 480 |     width:60px;height:60px;
 481 |     min-width:48px;min-height:48px;
 482 |   }
 483 |   .mic-hint{font-size:9px}
 484 | 
 485 |   /* Camera button: 48px touch target */
 486 |   #cam-btn{
 487 |     width:48px;height:48px;
 488 |     min-width:48px;min-height:48px;
 489 |   }
 490 | 
 491 |   /* Vision status */
 492 |   #vision-status{font-size:9px;min-height:12px}
 493 | 
 494 |   /* Cards grid: 1 column on mobile */
 495 |   #cards{grid-template-columns:1fr}
 496 |   #cards.on{
 497 |     display:grid;
 498 |     max-height:30vh;
 499 |     overflow-y:auto;
 500 |     -webkit-overflow-scrolling:touch;
 501 |   }
 502 |   .card{
 503 |     padding:10px;
 504 |     min-height:48px;
 505 |     display:flex;flex-direction:row;align-items:center;
 506 |     gap:8px;
 507 |   }
 508 |   .card-title{font-size:13px}
 509 |   .card-link{font-size:10px}
 510 | 
 511 |   /* Gate: ensure it fits small screens */
 512 |   #gate{
 513 |     padding:20px 16px;
 514 |     gap:16px;
 515 |   }
 516 |   .sigil-wrap{width:130px;height:130px}
 517 |   .gate-title{font-size:32px}
 518 |   .gate-sub{font-size:13px;max-width:260px}
 519 |   #gate-btn{width:220px}
 520 |   .btn-inner{padding:14px 20px}
 521 |   #gate-status{font-size:10px}
 522 |   #gate-error{font-size:11px;max-width:260px}
 523 | 
 524 |   /* Float bubble: smaller on mobile */
 525 |   #oracle-float{
 526 |     width:56px;height:56px;
 527 |     bottom:16px;right:16px;
 528 |   }
 529 | }
 530 | 
 531 | /* ── STUDIO TREATMENT (oracle-live only) ─────────── */
 532 | .video-wrap {
 533 |   border: 2px solid rgba(220,38,38,0.4);
 534 |   box-shadow: 0 0 40px rgba(220,38,38,0.15);
 535 | }
 536 | #oracle-matrix { pointer-events: none; }
 537 | 
 538 | /* ── VISION TRANSCRIPT ─────────────────────────── */
 539 | .vision-entry {
 540 |   padding: 10px 14px;
 541 |   border-bottom: 1px solid rgba(255,255,255,.04);
 542 |   cursor: pointer;
 543 | }
 544 | .vision-entry:hover { background: rgba(255,255,255,.03); }
 545 | .vision-entry:last-child { border-bottom: none; }
 546 | .vision-entry-device {
 547 |   font-family: monospace;
 548 |   font-size: 10px;
 549 |   letter-spacing: .1em;
 550 |   color: rgba(255,59,95,.7);
 551 |   text-transform: uppercase;
 552 |   margin-bottom: 4px;
 553 | }
 554 | .vision-entry-step {
 555 |   font-size: 0.8rem;
 556 |   color: rgba(255,255,255,.7);
 557 |   line-height: 1.5;
 558 |   margin: 2px 0;
 559 | }
 560 | .vision-entry-time {
 561 |   font-family: monospace;
 562 |   font-size: 9px;
 563 |   color: rgba(255,255,255,.2);
 564 |   margin-top: 4px;
 565 | }
 566 | </style>
 567 | </head>
 568 | <body>
 569 | <div id="vision-security-overlay" style="display:none;position:fixed;inset:0;
 570 | z-index:99999;background:rgba(180,0,0,0.97);flex-direction:column;
 571 | align-items:center;justify-content:center;padding:32px;text-align:center;">
 572 |   <div style="font-size:64px;margin-bottom:16px;">⚠️</div>
 573 |   <div style="font-family:monospace;font-size:13px;letter-spacing:.12em;
 574 | color:rgba(255,255,255,.6);margin-bottom:8px;text-transform:uppercase;">
 575 | SECURITY ALERT</div>
 576 |   <div id="vision-security-msg" style="font-size:1.2rem;font-weight:700;
 577 | color:#fff;margin-bottom:32px;line-height:1.5;max-width:340px;"></div>
 578 |   <button id="vision-security-dismiss"
 579 |     style="background:#fff;color:#b40000;font-family:monospace;font-weight:800;
 580 | font-size:14px;letter-spacing:.1em;border:none;border-radius:8px;
 581 | padding:16px 32px;cursor:pointer;text-transform:uppercase;
 582 | min-height:56px;width:100%;max-width:320px;">
 583 |     ✓ GOT IT — COVER NOW
 584 |   </button>
 585 |   <div id="vision-recovery-panel" style="display:none;width:100%;
 586 | max-width:340px;margin-top:24px;">
 587 |     <div style="font-family:monospace;font-size:11px;letter-spacing:.12em;
 588 | color:rgba(255,255,255,.5);margin-bottom:12px;text-transform:uppercase;">
 589 | YOUR FUNDS MAY BE AT RISK — ACT NOW</div>
 590 |     <div id="vision-recovery-step-label" style="font-family:monospace;
 591 | font-size:11px;color:rgba(255,200,0,.8);letter-spacing:.1em;
 592 | margin-bottom:8px;text-transform:uppercase;">STEP 1 OF 3</div>
 593 |     <div id="vision-recovery-step-text" style="font-size:1rem;
 594 | font-weight:600;color:#fff;line-height:1.6;margin-bottom:24px;"></div>
 595 |     <button id="vision-recovery-next"
 596 |       style="background:rgba(255,255,255,.15);color:#fff;
 597 | font-family:monospace;font-weight:700;font-size:13px;
 598 | letter-spacing:.08em;border:2px solid rgba(255,255,255,.3);
 599 | border-radius:8px;padding:14px 24px;cursor:pointer;
 600 | text-transform:uppercase;min-height:52px;width:100%;">
 601 |       NEXT STEP →
 602 |     </button>
 603 |     <button id="vision-recovery-help"
 604 |       style="display:none;background:#fff;color:#b40000;
 605 | font-family:monospace;font-weight:800;font-size:13px;
 606 | letter-spacing:.08em;border:none;border-radius:8px;
 607 | padding:14px 24px;cursor:pointer;text-transform:uppercase;
 608 | min-height:52px;width:100%;margin-top:8px;">
 609 |       HELP ME SET UP NEW WALLET
 610 |     </button>
 611 |     <button id="vision-recovery-close"
 612 |       style="display:none;background:none;color:rgba(255,255,255,.4);
 613 | font-family:monospace;font-size:11px;letter-spacing:.08em;
 614 | border:none;padding:12px;cursor:pointer;text-transform:uppercase;
 615 | width:100%;margin-top:4px;">
 616 |       I UNDERSTAND THE RISK — CLOSE
 617 |     </button>
 618 |   </div>
 619 | </div>
 620 | <div id="mobile-nav-bar" style="display:none;position:fixed;top:0;left:0;right:0;z-index:9998;background:rgba(4,5,10,.95);padding:10px 16px;border-bottom:1px solid rgba(255,59,95,.15);align-items:center;gap:12px;">
 621 |   <button onclick="window.history.back()" style="background:none;border:1px solid rgba(255,255,255,.15);color:rgba(255,255,255,.6);padding:6px 14px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;letter-spacing:.08em;">&larr; BACK</button>
 622 |   <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:rgba(255,59,95,.8);letter-spacing:.15em;">ORACLE &mdash; PROTOCOL PULSE</span>
 623 | </div>
 624 | <div id="root">
 625 | 
 626 | <!-- ══ GATE ══ -->
 627 | <div id="gate">
 628 |   <div class="gate-brand">Protocol Pulse</div>
 629 | 
 630 |   <div class="sigil-wrap">
 631 |     <div class="ring ring-1"></div>
 632 |     <div class="ring ring-2"></div>
 633 |     <div class="sigil-avatar">
 634 |       <img src="/static/oracle_avatar.png" alt="Satomi"
 635 |            onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
 636 |       <div class="sigil-fallback" style="display:none">⚡</div>
 637 |     </div>
 638 |     <div class="sigil-scan"></div>
 639 |   </div>
 640 | 
 641 |   <h1 class="gate-title">THE <span>SATOMI</span></h1>
 642 |   <p class="gate-sub">Sovereign Bitcoin intelligence.<br>Ask anything, in real time.</p>
 643 | 
 644 |   <button id="gate-btn" onclick="requestMic()">
 645 |     <div class="btn-sweep"></div>
 646 |     <div class="btn-inner">
 647 |       <div class="btn-label">Protocol Pulse Intelligence</div>
 648 |       <div class="btn-text">
 649 |         <svg class="btn-mic-icon" viewBox="0 0 24 24" fill="none">
 650 |           <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 651 |           <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 652 |           <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 653 |         </svg>
 654 |         Speak to Satomi
 655 |       </div>
 656 |     </div>
 657 |   </button>
 658 | 
 659 |   <div id="gate-status">— tap to activate —</div>
 660 |   <div id="gate-error"></div>
 661 |   <!-- P0: Text input fallback when mic is unavailable -->
 662 |   <div id="text-input-fallback" style="display:none;width:100%;max-width:320px;margin-top:12px;">
 663 |     <div style="display:flex;gap:8px;align-items:center;">
 664 |       <input type="text" id="text-input-field" placeholder="Type your question..."
 665 |         style="flex:1;background:#0a0c12;border:1px solid rgba(255,59,95,.4);border-radius:4px;
 666 |         padding:12px 14px;color:#fff;font-family:'JetBrains Mono',monospace;font-size:13px;
 667 |         outline:none;" onkeydown="if(event.key==='Enter')submitTextInput()">
 668 |       <button onclick="submitTextInput()"
 669 |         style="background:rgba(255,59,95,.15);border:1px solid rgba(255,59,95,.5);
 670 |         border-radius:4px;padding:12px 16px;color:#ff3b5f;font-family:'JetBrains Mono',monospace;
 671 |         font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap;letter-spacing:.05em;">SEND</button>
 672 |     </div>
 673 |   </div>
 674 | </div>
 675 | 
 676 | <!-- ══ LIVE STAGE ══ -->
 677 | <div id="stage">
 678 | 
 679 |   <div class="topbar">
 680 |     <span class="topbar-brand">Satomi</span>
 681 |     <div class="live-pill"><div class="live-dot"></div><span class="live-text">LIVE</span></div>
 682 |     <a href="/" style="margin-left:auto;color:rgba(255,255,255,0.3);font-size:22px;text-decoration:none;padding:4px 10px;line-height:1;transition:color 0.2s;" onmouseover="this.style.color='rgba(255,255,255,0.8)'" onmouseout="this.style.color='rgba(255,255,255,0.3)'" aria-label="Exit Satomi" title="Go to homepage">&times;</a>
 683 |   </div>
 684 | 
 685 |   <canvas id="bg-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;will-change:transform;"></canvas>
 686 | 
 687 |   <div class="video-wrap" style="position:relative;z-index:1;">
 688 |     <!-- P0-1: Static avatar always visible behind video — never black screen -->
 689 |     <img id="avatar-idle" src="/static/oracle_avatar.png" alt="Satomi"
 690 |          style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;border-radius:8px;"
 691 |          onerror="this.style.background='radial-gradient(circle,#1a0608,#050203)'">
 692 |     <canvas id="oracle-matrix" style="position:absolute;inset:0;width:100%;height:100%;z-index:1;opacity:0.35;transition:opacity 0.5s;"></canvas>
 693 |     <video id="vid" playsinline webkit-playsinline x-webkit-airplay="allow" preload="auto" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;z-index:2;"></video>
 694 |     <!-- P0: Tap-to-play overlay for iOS Safari autoplay restrictions -->
 695 |     <div id="tap-to-play" style="display:none;position:absolute;inset:0;z-index:10;background:rgba(0,0,0,.55);
 696 |       border-radius:8px;cursor:pointer;align-items:center;justify-content:center;flex-direction:column;gap:8px;"
 697 |       onclick="dismissTapOverlay()">
 698 |       <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
 699 |         <circle cx="12" cy="12" r="11" stroke="rgba(255,59,95,.7)" stroke-width="1.5"/>
 700 |         <polygon points="10,7 10,17 18,12" fill="#ff3b5f"/>
 701 |       </svg>
 702 |       <span style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.12em;color:rgba(255,255,255,.8);text-transform:uppercase;">Tap to Play</span>
 703 |     </div>
 704 |   </div>
 705 | 
 706 |   <div id="subtitle"></div>
 707 |   <div id="oracle-action-card" style="display:none;margin-top:12px;max-width:min(440px,calc(100vw - 24px));width:100%;"></div>
 708 | 
 709 |   <div id="stat">
 710 |     <span class="spin" id="spin"></span>
 711 |     <span id="stat-text">Ready</span>
 712 |   </div>
 713 | 
 714 |   <div id="tx"></div>
 715 | 
 716 |   <div class="mic-area">
 717 |     <button id="mic" disabled onclick="toggleMic()">
 718 |       <svg id="i-mic" width="24" height="24" viewBox="0 0 24 24" fill="none">
 719 |         <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 720 |         <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 721 |         <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 722 |         <line x1="9" y1="22" x2="15" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 723 |       </svg>
 724 |       <svg id="i-stop" width="24" height="24" viewBox="0 0 24 24" fill="none" style="display:none">
 725 |         <rect x="6" y="6" width="12" height="12" rx="2" fill="#fff"/>
 726 |       </svg>
 727 |     </button>
 728 |     <span class="mic-hint" id="mic-hint">tap to speak</span>
 729 |   </div>
 730 |   <!-- P0: Stage text input — shown when mic is unavailable or as alternative -->
 731 |   <div id="stage-text-input" style="display:none;width:100%;max-width:min(440px,calc(100vw - 24px));margin-top:4px;">
 732 |     <div style="display:flex;gap:6px;align-items:center;">
 733 |       <input type="text" id="stage-text-field" placeholder="Type your question..."
 734 |         style="flex:1;background:#080a0f;border:1px solid #1e2235;border-radius:4px;
 735 |         padding:10px 12px;color:#fff;font-family:'JetBrains Mono',monospace;font-size:12px;
 736 |         outline:none;transition:border-color .15s;" onfocus="this.style.borderColor='rgba(255,59,95,.5)'" onblur="this.style.borderColor='#1e2235'" onkeydown="if(event.key==='Enter')stageTextSubmit()">
 737 |       <button onclick="stageTextSubmit()"
 738 |         style="background:#0a0c12;border:1px solid rgba(255,59,95,.4);border-radius:4px;
 739 |         padding:10px 14px;color:#ff3b5f;font-family:'JetBrains Mono',monospace;font-size:11px;
 740 |         font-weight:600;cursor:pointer;letter-spacing:.05em;">SEND</button>
 741 |     </div>
 742 |   </div>
 743 | 
 744 |   <!-- Vision status + Camera button -->
 745 |   <div id="vision-status"></div>
 746 |   <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:4px">
 747 |     <button id="cam-btn" onclick="triggerCamera()" title="Show Satomi your screen — she will guide you step by step">
 748 |       <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
 749 |         <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke="#556" stroke-width="1.5" stroke-linecap="round"/>
 750 |         <circle cx="12" cy="13" r="4" stroke="#556" stroke-width="1.5"/>
 751 |       </svg>
 752 |     </button>
 753 |     <span id="cam-btn-label" style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.08em">ANALYZE HARDWARE</span>
 754 |   </div>
 755 |   <div id="vision-transcript-panel" style="display:none;
 756 |   width:100%;max-width:min(440px,calc(100vw - 24px));
 757 |   margin:12px auto 0;background:rgba(6,7,14,.9);
 758 |   border:1px solid rgba(255,59,95,.15);border-radius:8px;
 759 |   overflow:hidden;">
 760 |     <div style="display:flex;align-items:center;justify-content:space-between;
 761 |   padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.06);">
 762 |       <span style="font-family:monospace;font-size:10px;letter-spacing:.12em;
 763 |   color:rgba(255,59,95,.8);text-transform:uppercase;">SESSION LOG</span>
 764 |       <button id="vision-transcript-clear"
 765 |         style="background:none;border:none;color:rgba(255,255,255,.3);
 766 |   font-family:monospace;font-size:9px;letter-spacing:.08em;
 767 |   cursor:pointer;text-transform:uppercase;padding:2px 6px;">
 768 |         CLEAR
 769 |       </button>
 770 |     </div>
 771 |     <div id="vision-transcript-entries" style="max-height:280px;
 772 |   overflow-y:auto;padding:8px 0;"></div>
 773 |   </div>
 774 | 
 775 |   <input type="file" id="cam-input" accept="image/*" capture="environment" onchange="handleVisionUpload(event)">
 776 | 
 777 |   <div id="cards">
 778 |     <div class="card" onclick="si('SOVEREIGNTY_COLD_WALLET')">
 779 |       <div class="card-title">&#128272; Self-Custody</div>
 780 |       <a class="card-link" href="https://coldcard.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">coldcard.com &#8594;</a>
 781 |     </div>
 782 |     <div class="card" onclick="si('SOVEREIGNTY_NODE')">
 783 |       <div class="card-title">&#9889; Run a Node</div>
 784 |       <a class="card-link" href="https://getumbrel.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">getumbrel.com &#8594;</a>
 785 |     </div>
 786 |     <div class="card" onclick="si('SOVEREIGNTY_BITAXE')">
 787 |       <div class="card-title">&#9935; Solo Mining</div>
 788 |       <a class="card-link" href="https://curatedmining.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">curatedmining.com &#8594;</a>
 789 |     </div>
 790 |     <div class="card" onclick="si('SOVEREIGNTY_LIFE_INSURANCE')">
 791 |       <div class="card-title">&#128737; BTC Insurance</div>
 792 |       <a class="card-link" href="https://application.meanwhile.bm/start?referralCode=KKM73K" target="_blank" rel="noopener" onclick="event.stopPropagation()">meanwhile.bm &#8594;</a>
 793 |     </div>
 794 |   </div>
 795 | 
 796 | </div><!-- /stage -->
 797 | </div><!-- /root -->
 798 | 
 799 | <script>
 800 | 'use strict';
 801 | /* ── iOS zoom prevention ── */
 802 | document.addEventListener('gesturestart',function(e){e.preventDefault();},{passive:false});
 803 | document.addEventListener('touchmove',function(e){if(e.touches.length>1)e.preventDefault();},{passive:false});
 804 | var A='https://avatar.protocolpulse.io';
 805 | var S={
 806 |   GREETING:"Hey. I'm Satomi — your Protocol Pulse intelligence anchor. On-chain, macro, geopolitical. What can I help you with?",
 807 |   SOVEREIGNTY_INTRO:"Your sovereignty score is a snapshot of how free you actually are — how much of your financial life you've pulled out of legacy systems.",
 808 |   SOVEREIGNTY_ASSESSMENT:"Four pillars: self-custody of your Bitcoin, your own node, private comms, and no KYC on your income. Where are you today?",
 809 |   SOVEREIGNTY_COLD_WALLET:"If your Bitcoin is on an exchange, it's not yours — it's an IOU. A hardware wallet fixes that. I can walk you through it.",
 810 |   SOVEREIGNTY_NODE:"Running your own node means you verify your own transactions. You don't trust, you verify. Umbrel on a Pi is the easiest path.",
 811 |   SOVEREIGNTY_BITAXE:"Bitaxe is a solo miner you can run at home. A Bitcoin lottery ticket. Curated Mining also does white-glove setup.",
 812 |   SOVEREIGNTY_LIFE_INSURANCE:"If you die with Bitcoin in cold storage and nobody knows the seed phrase, it's gone. Meanwhile offers life insurance that actually understands Bitcoin.",
 813 |   SOVEREIGNTY_RESIDENCY:"Digital residency through Palau via RNS.ID gives you a second legal identity outside your home country. Real tax and privacy implications.",
 814 |   DAILY_BRIEF_INTRO:"Here's what's moving in Bitcoin right now. Pulling the latest from our intelligence layer...",
 815 |   DAILY_BRIEF_LIVE:"Here's today's Bitcoin intelligence brief.",
 816 |   UNKNOWN_QUESTION:"I'm researching that now. One moment.",
 817 |   GOODBYE:"Stack sats, verify everything, and come back anytime."
 818 | };
 819 | 
 820 | var busy=false,isRec=false,pending='',objURL=null,recognition=null;
 821 | var _greeted=false;
 822 | 
 823 | /* ── ORACLE STATE MACHINE ──
 824 |    States: WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING
 825 |    Every state shows the avatar face (never black screen).
 826 |    LISTENING: mic active, avatar static idle visible, status "Ready"
 827 |    PROCESSING: mic off, spinner, avatar idle visible
 828 |    RESPONDING: video playing over idle bg, mic off
 829 | */
 830 | var ORACLE_STATE = 'IDLE'; /* IDLE, WELCOME, LISTENING, PROCESSING, RESPONDING */
 831 | function setOracleState(state){
 832 |   ORACLE_STATE = state;
 833 |   console.log('[Satomi] State →', state);
 834 |   switch(state){
 835 |     case 'LISTENING':
 836 |       mic.disabled=false;
 837 |       setStat('Ready','#334',false);
 838 |       /* Ensure avatar idle is visible (video-wrap bg shows through when vid is transparent) */
 839 |       vid.style.opacity='0';
 840 |       break;
 841 |     case 'PROCESSING':
 842 |       mic.disabled=true;
 843 |       if(isRec) stopRec();
 844 |       break;
 845 |     case 'RESPONDING':
 846 |       mic.disabled=true;
 847 |       if(isRec) stopRec();
 848 |       break;
 849 |     case 'WELCOME':
 850 |       mic.disabled=true;
 851 |       break;
 852 |   }
 853 | }
 854 | 
 855 | var VISION_SPONSOR_MAP = {
 856 |   'trezor':   { category:'amazon', title:'Trezor Hardware Wallet', id:'vision_trezor',
 857 |     description:'The original Bitcoin hardware wallet. Battle-tested since 2014.',
 858 |     url:'https://amzn.to/trezor', cta:'View on Amazon' },
 859 |   'coldcard': { category:'affiliate', title:'Coldcard Mk4', id:'vision_coldcard',
 860 |     description:'The most secure Bitcoin signing device. Air-gapped by default.',
 861 |     url:'https://coldcard.com', cta:'Get Coldcard' },
 862 |   'ledger':   { category:'amazon', title:'Ledger Hardware Wallet', id:'vision_ledger',
 863 |     description:'Secure your Bitcoin with industry-leading hardware security.',
 864 |     url:'https://amzn.to/ledger', cta:'View on Amazon' },
 865 |   'bitaxe':   { category:'affiliate', title:'BitAxe Solo Miner', id:'vision_bitaxe',
 866 |     description:'Open-source Bitcoin miner. Stack sats from your home.',
 867 |     url:'https://bitaxe.org', cta:'Get BitAxe' },
 868 |   'umbrel':   { category:'affiliate', title:'Umbrel Home Server', id:'vision_umbrel',
 869 |     description:'Run your own Bitcoin node. Your keys, your coins.',
 870 |     url:'https://umbrel.com', cta:'Run Umbrel' },
 871 |   'start9':   { category:'affiliate', title:'Start9 Embassy', id:'vision_start9',
 872 |     description:'Sovereign computing for the sovereign individual.',
 873 |     url:'https://start9.com', cta:'Get Embassy' },
 874 |   'seedsigner':{ category:'affiliate', title:'SeedSigner', id:'vision_seedsigner',
 875 |     description:'Air-gapped signing device. Build your own or buy assembled.',
 876 |     url:'https://seedsigner.com', cta:'Learn More' },
 877 |   'passport': { category:'affiliate', title:'Foundation Passport', id:'vision_passport',
 878 |     description:'Open-source, air-gapped Bitcoin hardware wallet.',
 879 |     url:'https://foundationdevices.com', cta:'Get Passport' },
 880 |   'jade':     { category:'affiliate', title:'Blockstream Jade', id:'vision_jade',
 881 |     description:'Open-source hardware wallet with air-gapped signing.',
 882 |     url:'https://store.blockstream.com', cta:'Get Jade' }
 883 | };
 884 | 
 885 | function pulseMic(){
 886 |   if(!mic||mic.disabled||isRec)return;
 887 |   mic.classList.remove('idle-pulse');
 888 |   void mic.offsetWidth;
 889 |   mic.classList.add('idle-pulse');
 890 |   setStat('Tap mic to respond','#ff3b5f',false);
 891 |   setTimeout(function(){mic.classList.remove('idle-pulse');setStat('Ready','#334',false);},6000);
 892 | }
 893 | 
 894 | /* FIX 4: Fallback tap-to-speak — if greeting played but mic never activated,
 895 |    any tap on the stage area starts recognition */
 896 | var _tapFallbackSet=false;
 897 | function setupTapFallback(){
 898 |   if(_tapFallbackSet)return;
 899 |   _tapFallbackSet=true;
 900 |   var _stageEl=document.getElementById('stage');
 901 |   if(!_stageEl)return;
 902 |   function _tapToSpeak(e){
 903 |     /* Only fire if: greeted, not busy, mic not recording, recognition available */
 904 |     if(!_greeted||busy||isRec||!recognition)return;
 905 |     /* Don't intercept mic button clicks or other interactive elements */
 906 |     if(e.target.closest&&(e.target.closest('#mic-btn')||e.target.closest('.action-card')||e.target.closest('#stage-text-input')))return;
 907 |     console.log('[Satomi] Tap fallback — starting recognition');
 908 |     setBusy(false);
 909 |     mic.disabled=false;
 910 |     startRec();
 911 |     setStat('Listening\u2026','#6cff9f',false);
 912 |     /* Remove after first successful activation */
 913 |     _stageEl.removeEventListener('click',_tapToSpeak);
 914 |   }
 915 |   _stageEl.addEventListener('click',_tapToSpeak);
 916 |   console.log('[Satomi] Tap-to-speak fallback registered on stage');
 917 | }
 918 | 
 919 | // ── VISITOR FINGERPRINT ───────────────────────────────────
 920 | // Generates a stable browser fingerprint — no cookies, no login
 921 | // Used server-side to recognize returning visitors
 922 | (function() {
 923 |   try {
 924 |     var fp = '';
 925 |     // Canvas fingerprint
 926 |     var canvas = document.createElement('canvas');
 927 |     var ctx = canvas.getContext('2d');
 928 |     ctx.textBaseline = 'top';
 929 |     ctx.font = '14px Arial';
 930 |     ctx.fillText('Satomi fp', 2, 2);
 931 |     fp += canvas.toDataURL().slice(-20);
 932 |     // Screen + timezone
 933 |     fp += screen.width + 'x' + screen.height + Intl.DateTimeFormat().resolvedOptions().timeZone;
 934 |     // Hash it (simple djb2)
 935 |     var hash = 5381;
 936 |     for (var i = 0; i < fp.length; i++) {
 937 |       hash = ((hash << 5) + hash) + fp.charCodeAt(i);
 938 |       hash = hash & hash; // 32-bit int
 939 |     }
 940 |     window._visitorToken = Math.abs(hash).toString(36);
 941 |   } catch(e) {
 942 |     window._visitorToken = 'anon';
 943 |   }
 944 | })();
 945 | 
 946 | // Read session_id and page context from URL params (injected by widget)
 947 | var _urlParams = new URLSearchParams(window.location.search);
 948 | var SESSION_ID = _urlParams.get('session_id') || ('sess_'+Date.now()+'_'+Math.random().toString(36).slice(2,8));
 949 | window.ORACLE_FINGERPRINT_MATCH = false;
 950 | var PAGE_CONTEXT = {
 951 |   type: _urlParams.get('page_type') || 'general',
 952 |   path: _urlParams.get('page_path') || window.location.pathname,
 953 |   content: null,
 954 |   url: document.referrer || window.location.href,
 955 | };
 956 | 
 957 | // Receive richer context from parent widget via postMessage
 958 | window.addEventListener('message', function(e) {
 959 |   if (!e.data || typeof e.data !== 'object') return;
 960 |   var d = e.data;
 961 |   if (d.type === 'oracle:context') {
 962 |     // Parent widget sent full page context
 963 |     if (d.sessionId) SESSION_ID = d.sessionId;
 964 |     if (d.pageContext) PAGE_CONTEXT = d.pageContext;
 965 |   }
 966 | });
 967 | 
 968 | // Tell parent we want context (in case we loaded before message was sent)
 969 | setTimeout(function(){
 970 |   try{ if(window.parent!==window) window.parent.postMessage({type:'oracle:context_request'},'*'); }catch(e){}
 971 | },300);
 972 | 
 973 | /* DOM */
 974 | var gate=document.getElementById('gate');
 975 | var stage=document.getElementById('stage');
 976 | var gBtn=document.getElementById('gate-btn');
 977 | /* iOS bfcache fix: always reset gate button on page load */
 978 | if(gBtn){ gBtn.disabled=false; }
 979 | var gStatus=document.getElementById('gate-status');
 980 | /* iOS bfcache: re-enable gate button when page is restored from cache */
 981 | window.addEventListener('pageshow', function(e){
 982 |   if(e.persisted && gBtn){ gBtn.disabled=false; gStatus.textContent=''; }
 983 | });
 984 | var gErr=document.getElementById('gate-error');
 985 | var vid=document.getElementById('vid');
 986 | var sub=document.getElementById('subtitle');
 987 | var statEl=document.getElementById('stat-text');
 988 | var spinEl=document.getElementById('spin');
 989 | var txEl=document.getElementById('tx');
 990 | var mic=document.getElementById('mic');
 991 | var micHint=document.getElementById('mic-hint');
 992 | var iMic=document.getElementById('i-mic');
 993 | var iStop=document.getElementById('i-stop');
 994 | var cards=document.getElementById('cards');
 995 | 
 996 | /* ── MIC REQUEST ── */
 997 | function requestMic(){
 998 |   gBtn.disabled=true;
 999 |   gStatus.textContent='Requesting microphone...';
1000 |   gErr.style.display='none';
1001 | 
1002 |   /* CRITICAL: unlock audio context immediately on this user gesture */
1003 |   try{
1004 |     var _unlockAc=new(window.AudioContext||window.webkitAudioContext)();
1005 |     var _unlockBuf=_unlockAc.createBuffer(1,1,22050);
1006 |     var _unlockSrc=_unlockAc.createBufferSource();
1007 |     _unlockSrc.buffer=_unlockBuf;_unlockSrc.connect(_unlockAc.destination);_unlockSrc.start(0);
1008 |     setTimeout(function(){try{_unlockAc.close();}catch(e){}},300);
1009 |   }catch(e){}
1010 | 
1011 |   try{
1012 |     var ac=new(window.AudioContext||window.webkitAudioContext)();
1013 |     var buf=ac.createBuffer(1,1,22050);
1014 |     var src=ac.createBufferSource();
1015 |     src.buffer=buf;src.connect(ac.destination);src.start(0);
1016 |     setTimeout(function(){try{ac.close();}catch(e){}},500);
1017 |   }catch(e){}
1018 | 
1019 |   /* Also "unlock" video element immediately */
1020 |   vid.muted=true;
1021 |   vid.play().catch(function(){});
1022 | 
1023 |   /* Pre-unlock Audio element for PATH B (chat responses) */
1024 |   window._audioUnlocked = new Audio();
1025 |   window._audioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1026 |   window._audioUnlocked.volume = 0.001;
1027 |   window._audioUnlocked.play().catch(function(){});
1028 | 
1029 |   window._chatAudioPlaying = false;
1030 | 
1031 |   navigator.mediaDevices.getUserMedia({audio:true,video:false})
1032 |     .then(function(stream){
1033 |       stream.getTracks().forEach(function(t){t.stop();}); /* don't need stream, just the gesture */
1034 |       gStatus.textContent='';
1035 |       go();
1036 |     })
1037 |     .catch(function(err){
1038 |       console.warn('[Satomi mic error]', err);
1039 |       gBtn.disabled=false;
1040 |       gStatus.textContent='';
1041 |       gErr.style.display='block';
1042 |       var name = err && err.name ? err.name : '';
1043 |       var msg='';
1044 |       if(name === 'NotAllowedError' || name === 'PermissionDeniedError'){
1045 |         msg='Microphone access denied. Allow mic in your browser settings, then retry.';
1046 |       } else if(name === 'NotReadableError' || name === 'TrackStartError'){
1047 |         msg='Microphone busy. Close other apps using the mic.';
1048 |       } else if(name === 'NotFoundError'){
1049 |         msg='No microphone detected.';
1050 |       } else {
1051 |         msg='Microphone unavailable'+(name?' ('+name+')':'.')+'.';
1052 |       }
1053 |       /* P0: Styled error + text fallback — demo never stops */
1054 |       gErr.innerHTML='<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;letter-spacing:.1em;color:rgba(255,59,95,.7);text-transform:uppercase;margin-bottom:6px;">MIC UNAVAILABLE</div>'
1055 |         +'<div style="font-size:12px;color:rgba(255,255,255,.7);margin-bottom:12px;line-height:1.5;">'+msg+'</div>'
1056 |         +'<div style="display:flex;flex-direction:column;gap:8px;">'
1057 |         +'<button onclick="requestMic()" style="background:rgba(255,59,95,.1);border:1px solid rgba(255,59,95,.3);color:#ff3b5f;font-family:\'JetBrains Mono\',monospace;font-size:11px;letter-spacing:.05em;padding:10px 16px;border-radius:4px;cursor:pointer;font-weight:600;">RETRY MIC ACCESS</button>'
1058 |         +'<button onclick="goTextMode()" style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.15);color:#fff;font-family:\'JetBrains Mono\',monospace;font-size:11px;letter-spacing:.05em;padding:10px 16px;border-radius:4px;cursor:pointer;font-weight:600;">CONTINUE WITH TEXT INPUT</button>'
1059 |         +'</div>';
1060 |     });
1061 | }
1062 | 
1063 | /* ── TRANSITION ── */
1064 | function go(){
1065 |   gate.style.opacity='0';
1066 |   setTimeout(function(){
1067 |     gate.style.display='none';
1068 |     stage.style.display='flex';
1069 |     stage.style.opacity='0';
1070 |     setTimeout(function(){
1071 |       stage.style.transition='opacity .45s';
1072 |       stage.style.opacity='1';
1073 |       initSR();
1074 |       setOracleState('WELCOME');
1075 |       playIntent('GREETING');
1076 |       setupTapFallback(); /* FIX 4: register tap-to-speak safety net */
1077 |     },30);
1078 |   },350);
1079 | }
1080 | 
1081 | /* ── PLAY CACHED INTENT ── */
1082 | function playIntent(intent){
1083 |   if(busy&&intent!=='GREETING')return;
1084 |   if(intent.indexOf('DAILY_BRIEF')===0&&window._briefFetched)return;
1085 |   setBusy(true);
1086 |   setStat('Satomi loading\u2026','#f4c46f',true);
1087 |   // Show thinking loop during intent loading (never dark screen)
1088 |   try{vid.muted=true;vid.loop=true;vid.src=A+'/oracle/thinking';vid.style.opacity='1';vid.play().catch(function(){vid.style.opacity='0';});}catch(e){}
1089 |   // Progress messages so user knows it's working, not broken
1090 |   var _loadMsgs = ['Initializing\u2026','Rendering response\u2026','Almost ready\u2026'];
1091 |   var _loadIdx = 0;
1092 |   var _loadTimer = setInterval(function(){
1093 |     _loadIdx++;
1094 |     if(_loadIdx < _loadMsgs.length) setStat(_loadMsgs[_loadIdx],'#f4c46f',true);
1095 |     else clearInterval(_loadTimer);
1096 |   }, 6000);
1097 |   var _clearTimer = function(){ clearInterval(_loadTimer); };
1098 |   fetchTO(A+'/oracle/speak',{
1099 |     method:'POST',
1100 |     headers:{'Content-Type':'application/json'},
1101 |     body:JSON.stringify({intent:intent})
1102 |   },30000)
1103 |   .then(function(r){
1104 |     if(!r.ok)throw new Error('HTTP '+r.status);
1105 |     var ct=r.headers.get('content-type')||'';
1106 |     if(ct.indexOf('video')>=0)return r.blob().then(blobURL);
1107 |     return r.json().then(function(j){
1108 |       return fetchTO(A+j.video_url,{},20000).then(function(r2){return r2.blob().then(blobURL);});
1109 |     });
1110 |   })
1111 |   .then(function(url){
1112 |     if(typeof _clearTimer=='function') _clearTimer();
1113 |     /* FIX 2: Start independent mic activation timer BEFORE video plays.
1114 |        This fires regardless of whether playVid() Promise resolves. */
1115 |     if(intent==='GREETING'){
1116 |       var _estDuration=8; /* estimated greeting video duration in seconds */
1117 |       console.log('[Satomi] Greeting video starting — mic timer set for',_estDuration+1,'s');
1118 |       setTimeout(function(){
1119 |         console.log('[Satomi] Independent mic timer fired — _greeted:',_greeted,'busy:',busy,'isRec:',isRec);
1120 |         if(_greeted&&!busy&&!isRec&&mic&&recognition){
1121 |           mic.disabled=false;
1122 |           startRec();
1123 |           setStat('Listening\u2026','#6cff9f',false);
1124 |         }
1125 |       },(_estDuration+1)*1000);
1126 |     }
1127 |     return playVid(url);
1128 |   })
1129 |   .then(function(){
1130 |     if(intent==='SOVEREIGNTY_ASSESSMENT')showCards();
1131 |     /* FIX 4: Always reset _audioFinished after response plays */
1132 |     _audioFinished=false;
1133 |     if(intent==='GREETING'){
1134 |       window._briefFetched=false;
1135 |       _greeted=true;
1136 |       console.log('[Satomi] Greeting .then() — activating mic');
1137 |       /* FIX 3: Explicit setBusy(false) BEFORE mic activation */
1138 |       setBusy(false);
1139 |       setOracleState('LISTENING');
1140 |       /* FIX 2 cont: Call startRec directly — no setTimeout for iOS gesture trust */
1141 |       if(!isRec&&mic&&recognition){
1142 |         mic.disabled=false;
1143 |         startRec();
1144 |         setStat('Listening\u2026','#6cff9f',false);
1145 |       }
1146 |     }
1147 |   })
1148 |   .catch(function(e){
1149 |     console.warn('[Satomi] playIntent catch:',e);
1150 |     /* On any error (including playVid timeout), ensure mic activates for greeting */
1151 |     if(intent==='GREETING'){
1152 |       _greeted=true;
1153 |       setBusy(false);
1154 |       setOracleState('LISTENING');
1155 |       if(!isRec&&mic&&recognition){
1156 |         mic.disabled=false;
1157 |         startRec();
1158 |         setStat('Listening\u2026','#6cff9f',false);
1159 |       }
1160 |     } else {
1161 |       if(e&&e.message&&String(e.message).indexOf('HTTP')>=0)
1162 |         setStat('Satomi error \u2014 try again.','#ff3b5f',false);
1163 |     }
1164 |   })
1165 |   .finally(function(){
1166 |     setBusy(false);
1167 |     setOracleState('LISTENING');
1168 |     setTimeout(pulseMic,500);
1169 |   });
1170 | }
1171 | 
1172 | function si(intent){if(busy)return;hideCards();playIntent(intent);}
1173 | 
1174 | /* ── PROCESS SPEECH (two-phase: audio-first + async video) ── */
1175 | function process(text){
1176 |   console.log('[Satomi] process() called — text:',JSON.stringify((text||'').substring(0,50)),'busy:',busy);
1177 |   /* FIX: Hard-stop any currently playing video/audio before starting response */
1178 |   try{vid.pause();vid.loop=false;}catch(e){} /* do not mute — let playVid control mute state */
1179 |   try{if(window._chatAudioEl){window._chatAudioEl.pause();window._chatAudioEl.currentTime=0;window._chatAudioPlaying=false;}}catch(e){}
1180 |   _audioFinished=false;
1181 |   if(!text.trim()||busy)return;
1182 |   // Guard: mark brief as fetched to prevent double-play with DAILY_BRIEF_INTRO
1183 |   if(/daily\s*brief/i.test(text)) window._briefFetched=true;
1184 |   setOracleState('PROCESSING');
1185 |   setBusy(true);hideCards();hideActionCard();showTX(text);
1186 | 
1187 |   // P0-3: Elapsed time counter — show "Satomi is thinking... Xs" with live counter
1188 |   var _thinkStart=Date.now();
1189 |   var _thinkReassured=false;
1190 |   setStat('Satomi is thinking\u2026 0s','#f4c46f',true);
1191 |   var _thinkTimer=setInterval(function(){
1192 |     var elapsed=Math.floor((Date.now()-_thinkStart)/1000);
1193 |     // P0-4: Reassurance message after 15s
1194 |     if(elapsed>=15&&!_thinkReassured){
1195 |       _thinkReassured=true;
1196 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1197 |     } else if(!_thinkReassured){
1198 |       setStat('Satomi is thinking\u2026 '+elapsed+'s','#f4c46f',true);
1199 |     } else {
1200 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1201 |     }
1202 |   },1000);
1203 |   window._thinkTimer=_thinkTimer;
1204 | 
1205 |   // Phase 2 T1.4: Play thinking loop immediately for instant visual feedback
1206 |   // P0-2: Add onerror fallback — if thinking video fails, show static avatar
1207 |   vid.muted=true;
1208 |   vid.loop=true;
1209 |   vid.src=A+'/oracle/thinking';
1210 |   vid.style.opacity='1';
1211 |   vid.onerror=function(){
1212 |     console.warn('[Satomi] thinking video failed — showing static avatar');
1213 |     vid.style.opacity='0'; /* static avatar image underneath is always visible */
1214 |   };
1215 |   vid.play().catch(function(e){
1216 |     console.warn('[Satomi] thinking autoplay blocked:',e);
1217 |     vid.style.opacity='0'; /* fallback to static avatar */
1218 |   });
1219 | 
1220 |   // Re-unlock audio context on every user interaction
1221 |   try{
1222 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1223 |     if(_ac.state==='suspended') _ac.resume();
1224 |     var _buf=_ac.createBuffer(1,1,22050);
1225 |     var _src=_ac.createBufferSource();
1226 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1227 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1228 |   }catch(e){}
1229 | 
1230 |   var pendingVideoUrl=null;
1231 |   var _audioFinished=false;
1232 | 
1233 |   fetchTO(A+'/oracle/chat',{
1234 |     method:'POST',headers:{'Content-Type':'application/json'},
1235 |     body:JSON.stringify({text:text,session_id:SESSION_ID,visitor_token:window._visitorToken||'anon',use_cache_for_intents:true,page_context:PAGE_CONTEXT,audio_first:false,avatar_source:"oracle_studio"})
1236 |   },90000)
1237 |   .then(function(r){
1238 |     if(!r.ok) throw new Error('HTTP '+r.status);
1239 |     var ct=r.headers.get('content-type')||'';
1240 |     if(ct.indexOf('video')>=0){
1241 |       // Cache hit — video came back immediately
1242 |       return r.blob().then(blobURL).then(function(url){ return playVid(url); });
1243 |     }
1244 |     // Audio-first JSON response
1245 |     return r.json().then(function(j){
1246 |       var responseText=j.text;
1247 |       var videoJobId=j.job_id;
1248 |       var _pendingCard = j.action_card || null;
1249 | 
1250 |       // Video-first: poll for lip sync video, play once, restart mic
1251 |       setStat('Satomi is thinking… 0s','#f4c46f',true);
1252 |       var _pollAttempts=0, _maxAttempts=45, _pollDone=false;
1253 |       var _thinkSec=0;
1254 | 
1255 |       function _pollForVideo(){
1256 |         if(_pollDone) return;
1257 |         _pollAttempts++;
1258 |         _thinkSec=Math.round(_pollAttempts*2);
1259 |         setStat('Satomi is thinking… '+_thinkSec+'s','#f4c46f',true);
1260 | 
1261 |         fetch(A+'/oracle/job/'+videoJobId)
1262 |           .then(function(vr){
1263 |             if(_pollDone) return null;
1264 |             if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1265 |               return vr.blob();
1266 |             }
1267 |             return null;
1268 |           })
1269 |           .then(function(vb){
1270 |             if(_pollDone) return;
1271 |             if(vb && vb.size > 10000){
1272 |               _pollDone=true;
1273 |               var url=blobURL(vb);
1274 |               /* Stop thinking counter */
1275 |               if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1276 |               setStat('Speaking','#6cff9f',false);
1277 |               /* Play lip sync video — it has baked audio */
1278 |               playVid(url)
1279 |                 .then(function(){
1280 |                   /* Video finished — restart conversation */
1281 |                   setBusy(false);
1282 |                   setOracleState('LISTENING');
1283 |                   hideTX();
1284 |                   setTimeout(startRec, 600);
1285 |                 })
1286 |                 .catch(function(e){
1287 |                   console.warn('[Satomi] playVid error:',e);
1288 |                   setBusy(false);
1289 |                   setOracleState('LISTENING');
1290 |                   setTimeout(startRec, 600);
1291 |                 });
1292 |             } else if(_pollAttempts < _maxAttempts){
1293 |               /* Not ready yet — poll again in 2s */
1294 |               setTimeout(_pollForVideo, 2000);
1295 |             } else {
1296 |               /* Timeout — give up, restart mic */
1297 |               console.warn('[Satomi] Video poll timeout');
1298 |               setBusy(false);
1299 |               setOracleState('LISTENING');
1300 |               setStat('Tap mic to respond','#ff3b5f',false);
1301 |               setTimeout(startRec, 800);
1302 |             }
1303 |           })
1304 |           .catch(function(){ if(_pollAttempts < _maxAttempts) setTimeout(_pollForVideo,2000); });
1305 |       }
1306 | 
1307 |       /* Start polling in 2s (give GPU time to start rendering) */
1308 |       setTimeout(_pollForVideo, 2000);
1309 | 
1310 |       /* Return resolved promise so outer .then() fires immediately */
1311 |       return Promise.resolve();
1312 |       });
1313 |     });
1314 |   })
1315 |   .then(function(){
1316 |     /* Auto-restart mic after every response — conversational flow */
1317 |     setTimeout(function(){
1318 |       if(_greeted&&!busy&&!isRec&&mic&&recognition){
1319 |         mic.disabled=false;
1320 |         setStat('Listening…','#6cff9f',false);
1321 |         try{ recognition.start(); isRec=true; setRec(true); }
1322 |         catch(e){ console.warn('[Satomi] post-response startRec:',e); }
1323 |       }
1324 |     }, 800); /* 800ms gap after video ends before mic opens */
1325 |   })
1326 |   .catch(function(e){
1327 |     console.error('process error:',e);
1328 |     var msg=(e&&e.message)||'';
1329 |     /* P1: 429/503 — server overloaded, auto-retry after 5s */
1330 |     if(msg.indexOf('429')>=0||msg.indexOf('503')>=0){
1331 |       vid.style.opacity='0';
1332 |       setStat('Satomi is meditating\u2026 retrying in 5s','#f4c46f',true);
1333 |       var _retryText=text;
1334 |       setTimeout(function(){
1335 |         setBusy(false);
1336 |         if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1337 |         setOracleState('LISTENING');
1338 |         if(_retryText)process(_retryText);
1339 |       },5000);
1340 |       return; /* skip .finally cleanup — retry will handle it */
1341 |     } else if(msg.indexOf('timeout')>=0){
1342 |       vid.style.opacity='0';
1343 |       setStat('Request timed out — tap mic to retry','#f4c46f',false);
1344 |     } else if(msg.indexOf('HTTP')>=0){
1345 |       vid.style.opacity='0';
1346 |       setStat('Satomi error — tap mic to retry','#ff3b5f',false);
1347 |     } else if(msg.indexOf('Failed to fetch')>=0||msg.indexOf('NetworkError')>=0){
1348 |       vid.style.opacity='0';
1349 |       setStat('Network error — check connection','#ff3b5f',false);
1350 |     }
1351 |   })
1352 |   .finally(function(){
1353 |     if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1354 |     setBusy(false);hideTX();
1355 |     setOracleState('LISTENING');
1356 |     /* Ensure mic restarts after any error path too */
1357 |     setTimeout(function(){
1358 |       if(_greeted&&!busy&&!isRec&&mic&&recognition){
1359 |         mic.disabled=false;
1360 |         try{ recognition.start(); isRec=true; setRec(true); setStat('Listening…','#6cff9f',false); }
1361 |         catch(e){ setStat('Tap mic to respond','#ff3b5f',false); }
1362 |       }
1363 |     }, 1000);
1364 |   });
1365 | }
1366 | 
1367 | function blobURL(b){
1368 |   if(objURL)try{URL.revokeObjectURL(objURL);}catch(e){}
1369 |   objURL=URL.createObjectURL(b);
1370 |   return objURL;
1371 | }
1372 | 
1373 | /* ── PLAY VIDEO (FIX 1: settled guard + timeupdate fallback + dynamic timeout) ── */
1374 | function playVid(url){
1375 |   return new Promise(function(res,rej){
1376 |     console.log('[Satomi] playVid called:',url&&url.substring(0,60));
1377 |     setOracleState('RESPONDING');
1378 |     /* FORENSIC FIX: Fully reset video element before loading new source.
1379 |        iOS Safari requires pause+clear+load when switching from thinking loop.
1380 |        Without this, iOS shows the frozen last frame of the previous video. */
1381 |     vid.onerror=null;vid.onended=null;vid.ontimeupdate=null;
1382 |     vid.pause();
1383 |     vid.removeAttribute('src');
1384 |     vid.load();
1385 |     vid.loop=false;
1386 |     vid.muted=false; /* Always unmute — the video IS the audio source */
1387 |     vid.src=url;
1388 |     vid.style.opacity='1';
1389 |     if(window._matrixHide) window._matrixHide();
1390 | 
1391 |     /* Settled guard — prevents double-resolution from onended/onerror/safety/timeupdate */
1392 |     var _settled=false;
1393 |     function _finish(ok){
1394 |       if(_settled)return;
1395 |       _settled=true;
1396 |       clearTimeout(_safetyTimer);
1397 |       clearTimeout(_dynamicTimer);
1398 |       vid.ontimeupdate=null;
1399 |       if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1400 |       console.log('[Satomi] playVid settled via:',ok?'success':'error/timeout');
1401 |       vid.onended=null;vid.onerror=null;
1402 |       vid.style.opacity='0';
1403 |       setTimeout(function(){ try{vid.pause();vid.removeAttribute('src');vid.load();}catch(e){} },300);
1404 |       if(window._matrixShow) window._matrixShow();
1405 |       hideSub();
1406 |       try{if(window.parent!==window) window.parent.postMessage({type:'oracle:idle'},'*');}catch(e){}
1407 |       /* FIX 1: Always resolve — even on error — so .then() chain continues */
1408 |       res();
1409 |     }
1410 | 
1411 |     /* Safety timeout: fixed 12s fallback (covers worst case if duration unknown) */
1412 |     var _safetyTimer=setTimeout(function(){
1413 |       if(!_settled){
1414 |         console.warn('[Satomi] Safety timeout — forcing playVid resolve');
1415 |         setStat('Ready','#6cff9f',false);
1416 |         _finish(false);
1417 |       }
1418 |     },12000);
1419 | 
1420 |     /* Dynamic timeout: set once we know actual duration (duration + 3s buffer) */
1421 |     var _dynamicTimer=null;
1422 |     vid.addEventListener('loadedmetadata',function _onmeta(){
1423 |       vid.removeEventListener('loadedmetadata',_onmeta);
1424 |       if(_settled)return;
1425 |       var dur=vid.duration;
1426 |       if(dur&&isFinite(dur)){
1427 |         clearTimeout(_safetyTimer);
1428 |         var timeoutMs=Math.ceil(dur*1000)+3000;
1429 |         console.log('[Satomi] Dynamic timeout set:',timeoutMs+'ms for',dur+'s video');
1430 |         _dynamicTimer=setTimeout(function(){
1431 |           if(!_settled){
1432 |             console.warn('[Satomi] Dynamic safety timeout fired after',dur+'s video');
1433 |             setStat('Ready','#6cff9f',false);
1434 |             _finish(false);
1435 |           }
1436 |         },timeoutMs);
1437 |       }
1438 |     });
1439 | 
1440 |     /* timeupdate near-end fallback: catches iOS onended suppression */
1441 |     vid.ontimeupdate=function(){
1442 |       if(!_settled&&vid.duration>0&&vid.currentTime>=vid.duration-0.3){
1443 |         console.log('[Satomi] timeupdate near-end fallback triggered');
1444 |         _finish(true);
1445 |       }
1446 |     };
1447 | 
1448 |     try{if(window.parent!==window) window.parent.postMessage({type:'oracle:speaking'},'*');}catch(e){}
1449 |     vid.onended=function(){
1450 |       console.log('[Satomi] vid.onended fired');
1451 |       _finish(true);
1452 |     };
1453 |     vid.onerror=function(e){
1454 |       console.warn('[Satomi] vid.onerror:',e);
1455 |       /* FORENSIC FIX: No "Recovering" deadlock — finish cleanly so state machine continues */
1456 |       _finish(false);
1457 |     };
1458 |     /* Status update when video starts playing */
1459 |     vid.addEventListener('canplay',function oncp(){
1460 |       vid.removeEventListener('canplay',oncp);
1461 |       setStat('Speaking','#6cff9f',false);
1462 |       vid.muted=false; /* Ensure unmuted — no conditions */
1463 |       vid.volume=1.0;
1464 |     },{once:true});
1465 |     var p=vid.play();
1466 |     if(p){
1467 |       p.then(function(){}).catch(function(err){
1468 |         console.warn('[Satomi] vid.play() rejected (autoplay):',err);
1469 |         /* P0: iOS Safari — show centered tap-to-play overlay */
1470 |         showTapOverlay();
1471 |       });
1472 |     }
1473 |   });
1474 | }
1475 | 
1476 | /* ── SPEECH RECOGNITION ── */
1477 | function initSR(){
1478 |   /* iOS-safe: test only, actual instances created fresh per session */
1479 |   var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
1480 |   if(!SR){ micHint.textContent='no speech api'; return; }
1481 |   window._SR = SR; /* store constructor */
1482 |   console.log('[Satomi] SR available');
1483 | }
1484 | 
1485 | function _newRecognition(){
1486 |   if(!window._SR) return null;
1487 |   var r = new window._SR();
1488 |   r.continuous = false;       /* single-shot: fires onend reliably on iOS */
1489 |   r.interimResults = true;
1490 |   r.lang = 'en-US';
1491 |   r.maxAlternatives = 1;
1492 |   return r;
1493 | }
1494 | 
1495 | function toggleMic(){
1496 |   if(busy) return;
1497 |   if(isRec){ _submitSpeech(); } else { startRec(); }
1498 | }
1499 | 
1500 | function startRec(){
1501 |   if(!window._SR){ setStat('No speech API','#ff3b5f',false); return; }
1502 |   if(isRec) return; /* already recording */
1503 | 
1504 |   /* Always create fresh recognition instance — iOS InvalidStateError fix */
1505 |   recognition = _newRecognition();
1506 |   if(!recognition) return;
1507 | 
1508 |   var _transcript = '';   /* captured in closure — survives onend */
1509 |   var _submitted  = false;
1510 | 
1511 |   recognition.onresult = function(e){
1512 |     var fin='', int='';
1513 |     for(var i=0; i<e.results.length; i++){
1514 |       if(e.results[i].isFinal) fin += e.results[i][0].transcript;
1515 |       else                      int += e.results[i][0].transcript;
1516 |     }
1517 |     if(fin){ _transcript = fin; }
1518 |     else if(int && !_transcript){ _transcript = int; } /* keep best */
1519 |     showTX(_transcript || int);
1520 |     pending = _transcript; /* keep global in sync */
1521 |   };
1522 | 
1523 |   recognition.onend = function(){
1524 |     setRec(false); isRec = false;
1525 |     var text = (_transcript || pending || '').trim();
1526 |     _transcript = ''; pending = ''; window._interimPending = '';
1527 |     console.log('[Satomi] onend text:', JSON.stringify(text.substring(0,50)), 'busy:', busy, 'submitted:', _submitted);
1528 |     if(_submitted) return; /* already handled by _submitSpeech */
1529 |     if(text && !busy){
1530 |       setStat('Processing…','#f4c46f',true);
1531 |       setTimeout(function(){ process(text); }, 100);
1532 |     } else if(!busy && _greeted){
1533 |       /* No speech — restart listening after brief pause */
1534 |       setStat('Listening…','#6cff9f',false);
1535 |       setTimeout(startRec, 600);
1536 |     }
1537 |   };
1538 | 
1539 |   recognition.onerror = function(e){
1540 |     console.warn('[Satomi] SR error:', e.error);
1541 |     setRec(false); isRec = false;
1542 |     if(e.error === 'no-speech'){
1543 |       if(_greeted && !busy) setTimeout(startRec, 600);
1544 |     } else if(e.error === 'not-allowed'){
1545 |       setStat('Mic permission denied','#ff3b5f',false);
1546 |     }
1547 |   };
1548 | 
1549 |   isRec = true; setRec(true);
1550 |   setStat('Listening…','#6cff9f',false);
1551 |   pending = ''; _transcript = '';
1552 |   try{
1553 |     recognition.start();
1554 |     console.log('[Satomi] recognition.start() OK');
1555 |   } catch(e){
1556 |     console.warn('[Satomi] recognition.start() error:', e.message);
1557 |     isRec = false; setRec(false);
1558 |     setStat('Tap mic to speak','#ff3b5f',false);
1559 |   }
1560 | }
1561 | 
1562 | function _submitSpeech(){
1563 |   /* Called by tap-to-send — stop recognition and submit what we have */
1564 |   if(!recognition) return;
1565 |   var text = (pending || window._interimPending || '').trim();
1566 |   console.log('[Satomi] _submitSpeech:', JSON.stringify(text.substring(0,40)));
1567 |   if(text && !busy){
1568 |     /* Mark as submitted so onend doesn't double-submit */
1569 |     try{ recognition._submitted = true; }catch(e){}
1570 |     isRec = false; setRec(false);
1571 |     try{ recognition.stop(); }catch(e){}
1572 |     setStat('Processing…','#f4c46f',true);
1573 |     setTimeout(function(){ process(text); pending=''; window._interimPending=''; }, 150);
1574 |   } else {
1575 |     /* No text yet — just stop, onend will handle */
1576 |     isRec = false; setRec(false);
1577 |     try{ recognition.stop(); }catch(e){}
1578 |   }
1579 | }
1580 | 
1581 | function stopRec(){
1582 |   /* Called internally — just stop, let onend handle submission */
1583 |   isRec = false; setRec(false);
1584 |   if(recognition) try{ recognition.stop(); }catch(e){}
1585 | }
1586 | 
1587 | function setRec(on){
1588 |   mic.classList.toggle('rec',on);
1589 |   iMic.style.display  = on?'none':'block';
1590 |   iStop.style.display = on?'block':'none';
1591 |   micHint.textContent = on?'tap to send':'tap to speak';
1592 | }
1593 | 
1594 | /* ── HELPERS ── */
1595 | function setStat(t,c,sp){statEl.textContent=t;statEl.style.color=c||'#334';spinEl.style.display=sp?'block':'none';spinEl.style.color=c||'#334';}
1596 | function setBusy(b){busy=b;if(b){mic.disabled=true;if(isRec)stopRec();}else{mic.disabled=false;}}
1597 | function showSub(t){sub.textContent=t;sub.classList.add('on');}
1598 | function hideSub(){sub.classList.remove('on');}
1599 | function showTX(t){txEl.textContent=t;txEl.classList.add('on');}
1600 | function hideTX(){txEl.classList.remove('on');}
1601 | function showCards(){cards.classList.add('on');}
1602 | function hideCards(){cards.classList.remove('on');}
1603 | 
1604 | /* ── TAP-TO-PLAY OVERLAY (P0: iOS Safari autoplay) ── */
1605 | function showTapOverlay(){
1606 |   var ov=document.getElementById('tap-to-play');
1607 |   if(ov){ov.style.display='flex';}
1608 |   setStat('Tap to play','#f4c46f',false);
1609 |   /* P2 FORENSIC FIX (Grok): Auto-dismiss after 10s if user ignores — prevents permanent UI block */
1610 |   setTimeout(function(){
1611 |     if(ov&&ov.style.display==='flex'){
1612 |       ov.style.display='none';
1613 |       vid.style.opacity='0';
1614 |       setStat('Ready','#334',false);
1615 |       setBusy(false);
1616 |       setOracleState('LISTENING');
1617 |     }
1618 |   },10000);
1619 | }
1620 | function dismissTapOverlay(){
1621 |   var ov=document.getElementById('tap-to-play');
1622 |   if(ov){ov.style.display='none';}
1623 |   vid.muted=false;vid.volume=1.0;
1624 |   vid.play().then(function(){
1625 |     setStat('Speaking','#6cff9f',false);
1626 |   }).catch(function(e){
1627 |     console.warn('[Satomi] tap-to-play retry failed:',e);
1628 |     vid.style.opacity='0';
1629 |     setStat('Ready','#334',false);
1630 |   });
1631 | }
1632 | 
1633 | /* ── TEXT INPUT FALLBACK (P0: mic failure → text mode) ── */
1634 | var _textMode=false;
1635 | function goTextMode(){
1636 |   /* Skip mic, transition straight to stage with text input visible */
1637 |   _textMode=true;
1638 |   gBtn.disabled=true;
1639 |   gErr.style.display='none';
1640 |   /* Unlock audio context on this user gesture (same as requestMic) */
1641 |   try{
1642 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1643 |     var _buf=_ac.createBuffer(1,1,22050);var _src=_ac.createBufferSource();
1644 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1645 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1646 |   }catch(e){}
1647 |   vid.muted=true;vid.play().catch(function(){});
1648 |   window._audioUnlocked=new Audio();
1649 |   window._audioUnlocked.src='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1650 |   window._audioUnlocked.volume=0.001;
1651 |   window._audioUnlocked.play().catch(function(){});
1652 |   window._chatAudioPlaying=false;
1653 |   gate.style.opacity='0';
1654 |   setTimeout(function(){
1655 |     gate.style.display='none';
1656 |     stage.style.display='flex';
1657 |     stage.style.opacity='0';
1658 |     setTimeout(function(){
1659 |       stage.style.transition='opacity .45s';
1660 |       stage.style.opacity='1';
1661 |       /* Show text input, hide mic area, init speech recognition (may still work for some) */
1662 |       document.getElementById('stage-text-input').style.display='block';
1663 |       mic.disabled=true;
1664 |       micHint.textContent='text mode';
1665 |       initSR();
1666 |       setOracleState('WELCOME');
1667 |       playIntent('GREETING');
1668 |       /* After greeting, enable mic if SR is available as bonus */
1669 |       setTimeout(function(){
1670 |         if(recognition){mic.disabled=false;micHint.textContent='tap to speak';}
1671 |       },8000);
1672 |     },30);
1673 |   },350);
1674 | }
1675 | function submitTextInput(){
1676 |   var field=document.getElementById('text-input-field');
1677 |   var text=(field.value||'').trim();
1678 |   if(!text)return;
1679 |   field.value='';
1680 |   goTextMode();
1681 |   /* Queue the text to process after greeting finishes */
1682 |   var _waitGreeting=setInterval(function(){
1683 |     if(!busy){clearInterval(_waitGreeting);process(text);}
1684 |   },500);
1685 | }
1686 | function stageTextSubmit(){
1687 |   var field=document.getElementById('stage-text-field');
1688 |   var text=(field.value||'').trim();
1689 |   if(!text||busy)return;
1690 |   field.value='';
1691 |   process(text);
1692 | }
1693 | 
1694 | /* ── GEMINI VISION ── */
1695 | var _visionSessionId = null;
1696 | 
1697 | function updateCameraButtonState() {
1698 |   var lbl = document.getElementById('cam-btn-label');
1699 |   if (!lbl) return;
1700 |   lbl.textContent = _visionSessionId
1701 |     ? 'FOLLOW-UP PHOTO'
1702 |     : 'ANALYZE HARDWARE';
1703 | }
1704 | 
1705 | function triggerCamera(){
1706 |   document.getElementById("cam-input").click();
1707 | }
1708 | 
1709 | function handleVisionUpload(evt){
1710 |   var file = evt.target.files[0];
1711 |   if(!file) return;
1712 |   if (busy) {
1713 |     showVisionStatus('Satomi is speaking — wait a moment');
1714 |     setTimeout(hideVisionStatus, 2000);
1715 |     evt.target.value = "";
1716 |     return;
1717 |   }
1718 |   evt.target.value = "";
1719 |   
1720 |   var reader = new FileReader();
1721 |   reader.onload = function(e){
1722 |     var b64 = e.target.result.split(",")[1];
1723 |     var mime = file.type || "image/jpeg";
1724 |     sendVisionImage(b64, mime);
1725 |   };
1726 |   reader.readAsDataURL(file);
1727 | }
1728 | 
1729 | var SEED_RECOVERY_STEPS = [
1730 |   {
1731 |     label: 'STEP 1 OF 3 — STOP IMMEDIATELY',
1732 |     text: 'Do NOT send any Bitcoin from this wallet until you have moved your funds. Anyone who saw this seed phrase can access your Bitcoin right now.',
1733 |     speak: 'Stop. Do not send any Bitcoin from this wallet. Anyone who saw this seed phrase can steal your funds right now.'
1734 |   },
1735 |   {
1736 |     label: 'STEP 2 OF 3 — MOVE YOUR FUNDS',
1737 |     text: 'On a different device, create a brand new wallet. Generate a NEW seed phrase — write it down on paper only, never photograph it. Transfer ALL funds to the new wallet address immediately.',
1738 |     speak: 'On a different device, create a new wallet with a new seed phrase. Write it on paper only. Transfer all your funds to the new wallet immediately.'
1739 |   },
1740 |   {
1741 |     label: 'STEP 3 OF 3 — SECURE THE NEW WALLET',
1742 |     text: 'Once funds are transferred, the old wallet is abandoned. Store your new seed phrase in a metal backup, split across two secure locations. Never store seed phrases digitally.',
1743 |     speak: 'Once funds are moved, abandon the old wallet. Store your new seed phrase in metal, split across two secure locations. Never store seed phrases digitally.'
1744 |   }
1745 | ];
1746 | 
1747 | function showSecurityAlert(msg, onDismiss) {
1748 |   var overlay = document.getElementById('vision-security-overlay');
1749 |   var msgEl = document.getElementById('vision-security-msg');
1750 |   var dismissBtn = document.getElementById('vision-security-dismiss');
1751 |   var recoveryPanel = document.getElementById('vision-recovery-panel');
1752 |   if (!overlay || !msgEl) return;
1753 | 
1754 |   msgEl.textContent = msg;
1755 |   overlay.style.display = 'flex';
1756 | 
1757 |   // Speak the initial alert urgently
1758 |   function speakText(text) {
1759 |     fetchTO(A+'/oracle/voice', {
1760 |       method: 'POST',
1761 |       headers: {'Content-Type': 'application/json'},
1762 |       body: JSON.stringify({text: text})
1763 |     }, 20000).then(function(r) {
1764 |       if (!r.ok) return;
1765 |       return r.blob();
1766 |     }).then(function(blob) {
1767 |       if (!blob) return;
1768 |       var alertAudio = new Audio(URL.createObjectURL(blob));
1769 |       alertAudio.volume = 1.0;
1770 |       alertAudio.play().catch(function(){});
1771 |     }).catch(function(){});
1772 |   }
1773 | 
1774 |   speakText('SECURITY ALERT. ' + msg +
1775 |     ' Your seed phrase may be compromised. Do not send Bitcoin until you hear the recovery steps.');
1776 | 
1777 |   // Dismiss transitions to recovery steps
1778 |   dismissBtn.onclick = function() {
1779 |     dismissBtn.style.display = 'none';
1780 |     msgEl.style.fontSize = '0.9rem';
1781 |     msgEl.style.opacity = '0.7';
1782 |     recoveryPanel.style.display = 'block';
1783 |     _showRecoveryStep(0, speakText);
1784 |   };
1785 | }
1786 | 
1787 | function _showRecoveryStep(idx, speakFn) {
1788 |   var steps = SEED_RECOVERY_STEPS;
1789 |   var stepLabel = document.getElementById('vision-recovery-step-label');
1790 |   var stepText = document.getElementById('vision-recovery-step-text');
1791 |   var nextBtn = document.getElementById('vision-recovery-next');
1792 |   var helpBtn = document.getElementById('vision-recovery-help');
1793 |   var closeBtn = document.getElementById('vision-recovery-close');
1794 | 
1795 |   if (!stepLabel || !stepText) return;
1796 | 
1797 |   stepLabel.textContent = steps[idx].label;
1798 |   stepText.textContent = steps[idx].text;
1799 |   speakFn(steps[idx].speak);
1800 | 
1801 |   var isLast = (idx === steps.length - 1);
1802 |   nextBtn.style.display = isLast ? 'none' : 'block';
1803 |   helpBtn.style.display = isLast ? 'block' : 'none';
1804 |   closeBtn.style.display = isLast ? 'block' : 'none';
1805 | 
1806 |   nextBtn.onclick = function() {
1807 |     if (idx < steps.length - 1) _showRecoveryStep(idx + 1, speakFn);
1808 |   };
1809 | 
1810 |   helpBtn.onclick = function() {
1811 |     // Close overlay and trigger Satomi to help set up new wallet
1812 |     var overlay = document.getElementById('vision-security-overlay');
1813 |     if (overlay) overlay.style.display = 'none';
1814 |     // Inject a vision guidance request for new wallet setup
1815 |     sendVisionImage(null, null, 'help me set up a new hardware wallet safely');
1816 |   };
1817 | 
1818 |   closeBtn.onclick = function() {
1819 |     var overlay = document.getElementById('vision-security-overlay');
1820 |     if (overlay) overlay.style.display = 'none';
1821 |   };
1822 | }
1823 | 
1824 | function _speakVisionGuidance(d) {
1825 |   var raw = d.guidance_text || d.guidance || d.analysis || d.response
1826 |     || "I can see your hardware. Let me walk you through the next step.";
1827 |   // Hard 30-word cap for TTS speed
1828 |   var words = raw.split(/\s+/);
1829 |   var guideText = words.length > 30 ? words.slice(0,30).join(" ") : raw;
1830 | 
1831 |   // Urgent spoken prefix for transaction verdicts
1832 |   if (d.verdict === 'DO NOT SIGN') {
1833 |     guideText = 'WARNING. DO NOT SIGN THIS TRANSACTION. ' + guideText;
1834 |   } else if (d.verdict === 'REVIEW CAREFULLY' && d.red_flags && d.red_flags.length) {
1835 |     guideText = 'REVIEW CAREFULLY. ' + guideText;
1836 |   }
1837 | 
1838 |   showVisionStatus("Speaking...");
1839 |   showSub(guideText);
1840 | 
1841 |   // Transaction review verdict card
1842 |   if (d.category === 'transaction' && d.verdict) {
1843 |     var verdictColor = d.verdict === 'SAFE TO SIGN'
1844 |       ? '#00d4aa'
1845 |       : d.verdict === 'DO NOT SIGN'
1846 |       ? '#ff3b5f'
1847 |       : '#f5a623';
1848 | 
1849 |     var verdictHtml = '<div style="background:rgba(0,0,0,.4);' +
1850 |       'border:2px solid ' + verdictColor + ';border-radius:8px;' +
1851 |       'padding:12px 16px;margin-bottom:12px;">' +
1852 |       '<div style="font-family:monospace;font-size:10px;' +
1853 |       'letter-spacing:.12em;color:' + verdictColor + ';' +
1854 |       'text-transform:uppercase;margin-bottom:6px;">' +
1855 |       '\u26A1 TRANSACTION ANALYSIS</div>' +
1856 |       '<div style="font-size:1.1rem;font-weight:800;' +
1857 |       'color:' + verdictColor + ';margin-bottom:8px;">' +
1858 |       d.verdict + '</div>';
1859 | 
1860 |     if (d.recipient_address) {
1861 |       verdictHtml += '<div style="font-family:monospace;font-size:10px;' +
1862 |         'color:rgba(255,255,255,.5);word-break:break-all;">' +
1863 |         'TO: ' + d.recipient_address + '</div>';
1864 |     }
1865 |     if (d.amount_btc) {
1866 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1867 |         'color:rgba(255,255,255,.7);margin-top:4px;">' +
1868 |         'AMOUNT: ' + d.amount_btc + ' BTC</div>';
1869 |     }
1870 |     if (d.fee_sats) {
1871 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1872 |         'color:rgba(255,255,255,.6);">' +
1873 |         'FEE: ' + d.fee_sats + ' sats</div>';
1874 |     }
1875 |     if (d.red_flags && d.red_flags.length) {
1876 |       verdictHtml += '<div style="margin-top:8px;">';
1877 |       d.red_flags.forEach(function(flag) {
1878 |         verdictHtml += '<div style="font-family:monospace;font-size:9px;' +
1879 |           'color:#f5a623;letter-spacing:.06em;">\u26A0 ' + flag + '</div>';
1880 |       });
1881 |       verdictHtml += '</div>';
1882 |     }
1883 |     verdictHtml += '</div>';
1884 | 
1885 |     var vsEl = document.getElementById('vision-status');
1886 |     if (vsEl) {
1887 |       vsEl.innerHTML = verdictHtml + (vsEl.innerHTML || '');
1888 |       vsEl.classList.add('on');
1889 |     }
1890 |   }
1891 | 
1892 |   // Show steps in vision-status area if present
1893 |   if(d.steps && d.steps.length){
1894 |     var stepsHtml = d.steps.map(function(s,i){ return (i+1)+". "+s; }).join("<br>");
1895 |     var el=document.getElementById("vision-status");
1896 |     el.innerHTML = (d.device_name && d.device_name!=="unknown" ? "<b>"+d.device_name+"</b><br>" : "") + stepsHtml;
1897 |     el.classList.add("on");
1898 |   }
1899 | 
1900 |   // Add to session transcript
1901 |   _addVisionEntry(d.device_name, d.steps || [], guideText);
1902 | 
1903 |   // VOICE-ONLY: /oracle/voice is ElevenLabs-only, no GPU, ~400ms vs 14s
1904 |   fetchTO(A+"/oracle/voice",{method:"POST",
1905 |     headers:{"Content-Type":"application/json"},
1906 |     body:JSON.stringify({text:guideText})},15000)
1907 |   .then(function(ar){
1908 |     if(!ar.ok) throw new Error("voice "+ar.status);
1909 |     return ar.blob();
1910 |   })
1911 |   .then(function(audioBlob){
1912 |     hideVisionStatus();
1913 |     var audioURL = URL.createObjectURL(audioBlob);
1914 |     var audio;
1915 |     if(window._audioUnlocked){
1916 |       audio=window._audioUnlocked;
1917 |       window._audioUnlocked=null;
1918 |       audio.src=audioURL;
1919 |       audio.volume=1.0;
1920 |       audio.muted=false;
1921 |     } else {
1922 |       audio = new Audio(audioURL);
1923 |       audio.volume = 1.0;
1924 |     }
1925 |     return new Promise(function(res){
1926 |       audio.onended = function(){
1927 |         URL.revokeObjectURL(audioURL);
1928 |         setStat("Ready","#334",false);
1929 |         hideSub();
1930 |         if(d.device_name){
1931 |           setTimeout(function(){ showVisionSponsor(d.device_name); },800);
1932 |         }
1933 |         // Prompt for follow-up photo if session is active
1934 |         if (_visionSessionId) {
1935 |           showVisionStatus('Tap camera to show next screen \u2192');
1936 |           setTimeout(function() {
1937 |             hideVisionStatus();
1938 |           }, 4000);
1939 |         }
1940 |         res();
1941 |       };
1942 |       audio.onerror = function(){ URL.revokeObjectURL(audioURL); res(); };
1943 |       var vp = audio.play();
1944 |       if(vp !== undefined){
1945 |         vp.then(function(){ setStat("Speaking","#6cff9f",false); }).catch(function(){ res(); });
1946 |       }
1947 |     });
1948 |   })
1949 |   .catch(function(){
1950 |     showVisionStatus("Ready");
1951 |     setBusy(false);
1952 |     mic.disabled = false;
1953 |   });
1954 | }
1955 | 
1956 | function sendVisionImage(b64, mimeType, textOverride){
1957 |   // Text-only mode: no image, just a guided question
1958 |   if (!b64 && textOverride) {
1959 |     setBusy(true);
1960 |     showVisionStatus('Preparing guidance...');
1961 |     _speakVisionGuidance({
1962 |       guidance_text: 'I can guide you through setting up a new hardware wallet securely. First, choose a wallet: Coldcard for maximum security, Trezor for ease of use, or SeedSigner for open-source air-gapped signing. Which would you like help with?',
1963 |       device_name: 'new_wallet_setup',
1964 |       steps: [
1965 |         'Choose your hardware wallet: Coldcard, Trezor, or SeedSigner',
1966 |         'Purchase only from official manufacturer websites — never third party',
1967 |         'On first boot, generate a new seed phrase on the device itself',
1968 |         'Write seed phrase on paper only — never photograph or type it',
1969 |         'Test recovery before sending any funds'
1970 |       ]
1971 |     });
1972 |     setBusy(false);
1973 |     return;
1974 |   }
1975 | 
1976 |   setBusy(true);
1977 |   showVisionStatus("Analyzing your screen...");
1978 | 
1979 |   var endpoint = _visionSessionId ? A+"/vision/guide" : A+"/vision/analyze";
1980 |   var body = {image_base64:b64, mime_type:mimeType,
1981 |     context:"User needs Bitcoin hardware setup guidance"};
1982 |   if(_visionSessionId){
1983 |     body.session_id = _visionSessionId;
1984 |     body.question = "What step am I at and what should I do next?";
1985 |     body.last_context = _visionTranscript.length > 0
1986 |       ? _visionTranscript[_visionTranscript.length - 1].steps.join('; ')
1987 |       : '';
1988 |   }
1989 | 
1990 |   fetchTO(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},
1991 |     body:JSON.stringify(body)},20000)
1992 |   .then(function(r){
1993 |     if(!r.ok) throw new Error("vision "+r.status);
1994 |     return r.json();
1995 |   })
1996 |   .then(function(d){
1997 |     _visionSessionId = d.session_id || _visionSessionId;
1998 |     updateCameraButtonState();
1999 | 
2000 |     // Security alert takes absolute priority — recovery flow keeps overlay open
2001 |     if (d.security_alert) {
2002 |       showSecurityAlert(d.security_alert);
2003 |       return;
2004 |     }
2005 |     _speakVisionGuidance(d);
2006 |   })
2007 |   .catch(function(e){
2008 |     console.error("Vision error:", e);
2009 |     showVisionStatus("Vision error — try again.");
2010 |     setTimeout(hideVisionStatus, 3000);
2011 |   })
2012 |   .finally(function(){ setBusy(false); mic.disabled=false; });
2013 | }
2014 | 
2015 | function showVisionStatus(msg){ 
2016 |   var el=document.getElementById("vision-status");
2017 |   el.textContent=msg; el.classList.add("on");
2018 | }
2019 | function hideVisionStatus(){
2020 |   var el=document.getElementById("vision-status");
2021 |   el.classList.remove("on");
2022 | }
2023 | 
2024 | /* ── VISION SESSION TRANSCRIPT ── */
2025 | var _visionTranscript = [];
2026 | 
2027 | function _addVisionEntry(deviceName, steps, guidanceText) {
2028 |   var panel = document.getElementById('vision-transcript-panel');
2029 |   var entries = document.getElementById('vision-transcript-entries');
2030 |   if (!entries) return;
2031 | 
2032 |   if (panel && _visionTranscript.length === 0) {
2033 |     panel.style.display = 'block';
2034 |   }
2035 | 
2036 |   var entry = {
2037 |     device: deviceName || 'Unknown Device',
2038 |     steps: steps || [],
2039 |     guidance: guidanceText || '',
2040 |     time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})
2041 |   };
2042 |   _visionTranscript.push(entry);
2043 | 
2044 |   var el = document.createElement('div');
2045 |   el.className = 'vision-entry';
2046 | 
2047 |   var deviceEl = document.createElement('div');
2048 |   deviceEl.className = 'vision-entry-device';
2049 |   deviceEl.textContent = entry.device.toUpperCase();
2050 |   el.appendChild(deviceEl);
2051 | 
2052 |   if (entry.steps.length) {
2053 |     entry.steps.forEach(function(s, i) {
2054 |       var stepEl = document.createElement('div');
2055 |       stepEl.className = 'vision-entry-step';
2056 |       stepEl.textContent = (i+1) + '. ' + s;
2057 |       el.appendChild(stepEl);
2058 |     });
2059 |   } else if (entry.guidance) {
2060 |     var guidEl = document.createElement('div');
2061 |     guidEl.className = 'vision-entry-step';
2062 |     guidEl.textContent = entry.guidance.substring(0, 120) +
2063 |       (entry.guidance.length > 120 ? '…' : '');
2064 |     el.appendChild(guidEl);
2065 |   }
2066 | 
2067 |   var timeEl = document.createElement('div');
2068 |   timeEl.className = 'vision-entry-time';
2069 |   timeEl.textContent = entry.time + ' — tap to re-read';
2070 |   el.appendChild(timeEl);
2071 | 
2072 |   el.onclick = function() {
2073 |     var text = entry.steps.length
2074 |       ? entry.device + '. ' + entry.steps.join('. ')
2075 |       : entry.guidance;
2076 |     fetchTO(A+'/oracle/voice', {
2077 |       method: 'POST',
2078 |       headers: {'Content-Type': 'application/json'},
2079 |       body: JSON.stringify({text: text.substring(0, 200)})
2080 |     }, 20000).then(function(r) {
2081 |       return r.ok ? r.blob() : null;
2082 |     }).then(function(blob) {
2083 |       if (!blob) return;
2084 |       var a = new Audio(URL.createObjectURL(blob));
2085 |       a.volume = 1.0;
2086 |       a.play().catch(function(){});
2087 |     }).catch(function(){});
2088 |   };
2089 | 
2090 |   entries.appendChild(el);
2091 |   entries.scrollTop = entries.scrollHeight;
2092 | }
2093 | 
2094 | document.addEventListener('DOMContentLoaded', function() {
2095 |   var clearBtn = document.getElementById('vision-transcript-clear');
2096 |   if (clearBtn) {
2097 |     clearBtn.onclick = function() {
2098 |       _visionTranscript = [];
2099 |       var entries = document.getElementById('vision-transcript-entries');
2100 |       if (entries) entries.innerHTML = '';
2101 |       var panel = document.getElementById('vision-transcript-panel');
2102 |       if (panel) panel.style.display = 'none';
2103 |       _visionSessionId = null;
2104 |       updateCameraButtonState();
2105 |     };
2106 |   }
2107 | });
2108 | 
2109 | /* ── MINIMIZE / EXIT / FLOAT ── */
2110 | var _oracleMinimized = false;
2111 | 
2112 | function minimizeOracle(){
2113 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
2114 |   if(inIframe){
2115 |     try{ window.parent.postMessage({type:'oracle:minimize'},'*'); }catch(e){}
2116 |     return;
2117 |   }
2118 |   // Standalone: shrink to float bubble
2119 |   _oracleMinimized = true;
2120 |   document.getElementById("oracle-root").style.display = "none";
2121 |   var f = document.getElementById("oracle-float");
2122 |   if(f){ f.style.display = "flex"; if(busy) f.classList.add("speaking"); }
2123 | }
2124 | 
2125 | function restoreOracle(){
2126 |   _oracleMinimized = false;
2127 |   document.getElementById("oracle-float").style.display = "none";
2128 |   document.getElementById("oracle-root").style.display = "flex";
2129 |   document.getElementById("oracle-float").classList.remove("speaking");
2130 | }
2131 | 
2132 | function exitOracle(){
2133 |   // If running inside widget iframe — tell parent to close
2134 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
2135 |   if(inIframe){
2136 |     try{ window.parent.postMessage({type:'oracle:close'},'*'); }catch(e){}
2137 |     return;
2138 |   }
2139 |   // Standalone page — return to gate screen
2140 |   _oracleMinimized = false;
2141 |   // Stop any playing audio/video
2142 |   vid.pause(); vid.src="";
2143 |   if(isRec) stopRec();
2144 |   // Reset session on server
2145 |   fetch(A+"/oracle/session/reset",{method:"POST",
2146 |     headers:{"Content-Type":"application/json"},
2147 |     body:JSON.stringify({session_id:SESSION_ID})}).catch(function(){});
2148 |   // Hide everything
2149 |   document.getElementById("oracle-float").style.display = "none";
2150 |   document.getElementById("live-stage").style.display = "none";
2151 |   document.getElementById("oracle-root").style.display = "flex";
2152 |   // Show gate again
2153 |   var g = document.getElementById("gate");
2154 |   g.style.display = "flex";
2155 |   g.style.opacity = "1";
2156 |   g.style.transition = "opacity .3s";
2157 |   // Reset state
2158 |   busy = false; window._briefFetched = false;
2159 |   setStat("Ready","#334",false);
2160 |   hideSub(); hideTranscript && hideTX();
2161 | }
2162 | 
2163 | // Keep float speaking indicator in sync
2164 | var _origSetStat = setStat;
2165 | setStat = function(msg, color, spin){
2166 |   _origSetStat(msg, color, spin);
2167 |   var f = document.getElementById("oracle-float");
2168 |   if(f && _oracleMinimized){
2169 |     if(msg === "Speaking") f.classList.add("speaking");
2170 |     else f.classList.remove("speaking");
2171 |   }
2172 | };
2173 | 
2174 | /* ── ORACLE IDLE MATRIX ANIMATION ── */
2175 | (function(){
2176 |   var canvas = document.getElementById('oracle-matrix');
2177 |   if (!canvas) return;
2178 |   var ctx = canvas.getContext('2d');
2179 |   var chars = '01₿⚡∆Ω█▓░10₿Ξ∞◆'.split('');
2180 |   var cols, drops;
2181 | 
2182 |   function resize() {
2183 |     canvas.width = canvas.offsetWidth;
2184 |     canvas.height = canvas.offsetHeight;
2185 |     cols = Math.floor(canvas.width / 14);
2186 |     drops = Array(cols).fill(1);
2187 |   }
2188 |   resize();
2189 |   window.addEventListener('resize', resize);
2190 | 
2191 |   function draw() {
2192 |     ctx.fillStyle = 'rgba(4,5,8,0.05)';
2193 |     ctx.fillRect(0, 0, canvas.width, canvas.height);
2194 |     ctx.font = '11px monospace';
2195 |     for (var i = 0; i < drops.length; i++) {
2196 |       var char = chars[Math.floor(Math.random() * chars.length)];
2197 |       var alpha = Math.random() * 0.4 + 0.05;
2198 |       var cx = canvas.width / 2;
2199 |       var dist = Math.abs(i * 14 - cx) / cx;
2200 |       var r = Math.floor(180 + (1 - dist) * 75);
2201 |       var g = Math.floor(20 + (1 - dist) * 30);
2202 |       var b = Math.floor(40 + (1 - dist) * 20);
2203 |       ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
2204 |       ctx.fillText(char, i * 14, drops[i] * 14);
2205 |       if (drops[i] * 14 > canvas.height && Math.random() > 0.975) drops[i] = 0;
2206 |       drops[i]++;
2207 |     }
2208 |   }
2209 | 
2210 |   var _matrixInterval = setInterval(draw, 50);
2211 | 
2212 |   window._matrixHide = function() {
2213 |     canvas.style.opacity = '0';
2214 |   };
2215 |   window._matrixShow = function() {
2216 |     /* P0-1: Subtle overlay so static avatar face stays visible during idle */
2217 |     canvas.style.opacity = '0.35';
2218 |   };
2219 | })();
2220 | 
2221 | /* ── CYBERPUNK MATRIX BACKGROUND ── */
2222 | (function(){
2223 |   var cvs=document.getElementById('bg-canvas');
2224 |   if(!cvs)return;
2225 |   var ctx=cvs.getContext('2d');
2226 |   var W,H,cols,drops,hexFrags=[];
2227 |   var matrixChars='0123456789ABCDEFabcdef₿⚡∆Ω█▓░▒╔╗╚╝║═';
2228 |   var fontSize=14;
2229 |   var scanY=-2,scanDir=1,scanTimer=0,scanInterval=15000;
2230 | 
2231 |   function resize(){
2232 |     W=cvs.width=cvs.offsetWidth;
2233 |     H=cvs.height=cvs.offsetHeight;
2234 |     cols=Math.floor(W/fontSize);
2235 |     drops=new Array(cols);
2236 |     for(var i=0;i<cols;i++) drops[i]=Math.random()*(-H/fontSize);
2237 |   }
2238 |   resize();
2239 |   window.addEventListener('resize',resize);
2240 | 
2241 |   // Hex fragments: random hex strings that fade in/out
2242 |   function spawnHex(){
2243 |     if(hexFrags.length>6) return;
2244 |     hexFrags.push({
2245 |       x:Math.random()*W,
2246 |       y:Math.random()*H,
2247 |       text:'0x'+Math.random().toString(16).substr(2,6).toUpperCase(),
2248 |       alpha:0,phase:0, // 0=fade in, 1=hold, 2=fade out
2249 |       speed:0.003+Math.random()*0.005,
2250 |       holdTime:2000+Math.random()*3000,
2251 |       holdStart:0
2252 |     });
2253 |   }
2254 | 
2255 |   var lastTime=0;
2256 |   function frame(ts){
2257 |     requestAnimationFrame(frame);
2258 |     if(!lastTime) lastTime=ts;
2259 |     var dt=ts-lastTime;
2260 |     lastTime=ts;
2261 | 
2262 |     ctx.clearRect(0,0,W,H);
2263 | 
2264 |     // 1. Falling matrix characters (sparse)
2265 |     ctx.font=fontSize+'px JetBrains Mono,monospace';
2266 |     for(var i=0;i<cols;i++){
2267 |       if(Math.random()>0.06) { // sparse: only 6% of columns draw per frame
2268 |         if(drops[i]>0){
2269 |           ctx.fillStyle='rgba(255,59,95,0.15)';
2270 |           var ch=matrixChars[Math.floor(Math.random()*matrixChars.length)];
2271 |           ctx.fillText(ch,i*fontSize,drops[i]*fontSize);
2272 |         }
2273 |       }
2274 |       drops[i]+=0.3;
2275 |       if(drops[i]*fontSize>H && Math.random()>0.98){
2276 |         drops[i]=0;
2277 |       }
2278 |     }
2279 | 
2280 |     // 2. Scan line sweep every 15s
2281 |     scanTimer+=dt;
2282 |     if(scanTimer>=scanInterval){
2283 |       scanTimer=0;
2284 |       scanY=-2;
2285 |       scanDir=1;
2286 |     }
2287 |     if(scanY>=0 && scanY<=H){
2288 |       var grad=ctx.createLinearGradient(0,scanY-8,0,scanY+8);
2289 |       grad.addColorStop(0,'rgba(255,59,95,0)');
2290 |       grad.addColorStop(0.5,'rgba(255,59,95,0.12)');
2291 |       grad.addColorStop(1,'rgba(255,59,95,0)');
2292 |       ctx.fillStyle=grad;
2293 |       ctx.fillRect(0,scanY-8,W,16);
2294 |     }
2295 |     if(scanY>=-2 && scanY<=H+10) scanY+=2;
2296 | 
2297 |     // 3. Hex fragments fade in/out
2298 |     if(Math.random()<0.008) spawnHex();
2299 |     for(var h=hexFrags.length-1;h>=0;h--){
2300 |       var frag=hexFrags[h];
2301 |       if(frag.phase===0){
2302 |         frag.alpha+=frag.speed*dt;
2303 |         if(frag.alpha>=0.2){frag.alpha=0.2;frag.phase=1;frag.holdStart=ts;}
2304 |       } else if(frag.phase===1){
2305 |         if(ts-frag.holdStart>frag.holdTime) frag.phase=2;
2306 |       } else {
2307 |         frag.alpha-=frag.speed*dt;
2308 |         if(frag.alpha<=0){hexFrags.splice(h,1);continue;}
2309 |       }
2310 |       ctx.fillStyle='rgba(255,59,95,'+frag.alpha.toFixed(3)+')';
2311 |       ctx.font='10px JetBrains Mono,monospace';
2312 |       ctx.fillText(frag.text,frag.x,frag.y);
2313 |     }
2314 |   }
2315 |   requestAnimationFrame(frame);
2316 | })();
2317 | 
2318 | function fetchTO(url,opts,ms){
2319 |   var ctrl=new AbortController();
2320 |   var id=setTimeout(function(){ctrl.abort();},ms);
2321 |   var o=opts||{};o.signal=ctrl.signal;
2322 |   return fetch(url,o).finally(function(){clearTimeout(id);})
2323 |     .catch(function(e){if(e.name==='AbortError')throw new Error('timeout');throw e;});
2324 | }
2325 | /* ── ACTION CARDS ── */
2326 | function showActionCard(card){
2327 |   var el=document.getElementById('oracle-action-card');
2328 |   var catColor = card.category==='amazon' ? '#FF9900' : card.category==='internal' ? '#6cff9f' : '#ff3b5f';
2329 |   el.innerHTML='<a href="'+card.url+'" target="_blank" rel="noopener" onclick="trackCardClick(\''+card.id+'\')" style="display:block;background:#0d0f14;border:1px solid '+catColor+';border-radius:8px;padding:14px 16px;text-decoration:none;transition:border-color 0.2s;">'
2330 |     +'<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;letter-spacing:.1em;color:'+catColor+';margin-bottom:4px;">'+card.category.toUpperCase()+'</div>'
2331 |     +'<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:4px;">'+card.title+'</div>'
2332 |     +'<div style="font-size:11px;color:rgba(255,255,255,0.55);margin-bottom:10px;">'+card.description+'</div>'
2333 |     +'<div style="font-size:11px;font-weight:600;color:'+catColor+';">'+card.cta+'</div>'
2334 |     +'</a>';
2335 |   el.style.display='block';
2336 |   el.style.opacity='0';
2337 |   setTimeout(function(){el.style.transition='opacity 0.4s';el.style.opacity='1';},100);
2338 |   setTimeout(function(){hideActionCard();},45000);
2339 | }
2340 | function showVisionSponsor(deviceName){
2341 |   if(!deviceName || deviceName==='unknown') return;
2342 |   var key=deviceName.toLowerCase();
2343 |   var match=null;
2344 |   Object.keys(VISION_SPONSOR_MAP).forEach(function(k){
2345 |     if(!match && key.indexOf(k)>=0) match=VISION_SPONSOR_MAP[k];
2346 |   });
2347 |   if(!match) return;
2348 |   showActionCard(match);
2349 | }
2350 | function hideActionCard(){
2351 |   var el=document.getElementById('oracle-action-card');
2352 |   el.style.opacity='0';
2353 |   setTimeout(function(){el.style.display='none';el.innerHTML='';},400);
2354 | }
2355 | function trackCardClick(id){
2356 |   fetch('/api/telemetry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event:'oracle_card_clicked',properties:{card_id:id,fingerprint:window._visitorToken||'anon'}})}).catch(function(){});
2357 | }
2358 | 
2359 | /* ── MOBILE NAV BAR ── */
2360 | (function(){
2361 |   var isMobile=/iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
2362 |   if(isMobile){
2363 |     var nb=document.getElementById('mobile-nav-bar');
2364 |     if(nb) nb.style.display='flex';
2365 |   }
2366 | })();
2367 | 
2368 | window.addEventListener('beforeunload',function(){
2369 |   try{
2370 |     var xhr=new XMLHttpRequest();
2371 |     xhr.open('POST',A+'/oracle/session/save',false);
2372 |     xhr.setRequestHeader('Content-Type','application/json');
2373 |     xhr.send(JSON.stringify({session_id:SESSION_ID}));
2374 |   }catch(e){}
2375 | });
2376 | </script>
2377 | </body>
2378 | </html>
2379 | 
```

---

## YOUR REVIEW TASK — ORACLE EXTERNAL AUDIT: DUPLICATE FUNCTIONS + iOS RELIABILITY (4 QUESTIONS)

You are auditing templates/oracle_live.html — the Satomi AI voice oracle for Protocol Pulse.
This file has had 20+ surgical patches applied in 8 hours by multiple developers.
The server side (avatar_server.py, Wav2Lip, Kokoro TTS) is confirmed working — all issues are frontend JS.

The architecture:
- Gate screen: user taps "Activate Microphone" → requestMic() → getUserMedia → go()
- go(): hides gate, shows stage, calls initSR() + playIntent('GREETING')
- playIntent('GREETING'): fetches greeting blob from /oracle/speak, calls playVid()
- playVid(): pause+removeAttribute+load, muted=false, sets src, plays video with baked audio
- After greeting: startRec() creates fresh recognition instance, starts listening
- User speaks → onresult sets pending/transcript → onend auto-submits → process(text)
- process(): calls /oracle/chat with audio_first:false, polls /oracle/job/{id} every 2s
- When video blob arrives: playVid() → video plays with baked audio + lip sync
- After playVid() resolves: setBusy(false) + startRec() → loop continues

Known fix just applied: setBusy(false) was missing `else{mic.disabled=false;}` — mic stayed permanently disabled.

### Q1 — DUPLICATE FUNCTION DEFINITIONS
Scan the ENTIRE file for any function that is defined more than once. In a 2400-line template
with 20+ patches, function definitions can be accidentally duplicated when patches are applied
to the wrong line. List EVERY function name and its line number(s). Flag any function that
appears more than once. Also check for variable name collisions between global scope and
function-local scope that could cause shadowing bugs.

### Q2 — iOS SAFARI POLLING RELIABILITY
The current approach for chat responses is: POST /oracle/chat → get job_id → poll /oracle/job/{id}
every 2 seconds for up to 45 attempts (90 seconds). The video render takes 8-15 seconds on 4x RTX 4090.
On iOS Safari specifically:
- Will the page stay alive during 90 seconds of fetch() polling in the foreground?
- What happens if the user locks their phone briefly during polling?
- Is there a risk of iOS killing the page or suspending JS execution during the poll loop?
- Would a single long-poll fetch be more reliable than repeated short polls?

### Q3 — MINIMAL VIABLE ARCHITECTURE
After all these patches, is there a clean architectural approach that avoids all these failure modes
without a full rewrite? Specifically:
- Can the state machine (IDLE → WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING) be
  simplified to prevent state flag desynchronization?
- Are there redundant state variables that should be consolidated?
- What is the minimum set of state variables needed for correct operation?

### Q4 — WHAT WILL ACTUALLY WORK ON FRIDAY DEMO
Given the current code with all patches applied, what is the most likely failure mode
on an iPhone running iOS Safari during a live demo? Be specific about:
- The exact sequence of events that could fail
- Which state variable is most likely to get stuck
- The single most dangerous race condition remaining
- What manual recovery action the user should take if it breaks during demo

### RESPONSE FORMAT
For each question (Q1-Q4):
- ANALYSIS: Detailed findings with line number citations
- RISK LEVEL: CRITICAL / HIGH / MEDIUM / LOW
- RECOMMENDATION: Specific actionable fix or mitigation

### FINAL VERDICT
- Number of duplicate functions found
- Top 3 risks for Friday demo, ranked by likelihood
- Single most important fix still needed (if any)

