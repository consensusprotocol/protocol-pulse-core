Read these files completely before touching anything:
  ~/protocol_pulse/PIPELINE_LAWS.md
  ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md
  ~/protocol_pulse/core/app.py (grep: stripe, commander, subscription, register, login, tier)
  ~/protocol_pulse/core/blueprints/routes_commander.py (full file if exists)
  ~/protocol_pulse/core/templates/base.html (first 80 lines — design tokens)

Then answer internally:
  Q1: What does the current Stripe webhook handle? What tiers exist?
  Q2: What happens after a user pays — where do they land?
  Q3: What is the current sign-up flow — what route handles it?
  Q4: Does a dedicated /pricing or /join page exist?
  Q5: Is there any post-payment email sequence configured?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION 2 — WORLD-CLASS PREMIUM ONBOARDING + STRIPE INTEGRATION
"From first visit to paying subscriber in under 60 seconds"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WRITE PROGRESS LOG: ~/protocol_pulse/logs/onboarding_build.log

CONTEXT:
  Product: Protocol Pulse Intelligence Terminal
  Price: $49/mo Commander tier (Stripe live, webhook at /api/v1/stripe/webhook)
  Brand: Bitcoin intelligence war room. Sovereign. Serious. Cypherpunk.
  User: Serious Bitcoiner, self-sovereign, allergic to bullshit.
  Goal: Sign up → pay → inside the terminal in under 60 seconds.
  2026 standard: inline modals, no redirects, instant access, Bitcoin-native copy.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — CROSS-LLM ONBOARDING AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Write: utils/onboarding_audit.py
Run it. Save: docs/audits/onboarding_audit_2026-03-24.md

BRIEF to GPT-4o + Grok (parallel, 1 cycle):

---ONBOARDING AUDIT BRIEF---
You are a conversion rate optimization expert and product designer
auditing the onboarding flow for Protocol Pulse Intelligence Terminal.

THE PRODUCT: $49/mo Bitcoin intelligence war room. Real-time GNN
anomaly detection, 5-scenario Monte Carlo predictive analytics,
whale coordination tracking, regulatory intelligence, miner stress
model. Think Bloomberg Terminal for cypherpunks.

THE AUDIENCE: Bitcoin maximalists, sovereign wealth managers,
serious traders, HODLers who run nodes. They hate popups. They
hate dark patterns. They respect directness and technical depth.
They will pay $49/mo if the product is real.

2026 BEST PRACTICES CONTEXT:
- Top SaaS conversion: inline modals (no redirect to /signup)
- Fastest checkout: Stripe Payment Links or Stripe.js inline
- Post-payment: instant unlock + welcome sequence
- Email sequence: 3-touch maximum for technical products
- Demo-first: let them see the product before asking for payment
- Bitcoin products: no KYC friction, minimal form fields

Answer 6 questions:

Q1 — PRICING PAGE DESIGN:
Design the /join page for this product. What elements are on it?
What social proof works for this audience (not testimonials —
something more credible to Bitcoiners)? What CTA copy converts?
What does the page look like at 9pm when a Bitcoiner lands from
a tweet about a PCAF alert? Be specific about layout and copy.

Q2 — FRICTION AUDIT:
List every piece of friction in the ideal sign-up flow.
For each: is it necessary or eliminatable? What is the minimum
viable set of fields/steps to get someone from landing to
accessing the terminal? (Hint: email + password + Stripe = 3 fields)

Q3 — POST-PAYMENT EXPERIENCE:
The moment Stripe webhook fires confirming payment — what happens?
Design the exact sequence: redirect, welcome overlay, onboarding
tooltip tour, first email. What does the user see in the first
30 seconds after paying? What makes them feel they made the
right decision immediately?

Q4 — EMAIL SEQUENCE:
Design a 3-email post-payment sequence for a Bitcoiner.
Email 1 (instant): What does it say? Subject line, body, one CTA.
Email 2 (day 3): What's the hook? What feature do you highlight?
Email 3 (day 7): What's the retention play? What proves value?
Write the actual subject lines and first sentence of each.

Q5 — DEMO PANEL (unauthenticated preview):
The /intelligence page currently requires Commander auth.
Design an unauthenticated demo state: what data is real vs blurred?
What signals can a non-subscriber see that make them want in?
What is the exact "upgrade" prompt that appears inline — not a popup,
not a redirect, just a natural moment where they hit the wall?

Q6 — BITCOIN-NATIVE COPY:
Write the hero headline, sub-headline, and 3 feature bullets for
the /join pricing page. This copy must resonate with a sovereign
Bitcoiner. No buzzwords. No "unlock insights." No "powerful dashboard."
Write like a cypherpunk wrote it, not a marketing team.
---END BRIEF---

