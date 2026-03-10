# PROTOCOL PULSE MEDIA NETWORK — PRODUCTION ENGINE SPEC
# Automated Partner Channel Pipeline: Record → Edit → Clip → Distribute → Report
# Admin dashboard on protocolpulse.io/admin (drag-and-drop media management)
# Status: FOUNDATIONAL SPEC. Build after Pulse Check pipeline is locked.
# Created: 2026-03-06

---

## THE VISION

A partner records a podcast episode. They upload the raw file (or it auto-syncs
from Riverside/Zencastr/Google Drive). From that moment, EVERYTHING is automated:

1. AI-enhanced edit (noise removal, levels, intro/outro insertion)
2. 5-10 short clips auto-extracted (best moments via Whisper + scoring)
3. Branded thumbnails generated for each clip + full episode
4. Multi-platform distribution (YouTube, Spotify, Apple, RSS, Rumble)
5. Social media posts drafted (X, Instagram, TikTok captions)
6. Analytics dashboard updated in real-time
7. Monthly/quarterly report auto-generated and emailed to partner
8. Revenue tracking with automated split calculations

The partner does ONE thing: show up and talk. We handle everything else.

---

## SECTION 1: PARTNER ONBOARDING FLOW

### Step 1: Admin creates partner profile
protocolpulse.io/admin/partners/new

```json
{
  "partner_id": "bitcoin_boomers",
  "display_name": "The Bitcoin Boomers",
  "host_name": "Melissa Sands",
  "email": "sandsotime1@gmail.com",
  "channels": {
    "youtube": { "id": null, "status": "pending_creation" },
    "podcast_rss": { "feed_url": null, "status": "pending_creation" },
    "website": { "url": null, "status": "pending_creation" }
  },
  "branding": {
    "logo": null,
    "colors": { "primary": "#cc0000", "secondary": "#f8c15c" },
    "intro_audio": null,
    "outro_audio": null,
    "watermark": null
  },
  "agreement": {
    "revenue_split": { "company": 70, "partner": 30 },
    "min_episodes_per_month": 1,
    "clips_per_episode": 5,
    "effective_date": "2026-02-23",
    "status": "active"
  },
  "distribution": {
    "youtube": true,
    "spotify": true,
    "apple_podcasts": true,
    "rumble": true,
    "x_clips": true,
    "instagram_reels": true,
    "tiktok": true,
    "nostr": true
  }
}
```

### Step 2: Auto-provision infrastructure
When admin clicks "Create Partner," the system:
- Creates YouTube channel (via YouTube API, or flags for manual creation)
- Generates RSS feed (via podcast hosting — Buzzsprout/Podbean API or self-hosted)
- Creates partner page on protocolpulse.io/network/bitcoin-boomers
- Generates branded assets (intro/outro from templates + partner colors/logo)
- Creates Google Drive shared folder for raw file uploads
- Sets up webhook: new file in Drive → triggers production pipeline

---

## SECTION 2: THE PRODUCTION PIPELINE

### Trigger: Raw file lands in partner's upload folder

