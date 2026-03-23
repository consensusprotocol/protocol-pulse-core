Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROTOCOL PULSE COMMANDER — $29/MONTH PREMIUM EXPERIENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRODUCT VISION:
Protocol Pulse Commander is not a newsletter. It is not a dashboard.
It is the intelligence layer that serious Bitcoin people actually need —
the thing they open every morning before the market moves, the thing
they cite in conversations, the thing they tell other Bitcoiners about.

At $29/month it must feel like it's worth $299. Every feature must earn
its place. Nothing decorative. Everything operational.

TARGET USER:
- Holds Bitcoin. Not trading it — accumulating it.
- Follows macro closely. Understands monetary policy, geopolitics.
- Reads Marty Bent, listens to Preston Pysh, watches Simply Bitcoin.
- Frustrated that most Bitcoin media is either too surface-level or
  too technical. Wants the signal, not the noise.
- Has disposable income. Pays for quality tools without hesitation.
- Will tell other Bitcoiners about this if it genuinely helps them.

THE CORE PROMISE:
"Every morning you open Protocol Pulse Commander, you know exactly
what happened in Bitcoin overnight, what it means for your stack,
and what to watch for today. In under 3 minutes."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY CROSS-LLM AUDIT FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["commander-premium"] = ("VISUAL_DESIGN_SYSTEM.md", "main")
  EXPLICIT_FILES["commander-premium"] = [
      "templates/commander_dashboard.html",
      "routes.py",  # Commander routes only
      "services/morning_brief.py",
  ]

python3 utils/cross_llm_audit.py --feature commander-premium
[save C1 output]
python3 utils/cross_llm_audit.py --feature commander-premium --cycle 2 --cycle1-results [C1]

Read audit consensus fully before building anything.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — AUDIT EXISTING COMMANDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read templates/commander_dashboard.html fully.
Read routes_commander.py or equivalent Commander routes.
Check what's already built vs what's missing.
Check Stripe Commander subscription logic — is $29/mo plan wired?
  grep -n "29\|commander\|COMMANDER\|stripe" routes.py | head -20
Check how Commander auth/gating works currently.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — THE COMMANDER EXPERIENCE (build these features)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FEATURE 1: THE MORNING BRIEF — "Your 3-Minute Bitcoin Briefing"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is the anchor feature. The reason people subscribe.

Design: Full-screen immersive brief. Dark background, Protocol Pulse
red accents. Feels like a classified intelligence document.

Content (pulled from morning_intelligence_brief.json):
  TOP CARD — "THE NUMBER":
    BTC price + 24h change. Large. Impossible to miss.
    Color-coded: green if up, red if down. Clean. No clutter.

  SIGNAL BLOCK — "WHAT HAPPENED":
    3-4 bullet points. Each one is a signal, not a headline.
    NOT: "Bitcoin price rose 2% amid market uncertainty"
    YES: "Spot ETF inflows reversed — $180M outflow on Thursday.
          Last time this happened: March 2024, 3 weeks before ATH."
    Each bullet links to the source article on protocolpulse.io.

  THE TAKE — "WHAT IT MEANS":
    1 paragraph. PBX voice. Cypherpunk lens. No hedging.
    This is the editorial. What does this mean for someone who
    holds Bitcoin and thinks in decades, not days.

  WATCH LIST — "3 THINGS TO MONITOR TODAY":
    3 specific data points to watch. Not vague.
    NOT: "Watch Bitcoin price"
    YES: "ETF flow data releases at 4pm ET — first positive week
          in 3 would flip the trend signal"

  FEAR & GREED METER:
    Visual gauge. Current reading + 7-day trend.
    Protocol Pulse design — red/black, not green/red generic.

FEATURE 2: PULSE SCORE — "Your Bitcoin Intelligence Rating"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A composite score (0-100) showing the overall Bitcoin signal strength.
Updated every 4 hours. Pulls from:
  - On-chain metrics (hashrate, mempool, difficulty)
  - Macro signals (DXY, gold, 10Y yield)
  - Sentiment (Fear & Greed, social volume)
  - Institutional flow (ETF data)
  - Market structure (price vs key MAs)

Display: Large circular gauge. Red/black Protocol Pulse design.
Score + label: EXTREME FEAR / FEAR / NEUTRAL / GREED / EXTREME GREED
Sub-scores for each category so users understand the breakdown.
7-day sparkline showing score trend.
"Last 5 times score was this low: [dates + what happened after]"
— This historical context is what makes it valuable.

FEATURE 3: INTEL FEED — "Unfiltered Signal Stream"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Real-time feed of high-signal Bitcoin events. No noise.
Each item scored 1-10 for signal strength. Only 7+ shown.
Sources: on-chain anomalies, large wallet movements, ETF flows,
         Fed statements, geopolitical events affecting BTC.

