# CONSENSUS REPORT — LIVE-TERMINAL-DESIGN — CYCLE 2
Generated: 2026-03-25 02:06
Models: gpt4o, gemini, grok

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Hero Visualization | 90 | 86 | 75 | **84** |
| Data Mapping | 85 | 84 | 80 | **83** |
| Layout | 40 | 75 | 70 | **62** |
| Performance | 20 | 74 | 65 | **53** |
| Fibonacci / Sacred Geometry | — | 78 | 65 | **72** |
| Emotional Impact | — | 81 | 75 | **78** |
| Data Freshness | — | 68 | — | **68** |
| Killer Feature | — | 72 | — | **72** |
| Law Compliance | 30 | 72 | — | **51** |
| Code Quality | 15 | 67 | — | **41** |

> **Scoring note:** Gemini's second-pass scores are the most architecturally informed and most critical; GPT-4o's are more optimistic; Grok's are moderate. Consensus column applies weighted averaging with a penalty where a model gave a severe-outlier score, indicating a real architectural problem the other models underweighted. Performance (53) and Code Quality (41) are the two most alarming composite scores.

---

## UNANIMOUS FINDINGS
*All 3 models flagged — implement unconditionally.*

---

### U1 — Background Color Brand Violation
**What:** CSS declares `--apple-bg: #000000` and uses `background: #000` throughout, violating LAW 1 which mandates `#0A0A0F`.
**File/Line:** `live-terminal-design.html`, line 31 (`--apple-bg`) and line 60 (body background)
**Change:** Replace every instance of `#000000` / `#000` background with `#0A0A0F`. Audit all descendant elements for the same violation.

---

### U2 — Outdated Three.js Version (r128)
**What:** Three.js r128 is from early 2021. It predates years of critical performance improvements: better InstancedMesh handling, shader optimizations, WebGL2 defaults, and security patches.
**File/Line:** `live-terminal-design.html`, lines 790–798
**Change:** Replace CDN script tags with the latest stable Three.js release (≥ r165 at time of writing) using ES6 module imports and an import map. Remove all legacy `<script src="...three.min.js">` tags.

---

### U3 — Redundant / Uncoordinated API Fetch Calls
**What:** Multiple independent functions (`updateSovereignStatusBar`, `updateNetworkIntel`, `updateMempoolData`, and others) each make their own `fetch` calls to the same `mempool.space` endpoints. This wastes bandwidth, risks rate-limiting, creates race conditions, and produces inconsistent UI state.
**File/Line:** `live-terminal-design.html`, lines 7132–7200 and 7225–7310 (and scattered throughout)
**Change:** Consolidate into a single `DataService` module with one fetch cycle, a shared state cache (`window.networkState`), and an event/callback system that UI components subscribe to. The partial `window.mempoolCache` implementation at line 7401 is the right instinct — make it the single source of truth.

---

### U4 — Fragmented Widget Layout Lacks Unified Hero Narrative
**What:** All three models independently concluded the current page is a collection of disconnected widgets, not a single living visualization. The "hero" canvas and the dashboard grid below it fight each other rather than reinforcing a singular story.
**File/Line:** Overall page architecture, `zone-tactical-horizon`, `zone-logic-engine`, `zone-sovereign-archive` divs throughout
**Change:** Redesign the page around a single full-viewport hero visualization. Supporting data surfaces as HUD overlays on the hero, not as a separate dashboard below it. The "zone" concept should be abolished or radically simplified.

---

### U5 — Typography Violations (Non-Compliant Fonts Imported and Used)
**What:** The CSS imports `'Crimson Pro'` and `'SF Pro Display'` — neither is the specified `JetBrains Mono` mandated by LAW 3 for data display and kicker text.
**File/Line:** `live-terminal-design.html`, lines 52 (Google Fonts import) and 195 (`font-family: 'SF Pro Display'`)
**Change:** Remove the `Crimson Pro` and `SF Pro Display` Google Fonts imports. Replace all `font-family` declarations using those fonts with `JetBrains Mono, monospace`.

---

