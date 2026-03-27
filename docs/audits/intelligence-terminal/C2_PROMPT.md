# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: intelligence-terminal
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### AUDIT RESPONSE: PROTOCOL PULSE INTELLIGENCE DASHBOARD

I have conducted a thorough review of the provided codebase and competitive landscape to address the questions posed. My analysis focuses on leveraging the existing data and infrastructure to create a premium Bitcoin intelligence dashboard that can rival high-end platforms like Bloomberg Terminal, Glassnode, CryptoQuant, and Santiment. Below are my detailed responses to each question, formatted as requested.

---

### Q1 — COMPETITIVE GAP ANALYSIS
**DETAILED ANALYSIS:**  
Competitors like Bloomberg Terminal, Glassnode, CryptoQuant, and Santiment offer a range of premium features at $500-2000/month, focusing on deep on-chain analytics, institutional-grade data visualization, and predictive signals. With Protocol Pulse's existing data streams (BTC price, Fear & Greed, mempool fees, hashrate, Lightning stats, KOL sentiment, article sentiment, exchange flows, whale alerts, Polymarket odds, PCAF anomaly score, and stage brief narratives), we can replicate or exceed several high-value features:  
- **Glassnode ($500/mo):** Offers metrics like Stock-to-Flow (S2F) ratio, Net Unrealized Profit/Loss (NUPL), and Exchange Net Position Change. We can approximate S2F using block height and price data, and mimic Exchange Net Position Change with our exchange flow data.  
- **CryptoQuant ($500/mo):** Focuses on exchange reserve trends, miner outflows, and stablecoin ratios. Our exchange flow and whale alert data can replicate exchange reserve trends and miner outflow signals.  
- **Santiment ($500/mo):** Emphasizes social volume, sentiment divergence, and whale transaction counts. Our KOL sentiment, article sentiment, and whale alerts directly map to these.  
- **Bloomberg Terminal ($2000/mo):** Provides cross-asset correlation, macro overlays, and proprietary indices. We can build proprietary indices (already in progress with Miner Conviction, Exchange Pressure, Social Divergence) and overlay Polymarket macro sentiment with BTC price trends.

**SPECIFIC RECOMMENDATION:**  
1. **Stock-to-Flow Approximation (vs. Glassnode):** Use block height (already collected) and BTC price to calculate a simplified S2F ratio, displaying it as a long-term valuation metric.  
2. **Exchange Reserve Trend (vs. CryptoQuant):** Visualize exchange flow data as a cumulative net inflow/outflow chart over 7/30/90 days, highlighting accumulation/distribution phases.  
3. **Social Sentiment Divergence (vs. Santiment):** Combine KOL sentiment and article sentiment into a divergence index (e.g., KOL bullish + articles bearish = potential reversal).  
4. **Proprietary Indices (vs. Bloomberg):** Enhance the existing Miner Conviction, Exchange Pressure, and Social Divergence indices with historical backtesting data and display them as key dashboard metrics with bullish/bearish thresholds.  
5. **Whale Transaction Heatmap (vs. Santiment/CryptoQuant):** Plot whale alerts by tier and time on a heatmap to show accumulation/distribution spikes.

**IMPLEMENTATION PRIORITY:** P0 (Immediate)  
These features leverage existing data and directly compete with paid metrics, positioning Protocol Pulse as a premium alternative.

---

### Q2 — CROSS-SIGNAL ALPHA
**DETAILED ANALYSIS:**  
Cross-signal combinations are the core of predictive alpha, as they capture market dynamics that single metrics miss. Using Protocol Pulse’s diverse data, I’ve identified combinations with historical precedence for Bitcoin price movements. These are backtestable using historical data from 2017-2023 (e.g., Glassnode archives, CoinGecko, alternative.me).  
- Historical context shows that multi-signal confirmation often precedes 20-40% moves within 30-60 days (e.g., 2019 supply shock, 2020 post-halving rally).

**SPECIFIC RECOMMENDATION:**  
1. **Hashrate Up + Exchange Outflows + Fear & Greed < 20 (Supply Shock Precursor):**  
   - **Historical Context:** In Q2 2019, hashrate rose 30% while F&G hit 11 and exchange outflows spiked, preceding a 42% rally in 30 days.  
   - **Alpha:** Signals miner conviction and retail capitulation during accumulation.  
2. **Fear & Greed < 15 + Whale Accumulation Alerts + Price Down > 5% (Capitulation Buy):**  
   - **Historical Context:** March 2020 crash saw F&G at 10, whale buys, and a 12% drop, followed by a 60% recovery in 45 days.  
   - **Alpha:** Extreme fear with smart money buying signals bottoming.  
3. **Polymarket Sentiment > 70 + KOL Sentiment > 65 + Article Sentiment Bullish (Consensus FOMO Top):**  
   - **Historical Context:** Late 2017, social sentiment peaked with high prediction market odds, preceding a 30% correction.  
   - **Alpha:** Overbought consensus across markets and social signals a local top.  
4. **Mempool Fees > 50 sat/vB + Lightning Capacity Growth + Price Up < 2% (Utility Demand Signal):**  
   - **Historical Context:** Q3 2021, high fees and Lightning growth with flat price signaled underlying demand, leading to a 25% rally.  
   - **Alpha:** On-chain utility grow

## GEMINI — CYCLE 1 OUTPUT
Excellent. This is a high-quality codebase with a robust data collection engine at its core. The front-end is visually appealing and adheres to the specified brand laws. The challenge now is to leverage these powerful data assets to create an undeniable competitive advantage.

Here is my competitive audit and strategic analysis.

---

### Q1 — COMPETITIVE GAP ANALYSIS

What specific Bloomberg/Glassnode/CryptoQuant features costing $500-2000/month can we replicate or beat with our existing data?

**DETAILED ANALYSIS**
Competitors like Glassnode and CryptoQuant win by creating and branding proprietary on-chain metrics. Users don't just pay for "exchange flows"; they pay for Glassnode's "Exchange Net Position Change" or CryptoQuant's "All Exchanges Netflow". These are often simple calculations presented as indispensable, branded indicators.

Our `sovereign_context_engine.py` already collects the foundational data for these metrics: exchange flows, whale movements, miner data (hashrate/difficulty), and market sentiment (F&G). We also have unique assets they lack, like real-time Polymarket odds and structured KOL/narrative sentiment. The gap is not in data collection, but in the final step of synthesis, branding, and visualization.

The `_calculate_proprietary_indices` function is a P0 proof-of-concept for this exact strategy and should be expanded aggressively.

**SPECIFIC RECOMMENDATION**
We can immediately create a suite of "Protocol Pulse Indices" that directly compete with paid offerings.

1.  **Miner Capitulation Risk Indicator:** Glassnode sells a "Difficulty Ribbon Compression" indicator. We can replicate this.
    *   **Formula:** Calculate a 14-day and 50-day moving average of our `hashrate_eh`. When the short MA crosses below the long MA during a price downturn (`change_7d < -10%`), it signals miner stress.
    *   **Data Used:** `network.hashrate_eh`, `btc.change_7d`.

2.  **Liquid Supply Shock Ratio:** Competitors track illiquid supply. We can proxy this by combining whale alerts with exchange flow data.
    *   **Formula:** `(Whale Withdrawals in 24h + Total Exchange Outflow Volume) / (Whale Deposits in 24h + Total Exchange Inflow Volume)`. A ratio > 1 suggests a supply shock is building.
    *   **Data Used:** `whale_alerts`, `exchange_flow`. (Note: We need to enhance `exchange_flow` to include volume, not just direction).

3.  **Speculator-to-Hodler Conviction Index:** This pits short-term sentiment against long-term network health.
    *   **Formula:** `(LN Capacity Growth % + Hashrate Growth %) / (KOL Sentiment Score Delta % + F&G Value)`. A low score indicates froth and speculation dominating fundamentals. A high score shows network growth is outpacing hype.
    *   **Data Used:** `lightning.capacity_btc`, `network.hashrate_eh`, `kol.sentiment_score`, `fear_greed.value`.

Display these as dedicated charts with clear "Bullish Crossover" or "Bearish Divergence" zones, just as our competitors do.

**IMPLEMENTATION PRIORITY: P0**
The logic for these indices can be added directly to `sovereign_context_engine.py` in a single session. The front-end would require new chart components.

---

### Q2 — CROSS-SIGNAL ALPHA

What are the 5 most powerful cross-signal COMBINATIONS from our data that produce predictive alpha?

**DETAILED ANALYSIS**
The `detect_patterns` function is a solid foundation. True alpha comes from identifying non-obvious, multi-domain confluences that precede major market moves. The key is combining network health, market sentiment, and narrative velocity.

**SPECIFIC RECOMMENDATION**

1.  **The "Stealth Accumulation" Pattern:**
    *   **Signal:** `Fear & Greed < 25` + `exchange_flow == "outflow"` + `(Whale Withdrawals > Whale Deposits)` + `Price action is flat/down (change_7d between -5% and 2%)`.
    *   **Context:** Retail is terrified, but large entities are actively moving coins off exchanges to cold storage while the price is suppressed. This was visible at the $29k bottom in July 2021 and the post-FTX lows. It is one of the highest-conviction bottom signals.

2.  **The "Narrative Saturation Top" Pattern:**
    *   **Signal:** `KOL Post Count (24h) > 90th percentile` + `Article count > 90th percentile` for a specific theme (e.g., "ETF") + `Fear & Greed > 75` + `Polymarket odds for related event > 80%`.
    *   **Context:** The narrative has reached maximum penetration; everyone who could buy the rumor has. This is a classic "sell the news" setup. The pre-ETF approval peak in early 2024 is the canonical example.

3.  **The "Miner's Price Floor" Signal:**
    *   **Signal:** `btc.price` approaches the estimated cost of production (a metric we need to add, calculable from `network.difficulty` and energy price estimates) + `network.next_adj_pct` is negative + `Fear & Greed < 20`.
    *   **Context:** The price is low enough to stress miners, forcing some to turn off (negative difficulty adjustment), creating a capitulation event that often forms a generational price floor, as seen 

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — INTELLIGENCE-TERMINAL — CYCLE 1
Generated: 2026-03-26 03:42
Models: grok, gemini (+1 failed: gpt4o — rate limit exceeded)

---

## SCORES

> **Note:** Neither Grok nor Gemini produced explicit numerical scores. Scores below are derived by synthesizing the qualitative assessments, priority assignments, and depth of critique from each model's output. GPT-4o failed entirely — all GPT-4o cells are marked N/A.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Data Collection Engine | 88 | N/A | 85 | **87** |
| Proprietary Index Calculation | 62 | N/A | 65 | **64** |
| Cross-Signal Pattern Detection | 58 | N/A | 60 | **59** |
| Visual Design / Front-End | 72 | N/A | 70 | **71** |
| Competitive Feature Parity | 45 | N/A | 50 | **48** |
| ML / Predictive Layer | N/A | N/A | 55 | **55** |
| Overall Readiness | 63 | N/A | 65 | **64** |

**Confidence modifier applied:** All consensus scores are dampened by ~8 points due to GPT-4o failure. A 2-model consensus on a complex audit carries materially less certainty than a 3-model consensus. Second-pass decisions should treat all findings as "high-confidence provisional" rather than "definitive."

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

---

### U1 — `_calculate_proprietary_indices` is a proof-of-concept stub; it must be expanded into production-grade logic

**What it is:** Both Gemini and Grok independently identified that the `_calculate_proprietary_indices` function in `sovereign_context_engine.py` exists but is underdeveloped. It contains skeleton logic for Miner Conviction, Exchange Pressure, and Social Divergence indices but lacks the mathematical rigor, moving averages, and threshold definitions that would make these indices meaningful and defensible.

**File/Location:** `sovereign_context_engine.py` — `_calculate_proprietary_indices()` function

**What to change:**
- Implement rolling window calculations (14-day and 50-day MAs) for hashrate-based indices
- Define explicit bullish/bearish threshold bands with documented rationale for each index
- Add input validation so indices degrade gracefully when source data is missing rather than silently producing bad values
- Add docstrings with formula definitions so the logic is auditable

**Priority:** P0

---

### U2 — Exchange flow data captures direction only; volume is missing and required for meaningful analysis

**What it is:** Both models flagged that the `exchange_flow` data structure tracks directional flow (inflow/outflow) but does not capture volume. Gemini stated explicitly: *"We need to enhance `exchange_flow` to include volume, not just direction."* Grok's Supply Shock Precursor signal requires volume to be actionable. Without volume, exchange flow signals are qualitatively descriptive but quantitatively useless — you cannot distinguish a $1M outflow from a $1B outflow.

