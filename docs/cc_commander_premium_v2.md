Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/audits/commander_product_audit_2026-03-22.md for full audit context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROTOCOL PULSE COMMANDER v2 — $29/MONTH PREMIUM EXPERIENCE
Post-Audit Build Spec — 3-Model Consensus (Gemini + GPT-4o + Grok)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRODUCT VISION:
Protocol Pulse Commander is the Sovereign Bitcoiner's Co-Pilot.
It is the intelligence layer that serious Bitcoin accumulators need —
the thing they open every morning before the market moves, the thing
that tells them when conditions align with their strategy, the thing
they guard like a secret weapon and share only with trusted peers.

At $29/month it must feel like it's worth $299. Every feature must earn
its place. Nothing decorative. Everything operational.

ONE-LINE PITCH:
"Protocol Pulse Commander: Your sovereign Bitcoin war room for
strategic intelligence and accumulation mastery."

TARGET USER:
- Holds Bitcoin. Not trading it — accumulating it.
- Follows macro closely. Understands monetary policy, geopolitics.
- Reads Marty Bent, listens to Preston Pysh, watches Simply Bitcoin.
- Frustrated that most Bitcoin media is either too surface-level or
  too technical. Wants the signal, not the noise.
- Has disposable income. Pays for quality tools without hesitation.
- Thinks in decades, not days. Stack is multi-generational wealth.
- Values sovereignty, privacy, and self-custody above all.

THE CORE PROMISE:
"Every morning you open Commander, you know exactly what happened
overnight, what it means for your stack, whether conditions favor
accumulation, and what to watch for today. In under 3 minutes."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIT PROVENANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This spec was produced by a 2-cycle cross-LLM product audit on 2026-03-22.
3 models (Gemini 2.5 Pro, GPT-4o, Grok-3) independently challenged the v1 spec,
then cross-examined each other's recommendations.

Key audit decisions:
- CUT: Fear & Greed Meter (unanimous — generic, free everywhere, cheapens Pulse Score)
- CUT: Bitcoin Time Machine, Milestone Alerts (commodity features, not premium-worthy)
- CUT: Daily gamified challenges (patronizing for this audience)
- ADDED: Accumulation Zone Advisor (unanimous must-build — closes intelligence→action loop)
- ADDED: Sovereign Snapshot (designed-for-viral shareable image)
- ADDED: Pulse Score Prediction Accuracy Tracker (proof-of-intelligence, brag-worthy)
- UPGRADED: On-chain metrics replace F&G (MVRV Z-Score, Puell Multiple, Realized Price)
- DEFERRED TO V1.5: Lightning payments, Commander's Canary inheritance tool
- DEFERRED TO V2: Bitcoin War Room Simulation, Cypherpunk Signal Feed

Full audit: docs/audits/commander_product_audit_2026-03-22.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE 1: THE MORNING BRIEF — "Your 3-Minute Bitcoin Briefing"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is the anchor feature. The reason people subscribe.
The daily pull mechanic — the thing they check first, every morning.

