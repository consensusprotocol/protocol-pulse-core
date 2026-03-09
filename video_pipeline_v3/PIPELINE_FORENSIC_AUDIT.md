# PROTOCOL PULSE VIDEO PIPELINE — FORENSIC AUDIT
# Senior Developer Level. No assumptions. Ground truth only.
# Generated: 2026-03-04 | Auditor: Claude (pre-V11 freeze)

---

## EXECUTIVE SUMMARY

The pipeline is more capable than it feels from the output quality. The core
architecture is sound. The gaps are specific and fixable. The main failure mode
is not broken code — it is assumptions baked into prompts and configs that
contradict each other. This audit maps every gap, every assumption, every
missing piece, and proposes a laws framework that guarantees reproducible results.

---

## PART 1: WHAT ACTUALLY EXISTS (verified from source)

### 1.1 File Inventory (5,783 lines total across 21 Python files)

| File | Lines | Status | Purpose |
|------|-------|--------|---------|
| daily_producer.py | 421 | WORKING | Main orchestrator — 12-step pipeline |
| assembler.py | 1,094 | WORKING* | FFmpeg assembly engine |
| channel_scanner.py | 299 | WORKING | yt-dlp + Whisper transcript engine |
| clip_selector.py | 210 | WORKING | Claude-powered clip selection |
| clip_extractor.py | 352 | WORKING* | yt-dlp clip downloader + sync fix |
| script_writer.py | 239 | WORKING | Claude dialogue generator |
| tts_engine.py | 313 | WORKING | ElevenLabs dual-host TTS |
| dual_host_tts.py | 334 | WORKING | Audio generation controller |
| music.py | 96 | PARTIAL | Only handles pp_background.mp3 — Suno library NOT wired |
| thumbnail_gen.py | 226 | WORKING | PIL-based thumbnail generator |
| shorts_cutter.py | 344 | WORKING* | Shorts generation |
| channel_scanner.py | 299 | WORKING | Whisper transcription |
| chapters.py | 175 | WORKING | YouTube chapters |
| podcast_feed.py | 139 | WORKING | MP3 extraction + RSS |
| newsletter_embed.py | 156 | WORKING | HTML newsletter |
| visual_fetcher.py | 660 | UNKNOWN | Large file — likely social/image fetching |
| clip_fetcher.py | 329 | UNKNOWN | Duplicate of clip_extractor? |
| daily_run.py | 123 | UNKNOWN | Cron wrapper? |
| regression_test.sh | bash | WORKING | 11-section validation |
| channels.yaml | config | WORKING | 11 Bitcoin + 7 mainstream channels |

*WORKING with known bugs documented below

### 1.2 Channel Coverage (verified in channels.yaml)

**Bitcoin-native channels (priority 1-3):**
Bitcoin Magazine, Simply Bitcoin, What Bitcoin Did, TFTC, Preston Pysh,
The Bitcoin Layer, Blockworks, Natalie Brunell, Andreas Antonopoulos,
Robert Breedlove, Unchained

**Mainstream (keyword-filtered):**
Joe Rogan, Lex Fridman, Patrick Bet-David, Tucker Carlson,
All-In Podcast, Megyn Kelly, JRE Clips

CONFIRMED WORKING: yt-dlp channel scan, Whisper GPU transcription (CUDA float16),
transcript caching by video_id, 48h window with 7-day fallback.

### 1.3 The 12-Step Pipeline (verified working flow)

```
Step 1:  BTC price (mempool.space API, $97k fallback)
Step 2:  Channel scan (yt-dlp + faster-whisper GPU)
Step 3:  Clip selection (Claude claude-sonnet-4-6)
Step 4:  Clip extraction (yt-dlp sections + AV sync fix)
Step 4b: Mood classification + music selection
Step 5:  Script generation (Claude claude-sonnet-4-6)
Step 6:  TTS generation (ElevenLabs dual host)
Step 7:  Video assembly (FFmpeg)
Step 8:  Shorts (avatar pipeline)
Step 9:  Thumbnail (PIL)
Step 10: Chapters (timestamp-based)
Step 11: Podcast MP3 + newsletter HTML
Step 12: Verify (ffprobe validation)
```

