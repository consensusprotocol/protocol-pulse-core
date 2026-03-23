# CONVERGENCE DETECTION — V1 BUILD SPECIFICATION
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# Date: 2026-03-23
# Status: AUDIT-HARDENED — Ready for Implementation
# Version: 2.0 (Post Cross-LLM Audit)

---

## 1. EXECUTIVE SUMMARY

### What This Is

The Convergence Detection engine is a real-time, rule-based multi-signal correlation system that monitors six named market patterns simultaneously across on-chain, macro, and structured news data. When signals from multiple data layers align within a defined detection window, the engine escalates through defined states (FORMING → WATCH → CRITICAL) and dispatches alerts. When signals diverge or expire, it dissolves quietly. The engine runs as an embedded module inside `sentinel.py`, evaluating pattern state every 60 seconds against signals derived from the existing `SentinelState` object plus six new external data feeds.

### What It Replaces

No existing tool does this. Bloomberg correlates price with price. Glassnode gives you charts. CoinMetrics gives you data. This gives you the moment before the moment — the period during which capital, behavior, and macro environment are assembling in detectable ways before price moves.

Specifically:
- **Replaces manual monitoring** of 5–6 disparate dashboards (Glassnode, mempool.space, TradingView, CME data, news feeds) that an analyst would need to watch simultaneously to catch these patterns.
- **Replaces intuition-based alerts** that require an expert to be watching at the right moment.
- **Does not replace** Bloomberg Terminal, Glassnode, or CoinMetrics for deep-dive analysis. It is the detection layer that tells you *when* to open those tools.

### Why It Matters

The product positioning claim: "The feature that makes people cancel Bloomberg" is earned by this: Bloomberg correlates price with price. This engine correlates miner behavior with macro stress with institutional flow with on-chain accumulation in a single inference pass. At sub-60-second detection latency. At zero incremental cost to the user after subscription.

### Scope of This Document

This document specifies everything required to build, test, and ship Phase 2 Feature 1. It is the authoritative implementation reference. No decision made in this document requires further approval before implementation. All audit findings from the GPT-4o and Grok-3 cross-examination cycles (2 cycles each) are incorporated and binding.

---

## 2. ARCHITECTURE DECISION: RULE-BASED

**BINDING DECISION: Rule-based pattern evaluation engine. Not a transformer. Not ML of any kind in Phase 2.**

This decision is final. It emerged from independent convergence across both audit models across both evaluation cycles and was not challenged in cross-examination.

### Technical Justification

**1. Training data does not exist and cannot be fabricated.**

A machine learning approach to convergence detection requires a labeled dataset of historical convergence events: timestamps, multi-signal state snapshots at detection time, and binary outcome labels (did the predicted market event occur?). Protocol Pulse has no such dataset at Phase 2 inception. The labeled dataset *can only be generated* by running a rule-based system for 6+ months and collecting observations. ML is architecturally downstream of the rule-based system — it is a Phase 3+ optimization, not a Phase 2 option.

**2. Data quality disqualifies ML.**

Of the 25 signals audited in the original spec, 6 were rated C-grade (replaced), 11 B-grade (significant noise caveats), and only 8 A-grade. Training a model on a signal corpus where the majority of inputs have noise, coverage gaps, or proxy-measurement error produces a model that learns to amplify the noise. Overfitting risk on a noisy, small-sample dataset is catastrophically high.

**3. Debuggability is a product requirement.**

High-stakes users who receive a CRITICAL alert at 3am must be able to understand *why* the alert fired within seconds of reading it. A rule engine produces a readable audit trail: "Pattern fired because signals #7, #8, #9, and #10 all confirmed within the 24-hour evaluation window. Guard rail: hashrate and difficulty both confirmed (required). Persistence: 4/4 required checks passed." A neural network produces an embedding vector. Only the rule engine satisfies the system's implicit transparency contract with its users.

**4. Phase 2 scope is incompatible with ML infrastructure.**

ML adds: training pipeline, model versioning, inference latency management, model drift monitoring, retraining schedule, and A/B testing framework. None of this is in Phase 2 scope. A rule engine can be built, tuned, tested, and shipped within the defined timeline.

### Implementation Architecture

```
Each pattern is a class inheriting from BasePattern with three methods:
  - evaluate(signals: dict, baseline: dict) -> PatternState
  - check_persistence(state: PatternState, history: list) -> bool
  - validate_cross_signals(signals: dict) -> CrossValidationResult

Signal thresholds are loaded from convergence_config.yaml (not hardcoded).
All guard rail checks are logged to audit_log[] regardless of pass/fail.
PatternState objects carry the full decision trail.
```

### Future ML Path (Non-Binding, For Reference)

After 6+ months of labeled rule-based observations, evaluate a gradient-boosted tree ensemble (XGBoost/LightGBM) for signal *weight* optimization within the existing rule framework. A transformer may be appropriate for NLP components only (news sentiment classification) in Phase 3+. No transformer-based end-to-end convergence detection should be built until a dataset of 500+ labeled events exists with outcome validation.

---

## 3. FINAL PATTERN LIBRARY

### Signal Grade Legend
- **A** — High confidence, direct source, low noise
- **B** — Acceptable with stated caveats and required validation
- **B*** — B-grade replacement for a C-grade signal
- **CTX** — Supporting context signal, half-weight (0.5), does not count toward threshold integer

