Read VISUAL_DESIGN_SYSTEM.md fully first. Brand: red/black/white, JetBrains Mono,
futuristic Bloomberg-meets-cypherpunk aesthetic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JOIN PAGE REDESIGN + PROMO CODE — HIGH PRIORITY BEFORE FRIDAY DEMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILE: templates/join.html (525 lines, extends base.html)
ROUTE: Check if /join route exists in routes.py, add if missing

TASK 1 — Add promo code section to join.html
The /join page currently has NO promo code input. Add a prominent section:
- Heading: "TEAM ACCESS" or "HAVE AN ACCESS CODE?"
- Input field with monospace font, red border, placeholder "Enter access code..."
- Submit button: "UNLOCK TERMINAL"
- On submit: POST to /api/apply-promo with {"code": inputValue}
- On success: redirect to /signal-terminal or /live
- On error: show "Invalid code" in red
- Promo codes: 'SOVEREIGN-TEAM-2026' → commander, 'STAY-SOVEREIGN' → operator
- Style it like a classified access terminal — scanlines, blinking cursor

TASK 2 — World-class UI redesign of the full /join page
The page must look like Bloomberg Terminal meets cyberpunk — glass morphism,
red accent particles, JetBrains Mono typography. Requirements:
- Hero: "PROTOCOL PULSE INTELLIGENCE" with animated red scan line
- Sub: "Sovereign Bitcoin intelligence. Real-time. Unfiltered."
- 3 tiers clearly presented:
  * FREE: Articles, basic market data
  * COMMANDER ($49/mo): Full terminal, Oracle AI, daily briefings, stage avatar
  * SOVEREIGN (custom): White-glove, team access, API
- Each tier as a glass card with red/amber/gold accent colors
- Stripe checkout button for Commander tier
- Real-time market ticker at top (BTC price, fear/greed)
- "Already have access?" link → /signal-terminal
- Must be fully responsive, mobile-perfect
- NO generic looking design — this needs to feel like a $500/month Bloomberg subscription

TASK 3 — Wire the /join route if missing
Check routes.py for @app.route('/join'). If missing, add it:
@app.route('/join')
def join_page():
    return render_template('join.html',
        btc_price=_fetch_btc_price() or 0,
        stripe_key=os.environ.get('STRIPE_PUBLIC_KEY', ''))

TASK 4 — Add STRIPE_PUBLIC_KEY to template context
The join page needs the Stripe publishable key for client-side checkout.
Check .env for STRIPE_PUBLIC_KEY or STRIPE_PUBLISHABLE_KEY.
If not present, use test key for now and add note.

After all tasks:
git add templates/join.html core/routes.py
git commit -m "feat(join): world-class join page with promo code access, Commander tier"
git push