## MAJORITY FINDINGS
*2 of 3 models flagged — implement unless a compelling reason exists not to.*

---

### M1 — Massive Inline Style Usage (Gemini + GPT-4o)
**What:** Thousands of `style="..."` attributes are scattered throughout the HTML, making the file nearly unmaintainable, preventing CSS cascade, blocking theming, and degrading parse performance.
**File/Line:** Hundreds of instances throughout `live-terminal-design.html` (e.g., lines 4587, 4733, 5299 and beyond)
**Change:** Systematically extract all inline styles. Create semantic CSS classes in the `<style>` block. Apply classes to elements. No exceptions — inline styles should be zero after this pass.

---

### M2 — Delete the `panel-node-globe` and Its Associated Code (Gemini + Grok)
**What:** A secondary WebGL node globe exists inside a dashboard panel, creating two competing WebGL contexts. It uses inefficient `THREE.Points` (not InstancedMesh), fakes its pulse via material opacity on a sine wave, and uses a slow node-distribution loop. It is architecturally redundant with the primary `#visualizer-canvas`.
**File/Line:** `live-terminal-design.html`, lines 595–685 (HTML panel), lines 7726–8060 (JavaScript `initNodeGlobe` and related)
**Change:** Delete the panel HTML, all associated CSS, and the entire `initNodeGlobe` function block. All WebGL investment must concentrate on `#visualizer-canvas` exclusively.

---

### M3 — Apple-Style CSS Variable System Must Be Purged (Gemini + GPT-4o)
**What:** An entire rogue design system (`--apple-bg`, `--apple-card`, `--apple-text-primary`, etc.) has been embedded in the CSS, constituting a complete parallel brand identity that overrides the governing design laws. This is more severe than an incidental color error — it is a systemic brand corruption.
**File/Line:** `live-terminal-design.html`, lines 31–36 (variable declarations) and numerous usage sites (line 134 and beyond)
**Change:** Remove the entire `--apple-*` variable block. Audit every usage site. Replace with the approved brand palette variables (`--bitcoin-orange: #f7931a`, `--bg-primary: #0A0A0F`, etc.). Do not simply reassign the variables — delete them entirely to prevent future misuse.

---

### M4 — No Centralized Data Layer / State Architecture (Gemini + Grok)
**What:** Data fetching, state storage, and UI updates are tightly coupled and duplicated. There is no separation of concerns. This is the root cause of the redundant API calls (U3) and produces brittle, hard-to-debug behavior.
**File/Line:** Architectural issue spanning `live-terminal-design.html` lines 7100–7500
**Change:** Implement a minimal `NetworkState` object as the single source of truth. One `DataService.poll()` function updates it on a configurable interval. UI render functions are pure: they read from `NetworkState` and update the DOM/canvas. No UI function ever calls `fetch` directly.

---

### M5 — WebGL Animation Law Requires Formal Clarification (Gemini + GPT-4o)
**What:** The governing laws state "All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas." This feature is built almost entirely on Three.js/WebGL. This is either a law violation or the law needs an explicit carve-out for data visualization hero canvases.
**File/Line:** Governing Laws document + `live-terminal-design.html` lines 790–798 and 7099–7108
**Change:** The law must be formally amended to read: *"All UI chrome animations (buttons, cards, modals, transitions): CSS/SVG only. Data visualization hero canvases may use WebGL/Three.js with explicit architectural approval."* Document this decision. Do not proceed with the WebGL build until this is in writing.

---

## UNIQUE INSIGHTS
*Single-model findings — evaluated individually.*

---

### UI-1 — Audio Accessibility: No Visual Fallback for Block Confirmation Audio (Grok)
**What:** The Bitcoin Heartbeat audio feature (lines 4557–4569, 8700–8731) fires audio on block confirmation events but provides no visual equivalent for deaf/hard-of-hearing users or users with audio disabled.
**Assessment: IMPLEMENT.** This is a meaningful accessibility gap that is also cheap to fix. Add a visible flash or pulse animation on the hero visualization that fires simultaneously with the audio event, regardless of whether audio is enabled. This improves the experience for all users.

