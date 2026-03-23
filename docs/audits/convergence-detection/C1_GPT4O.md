### QUESTION 1 — SIGNAL DESIGN:

**Pattern 1 — Safe-Haven Rotation:**
- **Exchange net outflow > 2x 30-day average:** Reliable but needs filtering for internal exchange movements.
- **Gold spot price +1.5% in 4h window:** Noisy due to frequent fluctuations; consider a longer window or additional confirmation.
- **DXY declining > 0.5% in 4h window:** Similar to gold, prone to noise; a combination with other macro indicators might be more reliable.
- **Sentiment score trending +15 points over 2h:** Sentiment data can be volatile; needs smoothing or averaging.
- **CME futures basis expanding:** Reliable if data source is stable.

**Pattern 2 — Miner Capitulation Cascade:**
- **Coinbase-to-exchange transactions > 300% of 7-day average:** Reliable if exchange wallet clusters are accurately identified.
- **Hashrate 3-day average declining > 8% vs 14-day average:** Reliable, but ensure data is not delayed.
- **Difficulty adjustment incoming > -5%:** Reliable, but ensure timely data.
- **Miner revenue per EH/s at 6-month low:** Reliable if revenue data is accurate.
- **Mempool fee market softening:** Reliable if mempool data is consistently updated.

**Pattern 3 — Whale Accumulation Pre-Move:**
- **3+ whale addresses moving within 90-minute window:** Reliable if whale addresses are correctly identified.
- **Exchange reserve ratio declining > 1% over 24h:** Reliable with accurate exchange wallet data.
- **UTXO age bands moving above 2x baseline:** Reliable if UTXO data is current.
- **PCAF anomaly score elevated:** Reliable if anomaly detection is accurate.
- **2+ Tier-1 pseudonymous accounts posting signals:** Noisy; requires careful filtering and validation.

**Pattern 4 — Institutional Entry Signal:**
- **ETF net inflow > $300M in 6h window:** Reliable if custodian wallet monitoring is accurate.
- **CME futures basis expanding > 1.5%:** Reliable with stable data source.
- **Stablecoin minting > $500M in 6h:** Reliable if minting events are accurately captured.
- **Dormant coins not moving:** Reliable if UTXO data is accurate.
- **SPY / equity markets up:** Noisy; requires confirmation with other macro indicators.

**Pattern 5 — Regulatory Shock Propagation:**
- **Regulatory alert fired in last 4h:** Reliable if alert system is accurate.
- **Sentiment score dropped > 25 points in < 2h:** Noisy; requires smoothing.
- **Exchange inflows spike > 3x 30-day average:** Reliable if exchange wallet data is accurate.
- **P2P volume spike > 200% in affected jurisdiction:** Reliable if P2P data is current.
- **Regulatory keywords trending on social media:** Noisy; requires careful filtering.

### QUESTION 2 — FALSE POSITIVE KILL RATE:

- **Safe-Haven Rotation:** Require a minimum 6-hour confirmation window for macro signals (gold, DXY) to confirm persistence. Cross-validate with at least one on-chain signal.
- **Miner Capitulation Cascade:** Require a 24-hour persistence for hashrate and difficulty signals to confirm a sustained trend.
- **Whale Accumulation Pre-Move:** Require a 12-hour persistence for whale movements and exchange reserve changes; cross-validate with social signals.
- **Institutional Entry Signal:** Require at least two macro signals to confirm within a 12-hour window; cross-validate with on-chain signals.
- **Regulatory Shock Propagation:** Require a 4-hour persistence for sentiment and exchange inflow signals; cross-validate with P2P volume spikes.

### QUESTION 3 — DATA DEPENDENCY AUDIT:

- **A-Grade:**
  - Mempool fee market softening
  - Hashrate decline
  - Difficulty adjustment
  - Exchange inflows
  - Whale clusters moving

- **B-Grade:**
  - Gold price (requires fallback to scraping)
  - DXY (requires fallback to ETF proxy)
  - CME futures basis (requires proxy)
  - Stablecoin minting (requires fallback to on-chain data)
  - Sentiment score (requires smoothing)

- **C-Grade:**
  - Tier-1 social signals: Replace with a more structured sentiment analysis using NLP models.
  - Regulatory keywords trending: Replace with a structured news feed analysis using NLP.

### QUESTION 4 — TRANSFORMER VS RULE-BASED:

A rule-based approach is more suitable for Phase 2. It allows for deterministic evaluation of signals and is easier to debug and optimize given the current data quality. A transformer model might overfit to noise and require extensive training data, which is not feasible with the current data sources. The rule-based system can be enhanced with machine learning models in future phases once data quality and volume improve.

### QUESTION 5 — LATENCY AUDIT:

- Use a weighted average approach where more frequent signals (e.g., mempool) have higher weights in short-term evaluations, while less frequent signals (e.g., ETF flows) have higher weights in long-term evaluations.
- Implement a decay function for signal relevance based on time since last update, ensuring that older signals are gradually deprioritized unless confirmed by newer data.
- Prioritize signals that have updated within the last evaluation cycle to avoid stale data influencing decisions.

### QUESTION 6 — FRONTEND CHALLENGE:

- **Empty State:** "NO ACTIVE CONVERGENCE EVENTS — NETWORK STABLE"
- **Forming State:** Gray background with muted icons, showing pattern name and forming signals.
- **Watching State:** Yellow background with pulsing icons, showing pattern name, confirmed signals, confidence percentage, and time since first signal.
- **Critical State:** Red background with flashing border, showing pattern name, all confirmed signals, confidence percentage, and escalation indicator.
- **Resolved State:** Green background with checkmark, showing pattern name and resolution outcome.
- **Interaction:** Clicking an event expands it to show full signal breakdown and historical context. The panel should be designed to allow quick scanning and immediate understanding of the network state.

### QUESTION 7 — 6TH PATTERN:

**Pattern Name:** "LIQUIDITY CRUNCH SIGNAL"
- **Signal Set:**
  - On-chain: Exchange reserve ratio increasing > 2% over 24h
  - On-chain: Stablecoin outflows > $500M in 6h
  - Macro: Interest rates rising > 0.5% in 24h
  - Sentiment: Negative sentiment spike > 20 points in 2h
  - Mempool: Fee market tightening (next-block fee > 50 sat/vB for > 2h)

**WATCH Threshold:** 3/5 signals confirmed
**CRITICAL Threshold:** 4/5 signals confirmed with sustained > 4h

### QUESTION 8 — INTEGRATION HARDENING:

- **Race Conditions:** Ensure atomic writes to `/tmp/sentinel_state.json` to prevent partial updates.
- **Data Freshness Failures:** Implement a timestamp check before reading the state file to ensure data is current.
- **Stale Signal Propagation:** Use a time-to-live (TTL) mechanism for signals to ensure they are refreshed or invalidated after a certain period.
- **Edge Cases:** Implement fallback logic for missing or delayed data, using historical averages or proxies to maintain continuity.
- **Hardening:** Use file locks during state updates, implement robust error handling for data fetch failures, and ensure SSE streams are resilient to temporary network issues.