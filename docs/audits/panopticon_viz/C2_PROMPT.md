# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: panopticon_viz
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
### Q1 — VISUALIZATION DESIGN CHOICE

**Detailed Analysis:**

- **Force-Directed Graph Suitability:** A D3 force-directed network graph is a suitable choice for visualizing correlations among a small number of nodes (6 in this case). The layout naturally emphasizes relationships through proximity, which can be intuitive for users to understand. However, this choice might introduce visual noise due to the dynamic nature of the layout, especially if nodes are constantly moving or overlapping.

- **Alternatives:**
  - **Chord Diagram:** Could effectively show relationships between indices, but might be less intuitive for users unfamiliar with this type of visualization.
  - **Radar/Spider Chart:** Useful for comparing scores across multiple dimensions but less effective for showing pairwise correlations.
  - **Heatmap Matrix:** Offers a clear, static view of correlations but lacks the interactivity and visual appeal of a force-directed graph.
  - **Parallel Coordinates:** Good for high-dimensional data but might be overkill for only 6 nodes.

- **Information Density vs. Visual Noise:** The force-directed graph can add information density by showing both node scores and edge correlations dynamically. However, the constant movement might create visual noise, making it harder for users to focus on specific correlations.

- **Edge Encoding:** Using edge thickness and style to represent correlation strength is effective, but users might misinterpret proximity as a stronger correlation than it actually is, especially if nodes are close due to layout constraints rather than data-driven reasons.

- **Interactivity:** The hover highlight, drag, and click-through interactions are appropriate for this data density, enhancing user engagement and allowing for deeper exploration of the data.

**Severity: MEDIUM**

**Specific Fix:** Consider adding a static representation (e.g., a heatmap matrix) alongside the force-directed graph to provide a stable reference for correlations, reducing reliance on dynamic proximity.

### Q2 — D3 IMPLEMENTATION CORRECTNESS

**Detailed Analysis:**

- **Force Simulation Configuration:** The force simulation is configured with appropriate forces (charge, link distance, collision) to maintain node separation and edge clarity (lines 2728-2733). However, the collision force might need fine-tuning to prevent node overlap.

- **Data Joins:** The enter/update/exit pattern is correctly implemented for nodes and links (lines 2626-2634, 2637-2641), ensuring smooth transitions during live data updates.

- **Memory Management:** The simulation is properly stopped and restarted on re-render (lines 2728-2730), minimizing the risk of memory leaks.

- **SVG vs. Canvas:** SVG is appropriate for this scale (6 nodes + ~15 edges), providing high-quality rendering and easy manipulation of DOM elements.

- **SRI Hash:** The SRI hash for the D3 CDN matches the official d3 v7.8.5 release, ensuring integrity and security (line 2220).

**Severity: LOW**

**Specific Fix:** Fine-tune the collision force to ensure nodes do not overlap, especially on smaller screens.

### Q3 — INTERACTION + ACCESSIBILITY

**Detailed Analysis:**

- **Hover Interaction:** The edge dimming and node opacity changes on hover (lines 2678-2689) effectively focus user attention but might confuse users if not clearly explained in the legend.

- **Touch Interaction:** Force-directed drag might not work optimally on mobile devices due to touch event conflicts. Testing on various devices is necessary to ensure usability.

- **Commander Lock:** The blur overlay for free-tier users is correctly implemented (lines 2028-2037), preserving the intended access restrictions.

- **Keyboard Navigation:** SVG-only interaction lacks keyboard accessibility, which is a significant a11y concern. Users relying on keyboard navigation might find it challenging to interact with the graph.

**Severity: HIGH**

**Specific Fix:** Implement keyboard navigation support, possibly by allowing users to cycle through nodes and edges using the keyboard and providing focus indicators.

### Q4 — VISUAL QUALITY + INFORMATION DENSITY

**Detailed Analysis:**

- **Legend Clarity:** The legend provides essential information but could be expanded to clarify how proximity relates to correlation strength (lines 1713-1722).

- **Node Label Readability:** Node labels (index code + score) are generally readable, but smaller viewports might cause overlap or truncation (lines 2650-2673).

- **Visual Effects:** Glow effects and transitions enhance the premium feel but should be subtle to avoid distraction (lines 2663-2667).

- **Information Density:** The graph is information-dense, offering a dynamic view of correlations. However, it might not convey as much static information as the scatter plot it replaced.

**Severity: MEDIUM**

**Specific Fix:** Enhance the legend with more detailed explanations and ensure node labels are always visible, possibly by adjusting font sizes dynamically based on

## GROK — CYCLE 1 OUTPUT
### Audit Report for Panopticon Correlation Map Visualization

I am conducting a thorough review of the D3.js force-directed network graph implementation in the `panopticon.html` file, specifically focusing on the correlation map visualization for the 6 sovereign signal indices. Below, I address the four critical questions with detailed analysis, severity ratings, and specific fixes. I conclude with a final verdict and prioritized recommendations.

---

### Q1 — VISUALIZATION DESIGN CHOICE

**Detailed Analysis:**
- **Suitability of D3 Force-Directed Network Graph (Lines 2550-2749):** The force-directed graph is implemented to visualize correlations between 6 indices (IHX, EPX, MCX, OCX, FDX, OPX) with nodes representing indices (size based on score, color indicating bullish/neutral/bearish) and edges representing correlation strength based on score proximity (HIGH <15 difference, MEDIUM 15-30, LOW >30 no edge). This choice leverages the natural metaphor of "closeness" to imply correlation, which can be intuitive for users familiar with network graphs. However, with only 6 nodes, the graph may not fully utilize the dynamic layout capabilities of force-directed simulations, which are more effective with larger datasets (10+ nodes) to show clustering and complex relationships (see line 2570 for node creation).
- **Alternatives Considered:**
  - **Chord Diagram:** Better for showing pairwise relationships with weighted connections, emphasizing flow or strength of correlation via ribbon thickness. It would be more compact and avoid the "floating" ambiguity of force-directed layouts where node positions can vary on refresh (line 2729-2734 for force simulation).
  - **Radar/Spider Chart:** Useful for comparing multiple dimensions (indices) across a shared scale (score), but it struggles to show pairwise correlations directly, focusing instead on individual performance.
  - **Heatmap Matrix (6x6):** Directly maps correlation values (score differences) to a color grid, providing precision and eliminating positional ambiguity. It’s less visually engaging but more data-dense and stable for small node counts like 6 (not implemented in current code).
  - **Parallel Coordinates:** Good for multidimensional data but overkill for 6 nodes and less intuitive for correlation; it prioritizes individual variable trends over relationships.
- **Information Density vs. Visual Noise:** For 6 nodes, the force-directed graph adds visual noise due to random initial positioning and simulation settling (lines 2729-2748). The layout doesn’t inherently encode additional data beyond edge thickness and node size/color, as node positions are algorithmically determined rather than data-driven. This can mislead users into over-interpreting spatial proximity beyond the defined edge rules (line 2577-2588 for edge logic).
- **Edge Encoding Meaningfulness:** The edge encoding (score proximity = correlation, lines 2579-2583) is a reasonable heuristic but risks false impressions. A score difference of 15 might not always mean a "high" correlation in a real-world context if other factors (e.g., temporal alignment or external events) are ignored. The current implementation doesn’t account for such nuances, presenting a simplified view that could mislead users into assuming causality or deeper linkage.
- **Interactivity Suitability (Lines 2678-2712):** Hover (dimming unconnected edges), drag (repositioning nodes), and click-through (to detailed cards) add engagement, but for 6 nodes, drag functionality feels unnecessary and can disrupt the intended layout without adding analytical value. Hover focus is helpful but may be over-engineered for such a small dataset.

**Severity:** MEDIUM
- The force-directed graph is not optimal for 6 nodes due to visual noise and potential misinterpretation of spatial positioning. However, it’s not critically flawed and can still convey basic correlation with edges.

