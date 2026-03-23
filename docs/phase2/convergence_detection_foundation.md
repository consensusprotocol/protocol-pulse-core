# CONVERGENCE DETECTION — FOUNDATIONAL BUILD DOC
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# "The feature that makes people cancel Bloomberg"
# Created: 2026-03-23

---

## WHAT THIS IS

The Matrix Layer. A transformer-based multi-signal correlation engine that watches
five named convergence patterns 24/7 across on-chain, social, and macro data
simultaneously. When signals align, it fires. When they don't, silence.

No existing tool correlates whale UTXO movement + sentiment signals + macro
indicators in a single inference pass with sub-60-second detection latency.

Bloomberg correlates price with price. CoinMetrics gives you data. Glassnode gives
you charts. This gives you the moment before the moment — when the pieces are
assembling in real time across every data layer and nothing else has noticed yet.

---

## THE FIVE PATTERNS (V1 PATTERN LIBRARY)

### PATTERN 1 — SAFE-HAVEN ROTATION
**What it means:** Capital is rotating OUT of risk assets INTO Bitcoin as a safe-haven.
This is the macro thesis playing out in real time.

**Signal set:**
- On-chain: BTC exchange net outflow > 2x 30-day average (coins leaving exchanges = accumulation)
- Macro: Gold spot price +1.5% in 4h window
- Macro: DXY (US Dollar Index) declining > 0.5% in 4h window
- Sentiment: Sentiment score trending +15 points over 2h
- Confirming: CME futures basis expanding (institutional demand)

**Minimum signals to trigger WATCH: 3/5**
**Minimum signals to trigger CRITICAL: 5/5 sustained >2h**

---

### PATTERN 2 — MINER CAPITULATION CASCADE
**What it means:** Mining economics have broken. Miners are selling to cover costs.
This is historically the best time to accumulate.

**Signal set:**
- On-chain: Coinbase-to-exchange transactions > 300% of 7-day average
- On-chain: Hashrate 3-day average declining > 8% vs 14-day average
- On-chain: Difficulty adjustment incoming > -5% (negative adjustment = network shrinking)
- On-chain: Miner revenue per EH/s at 6-month low
- Mempool: Fee market softening (next-block fee < 5 sat/vB for > 2h)

**Minimum signals to trigger WATCH: 3/5**
**Minimum signals to trigger CRITICAL: 4/5**

---

### PATTERN 3 — WHALE ACCUMULATION PRE-MOVE
**What it means:** Large holders are quietly accumulating. Price move likely imminent.

**Signal set:**
- On-chain: 3+ whale addresses (>100 BTC clusters) moving within 90-minute window
- On-chain: Exchange reserve ratio declining > 1% over 24h
- On-chain: UTXO age bands: coins aged 6-12 months moving above 2x baseline
- Sentinel: PCAF v0/v1 anomaly score elevated (> 40/100) — unusual block timing
- Social: 2+ Tier-1 pseudonymous accounts posting accumulation signals

**Minimum signals to trigger WATCH: 3/5**
**Minimum signals to trigger CRITICAL: 4/5 + price still flat (pre-move window)**

---

### PATTERN 4 — INSTITUTIONAL ENTRY SIGNAL
**What it means:** Institutional capital is entering via ETFs and derivatives.
The smart money is moving before retail notices.

**Signal set:**
- ETF: Net inflow > $300M in 6h window (on-chain custodian wallet monitoring)
- Derivatives: CME futures basis expanding > 1.5% (premium = institutional demand)
- On-chain: Stablecoin minting (USDT/USDC) > $500M in 6h (dry powder entering)
- On-chain: Dormant coins (>1yr) NOT moving (long-term holders not distributing)
- Macro: SPY / equity markets up (risk-on environment)

**Minimum signals to trigger WATCH: 3/5**
**Minimum signals to trigger CRITICAL: 4/5**

---

### PATTERN 5 — REGULATORY SHOCK PROPAGATION
**What it means:** A regulatory event has hit. Measuring how far and fast it spreads.

**Signal set:**
- Sovereign Layer: Regulatory CRITICAL or WATCH alert fired in last 4h
- Sentiment: Score dropped > 25 points in < 2h (panic propagation)
- On-chain: Exchange inflows spike > 3x 30-day average (people moving to exchanges to sell)
- Sovereign Layer: P2P volume spike > 200% in affected jurisdiction
- Social: Regulatory keywords trending in top-10 Bitcoin Twitter (scraped)

**Minimum signals to trigger WATCH: 2/5 (regulatory alert already fired)**
**Minimum signals to trigger CRITICAL: 4/5**

---

## ARCHITECTURE

### Convergence Engine Design

```
[SentinelState] ──► [SignalExtractor] ──► [PatternStateMachine]
                                                    │
                         ┌──────────────────────────┤
                         │                          │
                    [PatternEvaluator]     [HistoricalBaseline]
                    (5 pattern rules)      (rolling 30-day stats)
                         │
                         ▼
                  [ConvergenceEvent]
                  {pattern, signals_confirmed, signals_total,
                   confidence_pct, first_signal_at, escalating,
                   tier: WATCH|CRITICAL}
                         │
                         ▼
              [AlertDispatcher] ──► Telegram + Voice
                         │
                         ▼
              [ConvergenceStore] ──► SQLite + in-memory cache
```

