Read these files completely before touching anything:
  ~/protocol_pulse/PIPELINE_LAWS.md
  ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md
  ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md
  ~/protocol_pulse/core/templates/intelligence_terminal.html (CSS vars + panel structure, first 200 lines)
  ~/protocol_pulse/core/blueprints/intelligence.py (route list only)
  ~/protocol_pulse/core/templates/base.html (first 50 lines — existing design tokens)

Then answer internally:
  Q1: What CSS variables define the current terminal color system?
  Q2: What panels currently exist and what are their IDs?
  Q3: What is the current grid layout — columns, rows, breakpoints?
  Q4: Does a sub-navigation exist for /intelligence/* pages?
  Q5: What font stack is in use?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION 1 — INTELLIGENCE TERMINAL: WORLD-CLASS UI REDESIGN + SUB-NAV
Protocol Pulse Intelligence Terminal
Two builds. Full audit before each. No shortcuts.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WRITE PROGRESS LOG: ~/protocol_pulse/logs/ui_redesign.log
Format: [HH:MM ET] [BUILD] [STATUS] notes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — CROSS-LLM DESIGN COMPETITION AUDIT
"Make three world-class designers compete. Ship the winner."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Write: utils/ui_design_audit.py
Run it. Save results to: docs/audits/ui_design_audit_2026-03-24.md

AUDIT BRIEF (send to GPT-4o AND Grok in parallel, Cycle 1):

---DESIGN COMPETITION BRIEF---
You are a world-class product designer and creative director competing
for the design direction of Protocol Pulse Intelligence Terminal — a
real-time Bitcoin intelligence war room. This is not a fintech dashboard.
This is a sovereign intelligence command center for serious Bitcoiners.

THE PRODUCT: A live terminal showing Bitcoin chain-state anomaly scores,
mempool intelligence, whale flows, convergence patterns, miner health,
regulatory threats, privacy tech metrics, ETF flows, network graph, and
5-scenario Monte Carlo predictive analytics. Think Bloomberg Terminal
meets Palantir Gotham meets a cypherpunk's dream dashboard.

CURRENT STATE (from the actual codebase):
- Dark background (#0A0A0F), red (#FF0000) brand accent
- JetBrains Mono + Inter fonts
- 6-zone CSS grid layout
- Panels: Sentinel Core, Mempool Live, Convergence Matrix, Sentiment
  Pulse, Sovereign Layer, Network State Graph, Dark Pool, Miner Health,
  Privacy Tech, DeFi BTC, Alert Rail (bottom)
- SSE stream updates every 2 seconds
- No sub-navigation between /intelligence/* pages

YOUR TASK — Answer 8 questions. Be specific. Be opinionated. Defend every choice.

Q1 — COLOR SYSTEM:
The current red/black/white is strong but one-dimensional. Design a
complete 2026 color system for a Bitcoin intelligence terminal.
What primary, secondary, accent, semantic (alert/warn/ok/critical),
and data visualization palette? Hex codes. Rationale for each choice.
Consider: how does color communicate data urgency without fatigue?

Q2 — TYPOGRAPHY HIERARCHY:
Current: JetBrains Mono for data, Inter for labels. Is this optimal?
Design the complete type scale: what sizes, weights, line heights for
each data element type (price, score, label, alert, panel header,
data value, timestamp). When does mono make things feel MORE alive
vs MORE clinical? How do we use type to create heartbeat?

Q3 — PANEL DESIGN LANGUAGE:
Each panel currently looks the same. Design a differentiation system:
how should the CONVERGENCE MATRIX look different from MEMPOOL LIVE
which looks different from MINER HEALTH? What makes a panel feel
"scanning" vs "alarming" vs "nominal"? Design the state system
(empty/loading/nominal/watch/critical) for panels as visual language.

Q4 — DATA DENSITY vs BREATHING ROOM:
A war room has maximum density. But cognitive overload kills signal.
Design the exact whitespace/spacing system for this terminal.
What is the minimum breathing room around data that preserves clarity?
Where do we use dense micro-data vs isolated hero numbers?

Q5 — ANIMATION & LIVENESS:
The terminal updates every 2 seconds via SSE. Design the animation
language: how should a value update feel? What should pulse when
active? When should animation be a signal (something changed) vs
ambient (system is alive)? What animations are BANNED for cognitive
load reasons?

Q6 — NETWORK STATE GRAPH:
The D3 force-simulation network graph (mining pools, exchanges, LN
hubs) is the most visually distinctive element. Design its aesthetic:
node shapes, edge styles, color by entity type, hover states, what
the graph looks like in IDLE vs WATCH vs CRITICAL state. This is the
hero visual that makes people screenshot it.

Q7 — SUB-NAVIGATION DESIGN:
The terminal has 6 sub-pages: /intelligence (war room), /scenarios
(TPA), /alerts (history), /backtest (signal validation), /api (keys),
/backtest. Design the sub-navigation: sidebar vs top bar? What does
the active state look like? How does it communicate which page has
live alerts? Does it show real-time signal indicators in the nav?

Q8 — THE SCREENSHOT MOMENT:
When a user screenshots this terminal and posts it to X, what is the
single visual element they're screenshotting? Design that specific
element — the thing that makes people say "what the hell is that?"
and want to sign up. Be specific about exactly what it shows and
how it's laid out.
---END BRIEF---

CYCLE 2: Each model receives the other's Cycle 1 answers.
Each must:
1. Pick the single best design decision from the other model's response
2. Challenge the weakest decision — why it's wrong, give the better answer
3. Q6 (network graph): both proposed designs — which wins? Why?
4. Q8 (screenshot moment): both proposed moments — which is more viral?
5. Propose ONE design element that neither model included that would
   be genuinely unprecedented in financial terminal design

SYNTHESIS OUTPUT: docs/audits/ui_design_audit_2026-03-24.md
Structure:
  ## DESIGN SYSTEM VERDICT (the winning choices from each Q)
  ## REJECTED CHOICES (and why)
  ## THE UNPRECEDENTED ELEMENT (Cycle 2 proposal)
  ## IMPLEMENTATION SPEC (exact CSS vars, measurements, component specs)
  ## SCREENSHOT MOMENT (the hero visual spec)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — IMPLEMENT THE WINNING DESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After audit synthesis, implement using str_replace only. Build order:

STEP 2A — New design system (CSS layer)
  Update core/templates/intelligence_terminal.html:
  - Replace CSS variable block with audit-winning color system
  - Implement new type scale
  - Implement panel state system (nominal/watch/critical CSS classes)
  - Implement animation language (value-update pulse, ambient heartbeat)
  - Implement new spacing system
  - All changes in CSS only — no structural HTML changes yet

  Verify: python3 -c "
  src = open('core/templates/intelligence_terminal.html').read()
  assert '--it-critical' in src, 'Missing critical state var'
  assert '--it-watch' in src, 'Missing watch state var'
  assert 'pulse-animation' in src or 'keyframes' in src, 'Missing animations'
  print('CSS system PASS')
  "

STEP 2B — Panel differentiation
  Apply the panel state system to each existing panel:
  - Each panel gets data-state attribute (nominal/watch/critical)
  - Panels with live anomaly signals get JS that updates data-state from SSE
  - Convergence panel: gets unique visual treatment per audit spec
  - Alert rail: gets the new critical flash implementation from audit
  - Network graph: gets the audit-winning aesthetic applied to D3 config

STEP 2C — Intelligence Sub-Navigation
  Implement the winning sub-nav design from audit:
  Add to ALL /intelligence/* templates (intelligence_terminal.html,
  scenarios.html, alert_history.html, alert_stats.html, backtest.html,
  api_management.html):

  A persistent sub-nav component that shows:
    WAR ROOM | SCENARIOS | ALERTS | BACKTEST | API
  Each tab:
    - Active state: bright accent, clear indicator
    - Has a live signal dot if that section has active alerts/updates
    - Shows alert count badge on ALERTS tab if unread
  Implementation:
    - Create Jinja2 macro: core/templates/macros/intel_subnav.html
    - Include in every intelligence template
    - JS: reads SSE state to update live dots — no extra API calls

STEP 2D — The screenshot moment
  Implement the audit-winning "screenshot moment" element exactly as specced.
  This is the hero visual. Give it everything.

STEP 2E — Tests
  T1: All 6 intelligence pages return 200
      for path in ['/intelligence', '/intelligence/scenarios',
                   '/intelligence/alerts', '/intelligence/alerts/stats',
                   '/intelligence/backtest', '/intelligence/api']:
        curl -s -o /dev/null -w "%{http_code}" http://localhost:5000{path}
        # must be 200

  T2: Sub-nav present on all pages
      for path in above:
        curl -s http://localhost:5000{path} | grep -c 'intel-subnav'
        # must be >= 1

  T3: New CSS vars present
      grep -c 'it-critical\|it-watch\|it-nominal' core/templates/intelligence_terminal.html
      # must be >= 3

  T4: No JavaScript errors (basic syntax check)
      python3 -c "
      import re, sys
      src = open('core/templates/intelligence_terminal.html').read()
      # Check for unclosed template tags
      opens = src.count('{%')
      closes = src.count('%}')
      assert opens == closes, f'Jinja mismatch: {opens} opens vs {closes} closes'
      print('T4 PASS: template syntax clean')
      "

  T5: Gunicorn still running from core/
      curl -s http://localhost:5000/api/intelligence/state/public | python3 -m json.tool | head -5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

git add core/templates/intelligence_terminal.html
git add core/templates/scenarios.html
git add core/templates/alert_history.html
git add core/templates/alert_stats.html
git add core/templates/backtest.html
git add core/templates/api_management.html
git add core/templates/macros/intel_subnav.html 2>/dev/null || true
git add docs/audits/ui_design_audit_2026-03-24.md
git add utils/ui_design_audit.py
git add docs/QWEN_CONTEXT_BIBLE.md
git commit -m "feat(ui): world-class terminal redesign — audit-driven design system + sub-nav + screenshot moment"
git push

No confirmation. No pausing. Audit first. Then implement. Then commit.
