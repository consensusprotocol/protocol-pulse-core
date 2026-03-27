# CONSENSUS REPORT — INTELLIGENCE-TERMINAL — CYCLE 2
Generated: 2026-03-26 03:45
Models: grok, gemini (+1 failed — GPT-4o rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Data Collection Engine | 60 | N/A | 85 | **72** |
| Proprietary Index Calculation | 65 | N/A | 60 | **62** |
| Cross-Signal Pattern Detection | 30 | N/A | 62 | **46** |
| Visual Design / Front-End | 75 | N/A | 68 | **71** |
| Competitive Feature Parity | 45 | N/A | 52 | **48** |
| ML / Predictive Layer | N/A | N/A | 55 | **55** |
| Security / Paywall Architecture | 25 | N/A | N/A | **25** |
| Overall Readiness | 40 | N/A | 62 | **51** |

> **Synthesizer Note:** GPT-4o failed due to token rate limits. Consensus scores are derived from 2 models only. Confidence is moderate — not the full 3-model signal. The overall readiness score of **51** reflects a feature that has strong foundations but critical architectural blockers preventing production deployment. The wide divergence between Gemini (40) and Grok (62) on Overall Readiness is itself a signal: Gemini's architectural discovery (D1 below) is the reason for the gap and should be treated as dispositive.

---

## UNANIMOUS FINDINGS
*(Both active models agree — implement unconditionally)*

### U1 — `_calculate_proprietary_indices` is a Stub, Not a Production Feature
- **What it is:** The function responsible for calculating the signature branded indices (Miner Conviction, Exchange Pressure, Social Divergence) uses hardcoded baseline values and simplistic point-in-time logic rather than rolling statistical calculations. Specifically, `miner_conviction` uses a hardcoded `900 EH/s` baseline (Gemini, line 647) that will decay in accuracy as the network grows. There is no threshold validation, no historical smoothing, and no backtesting framework.
- **File/Line:** `sovereign_context_engine.py`, lines 628–714
- **What to change:** Replace hardcoded baselines with rolling moving averages (14-day and 50-day MAs of hashrate). Implement explicit bullish/bearish threshold zones. Add output validation to ensure scores stay within expected ranges. The formula structure proposed in Cycle 1 by Gemini (Miner Capitulation Risk, Liquid Supply Shock Ratio, Speculator-to-Hodler Conviction Index) should be the implementation target.

### U2 — Exchange Flow Data Has No Volume, Making It Quantitatively Useless
- **What it is:** The `_fetch_exchange_flow` function captures only the *direction* of exchange flows (inflow vs. outflow) but not the *magnitude* (USD or BTC volume). A $10,000 outflow and a $1,000,000,000 outflow are treated as identical signals. Any index, alert, or pattern detection built on top of this data is fundamentally unreliable for quantitative analysis.
- **File/Line:** `sovereign_context_engine.py`, lines 349–388
- **What to change:** The `_fetch_exchange_flow` function must be rewritten to source data that includes USD/BTC volume for both inflows and outflows. The existing string-scraping approach against other database tables is brittle and must be replaced with a proper data source or API integration. All downstream indices and pattern detectors that consume `exchange_flow` must be updated to use the volume field once available.

---

## MAJORITY FINDINGS
*(2 of 2 active models agree — implement unless compelling reason not to)*

> With only 2 active models, all agreements are effectively unanimous. The findings below were emphasized with slightly different framing or priority between models but represent full consensus.

### M1 — Proprietary Indices Must Be Visualized, Not Displayed as Static Text
- **What it is:** Both models converged on the idea that the competitive moat comes from *branded, visualized* indices — not just calculated values displayed as numbers. Grok explicitly called out that `intelligence_page.html` (lines 999–1025) displays indices as static text. Gemini noted that competitors win by branding indicators with clear "Bullish Crossover" / "Bearish Divergence" visual zones.
- **File/Line:** `intelligence_page.html`, lines 999–1025
- **What to change:** Replace static text output of proprietary indices with interactive charts. Each index should have a time-series visualization with labeled threshold zones (e.g., green zone above 70 = "Accumulation Confirmed," red zone below 30 = "Capitulation Risk"). Use the existing charting library already present in the codebase.

### M2 — Whale Alert Fetch is Hard-Capped at 5 Records, Missing Critical Signals
- **What it is:** The whale alerts fetch in `sovereign_context_engine.py` (lines 401–417) uses a hard limit of 5 records from `sentinel_alerts.db`. During high-activity periods (exactly when whale signals are most actionable), this cap will silently drop critical intelligence.
- **File/Line:** `sovereign_context_engine.py`, lines 401–417
- **What to change:** Increase the limit or implement dynamic windowing. Consider fetching the last N hours of data (e.g., 24h rolling window) rather than a static record count. Add a metadata field to the response indicating whether the result set was truncated.

### M3 — Cross-Signal Patterns Are Promising but Lack Validation Infrastructure
- **What it is:** Both models agreed that the cross-signal pattern library (`detect_patterns`, lines 452–591) contains valuable signal combinations (e.g., "Hashrate Up + Exchange Outflows + F&G < 20") but lacks any backtesting or historical validation. Grok cautioned against over-reliance on historical patterns cited in narrative form without quantitative validation. Gemini noted the backend and frontend detection are out of sync.
- **File/Line:** `sovereign_context_engine.py`, lines 452–591
- **What to change:** Add a confidence weighting system to each pattern based on historical occurrence rate. Even a simple lookup table of "this pattern preceded a 20%+ move within 30 days in X of Y occurrences" adds credibility. Priority patterns to validate first: Stealth Accumulation, Narrative Saturation Top.

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluated carefully)*

