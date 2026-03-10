# PROTOCOL PULSE — MASTER AUDIT + NEXT SESSION PLAN
## Generated: March 9, 2026 | Verified against live server

---

## THE HONEST TRUTH FIRST

**CRITICAL FINDING: Zero feature branches have been merged to main.**

Every single build session from Phase 3, Phase 4, F-series, B-series, V-series — 17+ branches — exists as unmerged code. The production site (protocolpulse.io) is running off a main branch that predates all of this work. The features were written. The code exists. Nothing has shipped.

This is actually a clean, recoverable situation — no broken production, no half-deployed features. But the path forward requires a deliberate merge + QA session before we build anything new. Otherwise we're stacking new work on top of unvalidated foundation.

---

## LIVE SITE STATUS (verified by actual HTTP calls)

| Route | HTTP | Status |
|-------|------|--------|
| / (homepage) | 200 | ✅ Live |
| /articles | 200 | ✅ Live |
| /oracle | 200 | ✅ Live |
| /charts | 200 | ✅ Live (old version, pre-P3) |
| /premium | 200 | ✅ Live (old version, pre-P3) |
| /media | 200 | ✅ Live (Media Hub, pre-UNIFIED) |
| /signal-terminal | 200 | ✅ Live |
| /api/btc-price | 200 | ✅ Live |
| /api/v2/terminal/topics | 401 | ⚠️ Route exists, auth required (V30 partially live?) |
| /terminal | 404 | ❌ NOT LIVE |
| /mining-risk | 404 | ❌ NOT LIVE |
| /newsletter | 404 | ❌ NOT LIVE |
| /oracle-live | 404 | ❌ NOT LIVE |
| /articles/latest | 404 | ❌ NOT LIVE |

---

## BRANCH AUDIT — WHAT EXISTS BUT ISN'T ON PRODUCTION

