Read these files completely before touching anything:
  ~/protocol_pulse/PIPELINE_LAWS.md
  ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md
  ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md
  ~/protocol_pulse/core/templates/join.html (if it exists from Session 2)
  ~/protocol_pulse/core/app.py (grep: index, home, '/', landing)
  ~/protocol_pulse/core/templates/base.html (first 80 lines)

Then answer internally:
  Q1: What is the current homepage route and template?
  Q2: What design tokens were established in Sessions 1 and 2?
  Q3: Does a live demo panel exist anywhere yet?
  Q4: What real-time endpoints are available unauthenticated?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION 3 — INTELLIGENCE LANDING PAGE + LIVE DEMO PANEL
"The page that converts curious Bitcoiners into subscribers"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WRITE PROGRESS LOG: ~/protocol_pulse/logs/landing_build.log

CONTEXT:
  This is protocolpulse.io/intelligence-terminal (or /terminal)
  A dedicated landing page for the Intelligence Terminal product.
  Not the main Protocol Pulse homepage — a product-specific page.
  Traffic source: Twitter/X posts sharing PCAF alerts and TPA scenarios.
  User lands, sees live data, understands the product, clicks to join.
  Goal: 60-second decision. Demo → desire → action.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — CROSS-LLM LANDING PAGE AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Write: utils/landing_audit.py
Run it. Save: docs/audits/landing_audit_2026-03-24.md

BRIEF to GPT-4o + Grok (parallel, 1 cycle):

---LANDING PAGE AUDIT BRIEF---
You are designing the landing page for Protocol Pulse Intelligence
Terminal — a $49/mo real-time Bitcoin intelligence war room powered
by GNN anomaly detection and Monte Carlo scenario analytics.

The page lives at /intelligence-terminal.
Traffic comes from: Twitter/X posts of live alerts and screenshots,
Bitcoin podcasts, word of mouth among serious Bitcoiners.

The visitor: Already knows Bitcoin. Doesn't need education. Wants
to know if this tool is serious or vaporware. Will decide in 15
seconds. Respects technical depth over marketing polish.

Answer 5 questions:

Q1 — ABOVE THE FOLD:
Design the exact above-the-fold section. What headline? What
subheadline? What visual? The live demo panel will be here —
design what it shows (specific data points, layout, how it feels
alive). What is the immediate "holy shit" moment?

Q2 — LIVE DEMO PANEL DESIGN:
The page embeds a live mini-terminal showing real data from
/api/intelligence/state/public (no auth). Design exactly what
this panel shows. What data? What layout? What makes it feel
like a real intelligence feed, not a marketing mockup?
The panel auto-updates every 5 seconds via polling.

Q3 — SOCIAL PROOF FOR BITCOINERS:
What social proof works for this audience? NOT testimonials.
Design the specific proof elements: what technical specifications,
live metrics (articles published, alerts fired, uptime), or
credibility signals make a sovereign Bitcoiner say "this is real"?

Q4 — FEATURES SECTION:
Design the features section. What 4-6 features are highlighted?
What is the visual treatment — icons, mini-screenshots, or pure
typographic? How do you communicate GNN anomaly detection and
Monte Carlo to someone who is smart but not an ML engineer?
Translate without dumbing down.

Q5 — THE BOTTOM OF THE PAGE:
What is at the bottom? FAQ? Another CTA? A live alert ticker?
What is the last thing someone sees before they either click
"Join" or leave? Design that moment.
---END BRIEF---

