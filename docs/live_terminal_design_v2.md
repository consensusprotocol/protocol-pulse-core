# LIVE TERMINAL DESIGN V2 -- BUILD BIBLE

**Synthesized from cross-LLM audit (Gemini, Grok, GPT-4o)**
**Winner: Gemini -- strongest analysis, surgical law-violation precision, deepest architectural insight**
**Date: 2026-03-25**
**Status: APPROVED FOR BUILD**

---

## WINNING CONCEPT

### "Stellar Nebula" -- The Heartbeat of Bitcoin

The final concept fuses Gemini's "Stellar Consensus" narrative backbone with Grok's "Bitcoin Nebula" geographic richness and Fibonacci physics into a single cohesive visualization called **Stellar Nebula**.

**The story is: chaos becomes order.** This is Bitcoin's fundamental narrative -- unconfirmed transactions are entropy; block confirmation is consensus; the blockchain is permanence.

**Central Star (The Heartbeat):**
At the center of a full-viewport WebGL canvas sits a single pulsing star. Its core is dense white, its corona is Protocol Pulse Gold (#F8C15C). The star's pulse frequency is driven by hashrate (higher hashrate = faster, more confident pulse). Its luminosity is driven by BTC price (higher price = brighter bloom). This is not a literal sun -- it is an abstract, data-driven beacon representing Bitcoin's aggregate network state.

**Mempool Nebula (The Chaos):**
Surrounding the star is a swirling cloud of transaction particles -- the Mempool Nebula. New transactions spawn at the scene's edges (on a Fibonacci sphere distribution for organic uniformity) and are pulled inward by simulated gravity toward the star. They do not travel in straight lines; they arc along golden spiral paths (r = a * e^(b * theta)), creating the swirling, organic motion of a stellar accretion system. Particle color encodes fee rate: low fee = gold (#F8C15C), medium = white (#FFFFFF), high = burning red (#CC2222). A congested mempool creates a dense, angry, red-tinted cloud. A quiet mempool is sparse and golden.

**Geographic Node Clusters (From Grok):**
Within the nebula, larger glowing nodes represent geographic concentrations of Bitcoin full nodes (Frankfurt, New York, Tokyo, Sao Paulo). These are sourced from live bitnodes.io data via DataService, not hardcoded. Node clusters pulse in unison with the central star, creating a sense of distributed but synchronized heartbeat. Rendered via InstancedMesh with per-instance color attributes.

**Block Confirmation Shockwave (The Moment of Consensus):**
When a new block is found (via WebSocket), the central star erupts in a brilliant white flash. An expanding ring of light -- the shockwave -- sweeps outward through the Mempool Nebula. As it passes, it captures the highest-fee particles from the chaotic cloud.

**Accretion Disk (The Blockchain -- From Gemini):**
Captured particles do not disappear. They are pulled out of the nebula and gracefully settle into a new stable ring orbiting the star -- an accretion disk. Each ring represents one confirmed block. The rings rotate slowly, accumulating over time, creating a visual record of Bitcoin's settlement finality. The most recent ring glows brightest; older rings fade to a dim gold. This transforms the visualization from "real-time ticker" into "historical monument." Positions within each ring follow the golden angle (137.5 degrees) for natural, sunflower-like distribution.

**Ambient Aura (Fear and Greed):**
The entire scene's ambient lighting is tinted by the Fear and Greed Index. Extreme Fear (FNG < 25) casts a cold, deep navy-blue wash. Neutral is the brand background (#0A0A0F). Extreme Greed (FNG > 75) suffuses everything in warm gold, making the star's corona burn brighter and the nebula shimmer. This is implemented as a scene background color lerp and ambient light color shift driven by a single uniform.

**The Result:**
Users see a vast, dark void. A golden star pulses at the center. From all directions, embers of red, white, and gold drift inward, forming a chaotic swirling cloud. Suddenly, the star erupts -- a ring of light expands outward, sweeping the nearest particles into a perfect, glowing ring that joins the other rings rotating around the star. The red chaos of the mempool has been transformed into immutable, golden order. This is Bitcoin.

---

## DATA MAPPING TABLE

| Data Point | Visual Property | Range / Detail |
|---|---|---|
| BTC Price | Star core luminosity + UnrealBloomPass strength | $20K = bloom 0.5 (dim); $150K = bloom 2.0 (supernova). ATH triggers a 0.5s lens flare. |
| Mempool Size (vMB) | Nebula cloud scale + particle density | 1 vMB = scale 1.0x, 100 particles; 300 vMB = scale 3.0x, 1000 particles. Cloud opacity also increases with scale. |
| Hashrate (EH/s) | Central star pulse frequency | 200 EH/s = 0.5 Hz (slow, uncertain); 800 EH/s = 2.0 Hz (fast, confident). Sudden drops make pulse erratic (jitter noise added to sine). |
| Fear & Greed Index | Scene ambient light color + background tint | 0 (Extreme Fear) = deep navy #0A0A2F; 50 (Neutral) = brand bg #0A0A0F; 100 (Extreme Greed) = gold #F8C15C. Lerp between three stops. |
| Block Time (seconds since last block) | Shockwave interval + visual tension buildup | As block time exceeds 600s, nebula grows redder and denser, building visual tension. Shockwave when block arrives is proportionally more dramatic (larger radius, brighter flash). |
| Fee Rate (sat/vB) | Transaction particle color | 1 sat/vB = gold #F8C15C; 50 sat/vB = white #FFFFFF; 200+ sat/vB = red #CC2222. GLSL mix() interpolation on feeRate/maxFeeRate uniform. |
| Transaction Count (tx/s) | Particle spawn rate at scene edges | 1 tx/s = 1 new particle/second; 50 tx/s = 50 particles/second. Capped at MAX_PARTICLES with oldest recycled. |
| Block Height | Displayed in HUD; new block triggers shockwave + accretion ring formation | Integer, updated on WebSocket block event. |
| Node Count | Geographic cluster size and brightness | More nodes in a region = brighter, larger InstancedMesh cluster at that lat/lon projection. |

---

## FIBONACCI PHYSICS SPEC

### 1. Golden Spiral Transaction Paths

Transactions travel from their spawn point to the central star along logarithmic spiral arcs, not straight lines. This creates the swirling, organic motion of the nebula.

**Formula:**

```
r = a * e^(b * theta)
```

Where:
- `r` = distance from the star center
- `theta` = angle of rotation (radians)
- `a` = initial radius (spawn distance from center, typically 5.0-8.0 scene units)
- `b = ln(phi) / (pi/2)` where `phi = 1.6180339887` (the golden ratio)
- This means the spiral grows by a factor of phi for every quarter turn (90 degrees)

**Pseudocode:**

```
phi = 1.6180339887
b = ln(phi) / (PI / 2)    // approximately 0.3063

function spiralPosition(t, startRadius):
    // t goes from 0.0 (spawn) to 1.0 (star center)
    // We travel the spiral inward, so theta increases as r decreases
    theta = t * PI * 4       // 2 full rotations from edge to center
    r = startRadius * e^(-b * theta)  // negative b for inward spiral
    x = r * cos(theta)
    z = r * sin(theta)
    y = sin(t * PI) * 0.3    // gentle vertical arc for 3D depth
    return (x, y, z)
```

Each particle's `t` advances per frame based on fee rate (higher fee = faster travel). When `t >= 1.0`, the particle enters the nebula swirl zone near the star.

### 2. Fibonacci Sphere for Spawn Points

To spawn particles uniformly across the scene's outer shell (avoiding polar clustering), use the Fibonacci sphere algorithm. This produces sunflower-like distribution on a sphere's surface.

**Formula:**

```
For particle i out of N total spawn points:
    y = 1 - (2 * i) / (N - 1)              // y ranges from +1 to -1
    radius = sqrt(1 - y * y)                // radius of circle at height y
    phi = golden_angle * i                  // golden_angle = PI * (3 - sqrt(5)) ~ 2.39996
    x = cos(phi) * radius
    z = sin(phi) * radius
```

**Pseudocode:**

```
golden_angle = PI * (3 - sqrt(5))   // approximately 2.39996 radians (137.5 degrees)

function fibonacciSpherePoint(i, N):
    y = 1.0 - (2.0 * i) / (N - 1)
    radiusAtY = sqrt(1.0 - y * y)
    phi = golden_angle * i
    x = cos(phi) * radiusAtY
    z = sin(phi) * radiusAtY
    return (x * SPAWN_RADIUS, y * SPAWN_RADIUS, z * SPAWN_RADIUS)
```

Pre-compute N spawn points (N = MAX_PARTICLES). When a new transaction arrives, assign it the next available Fibonacci sphere point as its origin.

### 3. Block Confirmation Accretion Ring Formation

When a block is confirmed, captured particles animate from their chaotic nebula positions into ordered positions along a ring. Positions within the ring use the golden angle to avoid clumping.

**Formula:**

```
For transaction i out of n transactions in the block:
    angle = i * golden_angle                // golden_angle = 2.39996 rad
    ring_radius = BASE_RING_RADIUS + (block_index * RING_SPACING)
    x = ring_radius * cos(angle)
    z = ring_radius * sin(angle)
    y = 0  // rings are planar, slight tilt for perspective
```

**Pseudocode:**

```
golden_angle = PI * (3 - sqrt(5))

function computeRingPositions(blockIndex, txCount):
    positions = []
    ringRadius = 2.0 + blockIndex * 0.15   // each new block's ring is slightly farther out
    for i in range(txCount):
        angle = i * golden_angle
        x = ringRadius * cos(angle)
        z = ringRadius * sin(angle)
        y = 0.0
        positions.push((x, y, z))
    return positions
```

Animation: over 1.5 seconds, each captured particle lerps from its current nebula position to its target ring position using an ease-out cubic. The ring then begins slow rotation (0.001 rad/frame). Older rings have lower opacity (fade by 0.05 per ring index, min 0.15).

---

## LAYOUT PLAN (KEEP / CUT / ADD)

| KEEP | CUT | ADD |
|---|---|---|
| `#visualizer-canvas` (promoted to full-viewport hero, `position: fixed; width: 100vw; height: 100vh; z-index: 0`) | Entire `.dashboard-grid` layout | Bottom HUD bar: BTC price, mempool vMB, fee rate, hashrate, block height, connection status -- all in JetBrains Mono on a glass panel (`backdrop-filter: blur(10px)`, bg `rgba(10,10,15,0.82)`) |
| WebSocket connection to `mempool.space` (moved into DataService) | `.zone-sovereign-archive` div and all children | Top-right Pulse logo icon that opens a slide-in "Intel Drawer" from right edge (glass panel) |
| Fee rate data fetching logic (moved into DataService) | `.zone-tactical-horizon` div and all children | Intel Drawer contents: Sovereign Health, Epoch Progress, Mining Pools, Fee Histogram -- the deep data that was cut from the main view |
| Block height display (moved to HUD) | `.zone-logic-engine` div and all children | Connection status indicator in HUD: `LIVE` (green dot), `DELAYED` (yellow, >15s no data), `DISCONNECTED` (red, >30s) |
| FNG data integration (moved into DataService) | `panel-node-globe` HTML (lines 595-685) and `initNodeGlobe` JS (lines 7726-8060) -- replaced by hero | Stale data overlay: semi-transparent desaturation filter on WebGL canvas when disconnected >30s |
| Core data-to-visual mapping philosophy (price->brightness, fee->color, hashrate->pulse, FNG->aura) | All Chart.js 2D chart panels | Audio toggle button (muted by default): block confirmation heartbeat chime via AudioContext |
| | All inline `style=""` attributes (extracted to CSS classes) | CSS fallback for no-WebGL browsers: static hero image + HUD metrics only |
| | `Crimson Pro` and `SF Pro Display` font imports | |
| | Entire `--apple-*` CSS variable system | |
| | Sovereignty calculator widget | |
| | All zone naming (`zone-tactical-horizon`, etc.) -- replaced with semantic IDs (`#hero-canvas-wrapper`, `#hud-overlay`, `#intel-drawer`) | |

---

## FIRST 5 SECONDS EXPERIENCE

**This is the hook. Every millisecond is designed.**

**0.0s -- Black.**
The page loads to `#0A0A0F` -- near-black. No content visible. The WebGL canvas is initializing. The DataService begins its first fetch cycle. CSS `opacity: 0` on all elements.

**0.3s -- The Star Ignites.**
The central star materializes at the exact center of the viewport. It fades in from zero opacity over 300ms. It is small, warm gold (#F8C15C), and begins its first pulse -- a slow, deep expansion and contraction. The pulse frequency matches the current hashrate. If this is the user's first visit and data has not arrived yet, default to 1.0 Hz (the "resting heartbeat"). The bloom pass activates, giving the star a soft, ethereal corona glow.

**1.0s -- The HUD Materializes.**
The bottom HUD bar fades in with a 700ms ease-in. Crisp JetBrains Mono text appears: `BTC $87,432` | `MEMPOOL 45.2 vMB` | `FEES 12 sat/vB` | `812 EH/s` | `BLOCK 889,247` | green dot `LIVE`. The text is small (14px), high-contrast white on the glass panel. It does not compete with the star -- it contextualizes it.

**2.0s -- First Particles Drift In.**
The first batch of transaction particles spawn at the Fibonacci sphere shell and begin their golden spiral journey inward. They are faint at first -- gold and white motes drifting through the void. The user sees movement. Something is alive. The ambient FNG aura subtly tints the scene (if fear, a barely perceptible blue wash; if greed, a warm gold undertone).

**3.5s -- The Nebula Takes Shape.**
More particles have arrived. The space around the star is no longer empty -- a faint, swirling cloud is forming. The user can see the directional flow: particles spiral inward, pulled by the star. Some are red (high fee), some gold (low fee). The cloud has texture and depth. The user understands: this is not a screensaver. This is data. This is real. This is happening right now.

**5.0s -- The First Shockwave (Simulated If No Real Block).**
If a real block arrives within the first 5 seconds, perfect -- the organic shockwave fires. If not, simulate one: the star flashes white, an expanding ring of light sweeps through the nascent nebula, and a handful of particles settle into the first faint accretion ring. The user sees the chaos-to-order transformation for the first time. A subtle heartbeat chime plays (if audio enabled). The holographic block number appears briefly at the core.

**The user now understands: they are watching the heartbeat of a new financial universe. They are not looking at a chart. They are inside Bitcoin.**

---

## PERFORMANCE BUDGET

### Particle and Node Limits

| Tier | Detection Method | Max Particles | Max Nodes | Accretion Ring Instances | Post-Processing |
|---|---|---|---|---|---|
| Mobile | `window.innerWidth < 768` OR `navigator.hardwareConcurrency <= 4` | 2,000 | 500 | 50 per ring, max 10 rings visible | UnrealBloomPass OFF by default; enable ONLY during block shockwave (1.5s burst), then disable. No other post-processing. |
| Tablet | `768 <= innerWidth < 1280` AND `hardwareConcurrency > 4` | 8,000 | 2,000 | 200 per ring, max 20 rings visible | UnrealBloomPass at half resolution (0.5x). Ambient bloom only (strength 0.5). Full bloom (1.5) on block events only. |
| Desktop | `innerWidth >= 1280` AND `hardwareConcurrency > 6` | 20,000 | 5,000 | 500 per ring, max 50 rings visible | Full UnrealBloomPass (1x resolution). Ambient bloom strength 1.0. Block event bloom strength 2.0. |

### Frame Rate Targets

- Target: 60 FPS on all tiers
- Minimum acceptable: 30 FPS
- If FPS drops below 30 for 3 consecutive seconds, automatically drop one tier (desktop -> tablet limits, tablet -> mobile limits) and log the demotion to console
- FPS monitored via `performance.now()` delta in the render loop, not via stats.js in production

### WebGL Context Rules

- **ONE WebGL context only.** The `#visualizer-canvas` is the sole WebGL surface on the page. No secondary canvases, no node globe, no Chart.js WebGL mode. This is non-negotiable.
- If the browser cannot create a WebGL2 context, fall back to WebGL1. If neither is available, show a static hero image with CSS-animated pulse effect and the HUD metrics.

### Texture Resolution Limits

- Particle sprites: 64x64 max on mobile, 128x128 on desktop
- Star corona noise texture: 256x256 on mobile, 512x512 on desktop
- No textures above 1024x1024 anywhere in the scene
- All textures use `THREE.LinearFilter` (no mipmapping for sprites)

### Rendering Rules

- `renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))` -- cap at 2x to prevent 3x Retina GPU burn
- `renderer.antialias = false` on mobile tier; `true` on desktop
- All particle animation logic runs in GLSL vertex/fragment shaders, NOT in JavaScript. The JS render loop updates only uniform values (time, FNG color, pulse frequency). CPU cost per frame must be < 2ms.
- InstancedMesh for all repeated geometry (nodes, ring particles). Zero individual mesh objects for data elements.

---

## KILLER FEATURE

### Winner: Block Birth Celebration (Grok's Concept)

**Justification for choosing Block Birth Celebration over Block Explorer Replay:**

Block Explorer Replay (Gemini's concept) is the more ambitious idea -- scrubbing through Bitcoin's entire history is genuinely compelling. However, it requires a backend historical data API that does not exist, would need time-bucketed network statistics going back to 2009, and the data interpolation system for smooth visual replay is a multi-sprint engineering effort. It is a P3/P4 feature that depends on infrastructure Protocol Pulse does not yet have.

Block Birth Celebration is implementable in the current sprint with zero backend dependencies. It works with the existing WebSocket feed. It is the feature most likely to drive immediate social sharing because it creates a specific, screenshot-worthy, time-bounded moment that a user can capture and post. Every 10 minutes, every user on the page simultaneously experiences a celebration -- this creates community synchronicity. The share prompt with pre-formatted tweet + canvas screenshot is a direct viral growth mechanism.

Block Explorer Replay should be logged as a future roadmap item (Phase 4+) once the historical data API exists.

### Block Birth Celebration -- Implementation Approach

**Trigger:** WebSocket `block` event from mempool.space.

**Sequence (3 seconds total):**

1. **0.0s - Flash:** Central star bloom strength spikes from ambient (1.0) to peak (2.5) over 100ms. Screen briefly washes white at 20% opacity.

2. **0.1s - Shockwave:** A `THREE.RingGeometry` mesh with a custom ripple shader spawns at the star's center. It expands outward at accelerating speed over 1.5s, fading opacity from 1.0 to 0.0. The shockwave color is gold (#F8C15C). As the ring passes through nebula particles, it "captures" the highest-fee particles (those with feeRate > median) and begins their lerp animation toward accretion ring positions.

3. **0.3s - Holographic Block ID (From Grok):** A glowing block number (e.g., "#889,248") materializes at the star's core in JetBrains Mono, white with gold outline. It is rendered as a `THREE.Sprite` with a dynamically generated canvas texture (not TextGeometry, which is too expensive). The number rotates slowly on the Y axis for 2 seconds, then dissolves into particles (opacity fade + scale down to 0).

4. **0.5s - Node Synchronization Pulse:** All geographic node clusters flash to full brightness simultaneously for 500ms, then ease back to ambient. This symbolizes consensus -- every node in the world agreed.

5. **1.5s - Accretion Ring Settles:** The captured particles complete their golden-angle-positioned animation into the new ring. The ring begins its slow, permanent rotation.

6. **2.5s - Share Prompt:** A minimal, non-intrusive prompt appears in the bottom-right corner: `"Block #889,248 just confirmed. [Share]"` in JetBrains Mono. The share button captures the current WebGL frame via `renderer.domElement.toDataURL('image/png')`, opens a Twitter intent URL with the image and pre-formatted text: `"Block #889,248 just confirmed on the Bitcoin network. Witnessed live on @protocolpulse"`. The prompt auto-dismisses after 8 seconds if not clicked.

7. **3.0s - Return to Ambient:** Bloom returns to ambient level. Scene resumes normal behavior. The new accretion ring is now a permanent part of the visualization.

**Audio (opt-in only):** A single low-frequency resonant chime (100Hz sine wave, 500ms duration, generated via AudioContext) plays at t=0.0s. Audio is muted by default. Toggle in bottom-right control cluster. Visual pulse animation fires regardless of audio state (accessibility requirement from audit).

---

## IMPLEMENTATION NOTES FOR BUILD SESSION

### Ordered Priority List

This is the exact build order. Do not skip steps. Each step depends on the one before it.

**STEP 1: Amend the Animation Law (P0 -- 5 minutes)**

Before writing a single line of WebGL code, add the following amendment to the governing design laws document:

> "AMENDMENT: Data visualization hero canvases are permitted to use WebGL / Three.js. The 'No WebGL' law applies exclusively to UI chrome: buttons, cards, modals, navigation, tooltips, and page transitions. This amendment covers the Live Terminal hero canvas only and must be re-evaluated for any additional WebGL surface."

This was flagged by Gemini as a build-blocking governance risk. Without this in writing, the entire feature is technically a law violation.

**STEP 2: Build the DataService (P0 -- 2 hours)**

Architecture:
- Singleton module: `DataService`
- One `setInterval` fetch loop per unique endpoint:
  - `mempool.space/api/mempool` -- every 10 seconds
  - `mempool.space/api/v1/fees/recommended` -- every 30 seconds
  - `mempool.space/api/v1/mining/hashrate/3d` -- every 60 seconds
  - Fear & Greed API -- every 300 seconds (5 minutes)
  - `bitnodes.io/api/v1/snapshots/latest/` -- every 600 seconds (10 minutes)
- Central state cache object: `window.NetworkState = { btcPrice, mempoolVsize, feeRate, hashrate, fng, blockHeight, blockTime, nodeDistribution, lastUpdated }`
- Pub/sub via `CustomEvent` dispatched on `document`: `document.dispatchEvent(new CustomEvent('network-update', { detail: NetworkState }))`
- WebSocket wrapper for `wss://mempool.space/api/v1/ws` with:
  - Exponential backoff reconnection (1s, 2s, 4s, 8s, 16s, 30s max, 12 retries)
  - Health state exposed: `DataService.connectionState` = `'live'` | `'delayed'` | `'disconnected'`
  - `'delayed'` after 15s no message; `'disconnected'` after 30s
- All existing `fetch` calls throughout the file are deleted. No UI function ever calls `fetch` directly. Every UI component subscribes to `'network-update'` events and reads from `NetworkState`.

**STEP 3: Brand Compliance Purge (P0 -- 1 hour)**

In this exact order:
1. Delete the entire `--apple-*` CSS variable block (lines 31-36) and every reference site
2. Find-and-replace all `#000000` and `#000` backgrounds with `#0A0A0F`
3. Remove `@import` for Crimson Pro and SF Pro Display fonts
4. Find-and-replace all `font-family` declarations to `'JetBrains Mono', monospace`
5. Extract all inline `style=""` attributes into semantic CSS classes. Use BEM naming: `.hud__metric`, `.hud__status`, `.intel-drawer__panel`, `.hero__canvas`

**STEP 4: Three.js Upgrade (P0 -- 1 hour)**

1. Remove all `<script src="...three.min.js">` CDN tags (lines 790-798)
2. Add ES6 import map:
   ```html
   <script type="importmap">
   {
     "imports": {
       "three": "https://cdn.jsdelivr.net/npm/three@0.168.0/build/three.module.js",
       "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.168.0/examples/jsm/"
     }
   }
   </script>
   ```
3. Convert all Three.js usage to ES6 module imports
4. Breaking changes to handle between r128 and r168: `Material.vertexColors` is now a boolean (not `THREE.VertexColors`), `Geometry` is removed (use `BufferGeometry` only), `WebGLRenderer` defaults to WebGL2, light intensity units changed
5. Test that the renderer initializes cleanly before proceeding

**STEP 5: Delete the Node Globe (P1 -- 30 minutes)**

1. Delete `panel-node-globe` HTML (lines 595-685)
2. Delete `initNodeGlobe` function and all associated JS (lines 7726-8060)
3. Delete all CSS rules targeting `.panel-node-globe` or related selectors
4. Confirm only ONE WebGL context exists on the page: `#visualizer-canvas`

**STEP 6: Layout Restructure (P1 -- 2 hours)**

1. Restructure HTML: `#visualizer-canvas` becomes `position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0`
2. Delete all `.zone-*` divs and the `.dashboard-grid`
3. Build the bottom HUD bar: `position: fixed; bottom: 0; z-index: 10; width: 100%; backdrop-filter: blur(10px); background: rgba(10,10,15,0.82)`. Contents: BTC price (gold), mempool (white), fees (color-coded), hashrate (white), block height (white), status dot + label.
4. Build the Intel Drawer: `position: fixed; right: -400px; top: 0; height: 100vh; width: 400px; z-index: 20; transition: right 0.3s ease`. Toggled by a Pulse logo icon in the top-right corner. Contains: Sovereign Health, Epoch Progress, Mining Pools, Fee Histogram.
5. Build the connection status indicator: green dot for LIVE, yellow for DELAYED, red for DISCONNECTED. Driven by `DataService.connectionState`.

**STEP 7: Hero Visualization Build (P1 -- 4-6 hours, the core work)**

Build in this sub-order:
1. Scene setup: camera, renderer (single context), ambient light, EffectComposer + RenderPass + UnrealBloomPass
2. Central star: SphereGeometry with custom ShaderMaterial (noise-driven corona, pulsing uniforms for hashrate and price)
3. Particle system: BufferGeometry with Points, custom vertex/fragment shaders. Attributes: position, color (fee-mapped), size, spiralT (progress along golden spiral path). All animation in GLSL.
4. FNG ambient system: scene.background color lerp + ambient light color driven by fng uniform
5. Block confirmation shockwave: RingGeometry + ShaderMaterial, triggered on WebSocket block event
6. Accretion disk: InstancedMesh for settled transactions, golden-angle positioning, per-ring rotation
7. Geographic node clusters: InstancedMesh with per-instance color, positions from DataService bitnodes data
8. Block Birth Celebration sequence: bloom spike, holographic block ID sprite, node sync pulse, share prompt
9. Performance tiering: detect device, set particle/node caps, toggle bloom

**STEP 8: Audio Layer (P2 -- 1 hour)**

1. AudioContext-based heartbeat chime generator (100Hz sine, 500ms)
2. Muted by default. Toggle button in bottom-right control cluster.
3. Fires on block confirmation event regardless of visual state
4. Visual pulse animation fires simultaneously (accessibility: deaf/HoH users see the equivalent)

**STEP 9: Fallback and Accessibility (P2 -- 1 hour)**

1. WebGL detection: if no WebGL2 or WebGL1 context available, show static hero image with CSS pulse animation + HUD metrics
2. Stale data overlay: when DataService.connectionState === 'disconnected', apply CSS filter `grayscale(0.6) brightness(0.7)` to the WebGL canvas, freeze particle animation, display red "CONNECTION INTERRUPTED" in HUD
3. ARIA labels on all HUD metrics for screen readers
4. Reduced-motion media query: if `prefers-reduced-motion: reduce`, disable particle animation, show static star with HUD only

---

*This document is the single source of truth for the Live Terminal V2 build. No design decisions should be made outside this spec without updating it. The build session should reference this file by path: `/home/ultron/protocol_pulse/docs/live_terminal_design_v2.md`.*
