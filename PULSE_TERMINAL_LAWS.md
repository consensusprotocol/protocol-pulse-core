# PROTOCOL PULSE — PULSE TERMINAL LAWS
# Premium Bitcoin Intelligence Terminal — Product Bible
# Bloomberg for Bitcoin at $49/month
# Status: GOSPEL. Dedicated buildout required.
# Created: 2026-03-05

---

## THE VISION

The Pulse Terminal is not an API bolted onto a content platform.
It IS the product. The video pipeline, articles, and social posts are
distribution channels for the intelligence. The Terminal is where
professionals access that intelligence directly.

Bloomberg Terminal charges $24,000/year for financial data.
Protocol Pulse charges $588/year ($49/month) for Bitcoin-specific
intelligence that Bloomberg doesn't have: real-time YouTube sentiment,
topic velocity across 18+ channels, narrative convergence detection,
and breaking signal alerts hours before any media outlet covers the story.

This is the revenue engine. Build it like a financial product, not a side feature.

---

## SECTION 1: PRODUCT TIERS

### Free Tier ($0/month)
- Top 3 trending topics (names only, no velocity scores)
- Overall sentiment label (bullish/bearish/neutral)
- 24-hour delay on all data
- No API access
- Access via: protocolpulse.io/terminal (read-only dashboard)

### Operator Tier ($19/month)
- Full topic velocity dashboard (all topics, scores, channel counts)
- Entity mention tracking (top 20 entities)
- Sentiment breakdown (overall, institutional, retail)
- Real-time data (no delay)
- API access: 100 requests/day
- Email alerts: daily digest
- Access via: dashboard + REST API

### Commander Tier ($49/month)
- Everything in Operator PLUS:
- Full API access: 1,000 requests/day
- WebSocket real-time stream
- Breaking news alerts (push notification, email, Telegram)
- Historical data (90 days rolling)
- Custom alert rules (e.g., "alert me when mining topic velocity > 70")
- Entity relationship graph
- Channel performance analytics
- Exportable data (CSV, JSON)
- Access via: dashboard + REST API + WebSocket + alerts

### Sovereign Tier ($99/month)
- Everything in Commander PLUS:
- Unlimited API requests
- Historical data (365 days rolling)
- Priority Discord channel with PBX
- Early access to new intelligence features
- Custom data queries (request specific analysis)
- White-label data licensing rights
- Monthly intelligence briefing call with PBX (30 min)

---

## SECTION 2: DATA ARCHITECTURE

### Data Sources (pipeline feeds Terminal):

```
Channel Intelligence Daemon (every 15 min)
  ├── data/channel_archive/known_videos.json (42+ videos, growing)
  ├── data/intelligence/daily_signals.json (topic velocity)
  ├── data/intelligence/entity_mentions.json (NER tracking)
  └── data/intelligence/sentiment.json (market sentiment)

Article Generation Pipeline (every 15 min)
  └── 1,479+ articles with topic classification

Tweet Study Data (quarterly refresh)
  └── data/tweet_study/raw_tweets.json (1,943 tweets, engagement data)

Node Monitor (every 15 min)
  └── data/node_snapshots/ (network health)

Performance Analytics (post-episode)
  └── data/performance/ (episode quality, channel scoring)
```

### Data Freshness Guarantees:
- Topic velocity: Updated every 15 minutes (daemon cycle)
- Entity mentions: Updated every 15 minutes
- Sentiment: Updated every 15 minutes
- Breaking alerts: Real-time (within 60 seconds of detection)
- Node count: Updated every 15 minutes
- Historical data: Retained for tier-specific duration

### Data Quality Rules:
- Every data point must have a timestamp and source attribution
- Sentiment scores use consistent 0-100 scale
- Topic velocity measures # of channels covering topic in rolling 24-hour window
- Entity mentions are deduplicated (same person mentioned 5 times in 1 video = 1 mention)
- Breaking threshold: 4+ channels covering same topic within 3 hours

---

## SECTION 3: API SPECIFICATION

