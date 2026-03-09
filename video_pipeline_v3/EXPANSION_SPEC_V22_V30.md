# PROTOCOL PULSE — EXPANSION SPEC V22-V30
# The features that make this unprecedented in Bitcoin media
# Created: 2026-03-04
# Status: GOSPEL alongside MASTER_PLAN_OF_ACTION.md

---

## THE THESIS

V11-V21 fixes what's broken and builds a reliable autonomous daily machine.
V22-V30 is where Protocol Pulse becomes something that doesn't exist anywhere
else. Every feature below compounds on the V11-V21 foundation. None of these
should be attempted until V13 (auto-upload + quality gate) is live and stable.

---

## V22 — MULTI-FORMAT OUTPUT ENGINE

### What it does
One scan, one Claude analysis pass, six distribution formats. The pipeline
already does the expensive work (scanning 18 channels, transcribing, selecting
clips, writing scripts). Right now it throws away 80% of that value by only
producing one video. This version produces all formats from a single run.

### Output formats from every daily run
1. **12-min YouTube episode** (existing, enhanced)
2. **3-5 YouTube Shorts** (existing shorts_cutter.py, enhanced with better selection)
3. **Audio-only podcast** (existing podcast_feed.py, auto-push to Fountain RSS)
4. **Written article** for protocolpulse.io (new: script → article adapter)
5. **Tweet thread** summarizing episode (new: script → thread formatter)
6. **Nostr long-form note** (new: NIP-23 post via relay)

### Architecture
```
daily_producer.py (existing 12-step pipeline)
     ↓ after Step 7 (assembly complete)
     ↓
format_multiplier.py (NEW)
  ├── shorts_cutter.py → 3-5 shorts with captions
  ├── podcast_feed.py → MP3 + RSS push to Fountain
  ├── article_adapter.py → script → article HTML → POST to /api/v2/articles
  ├── thread_formatter.py → script → 8-tweet thread → POST to X API
  └── nostr_publisher.py → script → NIP-23 long-form → relay publish
```

### Quality rules
- Article adapter strips TTS-specific language ("as we discussed earlier")
  and rewrites for reading, not listening. Claude does a rewrite pass.
- Tweet thread is max 8 tweets. First tweet is the hook. Last tweet links
  to the full episode. Each tweet is under 280 chars with zero em dashes.
- Shorts selection picks the 3 highest-impact moments from the clip
  selection, not random segments. Each short has burned-in captions.
- Podcast MP3 strips all visual-only segments (intro animation, transitions)
  and keeps only audio (narration + clip audio + music bed).

### Verification
- All 6 formats produced in a single pipeline run
- Article appears on protocolpulse.io/articles within 5 minutes of render
- Tweet thread posted within 10 minutes of upload
- Podcast episode live on Fountain within 15 minutes
- Each format passes its own quality check

### Estimated build: 3 sessions, 6 hours total

---

## V23 — CONTINUATION SERIES ENGINE

### What it does
Produces a SECOND daily video that follows narrative arcs across episodes.
The daily brief covers today's hottest topics. The continuation series
tracks evolving stories across days and weeks.

### How it works
```
data/story_arcs.json — tracks ongoing stories
{
  "arcs": [
    {
      "id": "etf-flow-surge-2026q1",
      "title": "The ETF Flow Surge",
      "started": "2026-02-28",
      "last_covered": "2026-03-03",
      "episodes_count": 4,
      "key_developments": [
        "2026-02-28: BlackRock IBIT hits $50B AUM",
        "2026-03-01: Fidelity reports record inflows",
        "2026-03-03: Bitwise files for new ETF product"
      ],
      "status": "active",
      "next_angle": "What happens when ETF holdings exceed exchange reserves?"
    }
  ]
}
```

### Production flow
1. After daily brief renders, `arc_analyzer.py` scans today's clips and
   transcripts for topics that match active arcs in story_arcs.json
2. If a match is found, it generates a "continuation episode" script that:
   - Opens with "Previously on Protocol Pulse..." recap (30 seconds)
   - Shows the new development with fresh clip
   - Adds analysis: what changed, what it means, what to watch for
   - Closes with "This story continues. Subscribe for updates."
3. Continuation episodes are 5-7 minutes (shorter than daily brief)
4. Published to a separate "Deep Signal" playlist on YouTube
5. Arc status updates automatically: episode count, last covered, next angle

