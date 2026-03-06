# PROTOCOL PULSE — LIVE SPACES PULSE LAWS
# Real-Time X Spaces Intelligence Extraction & Distribution
# Maximum Squeeze From Every Live Bitcoin Conversation
# Status: GOSPEL. Dedicated buildout required.
# Created: 2026-03-05

---

## THE VISION

When someone drops a fire take in a live Bitcoin X Space, the half-life of that
moment is 5 minutes. After the Space ends, it's gone forever — unless Protocol
Pulse captures it in real-time, transcribes it, contextualizes it, and distributes
it across 8+ channels simultaneously.

This positions Protocol Pulse as the ARCHIVE of live Bitcoin discourse.
The investigative reporter who was in the room when it happened.
Not an eavesdropper — a journalist. Not a parrot — an intelligence analyst.

Nobody else does this. That's the moat.

---

## SECTION 1: CAPTURE PIPELINE

### Detection (every 5 minutes):
```
utils/spaces_monitor.py (cron */5)
  ├── Monitor 30+ Bitcoin influencer X accounts for active Spaces
  ├── Detection: yt-dlp / twspace-dl / profile polling
  ├── When Space detected: log "X SPACE LIVE: @{handle} — {title}"
  └── Trigger: capture pipeline activates
```

### Monitored Accounts:
@saylor, @APompliano, @LynAldenContact, @DocumentingBTC, @PeterMcCormack,
@nataborelle, @PrestonPysh, @MartyBent, @stephanlivera, @david_eng_mba,
@BitPaine, @jack, @saborosgrams, @maxkeiser, @BitcoinPierre,
@gladstein, @daboromir, @BitcoinBroski, @NickSzabo4, @matt_odell

Add new handles to utils/spaces_monitor.py MONITORED_ACCOUNTS list.
PBX can add handles at any time via Claude Code or direct file edit.

### Audio Capture:
```
Space goes live → twspace-dl captures audio stream
  ├── Stream saved to: data/spaces/{date}/{space_id}/audio.m4a
  ├── Audio piped to Whisper in 30-second chunks (GPU-accelerated)
  ├── Each chunk: transcribe → classify topics → score sentiment → score impact
  └── High-impact moments flagged for immediate distribution
```

### Impact Scoring (per 30-second chunk):
Each chunk gets scored 0-100:
- Controversial statement (strong opinion, disagreement): +25
- Specific data/metric mentioned (numbers, percentages): +20
- Named entity prediction ("Saylor will...", "BlackRock is going to..."): +20
- Emotional intensity (raised voice, emphasis, passion detected): +15
- Novel information (not covered by other channels today): +10
- Breaking news reference: +10

Threshold: Score >= 60 = "high-impact moment" → triggers distribution

---

## SECTION 2: DISTRIBUTION — 8 USE CASES (MAXIMUM SQUEEZE)

### USE CASE 1: Real-Time Quote Tweet
**Trigger:** High-impact moment detected (score >= 60)
**Action:** Auto-draft X post
**Format:**
```
"[Exact transcribed quote, max 200 chars]"

— @{speaker_handle}, LIVE right now

{1-2 sentence Protocol Pulse intelligence context}

[Quote-retweet link to the live Space]
```

**Example:**
```
"I think miners are about to capitulate harder than 2022. The math 
doesn't work below $65K with this difficulty."

— @PrestonPysh, LIVE right now

Difficulty just adjusted +3.2%. Hash price at $0.047/TH/day. 
The numbers back this up. 🔴

[Space link]
```

**Rules:**
- NEVER just transcribe. ALWAYS add Protocol Pulse intelligence context.
- Context must reference actual data (from daily_signals.json, terminal data)
- Tone: investigative reporter, not fanboy. Authoritative, not preachy.
- Human approval for first 50 posts (batches of 10 with PBX curation)
- After 50 approved with <5% rejection: auto-post with quality gate

