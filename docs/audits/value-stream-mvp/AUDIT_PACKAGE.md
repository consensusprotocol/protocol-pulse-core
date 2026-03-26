# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: value-stream-mvp
# Branch: main
# Generated: 2026-03-26 14:42 UTC
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

### File: templates/value_stream.html (474 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Value Stream - Protocol Pulse{% endblock %}
   4 | 
   5 | {% block extra_head %}
   6 | <style>
   7 |     .value-stream-hero {
   8 |         background: linear-gradient(135deg, #0a0a12 0%, #1a0a2e 50%, #0a0a12 100%);
   9 |         padding: 60px 0;
  10 |         border-bottom: 1px solid rgba(138, 43, 226, 0.3);
  11 |     }
  12 |     
  13 |     .stream-title {
  14 |         font-family: 'JetBrains Mono', monospace;
  15 |         font-size: 2.5rem;
  16 |         color: #f7931a;
  17 |         text-shadow: 0 0 30px rgba(247, 147, 26, 0.5);
  18 |     }
  19 |     
  20 |     .stream-subtitle {
  21 |         color: rgba(255,255,255,0.7);
  22 |         font-size: 1.1rem;
  23 |         max-width: 600px;
  24 |         margin: 0 auto;
  25 |     }
  26 |     
  27 |     .platform-filters {
  28 |         display: flex;
  29 |         gap: 12px;
  30 |         justify-content: center;
  31 |         flex-wrap: wrap;
  32 |         margin: 30px 0;
  33 |     }
  34 |     
  35 |     .platform-btn {
  36 |         background: rgba(138, 43, 226, 0.2);
  37 |         border: 1px solid rgba(138, 43, 226, 0.4);
  38 |         color: #fff;
  39 |         padding: 8px 20px;
  40 |         border-radius: 20px;
  41 |         cursor: pointer;
  42 |         transition: all 0.3s ease;
  43 |         font-family: 'JetBrains Mono', monospace;
  44 |         font-size: 0.85rem;
  45 |     }
  46 |     
  47 |     .platform-btn:hover, .platform-btn.active {
  48 |         background: rgba(247, 147, 26, 0.3);
  49 |         border-color: #f7931a;
  50 |         color: #f7931a;
  51 |     }
  52 |     
  53 |     .content-card {
  54 |         background: rgba(20, 20, 35, 0.9);
  55 |         border: 1px solid rgba(138, 43, 226, 0.3);
  56 |         border-radius: 12px;
  57 |         padding: 20px;
  58 |         margin-bottom: 20px;
  59 |         transition: all 0.3s ease;
  60 |     }
  61 |     
  62 |     .content-card:hover {
  63 |         border-color: #f7931a;
  64 |         transform: translateY(-2px);
  65 |         box-shadow: 0 8px 30px rgba(247, 147, 26, 0.15);
  66 |     }
  67 |     
  68 |     .content-card.featured {
  69 |         border-color: #f7931a;
  70 |         background: linear-gradient(135deg, rgba(247, 147, 26, 0.1), rgba(20, 20, 35, 0.9));
  71 |     }
  72 |     
  73 |     .platform-badge {
  74 |         display: inline-block;
  75 |         padding: 4px 10px;
  76 |         border-radius: 12px;
  77 |         font-size: 0.75rem;
  78 |         font-weight: 600;
  79 |         text-transform: uppercase;
  80 |         font-family: 'JetBrains Mono', monospace;
  81 |     }
  82 |     
  83 |     .platform-twitter { background: rgba(29, 161, 242, 0.2); color: #1da1f2; }
  84 |     .platform-youtube { background: rgba(255, 0, 0, 0.2); color: #ff0000; }
  85 |     .platform-reddit { background: rgba(255, 69, 0, 0.2); color: #ff4500; }
  86 |     .platform-nostr { background: rgba(138, 43, 226, 0.2); color: #8a2be2; }
  87 |     .platform-stacker_news { background: rgba(247, 147, 26, 0.2); color: #f7931a; }
  88 |     
  89 |     .signal-score {
  90 |         font-family: 'JetBrains Mono', monospace;
  91 |         font-size: 1.5rem;
  92 |         color: #00ff88;
  93 |         text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
  94 |     }
  95 |     
  96 |     .sats-count {
  97 |         color: #f7931a;
  98 |         font-weight: 600;
  99 |     }
 100 |     
 101 |     .zap-count {
 102 |         color: rgba(255,255,255,0.6);
 103 |     }
 104 |     
 105 |     .curator-badge {
 106 |         display: flex;
 107 |         align-items: center;
 108 |         gap: 8px;
 109 |         padding: 6px 12px;
 110 |         background: rgba(138, 43, 226, 0.2);
 111 |         border-radius: 20px;
 112 |         font-size: 0.85rem;
 113 |     }
 114 |     
 115 |     .curator-badge.verified::after {
 116 |         content: "✓";
 117 |         color: #00ff88;
 118 |         margin-left: 4px;
 119 |     }
 120 |     
 121 |     .zap-btn {
 122 |         background: linear-gradient(135deg, #f7931a, #ff6b00);
 123 |         border: none;
 124 |         color: #000;
 125 |         padding: 10px 24px;
 126 |         border-radius: 8px;
 127 |         font-weight: 700;
 128 |         cursor: pointer;
 129 |         transition: all 0.3s ease;
 130 |         font-family: 'JetBrains Mono', monospace;
 131 |     }
 132 |     
 133 |     .zap-btn:hover {
 134 |         transform: scale(1.05);
 135 |         box-shadow: 0 4px 20px rgba(247, 147, 26, 0.4);
 136 |     }
 137 |     
 138 |     .curator-leaderboard {
 139 |         background: rgba(20, 20, 35, 0.9);
 140 |         border: 1px solid rgba(138, 43, 226, 0.3);
 141 |         border-radius: 12px;
 142 |         padding: 20px;
 143 |     }
 144 |     
 145 |     .curator-row {
 146 |         display: flex;
 147 |         align-items: center;
 148 |         justify-content: space-between;
 149 |         padding: 12px 0;
 150 |         border-bottom: 1px solid rgba(138, 43, 226, 0.2);
 151 |     }
 152 |     
 153 |     .curator-row:last-child {
 154 |         border-bottom: none;
 155 |     }
 156 |     
 157 |     .curator-rank {
 158 |         width: 30px;
 159 |         font-family: 'JetBrains Mono', monospace;
 160 |         color: #f7931a;
 161 |     }
 162 |     
 163 |     .extension-promo {
 164 |         background: linear-gradient(135deg, rgba(247, 147, 26, 0.2), rgba(138, 43, 226, 0.2));
 165 |         border: 1px solid rgba(247, 147, 26, 0.4);
 166 |         border-radius: 16px;
 167 |         padding: 30px;
 168 |         text-align: center;
 169 |         margin: 40px 0;
 170 |     }
 171 |     
 172 |     .extension-btn {
 173 |         background: linear-gradient(135deg, #8a2be2, #6b1fa9);
 174 |         border: none;
 175 |         color: #fff;
 176 |         padding: 14px 32px;
 177 |         border-radius: 8px;
 178 |         font-weight: 700;
 179 |         cursor: pointer;
 180 |         font-size: 1rem;
 181 |         transition: all 0.3s ease;
 182 |     }
 183 |     
 184 |     .extension-btn:hover {
 185 |         transform: scale(1.05);
 186 |         box-shadow: 0 4px 20px rgba(138, 43, 226, 0.4);
 187 |     }
 188 |     
 189 |     .how-it-works {
 190 |         display: grid;
 191 |         grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
 192 |         gap: 24px;
 193 |         margin: 40px 0;
 194 |     }
 195 |     
 196 |     .how-card {
 197 |         background: rgba(20, 20, 35, 0.8);
 198 |         border: 1px solid rgba(138, 43, 226, 0.3);
 199 |         border-radius: 12px;
 200 |         padding: 24px;
 201 |         text-align: center;
 202 |     }
 203 |     
 204 |     .how-icon {
 205 |         font-size: 2.5rem;
 206 |         margin-bottom: 16px;
 207 |     }
 208 |     
 209 |     .empty-stream {
 210 |         text-align: center;
 211 |         padding: 60px;
 212 |         color: rgba(255,255,255,0.5);
 213 |     }
 214 |     
 215 |     .submit-form {
 216 |         background: rgba(20, 20, 35, 0.9);
 217 |         border: 1px solid rgba(138, 43, 226, 0.3);
 218 |         border-radius: 12px;
 219 |         padding: 24px;
 220 |         margin-bottom: 30px;
 221 |     }
 222 |     
 223 |     .submit-input {
 224 |         background: rgba(0,0,0,0.3);
 225 |         border: 1px solid rgba(138, 43, 226, 0.4);
 226 |         color: #fff;
 227 |         padding: 12px 16px;
 228 |         border-radius: 8px;
 229 |         width: 100%;
 230 |         font-family: 'JetBrains Mono', monospace;
 231 |     }
 232 |     
 233 |     .submit-input:focus {
 234 |         outline: none;
 235 |         border-color: #f7931a;
 236 |     }
 237 | </style>
 238 | {% endblock %}
 239 | 
 240 | {% block content %}
 241 | <div class="value-stream-hero text-center">
 242 |     <div class="container">
 243 |         <h1 class="stream-title">
 244 |             <i class="fas fa-bolt"></i> VALUE STREAM
 245 |         </h1>
 246 |         <p class="stream-subtitle">
 247 |             Decentralized content curation powered by sats. The best content rises based on 
 248 |             real economic signals, not engagement farming. Zap to signal value.
 249 |         </p>
 250 |         
 251 |         <div class="platform-filters">
 252 |             <button class="platform-btn active" data-platform="all">ALL PLATFORMS</button>
 253 |             <button class="platform-btn" data-platform="twitter">X/TWITTER</button>
 254 |             <button class="platform-btn" data-platform="youtube">YOUTUBE</button>
 255 |             <button class="platform-btn" data-platform="nostr">NOSTR</button>
 256 |             <button class="platform-btn" data-platform="reddit">REDDIT</button>
 257 |             <button class="platform-btn" data-platform="stacker_news">STACKER NEWS</button>
 258 |         </div>
 259 |     </div>
 260 | </div>
 261 | 
 262 | <div class="container py-5">
 263 |     <div class="row">
 264 |         <div class="col-lg-8">
 265 |             <div class="submit-form">
 266 |                 <h5 class="text-white mb-3"><i class="fas fa-plus-circle text-warning"></i> Curate Content</h5>
 267 |                 <form id="submit-content-form" class="d-flex gap-3">
 268 |                     <input type="url" class="submit-input flex-grow-1" id="content-url" 
 269 |                            placeholder="Paste URL from any platform..." required>
 270 |                     <button type="submit" class="zap-btn">
 271 |                         <i class="fas fa-paper-plane"></i> SUBMIT
 272 |                     </button>
 273 |                 </form>
 274 |                 <small class="text-muted mt-2 d-block">Share valuable content and earn curator splits when others zap</small>
 275 |             </div>
 276 |             
 277 |             <div id="value-stream-feed">
 278 |                 {% if posts %}
 279 |                     {% for post in posts %}
 280 |                     <div class="content-card {% if post.is_featured %}featured{% endif %}">
 281 |                         <div class="d-flex justify-content-between align-items-start mb-3">
 282 |                             <div>
 283 |                                 <span class="platform-badge platform-{{ post.platform }}">
 284 |                                     {{ post.platform }}
 285 |                                 </span>
 286 |                                 {% if post.is_featured %}
 287 |                                 <span class="badge bg-warning text-dark ms-2">FEATURED</span>
 288 |                                 {% endif %}
 289 |                             </div>
 290 |                             <div class="signal-score" title="Signal Score">
 291 |                                 {{ "%.1f"|format(post.signal_score) }}
 292 |                             </div>
 293 |                         </div>
 294 |                         
 295 |                         <h5 class="text-white mb-2">
 296 |                             <a href="{{ post.original_url }}" target="_blank" class="text-decoration-none text-white">
 297 |                                 {{ post.title or 'Untitled Content' }}
 298 |                                 <i class="fas fa-external-link-alt fa-xs ms-2 text-muted"></i>
 299 |                             </a>
 300 |                         </h5>
 301 |                         
 302 |                         {% if post.content_preview %}
 303 |                         <p class="text-muted mb-3">{{ post.content_preview[:200] }}...</p>
 304 |                         {% endif %}
 305 |                         
 306 |                         <div class="d-flex justify-content-between align-items-center mt-3">
 307 |                             <div class="d-flex gap-4">
 308 |                                 <span class="sats-count">
 309 |                                     <i class="fas fa-bolt"></i> {{ "{:,}".format(post.total_sats) }} sats
 310 |                                 </span>
 311 |                                 <span class="zap-count">
 312 |                                     {{ post.zap_count }} zaps
 313 |                                 </span>
 314 |                             </div>
 315 |                             
 316 |                             <div class="d-flex align-items-center gap-3">
 317 |                                 {% if post.curator %}
 318 |                                 <div class="curator-badge {% if post.curator.verified %}verified{% endif %}">
 319 |                                     <i class="fas fa-user-check"></i>
 320 |                                     {{ post.curator.display_name }}
 321 |                                 </div>
 322 |                                 {% endif %}
 323 |                                 
 324 |                                 <button class="zap-btn zap-content-btn" data-post-id="{{ post.id }}">
 325 |                                     <i class="fas fa-bolt"></i> ZAP
 326 |                                 </button>
 327 |                             </div>
 328 |                         </div>
 329 |                     </div>
 330 |                     {% endfor %}
 331 |                 {% else %}
 332 |                     <div class="empty-stream">
 333 |                         <i class="fas fa-stream fa-3x mb-3"></i>
 334 |                         <h4>No Curated Content Yet</h4>
 335 |                         <p>Be the first to curate valuable content and earn sats when others zap!</p>
 336 |                     </div>
 337 |                 {% endif %}
 338 |             </div>
 339 |         </div>
 340 |         
 341 |         <div class="col-lg-4">
 342 |             <div class="extension-promo mb-4">
 343 |                 <h4 class="text-white mb-3">
 344 |                     <i class="fas fa-puzzle-piece"></i> Browser Extension
 345 |                 </h4>
 346 |                 <p class="text-muted mb-4">
 347 |                     Zap content anywhere on the web. Curate from any site. 
 348 |                     Connect your Lightning wallet.
 349 |                 </p>
 350 |                 <a href="/extension" class="extension-btn text-decoration-none">
 351 |                     <i class="fas fa-download me-2"></i> GET EXTENSION
 352 |                 </a>
 353 |             </div>
 354 |             
 355 |             <div class="curator-leaderboard">
 356 |                 <h5 class="text-white mb-3">
 357 |                     <i class="fas fa-trophy text-warning"></i> Top Curators
 358 |                 </h5>
 359 |                 
 360 |                 {% if curators %}
 361 |                     {% for curator in curators[:10] %}
 362 |                     <div class="curator-row">
 363 |                         <div class="d-flex align-items-center gap-3">
 364 |                             <span class="curator-rank">#{{ loop.index }}</span>
 365 |                             <div>
 366 |                                 <div class="text-white">
 367 |                                     {{ curator.display_name }}
 368 |                                     {% if curator.verified %}
 369 |                                     <i class="fas fa-check-circle text-success fa-xs"></i>
 370 |                                     {% endif %}
 371 |                                 </div>
 372 |                                 <small class="text-muted">Score: {{ curator.curator_score }}</small>
 373 |                             </div>
 374 |                         </div>
 375 |                         <div class="text-end">
 376 |                             <div class="sats-count small">{{ "{:,}".format(curator.total_sats_received) }}</div>
 377 |                             <small class="text-muted">{{ curator.total_zaps }} zaps</small>
 378 |                         </div>
 379 |                     </div>
 380 |                     {% endfor %}
 381 |                 {% else %}
 382 |                     <p class="text-muted text-center py-3">No curators yet</p>
 383 |                 {% endif %}
 384 |             </div>
 385 |             
 386 |             <div class="how-it-works mt-4">
 387 |                 <div class="how-card">
 388 |                     <div class="how-icon">🔗</div>
 389 |                     <h6 class="text-white">1. Curate</h6>
 390 |                     <p class="text-muted small mb-0">Share valuable content from any platform</p>
 391 |                 </div>
 392 |                 <div class="how-card">
 393 |                     <div class="how-icon">⚡</div>
 394 |                     <h6 class="text-white">2. Zap</h6>
 395 |                     <p class="text-muted small mb-0">Send sats to signal content value</p>
 396 |                 </div>
 397 |                 <div class="how-card">
 398 |                     <div class="how-icon">📈</div>
 399 |                     <h6 class="text-white">3. Rise</h6>
 400 |                     <p class="text-muted small mb-0">Best content surfaces via economic signal</p>
 401 |                 </div>
 402 |                 <div class="how-card">
 403 |                     <div class="how-icon">💰</div>
 404 |                     <h6 class="text-white">4. Earn</h6>
 405 |                     <p class="text-muted small mb-0">Curators get 10% of zaps to content they share</p>
 406 |                 </div>
 407 |             </div>
 408 |         </div>
 409 |     </div>
 410 | </div>
 411 | 
 412 | <script>
 413 | document.querySelectorAll('.platform-btn').forEach(btn => {
 414 |     btn.addEventListener('click', function() {
 415 |         document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
 416 |         this.classList.add('active');
 417 |         const platform = this.dataset.platform;
 418 |         window.location.href = platform === 'all' ? '/value-stream' : `/value-stream?platform=${platform}`;
 419 |     });
 420 | });
 421 | 
 422 | document.getElementById('submit-content-form')?.addEventListener('submit', async function(e) {
 423 |     e.preventDefault();
 424 |     const url = document.getElementById('content-url').value;
 425 |     
 426 |     try {
 427 |         const response = await fetch('/api/value-stream/submit', {
 428 |             method: 'POST',
 429 |             headers: {'Content-Type': 'application/json'},
 430 |             body: JSON.stringify({url: url})
 431 |         });
 432 |         const data = await response.json();
 433 |         
 434 |         if (data.success) {
 435 |             alert('Content curated successfully!');
 436 |             window.location.reload();
 437 |         } else {
 438 |             alert(data.error || 'Failed to curate content');
 439 |         }
 440 |     } catch (err) {
 441 |         alert('Error submitting content');
 442 |     }
 443 | });
 444 | 
 445 | document.querySelectorAll('.zap-content-btn').forEach(btn => {
 446 |     btn.addEventListener('click', async function() {
 447 |         const postId = this.dataset.postId;
 448 |         
 449 |         if (typeof webln !== 'undefined') {
 450 |             try {
 451 |                 await webln.enable();
 452 |                 const response = await fetch(`/api/value-stream/invoice/${postId}`, {
 453 |                     method: 'POST',
 454 |                     headers: {'Content-Type': 'application/json'},
 455 |                     body: JSON.stringify({amount_sats: 1000})
 456 |                 });
 457 |                 const data = await response.json();
 458 |                 
 459 |                 if (data.invoice) {
 460 |                     const result = await webln.sendPayment(data.invoice);
 461 |                     alert('Zap sent! Thank you for signaling value.');
 462 |                     window.location.reload();
 463 |                 }
 464 |             } catch (err) {
 465 |                 alert('WebLN payment failed: ' + err.message);
 466 |             }
 467 |         } else {
 468 |             alert('Please install a WebLN-compatible wallet extension (Alby, etc.)');
 469 |         }
 470 |     });
 471 | });
 472 | </script>
 473 | {% endblock %}
 474 | 
```

### File: services/value_stream_service.py (698 lines)
```
   1 | """
   2 | Value Stream — Sovereign Intelligence Market.
   3 | Curated content feed and creator/curator APIs with metadata enrichment and zap splits.
   4 | """
   5 | 
   6 | import logging
   7 | import re
   8 | from datetime import datetime, timedelta
   9 | from urllib.parse import urlparse
  10 | from urllib.parse import urlunparse
  11 | 
  12 | logger = logging.getLogger(__name__)
  13 | 
  14 | # Curator earns 10%, creator/platform gets 90%
  15 | CURATOR_SPLIT = 0.10
  16 | CREATOR_SPLIT = 0.90
  17 | 
  18 | 
  19 | def _extract_meta(soup):
  20 |     """Extract metadata across OG/Twitter tags."""
  21 |     title = None
  22 |     description = None
  23 |     image = None
  24 | 
  25 |     title_selectors = [
  26 |         ("meta", {"property": "og:title"}),
  27 |         ("meta", {"name": "twitter:title"}),
  28 |     ]
  29 |     desc_selectors = [
  30 |         ("meta", {"property": "og:description"}),
  31 |         ("meta", {"name": "twitter:description"}),
  32 |         ("meta", {"name": "description"}),
  33 |     ]
  34 |     image_selectors = [
  35 |         ("meta", {"property": "og:image"}),
  36 |         ("meta", {"name": "twitter:image"}),
  37 |     ]
  38 | 
  39 |     for tag_name, attrs in title_selectors:
  40 |         tag = soup.find(tag_name, attrs=attrs)
  41 |         if tag and tag.get("content"):
  42 |             title = tag.get("content")
  43 |             break
  44 |     if not title and soup.title and soup.title.string:
  45 |         title = soup.title.string
  46 | 
  47 |     for tag_name, attrs in desc_selectors:
  48 |         tag = soup.find(tag_name, attrs=attrs)
  49 |         if tag and tag.get("content"):
  50 |             description = tag.get("content")
  51 |             break
  52 | 
  53 |     for tag_name, attrs in image_selectors:
  54 |         tag = soup.find(tag_name, attrs=attrs)
  55 |         if tag and tag.get("content"):
  56 |             image = tag.get("content")
  57 |             break
  58 | 
  59 |     title = (title or "").strip()[:500] or None
  60 |     description = (description or "").strip()[:1000] or None
  61 |     image = (image or "").strip()[:500] or None
  62 |     if image and image.startswith("//"):
  63 |         image = "https:" + image
  64 | 
  65 |     return {"title": title, "description": description, "image": image}
  66 | 
  67 | 
  68 | def _fetch_html(url, timeout=8):
  69 |     import requests
  70 |     headers = {
  71 |         "User-Agent": "Mozilla/5.0 (compatible; ProtocolPulse/1.0)",
  72 |         "Accept-Language": "en-US,en;q=0.9",
  73 |     }
  74 |     resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
  75 |     if not resp.text:
  76 |         return None
  77 |     return resp.text
  78 | 
  79 | 
  80 | def _tweet_id_from_url(url):
  81 |     if not url:
  82 |         return None
  83 |     m = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", url, re.I)
  84 |     return m.group(1) if m else None
  85 | 
  86 | 
  87 | def _large_twitter_image(url):
  88 |     """Promote twitter CDN image URLs to large variant where possible."""
  89 |     if not url:
  90 |         return None
  91 |     if "pbs.twimg.com" not in url:
  92 |         return url
  93 |     if "name=" in url:
  94 |         return re.sub(r"name=\w+", "name=large", url)
  95 |     return url + ("&name=large" if "?" in url else "?name=large")
  96 | 
  97 | 
  98 | def _fetch_x_api_metadata(tweet_id):
  99 |     """Fetch text/media for X posts from fx/vx API mirrors."""
 100 |     try:
 101 |         import requests
 102 |         resp = requests.get(f"https://api.fxtwitter.com/status/{tweet_id}", timeout=8)
 103 |         if resp.ok:
 104 |             data = resp.json() or {}
 105 |             tweet = data.get("tweet") or {}
 106 |             text = (tweet.get("text") or tweet.get("raw_text") or "").strip()
 107 |             author = ((tweet.get("author") or {}).get("name") or "").strip()
 108 |             media = tweet.get("media") or {}
 109 |             media_all = media.get("all") or []
 110 |             image = None
 111 |             for item in media_all:
 112 |                 if not isinstance(item, dict):
 113 |                     continue
 114 |                 thumb = item.get("thumbnail_url")
 115 |                 url = item.get("url")
 116 |                 image = _large_twitter_image(thumb or url)
 117 |                 if image:
 118 |                     break
 119 |             title = f"Post by {author}" if author else "X post"
 120 |             if text or image:
 121 |                 return {"title": title[:500], "description": text[:1000] or None, "image": image}
 122 |     except Exception:
 123 |         pass
 124 | 
 125 |     try:
 126 |         import requests
 127 |         resp = requests.get(f"https://api.vxtwitter.com/Twitter/status/{tweet_id}", timeout=8)
 128 |         if resp.ok:
 129 |             data = resp.json() or {}
 130 |             text = (data.get("text") or "").strip()
 131 |             author = (data.get("user_name") or data.get("user_screen_name") or "").strip()
 132 |             image = None
 133 |             for item in (data.get("media_extended") or []):
 134 |                 if not isinstance(item, dict):
 135 |                     continue
 136 |                 thumb = item.get("thumbnail_url")
 137 |                 url = item.get("url")
 138 |                 image = _large_twitter_image(thumb or url)
 139 |                 if image:
 140 |                     break
 141 |             title = f"Post by {author}" if author else "X post"
 142 |             if text or image:
 143 |                 return {"title": title[:500], "description": text[:1000] or None, "image": image}
 144 |     except Exception:
 145 |         pass
 146 |     return None
 147 | 
 148 | 
 149 | def fetch_metadata(url):
 150 |     """Scrape metadata from URL with X/Twitter fallback domains. Returns dict or None."""
 151 |     try:
 152 |         from bs4 import BeautifulSoup
 153 |         parsed = urlparse(url)
 154 | 
 155 |         html = _fetch_html(url)
 156 |         if html:
 157 |             primary = _extract_meta(BeautifulSoup(html, "html.parser"))
 158 |             if primary.get("title") or primary.get("description") or primary.get("image"):
 159 |                 return primary
 160 | 
 161 |         # X/Twitter often blocks OG for server-side requests. Try metadata mirrors.
 162 |         host = (parsed.netloc or "").lower()
 163 |         if "x.com" in host or "twitter.com" in host:
 164 |             tweet_id = _tweet_id_from_url(url)
 165 |             if tweet_id:
 166 |                 api_meta = _fetch_x_api_metadata(tweet_id)
 167 |                 if api_meta and (api_meta.get("title") or api_meta.get("description") or api_meta.get("image")):
 168 |                     return api_meta
 169 | 
 170 |             path_with_query = urlunparse(("", "", parsed.path or "", parsed.params or "", parsed.query or "", ""))
 171 |             for alt_base in ("https://vxtwitter.com", "https://fxtwitter.com"):
 172 |                 alt_url = f"{alt_base}{path_with_query}"
 173 |                 try:
 174 |                     alt_html = _fetch_html(alt_url)
 175 |                     if not alt_html:
 176 |                         continue
 177 |                     alt_meta = _extract_meta(BeautifulSoup(alt_html, "html.parser"))
 178 |                     if alt_meta.get("title") or alt_meta.get("description") or alt_meta.get("image"):
 179 |                         return alt_meta
 180 |                 except Exception:
 181 |                     continue
 182 | 
 183 |             # Fallback: Twitter/X oEmbed still returns text when OG tags are unavailable.
 184 |             try:
 185 |                 import requests
 186 |                 from bs4 import BeautifulSoup
 187 |                 resp = requests.get(
 188 |                     "https://publish.twitter.com/oembed",
 189 |                     params={"url": url, "omit_script": "1", "dnt": "true"},
 190 |                     timeout=8,
 191 |                 )
 192 |                 if resp.ok:
 193 |                     data = resp.json()
 194 |                     html_snippet = data.get("html") or ""
 195 |                     soup = BeautifulSoup(html_snippet, "html.parser")
 196 |                     p = soup.find("p")
 197 |                     text = (p.get_text(" ", strip=True) if p else "").strip()
 198 |                     author = (data.get("author_name") or "").strip()
 199 |                     title = f"Post by {author}" if author else "X post"
 200 |                     if text:
 201 |                         return {
 202 |                             "title": title[:500],
 203 |                             "description": text[:1000],
 204 |                             "image": None,
 205 |                         }
 206 |             except Exception:
 207 |                 pass
 208 |     except Exception as e:
 209 |         logger.warning("fetch_metadata failed for %s: %s", url[:80], e)
 210 |     return None
 211 | 
 212 | 
 213 | def _platform_from_url(url):
 214 |     """Infer platform from URL for badge/filter. Returns x, youtube, nostr, reddit, stacker, web."""
 215 |     try:
 216 |         parsed = urlparse(url)
 217 |         host = (parsed.netloc or "").lower()
 218 |         if "youtube.com" in host or "youtu.be" in host:
 219 |             return "youtube"
 220 |         if "twitter.com" in host or "x.com" in host:
 221 |             return "x"
 222 |         if "reddit.com" in host:
 223 |             return "reddit"
 224 |         if "stacker.news" in host or "stackernews" in host:
 225 |             return "stacker"
 226 |         if "nostr" in host or "njump" in host or "snort" in host:
 227 |             return "nostr"
 228 |     except Exception:
 229 |         pass
 230 |     return "web"
 231 | 
 232 | 
 233 | def _db():
 234 |     from app import db
 235 |     return db
 236 | 
 237 | 
 238 | def _models():
 239 |     import models
 240 |     return models
 241 | 
 242 | 
 243 | def get_value_stream(limit=50, platform=None):
 244 |     """Return list of post dicts with at least 'id' for CuratedPost.query.get."""
 245 |     from flask import has_app_context
 246 |     if not has_app_context():
 247 |         from app import app
 248 |         with app.app_context():
 249 |             return get_value_stream(limit=limit, platform=platform)
 250 |     db = _db()
 251 |     models = _models()
 252 |     q = models.CuratedPost.query.order_by(db.func.coalesce(models.CuratedPost.signal_score, 0).desc())
 253 |     if platform:
 254 |         if platform == "stacker":
 255 |             q = q.filter(models.CuratedPost.platform.in_(["stacker", "stacker_news"]))
 256 |         else:
 257 |             q = q.filter(models.CuratedPost.platform == platform)
 258 |     posts = q.limit(limit).all()
 259 |     return [{"id": p.id} for p in posts]
 260 | 
 261 | 
 262 | def get_top_curators(limit=10):
 263 |     """Return list of curator dicts with at least 'id' for ValueCreator.query.get."""
 264 |     from flask import has_app_context
 265 |     if not has_app_context():
 266 |         from app import app
 267 |         with app.app_context():
 268 |             return get_top_curators(limit=limit)
 269 |     db = _db()
 270 |     models = _models()
 271 |     curators = (
 272 |         models.ValueCreator.query
 273 |         .order_by(db.func.coalesce(models.ValueCreator.curator_score, 0).desc())
 274 |         .limit(limit)
 275 |         .all()
 276 |     )
 277 |     return [{"id": c.id} for c in curators]
 278 | 
 279 | 
 280 | def get_value_stream_enhanced(limit=50):
 281 |     """Enhanced feed for Signal Terminal: list of dicts with post + curator info."""
 282 |     db = _db()
 283 |     models = _models()
 284 |     posts = (
 285 |         models.CuratedPost.query
 286 |         .order_by(db.func.coalesce(models.CuratedPost.signal_score, 0).desc())
 287 |         .limit(limit)
 288 |         .all()
 289 |     )
 290 |     out = []
 291 |     for p in posts:
 292 |         c = p.curator if hasattr(p, "curator") else None
 293 |         out.append({
 294 |             "id": p.id,
 295 |             "platform": p.platform or "",
 296 |             "title": p.title or "Untitled",
 297 |             "content_preview": (p.content_preview or "")[:200],
 298 |             "original_url": p.original_url or "",
 299 |             "total_sats": p.total_sats or 0,
 300 |             "zap_count": p.zap_count or 0,
 301 |             "signal_score": round(p.signal_score or 0, 2),
 302 |             "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
 303 |             "curator_name": c.display_name if c else "Anonymous",
 304 |             "curator_id": c.id if c else None,
 305 |         })
 306 |     return out
 307 | 
 308 | 
 309 | def submit_content(url, curator_id, title):
 310 |     """Submit a new curated post. Enriches with og:title/description/image and platform. Returns {success, id} or {success: False, error}."""
 311 |     db = _db()
 312 |     models = _models()
 313 |     try:
 314 |         url = (url or "").strip()
 315 |         if not url.startswith(("http://", "https://")):
 316 |             url = "https://" + url
 317 |         existing = models.CuratedPost.query.filter_by(original_url=url).first()
 318 |         if existing:
 319 |             # If older row was created before metadata parser worked, backfill now.
 320 |             if (existing.thumbnail_url or "").startswith("https://www.google.com/s2/favicons"):
 321 |                 existing.thumbnail_url = None
 322 |                 db.session.commit()
 323 |             needs_backfill = (
 324 |                 not existing.content_preview
 325 |                 or not existing.thumbnail_url
 326 |                 or not existing.title
 327 |                 or existing.title == existing.original_url
 328 |             )
 329 |             if needs_backfill:
 330 |                 meta = fetch_metadata(url)
 331 |                 changed = False
 332 |                 if meta:
 333 |                     if (not existing.title or existing.title == existing.original_url) and meta.get("title"):
 334 |                         existing.title = meta["title"]
 335 |                         changed = True
 336 |                     if not existing.content_preview and meta.get("description"):
 337 |                         existing.content_preview = meta["description"]
 338 |                         changed = True
 339 |                     if not existing.thumbnail_url and meta.get("image"):
 340 |                         existing.thumbnail_url = meta["image"]
 341 |                         changed = True
 342 |                     if changed:
 343 |                         db.session.commit()
 344 |             return {"success": True, "id": existing.id, "existing": True}
 345 |         meta = fetch_metadata(url)
 346 |         platform = _platform_from_url(url)
 347 |         title_val = (title or "").strip()[:500]
 348 |         content_preview = None
 349 |         thumbnail_url = None
 350 |         if meta:
 351 |             if not title_val and meta.get("title"):
 352 |                 title_val = meta["title"]
 353 |             if meta.get("description"):
 354 |                 content_preview = meta["description"]
 355 |             if meta.get("image"):
 356 |                 thumbnail_url = meta["image"]
 357 |         if not title_val:
 358 |             title_val = url
 359 |         post = models.CuratedPost(
 360 |             platform=platform,
 361 |             original_url=url,
 362 |             title=title_val,
 363 |             content_preview=content_preview,
 364 |             thumbnail_url=thumbnail_url,
 365 |             curator_id=curator_id,
 366 |         )
 367 |         if post.submitted_at is None:
 368 |             post.submitted_at = datetime.utcnow()
 369 |         post.calculate_signal_score()
 370 |         db.session.add(post)
 371 |         db.session.commit()
 372 |         return {"success": True, "id": post.id}
 373 |     except Exception as e:
 374 |         logger.exception("submit_content failed")
 375 |         db.session.rollback()
 376 |         return {"success": False, "error": str(e)}
 377 | 
 378 | 
 379 | def process_zap(post_id, sender_id, amount, payment_hash):
 380 |     """Record a zap and update post totals. Returns {success, ...}."""
 381 |     import os
 382 |     db = _db()
 383 |     models = _models()
 384 |     try:
 385 |         post = models.CuratedPost.query.get(post_id)
 386 |         if not post:
 387 |             return {"success": False, "error": "Post not found"}
 388 |         require_verify = str(os.environ.get("VERIFY_ZAP_PAYMENT", "true")).strip().lower() in {"1", "true", "yes", "on"}
 389 |         verified = bool(payment_hash) or not require_verify
 390 |         curator_share_sats = int(amount * CURATOR_SPLIT)
 391 |         creator_share_sats = amount - curator_share_sats
 392 |         zap = models.ZapEvent(
 393 |             post_id=post_id,
 394 |             sender_id=sender_id,
 395 |             amount_sats=amount,
 396 |             curator_share=curator_share_sats,
 397 |             creator_share=creator_share_sats,
 398 |             platform_share=0,
 399 |             payment_hash=payment_hash or "",
 400 |             status="settled" if verified else "pending",
 401 |         )
 402 |         db.session.add(zap)
 403 |         db.session.flush()
 404 |         zap_id = zap.id
 405 |         if verified:
 406 |             post.total_sats = (post.total_sats or 0) + amount
 407 |             post.zap_count = (post.zap_count or 0) + 1
 408 |             post.last_zap_at = datetime.utcnow()
 409 |             post.calculate_signal_score()
 410 |             if post.curator_id:
 411 |                 curator = models.ValueCreator.query.get(post.curator_id)
 412 |                 if curator:
 413 |                     curator.total_sats_received = (curator.total_sats_received or 0) + curator_share_sats
 414 |                     curator.total_zaps = (curator.total_zaps or 0) + 1
 415 |             if post.creator_id:
 416 |                 creator = models.ValueCreator.query.get(post.creator_id)
 417 |                 if creator:
 418 |                     creator.total_sats_received = (creator.total_sats_received or 0) + creator_share_sats
 419 |         db.session.commit()
 420 |         return {
 421 |             "success": True,
 422 |             "post_id": post_id,
 423 |             "zap_id": zap_id,
 424 |             "amount_sats": amount,
 425 |             "curator_share_sats": curator_share_sats,
 426 |             "creator_share_sats": creator_share_sats,
 427 |             "status": "settled" if verified else "pending",
 428 |         }
 429 |     except Exception as e:
 430 |         logger.exception("process_zap failed")
 431 |         db.session.rollback()
 432 |         return {"success": False, "error": str(e)}
 433 | 
 434 | 
 435 | def post_zap_comment(post_id, zap_id, amount_sats, base_url=None):
 436 |     """
 437 |     Diplomat bridge: after a zap, post a reply on X (and optionally Nostr) so the KOL can claim sats.
 438 |     base_url e.g. https://protocolpulse.com. Claim URL = base_url/value-stream/claim?zap_id=...
 439 |     """
 440 |     import os
 441 |     db = _db()
 442 |     models = _models()
 443 |     post = models.CuratedPost.query.get(post_id)
 444 |     if not post:
 445 |         return
 446 |     base_url = (base_url or os.environ.get("PROTOCOL_PULSE_CLAIM_BASE_URL") or "").rstrip("/")
 447 |     claim_path = f"/value-stream/claim?zap={zap_id}"
 448 |     claim_url = f"{base_url}{claim_path}" if base_url else claim_path
 449 |     amount_str = f"{amount_sats:,}" if amount_sats >= 1000 else str(amount_sats)
 450 |     message = f"⚡ Signal detected. You received {amount_str} sats on Protocol Pulse for this alpha. Claim: {claim_url}"
 451 |     if post.platform in ("x", "twitter"):
 452 |         tweet_id = _tweet_id_from_url(post.original_url) or post.original_id
 453 |         if tweet_id:
 454 |             try:
 455 |                 from services.x_service import XService
 456 |                 svc = XService()
 457 |                 reply_id = svc.post_reply(tweet_id, message)
 458 |                 if reply_id:
 459 |                     log = models.ZapCommentLog(
 460 |                         post_id=post_id,
 461 |                         zap_event_id=zap_id,
 462 |                         platform="x",
 463 |                         external_id=tweet_id,
 464 |                         reply_id=reply_id,
 465 |                         message=message,
 466 |                         claim_url=claim_url,
 467 |                     )
 468 |                     db.session.add(log)
 469 |                     db.session.commit()
 470 |                     logger.info("Zap comment posted to X for post %s reply %s", post_id, reply_id)
 471 |             except Exception as e:
 472 |                 logger.warning("post_zap_comment X: %s", e)
 473 |     # Nostr kind:9734 stub: would broadcast zap request to creator's pubkey if we have it
 474 |     # if post.creator and post.creator.nostr_pubkey: ...
 475 | 
 476 | 
 477 | def register_creator(display_name, nostr_pubkey=None, lightning_address=None, nip05=None):
 478 |     """Register a new value creator. Returns {success, id} or {success: False, error}."""
 479 |     db = _db()
 480 |     models = _models()
 481 |     try:
 482 |         existing = models.ValueCreator.query.filter_by(display_name=display_name).first()
 483 |         if existing:
 484 |             return {"success": True, "id": existing.id, "existing": True}
 485 |         creator = models.ValueCreator(
 486 |             display_name=display_name[:100],
 487 |             nostr_pubkey=nostr_pubkey[:128] if nostr_pubkey else None,
 488 |             lightning_address=lightning_address[:200] if lightning_address else None,
 489 |             nip05=nip05[:200] if nip05 else None,
 490 |         )
 491 |         db.session.add(creator)
 492 |         db.session.commit()
 493 |         return {"success": True, "id": creator.id}
 494 |     except Exception as e:
 495 |         logger.exception("register_creator failed")
 496 |         db.session.rollback()
 497 |         return {"success": False, "error": str(e)}
 498 | 
 499 | 
 500 | # ---------- Sovereign Claim Portal ----------
 501 | 
 502 | def get_claimable_balance(creator_id):
 503 |     """Claimable sats = total_sats_received - sum of successful payouts."""
 504 |     try:
 505 |         db = _db()
 506 |         models = _models()
 507 |         creator = models.ValueCreator.query.get(creator_id)
 508 |         if not creator:
 509 |             return 0
 510 |         total = creator.total_sats_received or 0
 511 |         paid = db.session.query(db.func.coalesce(db.func.sum(models.ClaimPayout.amount_sats), 0)).filter(
 512 |             models.ClaimPayout.creator_id == creator_id,
 513 |             models.ClaimPayout.status == "sent"
 514 |         ).scalar() or 0
 515 |         return max(0, int(total) - int(paid))
 516 |     except Exception as e:
 517 |         logger.warning("get_claimable_balance failed: %s", e)
 518 |         return 0
 519 | 
 520 | 
 521 | def get_creator_by_pubkey(pubkey):
 522 |     """Return ValueCreator for nostr_pubkey or None."""
 523 |     if not pubkey or not isinstance(pubkey, str):
 524 |         return None
 525 |     models = _models()
 526 |     return models.ValueCreator.query.filter_by(nostr_pubkey=pubkey.strip()).first()
 527 | 
 528 | 
 529 | def _last_claim_at(pubkey):
 530 |     """Timestamp of most recent successful claim by this pubkey, or None."""
 531 |     try:
 532 |         db = _db()
 533 |         models = _models()
 534 |         creator = get_creator_by_pubkey(pubkey)
 535 |         if not creator:
 536 |             return None
 537 |         row = (
 538 |             db.session.query(db.func.max(models.ClaimPayout.settled_at))
 539 |             .filter(
 540 |                 models.ClaimPayout.claimed_by_pubkey == pubkey.strip(),
 541 |                 models.ClaimPayout.status == "sent"
 542 |             )
 543 |             .scalar()
 544 |         )
 545 |         return row
 546 |     except Exception as e:
 547 |         logger.warning("_last_claim_at failed: %s", e)
 548 |         return None
 549 | 
 550 | 
 551 | def _parse_datetime(value):
 552 |     """Parse DB datetime (may be datetime or string from SQLite) to datetime or None."""
 553 |     if value is None:
 554 |         return None
 555 |     if isinstance(value, datetime):
 556 |         return value
 557 |     if isinstance(value, str):
 558 |         # Try without microseconds first (SQLite often returns no .ffffff)
 559 |         for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
 560 |             try:
 561 |                 s = value[:26] if len(value) > 26 else value
 562 |                 return datetime.strptime(s, fmt)
 563 |             except Exception:
 564 |                 continue
 565 |     return None
 566 | 
 567 | 
 568 | def can_claim_again(pubkey):
 569 |     """True if no successful claim in the last 24 hours for this pubkey."""
 570 |     last = _last_claim_at(pubkey)
 571 |     last_dt = _parse_datetime(last)
 572 |     if last_dt is None:
 573 |         return True
 574 |     return (datetime.utcnow() - last_dt).total_seconds() >= 24 * 3600
 575 | 
 576 | 
 577 | def _verify_nostr_signature(pubkey_hex, message, sig_hex):
 578 |     """Verify Nostr-style schnorr signature. Returns True if valid. Uses secp256k1 if available."""
 579 |     try:
 580 |         import hashlib
 581 |         pubkey_hex = (pubkey_hex or "").strip()
 582 |         sig_hex = (sig_hex or "").strip()
 583 |         if len(pubkey_hex) != 64 or len(sig_hex) != 128:
 584 |             return False
 585 |         try:
 586 |             from secp256k1 import PublicKey
 587 |             pk = PublicKey(bytes.fromhex(pubkey_hex), raw=True)
 588 |             msg_hash = hashlib.sha256(message.encode("utf-8")).digest()
 589 |             sig_bytes = bytes.fromhex(sig_hex)
 590 |             return pk.verify(sig_bytes, msg_hash)
 591 |         except ImportError:
 592 |             pass
 593 |         # Optional: ecdda / nostr package
 594 |         return False
 595 |     except Exception as e:
 596 |         logger.warning("nostr verify failed: %s", e)
 597 |         return False
 598 | 
 599 | 
 600 | def process_claim(pubkey, signature, signed_message, lightning_address):
 601 |     """
 602 |     Verify Nostr identity, check balance and rate limit, create ClaimPayout, send via Lightning.
 603 |     Returns {success, amount_sats, payment_hash, error}.
 604 |     """
 605 |     try:
 606 |         db = _db()
 607 |         models = _models()
 608 |         pubkey = (pubkey or "").strip()
 609 |         if not pubkey:
 610 |             return {"success": False, "error": "Missing pubkey"}
 611 |         creator = get_creator_by_pubkey(pubkey)
 612 |         if not creator:
 613 |             return {"success": False, "error": "No account linked to this Nostr key. Register or link your pubkey first."}
 614 |         if not can_claim_again(pubkey):
 615 |             return {"success": False, "error": "Rate limit: one claim per 24 hours. Try again later."}
 616 |         balance = get_claimable_balance(creator.id)
 617 |         if balance <= 0:
 618 |             return {"success": False, "error": "No sats available to claim."}
 619 |         lightning_address = (lightning_address or (creator.lightning_address or "") or "").strip()
 620 |         if not lightning_address or "@" not in lightning_address:
 621 |             return {"success": False, "error": "Valid Lightning Address required (e.g. you@getalby.com)."}
 622 |         import os
 623 |         if signature and signed_message and not os.environ.get("ALLOW_CLAIM_WITHOUT_NOSTR_VERIFY"):
 624 |             if not _verify_nostr_signature(pubkey, signed_message, signature):
 625 |                 return {"success": False, "error": "Invalid Nostr signature. Prove you own this key."}
 626 |         amount = min(balance, 10_000_000)  # 10M sats max per claim
 627 |         payout = models.ClaimPayout(
 628 |             creator_id=creator.id,
 629 |             amount_sats=amount,
 630 |             lightning_address=lightning_address,
 631 |             claimed_by_pubkey=pubkey,
 632 |             status="pending",
 633 |         )
 634 |         db.session.add(payout)
 635 |         db.session.flush()
 636 |         payment_hash, pay_error = _pay_lightning(amount, lightning_address)
 637 |         if pay_error:
 638 |             payout.status = "failed"
 639 |             payout.error_message = pay_error[:500]
 640 |             db.session.commit()
 641 |             return {"success": False, "error": pay_error}
 642 |         payout.status = "sent"
 643 |         payout.payment_hash = payment_hash or ""
 644 |         payout.settled_at = datetime.utcnow()
 645 |         db.session.commit()
 646 |         return {"success": True, "amount_sats": amount, "payment_hash": payment_hash}
 647 |     except Exception as e:
 648 |         logger.exception("process_claim failed: %s", e)
 649 |         try:
 650 |             _db().session.rollback()
 651 |         except Exception:
 652 |             pass
 653 |         return {"success": False, "error": "Claim failed. Please try again."}
 654 | 
 655 | 
 656 | def _pay_lightning(amount_sats, lightning_address):
 657 |     """Send sats to Lightning Address. Returns (payment_hash, None) or (None, error_string)."""
 658 |     import os
 659 |     url = os.environ.get("LNBITS_URL") or os.environ.get("LNURL_PAY_URL")
 660 |     key = os.environ.get("LNBITS_ADMIN_KEY") or os.environ.get("LNBITS_API_KEY")
 661 |     if not url or not key:
 662 |         return None, "Lightning payout not configured. Set LNBITS_URL and LNBITS_ADMIN_KEY."
 663 |     try:
 664 |         import requests
 665 |         # LNbits pay to Lightning Address: POST /api/v1/payments
 666 |         # body: amount in sats, lnaddr or bolt11
 667 |         r = requests.post(
 668 |             f"{url.rstrip('/')}/api/v1/payments",
 669 |             headers={"X-Api-Key": key, "Content-Type": "application/json"},
 670 |             json={"amount": amount_sats, "lnaddr": lightning_address},
 671 |             timeout=30,
 672 |         )
 673 |         if r.status_code != 200:
 674 |             return None, r.text or f"HTTP {r.status_code}"
 675 |         data = r.json()
 676 |         return data.get("payment_hash") or data.get("checking_id") or "", None
 677 |     except Exception as e:
 678 |         logger.exception("_pay_lightning failed")
 679 |         return None, str(e)
 680 | 
 681 | 
 682 | class ValueStreamService:
 683 |     """Namespace for value stream methods (used as value_stream_service in routes)."""
 684 |     get_value_stream = staticmethod(get_value_stream)
 685 |     get_top_curators = staticmethod(get_top_curators)
 686 |     get_value_stream_enhanced = staticmethod(get_value_stream_enhanced)
 687 |     submit_content = staticmethod(submit_content)
 688 |     process_zap = staticmethod(process_zap)
 689 |     post_zap_comment = staticmethod(post_zap_comment)
 690 |     register_creator = staticmethod(register_creator)
 691 |     get_claimable_balance = staticmethod(get_claimable_balance)
 692 |     get_creator_by_pubkey = staticmethod(get_creator_by_pubkey)
 693 |     can_claim_again = staticmethod(can_claim_again)
 694 |     process_claim = staticmethod(process_claim)
 695 | 
 696 | 
 697 | value_stream_service = ValueStreamService()
 698 | 
```

---

## YOUR REVIEW TASK — VALUE STREAM PRE-BUILD AUDIT (5 CRITICAL QUESTIONS)

VALUE STREAM is a Proof of Value social content curation platform powered by Bitcoin Lightning sats.
The ethos: opt out of Proof of Waste engagement farming. Reclaim your attention.
Value each other's ideas like we value our limited time on this planet.
No algorithmic manipulation. No infinite scroll dopamine.
Content rises by economic signal — sats zapped, not likes clicked.

### Q1 — MVP CRITICAL FEATURES
What are the 3 most critical features needed for an MVP that demonstrates this vision
compellingly to a Bitcoin maximalist seeing it for the first time?

### Q2 — CURRENT UI COMMUNICATION
What does the current UI communicate and what should it communicate instead?
The page currently shows a URL submission form and a leaderboard but has no content.

### Q3 — EMPTY STATE DESIGN
How do we make an empty state feel like an invitation rather than abandonment?

### Q4 — DESIGN COMPETITION
Gemini designs the hero section that communicates the anti-algorithmic ethos without being preachy.
GPT-4o designs the content card that makes sats-based curation feel natural.
Grok designs the flow of discovering and zapping content.
Which wins for the Bitcoin audience? Propose your best design.

### Q5 — BRAND ALIGNMENT
Does the current implementation match the Protocol Pulse brand (dark, red accent, JetBrains Mono)?
What specific visual changes are needed?

### RESPONSE FORMAT
For each question: DETAILED ANALYSIS + SPECIFIC RECOMMENDATION
### FINAL VERDICT: Top 3 changes needed + Overall assessment