### Arc lifecycle
- **Birth:** When 3+ channels cover the same topic within 48 hours
- **Active:** New developments detected in subsequent scans
- **Dormant:** No new developments for 7 days → moved to dormant
- **Closed:** PBX manually marks as resolved, or auto-close after 30 days dormant

### Why this is powerful
- Creates appointment viewing: "I need to check what happened with the ETF story"
- YouTube algorithm rewards series/playlists with sequential viewing
- Each continuation episode links back to previous episodes → watch time compounds
- The "Previously on..." format is proven in every successful serialized show

### Verification
- story_arcs.json updated after every scan
- Continuation episode only produced when genuine new development exists
- Never produces a continuation that just repeats yesterday's content
- Separate YouTube playlist maintained automatically

### Estimated build: 2 sessions, 4 hours total

---

## V24 — TOPIC VELOCITY DETECTOR (BREAKING NEWS)

### What it does
Detects when something is breaking in Bitcoin and triggers an emergency
episode within 60 minutes of the event, before any other Bitcoin YouTube
channel can produce a polished response.

### How it detects breaking news
```
velocity_detector.py runs every 30 minutes (lightweight scan)
  ↓
Checks: how many of the 18 channels published about the same topic
in the last 3 hours?
  ↓
If topic_count >= 4 channels AND time_window <= 3 hours:
  → BREAKING NEWS DETECTED
  → Trigger emergency pipeline (skip queue, max priority)
  → Telegram alert to PBX: "BREAKING: [topic]. 6 channels covering.
    Emergency episode rendering. Reply HOLD to pause."
  → If no HOLD reply within 15 minutes: auto-render and upload
```

### Emergency pipeline (fast path)
- Skip full channel scan (use cached transcripts from velocity scan)
- Select top 2 clips only (not 5)
- Script is shorter: 4-5 minutes, focused on the single breaking topic
- Thumbnail auto-generates with "BREAKING" banner
- Upload with "BREAKING:" prefix in title
- YouTube notification sent to subscribers immediately (bell icon)
- Tweet + Nostr post within 5 minutes of upload

### Topic clustering
The velocity detector doesn't match on keywords alone. It uses Claude to
cluster video titles by semantic topic:
- "BlackRock Bitcoin ETF hits record" + "IBIT inflows surge" + "ETF buying
  accelerates" = same topic cluster, even though keywords differ
- Cluster confidence must be > 0.8 to trigger breaking

### Why this is a moat
- Most Bitcoin YouTubers take 24-48 hours to produce a response to events
- Protocol Pulse can have a polished breaking episode live in 60 minutes
- First-mover advantage on breaking news = massive impression spikes
- YouTube rewards channels that are first to cover trending topics

### Safeguards
- Max 1 breaking episode per day (prevents trigger-happy false positives)
- PBX can HOLD via Telegram within 15 minutes
- Quality gate still applies: score must be >= 75 (lower threshold for breaking)
- If the "breaking" topic turns out to be nothing, the episode can be unlisted

### Verification
- Velocity detector catches a real multi-channel topic cluster
- Emergency pipeline renders in under 15 minutes
- Breaking episode goes live within 60 minutes of first detection
- Telegram alert works end-to-end

### Estimated build: 2 sessions, 4 hours total

---

## V25 — PBX VOICE CLONE INTEGRATION

### What it does
Replaces the stock ElevenLabs voice with a cloned version of PBX's voice.
Every episode sounds like PBX recorded it personally.

### PBX action required (before this version starts)
1. Record 30 minutes of yourself reading scripts in your natural cadence
2. Include: conversational tone, emphasis on data points, occasional humor
3. Upload to ElevenLabs Professional Voice Cloning
4. Get the voice_id from ElevenLabs dashboard
5. Share voice_id with the pipeline

### Pipeline integration
```python
# tts_engine.py — updated voice config
VOICES = {
    "pbx": {
        "voice_id": "YOUR_CLONED_VOICE_ID",
        "stability": 0.45,
        "similarity_boost": 0.85,
        "style": 0.15,
        "use_speaker_boost": True
    },
    "host2": {
        "voice_id": "piTKgcLEGmPE4e6mEKli",  # Nicole stays as co-host
        "stability": 0.40,
        "similarity_boost": 0.80,
        "style": 0.20
    }
}
```

