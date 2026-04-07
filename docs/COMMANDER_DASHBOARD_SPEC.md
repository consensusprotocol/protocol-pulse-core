# COMMANDER DASHBOARD — Design Specification

**Version:** 3.0 (Post-Audit Rebuild)
**Date:** 2026-04-07
**Audit Provenance:** 3-model cross-LLM audit (Gemini 2.5 Pro, Grok-3 x2)
**Route:** `/commander/dashboard` → `templates/commander_dashboard.html`

---

## Product Vision

Commander is not a developer portal. It is a **sovereign Bitcoin intelligence command center** — the first thing a serious Bitcoin holder opens every morning. Bloomberg Terminal energy for Bitcoin.

**One-line pitch:** "Your pre-defined conditions have been met. The regime has shifted. Here's what happened overnight and what it means for your stack."

---

## Layout Architecture

### Desktop (≥992px): 2-Column Grid
```
┌─────────────────────────────────────────────────────────┐
│  STATUS BAR: BTC $68,601 ▼0.54% │ Block 944,004 │ LIVE │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─ CONVERGENCE REGIME ──────────────────────────────┐  │
│  │  ACCUMULATION          Score: 67.4                │  │
│  │  "Miners holding, exchange outflows accelerating.  │  │
│  │   Last 5 times this pattern: +18% avg in 30d."    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─ SIGNAL MATRIX ─────┐  ┌─ MORNING BRIEF ─────────┐  │
│  │  [Interactive Radar] │  │  THE VERDICT:            │  │
│  │  MCX: 72  EPX: 45   │  │  "Overnight derivatives   │  │
│  │  IHX: 68  OPX: 55   │  │   pressure absorbed by    │  │
│  │  FDX: 41  OCX: 63   │  │   spot demand..."         │  │
│  │  + 24h ghost overlay │  │                           │  │
│  │  + sparklines        │  │  KEY DRIVERS: 4 bullets   │  │
│  └──────────────────────┘  │  WATCH LIST: 3 items      │  │
│                            └───────────────────────────┘  │
│  ┌─ MARKET DATA ────────┐  ┌─ KOL SENTIMENT ─────────┐  │
│  │  Price │ Fees │ Hash  │  │  Overall: BULLISH        │  │
│  │  F&G │ Mempool │ LN   │  │  Voices: @nvk, @booth   │  │
│  │  DXY │ Gold │ S&P    │  │  "Fiat is a scam..." —   │  │
│  └──────────────────────┘  │  Gladstein               │  │
│                            └───────────────────────────┘  │
│  ┌─ SIGNAL ACCURACY ────┐  ┌─ ACTIVE THESIS ─────────┐  │
│  │  Last 10 signals:    │  │  "Miner-Speculator       │  │
│  │  ████████░░ 80%      │  │   Divergence"            │  │
│  │  30d avg: +12.4%     │  │  Confidence: 78%         │  │
│  └──────────────────────┘  │  Invalidated if MCX < 50 │  │
│                            └───────────────────────────┘  │
│  ┌─ WHALE WATCH ────────┐  ┌─ HALVING CYCLE ─────────┐  │
│  │  3 recent movements  │  │  Day 713 of 1,460        │  │
│  │  Exchange flow: OUT  │  │  ████████████░░░░ 49%    │  │
│  └──────────────────────┘  │  Phase: Mid-Cycle        │  │
│                            └───────────────────────────┘  │
│  ┌─ INTEL FEED ──────────────────────────────────────┐  │
│  │  [8/10] ON-CHAIN: 3,200 BTC moved off Coinbase    │  │
│  │  [7/10] MACRO: DXY correlation weakened overnight  │  │
│  │  [9/10] REGIME: Accumulation pattern confirmed     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Mobile (<992px): Single Column Stack
Same sections, stacked vertically. Convergence Regime hero stays full-width. Radar chart scales to viewport width.

---

## Section Specifications

### 1. STATUS BAR (persistent top)
- **Data:** BTC price, 24h change, block height, data freshness indicator
- **Source:** `/api/btc-price` (real-time) + `data/sovereign_context/latest.json`
- **Refresh:** Every 30 seconds
- **Design:** Fixed top bar, `#030408` bg, JetBrains Mono, subtle glow on price change

### 2. CONVERGENCE REGIME (hero section)
- **Data:** Composite convergence score, regime label, one-line AI thesis, historical context
- **Source:** `/api/v1/orb` → `composite.score`, `composite.pattern`
- **Logic:** Score 0-100 maps to regime:
  - 0-25: WATCH (red pulse)
  - 26-45: MONITORING (amber)
  - 46-65: CONSTRUCTIVE (blue)
  - 66-100: ACCUMULATION (gold pulse)
