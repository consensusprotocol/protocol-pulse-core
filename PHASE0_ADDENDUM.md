# PHASE 0 ADDENDUM — P3 CHARTS
# Generated: 2026-03-09
# Status: GOSPEL supplement — all items below are incorporated into build

---

## TOP PHASE 0 ADDITIONS TO IMPLEMENT

### 1. AI Chart Interpreter — "Explain This Chart" Button
**Priority: P0 (Category-Defining)**
- Every chart card gets an "INTERPRET" button
- Calls `/api/charts/ai-explain` with chart metadata + current data snapshot
- Uses Anthropic Claude API (ANTHROPIC_API_KEY from env)
- Returns 2-3 sentence interpretation in professional analyst voice
- Loading state: "Analyzing market structure..."
- Displayed in glassmorphism overlay beneath the chart
- **Implementation**: Backend streams chart context to Claude claude-haiku-4-5-20251001. Frontend shows typewriter reveal.

### 2. Advanced Bitcoin Valuation Metrics Panel
**Priority: P0 (Market Leadership)**
- Mayer Multiple: real-time calculation (price / 200d MA). Display with zones: < 1.0 (undervalued), 1.0–2.4 (fair), > 2.4 (overbought)
- Stock-to-Flow model price: calculate from current supply + block schedule. Display as overlay on price chart.
- Puell Multiple: approximated from daily issuance value vs 365d MA (proxy from hashrate data)
- NUPL approximation: Market Cap - Realized Cap estimate / Market Cap. Display as colored sentiment gauge.
- **Implementation**: Pure JS math on price history data. No external API needed for Mayer/S2F/NUPL estimates.

### 3. Real-Time Architecture Improvements
**Priority: P0 (Foundation)**
- mempool.space WebSocket with exponential backoff reconnect (as per GOSPEL)
- Heartbeat ping every 30s to keep connection alive
- Connection status indicator in stat bar (green dot = live, red = polling fallback)
- **Implementation**: Single WebSocket manager class, wraps all WS subscriptions.

### 4. Lightning Network Metrics Section
**Priority: P1**
- Total capacity (BTC + USD), node count, channel count from mempool.space API
- 30-day capacity trend mini-chart (Canvas bar chart)
- Source: `/api/charts/lightning` proxy → `https://mempool.space/api/v1/lightning/statistics/latest`
- **Implementation**: New section after Supply Analysis

### 5. Difficulty Adjustment Prediction
**Priority: P1**
- Calculate next difficulty adjustment from current block height + epoch progress
- Show: blocks remaining, estimated date, expected % change (from current hashrate trend)
- Visual: progress ring (Canvas arc) + prediction badge
- **Implementation**: Pure math from block height + mempool data (no external API)

### 6. Fear & Greed Index Display
**Priority: P1**
- Fetch from `https://api.alternative.me/fng/?limit=7` (free, no key)
- 7-day trend sparkline + current value gauge
- Proxy via `/api/charts/fear-greed`, cache 1hr
- **Implementation**: Semicircle gauge Canvas component

### 7. Export/Sharing with Protocol Pulse Branding
**Priority: P1 (from GOSPEL LAW 3)**
- canvas.toDataURL("image/png") download per chart
- Watermark "PROTOCOLPULSE.IO" in corner before download
- Web Share API with fallback to clipboard copy
- **Implementation**: ChartEngine.exportPNG(chartId, title) method

### 8. Rate Limiting on Price Alert Endpoint
**Priority: P1 (Security)**
- Max 3 alerts per email address per day
- Max 10 active alerts per email total
- Input validation: valid email format, price must be numeric 1000–10,000,000
- **Implementation**: DB query count before insert

### 9. Keyboard Accessibility + Command Bar
**Priority: P2**
- Cmd+K opens quick-jump to any chart section
- Tab navigation through all interactive elements
- ARIA labels on all charts (role="img", aria-label describing the chart)
- **Implementation**: Global keydown handler, smooth scrollTo sections

### 10. Hashrate Ribbon Indicator
**Priority: P2**
- Show 30d vs 60d SMA of hashrate — ribbon color flips bullish/bearish
- Overlaid on hashrate chart as shaded band
- **Implementation**: Calculate from hashrate history array in JS

---

## DESIGN DECISIONS (Best Calls)

- **No Glassnode/CoinMetrics API**: Free tiers too limited and require keys. Use pure-JS calculations from price/hashrate history instead for MVRV/NUPL approximations. Label as "estimated" where not exact.
- **No Redis/Node.js**: Keep single-process Flask. Cache with functools.lru_cache + TTL wrapper.
- **No TensorFlow.js**: Predictive analytics kept to simple trend extrapolation (linear regression in pure JS) — no ML frameworks.
- **Fear & Greed**: alternative.me API is genuinely free, no auth, perfect fit.
- **Lightning metrics**: mempool.space `/lightning/statistics/latest` is free and comprehensive.

---
*End PHASE0_ADDENDUM.md — All items above incorporated into the build.*