### Authentication:
```
Header: X-API-Key: {api_key}
```
All endpoints require authentication. Invalid/missing key returns 401.
Rate limits enforced per tier. Exceeding limit returns 429 with Retry-After header.

### REST Endpoints:

#### GET /api/v2/terminal/topics
Topic velocity — what Bitcoin YouTube is talking about right now.
```json
{
  "data": {
    "topics": [
      {
        "topic": "mining difficulty",
        "velocity_score": 85,
        "channels_covering": 7,
        "channel_names": ["Simply Bitcoin", "TFTC", "The Bitcoin Layer", ...],
        "sentiment": "bearish",
        "sentiment_score": 38,
        "first_detected": "2026-03-05T06:15:00Z",
        "peak_velocity": "2026-03-05T10:30:00Z",
        "trend": "rising"
      }
    ],
    "scan_time": "2026-03-05T12:15:00Z",
    "next_scan": "2026-03-05T12:30:00Z",
    "total_channels_monitored": 18,
    "total_videos_analyzed_24h": 42
  },
  "meta": {
    "tier": "commander",
    "freshness": "2026-03-05T12:15:00Z",
    "rate_limit_remaining": 987
  }
}
```
Query params: ?period=24h|7d|30d, ?min_velocity=50, ?topic=mining

#### GET /api/v2/terminal/entities
Entity tracking — who's being talked about and how sentiment is shifting.
```json
{
  "data": {
    "entities": [
      {
        "name": "Michael Saylor",
        "type": "person",
        "mentions_24h": 14,
        "mentions_7d": 67,
        "sentiment_current": 78,
        "sentiment_7d_avg": 72,
        "sentiment_shift": "+8.3%",
        "top_channels": ["Simply Bitcoin", "The Bitcoin Layer"],
        "related_topics": ["ETF flows", "corporate treasury"],
        "first_mention_today": "2026-03-05T07:22:00Z"
      }
    ]
  }
}
```
Query params: ?type=person|company|protocol, ?min_mentions=5, ?sort=mentions|sentiment

#### GET /api/v2/terminal/sentiment
Market sentiment composite — the Protocol Pulse sentiment index.
```json
{
  "data": {
    "overall": {
      "score": 72,
      "label": "bullish",
      "change_24h": "+7",
      "change_7d": "+12",
      "components": {
        "youtube_sentiment": 75,
        "topic_velocity_bullish_pct": 68,
        "entity_sentiment_avg": 71,
        "social_engagement_trend": "rising"
      }
    },
    "breakdown": {
      "institutional": {"score": 85, "label": "very_bullish", "driver": "ETF inflows narrative"},
      "retail": {"score": 55, "label": "neutral", "driver": "price consolidation"},
      "mining": {"score": 42, "label": "bearish", "driver": "difficulty increase"}
    },
    "historical": [
      {"date": "2026-03-04", "score": 65},
      {"date": "2026-03-03", "score": 58},
      {"date": "2026-03-02", "score": 61}
    ]
  }
}
```

#### GET /api/v2/terminal/breaking
Breaking news detection — real-time alerts when narrative convergence detected.
```json
{
  "data": {
    "breaking": true,
    "alert": {
      "topic": "Strategic Bitcoin Reserve executive order",
      "velocity_score": 95,
      "channels": 8,
      "detected_at": "2026-03-05T11:47:00Z",
      "severity": "high",
      "summary": "8 channels covering strategic reserve EO within 2-hour window"
    },
    "recent_alerts": [],
    "monitoring": true,
    "threshold": {"channels": 4, "window_hours": 3}
  }
}
```

#### GET /api/v2/terminal/network
Bitcoin network health — node count, hashrate, difficulty.
```json
{
  "data": {
    "nodes": {
      "total_reachable": 102847,
      "net_change_24h": +127,
      "countries": 94,
      "top_countries": [{"country": "US", "nodes": 21847}, ...]
    },
    "hashrate": {
      "current_eh": 1056.2,
      "change_24h": "+2.3%"
    },
    "difficulty": {
      "current": 114171805838.02,
      "next_adjustment_blocks": 847,
      "estimated_change": "+3.2%"
    },
    "halving": {
      "blocks_remaining": 198420,
      "estimated_date": "2028-04-17"
    }
  }
}
```