**Specific Fix:**
- Replace the force-directed graph with a **6x6 Heatmap Matrix** for precision and stability. Encode correlation (score difference) as cell color intensity (darker = higher correlation, i.e., smaller difference). Use a fixed grid layout to avoid positional ambiguity.
  ```javascript
  // Replace renderCorrelationMap() starting at line 2550 with a heatmap matrix
  function renderCorrelationMap() {
    var container = document.getElementById('ss2-map-graph');
    if (!container || typeof d3 === 'undefined') return;
    var W = container.clientWidth || 400;
    var H = Math.max(container.clientHeight || 260, 260);
    var cellSize = Math.min(W, H) / 7; // 6 cells + margin

    var svg = d3.select(container).select('svg');
    if (svg.empty()) {
      svg = d3.select(container).append('svg').attr('width', W).attr('height', H).style('background', '#050505');
      // Add grid and other static elements as needed
    } else {
      svg.attr('width', W).attr('height', H);
    }

    var nodes = streamOrder.map(function(sid) {
      return { id: sid,

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PANOPTICON_VIZ — CYCLE 1
Generated: 2026-04-16 08:30
Models: gpt4o, grok (+1 failed: gemini/403-PERMISSION_DENIED)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Visualization Design Choice | N/A (failed) | MEDIUM | MEDIUM | MEDIUM |
| D3 Implementation Correctness | N/A (failed) | LOW | LOW-MEDIUM | LOW |
| Interaction + Accessibility | N/A (failed) | HIGH | MEDIUM | HIGH |
| Visual Quality + Information Density | N/A (failed) | MEDIUM | MEDIUM | MEDIUM |
| Overall | N/A | PASS WITH FIXES | PASS WITH FIXES | PASS WITH FIXES |

> **Note on Gemini failure:** Only 2 of 3 models produced output. Confidence thresholds are adjusted accordingly — "unanimous" = both available models agree; "majority" threshold cannot meaningfully exceed 2/2 in this cycle. Gemini data will be recovered in Cycle 2.

---

## UNANIMOUS FINDINGS
*(Both GPT-4o and Grok flagged — implement unconditionally)*

---

### U1 — Keyboard Accessibility Absent from SVG Interaction Layer
**What it is:** The force-directed graph is SVG-only with no keyboard navigation support. Users who rely on keyboard or assistive technology cannot access node data, traverse edges, or trigger click-through interactions.
**File/Line:** `panopticon.html` lines 2678–2712 (interaction handlers)
**What to change:** Add `tabindex="0"` to each node `<g>` element on creation. Implement `keydown` listeners (ArrowLeft/ArrowRight to cycle nodes, Enter to trigger click-through). Add visible `:focus` ring using SVG `filter` or `stroke`. Expose correlation data to screen readers via `<title>` and `aria-label` child elements within each node group.

---

### U2 — Force-Directed Layout is Suboptimal for 6-Node Dataset
**What it is:** Both models independently concluded that a force-directed graph is a weak choice for exactly 6 nodes. The randomized initial positioning and physics-based settling introduce layout instability and positional ambiguity — users may misinterpret spatial proximity as analytical signal when it is actually algorithmic artifact.
**File/Line:** `panopticon.html` lines 2550–2749 (`renderCorrelationMap()`)
**What to change:** Either (a) replace with a static 6×6 heatmap matrix for precision, or (b) freeze node positions after simulation convergence so layout is stable across refreshes. See conflicts section for tiebreaker on which path to take.

---

### U3 — Legend Does Not Explain Proximity ≠ Correlation
**What it is:** Both models flagged that the existing legend (lines 1713–1722) fails to clarify that node proximity in the force layout is algorithmic, not a direct data encoding. Users will naturally read closeness as meaning stronger correlation, which is only partially true (edges encode correlation; position does not).
**File/Line:** `panopticon.html` lines 1713–1722
**What to change:** Add a legend annotation: *"Node position is layout-only. Correlation strength is encoded by edge thickness and style only."* Additionally clari

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: templates/panopticon.html (4051 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}PANOPTICON — Congressional Intelligence | Protocol Pulse
   4 | <script src="/static/js/panopticon_stream.js"></script>
   5 | {% endblock %}
   6 | {% block meta_description %}Real-time intelligence dashboard tracking congressional disclosures, whale wallet movements, and geopolitical financial signals cross-referenced with Bitcoin data.{% endblock %}
   7 | 
   8 | {% block head %}
   9 | <link rel="preconnect" href="https://fonts.googleapis.com">
  10 | <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  11 | <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  12 | <style>
  13 | /* ── FONT FALLBACK — readable text before web fonts load ── */
  14 | body { font-family: 'JetBrains Mono', 'Courier New', monospace; }
  15 | /* ═══════════════════════════════════════════════════════════════════════
  16 |    PANOPTICON — "They watch us. Now we watch them."
  17 |    Surveillance Grid × Bloomberg Terminal
  18 |    ═══════════════════════════════════════════════════════════════════════ */
  19 | :root {
  20 |     --pn-bg: #0A0A0F;
  21 |     --pn-surface: #0a0a0a;
  22 |     --pn-surface-2: #111;
  23 |     --pn-border: #1a1a1a;
  24 |     --pn-border-active: #333;
  25 |     --pn-text: #fff;
  26 |     --pn-text-secondary: #888;
  27 |     --pn-muted: #555;
  28 |     --pn-red: #CC2222;
  29 |     --pn-red-dim: rgba(204,34,34,0.12);
  30 |     --pn-gold: #f8c15c;
  31 |     --pn-white: #fff;
  32 | }
  33 | 
  34 | * { box-sizing: border-box; }
  35 | 
  36 | body.panopticon-body {
  37 |     background: var(--pn-bg) !important;
  38 |     color: var(--pn-text);
  39 |     font-family: 'Inter', -apple-system, sans-serif;
  40 |     margin: 0;
  41 |     padding: 0;
  42 |     overflow-x: hidden;
  43 |     -webkit-font-smoothing: antialiased;
  44 | }
  45 | body.panopticon-body nav,
  46 | body.panopticon-body .navbar,
  47 | body.panopticon-body footer,
  48 | body.panopticon-body .site-footer,
  49 | body.panopticon-body .pp-nav,
  50 | body.panopticon-body .pp-footer { display: none !important; }
  51 | 
  52 | /* ── HERO SECTION — RADAR SWEEP ─────────────────────────────── */
  53 | .pn-hero {
  54 |     position: relative;
  55 |     width: 100%;
  56 |     height: clamp(320px, 18vh, 400px);
  57 |     min-height: 320px;
  58 |     overflow: hidden;
  59 |     display: flex;
  60 |     align-items: center;
  61 |     justify-content: center;
  62 |     flex-direction: column;
  63 |     border-bottom: 1px solid var(--pn-border);
  64 | }
  65 | .pn-hero-radar {
  66 |     position: absolute;
  67 |     inset: 0;
  68 |     overflow: hidden;
  69 | }
  70 | /* Radar concentric rings */
  71 | .pn-radar-rings {
  72 |     position: absolute;
  73 |     top: 50%;
  74 |     left: 50%;
  75 |     width: 600px;
  76 |     height: 600px;
  77 |     transform: translate(-50%, -50%);
  78 | }
  79 | .pn-radar-ring {
  80 |     position: absolute;
  81 |     top: 50%;
  82 |     left: 50%;
  83 |     border: 1px solid rgba(255,59,95,0.06);
  84 |     border-radius: 50%;
  85 | }
  86 | .pn-radar-ring:nth-child(1) { width: 150px; height: 150px; transform: translate(-50%,-50%); }
  87 | .pn-radar-ring:nth-child(2) { width: 300px; height: 300px; transform: translate(-50%,-50%); }
  88 | .pn-radar-ring:nth-child(3) { width: 450px; height: 450px; transform: translate(-50%,-50%); }
  89 | .pn-radar-ring:nth-child(4) { width: 600px; height: 600px; transform: translate(-50%,-50%); }
  90 | /* Crosshairs */
  91 | .pn-radar-cross {
  92 |     position: absolute;
  93 |     top: 50%;
  94 |     left: 50%;
  95 |     width: 600px;
  96 |     height: 600px;
  97 |     transform: translate(-50%,-50%);
  98 | }
  99 | .pn-radar-cross::before,
 100 | .pn-radar-cross::after {
 101 |     content: '';
 102 |     position: absolute;
 103 |     background: rgba(255,59,95,0.04);
 104 | }
 105 | .pn-radar-cross::before {
 106 |     top: 0;
 107 |     left: 50%;
 108 |     width: 1px;
 109 |     height: 100%;
 110 | }
 111 | .pn-radar-cross::after {
 112 |     top: 50%;
 113 |     left: 0;
 114 |     width: 100%;
 115 |     height: 1px;
 116 | }
 117 | /* Rotating sweep beam */
 118 | .pn-radar-sweep {
 119 |     position: absolute;
 120 |     top: 50%;
 121 |     left: 50%;
 122 |     width: 300px;
 123 |     height: 300px;
 124 |     transform-origin: 0 0;
 125 |     animation: radarSweep 6s linear infinite;
 126 |     background: conic-gradient(
 127 |         from 0deg,
 128 |         transparent 0deg,
 129 |         rgba(255,59,95,0.15) 10deg,
 130 |         rgba(255,59,95,0.08) 30deg,
 131 |         transparent 60deg
 132 |     );
 133 |     border-radius: 0 300px 0 0;
 134 |     pointer-events: none;
 135 | }
 136 | @keyframes radarSweep {
 137 |     from { transform: rotate(0deg); }
 138 |     to { transform: rotate(360deg); }
 139 | }
 140 | /* Scan lines */
 141 | .pn-scanlines {
 142 |     position: absolute;
 143 |     inset: 0;
 144 |     background: repeating-linear-gradient(
 145 |         to bottom,
 146 |         transparent 0px,
 147 |         transparent 2px,
 148 |         rgba(255,59,95,0.015) 2px,
 149 |         rgba(255,59,95,0.015) 4px
 150 |     );
 151 |     pointer-events: none;
 152 | }
 153 | /* Hero content */
 154 | .pn-hero-content {
 155 |     position: relative;
 156 |     z-index: 2;
 157 |     text-align: center;
 158 | }
 159 | .pn-hero-title {
 160 |     font-family: 'JetBrains Mono', monospace;
 161 |     font-weight: 800;
 162 |     font-size: clamp(32px, 3vw, 52px);
 163 |     letter-spacing: clamp(6px, 0.7vw, 14px);
 164 |     text-transform: uppercase;
 165 |     color: var(--pn-red);
 166 |     margin: 0 0 10px;
 167 |     text-shadow: 0 0 40px rgba(255,59,95,0.3);
 168 | }
 169 | .pn-hero-tagline {
 170 |     font-family: 'JetBrains Mono', monospace;
 171 |     font-size: clamp(12px, 0.9vw, 15px);
 172 |     letter-spacing: clamp(4px, 0.4vw, 7px);
 173 |     text-transform: uppercase;
 174 |     color: var(--pn-text-secondary);
 175 |     margin: 0 0 28px;
 176 | }
 177 | .pn-hero-stats {
 178 |     display: flex;
 179 |     gap: clamp(24px, 2.5vw, 48px);
 180 |     justify-content: center;
 181 |     align-items: center;
 182 |     min-height: clamp(60px, 6vh, 84px);
 183 |     padding: 0 clamp(16px, 2vw, 32px);
 184 |     flex-wrap: wrap;
 185 | }
 186 | .pn-hero-stat {
 187 |     text-align: center;
 188 |     min-width: 92px;
 189 | }
 190 | .pn-hero-stat-val {
 191 |     font-family: 'JetBrains Mono', monospace;
 192 |     font-size: clamp(22px, 1.9vw, 32px);
 193 |     font-weight: 700;
 194 |     color: var(--pn-white);
 195 |     line-height: 1.1;
 196 | }
 197 | .pn-hero-stat-label {
 198 |     font-family: 'JetBrains Mono', monospace;
 199 |     font-size: clamp(10px, 0.7vw, 13px);
 200 |     letter-spacing: clamp(1.5px, 0.15vw, 2.5px);
 201 |     text-transform: uppercase;
 202 |     color: var(--pn-muted);
 203 |     margin-top: 6px;
 204 | }
 205 | .pn-hero-stat-sep {
 206 |     width: 1px;
 207 |     height: clamp(28px, 2.5vh, 44px);
 208 |     background: var(--pn-border);
 209 | }
 210 | /* Header bar */
 211 | .pn-topbar {
 212 |     position: sticky;
 213 |     top: 0;
 214 |     z-index: 100;
 215 |     display: flex;
 216 |     align-items: center;
 217 |     justify-content: space-between;
 218 |     padding: 8px 16px;
 219 |     background: rgba(0,0,0,0.92);
 220 |     backdrop-filter: blur(12px);
 221 |     -webkit-backdrop-filter: blur(12px);
 222 |     border-bottom: 1px solid var(--pn-border);
 223 | }
 224 | .pn-topbar-left {
 225 |     display: flex;
 226 |     align-items: center;
 227 |     gap: 16px;
 228 | }
 229 | .pn-topbar-logo {
 230 |     font-family: 'JetBrains Mono', monospace;
 231 |     font-weight: 800;
 232 |     font-size: 12px;
 233 |     letter-spacing: 3px;
 234 |     color: var(--pn-red);
 235 | }
 236 | .pn-topbar-status {
 237 |     display: flex;
 238 |     align-items: center;
 239 |     gap: 6px;
 240 |     font-family: 'JetBrains Mono', monospace;
 241 |     font-size: 10px;
 242 |     color: var(--pn-red);
 243 |     letter-spacing: 1px;
 244 | }
 245 | .pn-topbar-dot {
 246 |     width: 6px;
 247 |     height: 6px;
 248 |     border-radius: 50%;
 249 |     background: var(--pn-red);
 250 |     animation: pnPulse 2s ease-in-out infinite;
 251 | }
 252 | @keyframes pnPulse {
 253 |     0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(255,59,95,0.5); }
 254 |     50% { opacity: 0.4; box-shadow: 0 0 0 4px rgba(255,59,95,0); }
 255 | }
 256 | .pn-topbar-right {
 257 |     display: flex;
 258 |     align-items: center;
 259 |     gap: 20px;
 260 | }
 261 | .pn-topbar-clock {
 262 |     font-family: 'JetBrains Mono', monospace;
 263 |     font-size: 13px;
 264 |     font-weight: 500;
 265 |     color: var(--pn-white);
 266 |     letter-spacing: 1px;
 267 | }
 268 | .pn-topbar-btc {
 269 |     font-family: 'JetBrains Mono', monospace;
 270 |     font-size: 13px;
 271 |     font-weight: 700;
 272 |     color: var(--pn-gold);
 273 | }
 274 | .pn-topbar-back {
 275 |     color: var(--pn-muted);
 276 |     text-decoration: none;
 277 |     font-family: 'JetBrains Mono', monospace;
 278 |     font-size: 10px;
 279 |     letter-spacing: 1px;
 280 |     transition: color 0.2s;
 281 | }
 282 | .pn-topbar-back:hover { color: var(--pn-white); }
 283 | 
 284 | /* ── LIVE TICKER ─────────────────────────────────────────────── */
 285 | .pn-ticker {
 286 |     display: flex;
 287 |     align-items: center;
 288 |     padding: clamp(8px, 0.8vw, 12px) clamp(16px, 1.5vw, 24px);
 289 |     border-bottom: 1px solid var(--pn-border);
 290 |     background: var(--pn-surface);
 291 |     gap: clamp(12px, 1.2vw, 18px);
 292 |     overflow: hidden;
 293 |     min-height: clamp(36px, 3vh, 44px);
 294 | }
 295 | .pn-ticker-tag {
 296 |     font-family: 'JetBrains Mono', monospace;
 297 |     font-size: clamp(10px, 0.7vw, 12px);
 298 |     font-weight: 800;
 299 |     letter-spacing: clamp(1.5px, 0.15vw, 2.5px);
 300 |     text-transform: uppercase;
 301 |     color: var(--pn-red);
 302 |     padding: 3px 10px;
 303 |     border: 1px solid rgba(255,59,95,0.3);
 304 |     background: rgba(255,59,95,0.06);
 305 |     white-space: nowrap;
 306 |     flex-shrink: 0;
 307 | }
 308 | .pn-ticker-scroll {
 309 |     flex: 1;
 310 |     overflow: hidden;
 311 |     position: relative;
 312 |     height: clamp(18px, 1.4vh, 22px);
 313 | }
 314 | .pn-ticker-text {
 315 |     font-family: 'JetBrains Mono', monospace;
 316 |     font-size: clamp(11px, 0.8vw, 13px);
 317 |     color: var(--pn-text-secondary);
 318 |     white-space: nowrap;
 319 |     position: absolute;
 320 |     animation: tickerScroll 40s linear infinite;
 321 | }
 322 | @keyframes tickerScroll {
 323 |     0% { transform: translateX(0); }
 324 |     100% { transform: translateX(-50%); }
 325 | }
 326 | 
 327 | /* ── MAIN GRID — 2-ZONE LAYOUT (evidence left, intel right) ─── */
 328 | .pn-main {
 329 |     max-width: clamp(1280px, 94vw, 2400px);
 330 |     margin: 0 auto;
 331 |     padding: 0 clamp(0px, 1vw, 24px);
 332 | }
 333 | .pn-grid {
 334 |     display: grid;
 335 |     grid-template-columns: 65fr 35fr;
 336 |     gap: clamp(16px, 1.5vw, 28px);
 337 |     background: transparent;
 338 |     min-height: calc(100vh - 420px);
 339 |     padding: clamp(16px, 1.5vw, 28px) 0;
 340 |     align-items: start;
 341 | }
 342 | .pn-grid > .pn-right-rail {
 343 |     position: sticky;
 344 |     top: 52px;
 345 |     max-height: calc(100vh - 64px);
 346 |     overflow-y: auto;
 347 |     scrollbar-width: thin;
 348 |     scrollbar-color: rgba(255,59,95,0.25) transparent;
 349 | }
 350 | .pn-grid > .pn-right-rail::-webkit-scrollbar { width: 3px; }
 351 | .pn-grid > .pn-right-rail::-webkit-scrollbar-thumb { background: rgba(255,59,95,0.25); border-radius: 2px; }
 352 | @media (max-width: 1100px) {
 353 |     .pn-grid { grid-template-columns: 1fr; }
 354 |     .pn-grid > .pn-right-rail { position: static; max-height: none; }
 355 | }
 356 | @media (max-width: 768px) {
 357 |     .pn-grid { grid-template-columns: 1fr; gap: 12px; padding: 12px 0; }
 358 |     .pn-hero { height: 240px; min-height: 240px; }
 359 |     .pn-hero-title { font-size: 24px; letter-spacing: 6px; }
 360 |     .pn-hero-tagline { font-size: 11px; letter-spacing: 3px; }
 361 |     .pn-hero-stats { flex-wrap: wrap; gap: 16px; min-height: 0; }
 362 |     .pn-hero-stat-val { font-size: 18px; }
 363 |     .pn-hero-stat-label { font-size: 10px; }
 364 | }
 365 | 
 366 | /* ── PANEL ────────────────────────────────────────────────────── */
 367 | .pn-panel {
 368 |     background: var(--pn-bg);
 369 |     padding: clamp(20px, 2vw, 32px) clamp(16px, 1.5vw, 24px);
 370 |     position: relative;
 371 |     overflow-y: auto;
 372 |     max-height: calc(100vh - 200px);
 373 |     border: 1px solid var(--pn-border);
 374 |     border-radius: 6px;
 375 | }
 376 | .pn-panel-head {
 377 |     font-family: 'JetBrains Mono', monospace;
 378 |     font-size: clamp(12px, 0.85vw, 15px);
 379 |     font-weight: 700;
 380 |     text-transform: uppercase;
 381 |     letter-spacing: clamp(1.5px, 0.18vw, 2.5px);
 382 |     margin-bottom: clamp(16px, 1.4vw, 22px);
 383 |     padding-bottom: clamp(10px, 1vw, 14px);
 384 |     padding-left: 12px;
 385 |     border-bottom: 1px solid var(--pn-border);
 386 |     display: flex;
 387 |     align-items: center;
 388 |     gap: 10px;
 389 |     flex-wrap: wrap;
 390 | }
 391 | /* Mission-control left accent on panel headers */
 392 | .pn-tier-confirmed .pn-panel-head { border-left: 2px solid var(--pn-red); }
 393 | .pn-tier-flagged .pn-panel-head { border-left: 2px solid var(--pn-gold); }
 394 | .pn-tier-feed .pn-panel-head { border-left: 2px solid var(--pn-white); }
 395 | /* Animated pulse dot for TIER 1 header */
 396 | .pn-tier-confirmed .pn-panel-head .tier-dot {
 397 |     animation: pnPulse 2s ease-in-out infinite;
 398 | }
 399 | .pn-panel-head .tier-dot {
 400 |     width: 8px;
 401 |     height: 8px;
 402 |     border-radius: 50%;
 403 |     flex-shrink: 0;
 404 | }
 405 | .pn-panel-head .tier-label {
 406 |     flex: 1;
 407 | }
 408 | .pn-panel-head .tier-count {
 409 |     font-size: clamp(10px, 0.7vw, 12px);
 410 |     color: var(--pn-muted);
 411 |     font-weight: 500;
 412 | }
 413 | .pn-tier-confirmed .tier-dot { background: var(--pn-red); box-shadow: 0 0 8px rgba(255,59,95,0.4); }
 414 | .pn-tier-confirmed .pn-panel-head { color: var(--pn-red); }
 415 | .pn-tier-flagged .tier-dot { background: var(--pn-gold); box-shadow: 0 0 8px rgba(248,193,92,0.4); }
 416 | .pn-tier-flagged .pn-panel-head { color: var(--pn-gold); }
 417 | .pn-tier-feed .tier-dot { background: var(--pn-white); box-shadow: 0 0 8px rgba(255,255,255,0.3); }
 418 | .pn-tier-feed .pn-panel-head { color: var(--pn-white); }
 419 | 
 420 | .pn-section-label {
 421 |     font-family: 'JetBrains Mono', monospace;
 422 |     font-size: clamp(11px, 0.75vw, 13px);
 423 |     font-weight: 700;
 424 |     letter-spacing: clamp(1.5px, 0.18vw, 2.5px);
 425 |     text-transform: uppercase;
 426 |     color: var(--pn-muted);
 427 |     margin: clamp(24px, 2vw, 36px) 0 clamp(14px, 1.2vw, 18px);
 428 |     padding: clamp(16px, 1.4vw, 20px) 0 0 12px;
 429 |     border-top: 1px solid var(--pn-border);
 430 |     border-left: 2px solid rgba(255,59,95,0.3);
 431 | }
 432 | 
 433 | /* ── DISCLOSURE CARDS — elevated with party-colored borders ─── */
 434 | .pn-disc-card {
 435 |     background: var(--pn-surface);
 436 |     border: 1px solid var(--pn-border);
 437 |     border-left: 3px solid var(--pn-red);
 438 |     padding: 14px 16px;
 439 |     margin-bottom: clamp(10px, 1vw, 14px);
 440 |     border-radius: 4px;
 441 |     transition: border-color 0.3s, transform 0.3s;
 442 |     opacity: 0;
 443 |     transform: translateX(-8px);
 444 |     animation: cardEnter 0.4s ease forwards;
 445 |     position: relative;
 446 | }
 447 | /* Party-colored left border */
 448 | .pn-disc-card[data-party="R"] { border-left-color: var(--pn-red); }
 449 | .pn-disc-card[data-party="D"] { border-left-color: #3b82f6; }
 450 | .pn-disc-card[data-party="I"] { border-left-color: #888; }
 451 | /* Gradient separator between cards */
 452 | .pn-disc-card + .pn-disc-card::before {
 453 |     content: '';
 454 |     display: block;
 455 |     position: absolute;
 456 |     top: -6px;
 457 |     left: 10%;
 458 |     right: 10%;
 459 |     height: 1px;
 460 |     background: linear-gradient(90deg, transparent, rgba(255,59,95,0.12), transparent);
 461 | }
 462 | .pn-disc-card:nth-child(1) { animation-delay: 0.1s; }
 463 | .pn-disc-card:nth-child(2) { animation-delay: 0.2s; }
 464 | .pn-disc-card:nth-child(3) { animation-delay: 0.3s; }
 465 | .pn-disc-card:nth-child(4) { animation-delay: 0.4s; }
 466 | .pn-disc-card:nth-child(5) { animation-delay: 0.5s; }
 467 | @keyframes cardEnter {
 468 |     to { opacity: 1; transform: translateX(0); }
 469 | }
 470 | .pn-disc-card:hover { border-color: var(--pn-red); }
 471 | .pn-disc-head {
 472 |     display: flex;
 473 |     justify-content: space-between;
 474 |     align-items: center;
 475 |     margin-bottom: 10px;
 476 |     gap: 8px;
 477 | }
 478 | /* Amount range tag — subtle right-aligned */
 479 | .pn-disc-amount-tag {
 480 |     font-family: 'JetBrains Mono', monospace;
 481 |     font-size: 9px;
 482 |     color: var(--pn-text-secondary);
 483 |     background: rgba(255,255,255,0.03);
 484 |     border: 1px solid var(--pn-border);
 485 |     padding: 2px 8px;
 486 |     border-radius: 3px;
 487 |     white-space: nowrap;
 488 |     flex-shrink: 0;
 489 | }
 490 | .pn-disc-entity {
 491 |     font-size: 13px;
 492 |     font-weight: 700;
 493 |     color: var(--pn-white);
 494 |     overflow: hidden;
 495 |     white-space: nowrap;
 496 |     text-overflow: ellipsis;
 497 |     line-height: 1.35;
 498 | }
 499 | /* Typewriter effect for entity names */
 500 | .pn-disc-entity.typewriter {
 501 |     border-right: 2px solid var(--pn-red);
 502 |     animation: typewriterBlink 0.7s step-end infinite;
 503 |     width: 0;
 504 |     display: inline-block;
 505 | }
 506 | @keyframes typewriterBlink {
 507 |     50% { border-color: transparent; }
 508 | }
 509 | .pn-disc-party {
 510 |     font-family: 'JetBrains Mono', monospace;
 511 |     font-size: 8px;
 512 |     font-weight: 700;
 513 |     padding: 2px 8px;
 514 |     letter-spacing: 1px;
 515 |     flex-shrink: 0;
 516 |     border-radius: 10px;
 517 | }
 518 | .pn-disc-party.R { background: rgba(255,59,95,0.15); color: var(--pn-red); border: 1px solid rgba(255,59,95,0.3); }
 519 | .pn-disc-party.D { background: rgba(59,130,246,0.12); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); }
 520 | .pn-disc-party.I { background: rgba(255,255,255,0.05); color: var(--pn-muted); border: 1px solid rgba(255,255,255,0.1); }
 521 | .pn-disc-fields {
 522 |     display: grid;
 523 |     grid-template-columns: 1fr 1fr;
 524 |     gap: clamp(8px, 0.8vw, 14px);
 525 | }
 526 | .pn-disc-field-label {
 527 |     font-family: 'JetBrains Mono', monospace;
 528 |     font-size: clamp(10px, 0.7vw, 11px);
 529 |     font-weight: 700;
 530 |     letter-spacing: clamp(1.2px, 0.12vw, 1.8px);
 531 |     text-transform: uppercase;
 532 |     color: var(--pn-muted);
 533 |     margin-bottom: 3px;
 534 | }
 535 | .pn-disc-field-val {
 536 |     font-family: 'JetBrains Mono', monospace;
 537 |     font-size: 12px;
 538 |     font-weight: 500;
 539 |     color: var(--pn-white);
 540 |     line-height: 1.35;
 541 | }
 542 | /* Asset name in gold, Type in small caps */
 543 | .pn-disc-field-val.asset-val { color: var(--pn-gold); font-size: 11px; }
 544 | .pn-disc-field-val.type-val { font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; }
 545 | .pn-disc-field-val.buy { color: #89ffb8; }
 546 | .pn-disc-field-val.sell { color: var(--pn-red); }
 547 | .pn-disc-correlation {
 548 |     margin-top: 10px;
 549 |     padding: 8px 10px;
 550 |     background: rgba(255,59,95,0.04);
 551 |     border: 1px solid rgba(255,59,95,0.12);
 552 |     font-family: 'JetBrains Mono', monospace;
 553 |     font-size: 10px;
 554 |     color: var(--pn-red);
 555 |     line-height: 1.4;
 556 |     position: relative;
 557 |     overflow: hidden;
 558 | }
 559 | .pn-disc-correlation::before {
 560 |     content: "PATTERN DETECTED";
 561 |     display: block;
 562 |     font-size: 8px;
 563 |     font-weight: 800;
 564 |     letter-spacing: 2px;
 565 |     margin-bottom: 4px;
 566 |     opacity: 0.7;
 567 | }
 568 | /* Red ripple pulse on PATTERN DETECTED */
 569 | .pn-disc-correlation::after {
 570 |     content: '';
 571 |     position: absolute;
 572 |     top: 50%;
 573 |     left: 50%;
 574 |     width: 200%;
 575 |     height: 200%;
 576 |     transform: translate(-50%,-50%) scale(0);
 577 |     background: radial-gradient(circle, rgba(255,59,95,0.08) 0%, transparent 70%);
 578 |     animation: patternPulse 3s ease-out infinite;
 579 |     pointer-events: none;
 580 | }
 581 | @keyframes patternPulse {
 582 |     0% { transform: translate(-50%,-50%) scale(0); opacity: 1; }
 583 |     100% { transform: translate(-50%,-50%) scale(1); opacity: 0; }
 584 | }
 585 | .pn-disc-source {
 586 |     margin-top: 8px;
 587 |     font-family: 'JetBrains Mono', monospace;
 588 |     font-size: 9px;
 589 |     color: var(--pn-muted);
 590 | }
 591 | .pn-disc-source a { color: var(--pn-text-secondary); text-decoration: none; }
 592 | .pn-disc-source a:hover { color: var(--pn-red); }
 593 | 
 594 | /* ── TIER BADGE ANIMATION ─────────────────────────────────────── */
 595 | .pn-tier-badge {
 596 |     font-family: 'JetBrains Mono', monospace;
 597 |     font-size: 8px;
 598 |     font-weight: 800;
 599 |     letter-spacing: 2px;
 600 |     padding: 3px 10px;
 601 |     text-transform: uppercase;
 602 |     opacity: 0;
 603 |     transform: scale(0.8);
 604 |     animation: badgeReveal 0.4s ease forwards;
 605 | }
 606 | .pn-tier-badge.tier-1 {
 607 |     background: rgba(255,59,95,0.12);
 608 |     color: var(--pn-red);
 609 |     border: 1px solid rgba(255,59,95,0.25);
 610 |     animation-delay: 0.6s;
 611 | }
 612 | .pn-tier-badge.tier-2 {
 613 |     background: rgba(248,193,92,0.12);
 614 |     color: var(--pn-gold);
 615 |     border: 1px solid rgba(248,193,92,0.25);
 616 |     animation-delay: 0.7s;
 617 | }
 618 | @keyframes badgeReveal {
 619 |     to { opacity: 1; transform: scale(1); }
 620 | }
 621 | 
 622 | /* ── CORRELATION TIMELINE SVG ─────────────────────────────────── */
 623 | .pn-corr-timeline {
 624 |     margin: 12px 0;
 625 |     padding: 16px;
 626 |     background: var(--pn-surface);
 627 |     border: 1px solid var(--pn-border);
 628 |     overflow-x: auto;
 629 | }
 630 | .pn-corr-timeline svg {
 631 |     display: block;
 632 |     margin: 0 auto;
 633 |     overflow: visible;
 634 | }
 635 | .pn-corr-node {
 636 |     cursor: default;
 637 | }
 638 | .pn-corr-node circle {
 639 |     transition: r 0.3s ease;
 640 | }
 641 | .pn-corr-node:hover circle {
 642 |     r: 14;
 643 | }
 644 | .pn-corr-path {
 645 |     fill: none;
 646 |     stroke-linecap: round;
 647 |     animation: pathDraw 1.5s ease forwards;
 648 |     stroke-dasharray: 300;
 649 |     stroke-dashoffset: 300;
 650 | }
 651 | @keyframes pathDraw {
 652 |     to { stroke-dashoffset: 0; }
 653 | }
 654 | .pn-corr-summary {
 655 |     font-family: 'Inter', sans-serif;
 656 |     font-size: 12px;
 657 |     color: var(--pn-text-secondary);
 658 |     line-height: 1.5;
 659 |     margin: 10px 0;
 660 | }
 661 | .pn-corr-event-row {
 662 |     display: flex;
 663 |     align-items: center;
 664 |     gap: 8px;
 665 |     padding: 6px 10px;
 666 |     background: rgba(255,255,255,0.02);
 667 |     margin-bottom: 4px;
 668 |     font-family: 'JetBrains Mono', monospace;
 669 |     font-size: 10px;
 670 |     color: var(--pn-text-secondary);
 671 | }
 672 | .pn-corr-event-tag {
 673 |     font-size: 8px;
 674 |     font-weight: 800;
 675 |     letter-spacing: 1px;
 676 |     padding: 2px 6px;
 677 |     text-transform: uppercase;
 678 |     flex-shrink: 0;
 679 | }
 680 | .pn-corr-event-tag.disclosure { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 681 | .pn-corr-event-tag.whale { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 682 | .pn-corr-event-tag.geo { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
 683 | 
 684 | .pn-disclaimer-note {
 685 |     margin-bottom: 12px;
 686 |     padding: 8px 12px;
 687 |     background: rgba(255,59,95,0.03);
 688 |     border: 1px solid rgba(255,59,95,0.08);
 689 |     font-family: 'JetBrains Mono', monospace;
 690 |     font-size: 9px;
 691 |     color: var(--pn-muted);
 692 |     letter-spacing: 0.5px;
 693 |     line-height: 1.5;
 694 | }
 695 | 
 696 | /* ── WHALE CASCADE FEED ──────────────────────────────────────── */
 697 | .pn-whale-item {
 698 |     background: var(--pn-surface);
 699 |     border: 1px solid var(--pn-border);
 700 |     padding: 12px 14px;
 701 |     margin-bottom: 6px;
 702 |     position: relative;
 703 |     opacity: 0;
 704 |     transform: translateY(-20px);
 705 |     animation: whaleDrop 0.5s ease forwards;
 706 | }
 707 | .pn-whale-item:nth-child(1) { animation-delay: 0.1s; }
 708 | .pn-whale-item:nth-child(2) { animation-delay: 0.25s; }
 709 | .pn-whale-item:nth-child(3) { animation-delay: 0.4s; }
 710 | .pn-whale-item:nth-child(4) { animation-delay: 0.55s; }
 711 | .pn-whale-item:nth-child(5) { animation-delay: 0.7s; }
 712 | @keyframes whaleDrop {
 713 |     to { opacity: 1; transform: translateY(0); }
 714 | }
 715 | .pn-whale-item.inflow { border-left: 3px solid var(--pn-red); }
 716 | .pn-whale-item.outflow { border-left: 3px solid var(--pn-white); }
 717 | .pn-whale-row {
 718 |     display: flex;
 719 |     justify-content: space-between;
 720 |     align-items: center;
 721 |     margin-bottom: 4px;
 722 | }
 723 | .pn-whale-entity {
 724 |     font-size: 12px;
 725 |     font-weight: 600;
 726 |     color: var(--pn-white);
 727 | }
 728 | .pn-whale-type-tag {
 729 |     font-family: 'JetBrains Mono', monospace;
 730 |     font-size: 8px;
 731 |     font-weight: 700;
 732 |     letter-spacing: 1px;
 733 |     text-transform: uppercase;
 734 |     padding: 2px 6px;
 735 | }
 736 | .pn-whale-type-tag.inflow { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 737 | .pn-whale-type-tag.outflow { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 738 | .pn-whale-amt {
 739 |     font-family: 'JetBrains Mono', monospace;
 740 |     font-size: 20px;
 741 |     font-weight: 700;
 742 | }
 743 | .pn-whale-amt.inflow { color: var(--pn-red); }
 744 | .pn-whale-amt.outflow { color: var(--pn-white); }
 745 | .pn-whale-usd {
 746 |     font-family: 'JetBrains Mono', monospace;
 747 |     font-size: 11px;
 748 |     color: var(--pn-text-secondary);
 749 |     margin-bottom: 6px;
 750 | }
 751 | .pn-whale-meta {
 752 |     display: flex;
 753 |     justify-content: space-between;
 754 |     font-family: 'JetBrains Mono', monospace;
 755 |     font-size: 9px;
 756 |     color: var(--pn-muted);
 757 | }
 758 | .pn-whale-meta a { color: var(--pn-text-secondary); text-decoration: none; }
 759 | .pn-whale-meta a:hover { color: var(--pn-red); }
 760 | /* Whale size indicator (logarithmic glow bar) */
 761 | .pn-whale-size-bar {
 762 |     height: 2px;
 763 |     background: var(--pn-red);
 764 |     margin-top: 8px;
 765 |     border-radius: 1px;
 766 |     box-shadow: 0 0 6px rgba(255,59,95,0.4);
 767 |     transition: width 0.6s ease;
 768 | }
 769 | 
 770 | /* ── POLYMARKET ──────────────────────────────────────────────── */
 771 | .pn-poly-item {
 772 |     background: var(--pn-surface);
 773 |     border: 1px solid var(--pn-border);
 774 |     padding: 12px 14px;
 775 |     margin-bottom: 6px;
 776 | }
 777 | .pn-poly-question {
 778 |     font-size: 11px;
 779 |     font-weight: 600;
 780 |     color: var(--pn-white);
 781 |     margin-bottom: 8px;
 782 |     line-height: 1.3;
 783 | }
 784 | .pn-poly-row {
 785 |     display: flex;
 786 |     align-items: center;
 787 |     gap: 8px;
 788 |     margin-bottom: 6px;
 789 | }
 790 | .pn-poly-pct {
 791 |     font-family: 'JetBrains Mono', monospace;
 792 |     font-size: 20px;
 793 |     font-weight: 700;
 794 | }
 795 | /* Colored percentage — green >60, red <40, gold else */
 796 | .pn-poly-pct.pct-high { color: #22c55e; }
 797 | .pn-poly-pct.pct-low { color: var(--pn-red); }
 798 | .pn-poly-pct.pct-mid { color: var(--pn-gold); }
 799 | .pn-poly-yes {
 800 |     font-family: 'JetBrains Mono', monospace;
 801 |     font-size: 9px;
 802 |     color: var(--pn-muted);
 803 |     text-transform: uppercase;
 804 | }
 805 | .pn-poly-signal {
 806 |     margin-left: auto;
 807 |     font-family: 'JetBrains Mono', monospace;
 808 |     font-size: 9px;
 809 |     font-weight: 700;
 810 |     letter-spacing: 1px;
 811 |     padding: 2px 6px;
 812 |     text-transform: uppercase;
 813 | }
 814 | .pn-poly-signal.bullish { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 815 | .pn-poly-signal.bearish { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 816 | .pn-poly-signal.neutral { background: rgba(255,255,255,0.03); color: var(--pn-muted); }
 817 | .pn-poly-bar {
 818 |     height: 3px;
 819 |     background: var(--pn-border);
 820 |     margin-bottom: 8px;
 821 |     overflow: hidden;
 822 | }
 823 | .pn-poly-bar-fill {
 824 |     height: 100%;
 825 |     transition: width 0.8s ease;
 826 | }
 827 | .pn-poly-bar-fill.bullish { background: var(--pn-white); }
 828 | .pn-poly-bar-fill.bearish { background: var(--pn-red); }
 829 | .pn-poly-bar-fill.neutral { background: var(--pn-muted); }
 830 | .pn-poly-meta {
 831 |     display: flex;
 832 |     gap: 12px;
 833 |     font-family: 'JetBrains Mono', monospace;
 834 |     font-size: 9px;
 835 |     color: var(--pn-muted);
 836 | }
 837 | .pn-poly-meta a { color: var(--pn-text-secondary); text-decoration: none; }
 838 | .pn-poly-meta a:hover { color: var(--pn-red); }
 839 | 
 840 | /* ── FOREX / NATION-STATE ────────────────────────────────────── */
 841 | .pn-forex-item {
 842 |     display: flex;
 843 |     justify-content: space-between;
 844 |     align-items: center;
 845 |     padding: 8px 12px;
 846 |     background: var(--pn-surface);
 847 |     border: 1px solid var(--pn-border);
 848 |     margin-bottom: 4px;
 849 | }
 850 | .pn-forex-pair {
 851 |     font-family: 'JetBrains Mono', monospace;
 852 |     font-size: 12px;
 853 |     font-weight: 700;
 854 |     color: var(--pn-white);
 855 | }
 856 | .pn-forex-rate {
 857 |     font-family: 'JetBrains Mono', monospace;
 858 |     font-size: 14px;
 859 |     font-weight: 700;
 860 |     color: var(--pn-gold);
 861 | }
 862 | 
 863 | /* ── GEOPOLITICAL ────────────────────────────────────────────── */
 864 | .pn-geo-item {
 865 |     background: var(--pn-surface);
 866 |     border: 1px solid var(--pn-border);
 867 |     padding: 12px 14px;
 868 |     margin-bottom: 6px;
 869 | }
 870 | .pn-geo-headline {
 871 |     font-size: 13px;
 872 |     font-weight: 600;
 873 |     color: var(--pn-white);
 874 |     margin-bottom: 8px;
 875 |     line-height: 1.3;
 876 | }
 877 | .pn-geo-signal-tag {
 878 |     display: inline-flex;
 879 |     align-items: center;
 880 |     gap: 4px;
 881 |     font-family: 'JetBrains Mono', monospace;
 882 |     font-size: 9px;
 883 |     font-weight: 700;
 884 |     letter-spacing: 1px;
 885 |     padding: 2px 8px;
 886 |     text-transform: uppercase;
 887 |     margin-bottom: 6px;
 888 | }
 889 | .pn-geo-signal-tag.bullish { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 890 | .pn-geo-signal-tag.bearish { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 891 | .pn-geo-signal-tag.neutral { background: rgba(255,255,255,0.03); color: var(--pn-muted); }
 892 | .pn-geo-rationale {
 893 |     font-family: 'JetBrains Mono', monospace;
 894 |     font-size: 10px;
 895 |     color: var(--pn-text-secondary);
 896 |     line-height: 1.4;
 897 |     margin-top: 6px;
 898 | }
 899 | .pn-geo-meta {
 900 |     margin-top: 8px;
 901 |     font-family: 'JetBrains Mono', monospace;
 902 |     font-size: 9px;
 903 |     color: var(--pn-muted);
 904 |     display: flex;
 905 |     justify-content: space-between;
 906 | }
 907 | 
 908 | /* ── WATCHLIST ────────────────────────────────────────────────── */
 909 | .pn-watchlist-item {
 910 |     display: flex;
 911 |     align-items: center;
 912 |     gap: 12px;
 913 |     padding: 8px 12px;
 914 |     background: var(--pn-surface);
 915 |     border: 1px solid var(--pn-border);
 916 |     margin-bottom: 4px;
 917 | }
 918 | .pn-watchlist-name {
 919 |     font-size: 12px;
 920 |     font-weight: 600;
 921 |     color: var(--pn-white);
 922 |     min-width: 120px;
 923 | }
 924 | .pn-watchlist-note {
 925 |     font-family: 'JetBrains Mono', monospace;
 926 |     font-size: 10px;
 927 |     color: var(--pn-text-secondary);
 928 |     flex: 1;
 929 | }
 930 | 
 931 | /* ── MAKE THE BITCOIN CASE ───────────────────────────────────── */
 932 | .pn-btc-case-btn {
 933 |     display: inline-flex;
 934 |     align-items: center;
 935 |     gap: 6px;
 936 |     background: transparent;
 937 |     border: 1px solid var(--pn-red);
 938 |     color: var(--pn-red);
 939 |     font-family: 'JetBrains Mono', monospace;
 940 |     font-size: 10px;
 941 |     font-weight: 700;
 942 |     letter-spacing: 1px;
 943 |     padding: 8px 16px;
 944 |     cursor: pointer;
 945 |     margin-top: 10px;
 946 |     transition: all 0.2s;
 947 |     text-transform: uppercase;
 948 | }
 949 | .pn-btc-case-btn:hover {
 950 |     background: rgba(255,59,95,0.08);
 951 | }
 952 | .pn-btc-case-btn:disabled {
 953 |     opacity: 0.5;
 954 |     cursor: not-allowed;
 955 | }
 956 | .pn-btc-case-output {
 957 |     display: none;
 958 |     margin-top: 10px;
 959 |     padding: 14px;
 960 |     background: var(--pn-surface);
 961 |     border: 1px solid rgba(248,193,92,0.15);
 962 |     font-family: 'JetBrains Mono', monospace;
 963 |     font-size: 11px;
 964 |     color: var(--pn-gold);
 965 |     line-height: 1.6;
 966 | }
 967 | .pn-btc-case-output.visible { display: block; }
 968 | .pn-btc-case-label {
 969 |     font-size: 8px;
 970 |     font-weight: 800;
 971 |     letter-spacing: 2px;
 972 |     color: var(--pn-gold);
 973 |     margin-bottom: 8px;
 974 |     opacity: 0.6;
 975 | }
 976 | .pn-typewriter-cursor {
 977 |     display: inline-block;
 978 |     width: 2px;
 979 |     height: 14px;
 980 |     background: var(--pn-gold);
 981 |     margin-left: 1px;
 982 |     animation: cursorBlink 0.5s step-end infinite;
 983 |     vertical-align: text-bottom;
 984 | }
 985 | @keyframes cursorBlink {
 986 |     50% { opacity: 0; }
 987 | }
 988 | .pn-btc-case-model {
 989 |     margin-top: 8px;
 990 |     font-size: 9px;
 991 |     color: var(--pn-muted);
 992 | }
 993 | 
 994 | /* ── CLASSIFIED OVERLAY ──────────────────────────────────────── */
 995 | .pn-classified-overlay {
 996 |     position: absolute;
 997 |     inset: 0;
 998 |     z-index: 10;
 999 |     backdrop-filter: blur(12px);
1000 |     -webkit-backdrop-filter: blur(12px);
1001 |     background: rgba(0,0,0,0.6);
1002 |     display: flex;
1003 |     flex-direction: column;
1004 |     align-items: center;
1005 |     justify-content: center;
1006 |     gap: 12px;
1007 | }
1008 | .pn-classified-stamp {
1009 |     font-family: 'JetBrains Mono', monospace;
1010 |     font-size: 28px;
1011 |     font-weight: 800;
1012 |     letter-spacing: 8px;
1013 |     color: var(--pn-red);
1014 |     text-transform: uppercase;
1015 |     transform: rotate(-8deg);
1016 |     border: 3px solid var(--pn-red);
1017 |     padding: 8px 24px;
1018 |     opacity: 0.85;
1019 |     text-shadow: 0 0 20px rgba(255,59,95,0.4);
1020 | }
1021 | .pn-classified-sub {
1022 |     font-family: 'JetBrains Mono', monospace;
1023 |     font-size: 11px;
1024 |     color: var(--pn-text-secondary);
1025 |     letter-spacing: 2px;
1026 | }
1027 | .pn-upgrade-btn {
1028 |     display: inline-block;
1029 |     padding: 10px 24px;
1030 |     background: var(--pn-red);
1031 |     color: var(--pn-white);
1032 |     font-family: 'JetBrains Mono', monospace;
1033 |     font-size: 11px;
1034 |     font-weight: 700;
1035 |     letter-spacing: 2px;
1036 |     text-transform: uppercase;
1037 |     text-decoration: none;
1038 |     transition: all 0.2s;
1039 |     margin-top: 4px;
1040 | }
1041 | .pn-upgrade-btn:hover {
1042 |     background: #e0304f;
1043 |     box-shadow: 0 0 20px rgba(255,59,95,0.3);
1044 | }
1045 | 
1046 | /* ── FALLBACK BANNER ─────────────────────────────────────────── */
1047 | .pn-fallback-banner {
1048 |     background: rgba(255,59,95,0.04);
1049 |     border: 1px solid rgba(255,59,95,0.15);
1050 |     padding: 10px 14px;
1051 |     margin-bottom: 12px;
1052 |     font-family: 'JetBrains Mono', monospace;
1053 |     font-size: 10px;
1054 |     color: var(--pn-red);
1055 |     letter-spacing: 0.5px;
1056 | }
1057 | 
1058 | /* ── EMPTY / LOADING ─────────────────────────────────────────── */
1059 | .pn-empty {
1060 |     font-family: 'JetBrains Mono', monospace;
1061 |     font-size: 11px;
1062 |     color: var(--pn-muted);
1063 |     padding: 20px;
1064 |     text-align: center;
1065 | }
1066 | .pn-loading {
1067 |     display: flex;
1068 |     align-items: center;
1069 |     justify-content: center;
1070 |     gap: 6px;
1071 |     font-family: 'JetBrains Mono', monospace;
1072 |     font-size: 10px;
1073 |     color: var(--pn-muted);
1074 |     padding: 20px;
1075 | }
1076 | .pn-loading-dot {
1077 |     width: 4px;
1078 |     height: 4px;
1079 |     border-radius: 50%;
1080 |     background: var(--pn-red);
1081 |     animation: loadDot 1.2s ease-in-out infinite;
1082 | }
1083 | .pn-loading-dot:nth-child(2) { animation-delay: 0.2s; }
1084 | .pn-loading-dot:nth-child(3) { animation-delay: 0.4s; }
1085 | @keyframes loadDot {
1086 |     0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
1087 |     40% { opacity: 1; transform: scale(1.2); }
1088 | }
1089 | 
1090 | /* ── HISTORICAL PRECEDENTS TIMELINE (GLASSMORPHIC REBUILD) ─── */
1091 | .pn-history {
1092 |     max-width: 1800px;
1093 |     margin: 0 auto;
1094 |     padding: 32px 16px 40px;
1095 |     position: relative;
1096 | }
1097 | .pn-history-header {
1098 |     font-family: 'JetBrains Mono', monospace;
1099 |     font-size: 13px;
1100 |     font-weight: 700;
1101 |     letter-spacing: 0.3em;
1102 |     text-transform: uppercase;
1103 |     color: var(--pn-red);
1104 |     margin-bottom: 6px;
1105 | }
1106 | .pn-history-subhead {
1107 |     font-family: 'Inter', sans-serif;
1108 |     font-size: 12px;
1109 |     color: var(--pn-muted);
1110 |     margin-bottom: 24px;
1111 |     line-height: 1.6;
1112 | }
1113 | .pn-timeline-scroll {
1114 |     overflow-x: auto;
1115 |     overflow-y: visible;
1116 |     -webkit-overflow-scrolling: touch;
1117 |     padding-bottom: 16px;
1118 |     scrollbar-width: thin;
1119 |     scrollbar-color: rgba(255,59,95,0.3) transparent;
1120 | }
1121 | .pn-timeline-scroll::-webkit-scrollbar { height: 4px; }
1122 | .pn-timeline-scroll::-webkit-scrollbar-thumb { background: rgba(255,59,95,0.3); border-radius: 2px; }
1123 | .pn-timeline {
1124 |     display: flex;
1125 |     align-items: center;
1126 |     position: relative;
1127 |     min-width: max-content;
1128 |     padding: 140px 40px 140px;
1129 | }
1130 | /* Glowing red timeline line */
1131 | .pn-timeline::before {
1132 |     content: '';
1133 |     position: absolute;
1134 |     top: 50%;
1135 |     left: 20px;
1136 |     right: 20px;
1137 |     height: 1px;
1138 |     background: var(--pn-red);
1139 |     opacity: 0.6;
1140 |     transform: translateY(-50%);
1141 |     animation: tlGlow 3s ease-in-out infinite;
1142 | }
1143 | @keyframes tlGlow {
1144 |     0%, 100% { box-shadow: 0 0 4px rgba(255,59,95,0.4); }
1145 |     50% { box-shadow: 0 0 12px rgba(255,59,95,0.6); }
1146 | }
1147 | /* Timeline node container */
1148 | .pn-tl-node {
1149 |     position: relative;
1150 |     flex: 0 0 auto;
1151 |     min-width: 110px;
1152 |     text-align: center;
1153 |     display: flex;
1154 |     flex-direction: column;
1155 |     align-items: center;
1156 | }
1157 | /* Above-line events: label on top, dot connects to line */
1158 | .pn-tl-node.tl-above {
1159 |     flex-direction: column-reverse;
1160 |     margin-bottom: 0;
1161 |     margin-top: -120px;
1162 | }
1163 | /* Below-line events */
1164 | .pn-tl-node.tl-below {
1165 |     margin-top: 120px;
1166 | }
1167 | /* Year label */
1168 | .pn-tl-year {
1169 |     font-family: 'JetBrains Mono', monospace;
1170 |     font-size: 11px;
1171 |     font-weight: 800;
1172 |     color: var(--pn-red);
1173 |     margin-bottom: 2px;
1174 |     white-space: nowrap;
1175 | }
1176 | .tl-above .pn-tl-year { margin-bottom: 0; margin-top: 2px; }
1177 | /* Event name */
1178 | .pn-tl-name {
1179 |     font-family: 'Inter', sans-serif;
1180 |     font-size: 10px;
1181 |     font-weight: 600;
1182 |     color: var(--pn-white);
1183 |     line-height: 1.3;
1184 |     max-width: 100px;
1185 |     margin-bottom: 6px;
1186 |     opacity: 0.85;
1187 | }
1188 | .tl-above .pn-tl-name { margin-bottom: 0; margin-top: 6px; }
1189 | /* Stem connecting dot to label area */
1190 | .pn-tl-stem {
1191 |     width: 1px;
1192 |     height: 30px;
1193 |     background: linear-gradient(to bottom, rgba(255,59,95,0.5), rgba(255,59,95,0.1));
1194 | }
1195 | .tl-above .pn-tl-stem {
1196 |     background: linear-gradient(to top, rgba(255,59,95,0.5), rgba(255,59,95,0.1));
1197 | }
1198 | /* The clickable pin dot */
1199 | .pn-tl-dot {
1200 |     width: 16px;
1201 |     height: 16px;
1202 |     border-radius: 50%;
1203 |     background: var(--pn-red);
1204 |     cursor: pointer;
1205 |     position: relative;
1206 |     flex-shrink: 0;
1207 |     transition: transform 0.2s, box-shadow 0.2s;
1208 |     box-shadow: 0 0 6px rgba(255,59,95,0.4);
1209 |     animation: pinPulse 2s ease-in-out infinite;
1210 |     z-index: 2;
1211 | }
1212 | @keyframes pinPulse {
1213 |     0%, 100% { box-shadow: 0 0 6px rgba(255,59,95,0.4), 0 0 0 0 rgba(255,59,95,0.3); }
1214 |     50% { box-shadow: 0 0 8px rgba(255,59,95,0.6), 0 0 0 6px rgba(255,59,95,0); }
1215 | }
1216 | .pn-tl-dot:hover {
1217 |     transform: scale(1.3);
1218 |     box-shadow: 0 0 14px rgba(255,59,95,0.7);
1219 | }
1220 | .pn-tl-dot.active {
1221 |     background: #fff;
1222 |     box-shadow: 0 0 16px rgba(255,59,95,0.8);
1223 |     animation: none;
1224 | }
1225 | /* Glassmorphic info card — fixed position to avoid clipping */
1226 | .pn-tl-card {
1227 |     position: fixed;
1228 |     max-width: 340px;
1229 |     min-width: 280px;
1230 |     background: rgba(0,0,0,0.88);
1231 |     backdrop-filter: blur(20px) saturate(180%);
1232 |     -webkit-backdrop-filter: blur(20px) saturate(180%);
1233 |     border: 1px solid rgba(255,59,95,0.4);
1234 |     border-radius: 12px;
1235 |     padding: 20px;
1236 |     text-align: left;
1237 |     opacity: 0;
1238 |     pointer-events: none;
1239 |     transform: translateY(-8px);
1240 |     transition: opacity 0.25s ease, transform 0.25s ease;
1241 |     z-index: 10000;
1242 |     box-shadow: 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05);
1243 | }
1244 | .pn-tl-card.active {
1245 |     opacity: 1;
1246 |     pointer-events: auto;
1247 |     transform: translateY(0);
1248 | }
1249 | .pn-tl-card-close {
1250 |     position: absolute;
1251 |     top: 10px;
1252 |     right: 12px;
1253 |     background: none;
1254 |     border: none;
1255 |     color: var(--pn-muted);
1256 |     font-size: 16px;
1257 |     cursor: pointer;
1258 |     padding: 2px 6px;
1259 |     line-height: 1;
1260 |     transition: color 0.2s;
1261 | }
1262 | .pn-tl-card-close:hover { color: var(--pn-white); }
1263 | .pn-tl-card-header {
1264 |     font-family: 'JetBrains Mono', monospace;
1265 |     font-size: 11px;
1266 |     font-weight: 700;
1267 |     color: var(--pn-red);
1268 |     text-transform: uppercase;
1269 |     letter-spacing: 1px;
1270 |     margin-bottom: 4px;
1271 |     padding-right: 24px;
1272 | }
1273 | .pn-tl-card-short {
1274 |     font-family: 'Inter', sans-serif;
1275 |     font-size: 13px;
1276 |     color: var(--pn-white);
1277 |     line-height: 1.7;
1278 |     margin-bottom: 10px;
1279 | }
1280 | .pn-tl-card-detail {
1281 |     font-family: 'Inter', sans-serif;
1282 |     font-size: 12px;
1283 |     color: rgba(255,255,255,0.7);
1284 |     line-height: 1.7;
1285 |     margin-bottom: 12px;
1286 | }
1287 | .pn-tl-card-btc {
1288 |     font-family: 'JetBrains Mono', monospace;
1289 |     font-size: 10px;
1290 |     color: var(--pn-red);
1291 |     padding: 8px 10px;
1292 |     background: rgba(255,59,95,0.08);
1293 |     border-left: 2px solid var(--pn-red);
1294 |     border-radius: 0 6px 6px 0;
1295 |     line-height: 1.5;
1296 | }
1297 | .pn-history-coda {
1298 |     font-family: 'JetBrains Mono', monospace;
1299 |     font-size: 11px;
1300 |     color: var(--pn-red);
1301 |     margin-top: 24px;
1302 |     line-height: 1.6;
1303 |     max-width: 800px;
1304 |     font-style: italic;
1305 |     opacity: 0.85;
1306 | }
1307 | 
1308 | /* ── DISCLAIMER ──────────────────────────────────────────────── */
1309 | .pn-disclaimer {
1310 |     padding: 20px 16px;
1311 |     font-family: 'JetBrains Mono', monospace;
1312 |     font-size: 9px;
1313 |     color: var(--pn-muted);
1314 |     line-height: 1.6;
1315 |     max-width: 1800px;
1316 |     margin: 0 auto;
1317 |     border-top: 1px solid var(--pn-border);
1318 | }
1319 | 
1320 | /* ── STATUS CHIP ─────────────────────────────────────────────── */
1321 | .pn-status-chip {
1322 |     font-family: 'JetBrains Mono', monospace;
1323 |     font-size: 8px;
1324 |     font-weight: 700;
1325 |     letter-spacing: 1px;
1326 |     text-transform: uppercase;
1327 |     padding: 2px 8px;
1328 | }
1329 | .pn-status-chip.loading { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
1330 | 
1331 | /* ── CONVICTION SCORE ────────────────────────────────────────── */
1332 | .pn-conviction {
1333 |     display: flex;
1334 |     align-items: center;
1335 |     gap: 6px;
1336 |     margin-top: 8px;
1337 |     padding: 6px 10px;
1338 |     background: rgba(255,255,255,0.02);
1339 |     border: 1px solid var(--pn-border);
1340 | }
1341 | .pn-conviction-label {
1342 |     font-family: 'JetBrains Mono', monospace;
1343 |     font-size: 8px;
1344 |     font-weight: 800;
1345 |     letter-spacing: 1.5px;
1346 |     text-transform: uppercase;
1347 |     color: var(--pn-muted);
1348 | }
1349 | .pn-conviction-score {
1350 |     font-family: 'JetBrains Mono', monospace;
1351 |     font-size: 14px;
1352 |     font-weight: 700;
1353 | }
1354 | .pn-conviction-score.high { color: var(--pn-red); }
1355 | .pn-conviction-score.medium { color: var(--pn-gold); }
1356 | .pn-conviction-score.low { color: var(--pn-muted); }
1357 | .pn-conviction-tag {
1358 |     font-family: 'JetBrains Mono', monospace;
1359 |     font-size: 8px;
1360 |     font-weight: 700;
1361 |     letter-spacing: 1px;
1362 |     padding: 2px 6px;
1363 |     text-transform: uppercase;
1364 | }
1365 | .pn-conviction-tag.high { background: rgba(255,59,95,0.2); color: var(--pn-red); border: 1px solid rgba(255,59,95,0.4); }
1366 | .pn-conviction-tag.medium { background: rgba(248,193,92,0.18); color: var(--pn-gold); border: 1px solid rgba(248,193,92,0.35); }
1367 | .pn-conviction-tag.low { background: transparent; color: var(--pn-muted); border: 1px solid rgba(255,255,255,0.12); }
1368 | .pn-conviction-bar {
1369 |     flex: 1;
1370 |     height: 3px;
1371 |     background: var(--pn-border);
1372 |     overflow: hidden;
1373 | }
1374 | .pn-conviction-bar-fill {
1375 |     height: 100%;
1376 |     transition: width 0.8s ease;
1377 | }
1378 | .pn-conviction-bar-fill.high { background: var(--pn-red); box-shadow: 0 0 6px rgba(255,59,95,0.4); }
1379 | .pn-conviction-bar-fill.medium { background: var(--pn-gold); }
1380 | .pn-conviction-bar-fill.low { background: var(--pn-muted); }
1381 | 
1382 | /* ── WHALE FLOW CLASSIFICATION ───────────────────────────────── */
1383 | .pn-whale-flow {
1384 |     margin-top: 6px;
1385 |     padding: 6px 10px;
1386 |     font-family: 'JetBrains Mono', monospace;
1387 |     font-size: 10px;
1388 |     line-height: 1.4;
1389 |     border-left: 2px solid var(--pn-border);
1390 | }
1391 | .pn-whale-flow.bullish {
1392 |     background: rgba(137,255,184,0.04);
1393 |     border-left-color: #89ffb8;
1394 |     color: #89ffb8;
1395 | }
1396 | .pn-whale-flow.bearish {
1397 |     background: rgba(255,59,95,0.04);
1398 |     border-left-color: var(--pn-red);
1399 |     color: var(--pn-red);
1400 | }
1401 | .pn-whale-flow.neutral {
1402 |     background: rgba(255,255,255,0.02);
1403 |     border-left-color: var(--pn-muted);
1404 |     color: var(--pn-text-secondary);
1405 | }
1406 | .pn-whale-flow-label {
1407 |     font-size: 8px;
1408 |     font-weight: 800;
1409 |     letter-spacing: 1.5px;
1410 |     text-transform: uppercase;
1411 |     margin-bottom: 2px;
1412 |     opacity: 0.7;
1413 | }
1414 | .pn-whale-signal-tag {
1415 |     font-family: 'JetBrains Mono', monospace;
1416 |     font-size: 8px;
1417 |     font-weight: 700;
1418 |     letter-spacing: 1px;
1419 |     padding: 2px 6px;
1420 |     text-transform: uppercase;
1421 |     margin-left: 8px;
1422 | }
1423 | .pn-whale-signal-tag.bullish { background: rgba(137,255,184,0.12); color: #89ffb8; }
1424 | .pn-whale-signal-tag.bearish { background: rgba(255,59,95,0.12); color: var(--pn-red); }
1425 | .pn-whale-signal-tag.neutral { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
1426 | 
1427 | /* ── CORRELATION GAP COLORING ────────────────────────────────── */
1428 | .pn-corr-gap {
1429 |     font-family: 'JetBrains Mono', monospace;
1430 |     font-size: 11px;
1431 |     font-weight: 700;
1432 |     padding: 4px 8px;
1433 |     display: inline-flex;
1434 |     align-items: center;
1435 |     gap: 4px;
1436 |     margin-bottom: 6px;
1437 | }
1438 | .pn-corr-gap.red { background: rgba(255,59,95,0.12); color: var(--pn-red); }
1439 | .pn-corr-gap.orange { background: rgba(248,193,92,0.12); color: var(--pn-gold); }
1440 | .pn-corr-gap.white { background: rgba(255,255,255,0.06); color: var(--pn-white); }
1441 | 
1442 | /* ── POLYMARKET HERO MARKET ──────────────────────────────────── */
1443 | .pn-poly-hero {
1444 |     background: var(--pn-surface);
1445 |     border: 1px solid var(--pn-border);
1446 |     border-left: 3px solid var(--pn-gold);
1447 |     padding: 16px;
1448 |     margin-bottom: 10px;
1449 | }
1450 | .pn-poly-hero .pn-poly-question {
1451 |     font-size: 14px;
1452 |     font-weight: 700;
1453 |     margin-bottom: 10px;
1454 | }
1455 | .pn-poly-hero .pn-poly-pct {
1456 |     font-size: 28px;
1457 | }
1458 | .pn-poly-hero-bar {
1459 |     height: 6px;
1460 |     background: var(--pn-border);
1461 |     overflow: hidden;
1462 |     margin-bottom: 8px;
1463 |     position: relative;
1464 | }
1465 | .pn-poly-hero-bar-fill {
1466 |     height: 100%;
1467 |     background: linear-gradient(90deg, var(--pn-gold), var(--pn-red));
1468 |     transition: width 1.2s ease;
1469 |     position: relative;
1470 | }
1471 | .pn-poly-hero-bar-fill::after {
1472 |     content: '';
1473 |     position: absolute;
1474 |     right: 0;
1475 |     top: -2px;
1476 |     width: 2px;
1477 |     height: 10px;
1478 |     background: var(--pn-white);
1479 |     box-shadow: 0 0 6px rgba(255,255,255,0.6);
1480 |     animation: polyPulse 2s ease-in-out infinite;
1481 | }
1482 | @keyframes polyPulse {
1483 |     0%, 100% { opacity: 1; }
1484 |     50% { opacity: 0.3; }
1485 | }
1486 | .pn-poly-vol-badge {
1487 |     font-family: 'JetBrains Mono', monospace;
1488 |     font-size: 9px;
1489 |     font-weight: 700;
1490 |     color: var(--pn-gold);
1491 |     letter-spacing: 1px;
1492 | }
1493 | </style>
1494 | {% endblock %}
1495 | 
1496 | {% block body_class %}panopticon-body{% endblock %}
1497 | 
1498 | {% block content %}
1499 | 
1500 | <!-- ═══ STICKY TOP BAR ═══ -->
1501 | <div class="pn-topbar">
1502 |     <div class="pn-topbar-left">
1503 |         <span class="pn-topbar-logo">PANOPTICON</span>
1504 |         <div class="pn-topbar-status">
1505 |             <div class="pn-topbar-dot"></div>
1506 |             <span>SCANNING</span>
1507 |         </div>
1508 |     </div>
1509 |     <div class="pn-topbar-right">
1510 |         <span class="pn-topbar-btc" id="pnBtcPrice">
1511 |             {% if data.btc_price %}BTC ${{ "{:,.0f}".format(data.btc_price) }}{% else %}BTC --{% endif %}
1512 |         </span>
1513 |         <span class="pn-topbar-clock" id="pnClock">--:--:-- UTC</span>
1514 |         <a href="/" class="pn-topbar-back">&larr; PROTOCOL PULSE</a>
1515 |     </div>
1516 | </div>
1517 | 
1518 | <!-- ═══ HERO — RADAR SWEEP ═══ -->
1519 | <section class="pn-hero">
1520 |     <div class="pn-hero-radar">
1521 |         <div class="pn-radar-rings">
1522 |             <div class="pn-radar-ring"></div>
1523 |             <div class="pn-radar-ring"></div>
1524 |             <div class="pn-radar-ring"></div>
1525 |             <div class="pn-radar-ring"></div>
1526 |         </div>
1527 |         <div class="pn-radar-cross"></div>
1528 |         <div class="pn-radar-sweep"></div>
1529 |         <div class="pn-scanlines"></div>
1530 |     </div>
1531 |     <div class="pn-hero-content">
1532 |         <h1 class="pn-hero-title">PANOPTICON</h1>
1533 |         <p class="pn-hero-tagline">They watch us. Now we watch them.</p>
1534 | 
1535 |         <div class="pn-hero-stats">
1536 |             <div class="pn-hero-stat">
1537 |                 <div class="pn-hero-stat-val" id="pnStatDisc">{{ data.disclosures|length }}</div>
1538 |                 <div class="pn-hero-stat-label">Disclosures</div>
1539 |             </div>
1540 |             <div class="pn-hero-stat-sep"></div>
1541 |             <div class="pn-hero-stat">
1542 |                 <div class="pn-hero-stat-val" id="pnStatWhales">{{ data.whales|length }}</div>
1543 |                 <div class="pn-hero-stat-label">Whale Moves</div>
1544 |             </div>
1545 |             <div class="pn-hero-stat-sep"></div>
1546 |             <div class="pn-hero-stat">
1547 |                 <div class="pn-hero-stat-val" id="pnStatFlags">{{ data.flagged|length }}</div>
1548 |                 <div class="pn-hero-stat-label">Patterns</div>
1549 |             </div>
1550 |             <div class="pn-hero-stat-sep"></div>
1551 |             <div class="pn-hero-stat">
1552 |                 <div class="pn-hero-stat-val" id="pnStatEvents">{{ data.events_today }}</div>
1553 |                 <div class="pn-hero-stat-label">Events Today</div>
1554 |             </div>
1555 |         </div>
1556 |     </div>
1557 | </section>
1558 | 
1559 | <!-- ═══ LIVE TICKER ═══ -->
1560 | <div class="pn-ticker">
1561 |     <span class="pn-ticker-tag">LIVE FEED</span>
1562 |     <div class="pn-ticker-scroll">
1563 |         <span class="pn-ticker-text">
1564 |             {% if data.whales %}{% for w in data.whales[:3] %}{{ w.entity }}: {{ w.amount_btc }} BTC {{ w.tx_type }} &nbsp;&bull;&nbsp; {% endfor %}{% endif %}{% for d in data.disclosures[:3] %}{{ d.entity }} &mdash; {{ d.asset }} ({{ d.trade_type }}) &nbsp;&bull;&nbsp; {% endfor %}PANOPTICON monitoring {{ data.events_today }} events &nbsp;&bull;&nbsp; All data from public sources &nbsp;&bull;&nbsp; {% if data.whales %}{% for w in data.whales[:3] %}{{ w.entity }}: {{ w.amount_btc }} BTC {{ w.tx_type }} &nbsp;&bull;&nbsp; {% endfor %}{% endif %}{% for d in data.disclosures[:3] %}{{ d.entity }} &mdash; {{ d.asset }} ({{ d.trade_type }}) &nbsp;&bull;&nbsp; {% endfor %}PANOPTICON monitoring {{ data.events_today }} events &nbsp;&bull;&nbsp;
1565 |         </span>
1566 |     </div>
1567 | </div>
1568 | 
1569 | {% if demo_mode %}
1570 | <!-- ═══ CLASSIFIED ALERT BAR ═══ -->
1571 | <div style="display:flex;align-items:center;padding:8px 16px;background:rgba(255,59,95,0.04);border-bottom:1px solid var(--pn-border);gap:12px;">
1572 |     <div style="display:flex;align-items:center;gap:6px;">
1573 |         <div class="pn-topbar-dot"></div>
1574 |         <span style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;color:var(--pn-red);letter-spacing:1px;">CLASSIFIED — COMMANDER ACCESS REQUIRED</span>
1575 |     </div>
1576 |     <a href="/join" style="margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--pn-muted);text-decoration:none;letter-spacing:1px;">Upgrade &rarr;</a>
1577 | </div>
1578 | {% endif %}
1579 | 
1580 | <!-- ═══════════════════════════════════════════════════════════════════════
1581 |      SOVEREIGN SIGNAL v2 — MISSION CONTROL INTELLIGENCE PANEL
1582 |      Replaces the orb/radar. Live data from APIs. Every element is analytical.
1583 |      ════════════════════════════════════════════════════════════════════════ -->
1584 | <div id="ss2-root">
1585 | 
1586 | <!-- ── HEADER ── -->
1587 | <div id="ss2-header">
1588 |   <div>
1589 |     <div class="ss2-overline">PROTOCOL PULSE · INTELLIGENCE SYNTHESIS · LIVE</div>
1590 |     <div class="ss2-title">SOVEREIGN SIGNAL</div>
1591 |   </div>
1592 |   <div id="ss2-composite-block">
1593 |     <div class="ss2-overline" style="text-align:right;">CONVERGENCE INDEX</div>
1594 |     <div id="ss2-score-display">
1595 |       <span id="ss2-score-num">—</span><span class="ss2-score-denom">/100</span>
1596 |     </div>
1597 |     <div id="ss2-verdict">▋ LOADING STREAMS...</div>
1598 |   </div>
1599 | </div>
1600 | 
1601 | <!-- ── SIX ARC GAUGES ── -->
1602 | <div id="ss2-gauges-row">
1603 |   <div class="ss2-gauge-cell" id="gc-congress"   data-stream="congress">
1604 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1605 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1606 |       <path class="ss2-arc-fill" id="ga-congress" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1607 |       <line class="ss2-needle" id="gn-congress" x1="60" y1="65" x2="60" y2="20"/>
1608 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1609 |       <text class="ss2-gauge-score" id="gs-congress" x="60" y="58">—</text>
1610 |     </svg>
1611 |     <div class="ss2-gauge-label">CONGRESS</div>
1612 |     <div class="ss2-gauge-sub" id="gd-congress">IHX · INSIDER TRADES</div>
1613 |     <div class="ss2-gauge-arrow" id="garr-congress">—</div>
1614 |   </div>
1615 |   <div class="ss2-gauge-cell" id="gc-pac" data-stream="pac">
1616 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1617 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1618 |       <path class="ss2-arc-fill" id="ga-pac" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1619 |       <line class="ss2-needle" id="gn-pac" x1="60" y1="65" x2="60" y2="20"/>
1620 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1621 |       <text class="ss2-gauge-score" id="gs-pac" x="60" y="58">—</text>
1622 |     </svg>
1623 |     <div class="ss2-gauge-label">PAC CAPITAL</div>
1624 |     <div class="ss2-gauge-sub" id="gd-pac">FAIRSHAKE · POLITICAL SPEND</div>
1625 |     <div class="ss2-gauge-arrow" id="garr-pac">—</div>
1626 |   </div>
1627 |   <div class="ss2-gauge-cell" id="gc-legislation" data-stream="legislation">
1628 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1629 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1630 |       <path class="ss2-arc-fill" id="ga-legislation" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1631 |       <line class="ss2-needle" id="gn-legislation" x1="60" y1="65" x2="60" y2="20"/>
1632 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1633 |       <text class="ss2-gauge-score" id="gs-legislation" x="60" y="58">—</text>
1634 |     </svg>
1635 |     <div class="ss2-gauge-label">LEGISLATION</div>
1636 |     <div class="ss2-gauge-sub" id="gd-legislation">BILL MOMENTUM · VOTES</div>
1637 |     <div class="ss2-gauge-arrow" id="garr-legislation">—</div>
1638 |   </div>
1639 |   <div class="ss2-gauge-cell" id="gc-onchain" data-stream="onchain">
1640 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1641 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1642 |       <path class="ss2-arc-fill" id="ga-onchain" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1643 |       <line class="ss2-needle" id="gn-onchain" x1="60" y1="65" x2="60" y2="20"/>
1644 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1645 |       <text class="ss2-gauge-score" id="gs-onchain" x="60" y="58">—</text>
1646 |     </svg>
1647 |     <div class="ss2-gauge-label">ON-CHAIN</div>
1648 |     <div class="ss2-gauge-sub" id="gd-onchain">HASHRATE · ACCUMULATION</div>
1649 |     <div class="ss2-gauge-arrow" id="garr-onchain">—</div>
1650 |   </div>
1651 |   <div class="ss2-gauge-cell" id="gc-institutional" data-stream="institutional">
1652 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1653 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1654 |       <path class="ss2-arc-fill" id="ga-institutional" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1655 |       <line class="ss2-needle" id="gn-institutional" x1="60" y1="65" x2="60" y2="20"/>
1656 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1657 |       <text class="ss2-gauge-score" id="gs-institutional" x="60" y="58">—</text>
1658 |     </svg>
1659 |     <div class="ss2-gauge-label">INSTITUTIONAL</div>
1660 |     <div class="ss2-gauge-sub" id="gd-institutional">13F · FORM D · EDGAR</div>
1661 |     <div class="ss2-gauge-arrow" id="garr-institutional">—</div>
1662 |   </div>
1663 |   <div class="ss2-gauge-cell" id="gc-geo" data-stream="geo">
1664 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1665 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1666 |       <path class="ss2-arc-fill" id="ga-geo" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1667 |       <line class="ss2-needle" id="gn-geo" x1="60" y1="65" x2="60" y2="20"/>
1668 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1669 |       <text class="ss2-gauge-score" id="gs-geo" x="60" y="58">—</text>
1670 |     </svg>
1671 |     <div class="ss2-gauge-label">GEOPOLITICAL</div>
1672 |     <div class="ss2-gauge-sub" id="gd-geo">MACRO · NATION-STATE</div>
1673 |     <div class="ss2-gauge-arrow" id="garr-geo">—</div>
1674 |   </div>
1675 | </div>
1676 | 
1677 | <!-- ── HOVER DATA CARD ── -->
1678 | <div id="ss2-datacard">
1679 |   <div id="ss2-dc-header">
1680 |     <div>
1681 |       <div id="ss2-dc-stream" class="ss2-overline"></div>
1682 |       <div id="ss2-dc-title"></div>
1683 |     </div>
1684 |     <div id="ss2-dc-score-wrap">
1685 |       <div id="ss2-dc-score"></div>
1686 |       <div id="ss2-dc-verdict"></div>
1687 |     </div>
1688 |   </div>
1689 |   <div id="ss2-dc-rows"></div>
1690 |   <div id="ss2-dc-insight"></div>
1691 | </div>
1692 | 
1693 | <!-- ── MIDDLE ROW: CORRELATION MAP + SIGNAL BOARD ── -->
1694 | <div id="ss2-middle">
1695 | 
1696 |   <!-- Correlation network graph (D3 force-directed) -->
1697 |   <div id="ss2-map-wrap">
1698 |     <div class="ss2-overline" style="padding:clamp(14px,1.2vw,18px) clamp(16px,1.4vw,22px) 8px;">SIGNAL CORRELATION MAP  <span style="color:rgba(255,255,255,0.45);font-weight:400;">{% if is_commander %}· HOVER FOR DRILL-DOWN{% else %}· COMMANDER INTELLIGENCE{% endif %}</span></div>
1699 |     <div class="ss2-map-graph-holder" style="position:relative;flex:1;">
1700 |       <div id="ss2-map-graph" {% if not is_commander %}style="filter:blur(8px);opacity:0.55;pointer-events:none;"{% endif %}></div>
1701 |       <div id="ss2-map-tooltip"></div>
1702 |       {% if not is_commander %}
1703 |       <div class="ss2-map-lock">
1704 |         <div class="ss2-map-lock-box">
1705 |           <div class="ss2-map-lock-badge">COMMANDER</div>
1706 |           <div class="ss2-map-lock-title">SIGNAL CORRELATION MAP</div>
1707 |           <div class="ss2-map-lock-sub">Unlock to see live correlation between all 6 sovereign indices — congress, PAC capital, legislation, on-chain, institutional, and geopolitical.</div>
1708 |           <a class="ss2-map-lock-cta" href="/join">UNLOCK COMMANDER →</a>
1709 |         </div>
1710 |       </div>
1711 |       {% endif %}
1712 |     </div>
1713 |     <div id="ss2-map-legend">
1714 |       <span class="ss2-leg-item"><span class="ss2-leg-line ss2-leg-high"></span> HIGH CORR</span>
1715 |       <span class="ss2-leg-item"><span class="ss2-leg-line ss2-leg-med"></span> MEDIUM</span>
1716 |       <span class="ss2-leg-sep">|</span>
1717 |       <span class="ss2-leg-item">SIZE = SCORE</span>
1718 |       <span class="ss2-leg-sep">|</span>
1719 |       <span class="ss2-leg-item"><span class="ss2-leg-dot" style="background:#10B981;"></span> BULLISH</span>
1720 |       <span class="ss2-leg-item"><span class="ss2-leg-dot" style="background:#F59E0B;"></span> NEUTRAL</span>
1721 |       <span class="ss2-leg-item"><span class="ss2-leg-dot" style="background:#CC0000;"></span> BEARISH</span>
1722 |     </div>
1723 |   </div>
1724 | 
1725 |   <!-- Signal Board -->
1726 |   <div id="ss2-board-wrap">
1727 |     <div class="ss2-overline" style="padding:12px 16px 8px;display:flex;justify-content:space-between;">
1728 |       <span>LIVE SIGNAL BOARD</span>
1729 |       <span id="ss2-board-ts" style="color:rgba(255,255,255,0.4);font-weight:400;font-size:clamp(8px,0.6vw,10px);letter-spacing:.1em;"></span>
1730 |     </div>
1731 |     <div id="ss2-signal-board"></div>
1732 |   </div>
1733 | 
1734 | </div>
1735 | 
1736 | <!-- ── BOTTOM: DATA BARS WATERFALL ── -->
1737 | <div id="ss2-waterfall">
1738 |   <div class="ss2-overline" style="padding:10px 16px 8px;">CONVERGENCE WATERFALL  <span style="color:rgba(255,255,255,0.45);font-weight:400;">· CONTRIBUTION TO 74/100</span></div>
1739 |   <div id="ss2-waterfall-bars"></div>
1740 |   <div style="padding:6px 16px 10px;font-size:7px;color:rgba(255,255,255,0.12);font-family:'JetBrains Mono',monospace;">
1741 |     SOURCE: OPENFEC · SEC EDGAR · LEGISCAN CC BY 4.0 · MEMPOOL.SPACE · POLYMARKET &nbsp;·&nbsp; NOT FINANCIAL ADVICE
1742 |   </div>
1743 | </div>
1744 | 
1745 | </div><!-- #ss2-root -->
1746 | 
1747 | <!-- ── STYLES ── -->
1748 | <style>
1749 | #ss2-root {
1750 |   font-family: 'JetBrains Mono', 'Courier New', monospace;
1751 |   background: #030303;
1752 |   border-top: 1px solid rgba(204,0,0,0.25);
1753 |   border-bottom: 1px solid rgba(204,0,0,0.18);
1754 |   color: #fff;
1755 |   position: relative;
1756 |   overflow: hidden;
1757 |   max-width: clamp(1280px, 94vw, 2400px);
1758 |   margin: clamp(16px, 1.5vw, 28px) auto;
1759 |   border-left: 1px solid rgba(204,0,0,0.12);
1760 |   border-right: 1px solid rgba(204,0,0,0.12);
1761 |   border-radius: 6px;
1762 | }
1763 | #ss2-root::before {
1764 |   content: '';
1765 |   position: absolute;
1766 |   inset: 0;
1767 |   background:
1768 |     repeating-linear-gradient(0deg, transparent, transparent 47px, rgba(204,0,0,0.025) 47px, rgba(204,0,0,0.025) 48px),
1769 |     repeating-linear-gradient(90deg, transparent, transparent 47px, rgba(204,0,0,0.025) 47px, rgba(204,0,0,0.025) 48px);
1770 |   pointer-events: none;
1771 |   z-index: 0;
1772 | }
1773 | #ss2-root > * { position: relative; z-index: 1; }
1774 | 
1775 | .ss2-overline {
1776 |   font-size: clamp(10px, 0.7vw, 12px);
1777 |   letter-spacing: .22em;
1778 |   color: rgba(204,0,0,.7);
1779 |   font-weight: 700;
1780 |   text-transform: uppercase;
1781 | }
1782 | .ss2-title {
1783 |   font-size: clamp(22px, 1.8vw, 30px);
1784 |   font-weight: 900;
1785 |   letter-spacing: .12em;
1786 |   color: #fff;
1787 |   line-height: 1;
1788 |   margin-top: 6px;
1789 | }
1790 | 
1791 | /* Header */
1792 | #ss2-header {
1793 |   display: flex;
1794 |   justify-content: space-between;
1795 |   align-items: flex-start;
1796 |   padding: clamp(18px, 1.5vw, 26px) clamp(20px, 1.8vw, 32px) clamp(14px, 1.2vw, 20px);
1797 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1798 |   gap: clamp(16px, 1.5vw, 24px);
1799 |   flex-wrap: wrap;
1800 | }
1801 | #ss2-composite-block { text-align: right; }
1802 | #ss2-score-display {
1803 |   display: flex;
1804 |   align-items: baseline;
1805 |   gap: 3px;
1806 |   justify-content: flex-end;
1807 |   margin-top: 4px;
1808 | }
1809 | #ss2-score-num {
1810 |   font-size: clamp(52px, 4.5vw, 72px);
1811 |   font-weight: 900;
1812 |   line-height: 1;
1813 |   color: #CC0000;
1814 |   text-shadow: 0 0 30px rgba(204,0,0,.55);
1815 |   transition: color .5s;
1816 | }
1817 | .ss2-score-denom { font-size: clamp(16px, 1.2vw, 20px); color: rgba(255,255,255,.2); }
1818 | #ss2-verdict {
1819 |   font-size: clamp(11px, 0.75vw, 13px);
1820 |   letter-spacing: .1em;
1821 |   margin-top: 5px;
1822 |   transition: color .5s;
1823 | }
1824 | 
1825 | /* Gauges row */
1826 | #ss2-gauges-row {
1827 |   display: grid;
1828 |   grid-template-columns: repeat(6, 1fr);
1829 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1830 | }
1831 | .ss2-gauge-cell {
1832 |   padding: clamp(16px, 1.4vw, 24px) clamp(12px, 1.5vw, 22px) clamp(12px, 1.1vw, 18px);
1833 |   border-right: 1px solid rgba(255,255,255,0.04);
1834 |   cursor: pointer;
1835 |   transition: background .15s;
1836 |   position: relative;
1837 | }
1838 | .ss2-gauge-cell:last-child { border-right: none; }
1839 | .ss2-gauge-cell:hover, .ss2-gauge-cell.active { background: rgba(204,0,0,.05); }
1840 | .ss2-gauge-cell.active { background: rgba(204,0,0,.08); }
1841 | 
1842 | .ss2-gauge-svg {
1843 |   width: 100%;
1844 |   height: auto;
1845 |   display: block;
1846 |   margin-bottom: 6px;
1847 |   overflow: visible;
1848 | }
1849 | .ss2-arc-bg {
1850 |   fill: none;
1851 |   stroke: rgba(255,255,255,.06);
1852 |   stroke-width: 5;
1853 |   stroke-linecap: round;
1854 | }
1855 | .ss2-arc-fill {
1856 |   fill: none;
1857 |   stroke-width: 5;
1858 |   stroke-linecap: round;
1859 |   stroke: #f8c15c;
1860 |   transition: stroke-dasharray 1.2s cubic-bezier(.22,.61,.36,1);
1861 | }
1862 | /* Skeleton pulse on gauges before data loads */
1863 | .ss2-arc-fill.skeleton {
1864 |   opacity: 0.3;
1865 |   animation: skeletonPulse 1.5s ease-in-out infinite;
1866 | }
1867 | @keyframes skeletonPulse {
1868 |   0%, 100% { opacity: 0.15; }
1869 |   50% { opacity: 0.35; }
1870 | }
1871 | .ss2-needle {
1872 |   stroke: rgba(255,255,255,.7);
1873 |   stroke-width: 1.5;
1874 |   stroke-linecap: round;
1875 |   transform-origin: 60px 65px;
1876 |   transition: transform 1.4s cubic-bezier(.34,1.56,.64,1);
1877 | }
1878 | .ss2-needle-hub {
1879 |   fill: rgba(255,255,255,.9);
1880 | }
1881 | .ss2-gauge-score {
1882 |   font-family: 'JetBrains Mono', monospace;
1883 |   font-size: 15px;
1884 |   font-weight: 900;
1885 |   text-anchor: middle;
1886 |   fill: #fff;
1887 | }
1888 | .ss2-gauge-label {
1889 |   font-size: clamp(11px, 0.8vw, 14px);
1890 |   font-weight: 700;
1891 |   letter-spacing: .12em;
1892 |   text-align: center;
1893 |   color: rgba(255,255,255,.85);
1894 | }
1895 | .ss2-gauge-sub {
1896 |   font-size: clamp(10px, 0.65vw, 12px);
1897 |   color: rgba(255,255,255,.45);
1898 |   text-align: center;
1899 |   margin-top: 4px;
1900 |   letter-spacing: .04em;
1901 |   line-height: 1.45;
1902 | }
1903 | .ss2-gauge-arrow {
1904 |   font-size: clamp(11px, 0.75vw, 13px);
1905 |   text-align: center;
1906 |   margin-top: 5px;
1907 |   transition: color .5s;
1908 |   letter-spacing: .06em;
1909 | }
1910 | 
1911 | /* Data Card */
1912 | #ss2-datacard {
1913 |   display: none;
1914 |   background: rgba(5,5,5,.97);
1915 |   border: 1px solid rgba(204,0,0,.45);
1916 |   border-radius: 4px;
1917 |   padding: 18px 20px;
1918 |   position: absolute;
1919 |   top: 100px;
1920 |   left: 50%;
1921 |   transform: translateX(-50%);
1922 |   z-index: 50;
1923 |   box-shadow: 0 16px 48px rgba(0,0,0,.85), 0 0 24px rgba(204,0,0,.12);
1924 |   width: 580px;
1925 |   max-width: calc(100% - 40px);
1926 |   animation: ss2FadeIn .15s ease;
1927 | }
1928 | #ss2-datacard.visible { display: block; }
1929 | @keyframes ss2FadeIn { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }
1930 | #ss2-dc-header {
1931 |   display: flex;
1932 |   justify-content: space-between;
1933 |   align-items: flex-start;
1934 |   margin-bottom: 10px;
1935 |   padding-bottom: 10px;
1936 |   border-bottom: 1px solid rgba(255,255,255,.06);
1937 | }
1938 | #ss2-dc-title {
1939 |   font-size: 13px;
1940 |   font-weight: 700;
1941 |   color: #fff;
1942 |   margin-top: 4px;
1943 | }
1944 | #ss2-dc-score { font-size: 32px; font-weight: 900; line-height: 1; }
1945 | #ss2-dc-verdict { font-size: 8px; letter-spacing: .1em; margin-top: 2px; }
1946 | #ss2-dc-rows {
1947 |   display: grid;
1948 |   grid-template-columns: 1fr 1fr;
1949 |   gap: 5px 20px;
1950 |   margin-bottom: 10px;
1951 | }
1952 | .ss2-dc-row {
1953 |   display: flex;
1954 |   justify-content: space-between;
1955 |   align-items: baseline;
1956 |   padding: 5px 0;
1957 |   border-bottom: 1px solid rgba(255,255,255,.04);
1958 |   font-size: clamp(11px, 0.75vw, 13px);
1959 | }
1960 | .ss2-dc-key { color: rgba(255,255,255,.35); }
1961 | .ss2-dc-val { color: rgba(255,255,255,.9); font-weight: 700; }
1962 | .ss2-dc-val.hot { color: #CC0000; }
1963 | .ss2-dc-val.gold { color: #f8c15c; }
1964 | .ss2-dc-val.green { color: #22c55e; }
1965 | #ss2-dc-insight {
1966 |   font-size: clamp(11px, 0.8vw, 13px);
1967 |   color: rgba(255,255,255,.52);
1968 |   line-height: 1.65;
1969 |   border-top: 1px solid rgba(255,255,255,.04);
1970 |   padding-top: 10px;
1971 |   font-style: italic;
1972 | }
1973 | 
1974 | /* Middle row */
1975 | #ss2-middle {
1976 |   display: grid;
1977 |   grid-template-columns: 1fr clamp(380px, 24vw, 520px);
1978 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1979 |   min-height: clamp(340px, 32vh, 440px);
1980 |   position: relative;
1981 | }
1982 | #ss2-map-wrap {
1983 |   border-right: 1px solid rgba(255,255,255,0.04);
1984 |   display: flex;
1985 |   flex-direction: column;
1986 |   position: relative;
1987 | }
1988 | #ss2-map-graph {
1989 |   width: 100%;
1990 |   flex: 1;
1991 |   min-height: clamp(260px, 28vh, 400px);
1992 | }
1993 | #ss2-map-graph svg { display: block; width: 100%; height: 100%; }
1994 | #ss2-map-legend {
1995 |   display: flex;
1996 |   align-items: center;
1997 |   gap: clamp(8px, 0.7vw, 14px);
1998 |   padding: 6px 16px 10px;
1999 |   font-family: 'JetBrains Mono', monospace;
2000 |   font-size: clamp(8px, 0.6vw, 10px);
2001 |   color: rgba(255,255,255,0.45);
2002 |   letter-spacing: .1em;
2003 |   flex-wrap: wrap;
2004 | }
2005 | .ss2-leg-item { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
2006 | .ss2-leg-line { display: inline-block; width: 16px; height: 0; border-top: 2px solid; }
2007 | .ss2-leg-line.ss2-leg-high { border-top-width: 3px; border-color: rgba(255,255,255,0.5); }
2008 | .ss2-leg-line.ss2-leg-med  { border-top-width: 1.5px; border-color: rgba(255,255,255,0.3); border-style: dashed; }
2009 | .ss2-leg-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; }
2010 | .ss2-leg-sep { color: rgba(255,255,255,0.15); }
2011 | #ss2-map-tooltip {
2012 |   position: absolute;
2013 |   pointer-events: none;
2014 |   opacity: 0;
2015 |   background: rgba(5,5,5,.95);
2016 |   border: 1px solid rgba(204,0,0,.4);
2017 |   border-radius: 3px;
2018 |   padding: 8px 10px;
2019 |   font-size: clamp(10px, 0.7vw, 12px);
2020 |   color: rgba(255,255,255,.8);
2021 |   transition: opacity .12s;
2022 |   z-index: 30;
2023 |   min-width: 140px;
2024 |   line-height: 1.6;
2025 | }
2026 | 
2027 | /* Commander lock overlay (correlation map only — free-tier teaser) */
2028 | .ss2-map-lock {
2029 |   position: absolute;
2030 |   inset: 0;
2031 |   display: flex;
2032 |   align-items: center;
2033 |   justify-content: center;
2034 |   z-index: 20;
2035 |   background: linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.78) 100%);
2036 |   padding: clamp(16px, 2vw, 32px);
2037 | }
2038 | .ss2-map-lock-box {
2039 |   background: rgba(8,8,10,0.92);
2040 |   border: 1px solid rgba(204,0,0,0.55);
2041 |   border-radius: 6px;
2042 |   padding: clamp(20px, 2vw, 32px) clamp(24px, 2.2vw, 36px);
2043 |   max-width: 460px;
2044 |   text-align: center;
2045 |   box-shadow: 0 20px 60px rgba(0,0,0,0.7), 0 0 30px rgba(204,0,0,0.18);
2046 |   backdrop-filter: blur(4px);
2047 | }
2048 | .ss2-map-lock-badge {
2049 |   display: inline-block;
2050 |   font-family: 'JetBrains Mono', monospace;
2051 |   font-size: clamp(10px, 0.75vw, 12px);
2052 |   font-weight: 800;
2053 |   letter-spacing: clamp(2px, 0.2vw, 3.5px);
2054 |   color: #CC0000;
2055 |   padding: 4px 12px;
2056 |   border: 1px solid rgba(204,0,0,0.5);
2057 |   border-radius: 2px;
2058 |   margin-bottom: 14px;
2059 |   background: rgba(204,0,0,0.08);
2060 | }
2061 | .ss2-map-lock-title {
2062 |   font-family: 'JetBrains Mono', monospace;
2063 |   font-size: clamp(16px, 1.3vw, 22px);
2064 |   font-weight: 800;
2065 |   color: #fff;
2066 |   letter-spacing: .08em;
2067 |   line-height: 1.2;
2068 |   margin-bottom: 10px;
2069 | }
2070 | .ss2-map-lock-sub {
2071 |   font-family: 'Inter', -apple-system, sans-serif;
2072 |   font-size: clamp(12px, 0.85vw, 14px);
2073 |   color: rgba(255,255,255,0.65);
2074 |   line-height: 1.55;
2075 |   margin-bottom: 18px;
2076 | }
2077 | .ss2-map-lock-cta {
2078 |   display: inline-block;
2079 |   font-family: 'JetBrains Mono', monospace;
2080 |   font-size: clamp(11px, 0.8vw, 13px);
2081 |   font-weight: 800;
2082 |   letter-spacing: clamp(1.5px, 0.15vw, 2.5px);
2083 |   color: #fff;
2084 |   background: #CC0000;
2085 |   padding: 11px 22px;
2086 |   border-radius: 3px;
2087 |   text-decoration: none;
2088 |   border: 1px solid rgba(255,59,95,0.55);
2089 |   transition: background .2s, transform .15s, box-shadow .2s;
2090 |   text-transform: uppercase;
2091 |   box-shadow: 0 6px 18px rgba(204,0,0,0.28);
2092 | }
2093 | .ss2-map-lock-cta:hover {
2094 |   background: #ff3b5f;
2095 |   transform: translateY(-1px);
2096 |   box-shadow: 0 10px 24px rgba(204,0,0,0.42);
2097 | }
2098 | 
2099 | /* Signal Board */
2100 | #ss2-board-wrap { overflow: hidden; display: flex; flex-direction: column; }
2101 | #ss2-signal-board {
2102 |   padding: 4px 0;
2103 |   overflow-y: auto;
2104 |   flex: 1;
2105 |   max-height: clamp(310px, 32vh, 440px);
2106 | }
2107 | #ss2-signal-board::-webkit-scrollbar { width: 3px; }
2108 | #ss2-signal-board::-webkit-scrollbar-track { background: transparent; }
2109 | #ss2-signal-board::-webkit-scrollbar-thumb { background: rgba(204,0,0,0.3); border-radius: 2px; }
2110 | .ss2-signal-item {
2111 |   display: flex;
2112 |   align-items: flex-start;
2113 |   gap: clamp(10px, 0.8vw, 14px);
2114 |   padding: clamp(10px, 0.9vw, 14px) clamp(16px, 1.2vw, 20px);
2115 |   border-bottom: 1px solid rgba(255,255,255,.04);
2116 |   cursor: default;
2117 |   transition: background .12s;
2118 | }
2119 | .ss2-signal-item:hover { background: rgba(255,255,255,.025); }
2120 | .ss2-si-dot {
2121 |   width: 8px;
2122 |   height: 8px;
2123 |   border-radius: 50%;
2124 |   flex-shrink: 0;
2125 |   margin-top: 5px;
2126 | }
2127 | .ss2-si-body { flex: 1; min-width: 0; }
2128 | .ss2-si-label {
2129 |   font-size: clamp(10px, 0.7vw, 12px);
2130 |   letter-spacing: .14em;
2131 |   margin-bottom: 4px;
2132 |   font-weight: 700;
2133 | }
2134 | .ss2-si-text {
2135 |   font-size: clamp(11px, 0.8vw, 13px);
2136 |   color: rgba(255,255,255,.75);
2137 |   line-height: 1.55;
2138 |   white-space: normal;
2139 | }
2140 | .ss2-si-val {
2141 |   font-size: clamp(12px, 0.85vw, 14px);
2142 |   font-weight: 700;
2143 |   flex-shrink: 0;
2144 |   text-align: right;
2145 |   min-width: 54px;
2146 | }
2147 | 
2148 | /* Waterfall */
2149 | #ss2-waterfall { border-top: 1px solid rgba(255,255,255,0.04); }
2150 | #ss2-waterfall-bars {
2151 |   display: grid;
2152 |   grid-template-columns: repeat(6, 1fr);
2153 |   gap: 1px;
2154 |   padding: clamp(4px, 0.5vw, 8px) clamp(20px, 1.8vw, 32px) clamp(16px, 1.4vw, 22px);
2155 | }
2156 | .ss2-wf-col {
2157 |   padding: clamp(6px, 0.6vw, 10px) clamp(10px, 0.9vw, 14px);
2158 |   cursor: pointer;
2159 |   transition: background .12s;
2160 |   border-right: 1px solid rgba(255,255,255,0.03);
2161 | }
2162 | .ss2-wf-col:last-child { border-right: none; }
2163 | .ss2-wf-col:hover { background: rgba(255,255,255,.025); }
2164 | .ss2-wf-bar-wrap {
2165 |   height: clamp(54px, 4.5vh, 78px);
2166 |   display: flex;
2167 |   align-items: flex-end;
2168 |   justify-content: center;
2169 |   margin-bottom: 8px;
2170 |   gap: 2px;
2171 | }
2172 | .ss2-wf-bar {
2173 |   width: 50%;
2174 |   border-radius: 2px 2px 0 0;
2175 |   min-height: 2px;
2176 |   transition: height 1.5s cubic-bezier(.22,.61,.36,1);
2177 | }
2178 | .ss2-wf-score {
2179 |   font-size: clamp(13px, 0.95vw, 16px);
2180 |   font-weight: 900;
2181 |   text-align: center;
2182 |   margin-bottom: 4px;
2183 | }
2184 | .ss2-wf-label {
2185 |   font-size: clamp(10px, 0.7vw, 12px);
2186 |   color: rgba(255,255,255,.55);
2187 |   text-align: center;
2188 |   letter-spacing: .08em;
2189 |   line-height: 1.45;
2190 |   font-weight: 600;
2191 | }
2192 | .ss2-wf-contrib {
2193 |   font-size: clamp(9px, 0.6vw, 11px);
2194 |   color: rgba(255,255,255,.32);
2195 |   text-align: center;
2196 |   margin-top: 4px;
2197 |   letter-spacing: .04em;
2198 | }
2199 | 
2200 | @media(max-width:1100px) {
2201 |   #ss2-middle { grid-template-columns: 1fr 340px; }
2202 | }
2203 | @media(max-width:900px) {
2204 |   #ss2-middle { grid-template-columns: 1fr; min-height: auto; }
2205 |   #ss2-map-graph { min-height: 220px; }
2206 |   #ss2-board-wrap { border-top: 1px solid rgba(255,255,255,0.04); }
2207 | }
2208 | @media(max-width:768px) {
2209 |   #ss2-gauges-row { grid-template-columns: repeat(3,1fr); }
2210 |   #ss2-waterfall-bars { grid-template-columns: repeat(3,1fr); }
2211 | }
2212 | @media(max-width:480px) {
2213 |   #ss2-gauges-row { grid-template-columns: repeat(2,1fr); }
2214 |   #ss2-waterfall-bars { grid-template-columns: repeat(2,1fr); }
2215 |   #ss2-score-num { font-size: 40px; }
2216 | }
2217 | </style>
2218 | 
2219 | <!-- ── JAVASCRIPT ── -->
2220 | <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js" integrity="sha512-M7nHCiNUOwFt6Us3r8alutZLm9qMt4s9951uo8jqO4UwJ1hziseL6O3ndFyigx6+LREfZqnhHxYjKRJ8ZQ69DQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
2221 | <script>
2222 | (function() {
2223 | 'use strict';
2224 | 
2225 | // ─── Stream definitions ─────────────────────────────────────────────────────
2226 | var STREAMS = {
2227 |   congress:    { label:'CONGRESS',      sub:'IHX · INSIDER TRADES',   color:'#f8c15c', apiKey:'ihx' },
2228 |   pac:         { label:'PAC CAPITAL',   sub:'FAIRSHAKE · SPEND',       color:'#CC0000', apiKey:'pac' },
2229 |   legislation: { label:'LEGISLATION',   sub:'BILL MOMENTUM',           color:'#22c55e', apiKey:'leg' },
2230 |   onchain:     { label:'ON-CHAIN',      sub:'HASHRATE · ACCUM',        color:'#f8c15c', apiKey:'orb' },
2231 |   institutional:{ label:'INSTITUTIONAL',sub:'13F · FORM D',            color:'#22c55e', apiKey:'inst' },
2232 |   geo:         { label:'GEOPOLITICAL',  sub:'MACRO · NATION-STATE',    color:'#22c55e', apiKey:'orb' },
2233 | };
2234 | 
2235 | var streamOrder = ['congress','pac','legislation','onchain','institutional','geo'];
2236 | var liveData = window._pnLiveData = window._pnLiveData || {};   // filled by API calls, shared across scopes
2237 | var scores = {};     // filled after data arrives
2238 | 
2239 | // ─── Gauge arc math ─────────────────────────────────────────────────────────
2240 | var ARC_LEN = 157; // approx circumference of the half-circle path at r=50
2241 | 
2242 | function scoreToArc(score) {
2243 |   return Math.max(0, Math.min(ARC_LEN, (score / 100) * ARC_LEN));
2244 | }
2245 | 
2246 | function scoreToNeedleAngle(score) {
2247 |   // -90deg (full left) to +90deg (full right)
2248 |   return -90 + (score / 100) * 180;
2249 | }
2250 | 
2251 | function scoreToColor(score) {
2252 |   if (score >= 80) return '#CC0000';
2253 |   if (score >= 65) return '#f8c15c';
2254 |   if (score >= 50) return '#22c55e';
2255 |   return 'rgba(255,255,255,0.35)';
2256 | }
2257 | 
2258 | function scoreToVerdict(score) {
2259 |   if (score >= 85) return { label:'▲ STRONG BULL', col:'#CC0000' };
2260 |   if (score >= 70) return { label:'▲ BULLISH', col:'#f8c15c' };
2261 |   if (score >= 55) return { label:'→ NEUTRAL', col:'rgba(255,255,255,0.45)' };
2262 |   return { label:'▼ CAUTION', col:'#888' };
2263 | }
2264 | 
2265 | function animateGauge(streamId, score) {
2266 |   var color = scoreToColor(score);
2267 |   var arcEl = document.getElementById('ga-' + streamId);
2268 |   var needleEl = document.getElementById('gn-' + streamId);
2269 |   var scoreEl = document.getElementById('gs-' + streamId);
2270 |   var arrEl = document.getElementById('garr-' + streamId);
2271 | 
2272 |   if (!arcEl) return;
2273 | 
2274 |   // Remove skeleton state once real data arrives
2275 |   arcEl.classList.remove('skeleton');
2276 | 
2277 |   arcEl.style.stroke = color;
2278 |   arcEl.style.strokeDasharray = scoreToArc(score) + ' ' + ARC_LEN;
2279 | 
2280 |   var angle = scoreToNeedleAngle(score);
2281 |   needleEl.style.transform = 'rotate(' + angle + 'deg)';
2282 |   scoreEl.textContent = score;
2283 |   scoreEl.style.fill = color;
2284 | 
2285 |   var v = scoreToVerdict(score);
2286 |   arrEl.textContent = v.label.split(' ')[0];
2287 |   arrEl.style.color = v.col;
2288 | }
2289 | 
2290 | function updateComposite(allScores) {
2291 |   var vals = Object.values(allScores);
2292 |   if (!vals.length) return;
2293 |   var avg = Math.round(vals.reduce(function(a,b){return a+b;},0)/vals.length);
2294 |   var scoreEl = document.getElementById('ss2-score-num');
2295 |   var verdEl = document.getElementById('ss2-verdict');
2296 |   var v = scoreToVerdict(avg);
2297 |   if (scoreEl) { scoreEl.textContent = avg; scoreEl.style.color = v.col; }
2298 |   if (verdEl) { verdEl.textContent = v.label; verdEl.style.color = v.col; }
2299 |   // Update waterfall heading
2300 |   var wfHead = document.querySelector('#ss2-waterfall .ss2-overline');
2301 |   if (wfHead) wfHead.innerHTML = 'CONVERGENCE WATERFALL &nbsp;<span style="color:rgba(255,255,255,0.2);font-size:6px;">· CONTRIBUTION TO ' + avg + '/100</span>';
2302 |   return avg;
2303 | }
2304 | 
2305 | // ─── API fetches — progressive rendering with error handling + timeouts ──────
2306 | var _fetchCycleId = 0;  // prevents stale renders from old fetch cycles
2307 | 
2308 | function progressiveRender() {
2309 |   computeScores();
2310 |   renderAll();
2311 | }
2312 | 
2313 | window.fetchWithTimeout = function fetchWithTimeout(url, timeoutMs) {
2314 |   var controller = new AbortController();
2315 |   var timeoutId = setTimeout(function(){ controller.abort(); }, timeoutMs || 10000);
2316 |   return fetch(url, { signal: controller.signal })
2317 |     .then(function(r){ clearTimeout(timeoutId); return r.json(); })
2318 |     .catch(function(err){
2319 |       clearTimeout(timeoutId);
2320 |       console.warn('[PANOPTICON] Fetch failed: ' + url, err.name === 'AbortError' ? '(timeout)' : err.message);
2321 |       return null;
2322 |     });
2323 | }
2324 | 
2325 | function fetchAll() {
2326 |   var cycleId = ++_fetchCycleId;
2327 |   var calls = [
2328 |     fetchWithTimeout('/api/congress/ihx', 10000).then(function(d){ if(d && cycleId===_fetchCycleId){ liveData.ihx=d; progressiveRender(); } }),
2329 |     fetchWithTimeout('/api/donations/pulse', 10000).then(function(d){ if(d && cycleId===_fetchCycleId){ liveData.pac=d; progressiveRender(); } }),
2330 |     fetchWithTimeout('/api/panopticon/bills', 10000).then(function(d){ if(d && cycleId===_fetchCycleId){ liveData.bills=d; progressiveRender(); } }),
2331 |     fetchWithTimeout('/api/orb', 10000).then(function(d){ if(d && cycleId===_fetchCycleId){ liveData.orb=d; progressiveRender(); } }),
2332 |     fetchWithTimeout('/api/panopticon/institutional', 10000).then(function(d){ if(d && cycleId===_fetchCycleId){ liveData.inst=d; progressiveRender(); } }),
2333 |     fetchWithTimeout('/api/congress/trades', 10000).then(function(d){ if(d && cycleId===_fetchCycleId){ liveData.trades=d; progressiveRender(); } }),
2334 |     fetchWithTimeout('/api/panopticon/pe-datastream', 10000).then(function(d){ if(d && cycleId===_fetchCycleId){ liveData.pe=d; progressiveRender(); } }),
2335 |   ];
2336 |   // Final pass after all settle to ensure complete render
2337 |   Promise.allSettled(calls).then(function(){ if(cycleId===_fetchCycleId) progressiveRender(); });
2338 | }
2339 | 
2340 | function computeScores() {
2341 |   var ihx = liveData.ihx || {};
2342 |   var pac = liveData.pac || {};
2343 |   var bills = liveData.bills || {};
2344 |   var orb = (liveData.orb || {});
2345 |   var inst = liveData.inst || {};
2346 |   var streams = orb.streams || {};
2347 | 
2348 |   // Congress: IHX score is 0-100
2349 |   scores.congress = ihx.score || 64;
2350 | 
2351 |   // PAC: donation pulse score
2352 |   scores.pac = pac.score || 88;
2353 | 
2354 |   // Legislation: weight GENIUS (passed=+25), bill bullish count, bills_with_votes
2355 |   var legBase = 50;
2356 |   var billsWithVotes = bills.bills_with_votes || 0;
2357 |   var bullish = bills.bullish_count || 0;
2358 |   legBase += Math.min(30, billsWithVotes * 6);
2359 |   legBase += Math.min(10, bullish * 5);
2360 |   legBase += 15; // GENIUS Act supermajority permanent bonus
2361 |   scores.legislation = Math.min(100, legBase);
2362 | 
2363 |   // On-chain: blend ORB streams (hashrate, accum, exchange_flow, whale)
2364 |   var hashrate = streams.hashrate || 83;
2365 |   var accum = streams.accum || 65;
2366 |   var exchFlow = streams.exchange_flow || 50;
2367 |   var whale = streams.whale || 90;
2368 |   scores.onchain = Math.round((hashrate * 0.3 + accum * 0.3 + exchFlow * 0.2 + whale * 0.2));
2369 | 
2370 |   // Institutional: filers + coalition signal
2371 |   var filers = inst.total_institutional_filers || 20;
2372 |   var coalition = (inst.coalition_summary || {}).count || 0;
2373 |   scores.institutional = Math.min(100, Math.round(40 + filers * 1.2 + coalition * 0.5));
2374 | 
2375 |   // Geo: macro_corr + polymarket blend from ORB
2376 |   var macro = streams.macro_corr || 69.8;
2377 |   var poly = streams.polymarket || 74;
2378 |   var putcall = streams.put_call || 70;
2379 |   scores.geo = Math.round((macro * 0.4 + poly * 0.3 + putcall * 0.3));
2380 | }
2381 | 
2382 | // ─── Render all elements ─────────────────────────────────────────────────────
2383 | function renderAll() {
2384 |   streamOrder.forEach(function(id) {
2385 |     animateGauge(id, scores[id] || 50);
2386 |     // Update gauge sub-label with live key stat
2387 |     var subEl = document.getElementById('gd-' + id);
2388 |     if (subEl) subEl.textContent = getLiveSubLabel(id);
2389 |   });
2390 |   var avg = updateComposite(scores);
2391 |   renderSignalBoard();
2392 |   renderCorrelationMap();
2393 |   renderWaterfall();
2394 |   document.getElementById('ss2-board-ts').textContent = new Date().toLocaleTimeString() + ' LOCAL';
2395 | }
2396 | 
2397 | function getLiveSubLabel(id) {
2398 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {}, orb = liveData.orb || {};
2399 |   var inst = liveData.inst || {}, bills = liveData.bills || {};
2400 |   var streams = orb.streams || {};
2401 |   switch(id) {
2402 |     case 'congress':     return 'IHX ' + (ihx.score||'—') + ' · ' + (ihx.buy_count||0) + 'B/' + (ihx.sell_count||0) + 'S · ' + (ihx.crypto_trades||0) + ' crypto';
2403 |     case 'pac':          return '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M raised · $' + ((pac.fairshake_spend||0)/1e6).toFixed(1) + 'M spent';
2404 |     case 'legislation':  return (bills.bills_with_votes||0) + ' with votes · GENIUS 66–32';
2405 |     case 'onchain':      return 'HR ' + (streams.hashrate||0) + ' · ACCUM ' + (streams.accum||0) + ' · WHALE ' + (streams.whale||0);
2406 |     case 'institutional':return (inst.total_institutional_filers||0) + ' filers · ' + ((inst.coalition_summary||{}).count||0) + ' coalition';
2407 |     case 'geo':          return 'MACRO ' + Math.round(streams.macro_corr||0) + ' · POLY ' + (streams.polymarket||0) + ' · P/C ' + Math.round(streams.put_call||0);
2408 |   }
2409 |   return '';
2410 | }
2411 | 
2412 | // ─── Data card (expanded on gauge click) ────────────────────────────────────
2413 | var activeGauge = null;
2414 | document.addEventListener('click', function(e) {
2415 |   var cell = e.target.closest('.ss2-gauge-cell');
2416 |   if (cell) {
2417 |     var sid = cell.getAttribute('data-stream');
2418 |     if (activeGauge === sid) {
2419 |       closeCard();
2420 |     } else {
2421 |       openCard(sid, cell);
2422 |     }
2423 |     return;
2424 |   }
2425 |   if (!e.target.closest('#ss2-datacard')) closeCard();
2426 | });
2427 | 
2428 | function closeCard() {
2429 |   var card = document.getElementById('ss2-datacard');
2430 |   card.classList.remove('visible');
2431 |   if (activeGauge) {
2432 |     document.getElementById('gc-' + activeGauge).classList.remove('active');
2433 |   }
2434 |   activeGauge = null;
2435 | }
2436 | 
2437 | function openCard(sid, cell) {
2438 |   if (activeGauge) document.getElementById('gc-' + activeGauge).classList.remove('active');
2439 |   activeGauge = sid;
2440 |   cell.classList.add('active');
2441 | 
2442 |   var card = document.getElementById('ss2-datacard');
2443 |   var score = scores[sid] || 50;
2444 |   var v = scoreToVerdict(score);
2445 | 
2446 |   document.getElementById('ss2-dc-stream').textContent = STREAMS[sid].label + ' STREAM';
2447 |   document.getElementById('ss2-dc-title').textContent = STREAMS[sid].sub;
2448 |   document.getElementById('ss2-dc-score').textContent = score;
2449 |   document.getElementById('ss2-dc-score').style.color = scoreToColor(score);
2450 |   document.getElementById('ss2-dc-verdict').textContent = v.label;
2451 |   document.getElementById('ss2-dc-verdict').style.color = v.col;
2452 | 
2453 |   var rows = getCardRows(sid);
2454 |   var rowsEl = document.getElementById('ss2-dc-rows');
2455 |   rowsEl.innerHTML = rows.map(function(r) {
2456 |     return '<div class="ss2-dc-row"><span class="ss2-dc-key">' + r.k + '</span><span class="ss2-dc-val ' + (r.cls||'') + '">' + r.v + '</span></div>';
2457 |   }).join('');
2458 | 
2459 |   document.getElementById('ss2-dc-insight').textContent = getInsight(sid);
2460 | 
2461 |   // Position card below the clicked gauge row
2462 |   var rect = cell.getBoundingClientRect();
2463 |   var rootRect = document.getElementById('ss2-root').getBoundingClientRect();
2464 |   card.style.top = (rect.bottom - rootRect.top + 8) + 'px';
2465 |   card.classList.add('visible');
2466 | }
2467 | 
2468 | function getCardRows(sid) {
2469 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {}, bills = liveData.bills || {};
2470 |   var orb = liveData.orb || {}, streams = (orb.streams || {}), inst = liveData.inst || {};
2471 |   var pe = liveData.pe || {}, trades = liveData.trades || {};
2472 |   switch(sid) {
2473 |     case 'congress': return [
2474 |       { k:'IHX Score',        v: ihx.score + '/100',                    cls: ihx.score>=70?'green':ihx.score>=50?'gold':'hot' },
2475 |       { k:'Buy / Sell',       v: (ihx.buy_count||0) + ' buys / ' + (ihx.sell_count||0) + ' sells' },
2476 |       { k:'Crypto Trades',    v: (ihx.crypto_trades||0) + ' / 8 total' },
2477 |       { k:'Signal',           v: (ihx.signal||'neutral').toUpperCase() },
2478 |       { k:'Top buy',          v: 'McCormick — Bitwise BTC ETF',         cls:'green' },
2479 |       { k:'Top sell',         v: 'Tim Moore — COIN (2-day filing)',      cls:'hot' },
2480 |       { k:'Conviction peak',  v: '95% — Moore COIN, 80-95% — McCormick' },
2481 |       { k:'Net positioning',  v: ihx.buy_count > ihx.sell_count ? 'BULLISH BIAS' : 'MIXED', cls:'gold' },
2482 |     ];
2483 |     case 'pac': var exps = pac.fairshake_expenditures || []; return [
2484 |       { k:'Fairshake raised',  v: '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M (2026 cycle)', cls:'hot' },
2485 |       { k:'Deployed',          v: '$' + ((pac.fairshake_spend||0)/1e6).toFixed(1) + 'M' },
2486 |       { k:'Pulse score',       v: (pac.score||88) + '/100 ' + (pac.label||'HIGH') },
2487 |       { k:'Crypto PACs',       v: (pac.crypto_committees||0) + ' active committees' },
2488 |       { k:'Top donor',         v: 'a16z (AH Capital) — $23.8M',         cls:'gold' },
2489 |       { k:'#2 donor',          v: 'Ben Horowitz — $11.9M' },
2490 |       { k:'#3 donor',          v: 'Marc Andreessen — $11.9M' },
2491 |       { k:'Biggest OPPOSE',    v: (exps[0] ? (exps[0].candidate||'?').substring(0,28) + ' $' + ((exps[0].amount||0)/1e6).toFixed(1)+'M' : '—'), cls:'hot' },
2492 |     ];
2493 |     case 'legislation': var blist = (bills.bills||[]).filter(function(b){return b.congress_score>50;}).slice(0,4); return [
2494 |       { k:'Bills tracked',     v: ((bills.bills||[]).length || 18) + ' total' },
2495 |       { k:'With floor votes',  v: (bills.bills_with_votes||0) + ' bills' },
2496 |       { k:'GENIUS Act',        v: 'PASSED 66–32 Senate',                 cls:'green' },
2497 |       { k:'Market Clarity',    v: '69% congressional support',           cls:'green' },
2498 |       { k:'Anti-CBDC',         v: 'Introduced — Tom Emmer',              cls:'gold' },
2499 |       { k:'BTC Reserve Act',   v: 'Introduced — Tim Burchett',           cls:'gold' },
2500 |       { k:'STABLE Act',        v: 'Introduced — Bryan Steil' },
2501 |       { k:'Bullish vs bearish',v: (bills.bullish_count||0) + 'B / ' + (bills.bearish_count||0) + 'B gap' },
2502 |     ];
2503 |     case 'onchain': return [
2504 |       { k:'Hashrate signal',   v: (streams.hashrate||0) + '/100',         cls: streams.hashrate>=80?'green':'gold' },
2505 |       { k:'Accumulation',      v: (streams.accum||0) + '/100' },
2506 |       { k:'Exchange flow',     v: (streams.exchange_flow||0) + '/100' },
2507 |       { k:'Whale signal',      v: (streams.whale||0) + '/100',            cls: streams.whale>=80?'green':'gold' },
2508 |       { k:'Fear & Greed',      v: (streams.fear_greed||0) + '/100 (FEAR)',cls: streams.fear_greed<=30?'hot':'' },
2509 |       { k:'Fee signal',        v: (streams.fees||0) + '/100',             cls: streams.fees>=90?'green':'' },
2510 |       { k:'SOPR',              v: '0.15 — capitulation zone',             cls:'hot' },
2511 |       { k:'Puell Multiple',    v: 'Green accumulation band',              cls:'green' },
2512 |     ];
2513 |     case 'institutional': return [
2514 |       { k:'Total 13F filers',  v: (inst.total_institutional_filers||0),  cls:'green' },
2515 |       { k:'Coalition detected',v: ((inst.coalition_summary||{}).count||0) + ' coordinated', cls:'hot' },
2516 |       { k:'PE Form D rounds',  v: (pe.pe_count||0) + ' active raises' },
2517 |       { k:'Top filer',         v: 'ParaFi Capital LP — hedge fund',       cls:'gold' },
2518 |       { k:'#2 filer',          v: 'Avenir Tech Ltd — hedge fund' },
2519 |       { k:'#3 filer',          v: 'Galaxy Institutional Bitcoin Fund' },
2520 |       { k:'Coalition signal',  v: (inst.coalition_summary||{}).detected ? 'ACTIVE — coordinated accumulation' : 'None', cls:(inst.coalition_summary||{}).detected?'hot':'' },
2521 |       { k:'Form 4 insiders',   v: 'Coinbase exec cluster buying',         cls:'green' },
2522 |     ];
2523 |     case 'geo': return [
2524 |       { k:'Macro correlation', v: Math.round(streams.macro_corr||0) + '/100',   cls: streams.macro_corr>=65?'green':'' },
2525 |       { k:'Polymarket signal', v: (streams.polymarket||0) + '/100' },
2526 |       { k:'Put/Call ratio',    v: Math.round(streams.put_call||0) + '/100',      cls:'green' },
2527 |       { k:'US Strategic Res.', v: 'EO 14233 — BTC stockpile active',     cls:'green' },
2528 |       { k:'Fed rate (Apr)',    v: '98.2% NO CHANGE (Polymarket)',          cls:'green' },
2529 |       { k:'10Y Treasury',      v: '3.21%' },
2530 |       { k:'JPY pressure',      v: 'Yen debasement accelerating',          cls:'gold' },
2531 |       { k:'EU MiCA',           v: 'Full implementation — neutral' },
2532 |     ];
2533 |   }
2534 |   return [];
2535 | }
2536 | 
2537 | function getInsight(sid) {
2538 |   var insights = {
2539 |     congress:    'IHX at 64 (neutral) with 6/8 crypto-adjacent. McCormick buying Bitwise BTC ETF at 80-95% conviction while Tim Moore\'s 2-day COIN filing speed signals insider awareness. Net positioning: informed bifurcation between senators and representatives.',
2540 |     pac:         'Fairshake 2026 is the largest crypto political operation in US history. a16z, Horowitz, Andreessen coordinating $134M to reshape the congressional map — primarily opposing anti-crypto incumbents. This capital velocity is unprecedented and structurally bullish for regulatory outcomes.',
2541 |     legislation: 'GENIUS Act passing 66-32 was the first major crypto legislation through the Senate. Digital Asset Market Clarity at 69% support signals bipartisan floor momentum. The regulatory moat is forming faster than previous cycles.',
2542 |     onchain:     'SOPR at 0.15 is a deep loss-realization signal. Historical analogue: sub-0.2 SOPR in Q4 2018 preceded +312% over 18 months. Puell Multiple in green band + ATH hashrate (miners not selling) = smart money accumulation concurrent with retail capitulation.',
2543 |     institutional:'Coalition of 18 institutions with coordinated accumulation windows. Galaxy, ParaFi, Coinbase insiders buying via separate channels. Classic informed money vs uninformed market divergence.',
2544 |     geo:         'US Strategic Bitcoin Reserve (EO 14233) represents sovereign demand. 98.2% Polymarket probability of Fed hold removes tail risk. Yen debasement creates structural Bitcoin demand from Japanese capital. Macro backdrop is the most constructive since 2020.',
2545 |   };
2546 |   return insights[sid] || '';
2547 | }
2548 | 
2549 | // ─── Correlation network graph (D3 force-directed) ──────────────────────────
2550 | var _d3Sim = null;  // hold simulation reference for cleanup
2551 | 
2552 | function renderCorrelationMap() {
2553 |   var container = document.getElementById('ss2-map-graph');
2554 |   if (!container || typeof d3 === 'undefined') return;
2555 | 
2556 |   var W = container.clientWidth || 400;
2557 |   var H = Math.max(container.clientHeight || 0, 260);
2558 | 
2559 |   // Index codes for compact node labels
2560 |   var INDEX_CODES = {
2561 |     congress:'IHX', pac:'EPX', legislation:'MCX',
2562 |     onchain:'OCX', institutional:'FDX', geo:'OPX'
2563 |   };
2564 | 
2565 |   // Score-based node color
2566 |   function nodeColor(s) { return s >= 65 ? '#10B981' : s >= 45 ? '#F59E0B' : '#CC0000'; }
2567 |   function nodeRadius(s) { return 18 + (s / 100) * 16; }
2568 | 
2569 |   // Build nodes from live scores
2570 |   var nodes = streamOrder.map(function(sid) {
2571 |     var s = scores[sid] || 50;
2572 |     return { id: sid, code: INDEX_CODES[sid], score: s, r: nodeRadius(s), fill: nodeColor(s) };
2573 |   });
2574 | 
2575 |   // Build edges: correlation = closeness of scores
2576 |   var links = [];
2577 |   for (var i = 0; i < nodes.length; i++) {
2578 |     for (var j = i + 1; j < nodes.length; j++) {
2579 |       var diff = Math.abs(nodes[i].score - nodes[j].score);
2580 |       if (diff > 30) continue; // no edge for LOW correlation
2581 |       var strength = diff < 15 ? 'high' : 'medium';
2582 |       var aBull = nodes[i].score >= 65, bBull = nodes[j].score >= 65;
2583 |       var aBear = nodes[i].score < 45, bBear = nodes[j].score < 45;
2584 |       var edgeColor;
2585 |       if (aBull && bBull) edgeColor = 'rgba(16,185,129,0.4)';
2586 |       else if (aBear && bBear) edgeColor = 'rgba(204,0,0,0.3)';
2587 |       else edgeColor = 'rgba(248,196,92,0.25)';
2588 |       links.push({
2589 |         source: nodes[i].id, target: nodes[j].id,
2590 |         strength: strength, color: edgeColor,
2591 |         width: strength === 'high' ? 3 : 1.5,
2592 |         dash: strength === 'high' ? 'none' : '4 4'
2593 |       });
2594 |     }
2595 |   }
2596 | 
2597 |   // On first call: create SVG. On subsequent calls: update in place.
2598 |   var svg = d3.select(container).select('svg');
2599 |   var isNew = svg.empty();
2600 |   if (isNew) {
2601 |     svg = d3.select(container).append('svg')
2602 |       .attr('width', W).attr('height', H)
2603 |       .style('background', '#050505');
2604 | 
2605 |     // Subtle grid pattern
2606 |     var defs = svg.append('defs');
2607 |     var pat = defs.append('pattern').attr('id','ss2-grid-pat')
2608 |       .attr('width',40).attr('height',40).attr('patternUnits','userSpaceOnUse');
2609 |     pat.append('path').attr('d','M 40 0 L 0 0 0 40')
2610 |       .attr('fill','none').attr('stroke','rgba(255,255,255,0.03)').attr('stroke-width',0.5);
2611 |     // Glow filter
2612 |     var glow = defs.append('filter').attr('id','ss2-node-glow')
2613 |       .attr('x','-50%').attr('y','-50%').attr('width','200%').attr('height','200%');
2614 |     glow.append('feGaussianBlur').attr('stdDeviation','6').attr('result','blur');
2615 |     glow.append('feComposite').attr('in','SourceGraphic').attr('in2','blur').attr('operator','over');
2616 | 
2617 |     svg.append('rect').attr('width',W).attr('height',H).attr('fill','url(#ss2-grid-pat)');
2618 |     svg.append('g').attr('class','ss2-links');
2619 |     svg.append('g').attr('class','ss2-nodes');
2620 |   } else {
2621 |     svg.attr('width', W).attr('height', H);
2622 |     svg.select('rect').attr('width', W).attr('height', H);
2623 |   }
2624 | 
2625 |   // --- Update links ---
2626 |   var linkSel = svg.select('.ss2-links').selectAll('line').data(links, function(d) { return d.source.id || d.source; });
2627 |   linkSel.exit().transition().duration(400).style('opacity', 0).remove();
2628 |   var linkEnter = linkSel.enter().append('line').style('opacity', 0);
2629 |   var linkAll = linkEnter.merge(linkSel);
2630 |   linkAll.transition().duration(800)
2631 |     .style('opacity', 1)
2632 |     .attr('stroke', function(d) { return d.color; })
2633 |     .attr('stroke-width', function(d) { return d.width; })
2634 |     .attr('stroke-dasharray', function(d) { return d.dash; });
2635 | 
2636 |   // --- Update nodes ---
2637 |   var nodeSel = svg.select('.ss2-nodes').selectAll('g.ss2-node').data(nodes, function(d) { return d.id; });
2638 |   nodeSel.exit().remove();
2639 | 
2640 |   var nodeEnter = nodeSel.enter().append('g').attr('class','ss2-node').style('cursor','pointer');
2641 |   // Glow circle (behind)
2642 |   nodeEnter.append('circle').attr('class','ss2-glow')
2643 |     .attr('r', function(d) { return d.r * 1.8; })
2644 |     .attr('fill','none').attr('filter','url(#ss2-node-glow)');
2645 |   // Main circle
2646 |   nodeEnter.append('circle').attr('class','ss2-disc')
2647 |     .attr('r', function(d) { return d.r; })
2648 |     .attr('stroke-width', 1.5);
2649 |   // Index code label
2650 |   nodeEnter.append('text').attr('class','ss2-code')
2651 |     .attr('text-anchor','middle').attr('dy','-0.15em')
2652 |     .style('font-family','JetBrains Mono, monospace').style('font-weight','800')
2653 |     .style('font-size','11px').style('fill','#fff').style('pointer-events','none');
2654 |   // Score label
2655 |   nodeEnter.append('text').attr('class','ss2-nscore')
2656 |     .attr('text-anchor','middle').attr('dy','1.15em')
2657 |     .style('font-family','JetBrains Mono, monospace').style('font-weight','600')
2658 |     .style('font-size','9px').style('fill','rgba(255,255,255,0.7)').style('pointer-events','none');
2659 | 
2660 |   var nodeAll = nodeEnter.merge(nodeSel);
2661 | 
2662 |   // Animated transitions for score changes
2663 |   nodeAll.select('.ss2-glow').transition().duration(800)
2664 |     .attr('r', function(d) { return d.r * 1.8; })
2665 |     .attr('stroke', function(d) { return d.fill; })
2666 |     .attr('stroke-width', 2)
2667 |     .attr('opacity', 0.35);
2668 |   nodeAll.select('.ss2-disc').transition().duration(800)
2669 |     .attr('r', function(d) { return d.r; })
2670 |     .attr('fill', function(d) { return d.fill + '18'; })
2671 |     .attr('stroke', function(d) { return d.fill; });
2672 |   nodeAll.select('.ss2-code').text(function(d) { return d.code; });
2673 |   nodeAll.select('.ss2-nscore').text(function(d) { return d.score; });
2674 | 
2675 |   // --- Hover + click interactions ---
2676 |   var tooltip = document.getElementById('ss2-map-tooltip');
2677 | 
2678 |   nodeAll.on('mouseenter', function(ev, d) {
2679 |     // Dim unconnected edges
2680 |     var connected = {};
2681 |     links.forEach(function(l) {
2682 |       var s = l.source.id || l.source, t = l.target.id || l.target;
2683 |       if (s === d.id || t === d.id) { connected[s] = true; connected[t] = true; }
2684 |     });
2685 |     svg.select('.ss2-links').selectAll('line').transition().duration(200)
2686 |       .style('opacity', function(l) {
2687 |         var s = l.source.id || l.source, t = l.target.id || l.target;
2688 |         return (s === d.id || t === d.id) ? 1 : 0.08;
2689 |       });
2690 |     svg.select('.ss2-nodes').selectAll('g.ss2-node').transition().duration(200)
2691 |       .style('opacity', function(n) { return connected[n.id] ? 1 : 0.25; });
2692 | 
2693 |     // Tooltip
2694 |     var rect = container.getBoundingClientRect();
2695 |     var cx = ev.clientX - rect.left, cy = ev.clientY - rect.top;
2696 |     tooltip.style.opacity = '1';
2697 |     tooltip.style.left = (cx + 18) + 'px';
2698 |     tooltip.style.top = (cy - 14) + 'px';
2699 |     tooltip.innerHTML = '<div style="color:' + d.fill + ';font-size:7px;letter-spacing:.15em;margin-bottom:3px;">' + STREAMS[d.id].label + ' (' + d.code + ')</div>'
2700 |       + '<div style="font-size:11px;font-weight:700;">' + d.score + '/100</div>'
2701 |       + '<div style="font-size:8px;color:rgba(255,255,255,0.5);margin-top:3px;">' + getLiveSubLabel(d.id) + '</div>'
2702 |       + '<div style="font-size:7px;color:rgba(255,255,255,0.3);margin-top:4px;">Click for full breakdown</div>';
2703 |   })
2704 |   .on('mouseleave', function() {
2705 |     svg.select('.ss2-links').selectAll('line').transition().duration(300).style('opacity', 1);
2706 |     svg.select('.ss2-nodes').selectAll('g.ss2-node').transition().duration(300).style('opacity', 1);
2707 |     tooltip.style.opacity = '0';
2708 |   })
2709 |   .on('click', function(ev, d) {
2710 |     var cell = document.getElementById('gc-' + d.id);
2711 |     if (cell) cell.click();
2712 |   });
2713 | 
2714 |   // --- D3 drag ---
2715 |   nodeAll.call(d3.drag()
2716 |     .on('start', function(ev, d) {
2717 |       if (!ev.active && _d3Sim) _d3Sim.alphaTarget(0.3).restart();
2718 |       d.fx = d.x; d.fy = d.y;
2719 |     })
2720 |     .on('drag', function(ev, d) { d.fx = ev.x; d.fy = ev.y; })
2721 |     .on('end', function(ev, d) {
2722 |       if (!ev.active && _d3Sim) _d3Sim.alphaTarget(0);
2723 |       d.fx = null; d.fy = null;
2724 |     })
2725 |   );
2726 | 
2727 |   // --- Force simulation ---
2728 |   if (_d3Sim) _d3Sim.stop();
2729 |   _d3Sim = d3.forceSimulation(nodes)
2730 |     .force('charge', d3.forceManyBody().strength(-200))
2731 |     .force('link', d3.forceLink(links).id(function(d) { return d.id; }).distance(80))
2732 |     .force('center', d3.forceCenter(W / 2, H / 2))
2733 |     .force('collision', d3.forceCollide().radius(function(d) { return d.r + 6; }))
2734 |     .force('bounds', function() {
2735 |       nodes.forEach(function(d) {
2736 |         d.x = Math.max(d.r + 4, Math.min(W - d.r - 4, d.x));
2737 |         d.y = Math.max(d.r + 4, Math.min(H - d.r - 4, d.y));
2738 |       });
2739 |     })
2740 |     .alphaDecay(0.03)
2741 |     .on('tick', function() {
2742 |       linkAll
2743 |         .attr('x1', function(d) { return d.source.x; })
2744 |         .attr('y1', function(d) { return d.source.y; })
2745 |         .attr('x2', function(d) { return d.target.x; })
2746 |         .attr('y2', function(d) { return d.target.y; });
2747 |       nodeAll.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
2748 |     });
2749 | }
2750 | 
2751 | // ─── Signal board ────────────────────────────────────────────────────────────
2752 | function renderSignalBoard() {
2753 |   var board = document.getElementById('ss2-signal-board');
2754 |   if (!board) return;
2755 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {};
2756 |   var orb = liveData.orb || {}, streams = orb.streams || {};
2757 |   var inst = liveData.inst || {}, bills = liveData.bills || {};
2758 |   var exps = pac.fairshake_expenditures || [];
2759 | 
2760 |   var items = [
2761 |     // CRITICAL (red)
2762 |     { col:'#CC0000', label:'PAC CAPITAL · CRITICAL', text:'Fairshake PAC raised $' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M — largest crypto political operation in US history', val: '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M' },
2763 |     exps[0] ? { col:'#CC0000', label:'FAIRSHAKE · TOP EXPENDITURE', text:exps[0].candidate + ' — ' + (exps[0].support==='O'?'OPPOSE':'SUPPORT'), val: '$' + ((exps[0].amount||0)/1e6).toFixed(1) + 'M' } : null,
2764 |     // SIGNAL (orange)
2765 |     { col:'#f8c15c', label:'ON-CHAIN · SOPR SIGNAL', text:'SOPR at 0.15 — historical capitulation. Prior sub-0.2 episodes: avg +312% over 18 months', val: '0.15' },
2766 |     streams.hashrate >= 80 ? { col:'#f8c15c', label:'ON-CHAIN · HASHRATE', text:'Hashrate signal at ' + streams.hashrate + '/100 — miners holding, not selling into weakness', val: streams.hashrate + '/100' } : null,
2767 |     { col:'#f8c15c', label:'CONGRESS · IHX', text:'Insider Heat Index ' + (ihx.score||64) + '/100 — ' + (ihx.buy_count||0) + ' buys vs ' + (ihx.sell_count||0) + ' sells, ' + (ihx.crypto_trades||0) + ' crypto-adjacent', val: (ihx.score||64) + '/100' },
2768 |     { col:'#22c55e', label:'LEGISLATION · GENIUS ACT', text:'Passed Senate 66–32. Digital Asset Market Clarity at 69% congressional support. Regulatory moat forming.', val: '66–32' },
2769 |     (inst.total_institutional_filers||0) > 15 ? { col:'#22c55e', label:'INSTITUTIONAL · COALITION', text:((inst.coalition_summary||{}).count||0) + ' institutions in coordinated BTC ETF accumulation windows — ' + (inst.total_institutional_filers||0) + ' total 13F filers', val: (inst.total_institutional_filers||0) + ' filers' } : null,
2770 |     streams.whale >= 80 ? { col:'#22c55e', label:'ON-CHAIN · WHALE SIGNAL', text:'Whale accumulation signal at ' + streams.whale + '/100 — on-chain large wallet flows bullish', val: streams.whale + '/100' } : null,
2771 |     // NOTE (dim)
2772 |     { col:'rgba(255,255,255,0.3)', label:'GEO · FED RATE', text:'98.2% Polymarket probability of no rate change in April — macro tail risk removed for current cycle', val: '98.2%' },
2773 |     { col:'rgba(255,255,255,0.3)', label:'GEO · US STRATEGIC RESERVE', text:'Executive Order 14233 establishes national Bitcoin stockpile — sovereign demand signal', val: 'EO 14233' },
2774 |   ].filter(Boolean);
2775 | 
2776 |   board.innerHTML = items.map(function(item) {
2777 |     return '<div class="ss2-signal-item">'
2778 |       + '<div class="ss2-si-dot" style="background:' + item.col + ';box-shadow:0 0 4px ' + item.col + ';"></div>'
2779 |       + '<div class="ss2-si-body">'
2780 |       + '<div class="ss2-si-label" style="color:' + item.col + ';">' + item.label + '</div>'
2781 |       + '<div class="ss2-si-text">' + item.text + '</div>'
2782 |       + '</div>'
2783 |       + '<div class="ss2-si-val" style="color:' + item.col + ';">' + item.val + '</div>'
2784 |       + '</div>';
2785 |   }).join('');
2786 | }
2787 | 
2788 | // ─── Waterfall bars ───────────────────────────────────────────────────────────
2789 | function renderWaterfall() {
2790 |   var el = document.getElementById('ss2-waterfall-bars');
2791 |   if (!el) return;
2792 |   var totalScore = 0;
2793 |   streamOrder.forEach(function(id) { totalScore += (scores[id]||0); });
2794 |   var avg = totalScore / streamOrder.length;
2795 | 
2796 |   el.innerHTML = streamOrder.map(function(sid) {
2797 |     var score = scores[sid] || 50;
2798 |     var color = scoreToColor(score);
2799 |     var contrib = Math.round((score / totalScore) * 100);
2800 |     var pct = (score / 100) * 100;
2801 |     return '<div class="ss2-wf-col" onclick="(function(){var cell=document.getElementById(\'gc-\'+\'' + sid + '\');if(cell)cell.click();})();">'
2802 |       + '<div class="ss2-wf-bar-wrap"><div class="ss2-wf-bar" style="height:' + pct + '%;background:' + color + ';box-shadow:0 0 8px ' + color + '44;"></div></div>'
2803 |       + '<div class="ss2-wf-score" style="color:' + color + ';">' + score + '</div>'
2804 |       + '<div class="ss2-wf-label">' + STREAMS[sid].label + '</div>'
2805 |       + '<div class="ss2-wf-contrib">' + contrib + '% weight</div>'
2806 |       + '</div>';
2807 |   }).join('');
2808 | }
2809 | 
2810 | // ─── Init ────────────────────────────────────────────────────────────────────
2811 | // Set skeleton state on all gauge arcs before data arrives
2812 | streamOrder.forEach(function(id) {
2813 |   var arcEl = document.getElementById('ga-' + id);
2814 |   if (arcEl) arcEl.classList.add('skeleton');
2815 | });
2816 | fetchAll();
2817 | var _ss2RefreshInterval = setInterval(fetchAll, 120000); // refresh every 2 min
2818 | 
2819 | // Cleanup intervals on page unload to prevent memory leaks
2820 | window.addEventListener('beforeunload', function() {
2821 |   clearInterval(_ss2RefreshInterval);
2822 | });
2823 | 
2824 | // Close card when pressing Escape
2825 | document.addEventListener('keydown', function(e) {
2826 |   if (e.key === 'Escape') closeCard();
2827 | });
2828 | 
2829 | })();
2830 | </script>
2831 | 
2832 | 
2833 | <!-- ═══ TWO-ZONE LAYOUT: LEFT EVIDENCE + RIGHT INTEL RAIL ═══ -->
2834 | <div class="pn-main">
2835 |     <div class="pn-grid">
2836 | 
2837 |         <!-- ═══ LEFT MAIN (65%): EVIDENCE — DISCLOSURES + FLAGGED + CORRELATION ═══ -->
2838 |         <div class="pn-left-main">
2839 | 
2840 |         <!-- ═══ TIER 1: CONFIRMED DISCLOSURES ═══ -->
2841 |         <div class="pn-panel pn-tier-confirmed">
2842 |             <div class="pn-panel-head">
2843 |                 <span class="tier-dot"></span>
2844 |                 <span class="tier-label">TIER 1 — CONFIRMED</span>
2845 |                 <span class="pn-tier-badge tier-1">STOCK ACT</span>
2846 |                 <span class="tier-count">{{ data.disclosures|length }} FILED</span>
2847 |             </div>
2848 | 
2849 |             {% if not demo_mode and data.disclosures_live is defined and not data.disclosures_live %}
2850 |             <div class="pn-fallback-banner">
2851 |                 <strong>HISTORICAL DATA</strong> &mdash; Live data from efts.house.gov temporarily unavailable. Displaying documented public examples from {{ data.fallback_as_of|default('recent filings') }}.
2852 |             </div>
2853 |             {% endif %}
2854 | 
2855 |             <div id="pnDisclosures">
2856 |                 {% for d in data.disclosures %}
2857 |                 <div class="pn-disc-card" data-party="{{ d.party|default('') }}">
2858 |                     <div class="pn-disc-head">
2859 |                         <div class="pn-disc-entity">{{ d.entity }}</div>
2860 |                         {% if d.amount_range %}<span class="pn-disc-amount-tag">{{ d.amount_range }}</span>{% endif %}
2861 |                         {% if d.party %}
2862 |                         <span class="pn-disc-party {{ d.party }}">{{ d.party }}</span>
2863 |                         {% endif %}
2864 |                     </div>
2865 |                     <div class="pn-disc-fields">
2866 |                         <div>
2867 |                             <div class="pn-disc-field-label">Asset</div>
2868 |                             <div class="pn-disc-field-val asset-val">{{ d.asset }}</div>
2869 |                         </div>
2870 |                         <div>
2871 |                             <div class="pn-disc-field-label">Type</div>
2872 |                             <div class="pn-disc-field-val type-val {{ 'buy' if d.trade_type == 'purchase' else 'sell' if d.trade_type == 'sale' else '' }}">{{ d.trade_type|upper }}</div>
2873 |                         </div>
2874 |                         <div>
2875 |                             <div class="pn-disc-field-label">Amount</div>
2876 |                             <div class="pn-disc-field-val">{{ d.amount_range }}</div>
2877 |                         </div>
2878 |                         <div>
2879 |                             <div class="pn-disc-field-label">Filed</div>
2880 |                             <div class="pn-disc-field-val">{{ d.date_filed }}</div>
2881 |                         </div>
2882 |                         {% if d.get('days_to_file') %}
2883 |                         <div>
2884 |                             <div class="pn-disc-field-label">Days to File</div>
2885 |                             <div class="pn-disc-field-val">{{ d.days_to_file }}d</div>
2886 |                         </div>
2887 |                         {% endif %}
2888 |                         {% if d.get('committee') %}
2889 |                         <div>
2890 |                             <div class="pn-disc-field-label">Committee</div>
2891 |                             <div class="pn-disc-field-val">{{ d.committee }}</div>
2892 |                         </div>
2893 |                         {% endif %}
2894 |                     </div>
2895 |                     {% if d.get('conviction') and d.conviction.score > 0 %}
2896 |                     <div class="pn-conviction">
2897 |                         <span class="pn-conviction-label">CONVICTION</span>
2898 |                         <span class="pn-conviction-score {{ d.conviction.color }}">{{ d.conviction.score }}%</span>
2899 |                         <span class="pn-conviction-tag {{ d.conviction.color }}">{{ d.conviction.label }}</span>
2900 |                         <div class="pn-conviction-bar">
2901 |                             <div class="pn-conviction-bar-fill {{ d.conviction.color }}" style="width:{{ d.conviction.score }}%"></div>
2902 |                         </div>
2903 |                     </div>
2904 |                     {% endif %}
2905 |                     {% if d.get('correlation_note') %}
2906 |                     <div class="pn-disc-correlation">{{ d.correlation_note }}</div>
2907 |                     {% endif %}
2908 |                     {% if d.get('status') == 'loading' %}
2909 |                     <div style="margin-top:8px;">
2910 |                         <span class="pn-status-chip loading">Awaiting Live Data</span>
2911 |                     </div>
2912 |                     {% endif %}
2913 |                     <div class="pn-disc-source">
2914 |                         Source: <a href="{{ d.source_url }}" target="_blank" rel="noopener">Public Financial Disclosure</a>
2915 |                     </div>
2916 |                 </div>
2917 |                 {% endfor %}
2918 |                 {% if not data.disclosures %}
2919 |                 <div class="pn-empty">No crypto-related disclosures in current window</div>
2920 |                 {% endif %}
2921 |             </div>
2922 | 
2923 |             <!-- WATCH LIST -->
2924 |             {% if data.watch_list %}
2925 |             <div class="pn-section-label">TIER 3 — WATCH LIST</div>
2926 |             {% for w in data.watch_list %}
2927 |             <div class="pn-watchlist-item">
2928 |                 <div class="pn-watchlist-name">
2929 |                     {{ w.name }}
2930 |                     <span class="pn-disc-party {{ w.party }}" style="margin-left:4px;font-size:8px;">{{ w.party }}</span>
2931 |                 </div>
2932 |                 <div class="pn-watchlist-note">{{ w.note }}</div>
2933 |             </div>
2934 |             {% endfor %}
2935 |             {% endif %}
2936 |         </div>
2937 | 
2938 |         <!-- ═══ TIER 2: FLAGGED — PATTERN DETECTION ═══ -->
2939 |         <div class="pn-panel pn-tier-flagged">
2940 |             <div class="pn-panel-head">
2941 |                 <span class="tier-dot"></span>
2942 |                 <span class="tier-label">TIER 2 — FLAGGED</span>
2943 |                 <span class="pn-tier-badge tier-2">PATTERNS</span>
2944 |                 <span class="tier-count">{{ data.flagged|length }} DETECTED</span>
2945 |             </div>
2946 | 
2947 |             {% if demo_mode %}
2948 |             <div class="pn-classified-overlay">
2949 |                 <div class="pn-classified-stamp">CLASSIFIED</div>
2950 |                 <div class="pn-classified-sub">Commander Access Required</div>
2951 |                 <a href="/join" class="pn-upgrade-btn">Unlock Intelligence</a>
2952 |             </div>
2953 |             {% endif %}
2954 | 
2955 |             <div class="pn-disclaimer-note">
2956 |                 PATTERN FOR RESEARCH &mdash; NOT VERIFIED. Statistical correlations shown for independent research purposes only. These are computed patterns, not accusations.
2957 |             </div>
2958 | 
2959 |             <!-- Correlation Timeline SVG -->
2960 |             <div class="pn-section-label">CORRELATION TIMELINE</div>
2961 |             <div id="pnCorrelations">
2962 |                 {% for c in data.correlations %}
2963 |                 <div class="pn-corr-timeline" data-idx="{{ loop.index }}">
2964 |                     <!-- Gap indicator -->
2965 |                     {% set gap = c.get('gap_days', 0) %}
2966 |                     {% set gap_color = 'red' if gap < 7 else ('orange' if gap < 30 else 'white') %}
2967 |                     <div class="pn-corr-gap {{ c.get('gap_color', gap_color) }}">
2968 |                         {% if gap < 7 %}&#9888;{% elif gap < 30 %}&#9679;{% else %}&#9675;{% endif %}
2969 |                         {{ gap }} DAY GAP
2970 |                     </div>
2971 | 
2972 |                     <!-- SVG Timeline: Trade Date → Event Date -->
2973 |                     <svg width="100%" height="90" viewBox="0 0 500 90" preserveAspectRatio="xMidYMid meet">
2974 |                         <!-- Trade node -->
2975 |                         <g class="pn-corr-node" transform="translate(60,40)">
2976 |                             <circle r="10" fill="{{ '#ff3b5f' if gap < 7 else ('#f8c15c' if gap < 30 else '#fff') }}" opacity="0.9"/>
2977 |                             <text y="-16" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">TRADE</text>
2978 |                             <text y="28" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7">{{ c.disclosure.date[:10] if c.disclosure else '' }}</text>
2979 |                         </g>
2980 |                         <!-- Connecting line with gap label -->
2981 |                         <path class="pn-corr-path" d="M70,40 L230,40" stroke="{{ '#ff3b5f' if gap < 7 else ('#f8c15c' if gap < 30 else '#555') }}" stroke-width="2" style="animation-delay:0.2s"/>
2982 |                         <text x="150" y="32" text-anchor="middle" fill="{{ '#ff3b5f' if gap < 7 else '#f8c15c' }}" font-family="JetBrains Mono" font-size="10" font-weight="700">{{ gap }}d</text>
2983 |                         <!-- Event node -->
2984 |                         <g class="pn-corr-node" transform="translate(240,40)">
2985 |                             <circle r="10" fill="#fff" opacity="0.7"/>
2986 |                             <text y="-16" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">EVENT</text>
2987 |                         </g>
2988 |                         <!-- Score -->
2989 |                         <path class="pn-corr-path" d="M250,40 L400,40" stroke="var(--pn-gold)" stroke-width="1.5" style="animation-delay:0.6s"/>
2990 |                         <g class="pn-corr-node" transform="translate(420,40)">
2991 |                             <circle r="14" fill="none" stroke="{{ '#ff3b5f' if c.correlation_score > 0.8 else '#f8c15c' }}" stroke-width="2" opacity="0.8"/>
2992 |                             <text y="4" text-anchor="middle" fill="{{ '#ff3b5f' if c.correlation_score > 0.8 else '#f8c15c' }}" font-family="JetBrains Mono" font-size="10" font-weight="700">{{ "%.0f"|format(c.correlation_score * 100) }}%</text>
2993 |                             <text y="28" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">SCORE</text>
2994 |                         </g>
2995 |                     </svg>
2996 | 
2997 |                     <div class="pn-corr-summary">{{ c.timeline_summary }}</div>
2998 | 
2999 |                     <div>
3000 |                         {% if c.disclosure %}
3001 |                         <div class="pn-corr-event-row">
3002 |                             <span class="pn-corr-event-tag disclosure">DISCLOSURE</span>
3003 |                             {{ c.disclosure.entity }} &mdash; {{ c.disclosure.asset }} ({{ c.disclosure.trade_type }})
3004 |                         </div>
3005 |                         {% endif %}
3006 |                         {% for w in c.related_whales %}
3007 |                         <div class="pn-corr-event-row">
3008 |                             <span class="pn-corr-event-tag whale">WHALE</span>
3009 |                             {{ w.entity }} &mdash; {{ w.amount }} {{ w.direction }}
3010 |                         </div>
3011 |                         {% endfor %}
3012 |                         {% for g in c.related_geo %}
3013 |                         <div class="pn-corr-event-row">
3014 |                             <span class="pn-corr-event-tag geo">GEO</span>
3015 |                             {{ g.headline[:80] }}{% if g.headline|length > 80 %}...{% endif %}
3016 |                         </div>
3017 |                         {% endfor %}
3018 |                     </div>
3019 | 
3020 |                     {% if not demo_mode %}
3021 |                     <button class="pn-btc-case-btn" onclick="makeBitcoinCase(this, '{{ c.timeline_summary|e }}')" data-idx="{{ loop.index }}">
3022 |                         &#x20BF; Make the Bitcoin Case
3023 |                     </button>
3024 |                     <div class="pn-btc-case-output" id="btcCase{{ loop.index }}"></div>
3025 |                     {% endif %}
3026 |                 </div>
3027 |                 {% endfor %}
3028 |                 {% if not data.correlations %}
3029 |                 <div class="pn-empty">Awaiting correlated events...</div>
3030 |                 {% endif %}
3031 |             </div>
3032 | 
3033 |             <!-- Flagged Trades -->
3034 |             <div class="pn-section-label">FLAGGED TRADES</div>
3035 |             {% for f in data.flagged %}
3036 |             <div class="pn-disc-card" style="border-left-color:var(--pn-gold);">
3037 |                 <div class="pn-disc-head">
3038 |                     <div class="pn-disc-entity">{{ f.entity }}</div>
3039 |                     {% if f.party %}
3040 |                     <span class="pn-disc-party {{ f.party }}">{{ f.party }}</span>
3041 |                     {% endif %}
3042 |                 </div>
3043 |                 <div class="pn-disc-fields">
3044 |                     <div>
3045 |                         <div class="pn-disc-field-label">Asset</div>
3046 |                         <div class="pn-disc-field-val">{{ f.asset }}</div>
3047 |                     </div>
3048 |                     <div>
3049 |                         <div class="pn-disc-field-label">Score</div>
3050 |                         <div class="pn-disc-field-val" style="color:var(--pn-gold)">{{ "%.0f"|format(f.correlation_score * 100) }}%</div>
3051 |                     </div>
3052 |                 </div>
3053 |                 <div class="pn-disc-correlation" style="border-color:rgba(248,193,92,0.15);color:var(--pn-gold);">{{ f.flag_reason }}</div>
3054 |             </div>
3055 |             {% endfor %}
3056 |             {% if not data.flagged %}
3057 |             <div class="pn-empty">No statistical patterns detected in current window</div>
3058 |             {% endif %}
3059 |         </div>
3060 | 
3061 |         </div><!-- end .pn-left-main -->
3062 | 
3063 |         <!-- ═══ RIGHT RAIL (35%): INTEL — SIGNALS + MARKETS + GEO ═══ -->
3064 |         <div class="pn-right-rail">
3065 |         <div class="pn-panel pn-tier-feed">
3066 |             <div class="pn-panel-head">
3067 |                 <span class="tier-dot"></span>
3068 |                 <span class="tier-label">REAL-TIME FEED</span>
3069 |                 <span class="tier-count">WHALE + MARKET + GEO</span><span style="display:inline-flex;align-items:center;gap:5px;margin-left:10px;"><span id="pnStreamDot" style="width:7px;height:7px;border-radius:50%;background:#888;display:inline-block;"></span><span id="pnStreamLabel" style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.12em;color:#888;">CONNECTING</span></span>
3070 |             </div>
3071 | 
3072 |             <!-- Whale Tracker -->
3073 |             <div class="pn-section-label">WHALE TRACKER</div>
3074 |             <div id="pnWhales">
3075 |                 {% for w in data.whales %}
3076 |                 <div class="pn-whale-item {{ w.tx_type }}">
3077 |                     <div class="pn-whale-row">
3078 |                         <div class="pn-whale-entity">{{ w.entity }}</div>
3079 |                         <span class="pn-whale-type-tag {{ w.tx_type }}">{{ w.tx_type|upper }}</span>
3080 |                         {% if w.get('flow_signal') %}
3081 |                         <span class="pn-whale-signal-tag {{ w.flow_signal }}">{{ w.flow_signal|upper }}</span>
3082 |                         {% endif %}
3083 |                     </div>
3084 |                     <div class="pn-whale-amt {{ w.tx_type }}">
3085 |                         {% if w.tx_type == 'inflow' %}+{% else %}-{% endif %}{{ w.amount_btc }} BTC
3086 |                     </div>
3087 |                     {% if w.amount_usd %}
3088 |                     <div class="pn-whale-usd">${{ "{:,.0f}".format(w.amount_usd) }} USD</div>
3089 |                     {% endif %}
3090 |                     {% if w.get('flow_context') %}
3091 |                     <div class="pn-whale-flow {{ w.flow_signal|default('neutral') }}">
3092 |                         <div class="pn-whale-flow-label">{{ w.flow_label|default('TRANSFER') }}</div>
3093 |                         {{ w.flow_context }}
3094 |                     </div>
3095 |                     {% endif %}
3096 |                     <div class="pn-whale-size-bar" style="width:{{ [w.amount_btc / 10, 100]|min }}%"></div>
3097 |                     <div class="pn-whale-meta">
3098 |                         <span>{{ w.address }}</span>
3099 |                         <a href="{{ w.source_url }}" target="_blank" rel="noopener">View TX &rarr;</a>
3100 |                     </div>
3101 |                 </div>
3102 |                 {% endfor %}
3103 |                 {% if not data.whales %}
3104 |                 <div class="pn-loading">
3105 |                     <div class="pn-loading-dot"></div>
3106 |                     <div class="pn-loading-dot"></div>
3107 |                     <div class="pn-loading-dot"></div>
3108 |                     Scanning whale wallets...
3109 |                 </div>
3110 |                 {% endif %}
3111 |             </div>
3112 | 
3113 |             <!-- Polymarket -->
3114 |             <div class="pn-section-label">BITCOIN PREDICTION MARKETS</div>
3115 |             <div id="pnPolymarket">
3116 |                 {% if data.polymarket %}
3117 |                 <!-- Hero market: highest volume -->
3118 |                 {% set hero = data.polymarket[0] %}
3119 |                 <div class="pn-poly-hero">
3120 |                     {% if hero.get('event_title') %}
3121 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--pn-gold);margin-bottom:6px;">TOP MARKET</div>
3122 |                     {% endif %}
3123 |                     <div class="pn-poly-question">{{ hero.question }}</div>
3124 |                     <div class="pn-poly-row">
3125 |                         {% if hero.yes_price %}
3126 |                         <span class="pn-poly-pct">{{ hero.yes_price }}%</span>
3127 |                         <span class="pn-poly-yes">YES</span>
3128 |                         {% else %}
3129 |                         <span class="pn-poly-pct" style="color:var(--pn-muted)">--</span>
3130 |                         {% endif %}
3131 |                         <span class="pn-poly-signal {{ hero.btc_signal }}">
3132 |                             {% if hero.btc_signal == 'bullish' %}&#9650;{% elif hero.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
3133 |                             {{ hero.btc_signal|upper }}
3134 |                         </span>
3135 |                     </div>
3136 |                     {% if hero.yes_price %}
3137 |                     <div class="pn-poly-hero-bar">
3138 |                         <div class="pn-poly-hero-bar-fill" style="width:{{ hero.yes_price }}%"></div>
3139 |                     </div>
3140 |                     {% endif %}
3141 |                     <div class="pn-poly-meta">
3142 |                         {% if hero.volume %}<span class="pn-poly-vol-badge">${{ "{:,.0f}".format(hero.volume) }} TOTAL VOL</span>{% endif %}
3143 |                         {% if hero.volume_24h %}<span>${{ "{:,.0f}".format(hero.volume_24h) }} 24h</span>{% endif %}
3144 |                         {% if hero.end_date %}<span>Expires {{ hero.end_date[:10] }}</span>{% endif %}
3145 |                         {% if hero.source_url %}<a href="{{ hero.source_url }}" target="_blank" rel="noopener">Polymarket &rarr;</a>{% endif %}
3146 |                     </div>
3147 |                 </div>
3148 | 
3149 |                 <!-- Remaining markets -->
3150 |                 {% for p in data.polymarket[1:] %}
3151 |                 <div class="pn-poly-item">
3152 |                     <div class="pn-poly-question">{{ p.question }}</div>
3153 |                     <div class="pn-poly-row">
3154 |                         {% if p.yes_price %}
3155 |                         <span class="pn-poly-pct">{{ p.yes_price }}%</span>
3156 |                         <span class="pn-poly-yes">YES</span>
3157 |                         {% else %}
3158 |                         <span class="pn-poly-pct" style="color:var(--pn-muted)">--</span>
3159 |                         {% endif %}
3160 |                         <span class="pn-poly-signal {{ p.btc_signal }}">
3161 |                             {% if p.btc_signal == 'bullish' %}&#9650;{% elif p.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
3162 |                             {{ p.btc_signal|upper }}
3163 |                         </span>
3164 |                     </div>
3165 |                     {% if p.yes_price %}
3166 |                     <div class="pn-poly-bar">
3167 |                         <div class="pn-poly-bar-fill {{ p.btc_signal }}" style="width:{{ p.yes_price }}%"></div>
3168 |                     </div>
3169 |                     {% endif %}
3170 |                     <div class="pn-poly-meta">
3171 |                         {% if p.volume %}<span>${{ "{:,.0f}".format(p.volume) }} vol</span>{% endif %}
3172 |                         {% if p.volume_24h %}<span>${{ "{:,.0f}".format(p.volume_24h) }} 24h</span>{% endif %}
3173 |                         {% if p.end_date %}<span>Expires {{ p.end_date[:10] }}</span>{% endif %}
3174 |                         {% if p.source_url %}<a href="{{ p.source_url }}" target="_blank" rel="noopener">Polymarket &rarr;</a>{% endif %}
3175 |                     </div>
3176 |                 </div>
3177 |                 {% endfor %}
3178 |                 {% else %}
3179 |                 <div class="pn-loading">
3180 |                     <div class="pn-loading-dot"></div>
3181 |                     <div class="pn-loading-dot"></div>
3182 |                     <div class="pn-loading-dot"></div>
3183 |                     Fetching prediction markets...
3184 |                 </div>
3185 |                 {% endif %}
3186 |             </div>
3187 | 
3188 |             <!-- Nation-State / Forex -->
3189 |             {% if data.forex %}
3190 |             <div class="pn-section-label">NATION-STATE SIGNALS</div>
3191 |             <div id="pnForex">
3192 |                 {% for f in data.forex %}
3193 |                 <div class="pn-forex-item">
3194 |                     <span class="pn-forex-pair">{{ f.pair }}</span>
3195 |                     {% if f.rate %}<span class="pn-forex-rate">{{ f.rate }}</span>{% endif %}
3196 |                 </div>
3197 |                 {% endfor %}
3198 |             </div>
3199 |             {% endif %}
3200 | 
3201 |             <!-- Geopolitical Feed -->
3202 |             <div class="pn-section-label">GEOPOLITICAL ALERT FEED</div>
3203 |             <div id="pnGeo">
3204 |                 {% for g in data.geopolitical %}
3205 |                 <div class="pn-geo-item">
3206 |                     <div class="pn-geo-headline">{{ g.headline }}</div>
3207 |                     <span class="pn-geo-signal-tag {{ g.btc_signal }}">
3208 |                         {% if g.btc_signal == 'bullish' %}&#9650;{% elif g.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
3209 |                         BTC {{ g.btc_signal|upper }}
3210 |                     </span>
3211 |                     <div class="pn-geo-rationale">{{ g.btc_rationale }}</div>
3212 |                     <div class="pn-geo-meta">
3213 |                         <span>{{ g.source }}</span>
3214 |                         <span>{{ g.timestamp[:10] if g.timestamp else '' }}</span>
3215 |                     </div>
3216 |                 </div>
3217 |                 {% endfor %}
3218 |                 {% if not data.geopolitical %}
3219 |                 <div class="pn-empty">No geopolitical signals in current window</div>
3220 |                 {% endif %}
3221 |             </div>
3222 | 
3223 |             <!-- Political Donation Pulse -->
3224 |             <div class="pn-section-label">POLITICAL DONATION PULSE</div>
3225 |             <div id="pnDonations" style="padding:12px;">
3226 |                 <div style="color:rgba(255,255,255,0.15);font-size:9px;font-family:'JetBrains Mono',monospace;padding:4px 0;">Loading PAC intelligence...</div>
3227 |             <!-- ═══ PRIVATE EQUITY & INSTITUTIONAL INTELLIGENCE ═══ -->
3228 |             <div class="pn-section-label">INSTITUTIONAL ACCUMULATION</div>
3229 |             <div id="pnInstitutional" style="padding:8px 12px;">
3230 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">
3231 |                     Loading institutional data...
3232 |                 </div>
3233 |             </div>
3234 | 
3235 |             <!-- Coalition Detected Banner (hidden until data loads) -->
3236 |             <div id="pnCoalitionBanner" style="display:none;margin:0 12px 8px;padding:10px 14px;
3237 |                 background:rgba(204,0,0,0.1);border:1px solid rgba(204,0,0,0.4);border-radius:6px;">
3238 |                 <div style="display:flex;align-items:center;gap:8px;">
3239 |                     <div style="width:8px;height:8px;border-radius:50%;background:#cc0000;
3240 |                         animation:pn-pulse 1s ease-in-out infinite;flex-shrink:0;"></div>
3241 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
3242 |                         letter-spacing:.15em;color:#cc0000;font-weight:700;">COALITION SIGNAL DETECTED</div>
3243 |                 </div>
3244 |                 <div id="pnCoalitionNote" style="font-family:'DM Sans',sans-serif;font-size:11px;
3245 |                     color:rgba(255,255,255,0.7);margin-top:6px;line-height:1.5;"></div>
3246 |             </div>
3247 | 
3248 |             <div class="pn-section-label">PRIVATE EQUITY DATASTREAM</div>
3249 |             <div id="pnPEDatastream" style="padding:8px 12px;">
3250 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">
3251 |                     Loading PE fundraising data...
3252 |                 </div>
3253 |             </div>
3254 | 
3255 | 
3256 |             <!-- ═══ BITCOIN BILL GAP TRACKER ═══ -->
3257 |             <div class="pn-section-label" style="display:flex;justify-content:space-between;align-items:center;">
3258 |                 <span>BITCOIN BILL TRACKER</span>
3259 |                 <span style="font-family:'JetBrains Mono',monospace;font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:.08em;">Source: LegiScan · CC BY 4.0</span>
3260 |             </div>
3261 |             <div id="pnBillTracker" style="padding:8px 12px;">
3262 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">Loading congressional bill data...</div>
3263 |             </div>
3264 | 
3265 |             <!-- Congressional Trading — STOCK Act -->
3266 |             <div class="pn-section-label" style="display:flex;justify-content:space-between;align-items:center;"><span>CONGRESSIONAL STOCK TRADES</span><span id="pnLastUpdate" style="font-family:'JetBrains Mono',monospace;font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:.06em;"></span></div>
3267 |             <div id="pnCongress" style="padding:8px 12px;">
3268 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Loading STOCK Act filings...</div>
3269 |             </div>
3270 | 
3271 |             <!-- Party Breakdown -->
3272 |             <div class="pn-section-label">PARTY TRADING BREAKDOWN</div>
3273 |             <div id="pnPartyBreakdown" style="padding:8px 12px;">
3274 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Analyzing party patterns...</div>
3275 |             </div>
3276 | 
3277 |             <!-- IHX Score -->
3278 |             <div class="pn-section-label">INSIDER HEAT INDEX (IHX)</div>
3279 |             <div id="pnIHX" style="padding:12px;">
3280 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Computing insider heat...</div>
3281 |             </div>
3282 | 
3283 |                     </div>
3284 |                     <div>
3285 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;color:var(--pn-white);" id="donCommittees">--</div>
3286 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--pn-muted);margin-top:4px;">CRYPTO COMMITTEES</div>
3287 |                     </div>
3288 |                     <div>
3289 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;color:var(--pn-gold);" id="donStates">--</div>
3290 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--pn-muted);margin-top:4px;">STATES ACTIVE</div>
3291 |                     </div>
3292 |                 </div>
3293 |                 <div style="margin-top:12px;text-align:center;">
3294 |                     <span id="donLabel" style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:2px;padding:4px 12px;border:1px solid var(--pn-border);background:rgba(255,59,95,0.04);color:var(--pn-muted);">LOADING</span>
3295 |                 </div>
3296 |             </div>
3297 |         </div>
3298 |         </div><!-- end .pn-right-rail -->
3299 | 
3300 |     </div>
3301 | </div>
3302 | 
3303 | 
3304 | 
3305 | 
3306 | <!-- ═══ HISTORICAL PRECEDENTS TIMELINE (GLASSMORPHIC) ═══ -->
3307 | <div class="pn-history">
3308 |     <div class="pn-history-header">HISTORICAL PRECEDENTS</div>
3309 |     <div class="pn-history-subhead">Documented cases of government financial overreach — the pattern Bitcoin was engineered to break.</div>
3310 | 
3311 |     <div class="pn-timeline-scroll">
3312 |         <div class="pn-timeline" id="pn-timeline">
3313 | 
3314 |             <!-- 1: 60 AD — Roman Coin Debasement (ABOVE) -->
3315 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3316 |                 <div class="pn-tl-year">60 AD</div>
3317 |                 <div class="pn-tl-name">Roman Coin Debasement</div>
3318 |                 <div class="pn-tl-stem"></div>
3319 |                 <div class="pn-tl-dot" data-evt="0" onclick="tlToggle(this)"></div>
3320 |             </div>
3321 | 
3322 |             <!-- 2: 1544 — Henry VIII (BELOW) -->
3323 |             <div class="pn-tl-node tl-below" style="margin-right:40px">
3324 |                 <div class="pn-tl-dot" data-evt="1" onclick="tlToggle(this)"></div>
3325 |                 <div class="pn-tl-stem"></div>
3326 |                 <div class="pn-tl-year">1544</div>
3327 |                 <div class="pn-tl-name">Henry VIII Great Debasement</div>
3328 |             </div>
3329 | 
3330 |             <!-- 3: 1789 — French Assignats (ABOVE) -->
3331 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3332 |                 <div class="pn-tl-year">1789</div>
3333 |                 <div class="pn-tl-name">French Assignat Hyperinflation</div>
3334 |                 <div class="pn-tl-stem"></div>
3335 |                 <div class="pn-tl-dot" data-evt="2" onclick="tlToggle(this)"></div>
3336 |             </div>
3337 | 
3338 |             <!-- 4: 1921 — Weimar (BELOW) -->
3339 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3340 |                 <div class="pn-tl-dot" data-evt="3" onclick="tlToggle(this)"></div>
3341 |                 <div class="pn-tl-stem"></div>
3342 |                 <div class="pn-tl-year">1921</div>
3343 |                 <div class="pn-tl-name">Weimar Hyperinflation</div>
3344 |             </div>
3345 | 
3346 |             <!-- 5: 1933 — FDR Gold Seizure (ABOVE) -->
3347 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3348 |                 <div class="pn-tl-year">1933</div>
3349 |                 <div class="pn-tl-name">FDR Gold Seizure</div>
3350 |                 <div class="pn-tl-stem"></div>
3351 |                 <div class="pn-tl-dot" data-evt="4" onclick="tlToggle(this)"></div>
3352 |             </div>
3353 | 
3354 |             <!-- 6: 1944 — Bretton Woods (BELOW) -->
3355 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3356 |                 <div class="pn-tl-dot" data-evt="5" onclick="tlToggle(this)"></div>
3357 |                 <div class="pn-tl-stem"></div>
3358 |                 <div class="pn-tl-year">1944</div>
3359 |                 <div class="pn-tl-name">Bretton Woods Dollar Peg</div>
3360 |             </div>
3361 | 
3362 |             <!-- 7: 1946 — Hungary (ABOVE) -->
3363 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3364 |                 <div class="pn-tl-year">1946</div>
3365 |                 <div class="pn-tl-name">Hungarian Hyperinflation</div>
3366 |                 <div class="pn-tl-stem"></div>
3367 |                 <div class="pn-tl-dot" data-evt="6" onclick="tlToggle(this)"></div>
3368 |             </div>
3369 | 
3370 |             <!-- 8: 1971 — Nixon Shock (BELOW) -->
3371 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3372 |                 <div class="pn-tl-dot" data-evt="7" onclick="tlToggle(this)"></div>
3373 |                 <div class="pn-tl-stem"></div>
3374 |                 <div class="pn-tl-year">1971</div>
3375 |                 <div class="pn-tl-name">Nixon Shock</div>
3376 |             </div>
3377 | 
3378 |             <!-- 9: 1980s — S&L Crisis (ABOVE) -->
3379 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3380 |                 <div class="pn-tl-year">1980s</div>
3381 |                 <div class="pn-tl-name">S&amp;L Crisis</div>
3382 |                 <div class="pn-tl-stem"></div>
3383 |                 <div class="pn-tl-dot" data-evt="8" onclick="tlToggle(this)"></div>
3384 |             </div>
3385 | 
3386 |             <!-- 10: 2001 — Argentina (BELOW) -->
3387 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3388 |                 <div class="pn-tl-dot" data-evt="9" onclick="tlToggle(this)"></div>
3389 |                 <div class="pn-tl-stem"></div>
3390 |                 <div class="pn-tl-year">2001</div>
3391 |                 <div class="pn-tl-name">Argentina Corralito</div>
3392 |             </div>
3393 | 
3394 |             <!-- 11: 2008 — GFC Bailouts (ABOVE) -->
3395 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3396 |                 <div class="pn-tl-year">2008</div>
3397 |                 <div class="pn-tl-name">Global Financial Crisis</div>
3398 |                 <div class="pn-tl-stem"></div>
3399 |                 <div class="pn-tl-dot" data-evt="10" onclick="tlToggle(this)"></div>
3400 |             </div>
3401 | 
3402 |             <!-- 12: 2013 — Cyprus (BELOW) -->
3403 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3404 |                 <div class="pn-tl-dot" data-evt="11" onclick="tlToggle(this)"></div>
3405 |                 <div class="pn-tl-stem"></div>
3406 |                 <div class="pn-tl-year">2013</div>
3407 |                 <div class="pn-tl-name">Cyprus Bail-In</div>
3408 |             </div>
3409 | 
3410 |             <!-- 13: 2016 — India (ABOVE) -->
3411 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3412 |                 <div class="pn-tl-year">2016</div>
3413 |                 <div class="pn-tl-name">India Demonetization</div>
3414 |                 <div class="pn-tl-stem"></div>
3415 |                 <div class="pn-tl-dot" data-evt="12" onclick="tlToggle(this)"></div>
3416 |             </div>
3417 | 
3418 |             <!-- 14: 2020 — COVID (BELOW) -->
3419 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3420 |                 <div class="pn-tl-dot" data-evt="13" onclick="tlToggle(this)"></div>
3421 |                 <div class="pn-tl-stem"></div>
3422 |                 <div class="pn-tl-year">2020</div>
3423 |                 <div class="pn-tl-name">COVID Money Printing</div>
3424 |             </div>
3425 | 
3426 |             <!-- 15: 2022 — Russia SWIFT (ABOVE) -->
3427 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3428 |                 <div class="pn-tl-year">2022</div>
3429 |                 <div class="pn-tl-name">Russia SWIFT Exclusion</div>
3430 |                 <div class="pn-tl-stem"></div>
3431 |                 <div class="pn-tl-dot" data-evt="14" onclick="tlToggle(this)"></div>
3432 |             </div>
3433 | 
3434 |             <!-- 16: 2022 — Canada Truckers (BELOW) -->
3435 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3436 |                 <div class="pn-tl-dot" data-evt="15" onclick="tlToggle(this)"></div>
3437 |                 <div class="pn-tl-stem"></div>
3438 |                 <div class="pn-tl-year">2022</div>
3439 |                 <div class="pn-tl-name">Canada Trucker Freeze</div>
3440 |             </div>
3441 | 
3442 |             <!-- 17: 2023 — US Banking (ABOVE) -->
3443 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3444 |                 <div class="pn-tl-year">2023</div>
3445 |                 <div class="pn-tl-name">U.S. Banking Crisis</div>
3446 |                 <div class="pn-tl-stem"></div>
3447 |                 <div class="pn-tl-dot" data-evt="16" onclick="tlToggle(this)"></div>
3448 |             </div>
3449 | 
3450 |             <!-- 18: NOW — CBDC (BELOW) -->
3451 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3452 |                 <div class="pn-tl-dot" data-evt="17" onclick="tlToggle(this)"></div>
3453 |                 <div class="pn-tl-stem"></div>
3454 |                 <div class="pn-tl-year">NOW</div>
3455 |                 <div class="pn-tl-name">CBDC Push</div>
3456 |             </div>
3457 | 
3458 |         </div>
3459 |     </div>
3460 | 
3461 |     <div class="pn-history-coda">
3462 |         WHY HISTORY MATTERS — These are not conspiracy theories. These are documented events. Bitcoin was built to prevent them.
3463 |     </div>
3464 | </div>
3465 | 
3466 | <!-- Glassmorphic info card (single, repositioned on click) -->
3467 | <div class="pn-tl-card" id="pn-tl-card">
3468 |     <button class="pn-tl-card-close" onclick="tlClose()">&times;</button>
3469 |     <div class="pn-tl-card-header" id="tlCardHeader"></div>
3470 |     <div class="pn-tl-card-short" id="tlCardShort"></div>
3471 |     <div class="pn-tl-card-detail" id="tlCardDetail"></div>
3472 |     <div class="pn-tl-card-btc" id="tlCardBtc"></div>
3473 | </div>
3474 | 
3475 | <script>
3476 | (function(){
3477 | var TL_EVENTS=[
3478 | {year:"60 AD",title:"Roman Coin Debasement",short:"Nero reduces silver content from 90% to near 0% over centuries. Denarius becomes copper-clad.",detail:"Roman emperors starting with Nero systematically reduced silver content in the denarius from ~90% to under 5% to fund wars and government spending. By the Crisis of the Third Century (235\u2013284 AD), 26 emperors ruled in 49 years as the currency collapsed and hyperinflation took hold. The pattern: spend beyond means, debase the money, watch civilization fracture.",btc:"\u26a1 BITCOIN PARALLEL: 21 million coins. No emperor can change that."},
3479 | {year:"1544",title:"Henry VIII Great Debasement",short:"England\u2019s king secretly reduces gold/silver in coins to fund wars. Coins dubbed \u2018Old Coppernose.\u2019",detail:"King Henry VIII reduced gold content from 23 to 20 karat and silver content to just 25% (rest copper) to fund wars with France and Scotland and his lifestyle. Citizens noticed when the copper showed through the silver on the king\u2019s portrait \u2014 the nose turned copper first. Result: Severe inflation, erosion of trust, economic damage lasting decades until reversed by Elizabeth I in 1560.",btc:"\u26a1 BITCOIN PARALLEL: Cryptographically verified. No hidden copper."},
3480 | {year:"1789",title:"French Assignat Hyperinflation",short:"Revolutionary France prints paper money backed by seized church land. Massive over-issue destroys savings.",detail:"The revolutionary government issued paper \u2018assignats\u2019 backed by confiscated church lands, then printed them without restraint to fund wars and deficits. Total issuance: 45 billion livres. Result: Hyperinflation wiped out the middle class, triggered food riots, and contributed to the Reign of Terror. The paper money became so worthless it was burned for heat.",btc:"\u26a1 BITCOIN PARALLEL: Cannot be printed. Supply is fixed at genesis."},
3481 | {year:"1921",title:"Weimar Republic Hyperinflation",short:"Germany prints trillions of marks to pay WWI reparations. A loaf of bread costs 200 billion marks by 1923.",detail:"The German government printed money to pay WWI war reparations imposed by the Treaty of Versailles. By November 1923, a single loaf of bread cost 200 billion marks. Citizens carried cash in wheelbarrows. Middle-class savings were completely destroyed. The resulting economic chaos and resentment directly enabled the rise of extremism. The Reichsbank printed notes so fast new denominations were issued daily.",btc:"\u26a1 BITCOIN PARALLEL: No central bank. No war reparations. 21 million."},
3482 | {year:"1933",title:"FDR Gold Seizure",short:"Executive Order 6102 forces citizens to surrender gold. Penalty: 10 years prison or $10,000 fine.",detail:"President Roosevelt signed Executive Order 6102 requiring all U.S. persons to deliver their gold coins, bullion, and certificates to Federal Reserve banks at $20.67/oz. Days later, the government revalued gold to $35/oz \u2014 an immediate 41% wealth transfer from citizens to the state. Noncompliance carried criminal penalties of up to 10 years imprisonment. This was not a purchase \u2014 it was confiscation.",btc:"\u26a1 BITCOIN PARALLEL: Stored in your head as 12 words. No EO can seize a seed phrase."},
3483 | {year:"1944",title:"Bretton Woods Dollar Peg",short:"USD becomes global reserve currency backed by gold. Seeds Nixon Shock 27 years later.",detail:"44 nations signed the Bretton Woods Agreement making the USD the world reserve currency pegged at $35/oz gold. The U.S. promised to maintain convertibility. For 27 years, the system worked \u2014 until the U.S. printed more dollars than it had gold to back them, setting the stage for Nixon\u2019s 1971 unilateral break.",btc:"\u26a1 BITCOIN PARALLEL: No central peg. No promise of convertibility. It just works."},
3484 | {year:"1946",title:"Hungarian Hyperinflation",short:"Worst hyperinflation in recorded history. Prices doubled every 15 hours. Currency abandoned entirely.",detail:"Post-WWII Hungary experienced the most extreme hyperinflation ever recorded. The Hungarian peng\u0151 lost all value \u2014 at peak, prices doubled every 15.6 hours. The government printed a 100 quintillion peng\u0151 note. Total currency abandoned. A new currency (forint) was introduced, but savings were destroyed absolutely. Workers were paid daily and ran to spend before prices doubled again.",btc:"\u26a1 BITCOIN PARALLEL: Cannot be inflated. Ever."},
3485 | {year:"1971",title:"Nixon Shock",short:"Nixon ends gold convertibility \u2018temporarily.\u2019 54 years later, still temporary.",detail:"On August 15, 1971, President Nixon unilaterally terminated USD convertibility to gold, ending the Bretton Woods system. He called it \u2018temporary.\u2019 Every dollar since has been backed only by government debt. The result: USD has lost 85%+ of its purchasing power since 1971. The move enabled unlimited government spending backed by nothing but future tax obligations and the threat of military force.",btc:"\u26a1 BITCOIN PARALLEL: Born the day Satoshi embedded the bank bailout headline in the genesis block."},
3486 | {year:"1980s",title:"U.S. Savings & Loan Crisis",short:"1,000+ S&Ls fail after deregulation. $160 billion taxpayer bailout. First major \u2018too big to fail.\u2019",detail:"Deregulation of the savings and loan industry combined with government-backed deposit insurance led to reckless lending and outright fraud at over 1,000 institutions. When they failed, taxpayers were forced to cover losses of $124\u2013160 billion. The S&L crisis established the template: privatize profits, socialize losses. Executives faced minimal consequences.",btc:"\u26a1 BITCOIN PARALLEL: No deposit insurance needed. Not your keys, not your coins \u2014 but if it is your keys, no bailout required."},
3487 | {year:"2001",title:"Argentina Corralito",short:"Bank accounts frozen. USD deposits forcibly converted to devalued pesos. Riots in the streets.",detail:"After pegging the peso to the USD, Argentina\u2019s government froze all bank accounts (the \u2018corralito\u2019) limiting withdrawals to $250/week. When the peg broke, USD deposits were forcibly converted to pesos at a rate that immediately lost 70% of value \u2014 wiping out savings overnight. Multiple presidents resigned in weeks. Riots killed dozens. Argentina defaulted on $100 billion in debt.",btc:"\u26a1 BITCOIN PARALLEL: Your wallet. Your keys. No bank holiday can freeze a UTXO."},
3488 | {year:"2008",title:"Global Financial Crisis Bailouts",short:"TARP: $700B. Total Fed backstop: $29 trillion. Banks rescued. Homeowners foreclosed.",detail:"The U.S. government passed TARP ($700B+) and the Federal Reserve provided up to $29 trillion in emergency backstops to rescue banks, AIG, Fannie Mae, Freddie Mac, and the auto industry after the subprime mortgage collapse. While institutions deemed \u2018too big to fail\u2019 were rescued, 10 million Americans lost their homes to foreclosure. The genesis block of Bitcoin was mined January 3, 2009 \u2014 with a newspaper headline about bank bailouts embedded as a timestamp.",btc:"\u26a1 BITCOIN PARALLEL: The genesis block timestamp: \u2018Chancellor on brink of second bailout for banks.\u2019 Satoshi saw this coming."},
3489 | {year:"2013",title:"Cyprus Bail-In",short:"EU forces haircut of 47.5% on deposits over \u20ac100,000. First direct bank account confiscation in modern Europe.",detail:"The European Union forced Cyprus to impose a \u2018bail-in\u2019 as a condition of a \u20ac10B rescue \u2014 directly seizing up to 47.5% of bank deposits over \u20ac100,000. This was the first time in modern history that EU governments explicitly took depositor money to rescue a bank. It established the legal template that deposits are not cash \u2014 they are unsecured loans to the bank.",btc:"\u26a1 BITCOIN PARALLEL: People who held BTC were not subject to the bail-in."},
3490 | {year:"2016",title:"India Demonetization",short:"86% of all currency invalidated overnight. Chaos, queues, economic disruption. Affected 1.3 billion people.",detail:"Indian Prime Minister Modi announced with 4 hours notice that \u20b9500 and \u20b91,000 notes \u2014 86% of all currency in circulation \u2014 were immediately invalid. Citizens had weeks to exchange limited amounts. Result: Cash chaos, severe disruption to the informal economy (which employs 90% of Indians), GDP growth slowed, and the stated goal of eliminating \u2018black money\u2019 largely failed. The demonetization affected 1.3 billion people with near-zero time to prepare.",btc:"\u26a1 BITCOIN PARALLEL: A Bitcoin private key cannot be demonetized by government decree."},
3491 | {year:"2020",title:"COVID Money Printing",short:"$5\u20136 trillion U.S. stimulus + Fed balance sheet to $9T. Highest inflation in 40 years follows.",detail:"The U.S. government passed ~$5\u20136 trillion in fiscal stimulus packages (CARES Act, American Rescue Plan, etc.) while the Federal Reserve doubled its balance sheet from $4T to $9T through quantitative easing. The result: 9.1% inflation in June 2022 \u2014 the highest in 40 years. Purchasing power of savings eroded. Asset owners saw portfolios surge while wage earners fell behind. The Cantillon effect: those closest to the money printer benefit first.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin supply did not change. 21 million. The halving in May 2020 reduced new issuance. Bitcoiners called it."},
3492 | {year:"2022",title:"Russia SWIFT Exclusion",short:"$300B in sovereign reserves frozen. Proof that nation-state assets are weapons.",detail:"Following Russia\u2019s invasion of Ukraine, Western nations froze approximately $300 billion in Russian central bank reserves held in Western financial institutions. This demonstrated that sovereign wealth \u2014 money a country legally owns \u2014 can be weaponized by adversaries with institutional access. No court order, no due process. Every central bank in the world took note.",btc:"\u26a1 BITCOIN PARALLEL: Censorship-resistant by design. No counterparty holds your sats."},
3493 | {year:"2022",title:"Canada Trucker Freeze",short:"Bank accounts frozen without court order. Protesters financially silenced in 48 hours.",detail:"The Canadian government invoked the Emergencies Act to freeze bank accounts of Freedom Convoy protesters and donors without court orders. Financial institutions were directed to freeze accounts based on government lists. Accounts were blocked within 48 hours of the declaration. A peaceful protest was financially neutralized. The act was later found to have been applied unlawfully by a Federal Court, but the damage was done.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin transactions cannot be stopped. A node in your home means no one can freeze your economic activity."},
3494 | {year:"2023",title:"U.S. Banking Crisis",short:"SVB, Signature, Silvergate collapse. Crypto-friendly banks systematically shut down \u2014 Operation Chokepoint 2.0.",detail:"Silicon Valley Bank ($212B), Signature Bank ($110B), and Silvergate Bank collapsed in rapid succession. SVB\u2019s failure was partly triggered by the Fed\u2019s rate hiking cycle destroying its bond portfolio. Signature and Silvergate \u2014 both crypto-friendly banks \u2014 were also shut down by regulators. Critics and a Congressional investigation documented \u2018Operation Chokepoint 2.0\u2019: a coordinated effort to deny banking services to crypto businesses.",btc:"\u26a1 BITCOIN PARALLEL: A bank that cannot be closed. Runs 24/7/365. No bank holiday."},
3495 | {year:"NOW",title:"CBDC Push",short:"130+ countries developing programmable digital currencies. Expiry dates. Spending restrictions. Surveillance.",detail:"As of 2026, 130+ countries (representing 98% of global GDP) are developing or piloting Central Bank Digital Currencies. Unlike cash, CBDCs are programmable: governments can set expiry dates (spend it or lose it), restrict what categories of goods can be purchased, tie spending to social credit scores, and surveil every transaction in real time. China\u2019s digital yuan has already been deployed with regional spending restrictions.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin is the opt-out. Permissionless. Unseizable. 21 million. Forever."}
3496 | ];
3497 | var openDot=null,card=document.getElementById('pn-tl-card');
3498 | function tlToggle(dot){
3499 |     var idx=parseInt(dot.dataset.evt),e=TL_EVENTS[idx];
3500 |     if(openDot===dot){tlClose();return;}
3501 |     if(openDot)openDot.classList.remove('active');
3502 |     dot.classList.add('active');
3503 |     openDot=dot;
3504 |     document.getElementById('tlCardHeader').textContent=e.year+' \u2014 '+e.title;
3505 |     document.getElementById('tlCardShort').textContent=e.short;
3506 |     document.getElementById('tlCardDetail').textContent=e.detail;
3507 |     document.getElementById('tlCardBtc').textContent=e.btc;
3508 |     /* Position card near the dot */
3509 |     var r=dot.getBoundingClientRect(),cw=340;
3510 |     card.style.visibility='hidden';card.style.display='block';
3511 |     var ch=card.offsetHeight||300;
3512 |     card.style.visibility='';card.style.display='';
3513 |     var left=r.left+r.width/2-cw/2;
3514 |     var top=r.top+window.scrollY-ch-16;
3515 |     if(dot.closest('.tl-below'))top=r.bottom+window.scrollY+12;
3516 |     if(left<8)left=8;
3517 |     if(left+cw>window.innerWidth-8)left=window.innerWidth-cw-8;
3518 |     if(top<8)top=r.bottom+window.scrollY+12;
3519 |     card.style.left=left+'px';card.style.top=top+'px';
3520 |     card.classList.add('active');
3521 | }
3522 | function tlClose(){
3523 |     card.classList.remove('active');
3524 |     if(openDot){openDot.classList.remove('active');openDot=null;}
3525 | }
3526 | window.tlToggle=tlToggle;window.tlClose=tlClose;
3527 | /* Close on click outside */
3528 | document.addEventListener('click',function(ev){
3529 |     if(!ev.target.closest('.pn-tl-dot')&&!ev.target.closest('.pn-tl-card'))tlClose();
3530 | });
3531 | /* Close on scroll */
3532 | var scr=document.querySelector('.pn-timeline-scroll');
3533 | if(scr)scr.addEventListener('scroll',tlClose);
3534 | })();
3535 | </script>
3536 | 
3537 | <!-- ═══ DISCLAIMER ═══ -->
3538 | <div class="pn-disclaimer">
3539 |     All data sourced from public filings (STOCK Act, SEC EDGAR), public blockchain explorers (mempool.space), and open APIs.
3540 |     Correlation shown for independent research purposes only. Protocol Pulse does not make accusations of insider trading.
3541 |     "FLAGGED" items are statistical patterns, not verified misconduct. Always consult original sources.
3542 |     <strong>This is not financial, investment, or legal advice.</strong> Nothing on this dashboard constitutes a recommendation to buy, sell, or hold any asset.
3543 |     All information is provided for educational and research purposes only.
3544 | </div>
3545 | 
3546 | {% endblock %}
3547 | 
3548 | {% block scripts %}
3549 | <script>
3550 | (function() {
3551 |     // ── UTC Clock ──
3552 |     function updateClock() {
3553 |         var now = new Date();
3554 |         var h = String(now.getUTCHours()).padStart(2, '0');
3555 |         var m = String(now.getUTCMinutes()).padStart(2, '0');
3556 |         var s = String(now.getUTCSeconds()).padStart(2, '0');
3557 |         var el = document.getElementById('pnClock');
3558 |         if (el) el.textContent = h + ':' + m + ':' + s + ' UTC';
3559 |     }
3560 |     updateClock();
3561 |     setInterval(updateClock, 1000);
3562 | 
3563 |     // ── Whale Tracker: fetch from /api/orb (works for all users) ──
3564 |     (function() {
3565 |         var el = document.getElementById('pnWhales');
3566 |         if (!el) return;
3567 |         function loadWhales() {
3568 |             fetch('/api/orb')
3569 |                 .then(function(r) { return r.json(); })
3570 |                 .then(function(d) {
3571 |                     var raw = d.raw || {};
3572 |                     var whales = raw.whale_alerts_list || [];
3573 |                     if (!whales.length) {
3574 |                         el.innerHTML = '<div class="pn-empty">No whale activity detected</div>';
3575 |                         return;
3576 |                     }
3577 |                     var html = '';
3578 |                     whales.slice(0, 5).forEach(function(w) {
3579 |                         var tierCol = w.tier === 'CRITICAL' ? '#ef4444' : (w.tier === 'WARNING' ? '#f97316' : 'var(--pn-muted)');
3580 |                         var isInflow = (w.message || '').toLowerCase().indexOf('inflow') >= 0;
3581 |                         var flowClass = isInflow ? 'inflow' : 'outflow';
3582 |                         html += '<div class="pn-whale-item ' + flowClass + '">';
3583 |                         html += '<div class="pn-whale-row">';
3584 |                         html += '<div class="pn-whale-entity" style="color:' + tierCol + ';font-weight:700;font-size:9px;letter-spacing:1px;">' + (w.tier || 'NOTE') + '</div>';
3585 |                         html += '</div>';
3586 |                         html += '<div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">' + (w.message || '') + '</div>';
3587 |                         html += '<div class="pn-whale-meta"><span style="color:var(--pn-muted);font-size:10px;">Score: ' + (w.score || 0) + '</span></div>';
3588 |                         html += '</div>';
3589 |                     });
3590 |                     el.innerHTML = html;
3591 |                     var c = document.getElementById('pnStatWhales');
3592 |                     if (c) c.textContent = whales.length;
3593 |                 })
3594 |                 .catch(function() {});
3595 |         }
3596 |         loadWhales();
3597 |         var _whaleInterval = setInterval(loadWhales, 60000);
3598 |         window.addEventListener('beforeunload', function(){ clearInterval(_whaleInterval); });
3599 |     })();
3600 | 
3601 |     // ── Political Donation Pulse (rebuilt) ──
3602 |     (function() {
3603 |         fetch('/api/donations/pulse')
3604 |             .then(function(r) { return r.json(); })
3605 |             .then(function(d) {
3606 |                 var el = document.getElementById('pnDonations');
3607 |                 if (!el) return;
3608 | 
3609 |                 var score    = d.score || 0;
3610 |                 var label    = d.label || 'LOW';
3611 |                 var spend    = d.fairshake_spend || 0;
3612 |                 var nComm    = d.crypto_committees || 0;
3613 |                 var nStates  = d.states_active || 0;
3614 |                 var exps     = d.fairshake_expenditures || [];
3615 |                 var topDons  = d.top_donations || [];
3616 |                 var scoreCol = score > 70 ? '#CC0000' : score > 40 ? '#f8c15c' : 'rgba(255,255,255,0.3)';
3617 |                 var spendFmt = spend >= 1e6 ? '$' + (spend/1e6).toFixed(1) + 'M'
3618 |                              : spend >= 1e3 ? '$' + (spend/1e3).toFixed(0) + 'K' : '$0';
3619 | 
3620 |                 var html = '<div style="display:flex;gap:12px;margin-bottom:10px;align-items:flex-start;">';
3621 | 
3622 |                 // Pulse score
3623 |                 html += '<div style="text-align:center;min-width:64px;">'
3624 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:28px;font-weight:900;color:' + scoreCol + ';">' + score + '</div>'
3625 |                       + '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.3);margin-top:2px;">PULSE SCORE</div>'
3626 |                       + '</div>';
3627 | 
3628 |                 // Stats
3629 |                 html += '<div style="display:flex;flex-direction:column;gap:6px;flex:1;">';
3630 |                 html += '<div style="display:flex;gap:16px;">';
3631 |                 html += '<div style="text-align:center;">'
3632 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:#f8c15c;">' + spendFmt + '</div>'
3633 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">FAIRSHAKE SPEND</div>'
3634 |                       + '</div>';
3635 |                 html += '<div style="text-align:center;">'
3636 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:rgba(255,255,255,0.7);">' + nComm + '</div>'
3637 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">CRYPTO PACs</div>'
3638 |                       + '</div>';
3639 |                 html += '<div style="text-align:center;">'
3640 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:rgba(255,255,255,0.7);">' + nStates + '</div>'
3641 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">STATES ACTIVE</div>'
3642 |                       + '</div>';
3643 |                 html += '</div>'; // stats row
3644 |                 html += '</div></div>'; // right col + header
3645 | 
3646 |                 // Fairshake expenditures
3647 |                 if (exps.length) {
3648 |                     html += '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.25);margin-bottom:4px;">FAIRSHAKE PAC — INDEPENDENT EXPENDITURES</div>';
3649 |                     exps.slice(0,4).forEach(function(e) {
3650 |                         var amtFmt = e.amount >= 1e6 ? '$'+(e.amount/1e6).toFixed(1)+'M'
3651 |                                    : e.amount >= 1e3 ? '$'+(e.amount/1e3).toFixed(0)+'K'
3652 |                                    : '$'+e.amount;
3653 |                         var suppCol = e.support === 'S' ? '#22c55e' : '#ef4444';
3654 |                         var suppTxt = e.support === 'S' ? 'SUPPORT' : 'OPPOSE';
3655 |                         html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3656 |                               + '<div>'
3657 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:rgba(255,255,255,0.8);">' + (e.candidate||'?').substring(0,28) + '</span>'
3658 |                               + '<span style="font-size:7px;color:' + suppCol + ';margin-left:6px;border:1px solid '+suppCol+';padding:1px 4px;border-radius:2px;">' + suppTxt + '</span>'
3659 |                               + '</div>'
3660 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:#f8c15c;">' + amtFmt + '</span>'
3661 |                               + '</div>';
3662 |                     });
3663 |                 }
3664 | 
3665 |                 // Top donations
3666 |                 if (topDons.length) {
3667 |                     html += '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.25);margin:8px 0 4px;">TOP INDIVIDUAL DONATIONS TO CRYPTO PACs</div>';
3668 |                     topDons.slice(0,4).forEach(function(d2) {
3669 |                         var amtFmt = d2.amount >= 1e6 ? '$'+(d2.amount/1e6).toFixed(1)+'M'
3670 |                                    : d2.amount >= 1e3 ? '$'+(d2.amount/1e3).toFixed(0)+'K'
3671 |                                    : '$'+d2.amount;
3672 |                         var loc = d2.city ? d2.city + ', ' + d2.state : d2.state || '';
3673 |                         html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3674 |                               + '<div>'
3675 |                               + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:rgba(255,255,255,0.8);">' + (d2.donor||'Anonymous').substring(0,26) + '</div>'
3676 |                               + '<div style="font-size:7px;color:rgba(255,255,255,0.3);">' + loc + (d2.employer ? ' · ' + d2.employer.substring(0,20) : '') + '</div>'
3677 |                               + '</div>'
3678 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:#CC0000;">' + amtFmt + '</span>'
3679 |                               + '</div>';
3680 |                     });
3681 |                 }
3682 | 
3683 |                 if (!exps.length && !topDons.length) {
3684 |                     html += '<div style="color:rgba(255,255,255,0.2);font-size:9px;font-family:\'JetBrains Mono\',monospace;margin-top:8px;">'
3685 |                           + (d.key_type === 'demo' ? 'Add OPENFEC_API_KEY to .env for live data' : 'No recent expenditure data')
3686 |                           + '</div>';
3687 |                 }
3688 | 
3689 |                 html += '<div style="font-size:7px;color:rgba(255,255,255,0.1);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: OpenFEC Public API · FEC.gov</div>';
3690 |                 el.innerHTML = html;
3691 |             })
3692 |             .catch(function(err) {
3693 |                 var el = document.getElementById('pnDonations');
3694 |                 if (el) el.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:9px;font-family:\'JetBrains Mono\',monospace;">Donation data unavailable</div>';
3695 |             });
3696 |     })();
3697 | 
3698 | 
3699 |     {% if not demo_mode %}
3700 |     // ── Make the Bitcoin Case (typewriter 18ms/char, gold cursor) ──
3701 |     var _btcCaseCooldown = false;
3702 |     window.makeBitcoinCase = function(btn, eventSummary) {
3703 |         var idx = btn.getAttribute('data-idx');
3704 |         var outputEl = document.getElementById('btcCase' + idx);
3705 |         if (!outputEl) return;
3706 | 
3707 |         // Rate limit: 5s cooldown between requests
3708 |         if (_btcCaseCooldown) return;
3709 |         _btcCaseCooldown = true;
3710 |         setTimeout(function(){ _btcCaseCooldown = false; }, 5000);
3711 | 
3712 |         btn.disabled = true;
3713 |         btn.textContent = 'GENERATING...';
3714 |         outputEl.innerHTML = '';
3715 |         outputEl.classList.add('visible');
3716 | 
3717 |         fetch('/api/panopticon/make-bitcoin-case', {
3718 |             method: 'POST',
3719 |             headers: {'Content-Type': 'application/json'},
3720 |             body: JSON.stringify({event_summary: eventSummary})
3721 |         })
3722 |         .then(function(r) { return r.json(); })
3723 |         .then(function(data) {
3724 |             if (data.error) {
3725 |                 outputEl.innerHTML = '<span style="color:var(--pn-red)">' + data.error + '</span>';
3726 |                 btn.disabled = false;
3727 |                 btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
3728 |                 return;
3729 |             }
3730 |             var text = data.case_text || '';
3731 |             var model = data.model || '';
3732 |             outputEl.innerHTML = '<div class="pn-btc-case-label">THE BITCOIN CASE</div><span id="typewriter' + idx + '"></span><span class="pn-typewriter-cursor"></span>';
3733 |             var twEl = document.getElementById('typewriter' + idx);
3734 |             var i = 0;
3735 |             function typeChar() {
3736 |                 if (i < text.length) {
3737 |                     twEl.textContent += text.charAt(i);
3738 |                     i++;
3739 |                     setTimeout(typeChar, 18 + Math.random() * 12);
3740 |                 } else {
3741 |                     var cursor = outputEl.querySelector('.pn-typewriter-cursor');
3742 |                     if (cursor) cursor.remove();
3743 |                     outputEl.innerHTML += '<div class="pn-btc-case-model">Model: ' + model + '</div>';
3744 |                     btn.disabled = false;
3745 |                     btn.innerHTML = '&#x20BF; Regenerate Case';
3746 |                 }
3747 |             }
3748 |             typeChar();
3749 |         })
3750 |         .catch(function() {
3751 |             outputEl.innerHTML = '<span style="color:var(--pn-red)">Failed to generate. Try again.</span>';
3752 |             btn.disabled = false;
3753 |             btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
3754 |         });
3755 |     };
3756 | 
3757 |     // ── Auto-refresh every 5 minutes ──
3758 |     function refreshData() {
3759 |         fetch('/api/panopticon/whale-alerts')
3760 |             .then(function(r) { return r.json(); })
3761 |             .then(function(data) {
3762 |                 if (data.alerts && data.alerts.length > 0) {
3763 |                     var c = document.getElementById('pnStatWhales');
3764 |                     if (c) c.textContent = data.alerts.length;
3765 |                 }
3766 |             })
3767 |             .catch(function() {});
3768 | 
3769 |         fetch('/api/panopticon/geopolitical')
3770 |             .then(function(r) { return r.json(); })
3771 |             .then(function(data) {
3772 |                 if (data.geopolitical) {
3773 |                     var c = document.getElementById('pnStatGeo');
3774 |                     if (c) c.textContent = data.geopolitical.length;
3775 |                 }
3776 |             })
3777 |             .catch(function() {});
3778 |     }
3779 |     var _refreshDataInterval = setInterval(refreshData, 300000);
3780 |     window.addEventListener('beforeunload', function(){ clearInterval(_refreshDataInterval); });
3781 |     {% endif %}
3782 | })();
3783 | 
3784 | 
3785 | /* ═══ CONGRESSIONAL TRADING ═══ */
3786 | (function(){
3787 |   // Helper: reuse liveData cache from SS2 fetchAll() if available, else fetch once
3788 |   var liveData = window._pnLiveData || {};
3789 |   function getCachedOrFetch(key, url) {
3790 |     if (liveData[key]) return Promise.resolve(liveData[key]);
3791 |     return (window.fetchWithTimeout || function(u){ return fetch(u).then(function(r){return r.json();}); })(url, 10000)
3792 |       .then(function(d){ if(d) liveData[key] = d; return d || {}; });
3793 |   }
3794 |   // Recent trades (deduped — uses liveData.trades from SS2 fetchAll)
3795 |   getCachedOrFetch('trades', '/api/congress/trades').then(function(d){
3796 |     var el = document.getElementById('pnCongress');
3797 |     if (!el) return;
3798 |     var trades = d.trades || [];
3799 |     if (!trades.length) { el.innerHTML = '<div style="color:#555;font-size:10px;">No trades available</div>'; return; }
3800 |     var html = '';
3801 |     trades.slice(0, 8).forEach(function(t) {
3802 |       var isBuy = (t.transaction || '').toLowerCase().indexOf('purchase') >= 0;
3803 |       var partyCol = t.party === 'D' ? '#3b82f6' : t.party === 'R' ? '#ef4444' : '#888';
3804 |       html += '<div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-family:\'JetBrains Mono\',monospace;font-size:9px;">';
3805 |       html += '<span style="color:' + partyCol + ';font-weight:700;min-width:14px;">' + (t.party || '?') + '</span>';
3806 |       html += '<span style="color:rgba(255,255,255,0.6);min-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + (t.member || 'Unknown') + '</span>';
3807 |       html += '<span style="color:' + (isBuy ? '#22c55e' : '#ef4444') + ';font-weight:600;min-width:45px;">' + (isBuy ? 'BUY' : 'SELL') + '</span>';
3808 |       html += '<span style="color:#f8c15c;font-weight:700;min-width:40px;">' + (t.ticker || '???') + '</span>';
3809 |       html += '<span style="color:rgba(255,255,255,0.3);margin-left:auto;">' + (t.amount || '') + '</span>';
3810 |       html += '</div>';
3811 |     });
3812 |     if (d.trades && d.trades[0] && d.trades[0].source === 'fallback') {
3813 |       html += '<div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;">Source: Public STOCK Act filings (add QUIVER_API_KEY for live data)</div>';
3814 |     }
3815 |     el.innerHTML = html;
3816 |   }).catch(function(e){ console.warn('Congress trades:', e); });
3817 | 
3818 |   // Party breakdown (deduped — reuses liveData.trades)
3819 |   getCachedOrFetch('trades', '/api/congress/trades').then(function(d){
3820 |     var el = document.getElementById('pnPartyBreakdown');
3821 |     if (!el) return;
3822 |     var pb = d.party_breakdown || {};
3823 |     var html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">';
3824 |     [{k:'D',label:'DEMOCRAT',col:'#3b82f6'},{k:'R',label:'REPUBLICAN',col:'#ef4444'},{k:'I',label:'INDEPENDENT',col:'#888'}].forEach(function(p){
3825 |       var data = pb[p.k] || {buys:0,sells:0,total:0};
3826 |       html += '<div style="text-align:center;padding:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);border-radius:4px;">';
3827 |       html += '<div style="font-size:7px;font-weight:700;letter-spacing:0.12em;color:' + p.col + ';">' + p.label + '</div>';
3828 |       html += '<div style="font-size:18px;font-weight:900;color:#fff;margin-top:4px;">' + data.total + '</div>';
3829 |       html += '<div style="font-size:8px;color:rgba(255,255,255,0.3);margin-top:2px;">' + data.buys + ' BUY / ' + data.sells + ' SELL</div>';
3830 |       html += '</div>';
3831 |     });
3832 |     html += '</div>';
3833 |     el.innerHTML = html;
3834 |   }).catch(function(){});
3835 | 
3836 |   // IHX Score (deduped — reuses liveData.ihx)
3837 |   getCachedOrFetch('ihx', '/api/congress/ihx').then(function(d){
3838 |     var el = document.getElementById('pnIHX');
3839 |     if (!el) return;
3840 |     var s = d.score || 50;
3841 |     var col = s > 65 ? '#22c55e' : s < 35 ? '#ef4444' : '#f8c15c';
3842 |     var signal = (d.signal || 'neutral').toUpperCase();
3843 |     el.innerHTML = '<div style="display:flex;align-items:center;gap:12px;">'
3844 |       + '<div style="font-size:28px;font-weight:900;color:' + col + ';">' + s + '</div>'
3845 |       + '<div><div style="font-size:10px;font-weight:700;color:' + col + ';">' + signal + '</div>'
3846 |       + '<div style="font-size:8px;color:rgba(255,255,255,0.4);margin-top:2px;">' + (d.interpretation || '') + '</div></div></div>'
3847 |       + '<div style="height:3px;background:rgba(255,255,255,0.04);border-radius:2px;margin-top:8px;"><div style="height:100%;width:' + s + '%;background:' + col + ';border-radius:2px;"></div></div>'
3848 |       + '<div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:6px;">' + (d.trade_count || 0) + ' trades analyzed • ' + (d.crypto_trades || 0) + ' crypto-adjacent</div>';
3849 |   }).catch(function(){});
3850 | 
3851 |   // ── Institutional Accumulation (SEC EDGAR 13F) ─────────────────
3852 |   getCachedOrFetch('inst', '/api/panopticon/institutional').then(function(d){
3853 |     var el13f = document.getElementById('pnInstitutional');
3854 |     var elBanner = document.getElementById('pnCoalitionBanner');
3855 |     var elNote = document.getElementById('pnCoalitionNote');
3856 |     if (!el13f) return;
3857 | 
3858 |     // Coalition banner
3859 |     if (d.coalition_summary && d.coalition_summary.detected && elBanner) {
3860 |       var months = d.coalition_summary.active_months || {};
3861 |       var monthKeys = Object.keys(months);
3862 |       var bestMonth = monthKeys.length ? months[monthKeys[0]] : null;
3863 |       if (bestMonth) {
3864 |         elNote.textContent = bestMonth.note || (bestMonth.filers + ' institutions in coordinated accumulation window');
3865 |         elBanner.style.display = 'block';
3866 |       }
3867 |     }
3868 | 
3869 |     var filers = d.institutional_13f || [];
3870 |     if (!filers.length) { el13f.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;font-family:\'JetBrains Mono\',monospace;">No 13F data in current window</div>'; return; }
3871 | 
3872 |     var html = '<div style="display:flex;flex-direction:column;gap:6px;">';
3873 |     filers.slice(0,8).forEach(function(f){
3874 |       var score = f.coalition_score || 0;
3875 |       var scoreCol = score >= 80 ? '#ef4444' : score >= 50 ? '#f8c15c' : '#888';
3876 |       var tag = f.coalition_detected ? '<span style="background:rgba(204,0,0,0.15);color:#cc0000;font-size:7px;padding:2px 6px;border-radius:3px;letter-spacing:.08em;margin-left:6px;">COALITION</span>' : '';
3877 |       html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3878 |         + '<div><div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:rgba(255,255,255,0.85);">' + f.entity + tag + '</div>'
3879 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.35);margin-top:2px;">' + f.institution_type + ' · ' + (f.filing_date || '') + ' · 13F-HR</div></div>'
3880 |         + '<div style="font-size:9px;color:#22c55e;font-family:\'JetBrains Mono\',monospace;">BTC ETF ↑</div>'
3881 |         + '</div>';
3882 |     });
3883 |     html += '</div><div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: SEC EDGAR 13F · ' + (d.total_institutional_filers || 0) + ' filers</div>';
3884 |     el13f.innerHTML = html;
3885 |   }).catch(function(){ });
3886 | 
3887 |   // ── Private Equity Datastream (Form D + Coalition) ────────────
3888 |   getCachedOrFetch('pe', '/api/panopticon/pe-datastream').then(function(d){
3889 |     var elPE = document.getElementById('pnPEDatastream');
3890 |     if (!elPE) return;
3891 |     var rounds = d.pe_rounds || [];
3892 |     if (!rounds.length) { elPE.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;font-family:\'JetBrains Mono\',monospace;">No PE rounds in current window</div>'; return; }
3893 | 
3894 |     var html = '';
3895 |     if (d.coalition_active) {
3896 |       html += '<div style="background:rgba(204,0,0,0.08);border-left:3px solid #cc0000;padding:8px 12px;margin-bottom:10px;border-radius:0 4px 4px 0;">'
3897 |         + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:8px;letter-spacing:.15em;color:#cc0000;font-weight:700;">COALITION EFFECT ACTIVE</div>'
3898 |         + '<div style="font-size:10px;color:rgba(255,255,255,0.6);margin-top:4px;">' + (d.insight || '') + '</div>'
3899 |         + '</div>';
3900 |     }
3901 | 
3902 |     html += '<div style="display:flex;flex-direction:column;gap:6px;">';
3903 |     rounds.slice(0,8).forEach(function(r){
3904 |       html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3905 |         + '<div><div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:rgba(255,255,255,0.85);">' + r.entity + '</div>'
3906 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.35);margin-top:2px;">' + (r.filing_date || '') + ' · Form D · Digital Assets</div></div>'
3907 |         + '<div style="font-size:9px;color:#f8c15c;font-family:\'JetBrains Mono\',monospace;">RAISE ↑</div>'
3908 |         + '</div>';
3909 |     });
3910 |     html += '</div><div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: SEC EDGAR Form D · ' + (d.pe_count || 0) + ' rounds</div>';
3911 |     elPE.innerHTML = html;
3912 |   }).catch(function(){ });
3913 | 
3914 | 
3915 |   // ── Bitcoin Bill Gap Tracker ──────────────────────────────────────────────
3916 |   (function loadBillTracker() {
3917 |     var el = document.getElementById('pnBillTracker');
3918 |     if (!el) return;
3919 | 
3920 |     fetch('/api/panopticon/bills')
3921 |       .then(function(r) { return r.json(); })
3922 |       .then(function(data) {
3923 |         var bills = (data.bills || []).slice(0, 12);
3924 |         if (!bills.length) {
3925 |           el.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;">No active Bitcoin legislation found</div>';
3926 |           return;
3927 |         }
3928 | 
3929 |         var html = '<div style="display:flex;flex-direction:column;gap:10px;">';
3930 | 
3931 |         bills.forEach(function(b) {
3932 |           var gap = b.gap_score !== null ? b.gap_score : null;
3933 |           var gapCol = gap === null ? '#888' : gap >= 40 ? '#ef4444' : gap >= 20 ? '#f97316' : '#22c55e';
3934 |           var gapLabel = b.gap_label || 'PENDING';
3935 |           var congPct = b.congress_pct || 0;
3936 |           var pubPct  = b.public_pct  || 50;
3937 |           var hasCongVote = b.vote_tally && b.vote_tally.total > 0;
3938 |           var btcCol = b.btc_signal === 'bullish' ? '#22c55e' : b.btc_signal === 'bearish' ? '#ef4444' : '#888';
3939 |           var cats = (b.categories || []).join(', ').replace(/_/g,' ');
3940 | 
3941 |           html += '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:10px 12px;">';
3942 | 
3943 |           // Header row
3944 |           html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
3945 |             + '<div>'
3946 |             + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:rgba(255,255,255,0.9);">'
3947 |             + b.bill_number + ' — ' + (b.short_title || '').substring(0,40) + '</div>'
3948 |             + '<div style="font-size:7px;color:rgba(255,255,255,0.3);margin-top:2px;text-transform:uppercase;letter-spacing:.06em;">'
3949 |             + cats.substring(0,35) + '</div>'
3950 |             + '</div>'
3951 |             + '<div style="text-align:right;flex-shrink:0;margin-left:8px;">'
3952 |             + (gap !== null ? '<div style="font-family:\'JetBrains Mono\',monospace;font-size:14px;font-weight:900;color:' + gapCol + ';">' + gap + '%</div>'
3953 |                            : '<div style="font-size:8px;color:#888;font-family:\'JetBrains Mono\',monospace;">PENDING</div>')
3954 |             + '<div style="font-size:6px;letter-spacing:.1em;color:' + gapCol + ';font-weight:700;">GAP</div>'
3955 |             + '</div>'
3956 |             + '</div>';
3957 | 
3958 |           // Progress bars
3959 |           html += '<div style="display:flex;flex-direction:column;gap:5px;margin-bottom:6px;">';
3960 | 
3961 |           // Public bar
3962 |           html += '<div style="display:flex;align-items:center;gap:6px;">'
3963 |             + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;flex-shrink:0;font-family:\'JetBrains Mono\',monospace;">PUBLIC</div>'
3964 |             + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;position:relative;">'
3965 |             + '<div style="height:100%;width:' + pubPct + '%;background:linear-gradient(90deg,#22c55e,#16a34a);border-radius:3px;transition:width .8s ease;"></div>'
3966 |             + '</div>'
3967 |             + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;font-weight:700;color:#22c55e;width:30px;text-align:right;">' + pubPct + '%</div>'
3968 |             + '</div>';
3969 | 
3970 |           // Congress bar
3971 |           if (hasCongVote) {
3972 |             var congBarColor = congPct >= 67 ? '#22c55e' : congPct >= 50 ? '#f8c15c' : '#ef4444';
3973 |             var nayPct = 100 - congPct;
3974 |             html += '<div style="display:flex;align-items:center;gap:6px;">'
3975 |               + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;flex-shrink:0;font-family:\'JetBrains Mono\',monospace;">CONGRESS</div>'
3976 |               + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;display:flex;">'
3977 |               + '<div style="height:100%;width:' + congPct + '%;background:' + congBarColor + ';transition:width .8s ease;"></div>'
3978 |               + '<div style="height:100%;width:' + nayPct + '%;background:#ef4444;opacity:0.5;"></div>'
3979 |               + '</div>'
3980 |               + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;font-weight:700;color:' + congBarColor + ';width:30px;text-align:right;">' + congPct + '%</div>'
3981 |               + '</div>';
3982 |           } else {
3983 |             html += '<div style="display:flex;align-items:center;gap:6px;">'
3984 |               + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;font-family:\'JetBrains Mono\',monospace;">CONGRESS</div>'
3985 |               + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.04);border-radius:3px;display:flex;align-items:center;padding-left:8px;">'
3986 |               + '<span style="font-size:7px;color:rgba(255,255,255,0.2);font-family:\'JetBrains Mono\',monospace;">NO VOTE YET</span>'
3987 |               + '</div></div>';
3988 |           }
3989 | 
3990 |           html += '</div>'; // end bars
3991 | 
3992 |           // Footer: status + vote buttons
3993 |           html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">'
3994 |             + '<div>'
3995 |             + '<span style="font-size:7px;color:rgba(255,255,255,0.3);">' + (b.status||'') + '</span>'
3996 |             + (b.sponsor ? '<span style="font-size:7px;color:rgba(255,255,255,0.2);margin-left:8px;">Sponsor: ' + b.sponsor.substring(0,20) + '</span>' : '')
3997 |             + '</div>'
3998 |             + '<div style="display:flex;gap:4px;align-items:center;">'
3999 |             + '<span style="font-size:7px;color:rgba(255,255,255,0.25);font-family:\'JetBrains Mono\',monospace;">SHOULD PASS?</span>'
4000 |             + '<button onclick="castBillVote(' + b.bill_id + ',\'' + b.bill_number + '\',\'yes\')" '
4001 |             +   'style="background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);color:#22c55e;padding:2px 8px;border-radius:3px;font-size:8px;font-family:\'JetBrains Mono\',monospace;cursor:pointer;letter-spacing:.08em;">YES</button>'
4002 |             + '<button onclick="castBillVote(' + b.bill_id + ',\'' + b.bill_number + '\',\'no\')" '
4003 |             +   'style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;padding:2px 8px;border-radius:3px;font-size:8px;font-family:\'JetBrains Mono\',monospace;cursor:pointer;letter-spacing:.08em;">NO</button>'
4004 |             + '</div>'
4005 |             + '</div>';
4006 | 
4007 |           html += '</div>'; // end card
4008 |         });
4009 | 
4010 |         html += '</div>';
4011 |         html += '<div style="font-size:7px;color:rgba(255,255,255,0.15);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">'
4012 |           + 'Source: LegiScan API (CC BY 4.0) · ' + data.total_bills + ' bills tracked'
4013 |           + '</div>';
4014 |         el.innerHTML = html;
4015 |       })
4016 |       .catch(function(e) {
4017 |         if (el) el.innerHTML = '<div style="color:rgba(255,255,255,0.15);font-size:9px;">Bill tracker unavailable</div>';
4018 |       });
4019 |   })();
4020 | 
4021 |   function castBillVote(billId, billNumber, vote) {
4022 |     // Frontend validation — backend must also validate (secondary defense only)
4023 |     if (typeof billId !== 'number' || !Number.isFinite(billId)) return;
4024 |     if (typeof billNumber !== 'string' || !/^[A-Za-z0-9.\- ]+$/.test(billNumber)) return;
4025 |     if (vote !== 'yes' && vote !== 'no') return;
4026 |     fetch('/api/panopticon/bills/vote', {
4027 |       method: 'POST',
4028 |       headers: {'Content-Type': 'application/json'},
4029 |       body: JSON.stringify({bill_id: billId, bill_number: billNumber, vote: vote})
4030 |     })
4031 |     .then(function(r) { return r.json(); })
4032 |     .then(function(d) {
4033 |       if (d.success) {
4034 |         // Flash the bill card
4035 |         var cards = document.querySelectorAll('#pnBillTracker > div > div');
4036 |         // Reload the tracker to show updated votes
4037 |         setTimeout(function() {
4038 |           document.getElementById('pnBillTracker').innerHTML =
4039 |             '<div style="color:rgba(34,197,94,0.8);font-size:9px;font-family:\'JetBrains Mono\',monospace;padding:8px;">Vote recorded. Reloading...</div>';
4040 |           setTimeout(function() { loadBillTracker(); }, 1500);
4041 |         }, 300);
4042 |       }
4043 |     })
4044 |     .catch(function() {});
4045 |   }
4046 | 
4047 | })();
4048 | 
4049 | </script>
4050 | {% endblock %}
4051 | 
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
