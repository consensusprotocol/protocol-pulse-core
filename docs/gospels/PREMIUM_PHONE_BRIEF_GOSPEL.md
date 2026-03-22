# GOSPEL: PREMIUM MORNING PHONE CALL BRIEF
# Version 1.0 | March 2026
# Status: FOUNDATIONAL SPEC — NOT YET BUILT
# Product tier: PREMIUM (paid subscribers only)

## THE VISION
Every morning at 5:58 AM ET, Protocol Pulse premium subscribers receive
a phone call from the Oracle avatar (Eryn). She delivers a 90-second
personalised Bitcoin intelligence brief — synthesized from real-time
Bloomberg terminal data, WSJ headlines, and on-chain signals pulled
in the 2 minutes before the call fires.

The call ends. The subscriber goes to work with more signal than
any institutional trader had at that hour in 2020.

## PRODUCT DIFFERENTIATOR
This is not a podcast. Not a newsletter. A PHONE CALL.
The avatar speaks to YOU. She knows your timezone, your holdings tier
(if disclosed), and the macro signals that matter to your context.
Nobody else in Bitcoin media does this. It is the moat.

## ARCHITECTURE

### DATA PIPELINE (5:55 AM ET — 3 minutes before call)
Sources (in priority order):
1. Bloomberg Terminal API (if available) or Bloomberg RSS scrape
2. WSJ Markets RSS feed (free, real-time)
3. Reuters Finance RSS
4. Nitter fresh pull (30-minute window, Tier 1 handles only)
5. CoinGecko BTC price + 1h/4h/24h change
6. Mempool.space: fee rate, block height, hashrate
7. Fear & Greed Index
8. Protocol Pulse morning_intelligence_brief.json (already generated at 6am)

### SCRIPT GENERATION (5:56 AM ET)
Model: Claude Sonnet 4.6 (NOT local — this is premium, quality is the product)
Max tokens: 600 (90-second spoken brief at 150 words/min = ~225 words)
Format: HOOK → THE NUMBER → THE SIGNAL → THE MACRO → THE TAKE → SIGN-OFF

HOOK (5-8 seconds): The single most important thing that happened overnight.
  Not "good morning." Not "here is your brief." The signal, immediately.
  Example: "Bitcoin held $70,000 through the Iran strike. The petrodollar just got weaker."

THE NUMBER (10 seconds): One specific metric that matters today.
  Example: "Hashrate: 970 exahash. Difficulty adjustment in 3 days. Miners are not scared."

THE SIGNAL (20 seconds): What the smart money is doing or saying.
  From Tier 1 Nitter handles + on-chain. One specific action or statement.

THE MACRO (20 seconds): One macro event connecting to Bitcoin's thesis.
  WSJ/Bloomberg headline synthesis. Why it matters for sound money specifically.

THE TAKE (25 seconds): Eryn's analysis. Original. Not obvious.
  This is the premium value — the synthesis nobody else does at 6am.

SIGN-OFF (5 seconds): "Stay sovereign. Eryn, Protocol Pulse."

### VOICE
Avatar: Eryn (Kokoro af_heart — warm female, already running)
TTS: Kokoro af_heart on GPU 0 (same as episode narrator)
Output: 16kHz mono MP3, 90 seconds max, optimised for phone playback
Alternative: ElevenLabs Jessica voice for premium tier (higher quality)

### DELIVERY
Provider: Twilio Programmable Voice
Method: POST to Twilio API with TwiML that plays the MP3
Timing: Cron at 5:55 ET → generate → 5:58 ET → call fires
Subscriber list: DB table premium_subscribers (phone, timezone, tier)
Personalisation: "Good morning [first name]" as opening if name known

### PERSONALISATION TIERS
Tier 1 ($29/mo): Standard brief, same for all subscribers
Tier 2 ($79/mo): Personalised — brief references their local market if known,
                 mentions their timezone-appropriate context
Tier 3 ($199/mo): Full personalisation — references their specific holding
                  context, asks 1 follow-up question for feedback signal