---

## PART 2: CONFIRMED BUGS (do not assume fixed unless proven in log)

### BUG-001: Clip Premature Cutoff (CRITICAL — still occurring in V10)
**Where:** `clip_extractor.py` line ~132 — padded_end calculation
**Root cause:** `end_seconds + 3` padding is insufficient. Whisper timestamps
are approximate (±2-5 seconds off). When Claude selects end_seconds=45 but
the speaker's sentence actually ends at second 48, the 3-second pad is used
up just catching up to the real end, leaving zero buffer.
**Fix needed:** Increase pad to 6-8 seconds on end. Add silence detection
to find a natural pause AFTER the padded_end before cutting.
**Verification:** Log must show "trimmed at natural pause, not hard cutoff"

### BUG-002: Same-Channel Duplicate Clips (CONFIRMED in V10 — two Natalie Brunell)
**Where:** `clip_selector.py` SELECTION_PROMPT — rule says "NEVER select more
than 1 clip from same video" but does NOT enforce "max 1 clip per channel."
**Root cause:** The rule "vary the source" is advisory to the LLM, not enforced
in code. Claude can and does select 2 clips from the same channel.
**Fix needed:** Post-selection validation in `select_clips()`:
```python
seen_channels = {}
for clip in clean_clips:
    ch = clip.get("channel", "")
    if ch in seen_channels:
        logger.warning(f"DUPLICATE CHANNEL: {ch} — keeping higher ranked clip")
        # Keep lower rank number (= more important)
        if clip["rank"] < seen_channels[ch]["rank"]:
            clean_clips.remove(seen_channels[ch])
            seen_channels[ch] = clip
        else:
            clean_clips.remove(clip)
    else:
        seen_channels[ch] = clip
```

### BUG-003: Transition Colors Still Blue (CONFIRMED in V10 screenshot)
**Where:** Glitch transition is a Remotion component or separate FFmpeg filter
**Root cause:** Remotion GlitchTransition.tsx was built with blue palette.
Brand color pass in assembler.py did not reach Remotion components.
**Fix needed:** Find GlitchTransition.tsx in remotion/src/compositions/ and
replace all blue/cyan values with CC0000/880000/FFFFFF

### BUG-004: Social Segment Shows Plain Text Not Tweet Cards (CONFIRMED)
**Where:** `assembler.py` — make_clip_visual() / social segment rendering
**Root cause:** `make_social_card_visual()` was specced but never implemented.
Social segment falls back to drawtext overlay on plain background.
**Fix needed:** Implement tweet card visual (see V10 fix doc). This is cosmetic
but high impact — real screenshot-style cards with red border are significantly
more engaging.

### BUG-005: Mainstream Channels Not Actually Filtered
**Where:** `channel_scanner.py` — `filter_keywords` in channels.yaml
**Root cause:** The `filter_keywords` field exists in channels.yaml for
mainstream channels, BUT `scan_channel()` does not read or apply this field.
It scans all videos regardless of keywords.
**Consequence:** Joe Rogan episodes about comedy or hunting could be transcribed
and potentially selected as Bitcoin content by Claude.
**Fix needed:** In `scan_channel()`, check if channel config has `filter_keywords`.
If yes, filter `title.lower()` against keyword list before including video.

### BUG-006: music.py Only References pp_background.mp3 — Suno Library Not Used
**Where:** `music.py` — hardcoded BG_MUSIC path
**Root cause:** `music.py` has fixed paths (pp_background, pp_intro, pp_outro).
The mood-based Suno library selection lives in `daily_producer.py` as a local
function that calls `assembler.assemble_episode()` with `music_bed` param.
But `music.py`'s `mix_tts_with_music()` still uses BG_MUSIC hardcoded path.
The Suno library IS being passed to assembler but only if pp_background.mp3
exists does the fallback kick in correctly. Need to verify actual audio bed used.