### Dual-host dynamic
- PBX voice is the lead anchor. Opens the show. Delivers the cold open.
  Introduces clips. Delivers the closing.
- Nicole (or future co-host voice) handles transitions, social segment,
  and lighter commentary. Creates contrast and pacing.
- Script writer tags each line with `[PBX]` or `[COHOST]` so TTS engine
  routes to the correct voice.

### Why this is a moat
- Nobody can clone your voice without your consent
- Builds personal brand equity: viewers associate the voice with the show
- Scales your presence: you're "hosting" every episode without recording
- The co-host dynamic makes it feel like a real two-person show

### Verification
- PBX listens and confirms the clone sounds natural, not robotic
- Co-host transitions sound like a real conversation, not two robots
- Clone voice handles Bitcoin terminology correctly (sats, UTXO, halving)

### Estimated build: 1 session, 1 hour (after PBX provides voice_id)

---

## V26 — COMPETITIVE INTELLIGENCE ENGINE

### What it does
Tracks performance of partner channels' videos to identify which topics
and formats are resonating across the Bitcoin YouTube ecosystem right now.
Uses this to weight the pipeline's topic selection.

### Data collected per partner channel video
```json
{
  "video_id": "abc123",
  "channel": "Simply Bitcoin",
  "title": "Is This the Blow-Off Top?",
  "published_at": "2026-03-04T10:00:00Z",
  "views_24h": 45000,
  "views_7d": 120000,
  "avg_views_channel": 30000,
  "performance_ratio": 4.0,
  "topic_cluster": "price-action-top",
  "thumbnail_style": "face-reaction"
}
```

### Performance ratio
`views_7d / avg_views_channel_30d` = how much this video outperformed
the channel's baseline. A ratio of 4.0 means 4x their normal views.
Topics and formats with high ratios across multiple channels = validated demand.

### How it feeds the pipeline
```
channel_intelligence.py (weekly cron)
  ↓
Pulls view counts for all scanned videos (YouTube Data API)
  ↓
Computes performance_ratio per video
  ↓
Clusters by topic → ranks topics by avg performance_ratio
  ↓
Outputs data/topic_demand.json:
  {
    "trending_topics": [
      {"topic": "ETF flows", "avg_ratio": 3.2, "channels_covering": 6},
      {"topic": "mining difficulty", "avg_ratio": 1.8, "channels_covering": 4}
    ]
  }
  ↓
SELECTION_PROMPT reads topic_demand.json
  → "Prioritize clips about ETF flows (3.2x avg performance across 6 channels)"
```

### Why this matters
- You're not guessing what topics to cover. You know.
- Topics that are proven to get views across the ecosystem get prioritized
- Topics that consistently underperform get deprioritized
- This is what media companies pay millions for: demand-side intelligence

### Verification
- topic_demand.json populated with real view count data
- SELECTION_PROMPT references trending topics
- Episode topic selection demonstrably correlates with high-demand topics

### Estimated build: 2 sessions, 3 hours total

---

## V27 — DYNAMIC THUMBNAIL A/B TESTING

### What it does
Generates 3 thumbnail variants per episode. Uploads with variant A.
After 24 hours, swaps to variant B. After 48 hours, keeps the winner.

### Variant styles
1. **Face-focused:** Zoomed-in face of the featured speaker with reaction expression.
   Title text overlay. Yellow/red accent. (Proven highest CTR in YouTube data.)
2. **Data-focused:** BTC price chart with dramatic arrow. Key metric in large font.
   Clean, Bloomberg-style. Works for data-heavy episodes.
3. **Text-focused:** Bold title text on dark background with red accent bar.
   Protocol Pulse branding prominent. Works when no strong face/data hook.

### A/B test flow
```
Episode uploads with Variant A (face-focused, default highest CTR)
  ↓ 24 hours later
YouTube Analytics API pulls CTR for the episode
  ↓
If CTR < channel_avg_ctr:
  Swap thumbnail to Variant B (data-focused)
  ↓ 24 hours later
  Pull CTR again
  ↓
  Keep whichever variant had higher CTR
  ↓
Log winning style to data/thumbnail_performance.json
  ↓
After 20 episodes: thumbnail_gen.py defaults to the statistically
winning style for each topic cluster
```

