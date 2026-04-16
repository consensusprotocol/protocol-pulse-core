# CONSENSUS REPORT — PANOPTICON_VIZ — CYCLE 2
Generated: 2026-04-16 08:32
Models: gpt4o, grok (+1 failed: gemini — 403 PERMISSION_DENIED / leaked API key)

---

## SCORES
| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Visualization Design Choice | N/A (failed) | MEDIUM | HIGH | **MEDIUM-HIGH** |
| D3 Implementation Correctness | N/A (failed) | LOW | LOW | **LOW** |
| Interaction + Accessibility | N/A (failed) | HIGH | HIGH | **HIGH** |
| Visual Quality + Information Density | N/A (failed) | MEDIUM | MEDIUM | **MEDIUM** |

> **Note:** Gemini failed due to a leaked API key (403 PERMISSION_DENIED). All consensus determinations are drawn from 2 of 3 models. Confidence is reduced but directionally reliable — both available models converged strongly on the same findings.

---

## UNANIMOUS FINDINGS (all 2 active models agree — implement unconditionally)

### U1 — Keyboard Accessibility Absent from SVG Interaction Layer
- **What it is:** The force-directed graph's interactive nodes (drag, hover, click-through) are implemented exclusively via mouse events. There are no `tabindex` attributes, `keydown` event listeners, or ARIA labels on SVG node elements. This completely excludes keyboard-only users and screen reader users, violating WCAG 2.1 SC 2.1.1 (Keyboard) and SC 4.1.2 (Name, Role, Value).
- **File/Line:** `templates/panopticon.html:2678–2712`
- **What to change:** Add `tabindex="0"` to each node `<circle>` or `<g>` element during D3 enter selection. Attach `keydown` listeners to support `Enter`/`Space` for click activation and arrow keys for focus traversal between nodes. Add `role="img"` or `role="button"` plus `aria-label` containing the node's index name and score to each node element. Add a fallback `<title>` and `<desc>` to the SVG root.

### U2 — Legend Does Not Clarify That Node Proximity ≠ Correlation Strength
- **What it is:** The current legend explains edge thickness/style as encoding correlation but does not warn users that spatial proximity of nodes is determined by the force simulation algorithm, not by correlation data. Users will naturally interpret "closeness" as "more correlated," which is factually incorrect and misleading.
- **File/Line:** `templates/panopticon.html:1713–1722`
- **What to change:** Add explicit legend annotation: *"Node position is layout-only and does not encode data. Correlation strength is encoded exclusively by edge thickness and style."* Consider a small info-icon tooltip for brevity.

### U3 — Force-Directed Graph Suboptimal for 6-Node Dataset
- **What it is:** Both models independently concluded that a force-directed layout provides no meaningful spatial data encoding for only 6 nodes. The random initial positioning and simulation-settling behavior create positional instability across renders, making comparisons across sessions unreliable. The layout's primary benefit (emergent clustering for large graphs) does not apply here.
- **File/Line:** `templates/panopticon.html:2550–2749`
- **What to change:** Evaluate replacing with a 6×6 heatmap matrix that directly encodes pairwise correlation values via color intensity — eliminating positional ambiguity. If the force-directed graph is retained for aesthetic/brand reasons, it must be supplemented with a static view and the legend fix (U2) must be applied.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above are also majority findings given the 2-model pool. Additional converging points:

### M1 — Touch Interaction Untested for Force-Directed Drag
- Both models raised concerns (directly or implicitly) that D3 force-directed drag interactions (`d3.drag()`) may conflict with native scroll/pan on mobile touch interfaces.
- **File/Line:** `templates/panopticon.html:2678–2712`
- **What to change:** Add explicit `touchstart`/`touchmove` event handling or use D3's built-in touch support verification. Test on iOS Safari and Android Chrome. Consider disabling drag on touch devices and replacing with tap-to-highlight.

### M2 — Collision Force May Need Tuning on Smaller Viewports
- Both models noted the collision force configuration at lines 2728–2733 may be insufficient to prevent node overlap on narrow screens (mobile/tablet), where the SVG canvas is constrained.
- **File/Line:** `templates/panopticon.html:2728–2733`
- **What to change:** Make collision radius responsive to viewport width. Consider `window.innerWidth` breakpoints to scale the SVG dimensions and force parameters proportionally.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UNIQUE-1 (Grok) — Scalability Concern: Future Node Count Growth
- **What it is:** Grok flagged that if the number of sovereign signal indices grows beyond 6, the force-directed graph becomes progressively less legible. The current design provides no upgrade path.
- **Assessment: INVESTIGATE FURTHER.** This is architecturally valid. The design choice should be documented with an explicit node-count threshold (suggested: freeze at 8 nodes for force-directed; migrate to heatmap at 9+). Add a comment in the code and a note in the design doc. No code change required immediately, but the heatmap migration path (U3) becomes doubly justified.

