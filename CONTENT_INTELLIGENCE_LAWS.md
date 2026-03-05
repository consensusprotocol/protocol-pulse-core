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