---

### PATTERN 1 — SAFE-HAVEN ROTATION

**Description:** Capital is rotating out of risk assets into Bitcoin as a perceived safe-haven. This is the macro thesis (BTC as digital gold) playing out in real time. Characterized by simultaneous institutional-scale BTC accumulation, macro stress indicators firing, and sentiment improvement on BTC-specific channels.

**Signal Set:**

| ID | Signal Name | Threshold | Grade | Source | Notes |
|----|-------------|-----------|-------|--------|-------|
| SHR-1 | BTC exchange net outflow | >2x 30-day average, sustained 3 consecutive hourly checks | A | mempool.space known exchange wallets | Must pass `validate_not_internal_transfer()`. Cross-validate: exchange reserve ratio must simultaneously decline ≥0.5% |
| SHR-2 | VIX spike (replaces Gold) | >20% above 30-day average, sustained 24h | B* | Yahoo Finance `^VIX` | Replaces gold spot price (C-grade). If VIX unavailable, use gold >+2.0% sustained 8h as fallback only |
| SHR-3 | SPY risk-on confirmation (replaces DXY) | SPY >+1.0% sustained 4h | B* | Yahoo Finance `SPY` | Replaces DXY (C-grade). SPY rise confirms macro rotation rather than pure gold/safe-haven noise |
| SHR-4 | Volume-weighted sentiment trending positive | Score >+10 pts above 7-day rolling baseline, with concurrent post volume ≥50% above 2h baseline, sustained 4 of 6 window hours | B | Internal sentiment scraper | Volume-weighted. Smoothed with 30-min EMA before threshold check. 7-day rolling average as explicit baseline |
| SHR-5 | CME/Deribit basis expanding | >+1.0% over 4h, sustained | B | Deribit API (perpetual funding rate as proxy) | Must be cross-validated with at least one on-chain signal (SHR-1) before counting. Deribit is Phase 2 proxy for real CME data |

**Thresholds:**
- **WATCH:** 3/5 signals confirmed
- **CRITICAL:** 5/5 sustained >2h (or 4/5 with VIX as mandatory confirmed)

**Minimum Confirmation Window:** 6 hours from first signal to WATCH alert emission.

**Signal Persistence Requirements:**
- SHR-2 (VIX): Must sustain >20% for full 6h window, checked at 30-minute intervals. Failure at any interval resets the persistence counter.
- SHR-1 (exchange outflow): Must persist across 3 consecutive hourly checks. Single large transaction does not satisfy this.
- SHR-4 (sentiment): Must sustain >+10 pts above baseline (smoothed) for 4 of 6 window hours.
- SHR-3 (SPY): Must sustain >+1.0% for full 4h window.
- SHR-5 (CME basis): Must sustain >+1.0% for full 4h window.

**False Positive Guard Rails:**
1. **Cross-layer requirement:** Cannot fire on macro signals (SHR-2, SHR-3) alone. At least 1 on-chain signal (SHR-1 or SHR-5) must be active simultaneously before the counter reaches WATCH threshold.
2. **Internal transfer filter:** SHR-1 only counts after `validate_not_internal_transfer()` passes against known intra-exchange wallet clusters. Exchange reserve ratio must simultaneously show ≥0.5% decline.
3. **Time-of-day adjustments:**
   - Asian session (00:00–08:00 UTC): Increase outflow threshold to 2.5x. Increase SHR-4 volume requirement by 30%.
   - US open (13:00–17:00 UTC): Standard thresholds. Add 30-minute delay before any CRITICAL alert to absorb opening volatility.
   - Weekend: Extend VIX and SPY signal persistence to 8h. Lower institutional activity means macro moves are more likely speculative.
4. **State must not skip FORMING:** Pattern must pass through FORMING state before WATCH. Direct WATCH entry is blocked.

---

### PATTERN 2 — MINER CAPITULATION CASCADE

**Description:** Mining economics have broken down. Miners are selling BTC to cover operational costs. Hashrate is declining, revenue per unit of computation is at a low, and fees are soft — all simultaneously. Historically the highest-confidence accumulation signal in BTC market cycles.

**Signal Set:**

| ID | Signal Name | Threshold | Grade | Source | Notes |
|----|-------------|-----------|-------|--------|-------|
| MCC-1 | Coinbase-to-exchange transactions | >300% of 7-day average, sustained 6h | B | On-chain tagged miner wallets | Must pass `validate_miner_wallet_cluster()`. Only wallets confirmed as mining-entity-associated in last 90 days. Known addresses: F2Pool, AntPool, Foundry, ViaBTC |
| MCC-2 | Hashrate 3-day average declining | >8% vs 14-day average, showing continued degradation at each 6h check | A | mempool.space `/api/v1/mining/hashrate/3d` | Dual-average comparison is methodologically sound |
| MCC-3 | Difficulty adjustment incoming | >-5% (negative adjustment) | A | Computed from blockchain data: `next_difficulty_adjustment` | Deterministic. Counts once confirmed. No persistence requirement |
| MCC-4 | Miner revenue per EH/s at 6-month low | Current value < any value in rolling 180-day window | B | mempool.space fee data + hashrate estimates | Requires persistent 6-month rolling window in SQLite. Cross-validate against mempool fee market to avoid false readings during fee spikes |
| MCC-5 | Mempool fee market softening | Next-block fee <5 sat/vB sustained >4h cumulative during evaluation window | A | mempool.space `/api/v1/fees/recommended` | Direct, low-latency, low-noise |