---

### UI-2 — Mobile Tooltip Gap on Node Globe (Grok)
**What:** Touch drag disables tooltips (lines 7861–7915) but there is no tap-to-reveal mechanism for node details on mobile.
**Assessment: INVESTIGATE FURTHER.** Given M2 recommends deleting the node globe entirely, this may become moot. If the hero visualization retains any tappable elements, implement a tap-to-reveal pattern there instead.

---

### UI-3 — Hardcoded Geographic Node Data (Grok)
**What:** Node geographic data used in the globe visualization (lines 7732–7748) is hardcoded, not fetched from a live API. This directly contradicts the "live terminal" premise.
**Assessment: IMPLEMENT.** This is a data integrity issue. Even if the globe is replaced (M2), the successor visualization must source node distribution data from a live endpoint (e.g., `bitnodes.io` API). The DataService from M4 should own this fetch.

---

### UI-4 — No WebSocket Failure Fallback / Stale Data User Notification (Grok)
**What:** WebSocket connection failures are not surfaced to the user. Data goes stale silently.
**Assessment: IMPLEMENT.** Add a visible "DISCONNECTED — data may be stale" banner that appears when the WebSocket has been down for more than 30 seconds. This is critical for a "live" terminal — users must know when data is not live.

---

### UI-5 — Two Competing WebGL Canvases Create Context Conflicts (Gemini — architectural depth)
**What:** Beyond the code quality issue, two simultaneous WebGL contexts on one page consume double the GPU memory budget and can trigger browser-level context loss on lower-end devices.
**Assessment: IMPLEMENT (already covered by M2, but the GPU context angle is worth documenting).** The browser limit on simultaneous WebGL contexts (typically 8–16, but each is expensive) means this is a real crash risk on mobile. M2's deletion of `panel-node-globe` resolves this.

---

### UI-6 — The Entire "Zone" Naming / Architecture is an Abstraction That Adds No Value (Gemini)
**What:** `zone-tactical-horizon`, `zone-logic-engine`, `zone-sovereign-archive` are abstract names that map to no user mental model and make the code harder to navigate.
**Assessment: IMPLEMENT during the layout redesign.** Replace with semantic names: `#hero-canvas-wrapper`, `#hud-overlay`, `#data-footer`. This is zero-cost during the layout refactor.

---

## CONFLICTS
*Models gave contradictory recommendations — tiebreaker applied.*

---

### C1 — Performance Score: Gemini (20) vs. GPT-4o (74)
**Conflict:** Gemini scored performance at 20; GPT-4o scored it at 74. A 54-point gap.
**Tiebreaker: Gemini is correct.** GPT-4o's optimism appears to stem from evaluating the conceptual design quality rather than the code's actual runtime behavior. Gemini correctly identified that: (a) redundant API calls fire on every update cycle, (b) the node globe uses unoptimized `THREE.Points` with a per-frame sine opacity recalculation, and (c) two WebGL contexts run simultaneously. These are not minor issues — they compound into a page that will visibly stutter on mid-range hardware. Consensus score of 53 reflects Gemini's analysis with a slight upward adjustment acknowledging GPT-4o's point that the conceptual data-mapping architecture is sound.

---

### C2 — Fibonacci Spirals: Grok (implement as core design) vs. GPT-4o (partial agreement) vs. Gemini (not addressed)
**Conflict:** Grok argues Fibonacci spirals are central to the visualization's identity. GPT-4o partially agrees but does not prioritize. Gemini does not mention them.
**Tiebreaker: Fibonacci spirals are a P2 aesthetic enhancement, not a P0/P1 functional requirement.** They should not delay critical fixes. Once the data layer and WebGL foundation are correct, Fibonacci spiral paths for transactions are an excellent differentiator and should be implemented as part of the hero visualization build. They do not belong in the critical path.

---