### [GEMINI UNIQUE] — D1: Critical Business Logic Embedded in Frontend JavaScript, Bypassing Paywall and Creating Dual Sources of Truth
- **What it is:** Gemini identified what may be the most severe architectural flaw in the codebase. The `computeSignalMatrix` (line 1372) and `computeDivergences` (line 1521) functions in `intelligence_page.html` perform substantive intelligence calculations in the user's browser. This creates three distinct problems:
  1. **Security:** The paywall is implemented as a CSS overlay (`.classified-gate`, line 758). The underlying data and logic are delivered to every user regardless of subscription status. Any user can inspect the page source to access "premium" divergence signals. This is not a paywall — it is a visual obstruction.
  2. **Architecture:** The backend `detect_patterns` function and the frontend `computeDivergences` function are independent implementations of the same conceptual task. They will inevitably drift out of sync, producing contradictory results between what the backend logs and what users see.
  3. **Scalability:** Logic embedded in frontend JS cannot be reused for backend alerting, API endpoints, email notifications, or historical analysis.
- **File/Line:** `intelligence_page.html`, lines 758, 1372, 1521
- **Assessment:** **IMPLEMENT — P0.** This is the highest-severity finding of the entire two-cycle audit. It is a security vulnerability, an architectural anti-pattern, and a business risk simultaneously. Grok did not catch this. The fact that only one model flagged it does not reduce its severity — it increases our obligation to act on it. The fix is non-negotiable before any paid tier goes live.

### [GROK UNIQUE] — Stock-to-Flow Approximation Using Existing Block Height Data
- **What it is:** Grok proposed using the already-collected `block_height` and `btc.price` data to calculate a simplified S2F ratio, directly competing with Glassnode's premium S2F offering.
- **Assessment:** **INVESTIGATE FURTHER.** The S2F model is well-understood, and the data is already available. However, S2F is a long-term valuation model and its predictive validity has been widely disputed post-2022. Implementing it as a "valuation reference" rather than a "predictive signal" is the correct framing. Add it as a P2 branded metric with clear disclaimers. Do not represent it as a forward-looking indicator.

### [GROK UNIQUE] — No Real-Time Alert Updates Without Full Page Reload
- **What it is:** The dashboard auto-refreshes signal scores every 5 minutes (lines 1679–1698 in `intelligence_page.html`) but whale alerts and divergence alerts require a full page reload to update.
- **Assessment:** **IMPLEMENT — P1.** This is a UX gap that directly impacts the "intelligence terminal" experience. High-frequency alerts (whale movements, divergence crossovers) lose their value if they're delayed by page reload cycles. The existing 5-minute refresh mechanism should be extended to include alert components via the same polling architecture.