**Contextual Indicator (non-counting):**
- **MCC-CTX:** WTI crude oil +5% in 24h — mining cost pressure context. Source: Yahoo Finance `CL=F`. Displayed in UI as supporting context. Does not count toward WATCH/CRITICAL thresholds. Weight: 0 for threshold count, displayed as amber indicator in signal breakdown.

**Thresholds:**
- **WATCH:** 3/5 signals confirmed
- **CRITICAL:** 4/5 signals confirmed

**Minimum Confirmation Window:** 24 hours. Miner capitulation is a slow-moving systemic event. The 24h window eliminates noise from single-session anomalies.

**Signal Persistence Requirements:**
- MCC-2 (hashrate): Must show continued degradation at each 6h check during the 24h window. A single non-declining check does not invalidate; two consecutive non-declining checks reset the counter.
- MCC-3 (difficulty): Deterministic. Counts once confirmed from blockchain data.
- MCC-4 (miner revenue): Must remain at 6-month low for 12 of 24 evaluation hours. Not required to be continuous (accommodates intraday fee spikes).
- MCC-5 (mempool fees): Must sustain <5 sat/vB for >4h cumulative during evaluation window.
- MCC-1 (coinbase flows): Must sustain >300% for 6h continuous.

**False Positive Guard Rails:**
1. **Anchor signal requirement:** MCC-2 (hashrate decline) AND MCC-3 (difficulty adjustment) must both be confirmed before CRITICAL is possible. Neither can be absent at CRITICAL threshold. These are the two anchor signals.
2. **Suppression rule:** If miner wallet flows (MCC-1) appear without hashrate decline (MCC-2), suppress the pattern entirely. This indicates exchange reshuffling, not genuine capitulation.
3. **Miner wallet validation:** MCC-1 must pass `validate_miner_wallet_cluster()` before counting.
4. **Exclude maintenance windows:** Exclude single-hour inflow spikes that occur during documented major exchange maintenance windows (maintain a static maintenance_windows.json reference file).
5. **Time-of-day adjustments:** Minimal impact at 24h windows. However, no evaluation window should be started from a partial day — always compute from the most recent complete 24h cycle.

---

### PATTERN 3 — WHALE ACCUMULATION PRE-MOVE

**Description:** Large BTC holders (>100 BTC clusters) are quietly accumulating. Price has not yet moved significantly. Coins are flowing from exchange-adjacent storage to cold storage. A price move is likely imminent because accumulation at this scale historically precedes significant directional moves.

**Signal Set:**

| ID | Signal Name | Threshold | Grade | Source | Notes |
|----|-------------|-----------|-------|--------|-------|
| WAP-1 | Whale cluster movements | 3+ non-exchange whale addresses (>100 BTC) moving within any 90-min window during evaluation period | B | mempool.space large transaction feed + known wallet registry | Must pass `filter_exchange_controlled_addresses()`. Minimum 2 of 3 qualifying movements must terminate at non-exchange destinations (cold wallets, OTC desk addresses, unknown wallets) |
| WAP-2 | Exchange reserve ratio declining | >1% over 24h, shown across 3 consecutive 4h checks | A | Known exchange cold wallet cluster balances | Long window filters noise. 24h is appropriate |
| WAP-3 | UTXO age bands (6–12 months) moving | >2x baseline, sustained 8 of 12 evaluation hours | A | mempool.space coin-days-destroyed metrics | Targets whale-scale accumulation. 6-12mo band avoids recent-buyer noise |
| WAP-4 | PCAF anomaly score elevated | >40/100 | B | Internal `/lib/pcaf_scorer.py` | **Critical implementation requirement:** PCAF score formula must be published and auditable before this counts toward threshold. Formula: `weight(clustering_coefficient_recent_large_txs) + weight(deviation_from_address_reuse_patterns) + weight(cross_pattern_address_appearance)`. Until formula is published and validated, treat as supporting context only (does not count toward WATCH/CRITICAL threshold integer). See Section 11. |
| WAP-5 | Large unconfirmed transaction volume (replaces Tier-1 social) | Sum of unconfirmed transactions >100 BTC each exceeds 3x 4h average | B* | mempool.space unconfirmed transaction feed | Replaces Tier-1 pseudonymous accounts (C-grade). Captures OTC desk activity via on-chain data without social media dependency |

**Thresholds:**
- **WATCH:** 3/5 signals confirmed
- **CRITICAL:** 4/5 confirmed AND BTC price movement <4% in last 4h (pre-move window still open)

**Minimum Confirmation Window:** 12 hours from first whale movement signal.

**Signal Persistence Requirements:**
- WAP-1 (whale movements): Require 3+ qualifying movements within any 90-min window during the 12h evaluation period. A single cluster of qualifying movements initiates WATCH consideration; a second qualifying cluster within 12h elevates to CRITICAL consideration.
- WAP-2 (exchange reserve): Must show sustained decline across 3 consecutive 4h checks (not just one large withdrawal).
- WAP-3 (UTXO age bands): Must remain elevated for 8 of 12 evaluation hours.
- WAP-4 (PCAF, if counting): Must remain >40 for 6 of 12 evaluation hours.
- WAP-5 (unconfirmed volume): Must sustain >3x 4h average for 2 consecutive 30-minute checks.