### USE CASE 2: Reply Thread — Full Space Recap
**Trigger:** Space ends OR after 30+ minutes of capture
**Action:** Reply thread under the quote tweet
**Format:**
```
Reply 1: "Here's what just went down on @{host}'s Space..."
  - 4-5 bullet recap of key moments
  - Written as investigative reporter, not eavesdropper
  - "We were listening the whole time" energy

Reply 2: Protocol Pulse Intelligence Context
  - "This aligns with what we're tracking across 7 other channels..."
  - Cross-reference with daily_signals.json topic velocity
  - Connect to broader narrative

Reply 3: Best Moments Timestamps (if Space is recorded)
  - "🔥 @{speaker} at 14:32 on mining capitulation"
  - "📊 @{speaker} at 27:15 on ETF flow data"
  - Links to recorded Space with timestamps
```

**Tone Rules:**
- Humanize it. Sound like you were actively listening, not scraping.
- Investigative reporter style: "What emerged from tonight's Space was..."
- Less about Protocol Pulse, more about the substance and ecosystem implications
- Subtle brand integration: the intelligence context IS the brand
- Never preach. Never self-promote beyond the context being valuable.

### USE CASE 3: Site Dashboard — Live Flashcards
**Trigger:** Any high-impact moment (real-time)
**Action:** Push to protocolpulse.io/terminal Live Feed widget
**Format:**
```
┌─────────────────────────────────────────────────────┐
│ 🔴 LIVE  @PrestonPysh — Bitcoin Macro Weekly       │
│                                                      │
│ "Miners are about to capitulate harder than 2022"   │
│                                                      │
│ Sentiment: BEARISH (32/100) │ Topics: mining, price │
│ 📡 Tune in live →                                    │
└─────────────────────────────────────────────────────┘
```

**Design:**
- Glassmorphism card with BRAND.RED accents
- Animated pulse dot (live indicator)
- Quote text: BRAND.WHITE, Inter, 18px
- Handle: BRAND.RED, monospace
- "Tune in live →" is HYPERLINKED to the actual Space URL
- Cards auto-stack (newest on top, max 5 visible, scroll for more)
- Cards fade out after Space ends (marked as "ENDED — replay available")
- Advanced Remotion-style animations: slide-in from right, subtle glow pulse

**Implementation:**
- WebSocket push from Ultron → site (or polling every 15 seconds)
- data/intelligence/live_spaces_feed.json stores current feed
- Terminal API: GET /api/v2/terminal/spaces — returns live feed data
- Dashboard renders from API response

### USE CASE 4: Video Pipeline Injection
**Trigger:** Next daily Pulse Check production run
**Action:** Incorporate live quotes into the episode
**Format:**
- Script writer receives live_signals.json with Space quotes
- Narration: "Earlier today on @saylor's Space, he said..."
- If audio clip extracted: play the ACTUAL 10-second audio clip in the episode
  (from data/spaces/{date}/{space_id}/clips/{timestamp}.wav)
- Visual: Remotion SocialCard with the quote, styled as "LIVE from X Spaces"
  with a different accent color (amber/gold instead of red) to distinguish from tweets