### BUG-007: social_posts in Script Writer Is Hardcoded Placeholder
**Where:** `script_writer.py` line ~180
```python
social_posts = "Bitcoin Twitter is reacting to today's price action. Nostr devs are building..."
```
This is a static string. No live tweet data is ever fetched or injected.
The "WHAT THE BITCOIN INTERNET IS SAYING" segment is generated from imagination,
not actual tweets. This is a significant gap — the social segment has no signal.

### BUG-008: visual_fetcher.py (660 lines) — Unclear Integration
**Where:** `visual_fetcher.py` — purpose unknown from filename alone
**Risk:** 660 lines of code with unknown integration status. Could be broken,
could be unused, could be essential. Needs audit.

### BUG-009: clip_fetcher.py vs clip_extractor.py — Possible Duplication
**Where:** Both exist at 329 and 352 lines. daily_producer imports clip_extractor.
**Risk:** clip_fetcher.py may be dead code or an older version with different behavior.

---

## PART 3: WHAT IS MISSING (features assumed to exist that do not)

### MISSING-001: Real Tweet/Nostr Data Injection
The social segment generates from placeholder text. No Twitter API, no Nostr
relay scraping, no real-time social signal. The segment is pure fabrication.
**Impact:** High. This segment is shown on screen. Text is invented.
**Required:** Either X API integration OR a curated daily tweet input file
that PBX or an operator reviews and provides.

### MISSING-002: Feature Flags System
`config/feature_flags.json` does not exist. Every feature is always on.
No way to disable a broken feature without editing code.
**Impact:** Medium. Code is fragile because there's no kill switch.
**Required:** Create config/feature_flags.json with all toggles.

### MISSING-003: YouTube Analytics Feedback Loop
Zero analytics integration. The pipeline does not know:
- Which episodes got most watch time
- Which clip sources perform best
- Which hosts' segments get skipped
- What thumbnail styles drive CTR
- Which topics trend across episodes
**Impact:** High for growth. Pipeline is blind to what works.
**Required:** YouTube Data API v3 integration (API key exists in Replit secrets).

### MISSING-004: Self-Analysis / Machine Learning Loop
No mechanism for the pipeline to learn from its own output.
No performance logging that feeds back into clip selection or script tone.
**Required:** Analytics ingestion → preference weighting in SELECTION_PROMPT.

### MISSING-005: Tweet Card Visuals
Specced in V10, not implemented. Social segment shows plain drawtext.

### MISSING-006: Actual X/Nostr Post Screenshot Capture
PBX wants real screenshot-style post images in the social segment.
No screenshot capture tool exists in the pipeline.
**Options:** Playwright headless browser screenshot, or Twitter card API,
or manual curation workflow.

### MISSING-007: Per-Episode Performance Database
No SQLite or JSON database storing episode metadata, performance metrics,
channel scores, clip success rates. Everything is ephemeral per-run.

### MISSING-008: YouTube Auto-Upload
pipeline produces the video but does not upload it. Manual upload required.
YouTube Data API v3 integration is missing (token not set up).

### MISSING-009: Telegram/Alerting on Failure
No push notification when pipeline fails at 3am.

### MISSING-010: Fast Test Mode (--fast-test)
`--test` mode reduces clips to 2 but still does full scan + full render.
No `--fast-test` that skips scan entirely and renders in 3 minutes.

---

## PART 4: WHAT NEEDS REFINEMENT (works but not well enough)

### REFINE-001: Clip End Padding (3s → 8s + silence detection)
### REFINE-002: Whisper Model (tiny in test → base in prod → large-v3 available)
### REFINE-003: Transition sound — great, but needs red not blue
### REFINE-004: Voice — Gigi too childish. Need Nicole/Sarah (mid-20s confident)
### REFINE-005: Social segment card design — needs tweet card with border
### REFINE-006: Thumbnail — needs human face integration for CTR (proven in YouTube data)
### REFINE-007: Channel deduplication — max 1 clip per channel enforced in code not just prompt
### REFINE-008: Script tone — "Jessica" and "Chris" need personas with backstory in prompt
### REFINE-009: Cold open — needs to be the absolute most shocking/interesting moment
### REFINE-010: Segment length balance — some episodes are clip-heavy, others narration-heavy