Synthesize into: docs/audits/onboarding_audit_2026-03-24.md
Key outputs:
  - /join page spec (layout, copy, CTA)
  - Minimum friction flow (exact fields + steps)
  - Post-payment 30-second experience spec
  - 3 email sequence (subject lines + first sentences)
  - Demo panel design (what's real vs blurred)
  - Bitcoin-native copy (headline + bullets)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — IMPLEMENT THE WINNING ONBOARDING FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 2A — /join pricing page
  Create: core/templates/join.html
  War room aesthetic (inherits VISUAL_DESIGN_SYSTEM.md).
  Implement audit-winning layout:
    - Hero section: audit-winning headline + sub-headline
    - Live signal preview (3 real data points from /api/intelligence/state/public,
      no auth required — just price, FNG, block height)
    - Pricing card: Commander $49/mo, clean, no dark patterns
    - 3 feature bullets from audit-winning copy
    - CTA: "Access the Terminal" → triggers inline signup modal (no redirect)
    - Social proof: "Built on Ultron — 4x RTX 4090 — Real-time GNN inference"
      (technical credibility, not testimonials)

  Add route to intelligence.py:
  @intelligence_bp.route("/join")
  def join_page():
      return render_template("join.html")

  Also add /join to main app navigation if not present.

STEP 2B — Inline signup modal
  Add to join.html (and base.html for site-wide access):
  A modal triggered by "Access the Terminal" CTA.
  Fields: email, password, confirm password — nothing else.
  On submit: POST to existing /register route.
  On success: redirect directly to Stripe checkout (generate Stripe
  Payment Link URL or use existing Stripe integration).
  No email verification step before payment — verify after.
  Implement as vanilla JS modal, no external dependencies.

STEP 2C — Post-payment welcome experience
  Read routes_commander.py (or wherever Stripe webhook is handled).
  After successful payment webhook fires and user tier is upgraded:
    1. Set a session flag: session['just_upgraded'] = True
    2. Redirect to /intelligence with welcome overlay active
  
  Add to intelligence_terminal.html:
  Welcome overlay (shown once, dismissed with click):
    - Shown only if session['just_upgraded'] is True
    - Clears the flag immediately on display
    - Content: "TERMINAL ACCESS GRANTED" headline
      + 3 quick-start bullets: "Your first alert", "Check PCAF score",
        "Explore Scenarios"
    - Keyboard shortcut hint: "Press ? for all shortcuts"
    - Dismiss: click anywhere or press Escape
    - Design: full-screen dark overlay, red accent, war room aesthetic

STEP 2D — Demo mode for unauthenticated users
  Modify _has_access() behavior for the main /intelligence page only:
  Instead of redirecting to login, show intelligence_terminal.html
  in DEMO MODE:
    - Real data for: price, FNG, block height, mempool count
    - Blurred/placeholder for: PCAF score, convergence state,
      sentiment score, dark pool signal, miner health
    - Alert rail shows "[ CLASSIFIED — Commander Access Required ]"
    - Each blurred panel has an inline "Unlock" link → triggers signup modal
    - No redirect. They see the terminal. They see what they're missing.

  Implementation:
    Pass demo_mode=True to template when not authenticated.
    Template JS: if demoCmode, replace sensitive values with blur CSS class
    and "CLASSIFIED" text.

STEP 2E — Post-payment email sequence
  Check if SMTP is configured (privateemail.com from Argos build).
  Implement email sequence trigger in Stripe webhook handler:
  After payment confirmed: schedule 3 emails using simple threading.Timer
  or write to a pending_emails table for a background worker.
  
  EMAIL 1 (immediate, on webhook):
    Subject: "Terminal access granted — here's what you're seeing"
    Body: audit-winning content, link to /intelligence
    
  EMAIL 2 (72h later, use threading.Timer or APScheduler if available):
    Subject: "Your first PCAF alert just fired" (or "PCAF is watching")
    Body: explain what PCAF v0 does, what to watch for
    
  EMAIL 3 (7 days later):
    Subject: "The scenario that's forming right now"
    Body: link to /intelligence/scenarios with current top scenario

  If APScheduler not available: write email schedule to
  data/pending_emails.json (processed by background worker on next boot).

STEP 2F — Tests
  T1: GET /join returns 200
  T2: join.html contains signup modal trigger
      grep -c 'join-modal\|signup-modal\|Access the Terminal' core/templates/join.html
  T3: Demo mode renders without crash
      curl -s http://localhost:5000/intelligence | grep -c 'demo\|classified\|CLASSIFIED'
      (unauthenticated curl should hit demo mode)
  T4: Welcome overlay exists in terminal template
      grep -c 'just_upgraded\|TERMINAL ACCESS GRANTED' core/templates/intelligence_terminal.html
  T5: Email 1 function exists in webhook handler
      grep -c 'send.*welcome\|welcome.*email\|email.*granted' core/blueprints/routes_commander.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

git add core/templates/join.html core/templates/intelligence_terminal.html
git add core/blueprints/intelligence.py core/blueprints/routes_commander.py
git add core/templates/base.html
git add docs/audits/onboarding_audit_2026-03-24.md utils/onboarding_audit.py
git add docs/QWEN_CONTEXT_BIBLE.md
git commit -m "feat(onboarding): world-class join page + demo mode + welcome overlay + post-payment email sequence"
git push

No confirmation. No pausing. Audit first. Implement. Commit.