## FILES (to build)
Service:         ~/protocol_pulse/services/phone_brief_service.py
Script gen:      ~/protocol_pulse/services/phone_brief_generator.py
Data fetcher:    ~/protocol_pulse/services/realtime_market_fetcher.py
Subscriber DB:   Table: premium_subscribers (id, phone, name, tier, timezone, active)
Audio cache:     ~/protocol_pulse/data/phone_briefs/{DATE}/brief_{TIER}.mp3
Cron:            55 9 * * 1-5 (5:55am ET Mon-Fri = 9:55 UTC)

## API REQUIREMENTS
Twilio:    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env
Bloomberg: BLOOMBERG_API_KEY (premium — use RSS scrape as fallback)
WSJ RSS:   https://feeds.content.dowjones.io/public/rss/mw_marketpulse (free)
Reuters:   https://feeds.reuters.com/reuters/businessNews (free)

## QUALITY STANDARDS
- Script must be reviewed by Claude Sonnet before TTS synthesis
- No hallucinated data — all numbers verified against live sources
- If BTC price data fails: ABORT call, send SMS fallback instead
- Brief must pass length check: 200-260 words (88-104 seconds at 150wpm)
- No call fires without audio file confirmed > 50KB

## REVENUE MODEL
Phase 1: Invite-only beta (50 subscribers), free for early Protocol Pulse community
Phase 2: $29/mo tier (standard), $79/mo (personalised)
Phase 3: Enterprise ($499/mo) — multiple team members, custom time windows
Annual run rate at 500 subscribers ($29 avg): $174,000/yr

## BUILD ORDER (do not start until Phase 1 pipeline is stable)
Step 1: realtime_market_fetcher.py (Bloomberg RSS + WSJ + CoinGecko)
Step 2: phone_brief_generator.py (Claude Sonnet script + Kokoro TTS)
Step 3: phone_brief_service.py (Twilio delivery + subscriber management)
Step 4: Premium subscriber DB table + admin UI
Step 5: Beta with 5 handpicked Protocol Pulse community members
Step 6: Public launch with waitlist

## WHAT NEVER CHANGES
- Script model: Claude Sonnet minimum. Never Haiku. Never local for this.
- Call fires Mon-Fri only (markets closed weekends = less signal)
- Always verify BTC price before firing — never deliver stale data
- Subscriber phone numbers encrypted at rest
- Opt-out must be instant — one SMS reply "STOP" kills all future calls
- Never call before 5:58am ET or after 6:15am ET

## CC SPEC LOCATION
~/protocol_pulse/docs/cc_phone_brief_build.md (to be written when pipeline stable)


## CALL TIME PREFERENCES (user-selectable)
Subscribers choose their preferred delivery window at signup.
Available slots (all ET, Mon-Fri):

  SLOT A | 5:58 AM  | Pre-Market (default) | before US market open
  SLOT B | 3:58 AM  | UK Open              | before London market open
  SLOT C | 11:58 PM | Asia Close           | end of Asia session
  SLOT D | 12:58 PM | Lunch                | midday market check-in
  SLOT E | 3:58 PM  | Market Close         | before US market close
  SLOT F | 7:58 PM  | Evening              | post-market debrief

DB field: premium_subscribers.call_slot (A/B/C/D/E/F)
Default:  SLOT A
Cron:     One entry per active slot, fires 2 minutes before call time

Brief content adapts to slot:
  Morning (A,B):   overnight moves + what to watch today
  Midday (D):      morning recap + afternoon signal
  Close/Evening (E,F): daily summary + overnight thesis

## VOICE PREFERENCES (user-selectable)
Two options matching Protocol Pulse on-air talent:

  VOICE F | Eryn | female | Kokoro af_heart (ElevenLabs Jessica for premium)
  VOICE M | PBX  | male   | Kokoro am_onyx (StyleTTS2 PBX clone when ready)

DB field: premium_subscribers.voice_pref (F/M)
Default:  F (Eryn)

Same script content for both voices. TTS generates both in parallel,
serves correct audio per subscriber. No additional latency.
