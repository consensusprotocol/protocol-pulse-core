# CONSENSUS REPORT — INTELLIGENCE-TERMINAL — CYCLE 1
Generated: 2026-03-26 01:06
Models: gpt4o, grok, gemini

---

## SCORES

*Note: No model provided explicit numerical scores. Scores below are synthesized from priority ratings, depth of analysis, and confidence of recommendations across each model's Q1–Q6 responses.*

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Competitive Gap Analysis (Q1) | 9/10 | 7/10 | 8/10 | **8/10** |
| Cross-Signal Alpha (Q2) | 9/10 | 7/10 | 9/10 | **8.5/10** |
| Visual Innovation (Q3) | 9/10 | 6/10 | 8/10 | **7.5/10** |
| ML Model Recommendations (Q4) | N/A | 6/10 | 7/10 | **6.5/10** |
| $5K/mo Feature (Q5) | N/A | 8/10 | N/A | **8/10** |
| Design Competition (Q6) | N/A | 6/10 | N/A | **6/10** |
| Existing Foundation Quality | 9/10 | 7/10 | 8/10 | **8/10** |
| **Overall Product Readiness** | **8/10** | **6.5/10** | **7.5/10** | **7.3/10** |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Raw Data Is Not Being Synthesized Into Proprietary Indices
**What it is:** All three models independently identified that the dashboard aggregates raw data (hashrate, exchange flows, KOL sentiment, etc.) but fails to synthesize these into named, branded, competitor-grade metrics. The data pipeline is excellent; the analytical output layer is the gap.

**Files affected:** `sovereign_context_engine.py`, `intelligence_page.html`, `world_state.json`