### Face extraction
For face-focused thumbnails, the pipeline needs a face from the clip.
`thumbnail_gen.py` enhanced to:
1. Extract frame at the most expressive moment of the featured clip
2. Run face detection (OpenCV Haar cascade, already on Ultron)
3. Crop and enhance the face
4. Composite onto thumbnail template with title text

### Verification
- 3 variants generated per episode
- Swap happens automatically at 24h mark
- Winner logged and influences future defaults
- Face extraction produces usable faces (not blurry, not off-center)

### Estimated build: 2 sessions, 3 hours total

---

## V28 — CROSS-EPISODE NARRATIVE MEMORY

### What it does
Gives the script writer memory of the last 5 episodes. Creates continuity
references that make the show feel serialized, not standalone.

### Episode memory structure
```json
// data/episode_memory.json
{
  "recent_episodes": [
    {
      "date": "2026-03-03",
      "top_topics": ["ETF flows", "mining difficulty", "Fed policy"],
      "key_quotes": [
        "Saylor called it 'the most important quarter for Bitcoin adoption'"
      ],
      "unresolved_threads": [
        "Will the difficulty adjustment break mining margins?"
      ],
      "btc_price": 73100
    }
  ]
}
```

### How the script writer uses it
SCRIPT_PROMPT gets a new section:
```
CONTINUITY RULES:
- Check episode_memory.json for the last 5 episodes
- If today's clips cover a topic from yesterday, open with:
  "Yesterday we showed you [X]. Today, the story develops..."
- If an unresolved thread from a previous episode gets resolved today,
  explicitly close the loop: "Remember when we asked [question]?
  We now have the answer."
- Reference BTC price changes: "Bitcoin is at $73,500, up $400 from
  yesterday's show."
- Never repeat the same insight two days in a row. If yesterday covered
  it, acknowledge and add NEW analysis only.
```

### Why this transforms the show
- Viewers feel like they're following a story, not watching isolated clips
- "Previously on..." references reward consistent viewers
- Unresolved threads create cliffhangers that drive return viewing
- Price context across episodes creates a running narrative
- This is what makes podcasts addictive: the parasocial continuity

### Verification
- episode_memory.json updated after every render
- Script contains at least one continuity reference per episode
- Never repeats yesterday's exact insight (dedup check)

### Estimated build: 1 session, 2 hours

---

## V29 — AUTOMATED PARTNER OUTREACH

### What it does
After every episode upload, automatically emails the channels whose clips
were featured with a professional outreach message.

### Email template (via Resend, already configured)
```
Subject: Your analysis was featured on Protocol Pulse

Hi [Channel Name] team,

We featured a clip from your video "[Video Title]" in today's
Protocol Pulse episode: [YouTube URL]

Protocol Pulse is a daily Bitcoin intelligence briefing reaching
[subscriber_count] subscribers. We select the most insightful
moments from across the Bitcoin YouTube ecosystem.

If you'd like to be notified when we feature your content, or
discuss cross-promotion, reply to this email.

Keep building.
— Protocol Pulse
```

### Outreach rules
- Max 1 email per channel per week (no spam)
- Only email channels with a public contact (YouTube "About" page email)
- Track responses in `data/partner_outreach.json`
- If a channel replies positively, flag them as "active partner" in channels.yaml
  → their clips get slight priority boost
- If a channel requests removal, immediately add to exclusion list

### Why this compounds
- Every featured clip becomes a relationship touchpoint
- Channels start looking forward to being featured → they share your episodes
- Cross-promotion from a channel with 500K subscribers is worth more than
  any ad spend
- Over 6 months, you build a network of 50+ Bitcoin creators who know your brand

### Verification
- Outreach email sent within 1 hour of upload
- No duplicate emails within 7 days
- Response tracking logged
- Opt-out respected immediately

### Estimated build: 1 session, 1.5 hours

---

## V30 — THE PULSE TERMINAL (SUBSCRIBER INTELLIGENCE DASHBOARD)

### What it does
Exposes the pipeline's scanning intelligence as a real-time subscriber-facing
product on protocolpulse.io. This is the feature that transforms Protocol Pulse
from a media company into an intelligence platform.