**False Positive Guard Rails:**
1. **Price stability check:** If BTC price has moved >4% in either direction in the last 4h, suppress the CRITICAL state. The pre-move window has likely closed. Pattern downgrades to WATCH with a "LATE DETECTION" flag.
2. **Exchange address filter:** WAP-1 must pass `filter_exchange_controlled_addresses()`. Minimum 2 of 3 qualifying movements must terminate at non-exchange destinations. This is a hard requirement, not a soft check.
3. **PCAF gate:** WAP-4 does not count toward integer threshold until `/lib/pcaf_scorer.py` formula is published. Until then, displayed as context indicator only.
4. **Time-of-day adjustments:**
   - OTC hours (16:00–20:00 UTC, US business day): Lower WAP-1 threshold to 2+ qualifying movements (institutional OTC activity is highest, so 3 movements is too restrictive during this window).
   - Asian session (00:00–08:00 UTC): Increase WAP-1 threshold to 4+ qualifying movements (lower overall volume makes 3 large movements more likely to be noise).

---

### PATTERN 4 — INSTITUTIONAL ENTRY SIGNAL

**Description:** Institutional capital is entering via ETF custodian wallets and derivatives markets. Stablecoin dry powder is minting. Long-term holders are not selling into the institutional buying. The smart money is positioning before retail notices.

**Signal Set:**

| ID | Signal Name | Threshold | Grade | Source | Notes |
|----|-------------|-----------|-------|--------|-------|
| IES-1 | Custodian wallet inflow proxy (replaces ETF net inflow) | Known BlackRock/Fidelity/Grayscale/Coinbase Custody BTC wallet inflows >$150M equivalent in 6h window, across at least 3 of 6 two-hour sub-windows in the 12h evaluation period | B* | mempool.space with labeled custodian wallet addresses | Replaces real-time ETF inflow monitoring (C-grade, data unavailable via free APIs). Flagged as proxy in UI display. See custodian wallet address registry in Appendix A |
| IES-2 | CME/Deribit futures basis expanding | >1.5% over 4h consecutive | B | Deribit perpetual funding rate API | Must sustain 4 consecutive hours before counting. Cross-validate against IES-3 (stablecoin minting) to confirm dry powder is available |
| IES-3 | Stablecoin net minting (USDT+USDC) | >$500M total in 6h window | A | mempool.space USDT on-chain + Circle USDC API | Strong historical correlation with institutional buying pressure. Mandatory signal for CRITICAL |
| IES-4 | Dormant coins (>1yr) NOT moving | coin-days-destroyed metric <0.5x 30-day baseline throughout 12h window | A | mempool.space coin-days-destroyed | Inverted logic: absence of event = signal confirmed. Implement as explicit threshold check `dormant_cdd < 0.5 * baseline_30d`, not a null check |
| IES-5 | SPY/equity risk-on | SPY >+1.0% sustained 4h | B | Yahoo Finance `SPY` | Tightened from "up" to >+1.0%. Counts only if concurrent with at least one on-chain signal (IES-1 or IES-3). Downweighted in confidence formula (B-grade weight = 0.7) |

**Thresholds:**
- **WATCH:** 3/5 signals confirmed
- **CRITICAL:** 4/5 signals confirmed. IES-3 (stablecoin minting) is mandatory at CRITICAL — institutional entry without stablecoin dry powder is suspect.

**Minimum Confirmation Window:** 12 hours.

**Signal Persistence Requirements:**
- IES-1 (custodian wallets): Must show continued inflow activity across at least 3 of the 6 two-hour sub-windows in the 12h evaluation period. Single large transaction does not satisfy.
- IES-2 (basis): Must sustain >1.5% for 4 consecutive hours.
- IES-3 (stablecoin minting): Must reach $500M threshold within any 6h sub-window of the 12h evaluation period. A single minting event qualifies if it meets threshold.
- IES-4 (dormant coins): Must confirm absence of coin-days-destroyed spike throughout the full 12h window.
- IES-5 (SPY): Must sustain >+1.0% for the full 4h window.

**False Positive Guard Rails:**
1. **Stablecoin mandatory rule:** IES-3 must be confirmed for CRITICAL. If four other signals confirm without stablecoin minting, the pattern stays at WATCH with the note "Awaiting stablecoin confirmation for CRITICAL."
2. **At least two macro signals:** At least 2 of (IES-2, IES-3, IES-5) must fire before CRITICAL is possible.
3. **US market hours gate for IES-1:** ETF custodian wallet movements outside US market hours (21:00–13:00 UTC) are flagged as potentially anomalous, not routine inflows. Do not count toward WATCH/CRITICAL threshold during these hours; display as context only.
4. **US open suppression:** Suppress CRITICAL alerts during 13:30–14:00 UTC (first 30 minutes of US open). Allow WATCH state only. CRITICAL can elevate after 14:00 UTC if thresholds are still met.
5. **IES-5 dependency rule:** IES-5 (SPY) only counts if at least one on-chain signal (IES-1 or IES-3) is simultaneously confirmed.

---