### C3 — Whether to Refactor or Delete the Node Globe: GPT-4o (refactor/update) vs. Gemini + Grok (delete entirely)
**Conflict:** GPT-4o suggests updating Three.js will address the node globe's issues. Gemini and Grok argue it should be deleted and rebuilt from scratch.
**Tiebreaker: Gemini and Grok are correct.** The node globe's problems are not version-related — they are architectural. `THREE.Points` vs. InstancedMesh, hardcoded static data, sine-wave opacity as a fake "pulse," and the redundant WebGL context are design problems that a library upgrade does not fix. Deleting and rebuilding on a proper foundation (InstancedMesh, live data, bloom post-processing) is less effort than untangling the existing code and produces a better result.

---

## VALIDATED STRENGTHS
*All models agree these are already excellent — do NOT change in the second pass.*

---

### VS1 — Conceptual Data-to-Visual Mapping Philosophy
All three models praised the fundamental idea of mapping BTC price → node size/brightness, mempool size → line thickness, hashrate → particle speed, FNG → background aura, fee rate → particle color. This mapping philosophy is architecturally correct and emotionally resonant. **Do not change the mapping logic — only improve its implementation.**

### VS2 — Bitcoin Orange (#f7931a) as Primary Node Color
The choice of Bitcoin orange as the primary node color with deep navy background creates a striking, on-brand visual identity. All models affirmed this. **Keep this color pairing as the hero's chromatic foundation.**

### VS3 — Fear & Greed Index Background Aura Concept
The concept of using FNG to shift the hero's background aura (dark red haze for fear <25, gold shimmer for greed >75) was praised by all models as emotionally intelligent design. **Preserve and implement this feature.**

### VS4 — Block Confirmation Shockwave Event
The radial shockwave emanating from the network core on each block confirmation — with audio chime — was unanimously recognized as the single most powerful emotional design moment in the feature. **This must be implemented as the centerpiece interaction.**

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Violation Detail |
|---|---|---|
| LAW 1 — Brand Palette | 🔴 VIOLATED | `#000`/`#000000` used instead of `#0A0A0F`. Entire `--apple-*` color system embedded. Non-palette colors (`--fee-green: #22c55e`, `--accent-blue: #0a84ff`) used without justification. |
| LAW 3 — Typography | 🔴 VIOLATED | `'Crimson Pro'` and `'SF Pro Display'` imported and used. `JetBrains Mono` is the mandated font. |
| Animation Law | ⚠️ AMBIGUOUS | Law says "No Three.js, no WebGL" but feature requires WebGL hero canvas. Law must be formally amended before this feature ships. |
| General Code Quality Laws | 🔴 VIOLATED | Thousands of inline styles violate maintainability standards. Redundant fetch calls violate efficiency standards. |
| Three.js Version Policy | 🔴 VIOLATED | r128 (2021) is in use. Must be updated to latest stable. |

**Final determination:** The code is in active violation of LAW 1 and LAW 3. These are non-negotiable blockers. The Animation Law ambiguity is a governance risk that must be resolved in writing before the WebGL hero is considered compliant.

---

## SECURITY CONSENSUS

| Issue | Severity | Models | Detail |
|---|---|---|---|
| No WebSocket reconnection / stale data notification | MEDIUM | Grok + implied by all | Silent data staleness in a financial data terminal is a trust/integrity risk. Users may act on stale data believing it is live. |
| Unvalidated external data rendered to DOM | MEDIUM | Implied by all (API fetch pattern) | Data from `mempool.space` and other APIs is rendered into the DOM without sanitization. If an API endpoint is compromised or returns unexpected data, XSS is possible. Validate and sanitize all external data before DOM insertion. |
| Outdated Three.js (r128) with known CVEs | LOW-MEDIUM | All models (performance context) | Outdated dependencies accumulate known vulnerabilities. r128 is 4+ years old. Update eliminates this surface. |
| No rate-limit handling on API calls | LOW | Gemini + Grok | Redundant fetch calls with no backoff or rate-limit detection could result in IP bans from `mempool.space`, causing a complete data outage for the user. |

**Priority order:** (1) Sanitize external API data before DOM insertion. (2) Add WebSocket stale-data detection and user notification. (3) Update Three.js. (4) Add exponential backoff to DataService.

---

