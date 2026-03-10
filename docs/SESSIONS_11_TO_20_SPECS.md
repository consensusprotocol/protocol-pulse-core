# PROTOCOL PULSE — SESSIONS 11–20 OVERNIGHT BUILD SPECS
# Generated: 2026-03-10 | Batch 2 overnight build
# Gospel files already exist for N11–N14. N15–N20 specs written below.
# RULE: Every session reads PIPELINE_LAWS.md + ARTICLE_PAGE_LAWS.md if touching articles.
# RULE: Every session runs regression_test.sh — zero FAILs before commit.
# RULE: Every session commits to its own branch, pushes to origin.
# RULE: audit_gate.py runs on all branches after this batch completes before any merge.

---

## SESSION 11 — PREMIUM + STRIPE (DIRECT REVENUE)
Branch: feature/session11-premium-stripe
Gospel: ~/protocol_pulse/docs/gospels/P3_PREMIUM_STRIPE_GOSPEL.md
Route: /premium (currently live but old version), /api/v2/terminal/*

Commander tier ($49/mo). Full Stripe checkout → webhook → API key → self-service portal.

### MUST BUILD:
- /premium route: world-class upgrade page with feature comparison (Free vs Commander)
- Stripe Checkout session creation: POST /api/subscribe/commander
- Webhook handler: POST /api/stripe/webhook (payment_intent.succeeded → issue key, subscription.deleted → revoke)
- API key generation: pp_cmd_ + uuid4, stored in api_subscribers table
- Commander dashboard: /terminal/dashboard (usage stats, API key display, copy button, regenerate)
- API Playground: /terminal/playground (sandboxed demo key, live endpoint tester)
- Rate limiting: 10 req/hr free, 1000 req/hr commander
- All 5 Terminal API endpoints behind auth: /api/v2/terminal/topics /entities /sentiment /breaking /health
- SETUP.md written to ~/protocol_pulse/docs/STRIPE_SETUP.md with exact steps for PBX

### WORLD-CLASS UI:
- /premium: split comparison cards, free tier in white/gray, Commander in gold glow
- Gold "UPGRADE TO COMMANDER" CTA — pulsing subtle animation
- Feature list: checkmark icons in gold for Commander, dim for free
- Stripe Checkout redirect handles both success and cancel states
- Post-checkout: success page shows API key with copy button + "you're in" confirmation
- Commander dashboard: usage graph (requests/day), quota meter, key last-used timestamp

### LAWS (from gospel):
- Stripe keys from .env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_COMMANDER_PRICE_ID
- API keys: UUID4, never sequential
- Webhook: stripe.Webhook.construct_event() validation — 400 on failure
- Rate limit tracked in api_subscribers table with window reset logic

---

## SESSION 12 — SENTIMENT INTELLIGENCE ENGINE (AI BRAIN)
Branch: feature/session12-sentiment-intel
Gospel: ~/protocol_pulse/docs/gospels/P3_SENTIMENT_INTEL_GOSPEL.md
Routes: /intelligence (new), /api/stream/sentiment (SSE)

The AI classification layer that makes Protocol Pulse genuinely intelligent.

### MUST BUILD:
- Background service: core/services/sentiment_engine.py
  - Polls for unclassified articles every 60s
  - Uses claude-haiku-4-5-20251001 to classify each: sentiment (bullish/bearish/neutral), confidence (0-1), narrative label
  - Narrative labels: "ETF flows", "halving cycle", "regulatory clarity", "mining capitulation", "institutional adoption", "Lightning growth", "miner selling pressure", "macro correlation", "protocol development", "exchange drama"
  - Batch re-classify last 100 articles on service start
  - Store: articles.sentiment, articles.sentiment_confidence, articles.sentiment_narrative, articles.sentiment_at
- SSE endpoint: GET /api/stream/sentiment → pushes JSON on every new classification
- Sentiment API: GET /api/v2/sentiment/summary → aggregate score, dominant narrative, momentum
- /intelligence page: Signal Intelligence command center
  - Sentiment heatmap by category (color-coded: red=bearish, green=bullish, gold=neutral)
  - Dominant narrative display (large, prominent — what's the market story today)
  - Narrative momentum tracker (is the narrative intensifying or fading)
  - Anomaly alert panel (when sentiment shifts >20% in 1hr: RED ALERT displayed)
  - Entity relationship tracker: which entities (people, companies, protocols) are most mentioned with negative/positive framing
  - Live sentiment feed: articles classified in real-time with fade-in animation

### WORLD-CLASS UI:
- Deep black base, sentiment shown in color spectrum (red→yellow→green gradient)
- Dominant narrative shown in massive bold typography — the "headline of the intelligence"
- Heatmap grid: categories as cells, color = aggregate sentiment, size = volume
- Anomaly alerts: red pulsing banner at top when triggered
- All panels update via SSE — zero polling, zero page reloads

### LAWS (from gospel):
- Haiku only — never Sonnet for classification (cost)
- SSE not polling for real-time stream
- Narrative labels beyond bullish/bearish
- Anomaly detection fires when shift >20% in 1hr

---

## SESSION 13 — AFFILIATE REVENUE ENGINE (PASSIVE INCOME)
Branch: feature/session13-affiliates
Gospel: ~/protocol_pulse/docs/gospels/P3_AFFILIATES_GOSPEL.md
Routes: /bitcoin-insurance (new), /digital-residency (new), + article injection

Two live affiliate programs with proper tracking and A/B testing.

### MUST BUILD:
- Landing page: /bitcoin-insurance
  - Meanwhile Life Insurance affiliate: referralCode=KKM73K
  - CTA: "Get Your Bitcoin Life Insurance Quote" → meanwhile.app with referral code
  - Copy: sovereignty framing, protect your stack for your family, tax-advantaged
  - Trust signals: meanwhile's credentials, typical coverage amounts
- Landing page: /digital-residency
  - RNS.ID Palau Digital Residency: $300/referral
  - CTA: "Get Your Digital Residency" → RNS.ID with referral tracking
  - Copy: sovereignty/privacy framing, second residency, global citizen
- Contextual article injection service: core/services/affiliate_injector.py
  - Claude Haiku analyzes article content on save → decides which affiliate fits
  - Meanwhile: articles about wealth/insurance/sovereignty/estate-planning
  - RNS.ID: articles about regulation/privacy/sovereignty/residency
  - Never both on same article. Never on breaking news.
  - Injects tasteful CTA card at article bottom (not mid-article)
- Click tracking: GET /api/affiliate/click?partner=meanwhile&article_id=X
  - SHA256(ip + date + TRACKING_SALT) → user_hash stored
  - Redirect to affiliate URL with referral code
  - affiliate_clicks table: partner, article_id, user_hash, variant (A or B), timestamp
- A/B testing: 50/50 split per SHA256(ip+date) → Variant A (text) or B (card)
  - After 200 clicks per variant: evaluate winner in admin panel

### WORLD-CLASS UI (landing pages):
- Dark cyberpunk aesthetic matching site
- Strong sovereignty/freedom framing (Bitcoin audience)
- Social proof: "X Protocol Pulse readers have protected their stack"
- Hero section with powerful visual: for Meanwhile = family/legacy, for RNS.ID = globe/passport
- FAQ section addressing common objections
- Clear single CTA — no distractions

### LAWS (from gospel):
- Contextual relevance only — never random banners
- A/B test every variant (50/50)
- Hash IPs — never store raw

---

## SESSION 14 — MARKET BRIEFING ROOM (HEYGEN 3X/DAY)
Branch: feature/session14-briefing-room
Gospel: ~/protocol_pulse/docs/gospels/F2_BRIEFING_ROOM_GOSPEL.md
Route: /briefing (new, replaces stub)

Scheduled HeyGen Sarah briefings. 3x/day. Auto-scripted by Claude. Archive-able.

### MUST BUILD:
- Scheduler: core/services/briefing_scheduler.py
  - Cron: 06:45 ET, 09:15 ET, 16:15 ET (15 min before scheduled time = generation window)
  - Script generation: Claude Sonnet writes 90-second briefing from top articles + BTC data
  - HeyGen API call: POST /v2/video/generate with avatar d259c335741f4fc0b061e04c59388b4e
  - Poll for completion: GET /v2/video/{video_id} every 30s until status=completed
  - Store video URL in briefings table: id, title, video_url, script, created_at, briefing_time
  - Cost guard: if briefings_today >= 3: skip and log (never exceed 3x/day budget)
  - On HeyGen failure: log, do NOT retry more than twice, mark as failed
- /briefing page:
  - Latest briefing video (embedded, auto-plays muted on load)
  - Schedule display: "Next briefing at 4:30 PM ET" with countdown timer
  - Full archive grid: all past briefings with thumbnail, title, date, duration
  - Each briefing: click to expand with full script shown below video
  - Briefing categories: "Pre-Market" / "Market Open" / "Market Close" with icons
- briefings table migration: CREATE TABLE IF NOT EXISTS briefings(...)

### WORLD-CLASS UI:
- Video player: custom controls, dark themed, gold progress bar
- "LIVE IN Xh Xm" countdown to next briefing — updates in real-time
- Archive: masonry grid, each card shows video thumbnail + briefing time badge
- Script toggle: "Read Script" button below each video
- Sarah's face/voice = trust anchor — professional broadcast aesthetic

### LAWS (from gospel):
- HeyGen Sarah ONLY (avatar d259c335741f4fc0b061e04c59388b4e)
- $1/min — cap at 2 min per briefing = $6/day
- 3 briefings/day MAXIMUM — cost guard enforced in code
- Never retry HeyGen more than twice on failure

---

## SESSION 15 — HOMEPAGE WORLD-CLASS UPGRADE
Branch: feature/session15-homepage
Route: / (upgrade existing)

The first impression. Currently functional but not world-class.

### MUST BUILD:
- Hero section: animated BTC price display (large, prominent, live-updating via /api/btc-price)
  - Price changes: smooth number transition animation (count up/down)
  - 24hr change shown: green up arrow or red down arrow + percentage
  - "LIVE" pulsing dot indicator
- Above-the-fold intelligence strip (below hero):
  - Block height | Mempool (sat/vB) | Fear & Greed | Hashrate | Next halving countdown
  - All live data, each with subtle animated update flash
  - Compact monospace display, gold values, dark background
- Featured article carousel: top 3 articles by score, large card format, 5s auto-advance
  - Cover image background, title overlay, category badge, reading time
  - Manual prev/next navigation
- Article grid: 12 most recent articles in 3-column responsive grid
  - Each card: cover image, title, category, sentiment badge, timestamp
  - Hover: card lifts with gold border glow
- Category filter bar: All | Markets | Mining | Layer2 | Regulation | Macro
  - Client-side filter — no page reload
- "Signal Intelligence" teaser strip: 3 sentiment metrics, link to /intelligence
- Footer upgrade: links, social icons (X, Nostr, YouTube), newsletter CTA

### WORLD-CLASS UI:
- Full viewport hero with subtle parallax on BTC price
- Cyberpunk grid overlay on hero background (very subtle, CSS only)
- Color language: dark navy base, gold for prices/highlights, red for alerts, white for text
- No white space that feels empty — every section has purpose and data
- Mobile: single column, hero price stays prominent, article grid becomes 1-col
- Lighthouse target: ≥ 90 mobile, ≥ 95 desktop

---

## SESSION 16 — CYPHERPUNK'D PODCAST PAGE
Branch: feature/session16-podcast
Route: /podcast (currently 404), /podcast/<slug>

CypherPunk'd is a core product. It has no page. Fix that.

### MUST BUILD:
- /podcast: episode listing page
  - Hero: show branding, description "The uncensored voice of Bitcoin sovereignty"
  - Subscribe strip: Apple Podcasts | Spotify | YouTube | RSS links
  - Episode grid: cover art, title, guest name, episode number, date, duration
  - Latest episode plays inline (audio player, gold themed)
  - Search: filter episodes by guest name or keyword
- /podcast/<slug>: individual episode page
  - Full episode embed (YouTube or audio player)
  - Guest bio section with photo, title, links
  - Episode show notes (markdown rendered)
  - Key timestamps (chapter markers)
  - Related episodes (3 suggestions based on tags)
  - Share buttons: X, Nostr, copy link
- Database: podcasts table
  - id, slug, title, guest_name, guest_bio, guest_image_url, episode_number, 
    youtube_url, audio_url, duration, published_at, show_notes, tags, featured
- Seed data: 10 real CypherPunk'd episodes from memory/available data
  - Known guests: Knut Svanholm, Luke Dashjr, Natalie Brunell, Bruce Barone Jr,
    Joseph Welbourn (Carbon Marine), Michelle Weekley (ByteFederal)
- Admin: /admin/podcast/add — form to add new episodes
- RSS feed: /podcast/feed.xml (valid podcast RSS for Apple/Spotify submission)

### WORLD-CLASS UI:
- Show art prominent — large, bold, professional
- Episode cards: rich media (cover image + guest photo overlay)
- Audio player: custom styled, waveform visualization, playback speed control
- Guest spotlight: each guest gets a mini-profile card
- "Now Playing" sticky bar at bottom when episode is active

---

## SESSION 17 — GLOBAL SEARCH
Branch: feature/session17-search
Route: /search (new), + search bar in nav

Search across 1,300+ articles, episodes, and events. Real-time, no page reload.

### MUST BUILD:
- Search index: core/services/search_service.py
  - SQLite FTS5 (Full Text Search) index on articles: title + content + category + tags
  - Also indexes: podcast episodes (title + guest + show notes), events (title + speakers)
  - Index rebuilt on new article creation (async, <1s)
  - Supports: phrase search ("lightning network"), boolean (bitcoin AND mining), fuzzy
- GET /api/search?q=query&type=all|articles|podcast|events&limit=20
  - Returns ranked results with snippet (150 chars around match, match terms bolded)
  - Response time target: <200ms for any query
- /search page:
  - Large search input, centered, autofocus, gold ring on focus
  - Real-time results as-you-type (debounced 300ms)
  - Result tabs: All Results | Articles | Podcast | Events
  - Each result: title, snippet, category badge, date, result type icon
  - No results state: "Nothing found for X — try [suggested terms]"
  - Popular searches: 5 trending queries shown before typing
- Nav bar: search icon that expands to inline search input on click
  - cmd+K keyboard shortcut opens search from anywhere
  - ESC closes it
  - Results dropdown overlay (max 5) with "see all results" link

### WORLD-CLASS UI:
- Search feels instant — debounce + optimistic UI
- Highlighted match terms in snippets (bold, gold color)
- Keyboard-navigable results (arrow keys + enter)
- Search as a command palette: /search also shows site navigation options

---

## SESSION 18 — CURATED MINING LANDING PAGE
Branch: feature/session18-curated-mining
Route: /mining (new standalone page)

Curated Mining = white-glove Bitcoin mining service. LLC partnership + Section 179 tax benefits.

### MUST BUILD:
- /mining: standalone landing page (NOT inside the app nav — this is a conversion page)
  - Hero: "MINE BITCOIN. OWN YOUR FUTURE." — bold, cinematic
  - Value prop: white-glove setup, LLC structure, Section 179 depreciation
  - 3-step process: (1) Consult → (2) Deploy → (3) Mine
  - Benefits section: tax advantages, passive income, sovereignty, energy arbitrage
  - Hardware section: ASIC miner showcase (S21 Pro, Antminer models) with specs
  - Calculator: estimated monthly BTC earned based on hashrate input
    - Inputs: budget ($), power cost ($/kWh) — sliders
    - Output: estimated monthly BTC, USD value, payback period
    - Live BTC price from /api/btc-price
    - Disclaimer: estimates only, not financial advice
  - Section 179 callout: "Deduct up to $1.16M in year 1" — link to IRS guidance
  - LLC structure benefits: liability protection, pass-through taxation
  - CTA: "Schedule Your Mining Consultation" → mailto:john@curatedmining.com
    OR embedded Calendly-style form
  - Trust signals: Consensus Protocol LLC, Naples FL, Protocol Pulse media partner
- Mining calculator API: GET /api/mining/estimate?budget=X&power_cost=Y
  - Real hashrate data from mining pool APIs
  - Current network difficulty + block reward

### WORLD-CLASS UI:
- Premium, not scrappy — this is a high-ticket service page
- Dark base with gold accents (money/prestige aesthetic)
- Calculator interactive and smooth — sliders update results instantly
- Mining hardware images (sourced from manufacturer sites or stock)
- Mobile: calculator works perfectly on phone
- CTA button: prominent, gold background, black text, large

---

## SESSION 19 — ADMIN INTELLIGENCE DASHBOARD
Branch: feature/session19-admin-dashboard
Route: /admin (upgrade existing or create comprehensive new)

PBX needs to see everything in one place. Article pipeline health, subscribers, system status.

### MUST BUILD:
- /admin (requires admin auth — check existing auth pattern): comprehensive ops dashboard
- SECTION 1: Pipeline Health
  - Article generation: articles in last 24h, 7d, 30d with sparkline
  - Video pipeline: last render timestamp, Gemini grade, next scheduled run
  - Briefing Room: today's briefings (sent/failed), next scheduled
  - ElevenLabs quota: remaining credits, daily burn rate
  - HeyGen quota: remaining credits, daily burn rate
- SECTION 2: Audience
  - Newsletter subscribers: total, new today, new this week, unsubscribes
  - Last email sent: subject, open rate, click rate (from Resend API)
  - Next email: scheduled time, preview link
- SECTION 3: Content
  - Article queue: articles awaiting publication, articles with errors
  - Top 10 articles by views (last 7d)
  - Sentiment distribution donut chart (bullish/bearish/neutral %)
  - Active affiliate CTAs: click counts, conversion estimates
- SECTION 4: System
  - Ultron health: CPU %, RAM %, disk %, GPU %, GPU temp
  - Flask uptime, last restart
  - Active cron jobs: last run time, next run, status (green/red)
  - Recent errors from gunicorn_error.log (last 10, with level + message)
- SECTION 5: Revenue (if Stripe connected)
  - MRR, active Commander subscribers, churned this month
  - Recent payments table

### WORLD-CLASS UI:
- Bloomberg-style operator dashboard — dense, data-rich, monospace
- Color coding: green=healthy, gold=warning, red=critical
- Auto-refresh every 30s without page reload (fetch API)
- Collapsed sections by default, expand on click
- Mobile: single column, all sections stack

---

## SESSION 20 — PRICE ALERT + NOTIFICATION SYSTEM
Branch: feature/session20-price-alerts
Route: /alerts (new), /api/alerts/* 

BTC price alerts via email. Users set targets, system fires when price crosses.

### MUST BUILD:
- /alerts page:
  - "Set a Price Alert" form: email, target price, direction (above/below)
  - Active alerts display (for email-verified users)
  - Alert history: triggered alerts with timestamp and price at trigger
- Database: price_alerts table
  - id, email, target_price, direction (above/below), triggered_at, created_at, active
- Alert engine: core/services/alert_engine.py
  - Runs every 5 min (cron) — checks current BTC price vs all active alerts
  - On trigger: send email via Resend API, mark alert as triggered
  - Email template: "🚨 BTC hit your target of $X — current price: $Y"
    Include: current price, 24hr change, link to /charts, "Set another alert" link
  - Rate limit: max 3 active alerts per email address
  - Unsubscribe link in every alert email (one-click deactivate)
- Double opt-in:
  - On alert creation: send confirmation email with verify link
  - Alert only activates after email confirmed
  - Unconfirmed alerts expire after 24hrs
- POST /api/alerts/create — create new alert
- GET /api/alerts/verify?token=X — email verification
- DELETE /api/alerts/cancel?token=X — one-click cancel from email

### WORLD-CLASS UI:
- Clean, focused single-purpose page
- Price input: formatted with $ and commas as you type
- Visual: BTC price chart (7d) with alert target shown as a horizontal line
- "Above" vs "Below" toggle: above = green arrow, below = red arrow
- Confirmation state: "Alert set — check your email to activate"
- Active alerts list: each shows target, current distance ("BTC is $X away from your alert")
