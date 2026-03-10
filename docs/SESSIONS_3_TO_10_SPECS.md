# SESSIONS 3–10: PARALLEL BUILD SPECS
# All sessions fire simultaneously. Each works in its own blueprint file.
# routes.py is deprecated — all new code goes in core/blueprints/<name>.py
# Every session: branch → build → regression → commit+push. No pauses.

---

# SESSION 3 — MEDIA UNIFIED
# Branch: feature/session3-media-unified
# File: core/blueprints/media.py + core/templates/media_unified.html

## FORENSIC AUDIT OF CURRENT STATE
- /media returns 200 but pulls from media_hub.html + media_terminal.html (two separate files)
- Fake X feed hardcoded — not real Nostr/X data
- Hardcoded quotes throughout — not live
- Telemetry/sentiment panels show static placeholder values
- Signal Strength composite not wired to any real computation
- No real Nostr relay data anywhere

## WHAT TO BUILD

### Frontend: single media_unified.html
Dark full-bleed layout. Two-column desktop (signal/intel left, feeds right). Single column mobile.

HEADER BAR (fixed):
- Left: "PROTOCOL PULSE // MEDIA INTELLIGENCE"
- Center: Signal Strength composite score (live, colored by strength)
- Right: UTC clock + LIVE dot

COLUMN 1 — INTELLIGENCE PANELS:
Panel A — Signal Strength Composite:
  - Overall score 0-100 with color coding (red <30 / amber 30-60 / green >60)
  - Sub-components: Article Velocity, Sentiment Trend, Network Activity, Social Volume
  - Each with mini bar and delta from 24h ago
  - Wire to /api/signal/composite (create this endpoint)

Panel B — Sentiment Heatmap:
  - Category grid: Mining, Regulation, ETFs, Lightning, DeFi, Macro
  - Each cell: color-coded sentiment + article count in last 2h
  - Real data from PP article tags/categories in DB
  - Wire to /api/sentiment/heatmap endpoint

Panel C — Trending Topics:
  - Top 10 topics ranked by velocity (articles/hour)
  - Each: topic name, count, 1h trend arrow, mini sparkline
  - Wire to /api/v2/terminal/topics

Panel D — Source Health Monitor:
  - Grid of 12 key sources (top channels by tier)
  - Each: source name, last scraped, articles today, status dot (green/amber/red)
  - Wire to /api/media/sources/health

COLUMN 2 — LIVE FEEDS:
Panel E — Virtual Intelligence Feed (replaces fake X):
  - NOT a fake X/Twitter feed
  - Instead: "PP INTELLIGENCE STREAM" — live articles from PP pipeline
  - Each entry: timestamp, title, source channel, sentiment badge, link
  - Real-time via SSE or 30s polling
  - Wire to /api/media/feed/intelligence