### What subscribers see
```
protocolpulse.io/terminal (premium tier)

┌─────────────────────────────────────────────────────┐
│ PULSE TERMINAL                        BTC $73,500 ↑ │
├─────────────────────────────────────────────────────┤
│                                                     │
│ TOPIC VELOCITY (last 6 hours)                       │
│ ████████████ ETF Flows (7 channels, BREAKING)       │
│ ████████     Mining Difficulty (5 channels)         │
│ ██████       Fed Policy (4 channels)               │
│ ████         Lightning Network (3 channels)         │
│ ██           Sovereign Wealth Funds (2 channels)    │
│                                                     │
│ ENTITY MENTIONS (24h trend)                         │
│ ↑ Saylor (mentioned 14x, up 300% from yesterday)   │
│ ↑ BlackRock (mentioned 9x, up 150%)                │
│ → Tether (mentioned 5x, stable)                    │
│ ↓ Binance (mentioned 2x, down 60%)                 │
│                                                     │
│ SENTIMENT SHIFT                                     │
│ Overall: BULLISH (72/100, up from 65 yesterday)     │
│ Institutional: VERY BULLISH (85/100)                │
│ Retail: NEUTRAL (55/100)                            │
│                                                     │
│ CLIPS FLAGGED AS SIGNIFICANT (pre-episode)          │
│ 1. Saylor on sovereign wealth fund Bitcoin alloc... │
│ 2. Lyn Alden: "This is the accumulation phase"...   │
│ 3. Simply Bitcoin: Mining margins at 2-year low...  │
│                                                     │
│ NEXT EPISODE RENDERING IN: 4h 32m                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Data sources (all already collected by the pipeline)
- **Topic velocity:** channel_scanner.py already transcribes and classifies topics
- **Entity mentions:** NER pass on transcripts (spaCy or Claude extraction)
- **Sentiment:** Claude already classifies mood for music selection
- **Significant clips:** clip_selector.py already ranks clips by importance
- **Price data:** mempool.space API already called in Step 1

### Architecture
```
Pipeline scan (runs every 6 hours or on breaking detection)
  ↓
Writes to data/terminal_state.json:
  - topic_velocity[]
  - entity_mentions[]
  - sentiment_scores{}
  - flagged_clips[]
  - next_episode_eta
  ↓
New Flask API endpoint: GET /api/v2/terminal
  ↓
Next.js page: /terminal (React components, auto-refresh every 60s)
  ↓
Premium gate: only logged-in subscribers with Operator+ tier see full data
Free tier sees: topic velocity (top 3 only) + overall sentiment
```

### Why this is the killer feature
- Bloomberg Terminal charges $24,000/year for financial intelligence
- Protocol Pulse Terminal at $50/month for Bitcoin-specific intelligence
  is absurdly good value
- The data is already being collected. Exposing it costs near-zero.
- Subscribers see what the AI sees BEFORE the episode publishes.
  That time advantage is what people pay for.
- Creates a reason for premium subscriptions beyond just ad-free viewing
- Positions Protocol Pulse as an intelligence platform, not a YouTube channel

### Revenue model
- Free: Top 3 topics + sentiment + daily episode
- Operator ($19/mo): Full terminal + all topics + entity tracking + pre-episode clips
- Commander ($49/mo): Everything + API access + Telegram alerts on breaking detection
- Sovereign ($99/mo): Everything + priority Discord + direct line to PBX

### Verification
- Terminal page renders with live data
- Data updates within 10 minutes of pipeline scan
- Premium gate works (free vs paid tiers)
- Auto-refresh doesn't break or leak data

### Estimated build: 3 sessions, 8 hours total

---

## THE MISSING PIECE THAT TIES IT ALL TOGETHER

### The Intelligence Graph

Every feature above produces data. Articles, videos, tweets, terminal readings,
analytics, partner channel performance, topic velocity, entity mentions. Right now
each feature stores its data independently. The Intelligence Graph connects them.

```
                    ┌─────────────────┐
                    │ INTELLIGENCE    │
                    │ GRAPH           │
                    │ (Neo4j or JSON) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │ ENTITIES │         │ TOPICS  │         │ EPISODES│
   │          │         │         │         │         │
   │ Saylor   │◄───────►│ ETF     │◄───────►│ EP-0304 │
   │ BlackRock│         │ Mining  │         │ EP-0303 │
   │ Lyn Alden│         │ Fed     │         │ EP-0302 │
   └────┬─────┘         └────┬────┘         └────┬────┘
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │SENTIMENT│         │VELOCITY │         │ANALYTICS│
   │ per      │         │ per     │         │ per     │
   │ entity   │         │ topic   │         │ episode │
   └──────────┘         └─────────┘         └─────────┘
