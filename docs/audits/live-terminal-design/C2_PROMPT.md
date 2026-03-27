# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: live-terminal-design
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
Below is a comprehensive design audit for the "Live Terminal" visualization of Bitcoin network data, focusing on creating a unified, breathtaking, and emotionally resonant experience. My responses to the eight design questions aim to transform the current collection of widgets into a singular, living visualization that captures the essence of Bitcoin's decentralized heartbeat. Each answer includes detailed design concepts, visual descriptions, technical approaches, and justifications for why these ideas stand out.

---

### Q1. HERO VISUALIZATION
**Design Concept: "Bitcoin Nebula" - A Pulsating Cosmic WebGL Heartbeat**  
The centerpiece is a 3D WebGL visualization called "Bitcoin Nebula," representing the Bitcoin network as a dynamic, pulsating cosmic structure. It combines the organic feel of a living organism with the vastness of a galaxy, embodying Bitcoin's decentralized and resilient nature.

- **Particles/Nodes Representation**: Each particle represents a Bitcoin node, with clusters forming around major geographic hubs (e.g., Frankfurt, New York) based on real data from `nodeRegions`. Larger, brighter particles indicate higher node density or hashrate contribution, pulsing subtly to mimic a heartbeat (tied to block time).
- **Transactions Appearance and Travel**: Transactions appear as glowing, comet-like streaks originating from random nodes, arcing through the nebula in Fibonacci spiral paths (see Q5). Their speed reflects fee rate (faster for higher fees), and they converge into a central "mempool vortex" before being absorbed into blocks.
- **Block Confirmations Manifestation**: When a block is confirmed (via WebSocket), a radiant shockwave emanates from the nebula's core, rippling outward in a golden spiral pattern. Nodes briefly flare brighter, symbolizing network consensus, with a deep, resonant audio chime (if enabled).
- **Color Language**: The nebula's base color is a deep navy (#0A0A0F per LAW 1), with nodes glowing in Bitcoin orange (#f7931a). Transaction streaks shift from red (#CC2222) for high fee pressure to green (#22c55e) for low fees. Fear and Greed Index (FNG) influences the nebula's background aura—red haze for fear (<25), gold shimmer (#F8C15C) for greed (>75).
- **Fibonacci/Golden Spiral Physics**: Transaction paths and shockwaves follow Fibonacci spirals, with radii expanding by the golden ratio (1.618) for each turn, creating a natural, harmonious flow (detailed in Q5).

**Visual Description**: Users see a 3D cosmic nebula floating in the browser, with thousands of glowing orange nodes pulsing like a heartbeat. Comet-like transactions streak in elegant spirals, converging into a swirling mempool vortex at the center. Periodic block confirmations trigger golden shockwaves that ripple outward, illuminating nodes in a mesmerizing dance of light.

**Technical Approach**: Use Three.js r128 with instanced meshes for nodes (reducing draw calls), custom vertex shaders for pulsing effects (sin wave on opacity), and particle systems for transaction streaks with Bezier curve paths. UnrealBloomPass enhances glow effects for shockwaves. AudioContext API syncs chimes to block events.

**Why This Wins**: Unlike static charts or disconnected widgets, "Bitcoin Nebula" unifies all network data into a single, living entity. It captures Bitcoin's essence as a decentralized, unstoppable force, evoking awe and curiosity through organic motion and cosmic scale, far surpassing typical financial dashboards.

---

### Q2. DATA MAPPING
**Design Concept: Visual Properties as Network Vital Signs**  
Each live data point drives a specific visual or auditory element in the "Bitcoin Nebula," making the visualization a real-time reflection of network health.

- **BTC Price → Nebula Core Brightness**: Higher prices increase the core's glow intensity (mapped to UnrealBloomPass strength, 0.5 to 2.0), symbolizing market energy.
- **Mempool Size → Vortex Scale**: Larger mempool sizes (vsize from API) scale up the central vortex diameter (1.0 to 3.0 units in Three.js), with denser particle swirls indicating congestion.
- **Hashrate → Node Pulse Frequency**: Higher hashrate (EH/s) speeds up node pulsing (sin wave frequency from 0.5 to 2.0 Hz), reflecting network security.
- **Fear and Greed Index (FNG) → Background Aura Color**: FNG shifts the nebula's background gradient—red (#CC2222) for fear, neutral navy (#0A0A0F) for balanced, gold (#F8C15C) for greed—via fragment shader uniforms.
- **Block Time → Shockwave Intensity**: Longer block times (minutes since last block) amplify shockwave opacity and radius (0.2 to 0.8 opacity), showing network strain.
- **Fee Rate → Transaction Color and Speed**: Higher sat/vB shifts transaction streaks from green (#22c55e) to red (#CC2222) via color interpolation, with speed scaling linearly (0.1 to 0.5 units/frame).
- **Transaction Count → Vortex Particle Density**: Higher pending TX counts increase particle density in the mempool vortex (100 to 1000 particles), creating a thicker

## GEMINI — CYCLE 1 OUTPUT
An audit of the `live-terminal-design` feature for Protocol Pulse has been completed.

This is a comprehensive design and architectural review, focusing on transforming the existing implementation into a world-class, cohesive, and breathtaking visual experience. The current page is a feature-rich dashboard, but it lacks a singular, powerful narrative. My recommendations aim to unify these components into an awe-inspiring "living" visualization of the Bitcoin network.

First, I must flag several violations of the Governing Laws in the provided code, which should be addressed regardless of the design direction chosen:

*   **LAW 1 (BRAND PALETTE) VIOLATION:**
    *   The CSS defines `--apple-bg: #000000` (line 31) and uses `background: #000` (line 60), violating the `#0A0A0F` background law.
    *   It introduces numerous non-palette colors like `--fee-green: #22c55e`, `--accent-blue: #0a84ff`, etc., without justification.
    *   The "Apple-style" color system (lines 31-36) is a deviation from the established brand palette and should be removed in favor of the primary laws.
*   **LAW 3 (TYPOGRAPHY) VIOLATION:**
    *   The CSS imports and uses `'Crimson Pro'` (line 52) and `'SF Pro Display'` (line 195), which are not the specified `JetBrains Mono` font for data and kickers.
*   **TECHNOLOGY STACK (MAINTAINABILITY) VIOLATION:**
    *   The HTML file is riddled with thousands of lines of inline `style` attributes. This is a severe maintainability issue that violates best practices. All styles should be moved to the CSS `<style>` block or external stylesheets.
*   **TECHNOLOGY STACK (PERFORMANCE) VIOLATION:**
    *   The code imports Three.js `r128` (lines 790-798). This version is from early 2021. It is critically outdated and misses years of major performance improvements (e.g., InstancedMesh updates, shader optimizations) and features. This must be updated to the latest stable version.
*   **TECHNOLOGY STACK (EFFICIENCY) VIOLATION:**
    *   Multiple JavaScript functions (`updateSovereignStatusBar`, `updateNetworkIntel`, `updateMempoolData`, etc.) make redundant `fetch` calls to the same `mempool.space` API endpoints. This should be consolidated into a single data-fetching service with a state cache to improve performance and reduce API load.
*   **TECHNOLOGY STACK (ANIMATION) VIOLATION:**
    *   The code includes scripts to import and use Three.js (lines 7099-7108, 7726+). This is a direct and severe violation of the law: "All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas". **However, given the explicit context of the audit to design a WebGL experience, I will proceed under the assumption this law is meant for UI components (buttons, cards) and that WebGL is permitted for the main "hero" data visualization canvas. This law must be clarified or amended.**

---

### Q1. HERO VISUALIZATION

**DETAILED DESIGN: "Stellar Consensus"**

The centerpiece is an abstract, celestial visualization. We discard the literal globe of nodes. Instead, the "heartbeat of Bitcoin" is represented as a stellar system, a living star surrounded by a nebula of unconfirmed transactions.

*   **The Star (Current State):** At the center of the canvas is a single, slowly pulsing star. Its properties are directly tied to the network's health. The core is a dense, bright white, with a gaseous corona of Protocol Pulse Gold (`#F8C15C`).
*   **Particles (Transactions):** New transactions are not dots on a map; they are motes of light, particles of "stardust" that spawn at the edge of the scene and are drawn by gravity toward the central star.
*   **Transaction Flow:** These particles don't travel in straight lines. They are pulled into a swirling, chaotic cloud around the star—the "Mempool Nebula."
*   **Block Confirmation (The Pulse):** A block confirmation is the most dramatic event. The central star flashes brilliantly, emitting a visible, expanding shockwave of pure white light. This shockwave sweeps through the inner layers of the Mempool Nebula. It's a moment of consensus and finality.
*   **Settlement (Accretion Disk):** As the shockwave passes, it captures the "heaviest" (highest fee) particles from the nebula. These captured particles are pulled out of the chaotic cloud and gracefully settle into a new, stable, glowing ring around the star—an accretion disk. This disk represents the blockchain itself. Each new ring is a new block, slowly rotating and adding to the permanent history of the star.
*   **Color Language:**
    *   **Fee Pressure:** Transaction particles are colored by fee rate. Low-fee transactions are a subtle Gold (`#F8C15C`). Medium fees are White (`#FFFFFF`). High-fee, urgent transactions are a burning Primary Red (`#CC2222`). A congested mempool will cause the entire nebula to glow with an angry red hue.
    *   **Fear & Greed (FNG):** The scene's ambient lighting is tinted by the FNG index. "Extreme Fear" casts a cool, deep navy/blue light over everything. "Extreme Greed" gives the entire visualizat

## GPT4O — CYCLE 1 OUTPUT
### Q1. HERO VISUALIZATION

**DETAILED DESIGN:**
- **Particles/Nodes:** Each particle represents a Bitcoin node, with size and brightness indicating node activity and importance. Nodes are interconnected by lines representing the network's mesh.
- **Transactions:** Appear as glowing particles that travel along the network lines, with speed and color intensity representing transaction size and fee.
- **Block Confirmations:** Manifest as waves of light that ripple outward from the center of the network, with intensity and frequency indicating block confirmations.
- **Color Language:** 
  - **Fee Pressure:** High fee pressure is shown with intense red hues, while low pressure is a calming green.
  - **Fear vs. Greed:** Fear is depicted with dark, muted colors, while greed is shown with vibrant golds and yellows.
- **Fibonacci/Golden Spiral:** The entire network layout follows a golden spiral, with nodes and transaction paths adhering to Fibonacci ratios for natural aesthetics.

**VISUAL DESCRIPTION:**
Users see a dynamic, interconnected web of nodes with glowing lines. Transactions move like shooting stars, and block confirmations create mesmerizing ripples. The color scheme shifts based on network conditions, creating a living, breathing visualization.

**TECHNICAL APPROACH:**
- **Three.js:** Use instanced meshes for nodes and lines to optimize performance. Implement shaders for glowing effects and dynamic color changes.
- **Shaders:** Custom shaders for particle glow and ripple effects, using sine functions to create smooth transitions.
- **Golden Spiral Physics:** Calculate node positions using polar coordinates with Fibonacci ratios to create a spiral layout.

**WHY THIS WINS:**
This design creates a visually stunning and informative representation of the Bitcoin network, leveraging natural mathematical beauty to engage users.

### Q2. DATA MAPPING

**DETAILED DESIGN:**
- **BTC Price:** Node size and brightness.
- **Mempool Size:** Thickness and intensity of transaction lines.
- **Hashrate:** Speed of transaction particles.
- **FNG Index:** Background color gradient (fear: dark blue, greed: bright yellow).
- **Block Time:** Frequency of ripple effects.
- **Fee Rate:** Color of transaction particles (low: green, high: red).
- **Transaction Count:** Density of particles on the network.

**VISUAL DESCRIPTION:**
Each data point directly influences a visual property, creating a dynamic and responsive visualization that reflects real-time network conditions.

**TECHNICAL APPROACH:**
- **Shaders:** Use uniforms to dynamically update visual properties based on real-time data.
- **Three.js:** Efficiently manage particle systems and line meshes to reflect data changes.

**WHY THIS WINS:**
Direct data-to-visual mapping ensures users can intuitively understand network conditions at a glance.

### Q3. LAYOUT

**DETAILED DESIGN:**
- **Hero Visualization:** Centralized, occupying the majority of the screen.
- **Supporting Elements:** Minimalistic data panels on the sides, showing key metrics like BTC price, mempool size, and hashrate.
- **Cuts:** Remove redundant widgets and focus on integrating data into the hero visualization.

**VISUAL DESCRIPTION:**
A clean, focused layout with a dominant central visualization and essential data panels on the periphery.

**TECHNICAL APPROACH:**
- **CSS Grid/Flexbox:** For responsive layout management.
- **Three.js Canvas:** Positioned centrally with adaptive scaling for different screen sizes.

**WHY THIS WINS:**
A streamlined layout enhances focus on the hero visualization, reducing distractions and improving user experience.

### Q4. PERFORMANCE

**DETAILED DESIGN:**
- **Particle Count Limits:** Cap at 10,000 particles for mobile.
- **Instanced Meshes:** Use for nodes and lines to reduce draw calls.
- **LOD (Level of Detail):** Implement LOD techniques to reduce complexity based on camera distance.

**VISUAL DESCRIPTION:**
Smooth, responsive interactions even on mobile, with adaptive detail levels ensuring performance without sacrificing visual quality.

**TECHNICAL APPROACH:**
- **Three.js:** Utilize instanced meshes and LOD.
- **WebGL Optimization:** Minimize shader complexity and use efficient data structures.

**WHY THIS WINS:**
Optimizations ensure the visualization remains fluid and engaging across devices, crucial for user retention.

### Q5. FIBONACCI/SACRED GEOMETRY

**DETAILED DESIGN:**
- **Golden Spiral Layout:** Nodes are positioned along a logarithmic spiral, calculated using the formula \( r = ae^{b\theta} \), where \( a \) and \( b \) are constants derived from Fibonacci ratios.
- **Particle Movement:** Transaction paths follow spiral arcs, creating a natural flow.

**VISUAL DESCRIPTION:**
A harmonious, aesthetically pleasing network layout that feels organic and balanced.

**TECHNICAL APPROACH:**
- **Mathematical Calculations:** Pre-calculate node positions using the spiral formula.
- **Three.js:** Implement particle movement along pre-defined spiral paths.

**WHY T

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — LIVE-TERMINAL-DESIGN — CYCLE 1
Generated: 2026-03-25 02:03
Models: grok, gemini, gpt4o

---

## SCORES

> **Scoring Note:** No models provided explicit numerical scores in their outputs. Scores below are synthesized from depth, specificity, technical rigor, and actionability of each model's response per subsystem.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Hero Visualization | 95 | 72 | 92 | 86 |
| Data Mapping | 90 | 75 | 88 | 84 |
| Layout | 70 | 70 | 85 | 75 |
| Performance | 65 | 78 | 80 | 74 |
| Fibonacci/Sacred Geometry | 75 | 72 | 88 | 78 |
| Emotional Impact | 88 | 72 | 82 | 81 |
| Data Freshness | 60 | 78 | 65 | 68 |
| Killer Feature | 72 | 75 | 70 | 72 |
| Law Compliance | 92 | 55 | 70 | 72 |
| Code Quality | 90 | 50 | 60 | 67 |
| **OVERALL** | **80** | **68** | **78** | **75** |

**Scoring rationale:**
- Gemini scored highest on Law Compliance and Code Quality due to being the only model to systematically audit violations with file/line specificity
- Grok scored highest on Hero Visualization and Fibonacci due to deepest technical implementation detail
- GPT-4o scored highest on Data Freshness due to explicit reconnection/fallback strategy mention
- No model achieved excellence on Data Freshness or Killer Feature — systemic gap

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

---

### U1 — Background color is `#000000`, must be `#0A0A0F`
**What it is:** The CSS defines `--apple-bg: #000000` and `background: #000` in multiple places. All three models independently identified this as a LAW 1 violation (brand palette).
**File/Line:** `live-terminal-design.html` — CSS block, approximately line 31 (`--apple-bg: #000000`) and line 60 (`background: #000`)
**What to change:**
```css
/* REMOVE */
--apple-bg: #000000;
background: #000;

/* REPLACE WITH */
--bg-primary: #0A0A0F;
background: #0A0A0F;
```
Apply globally to all body, canvas, and container backgrounds.

---

### U2 — WebGL/Three.js is used; Three.js version `r128` is critically outdated
**What it is:** All three models flagged the use of Three.js r128 (circa early 2021). Three+ years of performance improvements, InstancedMesh updates, and shader optimizations are being missed. Grok and GPT-4o both recommend InstancedMesh patterns. Gemini explicitly calls this a TECHNOLOGY STACK violation.
**File/Line:** `live-terminal-design.html` — import block, approximately lines 790–798
**What to change:**
```html
<!-- REMOVE -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

<!-- REPLACE WITH — use importmap or CDN pointing to latest stable -->
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.163.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.163.0/examples/jsm/"
  }
}
</script>
```

---

### U3 — Hero visualization lacks a singular, unified narrative structure
**What it is:** All three m

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/live-terminal-design/live_terminal_excerpt.html (1624 lines)
```
   1 | 
   2 | ============================================================
   3 | === CSS VARIABLES & ZONE ARCHITECTURE (lines 1-100 of 9534) ===
   4 | ============================================================
   5 | 
   6 |     1 | {% extends "base.html" %}
   7 |     2 | 
   8 |     3 | {% block title %}Live Settlement Terminal | Protocol Pulse{% endblock %}
   9 |     4 | 
  10 |     5 | {% block head %}
  11 |     6 | <style>
  12 |     7 | :root {
  13 |     8 |     --pp-bitcoin: #f7931a;
  14 |     9 |     --pp-bitcoin-dark: #c16c00;
  15 |    10 |     --pp-bitcoin-glow: rgba(247, 147, 26, 0.5);
  16 |    11 |     --pp-dark: #0a0a0a;
  17 |    12 |     --pp-glass: rgba(10, 10, 10, 0.9);
  18 |    13 |     --zone-border: rgba(255, 255, 255, 0.06);
  19 |    14 |     --fee-green: #22c55e;
  20 |    15 |     --fee-yellow: #eab308;
  21 |    16 |     --fee-red: #dc2626;
  22 |    17 | 
  23 |    18 |     /* Apple-style spacing system */
  24 |    19 |     --space-xs: 8px;
  25 |    20 |     --space-sm: 16px;
  26 |    21 |     --space-md: 32px;
  27 |    22 |     --space-lg: 64px;
  28 |    23 |     --space-xl: 96px;
  29 |    24 | 
  30 |    25 |     /* Apple-style colors */
  31 |    26 |     --apple-bg: #000000;
  32 |    27 |     --apple-card: rgba(28, 28, 30, 0.8);
  33 |    28 |     --apple-card-border: rgba(255, 255, 255, 0.08);
  34 |    29 |     --apple-text-primary: rgba(255, 255, 255, 0.92);
  35 |    30 |     --apple-text-secondary: rgba(255, 255, 255, 0.55);
  36 |    31 |     --apple-text-tertiary: rgba(255, 255, 255, 0.35);
  37 |    32 | 
  38 |    33 |     /* Refined accent colors */
  39 |    34 |     --accent-bitcoin: #f7931a;
  40 |    35 |     --accent-green: #30d158;
  41 |    36 |     --accent-red: #ff453a;
  42 |    37 |     --accent-blue: #0a84ff;
  43 |    38 |     --accent-purple: #bf5af2;
  44 |    39 | }
  45 |    40 | 
  46 |    41 | /* ============================================
  47 |    42 |    OPERATION SOVEREIGN TIGHTENING
  48 |    43 |    Three-Zone Architecture
  49 |    44 |    ============================================ */
  50 |    45 | 
  51 |    46 | /* Google Fonts - Premium Serif for Analysis */
  52 |    47 | @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600;700&display=swap');
  53 |    48 | 
  54 |    49 | /* ZONE 1: TACTICAL HORIZON */
  55 |    50 | .zone-tactical-horizon {
  56 |    51 |     position: relative;
  57 |    52 |     width: 100%;
  58 |    53 |     height: auto;
  59 |    54 |     overflow: hidden;
  60 |    55 |     background: #000;
  61 |    56 | }
  62 |    57 | 
  63 |    58 | /* BITCOIN HEARTBEAT AUDIO INDICATOR - World-Class Subtle Touch */
  64 |    59 | .heartbeat-audio-indicator {
  65 |    60 |     display: flex;
  66 |    61 |     align-items: center;
  67 |    62 |     gap: 8px;
  68 |    63 |     padding: 6px 14px;
  69 |    64 |     background: rgba(220, 38, 38, 0.08);
  70 |    65 |     border: 1px solid rgba(220, 38, 38, 0.15);
  71 |    66 |     border-radius: 20px;
  72 |    67 |     cursor: pointer;
  73 |    68 |     position: relative;
  74 |    69 |     transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  75 |    70 |     opacity: 0.7;
  76 |    71 | }
  77 |    72 | 
  78 |    73 | .heartbeat-audio-indicator:hover {
  79 |    74 |     opacity: 1;
  80 |    75 |     background: rgba(220, 38, 38, 0.12);
  81 |    76 |     border-color: rgba(220, 38, 38, 0.25);
  82 |    77 |     transform: scale(1.02);
  83 |    78 | }
  84 |    79 | 
  85 |    80 | .heartbeat-audio-indicator.active {
  86 |    81 |     opacity: 1;
  87 |    82 |     background: rgba(220, 38, 38, 0.15);
  88 |    83 |     border-color: rgba(220, 38, 38, 0.4);
  89 |    84 | }
  90 |    85 | 
  91 |    86 | .heartbeat-pulse-ring {
  92 |    87 |     position: absolute;
  93 |    88 |     inset: -4px;
  94 |    89 |     border-radius: 24px;
  95 |    90 |     border: 1px solid rgba(220, 38, 38, 0);
  96 |    91 |     pointer-events: none;
  97 |    92 |     transition: all 0.3s ease;
  98 |    93 | }
  99 |    94 | 
 100 |    95 | .heartbeat-audio-indicator.active .heartbeat-pulse-ring {
 101 |    96 |     animation: heartbeatRingPulse 1.5s ease-in-out infinite;
 102 |    97 | }
 103 |    98 | 
 104 |    99 | @keyframes heartbeatRingPulse {
 105 |   100 |     0%, 100% {
 106 | 
 107 | ============================================================
 108 | === ZONE LOGIC ENGINE & SOVEREIGN ARCHIVE CSS (lines 186-300 of 9534) ===
 109 | ============================================================
 110 | 
 111 |   186 | .zone-logic-engine {
 112 |   187 |     position: relative;
 113 |   188 |     z-index: 10;
 114 |   189 |     background: transparent;
 115 |   190 |     padding: 30px 0 var(--space-lg) 0;
 116 |   191 |     margin-top: 0;
 117 |   192 | }
 118 |   193 | 
 119 |   194 | .dashboard-grid {
 120 |   195 |     display: grid;
 121 |   196 |     grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
 122 |   197 |     gap: var(--space-md);
 123 |   198 |     transition: opacity 0.3s ease;
 124 |   199 | }
 125 |   200 | 
 126 |   201 | @media (max-width: 991px) {
 127 |   202 |     .dashboard-grid {
 128 |   203 |         grid-template-columns: 1fr;
 129 |   204 |     }
 130 |   205 | }
 131 |   206 | 
 132 |   207 | /* Dashboard Instrument Panels - Apple Style */
 133 |   208 | .instrument-panel {
 134 |   209 |     background: var(--apple-card);
 135 |   210 |     border: 1px solid var(--apple-card-border);
 136 |   211 |     border-radius: 20px;
 137 |   212 |     padding: var(--space-md);
 138 |   213 |     position: relative;
 139 |   214 |     overflow: hidden;
 140 |   215 |     transition: transform 0.2s ease;
 141 |   216 | }
 142 |   217 | 
 143 |   218 | .instrument-panel::before {
 144 |   219 |     display: none;
 145 |   220 | }
 146 |   221 | 
 147 |   222 | /* Simplified fee states - subtle, not distracting */
 148 |   223 | .instrument-panel.fee-low,
 149 |   224 | .instrument-panel.fee-medium,
 150 |   225 | .instrument-panel.fee-high {
 151 |   226 |     border-color: var(--apple-card-border);
 152 |   227 |     box-shadow: none;
 153 |   228 |     animation: none;
 154 |   229 | }
 155 |   230 | 
 156 |   231 | @keyframes pulseHighFee {
 157 |   232 |     0%, 100% { box-shadow: none; }
 158 |   233 | }
 159 |   234 | 
 160 |   235 | /* Cleaner hover - no sibling dimming */
 161 |   236 | .dashboard-grid:hover .instrument-panel {
 162 |   237 |     opacity: 1;
 163 |   238 |     transition: opacity 0.4s ease;
 164 |   239 | }
 165 |   240 | 
 166 |   241 | .dashboard-grid:hover .instrument-panel:hover,
 167 |   242 | .instrument-panel:hover {
 168 |   243 |     opacity: 1;
 169 |   244 |     transform: translateY(-4px);
 170 |   245 | }
 171 |   246 | 
 172 |   247 | .instrument-panel .panel-header {
 173 |   248 |     display: flex;
 174 |   249 |     align-items: center;
 175 |   250 |     gap: var(--space-sm);
 176 |   251 |     margin-bottom: var(--space-md);
 177 |   252 |     padding-bottom: var(--space-sm);
 178 |   253 |     border-bottom: none;
 179 |   254 | }
 180 |   255 | 
 181 |   256 | .panel-icon {
 182 |   257 |     width: 44px;
 183 |   258 |     height: 44px;
 184 |   259 |     background: rgba(255, 255, 255, 0.06);
 185 |   260 |     border: none;
 186 |   261 |     border-radius: 12px;
 187 |   262 |     display: flex;
 188 |   263 |     align-items: center;
 189 |   264 |     justify-content: center;
 190 |   265 |     color: var(--accent-blue);
 191 |   266 |     font-size: 1.1rem;
 192 |   267 | }
 193 |   268 | 
 194 |   269 | .panel-title {
 195 |   270 |     font-family: 'SF Pro Display', -apple-system, sans-serif;
 196 |   271 |     font-size: 1.1rem;
 197 |   272 |     font-weight: 600;
 198 |   273 |     letter-spacing: -0.02em;
 199 |   274 |     color: var(--apple-text-primary);
 200 |   275 |     text-transform: none;
 201 |   276 |     margin: 0;
 202 |   277 | }
 203 |   278 | 
 204 |   279 | /* ZONE 3: SOVEREIGN ARCHIVE - Apple Style Folders */
 205 |   280 | .zone-sovereign-archive {
 206 |   281 |     position: relative;
 207 |   282 |     z-index: 10;
 208 |   283 |     background: transparent;
 209 |   284 |     padding: 20px 0 var(--space-lg) 0;
 210 |   285 | }
 211 |   286 | 
 212 |   287 | .archive-folder {
 213 |   288 |     background: var(--apple-card);
 214 |   289 |     border: 1px solid var(--apple-card-border);
 215 |   290 |     border-radius: 16px;
 216 |   291 |     margin-bottom: var(--space-sm);
 217 |   292 |     overflow: hidden;
 218 |   293 |     transition: all 0.3s ease;
 219 |   294 | }
 220 |   295 | 
 221 |   296 | .archive-folder.collapsed {
 222 |   297 |     background: var(--apple-card);
 223 |   298 | }
 224 |   299 | 
 225 |   300 | .archive-folder-header {
 226 | 
 227 | ============================================================
 228 | === NODE GLOBE CSS (lines 1838-1920 of 9534) ===
 229 | ============================================================
 230 | 
 231 |  1838 | /* NODE GLOBE */
 232 |  1839 | .globe-container {
 233 |  1840 |     width: 100%;
 234 |  1841 |     height: 400px;
 235 |  1842 |     position: relative;
 236 |  1843 |     border-radius: 12px;
 237 |  1844 |     overflow: hidden;
 238 |  1845 |     background: radial-gradient(circle at center, rgba(10, 10, 30, 0.8) 0%, rgba(0, 0, 0, 0.95) 100%);
 239 |  1846 | }
 240 |  1847 | 
 241 |  1848 | .globe-stats-overlay {
 242 |  1849 |     position: absolute;
 243 |  1850 |     bottom: 20px;
 244 |  1851 |     left: 20px;
 245 |  1852 |     background: rgba(0,0,0,0.7);
 246 |  1853 |     backdrop-filter: blur(10px);
 247 |  1854 |     border: 1px solid rgba(255,255,255,0.1);
 248 |  1855 |     border-radius: 10px;
 249 |  1856 |     padding: 15px 20px;
 250 |  1857 | }
 251 |  1858 | 
 252 |  1859 | .globe-stat-row {
 253 |  1860 |     display: flex;
 254 |  1861 |     align-items: center;
 255 |  1862 |     gap: 10px;
 256 |  1863 |     margin-bottom: 8px;
 257 |  1864 | }
 258 |  1865 | 
 259 |  1866 | .globe-stat-row:last-child {
 260 |  1867 |     margin-bottom: 0;
 261 |  1868 | }
 262 |  1869 | 
 263 |  1870 | .globe-stat-icon {
 264 |  1871 |     color: #f7931a;
 265 |  1872 |     width: 20px;
 266 |  1873 | }
 267 |  1874 | 
 268 |  1875 | .globe-stat-label {
 269 |  1876 |     font-size: 0.7rem;
 270 |  1877 |     color: rgba(255,255,255,0.5);
 271 |  1878 | }
 272 |  1879 | 
 273 |  1880 | .globe-stat-value {
 274 |  1881 |     font-family: 'JetBrains Mono', monospace;
 275 |  1882 |     font-size: 0.9rem;
 276 |  1883 |     color: white;
 277 |  1884 | }
 278 |  1885 | 
 279 |  1886 | .globe-controls {
 280 |  1887 |     position: absolute;
 281 |  1888 |     top: 15px;
 282 |  1889 |     right: 15px;
 283 |  1890 |     display: flex;
 284 |  1891 |     gap: 8px;
 285 |  1892 | }
 286 |  1893 | 
 287 |  1894 | .globe-control-btn {
 288 |  1895 |     width: 36px;
 289 |  1896 |     height: 36px;
 290 |  1897 |     background: rgba(0,0,0,0.6);
 291 |  1898 |     border: 1px solid rgba(255,255,255,0.2);
 292 |  1899 |     border-radius: 8px;
 293 |  1900 |     color: white;
 294 |  1901 |     cursor: pointer;
 295 |  1902 |     display: flex;
 296 |  1903 |     align-items: center;
 297 |  1904 |     justify-content: center;
 298 |  1905 |     transition: all 0.2s;
 299 |  1906 | }
 300 |  1907 | 
 301 |  1908 | .globe-control-btn:hover {
 302 |  1909 |     background: rgba(247, 147, 26, 0.3);
 303 |  1910 |     border-color: #f7931a;
 304 |  1911 | }
 305 |  1912 | 
 306 |  1913 | /* SOVEREIGNTY CALCULATOR */
 307 |  1914 | .calc-container {
 308 |  1915 |     background: rgba(0,0,0,0.4);
 309 |  1916 |     border-radius: 12px;
 310 |  1917 |     padding: 25px;
 311 |  1918 | }
 312 |  1919 | 
 313 |  1920 | .calc-inputs {
 314 | 
 315 | ============================================================
 316 | === VISUALIZER CANVAS CSS (lines 3020-3100 of 9534) ===
 317 | ============================================================
 318 | 
 319 |  3020 |     pointer-events: none !important;
 320 |  3021 | }
 321 |  3022 | 
 322 |  3023 | /* VISUALIZER MUST RECEIVE ALL MOUSE EVENTS */
 323 |  3024 | #visualizer-container {
 324 |  3025 |     z-index: 10 !important;
 325 |  3026 |     pointer-events: auto !important;
 326 |  3027 | }
 327 |  3028 | 
 328 |  3029 | #visualizer-canvas {
 329 |  3030 |     pointer-events: auto !important;
 330 |  3031 | }
 331 |  3032 | 
 332 |  3033 | /* VIDEO MUST NOT BLOCK CLICKS */
 333 |  3034 | #pulse-bg-video {
 334 |  3035 |     pointer-events: none !important;
 335 |  3036 | }
 336 |  3037 | 
 337 |  3038 | .terminal-container {
 338 |  3039 |     position: relative;
 339 |  3040 |     width: 100%;
 340 |  3041 |     min-height: auto;
 341 |  3042 |     background: transparent;
 342 |  3043 |     overflow: hidden;
 343 |  3044 | }
 344 |  3045 | 
 345 |  3046 | /* LIVE TERMINAL PAGE SPECIFIC - Video Background */
 346 |  3047 | .pulse-video-background {
 347 |  3048 |     position: fixed;
 348 |  3049 |     inset: 0;
 349 |  3050 |     z-index: -2;
 350 |  3051 |     overflow: hidden;
 351 |  3052 |     pointer-events: none;
 352 |  3053 | }
 353 |  3054 | 
 354 |  3055 | #pulse-bg-video {
 355 |  3056 |     width: 100%;
 356 |  3057 |     height: 100%;
 357 |  3058 |     object-fit: cover;
 358 |  3059 |     display: block;
 359 |  3060 | }
 360 |  3061 | 
 361 |  3062 | /* Transparent containers for video visibility - ONLY on this page */
 362 |  3063 | .terminal-container,
 363 |  3064 | .visualizer-container,
 364 |  3065 | #visualizer-container,
 365 |  3066 | #visualizer-canvas {
 366 |  3067 |     background: transparent !important;
 367 |  3068 |     background-color: transparent !important;
 368 |  3069 | }
 369 |  3070 | 
 370 |  3071 | /* Kill any pseudo-element overlays */
 371 |  3072 | .terminal-container::before,
 372 |  3073 | .terminal-container::after,
 373 |  3074 | .visualizer-container::before,
 374 |  3075 | .visualizer-container::after {
 375 |  3076 |     display: none !important;
 376 |  3077 | }
 377 |  3078 | 
 378 |  3079 | /* Visualizer canvas must sit above the video */
 379 |  3080 | .visualizer-container,
 380 |  3081 | #visualizer-canvas {
 381 |  3082 |     position: relative;
 382 |  3083 |     z-index: 1;
 383 |  3084 | }
 384 |  3085 | 
 385 |  3086 | .back-nav {
 386 |  3087 |     position: fixed;
 387 |  3088 |     top: 80px;
 388 |  3089 |     left: 20px;
 389 |  3090 |     z-index: 1000;
 390 |  3091 | }
 391 |  3092 | 
 392 |  3093 | .back-btn {
 393 |  3094 |     display: inline-flex;
 394 |  3095 |     align-items: center;
 395 |  3096 |     gap: 10px;
 396 |  3097 |     background: var(--pp-glass);
 397 |  3098 |     border: 1px solid rgba(247, 147, 26, 0.3);
 398 |  3099 |     border-radius: 12px;
 399 |  3100 |     padding: 12px 20px;
 400 | 
 401 | ============================================================
 402 | === HTML STRUCTURE (Zones, Canvas, Status Bar) (lines 4507-4620 of 9534) ===
 403 | ============================================================
 404 | 
 405 |  4507 | </style>
 406 |  4508 | {% endblock %}
 407 |  4509 | 
 408 |  4510 | {% block content %}
 409 |  4511 | <!-- Whale Alert Banner -->
 410 |  4512 | <div id="whale-alert-banner"></div>
 411 |  4513 | 
 412 |  4514 | <nav class="back-nav">
 413 |  4515 |     <a href="/" class="back-btn">
 414 |  4516 |         <i class="fas fa-arrow-left"></i>
 415 |  4517 |         <span>Back to Home</span>
 416 |  4518 |     </a>
 417 |  4519 | </nav>
 418 |  4520 | 
 419 |  4521 | <!-- Mobile TX Popup Card (outside terminal-container for proper z-index) -->
 420 |  4522 | <div class="tx-popup-overlay" id="tx-popup-overlay" onclick="closeTxPopup()"></div>
 421 |  4523 | <div class="tx-popup-card" id="tx-popup-card">
 422 |  4524 |     <button class="tx-popup-close" onclick="closeTxPopup()">&times;</button>
 423 |  4525 |     <div class="tx-popup-header">Transaction Details</div>
 424 |  4526 |     <div class="tx-popup-amount" id="tx-popup-amount">0.0000 BTC</div>
 425 |  4527 |     <div class="tx-popup-fiat" id="tx-popup-fiat">~$0.00 USD</div>
 426 |  4528 |     <div class="tx-popup-txid">
 427 |  4529 |         <div class="tx-popup-txid-label">Transaction ID</div>
 428 |  4530 |         <div class="tx-popup-txid-value" id="tx-popup-txid">...</div>
 429 |  4531 |     </div>
 430 |  4532 |     <div class="tx-popup-meta">
 431 |  4533 |         <div class="tx-popup-meta-item">
 432 |  4534 |             <div class="tx-popup-meta-label">Fee Rate</div>
 433 |  4535 |             <div class="tx-popup-meta-value" id="tx-popup-fee">-- sat/vB</div>
 434 |  4536 |         </div>
 435 |  4537 |         <div class="tx-popup-meta-item">
 436 |  4538 |             <div class="tx-popup-meta-label">Status</div>
 437 |  4539 |             <div class="tx-popup-meta-value" style="color: #eab308;">Unconfirmed</div>
 438 |  4540 |         </div>
 439 |  4541 |     </div>
 440 |  4542 |     <button type="button" class="tx-popup-verify" id="tx-popup-verify">
 441 |  4543 |         <i class="fas fa-external-link-alt"></i>Verify on Mempool.space
 442 |  4544 |     </button>
 443 |  4545 | </div>
 444 |  4546 | 
 445 |  4547 | 
 446 |  4548 | <!-- ============================================
 447 |  4549 |      ZONE 1: TACTICAL HORIZON
 448 |  4550 |      The Cinematic Hook - Pure Visualizer Experience
 449 |  4551 |      ============================================ -->
 450 |  4552 | <div class="zone-tactical-horizon">
 451 |  4553 |     <!-- Sovereign Status Bar - Inside Zone 1 -->
 452 |  4554 |     <div class="sovereign-status-bar zone-status">
 453 |  4555 |         <div class="container d-flex justify-content-around align-items-center">
 454 |  4556 |             <!-- Bitcoin Heartbeat Audio Indicator - Subtle World-Class Touch -->
 455 |  4557 |             <div class="heartbeat-audio-indicator" id="heartbeat-indicator" onclick="toggleHeartbeatAudio()" title="Toggle Bitcoin Heartbeat">
 456 |  4558 |                 <div class="heartbeat-pulse-ring"></div>
 457 |  4559 |                 <div class="heartbeat-icon">
 458 |  4560 |                     <i class="fas fa-heart"></i>
 459 |  4561 |                 </div>
 460 |  4562 |                 <div class="heartbeat-waveform">
 461 |  4563 |                     <span class="wave-bar"></span>
 462 |  4564 |                     <span class="wave-bar"></span>
 463 |  4565 |                     <span class="wave-bar"></span>
 464 |  4566 |                     <span class="wave-bar"></span>
 465 |  4567 |                     <span class="wave-bar"></span>
 466 |  4568 |                 </div>
 467 |  4569 |             </div>
 468 |  4570 | 
 469 |  4571 |             <div class="status-metric">
 470 |  4572 |                 <span class="status-label">Sats/vB</span>
 471 |  4573 |                 <span class="status-value highlight data-mono" id="status-fee-rate">--</span>
 472 |  4574 |             </div>
 473 |  4575 |             <div class="status-metric rec-indicator">
 474 |  4576 |                 <span class="rec-dot"></span>
 475 |  4577 |                 <span class="status-label">Hashrate</span>
 476 |  4578 |                 <span class="status-value data-mono" id="status-hashrate">-- EH/s</span>
 477 |  4579 |             </div>
 478 |  4580 |             <div class="status-metric">
 479 |  4581 |                 <span class="status-label">Blocks to Retarget</span>
 480 |  4582 |                 <span class="status-value data-mono" id="status-retarget">--</span>
 481 |  4583 |             </div>
 482 |  4584 |         </div>
 483 |  4585 |     </div>
 484 |  4586 | 
 485 |  4587 |     <div id="live-terminal-wrapper" style="position: relative; width: 100%; aspect-ratio: 16/9; overflow: hidden; background-color: black;">
 486 |  4588 |     <!-- Video Background - ABSOLUTE positioned behind visualizer, pushed down so TXIDs float above platform -->
 487 |  4589 |     <video autoplay muted loop playsinline id="pulse-bg-video"
 488 |  4590 |            style="position: absolute; top: 15%; left: 50%; transform: translateX(-50%); width: 100%; height: 100%; object-fit: cover; z-index: 0; filter: brightness(0.6);">
 489 |  4591 |         <source src="/static/video/pulse-bg.mp4" type="video/mp4">
 490 |  4592 |     </video>
 491 |  4593 | 
 492 |  4594 |     <!-- Gradient Fade: Header into Video (top) -->
 493 |  4595 |     <div class="video-fade-top"></div>
 494 |  4596 | 
 495 |  4597 |     <!-- Gradient Fade: Video into Footer/Dashboard (bottom) -->
 496 |  4598 |     <div class="video-fade-bottom"></div>
 497 |  4599 | 
 498 |  4600 |     <!-- Custom Blockchain Visualizer - ABSOLUTE positioned above video -->
 499 |  4601 |     <div class="visualizer-container" id="visualizer-container"
 500 |  4602 |          style="position: absolute; top: 80px; left: 0; width: 100%; height: calc(100% - 80px); z-index: 1; background: transparent !important;">
 501 |  4603 |         <canvas id="visualizer-canvas" style="background: transparent !important;"></canvas>
 502 |  4604 |     </div>
 503 |  4605 | 
 504 |  4606 |     <!-- Live Network Status HUD - INSIDE wrapper so it doesn't scroll with page -->
 505 |  4607 |     <div class="terminal-hud">
 506 |  4608 |         <div class="hud-title">Live Network Status</div>
 507 |  4609 | 
 508 |  4610 |         <div class="hud-metric">
 509 |  4611 |             <span class="metric-label">Mempool Size</span>
 510 |  4612 |             <span class="metric-value" id="mempool-size">Loading...</span>
 511 |  4613 |         </div>
 512 |  4614 | 
 513 |  4615 |         <div class="hud-metric">
 514 |  4616 |             <span class="metric-label">Pending TXs</span>
 515 |  4617 |             <span class="metric-value" id="pending-txs">--</span>
 516 |  4618 |         </div>
 517 |  4619 | 
 518 |  4620 |         <div class="hud-metric">
 519 | 
 520 | ============================================================
 521 | === ZONE LOGIC ENGINE HTML (lines 4728-4830 of 9534) ===
 522 | ============================================================
 523 | 
 524 |  4728 | <section class="zone-logic-engine">
 525 |  4729 |     <div class="container">
 526 |  4730 |         <div class="dashboard-grid" id="dashboard-grid">
 527 |  4731 | 
 528 |  4732 | <!-- SOVEREIGN HEALTH HUD - First Grid Item -->
 529 |  4733 | <div class="instrument-panel" id="panel-sovereign-health" style="grid-column: span 2;">
 530 |  4734 |         <div class="module-header" style="margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05);">
 531 |  4735 |             <div class="module-icon" style="background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); color: #dc2626;"><i class="fas fa-heartbeat"></i></div>
 532 |  4736 |             <div>
 533 |  4737 |                 <h3 class="module-title">Sovereign Health</h3>
 534 |  4738 |                 <p class="module-subtitle">Real-time Network Vitals</p>
 535 |  4739 |             </div>
 536 |  4740 |         </div>
 537 |  4741 | 
 538 |  4742 |         <div class="row">
 539 |  4743 |             <div class="col-md-5">
 540 |  4744 |                 <div class="pulse-heartbeat">
 541 |  4745 |                     <div class="heartbeat-visual">
 542 |  4746 |                         <div class="heartbeat-ring"></div>
 543 |  4747 |                         <div class="heartbeat-ring"></div>
 544 |  4748 |                         <div class="heartbeat-core"></div>
 545 |  4749 |                     </div>
 546 |  4750 |                     <div class="heartbeat-info">
 547 |  4751 |                         <div class="heartbeat-label">Network Heartbeat</div>
 548 |  4752 |                         <div class="heartbeat-value" id="health-block-time">9:42</div>
 549 |  4753 |                         <span class="heartbeat-status normal" id="health-status">On Schedule</span>
 550 |  4754 |                         <div class="variance-alert" id="variance-alert" style="display: none;">
 551 |  4755 |                             <div class="variance-alert-badge"><i class="fas fa-broadcast-tower"></i> SIGNAL</div>
 552 |  4756 |                             <div class="variance-alert-text">High Variance Detected. The Poisson tail is lengthening. Block crystallization remains secure but delayed.</div>
 553 |  4757 |                         </div>
 554 |  4758 |                     </div>
 555 |  4759 |                 </div>
 556 |  4760 |             </div>
 557 |  4761 |             <div class="col-md-7">
 558 |  4762 |                 <div class="fee-friction-calc">
 559 |  4763 |                     <div class="fee-friction-header">
 560 |  4764 |                         <span class="fee-friction-title">Cost of Absolute Finality</span>
 561 |  4765 |                         <span class="fee-friction-label">Fee-Friction Calculator</span>
 562 |  4766 |                     </div>
 563 |  4767 |                     <div class="fee-scale">
 564 |  4768 |                         <div class="fee-tier">
 565 |  4769 |                             <div class="fee-tier-label">Economy</div>
 566 |  4770 |                             <div class="fee-tier-value low" id="fee-economy">1</div>
 567 |  4771 |                             <div class="fee-tier-time">~60 min</div>
 568 |  4772 |                         </div>
 569 |  4773 |                         <div class="fee-tier">
 570 |  4774 |                             <div class="fee-tier-label">Standard</div>
 571 |  4775 |                             <div class="fee-tier-value medium" id="fee-standard">3</div>
 572 |  4776 |                             <div class="fee-tier-time">~30 min</div>
 573 |  4777 |                         </div>
 574 |  4778 |                         <div class="fee-tier">
 575 |  4779 |                             <div class="fee-tier-label">Priority</div>
 576 |  4780 |                             <div class="fee-tier-value high" id="fee-priority">5</div>
 577 |  4781 |                             <div class="fee-tier-time">~10 min</div>
 578 |  4782 |                         </div>
 579 |  4783 |                         <div class="fee-tier">
 580 |  4784 |                             <div class="fee-tier-label">Urgent</div>
 581 |  4785 |                             <div class="fee-tier-value urgent" id="fee-urgent">8</div>
 582 |  4786 |                             <div class="fee-tier-time">Next Block</div>
 583 |  4787 |                         </div>
 584 |  4788 |                     </div>
 585 |  4789 |                     <div class="finality-cost">
 586 |  4790 |                         <div class="finality-label">Avg. Finality Cost (140 vB TX)</div>
 587 |  4791 |                         <div class="finality-value" id="finality-cost">~$0.45</div>
 588 |  4792 |                     </div>
 589 |  4793 |                 </div>
 590 |  4794 |             </div>
 591 |  4795 |         </div>
 592 |  4796 | </div><!-- END panel-sovereign-health -->
 593 |  4797 | 
 594 |  4798 | <!-- NODE GLOBE - Dashboard Grid Item -->
 595 |  4799 | <div class="instrument-panel" id="panel-node-globe" style="grid-column: span 2;">
 596 |  4800 |     <div class="node-globe-showcase" style="background: linear-gradient(180deg, rgba(0, 20, 60, 0.95) 0%, rgba(0, 10, 30, 0.98) 100%); border: 2px solid rgba(59, 130, 246, 0.4); border-radius: 20px; padding: 0; overflow: hidden; position: relative;">
 597 |  4801 |         <!-- Animated star field background -->
 598 |  4802 |         <div class="globe-starfield" style="position: absolute; inset: 0; overflow: hidden; pointer-events: none;">
 599 |  4803 |             <div class="star" style="top: 10%; left: 20%; animation-delay: 0s;"></div>
 600 |  4804 |             <div class="star" style="top: 30%; left: 80%; animation-delay: 1s;"></div>
 601 |  4805 |             <div class="star" style="top: 60%; left: 15%; animation-delay: 2s;"></div>
 602 |  4806 |             <div class="star" style="top: 80%; left: 70%; animation-delay: 0.5s;"></div>
 603 |  4807 |             <div class="star" style="top: 45%; left: 50%; animation-delay: 1.5s;"></div>
 604 |  4808 |         </div>
 605 |  4809 | 
 606 |  4810 |         <div class="module-header" style="padding: 25px 30px 15px; border-bottom: 1px solid rgba(59, 130, 246, 0.2);">
 607 |  4811 |             <div class="module-icon" style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(59, 130, 246, 0.1) 100%); border: 2px solid rgba(59, 130, 246, 0.5); color: #3b82f6; width: 50px; height: 50px; font-size: 1.3rem;">
 608 |  4812 |                 <i class="fas fa-globe-americas"></i>
 609 |  4813 |             </div>
 610 |  4814 |             <div>
 611 |  4815 |                 <h3 class="module-title" style="color: #3b82f6; font-size: 1.5rem; letter-spacing: 2px;">NODE GLOBE</h3>
 612 |  4816 |                 <p class="module-subtitle" style="color: rgba(255,255,255,0.6);">Bitcoin's Decentralized Nervous System</p>
 613 |  4817 |             </div>
 614 |  4818 |         </div>
 615 |  4819 | 
 616 |  4820 |         <div class="globe-main-container" style="display: flex; flex-wrap: wrap; min-height: 550px;">
 617 |  4821 |             <!-- Globe visualization -->
 618 |  4822 |             <div class="globe-visual-area" style="flex: 2; min-width: 300px; position: relative; display: flex; flex-direction: column;">
 619 |  4823 |                 <div class="globe-container" id="node-globe" style="height: 480px; flex-shrink: 0;">
 620 |  4824 |                     <div class="globe-controls" style="position: absolute; top: 15px; right: 15px; z-index: 10;">
 621 |  4825 |                         <button class="globe-control-btn" onclick="resetGlobeRotation()" title="Reset View" style="background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); color: #3b82f6;">
 622 |  4826 |                             <i class="fas fa-sync-alt"></i>
 623 |  4827 |                         </button>
 624 |  4828 |                         <button class="globe-control-btn" onclick="toggleGlobeAutoRotate()" title="Auto-Rotate" style="background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); color: #3b82f6;">
 625 |  4829 |                             <i class="fas fa-redo"></i>
 626 |  4830 |                         </button>
 627 | 
 628 | ============================================================
 629 | === NODE GLOBE HTML (lines 4798-4850 of 9534) ===
 630 | ============================================================
 631 | 
 632 |  4798 | <!-- NODE GLOBE - Dashboard Grid Item -->
 633 |  4799 | <div class="instrument-panel" id="panel-node-globe" style="grid-column: span 2;">
 634 |  4800 |     <div class="node-globe-showcase" style="background: linear-gradient(180deg, rgba(0, 20, 60, 0.95) 0%, rgba(0, 10, 30, 0.98) 100%); border: 2px solid rgba(59, 130, 246, 0.4); border-radius: 20px; padding: 0; overflow: hidden; position: relative;">
 635 |  4801 |         <!-- Animated star field background -->
 636 |  4802 |         <div class="globe-starfield" style="position: absolute; inset: 0; overflow: hidden; pointer-events: none;">
 637 |  4803 |             <div class="star" style="top: 10%; left: 20%; animation-delay: 0s;"></div>
 638 |  4804 |             <div class="star" style="top: 30%; left: 80%; animation-delay: 1s;"></div>
 639 |  4805 |             <div class="star" style="top: 60%; left: 15%; animation-delay: 2s;"></div>
 640 |  4806 |             <div class="star" style="top: 80%; left: 70%; animation-delay: 0.5s;"></div>
 641 |  4807 |             <div class="star" style="top: 45%; left: 50%; animation-delay: 1.5s;"></div>
 642 |  4808 |         </div>
 643 |  4809 | 
 644 |  4810 |         <div class="module-header" style="padding: 25px 30px 15px; border-bottom: 1px solid rgba(59, 130, 246, 0.2);">
 645 |  4811 |             <div class="module-icon" style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(59, 130, 246, 0.1) 100%); border: 2px solid rgba(59, 130, 246, 0.5); color: #3b82f6; width: 50px; height: 50px; font-size: 1.3rem;">
 646 |  4812 |                 <i class="fas fa-globe-americas"></i>
 647 |  4813 |             </div>
 648 |  4814 |             <div>
 649 |  4815 |                 <h3 class="module-title" style="color: #3b82f6; font-size: 1.5rem; letter-spacing: 2px;">NODE GLOBE</h3>
 650 |  4816 |                 <p class="module-subtitle" style="color: rgba(255,255,255,0.6);">Bitcoin's Decentralized Nervous System</p>
 651 |  4817 |             </div>
 652 |  4818 |         </div>
 653 |  4819 | 
 654 |  4820 |         <div class="globe-main-container" style="display: flex; flex-wrap: wrap; min-height: 550px;">
 655 |  4821 |             <!-- Globe visualization -->
 656 |  4822 |             <div class="globe-visual-area" style="flex: 2; min-width: 300px; position: relative; display: flex; flex-direction: column;">
 657 |  4823 |                 <div class="globe-container" id="node-globe" style="height: 480px; flex-shrink: 0;">
 658 |  4824 |                     <div class="globe-controls" style="position: absolute; top: 15px; right: 15px; z-index: 10;">
 659 |  4825 |                         <button class="globe-control-btn" onclick="resetGlobeRotation()" title="Reset View" style="background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); color: #3b82f6;">
 660 |  4826 |                             <i class="fas fa-sync-alt"></i>
 661 |  4827 |                         </button>
 662 |  4828 |                         <button class="globe-control-btn" onclick="toggleGlobeAutoRotate()" title="Auto-Rotate" style="background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); color: #3b82f6;">
 663 |  4829 |                             <i class="fas fa-redo"></i>
 664 |  4830 |                         </button>
 665 |  4831 |                     </div>
 666 |  4832 |                     <!-- Mobile Zoom Controls -->
 667 |  4833 |                     <div class="globe-zoom-controls" id="globe-zoom-controls">
 668 |  4834 |                         <button class="globe-zoom-btn" onclick="event.preventDefault(); event.stopPropagation(); globeZoomIn(); return false;" title="Zoom In">
 669 |  4835 |                             <i class="fas fa-search-plus"></i>
 670 |  4836 |                         </button>
 671 |  4837 |                         <button class="globe-zoom-btn" onclick="event.preventDefault(); event.stopPropagation(); globeZoomOut(); return false;" title="Zoom Out">
 672 |  4838 |                             <i class="fas fa-search-minus"></i>
 673 |  4839 |                         </button>
 674 |  4840 |                     </div>
 675 |  4841 |                     <!-- Node tooltip -->
 676 |  4842 |                     <div id="node-tooltip" class="node-tooltip" style="display: none; position: absolute; background: rgba(0,0,0,0.95); border: 1px solid rgba(59, 130, 246, 0.6); border-radius: 8px; padding: 12px; pointer-events: none; z-index: 100; min-width: 200px; box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);">
 677 |  4843 |                         <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #3b82f6; margin-bottom: 6px;">NODE INTEL</div>
 678 |  4844 |                         <div id="node-tooltip-content"></div>
 679 |  4845 |                     </div>
 680 |  4846 |                 </div>
 681 |  4847 | 
 682 |  4848 |                 <!-- ROTATING AD BANNER - Under the globe in blue area -->
 683 |  4849 |                 <div style="border-top: 1px solid rgba(59, 130, 246, 0.3); padding: 15px; text-align: center; min-height: 100px; display: flex; align-items: center; justify-content: center;">
 684 |  4850 |                     <div id="globe-ad-container">
 685 | 
 686 | ============================================================
 687 | === ZONE SOVEREIGN ARCHIVE HTML (lines 5206-5300 of 9534) ===
 688 | ============================================================
 689 | 
 690 |  5206 | <section class="zone-sovereign-archive">
 691 |  5207 |     <div class="container">
 692 |  5208 | 
 693 |  5209 | <!-- SOVEREIGNTY CALCULATOR - HIDDEN (moved to Pulse Intel Grid) -->
 694 |  5210 | <div class="archive-folder collapsed" id="folder-calculator" style="display: none;">
 695 |  5211 |     <div class="archive-folder-header" onclick="toggleArchiveFolder(this.parentElement)">
 696 |  5212 |         <div class="archive-folder-title">
 697 |  5213 |             <i class="fas fa-calculator"></i>
 698 |  5214 |             <span>Sovereignty Calculator</span>
 699 |  5215 |             <span style="color: rgba(255,255,255,0.3); font-size: 0.65rem; margin-left: 10px;">DCA Strategy Tool</span>
 700 |  5216 |         </div>
 701 |  5217 |         <i class="fas fa-chevron-down archive-folder-toggle"></i>
 702 |  5218 |     </div>
 703 |  5219 |     <div class="archive-folder-content">
 704 |  5220 |     <div class="sovereignty-calc-showcase" style="background: linear-gradient(180deg, rgba(0, 30, 20, 0.95) 0%, rgba(0, 15, 10, 0.98) 100%); border: 2px solid rgba(34, 197, 94, 0.4); border-radius: 20px; overflow: hidden;">
 705 |  5221 |         <div class="module-header" style="padding: 25px 30px; border-bottom: 1px solid rgba(34, 197, 94, 0.2);">
 706 |  5222 |             <div style="display: flex; align-items: center; gap: 15px;">
 707 |  5223 |                 <div style="width: 55px; height: 55px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.3) 0%, rgba(34, 197, 94, 0.1) 100%); border: 2px solid rgba(34, 197, 94, 0.5); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
 708 |  5224 |                     <i class="fas fa-calculator" style="font-size: 1.4rem; color: #22c55e;"></i>
 709 |  5225 |                 </div>
 710 |  5226 |                 <div>
 711 |  5227 |                     <h3 style="font-size: 1.4rem; font-weight: 800; color: #22c55e; text-transform: uppercase; letter-spacing: 2px; margin: 0;">Sovereignty Calculator</h3>
 712 |  5228 |                     <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 5px 0 0;">What If You'd Stacked?</p>
 713 |  5229 |                 </div>
 714 |  5230 |             </div>
 715 |  5231 |         </div>
 716 |  5232 | 
 717 |  5233 |         <div style="padding: 25px 30px;">
 718 |  5234 |             <!-- Input Controls -->
 719 |  5235 |             <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-bottom: 25px;">
 720 |  5236 |                 <div>
 721 |  5237 |                     <label style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 8px;">Amount ($)</label>
 722 |  5238 |                     <input type="number" id="calc-amount" value="50" min="1" style="width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 8px; padding: 12px 15px; color: #22c55e; font-size: 1.2rem; font-family: 'JetBrains Mono', monospace;">
 723 |  5239 |                 </div>
 724 |  5240 |                 <div>
 725 |  5241 |                     <label style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 8px;">Frequency</label>
 726 |  5242 |                     <select id="calc-frequency" onchange="calculateDCA()" style="width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 8px; padding: 12px 15px; color: #22c55e; font-size: 1rem;">
 727 |  5243 |                         <option value="daily">Daily</option>
 728 |  5244 |                         <option value="weekly" selected>Weekly</option>
 729 |  5245 |                         <option value="monthly">Monthly</option>
 730 |  5246 |                     </select>
 731 |  5247 |                 </div>
 732 |  5248 |                 <div>
 733 |  5249 |                     <label style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 8px;">Start Date</label>
 734 |  5250 |                     <input type="date" id="calc-start-date" value="2021-01-01" style="width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 8px; padding: 12px 15px; color: #22c55e; font-size: 1rem;">
 735 |  5251 |                 </div>
 736 |  5252 |             </div>
 737 |  5253 | 
 738 |  5254 |             <!-- Preset Buttons -->
 739 |  5255 |             <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 30px;">
 740 |  5256 |                 <button onclick="setCalcPreset('inception', event)" style="background: linear-gradient(135deg, rgba(247, 147, 26, 0.4) 0%, rgba(247, 147, 26, 0.15) 100%); border: 1px solid rgba(247, 147, 26, 0.6); color: #f7931a; padding: 10px 18px; border-radius: 8px; font-size: 0.8rem; cursor: pointer; transition: all 0.3s; font-weight: 600;">
 741 |  5257 |                     <i class="fas fa-star me-1"></i> Since Inception
 742 |  5258 |                 </button>
 743 |  5259 |                 <button onclick="setCalcPreset('halving', event)" style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; padding: 10px 18px; border-radius: 8px; font-size: 0.8rem; cursor: pointer; transition: all 0.3s;">Since Last Halving</button>
 744 |  5260 |                 <button onclick="setCalcPreset('2020', event)" style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; padding: 10px 18px; border-radius: 8px; font-size: 0.8rem; cursor: pointer; transition: all 0.3s;">Since 2020</button>
 745 |  5261 |                 <button onclick="setCalcPreset('ath', event)" style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; padding: 10px 18px; border-radius: 8px; font-size: 0.8rem; cursor: pointer; transition: all 0.3s;">Since $69K Top</button>
 746 |  5262 |                 <button onclick="setCalcPreset('year', event)" style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; padding: 10px 18px; border-radius: 8px; font-size: 0.8rem; cursor: pointer; transition: all 0.3s;">Past Year</button>
 747 |  5263 |             </div>
 748 |  5264 | 
 749 |  5265 |             <!-- Results Grid -->
 750 |  5266 |             <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px;">
 751 |  5267 |                 <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 12px; padding: 20px; text-align: center;">
 752 |  5268 |                     <div style="font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Total Invested</div>
 753 |  5269 |                     <div id="calc-invested" style="font-size: 1.6rem; font-weight: 700; color: #f7931a; font-family: 'JetBrains Mono', monospace;">$10,400</div>
 754 |  5270 |                 </div>
 755 |  5271 |                 <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 12px; padding: 20px; text-align: center;">
 756 |  5272 |                     <div style="font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">BTC Accumulated</div>
 757 |  5273 |                     <div id="calc-btc" style="font-size: 1.6rem; font-weight: 700; color: #f7931a; font-family: 'JetBrains Mono', monospace;">0.2847 BTC</div>
 758 |  5274 |                 </div>
 759 |  5275 |                 <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 12px; padding: 20px; text-align: center;">
 760 |  5276 |                     <div style="font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Current Value</div>
 761 |  5277 |                     <div id="calc-value" style="font-size: 1.6rem; font-weight: 700; color: #22c55e; font-family: 'JetBrains Mono', monospace;">$28,470</div>
 762 |  5278 |                 </div>
 763 |  5279 |                 <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 20px; text-align: center;">
 764 |  5280 |                     <div style="font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Total Gain</div>
 765 |  5281 |                     <div id="calc-gain" style="font-size: 1.6rem; font-weight: 700; color: #22c55e; font-family: 'JetBrains Mono', monospace;">+173.8%</div>
 766 |  5282 |                 </div>
 767 |  5283 |             </div>
 768 |  5284 | 
 769 |  5285 |             <!-- Chart Area -->
 770 |  5286 |             <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(34, 197, 94, 0.15); border-radius: 12px; padding: 20px; height: 200px; position: relative;">
 771 |  5287 |                 <div style="position: absolute; top: 10px; left: 15px; font-size: 0.65rem; color: rgba(255,255,255,0.3); text-transform: uppercase; letter-spacing: 1px;">Portfolio Growth Over Time</div>
 772 |  5288 |                 <canvas id="stack-chart" style="width: 100%; height: 100%;"></canvas>
 773 |  5289 |             </div>
 774 |  5290 | 
 775 |  5291 |             <!-- Insight -->
 776 |  5292 |             <div style="margin-top: 20px; padding: 15px 20px; background: rgba(247, 147, 26, 0.08); border-left: 3px solid #f7931a; border-radius: 0 8px 8px 0;">
 777 |  5293 |                 <p style="margin: 0; font-size: 0.85rem; color: rgba(255,255,255,0.7); line-height: 1.6;">
 778 |  5294 |                     <i class="fas fa-lightbulb me-2" style="color: #f7931a;"></i>
 779 |  5295 |                     <strong style="color: #f7931a;">DCA Strategy:</strong> Dollar-cost averaging reduces timing risk by spreading purchases over time. This calculator uses historical Bitcoin prices to show what consistent stacking would have achieved.
 780 |  5296 |                 </p>
 781 |  5297 |             </div>
 782 |  5298 |         </div>
 783 |  5299 |     </div>
 784 |  5300 | </section>
 785 | 
 786 | ============================================================
 787 | === THREE.JS IMPORTS (lines 7099-7115 of 9534) ===
 788 | ============================================================
 789 | 
 790 |  7099 | <!-- Three.js Core -->
 791 |  7100 | <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
 792 |  7101 | <!-- Three.js Post-Processing -->
 793 |  7102 | <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/CopyShader.js"></script>
 794 |  7103 | <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/LuminosityHighPassShader.js"></script>
 795 |  7104 | <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/EffectComposer.js"></script>
 796 |  7105 | <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/RenderPass.js"></script>
 797 |  7106 | <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/ShaderPass.js"></script>
 798 |  7107 | <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/UnrealBloomPass.js"></script>
 799 |  7108 | 
 800 |  7109 | <script src="{{ url_for('static', filename='js/visualizer.js') }}?v=20260128h"></script>
 801 |  7110 | <script>
 802 |  7111 | // Ensure video plays on load
 803 |  7112 | window.addEventListener('DOMContentLoaded', () => {
 804 |  7113 |     const v = document.getElementById('pulse-bg-video');
 805 |  7114 |     if (!v) return;
 806 |  7115 | 
 807 | 
 808 | ============================================================
 809 | === STATUS BAR UPDATE (lines 7132-7200 of 9534) ===
 810 | ============================================================
 811 | 
 812 |  7132 | <script>
 813 |  7133 | // Update Sovereign Status Bar with live network intel
 814 |  7134 | async function updateSovereignStatusBar() {
 815 |  7135 |     try {
 816 |  7136 |         const [feesRes, hashrateRes, diffRes] = await Promise.all([
 817 |  7137 |             fetch('https://mempool.space/api/v1/fees/recommended'),
 818 |  7138 |             fetch('https://mempool.space/api/v1/mining/hashrate/1d'),
 819 |  7139 |             fetch('https://mempool.space/api/v1/difficulty-adjustment')
 820 |  7140 |         ]);
 821 |  7141 | 
 822 |  7142 |         const fees = await feesRes.json();
 823 |  7143 |         const hashrate = await hashrateRes.json();
 824 |  7144 |         const diff = await diffRes.json();
 825 |  7145 | 
 826 |  7146 |         // Fastest fee in sats/vB
 827 |  7147 |         document.getElementById('status-fee-rate').textContent = fees.fastestFee + ' sat/vB';
 828 |  7148 | 
 829 |  7149 |         // Hashrate in EH/s
 830 |  7150 |         if (hashrate.currentHashrate) {
 831 |  7151 |             const ehps = (hashrate.currentHashrate / 1e18).toFixed(2);
 832 |  7152 |             document.getElementById('status-hashrate').textContent = ehps + ' EH/s';
 833 |  7153 |         }
 834 |  7154 | 
 835 |  7155 |         // Blocks until difficulty retarget
 836 |  7156 |         if (diff.remainingBlocks !== undefined) {
 837 |  7157 |             document.getElementById('status-retarget').textContent = diff.remainingBlocks.toLocaleString();
 838 |  7158 |         }
 839 |  7159 | 
 840 |  7160 |         // Update Intel Strip - Difficulty (use current difficulty from API)
 841 |  7161 |         try {
 842 |  7162 |             const difficultyRes = await fetch('https://mempool.space/api/v1/mining/hashrate/3d');
 843 |  7163 |             const diffData = await difficultyRes.json();
 844 |  7164 |             if (diffData.currentDifficulty) {
 845 |  7165 |                 const diffT = (diffData.currentDifficulty / 1e12).toFixed(2);
 846 |  7166 |                 document.getElementById('intel-difficulty').textContent = diffT + ' T';
 847 |  7167 |             }
 848 |  7168 |         } catch (diffErr) {
 849 |  7169 |             console.log('Difficulty fetch error:', diffErr);
 850 |  7170 |         }
 851 |  7171 |     } catch (e) {
 852 |  7172 |         console.error('Status bar update error:', e);
 853 |  7173 |     }
 854 |  7174 | }
 855 |  7175 | 
 856 |  7176 | // Update Sovereign Intelligence Dashboard
 857 |  7177 | async function updateNetworkIntel() {
 858 |  7178 |     try {
 859 |  7179 |         const [lnRes, blocksRes, mempoolRes, hashrateRes] = await Promise.all([
 860 |  7180 |             fetch('https://mempool.space/api/v1/lightning/statistics/latest'),
 861 |  7181 |             fetch('https://mempool.space/api/blocks/tip/height'),
 862 |  7182 |             fetch('https://mempool.space/api/mempool'),
 863 |  7183 |             fetch('https://mempool.space/api/v1/mining/hashrate/1d')
 864 |  7184 |         ]);
 865 |  7185 | 
 866 |  7186 |         // Lightning Network capacity
 867 |  7187 |         const ln = await lnRes.json();
 868 |  7188 |         if (ln.latest && ln.latest.total_capacity) {
 869 |  7189 |             const btcCapacity = (ln.latest.total_capacity / 100000000).toLocaleString();
 870 |  7190 |             document.getElementById('intel-lightning').textContent = btcCapacity + ' BTC';
 871 |  7191 |         }
 872 |  7192 | 
 873 |  7193 |         // Block height and halving ETA
 874 |  7194 |         const currentHeight = await blocksRes.json();
 875 |  7195 |         document.getElementById('intel-height').textContent = '#' + currentHeight.toLocaleString();
 876 |  7196 | 
 877 |  7197 |         const nextHalving = 1050000;
 878 |  7198 |         const blocksRemaining = nextHalving - currentHeight;
 879 |  7199 |         const daysRemaining = Math.round((blocksRemaining * 10) / 1440);
 880 |  7200 |         document.getElementById('intel-halving').textContent = daysRemaining.toLocaleString() + ' days';
 881 | 
 882 | ============================================================
 883 | === MEMPOOL DATA FUNCTIONS (lines 7225-7310 of 9534) ===
 884 | ============================================================
 885 | 
 886 |  7225 | async function updateMempoolData() {
 887 |  7226 |     try {
 888 |  7227 |         const [mempoolRes, feesRes, blocksRes] = await Promise.all([
 889 |  7228 |             fetch('https://mempool.space/api/mempool'),
 890 |  7229 |             fetch('https://mempool.space/api/v1/fees/recommended'),
 891 |  7230 |             fetch('https://mempool.space/api/blocks')
 892 |  7231 |         ]);
 893 |  7232 | 
 894 |  7233 |         const mempool = await mempoolRes.json();
 895 |  7234 |         const fees = await feesRes.json();
 896 |  7235 |         const blocks = await blocksRes.json();
 897 |  7236 | 
 898 |  7237 |         const mempoolMB = (mempool.vsize / 1000000).toFixed(1);
 899 |  7238 |         const mempoolPercent = Math.min((mempool.vsize / 300000000) * 100, 100);
 900 |  7239 | 
 901 |  7240 |         document.getElementById('mempool-size').textContent = mempoolMB + ' vMB';
 902 |  7241 |         document.getElementById('pending-txs').textContent = mempool.count.toLocaleString();
 903 |  7242 |         document.getElementById('mempool-mb').textContent = mempoolMB + ' MB';
 904 |  7243 |         document.getElementById('mempool-bar').style.height = mempoolPercent + '%';
 905 |  7244 | 
 906 |  7245 |         const nextBlockFee = fees.fastestFee;
 907 |  7246 |         const feeEl = document.getElementById('next-block-fee');
 908 |  7247 |         feeEl.textContent = nextBlockFee + ' sat/vB';
 909 |  7248 |         feeEl.className = 'metric-value ' + (nextBlockFee < 10 ? 'fee-low' : nextBlockFee < 50 ? 'fee-medium' : 'fee-high');
 910 |  7249 | 
 911 |  7250 |         document.getElementById('low-fee').textContent = fees.hourFee + ' sat/vB';
 912 |  7251 | 
 913 |  7252 |         // Update heatmap elements
 914 |  7253 |         const heatmapTotalTxs = document.getElementById('heatmap-total-txs');
 915 |  7254 |         if (heatmapTotalTxs) heatmapTotalTxs.textContent = mempool.count.toLocaleString();
 916 |  7255 | 
 917 |  7256 |         const heatmapMedianFee = document.querySelectorAll('#heatmap-median-fee');
 918 |  7257 |         const medianFee = Math.round((fees.fastestFee + fees.hourFee) / 2);
 919 |  7258 |         heatmapMedianFee.forEach(el => el.textContent = medianFee + ' sat/vB');
 920 |  7259 | 
 921 |  7260 |         // Update fee distribution grid from histogram
 922 |  7261 |         if (mempool.fee_histogram && mempool.fee_histogram.length > 0) {
 923 |  7262 |             const histogram = mempool.fee_histogram;
 924 |  7263 |             let fee1_5 = 0, fee5_10 = 0, fee10_20 = 0, fee20_50 = 0, fee50 = 0;
 925 |  7264 |             histogram.forEach(([feeRate, vsize]) => {
 926 |  7265 |                 if (feeRate <= 5) fee1_5 += Math.round(vsize / 1000);
 927 |  7266 |                 else if (feeRate <= 10) fee5_10 += Math.round(vsize / 1000);
 928 |  7267 |                 else if (feeRate <= 20) fee10_20 += Math.round(vsize / 1000);
 929 |  7268 |                 else if (feeRate <= 50) fee20_50 += Math.round(vsize / 1000);
 930 |  7269 |                 else fee50 += Math.round(vsize / 1000);
 931 |  7270 |             });
 932 |  7271 |             const updateGridFee = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val > 999 ? (val/1000).toFixed(1) + 'k' : val; };
 933 |  7272 |             updateGridFee('grid-fee-1-5', fee1_5);
 934 |  7273 |             updateGridFee('grid-fee-5-10', fee5_10);
 935 |  7274 |             updateGridFee('grid-fee-10-20', fee10_20);
 936 |  7275 |             updateGridFee('grid-fee-20-50', fee20_50);
 937 |  7276 |             updateGridFee('grid-fee-50', fee50);
 938 |  7277 |             updateGridFee('fee-1-5-count', fee1_5);
 939 |  7278 |             updateGridFee('fee-5-10-count', fee5_10);
 940 |  7279 |             updateGridFee('fee-10-20-count', fee10_20);
 941 |  7280 |             updateGridFee('fee-20-30-count', Math.round(fee20_50 * 0.6));
 942 |  7281 |             updateGridFee('fee-30-50-count', Math.round(fee20_50 * 0.4));
 943 |  7282 |             updateGridFee('fee-50-100-count', Math.round(fee50 * 0.7));
 944 |  7283 |             updateGridFee('fee-100-count', Math.round(fee50 * 0.3));
 945 |  7284 |         }
 946 |  7285 | 
 947 |  7286 |         if (blocks.length > 0) {
 948 |  7287 |             const latest = blocks[0];
 949 |  7288 |             document.getElementById('block-height').textContent = '#' + latest.height.toLocaleString();
 950 |  7289 | 
 951 |  7290 |             const blockTime = new Date(latest.timestamp * 1000);
 952 |  7291 |             const now = new Date();
 953 |  7292 |             const minAgo = Math.floor((now - blockTime) / 60000);
 954 |  7293 |             document.getElementById('block-time').textContent = minAgo + ' min ago';
 955 |  7294 | 
 956 |  7295 |             document.getElementById('block-txs').textContent = latest.tx_count.toLocaleString();
 957 |  7296 |             document.getElementById('block-size').textContent = (latest.size / 1000000).toFixed(2) + ' MB';
 958 |  7297 |         }
 959 |  7298 | 
 960 |  7299 |         if (nextBlockFee <= 5) {
 961 |  7300 |             checkAndNotifyLowFees(nextBlockFee);
 962 |  7301 |         }
 963 |  7302 | 
 964 |  7303 |     } catch (error) {
 965 |  7304 |         console.error('Mempool data fetch error:', error);
 966 |  7305 |         document.getElementById('connection-status').textContent = 'Reconnecting...';
 967 |  7306 |     }
 968 |  7307 | }
 969 |  7308 | 
 970 |  7309 | function checkAndNotifyLowFees(fee) {
 971 |  7310 |     if ('Notification' in window && Notification.permission === 'granted') {
 972 | 
 973 | ============================================================
 974 | === SETTLEMENT PULSE (lines 7394-7425 of 9534) ===
 975 | ============================================================
 976 | 
 977 |  7394 |             fetch('https://mempool.space/api/blocks'),
 978 |  7395 |             fetch('https://mempool.space/api/v1/fees/recommended'),
 979 |  7396 |             fetch('https://mempool.space/api/mempool'),
 980 |  7397 |             fetch('https://mempool.space/api/v1/difficulty-adjustment'),
 981 |  7398 |             fetch('https://mempool.space/api/blocks/tip/height')
 982 |  7399 |         ]);
 983 |  7400 | 
 984 |  7401 |         window.mempoolCache = {
 985 |  7402 |             blocks: await blocksRes.json(),
 986 |  7403 |             fees: await feesRes.json(),
 987 |  7404 |             mempool: await mempoolRes.json(),
 988 |  7405 |             difficulty: await diffRes.json(),
 989 |  7406 |             height: await heightRes.json(),
 990 |  7407 |             lastFetch: now
 991 |  7408 |         };
 992 |  7409 | 
 993 |  7410 |         return window.mempoolCache;
 994 |  7411 |     } catch (e) {
 995 |  7412 |         console.error('Mempool data fetch error:', e);
 996 |  7413 |         return window.mempoolCache;
 997 |  7414 |     }
 998 |  7415 | }
 999 |  7416 | 
1000 |  7417 | // Master update function for all Intelligence Descent modules
1001 |  7418 | async function updateIntelligenceDescent() {
1002 |  7419 |     const data = await fetchMempoolData();
1003 |  7420 |     if (!data.blocks) return;
1004 |  7421 | 
1005 |  7422 |     // 1. Update Sovereign Health HUD
1006 |  7423 |     updateSovereignHealthFromCache(data);
1007 |  7424 | 
1008 |  7425 |     // 2. Update Protocol Roadmap
1009 | 
1010 | ============================================================
1011 | === EPOCH PROGRESS & MINING POOLS (lines 7606-7710 of 9534) ===
1012 | ============================================================
1013 | 
1014 |  7606 | async function updateEpochProgress() {
1015 |  7607 |     if (!window.mempoolCache.difficulty || !window.mempoolCache.height) return;
1016 |  7608 | 
1017 |  7609 |     const diff = window.mempoolCache.difficulty;
1018 |  7610 |     const height = window.mempoolCache.height;
1019 |  7611 | 
1020 |  7612 |     const blocksInEpoch = height % 2016;
1021 |  7613 |     const percentage = ((blocksInEpoch / 2016) * 100).toFixed(1);
1022 |  7614 |     const blocksRemaining = 2016 - blocksInEpoch;
1023 |  7615 | 
1024 |  7616 |     const barFill = document.getElementById('epoch-bar-fill');
1025 |  7617 |     const barText = document.getElementById('epoch-bar-text');
1026 |  7618 |     const blockCurrent = document.getElementById('epoch-block-current');
1027 |  7619 |     const blocksRem = document.getElementById('epoch-blocks-remaining');
1028 |  7620 |     const adjustment = document.getElementById('epoch-adjustment');
1029 |  7621 |     const timeRem = document.getElementById('epoch-time-remaining');
1030 |  7622 | 
1031 |  7623 |     if (barFill) barFill.style.width = percentage + '%';
1032 |  7624 |     if (barText) barText.textContent = percentage + '%';
1033 |  7625 |     if (blockCurrent) blockCurrent.textContent = blocksInEpoch.toLocaleString();
1034 |  7626 |     if (blocksRem) blocksRem.textContent = blocksRemaining.toLocaleString();
1035 |  7627 | 
1036 |  7628 |     if (diff.difficultyChange !== undefined && adjustment) {
1037 |  7629 |         const change = diff.difficultyChange.toFixed(2);
1038 |  7630 |         adjustment.textContent = (change >= 0 ? '+' : '') + change + '%';
1039 |  7631 |         adjustment.className = 'epoch-stat-value ' + (change >= 0 ? 'positive' : 'negative');
1040 |  7632 |     }
1041 |  7633 | 
1042 |  7634 |     if (diff.remainingTime !== undefined && timeRem) {
1043 |  7635 |         const days = Math.floor(diff.remainingTime / 86400000);
1044 |  7636 |         const hours = Math.floor((diff.remainingTime % 86400000) / 3600000);
1045 |  7637 |         timeRem.textContent = '~' + days + 'd ' + hours + 'h';
1046 |  7638 |     }
1047 |  7639 | }
1048 |  7640 | 
1049 |  7641 | // 3. MINING POOL DISTRIBUTION (using mempool.space mining pool data)
1050 |  7642 | async function updateMiningPools() {
1051 |  7643 |     try {
1052 |  7644 |         const res = await fetch('https://mempool.space/api/v1/mining/pools/1w');
1053 |  7645 |         const data = await res.json();
1054 |  7646 | 
1055 |  7647 |         if (data.pools && data.pools.length > 0) {
1056 |  7648 |             const legend = document.getElementById('pool-legend');
1057 |  7649 |             const colors = ['#f7931a', '#dc2626', '#22c55e', '#3b82f6', '#8b5cf6', '#14b8a6', '#eab308', '#ec4899'];
1058 |  7650 | 
1059 |  7651 |             if (!legend) return;
1060 |  7652 |             legend.innerHTML = '';
1061 |  7653 | 
1062 |  7654 |             // Calculate total blocks to derive percentages
1063 |  7655 |             const totalBlocks = data.blockCount || data.pools.reduce((sum, p) => sum + p.blockCount, 0);
1064 |  7656 | 
1065 |  7657 |             // Add share percentage to each pool
1066 |  7658 |             const poolsWithShare = data.pools.slice(0, 6).map(pool => ({
1067 |  7659 |                 ...pool,
1068 |  7660 |                 share: (pool.blockCount / totalBlocks) * 100
1069 |  7661 |             }));
1070 |  7662 | 
1071 |  7663 |             poolsWithShare.forEach((pool, i) => {
1072 |  7664 |                 const item = document.createElement('div');
1073 |  7665 |                 item.className = 'pool-legend-item';
1074 |  7666 |                 item.innerHTML = `
1075 |  7667 |                     <div class="pool-legend-name">
1076 |  7668 |                         <div class="pool-legend-dot" style="background: ${colors[i]}"></div>
1077 |  7669 |                         <span>${pool.name}</span>
1078 |  7670 |                     </div>
1079 |  7671 |                     <span class="pool-legend-pct">${pool.share.toFixed(1)}%</span>
1080 |  7672 |                 `;
1081 |  7673 |                 legend.appendChild(item);
1082 |  7674 | 
1083 |  7675 |                 // Check for centralization warning
1084 |  7676 |                 const warningEl = document.getElementById('pool-warning');
1085 |  7677 |                 if (pool.share > 35 && warningEl) {
1086 |  7678 |                     warningEl.style.display = 'block';
1087 |  7679 |                 }
1088 |  7680 |             });
1089 |  7681 | 
1090 |  7682 |             // Update total hashrate display
1091 |  7683 |             if (data.lastEstimatedHashrate) {
1092 |  7684 |                 const hashrateEl = document.getElementById('pool-total-hashrate');
1093 |  7685 |                 if (hashrateEl) {
1094 |  7686 |                     const ehps = data.lastEstimatedHashrate / 1e18;
1095 |  7687 |                     hashrateEl.textContent = ehps.toFixed(0) + ' EH/s';
1096 |  7688 |                 }
1097 |  7689 |             }
1098 |  7690 | 
1099 |  7691 |             // Draw simple donut chart
1100 |  7692 |             drawPoolDonut(poolsWithShare, colors);
1101 |  7693 |         }
1102 |  7694 |     } catch (e) {
1103 |  7695 |         console.error('Mining pools update error:', e);
1104 |  7696 |     }
1105 |  7697 | }
1106 |  7698 | 
1107 |  7699 | function drawPoolDonut(pools, colors) {
1108 |  7700 |     const canvas = document.getElementById('pool-chart');
1109 |  7701 |     if (!canvas) return;
1110 |  7702 | 
1111 |  7703 |     const ctx = canvas.getContext('2d');
1112 |  7704 |     const centerX = canvas.width / 2;
1113 |  7705 |     const centerY = canvas.height / 2;
1114 |  7706 |     const radius = 80;
1115 |  7707 |     const innerRadius = 50;
1116 |  7708 | 
1117 |  7709 |     ctx.clearRect(0, 0, canvas.width, canvas.height);
1118 |  7710 | 
1119 | 
1120 | ============================================================
1121 | === NODE GLOBE THREE.JS (CORE) (lines 7726-8060 of 9534) ===
1122 | ============================================================
1123 | 
1124 |  7726 | // 4. NODE GLOBE (Three.js) - Enhanced with interactive tooltips
1125 |  7727 | let nodeGlobe = null;
1126 |  7728 | let globeAutoRotate = true;
1127 |  7729 | let nodeDataArray = []; // Store node data for tooltips
1128 |  7730 | 
1129 |  7731 | // Node data with accurate geographic coordinates for major Bitcoin node concentrations
1130 |  7732 | const nodeRegions = [
1131 |  7733 |     { name: 'Germany', flag: '🇩🇪', city: 'Frankfurt', version: '/Satoshi:25.0.0/', lat: 50.1, lon: 8.7, count: 2847 },
1132 |  7734 |     { name: 'Germany', flag: '🇩🇪', city: 'Berlin', version: '/Satoshi:26.0.0/', lat: 52.5, lon: 13.4, count: 1200 },
1133 |  7735 |     { name: 'Germany', flag: '🇩🇪', city: 'Munich', version: '/Satoshi:25.1.0/', lat: 48.1, lon: 11.6, count: 800 },
1134 |  7736 |     { name: 'United States', flag: '🇺🇸', city: 'San Francisco', version: '/Satoshi:26.0.0/', lat: 37.7, lon: -122.4, count: 2412 },
1135 |  7737 |     { name: 'United States', flag: '🇺🇸', city: 'New York', version: '/Satoshi:25.1.0/', lat: 40.7, lon: -74.0, count: 1850 },
1136 |  7738 |     { name: 'United States', flag: '🇺🇸', city: 'Chicago', version: '/Satoshi:25.0.0/', lat: 41.9, lon: -87.6, count: 950 },
1137 |  7739 |     { name: 'United States', flag: '🇺🇸', city: 'Los Angeles', version: '/Satoshi:26.0.0/', lat: 34.0, lon: -118.2, count: 780 },
1138 |  7740 |     { name: 'United States', flag: '🇺🇸', city: 'Austin', version: '/Satoshi:25.1.0/', lat: 30.3, lon: -97.7, count: 620 },
1139 |  7741 |     { name: 'United Kingdom', flag: '🇬🇧', city: 'London', version: '/Satoshi:24.1.0/', lat: 51.5, lon: -0.1, count: 847 },
1140 |  7742 |     { name: 'France', flag: '🇫🇷', city: 'Paris', version: '/Satoshi:26.0.0/', lat: 48.8, lon: 2.3, count: 982 },
1141 |  7743 |     { name: 'Netherlands', flag: '🇳🇱', city: 'Amsterdam', version: '/Satoshi:25.0.0/', lat: 52.4, lon: 4.9, count: 847 },
1142 |  7744 |     { name: 'Japan', flag: '🇯🇵', city: 'Tokyo', version: '/Satoshi:25.0.0/', lat: 35.7, lon: 139.7, count: 523 },
1143 |  7745 |     { name: 'Singapore', flag: '🇸🇬', city: 'Singapore', version: '/Satoshi:24.0.1/', lat: 1.3, lon: 103.8, count: 312 },
1144 |  7746 |     { name: 'Canada', flag: '🇨🇦', city: 'Toronto', version: '/Satoshi:26.0.0/', lat: 43.7, lon: -79.4, count: 489 },
1145 |  7747 |     { name: 'Australia', flag: '🇦🇺', city: 'Sydney', version: '/Satoshi:25.0.0/', lat: -33.9, lon: 151.2, count: 287 },
1146 |  7748 | ];
1147 |  7749 | 
1148 |  7750 | function initNodeGlobe() {
1149 |  7751 |     const container = document.getElementById('node-globe');
1150 |  7752 |     if (!container || !window.THREE) return;
1151 |  7753 | 
1152 |  7754 |     const width = container.clientWidth;
1153 |  7755 |     const height = container.clientHeight || 400;
1154 |  7756 | 
1155 |  7757 |     // Scene setup
1156 |  7758 |     const scene = new THREE.Scene();
1157 |  7759 |     const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
1158 |  7760 |     camera.position.z = 2.8;
1159 |  7761 | 
1160 |  7762 |     const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
1161 |  7763 |     renderer.setSize(width, height);
1162 |  7764 |     renderer.setClearColor(0x000000, 0);
1163 |  7765 |     container.insertBefore(renderer.domElement, container.firstChild);
1164 |  7766 | 
1165 |  7767 |     // Globe with glow effect
1166 |  7768 |     const globeGeometry = new THREE.SphereGeometry(1, 64, 64);
1167 |  7769 |     const globeMaterial = new THREE.MeshBasicMaterial({
1168 |  7770 |         color: 0x1a3a6e,
1169 |  7771 |         wireframe: true,
1170 |  7772 |         transparent: true,
1171 |  7773 |         opacity: 0.25
1172 |  7774 |     });
1173 |  7775 |     const globe = new THREE.Mesh(globeGeometry, globeMaterial);
1174 |  7776 |     scene.add(globe);
1175 |  7777 | 
1176 |  7778 |     // Add inner glow sphere
1177 |  7779 |     const glowGeometry = new THREE.SphereGeometry(0.98, 32, 32);
1178 |  7780 |     const glowMaterial = new THREE.MeshBasicMaterial({
1179 |  7781 |         color: 0x0a1628,
1180 |  7782 |         transparent: true,
1181 |  7783 |         opacity: 0.8
1182 |  7784 |     });
1183 |  7785 |     const glowSphere = new THREE.Mesh(glowGeometry, glowMaterial);
1184 |  7786 |     scene.add(glowSphere);
1185 |  7787 | 
1186 |  7788 |     // Generate nodes with data
1187 |  7789 |     nodeDataArray = [];
1188 |  7790 |     const nodePositions = [];
1189 |  7791 |     const nodeSizes = [];
1190 |  7792 |     const nodeColors = [];
1191 |  7793 | 
1192 |  7794 |     // Calculate total count for weighted distribution
1193 |  7795 |     const totalNodes = nodeRegions.reduce((sum, r) => sum + r.count, 0);
1194 |  7796 | 
1195 |  7797 |     for (let i = 0; i < 400; i++) {
1196 |  7798 |         let region;
1197 |  7799 |         let lat, lon;
1198 |  7800 | 
1199 |  7801 |         // Weighted selection based on actual node counts per region
1200 |  7802 |         let rand = Math.random() * totalNodes;
1201 |  7803 |         let cumulative = 0;
1202 |  7804 |         for (const r of nodeRegions) {
1203 |  7805 |             cumulative += r.count;
1204 |  7806 |             if (rand <= cumulative) {
1205 |  7807 |                 region = r;
1206 |  7808 |                 break;
1207 |  7809 |             }
1208 |  7810 |         }
1209 |  7811 |         if (!region) region = nodeRegions[0];
1210 |  7812 | 
1211 |  7813 |         // Wide spread across region for visual symmetry (25-45 degree spread)
1212 |  7814 |         const clusterSpread = 25 + Math.random() * 20;
1213 |  7815 |         lat = region.lat + (Math.random() - 0.5) * clusterSpread;
1214 |  7816 |         lon = region.lon + (Math.random() - 0.5) * clusterSpread;
1215 |  7817 | 
1216 |  7818 |         const phi = (90 - lat) * (Math.PI / 180);
1217 |  7819 |         const theta = (lon + 180) * (Math.PI / 180);
1218 |  7820 |         const r = 1.02;
1219 |  7821 | 
1220 |  7822 |         const x = r * Math.sin(phi) * Math.cos(theta);
1221 |  7823 |         const y = r * Math.cos(phi);
1222 |  7824 |         const z = r * Math.sin(phi) * Math.sin(theta);
1223 |  7825 | 
1224 |  7826 |         nodePositions.push(x, y, z);
1225 |  7827 | 
1226 |  7828 |         // Store node data for tooltips
1227 |  7829 |         const uptimeDays = Math.floor(Math.random() * 1000) + 30;
1228 |  7830 |         const blockHeight = 879000 + Math.floor(Math.random() * 100);
1229 |  7831 |         nodeDataArray.push({
1230 |  7832 |             region: region.name,
1231 |  7833 |             flag: region.flag,
1232 |  7834 |             city: region.city,
1233 |  7835 |             version: region.version,
1234 |  7836 |             uptime: uptimeDays,
1235 |  7837 |             blockHeight: blockHeight,
1236 |  7838 |             connections: Math.floor(Math.random() * 100) + 8,
1237 |  7839 |             position: { x, y, z }
1238 |  7840 |         });
1239 |  7841 |     }
1240 |  7842 | 
1241 |  7843 |     const nodesGeometry = new THREE.BufferGeometry();
1242 |  7844 |     nodesGeometry.setAttribute('position', new THREE.Float32BufferAttribute(nodePositions, 3));
1243 |  7845 | 
1244 |  7846 |     const nodesMaterial = new THREE.PointsMaterial({
1245 |  7847 |         color: 0xf7931a,
1246 |  7848 |         size: 0.025,
1247 |  7849 |         transparent: true,
1248 |  7850 |         opacity: 0.9,
1249 |  7851 |         sizeAttenuation: true
1250 |  7852 |     });
1251 |  7853 | 
1252 |  7854 |     const nodes = new THREE.Points(nodesGeometry, nodesMaterial);
1253 |  7855 |     scene.add(nodes);
1254 |  7856 | 
1255 |  7857 |     // Raycaster for hover detection
1256 |  7858 |     const raycaster = new THREE.Raycaster();
1257 |  7859 |     raycaster.params.Points.threshold = 0.05;
1258 |  7860 |     const mouse = new THREE.Vector2();
1259 |  7861 |     const tooltip = document.getElementById('node-tooltip');
1260 |  7862 |     const tooltipContent = document.getElementById('node-tooltip-content');
1261 |  7863 | 
1262 |  7864 |     // Mouse interaction
1263 |  7865 |     let isDragging = false;
1264 |  7866 |     let previousMousePosition = { x: 0, y: 0 };
1265 |  7867 | 
1266 |  7868 |     renderer.domElement.addEventListener('mousedown', (e) => {
1267 |  7869 |         isDragging = true;
1268 |  7870 |         previousMousePosition = { x: e.clientX, y: e.clientY };
1269 |  7871 |     });
1270 |  7872 | 
1271 |  7873 |     renderer.domElement.addEventListener('mousemove', (e) => {
1272 |  7874 |         const rect = renderer.domElement.getBoundingClientRect();
1273 |  7875 |         mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
1274 |  7876 |         mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
1275 |  7877 | 
1276 |  7878 |         if (isDragging) {
1277 |  7879 |             const deltaX = e.clientX - previousMousePosition.x;
1278 |  7880 |             const deltaY = e.clientY - previousMousePosition.y;
1279 |  7881 | 
1280 |  7882 |             globe.rotation.y += deltaX * 0.005;
1281 |  7883 |             nodes.rotation.y += deltaX * 0.005;
1282 |  7884 |             glowSphere.rotation.y += deltaX * 0.005;
1283 |  7885 |             globe.rotation.x += deltaY * 0.005;
1284 |  7886 |             nodes.rotation.x += deltaY * 0.005;
1285 |  7887 |             glowSphere.rotation.x += deltaY * 0.005;
1286 |  7888 | 
1287 |  7889 |             previousMousePosition = { x: e.clientX, y: e.clientY };
1288 |  7890 |             tooltip.style.display = 'none';
1289 |  7891 |         } else {
1290 |  7892 |             // Hover detection
1291 |  7893 |             raycaster.setFromCamera(mouse, camera);
1292 |  7894 |             const intersects = raycaster.intersectObject(nodes);
1293 |  7895 | 
1294 |  7896 |             if (intersects.length > 0) {
1295 |  7897 |                 const idx = intersects[0].index;
1296 |  7898 |                 const nodeData = nodeDataArray[idx];
1297 |  7899 | 
1298 |  7900 |                 tooltipContent.innerHTML = `
1299 |  7901 |                     <div style="font-size: 1rem; margin-bottom: 8px;">${nodeData.flag} <span style="color: #fff;">${nodeData.city}, ${nodeData.region}</span></div>
1300 |  7902 |                     <div style="font-size: 0.7rem; color: rgba(255,255,255,0.6); margin-bottom: 10px; font-family: 'JetBrains Mono', monospace;">${nodeData.version}</div>
1301 |  7903 |                     <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.75rem;">
1302 |  7904 |                         <div><span style="color: rgba(255,255,255,0.5);">Uptime:</span> <span style="color: #22c55e;">${nodeData.uptime}d</span></div>
1303 |  7905 |                         <div><span style="color: rgba(255,255,255,0.5);">Peers:</span> <span style="color: #f7931a;">${nodeData.connections}</span></div>
1304 |  7906 |                         <div style="grid-column: span 2;"><span style="color: rgba(255,255,255,0.5);">Block:</span> <span style="color: #3b82f6; font-family: 'JetBrains Mono', monospace;">#${nodeData.blockHeight.toLocaleString()}</span></div>
1305 |  7907 |                     </div>
1306 |  7908 |                 `;
1307 |  7909 | 
1308 |  7910 |                 tooltip.style.display = 'block';
1309 |  7911 |                 tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
1310 |  7912 |                 tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
1311 |  7913 |             } else {
1312 |  7914 |                 tooltip.style.display = 'none';
1313 |  7915 |             }
1314 |  7916 |         }
1315 |  7917 |     });
1316 |  7918 | 
1317 |  7919 |     renderer.domElement.addEventListener('mouseup', () => isDragging = false);
1318 |  7920 |     renderer.domElement.addEventListener('mouseleave', () => {
1319 |  7921 |         isDragging = false;
1320 |  7922 |         tooltip.style.display = 'none';
1321 |  7923 |     });
1322 |  7924 | 
1323 |  7925 |     // Hide tooltip on scroll to prevent it from floating over other content
1324 |  7926 |     window.addEventListener('scroll', () => {
1325 |  7927 |         tooltip.style.display = 'none';
1326 |  7928 |     }, { passive: true });
1327 |  7929 | 
1328 |  7930 |     // Mouse wheel zoom
1329 |  7931 |     renderer.domElement.addEventListener('wheel', (e) => {
1330 |  7932 |         e.preventDefault();
1331 |  7933 |         camera.position.z += e.deltaY * 0.002;
1332 |  7934 |         camera.position.z = Math.max(1.5, Math.min(5, camera.position.z));
1333 |  7935 |     }, { passive: false });
1334 |  7936 | 
1335 |  7937 |     // Touch support for mobile
1336 |  7938 |     let touchStartDistance = 0;
1337 |  7939 |     let isTouchDragging = false;
1338 |  7940 |     let previousTouchPosition = { x: 0, y: 0 };
1339 |  7941 | 
1340 |  7942 |     renderer.domElement.addEventListener('touchstart', (e) => {
1341 |  7943 |         if (e.touches.length === 1) {
1342 |  7944 |             isTouchDragging = true;
1343 |  7945 |             previousTouchPosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
1344 |  7946 |         } else if (e.touches.length === 2) {
1345 |  7947 |             // Pinch zoom - calculate initial distance
1346 |  7948 |             const dx = e.touches[0].clientX - e.touches[1].clientX;
1347 |  7949 |             const dy = e.touches[0].clientY - e.touches[1].clientY;
1348 |  7950 |             touchStartDistance = Math.sqrt(dx * dx + dy * dy);
1349 |  7951 |         }
1350 |  7952 |     }, { passive: true });
1351 |  7953 | 
1352 |  7954 |     renderer.domElement.addEventListener('touchmove', (e) => {
1353 |  7955 |         if (e.touches.length === 1 && isTouchDragging) {
1354 |  7956 |             const deltaX = e.touches[0].clientX - previousTouchPosition.x;
1355 |  7957 |             const deltaY = e.touches[0].clientY - previousTouchPosition.y;
1356 |  7958 | 
1357 |  7959 |             globe.rotation.y += deltaX * 0.008;
1358 |  7960 |             nodes.rotation.y += deltaX * 0.008;
1359 |  7961 |             glowSphere.rotation.y += deltaX * 0.008;
1360 |  7962 |             globe.rotation.x += deltaY * 0.008;
1361 |  7963 |             nodes.rotation.x += deltaY * 0.008;
1362 |  7964 |             glowSphere.rotation.x += deltaY * 0.008;
1363 |  7965 | 
1364 |  7966 |             previousTouchPosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
1365 |  7967 |             tooltip.style.display = 'none';
1366 |  7968 |         } else if (e.touches.length === 2) {
1367 |  7969 |             // Pinch zoom
1368 |  7970 |             const dx = e.touches[0].clientX - e.touches[1].clientX;
1369 |  7971 |             const dy = e.touches[0].clientY - e.touches[1].clientY;
1370 |  7972 |             const distance = Math.sqrt(dx * dx + dy * dy);
1371 |  7973 | 
1372 |  7974 |             if (touchStartDistance > 0) {
1373 |  7975 |                 const delta = touchStartDistance - distance;
1374 |  7976 |                 camera.position.z += delta * 0.01;
1375 |  7977 |                 camera.position.z = Math.max(1.5, Math.min(5, camera.position.z));
1376 |  7978 |                 touchStartDistance = distance;
1377 |  7979 |             }
1378 |  7980 |         }
1379 |  7981 |     }, { passive: true });
1380 |  7982 | 
1381 |  7983 |     renderer.domElement.addEventListener('touchend', () => {
1382 |  7984 |         isTouchDragging = false;
1383 |  7985 |         touchStartDistance = 0;
1384 |  7986 |     }, { passive: true });
1385 |  7987 | 
1386 |  7988 |     // Animation with pulsing nodes
1387 |  7989 |     let time = 0;
1388 |  7990 |     function animate() {
1389 |  7991 |         requestAnimationFrame(animate);
1390 |  7992 |         time += 0.01;
1391 |  7993 | 
1392 |  7994 |         if (globeAutoRotate && !isDragging) {
1393 |  7995 |             globe.rotation.y += 0.001;
1394 |  7996 |             nodes.rotation.y += 0.001;
1395 |  7997 |             glowSphere.rotation.y += 0.001;
1396 |  7998 |         }
1397 |  7999 | 
1398 |  8000 |         // Subtle pulse effect
1399 |  8001 |         nodesMaterial.opacity = 0.7 + Math.sin(time * 2) * 0.2;
1400 |  8002 | 
1401 |  8003 |         renderer.render(scene, camera);
1402 |  8004 |     }
1403 |  8005 | 
1404 |  8006 |     animate();
1405 |  8007 | 
1406 |  8008 |     // Set initial rotation to center on North America (longitude ~-100°)
1407 |  8009 |     // Y rotation of ~1.75 radians rotates globe to show North America
1408 |  8010 |     const northAmericaRotation = 1.75;
1409 |  8011 |     globe.rotation.y = northAmericaRotation;
1410 |  8012 |     nodes.rotation.y = northAmericaRotation;
1411 |  8013 |     glowSphere.rotation.y = northAmericaRotation;
1412 |  8014 | 
1413 |  8015 |     nodeGlobe = { globe, nodes, glowSphere, renderer, scene, camera };
1414 |  8016 | }
1415 |  8017 | 
1416 |  8018 | // Default rotation for North America view
1417 |  8019 | const NORTH_AMERICA_ROTATION = 1.75;
1418 |  8020 | 
1419 |  8021 | function resetGlobeRotation() {
1420 |  8022 |     if (nodeGlobe) {
1421 |  8023 |         // Reset to North America centered view
1422 |  8024 |         nodeGlobe.globe.rotation.set(0, NORTH_AMERICA_ROTATION, 0);
1423 |  8025 |         nodeGlobe.nodes.rotation.set(0, NORTH_AMERICA_ROTATION, 0);
1424 |  8026 |         if (nodeGlobe.glowSphere) nodeGlobe.glowSphere.rotation.set(0, NORTH_AMERICA_ROTATION, 0);
1425 |  8027 |     }
1426 |  8028 | }
1427 |  8029 | 
1428 |  8030 | function toggleGlobeAutoRotate() {
1429 |  8031 |     globeAutoRotate = !globeAutoRotate;
1430 |  8032 | }
1431 |  8033 | 
1432 |  8034 | // Globe zoom controls
1433 |  8035 | const globeZoomLimits = { min: 1.5, max: 5.0, step: 0.3 };
1434 |  8036 | let currentGlobeZoom = 2.8;
1435 |  8037 | 
1436 |  8038 | function globeZoomIn() {
1437 |  8039 |     if (nodeGlobe && nodeGlobe.camera) {
1438 |  8040 |         currentGlobeZoom = Math.max(globeZoomLimits.min, currentGlobeZoom - globeZoomLimits.step);
1439 |  8041 |         nodeGlobe.camera.position.z = currentGlobeZoom;
1440 |  8042 |         console.log('Globe zoom in:', currentGlobeZoom);
1441 |  8043 |     }
1442 |  8044 | }
1443 |  8045 | 
1444 |  8046 | function globeZoomOut() {
1445 |  8047 |     if (nodeGlobe && nodeGlobe.camera) {
1446 |  8048 |         currentGlobeZoom = Math.min(globeZoomLimits.max, currentGlobeZoom + globeZoomLimits.step);
1447 |  8049 |         nodeGlobe.camera.position.z = currentGlobeZoom;
1448 |  8050 |         console.log('Globe zoom out:', currentGlobeZoom);
1449 |  8051 |     }
1450 |  8052 | }
1451 |  8053 | 
1452 |  8054 | // Mobile pinch-to-zoom for Node Globe
1453 |  8055 | function initGlobePinchZoom() {
1454 |  8056 |     const container = document.getElementById('node-globe');
1455 |  8057 |     if (!container) return;
1456 |  8058 | 
1457 |  8059 |     let initialDistance = 0;
1458 |  8060 |     let initialZoom = currentGlobeZoom;
1459 | 
1460 | ============================================================
1461 | === AUDIO BARS & INIT (lines 8700-8800 of 9534) ===
1462 | ============================================================
1463 | 
1464 |  8700 | }
1465 |  8701 | 
1466 |  8702 | function playWhaleChime() {
1467 |  8703 |     if (!heartbeatEnabled || !audioContext) return;
1468 |  8704 | 
1469 |  8705 |     const oscillator = audioContext.createOscillator();
1470 |  8706 |     const gainNode = audioContext.createGain();
1471 |  8707 | 
1472 |  8708 |     oscillator.type = 'triangle';
1473 |  8709 |     oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
1474 |  8710 |     oscillator.frequency.exponentialRampToValueAtTime(440, audioContext.currentTime + 0.5);
1475 |  8711 | 
1476 |  8712 |     gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
1477 |  8713 |     gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.8);
1478 |  8714 | 
1479 |  8715 |     oscillator.connect(gainNode);
1480 |  8716 |     gainNode.connect(audioContext.destination);
1481 |  8717 | 
1482 |  8718 |     oscillator.start(audioContext.currentTime);
1483 |  8719 |     oscillator.stop(audioContext.currentTime + 0.8);
1484 |  8720 | }
1485 |  8721 | 
1486 |  8722 | function animateAudioBars() {
1487 |  8723 |     if (!heartbeatEnabled) return;
1488 |  8724 | 
1489 |  8725 |     const bars = document.querySelectorAll('#audio-visualizer .audio-bar');
1490 |  8726 |     bars.forEach(bar => {
1491 |  8727 |         bar.style.height = (10 + Math.random() * 30) + 'px';
1492 |  8728 |     });
1493 |  8729 | 
1494 |  8730 |     setTimeout(animateAudioBars, 100);
1495 |  8731 | }
1496 |  8732 | 
1497 |  8733 | // 9. GENESIS BLOCK EXPAND
1498 |  8734 | function toggleGenesisExpand() {
1499 |  8735 |     const expanded = document.getElementById('genesis-expanded');
1500 |  8736 |     const btn = document.querySelector('.genesis-expand-btn i');
1501 |  8737 | 
1502 |  8738 |     if (expanded.style.display === 'none') {
1503 |  8739 |         expanded.style.display = 'block';
1504 |  8740 |         btn.className = 'fas fa-minus me-1';
1505 |  8741 |     } else {
1506 |  8742 |         expanded.style.display = 'none';
1507 |  8743 |         btn.className = 'fas fa-plus me-1';
1508 |  8744 |     }
1509 |  8745 | }
1510 |  8746 | 
1511 |  8747 | // 10. CTA FUNCTIONS
1512 |  8748 | function subscribeEmail(event) {
1513 |  8749 |     event.preventDefault();
1514 |  8750 |     const email = event.target.querySelector('input').value;
1515 |  8751 |     alert('Thank you for subscribing! You\'ll receive the Daily Pulse at 6am EST.');
1516 |  8752 |     event.target.reset();
1517 |  8753 | }
1518 |  8754 | 
1519 |  8755 | function showLightningTip() {
1520 |  8756 |     // Would integrate with Lightning tip jar
1521 |  8757 |     alert('Lightning tip jar coming soon! ⚡');
1522 |  8758 | }
1523 |  8759 | 
1524 |  8760 | // Initialize new modules - Wait for DOM and Three.js
1525 |  8761 | function initializeNewModules() {
1526 |  8762 |     // Only proceed if DOM is ready and cache is available
1527 |  8763 |     if (document.readyState === 'loading') {
1528 |  8764 |         document.addEventListener('DOMContentLoaded', initializeNewModules);
1529 |  8765 |         return;
1530 |  8766 |     }
1531 |  8767 | 
1532 |  8768 |     // Init Node Globe (requires Three.js)
1533 |  8769 |     if (typeof THREE !== 'undefined') {
1534 |  8770 |         try { initNodeGlobe(); } catch (e) { console.log('Globe init error:', e); }
1535 |  8771 |     } else {
1536 |  8772 |         console.log('Three.js not loaded for globe');
1537 |  8773 |     }
1538 |  8774 | 
1539 |  8775 |     updateNodeCount();
1540 |  8776 |     fetchBtcPriceHistory().then(() => calculateDCA()).catch(e => console.log('DCA calc error:', e));
1541 |  8777 |     updateMiningPools().catch(e => console.log('Mining pools error:', e));
1542 |  8778 |     updateLightningPulse().catch(e => console.log('Lightning error:', e));
1543 |  8779 |     updateEpochProgress();
1544 |  8780 |     updateTimechainClock();
1545 |  8781 |     initAdRotation();
1546 |  8782 | 
1547 |  8783 |     // Generate 60 precision tick marks for Holographic Horizon clock
1548 |  8784 |     const tickContainer = document.querySelector('.clock-tick-marks');
1549 |  8785 |     if (tickContainer && tickContainer.querySelectorAll('.tick-mark').length === 0) {
1550 |  8786 |         for (let i = 0; i < 60; i++) {
1551 |  8787 |             const tick = document.createElement('div');
1552 |  8788 |             tick.className = 'tick-mark';
1553 |  8789 |             const isMajor = i % 5 === 0;
1554 |  8790 |             const angle = i * 6; // 360/60 = 6 degrees per tick
1555 |  8791 | 
1556 |  8792 |             // Position ticks on inner rim
1557 |  8793 |             const tickLength = isMajor ? 12 : 6;
1558 |  8794 |             const tickWidth = isMajor ? 3 : 1;
1559 |  8795 |             const radius = 140; // Distance from center
1560 |  8796 | 
1561 |  8797 |             tick.style.cssText = `
1562 |  8798 |                 position: absolute;
1563 |  8799 |                 width: ${tickWidth}px;
1564 |  8800 |                 height: ${tickLength}px;
1565 | 
1566 | ============================================================
1567 | === END OF FILE (lines 9480-9534 of 9534) ===
1568 | ============================================================
1569 | 
1570 |  9480 |   { amount: 2100, message: 'Bitcoin fixes this', node: 'Strike' },
1571 |  9481 |   { amount: 5000, message: 'Nostr zap', node: 'WoS' },
1572 |  9482 |   { amount: 10000, message: 'V4V ⚡', node: 'Alby' },
1573 |  9483 |   { amount: 21000, message: 'Pleb power', node: 'Mutiny' },
1574 |  9484 | ];
1575 |  9485 | 
1576 |  9486 | function addLightningZap() {
1577 |  9487 |     const container = document.getElementById('lightning-zap-feed');
1578 |  9488 |     if (!container) return;
1579 |  9489 | 
1580 |  9490 |     const zap = lightningZapExamples[Math.floor(Math.random() * lightningZapExamples.length)];
1581 |  9491 |     const variation = Math.random() * 0.5 + 0.75; // 0.75 to 1.25
1582 |  9492 |     const amount = Math.round(zap.amount * variation);
1583 |  9493 | 
1584 |  9494 |     const zapEl = document.createElement('div');
1585 |  9495 |     zapEl.className = 'lightning-zap';
1586 |  9496 |     zapEl.innerHTML = `
1587 |  9497 |         <div class="zap-icon"><i class="fas fa-bolt"></i></div>
1588 |  9498 |         <div style="flex: 1;">
1589 |  9499 |             <div style="color: #facc15; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; font-weight: 600;">
1590 |  9500 |                 ${amount.toLocaleString()} sats
1591 |  9501 |             </div>
1592 |  9502 |             <div style="color: rgba(255,255,255,0.6); font-size: 0.75rem;">
1593 |  9503 |                 via ${zap.node} • ${zap.message}
1594 |  9504 |             </div>
1595 |  9505 |         </div>
1596 |  9506 |         <div style="color: rgba(255,255,255,0.4); font-size: 0.7rem;">now</div>
1597 |  9507 |     `;
1598 |  9508 | 
1599 |  9509 |     container.insertBefore(zapEl, container.firstChild);
1600 |  9510 | 
1601 |  9511 |     // Keep only last 6 zaps
1602 |  9512 |     while (container.children.length > 6) {
1603 |  9513 |         container.removeChild(container.lastChild);
1604 |  9514 |     }
1605 |  9515 | }
1606 |  9516 | 
1607 |  9517 | // Add initial zaps and simulate ongoing activity
1608 |  9518 | setTimeout(() => {
1609 |  9519 |     for (let i = 0; i < 4; i++) {
1610 |  9520 |         setTimeout(() => addLightningZap(), i * 200);
1611 |  9521 |     }
1612 |  9522 | }, 2000);
1613 |  9523 | 
1614 |  9524 | // Simulate new zaps at random intervals (3-8 seconds)
1615 |  9525 | function scheduleNextZap() {
1616 |  9526 |     const delay = 3000 + Math.random() * 5000;
1617 |  9527 |     setTimeout(() => {
1618 |  9528 |         addLightningZap();
1619 |  9529 |         scheduleNextZap();
1620 |  9530 |     }, delay);
1621 |  9531 | }
1622 |  9532 | scheduleNextZap();
1623 |  9533 | </script>
1624 |  9534 | {% endblock %}
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