```
RAW UPLOAD (mp4/wav/mp3)
    │
    ▼
STEP 1: AUDIO ENHANCEMENT (Ultron GPU)
    ├── Noise reduction (RNNoise or similar)
    ├── Loudnorm to -14 LUFS
    ├── Compression (gentle, broadcast-standard)
    ├── EQ (voice clarity boost)
    └── Output: enhanced_audio.wav
    │
    ▼
STEP 2: BRANDED EDIT (FFmpeg + Remotion)
    ├── Prepend partner intro (branded, 4-6 seconds)
    ├── Append partner outro (branded, 4-6 seconds)
    ├── Add persistent lower-third watermark
    ├── Insert chapter markers from transcript
    ├── Color grade (if video — consistent look)
    └── Output: full_episode.mp4 + full_episode.mp3
    │
    ▼
STEP 3: TRANSCRIPTION (Whisper on 4090)
    ├── Full transcript with word-level timestamps
    ├── Speaker diarization (who said what)
    ├── Chapter detection (topic shifts)
    └── Output: transcript.json, chapters.json, srt file
    │
    ▼
STEP 4: CLIP EXTRACTION (Intelligent Scoring)
    ├── Score every 30-second window (0-100):
    │   ├── Emotional intensity (volume spikes, emphasis)
    │   ├── Topic relevance (Bitcoin keywords, trending topics)
    │   ├── Quote quality (complete thoughts, punchy statements)
    │   ├── Speaker clarity (no crosstalk, clean audio)
    │   └── Novelty (not similar to other clips from this episode)
    ├── Select top 5-10 moments
    ├── Extend each to nearest sentence boundary
    ├── Apply clip fade-in/fade-out
    ├── Format: 9:16 vertical (Shorts/Reels/TikTok) + 16:9 horizontal
    ├── Add captions (word-level highlighted, Hormozi style)
    ├── Add partner branding (lower third, watermark)
    └── Output: clip_01.mp4 through clip_10.mp4 (both formats)
    │
    ▼
STEP 5: THUMBNAIL GENERATION
    ├── Full episode: extract best face frame + hook text + brand colors
    ├── Each clip: extract key moment frame + quote text overlay
    ├── A/B variants: 2-3 per asset for testing
    └── Output: thumbnails/episode_thumb_v1.jpg, clip_01_thumb_v1.jpg, etc.
    │
    ▼
STEP 6: METADATA GENERATION (Claude AI)
    ├── Episode title (hook-style, max 60 chars)
    ├── Episode description (SEO-optimized, 200+ words, with chapters)
    ├── Tags (15-20 relevant tags)
    ├── Social captions: X (280 chars), Instagram (longer), TikTok (short)
    ├── Newsletter blurb (2-3 sentences for Protocol Pulse digest)
    └── Output: metadata.json
    │
    ▼
STEP 7: MULTI-PLATFORM DISTRIBUTION
    ├── YouTube: upload full episode + all clips (scheduled or immediate)
    ├── Spotify/Apple/RSS: upload audio-only episode
    ├── Rumble: upload full episode
    ├── X/Twitter: post 1-2 best clips with captions
    ├── Instagram: post 1-2 Reels
    ├── TikTok: post 1-2 clips
    ├── Nostr: post episode link + clip links
    ├── Protocol Pulse aggregator: add to site + newsletter queue
    └── Output: distribution_log.json (URLs, timestamps, status per platform)
    │
    ▼
STEP 8: ANALYTICS COLLECTION (ongoing, daily)
    ├── YouTube Analytics API: views, watch time, CTR, subscribers gained
    ├── Spotify for Podcasters API: listens, followers, skip rate
    ├── Social metrics: likes, shares, comments per clip
    ├── Website: page views on partner page
    └── Output: analytics/{partner_id}/{episode_id}/daily.json
    │
    ▼
STEP 9: AUTOMATED REPORTING
    ├── Monthly: summary email to partner with key metrics
    ├── Quarterly: detailed report (PDF) with charts, growth trends, revenue
    ├── Revenue: calculate splits, track sponsorship income
    └── Output: reports/{partner_id}/2026-Q1.pdf
```

---

## SECTION 3: ADMIN DASHBOARD (protocolpulse.io/admin)

### Authentication:
- Admin-only access (PBX, John Drew, authorized staff)
- Role-based: admin (full access), editor (production only), viewer (analytics only)

### Dashboard Pages:

#### /admin/partners
- List all partners with status badges (active, pending, paused)
- Quick stats: total episodes, total clips, monthly views, revenue
- One-click: "Create New Partner" wizard

#### /admin/partners/{id}
- Partner profile, branding assets, agreement details
- Episode list with production status (queued → processing → published)
- Analytics overview (views, growth, engagement)
- Revenue tracker (sponsorships, ad revenue, splits owed)

#### /admin/production
- **Drag-and-drop upload zone** — drop raw file, select partner, pipeline auto-starts
- Production queue: all episodes in progress with stage indicators
- Clip review: preview auto-extracted clips, approve/reject/re-extract
- Thumbnail review: preview generated thumbnails, select winners

#### /admin/distribution
- Distribution status per episode per platform
- Retry failed uploads
- Schedule future publications
- Cross-promote: one-click share any partner content on Protocol Pulse channels

#### /admin/analytics
- Network-wide dashboard: total views, subscribers, revenue across all partners
- Per-partner breakdown with comparison charts
- Content performance: which clips performed best, which topics trend
- Audience overlap analysis (Protocol Pulse viewers who also watch partners)

