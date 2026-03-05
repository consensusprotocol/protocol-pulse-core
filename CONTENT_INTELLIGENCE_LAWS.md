# PROTOCOL PULSE — CONTENT INTELLIGENCE LAWS
# Sentiment-driven content strategy + cross-platform distribution
# Status: GOSPEL. Read alongside X_POSTING_LAWS.md and PIPELINE_LAWS.md.
# Created: 2026-03-05

---

## THE PRINCIPLE

The pipeline's scanning intelligence DRIVES content decisions across all platforms.
What Protocol Pulse publishes is determined by data, not gut feeling.
The sentiment engine sees trends 6-12 hours before the daily video publishes.
That lead time is the competitive advantage. Use it everywhere.

---

## SECTION 1: SENTIMENT-DRIVEN CONTENT DIRECTION

### How it works:
```
Channel scanner (every 6 hours)
     ↓
Transcribes 18+ channels → classifies topics → measures sentiment
     ↓
data/intelligence/daily_signals.json:
  {
    "topic_velocity": [
      {"topic": "ETF flows", "channels": 7, "sentiment": "bullish", "score": 85},
      {"topic": "mining difficulty", "channels": 4, "sentiment": "bearish", "score": 42}
    ],
    "entity_mentions": [
      {"entity": "BlackRock", "count": 14, "sentiment_shift": "+23% vs yesterday"},
      {"entity": "Saylor", "count": 9, "sentiment_shift": "+5%"}
    ],
    "breaking_threshold": false,
    "recommended_topics": ["ETF flows", "BlackRock accumulation"]
  }
     ↓
Content decisions for ALL platforms reference this file:
  - Daily video: clips selected from highest-velocity topics
  - X posts: morning intelligence tweet references top signal
  - Articles: daily brief article covers recommended_topics
  - Substack: weekly deep-dive into the week's dominant narrative
  - X Articles: 1-3/day on the most significant signals
```

### The Rule:
If the sentiment engine flags a topic with velocity >= 4 channels AND
sentiment score >= 70, that topic MUST appear in the next content cycle.
The data leads. Content follows. Never the reverse.

### What to post based on sentiment signals:

| Signal | X Post | Article | Video |
|--------|--------|---------|-------|
| Topic velocity spike (4+ channels, 3hrs) | Immediate tweet with data | Breaking brief within 2 hours | Emergency episode if >= 6 channels |
| Entity mention surge (+50% vs yesterday) | Commentary tweet | Analysis article | Include in next daily episode |
| Sentiment shift (bullish → bearish) | Thread analyzing the shift | Deep-dive article | Lead segment in next episode |
| New topic emergence (first time seen) | Introductory tweet | Explainer article | Cold open hook |
| Steady topic (no change) | Skip or brief mention | Only if new angle | Background mention only |

---

## SECTION 2: CROSS-PLATFORM DISTRIBUTION PIPELINE

### One intelligence scan → 8 distribution formats:

```
Pipeline Intelligence Scan
     ↓
     ├── 1. Daily Video (YouTube) — 12-15 min, 5 clips + narration
     ├── 2. YouTube Shorts — 3-5 clips, 30-60s each, vertical
     ├── 3. Podcast (Fountain) — Audio-only extract from video
     ├── 4. protocolpulse.io Article — Written brief from script
     ├── 5. X Post — Morning intelligence, episode promo, commentary
     ├── 6. X Article — 1-3/day, long-form analysis (800-1500 words)
     ├── 7. Substack — Weekly deep-dive (2000-3000 words)
     ├── 8. Nostr — Intelligence note + episode link
```

### Platform-Specific Rules:

#### YouTube (Video + Shorts):
- Thumbnail: face + data + red accent (see PIPELINE_LAWS Section 19)
- Title: Lead with the hook, under 60 chars. Include "Bitcoin" for search.
- Description: Summary → timestamps → affiliate links → social links
- Tags: 15-20, mix of broad ("Bitcoin") and specific ("ETF flows March 2026")
- Upload timing: 7-8 AM ET (catch morning East Coast + pre-market)
- Shorts: Vertical 1080x1920, burned-in captions, hook in first 2 seconds

#### X (Posts + Articles):
- See X_POSTING_LAWS.md for full rules
- X Articles: formatted with proper header image (1600x900), paragraph breaks,
  bold key phrases, embedded charts/images
- X Articles do NOT get suppressed like external links — they're native content
- Publish 1-3 X Articles per day, ONLY the top-performing intelligence
- Selection criteria: topic velocity >= 3 channels OR entity surge >= 30%
- X Articles auto-generated from protocolpulse.io articles with formatting adapted
  for X's article editor (shorter paragraphs, more subheadings, data callouts)

