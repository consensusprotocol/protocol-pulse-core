# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.

# PROTOCOL PULSE — GOSPEL: P3 BITCOIN CHARTS
# Branch: feature/p3-charts | Created: 2026-03-09

---

## WHAT THIS IS
The Bitcoin data intelligence hub at /charts. Price charts, technical indicators,
on-chain metrics, mining stats, supply analysis, Lightning stats. Bloomberg Terminal
meets cypherpunk. All free APIs — no keys needed. The go-to bookmark for data-driven
Bitcoiners. SEO goldmine. Zero stock imagery. Zero fluff.

## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY)
Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-charts --phase0
Ask all 3 LLMs: "What are the most advanced Bitcoin on-chain metrics and chart
visualizations that a sophisticated Bitcoiner would want in 2026? Think beyond basic
price — what do serious analysts look at? What technical indicators are most valuable?
What free APIs exist for on-chain data?"
Incorporate top P0 ideas before building.

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

## ARCHITECTURE

### /charts Route
```python
@app.route("/charts")
def charts():
    # Pass: current btc_price, block_height, mempool_size
    # All charts load data client-side via JS fetch to proxy endpoints
    ...
```

### Template: charts.html
LAYOUT: Dark dashboard, 2-column grid on desktop, 1-col mobile.

HEADER STAT BAR (6 cards, live via WebSocket/SSE):
[BTC PRICE] [24H %] [MARKET CAP] [BLOCK HEIGHT] [MEMPOOL MB] [NEXT BLOCK FEE]

SECTION 1 — PRICE CHART (full width):
7-day BTC/USD line chart (Canvas). Controls: 1D / 7D / 30D / 90D / 1Y
Overlays (toggleable checkboxes):
  ☑ 200-day MA (gold dashed line)
  ☐ Bollinger Bands (upper/lower, red/green shaded area)
  ☐ RSI (14-period) — plotted in separate mini-chart below main
  ☐ MACD — plotted in separate mini-chart below RSI
  ☐ Mayer Multiple — current price / 200-day MA ratio (> 2.4 = historically overbought)
  ☐ Stock-to-Flow — model price overlay (gold line)
All indicator math in pure JS. RSI = 14-period relative strength. MACD = 12/26/9 EMA.

SECTION 2 — MINING METRICS (2-column):
Left: Hashrate chart (30-day, cyan, EH/s)
Right: Difficulty epoch (current progress bar + next adjustment prediction)
Under: Hash Price trend (USD per PH/day — proxy from /api/charts/hashrate-history)

SECTION 3 — MINING POOL DISTRIBUTION (2-column):
Left: Pie chart — top pools last 7 days (Canvas donut)
Right: Pool table with HHI concentration score
Red warning if top 3 pools control > 50% of hashrate

SECTION 4 — MEMPOOL & FEES (full width):
Stacked area chart: mempool size over last 7 days (MB)
Fee rates: Low/Mid/High/Urgent sat/vB colored pills (live WebSocket)
Recommended fee for 1h confirmation target — big display

SECTION 5 — SUPPLY ANALYSIS:
Progress bar: X of 21,000,000 BTC mined (calculate from block height × schedule)
% mined → animated fill bar (gold)
Next halving: block countdown + date estimate (big display, red accent)
Current subsidy: 3.125 BTC/block
Sats per dollar: 100,000,000 / btc_price (live, gold number)
Lost coins estimate: ~4M BTC (Chainalysis estimate — static, cited)
Circulating supply: total - estimated lost

SECTION 6 — UTXO AGE DISTRIBUTION (HODL Waves concept):
Stacked bar chart showing approximate % of supply by last-moved age:
<1 day | 1d-1w | 1w-1m | 1m-3m | 3m-6m | 6m-1y | 1y-2y | 2y-3y | 3y-5y | 5y+
(Use static/approximated data updated monthly — no free API for this exact metric)
Note: "Estimated from on-chain analysis. Updated monthly."

SECTION 7 — CUSTOM PRICE ALERT
Email alert form: "Alert me when BTC reaches $____"
POST /api/charts/price-alert → saves to price_alerts table
Check alerts every 5min via cron → send email via Resend when triggered
CREATE TABLE price_alerts (email, target_price, direction, triggered, created_at)

SECTION 8 — CHART EMBED WIDGET
Every chart has "Embed" button → shows iframe code:
<iframe src="https://protocolpulse.io/charts/embed/price?days=7" .../>
/charts/embed/price → stripped-down chart page (no nav, dark bg, just chart)
Attribution: "Powered by Protocol Pulse" link in corner

## VERIFICATION
- [ ] GET /charts → HTTP 200 with all sections
- [ ] Price chart loads CoinGecko data via proxy
- [ ] RSI and MACD overlays calculate correctly (manual test)
- [ ] Mempool fee pills show live data from mempool.space
- [ ] Mining pool distribution pie renders real pool data
- [ ] Halving countdown shows correct block count
- [ ] Sats per dollar updates when BTC price changes
- [ ] Price alert saves to DB, cron checks alerts
- [ ] "Download PNG" works on at least price chart
- [ ] Embed route returns minimal chart page
- [ ] regression_test.sh: zero FAILs
- [ ] git commit + push to origin feature/p3-charts