### PATTERN 5 — REGULATORY SHOCK PROPAGATION

**Description:** A regulatory event has occurred and is propagating through the market. The engine measures how far and fast the shock is spreading — from exchange inflows (people moving to sell) to privacy-seeking behavior (coinjoins) to P2P volume spikes in the affected jurisdiction. Designed to give a rapid read on whether this is a contained event or a systemic cascade.

**Signal Set:**

| ID | Signal Name | Threshold | Grade | Source | Notes |
|----|-------------|-----------|-------|--------|-------|
| RSP-1 | Regulatory CRITICAL or WATCH alert | Alert fired in last 4h in Sentinel alert stream | A | Internal Sentinel alert stream | Mandatory signal. Pattern cannot fire without this. Alert must remain in CRITICAL/WATCH state throughout evaluation window |
| RSP-2 | Multi-source news sentiment (replaces raw sentiment drop) | 3+ independent news sources (Reuters, AP, CoinDesk, Bloomberg Crypto RSS) confirm negative framing with regulatory keyword match within 2h window | B* | RSS feeds from Reuters/AP/CoinDesk | Replaces raw sentiment score drop (C-grade). Lower velocity, higher precision. Until RSS pipeline is operational, use sentiment score >30 pt drop as temporary proxy — flagged in UI as "PROXY SIGNAL" |
| RSP-3 | Exchange inflow spike | >3x 30-day average, sustained 2h (not instantaneous) | B | Known exchange wallet inflows | Must pass internal-transfer filter. 2h persistence filters single large transactions. Excludes known exchange internal consolidations |
| RSP-4 | Coinjoin transaction volume spike (replaces regulatory social trending) | Coinjoin transaction count >2x 7-day average sustained >4h | B* | mempool.space coinjoin detection | Replaces regulatory keywords trending on X (C-grade). Privacy-seeking behavior accelerates reliably under genuine regulatory pressure |
| RSP-5 | P2P volume spike in affected jurisdiction | >200% of 7-day average in jurisdiction matching the regulatory alert | CTX | HodlHodl public API + LocalBitcoins historical | **Half-signal (weight: 0.5). Does not count as a full counting signal.** Retained for informational value. Jurisdiction must match regulatory alert jurisdiction. Coverage gaps acknowledged |

**Thresholds:**
- **WATCH:** 2/4.5 signals confirmed (RSP-1 mandatory + 1.5 from RSP-2/3/4/5. Note: RSP-5 at 0.5 weight means RSP-1 + RSP-3 + RSP-5 = 2.5, which satisfies WATCH)
- **CRITICAL:** 4/4.5 signals confirmed (treating RSP-5 as 0.5)

**Minimum Confirmation Window:** 4 hours. Regulatory events are time-sensitive. A 12h window would miss the actionable detection period.

**Signal Persistence Requirements:**
- RSP-1 (regulatory alert): Must remain in CRITICAL/WATCH state throughout the 4h evaluation window. If the alert auto-resolves in Sentinel before the 4h window closes, RSP pattern evaluates resolution.
- RSP-3 (exchange inflows): Must sustain >2x 30-day average (relaxed from 3x spike for persistence) for 2h cumulative during the 4h window.
- RSP-2 (multi-source news): Requires 3+ independent sources within 4h window. Each source counts once; repetition of the same story across outlets counts as 1.
- RSP-4 (coinjoin volume): Must sustain >2x average for majority (>2h) of the 4h window.
- RSP-5 (P2P volume): Single check sufficient given half-weight.

**False Positive Guard Rails:**
1. **Regulatory alert mandatory:** RSP-1 must be confirmed for any state above IDLE. This prevents exchange inflow spikes from spuriously triggering the regulatory pattern.
2. **Late detection flag:** If BTC price has already dropped >10% before pattern evaluation begins, flag as "LATE DETECTION — INFORMATIONAL ONLY." The shock has already propagated.
3. **Jurisdiction match:** RSP-5 (P2P volume) only counts toward its 0.5 weight if the jurisdiction matches the regulatory alert jurisdiction. Cross-jurisdictional P2P spikes are logged as context but have zero weight.
4. **Time-of-day adjustments:**
   - US regulatory alert during US business hours (13:00–21:00 UTC): Permit WATCH after 2h persistence (faster market response expected).
   - Asian regulatory alert outside Asian hours (01:00–09:00 UTC): Require full 4h persistence before WATCH. Market response is delayed when the alert fires outside the relevant market session.
5. **Coordinated FUD suppression:** If RSP-2 fires but RSP-1 has not fired (no Sentinel regulatory alert), RSP-2 is displayed as context only. Pattern stays in IDLE. Social/media signals without a regulatory event trigger are not a pattern.

---

### PATTERN 6 — LIQUIDITY STRESS CASCADE

**Description:** Market liquidity is evaporating. Stablecoins are leaving the ecosystem rather than accumulating as dry powder. Exchange reserves are increasing (people sending BTC to exchanges, not taking it off). Mempool fees are rising as on-chain activity compresses into fee competition. VIX confirms macro-level risk stress. This pattern precedes forced liquidation events and systemic deleveraging. Unlike Regulatory Shock, this is structurally driven rather than event-driven.

**Signal Set:**