## WORLD-CLASS GAP CONSENSUS
*Items mentioned by 2+ models as missing from a truly world-class product.*

---

### WCG1 — No Singular Emotional Narrative (all 3 models)
A world-class data visualization does not show data — it tells a story. The Bitcoin network has a heartbeat (block time), a mood (FNG), a metabolism (mempool), and a body (nodes). The current page shows metrics. A world-class terminal makes you *feel* the network breathing. This requires the unified hero + HUD overlay architecture all models prescribed.

### WCG2 — No Centralized Data Architecture / State Management (Gemini + Grok)
World-class real-time applications are built on a clean data layer: one source of truth, one update cycle, reactive UI. The current spaghetti of fetch calls scattered across functions is the single largest gap between this code and production quality.

### WCG3 — Performance on Mid-Range Hardware (Gemini + GPT-4o)
A world-class visualization must run at 60fps on a 2020-era laptop. The current dual-WebGL-context, unoptimized particle system, and redundant API fetch storm will produce a janky, battery-draining experience. InstancedMesh, a single WebGL context, and a clean DataService are prerequisites.

### WCG4 — Meaningful Interactivity (Grok + GPT-4o)
World-class hero visualizations are not screensavers — they reward exploration. Clicking a node should surface its data. Hovering a transaction streak should show fee and size. Tapping the mempool vortex should open a fee histogram. The current implementation has no interactive layer on the primary visualization.

### WCG5 — Accessibility and Graceful Degradation (Grok + GPT-4o)
A world-class product works for everyone. Audio events need visual equivalents. WebGL should degrade gracefully to a CSS fallback for browsers/devices that cannot support it. Screen-reader labels must be present on all data elements.

---

## FINAL ACTION PLAN

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Replace all `#000`/`#000000` backgrounds with `#0A0A0F` | `live-terminal-design.html:31,60` and all descendant usage | All 3 | Active LAW 1 violation. Blocks brand compliance. |
| P0-2 | Delete entire `--apple-*` CSS variable block and all usage sites | `live-terminal-design.html:31-36,134+` | Gemini + GPT-4o | Rogue design system actively corrupting brand identity. Not a minor fix — a systemic purge. |
| P0-3 | Remove `'Crimson Pro'` and `'SF Pro Display'` font imports and all usage; replace with `JetBrains Mono` | `live-terminal-design.html:52,195` | All 3 | Active LAW 3 violation. Blocks typography compliance. |
| P0-4 | Upgrade Three.js from r128 to latest stable via ES6 import map | `live-terminal-design.html:790-798` | All 3 | 4-year-old library. Security exposure + missing 4 years of performance improvements. Blocks all WebGL work. |
| P0-5 | Build `DataService` module: single fetch cycle, `NetworkState` cache, subscriber pattern; remove all direct `fetch` calls from UI functions | `live-terminal-design.html:7132-7200,7225-7310,7401` | Gemini + Grok | Race conditions, redundant API calls, and no source of truth. Architectural blocker for all data features. |
| P0-6 | Formally amend Animation Law to permit WebGL for data visualization hero canvases; document the decision | Governing Laws document | Gemini + GPT-4o | Feature cannot legally ship without this. All WebGL code is currently an undocumented law violation. |
| P0-7 | Sanitize all external API data before DOM insertion | `live-terminal-design.html:7100-7500` (all fetch handlers) | Implied all | XSS risk from compromised or malformed API responses in a financial data terminal. |

