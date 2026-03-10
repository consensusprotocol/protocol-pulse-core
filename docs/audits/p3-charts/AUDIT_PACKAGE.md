# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: p3-charts
# Branch: feature/p3-charts
# Generated: 2026-03-09 14:31 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
### LAW 1: WebSocket for price — not polling
Use mempool.space WebSocket for real-time block and stats data:
  wss://mempool.space/api/v1/ws
  Send: {"action": "want", "data": ["stats", "blocks"]}
  Receive: live stats including mempool size, fee rates, block time
For price: /api/btc-price proxy (already exists on server, 30s cache)
JS auto-reconnects on disconnect with exponential backoff.

### LAW 2: All charts use Canvas API — no Chart.js, no Recharts, no D3
Pure vanilla JS Canvas. This ensures maximum performance and zero dependency bloat.
Implement ChartEngine class with methods: drawLine, drawArea, drawBar, drawPie,
drawAxis, drawGrid, drawCrosshair, drawTooltip. Reusable across all charts.

### LAW 3: Every chart is shareable as PNG
canvas.toDataURL("image/png") → download link on each chart
"Share Chart" button per chart: native Web Share API (falls back to copy link)

### LAW 4: Server proxies all external APIs — never direct browser calls
/api/charts/price-history?days=N     → proxies CoinGecko, cache 5min
/api/charts/mempool-data             → proxies mempool.space, cache 60s
/api/charts/hashrate-history         → proxies mempool.space, cache 5min
/api/charts/pool-distribution        → proxies mempool.space, cache 1hr
/api/charts/fee-history              → proxies mempool.space, cache 30min



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

### File: PHASE0_ADDENDUM.md (94 lines)
```
   1 | # PHASE 0 ADDENDUM — P3 CHARTS
   2 | # Generated: 2026-03-09
   3 | # Status: GOSPEL supplement — all items below are incorporated into build
   4 | 
   5 | ---
   6 | 
   7 | ## TOP PHASE 0 ADDITIONS TO IMPLEMENT
   8 | 
   9 | ### 1. AI Chart Interpreter — "Explain This Chart" Button
  10 | **Priority: P0 (Category-Defining)**
  11 | - Every chart card gets an "INTERPRET" button
  12 | - Calls `/api/charts/ai-explain` with chart metadata + current data snapshot
  13 | - Uses Anthropic Claude API (ANTHROPIC_API_KEY from env)
  14 | - Returns 2-3 sentence interpretation in professional analyst voice
  15 | - Loading state: "Analyzing market structure..."
  16 | - Displayed in glassmorphism overlay beneath the chart
  17 | - **Implementation**: Backend streams chart context to Claude claude-haiku-4-5-20251001. Frontend shows typewriter reveal.
  18 | 
  19 | ### 2. Advanced Bitcoin Valuation Metrics Panel
  20 | **Priority: P0 (Market Leadership)**
  21 | - Mayer Multiple: real-time calculation (price / 200d MA). Display with zones: < 1.0 (undervalued), 1.0–2.4 (fair), > 2.4 (overbought)
  22 | - Stock-to-Flow model price: calculate from current supply + block schedule. Display as overlay on price chart.
  23 | - Puell Multiple: approximated from daily issuance value vs 365d MA (proxy from hashrate data)
  24 | - NUPL approximation: Market Cap - Realized Cap estimate / Market Cap. Display as colored sentiment gauge.
  25 | - **Implementation**: Pure JS math on price history data. No external API needed for Mayer/S2F/NUPL estimates.
  26 | 
  27 | ### 3. Real-Time Architecture Improvements
  28 | **Priority: P0 (Foundation)**
  29 | - mempool.space WebSocket with exponential backoff reconnect (as per GOSPEL)
  30 | - Heartbeat ping every 30s to keep connection alive
  31 | - Connection status indicator in stat bar (green dot = live, red = polling fallback)
  32 | - **Implementation**: Single WebSocket manager class, wraps all WS subscriptions.
  33 | 
  34 | ### 4. Lightning Network Metrics Section
  35 | **Priority: P1**
  36 | - Total capacity (BTC + USD), node count, channel count from mempool.space API
  37 | - 30-day capacity trend mini-chart (Canvas bar chart)
  38 | - Source: `/api/charts/lightning` proxy → `https://mempool.space/api/v1/lightning/statistics/latest`
  39 | - **Implementation**: New section after Supply Analysis
  40 | 
  41 | ### 5. Difficulty Adjustment Prediction
  42 | **Priority: P1**
  43 | - Calculate next difficulty adjustment from current block height + epoch progress
  44 | - Show: blocks remaining, estimated date, expected % change (from current hashrate trend)
  45 | - Visual: progress ring (Canvas arc) + prediction badge
  46 | - **Implementation**: Pure math from block height + mempool data (no external API)
  47 | 
  48 | ### 6. Fear & Greed Index Display
  49 | **Priority: P1**
  50 | - Fetch from `https://api.alternative.me/fng/?limit=7` (free, no key)
  51 | - 7-day trend sparkline + current value gauge
  52 | - Proxy via `/api/charts/fear-greed`, cache 1hr
  53 | - **Implementation**: Semicircle gauge Canvas component
  54 | 
  55 | ### 7. Export/Sharing with Protocol Pulse Branding
  56 | **Priority: P1 (from GOSPEL LAW 3)**
  57 | - canvas.toDataURL("image/png") download per chart
  58 | - Watermark "PROTOCOLPULSE.IO" in corner before download
  59 | - Web Share API with fallback to clipboard copy
  60 | - **Implementation**: ChartEngine.exportPNG(chartId, title) method
  61 | 
  62 | ### 8. Rate Limiting on Price Alert Endpoint
  63 | **Priority: P1 (Security)**
  64 | - Max 3 alerts per email address per day
  65 | - Max 10 active alerts per email total
  66 | - Input validation: valid email format, price must be numeric 1000–10,000,000
  67 | - **Implementation**: DB query count before insert
  68 | 
  69 | ### 9. Keyboard Accessibility + Command Bar
  70 | **Priority: P2**
  71 | - Cmd+K opens quick-jump to any chart section
  72 | - Tab navigation through all interactive elements
  73 | - ARIA labels on all charts (role="img", aria-label describing the chart)
  74 | - **Implementation**: Global keydown handler, smooth scrollTo sections
  75 | 
  76 | ### 10. Hashrate Ribbon Indicator
  77 | **Priority: P2**
  78 | - Show 30d vs 60d SMA of hashrate — ribbon color flips bullish/bearish
  79 | - Overlaid on hashrate chart as shaded band
  80 | - **Implementation**: Calculate from hashrate history array in JS
  81 | 
  82 | ---
  83 | 
  84 | ## DESIGN DECISIONS (Best Calls)
  85 | 
  86 | - **No Glassnode/CoinMetrics API**: Free tiers too limited and require keys. Use pure-JS calculations from price/hashrate history instead for MVRV/NUPL approximations. Label as "estimated" where not exact.
  87 | - **No Redis/Node.js**: Keep single-process Flask. Cache with functools.lru_cache + TTL wrapper.
  88 | - **No TensorFlow.js**: Predictive analytics kept to simple trend extrapolation (linear regression in pure JS) — no ML frameworks.
  89 | - **Fear & Greed**: alternative.me API is genuinely free, no auth, perfect fit.
  90 | - **Lightning metrics**: mempool.space `/lightning/statistics/latest` is free and comprehensive.
  91 | 
  92 | ---
  93 | *End PHASE0_ADDENDUM.md — All items above incorporated into the build.*
  94 | 