#### WebSocket: wss://api.protocolpulse.io/v2/terminal/stream
Real-time event stream (Commander+ tier).
```json
{"event": "topic_velocity", "data": {"topic": "mining", "velocity": 72, "trend": "rising"}}
{"event": "breaking_alert", "data": {"topic": "...", "channels": 6}}
{"event": "entity_surge", "data": {"entity": "Saylor", "mentions": 14, "shift": "+23%"}}
{"event": "node_milestone", "data": {"total": 105000, "type": "round_number"}}
{"event": "sentiment_shift", "data": {"from": 65, "to": 72, "driver": "ETF flows"}}
```

---

## SECTION 4: DASHBOARD UI

### Design Standard:
The web dashboard at protocolpulse.io/terminal must look like a Bloomberg terminal
meets a cyberpunk command center. Dark mode only. Real-time updates. Dense but readable.

### Layout:
```
┌─────────────────────────────────────────────────────────┐
│  PULSE TERMINAL          BTC $87,245 ▲2.3%  │ LIVE ●   │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  SENTIMENT   │  TOPIC VELOCITY                         │
│  ████ 72     │  ┌─────────────────────────────────┐    │
│  Bullish     │  │ Mining Difficulty  ████████ 85   │    │
│  ▲+7 (24h)   │  │ ETF Flows         ██████   68   │    │
│              │  │ Self-Custody      █████    55   │    │
│  Inst: 85    │  │ Lightning         ████     42   │    │
│  Retail: 55  │  │ Regulation        ███      35   │    │
│  Mining: 42  │  └─────────────────────────────────┘    │
│              │                                          │
├──────────────┤  ENTITY TRACKER                         │
│              │  Saylor    14 mentions  ▲+23%            │
│  BREAKING    │  BlackRock  9 mentions  ▲+5%             │
│  ● LIVE      │  Bitwise    7 mentions  ▼-3%            │
│  8 channels  │                                          │
│  covering    ├──────────────────────────────────────────┤
│  Strategic   │  NETWORK HEALTH                         │
│  Reserve EO  │  Nodes: 102,847 (+127)                  │
│              │  Hashrate: 1,056.2 EH/s                 │
│              │  Next Difficulty: +3.2% in 847 blocks   │
│              │  Next Halving: 198,420 blocks            │
├──────────────┴──────────────────────────────────────────┤
│  HISTORICAL SENTIMENT  [7D] [30D] [90D]               │
│  ───────────────/\────────/\──────────────             │
│  ──────────────/  \──────/  \─────────────            │
│  ─────────────/    \────/    \────────────            │
└─────────────────────────────────────────────────────────┘
```

### Visual Standards:
- Background: #0A0A0A (consistent with PIPELINE_LAWS brand)
- Accent: #CC0000 (Protocol Pulse red)
- Data positive: #00CC66 (green)
- Data negative: #CC0000 (red — same as brand, dual purpose)
- Text primary: #EDEDED
- Text secondary: #888888
- Borders: #1F1F1F
- Font: JetBrains Mono for data, Inter for labels
- Animations: Real-time number counters, smooth chart updates
- Glassmorphism cards for each section (consistent with articles page)

### Tech Stack:
- Frontend: React (Next.js on Vercel, extend existing articles frontend)
- Real-time: WebSocket via Ultron relay or dedicated WS server
- Charts: Recharts or D3.js for historical data visualization
- State: React Query for API polling (30-second intervals for free, 5-second for paid)
- Auth: API key in header for programmatic access, session cookie for dashboard

---

## SECTION 5: BILLING AND SUBSCRIPTION

### Stripe Integration:
- Product: "Pulse Terminal"
- Prices: $19/mo (Operator), $49/mo (Commander), $99/mo (Sovereign)
- Free trial: 7 days of Commander tier
- Payment: Credit card, Bitcoin (via BTCPay Server or Lightning)
- Billing cycle: Monthly, annual discount (2 months free)