| ID | Signal Name | Threshold | Grade | Source | Notes |
|----|-------------|-----------|-------|--------|-------|
| LSC-1 | Exchange reserve ratio increasing | >2% over 24h, shown across 3 consecutive 8h checks | A | mempool.space known exchange wallet data | Inverted from Pattern 3/4. Rising reserves = coins moving TO exchanges (selling pressure) |
| LSC-2 | Stablecoin net outflows (USDT+USDC combined) | >$400M net outflows in 8h window | A | Token APIs (mempool.space USDT + Circle USDC API) | Adjusted from $500M/6h to $400M/8h — reduces noise, extends detection window. Stablecoin leaving = dry powder exiting |
| LSC-3 | Mempool fee market tightening | Next-block fee >40 sat/vB sustained 3h | A | mempool.space `/api/v1/fees/recommended` | Lowered from 50 sat/vB. Extended from 2h to 3h for noise reduction |
| LSC-4 | BTC exchange inflows rising | >2x 30-day average over 6h | B | On-chain exchange inflow monitoring | Adjusted from 3x/12h. Must pass internal-transfer filter. Note: This signal also appears in RSP-3 — if Pattern 5 is simultaneously active, cross-reference but do not suppress either pattern |
| LSC-5 | VIX risk-off macro indicator | >20% above 30-day VIX average, sustained 24h | B | Yahoo Finance `^VIX` | Same source as SHR-2. If both SHR and LSC fire simultaneously with VIX, the same VIX reading satisfies both patterns — this is expected and correct behavior, not double-counting |

**Thresholds:**
- **WATCH:** 3/5 signals confirmed
- **CRITICAL:** 4/5 signals confirmed

**Minimum Confirmation Window:** 12 hours.

**Signal Persistence Requirements:**
- LSC-1 (exchange reserves): Must show sustained increase across 3 consecutive 8h checks.
- LSC-2 (stablecoin outflows): Must sustain net outflow >$400M in any 8h window during the 12h evaluation period.
- LSC-3 (mempool fees): Must sustain >40 sat/vB for 3h continuous.
- LSC-4 (exchange inflows): Must sustain >2x average for 6h cumulative during evaluation period.
- LSC-5 (VIX): Must sustain >20% above 30-day average for full 24h. This means LSC-5 is often a lagging confirmer rather than a leading signal — correct behavior.

**False Positive Guard Rails:**
1. **Directional consistency check:** LSC-1 (exchange reserves rising) and LSC-4 (exchange inflows rising) must be directionally consistent. If reserves are rising but inflows are not (implying internal consolidation), suppress LSC-4. If both are rising, counts normally.
2. **Pattern 5 cross-reference:** If Pattern 5 (Regulatory Shock) is simultaneously in WATCH or CRITICAL state, LSC-4 (exchange inflows) may be double-attributed. Do not suppress either pattern, but add a cross-reference note in both UI cards: "LSC-4 also attributed to active RSP pattern." Do not artificially reduce either pattern's confidence.
3. **Stablecoin outflow vs. Pattern 4:** If Pattern 4 (Institutional Entry) is simultaneously in WATCH state (expecting stablecoin *inflows*), and LSC-2 is showing stablecoin *outflows*, flag a pattern contradiction: "CONTRADICTION: IES-3 expects stablecoin accumulation. LSC-2 shows stablecoin outflows. Verify data freshness." Do not suppress either pattern; require human review.
4. **Time-of-day:** LSC-3 (mempool fees) can spike temporarily during high-demand periods (ordinal inscriptions, major exchange withdrawals) without structural liquidity stress. Require 3h sustained (already implemented in threshold) and cross-validate with LSC-1 or LSC-2 before counting LSC-3 toward threshold.

---

## 4. SIGNAL EXTRACTION LAYER

The `SignalExtractor` class runs every 60 seconds, reads from `SentinelState` plus the external data feed cache, and outputs a flat `signals` dict of booleans plus a `signal_metadata` dict with the raw values, freshness timestamps, decay factors, and validation audit logs.

### Complete Signal Dictionary (30 Signals)