---

## PART 5: THE MASTER LAWS FOR V11-V20

### LAW CATEGORY A: DATA INTEGRITY

**A1 — No invented data**
If real data is unavailable, show nothing. Never fabricate tweet content,
clip quotes, or analytics. Placeholder text is banned from the social segment.
If no real tweets exist, skip the social segment entirely.

**A2 — Source diversity enforced in code**
Max 1 clip per channel, enforced post-selection with deduplication code.
The LLM prompt is advisory. Python code is the law.

**A3 — Ad read double gate**
Gate 1: LLM prompt instructs avoidance.
Gate 2: `contains_ad_read()` called on every selected clip's transcript range.
Both gates required. Either gate alone is insufficient.

**A4 — Clip end buffer is 8 seconds minimum**
Whisper timestamps are ±5s. Every clip end gets 8s of padding minimum.
Silence detection finds natural pause within that window.
Hard cutoff mid-sentence is a pipeline failure, not acceptable output.

### LAW CATEGORY B: VISUAL CONSISTENCY

**B1 — Brand color enforcement**
Before every commit: `grep -rn "00D4FF\|7B2FFF\|3388FF" *.py remotion/` must
return zero results. If any found, commit blocked.

**B2 — All Remotion components use BRAND constants**
GlitchTransition.tsx, WaveformVisualizer.tsx, TitleCard.tsx — all import
a shared `brand.ts` constants file. No hardcoded hex values anywhere.

**B3 — Waveform is bottom-third only**
Max height: 160px. Max width: 960px. Centered. Below the fold.
Full-screen waveform is banned.

**B4 — Resolution lock**
1920x1080 for all episode parts. 1080x1920 for all shorts.
Mixed resolution in a single concat is a pipeline failure.

### LAW CATEGORY C: AUDIO/VOICE

**C1 — AV sync validated at packet level after every clip extract**
`check_av_sync()` uses `ffprobe -show_packets`. Container header
`start_time` is NOT a valid sync measurement. Packet DTS is.
Any clip with offset > 0.05s after fix must re-encode with nuclear option.

**C2 — No loudnorm in clip visual pipeline**
`make_clip_visual()` uses `asetpts=PTS-STARTPTS,volume=1.0` not `loudnorm`.
loudnorm adds 200ms latency and re-introduces sync drift.

**C3 — Voice is mid-20s American female for host 1**
Nicole (`piTKgcLEGmPE4e6mEKli`) or Sarah (`EXAVITQu4vr4xnSDxMaL`) are targets.
Gigi is banned — too childish. Jessica (cgSgsp) is banned — British and old.
Voice settings: stability 0.40, similarity_boost 0.80, style 0.20.

**C4 — Music bed at -18dB to -22dB**
Never overpowers narration. Measured in final mix.

### LAW CATEGORY D: SELF-LEARNING

**D1 — Every episode writes a performance_seed.json**
After upload, the pipeline checks YouTube Analytics API for:
- avg_view_duration, ctr, impressions, likes, comments
for the previous episode and stores it in `data/performance/`.

**D2 — Top-performing channels get priority weighting**
Weekly cron re-scores channels.yaml priority based on:
- Which channel's clips correlated with highest watch time
- Which topics had highest CTR
High-performing channels get priority bumped. Consistently low ones get dropped.

**D3 — Script prompt evolves with data**
Quarterly (or after 20 episodes): run an analysis pass that compares
episode analytics against script characteristics (setup length, tone words,
cold open style) and updates SCRIPT_PROMPT with what the data shows.