### [GEMINI UNIQUE] — Silent Exception Swallowing in Polymarket Service
- **What it is:** In `services/polymarket_service.py`, the `_parse_outcomes` function (line 74) uses a bare `except:` block, silently catching all exceptions and potentially returning corrupt or empty data with no log trace.
- **Assessment:** **IMPLEMENT — P1.** Silent data corruption in a service that feeds market intelligence signals is unacceptable. This is a standard engineering hygiene issue that is trivially fixed and high-impact.

### [GROK UNIQUE] — Social Sentiment Divergence Index as Competitive Feature
- **What it is:** Combining KOL sentiment and article sentiment into a divergence index (e.g., KOL bullish + articles bearish = potential reversal signal) as a direct competitor to Santiment's Social Volume/Divergence offering.
- **Assessment:** **IMPLEMENT — P1.** The data already exists. The combination is novel, branded, and directly replicates a $500/month paid feature. This should be one of the first additions to `_calculate_proprietary_indices` after the architectural fixes are complete.

---

## CONFLICTS
*(Models gave contradictory signals — synthesizer tiebreaker applied)*

### Conflict 1 — Overall Readiness Score: Gemini (40) vs. Grok (62)
- **Gemini's position:** The paywall security flaw and frontend business logic make the feature unfit for production. Score: 40.
- **Grok's position:** The feature is functional with known gaps, close to production with targeted fixes. Score: 62.
- **Tiebreaker — Gemini is correct.** The CSS-only paywall bypassing premium data is not a UX deficiency — it is a billing integrity failure. A paying user who discovers a free user can access the same "classified" data through DevTools will churn and dispute their charge. This alone makes the current state non-shippable for any commercial tier. Grok's higher score appears to reflect optimism about the feature set without adequately weighting the security risk.

### Conflict 2 — Cross-Signal Pattern Detection Score: Gemini (30) vs. Grok (62)
- **Gemini's position:** The backend/frontend split is a critical architectural flaw warranting a 30/100.
- **Grok's position:** The patterns are promising and actionable, warranting a 62/100 with caveats about validation.
- **Tiebreaker — Gemini is correct on direction, Grok is correct on nuance.** The frontend JS duplication is a genuine architectural problem. However, Grok's point that the patterns themselves are valuable is also true. The *logic* deserves a 62; the *architecture* deserves a 30. The consensus score of 46 appropriately reflects that a good feature is currently built on a broken foundation.

### Conflict 3 — Data Collection Engine Score: Gemini (60) vs. Grok (85)
- **Gemini's position:** The missing volume data and brittle fetch functions are fundamental data quality failures. Score: 60.
- **Grok's position:** The engine is largely capable and comprehensive. Score: 85.
- **Tiebreaker — Split decision, lean toward Gemini.** Grok's 85 reflects the breadth and sophistication of the data collection architecture, which is genuinely impressive. However, Gemini is correct that a data pipeline which produces directional-only exchange flow signals is quantitatively broken for any serious analytics use case. Consensus score of 72 is appropriate — strong architecture, meaningful data gap.

---

## VALIDATED STRENGTHS
*(Both models confirmed these areas are excellent — do NOT change in the second pass)*