Panel F — Nostr Relay Manager:
  - Connect to 3 default relays: wss://relay.damus.io, wss://nos.lol, wss://relay.nostr.band
  - Show relay status: connected/disconnected, message rate, latency
  - Display last 10 Bitcoin-tagged Nostr events (kind:1 with #bitcoin)
  - Wire to WebSocket client in JS connecting to public Nostr relays
  - Fallback: show "Connecting to Nostr network..." if no WS support

Panel G — Health Strip (bottom, full width):
  - 8 metric pills: BTC Price | Mempool | Hashrate | Nodes | Fear/Greed | Articles/hr | Sentiment | Signal
  - All live, all updating, all clickable to relevant section
  - Color coded by status

## BANNED (per MEDIA_UNIFIED spec):
- NO fake X/Twitter feed
- NO hardcoded quotes
- NO static placeholder values
- NO Three.js, VR, DAO, quantum auth, Sora, genetic algorithms

## BACKEND ADDITIONS to core/blueprints/media.py:
GET /api/signal/composite — weighted signal from all sources, cached 2min
GET /api/sentiment/heatmap — category sentiment from last 2h of articles
GET /api/media/sources/health — scraper source status from last_scraped timestamps
GET /api/media/feed/intelligence — latest 20 PP articles with sentiment badges
SSE /api/media/feed/stream — server-sent events for real-time feed updates

---

# SESSION 4 — CHARTS
# Branch: feature/session4-charts
# File: core/blueprints/charts.py + core/templates/charts.html

## FORENSIC AUDIT OF CURRENT STATE
- /charts returns 200 (merged from p3-charts branch)
- Unknown what data is actually wired vs placeholder
- Need real chart data for all timeframes

## WHAT TO BUILD

### Frontend: charts.html
Bloomberg terminal aesthetic — matches /terminal visual language exactly.
Full-width chart area. Left sidebar for chart selector. Right sidebar for stats.

CHART SELECTOR (left sidebar, 200px):
Categories:
  PRICE: BTC/USD (all timeframes)
  NETWORK: Hashrate, Difficulty, Block Time
  VALUATION: MVRV Z-Score, Realized Price, Stock-to-Flow
  MARKET: Fear & Greed History, Dominance
  FEES: Fee Market History, Mempool Size

Each chart selector item: chart name + current value + 7d delta

MAIN CHART AREA:
- D3.js for all charts (import from CDN)
- Timeframe selector: 1D / 7D / 1M / 3M / 1Y / ALL
- Crosshair cursor with tooltip showing exact value + date
- Chart bg: #080810, gridlines: #1C1C2E (subtle)
- Line color: GOLD (#F59E0B) for price, CYAN for network metrics
- Area fill: gradient from line color to transparent
- Axis labels: monospace, TEXT_LABEL color
- On mobile: hide left sidebar, show chart selector as horizontal scroll tabs

STATS SIDEBAR (right, 200px desktop / hidden mobile):
Current chart stats: current value, ATH, ATL, 24h/7d/30d change
Rolling statistics: avg, median, std dev for selected timeframe

### DATA SOURCES (all server-side cached, never expose keys):
BTC price history: CoinGecko /coins/bitcoin/market_chart (free tier, cache 5min)
Hashrate/Difficulty: mempool.space /api/v1/mining/hashrate/3y
MVRV: Glassnode free endpoints or CryptoQuant public
Fear & Greed history: alternative.me /fng/?limit=365
Realized Price: computed from UTXO data or CryptoQuant public

### BACKEND: core/blueprints/charts.py
GET /api/charts/price?period=7d — OHLCV data, server-cached
GET /api/charts/hashrate?period=1y — hashrate history
GET /api/charts/difficulty?period=1y — difficulty history  
GET /api/charts/fear-greed?period=365d — F&G history
GET /api/charts/mvrv?period=1y — MVRV history
GET /api/charts/realized-price?period=1y — realized price history
All endpoints: {"data": [[timestamp, value], ...], "cached_until": "...", "source": "..."}

### OG IMAGE FOR SHARING:
GET /api/charts/og-image?chart=price&period=7d
Generates PNG of current chart via matplotlib server-side
Returns image for social sharing / embeds

---

# SESSION 5 — MINING INTEL
# Branch: feature/session5-mining-intel
# File: core/blueprints/mining.py + core/templates/mining_intel.html

## FORENSIC AUDIT
- /mining-risk returns 200 (merged from p3-mining-intel)
- Actual content unknown — likely placeholder

## WHAT TO BUILD

### Page purpose: dual mission
1. Intelligence tool for Bitcoin miners tracking profitability/difficulty
2. Curated Mining lead generation — every data point connects back to "want help optimizing this? → Curated Mining"

### Frontend: mining_intel.html
Dark theme, same aesthetic system. Three sections.

SECTION 1 — MINING DASHBOARD (live data):
Panel A — Current Profitability:
  HASHPRICE ($/TH/day): [live]  ← the single most important metric for miners
  NETWORK HASHRATE: [EH/s]
  NEXT DIFFICULTY ADJ: [% up/down] in [days]
  BLOCK SUBSIDY: 3.125 BTC (until next halving)
  AVG BLOCK REWARD (with fees): [BTC]
  
Panel B — Miner Revenue (30-day):
  Total miner revenue: [BTC] + [$USD]
  Subsidy vs fees breakdown: [bar chart D3]
  Revenue trend: sparkline

Panel C — Pool Market Share:
  Top 8 pools: name, % hashrate, blocks last 24h
  D3 horizontal bar chart
  Source: mempool.space pool stats

Panel D — Hardware Efficiency Tracker:
  Table: ASIC model | TH/s | W/TH | Daily revenue at current hashprice | Break-even BTC price
  Pre-populated with: S21 Pro, S21, T21, S19 XP, S19 Pro
  User can input their own electricity cost ($/kWh) to see their specific P&L
  Electricity input: slider 0.03–0.15 $/kWh, updates all calculations live

SECTION 2 — BLOCKWARE INTELLIGENCE (curated external analysis):
  - Monitor Blockware Intelligence Substack (RSS feed)
  - Show last 5 articles: title, date, 2-sentence summary, "READ FULL ANALYSIS →" link
  - Label: "EXTERNAL ANALYSIS — BLOCKWARE INTELLIGENCE"
  - Update: daily

SECTION 3 — CURATED MINING CTA (not an ad — a genuine offer):
Full-width section, dark with subtle gold border:
  "OPTIMIZE YOUR OPERATION"
  Headline: "You're tracking the data. Let us handle the hardware."
  3 value props:
    - "White-glove procurement — best ASICs at wholesale pricing"
    - "LLC structure + Section 179 tax optimization"
    - "Ongoing support from active miners"
  CTA: [GET A FREE MINING ASSESSMENT] → mailto:john@curatedmining.com
  Secondary: [LEARN MORE ABOUT CURATED MINING] → /curated-mining page

### BACKEND: core/blueprints/mining.py
GET /api/mining/dashboard — hashprice, hashrate, next difficulty, block reward (mempool.space)
GET /api/mining/pools — pool market share (mempool.space)
GET /api/mining/profitability?electricity=0.07 — profitability calculator, returns per-model data
GET /api/mining/blockware — Blockware RSS parsed, cached 4h
All server-cached appropriately.

---

# SESSION 6 — SCHIFF BOT
# Branch: feature/session6-schiff-bot
# File: core/blueprints/schiff.py + core/templates/schiff_bot.html

## WHAT THIS IS
Peter Schiff is Bitcoin's most famous persistent critic. He debates Bitcoin on CT constantly.
The Schiff Bot is an AI that argues Schiff's positions — gold > Bitcoin, inflation hedge narrative,
"Bitcoin has no intrinsic value" — while the user argues back for Bitcoin.
It's educational, entertaining, and deeply shareable. Cypherpunk humor meets serious macro debate.

## FRONTEND: schiff_bot.html
Visual concept: split screen. Left: Peter Schiff avatar (static image, gold background, old-school).
Right: Bitcoin logo / orange background. Center: chat interface.

HEADER: "DEBATE THE SCHIFF BOT — Can you out-argue the most famous Bitcoin skeptic?"

CHAT INTERFACE:
- Standard chat UI but styled terminal-dark
- Schiff messages: left-aligned, avatar thumbnail, gold text on dark bg
- User messages: right-aligned, orange/white
- Input: "Make your case for Bitcoin..." placeholder
- Send button: "ARGUE →"

SCHIFF'S OPENING LINE (random from pool of 5, loads on page open):
1. "Bitcoin is a speculative bubble with no intrinsic value. Gold has been money for 5,000 years."
2. "Tell me — what can you DO with Bitcoin that you can't do with gold or dollars?"
3. "Bitcoin consumes more electricity than some countries. That's not sound money, that's waste."
4. "The government will simply ban Bitcoin when it becomes a real threat. They did it with gold in 1933."
5. "Every institution that has bought Bitcoin has done so as speculation. Gold is a store of value."

SCHIFF AI PERSONA (system prompt to Claude API):
You are Peter Schiff, the Austrian economist and gold bug, debating Bitcoin.
Argue EXACTLY as Peter Schiff does:
- Gold has 5,000 years of history; Bitcoin has 15
- Bitcoin has no intrinsic value, no industrial use
- Fiat inflation hedge: gold proven, Bitcoin speculative
- Government will regulate/ban it when threatened
- Bitcoin is rat poison: Schiff quotes Buffett approvingly
- Energy waste argument
- "Digital gold" is marketing, not substance
- Every price rise is a bubble; every crash is the end
Stay in character. Be combative but not rude. Make the BEST case for the gold/skeptic position.
After 6 exchanges, end with: "I'll give you this — you Bitcoin people are persistent. Wrong, but persistent."

SHARE MECHANIC:
After each Schiff response, show: [SHARE THIS DEBATE] button
Generates a screenshot-ready card: "I debated the Schiff Bot and [won/survived/got wrecked]"
Share to Twitter/X prepopulated: "I just debated the Schiff Bot on @ProtocolPulse and [outcome]. Can you do better? [link]"

SIDEBAR (desktop):
"SCHIFF'S GREATEST HITS" — 5 real Peter Schiff quotes with dates
"BITCOIN'S RESPONSE" — Bitcoin price on that date vs today
e.g., "Bitcoin is a fraud" — Oct 2017 — BTC was $5,800 then / $85,000 now

### BACKEND: core/blueprints/schiff.py
POST /api/schiff/chat:
  Body: {"message": "user argument", "history": [...previous turns...]}
  Calls Claude API (claude-sonnet-4-20250514, $0.003/msg) with Schiff system prompt
  Returns: {"response": "...", "exchange_count": n}
  Rate limit: 10 exchanges per IP per hour (prevent abuse)
  Cache nothing (each debate is live)

---

# SESSION 7 — ORACLE AVATAR
# Branch: feature/session7-oracle-avatar
# File: core/blueprints/oracle_avatar.py + core/templates/oracle_live.html

## FORENSIC AUDIT
- /oracle-live returns 200 (merged f1-avatar-oracle branch)
- Oracle avatar_server.py running on port 8200 (Wav2Lip)
- HeyGen Sarah avatar: d259c335741f4fc0b061e04c59388b4e ($1/min)
- HeyGen PBX Digital Twin: 3be8ed14b0954b898f4127836c21f6cc ($2/min)
- KNOWN ISSUE: apply_blink() creates black oval artifacts — body must return frame (no-op)

## WHAT TO BUILD

### ORACLE LIVE PAGE (oracle_live.html):
Dark cinematic page. Not a terminal — this is broadcast quality.

HERO VIDEO PLAYER:
- Displays current Oracle Briefing video
- Autoplay muted (browser policy), unmute button prominent
- Shows: today's Oracle briefing (3-4 min HeyGen Sarah video)
- Below player: transcript accordion (click to expand full script)
- Share button: "Share this briefing"

BRIEFING SCHEDULE DISPLAY:
- "TODAY'S BRIEFINGS" section
- Morning (8am ET): Market Open briefing — BTC overnight, key levels, sentiment
- Midday (12pm ET): Mid-session update — mempool, fee market, notable articles
- Evening (5pm ET): Daily close briefing — day summary, Signal score, tomorrow outlook
- Each slot: video thumbnail + title + duration + "WATCH" button
- If not yet generated: "GENERATING..." with ETA

BRIEFING ARCHIVE:
- Last 7 days of briefings in a grid
- Each: thumbnail, date, title, duration, watch button
- Videos stored at video.protocolpulse.io

LIVE STATUS PANEL (sidebar):
- Oracle system status: HeyGen API ✓, ElevenLabs ✓, Script gen ✓
- Next scheduled briefing: countdown timer
- Last generated: [time ago]
- Today's briefings generated: [n]/3

### AUTOMATED BRIEFING GENERATION (core/services/oracle_scheduler.py):
Schedule: 3x daily (7:45am, 11:45am, 4:45am ET — 15min before publish time)
For each briefing:
  1. Pull live data: BTC price, Signal score, top 3 articles, mempool, Fear & Greed
  2. Generate script via Claude API (600-800 words, Sarah voice, Oracle persona)
     Sarah persona: authoritative, calm, intelligence analyst energy
     Opening: "Good [morning/afternoon/evening]. I'm Oracle, and this is your Protocol Pulse briefing for [date/time]."
  3. Submit to HeyGen API with Sarah avatar ID
  4. Poll for completion (HeyGen async, ~2-4min)
  5. Download MP4 to ~/protocol_pulse/static/oracle/briefings/
  6. Update oracle_briefings table in DB
  7. Serve via video.protocolpulse.io

### HEYGEN INTEGRATION (core/services/heygen_service.py):
Already exists from f1-avatar-oracle — verify it works with current HeyGen API.
Fix any auth issues (HEYGEN_API_KEY from .env).
Add retry logic: if generation fails, retry once after 60s.
Cost tracking: log each generation with cost estimate to oracle_costs table.

### BACKEND: core/blueprints/oracle_avatar.py
GET /oracle-live — main page
GET /api/oracle/briefings — list today's + last 7 days
GET /api/oracle/status — system health, next scheduled, last generated
POST /api/oracle/generate — manual trigger (admin only, IP-gated to Ultron)

---

# SESSION 8 — NOSTR FEED
# Branch: feature/session8-nostr
# File: core/blueprints/nostr.py + (integrated into media_unified.html Panel F)

## NOTE: Nostr is already partially specced in Session 3 (Media Unified Panel F).
## Session 8 makes it production-grade as a standalone feature.

## WHAT TO BUILD

### NOSTR INTEGRATION ARCHITECTURE:
The browser connects directly to Nostr relays via WebSocket (client-side).
The server provides relay configuration and caching (server-side).

DEFAULT RELAYS (configurable):
- wss://relay.damus.io (largest, most reliable)
- wss://nos.lol (fast, well-maintained)
- wss://relay.nostr.band (good search/aggregation)
- wss://nostr.wine (curated, high quality)

### NOSTR PAGE (/nostr):
Dark terminal aesthetic. Real-time feed of Bitcoin-tagged Nostr events.

RELAY STATUS BAR (top):
- 4 relay pills: each shows name, connection status (green/red), latency, events/min
- "Connected to [n]/4 relays" summary
- Reconnect button for failed relays

FILTER BAR:
- Tags: #bitcoin #btc #lightning #nostr (multi-select toggle)
- Event kinds: Notes (1), Reposts (6), Reactions (7)
- Time: Last hour / Last 6h / Last 24h
- Search: keyword filter (client-side)

LIVE FEED:
- Events scroll up as they arrive (newest at top)
- Each event: avatar (Robohash fallback) + npub truncated + content preview (200 chars) + timestamp + like/zap/reply counts
- Click to expand full event
- External link: open in Snort/Primal/Nostrudel

RELAY MANAGER:
- Add custom relay: input + connect button
- Remove relay: X on each pill
- Relay config saved to localStorage
- Show relay NIP support: NIP-01, NIP-04, NIP-09, etc.

### NOSTR STATS PANEL (sidebar):
- Events received this session: [n]
- Active pubkeys seen: [n]
- Top hashtags in last hour (besides #bitcoin)
- Most active hour today

### BACKEND: core/blueprints/nostr.py
GET /nostr — page route
GET /api/nostr/relays — default relay list with metadata
GET /api/nostr/cache — last 50 cached events (server pre-fetches for faster initial load)
POST /api/nostr/relay/add — validate and add relay to user's config
Server-side: background worker subscribes to relays, caches last 50 Bitcoin events in memory for fast initial page load. Client WebSocket takes over after page load.

---

# SESSION 9 — NODE WATCH
# Branch: feature/session9-node-watch
# File: core/blueprints/node_watch.py + core/templates/node_watch.html

## WHAT TO BUILD

### Page: /node-watch (or wire into /terminal as a panel — CC decides which is cleaner)

HERO STATS (top row, always visible):
- REACHABLE NODES: [live from Bitnodes API]
- UNREACHABLE NODES: [live]
- TOTAL NODES (est): [live]
- NODES LAST 24H: delta ▲/▼ [n]
- IPV4 / IPV6 / TOR / I2P breakdown (pie or bar)

GEOGRAPHIC DISTRIBUTION:
- Top 15 countries by node count: table + horizontal bar chart (D3)
- Country | Nodes | % | 7d trend
- Highlight top 5: US, Germany, France, Netherlands, Canada typically

VERSION DISTRIBUTION:
- Bitcoin Core versions: breakdown by count + %
- Show: which % is on latest vs outdated versions
- "Latest: Bitcoin Core 28.0" with node % running it

NETWORK HEALTH SCORE (PP proprietary):
- Composite 0-100 from: node count trend, version currency, geographic distribution, tor %, uptime
- Colored gauge: red/amber/green
- "Network health is [STRONG/MODERATE/WEAK] — [one sentence reason]"

MAP (if feasible with a free map library):
- Leaflet.js (open source, free CDN) dot map of node geographic distribution
- Dots sized by node count, colored by concentration
- Fallback: country table if map is too slow

HISTORICAL CHARTS (D3):
- Node count 1Y history
- Version adoption curve over time

### BACKEND: core/blueprints/node_watch.py
GET /api/nodes/summary — reachable/unreachable/total, IPvX breakdown (Bitnodes /api/v1/snapshots/latest/)
GET /api/nodes/countries — geographic distribution (Bitnodes /api/v1/nodes/leaderboard/)
GET /api/nodes/versions — version distribution (Bitnodes snapshot data)
GET /api/nodes/history — node count history (Bitnodes /api/v1/snapshots/?limit=365)
All cached: summary 5min, geographic 1h, versions 1h, history 24h

---

# SESSION 10 — ARTICLE PAGE WORLD-CLASS REBUILD
# Branch: feature/session10-articles
# File: core/blueprints/articles.py (already exists from Session 2) + full template rebuild

## FORENSIC CONTEXT (from ARTICLE_PAGE_LAWS.md):
- 16 different article creation paths in routes.py (now blueprints/articles.py)
- 8,472 lines in original routes.py — article routes were the heaviest section
- Broken images widespread (wrong URL patterns, missing files)
- No consistent template — articles render differently based on creation path
- Cover images: 90% Pexels stock (cover_image_url column), 10% Grok hyper-realistic

## WHAT TO BUILD

### ARTICLES LIST PAGE (/articles):
Dark terminal aesthetic. Three-column grid desktop, two-column tablet, single mobile.

HEADER:
- "PROTOCOL PULSE // INTELLIGENCE FEED"
- Article count: "1,342 articles across 23 categories"
- Search bar: live search (client-side filter on article titles/summaries)
- Filter pills: All | Mining | Regulation | ETFs | Lightning | Macro | Technical | Editorial

ARTICLE CARDS:
Each card:
  - Cover image (Pexels URL or fallback to category gradient if null/broken)
  - Category badge (top-left, colored by category)
  - Sentiment badge (top-right: BULLISH/BEARISH/NEUTRAL, colored)
  - Title: 2 lines max, truncated
  - Summary: 3 lines max, truncated
  - Meta row: source channel name | time ago | read time estimate
  - Hover: subtle gold border glow

PAGINATION:
- 24 cards per page
- Infinite scroll OR numbered pagination — CC decides based on article count
- "LOAD MORE INTELLIGENCE" button if infinite scroll

BROKEN IMAGE HANDLING:
- onerror on every img: replace with category-specific gradient + icon
- Never show broken image icons anywhere on the site

### INDIVIDUAL ARTICLE PAGE (/article/<slug>):
Full-width hero image (Pexels URL) — 400px tall, object-fit cover, with dark gradient overlay
Article meta: source | date | category | sentiment badge | read time
Title: large, gold, monospace
Body: clean readable prose — 18px, 1.7 line height, max-width 720px centered
In-article elements:
  - Pull quotes: gold left border, italic, slightly larger
  - Data callouts: dark card with key stat highlighted
  - Related articles: 3 cards at bottom "MORE INTELLIGENCE"

ARTICLE ENRICHMENT (if time):
  - "What you need to know" — 3 bullet TL;DR above article body (Claude-generated, stored in DB)
  - Sentiment reasoning: "Why BULLISH: [one sentence from scoring engine]"
  - Key entities: linked mentions of Bitcoin, companies, people

### BACKEND CONSOLIDATION (core/blueprints/articles.py):
SINGLE article creation endpoint — all 16 paths must funnel to one function: create_article()
Single article renderer — one template, zero conditional rendering paths
Image URL normalization: run migration to standardize all cover_image_url values
Broken URL detection: background job that pings image URLs, marks broken ones in DB

### PERMANENT LAWS (from ARTICLE_PAGE_LAWS.md — enforce in code):
1. Every article has a cover image or falls back gracefully — never broken
2. One template renders all articles — no conditional template paths
3. Sentiment badge on every article card and article page
4. Category filter always works — never 500s
5. Search is instant (client-side filter) — never a page reload
6. Mobile article reading: 16px min, readable line length, no horizontal scroll
7. Related articles always shows 3 real articles — never empty

---

# EXECUTION INSTRUCTIONS FOR ALL SESSIONS 3-10

Each session independently:
1. git checkout main && git pull
2. git checkout -b feature/session[N]-[name]
3. Read relevant existing code before touching anything
4. Build per spec above — blueprints file + template
5. Wire all API endpoints with REAL data (no mocks, no hardcoded values)
6. Test: relevant routes return 200 with real content
7. ./regression_test.sh → 0 FAILs
8. git add -A && git commit -m "feat: SESSION [N] — [name] world-class rebuild" && git push

No mocks. No placeholder data. No "TODO: wire real data."
If a data source API key is missing from .env: log a clear warning, show graceful empty state, do NOT crash.
World-class quality bar: Lighthouse mobile ≥ 85, FCP < 1.5s, zero broken images, zero raw tracebacks.