**What to change:**
- Create computed properties in `sovereign_context_engine.py` that derive composite indices from existing data streams before writing to `world_state.json`
- Three specific indices are unanimously demanded:
  1. **Miner Conviction / Hashrate Sentiment Index** — All three models flagged hashrate alone as insufficient; it must be normalized against price action and rolling averages (Gemini's "Miner Conviction Index" is the most rigorous formula)
  2. **Exchange Pressure / Whale Flow Pressure** — Combine `exchange_flow` strings with `whale_alerts` directional data into a discrete scored metric (Gemini: -2 to +2 scale; Grok: "Whale Flow Pressure" label)
  3. **Social-to-Market Divergence** — KOL sentiment vs. price action delta as a named indicator

---

### U2 — Pattern Detection in `detect_patterns()` Is Underpowered
**What it is:** All three models reviewed the existing `detect_patterns()` function and unanimously concluded it needs additional cross-signal patterns. It currently handles single-domain signals but lacks multi-domain convergence alerts.

**Files affected:** `sovereign_context_engine.py` → `detect_patterns()` function

**What to change:**
- Add at minimum 4 new named alert types (all three models proposed overlapping sets):
  - `ACCUMULATION_STEALTH` — Hashrate rising + Exchange outflows + Fear & Greed < 30
  - `CAPITULATION_SIGNAL` — Whale alerts (high volume) + Exchange inflows + Fear & Greed < 15
  - `NARRATIVE_DIVERGENCE` — KOL sentiment bullish + Article/narrative sentiment bearish + Polymarket divergence
  - `SMART_MONEY_VS_RETAIL` — On-chain strength signals contradicting social/sentiment signals
- Each alert must carry a severity level (`CRITICAL`, `HIGH`, `MEDIUM`) and a human-readable explanation string

---

### U3 — The Radar/Multi-Dimensional Visual Is the Breakout Feature
**What it is:** All three models independently converged on a radial/radar chart concept as the highest-impact visual innovation. Grok calls it "Signal Convergence Radar." Gemini calls it "Sovereign Context Sonar." GPT-4o calls it a "Market Sentiment Heatmap" (radial variant implied). The convergence on this concept across three independent models is the strongest signal in this entire audit.

**Files affected:** `intelligence_page.html`, new `signal_radar.js` or D3 component

**What to change:**
- Build a radar chart with 5–8 axes representing normalized, orthogonal market dimensions:
  - On-Chain Strength, Retail Sentiment, Media Narrative, Market Conviction, Network Congestion, Price Momentum
- Each axis must be a normalized 0–100 score derived from composite sub-signals
- Include a "ghost" overlay of the 24h-ago shape so analysts can see character evolution at a glance
- Color the polygon by overall market state (red/gold/green)
- This is the single feature no competitor offers in this form

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Polymarket Data Is Underutilized as a Leading Indicator
**Models:** Gemini + Grok (GPT-4o mentioned but less specifically)

**What it is:** Polymarket odds represent capital-weighted conviction and historically lead sentiment indicators by 1–3 days. Currently it appears as a raw data point rather than being used as an alpha-generating leading signal.

**Files affected:** `sovereign_context_engine.py`, `world_state.json`

**What to change:**
- Add a `polymarket_sentiment_shift` detector: flag when `polymarket.macro_sentiment` flips >20 points within 48 hours *before* a corresponding shift in `fear_greed.value`
- Surface this as a "LEADING INDICATOR ALERT" with timestamp delta showing how far ahead of fear/greed it is
- Create a "Polymarket Front-Run" pattern in `detect_patterns()`: rapid Polymarket flip + lagging F&G = high-conviction signal

**Assessment:** Implement. This is genuinely novel alpha and requires minimal new data infrastructure.

---

### M2 — Lightning Network Data Is Decorative, Not Analytical
**Models:** Gemini + Grok

**What it is:** Both models flagged that Lightning capacity and channel counts are displayed but not used in any composite signal. Lightning data is fundamentally different from other signals—it's a long-term adoption thesis indicator, not a short-term price signal.

**Files affected:** `sovereign_context_engine.py`, `intelligence_page.html`

**What to change:**
- Create a "Lightning Adoption Inflection" pattern: `lightning.capacity_btc` and `lightning.channels` both > 2-sigma above 90-day moving average AND mempool unconfirmed count persistently elevated
- Label this explicitly as a **long-term thesis signal** (not a short-term trade signal) in the UI — critical distinction that professional analysts will respect
- Add a secondary "L2 Adoption Surge" alert: mempool fees > 50 sat/vB + Lightning capacity growing = on-chain congestion driving Layer 2 demand

**Assessment:** Implement. Reframing Lightning data as a thesis-confirmation signal rather than a price signal is both intellectually honest and analytically differentiated.

---

### M3 — Mempool Fee Data Needs Historical Context and Percentile Scoring
**Models:** GPT-4o + Gemini (Grok implied)

**What it is:** Raw mempool fees in sat/vB are only meaningful in context. 50 sat/vB could be extreme in a quiet market or normal in a congested one. No percentile or historical context is currently surfaced.

**Files affected:** `sovereign_context_engine.py`, `world_state.json`, `intelligence_page.html`

**What to change:**
- Store a rolling 30-day history of mempool fee highs
- Compute and expose `mempool.fee_percentile_30d` (0–100) in `world_state.json`
- Use this percentile in the "Coiled Spring" volatility pattern (Gemini) and surface it in the UI alongside the raw sat/vB figure
- Display format: "42 sat/vB (78th percentile / 30d)"

**Assessment:** Implement. Low effort, high analytical credibility.

---

### M4 — No Backtesting or Historical Validation Framework Exists
**Models:** GPT-4o + Grok

**What it is:** The cross-signal patterns currently have no historical validation. Sophisticated users (hedge funds) will immediately ask "how has this signal performed historically?" and the answer must not be silence.

**Files affected:** New file `backtest_engine.py`

**What to change:**
- Build a lightweight backtesting module that can replay historical `world_state.json` snapshots against the pattern detection logic
- Minimum viable output: for each named pattern, show the number of historical triggers, and the median BTC price movement 24h/72h/7d after each trigger
- Surface these stats in the UI as confidence metadata alongside each alert: e.g., "ACCUMULATION signal historically preceded +8.3% median move over 7d (n=14)"

**Assessment:** Implement at P1. This is what separates a "dashboard" from an "intelligence terminal." Without this, all pattern alerts are assertions, not evidence.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — "Narrative Exhaustion Peak" Pattern (Gemini only)
**What it is:** When a single dominant narrative persists for >5 consecutive days + Fear & Greed > 75 + KOL post count > 2x 30-day average, this signals narrative saturation and contrarian top signal.

**Assessment: IMPLEMENT.** This is intellectually rigorous and genuinely unique. Narrative velocity and persistence as a contrarian indicator is not something any competitor currently offers in an automated way. The data (`narrative.dominant_theme` tracking, `fear_greed.value`, `kol.post_count_24h`) exists. This is a high-conviction unique addition.

---

### UI2 — "Social-to-Market Divergence" Formula (Gemini only)
**What it is:** `(KOL Sentiment Score - 50) - (BTC 7-day Price % Change * 2)` as a specific, named, single-number index analogous to Santiment's social metrics.

**Assessment: IMPLEMENT.** The specific formula is Gemini's unique contribution. GPT-4o and Grok discussed the concept but didn't operationalize it. This formula is simple, auditable, and creates a named proprietary metric. Store it in `world_state.json` as `indices.social_market_divergence`.

---

### UI3 — Cross-Signal Anomaly Detector as $5K/Month Premium Feature (GPT-4o only)
**What it is:** A dedicated "anomaly detection" product tier that identifies rare simultaneous multi-signal conditions that historically precede major market movements. Marketed specifically to hedge funds and institutional investors as a standalone premium.

**Assessment: INVESTIGATE FURTHER.** The concept is sound and the monetization logic is strong (GPT-4o is the only model to think about pricing tiers and institutional GTM strategy). However, this requires the backtesting framework (M4) to exist first — you cannot sell anomaly detection to institutions without validated historical performance. Revisit in Cycle 2 after M4 is implemented.

---

### UI4 — RTX 4090 ML Model Deployment with VRAM Partitioning (Grok only)
**What it is:** Specific guidance on deploying TimeMixer and PatchTST within 8GB VRAM for inference to avoid contention with the HeyGen/Wav2Lip render pipeline. Includes the insight that inference can run on one 4090 while rendering uses the other.

**Assessment: IMPLEMENT — but P2.** The VRAM partitioning insight is technically sound and the specific concern about render pipeline contention is the correct engineering constraint. TimeMixer for multivariate BTC forecasting using hashrate, F&G, and exchange flows as inputs is the right model choice. However, this is infrastructure work that should not block the analytical and visual improvements above. Schedule for after P0/P1 are stable.

---

### UI5 — "Miner Conviction Index" Specific Formula (Gemini only)
**What it is:** `(Current Hashrate / 90-day Avg Hashrate) - (BTC Price % Change over 30 days)` as the Puell Multiple analog.

**Assessment: IMPLEMENT.** While all three models agreed hashrate needs synthesis (U1), only Gemini provided a specific, actionable, mathematically sound formula. This is the implementation to use. Store the 90-day rolling hashrate average in state and compute this index on each update cycle.

---

### UI6 — Clickable Radar Axes Revealing Component Sparklines (Gemini only)
**What it is:** In the radar chart (U3), clicking any axis would drill down to show the underlying sub-signals and their sparklines. Transforms the radar from a display into an interactive investigation tool.

**Assessment: IMPLEMENT at P1.** This is the feature that turns a "pretty chart" into a "professional tool." Analysts will click. This interaction model is standard in Bloomberg and Glassnode. The effort is moderate (click handler + sparkline panel component) but the professional credibility gain is disproportionate.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Visual Innovation: Heatmap (GPT-4o) vs. Radar/Sonar (Grok + Gemini)
**GPT-4o says:** Build a sentiment heatmap showing sentiment across metrics and timeframes.
**Grok + Gemini say:** Build a radar/sonar chart showing multi-dimensional signal convergence.

**VERDICT: Radar/Sonar wins.** Two vs. one, and the qualitative argument is stronger. A heatmap is a well-understood format that every competitor already uses. A live radar chart that changes shape as market conditions shift is genuinely novel and creates the "what is that?" reaction that drives demos and word-of-mouth among institutional users. The heatmap is not wrong — it could be a secondary view — but it should not be the flagship innovation.

---

### C2 — Implementation of ML Models: Specific Repos (GPT-4o) vs. General Guidance (Grok)
**GPT-4o says:** TimeMixer repo is `github.com/locuslab/TimeMix`, PatchTST is `github.com/patchtst/patchtst`, Chronos is `github.com/chronos/chronos`.
**Grok says:** TimeMixer repo is `github.com/tsinghuarui/TimeMixer`, PatchTST correct, and provides VRAM-aware deployment guidance.

**VERDICT: GPT-4o's repo URLs appear to be hallucinated or incorrect.** The official TimeMixer paper is from Tsinghua (Grok is directionally correct). The "locuslab" organization is associated with a different project (DEQ). Do not use GPT-4o's repo links without manual verification. Grok's VRAM guidance is the more operationally useful contribution here regardless. **Action:** Verify all repos manually before implementation. Use `tsinghua-earth/TimeMixer` as the starting search point.

---

### C3 — Priority of ML Features: P2 (GPT-4o/Grok) vs. Not Mentioned (Gemini)
**GPT-4o + Grok say:** ML forecasting models should be P2.
**Gemini says:** Does not recommend ML models at all — focuses entirely on analytical synthesis of existing data.

**VERDICT: Gemini is implicitly correct on sequencing, GPT-4o/Grok are right on the feature.** Gemini's silence on ML is a signal: the existing data is not yet fully synthesized, so running ML on top of unsynthesized data is premature. The right order is: (1) implement composite indices and pattern detection upgrades, (2) implement backtesting, (3) then apply ML. Mark ML as P2 with an explicit dependency on M4 (backtesting framework) being complete first.

---

### C4 — "$5K Feature": Anomaly Detector (GPT-4o) vs. Polymarket Front-Run (Grok) vs. Sovereign Context Sonar (Gemini)
**GPT-4o says:** The anomaly detector is the $5K feature.
**Grok says:** The full cross-signal alpha system is the value prop.
**Gemini says:** The Sovereign Context Sonar radar is the differentiator.

**VERDICT: The $5K/month feature is the combination of the radar + validated cross-signal alerts + backtested performance stats.** No single feature stands alone. GPT-4o is right that anomaly detection is the monetization frame (it's what you tell institutional clients). Gemini is right that the radar is the demo hook. Grok is right that the cross-signal alerts are the core analytical engine. Build them as one integrated product: the radar is the visual, the alerts are the engine, and "anomaly detection with backtested performance" is the sales pitch.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

1. **Data Pipeline Architecture** — All three models praised the breadth and quality of data streams being collected. The `sovereign_context_engine.py` data aggregation layer, `world_state.json` state management, and the existing range of sources (BTC metrics, Fear & Greed, mempool, Lightning, KOL sentiment, articles, whale alerts, Polymarket, PCAF) are production-grade. **Do not restructure the data collection layer.**

2. **PCAF Anomaly Score** — All models referenced this as a unique, existing differentiator that competitors do not have. It should be featured more prominently in the UI but the underlying logic is solid. **Do not change the PCAF calculation.**

3. **Existing `detect_patterns()` Foundation** — All models confirmed the existing pattern detection architecture is the correct approach and the right place to extend. The function structure, alert format, and severity system are sound. **Extend it; do not rewrite it.**

4. **Stage Brief Narrative System** — The narrative labeling and dominant theme tracking was praised by all models as a genuine differentiator. Gemini's "Narrative Exhaustion Peak" pattern builds on it, but the underlying system is excellent. **Do not change the narrative generation logic.**

5. **Front-End SVG/Gauge Components** — The existing `signal-gauge-svg` and clean visual design language were referenced positively by Grok and Gemini as the right foundation to extend (specifically: extend to radar, not replace). **Do not redesign the component system from scratch.**

---

## LAW COMPLIANCE CONSENSUS

*Note: No model raised explicit legal/regulatory compliance concerns. The following is synthesized from implicit requirements in the recommendations.*

**Fully Compliant (no model raised concerns):**
- Data display of publicly available market data (BTC price, Fear & Greed, mempool) — compliant
- Sentiment aggregation from public sources — compliant
- Polymarket odds display — compliant as information display, not as regulated financial advice

**Requires Attention (implied by institutional user targeting):**
- **Financial Advice Disclaimer:** All three models discuss targeting hedge funds and institutional investors. Any feature framed as a "signal" or "alert" that could be construed as investment advice requires explicit disclaimer language in the UI. Recommendation: Add a persistent "For informational purposes only — not financial advice" footer and per-alert disclaimer. **Priority: P0 from a liability standpoint.**
- **Backtested Performance Disclosure:** M4 (backtesting framework) surfaces historical signal performance. If this is shown to institutional clients, it likely triggers "past performance" disclosure requirements depending on jurisdiction. Any backtested stat must be accompanied by: "Past signal performance does not guarantee future results." **Priority: P0 before any institutional demo.**

**No consensus on violations** — no model flagged GDPR, CCPA, or securities law violations in the current implementation.

---

## SECURITY CONSENSUS

*Note: Models focused on product/feature audit rather than security code review. No security vulnerabilities were explicitly identified in code. The following reflects consensus-implied security considerations.*

**No explicit security vulnerabilities flagged by any model.**

**Implicit security considerations from recommendations:**
1. **API Key Management for New Data Sources** — As M1 (Polymarket expansion) and UI4 (ML model deployment) add new external integrations, ensure all API credentials remain in environment variables/secrets manager, never hardcoded. Current pattern appears sound; maintain it.
2. **ML Model Input Validation** — If UI4 (RTX 4090 ML inference) is implemented, add input sanitization before feeding data to inference pipeline to prevent adversarial data injection.
3. **Backtesting Data Integrity** — Historical `world_state.json` snapshots used for backtesting (M4) must be write-protected/checksummed to prevent retroactive manipulation of "historical" performance claims.

**Security audit recommendation:** A dedicated security-focused Cycle 2 audit pass is warranted before any institutional client access is granted, specifically targeting authentication, API exposure, and data integrity.

---

## WORLD-CLASS GAP CONSENSUS

*Items mentioned by 2+ models as missing from a truly world-class intelligence terminal:*

### WCG1 — No Proprietary Named Metrics (all 3 models)
Bloomberg sells MVRV. Glassnode sells SOPR. We sell raw numbers with no brand equity. A world-class terminal has 3–5 proprietary named indices that become industry vocabulary. We have the data to create them; we haven't created them yet.

### WCG2 — No Multi-Dimensional Signal Synthesis Visualization (all 3 models)
Every competitor shows charts. None shows a live "fingerprint" of market conditions across 6+ orthogonal dimensions simultaneously. The radar chart is the gap between "crypto dashboard" and "intelligence terminal."

### WCG3 — No Validated Historical Signal Performance (2 models: GPT-4o, Grok)
Alerts without historical accuracy data are opinions. Alerts with "triggered 14 times historically, median +8.3% BTC move in 7 days (n=14)" are evidence. The backtesting gap is the gap between a retail tool and an institutional tool.

### WCG4 — No Leading Indicator Layer (2 models: Gemini, Grok)
Polymarket data is being used as a sentiment indicator when it should be used as a *leading* indicator. A world-class terminal distinguishes between lagging indicators (price, F&G), coincident indicators (exchange flows), and leading indicators (Polymarket, whale alerts) and labels them explicitly.

### WCG5 — Macro Correlation Layer Absent (2 models: GPT-4o, Grok)
Bloomberg's core value is cross-asset correlation. BTC vs. S&P 500, BTC vs. DXY, BTC vs. gold — none of this is currently surfaced. Polymarket macro sentiment is a partial proxy but not a substitute. A world-class terminal must show BTC's relationship to macro conditions.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Add financial advice disclaimer to all alert outputs and UI | `intelligence_page.html` (footer + per-alert), `sovereign_context_engine.py` (alert objects) | All (implied) | Institutional targeting without disclaimers is a liability |
| **P0 CRITICAL** | Implement "Miner Conviction Index" composite: `(hashrate / 90d_avg_hashrate) - (price_30d_pct_change)` | `sovereign_context_engine.py` → new `compute_indices()` function | All (U1, UI5) | Core gap vs. Glassnode/Puell Multiple; uses existing data |
| **P0 CRITICAL** | Implement "Exchange Pressure Ratio" discrete scored metric (-2 to +2) from exchange_flow + whale_alerts | `sovereign_context_engine.py` → `compute_indices()`, `world_state.json` schema | All (U1) | Replicates CryptoQuant's core value prop using existing data |
| **P0 CRITICAL** | Implement "Social-to-Market Divergence" index: `(kol_sentiment - 50) - (btc_change_7d * 2)` | `sovereign_context_engine.py` → `compute_indices()` | All (U1, UI2) | Santiment analog; single formula, high analytical value |
| **P0 CRITICAL** | Add `ACCUM