Design: Full-screen immersive brief. Dark background (#030408),
Protocol Pulse red accents (#CC2222). Feels like a classified
intelligence document.

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
    This section alone must justify the subscription.

  WATCH LIST — "3 THINGS TO MONITOR TODAY":
    3 specific data points to watch. Not vague.
    NOT: "Watch Bitcoin price"
    YES: "ETF flow data releases at 4pm ET — first positive week
          in 3 would flip the trend signal"

  ON-CHAIN SNAPSHOT (replaces Fear & Greed Meter per audit consensus):
    3 key on-chain metrics, updated daily:
    - MVRV Z-Score (historically over/undervalued indicator)
    - Puell Multiple (mining profitability, market cycle position)
    - Realized Price vs Spot (network cost basis)
    Each metric shown with current value, trend arrow, and one-line
    interpretation. Protocol Pulse red/black design, not generic charts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE 2: ACCUMULATION ZONE ADVISOR — "Your Operational Co-Pilot"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEW FEATURE — Unanimous consensus from all 3 audit models.
This is the feature that makes Commander indispensable.

It closes the loop between intelligence and action — translating
all data into the user's core objective: when to accumulate.

Setup (one-time, private, browser-stored):
  User defines what "opportunity" looks like for them:
  - Pulse Score threshold (e.g., "below 30")
  - Price drawdown from recent high (e.g., "15%+ from 30-day high")
  - On-chain conditions (e.g., "MVRV Z-Score enters green zone")
  - ETF flow conditions (e.g., "3+ days consecutive outflows")

Dashboard element:
  Large, prominent status indicator on Commander dashboard:
  ┌─────────────────────────────────────┐
  │  ACCUMULATION ZONE: MONITORING      │  (grey, steady)
  └─────────────────────────────────────┘
  or
  ┌─────────────────────────────────────┐
  │  ACCUMULATION ZONE: ACTIVE          │  (gold pulse, attention)
  └─────────────────────────────────────┘

When zone activates:
  - Browser push notification (if permitted)
  - In-brief banner on next Morning Brief
  - Historical context: "Last 5 times these conditions aligned:
    [date: BTC was $X, 30d later: +Y%]"

Important framing:
  - NOT financial advice. NOT a "buy signal."
  - "Your pre-defined conditions have been met."
  - User is the strategist. Commander is the instrument.
  - All criteria stored locally — never sent to server.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE 3: PULSE SCORE — "Your Bitcoin Intelligence Rating"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A composite score (0-100) showing overall Bitcoin signal strength.
Updated every 4 hours. Pulls from:
  - On-chain metrics (hashrate, mempool, difficulty, MVRV)
  - Macro signals (DXY, gold, 10Y yield)
  - Sentiment (social volume, narrative analysis)
  - Institutional flow (ETF data)
  - Market structure (price vs key MAs, RSI, MACD)

Display: Large circular gauge. Red/black Protocol Pulse design.
Score + label: EXTREME FEAR / FEAR / NEUTRAL / GREED / EXTREME GREED
Sub-scores for each category visible on expansion.
7-day sparkline showing score trend.

PREDICTION ACCURACY TRACKER (new — Grok audit recommendation):
  Track every time Pulse Score hits notable levels.
  Log BTC price movement over next 7/30/90 days.
  Display: "Pulse Score predicted X% of major reversals since launch."
  Example: "Last Extreme Fear (Sept 2025): BTC +27% in 30 days."
  "Share Prediction" button with preformatted X post text.
  This is the proof-of-intelligence viral moment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE 4: LIVE SPACES INTERCEPT ALERTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unanimously identified as the most differentiated feature.
This alone justifies $29/month for the right user.

When a TIER1 Bitcoin thought leader goes live on X Spaces,
Commander subscribers get:
  - Push notification (browser)
  - In-app banner: "LIVE NOW: Marty Bent + Preston Pysh — Bitcoin
    ETF Outflows. 847 listeners. Protocol Pulse intercepting."
  - Real-time transcript stream inside Commander
  - Key quote extraction every 5 minutes: the most signal-dense
    sentence from the last 5 minutes, surfaced automatically
  - Post-space recap available within 30 minutes of space ending

This leverages the existing x_spaces_scraper infrastructure:
  - Whisper large-v3 on CUDA (94x realtime after warmup)
  - Gemini 2.0 Flash sentiment analysis every 30s
  - Existing TIER1 channel list in scraper config

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE 5: SOVEREIGN STACK TRACKER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Personal. Private. The retention anchor.

User inputs their BTC holdings (stored ONLY in localStorage,
never sent to server — critical for cypherpunk audience).

Commander shows:
  - Current fiat value of stack
  - Stack value in gold oz, barrels of oil, S&P units
  - "Since you started watching" — stack value when they first
    entered their amount vs today
  - "If Bitcoin reaches $X" calculator — slider to target price
  - DCA tracker — enter weekly/monthly buy amount, see
    projected accumulation over 1/5/10 years

SOVEREIGN SNAPSHOT (new — Gemini audit recommendation):
  "Share Sovereign Snapshot" button generates a shareable image:
  ┌─────────────────────────────────────────────┐
  │  MY STACK: 1.25 BTC                         │
  │  CURRENT SIGNAL: 25 (EXTREME FEAR)          │
  │                                             │
  │  "The last time the signal was this low      │
  │   (March 2020), accumulating here preceded   │
  │   a 1,200% rise over 18 months.              │
  │   Conviction is forged in fire."             │
  │                                             │
  │  ▪ PROTOCOL PULSE COMMANDER                  │
  └─────────────────────────────────────────────┘
  Dynamic quote based on current Pulse Score.
  Designed for X — personal, conviction-aligned, product-endorsing.

Language throughout:
  "Your stack" not "your portfolio"
  "Accumulation" not "investment"
  "Sound money" not "crypto asset"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE 6: INTEL FEED — "Unfiltered Signal Stream"
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE 7: COMMANDER BRIEFING ARCHIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Full archive of every morning brief since launch.
Searchable by date, topic, BTC price range.
"What was the signal on [date]?" — useful for pattern recognition.
Each brief linked to what the price did in the following 7 days.
This turns the archive into a learning tool, not just a record.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commander must feel DIFFERENT from the free site. It should feel like
you've entered a secure operations center. The free site is the lobby.
Commander is the war room.

Color palette:
  - Background: #030408 (deeper than free site's #000)
  - Primary accent: #CC2222 (Protocol Pulse red)
  - Commander gold: #B8860B (premium-exclusive elements, used sparingly)
  - Gold = premium signal. Accumulation Zone status, Sovereign Snapshot border.

Typography: JetBrains Mono for data. System sans-serif for prose.
Commander subscribers see their name in the top right. Personalized.

Identity signals:
  - Node Status indicator: green dot + latest block height ("Don't trust, verify")
  - "No KYC, No Tracking" badge — prominent, not hidden
  - All personal data in localStorage — privacy-first architecture

Layout:
  Single-column on mobile (this gets checked on phones first).
  Dashboard grid on desktop. No sidebar clutter.

Micro-interactions:
  Data that updates should animate subtly.
  New intel items slide in. Score changes pulse briefly.
  Accumulation Zone activation gets a gold pulse border.
  Nothing jarring. Everything purposeful.

Loading states: Never show empty boxes. Skeleton loaders that match
the final content shape. Commander never looks broken.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRIPE INTEGRATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$29/month Commander plan via Stripe.
Subscription gate: non-subscribers see a preview of Feature 1
  (first 2 bullets + The Number, rest blurred) with conversion prompt.
  NOT a popup. An integrated teaser that makes the value obvious.

Conversion copy on gate:
  "You're seeing 2 of 7 signals from this morning's brief.
   Commander subscribers see the full picture — plus the Take,
   the Accumulation Zone Advisor, live Spaces intercepts, and
   the Pulse Score with prediction accuracy tracking.
   $29/month. Cancel anytime. No KYC required."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUTES AND DATA WIRING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/commander — main dashboard (auth gated)
/commander/brief — today's morning brief
/commander/brief/<date> — archive access
/commander/score — Pulse Score detail view
/commander/feed — Intel Feed full view
/commander/zones — Accumulation Zone setup & status
/api/commander/brief — JSON endpoint for morning brief data
/api/commander/score — JSON endpoint for Pulse Score
/api/commander/score/accuracy — Prediction accuracy history
/api/commander/feed — JSON endpoint for Intel Feed (paginated)
/api/commander/spaces/live — live spaces status
/api/commander/zones/status — current zone status (no PII — criteria are client-side)
/api/commander/snapshot — generate Sovereign Snapshot image

All /api/commander/* endpoints require valid Commander subscription.
Return proper 403 with JSON error for unauthorized requests.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V1.5 ROADMAP (build within 30 days of V1 launch)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LIGHTNING NETWORK PAYMENTS:
  Accept BTC via Lightning as primary payment method.
  Stripe as "legacy finance" fallback.
  Anonymous sign-up: username + password only, email optional.
  This is the single most powerful authenticity signal.

COMMANDER'S CANARY (Dead-Man's-Switch Inheritance):
  User defines check-in period (e.g., 90 days).
  Writes encrypted instructions for key recovery (NOT the keys).
  Designates a recipient contact.
  Timer expires → auto-send encrypted message.
  "Confirm Liveness" button resets timer on login.
  Near-absolute retention — users can never cancel.

PROPRIETARY ON-CHAIN INTELLIGENCE LAYER:
  Deep mempool composition analysis via dedicated node infrastructure.
  Whale wallet clustering + behavior patterns (not publicly available).
  Leading indicators before block confirmation.
  Feeds into Intel Feed and Pulse Score for exclusive data edge.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V2 ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BITCOIN WAR ROOM SIMULATION:
  Interactive scenario planner. Input macro variables, see projected
  impact on price/hashrate/adoption. "What if Fed raises 50bps?"
  Must be carefully framed to avoid financial advice perception.

CYPHERPUNK SIGNAL FEED:
  Anonymous, vetted community-submitted on-chain observations.
  Signal-strength scored, curated by Commander team.
  Makes product feel like a collective resistance tool.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs
git add [relevant files]
git commit -m "feat(commander): Protocol Pulse Commander $29/mo — morning brief, accumulation zone advisor, pulse score with prediction accuracy, live spaces, sovereign stack tracker with snapshot, intel feed, briefing archive"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY BAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before calling this done, ask:
  - Would a serious Bitcoin holder pay $29/month for this TODAY?
  - Does every feature feel earned, not decorative?
  - Does it load fast on mobile?
  - Is the Accumulation Zone Advisor genuinely useful or just gimmick?
  - Would someone Sovereign Snapshot this and post it on X?
  - Does the Morning Brief consistently beat Marty Bent's newsletter?
  - Does it feel like it was built BY a Bitcoiner FOR Bitcoiners?

If any answer is no — keep building.