### Integration into Sentinel

The convergence engine runs as a module INSIDE sentinel.py — not a separate service.
It reads from the existing SentinelState (populated every 2s by the WebSocket loop)
and runs its pattern evaluation every 30 seconds.

New additions to SentinelState:
```python
convergence: dict = field(default_factory=lambda: {
    "active_events": [],      # list of ConvergenceEvent dicts
    "forming_events": [],     # partial patterns (1-2 signals confirmed)
    "resolved_events": [],    # last 10 resolved (confirmed or dissolved)
    "last_evaluated_at": 0.0,
})
```

### ConvergenceEvent data structure
```python
{
    "id": str,                    # uuid4
    "pattern": str,               # SAFE_HAVEN_ROTATION etc.
    "pattern_display": str,       # human label
    "signals_confirmed": int,     # how many signals are currently active
    "signals_total": int,         # total signals in this pattern (5)
    "confirmed_signals": list,    # names of confirmed signal
    "pending_signals": list,      # names of signals not yet confirmed
    "confidence_pct": int,        # signals_confirmed/signals_total * 100, adjusted
    "first_signal_at": float,     # unix timestamp of first confirming signal
    "last_updated_at": float,
    "escalating": bool,           # True if confidence grew in last evaluation cycle
    "tier": str,                  # NOTE / WATCH / CRITICAL
    "alert_fired": bool,          # whether Telegram alert has been sent
}
```

### Signal Extraction Layer (maps SentinelState → named booleans)

Each pattern signal must be expressed as a deterministic boolean computed
from current SentinelState + historical baseline data. The signal extractor
runs every 30 seconds and outputs a flat dict of all signal states:

```python
signals = {
    # Safe-Haven Rotation
    "exchange_net_outflow_2x": bool,
    "gold_price_up_1_5pct_4h": bool,
    "dxy_down_0_5pct_4h": bool,
    "sentiment_trending_up_15pts_2h": bool,
    "cme_basis_expanding": bool,

    # Miner Capitulation
    "coinbase_to_exchange_3x_7d": bool,
    "hashrate_declining_8pct": bool,
    "difficulty_adj_negative_5pct": bool,
    "miner_revenue_6mo_low": bool,
    "mempool_fees_soft": bool,

    # Whale Accumulation
    "whale_cluster_3_in_90min": bool,
    "exchange_reserve_declining_1pct_24h": bool,
    "utxo_6_12mo_moving_2x": bool,
    "pcaf_anomaly_elevated_40": bool,
    "tier1_accumulation_signal_2plus": bool,

    # Institutional Entry
    "etf_inflow_300m_6h": bool,
    "cme_basis_1_5pct": bool,
    "stablecoin_minting_500m_6h": bool,
    "dormant_coins_stable": bool,
    "equities_risk_on": bool,

    # Regulatory Shock
    "regulatory_alert_4h": bool,
    "sentiment_drop_25pts_2h": bool,
    "exchange_inflow_3x": bool,
    "p2p_spike_200pct": bool,
    "regulatory_trending_social": bool,
}
```

### Data Sources for Each Signal (Phase 2 — what exists vs. what needs building)

EXISTING (already in sentinel.py SentinelState):
- hashrate_3d, difficulty, orphan_count_6h ✓
- mempool fee bands ✓
- PCAF anomaly score ✓
- whale_txs feed (>50 BTC) ✓

NEEDS ADDING to sentinel polling:
- Gold price: use free API — api.metals.live/v1/spot/gold OR metals-api.com
  Fallback: scrape kitco.com/gold-price-today-usa.html (public)
- DXY: alphavantage.co/query?function=FX_INTRADAY&from_symbol=USD&to_symbol=DXY
  Fallback: marketstack.com (DXY not easy — use UUP ETF as proxy via Yahoo Finance)
- CME futures basis: Deribit API (free, no auth) for BTC perpetual funding rate as proxy
  Real CME data requires paid subscription — use Deribit funding rate as Phase 2 proxy
- ETF flows (intraday): monitor known custodian wallets on-chain
  BlackRock iShares: bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97 (known)
- Stablecoin minting: watch USDT/USDC mint/burn events via mempool.space token API
- Exchange reserve: compute from known exchange cold wallet cluster balances
  Use Glassnode public data OR compute from known wallet list
- Dormant coins: coin-days-destroyed metric from mempool.space/api/v1/mining/blocks
- Social Tier-1 signals: from X scraper (existing nitter scraper infra)
- Equities risk-on: SPY ETF via Yahoo Finance free API
- P2P volume: HodlHodl API (public)
  https://hodlhodl.com/api/v1/offers?filters[side]=buy&pagination[limit]=50
- Regulatory alert: already exists in Sentinel alert stream

### Historical Baseline Computation