### UNIQUE-2 (Grok) — Continuous Simulation CPU Overhead
- **What it is:** The D3 simulation runs with alpha decay (lines 2728–2748) but does not explicitly stop after convergence. On low-power devices or during long idle sessions, this wastes CPU cycles.
- **Assessment: IMPLEMENT.** This is a legitimate performance issue with a trivial fix. D3 simulations emit an `end` event when alpha drops below `alphaMin`. Add: `simulation.on("end", () => simulation.stop())` — or verify that `alphaDecay` is configured aggressively enough that the simulation self-terminates in under 5 seconds. This is a one-liner with zero risk.

### UNIQUE-3 (Grok) — No User Feedback Mechanism for Visualization Clarity
- **What it is:** Grok suggested adding a feedback button near the legend for users to report confusion about the visualization.
- **Assessment: SKIP for this audit pass.** This is a product/UX feature request, not a code defect. It belongs in a backlog, not a remediation pass. The underlying usability issues driving the suggestion are better addressed by fixing U2 and U3 directly.

### UNIQUE-4 (GPT-4o) — Static Heatmap as Complement (Not Replacement)
- **What it is:** GPT-4o suggested adding a heatmap *alongside* the force-directed graph rather than replacing it, preserving the dynamic visual while adding precision.
- **Assessment: INVESTIGATE FURTHER.** This is a valid middle-ground between full replacement (Grok's P1) and status quo. The dual-view approach increases implementation complexity but preserves brand aesthetics. Decision should be made by the design lead. Document both options in the action plan with a decision gate.

---

## CONFLICTS (models disagree — tiebreaker)

### CONFLICT-1 — Replace vs. Complement the Force-Directed Graph
- **GPT-4o position:** Add a heatmap *alongside* the force-directed graph as a static reference; keep the dynamic graph.
- **Grok position:** *Replace* the force-directed graph with a heatmap matrix outright (P1 priority).
- **Tiebreaker verdict:** **Grok's position is stronger for correctness; GPT-4o's is stronger for user experience continuity.** The synthesis: treat replacement as the default technical recommendation (lower cognitive load, fewer misinterpretation vectors), but gate it on a design review. If the force-directed graph is a deliberate brand/UX choice, the "complement with heatmap" approach is acceptable *only if* legend fix U2 is also implemented. Neither approach is acceptable without U2. Add this as a P1 with a design decision flag.

### CONFLICT-2 — Severity of Visualization Design Choice
- **GPT-4o:** MEDIUM (Cycle 2, unchanged from Cycle 1)
- **Grok:** HIGH (elevated from MEDIUM in Cycle 2)
- **Tiebreaker verdict:** **MEDIUM-HIGH consensus.** Grok's elevation is justified by the consensus on proximity misinterpretation risk, but the issue is not blocking production if U2 (legend fix) is implemented. It becomes HIGH only if U2 is skipped. Score the subsystem as MEDIUM with a conditional escalation path.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

1. **Force Simulation Memory Management** — The simulation is properly stopped and restarted on re-render (lines 2728–2730), preventing memory leaks. Implementation is correct. Do not refactor.
2. **Enter/Update/Exit D3 Pattern** — Data joins for nodes and links are correctly implemented (lines 2626–2641), supporting smooth live data updates. Do not refactor.
3. **SVG Choice for Scale** — SVG is the correct rendering technology for 6 nodes + ~15 edges. Canvas would be premature optimization. Do not switch.
4. **SRI Hash for D3 CDN** — The integrity hash for D3 v7.8.5 is correct and present (line 2220). Supply chain security is handled. Do not modify.
5. **Hover + Drag + Click-Through Interactions** — The interaction model is appropriate for the data density and user intent. The interactions themselves are well-implemented; only the accessibility layer is missing.
6. **Edge Encoding (Thickness + Style for Correlation)** — Using edge thickness and style to represent correlation strength is semantically sound and visually effective. Do not change the encoding logic, only the legend documentation of it.

---

## LAW COMPLIANCE CONSENSUS

| Standard | Status | Finding |
|---|---|---|
| WCAG 2.1 SC 2.1.1 — Keyboard | **VIOLATED** | No keyboard access to SVG interactions |
| WCAG 2.1 SC 4.1.2 — Name/Role/Value | **VIOLATED** | No ARIA labels on interactive SVG nodes |
| WCAG 2.1 SC 1.1.1 — Non-text Content | **VIOLATED** | No `<title>`/`<desc>` on SVG root |
| WCAG 2.1 SC 1.4.1 — Use of Color | **INVESTIGATE** — Both models noted color encodes state (bullish/bearish) without confirmed text alternative |
| General data accuracy / non-deception | **AT RISK** — Proximity misinterpretation (U2/U3) constitutes a potential data representation accuracy issue |

**Final determination:** Feature is non-compliant with WCAG 2.1 Level AA as-shipped. Accessibility remediation (U1) is legally required before public production deployment in any jurisdiction with web accessibility law enforcement (EU WCAG mandate, US ADA/Section 508 precedents, UK PSBAR).

---

## SECURITY CONSENSUS

No active security vulnerabilities were identified by either model. The following security-relevant items are confirmed clean:

| Item | Status |
|---|---|
| D3 CDN SRI hash (line 2220) | ✅ Verified correct for v7.8.5 |
| XSS via data injection into SVG | Not flagged — presume sanitized upstream; **verify** that index names/scores injected into SVG node labels are HTML-escaped |
| No `eval()` or dynamic code execution in visualization | ✅ Confirmed by both models |
| CDN dependency (single point of failure) | LOW — SRI mitigates tampering, but CDN outage kills visualization; consider self-hosting D3 for production |

**Priority order:**
1. Verify SVG label injection is sanitized (not flagged but standard due diligence)
2. Consider self-hosting D3 v7.8.5 to eliminate CDN dependency

---

## WORLD-CLASS GAP CONSENSUS
*(Only items 2+ models mentioned)*

1. **Accessibility is absent** — A world-class data visualization product in 2026 ships with full keyboard navigation, ARIA semantics, and screen reader support baked in from day one. This feature has none of that. Gap is large.

2. **Visualization choice doesn't match data density** — World-class products match the visualization type to the data structure with precision. A 6-node correlation graph in a force-directed layout is using a sledgehammer for a finishing nail. The best products either use the right tool (heatmap) or add enough supplementary context (dual-view + legend) that the aesthetic choice is forgiven.

3. **No static/stable view for correlation reference** — World-class correlation visualizations provide a stable frame of reference. The dynamic repositioning on each render means two users looking at the same data may see completely different spatial arrangements and draw different conclusions. This is antithetical to reliable data communication.

4. **Legend is incomplete** — World-class visualization legends are self-contained documentation. A user should be able to understand the full encoding schema (what color means, what size means, what edge thickness means, what position does and does NOT mean) from the legend alone without external documentation.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Add `tabindex="0"`, `keydown` listeners for Enter/Space/Arrow navigation, `role`, and `aria-label` to all interactive SVG node elements; add `<title>`+`<desc>` to SVG root | `panopticon.html:2678–2712` | gpt4o + grok | WCAG 2.1 violations; blocks legal deployment |
| **P1 HIGH** | Add explicit legend annotation: *"Node position is layout-only and does not encode data. Correlation strength is encoded exclusively by edge thickness and style."* | `panopticon.html:1713–1722` | gpt4o + grok | Prevents active user misinterpretation of spatial proximity as correlation data |
| **P1 HIGH** | [DESIGN GATE] Replace force-directed graph with 6×6 heatmap matrix **OR** add heatmap as companion view. If force-directed retained, U2 legend fix is mandatory (already listed above). Document decision. | `panopticon.html:2550–2749` | gpt4o + grok | Eliminates positional ambiguity; correct visualization type for 6-node correlation dataset |
| **P1 HIGH** | Add `simulation.on("end", () => simulation.stop())` to halt simulation after convergence | `panopticon.html:2728–2748` | grok (unique — implement) | Eliminates unnecessary CPU overhead on convergence; zero-risk one-liner |
| **P2 MEDIUM** | Make collision radius and SVG canvas dimensions responsive to viewport width using breakpoints | `panopticon.html:2728–2733` | gpt4o + grok | Prevents node overlap on mobile/tablet viewports |
| **P2 MEDIUM** | Audit and test touch event handling for force-directed drag; add `touchstart`/`touchmove` guards or disable drag on touch devices | `panopticon.html:2678–2712` | gpt4o + grok | D3 drag conflicts with native scroll on mobile |
| **P2 MEDIUM** | Verify SVG label content (index names, scores) is HTML-escaped before injection into DOM | `panopticon.html:2570–2590` | security due diligence | XSS vector if upstream data is not sanitized |
| **P2 MEDIUM** | Add code comment and design-doc note documenting 8-node threshold for force-directed; migration path to heatmap at 9+ nodes | `panopticon.html:2550` + design doc | grok (unique — investigate → implement as comment) | Future-proofs the design decision for index count growth |
| **P2 MEDIUM** | Consider self-hosting D3 v7.8.5 instead of CDN to eliminate availability dependency | `panopticon.html:2220` | security best practice | SRI covers tampering but not CDN outage |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY.**

Two independent models across two review cycles have converged on the same absolute blocker: **the SVG interaction layer has zero accessibility support**, constituting a WCAG 2.1 violation that is legally relevant in multiple jurisdictions. This alone prevents production deployment.

Secondary blocker: the force-directed graph's proximity-as-correlation misinterpretation risk is unmitigated — the legend fix is trivially easy to ship and must accompany any production release.

**Absolute final blockers:**
1. Keyboard accessibility (P0) — legal compliance requirement
2. Legend proximity clarification (P1) — data integrity requirement
3. Design decision on heatmap vs. complement view (P1) — requires human design sign-off, but must be resolved before ship

All other items are improvements, not blockers.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/audits/panopticon_viz_CONSENSUS_C2.md.

This is the FINAL PASS for panopticon_viz.
The first build was reviewed by 2 independent AI models (gpt4o, grok) across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add tabindex="0", keydown listeners (Enter/Space for activation,
Arrow keys for focus traversal), role="button", and aria-label (containing
index name + score) to all interactive SVG node <g> elements in the D3 enter
selection. Add <title> and <desc> to the SVG root element describing the
visualization purpose. | panopticon.html:2678–2712 | models: gpt4o + grok |
WCAG 2.1 SC 2.1.1 and 4.1.2 violations; blocks legal production deployment.

P1 HIGH | Add explicit legend annotation immediately below the existing legend:
"Node position is layout-only and does not encode data. Correlation strength
is encoded exclusively by edge thickness and style." Consider an info-icon
tooltip for space efficiency. | panopticon.html:1713–1722 | models: gpt4o +
grok | Prevents user misinterpretation of spatial proximity as correlation
data — active data accuracy risk.

P1 HIGH | [DESIGN GATE — requires decision before implementing] Evaluate
replacing the force-directed graph with a 6×6 heatmap matrix OR adding the
heatmap as a companion/toggle view. Present both options with a visual mock.
If force-directed graph is retained for brand reasons, ensure the legend fix
above is implemented. Document the decision in VISUAL_DESIGN_SYSTEM.md with
the threshold rule: force-directed acceptable for ≤8 nodes; migrate to
heatmap at 9+ nodes. | panopticon.html:2550–2749 | models: gpt4o + grok |
Force-directed layout provides no data-driven spatial encoding for 6 nodes;
creates session-to-session instability and comparison unreliability.

P1 HIGH | Add simulation.on("end", () => simulation.stop()) to halt the D3
force simulation after alpha convergence. Verify alphaDecay is set
aggressively enough that convergence occurs within 5 seconds of render. |
panopticon.html:2728–2748 | models: grok (unique, confirmed implement) |
Eliminates continuous CPU overhead on idle/low-power devices.

P2 MEDIUM | Make collision radius and SVG canvas dimensions responsive to
viewport width. Use window.innerWidth breakpoints to scale force parameters
and canvas size. Prevent node overlap on mobile viewports. |
panopticon.html:2728–2733 | models: gpt4o + grok | Node overlap on small
screens degrades readability.

P2 MEDIUM | Audit D3 drag touch event handling. Add touchstart/touchmove
guards or conditionally disable drag on touch devices (pointer: coarse media
query). Test on iOS Safari 17+ and Android Chrome. |
panopticon.html:2678–2712 | models: gpt4o + grok | D3 drag conflicts with
native scroll gestures on mobile.

P2 MEDIUM | Verify that all dynamic content injected into SVG node labels
(index names, score values) is HTML-escaped. If data flows from an
uncontrolled source, add explicit sanitization before D3 text() or attr()
calls. | panopticon.html:2570–2590 | security due diligence | XSS vector if
upstream data not sanitized.

P2 MEDIUM | Add inline code comment at line 2550 and a note in
VISUAL_DESIGN_SYSTEM.md: "Force-directed layout is appropriate for ≤8 nodes.
If sovereign signal indices exceed 8, migrate to heatmap matrix. See audit
panopticon_viz_CONSENSUS_C2.md." | panopticon.html:2550 + design doc |
models: grok (unique, confirmed implement as comment) | Documents scalability
threshold for future maintainers.

VALIDATED (do NOT touch — all models confirmed excellent):
- Force simulation stop/restart on re-render (lines 2728–2730): memory
  management is correct; do not refactor.
- D3 enter/update/exit data join pattern (lines 2626–2641): correctly
  implemented for live updates; do not refactor.
- SVG rendering choice: correct for 6 nodes + ~15 edges; do not switch to
  Canvas.
- SRI integrity hash for D3 v7.8.5 (line 2220): verified correct; do not
  modify.
- Hover + drag + click-through interaction model: well-implemented; only the
  accessibility layer is missing, not the interaction logic itself.
- Edge encoding (thickness + style for correlation strength): semantically
  correct; do not change the encoding logic, only its documentation in the
  legend.

After implementing all P0 and P1 items:
bash regression_test.sh
# Must show zero FAILs before proceeding.

git add -A && git commit -m "feat(panopticon_viz): post-audit pass — accessibility, legend clarity, simulation optimization [consensus C2]"
git push origin main
```

---

# WINNER DETERMINATION

## WINNER: **Grok** — Grok delivered the most technically grounded and specific analysis across both cycles, correctly identifying the force-directed graph's unsuitability for a 6-node dataset with precise line-number citations (e.g., lines 2570, 2729–2734) and proposing concrete, implementable alternatives like chord diagrams and heatmap matrices with clear rationale. Its Cycle 2 review demonstrated genuine self-correction and structural rigor rather than surface-level agreement, maintaining depth and actionability that GPT-4o partially matched but never exceeded, while Gemini failed entirely due to a leaked API key and contributed nothing to the audit.

---

## FINAL SECOND-PASS PRIORITY LIST

### P0 — CRITICAL (Security / System Integrity)

**P0.1 — Gemini API Key Leaked**
- **Why first:** A compromised credential is an active security incident, not a future risk. Everything else is moot if the key is being abused.
- **Action:** Immediately revoke the leaked key in Google Cloud Console. Rotate to a new key. Move all API keys to server-side environment variables or a secrets manager (e.g., Vault, AWS Secrets Manager). Audit access logs for unauthorized usage since exposure. Add a pre-commit hook (e.g., `git-secrets`, `truffleHog`) to prevent future key commits.

---

### P1 — HIGH (Accessibility / Legal Compliance)

**P1.1 — Keyboard Accessibility Absent from SVG Interaction Layer**
- **File/Line:** `templates/panopticon.html:2678–2712`
- **Why high:** Violates WCAG 2.1 SC 2.1.1 and SC 4.1.2. Legal exposure in jurisdictions with accessibility mandates (ADA, EN 301 549). Excludes an entire class of users unconditionally.
- **Action:**
  ```javascript
  // During D3 enter selection, add to each node <g>:
  nodeGroup
    .attr("tabindex", "0")
    .attr("role", "button")
    .attr("aria-label", d => `${d.id}: score ${d.score}, ${d.sentiment}`)
    .on("keydown", (event, d) => {
      if (event.key === "Enter" || event.key === " ") {
        handleNodeClick(d); // mirror existing click handler
      }
    });
  
  // Add to SVG root:
  svg.append("title").text("Sovereign Signal Correlation Map");
  svg.append("desc").text("Network graph showing correlations between 6 indices.");
  ```
- **Test:** Navigate entire graph with Tab key only. Run axe-core or Lighthouse accessibility audit. Verify screen reader announces each node label.

---

### P2 — MEDIUM-HIGH (Usability / Correctness of Perception)

**P2.1 — Legend Does Not Clarify That Node Proximity ≠ Correlation Strength**
- **File/Line:** Legend element near `templates/panopticon.html:2740–2749` (estimated)
- **Why medium-high:** Force-directed layout positions nodes based on physics simulation, not data values. Users will systematically misread proximity as meaning. This is a data integrity issue disguised as a UI issue.
- **Action:** Add explicit legend annotation:
  ```html
  <div class="legend-note" style="font-size:0.75rem; color:#aaa; margin-top:4px;">
    ⚠️ Node position reflects simulation forces, not correlation magnitude.
    Correlation strength is encoded by edge thickness and style only.
  </div>
  ```
- **Additionally:** Add a tooltip on the SVG background `mouseenter` with the same clarification.

**P2.2 — Force-Directed Graph Suboptimal for 6-Node Dataset**
- **File/Line:** `templates/panopticon.html:2550–2749`
- **Why medium-high:** Grok correctly identified (validated in Cycle 2 consensus) that force-directed layouts provide meaningful value at 10+ nodes. At 6 nodes, the layout is positionally non-deterministic, adds animation noise, and provides no clustering insight that a static layout wouldn't deliver more clearly.
- **Action (phased):**
  - **Phase 1 (immediate):** Pin the layout after initial stabilization using `simulation.on("end", () => simulation.stop())` to eliminate continuous drift.
  - **Phase 2 (next sprint):** Implement a 6×6 heatmap matrix as a toggle alternative view. Encode score-difference correlation as a sequential color scale (e.g., `d3.interpolateRdYlGn`). Provide a UI toggle button: `[Network View] [Matrix View]`.
  - **Phase 3 (optional):** Evaluate chord diagram if directionality or flow semantics are ever relevant to the data model.

---

### P3 — MEDIUM (Implementation Quality)

**P3.1 — Collision Force Tuning for Small Viewports**
- **File/Line:** Force simulation config, estimated `panopticon.html:2729–2734`
- **Why medium:** GPT-4o's Cycle 2 addition (small screen collision) is valid and additive to Grok's base finding.
- **Action:**
  ```javascript
  const collideRadius = Math.max(nodeRadius + 8, viewportWidth < 480 ? nodeRadius + 20 : nodeRadius + 10);
  simulation.force("collide", d3.forceCollide(collideRadius).iterations(3));
  ```
- **Test:** Validate at 320px, 375px, 768px, and 1440px viewport widths. No node overlap at any size.

**P3.2 — D3 Implementation Review for Edge Calculation Logic**
- **Consensus severity:** LOW (both active models agreed)
- **Action:** Audit the edge-drawing logic (score proximity thresholds: HIGH <15, MEDIUM 15–30, LOW >30 no edge) against actual index score variance in production data. If scores cluster tightly, most edges will render as HIGH and the encoding loses discriminative power. Add a dynamic threshold calculation:
  ```javascript
  const scoreRange = d3.extent(nodes, d => d.score);
  const rangeSpan = scoreRange[1] - scoreRange[0];
  const HIGH_THRESHOLD = rangeSpan * 0.2;
  const MEDIUM_THRESHOLD = rangeSpan * 0.5;
  ```

---

### P4 — LOW (Polish / Technical Debt)

**P4.1 — Add Static Fallback for No-JS / SVG-Unsupported Environments**
- Render a server-side HTML table of correlation scores inside a `<noscript>` tag or as a visually-hidden accessible table mirroring the SVG data. This satisfies both progressive enhancement and screen-reader fallback.

**P4.2 — Document Audit Trail for Gemini Failure**
- Log the 403 PERMISSION_DENIED event with timestamp, affected audit ID, and remediation steps taken. Update the cross-LLM audit runner to treat 403 as a hard failure with automatic alert rather than a silent partial result, so future audits are never silently running at 2/3 model capacity.

---

## IMPLEMENTATION ORDER SUMMARY

| Priority | Item | Owner | Estimated Effort |
|---|---|---|---|
| P0.1 | Revoke leaked Gemini API key | DevOps / Security | 30 min |
| P1.1 | SVG keyboard + ARIA accessibility | Frontend | 3–4 hrs |
| P2.1 | Legend proximity disclaimer | Frontend | 30 min |
| P2.2 | Layout stabilization + matrix toggle | Frontend | 1–2 days |
| P3.1 | Collision force responsive tuning | Frontend | 1 hr |
| P3.2 | Dynamic edge threshold calculation | Frontend | 2 hrs |
| P4.1 | Static table fallback | Frontend | 2 hrs |
| P4.2 | Audit failure alerting | DevOps | 1 hr |