1. **Brand Aesthetic and Visual Design Language:** Both models agreed the front-end adheres well to the specified brand laws. The dark terminal aesthetic, color palette, and typography are strong and should not be modified.
2. **Data Collection Breadth:** The `sovereign_context_engine.py` collects an impressive range of signals (BTC price, Fear & Greed, mempool fees, hashrate, Lightning stats, KOL sentiment, article sentiment, exchange flows, whale alerts, Polymarket odds, PCAF anomaly score). The diversity of data sources is a genuine competitive asset.
3. **Narrative Synthesis via Stage Brief:** The stage brief narrative mechanism is a differentiating feature that competitors do not offer. Both models praised this as a unique capability.
4. **Polymarket Integration:** The use of Polymarket odds as a macro sentiment overlay is a novel competitive advantage not available in Glassnode, CryptoQuant, or Santiment. Preserve this integration.
5. **Overall Structural Architecture of `sovereign_context_engine.py`:** The concept of a centralized intelligence brain that coordinates all data fetching and synthesis is the correct architectural pattern — the problem is that it isn't being fully respected by the frontend. The architecture itself is sound.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Finding |
|---|---|---|
| Single Source of Truth | ❌ VIOLATED | Business logic split between `sovereign_context_engine.py` and `intelligence_page.html` JS creates two independent calculation engines. |
| Paywall Integrity | ❌ VIOLATED | CSS-only gate sends premium data to all users regardless of subscription status. |
| Data Quality | ⚠️ PARTIAL | Exchange flow direction captured but volume missing; whale alert hard cap may truncate signal. |
| No Silent Failures | ❌ VIOLATED | Bare `except:` in `polymarket_service.py` line 74 swallows errors silently. |
| Brand Consistency | ✅ COMPLIANT | Both models confirmed visual design adherence. |
| Proprietary Index Branding | ⚠️ PARTIAL | Names exist but formulas are not production-grade; indices are not visualized competitively. |
| Competitive Feature Parity | ⚠️ PARTIAL | Data exists to compete with $500/month tools; implementation is incomplete. |

---

## SECURITY CONSENSUS

**Critical security issues flagged by at least 1 model, ordered by severity:**

1. **🔴 P0 — CSS Paywall Bypass (Gemini, unique):** Premium intelligence data is delivered to all users in the page HTML. The subscription gate is purely visual. Any user can access classified signals via browser DevTools. This is a billing fraud risk and must be resolved with server-side conditional rendering before any commercial launch.

2. **🟠 P1 — No Input Validation on Signal Calculation Inputs (inferred from both models):** Neither model explicitly named this, but the absence of data validation on inputs to `_calculate_proprietary_indices` means malformed or missing upstream data (e.g., a null hashrate reading) could produce corrupted index scores that propagate silently to the dashboard.

3. **🟡 P2 — Silent Exception in Polymarket Service (Gemini, unique):** Bare `except:` block in `_parse_outcomes` (line 74) prevents any visibility into data corruption events in a production environment. An exception here means the Polymarket odds feed could silently return zeros or stale data.

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models as missing from a truly world-class product)*

1. **Historical Backtesting for Cross-Signal Patterns** *(both models)*: Every competitor at the $500+/month tier provides historical performance data for their signals. "This pattern preceded a 15%+ move in 7 of 9 historical occurrences" is what converts a dashboard into a decision-support tool. Without this, Protocol Pulse is a display — not intelligence.

2. **Volume-Weighted Exchange Flow Signals** *(both models)*: World-class platforms (CryptoQuant, Glassnode) lead with magnitude, not just direction. The entire exchange flow signal layer needs to be rebuilt on volumetric data to reach competitive parity.

3. **Interactive, Branded Proprietary Index Charts with Threshold Zones** *(both models)*: Glassnode and Santiment don't just show numbers — they show colored zones, crossover events, and alert thresholds. The current static text display of proprietary indices is the equivalent of Bloomberg Terminal showing a number in a text file. Visualization is not cosmetic — it is the product.

4. **Real-Time Alert Architecture** *(Grok primary, Gemini secondary)*: A terminal-grade product must push alerts to users, not require them to refresh. WebSocket or SSE architecture for whale alerts and divergence crossovers would differentiate Protocol Pulse from static dashboard competitors.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

