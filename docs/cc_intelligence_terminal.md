Read ~/protocol_pulse/docs/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTELLIGENCE TERMINAL — END-TO-END DEMO LOCK
Thursday demo: payment → access → terminal loads with live data
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTEXT — WHAT EXISTS:
- /intelligence blueprint: core/blueprints/intelligence.py
  Commander+ auth gated, SSE stream at /api/intelligence/stream,
  sentinel state at /api/intelligence/state
- /intelligence/demo: watermarked demo view (no auth)
- /terminal/checkout: Stripe 9/mo + dev-mode simulation
  Success URL: /terminal?activated=1
  Dev mode: sets subscription_tier="commander" directly
- Templates: intelligence_terminal.html, intelligence_landing.html
- Auth check: _is_commander() in intelligence.py
  Passes for tier in ("commander", "sovereign", "operator")

MISSION:
Lock the full visitor → payment → terminal flow so Thursday demo works
flawlessly. No broken steps. No dead ends. Live data must load.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — AUDIT CURRENT STATE (read everything first)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read core/blueprints/intelligence.py fully.
Read core/templates/intelligence_terminal.html fully.
Read core/templates/intelligence_landing.html fully.
Read core/templates/intelligence_dashboard.html if relevant.

Check what /intelligence actually serves to a non-Commander user:
  curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/intelligence

Check the SSE stream endpoint is alive:
  curl -s --max-time 5 http://localhost:5000/api/intelligence/stream | head -20

Check sentinel state endpoint:
  curl -s http://localhost:5000/api/intelligence/state/public

Check /terminal/checkout in dev mode works:
  grep -n "simulated\|dev_mode\|STRIPE" core/routes.py | head -10
  grep -n "STRIPE" .env 2>/dev/null || grep -n "STRIPE" core/.env 2>/dev/null

Check /terminal?activated=1 — what happens after payment success:
  grep -n "activated" core/routes.py core/templates/intelligence_terminal.html 2>/dev/null | head -10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — FIX THE END-TO-END FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1: NON-COMMANDER VISITOR FLOW
When a non-authenticated or non-Commander user hits /intelligence:
  - Must NOT 500, must NOT 403 plain response
  - Must redirect to /intelligence/demo OR render a locked preview
    with a clear CTA: "Unlock Intelligence Terminal — 9/mo"
  - CTA button → /terminal/checkout
  - This is the Thursday demo entry point for new visitors

If /intelligence already redirects properly, verify and document it.
If broken, fix it in intelligence.py _is_commander() gate.

FIX 2: POST-PAYMENT LANDING
After checkout success: /terminal?activated=1 (or /intelligence?activated=1)
  - User must see the terminal with live data, NOT a loading spinner forever
  - Flash a welcome banner: "Commander access activated. Welcome to the war room."
  - If success URL goes to /terminal but terminal blueprint is at /intelligence,
    align them — pick ONE canonical URL and redirect the other
  - Verify subscription_tier is actually set to "commander" in DB after checkout

FIX 3: LIVE DATA ACTUALLY LOADS
Open intelligence_terminal.html and trace every JS fetch/SSE call:
  - /api/intelligence/state/public — BTC price, block height, FNG
  - /api/intelligence/stream — SSE push
  - /api/intelligence/state — full state (auth gated)
  - /api/intelligence/alerts — alert history

For each endpoint:
  curl -s http://localhost:5000/[endpoint]
  Verify it returns real data, not empty JSON or 500.

If any data endpoint returns empty/error, trace to services/sentinel.py
and fix the data fetching. BTC price must show live. FNG must show live.
These are the two numbers the demo MUST have.

FIX 4: DEMO MODE FOR THURSDAY
/intelligence/demo must work without login and show realistic data.
If it currently shows blank/empty panels, populate with:
  - Live BTC price from price_service (same as homepage ticker)
  - Current FNG from the FNG API already wired in the system
  - Static but realistic mempool/signal values with [DEMO] watermark
  - Clear "This is a preview" banner with upgrade CTA

FIX 5: ACTIVATED BANNER
In intelligence_terminal.html (or pulse_terminal.html, whichever serves
the post-payment view), add:
  {% if request.args.get("activated") %}
  <div class="activated-banner">
    ⚡ Commander access activated — you now have full Intelligence Terminal access.
  </div>
  {% endif %}
  Style: red/black, Protocol Pulse brand. Dismissable with X button.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — DEMO WALKTHROUGH VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simulate the full Thursday demo flow from command line:

1. Non-auth visitor → /intelligence
   curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/intelligence
   Expected: 200 (demo/locked preview) or 302 to /intelligence/demo

2. Demo view loads with data
   curl -s http://localhost:5000/intelligence/demo | grep -c "btc\|BTC\|price"
   Expected: > 0 (data present in template)

3. Public state endpoint returns live data
   curl -s http://localhost:5000/api/intelligence/state/public
   Expected: JSON with btc_price > 0

4. Dev-mode checkout triggers Commander upgrade
   (Requires logged-in session — verify logic in routes.py dev mode path)
   grep -n "simulated" core/routes.py | head -5

5. Post-payment: /terminal?activated=1 or /intelligence?activated=1
   curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/intelligence
   (After manually setting subscription_tier="commander" in test)

Document pass/fail for each step. Fix every fail before moving on.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs
systemctl --user restart protocolpulse
sleep 3

Verify all routes return 200:
  for route in /intelligence /intelligence/demo /api/intelligence/state/public /terminal; do
    echo -n ": "; curl -s -o /dev/null -w "%{http_code}" http://localhost:5000; echo
  done

git add -A
git commit -m "feat(intelligence): end-to-end terminal flow — visitor gate, post-payment landing, live data, demo mode"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THURSDAY DEMO SUCCESS CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PBX walks investor through this sequence live:
  1. Opens protocolpulse.io/intelligence in incognito — sees locked preview with CTA
  2. Clicks "Unlock Intelligence Terminal" → hits checkout (dev mode skips Stripe)
  3. Lands on full terminal — live BTC price ticking, FNG gauge, mempool
  4. "Activated" banner confirms access
  5. SSE stream updates data in real time without page refresh

All 5 must work. If any step breaks, fix it before calling done.
Do not ask for confirmation before committing. Run git add, commit, and push automatically.