```python
signals: dict = {
    # ─── PATTERN 1: SAFE-HAVEN ROTATION ─────────────────────────────────
    "SHR_1_exchange_net_outflow_2x": {
        "confirmed": bool,
        "raw_value": float,          # current outflow ratio vs 30d avg
        "threshold": 2.0,
        "grade": "A",
        "last_updated": float,       # unix timestamp
        "validation_passed": bool,   # result of validate_not_internal_transfer()
        "decay_factor": float,       # 0.0–1.0
    },
    "SHR_2_vix_spike_20pct": {
        "confirmed": bool,
        "raw_value": float,          # VIX % change vs 30d average
        "threshold": 20.0,
        "grade": "B",
        "last_updated": float,
        "fallback_active": bool,     # True if using gold fallback
        "decay_factor": float,
    },
    "SHR_3_spy_risk_on_1pct": {
        "confirmed": bool,
        "raw_value": float,          # SPY % change
        "threshold": 1.0,
        "grade": "B",
        "last_updated": float,
        "decay_factor": float,
    },
    "SHR_4_sentiment_trending_up": {
        "confirmed": bool,
        "raw_value": float,          # smoothed sentiment score delta vs 7d baseline
        "threshold": 10.0,
        "grade": "B",
        "volume_check_passed": bool, # True if post volume ≥50% above 2h baseline
        "last_updated": float,
        "decay_factor": float,
    },
    "SHR_5_cme_basis_expanding": {
        "confirmed": bool,
        "raw_value": float,          # basis % (Deribit funding rate proxy)
        "threshold": 1.0,
        "grade": "B",
        "cross_validated": bool,     # True if SHR_1 also confirmed
        "last_updated": float,
        "decay_factor": float,
    },

    # ─── PATTERN 2: MINER CAPITULATION CASCADE ───────────────────────────
    "MCC_1_coinbase_to_exchange_3x": {
        "confirmed": bool,
        "raw_value": float,          # % of 7d average
        "threshold": 300.0,
        "grade": "B",
        "miner_wallet_validated": bool,
        "last_updated": float,
        "decay_factor": float,
    },
    "MCC_2_hashrate_declining_8pct": {
        "confirmed": bool,
        "raw_value": float,          # % decline 3d vs 14d avg
        "threshold": -8.0,
        "grade": "A",
        "last_updated": float,
        "decay_factor": float,
    },
    "MCC_3_difficulty_adj_negative_5pct": {
        "confirmed": bool,
        "raw_value": float,          # projected next difficulty adjustment %
        "threshold": -5.0,
        "grade": "A",
        "last_updated": float,
        "deterministic": True,       # no decay for deterministic signals
        "decay_factor": 1.0,
    },
    "MCC_4_miner_revenue_6mo_low": {
        "confirmed": bool,
        "raw_value": float,          # current revenue per EH/s in USD
        "threshold_type": "6mo_low",
        "grade": "B",
        "last_updated": float,
        "decay_factor": float,
    },
    "MCC_5_mempool_fees_soft": {
        "confirmed": bool,
        "raw_value": float,          # next-block fee in sat/vB
        "threshold": 5.0,
        "grade": "A",
        "last_updated": float,
        "decay_factor": float,
    },
    "MCC_CTX_wti_crude_up": {
        "confirmed": bool,
        "raw_value": float,
        "threshold": 5.0,
        "grade": "CTX",
        "is_context_only": True,
        "weight": 0.0,               # does not count toward threshold
        "last_updated": float,
        "decay_factor": float,
    },

    # ─── PATTERN 3: WHALE ACCUMULATION PRE-MOVE ──────────────────────────
    "WAP_1_whale_cluster_3_in_90min": {
        "confirmed": bool,
        "raw_value": int,            # count of qualifying whale movements in window
        "threshold": 3,
        "grade": "B",
        "exchange_filter_passed": bool,
        "non_exchange_destination_count": int,
        "last_updated": float,
        "decay_factor": float,
    },
    "WAP_2_exchange_reserve_declining_1pct": {
        "confirmed": bool,
        "raw_value": float,          # % change in exchange reserves over 24h
        "threshold": -1.0,
        "grade": "A",
        "consecutive_checks_passed": int,  # of 3 required
        "last_updated": float,
        "decay_factor": float,
    },
    "WAP_3_utxo_6_12mo_moving_2x": {
        "confirmed": bool,
        "raw_value": float,          # current / baseline ratio
        "threshold": 2.0,
        "grade": "A",
        "last_updated": float,
        "decay_factor": float,
    },
    "WAP_4_pcaf_anomaly_elevated": {
        "confirmed": bool,
        "raw_value": float,          # PCAF score 0–100
        "threshold": 40.0,
        "grade": "B",
        "formula_published": bool,   # False until pcaf_scorer.py formula is published
        "counting": bool,            # False until formula_published = True
        "last_updated": float,
        "decay_factor": float,
    },
    "WAP_5_large_unconfirmed_tx_3x": {
        "confirmed": bool,
        "raw_value": float,          # current / 4h average ratio
        "threshold": 3.0,
        "grade": "B",
        "last_updated": float,
        "decay_factor": float,
    },

    # ─── PATTERN 4: INSTITUTIONAL ENTRY SIGNAL ───────────────────────────
    "IES_1_custodian_wallet_inflow_150m": {
        "confirmed": bool,
        "raw_value": float,          # USD equivalent inflow in 6h
        "threshold": 150_000_000,
        "grade": "B",
        "is_proxy": True,            # flagged as proxy in UI
        "sub_windows_active": int,   # of 3 required sub-windows
        "last_updated": float,
        "decay_factor": float,
    },
    "IES_2_cme_basis_1_5pct": {
        "confirmed": bool,
        "raw_value": float,
        "threshold": 1.5,
        "grade": "B",
        "consecutive_hours_met": int,  # of 4 required
        "stablecoin_cross_validated": bool,
        "last_updated": float,
        "decay_factor": float,
    },
    "IES_3_stablecoin_minting_500m": {
        "confirmed": bool,
        "raw_value": float,          # USD minted in 6h window
        "threshold": 500_000_000,
        "grade": "A",
        "is_mandatory_for_critical": True,
        "last_updated": float,
        "decay_factor": float,
    },
    "IES_4_dormant_coins_stable": {
        "confirmed": bool,
        "raw_value": float,          # current CDD / 30d baseline ratio
        "threshold": 0.5,            # must be BELOW this (inverted)
        "threshold_type": "below",
        "grade": "A",
        "last_updated": float,
        "decay_factor": float,
    },
    "IES_5_spy_risk_on": {
        "confirmed": bool,
        "raw_value": float,
        "threshold": 1.0,
        "grade": "B",
        "onchain_cross_validated": bool,  # True if IES_1 or IES_3 also confirmed
        "last_updated": float,
        "decay_factor": float,
    },

    # ─── PATTERN 5: REGULATORY SHOCK PROPAGATION ─────────────────────────
    "RSP_1_regulatory_alert_4h": {
        "confirmed": bool,
        "alert_tier": str,           # "CRITICAL" or "WATCH"
        "alert_fired_at": float,     # timestamp
        "jurisdiction": str,         # for P2P cross-matching
        "grade": "A",
        "is_mandatory": True,
        "last_updated": float,
        "decay_factor": 1.0,         # no decay for event triggers
    },
    "RSP_2_multisource_news_regulatory": {
        "confirmed": bool,
        "raw_value": int,            # count of independent sources confirmed
        "threshold": 3,
        "grade": "B",
        "proxy_active": bool,        # True if using sentiment drop as proxy
        "sources_confirmed": list,   # list of source names
        "last_updated": float,
        "decay_factor": float,
    },
    "RSP_3_exchange_inflow_3x": {
        "confirmed": bool,
        "raw_value": float,
        "threshold": 3.0,
        "grade": "B",
        "internal_transfer_filtered": bool,
        "persistence_hours_met": float,  # of 2 required
        "last_updated": float,
        "decay_factor": float,
    },
    "RSP_4_coinjoin_volume_2x": {
        "confirmed": bool,
        "raw_value": float,          # current / 7d average ratio
        "threshold": 2.0,
        "grade": "B",
        "last_updated": float,
        "decay_factor": float,
    },
    "RSP_5_p2p_spike_200pct": {
        "confirmed": bool,
        "raw_value": float,          # % change from 7d avg
        "threshold": 200.0,
        "grade": "CTX",
        "weight": 0.5,               # half-signal
        "jurisdiction_matched": bool,
        "last_updated": float,
        "decay_factor": float,
    },

    # ─── PATTERN 6: LIQUIDITY STRESS CASCADE ─────────────────────────────
    "LSC_1_exchange_reserve_increasing_2pct": {
        "confirmed": bool,
        "raw_value": float,          # % increase over 24h
        "threshold": 2.0,
        "grade": "A",
        "consecutive_8h_checks": int,  # of 3 required
        "last_updated": float,
        "decay_factor": float,
    },
    "LSC_2_stablecoin_net_outflows_400m": {
        "confirmed": bool,
        "raw_value": float,          # net outflow USD in 8h
        "threshold": -400_000_000,   # negative = outflow
        "grade": "A",
        "last_updated": float,
        "decay_factor": float,
    },
    "LSC_3_mempool_fees_tightening_40svb": {
        "confirmed": bool,
        "raw_value": float,          # next-block fee in sat/vB
        "threshold": 40.0,
        "grade": "A",
        "sustained_hours": float,    # of 3 required
        "last_updated": float,
        "decay_factor": float,
    },
    "LSC_4_btc_exchange_inflows_2x": {
        "confirmed": bool,
        "raw_value": float,
        "threshold": 2.0,
        "grade": "B",
        "internal_transfer_filtered": bool,
        "lsc1_consistent": bool,     # directional consistency with LSC_1
        "last_updated": float,
        "decay_factor": float,
    },
    "LSC_5_vix_risk_off_20pct": {
        "confirmed": bool,
        "raw_value": float,
        "threshold": 20.0,
        "grade": "B",
        "last_updated": float,
        "decay_factor": float,
    },
}
```