```

### File: core/models.py (950 lines)
```
   1 | from datetime import datetime, timedelta
   2 | from flask_login import UserMixin
   3 | from werkzeug.security import generate_password_hash, check_password_hash
   4 | from app import db  # This stays here; we will fix the 'loop' in app.py
   5 | 
   6 | # =====================================
   7 | # USER & OPERATIVE MODELS
   8 | # =====================================
   9 | 
  10 | class User(UserMixin, db.Model):
  11 |     id = db.Column(db.Integer, primary_key=True)
  12 |     username = db.Column(db.String(80), unique=True, nullable=False)
  13 |     email = db.Column(db.String(120), unique=True, nullable=False)
  14 |     password_hash = db.Column(db.String(256))
  15 |     is_admin = db.Column(db.Boolean, default=False)
  16 |     newsletter_subscribed = db.Column(db.Boolean, default=False)
  17 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
  18 |     
  19 |     operative_rank = db.Column(db.Integer, default=1)
  20 |     drill_completions = db.Column(db.Integer, default=0)
  21 |     brief_clicks = db.Column(db.Integer, default=0)
  22 |     operative_slug = db.Column(db.String(100), unique=True)
  23 |     crm_synced_at = db.Column(db.DateTime)
  24 |     last_drill_at = db.Column(db.DateTime)
  25 |     last_brief_at = db.Column(db.DateTime)
  26 |     
  27 |     # Premium subscription (free | operator | commander | sovereign)
  28 |     subscription_tier = db.Column(db.String(30), default='free')
  29 |     stripe_customer_id = db.Column(db.String(120))
  30 |     stripe_subscription_id = db.Column(db.String(120))
  31 |     subscription_expires_at = db.Column(db.DateTime)
  32 |     # Commander+: opt-in to email alerts for mega whales (≥1000 BTC)
  33 |     mega_whale_email_alerts = db.Column(db.Boolean, default=False)
  34 |     
  35 |     # --- Auth Methods ---
  36 |     def set_password(self, password):
  37 |         self.password_hash = generate_password_hash(password)
  38 | 
  39 |     def check_password(self, password):
  40 |         return check_password_hash(self.password_hash, password)
  41 | 
  42 |     # --- Operative Logic ---
  43 |     def get_rank_name(self):
  44 |         if self.operative_rank >= 3:
  45 |             return 'SOVEREIGN ELITE'
  46 |         elif self.operative_rank >= 2:
  47 |             return 'OPERATIVE'
  48 |         return 'RECRUIT'
  49 |     
  50 |     def check_rank_progression(self):
  51 |         if self.drill_completions >= 5 and self.brief_clicks >= 10:
  52 |             self.operative_rank = 3
  53 |         elif self.drill_completions >= 1:
  54 |             self.operative_rank = 2
  55 |         else:
  56 |             self.operative_rank = 1
  57 |     
  58 |     def generate_operative_slug(self):
  59 |         import hashlib
  60 |         import time
  61 |         if not self.operative_slug:
  62 |             base = self.username.lower().replace(' ', '-')[:20]
  63 |             unique_hash = hashlib.md5(f"{self.email}{time.time()}".encode()).hexdigest()[:6]
  64 |             self.operative_slug = f"{base}-{unique_hash}"
  65 |         return self.operative_slug
  66 |     
  67 |     def can_increment_drill(self):
  68 |         if not self.last_drill_at:
  69 |             return True
  70 |         cooldown = datetime.utcnow() - self.last_drill_at
  71 |         return cooldown.total_seconds() >= 300
  72 |     
  73 |     def can_increment_brief(self):
  74 |         if not self.last_brief_at:
  75 |             return True
  76 |         cooldown = datetime.utcnow() - self.last_brief_at
  77 |         return cooldown.total_seconds() >= 60
  78 |     
  79 |     def has_premium(self):
  80 |         """True if user has any paid tier (operator, commander, sovereign)."""
  81 |         tier = getattr(self, 'subscription_tier', None)
  82 |         return tier and tier != 'free'
  83 | 
  84 |     def has_commander_tier(self):
  85 |         """True if user has $99/mo Commander (or higher) tier."""
  86 |         tier = getattr(self, 'subscription_tier', None)
  87 |         return tier in ('commander', 'sovereign')
  88 | 
  89 | # =====================================
  90 | # CONTENT & INTELLIGENCE MODELS
  91 | # =====================================
  92 | 
  93 | class Article(db.Model):
  94 |     __tablename__ = "articles"
  95 |     id = db.Column(db.Integer, primary_key=True)
  96 |     title = db.Column(db.String(200), nullable=False)
  97 |     content = db.Column(db.Text, nullable=False)
  98 |     summary = db.Column(db.Text)
  99 |     author = db.Column(db.String(100), default="Protocol Pulse AI")
 100 |     category = db.Column(db.String(50), default="Web3")
 101 |     tags = db.Column(db.String(500))
 102 |     source_url = db.Column(db.String(500))
 103 |     source_type = db.Column(db.String(50))
 104 |     featured = db.Column(db.Boolean, default=False)
 105 |     published = db.Column(db.Boolean, default=False)
 106 |     # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
 107 |     premium_tier = db.Column(db.String(30), default=None)
 108 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 109 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 110 |     seo_title = db.Column(db.String(200))
 111 |     seo_description = db.Column(db.String(300))
 112 |     substack_url = db.Column(db.String(500))
 113 |     header_image_url = db.Column(db.String(500))
 114 |     screenshot_url = db.Column(db.String(500))
 115 |     video_url = db.Column(db.String(500))
 116 | 
 117 | class Podcast(db.Model):
 118 |     id = db.Column(db.Integer, primary_key=True)
 119 |     title = db.Column(db.String(200), nullable=False)
 120 |     description = db.Column(db.Text)
 121 |     host = db.Column(db.String(100))
 122 |     episode_number = db.Column(db.Integer)
 123 |     duration = db.Column(db.String(20))
 124 |     audio_url = db.Column(db.String(500))
 125 |     cover_image_url = db.Column(db.String(500))
 126 |     published_date = db.Column(db.DateTime, default=datetime.utcnow)
 127 |     featured = db.Column(db.Boolean, default=False)
 128 |     category = db.Column(db.String(50), default="Web3")
 129 |     rss_source = db.Column(db.String(100))
 130 | 
 131 | class ContentPrompt(db.Model):
 132 |     id = db.Column(db.Integer, primary_key=True)
 133 |     name = db.Column(db.String(100), nullable=False)
 134 |     prompt_text = db.Column(db.Text, nullable=False)
 135 |     category = db.Column(db.String(50))
 136 |     active = db.Column(db.Boolean, default=True)
 137 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 138 | 
 139 | class Advertisement(db.Model):
 140 |     id = db.Column(db.Integer, primary_key=True)
 141 |     name = db.Column(db.String(150), nullable=False)
 142 |     image_url = db.Column(db.String(300), nullable=False)
 143 |     target_url = db.Column(db.String(300), nullable=False)
 144 |     is_active = db.Column(db.Boolean, default=False)
 145 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 146 | 
 147 | 
 148 | class AffiliateProduct(db.Model):
 149 |     """Products we have affiliate links for (Amazon, Trezor, etc.) — used in product-highlight articles."""
 150 |     __tablename__ = 'affiliate_product'
 151 |     id = db.Column(db.Integer, primary_key=True)
 152 |     name = db.Column(db.String(200), nullable=False)
 153 |     product_type = db.Column(db.String(50), nullable=False)  # amazon_book, trezor, cold_wallet, seed_plate, miner, etc.
 154 |     product_id = db.Column(db.String(100))  # ASIN, offer_id, etc.
 155 |     affiliate_url = db.Column(db.String(500))
 156 |     category = db.Column(db.String(80))  # cold_wallet, seed_plate, bitaxe_miner, book, etc.
 157 |     short_description = db.Column(db.String(500))
 158 |     active = db.Column(db.Boolean, default=True)
 159 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 160 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 161 | 
 162 | 
 163 | class AffiliateProductClick(db.Model):
 164 |     """Track affiliate product link clicks for revenue analytics (Smart Analytics)."""
 165 |     __tablename__ = 'affiliate_product_click'
 166 |     id = db.Column(db.Integer, primary_key=True)
 167 |     product_id = db.Column(db.Integer, db.ForeignKey('affiliate_product.id'), nullable=True)
 168 |     link_type = db.Column(db.String(50))  # amazon, trezor, etc.
 169 |     page_path = db.Column(db.String(500))
 170 |     session_id = db.Column(db.String(64))
 171 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 172 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 173 | 
 174 | 
 175 | # =====================================
 176 | # AUTOMATION & LOGISTICS
 177 | # =====================================
 178 | 
 179 | class AutomationRun(db.Model):
 180 |     id = db.Column(db.Integer, primary_key=True)
 181 |     task_name = db.Column(db.String(100), nullable=False)
 182 |     started_at = db.Column(db.DateTime, nullable=False)
 183 |     finished_at = db.Column(db.DateTime)
 184 |     status = db.Column(db.String(20))
 185 |     error = db.Column(db.String(500))
 186 | 
 187 | class LaunchSequence(db.Model):
 188 |     id = db.Column(db.Integer, primary_key=True)
 189 |     content_id = db.Column(db.Integer)
 190 |     content_type = db.Column(db.String(50))
 191 |     primary_post_copy = db.Column(db.Text)
 192 |     thread_replies = db.Column(db.Text)
 193 |     quote_variants = db.Column(db.Text)
 194 |     reply_drafts = db.Column(db.Text)
 195 |     hashtags = db.Column(db.String(500))
 196 |     posting_time = db.Column(db.Time)
 197 |     velocity_prediction = db.Column(db.Float)
 198 |     first_reply_link = db.Column(db.String(500))
 199 |     call_to_action = db.Column(db.String(300))
 200 |     status = db.Column(db.String(50), default='draft')
 201 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 202 |     approved_at = db.Column(db.DateTime)
 203 |     published_at = db.Column(db.DateTime)
 204 |     tweet_id = db.Column(db.String(100))
 205 |     actual_velocity_score = db.Column(db.Float)
 206 |     replies_first_5min = db.Column(db.Integer, default=0)
 207 |     total_engagement = db.Column(db.Integer, default=0)
 208 |     reached_for_you = db.Column(db.Boolean, default=False)
 209 |     dispatch_window = db.Column(db.String(20))
 210 |     dispatch_timezone = db.Column(db.String(50), default='America/New_York')
 211 |     persona_debate = db.Column(db.Text)
 212 |     is_autonomous = db.Column(db.Boolean, default=False)
 213 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 214 |     ground_truth = db.Column(db.Text)
 215 |     target_segment = db.Column(db.String(100))
 216 |     generated_by = db.Column(db.String(50))
 217 |     nostr_event_id = db.Column(db.String(100))
 218 |     x_tweet_id = db.Column(db.String(100))
 219 |     is_approved = db.Column(db.Boolean, default=False)
 220 |     is_posted = db.Column(db.Boolean, default=False)
 221 | 
 222 | class TargetAlert(db.Model):
 223 |     id = db.Column(db.Integer, primary_key=True)
 224 |     trigger_type = db.Column(db.String(50))
 225 |     source_url = db.Column(db.String(500))
 226 |     source_account = db.Column(db.String(100))
 227 |     content_snippet = db.Column(db.Text)
 228 |     priority = db.Column(db.Integer, default=2)
 229 |     strategy_suggested = db.Column(db.String(100))
 230 |     draft_replies = db.Column(db.Text)
 231 |     status = db.Column(db.String(50), default='pending')
 232 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 233 |     responded_at = db.Column(db.DateTime)
 234 | 
 235 | class NostrEvent(db.Model):
 236 |     id = db.Column(db.Integer, primary_key=True)
 237 |     event_id = db.Column(db.String(100))
 238 |     content_type = db.Column(db.String(50))
 239 |     content_id = db.Column(db.Integer)
 240 |     relays_success = db.Column(db.Text)
 241 |     relays_failed = db.Column(db.Text)
 242 |     zaps_received = db.Column(db.Integer, default=0)
 243 |     zaps_amount_sats = db.Column(db.Integer, default=0)
 244 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 245 | 
 246 | class ReplySquadMember(db.Model):
 247 |     id = db.Column(db.Integer, primary_key=True)
 248 |     handle = db.Column(db.String(100), nullable=False)
 249 |     display_name = db.Column(db.String(150))
 250 |     category = db.Column(db.String(100))
 251 |     priority = db.Column(db.Integer, default=2)
 252 |     reciprocal_engagements = db.Column(db.Integer, default=0)
 253 |     last_engagement = db.Column(db.DateTime)
 254 |     notes = db.Column(db.Text)
 255 |     active = db.Column(db.Boolean, default=True)
 256 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 257 | 
 258 | # =====================================
 259 | # BITCOIN NETWORK & DONATIONS
 260 | # =====================================
 261 | 
 262 | class WhaleTransaction(db.Model):
 263 |     id = db.Column(db.Integer, primary_key=True)
 264 |     txid = db.Column(db.String(100), unique=True, nullable=False)
 265 |     btc_amount = db.Column(db.Float, nullable=False)
 266 |     usd_value = db.Column(db.Float)
 267 |     fee_sats = db.Column(db.Integer)
 268 |     block_height = db.Column(db.Integer)
 269 |     detected_at = db.Column(db.DateTime, default=datetime.utcnow)
 270 |     is_mega = db.Column(db.Boolean, default=False)
 271 | 
 272 | 
 273 | class ContactSubmission(db.Model):
 274 |     """Contact form submissions (stored for admin; optional email notification)."""
 275 |     id = db.Column(db.Integer, primary_key=True)
 276 |     name = db.Column(db.String(200), nullable=False)
 277 |     email = db.Column(db.String(200), nullable=False)
 278 |     subject = db.Column(db.String(100), nullable=False)
 279 |     message = db.Column(db.Text, nullable=False)
 280 |     ip_address = db.Column(db.String(64))
 281 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 282 |     read = db.Column(db.Boolean, default=False)
 283 | 
 284 | 
 285 | class PremiumAsk(db.Model):
 286 |     """Sovereign Elite monthly ask: one research/question per month, answered by team."""
 287 |     id = db.Column(db.Integer, primary_key=True)
 288 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 289 |     question_text = db.Column(db.Text, nullable=False)
 290 |     status = db.Column(db.String(20), default='pending')  # pending | answered
 291 |     answer_text = db.Column(db.Text)
 292 |     answer_url = db.Column(db.String(500))  # optional link to brief or doc
 293 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 294 |     answered_at = db.Column(db.DateTime)
 295 |     user = db.relationship('User', backref=db.backref('premium_asks', lazy='dynamic'))
 296 | 
 297 | 
 298 | class BitcoinDonation(db.Model):
 299 |     id = db.Column(db.Integer, primary_key=True)
 300 |     payment_id = db.Column(db.String(100))
 301 |     amount_sats = db.Column(db.Integer)
 302 |     amount_usd = db.Column(db.Float)
 303 |     donor_email = db.Column(db.String(200))
 304 |     donor_name = db.Column(db.String(200))
 305 |     message = db.Column(db.Text)
 306 |     status = db.Column(db.String(50), default='pending')
 307 |     payment_method = db.Column(db.String(50))
 308 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 309 |     confirmed_at = db.Column(db.DateTime)
 310 | 
 311 | # =====================================
 312 | # ANALYTICS & PERFORMANCE
 313 | # =====================================
 314 | 
 315 | class EngagementEvent(db.Model):
 316 |     id = db.Column(db.Integer, primary_key=True)
 317 |     event_type = db.Column(db.String(50), nullable=False)
 318 |     content_type = db.Column(db.String(50))
 319 |     content_id = db.Column(db.Integer)
 320 |     source_platform = db.Column(db.String(50))
 321 |     source_url = db.Column(db.String(500))
 322 |     persona = db.Column(db.String(50))
 323 |     strategy = db.Column(db.String(100))
 324 |     minutes_after_post = db.Column(db.Float)
 325 |     is_30min_window = db.Column(db.Boolean, default=False)
 326 |     grok_score_contribution = db.Column(db.Integer, default=0)
 327 |     user_agent = db.Column(db.String(300))
 328 |     referrer = db.Column(db.String(500))
 329 |     ip_hash = db.Column(db.String(64))
 330 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 331 | 
 332 | class ContentPerformance(db.Model):
 333 |     id = db.Column(db.Integer, primary_key=True)
 334 |     content_type = db.Column(db.String(50), nullable=False)
 335 |     content_id = db.Column(db.Integer, nullable=False)
 336 |     content_title = db.Column(db.String(300))
 337 |     total_views = db.Column(db.Integer, default=0)
 338 |     total_clicks = db.Column(db.Integer, default=0)
 339 |     total_replies = db.Column(db.Integer, default=0)
 340 |     total_retweets = db.Column(db.Integer, default=0)
 341 |     total_quotes = db.Column(db.Integer, default=0)
 342 |     total_likes = db.Column(db.Integer, default=0)
 343 |     profile_visits = db.Column(db.Integer, default=0)
 344 |     replies_0_5min = db.Column(db.Integer, default=0)
 345 |     replies_5_15min = db.Column(db.Integer, default=0)
 346 |     replies_15_30min = db.Column(db.Integer, default=0)
 347 |     replies_30plus_min = db.Column(db.Integer, default=0)
 348 |     velocity_score = db.Column(db.Float, default=0)
 349 |     grok_score_total = db.Column(db.Integer, default=0)
 350 |     reached_for_you = db.Column(db.Boolean, default=False)
 351 |     peak_velocity_minute = db.Column(db.Integer)
 352 |     alex_engagements = db.Column(db.Integer, default=0)
 353 |     sarah_engagements = db.Column(db.Integer, default=0)
 354 |     best_performing_strategy = db.Column(db.String(100))
 355 |     best_performing_time = db.Column(db.String(20))
 356 |     published_at = db.Column(db.DateTime)
 357 |     last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 358 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 359 | 
 360 | class AnalyticsSummary(db.Model):
 361 |     id = db.Column(db.Integer, primary_key=True)
 362 |     period_type = db.Column(db.String(20), nullable=False)
 363 |     period_start = db.Column(db.Date, nullable=False)
 364 |     period_end = db.Column(db.Date, nullable=False)
 365 |     total_posts = db.Column(db.Integer, default=0)
 366 |     total_impressions = db.Column(db.Integer, default=0)
 367 |     total_engagements = db.Column(db.Integer, default=0)
 368 |     total_profile_visits = db.Column(db.Integer, default=0)
 369 |     total_followers_gained = db.Column(db.Integer, default=0)
 370 |     avg_velocity_score = db.Column(db.Float, default=0)
 371 |     avg_grok_score = db.Column(db.Float, default=0)
 372 |     for_you_reach_rate = db.Column(db.Float, default=0)
 373 |     top_performing_content_id = db.Column(db.Integer)
 374 |     top_performing_content_type = db.Column(db.String(50))
 375 |     top_performing_strategy = db.Column(db.String(100))
 376 |     alex_total_score = db.Column(db.Integer, default=0)
 377 |     sarah_total_score = db.Column(db.Integer, default=0)
 378 |     persona_winner = db.Column(db.String(50))
 379 |     best_posting_hour = db.Column(db.Integer)
 380 |     best_posting_day = db.Column(db.Integer)
 381 |     sponsor_value_estimate = db.Column(db.Float)
 382 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 383 | 
 384 | class Sponsor(db.Model):
 385 |     id = db.Column(db.Integer, primary_key=True)
 386 |     name = db.Column(db.String(200), nullable=False)
 387 |     company = db.Column(db.String(200))
 388 |     email = db.Column(db.String(200))
 389 |     website_url = db.Column(db.String(500))
 390 |     logo_url = db.Column(db.String(500))
 391 |     tier = db.Column(db.String(50), default='standard')
 392 |     status = db.Column(db.String(50), default='pending')
 393 |     impressions = db.Column(db.Integer, default=0)
 394 |     clicks = db.Column(db.Integer, default=0)
 395 |     ctr = db.Column(db.Float, default=0)
 396 |     budget_sats = db.Column(db.Integer, default=0)
 397 |     spent_sats = db.Column(db.Integer, default=0)
 398 |     cpm_sats = db.Column(db.Integer, default=1000)
 399 |     target_categories = db.Column(db.String(500))
 400 |     target_personas = db.Column(db.String(200))
 401 |     ad_copy = db.Column(db.Text)
 402 |     cta_text = db.Column(db.String(100))
 403 |     cta_url = db.Column(db.String(500))
 404 |     start_date = db.Column(db.DateTime)
 405 |     end_date = db.Column(db.DateTime)
 406 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 407 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 408 | 
 409 | class CreditAccount(db.Model):
 410 |     id = db.Column(db.Integer, primary_key=True)
 411 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 412 |     signal_points = db.Column(db.Integer, default=0)
 413 |     lifetime_points = db.Column(db.Integer, default=0)
 414 |     tier = db.Column(db.String(50), default='recruit')
 415 |     tier_progress = db.Column(db.Float, default=0)
 416 |     articles_read = db.Column(db.Integer, default=0)
 417 |     podcasts_listened = db.Column(db.Integer, default=0)
 418 |     quizzes_completed = db.Column(db.Integer, default=0)
 419 |     referrals_made = db.Column(db.Integer, default=0)
 420 |     streak_days = db.Column(db.Integer, default=0)
 421 |     longest_streak = db.Column(db.Integer, default=0)
 422 |     last_activity = db.Column(db.DateTime)
 423 |     badges = db.Column(db.Text)
 424 |     achievements = db.Column(db.Text)
 425 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 426 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 427 |     user = db.relationship('User', backref=db.backref('credit_account', uselist=False))
 428 | 
 429 | class PredictionOracle(db.Model):
 430 |     id = db.Column(db.Integer, primary_key=True)
 431 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 432 |     prediction_type = db.Column(db.String(50))
 433 |     prediction_value = db.Column(db.Float)
 434 |     target_date = db.Column(db.DateTime)
 435 |     actual_value = db.Column(db.Float)
 436 |     accuracy_score = db.Column(db.Float)
 437 |     status = db.Column(db.String(50), default='pending')
 438 |     is_correct = db.Column(db.Boolean)
 439 |     signal_points_wagered = db.Column(db.Integer, default=0)
 440 |     signal_points_won = db.Column(db.Integer, default=0)
 441 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 442 |     resolved_at = db.Column(db.DateTime)
 443 | 
 444 | class UserSegment(db.Model):
 445 |     id = db.Column(db.Integer, primary_key=True)
 446 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 447 |     segment_type = db.Column(db.String(50), default='general')
 448 |     confidence = db.Column(db.Float, default=0.5)
 449 |     hashrate_interest = db.Column(db.Float, default=0)
 450 |     macro_interest = db.Column(db.Float, default=0)
 451 |     technical_interest = db.Column(db.Float, default=0)
 452 |     trading_interest = db.Column(db.Float, default=0)
 453 |     privacy_interest = db.Column(db.Float, default=0)
 454 |     articles_viewed = db.Column(db.Integer, default=0)
 455 |     avg_read_time = db.Column(db.Float, default=0)
 456 |     preferred_categories = db.Column(db.Text)
 457 |     last_classification = db.Column(db.DateTime, default=datetime.utcnow)
 458 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 459 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 460 |     user = db.relationship('User', backref=db.backref('segment', uselist=False))
 461 | 
 462 | class AffiliatePartner(db.Model):
 463 |     __tablename__ = 'affiliate_partner'
 464 |     id = db.Column(db.Integer, primary_key=True)
 465 |     name = db.Column(db.String(100), unique=True, nullable=False)
 466 |     slug = db.Column(db.String(50), unique=True, nullable=False)
 467 |     category = db.Column(db.String(50))
 468 |     url = db.Column(db.String(500))
 469 |     benefit = db.Column(db.String(200))
 470 |     is_active = db.Column(db.Boolean, default=True)
 471 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 472 |     clicks = db.relationship('AffiliateClick', backref='partner', lazy='dynamic')
 473 | 
 474 | class AffiliateClick(db.Model):
 475 |     __tablename__ = 'affiliate_click'
 476 |     id = db.Column(db.Integer, primary_key=True)
 477 |     partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=False)
 478 |     source_page = db.Column(db.String(500))
 479 |     ip_hash = db.Column(db.String(64))
 480 |     user_agent = db.Column(db.String(500))
 481 |     clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
 482 | 
 483 | class FeedItem(db.Model):
 484 |     __tablename__ = 'feed_item'
 485 |     id = db.Column(db.Integer, primary_key=True)
 486 |     source = db.Column(db.String(100), nullable=False)
 487 |     source_type = db.Column(db.String(50), nullable=False)
 488 |     tier = db.Column(db.String(20))
 489 |     title = db.Column(db.String(500))
 490 |     url = db.Column(db.String(1000), unique=True)
 491 |     published_at = db.Column(db.DateTime)
 492 |     author = db.Column(db.String(100))
 493 |     summary = db.Column(db.Text)
 494 |     platform_icon = db.Column(db.String(50))
 495 |     raw_json = db.Column(db.Text)
 496 |     verified = db.Column(db.Boolean, default=False)
 497 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 498 | 
 499 | class SentimentSnapshot(db.Model):
 500 |     __tablename__ = 'sentiment_snapshot'
 501 |     id = db.Column(db.Integer, primary_key=True)
 502 |     score = db.Column(db.Float, default=50.0)
 503 |     state = db.Column(db.String(50), default='EQUILIBRIUM')
 504 |     state_label = db.Column(db.String(50), default='EQUILIBRIUM')
 505 |     state_color = db.Column(db.String(20), default='#ffffff')
 506 |     velocity = db.Column(db.Float, default=0.0)
 507 |     top_keywords = db.Column(db.Text)
 508 |     top_topics_json = db.Column(db.Text)
 509 |     sample_size = db.Column(db.Integer, default=0)
 510 |     verified_weight = db.Column(db.Integer, default=0)
 511 |     computed_at = db.Column(db.DateTime, default=datetime.utcnow)
 512 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 513 | 
 514 | class PulseEvent(db.Model):
 515 |     __tablename__ = 'pulse_event'
 516 |     id = db.Column(db.Integer, primary_key=True)
 517 |     event_type = db.Column(db.String(50), nullable=False)
 518 |     from_state = db.Column(db.String(50))
 519 |     to_state = db.Column(db.String(50))
 520 |     score = db.Column(db.Float)
 521 |     triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
 522 |     payload_json = db.Column(db.Text)
 523 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 524 | 
 525 | class AutoPostDraft(db.Model):
 526 |     __tablename__ = 'autopost_draft'
 527 |     id = db.Column(db.Integer, primary_key=True)
 528 |     platform = db.Column(db.String(30), nullable=False)
 529 |     status = db.Column(db.String(20), default='draft')
 530 |     body = db.Column(db.Text)
 531 |     reason = db.Column(db.String(200))
 532 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 533 |     approved_at = db.Column(db.DateTime)
 534 |     posted_at = db.Column(db.DateTime)
 535 | 
 536 | class DailyBrief(db.Model):
 537 |     __tablename__ = 'daily_brief'
 538 |     id = db.Column(db.Integer, primary_key=True)
 539 |     headline = db.Column(db.String(500))
 540 |     body = db.Column(db.Text)
 541 |     signals_json = db.Column(db.Text)
 542 |     status = db.Column(db.String(20), default='draft')
 543 |     published_at = db.Column(db.DateTime)
 544 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 545 | 
 546 | class PageView(db.Model):
 547 |     __tablename__ = 'page_view'
 548 |     id = db.Column(db.Integer, primary_key=True)
 549 |     page_path = db.Column(db.String(500), nullable=False)
 550 |     page_title = db.Column(db.String(300))
 551 |     page_category = db.Column(db.String(50))
 552 |     session_id = db.Column(db.String(64))
 553 |     ip_hash = db.Column(db.String(64))
 554 |     user_agent = db.Column(db.String(300))
 555 |     referrer = db.Column(db.String(500))
 556 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 557 |     time_on_page = db.Column(db.Integer, default=0)
 558 |     scroll_depth = db.Column(db.Integer, default=0)
 559 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 560 | 
 561 | class HotMoment(db.Model):
 562 |     __tablename__ = 'hot_moment'
 563 |     id = db.Column(db.Integer, primary_key=True)
 564 |     page_path = db.Column(db.String(500), nullable=False)
 565 |     page_title = db.Column(db.String(300))
 566 |     page_category = db.Column(db.String(50))
 567 |     views_in_window = db.Column(db.Integer, default=0)
 568 |     unique_visitors = db.Column(db.Integer, default=0)
 569 |     heat_score = db.Column(db.Float, default=0)
 570 |     is_peak = db.Column(db.Boolean, default=False)
 571 |     peak_detected_at = db.Column(db.DateTime)
 572 |     tweet_drafted = db.Column(db.Boolean, default=False)
 573 |     tweet_content = db.Column(db.Text)
 574 |     tweet_posted_at = db.Column(db.DateTime)
 575 |     window_start = db.Column(db.DateTime, nullable=False)
 576 |     window_end = db.Column(db.DateTime, nullable=False)
 577 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 578 | 
 579 | class ContentSuggestion(db.Model):
 580 |     __tablename__ = 'content_suggestion'
 581 |     id = db.Column(db.Integer, primary_key=True)
 582 |     suggestion_type = db.Column(db.String(50))
 583 |     title = db.Column(db.String(300))
 584 |     description = db.Column(db.Text)
 585 |     reasoning = db.Column(db.Text)
 586 |     based_on_page = db.Column(db.String(500))
 587 |     based_on_trend = db.Column(db.String(200))
 588 |     confidence_score = db.Column(db.Float, default=0)
 589 |     status = db.Column(db.String(20), default='pending')
 590 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 591 |     actioned_at = db.Column(db.DateTime)
 592 | 
 593 | class AutoTweet(db.Model):
 594 |     __tablename__ = 'auto_tweet'
 595 |     id = db.Column(db.Integer, primary_key=True)
 596 |     trigger_type = db.Column(db.String(50))
 597 |     trigger_page = db.Column(db.String(500))
 598 |     heat_score_at_trigger = db.Column(db.Float)
 599 |     tweet_content = db.Column(db.Text, nullable=False)
 600 |     hashtags = db.Column(db.String(200))
 601 |     status = db.Column(db.String(20), default='draft')
 602 |     approved_at = db.Column(db.DateTime)
 603 |     posted_at = db.Column(db.DateTime)
 604 |     post_url = db.Column(db.String(500))
 605 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 606 | 
 607 | 
 608 | # =====================================
 609 | # X ENGAGEMENT SENTRY (TWEET REPLIES)
 610 | # =====================================
 611 | 
 612 | 
 613 | class XInboxTweet(db.Model):
 614 |     """Incoming tweets from monitored X accounts for Sovereign Sentry."""
 615 |     __tablename__ = 'x_inbox_tweet'
 616 | 
 617 |     id = db.Column(db.Integer, primary_key=True)
 618 |     tweet_id = db.Column(db.String(64), unique=True, nullable=False)
 619 |     author_handle = db.Column(db.String(50), nullable=False, index=True)
 620 |     author_name = db.Column(db.String(100))
 621 |     tweet_text = db.Column(db.Text, nullable=False)
 622 |     tweet_url = db.Column(db.String(500))
 623 |     tweet_created_at = db.Column(db.DateTime)
 624 |     status = db.Column(
 625 |         db.String(20),
 626 |         default='new',
 627 |     )  # new | drafted | approved | posted | rejected | skipped | error
 628 |     tier = db.Column(db.String(30))
 629 |     style = db.Column(db.String(30))
 630 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 631 | 
 632 | 
 633 | class XReplyDraft(db.Model):
 634 |     """Generated reply drafts evaluated by Sovereign Sentry."""
 635 |     __tablename__ = 'x_reply_draft'
 636 | 
 637 |     id = db.Column(db.Integer, primary_key=True)
 638 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 639 |     draft_text = db.Column(db.String(300), nullable=False)
 640 |     confidence = db.Column(db.Float)
 641 |     reasoning = db.Column(db.Text)
 642 |     style_used = db.Column(db.String(30))
 643 |     risk_flags = db.Column(db.Text)  # optional JSON array string
 644 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 645 | 
 646 |     inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))
 647 | 
 648 | 
 649 | class XReplyPost(db.Model):
 650 |     """Log of replies actually posted to X."""
 651 |     __tablename__ = 'x_reply_post'
 652 | 
 653 |     id = db.Column(db.Integer, primary_key=True)
 654 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 655 |     draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
 656 |     reply_tweet_id = db.Column(db.String(64))
 657 |     posted_at = db.Column(db.DateTime, default=datetime.utcnow)
 658 |     response_payload = db.Column(db.Text)  # raw JSON from X API
 659 | 
 660 |     inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
 661 |     draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))
 662 | 
 663 | 
 664 | # =====================================
 665 | # VALUE STREAM MODELS
 666 | # =====================================
 667 | 
 668 | class ValueCreator(db.Model):
 669 |     __tablename__ = 'value_creator'
 670 |     id = db.Column(db.Integer, primary_key=True)
 671 |     display_name = db.Column(db.String(100), nullable=False)
 672 |     nostr_pubkey = db.Column(db.String(128), unique=True)
 673 |     lightning_address = db.Column(db.String(200))
 674 |     nip05 = db.Column(db.String(200))
 675 |     twitter_handle = db.Column(db.String(50))
 676 |     youtube_channel_id = db.Column(db.String(50))
 677 |     reddit_username = db.Column(db.String(50))
 678 |     stacker_news_username = db.Column(db.String(50))
 679 |     profile_image = db.Column(db.String(500))
 680 |     bio = db.Column(db.Text)
 681 |     total_sats_received = db.Column(db.BigInteger, default=0)
 682 |     total_zaps = db.Column(db.Integer, default=0)
 683 |     curator_score = db.Column(db.Float, default=0)
 684 |     verified = db.Column(db.Boolean, default=False)
 685 |     verified_at = db.Column(db.DateTime)
 686 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 687 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 688 |     curated_posts = db.relationship('CuratedPost', backref='creator', lazy='dynamic',
 689 |                                      foreign_keys='CuratedPost.creator_id')
 690 |     submitted_posts = db.relationship('CuratedPost', backref='curator', lazy='dynamic',
 691 |                                        foreign_keys='CuratedPost.curator_id')
 692 | 
 693 | class CuratedPost(db.Model):
 694 |     __tablename__ = 'curated_post'
 695 |     id = db.Column(db.Integer, primary_key=True)
 696 |     platform = db.Column(db.String(30), nullable=False)
 697 |     original_url = db.Column(db.String(1000), nullable=False, unique=True)
 698 |     original_id = db.Column(db.String(200))
 699 |     title = db.Column(db.String(500))
 700 |     content_preview = db.Column(db.Text)
 701 |     thumbnail_url = db.Column(db.String(500))
 702 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 703 |     curator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 704 |     total_sats = db.Column(db.BigInteger, default=0)
 705 |     zap_count = db.Column(db.Integer, default=0)
 706 |     boost_sats = db.Column(db.BigInteger, default=0)
 707 |     signal_score = db.Column(db.Float, default=0)
 708 |     decay_factor = db.Column(db.Float, default=1.0)
 709 |     is_verified = db.Column(db.Boolean, default=False)
 710 |     is_featured = db.Column(db.Boolean, default=False)
 711 |     submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
 712 |     last_zap_at = db.Column(db.DateTime)
 713 |     
 714 |     def calculate_signal_score(self):
 715 |         age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
 716 |         time_decay = max(0.1, 1 - (age_hours / 168))
 717 |         raw_score = (self.total_sats * 0.001) + (self.zap_count * 10)
 718 |         self.signal_score = raw_score * time_decay * self.decay_factor
 719 |         return self.signal_score
 720 | 
 721 | class ZapEvent(db.Model):
 722 |     __tablename__ = 'zap_event'
 723 |     id = db.Column(db.Integer, primary_key=True)
 724 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 725 |     sender_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 726 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 727 |     creator_share = db.Column(db.BigInteger)
 728 |     curator_share = db.Column(db.BigInteger)
 729 |     platform_share = db.Column(db.BigInteger)
 730 |     payment_hash = db.Column(db.String(128))
 731 |     bolt11_invoice = db.Column(db.Text)
 732 |     preimage = db.Column(db.String(128))
 733 |     status = db.Column(db.String(20), default='pending')
 734 |     source = db.Column(db.String(30))
 735 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 736 |     settled_at = db.Column(db.DateTime)
 737 |     post = db.relationship('CuratedPost', backref=db.backref('zaps', lazy='dynamic'))
 738 | 
 739 | class TrustEdge(db.Model):
 740 |     __tablename__ = 'trust_edge'
 741 |     id = db.Column(db.Integer, primary_key=True)
 742 |     truster_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 743 |     trusted_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 744 |     trust_weight = db.Column(db.Float, default=1.0)
 745 |     total_sats_via = db.Column(db.BigInteger, default=0)
 746 |     successful_curations = db.Column(db.Integer, default=0)
 747 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 748 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 749 |     __table_args__ = (db.UniqueConstraint('truster_id', 'trusted_id', name='unique_trust_edge'),)
 750 | 
 751 | class BoostStake(db.Model):
 752 |     __tablename__ = 'boost_stake'
 753 |     id = db.Column(db.Integer, primary_key=True)
 754 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 755 |     staker_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 756 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 757 |     boost_multiplier = db.Column(db.Float, default=1.0)
 758 |     expires_at = db.Column(db.DateTime)
 759 |     refunded = db.Column(db.Boolean, default=False)
 760 |     refund_amount = db.Column(db.BigInteger, default=0)
 761 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 762 |     post = db.relationship('CuratedPost', backref=db.backref('boosts', lazy='dynamic'))
 763 | 
 764 | class ExtensionSession(db.Model):
 765 |     __tablename__ = 'extension_session'
 766 |     id = db.Column(db.Integer, primary_key=True)
 767 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 768 |     session_token = db.Column(db.String(128), unique=True, nullable=False)
 769 |     browser_fingerprint = db.Column(db.String(128))
 770 |     user_agent = db.Column(db.String(500))
 771 |     is_active = db.Column(db.Boolean, default=True)
 772 |     last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
 773 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 774 |     expires_at = db.Column(db.DateTime)
 775 |     creator = db.relationship('ValueCreator', backref=db.backref('sessions', lazy='dynamic'))
 776 | 
 777 | class RollingActivity(db.Model):
 778 |     __tablename__ = 'rolling_activity'
 779 |     id = db.Column(db.Integer, primary_key=True)
 780 |     page_path = db.Column(db.String(500), nullable=False, index=True)
 781 |     page_name = db.Column(db.String(200))
 782 |     session_hash = db.Column(db.String(64), nullable=False)
 783 |     last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 784 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 785 |     
 786 |     @classmethod
 787 |     def record_activity(cls, page_path, page_name, session_hash):
 788 |         existing = cls.query.filter_by(page_path=page_path, session_hash=session_hash).first()
 789 |         if existing:
 790 |             existing.last_seen = datetime.utcnow()
 791 |         else:
 792 |             activity = cls(page_path=page_path, page_name=page_name, session_hash=session_hash, last_seen=datetime.utcnow())
 793 |             db.session.add(activity)
 794 |         try:
 795 |             db.session.commit()
 796 |         except Exception:
 797 |             db.session.rollback()
 798 | 
 799 |     @classmethod
 800 |     def get_operative_density(cls, window_minutes=30, limit=5):
 801 |         from sqlalchemy import func
 802 |         cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
 803 |         results = db.session.query(cls.page_path, cls.page_name, func.count(func.distinct(cls.session_hash)).label('count')).filter(cls.last_seen >= cutoff).group_by(cls.page_path, cls.page_name).order_by(func.count(func.distinct(cls.session_hash)).desc()).limit(limit).all()
 804 |         return results
 805 | 
 806 | class RealTimeProduct(db.Model):
 807 |     __tablename__ = 'realtime_product'
 808 |     id = db.Column(db.Integer, primary_key=True)
 809 |     statement_text = db.Column(db.String(100), nullable=False)
 810 |     design_url = db.Column(db.String(500))
 811 |     design_style = db.Column(db.String(50), default='center_chest')
 812 |     text_color = db.Column(db.String(20), default='#FFFFFF')
 813 |     trigger_state = db.Column(db.String(50))
 814 |     trigger_keywords = db.Column(db.Text)
 815 |     sentiment_score = db.Column(db.Float)
 816 |     status = db.Column(db.String(20), default='draft')
 817 |     approved_at = db.Column(db.DateTime)
 818 |     approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
 819 |     printful_product_id = db.Column(db.String(100))
 820 |     printful_sync_status = db.Column(db.String(50), default='pending')
 821 |     heat_multiplier = db.Column(db.Float, default=2.0)
 822 |     heat_expires_at = db.Column(db.DateTime)
 823 |     sarah_description = db.Column(db.Text)
 824 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 825 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 826 |     
 827 |     def is_hot(self):
 828 |         return self.heat_expires_at and datetime.utcnow() < self.heat_expires_at
 829 | 
 830 | class IntelligencePost(db.Model):
 831 |     id = db.Column(db.Integer, primary_key=True)
 832 |     persona = db.Column(db.String(20))
 833 |     partner_name = db.Column(db.String(100))
 834 |     partner_handle = db.Column(db.String(100))
 835 |     primary_tweet = db.Column(db.Text, nullable=False)
 836 |     thread_content = db.Column(db.Text)
 837 |     key_insight = db.Column(db.Text)
 838 |     source_video_id = db.Column(db.String(50))
 839 |     source_video_title = db.Column(db.String(500))
 840 |     x_tweet_id = db.Column(db.String(100))
 841 |     nostr_event_id = db.Column(db.String(100))
 842 |     engagement_likes = db.Column(db.Integer, default=0)
 843 |     engagement_retweets = db.Column(db.Integer, default=0)
 844 |     engagement_replies = db.Column(db.Integer, default=0)
 845 |     published_at = db.Column(db.DateTime, default=datetime.utcnow)
 846 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 847 | 
 848 | class SentimentReport(db.Model):
 849 |     id = db.Column(db.Integer, primary_key=True)
 850 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 851 |     report_date = db.Column(db.Date, nullable=False, unique=True)
 852 |     overall_sentiment = db.Column(db.String(20))
 853 |     sentiment_score = db.Column(db.Float)
 854 |     x_posts_analyzed = db.Column(db.Integer, default=0)
 855 |     nostr_notes_analyzed = db.Column(db.Integer, default=0)
 856 |     top_themes = db.Column(db.Text)
 857 |     key_narratives = db.Column(db.Text)
 858 |     cited_sources = db.Column(db.Text)
 859 |     raw_analysis = db.Column(db.Text)
 860 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 861 |     article = db.relationship('Article', backref='sentiment_report', lazy=True)
 862 | 
 863 | class SarahBrief(db.Model):
 864 |     __tablename__ = 'sarah_brief'
 865 |     id = db.Column(db.Integer, primary_key=True)
 866 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 867 |     brief_date = db.Column(db.Date, nullable=False, unique=True)
 868 |     macro_state = db.Column(db.Text)
 869 |     network_calibration = db.Column(db.Text)
 870 |     signal_1_title = db.Column(db.String(500))
 871 |     signal_1_source = db.Column(db.String(500))
 872 |     signal_1_url = db.Column(db.String(500))
 873 |     signal_1_impact = db.Column(db.Float, default=0.0)
 874 |     signal_2_title = db.Column(db.String(500))
 875 |     signal_2_source = db.Column(db.String(500))
 876 |     signal_2_url = db.Column(db.String(500))
 877 |     signal_2_impact = db.Column(db.Float, default=0.0)
 878 |     signal_3_title = db.Column(db.String(500))
 879 |     signal_3_source = db.Column(db.String(500))
 880 |     signal_3_url = db.Column(db.String(500))
 881 |     signal_3_impact = db.Column(db.Float, default=0.0)
 882 |     mempool_state = db.Column(db.Text)
 883 |     hashrate_state = db.Column(db.Text)
 884 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 885 |     article = db.relationship('Article', backref='sarah_brief', lazy=True)
 886 | 
 887 | class SentimentBuffer(db.Model):
 888 |     id = db.Column(db.Integer, primary_key=True)
 889 |     timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 890 |     sentiment_score = db.Column(db.Float, nullable=False)
 891 |     post_count = db.Column(db.Integer, default=0)
 892 |     dominant_theme = db.Column(db.String(200))
 893 |     source_breakdown = db.Column(db.Text)
 894 | 
 895 | class EmergencyFlash(db.Model):
 896 |     id = db.Column(db.Integer, primary_key=True)
 897 |     triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 898 |     previous_score = db.Column(db.Float)
 899 |     current_score = db.Column(db.Float)
 900 |     drift_magnitude = db.Column(db.Float)
 901 |     direction = db.Column(db.String(20))
 902 |     trigger_reason = db.Column(db.Text)
 903 |     top_signal_url = db.Column(db.String(500))
 904 |     top_signal_author = db.Column(db.String(200))
 905 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 906 |     acknowledged = db.Column(db.Boolean, default=False)
 907 |     acknowledged_at = db.Column(db.DateTime)
 908 |     article = db.relationship('Article', backref='emergency_flash', lazy=True)
 909 | 
 910 | class CollectedSignal(db.Model):
 911 |     __tablename__ = 'collected_signal'
 912 |     id = db.Column(db.Integer, primary_key=True)
 913 |     platform = db.Column(db.String(20), nullable=False)
 914 |     post_id = db.Column(db.String(100), nullable=False, unique=True)
 915 |     author_name = db.Column(db.String(200), nullable=False)
 916 |     author_handle = db.Column(db.String(100), nullable=False)
 917 |     author_tier = db.Column(db.String(50), default='general')
 918 |     content = db.Column(db.Text, nullable=False)
 919 |     url = db.Column(db.String(500), nullable=False)
 920 |     engagement_likes = db.Column(db.Integer, default=0)
 921 |     engagement_reposts = db.Column(db.Integer, default=0)
 922 |     engagement_replies = db.Column(db.Integer, default=0)
 923 |     engagement_score = db.Column(db.Float, default=0.0)
 924 |     sentiment = db.Column(db.String(20))
 925 |     sentiment_score = db.Column(db.Float)
 926 |     is_bitcoin_related = db.Column(db.Boolean, default=True)
 927 |     posted_at = db.Column(db.DateTime)
 928 |     collected_at = db.Column(db.DateTime, default=datetime.utcnow)
 929 |     is_verified = db.Column(db.Boolean, default=True)
 930 |     is_legendary = db.Column(db.Boolean, default=False)
 931 |     __table_args__ = (
 932 |         db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
 933 |         db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
 934 |     )
 935 | 
 936 | 
 937 | class PriceAlert(db.Model):
 938 |     """Bitcoin price alert subscriptions for /charts page."""
 939 |     __tablename__ = 'price_alerts'
 940 |     id = db.Column(db.Integer, primary_key=True)
 941 |     email = db.Column(db.String(254), nullable=False, index=True)
 942 |     target_price = db.Column(db.Float, nullable=False)
 943 |     direction = db.Column(db.String(5), nullable=False)  # 'above' or 'below'
 944 |     triggered = db.Column(db.Boolean, default=False, nullable=False)
 945 |     triggered_at = db.Column(db.DateTime, nullable=True)
 946 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
 947 |     __table_args__ = (
 948 |         db.Index('idx_price_alerts_email_triggered', 'email', 'triggered'),
 949 |         db.Index('idx_price_alerts_active', 'triggered', 'target_price'),
 950 |     )