**File/Location:** `sovereign_context_engine.py` — data ingestion layer for `exchange_flow`; al

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: templates/intelligence_page.html (1703 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Intelligence Dashboard | Protocol Pulse{% endblock %}
   4 | 
   5 | {% block meta_description %}Premium Bitcoin signal intelligence — sovereign signal matrix, cross-signal divergence, whale intelligence, algorithmic scoring, Polymarket odds.{% endblock %}
   6 | 
   7 | {% block extra_css %}
   8 | <style>
   9 | /* ── Intelligence Page ── */
  10 | .intel-page {
  11 |   min-height: 100vh;
  12 |   background: #06070b;
  13 |   padding: 100px 24px 80px;
  14 |   position: relative;
  15 |   z-index: 2;
  16 |   box-shadow: inset 0 0 120px rgba(0,0,0,0.45), inset 0 0 60px rgba(0,0,0,0.3);
  17 | }
  18 | 
  19 | /* ── Cinematic Background System ── */
  20 | .intel-page::before {
  21 |   content: '';
  22 |   position: fixed;
  23 |   inset: 0;
  24 |   z-index: -2;
  25 |   pointer-events: none;
  26 |   background:
  27 |     radial-gradient(circle 300px at 15% 12%, rgba(255,59,95,0.18), transparent),
  28 |     radial-gradient(circle 250px at 85% 8%, rgba(93,228,255,0.10), transparent),
  29 |     radial-gradient(circle 200px at 50% 92%, rgba(248,193,92,0.12), transparent),
  30 |     #06070b;
  31 |   animation: bg-shift 12s ease-in-out infinite alternate;
  32 | }
  33 | .intel-page::after {
  34 |   content: '';
  35 |   position: fixed;
  36 |   inset: 0;
  37 |   z-index: -1;
  38 |   pointer-events: none;
  39 |   background:
  40 |     linear-gradient(to right, rgba(255,255,255,0.015) 1px, transparent 1px),
  41 |     linear-gradient(to bottom, rgba(255,255,255,0.015) 1px, transparent 1px);
  42 |   background-size: 48px 48px;
  43 |   opacity: 0.6;
  44 | }
  45 | @keyframes bg-shift {
  46 |   0%   { background-position: 0 0, 0 0, 0 0, 0 0; }
  47 |   100% { background-position: -20px 12px, 15px -8px, -8px 20px, 0 0; }
  48 | }
  49 | 
  50 | .intel-container {
  51 |   max-width: 1440px;
  52 |   margin: 0 auto;
  53 | }
  54 | 
  55 | /* ── Header ── */
  56 | .intel-eyebrow {
  57 |   font-family: 'JetBrains Mono', monospace;
  58 |   font-size: 10px;
  59 |   font-weight: 800;
  60 |   letter-spacing: 0.20em;
  61 |   text-transform: uppercase;
  62 |   color: #f8c15c;
  63 |   margin-bottom: 8px;
  64 | }
  65 | 
  66 | .intel-headline {
  67 |   font-size: 2.4rem;
  68 |   font-weight: 900;
  69 |   color: #eef2ff;
  70 |   letter-spacing: -0.03em;
  71 |   line-height: 1.1;
  72 |   margin-bottom: 8px;
  73 |   text-shadow: 0 4px 28px rgba(0,0,0,0.4);
  74 | }
  75 | 
  76 | /* ── Glass card ── */
  77 | .g-card {
  78 |   background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
  79 |   border: 1px solid rgba(255,255,255,0.08);
  80 |   border-radius: 16px;
  81 |   padding: 24px;
  82 |   height: 100%;
  83 |   position: relative;
  84 |   overflow: hidden;
  85 |   backdrop-filter: blur(16px);
  86 |   -webkit-backdrop-filter: blur(16px);
  87 |   box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  88 |   transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
  89 | }
  90 | .g-card:hover {
  91 |   border-color: rgba(255,59,95,0.25);
  92 |   box-shadow: 0 12px 36px rgba(0,0,0,0.35), 0 0 24px rgba(255,59,95,0.08);
  93 |   transform: translateY(-1px);
  94 | }
  95 | 
  96 | .g-card.accent-red { border-color: rgba(255,59,95,0.22); }
  97 | .g-card.accent-gold { border-color: rgba(248,193,92,0.18); }
  98 | .g-card.accent-cyan { border-color: rgba(93,228,255,0.15); }
  99 | 
 100 | .g-eyebrow {
 101 |   font-family: 'JetBrains Mono', monospace;
 102 |   font-size: 9px;
 103 |   font-weight: 800;
 104 |   letter-spacing: 0.18em;
 105 |   text-transform: uppercase;
 106 |   color: #f8c15c;
 107 |   margin-bottom: 16px;
 108 |   display: block;
 109 | }
 110 | 
 111 | /* ── Signal Strength Big Number ── */
 112 | .signal-composite {
 113 |   font-family: 'JetBrains Mono', monospace;
 114 |   font-size: 5rem;
 115 |   font-weight: 900;
 116 |   letter-spacing: -0.05em;
 117 |   line-height: 1;
 118 |   transition: color 0.5s ease;
 119 | }
 120 | 
 121 | .signal-label {
 122 |   font-family: 'JetBrains Mono', monospace;
 123 |   font-size: 14px;
 124 |   font-weight: 800;
 125 |   letter-spacing: 0.18em;
 126 |   text-transform: uppercase;
 127 |   margin-top: 6px;
 128 | }
 129 | 
 130 | .signal-trajectory {
 131 |   font-family: 'JetBrains Mono', monospace;
 132 |   font-size: 10px;
 133 |   font-weight: 700;
 134 |   letter-spacing: 0.12em;
 135 |   text-transform: uppercase;
 136 |   color: #95a0ba;
 137 |   margin-top: 8px;
 138 |   display: flex;
 139 |   align-items: center;
 140 |   gap: 6px;
 141 | }
 142 | 
 143 | /* ── Radial gauge ── */
 144 | .signal-gauge-wrap {
 145 |   position: relative;
 146 |   display: flex;
 147 |   flex-direction: column;
 148 |   align-items: center;
 149 | }
 150 | 
 151 | .signal-gauge-svg {
 152 |   width: 180px;
 153 |   height: 180px;
 154 | }
 155 | 
 156 | /* ── Component mini-gauges ── */
 157 | .component-row {
 158 |   display: grid;
 159 |   grid-template-columns: 1fr;
 160 |   gap: 10px;
 161 | }
 162 | 
 163 | .comp-item {
 164 |   display: flex;
 165 |   flex-direction: column;
 166 |   gap: 4px;
 167 | }
 168 | 
 169 | .comp-header {
 170 |   display: flex;
 171 |   justify-content: space-between;
 172 |   align-items: center;
 173 | }
 174 | 
 175 | .comp-label {
 176 |   font-family: 'JetBrains Mono', monospace;
 177 |   font-size: 9px;
 178 |   font-weight: 700;
 179 |   letter-spacing: 0.14em;
 180 |   text-transform: uppercase;
 181 |   color: #95a0ba;
 182 | }
 183 | 
 184 | .comp-score {
 185 |   font-family: 'JetBrains Mono', monospace;
 186 |   font-size: 11px;
 187 |   font-weight: 800;
 188 |   color: #f8c15c;
 189 | }
 190 | 
 191 | .comp-bar-track {
 192 |   height: 4px;
 193 |   background: rgba(255,255,255,0.06);
 194 |   border-radius: 2px;
 195 |   overflow: hidden;
 196 | }
 197 | 
 198 | .comp-bar-fill {
 199 |   height: 100%;
 200 |   border-radius: 2px;
 201 |   transition: width 0.8s ease;
 202 | }
 203 | 
 204 | .comp-desc {
 205 |   font-size: 10px;
 206 |   color: #95a0ba;
 207 |   font-family: 'JetBrains Mono', monospace;
 208 | }
 209 | 
 210 | /* ── Stat pills ── */
 211 | .stat-pill {
 212 |   display: flex;
 213 |   flex-direction: column;
 214 |   align-items: center;
 215 |   padding: 16px;
 216 |   background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015));
 217 |   border: 1px solid rgba(255,255,255,0.06);
 218 |   border-radius: 12px;
 219 |   flex: 1;
 220 |   min-width: 100px;
 221 |   backdrop-filter: blur(8px);
 222 |   -webkit-backdrop-filter: blur(8px);
 223 |   box-shadow: 0 4px 12px rgba(0,0,0,0.18);
 224 | }
 225 | 
 226 | .stat-pill-value {
 227 |   font-family: 'JetBrains Mono', monospace;
 228 |   font-size: 1.6rem;
 229 |   font-weight: 900;
 230 |   color: #f8c15c;
 231 |   letter-spacing: -0.03em;
 232 |   line-height: 1;
 233 | }
 234 | 
 235 | .stat-pill-label {
 236 |   font-family: 'JetBrains Mono', monospace;
 237 |   font-size: 9px;
 238 |   font-weight: 800;
 239 |   letter-spacing: 0.16em;
 240 |   text-transform: uppercase;
 241 |   color: #95a0ba;
 242 |   margin-top: 4px;
 243 | }
 244 | 
 245 | /* ── Fear & Greed widget ── */
 246 | .fg-wrap { text-align: center; }
 247 | 
 248 | .fg-value {
 249 |   font-family: 'JetBrains Mono', monospace;
 250 |   font-size: 3.5rem;
 251 |   font-weight: 900;
 252 |   letter-spacing: -0.04em;
 253 |   line-height: 1;
 254 | }
 255 | 
 256 | .fg-label {
 257 |   font-family: 'JetBrains Mono', monospace;
 258 |   font-size: 11px;
 259 |   font-weight: 800;
 260 |   letter-spacing: 0.16em;
 261 |   text-transform: uppercase;
 262 |   margin-top: 6px;
 263 | }
 264 | 
 265 | .fg-history {
 266 |   display: flex;
 267 |   gap: 4px;
 268 |   margin-top: 16px;
 269 |   align-items: flex-end;
 270 |   justify-content: center;
 271 |   height: 40px;
 272 | }
 273 | 
 274 | .fg-bar {
 275 |   width: 24px;
 276 |   border-radius: 2px 2px 0 0;
 277 |   min-height: 4px;
 278 |   transition: height 0.5s ease;
 279 | }
 280 | 
 281 | /* ── Narrative timeline ── */
 282 | .narr-timeline {
 283 |   display: flex;
 284 |   flex-direction: column;
 285 |   gap: 0;
 286 | }
 287 | 
 288 | .narr-day {
 289 |   display: grid;
 290 |   grid-template-columns: 60px 1fr auto;
 291 |   gap: 12px;
 292 |   align-items: center;
 293 |   padding: 10px 0;
 294 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 295 | }
 296 | 
 297 | .narr-day:last-child { border-bottom: none; }
 298 | 
 299 | .narr-date {
 300 |   font-family: 'JetBrains Mono', monospace;
 301 |   font-size: 10px;
 302 |   color: #95a0ba;
 303 |   font-weight: 700;
 304 | }
 305 | 
 306 | .narr-narrative {
 307 |   font-size: 12px;
 308 |   color: #eef2ff;
 309 |   font-weight: 600;
 310 | }
 311 | 
 312 | .narr-score {
 313 |   font-family: 'JetBrains Mono', monospace;
 314 |   font-size: 12px;
 315 |   font-weight: 800;
 316 |   min-width: 32px;
 317 |   text-align: right;
 318 | }
 319 | 
 320 | /* ── Topic cloud ── */
 321 | .topic-cloud {
 322 |   display: flex;
 323 |   flex-wrap: wrap;
 324 |   gap: 10px;
 325 |   align-items: center;
 326 |   line-height: 1.6;
 327 | }
 328 | 
 329 | .topic-word {
 330 |   cursor: default;
 331 |   font-family: 'JetBrains Mono', monospace;
 332 |   font-weight: 700;
 333 |   letter-spacing: 0.04em;
 334 |   transition: opacity 0.2s;
 335 |   text-decoration: none;
 336 | }
 337 | 
 338 | .topic-word.bullish { color: #89ffb8; }
 339 | .topic-word.bearish { color: #ff8ba0; }
 340 | .topic-word.neutral { color: #eef2ff; }
 341 | .topic-word:hover { opacity: 0.7; }
 342 | 
 343 | /* ── Entity table ── */
 344 | .entity-table {
 345 |   width: 100%;
 346 |   border-collapse: collapse;
 347 | }
 348 | 
 349 | .entity-table th {
 350 |   font-family: 'JetBrains Mono', monospace;
 351 |   font-size: 9px;
 352 |   font-weight: 800;
 353 |   letter-spacing: 0.14em;
 354 |   text-transform: uppercase;
 355 |   color: #95a0ba;
 356 |   padding: 8px 12px;
 357 |   border-bottom: 1px solid rgba(255,255,255,0.06);
 358 |   text-align: left;
 359 | }
 360 | 
 361 | .entity-table td {
 362 |   padding: 10px 12px;
 363 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 364 |   font-size: 13px;
 365 |   color: #eef2ff;
 366 |   vertical-align: middle;
 367 | }
 368 | 
 369 | .entity-table tr:last-child td { border-bottom: none; }
 370 | 
 371 | .entity-type {
 372 |   font-family: 'JetBrains Mono', monospace;
 373 |   font-size: 9px;
 374 |   font-weight: 700;
 375 |   text-transform: uppercase;
 376 |   letter-spacing: 0.12em;
 377 |   padding: 2px 6px;
 378 |   border-radius: 4px;
 379 |   background: rgba(93,228,255,0.08);
 380 |   color: #5de4ff;
 381 | }
 382 | 
 383 | /* ── Event list ── */
 384 | .evt-item {
 385 |   display: flex;
 386 |   gap: 12px;
 387 |   padding: 12px 0;
 388 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 389 |   align-items: flex-start;
 390 | }
 391 | 
 392 | .evt-item:last-child { border-bottom: none; }
 393 | 
 394 | .evt-badge {
 395 |   font-family: 'JetBrains Mono', monospace;
 396 |   font-size: 9px;
 397 |   font-weight: 800;
 398 |   letter-spacing: 0.10em;
 399 |   text-transform: uppercase;
 400 |   padding: 3px 7px;
 401 |   border-radius: 4px;
 402 |   flex-shrink: 0;
 403 |   margin-top: 1px;
 404 | }
 405 | 
 406 | .evt-badge.critical { background: rgba(255,59,95,0.15); color: #ff8ba0; }
 407 | .evt-badge.warning  { background: rgba(248,193,92,0.12); color: #f8c15c; }
 408 | .evt-badge.info     { background: rgba(93,228,255,0.10); color: #5de4ff; }
 409 | 
 410 | /* ── Article stream ── */
 411 | .art-stream-item {
 412 |   display: grid;
 413 |   grid-template-columns: 28px 1fr auto;
 414 |   gap: 12px;
 415 |   padding: 10px 0;
 416 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 417 |   align-items: start;
 418 | }
 419 | 
 420 | .art-stream-item:last-child { border-bottom: none; }
 421 | 
 422 | .art-rank {
 423 |   font-family: 'JetBrains Mono', monospace;
 424 |   font-size: 10px;
 425 |   font-weight: 700;
 426 |   color: #95a0ba;
 427 |   padding-top: 2px;
 428 | }
 429 | 
 430 | .art-title {
 431 |   font-size: 13px;
 432 |   font-weight: 600;
 433 |   color: #eef2ff;
 434 |   line-height: 1.4;
 435 |   margin-bottom: 3px;
 436 | }
 437 | 
 438 | .art-meta {
 439 |   display: flex;
 440 |   gap: 6px;
 441 |   flex-wrap: wrap;
 442 |   align-items: center;
 443 | }
 444 | 
 445 | .art-imp {
 446 |   font-family: 'JetBrains Mono', monospace;
 447 |   font-size: 1rem;
 448 |   font-weight: 900;
 449 |   text-align: right;
 450 | }
 451 | 
 452 | /* ── Badges ── */
 453 | .s-badge {
 454 |   display: inline-flex;
 455 |   align-items: center;
 456 |   gap: 4px;
 457 |   padding: 2px 8px;
 458 |   border-radius: 999px;
 459 |   font-family: 'JetBrains Mono', monospace;
 460 |   font-size: 9px;
 461 |   font-weight: 800;
 462 |   letter-spacing: 0.10em;
 463 |   text-transform: uppercase;
 464 | }
 465 | 
 466 | .s-badge.bullish { background: rgba(137,255,184,0.10); color: #89ffb8; }
 467 | .s-badge.bearish { background: rgba(255,139,160,0.10); color: #ff8ba0; }
 468 | .s-badge.neutral { background: rgba(248,193,92,0.10); color: #f8c15c; }
 469 | .s-badge.unclassified { background: rgba(149,160,186,0.08); color: #95a0ba; }
 470 | 
 471 | .narr-chip {
 472 |   font-family: 'JetBrains Mono', monospace;
 473 |   font-size: 9px;
 474 |   font-weight: 700;
 475 |   letter-spacing: 0.08em;
 476 |   text-transform: uppercase;
 477 |   color: #95a0ba;
 478 |   background: rgba(149,160,186,0.07);
 479 |   border-radius: 4px;
 480 |   padding: 2px 5px;
 481 | }
 482 | 
 483 | /* ═══════════════════════════════════════════════════════════════════
 484 |    A. SOVEREIGN SIGNAL MATRIX — Radar Chart
 485 |    ═══════════════════════════════════════════════════════════════════ */
 486 | .radar-container {
 487 |   position: relative;
 488 |   width: 100%;
 489 |   max-width: 320px;
 490 |   margin: 0 auto;
 491 | }
 492 | 
 493 | .radar-container canvas {
 494 |   width: 100% !important;
 495 |   height: auto !important;
 496 | }
 497 | 
 498 | .radar-composite {
 499 |   text-align: center;
 500 |   margin-top: 12px;
 501 | }
 502 | 
 503 | .radar-composite-num {
 504 |   font-family: 'JetBrains Mono', monospace;
 505 |   font-size: 2rem;
 506 |   font-weight: 900;
 507 |   letter-spacing: -0.04em;
 508 | }
 509 | 
 510 | .radar-composite-label {
 511 |   font-family: 'JetBrains Mono', monospace;
 512 |   font-size: 10px;
 513 |   font-weight: 800;
 514 |   letter-spacing: 0.14em;
 515 |   text-transform: uppercase;
 516 |   color: #95a0ba;
 517 |   margin-top: 2px;
 518 | }
 519 | 
 520 | /* ═══════════════════════════════════════════════════════════════════
 521 |    B. POLYMARKET PANEL
 522 |    ═══════════════════════════════════════════════════════════════════ */
 523 | .poly-market {
 524 |   padding: 12px 0;
 525 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 526 | }
 527 | 
 528 | .poly-market:last-child { border-bottom: none; }
 529 | 
 530 | .poly-question {
 531 |   font-size: 12px;
 532 |   color: #eef2ff;
 533 |   font-weight: 600;
 534 |   line-height: 1.4;
 535 |   margin-bottom: 8px;
 536 | }
 537 | 
 538 | .poly-bar-wrap {
 539 |   display: flex;
 540 |   height: 24px;
 541 |   border-radius: 4px;
 542 |   overflow: hidden;
 543 |   background: rgba(255,255,255,0.04);
 544 | }
 545 | 
 546 | .poly-bar-yes {
 547 |   background: rgba(137,255,184,0.25);
 548 |   display: flex;
 549 |   align-items: center;
 550 |   justify-content: center;
 551 |   font-family: 'JetBrains Mono', monospace;
 552 |   font-size: 10px;
 553 |   font-weight: 800;
 554 |   color: #89ffb8;
 555 |   min-width: 36px;
 556 |   transition: width 0.8s ease;
 557 | }
 558 | 
 559 | .poly-bar-no {
 560 |   background: rgba(255,139,160,0.15);
 561 |   display: flex;
 562 |   align-items: center;
 563 |   justify-content: center;
 564 |   font-family: 'JetBrains Mono', monospace;
 565 |   font-size: 10px;
 566 |   font-weight: 800;
 567 |   color: #ff8ba0;
 568 |   min-width: 36px;
 569 |   flex: 1;
 570 | }
 571 | 
 572 | .poly-meta {
 573 |   display: flex;
 574 |   gap: 12px;
 575 |   margin-top: 6px;
 576 |   font-family: 'JetBrains Mono', monospace;
 577 |   font-size: 9px;
 578 |   font-weight: 700;
 579 |   color: #95a0ba;
 580 |   letter-spacing: 0.08em;
 581 | }
 582 | 
 583 | /* ═══════════════════════════════════════════════════════════════════
 584 |    C. DIVERGENCE ALERTS
 585 |    ═══════════════════════════════════════════════════════════════════ */
 586 | .divergence-alert {
 587 |   padding: 14px;
 588 |   border-radius: 10px;
 589 |   margin-bottom: 10px;
 590 |   border-left: 3px solid;
 591 | }
 592 | 
 593 | .divergence-alert.bullish {
 594 |   background: rgba(137,255,184,0.05);
 595 |   border-color: #89ffb8;
 596 | }
 597 | 
 598 | .divergence-alert.bearish {
 599 |   background: rgba(255,139,160,0.05);
 600 |   border-color: #ff8ba0;
 601 | }
 602 | 
 603 | .divergence-alert.mixed {
 604 |   background: rgba(248,193,92,0.05);
 605 |   border-color: #f8c15c;
 606 | }
 607 | 
 608 | .divergence-title {
 609 |   font-family: 'JetBrains Mono', monospace;
 610 |   font-size: 11px;
 611 |   font-weight: 800;
 612 |   letter-spacing: 0.10em;
 613 |   text-transform: uppercase;
 614 |   margin-bottom: 6px;
 615 | }
 616 | 
 617 | .divergence-detail {
 618 |   font-size: 12px;
 619 |   color: #95a0ba;
 620 |   line-height: 1.5;
 621 |   margin-bottom: 6px;
 622 | }
 623 | 
 624 | .divergence-accuracy {
 625 |   font-family: 'JetBrains Mono', monospace;
 626 |   font-size: 10px;
 627 |   font-weight: 700;
 628 |   color: #f8c15c;
 629 | }
 630 | 
 631 | /* ═══════════════════════════════════════════════════════════════════
 632 |    D. WHALE FEED
 633 |    ═══════════════════════════════════════════════════════════════════ */
 634 | .whale-item {
 635 |   display: flex;
 636 |   gap: 10px;
 637 |   padding: 10px 0;
 638 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 639 |   align-items: flex-start;
 640 | }
 641 | 
 642 | .whale-item:last-child { border-bottom: none; }
 643 | 
 644 | .whale-tier {
 645 |   font-family: 'JetBrains Mono', monospace;
 646 |   font-size: 8px;
 647 |   font-weight: 800;
 648 |   letter-spacing: 0.10em;
 649 |   text-transform: uppercase;
 650 |   padding: 2px 6px;
 651 |   border-radius: 4px;
 652 |   flex-shrink: 0;
 653 | }
 654 | 
 655 | .whale-tier.critical {
 656 |   background: rgba(255,59,95,0.15);
 657 |   color: #ff3b5f;
 658 |   animation: pulse-critical 2s ease-in-out infinite;
 659 | }
 660 | 
 661 | .whale-tier.alert { background: rgba(248,193,92,0.12); color: #f8c15c; }
 662 | .whale-tier.note { background: rgba(149,160,186,0.08); color: #95a0ba; }
 663 | 
 664 | @keyframes pulse-critical {
 665 |   0%, 100% { box-shadow: 0 0 0 0 rgba(255,59,95,0); }
 666 |   50% { box-shadow: 0 0 12px 2px rgba(255,59,95,0.3); }
 667 | }
 668 | 
 669 | .whale-msg {
 670 |   font-size: 12px;
 671 |   color: #eef2ff;
 672 |   line-height: 1.4;
 673 | }
 674 | 
 675 | .whale-time {
 676 |   font-family: 'JetBrains Mono', monospace;
 677 |   font-size: 9px;
 678 |   color: #95a0ba;
 679 |   margin-top: 3px;
 680 | }
 681 | 
 682 | /* ═══════════════════════════════════════════════════════════════════
 683 |    E. ALGORITHMIC SIGNAL SCORE
 684 |    ═══════════════════════════════════════════════════════════════════ */
 685 | .algo-score-wrap {
 686 |   text-align: center;
 687 |   padding: 16px 0;
 688 | }
 689 | 
 690 | .algo-big-num {
 691 |   font-family: 'JetBrains Mono', monospace;
 692 |   font-size: 4.5rem;
 693 |   font-weight: 900;
 694 |   letter-spacing: -0.05em;
 695 |   line-height: 1;
 696 |   transition: color 0.5s ease;
 697 | }
 698 | 
 699 | .algo-trend-arrow {
 700 |   font-size: 2rem;
 701 |   display: inline-block;
 702 |   margin-left: 8px;
 703 |   vertical-align: middle;
 704 | }
 705 | 
 706 | .algo-sub-label {
 707 |   font-family: 'JetBrains Mono', monospace;
 708 |   font-size: 12px;
 709 |   font-weight: 800;
 710 |   letter-spacing: 0.16em;
 711 |   text-transform: uppercase;
 712 |   margin-top: 4px;
 713 | }
 714 | 
 715 | .algo-subscore {
 716 |   display: flex;
 717 |   justify-content: space-between;
 718 |   align-items: center;
 719 |   padding: 8px 0;
 720 |   border-bottom: 1px solid rgba(255,255,255,0.04);
 721 |   cursor: pointer;
 722 | }
 723 | 
 724 | .algo-subscore:last-child { border-bottom: none; }
 725 | 
 726 | .algo-subscore-label {
 727 |   font-family: 'JetBrains Mono', monospace;
 728 |   font-size: 10px;
 729 |   font-weight: 700;
 730 |   letter-spacing: 0.12em;
 731 |   text-transform: uppercase;
 732 |   color: #95a0ba;
 733 | }
 734 | 
 735 | .algo-subscore-val {
 736 |   font-family: 'JetBrains Mono', monospace;
 737 |   font-size: 14px;
 738 |   font-weight: 900;
 739 | }
 740 | 
 741 | .algo-subscore-bar {
 742 |   height: 3px;
 743 |   background: rgba(255,255,255,0.06);
 744 |   border-radius: 2px;
 745 |   overflow: hidden;
 746 |   margin-top: 4px;
 747 | }
 748 | 
 749 | .algo-subscore-fill {
 750 |   height: 100%;
 751 |   border-radius: 2px;
 752 |   transition: width 1s ease;
 753 | }
 754 | 
 755 | /* ═══════════════════════════════════════════════════════════════════
 756 |    F. CLASSIFIED OVERLAY (CSS-only, not JS-removable)
 757 |    ═══════════════════════════════════════════════════════════════════ */
 758 | .classified-gate {
 759 |   position: absolute;
 760 |   inset: 0;
 761 |   z-index: 10;
 762 |   display: flex;
 763 |   flex-direction: column;
 764 |   align-items: center;
 765 |   justify-content: center;
 766 |   backdrop-filter: blur(12px);
 767 |   -webkit-backdrop-filter: blur(12px);
 768 |   background: rgba(6,7,11,0.82);
 769 |   border-radius: 16px;
 770 | }
 771 | 
 772 | .classified-gate::before {
 773 |   content: 'CLASSIFIED';
 774 |   font-family: 'JetBrains Mono', monospace;
 775 |   font-size: 14px;
 776 |   font-weight: 900;
 777 |   letter-spacing: 0.30em;
 778 |   color: #ff3b5f;
 779 |   margin-bottom: 12px;
 780 | }
 781 | 
 782 | .classified-cta {
 783 |   display: inline-block;
 784 |   font-family: 'JetBrains Mono', monospace;
 785 |   font-size: 11px;
 786 |   font-weight: 800;
 787 |   letter-spacing: 0.12em;
 788 |   text-transform: uppercase;
 789 |   color: #06070b;
 790 |   background: #f8c15c;
 791 |   padding: 10px 24px;
 792 |   border-radius: 8px;
 793 |   text-decoration: none;
 794 |   transition: background 0.2s;
 795 | }
 796 | 
 797 | .classified-cta:hover {
 798 |   background: #ffd47a;
 799 |   color: #06070b;
 800 |   text-decoration: none;
 801 | }
 802 | 
 803 | .classified-teaser {
 804 |   font-family: 'JetBrains Mono', monospace;
 805 |   font-size: 10px;
 806 |   color: #95a0ba;
 807 |   margin-top: 8px;
 808 |   letter-spacing: 0.08em;
 809 | }
 810 | 
 811 | /* ── Responsive ── */
 812 | @media (max-width: 768px) {
 813 |   .intel-headline { font-size: 1.6rem; }
 814 |   .signal-composite { font-size: 3rem; }
 815 |   .algo-big-num { font-size: 2.5rem; }
 816 |   .intel-page { padding: 80px 12px 60px; }
 817 |   .radar-container { max-width: 220px; }
 818 |   .g-card { padding: 18px; }
 819 |   .g-eyebrow { font-size: 8px; margin-bottom: 10px; }
 820 |   .stat-pill { min-width: 70px; padding: 10px 8px; }
 821 |   .stat-pill-value { font-size: 1.2rem; }
 822 |   .fg-value { font-size: 2.5rem; }
 823 |   .entity-table { font-size: 10px; }
 824 |   .classified-gate::before { font-size: 10px; }
 825 |   .poly-card { padding: 10px; }
 826 |   .whale-item { padding: 8px; }
 827 | }
 828 | 
 829 | @media (max-width: 480px) {
 830 |   .intel-page { padding: 70px 8px 50px; }
 831 |   .intel-headline { font-size: 1.3rem; }
 832 |   .stat-pill { min-width: 60px; padding: 8px 6px; }
 833 |   .stat-pill-value { font-size: 1rem; }
 834 |   .signal-composite { font-size: 2.5rem; }
 835 | }
 836 | 
 837 | @media (max-width: 1200px) {
 838 |   .intel-container { max-width: 100%; }
 839 | }
 840 | </style>
 841 | {% endblock %}
 842 | 
 843 | {% block content %}
 844 | <div class="intel-page">
 845 | <div class="intel-container">
 846 | 
 847 |   <!-- Header -->
 848 |   <div class="mb-4">
 849 |     <div class="intel-eyebrow">SOVEREIGN INTELLIGENCE • PREMIUM COMMAND CENTER</div>
 850 |     <h1 class="intel-headline">Bitcoin Intelligence Dashboard</h1>
 851 |     <p style="color:#95a0ba;font-size:0.95rem;">
 852 |       Cross-signal analysis, prediction market odds, whale tracking, algorithmic scoring.
 853 |       <a href="/sentiment" style="color:#f8c15c;text-decoration:none;margin-left:12px;">Sentiment ↗</a>
 854 |       <a href="/terminal" style="color:#f8c15c;text-decoration:none;margin-left:12px;">Terminal ↗</a>
 855 |     </p>
 856 |     <div style="font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#4a5568;margin-top:4px;">
 857 |       For informational purposes only — not financial advice. Past signal performance does not guarantee future results.
 858 |     </div>
 859 |   </div>
 860 | 
 861 |   <!-- Stat Pills Row -->
 862 |   <div class="d-flex gap-3 mb-4 flex-wrap">
 863 |     <div class="stat-pill">
 864 |       {% set ctx_btc = sovereign_ctx.btc if sovereign_ctx and sovereign_ctx.btc else {} %}
 865 |       <div class="stat-pill-value" style="font-size:1.1rem;">
 866 |         ${{ "{:,.0f}".format(ctx_btc.price) if ctx_btc.price else '—' }}
 867 |       </div>
 868 |       <div class="stat-pill-label">BTC Price</div>
 869 |     </div>
 870 |     <div class="stat-pill">
 871 |       {% set ctx_fg = sovereign_ctx.fear_greed if sovereign_ctx and sovereign_ctx.fear_greed else {} %}
 872 |       <div class="stat-pill-value" style="color:{% if ctx_fg.value is defined and ctx_fg.value >= 60 %}#89ffb8{% elif ctx_fg.value is defined and ctx_fg.value <= 35 %}#ff8ba0{% else %}#f8c15c{% endif %};">
 873 |         {{ ctx_fg.value if ctx_fg.value is defined else '—' }}
 874 |       </div>
 875 |       <div class="stat-pill-label">Fear & Greed</div>
 876 |     </div>
 877 |     <div class="stat-pill">
 878 |       {% set ctx_net = sovereign_ctx.network if sovereign_ctx and sovereign_ctx.network else {} %}
 879 |       <div class="stat-pill-value">{{ "{:.0f}".format(ctx_net.hashrate_eh) if ctx_net.hashrate_eh else '—' }}</div>
 880 |       <div class="stat-pill-label">EH/s</div>
 881 |     </div>
 882 |     <div class="stat-pill">
 883 |       {% set ctx_ln = sovereign_ctx.lightning if sovereign_ctx and sovereign_ctx.lightning else {} %}
 884 |       <div class="stat-pill-value" style="font-size:1.1rem;">{{ "{:,.0f}".format(ctx_ln.capacity_btc) if ctx_ln.capacity_btc else '—' }}</div>
 885 |       <div class="stat-pill-label">LN Capacity</div>
 886 |     </div>
 887 |     <div class="stat-pill">
 888 |       {% set ctx_mem = sovereign_ctx.mempool if sovereign_ctx and sovereign_ctx.mempool else {} %}
 889 |       <div class="stat-pill-value">{{ ctx_mem.fee_high if ctx_mem.fee_high else '—' }}</div>
 890 |       <div class="stat-pill-label">sat/vB</div>
 891 |     </div>
 892 |     <div class="stat-pill">
 893 |       <div class="stat-pill-value">{{ sovereign_ctx.block_height if sovereign_ctx and sovereign_ctx.block_height else '—' }}</div>
 894 |       <div class="stat-pill-label">Block</div>
 895 |     </div>
 896 |   </div>
 897 | 
 898 |   <!-- ════════════════════════════════════════════════════════════════
 899 |        ROW 1: Algo Score + Sovereign Signal Matrix + Fear & Greed
 900 |        ════════════════════════════════════════════════════════════════ -->
 901 |   <div class="row g-4 mb-4">
 902 | 
 903 |     <!-- F. ALGORITHMIC SIGNAL SCORE -->
 904 |     <div class="col-lg-3">
 905 |       <div class="g-card accent-red" id="algo-card">
 906 |         <span class="g-eyebrow">Algorithmic Signal Score</span>
 907 |         <div class="algo-score-wrap">
 908 |           <div>
 909 |             <span class="algo-big-num" id="algo-num" style="color:{{ signal.color }};">{{ signal.composite|int }}</span>
 910 |             <span class="algo-trend-arrow" id="algo-arrow" style="color:{{ signal.color }};">
 911 |               {% set traj = signal.trajectory %}
 912 |               {% if 'BULLISH' in traj %}&#9650;{% elif 'BEARISH' in traj %}&#9660;{% else %}&#9654;{% endif %}
 913 |             </span>
 914 |           </div>
 915 |           <div class="algo-sub-label" style="color:{{ signal.color }};">{{ signal.label }}</div>
 916 |         </div>
 917 | 
 918 |         <div style="margin-top:16px;">
 919 |           {% if signal.components %}
 920 |           {% set tech_keys = ['hashrate', 'mempool'] %}
 921 |           {% set chain_keys = ['exchange_flow', 'whale'] %}
 922 |           {% set sent_keys = ['fear_greed', 'kol_sentiment', 'narrative'] %}
 923 | 
 924 |           {% set tech_score = [] %}
 925 |           {% set chain_score = [] %}
 926 |           {% set sent_score = [] %}
 927 | 
 928 |           {% for key, comp in signal.components.items() %}
 929 |             {% set s = comp.score|default(50)|float %}
 930 |             {% if key in tech_keys %}{% if tech_score.append(s) %}{% endif %}
 931 |             {% elif key in chain_keys %}{% if chain_score.append(s) %}{% endif %}
 932 |             {% else %}{% if sent_score.append(s) %}{% endif %}
 933 |             {% endif %}
 934 |           {% endfor %}
 935 | 
 936 |           {% set ts = (tech_score|sum / tech_score|length)|int if tech_score|length > 0 else 50 %}
 937 |           {% set cs = (chain_score|sum / chain_score|length)|int if chain_score|length > 0 else 50 %}
 938 |           {% set ss = (sent_score|sum / sent_score|length)|int if sent_score|length > 0 else 50 %}
 939 | 
 940 |           <div class="algo-subscore">
 941 |             <span class="algo-subscore-label">Technical (40%)</span>
 942 |             <span class="algo-subscore-val" style="color:{% if ts >= 65 %}#89ffb8{% elif ts >= 45 %}#f8c15c{% else %}#ff8ba0{% endif %};">{{ ts }}</span>
 943 |           </div>
 944 |           <div class="algo-subscore-bar">
 945 |             <div class="algo-subscore-fill" style="width:{{ ts }}%;background:{% if ts >= 65 %}#89ffb8{% elif ts >= 45 %}#f8c15c{% else %}#ff8ba0{% endif %};"></div>
 946 |           </div>
 947 | 
 948 |           <div class="algo-subscore" style="margin-top:8px;">
 949 |             <span class="algo-subscore-label">On-Chain (35%)</span>
 950 |             <span class="algo-subscore-val" style="color:{% if cs >= 65 %}#89ffb8{% elif cs >= 45 %}#f8c15c{% else %}#ff8ba0{% endif %};">{{ cs }}</span>
 951 |           </div>
 952 |           <div class="algo-subscore-bar">
 953 |             <div class="algo-subscore-fill" style="width:{{ cs }}%;background:{% if cs >= 65 %}#89ffb8{% elif cs >= 45 %}#f8c15c{% else %}#ff8ba0{% endif %};"></div>
 954 |           </div>
 955 | 
 956 |           <div class="algo-subscore" style="margin-top:8px;">
 957 |             <span class="algo-subscore-label">Sentiment (25%)</span>
 958 |             <span class="algo-subscore-val" style="color:{% if ss >= 65 %}#89ffb8{% elif ss >= 45 %}#f8c15c{% else %}#ff8ba0{% endif %};">{{ ss }}</span>
 959 |           </div>
 960 |           <div class="algo-subscore-bar">
 961 |             <div class="algo-subscore-fill" style="width:{{ ss }}%;background:{% if ss >= 65 %}#89ffb8{% elif ss >= 45 %}#f8c15c{% else %}#ff8ba0{% endif %};"></div>
 962 |           </div>
 963 |           {% else %}
 964 |           <p style="color:#4a5568;font-size:11px;text-align:center;">Loading components...</p>
 965 |           {% endif %}
 966 |         </div>
 967 | 
 968 |         {% if not is_commander %}
 969 |         <div class="classified-gate">
 970 |           <a href="/terminal/checkout" class="classified-cta">Upgrade to Commander — $49/mo</a>
 971 |           <span class="classified-teaser">Full breakdown unlocked</span>
 972 |         </div>
 973 |         {% endif %}
 974 |       </div>
 975 |     </div>
 976 | 
 977 |     <!-- A. SOVEREIGN SIGNAL MATRIX (Radar) -->
 978 |     <div class="col-lg-5">
 979 |       <div class="g-card accent-gold">
 980 |         <span class="g-eyebrow">Sovereign Signal Matrix • PCAF Visual</span>
 981 |         <div class="radar-container">
 982 |           <canvas id="radarChart" width="320" height="320"></canvas>
 983 |         </div>
 984 |         <div class="radar-composite">
 985 |           <span class="radar-composite-num" id="radar-composite" style="color:#f8c15c;">—</span>
 986 |           <div class="radar-composite-label" id="radar-bias">Loading...</div>
 987 |         </div>
 988 |         <!-- Axis legend -->
 989 |         <div class="d-flex flex-wrap gap-2 mt-3 justify-content-center" style="font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;">
 990 |           <span style="color:#89ffb8;">&#9679; Miner</span>
 991 |           <span style="color:#f8c15c;">&#9679; Exchange</span>
 992 |           <span style="color:#5de4ff;">&#9679; Narrative</span>
 993 |           <span style="color:#ff8ba0;">&#9679; On-Chain</span>
 994 |           <span style="color:#eef2ff;">&#9679; Lightning</span>
 995 |           <span style="color:#ff3b5f;">&#9679; Market</span>
 996 |         </div>
 997 | 
 998 |         <!-- Proprietary Indices (from sovereign context engine) -->
 999 |         {% set indices = sovereign_ctx.indices if sovereign_ctx and sovereign_ctx.indices else {} %}
1000 |         {% if indices %}
1001 |         <div style="margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.06);">
1002 |           <span class="g-eyebrow" style="font-size:8px;">Protocol Pulse Indices</span>
1003 |           {% set mc = indices.get('miner_conviction', {}) %}
1004 |           {% set ep = indices.get('exchange_pressure', {}) %}
1005 |           {% set sd = indices.get('social_divergence', {}) %}
1006 | 
1007 |           <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
1008 |             <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:#95a0ba;">MINER CONVICTION</span>
1009 |             <span style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:900;color:{% if mc.signal == 'bullish' %}#89ffb8{% elif mc.signal == 'bearish' %}#ff8ba0{% else %}#f8c15c{% endif %};">{{ mc.score|default('—') }}</span>
1010 |           </div>
1011 |           <div style="font-size:9px;color:#4a5568;padding:3px 0 6px;font-family:'JetBrains Mono',monospace;">{{ mc.interpretation|default('') }}</div>
1012 | 
1013 |           <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
1014 |             <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:#95a0ba;">EXCHANGE PRESSURE</span>
1015 |             <span style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:900;color:{% if ep.signal == 'bullish' %}#89ffb8{% elif ep.signal == 'bearish' %}#ff8ba0{% else %}#f8c15c{% endif %};">{{ ep.score|default('0') }}</span>
1016 |           </div>
1017 |           <div style="font-size:9px;color:#4a5568;padding:3px 0 6px;font-family:'JetBrains Mono',monospace;">{{ ep.interpretation|default('') }}</div>
1018 | 
1019 |           <div style="display:flex;justify-content:space-between;padding:6px 0;">
1020 |             <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:#95a0ba;">SOCIAL DIVERGENCE</span>
1021 |             <span style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:900;color:{% if sd.signal == 'bullish' %}#89ffb8{% elif sd.signal == 'bearish' %}#ff8ba0{% else %}#f8c15c{% endif %};">{{ sd.score|default('0') }}</span>
1022 |           </div>
1023 |           <div style="font-size:9px;color:#4a5568;padding:3px 0;font-family:'JetBrains Mono',monospace;">{{ sd.interpretation|default('') }}</div>
1024 |         </div>
1025 |         {% endif %}
1026 |       </div>
1027 |     </div>
1028 | 
1029 |     <!-- Fear & Greed + Narrative Timeline -->
1030 |     <div class="col-lg-4">
1031 |       <div class="row g-4">
1032 |         <!-- Fear & Greed -->
1033 |         <div class="col-12">
1034 |           <div class="g-card accent-gold text-center">
1035 |             <span class="g-eyebrow">Fear & Greed</span>
1036 |             {% if ctx_fg %}
1037 |             <div class="fg-wrap">
1038 |               <div class="fg-value"
1039 |                    style="color:{% if ctx_fg.value is defined and ctx_fg.value >= 75 %}#5de4ff{% elif ctx_fg.value is defined and ctx_fg.value >= 55 %}#89ffb8{% elif ctx_fg.value is defined and ctx_fg.value >= 45 %}#f8c15c{% elif ctx_fg.value is defined and ctx_fg.value >= 25 %}#ff8ba0{% else %}#ff3b5f{% endif %};">
1040 |                 {{ ctx_fg.value if ctx_fg.value is defined else '—' }}
1041 |               </div>
1042 |               <div class="fg-label"
1043 |                    style="color:{% if ctx_fg.value is defined and ctx_fg.value >= 75 %}#5de4ff{% elif ctx_fg.value is defined and ctx_fg.value >= 55 %}#89ffb8{% elif ctx_fg.value is defined and ctx_fg.value >= 45 %}#f8c15c{% elif ctx_fg.value is defined and ctx_fg.value >= 25 %}#ff8ba0{% else %}#ff3b5f{% endif %};">
1044 |                 {{ ctx_fg.label if ctx_fg.label is defined else 'Loading' }}
1045 |               </div>
1046 |             </div>
1047 |             {% else %}
1048 |             <div class="fg-wrap" style="padding:20px 0;">
1049 |               <div class="fg-value" style="color:#95a0ba;">—</div>
1050 |               <div class="fg-label" style="color:#4a5568;">Loading…</div>
1051 |             </div>
1052 |             {% endif %}
1053 |           </div>
1054 |         </div>
1055 | 
1056 |         <!-- 7-Day Narrative -->
1057 |         <div class="col-12">
1058 |           <div class="g-card">
1059 |             <span class="g-eyebrow">7-Day Narrative Timeline</span>
1060 |             <div class="narr-timeline">
1061 |               {% if narrative_timeline %}
1062 |               {% for day in narrative_timeline %}
1063 |               {% set sc = day.score|float %}
1064 |               <div class="narr-day">
1065 |                 <span class="narr-date">{{ day.date }}</span>
1066 |                 <span class="narr-narrative">{{ day.dominant_narrative }}</span>
1067 |                 <span class="narr-score"
1068 |                       style="color:{% if sc >= 60 %}#89ffb8{% elif sc <= 40 %}#ff8ba0{% else %}#f8c15c{% endif %};">
1069 |                   {{ sc|int }}
1070 |                 </span>
1071 |               </div>
1072 |               {% endfor %}
1073 |               {% else %}
1074 |               <p class="text-muted small">No narrative data yet.</p>
1075 |               {% endif %}
1076 |             </div>
1077 |           </div>
1078 |         </div>
1079 |       </div>
1080 |     </div>
1081 |   </div>
1082 | 
1083 |   <!-- ════════════════════════════════════════════════════════════════
1084 |        ROW 2: Cross-Signal Divergence + Polymarket Intelligence
1085 |        ════════════════════════════════════════════════════════════════ -->
1086 |   <div class="row g-4 mb-4">
1087 | 
1088 |     <!-- C. CROSS-SIGNAL DIVERGENCE ENGINE -->
1089 |     <div class="col-lg-5">
1090 |       <div class="g-card accent-red" id="divergence-card" style="position:relative;">
1091 |         <span class="g-eyebrow">Cross-Signal Divergence Engine</span>
1092 |         <div id="divergence-alerts">
1093 |           <!-- Populated by JS from sovereign context -->
1094 |         </div>
1095 | 
1096 |         {% if not is_commander %}
1097 |         <div class="classified-gate">
1098 |           <a href="/terminal/checkout" class="classified-cta">Upgrade to Commander — $49/mo</a>
1099 |           <span class="classified-teaser">3 active divergences detected</span>
1100 |         </div>
1101 |         {% endif %}
1102 |       </div>
1103 |     </div>
1104 | 
1105 |     <!-- B. POLYMARKET INTELLIGENCE PANEL -->
1106 |     <div class="col-lg-7">
1107 |       <div class="g-card accent-cyan" id="polymarket-card" style="position:relative;">
1108 |         <div class="d-flex align-items-center justify-content-between mb-3">
1109 |           <span class="g-eyebrow" style="margin-bottom:0;">Polymarket Intelligence</span>
1110 |           <span style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:800;letter-spacing:0.12em;color:#5de4ff;">
1111 |             MACRO SCORE: <span id="poly-macro">{{ polymarket_sentiment }}</span>/100
1112 |           </span>
1113 |         </div>
1114 |         <div id="polymarket-list">
1115 |           {% if polymarket_markets %}
1116 |           {% for m in polymarket_markets %}
1117 |           <div class="poly-market">
1118 |             <div class="poly-question">{{ m.question }}</div>
1119 |             {% set yes = m.outcomes.get('Yes', 50) if m.outcomes else 50 %}
1120 |             {% set no = m.outcomes.get('No', 50) if m.outcomes else 50 %}
1121 |             <div class="poly-bar-wrap">
1122 |               <div class="poly-bar-yes" style="width:{{ yes }}%;">YES {{ yes }}%</div>
1123 |               <div class="poly-bar-no">NO {{ no }}%</div>
1124 |             </div>
1125 |             <div class="poly-meta">
1126 |               <span>VOL ${{ "{:,.0f}".format(m.volume) if m.volume else '0' }}</span>
1127 |               <span>LIQ ${{ "{:,.0f}".format(m.liquidity) if m.liquidity else '0' }}</span>
1128 |             </div>
1129 |           </div>
1130 |           {% endfor %}
1131 |           {% else %}
1132 |           <p style="color:#4a5568;font-size:12px;text-align:center;padding:24px 0;">No active Polymarket data.</p>
1133 |           {% endif %}
1134 |         </div>
1135 | 
1136 |         {% if not is_commander %}
1137 |         <div class="classified-gate">
1138 |           <a href="/terminal/checkout" class="classified-cta">Upgrade to Commander — $49/mo</a>
1139 |           <span class="classified-teaser">1 of 5 markets shown free</span>
1140 |         </div>
1141 |         {% endif %}
1142 |       </div>
1143 |     </div>
1144 |   </div>
1145 | 
1146 |   <!-- ════════════════════════════════════════════════════════════════
1147 |        ROW 3: Whale Feed + Narrative Momentum
1148 |        ════════════════════════════════════════════════════════════════ -->
1149 |   <div class="row g-4 mb-4">
1150 | 
1151 |     <!-- E. WHALE INTELLIGENCE FEED -->
1152 |     <div class="col-lg-4">
1153 |       <div class="g-card accent-red" id="whale-card" style="position:relative;">
1154 |         <span class="g-eyebrow">Whale Intelligence Feed</span>
1155 |         <div id="whale-feed">
1156 |           {% set whales = sovereign_ctx.whale_alerts if sovereign_ctx and sovereign_ctx.whale_alerts else [] %}
1157 |           {% if whales %}
1158 |           {% for w in whales %}
1159 |           <div class="whale-item">
1160 |             <span class="whale-tier {{ w.tier|lower }}">{{ w.tier }}</span>
1161 |             <div>
1162 |               <div class="whale-msg">{{ w.message }}</div>
1163 |               <div class="whale-time">{{ w.rule }} • Score {{ w.score }}</div>
1164 |             </div>
1165 |           </div>
1166 |           {% endfor %}
1167 |           {% else %}
1168 |           <div style="text-align:center;padding:24px 0;">
1169 |             <div style="color:#95a0ba;font-size:28px;margin-bottom:8px;">&#128011;</div>
1170 |             <div style="color:#95a0ba;font-size:13px;">No whale activity detected.</div>
1171 |           </div>
1172 |           {% endif %}
1173 | 
1174 |           <!-- Cross-reference signal -->
1175 |           {% if ctx_fg.value is defined and ctx_fg.value < 25 and whales|length > 0 %}
1176 |           <div style="margin-top:12px;padding:10px;border-radius:8px;background:rgba(137,255,184,0.06);border:1px solid rgba(137,255,184,0.15);">
1177 |             <div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:800;letter-spacing:0.12em;color:#89ffb8;">CROSS-REFERENCE: BULLISH</div>
1178 |             <div style="font-size:11px;color:#95a0ba;margin-top:4px;">Whale accumulation + F&G {{ ctx_fg.value }} = historically strong buy signal</div>
1179 |           </div>
1180 |           {% endif %}
1181 |         </div>
1182 | 
1183 |         {% if not is_commander %}
1184 |         <div class="classified-gate">
1185 |           <a href="/terminal/checkout" class="classified-cta">Upgrade to Commander — $49/mo</a>
1186 |           <span class="classified-teaser">Real-time whale tracking</span>
1187 |         </div>
1188 |         {% endif %}
1189 |       </div>
1190 |     </div>
1191 | 
1192 |     <!-- D. NARRATIVE MOMENTUM TRACKER -->
1193 |     <div class="col-lg-4">
1194 |       <div class="g-card">
1195 |         <span class="g-eyebrow">Narrative Momentum Tracker</span>
1196 |         <div id="narrative-momentum">
1197 |           <!-- Populated by JS -->
1198 |           <p style="color:#4a5568;font-size:11px;text-align:center;padding:20px 0;">Loading narrative data...</p>
1199 |         </div>
1200 |       </div>
1201 |     </div>
1202 | 
1203 |     <!-- Intelligence Events -->
1204 |     <div class="col-lg-4">
1205 |       <div class="g-card accent-red">
1206 |         <span class="g-eyebrow">Intelligence Events</span>
1207 |         {% if intel_events %}
1208 |         {% for evt in intel_events %}
1209 |         <div class="evt-item">
1210 |           <span class="evt-badge {{ evt.severity }}">{{ evt.severity }}</span>
1211 |           <div>
1212 |             <div style="font-size:12px;color:#eef2ff;line-height:1.4;margin-bottom:4px;">{{ evt.description|truncate(140) }}</div>
1213 |             <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#4a5568;">
1214 |               {{ evt.event_type|replace('_', ' ')|upper }} • {{ evt.created_at }}</div>
1215 |           </div>
1216 |         </div>
1217 |         {% endfor %}
1218 |         {% else %}
1219 |         <div class="text-center py-4">
1220 |           <div style="color:#95a0ba;font-size:28px;margin-bottom:8px;">&#10003;</div>
1221 |           <div style="color:#95a0ba;font-size:13px;">No anomalies detected.</div>
1222 |           <div style="color:#4a5568;font-size:11px;margin-top:4px;">All signals within normal range.</div>
1223 |         </div>
1224 |         {% endif %}
1225 |       </div>
1226 |     </div>
1227 |   </div>
1228 | 
1229 |   <!-- ════════════════════════════════════════════════════════════════
1230 |        ROW 4: Topic Cloud + Entity Tracker
1231 |        ════════════════════════════════════════════════════════════════ -->
1232 |   <div class="row g-4 mb-4">
1233 |     <!-- Trending Topics Cloud -->
1234 |     <div class="col-lg-5">
1235 |       <div class="g-card accent-cyan">
1236 |         <span class="g-eyebrow">Trending Topics (24h)</span>
1237 |         {% if trending %}
1238 |         <div class="topic-cloud">
1239 |           {% for topic in trending %}
1240 |           <span class="topic-word {{ topic.sentiment }}"
1241 |                 style="font-size:{{ topic.size }}px;"
1242 |                 title="{{ topic.count }} articles — {{ topic.sentiment }}">
1243 |             {{ topic.topic }}
1244 |           </span>
1245 |           {% endfor %}
1246 |         </div>
1247 |         <div class="mt-3 d-flex gap-3" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;">
1248 |           <span style="color:#89ffb8;">&#9679; Bullish</span>
1249 |           <span style="color:#ff8ba0;">&#9679; Bearish</span>
1250 |           <span style="color:#eef2ff;">&#9679; Neutral</span>
1251 |         </div>
1252 |         {% else %}
1253 |         <p class="text-muted small">No trending topics data.</p>
1254 |         {% endif %}
1255 |       </div>
1256 |     </div>
1257 | 
1258 |     <!-- Entity Tracker -->
1259 |     <div class="col-lg-7">
1260 |       <div class="g-card">
1261 |         <span class="g-eyebrow">Entity Tracker (48h)</span>
1262 |         {% if entities %}
1263 |         <div style="overflow-x:auto;">
1264 |           <table class="entity-table">
1265 |             <thead>
1266 |               <tr>
1267 |                 <th>Entity</th>
1268 |                 <th>Type</th>
1269 |                 <th>Mentions</th>
1270 |                 <th>Sentiment</th>
1271 |                 <th>Trend</th>
1272 |               </tr>
1273 |             </thead>
1274 |             <tbody>
1275 |               {% for ent in entities[:12] %}
1276 |               <tr>
1277 |                 <td style="font-weight:600;">{{ ent.entity }}</td>
1278 |                 <td><span class="entity-type">{{ ent.type }}</span></td>
1279 |                 <td style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f8c15c;">{{ ent.mention_count }}</td>
1280 |                 <td>
1281 |                   <span class="s-badge {{ ent.sentiment }}">
1282 |                     {% if ent.sentiment == 'bullish' %}&#9650;{% elif ent.sentiment == 'bearish' %}&#9660;{% else %}&#9679;{% endif %}
1283 |                     {{ ent.sentiment }}
1284 |                   </span>
1285 |                 </td>
1286 |                 <td style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#95a0ba;">
1287 |                   {% if ent.trend == 'up' %}&#9650; rising{% elif ent.trend == 'down' %}&#9660; falling{% else %}&#8594; stable{% endif %}
1288 |                 </td>
1289 |               </tr>
1290 |               {% endfor %}
1291 |             </tbody>
1292 |           </table>
1293 |         </div>
1294 |         {% else %}
1295 |         <p class="text-muted small">No entity data.</p>
1296 |         {% endif %}
1297 |       </div>
1298 |     </div>
1299 |   </div>
1300 | 
1301 |   <!-- ════════════════════════════════════════════════════════════════
1302 |        ROW 5: Article Stream
1303 |        ════════════════════════════════════════════════════════════════ -->
1304 |   <div class="row g-4">
1305 |     <div class="col-12">
1306 |       <div class="g-card">
1307 |         <div class="d-flex align-items-center justify-content-between mb-4">
1308 |           <span class="g-eyebrow" style="margin-bottom:0;">Article Stream — Sorted by Importance</span>
1309 |           <a href="/articles" style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#f8c15c;text-decoration:none;font-weight:700;letter-spacing:0.10em;">ALL ARTICLES &#8599;</a>
1310 |         </div>
1311 | 
1312 |         {% if top_articles %}
1313 |         <div class="row">
1314 |           {% for art in top_articles %}
1315 |           {% set imp = art.importance_score|default(50)|int %}
1316 |           <div class="col-md-6">
1317 |             <div class="art-stream-item">
1318 |               <div class="art-rank">{{ loop.index }}</div>
1319 |               <div>
1320 |                 <div class="art-title">
1321 |                   <a href="/articles/{{ art.id }}" style="color:inherit;text-decoration:none;">
1322 |                     {{ art.title|truncate(120) }}
1323 |                   </a>
1324 |                 </div>
1325 |                 <div class="art-meta">
1326 |                   <span class="s-badge {{ art.sentiment }}">
1327 |                     {% if art.sentiment == 'bullish' %}&#9650;{% elif art.sentiment == 'bearish' %}&#9660;{% else %}&#9679;{% endif %}
1328 |                     {{ art.sentiment }}
1329 |                   </span>
1330 |                   {% if art.narrative_label and art.narrative_label != '—' %}
1331 |                   <span class="narr-chip">{{ art.narrative_label }}</span>
1332 |                   {% endif %}
1333 |                   <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#4a5568;">{{ art.created_at[:10] }}</span>
1334 |                 </div>
1335 |               </div>
1336 |               <div style="text-align:right;flex-shrink:0;">
1337 |                 <div class="art-imp"
1338 |                      style="color:{% if imp >= 70 %}#f8c15c{% elif imp >= 50 %}#95a0ba{% else %}#4a5568{% endif %};">
1339 |                   {{ imp }}
1340 |                 </div>
1341 |                 <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:0.12em;color:#4a5568;">IMP</div>
1342 |               </div>
1343 |             </div>
1344 |           </div>
1345 |           {% endfor %}
1346 |         </div>
1347 |         {% else %}
1348 |         <div class="text-center py-5">
1349 |           <div style="color:#95a0ba;font-size:14px;">No articles classified yet.</div>
1350 |         </div>
1351 |         {% endif %}
1352 |       </div>
1353 |     </div>
1354 |   </div>
1355 | 
1356 | </div><!-- /intel-container -->
1357 | </div><!-- /intel-page -->
1358 | {% endblock %}
1359 | 
1360 | {% block extra_js %}
1361 | <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
1362 | <script>
1363 | (function() {
1364 |   'use strict';
1365 | 
1366 |   const sovereignCtx = {{ sovereign_ctx_json|safe if sovereign_ctx_json else '{}' }};
1367 |   const isCommander = {{ 'true' if is_commander else 'false' }};
1368 | 
1369 |   // ═══════════════════════════════════════════════════════════════════
1370 |   // A. SOVEREIGN SIGNAL MATRIX — Radar Chart (Chart.js)
1371 |   // ═══════════════════════════════════════════════════════════════════
1372 |   function computeSignalMatrix(ctx) {
1373 |     if (!ctx || !ctx.btc) return null;
1374 | 
1375 |     const fg = (ctx.fear_greed || {}).value || 50;
1376 |     const hashrate = (ctx.network || {}).hashrate_eh || 0;
1377 |     const adjPct = (ctx.network || {}).next_adj_pct || 0;
1378 |     const flow = ctx.exchange_flow || 'neutral';
1379 |     const pcaf = ctx.pcaf_score || 0;
1380 |     const kolScore = (ctx.kol || {}).sentiment_score || 50;
1381 |     const artCount = (ctx.narrative || {}).article_count || 0;
1382 |     const lnCap = (ctx.lightning || {}).capacity_btc || 0;
1383 |     const lnChannels = (ctx.lightning || {}).channels || 0;
1384 |     const dominance = (ctx.btc || {}).dominance || 0;
1385 |     const polyScore = (ctx.polymarket || {}).macro_sentiment || 50;
1386 |     const whaleCount = (ctx.whale_alerts || []).length;
1387 | 
1388 |     // 1. Miner Health: hashrate + positive adj = healthy
1389 |     const minerHealth = Math.min(100, Math.max(0,
1390 |       (hashrate > 0 ? Math.min(50, hashrate / 20) : 25) +
1391 |       (adjPct > 0 ? Math.min(30, adjPct * 10) : 0) +
1392 |       (flow === 'outflow' ? 20 : flow === 'inflow' ? -10 : 0)
1393 |     ));
1394 | 
1395 |     // 2. Exchange Pressure: pcaf + flow direction
1396 |     const flowScore = flow === 'outflow' ? 70 : flow === 'inflow' ? 30 : 50;
1397 |     const exchangePressure = Math.min(100, Math.max(0,
1398 |       (pcaf * 0.5) + (flowScore * 0.5)
1399 |     ));
1400 | 
1401 |     // 3. Narrative Momentum: KOL sentiment + article velocity
1402 |     const narrativeMomentum = Math.min(100, Math.max(0,
1403 |       (kolScore * 0.6) + (Math.min(100, artCount * 5) * 0.4)
1404 |     ));
1405 | 
1406 |     // 4. On-Chain Accumulation: whale alerts + patterns
1407 |     const onchainAccum = Math.min(100, Math.max(0,
1408 |       (whaleCount * 15) + (flow === 'outflow' ? 30 : 10) + (pcaf * 0.2)
1409 |     ));
1410 | 
1411 |     // 5. Lightning Growth: capacity + channels
1412 |     const lnCapScore = lnCap > 0 ? Math.min(100, (lnCap / 6000) * 80) : 40;
1413 |     const lnChanScore = lnChannels > 0 ? Math.min(100, (lnChannels / 45000) * 80) : 40;
1414 |     const lightningGrowth = Math.round(lnCapScore * 0.6 + lnChanScore * 0.4);
1415 | 
1416 |     // 6. Market Structure: F&G + dominance + polymarket
1417 |     const marketStructure = Math.min(100, Math.max(0,
1418 |       (fg * 0.4) + (dominance * 0.3) + (polyScore * 0.3)
1419 |     ));
1420 | 
1421 |     const axes = {
1422 |       miner_health: Math.round(minerHealth),
1423 |       exchange_pressure: Math.round(exchangePressure),
1424 |       narrative_momentum: Math.round(narrativeMomentum),
1425 |       onchain_accumulation: Math.round(onchainAccum),
1426 |       lightning_growth: Math.round(lightningGrowth),
1427 |       market_structure: Math.round(marketStructure)
1428 |     };
1429 | 
1430 |     const vals = Object.values(axes);
1431 |     const composite = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
1432 |     const bias = composite >= 65 ? 'BULLISH' : composite <= 35 ? 'BEARISH' : 'NEUTRAL';
1433 | 
1434 |     return { axes, composite, bias };
1435 |   }
1436 | 
1437 |   function renderRadar(matrix) {
1438 |     const canvas = document.getElementById('radarChart');
1439 |     if (!canvas || !matrix) return;
1440 | 
1441 |     const labels = ['MINER HEALTH', 'EXCHANGE PRESSURE', 'NARRATIVE', 'ON-CHAIN', 'LIGHTNING', 'MARKET'];
1442 |     const values = [
1443 |       matrix.axes.miner_health,
1444 |       matrix.axes.exchange_pressure,
1445 |       matrix.axes.narrative_momentum,
1446 |       matrix.axes.onchain_accumulation,
1447 |       matrix.axes.lightning_growth,
1448 |       matrix.axes.market_structure
1449 |     ];
1450 | 
1451 |     const colors = values.map(v => v < 33 ? 'rgba(255,59,95,0.7)' : v < 66 ? 'rgba(248,193,92,0.7)' : 'rgba(137,255,184,0.7)');
1452 | 
1453 |     new Chart(canvas, {
1454 |       type: 'radar',
1455 |       data: {
1456 |         labels: labels,
1457 |         datasets: [{
1458 |           label: 'Current',
1459 |           data: values,
1460 |           backgroundColor: 'rgba(248,193,92,0.12)',
1461 |           borderColor: '#f8c15c',
1462 |           borderWidth: 2,
1463 |           pointBackgroundColor: colors,
1464 |           pointBorderColor: colors,
1465 |           pointRadius: 5,
1466 |           pointHoverRadius: 7,
1467 |         }]
1468 |       },
1469 |       options: {
1470 |         responsive: true,
1471 |         maintainAspectRatio: true,
1472 |         scales: {
1473 |           r: {
1474 |             angleLines: { color: 'rgba(255,255,255,0.06)' },
1475 |             grid: { color: 'rgba(255,255,255,0.06)' },
1476 |             pointLabels: {
1477 |               color: '#95a0ba',
1478 |               font: { family: "'JetBrains Mono', monospace", size: 9, weight: 700 }
1479 |             },
1480 |             ticks: { display: false },
1481 |             suggestedMin: 0,
1482 |             suggestedMax: 100,
1483 |           }
1484 |         },
1485 |         plugins: {
1486 |           legend: { display: false },
1487 |           tooltip: {
1488 |             backgroundColor: '#0d1118',
1489 |             titleFont: { family: "'JetBrains Mono', monospace", size: 11 },
1490 |             bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
1491 |             borderColor: 'rgba(255,255,255,0.1)',
1492 |             borderWidth: 1,
1493 |             callbacks: {
1494 |               label: function(ctx) {
1495 |                 const v = ctx.raw;
1496 |                 const zone = v < 33 ? 'BEARISH' : v < 66 ? 'NEUTRAL' : 'BULLISH';
1497 |                 return v + '/100 — ' + zone;
1498 |               }
1499 |             }
1500 |           }
1501 |         }
1502 |       }
1503 |     });
1504 | 
1505 |     // Update composite display
1506 |     const compEl = document.getElementById('radar-composite');
1507 |     const biasEl = document.getElementById('radar-bias');
1508 |     if (compEl) {
1509 |       compEl.textContent = matrix.composite;
1510 |       compEl.style.color = matrix.composite >= 65 ? '#89ffb8' : matrix.composite <= 35 ? '#ff8ba0' : '#f8c15c';
1511 |     }
1512 |     if (biasEl) biasEl.textContent = 'SOVEREIGN COMPOSITE • ' + matrix.bias;
1513 |   }
1514 | 
1515 |   const matrix = computeSignalMatrix(sovereignCtx);
1516 |   renderRadar(matrix);
1517 | 
1518 |   // ═══════════════════════════════════════════════════════════════════
1519 |   // C. CROSS-SIGNAL DIVERGENCE ENGINE
1520 |   // ═══════════════════════════════════════════════════════════════════
1521 |   function computeDivergences(ctx) {
1522 |     if (!ctx || !ctx.btc) return [];
1523 |     const divergences = [];
1524 | 
1525 |     const fg = (ctx.fear_greed || {}).value || 50;
1526 |     const hashrate = (ctx.network || {}).hashrate_eh || 0;
1527 |     const adjPct = (ctx.network || {}).next_adj_pct || 0;
1528 |     const flow = ctx.exchange_flow || 'neutral';
1529 |     const kolScore = (ctx.kol || {}).sentiment_score || 50;
1530 |     const change24h = (ctx.btc || {}).change_24h || 0;
1531 |     const lnCap = (ctx.lightning || {}).capacity_btc || 0;
1532 | 
1533 |     // 1. Extreme Fear + Hashrate ATH = historically bullish
1534 |     if (fg <= 20 && hashrate > 900) {
1535 |       divergences.push({
1536 |         direction: 'bullish',
1537 |         title: 'EXTREME FEAR + HASHRATE HIGH',
1538 |         signals: 'Fear & Greed ' + fg + ' + Hashrate ' + hashrate.toFixed(0) + ' EH/s',
1539 |         detail: 'Historically, F&G <20 with hashrate near ATH preceded 15-40% rallies within 30 days.',
1540 |         accuracy: 78
1541 |       });
1542 |     }
1543 | 
1544 |     // 2. Exchange inflow + KOL euphoria = bearish 4-7d
1545 |     if (flow === 'inflow' && kolScore > 75) {
1546 |       divergences.push({
1547 |         direction: 'bearish',
1548 |         title: 'EXCHANGE INFLOW + KOL EUPHORIA',
1549 |         signals: 'Exchange inflows + KOL sentiment ' + kolScore + '/100',
1550 |         detail: 'Exchange deposit spikes during KOL euphoria historically precede 5-12% corrections within 7 days.',
1551 |         accuracy: 71
1552 |       });
1553 |     }
1554 | 
1555 |     // 3. Price drop + hashrate rise = supply squeeze
1556 |     if (change24h < -3 && adjPct > 2) {
1557 |       divergences.push({
1558 |         direction: 'bullish',
1559 |         title: 'PRICE DOWN + MINERS EXPANDING',
1560 |         signals: 'Price ' + change24h.toFixed(1) + '% + Difficulty adj +' + adjPct.toFixed(1) + '%',
1561 |         detail: 'Miners increasing capacity despite price decline signals conviction. Supply squeeze pattern.',
1562 |         accuracy: 74
1563 |       });
1564 |     }
1565 | 
1566 |     // 4. Fear + Lightning growth = long-term bullish
1567 |     if (fg < 30 && lnCap > 5500) {
1568 |       divergences.push({
1569 |         direction: 'bullish',
1570 |         title: 'FEAR + LIGHTNING CAPACITY HIGH',
1571 |         signals: 'F&G ' + fg + ' + LN ' + lnCap.toFixed(0) + ' BTC capacity',
1572 |         detail: 'Network utility growing during fear signals adoption-driven demand, not speculation.',
1573 |         accuracy: 68
1574 |       });
1575 |     }
1576 | 
1577 |     // 5. KOL bearish + price stable = accumulation
1578 |     if (kolScore < 35 && Math.abs(change24h) < 2) {
1579 |       divergences.push({
1580 |         direction: 'bullish',
1581 |         title: 'KOL BEARISH + PRICE STABLE',
1582 |         signals: 'KOL sentiment ' + kolScore + '/100 + Price ' + change24h.toFixed(1) + '%',
1583 |         detail: 'Social sentiment negative but price holding = smart money accumulating under retail fear.',
1584 |         accuracy: 65
1585 |       });
1586 |     }
1587 | 
1588 |     return divergences;
1589 |   }
1590 | 
1591 |   function renderDivergences() {
1592 |     const container = document.getElementById('divergence-alerts');
1593 |     if (!container) return;
1594 | 
1595 |     const divergences = computeDivergences(sovereignCtx);
1596 | 
1597 |     if (divergences.length === 0) {
1598 |       container.innerHTML = '<div style="text-align:center;padding:24px 0;">' +
1599 |         '<div style="color:#95a0ba;font-size:28px;margin-bottom:8px;">&#9745;</div>' +
1600 |         '<div style="color:#95a0ba;font-size:13px;">No divergences detected.</div>' +
1601 |         '<div style="color:#4a5568;font-size:11px;margin-top:4px;">All signals aligned.</div></div>';
1602 |       return;
1603 |     }
1604 | 
1605 |     let html = '';
1606 |     divergences.forEach(function(d) {
1607 |       const titleColor = d.direction === 'bullish' ? '#89ffb8' : d.direction === 'bearish' ? '#ff8ba0' : '#f8c15c';
1608 |       html += '<div class="divergence-alert ' + d.direction + '">' +
1609 |         '<div class="divergence-title" style="color:' + titleColor + ';">' +
1610 |         (d.direction === 'bullish' ? '&#9650; ' : d.direction === 'bearish' ? '&#9660; ' : '&#9644; ') +
1611 |         d.title + '</div>' +
1612 |         '<div class="divergence-detail">' + d.detail + '</div>' +
1613 |         '<div style="display:flex;justify-content:space-between;align-items:center;">' +
1614 |         '<span style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:#4a5568;">' + d.signals + '</span>' +
1615 |         '<span class="divergence-accuracy">ACCURACY: ' + d.accuracy + '%</span>' +
1616 |         '</div></div>';
1617 |     });
1618 |     container.innerHTML = html;
1619 |   }
1620 | 
1621 |   renderDivergences();
1622 | 
1623 |   // ═══════════════════════════════════════════════════════════════════
1624 |   // D. NARRATIVE MOMENTUM TRACKER
1625 |   // ═══════════════════════════════════════════════════════════════════
1626 |   async function loadNarrativeMomentum() {
1627 |     const container = document.getElementById('narrative-momentum');
1628 |     if (!container) return;
1629 | 
1630 |     try {
1631 |       const resp = await fetch('/api/intelligence/narrative-momentum');
1632 |       if (!resp.ok) throw new Error('API error');
1633 |       const data = await resp.json();
1634 | 
1635 |       if (!data.momentum || data.momentum.length === 0) {
1636 |         container.innerHTML = '<p style="color:#4a5568;font-size:11px;text-align:center;">No momentum data yet.</p>';
1637 |         return;
1638 |       }
1639 | 
1640 |       let html = '';
1641 |       data.momentum.slice(0, 6).forEach(function(m) {
1642 |         const trendColor = m.trend === 'accelerating' ? '#89ffb8' : m.trend === 'decelerating' ? '#ff8ba0' : '#f8c15c';
1643 |         const trendIcon = m.trend === 'accelerating' ? '&#9650;' : m.trend === 'decelerating' ? '&#9660;' : '&#8594;';
1644 |         const barWidth = Math.min(100, Math.max(5, m.recent_pct * 3));
1645 | 
1646 |         html += '<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">' +
1647 |           '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +
1648 |           '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;color:#eef2ff;">' + m.topic + '</span>' +
1649 |           '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:800;color:' + trendColor + ';">' +
1650 |           trendIcon + ' ' + (m.delta > 0 ? '+' : '') + m.delta + 'pp</span>' +
1651 |           '</div>' +
1652 |           '<div style="height:3px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden;">' +
1653 |           '<div style="width:' + barWidth + '%;height:100%;background:' + trendColor + ';border-radius:2px;transition:width 0.8s ease;"></div>' +
1654 |           '</div>' +
1655 |           '<div style="font-family:\'JetBrains Mono\',monospace;font-size:8px;color:#4a5568;margin-top:3px;">' +
1656 |           m.recent_count + ' articles (3d) vs ' + m.prior_count + ' (prior 7d)</div></div>';
1657 |       });
1658 | 
1659 |       // Leading signals
1660 |       if (data.leading_signals && data.leading_signals.length > 0) {
1661 |         html += '<div style="margin-top:12px;padding:10px;border-radius:8px;background:rgba(248,193,92,0.06);border:1px solid rgba(248,193,92,0.12);">' +
1662 |           '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;font-weight:800;letter-spacing:0.12em;color:#f8c15c;margin-bottom:6px;">LEADING SIGNALS</div>';
1663 |         data.leading_signals.forEach(function(s) {
1664 |           html += '<div style="font-size:11px;color:#95a0ba;margin-bottom:3px;">' + s + '</div>';
1665 |         });
1666 |         html += '</div>';
1667 |       }
1668 | 
1669 |       container.innerHTML = html;
1670 |     } catch (e) {
1671 |       container.innerHTML = '<p style="color:#4a5568;font-size:11px;text-align:center;">Narrative data unavailable.</p>';
1672 |     }
1673 |   }
1674 | 
1675 |   loadNarrativeMomentum();
1676 | 
1677 |   // ═══════════════════════════════════════════════════════════════════
1678 |   // Auto-refresh every 5 minutes
1679 |   // ═══════════════════════════════════════════════════════════════════
1680 |   setInterval(async function() {
1681 |     try {
1682 |       // Refresh signal score
1683 |       const sigResp = await fetch('/api/intelligence/signal');
1684 |       if (sigResp.ok) {
1685 |         const sigData = await sigResp.json();
1686 |         if (sigData.success && sigData.data) {
1687 |           const numEl = document.getElementById('algo-num');
1688 |           if (numEl) {
1689 |             numEl.textContent = Math.round(sigData.data.composite);
1690 |             numEl.style.color = sigData.data.color;
1691 |           }
1692 |         }
1693 |       }
1694 | 
1695 |       // Refresh narrative momentum
1696 |       loadNarrativeMomentum();
1697 |     } catch (e) { /* silent */ }
1698 |   }, 300000);
1699 | 
1700 | })();
1701 | </script>
1702 | {% endblock %}
1703 | 
```

### File: services/sovereign_context_engine.py (862 lines)
```
   1 | """
   2 | Sovereign Context Engine — Unified Intelligence Brain
   3 | 
   4 | Reads ALL Protocol Pulse data streams, maintains a world-state snapshot,
   5 | detects cross-stream patterns, and emits SOVEREIGN ALERTS when multiple
   6 | streams confirm the same signal.
   7 | 
   8 | Every downstream system reads from this engine:
   9 |   Oracle briefings, Stage content, article generator,
  10 |   intelligence terminal, PANOPTICON dashboard.
  11 | 
  12 | Usage:
  13 |   python3 services/sovereign_context_engine.py --cycle
  14 | """
  15 | 
  16 | import argparse
  17 | import hashlib
  18 | import json
  19 | import logging
  20 | import os
  21 | import sqlite3
  22 | import sys
  23 | import time
  24 | from datetime import datetime, timezone
  25 | from pathlib import Path
  26 | from typing import Any, Dict, List, Optional
  27 | 
  28 | import requests
  29 | 
  30 | # ---------------------------------------------------------------------------
  31 | # Paths
  32 | # ---------------------------------------------------------------------------
  33 | BASE_DIR = Path(__file__).resolve().parent.parent
  34 | DATA_DIR = BASE_DIR / "data"
  35 | CONTEXT_DIR = DATA_DIR / "sovereign_context"
  36 | LATEST_PATH = CONTEXT_DIR / "latest.json"
  37 | HISTORY_PATH = CONTEXT_DIR / "history.jsonl"
  38 | ALERTS_DB_PATH = DATA_DIR / "sovereign_alerts.db"
  39 | SOVEREIGN_INTEL_DB = DATA_DIR / "sovereign_intel.db"
  40 | SENTINEL_ALERTS_DB = DATA_DIR / "sentinel_alerts.db"
  41 | ACTIVE_SIGNAL_PATH = BASE_DIR / "video_pipeline_v3" / "cache" / "active_signal.json"
  42 | STAGE_BRIEF_PATH = BASE_DIR / "video_pipeline_v3" / "data" / "stage_briefs" / "latest.json"
  43 | PRICE_CACHE_PATH = DATA_DIR / "price_cache.json"
  44 | 
  45 | # ---------------------------------------------------------------------------
  46 | # Logging
  47 | # ---------------------------------------------------------------------------
  48 | logging.basicConfig(
  49 |     level=logging.INFO,
  50 |     format="%(asctime)s [SCE] %(levelname)s %(message)s",
  51 |     datefmt="%Y-%m-%d %H:%M:%S",
  52 | )
  53 | log = logging.getLogger("sovereign_context_engine")
  54 | 
  55 | # ---------------------------------------------------------------------------
  56 | # HTTP helpers
  57 | # ---------------------------------------------------------------------------
  58 | SESSION = requests.Session()
  59 | SESSION.headers.update({"User-Agent": "ProtocolPulse/SovereignContext/1.0"})
  60 | REQ_TIMEOUT = 12
  61 | 
  62 | 
  63 | def _get_json(url: str, timeout: int = REQ_TIMEOUT) -> Optional[dict]:
  64 |     """Safe JSON GET — returns None on any failure."""
  65 |     try:
  66 |         r = SESSION.get(url, timeout=timeout)
  67 |         r.raise_for_status()
  68 |         return r.json()
  69 |     except Exception as exc:
  70 |         log.warning("GET %s failed: %s", url, exc)
  71 |         return None
  72 | 
  73 | 
  74 | def _read_json_file(path: Path) -> Optional[dict]:
  75 |     """Read a local JSON file, return None on failure."""
  76 |     try:
  77 |         if path.exists():
  78 |             return json.loads(path.read_text())
  79 |     except Exception as exc:
  80 |         log.warning("Read %s failed: %s", path, exc)
  81 |     return None
  82 | 
  83 | 
  84 | # ---------------------------------------------------------------------------
  85 | # Alerts DB setup
  86 | # ---------------------------------------------------------------------------
  87 | def _init_alerts_db():
  88 |     """Create sovereign_alerts.db if needed."""
  89 |     conn = sqlite3.connect(str(ALERTS_DB_PATH))
  90 |     conn.execute("""
  91 |         CREATE TABLE IF NOT EXISTS sovereign_alerts (
  92 |             id INTEGER PRIMARY KEY AUTOINCREMENT,
  93 |             ts_utc TEXT NOT NULL,
  94 |             pattern_id TEXT NOT NULL,
  95 |             title TEXT NOT NULL,
  96 |             description TEXT,
  97 |             severity TEXT DEFAULT 'WATCH',
  98 |             data_json TEXT,
  99 |             fingerprint TEXT UNIQUE
 100 |         )
 101 |     """)
 102 |     conn.execute("""
 103 |         CREATE INDEX IF NOT EXISTS idx_sa_ts ON sovereign_alerts(ts_utc DESC)
 104 |     """)
 105 |     conn.commit()
 106 |     conn.close()
 107 | 
 108 | 
 109 | # ===================================================================
 110 | # DATA COLLECTORS — one per stream
 111 | # ===================================================================
 112 | 
 113 | def _fetch_btc_price() -> dict:
 114 |     """BTC price from CoinGecko (same source as price_service.py)."""
 115 |     data = _get_json(
 116 |         "https://api.coingecko.com/api/v3/simple/price"
 117 |         "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
 118 |         "&include_7d_change=true&include_market_cap=true"
 119 |     )
 120 |     if not data or "bitcoin" not in data:
 121 |         return {"price": 0, "change_24h": 0, "change_7d": 0, "market_cap": 0, "dominance": 0}
 122 |     btc = data["bitcoin"]
 123 |     # Dominance from CoinGecko global
 124 |     dom = 0
 125 |     g = _get_json("https://api.coingecko.com/api/v3/global")
 126 |     if g and "data" in g:
 127 |         dom = round(g["data"].get("market_cap_percentage", {}).get("btc", 0), 1)
 128 |     return {
 129 |         "price": btc.get("usd", 0),
 130 |         "change_24h": round(btc.get("usd_24h_change", 0), 2),
 131 |         "change_7d": round(btc.get("usd_7d_change", 0) if "usd_7d_change" in btc else 0, 2),
 132 |         "market_cap": btc.get("usd_market_cap", 0),
 133 |         "dominance": dom,
 134 |     }
 135 | 
 136 | 
 137 | def _fetch_fear_greed() -> dict:
 138 |     """Fear & Greed Index from alternative.me."""
 139 |     data = _get_json("https://api.alternative.me/fng/?limit=1")
 140 |     if not data or "data" not in data:
 141 |         return {"value": 50, "label": "Neutral"}
 142 |     d = data["data"][0]
 143 |     return {"value": int(d.get("value", 50)), "label": d.get("value_classification", "Neutral")}
 144 | 
 145 | 
 146 | def _fetch_mempool() -> dict:
 147 |     """Mempool stats + fee estimates from mempool.space."""
 148 |     stats = _get_json("https://mempool.space/api/mempool") or {}
 149 |     fees = _get_json("https://mempool.space/api/v1/fees/recommended") or {}
 150 |     return {
 151 |         "fee_low": fees.get("economyFee", 0),
 152 |         "fee_mid": fees.get("halfHourFee", 0),
 153 |         "fee_high": fees.get("fastestFee", 0),
 154 |         "unconfirmed": stats.get("count", 0),
 155 |         "size_mb": round(stats.get("vsize", 0) / 1_000_000, 1),
 156 |     }
 157 | 
 158 | 
 159 | def _fetch_network() -> dict:
 160 |     """Hashrate, difficulty, next adjustment from mempool.space."""
 161 |     hr_data = _get_json("https://mempool.space/api/v1/mining/hashrate/3d")
 162 |     diff = _get_json("https://mempool.space/api/v1/difficulty-adjustment") or {}
 163 |     block_height = 0
 164 |     tip = _get_json("https://mempool.space/api/blocks/tip/height")
 165 |     if isinstance(tip, int):
 166 |         block_height = tip
 167 |     elif isinstance(tip, dict):
 168 |         block_height = tip.get("height", 0)
 169 | 
 170 |     hashrate_eh = 0
 171 |     if hr_data and "currentHashrate" in hr_data:
 172 |         hashrate_eh = round(hr_data["currentHashrate"] / 1e18, 1)
 173 |     elif hr_data and "hashrates" in hr_data and hr_data["hashrates"]:
 174 |         last = hr_data["hashrates"][-1]
 175 |         hashrate_eh = round(last.get("avgHashrate", 0) / 1e18, 1)
 176 | 
 177 |     return {
 178 |         "hashrate_eh": hashrate_eh,
 179 |         "difficulty": diff.get("difficulty", 0),
 180 |         "next_adj_pct": round(diff.get("difficultyChange", 0), 2),
 181 |         "next_adj_blocks": diff.get("remainingBlocks", 0),
 182 |         "block_height": block_height,
 183 |     }
 184 | 
 185 | 
 186 | def _fetch_lightning() -> dict:
 187 |     """Lightning Network stats from mempool.space."""
 188 |     data = _get_json("https://mempool.space/api/v1/lightning/statistics/latest")
 189 |     if not data or "latest" not in data:
 190 |         return {"capacity_btc": 0, "channels": 0, "nodes": 0}
 191 |     ln = data["latest"]
 192 |     return {
 193 |         "capacity_btc": round(ln.get("total_capacity", 0) / 1e8, 1),
 194 |         "channels": ln.get("channel_count", 0),
 195 |         "nodes": ln.get("node_count", 0),
 196 |     }
 197 | 
 198 | 
 199 | def _fetch_kol_sentiment() -> dict:
 200 |     """KOL sentiment from kol_pulse_item table (last 50 posts)."""
 201 |     db_path = BASE_DIR / "instance" / "protocol_pulse.db"
 202 |     if not db_path.exists():
 203 |         db_path = BASE_DIR / "protocol_pulse.db"
 204 |     if not db_path.exists():
 205 |         return {"sentiment_score": 50, "top_topics": [], "post_count_24h": 0}
 206 | 
 207 |     try:
 208 |         conn = sqlite3.connect(str(db_path))
 209 |         conn.row_factory = sqlite3.Row
 210 | 
 211 |         # Count posts in last 24h
 212 |         row = conn.execute(
 213 |             "SELECT COUNT(*) as cnt FROM kol_pulse_item "
 214 |             "WHERE created_at > datetime('now', '-1 day')"
 215 |         ).fetchone()
 216 |         count_24h = row["cnt"] if row else 0
 217 | 
 218 |         # Last 50 posts for basic topic extraction
 219 |         rows = conn.execute(
 220 |             "SELECT content FROM kol_pulse_item ORDER BY created_at DESC LIMIT 50"
 221 |         ).fetchall()
 222 |         conn.close()
 223 | 
 224 |         # Simple keyword-based topic extraction
 225 |         topic_counts: Dict[str, int] = {}
 226 |         keywords = {
 227 |             "etf": ["etf", "blackrock", "ishares", "grayscale"],
 228 |             "halving": ["halving", "halvening", "block reward"],
 229 |             "regulation": ["sec", "regulation", "regulatory", "gensler", "congress"],
 230 |             "mining": ["mining", "hashrate", "miner", "asic"],
 231 |             "lightning": ["lightning", "ln", "layer 2", "layer2"],
 232 |             "self-custody": ["self-custody", "self custody", "not your keys", "cold storage"],
 233 |             "macro": ["fed", "inflation", "interest rate", "treasury", "macro"],
 234 |             "stablecoin": ["stablecoin", "usdt", "usdc", "tether"],
 235 |             "defi": ["defi", "dex", "yield", "lending"],
 236 |             "cbdc": ["cbdc", "digital dollar", "digital currency"],
 237 |         }
 238 |         for row in rows:
 239 |             text = (row["content"] or "").lower()
 240 |             for topic, kws in keywords.items():
 241 |                 if any(kw in text for kw in kws):
 242 |                     topic_counts[topic] = topic_counts.get(topic, 0) + 1
 243 | 
 244 |         top_topics = sorted(topic_counts, key=topic_counts.get, reverse=True)[:5]
 245 | 
 246 |         # Rough sentiment: count bullish vs bearish keywords
 247 |         bullish_kw = ["bullish", "moon", "pump", "ath", "accumulate", "buy", "long", "breakout", "green"]
 248 |         bearish_kw = ["bearish", "dump", "crash", "sell", "short", "fear", "capitulation", "red"]
 249 |         bull = sum(1 for r in rows if any(k in (r["content"] or "").lower() for k in bullish_kw))
 250 |         bear = sum(1 for r in rows if any(k in (r["content"] or "").lower() for k in bearish_kw))
 251 |         total = bull + bear
 252 |         sentiment_score = int((bull / total * 100) if total > 0 else 50)
 253 | 
 254 |         return {
 255 |             "sentiment_score": sentiment_score,
 256 |             "top_topics": top_topics,
 257 |             "post_count_24h": count_24h,
 258 |         }
 259 |     except Exception as exc:
 260 |         log.warning("KOL sentiment fetch failed: %s", exc)
 261 |         return {"sentiment_score": 50, "top_topics": [], "post_count_24h": 0}
 262 | 
 263 | 
 264 | def _fetch_article_narrative() -> dict:
 265 |     """Article corpus: last 20 articles, dominant theme, sentiment."""
 266 |     db_path = BASE_DIR / "instance" / "protocol_pulse.db"
 267 |     if not db_path.exists():
 268 |         db_path = BASE_DIR / "protocol_pulse.db"
 269 |     if not db_path.exists():
 270 |         return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}
 271 | 
 272 |     try:
 273 |         conn = sqlite3.connect(str(db_path))
 274 |         conn.row_factory = sqlite3.Row
 275 |         rows = conn.execute(
 276 |             "SELECT title, category, sentiment, narrative_label FROM articles "
 277 |             "ORDER BY created_at DESC LIMIT 20"
 278 |         ).fetchall()
 279 |         conn.close()
 280 | 
 281 |         if not rows:
 282 |             return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}
 283 | 
 284 |         # Dominant theme from narrative_label or category
 285 |         themes: Dict[str, int] = {}
 286 |         sentiments = []
 287 |         for r in rows:
 288 |             label = r["narrative_label"] or r["category"] or "general"
 289 |             themes[label] = themes.get(label, 0) + 1
 290 |             if r["sentiment"]:
 291 |                 sentiments.append(r["sentiment"])
 292 | 
 293 |         dominant = max(themes, key=themes.get) if themes else "unknown"
 294 | 
 295 |         # Aggregate sentiment
 296 |         if sentiments:
 297 |             bull = sum(1 for s in sentiments if s and "bull" in s.lower())
 298 |             bear = sum(1 for s in sentiments if s and "bear" in s.lower())
 299 |             if bull > bear:
 300 |                 agg_sentiment = "bullish"
 301 |             elif bear > bull:
 302 |                 agg_sentiment = "bearish"
 303 |             else:
 304 |                 agg_sentiment = "neutral"
 305 |         else:
 306 |             agg_sentiment = "neutral"
 307 | 
 308 |         return {
 309 |             "dominant_theme": dominant,
 310 |             "sentiment": agg_sentiment,
 311 |             "article_count": len(rows),
 312 |         }
 313 |     except Exception as exc:
 314 |         log.warning("Article narrative fetch failed: %s", exc)
 315 |         return {"dominant_theme": "unknown", "sentiment": "neutral", "article_count": 0}
 316 | 
 317 | 
 318 | def _fetch_polymarket() -> dict:
 319 |     """Polymarket crypto/macro sentiment."""
 320 |     try:
 321 |         # Import from existing service
 322 |         sys.path.insert(0, str(BASE_DIR))
 323 |         from services.polymarket_service import (
 324 |             get_bitcoin_markets,
 325 |             get_macro_sentiment_score,
 326 |             get_top_market_by_volume,
 327 |         )
 328 |         top = get_top_market_by_volume()
 329 |         score = get_macro_sentiment_score()
 330 |         return {
 331 |             "macro_sentiment": score,
 332 |             "top_market": top["question"] if top else "N/A",
 333 |             "top_probability": round(max(top["outcomes"].values()), 1) if top and top.get("outcomes") else 0,
 334 |         }
 335 |     except Exception as exc:
 336 |         log.warning("Polymarket fetch failed: %s", exc)
 337 |         return {"macro_sentiment": 50, "top_market": "N/A", "top_probability": 0}
 338 | 
 339 | 
 340 | def _fetch_pcaf_score() -> int:
 341 |     """PCAF anomaly score from active_signal.json (Nostr relay cache)."""
 342 |     data = _read_json_file(ACTIVE_SIGNAL_PATH)
 343 |     if not data:
 344 |         return 0
 345 |     # Score based on filtered post count (higher = more signal activity)
 346 |     return min(data.get("total_scored", 0) * 5, 100)
 347 | 
 348 | 
 349 | def _fetch_exchange_flow() -> str:
 350 |     """Exchange netflow from sentinel_alerts.db or sovereign_intel.db signals."""
 351 |     # Check sovereign_intel signals table for exchange flow direction
 352 |     if SOVEREIGN_INTEL_DB.exists():
 353 |         try:
 354 |             conn = sqlite3.connect(str(SOVEREIGN_INTEL_DB))
 355 |             conn.row_factory = sqlite3.Row
 356 |             row = conn.execute(
 357 |                 "SELECT direction FROM signals "
 358 |                 "WHERE category = 'onchain' AND metric LIKE '%exchange%' "
 359 |                 "ORDER BY ts_utc DESC LIMIT 1"
 360 |             ).fetchone()
 361 |             conn.close()
 362 |             if row:
 363 |                 return row["direction"]
 364 |         except Exception:
 365 |             pass
 366 | 
 367 |     # Check sentinel for whale-related alerts
 368 |     if SENTINEL_ALERTS_DB.exists():
 369 |         try:
 370 |             conn = sqlite3.connect(str(SENTINEL_ALERTS_DB))
 371 |             conn.row_factory = sqlite3.Row
 372 |             row = conn.execute(
 373 |                 "SELECT message FROM alerts "
 374 |                 "WHERE rule LIKE '%exchange%' OR rule LIKE '%whale%' "
 375 |                 "ORDER BY created_at DESC LIMIT 1"
 376 |             ).fetchone()
 377 |             conn.close()
 378 |             if row:
 379 |                 msg = (row["message"] or "").lower()
 380 |                 if "outflow" in msg:
 381 |                     return "outflow"
 382 |                 if "inflow" in msg:
 383 |                     return "inflow"
 384 |         except Exception:
 385 |             pass
 386 | 
 387 |     return "neutral"
 388 | 
 389 | 
 390 | def _fetch_stage_brief() -> dict:
 391 |     """Latest narrative from stage briefs."""
 392 |     data = _read_json_file(STAGE_BRIEF_PATH)
 393 |     if not data:
 394 |         return {"narrative": "N/A", "brief_type": "unknown"}
 395 |     return {
 396 |         "narrative": (data.get("script_summary") or "N/A")[:200],
 397 |         "brief_type": data.get("brief_type", "unknown"),
 398 |     }
 399 | 
 400 | 
 401 | def _fetch_whale_alerts() -> List[dict]:
 402 |     """Recent whale alerts from sentinel_alerts.db."""
 403 |     if not SENTINEL_ALERTS_DB.exists():
 404 |         return []
 405 |     try:
 406 |         conn = sqlite3.connect(str(SENTINEL_ALERTS_DB))
 407 |         conn.row_factory = sqlite3.Row
 408 |         rows = conn.execute(
 409 |             "SELECT tier, rule, message, score, created_at FROM alerts "
 410 |             "ORDER BY created_at DESC LIMIT 5"
 411 |         ).fetchall()
 412 |         conn.close()
 413 |         return [dict(r) for r in rows]
 414 |     except Exception as exc:
 415 |         log.warning("Whale alerts fetch failed: %s", exc)
 416 |         return []
 417 | 
 418 | 
 419 | # ===================================================================
 420 | # PATTERN DETECTION
 421 | # ===================================================================
 422 | 
 423 | class Alert:
 424 |     """A sovereign pattern-match alert."""
 425 | 
 426 |     def __init__(self, pattern_id: str, title: str, description: str,
 427 |                  severity: str = "WATCH", data: Optional[dict] = None):
 428 |         self.pattern_id = pattern_id
 429 |         self.title = title
 430 |         self.description = description
 431 |         self.severity = severity  # CRITICAL, WATCH, NOTE
 432 |         self.data = data or {}
 433 |         self.ts = datetime.now(timezone.utc).isoformat()
 434 | 
 435 |     def fingerprint(self) -> str:
 436 |         """Unique ID per pattern + hour to prevent spam."""
 437 |         hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
 438 |         raw = f"{self.pattern_id}:{hour}"
 439 |         return hashlib.sha256(raw.encode()).hexdigest()[:16]
 440 | 
 441 |     def to_dict(self) -> dict:
 442 |         return {
 443 |             "pattern_id": self.pattern_id,
 444 |             "title": self.title,
 445 |             "description": self.description,
 446 |             "severity": self.severity,
 447 |             "ts": self.ts,
 448 |             "data": self.data,
 449 |         }
 450 | 
 451 | 
 452 | def detect_patterns(ws: dict) -> List[Alert]:
 453 |     """Run all pattern detection rules against the world state."""
 454 |     alerts: List[Alert] = []
 455 | 
 456 |     btc = ws.get("btc", {})
 457 |     fg = ws.get("fear_greed", {})
 458 |     mempool = ws.get("mempool", {})
 459 |     network = ws.get("network", {})
 460 |     lightning = ws.get("lightning", {})
 461 |     kol = ws.get("kol", {})
 462 |     narrative = ws.get("narrative", {})
 463 |     polymarket = ws.get("polymarket", {})
 464 |     exchange_flow = ws.get("exchange_flow", "neutral")
 465 | 
 466 |     fg_val = fg.get("value", 50)
 467 |     change_24h = btc.get("change_24h", 0)
 468 |     hashrate = network.get("hashrate_eh", 0)
 469 |     fee_high = mempool.get("fee_high", 0)
 470 | 
 471 |     # 1. ACCUMULATION SIGNAL
 472 |     # hashrate UP (positive adj) + exchange outflows + FG < 30
 473 |     if (network.get("next_adj_pct", 0) > 0
 474 |             and exchange_flow == "outflow"
 475 |             and fg_val < 30):
 476 |         alerts.append(Alert(
 477 |             "ACCUMULATION",
 478 |             "Stealth accumulation detected",
 479 |             f"Hashrate adj +{network['next_adj_pct']}%, exchange outflows active, "
 480 |             f"Fear & Greed at {fg_val} ({fg.get('label', '')}).",
 481 |             severity="WATCH",
 482 |             data={"fg": fg_val, "adj_pct": network["next_adj_pct"], "flow": exchange_flow},
 483 |         ))
 484 | 
 485 |     # 2. SUPPLY SHOCK PRECURSOR
 486 |     # hashrate UP + price DOWN + miners not capitulating
 487 |     if (network.get("next_adj_pct", 0) > 0
 488 |             and change_24h < -2
 489 |             and hashrate > 0):
 490 |         alerts.append(Alert(
 491 |             "SUPPLY_SHOCK",
 492 |             "Miners not capitulating — supply shock risk",
 493 |             f"Hashrate {hashrate} EH/s (adj +{network['next_adj_pct']}%), "
 494 |             f"price down {change_24h}% — miners holding.",
 495 |             severity="WATCH",
 496 |             data={"hashrate": hashrate, "change_24h": change_24h},
 497 |         ))
 498 | 
 499 |     # 3. NARRATIVE DIVERGENCE
 500 |     # article sentiment BULLISH + KOL sentiment BEARISH (or vice versa)
 501 |     art_sent = narrative.get("sentiment", "neutral")
 502 |     kol_score = kol.get("sentiment_score", 50)
 503 |     if art_sent == "bullish" and kol_score < 35:
 504 |         alerts.append(Alert(
 505 |             "NARRATIVE_DIVERGENCE",
 506 |             "Narrative split — watch for resolution",
 507 |             f"Articles bullish but KOL sentiment at {kol_score}/100 (bearish). "
 508 |             "Divergence often precedes volatility.",
 509 |             severity="WATCH",
 510 |             data={"article_sentiment": art_sent, "kol_score": kol_score},
 511 |         ))
 512 |     elif art_sent == "bearish" and kol_score > 65:
 513 |         alerts.append(Alert(
 514 |             "NARRATIVE_DIVERGENCE",
 515 |             "Narrative split — watch for resolution",
 516 |             f"Articles bearish but KOL sentiment at {kol_score}/100 (bullish). "
 517 |             "Divergence often precedes volatility.",
 518 |             severity="WATCH",
 519 |             data={"article_sentiment": art_sent, "kol_score": kol_score},
 520 |         ))
 521 | 
 522 |     # 4. POLYMARKET CONFIRMATION
 523 |     # Big probability shift + KOL mention overlap
 524 |     poly_sent = polymarket.get("macro_sentiment", 50)
 525 |     if abs(poly_sent - 50) > 20 and kol.get("post_count_24h", 0) > 10:
 526 |         direction = "bullish" if poly_sent > 50 else "bearish"
 527 |         alerts.append(Alert(
 528 |             "POLYMARKET_CONFIRM",
 529 |             "Market consensus shifting",
 530 |             f"Polymarket sentiment {poly_sent}/100 ({direction}), "
 531 |             f"{kol['post_count_24h']} KOL posts in 24h — consensus forming.",
 532 |             severity="WATCH",
 533 |             data={"poly_sentiment": poly_sent, "kol_posts": kol["post_count_24h"]},
 534 |         ))
 535 | 
 536 |     # 5. MEMPOOL PRESSURE
 537 |     # fees > 50 sat/vB + Lightning growing
 538 |     if fee_high > 50 and lightning.get("capacity_btc", 0) > 0:
 539 |         alerts.append(Alert(
 540 |             "MEMPOOL_PRESSURE",
 541 |             "On-chain congestion — Lightning demand increasing",
 542 |             f"Priority fees at {fee_high} sat/vB, Lightning capacity "
 543 |             f"{lightning['capacity_btc']} BTC across {lightning['channels']} channels.",
 544 |             severity="NOTE",
 545 |             data={"fee_high": fee_high, "ln_capacity": lightning["capacity_btc"]},
 546 |         ))
 547 | 
 548 |     # 6. FEAR CAPITULATION
 549 |     # FG < 15 + exchange inflows + price DOWN >5%
 550 |     if fg_val < 15 and exchange_flow == "inflow" and change_24h < -5:
 551 |         alerts.append(Alert(
 552 |             "FEAR_CAPITULATION",
 553 |             "Extreme fear — historically bullish 30-day forward",
 554 |             f"Fear & Greed at {fg_val}, exchange inflows active, "
 555 |             f"price down {change_24h}%. Capitulation pattern detected.",
 556 |             severity="CRITICAL",
 557 |             data={"fg": fg_val, "change_24h": change_24h, "flow": exchange_flow},
 558 |         ))
 559 | 
 560 |     # 7. CROSS-ASSET DIVERGENCE
 561 |     # 3+ signals diverge from their baseline simultaneously
 562 |     divergence_count = 0
 563 |     divergence_details = []
 564 | 
 565 |     if abs(change_24h) > 5:
 566 |         divergence_count += 1
 567 |         divergence_details.append(f"Price {change_24h:+.1f}%")
 568 |     if abs(fg_val - 50) > 25:
 569 |         divergence_count += 1
 570 |         divergence_details.append(f"F&G {fg_val}")
 571 |     if abs(kol_score - 50) > 25:
 572 |         divergence_count += 1
 573 |         divergence_details.append(f"KOL {kol_score}")
 574 |     if abs(poly_sent - 50) > 25:
 575 |         divergence_count += 1
 576 |         divergence_details.append(f"Polymarket {poly_sent}")
 577 |     if fee_high > 100:
 578 |         divergence_count += 1
 579 |         divergence_details.append(f"Fees {fee_high} sat/vB")
 580 | 
 581 |     if divergence_count >= 3:
 582 |         alerts.append(Alert(
 583 |             "CROSS_DIVERGENCE",
 584 |             "DIVERGENCE ALERT — major move probable 24-72h",
 585 |             f"{divergence_count} signals diverging: {', '.join(divergence_details)}. "
 586 |             "Multiple streams confirming unusual activity.",
 587 |             severity="CRITICAL",
 588 |             data={"count": divergence_count, "details": divergence_details},
 589 |         ))
 590 | 
 591 |     return alerts
 592 | 
 593 | 
 594 | # ===================================================================
 595 | # ALERT PERSISTENCE
 596 | # ===================================================================
 597 | 
 598 | def emit_alerts(alerts: List[Alert]):
 599 |     """Write alerts to sovereign_alerts.db (dedup by fingerprint per hour)."""
 600 |     if not alerts:
 601 |         return
 602 |     _init_alerts_db()
 603 |     conn = sqlite3.connect(str(ALERTS_DB_PATH))
 604 |     inserted = 0
 605 |     for a in alerts:
 606 |         try:
 607 |             conn.execute(
 608 |                 "INSERT OR IGNORE INTO sovereign_alerts "
 609 |                 "(ts_utc, pattern_id, title, description, severity, data_json, fingerprint) "
 610 |                 "VALUES (?, ?, ?, ?, ?, ?, ?)",
 611 |                 (a.ts, a.pattern_id, a.title, a.description,
 612 |                  a.severity, json.dumps(a.data), a.fingerprint()),
 613 |             )
 614 |             inserted += 1
 615 |         except sqlite3.IntegrityError:
 616 |             pass  # duplicate fingerprint — already emitted this hour
 617 |     conn.commit()
 618 |     conn.close()
 619 |     if inserted:
 620 |         log.info("Emitted %d new alert(s): %s",
 621 |                  inserted, ", ".join(a.pattern_id for a in alerts))
 622 | 
 623 | 
 624 | # ===================================================================
 625 | # MAIN ENGINE
 626 | # ===================================================================
 627 | 
 628 | def _calculate_proprietary_indices(
 629 |     btc: dict, network: dict, kol: dict,
 630 |     exchange_flow: str, whale_alerts: list, fg: dict
 631 | ) -> dict:
 632 |     """Compute Protocol Pulse proprietary branded indices from raw data.
 633 | 
 634 |     Three indices (consensus P0 from cross-LLM audit):
 635 |       1. Miner Conviction Index — hashrate strength vs price weakness
 636 |       2. Exchange Pressure Ratio — -2 to +2 flow directional score
 637 |       3. Social-to-Market Divergence — KOL sentiment vs price action delta
 638 |     """
 639 |     hashrate = network.get("hashrate_eh", 0)
 640 |     change_7d = btc.get("change_7d", 0)
 641 |     change_24h = btc.get("change_24h", 0)
 642 |     kol_score = kol.get("sentiment_score", 50)
 643 |     fg_val = fg.get("value", 50)
 644 | 
 645 |     # 1. Miner Conviction Index (0-100 scale, >50 = conviction, <50 = capitulation)
 646 |     # Normalized: hashrate relative to ~900 EH/s baseline + inverse price pressure
 647 |     hashrate_norm = min(100, (hashrate / 900) * 50) if hashrate > 0 else 25
 648 |     price_pressure = max(-25, min(25, -change_7d))  # negative change = positive conviction
 649 |     miner_conviction = max(0, min(100, int(hashrate_norm + price_pressure + 25)))
 650 | 
 651 |     if miner_conviction >= 70:
 652 |         mc_interp = "Miners expanding despite price consolidation — supply shock precursor."
 653 |         mc_signal = "bullish"
 654 |     elif miner_conviction <= 30:
 655 |         mc_interp = "Miner stress detected — potential capitulation zone."
 656 |         mc_signal = "bearish"
 657 |     else:
 658 |         mc_interp = "Miner activity within normal range."
 659 |         mc_signal = "neutral"
 660 | 
 661 |     # 2. Exchange Pressure Ratio (-2 to +2)
 662 |     ep_score = 0
 663 |     if exchange_flow == "outflow":
 664 |         ep_score += 1
 665 |     elif exchange_flow == "inflow":
 666 |         ep_score -= 1
 667 |     # Whale alert direction analysis
 668 |     whale_withdrawals = sum(1 for w in whale_alerts if "withdraw" in (w.get("message", "") or "").lower())
 669 |     whale_deposits = sum(1 for w in whale_alerts if "deposit" in (w.get("message", "") or "").lower())
 670 |     if whale_withdrawals > whale_deposits:
 671 |         ep_score += 1
 672 |     elif whale_deposits > whale_withdrawals:
 673 |         ep_score -= 1
 674 | 
 675 |     ep_labels = {
 676 |         2: ("Strong outflow — bullish accumulation", "bullish"),
 677 |         1: ("Net outflow detected", "bullish"),
 678 |         0: ("Neutral exchange flow", "neutral"),
 679 |         -1: ("Net inflow — selling pressure", "bearish"),
 680 |         -2: ("Strong inflow — distribution detected", "bearish"),
 681 |     }
 682 |     ep_interp, ep_signal = ep_labels.get(ep_score, ("Neutral", "neutral"))
 683 | 
 684 |     # 3. Social-to-Market Divergence
 685 |     # Formula: (kol_sentiment - 50) - (btc_7d_change * 2)
 686 |     social_div = round((kol_score - 50) - (change_7d * 2), 1)
 687 | 
 688 |     if social_div > 20:
 689 |         sd_interp = "Social FOMO ahead of price — potential local top signal."
 690 |         sd_signal = "bearish"
 691 |     elif social_div < -20:
 692 |         sd_interp = "Social capitulation while price holds — potential accumulation zone."
 693 |         sd_signal = "bullish"
 694 |     else:
 695 |         sd_interp = "Social sentiment aligned with price action."
 696 |         sd_signal = "neutral"
 697 | 
 698 |     return {
 699 |         "miner_conviction": {
 700 |             "score": miner_conviction,
 701 |             "interpretation": mc_interp,
 702 |             "signal": mc_signal,
 703 |         },
 704 |         "exchange_pressure": {
 705 |             "score": ep_score,
 706 |             "interpretation": ep_interp,
 707 |             "signal": ep_signal,
 708 |         },
 709 |         "social_divergence": {
 710 |             "score": social_div,
 711 |             "interpretation": sd_interp,
 712 |             "signal": sd_signal,
 713 |         },
 714 |     }
 715 | 
 716 | 
 717 | class SovereignContextEngine:
 718 |     """The connective brain that unifies all Protocol Pulse data streams."""
 719 | 
 720 |     def build_world_state(self) -> dict:
 721 |         """Assemble everything into one JSON world state."""
 722 |         log.info("Building world state...")
 723 |         t0 = time.monotonic()
 724 | 
 725 |         # Fetch all streams
 726 |         btc = _fetch_btc_price()
 727 |         fg = _fetch_fear_greed()
 728 |         mempool = _fetch_mempool()
 729 |         network = _fetch_network()
 730 |         lightning = _fetch_lightning()
 731 |         kol = _fetch_kol_sentiment()
 732 |         narrative = _fetch_article_narrative()
 733 |         polymarket = _fetch_polymarket()
 734 |         pcaf = _fetch_pcaf_score()
 735 |         exchange_flow = _fetch_exchange_flow()
 736 |         stage = _fetch_stage_brief()
 737 |         whale_alerts = _fetch_whale_alerts()
 738 | 
 739 |         block_height = network.pop("block_height", 0)
 740 | 
 741 |         world_state = {
 742 |             "timestamp": datetime.now(timezone.utc).isoformat(),
 743 |             "block_height": block_height,
 744 |             "btc": btc,
 745 |             "fear_greed": fg,
 746 |             "mempool": mempool,
 747 |             "network": network,
 748 |             "lightning": lightning,
 749 |             "kol": kol,
 750 |             "narrative": narrative,
 751 |             "polymarket": polymarket,
 752 |             "pcaf_score": pcaf,
 753 |             "exchange_flow": exchange_flow,
 754 |             "stage_brief": stage,
 755 |             "whale_alerts": whale_alerts,
 756 |             "active_alerts": [],
 757 |             "pattern_matches": [],
 758 |             "indices": _calculate_proprietary_indices(
 759 |                 btc, network, kol, exchange_flow, whale_alerts, fg
 760 |             ),
 761 |         }
 762 | 
 763 |         elapsed = time.monotonic() - t0
 764 |         log.info("World state built in %.1fs — BTC $%s, F&G %s, Hashrate %s EH/s",
 765 |                  elapsed, f"{btc['price']:,.0f}", fg["value"], network["hashrate_eh"])
 766 |         return world_state
 767 | 
 768 |     def run_cycle(self) -> dict:
 769 |         """Full cycle: build state → detect patterns → emit alerts → save."""
 770 |         log.info("=== Sovereign Context Cycle Start ===")
 771 |         t0 = time.monotonic()
 772 | 
 773 |         # 1. Build world state
 774 |         ws = self.build_world_state()
 775 | 
 776 |         # 2. Detect patterns
 777 |         alerts = detect_patterns(ws)
 778 |         ws["active_alerts"] = [a.to_dict() for a in alerts]
 779 |         ws["pattern_matches"] = [a.pattern_id for a in alerts]
 780 | 
 781 |         if alerts:
 782 |             log.info("Detected %d pattern(s): %s",
 783 |                      len(alerts), ", ".join(a.pattern_id for a in alerts))
 784 |         else:
 785 |             log.info("No pattern matches this cycle")
 786 | 
 787 |         # 3. Emit alerts to DB
 788 |         emit_alerts(alerts)
 789 | 
 790 |         # 4. Save latest snapshot
 791 |         CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
 792 |         LATEST_PATH.write_text(json.dumps(ws, indent=2, default=str))
 793 |         log.info("Saved latest.json (%d bytes)", LATEST_PATH.stat().st_size)
 794 | 
 795 |         # 5. Append to history
 796 |         with open(HISTORY_PATH, "a") as f:
 797 |             f.write(json.dumps(ws, default=str) + "\n")
 798 | 
 799 |         elapsed = time.monotonic() - t0
 800 |         log.info("=== Cycle complete in %.1fs — %d alerts ===", elapsed, len(alerts))
 801 |         return ws
 802 | 
 803 | 
 804 | # ===================================================================
 805 | # Flask route helper (imported by app.py)
 806 | # ===================================================================
 807 | 
 808 | def get_latest_context() -> Optional[dict]:
 809 |     """Read the latest sovereign context snapshot for API serving."""
 810 |     return _read_json_file(LATEST_PATH)
 811 | 
 812 | 
 813 | def get_recent_alerts(limit: int = 20) -> List[dict]:
 814 |     """Read recent alerts from sovereign_alerts.db."""
 815 |     if not ALERTS_DB_PATH.exists():
 816 |         return []
 817 |     try:
 818 |         conn = sqlite3.connect(str(ALERTS_DB_PATH))
 819 |         conn.row_factory = sqlite3.Row
 820 |         rows = conn.execute(
 821 |             "SELECT ts_utc, pattern_id, title, description, severity, data_json "
 822 |             "FROM sovereign_alerts ORDER BY ts_utc DESC LIMIT ?",
 823 |             (limit,)
 824 |         ).fetchall()
 825 |         conn.close()
 826 |         results = []
 827 |         for r in rows:
 828 |             d = dict(r)
 829 |             d["data"] = json.loads(d.pop("data_json", "{}"))
 830 |             results.append(d)
 831 |         return results
 832 |     except Exception:
 833 |         return []
 834 | 
 835 | 
 836 | # ===================================================================
 837 | # CLI entrypoint
 838 | # ===================================================================
 839 | 
 840 | def main():
 841 |     parser = argparse.ArgumentParser(description="Sovereign Context Engine")
 842 |     parser.add_argument("--cycle", action="store_true", help="Run one full cycle")
 843 |     args = parser.parse_args()
 844 | 
 845 |     if args.cycle:
 846 |         engine = SovereignContextEngine()
 847 |         ws = engine.run_cycle()
 848 |         print(json.dumps({
 849 |             "status": "ok",
 850 |             "btc_price": ws["btc"]["price"],
 851 |             "fear_greed": ws["fear_greed"]["value"],
 852 |             "hashrate_eh": ws["network"]["hashrate_eh"],
 853 |             "alerts": len(ws["active_alerts"]),
 854 |             "patterns": ws["pattern_matches"],
 855 |         }, indent=2))
 856 |     else:
 857 |         parser.print_help()
 858 | 
 859 | 
 860 | if __name__ == "__main__":
 861 |     main()
 862 | 
```

### File: services/polymarket_service.py (127 lines)
```
   1 | """
   2 | Polymarket Intelligence Service — Real-time prediction market data.
   3 | Free API, no auth required. Filters for Bitcoin/crypto/macro markets.
   4 | Feeds directly into Cross-Signal Divergence Engine.
   5 | """
   6 | import requests, logging
   7 | from datetime import datetime
   8 | 
   9 | logger = logging.getLogger('polymarket')
  10 | 
  11 | POLYMARKET_API = 'https://gamma-api.polymarket.com'
  12 | 
  13 | # Bitcoin/macro relevant tags on Polymarket
  14 | RELEVANT_TAGS = ['Crypto', 'Bitcoin', 'Fed', 'Economy', 'Geopolitics', 'US Politics']
  15 | 
  16 | def get_bitcoin_markets(limit=10):
  17 |     """Fetch active Polymarket markets relevant to Bitcoin/macro."""
  18 |     try:
  19 |         # Search for crypto/bitcoin markets
  20 |         resp = requests.get(
  21 |             f'{POLYMARKET_API}/markets',
  22 |             params={
  23 |                 'limit': 50,
  24 |                 'active': 'true',
  25 |                 'closed': 'false',
  26 |             },
  27 |             timeout=8
  28 |         )
  29 |         if not resp.ok:
  30 |             return []
  31 |         
  32 |         markets = resp.json()
  33 |         
  34 |         # Filter for relevant markets
  35 |         keywords = ['bitcoin', 'btc', 'crypto', 'fed', 'rate', 'inflation', 
  36 |                     'etf', 'halving', 'saylor', 'blackrock', 'recession', 'trump']
  37 |         
  38 |         filtered = []
  39 |         for m in markets:
  40 |             q = m.get('question', '').lower()
  41 |             if any(k in q for k in keywords):
  42 |                 filtered.append({
  43 |                     'question': m.get('question', ''),
  44 |                     'slug': m.get('slug', ''),
  45 |                     'volume': float(m.get('volume', 0) or 0),
  46 |                     'liquidity': float(m.get('liquidity', 0) or 0),
  47 |                     'end_date': m.get('endDate', ''),
  48 |                     'outcomes': _parse_outcomes(m),
  49 |                 })
  50 |         
  51 |         # Sort by volume descending
  52 |         filtered.sort(key=lambda x: x['volume'], reverse=True)
  53 |         return filtered[:limit]
  54 |     
  55 |     except Exception as e:
  56 |         logger.error(f'[Polymarket] Fetch failed: {e}')
  57 |         return []
  58 | 
  59 | def _parse_outcomes(market):
  60 |     """Extract Yes/No probabilities from market."""
  61 |     import json as _json
  62 |     try:
  63 |         raw_names = market.get('outcomes', [])
  64 |         raw_prices = market.get('outcomePrices', [])
  65 |         # API returns JSON strings, not lists
  66 |         if isinstance(raw_names, str):
  67 |             raw_names = _json.loads(raw_names)
  68 |         if isinstance(raw_prices, str):
  69 |             raw_prices = _json.loads(raw_prices)
  70 |         outcomes = {}
  71 |         for name, price_str in zip(raw_names, raw_prices):
  72 |             outcomes[name] = round(float(price_str or 0) * 100, 1)
  73 |         return outcomes
  74 |     except:
  75 |         return {}
  76 | 
  77 | def get_macro_sentiment_score():
  78 |     """
  79 |     Derive a macro sentiment score (0-100) from Polymarket crypto markets.
  80 |     High score = market expects bullish macro (rate cuts, BTC ETF approval, etc)
  81 |     Low score = market expects bearish macro
  82 |     """
  83 |     try:
  84 |         markets = get_bitcoin_markets(20)
  85 |         if not markets:
  86 |             return 50  # Neutral default
  87 |         
  88 |         bullish_signals = 0
  89 |         bearish_signals = 0
  90 |         
  91 |         for m in markets:
  92 |             outcomes = m.get('outcomes', {})
  93 |             q = m.get('question', '').lower()
  94 |             yes_prob = outcomes.get('Yes', 50)
  95 |             
  96 |             # Classify as bullish or bearish signal
  97 |             bullish_keywords = ['etf', 'approve', 'above', 'higher', 'rate cut', 
  98 |                                'halving', 'saylor', 'blackrock', 'reach', 'exceed']
  99 |             bearish_keywords = ['below', 'crash', 'recession', 'ban', 'hike',
 100 |                                'fail', 'reject', 'regulation']
 101 |             
 102 |             is_bullish_question = any(k in q for k in bullish_keywords)
 103 |             is_bearish_question = any(k in q for k in bearish_keywords)
 104 |             
 105 |             weight = max(1, m['volume'] / 10000)  # Weight by volume
 106 |             
 107 |             if is_bullish_question:
 108 |                 bullish_signals += (yes_prob / 100) * weight
 109 |             elif is_bearish_question:
 110 |                 bearish_signals += (yes_prob / 100) * weight
 111 |         
 112 |         total = bullish_signals + bearish_signals
 113 |         if total == 0:
 114 |             return 50
 115 |         
 116 |         score = (bullish_signals / total) * 100
 117 |         return round(score)
 118 |     
 119 |     except Exception as e:
 120 |         logger.error(f'[Polymarket] Sentiment score failed: {e}')
 121 |         return 50
 122 | 
 123 | def get_top_market_by_volume():
 124 |     """Get single most-traded Bitcoin/crypto market for dashboard widget."""
 125 |     markets = get_bitcoin_markets(5)
 126 |     return markets[0] if markets else None
 127 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