**D4 — Episode quality score**
After each render, compute a quality score (0-100) based on:
- AV sync pass (each clip in sync = +10)
- No premature cutoffs (each clean clip end = +5)
- Channel diversity (all different channels = +20)
- Social segment has real data = +10
- Thumbnail has face = +10
- Music present = +10
- Regression pass = +25
Log this score per episode. Target: 85+ before shipping.

### LAW CATEGORY E: PROCESS

**E1 — One Claude Code session at a time on pipeline repo**
v9fix, v10fix, twitter-study can coexist.
But only one session writes to video_pipeline_v3/ at a time.

**E2 — Regression test before every commit**
`bash regression_test.sh` must show 0 FAILs.
Commit message must include: `regression: X/Y PASS`

**E3 — New features start behind feature flags**
`config/feature_flags.json` must exist before V11 starts.
Every new capability starts as `false`. Flip to `true` only after isolated test.

**E4 — Never claim done without proof**
"Done" = log output proves it. AV sync "done" = log shows offsets.
Brand colors "done" = grep shows zero banned colors.
Voice changed "done" = voice_id in tts_engine.py matches target ID.

**E5 — No parallel feature builds**
Fix one thing. Verify it. Commit. Then fix the next thing.
V11 = voice fix only. Verified. Then V12 = tweet cards. Verified. Etc.

---

## PART 6: RECOMMENDED V11-V20 SEQUENCE

### V11 — VOICE + CHANNEL DEDUP (one session, ~30 min)
Fixes: BUG-003 (Gigi → Nicole/Sarah), BUG-002 (channel dedup in code)
Verify: voice sounds right (manual listen), no duplicate channels in output
Commit: `fix: V11 — Nicole voice, channel dedup enforced`

### V12 — CLIP PADDING + SILENCE DETECTION (one session, ~45 min)
Fixes: BUG-001 (premature cutoffs)
Verify: log shows "trimmed at natural pause" for every clip
Commit: `fix: V12 — 8s clip padding + silence detection trim`

### V13 — TRANSITION RED + FEATURE FLAGS (one session, ~30 min)
Fixes: BUG-003 (blue transitions), MISSING-002 (feature flags)
Build: config/feature_flags.json, update GlitchTransition.tsx colors
Commit: `feat: V13 — red transitions, feature flags system`

### V14 — REAL SOCIAL DATA (one session, ~2 hours)
Fixes: BUG-007 (fake social posts), MISSING-001 (no real tweet data)
Build: Either X API minimal integration OR curated tweet input file workflow
Verify: social segment shows real post content
Commit: `feat: V14 — real social data in segment`

### V15 — TWEET CARD VISUALS (one session, ~45 min)
Fixes: BUG-004, MISSING-005
Build: make_social_card_visual() in assembler.py
Verify: screenshot shows styled red-border card, not plain text
Commit: `feat: V15 — tweet card visual design`

### V16 — YOUTUBE AUTO-UPLOAD (one session, ~2 hours)
Builds: YouTube Data API v3 OAuth + upload endpoint
MISSING-008
Verify: test upload to unlisted video, confirm metadata correct
Commit: `feat: V16 — YouTube auto-upload`

### V17 — ANALYTICS FEEDBACK LOOP (one session, ~2 hours)
Builds: YouTube Analytics API pull, performance_seed.json, channel scoring
MISSING-003, MISSING-007, LAW D1, D2
Commit: `feat: V17 — YouTube analytics feedback loop`

### V18 — MAINSTREAM CHANNEL KEYWORD FILTER (30 min)
Fixes: BUG-005 — apply filter_keywords to scan_channel()
Commit: `fix: V18 — keyword filter for mainstream channels`

### V19 — TELEGRAM ALERTS + FAST TEST MODE (30 min)
Builds: MISSING-009, MISSING-010
Commit: `feat: V19 — failure alerts + fast test mode`

### V20 — SELF-ANALYSIS PASS + QUALITY SCORE (one session, ~2 hours)
Builds: LAW D3, D4 — quality score per episode, script prompt evolution
Commit: `feat: V20 — self-analysis, quality score, prompt evolution`

---