#### Substack:
- Weekly frequency: "The Sovereign Signal" — Sunday evening publish
- 2000-3000 words, deep narrative, connects the week's dots
- NOT a recap of daily briefs. New synthesis and analysis.
- Free tier: summary + 1 key insight
- Paid tier: full analysis + data charts + prediction
- Cross-link to protocolpulse.io for daily content

#### Nostr:
- See X_POSTING_LAWS.md Section 5
- NIP-23 long-form notes for articles
- NIP-01 text notes for quick intelligence
- Zap-worthy content: provide genuine value, not promotion
- Relay list in profile, cross-post to 5+ relays

#### Fountain (Podcast):
- Audio extract from daily video (strip visual-only segments)
- Episode title matches YouTube title
- Show notes: timestamps + key quotes + links
- RSS auto-update within 15 minutes of video upload

---

## SECTION 3: ARTICLE SELECTION FOR X ARTICLES + SUBSTACK

### Daily X Article Selection (1-3 per day):
From the day's protocolpulse.io articles, select based on:
1. **Topic velocity score** (highest velocity = publish first)
2. **Uniqueness** (does this add insight no one else has?)
3. **Data density** (articles with specific numbers/metrics perform best)
4. **Timeliness** (breaking > developing > evergreen)

### Formatting for X Articles:
- Header image: 1600x900, Protocol Pulse branded template with topic keyword
- Title: Under 50 chars, lead with the insight not the topic
  GOOD: "RIAs Are Front-Running the Next Wave"
  BAD: "Bitcoin ETF Update March 5 2026"
- Body: 800-1500 words, short paragraphs (2-3 sentences max)
- Bold key data points: **"Hash rate hit 1,056 EH/s"**
- Embed 2-3 charts or data visuals
- End with: "Follow @ProtocolPulse for daily Bitcoin intelligence"
- No external links in the article body (keep readers on X)

### Weekly Substack Selection:
- Review the week's top 5 signals by velocity and engagement
- Identify the connecting narrative (what story ties them together?)
- Write original synthesis, not a compilation of daily briefs
- Include: 1 prediction for next week (with conviction level: low/medium/high)
- Publish Sunday 6 PM ET (high email open rates Sunday evening)

---

## SECTION 4: PLATFORM TOS MONITORING (AUTO-UPDATING)

### The Problem:
Platform algorithms and TOS change without notice. What works today may be
penalized tomorrow. Protocol Pulse must detect and adapt.

### Monitoring Sources:
- **X**: @XEng, @elonmusk, X Developer Blog, X Business blog
- **YouTube**: YouTube Creator Blog, YouTube Help forums, @TeamYouTube
- **Substack**: Substack Blog, community forums
- **Nostr**: NIP proposals (GitHub), relay operator discussions

### Automated Detection:
Weekly cron job (utils/platform_monitor.py):
1. Scrape platform blogs/announcement pages for new posts
2. Claude analyzes: "Does this affect our posting strategy?"
3. If yes: generate a recommended update to the relevant LAWS doc
4. Alert PBX via Telegram: "Platform change detected: [summary]. Recommended update: [change]."
5. PBX approves → update committed to gospel doc

### Manual Detection:
If Protocol Pulse engagement drops >30% for 2 consecutive weeks:
1. Trigger platform investigation
2. Check all monitoring sources for algorithm changes
3. A/B test posting variations to identify what changed
4. Update relevant LAWS doc with findings

### Known Platform Preferences (as of March 2026):

**X Algorithm Preferences:**
- Native media (images, video uploaded directly)
- Long dwell time (people spending time reading your post)
- Bookmarks (strongest signal)
- Replies and conversation depth
- Consistent posting (daily active accounts)
- Threads (if first tweet hooks well)
- X Articles (native long-form, not suppressed)
- Spaces participation (audio feature engagement)

**X Algorithm Penalties:**
- External outbound links (YouTube, websites)
- Engagement bait language
- Excessive hashtags (>2)
- Identical content posted by multiple accounts
- Rapid-fire posting (>10 in an hour)
- New accounts with sudden high volume

**YouTube Algorithm Preferences:**
- Click-through rate (thumbnail + title = most important)
- Watch time (total minutes watched)
- Average view duration (% of video watched)
- Session time (do viewers watch another video after yours?)
- Upload consistency (same time, same days)
- End screens and cards that drive internal navigation
- Community posts between uploads

**YouTube Algorithm Penalties:**
- Misleading thumbnails (high CTR, low watch time = death)
- Inconsistent upload schedule
- Excessive tags (looks spammy)
- Re-uploaded content (duplicate detection)
- Controversial content without context (demonetization risk)