```

### What the graph enables
- "Show me everything Protocol Pulse has covered about BlackRock in the
  last 30 days" → instant cross-reference across videos, articles, tweets
- "Which topics have increasing velocity AND increasing positive sentiment?"
  → the pipeline auto-prioritizes these
- "Which entity mentions correlate with our highest-performing episodes?"
  → the ML loop gets vastly more powerful
- "Saylor was mentioned in 3 episodes this week. Auto-generate a Saylor
  compilation for Shorts." → content multiplication from the graph

### Why this is the ultimate moat
No other Bitcoin media operation has a knowledge graph of the entire
Bitcoin YouTube ecosystem's output. Protocol Pulse scans, transcribes,
and classifies content from 18 channels every single day. Over 6 months,
that's thousands of hours of transcribed Bitcoin content, all tagged by
entity, topic, sentiment, and performance.

That dataset is the moat. Not the video production. Not the thumbnail.
Not the voice. The accumulated, structured intelligence about what the
entire Bitcoin media ecosystem is saying, and how audiences respond to it.

### Implementation
Start simple: JSON files in `data/graph/`. Entities, topics, and episodes
as separate JSON documents with cross-references by ID. This is enough for
the first 100 episodes. If Protocol Pulse scales to thousands of episodes,
migrate to Neo4j or a proper graph database. But don't over-engineer on day one.

### Estimated build: 2 sessions, 4 hours (simple JSON graph)

---

## COMPLETE V22-V30 EXECUTION TIMELINE

```
V22 — Multi-Format Output Engine         (3 sessions, 6 hrs)
V23 — Continuation Series Engine          (2 sessions, 4 hrs)
V24 — Topic Velocity / Breaking News      (2 sessions, 4 hrs)
V25 — PBX Voice Clone Integration         (1 session, 1 hr)
V26 — Competitive Intelligence Engine     (2 sessions, 3 hrs)
V27 — Dynamic Thumbnail A/B Testing       (2 sessions, 3 hrs)
V28 — Cross-Episode Narrative Memory      (1 session, 2 hrs)
V29 — Automated Partner Outreach          (1 session, 1.5 hrs)
V30 — Pulse Terminal + Intelligence Graph (3 sessions, 8 hrs)

Total: 17 sessions, ~32.5 hours of Claude Code time
At 2 sessions per day: ~9 working days after V21 completes
```

---

## REVENUE PROJECTIONS (conservative)

### Current: $0/month from pipeline

### After V21 (sponsor rotation):
- Meanwhile affiliate: ~$200/month (1-2 signups)
- Curated Mining leads: ~$500/month (1 qualified lead)
- RNS.ID referrals: ~$300/month (1 referral)
- **Total: ~$1,000/month**

### After V30 (Pulse Terminal):
- Operator tier ($19/mo) × 200 subscribers = $3,800/month
- Commander tier ($49/mo) × 50 subscribers = $2,450/month
- Sovereign tier ($99/mo) × 10 subscribers = $990/month
- Sponsor rotation: $2,000/month (established audience)
- **Total: ~$9,240/month**

### After 6 months of compounding (intelligence graph mature):
- Terminal subscribers grow with content library
- Partner channel cross-promotion drives organic growth
- Breaking news episodes spike impressions
- Analytics loop optimizes content for maximum engagement
- **Conservative target: $15,000-25,000/month**

---

## THE RULE

Every feature in this spec serves one principle:
**The intelligence is the product. The video is just the most visible output.**

The scanning, classifying, analyzing, and connecting of information across
the entire Bitcoin media ecosystem is what no one else can replicate.
The video, the article, the tweet, the terminal — those are all just
different views into the same intelligence layer.

Build the intelligence layer right, and every output format improves
automatically. Build the outputs without the intelligence layer, and
you're just another YouTube channel.

---

*This document is the roadmap for V22-V30. It should be read alongside
MASTER_PLAN_OF_ACTION.md (V11-V21) and ARTICLE_PAGE_LAWS.md (frontend).
Together these three documents define the complete Protocol Pulse product.*