#### /admin/revenue
- Sponsorship tracker: deals, amounts, splits per partner
- AdSense/platform revenue per channel
- Automated quarterly statement generation
- Payment status tracking (paid/pending/overdue)

#### /admin/reports
- Auto-generated monthly/quarterly reports per partner
- One-click PDF generation with charts
- Email delivery to partner with one button

---

## SECTION 4: TECH ARCHITECTURE

### Backend (Ultron + Flask):
```
~/protocol_pulse/media_network/
  ├── models/
  │   ├── partner.py         # Partner profile, agreement, branding
  │   ├── episode.py         # Episode metadata, production state
  │   ├── clip.py            # Extracted clips with scores
  │   ├── distribution.py    # Platform upload status per asset
  │   ├── analytics.py       # Daily metrics per episode per platform
  │   └── revenue.py         # Sponsorship deals, splits, payments
  ├── pipeline/
  │   ├── audio_enhance.py   # RNNoise + loudnorm + EQ
  │   ├── branded_edit.py    # Intro/outro + watermark + chapters
  │   ├── transcriber.py     # Whisper + diarization
  │   ├── clip_extractor.py  # Intelligent moment selection + formatting
  │   ├── thumbnail_gen.py   # Face extraction + text overlay
  │   ├── metadata_gen.py    # Claude-powered titles + descriptions
  │   └── distributor.py     # Multi-platform upload orchestrator
  ├── integrations/
  │   ├── youtube_api.py     # Upload, analytics, channel management
  │   ├── spotify_api.py     # Podcast upload via Spotify for Podcasters
  │   ├── rss_manager.py     # Self-hosted RSS feed generation
  │   ├── x_api.py           # Tweet/clip posting
  │   ├── instagram_api.py   # Reels posting (via Meta Graph API)
  │   ├── tiktok_api.py      # Clip upload
  │   ├── nostr_api.py       # Note publishing
  │   └── drive_watcher.py   # Google Drive webhook for raw uploads
  ├── reports/
  │   ├── monthly_report.py  # Generate monthly summary
  │   ├── quarterly_report.py # Generate quarterly PDF with charts
  │   └── revenue_calc.py    # Automated split calculations
  └── routes/
      ├── routes_admin.py    # Admin dashboard API endpoints
      ├── routes_partners.py # Partner management CRUD
      └── routes_analytics.py # Analytics API
```

### Frontend (protocolpulse.io/admin):
- React dashboard (or Next.js page within existing Vercel app)
- Drag-and-drop file upload (direct to Ultron via presigned URL or relay)
- Real-time production progress (WebSocket updates)
- Charts: Recharts or Chart.js for analytics visualization
- PDF generation: jsPDF or server-side WeasyPrint

### Database:
- PostgreSQL (on Neon, already set up for Replit — extend schema)
- Tables: partners, episodes, clips, distributions, analytics_daily, sponsorships, payments

### Storage:
- Raw uploads: Google Drive (shared folders per partner)
- Processed media: Ultron local storage (SSD, backed up)
- Distributed assets: YouTube/Spotify/etc. host their own copies
- Thumbnails + clips: S3 or Cloudflare R2 (CDN-backed)

### Cron Jobs:
```
# Analytics collection (daily)
0 6 * * * python3 media_network/integrations/youtube_api.py collect
0 6 * * * python3 media_network/integrations/spotify_api.py collect

# Monthly report generation (1st of each month)
0 8 1 * * python3 media_network/reports/monthly_report.py --all-partners

# Quarterly report + revenue calc (1st of quarter)
0 8 1 1,4,7,10 * python3 media_network/reports/quarterly_report.py --all-partners

# Drive watcher (check for new uploads every 5 min)
*/5 * * * * python3 media_network/integrations/drive_watcher.py
```

---

## SECTION 5: WHAT WE REUSE FROM PULSE CHECK PIPELINE

The Pulse Check video pipeline already solved the hardest problems.
The Media Network Engine reuses:

| Pulse Check Component | Media Network Reuse |
|----------------------|---------------------|
| Whisper transcription | Episode transcription + clip extraction |
| Intelligent clip scorer | Best-moment extraction for shorts |
| ElevenLabs TTS | Partner intro/outro voiceover generation |
| Remotion components | Branded overlays, thumbnails, clip captions |
| FFmpeg audio chain | Loudnorm, compression, noise reduction |
| Loudnorm pipeline | Broadcast-standard audio processing |
| Sidechain ducking | Music beds under partner intros |
| manifest_builder | Episode production manifest per partner |
| qc_pipeline | Automated quality checks before distribution |