### Signal Extraction Implementation Notes

1. **Every signal has a `last_updated` timestamp.** The evaluator checks this before using any signal value.
2. **Validation functions are called during extraction, not during pattern evaluation.** The `signals` dict already contains the result of `validate_not_internal_transfer()`, `validate_miner_wallet_cluster()`, `filter_exchange_controlled_addresses()`. The pattern evaluator trusts these results.
3. **Context signals (CTX)** are extracted identically to counting signals. Their `weight` field determines whether they count toward thresholds.
4. **WAP-4 (PCAF):** The `counting` field is `False` by default. It becomes `True` only after the PCAF formula is published and the `formula_published` flag is explicitly set to `True` in `convergence_config.yaml`.
5. **Signal dict is written to `SentinelState.convergence["last_signals"]`** at the end of each extraction pass.

---

## 5. MIXED-FREQUENCY STATE MACHINE

### The Core Problem

Signals update at radically different frequencies. Mempool fees update every ~1 minute. Hashrate updates every ~10 minutes (per block). Sentiment every 15–30 minutes. Custodian wallet movements may update once per hour. Difficulty adjustment is known days in advance. The engine must handle signals with age ranging from 60 seconds to 24+ hours without treating a 6-hour-old reading as equivalent to a 60-second-old reading.

### Signal Freshness Classification Table

| Signal Class | Examples | `decay_onset_age` | `max_valid_age` | Update Frequency |
|---|---|---|---|---|
| Mempool real-time | MCC-5 fees, LSC-3 fees, WAP-5 unconfirmed | 5 min | 15 min | ~1 min |
| On-chain per-block | MCC-2 hashrate, MCC-3 difficulty | 30 min | 2