**Substack Preferences:**
- Email open rates (primary distribution mechanism)
- Comment engagement
- Subscriber growth rate
- Cross-referencing with other Substack publications
- Notes feature (Substack's social layer)

**Nostr Characteristics:**
- No algorithm. Chronological relay-based distribution.
- Zaps (Lightning tips) as engagement signal
- Relay selection matters (popular relays = more reach)
- NIP compliance for discoverability
- No penalties for links, length, frequency

---

## SECTION 5: CONTENT QUALITY GATES (PER PLATFORM)

Before publishing to ANY platform, the content must pass:

### X Posts:
- [ ] Under 280 chars (ideally under 120)
- [ ] No external links in body
- [ ] Contains specific data or insight (not vague)
- [ ] Matches brand voice (intelligence, not hype)
- [ ] No banned phrases (see X_POSTING_LAWS Section 4)

### X Articles:
- [ ] 800-1500 words
- [ ] Header image at 1600x900
- [ ] At least 2 data points with specific numbers
- [ ] Short paragraphs (2-3 sentences)
- [ ] No external links in body
- [ ] Ends with CTA to follow

### YouTube:
- [ ] Quality score >= 85 (from quality_gate.py)
- [ ] Thumbnail generated with face + data hook
- [ ] Title under 60 chars with "Bitcoin" keyword
- [ ] Description has timestamps, affiliates, social links
- [ ] Video is 1920x1080, >5Mbps, <0.03s AV sync

### Substack:
- [ ] 2000-3000 words
- [ ] Original synthesis (not recap of daily briefs)
- [ ] At least 1 prediction with conviction level
- [ ] Free preview available (first 500 words)
- [ ] Cross-links to protocolpulse.io

### Nostr:
- [ ] Rewritten for Nostr audience (more technical, more cypherpunk)
- [ ] NIP-23 format for long-form
- [ ] Published to 5+ relays
- [ ] Includes npub for attribution

---

*This document defines how intelligence drives content across all platforms.
Pair with: X_POSTING_LAWS.md, PIPELINE_LAWS.md, ARTICLE_PAGE_LAWS.md.
Updates quarterly with platform monitoring data.*


---

## ADDENDUM A: PROTOCOL PULSE EDITORIAL VOICE & BRAND ETHOS

### Core Identity:
Protocol Pulse is a **Bitcoin self-custody, sovereign individual** brand.
"Not your keys, not your coins" is the philosophical bedrock.
We serve transactors, not tourists. Bitcoiners, not crypto speculators.

### The ETF Nuance:
Protocol Pulse does NOT cheerleader ETFs. We cover them because they're market-moving.
But the editorial angle is ALWAYS from the sovereign Bitcoiner's perspective:

**The rule:** When covering tradfi Bitcoin instruments (ETFs, futures, MSTR, etc.):
- Lead with what it means for Bitcoin the NETWORK, not Bitcoin the ASSET
- Frame it as: "Tradfi is validating what we already know"
- Acknowledge the reality: these instruments exist, capital is flowing, ignore at your peril
- The sovereign angle: "If tradfi is going to leverage Bitcoin, it may as well be
  Bitcoiners getting double exposure — borrowing against holdings, milking the
  fiat system, funneling gains back into real Bitcoin"
- NEVER frame ETFs as "the way to buy Bitcoin." Self-custody is always the recommendation.
- NEVER sound anti-tradfi in a way that alienates sponsors or institutional audience.
  The tone is: "We understand the game. We play it better."
- Subtle, not preachy. The audience should feel like insiders, not lectured.

**Topic balance rule:**
If ETF/tradfi topics exceed 40% of a week's content, the system must auto-balance:
- Force at least 2 mining/hashrate segments per week
- Force at least 1 Lightning/self-custody segment per week
- Force at least 1 cypherpunk/privacy segment per week
- The sentiment engine's topic_velocity is advisory, not mandatory.
  Brand identity overrides pure velocity when necessary.

### Voice Characteristics:
- **Authoritative but not arrogant.** We know our stuff. We don't need to prove it.
- **Insider, not outsider.** "Here's what's actually happening" not "Let me explain crypto."
- **Data-first, opinion-second.** Lead with the number. Then interpret.
- **Cypherpunk at heart, professional in delivery.** We believe in sovereignty
  but we present it in a way that Fortune 500 executives take seriously.
- **Never salesy about sponsors.** Affiliate reads sound like genuine recommendations
  from someone who uses the product, not ad copy.
- **Humor is dry and knowing.** We don't try to be funny. We observe absurdity.

### Content Pillars (in order of brand priority):
1. **Network Security** — Hash rate, difficulty, mining economics
2. **Sovereignty** — Self-custody, privacy, censorship resistance
3. **Macro** — Bitcoin's role in global monetary policy, fiat collapse thesis
4. **Institutional** — ETFs, corporate treasuries, sovereign wealth funds
5. **Lightning/Layer 2** — Payments, scaling, real-world adoption
6. **Culture** — Cypherpunk philosophy, freedom technology, community

If the sentiment engine only surfaces Pillar 4 (institutional) topics for 3
consecutive days, manually inject Pillars 1-3 content to maintain brand balance.

### Sponsor Sensitivity:
- Meanwhile (Bitcoin life insurance): Aligned. Self-custody philosophy. Promote freely.
- Curated Mining: Aligned. Mining = network security. Promote freely.
- RNS.ID (Palau Digital Residency): Sovereignty-adjacent. Promote as freedom tool.
- Future sponsors: Must align with at least one content pillar.
  No shitcoin sponsors. No centralized exchange sponsors (unless they prove
  proof-of-reserves and self-custody withdrawal support). No "web3" sponsors.

---

## ADDENDUM B: X ARTICLES + SUBSTACK FREQUENCY UPDATE

### X Articles: 1 per week (not 1-3 per day as previously stated)
- Published: Wednesday (mid-week, high engagement day on X)
- Selecting the single best intelligence piece from the week so far
- Can be the SAME article as the Substack piece, reformatted for X
- Header image: 1600x900, Protocol Pulse branded template
- Platform-specific formatting: shorter paragraphs than Substack, more bold callouts

### Substack: 1 per week
- Published: Sunday 6PM ET ("The Sovereign Signal")
- 2000-3000 words, original synthesis
- Header image: 1200x630 (Substack optimal)
- Can share core analysis with X Article but with expanded depth

### Same Article, Two Formats:
When the X Article and Substack cover the same topic:
- Substack version: Full depth, 2500+ words, all data, prediction
- X Article version: Condensed, 1000-1200 words, punchier, more bold text
- Different header images (platform-specific dimensions)
- Different opening hooks (X is more immediate, Substack more narrative)
- Both link to protocolpulse.io for daily content


---

## ADDENDUM C: BITCOIN NODE MONITORING — "THE NODE PULSE"

### Why this matters to the brand:
Protocol Pulse's #1 content pillar is Network Security. Node count dropped
from ~200K (2017) to ~100K (2026). This is the single most important metric
for Bitcoin's decentralization health. Mining centralization + node decline +
ETF hypothecation are the three existential threats. Monitoring and celebrating
new nodes directly serves the sovereignty mission.

### Data Source:
- Bitnodes.io API: https://bitnodes.io/api/v1/snapshots/
- Polls every 15 minutes
- Compares current snapshot to previous: new IPs = new nodes
- Also tracks: total reachable nodes, geographic distribution, client versions

### Site Integration:
- protocolpulse.io sidebar widget: "NODE PULSE" live counter
  - Total reachable nodes (large number, updated every 15 min)
  - Net change today: +12 / -5 (green/red)
  - "Run a node. Secure the network." CTA linking to guide
  - Sparkline chart: last 30 days of node count

### Auto-Tweet on Milestone Events:
Trigger an automated X post when:
1. **Net positive day**: More nodes came online than went offline
   Tweet: "Network grew today. {total} nodes securing the chain. [sparkline emoji] +{net_new}"
2. **New round number**: Total crosses 100K, 105K, 110K, etc.
   Tweet: "Bitcoin just crossed {milestone} reachable nodes. Decentralization is not a spectator sport."
3. **Geographic milestone**: New country appears in the node map
   Tweet: "{country} just came online. Bitcoin's network now spans {count} countries."
4. **Weekly summary**: Every Monday
   Tweet: "NODE PULSE: {total} nodes this week ({change} vs last). Top growth: {country_1}, {country_2}."

### Tweet Voice for Node Posts:
- Celebratory but not cheesy. Factual with subtle pride.
- NEVER "OMG new node!" energy. Always measured, authoritative.
- Data first: the number, then the implication.
- Dry humor when appropriate: "Another sovereign individual chose violence today. Node #{total}."
- Vary the format. Don't repeat the same template.

### Implementation:
- utils/node_monitor.py: Bitnodes API poller, snapshot diffing, milestone detection
- Cron: every 15 minutes on Ultron
- data/node_snapshots/: JSON files per snapshot
- Telegram alert on milestones (reuse V18 Telegram infrastructure)
- X auto-post on milestones (reuse X posting pipeline, human review first 50 posts)

### Brand Integration:
This feature reinforces Protocol Pulse as THE network health authority.
Nobody else auto-tweets node milestones with context and data.
Over time, the Node Pulse becomes a cited source — "According to Protocol Pulse's
node tracker, Bitcoin's network grew by 3% this quarter."

### Decentralization Dashboard (future, post-V30):
Expand to a full /nodes page on protocolpulse.io:
- Live map of reachable nodes by geography
- Client version distribution (Bitcoin Core vs others)
- Historical trend charts (node count over years)
- Mining pool distribution (hashrate centralization risk)
- ETF holdings as % of total supply (hypothecation risk metric)
- Combined "Decentralization Health Score" (0-100)

This positions Protocol Pulse as the definitive source for Bitcoin network health.