The architecture is the SAME. The difference: Pulse Check processes
80 external channels into one show. The Media Network processes
partner raw recordings into distributed content across many channels.

---

## SECTION 6: PARTNER-FACING FEATURES

### Partner Portal (protocolpulse.io/network/{partner_id}/dashboard)
Partners get a read-only dashboard showing:
- Episode list with view counts and growth
- Clip performance (which shorts did best)
- Subscriber growth chart
- Revenue earned (their split) with payment history
- Upcoming content calendar
- "Upload Raw File" button (goes to shared Drive folder)

This is the "white glove" experience that makes partners feel like
they have a full production team behind them — because they do.

### Partner Monthly Email (auto-generated):
```
Subject: Your Bitcoin Boomers Monthly Report — March 2026

Hey Mel,

Here's what happened on your channel this month:

📊 EPISODE PERFORMANCE
  - 4 episodes published
  - 22 clips distributed across 7 platforms
  - 12,400 total views (up 34% from February)

📈 GROWTH
  - YouTube: +180 subscribers (total: 1,240)
  - Podcast: +95 listeners (total: 680)
  - Most popular clip: "Why Boomers Need Bitcoin NOW" (3,200 views)

💰 REVENUE
  - Sponsorship revenue: $600
  - AdSense: $82
  - Your 30% share: $204.60
  - Payment status: Processing (due by April 15)

🎯 NEXT MONTH
  - Guest lined up: [TBD from conference access]
  - Trending topics to consider: [from intelligence pipeline]

Keep stacking. 🔶
— Protocol Pulse Media Network
```

---

## SECTION 7: IMPLEMENTATION PHASES

### Phase 1: Core Pipeline (Week 1-2)
- Partner model + database schema
- Raw upload → audio enhance → branded edit → transcribe
- Manual clip review (admin selects moments, system formats them)
- YouTube upload integration

### Phase 2: Intelligent Automation (Week 3-4)
- Auto clip extraction (scoring engine from Pulse Check)
- Auto thumbnail generation
- Auto metadata generation (Claude)
- Multi-platform distribution (Spotify, Apple, RSS, Rumble)

### Phase 3: Admin Dashboard (Week 5-6)
- React admin UI on protocolpulse.io/admin
- Drag-and-drop upload
- Production queue with status tracking
- Clip review/approve interface

### Phase 4: Analytics + Reporting (Week 7-8)
- YouTube/Spotify analytics collection
- Monthly auto-report generation
- Revenue tracking + split calculations
- Partner portal (read-only dashboard)

### Phase 5: Social Distribution (Week 9-10)
- X/Twitter clip posting
- Instagram Reels
- TikTok
- Nostr
- Cross-promotion engine

---

## SECTION 8: SCALABILITY

### Current capacity (4x 4090):
- Whisper transcription: ~17x realtime (1 hour episode = 3.5 min)
- Clip extraction: ~2 min per episode (10 clips)
- Thumbnail generation: ~30 sec per thumbnail
- Total per episode: ~15 minutes from raw to fully distributed

### At 5 partners × 4 episodes/month = 20 episodes/month:
- ~5 hours of GPU time per month
- Well within capacity (4090s are 95% idle)

### At 20 partners × 4 episodes/month = 80 episodes/month:
- ~20 hours of GPU time per month
- Still comfortable. The 40 additional 4090s coming online make this trivial.

### At 50+ partners:
- Consider dedicated worker queue (Celery + Redis)
- Parallel processing across multiple GPUs
- CDN for media delivery (Cloudflare R2)

---

*This spec turns Protocol Pulse from a content producer into a MEDIA NETWORK PLATFORM.
The competitive moat: no other Bitcoin media company offers autonomous production
+ distribution + analytics to independent creators. This is the MCN (Multi-Channel Network)
model reimagined with AI infrastructure.
Pair with: MARKETING_STRATEGY_LAWS.md, PRODUCTION_DESIGN_LAWS.md, VISUAL_DESIGN_SYSTEM.md*
