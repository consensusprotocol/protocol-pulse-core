# CONVERGENCE DETECTION — CROSS-LLM AUDIT REPORT
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# Date: 2026-03-23
# Models: GPT-4o, Grok-3 (2 cycles each)
# Synthesized by: Claude Sonnet 4.6

---

## Q1 CONSENSUS: SIGNAL DESIGN

Both models evaluated all 25 signals across the 5 patterns. Verdicts are synthesized from both cycles, with disagreements resolved by weight of technical evidence. Grades are: **STRONG** / **ACCEPTABLE** / **WEAK** / **REPLACE**.

---

### PATTERN 1 — SAFE-HAVEN ROTATION

**Signal 1: BTC exchange net outflow > 2x 30-day average**
- **Grade: ACCEPTABLE**
- Both models rated this A/B-grade. Reliable in principle, but requires robust exchange wallet labeling to exclude internal reshuffling. Grok specifically flagged the need to cross-validate with exchange reserve ratio decline to confirm coins are genuinely leaving exchange custody rather than moving between internal wallets.
- **Fix required:** Add mandatory cross-validation gate: outflow only counts if exchange reserve ratio simultaneously declines by ≥0.5%. Implement `validate_not_internal_transfer()` check against known intra-exchange wallet clusters before signal is logged.

**Signal 2: Gold spot price +1.5% in 4h window**
- **Grade: REPLACE**
- Both models independently graded this C. Free API latency (metals-api.com), intraday volatility unrelated to BTC, and frequent false signal generation make this unreliable for a sub-6-hour detection window. GPT-4o called it "noisy." Grok called it C-grade explicitly. Cross-examination consensus confirmed replacement.
- **Fix:** Replace with **VIX spike >20% over 24h** (Yahoo Finance API, B-grade). VIX captures the risk-off equity stress environment that actually drives safe-haven BTC flows. If VIX is unavailable, use gold as a secondary fallback only, requiring 8h persistence rather than 4h.

**Signal 3: DXY declining >0.5% in 4h window**
- **Grade: REPLACE**
- Both models rated this C. Same latency and noise issues as gold. DXY frequently moves on non-BTC-related forex dynamics (Fed commentary, geopolitical events) generating constant false triggers. The 4h window is too short to filter genuine macro shifts from noise.
- **Fix:** Replace with **SPY/equity market risk-on confirmation: SPY >+0.8% sustained 4h** as a cross-asset confirmation that the rotation is macro-driven, not gold-specific. Alternatively, use DXY but extend persistence to 8h and require simultaneous VIX signal. Grok's VIX substitution is the stronger primary replacement.

**Signal 4: Sentiment score trending +15 points over 2h**
- **Grade: WEAK**
- Both models flagged this as noisy (GPT-4o explicitly, Grok as B-grade requiring volume-weighting). The +15 point threshold is arbitrary without specifying the baseline, the data source methodology, or minimum post volume. However, both models retained it rather than replacing it, distinguishing it from the gold/DXY C-grades.
- **Fix:** Require volume-weighted sentiment: score only counts if concurrent post volume is ≥50% above 2h baseline (filtering low-activity periods where small swings produce large percentage moves). Define explicit baseline as 7-day rolling average sentiment. Smooth with 30-minute exponential moving average before threshold check.

**Signal 5: CME futures basis expanding**
- **Grade: ACCEPTABLE**
- Both models rated this B-grade. The Deribit proxy is imperfect but functional. The concern is basis expansion can occur for reasons unrelated to institutional safe-haven rotation (e.g., leveraged long speculative positions). Workable for Phase 2 with caveats.
- **Fix:** Specify threshold: basis expanding >1.0% over 4h. Require cross-validation with at least one on-chain signal before counting toward pattern. Flag as B-grade in data dependency table.

---

### PATTERN 2 — MINER CAPITULATION CASCADE

**Signal 6: Coinbase-to-exchange transactions >300% of 7-day average**
- **Grade: WEAK**
- Both models rated this B-grade with significant caveats. The core concern is wallet labeling accuracy: miner addresses are imprecisely identified from public data, and many "coinbase" outputs flow through intermediate addresses before reaching exchanges. The 300% threshold could trigger on exchange internal consolidations.
- **Fix:** Cross-validate against tagged miner wallet clusters (e.g., F2Pool, AntPool known addresses from public blockchain explorers). Only count transactions from wallets confirmed as mining-entity-associated in the last 90 days. Implement `validate_miner_wallet_cluster()` before signal fires. Require 6h persistence.

**Signal 7: Hashrate 3-day average declining >8% vs 14-day average**
- **Grade: STRONG**
- Both models rated this A-grade. Directly computable from mempool.space API, low noise, well-documented. The dual-average comparison (3-day vs 14-day) is methodologically sound for distinguishing genuine decline from temporary variance.
- **No change required.** Confirmed as-is.

**Signal 8: Difficulty adjustment incoming >-5%**
- **Grade: STRONG**
- Both models rated this A-grade. Deterministic from blockchain data, computable with precision, no API quality issues. A negative adjustment of >5% is a strong objective indicator of sustained hash power reduction.
- **No change required.** Confirmed as-is.

**Signal 9: Miner revenue per EH/s at 6-month low**
- **Grade: ACCEPTABLE**
- Both models rated this B-grade. Computable from mempool.space fee data and hashrate estimates, but requires accurate long-window historical data and is sensitive to fee market spikes (which can temporarily inflate revenue masking underlying capitulation). Operationally reliable if the calculation window is correctly maintained.
- **Fix:** Ensure 6-month rolling window is stored in persistent state rather than recomputed on each evaluation. Cross-validate against mempool fee market signal to avoid false readings during fee spikes.