**P0 CRITICAL**

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0.1 | Move `computeSignalMatrix` and `computeDivergences` logic from frontend JS to `sovereign_context_engine.py`. Pass computed results to template as server-side context variables. | `intelligence_page.html` lines 1372, 1521 → `sovereign_context_engine.py` | Gemini (unique, high confidence) | Single source of truth violation; architectural anti-pattern; renders backend `detect_patterns` redundant and contradictory |
| P0.2 | Implement server-side paywall gating. Modify the Flask route serving `intelligence_page.html` to conditionally exclude premium signal data from template context if `is_commander` is false. CSS gate must be removed. | Flask route handler + `intelligence_page.html` line 758 | Gemini (unique, high confidence) | CSS-only paywall is a billing integrity failure — premium data is delivered to all users |
| P0.3 | Rewrite `_fetch_exchange_flow` to source volumetric data (USD/BTC inflow and outflow totals), replacing the current direction-only string scraping approach | `sovereign_context_engine.py` lines 349–388 | Both models | Directional-only exchange flow makes all downstream indices and patterns quantitatively meaningless |
| P0.4 | Expand `_calculate_proprietary_indices` with rolling MA baselines (14-day / 50-day), replace hardcoded `900 EH/s` baseline, add threshold validation and bullish/bearish zone outputs | `sovereign_context_engine.py` lines 628–714 | Both models | Current implementation is a non-production stub; hardcoded baselines decay over time |

**P1 HIGH**

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1.1 | Add interactive time-series charts for all proprietary indices with labeled threshold zones (Bullish/Bearish/Neutral bands). Replace static text display. | `intelligence_page.html` lines 999–1025 | Both models | Competitive parity requires visualization — displaying numbers is not a premium product |
| P1.2 | Replace bare `except:` in `_parse_outcomes` with specific exception types and structured logging | `services/polymarket_service.py` line 74 | Gemini (unique) | Silent failure in a live intelligence feed is a production data quality risk |
| P1.3 | Extend 5-minute auto-refresh to include whale alerts and divergence alert components without full page reload. Implement polling or SSE for alert components. | `intelligence_page.html` lines 1679–1698 | Grok (unique) | Alert latency defeats the "terminal" value proposition; high-frequency signals must be near-real-time |
| P1.4 | Add Social Sentiment Divergence Index to `_calculate_proprietary_indices`: combine KOL sentiment score with article sentiment to surface divergence as a reversal signal | `sovereign_context_engine.py` lines 628–714 | Grok (unique) | Directly replicates Santiment's $500/month Social Divergence feature using already-collected data |
| P1.5 | Increase whale alert fetch from hard cap of 5 to a 24-hour rolling window with truncation metadata | `sovereign_context_engine.py` lines 401–417 | Grok (unique, Gemini inferred) | Hard cap of 5 silently drops signals during peak activity — worst-case failure mode |
| P1.6 | Add time-based caching to all `_fetch_...` functions (Redis or `functools.lru_cache`) to improve resilience and performance | `sovereign_context_engine.py`, all `_fetch_` functions | Gemini (unique) | No caching means every render cycle makes full external calls; single API failure takes down the entire intelligence layer |

**P2 MEDIUM**

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P2.1 | Add confidence weighting to `detect_patterns` using historical occurrence lookup table | `sovereign_context_engine.py` lines 452–591 | Both models | Patterns without historical validation are assertions, not intelligence |
| P2.2 | Implement simplified Stock-to-Flow ratio using existing `block_height` and `btc.price` data; display as long-term valuation reference (not predictive signal) | `sovereign_context_engine.py` + `intelligence_page.html` | Grok (unique) | Replicates Glassnode premium feature using already-collected data; must be framed carefully |
| P2.3 | Visualize exchange flow as cumulative 7/30/90-day net inflow/outflow chart showing accumulation/distribution phases (requires P0.3 volume data first) | `intelligence_page.html` | Grok (unique) | Directly competes with CryptoQuant's Exchange Net Position Change; visually compelling |
| P2.4 | Implement Speculator-to-Hodler Conviction Index: `(LN Capacity Growth + Hashrate Growth) / (KOL Sentiment Delta + F&G Value)` | `sovereign_context_engine.py` lines 628–714 | Gemini Cycle 1 | Unique branded metric that uses Lightning data as a differentiator vs. all named competitors |

---

## CYCLE 2 VERDICT

**Production Ready: NO**

The intelligence-terminal feature has a genuinely impressive foundation — the data collection breadth, the narrative synthesis capability, and the visual design are all competitive-grade assets. However, three blockers make the current state non-shippable:

**Absolute Final Blockers:**

1. **The CSS paywall is a commercial fraud risk.** Premium data is delivered to every user. This cannot be in a production release with any paid tier attached. It will generate chargebacks, user trust failures, and potential legal exposure.

