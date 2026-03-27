# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: oracle-forensic
# Branch: main
# Generated: 2026-03-25 18:30 UTC
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

### File: templates/oracle_live.html (2402 lines)
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
 977 | var gStatus=document.getElementById('gate-status');
 978 | var gErr=document.getElementById('gate-error');
 979 | var vid=document.getElementById('vid');
 980 | var sub=document.getElementById('subtitle');
 981 | var statEl=document.getElementById('stat-text');
 982 | var spinEl=document.getElementById('spin');
 983 | var txEl=document.getElementById('tx');
 984 | var mic=document.getElementById('mic');
 985 | var micHint=document.getElementById('mic-hint');
 986 | var iMic=document.getElementById('i-mic');
 987 | var iStop=document.getElementById('i-stop');
 988 | var cards=document.getElementById('cards');
 989 | 
 990 | /* ── MIC REQUEST ── */
 991 | function requestMic(){
 992 |   gBtn.disabled=true;
 993 |   gStatus.textContent='Requesting microphone...';
 994 |   gErr.style.display='none';
 995 | 
 996 |   /* CRITICAL: unlock audio context immediately on this user gesture */
 997 |   try{
 998 |     var _unlockAc=new(window.AudioContext||window.webkitAudioContext)();
 999 |     var _unlockBuf=_unlockAc.createBuffer(1,1,22050);
1000 |     var _unlockSrc=_unlockAc.createBufferSource();
1001 |     _unlockSrc.buffer=_unlockBuf;_unlockSrc.connect(_unlockAc.destination);_unlockSrc.start(0);
1002 |     setTimeout(function(){try{_unlockAc.close();}catch(e){}},300);
1003 |   }catch(e){}
1004 | 
1005 |   try{
1006 |     var ac=new(window.AudioContext||window.webkitAudioContext)();
1007 |     var buf=ac.createBuffer(1,1,22050);
1008 |     var src=ac.createBufferSource();
1009 |     src.buffer=buf;src.connect(ac.destination);src.start(0);
1010 |     setTimeout(function(){try{ac.close();}catch(e){}},500);
1011 |   }catch(e){}
1012 | 
1013 |   /* Also "unlock" video element immediately */
1014 |   vid.muted=true;
1015 |   vid.play().catch(function(){});
1016 | 
1017 |   /* Pre-unlock Audio element for PATH B (chat responses) */
1018 |   window._audioUnlocked = new Audio();
1019 |   window._audioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1020 |   window._audioUnlocked.volume = 0.001;
1021 |   window._audioUnlocked.play().catch(function(){});
1022 | 
1023 |   window._chatAudioPlaying = false;
1024 | 
1025 |   navigator.mediaDevices.getUserMedia({audio:true,video:false})
1026 |     .then(function(stream){
1027 |       stream.getTracks().forEach(function(t){t.stop();}); /* don't need stream, just the gesture */
1028 |       gStatus.textContent='';
1029 |       go();
1030 |     })
1031 |     .catch(function(err){
1032 |       console.warn('[Satomi mic error]', err);
1033 |       gBtn.disabled=false;
1034 |       gStatus.textContent='';
1035 |       gErr.style.display='block';
1036 |       var name = err && err.name ? err.name : '';
1037 |       var msg='';
1038 |       if(name === 'NotAllowedError' || name === 'PermissionDeniedError'){
1039 |         msg='Microphone access denied. Allow mic in your browser settings, then retry.';
1040 |       } else if(name === 'NotReadableError' || name === 'TrackStartError'){
1041 |         msg='Microphone busy. Close other apps using the mic.';
1042 |       } else if(name === 'NotFoundError'){
1043 |         msg='No microphone detected.';
1044 |       } else {
1045 |         msg='Microphone unavailable'+(name?' ('+name+')':'.')+'.';
1046 |       }
1047 |       /* P0: Styled error + text fallback — demo never stops */
1048 |       gErr.innerHTML='<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;letter-spacing:.1em;color:rgba(255,59,95,.7);text-transform:uppercase;margin-bottom:6px;">MIC UNAVAILABLE</div>'
1049 |         +'<div style="font-size:12px;color:rgba(255,255,255,.7);margin-bottom:12px;line-height:1.5;">'+msg+'</div>'
1050 |         +'<div style="display:flex;flex-direction:column;gap:8px;">'
1051 |         +'<button onclick="requestMic()" style="background:rgba(255,59,95,.1);border:1px solid rgba(255,59,95,.3);color:#ff3b5f;font-family:\'JetBrains Mono\',monospace;font-size:11px;letter-spacing:.05em;padding:10px 16px;border-radius:4px;cursor:pointer;font-weight:600;">RETRY MIC ACCESS</button>'
1052 |         +'<button onclick="goTextMode()" style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.15);color:#fff;font-family:\'JetBrains Mono\',monospace;font-size:11px;letter-spacing:.05em;padding:10px 16px;border-radius:4px;cursor:pointer;font-weight:600;">CONTINUE WITH TEXT INPUT</button>'
1053 |         +'</div>';
1054 |     });
1055 | }
1056 | 
1057 | /* ── TRANSITION ── */
1058 | function go(){
1059 |   gate.style.opacity='0';
1060 |   setTimeout(function(){
1061 |     gate.style.display='none';
1062 |     stage.style.display='flex';
1063 |     stage.style.opacity='0';
1064 |     setTimeout(function(){
1065 |       stage.style.transition='opacity .45s';
1066 |       stage.style.opacity='1';
1067 |       initSR();
1068 |       setOracleState('WELCOME');
1069 |       playIntent('GREETING');
1070 |       setupTapFallback(); /* FIX 4: register tap-to-speak safety net */
1071 |     },30);
1072 |   },350);
1073 | }
1074 | 
1075 | /* ── PLAY CACHED INTENT ── */
1076 | function playIntent(intent){
1077 |   if(busy&&intent!=='GREETING')return;
1078 |   if(intent.indexOf('DAILY_BRIEF')===0&&window._briefFetched)return;
1079 |   setBusy(true);
1080 |   setStat('Satomi loading\u2026','#f4c46f',true);
1081 |   // Show thinking loop during intent loading (never dark screen)
1082 |   try{vid.muted=true;vid.loop=true;vid.src=A+'/oracle/thinking';vid.style.opacity='1';vid.play().catch(function(){vid.style.opacity='0';});}catch(e){}
1083 |   // Progress messages so user knows it's working, not broken
1084 |   var _loadMsgs = ['Initializing\u2026','Rendering response\u2026','Almost ready\u2026'];
1085 |   var _loadIdx = 0;
1086 |   var _loadTimer = setInterval(function(){
1087 |     _loadIdx++;
1088 |     if(_loadIdx < _loadMsgs.length) setStat(_loadMsgs[_loadIdx],'#f4c46f',true);
1089 |     else clearInterval(_loadTimer);
1090 |   }, 6000);
1091 |   var _clearTimer = function(){ clearInterval(_loadTimer); };
1092 |   fetchTO(A+'/oracle/speak',{
1093 |     method:'POST',
1094 |     headers:{'Content-Type':'application/json'},
1095 |     body:JSON.stringify({intent:intent})
1096 |   },30000)
1097 |   .then(function(r){
1098 |     if(!r.ok)throw new Error('HTTP '+r.status);
1099 |     var ct=r.headers.get('content-type')||'';
1100 |     if(ct.indexOf('video')>=0)return r.blob().then(blobURL);
1101 |     return r.json().then(function(j){
1102 |       return fetchTO(A+j.video_url,{},20000).then(function(r2){return r2.blob().then(blobURL);});
1103 |     });
1104 |   })
1105 |   .then(function(url){
1106 |     if(typeof _clearTimer=='function') _clearTimer();
1107 |     /* FIX 2: Start independent mic activation timer BEFORE video plays.
1108 |        This fires regardless of whether playVid() Promise resolves. */
1109 |     if(intent==='GREETING'){
1110 |       var _estDuration=8; /* estimated greeting video duration in seconds */
1111 |       console.log('[Satomi] Greeting video starting — mic timer set for',_estDuration+1,'s');
1112 |       setTimeout(function(){
1113 |         console.log('[Satomi] Independent mic timer fired — _greeted:',_greeted,'busy:',busy,'isRec:',isRec);
1114 |         if(_greeted&&!busy&&!isRec&&mic&&recognition){
1115 |           mic.disabled=false;
1116 |           startRec();
1117 |           setStat('Listening\u2026','#6cff9f',false);
1118 |         }
1119 |       },(_estDuration+1)*1000);
1120 |     }
1121 |     return playVid(url);
1122 |   })
1123 |   .then(function(){
1124 |     if(intent==='SOVEREIGNTY_ASSESSMENT')showCards();
1125 |     if(intent==='GREETING'){
1126 |       window._briefFetched=false;
1127 |       _greeted=true;
1128 |       console.log('[Satomi] Greeting .then() — activating mic');
1129 |       /* FIX 3: Explicit setBusy(false) BEFORE mic activation */
1130 |       setBusy(false);
1131 |       setOracleState('LISTENING');
1132 |       /* FIX 2 cont: Call startRec directly — no setTimeout for iOS gesture trust */
1133 |       if(!isRec&&mic&&recognition){
1134 |         mic.disabled=false;
1135 |         startRec();
1136 |         setStat('Listening\u2026','#6cff9f',false);
1137 |       }
1138 |     }
1139 |   })
1140 |   .catch(function(e){
1141 |     console.warn('[Satomi] playIntent catch:',e);
1142 |     /* On any error (including playVid timeout), ensure mic activates for greeting */
1143 |     if(intent==='GREETING'){
1144 |       _greeted=true;
1145 |       setBusy(false);
1146 |       setOracleState('LISTENING');
1147 |       if(!isRec&&mic&&recognition){
1148 |         mic.disabled=false;
1149 |         startRec();
1150 |         setStat('Listening\u2026','#6cff9f',false);
1151 |       }
1152 |     } else {
1153 |       if(e&&e.message&&String(e.message).indexOf('HTTP')>=0)
1154 |         setStat('Satomi error \u2014 try again.','#ff3b5f',false);
1155 |     }
1156 |   })
1157 |   .finally(function(){
1158 |     setBusy(false);
1159 |     setOracleState('LISTENING');
1160 |     setTimeout(pulseMic,500);
1161 |   });
1162 | }
1163 | 
1164 | function si(intent){if(busy)return;hideCards();playIntent(intent);}
1165 | 
1166 | /* ── PROCESS SPEECH (two-phase: audio-first + async video) ── */
1167 | function process(text){
1168 |   console.log('[Satomi] process() called — text:',JSON.stringify((text||'').substring(0,50)),'busy:',busy);
1169 |   if(!text.trim()||busy)return;
1170 |   // Guard: mark brief as fetched to prevent double-play with DAILY_BRIEF_INTRO
1171 |   if(/daily\s*brief/i.test(text)) window._briefFetched=true;
1172 |   setOracleState('PROCESSING');
1173 |   setBusy(true);hideCards();hideActionCard();showTX(text);
1174 | 
1175 |   // P0-3: Elapsed time counter — show "Satomi is thinking... Xs" with live counter
1176 |   var _thinkStart=Date.now();
1177 |   var _thinkReassured=false;
1178 |   setStat('Satomi is thinking\u2026 0s','#f4c46f',true);
1179 |   var _thinkTimer=setInterval(function(){
1180 |     var elapsed=Math.floor((Date.now()-_thinkStart)/1000);
1181 |     // P0-4: Reassurance message after 15s
1182 |     if(elapsed>=15&&!_thinkReassured){
1183 |       _thinkReassured=true;
1184 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1185 |     } else if(!_thinkReassured){
1186 |       setStat('Satomi is thinking\u2026 '+elapsed+'s','#f4c46f',true);
1187 |     } else {
1188 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1189 |     }
1190 |   },1000);
1191 |   window._thinkTimer=_thinkTimer;
1192 | 
1193 |   // Phase 2 T1.4: Play thinking loop immediately for instant visual feedback
1194 |   // P0-2: Add onerror fallback — if thinking video fails, show static avatar
1195 |   vid.muted=true;
1196 |   vid.loop=true;
1197 |   vid.src=A+'/oracle/thinking';
1198 |   vid.style.opacity='1';
1199 |   vid.onerror=function(){
1200 |     console.warn('[Satomi] thinking video failed — showing static avatar');
1201 |     vid.style.opacity='0'; /* static avatar image underneath is always visible */
1202 |   };
1203 |   vid.play().catch(function(e){
1204 |     console.warn('[Satomi] thinking autoplay blocked:',e);
1205 |     vid.style.opacity='0'; /* fallback to static avatar */
1206 |   });
1207 | 
1208 |   // Re-unlock audio context on every user interaction
1209 |   try{
1210 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1211 |     if(_ac.state==='suspended') _ac.resume();
1212 |     var _buf=_ac.createBuffer(1,1,22050);
1213 |     var _src=_ac.createBufferSource();
1214 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1215 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1216 |   }catch(e){}
1217 | 
1218 |   var pendingVideoUrl=null;
1219 |   var _audioFinished=false;
1220 | 
1221 |   fetchTO(A+'/oracle/chat',{
1222 |     method:'POST',headers:{'Content-Type':'application/json'},
1223 |     body:JSON.stringify({text:text,session_id:SESSION_ID,visitor_token:window._visitorToken||'anon',use_cache_for_intents:true,page_context:PAGE_CONTEXT,audio_first:true,avatar_source:"oracle_studio"})
1224 |   },90000)
1225 |   .then(function(r){
1226 |     if(!r.ok) throw new Error('HTTP '+r.status);
1227 |     var ct=r.headers.get('content-type')||'';
1228 |     if(ct.indexOf('video')>=0){
1229 |       // Cache hit — video came back immediately
1230 |       return r.blob().then(blobURL).then(function(url){ return playVid(url); });
1231 |     }
1232 |     // Audio-first JSON response
1233 |     return r.json().then(function(j){
1234 |       var responseText=j.text;
1235 |       var videoJobId=j.job_id;
1236 |       var _pendingCard = j.action_card || null;
1237 | 
1238 |       // Play audio: try cached job audio first (no duplicate Kokoro), fallback to /oracle/voice
1239 |       var audioFetch;
1240 |       if(videoJobId){
1241 |         // Poll job audio with retry — server returns 202 while TTS is rendering
1242 |         function pollJobAudio(jobId, attemptsLeft){
1243 |           return fetchTO(A+'/oracle/job/'+jobId+'/audio',{},15000)
1244 |             .then(function(ar){
1245 |               if(ar.status===202){
1246 |                 // Still rendering — retry after 2s
1247 |                 if(attemptsLeft>0){
1248 |                   return new Promise(function(res){ setTimeout(function(){ res(pollJobAudio(jobId,attemptsLeft-1)); },2000); });
1249 |                 } else {
1250 |                   throw new Error('audio timeout after retries');
1251 |                 }
1252 |               }
1253 |               if(!ar.ok) throw new Error('no cached audio');
1254 |               return ar.blob().then(function(b){
1255 |                 // Validate: must be real audio (>1KB), not a tiny error body
1256 |                 if(b.size < 1024) throw new Error('audio blob too small: '+b.size);
1257 |                 return b;
1258 |               });
1259 |             });
1260 |         }
1261 |         audioFetch=pollJobAudio(videoJobId, 10)
1262 |           .catch(function(){
1263 |             // Fallback: generate fresh TTS
1264 |             return fetchTO(A+'/oracle/voice',{
1265 |               method:'POST',headers:{'Content-Type':'application/json'},
1266 |               body:JSON.stringify({text:responseText})
1267 |             },35000).then(function(ar){
1268 |               if(!ar.ok) throw new Error('audio failed');
1269 |               return ar.blob();
1270 |             });
1271 |           });
1272 |       } else {
1273 |         audioFetch=fetchTO(A+'/oracle/voice',{
1274 |           method:'POST',headers:{'Content-Type':'application/json'},
1275 |           body:JSON.stringify({text:responseText})
1276 |         },35000).then(function(ar){
1277 |           if(!ar.ok) throw new Error('audio failed');
1278 |           return ar.blob();
1279 |         });
1280 |       }
1281 |       return audioFetch
1282 |       .then(function(b){
1283 |         return new Blob([b], {type: b.type || 'audio/wav'});
1284 |       })
1285 |       .then(function(audioBlob){
1286 |         var audioUrl=URL.createObjectURL(audioBlob);
1287 |         var audio;
1288 |         if(window._audioUnlocked){
1289 |           audio=window._audioUnlocked;
1290 |           window._audioUnlocked=null;
1291 |           audio.src=audioUrl;
1292 |           audio.volume=1.0;
1293 |           audio.muted=false;
1294 |         } else {
1295 |           audio=new Audio(audioUrl);
1296 |           audio.volume=1.0;
1297 |           window._chatAudioEl=audio; /* track so video arrival can stop it */
1298 |         }
1299 |         window._chatAudioPlaying=true;
1300 |         var playPromise = audio.play();
1301 |         if(playPromise !== undefined){
1302 |           playPromise.then(function(){
1303 |             if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1304 |             /* P0-4: If video not yet ready, show "Rendering video..." instead of "Speaking" */
1305 |             if(!pendingVideoUrl) setStat('Rendering video\u2026','#f4c46f',true);
1306 |             else setStat('Speaking','#6cff9f',false);
1307 |           }).catch(function(err){
1308 |             console.warn('[Satomi] audio.play() rejected:', err.name);
1309 |             // On mobile, audio may be blocked — set volume via user gesture retry
1310 |             audio.muted = false;
1311 |             audio.volume = 1.0;
1312 |             setTimeout(function(){
1313 |               audio.play().catch(function(e2){
1314 |                 console.warn('[Satomi] retry failed:', e2.name);
1315 |                 if(audio.onended) audio.onended();
1316 |               });
1317 |             }, 100);
1318 |           });
1319 |         }
1320 | 
1321 |         return new Promise(function(resolve){
1322 |           audio.onended=function(){
1323 |             _audioFinished=true;
1324 |             if(_pendingCard){ showActionCard(_pendingCard); _pendingCard=null; }
1325 |             window._chatAudioPlaying=false;
1326 |             URL.revokeObjectURL(audioUrl);
1327 |             // Audio finished — unmute video if it's playing lip sync
1328 |             try{ if(!vid.paused){ vid.muted=false; vid.volume=1.0; } }catch(e){}
1329 |             // Don't replay lip-sync video after audio already finished — just resolve
1330 |             if(pendingVideoUrl){
1331 |               try { URL.revokeObjectURL(pendingVideoUrl); } catch(e) {}
1332 |             }
1333 |             resolve();
1334 |           };
1335 | 
1336 |           // Phase 2 T2.1: SSE push replaces polling (with polling fallback)
1337 |           if(videoJobId){
1338 |             var _videoHandled=false;
1339 |             function _handleVideoReady(){
1340 |               if(_videoHandled) return;
1341 |               _videoHandled=true;
1342 |               fetch(A+'/oracle/job/'+videoJobId)
1343 |                 .then(function(vr){
1344 |                   if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1345 |                     return vr.blob();
1346 |                   }
1347 |                   return null;
1348 |                 })
1349 |                 .then(function(vb){
1350 |                   if(vb){
1351 |                     pendingVideoUrl=blobURL(vb);
1352 |                     // Play video immediately when ready — don't wait for _audioFinished
1353 |                     // Stop any separate audio playing first
1354 |                     try{if(window._chatAudioEl){window._chatAudioEl.pause();window._chatAudioEl.currentTime=0;}}catch(e){}
1355 |                     vid.style.opacity='0';
1356 |                     setTimeout(function(){
1357 |                       vid.loop=false;vid.muted=false;
1358 |                       vid.src=pendingVideoUrl;
1359 |                       vid.style.opacity='1';
1360 |                       playVid(pendingVideoUrl);
1361 |                     },150);
1362 |                   }
1363 |                 })
1364 |                 .catch(function(e){console.warn('[Satomi] video fetch error:',e);});
1365 |             }
1366 | 
1367 |             if(window.EventSource){
1368 |               // SSE push — sub-100ms notification
1369 |               var evtSource=new EventSource(A+'/oracle/job/'+videoJobId+'/stream');
1370 |               evtSource.addEventListener('audio_ready',function(){
1371 |                 // Audio already being fetched above — this is informational
1372 |               });
1373 |               evtSource.addEventListener('video_ready',function(){
1374 |                 evtSource.close();
1375 |                 _handleVideoReady();
1376 |               });
1377 |               evtSource.addEventListener('error',function(e){
1378 |                 evtSource.close();
1379 |                 // P1-1: SSE error — stop thinking loop but keep static avatar visible
1380 |                 vid.loop=false;
1381 |                 vid.style.opacity='0'; /* static avatar img underneath remains visible */
1382 |                 setStat('Connection issue — retrying\u2026','#f4c46f',true);
1383 |               });
1384 |               evtSource.onerror=function(){
1385 |                 // Connection lost — fall back to polling
1386 |                 evtSource.close();
1387 |                 if(!_videoHandled) _startPollFallback();
1388 |               };
1389 |             } else {
1390 |               _startPollFallback();
1391 |             }
1392 | 
1393 |             function _startPollFallback(){
1394 |               var pollAttempts=0,maxPollAttempts=60;
1395 |               var pollVideo=setInterval(function(){
1396 |                 pollAttempts++;
1397 |                 fetch(A+'/oracle/job/'+videoJobId)
1398 |                   .then(function(vr){
1399 |                     if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1400 |                       return vr.blob();
1401 |                     }
1402 |                     return null;
1403 |                   })
1404 |                   .then(function(vb){
1405 |                     if(vb){
1406 |                       clearInterval(pollVideo);
1407 |                       _videoHandled=true;
1408 |                       pendingVideoUrl=blobURL(vb);
1409 |                       // Play immediately — stop separate audio, show lip-sync video
1410 |                       try{if(window._chatAudioEl){window._chatAudioEl.pause();window._chatAudioEl.currentTime=0;}}catch(e){}
1411 |                       vid.style.opacity='1';
1412 |                       playVid(pendingVideoUrl);
1413 |                     }
1414 |                   })
1415 |                   .catch(function(){});
1416 |                 if(pollAttempts>=maxPollAttempts){
1417 |                   clearInterval(pollVideo);
1418 |                   setBusy(false);mic.disabled=false;
1419 |                 }
1420 |               },2000);
1421 |             }
1422 |           }
1423 |         });
1424 |       });
1425 |     });
1426 |   })
1427 |   .then(function(){
1428 |     setTimeout(pulseMic,500);
1429 |   })
1430 |   .catch(function(e){
1431 |     console.error('process error:',e);
1432 |     var msg=(e&&e.message)||'';
1433 |     /* P1: 429/503 — server overloaded, auto-retry after 5s */
1434 |     if(msg.indexOf('429')>=0||msg.indexOf('503')>=0){
1435 |       vid.style.opacity='0';
1436 |       setStat('Satomi is meditating\u2026 retrying in 5s','#f4c46f',true);
1437 |       var _retryText=text;
1438 |       setTimeout(function(){
1439 |         setBusy(false);
1440 |         if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1441 |         setOracleState('LISTENING');
1442 |         if(_retryText)process(_retryText);
1443 |       },5000);
1444 |       return; /* skip .finally cleanup — retry will handle it */
1445 |     } else if(msg.indexOf('timeout')>=0){
1446 |       vid.style.opacity='0';
1447 |       setStat('Request timed out — tap mic to retry','#f4c46f',false);
1448 |     } else if(msg.indexOf('HTTP')>=0){
1449 |       vid.style.opacity='0';
1450 |       setStat('Satomi error — tap mic to retry','#ff3b5f',false);
1451 |     } else if(msg.indexOf('Failed to fetch')>=0||msg.indexOf('NetworkError')>=0){
1452 |       vid.style.opacity='0';
1453 |       setStat('Network error — check connection','#ff3b5f',false);
1454 |     }
1455 |   })
1456 |   .finally(function(){
1457 |     if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1458 |     setBusy(false);hideTX();
1459 |     setOracleState('LISTENING');
1460 |   });
1461 | }
1462 | 
1463 | function blobURL(b){
1464 |   if(objURL)try{URL.revokeObjectURL(objURL);}catch(e){}
1465 |   objURL=URL.createObjectURL(b);
1466 |   return objURL;
1467 | }
1468 | 
1469 | /* ── PLAY VIDEO (FIX 1: settled guard + timeupdate fallback + dynamic timeout) ── */
1470 | function playVid(url){
1471 |   return new Promise(function(res,rej){
1472 |     console.log('[Satomi] playVid called:',url&&url.substring(0,60));
1473 |     setOracleState('RESPONDING');
1474 |     vid.loop=false;
1475 |     vid.muted=false; /* FIX: always unmute before playing lip-sync video */
1476 |     vid.src=url;
1477 |     vid.style.opacity='1';
1478 |     if(window._matrixHide) window._matrixHide();
1479 | 
1480 |     /* Settled guard — prevents double-resolution from onended/onerror/safety/timeupdate */
1481 |     var _settled=false;
1482 |     function _finish(ok){
1483 |       if(_settled)return;
1484 |       _settled=true;
1485 |       clearTimeout(_safetyTimer);
1486 |       clearTimeout(_dynamicTimer);
1487 |       vid.ontimeupdate=null;
1488 |       if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1489 |       console.log('[Satomi] playVid settled via:',ok?'success':'error');
1490 |       /* P1-3: Fade out first, then clear src — avoids flash */
1491 |       vid.style.opacity='0';
1492 |       setTimeout(function(){ try{vid.src='';}catch(e){} },300);
1493 |       if(window._matrixShow) window._matrixShow();
1494 |       hideSub();
1495 |       try{if(window.parent!==window) window.parent.postMessage({type:'oracle:idle'},'*');}catch(e){}
1496 |       /* FIX 1: Always resolve — even on error — so .then() chain continues */
1497 |       res();
1498 |     }
1499 | 
1500 |     /* Safety timeout: fixed 12s fallback (covers worst case if duration unknown) */
1501 |     var _safetyTimer=setTimeout(function(){
1502 |       if(!_settled){
1503 |         console.warn('[Satomi] Safety timeout — forcing playVid resolve');
1504 |         setStat('Ready','#6cff9f',false);
1505 |         _finish(false);
1506 |       }
1507 |     },12000);
1508 | 
1509 |     /* Dynamic timeout: set once we know actual duration (duration + 3s buffer) */
1510 |     var _dynamicTimer=null;
1511 |     vid.addEventListener('loadedmetadata',function _onmeta(){
1512 |       vid.removeEventListener('loadedmetadata',_onmeta);
1513 |       if(_settled)return;
1514 |       var dur=vid.duration;
1515 |       if(dur&&isFinite(dur)){
1516 |         clearTimeout(_safetyTimer);
1517 |         var timeoutMs=Math.ceil(dur*1000)+3000;
1518 |         console.log('[Satomi] Dynamic timeout set:',timeoutMs+'ms for',dur+'s video');
1519 |         _dynamicTimer=setTimeout(function(){
1520 |           if(!_settled){
1521 |             console.warn('[Satomi] Dynamic safety timeout fired after',dur+'s video');
1522 |             setStat('Ready','#6cff9f',false);
1523 |             _finish(false);
1524 |           }
1525 |         },timeoutMs);
1526 |       }
1527 |     });
1528 | 
1529 |     /* timeupdate near-end fallback: catches iOS onended suppression */
1530 |     vid.ontimeupdate=function(){
1531 |       if(!_settled&&vid.duration>0&&vid.currentTime>=vid.duration-0.3){
1532 |         console.log('[Satomi] timeupdate near-end fallback triggered');
1533 |         _finish(true);
1534 |       }
1535 |     };
1536 | 
1537 |     try{if(window.parent!==window) window.parent.postMessage({type:'oracle:speaking'},'*');}catch(e){}
1538 |     vid.onended=function(){
1539 |       console.log('[Satomi] vid.onended fired');
1540 |       _finish(true);
1541 |     };
1542 |     vid.onerror=function(e){
1543 |       console.warn('[Satomi] vid.onerror:',e);
1544 |       setStat('Recovering\u2026','#f4c46f',true);
1545 |       setTimeout(function(){ _finish(false); },500);
1546 |     };
1547 |     vid.muted=true;
1548 |     vid.volume=1.0;
1549 |     var unmuted=false;
1550 |     function tryUnmute(){
1551 |       if(unmuted)return; unmuted=true;
1552 |       vid.muted=false;
1553 |       vid.volume=1.0;
1554 |     }
1555 |     vid.addEventListener('canplay',function oncp(){
1556 |       vid.removeEventListener('canplay',oncp);
1557 |       setStat('Speaking','#6cff9f',false);
1558 |       if(!window._chatAudioPlaying){
1559 |         tryUnmute();
1560 |       }
1561 |     },{once:true});
1562 |     var p=vid.play();
1563 |     if(p){
1564 |       p.then(function(){}).catch(function(err){
1565 |         console.warn('[Satomi] vid.play() rejected (autoplay):',err);
1566 |         /* P0: iOS Safari — show centered tap-to-play overlay */
1567 |         showTapOverlay();
1568 |       });
1569 |     }
1570 |   });
1571 | }
1572 | 
1573 | /* ── SPEECH RECOGNITION ── */
1574 | function initSR(){
1575 |   var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
1576 |   if(!SR){micHint.textContent='no speech api';return;}
1577 |   recognition=new SR();
1578 |   recognition.continuous=true;recognition.interimResults=true;recognition.lang='en-US';recognition.maxAlternatives=1;
1579 |   recognition.onresult=function(e){
1580 |     var fin='',int='';
1581 |     for(var i=0;i<e.results.length;i++){
1582 |       if(e.results[i].isFinal)fin+=e.results[i][0].transcript;
1583 |       else int+=e.results[i][0].transcript;
1584 |     }
1585 |     showTX(fin||int);if(fin){pending=fin;console.log('[Satomi] onresult final:',fin.substring(0,50));}
1586 |   };
1587 |   recognition.onend=function(){
1588 |     console.log('[Satomi] recognition.onend — pending:',JSON.stringify(pending),'busy:',busy);
1589 |     setRec(false);
1590 |     var _pend=pending;
1591 |     pending='';
1592 |     if(_pend.trim()&&!busy){
1593 |       /* P1: Bridge status — show "Processing..." immediately so user sees feedback */
1594 |       setStat('Processing\u2026','#f4c46f',true);
1595 |       setTimeout(function(){ if(!busy){process(_pend);}},100);
1596 |     } else if(!busy&&_greeted){
1597 |       /* FIX 5: Auto-restart recognition on silence — don't dead-end */
1598 |       console.log('[Satomi] Empty pending — auto-restarting listener');
1599 |       setStat('Listening\u2026','#6cff9f',false);
1600 |       setTimeout(function(){ if(!busy&&!isRec){startRec();} },300);
1601 |     }
1602 |   };
1603 |   recognition.onerror=function(e){console.warn(e.error);setRec(false);};
1604 | }
1605 | 
1606 | function toggleMic(){if(busy)return;isRec?stopRec():startRec();}
1607 | function startRec(){
1608 |   if(!recognition){setStat('No speech API','#ff3b5f',false);return;}
1609 |   console.log('[Satomi] startRec called');
1610 |   pending='';isRec=true;setRec(true);setStat('\ud83c\udf99 Listening...','#66d9ff',false);
1611 |   try{recognition.start();console.log('[Satomi] recognition.start() OK');}catch(e){console.warn('[Satomi] recognition.start() error:',e);}
1612 | }
1613 | function stopRec(){
1614 |   isRec=false;setRec(false);
1615 |   /* P1-2: Don't play thinking video here — let recognition.onend → process() be the sole trigger.
1616 |      This eliminates the race condition where both stopRec and onend try to set thinking state. */
1617 |   if(recognition)try{recognition.stop();}catch(e){}
1618 |   // onend will fire after recognition.stop() and handle process() automatically
1619 | }
1620 | function setRec(on){
1621 |   mic.classList.toggle('rec',on);
1622 |   iMic.style.display=on?'none':'block';
1623 |   iStop.style.display=on?'block':'none';
1624 |   micHint.textContent=on?'tap to send':'tap to speak';
1625 | }
1626 | 
1627 | /* ── HELPERS ── */
1628 | function setStat(t,c,sp){statEl.textContent=t;statEl.style.color=c||'#334';spinEl.style.display=sp?'block':'none';spinEl.style.color=c||'#334';}
1629 | function setBusy(b){busy=b;if(b){mic.disabled=true;if(isRec)stopRec();}}
1630 | function showSub(t){sub.textContent=t;sub.classList.add('on');}
1631 | function hideSub(){sub.classList.remove('on');}
1632 | function showTX(t){txEl.textContent=t;txEl.classList.add('on');}
1633 | function hideTX(){txEl.classList.remove('on');}
1634 | function showCards(){cards.classList.add('on');}
1635 | function hideCards(){cards.classList.remove('on');}
1636 | 
1637 | /* ── TAP-TO-PLAY OVERLAY (P0: iOS Safari autoplay) ── */
1638 | function showTapOverlay(){
1639 |   var ov=document.getElementById('tap-to-play');
1640 |   if(ov){ov.style.display='flex';}
1641 |   setStat('Tap to play','#f4c46f',false);
1642 | }
1643 | function dismissTapOverlay(){
1644 |   var ov=document.getElementById('tap-to-play');
1645 |   if(ov){ov.style.display='none';}
1646 |   vid.muted=false;vid.volume=1.0;
1647 |   vid.play().then(function(){
1648 |     setStat('Speaking','#6cff9f',false);
1649 |   }).catch(function(e){
1650 |     console.warn('[Satomi] tap-to-play retry failed:',e);
1651 |     vid.style.opacity='0';
1652 |     setStat('Ready','#334',false);
1653 |   });
1654 | }
1655 | 
1656 | /* ── TEXT INPUT FALLBACK (P0: mic failure → text mode) ── */
1657 | var _textMode=false;
1658 | function goTextMode(){
1659 |   /* Skip mic, transition straight to stage with text input visible */
1660 |   _textMode=true;
1661 |   gBtn.disabled=true;
1662 |   gErr.style.display='none';
1663 |   /* Unlock audio context on this user gesture (same as requestMic) */
1664 |   try{
1665 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1666 |     var _buf=_ac.createBuffer(1,1,22050);var _src=_ac.createBufferSource();
1667 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1668 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1669 |   }catch(e){}
1670 |   vid.muted=true;vid.play().catch(function(){});
1671 |   window._audioUnlocked=new Audio();
1672 |   window._audioUnlocked.src='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1673 |   window._audioUnlocked.volume=0.001;
1674 |   window._audioUnlocked.play().catch(function(){});
1675 |   window._chatAudioPlaying=false;
1676 |   gate.style.opacity='0';
1677 |   setTimeout(function(){
1678 |     gate.style.display='none';
1679 |     stage.style.display='flex';
1680 |     stage.style.opacity='0';
1681 |     setTimeout(function(){
1682 |       stage.style.transition='opacity .45s';
1683 |       stage.style.opacity='1';
1684 |       /* Show text input, hide mic area, init speech recognition (may still work for some) */
1685 |       document.getElementById('stage-text-input').style.display='block';
1686 |       mic.disabled=true;
1687 |       micHint.textContent='text mode';
1688 |       initSR();
1689 |       setOracleState('WELCOME');
1690 |       playIntent('GREETING');
1691 |       /* After greeting, enable mic if SR is available as bonus */
1692 |       setTimeout(function(){
1693 |         if(recognition){mic.disabled=false;micHint.textContent='tap to speak';}
1694 |       },8000);
1695 |     },30);
1696 |   },350);
1697 | }
1698 | function submitTextInput(){
1699 |   var field=document.getElementById('text-input-field');
1700 |   var text=(field.value||'').trim();
1701 |   if(!text)return;
1702 |   field.value='';
1703 |   goTextMode();
1704 |   /* Queue the text to process after greeting finishes */
1705 |   var _waitGreeting=setInterval(function(){
1706 |     if(!busy){clearInterval(_waitGreeting);process(text);}
1707 |   },500);
1708 | }
1709 | function stageTextSubmit(){
1710 |   var field=document.getElementById('stage-text-field');
1711 |   var text=(field.value||'').trim();
1712 |   if(!text||busy)return;
1713 |   field.value='';
1714 |   process(text);
1715 | }
1716 | 
1717 | /* ── GEMINI VISION ── */
1718 | var _visionSessionId = null;
1719 | 
1720 | function updateCameraButtonState() {
1721 |   var lbl = document.getElementById('cam-btn-label');
1722 |   if (!lbl) return;
1723 |   lbl.textContent = _visionSessionId
1724 |     ? 'FOLLOW-UP PHOTO'
1725 |     : 'ANALYZE HARDWARE';
1726 | }
1727 | 
1728 | function triggerCamera(){
1729 |   document.getElementById("cam-input").click();
1730 | }
1731 | 
1732 | function handleVisionUpload(evt){
1733 |   var file = evt.target.files[0];
1734 |   if(!file) return;
1735 |   if (busy) {
1736 |     showVisionStatus('Satomi is speaking — wait a moment');
1737 |     setTimeout(hideVisionStatus, 2000);
1738 |     evt.target.value = "";
1739 |     return;
1740 |   }
1741 |   evt.target.value = "";
1742 |   
1743 |   var reader = new FileReader();
1744 |   reader.onload = function(e){
1745 |     var b64 = e.target.result.split(",")[1];
1746 |     var mime = file.type || "image/jpeg";
1747 |     sendVisionImage(b64, mime);
1748 |   };
1749 |   reader.readAsDataURL(file);
1750 | }
1751 | 
1752 | var SEED_RECOVERY_STEPS = [
1753 |   {
1754 |     label: 'STEP 1 OF 3 — STOP IMMEDIATELY',
1755 |     text: 'Do NOT send any Bitcoin from this wallet until you have moved your funds. Anyone who saw this seed phrase can access your Bitcoin right now.',
1756 |     speak: 'Stop. Do not send any Bitcoin from this wallet. Anyone who saw this seed phrase can steal your funds right now.'
1757 |   },
1758 |   {
1759 |     label: 'STEP 2 OF 3 — MOVE YOUR FUNDS',
1760 |     text: 'On a different device, create a brand new wallet. Generate a NEW seed phrase — write it down on paper only, never photograph it. Transfer ALL funds to the new wallet address immediately.',
1761 |     speak: 'On a different device, create a new wallet with a new seed phrase. Write it on paper only. Transfer all your funds to the new wallet immediately.'
1762 |   },
1763 |   {
1764 |     label: 'STEP 3 OF 3 — SECURE THE NEW WALLET',
1765 |     text: 'Once funds are transferred, the old wallet is abandoned. Store your new seed phrase in a metal backup, split across two secure locations. Never store seed phrases digitally.',
1766 |     speak: 'Once funds are moved, abandon the old wallet. Store your new seed phrase in metal, split across two secure locations. Never store seed phrases digitally.'
1767 |   }
1768 | ];
1769 | 
1770 | function showSecurityAlert(msg, onDismiss) {
1771 |   var overlay = document.getElementById('vision-security-overlay');
1772 |   var msgEl = document.getElementById('vision-security-msg');
1773 |   var dismissBtn = document.getElementById('vision-security-dismiss');
1774 |   var recoveryPanel = document.getElementById('vision-recovery-panel');
1775 |   if (!overlay || !msgEl) return;
1776 | 
1777 |   msgEl.textContent = msg;
1778 |   overlay.style.display = 'flex';
1779 | 
1780 |   // Speak the initial alert urgently
1781 |   function speakText(text) {
1782 |     fetchTO(A+'/oracle/voice', {
1783 |       method: 'POST',
1784 |       headers: {'Content-Type': 'application/json'},
1785 |       body: JSON.stringify({text: text})
1786 |     }, 20000).then(function(r) {
1787 |       if (!r.ok) return;
1788 |       return r.blob();
1789 |     }).then(function(blob) {
1790 |       if (!blob) return;
1791 |       var alertAudio = new Audio(URL.createObjectURL(blob));
1792 |       alertAudio.volume = 1.0;
1793 |       alertAudio.play().catch(function(){});
1794 |     }).catch(function(){});
1795 |   }
1796 | 
1797 |   speakText('SECURITY ALERT. ' + msg +
1798 |     ' Your seed phrase may be compromised. Do not send Bitcoin until you hear the recovery steps.');
1799 | 
1800 |   // Dismiss transitions to recovery steps
1801 |   dismissBtn.onclick = function() {
1802 |     dismissBtn.style.display = 'none';
1803 |     msgEl.style.fontSize = '0.9rem';
1804 |     msgEl.style.opacity = '0.7';
1805 |     recoveryPanel.style.display = 'block';
1806 |     _showRecoveryStep(0, speakText);
1807 |   };
1808 | }
1809 | 
1810 | function _showRecoveryStep(idx, speakFn) {
1811 |   var steps = SEED_RECOVERY_STEPS;
1812 |   var stepLabel = document.getElementById('vision-recovery-step-label');
1813 |   var stepText = document.getElementById('vision-recovery-step-text');
1814 |   var nextBtn = document.getElementById('vision-recovery-next');
1815 |   var helpBtn = document.getElementById('vision-recovery-help');
1816 |   var closeBtn = document.getElementById('vision-recovery-close');
1817 | 
1818 |   if (!stepLabel || !stepText) return;
1819 | 
1820 |   stepLabel.textContent = steps[idx].label;
1821 |   stepText.textContent = steps[idx].text;
1822 |   speakFn(steps[idx].speak);
1823 | 
1824 |   var isLast = (idx === steps.length - 1);
1825 |   nextBtn.style.display = isLast ? 'none' : 'block';
1826 |   helpBtn.style.display = isLast ? 'block' : 'none';
1827 |   closeBtn.style.display = isLast ? 'block' : 'none';
1828 | 
1829 |   nextBtn.onclick = function() {
1830 |     if (idx < steps.length - 1) _showRecoveryStep(idx + 1, speakFn);
1831 |   };
1832 | 
1833 |   helpBtn.onclick = function() {
1834 |     // Close overlay and trigger Satomi to help set up new wallet
1835 |     var overlay = document.getElementById('vision-security-overlay');
1836 |     if (overlay) overlay.style.display = 'none';
1837 |     // Inject a vision guidance request for new wallet setup
1838 |     sendVisionImage(null, null, 'help me set up a new hardware wallet safely');
1839 |   };
1840 | 
1841 |   closeBtn.onclick = function() {
1842 |     var overlay = document.getElementById('vision-security-overlay');
1843 |     if (overlay) overlay.style.display = 'none';
1844 |   };
1845 | }
1846 | 
1847 | function _speakVisionGuidance(d) {
1848 |   var raw = d.guidance_text || d.guidance || d.analysis || d.response
1849 |     || "I can see your hardware. Let me walk you through the next step.";
1850 |   // Hard 30-word cap for TTS speed
1851 |   var words = raw.split(/\s+/);
1852 |   var guideText = words.length > 30 ? words.slice(0,30).join(" ") : raw;
1853 | 
1854 |   // Urgent spoken prefix for transaction verdicts
1855 |   if (d.verdict === 'DO NOT SIGN') {
1856 |     guideText = 'WARNING. DO NOT SIGN THIS TRANSACTION. ' + guideText;
1857 |   } else if (d.verdict === 'REVIEW CAREFULLY' && d.red_flags && d.red_flags.length) {
1858 |     guideText = 'REVIEW CAREFULLY. ' + guideText;
1859 |   }
1860 | 
1861 |   showVisionStatus("Speaking...");
1862 |   showSub(guideText);
1863 | 
1864 |   // Transaction review verdict card
1865 |   if (d.category === 'transaction' && d.verdict) {
1866 |     var verdictColor = d.verdict === 'SAFE TO SIGN'
1867 |       ? '#00d4aa'
1868 |       : d.verdict === 'DO NOT SIGN'
1869 |       ? '#ff3b5f'
1870 |       : '#f5a623';
1871 | 
1872 |     var verdictHtml = '<div style="background:rgba(0,0,0,.4);' +
1873 |       'border:2px solid ' + verdictColor + ';border-radius:8px;' +
1874 |       'padding:12px 16px;margin-bottom:12px;">' +
1875 |       '<div style="font-family:monospace;font-size:10px;' +
1876 |       'letter-spacing:.12em;color:' + verdictColor + ';' +
1877 |       'text-transform:uppercase;margin-bottom:6px;">' +
1878 |       '\u26A1 TRANSACTION ANALYSIS</div>' +
1879 |       '<div style="font-size:1.1rem;font-weight:800;' +
1880 |       'color:' + verdictColor + ';margin-bottom:8px;">' +
1881 |       d.verdict + '</div>';
1882 | 
1883 |     if (d.recipient_address) {
1884 |       verdictHtml += '<div style="font-family:monospace;font-size:10px;' +
1885 |         'color:rgba(255,255,255,.5);word-break:break-all;">' +
1886 |         'TO: ' + d.recipient_address + '</div>';
1887 |     }
1888 |     if (d.amount_btc) {
1889 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1890 |         'color:rgba(255,255,255,.7);margin-top:4px;">' +
1891 |         'AMOUNT: ' + d.amount_btc + ' BTC</div>';
1892 |     }
1893 |     if (d.fee_sats) {
1894 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1895 |         'color:rgba(255,255,255,.6);">' +
1896 |         'FEE: ' + d.fee_sats + ' sats</div>';
1897 |     }
1898 |     if (d.red_flags && d.red_flags.length) {
1899 |       verdictHtml += '<div style="margin-top:8px;">';
1900 |       d.red_flags.forEach(function(flag) {
1901 |         verdictHtml += '<div style="font-family:monospace;font-size:9px;' +
1902 |           'color:#f5a623;letter-spacing:.06em;">\u26A0 ' + flag + '</div>';
1903 |       });
1904 |       verdictHtml += '</div>';
1905 |     }
1906 |     verdictHtml += '</div>';
1907 | 
1908 |     var vsEl = document.getElementById('vision-status');
1909 |     if (vsEl) {
1910 |       vsEl.innerHTML = verdictHtml + (vsEl.innerHTML || '');
1911 |       vsEl.classList.add('on');
1912 |     }
1913 |   }
1914 | 
1915 |   // Show steps in vision-status area if present
1916 |   if(d.steps && d.steps.length){
1917 |     var stepsHtml = d.steps.map(function(s,i){ return (i+1)+". "+s; }).join("<br>");
1918 |     var el=document.getElementById("vision-status");
1919 |     el.innerHTML = (d.device_name && d.device_name!=="unknown" ? "<b>"+d.device_name+"</b><br>" : "") + stepsHtml;
1920 |     el.classList.add("on");
1921 |   }
1922 | 
1923 |   // Add to session transcript
1924 |   _addVisionEntry(d.device_name, d.steps || [], guideText);
1925 | 
1926 |   // VOICE-ONLY: /oracle/voice is ElevenLabs-only, no GPU, ~400ms vs 14s
1927 |   fetchTO(A+"/oracle/voice",{method:"POST",
1928 |     headers:{"Content-Type":"application/json"},
1929 |     body:JSON.stringify({text:guideText})},15000)
1930 |   .then(function(ar){
1931 |     if(!ar.ok) throw new Error("voice "+ar.status);
1932 |     return ar.blob();
1933 |   })
1934 |   .then(function(audioBlob){
1935 |     hideVisionStatus();
1936 |     var audioURL = URL.createObjectURL(audioBlob);
1937 |     var audio;
1938 |     if(window._audioUnlocked){
1939 |       audio=window._audioUnlocked;
1940 |       window._audioUnlocked=null;
1941 |       audio.src=audioURL;
1942 |       audio.volume=1.0;
1943 |       audio.muted=false;
1944 |     } else {
1945 |       audio = new Audio(audioURL);
1946 |       audio.volume = 1.0;
1947 |     }
1948 |     return new Promise(function(res){
1949 |       audio.onended = function(){
1950 |         URL.revokeObjectURL(audioURL);
1951 |         setStat("Ready","#334",false);
1952 |         hideSub();
1953 |         if(d.device_name){
1954 |           setTimeout(function(){ showVisionSponsor(d.device_name); },800);
1955 |         }
1956 |         // Prompt for follow-up photo if session is active
1957 |         if (_visionSessionId) {
1958 |           showVisionStatus('Tap camera to show next screen \u2192');
1959 |           setTimeout(function() {
1960 |             hideVisionStatus();
1961 |           }, 4000);
1962 |         }
1963 |         res();
1964 |       };
1965 |       audio.onerror = function(){ URL.revokeObjectURL(audioURL); res(); };
1966 |       var vp = audio.play();
1967 |       if(vp !== undefined){
1968 |         vp.then(function(){ setStat("Speaking","#6cff9f",false); }).catch(function(){ res(); });
1969 |       }
1970 |     });
1971 |   })
1972 |   .catch(function(){
1973 |     showVisionStatus("Ready");
1974 |     setBusy(false);
1975 |     mic.disabled = false;
1976 |   });
1977 | }
1978 | 
1979 | function sendVisionImage(b64, mimeType, textOverride){
1980 |   // Text-only mode: no image, just a guided question
1981 |   if (!b64 && textOverride) {
1982 |     setBusy(true);
1983 |     showVisionStatus('Preparing guidance...');
1984 |     _speakVisionGuidance({
1985 |       guidance_text: 'I can guide you through setting up a new hardware wallet securely. First, choose a wallet: Coldcard for maximum security, Trezor for ease of use, or SeedSigner for open-source air-gapped signing. Which would you like help with?',
1986 |       device_name: 'new_wallet_setup',
1987 |       steps: [
1988 |         'Choose your hardware wallet: Coldcard, Trezor, or SeedSigner',
1989 |         'Purchase only from official manufacturer websites — never third party',
1990 |         'On first boot, generate a new seed phrase on the device itself',
1991 |         'Write seed phrase on paper only — never photograph or type it',
1992 |         'Test recovery before sending any funds'
1993 |       ]
1994 |     });
1995 |     setBusy(false);
1996 |     return;
1997 |   }
1998 | 
1999 |   setBusy(true);
2000 |   showVisionStatus("Analyzing your screen...");
2001 | 
2002 |   var endpoint = _visionSessionId ? A+"/vision/guide" : A+"/vision/analyze";
2003 |   var body = {image_base64:b64, mime_type:mimeType,
2004 |     context:"User needs Bitcoin hardware setup guidance"};
2005 |   if(_visionSessionId){
2006 |     body.session_id = _visionSessionId;
2007 |     body.question = "What step am I at and what should I do next?";
2008 |     body.last_context = _visionTranscript.length > 0
2009 |       ? _visionTranscript[_visionTranscript.length - 1].steps.join('; ')
2010 |       : '';
2011 |   }
2012 | 
2013 |   fetchTO(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},
2014 |     body:JSON.stringify(body)},20000)
2015 |   .then(function(r){
2016 |     if(!r.ok) throw new Error("vision "+r.status);
2017 |     return r.json();
2018 |   })
2019 |   .then(function(d){
2020 |     _visionSessionId = d.session_id || _visionSessionId;
2021 |     updateCameraButtonState();
2022 | 
2023 |     // Security alert takes absolute priority — recovery flow keeps overlay open
2024 |     if (d.security_alert) {
2025 |       showSecurityAlert(d.security_alert);
2026 |       return;
2027 |     }
2028 |     _speakVisionGuidance(d);
2029 |   })
2030 |   .catch(function(e){
2031 |     console.error("Vision error:", e);
2032 |     showVisionStatus("Vision error — try again.");
2033 |     setTimeout(hideVisionStatus, 3000);
2034 |   })
2035 |   .finally(function(){ setBusy(false); mic.disabled=false; });
2036 | }
2037 | 
2038 | function showVisionStatus(msg){ 
2039 |   var el=document.getElementById("vision-status");
2040 |   el.textContent=msg; el.classList.add("on");
2041 | }
2042 | function hideVisionStatus(){
2043 |   var el=document.getElementById("vision-status");
2044 |   el.classList.remove("on");
2045 | }
2046 | 
2047 | /* ── VISION SESSION TRANSCRIPT ── */
2048 | var _visionTranscript = [];
2049 | 
2050 | function _addVisionEntry(deviceName, steps, guidanceText) {
2051 |   var panel = document.getElementById('vision-transcript-panel');
2052 |   var entries = document.getElementById('vision-transcript-entries');
2053 |   if (!entries) return;
2054 | 
2055 |   if (panel && _visionTranscript.length === 0) {
2056 |     panel.style.display = 'block';
2057 |   }
2058 | 
2059 |   var entry = {
2060 |     device: deviceName || 'Unknown Device',
2061 |     steps: steps || [],
2062 |     guidance: guidanceText || '',
2063 |     time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})
2064 |   };
2065 |   _visionTranscript.push(entry);
2066 | 
2067 |   var el = document.createElement('div');
2068 |   el.className = 'vision-entry';
2069 | 
2070 |   var deviceEl = document.createElement('div');
2071 |   deviceEl.className = 'vision-entry-device';
2072 |   deviceEl.textContent = entry.device.toUpperCase();
2073 |   el.appendChild(deviceEl);
2074 | 
2075 |   if (entry.steps.length) {
2076 |     entry.steps.forEach(function(s, i) {
2077 |       var stepEl = document.createElement('div');
2078 |       stepEl.className = 'vision-entry-step';
2079 |       stepEl.textContent = (i+1) + '. ' + s;
2080 |       el.appendChild(stepEl);
2081 |     });
2082 |   } else if (entry.guidance) {
2083 |     var guidEl = document.createElement('div');
2084 |     guidEl.className = 'vision-entry-step';
2085 |     guidEl.textContent = entry.guidance.substring(0, 120) +
2086 |       (entry.guidance.length > 120 ? '…' : '');
2087 |     el.appendChild(guidEl);
2088 |   }
2089 | 
2090 |   var timeEl = document.createElement('div');
2091 |   timeEl.className = 'vision-entry-time';
2092 |   timeEl.textContent = entry.time + ' — tap to re-read';
2093 |   el.appendChild(timeEl);
2094 | 
2095 |   el.onclick = function() {
2096 |     var text = entry.steps.length
2097 |       ? entry.device + '. ' + entry.steps.join('. ')
2098 |       : entry.guidance;
2099 |     fetchTO(A+'/oracle/voice', {
2100 |       method: 'POST',
2101 |       headers: {'Content-Type': 'application/json'},
2102 |       body: JSON.stringify({text: text.substring(0, 200)})
2103 |     }, 20000).then(function(r) {
2104 |       return r.ok ? r.blob() : null;
2105 |     }).then(function(blob) {
2106 |       if (!blob) return;
2107 |       var a = new Audio(URL.createObjectURL(blob));
2108 |       a.volume = 1.0;
2109 |       a.play().catch(function(){});
2110 |     }).catch(function(){});
2111 |   };
2112 | 
2113 |   entries.appendChild(el);
2114 |   entries.scrollTop = entries.scrollHeight;
2115 | }
2116 | 
2117 | document.addEventListener('DOMContentLoaded', function() {
2118 |   var clearBtn = document.getElementById('vision-transcript-clear');
2119 |   if (clearBtn) {
2120 |     clearBtn.onclick = function() {
2121 |       _visionTranscript = [];
2122 |       var entries = document.getElementById('vision-transcript-entries');
2123 |       if (entries) entries.innerHTML = '';
2124 |       var panel = document.getElementById('vision-transcript-panel');
2125 |       if (panel) panel.style.display = 'none';
2126 |       _visionSessionId = null;
2127 |       updateCameraButtonState();
2128 |     };
2129 |   }
2130 | });
2131 | 
2132 | /* ── MINIMIZE / EXIT / FLOAT ── */
2133 | var _oracleMinimized = false;
2134 | 
2135 | function minimizeOracle(){
2136 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
2137 |   if(inIframe){
2138 |     try{ window.parent.postMessage({type:'oracle:minimize'},'*'); }catch(e){}
2139 |     return;
2140 |   }
2141 |   // Standalone: shrink to float bubble
2142 |   _oracleMinimized = true;
2143 |   document.getElementById("oracle-root").style.display = "none";
2144 |   var f = document.getElementById("oracle-float");
2145 |   if(f){ f.style.display = "flex"; if(busy) f.classList.add("speaking"); }
2146 | }
2147 | 
2148 | function restoreOracle(){
2149 |   _oracleMinimized = false;
2150 |   document.getElementById("oracle-float").style.display = "none";
2151 |   document.getElementById("oracle-root").style.display = "flex";
2152 |   document.getElementById("oracle-float").classList.remove("speaking");
2153 | }
2154 | 
2155 | function exitOracle(){
2156 |   // If running inside widget iframe — tell parent to close
2157 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
2158 |   if(inIframe){
2159 |     try{ window.parent.postMessage({type:'oracle:close'},'*'); }catch(e){}
2160 |     return;
2161 |   }
2162 |   // Standalone page — return to gate screen
2163 |   _oracleMinimized = false;
2164 |   // Stop any playing audio/video
2165 |   vid.pause(); vid.src="";
2166 |   if(isRec) stopRec();
2167 |   // Reset session on server
2168 |   fetch(A+"/oracle/session/reset",{method:"POST",
2169 |     headers:{"Content-Type":"application/json"},
2170 |     body:JSON.stringify({session_id:SESSION_ID})}).catch(function(){});
2171 |   // Hide everything
2172 |   document.getElementById("oracle-float").style.display = "none";
2173 |   document.getElementById("live-stage").style.display = "none";
2174 |   document.getElementById("oracle-root").style.display = "flex";
2175 |   // Show gate again
2176 |   var g = document.getElementById("gate");
2177 |   g.style.display = "flex";
2178 |   g.style.opacity = "1";
2179 |   g.style.transition = "opacity .3s";
2180 |   // Reset state
2181 |   busy = false; window._briefFetched = false;
2182 |   setStat("Ready","#334",false);
2183 |   hideSub(); hideTranscript && hideTX();
2184 | }
2185 | 
2186 | // Keep float speaking indicator in sync
2187 | var _origSetStat = setStat;
2188 | setStat = function(msg, color, spin){
2189 |   _origSetStat(msg, color, spin);
2190 |   var f = document.getElementById("oracle-float");
2191 |   if(f && _oracleMinimized){
2192 |     if(msg === "Speaking") f.classList.add("speaking");
2193 |     else f.classList.remove("speaking");
2194 |   }
2195 | };
2196 | 
2197 | /* ── ORACLE IDLE MATRIX ANIMATION ── */
2198 | (function(){
2199 |   var canvas = document.getElementById('oracle-matrix');
2200 |   if (!canvas) return;
2201 |   var ctx = canvas.getContext('2d');
2202 |   var chars = '01₿⚡∆Ω█▓░10₿Ξ∞◆'.split('');
2203 |   var cols, drops;
2204 | 
2205 |   function resize() {
2206 |     canvas.width = canvas.offsetWidth;
2207 |     canvas.height = canvas.offsetHeight;
2208 |     cols = Math.floor(canvas.width / 14);
2209 |     drops = Array(cols).fill(1);
2210 |   }
2211 |   resize();
2212 |   window.addEventListener('resize', resize);
2213 | 
2214 |   function draw() {
2215 |     ctx.fillStyle = 'rgba(4,5,8,0.05)';
2216 |     ctx.fillRect(0, 0, canvas.width, canvas.height);
2217 |     ctx.font = '11px monospace';
2218 |     for (var i = 0; i < drops.length; i++) {
2219 |       var char = chars[Math.floor(Math.random() * chars.length)];
2220 |       var alpha = Math.random() * 0.4 + 0.05;
2221 |       var cx = canvas.width / 2;
2222 |       var dist = Math.abs(i * 14 - cx) / cx;
2223 |       var r = Math.floor(180 + (1 - dist) * 75);
2224 |       var g = Math.floor(20 + (1 - dist) * 30);
2225 |       var b = Math.floor(40 + (1 - dist) * 20);
2226 |       ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
2227 |       ctx.fillText(char, i * 14, drops[i] * 14);
2228 |       if (drops[i] * 14 > canvas.height && Math.random() > 0.975) drops[i] = 0;
2229 |       drops[i]++;
2230 |     }
2231 |   }
2232 | 
2233 |   var _matrixInterval = setInterval(draw, 50);
2234 | 
2235 |   window._matrixHide = function() {
2236 |     canvas.style.opacity = '0';
2237 |   };
2238 |   window._matrixShow = function() {
2239 |     /* P0-1: Subtle overlay so static avatar face stays visible during idle */
2240 |     canvas.style.opacity = '0.35';
2241 |   };
2242 | })();
2243 | 
2244 | /* ── CYBERPUNK MATRIX BACKGROUND ── */
2245 | (function(){
2246 |   var cvs=document.getElementById('bg-canvas');
2247 |   if(!cvs)return;
2248 |   var ctx=cvs.getContext('2d');
2249 |   var W,H,cols,drops,hexFrags=[];
2250 |   var matrixChars='0123456789ABCDEFabcdef₿⚡∆Ω█▓░▒╔╗╚╝║═';
2251 |   var fontSize=14;
2252 |   var scanY=-2,scanDir=1,scanTimer=0,scanInterval=15000;
2253 | 
2254 |   function resize(){
2255 |     W=cvs.width=cvs.offsetWidth;
2256 |     H=cvs.height=cvs.offsetHeight;
2257 |     cols=Math.floor(W/fontSize);
2258 |     drops=new Array(cols);
2259 |     for(var i=0;i<cols;i++) drops[i]=Math.random()*(-H/fontSize);
2260 |   }
2261 |   resize();
2262 |   window.addEventListener('resize',resize);
2263 | 
2264 |   // Hex fragments: random hex strings that fade in/out
2265 |   function spawnHex(){
2266 |     if(hexFrags.length>6) return;
2267 |     hexFrags.push({
2268 |       x:Math.random()*W,
2269 |       y:Math.random()*H,
2270 |       text:'0x'+Math.random().toString(16).substr(2,6).toUpperCase(),
2271 |       alpha:0,phase:0, // 0=fade in, 1=hold, 2=fade out
2272 |       speed:0.003+Math.random()*0.005,
2273 |       holdTime:2000+Math.random()*3000,
2274 |       holdStart:0
2275 |     });
2276 |   }
2277 | 
2278 |   var lastTime=0;
2279 |   function frame(ts){
2280 |     requestAnimationFrame(frame);
2281 |     if(!lastTime) lastTime=ts;
2282 |     var dt=ts-lastTime;
2283 |     lastTime=ts;
2284 | 
2285 |     ctx.clearRect(0,0,W,H);
2286 | 
2287 |     // 1. Falling matrix characters (sparse)
2288 |     ctx.font=fontSize+'px JetBrains Mono,monospace';
2289 |     for(var i=0;i<cols;i++){
2290 |       if(Math.random()>0.06) { // sparse: only 6% of columns draw per frame
2291 |         if(drops[i]>0){
2292 |           ctx.fillStyle='rgba(255,59,95,0.15)';
2293 |           var ch=matrixChars[Math.floor(Math.random()*matrixChars.length)];
2294 |           ctx.fillText(ch,i*fontSize,drops[i]*fontSize);
2295 |         }
2296 |       }
2297 |       drops[i]+=0.3;
2298 |       if(drops[i]*fontSize>H && Math.random()>0.98){
2299 |         drops[i]=0;
2300 |       }
2301 |     }
2302 | 
2303 |     // 2. Scan line sweep every 15s
2304 |     scanTimer+=dt;
2305 |     if(scanTimer>=scanInterval){
2306 |       scanTimer=0;
2307 |       scanY=-2;
2308 |       scanDir=1;
2309 |     }
2310 |     if(scanY>=0 && scanY<=H){
2311 |       var grad=ctx.createLinearGradient(0,scanY-8,0,scanY+8);
2312 |       grad.addColorStop(0,'rgba(255,59,95,0)');
2313 |       grad.addColorStop(0.5,'rgba(255,59,95,0.12)');
2314 |       grad.addColorStop(1,'rgba(255,59,95,0)');
2315 |       ctx.fillStyle=grad;
2316 |       ctx.fillRect(0,scanY-8,W,16);
2317 |     }
2318 |     if(scanY>=-2 && scanY<=H+10) scanY+=2;
2319 | 
2320 |     // 3. Hex fragments fade in/out
2321 |     if(Math.random()<0.008) spawnHex();
2322 |     for(var h=hexFrags.length-1;h>=0;h--){
2323 |       var frag=hexFrags[h];
2324 |       if(frag.phase===0){
2325 |         frag.alpha+=frag.speed*dt;
2326 |         if(frag.alpha>=0.2){frag.alpha=0.2;frag.phase=1;frag.holdStart=ts;}
2327 |       } else if(frag.phase===1){
2328 |         if(ts-frag.holdStart>frag.holdTime) frag.phase=2;
2329 |       } else {
2330 |         frag.alpha-=frag.speed*dt;
2331 |         if(frag.alpha<=0){hexFrags.splice(h,1);continue;}
2332 |       }
2333 |       ctx.fillStyle='rgba(255,59,95,'+frag.alpha.toFixed(3)+')';
2334 |       ctx.font='10px JetBrains Mono,monospace';
2335 |       ctx.fillText(frag.text,frag.x,frag.y);
2336 |     }
2337 |   }
2338 |   requestAnimationFrame(frame);
2339 | })();
2340 | 
2341 | function fetchTO(url,opts,ms){
2342 |   var ctrl=new AbortController();
2343 |   var id=setTimeout(function(){ctrl.abort();},ms);
2344 |   var o=opts||{};o.signal=ctrl.signal;
2345 |   return fetch(url,o).finally(function(){clearTimeout(id);})
2346 |     .catch(function(e){if(e.name==='AbortError')throw new Error('timeout');throw e;});
2347 | }
2348 | /* ── ACTION CARDS ── */
2349 | function showActionCard(card){
2350 |   var el=document.getElementById('oracle-action-card');
2351 |   var catColor = card.category==='amazon' ? '#FF9900' : card.category==='internal' ? '#6cff9f' : '#ff3b5f';
2352 |   el.innerHTML='<a href="'+card.url+'" target="_blank" rel="noopener" onclick="trackCardClick(\''+card.id+'\')" style="display:block;background:#0d0f14;border:1px solid '+catColor+';border-radius:8px;padding:14px 16px;text-decoration:none;transition:border-color 0.2s;">'
2353 |     +'<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;letter-spacing:.1em;color:'+catColor+';margin-bottom:4px;">'+card.category.toUpperCase()+'</div>'
2354 |     +'<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:4px;">'+card.title+'</div>'
2355 |     +'<div style="font-size:11px;color:rgba(255,255,255,0.55);margin-bottom:10px;">'+card.description+'</div>'
2356 |     +'<div style="font-size:11px;font-weight:600;color:'+catColor+';">'+card.cta+'</div>'
2357 |     +'</a>';
2358 |   el.style.display='block';
2359 |   el.style.opacity='0';
2360 |   setTimeout(function(){el.style.transition='opacity 0.4s';el.style.opacity='1';},100);
2361 |   setTimeout(function(){hideActionCard();},45000);
2362 | }
2363 | function showVisionSponsor(deviceName){
2364 |   if(!deviceName || deviceName==='unknown') return;
2365 |   var key=deviceName.toLowerCase();
2366 |   var match=null;
2367 |   Object.keys(VISION_SPONSOR_MAP).forEach(function(k){
2368 |     if(!match && key.indexOf(k)>=0) match=VISION_SPONSOR_MAP[k];
2369 |   });
2370 |   if(!match) return;
2371 |   showActionCard(match);
2372 | }
2373 | function hideActionCard(){
2374 |   var el=document.getElementById('oracle-action-card');
2375 |   el.style.opacity='0';
2376 |   setTimeout(function(){el.style.display='none';el.innerHTML='';},400);
2377 | }
2378 | function trackCardClick(id){
2379 |   fetch('/api/telemetry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event:'oracle_card_clicked',properties:{card_id:id,fingerprint:window._visitorToken||'anon'}})}).catch(function(){});
2380 | }
2381 | 
2382 | /* ── MOBILE NAV BAR ── */
2383 | (function(){
2384 |   var isMobile=/iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
2385 |   if(isMobile){
2386 |     var nb=document.getElementById('mobile-nav-bar');
2387 |     if(nb) nb.style.display='flex';
2388 |   }
2389 | })();
2390 | 
2391 | window.addEventListener('beforeunload',function(){
2392 |   try{
2393 |     var xhr=new XMLHttpRequest();
2394 |     xhr.open('POST',A+'/oracle/session/save',false);
2395 |     xhr.setRequestHeader('Content-Type','application/json');
2396 |     xhr.send(JSON.stringify({session_id:SESSION_ID}));
2397 |   }catch(e){}
2398 | });
2399 | </script>
2400 | </body>
2401 | </html>
2402 | 
```

---

## YOUR REVIEW TASK — ORACLE FORENSIC: GREETING LIP SYNC + RECOVERING LOOP (8 QUESTIONS)

CONFIRMED FACTS FROM SERVER LOGS:
- Server receives POST /oracle/speak -> returns video/mp4 (646KB greeting cache) -> 200 OK
- Server receives GET /oracle/thinking -> 206 (thinking loop served)
- Server receives POST /oracle/chat -> 200 with job_id
- Server renders Wav2Lip correctly (frames, audio, encoding all confirmed working)
- ALL server-side is working perfectly

THE BUGS (user-confirmed, reproducible every time):
BUG 1: Greeting video plays with NO lip sync — Satomi avatar is static/frozen while audio plays
BUG 2: After greeting, any user speech goes to "Recovering" mode and never produces output

### Q1 — iOS SRC SWAP ON ACTIVELY PLAYING VIDEO
The thinking loop video plays first (vid.muted=true, vid.loop=true, vid.src=/oracle/thinking).
When the greeting blob arrives, playVid() sets vid.muted=false, vid.loop=false, vid.src=blobURL.
On iOS Safari: does changing video.src while a video is actively playing require a user gesture?
Could iOS suppress the src change or show a frozen frame from the previous video?

### Q2 — BLOB URL VIDEO PLAYBACK
The greeting is served as a direct video/mp4 response from /oracle/speak (not via job polling).
The frontend checks content-type 'video' and calls r.blob().then(blobURL).
Is there any scenario where the blob URL is created but the video element shows a static frame
instead of playing the lip-sync animation?

### Q3 — RECOVERING STATE MAPPING
After the greeting plays (or appears to play), _greeted=true is set and startRec() is called.
recognition.start() fires. User speaks. recognition.onresult fires and sets pending.
Then recognition.onend fires. process(pending) is called.
process() calls /oracle/chat -> gets job_id -> polls /oracle/job/{id}/audio -> plays audio.
WHERE exactly does "Recovering" state appear and what triggers it?
Map every state transition that could lead to RECOVERING without ever resolving.

### Q4 — RECOVERING NEVER CLEARED
The oracle server logs show the interactive request received and processed successfully
(job rendered, audio ready, video ready). But the frontend shows "Recovering".
This means the frontend either: (a) never receives the job response, (b) receives it but
fails silently, or (c) the setStat('RECOVERING') is called somewhere and never cleared.
Find every place setStat('Recovering') is called and what conditions lead there.

### Q5 — AUDIO/VIDEO RACE CONDITION
Look at the audio polling flow: fetch /oracle/job/{id}/audio with polling retry.
If this returns 202 (audio not ready), it retries. If it returns 200, it plays audio.
Is there a race condition where audio 200 is received but the EventSource for video_ready
fires before audio.onended, causing the state machine to deadlock?

### Q6 — SETTLED GUARD FROM THINKING LOOP
The video element has a settled guard (_settled flag). If _settled=true from the thinking
loop's safety timeout, could it prevent the greeting video from ever triggering _finish()?

### Q7 — iOS BLOB URL + VIDEO ELEMENT ISSUES
On iOS Safari specifically: does fetch() with a blob response work correctly for video/mp4
of 646KB? Are there any known iOS issues with MediaSource, blob URLs, or video element
src swapping that would cause the video to render as a static image?

### Q8 — MUTED FLAG RACE
Is there a timing issue where vid.muted=true is set AFTER playVid() already set it to false?
Trace every place vid.muted is set in the entire template and identify if any async callback
could re-mute the video after playVid() unmutes it.

### RESPONSE FORMAT
For each question (Q1-Q8):
- ANALYSIS: Detailed trace with line number citations
- BUG CONFIRMED: Yes/No
- SEVERITY: CRITICAL / HIGH / MEDIUM
- ROOT CAUSE: Specific code path
- FIX: Specific code change with line numbers

### FINAL VERDICT
- How many CRITICAL issues confirmed?
- Root cause of the lip sync failure
- Root cause of the Recovering loop
- Ordered fix list (most impactful first)