```

### File: core/templates/charts.html (1813 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Bitcoin Charts — Live On-Chain Intelligence | Protocol Pulse{% endblock %}
   4 | {% block meta_description %}Bloomberg Terminal meets cypherpunk. Real-time Bitcoin price charts, mining metrics, mempool data, on-chain analytics, and supply analysis. Free. No account needed.{% endblock %}
   5 | 
   6 | {% block extra_css %}
   7 | <style>
   8 | /* ── Charts Page — Design System ─────────────────────────────── */
   9 | :root {
  10 |   --bg:      #06070b;
  11 |   --panel:   #0d1118;
  12 |   --panel-2: #121824;
  13 |   --text:    #eef2ff;
  14 |   --muted:   #95a0ba;
  15 |   --red:     #ff3b5f;
  16 |   --gold:    #f8c15c;
  17 |   --cyan:    #5de4ff;
  18 |   --lime:    #89ffb8;
  19 |   --coral:   #ff8ba0;
  20 |   --border:  rgba(255,255,255,0.07);
  21 | }
  22 | body { background: var(--bg); color: var(--text); }
  23 | 
  24 | .charts-page { max-width: 1440px; margin: 0 auto; padding: 0 1rem 4rem; }
  25 | 
  26 | /* Stat Bar */
  27 | .stat-bar {
  28 |   display: grid;
  29 |   grid-template-columns: repeat(6, 1fr);
  30 |   gap: .5rem;
  31 |   padding: 1rem 0;
  32 |   position: sticky;
  33 |   top: 0;
  34 |   z-index: 50;
  35 |   background: linear-gradient(180deg, rgba(6,7,11,.98) 85%, transparent);
  36 |   backdrop-filter: blur(12px);
  37 |   margin-bottom: 1.5rem;
  38 | }
  39 | .stat-card {
  40 |   background: var(--panel);
  41 |   border: 1px solid var(--border);
  42 |   border-radius: 10px;
  43 |   padding: .6rem .9rem;
  44 |   display: flex;
  45 |   flex-direction: column;
  46 |   gap: .15rem;
  47 | }
  48 | .stat-card .label {
  49 |   font-family: 'JetBrains Mono', monospace;
  50 |   font-size: 9px;
  51 |   font-weight: 800;
  52 |   letter-spacing: .18em;
  53 |   text-transform: uppercase;
  54 |   color: var(--muted);
  55 | }
  56 | .stat-card .value {
  57 |   font-family: 'JetBrains Mono', monospace;
  58 |   font-size: 1.1rem;
  59 |   font-weight: 900;
  60 |   color: var(--text);
  61 |   line-height: 1;
  62 | }
  63 | .stat-card .delta { font-size: 11px; font-weight: 700; }
  64 | .delta-up   { color: var(--lime); }
  65 | .delta-down { color: var(--coral); }
  66 | .live-dot {
  67 |   display: inline-block; width: 6px; height: 6px;
  68 |   border-radius: 50%; background: var(--lime);
  69 |   margin-right: 4px;
  70 |   animation: pulse-dot 2s infinite;
  71 | }
  72 | .live-dot.red { background: var(--coral); animation: none; }
  73 | @keyframes pulse-dot {
  74 |   0%,100% { opacity:1; } 50% { opacity:.3; }
  75 | }
  76 | 
  77 | /* Section header */
  78 | .section-header {
  79 |   display: flex; align-items: center; gap: 1rem;
  80 |   margin: 2.5rem 0 1rem;
  81 | }
  82 | .section-kicker {
  83 |   font-family: 'JetBrains Mono', monospace;
  84 |   font-size: 10px; font-weight: 800;
  85 |   letter-spacing: .20em; text-transform: uppercase;
  86 |   color: var(--gold);
  87 | }
  88 | .section-title {
  89 |   font-size: 1.25rem; font-weight: 900;
  90 |   color: var(--text); margin: 0;
  91 | }
  92 | 
  93 | /* Chart card */
  94 | .chart-card {
  95 |   background: var(--panel);
  96 |   border: 1px solid var(--border);
  97 |   border-radius: 14px;
  98 |   padding: 1.25rem;
  99 |   position: relative;
 100 |   overflow: hidden;
 101 | }
 102 | .chart-card-header {
 103 |   display: flex; align-items: center; justify-content: space-between;
 104 |   margin-bottom: 1rem; flex-wrap: wrap; gap: .5rem;
 105 | }
 106 | .chart-title {
 107 |   font-family: 'JetBrains Mono', monospace;
 108 |   font-size: 11px; font-weight: 800;
 109 |   letter-spacing: .14em; text-transform: uppercase;
 110 |   color: var(--muted);
 111 | }
 112 | .chart-actions { display: flex; gap: .4rem; flex-wrap: wrap; }
 113 | .btn-chip {
 114 |   background: rgba(255,255,255,.05);
 115 |   border: 1px solid var(--border);
 116 |   border-radius: 6px;
 117 |   padding: 3px 10px;
 118 |   font-family: 'JetBrains Mono', monospace;
 119 |   font-size: 10px; font-weight: 700;
 120 |   letter-spacing: .08em;
 121 |   color: var(--muted);
 122 |   cursor: pointer;
 123 |   transition: all .15s;
 124 | }
 125 | .btn-chip:hover, .btn-chip.active {
 126 |   background: rgba(248,193,92,.1);
 127 |   border-color: var(--gold);
 128 |   color: var(--gold);
 129 | }
 130 | .btn-chip.interpret-btn {
 131 |   background: rgba(93,228,255,.06);
 132 |   border-color: rgba(93,228,255,.2);
 133 |   color: var(--cyan);
 134 | }
 135 | .btn-chip.interpret-btn:hover {
 136 |   background: rgba(93,228,255,.12);
 137 |   border-color: var(--cyan);
 138 | }
 139 | .btn-chip.download-btn {
 140 |   background: rgba(137,255,184,.06);
 141 |   border-color: rgba(137,255,184,.2);
 142 |   color: var(--lime);
 143 | }
 144 | .btn-chip.download-btn:hover {
 145 |   background: rgba(137,255,184,.12);
 146 | }
 147 | 
 148 | /* Canvas wrapper */
 149 | .canvas-wrap {
 150 |   position: relative; width: 100%;
 151 | }
 152 | .canvas-wrap canvas {
 153 |   width: 100% !important;
 154 |   display: block;
 155 |   border-radius: 8px;
 156 | }
 157 | 
 158 | /* Loading / error overlay */
 159 | .chart-overlay {
 160 |   position: absolute; inset: 0;
 161 |   display: flex; align-items: center; justify-content: center;
 162 |   border-radius: 8px;
 163 |   background: rgba(6,7,11,.85);
 164 |   backdrop-filter: blur(4px);
 165 |   z-index: 10;
 166 | }
 167 | .chart-overlay .msg {
 168 |   font-family: 'JetBrains Mono', monospace;
 169 |   font-size: 12px; color: var(--muted);
 170 |   text-align: center;
 171 | }
 172 | .chart-overlay .msg .spinner {
 173 |   width: 20px; height: 20px;
 174 |   border: 2px solid var(--border);
 175 |   border-top-color: var(--gold);
 176 |   border-radius: 50%;
 177 |   animation: spin .8s linear infinite;
 178 |   margin: 0 auto .5rem;
 179 | }
 180 | @keyframes spin { to { transform: rotate(360deg); } }
 181 | 
 182 | /* AI interpretation box */
 183 | .ai-box {
 184 |   margin-top: .75rem;
 185 |   background: rgba(93,228,255,.05);
 186 |   border: 1px solid rgba(93,228,255,.15);
 187 |   border-radius: 8px;
 188 |   padding: .75rem 1rem;
 189 |   font-size: 13px; line-height: 1.5;
 190 |   color: #c8e8f0;
 191 |   display: none;
 192 | }
 193 | .ai-box.visible { display: block; }
 194 | .ai-box-label {
 195 |   font-family: 'JetBrains Mono', monospace;
 196 |   font-size: 9px; font-weight: 800;
 197 |   letter-spacing: .18em; text-transform: uppercase;
 198 |   color: var(--cyan); margin-bottom: .4rem;
 199 | }
 200 | 
 201 | /* Overlay toggles */
 202 | .overlay-toggles {
 203 |   display: flex; flex-wrap: wrap; gap: .5rem;
 204 |   margin-bottom: .75rem;
 205 | }
 206 | .toggle-chip {
 207 |   display: flex; align-items: center; gap: .4rem;
 208 |   background: rgba(255,255,255,.04);
 209 |   border: 1px solid var(--border);
 210 |   border-radius: 6px;
 211 |   padding: 4px 10px;
 212 |   font-family: 'JetBrains Mono', monospace;
 213 |   font-size: 10px; font-weight: 700;
 214 |   color: var(--muted);
 215 |   cursor: pointer;
 216 |   user-select: none;
 217 |   transition: all .15s;
 218 | }
 219 | .toggle-chip input[type=checkbox] { accent-color: var(--gold); }
 220 | .toggle-chip.active {
 221 |   border-color: rgba(248,193,92,.3);
 222 |   color: var(--gold);
 223 |   background: rgba(248,193,92,.07);
 224 | }
 225 | 
 226 | /* 2-col grid */
 227 | .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
 228 | @media (max-width: 768px) {
 229 |   .stat-bar { grid-template-columns: repeat(3, 1fr); }
 230 |   .two-col  { grid-template-columns: 1fr; }
 231 |   .chart-card-header { flex-direction: column; align-items: flex-start; }
 232 | }
 233 | @media (max-width: 480px) {
 234 |   .stat-bar { grid-template-columns: repeat(2, 1fr); }
 235 | }
 236 | 
 237 | /* Supply bar */
 238 | .supply-bar-wrap {
 239 |   margin: 1rem 0;
 240 |   background: rgba(255,255,255,.05);
 241 |   border-radius: 999px;
 242 |   height: 14px;
 243 |   overflow: hidden;
 244 | }
 245 | .supply-bar-fill {
 246 |   height: 100%;
 247 |   border-radius: 999px;
 248 |   background: linear-gradient(90deg, #f8c15c, #ffda8a);
 249 |   box-shadow: 0 0 16px rgba(248,193,92,.4);
 250 |   transition: width 1s ease;
 251 | }
 252 | 
 253 | /* HODL wave colors */
 254 | .hodl-legend { display: flex; flex-wrap: wrap; gap: .4rem .8rem; margin-top: .5rem; }
 255 | .hodl-legend-item { display: flex; align-items: center; gap: .3rem; font-size: 10px; color: var(--muted); }
 256 | .hodl-legend-swatch { width: 10px; height: 10px; border-radius: 2px; }
 257 | 
 258 | /* Fee pills */
 259 | .fee-pills { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: .5rem; }
 260 | .fee-pill {
 261 |   background: var(--panel-2);
 262 |   border: 1px solid var(--border);
 263 |   border-radius: 8px;
 264 |   padding: .5rem .9rem;
 265 |   text-align: center;
 266 | }
 267 | .fee-pill .fee-label { font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 800; letter-spacing: .15em; text-transform: uppercase; color: var(--muted); display: block; }
 268 | .fee-pill .fee-val   { font-family: 'JetBrains Mono', monospace; font-size: 1.3rem; font-weight: 900; display: block; }
 269 | 
 270 | /* HHI warning */
 271 | .hhi-warn {
 272 |   background: rgba(255,59,95,.08);
 273 |   border: 1px solid rgba(255,59,95,.25);
 274 |   border-radius: 8px;
 275 |   padding: .6rem 1rem;
 276 |   font-size: 12px; color: var(--coral);
 277 |   margin-top: .75rem;
 278 |   display: none;
 279 | }
 280 | .hhi-warn.visible { display: block; }
 281 | 
 282 | /* Halving countdown */
 283 | .halving-display {
 284 |   text-align: center; padding: 1.5rem 0;
 285 | }
 286 | .halving-blocks {
 287 |   font-family: 'JetBrains Mono', monospace;
 288 |   font-size: 3rem; font-weight: 900;
 289 |   color: var(--red);
 290 |   letter-spacing: -.04em;
 291 |   line-height: 1;
 292 |   text-shadow: 0 0 40px rgba(255,59,95,.4);
 293 | }
 294 | .halving-sub {
 295 |   font-family: 'JetBrains Mono', monospace;
 296 |   font-size: 11px; font-weight: 800;
 297 |   letter-spacing: .18em; text-transform: uppercase;
 298 |   color: var(--muted); margin-top: .4rem;
 299 | }
 300 | .sats-display {
 301 |   font-family: 'JetBrains Mono', monospace;
 302 |   font-size: 2rem; font-weight: 900;
 303 |   color: var(--gold);
 304 |   text-shadow: 0 0 30px rgba(248,193,92,.35);
 305 | }
 306 | 
 307 | /* Fear & Greed gauge */
 308 | .fg-gauge-wrap { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
 309 | .fg-score {
 310 |   font-family: 'JetBrains Mono', monospace;
 311 |   font-size: 3rem; font-weight: 900;
 312 |   line-height: 1;
 313 | }
 314 | .fg-label { font-size: 13px; color: var(--muted); margin-top: .2rem; }
 315 | 
 316 | /* Alert form */
 317 | .alert-form { display: flex; gap: .75rem; flex-wrap: wrap; margin-top: 1rem; }
 318 | .alert-form input[type=email],
 319 | .alert-form input[type=number] {
 320 |   flex: 1; min-width: 160px;
 321 |   background: var(--panel-2);
 322 |   border: 1px solid var(--border);
 323 |   border-radius: 8px;
 324 |   padding: .6rem 1rem;
 325 |   color: var(--text);
 326 |   font-family: 'JetBrains Mono', monospace;
 327 |   font-size: 14px;
 328 | }
 329 | .alert-form input:focus {
 330 |   outline: none;
 331 |   border-color: rgba(248,193,92,.4);
 332 |   box-shadow: 0 0 0 2px rgba(248,193,92,.08);
 333 | }
 334 | .alert-form select {
 335 |   background: var(--panel-2);
 336 |   border: 1px solid var(--border);
 337 |   border-radius: 8px;
 338 |   padding: .6rem 1rem;
 339 |   color: var(--text);
 340 |   font-family: 'JetBrains Mono', monospace;
 341 |   font-size: 13px;
 342 |   cursor: pointer;
 343 | }
 344 | .btn-submit {
 345 |   background: linear-gradient(135deg, rgba(255,59,95,.2), rgba(255,59,95,.1));
 346 |   border: 1px solid rgba(255,59,95,.4);
 347 |   border-radius: 8px;
 348 |   padding: .6rem 1.5rem;
 349 |   color: var(--red);
 350 |   font-family: 'JetBrains Mono', monospace;
 351 |   font-size: 12px; font-weight: 800;
 352 |   letter-spacing: .1em; text-transform: uppercase;
 353 |   cursor: pointer;
 354 |   transition: all .15s;
 355 | }
 356 | .btn-submit:hover {
 357 |   background: rgba(255,59,95,.2);
 358 |   box-shadow: 0 0 20px rgba(255,59,95,.2);
 359 | }
 360 | .alert-msg { margin-top: .5rem; font-size: 13px; }
 361 | .alert-msg.ok  { color: var(--lime); }
 362 | .alert-msg.err { color: var(--coral); }
 363 | 
 364 | /* Embed modal */
 365 | .embed-modal {
 366 |   display: none; position: fixed; inset: 0; z-index: 999;
 367 |   background: rgba(0,0,0,.7); backdrop-filter: blur(6px);
 368 |   align-items: center; justify-content: center;
 369 | }
 370 | .embed-modal.open { display: flex; }
 371 | .embed-box {
 372 |   background: var(--panel);
 373 |   border: 1px solid var(--border);
 374 |   border-radius: 14px;
 375 |   padding: 1.5rem;
 376 |   width: min(500px, 90vw);
 377 | }
 378 | .embed-code {
 379 |   background: var(--panel-2);
 380 |   border: 1px solid var(--border);
 381 |   border-radius: 8px;
 382 |   padding: .75rem 1rem;
 383 |   font-family: 'JetBrains Mono', monospace;
 384 |   font-size: 12px; color: var(--muted);
 385 |   word-break: break-all;
 386 |   margin: .75rem 0;
 387 | }
 388 | 
 389 | /* Cmd+K bar */
 390 | .cmdbar {
 391 |   display: none; position: fixed; inset: 0; z-index: 998;
 392 |   background: rgba(0,0,0,.65); backdrop-filter: blur(8px);
 393 |   align-items: flex-start; justify-content: center;
 394 |   padding-top: 15vh;
 395 | }
 396 | .cmdbar.open { display: flex; }
 397 | .cmdbar-inner {
 398 |   background: var(--panel);
 399 |   border: 1px solid rgba(248,193,92,.25);
 400 |   border-radius: 14px;
 401 |   width: min(540px, 90vw);
 402 |   overflow: hidden;
 403 |   box-shadow: 0 24px 64px rgba(0,0,0,.6), 0 0 40px rgba(248,193,92,.08);
 404 | }
 405 | .cmdbar-input {
 406 |   width: 100%; background: transparent; border: none;
 407 |   padding: 1rem 1.25rem;
 408 |   font-family: 'JetBrains Mono', monospace;
 409 |   font-size: 15px; color: var(--text);
 410 | }
 411 | .cmdbar-input:focus { outline: none; }
 412 | .cmdbar-results { border-top: 1px solid var(--border); }
 413 | .cmdbar-item {
 414 |   display: flex; align-items: center; gap: .75rem;
 415 |   padding: .65rem 1.25rem;
 416 |   cursor: pointer;
 417 |   transition: background .1s;
 418 |   font-size: 14px;
 419 | }
 420 | .cmdbar-item:hover { background: rgba(248,193,92,.07); }
 421 | .cmdbar-item-key {
 422 |   font-family: 'JetBrains Mono', monospace;
 423 |   font-size: 10px; font-weight: 800; color: var(--gold);
 424 |   min-width: 80px;
 425 | }
 426 | 
 427 | /* Pool table */
 428 | .pool-table { width: 100%; border-collapse: collapse; margin-top: .75rem; }
 429 | .pool-table th {
 430 |   font-family: 'JetBrains Mono', monospace;
 431 |   font-size: 9px; font-weight: 800;
 432 |   letter-spacing: .15em; text-transform: uppercase;
 433 |   color: var(--muted); text-align: left;
 434 |   padding: .4rem .6rem; border-bottom: 1px solid var(--border);
 435 | }
 436 | .pool-table td {
 437 |   font-family: 'JetBrains Mono', monospace;
 438 |   font-size: 12px; color: var(--text);
 439 |   padding: .4rem .6rem; border-bottom: 1px solid rgba(255,255,255,.03);
 440 | }
 441 | 
 442 | /* Lightning stats */
 443 | .lightning-stats { display: grid; grid-template-columns: repeat(3,1fr); gap: .75rem; }
 444 | .ln-stat {
 445 |   background: var(--panel-2);
 446 |   border: 1px solid var(--border);
 447 |   border-radius: 10px;
 448 |   padding: .8rem 1rem;
 449 | }
 450 | .ln-stat .ln-label { font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 800; letter-spacing: .15em; text-transform: uppercase; color: var(--muted); }
 451 | .ln-stat .ln-val   { font-family: 'JetBrains Mono', monospace; font-size: 1.3rem; font-weight: 900; color: var(--cyan); margin-top: .2rem; }
 452 | </style>
 453 | {% endblock %}
 454 | 
 455 | {% block content %}
 456 | <div class="charts-page" id="charts-page">
 457 | 
 458 |   <!-- Stat Bar -->
 459 |   <div class="stat-bar" id="stat-bar" role="region" aria-label="Live Bitcoin metrics">
 460 |     <div class="stat-card">
 461 |       <span class="label"><span class="live-dot" id="ws-dot"></span>BTC Price</span>
 462 |       <span class="value" id="stat-price" aria-live="polite">${{ "{:,.0f}".format(btc_price) if btc_price else "---" }}</span>
 463 |       <span class="delta" id="stat-price-delta">—</span>
 464 |     </div>
 465 |     <div class="stat-card">
 466 |       <span class="label">24H Change</span>
 467 |       <span class="value delta" id="stat-change">—</span>
 468 |     </div>
 469 |     <div class="stat-card">
 470 |       <span class="label">Market Cap</span>
 471 |       <span class="value" id="stat-mcap">—</span>
 472 |     </div>
 473 |     <div class="stat-card">
 474 |       <span class="label">Block Height</span>
 475 |       <span class="value" id="stat-height">{{ "{:,}".format(block_height) if block_height else "—" }}</span>
 476 |     </div>
 477 |     <div class="stat-card">
 478 |       <span class="label">Mempool</span>
 479 |       <span class="value" id="stat-mempool">{{ mempool_mb }} MB</span>
 480 |     </div>
 481 |     <div class="stat-card">
 482 |       <span class="label">Next Block Fee</span>
 483 |       <span class="value" id="stat-fee">{{ next_block_fee }} sat/vB</span>
 484 |     </div>
 485 |   </div>
 486 | 
 487 |   <!-- ── SECTION 1: PRICE CHART ─────────────────────────────────── -->
 488 |   <div class="section-header" id="section-price">
 489 |     <span class="section-kicker">Section 01 • Live Data</span>
 490 |     <h2 class="section-title">BTC/USD Price Chart</h2>
 491 |   </div>
 492 |   <div class="chart-card">
 493 |     <div class="chart-card-header">
 494 |       <span class="chart-title">Bitcoin / US Dollar</span>
 495 |       <div class="chart-actions">
 496 |         <button class="btn-chip active" data-tf="1" onclick="loadPriceChart(1,this)">1D</button>
 497 |         <button class="btn-chip active" data-tf="7" onclick="loadPriceChart(7,this)">7D</button>
 498 |         <button class="btn-chip" data-tf="30" onclick="loadPriceChart(30,this)">30D</button>
 499 |         <button class="btn-chip" data-tf="90" onclick="loadPriceChart(90,this)">90D</button>
 500 |         <button class="btn-chip" data-tf="365" onclick="loadPriceChart(365,this)">1Y</button>
 501 |         <button class="btn-chip interpret-btn" onclick="interpretChart('price','Price Chart')">⚡ INTERPRET</button>
 502 |         <button class="btn-chip download-btn" onclick="downloadChart('price-canvas','BTC Price')">↓ PNG</button>
 503 |         <button class="btn-chip" onclick="openEmbed('price')">⊞ EMBED</button>
 504 |       </div>
 505 |     </div>
 506 |     <div class="overlay-toggles" id="price-overlays">
 507 |       <label class="toggle-chip active"><input type="checkbox" checked onchange="toggleOverlay('ma200',this)"> 200D MA</label>
 508 |       <label class="toggle-chip"><input type="checkbox" onchange="toggleOverlay('bb',this)"> Bollinger Bands</label>
 509 |       <label class="toggle-chip"><input type="checkbox" onchange="toggleOverlay('s2f',this)"> Stock-to-Flow</label>
 510 |       <label class="toggle-chip"><input type="checkbox" onchange="toggleOverlay('mayer',this)"> Mayer Multiple</label>
 511 |     </div>
 512 |     <div class="canvas-wrap" style="height:320px">
 513 |       <canvas id="price-canvas" height="320" aria-label="BTC/USD price chart" role="img"></canvas>
 514 |       <div class="chart-overlay" id="price-loading">
 515 |         <div class="msg"><div class="spinner"></div>Loading price data…</div>
 516 |       </div>
 517 |     </div>
 518 |     <!-- RSI sub-chart -->
 519 |     <div id="rsi-wrap" style="display:none; margin-top:.5rem;">
 520 |       <label class="toggle-chip" style="margin-bottom:.4rem; display:inline-flex;">
 521 |         <input type="checkbox" id="rsi-toggle" onchange="toggleSubChart('rsi-wrap',this)"> RSI (14)
 522 |       </label>
 523 |       <div class="canvas-wrap" style="height:80px">
 524 |         <canvas id="rsi-canvas" height="80" aria-label="RSI indicator" role="img"></canvas>
 525 |       </div>
 526 |     </div>
 527 |     <!-- MACD sub-chart -->
 528 |     <div id="macd-wrap" style="display:none; margin-top:.5rem;">
 529 |       <label class="toggle-chip" style="margin-bottom:.4rem; display:inline-flex;">
 530 |         <input type="checkbox" id="macd-toggle" onchange="toggleSubChart('macd-wrap',this)"> MACD (12/26/9)
 531 |       </label>
 532 |       <div class="canvas-wrap" style="height:80px">
 533 |         <canvas id="macd-canvas" height="80" aria-label="MACD indicator" role="img"></canvas>
 534 |       </div>
 535 |     </div>
 536 |     <div style="margin-top:.5rem; display:flex; gap:.4rem; flex-wrap:wrap;">
 537 |       <label class="toggle-chip"><input type="checkbox" onchange="document.getElementById('rsi-wrap').style.display=this.checked?'block':'none'; if(this.checked)drawRSI();"> RSI (14)</label>
 538 |       <label class="toggle-chip"><input type="checkbox" onchange="document.getElementById('macd-wrap').style.display=this.checked?'block':'none'; if(this.checked)drawMACD();"> MACD</label>
 539 |     </div>
 540 |     <div class="ai-box" id="ai-price"><div class="ai-box-label">⚡ AI ANALYSIS</div><span id="ai-price-text"></span></div>
 541 |   </div>
 542 | 
 543 |   <!-- ── SECTION 2: MINING METRICS ─────────────────────────────── -->
 544 |   <div class="section-header" id="section-mining">
 545 |     <span class="section-kicker">Section 02 • Mining</span>
 546 |     <h2 class="section-title">Hashrate & Difficulty</h2>
 547 |   </div>
 548 |   <div class="two-col">
 549 |     <div class="chart-card">
 550 |       <div class="chart-card-header">
 551 |         <span class="chart-title">Network Hashrate (EH/s)</span>
 552 |         <div class="chart-actions">
 553 |           <button class="btn-chip interpret-btn" onclick="interpretChart('hashrate','Hashrate Chart')">⚡ INTERPRET</button>
 554 |           <button class="btn-chip download-btn" onclick="downloadChart('hashrate-canvas','Hashrate')">↓ PNG</button>
 555 |         </div>
 556 |       </div>
 557 |       <div class="canvas-wrap" style="height:200px">
 558 |         <canvas id="hashrate-canvas" height="200" aria-label="Bitcoin network hashrate chart" role="img"></canvas>
 559 |         <div class="chart-overlay" id="hashrate-loading">
 560 |           <div class="msg"><div class="spinner"></div>Loading…</div>
 561 |         </div>
 562 |       </div>
 563 |       <div class="ai-box" id="ai-hashrate"><div class="ai-box-label">⚡ AI ANALYSIS</div><span id="ai-hashrate-text"></span></div>
 564 |     </div>
 565 |     <div class="chart-card">
 566 |       <div class="chart-card-header">
 567 |         <span class="chart-title">Difficulty Epoch</span>
 568 |       </div>
 569 |       <div id="difficulty-display" style="padding:.5rem 0"></div>
 570 |     </div>
 571 |   </div>
 572 | 
 573 |   <!-- ── SECTION 3: MINING POOLS ───────────────────────────────── -->
 574 |   <div class="section-header" id="section-pools">
 575 |     <span class="section-kicker">Section 03 • Decentralisation</span>
 576 |     <h2 class="section-title">Mining Pool Distribution</h2>
 577 |   </div>
 578 |   <div class="two-col">
 579 |     <div class="chart-card">
 580 |       <div class="chart-card-header">
 581 |         <span class="chart-title">Pool Share — Last 7 Days</span>
 582 |         <div class="chart-actions">
 583 |           <button class="btn-chip download-btn" onclick="downloadChart('pools-canvas','Mining Pools')">↓ PNG</button>
 584 |         </div>
 585 |       </div>
 586 |       <div class="canvas-wrap" style="height:220px">
 587 |         <canvas id="pools-canvas" height="220" aria-label="Mining pool distribution donut chart" role="img"></canvas>
 588 |         <div class="chart-overlay" id="pools-loading">
 589 |           <div class="msg"><div class="spinner"></div>Loading…</div>
 590 |         </div>
 591 |       </div>
 592 |     </div>
 593 |     <div class="chart-card">
 594 |       <div class="chart-card-header">
 595 |         <span class="chart-title">Pool Breakdown + HHI Score</span>
 596 |       </div>
 597 |       <div id="pool-table-wrap"></div>
 598 |       <div class="hhi-warn" id="hhi-warn">⚠ Top 3 pools control &gt;50% of hashrate — centralisation risk elevated.</div>
 599 |     </div>
 600 |   </div>
 601 | 
 602 |   <!-- ── SECTION 4: MEMPOOL & FEES ─────────────────────────────── -->
 603 |   <div class="section-header" id="section-mempool">
 604 |     <span class="section-kicker">Section 04 • Fee Market</span>
 605 |     <h2 class="section-title">Mempool & Fees</h2>
 606 |   </div>
 607 |   <div class="chart-card">
 608 |     <div class="chart-card-header">
 609 |       <span class="chart-title">Mempool Size (MB) — Live via WebSocket</span>
 610 |       <div class="chart-actions">
 611 |         <button class="btn-chip interpret-btn" onclick="interpretChart('mempool','Mempool Chart')">⚡ INTERPRET</button>
 612 |         <button class="btn-chip download-btn" onclick="downloadChart('mempool-canvas','Mempool')">↓ PNG</button>
 613 |       </div>
 614 |     </div>
 615 |     <div class="canvas-wrap" style="height:180px">
 616 |       <canvas id="mempool-canvas" height="180" aria-label="Mempool size chart" role="img"></canvas>
 617 |     </div>
 618 |     <div class="fee-pills" id="fee-pills">
 619 |       <div class="fee-pill"><span class="fee-label">No Priority</span><span class="fee-val" id="fee-low" style="color:var(--lime)">—</span><span style="font-size:10px;color:var(--muted)">sat/vB</span></div>
 620 |       <div class="fee-pill"><span class="fee-label">1 Hour</span><span class="fee-val" id="fee-mid" style="color:var(--gold)">—</span><span style="font-size:10px;color:var(--muted)">sat/vB</span></div>
 621 |       <div class="fee-pill"><span class="fee-label">30 Min</span><span class="fee-val" id="fee-high" style="color:var(--coral)">—</span><span style="font-size:10px;color:var(--muted)">sat/vB</span></div>
 622 |       <div class="fee-pill"><span class="fee-label">Next Block</span><span class="fee-val" id="fee-urgent" style="color:var(--red)">—</span><span style="font-size:10px;color:var(--muted)">sat/vB</span></div>
 623 |     </div>
 624 |     <div class="ai-box" id="ai-mempool"><div class="ai-box-label">⚡ AI ANALYSIS</div><span id="ai-mempool-text"></span></div>
 625 |   </div>
 626 | 
 627 |   <!-- ── SECTION 5: SUPPLY ANALYSIS ────────────────────────────── -->
 628 |   <div class="section-header" id="section-supply">
 629 |     <span class="section-kicker">Section 05 • Scarcity</span>
 630 |     <h2 class="section-title">Supply Analysis</h2>
 631 |   </div>
 632 |   <div class="chart-card">
 633 |     <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;flex-wrap:wrap">
 634 |       <div>
 635 |         <div class="label" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);">Mined Supply</div>
 636 |         <div class="value" style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:900;color:var(--gold);">{{ "{:,.0f}".format(mined_supply) }}</div>
 637 |         <div style="font-size:11px;color:var(--muted);">of 21,000,000 BTC</div>
 638 |       </div>
 639 |       <div>
 640 |         <div class="label" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);">% Mined</div>
 641 |         <div class="value sats-display" style="font-size:1.5rem;">{{ pct_mined }}%</div>
 642 |       </div>
 643 |       <div>
 644 |         <div class="label" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);">Current Subsidy</div>
 645 |         <div class="value" style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:900;color:var(--cyan);">{{ current_subsidy }} BTC/block</div>
 646 |       </div>
 647 |     </div>
 648 |     <div class="supply-bar-wrap" style="margin:.75rem 0" aria-label="{{ pct_mined }}% of Bitcoin mined">
 649 |       <div class="supply-bar-fill" style="width:{{ pct_mined }}%"></div>
 650 |     </div>
 651 | 
 652 |     <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem">
 653 |       <div class="halving-display">
 654 |         <div class="halving-blocks" aria-label="{{ '{:,}'.format(blocks_to_halving) }} blocks to next halving">{{ "{:,}".format(blocks_to_halving) }}</div>
 655 |         <div class="halving-sub">blocks to next halving · ~{{ days_to_halving }} days</div>
 656 |       </div>
 657 |       <div style="text-align:center;padding:1.5rem 0">
 658 |         <div class="label" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);">Sats Per Dollar</div>
 659 |         <div class="sats-display" id="sats-per-dollar">{{ "{:,}".format(sats_per_dollar) }}</div>
 660 |         <div style="font-size:11px;color:var(--muted);margin-top:.2rem;">1 USD = <span id="sats-per-dollar-val">{{ "{:,}".format(sats_per_dollar) }}</span> sats</div>
 661 |       </div>
 662 |     </div>
 663 | 
 664 |     <div style="margin-top:1rem;background:var(--panel-2);border:1px solid var(--border);border-radius:10px;padding:.8rem 1rem;">
 665 |       <div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:.4rem;">Lost Coins Estimate</div>
 666 |       <div style="font-size:13px;color:var(--muted);">~3.7–4M BTC estimated lost or dormant (Chainalysis 2024). Effective circulating supply closer to <strong style="color:var(--text);">~{{ "{:,.0f}".format(mined_supply - 3_800_000) }} BTC</strong>.</div>
 667 |     </div>
 668 |   </div>
 669 | 
 670 |   <!-- ── SECTION 6: HODL WAVES ─────────────────────────────────── -->
 671 |   <div class="section-header" id="section-hodl">
 672 |     <span class="section-kicker">Section 06 • Conviction</span>
 673 |     <h2 class="section-title">UTXO Age Distribution (HODL Waves)</h2>
 674 |   </div>
 675 |   <div class="chart-card">
 676 |     <div class="chart-card-header">
 677 |       <span class="chart-title">Estimated % of Supply by Last-Moved Age</span>
 678 |       <div class="chart-actions">
 679 |         <button class="btn-chip download-btn" onclick="downloadChart('hodl-canvas','HODL Waves')">↓ PNG</button>
 680 |       </div>
 681 |     </div>
 682 |     <div class="canvas-wrap" style="height:200px">
 683 |       <canvas id="hodl-canvas" height="200" aria-label="HODL Waves UTXO age distribution" role="img"></canvas>
 684 |     </div>
 685 |     <div class="hodl-legend" id="hodl-legend"></div>
 686 |     <div style="margin-top:.75rem;font-size:11px;color:var(--muted);">Estimated from on-chain analysis. Updated monthly. Source: Glassnode/Coin Metrics community estimates.</div>
 687 |   </div>
 688 | 
 689 |   <!-- ── SECTION 7: FEAR & GREED + VALUATION ───────────────────── -->
 690 |   <div class="section-header" id="section-valuation">
 691 |     <span class="section-kicker">Section 07 • Market Sentiment</span>
 692 |     <h2 class="section-title">Fear &amp; Greed + Valuation Metrics</h2>
 693 |   </div>
 694 |   <div class="two-col">
 695 |     <div class="chart-card">
 696 |       <div class="chart-card-header">
 697 |         <span class="chart-title">Fear &amp; Greed Index</span>
 698 |         <div class="chart-actions">
 699 |           <button class="btn-chip download-btn" onclick="downloadChart('fg-canvas','Fear Greed')">↓ PNG</button>
 700 |         </div>
 701 |       </div>
 702 |       <div class="canvas-wrap" style="height:160px">
 703 |         <canvas id="fg-canvas" height="160" aria-label="Fear and Greed index gauge" role="img"></canvas>
 704 |         <div class="chart-overlay" id="fg-loading">
 705 |           <div class="msg"><div class="spinner"></div>Loading…</div>
 706 |         </div>
 707 |       </div>
 708 |       <div class="fg-gauge-wrap" id="fg-stats" style="margin-top:.75rem;display:none">
 709 |         <div>
 710 |           <div class="fg-score" id="fg-score-val">—</div>
 711 |           <div class="fg-label" id="fg-label-val">—</div>
 712 |         </div>
 713 |         <div style="flex:1">
 714 |           <div class="canvas-wrap" style="height:40px"><canvas id="fg-sparkline" height="40" aria-label="7-day fear greed trend" role="img"></canvas></div>
 715 |           <div style="font-size:10px;color:var(--muted);margin-top:.3rem">7-day trend</div>
 716 |         </div>
 717 |       </div>
 718 |     </div>
 719 |     <div class="chart-card">
 720 |       <div class="chart-card-header">
 721 |         <span class="chart-title">Valuation Metrics</span>
 722 |       </div>
 723 |       <div id="valuation-metrics" style="display:flex;flex-direction:column;gap:.6rem;padding:.25rem 0"></div>
 724 |     </div>
 725 |   </div>
 726 | 
 727 |   <!-- ── SECTION 8: LIGHTNING NETWORK ──────────────────────────── -->
 728 |   <div class="section-header" id="section-lightning">
 729 |     <span class="section-kicker">Section 08 • Layer 2</span>
 730 |     <h2 class="section-title">Lightning Network</h2>
 731 |   </div>
 732 |   <div class="chart-card">
 733 |     <div class="chart-card-header">
 734 |       <span class="chart-title">Lightning Network Stats</span>
 735 |     </div>
 736 |     <div class="lightning-stats" id="lightning-stats">
 737 |       <div class="ln-stat"><div class="ln-label">Total Capacity</div><div class="ln-val" id="ln-capacity">—</div></div>
 738 |       <div class="ln-stat"><div class="ln-label">Node Count</div><div class="ln-val" id="ln-nodes">—</div></div>
 739 |       <div class="ln-stat"><div class="ln-label">Channel Count</div><div class="ln-val" id="ln-channels">—</div></div>
 740 |     </div>
 741 |     <div style="margin-top:1rem">
 742 |       <div class="canvas-wrap" style="height:100px">
 743 |         <canvas id="ln-canvas" height="100" aria-label="Lightning capacity trend" role="img"></canvas>
 744 |         <div class="chart-overlay" id="ln-loading"><div class="msg"><div class="spinner"></div>Loading…</div></div>
 745 |       </div>
 746 |     </div>
 747 |   </div>
 748 | 
 749 |   <!-- ── SECTION 9: PRICE ALERT ─────────────────────────────────── -->
 750 |   <div class="section-header" id="section-alerts">
 751 |     <span class="section-kicker">Section 09 • Alerts</span>
 752 |     <h2 class="section-title">Custom Price Alert</h2>
 753 |   </div>
 754 |   <div class="chart-card">
 755 |     <p style="color:var(--muted);font-size:14px;margin-bottom:.25rem">Get an email when BTC hits your target. Free. No account needed.</p>
 756 |     <div class="alert-form" id="alert-form">
 757 |       <input type="email" id="alert-email" placeholder="your@email.com" aria-label="Email address" autocomplete="email">
 758 |       <select id="alert-direction" aria-label="Alert direction">
 759 |         <option value="above">Above</option>
 760 |         <option value="below">Below</option>
 761 |       </select>
 762 |       <input type="number" id="alert-price" placeholder="e.g. 100000" min="1000" max="10000000" step="1000" aria-label="Target price in USD">
 763 |       <button class="btn-submit" onclick="submitAlert()" aria-label="Set price alert">SET ALERT</button>
 764 |     </div>
 765 |     <div class="alert-msg" id="alert-msg"></div>
 766 |   </div>
 767 | 
 768 | </div><!-- .charts-page -->
 769 | 
 770 | <!-- Embed modal -->
 771 | <div class="embed-modal" id="embed-modal" role="dialog" aria-modal="true" aria-label="Embed chart">
 772 |   <div class="embed-box">
 773 |     <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem">
 774 |       <span style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:800;letter-spacing:.14em;color:var(--gold);">EMBED CHART</span>
 775 |       <button onclick="closeEmbed()" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:18px;" aria-label="Close">×</button>
 776 |     </div>
 777 |     <div class="embed-code" id="embed-code-text"></div>
 778 |     <div style="display:flex;gap:.5rem">
 779 |       <button class="btn-chip" onclick="copyEmbed()" style="flex:1">Copy Code</button>
 780 |       <button class="btn-chip" onclick="closeEmbed()">Close</button>
 781 |     </div>
 782 |   </div>
 783 | </div>
 784 | 
 785 | <!-- Cmd+K command bar -->
 786 | <div class="cmdbar" id="cmdbar" role="dialog" aria-modal="true" aria-label="Quick navigation">
 787 |   <div class="cmdbar-inner">
 788 |     <input class="cmdbar-input" id="cmdbar-input" placeholder="Jump to section… (Esc to close)" aria-label="Quick navigation search">
 789 |     <div class="cmdbar-results" id="cmdbar-results"></div>
 790 |   </div>
 791 | </div>
 792 | {% endblock %}
 793 | 
 794 | {% block extra_js %}
 795 | <script>
 796 | // ═══════════════════════════════════════════════════════════════════════════
 797 | // PROTOCOL PULSE — ChartEngine (Pure Canvas, No Dependencies)
 798 | // ═══════════════════════════════════════════════════════════════════════════
 799 | 
 800 | const PP = {
 801 |   colors: {
 802 |     bg: '#06070b', panel: '#0d1118', text: '#eef2ff', muted: '#95a0ba',
 803 |     red: '#ff3b5f', gold: '#f8c15c', cyan: '#5de4ff', lime: '#89ffb8', coral: '#ff8ba0',
 804 |     border: 'rgba(255,255,255,0.07)'
 805 |   }
 806 | };
 807 | 
 808 | class ChartEngine {
 809 |   constructor(canvasId) {
 810 |     this.canvas = document.getElementById(canvasId);
 811 |     if (!this.canvas) return;
 812 |     this.ctx = this.canvas.getContext('2d');
 813 |     this._dpr = window.devicePixelRatio || 1;
 814 |     this._resize();
 815 |     window.addEventListener('resize', () => this._resize());
 816 |   }
 817 | 
 818 |   _resize() {
 819 |     if (!this.canvas) return;
 820 |     const rect = this.canvas.parentElement.getBoundingClientRect();
 821 |     const w = rect.width || 600;
 822 |     const h = parseInt(this.canvas.getAttribute('height')) || 200;
 823 |     this.canvas.width  = w * this._dpr;
 824 |     this.canvas.height = h * this._dpr;
 825 |     this.canvas.style.width  = w + 'px';
 826 |     this.canvas.style.height = h + 'px';
 827 |     this.ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
 828 |     this.W = w; this.H = h;
 829 |   }
 830 | 
 831 |   clear() {
 832 |     if (!this.ctx) return;
 833 |     this.ctx.clearRect(0, 0, this.W, this.H);
 834 |   }
 835 | 
 836 |   drawGrid(padL=60, padR=20, padT=20, padB=40, xCount=6, yCount=5) {
 837 |     const ctx = this.ctx;
 838 |     ctx.strokeStyle = 'rgba(255,255,255,0.04)';
 839 |     ctx.lineWidth = 0.5;
 840 |     const innerW = this.W - padL - padR;
 841 |     const innerH = this.H - padT - padB;
 842 |     for (let i = 0; i <= yCount; i++) {
 843 |       const y = padT + (i / yCount) * innerH;
 844 |       ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + innerW, y); ctx.stroke();
 845 |     }
 846 |     for (let i = 0; i <= xCount; i++) {
 847 |       const x = padL + (i / xCount) * innerW;
 848 |       ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + innerH); ctx.stroke();
 849 |     }
 850 |   }
 851 | 
 852 |   drawLine(points, color='#5de4ff', lineWidth=2, filled=false, fillColor=null, padL=60, padR=20, padT=20, padB=40) {
 853 |     if (!points || points.length < 2) return;
 854 |     const ctx = this.ctx;
 855 |     const innerW = this.W - padL - padR;
 856 |     const innerH = this.H - padT - padB;
 857 |     const vals = points.map(p => p[1]);
 858 |     const minV = Math.min(...vals), maxV = Math.max(...vals);
 859 |     const range = maxV - minV || 1;
 860 | 
 861 |     const toX = (i) => padL + (i / (points.length - 1)) * innerW;
 862 |     const toY = (v) => padT + innerH - ((v - minV) / range) * innerH;
 863 | 
 864 |     ctx.beginPath();
 865 |     ctx.moveTo(toX(0), toY(points[0][1]));
 866 |     for (let i = 1; i < points.length; i++) {
 867 |       ctx.lineTo(toX(i), toY(points[i][1]));
 868 |     }
 869 | 
 870 |     if (filled) {
 871 |       ctx.lineTo(toX(points.length - 1), padT + innerH);
 872 |       ctx.lineTo(padL, padT + innerH);
 873 |       ctx.closePath();
 874 |       const grad = ctx.createLinearGradient(0, padT, 0, padT + innerH);
 875 |       grad.addColorStop(0, fillColor || (color + '44'));
 876 |       grad.addColorStop(1, color + '00');
 877 |       ctx.fillStyle = grad;
 878 |       ctx.fill();
 879 |       ctx.beginPath();
 880 |       ctx.moveTo(toX(0), toY(points[0][1]));
 881 |       for (let i = 1; i < points.length; i++) ctx.lineTo(toX(i), toY(points[i][1]));
 882 |     }
 883 | 
 884 |     ctx.strokeStyle = color;
 885 |     ctx.lineWidth = lineWidth;
 886 |     ctx.lineJoin = 'round';
 887 |     ctx.stroke();
 888 |     return { toX, toY, minV, maxV, range, innerW, innerH, padL, padR, padT, padB };
 889 |   }
 890 | 
 891 |   drawYAxis(points, color='#95a0ba', padL=60, padR=20, padT=20, padB=40, fmt=null) {
 892 |     if (!points || points.length === 0) return;
 893 |     const ctx = this.ctx;
 894 |     const vals = points.map(p => p[1]);
 895 |     const minV = Math.min(...vals), maxV = Math.max(...vals);
 896 |     const range = maxV - minV || 1;
 897 |     const innerH = this.H - padT - padB;
 898 |     ctx.fillStyle = color;
 899 |     ctx.font = '9px JetBrains Mono, monospace';
 900 |     ctx.textAlign = 'right';
 901 |     const steps = 4;
 902 |     for (let i = 0; i <= steps; i++) {
 903 |       const v = minV + (i / steps) * range;
 904 |       const y = padT + innerH - (i / steps) * innerH;
 905 |       const label = fmt ? fmt(v) : _fmtNum(v);
 906 |       ctx.fillText(label, padL - 5, y + 3);
 907 |     }
 908 |   }
 909 | 
 910 |   drawXAxis(points, color='#95a0ba', padL=60, padR=20, padT=20, padB=40, fmt=null) {
 911 |     if (!points || points.length === 0) return;
 912 |     const ctx = this.ctx;
 913 |     const innerW = this.W - padL - padR;
 914 |     ctx.fillStyle = color;
 915 |     ctx.font = '9px JetBrains Mono, monospace';
 916 |     ctx.textAlign = 'center';
 917 |     const steps = Math.min(6, points.length - 1);
 918 |     for (let i = 0; i <= steps; i++) {
 919 |       const idx = Math.floor(i / steps * (points.length - 1));
 920 |       const x = padL + (idx / (points.length - 1)) * innerW;
 921 |       const label = fmt ? fmt(points[idx][0]) : _fmtDate(points[idx][0]);
 922 |       ctx.fillText(label, x, this.H - padB + 14);
 923 |     }
 924 |   }
 925 | 
 926 |   drawBar(points, color='#f8c15c', padL=60, padR=20, padT=20, padB=40) {
 927 |     if (!points || points.length === 0) return;
 928 |     const ctx = this.ctx;
 929 |     const innerW = this.W - padL - padR;
 930 |     const innerH = this.H - padT - padB;
 931 |     const vals = points.map(p => p[1]);
 932 |     const minV = 0, maxV = Math.max(...vals) || 1;
 933 |     const barW = Math.max(1, innerW / points.length - 1);
 934 |     const toY = (v) => padT + innerH - ((v - minV) / (maxV - minV)) * innerH;
 935 |     points.forEach((p, i) => {
 936 |       const x = padL + (i / (points.length - 1)) * innerW - barW / 2;
 937 |       const y = toY(p[1]);
 938 |       const grad = ctx.createLinearGradient(0, y, 0, padT + innerH);
 939 |       grad.addColorStop(0, color);
 940 |       grad.addColorStop(1, color + '33');
 941 |       ctx.fillStyle = grad;
 942 |       ctx.beginPath();
 943 |       ctx.roundRect ? ctx.roundRect(x, y, barW, padT + innerH - y, 2) : ctx.rect(x, y, barW, padT + innerH - y);
 944 |       ctx.fill();
 945 |     });
 946 |   }
 947 | 
 948 |   drawDonut(slices, padL=10, padR=10, padT=10, padB=10) {
 949 |     const ctx = this.ctx;
 950 |     const cx = this.W / 2, cy = this.H / 2;
 951 |     const r = Math.min(this.W, this.H) / 2 - 20;
 952 |     const inner = r * 0.55;
 953 |     let angle = -Math.PI / 2;
 954 |     const total = slices.reduce((s, sl) => s + sl.value, 0);
 955 |     slices.forEach(sl => {
 956 |       const sweep = (sl.value / total) * Math.PI * 2;
 957 |       ctx.beginPath();
 958 |       ctx.moveTo(cx, cy);
 959 |       ctx.arc(cx, cy, r, angle, angle + sweep);
 960 |       ctx.closePath();
 961 |       ctx.fillStyle = sl.color;
 962 |       ctx.fill();
 963 |       angle += sweep;
 964 |     });
 965 |     // Inner hole
 966 |     ctx.beginPath();
 967 |     ctx.arc(cx, cy, inner, 0, Math.PI * 2);
 968 |     ctx.fillStyle = PP.colors.panel;
 969 |     ctx.fill();
 970 |     // Center label
 971 |     ctx.fillStyle = PP.colors.text;
 972 |     ctx.font = 'bold 13px JetBrains Mono, monospace';
 973 |     ctx.textAlign = 'center';
 974 |     ctx.textBaseline = 'middle';
 975 |     ctx.fillText(slices.length + ' pools', cx, cy);
 976 |   }
 977 | 
 978 |   drawGauge(value, min=0, max=100, color='#f8c15c') {
 979 |     const ctx = this.ctx;
 980 |     const cx = this.W / 2, cy = this.H * 0.85;
 981 |     const r = Math.min(this.W / 2, this.H) * 0.8;
 982 |     const startA = Math.PI, endA = 2 * Math.PI;
 983 |     const sweep = (value - min) / (max - min);
 984 | 
 985 |     // Background arc
 986 |     ctx.beginPath();
 987 |     ctx.arc(cx, cy, r, startA, endA);
 988 |     ctx.strokeStyle = 'rgba(255,255,255,0.08)';
 989 |     ctx.lineWidth = 14;
 990 |     ctx.lineCap = 'round';
 991 |     ctx.stroke();
 992 | 
 993 |     // Value arc
 994 |     const zones = [
 995 |       { end: 25, color: '#ff3b5f' }, { end: 45, color: '#ff8ba0' },
 996 |       { end: 55, color: '#f8c15c' }, { end: 75, color: '#89ffb8' }, { end: 100, color: '#5de4ff' }
 997 |     ];
 998 |     let zone = zones.find(z => value <= z.end) || zones[zones.length - 1];
 999 |     ctx.beginPath();
1000 |     ctx.arc(cx, cy, r, startA, startA + sweep * Math.PI);
1001 |     ctx.strokeStyle = zone.color;
1002 |     ctx.lineWidth = 14;
1003 |     ctx.lineCap = 'round';
1004 |     ctx.stroke();
1005 | 
1006 |     // Value text
1007 |     ctx.fillStyle = zone.color;
1008 |     ctx.font = 'bold 28px JetBrains Mono, monospace';
1009 |     ctx.textAlign = 'center';
1010 |     ctx.textBaseline = 'bottom';
1011 |     ctx.fillText(value, cx, cy - 5);
1012 |   }
1013 | 
1014 |   drawSparkline(points, color='#f8c15c') {
1015 |     if (!points || points.length < 2) return;
1016 |     const vals = points.map(p => typeof p === 'number' ? p : p[1]);
1017 |     const min = Math.min(...vals), max = Math.max(...vals);
1018 |     const range = max - min || 1;
1019 |     const ctx = this.ctx, W = this.W, H = this.H;
1020 |     const toX = i => (i / (vals.length - 1)) * W;
1021 |     const toY = v => H - ((v - min) / range) * H * 0.8 - H * 0.1;
1022 |     ctx.beginPath();
1023 |     ctx.moveTo(toX(0), toY(vals[0]));
1024 |     vals.forEach((v, i) => { if (i > 0) ctx.lineTo(toX(i), toY(v)); });
1025 |     ctx.strokeStyle = color;
1026 |     ctx.lineWidth = 1.5;
1027 |     ctx.lineJoin = 'round';
1028 |     ctx.stroke();
1029 |   }
1030 | 
1031 |   drawCrosshair(x, y, color='rgba(255,255,255,0.2)') {
1032 |     const ctx = this.ctx;
1033 |     ctx.strokeStyle = color; ctx.lineWidth = 0.5; ctx.setLineDash([4,4]);
1034 |     ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,this.H); ctx.stroke();
1035 |     ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(this.W,y); ctx.stroke();
1036 |     ctx.setLineDash([]);
1037 |   }
1038 | 
1039 |   exportPNG(title='chart') {
1040 |     const tmpCanvas = document.createElement('canvas');
1041 |     tmpCanvas.width = this.canvas.width;
1042 |     tmpCanvas.height = this.canvas.height;
1043 |     const tCtx = tmpCanvas.getContext('2d');
1044 |     tCtx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
1045 |     tCtx.fillStyle = PP.colors.bg;
1046 |     tCtx.fillRect(0, 0, this.W, this.H);
1047 |     tCtx.drawImage(this.canvas, 0, 0, this.W, this.H);
1048 |     tCtx.fillStyle = 'rgba(248,193,92,0.6)';
1049 |     tCtx.font = '10px JetBrains Mono, monospace';
1050 |     tCtx.textAlign = 'right';
1051 |     tCtx.fillText('PROTOCOLPULSE.IO', this.W - 10, this.H - 8);
1052 |     const a = document.createElement('a');
1053 |     a.href = tmpCanvas.toDataURL('image/png');
1054 |     a.download = 'pp-' + title.toLowerCase().replace(/\s+/g,'-') + '-' + new Date().toISOString().slice(0,10) + '.png';
1055 |     a.click();
1056 |   }
1057 | }
1058 | 
1059 | // ── Helpers ──────────────────────────────────────────────────────────────────
1060 | function _fmtNum(v) {
1061 |   if (v >= 1e12) return (v/1e12).toFixed(1)+'T';
1062 |   if (v >= 1e9)  return (v/1e9).toFixed(1)+'B';
1063 |   if (v >= 1e6)  return (v/1e6).toFixed(1)+'M';
1064 |   if (v >= 1e3)  return (v/1e3).toFixed(1)+'K';
1065 |   return v.toFixed(v < 10 ? 2 : 0);
1066 | }
1067 | function _fmtDate(ts) {
1068 |   const d = new Date(ts);
1069 |   return (d.getMonth()+1) + '/' + d.getDate();
1070 | }
1071 | function _fmtDateShort(ts) {
1072 |   const d = new Date(ts);
1073 |   const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
1074 |   return months[d.getMonth()] + ' ' + d.getDate();
1075 | }
1076 | 
1077 | // ── State ─────────────────────────────────────────────────────────────────────
1078 | const state = {
1079 |   priceData: null, priceDays: 7,
1080 |   overlays: { ma200: true, bb: false, s2f: false, mayer: false },
1081 |   mempoolHistory: [],
1082 |   currentPriceForAlerts: {{ btc_price or 0 }},
1083 | };
1084 | 
1085 | // ── WebSocket — mempool.space ─────────────────────────────────────────────────
1086 | let ws, wsRetryDelay = 1000, wsRetryTimer = null;
1087 | function connectWS() {
1088 |   try {
1089 |     ws = new WebSocket('wss://mempool.space/api/v1/ws');
1090 |     ws.onopen = () => {
1091 |       wsRetryDelay = 1000;
1092 |       ws.send(JSON.stringify({action:'want', data:['stats','blocks']}));
1093 |       document.getElementById('ws-dot').classList.remove('red');
1094 |     };
1095 |     ws.onmessage = (e) => {
1096 |       try { handleWSMessage(JSON.parse(e.data)); } catch(_) {}
1097 |     };
1098 |     ws.onclose = ws.onerror = () => {
1099 |       document.getElementById('ws-dot').classList.add('red');
1100 |       clearTimeout(wsRetryTimer);
1101 |       wsRetryTimer = setTimeout(() => { wsRetryDelay = Math.min(wsRetryDelay * 2, 30000); connectWS(); }, wsRetryDelay);
1102 |     };
1103 |     // Heartbeat
1104 |     setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({action:'ping'})); }, 30000);
1105 |   } catch(e) { document.getElementById('ws-dot').classList.add('red'); }
1106 | }
1107 | 
1108 | function handleWSMessage(data) {
1109 |   if (data.mempoolInfo) {
1110 |     const mb = (data.mempoolInfo.usage / 1e6).toFixed(2);
1111 |     document.getElementById('stat-mempool').textContent = mb + ' MB';
1112 |     state.mempoolHistory.push([Date.now(), parseFloat(mb)]);
1113 |     if (state.mempoolHistory.length > 60) state.mempoolHistory.shift();
1114 |     drawMempoolChart();
1115 |   }
1116 |   if (data.fees) {
1117 |     document.getElementById('stat-fee').textContent = (data.fees.fastestFee || '?') + ' sat/vB';
1118 |     document.getElementById('fee-low').textContent    = data.fees.minimumFee || '—';
1119 |     document.getElementById('fee-mid').textContent    = data.fees.hourFee    || '—';
1120 |     document.getElementById('fee-high').textContent   = data.fees.halfHourFee|| '—';
1121 |     document.getElementById('fee-urgent').textContent = data.fees.fastestFee || '—';
1122 |   }
1123 |   if (data.block) {
1124 |     const h = data.block.height;
1125 |     if (h) document.getElementById('stat-height').textContent = h.toLocaleString();
1126 |   }
1127 | }
1128 | connectWS();
1129 | 
1130 | // ── Price Chart ───────────────────────────────────────────────────────────────
1131 | const priceEngine = new ChartEngine('price-canvas');
1132 | let _priceActiveDays = 7;
1133 | let _priceActiveBtns = null;
1134 | 
1135 | function loadPriceChart(days, btn) {
1136 |   _priceActiveDays = days;
1137 |   if (_priceActiveBtns) _priceActiveBtns.forEach(b => b.classList.remove('active'));
1138 |   if (btn) { btn.classList.add('active'); _priceActiveBtns = [btn]; }
1139 |   showLoading('price-loading', true);
1140 |   fetch('/api/charts/price-history?days=' + days)
1141 |     .then(r => r.ok ? r.json() : null)
1142 |     .then(data => {
1143 |       showLoading('price-loading', false);
1144 |       if (!data || !data.prices) { showError('price-loading'); return; }
1145 |       state.priceData = data.prices;
1146 |       drawPriceChart();
1147 |       // Update stat bar with last price + 24h change
1148 |       if (data.prices.length > 0) {
1149 |         const last = data.prices[data.prices.length - 1][1];
1150 |         state.currentPriceForAlerts = last;
1151 |         document.getElementById('stat-price').textContent = '$' + last.toLocaleString('en-US', {maximumFractionDigits:0});
1152 |         document.getElementById('sats-per-dollar').textContent = Math.round(1e8/last).toLocaleString();
1153 |         document.getElementById('sats-per-dollar-val').textContent = Math.round(1e8/last).toLocaleString();
1154 |         if (data.prices.length > 24) {
1155 |           const prev = data.prices[data.prices.length > 24 ? data.prices.length - 25 : 0][1];
1156 |           const pct = ((last - prev) / prev * 100).toFixed(2);
1157 |           const el = document.getElementById('stat-change');
1158 |           el.textContent = (pct >= 0 ? '+' : '') + pct + '%';
1159 |           el.className = 'value delta ' + (pct >= 0 ? 'delta-up' : 'delta-down');
1160 |           // Market cap
1161 |           const mcap = last * 19640000;
1162 |           document.getElementById('stat-mcap').textContent = '$' + _fmtNum(mcap);
1163 |         }
1164 |       }
1165 |     })
1166 |     .catch(() => { showLoading('price-loading', false); showError('price-loading'); });
1167 | }
1168 | 
1169 | function drawPriceChart() {
1170 |   if (!state.priceData) return;
1171 |   const pts = state.priceData;
1172 |   priceEngine._resize();
1173 |   priceEngine.clear();
1174 |   priceEngine.drawGrid();
1175 | 
1176 |   const vals = pts.map(p => p[1]);
1177 |   const minV = Math.min(...vals), maxV = Math.max(...vals);
1178 |   const padL=60, padR=20, padT=20, padB=40;
1179 | 
1180 |   // Price line (filled area)
1181 |   priceEngine.drawLine(pts, PP.colors.gold, 2, true, null, padL, padR, padT, padB);
1182 |   priceEngine.drawYAxis(pts, PP.colors.muted, padL, padR, padT, padB, v => '$' + _fmtNum(v));
1183 |   priceEngine.drawXAxis(pts, PP.colors.muted, padL, padR, padT, padB, ts => _fmtDateShort(ts));
1184 | 
1185 |   // 200D MA overlay
1186 |   if (state.overlays.ma200 && pts.length >= 200) {
1187 |     const maPts = _calcMA(pts, 200);
1188 |     drawOverlayLine(priceEngine, maPts, pts, PP.colors.gold + 'bb', 1.5, [6,4], padL, padR, padT, padB);
1189 |   }
1190 | 
1191 |   // Bollinger Bands
1192 |   if (state.overlays.bb && pts.length >= 20) {
1193 |     const { upper, lower } = _calcBollinger(pts, 20);
1194 |     drawOverlayLine(priceEngine, upper, pts, PP.colors.lime + '80', 1, [3,3], padL, padR, padT, padB);
1195 |     drawOverlayLine(priceEngine, lower, pts, PP.colors.coral + '80', 1, [3,3], padL, padR, padT, padB);
1196 |   }
1197 | 
1198 |   // Stock-to-Flow overlay
1199 |   if (state.overlays.s2f) {
1200 |     const s2fPts = _calcS2F(pts);
1201 |     drawOverlayLine(priceEngine, s2fPts, pts, PP.colors.cyan + 'aa', 1.5, [8,4], padL, padR, padT, padB);
1202 |   }
1203 | }
1204 | 
1205 | function drawOverlayLine(engine, overlayPts, refPts, color, lw, dash, padL, padR, padT, padB) {
1206 |   if (!overlayPts || overlayPts.length < 2) return;
1207 |   const ctx = engine.ctx;
1208 |   const vals = refPts.map(p => p[1]);
1209 |   const minV = Math.min(...vals), maxV = Math.max(...vals);
1210 |   const range = maxV - minV || 1;
1211 |   const innerW = engine.W - padL - padR;
1212 |   const innerH = engine.H - padT - padB;
1213 |   const toX = i => padL + (i / (refPts.length - 1)) * innerW;
1214 |   const toY = v => padT + innerH - ((v - minV) / range) * innerH;
1215 | 
1216 |   ctx.save();
1217 |   ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.setLineDash(dash);
1218 |   ctx.beginPath();
1219 |   overlayPts.forEach((v, i) => {
1220 |     const refIdx = refPts.length - overlayPts.length + i;
1221 |     if (v === null) return;
1222 |     const x = toX(refIdx), y = toY(v);
1223 |     if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
1224 |   });
1225 |   ctx.stroke();
1226 |   ctx.setLineDash([]); ctx.restore();
1227 | }
1228 | 
1229 | // ── RSI ───────────────────────────────────────────────────────────────────────
1230 | const rsiEngine = new ChartEngine('rsi-canvas');
1231 | function drawRSI() {
1232 |   if (!state.priceData || state.priceData.length < 15) return;
1233 |   const rsi = _calcRSI(state.priceData, 14);
1234 |   rsiEngine._resize(); rsiEngine.clear();
1235 |   const pts = rsi.map((v, i) => [state.priceData[state.priceData.length - rsi.length + i][0], v]);
1236 |   rsiEngine.drawGrid(40, 10, 5, 25, 6, 3);
1237 |   rsiEngine.drawLine(pts, PP.colors.cyan, 1.5, false, null, 40, 10, 5, 25);
1238 |   // Overbought/oversold lines
1239 |   const ctx = rsiEngine.ctx;
1240 |   const padL=40, padR=10, padT=5, padB=25;
1241 |   const innerH = rsiEngine.H - padT - padB;
1242 |   const toY = v => padT + innerH - ((v) / 100) * innerH;
1243 |   ctx.strokeStyle = 'rgba(255,59,95,0.4)'; ctx.lineWidth = 0.5; ctx.setLineDash([4,4]);
1244 |   ctx.beginPath(); ctx.moveTo(padL, toY(70)); ctx.lineTo(rsiEngine.W - padR, toY(70)); ctx.stroke();
1245 |   ctx.strokeStyle = 'rgba(137,255,184,0.4)';
1246 |   ctx.beginPath(); ctx.moveTo(padL, toY(30)); ctx.lineTo(rsiEngine.W - padR, toY(30)); ctx.stroke();
1247 |   ctx.setLineDash([]);
1248 |   ctx.fillStyle = PP.colors.muted; ctx.font = '9px JetBrains Mono,monospace'; ctx.textAlign = 'right';
1249 |   ctx.fillText('70', padL-3, toY(70)+3); ctx.fillText('30', padL-3, toY(30)+3);
1250 |   ctx.fillStyle = PP.colors.muted; ctx.textAlign = 'left'; ctx.font = '9px JetBrains Mono,monospace';
1251 |   const lastRSI = rsi[rsi.length-1];
1252 |   ctx.fillStyle = lastRSI > 70 ? PP.colors.coral : lastRSI < 30 ? PP.colors.lime : PP.colors.muted;
1253 |   ctx.fillText('RSI ' + lastRSI.toFixed(1), padL+4, padT+12);
1254 | }
1255 | 
1256 | // ── MACD ──────────────────────────────────────────────────────────────────────
1257 | const macdEngine = new ChartEngine('macd-canvas');
1258 | function drawMACD() {
1259 |   if (!state.priceData || state.priceData.length < 26) return;
1260 |   const { macdLine, signalLine, histogram } = _calcMACD(state.priceData);
1261 |   macdEngine._resize(); macdEngine.clear();
1262 |   const padL=40, padR=10, padT=5, padB=25;
1263 |   const histPts = histogram.map((v, i) => [i, v]);
1264 |   const allVals = [...macdLine, ...signalLine, ...histogram].filter(v => v !== null);
1265 |   const minV = Math.min(...allVals), maxV = Math.max(...allVals);
1266 |   const range = maxV - minV || 1;
1267 |   const innerW = macdEngine.W - padL - padR;
1268 |   const innerH = macdEngine.H - padT - padB;
1269 |   const toX = i => padL + (i / (histogram.length - 1)) * innerW;
1270 |   const toY = v => padT + innerH - ((v - minV) / range) * innerH;
1271 |   const ctx = macdEngine.ctx;
1272 |   // Histogram bars
1273 |   histogram.forEach((v, i) => {
1274 |     if (v === null) return;
1275 |     const x = toX(i), barW = Math.max(1, innerW/histogram.length - 1);
1276 |     ctx.fillStyle = v >= 0 ? PP.colors.lime + '88' : PP.colors.coral + '88';
1277 |     const y0 = toY(0), yv = toY(v);
1278 |     ctx.fillRect(x - barW/2, Math.min(y0,yv), barW, Math.abs(y0-yv));
1279 |   });
1280 |   // MACD line
1281 |   ctx.beginPath(); ctx.strokeStyle = PP.colors.cyan; ctx.lineWidth = 1.5;
1282 |   macdLine.forEach((v, i) => { if (v===null) return; const x=toX(i),y=toY(v); i===0?ctx.moveTo(x,y):ctx.lineTo(x,y); }); ctx.stroke();
1283 |   // Signal line
1284 |   ctx.beginPath(); ctx.strokeStyle = PP.colors.coral; ctx.lineWidth = 1;
1285 |   signalLine.forEach((v, i) => { if (v===null) return; const x=toX(i),y=toY(v); i===0?ctx.moveTo(x,y):ctx.lineTo(x,y); }); ctx.stroke();
1286 | }
1287 | 
1288 | // ── Hashrate Chart ────────────────────────────────────────────────────────────
1289 | const hashrateEngine = new ChartEngine('hashrate-canvas');
1290 | function loadHashrateChart() {
1291 |   fetch('/api/charts/hashrate-history')
1292 |     .then(r => r.ok ? r.json() : null)
1293 |     .then(data => {
1294 |       showLoading('hashrate-loading', false);
1295 |       if (!data || !data.hashrates) return;
1296 |       const pts = data.hashrates.map(h => [h.timestamp * 1000, h.avgHashrate / 1e18]);
1297 |       hashrateEngine._resize(); hashrateEngine.clear();
1298 |       hashrateEngine.drawGrid();
1299 |       hashrateEngine.drawLine(pts, PP.colors.cyan, 2, true, null, 60, 20, 20, 40);
1300 |       hashrateEngine.drawYAxis(pts, PP.colors.muted, 60, 20, 20, 40, v => v.toFixed(0)+' EH/s');
1301 |       hashrateEngine.drawXAxis(pts, PP.colors.muted, 60, 20, 20, 40, ts => _fmtDateShort(ts));
1302 |       // Draw difficulty epoch
1303 |       loadDifficultyDisplay(data);
1304 |     })
1305 |     .catch(() => showLoading('hashrate-loading', false));
1306 | }
1307 | 
1308 | function loadDifficultyDisplay(hrData) {
1309 |   const el = document.getElementById('difficulty-display');
1310 |   if (!el) return;
1311 |   const blockHeight = parseInt(document.getElementById('stat-height').textContent.replace(/,/g,'')) || {{ block_height or 0 }};
1312 |   const EPOCH = 210000;
1313 |   const DIFF_INTERVAL = 2016;
1314 |   const epochStart = Math.floor(blockHeight / DIFF_INTERVAL) * DIFF_INTERVAL;
1315 |   const blocksInEpoch = blockHeight - epochStart;
1316 |   const pct = (blocksInEpoch / DIFF_INTERVAL * 100).toFixed(1);
1317 |   const blocksLeft = DIFF_INTERVAL - blocksInEpoch;
1318 |   const daysLeft = (blocksLeft * 10 / 1440).toFixed(1);
1319 | 
1320 |   // Predict next difficulty adjustment
1321 |   let adjPct = 0, adjSign = '';
1322 |   if (hrData && hrData.hashrates && hrData.hashrates.length > 5) {
1323 |     const recent = hrData.hashrates.slice(-5).reduce((s,h) => s + h.avgHashrate, 0) / 5;
1324 |     const tenDay = 10 * 60 * blocksLeft; // target time for remaining blocks
1325 |     const actualBlockTime = (blocksInEpoch > 0) ? (Date.now()/1000 - hrData.hashrates[0]?.timestamp) / blocksInEpoch * 1000 : 600;
1326 |     adjPct = ((600 / (actualBlockTime || 600)) - 1) * 100;
1327 |     adjSign = adjPct >= 0 ? '+' : '';
1328 |   }
1329 | 
1330 |   el.innerHTML = `
1331 |     <div style="margin-bottom:.75rem">
1332 |       <div class="label" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:.4rem">Epoch Progress</div>
1333 |       <div class="supply-bar-wrap"><div class="supply-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,#5de4ff,#89ffb8)"></div></div>
1334 |       <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);margin-top:.3rem">${blocksInEpoch.toLocaleString()} / 2,016 blocks (${pct}%) · ${blocksLeft.toLocaleString()} left · ~${daysLeft} days</div>
1335 |     </div>
1336 |     <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
1337 |       <div style="background:var(--panel-2);border:1px solid var(--border);border-radius:10px;padding:.8rem">
1338 |         <div class="label" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)">Adj. Prediction</div>
1339 |         <div style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:900;color:${adjPct>=0?'var(--lime)':'var(--coral)'};margin-top:.2rem">${adjSign}${adjPct.toFixed(1)}%</div>
1340 |         <div style="font-size:11px;color:var(--muted)">estimated</div>
1341 |       </div>
1342 |       <div style="background:var(--panel-2);border:1px solid var(--border);border-radius:10px;padding:.8rem">
1343 |         <div class="label" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)">Next Adjustment</div>
1344 |         <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:900;color:var(--gold);margin-top:.2rem">~${daysLeft}d</div>
1345 |         <div style="font-size:11px;color:var(--muted)">${blocksLeft.toLocaleString()} blocks</div>
1346 |       </div>
1347 |     </div>`;
1348 | }
1349 | 
1350 | // ── Pool Distribution ─────────────────────────────────────────────────────────
1351 | const poolsEngine = new ChartEngine('pools-canvas');
1352 | const POOL_COLORS = ['#ff3b5f','#f8c15c','#5de4ff','#89ffb8','#ff8ba0','#b8a9ff','#ffd4a0','#a0d4ff','#d4ffa0','#ffa0d4','#c0c0c0'];
1353 | 
1354 | function loadPoolDistribution() {
1355 |   fetch('/api/charts/pool-distribution')
1356 |     .then(r => r.ok ? r.json() : null)
1357 |     .then(data => {
1358 |       showLoading('pools-loading', false);
1359 |       if (!data || !data.pools) return;
1360 |       const pools = data.pools.slice(0, 10);
1361 |       const slices = pools.map((p, i) => ({ label: p.name, value: p.blockCount, color: POOL_COLORS[i % POOL_COLORS.length] }));
1362 |       poolsEngine._resize(); poolsEngine.clear();
1363 |       poolsEngine.drawDonut(slices);
1364 |       // Table
1365 |       const total = pools.reduce((s, p) => s + p.blockCount, 0);
1366 |       const top3Pct = pools.slice(0,3).reduce((s,p) => s + p.blockCount, 0) / total * 100;
1367 |       let tableHtml = '<table class="pool-table"><thead><tr><th>Pool</th><th>Blocks</th><th>Share</th></tr></thead><tbody>';
1368 |       pools.forEach((p, i) => {
1369 |         const pct = (p.blockCount / total * 100).toFixed(1);
1370 |         tableHtml += `<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${POOL_COLORS[i]};margin-right:6px;"></span>${p.name}</td><td>${p.blockCount}</td><td style="color:var(--gold)">${pct}%</td></tr>`;
1371 |       });
1372 |       // HHI
1373 |       const hhi = pools.reduce((s, p) => s + Math.pow(p.blockCount/total*100, 2), 0);
1374 |       tableHtml += `</tbody></table><div style="margin-top:.5rem;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted)">HHI Score: <span style="color:${hhi>2500?'var(--coral)':hhi>1500?'var(--gold)':'var(--lime)'}">${Math.round(hhi)}</span> ${hhi>2500?'(High concentration)':hhi>1500?'(Moderate)':'(Healthy)'}</div>`;
1375 |       document.getElementById('pool-table-wrap').innerHTML = tableHtml;
1376 |       if (top3Pct > 50) document.getElementById('hhi-warn').classList.add('visible');
1377 |     })
1378 |     .catch(() => showLoading('pools-loading', false));
1379 | }
1380 | 
1381 | // ── Mempool Chart ─────────────────────────────────────────────────────────────
1382 | const mempoolEngine = new ChartEngine('mempool-canvas');
1383 | function drawMempoolChart() {
1384 |   if (state.mempoolHistory.length < 2) return;
1385 |   mempoolEngine._resize(); mempoolEngine.clear();
1386 |   mempoolEngine.drawGrid(50, 20, 10, 30, 6, 4);
1387 |   mempoolEngine.drawLine(state.mempoolHistory, PP.colors.red, 2, true, null, 50, 20, 10, 30);
1388 | }
1389 | 
1390 | // ── HODL Waves ────────────────────────────────────────────────────────────────
1391 | const hodlEngine = new ChartEngine('hodl-canvas');
1392 | const HODL_DATA = [
1393 |   { label: '< 1 Day',   pct: 0.8,  color: '#ff3b5f' },
1394 |   { label: '1d–1w',     pct: 2.1,  color: '#ff8ba0' },
1395 |   { label: '1w–1m',     pct: 3.4,  color: '#f8c15c' },
1396 |   { label: '1m–3m',     pct: 6.2,  color: '#ffd080' },
1397 |   { label: '3m–6m',     pct: 7.8,  color: '#89ffb8' },
1398 |   { label: '6m–1y',     pct: 9.5,  color: '#5de4ff' },
1399 |   { label: '1y–2y',     pct: 15.2, color: '#b8a9ff' },
1400 |   { label: '2y–3y',     pct: 11.3, color: '#a0d4ff' },
1401 |   { label: '3y–5y',     pct: 14.6, color: '#ffa0d4' },
1402 |   { label: '5y+',       pct: 29.1, color: '#c0a0ff' },
1403 | ];
1404 | 
1405 | function drawHODLWaves() {
1406 |   hodlEngine._resize(); hodlEngine.clear();
1407 |   const ctx = hodlEngine.ctx;
1408 |   const W = hodlEngine.W, H = hodlEngine.H;
1409 |   const padL = 10, padR = 10, padT = 10, padB = 30;
1410 |   const innerW = W - padL - padR;
1411 |   const innerH = H - padT - padB;
1412 |   const total = HODL_DATA.reduce((s, d) => s + d.pct, 0);
1413 |   let x = padL;
1414 |   HODL_DATA.forEach(d => {
1415 |     const w = (d.pct / total) * innerW;
1416 |     const grad = ctx.createLinearGradient(0, padT, 0, padT + innerH);
1417 |     grad.addColorStop(0, d.color);
1418 |     grad.addColorStop(1, d.color + '44');
1419 |     ctx.fillStyle = grad;
1420 |     ctx.fillRect(x, padT, w, innerH);
1421 |     if (w > 30) {
1422 |       ctx.fillStyle = 'rgba(0,0,0,0.6)';
1423 |       ctx.font = `bold ${Math.min(10, w/4)}px JetBrains Mono,monospace`;
1424 |       ctx.textAlign = 'center';
1425 |       ctx.fillText(d.pct + '%', x + w/2, padT + innerH/2 + 4);
1426 |     }
1427 |     x += w;
1428 |   });
1429 |   // Legend
1430 |   const legendEl = document.getElementById('hodl-legend');
1431 |   legendEl.innerHTML = HODL_DATA.map(d => `<div class="hodl-legend-item"><span class="hodl-legend-swatch" style="background:${d.color}"></span>${d.label} (${d.pct}%)</div>`).join('');
1432 | }
1433 | 
1434 | // ── Fear & Greed ──────────────────────────────────────────────────────────────
1435 | const fgEngine = new ChartEngine('fg-canvas');
1436 | const fgSparkEngine = new ChartEngine('fg-sparkline');
1437 | 
1438 | function loadFearGreed() {
1439 |   fetch('/api/charts/fear-greed')
1440 |     .then(r => r.ok ? r.json() : null)
1441 |     .then(data => {
1442 |       showLoading('fg-loading', false);
1443 |       if (!data || !data.data || data.data.length === 0) return;
1444 |       document.getElementById('fg-stats').style.display = 'flex';
1445 |       const latest = data.data[0];
1446 |       const score = parseInt(latest.value);
1447 |       document.getElementById('fg-score-val').textContent = score;
1448 |       document.getElementById('fg-score-val').style.color = _fgColor(score);
1449 |       document.getElementById('fg-label-val').textContent = latest.value_classification;
1450 |       fgEngine._resize(); fgEngine.clear();
1451 |       fgEngine.drawGauge(score, 0, 100);
1452 |       // Sparkline
1453 |       const sparkVals = data.data.slice(0,7).reverse().map(d => parseInt(d.value));
1454 |       fgSparkEngine._resize(); fgSparkEngine.clear();
1455 |       fgSparkEngine.drawSparkline(sparkVals, PP.colors.gold);
1456 |     })
1457 |     .catch(() => showLoading('fg-loading', false));
1458 | }
1459 | 
1460 | function _fgColor(v) {
1461 |   if (v <= 25) return PP.colors.red;
1462 |   if (v <= 45) return PP.colors.coral;
1463 |   if (v <= 55) return PP.colors.gold;
1464 |   if (v <= 75) return PP.colors.lime;
1465 |   return PP.colors.cyan;
1466 | }
1467 | 
1468 | // ── Valuation Metrics ─────────────────────────────────────────────────────────
1469 | function renderValuationMetrics() {
1470 |   const el = document.getElementById('valuation-metrics');
1471 |   if (!el || !state.priceData || state.priceData.length < 200) {
1472 |     if (el) el.innerHTML = '<div style="color:var(--muted);font-size:12px;">Load 1Y price data to see valuation metrics</div>';
1473 |     return;
1474 |   }
1475 |   const prices = state.priceData.map(p => p[1]);
1476 |   const currentPrice = prices[prices.length - 1];
1477 |   const ma200 = prices.length >= 200 ? prices.slice(-200).reduce((s,v) => s+v, 0) / 200 : null;
1478 |   const mayer = ma200 ? (currentPrice / ma200) : null;
1479 |   // S2F model price estimate (simplified)
1480 |   const blockHeight = {{ block_height or 840000 }};
1481 |   const epochNum = Math.floor(blockHeight / 210000);
1482 |   const subsidy = 50 / Math.pow(2, epochNum);
1483 |   const annualIssuance = subsidy * 52560;
1484 |   const currentSupply = {{ mined_supply }};
1485 |   const s2fRatio = currentSupply / annualIssuance;
1486 |   const s2fModelPrice = Math.exp(3.31819 * Math.log(s2fRatio) + 14.6227);
1487 |   // NUPL approx
1488 |   const realizedCapEst = currentSupply * currentPrice * 0.65; // rough estimate
1489 |   const marketCap = currentSupply * currentPrice;
1490 |   const nupl = (marketCap - realizedCapEst) / marketCap;
1491 | 
1492 |   const metrics = [
1493 |     {
1494 |       label: 'Mayer Multiple',
1495 |       value: mayer ? mayer.toFixed(2) : '—',
1496 |       color: mayer ? (mayer > 2.4 ? PP.colors.coral : mayer < 1.0 ? PP.colors.lime : PP.colors.gold) : PP.colors.muted,
1497 |       note: mayer ? (mayer > 2.4 ? 'Historically overbought (>2.4)' : mayer < 1.0 ? 'Historically undervalued (<1.0)' : 'Fair value zone (1.0–2.4)') : 'Need 200d data',
1498 |     },
1499 |     {
1500 |       label: 'Stock-to-Flow Ratio',
1501 |       value: s2fRatio.toFixed(1),
1502 |       color: PP.colors.cyan,
1503 |       note: 'S2F model price: $' + Math.round(s2fModelPrice).toLocaleString(),
1504 |     },
1505 |     {
1506 |       label: 'NUPL (estimated)',
1507 |       value: (nupl * 100).toFixed(1) + '%',
1508 |       color: nupl > 0.75 ? PP.colors.coral : nupl > 0.5 ? PP.colors.gold : nupl > 0 ? PP.colors.lime : PP.colors.red,
1509 |       note: nupl > 0.75 ? 'Euphoria zone' : nupl > 0.5 ? 'Belief zone' : nupl > 0.25 ? 'Optimism zone' : 'Hope/Fear zone',
1510 |     },
1511 |   ];
1512 | 
1513 |   el.innerHTML = metrics.map(m => `
1514 |     <div style="background:var(--panel-2);border:1px solid var(--border);border-radius:10px;padding:.75rem 1rem;display:flex;justify-content:space-between;align-items:center">
1515 |       <div>
1516 |         <div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:.15em;text-transform:uppercase;color:var(--muted)">${m.label}</div>
1517 |         <div style="font-size:10px;color:var(--muted);margin-top:.15rem">${m.note}</div>
1518 |       </div>
1519 |       <div style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:900;color:${m.color}">${m.value}</div>
1520 |     </div>`).join('');
1521 | }
1522 | 
1523 | // ── Lightning Stats ───────────────────────────────────────────────────────────
1524 | const lnEngine = new ChartEngine('ln-canvas');
1525 | function loadLightning() {
1526 |   fetch('/api/charts/lightning')
1527 |     .then(r => r.ok ? r.json() : null)
1528 |     .then(data => {
1529 |       showLoading('ln-loading', false);
1530 |       if (!data) return;
1531 |       const latest = data.latest || data;
1532 |       if (latest.total_capacity != null) {
1533 |         document.getElementById('ln-capacity').textContent = (latest.total_capacity / 1e8).toFixed(0) + ' BTC';
1534 |       }
1535 |       if (latest.node_count != null) {
1536 |         document.getElementById('ln-nodes').textContent = latest.node_count.toLocaleString();
1537 |       }
1538 |       if (latest.channel_count != null) {
1539 |         document.getElementById('ln-channels').textContent = latest.channel_count.toLocaleString();
1540 |       }
1541 |       // Capacity trend
1542 |       if (data.channel_count && Array.isArray(data.channel_count)) {
1543 |         const pts = data.channel_count.slice(-30).map(d => [d[0]*1000, d[1]]);
1544 |         lnEngine._resize(); lnEngine.clear();
1545 |         lnEngine.drawGrid(50, 10, 5, 25, 6, 3);
1546 |         lnEngine.drawBar(pts, PP.colors.cyan, 50, 10, 5, 25);
1547 |         lnEngine.drawYAxis(pts, PP.colors.muted, 50, 10, 5, 25, v => _fmtNum(v));
1548 |       }
1549 |     })
1550 |     .catch(() => showLoading('ln-loading', false));
1551 | }
1552 | 
1553 | // ── Indicator Math ────────────────────────────────────────────────────────────
1554 | function _calcMA(pts, period) {
1555 |   const result = [];
1556 |   for (let i = 0; i < pts.length; i++) {
1557 |     if (i < period - 1) { result.push(null); continue; }
1558 |     const slice = pts.slice(i - period + 1, i + 1);
1559 |     result.push(slice.reduce((s, p) => s + p[1], 0) / period);
1560 |   }
1561 |   return result.slice(period - 1);
1562 | }
1563 | 
1564 | function _calcEMA(vals, period) {
1565 |   const k = 2 / (period + 1);
1566 |   const result = [vals[0]];
1567 |   for (let i = 1; i < vals.length; i++) {
1568 |     result.push(vals[i] * k + result[i-1] * (1 - k));
1569 |   }
1570 |   return result;
1571 | }
1572 | 
1573 | function _calcBollinger(pts, period=20, stdMult=2) {
1574 |   const upper = [], lower = [];
1575 |   for (let i = 0; i < pts.length; i++) {
1576 |     if (i < period - 1) { upper.push(null); lower.push(null); continue; }
1577 |     const slice = pts.slice(i - period + 1, i + 1).map(p => p[1]);
1578 |     const mean = slice.reduce((s,v) => s+v, 0) / period;
1579 |     const std  = Math.sqrt(slice.reduce((s,v) => s + Math.pow(v-mean,2), 0) / period);
1580 |     upper.push(mean + stdMult * std);
1581 |     lower.push(mean - stdMult * std);
1582 |   }
1583 |   return { upper: upper.filter(v=>v!==null), lower: lower.filter(v=>v!==null) };
1584 | }
1585 | 
1586 | function _calcRSI(pts, period=14) {
1587 |   const closes = pts.map(p => p[1]);
1588 |   const gains = [], losses = [];
1589 |   for (let i = 1; i < closes.length; i++) {
1590 |     const diff = closes[i] - closes[i-1];
1591 |     gains.push(Math.max(0, diff)); losses.push(Math.max(0, -diff));
1592 |   }
1593 |   const rsi = [];
1594 |   let avgGain = gains.slice(0, period).reduce((s,v) => s+v, 0) / period;
1595 |   let avgLoss = losses.slice(0, period).reduce((s,v) => s+v, 0) / period;
1596 |   for (let i = period; i < gains.length; i++) {
1597 |     avgGain = (avgGain * (period - 1) + gains[i]) / period;
1598 |     avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
1599 |     const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
1600 |     rsi.push(100 - (100 / (1 + rs)));
1601 |   }
1602 |   return rsi;
1603 | }
1604 | 
1605 | function _calcMACD(pts, fast=12, slow=26, signal=9) {
1606 |   const closes = pts.map(p => p[1]);
1607 |   const emaFast = _calcEMA(closes, fast);
1608 |   const emaSlow = _calcEMA(closes, slow);
1609 |   const macdLine = emaFast.map((v, i) => v - emaSlow[i]);
1610 |   const startIdx = slow - 1;
1611 |   const macdTrimmed = macdLine.slice(startIdx);
1612 |   const signalLine = _calcEMA(macdTrimmed, signal);
1613 |   const histogram = macdTrimmed.slice(signal - 1).map((v, i) => v - signalLine[i]);
1614 |   return { macdLine: macdLine.slice(startIdx + signal - 1), signalLine: signalLine.slice(signal - 1), histogram };
1615 | }
1616 | 
1617 | function _calcS2F(pts) {
1618 |   // Approximate S2F model price as overlay — uses approximate epoch schedule
1619 |   const blockHeight = {{ block_height or 840000 }};
1620 |   const epochs = Math.floor(blockHeight / 210000);
1621 |   const subsidy = 50 / Math.pow(2, epochs);
1622 |   const annIssuance = subsidy * 52560;
1623 |   const supply = {{ mined_supply }};
1624 |   const sf = supply / annIssuance;
1625 |   const modelPrice = Math.exp(3.31819 * Math.log(sf) + 14.6227);
1626 |   // Return constant horizontal line at model price
1627 |   return pts.map(() => modelPrice);
1628 | }
1629 | 
1630 | // ── Overlay toggle ────────────────────────────────────────────────────────────
1631 | function toggleOverlay(key, el) {
1632 |   state.overlays[key] = el.checked;
1633 |   el.closest('.toggle-chip').classList.toggle('active', el.checked);
1634 |   drawPriceChart();
1635 | }
1636 | 
1637 | // ── AI Interpret ──────────────────────────────────────────────────────────────
1638 | function interpretChart(chartType, label) {
1639 |   const aiBox = document.getElementById('ai-' + chartType);
1640 |   const aiText = document.getElementById('ai-' + chartType + '-text');
1641 |   if (!aiBox || !aiText) return;
1642 |   aiBox.classList.add('visible');
1643 |   aiText.textContent = 'Analyzing market structure…';
1644 |   const chartData = {};
1645 |   if (chartType === 'price' && state.priceData && state.priceData.length > 0) {
1646 |     const prices = state.priceData.map(p => p[1]);
1647 |     chartData.current_price = prices[prices.length - 1];
1648 |     chartData.period_high = Math.max(...prices);
1649 |     chartData.period_low = Math.min(...prices);
1650 |     chartData.price_change_pct = ((prices[prices.length-1] - prices[0]) / prices[0] * 100).toFixed(2);
1651 |     chartData.data_points = state.priceData.length;
1652 |     chartData.days = _priceActiveDays;
1653 |   }
1654 |   fetch('/api/charts/ai-explain', {
1655 |     method: 'POST',
1656 |     headers: {'Content-Type': 'application/json'},
1657 |     body: JSON.stringify({ chart_type: chartType, chart_data: chartData, question: 'Explain this chart' })
1658 |   })
1659 |   .then(r => r.json())
1660 |   .then(d => {
1661 |     aiText.textContent = d.explanation || 'Analysis unavailable.';
1662 |     // Typewriter effect
1663 |     const text = d.explanation || '';
1664 |     aiText.textContent = '';
1665 |     let i = 0;
1666 |     const timer = setInterval(() => {
1667 |       if (i < text.length) { aiText.textContent += text[i++]; } else { clearInterval(timer); }
1668 |     }, 18);
1669 |   })
1670 |   .catch(() => { aiText.textContent = 'AI analysis temporarily unavailable.'; });
1671 | }
1672 | 
1673 | // ── Download PNG ──────────────────────────────────────────────────────────────
1674 | function downloadChart(canvasId, title) {
1675 |   const engines = {
1676 |     'price-canvas': priceEngine, 'hashrate-canvas': hashrateEngine,
1677 |     'pools-canvas': poolsEngine, 'mempool-canvas': mempoolEngine,
1678 |     'hodl-canvas': hodlEngine, 'fg-canvas': fgEngine
1679 |   };
1680 |   const engine = engines[canvasId];
1681 |   if (engine) engine.exportPNG(title);
1682 | }
1683 | 
1684 | // ── Embed ─────────────────────────────────────────────────────────────────────
1685 | function openEmbed(chartId) {
1686 |   const code = `<iframe src="https://protocolpulse.io/charts/embed/${chartId}?days=7" width="600" height="360" frameborder="0" style="border-radius:12px" title="Bitcoin ${chartId} chart — Protocol Pulse"></iframe>`;
1687 |   document.getElementById('embed-code-text').textContent = code;
1688 |   document.getElementById('embed-modal').classList.add('open');
1689 | }
1690 | function closeEmbed() { document.getElementById('embed-modal').classList.remove('open'); }
1691 | function copyEmbed() {
1692 |   navigator.clipboard.writeText(document.getElementById('embed-code-text').textContent)
1693 |     .then(() => { const b = event.target; b.textContent = 'Copied!'; setTimeout(() => b.textContent = 'Copy Code', 2000); });
1694 | }
1695 | 
1696 | // ── Price Alert ───────────────────────────────────────────────────────────────
1697 | function submitAlert() {
1698 |   const email = document.getElementById('alert-email').value.trim();
1699 |   const dir   = document.getElementById('alert-direction').value;
1700 |   const price = document.getElementById('alert-price').value;
1701 |   const msgEl = document.getElementById('alert-msg');
1702 |   if (!email || !price) { msgEl.className = 'alert-msg err'; msgEl.textContent = 'Please fill in all fields.'; return; }
1703 |   msgEl.className = 'alert-msg'; msgEl.textContent = 'Setting alert…';
1704 |   fetch('/api/charts/price-alert', {
1705 |     method: 'POST',
1706 |     headers: {'Content-Type': 'application/json'},
1707 |     body: JSON.stringify({ email, direction: dir, target_price: parseFloat(price) })
1708 |   })
1709 |   .then(r => r.json())
1710 |   .then(d => {
1711 |     if (d.success) {
1712 |       msgEl.className = 'alert-msg ok';
1713 |       msgEl.textContent = '✓ ' + d.message;
1714 |       document.getElementById('alert-price').value = '';
1715 |     } else {
1716 |       msgEl.className = 'alert-msg err';
1717 |       msgEl.textContent = d.error || 'Error setting alert.';
1718 |     }
1719 |   })
1720 |   .catch(() => { msgEl.className = 'alert-msg err'; msgEl.textContent = 'Network error. Please try again.'; });
1721 | }
1722 | 
1723 | // ── Cmd+K Command Bar ─────────────────────────────────────────────────────────
1724 | const CMD_SECTIONS = [
1725 |   { key: 'PRICE',    label: 'BTC Price Chart', id: 'section-price' },
1726 |   { key: 'MINING',   label: 'Hashrate & Difficulty', id: 'section-mining' },
1727 |   { key: 'POOLS',    label: 'Mining Pool Distribution', id: 'section-pools' },
1728 |   { key: 'MEMPOOL',  label: 'Mempool & Fees', id: 'section-mempool' },
1729 |   { key: 'SUPPLY',   label: 'Supply Analysis', id: 'section-supply' },
1730 |   { key: 'HODL',     label: 'HODL Waves', id: 'section-hodl' },
1731 |   { key: 'SENTIMENT',label: 'Fear & Greed / Valuation', id: 'section-valuation' },
1732 |   { key: 'LIGHTNING',label: 'Lightning Network', id: 'section-lightning' },
1733 |   { key: 'ALERTS',   label: 'Price Alerts', id: 'section-alerts' },
1734 | ];
1735 | 
1736 | function openCmdBar() {
1737 |   document.getElementById('cmdbar').classList.add('open');
1738 |   document.getElementById('cmdbar-input').value = '';
1739 |   renderCmdResults('');
1740 |   setTimeout(() => document.getElementById('cmdbar-input').focus(), 50);
1741 | }
1742 | function closeCmdBar() { document.getElementById('cmdbar').classList.remove('open'); }
1743 | 
1744 | function renderCmdResults(q) {
1745 |   const filtered = CMD_SECTIONS.filter(s => !q || s.label.toLowerCase().includes(q.toLowerCase()) || s.key.toLowerCase().includes(q.toLowerCase()));
1746 |   document.getElementById('cmdbar-results').innerHTML = filtered.map(s =>
1747 |     `<div class="cmdbar-item" onclick="scrollToSection('${s.id}'); closeCmdBar();" tabindex="0" role="button" aria-label="Go to ${s.label}">
1748 |       <span class="cmdbar-item-key">${s.key}</span>
1749 |       <span>${s.label}</span>
1750 |     </div>`).join('');
1751 | }
1752 | 
1753 | function scrollToSection(id) {
1754 |   const el = document.getElementById(id);
1755 |   if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
1756 | }
1757 | 
1758 | document.getElementById('cmdbar-input').addEventListener('input', e => renderCmdResults(e.target.value));
1759 | document.getElementById('cmdbar').addEventListener('click', e => { if (e.target === e.currentTarget) closeCmdBar(); });
1760 | document.getElementById('embed-modal').addEventListener('click', e => { if (e.target === e.currentTarget) closeEmbed(); });
1761 | 
1762 | // Keyboard shortcuts
1763 | document.addEventListener('keydown', e => {
1764 |   if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openCmdBar(); }
1765 |   if (e.key === 'Escape') { closeCmdBar(); closeEmbed(); }
1766 | });
1767 | 
1768 | // ── Utility ───────────────────────────────────────────────────────────────────
1769 | function showLoading(id, show) {
1770 |   const el = document.getElementById(id);
1771 |   if (!el) return;
1772 |   el.style.display = show ? 'flex' : 'none';
1773 | }
1774 | function showError(id) {
1775 |   const el = document.getElementById(id);
1776 |   if (!el) return;
1777 |   el.style.display = 'flex';
1778 |   const msg = el.querySelector('.msg');
1779 |   if (msg) msg.innerHTML = '<span style="color:var(--coral)">Data unavailable</span>';
1780 | }
1781 | 
1782 | // ── Periodic price refresh ─────────────────────────────────────────────────────
1783 | function refreshPrice() {
1784 |   fetch('/api/charts/price-history?days=1')
1785 |     .then(r => r.ok ? r.json() : null)
1786 |     .then(data => {
1787 |       if (!data || !data.prices || data.prices.length === 0) return;
1788 |       const p = data.prices[data.prices.length - 1][1];
1789 |       state.currentPriceForAlerts = p;
1790 |       document.getElementById('stat-price').textContent = '$' + p.toLocaleString('en-US', {maximumFractionDigits:0});
1791 |       document.getElementById('sats-per-dollar').textContent = Math.round(1e8/p).toLocaleString();
1792 |       document.getElementById('sats-per-dollar-val').textContent = Math.round(1e8/p).toLocaleString();
1793 |     }).catch(() => {});
1794 | }
1795 | setInterval(refreshPrice, 30000);
1796 | 
1797 | // ── Bootstrap all charts on page load ────────────────────────────────────────
1798 | document.addEventListener('DOMContentLoaded', () => {
1799 |   loadPriceChart(7, document.querySelector('[data-tf="7"]'));
1800 |   loadHashrateChart();
1801 |   loadPoolDistribution();
1802 |   loadFearGreed();
1803 |   loadLightning();
1804 |   drawHODLWaves();
1805 |   setTimeout(renderValuationMetrics, 3000); // wait for price data
1806 | });
1807 | window.addEventListener('resize', () => {
1808 |   if (state.priceData) drawPriceChart();
1809 |   drawHODLWaves();
1810 | });
1811 | </script>
1812 | {% endblock %}
1813 | 
```

### File: core/templates/charts_embed.html (159 lines)
```
   1 | <!DOCTYPE html>
   2 | <html lang="en">
   3 | <head>
   4 | <meta charset="UTF-8">
   5 | <meta name="viewport" content="width=device-width, initial-scale=1.0">
   6 | <title>Bitcoin {{ chart_id|title }} Chart — Protocol Pulse</title>
   7 | <style>
   8 |   * { margin: 0; padding: 0; box-sizing: border-box; }
   9 |   body { background: #06070b; color: #eef2ff; font-family: 'JetBrains Mono', monospace; overflow: hidden; }
  10 |   canvas { display: block; width: 100% !important; }
  11 |   .embed-wrap { position: relative; width: 100vw; height: 100vh; padding: 16px; }
  12 |   .embed-title { font-size: 10px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; color: #95a0ba; margin-bottom: 8px; }
  13 |   .embed-footer { position: absolute; bottom: 8px; right: 12px; font-size: 9px; color: rgba(248,193,92,0.5); letter-spacing: .1em; }
  14 |   .embed-footer a { color: inherit; text-decoration: none; }
  15 |   .loading { display: flex; align-items: center; justify-content: center; height: 80%; color: #95a0ba; font-size: 12px; }
  16 |   .spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.08); border-top-color: #f8c15c; border-radius: 50%; animation: spin .8s linear infinite; margin-right: 8px; }
  17 |   @keyframes spin { to { transform: rotate(360deg); } }
  18 | </style>
  19 | <link rel="preconnect" href="https://fonts.googleapis.com">
  20 | <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;900&display=swap" rel="stylesheet">
  21 | </head>
  22 | <body>
  23 | <div class="embed-wrap">
  24 |   <div class="embed-title">
  25 |     {% if chart_id == 'price' %}BTC / USD — {{ days }}D Price Chart
  26 |     {% elif chart_id == 'hashrate' %}Bitcoin Network Hashrate
  27 |     {% elif chart_id == 'mempool' %}Mempool Size (MB)
  28 |     {% elif chart_id == 'pools' %}Mining Pool Distribution
  29 |     {% elif chart_id == 'fear-greed' %}Fear &amp; Greed Index
  30 |     {% endif %}
  31 |   </div>
  32 |   <div id="loading" class="loading"><div class="spinner"></div>Loading…</div>
  33 |   <canvas id="embed-canvas" style="display:none"></canvas>
  34 |   <div class="embed-footer"><a href="https://protocolpulse.io/charts" target="_blank" rel="noopener">PROTOCOLPULSE.IO</a></div>
  35 | </div>
  36 | 
  37 | <script>
  38 | const CHART = '{{ chart_id }}';
  39 | const DAYS  = {{ days }};
  40 | const C     = { gold:'#f8c15c', cyan:'#5de4ff', red:'#ff3b5f', muted:'#95a0ba', bg:'#06070b', panel:'#0d1118' };
  41 | 
  42 | const canvas = document.getElementById('embed-canvas');
  43 | const ctx    = canvas.getContext('2d');
  44 | const dpr    = window.devicePixelRatio || 1;
  45 | 
  46 | function resize() {
  47 |   const w = window.innerWidth - 32, h = window.innerHeight - 60;
  48 |   canvas.width  = w * dpr; canvas.height = h * dpr;
  49 |   canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  50 |   ctx.setTransform(dpr,0,0,dpr,0,0);
  51 |   return { W: w, H: h };
  52 | }
  53 | 
  54 | function drawLine(pts, { W, H }, color, filled) {
  55 |   if (!pts || pts.length < 2) return;
  56 |   const vals = pts.map(p=>p[1]);
  57 |   const minV = Math.min(...vals), maxV = Math.max(...vals);
  58 |   const range = maxV - minV || 1;
  59 |   const padL=50, padR=10, padT=15, padB=30;
  60 |   const iW = W-padL-padR, iH = H-padT-padB;
  61 |   const toX = i => padL + (i/(pts.length-1))*iW;
  62 |   const toY = v => padT + iH - ((v-minV)/range)*iH;
  63 |   // Grid
  64 |   ctx.strokeStyle='rgba(255,255,255,0.04)'; ctx.lineWidth=0.5;
  65 |   for(let i=0;i<=4;i++){const y=padT+(i/4)*iH;ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(padL+iW,y);ctx.stroke();}
  66 |   // Y labels
  67 |   ctx.fillStyle=C.muted; ctx.font='9px JetBrains Mono,monospace'; ctx.textAlign='right';
  68 |   for(let i=0;i<=4;i++){const v=minV+(i/4)*range;const y=padT+iH-(i/4)*iH;ctx.fillText(fmt(v),padL-4,y+3);}
  69 |   // X labels
  70 |   ctx.textAlign='center';
  71 |   const xSteps=Math.min(5,pts.length-1);
  72 |   for(let i=0;i<=xSteps;i++){const idx=Math.floor(i/xSteps*(pts.length-1));const d=new Date(pts[idx][0]);ctx.fillText((d.getMonth()+1)+'/'+d.getDate(),toX(idx),H-padB+14);}
  73 |   // Line
  74 |   if(filled){
  75 |     ctx.beginPath(); ctx.moveTo(toX(0),toY(pts[0][1]));
  76 |     pts.forEach((_,i)=>{ if(i>0) ctx.lineTo(toX(i),toY(pts[i][1])); });
  77 |     ctx.lineTo(toX(pts.length-1),padT+iH); ctx.lineTo(padL,padT+iH); ctx.closePath();
  78 |     const g=ctx.createLinearGradient(0,padT,0,padT+iH);
  79 |     g.addColorStop(0,color+'44'); g.addColorStop(1,color+'00');
  80 |     ctx.fillStyle=g; ctx.fill();
  81 |   }
  82 |   ctx.beginPath(); ctx.moveTo(toX(0),toY(pts[0][1]));
  83 |   pts.forEach((_,i)=>{ if(i>0) ctx.lineTo(toX(i),toY(pts[i][1])); });
  84 |   ctx.strokeStyle=color; ctx.lineWidth=2; ctx.lineJoin='round'; ctx.stroke();
  85 |   // Pulse dot
  86 |   const lx=toX(pts.length-1), ly=toY(pts[pts.length-1][1]);
  87 |   ctx.beginPath(); ctx.arc(lx,ly,4,0,Math.PI*2); ctx.fillStyle=color; ctx.fill();
  88 | }
  89 | 
  90 | function fmt(v) {
  91 |   if(v>=1e9)return(v/1e9).toFixed(1)+'B';
  92 |   if(v>=1e6)return(v/1e6).toFixed(1)+'M';
  93 |   if(v>=1e3)return(v/1e3).toFixed(0)+'K';
  94 |   return v.toFixed(v<10?1:0);
  95 | }
  96 | 
  97 | function show() {
  98 |   document.getElementById('loading').style.display='none';
  99 |   canvas.style.display='block';
 100 | }
 101 | 
 102 | const dims = resize();
 103 | ctx.fillStyle=C.bg; ctx.fillRect(0,0,dims.W,dims.H);
 104 | 
 105 | if (CHART === 'price') {
 106 |   fetch('/api/charts/price-history?days='+DAYS)
 107 |     .then(r=>r.json()).then(data=>{
 108 |       if(!data.prices) return;
 109 |       show();
 110 |       ctx.clearRect(0,0,dims.W,dims.H);
 111 |       drawLine(data.prices, dims, C.gold, true);
 112 |     }).catch(()=>{});
 113 | } else if (CHART === 'hashrate') {
 114 |   fetch('/api/charts/hashrate-history')
 115 |     .then(r=>r.json()).then(data=>{
 116 |       if(!data.hashrates) return;
 117 |       show();
 118 |       ctx.clearRect(0,0,dims.W,dims.H);
 119 |       const pts = data.hashrates.map(h=>[h.timestamp*1000, h.avgHashrate/1e18]);
 120 |       drawLine(pts, dims, C.cyan, true);
 121 |     }).catch(()=>{});
 122 | } else if (CHART === 'mempool') {
 123 |   fetch('/api/charts/mempool-data')
 124 |     .then(r=>r.json()).then(data=>{
 125 |       show();
 126 |       ctx.fillStyle=C.panel;
 127 |       ctx.fillRect(0,50,dims.W-30,dims.H-60);
 128 |       ctx.fillStyle=C.muted; ctx.font='12px JetBrains Mono,monospace'; ctx.textAlign='center';
 129 |       const mb = data.mempool ? (data.mempool.vsize/1e6).toFixed(2) : '—';
 130 |       ctx.fillStyle=C.red; ctx.font='bold 32px JetBrains Mono,monospace';
 131 |       ctx.fillText(mb+' MB', dims.W/2, dims.H/2);
 132 |       ctx.fillStyle=C.muted; ctx.font='10px JetBrains Mono,monospace';
 133 |       ctx.fillText('CURRENT MEMPOOL SIZE', dims.W/2, dims.H/2+20);
 134 |     }).catch(()=>{});
 135 | } else if (CHART === 'fear-greed') {
 136 |   fetch('/api/charts/fear-greed')
 137 |     .then(r=>r.json()).then(data=>{
 138 |       if(!data.data || !data.data[0]) return;
 139 |       show();
 140 |       const score = parseInt(data.data[0].value);
 141 |       const label = data.data[0].value_classification;
 142 |       // Gauge
 143 |       const cx=dims.W/2, cy=dims.H*0.75, r=Math.min(dims.W/2,dims.H)*0.65;
 144 |       ctx.beginPath(); ctx.arc(cx,cy,r,Math.PI,2*Math.PI);
 145 |       ctx.strokeStyle='rgba(255,255,255,0.08)'; ctx.lineWidth=16; ctx.lineCap='round'; ctx.stroke();
 146 |       const sweepAngle = (score/100)*Math.PI;
 147 |       const gColor = score<=25?C.red:score<=50?'#ff8ba0':score<=75?C.gold:'#89ffb8';
 148 |       ctx.beginPath(); ctx.arc(cx,cy,r,Math.PI,Math.PI+sweepAngle);
 149 |       ctx.strokeStyle=gColor; ctx.lineWidth=16; ctx.stroke();
 150 |       ctx.fillStyle=gColor; ctx.font='bold 40px JetBrains Mono,monospace'; ctx.textAlign='center'; ctx.textBaseline='middle';
 151 |       ctx.fillText(score, cx, cy-10);
 152 |       ctx.fillStyle=C.muted; ctx.font='12px JetBrains Mono,monospace';
 153 |       ctx.fillText(label.toUpperCase(), cx, cy+20);
 154 |     }).catch(()=>{});
 155 | }
 156 | </script>
 157 | </body>
 158 | </html>
 159 | 
```

### File: templates/media_unified.html (809 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Media Hub — Protocol Pulse Intelligence{% endblock %}
   3 | {% block meta_description %}Live Bitcoin intelligence terminal. Nostr feeds, on-chain data, sentiment analysis, and original podcast content.{% endblock %}
   4 | 
   5 | {% block head %}
   6 | <link rel="preconnect" href="https://fonts.googleapis.com">
   7 | <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   8 | <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Instrument+Serif&family=Geist+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
   9 | <link rel="stylesheet" href="/static/css/media_unified_v5.css">
  10 | {% endblock %}
  11 | 
  12 | {% block body_class %}mu-page{% endblock %}
  13 | 
  14 | {% block content %}
  15 | 
  16 | <!-- ════════════════════════════════════════════════════
  17 |      TELEMETRY RIBBON (sticky below nav)
  18 |      ════════════════════════════════════════════════════ -->
  19 | <div class="mu-telemetry" id="mu-telemetry">
  20 |   <div class="mu-telemetry-inner">
  21 |     <!-- Fee Rate -->
  22 |     <div class="mu-telem-metric">
  23 |       <span class="mu-telem-value" id="telem-fees" data-metric="fees">--</span>
  24 |       <canvas class="mu-sparkline" id="spark-fees" width="40" height="12"></canvas>
  25 |       <span class="mu-telem-label">sat/vB</span>
  26 |     </div>
  27 | 
  28 |     <div class="mu-telem-sep"></div>
  29 | 
  30 |     <!-- Mempool -->
  31 |     <div class="mu-telem-metric">
  32 |       <span class="mu-telem-value" id="telem-mempool" data-metric="mempool">--</span>
  33 |       <canvas class="mu-sparkline" id="spark-mempool" width="40" height="12"></canvas>
  34 |       <span class="mu-telem-label">MB</span>
  35 |     </div>
  36 | 
  37 |     <div class="mu-telem-sep"></div>
  38 | 
  39 |     <!-- Hashrate -->
  40 |     <div class="mu-telem-metric">
  41 |       <span class="mu-telem-value" id="telem-hashrate" data-metric="hashrate">--</span>
  42 |       <canvas class="mu-sparkline" id="spark-hashrate" width="40" height="12"></canvas>
  43 |       <span class="mu-telem-label">EH/s</span>
  44 |     </div>
  45 | 
  46 |     <div class="mu-telem-sep"></div>
  47 | 
  48 |     <!-- Block Height -->
  49 |     <div class="mu-telem-metric">
  50 |       <span class="mu-telem-value mu-telem-btc" id="telem-block" data-metric="block">--</span>
  51 |       <span class="mu-telem-label">BLOCK</span>
  52 |     </div>
  53 | 
  54 |     <div class="mu-telem-sep"></div>
  55 | 
  56 |     <!-- Signal Strength -->
  57 |     <div class="mu-telem-metric mu-telem-signal">
  58 |       <span class="mu-telem-label">SIGNAL</span>
  59 |       <span class="mu-telem-value" id="telem-signal">0</span>
  60 |       <div class="mu-signal-bar">
  61 |         <div class="mu-signal-fill" id="signal-fill"></div>
  62 |       </div>
  63 |     </div>
  64 | 
  65 |     <div class="mu-telem-sep"></div>
  66 | 
  67 |     <!-- X Spaces -->
  68 |     <div class="mu-telem-metric" title="X Spaces Sentiment">
  69 |       <span class="mu-telem-label">X SPACES</span>
  70 |       <span class="mu-telem-value" id="telem-xs-score" style="min-width:24px;">--</span>
  71 |       <span class="mu-telem-label" id="telem-xs-label" style="font-size:0.55rem;"></span>
  72 |     </div>
  73 | 
  74 |     <!-- Sentiment Track -->
  75 |     <div class="mu-sentiment-track-wrap">
  76 |       <span class="mu-sentiment-label-l">FEAR</span>
  77 |       <div class="mu-sentiment-track" id="sentiment-track">
  78 |         <div class="mu-sentiment-dot" id="sentiment-dot"></div>
  79 |       </div>
  80 |       <span class="mu-sentiment-label-r">GREED</span>
  81 |       <span class="mu-sentiment-num" id="sentiment-num">--</span>
  82 |     </div>
  83 |     <div class="mu-sentiment-why" id="sentiment-why"></div>
  84 | 
  85 |     <!-- Health Dots -->
  86 |     <div class="mu-health">
  87 |       <div class="mu-health-dot loading" id="health-nostr" title="Nostr"></div>
  88 |       <div class="mu-health-dot loading" id="health-telemetry" title="Telemetry"></div>
  89 |       <div class="mu-health-dot loading" id="health-sentiment" title="Sentiment"></div>
  90 |       <div class="mu-health-dot loading" id="health-xspaces" title="X Spaces"></div>
  91 |     </div>
  92 | 
  93 |     <!-- Cmd+K -->
  94 |     <div class="mu-cmdk-hint" id="cmd-k-hint">&#x2318;K</div>
  95 |   </div>
  96 | 
  97 |   <!-- Thermal border -->
  98 |   <div class="mu-thermal-border" id="thermal-border"></div>
  99 | </div>
 100 | 
 101 | <!-- ════════════════════════════════════════════════════
 102 |      HERO: Featured Media + Delta Card
 103 |      ════════════════════════════════════════════════════ -->
 104 | <section class="mu-hero">
 105 |   <!-- Featured — text IS the hero -->
 106 |   <div class="mu-featured" id="mu-featured">
 107 |     <div class="mu-featured-text" id="hero-text">
 108 |       <span class="mu-latest-label">LATEST</span>
 109 |       {% if latest_episodes and latest_episodes|length > 0 %}
 110 |         {% set ep = latest_episodes[0] %}
 111 |         <h1 class="mu-hero-title">{{ ep.title }}</h1>
 112 |         <div class="mu-hero-meta">
 113 |           <span>EP {{ loop.index if loop is defined else podcast_count }}</span>
 114 |           <span class="mu-hero-dot">&middot;</span>
 115 |           <span>PROTOCOL PULSE</span>
 116 |           <span class="mu-hero-dot">&middot;</span>
 117 |           <span>{{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}</span>
 118 |         </div>
 119 |         <button class="mu-play-btn" id="hero-play"
 120 |                 data-vid="{{ ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' }}">
 121 |           <span class="mu-play-icon">&#9654;</span>
 122 |           <span>PLAY</span>
 123 |         </button>
 124 |       {% else %}
 125 |         <h1 class="mu-hero-title">Protocol Pulse</h1>
 126 |         <div class="mu-hero-meta">
 127 |           <span>{{ podcast_count }} episodes</span>
 128 |         </div>
 129 |       {% endif %}
 130 |     </div>
 131 |     <!-- YouTube embed appears here on play click -->
 132 |     <div class="mu-featured-embed" id="hero-embed"></div>
 133 |   </div>
 134 | 
 135 |   <!-- Since You Were Gone -->
 136 |   <div class="mu-delta" id="mu-delta">
 137 |     <div class="mu-delta-count" id="delta-count">...</div>
 138 |     <div class="mu-delta-label" id="delta-label">Loading intelligence...</div>
 139 |     <div class="mu-delta-items" id="delta-items"></div>
 140 |     <button class="mu-delta-showme" id="delta-showme">&darr; SHOW ME</button>
 141 |   </div>
 142 | </section>
 143 | 
 144 | <!-- ════════════════════════════════════════════════════
 145 |      SIGNAL DASHBOARD: 2 Columns
 146 |      ════════════════════════════════════════════════════ -->
 147 | <section class="mu-signals" id="mu-signals">
 148 |   <!-- Left: Nostr + X Live -->
 149 |   <div class="mu-col">
 150 |     <div class="mu-col-header">
 151 |       <span class="mu-col-title">NOSTR + X LIVE</span>
 152 |       <span class="mu-col-source"><span class="mu-health-dot" id="health-nostr-col"></span></span>
 153 |     </div>
 154 |     <!-- D4: Relay Status Bar -->
 155 |     <div class="mu-relay-status-bar" id="relay-status-bar">
 156 |       <div class="mu-relay-item" data-relay="relay.damus.io">
 157 |         <div class="mu-relay-dot" style="background:#555"></div>
 158 |         <span class="mu-relay-name">damus</span>
 159 |         <span class="mu-relay-status">OFFLINE</span>
 160 |         <span class="mu-relay-count">0 notes</span>
 161 |       </div>
 162 |       <div class="mu-relay-item" data-relay="nos.lol">
 163 |         <div class="mu-relay-dot" style="background:#555"></div>
 164 |         <span class="mu-relay-name">nos.lol</span>
 165 |         <span class="mu-relay-status">OFFLINE</span>
 166 |         <span class="mu-relay-count">0 notes</span>
 167 |       </div>
 168 |       <div class="mu-relay-item" data-relay="relay.nostr.band">
 169 |         <div class="mu-relay-dot" style="background:#555"></div>
 170 |         <span class="mu-relay-name">nostr.band</span>
 171 |         <span class="mu-relay-status">OFFLINE</span>
 172 |         <span class="mu-relay-count">0 notes</span>
 173 |       </div>
 174 |     </div>
 175 |     <div class="mu-col-feed" id="nostr-feed"></div>
 176 |     <div class="mu-col-count" id="nostr-count">0 notes</div>
 177 |   </div>
 178 | 
 179 |   <div class="mu-col-divider"></div>
 180 | 
 181 |   <!-- Right: Verified Highlights -->
 182 |   <div class="mu-col">
 183 |     <div class="mu-col-header">
 184 |       <span class="mu-col-title">VERIFIED HIGHLIGHTS</span>
 185 |       <span class="mu-col-source">partner channels <span class="mu-health-dot connected" id="health-highlights-col"></span></span>
 186 |     </div>
 187 |     <div class="mu-col-feed" id="highlights-feed">
 188 |       {% if ssr_highlights %}
 189 |         {% for h in ssr_highlights %}
 190 |         <div class="mu-highlight-item">
 191 |           <div class="mu-highlight-quote">&ldquo;{{ h.excerpt[:180] }}&rdquo;</div>
 192 |           <div class="mu-highlight-source">&mdash; {{ h.source }}{% if h.direction == 'bullish' %} <span style="color:#22c55e">BULLISH</span>{% elif h.direction == 'bearish' %} <span style="color:#dc2626">BEARISH</span>{% endif %}</div>
 193 |         </div>
 194 |         {% endfor %}
 195 |       {% endif %}
 196 |     </div>
 197 |   </div>
 198 | </section>
 199 | 
 200 | <!-- ════════════════════════════════════════════════════
 201 |      SIGNAL STRENGTH GAUGE (Phase 2)
 202 |      ════════════════════════════════════════════════════ -->
 203 | <section class="mu-section mu-signal-section" id="mu-signal-section">
 204 |   <div class="mu-section-head">
 205 |     <h2 class="mu-section-title">SIGNAL STRENGTH</h2>
 206 |     <span class="mu-section-sub">Composite intelligence score — live</span>
 207 |   </div>
 208 |   <div class="mu-signal-gauge-wrap">
 209 |     <div id="signal-strength-gauge">
 210 |       <div class="mu-gauge-ring" style="--score:50%;--color:#E67E22">
 211 |         <div class="mu-gauge-inner">
 212 |           <div class="mu-gauge-score">--</div>
 213 |           <div class="mu-gauge-label">SIGNAL</div>
 214 |           <div class="mu-gauge-level">LOADING</div>
 215 |         </div>
 216 |       </div>
 217 |     </div>
 218 |     <div class="mu-signal-breakdown" id="signal-breakdown">
 219 |       <div class="mu-sig-row">
 220 |         <span class="mu-sig-key">SENTIMENT</span>
 221 |         <span class="mu-sig-val" id="sig-sentiment">--</span>
 222 |         <span class="mu-sig-weight">70%</span>
 223 |       </div>
 224 |       <div class="mu-sig-row">
 225 |         <span class="mu-sig-key">X SPACES</span>
 226 |         <span class="mu-sig-val" id="sig-spaces">--</span>
 227 |         <span class="mu-sig-weight">30%</span>
 228 |       </div>
 229 |       <div class="mu-sig-row mu-sig-total">
 230 |         <span class="mu-sig-key">COMPOSITE</span>
 231 |         <span class="mu-sig-val" id="sig-composite">--</span>
 232 |         <span class="mu-sig-weight">&nbsp;</span>
 233 |       </div>
 234 |     </div>
 235 |   </div>
 236 | </section>
 237 | 
 238 | <!-- ════════════════════════════════════════════════════
 239 |      REDDIT PULSE
 240 |      ════════════════════════════════════════════════════ -->
 241 | <section class="mu-section" id="mu-reddit">
 242 |   <div class="mu-section-head">
 243 |     <h2 class="mu-section-title">REDDIT PULSE</h2>
 244 |     <span class="mu-section-sub">r/bitcoin &middot; live</span>
 245 |   </div>
 246 |   <div class="mu-reddit-feed" id="reddit-feed"></div>
 247 | </section>
 248 | 
 249 | <!-- ════════════════════════════════════════════════════
 250 |      PARTNER CHANNELS TODAY
 251 |      ════════════════════════════════════════════════════ -->
 252 | <section class="mu-section" id="mu-partners">
 253 |   <div class="mu-section-head">
 254 |     <h2 class="mu-section-title">PARTNER CHANNELS TODAY</h2>
 255 |     <span class="mu-section-sub">{{ series_count }} channels tracked</span>
 256 |   </div>
 257 |   <div class="mu-partner-rail" id="partner-rail"></div>
 258 | </section>
 259 | 
 260 | <!-- ════════════════════════════════════════════════════
 261 |      ORIGINAL SERIES
 262 |      ════════════════════════════════════════════════════ -->
 263 | <section class="mu-section" id="mu-series">
 264 |   <div class="mu-section-head">
 265 |     <h2 class="mu-section-title">ORIGINAL SERIES</h2>
 266 |   </div>
 267 |   <div class="mu-series-grid">
 268 |     {% for s in series_list %}
 269 |     <a class="mu-series-item" href="https://youtube.com/watch?v={{ s.first_id }}" target="_blank" rel="noopener"
 270 |        data-thumb="https://img.youtube.com/vi/{{ s.first_id }}/maxresdefault.jpg">
 271 |       <div class="mu-series-name">{{ s.title }}</div>
 272 |       <div class="mu-series-sub">{{ s.description|upper if s.description else '' }}</div>
 273 |       <div class="mu-series-count">{{ s.ep_count }} episodes</div>
 274 |     </a>
 275 |     {% endfor %}
 276 |   </div>
 277 | </section>
 278 | 
 279 | <!-- ════════════════════════════════════════════════════
 280 |      LATEST EPISODES
 281 |      ════════════════════════════════════════════════════ -->
 282 | <section class="mu-section" id="mu-episodes">
 283 |   <div class="mu-section-head">
 284 |     <h2 class="mu-section-title">LATEST EPISODES</h2>
 285 |     <span class="mu-section-sub">{{ podcast_count }} episodes</span>
 286 |   </div>
 287 |   <div class="mu-ep-filters">
 288 |     <button class="mu-chip active" data-filter="all">All</button>
 289 |     <button class="mu-chip" data-filter="episodes">Episodes</button>
 290 |     <button class="mu-chip" data-filter="clips">Clips</button>
 291 |     <button class="mu-chip" data-filter="briefings">Briefings</button>
 292 |   </div>
 293 |   <div class="mu-ep-grid">
 294 |     {% for ep in latest_episodes[:12] %}
 295 |     {% set vid_id = ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' %}
 296 |     <a class="mu-ep-item" href="https://youtube.com/watch?v={{ vid_id }}" target="_blank" rel="noopener">
 297 |       <div class="mu-ep-thumb">
 298 |         <img src="https://img.youtube.com/vi/{{ vid_id }}/mqdefault.jpg" alt="{{ ep.title }}" loading="lazy" width="320" height="180">
 299 |       </div>
 300 |       <div class="mu-ep-info">
 301 |         <div class="mu-ep-title">{{ ep.title }}</div>
 302 |         <div class="mu-ep-meta">
 303 |           {{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}
 304 |           {% if ep.host %} &middot; {{ ep.host }}{% endif %}
 305 |         </div>
 306 |       </div>
 307 |     </a>
 308 |     {% endfor %}
 309 |   </div>
 310 | </section>
 311 | 
 312 | <!-- ════════════════════════════════════════════════════
 313 |      THE LIBRARY
 314 |      ════════════════════════════════════════════════════ -->
 315 | <section class="mu-section" id="mu-library">
 316 |   <div class="mu-section-head">
 317 |     <h2 class="mu-section-title">THE LIBRARY</h2>
 318 |     <span class="mu-section-sub">Curated reading for sovereign minds</span>
 319 |   </div>
 320 | 
 321 |   <!-- Leaderboard + Rising Stars -->
 322 |   <div class="mu-lib-top">
 323 |     <div class="mu-lib-leaderboard">
 324 |       <div class="mu-lib-subtitle">LEADERBOARD</div>
 325 |       <div class="mu-lb-item" data-rank="1">
 326 |         <span class="mu-lb-rank">#1</span>
 327 |         <span class="mu-lb-title">The Bitcoin Standard</span>
 328 |         <span class="mu-lb-dot">&middot;</span>
 329 |         <span class="mu-lb-author">Saifedean Ammous</span>
 330 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:100%"></div></div>
 331 |         <button class="mu-vote-btn" data-book="bitcoin-standard">&#128077;</button>
 332 |         <span class="mu-vote-count" data-book="bitcoin-standard">0</span>
 333 |       </div>
 334 |       <div class="mu-lb-item" data-rank="2">
 335 |         <span class="mu-lb-rank">#2</span>
 336 |         <span class="mu-lb-title">Broken Money</span>
 337 |         <span class="mu-lb-dot">&middot;</span>
 338 |         <span class="mu-lb-author">Lyn Alden</span>
 339 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:82%"></div></div>
 340 |         <button class="mu-vote-btn" data-book="broken-money">&#128077;</button>
 341 |         <span class="mu-vote-count" data-book="broken-money">0</span>
 342 |       </div>
 343 |       <div class="mu-lb-item" data-rank="3">
 344 |         <span class="mu-lb-rank">#3</span>
 345 |         <span class="mu-lb-title">The Sovereign Individual</span>
 346 |         <span class="mu-lb-dot">&middot;</span>
 347 |         <span class="mu-lb-author">Davidson &amp; Rees-Mogg</span>
 348 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:68%"></div></div>
 349 |         <button class="mu-vote-btn" data-book="sovereign-individual">&#128077;</button>
 350 |         <span class="mu-vote-count" data-book="sovereign-individual">0</span>
 351 |       </div>
 352 |       <div class="mu-lb-item" data-rank="4">
 353 |         <span class="mu-lb-rank">#4</span>
 354 |         <span class="mu-lb-title">Mastering Bitcoin</span>
 355 |         <span class="mu-lb-dot">&middot;</span>
 356 |         <span class="mu-lb-author">Andreas Antonopoulos</span>
 357 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:55%"></div></div>
 358 |         <button class="mu-vote-btn" data-book="mastering-bitcoin">&#128077;</button>
 359 |         <span class="mu-vote-count" data-book="mastering-bitcoin">0</span>
 360 |       </div>
 361 |     </div>
 362 | 
 363 |     <div class="mu-lib-rising">
 364 |       <div class="mu-lib-subtitle">RISING STARS</div>
 365 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Resistance Money &middot; Andrew M. Bailey</div>
 366 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Bitcoin is Venice &middot; Allen Farrington</div>
 367 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Check Your Financial Privilege &middot; Alex Gladstein</div>
 368 |     </div>
 369 |   </div>
 370 | 
 371 |   <!-- Learning Paths -->
 372 |   <div class="mu-lib-paths">
 373 |     <div class="mu-lib-subtitle">LEARNING PATHS</div>
 374 |     <div class="mu-paths-grid">
 375 |       <div class="mu-path">
 376 |         <div class="mu-path-name">UNDERSTAND MONEY</div>
 377 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1119473861" target="_blank" rel="noopener">The Bitcoin Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 378 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544526474" target="_blank" rel="noopener">The Fiat Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 379 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0CN14FKHF" target="_blank" rel="noopener">Broken Money <span class="mu-path-author">&middot; Lyn Alden</span></a>
 380 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1999257405" target="_blank" rel="noopener">The Price of Tomorrow <span class="mu-path-author">&middot; Jeff Booth</span></a>
 381 |       </div>
 382 |       <div class="mu-path">
 383 |         <div class="mu-path-name">UNDERSTAND BITCOIN</div>
 384 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1098150090" target="_blank" rel="noopener">Mastering Bitcoin <span class="mu-path-author">&middot; Andreas Antonopoulos</span></a>
 385 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B07MWGP64R" target="_blank" rel="noopener">Inventing Bitcoin <span class="mu-path-author">&middot; Yan Pritzker</span></a>
 386 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B08YQMC2WM" target="_blank" rel="noopener">The Blocksize War <span class="mu-path-author">&middot; Jonathan Bier</span></a>
 387 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0B3L61JYN" target="_blank" rel="noopener">The Genesis Book <span class="mu-path-author">&middot; Aaron van Wirdum</span></a>
 388 |       </div>
 389 |       <div class="mu-path">
 390 |         <div class="mu-path-name">UNDERSTAND FREEDOM</div>
 391 |         <a class="mu-path-book" href="https://www.amazon.com/dp/0684832720" target="_blank" rel="noopener">The Sovereign Individual <span class="mu-path-author">&middot; Davidson &amp; Rees-Mogg</span></a>
 392 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544542895" target="_blank" rel="noopener">Softwar <span class="mu-path-author">&middot; Jason Lowery</span></a>
 393 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09C4GLPYX" target="_blank" rel="noopener">Thank God for Bitcoin <span class="mu-path-author">&middot; Jimmy Song et al.</span></a>
 394 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09KLPNBPC" target="_blank" rel="noopener">Bitcoin is Venice <span class="mu-path-author">&middot; Allen Farrington</span></a>
 395 |       </div>
 396 |     </div>
 397 |   </div>
 398 | 
 399 |   <!-- Full Library (collapsed by default) -->
 400 |   <button class="mu-lib-toggle" id="lib-toggle">&darr; VIEW FULL LIBRARY</button>
 401 |   <div class="mu-lib-full" id="lib-full">
 402 |     <div class="mu-lib-grid">
 403 |       {% for book in all_books %}
 404 |       <a class="mu-lib-book" href="{{ book.amazon_url }}" target="_blank" rel="noopener">
 405 |         <div class="mu-lib-cover" style="background:{{ book.color|default('#222') }}">
 406 |           <span>{{ book.title[:40] }}</span>
 407 |         </div>
 408 |         <div class="mu-lib-book-title">{{ book.title }}</div>
 409 |         <div class="mu-lib-book-author">{{ book.author }}</div>
 410 |         <button class="mu-vote-btn" data-book="{{ book.title|lower|replace(' ','-') }}">&#128077;</button>
 411 |         <span class="mu-vote-count" data-book="{{ book.title|lower|replace(' ','-') }}">0</span>
 412 |       </a>
 413 |       {% endfor %}
 414 |     </div>
 415 |   </div>
 416 | </section>
 417 | 
 418 | <!-- ════════════════════════════════════════════════════
 419 |      NEWSLETTER CTA
 420 |      ════════════════════════════════════════════════════ -->
 421 | <section class="mu-newsletter" id="mu-newsletter">
 422 |   <h2 class="mu-nl-title">Sovereign Intel Briefing</h2>
 423 |   <p class="mu-nl-sub">Daily Bitcoin intelligence. No noise. No ads. Delivered before markets open.</p>
 424 |   <div class="mu-nl-form">
 425 |     <input type="email" placeholder="your@email.com" id="newsletter-email" autocomplete="email">
 426 |     <button id="newsletter-submit">Subscribe</button>
 427 |   </div>
 428 | </section>
 429 | 
 430 | <!-- ════════════════════════════════════════════════════
 431 |      COMMAND PALETTE (Cmd+K)
 432 |      ════════════════════════════════════════════════════ -->
 433 | <div class="mu-cmd-overlay" id="cmd-overlay">
 434 |   <div class="mu-cmd-box">
 435 |     <div class="mu-cmd-prompt">
 436 |       <span class="mu-cmd-caret">&gt;</span>
 437 |       <input class="mu-cmd-input" id="cmd-input" placeholder="" autocomplete="off" spellcheck="false">
 438 |     </div>
 439 |     <div class="mu-cmd-results" id="cmd-results"></div>
 440 |     <div class="mu-cmd-footer">Press &uarr;&darr; to navigate &middot; Enter to select &middot; Esc to close</div>
 441 |   </div>
 442 | </div>
 443 | 
 444 | <!-- ════════════════════════════════════════════════════
 445 |      AUDIO BAR (floating, hidden until active)
 446 |      ════════════════════════════════════════════════════ -->
 447 | <div class="mu-audio-bar" id="audio-bar">
 448 |   <button class="mu-ab-play" id="ab-play">&#9654;</button>
 449 |   <span class="mu-ab-info" id="ab-info"></span>
 450 |   <div class="mu-ab-progress">
 451 |     <div class="mu-ab-track">
 452 |       <div class="mu-ab-fill" id="ab-fill"></div>
 453 |       <div class="mu-ab-dot" id="ab-dot"></div>
 454 |     </div>
 455 |   </div>
 456 |   <span class="mu-ab-time" id="ab-time">0:00 / 0:00</span>
 457 |   <button class="mu-ab-speed" id="ab-speed">1&times;</button>
 458 | </div>
 459 | 
 460 | <!-- D5: Health Strip -->
 461 | <div id="health-strip" class="mu-health-strip"></div>
 462 | 
 463 | {% endblock %}
 464 | 
 465 | {% block scripts %}
 466 | <script src="/static/js/media_unified_v5.js"></script>
 467 | <script>
 468 | function subscribeNewsletter() {
 469 |   const email = document.getElementById('newsletter-email').value;
 470 |   if (!email || !email.includes('@')) { alert('Enter a valid email'); return; }
 471 |   fetch('/api/newsletter/subscribe', {
 472 |     method: 'POST',
 473 |     headers: {'Content-Type': 'application/json'},
 474 |     body: JSON.stringify({email: email})
 475 |   }).then(r => r.json()).then(d => {
 476 |     if (d.success) alert('Subscribed! Check your inbox.');
 477 |     else alert(d.message || 'Subscription failed');
 478 |   }).catch(() => alert('Network error — try again'));
 479 | }
 480 | document.getElementById('newsletter-submit')?.addEventListener('click', subscribeNewsletter);
 481 | 
 482 | // Phase 2: X Spaces + telemetry wired in media_p2_init below
 483 | </script>
 484 | 
 485 | <style>
 486 | /* ── D4: Relay Status Bar ─────────────────────── */
 487 | .mu-relay-status-bar {
 488 |   display: flex; gap: 8px; padding: 6px 12px;
 489 |   background: rgba(247,147,26,0.04); border-bottom: 1px solid #1a1a1a;
 490 |   flex-wrap: wrap;
 491 | }
 492 | .mu-relay-item {
 493 |   display: flex; align-items: center; gap: 5px;
 494 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 495 | }
 496 | .mu-relay-dot {
 497 |   width: 7px; height: 7px; border-radius: 50%;
 498 |   animation: mu-pulse 2s infinite;
 499 | }
 500 | .mu-relay-name { color: #888; letter-spacing: 1px; }
 501 | .mu-relay-status { color: #555; font-size: 8px; }
 502 | .mu-relay-count { color: #444; font-size: 8px; }
 503 | 
 504 | /* ── D3: Signal Strength Gauge ────────────────── */
 505 | .mu-signal-section { padding: 24px 0; }
 506 | .mu-signal-gauge-wrap {
 507 |   display: flex; align-items: center; gap: 40px;
 508 |   padding: 20px 0; flex-wrap: wrap;
 509 | }
 510 | #signal-strength-gauge { flex-shrink: 0; }
 511 | .mu-gauge-ring {
 512 |   position: relative; width: 140px; height: 140px;
 513 |   border-radius: 50%;
 514 |   background: conic-gradient(var(--color) var(--score), #1a1a1a 0);
 515 |   display: flex; align-items: center; justify-content: center;
 516 |   box-shadow: 0 0 24px color-mix(in srgb, var(--color) 30%, transparent);
 517 | }
 518 | .mu-gauge-inner {
 519 |   width: 100px; height: 100px; border-radius: 50%;
 520 |   background: #0a0a0a;
 521 |   display: flex; flex-direction: column;
 522 |   align-items: center; justify-content: center; gap: 2px;
 523 | }
 524 | .mu-gauge-score {
 525 |   font-family: 'Geist Mono', monospace; font-size: 30px;
 526 |   font-weight: 900; color: var(--color); line-height: 1;
 527 | }
 528 | .mu-gauge-label {
 529 |   font-family: 'Geist Mono', monospace; font-size: 8px;
 530 |   color: #555; letter-spacing: 2px;
 531 | }
 532 | .mu-gauge-level {
 533 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 534 |   font-weight: 700; color: var(--color);
 535 | }
 536 | .mu-signal-breakdown {
 537 |   display: flex; flex-direction: column; gap: 10px; min-width: 220px;
 538 | }
 539 | .mu-sig-row {
 540 |   display: flex; gap: 8px; align-items: center;
 541 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 542 | }
 543 | .mu-sig-key { color: #555; letter-spacing: 1px; min-width: 90px; }
 544 | .mu-sig-val { color: #F7931A; font-weight: 700; min-width: 32px; }
 545 | .mu-sig-weight { color: #333; font-size: 9px; }
 546 | .mu-sig-total .mu-sig-key { color: #888; }
 547 | .mu-sig-total .mu-sig-val { color: #fff; font-size: 14px; }
 548 | 
 549 | /* ── D5: Health Strip ─────────────────────────── */
 550 | .mu-health-strip {
 551 |   position: fixed; bottom: 0; left: 0; right: 0;
 552 |   height: 30px; background: #050505;
 553 |   border-top: 1px solid #1a1a1a;
 554 |   display: flex; align-items: center;
 555 |   padding: 0 16px; gap: 20px; z-index: 9999;
 556 |   overflow-x: auto; overflow-y: hidden;
 557 | }
 558 | .mu-hs-item { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
 559 | .mu-hs-dot {
 560 |   width: 7px; height: 7px; border-radius: 50%;
 561 |   animation: mu-pulse 2s infinite;
 562 | }
 563 | .mu-hs-name {
 564 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 565 |   color: #555; letter-spacing: 1px;
 566 | }
 567 | .mu-hs-lat {
 568 |   font-family: 'Geist Mono', monospace; font-size: 8px; color: #333;
 569 | }
 570 | @keyframes mu-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
 571 | 
 572 | /* Bottom padding so health strip doesn't cover content */
 573 | .mu-page { padding-bottom: 38px; }
 574 | </style>
 575 | 
 576 | <script>
 577 | // ═══════════════════════════════════════════════════════
 578 | // MEDIA UNIFIED — PHASE 2 RUNTIME
 579 | // D1: Clean API wiring  D2: Live telemetry  D3: Signal gauge
 580 | // D4: Nostr relay panel  D5: Health strip
 581 | // ═══════════════════════════════════════════════════════
 582 | 
 583 | (function() {
 584 |   'use strict';
 585 | 
 586 |   // ── Cache ────────────────────────────────────────────
 587 |   var _cache = { sentiment: null, spaces: null, tradfi: null };
 588 | 
 589 |   // ── D1 + D2: Live Telemetry Wiring ──────────────────
 590 |   async function fetchSentiment() {
 591 |     try {
 592 |       var r = await fetch('/api/media/sentiment');
 593 |       var d = await r.json();
 594 |       _cache.sentiment = d;
 595 |       return d;
 596 |     } catch(e) {
 597 |       console.warn('[P2] sentiment fetch failed:', e);
 598 |       return _cache.sentiment || { composite_score: null, label: 'OFFLINE' };
 599 |     }
 600 |   }
 601 | 
 602 |   async function fetchSpaces() {
 603 |     try {
 604 |       var r = await fetch('/api/spaces/live');
 605 |       var d = await r.json();
 606 |       _cache.spaces = d;
 607 |       return d;
 608 |     } catch(e) {
 609 |       console.warn('[P2] spaces fetch failed:', e);
 610 |       return _cache.spaces || { spaces: [], score: 0, label: 'OFFLINE' };
 611 |     }
 612 |   }
 613 | 
 614 |   async function fetchTradfi() {
 615 |     try {
 616 |       var r = await fetch('/api/tradfi/signals');
 617 |       var d = await r.json();
 618 |       _cache.tradfi = d;
 619 |       return d;
 620 |     } catch(e) {
 621 |       return _cache.tradfi || null;
 622 |     }
 623 |   }
 624 | 
 625 |   // ── D3: Signal Strength Gauge Renderer ──────────────
 626 |   function computeSignalStrength(sentData, spacesData) {
 627 |     var sentScore = (sentData && sentData.composite_score != null)
 628 |       ? parseFloat(sentData.composite_score) : 50;
 629 |     var spacesCount = (spacesData && spacesData.spaces)
 630 |       ? spacesData.spaces.length : 0;
 631 |     var spacesScore = Math.min(spacesCount * 10, 100);
 632 |     return Math.round(sentScore * 0.7 + spacesScore * 0.3);
 633 |   }
 634 | 
 635 |   function renderSignalGauge(score, sentScore, spacesScore) {
 636 |     var el = document.getElementById('signal-strength-gauge');
 637 |     if (!el) return;
 638 |     var level = score >= 70 ? 'HIGH' : score >= 40 ? 'MODERATE' : 'LOW';
 639 |     var color = score >= 70 ? '#F7931A' : score >= 40 ? '#E67E22' : '#666';
 640 |     el.innerHTML =
 641 |       '<div class="mu-gauge-ring" style="--score:' + score + '%;--color:' + color + '">' +
 642 |         '<div class="mu-gauge-inner">' +
 643 |           '<div class="mu-gauge-score">' + score + '</div>' +
 644 |           '<div class="mu-gauge-label">SIGNAL</div>' +
 645 |           '<div class="mu-gauge-level">' + level + '</div>' +
 646 |         '</div>' +
 647 |       '</div>';
 648 |     // Update breakdown
 649 |     var sEl = document.getElementById('sig-sentiment');
 650 |     var spEl = document.getElementById('sig-spaces');
 651 |     var cEl = document.getElementById('sig-composite');
 652 |     if (sEl) sEl.textContent = Math.round(sentScore);
 653 |     if (spEl) spEl.textContent = Math.round(Math.min((spacesScore||0)*10,100));
 654 |     if (cEl) cEl.textContent = score;
 655 |   }
 656 | 
 657 |   // ── D4: Nostr Relay Status Panel Updater ────────────
 658 |   // Hook into the existing RelayManager to sync relay dots
 659 |   function syncRelayStatusBar() {
 660 |     if (!window.relayManager || !window.relayManager.sockets) return;
 661 |     var sockets = window.relayManager.sockets;
 662 |     Object.keys(sockets).forEach(function(url) {
 663 |       var ws = sockets[url];
 664 |       var relayName = url.replace('wss://','').split('/')[0];
 665 |       var el = document.querySelector('[data-relay="' + relayName + '"]');
 666 |       if (!el) return;
 667 |       var dot = el.querySelector('.mu-relay-dot');
 668 |       var statusEl = el.querySelector('.mu-relay-status');
 669 |       var countEl = el.querySelector('.mu-relay-count');
 670 |       if (!dot || !statusEl) return;
 671 |       var rs = ws.readyState;
 672 |       if (rs === 1) { // OPEN
 673 |         dot.style.background = '#F7931A';
 674 |         statusEl.textContent = 'LIVE';
 675 |         statusEl.style.color = '#F7931A';
 676 |       } else if (rs === 0) { // CONNECTING
 677 |         dot.style.background = '#E67E22';
 678 |         statusEl.textContent = 'CONNECTING';
 679 |         statusEl.style.color = '#E67E22';
 680 |       } else {
 681 |         dot.style.background = '#444';
 682 |         statusEl.textContent = 'OFFLINE';
 683 |         statusEl.style.color = '#444';
 684 |       }
 685 |     });
 686 |     // Sync note counts from state
 687 |     if (window.state && window.state.nostrNotes) {
 688 |       var byRelay = {};
 689 |       window.state.nostrNotes.forEach(function(n) {
 690 |         if (n.relay) byRelay[n.relay] = (byRelay[n.relay]||0) + 1;
 691 |       });
 692 |       Object.keys(byRelay).forEach(function(url) {
 693 |         var relayName = url.replace('wss://','').split('/')[0];
 694 |         var el = document.querySelector('[data-relay="' + relayName + '"]');
 695 |         if (!el) return;
 696 |         var countEl = el.querySelector('.mu-relay-count');
 697 |         if (countEl) countEl.textContent = byRelay[url] + ' notes';
 698 |       });
 699 |     }
 700 |   }
 701 | 
 702 |   // ── X Spaces Telemetry Display (D1 replacement) ─────
 703 |   function updateXSpacesTelemetry(spacesData) {
 704 |     var xs = spacesData || {};
 705 |     var xsScore = xs.score != null ? xs.score : (xs.x_spaces ? xs.x_spaces.score : null);
 706 |     var xsLabel = xs.label || (xs.x_spaces ? xs.x_spaces.label : '') || '';
 707 |     var activeCount = xs.spaces ? xs.spaces.length : (xs.active_count || 0);
 708 | 
 709 |     var sc = document.getElementById('telem-xs-score');
 710 |     var lb = document.getElementById('telem-xs-label');
 711 |     var dot = document.getElementById('health-xspaces');
 712 |     if (sc && xsScore != null) sc.textContent = xsScore;
 713 |     if (lb && xsLabel) {
 714 |       lb.textContent = xsLabel;
 715 |       lb.style.color = xsLabel === 'BULLISH' ? '#22c55e'
 716 |                      : xsLabel === 'BEARISH' ? '#ef4444' : '#888';
 717 |     }
 718 |     if (dot) {
 719 |       dot.classList.remove('loading');
 720 |       dot.classList.add(activeCount > 0 ? 'connected' : 'error');
 721 |     }
 722 | 
 723 |     // Provide blend shim to existing signal engine
 724 |     window._ppBlendXSpaces = function(baseScore) {
 725 |       if (xsScore != null) return Math.round(baseScore * 0.7 + xsScore * 0.3);
 726 |       return baseScore;
 727 |     };
 728 |   }
 729 | 
 730 |   // ── D2: Master 30s Telemetry Poll ───────────────────
 731 |   async function updateTelemetry() {
 732 |     var results = await Promise.allSettled([
 733 |       fetchSentiment(),
 734 |       fetchSpaces(),
 735 |       fetchTradfi()
 736 |     ]);
 737 | 
 738 |     var sentData  = results[0].status === 'fulfilled' ? results[0].value : (_cache.sentiment || {});
 739 |     var spacesData = results[1].status === 'fulfilled' ? results[1].value : (_cache.spaces || {});
 740 | 
 741 |     // Update X Spaces display
 742 |     updateXSpacesTelemetry(spacesData);
 743 | 
 744 |     // D3: Compute + render Signal Strength gauge
 745 |     var spacesCount = spacesData.spaces ? spacesData.spaces.length : 0;
 746 |     var sentScore = sentData.composite_score != null ? parseFloat(sentData.composite_score) : 50;
 747 |     var score = computeSignalStrength(sentData, spacesData);
 748 |     renderSignalGauge(score, sentScore, spacesCount);
 749 | 
 750 |     // D4: Sync relay status bar
 751 |     syncRelayStatusBar();
 752 |   }
 753 | 
 754 |   // ── D5: Health Strip ─────────────────────────────────
 755 |   var P2_SERVICES = [
 756 |     { name: 'PIPELINE', url: 'https://relay.protocolpulse.io/health' },
 757 |     { name: 'ORACLE',   url: 'https://avatar.protocolpulse.io/health' },
 758 |     { name: 'REPLIT',   url: '/api/health' },
 759 |     { name: 'SPACES',   url: '/api/spaces/live' },
 760 |     { name: 'TRADFI',   url: '/api/tradfi/signals' },
 761 |   ];
 762 | 
 763 |   async function checkService(svc) {
 764 |     var start = Date.now();
 765 |     try {
 766 |       var r = await Promise.race([
 767 |         fetch(svc.url, { method: 'HEAD', cache: 'no-store' }),
 768 |         new Promise(function(_, rej) { setTimeout(function(){ rej(new Error('timeout')); }, 5000); })
 769 |       ]);
 770 |       return { status: r.ok ? 'UP' : 'DEGRADED', lat: Date.now() - start };
 771 |     } catch(e) {
 772 |       return { status: 'DOWN', lat: null };
 773 |     }
 774 |   }
 775 | 
 776 |   async function updateHealthStrip() {
 777 |     var strip = document.getElementById('health-strip');
 778 |     if (!strip) return;
 779 |     var results = await Promise.allSettled(P2_SERVICES.map(checkService));
 780 |     strip.innerHTML = P2_SERVICES.map(function(svc, i) {
 781 |       var r = (results[i].status === 'fulfilled' ? results[i].value : null) || { status: 'UNKNOWN', lat: null };
 782 |       var color = r.status === 'UP' ? '#27AE60' : r.status === 'DEGRADED' ? '#E67E22' : '#444';
 783 |       var lat = r.lat ? r.lat + 'ms' : '--';
 784 |       return '<div class="mu-hs-item">' +
 785 |         '<div class="mu-hs-dot" style="background:' + color + '"></div>' +
 786 |         '<span class="mu-hs-name">' + svc.name + '</span>' +
 787 |         '<span class="mu-hs-lat">' + lat + '</span>' +
 788 |       '</div>';
 789 |     }).join('');
 790 |   }
 791 | 
 792 |   // ── BOOT ─────────────────────────────────────────────
 793 |   document.addEventListener('DOMContentLoaded', function() {
 794 |     // D2+D3: initial poll + 30s interval
 795 |     updateTelemetry();
 796 |     setInterval(updateTelemetry, 30000);
 797 | 
 798 |     // D4: Relay status sync every 5s
 799 |     setInterval(syncRelayStatusBar, 5000);
 800 | 
 801 |     // D5: Health strip initial + 60s interval
 802 |     updateHealthStrip();
 803 |     setInterval(updateHealthStrip, 60000);
 804 |   });
 805 | 
 806 | })();
 807 | </script>
 808 | {% endblock %}
 809 | 
```

### File: video_pipeline_v3/dual_host_tts.py (372 lines)
```
   1 | #!/usr/bin/env python3
   2 | """dual_host_tts.py — Single-host TTS engine for Pulse Check.
   3 | 
   4 | Generates audio using ElevenLabs TTS.
   5 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) — PBX approved single narrator at 1.10x speed.
   6 | Both host=1 and host=2 entries route to Mark (single voice, no gender swap).
   7 | 
   8 | Usage:
   9 |     from dual_host_tts import generate_dialogue_audio
  10 | 
  11 |     dialogue = [
  12 |         {"host": 1, "text": "So Saylor just dropped another banger..."},
  13 |         {"host": 2, "text": "Let's roll the clip."},
  14 |         {"host": "CLIP", "duration": 30, "source": "@MicroStrategy"},
  15 |         {"host": 2, "text": "Ok here's what blows my mind about this..."},
  16 |         {"host": 1, "text": "Right, and if you think about it..."},
  17 |     ]
  18 | 
  19 |     result = generate_dialogue_audio(dialogue, output_dir="output/")
  20 |     # Returns: {
  21 |     #   "lines": [...],
  22 |     #   "full": "output/full_dialogue.m4a",
  23 |     #   "total_duration": 45.0,
  24 |     # }
  25 | """
  26 | import os
  27 | import sys
  28 | import json
  29 | import subprocess
  30 | import time
  31 | 
  32 | BASE = os.path.dirname(os.path.abspath(__file__))
  33 | sys.path.insert(0, BASE)
  34 | 
  35 | try:
  36 |     import requests
  37 |     HAS_REQUESTS = True
  38 | except ImportError:
  39 |     HAS_REQUESTS = False
  40 | 
  41 | from relay import get_key
  42 | 
  43 | # ── Voice configuration ──────────────────────────────────────────────────────
  44 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST ONLY — Mark at 1.10x speed.
  45 | # Nicole (piTKgcLEGmPE4e6mEKli) and Chris (iP95p4xoKVk53GoZ742B) are BANNED.
  46 | # Both host=1 and host=2 map to Mark.
  47 | 
  48 | _MARK_VOICE = {
  49 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  50 |     "name": "Mark",
  51 |     "model_id": "eleven_turbo_v2_5",
  52 |     "voice_settings": {
  53 |         "stability": 0.55,
  54 |         "similarity_boost": 0.80,
  55 |         "style": 0.15,
  56 |         "use_speaker_boost": True,
  57 |         "speed": 1.10,
  58 |     },
  59 | }
  60 | 
  61 | VOICES = {
  62 |     1: _MARK_VOICE,
  63 |     2: _MARK_VOICE,  # both hosts → Mark (single narrator)
  64 | }
  65 | 
  66 | SILENCE_GAP = 0.3  # seconds between speakers
  67 | MAX_CHUNK_CHARS = 4900
  68 | 
  69 | _KEY_CACHE: dict = {}
  70 | 
  71 | 
  72 | def _get_cached_key(name: str) -> str:
  73 |     if name not in _KEY_CACHE:
  74 |         k = get_key(name)
  75 |         if k:
  76 |             _KEY_CACHE[name] = k.strip()
  77 |     return _KEY_CACHE.get(name, "")
  78 | 
  79 | 
  80 | def ffprobe_duration(path: str) -> float:
  81 |     r = subprocess.run(
  82 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  83 |          "-of", "csv=p=0", path],
  84 |         capture_output=True, text=True,
  85 |     )
  86 |     try:
  87 |         return float(r.stdout.strip())
  88 |     except Exception:
  89 |         return 0.0
  90 | 
  91 | 
  92 | def _generate_silence(output_path: str, duration: float) -> bool:
  93 |     r = subprocess.run(
  94 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  95 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  96 |          "-c:a", "aac", "-b:a", "192k", output_path],
  97 |         capture_output=True, text=True, timeout=30,
  98 |     )
  99 |     return r.returncode == 0 and os.path.exists(output_path)
 100 | 
 101 | 
 102 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
 103 |     r = subprocess.run(
 104 |         ["ffmpeg", "-y", "-i", mp3_path,
 105 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
 106 |         capture_output=True, text=True, timeout=120,
 107 |     )
 108 |     return r.returncode == 0 and os.path.exists(m4a_path)
 109 | 
 110 | 
 111 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
 112 |     if len(text) <= max_chars:
 113 |         return [text]
 114 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
 115 |     sentences = raw.split("\x00")
 116 |     chunks, current = [], ""
 117 |     for sent in sentences:
 118 |         if len(current) + len(sent) + 1 <= max_chars:
 119 |             current = f"{current} {sent}".strip() if current else sent
 120 |         else:
 121 |             if current:
 122 |                 chunks.append(current)
 123 |             current = sent
 124 |     if current:
 125 |         chunks.append(current)
 126 |     return [c for c in chunks if c.strip()]
 127 | 
 128 | 
 129 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 130 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback (quota exhausted)."""
 131 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 132 |     r = subprocess.run([
 133 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 134 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 135 |         output_path,
 136 |     ], capture_output=True, text=True, timeout=15)
 137 |     if r.returncode == 0 and os.path.exists(output_path):
 138 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 139 |         return True
 140 |     return False
 141 | 
 142 | 
 143 | def tts_elevenlabs(text: str, output_path: str, host: int = 1) -> bool:
 144 |     """Generate TTS audio for a single line using the specified host voice.
 145 | 
 146 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 147 |     """
 148 |     if not HAS_REQUESTS:
 149 |         return _tts_generate_silence_fallback(text, output_path)
 150 | 
 151 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 152 |     if not key:
 153 |         return _tts_generate_silence_fallback(text, output_path)
 154 | 
 155 |     voice = VOICES.get(host, VOICES[1])
 156 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 157 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 158 | 
 159 |     chunks = _chunk_text(text)
 160 |     chunk_files = []
 161 | 
 162 |     for ci, chunk in enumerate(chunks):
 163 |         # Extract speed (top-level ElevenLabs param) from voice_settings if present
 164 |         raw_settings = dict(voice["voice_settings"])
 165 |         speed_val = raw_settings.pop("speed", None)
 166 |         body = {
 167 |             "text": chunk,
 168 |             "model_id": voice["model_id"],
 169 |             "voice_settings": raw_settings,
 170 |         }
 171 |         if speed_val is not None:
 172 |             body["speed"] = speed_val
 173 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 174 |         success = False
 175 | 
 176 |         for attempt in range(3):
 177 |             try:
 178 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 179 |                 if r.status_code == 200:
 180 |                     with open(mp3_tmp, "wb") as f:
 181 |                         f.write(r.content)
 182 |                     success = True
 183 |                     break
 184 |                 elif r.status_code == 429:
 185 |                     wait = 2 ** attempt
 186 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 187 |                     time.sleep(wait)
 188 |                 else:
 189 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 190 |                     if attempt < 2:
 191 |                         time.sleep(2 ** attempt)
 192 |             except Exception as e:
 193 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 194 |                 if attempt < 2:
 195 |                     time.sleep(2 ** attempt)
 196 | 
 197 |         if not success:
 198 |             for f in chunk_files:
 199 |                 try:
 200 |                     os.remove(f)
 201 |                 except Exception:
 202 |                     pass
 203 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 204 |             print(f"  [tts] ElevenLabs failed — trying pyttsx3 fallback")
 205 |             try:
 206 |                 import pyttsx3
 207 |                 _engine = pyttsx3.init()
 208 |                 _engine.setProperty("rate", 150)
 209 |                 wav_tmp = output_path + ".pyttsx3.wav"
 210 |                 _engine.save_to_file(chunk, wav_tmp)
 211 |                 _engine.runAndWait()
 212 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 213 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 214 |                     try:
 215 |                         os.remove(wav_tmp)
 216 |                     except Exception:
 217 |                         pass
 218 |                     if ok:
 219 |                         return ok
 220 |             except Exception as pyttsx_err:
 221 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 222 |             return _tts_generate_silence_fallback(text, output_path)
 223 |         chunk_files.append(mp3_tmp)
 224 | 
 225 |     if len(chunk_files) == 1:
 226 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 227 |         try:
 228 |             os.remove(chunk_files[0])
 229 |         except Exception:
 230 |             pass
 231 |         return ok
 232 | 
 233 |     # Multi-chunk concat
 234 |     concat_list = output_path + ".concat.txt"
 235 |     mp3_combined = output_path + ".combined.mp3"
 236 |     with open(concat_list, "w") as f:
 237 |         for p in chunk_files:
 238 |             f.write(f"file '{os.path.abspath(p)}'\n")
 239 |     subprocess.run(
 240 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 241 |          "-c", "copy", mp3_combined],
 242 |         capture_output=True, text=True,
 243 |     )
 244 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 245 |     for f in chunk_files + [concat_list, mp3_combined]:
 246 |         try:
 247 |             if os.path.exists(f):
 248 |                 os.remove(f)
 249 |         except Exception:
 250 |             pass
 251 |     return ok
 252 | 
 253 | 
 254 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 255 |     """Generate audio for the entire dual-host dialogue.
 256 | 
 257 |     Args:
 258 |         dialogue: List of dicts with keys:
 259 |             - host: 1 or 2 (both route to Mark), or "CLIP" (silence placeholder)
 260 |             - text: The line text (or clip description for CLIP)
 261 |             - duration: (CLIP only) silence duration in seconds
 262 |             - source: (CLIP only) source channel name
 263 | 
 264 |     Returns:
 265 |         {
 266 |             "lines": [
 267 |                 {"path": str, "host": int|"CLIP", "duration": float,
 268 |                  "start": float, "text": str},
 269 |                 ...
 270 |             ],
 271 |             "full": str,          # path to concatenated audio
 272 |             "total_duration": float,
 273 |         }
 274 |     """
 275 |     os.makedirs(output_dir, exist_ok=True)
 276 | 
 277 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 278 |     if not key:
 279 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 280 | 
 281 |     silence_path = os.path.join(output_dir, "silence.m4a")
 282 |     _generate_silence(silence_path, SILENCE_GAP)
 283 | 
 284 |     lines = []
 285 |     parts_for_concat = []
 286 |     current_time = 0.0
 287 | 
 288 |     for i, entry in enumerate(dialogue):
 289 |         host = entry.get("host")
 290 |         text = entry.get("text", "")
 291 | 
 292 |         if host == "CLIP":
 293 |             clip_dur = entry.get("duration", 0)
 294 |             lines.append({
 295 |                 "path": None,
 296 |                 "host": "CLIP",
 297 |                 "duration": clip_dur,
 298 |                 "start": current_time,
 299 |                 "source": entry.get("source", ""),
 300 |                 "query": entry.get("query", ""),
 301 |                 "text": text,
 302 |             })
 303 |             continue
 304 | 
 305 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 306 |         voice = VOICES.get(host_num, VOICES[1])
 307 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 308 | 
 309 |         print(f"  [tts] Line {i:02d} ({voice['name']}): {text[:60]}...")
 310 | 
 311 |         if tts_elevenlabs(text, line_path, host_num):
 312 |             dur = ffprobe_duration(line_path)
 313 |             lines.append({
 314 |                 "path": line_path,
 315 |                 "host": host_num,
 316 |                 "duration": dur,
 317 |                 "start": current_time,
 318 |                 "text": text,
 319 |             })
 320 |             parts_for_concat.append(line_path)
 321 |             current_time += dur
 322 | 
 323 |             if i < len(dialogue) - 1:
 324 |                 parts_for_concat.append(silence_path)
 325 |                 current_time += SILENCE_GAP
 326 |         else:
 327 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": host_num,
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "text": text,
 334 |             })
 335 | 
 336 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 337 |     if parts_for_concat:
 338 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 339 |         with open(concat_file, "w") as f:
 340 |             for p in parts_for_concat:
 341 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 342 |         subprocess.run(
 343 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 344 |              "-c", "copy", full_path],
 345 |             capture_output=True, text=True,
 346 |         )
 347 |         if os.path.exists(concat_file):
 348 |             os.remove(concat_file)
 349 | 
 350 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 351 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 352 | 
 353 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 354 | 
 355 |     return {
 356 |         "lines": lines,
 357 |         "full": full_path if os.path.exists(full_path) else None,
 358 |         "total_duration": total_dur,
 359 |     }
 360 | 
 361 | 
 362 | if __name__ == "__main__":
 363 |     from script_writer import generate_script
 364 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 365 |     script = generate_script(style=style)
 366 |     audio_dir = os.path.join(BASE, "output", "audio_test")
 367 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 368 |     print(json.dumps(
 369 |         {k: v for k, v in result.items() if k != "lines"},
 370 |         indent=2,
 371 |     ))
 372 | 
```

### File: video_pipeline_v3/tts_engine.py (420 lines)
```
   1 | #!/usr/bin/env python3
   2 | """TTS Engine V6 — Single-host Mark broadcast voice.
   3 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) at 1.10x speed — PBX approved sole narrator.
   4 | Both host=1 and host=2 route to Mark (no gender swap, no dual-host).
   5 | Generates per-line audio with 0.3s silence gaps."""
   6 | import os, sys, json, subprocess, tempfile, time, struct
   7 | from pathlib import Path
   8 | 
   9 | try:
  10 |     import requests
  11 |     HAS_REQUESTS = True
  12 | except ImportError:
  13 |     HAS_REQUESTS = False
  14 | 
  15 | from relay import get_key
  16 | 
  17 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST — Mark at 1.10x speed.
  18 | # Both host=1 and host=2 map to Mark. Deborah/Brian/Nicole/Chris are all BANNED.
  19 | _MARK_VOICE = {
  20 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  21 |     "name": "Mark",
  22 |     "model_id": "eleven_turbo_v2_5",
  23 |     "speed": 1.10,
  24 |     "voice_settings": {
  25 |         "stability": 0.55,
  26 |         "similarity_boost": 0.80,
  27 |         "style": 0.15,
  28 |         "use_speaker_boost": True,
  29 |     },
  30 | }
  31 | 
  32 | VOICES = {
  33 |     1: _MARK_VOICE,
  34 |     2: _MARK_VOICE,  # single narrator — both hosts are Mark
  35 | }
  36 | 
  37 | # Voice mode overrides for Mark (segment-type tuning)
  38 | VOICE_MODES = {
  39 |     "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18, "speed": 1.10},
  40 |     "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  41 |     "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  42 |     "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18, "speed": 1.10},
  43 |     "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20, "speed": 1.08},
  44 |     "data":            {"stability": 0.60, "similarity_boost": 0.82, "style": 0.12, "speed": 1.10},
  45 | }
  46 | 
  47 | SILENCE_GAP = 0.3  # seconds between speakers
  48 | MAX_CHUNK_CHARS = 4900
  49 | 
  50 | _KEY_CACHE: dict = {}
  51 | 
  52 | 
  53 | def _get_cached_key(name: str) -> str:
  54 |     if name not in _KEY_CACHE:
  55 |         k = get_key(name)
  56 |         if k:
  57 |             _KEY_CACHE[name] = k.strip()
  58 |     return _KEY_CACHE.get(name, "")
  59 | 
  60 | 
  61 | def ffprobe_duration(path: str) -> float:
  62 |     r = subprocess.run(
  63 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  64 |          "-of", "csv=p=0", path],
  65 |         capture_output=True, text=True,
  66 |     )
  67 |     try:
  68 |         return float(r.stdout.strip())
  69 |     except Exception:
  70 |         return 0.0
  71 | 
  72 | 
  73 | def _generate_silence(output_path: str, duration: float) -> bool:
  74 |     """Generate a silent audio file."""
  75 |     r = subprocess.run(
  76 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  77 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  78 |          "-c:a", "aac", "-b:a", "192k", output_path],
  79 |         capture_output=True, text=True, timeout=30,
  80 |     )
  81 |     return r.returncode == 0 and os.path.exists(output_path)
  82 | 
  83 | 
  84 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
  85 |     r = subprocess.run(
  86 |         ["ffmpeg", "-y", "-i", mp3_path,
  87 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
  88 |         capture_output=True, text=True, timeout=120,
  89 |     )
  90 |     return r.returncode == 0 and os.path.exists(m4a_path)
  91 | 
  92 | 
  93 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
  94 |     if len(text) <= max_chars:
  95 |         return [text]
  96 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
  97 |     sentences = raw.split("\x00")
  98 |     chunks, current = [], ""
  99 |     for sent in sentences:
 100 |         if len(current) + len(sent) + 1 <= max_chars:
 101 |             current = f"{current} {sent}".strip() if current else sent
 102 |         else:
 103 |             if current:
 104 |                 chunks.append(current)
 105 |             current = sent
 106 |     if current:
 107 |         chunks.append(current)
 108 |     return [c for c in chunks if c.strip()]
 109 | 
 110 | 
 111 | TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
 112 | 
 113 | 
 114 | def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
 115 |     """SHA256 hash of text+voice+segment_type → stable cache key."""
 116 |     import hashlib
 117 |     payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
 118 |     return hashlib.sha256(payload).hexdigest()[:16]
 119 | 
 120 | 
 121 | def _tts_cache_get(cache_key: str, output_path: str) -> bool:
 122 |     """Check TTS cache and copy to output_path if hit. Returns True on hit."""
 123 |     import shutil
 124 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 125 |     if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000:
 126 |         shutil.copy2(cache_file, output_path)
 127 |         return True
 128 |     return False
 129 | 
 130 | 
 131 | def _tts_cache_put(cache_key: str, audio_path: str) -> None:
 132 |     """Save audio to TTS cache for future runs."""
 133 |     import shutil
 134 |     os.makedirs(TTS_CACHE_DIR, exist_ok=True)
 135 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 136 |     if not os.path.exists(cache_file):
 137 |         shutil.copy2(audio_path, cache_file)
 138 | 
 139 | 
 140 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 141 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback when ElevenLabs quota is exhausted.
 142 | 
 143 |     Estimates duration from text length (~12.5 chars/sec speech rate).
 144 |     Called when both ElevenLabs AND pyttsx3 fail.
 145 |     """
 146 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 147 |     r = subprocess.run([
 148 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 149 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 150 |         output_path,
 151 |     ], capture_output=True, text=True, timeout=15)
 152 |     if r.returncode == 0 and os.path.exists(output_path):
 153 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 154 |         return True
 155 |     return False
 156 | 
 157 | 
 158 | def tts_elevenlabs(text: str, output_path: str, host: int = 1,
 159 |                    segment_type: str = "") -> bool:
 160 |     """Generate TTS for a single line using the specified host voice.
 161 | 
 162 |     Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
 163 |     copies cached audio — no ElevenLabs API call. On miss, generates and caches.
 164 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 165 |     """
 166 |     if not HAS_REQUESTS:
 167 |         # No requests lib — try pyttsx3 or silence
 168 |         return _tts_generate_silence_fallback(text, output_path)
 169 | 
 170 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 171 |     if not key:
 172 |         return _tts_generate_silence_fallback(text, output_path)
 173 | 
 174 |     voice = VOICES.get(host, VOICES[1])
 175 |     # Check TTS cache first — avoid API call if same text+voice was generated before
 176 |     cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
 177 |     if _tts_cache_get(cache_key, output_path):
 178 |         print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
 179 |         return True
 180 | 
 181 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 182 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 183 | 
 184 |     # Apply hybrid voice mode for Mark based on segment type
 185 |     voice_settings = dict(voice["voice_settings"])
 186 |     if host == 1 and segment_type in VOICE_MODES:
 187 |         mode = VOICE_MODES[segment_type]
 188 |         for k, v in mode.items():
 189 |             if k != "speed":
 190 |                 voice_settings[k] = v
 191 | 
 192 |     chunks = _chunk_text(text)
 193 |     chunk_files = []
 194 | 
 195 |     for ci, chunk in enumerate(chunks):
 196 |         body = {
 197 |             "text": chunk,
 198 |             "model_id": voice["model_id"],
 199 |             "voice_settings": voice_settings,
 200 |         }
 201 |         # Add speed parameter — use mode-specific speed for Host 1
 202 |         speed = voice.get("speed", 1.0)
 203 |         if host == 1 and segment_type in VOICE_MODES:
 204 |             speed = VOICE_MODES[segment_type].get("speed", speed)
 205 |         if speed != 1.0:
 206 |             body["speed"] = speed
 207 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 208 |         success = False
 209 | 
 210 |         for attempt in range(3):
 211 |             try:
 212 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 213 |                 if r.status_code == 200:
 214 |                     with open(mp3_tmp, "wb") as f:
 215 |                         f.write(r.content)
 216 |                     success = True
 217 |                     break
 218 |                 elif r.status_code == 429:
 219 |                     wait = 2 ** attempt
 220 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 221 |                     time.sleep(wait)
 222 |                 else:
 223 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 224 |                     if attempt < 2:
 225 |                         time.sleep(2 ** attempt)
 226 |             except Exception as e:
 227 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 228 |                 if attempt < 2:
 229 |                     time.sleep(2 ** attempt)
 230 | 
 231 |         if not success:
 232 |             for f in chunk_files:
 233 |                 try:
 234 |                     os.remove(f)
 235 |                 except Exception:
 236 |                     pass
 237 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 238 |             print(f"  [tts] ElevenLabs failed for chunk {ci} — trying pyttsx3 fallback")
 239 |             try:
 240 |                 import pyttsx3
 241 |                 _engine = pyttsx3.init()
 242 |                 _engine.setProperty("rate", 150)
 243 |                 wav_tmp = output_path + f".pyttsx3.wav"
 244 |                 _engine.save_to_file(chunk, wav_tmp)
 245 |                 _engine.runAndWait()
 246 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 247 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 248 |                     try:
 249 |                         os.remove(wav_tmp)
 250 |                     except Exception:
 251 |                         pass
 252 |                     if ok:
 253 |                         print(f"  [tts] pyttsx3 fallback SUCCESS for chunk {ci}")
 254 |                         return ok
 255 |             except Exception as pyttsx_err:
 256 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 257 |             # Final fallback: generate silence so the segment still renders
 258 |             return _tts_generate_silence_fallback(text, output_path)
 259 |         chunk_files.append(mp3_tmp)
 260 | 
 261 |     # Single chunk
 262 |     if len(chunk_files) == 1:
 263 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 264 |         try:
 265 |             os.remove(chunk_files[0])
 266 |         except Exception:
 267 |             pass
 268 |         if ok and os.path.exists(output_path):
 269 |             _tts_cache_put(cache_key, output_path)
 270 |         return ok
 271 | 
 272 |     # Multi-chunk concat
 273 |     concat_list = output_path + ".concat.txt"
 274 |     mp3_combined = output_path + ".combined.mp3"
 275 |     with open(concat_list, "w") as f:
 276 |         for p in chunk_files:
 277 |             f.write(f"file '{os.path.abspath(p)}'\n")
 278 |     subprocess.run(
 279 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 280 |          "-c", "copy", mp3_combined],
 281 |         capture_output=True, text=True,
 282 |     )
 283 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 284 |     for f in chunk_files + [concat_list, mp3_combined]:
 285 |         try:
 286 |             if os.path.exists(f):
 287 |                 os.remove(f)
 288 |         except Exception:
 289 |             pass
 290 |     if ok and os.path.exists(output_path):
 291 |         _tts_cache_put(cache_key, output_path)
 292 |     return ok
 293 | 
 294 | 
 295 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 296 |     """Generate audio for the entire dual-host dialogue.
 297 | 
 298 |     Args:
 299 |         dialogue: List of {host: 1|2|"CLIP", text: "..."}
 300 |         output_dir: Directory for audio files
 301 | 
 302 |     Returns:
 303 |         {
 304 |             "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
 305 |             "full": str,  # path to concatenated full audio
 306 |             "total_duration": float,
 307 |         }
 308 |     """
 309 |     os.makedirs(output_dir, exist_ok=True)
 310 | 
 311 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 312 |     if not key:
 313 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 314 | 
 315 |     silence_path = os.path.join(output_dir, "silence.m4a")
 316 |     _generate_silence(silence_path, SILENCE_GAP)
 317 | 
 318 |     lines = []
 319 |     parts_for_concat = []
 320 |     current_time = 0.0
 321 | 
 322 |     for i, entry in enumerate(dialogue):
 323 |         host = entry.get("host")
 324 |         text = entry.get("text", "")
 325 | 
 326 |         # Skip CLIP markers — they don't have audio
 327 |         if host == "CLIP":
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": "CLIP",
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "source": entry.get("source", ""),
 334 |                 "query": entry.get("query", ""),
 335 |                 "text": text,
 336 |             })
 337 |             continue
 338 | 
 339 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 340 |         voice = VOICES.get(host_num, VOICES[1])
 341 |         segment_type = entry.get("type", "")
 342 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 343 | 
 344 |         mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
 345 |         print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")
 346 | 
 347 |         if tts_elevenlabs(text, line_path, host_num, segment_type=segment_type):
 348 |             dur = ffprobe_duration(line_path)
 349 |             lines.append({
 350 |                 "path": line_path,
 351 |                 "host": host_num,
 352 |                 "duration": dur,
 353 |                 "start": current_time,
 354 |                 "text": text,
 355 |             })
 356 |             parts_for_concat.append(line_path)
 357 |             current_time += dur
 358 | 
 359 |             # Add silence gap between speakers (not after last line)
 360 |             if i < len(dialogue) - 1:
 361 |                 parts_for_concat.append(silence_path)
 362 |                 current_time += SILENCE_GAP
 363 |         else:
 364 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 365 |             lines.append({
 366 |                 "path": None,
 367 |                 "host": host_num,
 368 |                 "duration": 0.0,
 369 |                 "start": current_time,
 370 |                 "text": text,
 371 |             })
 372 | 
 373 |     # Concatenate all lines into full audio
 374 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 375 |     if parts_for_concat:
 376 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 377 |         with open(concat_file, "w") as f:
 378 |             for p in parts_for_concat:
 379 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 380 |         subprocess.run(
 381 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 382 |              "-c", "copy", full_path],
 383 |             capture_output=True, text=True,
 384 |         )
 385 |         if os.path.exists(concat_file):
 386 |             os.remove(concat_file)
 387 | 
 388 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 389 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 390 | 
 391 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 392 | 
 393 |     return {
 394 |         "lines": lines,
 395 |         "full": full_path if os.path.exists(full_path) else None,
 396 |         "total_duration": total_dur,
 397 |     }
 398 | 
 399 | 
 400 | # Legacy compatibility — V3 pipeline used generate_all_audio
 401 | def generate_all_audio(script: dict, output_dir: str) -> dict:
 402 |     """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
 403 |     if "dialogue" in script:
 404 |         return generate_dialogue_audio(script["dialogue"], output_dir)
 405 |     # V3 fallback
 406 |     raise RuntimeError("V4 pipeline requires dialogue-format script")
 407 | 
 408 | 
 409 | if __name__ == "__main__":
 410 |     from script_writer import generate_script
 411 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 412 |     script = generate_script(style=style)
 413 |     base = os.path.dirname(os.path.abspath(__file__))
 414 |     audio_dir = os.path.join(base, "output", "audio_test")
 415 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 416 |     print(json.dumps(
 417 |         {k: v for k, v in result.items() if k != "lines"},
 418 |         indent=2,
 419 |     ))
 420 | 
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