**Rules:**
- Max 2 Space quotes per episode (don't overwhelm with Spaces content)
- Only use quotes scoring >= 70 impact
- Prefer quotes that connect to the episode's other clips (narrative coherence)

### USE CASE 5: Article Auto-Generation
**Trigger:** End of day (11 PM EST) if >= 3 notable Spaces occurred
**Action:** Generate article: "What Happened on Today's Bitcoin X Spaces"
**Format:**
- Title: "X Spaces Recap: [Top Topic] — What Bitcoin's Biggest Voices Said Today"
- 800-1500 words
- Structured: recap each Space, highlight key quotes, provide Protocol Pulse analysis
- Published on protocolpulse.io/articles
- Cross-posted to X as X Article (1/week max for X Articles)

**Content Structure:**
```
1. Opening hook (most impactful quote of the day)
2. Space-by-space recap (chronological)
   - Host, topic, duration, key speakers
   - Top 2-3 quotes with context
   - Protocol Pulse intelligence on the topic
3. Connecting the dots (what pattern emerges across today's Spaces?)
4. What to watch tomorrow (forward-looking, based on signals)
```

### USE CASE 6: Sentiment Trend Line During Space
**Trigger:** While Space is live (real-time)
**Action:** Track sentiment shift across the duration of the Space
**Format:**
```
Space start: Sentiment 50 (neutral)
  → 10 min: Sentiment 62 (bullish shift — host mentions ETF inflows)
  → 20 min: Sentiment 45 (bearish shift — guest raises mining concerns)
  → 30 min: Sentiment 71 (bullish reversal — new data shared)
  → End: Sentiment 65 (net bullish)
```

**Storage:** data/spaces/{date}/{space_id}/sentiment_timeline.json
**Terminal API:** GET /api/v2/terminal/spaces/{space_id}/sentiment
**Dashboard:** Real-time sentiment line chart during live Spaces

**Intelligence Value:** Detecting sentiment REVERSALS during a Space is alpha.
If a Space starts bearish and ends bullish (or vice versa), that's a leading
indicator of narrative shift. Flag these for Terminal subscribers.

### USE CASE 7: Newsletter "Live Moments" Section
**Trigger:** Daily newsletter generation (8 AM EST)
**Action:** Include top 3 quotes from yesterday's Spaces
**Format:**
```
🎙️ LIVE MOMENTS — Yesterday's X Spaces

"[Quote]" — @{handle} on {Space title}
"[Quote]" — @{handle} on {Space title}
"[Quote]" — @{handle} on {Space title}

→ Full recaps on protocolpulse.io
```

**Rules:**
- Only include quotes scoring >= 70 impact
- Diverse speakers (not all from the same Space)
- Link to the full recap article if one was generated (Use Case 5)

### USE CASE 8: Sovereign Tier Telegram/Discord Push
**Trigger:** High-impact moment detected (score >= 75)
**Action:** Push notification to Sovereign tier subscribers ($99/mo)
**Format:**
```
🔴 LIVE INTELLIGENCE

@PrestonPysh just said:
"Miners are about to capitulate harder than 2022"

Mining difficulty: +3.2% | Hash price: $0.047/TH

Tune in: [Space link]
```

**Rules:**
- ONLY Sovereign tier ($99/mo) gets real-time push alerts
- Commander tier ($49/mo) sees it in the dashboard with 15-minute delay
- Operator tier ($19/mo) sees it in daily digest only
- Free tier: sees it in next day's article only
- This tiered access is a KEY selling point for Sovereign tier

---

## SECTION 3: QUALITY GATES

### Anti-Spam Rules:
- Max 3 quote tweets per Space (don't flood timeline)
- Min 10 minutes between quote tweets (no rapid-fire)
- Never quote the same speaker twice in a row
- Never quote a mundane statement (impact score must be >= 60)
- If Space has < 50 listeners, don't quote-tweet (not enough signal)
- Weekends: reduce to max 1 quote tweet per Space (lower engagement)

### Accuracy Rules:
- Whisper transcription must be >= 90% confidence for direct quotes
- If confidence < 90%: paraphrase instead of quote ("According to @handle...")
- NEVER fabricate or embellish a quote
- If multiple speakers, verify correct attribution (speaker diarization)
- Cross-reference controversial claims with data before posting context

### Brand Voice for Spaces Content:
- Investigative reporter, not commentator
- "Here's what was said" not "Here's what we think about what was said"
- Data-first context: back up the quote with metrics
- Sovereign perspective subtly woven in (self-custody, decentralization)
- Dry wit permitted when appropriate ("Turns out, the math does math.")
- NEVER attack a speaker, even if you disagree
- NEVER use: "BREAKING", "🚨", "WOW", excessive emojis, or engagement bait

---

## SECTION 4: DATA ARCHITECTURE

### File Structure:
```
data/spaces/
  2026-03-05/
    space_abc123/
      metadata.json       # Space info: host, title, listeners, start/end time
      audio.m4a           # Full audio capture
      transcript.json     # Full timestamped transcript
      sentiment_timeline.json  # Sentiment score per 30-sec chunk
      highlights.json     # High-impact moments (score >= 60)
      clips/
        0842_mining_capitulation.wav  # Extracted audio clip (timestamp_topic)
        1415_etf_prediction.wav
  2026-03-06/
    ...

data/intelligence/
  live_spaces_feed.json   # Current/recent live feed for dashboard
  spaces_daily_digest.json  # Aggregated daily data for newsletter/article
```

### API Endpoints:
```
GET /api/v2/terminal/spaces          # Current live Spaces + recent quotes
GET /api/v2/terminal/spaces/feed     # Real-time flashcard feed
GET /api/v2/terminal/spaces/{id}     # Specific Space detail
GET /api/v2/terminal/spaces/{id}/sentiment  # Sentiment timeline
```

---

## SECTION 5: HUMAN-IN-THE-LOOP (First 50 Posts)

### Curation Process:
PBX reviews in batches of 10 via Telegram:

**Batch 1 (Posts 1-10):** Focus on tone calibration
- Are quotes accurate?
- Is the intelligence context relevant and data-backed?
- Does it sound like a journalist or a bot?
- Adjust: voice, length, emoji usage, context depth

**Batch 2 (Posts 11-20):** Focus on timing and relevance
- Are we catching the RIGHT moments?
- Is the impact scoring too sensitive or too conservative?
- Are we over-quoting certain speakers?
- Adjust: impact threshold, speaker diversity rules

**Batch 3 (Posts 21-30):** Focus on thread quality
- Are the recap threads comprehensive?
- Do they add genuine value?
- Would YOU retweet this?
- Adjust: thread length, context depth, CTA placement

**Batch 4 (Posts 31-40):** Focus on ecosystem response
- How are other accounts reacting to our quote tweets?
- Are Space hosts acknowledging us? (Good sign)
- Any negative feedback? (Adjust immediately)
- Adjust: relationship management, attribution etiquette

**Batch 5 (Posts 41-50):** Graduation
- Rejection rate < 5%? → Approve auto-mode
- Rejection rate 5-15%? → One more batch of 10
- Rejection rate > 15%? → Recalibrate entirely before continuing

After graduation: Auto-post with quality gate (impact >= 60, confidence >= 90%)
PBX can always override via Telegram: reply "KILL" to retract, "PAUSE" to halt

---

## SECTION 6: IMPLEMENTATION PHASES

### Phase 1: Detection + Basic Distribution (Week 1)
- spaces_monitor.py detecting live Spaces (DONE)
- Whisper transcription of captured audio
- Impact scoring on 30-second chunks
- Manual quote-tweet drafting (PBX approves via Telegram)
- First 10 posts curated

### Phase 2: Dashboard + Auto-Distribution (Week 2)
- Live flashcards on protocolpulse.io/terminal
- API endpoints for Spaces data
- Auto-generated recap threads
- Sentiment timeline tracking
- Posts 11-30 curated

### Phase 3: Full Pipeline Integration (Week 3)
- Video pipeline reads Space quotes for episodes
- Newsletter includes Live Moments section
- Daily recap articles auto-generated
- Sovereign tier push alerts active
- Posts 31-50 curated, approaching auto-mode

### Phase 4: Scale + Intelligence (Week 4+)
- Auto-mode activated (if curation passes)
- Multi-Space parallel capture (when 40 additional 4090s come online)
- Cross-Space narrative detection (same topic across multiple Spaces = breaking)
- Historical Space archive becomes searchable intelligence
- "What did @saylor say about mining in the last 30 days?" → answerable

---

## SECTION 7: RELATIONSHIP MANAGEMENT

### How to NOT Be Seen as an Eavesdropper:

1. **Credit generously.** Always tag the host AND quoted speaker.
2. **Add value.** The data context makes us a journalist, not a parrot.
3. **Engage authentically.** Reply to hosts who acknowledge the quote tweet.
4. **Request permission proactively.** DM top hosts: "We love recapping your Spaces
   with data context. Is that cool with you?" Most will say yes and even promote it.
5. **Feature hosts.** When a host's Space generates high engagement on our recap,
   tag them: "Your Space on mining just drove 50K impressions on our recap. 🔥"
6. **Reciprocity.** Tune into Spaces as Protocol Pulse and occasionally speak up
   (PBX or team member). This makes us a PARTICIPANT, not an observer.
7. **Never misquote.** One inaccurate quote destroys trust. When in doubt, paraphrase.

### The Goal:
Space hosts should WANT Protocol Pulse to recap their Spaces.
It drives their listeners, amplifies their reach, and gives them data context
they wouldn't have otherwise. This is a symbiotic relationship, not extraction.

---

*This document defines the Live Spaces Pulse as a standalone intelligence product.
It must feel like journalism, not automation.
Pair with: LIVE_INTELLIGENCE_LAWS.md, X_POSTING_LAWS.md, MARKETING_STRATEGY_LAWS.md,
PULSE_TERMINAL_LAWS.md*