| Branch | Commits ahead of main | Last commit message | Verdict |
|--------|----------------------|--------------------|---------| 
| feature/b1-newsletter | +2 | "add missing NewsletterSubscriber/Send models" | Incomplete — missing models suggests it's not fully wired |
| feature/f1-avatar-oracle | +5 | "BUILD_COMPLETE for f1-avatar-oracle" | Code complete, never merged |
| feature/f2-briefing-room | +3 | "BUILD_COMPLETE for f2-briefing-room" | Code complete, never merged |
| feature/f3-schiff-bot | +3 | "BUILD_COMPLETE for f3-schiff-bot" | Code complete, never merged |
| feature/f4-nostr | +3 | "BUILD_COMPLETE for f4-nostr" | Code complete, never merged |
| feature/f5-node-watch | +3 | "BUILD_COMPLETE for f5-node-watch" | Code complete, never merged |
| feature/f6-marketing-os | +3 | "BUILD_COMPLETE for f6-marketing-os" | Code complete, never merged |
| feature/p3-affiliates | +5 | "add BUILD_COMPLETE.md" | Code complete, never merged |
| feature/p3-charts | +5 | "add BUILD_COMPLETE.md" | Code complete, never merged |
| feature/p3-media-unified | +3 | "build unified /media command center" | Code complete, never merged |
| feature/p3-mining-intel | +4 | "add BUILD_COMPLETE.md" | Code complete, never merged |
| feature/p3-premium-stripe | +6 | "third-pass — N1 key-in-URL, M6 rate_limit" | Most commits = most complex/problematic |
| feature/p3-sentiment-intel | +3 | "Phase0+Build+Audit complete" | Code complete, never merged |
| feature/p3-sponsor-agent | +4 | "BUILD_COMPLETE.md — verification checklist" | Code complete, never merged |
| feature/v22-multi-format | +3 | "BUILD_COMPLETE for v22-multi-format" | Code complete, never merged |
| feature/v30-terminal-api | +3 | "BUILD_COMPLETE for v30-terminal-api" | Partially live? /api/v2/terminal/* returns 401 not 404 |
| feature/video-audio-fix | ACTIVE | Narration gospel + bug fixes | Active dev, nearly ready to merge |

---

## ASSESSMENT: WHAT ACTUALLY WORKS VS CLAIMED

### ✅ GENUINELY WORKING (confirmed live):
- Homepage with BTC price, articles, hero section
- Article generation pipeline (active, 1,300+ articles)
- Oracle page
- Charts page (old design, not P3-enhanced)
- Signal Terminal
- Video pipeline infrastructure (4090 + Whisper + ElevenLabs)
- Cloudflare tunnel routing
- Cron jobs (channel_daemon, live_monitor, spaces_monitor, daily_producer all running)

### ⚠️ PARTIALLY WORKING (wired but degraded):
- /api/v2/terminal/* — returns 401 (auth exists, may be live from an older merge)
- /media → serves Media Hub but it's the old version, not MEDIA_UNIFIED
- /premium → serves old upgrade page, not new Stripe-integrated version
- Video pipeline narration — Bugs 1+2+3 fixed in branch but not yet verified A-grade

### ❌ NOT WORKING / NOT LIVE (hard 404):
- /terminal (Pulse Terminal)
- /mining-risk
- /newsletter (subscribe endpoint)
- /oracle-live
- Mining Intel feature
- Sponsor Agent feature
- Full Stripe/Premium flow

---

## THE 17-BRANCH MERGE QUESTION

These branches need to be merged in the right order to avoid conflicts given routes.py is 8,048 lines:

**Safest merge order (least conflicts first):**
1. v30-terminal-api (V30 — Pulse Terminal API — already partially live, cleanest to merge first)
2. p3-charts (standalone route, minimal overlap)
3. p3-sentiment-intel (new route + data service, minimal overlap)
4. p3-mining-intel (new route, depends on mining data service)
5. p3-media-unified (replaces /media, needs careful template swap)
6. p3-premium-stripe (touches auth flows — most dangerous, test last in this group)
7. p3-affiliates (RNS.ID integration, mostly additive)
8. p3-sponsor-agent (DO NOT MERGE — per spec, not until video pipeline producing clean daily renders)
9. b1-newsletter (subscription + email flows)
10. f1-avatar-oracle through f6-marketing-os (F-series, each isolated)
11. v22-multi-format (video format variants)
12. video-audio-fix (LAST — after gauntlet A-grade confirmed)

**HOLD on p3-sponsor-agent** — spec says explicitly: do not build/merge until pipeline producing clean daily renders. That gate isn't cleared yet.

---

## NEXT SESSIONS NEEDED — PRIORITIZED BUILD QUEUE

Below is the full plan, ordered by value + urgency + dependencies. Each session is scoped for one CC session.

---

### SESSION 0 — EMERGENCY FIRST (before anything else)
**MERGE SPRINT + SITE QA**
- Merge all 16 ready branches into main in the order above
- Full route audit post-merge (every route 200/functional)
- Mobile 375px QA pass on every new page
- Database migrations (any ALTER TABLE / new tables from feature branches)
- Regression test suite passes 0 FAILs
- git tag v2.0.0-merge
- Estimated time: 1 CC session, ~45 min

---

### SESSION 1 — PULSE TERMINAL (V30) [HIGHEST REVENUE]
**Goal:** Pulse Terminal API Commander tier ($49/mo) fully live, payment working

The /api/v2 endpoints appear partially wired but untested at UI layer. The full terminal needs:
- `/terminal` route → world-class React-in-Jinja dark terminal UI
- Live data feeds: BTC price, mempool, hashrate, fear/greed, trending topics
- Commander tier paywall: Stripe checkout → API key generation → dashboard
- Rate limiting by tier (free: 10 req/hr, commander: unlimited)
- API key management page
- Docs page at `/terminal/docs`

**World-class UI spec for this session:**
Deep black background (#050507). Gold top information ribbon (price, block, hashrate). Red/cyan terminal grid lines. Split stat cards with animated SVG sparklines. Radial glow effect behind key metrics. Monospace font throughout. Typewriter-effect data updates. "LIVE" pulse indicator on streaming endpoints. Commander tier badge glows gold.

---

### SESSION 2 — NEWSLETTER (B1) [HIGHEST ENGAGEMENT]
**Goal:** Subscriber capture + automated daily email fully live

Currently: /newsletter 404, subscribe endpoint returns 302 (redirect, not processing)

Needs:
- `/newsletter` → beautiful opt-in landing page
- POST /newsletter/subscribe → Resend API → welcome email → DB record
- Daily automated briefing email (pulls top 3 articles + BTC price + one-liner market take)
- Unsubscribe flow
- Admin panel at /admin/newsletter (subscriber count, open rates, send history)
- Existing subscriber import if legacy list exists

**World-class UI spec:**
Full-bleed dark hero, gold headline "Intel. Delivered." Floating email input with glow on focus. Social proof line ("Join X subscribers tracking the signal"). Preview of last issue. Clean typographic hierarchy. Mobile-first. Confirmation page that feels like an exclusive membership.

---

### SESSION 3 — MEDIA UNIFIED (P3) [BIGGEST SURFACE AREA]
**Goal:** Kill media_hub.html + media_terminal.html → single /media command center

26 features, 3 phases. The branch has the code — needs merge validation + live data wiring:
- Kill fake X feed (replace with real Nostr relay data)
- Kill hardcoded quotes (pull from real article sentiment)
- Wire Signal Strength composite indicator (live)
- Telemetry + sentiment cards (live data)
- Nostr relay manager panel
- Health strip at bottom (system status)
- Virtual feeds (curated topic streams)

**World-class UI spec:**
ChatGPT finance-terminal aesthetic per VISUAL_DESIGN_SYSTEM.md. Gold info bar at top. Dual-column layout: left = live feeds/signals, right = intelligence panels. Animated SVG chart for signal strength. Red/cyan/gold color language. Glassmorphism panels. Real-time data pulsing. Zero static content — everything either live data or clearly timestamped.

---

### SESSION 4 — CHARTS (P3) [SEO + ENGAGEMENT]
**Goal:** /charts fully live with real data, world-class Bitcoin data visualization

Current /charts returns old HTML. The P3 branch has the enhanced version. Needs:
- TradingView widget integration OR custom D3.js charts
- Bitcoin price (all timeframes: 1D, 1W, 1M, 1Y, ALL)
- Hashrate chart
- Difficulty adjustment chart + countdown to next
- Fee market chart (mempool backlog)
- Fear & Greed index chart
- 200-week moving average
- MVRV Z-Score
- Stock-to-Flow overlay

**World-class UI spec:**
Bloomberg Terminal meets cyber aesthetic. Dark charcoal base. Each chart in its own glassmorphism panel. Timeframe selector buttons (pill style, active = gold glow). Hover tooltips with exact values + date. Chart grid lines in deep cyan at 10% opacity. All charts load in 0-200ms (cached). Share button on each chart generates clean OG image.

---

### SESSION 5 — PREMIUM + STRIPE (P3) [DIRECT REVENUE]
**Goal:** Full subscription flow live — free / premium / commander tiers

Currently /premium serves old page. Needs:
- Clean pricing page (3 tiers: Free, Premium $19/mo, Commander $49/mo)
- Stripe Checkout Session creation
- Stripe webhook handler (subscription activated → user upgrade)
- Premium content gates on articles (teaser + paywall CTA)
- Account dashboard (/account) — subscription status, API keys, billing
- Cancel/downgrade flow

**World-class UI spec:**
3 pricing cards. Free = muted/dark. Premium = silver glow. Commander = GOLD with "MOST POPULAR" badge and subtle pulse animation. Feature comparison table below cards. FAQ accordion. Live testimonial strip. Trust badges (Stripe secure, Bitcoin accepted). Mobile-optimized checkout flow. Post-payment onboarding sequence.

---

### SESSION 6 — SENTIMENT INTEL (P3)
**Goal:** Live Bitcoin sentiment intelligence dashboard at /sentiment (or integrated into terminal)

The branch has Phase0+Build. Needs validation and:
- Sentiment score (0-100 Fear/Greed derived from multiple sources)
- Article sentiment trending (positive/neutral/negative ratio over time)
- Social signal sentiment (X posts, Nostr, Reddit)
- Whale alert integration
- Sentiment-driven article tagging

---

### SESSION 7 — MINING INTEL (P3)
**Goal:** /mining → live Bitcoin mining intelligence

- Hashrate trends (realtime + historical)
- Miner revenue analysis  
- Block difficulty projections
- Mining pool market share
- Blockware Intelligence content integration
- Curated Mining CTA (cross-sell to john@curatedmining.com)

---

### SESSION 8 — F-SERIES (AVATAR, BRIEFING, SCHIFF-BOT, NOSTR, NODE-WATCH)
**Goal:** Merge and validate all 5 F-series features

F1 — Oracle Avatar: HeyGen Sarah (3x/day briefings), PBX Digital Twin (2x/week)
F2 — Briefing Room: /briefing-room → live daily briefing page
F3 — Schiff Bot: Counter-narrative AI that argues against Bitcoin (engagement driver)  
F4 — Nostr: Native Nostr relay integration, publish articles to Nostr
F5 — Node Watch: Real-time node count, geographic distribution, /node-watch

---

### SESSION 9 — SPONSOR AGENT (P3) [HOLD UNTIL PIPELINE CLEAN]
**Goal:** Autonomous sponsor outreach and deal management

Per spec: DO NOT LAUNCH until video pipeline is producing clean daily A-grade renders. Once video is clean:
- Prospect identification (brand + Bitcoin alignment scoring)
- Outreach email generation
- Deal tracking dashboard
- Rate card generator
- Contract templates

---

## WHAT "WORLD-CLASS" ACTUALLY MEANS FOR THIS PLATFORM

Every page must pass this bar before it ships:

**Technical:**
- Lighthouse score ≥ 90 mobile, ≥ 95 desktop
- First Contentful Paint < 1.2s
- Time to Interactive < 2.5s
- Zero layout shift on load
- All data either live (cached <30s) or clearly timestamped

**Visual:**
- Consistent with VISUAL_DESIGN_SYSTEM.md (gold/red/cyan/black)
- Glassmorphism panels on data cards
- Animated transitions (not janky — 60fps CSS transforms only)
- Radial glow on hero elements
- Monospace for data, sans-serif for editorial content
- Every number formatted: commas, 2 decimal places, correct units
- Mobile 375px looks as intentional as desktop 1440px

**Content:**
- Zero placeholder text or lorem ipsum anywhere in production
- Zero hardcoded "mock" data
- Every live data field shows last-updated timestamp
- Error states are designed, not raw Python tracebacks
- 404 page is branded and helpful

**UX:**
- Single click to any feature from homepage
- Back navigation never breaks
- All modals/overlays have ESC to close
- Loading states on every async operation
- Success/error toast notifications (not alert())

---

## IMMEDIATE NEXT STEP

Gauntlet QC loop is running in `video_fix_sprint` → that's autonomous.

Next: Launch SESSION 0 (merge sprint) in a new CC session while video_fix_sprint runs.
Then sessions 1-4 sequentially in dedicated CC sessions.
Sponsor Agent held until after video pipeline A-grade.

Route: `ssh ultron` → start new CC session → SESSION 0 merge sprint.