Format per item:
  [SIGNAL STRENGTH: 8/10] [CATEGORY: ON-CHAIN]
  "3,200 BTC moved off Coinbase to cold storage — largest single
   transfer in 6 weeks. Accumulation signal."
  → Source link | 2 hours ago

Auto-refreshes every 5 minutes. New items slide in from top.
Unread count badge on the Commander nav icon.

FEATURE 4: SOVEREIGN STACK TRACKER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is personal. This is what creates retention.

User inputs their BTC holdings (stored locally in browser, never
sent to server — this is important for the cypherpunk audience).
Commander shows:
  - Current fiat value of stack
  - Stack value in gold oz, barrels of oil, S&P units
  - "Since you started watching" — stack value when they first
    entered their amount vs today
  - "If Bitcoin reaches $X" calculator — user slides to target
    price, sees their stack value
  - DCA tracker — enter weekly/monthly buy amount, see
    projected accumulation over 1/5/10 years

Design note: Frame everything in sovereign terms.
"Your stack" not "your portfolio". "Accumulation" not "investment".
"Sound money" not "crypto asset".

FEATURE 5: LIVE SPACES INTERCEPT ALERTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When a TIER1 Bitcoin thought leader goes live on X Spaces,
Commander subscribers get:
  - Push notification (browser)
  - In-app banner: "LIVE NOW: Marty Bent + Preston Pysh — Bitcoin
    ETF Outflows. 847 listeners. Protocol Pulse intercepting."
  - Real-time transcript stream inside Commander
  - Key quote extraction every 5 minutes: the most signal-dense
    sentence from the last 5 minutes, surfaced automatically
  - Post-space recap available within 30 minutes of space ending

This is genuinely unique. Nobody else does this.

FEATURE 6: COMMANDER BRIEFING ARCHIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Full archive of every morning brief since launch.
Searchable by date, topic, BTC price range.
"What was the signal on [date]?" — useful for pattern recognition.
Each brief linked to what the price did in the following 7 days.
This turns the archive into a learning tool, not just a record.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — DESIGN REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read VISUAL_DESIGN_SYSTEM.md fully before writing a single line of CSS.

Commander must feel DIFFERENT from the free site. It should feel like
you've entered a secure operations center. The free site is the lobby.
Commander is the war room.

Color palette: deeper blacks (#030408), red stays (#CC2222),
  add subtle gold (#B8860B) for Commander-exclusive elements.
  Gold = premium signal. Use sparingly.

Typography: JetBrains Mono for data. System sans-serif for prose.
  Commander subscribers see their name in the top right. Personalized.

Layout: Single-column on mobile (this gets checked on phones first).
  Dashboard grid on desktop. No sidebar clutter.

Micro-interactions: Data that updates should animate subtly.
  New intel items slide in. Score changes pulse briefly.
  Nothing jarring. Everything purposeful.

Loading states: Never show empty boxes. Skeleton loaders that match
  the final content shape. Commander never looks broken.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — STRIPE INTEGRATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verify Stripe Commander ($49/mo plan) exists or create $29/mo plan.
Check routes_commander.py for existing webhook handling.
Subscription gate: non-subscribers see a preview of Feature 1
  (first 2 bullets blurred) with a clean conversion prompt.
  NOT a popup. An integrated teaser that makes the value obvious.

Conversion copy on gate:
  "You're seeing 2 of 7 signals from this morning's brief.
   Commander subscribers see the full picture — plus the Take,
   the Watch List, live Spaces alerts, and the Pulse Score.
   $29/month. Cancel anytime. No crypto required."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — ROUTES AND DATA WIRING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/commander — main dashboard (auth gated)
/commander/brief — today's morning brief
/commander/brief/<date> — archive access
/commander/score — Pulse Score detail view
/commander/feed — Intel Feed full view
/api/commander/brief — JSON endpoint for morning brief data
/api/commander/score — JSON endpoint for Pulse Score
/api/commander/feed — JSON endpoint for Intel Feed (paginated)
/api/commander/spaces/live — live spaces status

All /api/commander/* endpoints require valid Commander subscription.
Return proper 403 with JSON error for unauthorized requests.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs
git add templates/commander_dashboard.html routes_commander.py routes.py
git commit -m "feat(commander): Protocol Pulse Commander $29/mo — morning brief, pulse score, intel feed, sovereign stack tracker, live spaces alerts"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY BAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before calling this done, ask:
  - Would a serious Bitcoin holder pay $29/month for this TODAY?
  - Does every feature feel earned, not decorative?
  - Does it load fast on mobile?
  - Is the morning brief genuinely better than what they get
    from Marty Bent's newsletter or Simply Bitcoin?
  - Would someone screenshot this and post it on X?

If any answer is no — keep building.