For each signal that requires a baseline (e.g., "exchange outflow > 2x 30-day avg"):
- Store a rolling 30-day daily value in SQLite table: signal_baselines
- Update once per day at 00:00 UTC
- If < 7 days of data exists, use static bootstrap values from known historical ranges

```sql
CREATE TABLE signal_baselines (
    signal_name TEXT,
    date TEXT,
    value REAL,
    PRIMARY KEY (signal_name, date)
);
```

---

## FRONTEND — CONVERGENCE MONITOR PANEL

Location: Top-right panel in intelligence_terminal.html (per spec zone map)

Display per active event:
```
┌─────────────────────────────────────────────────────┐
│ 🔴 WHALE ACCUMULATION PRE-MOVE          WATCH       │
│ ████████░░  4/5 signals  ·  80% confidence          │
│ Forming since 14:32 ET  ·  ↑ ESCALATING             │
│ ✓ Whale clusters moving  ✓ Exchange reserves ↓      │
│ ✓ UTXO age bands active  ✓ PCAF elevated            │
│ ⏳ Tier-1 social signal  (1 of 2 required)          │
│ [FULL BREAKDOWN ▼]                                  │
└─────────────────────────────────────────────────────┘
```

Forming events (1-2 signals) shown as muted gray rows:
```
⬜ SAFE-HAVEN ROTATION  · 1/5 signals forming  · 14 min
```

Resolved events shown with outcome:
```
✅ MINER CAPITULATION (resolved 2h ago) — Pattern dissolved at 2/5
```

Animation: escalating events pulse slowly. CRITICAL events flash the panel border red.
Empty state: "NO ACTIVE CONVERGENCE EVENTS — NETWORK STABLE"

---

## ALERT COPY FOR EACH PATTERN

SAFE-HAVEN ROTATION WATCH:
"WATCH: Safe-Haven Rotation forming — 3/5 signals confirmed. BTC exchange outflows elevated, gold +1.8% in 4h, DXY weakening. Sentiment trending positive. CME basis pending."

MINER CAPITULATION CASCADE CRITICAL:
"CRITICAL: Miner Capitulation Cascade — 4/5 signals confirmed. Coinbase-to-exchange flow at 340% of 7-day average. Hashrate declining 11%. Negative difficulty adjustment incoming. Historically highest-confidence accumulation signal."

WHALE ACCUMULATION PRE-MOVE WATCH:
"WATCH: Whale Accumulation Pre-Move — 4/5 signals. 4 whale clusters (>100 BTC) moved within 70-minute window. Exchange reserves declining. PCAF anomaly elevated at 52. Monitoring for Tier-1 social confirmation."

INSTITUTIONAL ENTRY SIGNAL CRITICAL:
"CRITICAL: Institutional Entry Signal — 4/5 signals. ETF inflows $440M in 5h. CME basis expanded 2.1%. $800M stablecoin minted in 6h window. Long-term holders not distributing."

REGULATORY SHOCK PROPAGATION WATCH:
"WATCH: Regulatory Shock Propagation — Pattern forming. Regulatory alert fired 2h ago. Sentiment score dropped 31 points. Exchange inflows 2.8x baseline. Monitor P2P volume."

---

## BUILD ORDER WITHIN THIS FEATURE

Step 1: Signal extraction layer + historical baseline store (2 days)
Step 2: Pattern state machine — 5 patterns, deterministic rules (3 days)
Step 3: ConvergenceEvent store + alert dispatch integration (1 day)
Step 4: New data feeds (gold, DXY proxy, CME proxy, ETF wallet monitor) (3 days)
Step 5: Frontend Convergence Monitor panel (2 days)
Step 6: Integration tests + false positive verification (2 days)
Total: ~13 days to ship

---

## FILES TO CREATE / MODIFY

NEW:
  services/convergence_engine.py     — Pattern state machine, signal extractor
  services/signal_feeds.py           — Gold, DXY, CME, ETF, stablecoin data fetchers
  services/baseline_store.py         — Rolling 30-day baseline SQLite manager
  data/convergence_patterns.json     — Pattern definitions (editable without code deploy)

MODIFY:
  services/sentinel.py               — Add convergence_engine to main loop
  core/blueprints/intelligence.py    — Add /api/intelligence/convergence endpoint
  core/templates/intelligence_terminal.html — Add Convergence Monitor panel

---

## SUCCESS CRITERIA

Before this feature ships, the following must be true:

1. All 5 patterns have fired at least once in backtesting against 90 days
   of historical data — proving signal sets are reachable, not theoretical

2. False positive rate in backtesting < 25% (1 in 4 alerts max should be
   a non-event — same target as PCAF)

3. Detection latency: time from last confirming signal to WATCH alert < 60 seconds

4. Panel renders correctly with: 0 active events, 1 WATCH, 1 CRITICAL,
   3 simultaneous events, 5 simultaneous events

5. SSE stream delivers convergence state update within 4 seconds of pattern
   threshold crossing (2s state write + 2s SSE push)

6. Telegram alert fires within 30 seconds of WATCH threshold being crossed

7. Zero false alarms in 72h live test before declaring Phase 2 Feature 1 complete