**Signal 10: Mempool fee market softening (<5 sat/vB for >2h)**
- **Grade: STRONG**
- Both models rated this A-grade. Direct from mempool.space, low latency, low noise. Sustained low-fee environments reliably indicate reduced transaction demand consistent with miner revenue pressure.
- **No change required.** Confirmed as-is.

**Missing signal (consensus addition):** Grok proposed **WTI crude oil +5% in 24h** as a mining cost pressure context signal. GPT-4o did not independently propose this but endorsed energy price context in cross-examination. Grade this as a **supplemental context signal** (does not count toward WATCH/CRITICAL thresholds but is displayed as supporting context in the UI). Include it as a "contextual indicator" field in the pattern state object, sourced from Yahoo Finance commodity feed.

---

### PATTERN 3 — WHALE ACCUMULATION PRE-MOVE

**Signal 11: 3+ whale addresses (>100 BTC clusters) moving within 90-minute window**
- **Grade: WEAK**
- Both models rated this B-grade with concerns about exchange reshuffling false positives. The 90-minute window is tight enough that legitimate exchange rebalancing operations could trigger this. Grok explicitly flagged "prone to false positives from exchange reshuffling."
- **Fix:** Exclude addresses identified as exchange-controlled in the known wallet registry. Require that at least 2 of the 3 whale movements are to non-exchange destinations (cold wallet clusters, OTC desk addresses, or unknown wallets). Implement `filter_exchange_controlled_addresses()` as a mandatory pre-check.

**Signal 12: Exchange reserve ratio declining >1% over 24h**
- **Grade: STRONG**
- Both models rated this A-grade. Long enough window to filter noise, reliable calculation from known wallet clusters, directly indicative of supply leaving exchange custody. The 24h window is appropriate.
- **No change required.** Confirmed as-is.

**Signal 13: UTXO age bands (6-12 months) moving above 2x baseline**
- **Grade: STRONG**
- Both models rated this A-grade. Computable from coin-days-destroyed metrics via mempool.space, reliable indicator of "older money" being activated. The 6-12 month band specifically targets whale-scale accumulation rather than recent buyer activity.
- **No change required.** Confirmed as-is.

**Signal 14: PCAF anomaly score elevated (>40/100)**
- **Grade: WEAK**
- Both models flagged this as vague. Grok rated it B-grade but noted it "lacks specificity—could be unrelated to accumulation." GPT-4o rated it reliable "if anomaly detection is accurate" — which is a circular condition that doesn't constitute a signal-level endorsement. The lack of a defined methodology for the PCAF score is the core problem.
- **Fix:** Define PCAF score computation explicitly in the spec: weight of (clustering coefficient of recent large transactions) + (deviation from typical address reuse patterns) + (cross-pattern address appearance). Publish the scoring formula in `/lib/pcaf_scorer.py` so the signal is auditable. Until defined, treat as supporting context only (non-counting toward WATCH/CRITICAL thresholds).