2. **Business logic split across backend and frontend creates an unmaintainable system.** Two independent calculation engines will diverge over time, producing contradictory intelligence for users and engineers alike. Every future feature built on this foundation will compound the problem.

3. **Exchange flow data is directionally captured but volumetrically empty.** Any index or pattern built on direction-only flow data cannot be defended as "institutional-grade intelligence." This is a core data quality issue, not a feature gap.

Resolve P0.1 through P0.4. The P1 items significantly improve product quality but the P0 items are the gate. After the second pass, re-run a targeted audit focused specifically on the paywall architecture and the data ingestion pipeline.

---

## SECOND PASS PROMPT
*(

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini consistently identified the highest-leverage architectural issues — specifically the P0 data integrity flaw (exchange flow lacking volume data, rendering signals quantitatively useless) and the strategic branding layer for proprietary metrics — findings that proved decisive enough to single-handedly explain the 22-point readiness gap between the two models and were validated as "dispositive" by the consensus synthesizer. Its recommendations were not only accurate in Cycle 2 but were framed with specific formulas, named indices, and file-level citations, making them immediately actionable rather than directionally correct.

---

# FINAL SECOND-PASS PRIORITY LIST
*Definitive ordered implementation backlog derived from all Cycle 1 + Cycle 2 findings*

---

## 🔴 P0 — CRITICAL BLOCKERS (Production is unsafe without these)

### P0-1 — Fix Exchange Flow: Add Volume Quantification
- **Finding:** U2 / Gemini D1. Current `exchange_flow` records only direction (inflow/outflow), not magnitude. A $10K outflow and a $1B outflow are treated identically. Every signal derived from this data is structurally weak.
- **File:** `sovereign_context_engine.py` — exchange flow ingestion layer
- **Action:** Modify the data fetch to capture USD/BTC volume alongside direction. Add a volume-weighted net flow calculation. Gate any Exchange Pressure index display behind a `volume_available: bool` flag until this is resolved. Do not ship Exchange Pressure as a paid feature in its current form.

### P0-2 — Replace Hardcoded Baselines in `_calculate_proprietary_indices`
- **Finding:** U1 — unanimous. `miner_conviction` uses a static `900 EH/s` baseline (line 647). As network hashrate grows, this baseline becomes increasingly wrong, silently degrading signal quality with no visible failure.
- **File:** `sovereign_context_engine.py`, lines 628–714
- **Action:** Replace all hardcoded scalar baselines with rolling moving averages. Minimum: 14-day MA for hashrate, 30-day MA for exchange flow magnitude, 7-day MA for social sentiment. Add a `baseline_staleness_warning` if the rolling window has fewer than N data points. Log when fallback to hardcoded values occurs.

### P0-3 — Implement Paywall Architecture
- **Finding:** Gemini identified Security/Paywall at 25 — the lowest score in the entire audit. No other subsystem scored this low. There is currently no enforcement layer preventing free users from accessing premium signal data.
- **File:** Not yet created — requires new `auth_middleware.py` or equivalent
- **Action:** Define tier boundaries explicitly (Free / Pro / Institutional). Implement server-side route guards — not just front-end UI hiding. Premium API endpoints must validate session/token before returning data. This is a revenue integrity issue, not just a feature gap.

---

## 🟠 P1 — HIGH PRIORITY (Ship within current sprint)

### P1-1 — Build Rolling Statistical Framework for All Indices
- **Finding:** U1 extension. Beyond replacing hardcoded baselines, the entire index calculation system needs a backtesting scaffold to validate that signals have historical predictive value before being sold as intelligence.
- **File:** `sovereign_context_engine.py`, new module `index_validator.py`
- **Action:** Implement a minimum 90-day historical backtest for each proprietary index. Track accuracy of directional calls (did a high Miner Conviction score precede price appreciation within 30 days?). Display a confidence interval or sample-size warning on any index with fewer than 30 historical data points.

### P1-2 — Brand and Name All Proprietary Indices with Product Copy
- **Finding:** Gemini's strategic framing — competitors don't sell "exchange flows," they sell "Exchange Net Position Change." The naming and marketing layer is a competitive moat, not cosmetic.
- **File:** Front-end dashboard components, `index_metadata.json` or equivalent config
- **Action:** Define canonical names, one-sentence descriptions, and methodology disclosures for every index. Suggested names already validated: **Miner Capitulation Risk Indicator**, **Liquid Supply Shock Ratio**, **Speculator-to-Hodler Conviction Index**, **Social Divergence Score**. Create a "Methodology" tooltip on each index card. This directly justifies premium pricing.

### P1-3 — Cross-Signal Pattern Detection: Implement Named Composite Patterns
- **Finding:** Cross-Signal Pattern Detection scored 30 (Gemini) / 62 (Grok) — the widest divergence in the audit, indicating this subsystem is partially implemented but architecturally incomplete.
- **File:** `sovereign_context_engine.py` — pattern detection module
- **Action:** Define at minimum 3 named composite patterns as first-class objects with explicit trigger conditions, historical validation notes, and confidence scores. Example: **Stealth Accumulation** = (whale inflows rising) + (social sentiment flat or negative) + (exchange outflows increasing). Each pattern should emit a structured object: `{name, confidence, triggered_at, contributing_signals[], historical_accuracy}`.

### P1-4 — Miner Capitulation Risk Indicator: Implement MA Crossover Logic
- **Finding:** Gemini Cycle 1, validated in Cycle 2. Glassnode's Difficulty Ribbon Compression is a paid feature we can replicate with existing data.
- **File:** `sovereign_context_engine.py`
- **Action:** Calculate 14-day and 50-day moving averages of `hashrate_eh`. Emit a `MINER_STRESS` signal when short MA crosses below long MA coinciding with `change_7d < -10%`. Backtest against 2018, 2022 capitulation events before display. Label clearly as "Protocol Pulse Miner Capitulation Risk."

---

## 🟡 P2 — MEDIUM PRIORITY (Next sprint)

### P2-1 — Liquid Supply Shock Ratio: Build Proxy Metric
- **Finding:** Gemini Cycle 1. Illiquid supply tracking is a high-value Glassnode feature. We can proxy it.
- **Action:** Use exchange outflow trends over 30/90 days as a supply tightness proxy. When sustained outflows coincide with rising price, flag as **Supply Shock Risk: Elevated**. Document the proxy methodology transparently — do not present it as equivalent to on-chain UTXO analysis.

### P2-2 — Polymarket Integration: Surface as Macro Overlay, Not Raw Data
- **Finding:** Grok Cycle 1 — Polymarket odds are a unique asset competitors lack. Currently underutilized.
- **Action:** Build a **Macro Sentiment Overlay** panel that shows Polymarket probability for key macro events (rate decisions, ETF approvals, regulatory events) alongside BTC price. Automate the mapping of Polymarket contract IDs to event categories. This is a genuine competitive differentiator — no competitor has real-time prediction market data embedded in their dashboard.

### P2-3 — KOL Sentiment: Add Divergence Detection vs. Price Action
- **Finding:** Santiment charges $500/month for social divergence. Our KOL + article sentiment data can replicate this.
- **Action:** Calculate a rolling 7-day correlation between KOL sentiment score and BTC price direction. When correlation breaks (sentiment bullish, price falling, or vice versa), emit a **Sentiment Divergence Alert**. This is a named, branded signal — not just a raw sentiment score.

### P2-4 — ML/Predictive Layer: Define Scope Before Building
- **Finding:** ML scored 55 with only Grok providing input. No consensus. Risk of over-engineering.
- **Action:** Do not build a generalized ML layer. Instead, define 2 specific, narrow prediction targets: (1) 72-hour price direction classification (up/flat/down), (2) Miner stress event prediction 14 days forward. Train only on features already in the data pipeline. Ship as **BETA — Experimental Signal** with explicit accuracy disclosure.

---

## 🟢 P3 — LOW PRIORITY / POLISH (Backlog)

### P3-1 — Stock-to-Flow Approximation
- **Finding:** Grok Cycle 1. Implementable with block height + price data.
- **Action:** Build as