## PART 7: ADDITIONAL ELEMENTS PBX SHOULD ADD

### 7.1 Clip Approval Workflow (optional but high-value)
Before final render, write `selections.json` and send a Telegram message:
"Today's clips: [1] Saylor on sovereign wealth funds, [2] Brunell on ETF flows..."
PBX gets 30 minutes to reply "go" or "swap #2 for something from TFTC."
If no reply, auto-proceed. This catches bad clips before a full render.

### 7.2 B-Roll and Chart Integration
For data-heavy segments (on-chain metrics, price action), the visual
shouldn't just be a waveform. It should show a BTC price chart, hash rate
chart, or relevant graph. `visual_fetcher.py` may already have this —
needs audit. TradingView lightweight charts can render to PNG via Playwright.

### 7.3 Guest Clip Recognition
When a partner channel features a known Bitcoin personality (Saylor, Lyn Alden,
Adam Back), extract their name from the transcript and show their name on screen
with a title card. Adds production quality. Simple NER (Named Entity Recognition)
pass on transcript text.

### 7.4 Episode Memory (Deduplication Across Days)
Store video_ids used in previous episodes in a `data/used_clips.json` file.
Never use the same clip source in two consecutive episodes.
Never use the same video_id twice ever.

### 7.5 Patreon/Fountain Attribution
When the outro plays, show real subscriber/supporter count pulled live.
"[X] sovereign stackers watching." Vanity metric but psychologically powerful
for community building.

### 7.6 Nostr Cross-Post
After YouTube upload, post episode link + title + top quote to Nostr via
nostr-tools or a relay API. Bitcoin-native distribution. Free. Aligned.
NIP-01 text note. Takes 20 lines of Python.

---

## PART 8: THE MACHINE LEARNING ARCHITECTURE

This is the piece that makes V20-V100 more powerful than V11-V20.

### The Feedback Loop

```
Episode Produced
     ↓
Uploaded to YouTube
     ↓ (wait 48 hours)
YouTube Analytics API pulls:
  - avg_view_duration_ratio (% of video watched)
  - click_through_rate
  - impressions
  - likes_per_impression
  - comments (sentiment)
     ↓
Store in data/performance/{episode_id}.json
     ↓
Weekly scoring run:
  - Which channels' clips = highest watch_duration?
  - Which topics = highest CTR?
  - Which cold open style = highest first-30s retention?
  - Which voice tone = most comments?
     ↓
Update channels.yaml priorities
Update SELECTION_PROMPT weighting
Update SCRIPT_PROMPT tone rules
     ↓
Next episode benefits from last week's data
```

### Implementation Notes
- Start simple: store raw metrics, manual analysis for first 10 episodes
- After 20 episodes: enough data to weight the prompt
- After 50 episodes: enough data to cluster by topic and find winning formulas
- After 100 episodes: full self-optimization loop

### What to Measure
```json
{
  "episode_id": "20260304",
  "channels_used": ["Natalie Brunell", "TFTC", "Simply Bitcoin"],
  "topics": ["ETF flows", "hash rate", "sovereign wealth"],
  "cold_open_style": "data-first",
  "voice_host1": "Nicole",
  "music_mood": "confident",
  "avg_view_duration_pct": 0.62,
  "ctr": 0.048,
  "impressions": 12400,
  "likes": 89,
  "comments": 14,
  "quality_score": 88
}
```

---

## FINAL VERDICT

The pipeline is 70% of the way to a shippable daily product.
The remaining 30% is:
- Clip reliability (V11-V12)
- Visual polish (V13-V15)
- Distribution automation (V16)
- Intelligence loop (V17-V20)

Do NOT do all of this in one session. One fix per version. Verified. Committed.
The machine learning piece is V17+ — not now. Get the fundamentals locked first.

The screenshot you shared shows the social segment visual is already dramatically
improved — red brand, card outline, compact waveform, correct layout.
The remaining issues are fixable in focused single-purpose sessions.

This audit stands as the source of truth for V11 onward.
All future sessions must read this before writing a line.