**Signal 15: 2+ Tier-1 pseudonymous accounts posting accumulation signals**
- **Grade: REPLACE**
- Both models independently graded this C. GPT-4o: "requires careful filtering and validation." Grok: "Noisy (C-grade), X scraper data is unreliable due to bots and spam." Cross-examination reinforced the consensus. Grok's proposed fix (follower count thresholds) was challenged by GPT-4o as insufficient against coordinated bot networks. Neither proposed fix is production-grade.
- **Fix:** Replace entirely with **large unconfirmed transaction volume: sum of unconfirmed transactions >100 BTC each exceeds 3x 4h average** as an OTC desk activity proxy (Grok's suggestion, endorsed by GPT-4o in cross-examination). This captures off-market accumulation signals via on-chain data without depending on social media reliability. Source: mempool.space unconfirmed transaction feed.

---

### PATTERN 4 — INSTITUTIONAL ENTRY SIGNAL

**Signal 16: ETF net inflow >$300M in 6h window**
- **Grade: REPLACE**
- Both models graded this C. Grok: "custodian wallet monitoring is incomplete and delayed; intraday data is often unavailable via free APIs." GPT-4o: "reliable if custodian wallet monitoring is accurate" — but that accuracy condition cannot be met with available free/semi-public data. This is a known technical debt item.
- **Fix:** Replace real-time ETF inflow monitoring with **custodian wallet inflow proxy: known BlackRock/Fidelity/Grayscale BTC custody wallet inflows >$150M equivalent in 6h**, sourced from mempool.space with labeled wallet addresses. This is less precise than direct ETF data but achievable with on-chain sources. Flag explicitly as a proxy in the UI display. Calibrate threshold downward to $150M to account for proxy imprecision.

**Signal 17: CME futures basis expanding >1.5%**
- **Grade: ACCEPTABLE**
- Both models rated this B-grade. Consistent assessment: Deribit proxy is imperfect but usable. The institutional entry interpretation (cash-and-carry trade setup) is valid when basis expansion persists.
- **Fix:** Require 4h persistence before counting. Cross-validate against stablecoin minting signal to confirm dry powder is available for institutional deployment.

**Signal 18: Stablecoin minting (USDT/USDC) >$500M in 6h**
- **Grade: STRONG**
- Both models rated this A-grade. Trackable via token APIs (mempool.space for USDT on Ethereum/Tron, Circle API for USDC), low noise, strong historical correlation with institutional buying pressure.
- **No change required.** Confirmed as-is.

**Signal 19: Dormant coins (>1yr) NOT moving**
- **Grade: STRONG**
- Both models rated this A-grade. Computable from coin-days-destroyed metrics. The absence of long-dormant supply activation during an accumulation period is a reliable confirmation that institutional buying is not being offset by long-term holder selling.
- **No change required.** The logic here is inverted (absence of an event = signal confirmation), which requires careful implementation: confirm this is explicitly implemented as `dormant_coin_movement < 0.5x_baseline` rather than a null check.

**Signal 20: SPY/equity markets up (risk-on)**
- **Grade: WEAK**
- Both models flagged this as noisy. GPT-4o: "requires confirmation with other macro indicators." Grok rated B-grade but noted equity moves "don't always correlate with BTC institutional entry." However, neither model recommended full replacement — it provides context for differentiating institutional entry from pure BTC-native flow.
- **Fix:** Tighten threshold to SPY >+1.0% sustained 4h (not just "up"). Require concurrent stablecoin minting signal to count. Downgrade this signal's weight in the confidence scoring formula — it should be a confirming signal, not a triggering signal.

---

### PATTERN 5 — REGULATORY SHOCK PROPAGATION

**Signal 21: Regulatory CRITICAL or WATCH alert fired in last 4h**
- **Grade: STRONG**
- Both models rated this A-grade. The internal Sentinel alert stream is a reliable first-party data source. The 4h window is appropriate for capturing the immediate post-announcement period.
- **No change required.** Confirmed as-is.

**Signal 22: Sentiment score dropped >25 points in <2h**
- **Grade: REPLACE**
- Both models rated this C-grade. GPT-4o: "requires smoothing." Grok: "unreliable and manipulable." The velocity threshold (25 points in 2h) is particularly dangerous — coordinated FUD campaigns or single viral posts can trigger this without any genuine regulatory event.
- **Fix:** Replace with **news source sentiment: structured feed from Reuters/AP/CoinDesk RSS with keyword match on regulatory terms, minimum 3 independent sources confirming negative framing within 2h**. This is lower velocity but higher precision. GPT-4o's NLP suggestion was challenged by Grok for resource overhead — the RSS multi-source approach is the achievable middle ground. Until implemented, use sentiment only as context display, not a counting signal.

**Signal 23: Exchange inflows spike >3x 30-day average**
- **Grade: ACCEPTABLE**
- Both models rated this B-grade. Reliable direction (people sending BTC to exchanges to sell during regulatory fear), but prone to noise from internal movements. The same wallet-labeling caveat from Pattern 1 applies.
- **Fix:** Apply same internal-transfer filter as Signal 1. Require 2h persistence (not instantaneous spike) to filter one-time large transactions from systemic inflow trends.

**Signal 24: P2P volume spike >200% in affected jurisdiction**
- **Grade: WEAK**
- Both models flagged this. Grok rated C-grade: "HodlHodl API is limited in coverage and prone to data gaps." GPT-4o rated it reliable "if P2P data is current" — which is the problematic condition. Jurisdiction-specific P2P monitoring is operationally difficult with free APIs.
- **Fix:** Retain but reframe as a **supporting context signal** rather than a primary counting signal. Source from HodlHodl public API + LocalBitcoins historical data where available. Weight at 0.5x in confidence scoring (half-signal). Require jurisdiction match with the regulatory alert that triggered Pattern 5 to avoid false cross-jurisdictional signals.

**Signal 25: Regulatory keywords trending in top-10 Bitcoin Twitter/X**
- **Grade: REPLACE**
- Both models rated this C-grade. Unanimous agreement: X scraper data is unreliable, bot-contaminated, and structurally manipulable. No debate required.
- **Fix:** Replace with **coinjoin volume spike: coinjoin transaction count >2x 7-day average over 4h**, sourced from mempool.space coinjoin detection. Privacy-seeking behavior accelerates reliably in response to genuine regulatory pressure, providing on-chain confirmation without social media dependency. Grok proposed this explicitly in Cycle 1; GPT-4o endorsed on-chain privacy signals in cross-examination.

---

### MISSING SIGNALS — CONSENSUS ADDITIONS

Both models, across both cycles, independently identified gaps. The following signals should be added to the spec:

1. **VIX spike >20% sustained 24h** — Macro stress indicator for Safe-Haven Rotation. Replaces gold/DXY. Source: Yahoo Finance. Grade: B.
2. **Large unconfirmed transaction volume >3x 4h average (>100 BTC each)** — OTC desk activity proxy for Whale Accumulation. Source: mempool.space. Grade: B.
3. **Coinjoin transaction count >2x 7-day average** — Privacy reaction signal for Regulatory Shock. Source: mempool.space. Grade: B.
4. **Retail momentum pattern (NEW Pattern 6)** — Both models agreed retail FOMO/FUD cycles are unaddressed. Full specification in Q7.

---

## Q2 CONSENSUS: FALSE POSITIVE GUARD RAILS

False positive elimination is the single most critical operational requirement for this system. Both models converged on this principle: **alerts must be rare, precise, and defensible to a sophisticated user at 3am.** The following guard rails are definitive.

---

### PATTERN 1 — SAFE-HAVEN ROTATION

**Minimum Confirmation Window:** 6 hours from first signal firing to alert emission.

**Signal Persistence Requirements:**
- VIX spike (replacing Gold/DXY): must sustain >20% for the full 6h window, checked at 30-minute intervals. Failure to sustain at any check resets the persistence counter.
- BTC exchange outflow: must persist across 3 consecutive hourly checks (not a single large transaction triggering the average).
- Sentiment: must sustain >+10 points above baseline (smoothed, see Q1 fix) for 4 of the 6 window hours.

**Cross-Validation Rules:**
- Cannot fire on macro signals alone. At least 1 on-chain signal (exchange outflow OR CME basis) must be active simultaneously.
- Exchange outflow must pass `validate_not_internal_transfer()` before counting.
- Minimum 3/5 signals required for WATCH. All 5 (or 4/5 with VIX as mandatory) for CRITICAL.

**Time-of-Day Adjustments:**
- **Asian session (00:00–08:00 UTC):** Increase outflow threshold to 2.5x (lower legitimate volume means smaller absolute flows can hit 2x average spuriously). Increase sentiment volume requirement by 30%.
- **US open (13:00–17:00 UTC):** Standard thresholds apply, but add a 30-minute delay before any CRITICAL alert to absorb opening volatility.
- **Weekend:** Extend macro signal persistence to 8h (lower institutional activity means weekend macro moves are more likely speculative than structural).

---

### PATTERN 2 — MINER CAPITULATION CASCADE

**Minimum Confirmation Window:** 24 hours. GPT-4o proposed this in Cycle 2 and Grok explicitly endorsed it in cross-examination as the correct window for a slow-moving systemic event.

**Signal Persistence Requirements:**
- Hashrate decline (3-day vs 14-day): must show continued degradation at each 6h check during the 24h window. A single reversal check does not invalidate, but two consecutive non-declining checks reset the counter.
- Difficulty adjustment: deterministic — counts once confirmed from blockchain data. Does not require persistence.
- Miner revenue per EH/s: must remain at 6-month low for 12 of 24 hours (not required continuous — accommodates intraday fee spikes).
- Mempool fee softening: must sustain <5 sat/vB for >4h cumulative during the evaluation window.

**Cross-Validation Rules:**
- Coinbase-to-exchange flows must pass `validate_miner_wallet_cluster()`. Only tagged miner entity wallets count.
- Hashrate decline and difficulty adjustment must both fire before CRITICAL is possible (they are the two anchor signals — neither can be absent at CRITICAL threshold).
- If miner flows appear without hashrate decline, suppress the pattern entirely — this indicates exchange reshuffling, not capitulation.

**Time-of-Day Adjustments:**
- Minimal — miner capitulation is a multi-day process. Time-of-day noise is less relevant at 24h windows. However: **exclude any single-hour inflow spike from the coinbase-to-exchange calculation** that occurs during known exchange maintenance windows (document these per major exchange).

---

### PATTERN 3 — WHALE ACCUMULATION PRE-MOVE

**Minimum Confirmation Window:** 12 hours from first whale movement signal.

**Signal Persistence Requirements:**
- Whale movements: require 3+ qualifying movements within any 90-minute window that occurs during the 12h evaluation period. A single cluster of qualifying movements initiates the WATCH state; a second cluster within 12h elevates to CRITICAL consideration.
- Exchange reserve ratio: must show sustained decline (not just a single large withdrawal) — require 3 consecutive 4h checks showing continued decline.
- UTXO age bands: must remain elevated for 8 of 12 evaluation hours.

**Cross-Validation Rules:**
- Price stability check: if BTC price has moved >4% in the last 4h, suppress the whale accumulation pattern — this indicates the "pre-move" has already occurred and the pattern is stale.
- Whale movements must pass `filter_exchange_controlled_addresses()`. Minimum 2 of 3 qualifying movements must terminate at non-exchange destinations.
- PCAF score (once properly defined per Q1 fix): required as a cross-validation signal, not a primary counting signal, until the scoring formula is published and validated.

**Time-of-Day Adjustments:**
- **OTC hours (16:00–20:00 UTC, US business day):** Lower the whale movement threshold to 2+ movements (instead of 3+) — legitimate institutional OTC activity is highest during this window and the reduced threshold is appropriate.
- **Asian session:** Increase whale movement threshold to 4+ movements — lower overall transaction volume makes 3 large movements more likely to be noise.

---

### PATTERN 4 — INSTITUTIONAL ENTRY SIGNAL

**Minimum Confirmation Window:** 12 hours.

**Signal Persistence Requirements:**
- Custodian wallet inflows (ETF proxy): must show continued inflow activity across at least 3 of the 6 two-hour sub-windows in the 12h evaluation period (not a single large transaction).
- CME futures basis: must sustain >1.5% for 4 consecutive hours before counting.
- Stablecoin minting: must occur as a single event or sustained minting >$500M total in the 12h window (not the 6h sub-window for persistence purposes, though the 6h threshold for initial trigger is retained).
- Dormant coins NOT moving: confirm absence of coin-days-destroyed spike throughout the 12h window.

**Cross-Validation Rules:**
- At least 2 macro signals must fire before institutional entry CRITICAL is possible (protecting against single-signal false positives from large one-time transactions).
- Stablecoin minting is a mandatory confirming signal for CRITICAL — institutional entry without visible stablecoin dry powder is suspect.
- SPY/equity signal counts only if concurrent with at least one on-chain signal.

**Time-of-Day Adjustments:**
- **US market closed (21:00–13:00 UTC):** ETF proxy signals are suppressed — institutional ETF activity cannot occur outside US market hours. Custodian wallet movements outside this window should be flagged as potentially anomalous, not routine.
- **US open first 30 minutes (13:30–14:00 UTC):** Suppress CRITICAL alerts — opening volatility produces spurious signals. Allow WATCH state only.

---

### PATTERN 5 — REGULATORY SHOCK PROPAGATION

**Minimum Confirmation Window:** 4 hours (shorter than other patterns — regulatory events are inherently time-sensitive and a 12h window would miss the actionable period).

**Signal Persistence Requirements:**
- Regulatory alert: counts immediately, but must remain in CRITICAL/WATCH state (not auto-resolved) throughout the evaluation window.
- Exchange inflows: must sustain >2x 30-day average (relaxed from 3x spike) for 2h of the 4h window to confirm systemic fear rather than a single large transaction.
- Multi-source news sentiment (replacing raw sentiment score): requires 3+ independent sources within the 4h window.
- Coinjoin volume (replacing social trending): must sustain >2x average for the majority of the 4h window.
- P2P volume (half-signal): counted at 0.5 weight.

**Cross-Validation Rules:**
- Regulatory alert is mandatory — pattern cannot fire without it. This prevents exchange inflow spikes from spuriously triggering the regulatory pattern.
- Jurisdiction match required: P2P volume spike must be in the same jurisdiction as the regulatory alert. Cross-jurisdictional signals are logged but do not count.
- If price has already dropped >10% before pattern evaluation, flag as "LATE DETECTION" — the event has already propagated and the alert is informational rather than actionable.

**Time-of-Day Adjustments:**
- Regulatory announcements often occur at market open or during business hours in the relevant jurisdiction. Implement jurisdiction-aware session detection: a US regulatory alert during US business hours (13:00–21:00 UTC) requires shorter persistence before firing because the market response is faster. An Asian regulatory alert outside Asian hours (01:00–09:00 UTC) requires full 4h persistence.

---

## Q3 CONSENSUS: DATA DEPENDENCY GRADES

Both models used consistent grading criteria. Final grades represent the consensus across all four cycles (two per model). C-grade replacements are definitive.

| # | Signal | Pattern | GPT-4o Grade | Grok Grade | **FINAL GRADE** | Replacement (if C) |
|---|--------|---------|-------------|-----------|-----------------|-------------------|
| 1 | BTC exchange net outflow >2x 30-day avg | Safe-Haven | A | A | **A** | — |
| 2 | Gold spot price +1.5% in 4h | Safe-Haven | B | C | **C** | VIX spike >20% sustained 24h (Yahoo Finance) |
| 3 | DXY declining >0.5% in 4h | Safe-Haven | B | C | **C** | SPY >+1.0% sustained 4h as risk-on confirmation; secondary to VIX |
| 4 | Sentiment score trending +15 pts over 2h | Safe-Haven | B | B | **B** | No replacement — apply volume-weighting and 7-day rolling baseline |
| 5 | CME futures basis expanding | Safe-Haven | B | B | **B** | No replacement — Deribit proxy with 4h persistence |
| 6 | Coinbase-to-exchange txs >300% of 7-day avg | Miner Cap | B | B | **B** | No replacement — apply miner wallet cluster validation |
| 7 | Hashrate 3-day avg declining >8% vs 14-day | Miner Cap | A | A | **A** | — |
| 8 | Difficulty adjustment incoming >-5% | Miner Cap | A | A | **A** | — |
| 9 | Miner revenue per EH/s at 6-month low | Miner Cap | B | B | **B** | No replacement — requires persistent 6-month state storage |
| 10 | Mempool fee market softening <5 sat/vB | Miner Cap | A | A | **A** | — |
| 11 | 3+ whale addresses moving in 90-min window | Whale Acc | B | B | **B** | No replacement — apply exchange address filter |
| 12 | Exchange reserve ratio declining >1% over 24h | Whale Acc | A | A | **A** | — |
| 13 | UTXO age bands (6-12mo) >2x baseline | Whale Acc | A | A | **A** | — |
| 14 | PCAF anomaly score elevated >40/100 | Whale Acc | B | B | **B** | No replacement — requires formula publication before production use |
| 15 | 2+ Tier-1 pseudonymous accounts posting signals | Whale Acc | C | C | **C** | Large unconfirmed tx volume >3x 4h average (>100 BTC each) via mempool.space |
| 16 | ETF net inflow >$300M in 6h | Institutional | C | C | **C** | Custodian wallet inflow proxy >$150M in 6h (known BlackRock/Fidelity/Grayscale wallets) |
| 17 | CME futures basis expanding >1.5% | Institutional | B | B | **B** | No replacement — requires 4h persistence and stablecoin cross-validation |
| 18 | Stablecoin minting >$500M in 6h | Institutional | A | A | **A** | — |
| 19 | Dormant coins (>1yr) NOT moving | Institutional | A | A | **A** | — |
| 20 | SPY/equity markets up (risk-on) | Institutional | B | B | **B** | No replacement — tighten to >+1.0% sustained 4h, downweight in confidence formula |
| 21 | Regulatory CRITICAL/WATCH alert in last 4h | Reg Shock | A | A | **A** | — |
| 22 | Sentiment score dropped >25 pts in <2h | Reg Shock | C | C | **C** | Multi-source RSS: 3+ independent news sources (Reuters/AP/CoinDesk) with regulatory keyword match within 2h |
| 23 | Exchange inflows spike >3x 30-day avg | Reg Shock | B | B | **B** | No replacement — apply 2h persistence and internal-transfer filter |
| 24 | P2P volume spike >200% in affected jurisdiction | Reg Shock | B | C | **C\*** | Retain as 0.5-weight supporting signal. Not a counting signal. Source HodlHodl + jurisdiction matching |
| 25 | Regulatory keywords trending top-10 BTC Twitter | Reg Shock | C | C | **C** | Coinjoin transaction count >2x 7-day average over 4h (mempool.space) |

**Note on Signal 24:** GPT-4o rated B, Grok rated C. Tiebreaker: the signal is retained but demoted to a supporting context indicator (0.5 weight) rather than a full counting signal. This honors GPT-4o's assessment that P2P data has value while respecting Grok's concern about coverage gaps.

**Summary by Grade:**
- **A-Grade (8 signals):** #1, #7, #8, #10, #12, #13, #18, #19, #21
- **B-Grade (11 signals):** #4, #5, #6, #9, #11, #14, #17, #20, #23, and new additions #VIX, #custodian proxy
- **C-Grade replaced (6 signals):** #2→VIX, #3→SPY, #15→OTC proxy, #16→custodian wallet proxy, #22→multi-source RSS, #25→coinjoin volume
- **C-Grade demoted (1 signal):** #24→0.5-weight supporting signal

---

## Q4 DECISION: TRANSFORMER VS RULE-BASED

**FINAL DECISION: Rule-based system for Phase 2. This is binding.**

Both models independently reached this conclusion. GPT-4o in Cycle 1 stated: "A rule-based approach is more suitable for Phase 2." Grok in Cycle 2 stated: "The definitive decision for Phase 2 is to adopt a rule-based system." The cross-examination produced zero disagreement on this question. There is no ambiguity.

**Binding rationale (consolidated from both models, both cycles):**

**1. Data quality makes ML non-viable.** The 25 signals reviewed above include 8 signals at C-grade requiring replacement, 11 at B-grade with significant noise caveats, and only 8 at A-grade. Training a transformer model on this data would produce a system that learns to amplify the noise patterns in the training data. Overfitting risk is unacceptably high when the majority of your signal corpus has quality problems. This was GPT-4o's core argument in Cycle 1 and Grok's in Cycle 2.

**2. Labeled training data does not exist.** A transformer-based convergence detector requires a labeled dataset of historical convergence events with timestamps, signal states at detection time, and outcome labels. Protocol Pulse does not have this dataset at Phase 2 inception. Building it requires running the rule-based system first to generate labeled observations. ML is therefore architecturally downstream of the rule-based system, not an alternative to it.

**3. Debuggability is a product requirement, not a preference.** High-stakes users who are woken up by a CRITICAL alert need to be able to understand why the alert fired. A rule engine produces a readable audit trail: "Pattern fired because signals #7, #8, #9, #10 all confirmed within 24h window." A transformer produces an embedding. The rule engine is the only option that satisfies the product's implicit transparency contract with its users.

**4. Phase 2 is delivery-scoped.** Adding ML dependencies introduces training infrastructure, model versioning, inference latency, and model drift monitoring — none of which are in the Phase 2 scope. The rule-based system can be built, tested, and shipped within scope. ML cannot.

**Implementation Directive:**
Implement the Convergence Detection engine as a modular Python rule engine:
- Each pattern is a class inheriting from `BasePattern` with `evaluate()`, `check_persistence()`, and `validate_cross_signals()` methods.
- Signal thresholds are loaded from `convergence_config.yaml` (not hardcoded) to enable tuning without code deploys.
- Each evaluation produces a structured `PatternState` object with: `pattern_id`, `state` (IDLE/FORMING/WATCH/CRITICAL/RESOLVED), `confirmed_signals[]`, `confidence_score` (rule-based, not probabilistic), `first_signal_ts`, `last_update_ts`, `guard_rail_audit_log[]`.
- All guard rail checks are logged to the audit log regardless of whether they pass or fail, providing a complete decision trail.

**Future phases:** Once 6+ months of labeled observations are generated by the rule system, evaluate a gradient-boosted tree ensemble (not a transformer — too heavy) for signal weight optimization. A transformer may be appropriate for the NLP components only (news sentiment classification) in Phase 3+, where curated training data can be assembled.

---

## Q5 CONSENSUS: MIXED-FREQUENCY STATE MACHINE

The fundamental challenge: signals update at radically different rates. Mempool fees update every minute. Hashrate updates every ~10 minutes (per block). Sentiment updates every 15-30 minutes depending on scraper frequency. ETF proxy (custodian wallets) may update only once per hour. Difficulty adjustment is known days in advance. This means the evaluation engine must handle signals with age ranging from 60 seconds to 24+ hours simultaneously without treating a 6-hour-old sentiment reading as equivalent to a 60-second-old mempool reading.

**Definitive Evaluation Logic:**

### Signal Freshness Classification

Every signal has a `max_valid_age` and a `decay_onset_age` defined at the signal level:

| Signal Type | `decay_onset_age` | `max_valid_age` | Update Source |
|-------------|-------------------|-----------------|---------------|
| Mempool fees | 5 min | 15 min | mempool.space (real-time) |
| Hashrate | 30 min | 2h | mempool.space (per-block) |
| Exchange flows | 15 min | 1h | on-chain (block-confirmed) |
| UTXO age bands | 30 min | 3h | mempool.space |
| Stablecoin minting | 10 min | 1h | token API |
| VIX / SPY | 5 min (market hours) | 1h | Yahoo Finance |
| Sentiment score | 15 min | 2h | scraper |
| CME/Deribit basis | 10 min | 1h | exchange API |
| Regulatory alert | N/A (event-triggered) | 4h (pattern window) | Sentinel stream |
| Difficulty adjustment | N/A (deterministic) | Until next adjustment | blockchain |

### Staleness Decay Function

When signal age exceeds `decay_onset_age`, its contribution to the confidence score is multiplied by a decay factor:

```
decay_factor = max(0.0, 1.0 - ((signal_age - decay_onset_age) / (max_valid_age - decay_onset_age)))
```

This produces a linear decay from 1.0 (at `decay_onset_age`) to 0.0 (at `max_valid_age`). When `decay_factor` reaches 0.0, the signal is considered STALE and does **not count toward the WATCH/CRITICAL threshold integer count**, but is retained in the state object as a "previously confirmed, now stale" indicator for the UI.

**Critical implementation note:** The WATCH/CRITICAL threshold counts (e.g., "3/5 signals confirmed") must use **non-decayed signal counts** — a signal either passes its threshold check or it doesn't. The decay function applies only to the **confidence percentage** displayed in the UI, not to the binary signal count. Mixing these would create a confusing system where the threshold count and the confidence percentage disagree in ways users cannot interpret.

### Weighting Formula for Confidence Score

The confidence score (0-100%, displayed in UI) is calculated as:

```
confidence = (Σ (signal_weight_i × decay_factor_i × threshold_met_i) / Σ signal_weight_i) × 100
```

Where `signal_weight_i` is the normalized weight for each signal by grade:
- A-grade signals: weight = 1.0
- B-grade signals: weight = 0.7
- C-grade signals (if retained as supporting): weight = 0.3 (half-signals use 0.5 × 0.3 = 0.15)

And `threshold_met_i` is binary (1 if signal threshold is currently met, 0 if not).

### State Transition Logic

The evaluation engine runs on a **60-second main evaluation loop** with the following logic:

```
IDLE → FORMING:    1 signal confirmed (any A-grade signal)
FORMING → WATCH:   threshold count met (e.g., 3/5) AND minimum confirmation window not yet elapsed
WATCH → CRITICAL:  threshold count met for CRITICAL (e.g., 4/5) AND persistence requirement met
CRITICAL → WATCH:  signal count drops below CRITICAL threshold (signal goes stale or threshold no longer met)
WATCH → FORMING:   signal count drops below WATCH threshold
FORMING → IDLE:    all signals return to below-threshold
ANY → RESOLVED:    manual resolution OR automatic resolution criteria met (pattern-specific)
```

**State cannot skip levels** — a pattern must pass through FORMING and WATCH before reaching CRITICAL. This prevents instantaneous CRITICAL alerts from single rapid signal cascades (a key false positive source).

### Staleness Warning System

When any counting signal has `decay_factor < 0.5` (halfway to full staleness), the UI displays a staleness warning on that specific signal indicator. When a previously CRITICAL pattern has signals going stale such that the CRITICAL threshold is no longer met, it **auto-demotes to WATCH** rather than going directly to RESOLVED. This prevents the jarring UI experience of a pattern disappearing immediately when one signal ages out.

---

## Q6 CONSENSUS: FRONTEND PANEL SPEC

Both models produced frontend proposals. GPT-4o provided more complete state definitions. Grok provided architectural context. The following spec synthesizes both, with Claude resolving gaps.

---

### PANEL IDENTITY AND LOCATION

- Panel ID: `convergence-matrix-panel`
- Location: Dedicated section in Protocol Pulse Intelligence Terminal, collapsible to summary strip
- Persistent: always visible when active events exist, even when user is viewing other panels
- Breakpoint behavior: Full panel on desktop (≥1280px), compact strip view on tablet (768–1279px), notification-only on mobile (<768px)

---

### STATE SPECIFICATIONS

**STATE 0: EMPTY**
- Background: `#0a0a0f` (terminal dark)
- Primary text: `CONVERGENCE MATRIX — NO ACTIVE EVENTS` in `#4a4a6a` (muted)
- Secondary text: `All 5 patterns evaluating · System operational` in `#2a2a4a`
- No icons, no borders, minimal visual weight
- System health indicator: 5 small green dots (one per pattern) showing evaluation is running
- This state must never feel alarming — it is the default stable state

**STATE 1: FORMING**
- Background: `#0d0d18` (slightly elevated from empty)
- Left border: 3px solid `#3a3a5a` (muted purple)
- Pattern name in `#8080a0` with "FORMING" badge in `#4a4a6a`
- Shows: pattern name, which signals are confirmed (grayed), which signals are pending (darker gray)
- Confidence percentage shown but in muted color
- No audio or push notification at this state
- Visual metaphor: quiet, watchful

**STATE 2: WATCH**
- Background: `#12120a` (warm dark)
- Left border: 3px solid `#8a8a00` (yellow/amber)
- Pattern name in `#cccc44` with pulsing "WATCH" badge (2-second pulse animation, subtle)
- Shows: pattern name, confirmed signals (lit), pending signals (dim), confidence %, time since first signal
- Guard rail status: small indicator showing persistence window progress (e.g., "4h / 6h required")
- Audio: single soft chime on state entry (can be disabled)
- Push notification: optional, off by default
- The "screenshot moment" for WATCH: a clean, information-dense card with amber left accent, showing exactly which signals fired and how long until CRITICAL is possible

**STATE 3: CRITICAL**
- Background: `#150a0a` (deep red-dark)
- Left border: 4px solid `#ff3333` with outer glow pulse (1-second cycle)
- Pattern name in `#ff6666` with FLASHING "CRITICAL" badge (0.5-second flash)
- Shows: pattern name, ALL confirmed signals (fully lit with checkmarks), confidence % in large type, escalation countdown or "SUSTAINED Xh", time since first signal
- Signal breakdown: each confirmed signal shown with its data value and threshold (e.g., "Hashrate ↓11.2% vs 14-day avg · threshold: 8%")
- Audio: distinct alert tone on state entry (louder than WATCH chime)
- Push notification: ON by default, requires explicit opt-out
- The "screenshot moment" for CRITICAL: a red-bordered card that is unmissable, with every confirmed signal visible at a glance and the pattern name as the largest text element. No ambiguity about what is happening.

**STATE 4: RESOLVED**
- Background: `#0a150a` (green-dark)
- Left border: 3px solid `#44aa44`
- Pattern name in `#88cc88` with "RESOLVED" badge
- Shows: pattern name, resolution outcome (auto-resolved/manual), peak confidence reached, duration from WATCH to RESOLVED, which signals led the resolution
- Fades to empty state after 30 minutes unless user has pinned it
- Kept in history log permanently

---

### INTERACTION MODEL

- **Clicking any non-empty state card:** expands inline to show full signal breakdown panel with individual signal values, thresholds, decay status, guard rail audit log, and historical context (last 5 times this pattern fired)
- **Right-clicking (desktop) / long-press (mobile):** context menu with options: "Silence for 1h," "Pin this event," "View full history," "Export signal state as JSON"
- **Multi-pattern simultaneous:** if multiple patterns are active, stack vertically in order: CRITICAL first, then WATCH, then FORMING. Maximum 5 cards visible simultaneously (one per pattern by definition).
- **Summary strip (tablet):** shows only state color, pattern name initial, and confidence %. Tap to expand.

---

### TYPOGRAPHY AND VISUAL CONSTANTS

- Font: Monospace throughout (JetBrains Mono or system monospace fallback)
- Confidence percentage: always shown as integer (never decimal) to convey precision without false specificity
- Timestamps: always UTC, always explicit (never relative like "5 minutes ago" — use "14:23 UTC")
- Signal checkmarks: ✓ for confirmed, ○ for pending, ✗ for stale
- Pattern name is ALWAYS the dominant visual element — the user must know which pattern fired before anything else

---

## Q7 WINNER: 6TH PATTERN

### Evaluation of Proposals

**GPT-4o's Proposal — "Liquidity Crunch Signal":**
Signals: Exchange reserve ratio increasing >2%/24h, Stablecoin outflows >$500M/6h, Interest rates rising >0.5%/24h, Negative sentiment spike >20 pts/2h, Mempool fee tightening >50 sat/vB for >2h.
Strengths: Strong on-chain anchoring (exchange reserves, stablecoin outflows, mempool), captures a genuine and important market dynamic (liquidity squeeze), WATCH/CRITICAL thresholds are well-calibrated.
Weaknesses: Interest rate signal is low-frequency, delayed via free APIs, and often already priced in by the time it's detectable. Sentiment spike retains the same noise problems identified in Pattern 5 Signal 22.

**Grok's Proposal — "Market Liquidity Stress Signal":**
Signals: Exchange reserve ratio increasing >2%/24h, Stablecoin outflows >$500M/6h, Mempool fee tightening >50 sat/vB for >3h (extended persistence), BTC exchange inflows >3x 30-day average over 12h, VIX spike >20%/24h.
Strengths: Drops the noisy sentiment signal, replaces interest rates with VIX (superior stress proxy), extends mempool fee persistence to 3h (reduces noise), adds exchange inflows as a selling pressure cross-validator, uses all-reliable sources.
Weaknesses: The BTC exchange inflows signal duplicates Pattern 5's exchange inflow signal, creating potential double-counting if both patterns are simultaneously active. The 12h window for exchange inflows is long relative to the other signals' 24h and 6h windows, creating an asymmetric evaluation window.

**Winner: Grok's signal set is stronger.** The replacement of interest rates with VIX is the decisive improvement — it eliminates the most brittle signal in GPT-4o's proposal without losing macro context. However, the double-counting risk and evaluation window asymmetry require correction.

---

### SYNTHESIZED 6TH PATTERN — "LIQUIDITY STRESS CASCADE"

**Rationale for name:** "Liquidity Crunch" (GPT-4o) is accurate but generic. "Market Liquidity Stress Signal" (Grok) is descriptive but verbose. "Liquidity Stress Cascade" captures the sequential, cascading nature of liquidity events in crypto markets where stablecoin outflows → reserve ratio increases → mempool congestion → selling pressure form a detectable chain.

**Signal Set:**

| # | Signal | Source | Grade | Threshold |
|---|--------|---------|-------|-----------|
| LSC-1 | Exchange reserve ratio increasing | mempool.space wallet data | A | >2% over 24h |
| LSC-2 | Stablecoin net outflows (USDT+USDC combined) | Token APIs | A | >$400M in 8h (adjusted from 6h to reduce noise) |
| LSC-3 | Mempool fee market tightening | mempool.space | A | Next-block fee >40 sat/vB sustained 3h (lowered from 50, extended from 2h) |
| LSC-4 | BTC exchange inflows rising | On-chain | B | >2x 30-day average over 6h (adjusted from 3x/12h — tightened for this pattern) |
| LSC-5 | VIX spike (risk-off macro indicator) | Yahoo Finance | B | >20% over 