Synthesize into: docs/audits/landing_audit_2026-03-24.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — BUILD THE LANDING PAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 2A — Create landing page template
  Create: core/templates/intelligence_landing.html
  Route: GET /intelligence-terminal (no auth required, fully public)
  
  Page structure (implement audit-winning layout):
  
  SECTION 1 — HERO (above fold):
    - Audit-winning headline + subheadline
    - LIVE DEMO PANEL (see below)
    - Primary CTA: "Access the Terminal — $49/mo" → /join
    - Secondary: "See what you're missing" → smooth scroll to features

  SECTION 2 — LIVE DEMO PANEL:
    Mini war room panel (450px wide, centered or full-width).
    Polls /api/intelligence/state/public every 5 seconds.
    Shows (no auth needed):
      - BTC price + 24h change (live)
      - Block height (live)
      - Fear & Greed value + label (live)
      - PCAF anomaly score: shown as [CLASSIFIED] with red lock icon
      - Convergence state: shown as [ENCRYPTED] with blur
      - Mempool: shows tx count (real) but fee data blurred
      - One fake "ACTIVE ALERT" example (hardcoded): 
        "WATCH: Hashrate concentration — Foundry 42% of last 10 blocks"
        (shows what alerts look like without revealing live alerts)
    Bottom of panel: "Full terminal shows 16 live intelligence streams"
    CTA: "Unlock Full Terminal" → /join

  SECTION 3 — TECHNICAL CREDIBILITY:
    Audit-winning proof elements.
    Actual live stats from the system (pull from API if possible,
    hardcode reasonable values if not):
      - Articles published, Alerts fired, Uptime %, GPU inference speed
    Technical spec callout: "Ultron: AMD EPYC 9R14 · 4× RTX 4090 · 128GB"
    (This credibility signal lands hard with technical Bitcoiners)

  SECTION 4 — FEATURES (4-6 items):
    Implement audit-winning feature section.
    Features to highlight (select best 6 from audit):
      - PCAF GNN anomaly detection
      - 5-scenario Monte Carlo (TPA)
      - Whale coordination detection
      - Regulatory intelligence (50 jurisdictions)
      - Dark pool OTC taint analysis
      - Real-time mempool intelligence
    Use audit-winning visual treatment.

  SECTION 5 — BOTTOM CTA:
    Audit-winning bottom section.
    Final CTA: prominent, no friction.

STEP 2B — Add route to intelligence blueprint
  @intelligence_bp.route("/intelligence-terminal")
  def intelligence_landing():
      return render_template("intelligence_landing.html")

STEP 2C — Add to navigation
  Add "Intelligence Terminal" to the Protocol Pulse main nav
  (in base.html or the navigation template) as a highlighted item.
  Link: /intelligence-terminal
  Style: amber/gold accent — visually distinct from other nav items.

STEP 2D — Meta tags for Twitter sharing
  intelligence_landing.html must have:
    <meta property="og:title" content="Protocol Pulse Intelligence Terminal">
    <meta property="og:description" content="Real-time Bitcoin chain-state intelligence. GNN anomaly detection. 5-scenario Monte Carlo analytics.">
    <meta property="og:image" content="/static/images/terminal-og.png">
    <meta name="twitter:card" content="summary_large_image">
  Generate a simple terminal-og.png if it doesn't exist:
    A dark background, red "PROTOCOL PULSE" text, "INTELLIGENCE TERMINAL"
    subtitle, BTC price placeholder. Use Python + PIL to generate it.

STEP 2E — Tests
  T1: GET /intelligence-terminal returns 200
  T2: Page contains live demo panel
      curl -s http://localhost:5000/intelligence-terminal | grep -c 'demo-panel\|live-terminal'
  T3: Page contains CTA link to /join
      curl -s http://localhost:5000/intelligence-terminal | grep -c '/join'
  T4: OG meta tags present
      curl -s http://localhost:5000/intelligence-terminal | grep -c 'og:title'
  T5: No template errors
      curl -s http://localhost:5000/intelligence-terminal | grep -v '500\|error\|Error' | head -5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

git add core/templates/intelligence_landing.html
git add core/blueprints/intelligence.py
git add core/templates/base.html
git add docs/audits/landing_audit_2026-03-24.md utils/landing_audit.py
git add docs/QWEN_CONTEXT_BIBLE.md
git add static/images/terminal-og.png 2>/dev/null || true
git commit -m "feat(landing): Intelligence Terminal product page — live demo panel + conversion flow + OG meta"
git push

No confirmation. No pausing. Audit first. Build. Commit.