- **Historical:** "Last N times score was at this level: [dates + 30d performance]"
- **Refresh:** Every 5 minutes
- **Design:** Full-width card, large score number, regime label in Commander gold (#B8860B), glass-morphism panel with subtle pulse animation matching regime color

### 3. SOVEREIGN SIGNAL MATRIX (interactive radar)
- **Data:** 6 index scores (MCX, EPX, IHX, OPX, FDX, OCX) + descriptions
- **Source:** `/api/v1/orb` → `nodes.*`
- **Visualization:** Canvas-rendered radar chart with:
  - Current values (solid fill, red border)
  - 24h previous values (ghost overlay, dashed line, 30% opacity)
  - Per-axis sparkline on hover
  - Click-to-expand per index with description + trend
- **Refresh:** Every 5 minutes
- **Design:** Dark glass panel, red (#dc2626) fill, axis labels in JetBrains Mono

### 4. MORNING BRIEF
- **Data:** AI-generated verdict, key drivers (3-5 bullets), watch list (3 items)
- **Source:** `data/intelligence/morning_intelligence_brief.json`
- **Fields used:** `sentiment`, `sentiment_reasoning`, `dominant_narratives`, `recommended_tweet_angles` (reframed as watch items), `btc_price`, `btc_change_24h`, `fng`
- **Refresh:** Daily (file-based, loaded on page load)
- **Design:** Crimson Pro serif for narrative text, JetBrains Mono for data. Left red border accent on each driver bullet.

### 5. KOL SENTIMENT
- **Data:** Sentiment direction, dominant narrative, top signal, contrarian view, voices sampled
- **Source:** `data/intelligence/kol_sentiment_brief.json`
- **Fields used:** `sentiment`, `dominant_narrative`, `top_signal`, `contrarian_view`, `kol_handles_seen`, `tts_script`
- **Refresh:** Daily (file-based)
- **Design:** Glass panel with sentiment badge (BULLISH=green, BEARISH=red, NEUTRAL=amber)

### 6. MARKET SNAPSHOT
- **Data:** BTC price, 24h/7d change, mempool fees, hashrate, F&G, LN stats, DXY/Gold/S&P
- **Source:** `data/sovereign_context/latest.json` + `data/signals.json`
- **Fields:** `btc.*`, `fear_greed.*`, `mempool.*`, `network.*`, `lightning.*`, macro from `/api/v1/orb` streams
- **Refresh:** Every 60 seconds for price, 5 min for network
- **Design:** Compact grid of stat cards, color-coded by direction

### 7. SIGNAL ACCURACY
- **Data:** Historical convergence scores + subsequent price performance
- **Source:** `data/sovereign_context/daily_snapshots/*.json` (historical data)
- **Logic:** Compare convergence score on date X with BTC price 7/30 days later
- **Design:** Progress bar showing accuracy %, last 10 signals with outcomes

### 8. ACTIVE THESIS
- **Data:** AI-generated thesis based on current regime
- **Source:** Generated client-side from morning brief + convergence data
- **Design:** Glass panel with thesis title, confidence percentage, historical precedent, invalidation criteria

### 9. WHALE WATCH
- **Data:** Recent large BTC movements, exchange flow direction
- **Source:** `/api/v1/orb` → `raw.whale_alerts_list`, `exchange_flow`
- **Refresh:** Every 5 minutes
- **Design:** List of whale movements with amount, direction, timestamp

### 10. HALVING CYCLE
- **Data:** Current block height, blocks since last halving, days to next, phase
- **Source:** `data/sovereign_context/latest.json` → `block_height`
- **Logic:** Halving at block 840,000 (April 2024), next at 1,050,000
- **Design:** Progress bar, day count, phase label

### 11. INTEL FEED
- **Data:** High-signal events scored 7+/10
- **Source:** `data/intelligence/morning_intelligence_brief.json` → narratives + signals.json
- **Design:** Scrollable feed with signal strength badge, category tag, timestamp

---

## Color System

| Element | Color | Usage |
|---|---|---|
| Background | `#030408` | Page background (deeper than free site) |
| Surface | `rgba(10,10,10,0.6)` | Glass panels |
| Primary accent | `#dc2626` | Borders, icons, radar fill |
| Commander gold | `#B8860B` | Premium elements, regime label, convergence score |
| Positive | `#22c55e` | Bullish, up, inflows |
| Negative | `#dc2626` | Bearish, down, outflows |
| Warning | `#eab308` | Neutral, monitoring |
| Text primary | `#ffffff` | Headlines, values |
| Text secondary | `rgba(255,255,255,0.6)` | Labels, descriptions |
| Text muted | `rgba(255,255,255,0.4)` | Timestamps, metadata |
| Border | `rgba(255,255,255,0.06)` | Panel borders |

## Typography

| Use | Font | Size | Weight |
|---|---|---|---|
| Data values | JetBrains Mono | 1.4-2.0rem | 700 |
| Section headers | JetBrains Mono | 0.7-0.75rem | 600, uppercase, 2px tracking |
| Narrative text | Crimson Pro, Georgia, serif | 1.05rem | 400, 1.7 line-height |
| Labels | System sans-serif | 0.6-0.7rem | 400, uppercase |
| Score numbers | JetBrains Mono | 3.0rem | 800 |

## Interaction Patterns

- **Progressive loading:** Skeleton loaders for each panel, data fills progressively
- **Hover:** Dim siblings to 40% opacity on panel hover (from live_terminal.html pattern)
- **Expand/collapse:** Click panel header to expand details
- **Auto-refresh:** Price every 30s, convergence every 5m, brief on page load
- **Pulse animation:** Convergence regime card pulses gently in regime color
- **Ghost overlay:** Radar chart shows 24h previous values as dashed ghost shape

## Data Refresh Strategy

| Data | Frequency | Method |
|---|---|---|
| BTC price | 30s | fetch `/api/btc-price` |
| Convergence/Signal Matrix | 5m | fetch `/api/v1/orb` |
| Morning brief | Page load | read from server-rendered JSON |
| KOL sentiment | Page load | read from server-rendered JSON |
| Sovereign context | 60s | fetch from server |
| Whale alerts | 5m | from `/api/v1/orb` response |
| Signal accuracy | Page load | computed from historical snapshots |

## Route Changes

**`core/routes_auth.py:706-726`** — Update `commander_dashboard()` to pass rich data:
- `morning_brief` — contents of morning_intelligence_brief.json
- `kol_brief` — contents of kol_sentiment_brief.json
- `sovereign` — contents of sovereign_context/latest.json
- `user` — current user object (name, tier, join date)
- Remove: `masked_key`, `calls_today`, `daily_limit`, `calls_month`