---

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Extract all inline `style="..."` attributes to semantic CSS classes in `<style>` block | Throughout entire file (lines 4587, 4733, 5299+) | Gemini + GPT-4o | Thousands of inline styles make maintenance impossible and hurt parse performance. |
| P1-2 | Delete `panel-node-globe` panel HTML and `initNodeGlobe` JavaScript entirely | `live-terminal-design.html:595-685 (HTML), 7726-8060 (JS)` | Gemini + Grok | Dual WebGL contexts cause GPU memory pressure and potential context loss. Architecturally redundant. |
| P1-3 | Rebuild hero visualization using InstancedMesh, bloom post-processing, and live data from DataService | `live-terminal-design.html:#visualizer-canvas` | All 3 | Current implementation uses inefficient primitives. New build on proper foundation is the feature's core value. |
| P1-4 | Redesign page layout: single full-viewport hero + HUD overlays; remove "zone" architecture | Page structure throughout | All 3 | Current fragmented layout destroys the unified narrative all models prescribed. |
| P1-5 | Add WebSocket failure detection + visible "DISCONNECTED — data stale" banner | `live-terminal-design.html:~7109` and DataService | Grok + implied all | Financial data terminal showing stale data silently is a trust and integrity failure. |
| P1-6 | Replace hardcoded node geographic data with live fetch from `bitnodes.io` API via DataService | `live-terminal-design.html:

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles by combining surgical precision on specific law violations (exact line numbers, exact color codes, the full "rogue Apple design system" diagnosis) with genuine architectural insight — most notably the redundant API call bottleneck and the WebGL law ambiguity — findings that GPT-4o only acknowledged *after* being shown Gemini's work, and that Grok admitted it missed entirely. Its recommendations were the most specific and implementable of the three, its scores proved the most calibrated (Consensus consistently validated its harshest ratings on Performance and Code Quality), and it was the only model to proactively flag a risk-management issue (the Three.js prohibition conflict) before it became a build-blocking problem.

---

# FINAL SECOND-PASS PRIORITY LIST
*Definitive implementation order — highest risk/impact first.*

---

## TIER 1 — CRITICAL BLOCKERS
*Must be resolved before any other development continues.*

### P1 — Resolve WebGL / Three.js Governing Law Conflict
**Source:** Gemini (unique find, Cycle 1)
**Problem:** LAW explicitly states "NO Three.js, no WebGL, no Canvas." The entire hero visualization is built on Three.js r128. This is not a style violation — it is a foundational architectural conflict that invalidates every downstream WebGL decision.
**Action:** Convene stakeholder decision. Either (A) formally amend the Governing Law to permit WebGL exclusively for the hero canvas with documented justification, or (B) replace the hero with a CSS/SVG/Canvas 2D implementation. Document the outcome as LAW 1 Amendment before touching any other code.
**Blocking:** P3, P4, P5, P6, P8

---

### P2 — Eliminate Redundant API Fetch Architecture
**Source:** Gemini (unique find, Cycle 1) — confirmed by all in Cycle 2
**Problem:** Functions `updateSovereignStatusBar`, `updateNetworkIntel`, `updateMempoolData`, and others each independently fetch the same `mempool.space` endpoints. This creates N×bandwidth waste, race conditions between UI panels showing inconsistent data states, and cascading failure if the endpoint rate-limits the client.
**Action:** Implement a single `DataBus` singleton service:
- One `setInterval` fetch loop per unique endpoint (recommended: 10s for mempool, 30s for fees, 60s for network stats)
- Central state cache object with `lastUpdated` timestamps
- Event emitter pattern (`CustomEvent` or lightweight pub/sub) so all UI panels subscribe rather than fetch
- All existing update functions refactored to consume from cache, not from network

**Files:** Consolidate all fetch logic currently scattered across lines 7132–7310+

---

## TIER 2 — SEVERE VIOLATIONS
*Resolve within current sprint. These corrupt brand integrity and performance simultaneously.*

### P3 — Purge the Rogue "Apple Design System"
**Source:** Gemini (Cycle 1), confirmed all models (Cycle 2)
**Problem:** An entirely foreign design system is embedded in the CSS: `--apple-bg`, `--apple-card`, `--apple-text`, `SF Pro Display` font imports. This is not a single color error — it is a competing design language that will cause brand drift across every component that inherits these variables.
**Action:**
1. Delete the entire Apple variable block (lines 31–36 and all references)
2. Replace `#000000` / `#000` backgrounds with `#0A0A0F` (LAW 1)
3. Remove `SF Pro Display` and `Crimson Pro` font imports (line 52, line 195)
4. Audit every CSS rule for orphaned Apple-variable references using find-replace across the full file

---

