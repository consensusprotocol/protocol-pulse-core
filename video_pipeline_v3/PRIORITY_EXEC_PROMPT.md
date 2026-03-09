Read PIPELINE_LAWS.md, ~/protocol_pulse/CONTENT_INTELLIGENCE_LAWS.md, and ~/protocol_pulse/PULSE_TERMINAL_LAWS.md first.

This session has 3 tasks. Execute ALL sequentially.

=== TASK 1: CHANNEL NETWORK EXPANSION (18 → 75+ channels) ===

Expand channels.yaml from 18 to 75+ channels across 4 tiers.
Research and add real, active Bitcoin YouTube channels using yt-dlp to verify each URL works.

TIER 1 — Core Bitcoin (priority 1, always scan, always transcribe):
Keep existing: Bitcoin Magazine, Simply Bitcoin, WBD, TFTC, Preston Pysh, The Bitcoin Layer, Blockworks, Natalie Brunell, Robert Breedlove, Andreas Antonopoulos, Unchained

Add these (verify URLs with yt-dlp --flat-playlist --max-downloads 1):
- Swan Bitcoin (@SwanBitcoin)
- Bitcoin Fundamentals (Preston Pysh podcast channel)
- BTC Sessions (@BTCSessions)
- Stephan Livera (@stephanlivera)
- Bitcoin Audible (@BitcoinAudible)
- Peter McCormack (@PeterMcCormack — already in WBD but may have separate)
- Saifedean Ammous (@saaborosgrams)
- Bitcoin Magazine Pro (@BitcoinMagazinePro)
- The Investor's Podcast Network — Bitcoin specific (@TIPBitcoin)
- American HODL (@americanhodl)

TIER 2 — Bitcoin Adjacent / Macro (priority 2, scan daily, transcribe if Bitcoin keywords in title):
- Real Vision Finance (@RealVisionFinance)
- Lyn Alden (@LynAldenContact — if she has a channel)
- George Gammon (@GeorgeGammon)
- Coin Bureau (@CoinBureau)
- Anthony Pompliano (@AnthonyPompliano)
- Ark Invest (@ArkInvest)
- Raoul Pal / Real Vision Crypto (@RealVisionCrypto)
- Winklevoss / Gemini (@Gemini)
- Marty Bent Rabbit Hole Recap (@MartyBent if separate from TFTC)
- Bitcoin Explained (@Bitcoin_Explained)
- Once Bitten (@OnceBittenPodcast)
- Max Keiser (@MaxKeiser)
- Stacker News (@StackerNews)
- Fountain (@Fountain_app)
- Nostr-related channels

TIER 3 — Tradfi / Macro that covers Bitcoin (priority 3, scan daily, ONLY transcribe if Bitcoin/BTC in title):
Add filter_keywords: ["bitcoin", "btc", "crypto", "digital asset", "digital currency", "saylor", "etf"]
- CNBC (@CNBC)
- Bloomberg Television (@BloombergTV)
- Fox Business (@FoxBusiness)
- Yahoo Finance (@YahooFinance)
- Wall Street Journal (@WSJ)
- Financial Times (@FinancialTimes)
- Kitco News (@KitcoNews)
- Bankless (@Bankless)
- The Block (@TheBlock)

TIER 4 — Mainstream with Bitcoin moments (priority 4, scan hourly, ONLY if Bitcoin keyword matches):
Keep existing: Joe Rogan, Lex Fridman, PBD, Tucker Carlson, All-In, Megyn Kelly, JRE Clips

For EVERY channel added:
1. Verify URL works: yt-dlp --flat-playlist --max-downloads 1 {url} 2>&1 | head -3
2. If URL fails, try alternate handle format
3. If channel doesn't exist or is dead, skip it
4. Add to channels.yaml with correct tier, priority, and filter_keywords where applicable

The daemon already handles the 15-minute scan cycle. Adding channels to yaml is all that's needed.

Commit: git add channels.yaml -m 'feat: expand channel network 18 → 75+ channels across 4 tiers'

=== TASK 2: NEWSLETTER ACTIVATION ===

The newsletter system (Resend API) is configured on Replit but not sending.
Check current state:
  Search for Resend integration: grep -rn 'resend\|RESEND\|newsletter' ~/protocol_pulse/*.py ~/protocol_pulse/routes*.py

Build utils/newsletter_engine.py:
  - Reads the latest 5 articles from the API (/api/v2/articles?per_page=5)
  - Reads daily_signals.json for top 3 topics
  - Reads sentiment.json for overall market sentiment
  - Compiles into an HTML email template:
    Subject: "Protocol Pulse Daily Brief — {date} | BTC {sentiment_label}"
    Body:
      - Top 3 topics with velocity scores
      - Sentiment gauge (bullish/bearish/neutral with score)
      - Top 5 article summaries with links to protocolpulse.io
      - "Watch Today's Pulse Check" link to YouTube (when live)
      - Node Pulse: total reachable nodes + net change
      - Footer: unsubscribe link, social links

  - Sends via Resend API (key in Replit secrets)
  - Target: send at 8 AM EST daily

Create the cron entry on Ultron (trigger Replit endpoint):
  0 13 * * * curl -s https://protocolpulse.replit.app/api/newsletter/send -H "Authorization: Bearer {token}" >> ~/protocol_pulse/logs/newsletter.log 2>&1

Or build the sender on Ultron directly if Resend API key is available there.

Commit: git add utils/newsletter_engine.py -m 'feat: daily newsletter engine with intelligence digest'

=== TASK 3: AVATAR AUDIT ===

Check the current state of the Proto P avatar system on Ultron:
  ls -la ~/protocol_pulse/avatar_server.py
  grep -n 'apply_blink\|wav2lip\|Wav2Lip\|lip_sync' ~/protocol_pulse/avatar_server.py | head -20
  tmux capture-pane -t avatar -p 2>/dev/null | tail -10
  curl -s http://localhost:8200/health 2>/dev/null

Report:
  - Is avatar_server.py running?
  - What lip sync engine is active?
  - Is the blink bug still present (apply_blink black oval)?
  - What's the current render time per segment?
  - Is Gemini vision integrated?

DO NOT fix the avatar yet. Just audit and report findings.
We need the status before deciding next steps.

Commit: git add -A && git push origin main

After all 3 tasks: report channel count, newsletter status, and avatar health.