### API Key Management:
- Each subscriber gets a unique API key on signup
- Key displayed in dashboard settings
- Key can be regenerated (old key invalidated immediately)
- Usage tracked per key: requests/day, endpoints hit, data volume
- Overage: soft limit (warning at 80%), hard limit (429 at 100%)

### Bitcoin Payment Option:
- Lightning invoice generated per month
- On-chain for annual subscriptions
- BTCPay Server integration or manual Lightning invoice
- This aligns with the brand: a Bitcoin intelligence product that accepts Bitcoin

---

## SECTION 6: DATA PIPELINE INTEGRATION

### How data flows from pipeline to Terminal:

```
Channel Daemon (every 15 min on Ultron)
  └── Writes: data/intelligence/daily_signals.json
  └── Writes: data/intelligence/entity_mentions.json
  └── Writes: data/intelligence/sentiment.json
       │
       ▼
Sync to Replit (every 5 min)
  └── Ultron pushes JSON files to Replit via relay /push endpoint
  └── OR: Replit polls Ultron API for latest intelligence data
       │
       ▼
Terminal API (on Replit)
  └── Reads JSON files, serves via REST endpoints
  └── WebSocket pushes updates to connected subscribers
       │
       ▼
Terminal Dashboard (on Vercel)
  └── React frontend polls API / connects WebSocket
  └── Renders real-time dashboard
```

### Data Sync Rules:
- Ultron is the source of truth for intelligence data
- Replit serves the API (it's the public-facing server)
- Sync must happen every 5 minutes minimum
- If sync fails, API returns stale data with "stale_since" timestamp
- Dashboard shows a "Data stale" warning if data is >30 minutes old

---

## SECTION 7: BUILD PHASES

### Phase 1: API Foundation (Week 1)
- Replace mock data with real daily_signals.json reads
- Implement proper rate limiting per tier
- Add Stripe subscription management
- API key generation and management
- OpenAPI/Swagger documentation
- Basic usage tracking

### Phase 2: Dashboard MVP (Week 2)
- React dashboard at protocolpulse.io/terminal
- Topic velocity bar chart (real-time)
- Entity tracker table
- Sentiment gauge with historical sparkline
- Breaking news alert banner
- Login/signup flow with Stripe checkout

### Phase 3: Real-Time + Network (Week 3)
- WebSocket stream implementation
- Node Pulse integration (network health panel)
- Custom alert configuration UI
- Historical data charts (7d, 30d, 90d)
- CSV/JSON export for Commander+ tier

### Phase 4: Intelligence Graph (Week 4+)
- Entity relationship visualization
- Topic correlation mapping
- Predictive signals (based on historical patterns)
- Channel performance leaderboard
- The full Intelligence Graph from EXPANSION_SPEC V30

---

## SECTION 8: COMPETITIVE MOAT

### What nobody else has:
1. **Real-time YouTube intelligence** — no other product monitors 18+ Bitcoin
   channels every 15 minutes and classifies topics/sentiment
2. **Narrative convergence detection** — knowing when 4+ channels cover the
   same topic within hours is a leading indicator
3. **Entity sentiment tracking** — tracking how sentiment around Saylor,
   BlackRock, etc. shifts across the entire Bitcoin media ecosystem
4. **The archive** — 42+ videos (growing daily) of transcribed, classified,
   sentiment-scored content. This compounds. After 6 months: 5,000+ videos.
   After 1 year: 15,000+. That's an intelligence graph nobody can replicate
   without the same 15-minute daemon running for a year.

### Pricing justification:
- Bloomberg Terminal: $2,000/month — broad financial data
- Santiment: $49/month — on-chain data only
- Glassnode: $39/month — on-chain data only
- LunarCrush: $29/month — social media sentiment (broad crypto, not Bitcoin-specific)
- Protocol Pulse Terminal: $49/month — Bitcoin-specific YouTube/media intelligence
  that NONE of the above provide. Different data source, different insights,
  complementary product.

---

*This document defines the Pulse Terminal as a standalone premium product.
It must be built with the same rigor as a financial data platform.
Pair with: PIPELINE_LAWS.md, CONTENT_INTELLIGENCE_LAWS.md*