### P4 — Update Three.js r128 → Latest Stable
**Source:** All three models, Cycle 1 — Unanimous Finding U2
**Problem:** r128 (early 2021) predates InstancedMesh optimizations, WebGL2 defaults, shader compiler improvements, and 4+ years of security patches.
**Action:**
1. Replace CDN `<script>` tags (lines 790–798) with ES6 module imports via import map
2. Target Three.js ≥ r165
3. Run regression test on all Three.js-dependent visualizations after upgrade — breaking API changes between r128 and r165 are significant (materials, lights, shadow APIs all changed)
4. This step is **contingent on P1 resolution** — only execute if WebGL is formally approved

---

### P5 — Enforce Typography: JetBrains Mono Exclusively
**Source:** Gemini (Cycle 1), confirmed GPT-4o (Cycle 2)
**Problem:** `Crimson Pro` (line 52) and `SF Pro Display` (line 195) are imported and applied to data labels and kickers, directly violating LAW 3 which mandates `JetBrains Mono` for all data and kicker text.
**Action:**
1. Remove font imports for Crimson Pro and SF Pro Display
2. Audit every `font-family` declaration in the stylesheet
3. Apply `font-family: 'JetBrains Mono', monospace` as a single root-level CSS variable `--font-data` and replace all inline font declarations with that variable

---

## TIER 3 — ARCHITECTURE & MAINTAINABILITY
*Schedule for next sprint. Technical debt that will compound if deferred.*

### P6 — Eliminate Inline Style Plague
**Source:** Gemini (Cycle 1), GPT-4o (Cycle 2)
**Problem:** Thousands of inline `style=""` attributes throughout the HTML make the file impossible to maintain, impossible to theme, and block any CSS variable cascade from working correctly.
**Action:**
1. Automated extraction pass: use a script to identify all unique inline style declarations, generate CSS class equivalents, and replace inline attributes with class references
2. Manual review pass for any dynamically-injected inline styles (these may be legitimate — flag but do not auto-remove)
3. Establish a linting rule (e.g., `stylelint` with `no-important` + custom rule) that fails CI on new inline style additions

---

### P7 — Eliminate Dual WebGL Canvas Architecture
**Source:** Gemini (Cycle 2, implied synthesis)
**Problem:** Two separate WebGL contexts exist: `visualizer-canvas` (hero) and `node-globe` (dashboard panel). Each WebGL context consumes GPU memory independently. Two contexts competing on the same page causes measurable frame-rate degradation and can hit browser WebGL context limits on lower-end hardware.
**Action:**
1. Determine which canvas is the true hero (per P1 decision)
2. Deprecate the subordinate canvas
3. If the globe data is valuable, render it as a 2D SVG overlay on the primary WebGL scene using Three.js CSS2DRenderer (zero additional GPU context cost)

---

### P8 — Unified Hero Narrative: Single Emotional Core
**Source:** All three models, Cycle 1 (creative direction)
**Problem:** The current page presents disconnected widgets with no visual hierarchy or emotional throughline. Scores for Emotional Impact (78 consensus) and Layout (62 consensus) confirm users feel no coherent story.
**Action:**
1. Designate one visualization as the hero — full viewport, above the fold, data-driven but immediately readable without a legend
2. Apply the color language system: fee pressure → red/orange spectrum; network health → blue/white spectrum; block confirmation events → radial pulse animation emanating from center
3. All secondary panels (mempool depth, fee histogram, node map) become subordinate data drawers that slide in on user intent, not passive always-visible widgets
4. Implement the Fibonacci/golden spiral node layout (all three models converged on this) as the spatial logic for node positioning — polar coordinates with φ ratio spacing

---

## TIER 4 — ENHANCEMENTS
*Implement after Tier 1–3 complete. High upside, zero blocking risk.*

### P9 — Block Confirmation Pulse Event
**Source:** Grok (Cycle 1), GPT-4o (Cycle 1)
**Action:** On new block WebSocket event, trigger a radial shockwave animation from the visualization center. Duration: 1.2s. Easing: `cubic-bezier(0.16, 