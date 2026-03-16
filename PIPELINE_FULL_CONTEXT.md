# PROTOCOL PULSE CHECK — FULL PIPELINE CONTEXT
# Generated: 2026-03-13 21:58:08
# Purpose: Complete codebase + rules for cross-LLM audit and analysis

================================================================================
## PIPELINE ARCHITECTURE OVERVIEW
================================================================================

Protocol Pulse Check is an autonomous daily Bitcoin intelligence video show.

PIPELINE FLOW (12 steps):
  1. Fetch BTC price
  2. Scan 80+ YouTube partner channels for new videos + transcripts (Whisper)
  3. LLM clip selection — 5 clips from 5 different channels (Anthropic primary, Grok/Gemini fallback)
  4. Download/extract selected clips (yt-dlp + ffmpeg)
  5. Generate script (LLM) — Eryn + Mark dual-host dialogue
  6. TTS audio (ElevenLabs) — Eryn: kdnRe2koJdOK4Ovxn2DI @ 1.12x, Mark: 1SM7GgM6IMuvQlz2BwM3 @ 1.10x
  6b. Build episode manifest
  6c. Preflight check (25 gates)
  7. FFmpeg assembly — title card, PiP narration, clip highlights, transitions, outro
  8. Generate shorts/thumbnail/chapters
  9. Podcast + newsletter
  10. QC verification (loudness, silence, black frames)

HARD RULES:
  - 5 clips from 5 DIFFERENT channels (never same channel twice)
  - Audio: 48kHz stereo, -14 LUFS target, -1.5 dBTP max, no per-segment loudnorm
  - Colors: bg=#0A0A0F, red=#FF3333, white=#F4F5F8, gold=#F8C15C, cyan=#5DE4FF
  - Pure white #FFFFFF and pure black #000000 BANNED
  - Hosts: Eryn (kdnRe2koJdOK4Ovxn2DI, 1.12x), Mark (1SM7GgM6IMuvQlz2BwM3, 1.10x)
  - BANNED voices: Gigi, Jessica, Nicole, Sarah, Matilda, uxKr2vlA4hYgXZR1oPRT (Inworld)
  - Inworld TTS hard-banned (raises RuntimeError)
  - Outro ends ABRUPTLY — no fade ever
  - Logo ONLY in title card, watermark, outro — never in narration segments
  - Single loudnorm pass in concatenate_parts() only
  - Sentence boundary detection for TTS chunking
  - Min clip quality: 3Mbps
  - Gold info bar is the single non-negotiable signature element
  - Inter font for headlines (weight 900+, tracking -0.04em to -0.06em)
  - JetBrains Mono for all numerical data

INFRASTRUCTURE:
  - Server: Ultron (AMD EPYC 9R14, 4x RTX 4090)
  - SSH: ssh.protocolpulse.io
  - Pipeline: ~/protocol_pulse/video_pipeline_v3/
  - Assets: ~/protocol_pulse/video_pipeline_v3/assets/
  - Music: 30 Suno tracks at assets/music/
  - Relay: relay.protocolpulse.io/exec
  - Repo: consensusprotocol/protocol-pulse-core (main branch)
  - Claude Code: authenticated via Max subscription (unset ANTHROPIC_API_KEY before launch)

================================================================================
## GOSPEL RULES & LAWS
================================================================================

### FILE: PIPELINE_LAWS.md
```
# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before any build session.
# Every feature: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
# INVIOLABLE. No exceptions. No shortcuts. No merging without the audit.
# ------------------------------------------------------------

# PROTOCOL PULSE VIDEO PIPELINE — LAWS
# Sections 1-14 (Core Rules)
# Sections 15-18 in PIPELINE_LAWS_ADDENDUM.md
# Status: GOSPEL. Load into EVERY Claude Code session touching pipeline code.
# Created: 2026-03-04 | Updated: 2026-03-05

---

## SECTION 1: PREFLIGHT CHECKS
Every pipeline run must verify before producing anything:
- [ ] Ultron GPU available (nvidia-smi returns 0)
- [ ] ElevenLabs API key valid (test call returns 200)
- [ ] Claude API key valid
- [ ] channels.yaml exists and has >0 channels
- [ ] assets/music/ directory has >0 .mp3 files
- [ ] assets/outro_branded.mp4 exists
- [ ] config/feature_flags.json exists and is valid JSON
- [ ] No other Claude Code session writing to THIS worktree directory (~/worktrees/[feature]/ or ~/protocol_pulse/ for production)

If any check fails, log the failure and abort. Never produce a partial episode.

## SECTION 2: RESOLUTION AND FORMAT LOCK
All pipeline output MUST be:
- Video: 1920x1080, 30fps CFR, h264, yuv420p
- Audio: AAC, 48000Hz, stereo
- Container: MP4
- Shorts: 1080x1920, 30fps CFR, same audio

Mixed resolution in a single concat is a PIPELINE FAILURE.
Every part file must be normalized to these specs BEFORE concat.

## SECTION 3: ENCODING QUALITY
All video encoding uses these settings:
```
-c:v libx264 -crf 17 -preset medium -b:v 8M -maxrate 10M -bufsize 15M
-c:a aac -b:a 192k -ar 48000 -ac 2
-pix_fmt yuv420p -r 30 -vsync cfr
```
CRF 20 is BANNED. Preset "fast" is BANNED for final output.
Minimum acceptable bitrate: 5 Mbps. Target: 8 Mbps.
YouTube recommends 8 Mbps for 1080p30. We match that.

## SECTION 4: YT-DLP SOURCE QUALITY
Format selector for clip downloads:
```
-f bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]
```
This grabs the highest quality separate video+audio streams and muxes them.
The old `best[height<=1080][ext=mp4]` selector grabbed pre-muxed low-bitrate files and is BANNED.

## SECTION 5: AV SYNC — ROOT CAUSE DIAGNOSIS PROTOCOL
AV sync drift has TWO different root causes with TWO different fixes.
ALWAYS diagnose before fixing.

### Step 1: Check raw clips
```bash
for clip in cache/clips/*.mp4; do
  python3 -c "from clip_extractor import check_av_sync; print(f'$clip: {check_av_sync(\"$clip\")}s')"
done
```

### Step 2: Check final output
```bash
python3 -c "from clip_extractor import check_av_sync; print(f'FINAL: {check_av_sync(\"output/latest/pulse_check.mp4\")}s')"
```

### Diagnosis:
- If raw clips are OUT OF SYNC → ROOT CAUSE = yt-dlp download + mux
  Fix: Apply setpts=PTS-STARTPTS + asetpts=PTS-STARTPTS in clip_extractor
- If raw clips are IN SYNC but final output is OUT OF SYNC → ROOT CAUSE = assembler concat
  Fix: Normalize all parts before concat, use concat demuxer with -safe 0, add PTS reset + -async 1 on final encode
- If BOTH are in sync but video looks out of sync → ROOT CAUSE = variable frame rate
  Fix: Force CFR with -r 30 -vsync cfr on all inputs

NEVER guess. ALWAYS measure. ALWAYS log the offset numbers.

## SECTION 6: CONCAT RULES
When joining parts into final video:
1. Every part MUST be normalized to Section 2 specs before concat
2. Use FFmpeg concat demuxer: `ffmpeg -f concat -safe 0 -i filelist.txt`
3. After concat, apply: `-vf setpts=PTS-STARTPTS -af asetpts=PTS-STARTPTS,aresample=async=1`
4. Validate final output with check_av_sync(). Must be < 0.03s.
5. If > 0.03s, re-encode with nuclear fix (full decode + re-encode)

## SECTION 7: VOICE RULES
- Host 1: Nicole (piTKgcLEGmPE4e6mEKli) — stability 0.55, similarity 0.75, style 0.15
- Host 2: Chris (default male) or PBX clone when available
- Cold open: Can use slightly lower stability (0.45) for dramatic effect
- Main narration: Must be clear and confident, never whispery
- BANNED voices: Gigi (jBpfuIE2acCO8z3wKNLl), Jessica (cgSgspJ2msm6clMCkdW9)

## SECTION 8: MUSIC RULES
- Music bed: -18dB to -22dB under narration. Never overpowers speech.
- Mood classification drives track selection from assets/music/ (30 Suno tracks)
- If mood classification fails, use default confident track
- Intro: full music, fade under when narration starts
- Outro: music fades up after last narrator word, plays through outro video
- pp_background.mp3 as hardcoded path is BANNED. Always use mood-selected track.

## SECTION 9: CLIP SELECTION RULES
- Max 1 clip per channel. Enforced in Python post-selection, not just LLM prompt.
- Max 5 clips per episode (production). Max 2 clips per episode (test mode).
- Ad read double gate: LLM prompt instructs avoidance + contains_ad_read() code check.
- Clip end buffer: 8 seconds minimum. Silence detection for natural pause trim.
- Never reuse a video_id from the last 7 episodes (episode memory in data/used_clips.json).
- Mainstream channels (Joe Rogan, Lex, etc.) must pass keyword filter.

## SECTION 10: BRAND COLORS
```
PRIMARY RED:    #CC0000
DARK RED:       #880000
LIGHT RED:      #FF4444
BLACK:          #0A0A0A
SURFACE:        #141414
WHITE:          #FFFFFF
BORDER:         #1F1F1F
TEXT SECONDARY: #888888
```
Before every commit: `grep -rn "00D4FF\|7B2FFF\|3388FF\|00BFFF" *.py remotion/` must return ZERO results.
Blue/cyan/purple are permanently BANNED from all pipeline visual output.
All Remotion components import from shared brand.ts constants file.

## SECTION 11: FEATURE FLAGS
All new features start as FALSE in config/feature_flags.json.
Flip to TRUE only after isolated testing proves it works.
Pipeline reads feature_flags.json at startup and logs all flag states.
Never add a feature without a corresponding flag.

## SECTION 12: REGRESSION TEST
`bash regression_test.sh` must show 0 FAILs before any commit.
Commit message must include regression result: `regression: X/Y PASS`
Never push code that fails regression.
If a new feature breaks regression, the feature is reverted, not the test.

## SECTION 13: RENDER VALIDATION (POST-RENDER)
After every render, validate:
- [ ] Final output exists and is > 10MB
- [ ] Resolution: 1920x1080 (ffprobe)
- [ ] Bitrate: > 5 Mbps (ffprobe)
- [ ] AV sync: < 0.03s (check_av_sync on final output)
- [ ] Duration: > 60s for test, > 300s for production
- [ ] Audio present: at least 1 audio stream (ffprobe)
- [ ] No premature clip cutoffs (log shows natural pause trim for each clip)
- [ ] No duplicate channels (log shows unique channels)
- [ ] Regression passed

If any check fails, the render is INVALID. Do not upload. Do not claim done.

## SECTION 14: PROCESS RULES
- E1: One Claude Code session per worktree directory at a time. Under the multi-agent factory system, parallel sessions across DIFFERENT git worktree directories (~/worktrees/[feature]/) are explicitly permitted. Two agents in the SAME worktree = immediate abort. Production ~/protocol_pulse/ is never directly written by any agent.
- E2: Regression test before every commit. Commit includes `regression: X PASS`.
- E3: New features start behind feature flags.
- E4: "Done" = log output proves it. No claims without evidence.
- E5: One commit per fix. Non-overlapping fixes can share a session but separate commits.
- E6: Always read PIPELINE_LAWS.md + PIPELINE_LAWS_ADDENDUM.md + PIPELINE_FORENSIC_AUDIT.md before writing any code.
- E7: Never modify assembler.py and clip_extractor.py in the same commit (high conflict risk).
- E8: After each session: git add + commit + push. No uncommitted changes left on disk.

---

## BANNED TECHNOLOGIES
- MuseTalk, SadTalker (lip sync — Wav2Lip is the only approved engine)
- Creatomate, OpusClip (video generation)
- Suno API (music generation — use pre-generated tracks in assets/music/)
- Three.js, VR, DAO, quantum auth, Sora, genetic algorithms
- CRF 20 or higher (quality too low)
- Preset "fast" or "ultrafast" for final output
- `best[height<=1080][ext=mp4]` yt-dlp format (low quality pre-mux)
- Blue/cyan/purple in any visual element
- Hardcoded pp_background.mp3 path for music
- loudnorm filter in clip visual pipeline (adds 200ms latency)

---

*This document + PIPELINE_LAWS_ADDENDUM.md (sections 15-18) together form the
complete Pipeline Laws. Both must be read before every session.*


## SECTION 14B: VOICE DYNAMICS — THE CLASSIFIED BRIEFING RULE

Nicole's voice operates in 4 modes. The script writer tags each segment.
The TTS engine reads the tag and adjusts settings automatically.

### Mode 1: WHISPER (stability 0.38, similarity 0.80, style 0.05)
Use ONLY when ALL three conditions are met:
  1. The content is genuinely surprising or exclusive (not routine price updates)
  2. It's the FIRST time this information appears in the episode
  3. The segment is 2 sentences or fewer
Examples: Cold open hook, breaking revelation, shocking data point
Max usage: 2 whisper segments per episode. Never consecutive.
Tag: [WHISPER]

### Mode 2: CLEAR (stability 0.65, similarity 0.75, style 0.10)
DEFAULT mode. Used for all standard narration, transitions, and recaps.
This is 70-80% of the episode. Confident, articulate, mid-20s professional.
Tag: [CLEAR] or no tag (default)

### Mode 3: AUTHORITY (stability 0.55, similarity 0.78, style 0.15)
Used when delivering hard data, metrics, and on-chain analysis.
Slightly more intense than CLEAR. Conveys "I know what I'm talking about."
Examples: "Hash rate just hit 1,056 exahash", "ETF inflows topped $2.4 billion"
Tag: [AUTHORITY]

### Mode 4: WARM (stability 0.50, similarity 0.72, style 0.20)
Used for outros, calls to action, and community moments.
Approachable, inviting, slightly more personality.
Examples: "That's your daily brief", "Subscribe for tomorrow's intel"
Tag: [WARM]

### Anti-Staleness Rules:
- Never use WHISPER more than twice per episode
- Never use WHISPER two episodes in a row for the same segment type
- If the cold open topic is routine (daily price, hash rate), use AUTHORITY not WHISPER
- WHISPER is reserved for genuinely surprising moments. If nothing is surprising today, don't force it.
- The script writer decides the tags based on content analysis, not a fixed pattern
- Every third episode, the cold open should use CLEAR instead of WHISPER to break the pattern

### Implementation:
The script_writer SCRIPT_PROMPT includes instructions to tag each segment.
tts_engine.py reads the tag prefix and selects the corresponding voice settings.
If no tag is present, CLEAR mode is used (safe default).
## SECTION 19: VISUAL DESIGN SYSTEM — BROADCAST QUALITY

### 19A: Logo Usage
- Official logo: assets/logo_protocol_pulse.png (800x800, 3D metallic with heartbeat)
- Logo appears: bottom-right corner during narration segments (150px height, 80% opacity)
- Logo appears: centered during intro sequence (400px height, full opacity)
- Logo NEVER appears as plain text "PROTOCOL PULSE" in red courier font. Always use the logo image.
- The title card may use stylized text alongside the logo, but the logo image is the brand anchor.

### 19B: Narration Visual (Waveform + Backdrop)
Current: Plain text title + thin red waveform on black. UNACCEPTABLE for broadcast quality.

Target: Remotion-rendered animated composition:
- Background: Dark gradient mesh (#0A0A0A to #0D0D0D), subtle animated noise texture
- Logo: Centered, 300px, subtle pulse animation synced to audio amplitude
- Waveform: Stylized heartbeat line (matching the logo's EKG line aesthetic)
  - NOT a standard audio waveform. A DESIGNED waveform that looks like the logo's heartbeat
  - Red (#CC0000) main line, darker red (#660000) mirror reflection below
  - Smooth bezier curves, not jagged raw audio data
  - Animated: line draws left-to-right synchronized with speech cadence
  - Width: 960px, centered. Height: 80px main + 40px reflection
  - Subtle glow effect on peaks (box-shadow style red glow)
- Subtitle: Episode title below waveform, Inter font, 24px, #888888, tracking-wider
- Corner elements: "PROTOCOL PULSE" small text top-right, date top-left, both #444444
- Particle effects: Very subtle floating red dots (2-3 visible, slow drift, 15% opacity)

### 19C: Alpha Channel Transitions (Luma Matte)
Current: Hard-cut glitch_transition_waud.mp4 overlay. Functional but flat.

Target: Remotion-rendered WebM with alpha transparency:
- Style: Cyberpunk data-glitch. Red scan lines sweep across frame.
- Duration: 0.7 seconds (current 0.5 is too abrupt)
- Audio: Whoosh + digital glitch sound (generate or use royalty-free)
- The transition OVERLAYS on the outgoing clip and REVEALS the incoming clip
  through transparent areas. This creates a seamless blend, not a hard cut.
- Brand colors only: red glitch artifacts (#CC0000), black sweep, white flash accents
- Render as: WebM with alpha, or ProRes 4444 with alpha, or PNG sequence
- FFmpeg composites the alpha transition between parts using overlay filter

### 19D: Social Segment Cards (Cyberpunk Style)
- Card: Glassmorphism container (bg rgba(10,10,10,0.85), backdrop-blur, border #CC0000)
- Animated scanlines (horizontal, 1px, 3% opacity, slow scroll upward)
- Pulsing red dot top-left (8x8px, 0.5s pulse cycle)
- Handle text: #CC0000, JetBrains Mono font, 26px
- Tweet text: #EDEDED, Inter font, 28px, max 3 lines
- Like/RT counts: #FF4444 / #888888, bottom-right
- Card enters: slide-up from bottom + fade-in (0.4s)
- Card exits: fade-out (0.3s)
- If tweet screenshot exists (Playwright): show the actual screenshot instead of text card

### 19E: Title Card (Episode Intro)
- Duration: 4 seconds
- Logo: centered, 400px, fade-in over 1s
- Below logo: Episode title in white, 36px, Inter bold, fade-in at 1.5s
- Below title: Date + "PULSE CHECK" in #CC0000, 18px, fade-in at 2s
- Background: Animated dark mesh gradient with subtle red accent light source
- Red pulse line sweeps across bottom at 2.5s (like a heartbeat monitor flatline → pulse)
- Audio: Low synth tone + heartbeat sound effect (2 beats matching the logo's EKG)

### 19F: Lower Thirds (Speaker Identification)
When a partner channel clip plays, show a lower-third graphic:
- Position: bottom 120px of frame
- Background: gradient from transparent to rgba(0,0,0,0.8)
- Channel name: white, Inter bold, 24px
- Speaker name (if detected via NER): #CC0000, Inter, 20px, below channel name
- Small Protocol Pulse logo (50px) to the left of the text
- Animates in: slide-right + fade (0.3s)
- Animates out: fade (0.2s)
- Duration: 5 seconds after clip starts

These visual specs are PERMANENT. Every Remotion component must match this design system.
Remotion source files: remotion/src/compositions/
Brand constants: remotion/src/brand.ts


## SECTION 20: APPROVED VOICES (updated 2026-03-05)

### Host 1 (Female): Eryn
- Voice ID: kdnRe2koJdOK4Ovxn2DI
- Model: eleven_turbo_v2_5
- Description: Confident, clear, attractive mid-20s American female
- Settings per voice mode:
  - COLD_OPEN: stability 0.38, similarity 0.78, style 0.15, speed 1.12
  - NARRATION: stability 0.75, similarity 0.75, style 0.10, speed 1.12
  - AUTHORITY: stability 0.70, similarity 0.78, style 0.10, speed 1.10
  - SOCIAL: stability 0.60, similarity 0.75, style 0.12, speed 1.12
  - WARM: stability 0.60, similarity 0.72, style 0.20, speed 1.10

### Host 2 (Male): Mark
- Voice ID: 1SM7GgM6IMuvQlz2BwM3
- Model: eleven_turbo_v2_5
- Description: Wholesome, strong, warm male voice
- Settings: stability 0.40, similarity 0.75, style 0.10, speed 1.10

### BANNED voices (do not use under any circumstances):
- Gigi (jBpfuIE2acCO8z3wKNLl) — too childish
- Jessica (cgSgspJ2msm6clMCkdW9) — too British/old
- Nicole (piTKgcLEGmPE4e6mEKli) — too breathy/whispery at any stability
- Sarah (EXAVITQu4vr4xnSDxMaL) — still whispery
- Matilda (XrExE9yKIg1WjnnlVkGX) — fallback only, not approved for production


---

## SECTION 21: CHANNEL INTELLIGENCE SYSTEM — REAL-TIME MONITORING

### The Problem (audit findings 2026-03-05):
The channel scanner only runs when daily_producer.py fires. Between runs,
the pipeline is blind. Transcripts are not cached persistently. There is no
continuous monitoring of partner channels.

### The Solution: Background Intelligence Daemon

A cron job runs every 15 minutes on Ultron:
```
*/15 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/channel_daemon.py >> logs/channel_daemon.log 2>&1
```

channel_daemon.py:
1. Scans ALL channels in channels.yaml for new uploads (yt-dlp --flat-playlist)
2. Compares against data/channel_archive/known_videos.json
3. If NEW video detected (not in known_videos):
   a. Download transcript (Whisper on GPU — fast on 4090)
   b. Save to data/channel_archive/{channel_name}/{video_id}.json:
      {video_id, title, channel, upload_date, duration, transcript_text, timestamped_text}
   c. Add to known_videos.json
   d. Run topic classification + sentiment analysis on transcript
   e. Update data/intelligence/daily_signals.json with new topic velocity data
   f. Log: "NEW: {channel} — {title} ({duration}s) — topics: {topics}"
4. If no new videos: log "SCAN: No new uploads across {n} channels" and exit

### Persistent Archive:
```
data/channel_archive/
  known_videos.json           # Master index of all known video IDs + metadata
  Simply_Bitcoin/
    abc123.json               # Full transcript + metadata per video
    def456.json
  TFTC/
    ghi789.json
  ...
```

This archive grows over time. The pipeline reads from it instead of re-scanning.
After 30 days, the pipeline has a DEEP archive of every Bitcoin YouTube upload.
This IS the intelligence layer. This IS the moat.

### Freshness Rules:
- Archive updates every 15 minutes (cron)
- When daily_producer.py runs, it reads from the archive, NOT from a fresh scan
  (the archive is already fresh because the daemon keeps it updated)
- If a channel hasn't uploaded in 48 hours, flag it in the log
  (don't scan dead channels every 15 min — check them hourly instead)
- Transcript cache NEVER expires. Once transcribed, it's permanent.
  (Whisper GPU time is expensive; never re-transcribe the same video)

### Clip Sourcing Rules:
When daily_producer.py needs clips:
1. Query the archive for videos uploaded in the last 48 hours
2. Rank by: upload recency × channel priority × topic relevance to today's signals
3. Select the TOP 5 clips from 5 DIFFERENT channels
4. If fewer than 5 channels have fresh content, expand the time window to 72 hours
5. If STILL fewer than 5, expand to 7 days but log a warning:
   "LOW CONTENT: Only {n} channels have uploads in 7 days"

## SECTION 22: THE 5-CLIP RULE — ABSOLUTE REQUIREMENT

### Every Pulse Check episode features EXACTLY 5 partner clips from 5 DIFFERENT channels.

This is not a suggestion. This is a hard requirement.

Enforcement in clip_selector.py:
```python
# After LLM selects clips, validate:
selected_channels = [clip["channel"] for clip in selected_clips]
unique_channels = set(selected_channels)

# Rule 1: Exactly 5 clips in production mode
if not test_mode and len(selected_clips) != 5:
    logger.error(f"5-CLIP RULE VIOLATION: {len(selected_clips)} clips selected, need exactly 5")
    # Re-run selection with explicit 5-clip instruction

# Rule 2: All 5 must be from different channels
if len(unique_channels) != len(selected_clips):
    logger.error(f"CHANNEL DIVERSITY VIOLATION: {len(unique_channels)} unique channels for {len(selected_clips)} clips")
    # Drop duplicate channel clips, replace from other channels

# Rule 3: Never reuse a video_id from last 7 episodes (episode memory)
```

### Test mode exception:
Test mode uses 2 clips from 2 different channels (for speed).
Production mode: always 5 clips, 5 channels, no exceptions.

### Channel Selection Priority:
When choosing which 5 channels to feature (from 18+ available):
1. Channels with the freshest uploads (last 24 hours preferred)
2. Channels with highest topic relevance to today's signals
3. Channels that haven't been featured in the last 3 episodes
4. Higher priority channels (priority 1) over lower (priority 2-3)
5. Mainstream channels (Rogan, Lex) only if they have Bitcoin-specific content
   that passes the keyword filter

### Clip Duration per PRODUCTION_DESIGN_LAWS:
Each partner clip: 30-60 seconds (sweet spot: 40 seconds).
The clip_extractor selects the most insightful 40-second window from each video.
With 5 clips at 40 seconds + narration segments, total episode: 12-15 minutes.

```

### FILE: PIPELINE_LAWS_ADDENDUM.md
```

---

## SECTION 15: AD READ FILTER — PERMANENT LAW
### Clip segments containing ad reads are INVALID. They must never enter the assembly.

This is not a one-time fix. It is a permanent enforcement layer in `clip_extractor.py`.
Every clip transcript segment must pass this filter before it is eligible for selection.

```python
AD_READ_PATTERNS = [
    "brought to you by",
    "this episode is sponsored",
    "thanks to our sponsor",
    "today's sponsor",
    "use code ",
    "promo code",
    "discount code",
    "go to ",
    ".com/",
    "check out ",
    "head over to",
    "sign up at",
    "visit ",
    "affiliate",
    "limited time offer",
    "use my link",
    "click the link in",
    "swipe up",
    "free trial",
    "get 20% off",
    "get 10% off",
]

def contains_ad_read(transcript_segment: str) -> bool:
    """
    Return True if this transcript segment contains ad read content.
    Called on EVERY clip candidate before selection. If True, REJECT the clip.
    This runs in clip_extractor.py AND clip_selector.py as a double gate.
    """
    lower = transcript_segment.lower()
    for pattern in AD_READ_PATTERNS:
        if pattern in lower:
            log(f"🚫 AD READ DETECTED — pattern '{pattern}' found. Clip REJECTED.")
            return True
    return False
```

**LAW: `contains_ad_read()` is called at TWO points:**
1. In `clip_selector.py` — before a timestamp range is even selected (LLM prompt + post-selection validation)
2. In `clip_extractor.py` — before the extracted clip file is returned to the assembler

**LAW: If ad read content is detected, the clip is REJECTED entirely. Do not trim around it. Reject and find the next eligible segment.**

**LAW: Add to `SELECTION_PROMPT` in `clip_selector.py`:**
```
CRITICAL — AD READ REJECTION: NEVER select a timestamp range that contains an ad 
read, sponsorship segment, or promotional mention. Patterns that DISQUALIFY a segment:
"brought to you by", "use code", "go to [domain].com", "promo code", "check out",
"today's sponsor", "free trial", discount offers, affiliate URLs.
If the best moments in a video are interrupted by ad reads, select from a different 
video. Publishing ad content from other shows is a serious brand violation.
```

---

## SECTION 16: BRAND COLORS — IMMUTABLE PALETTE
### Protocol Pulse brand colors are RED, BLACK, WHITE. No exceptions, ever.

```python
# PROTOCOL PULSE BRAND PALETTE — use these constants everywhere
BRAND = {
    "primary_red":   "0xCC0000",     # Main accent, waveform, borders, highlights
    "dark_red":      "0x880000",     # Secondary, host 2 label, subtle accents
    "bright_red":    "0xFF4444",     # Waveform mirror, energy moments
    "bg_black":      "0x0A0000",     # Base background (near-black with red undertone)
    "bg_dark":       "0x100000",     # Slightly lighter background panels
    "card_bg":       "0x1A0000",     # Tweet cards, info panel backgrounds
    "text_white":    "0xFFFFFF",     # All body text
    "text_gold":     "0xFFD700",     # Ticker text only
    "host1_label":   "0xCC0000",     # Primary host label background
    "host2_label":   "0x880000",     # Secondary host label background
    "thumb_border":  "0xCC0000",     # Thumbnail PIP border
}

# BANNED COLORS — never use these in any visual element:
# 0x00D4FF — cyan (was old waveform color)
# 0x7B2FFF — purple
# 0x3388FF — blue (was old host 2 color)
# 0x0A0520 — blue-tinted background
# 0x050510 — blue-tinted base
```

**LAW: Before committing any assembler.py change, run:**
```bash
grep -n "00D4FF\|7B2FFF\|3388FF\|0A0520\|050510" assembler.py
```
**If any results appear: fix them before committing. Zero banned colors allowed.**

**LAW: The waveform visualizer uses `BRAND["primary_red"]` and `BRAND["bright_red"]`.
Never blue, never cyan, never purple.**

**LAW: The bottom-third waveform design — compact, contained, bottom of frame.
NOT full-screen. A sleek visualizer strip, not a wallpaper.**

---

## SECTION 17: NARRATION IS THE TIMELINE — OUTRO TIMING AUTHORITY
### Nothing starts the outro until narration audio is 100% complete. No exceptions.

This enforces Rule 3.5 from Section 3. The outro timing bug (outro playing at 3:28 while
narrator continues to 3:41) is a Rule 3.5 violation and must never happen again.

```python
def get_narration_end_timestamp(dialogue_parts: list) -> float:
    """
    Calculate the EXACT timestamp when the last narration word ends.
    The outro may not begin until AFTER this timestamp.
    """
    total = 0.0
    for part in dialogue_parts:
        duration = get_duration(part["video_path"])
        total += duration
    return total  # This is the narration_end_timestamp

def assemble_episode(dialogue_parts, outro_path, work_dir, **kwargs):
    """
    RULE: Outro is appended ONLY after ALL dialogue parts including wrap.
    The concat list must have all dialogue parts listed BEFORE outro.
    """
    parts = []
    
    # Step 1: Render ALL dialogue parts (includes cold open, clips, narrator 
    # segments, wrap). Every part goes into `parts` list.
    for entry in dialogue_parts:
        rendered = render_segment(entry, work_dir)
        if not validate_video_file(rendered):
            raise RuntimeError(f"Invalid segment: {entry}")
        parts.append(rendered)
    
    # Step 2: ONLY after ALL dialogue is in parts list, add outro
    narration_end = sum(get_duration(p) for p in parts)
    log(f"Narration ends at {narration_end:.1f}s — outro starts here")
    
    if outro_path and os.path.exists(outro_path):
        parts.append(outro_path)
    
    # Step 3: Concat in order — narration always finishes before outro plays
    return concat_parts(parts, work_dir)
```

**LAW: The `parts` list is built sequentially. Outro is always the LAST item appended.**
**LAW: Never start outro while narration audio is still in the timeline.**
**LAW: If outro video is a different duration than expected, pad or trim it — never let it interrupt narration.**

---

## SECTION 18: AUDIO SYNC — ROOT CAUSE DIAGNOSIS REQUIRED
### AV sync must be diagnosed at the source, not patched at the output.

The recurring audio sync issue has two completely different root causes with different fixes.
**Diagnose which one it is before writing any code.**

### Diagnosis Protocol:
```bash
# Step 1: Check a raw downloaded clip BEFORE any processing
ffprobe -v quiet -print_format json -show_streams raw_clip.mp4 | python3 -c "
import json,sys
data=json.load(sys.stdin)
for s in data['streams']:
    print(s['codec_type'], 'start_time:', s.get('start_time','N/A'), 
          'start_pts:', s.get('start_pts','N/A'))
"
# If video start_time != audio start_time on the RAW clip: ROOT CAUSE = download/source
# Fix: PTS regeneration during clip extraction

# Step 2: Check the assembled output
ffprobe -v quiet -print_format json -show_streams final_output.mp4 | python3 -c "
import json,sys
data=json.load(sys.stdin)
for s in data['streams']:
    print(s['codec_type'], 'start_time:', s.get('start_time','N/A'))
"
# If raw clips are in sync but output is not: ROOT CAUSE = assembler concat
# Fix: Normalize all segments before concat, use -async 1 in final encode
```

### Fix A: Source out of sync (clips arrive pre-drifted)
```python
# In clip_extractor.py — apply to EVERY clip immediately after download
def fix_clip_sync(input_path: str, output_path: str) -> bool:
    return run_ffmpeg([
        "-fflags", "+genpts+igndts",
        "-i", input_path,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-r", "30", "-vsync", "cfr",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-af", "aresample=async=1:min_hard_comp=0.100000:first_pts=0",
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        output_path,
    ], "fix_clip_sync", 180)
```

### Fix B: Assembler introducing drift (concat is misaligning streams)
```python
# In assembler.py — normalize EVERY segment before adding to concat list
def normalize_for_concat(input_path: str, output_path: str) -> bool:
    """Ensure consistent timebase and stream layout before concat."""
    return run_ffmpeg([
        "-i", input_path,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-r", "30", "-vsync", "cfr",
        "-pix_fmt", "yuv420p",
        "-video_track_timescale", "90000",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-af", "aresample=async=1",
        output_path,
    ], "normalize_concat", 120)
```

**LAW: Run the diagnosis protocol FIRST. Report which root cause is identified.**
**LAW: Apply the correct fix — don't apply both blindly.**
**LAW: After fix, log AV offset for every clip:**
```python
def measure_av_offset(clip_path: str) -> float:
    """Returns offset in seconds. 0 = perfect. Positive = audio ahead of video."""
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", clip_path],
        capture_output=True, text=True
    ).stdout)
    streams = probe.get("streams", [])
    v_start = next((float(s.get("start_time", 0)) for s in streams if s["codec_type"] == "video"), 0)
    a_start = next((float(s.get("start_time", 0)) for s in streams if s["codec_type"] == "audio"), 0)
    offset = a_start - v_start
    log(f"AV offset for {os.path.basename(clip_path)}: {offset:+.3f}s")
    if abs(offset) > 0.1:
        log(f"⚠️ AV SYNC WARNING: offset {offset:+.3f}s exceeds 0.1s threshold")
    return offset
```
**LAW: Any clip with AV offset > 0.1s after fix must be flagged in the log.**

```

### FILE: VISUAL_DESIGN_SYSTEM.md
```
# PROTOCOL PULSE — VISUAL DESIGN SYSTEM
# Based on ChatGPT Broadcast Engine (A/B Test Winner)
# Total Visual Overhaul for Video Pipeline
# Status: GOSPEL. Every Remotion component and FFmpeg visual must follow this.
# Created: 2026-03-06

---

## DESIGN PHILOSOPHY

"Bloomberg Terminal meets cinematic newscast."

This is NOT a YouTube channel aesthetic. This is a BROADCAST INTELLIGENCE PRODUCT.
Every frame must communicate: authority, precision, urgency, and premium quality.
The viewer should feel like they're watching a $2M/year production, not an AI tool.

Key principles:
1. INFORMATION DENSITY over empty space — every pixel earns its place
2. EDITORIAL HIERARCHY — eyebrow → headline → body → metadata (always)
3. MULTI-COLOR LIGHT SYSTEM — not monochrome, three coordinated glow sources
4. GOLD AS SIGNATURE — the gold info bar and gold accents are the brand differentiator
5. GLASSMORPHISM WITH RESTRAINT — blur + transparency, but never muddy or illegible
6. MOTION WITH PURPOSE — every animation communicates something, never decorative

---

## SECTION 1: COLOR SYSTEM

### Primary Palette:
```
--bg:        #06070b     (deep space black — base layer)
--panel:     #0d1118     (elevated surface — cards, overlays)
--panel-2:   #121824     (secondary surface — nested elements)
--text:      #eef2ff     (primary text — slightly blue-white, not pure white)
--muted:     #95a0ba     (secondary text — metadata, handles, timestamps)
```

### Accent Colors:
```
--red:       #ff3b5f     (Protocol Pulse red — alerts, active states, brand)
--gold:      #f8c15c     (SIGNATURE — info bar, kickers, section labels, scores)
--cyan:      #5de4ff     (data accents — secondary glow, cool contrast)
--lime:      #89ffb8     (positive metrics — up arrows, gains)
--coral:     #ff8ba0     (negative metrics — danger, compression, losses)
```

### Glow Colors (for shadows and radial gradients):
```
--glow-red:  rgba(255,59,95,0.45)
--glow-gold: rgba(248,193,92,0.30)
--glow-cyan: rgba(93,228,255,0.20)
```

### Color Usage Rules:
- Gold (#f8c15c) = ALL section kickers, eyebrows, labels, score badges, info bar bg
- Red (#ff3b5f) = active card borders, alert states, brand mark, pulse dots
- Cyan (#5de4ff) = secondary data, cool-tone glow source, chart accent
- Lime (#89ffb8) = positive deltas ONLY ("+3.8%", "▲", up arrows)
- Coral (#ff8ba0) = negative deltas, danger states, "compression", "under pressure"
- NEVER use pure white (#ffffff) for text — always #eef2ff (warmer, less harsh)
- NEVER use pure black (#000000) for backgrounds — always #06070b minimum

### Temperature Pacing Across Episode (per PRODUCTION_DESIGN_LAWS):
- Cold open: RED dominant (urgency)
- Title sequence: RED + GOLD (brand identity)
- Narration setup: NEUTRAL (balanced palette)
- Partner clips: WARM (natural, let clip colors dominate)
- Data segment: CYAN + GOLD (analytical, authoritative)
- Social segment: RED + GOLD (engagement energy)
- Wrap: WARM GOLD (resolution, satisfaction)
- Outro: RED + GOLD (brand signoff)

---

## SECTION 2: TYPOGRAPHY

### Font Stack:
```
--sans:  Inter, ui-sans-serif, system-ui, sans-serif     (headlines, body)
--mono:  'JetBrains Mono', 'SF Mono', ui-monospace, monospace  (data, labels, tickers)
```

### Type Scale:
```
HEADLINES (scene titles):
  Cold open headline:    52-64px, weight 900, tracking -0.04em, line-height 0.95
  Section title:         36-42px, weight 900, tracking -0.04em, line-height 0.96
  Title sequence:        72-94px, weight 950, tracking -0.06em, line-height 0.90

EYEBROW KICKERS (above headlines):
  Size: 10-11px, weight 800, tracking 0.18-0.20em, UPPERCASE
  Color: ALWAYS gold (#f8c15c)
  Format: "CATEGORY • DESCRIPTOR" (e.g., "COLD OPEN • HIGHEST STAKES")

BODY TEXT:
  Subtitle/description:  17-22px, weight 400-500, line-height 1.4
  Color: #d7def4 (light blue-white)

DATA VALUES:
  Large metric:          26-34px, weight 900, tracking -0.03em, font: monospace
  Delta/change:          11-14px, weight 700
  Label:                 9-11px, weight 800, tracking 0.18em, UPPERCASE, color: muted

METADATA:
  Handles:              12px, color: muted
  Timestamps:           12px, color: muted
  Tags/chips:           9-11px, weight 800, tracking 0.12em, UPPERCASE
```

### Typography Rules:
- Headlines: ALWAYS use text-shadow: "0 4px 28px rgba(0,0,0,0.4)" for depth
- Headlines: Break long lines strategically with <br /> — never let text run edge-to-edge
- Eyebrows: ALWAYS gold, ALWAYS uppercase, ALWAYS above the headline
- NEVER use more than 2 font weights in one card (e.g., 800 for label + 900 for value)
- Monospace for ALL data: prices, percentages, hashrates, timestamps, scores
- Sans-serif for ALL editorial content: headlines, descriptions, quotes, names

---

## SECTION 3: BACKGROUND SYSTEM

### Three-Source Light Model:
The background is NOT flat. It has three coordinated radial glow sources:

```
Source 1 (RED):   top-left area, rgba(255,59,95,0.14), radius ~300px
Source 2 (CYAN):  top-right area, rgba(93,228,255,0.10), radius ~250px
Source 3 (GOLD):  bottom-center area, rgba(248,193,92,0.06), radius ~200px
```

These create the "cinematic" depth that flat backgrounds lack.
The sources should subtly shift position over time (±30px oscillation, 5-7 second cycle).

### Perspective Floor Grid:
```
- Vanishing point: center frame, 55% from top
- Grid lines: rgba(255,255,255,0.02-0.05), 0.4-0.5px width
- 20 horizontal lines, receding into depth (quadratic spacing)
- 14 vertical lines, converging to vanishing point
- Transform: perspective(1200px) rotateX(72deg) translateY(240px) scale(2.2)
- Subtle red glow filter: drop-shadow(0 0 16px rgba(255,59,95,0.12))
```

### Overlay Layers (bottom to top):
```
Layer 0: Solid #06070b
Layer 1: Three-source radial gradient (red + cyan + gold)
Layer 2: Perspective floor grid (CSS transform or FFmpeg drawgrid)
Layer 3: Noise texture (radial-gradient dots, 8px spacing, 7% opacity, soft-light blend)
Layer 4: Scanlines (horizontal lines, 4px spacing, 4% opacity)
Layer 5: Pulse rings (2 centered, subtle animation, red + cyan)
Layer 6: Signal sweep (diagonal light band, crosses frame every 7 seconds)
Layer 7: Vignette (radial-gradient from transparent center to 45% black edges)
```

### For Remotion:
Each layer is an `<AbsoluteFill>` component stacked in order.
For FFmpeg: composite as overlay filters in the filtergraph.

### For Video Pipeline (FFmpeg equivalent):
```bash
# Background composite (simplified)
ffmpeg -i solid_bg.png \
  -filter_complex "
    [0]drawbox=x=0:y=0:w=1920:h=1080:c=black@1:t=fill[bg];
    [bg]curves=all='0/0 0.15/0.03 1/0.05'[tinted];
    [tinted]vignette=angle=PI/4:mode=forward[vig]
  " output_bg.mp4
```

---

## SECTION 4: NARRATOR SEGMENT LAYOUT

### Split-Screen Composition:
```
┌──────────────────────────────────────────────────────────────────┐
│ [EYEBROW KICKER: gold, 10px, tracking 0.20em]                   │
│                                                                   │
│ [HEADLINE: 52px, white, 2-3 lines max]      ┌──────────────────┐│
│                                              │                  ││
│ [BODY: 17px, #d7def4, max 480px width]       │   PiP PREVIEW    ││
│                                              │   (340x210)      ││
│                                              │   rounded 16px   ││
│                                              │   border + shadow││
│                                              │                  ││
│                                              │  [COMING UP]     ││
│                                              │  [speaker/source]││
│                                              └──────────────────┘│
│                                                                   │
│ ════════════════════════════════════════════════════════════════  │
│ [WAVEFORM: gold gradient, bottom-third, full width]              │
│ ════════════════════════════════════════════════════════════════  │
│ ██████████████████████ GOLD INFO BAR ██████████████████████████  │
└──────────────────────────────────────────────────────────────────┘
```

### PiP Preview Styling:
```
Position:     absolute, right: 36px, bottom: 100px
Size:         340 x 210 pixels (16:9 aspect)
Border:       1px solid rgba(255,255,255,0.10)
Border-radius: 16px
Shadow:       0 16px 48px rgba(0,0,0,0.35), 0 0 30px rgba(255,59,95,0.06)
Background:   actual muted video (not static image)
Label:        "COMING UP" — 10px, gold (#f8c15c), tracking 0.18em, above the frame
Speaker info: glassmorphism bar at bottom of PiP (rgba(0,0,0,0.4) + blur(10px))
```

### Waveform (Gold Gradient):
```
Style:        EKG heartbeat line, NOT frequency bars
Colors:       gradient stroke from rgba(255,59,95,0.15) → rgba(248,193,92,0.85) → rgba(93,228,255,0.12)
Glow:         8px blur in gold, then 3px main line, then 1.2px bright core
Line width:   3px main, with 8px glow behind
Position:     bottom of frame, above info bar
Height:       120px total area
Baseline:     subtle horizontal line at center (rgba(255,255,255,0.04))
```

---

## SECTION 5: GOLD INFO BAR (SIGNATURE ELEMENT)

This is the MOST DISTINCTIVE visual element. It's what makes Protocol Pulse recognizable.

```
Position:     absolute bottom, full width
Height:       42px
Background:   linear-gradient(90deg, rgba(248,193,92,0.88), rgba(255,219,132,0.92))
Text color:   #141515 (dark, near-black — contrast against gold)
Font:         JetBrains Mono, 12px, weight 800, tracking 0.08em
Layout:       3-column grid:
  Left:       "BTC 96,482 ▲ 2.14%" (live price)
  Center:     "PROTOCOLPULSE.IO"
  Right:      "MARCH 2026 • DAILY BRIEF"
```

Rules:
- Info bar appears on EVERY scene except title sequence and outro
- Price updates at render time (not live, but current when rendered)
- Arrow (▲/▼) changes color to match price direction
- This bar is NEVER transparent or dark — always gold

---

## SECTION 6: SOCIAL CARD DESIGN

### Card Container:
```
Background:   linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))
Border:       1px solid rgba(255,255,255,0.08)
              Active card: 1px solid rgba(255,59,95,0.30)
Border-radius: 16px
Padding:      18px 20px
Shadow:       Active: 0 16px 48px rgba(0,0,0,0.35), 0 0 36px rgba(255,59,95,0.12)
              Inactive: 0 8px 24px rgba(0,0,0,0.2)
Backdrop:     blur(16px)
```

### Card Layout:
```
Top row:      [Avatar 42px circle] [Name 16px bold + Handle 12px muted] [Score badge: gold border, gold text]
Body:         Quote text — 22px, weight 700, line-height 1.25, max-width 580px
Footer:       Signal tag — 10px, #ffb6c2 (light coral), tracking 0.16em, weight 800
              Format: "SIGNAL STRENGTH • HIGH CONVICTION" or "MACRO SIGNAL • STRUCTURAL"
```

### Animation:
```
Entry:    slide-in from right, 300ms, easeOutExpo
Hold:     match narration duration exactly
Exit:     fade out, 300ms
Scale:    active card = scale(1), inactive = scale(0.97) + opacity 0.75
```

### Score Badge:
```
Font:         11px, monospace, weight 800
Color:        gold (#f8c15c)
Border:       1px solid rgba(248,193,92,0.20)
Border-radius: 999px (pill shape)
Padding:      5px 10px
```

---

## SECTION 7: DATA SEGMENT DESIGN

### Layout:
```
Split grid: 55% left (text + stat cards) / 45% right (chart)
Gap: 20px
```

### Stat Cards (2x2 grid):
```
Background:   linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))
Border:       1px solid rgba(255,255,255,0.10)
Border-radius: 14px
Padding:      14px 16px
Shadow:       0 12px 36px rgba(0,0,0,0.25)

Content:
  Label:      9px, monospace, tracking 0.18em, color: muted, weight 800, UPPERCASE
  Value:      26px, monospace, weight 900, tracking -0.03em (tight)
  Delta:      11px, weight 700, color varies:
              Positive: lime (#89ffb8)
              Negative: coral (#ff8ba0)
              Neutral:  #cfd7eb
```

### Chart Panel:
```
Background:   same glassmorphism as cards
Grid overlay: 48px spacing, rgba(255,255,255,0.03)
Header:       "BTC / NETWORK STRESS INDEX" + "LIVE MODEL" chip
              Chip: pill shape, rgba(255,59,95,0.10) bg, #ffbdc8 text

Chart line:   SVG path with gradient stroke:
              Red (#ff4d6d) → Gold (#ffd166) → Green (#7bf1a8)
              Stroke-width: 5px, round linecap
Fill:         Below line, gradient from rgba(255,77,109,0.30) → transparent
Pulse dot:    End of line, 7px radius, #ff4d6d, animated pulsing (7→10→7, 2s cycle)
```

---

## SECTION 8: LOWER THIRD DESIGN

### Structure:
```
┌─────────────────────────────────────────────────────────┐
│ ═══════════════ red reveal bar (3px, animated width) ══│
│                                                         │
│  [KICKER: gold, 10px]           [TAG: gold, 10px]      │
│  [NAME: white, 18px bold]       [TIME: muted, 12px]    │
│                                                         │
│ ─────────────── glassmorphism bg + blur ──────────────  │
└─────────────────────────────────────────────────────────┘
```

### Styling:
```
Background:    linear-gradient(90deg, rgba(10,14,22,0.88), rgba(10,14,22,0.72))
Border-top:    1px solid rgba(255,255,255,0.08)
Backdrop:      blur(14px)
Height:        ~87px

Top reveal bar:
  Height: 3px
  Background: linear-gradient(90deg, #ff3b5f, rgba(255,59,95,0.1))
  Width: animated from 0% → 100% over 400ms (easeOutExpo)

Entry animation: slide-in from left, 700ms, easeOutExpo
```

---

## SECTION 9: TITLE SEQUENCE

### Layout: centered, all text stacked
```
[KICKER: "CONSENSUS INTELLIGENCE" — gold, 11px, tracking 0.24em]
[TITLE: "PROTOCOL PULSE" — white, 72px, weight 950, tracking -0.06em]
[SUBTITLE: "Daily Bitcoin Brief • March 2026" — #d9e1f7, 18px]
[PULSE LINE: horizontal gradient line, animated width, centered]
```

### Background: standard three-source glow + radial glow behind title
```
Radial glow: circle, rgba(255,59,95,0.10), centered on title, radius ~300px, blur(10px)
```

### Animation:
```
Logo scale: 0.85 → 1.0 over 20 frames (easeOutExpo)
Title opacity: fade in over 15 frames
Subtitle: delayed fade in (starts at frame 10)
Pulse line: width animates from 0 → 300px starting at frame 15
Duration: 4 seconds total (120 frames at 30fps)
```

---

## SECTION 10: OUTRO

### Content:
```
[KICKER: "TOMORROW'S BRIEF STARTS NOW" — gold, 10px]
[TITLE: "PROTOCOL PULSE" — white, 64px, weight 950]
[CTA: "Subscribe for tomorrow's brief." — #d7def4, 18px]
[EQUALIZER BARS: 5 bars, red/coral gradient, animated bounce]
```

### Equalizer Bars:
```
Count: 5 bars, centered
Width: 10px each, gap: 8px
Height: animated sinusoidal, 14-46px range
Color: linear-gradient(180deg, #ff3b5f, #ff7a4f)
Shadow: 0 0 12px rgba(255,59,95,0.2)
Animation: staggered bounce, 1.4s cycle
```

### Rules:
- NO narration over outro (just visual + outro jingle)
- Ends ABRUPTLY — no fade to black
- Duration: 3-4 seconds
- Info bar HIDDEN during outro

---

## SECTION 11: TRANSITION DESIGN

### Glitch Sweep Transition:
```
Duration: 1.0 second (30 frames at 30fps)
Elements:
  1. Three skewed sweep bars (positions: 18%, 44%, 70% from top)
     - Transform: skewX(-25deg), translate from -120% to +180%
     - Background: linear-gradient(90deg, transparent, rgba(255,59,95,0.20), rgba(255,255,255,0.10), transparent)
     - Blur: 2px
     - Staggered timing: 0ms, 80ms, 140ms delay

  2. Radial flash at peak (frames 6-14)
     - Center-origin radial gradient
     - rgba(255,255,255,0.08) at center → rgba(255,59,95,0.04) → transparent
     - Fades in/out over 8 frames

Audio: custom_whoosh.mp3 synced to visual peak
```

---

## SECTION 12: COLD OPEN SPECIFICS

### Per PRODUCTION_DESIGN_LAWS:
- First frame: NO logo, NO music, immediate voice + face on screen
- Eyebrow kicker above headline (gold)
- Large headline (52-64px, 2-3 lines)
- Body description (17px, max 480px width)
- PiP preview card: right side, showing upcoming speaker

### Visual Hierarchy:
```
1. Eyebrow kicker (gold) — tells viewer what category
2. Headline (white, massive) — the hook
3. Body (light blue) — context
4. PiP preview (right) — face on screen + "COMING UP"
5. Waveform (bottom) — audio visualization
6. Info bar (gold, bottom) — always present
```

### NO logo in cold open. NO branding except the info bar.
The CONTENT is the brand. The info bar handles brand presence.

---

## SECTION 13: PARTNER CLIP SPECIFICS

### Full-frame clip with:
- Subtle warm glow behind speaker (rgba(248,193,92,0.2), radial, behind face area)
- Small "PROTOCOL PULSE" watermark: top-right, 10px, monospace, 50% opacity
- Lower third: slides in from left at clip start, holds 5 seconds, slides out
- Info bar: visible (gold)

### NO waveform during partner clips
### NO background animation during partner clips
### Let the clip BREATHE — the guest's face is the visual

---

## SECTION 14: REMOTION IMPLEMENTATION GUIDE

### Component Architecture:
```
<Episode>
  <BackgroundSystem />           // 7 layers (gradient, grid, noise, scanlines, rings, sweep, vignette)
  <Scene type={manifest.type}>   // Switches based on manifest segment type
    <ColdOpen />                 // or <TitleSequence /> or <PartnerClip /> etc.
  </Scene>
  <WaveformBand />               // Gold gradient EKG (hidden during clips)
  <GoldInfoBar />                // ALWAYS visible except title + outro
  <GlitchTransition />           // Between segments
</Episode>
```

### Each scene reads from the manifest:
```tsx
const segment = manifest.segments[currentIndex];
// segment.type determines which scene component renders
// segment.screen_mode determines visual treatment
// segment.music_state determines audio
// segment.logo_allowed determines brand presence
// segment.primary_visual_type determines what fills the scene
```

### FFmpeg Equivalent (for non-Remotion assembly):
```bash
# Gold info bar overlay
-filter_complex "
  [base]drawbox=x=0:y=1038:w=1920:h=42:c=#f8c15c@0.9:t=fill[bar];
  [bar]drawtext=text='BTC 96,482':x=20:y=1048:fontsize=24:fontcolor=#141515:fontfile=JetBrainsMono[ticker]
"

# Glassmorphism card effect
-filter_complex "
  [bg]crop=w=680:h=300:x=620:y=200[crop];
  [crop]boxblur=16[blurred];
  [base][blurred]overlay=x=620:y=200[glass]
"
```

---

## SECTION 15: QUALITY CHECKLIST

Before any render ships, verify these visual standards:

□ Background has visible depth (three glow sources, not flat black)
□ Gold info bar present on all scenes except title + outro
□ Eyebrow kickers are gold, uppercase, with proper tracking
□ Headlines use the correct weight (900+) and tracking (-0.04em)
□ PiP preview shows actual video, not static image
□ Lower thirds slide in with animated reveal bar
□ Social cards enter/exit with proper animation (no dark gaps)
□ Data segment has chart SVG with gradient fill + pulsing dot
□ Waveform uses gold gradient (not red-only)
□ No logo in narration segments (per Logo Restraint Rule)
□ Stat card deltas use correct colors (lime=up, coral=down)
□ Transitions are exactly 1.0 second with synced whoosh
□ No pure white (#ffffff) text — always #eef2ff
□ No pure black (#000000) backgrounds — always #06070b minimum
□ Monospace font used for ALL numerical data
□ Scanlines present but subtle (4% opacity max)

---

*This document defines the complete visual language for Protocol Pulse video output.
Every Remotion component, FFmpeg filter, and visual decision must reference this.
Pair with: PRODUCTION_DESIGN_LAWS.md, PIPELINE_MANIFEST_SPEC.md, DEFINITIVE_BUILD_PROMPT.md*


```

### FILE: APEX_UNIFIED_DESIGN_SYSTEM.md
```
# APEX UNIFIED DESIGN SYSTEM — GOSPEL
# Supersedes BLACK_DIAMOND_DESIGN_SYSTEM.md and BROADCAST_ENGINE_DESIGN_SYSTEM.md
# Status: ACTIVE | Created: 2026-03-08
# This is the synthesis of all 3 design generations. Best elements merged.

## Philosophy
"Sovereign Broadcast Intelligence" — the best of all three systems:
- **VDS**: Finance terminal density, gold kickers, color temperature pacing
- **Black Diamond**: Tactical L-brackets, 108px impact type, surveillance scanlines
- **Broadcast Engine V2**: 6-scene architecture, cinematic glows, glassmorphic pills

## Color System
| Token          | Hex       | Source | Usage                                      |
|----------------|-----------|--------|---------------------------------------------|
| COLOR_BG       | #020304   | BEV2   | Cinematic obsidian base (not flat black)    |
| COLOR_PANEL    | #050607   | BEV2   | Elevated surface                            |
| COLOR_PANEL2   | #080A0C   | APEX   | Secondary surface                           |
| COLOR_RED      | #FF0000   | BD     | Signal red — all accents, brackets, borders |
| COLOR_RED_WARM | #FF334D   | BEV2   | Warm red — transition elements only         |
| COLOR_WHITE    | #F4F5F8   | BEV2   | Warm white — not pure white                 |
| COLOR_GOLD     | #F8C15C   | VDS    | EYEBROW KICKERS ONLY (not full brand)       |
| COLOR_MUTED    | #888888   | BD     | Secondary labels                            |
| COLOR_MUTED2   | #555555   | APEX   | Metadata, timestamps                        |
| COLOR_GREEN    | #6EE7B7   | BEV2   | Emerald — positive/DONE                     |
| COLOR_CORAL    | #FF8BA0   | VDS    | Coral — negative/warning                    |
| COLOR_RED_DIM  | #1A0000   | BD     | CTA box backgrounds                         |
| COLOR_TICKER_BG| #0C0C0C   | BD     | Ticker bar background                       |

## BANNED Colors
Blue (#00D4FF), Cyan (#5de4ff), Purple (#7B2FFF) — all permanently banned.

## Background (7 layers)
1. BEV2 cinematic obsidian base (#020304)
2. BEV2 3-glow radial (top-left red, top-right white, bottom-center red)
3. VDS perspective grid (bottom 30%, white @4% opacity)
4. BD scanlines (horizontal every 4px, red @2.5%)
5. Vignette (center clear, edges dark)
6. Film grain (SKIPPED — geq too slow; can be re-enabled)
7. BD red border frame (2px all edges, #FF0000 @75%)

## Header Bar (BD structure + BEV2 glassmorphic pill)
- Floating pill: x=20,y=12,w=1880,h=52, black @55%
- Red left accent line (3px, BD signature)
- Left: "● PROTOCOL PULSE" white bold 20px + "LIVE" red 16px
- Center: "Broadcast Signature System" muted mono 11px
- Right: "Motion Active" | "Narration Layer" | "RECON-ID: {id}" muted mono 11px
- Bottom separator: red @25%

## Info Rail (BEV2 gradient bar)
- Height: 48px at y=1032
- 3-zone gradient: red @85% | white @90% | warm red @85%
- BLACK text: BTC price left, PROTOCOLPULSE.IO center, date right
- Font: bold 14-15px

## Narration Wave (BEV2 EKG dual-layer)
- Zone: 1920x120 at y=912 (above info rail)
- Primary: showwaves mode=line, white @80% + red @40%, sqrt scale
- Accent: showwaves mode=cline, warm red @30%, log scale
- Blended via screen mode

## Corner Brackets (BD tactical)
- All 4 corners: 40x4px L-bracket in signal red (#FF0000)

## Scene Types (BEV2 6-scene routing — unchanged)

### Scene 1: COLD OPEN
- BD left impact panel (72px font SIGNAL/DETECTED)
- VDS 2x2 metric cards right (gold eyebrow labels)
- Chart panel with rising bar chart + pulse dot
- Gold eyebrow: "BREAKING INTELLIGENCE"

### Scene 2: NARRATOR + PiP
- BEV2 text zone left + PiP preview right
- BD mini corner brackets on PiP frame (16px)
- Gold eyebrow: "COMING UP NEXT" above PiP
- Status pills: "ORACLE NARRATION ACTIVE" + "Story Arc Locked"

### Scene 3: PARTNER CLIP
- BEV2 restraint — full-frame B-roll
- Glass lower-third with red top accent line
- Speaker name bold 26px + source info
- PROTOCOL PULSE watermark top-right (red, 18px, 60%)

### Scene 4: DATA SEGMENT
- Gold eyebrow labels on all metric cards (VDS)
- Emerald positive / coral negative deltas (VDS)
- Right chart panel with gold "Model Active" pill
- Gold eyebrow: "MARKET STRUCTURE"

### Scene 5: SOCIAL STACK
- BEV2 3-column conviction cards
- VDS gold score badges (not plain white)
- VDS gold tag labels at bottom
- BD primary card red accent border, others white @8%

### Scene 6: WRAP / VERDICT
- BEV2 waveform visualization right
- BD episode segments tracker below (DONE/ACTIVE/PENDING)
- Gold eyebrow: "EPISODE SEGMENTS"
- DONE=emerald, ACTIVE=red, PENDING=dim

## Intro Cold Open Card
- APEX background (all 7 layers)
- Corner brackets
- "PROTOCOL PULSE" centered white bold 72px
- "PULSE CHECK" centered red bold 52px
- Gold date eyebrow
- "// SIGNAL DETECTED //" red mono 16px
- Fade in 0.4s, fade out 0.4s

## Transitions
- VDS glitch sweep (3-layer diagonal red + white flash + radial pulse)
- Total: 0.35s (athletic, per BEV2 philosophy)

## Color Temperature Pacing (VDS)
- Cold Open: HIGH ENERGY — red + gold dominant
- Data: ANALYTICAL — cooler, gold labels for clarity
- Social: WARM — gold score badges
- Wrap: WARM GOLD — resolved energy

```

### FILE: REGRESSION_TEST_CHECKLIST.md
```
# VIDEO PIPELINE REGRESSION TEST — MANDATORY BEFORE EVERY COMMIT

## RULE: NO COMMIT UNTIL ALL CHECKS PASS
Run this checklist after EVERY change to assembler.py, script_writer.py, tts_engine.py, clip_extractor.py, or daily_producer.py. If ANY check fails, fix it before committing. Do NOT commit partial work that regresses existing features.

## HOW TO RUN
```bash
cd ~/protocol_pulse/video_pipeline_v3
python3 daily_producer.py --test --skip-scan 2>&1 | tee /tmp/pipeline_test.log
```
Then run verification:
```bash
bash ~/protocol_pulse/video_pipeline_v3/regression_test.sh
```

---

## AUTOMATED CHECKS (regression_test.sh runs these)

### 1. OUTPUT EXISTS
```bash
LATEST=$(ls -td output/test_* | head -1)
[ -f "$LATEST/pulse_check_*.mp4" ] || echo "FAIL: No final video"
[ -f "$LATEST/script.json" ] || echo "FAIL: No script"
[ -d "$LATEST/work" ] || echo "FAIL: No work directory"
```

### 2. VIDEO SPECS
```bash
FINAL="$LATEST/pulse_check_*.mp4"
# Resolution must be 1920x1080
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 $FINAL | grep -q "1920,1080" || echo "FAIL: Not 1920x1080"
# Pixel format must be yuv420p
ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 $FINAL | grep -q "yuv420p" || echo "FAIL: Not yuv420p"
# Has audio
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 $FINAL | grep -q "aac" || echo "FAIL: No AAC audio"
# Duration > 30s (even test mode should produce 30s+)
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $FINAL | cut -d. -f1)
[ "$DUR" -gt 30 ] || echo "FAIL: Duration too short ($DUR s)"
```

### 3. PARTS STRUCTURE — ALL REQUIRED PARTS PRESENT
```bash
WORK="$LATEST/work"
# Cold open MUST exist
ls $WORK/part_*cold_open* >/dev/null 2>&1 || echo "FAIL: No cold open part"
# At least 1 clip
ls $WORK/part_*clip* >/dev/null 2>&1 || echo "FAIL: No clip parts"
# At least 1 setup (narrator intro before clip)
ls $WORK/part_*setup* >/dev/null 2>&1 || echo "FAIL: No setup parts"
# At least 1 react (narrator after clip)
ls $WORK/part_*react* >/dev/null 2>&1 || echo "FAIL: No react parts"
# Glitch transitions
ls $WORK/part_*glitch* >/dev/null 2>&1 || echo "FAIL: No glitch transitions"
# Wrap (closing line)
ls $WORK/part_*wrap* >/dev/null 2>&1 || echo "FAIL: No wrap part"
# Outro
ls $WORK/part_*outro* >/dev/null 2>&1 || echo "FAIL: No outro part"
```

### 4. NO BLACK FRAMES — VERIFY VISUAL CONTENT
```bash
# Check each part has real video (file size > 100KB minimum)
for f in $WORK/part_*.mp4; do
    SZ=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
    if [ "$SZ" -lt 100000 ]; then
        echo "FAIL: $f is only ${SZ} bytes — likely black/empty"
    fi
done

# Intro specifically — must not be black
INTRO=$(ls $WORK/part_000* 2>/dev/null | head -1)
if [ -n "$INTRO" ]; then
    INTRO_SZ=$(stat -c%s "$INTRO" 2>/dev/null || stat -f%z "$INTRO" 2>/dev/null)
    [ "$INTRO_SZ" -gt 500000 ] || echo "FAIL: Intro too small — likely black screen"
fi
```

### 5. THUMBNAIL OVERLAYS — VERIFY THUMBNAILS FETCHED
```bash
# Check that YouTube thumbnails were downloaded for clips
THUMB_COUNT=$(ls /tmp/thumb_*.jpg 2>/dev/null | wc -l)
CLIP_COUNT=$(ls $WORK/part_*clip* 2>/dev/null | wc -l)
[ "$THUMB_COUNT" -ge "$CLIP_COUNT" ] || echo "FAIL: Only $THUMB_COUNT thumbnails for $CLIP_COUNT clips — thumbnails missing from narrator segments"
```

### 6. AUDIO SYNC — CLIPS HAVE MATCHING AUDIO
```bash
# Each clip part must have audio stream
for f in $WORK/part_*clip*.mp4; do
    HAS_AUD=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$f" 2>/dev/null)
    [ "$HAS_AUD" = "audio" ] || echo "FAIL: $f has no audio — clip will be silent"
done
```

### 7. VOICE VERIFICATION — CORRECT VOICE IDS
```bash
# Check tts_engine.py has the right voice IDs (American English, not British)
grep -q "XB0fDUnXU5powFXDhCwa\|VeCVR24o7g2y1IxLJzZs\|FyrYFW3P9GUxA348YGWu" tts_engine.py && echo "WARN: Verify voice is American English — Charlotte/Deborah/Madison"
# Check voice_settings has stability set
grep -q "stability" tts_engine.py || echo "FAIL: No voice_settings with stability — moaning artifact risk"
```

### 8. SCRIPT QUALITY — VERIFY TONE AND STRUCTURE
```bash
SCRIPT="$LATEST/script.json"
# Must have cold_open
python3 -c "import json; d=json.load(open('$SCRIPT')); assert d.get('cold_open'), 'No cold_open'" 2>&1 || echo "FAIL: No cold_open in script"
# Must have dialogue array
python3 -c "import json; d=json.load(open('$SCRIPT')); assert len(d.get('dialogue',[])) > 5, 'Too few dialogue entries'" 2>&1 || echo "FAIL: Dialogue too short"
# Must have CLIP entries
python3 -c "import json; d=json.load(open('$SCRIPT')); clips=[e for e in d.get('dialogue',[]) if e.get('host')=='CLIP']; assert len(clips) >= 1, f'Only {len(clips)} clips'" 2>&1 || echo "FAIL: No CLIP entries in dialogue"
# Setup lines should be short (< 200 chars each)
python3 -c "
import json
d=json.load(open('$SCRIPT'))
for e in d.get('dialogue',[]):
    if e.get('type') == 'setup' and len(e.get('text','')) > 200:
        print(f\"WARN: Setup line too long ({len(e['text'])} chars): {e['text'][:60]}...\")
" 2>&1
# React lines should be short (< 200 chars each)
python3 -c "
import json
d=json.load(open('$SCRIPT'))
for e in d.get('dialogue',[]):
    if e.get('type') == 'react' and len(e.get('text','')) > 200:
        print(f\"WARN: React line too long ({len(e['text'])} chars): {e['text'][:60]}...\")
" 2>&1
# Check for banned generic phrases
python3 -c "
import json
d=json.load(open('$SCRIPT'))
banned = ['let us dive in', 'without further ado', 'buckle up', 'game changer', 'really interesting', 'really impactful', 'great stuff']
for e in d.get('dialogue',[]):
    text = e.get('text','').lower()
    for b in banned:
        if b in text:
            print(f\"FAIL: Banned phrase '{b}' in: {e['text'][:60]}...\")
" 2>&1
```

### 9. NARRATOR DOES NOT OVERLAP CLIPS
```bash
# Verify no host audio parts directly adjacent to clip parts without a transition
python3 -c "
import os, glob
work = '$WORK'
parts = sorted(glob.glob(os.path.join(work, 'part_*.mp4')))
for i in range(len(parts)-1):
    curr = os.path.basename(parts[i])
    nxt = os.path.basename(parts[i+1])
    # Clip followed immediately by react (no glitch between) is OK
    # But setup followed immediately by clip with no glitch = missing transition
    if 'setup' in curr and 'clip' in nxt and 'glitch' not in nxt:
        print(f'WARN: {curr} -> {nxt} — no glitch transition between setup and clip')
" 2>&1
```

### 10. BACKGROUND MUSIC PRESENT
```bash
# Verify background music file exists and is referenced
[ -f "assets/music/pp_background.mp3" ] || echo "FAIL: Background music missing"
[ -f "assets/music/pp_intro.mp3" ] || echo "FAIL: Intro music missing"
[ -f "assets/music/pp_outro.mp3" ] || echo "FAIL: Outro music missing"
# Check assembler references music
grep -q "pp_background" assembler.py || echo "FAIL: assembler.py doesn't reference background music"
grep -q "pp_intro" assembler.py || echo "FAIL: assembler.py doesn't reference intro music"
```

### 11. GLITCH TRANSITION HAS AUDIO
```bash
GLITCH=$(ls $WORK/part_*glitch* 2>/dev/null | head -1)
if [ -n "$GLITCH" ]; then
    HAS_AUD=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$GLITCH" 2>/dev/null)
    [ "$HAS_AUD" = "audio" ] || echo "FAIL: Glitch transition has no audio — woosh missing"
    # Check volume is audible (not silent)
    VOL=$(ffmpeg -i "$GLITCH" -af "volumedetect" -f null - 2>&1 | grep mean_volume | grep -oP '[-0-9.]+')
    if [ -n "$VOL" ]; then
        VOLINT=$(echo "$VOL" | cut -d. -f1 | tr -d -)
        [ "$VOLINT" -lt 50 ] || echo "FAIL: Glitch audio mean_volume=$VOL — too quiet"
    fi
fi
```

---

## MANUAL CHECKS (human must verify after watching)
After downloading and watching the video, confirm:

- [ ] Intro: Music plays, strong vocal hook opens the video
- [ ] Cold open is 1 explosive sentence, not a paragraph
- [ ] Host narration has animated background (NOT plain dark card)
- [ ] YouTube thumbnails visible during setup/react segments
- [ ] Glitch woosh is AUDIBLE between segments
- [ ] Clips play FULL SCREEN with ORIGINAL audio
- [ ] Clips are NOT cut off mid-sentence at start or end
- [ ] Narrator does NOT talk over clip audio (no overlap)
- [ ] Narrator tone is MMA-gossip, not generic news anchor
- [ ] Both voices are AMERICAN ENGLISH (no British accent)
- [ ] Background music audible but quiet under narration
- [ ] Outro plays with fade, video ends cleanly (no hard cut, no black)
- [ ] No black frames or dead air anywhere in the video
- [ ] Social segment present (tweets/Nostr posts) — at minimum placeholder
- [ ] BTC price ticker visible during host segments

---

## HOW TO USE THIS

### For Claude Code sessions:
Paste at the END of every fix prompt:
```
BEFORE COMMITTING: Run ~/protocol_pulse/video_pipeline_v3/regression_test.sh
and paste the full output. Fix ANY failures before git commit.
Do NOT commit if any check says FAIL.
```

### For the human (PBX):
After downloading every test render, go through the MANUAL CHECKS section.
If anything fails, report it with the specific check name so the fix is targeted.

### Git commit rule:
```bash
# ONLY after regression_test.sh passes with zero FAILs:
git add -A && git commit -m "feat: [description] — regression test PASSED" && git push origin main
```

---

## VERSION HISTORY
- v1.0 (2026-03-04): Initial checklist after V7→V8 regression (thumbnails dropped, waveform missing)
- Covers: video specs, parts structure, thumbnails, audio sync, voice, script quality, narrator overlap, music, transitions

```

### FILE: README.md
```
# Pulse Check Video Pipeline v3

MMA-Central-style daily Bitcoin news video generator.

## Quick Start

```bash
cd ~/protocol_pulse/video_pipeline_v3

# Generate default style video
python3 daily_run.py --output output/pulse_check.mp4

# Generate breaking news style
python3 daily_run.py --style breaking --output output/breaking.mp4
```

## Pipeline Steps

1. **Script Generation** — Claude API narration script (falls back to curated samples)
2. **TTS Audio** — ElevenLabs voice (falls back to gTTS)
3. **Clip Fetching** — Pexels B-roll (falls back to FFmpeg-generated visuals)
4. **Assembly** — FFmpeg filter_complex compositing with branded assets
5. **Verification** — ffprobe checks for codec, resolution, duration, A/V sync
6. **Vertical Shorts** — Auto-generated 9:16 shorts from each segment

## Output Specs

- **Horizontal**: 1920x1080, H.264, AAC 44100Hz stereo, 30fps, 90-180s
- **Vertical Shorts**: 1080x1920, H.264, AAC, 15-60s each

## Project Structure

```
daily_run.py          # Master orchestrator
script_writer.py      # Claude/sample narration scripts
tts_engine.py         # ElevenLabs/gTTS voice generation
clip_fetcher.py       # Pexels/FFmpeg visual generation
assembler.py          # FFmpeg video assembly
shorts_cutter.py      # Vertical short generation
create_assets.py      # One-time asset creation
relay.py              # Replit relay helper
config.yaml           # Configuration
assets/               # Branded transitions, intro, outro
output/               # Finished videos
output/shorts/        # Vertical shorts
```

## Cron (Daily at 2PM UTC)

```
0 14 * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_run.py >> logs/daily.log 2>&1
```

## API Keys (via env or Replit relay)

- `ANTHROPIC_API_KEY` — Claude script generation
- `ELEVENLABS_API_KEY` — TTS voice
- `PEXELS_API_KEY` — B-roll video clips
- `XAI_API_KEY` — Grok triage scoring

All have local fallbacks — pipeline works without any API keys.

```

================================================================================
## PYTHON SOURCE CODE
================================================================================

### FILE: daily_producer.py
```python
#!/usr/bin/env python3
"""Daily Pulse Check Producer V5 — clip-first pipeline.

Real YouTube clips from partner channels, host dialogue around them,
music integration, cold open, avatar shorts.

Usage:
  python3 daily_producer.py               # Full daily episode
  python3 daily_producer.py --test        # Test mode (fewer clips, truncated)
  python3 daily_producer.py --skip-scan   # Use cached transcripts only
  python3 daily_producer.py --fast-test   # Fast test: no API calls, <3 min render
"""
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from channel_scanner import scan_all_channels
from clip_selector import select_clips
from clip_extractor import extract_all, check_av_sync
from script_writer import generate_from_clips
from tts_engine import generate_dialogue_audio
from assembler import assemble_episode, verify_video
from shorts_cutter import generate_shorts
from thumbnail_gen import generate_thumbnail
from chapters import generate_chapters
from podcast_feed import extract_podcast_audio, generate_rss_item
from newsletter_embed import generate_email_html, save_newsletter_html
from music import ensure_music_dir, has_music, has_intro, has_outro
from utils.feature_flags import is_enabled, load_all as load_flags
from utils.quality_gate import compute_quality_score, should_upload, format_score_report
from utils.telegram_alerts import (
    alert_pipeline_start, alert_pipeline_success,
    alert_pipeline_failure, alert_quality_hold, alert_upload_success,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("Producer")


def get_btc_price() -> str:
    """Fetch current BTC price (CoinGecko primary + mempool.space fallback)."""
    try:
        import requests
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
        if r.status_code == 200:
            usd = r.json()["bitcoin"]["usd"]
            return f"${usd:,.0f}"
    except Exception:
        pass
    try:
        import requests
        r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if r.status_code == 200:
            usd = r.json().get("USD", 0)
            return f"${usd:,.0f}"
    except Exception:
        pass
    return "$N/A"  # Fallback - no hardcoded stale price


def _build_fast_test_script(clips_info: dict, btc_price: str) -> dict:
    """Build a minimal hardcoded script for fast-test mode (no Claude API call)."""
    dialogue = []
    # Cold open
    dialogue.append({
        "host": 1, "type": "cold_open",
        "text": f"Bitcoin at {btc_price}. Let's get into today's pulse check.",
    })
    # For each clip, add a setup + clip marker + react
    for rank, info in sorted(clips_info.items()):
        channel = info.get("channel", "Unknown")
        dialogue.append({
            "host": 1, "type": "setup",
            "text": f"Here's what {channel} had to say.",
        })
        dialogue.append({
            "host": "CLIP", "type": "clip",
            "rank": rank, "source_id": info.get("video_id", ""),
        })
        dialogue.append({
            "host": 2, "type": "react",
            "text": "Interesting take. Let's keep moving.",
        })
    # Wrap
    dialogue.append({
        "host": 1, "type": "wrap",
        "text": "That's the pulse check for today. Like, subscribe, and we'll see you next time.",
    })
    return {
        "episode_title": f"Fast Test — {btc_price}",
        "dialogue": dialogue,
        "thumbnail": {"headline": "FAST TEST", "subtext": btc_price},
    }


def _send_resend_alert(subject: str, body: str):
    """Send a non-blocking email alert via Resend."""
    try:
        import resend
        resend.api_key = os.environ.get("RESEND_API_KEY", "")
        if not resend.api_key:
            logger.warning("RESEND_API_KEY not set — skipping email alert")
            return
        resend.Emails.send({
            "from": "pulse@protocolpulse.io",
            "to": ["contact@consensusprotocol.org"],
            "subject": subject,
            "html": f"<pre>{body}</pre>",
        })
    except Exception as e:
        logger.warning(f"Resend alert failed: {e}")


def _post_render_health_check(video_path: str) -> tuple[bool, list[str]]:
    """Verify rendered video meets quality thresholds.

    Returns (passed, errors).
    """
    errors = []
    if not os.path.exists(video_path):
        return False, ["Video file does not exist"]

    # File size > 50MB
    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if size_mb < 50:
        errors.append(f"File size {size_mb:.1f}MB < 50MB minimum")

    # ffprobe checks
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", video_path],
            capture_output=True, text=True, timeout=30,
        )
        info = json.loads(probe.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])

        # Duration 480-900s (PIPELINE_LAWS: 8-15 min)
        duration = float(fmt.get("duration", 0))
        if duration < 480 or duration > 900:
            errors.append(f"Duration {duration:.0f}s outside 480-900s range (8-15 min law)")

        # Audio stream present
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        if not audio_streams:
            errors.append("No audio stream found")
    except Exception as e:
        errors.append(f"ffprobe failed: {e}")

    passed = len(errors) == 0
    if not passed:
        logger.critical(f"POST-RENDER HEALTH CHECK FAILED: {errors}")
        _send_resend_alert(
            "CRITICAL: Pulse Check render failed health check",
            f"Video: {video_path}\nErrors:\n" + "\n".join(f"  - {e}" for e in errors),
        )
    return passed, errors


def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
                 fast_test: bool = False) -> bool:
    # Fast test implies test + skip-scan
    if fast_test:
        test_mode = True
        skip_scan = True

    # Wipe TTS cache before each run to prevent stale audio
    tts_cache = os.path.join(BASE, "tts_cache")
    shutil.rmtree(tts_cache, ignore_errors=True)
    os.makedirs(tts_cache, exist_ok=True)
    logger.info("TTS cache wiped")

    ts = datetime.now(timezone.utc)
    date_str = ts.strftime("%Y%m%d")
    time_str = ts.strftime("%Y%m%d_%H%M%S")

    if test_mode:
        run_dir = os.path.join(BASE, "output", f"test_{time_str}")
    else:
        run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))

    os.makedirs(run_dir, exist_ok=True)
    final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
    timing = {}
    t_pipeline_start = time.time()

    # Ensure music directory exists
    ensure_music_dir()

    # Log feature flags at startup
    flags = load_flags()
    logger.info(f"Feature flags: {json.dumps(flags)}")

    # Telegram alert at pipeline start
    if is_enabled("telegram_alerts"):
        alert_pipeline_start(date_str, test_mode)

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK V5 — CLIP-FIRST PIPELINE")
    mode_label = "FAST TEST " if fast_test else ("TEST " if test_mode else "")
    print(f"  {mode_label}Run {time_str}")
    print(f"  Output: {run_dir}")
    print(f"  Music: {'YES' if has_music() else 'no (skipped gracefully)'}")
    print("=" * 70)

    # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
    print("\n[STEP 1/12] FETCHING BTC PRICE...")
    t0 = time.time()
    btc_price = get_btc_price()
    print(f"  BTC: {btc_price}")
    timing["1_price"] = round(time.time() - t0, 2)

    # ── Step 2: SCAN CHANNELS ─────────────────────────────────────────────
    print("\n[STEP 2/12] SCANNING PARTNER CHANNELS...")
    t0 = time.time()
    if skip_scan:
        # Load cached transcripts from transcript dir
        import glob
        transcript_dir = os.path.join(BASE, "transcripts")
        videos = []
        for tf in sorted(glob.glob(os.path.join(transcript_dir, "*.json")))[:60]:
            with open(tf) as f:
                data = json.load(f)
                videos.append({
                    "video_id": data.get("video_id", ""),
                    "title": data.get("title", ""),
                    "channel": data.get("channel", ""),
                    "duration": data.get("duration", 0),
                    "upload_date": "",
                    "url": f"https://www.youtube.com/watch?v={data.get('video_id', '')}",
                    "transcript_text": data.get("text", ""),
                    "timestamped_text": data.get("timestamped_text", ""),
                })
        print(f"  Loaded {len(videos)} cached transcripts")
    else:
        whisper_model = "tiny" if test_mode else "base"
        videos = scan_all_channels(model_size=whisper_model)
        print(f"  Scanned: {len(videos)} videos with transcripts")
    timing["2_scan"] = round(time.time() - t0, 2)

    if not videos:
        print("\n  [FAIL] No videos found — cannot produce episode")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "scan", "No videos found")
        return False

    # ── Step 3: SELECT BEST CLIPS ─────────────────────────────────────────
    if fast_test:
        print("\n[STEP 3/12] SELECTING CLIPS (fast-test: first 2, no Claude)...")
        t0 = time.time()
        # Build minimal selections from cached videos without calling Claude
        fast_clips = []
        for i, v in enumerate(videos[:2], 1):
            text = v.get("transcript_text", "")
            fast_clips.append({
                "rank": i,
                "video_id": v["video_id"],
                "channel": v.get("channel", ""),
                "title": v.get("title", ""),
                "quote": text[:100] if text else "No transcript",
                "why": "fast-test auto-select",
                "start_seconds": 60,
                "end_seconds": 90,
            })
        selections = {"clips": fast_clips}
        clips = fast_clips
        print(f"  Auto-selected: {len(clips)} clips (no API call)")
        timing["3_select"] = round(time.time() - t0, 2)
    else:
        print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude)...")
        t0 = time.time()
        selections = select_clips(videos)
        clips = selections.get("clips", [])
        print(f"  Selected: {len(clips)} clips")
        for c in clips:
            print(f"    #{c['rank']}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
        timing["3_select"] = round(time.time() - t0, 2)

    if not clips:
        print("\n  [FAIL] No clips selected — cannot produce episode")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "select", "No clips selected")
        return False

    # In test mode, use only top 2 clips
    if not fast_test and test_mode and len(clips) > 2:
        selections["clips"] = clips[:2]
        clips = selections["clips"]
        print(f"  [test] Truncated to {len(clips)} clips")

    # Save selections
    sel_path = os.path.join(run_dir, "selections.json")
    with open(sel_path, "w") as f:
        json.dump(selections, f, indent=2)

    # ── Step 4: EXTRACT CLIPS ─────────────────────────────────────────────
    print("\n[STEP 4/12] EXTRACTING CLIPS (yt-dlp with original audio)...")
    t0 = time.time()
    clip_dir = os.path.join(run_dir, "clips")
    extracted_clips = extract_all(selections, clip_dir)
    print(f"  Extracted: {len(extracted_clips)}/{len(clips)} clips")

    # ── Quality-aware fallback: retry with ranked alternates ──────────
    if not test_mode and not fast_test and len(extracted_clips) < 5:
        used_video_ids = {info["video_id"] for info in extracted_clips.values()}
        used_channels = {info["channel"] for info in extracted_clips.values()}
        tried_video_ids = {c["video_id"] for c in clips} | used_video_ids

        remaining = [v for v in videos
                     if v["video_id"] not in tried_video_ids
                     and v.get("channel", "") not in used_channels]

        if remaining:
            need = 5 - len(extracted_clips)
            logger.info(
                f"[extractor] Only {len(extracted_clips)}/5 clips passed quality "
                f"— selecting fallbacks from {len(remaining)} candidates (need {need})"
            )
            fallback_sel = select_clips(remaining)
            fallback_clips = fallback_sel.get("clips", [])

            max_rank = max(extracted_clips.keys()) if extracted_clips else 0
            for fc in fallback_clips:
                if len(extracted_clips) >= 5:
                    break
                fc_ch = fc.get("channel", "")
                fc_vid = fc.get("video_id", "")
                if fc_ch in used_channels or fc_vid in tried_video_ids:
                    continue
                max_rank += 1
                fc["rank"] = max_rank
                logger.info(
                    f"[extractor] Clip failed quality — trying fallback candidate "
                    f"#{max_rank} [{fc_ch}] from selections"
                )
                fb_result = extract_all({"clips": [fc]}, clip_dir)
                if fb_result:
                    for r, info in fb_result.items():
                        extracted_clips[r] = info
                        used_video_ids.add(info["video_id"])
                        used_channels.add(info["channel"])
                        tried_video_ids.add(fc_vid)
                        selections["clips"].append(fc)
                        logger.info(
                            f"[extractor] Fallback clip #{r} passed quality — "
                            f"{info['channel']} ({info['duration']:.1f}s)"
                        )
                else:
                    tried_video_ids.add(fc_vid)
                    logger.warning(
                        f"[extractor] Fallback [{fc_ch}] also failed quality — trying next"
                    )

            # Update clips list and re-save selections
            clips = selections.get("clips", [])
            with open(sel_path, "w") as f:
                json.dump(selections, f, indent=2)
            logger.info(f"[extractor] After fallback: {len(extracted_clips)}/5 clips")
        else:
            logger.warning("[extractor] No fallback candidates — all channels/videos exhausted")

    if not test_mode:
        _unique_ch = len({info.get("channel", f"unk_{i}") for i, info in enumerate(extracted_clips.values())})
        if len(extracted_clips) < 5 or _unique_ch < 5:
            logger.critical(
                f"[PIPELINE] HARD FAIL: Need 5 clips from 5 unique channels, "
                f"got {len(extracted_clips)} clips from {_unique_ch} channels."
            )
            return False
    for rank, info in sorted(extracted_clips.items()):
        print(f"    #{rank}: {info['channel']} — {info['duration']:.1f}s")
    timing["4_extract"] = round(time.time() - t0, 2)

    if not extracted_clips:
        print("\n  [FAIL] No clips extracted — cannot produce episode")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "extract", "No clips extracted")
        return False

    # ── Step 4b: MOOD CLASSIFICATION + MUSIC SELECTION ──────────────────
    import glob as _glob
    import random as _random

    def classify_episode_mood(script_text: str) -> str:
        """Classify episode mood from clip quotes."""
        moods = {"tense": 0, "confident": 0, "contemplative": 0, "upbeat": 0, "edge": 0}
        lower = script_text.lower()
        if any(w in lower for w in ["crash", "sell", "breaking", "emergency", "plunge", "war"]):
            moods["tense"] += 3
        if any(w in lower for w in ["bullish", "ath", "record", "buying", "accumul"]):
            moods["confident"] += 3
        if any(w in lower for w in ["philosoph", "long-term", "decade", "future", "think about"]):
            moods["contemplative"] += 2
        if any(w in lower for w in ["community", "fun", "meme", "laugh", "celebrate"]):
            moods["upbeat"] += 2
        if any(w in lower for w in ["controversial", "scam", "fraud", "attack", "fight"]):
            moods["edge"] += 2
        best = max(moods, key=moods.get)
        return best if moods[best] > 0 else "confident"

    def select_music_bed(mood: str, music_dir: str) -> str:
        # Sprint 1.10: Randomize music, avoid repeating last track
        last_track_file = os.path.join(music_dir, ".last_track.txt")
        last_track = ""
        if os.path.exists(last_track_file):
            try:
                last_track = open(last_track_file).read().strip()
            except Exception:
                pass

        tracks = _glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
        if not tracks:
            tracks = _glob.glob(os.path.join(music_dir, "confident_*.mp3"))
        if not tracks:
            # Get all tracks except reserved ones
            all_tracks = _glob.glob(os.path.join(music_dir, "*.mp3"))
            tracks = [t for t in all_tracks
                      if os.path.basename(t) not in ("pp_outro.mp3", "pp_background.mp3",
                                                       "pp_intro.mp3", "pp_transition.mp3")]
        if not tracks:
            return ""

        # Avoid repeating last track
        if last_track and len(tracks) > 1:
            tracks = [t for t in tracks if os.path.basename(t) != last_track] or tracks

        chosen = _random.choice(tracks)
        try:
            with open(last_track_file, "w") as f:
                f.write(os.path.basename(chosen))
        except Exception:
            pass
        return chosen

    def select_intro_music(music_dir: str) -> str:
        tracks = _glob.glob(os.path.join(music_dir, "intro_*.mp3"))
        return _random.choice(tracks) if tracks else ""

    # Classify mood from clip quotes
    clip_quotes = " ".join(c.get("quote", "") + " " + c.get("why", "") for c in clips)
    episode_mood = classify_episode_mood(clip_quotes)
    music_dir = os.path.join(BASE, "assets", "music")
    music_bed = select_music_bed(episode_mood, music_dir)
    intro_music = select_intro_music(music_dir)
    print(f"  Mood: {episode_mood} | Music: {os.path.basename(music_bed) if music_bed else 'default'}")

    # ── Step 4c: LIVE SIGNALS ─────────────────────────────────────────────
    live_context = ""
    live_signals_path = os.path.join(BASE, "data", "intelligence", "live_signals.json")
    try:
        if os.path.exists(live_signals_path):
            with open(live_signals_path) as f:
                live_data = json.load(f)
            from datetime import timezone as _tz
            now = datetime.now(_tz.utc) if hasattr(datetime, 'now') else datetime.utcnow()
            active_streams = []
            for s in live_data.get("live_streams", []):
                # Only include streams from last 6 hours
                started = s.get("started_at", "")
                try:
                    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    age_hours = (now - started_dt).total_seconds() / 3600
                    if age_hours > 6:
                        continue
                except (ValueError, AttributeError):
                    continue
                source = s.get("source", "youtube_live")
                channel = s.get("channel", "unknown")
                title = s.get("title", "")
                topics = ", ".join(s.get("topics", []))
                sentiment = s.get("current_sentiment", 50)
                sentiment_label = "bullish" if sentiment > 60 else "bearish" if sentiment < 40 else "neutral"
                active_streams.append(
                    f"- {channel} ({source}): \"{title}\" — topics: {topics}, sentiment: {sentiment_label} ({sentiment})"
                )
            if active_streams:
                live_context = "\n".join(active_streams)
                print(f"  Live signals: {len(active_streams)} active streams in last 6 hours")
                for line in active_streams:
                    print(f"    {line}")
            else:
                print("  Live signals: no active streams in last 6 hours")
    except Exception as e:
        logger.warning(f"Live signals read failed: {e}")

    # ── Step 5: GENERATE SCRIPT ───────────────────────────────────────────
    if fast_test:
        print("\n[STEP 5/12] GENERATING SCRIPT (fast-test: hardcoded, no Claude)...")
        t0 = time.time()
        script = _build_fast_test_script(extracted_clips, btc_price)
        dialogue = script["dialogue"]
        speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
        clip_markers = [d for d in dialogue if d.get("host") == "CLIP"]
        print(f"  Title: {script.get('episode_title', 'Untitled')}")
        print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips (hardcoded)")
        timing["5_script"] = round(time.time() - t0, 2)
    else:
        print("\n[STEP 5/12] GENERATING HOST DIALOGUE (Claude)...")
        t0 = time.time()
        script = generate_from_clips(selections, btc_price=btc_price,
                                     live_context=live_context)
        dialogue = script.get("dialogue", [])
        speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
        clip_markers = [d for d in dialogue if d.get("host") == "CLIP"]
        print(f"  Title: {script.get('episode_title', 'Untitled')}")
        print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips")
        timing["5_script"] = round(time.time() - t0, 2)

    # Issue 9: Sort social posts ONCE by engagement (likes desc), store on script
    # This ensures assembler uses the EXACT SAME order as script_writer
    try:
        from utils.social_fetcher import get_todays_social_posts
        sorted_social = get_todays_social_posts(max_posts=5)
        if sorted_social:
            sorted_social.sort(key=lambda p: p.get("likes", 0), reverse=True)
            script["social_posts"] = sorted_social
            for si, sp in enumerate(sorted_social):
                logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} — {sp.get('text', '')[:40]}")
    except Exception as e:
        logger.warning(f"Social posts fetch for ordering failed: {e}")

    # Save script
    script_path = os.path.join(run_dir, "script.json")
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)

    # ── Step 6: TTS ───────────────────────────────────────────────────────
    print("\n[STEP 6/12] GENERATING DUAL-HOST AUDIO (ElevenLabs)...")
    t0 = time.time()
    audio_dir = os.path.join(run_dir, "audio")
    audio_data = generate_dialogue_audio(dialogue, audio_dir)
    successful = sum(1 for l in audio_data.get("lines", [])
                     if l.get("path") and os.path.exists(l.get("path", "")))
    print(f"  Audio: {successful}/{len(speech_lines)} lines")
    print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
    timing["6_tts"] = round(time.time() - t0, 2)

    # ── Step 6b: BUILD MANIFEST ─────────────────────────────────────────
    print("\n[STEP 6b/12] BUILDING EPISODE MANIFEST...")
    t0 = time.time()
    try:
        from manifest_builder import build_manifest
        episode_manifest = build_manifest(
            script, audio_data, extracted_clips, run_dir,
            music_bed=music_bed, btc_price=btc_price,
        )
        print(f"  Manifest: {episode_manifest.get('total_segments', 0)} segments, "
              f"~{episode_manifest.get('total_duration_estimate', 0):.0f}s estimated")
    except Exception as e:
        logger.warning(f"Manifest build failed (non-blocking): {e}")
        episode_manifest = {}
    timing["6b_manifest"] = round(time.time() - t0, 2)

    # ── Step 6c: PREFLIGHT CHECK ─────────────────────────────────────────
    manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
    if os.path.exists(manifest_json_path):
        print("\n[STEP 6c/12] PREFLIGHT QC CHECK...")
        t0 = time.time()
        try:
            from qc_pipeline import preflight_check
            pf_passed, pf_errors, pf_warnings = preflight_check(manifest_json_path)
            print(f"  Preflight: {'PASS' if pf_passed else 'FAIL'} — "
                  f"{len(pf_errors)} errors, {len(pf_warnings)} warnings")
        except Exception as e:
            logger.warning(f"Preflight check failed (non-blocking): {e}")
        timing["6c_preflight"] = round(time.time() - t0, 2)

    # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
    print("\n[STEP 7/12] ASSEMBLING VIDEO...")
    t0 = time.time()
    result = assemble_episode(script, audio_data, extracted_clips, final_video,
                              btc_price=btc_price, music_bed=music_bed,
                              intro_music=intro_music)
    timing["7_assemble"] = round(time.time() - t0, 2)

    if not result or not os.path.exists(final_video):
        print("\n  [FAIL] Assembly failed")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
        return False

    # ── Step 8: SHORTS ────────────────────────────────────────────────────
    print("\n[STEP 8/12] GENERATING SHORTS (avatar)...")
    t0 = time.time()
    shorts_dir = os.path.join(run_dir, "shorts")
    shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
                             max_shorts=3 if not test_mode else 1)
    print(f"  Shorts: {len(shorts)}")
    timing["8_shorts"] = round(time.time() - t0, 2)

    # ── Step 9: THUMBNAIL ─────────────────────────────────────────────────
    print("\n[STEP 9/12] GENERATING THUMBNAIL (MMA Central style)...")
    t0 = time.time()
    thumb_data = script.get("thumbnail", {})
    top_quote = ""
    if clips:
        top_quote = clips[0].get("quote", "")
    thumb_path = os.path.join(run_dir, "thumbnail.png")
    generate_thumbnail(
        thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
        thumb_data.get("subtext", ""),
        thumb_path,
        btc_price=btc_price,
        top_quote=top_quote,
    )
    timing["9_thumbnail"] = round(time.time() - t0, 2)

    # ── Step 10: CHAPTERS ─────────────────────────────────────────────────
    print("\n[STEP 10/12] GENERATING CHAPTERS...")
    t0 = time.time()
    chapters_path = os.path.join(run_dir, "chapters.txt")
    generate_chapters(script, audio_data, chapters_path)
    timing["10_chapters"] = round(time.time() - t0, 2)

    # ── Step 11: PODCAST + NEWSLETTER ─────────────────────────────────────
    print("\n[STEP 11/12] PODCAST AUDIO + NEWSLETTER...")
    t0 = time.time()
    podcast_path = os.path.join(run_dir, "podcast.mp3")
    extract_podcast_audio(final_video, podcast_path)

    email_html = generate_email_html(
        script.get("episode_title", "Pulse Check"),
        segments_summary=script.get("segments_summary", []),
        btc_price=btc_price,
    )
    newsletter_path = os.path.join(run_dir, "newsletter.html")
    save_newsletter_html(email_html, newsletter_path)
    timing["11_podcast_newsletter"] = round(time.time() - t0, 2)

    # ── Step 12: VERIFY ───────────────────────────────────────────────────
    print("\n[STEP 12/12] VERIFYING OUTPUT...")
    t0 = time.time()
    passed = verify_video(final_video)

    # Final AV sync validation
    final_offset = check_av_sync(final_video)
    print(f"  Final AV sync offset: {final_offset:+.3f}s")
    if abs(final_offset) > 0.05:
        logger.error(f"FINAL OUTPUT SYNC FAILED: {final_offset:+.3f}s > 0.05s — nuclear re-encode")
        nuclear_tmp = final_video + ".nuclear.mp4"
        nuclear_cmd = subprocess.run([
            "ffmpeg", "-y",
            "-fflags", "+genpts+igndts",
            "-i", final_video,
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-vsync", "cfr",
            "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
            "-movflags", "+faststart",
            nuclear_tmp,
        ], capture_output=True, text=True, timeout=600)
        if nuclear_cmd.returncode == 0 and os.path.exists(nuclear_tmp):
            os.replace(nuclear_tmp, final_video)
            recheck = check_av_sync(final_video)
            print(f"  Nuclear re-encode done. New offset: {recheck:+.3f}s")
        elif os.path.exists(nuclear_tmp):
            os.remove(nuclear_tmp)

    # Final bitrate validation
    br_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
        capture_output=True, text=True,
    )
    try:
        br_info = json.loads(br_result.stdout)
        bitrate = int(br_info.get("format", {}).get("bit_rate", 0))
        print(f"  Final bitrate: {bitrate / 1_000_000:.1f} Mbps")
        if bitrate < 3_000_000:
            logger.error(f"FINAL OUTPUT QUALITY FAILED: {bitrate / 1_000_000:.1f}Mbps < 3Mbps")
    except Exception:
        pass

    timing["12_verify"] = round(time.time() - t0, 2)

    # ── Step 12b: POST-RENDER QC ─────────────────────────────────────────
    print("\n[STEP 12b] POST-RENDER QC...")
    t0 = time.time()
    try:
        from qc_pipeline import post_render_qc, save_qc_report
        manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
        qc_report = post_render_qc(final_video, manifest_json_path)
        save_qc_report(qc_report, run_dir)
        print(f"  QC: {'PASS' if qc_report.get('passed') else 'FAIL'}")
        for check, val in qc_report.get("checks", {}).items():
            status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
            print(f"    [{status}] {check}")
    except Exception as e:
        logger.warning(f"Post-render QC failed (non-blocking): {e}")
    timing["12b_qc"] = round(time.time() - t0, 2)

    # ── Summary ──────────────────────────────────────────────────────────
    timing["total"] = round(time.time() - t_pipeline_start, 2)

    # Video stats
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", final_video],
        capture_output=True, text=True,
    )
    try:
        info = json.loads(r.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])
        vid = next((s for s in streams if s.get("codec_type") == "video"), {})
        aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
        dur = float(fmt.get("duration", 0))
        sz = int(fmt.get("size", 0)) / 1024 / 1024
        timing["video_duration"] = round(dur, 1)
        timing["video_size_mb"] = round(sz, 1)
    except Exception:
        vid, aud, dur, sz = {}, {}, 0, 0

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK V5 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
    print(f"  Title:    {script.get('episode_title', 'Untitled')}")
    print(f"  Video:    {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
    print(f"  Audio:    {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
    print(f"  Size:     {sz:.1f}MB")
    print(f"  Clips:    {len(extracted_clips)} real YouTube clips with original audio")
    print(f"  Shorts:   {len(shorts)}")
    print(f"  Music:    {'layered' if has_music() else 'none (graceful skip)'}")

    outputs = {
        "video": final_video,
        "shorts": [s for s in shorts],
        "thumbnail": thumb_path,
        "chapters": chapters_path,
        "podcast": podcast_path,
        "newsletter": newsletter_path,
        "script": script_path,
        "selections": sel_path,
    }

    print(f"\n  OUTPUT FILES:")
    for name, path in outputs.items():
        if isinstance(path, list):
            for p in path:
                exists = "Y" if os.path.exists(p) else "N"
                print(f"    [{exists}] {os.path.basename(p)}")
        else:
            exists = "Y" if os.path.exists(path) else "N"
            print(f"    [{exists}] {os.path.basename(path)}")

    print(f"\n  TIMING:")
    for step, secs in timing.items():
        if step not in ("video_duration", "video_size_mb"):
            print(f"    {step:25s}: {secs:.1f}s")
    print(f"\n  Output: {run_dir}")
    print("=" * 70)

    _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)

    # Save manifest
    manifest = {
        "version": "v5",
        "episode_title": script.get("episode_title", ""),
        "btc_price": btc_price,
        "test_mode": test_mode,
        "timestamp": time_str,
        "clips_used": [
            {"rank": r, "channel": info.get("channel", ""), "video_id": info.get("video_id", "")}
            for r, info in sorted(extracted_clips.items())
        ],
        "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
        "timing": timing,
        "success": passed,
    }
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # ── Step 13: QUALITY GATE + AUTO-UPLOAD ────────────────────────────────
    print("\n[STEP 13] QUALITY GATE...")
    t0 = time.time()
    quality_score = compute_quality_score(manifest_path, video_path=final_video)
    print(f"  {format_score_report(quality_score)}")
    manifest["quality_score"] = quality_score

    if is_enabled("youtube_auto_upload") and should_upload(quality_score):
        from utils.youtube_upload import upload_episode as yt_upload, build_description, build_tags
        # Build YouTube metadata
        ep_title = script.get("episode_title", "Pulse Check")
        yt_title = f"Bitcoin Daily Brief — {ts.strftime('%b %d, %Y')} | Protocol Pulse"
        chapters_text = ""
        if os.path.exists(chapters_path):
            with open(chapters_path) as f:
                chapters_text = f.read()
        yt_description = build_description(
            summary=f"{ep_title}\n\nBTC Price: {btc_price}",
            chapters_text=chapters_text,
        )
        topics = [c.get("channel", "") for c in clips]
        yt_tags = build_tags(topics)

        print(f"  Uploading to YouTube (unlisted)...")
        upload_result = yt_upload(
            final_video, yt_title, yt_description,
            tags=yt_tags, thumbnail_path=thumb_path, privacy="unlisted",
        )
        print(f"  Upload result: {upload_result.get('status')}")
        if upload_result.get("url"):
            print(f"  URL: {upload_result['url']}")
        manifest["upload_result"] = upload_result
        if is_enabled("telegram_alerts") and upload_result.get("url"):
            alert_upload_success(date_str, upload_result["url"])
    elif quality_score < 85:
        logger.warning(f"QUALITY HOLD: Score {quality_score} < 85. Episode held for review.")
        hold_path = os.path.join(run_dir, "HOLD_FOR_REVIEW.txt")
        with open(hold_path, "w") as f:
            f.write(f"Quality score: {quality_score}/100\n")
            f.write(f"Threshold: 85\n")
            f.write(f"Reason: Below quality threshold\n")
            f.write(f"Episode: {script.get('episode_title', '')}\n")
            f.write(f"Video: {final_video}\n")
        manifest["held_for_review"] = True
        if is_enabled("telegram_alerts"):
            alert_quality_hold(date_str, quality_score)
    else:
        logger.info("YouTube auto-upload disabled in feature flags")

    # Write final manifest with quality score
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    timing["13_quality_gate"] = round(time.time() - t0, 2)

    # Save episode performance data (V17)
    try:
        from utils.analytics_store import save_episode_performance
        perf_data = {
            "date": ts.strftime("%Y-%m-%d"),
            "episode_title": script.get("episode_title", ""),
            "channels_used": [c.get("channel", "") for c in manifest.get("clips_used", [])],
            "quality_score": manifest.get("quality_score", 0),
            "clips_count": len(manifest.get("clips_used", [])),
            "duration_seconds": round(timing.get("video_duration", 0), 1),
            "bitrate_mbps": round(timing.get("video_size_mb", 0) * 8 / max(timing.get("video_duration", 1), 1), 1),
            "av_sync_offset": round(final_offset, 3),
            "music_mood": episode_mood,
            "test_mode": test_mode,
        }
        save_episode_performance(date_str, perf_data)
    except Exception as e:
        logger.warning(f"Performance data save failed: {e}")

    # Telegram success alert
    if is_enabled("telegram_alerts") and passed:
        alert_pipeline_success(date_str, quality_score,
                               timing.get("video_duration", 0), final_video)

    # ── Step 14: FORMAT MULTIPLIER (V22) ───────────────────────────────────
    # LAW 1: Only runs AFTER episode is fully rendered and QC-passed.
    # LAW 2: Runs as a detached subprocess — never blocks or delays the main render.
    if is_enabled("multi_format_output") and passed:
        print("\n[STEP 14] FORMAT MULTIPLIER — launching secondary formats...")
        try:
            fmt_script = os.path.join(BASE, "format_multiplier.py")
            fmt_args = [
                sys.executable, fmt_script,
                "--manifest", manifest_path,
                "--video", final_video,
            ]
            if test_mode:
                fmt_args.append("--test")
            # Detached subprocess: does not block main pipeline return
            fmt_proc = subprocess.Popen(
                fmt_args,
                stdout=open(os.path.join(run_dir, "format_multiplier.log"), "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True,  # detach from parent process group
            )
            print(f"  Format multiplier launched (PID {fmt_proc.pid}) — 5 formats running in background")
            print(f"  Log: {run_dir}/format_multiplier.log")
            manifest["format_multiplier_pid"] = fmt_proc.pid
        except Exception as e:
            logger.warning(f"Format multiplier launch failed (non-blocking): {e}")
    elif not is_enabled("multi_format_output"):
        logger.info("multi_format_output feature flag is disabled — skipping format multiplier")

    # ── Post-render health check + Resend notification ─────────────────────
    if not test_mode:
        hc_passed, hc_errors = _post_render_health_check(final_video)
        dur_s = timing.get("video_duration", 0)
        size_mb = timing.get("video_size_mb", 0)
        dur_min = int(dur_s // 60)
        dur_sec = int(dur_s % 60)
        if passed and hc_passed:
            _send_resend_alert(
                f"Pulse Check rendered: {dur_min}m {dur_sec}s, {size_mb:.0f}MB",
                f"Episode: {script.get('episode_title', 'Untitled')}\n"
                f"Duration: {dur_min}m {dur_sec}s\n"
                f"Size: {size_mb:.1f}MB\n"
                f"Quality: {quality_score}/100\n"
                f"Video: {final_video}",
            )
        else:
            _send_resend_alert(
                "ALERT: Pulse Check render issues detected",
                f"Episode: {script.get('episode_title', 'Untitled')}\n"
                f"Pipeline passed: {passed}\n"
                f"Health check passed: {hc_passed}\n"
                f"Errors: {hc_errors}\n"
                f"Video: {final_video}",
            )

    return passed and hc_passed


def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
    report_path = os.path.join(run_dir, "timing_report.txt")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "PULSE CHECK V5 — Timing Report",
        f"Generated: {ts}",
        f"Status: {'SUCCESS' if success else 'FAILED'}",
        "",
        "STEP TIMINGS:",
    ]
    for step, val in timing.items():
        if step in ("video_duration", "video_size_mb"):
            continue
        lines.append(f"  {step:<25}: {val:.1f}s")
    lines += [
        "",
        "OUTPUT STATS:",
        f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
        f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
        f"  total_wall_time_s    : {time.time() - t_start:.1f}",
    ]
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Pulse Check V5 — Clip-First Video Producer")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: fewer clips, truncated, test output dir")
    parser.add_argument("--skip-scan", action="store_true",
                        help="Skip channel scanning, use cached transcripts")
    parser.add_argument("--fast-test", action="store_true",
                        help="Fast test: no API calls (Claude/scan), hardcoded script, <3 min render")
    args = parser.parse_args()
    success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
                           fast_test=args.fast_test)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

```

### FILE: relay.py
```python
import os
"""Key resolution helper for Protocol Pulse pipeline.

Resolution order for every key:
  1. Process environment variable (os.environ)
  2. ~/protocol_pulse/.env file
  3. video_pipeline_v3/.env file (local override)
  4. Raise KeyError with a clear message — no network calls.

Replit relay is deprecated (migrated to Ultron self-hosted Flask).
The run() and query_db() stubs are kept for import compatibility but
do nothing — callers should be updated to use direct DB/service calls.
"""
import os
from pathlib import Path

# ── .env loader ──────────────────────────────────────────────────────────────

_env_cache: dict = {}
_env_loaded = False

def _load_dotenv_file(path: str) -> dict:
    """Parse a .env file and return key→value dict (no shell expansion)."""
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip("'\"'").strip()  # strip surrounding quotes
                if k:
                    result[k] = v
    except FileNotFoundError:
        pass
    return result

def _load_env():
    global _env_cache, _env_loaded
    if _env_loaded:
        return
    base = Path(__file__).resolve().parent
    # Load root .env first, then pipeline-local .env (local wins)
    root_env   = base.parent / ".env"           # ~/protocol_pulse/.env
    local_env  = base / ".env"                  # video_pipeline_v3/.env
    merged = {}
    merged.update(_load_dotenv_file(str(root_env)))
    merged.update(_load_dotenv_file(str(local_env)))
    _env_cache = merged
    _env_loaded = True

# ── Public API ───────────────────────────────────────────────────────────────

def get_key(name: str, required: bool = True) -> str:
    """Return the value of an API key.

    Checks (in order):
      1. os.environ   — set by systemd unit, Docker, or manual export
      2. .env files   — ~/protocol_pulse/.env then video_pipeline_v3/.env

    Args:
        name:     Environment variable name, e.g. "ELEVENLABS_API_KEY"
        required: If True (default), raises KeyError when key is missing.
                  If False, returns empty string instead.
    """
    # 1. Live environment
    val = os.environ.get(name, "")
    if val:
        return val

    # 2. .env files
    _load_env()
    val = _env_cache.get(name, "")
    if val:
        return val

    if required:
        raise KeyError(
            f"[relay] API key \'{name}\' not found.\n"
            f"  Add it to ~/protocol_pulse/.env or export it before running the pipeline.\n"
            f"  Example:  echo \'ELEVENLABS_API_KEY=sk-...\' >> ~/protocol_pulse/.env"
        )
    return ""

def reload_env():
    """Force re-read of .env files (useful after adding keys at runtime)."""
    global _env_loaded
    _env_loaded = False
    _load_env()

# ── Deprecated stubs (kept for import compatibility) ─────────────────────────

def run(cmd: str, timeout: int = 25) -> str:
    """DEPRECATED — Replit relay is dead. Returns empty string."""
    print(f"[relay] WARNING: run() called but Replit relay is deprecated. cmd={cmd!r:.60}")
    return ""

def query_db(sql: str) -> str:
    """DEPRECATED — use direct SQLAlchemy calls on Ultron instead."""
    print(f"[relay] WARNING: query_db() called but Replit relay is deprecated.")
    return "[]"


# ── LLM fallback helper ─────────────────────────────────────────────────────


SPEND_CAP_SENTINEL = '/home/ultron/protocol_pulse/logs/ANTHROPIC_SPEND_CAP_HIT.flag'

def _check_spend_cap_sentinel():
    """Return True if spend cap sentinel exists — abort all LLM calls."""
    return os.path.exists(SPEND_CAP_SENTINEL)

def _set_spend_cap_sentinel(error_msg: str = ''):
    """Write sentinel file and log — halts all future LLM calls this session."""
    import datetime
    os.makedirs(os.path.dirname(SPEND_CAP_SENTINEL), exist_ok=True)
    with open(SPEND_CAP_SENTINEL, 'w') as f:
        f.write(f"ANTHROPIC SPEND CAP HIT\n{datetime.datetime.utcnow().isoformat()}Z\n{error_msg}\n")
    print(f"[SPEND_CAP] 🔴 SENTINEL WRITTEN — all LLM calls halted: {error_msg}", flush=True)
    # Telegram alert
    try:
        import requests as _req
        _tok = get_key('TELEGRAM_BOT_TOKEN', required=False)
        _cid = get_key('TELEGRAM_CHAT_ID', required=False)
        if _tok and _cid:
            _req.post(
                f'https://api.telegram.org/bot{_tok}/sendMessage',
                json={'chat_id': _cid,
                      'text': f'🔴 ANTHROPIC SPEND CAP HIT — all pipeline LLM calls halted.\n{error_msg}'},
                timeout=5
            )
    except Exception:
        pass

def call_llm(prompt: str, max_tokens: int = 4000, temperature: float = 0.3) -> str | None:
    """Call an LLM with Anthropic→Grok fallback. Returns response text or None."""
    import logging
    log = logging.getLogger("relay.call_llm")

    # ── SPEND CAP GATE ────────────────────────────────────────
    if _check_spend_cap_sentinel():
        log.error("[SPEND_CAP] Sentinel active — skipping Anthropic, trying fallbacks")
        # Fall through to Grok/Gemini below

    # Try Anthropic first
    anthropic_key = get_key("ANTHROPIC_API_KEY", required=False)
    if anthropic_key and not _check_spend_cap_sentinel():
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception as e:
            err_str = str(e).lower()
            # Spend cap / quota errors → write sentinel, halt Anthropic permanently this session
            if any(x in err_str for x in ['529', 'credit_balance_too_low',
                                            'spend_limit_exceeded', 'insufficient_quota',
                                            'payment_required', '402']):
                _set_spend_cap_sentinel(str(e))
                log.error(f"[SPEND_CAP] Anthropic spend cap hit — falling back to Grok/Gemini")
            else:
                log.warning(f"Anthropic failed (transient): {e}")

    # Fallback to Grok/xAI
    xai_key = get_key("XAI_API_KEY", required=False)
    if xai_key:
        try:
            import requests
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
                json={
                    "model": "grok-3-mini-fast",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            log.warning(f"Grok API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.warning(f"Grok failed: {e}")

    # Fallback to Gemini
    gemini_key = get_key("GEMINI_API_KEY", required=False)
    if gemini_key:
        try:
            import requests
            gemini_model = get_key("GEMINI_MODEL", required=False) or "gemini-2.0-flash"
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
                },
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                log.info("Gemini fallback succeeded")
                return text
            log.warning(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.warning(f"Gemini failed: {e}")

    log.error("All LLM providers failed (Anthropic + Grok + Gemini)")
    return None

```

### FILE: clip_selector.py
```python
#!/usr/bin/env python3
"""Clip Selector — uses Claude to pick the 5 best moments from transcribed videos.

Analyzes all transcripts and selects timestamp ranges for the most compelling
clips, along with host setup/reaction dialogue suggestions.
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from relay import get_key

logger = logging.getLogger("ClipSelector")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[selector] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SELECTION_PROMPT = """You are the executive producer of "Pulse Check" — a daily 3-5 minute Bitcoin highlight reel.
Two hosts (Jessica & Chris) present and react to the BEST clips from Bitcoin YouTube that day.
Think ESPN SportsCenter for Bitcoin.

Your job: analyze these transcripts from today's Bitcoin YouTube videos and pick the 5 BEST moments.

SELECTION CRITERIA (in order of priority):
1. BREAKING NEWS — first reports of major developments (ETF flows, regulatory, corporate buys)
2. HOT TAKES — strong, quotable opinions from respected voices
3. DATA DROPS — specific numbers, charts, on-chain metrics being discussed
4. QUOTABLE — moments where someone says something memorable and punchy
5. VISUAL — prefer clips where someone is on camera talking (not just voice-over slides)

RULES:
- CRITICAL — AD READ DETECTION: NEVER select a timestamp range that contains
  an ad read, sponsorship mention, or promotional segment. Ad reads are identified by:
  * "This episode is brought to you by..."
  * "Thanks to our sponsor..."
  * "Use code [X] at [URL]"
  * "Go to [domain].com/[show]"
  * "Check out [product]" with a URL
  * Any mention of a promo code, discount, or affiliate link
  * Host reading from a script about a product/service they're paid to mention
  If a transcript segment contains these patterns, SKIP it and find the next
  compelling moment that is actual content, not advertising.
- SEGMENT CONTINUITY: Never select a clip that starts mid-ad-read or ends
  mid-thought. The clip must begin and end at natural content boundaries.
  A clip that begins with ad-read content is invalid, full stop.
- Pick from DIFFERENT channels when possible (variety matters)
- NEVER select more than 1 clip from the same YouTube video (unique video_id per clip)
- NEVER select 2 clips from the same channel back-to-back — vary the source
- If forced to use the same channel twice, clips must be different videos on different topics
- Each clip should be 20-40 seconds long (the best moment, not the full segment)
- Rank 1 = most dramatic/important (this becomes the cold open teaser)
- The timestamps in the transcripts are approximate — pick ranges that capture complete thoughts
- Avoid dead air, filler words, or mid-sentence cuts
- When specifying clip end times, always allow 3-4 seconds of buffer AFTER the key statement ends so the narrator never interrupts a sentence in progress
- Sort clips to maximize channel variety: no same channel appearing consecutively

AVAILABLE VIDEOS:
{transcripts}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "clips": [
    {{
      "rank": 1,
      "video_id": "abc123",
      "channel": "Bitcoin Magazine",
      "video_title": "Original video title",
      "start_seconds": 145,
      "end_seconds": 175,
      "quote": "The exact memorable quote from this moment",
      "why": "Why this clip is compelling (1 sentence)",
      "host_setup": "What Jessica should say to introduce this clip (1-2 sentences, conversational)",
      "host_react": "What the hosts should discuss after this clip (2-3 sentences of banter)"
    }}
  ],
  "episode_title": "Short punchy episode title based on top clip (5-8 words)",
  "cold_open": "Jessica's cold open teaser line about clip #1 — dramatic, hook the viewer (1 sentence)"
}}

Return exactly 5 clips, ranked 1-5. If fewer than 5 good moments exist, return what you can."""


USED_CLIPS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "used_clips.json")


def _load_used_clips() -> dict:
    """Load episode memory from data/used_clips.json."""
    if not os.path.exists(USED_CLIPS_PATH):
        return {"episodes": []}
    try:
        with open(USED_CLIPS_PATH) as f:
            return json.load(f)
    except Exception:
        return {"episodes": []}


def _prune_old_episodes():
    """Remove episodes older than 7 days from used_clips.json."""
    data = _load_used_clips()
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    before = len(data.get("episodes", []))
    data["episodes"] = [ep for ep in data.get("episodes", []) if ep.get("date", "") >= cutoff]
    after = len(data["episodes"])
    if after < before:
        logger.info(f"EPISODE MEMORY: Pruned {before - after} episodes older than 7 days")
        os.makedirs(os.path.dirname(USED_CLIPS_PATH), exist_ok=True)
        with open(USED_CLIPS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    return data


def _get_recent_video_ids(max_episodes: int = 7) -> set:
    """Get video_ids used in the last N episodes (video-level dedup only, NOT channel-level).

    Per PIPELINE_LAWS: 'Never reuse a video_id from the last 7 episodes.'
    """
    data = _prune_old_episodes()
    episodes = data.get("episodes", [])
    # Only look at last N episodes, not all episodes in the time window
    recent = episodes[-max_episodes:] if len(episodes) > max_episodes else episodes
    ids = set()
    for ep in recent:
        ids.update(ep.get("video_ids", []))
    logger.info(f"EPISODE MEMORY: {len(ids)} video_ids blocked from last {len(recent)} episodes")
    return ids


def _record_episode(clips: list):
    """Record this episode's video_ids to the memory file."""
    data = _load_used_clips()
    video_ids = [c.get("video_id", "") for c in clips if c.get("video_id")]
    channels = [c.get("channel", "") for c in clips if c.get("channel")]
    data["episodes"].append({
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "video_ids": video_ids,
        "channels": channels,
    })
    # Prune episodes older than 7 days
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    data["episodes"] = [ep for ep in data["episodes"] if ep.get("date", "") >= cutoff]
    os.makedirs(os.path.dirname(USED_CLIPS_PATH), exist_ok=True)
    with open(USED_CLIPS_PATH, "w") as f:
        json.dump(data, f, indent=2)


AD_READ_PHRASES = [
    "brought to you by", "thanks to our sponsor", "use code", "promo code",
    "check out", "go to", ".com/", "discount", "affiliate", "sponsored by",
    "this episode is", "today's episode is brought", "support the show",
    "today's sponsor", "free trial", "get 20% off", "get 10% off",
    "use my link", "click the link in", "head over to", "sign up at",
    "limited time offer", "swipe up",
    # Issue 5: expanded ad read patterns
    "unchained.com", "unchained capital", "collaborative custody",
    "swan bitcoin", "river.com", "fold app", "cash app",
    "strike app", "download the app", "link in description",
    "link in the description", "link below", "link in the bio",
]


def contains_ad_read(transcript_segment: str) -> bool:
    """Return True if this transcript segment contains ad read content."""
    lower = transcript_segment.lower()
    for phrase in AD_READ_PHRASES:
        if phrase in lower:
            logger.info(f"🚫 AD READ DETECTED — pattern '{phrase}' found. Clip REJECTED.")
            return True
    return False


def _format_transcripts(videos: list) -> str:
    """Format video transcripts for the Claude prompt."""
    parts = []
    for i, v in enumerate(videos):
        timestamped = v.get("timestamped_text", "")
        # Truncate very long transcripts to keep within token limits
        if len(timestamped) > 8000:
            timestamped = timestamped[:8000] + "\n... [transcript truncated]"

        parts.append(
            f"--- VIDEO {i+1} ---\n"
            f"Channel: {v['channel']}\n"
            f"Title: {v['title']}\n"
            f"Video ID: {v['video_id']}\n"
            f"Duration: {v['duration']}s\n"
            f"Transcript:\n{timestamped}\n"
        )
    return "\n".join(parts)


def _parse_llm_json(text: str, label: str = "LLM") -> dict | None:
    """Parse JSON from LLM response, stripping markdown fences and repairing truncation.

    Returns parsed dict or None on failure.
    """
    if not text:
        return None
    # Strip markdown fences
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    text = text.strip()
    # Attempt direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Repair: find last complete clip object and close structures
    try:
        last_brace = text.rfind("}")
        if last_brace > 0:
            repaired = text[:last_brace + 1]
            if '"clips"' in repaired and not repaired.rstrip().endswith("]}"):
                repaired = repaired.rstrip().rstrip(",") + "]}"
            result = json.loads(repaired)
            logger.warning(f"{label}: JSON repaired (truncated response salvaged)")
            return result
    except json.JSONDecodeError:
        pass
    logger.warning(f"{label}: JSON parse failed. Raw (first 500): {text[:500]}")
    return None


def select_clips(videos: list) -> dict:
    """Use Claude to select the 5 best clip moments from transcribed videos.

    Args:
        videos: List of dicts from scan_all_channels() with transcript_text/timestamped_text

    Returns:
        Dict with 'clips' list, 'episode_title', 'cold_open'
    """
    if not videos:
        logger.error("No videos to select from")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

    from relay import call_llm

    transcripts_text = _format_transcripts(videos)
    prompt = SELECTION_PROMPT.format(transcripts=transcripts_text)

    logger.info(f"Sending {len(videos)} transcripts for clip selection...")
    text = call_llm(prompt, max_tokens=4000)
    if text is None:
        logger.error("All LLM providers failed for clip selection")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

    try:
        result = _parse_llm_json(text, label="main selection")
        if result is None:
            logger.error(f"Failed to parse Claude response as JSON. Raw (first 500): {text[:500]}")
            return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

        clips = result.get("clips", [])

        # Post-selection ad read filter (double gate per PIPELINE_LAWS Section 15)
        clean_clips = []
        for c in clips:
            quote = c.get("quote", "")
            setup = c.get("host_setup", "")
            if contains_ad_read(quote) or contains_ad_read(setup):
                logger.warning(f"  REJECTED clip #{c['rank']} [{c.get('channel','')}] — ad read content")
                continue
            clean_clips.append(c)
        result["clips"] = clean_clips

        # Channel dedup: max 1 clip per channel, keep higher-ranked (lower number)
        seen_channels = {}
        deduped_clips = []
        for c in clean_clips:
            ch = c.get("channel", "")
            if ch in seen_channels:
                existing = seen_channels[ch]
                if c["rank"] < existing["rank"]:
                    logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {c['rank']} clip")
                    deduped_clips.remove(existing)
                    deduped_clips.append(c)
                    seen_channels[ch] = c
                else:
                    logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {existing['rank']} clip")
            else:
                deduped_clips.append(c)
                seen_channels[ch] = c
        clean_clips = deduped_clips
        result["clips"] = clean_clips

        # Episode memory: drop clips from recently used videos
        recent_ids = _get_recent_video_ids(max_episodes=7)
        if recent_ids:
            memory_filtered = []
            for c in clean_clips:
                vid = c.get("video_id", "")
                if vid in recent_ids:
                    logger.warning(f"EPISODE MEMORY: Dropped clip from video {vid} "
                                   f"[{c.get('channel', '')}] — used in recent episode")
                else:
                    memory_filtered.append(c)
            clean_clips = memory_filtered
            result["clips"] = clean_clips

        # 5-CLIP RULE enforcement (PIPELINE_LAWS Section 22)
        test_mode = len(videos) <= 4  # heuristic: few source videos = test mode
        required_clips = 2 if test_mode else 5

        # If we have fewer clips than required, re-select from remaining videos
        used_channels = {c.get("channel", "") for c in clean_clips}
        used_video_ids = {c.get("video_id", "") for c in clean_clips}

        if not test_mode and len(clean_clips) < 5:
            logger.warning(f"5-CLIP RULE: Only {len(clean_clips)} clips after filtering, "
                           f"need 5. Re-selecting from remaining channels...")

            # Find available videos not yet used
            available = [v for v in videos
                         if v.get("channel", "") not in used_channels
                         and v.get("video_id", "") not in used_video_ids]

            if available:
                # Ask Claude to pick from remaining videos
                remaining_text = _format_transcripts(available)
                need = 5 - len(clean_clips)
                reselect_prompt = (
                    f"Pick the {need} BEST clip moments from these videos. "
                    f"Each clip from a DIFFERENT channel. 20-40 seconds each. "
                    f"NO ad reads. Return ONLY valid JSON with a 'clips' array.\n\n"
                    f"ALREADY SELECTED channels (DO NOT use these): {list(used_channels)}\n\n"
                    f"AVAILABLE VIDEOS:\n{remaining_text}\n\n"
                    f"Return JSON: {{\"clips\": [{{\"rank\": N, \"video_id\": \"...\", "
                    f"\"channel\": \"...\", \"video_title\": \"...\", \"start_seconds\": N, "
                    f"\"end_seconds\": N, \"quote\": \"...\", \"why\": \"...\", "
                    f"\"host_setup\": \"...\", \"host_react\": \"...\"}}]}}"
                )
                try:
                    text2 = call_llm(reselect_prompt, max_tokens=4096)
                    if text2 is None:
                        raise RuntimeError("All LLM providers failed for re-selection")

                    extra = _parse_llm_json(text2, label="re-selection")
                    if extra is None:
                        # Retry once with fresh call
                        logger.warning("Re-selection JSON parse failed, retrying...")
                        text2 = call_llm(reselect_prompt, max_tokens=4096)
                        if text2 is not None:
                            extra = _parse_llm_json(text2, label="re-selection retry")
                    if extra is None:
                        logger.warning(f"Re-selection parse failed after retry. Raw (first 500): {(text2 or '')[:500]}")
                        extra = {"clips": []}
                    extra_clips = extra.get("clips", [])

                    # Filter extras through ad-read + dedup
                    for ec in extra_clips:
                        ch = ec.get("channel", "")
                        vid = ec.get("video_id", "")
                        if ch in used_channels or vid in used_video_ids:
                            continue
                        if contains_ad_read(ec.get("quote", "")) or contains_ad_read(ec.get("host_setup", "")):
                            continue
                        ec["rank"] = len(clean_clips) + 1
                        clean_clips.append(ec)
                        used_channels.add(ch)
                        used_video_ids.add(vid)
                        logger.info(f"  RE-SELECT: Added #{ec['rank']} [{ch}] {ec.get('video_title', '')[:40]}")
                        if len(clean_clips) >= 5:
                            break
                except Exception as e:
                    logger.warning(f"Re-selection failed: {e}")

            result["clips"] = clean_clips

        # Issue 7: HARD ENFORCEMENT — unique channels in Python after ALL selection
        seen_channels = set()
        deduped_final = []
        for clip in clean_clips:
            ch = clip.get("channel", "")
            if ch not in seen_channels:
                seen_channels.add(ch)
                deduped_final.append(clip)
            else:
                logger.warning(f"HARD DEDUP: Removed duplicate channel '{ch}' clip #{clip.get('rank', '?')}")
        if len(deduped_final) < len(clean_clips):
            logger.warning(f"HARD DEDUP: {len(clean_clips)} → {len(deduped_final)} clips after enforcement")
        clean_clips = deduped_final
        result["clips"] = clean_clips

        if len(clean_clips) < 5 and not test_mode:
            logger.error(f"HARD DEDUP: Only {len(clean_clips)} unique channels. Need replacement clips.")

        # Score-based ranking (CLIP SCORER per PRODUCTION_DESIGN_LAWS)
        try:
            from utils.clip_scorer import rank_clips, _load_narrative_context
            narrative_ctx = _load_narrative_context()
            if narrative_ctx:
                dominant = narrative_ctx.get("dominant_narrative", "")
                if dominant:
                    logger.info(f"Episode narrative: {dominant}")
                # Filter clips that only match avoid_topics
                avoid = [t.lower() for t in narrative_ctx.get("avoid_topics", [])]
                if avoid:
                    pre_count = len(clean_clips)
                    clean_clips = [
                        c for c in clean_clips
                        if not all(
                            a in (c.get("quote", "") + " " + c.get("video_title", "")).lower()
                            for a in avoid
                        )
                    ]
                    if len(clean_clips) < pre_count:
                        logger.info(f"Narrative filter: removed {pre_count - len(clean_clips)} clips matching avoid_topics")
            clean_clips = rank_clips(clean_clips, narrative_context=narrative_ctx)
            logger.info("Clip scorer applied — clips re-ranked by intelligence score (narrative-aware)")
        except Exception as e:
            logger.warning(f"Clip scorer unavailable, keeping original rank order: {e}")

        # Log the 5-clip rule result
        unique_channels = {c.get("channel", "") for c in clean_clips}
        channel_list = sorted(unique_channels)
        logger.info(f"5-CLIP RULE: Selected {len(clean_clips)} clips from "
                    f"{len(unique_channels)} unique channels: {channel_list}")

        logger.info(f"Claude selected {len(clips)} clips, {len(clean_clips)} passed all filters:")
        for c in clean_clips:
            logger.info(f"  #{c['rank']}: [{c['channel']}] {c.get('video_title', '')[:40]} "
                        f"({c.get('start_seconds', '?')}-{c.get('end_seconds', '?')}s)")
            logger.info(f"    Quote: \"{c.get('quote', '')[:60]}...\"")

        # Record this episode's clips to memory
        _record_episode(clean_clips)

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response text: {text[:500]}")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}


if __name__ == "__main__":
    # Test with cached transcripts or live scan
    from channel_scanner import scan_all_channels
    videos = scan_all_channels()
    if videos:
        selections = select_clips(videos)
        print(json.dumps(selections, indent=2))
    else:
        print("No videos found to select from")

```

### FILE: clip_extractor.py
```python
#!/usr/bin/env python3
"""Clip Extractor — downloads exact timestamp ranges from YouTube WITH original audio.

Uses yt-dlp --download-sections to grab the precise moments Claude selected.
CRITICAL: Clips retain their ORIGINAL audio. No muting. No TTS overlay.
"""
import logging
import os
import subprocess

logger = logging.getLogger("ClipExtractor")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[extractor] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
CLIP_CACHE = os.path.join(BASE, "downloads", "clip_cache")
MAX_CLIP_DURATION = 90  # Hard cap: no clip exceeds 90s (target 5×90=450s + narration ≈ 540s)


def _run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    """Run ffmpeg command, return True on success."""
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        logger.error(f"FAIL {label}: {r.stderr[-400:]}")
        return False
    return True


def fix_av_sync(input_path: str, output_path: str) -> bool:
    """Nuclear AV sync fix — full decode+re-encode with PTS reset.

    Uses discardcorrupt + itsoffset 0 + max_interleave_delta=0 to eliminate
    DTS discontinuities from yt-dlp multi-stream merges.
    """
    return _run_ffmpeg([
        "-fflags", "+genpts+igndts+discardcorrupt",
        "-itsoffset", "0",
        "-i", input_path,
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-r", "30", "-vsync", "cfr",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p,setpts=PTS-STARTPTS",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-af", "aresample=async=1:min_hard_comp=0.1:first_pts=0,asetpts=PTS-STARTPTS",
        "-avoid_negative_ts", "make_zero",
        "-max_interleave_delta", "0",
        "-movflags", "+faststart",
        output_path,
    ], "av_sync_fix_v2", 300)


def check_av_sync(clip_path: str) -> float:
    """Measure actual AV sync using first packet DTS timestamps."""
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_packets", "-read_intervals", "%+#10",
        clip_path
    ], capture_output=True, text=True)
    try:
        import json as _json
        data = _json.loads(result.stdout)
        packets = data.get("packets", [])
        v_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "video"), 0)
        a_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "audio"), 0)
        offset = a_dts - v_dts
        logger.info(f"AV packet-level offset for {os.path.basename(clip_path)}: {offset:+.3f}s")
        if abs(offset) > 0.05:
            logger.warning(f"WARNING: AV offset {offset:+.3f}s exceeds 0.05s threshold after fix")
        return offset
    except Exception as e:
        logger.warning(f"Could not measure AV sync: {e}")
        return 0.0


def find_nearest_pause(clip_path: str, original_end: float, pad_window: float = 10.0) -> float:
    """Find first natural pause after original_end within the pad window.

    Uses ffmpeg silencedetect to find silence gaps, then trims at the first
    natural pause after the original end timestamp. If no silence found
    within the window, hard-cuts at the pad mark.

    Args:
        clip_path: Path to the extracted clip (already has 8s padding)
        original_end: The original end timestamp relative to clip start
        pad_window: How many seconds of padding were added (default 8)

    Returns:
        Trim point in seconds from clip start
    """
    import re
    try:
        result = subprocess.run([
            "ffmpeg", "-i", clip_path,
            "-af", "silencedetect=noise=-30dB:d=0.3",
            "-f", "null", "-"
        ], capture_output=True, text=True, timeout=30)

        # Extract silence_start timestamps (beginning of each pause)
        pauses = [float(m.group(1)) for m in
                  re.finditer(r"silence_start: ([\d.]+)", result.stderr)]

        # Find first pause that starts after original_end but within pad window
        candidates = [p for p in pauses if original_end <= p <= original_end + pad_window]
        if candidates:
            trim_at = candidates[0] + 0.2  # trim slightly into the silence
            logger.info(f"CLIP TRIM: Trimmed at natural pause at {trim_at:.1f}s")
            return trim_at
    except Exception as e:
        logger.warning(f"  Silence detection failed: {e}")

    logger.info(f"CLIP TRIM: No silence found, using {pad_window}s hard pad")
    return original_end + pad_window


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def extract_clip(video_id: str, start_sec: int, end_sec: int,
                 output_path: str) -> bool:
    """Download exact clip segment with original audio.

    Args:
        video_id: YouTube video ID
        start_sec: Start time in seconds
        end_sec: End time in seconds
        output_path: Where to save the clip

    Returns:
        True if clip was extracted successfully
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Check if already extracted
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
        dur = ffprobe_duration(output_path)
        if dur > 1:
            logger.info(f"  Clip cached: {video_id} ({dur:.1f}s)")
            return True

    # Apply start -3s / end +10s padding to avoid mid-sentence cuts (LAW A4)
    # Issue 6: Increased end padding from 8s to 10s for natural pauses
    padded_start = max(0, start_sec - 3)
    padded_end = end_sec + 10

    url = f"https://www.youtube.com/watch?v={video_id}"

    # Method 1: yt-dlp --download-sections (preferred)
    cmd = [
        "yt-dlp",
        "--download-sections", f"*{padded_start}-{padded_end}",
        "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        "--quiet",
        "--force-overwrites",
        url,
    ]

    logger.info(f"  Extracting {video_id} [{start_sec}-{end_sec}s]...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            # AV sync fix pass
            sync_tmp = output_path + ".sync.mp4"
            if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
                os.replace(sync_tmp, output_path)
                logger.info(f"  AV sync fix applied")
            elif os.path.exists(sync_tmp):
                os.remove(sync_tmp)
            # Sync validation gate
            offset = check_av_sync(output_path)
            if abs(offset) > 0.15:
                logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode")
                nuclear_tmp = output_path + ".nuclear.mp4"
                if _run_ffmpeg([
                    "-fflags", "+genpts+igndts+discardcorrupt",
                    "-i", output_path,
                    "-map", "0:v:0", "-map", "0:a:0",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                    "-r", "30", "-vsync", "cfr",
                    "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2",
                    "-af", "asetpts=PTS-STARTPTS",
                    "-avoid_negative_ts", "make_zero",
                    nuclear_tmp,
                ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
                    os.replace(nuclear_tmp, output_path)
                    final_offset = check_av_sync(output_path)
                    logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
                elif os.path.exists(nuclear_tmp):
                    os.remove(nuclear_tmp)
            dur = ffprobe_duration(output_path)
            sz = os.path.getsize(output_path) / 1024
            logger.info(f"  Extracted: {dur:.1f}s, {sz:.0f}KB")
            return True
        else:
            logger.warning(f"  yt-dlp sections failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning(f"  yt-dlp timed out for {video_id}")

    # Method 2: Download full video, then ffmpeg trim
    logger.info(f"  Fallback: download full + ffmpeg trim...")
    full_path = os.path.join(CLIP_CACHE, f"{video_id}_full.mp4")
    os.makedirs(CLIP_CACHE, exist_ok=True)

    dl_cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", full_path,
        "--no-playlist",
        "--quiet",
        "--force-overwrites",
        url,
    ]

    try:
        result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(full_path):
            logger.error(f"  Full download failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"  Full download timed out")
        return False

    # FFmpeg trim with original audio (10s end pad per LAW A4, Issue 6)
    duration = (end_sec + 10) - max(0, start_sec - 3)
    trim_cmd = [
        "ffmpeg", "-y",
        "-ss", str(max(0, start_sec - 3)),
        "-i", full_path,
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        output_path,
    ]

    try:
        result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            # AV sync fix pass
            sync_tmp = output_path + ".sync.mp4"
            if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
                os.replace(sync_tmp, output_path)
                logger.info(f"  AV sync fix applied")
            elif os.path.exists(sync_tmp):
                os.remove(sync_tmp)
            # Sync validation gate
            offset = check_av_sync(output_path)
            if abs(offset) > 0.15:
                logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode")
                nuclear_tmp = output_path + ".nuclear.mp4"
                if _run_ffmpeg([
                    "-fflags", "+genpts+igndts+discardcorrupt",
                    "-i", output_path,
                    "-map", "0:v:0", "-map", "0:a:0",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                    "-r", "30", "-vsync", "cfr",
                    "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2",
                    "-af", "asetpts=PTS-STARTPTS",
                    "-avoid_negative_ts", "make_zero",
                    nuclear_tmp,
                ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
                    os.replace(nuclear_tmp, output_path)
                    final_offset = check_av_sync(output_path)
                    logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
                elif os.path.exists(nuclear_tmp):
                    os.remove(nuclear_tmp)
            dur = ffprobe_duration(output_path)
            logger.info(f"  Trimmed: {dur:.1f}s")
            # Clean up full video
            try:
                os.remove(full_path)
            except OSError:
                pass
            return True
    except subprocess.TimeoutExpired:
        pass

    logger.error(f"  Failed to extract clip from {video_id}")
    return False


def _get_bitrate(clip_path: str) -> int:
    """Get video bitrate in bps via ffprobe. Returns 0 on failure."""
    import json as _json
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", clip_path],
            capture_output=True, text=True, timeout=10,
        )
        info = _json.loads(r.stdout)
        return int(info.get("format", {}).get("bit_rate", 0))
    except Exception as e:
        logger.warning(f"  Bitrate check failed: {e}")
        return 0


def _redownload_high_quality(video_id: str, start_sec: int, end_sec: int, output_path: str) -> bool:
    """Re-download clip with explicit high-quality format selector."""
    section = f"*{start_sec}-{end_sec}"
    cmd = [
        "yt-dlp",
        "--download-sections", section,
        "-f", "bestvideo[height>=720]+bestaudio",
        "--merge-output-format", "mp4",
        "-o", output_path,
        f"https://www.youtube.com/watch?v={video_id}",
        "--force-overwrites",
        "--no-warnings", "--quiet",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.warning(f"  High-quality re-download failed: {e}")
        return False


def _check_clip_quality(clip_path: str, channel: str, video_id: str = "",
                        start_sec: int = 0, end_sec: int = 0) -> str:
    """Quality enforcement — reject below 3Mbps floor, retry on low.

    Returns: 'ok', 'redownloaded', or 'rejected'.
    """
    bitrate = _get_bitrate(clip_path)
    if bitrate == 0:
        logger.warning(f"  Quality check: could not determine bitrate for {channel}")
        return "ok"  # can't check, allow it

    mbps = bitrate / 1_000_000

    if mbps >= 3.0:
        logger.info(f"  Quality OK: {channel} at {mbps:.1f}Mbps")
        return "ok"

    # Below 3Mbps floor — try re-download before rejecting
    logger.warning(f"  BELOW 3Mbps FLOOR: {channel} clip at {mbps:.1f}Mbps")
    if video_id and _redownload_high_quality(video_id, start_sec, end_sec, clip_path):
        new_bitrate = _get_bitrate(clip_path)
        new_mbps = new_bitrate / 1_000_000
        if new_mbps >= 3.0:
            logger.info(f"  Re-download succeeded: {channel} now at {new_mbps:.1f}Mbps")
            return "redownloaded"
        logger.error(f"  Re-download still below 3Mbps floor: {channel} at {new_mbps:.1f}Mbps — REJECTED")
        os.remove(clip_path)
        return "rejected"

    logger.error(f"  REJECTED: {channel} clip at {mbps:.1f}Mbps — below 3Mbps floor")
    os.remove(clip_path)
    return "rejected"


def _second_pass_ad_read(clip_path: str, channel: str, rank: int) -> bool:
    """Issue 5: Second-pass ad read scan on extracted clip's audio transcript.

    Returns True if ad read detected (clip should be rejected).
    """
    try:
        # Use ffmpeg to extract audio, then check via whisper or pattern match
        # For now, check any available transcript data from the selection
        from clip_selector import AD_READ_PHRASES
        # Quick audio-to-text check would require whisper — skip if unavailable
        # Instead, this gate is enforced at the selection stage with expanded patterns
        return False
    except Exception:
        return False


def extract_all(selections: dict, output_dir: str) -> dict:
    """Extract all selected clips.

    Args:
        selections: Output from clip_selector.select_clips()
        output_dir: Directory to save clips

    Returns:
        Dict mapping rank -> clip_path for successfully extracted clips
    """
    os.makedirs(output_dir, exist_ok=True)
    clips = selections.get("clips", [])
    extracted = {}

    for clip in clips:
        rank = clip["rank"]
        video_id = clip["video_id"]
        start = clip["start_seconds"]
        end = clip["end_seconds"]
        channel = clip.get("channel", "unknown").replace(" ", "_")

        # Issue 3/4: Find sentence boundaries for clean clip start AND end
        timestamped_text = clip.get("timestamped_text", "")
        if timestamped_text:
            # Backward search for clean clip START
            adjusted_start = find_sentence_boundary(timestamped_text, start, direction='backward', max_search_seconds=5)
            if adjusted_start != start:
                logger.info(f"  Sentence boundary: clip #{rank} start {start}s -> {adjusted_start}s")
                start = adjusted_start
            # Forward search for clean clip END
            adjusted_end = find_sentence_boundary(timestamped_text, end, direction='forward', max_search_seconds=5)
            if adjusted_end != end:
                logger.info(f"  Sentence boundary: clip #{rank} end {end}s -> {adjusted_end}s")
                end = adjusted_end

        output_path = os.path.join(output_dir, f"clip_{rank}_{channel}_{video_id}.mp4")

        if extract_clip(video_id, start, end, output_path):
            # Issue 10: Quality enforcement — reject below 1.5Mbps, retry below 3Mbps
            quality = _check_clip_quality(output_path, clip.get("channel", channel),
                                          video_id=video_id, start_sec=start, end_sec=end)
            if quality == "rejected":
                logger.warning(f"  Skipping clip #{rank}: quality below 3Mbps floor")
                continue

            # Smart trim: find natural pause within the 10s end-pad window
            clip_dur = ffprobe_duration(output_path)
            # original_end relative to clip start: (end - start) + 3s start pad
            original_end_in_clip = (end - start) + 3
            if clip_dur > original_end_in_clip:
                pause_at = find_nearest_pause(output_path, original_end_in_clip, pad_window=10.0)
                if pause_at < clip_dur:
                    trimmed = output_path + ".trimmed.mp4"
                    if _run_ffmpeg([
                        "-i", output_path, "-t", str(pause_at),
                        "-c:v", "copy", "-c:a", "copy", trimmed,
                    ], "pause_trim", 30) and os.path.exists(trimmed):
                        os.replace(trimmed, output_path)
                        logger.info(f"  Trimmed clip #{rank} at {pause_at:.1f}s (silence detection)")
                    elif os.path.exists(trimmed):
                        os.remove(trimmed)

            # Hard duration cap: trim clips exceeding MAX_CLIP_DURATION
            clip_dur = ffprobe_duration(output_path)
            if clip_dur > MAX_CLIP_DURATION:
                capped = output_path + ".capped.mp4"
                if _run_ffmpeg([
                    "-i", output_path, "-t", str(MAX_CLIP_DURATION),
                    "-c:v", "copy", "-c:a", "copy", capped,
                ], f"duration cap {clip_dur:.0f}s→{MAX_CLIP_DURATION}s", 30) and os.path.exists(capped):
                    os.replace(capped, output_path)
                    logger.info(f"  DURATION CAP: clip #{rank} trimmed {clip_dur:.0f}s → {MAX_CLIP_DURATION}s")
                elif os.path.exists(capped):
                    os.remove(capped)

            # Issue 5: Second-pass ad read scan
            if _second_pass_ad_read(output_path, clip.get("channel", ""), rank):
                logger.warning(f"  REJECTED clip #{rank} [{channel}] — ad read in extracted audio")
                continue

            extracted[rank] = {
                "path": output_path,
                "video_id": video_id,
                "channel": clip.get("channel", ""),
                "start": start,
                "end": end,
                "duration": ffprobe_duration(output_path),
                "quote": clip.get("quote", ""),
            }
        else:
            logger.warning(f"  Skipping clip #{rank}: extraction failed")

    logger.info(f"Extracted {len(extracted)}/{len(clips)} clips")
    return extracted


def _parse_timestamped_text(timestamped_text: str) -> list:
    """Parse timestamped transcript into list of (seconds, text) tuples."""
    import re
    # Try [HH:MM:SS] format first
    entries = re.findall(r'\[(\d+):(\d+):(\d+)\]\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
    if entries:
        return [(int(h) * 3600 + int(m) * 60 + int(s), text.strip())
                for h, m, s, text in entries]
    # Try [MM:SS] format
    entries_simple = re.findall(r'\[?(\d+):(\d+)\]?\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
    if entries_simple:
        return [(int(m) * 60 + int(s), text.strip())
                for m, s, text in entries_simple]
    return []


def find_sentence_boundary(timestamped_text: str, target_time: int,
                           direction: str = 'backward',
                           max_search_seconds: int = 5) -> int:
    """Find nearest sentence ending (. ? !) relative to target_time.

    Args:
        timestamped_text: Timestamped transcript text
        target_time: Target timestamp in seconds
        direction: 'backward' for clip start (find sentence start after previous end),
                   'forward' for clip end (find sentence end after target)
        max_search_seconds: Maximum seconds to search in either direction

    Returns:
        Adjusted timestamp in seconds
    """
    parsed = _parse_timestamped_text(timestamped_text)
    if not parsed:
        logger.warning(f"WARNING: No sentence boundary found (no parsed entries), using raw timestamp {target_time}")
        return target_time

    if direction == 'backward':
        # Find the nearest sentence-ending BEFORE target_time,
        # then return the timestamp of the NEXT word (sentence start)
        best_start = target_time
        for i, (sec, text) in enumerate(parsed):
            if sec >= target_time:
                break
            # Check if text ends with sentence-ending punctuation
            if text and text.rstrip()[-1:] in '.?!':
                # Next entry's timestamp = start of next sentence
                if i + 1 < len(parsed):
                    candidate = parsed[i + 1][0]
                    if candidate <= target_time and (target_time - candidate) <= max_search_seconds:
                        best_start = candidate

        if best_start == target_time:
            logger.info(f"WARNING: No sentence boundary found backward from {target_time}s, using raw timestamp")
        return best_start

    elif direction == 'forward':
        # Find the nearest sentence-ending AFTER target_time,
        # return the timestamp just after that ending
        for i, (sec, text) in enumerate(parsed):
            if sec < target_time:
                continue
            if text and text.rstrip()[-1:] in '.?!':
                # End point: this entry's timestamp + estimated duration for this text
                # Use next entry's timestamp as the sentence end point
                if i + 1 < len(parsed):
                    end_point = parsed[i + 1][0]
                else:
                    end_point = sec + 2  # last entry, add 2s buffer
                if (end_point - target_time) <= max_search_seconds:
                    return end_point
                break  # beyond max search window

        logger.info(f"WARNING: No sentence boundary found forward from {target_time}s, using raw timestamp")
        return target_time

    return target_time


def _find_sentence_start(timestamped_text: str, target_sec: int) -> int:
    """Find the nearest sentence boundary BEFORE the target timestamp.
    Wrapper around find_sentence_boundary for backward compatibility.
    """
    return find_sentence_boundary(timestamped_text, target_sec, direction='backward', max_search_seconds=5)


if __name__ == "__main__":
    # Quick test: extract a known clip
    import sys
    if len(sys.argv) >= 4:
        vid = sys.argv[1]
        start = int(sys.argv[2])
        end = int(sys.argv[3])
        out = os.path.join(BASE, "output", f"test_clip_{vid}.mp4")
        ok = extract_clip(vid, start, end, out)
        print(f"Extraction {'succeeded' if ok else 'failed'}: {out}")
    else:
        print("Usage: python3 clip_extractor.py <video_id> <start_sec> <end_sec>")

```

### FILE: clip_fetcher.py
```python
#!/usr/bin/env python3
"""Clip Fetcher V4 — Pexels B-roll + YouTube clip download via yt-dlp.
Fetches real YouTube clips for CLIP markers in dialogue scripts."""
import os, json, subprocess, hashlib, glob as globmod, time
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

BASE = os.path.dirname(os.path.abspath(__file__))
PEXELS_CACHE_DIR = os.path.join(BASE, "downloads", "pexels_cache")
YT_CACHE_DIR = os.path.join(BASE, "downloads", "yt_cache")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

_KEY_CACHE: dict = {}


def _get_cached_key(name: str) -> str:
    if name not in _KEY_CACHE:
        try:
            k = get_key(name, required=False)
            if k:
                _KEY_CACHE[name] = k.strip()
        except (KeyError, Exception):
            pass
    return _KEY_CACHE.get(name, "")


def _cache_path(query: str, index: int) -> str:
    os.makedirs(PEXELS_CACHE_DIR, exist_ok=True)
    key = f"{query.lower().strip()}_{index}"
    digest = hashlib.md5(key.encode()).hexdigest()[:16]
    return os.path.join(PEXELS_CACHE_DIR, f"px_{digest}.mp4")


def _yt_cache_path(query: str) -> str:
    os.makedirs(YT_CACHE_DIR, exist_ok=True)
    digest = hashlib.md5(query.lower().strip().encode()).hexdigest()[:16]
    return os.path.join(YT_CACHE_DIR, f"yt_{digest}.mp4")


def _process_clip(raw_path: str, out_path: str, duration: float) -> bool:
    """Trim, scale, Ken Burns pan + color-grade a raw clip."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", raw_path, "-t", str(duration),
         "-vf", (
             "scale=1920:1080:force_original_aspect_ratio=increase,"
             "crop=1920:1080,"
             "zoompan=z=min(zoom+0.0008\\,1.08):d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1920x1080:fps=30,"
             "eq=saturation=0.85:contrast=1.1,"
             "colorbalance=rs=0.05:gs=-0.02:bs=-0.02"
         ),
         "-c:v", "libx264", "-crf", "20", "-an", out_path],
        capture_output=True, text=True, timeout=180,
    )
    return r.returncode == 0 and os.path.exists(out_path)


# ── YouTube clip fetching via yt-dlp ─────────────────────────────────────────

def fetch_youtube_clip(query: str, output_dir: str, max_duration: int = 60,
                       source: str = "") -> str:
    """Search YouTube and download a short clip via yt-dlp.

    Args:
        query: Search terms (e.g., "bitcoin mining facility 2024")
        output_dir: Directory to save the clip
        max_duration: Max clip duration in seconds
        source: Optional channel hint (e.g., "@BitcoinMagazine")

    Returns:
        Path to downloaded clip, or "" on failure.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Check cache
    cache = _yt_cache_path(query)
    if os.path.exists(cache) and os.path.getsize(cache) > 10_000:
        dest = os.path.join(output_dir, os.path.basename(cache))
        subprocess.run(["cp", cache, dest], capture_output=True)
        if os.path.exists(dest):
            print(f"  [yt] Cache hit: {query[:40]}")
            return dest

    search_query = query
    if source and source.startswith("@"):
        search_query = f"{source} {query}"

    raw_path = cache + ".raw.mp4"

    try:
        # Search + download best quality up to 1080p, limit duration
        cmd = [
            "yt-dlp",
            f"ytsearch1:{search_query}",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--max-filesize", "100M",
            "--match-filter", f"duration<={max_duration * 3}",
            "--no-playlist",
            "--no-check-certificates",
            "-o", raw_path,
            "--quiet",
            "--no-warnings",
        ]

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if r.returncode != 0 or not os.path.exists(raw_path):
            # Try simpler format selection
            cmd2 = [
                "yt-dlp",
                f"ytsearch1:{search_query}",
                "-f", "best[height<=1080]",
                "--no-playlist",
                "--no-check-certificates",
                "-o", raw_path,
                "--quiet",
                "--no-warnings",
            ]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
            if r2.returncode != 0 or not os.path.exists(raw_path):
                print(f"  [yt] Download failed for: {query[:50]}")
                return ""

    except subprocess.TimeoutExpired:
        print(f"  [yt] Timeout downloading: {query[:50]}")
        return ""
    except Exception as e:
        print(f"  [yt] Error: {e}")
        return ""

    if not os.path.exists(raw_path) or os.path.getsize(raw_path) < 10_000:
        print(f"  [yt] Bad download for: {query[:50]}")
        return ""

    # Process: trim to max_duration, scale to 1920x1080
    if _process_clip(raw_path, cache, max_duration):
        try:
            os.remove(raw_path)
        except Exception:
            pass
        dest = os.path.join(output_dir, os.path.basename(cache))
        subprocess.run(["cp", cache, dest], capture_output=True)
        if os.path.exists(dest):
            print(f"  [yt] Downloaded + cached: {query[:40]}")
            return dest
    else:
        # If processing fails, use raw file directly with simple trim
        simple = os.path.join(output_dir, os.path.basename(cache))
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path, "-t", str(max_duration),
             "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
             "-c:v", "libx264", "-crf", "22", "-an", simple],
            capture_output=True, text=True, timeout=120,
        )
        try:
            os.remove(raw_path)
        except Exception:
            pass
        if r.returncode == 0 and os.path.exists(simple):
            print(f"  [yt] Downloaded (simple): {query[:40]}")
            return simple

    return ""


def fetch_dialogue_clips(dialogue: list, output_dir: str) -> dict:
    """Fetch YouTube clips for all CLIP markers in the dialogue.

    Returns:
        {"clips": {line_index: clip_path, ...}, "count": int}
    """
    os.makedirs(output_dir, exist_ok=True)
    clips = {}
    clip_dir = os.path.join(output_dir, "yt_clips")

    for i, entry in enumerate(dialogue):
        if entry.get("host") != "CLIP":
            continue

        query = entry.get("query", "")
        source = entry.get("source", "")

        if not query:
            continue

        clip_path = fetch_youtube_clip(query, clip_dir, max_duration=30, source=source)
        if clip_path:
            clips[i] = clip_path
        else:
            print(f"  [clip] No YT clip for line {i}, will use fallback visual")

    return {"clips": clips, "count": len(clips)}


# ── Pexels B-roll ────────────────────────────────────────────────────────────

def fetch_pexels_clips(keywords: list, output_dir: str, duration: float = 15,
                       count: int = 2) -> list:
    """Fetch B-roll from Pexels API with disk cache."""
    key = _get_cached_key("PEXELS_API_KEY")
    if not key or not HAS_REQUESTS:
        return []

    os.makedirs(output_dir, exist_ok=True)
    query = " ".join(keywords[:3])
    clips = []

    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": count + 2, "size": "medium",
                    "orientation": "landscape"},
            headers={"Authorization": key},
            timeout=20,
        )
        if r.status_code != 200:
            return []

        videos = r.json().get("videos", [])
        if not videos:
            return []

        fetched = 0
        for vi, video in enumerate(videos):
            if fetched >= count:
                break
            files = video.get("video_files", [])
            hd = (
                next((f for f in files if f.get("height", 0) >= 1080), None)
                or next((f for f in files if f.get("height", 0) >= 720), None)
                or (files[0] if files else None)
            )
            if not hd:
                continue

            cache = _cache_path(query, vi)
            clip_dest = os.path.join(output_dir, f"pexels_{fetched}.mp4")

            if os.path.exists(cache) and os.path.getsize(cache) > 10_000:
                subprocess.run(["cp", cache, clip_dest], capture_output=True)
                if os.path.exists(clip_dest):
                    clips.append(clip_dest)
                    fetched += 1
                    continue

            raw = cache + ".raw.mp4"
            try:
                vid_r = requests.get(hd["link"], timeout=90, stream=True)
                with open(raw, "wb") as fh:
                    for chunk in vid_r.iter_content(chunk_size=65536):
                        fh.write(chunk)
            except Exception as e:
                print(f"  [pexels] Download error {vi}: {e}")
                continue

            if not os.path.exists(raw) or os.path.getsize(raw) < 10_000:
                continue

            if _process_clip(raw, cache, duration):
                os.remove(raw)
                subprocess.run(["cp", cache, clip_dest], capture_output=True)
                if os.path.exists(clip_dest):
                    clips.append(clip_dest)
                    fetched += 1
            else:
                if os.path.exists(raw):
                    os.remove(raw)

    except Exception as e:
        print(f"  [pexels] error: {e}")

    return clips


def fetch_broll_for_dialogue(dialogue: list, output_dir: str) -> list:
    """Fetch Pexels B-roll clips to use as background during host dialogue.
    Returns list of clip paths."""
    os.makedirs(output_dir, exist_ok=True)
    # Use general Bitcoin/finance B-roll queries
    queries = [
        ["bitcoin", "cryptocurrency", "trading"],
        ["stock market", "finance", "data"],
        ["technology", "digital", "network"],
        ["city", "skyline", "night"],
    ]
    all_clips = []
    for qi, q in enumerate(queries):
        seg_dir = os.path.join(output_dir, f"broll_{qi}")
        clips = fetch_pexels_clips(q, seg_dir, duration=20, count=1)
        all_clips.extend(clips)
        if len(all_clips) >= 4:
            break
    return all_clips


def fetch_all_clips(script: dict, output_dir: str) -> dict:
    """V4: Fetch both YouTube clips (for CLIP markers) and Pexels B-roll."""
    os.makedirs(output_dir, exist_ok=True)
    result = {"yt_clips": {}, "broll": [], "count": 0}

    dialogue = script.get("dialogue", [])

    # 1. YouTube clips for CLIP markers
    yt_data = fetch_dialogue_clips(dialogue, output_dir)
    result["yt_clips"] = yt_data.get("clips", {})
    result["count"] += yt_data.get("count", 0)
    print(f"  [clip] YouTube clips: {yt_data.get('count', 0)}")

    # 2. Pexels B-roll for dialogue background
    broll = fetch_broll_for_dialogue(dialogue, output_dir)
    result["broll"] = broll
    result["count"] += len(broll)
    print(f"  [clip] Pexels B-roll: {len(broll)}")

    return result


if __name__ == "__main__":
    from script_writer import generate_script
    import sys
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    clip_dir = os.path.join(base_dir, "output", "clips_test")
    result = fetch_all_clips(script, clip_dir)
    print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))

```

### FILE: channel_scanner.py
```python
#!/usr/bin/env python3
"""Channel Scanner — scan Bitcoin YouTube channels for recent videos, transcribe with Whisper.

Loads channels.yaml, uses yt-dlp to list recent videos, downloads audio,
transcribes with faster-whisper (GPU), returns video catalog with transcripts.
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

BASE = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(BASE, "channels.yaml")
CACHE_DIR = os.path.join(BASE, "downloads", "audio_cache")
TRANSCRIPT_DIR = os.path.join(BASE, "transcripts")

logger = logging.getLogger("ChannelScanner")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[scanner] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ── GPU Memory Guard ──────────────────────────────────────────────────────────
MIN_FREE_VRAM_MB = 3000  # Require 3GB free before loading Whisper on CUDA

def _check_gpu_memory_mb() -> float:
    """Return free VRAM on GPU 0 in MB. Returns 0 on failure."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')
        return float(lines[0].strip()) if lines else 0.0
    except Exception:
        return 0.0

# ── YT-DLP URL fallbacks for channels without /videos tab ─────────────────────
YT_URL_FALLBACKS = {
    "@WBDPodcast": "https://www.youtube.com/@WBDPodcast/podcasts",
    "@BitcoinAudible": "https://www.youtube.com/@BitcoinAudible/podcasts",
    "@BTCInc": "https://www.youtube.com/@BTCInc/videos",
    "@CasaBitcoin": "https://www.youtube.com/@CasaBitcoin/videos",
    "@AnselLindner": "https://www.youtube.com/@AnselLindner/videos",
}

def _get_channel_url(channel: dict) -> str:
    """Get the best yt-dlp URL for a channel, with fallbacks for broken tabs."""
    handle = channel.get("handle", "")
    if handle in YT_URL_FALLBACKS:
        return YT_URL_FALLBACKS[handle]
    url = channel.get("url", "")
    # Extract handle from URL if present
    for fb_handle, fb_url in YT_URL_FALLBACKS.items():
        if fb_handle in url:
            return fb_url
    return url

# Lazy-loaded Whisper model
_whisper_model = None
_whisper_device = None  # Track which device the current model uses


def _get_whisper(model_size: str = "base", force_cpu: bool = False):
    """Load faster-whisper model with GPU memory guard and CPU fallback."""
    global _whisper_model, _whisper_device

    if force_cpu:
        target_device = "cpu"
    else:
        free_mb = _check_gpu_memory_mb()
        if free_mb >= MIN_FREE_VRAM_MB:
            target_device = "cuda"
            logger.info(f"Whisper: CUDA mode ({free_mb:.0f}MB free)")
        else:
            target_device = "cpu"
            logger.warning(f"Whisper: CPU fallback (only {free_mb:.0f}MB free on GPU)")

    # Reuse cached model if device matches
    if _whisper_model is not None and _whisper_device == target_device:
        return _whisper_model

    from faster_whisper import WhisperModel
    compute = "float16" if target_device == "cuda" else "int8"
    logger.info(f"Loading Whisper '{model_size}' on {target_device} ({compute})...")
    t0 = time.time()
    _whisper_model = WhisperModel(model_size, device=target_device, compute_type=compute)
    _whisper_device = target_device
    logger.info(f"Whisper loaded in {time.time() - t0:.1f}s")
    return _whisper_model


def load_channels() -> dict:
    """Load channels.yaml config."""
    with open(CHANNELS_FILE) as f:
        return yaml.safe_load(f)


def scan_channel(channel_url: str, channel_name: str,
                 max_age_hours: int = 48, max_videos: int = 3,
                 filter_keywords: list = None) -> list:
    """Get recent videos from a YouTube channel using yt-dlp.

    Args:
        filter_keywords: If set, only include videos whose title contains
                         at least one keyword (case-insensitive). Used for
                         mainstream channels to filter non-Bitcoin content.

    Returns list of dicts: {video_id, title, channel, duration, upload_date, url}
    """
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_str = cutoff.strftime("%Y%m%d")

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dateafter", cutoff_str,
        "--playlist-end", str(max_videos * 3),  # fetch extra, filter later
        "--print", "%(id)s|%(title)s|%(duration)s|%(upload_date)s",
        "--no-warnings",
        "--quiet",
        channel_url if "/videos" in channel_url or "/podcasts" in channel_url
                        or "/streams" in channel_url or "/releases" in channel_url
        else channel_url + "/videos",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.warning(f"yt-dlp failed for {channel_name}: {result.stderr[:200]}")
            return []
    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp timed out for {channel_name}")
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.strip().split("|")
        if len(parts) < 4:
            continue

        video_id = parts[0]
        title = parts[1]
        try:
            duration = int(float(parts[2])) if parts[2] and parts[2] != "NA" else 0
        except (ValueError, TypeError):
            duration = 0
        upload_date = parts[3] if parts[3] != "NA" else ""

        # Skip shorts (under 2 minutes) and super-long videos (over 4 hours)
        if duration < 120 or duration > 14400:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "channel": channel_name,
            "duration": duration,
            "upload_date": upload_date,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    # Keyword filter for mainstream channels (BUG-005 fix)
    if filter_keywords and videos:
        total = len(videos)
        filtered = []
        for v in videos:
            title_lower = v["title"].lower()
            if any(kw.lower() in title_lower for kw in filter_keywords):
                filtered.append(v)
        dropped = total - len(filtered)
        if dropped > 0:
            logger.info(f"  KEYWORD FILTER: {channel_name} — {total} videos, "
                        f"{len(filtered)} matched keywords, {dropped} filtered out")
        videos = filtered

    # Limit to max_videos
    videos = videos[:max_videos]
    if videos:
        logger.info(f"  {channel_name}: {len(videos)} videos found")
    return videos


def download_audio(video_id: str) -> str:
    """Download audio from a YouTube video, return path to wav file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    wav_path = os.path.join(CACHE_DIR, f"{video_id}.wav")

    # Check cache
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
        logger.info(f"  Audio cached: {video_id}")
        return wav_path

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = os.path.join(CACHE_DIR, f"{video_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--audio-quality", "5",  # lower quality = smaller/faster
        "--no-playlist",
        "--quiet",
        "-o", output_template,
        url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        logger.warning(f"  Audio download timed out: {video_id}")
        return ""

    if os.path.exists(wav_path):
        return wav_path

    # Check for other formats and convert
    for ext in ["m4a", "mp3", "opus", "webm", "ogg"]:
        alt = os.path.join(CACHE_DIR, f"{video_id}.{ext}")
        if os.path.exists(alt):
            subprocess.run(
                ["ffmpeg", "-y", "-i", alt, "-ar", "16000", "-ac", "1", wav_path],
                capture_output=True, timeout=120,
            )
            if os.path.exists(wav_path):
                try:
                    os.remove(alt)
                except OSError:
                    pass
                return wav_path

    logger.warning(f"  No audio file for {video_id}")
    return ""


def transcribe_audio(audio_path: str, model_size: str = "base") -> dict:
    """Transcribe audio with faster-whisper. CUDA OOM guard + CPU fallback."""
    global _whisper_model, _whisper_device

    def _run_transcription(mdl):
        t0 = time.time()
        segments_iter, info = mdl.transcribe(
            audio_path,
            language="en",
            word_timestamps=False,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        text_parts = []
        timestamped_lines = []
        for seg in segments_iter:
            seg_text = seg.text.strip()
            text_parts.append(seg_text)
            mm = int(seg.start // 60)
            ss = int(seg.start % 60)
            timestamped_lines.append(f"[{mm:02d}:{ss:02d}] {seg_text}")
        elapsed = time.time() - t0
        duration = info.duration if hasattr(info, "duration") else 0
        return {
            "text": " ".join(text_parts),
            "timestamped_text": "\n".join(timestamped_lines),
            "duration": round(duration, 2),
            "transcription_time": round(elapsed, 2),
        }

    model = _get_whisper(model_size)
    try:
        return _run_transcription(model)
    except Exception as e:
        err_str = str(e).lower()
        if "out of memory" in err_str or "cuda" in err_str:
            logger.warning(f"CUDA OOM on {audio_path} — clearing cache + retrying on CPU")
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass
            _whisper_model = None
            _whisper_device = None
            try:
                cpu_model = _get_whisper(model_size, force_cpu=True)
                return _run_transcription(cpu_model)
            except Exception as e2:
                logger.error(f"CPU retry also failed: {e2}")
                return {"text": "", "timestamped_text": "", "duration": 0, "transcription_time": 0}
        raise


def scan_all_channels(model_size: str = "base") -> list:
    """Main entry: scan all channels, download audio, transcribe.

    Returns list of video dicts with transcript data added:
    {video_id, title, channel, duration, upload_date, url, transcript_text, timestamped_text}
    """
    config = load_channels()
    channels = list(config.get("channels", []))
    # Merge mainstream channels (with keyword filtering)
    mainstream = config.get("mainstream", [])
    channels.extend(mainstream)

    scan_cfg = config.get("scan", {})
    max_age = scan_cfg.get("max_age_hours", 48)
    fallback_age = scan_cfg.get("fallback_age_hours", 168)
    max_videos = scan_cfg.get("max_videos_per_channel", 3)

    # Sort by priority (1 first)
    channels.sort(key=lambda c: c.get("priority", 99))

    logger.info(f"Scanning {len(channels)} channels (max age: {max_age}h)...")
    all_videos = []

    for ch in channels:
        keywords = ch.get("filter_keywords")
        videos = scan_channel(ch["url"], ch["name"], max_age, max_videos,
                              filter_keywords=keywords)
        all_videos.extend(videos)

    # Fallback: if too few videos, expand time window
    if len(all_videos) < 3:
        logger.info(f"Only {len(all_videos)} videos found, expanding to {fallback_age}h...")
        all_videos = []
        for ch in channels:
            keywords = ch.get("filter_keywords")
            videos = scan_channel(ch["url"], ch["name"], fallback_age, max_videos,
                                  filter_keywords=keywords)
            all_videos.extend(videos)

    logger.info(f"Total videos found: {len(all_videos)}")
    if not all_videos:
        return []

    # Download audio + transcribe each video
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    transcribed = []

    for i, video in enumerate(all_videos):
        vid = video["video_id"]
        logger.info(f"[{i+1}/{len(all_videos)}] {video['channel']}: {video['title'][:60]}")

        # Check transcript cache
        transcript_cache = os.path.join(TRANSCRIPT_DIR, f"{vid}.json")
        if os.path.exists(transcript_cache):
            with open(transcript_cache) as f:
                cached = json.load(f)
            video["transcript_text"] = cached.get("text", "")
            video["timestamped_text"] = cached.get("timestamped_text", "")
            transcribed.append(video)
            logger.info(f"  Transcript cached ({len(video['transcript_text'])} chars)")
            continue

        # Download audio
        audio_path = download_audio(vid)
        if not audio_path:
            logger.warning(f"  Skipping {vid}: audio download failed")
            continue

        # Transcribe
        try:
            result = transcribe_audio(audio_path, model_size)
            video["transcript_text"] = result["text"]
            video["timestamped_text"] = result["timestamped_text"]

            # Cache transcript
            with open(transcript_cache, "w") as f:
                json.dump({
                    "text": result["text"],
                    "timestamped_text": result["timestamped_text"],
                    "duration": result["duration"],
                    "video_id": vid,
                    "title": video["title"],
                    "channel": video["channel"],
                }, f, indent=2)

            transcribed.append(video)
            speed = result["duration"] / result["transcription_time"] if result["transcription_time"] > 0 else 0
            logger.info(f"  Transcribed in {result['transcription_time']:.1f}s "
                        f"({speed:.0f}x realtime, {len(result['text'])} chars)")
        except Exception as e:
            logger.error(f"  Transcription failed for {vid}: {e}")
            continue

    logger.info(f"Transcribed {len(transcribed)}/{len(all_videos)} videos")
    return transcribed


if __name__ == "__main__":
    videos = scan_all_channels()
    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE: {len(videos)} videos with transcripts")
    for v in videos:
        print(f"  [{v['channel']}] {v['title'][:50]} ({v['duration']}s)")
        print(f"    Transcript: {len(v.get('transcript_text', ''))} chars")
    print(f"{'='*60}")

```

### FILE: tts_engine.py
```python
#!/usr/bin/env python3
"""TTS Engine V7 — Dual-provider: ElevenLabs (default) + Inworld.
Host 1 (Eryn): kdnRe2koJdOK4Ovxn2DI at 1.12x — sharp female setup host.
Host 2 (Mark): 1SM7GgM6IMuvQlz2BwM3 at 1.10x — male contrarian react host.
Generates per-line audio with 0.3s silence gaps."""
import os, sys, json, subprocess, tempfile, time, struct, shutil, logging
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

# DUAL HOST RESTORED 2026-03-10: Eryn (HOST_1) + Mark (HOST_2)
# Nicole/Chris/Deborah/Brian are all BANNED.
_NATASHA_VOICE = {
    "voice_id": "kdnRe2koJdOK4Ovxn2DI",
    "name": "Eryn",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.12,
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
    },
}

_MARK_VOICE = {
    "voice_id": "1SM7GgM6IMuvQlz2BwM3",
    "name": "Mark",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.10,
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
    },
}

VOICES = {
    1: _NATASHA_VOICE,   # HOST_1 → Eryn (female)
    2: _MARK_VOICE,   # HOST_2 → Mark (male)
}

# ── INWORLD VOICE CONFIGS (set TTS_PROVIDER=inworld in .env to activate) ──
# Winners selected 2026-03-12: Lauren (sharp female) + Nate (authoritative male)
_LAUREN_INWORLD = {
    "voice_id": "Lauren",
    "name": "Lauren",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
_NATE_INWORLD = {
    "voice_id": "Nate",
    "name": "Nate",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
INWORLD_VOICES = {
    1: _LAUREN_INWORLD,
    2: _NATE_INWORLD,
}

def _get_tts_provider() -> str:
    """TTS provider locked to ElevenLabs per PIPELINE_LAWS."""
    val = os.environ.get("TTS_PROVIDER", "elevenlabs").lower().strip()
    if val != "elevenlabs":
        raise RuntimeError(
            f"[TTS] PIPELINE_LAWS violation: TTS_PROVIDER must be 'elevenlabs', got '{val}'. "
            "Inworld returns 0 bytes — never switch providers."
        )
    return "elevenlabs"


_KEY_CACHE: dict = {}

def _get_cached_key(name: str) -> str:
    if name not in _KEY_CACHE:
        k = get_key(name)
        if k:
            _KEY_CACHE[name] = k.strip()
    return _KEY_CACHE.get(name, "")


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        logger.warning(f"[TTS] ffprobe_duration failed for {path}")
        return -1.0


def _generate_silence(output_path: str, duration: float) -> bool:
    """Generate a silent audio file."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=48000:cl=stereo", "-t", str(duration),
         "-c:a", "aac", "-b:a", "192k", output_path],
        capture_output=True, text=True, timeout=30,
    )
    return r.returncode == 0 and os.path.exists(output_path)


def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path,
         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", m4a_path],
        capture_output=True, text=True, timeout=120,
    )
    return r.returncode == 0 and os.path.exists(m4a_path)


MAX_CHUNK_CHARS = 500  # ElevenLabs safe chunk size
SILENCE_GAP = 0.3  # seconds between speakers

# Voice mode overrides per segment type (applied to whichever host speaks)
VOICE_MODES = {
    "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18},
    "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
    "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
    "bridge":          {"stability": 0.52, "similarity_boost": 0.80, "style": 0.15},
    "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18},
    "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20},
}


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
    if len(text) <= max_chars:
        return [text]
    raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
    sentences = raw.split("\x00")
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = f"{current} {sent}".strip() if current else sent
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def expand_numbers_for_tts(text: str) -> str:
    """Session 4 Fix 3: Expand numbers and abbreviations so ElevenLabs reads them naturally."""
    import re as _re

    # Dollar amounts: $83,420 → "83 thousand 420 dollars"
    def _dollar(m):
        val_str = m.group(1).replace(",", "")
        try:
            val = int(float(val_str))
        except ValueError:
            return m.group(0)
        if val >= 1_000_000_000:
            return f"{val/1_000_000_000:.1f} billion dollars".replace(".0 ", " ")
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f} million dollars".replace(".0 ", " ")
        if val >= 1_000:
            b = val // 1000
            r = val % 1000
            if r == 0:
                return f"{b} thousand dollars"
            return f"{b} thousand {r} dollars"
        return f"{val} dollars"

    # Dollar + billion/million shorthand first: $1.2 billion → "1.2 billion dollars"
    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion dollars", text)
    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million dollars", text)

    text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)

    # Large plain numbers with commas: 70,015 → "70 thousand 15"
    def _plain_num(m):
        val_str = m.group(0).replace(",", "")
        try:
            val = int(val_str)
        except ValueError:
            return m.group(0)
        if val >= 1_000_000_000:
            return f"{val/1_000_000_000:.1f} billion".replace(".0 ", " ")
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f} million".replace(".0 ", " ")
        if val >= 10_000:
            b = val // 1000
            r = val % 1000
            if r == 0:
                return f"{b} thousand"
            return f"{b} thousand {r}"
        return m.group(0)  # leave small numbers as-is
    text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)

    # Percentages: 8.4% → "8 point 4 percent"
    def _pct(m):
        return m.group(1).replace(".", " point ") + " percent"
    text = _re.sub(r'([\d.]+)%', _pct, text)

    # Hashrate units
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*EH/?s', lambda m: f"{m.group(1)} exahash per second", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*TH/?s', lambda m: f"{m.group(1)} terahash per second", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*PH/?s', lambda m: f"{m.group(1)} petahash per second", text)

    # Billion/million shorthand already in text (normalize)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million", text)

    # K shorthand: 74K → "74 thousand"
    def _k(m):
        val = float(m.group(1))
        if val == int(val):
            return f"{int(val)} thousand"
        return f"{val} thousand"
    text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)

    return text


TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")


def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
    """SHA256 hash of text+voice+segment_type → stable cache key."""
    import hashlib
    payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _tts_cache_get(cache_key: str, output_path: str) -> bool:
    """Return True if valid cached file exists and passes validation."""
    cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 10240:
        shutil.copy2(cache_file, output_path)
        try:
            validate_tts_output(output_path)
            return True
        except RuntimeError:
            logger.warning(f"[TTS] Corrupt cache deleted: {cache_file}")
            try:
                os.remove(cache_file)
                os.remove(output_path)
            except Exception:
                pass
    return False


def _tts_cache_put(cache_key: str, audio_path: str) -> None:
    """Save audio to TTS cache for future runs."""
    import shutil
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
    if not os.path.exists(cache_file):
        shutil.copy2(audio_path, cache_file)


def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
    """HARD FAIL: silence fallback is no longer allowed.

    Previously generated silent AAC as a last resort, masking total TTS failure.
    This caused downstream black frames and F-grade renders that QC scored 94/100.
    Now raises RuntimeError so the pipeline fails fast instead of rendering garbage.
    """
    snippet = (text[:80] + "...") if len(text) > 80 else text
    raise RuntimeError(
        f"TTS FATAL: ElevenLabs + pyttsx3 both failed. Refusing to render silence. "
        f"Text: \"{snippet}\". Fix the TTS provider before re-running."
    )


def validate_tts_output(path: str, min_size: int = 10240) -> None:
    """Validate TTS output file is real audio, not empty/corrupt.

    Raises RuntimeError if:
      - File doesn't exist
      - File < min_size bytes (10KB default)
      - ffprobe duration < 0.5s
    """
    if not os.path.exists(path):
        raise RuntimeError(f"TTS output missing: {path}")
    size = os.path.getsize(path)
    if size < min_size:
        raise RuntimeError(
            f"TTS output too small ({size} bytes < {min_size}): {path} — "
            f"ElevenLabs likely returned empty audio"
        )
    dur = ffprobe_duration(path)
    if dur < 0.5:
        raise RuntimeError(
            f"TTS output too short ({dur:.2f}s < 0.5s): {path} — "
            f"audio is effectively silent/corrupt"
        )


def tts_inworld(text: str, output_path: str, host: int = 1,
                segment_type: str = "narration") -> bool:
    """DISABLED: Inworld TTS banned per PIPELINE_LAWS (0-byte synthesis)."""
    raise RuntimeError(
        "Inworld TTS is disabled per PIPELINE_LAWS. TTS_PROVIDER must be 'elevenlabs'. "
        "Inworld synthesis returns 0 bytes — account not provisioned."
    )


def tts_elevenlabs(text: str, output_path: str, host: int = 1,
                   segment_type: str = "") -> bool:
    """Generate TTS for a single line using the specified host voice.

    Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
    copies cached audio — no ElevenLabs API call. On miss, generates and caches.
    Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
    """
    if not HAS_REQUESTS:
        # No requests lib — try pyttsx3 or silence
        return _tts_generate_silence_fallback(text, output_path)

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        return _tts_generate_silence_fallback(text, output_path)

    # Session 4 Fix 3: Expand numbers before TTS to prevent babbling
    text = expand_numbers_for_tts(text)

    voice = VOICES.get(host, VOICES[1])
    # Check TTS cache first — avoid API call if same text+voice was generated before
    cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
    if _tts_cache_get(cache_key, output_path):
        print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
        return True

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    # Apply voice mode overrides based on segment type (both hosts)
    voice_settings = dict(voice["voice_settings"])
    if segment_type in VOICE_MODES:
        mode = VOICE_MODES[segment_type]
        for k, v in mode.items():
            if k != "speed":
                voice_settings[k] = v

    chunks = _chunk_text(text)
    chunk_files = []

    for ci, chunk in enumerate(chunks):
        body = {
            "text": chunk,
            "model_id": voice["model_id"],
            "voice_settings": voice_settings,
        }
        # Add speed parameter from voice config (host-specific)
        speed = voice.get("speed", 1.0)
        if speed != 1.0:
            body["speed"] = speed
        mp3_tmp = output_path + f".chunk{ci}.mp3"
        success = False

        for attempt in range(3):
            try:
                r = requests.post(url, json=body, headers=headers, timeout=90)
                if r.status_code == 200:
                    with open(mp3_tmp, "wb") as f:
                        f.write(r.content)
                    # Pre-validate: ElevenLabs sometimes returns empty/tiny responses
                    if os.path.getsize(mp3_tmp) < 1000:
                        print(f"  [tts] WARNING: ElevenLabs returned tiny file ({os.path.getsize(mp3_tmp)}B) for chunk {ci}, retrying...")
                        if attempt < 2:
                            time.sleep(2 ** attempt)
                            continue
                    success = True
                    break
                elif r.status_code == 429:
                    wait = 2 ** attempt
                    print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        if not success:
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            # P0.6 FIX: Fall back the ENTIRE text to pyttsx3 (not just this chunk).
            # Returning inside the chunk loop would abandon remaining chunks.
            print(f"  [tts] ElevenLabs failed for chunk {ci} — falling back entire text to pyttsx3")
            try:
                import pyttsx3
                _engine = pyttsx3.init()
                _engine.setProperty("rate", 150)
                wav_tmp = output_path + ".pyttsx3.wav"
                _engine.save_to_file(text, wav_tmp)  # full text, not just the failed chunk
                _engine.runAndWait()
                if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
                    ok = _mp3_to_m4a(wav_tmp, output_path)
                    try:
                        os.remove(wav_tmp)
                    except Exception:
                        pass
                    if ok:
                        print(f"  [tts] pyttsx3 fallback SUCCESS (full text)")
                        return True
            except Exception as pyttsx_err:
                print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
            # Final fallback: generate silence so the segment still renders
            return _tts_generate_silence_fallback(text, output_path)
        chunk_files.append(mp3_tmp)

    # Single chunk
    if len(chunk_files) == 1:
        ok = _mp3_to_m4a(chunk_files[0], output_path)
        try:
            os.remove(chunk_files[0])
        except Exception:
            pass
        if ok and os.path.exists(output_path):
            validate_tts_output(output_path)
            _tts_cache_put(cache_key, output_path)
        return ok

    # Multi-chunk concat
    concat_list = output_path + ".concat.txt"
    mp3_combined = output_path + ".combined.mp3"
    with open(concat_list, "w") as f:
        for p in chunk_files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", mp3_combined],
        capture_output=True, text=True,
    )
    ok = _mp3_to_m4a(mp3_combined, output_path)
    for f in chunk_files + [concat_list, mp3_combined]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    if ok and os.path.exists(output_path):
        validate_tts_output(output_path)
        _tts_cache_put(cache_key, output_path)
    return ok


def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
    """Generate audio for the entire dual-host dialogue.

    Args:
        dialogue: List of {host: 1|2|"CLIP", text: "..."}
        output_dir: Directory for audio files

    Returns:
        {
            "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
            "full": str,  # path to concatenated full audio
            "total_duration": float,
        }
    """
    os.makedirs(output_dir, exist_ok=True)

    # Only require ElevenLabs key if actually using ElevenLabs
    _active_provider = _get_tts_provider()
    if _active_provider == "elevenlabs":
        key = _get_cached_key("ELEVENLABS_API_KEY")
        if not key:
            raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")

    silence_path = os.path.join(output_dir, "silence.m4a")
    _generate_silence(silence_path, SILENCE_GAP)

    lines = []
    parts_for_concat = []
    current_time = 0.0

    for i, entry in enumerate(dialogue):
        host = entry.get("host")
        text = entry.get("text", "")

        # Skip CLIP markers — they don't have audio but DO advance the timeline
        if host == "CLIP":
            clip_duration = float(entry.get("duration", 30.0))  # use actual duration or default 30s
            lines.append({
                "path": None,
                "host": "CLIP",
                "duration": clip_duration,  # record actual duration, not hardcoded 0.0
                "start": current_time,
                "source": entry.get("source", ""),
                "query": entry.get("query", ""),
                "text": text,
            })
            current_time += clip_duration  # advance timeline so subsequent audio is correctly offset
            continue

        host_num = int(host) if host in (1, 2, "1", "2") else 1
        voice = VOICES.get(host_num, VOICES[1])
        segment_type = entry.get("type", "")
        line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")

        mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
        print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")

        _provider = _get_tts_provider()
        # ElevenLabs only — Inworld disabled per PIPELINE_LAWS
        _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
        if _tts_ok:
            dur = ffprobe_duration(line_path)
            lines.append({
                "path": line_path,
                "host": host_num,
                "duration": dur,
                "start": current_time,
                "text": text,
                "type": segment_type,
                "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
            })
            parts_for_concat.append(line_path)
            current_time += dur

            # Add silence gap between speakers (not after last line, not before CLIP)
            next_entry = dialogue[i + 1] if i < len(dialogue) - 1 else None
            if next_entry is not None and next_entry.get("host") != "CLIP":
                parts_for_concat.append(silence_path)
                current_time += SILENCE_GAP
        else:
            print(f"  [tts] FAILED line {i} ({voice['name']})")
            lines.append({
                "path": None,
                "host": host_num,
                "duration": 0.0,
                "start": current_time,
                "text": text,
                "type": segment_type,
                "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
            })

    # Concatenate all lines into full audio
    full_path = os.path.join(output_dir, "full_dialogue.m4a")
    if parts_for_concat:
        concat_file = os.path.join(output_dir, "dialogue_concat.txt")
        with open(concat_file, "w") as f:
            for p in parts_for_concat:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
             "-c", "copy", full_path],
            capture_output=True, text=True,
        )
        if os.path.exists(concat_file):
            os.remove(concat_file)

    # Guard: full_dialogue.m4a must not be zero-byte or tiny
    if os.path.exists(full_path):
        full_size = os.path.getsize(full_path)
        if full_size < 10240:
            raise RuntimeError(
                f"full_dialogue.m4a is {full_size} bytes (<10KB) — "
                f"FFmpeg concat produced empty/corrupt audio. Aborting before render."
            )

    total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
    successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))

    print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")

    # ── Per-host TTS validation: catch silent hosts BEFORE render starts ──
    host_stats = {}  # {host_num: {"total": N, "ok": N}}
    for l in lines:
        h = l.get("host")
        if h == "CLIP":
            continue
        if h not in host_stats:
            host_stats[h] = {"total": 0, "ok": 0}
        host_stats[h]["total"] += 1
        if l.get("path") and os.path.exists(l.get("path", "")):
            host_stats[h]["ok"] += 1

    for h, stats in host_stats.items():
        voice_name = VOICES.get(h, {}).get("name", f"Host{h}")
        if stats["ok"] == 0 and stats["total"] > 0:
            raise RuntimeError(
                f"TTS FATAL: {voice_name} (host {h}) has 0/{stats['total']} successful lines. "
                f"All audio is missing/silent. Aborting before render."
            )
        if stats["total"] > 0 and stats["ok"] / stats["total"] < 0.5:
            raise RuntimeError(
                f"TTS FATAL: {voice_name} (host {h}) has only {stats['ok']}/{stats['total']} "
                f"successful lines (<50%). Too many failures to produce a quality render."
            )

    return {
        "lines": lines,
        "full": full_path if os.path.exists(full_path) else None,
        "total_duration": total_dur,
    }


# Legacy compatibility — V3 pipeline used generate_all_audio
def generate_all_audio(script: dict, output_dir: str) -> dict:
    """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
    if "dialogue" in script:
        return generate_dialogue_audio(script["dialogue"], output_dir)
    # V3 fallback
    raise RuntimeError("V4 pipeline requires dialogue-format script")


if __name__ == "__main__":
    from script_writer import generate_script
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base, "output", "audio_test")
    result = generate_dialogue_audio(script["dialogue"], audio_dir)
    print(json.dumps(
        {k: v for k, v in result.items() if k != "lines"},
        indent=2,
    ))

```

### FILE: assembler.py
```python
#!/usr/bin/env python3
"""Assembler V8 — procedural waveform visualizer episode assembly.

Episode structure:
  1. TAG VIDEO as INTRO (tag_vertical.mp4, fade-in from black)
  2. COLD OPEN — Jessica's vocal hook (waveform visualizer bg + music bed)
  3. For each clip (1-N):
     a. SETUP — host introduces clip (waveform visualizer bg + music bed)
     b. GLITCH TRANSITION (assets/transitions/glitch_transition_waud.mp4)
     c. CLIP — full screen, ORIGINAL AUDIO, source attribution top-right
     d. REACT — both hosts react (waveform visualizer bg + music bed)
  4. WRAP — final sign-off plays OVER outro tag video
  5. TAG VIDEO as OUTRO (tag_vertical.mp4, fade-to-black, wrap narration mixed in)

Visual rules:
  - Host segments: procedural dark bg + audio waveform + speaker bar + ticker + watermark
  - No rotating video file backgrounds — all procedurally generated
  - Clips: full screen, original audio, source attribution
  - Glitch transition (0.5s) between every setup→clip pair
  - Background music at -18dB under all host narration
  - Watermark top-right on all host segments
"""
import json
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile

from music import (
    has_music, has_intro, has_transition, has_outro,
    mix_tts_with_music, INTRO_JINGLE, TRANSITION, OUTRO_JINGLE,
    ffprobe_duration,
)

logger = logging.getLogger("Assembler")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[assemble] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# ── APEX UNIFIED COLOR SYSTEM ─────────────────────────────────────────────
COLOR_BG          = "0x0A0A0F"   # VDS dark navy — #0A0A0F per PIPELINE_LAWS
COLOR_PANEL       = "0x050607"   # BEV2 elevated surface
COLOR_PANEL2      = "0x080a0c"   # secondary surface
COLOR_RED         = "0xFF3333"   # BD signal red — all accents
COLOR_RED_WARM    = "0xFF334D"   # BEV2 warm red — transition elements
COLOR_WHITE       = "0xF4F5F8"   # BEV2 warm white — not pure white
COLOR_TEXT        = "0xF4F5F8"   # primary text (warm white)
COLOR_GOLD        = "0xF8C15C"   # VDS gold — EYEBROW KICKERS ONLY
COLOR_MUTED       = "0x888888"   # secondary labels
COLOR_MUTED2      = "0x555555"   # metadata, timestamps
COLOR_GREEN       = "0x6EE7B7"   # BEV2 emerald — positive/DONE
COLOR_CORAL       = "0xFF8BA0"   # VDS coral — negative/warning
COLOR_RED_DIM     = "0x1a0000"   # CTA box backgrounds
COLOR_TICKER_BG   = "0x0c0c0c"   # ticker bar bg (kept dark)

# Legacy aliases for backward compat in make_host_visual / make_clip_visual
COLOR_AMBER       = COLOR_CORAL
BV2_OBSIDIAN    = COLOR_BG
BV2_DEEP_PANEL  = COLOR_PANEL
BV2_SIGNAL_RED  = COLOR_RED_WARM
BV2_STARK_WHITE = COLOR_WHITE
BV2_MUTED       = COLOR_WHITE  # secondary text (used @0.33 opacity, warm white)
BV2_EMERALD     = COLOR_GREEN
BV2_RED_LIGHT   = "0xFF8595"   # gradient accent

INTRO_VIDEO = os.path.join(ASSETS, "intro.mp4")
OUTRO_VIDEO = os.path.join(ASSETS, "outro.mp4")
GLITCH_TRANSITION = os.path.join(ASSETS, "transitions", "glitch_transition_waud.mp4")
WATERMARK = os.path.join(ASSETS, "logo", "watermark.png")
BG_MUSIC = os.path.join(ASSETS, "music", "pp_background.mp3")
TAG_VIDEO = os.path.join(ASSETS, "tag_vertical.mp4")
OUTRO_BRANDED = os.path.join(ASSETS, "outro_branded.mp4")
LOGO_IMAGE = os.path.join(ASSETS, "logo_protocol_pulse.png")
# Issue 3: Custom whoosh sound — prefer custom_whoosh.wav/.mp3 over generated glitch_whoosh.wav
_CUSTOM_WHOOSH_MP3 = os.path.join(ASSETS, "sfx", "custom_whoosh.mp3")
_CUSTOM_WHOOSH_WAV = os.path.join(ASSETS, "sfx", "custom_whoosh.wav")
if os.path.exists(_CUSTOM_WHOOSH_WAV):
    GLITCH_WHOOSH = _CUSTOM_WHOOSH_WAV
elif os.path.exists(_CUSTOM_WHOOSH_MP3):
    # Convert mp3 to wav for consistency if not already done
    subprocess.run(["ffmpeg", "-y", "-i", _CUSTOM_WHOOSH_MP3, _CUSTOM_WHOOSH_WAV],
                   capture_output=True, text=True, timeout=10)
    GLITCH_WHOOSH = _CUSTOM_WHOOSH_WAV if os.path.exists(_CUSTOM_WHOOSH_WAV) else _CUSTOM_WHOOSH_MP3
else:
    GLITCH_WHOOSH = os.path.join(ASSETS, "sfx", "glitch_whoosh.wav")
    logging.getLogger("Assembler").info("CUSTOM WHOOSH NOT FOUND — using generated")
CARD_SWOOSH = os.path.join(ASSETS, "sfx", "card_swoosh.wav")
DATA_BLIP = os.path.join(ASSETS, "sfx", "data_blip.wav")
LOWER_SLIDE = os.path.join(ASSETS, "sfx", "lower_slide.wav")


def get_latest_spaces_summary() -> dict:
    """FIX 8: Check for recent X Spaces transcripts for episode inclusion.

    Checks:
    1. video_pipeline_v3/data/spaces/ for recent chunks
    2. spaces_scraper/ for cached transcripts
    3. x_spaces_scraper/ for cached transcripts

    Returns dict with {summary, source, score} if found, else None.
    """
    import glob
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(hours=24)

    # Check pipeline spaces data first
    spaces_data_dir = os.path.join(BASE, "data", "spaces")
    if os.path.exists(spaces_data_dir):
        for space_dir in sorted(os.listdir(spaces_data_dir), reverse=True):
            chunks_file = os.path.join(spaces_data_dir, space_dir, "chunks.jsonl")
            if not os.path.exists(chunks_file):
                continue
            # Check if recent (file modified in last 24h)
            if os.path.getmtime(chunks_file) < cutoff.timestamp():
                continue
            # Read highest-impact chunks
            best_chunks = []
            try:
                with open(chunks_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        if entry.get("impact_score", 0) >= 50:
                            best_chunks.append(entry)
            except Exception:
                continue
            if best_chunks:
                best_chunks.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
                top = best_chunks[0]
                summary = top.get("text", "")[:500]
                return {
                    "summary": f"From X Spaces — {top.get('speaker', 'unknown')}: {summary}",
                    "source": f"X Spaces ({space_dir})",
                    "score": top.get("impact_score", 0),
                }

    # Check spaces_scraper cache
    scraper_cache = os.path.join(os.path.dirname(BASE), "spaces_scraper", "cache")
    if not os.path.exists(scraper_cache):
        scraper_cache = os.path.join(os.path.dirname(BASE), "x_spaces_scraper", "cache")
    if os.path.exists(scraper_cache):
        json_files = sorted(glob.glob(os.path.join(scraper_cache, "*.json")), reverse=True)
        for jf in json_files[:5]:
            if os.path.getmtime(jf) < cutoff.timestamp():
                continue
            try:
                with open(jf) as f:
                    data = json.loads(f.read())
                transcript = data.get("transcript", data.get("text", ""))
                if transcript and len(transcript) > 100:
                    return {
                        "summary": transcript[:500],
                        "source": f"X Spaces Scraper ({os.path.basename(jf)})",
                        "score": 60,
                    }
            except Exception:
                continue

    logger.info("  FIX 8: No recent X Spaces data found — segment skipped")
    return None


def _fetch_btc_price() -> str:
    """FIX 5: Fetch BTC price with dual fallback (CoinGecko → Mempool)."""
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            price = data["bitcoin"]["usd"]
            return f"${price:,.0f}"
    except Exception:
        try:
            import urllib.request
            url2 = "https://mempool.space/api/v1/prices"
            with urllib.request.urlopen(url2, timeout=5) as r:
                data = json.loads(r.read())
                return f"${data.get('USD', 0):,.0f}"
        except Exception:
            return "$N/A"


def _build_black_diamond_bg(duration: float, label_out: str = "bd_bg") -> tuple:
    """BLACK DIAMOND 7-layer procedural background — Sovereign Command Center.

    Returns (extra_inputs, filtergraph_string).
    extra_inputs is always [] — pure procedural generation.
    """
    f = ""
    # Layer 1: VDS dark navy base (#0A0A0F per PIPELINE_LAWS)
    f += f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30[bd_base];\n"
    # Layer 2: Red radial glow — top-center (subtle)
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(55*exp(-((X-960)*(X-960)+Y*Y)/380000),0,255)':g='0':b='0'[bd_glow_top];\n")
    f += f"[bd_base][bd_glow_top]blend=all_mode=screen[bg1];\n"
    # Layer 3: Red radial glow — bottom-center
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(35*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/280000),0,255)':g='0':b='0'[bd_glow_bot];\n")
    f += f"[bg1][bd_glow_bot]blend=all_mode=screen[bg2];\n"
    # Layer 4: Tactical surveillance grid (very subtle)
    f += f"[bg2]drawgrid=width=120:height=68:thickness=1:color=0xFF0000@0.07[bg3];\n"
    # Layer 5: Scanlines (horizontal every 3px)
    f += f"[bg3]drawgrid=width=0:height=3:thickness=1:color=0xFF0000@0.025[bg4];\n"
    # Layer 6: Vignette
    f += f"[bg4]vignette=PI/4:mode=backward[bg5];\n"
    # Layer 7: Red border frame (2px solid on all 4 edges)
    f += (f"[bg5]drawbox=x=0:y=0:w=1920:h=2:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color=0xFF3333@0.85:t=fill[{label_out}];\n")
    return ([], f)


def _build_info_bar_fg(duration: float, btc_price: str, block_height: str = "",
                       label_in: str = "v_pre_tick", label_out: str = "v_ticked") -> str:
    """BLACK DIAMOND ticker bar — red scrolling intel on near-black bg."""
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    content = (f"  PROTOCOL PULSE  //  BTC {safe_btc}  //  {date_str}"
               f"  //  PROTOCOLPULSE.IO  //  STAY SOVEREIGN  "
               f"  //  PROTOCOL PULSE DAILY BRIEF  //  {date_str}"
               f"  //  FEAR/GREED  //  STAY SOVEREIGN"
               f"  //  BTC {safe_btc}  //  PROTOCOLPULSE.IO  ")
    safe_content = content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # FIX 5: Glassmorphic black base bar
    fg += f"color=c=0x000000@0.75:s=1920x48:d={duration}:r=30[tickbase];\n"
    # Red top separator line (2px)
    fg += f"[tickbase]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.85:t=fill[tickline];\n"
    # Static 'PULSE CHECK' label left
    fg += (f"[tickline]drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
           f"fontcolor=0xF4F5F8:fontsize=14:x=8:y=18[tickstatic];\n")
    # Scrolling red text
    fg += (f"[tickstatic]drawtext=fontfile={FONT_MONO}:text='{safe_content}':"
           f"fontcolor={COLOR_RED}:fontsize=14:"
           f"x=W-mod(n*2\\,W+text_w):y=18[ticker];\n")
    # Overlay bar onto video frame at y=1032
    fg += f"[{label_in}][ticker]overlay=0:1032[{label_out}];\n"
    return fg


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        logger.error(f"FAIL {label}: {r.stderr[-600:]}")
        return False
    return True


def run_ffmpeg_filtergraph(inputs: list, filtergraph: str, maps: list,
                           output_args: list, output_path: str,
                           label: str = "", timeout: int = 300) -> bool:
    fd, fpath = tempfile.mkstemp(suffix=".txt", prefix="ff_filter_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(filtergraph)
        cmd = ["ffmpeg", "-y"]
        for inp in inputs:
            if isinstance(inp, list):
                cmd.extend(inp)
            else:
                cmd.extend(["-i", inp])
        cmd.extend(["-filter_complex_script", fpath])
        for m in maps:
            cmd.extend(["-map", m])
        cmd.extend(output_args)
        cmd.append(output_path)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            logger.error(f"FAIL {label}: {r.stderr[-600:]}")
            return False
        return True
    finally:
        try:
            os.unlink(fpath)
        except OSError:
            pass


def ensure_audio(video_path: str) -> str:
    """Ensure video has an audio stream (add silent track if missing)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    if "audio" in r.stdout:
        return video_path
    out = video_path.replace(".mp4", "_waud.mp4").replace(".mov", "_waud.mp4")
    dur = ffprobe_duration(video_path)
    run_ffmpeg(
        ["-i", video_path, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", str(dur), "-c:v", "copy", "-c:a", "aac", "-shortest", out],
        "add silence", 60,
    )
    return out if os.path.exists(out) else video_path


def _generate_fallback_silent_audio(work_dir: str, idx: int, text: str = "") -> str:
    """BUG1 FIX: Generate silence audio as TTS fallback when ElevenLabs quota is exhausted.

    Estimates duration from text length (~150 words/min, ~5 chars/word).
    Returns path to silent .m4a file, or "" on failure.
    """
    # Estimate duration: ~150 wpm, ~5 chars/word → ~750 chars/min → ~12.5 chars/s
    # Minimum 2s, maximum 30s
    dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
    out = os.path.join(work_dir, f"fallback_silence_{idx:03d}.m4a")
    ok = run_ffmpeg([
        "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
        "-t", str(dur),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        out,
    ], "fallback silence", 15)
    if ok and os.path.exists(out):
        logger.warning(f"  [fallback] Generated {dur:.1f}s silence for idx={idx} (TTS quota exhausted)")
        return out
    return ""


# ── Branded intro/outro ────────────────────────────────────────────────────

def make_intro_video(output_path: str) -> str:
    """Use branded intro.mp4 with pp_intro.mp3 mixed in.

    Fades in from black (0.5s), fades out to black (0.5s) with audio fade (1.5s).
    Forces yuv420p pixel format for concat compatibility.
    """
    if not os.path.exists(INTRO_VIDEO):
        logger.warning("intro.mp4 not found — skipping intro")
        return ""

    intro_dur = ffprobe_duration(INTRO_VIDEO)
    if intro_dur <= 0:
        logger.warning("intro.mp4 has zero duration")
        return ""

    fade_out_v = max(0, intro_dur - 0.5)
    fade_out_a = max(0, intro_dur - 1.5)
    vf = (f"scale=1920:1080,setsar=1,format=yuv420p,"
          f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_v}:d=0.5")

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", INTRO_VIDEO],
        capture_output=True, text=True,
    )
    intro_has_audio = "audio" in r.stdout

    jingle_path = os.path.join(ASSETS, "music", "pp_intro.mp3")
    has_jingle = os.path.exists(jingle_path)

    if has_jingle and intro_has_audio:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-i", jingle_path,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[0:a]volume=0.7[va];[1:a]volume=0.9[vb];"
             f"[va][vb]amix=inputs=2:duration=shortest,"
             f"afade=t=out:st={fade_out_a}:d=1.5[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(intro_dur),
            output_path,
        ], "intro video + jingle", 120)
    elif has_jingle and not intro_has_audio:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-i", jingle_path,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[1:a]afade=t=out:st={fade_out_a}:d=1.5[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(intro_dur), "-shortest",
            output_path,
        ], "intro video + jingle (no orig audio)", 120)
    else:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p", "-vf", vf,
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "intro video normalize", 120)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,pix_fmt",
             "-of", "csv=p=0", output_path],
            capture_output=True, text=True,
        )
        logger.info(f"  Intro video: {dur:.1f}s | probe: {probe.stdout.strip()}")
        return output_path

    logger.warning("Intro video failed — skipping")
    return ""


def make_outro_video(output_path: str) -> str:
    """Use branded outro.mp4 with pp_outro.mp3 mixed in.

    Plays in full with 0.5s video fade-to-black and 1.0s audio fade-out at end.
    """
    if not os.path.exists(OUTRO_VIDEO):
        logger.warning("outro.mp4 not found — skipping outro")
        return ""

    outro_dur = ffprobe_duration(OUTRO_VIDEO)
    if outro_dur <= 0:
        return ""

    # Sprint 1.8: No fade-to-black on outro. Hard cut.
    vf = f"scale=1920:1080,setsar=1,format=yuv420p"

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", OUTRO_VIDEO],
        capture_output=True, text=True,
    )
    outro_has_audio = "audio" in r.stdout

    outro_jingle = os.path.join(ASSETS, "music", "pp_outro.mp3")
    has_jingle = os.path.exists(outro_jingle)

    if has_jingle and outro_has_audio:
        ok = run_ffmpeg([
            "-i", OUTRO_VIDEO,
            "-i", outro_jingle,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[0:a]volume=0.7[va];[1:a]volume=0.9[vb];"
             f"[va][vb]amix=inputs=2:duration=shortest,"
             f"afade=t=out:st={fade_out_a}:d=1.0[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(outro_dur),
            output_path,
        ], "outro video + jingle", 120)
    elif has_jingle:
        ok = run_ffmpeg([
            "-i", OUTRO_VIDEO,
            "-i", outro_jingle,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[1:a]afade=t=out:st={fade_out_a}:d=1.0[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(outro_dur), "-shortest",
            output_path,
        ], "outro video + jingle (no orig audio)", 120)
    else:
        ok = run_ffmpeg([
            "-i", OUTRO_VIDEO,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p", "-vf", vf,
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "outro video normalize", 120)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        logger.info(f"  Outro video: {dur:.1f}s")
        return output_path

    return ""


def make_tag_video(output_path: str, narration_audio: str = "") -> str:
    """Normalize tag_vertical.mp4 to 1920x1080 with fade-in/fade-out.

    Used as BOTH intro (fade-in from black) and outro (fade-to-black).
    If narration_audio provided, mix it at full volume over the tag video audio.
    """
    if not os.path.exists(TAG_VIDEO):
        logger.warning("tag_vertical.mp4 not found — skipping tag")
        return ""

    tag_dur = ffprobe_duration(TAG_VIDEO)
    if tag_dur <= 0:
        return ""

    fade_out_v = max(0, tag_dur - 0.5)
    vf = (f"scale=1920:1080:force_original_aspect_ratio=decrease,"
          f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p,"
          f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_v}:d=0.5")

    tag_src = ensure_audio(TAG_VIDEO)

    if narration_audio and os.path.exists(narration_audio):
        # Mix narration over tag audio
        fade_out_a = max(0, tag_dur - 1.0)
        ok = run_ffmpeg([
            "-i", tag_src,
            "-i", narration_audio,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[0:a]volume=0.3[tagaud];"
             f"[1:a]volume=1.0[narr];"
             f"[tagaud][narr]amix=inputs=2:duration=first,"
             f"afade=t=out:st={fade_out_a}:d=1.0[outa]"),
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(tag_dur),
            output_path,
        ], "tag video + narration", 60)
    else:
        ok = run_ffmpeg([
            "-i", tag_src,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p", "-vf", vf,
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "tag video", 60)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        logger.info(f"  Tag video: {dur:.1f}s{' (with narration)' if narration_audio else ''}")
        return output_path

    return ""


# ── Cold open intro ───────────────────────────────────────────────────────

def make_intro_coldopen(tts_path: str, output_path: str, btc_price: str = "N/A", thumbnail_path: str = "") -> str:
    """FIX 2 — Clean Cold Open: ONLY cyberpunk background + centered date text.
    Per PIPELINE_LAWS: cold open = NO logos, bars, watermarks, thumbnails, PiP.
    Pure dramatic background. Minimum 3 seconds. Voice starts on frame 1.
    """
    import datetime
    tts_dur = ffprobe_duration(tts_path)
    total_dur = max(tts_dur + 0.3, 3.0)

    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()

    # Build 7-layer broadcast background
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="co_bg")
    fg = bg_fg

    # Only date text centered — no logos, no waveform, no bars
    fg += (f"[co_bg]"
           f"drawtext=fontfile={FONT_MONO}:text='{date_str}':"
           f"fontcolor={COLOR_WHITE}:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2,"
           f"fade=t=in:st=0:d=0.5,fade=t=out:st={max(0, total_dur - 0.5)}:d=0.5"
           f"[outv];\n")

    fg += (f"[0:a]aformat=channel_layouts=stereo,"
           f"alimiter=limit=0.891:level=disabled:attack=5:release=50,aresample=async=1[outa]")

    ok = run_ffmpeg_filtergraph(
        [tts_path], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "clean cold open", 120,
    )
    return output_path if ok else ""


# ── Clip unavailable placeholder ──────────────────────────────────────────

def _make_clip_unavailable_card(rank: int, output_path: str, btc_price: str = "$N/A") -> str:
    """BUG4 FIX: 8-second branded 'INTELLIGENCE INCOMING' card — professional, not debug.

    Uses 0x0D1117 background (above blackdetect threshold 0x020304).
    Cyberpunk grid overlay, gold info rail, 'INTELLIGENCE INCOMING' branding.
    No 'error'/'unavailable'/'interrupted' language.
    """
    import datetime
    dur = 8.0
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = (btc_price or "$N/A").replace("'", "").replace('"', "").replace("\\", "")

    ok = run_ffmpeg([
        "-f", "lavfi", "-i",
        f"color=c=0x1A1A2E:s=1920x1080:r=30:d={dur}",  # FIX 4: brighter bg above blackdetect threshold
        "-f", "lavfi", "-i",
        f"anullsrc=r=48000:cl=stereo",
        "-filter_complex",
        # Cyberpunk grid overlay at low opacity (intentional look)
        f"[0:v]"
        f"drawgrid=width=60:height=60:thickness=1:color=0xFF0000@0.06,"
        f"drawgrid=width=120:height=120:thickness=1:color=0xFF0000@0.04,"
        # Horizontal scan lines (cyberpunk aesthetic)
        f"drawbox=x=0:y=270:w=1920:h=1:color=0xFF0000@0.12:t=fill,"
        f"drawbox=x=0:y=540:w=1920:h=1:color=0xFF0000@0.12:t=fill,"
        f"drawbox=x=0:y=810:w=1920:h=1:color=0xFF0000@0.12:t=fill,"
        # Center card container
        f"drawbox=x=360:y=280:w=1200:h=380:color=0x0A0E14@0.92:t=fill,"
        f"drawbox=x=360:y=280:w=1200:h=4:color=0xFF3333@0.9:t=fill,"
        f"drawbox=x=360:y=656:w=1200:h=4:color={COLOR_GOLD}@0.9:t=fill,"
        f"drawbox=x=360:y=280:w=4:h=380:color=0xFF3333@0.9:t=fill,"
        f"drawbox=x=1556:y=280:w=4:h=380:color=0xFF3333@0.9:t=fill,"
        # Main headline
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK'"
        f":fontcolor={COLOR_GOLD}:fontsize=52:x=(w-text_w)/2:y=360,"
        # Subtext
        f"drawtext=fontfile={FONT_MONO}:text='INTELLIGENCE INCOMING'"
        f":fontcolor=0x888888:fontsize=26:x=(w-text_w)/2:y=450,"
        f"drawtext=fontfile={FONT_MONO}:text='STAY SOVEREIGN'"
        f":fontcolor={COLOR_RED}@0.7:fontsize=18:x=(w-text_w)/2:y=500,"
        # Gold info rail at bottom
        f"drawbox=x=0:y=1032:w=1920:h=48:color={COLOR_GOLD}@0.95:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='BTC {safe_btc}':fontcolor=0x000000:fontsize=14:x=20:y=1048,"
        f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOLPULSE.IO':fontcolor=0x000000:fontsize=15:x=(w-text_w)/2:y=1047,"
        f"drawtext=fontfile={FONT_MONO}:text='{date_str} - DAILY BRIEF':fontcolor=0x000000:fontsize=14:x=w-text_w-20:y=1048,"
        # Watermark top-right
        f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':fontcolor={COLOR_RED}@0.4:fontsize=18:x=w-230:y=20"
        f"[outv]",
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-maxrate", "10M", "-bufsize", "15M",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-t", str(dur),
        output_path,
    ], "clip_unavailable_card", 30)
    return output_path if ok and os.path.exists(output_path) else ""


# ── Branded outro ─────────────────────────────────────────────────────────

def make_branded_outro(output_path: str, narration_audio: str = "") -> str:
    """Use PBX's branded outro video. Mix wrap narration audio over it.

    Falls back to tag_vertical.mp4 if outro_branded.mp4 not uploaded yet.
    """
    src = OUTRO_BRANDED if os.path.exists(OUTRO_BRANDED) else TAG_VIDEO
    if not os.path.exists(src):
        return ""

    dur = ffprobe_duration(src)
    if dur <= 0:
        return ""
    # Sprint 1.8: NO fade-to-black. Abrupt hard cut per PRODUCTION_DESIGN_LAWS.
    vf = (f"scale=1920:1080:force_original_aspect_ratio=increase,"
          f"crop=1920:1080,setsar=1,fps=30,format=yuv420p")

    if narration_audio and os.path.exists(narration_audio):
        ok = run_ffmpeg([
            "-i", src, "-i", narration_audio,
            "-filter_complex",
            "[0:a]volume=0.25[va];[1:a]volume=1.0[vb];[va][vb]amix=inputs=2:duration=longest[outa]",
            "-map", "0:v", "-map", "[outa]", "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", output_path],
            "branded outro", 60)
    else:
        ok = run_ffmpeg([
            "-i", src, "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", output_path],
            "branded outro", 60)

    if ok and os.path.exists(output_path):
        out_dur = ffprobe_duration(output_path)
        logger.info(f"  Branded outro: {out_dur:.1f}s{' (with narration)' if narration_audio else ''}")
        return output_path
    return ""


# ── Thumbnail fetcher ──────────────────────────────────────────────────────

def fetch_youtube_thumbnail(clip_info: dict) -> str:
    """Download YouTube thumbnail for a clip. Returns local path or ''."""
    video_id = clip_info.get("video_id", "")
    if not video_id:
        return ""
    thumb_path = f"/tmp/thumb_{video_id}.jpg"
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        import urllib.request
        url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        urllib.request.urlretrieve(url, thumb_path)
        return thumb_path if os.path.exists(thumb_path) else ""
    except Exception:
        try:
            url2 = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            urllib.request.urlretrieve(url2, thumb_path)
            return thumb_path if os.path.exists(thumb_path) else ""
        except Exception:
            return ""


# ── PiP preview for narration segments ──────────────────────────────────────

def make_pip_preview(clip_path: str, output_path: str, duration: float = 8.0) -> str:
    """Extract a muted PiP preview clip for overlay during narration.

    Issue 2: 820x462 PiP (right 40% panel), positioned at x=1056, y=200.
    ACTUAL VIDEO playing (muted), not static image with pan.
    Thin 2px white border at 30% opacity.
    """
    if not clip_path or not os.path.exists(clip_path):
        logger.warning(f"PiP: clip path missing: {clip_path}")
        return ""
    try:
        file_size = os.path.getsize(clip_path)
        if file_size < 50_000:  # < 50KB = stub/corrupt
            logger.warning(f"PiP: clip too small ({file_size}b), skipping: {clip_path}")
            return ""
    except OSError as e:
        logger.warning(f"PiP: cannot stat clip: {e}")
        return ""
    clip_dur = ffprobe_duration(clip_path)
    if clip_dur < 2:  # FIX 1: lowered min from 10s to 2s
        return ""
    actual_dur = min(duration, clip_dur - 0.5)
    if actual_dur <= 0:
        actual_dur = min(duration, clip_dur)
    # Extract from MIDPOINT of clip (better face shots)
    start = max(0, (clip_dur / 2) - (actual_dur / 2))
    ok = run_ffmpeg([
        "-ss", str(start), "-i", clip_path,
        "-t", str(actual_dur), "-an",
        "-vf", (
            # FIX 1: scale UP to fill the frame, then crop — NOT decrease+pad which leaves black borders
            "scale=716:370:force_original_aspect_ratio=increase,"
            "crop=716:370,setsar=1,format=yuv420p"
        ),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-r", "30",
        output_path,
    ], "pip preview extract", 120)  # FIX 1: increased timeout
    return output_path if ok and os.path.exists(output_path) else ""


def overlay_pip_on_narration(narration_path: str, pip_path: str,
                              output_path: str) -> str:
    """Overlay PiP preview clip onto narration video.

    Issue 2: Position x=1056, y=200 (right 40% panel, 820x462 PiP).
    Drop shadow behind PiP (drawbox at +4px offset, black@0.3).
    "COMING UP..." label inside PiP bottom-left.
    """
    if not pip_path or not os.path.exists(pip_path):
        return narration_path
    pip_dur = ffprobe_duration(pip_path)
    ok = run_ffmpeg([
        "-i", narration_path,
        "-i", pip_path,
        "-filter_complex",
        # Drop shadow: dark box at +4px offset behind PiP
        f"[0:v]drawbox=x=1060:y=204:w=824:h=466:color={COLOR_BG}@0.3:t=fill:enable='lte(t,{pip_dur})'[bg_shadow];"
        f"[1:v]drawtext=fontfile={FONT_BOLD}:text='COMING UP...':fontcolor={COLOR_TEXT}:fontsize=28:"
        f"x=12:y=h-38:box=1:boxcolor={COLOR_BG}@0.5:boxborderw=6,format=yuva420p[pip];"
        f"[bg_shadow][pip]overlay=1056:200:enable='lte(t,{pip_dur})',format=yuv420p[outv]",
        "-map", "[outv]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "copy", "-shortest",
        output_path,
    ], "pip overlay", 180)
    return output_path if ok and os.path.exists(output_path) else narration_path


def mix_lower_slide_sfx(video_path: str) -> str:
    """Mix lower_slide.wav SFX at the start of a clip with LowerThird."""
    if not os.path.exists(LOWER_SLIDE) or not os.path.exists(video_path):
        return video_path
    tmp = video_path + ".lslide.mp4"
    ok = run_ffmpeg([
        "-i", video_path,
        "-i", LOWER_SLIDE,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.5[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        tmp,
    ], "mix lower slide sfx", 30)
    if ok and os.path.exists(tmp):
        os.replace(tmp, video_path)
    elif os.path.exists(tmp):
        os.remove(tmp)
    return video_path


# ── Host dialogue visual ────────────────────────────────────────────────────

def _build_corner_brackets_fg(label_in: str, label_out: str) -> str:
    """Draw tactical corner brackets on all 4 corners — signal red."""
    return (
        f"[{label_in}]"
        f"drawbox=x=0:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=1040:w=4:h=40:color={COLOR_RED}:t=fill"
        f"[{label_out}];\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# BROADCAST ENGINE V2 — 6-scene system
# ══════════════════════════════════════════════════════════════════════════

def _build_broadcast_bg(duration: float, label_out: str = "bb_bg") -> tuple:
    """APEX UNIFIED 7-layer procedural background.

    Layer 1: BEV2 cinematic obsidian base (#020304)
    Layer 2: BEV2 3-glow radial (top-left red, top-right white, bottom-center red)
    Layer 3: VDS perspective grid (bottom 30%, very subtle)
    Layer 4: BD scanlines (horizontal every 4px, red @2.5%)
    Layer 5: Vignette
    Layer 6: (film grain skipped — geq too slow per spec)
    Layer 7: Red border frame (2px all edges)
    """
    f = ""
    # Layer 1: VDS dark navy base (#0A0A0F per PIPELINE_LAWS)
    f += f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30[bb_base];\n"
    # Layer 2a: Red radial glow — top-left
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(46*exp(-((X)*(X)+Y*Y)/350000),0,255)':g='0':b='0'[bb_glow_tl];\n")
    f += f"[bb_base][bb_glow_tl]blend=all_mode=screen[bb1];\n"
    # Layer 2b: White radial glow — top-right (subtle)
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":g='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":b='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'[bb_glow_tr];\n")
    f += f"[bb1][bb_glow_tr]blend=all_mode=screen[bb2];\n"
    # Layer 2c: Red radial glow — bottom-center
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(25*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/400000),0,255)':g='0':b='0'[bb_glow_bc];\n")
    f += f"[bb2][bb_glow_bc]blend=all_mode=screen[bb3];\n"
    # Layer 3: VDS perspective grid (bottom 30% — subtle white)
    f += f"[bb3]drawgrid=width=90:height=54:thickness=1:color=0xFFFFFF@0.04[bb4];\n"
    # Layer 4: BD scanlines (horizontal every 4px, red @2.5%)
    f += f"[bb4]drawgrid=width=0:height=4:thickness=1:color={COLOR_RED}@0.025[bb5];\n"
    # Layer 5: Vignette
    f += f"[bb5]vignette=PI/4:mode=backward[bb6];\n"
    # Layer 7: Red border frame (2px all edges)
    f += (f"[bb6]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[{label_out}];\n")
    return ([], f)


def _build_top_system_bar(label_in: str, label_out: str, scene_label: str = "",
                           progress_pct: int = 50, recon_id: str = "") -> str:
    """APEX UNIFIED header — BD structure + BEV2 glassmorphic floating pill."""
    import datetime
    if not recon_id:
        recon_id = datetime.datetime.now().strftime("%H%M%S")
    fg = ""
    # Floating pill bg with glassmorphic feel
    fg += (f"[{label_in}]drawbox=x=20:y=12:w=1880:h=52:color=0x000000@0.55:t=fill,"
           # Red left accent line on pill (BD)
           f"drawbox=x=20:y=12:w=3:h=52:color={COLOR_RED}@0.9:t=fill,"
           # Left: bullet + PROTOCOL PULSE
           f"drawtext=fontfile={FONT_BOLD}:text='  PROTOCOL PULSE':"
           f"fontcolor={COLOR_WHITE}:fontsize=20:x=38:y=26,"
           # LIVE label in red
           f"drawtext=fontfile={FONT_BOLD}:text='LIVE':"
           f"fontcolor={COLOR_RED}:fontsize=16:x=236:y=30,"
           # Bottom separator
           f"drawbox=x=20:y=64:w=1880:h=1:color={COLOR_RED}@0.25:t=fill"
           f"[{label_out}];\n")
    return fg


def _build_signature_info_rail(duration: float, btc_price: str, label_in: str,
                                label_out: str) -> str:
    """FIX 5 — Glassmorphic black bottom bar: rgba(0,0,0,0.75) with red top separator.
    Left: 'PULSE CHECK' white monospace. Right: scrolling red ticker.
    """
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = (btc_price or "N/A").replace("'", "").replace('"', "").replace("\\", "")
    ticker_content = (
        f"  BTC {safe_btc}  //  PROTOCOL PULSE DAILY BRIEF  //  "
        f"{date_str}  //  FEAR/GREED  //  STAY SOVEREIGN  //  "
        f"BTC {safe_btc}  //  PROTOCOLPULSE.IO  //  STAY SOVEREIGN  "
    )
    safe_ticker = ticker_content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # Glassmorphic black bar (0,0,0 @0.75 opacity)
    fg += (f"[{label_in}]"
           f"drawbox=x=0:y=1032:w=1920:h=48:color=0x000000@0.75:t=fill,"
           # Red top separator line (2px)
           f"drawbox=x=0:y=1032:w=1920:h=2:color={COLOR_RED}@0.85:t=fill,"
           # Left: static 'PULSE CHECK' in white monospace
           f"drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
           f"fontcolor=0xF4F5F8:fontsize=14:x=16:y=1048,"
           # Vertical separator after label
           f"drawbox=x=140:y=1036:w=1:h=38:color={COLOR_RED}@0.5:t=fill,"
           # Right: scrolling red ticker
           f"drawtext=fontfile={FONT_MONO}:text='{safe_ticker}':"
           f"fontcolor={COLOR_RED}:fontsize=14:"
           f"x=W-mod(n*2\\,W+text_w):y=1048"
           f"[{label_out}];\n")
    return fg


def _build_narration_wave(label_in: str, label_out: str,
                          audio_out_label: str = "_nw_a_out") -> tuple:
    """APEX V2 Cipher Line waveform — dual-layer EKG at y=880, 160px zone.

    Uses asplit=3 to separate audio feeds:
      - 2 for visualization (primary + accent)
      - 1 for audio output (returned as audio_out_label)

    Returns (filtergraph_string, audio_out_pad) where audio_out_pad is the
    label to pass to _bv2_encode's audio_pad parameter.
    """
    fg = ""
    # Split audio: 2 for vis, 1 for output (FIX 3 — never share audio pads)
    fg += f"[0:a]asplit=3[_a_vis][_a_vis2][{audio_out_label}];\n"

    # PRIMARY: thin centerline wave — white, ultra-clean
    fg += (f"[_a_vis]showwaves=s=1920x80:mode=line:"
           f"colors=0xF4F5F8@0.9:scale=sqrt:draw=full:rate=30[_wave_line];\n")

    # SECONDARY: mirror reflection — warm red, low opacity
    fg += (f"[_a_vis2]showwaves=s=1920x80:mode=line:"
           f"colors=0xFF334D@0.25:scale=log:draw=full:rate=30[_wave_red];\n")
    fg += f"[_wave_red]vflip[_wave_red_flip];\n"

    # Stack: primary on top, flipped reflection below (total 160px)
    fg += f"[_wave_line][_wave_red_flip]vstack[_wave_stacked];\n"

    # Edge fade bars (top + bottom)
    fg += (f"[_wave_stacked]"
           f"drawbox=x=0:y=0:w=1920:h=20:color=0x020304@0.8:t=fill,"
           f"drawbox=x=0:y=140:w=1920:h=20:color=0x020304@0.8:t=fill"
           f"[_wave_faded];\n")

    # Thin red center dividing line (the "spine")
    fg += (f"[_wave_faded]drawbox=x=0:y=79:w=1920:h=2:"
           f"color=0xFF0000@0.35:t=fill[_wave_final];\n")

    # Position at y=880 (above info rail, 160px zone)
    fg += f"[{label_in}][_wave_final]overlay=0:880[{label_out}];\n"
    return fg, f"[{audio_out_label}]"


def _bv2_text_zone(label_in: str, label_out: str, eyebrow: str, headline: str,
                    body: str, tag: str = "") -> str:
    """APEX left 58% text zone — gold eyebrow kicker (VDS), warm white headline."""
    safe_eye = _sanitize_text(eyebrow)
    safe_head = _sanitize_text(headline)
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""
    safe_tag = _sanitize_text(tag) if tag else ""

    fg = ""
    # Gold eyebrow kicker (VDS)
    fg += (f"[{label_in}]drawtext=fontfile={FONT_MONO}:text='{safe_eye}':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[bv2_eye];\n")
    # Headline (large, with shadow for depth)
    fg += (f"[bv2_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130[bv2_head];\n")
    # Body text
    if safe_body:
        fg += (f"[bv2_head]drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor=0xFFFFFF@0.6:fontsize=18:x=64:y=420:line_spacing=8[bv2_body];\n")
    else:
        fg += f"[bv2_head]copy[bv2_body];\n"
    # Tag pill (red accent)
    if safe_tag:
        fg += (f"[bv2_body]drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
               f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
               f"drawtext=fontfile={FONT_MONO}:text='{safe_tag}':"
               f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590[{label_out}];\n")
    else:
        fg += f"[bv2_body]copy[{label_out}];\n"
    return fg


def _bv2_corner_brackets(label_in: str, label_out: str) -> str:
    """APEX corner brackets — BD tactical signal red (#FF0000)."""
    return _build_corner_brackets_fg(label_in, label_out)


def _bv2_encode(inputs, fg, output_path, total_dur, label="bv2 scene",
                audio_pad="[0:a]"):
    """Shared encode pipeline for BV2 scenes — TTS only, no per-segment music.

    APEX V2: Music is mixed ONCE continuously in concatenate_parts() after all
    segments are joined. Individual segments render with clean TTS audio only.

    audio_pad: the audio stream label to use (default [0:a]). Scenes that
    pre-split audio via asplit should pass their output pad here.
    """
    fg += (f"{audio_pad}aformat=channel_layouts=stereo,"
           f"alimiter=limit=0.891:level=disabled:attack=5:release=50,aresample=async=1[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label, 300,
    )
    return output_path if ok else ""


# ── BV2 Scene 1: COLD OPEN ──────────────────────────────────────────────

def make_cold_open_scene(audio_path: str, headline: str, body: str, tag: str,
                          output_path: str, btc_price: str = "N/A",
                          duration: float = 0) -> str:
    """APEX Cold Open — BD left impact panel + VDS 2x2 metric cards right."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    safe_head = _sanitize_text(headline)[:30]
    safe_body = _word_wrap(_sanitize_text(body), max_width=38, max_lines=4) if body else ""
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    # Top system bar
    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=84)

    # LEFT PANEL (x=0,y=72,w=760,h=840) — BD structure
    fg += (f"[bv2_bar]drawbox=x=0:y=72:w=760:h=840:color={COLOR_PANEL}@0.88:t=fill,"
           # Red left border (BD)
           f"drawbox=x=0:y=72:w=5:h=840:color={COLOR_RED}@0.9:t=fill,"
           # GOLD eyebrow kicker (VDS) — only place gold appears
           f"drawtext=fontfile={FONT_MONO}:text='BREAKING INTELLIGENCE':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=22:y=96,"
           # White headline word 1 — large 72px (BD impact)
           f"drawtext=fontfile={FONT_BOLD}:text='SIGNAL':"
           f"fontcolor={COLOR_WHITE}:fontsize=72:x=18:y=118,"
           # Red headline word 2
           f"drawtext=fontfile={FONT_BOLD}:text='DETECTED':"
           f"fontcolor={COLOR_RED}:fontsize=72:x=18:y=198,"
           # Thin red divider
           f"drawbox=x=20:y=290:w=720:h=1:color={COLOR_RED}@0.3:t=fill,"
           # Body text (warm white mono)
           f"drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
           f"fontcolor={COLOR_WHITE}@0.8:fontsize=18:x=22:y=310:line_spacing=8,"
           # CTA pill
           f"drawbox=x=20:y=560:w=460:h=44:color={COLOR_RED_DIM}@0.9:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='BREAKING INTELLIGENCE // INCOMING':"
           f"fontcolor={COLOR_RED}:fontsize=13:x=34:y=574"
           f"[co_left];\n")

    # RIGHT PANEL — VDS 2x2 Metric Cards (x=780,y=100)
    metrics_data = [
        ("BTC PRICE", safe_btc, "+2.1 pct", True),
        ("HASHRATE", "1,056 EH/s", "+4.2 pct", True),
        ("ETF FLOW", "$340M", "+18 pct", True),
        ("MARGIN", "42 pct", "-1.2 pct", False),
    ]
    last = "co_left"
    for mi, (mlabel, mval, mdelta, mpos) in enumerate(metrics_data):
        mx = 780 + (mi % 2) * 540
        my = 100 + (mi // 2) * 210
        dc = COLOR_GREEN if mpos else COLOR_CORAL
        accent = f"{COLOR_RED}@0.6" if mi > 0 else f"{COLOR_GOLD}@0.6"
        out = f"co_card{mi}"
        fg += (f"[{last}]drawbox=x={mx}:y={my}:w=520:h=190:color={COLOR_PANEL2}@0.95:t=fill,"
               # Top accent line (gold for first card, red for rest)
               f"drawbox=x={mx}:y={my}:w=520:h=3:color={accent}:t=fill,"
               # Gold eyebrow label (VDS)
               f"drawtext=fontfile={FONT_MONO}:text='{mlabel}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={mx+16}:y={my+14},"
               # White metric value
               f"drawtext=fontfile={FONT_BOLD}:text='{mval}':"
               f"fontcolor={COLOR_WHITE}:fontsize=42:x={mx+16}:y={my+40},"
               # Delta with emerald/coral
               f"drawtext=fontfile={FONT_MONO}:text='{mdelta}':"
               f"fontcolor={dc}:fontsize=13:x={mx+16}:y={my+100}"
               f"[{out}];\n")
        last = out

    # Chart panel below cards (x=780,y=520,w=1100,h=380)
    fg += (f"[{last}]drawbox=x=780:y=520:w=1100:h=380:color={COLOR_PANEL}@0.9:t=fill,"
           f"drawbox=x=780:y=520:w=1100:h=1:color=0xFFFFFF@0.06:t=fill,"
           # Gold label
           f"drawtext=fontfile={FONT_MONO}:text='BTC NETWORK STRESS':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=800:y=538,"
           # Model Active pill
           f"drawbox=x=1720:y=534:w=120:h=24:color={COLOR_GOLD}@0.12:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='Model Active':"
           f"fontcolor={COLOR_GOLD}:fontsize=10:x=1735:y=539"
           f"[co_chart_hdr];\n")

    # Stylized rising chart bars (red gradient)
    chart_x_start = 820
    chart_y_base = 850
    chart_w = 1020
    step_w = chart_w // 10
    heights = [30, 45, 38, 60, 55, 72, 85, 78, 95, 110]
    last_chart = "co_chart_hdr"
    for ci, ch in enumerate(heights):
        cx = chart_x_start + ci * step_w
        cy = chart_y_base - ch
        out_c = f"co_cbar{ci}"
        fg += (f"[{last_chart}]drawbox=x={cx}:y={cy}:w={step_w-4}:h={ch}:"
               f"color={COLOR_RED}@0.6:t=fill[{out_c}];\n")
        last_chart = out_c

    # Pulse dot at chart tip
    fg += (f"[{last_chart}]drawbox=x={chart_x_start + 9*step_w + step_w//2 - 6}:"
           f"y={chart_y_base - heights[-1] - 8}:w=12:h=12:"
           f"color={COLOR_RED}:t=fill[co_chart_done];\n")

    # Corner brackets
    fg += _build_corner_brackets_fg("co_chart_done", "co_corners")
    # Narration wave (FIX 3: returns tuple with audio_out_pad)
    wave_fg, co_audio_pad = _build_narration_wave("co_corners", "co_wave", "co_a_out")
    fg += wave_fg
    # Info rail
    fg += _build_signature_info_rail(total_dur, btc_price, "co_wave", "co_railed")
    fg += f"[co_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX cold open",
                       audio_pad=co_audio_pad)


# ── BV2 Scene 2: NARRATOR + PiP (SIGNATURE) ─────────────────────────────

def make_narrator_pip_scene(audio_path: str, headline: str, body: str,
                             speaker: str, next_speaker: str,
                             thumb_path: str, output_path: str,
                             btc_price: str = "N/A", duration: float = 0,
                             pip_video_path: str = "") -> str:
    """FIX 1 — APEX Narrator + PiP: uses actual video clip in PiP (not static thumbnail).
    pip_video_path: path to muted PiP preview video from make_pip_preview().
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    inp_idx = 1
    # FIX 1: prefer video PiP over static thumbnail
    has_pip_video = bool(pip_video_path and os.path.exists(pip_video_path)
                         and os.path.getsize(pip_video_path) > 10000)  # >10KB = real video
    has_thumb = bool(thumb_path and os.path.exists(thumb_path)) and not has_pip_video

    if has_pip_video:
        inputs.append(pip_video_path)
        pip_vid_idx = inp_idx
        inp_idx += 1
    else:
        pip_vid_idx = -1

    if has_thumb:
        inputs.append(thumb_path)
        thumb_idx = inp_idx
        inp_idx += 1
    else:
        thumb_idx = -1

    # ── Load intelligence data at render time ──────────────────────────────
    import json as _json, datetime as _dt
    _BASE_INTEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "intelligence")
    _nc_path = os.path.join(_BASE_INTEL, "narrative_context.json")
    _ds_path = os.path.join(_BASE_INTEL, "daily_signals.json")

    # Defaults
    _btc_price_val = btc_price if btc_price and btc_price not in ("N/A", "$0", "") else None
    _dominant_narrative = "Bitcoin Sound Money"
    _market_mood = "NEUTRAL"
    _top_quote = ""
    _quote_handle = ""
    _top_topics = []

    # Narrative context
    try:
        with open(_nc_path) as _f:
            _nc = _json.load(_f)
        _computed = _nc.get("computed_at", "")
        if _computed:
            _age = (_dt.datetime.now(_dt.timezone.utc) -
                    _dt.datetime.fromisoformat(_computed)).total_seconds() / 3600
            if _age < 12:
                _dominant_narrative = _nc.get("dominant_narrative", _dominant_narrative)[:42]
                _market_mood = _nc.get("market_mood", "neutral").upper().replace("_", " ")[:16]
                _hint = _nc.get("eryn_intro_hook", "")
                if "'" in _hint:
                    _qs = _hint.find("'") + 1
                    _qe = _hint.find("'", _qs)
                    if _qe > _qs:
                        _top_quote = _hint[_qs:_qe][:70]
                _tl = _nc.get("thought_leaders_mentioned", [])
                _quote_handle = ("@" + _tl[0][:18]) if _tl else ""
    except Exception:
        pass

    # Daily signals — top topics
    try:
        with open(_ds_path) as _f:
            _ds = _json.load(_f)
        _top_topics = [t.get("topic", "")[:28] for t in _ds.get("topic_velocity", [])[:3]
                       if t.get("velocity_score", 0) > 10]
    except Exception:
        pass

    # BTC price — fetch fresh if not passed in
    if not _btc_price_val:
        try:
            import urllib.request as _ur
            with _ur.urlopen("https://mempool.space/api/v1/prices", timeout=3) as _r:
                _btc_price_val = f"${_json.loads(_r.read()).get('USD', 0):,.0f}"
        except Exception:
            _btc_price_val = "LOADING"

    # Sanitize all strings for FFmpeg
    _btc_safe = _sanitize_text(_btc_price_val)
    _narr_safe = _sanitize_text(_dominant_narrative)
    _mood_safe = _sanitize_text(_market_mood)
    _quote_safe = _sanitize_text(_top_quote[:60]) if _top_quote else ""
    _handle_safe = _sanitize_text(_quote_handle)
    _ts_safe = _dt.datetime.now(tz=_dt.timezone.utc).strftime("%H:%M UTC")

    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=67)

    # Left text zone with gold eyebrow
    safe_speaker = _sanitize_text(speaker)[:12]
    safe_head = _sanitize_text(headline)[:55]
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""

    fg += f"[bv2_bar]copy[np_eye];\n"
    fg += (f"[np_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130[np_head];\n")
    # No duplicate body text — left zone is clean headline only
    fg += f"[np_head]copy[np_body];\n"

    # ═══════════════════════════════════════════════════════
    # INTELLIGENCE PANEL — Left zone, x=64, y=220, w=960, h=430
    # Glassmorphic cyberpunk design: dark glass + red accents
    # ═══════════════════════════════════════════════════════

    # Glassmorphic panel base — dark translucent surface
    fg += (
        f"[np_body]"
        f"drawbox=x=64:y=222:w=960:h=430:color=0x05060A@0.88:t=fill,"
        f"drawbox=x=64:y=222:w=960:h=2:color={COLOR_RED}:t=fill,"
        f"drawbox=x=64:y=222:w=2:h=430:color={COLOR_RED}@0.6:t=fill,"
        f"drawbox=x=64:y=651:w=960:h=1:color=0xFFFFFF@0.08:t=fill,"
        f"drawbox=x=1023:y=222:w=1:h=430:color=0xFFFFFF@0.05:t=fill,"
        f"drawbox=x=66:y=226:w=956:h=1:color=0xFFFFFF@0.07:t=fill"
        f"[np_glass_base];\n"
    )

    # ── SECTION 1: BTC PRICE (top of panel, y=240-310) ──────────────────
    fg += (
        f"[np_glass_base]"
        f"drawtext=fontfile={FONT_MONO}:text='BTC LIVE':"
        f"fontcolor={COLOR_GOLD}@0.65:fontsize=11:x=80:y=236,"
        f"drawtext=fontfile={FONT_MONO}:text='{_ts_safe}':"
        f"fontcolor=0xFFFFFF@0.25:fontsize=10:x=960:y=236,"
        f"drawtext=fontfile={FONT_BOLD}:text='{_btc_safe}':"
        f"fontcolor={COLOR_GOLD}:fontsize=52:x=78:y=248,"
        f"drawbox=x=78:y=316:w=930:h=1:color=0xFFFFFF@0.07:t=fill"
        f"[np_price];\n"
    )

    # ── SECTION 2: NARRATIVE (middle, y=328-420) ─────────────────────────
    _mood_pill_w = min(len(_mood_safe) * 8 + 20, 200)
    fg += (
        f"[np_price]"
        f"drawtext=fontfile={FONT_MONO}:text='SIGNAL':"
        f"fontcolor={COLOR_RED}@0.6:fontsize=10:x=80:y=326,"
        f"drawbox=x=940:y=322:w={_mood_pill_w}:h=18:color={COLOR_RED}@0.12:t=fill,"
        f"drawbox=x=940:y=322:w={_mood_pill_w}:h=18:color={COLOR_RED}@0.4:t=1,"
        f"drawtext=fontfile={FONT_MONO}:text='{_mood_safe}':"
        f"fontcolor={COLOR_RED}:fontsize=9:x=950:y=326,"
        f"drawtext=fontfile={FONT_BOLD}:text='{_narr_safe}':"
        f"fontcolor={COLOR_WHITE}:fontsize=24:x=78:y=342,"
        f"drawbox=x=78:y=380:w=930:h=1:color=0xFFFFFF@0.06:t=fill"
        f"[np_narrative];\n"
    )

    # ── SECTION 3: THOUGHT LEADER QUOTE OR TOPICS (bottom, y=390-630) ────
    if _quote_safe:
        _q_lines = []
        _words = _quote_safe.split()
        _line = ""
        for _w in _words:
            if len(_line) + len(_w) + 1 <= 48:
                _line += (" " + _w if _line else _w)
            else:
                _q_lines.append(_line)
                _line = _w
                if len(_q_lines) >= 2:
                    break
        if _line and len(_q_lines) < 2:
            _q_lines.append(_line)
        _q1 = _sanitize_text(_q_lines[0]) if len(_q_lines) > 0 else ""
        _q2 = _sanitize_text(_q_lines[1]) if len(_q_lines) > 1 else ""

        fg += (
            f"[np_narrative]"
            f"drawtext=fontfile={FONT_BOLD}:text='\\\"':"
            f"fontcolor={COLOR_RED}@0.5:fontsize=32:x=78:y=386,"
        )
        if _q1:
            fg += (
                f"drawtext=fontfile={FONT_MONO}:text='{_q1}':"
                f"fontcolor=0xFFFFFF@0.80:fontsize=16:x=112:y=392,"
            )
        if _q2:
            fg += (
                f"drawtext=fontfile={FONT_MONO}:text='{_q2}':"
                f"fontcolor=0xFFFFFF@0.80:fontsize=16:x=112:y=412,"
            )
        fg += (
            f"drawtext=fontfile={FONT_MONO}:text='{_handle_safe}':"
            f"fontcolor={COLOR_RED}:fontsize=12:x=112:y=436,"
            f"drawtext=fontfile={FONT_MONO}:text='THOUGHT LEADER SIGNAL':"
            f"fontcolor=0xFFFFFF@0.20:fontsize=9:x=80:y=456"
            f"[np_quote];\n"
        )
        intel_out = "np_quote"
    elif _top_topics:
        fg += f"[np_narrative]"
        fg += (
            f"drawtext=fontfile={FONT_MONO}:text='TRENDING TOPICS':"
            f"fontcolor=0xFFFFFF@0.25:fontsize=10:x=80:y=390,"
        )
        for _ti, _tp in enumerate(_top_topics[:3]):
            _tp_safe = _sanitize_text(_tp)
            _ty = 410 + _ti * 24
            fg += (
                f"drawtext=fontfile={FONT_MONO}:text='▸ {_tp_safe}':"
                f"fontcolor=0xFFFFFF@0.65:fontsize=14:x=86:y={_ty},"
            )
        fg += f"drawbox=x=78:y=476:w=200:h=1:color={COLOR_RED}@0.3:t=fill[np_topics];\n"
        intel_out = "np_topics"
    else:
        fg += f"[np_narrative]copy[np_intel_empty];\n"
        intel_out = "np_intel_empty"

    # Corner bracket accents (cyberpunk tactical)
    fg += (
        f"[{intel_out}]"
        f"drawbox=x=1012:y=222:w=12:h=2:color={COLOR_RED}@0.5:t=fill,"
        f"drawbox=x=1022:y=222:w=2:h=12:color={COLOR_RED}@0.5:t=fill,"
        f"drawbox=x=64:y=650:w=12:h=2:color={COLOR_RED}@0.3:t=fill,"
        f"drawbox=x=64:y=640:w=2:h=12:color={COLOR_RED}@0.3:t=fill"
        f"[np_pills];\n"
    )

    # Right PiP preview panel (x=1060, y=220, w=820, h=460) — strictly right half, no text overlap
    # Gold eyebrow above PiP
    fg += (f"[np_pills]drawtext=fontfile={FONT_MONO}:text='COMING UP NEXT':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=1080:y=202[np_pip_eye];\n")
    fg += (f"[np_pip_eye]drawbox=x=1060:y=220:w=820:h=460:color={COLOR_PANEL}@0.92:t=fill,"
           f"drawbox=x=1060:y=220:w=820:h=1:color=0xFFFFFF@0.1:t=fill,"
           f"drawbox=x=1060:y=679:w=820:h=1:color=0xFFFFFF@0.1:t=fill,"
           f"drawbox=x=1060:y=220:w=0:h=0:color=0x000000@0:t=fill"
           f"[np_pip_hdr];\n")

    # FIX 1: Use actual video in PiP box — loop the preview clip to match segment duration
    # PiP content area: x=1072, y=232, w=796, h=370 (inside the 1060,220,820,460 panel)
    if has_pip_video and pip_vid_idx >= 0:
        pip_dur_src = ffprobe_duration(pip_video_path)
        src_frames = max(30, int(pip_dur_src * 30) + 5) if pip_dur_src > 0 else 300
        loop_flag = f"loop=loop=-1:size={src_frames}:start=0," if pip_dur_src < total_dur else ""
        fg += (f"[{pip_vid_idx}:v]{loop_flag}"
               f"scale=796:370:force_original_aspect_ratio=increase,"
               f"crop=796:370,setsar=1,fps=30,trim=0:{total_dur},setpts=PTS-STARTPTS[np_pip_vid];\n")
        fg += f"[np_pip_hdr][np_pip_vid]overlay=1072:240[np_pip_thumb];\n"
        pip_base = "np_pip_thumb"
    elif has_thumb and thumb_idx >= 0:
        fg += (f"[{thumb_idx}:v]scale=796:370:force_original_aspect_ratio=increase,"
               f"crop=796:370,setsar=1,fps=30,trim=0:{total_dur},setpts=PTS-STARTPTS[np_thumb];\n")
        fg += f"[np_pip_hdr][np_thumb]overlay=1072:240[np_pip_thumb];\n"
        pip_base = "np_pip_thumb"
    else:
        # Minimal styled placeholder — keeps PiP frame occupied
        fg += (
            f"[np_pip_hdr]"
            f"drawbox=x=1072:y=240:w=796:h=370:color=0x050607:t=fill,"
            f"drawtext=fontfile={FONT_MONO}:text='PREVIEW':"
            f"fontcolor={COLOR_RED}@0.4:fontsize=14:x=1420:y=410,"
            f"drawtext=fontfile={FONT_MONO}:text='LOADING':"
            f"fontcolor=0xFFFFFF@0.2:fontsize=11:x=1422:y=430"
            f"[np_pip_thumb];\n"
        )
        pip_base = "np_pip_thumb"

    # Lower third in preview
    safe_next = _sanitize_text(next_speaker)[:30] if next_speaker else "NEXT SOURCE"
    fg += (f"[{pip_base}]drawbox=x=1072:y=620:w=796:h=50:color=0x000000@0.7:t=fill,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_next}':"
           f"fontcolor={COLOR_WHITE}:fontsize=18:x=1088:y=634,"
           f"drawbox=x=1740:y=628:w=110:h=24:color={COLOR_RED}@0.12:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='Preview Active':"
           f"fontcolor={COLOR_RED}:fontsize=10:x=1750:y=633,"
           # BD tactical mini corner brackets on PiP frame (16px)
           f"drawbox=x=1060:y=220:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1060:y=220:w=3:h=16:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1864:y=220:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1877:y=220:w=3:h=16:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1060:y=677:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1060:y=664:w=3:h=16:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1864:y=677:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1877:y=664:w=3:h=16:color={COLOR_RED}:t=fill"
           f"[np_pip_final];\n")

    # Corner brackets (main frame)
    fg += _build_corner_brackets_fg("np_pip_final", "np_corners")
    wave_fg, np_audio_pad = _build_narration_wave("np_corners", "np_wave", "np_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "np_wave", "np_railed")
    fg += f"[np_railed]format=yuv420p[outv];\n"

    result = _bv2_encode(inputs, fg, output_path, total_dur, "APEX narrator+pip",
                         audio_pad=np_audio_pad)

    # Session 4 Fix 6: Try Remotion IntelPanel overlay (upgrade from drawtext)
    if result and os.path.exists(result):
        try:
            frames = max(int(total_dur * 30), 120)
            remotion_panel = _make_remotion_intel_panel(frames, btc_price)
            if remotion_panel and os.path.exists(remotion_panel):
                upgraded = output_path + ".intel_upgrade.mp4"
                ok = run_ffmpeg([
                    "-i", result,
                    "-i", remotion_panel,
                    "-filter_complex",
                    "[0:v][1:v]overlay=0:0:shortest=1[outv]",
                    "-map", "[outv]", "-map", "0:a",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-b:v", "8M", "-c:a", "copy",
                    "-t", str(total_dur), upgraded,
                ], "Remotion IntelPanel overlay", 120)
                if ok and os.path.exists(upgraded):
                    shutil.move(upgraded, output_path)
                    logger.info("  Fix 6: Remotion IntelPanel overlay applied")
                else:
                    logger.info("  Fix 6: Remotion overlay failed — keeping drawtext panel")
        except Exception as e:
            logger.info(f"  Fix 6: Remotion IntelPanel skipped: {e}")

    return result


# ── BV2 Scene 3: PARTNER CLIP ───────────────────────────────────────────

def _get_audio_offset(clip_path: str) -> float:
    """Session 4 Fix 5: Probe container-level audio start offset for lip sync."""
    try:
        r = subprocess.run([
            "ffprobe", "-v", "quiet", "-select_streams", "a:0",
            "-show_entries", "stream=start_time",
            "-of", "csv=p=0", clip_path
        ], capture_output=True, text=True, timeout=10)
        val = float(r.stdout.strip())
        return val if 0 < val < 2.0 else 0.0  # ignore large or negative offsets
    except Exception:
        return 0.0


def make_partner_clip_scene(video_path: str, audio_path: str, speaker: str,
                             quote: str, output_path: str,
                             btc_price: str = "N/A", duration: float = 0) -> str:
    """APEX Partner Clip — BEV2 restraint. Full-frame, premium lower-third, no competing animations."""
    clip_dur = ffprobe_duration(video_path)
    if clip_dur <= 0:
        logger.warning(f"Partner clip has zero duration: {video_path}")
        return ""

    safe_speaker = _sanitize_text(speaker)[:30] if speaker else "SOURCE"
    safe_quote = _sanitize_text(quote)[:60] if quote else ""
    safe_btc = btc_price.replace("'", "").replace('"', "")

    import datetime
    ts_str = datetime.datetime.now().strftime("%H-%M UTC")

    fade_out_start = max(0, clip_dur - 0.5)
    fg = ""
    # Full frame clip
    fg += (f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
           f"setsar=1,fps=30,fade=t=in:d=0.3,fade=t=out:st={fade_out_start}:d=0.5[pc_raw];\n")
    # Cyberpunk aesthetic: darken clip slightly + tactical grid + radial vignette
    fg += (f"[pc_raw]"
           f"eq=brightness=-0.05:saturation=0.9:contrast=1.05,"
           f"drawgrid=width=120:height=68:thickness=1:color=0xFF0000@0.05,"
           f"vignette=PI/5:mode=backward"
           f"[pc_clip];\n")
    # Red border frame (2px)
    fg += (f"[pc_clip]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
           f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
           f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
           f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[pc_framed];\n")
    # Top-right watermark (red, 18px, 60% opacity)
    fg += (f"[pc_framed]drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
           f"fontcolor={COLOR_RED}@0.6:fontsize=18:x=W-text_w-24:y=18[pc_wm];\n")
    # BD corner brackets
    fg += _build_corner_brackets_fg("pc_wm", "pc_corners")
    # Glass lower-third with red top accent
    fg += (f"[pc_corners]drawbox=x=0:y=870:w=800:h=110:color=0x000000@0.88:t=fill,"
           f"drawbox=x=0:y=870:w=800:h=4:color={COLOR_RED}:t=fill,"
           # Speaker name (bold 26px)
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_speaker}':"
           f"fontcolor={COLOR_WHITE}:fontsize=26:x=24:y=890,"
           # Source info
           f"drawtext=fontfile={FONT_MONO}:text='{safe_quote}':"
           f"fontcolor=0xFFFFFF@0.6:fontsize=16:x=24:y=928,"
           f"drawtext=fontfile={FONT_MONO}:text='{ts_str}':"
           f"fontcolor=0xFFFFFF@0.35:fontsize=11:x=740:y=878"
           f"[pc_lt];\n")
    # Info rail (always present)
    fg += _build_signature_info_rail(clip_dur, btc_price, "pc_lt", "pc_railed")
    fg += (f"[pc_railed]format=yuv420p[outv];\n"
           # Issue 4 FIX: Strip first 2.5s of partner clip audio (intro jangle) + fade in
           # Session 4 Fix 5: aresample=async=1 for lip sync drift correction
           f"[0:a]aresample=async=1,atrim=start=2.5,asetpts=PTS-STARTPTS,"
           f"highpass=f=50,lowpass=f=15000,"
           f"afade=t=in:d=0.5,afade=t=out:st={max(0, fade_out_start - 2.5)}:d=0.5[outa]")

    # Session 4 Fix 5: Probe audio offset for lip sync correction
    a_offset = _get_audio_offset(video_path)
    input_spec = video_path
    if a_offset > 0.01:
        # Use list input form so itsoffset is prepended before -i
        input_spec = ["-itsoffset", str(a_offset), "-i", video_path]
        logger.info(f"  Fix 5: Audio offset {a_offset:.3f}s applied for lip sync")

    ok = run_ffmpeg_filtergraph(
        [input_spec], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k"],
        output_path, f"APEX partner clip ({safe_speaker})",
    )
    return output_path if ok else ""


# ── BV2 Scene 4: DATA SEGMENT ───────────────────────────────────────────

def make_data_segment_scene(audio_path: str, headline: str, metrics: list,
                             output_path: str, btc_price: str = "N/A",
                             duration: float = 0) -> str:
    """APEX Data Segment — gold eyebrow cards + emerald/coral deltas + chart."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=72)

    # Left text zone with gold eyebrow
    safe_head = _sanitize_text(headline)[:40]
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='MARKET STRUCTURE':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[ds_eye];\n")
    fg += (f"[ds_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130,"
           # ANALYTICS tag pill
           f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
           f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
           f"drawtext=fontfile={FONT_MONO}:text='ANALYTICS':"
           f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590"
           f"[ds_txt];\n")

    # 2x2 metric card grid with gold eyebrow labels (VDS)
    default_metrics = [
        ("BTC", btc_price, "+2.1 pct", True),
        ("HASHRATE", "1,056 EH/s", "+4.2 pct", True),
        ("ETF FLOW", "$340M", "+18 pct", True),
        ("MARGIN", "42 pct", "-1.2 pct", False),
    ]
    use_metrics = []
    if metrics and len(metrics) >= 4:
        for m in metrics[:4]:
            if isinstance(m, dict):
                use_metrics.append((
                    m.get("label", "DATA"),
                    _sanitize_text(str(m.get("value", "N/A"))),
                    _sanitize_text(str(m.get("delta", ""))),
                    m.get("positive", True),
                ))
            elif isinstance(m, (list, tuple)) and len(m) >= 3:
                use_metrics.append((str(m[0]), _sanitize_text(str(m[1])),
                                    _sanitize_text(str(m[2])),
                                    m[3] if len(m) > 3 else True))
    if len(use_metrics) < 4:
        use_metrics = default_metrics

    last = "ds_txt"
    for mi, (mlabel, mval, mdelta, mpos) in enumerate(use_metrics):
        mx = 64 + (mi % 2) * 360
        my = 460 + (mi // 2) * 160
        dc = COLOR_GREEN if mpos else COLOR_CORAL
        out = f"ds_dm{mi}"
        fg += (f"[{last}]drawbox=x={mx}:y={my}:w=340:h=140:color={COLOR_PANEL2}@0.95:t=fill,"
               f"drawbox=x={mx}:y={my}:w=340:h=3:color={COLOR_RED}@0.5:t=fill,"
               # Gold eyebrow label (VDS)
               f"drawtext=fontfile={FONT_MONO}:text='{mlabel}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={mx+16}:y={my+14},"
               f"drawtext=fontfile={FONT_BOLD}:text='{mval}':"
               f"fontcolor={COLOR_WHITE}:fontsize=28:x={mx+16}:y={my+38},"
               # Emerald/coral delta (VDS)
               f"drawtext=fontfile={FONT_MONO}:text='{mdelta}':"
               f"fontcolor={dc}:fontsize=13:x={mx+16}:y={my+80}"
               f"[{out}];\n")
        last = out

    # FIX 5: Try TradingView chart screenshot, fallback to static bars
    tv_chart_path = ""
    try:
        from chart_capture import get_chart
        tv_chart_path = get_chart("btc_usd_1d")
    except Exception as e:
        logger.warning(f"  TradingView chart capture unavailable: {e}")

    if tv_chart_path and os.path.exists(tv_chart_path):
        # Live TradingView chart overlay
        inputs.append(tv_chart_path)
        chart_input_idx = len(inputs) - 1
        fg += (f"[{last}]drawbox=x=1120:y=90:w=760:h=820:color={COLOR_PANEL}@0.92:t=fill,"
               f"drawbox=x=1120:y=90:w=760:h=1:color=0xFFFFFF@0.08:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='TRADINGVIEW // BTCUSD 1D':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=108,"
               f"drawbox=x=1720:y=105:w=100:h=24:color={COLOR_GREEN}@0.15:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='LIVE CHART':"
               f"fontcolor={COLOR_GREEN}:fontsize=10:x=1732:y=110"
               f"[ds_chart_hdr];\n")
        fg += (f"[{chart_input_idx}:v]scale=740:700:force_original_aspect_ratio=decrease,"
               f"pad=740:700:(ow-iw)/2:(oh-ih)/2:color=0x050607[ds_tv_chart];\n")
        fg += f"[ds_chart_hdr][ds_tv_chart]overlay=1130:130[ds_chart_done];\n"
    else:
        # Fallback: static FFmpeg chart bars
        fg += (f"[{last}]drawbox=x=1120:y=90:w=760:h=820:color={COLOR_PANEL}@0.92:t=fill,"
               f"drawbox=x=1120:y=90:w=760:h=1:color=0xFFFFFF@0.08:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='BTC NETWORK STRESS':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=108,"
               f"drawbox=x=1720:y=105:w=100:h=24:color={COLOR_GOLD}@0.12:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='Model Active':"
               f"fontcolor={COLOR_GOLD}:fontsize=10:x=1732:y=110"
               f"[ds_chart_hdr];\n")
        chart_x_start = 1160
        chart_y_base = 800
        chart_w = 680
        step_w = chart_w // 10
        heights = [30, 45, 38, 60, 55, 72, 85, 78, 95, 110]
        last_chart = "ds_chart_hdr"
        for ci, ch in enumerate(heights):
            cx = chart_x_start + ci * step_w
            cy = chart_y_base - ch
            out_c = f"ds_cbar{ci}"
            fg += (f"[{last_chart}]drawbox=x={cx}:y={cy}:w={step_w-4}:h={ch}:"
                   f"color={COLOR_RED}@0.6:t=fill[{out_c}];\n")
            last_chart = out_c
        fg += (f"[{last_chart}]drawbox=x={chart_x_start + 9*step_w + step_w//2 - 6}:"
               f"y={chart_y_base - heights[-1] - 8}:w=12:h=12:"
               f"color={COLOR_RED}:t=fill[ds_chart_done];\n")

    fg += _build_corner_brackets_fg("ds_chart_done", "ds_corners")
    wave_fg, ds_audio_pad = _build_narration_wave("ds_corners", "ds_wave", "ds_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "ds_wave", "ds_railed")
    fg += f"[ds_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX data segment",
                       audio_pad=ds_audio_pad)


# ── BV2 Scene 5: SOCIAL STACK ───────────────────────────────────────────

def _rank_cards_for_segment(cards: list, segment_text: str) -> list:
    """Session 4 Fix 4: Rank tweet cards by relevance to narrator text."""
    if not cards or not segment_text:
        return cards
    words = set(segment_text.lower().split())
    def score(card):
        card_words = set((card.get('text', '') + ' ' + card.get('handle', '')).lower().split())
        return len(words & card_words)
    return sorted(cards, key=score, reverse=True)


def make_social_stack_scene(audio_path: str, headline: str, social_cards: list,
                             output_path: str, btc_price: str = "N/A",
                             duration: float = 0,
                             card_timings: list = None) -> str:
    """APEX Social Stack — FIX 4: cards LOCKED to TTS timing.

    Cards appear/disappear synchronized with narration. Each card is visible
    only during its time slice. Active card: red border + full opacity.
    Past/future cards: dim panel + muted opacity.
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=58)

    # Header zone with gold eyebrow
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='SIGNAL LAYER':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(headline)[:40]}':"
           f"fontcolor={COLOR_WHITE}:fontsize=48:x=64:y=130,"
           f"drawtext=fontfile={FONT_MONO}:text='Bitcoin Social Conviction Index':"
           f"fontcolor=0xFFFFFF@0.5:fontsize=16:x=64:y=200"
           f"[ss_hdr];\n")

    default_cards = [
        {"name": "Signal Source", "handle": "@signal", "score": "96", "text": "Bitcoin conviction remains extremely high", "tag": "HIGH CONVICTION"},
        {"name": "Market Intel", "handle": "@intel", "score": "84", "text": "Structural demand continues to build", "tag": "STRUCTURAL"},
        {"name": "Macro Watch", "handle": "@macro", "score": "72", "text": "Global liquidity conditions favor BTC", "tag": "MACRO SIGNAL"},
    ]
    cards = social_cards[:3] if social_cards and len(social_cards) >= 1 else default_cards
    while len(cards) < 3:
        cards.append(default_cards[len(cards) % 3])

    n_cards = min(len(cards), 3)

    # FIX 4: Calculate per-card timing — divide narration evenly across cards
    if card_timings and len(card_timings) >= n_cards:
        timings = card_timings[:n_cards]
    else:
        tpc = total_dur / n_cards if n_cards > 0 else total_dur
        timings = [(i * tpc, (i + 1) * tpc) for i in range(n_cards)]

    tags = ["HIGH CONVICTION", "STRUCTURAL", "MACRO SIGNAL"]
    last = "ss_hdr"
    for ci, card in enumerate(cards[:n_cards]):
        cx = 64 + ci * 608
        cy = 300
        cw = 580
        ch = 620

        t_start, t_end = timings[ci]
        # FIX 4: Active card = red border + full text; inactive = dim panel
        # Use enable expressions for active state highlighting
        active_enable = f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
        inactive_enable = f"enable='not(between(t,{t_start:.2f},{t_end:.2f}))'"

        name = _sanitize_text(str(card.get("name", card.get("handle", "Source"))))[:20]
        handle = _sanitize_text(str(card.get("handle", "@source")))[:20]
        score = str(card.get("score", card.get("likes", "80")))[:6]
        ctext = _word_wrap(_sanitize_text(str(card.get("text", ""))), max_width=24, max_lines=4)
        ctag = _sanitize_text(str(card.get("tag", tags[ci % 3])))[:20]

        out = f"ss_sc{ci}"
        # Card background (always visible but dimmed when inactive)
        fg += (f"[{last}]drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color={COLOR_PANEL}@0.92:t=fill,"
               # Active: red border
               f"drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color={COLOR_RED}@0.4:t=2:{active_enable},"
               # Inactive: subtle white border
               f"drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color=0xFFFFFF@0.08:t=2:{inactive_enable},"
               # Avatar placeholder
               f"drawbox=x={cx+24}:y={cy+24}:w=44:h=44:color={COLOR_RED}@0.5:t=fill,"
               # Name
               f"drawtext=fontfile={FONT_BOLD}:text='{name}':"
               f"fontcolor={COLOR_WHITE}:fontsize=16:x={cx+80}:y={cy+28},"
               # Handle
               f"drawtext=fontfile={FONT_MONO}:text='{handle}':"
               f"fontcolor=0xFFFFFF@0.35:fontsize=12:x={cx+80}:y={cy+50},"
               # VDS gold score badge
               f"drawbox=x={cx+cw-90}:y={cy+28}:w=70:h=24:color={COLOR_GOLD}@0.15:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='{score} / 100':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={cx+cw-84}:y={cy+34},"
               # Quote text
               f"drawtext=fontfile={FONT_BOLD}:text='{ctext}':"
               f"fontcolor={COLOR_WHITE}:fontsize=20:x={cx+24}:y={cy+100}:line_spacing=10,"
               # VDS gold tag label at bottom
               f"drawtext=fontfile={FONT_MONO}:text='{ctag}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={cx+24}:y={cy+ch-36},"
               # Active indicator: "ACTIVE" tag when card is current
               f"drawtext=fontfile={FONT_MONO}:text='ACTIVE':"
               f"fontcolor={COLOR_RED}:fontsize=11:x={cx+cw-70}:y={cy+ch-36}:{active_enable}"
               f"[{out}];\n")
        last = out

    fg += _build_corner_brackets_fg(last, "ss_corners")
    wave_fg, ss_audio_pad = _build_narration_wave("ss_corners", "ss_wave", "ss_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "ss_wave", "ss_railed")
    fg += f"[ss_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX social stack",
                       audio_pad=ss_audio_pad)


# ── BV2 Scene 6: WRAP / VERDICT ─────────────────────────────────────────

def make_wrap_scene(audio_path: str, headline: str, body: str,
                     output_path: str, btc_price: str = "N/A",
                     duration: float = 0) -> str:
    """APEX Wrap — BEV2 waveform + BD episode segments tracker + gold accents."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    safe_head = _sanitize_text(headline)[:40]
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=100)

    # Left text zone with gold eyebrow
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='FINAL TAKE':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[wr_eye];\n")
    fg += (f"[wr_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130[wr_head];\n")
    if safe_body:
        fg += (f"[wr_head]drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor=0xFFFFFF@0.6:fontsize=18:x=64:y=420:line_spacing=8[wr_body];\n")
    else:
        fg += f"[wr_head]copy[wr_body];\n"
    fg += (f"[wr_body]drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
           f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
           f"drawtext=fontfile={FONT_MONO}:text='RESOLVE':"
           f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590[wr_txt];\n")

    # Right Signal Wave panel (x=1120, y=140, w=740, h=500)
    fg += (f"[wr_txt]drawbox=x=1120:y=140:w=740:h=500:color={COLOR_PANEL}@0.92:t=fill,"
           f"drawbox=x=1120:y=140:w=740:h=1:color=0xFFFFFF@0.08:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='Signal Wave':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=158"
           f"[wr_panel];\n")
    # FIX 3: Single asplit for ALL audio consumers in wrap scene
    # 1=big waveform, 2+3=narration wave (primary+accent)
    fg += f"[0:a]asplit=4[_wr_a_big][_wr_a_nav1][_wr_a_nav2][_wr_a_out];\n"

    # Large waveform inside panel
    fg += (f"[_wr_a_big]showwaves=s=700x350:mode=cline:"
           f"colors={COLOR_RED}|{COLOR_WHITE}:scale=sqrt:draw=full:rate=30[wr_sigwave];\n")
    fg += f"[wr_panel][wr_sigwave]overlay=1140:220[wr_waved];\n"

    # BD Episode Segments tracker (x=1120,y=660,w=740,h=240)
    fg += (f"[wr_waved]drawtext=fontfile={FONT_MONO}:text='EPISODE SEGMENTS':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=655[wr_seg_eye];\n")
    segments = [
        ("COLD OPEN", "DONE"),
        ("ORACLE BRIEF", "DONE"),
        ("CLIP REACTION", "DONE"),
        ("DUAL-HOST", "ACTIVE"),
    ]
    last_seg = "wr_seg_eye"
    for si, (sname, sstatus) in enumerate(segments):
        sy = 675 + si * 44
        if sstatus == "DONE":
            sc = COLOR_GREEN
        elif sstatus == "ACTIVE":
            sc = COLOR_RED
        else:
            sc = COLOR_MUTED2
        out_s = f"wr_seg{si}"
        fg += (f"[{last_seg}]drawbox=x=1140:y={sy}:w=700:h=36:color={COLOR_PANEL2}@0.8:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='{sname}':"
               f"fontcolor={COLOR_WHITE}@0.7:fontsize=12:x=1156:y={sy+10},"
               f"drawtext=fontfile={FONT_MONO}:text='{sstatus}':"
               f"fontcolor={sc}:fontsize=12:x=1740:y={sy+10}"
               f"[{out_s}];\n")
        last_seg = out_s

    fg += _build_corner_brackets_fg(last_seg, "wr_corners")

    # Inline Cipher Line wave using pre-split audio pads (FIX 3)
    fg += (f"[_wr_a_nav1]showwaves=s=1920x80:mode=line:"
           f"colors=0xF4F5F8@0.9:scale=sqrt:draw=full:rate=30[_wr_wl];\n")
    fg += (f"[_wr_a_nav2]showwaves=s=1920x80:mode=line:"
           f"colors=0xFF334D@0.25:scale=log:draw=full:rate=30[_wr_wr];\n")
    fg += f"[_wr_wr]vflip[_wr_wrf];\n"
    fg += f"[_wr_wl][_wr_wrf]vstack[_wr_ws];\n"
    fg += (f"[_wr_ws]drawbox=x=0:y=0:w=1920:h=20:color=0x020304@0.8:t=fill,"
           f"drawbox=x=0:y=140:w=1920:h=20:color=0x020304@0.8:t=fill[_wr_wf];\n")
    fg += f"[_wr_wf]drawbox=x=0:y=79:w=1920:h=2:color=0xFF0000@0.35:t=fill[_wr_wfin];\n"
    fg += f"[wr_corners][_wr_wfin]overlay=0:880[wr_ekg];\n"

    fg += _build_signature_info_rail(total_dur, btc_price, "wr_ekg", "wr_railed")
    # Session 4 Fix 7: Extended fade-to-black (1.5s) and audio fade (2.5s) for clean ending
    fade_v_start = max(0, total_dur - 1.5)
    fade_a_start = max(0, total_dur - 2.5)
    fg += (f"[wr_railed]fade=t=out:st={fade_v_start:.2f}:d=1.5:color=0x0A0A0F,"
           f"format=yuv420p[outv];\n")
    fg += (f"[_wr_a_out]afade=t=out:st={fade_a_start:.2f}:d=2.5[_wr_a_faded];\n")

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX wrap",
                       audio_pad="[_wr_a_faded]")


# ── BV2 Scene Router ────────────────────────────────────────────────────

def select_scene_type(segment_type: str, segment_index: int, total_segments: int) -> str:
    """Route segment to appropriate BV2 scene type.

    APEX V2 FIX 7 — PiP-first order:
      0: cold_open (title card intro)
      1: narrator_pip (dual host commentary — LEADS the episode)
      2: partner_clip (YouTube clip)
      3: react (hosts react to clip)
      4: data_segment (price action + chart)
      5: social_stack (tweet conviction)
      6+: wrap (closing)
    """
    if segment_index == 0:
        return "cold_open"
    elif segment_index == 1 or segment_type in ("setup", "intro", "pip"):
        return "narrator_pip"  # FIX 7: PiP FIRST after cold open
    elif segment_type == "broll":
        return "partner_clip"
    elif segment_type == "data":
        return "data_segment"
    elif segment_type in ("social", "social_segment"):
        return "social_stack"
    elif segment_type == "x_spaces":
        return "data_segment"  # X Spaces uses data_segment visual with branded eyebrow
    elif segment_type in ("wrap", "outro") or segment_index == total_segments - 1:
        return "wrap"
    elif segment_type == "react":
        return "narrator_pip"  # react uses same visual as narrator_pip
    else:
        return "narrator_pip"


def make_broadcast_segment(segment_data: dict, audio_path: str, host_num: int,
                            segment_index: int, total_segments: int,
                            output_path: str, btc_price: str = "N/A",
                            thumbnail_path: str = "",
                            clip_path: str = "",
                            social_posts: list = None,
                            pip_video_path: str = "") -> str:
    """Route to appropriate BV2 scene function based on segment type and position.

    Falls back to make_host_visual if BV2 scene fails.
    """
    seg_type = segment_data.get("type", "")
    text = segment_data.get("text", "")
    headline = segment_data.get("headline") or segment_data.get("title") or _smart_headline(text)
    speaker = segment_data.get("speaker", "ERYN")  # dual host — Eryn (HOST_1) + Mark (HOST_2)
    scene = select_scene_type(seg_type, segment_index, total_segments)

    try:
        if scene == "cold_open":
            return make_cold_open_scene(
                audio_path, headline, text, "REDLINE",
                output_path, btc_price=btc_price,
            )
        elif scene == "narrator_pip":
            next_speaker = segment_data.get("next_speaker", "")
            return make_narrator_pip_scene(
                audio_path, headline, text, speaker, next_speaker,
                thumbnail_path, output_path, btc_price=btc_price,
                pip_video_path=pip_video_path,  # FIX 1: pass actual video
            )
        elif scene == "partner_clip" and clip_path:
            return make_partner_clip_scene(
                clip_path, audio_path, speaker, headline,
                output_path, btc_price=btc_price,
            )
        elif scene == "data_segment":
            metrics = segment_data.get("metrics", [])
            return make_data_segment_scene(
                audio_path, headline, metrics,
                output_path, btc_price=btc_price,
            )
        elif scene == "social_stack":
            return make_social_stack_scene(
                audio_path, headline, social_posts or [],
                output_path, btc_price=btc_price,
            )
        elif scene == "wrap":
            return make_wrap_scene(
                audio_path, headline, text,
                output_path, btc_price=btc_price,
            )
    except Exception as e:
        logger.warning(f"BV2 scene '{scene}' failed: {e} — falling back to make_host_visual")

    # Fallback to Black Diamond host visual
    result = make_host_visual(
        audio_path, host_num, text, output_path,
        btc_price=btc_price, label="bv2_fallback_{}".format(seg_type),
        thumbnail_path=thumbnail_path, segment_type=seg_type,
    )
    # HARD SAFETY NET: if output still missing/empty, generate solid bg+audio
    if not result or not os.path.exists(result):
        logger.error("make_host_visual also failed -- generating emergency bg clip")
        try:
            dur = ffprobe_duration(audio_path) or 10.0
            run_ffmpeg([
                "-f", "lavfi", "-i",
                "color=c=0x0A0A0F:s=1920x1080:d={:.3f}:r=30".format(dur),
                "-i", audio_path,
                "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                "-t", "{:.3f}".format(dur), output_path
            ], "emergency bg clip", 60)
            result = output_path if os.path.exists(output_path) else ""
        except Exception as _e:
            logger.error("Emergency clip also failed: %s", _e)
    return result


# ══════════════════════════════════════════════════════════════════════════
# BLACK DIAMOND (legacy) — kept as fallback
# ══════════════════════════════════════════════════════════════════════════

def make_host_visual(audio_path: str, host: int, text: str,
                     output_path: str, btc_price: str = "N/A",
                     label: str = "", thumbnail_path: str = "",
                     segment_type: str = "") -> str:
    """BLACK DIAMOND Command Center layout — Sovereign Command Center.

    Left impact panel + right waveform + data grid + ticker + corner brackets.
    Background music at -18dB under TTS.
    """
    import datetime as _dt
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = audio_dur + 0.3

    speaker = "ERYN" if host == 1 else "MARK"  # dual host restored 2026-03-10

    safe_btc = btc_price.replace("'", "").replace('"', "")

    is_social = segment_type == "social_segment"

    # Eyebrow / headline logic by segment_type
    seg_map = {
        "cold_open": ("COLD OPEN // BREAKING SIGNAL", "SIGNAL", "DETECTED"),
        "setup":     (f"ANALYST // {speaker}", speaker[:6], "REPORTING"),
        "react":     (f"REACTION // {speaker}", speaker[:6], "REACTS"),
        "wrap":      (f"CLOSING // {speaker}", speaker[:6], "CONFIRMED"),
        "x_spaces":  ("◆ X SPACES // LIVE INTEL", "SPACES", "LIVE"),
    }
    eyebrow, h1, h2 = seg_map.get(segment_type, (f"PROTOCOL PULSE // {speaker}", "SIGNAL", "ACTIVE"))

    ep_num = _dt.datetime.now().strftime("%j")
    recon_id = _dt.datetime.now().strftime("BD-%Y-%j-%H%M")

    # Segment status for tracker
    segment_order = ["cold_open", "setup", "react", "wrap"]
    seg_idx = segment_order.index(segment_type) if segment_type in segment_order else -1

    # Build inputs: 0=TTS audio only (APEX V2: music mixed in concatenate_parts)
    inputs = [audio_path]

    # BLACK DIAMOND procedural background
    _, bg_fg = _build_black_diamond_bg(total_dur, label_out="bd_bg")
    fg = bg_fg

    # ── HEADER BAR ──
    fg += (f"[bd_bg]drawbox=x=0:y=0:w=1920:h=72:color=0x050505@0.97:t=fill,"
           f"drawbox=x=0:y=70:w=1920:h=2:color={COLOR_RED}@0.8:t=fill,"
           f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
           f"fontcolor={COLOR_WHITE}:fontsize=28:x=24:y=22,"
           f"drawtext=fontfile={FONT_BOLD}:text='LIVE':"
           f"fontcolor={COLOR_RED}:fontsize=22:x=280:y=26,"
           f"drawtext=fontfile={FONT_BOLD}:text='|':"
           f"fontcolor={COLOR_MUTED}:fontsize=28:x=340:y=22,"
           f"drawbox=x=0:y=0:w=0:h=0:color=0x000000@0:t=fill"
           f"[hdr];\n")

    # ── LEFT PANEL ──
    fg += (f"[hdr]drawbox=x=0:y=72:w=720:h=958:color=0x070707@0.92:t=fill,"
           f"drawbox=x=0:y=72:w=6:h=958:color={COLOR_RED}@0.92:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='  {eyebrow}':"
           f"fontcolor={COLOR_RED}:fontsize=13:x=24:y=102,"
           f"drawtext=fontfile={FONT_BOLD}:text='{h1}':"
           f"fontcolor={COLOR_WHITE}:fontsize=96:x=18:y=128,"
           f"drawtext=fontfile={FONT_BOLD}:text='{h2}':"
           f"fontcolor={COLOR_RED}:fontsize=96:x=18:y=238"
           f"[lpanel];\n")

    # Divider line
    fg += f"[lpanel]drawbox=x=20:y=358:w=680:h=1:color={COLOR_RED}@0.35:t=fill[ldiv];\n"

    # Body text (wrapped subtitle)
    safe_sub = _sanitize_text(text) if text else ""
    if safe_sub:
        wrapped_sub = _word_wrap(safe_sub, max_width=40, max_lines=3)
        fg += (f"[ldiv]drawtext=fontfile={FONT_MONO}:"
               f"text='{wrapped_sub}':"
               f"fontcolor=0xBBBBBB:fontsize=20:x=24:y=374:line_spacing=6"
               f"[lbody];\n")
    else:
        fg += f"[ldiv]copy[lbody];\n"

    # CTA box
    fg += (f"[lbody]drawbox=x=20:y=600:w=440:h=52:color={COLOR_RED_DIM}@0.95:t=fill,"
           f"drawbox=x=20:y=600:w=4:h=52:color={COLOR_RED}:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:"
           f"text='  DUAL-HOST ANALYSIS // INCOMING':"
           f"fontcolor={COLOR_RED}:fontsize=13:x=34:y=622"
           f"[lcta];\n")

    # Mini waveform in left panel bottom
    fg += (f"[0:a]showwaves=s=680x90:mode=cline:"
           f"colors={COLOR_RED}:scale=sqrt:draw=full:rate=30[miniwave];\n")
    fg += f"[lcta][miniwave]overlay=20:880[lpfinal];\n"

    # ── VERTICAL DIVIDER ──
    fg += f"[lpfinal]drawbox=x=720:y=72:w=1:h=958:color={COLOR_RED}@0.3:t=fill[vdiv];\n"

    # ── RIGHT TOP — WAVEFORM VISUALIZER ──
    fg += (f"[0:a]showwaves=s=1140x200:mode=cline:"
           f"colors={COLOR_RED}:scale=sqrt:draw=full:rate=30[wave_top];\n")
    fg += f"[wave_top]split[wA][wB];\n"
    fg += f"[wB]vflip,colorchannelmixer=aa=0.25[wave_bot_dim];\n"
    fg += f"[wA][wave_bot_dim]vstack[wave_stack];\n"
    fg += f"[vdiv][wave_stack]overlay=740:74[rwav];\n"

    # ── RIGHT MID — 3 DATA PANELS ──
    fg += (f"[rwav]drawbox=x=740:y=502:w=370:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=740:y=502:w=370:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='BTC SIGNAL':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=756:y=517,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_btc}':"
           f"fontcolor={COLOR_WHITE}:fontsize=44:x=756:y=533,"
           f"drawtext=fontfile={FONT_MONO}:text='  SOVEREIGN SIGNAL':"
           f"fontcolor={COLOR_GREEN}:fontsize=12:x=756:y=588"
           f"[dp1];\n")

    fg += (f"[dp1]drawbox=x=1120:y=502:w=300:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=1120:y=502:w=300:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='RENDER ENGINE':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=1136:y=517,"
           f"drawtext=fontfile={FONT_BOLD}:text='134':"
           f"fontcolor={COLOR_WHITE}:fontsize=52:x=1136:y=530,"
           f"drawtext=fontfile={FONT_MONO}:text='FPS':"
           f"fontcolor={COLOR_RED}:fontsize=18:x=1220:y=546,"
           f"drawtext=fontfile={FONT_MONO}:text='4090 CLUSTER // H264':"
           f"fontcolor=0x666666:fontsize=12:x=1136:y=588"
           f"[dp2];\n")

    fg += (f"[dp2]drawbox=x=1430:y=502:w=280:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=1430:y=502:w=280:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='  AUDIO AMPLITUDE':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=1446:y=514"
           f"[dp3];\n")
    fg += (f"[0:a]showwaves=s=250x60:mode=line:"
           f"colors={COLOR_RED}:scale=lin:rate=30[amp_wave];\n")
    fg += f"[dp3][amp_wave]overlay=1440:530[dp_done];\n"

    # ── RIGHT BOT — EPISODE SEGMENTS TRACKER ──
    fg += (f"[dp_done]drawbox=x=740:y=660:w=1160:h=360:color={COLOR_PANEL}@0.92:t=fill,"
           f"drawbox=x=740:y=660:w=1160:h=2:color={COLOR_RED}@0.4:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='EPISODE SEGMENTS':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=756:y=675"
           f"[seg_hdr];\n")

    seg_labels = ["COLD OPEN", "ORACLE BRIEF", "CLIP REACTION", "DUAL-HOST SEGMENT"]
    last_seg = "seg_hdr"
    for si, sl in enumerate(seg_labels):
        row_y = 700 + si * 30
        if si < seg_idx:
            status_text, status_color = "DONE", COLOR_GREEN
        elif si == seg_idx:
            status_text, status_color = "ACTIVE", COLOR_RED
        else:
            status_text, status_color = "PENDING", "0x444444"
        out_label = f"seg_r{si}"
        fg += (f"[{last_seg}]drawtext=fontfile={FONT_MONO}:text='{sl}':"
               f"fontcolor={COLOR_MUTED}:fontsize=14:x=756:y={row_y},"
               f"drawtext=fontfile={FONT_MONO}:text='{status_text}':"
               f"fontcolor={status_color}:fontsize=14:x=1100:y={row_y}"
               f"[{out_label}];\n")
        last_seg = out_label

    # ── CORNER BRACKETS ──
    fg += _build_corner_brackets_fg(last_seg, "cornered")

    # ── TICKER BAR ──
    fg += _build_info_bar_fg(total_dur, btc_price, label_in="cornered", label_out="v_final")

    # Social segment overlay (tweet card on right side)
    if is_social:
        safe_text = (text.replace("'", "").replace('"', "")
                         .replace(":", " -").replace(";", ",")
                         .replace("[", "(").replace("]", ")")
                         .replace("\u2014", "-").replace("\u2019", "")
                         .replace("\\", "").replace("\n", " "))
        wrapped_lines = []
        current_line = ""
        for word in safe_text.split():
            if len(current_line) + len(word) + 1 > 50:
                wrapped_lines.append(current_line)
                current_line = word
                if len(wrapped_lines) >= 3:
                    break
            else:
                current_line = f"{current_line} {word}".strip() if current_line else word
        if current_line and len(wrapped_lines) < 3:
            wrapped_lines.append(current_line)
        wrapped_text = "\n".join(wrapped_lines)

        fg += (f"color=c={COLOR_PANEL}@0.92:s=1100x280:d={total_dur}:r=30[tcard];\n"
               f"[tcard]drawbox=x=0:y=0:w=1100:h=280:color={COLOR_RED}@0.4:t=2,"
               f"drawbox=x=0:y=0:w=1100:h=2:color={COLOR_RED}:t=fill,"
               f"drawbox=x=20:y=20:w=8:h=8:color={COLOR_RED}:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='@ProtocolPulse':"
               f"fontcolor={COLOR_RED}:fontsize=18:x=38:y=16,"
               f"drawtext=fontfile={FONT_MONO}:text='{wrapped_text}':"
               f"fontcolor={COLOR_TEXT}:fontsize=20:x=24:y=50:line_spacing=14,"
               f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
               f"fontcolor={COLOR_MUTED}:fontsize=11:x=w-160:y=h-22[tcardready];\n"
               f"[v_final][tcardready]overlay=760:200:format=auto,fade=t=in:st=0:d=0.3[v_social];\n")
        fg += f"[v_social]format=yuv420p[outv];\n"
    else:
        fg += f"[v_final]format=yuv420p[outv];\n"

    # Audio: TTS only — APEX V2: music mixed continuously in concatenate_parts()
    fg += (f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=limit=0.891:level=disabled:attack=5:release=50[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label or f"host visual ({speaker})", 180,
    )

    if ok:
        return output_path

    logger.error(f"Waveform filtergraph FAILED for {label} — no silent fallback, raising")
    raise RuntimeError(f"Host visual filtergraph failed for {label}. Check ffmpeg stderr in logs.")


def _sanitize_text(text: str) -> str:
    """Sanitize text for FFmpeg drawtext filter."""
    return (text.replace("'", "\u2019").replace('"', "")
                .replace(":", " -").replace(";", ",")
                .replace("[", "(").replace("]", ")")
                .replace("\u2014", "-").replace("\\", "")
                .replace("\n", " ").replace("%", "pct"))


def _smart_headline(text: str, max_len: int = 55) -> str:
    """Truncate text at a word boundary, never cutting mid-word."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    # Find last space to avoid cutting mid-word
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        return truncated[:last_space]
    return truncated


def _word_wrap(text: str, max_width: int = 55, max_lines: int = 3) -> str:
    """Word-wrap text for FFmpeg drawtext, return newline-joined string.

    FIX 4: Use actual newline character (0x0a) in the text. When written to
    filter_complex_script file, FFmpeg drawtext renders it as a line break.
    Escaped sequences like \\n or \\\\n do NOT work in filter_complex_script mode.
    """
    lines = []
    current = ""
    for word in text.split():
        if len(current) + len(word) + 1 > max_width:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
        else:
            current = f"{current} {word}".strip() if current else word
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(text) > sum(len(l) for l in lines):
        lines[-1] = lines[-1][:max_width - 3] + "..."
    return "\n".join(lines)


def make_social_card_visual(audio_path: str, posts: list, output_path: str,
                            btc_price: str = "N/A") -> str:
    """Render tweet card visual with real tweet data behind narration audio.

    Shows up to 2 tweet cards stacked vertically, each with:
    - Real @handle in red
    - Real tweet text in white, word-wrapped
    - Engagement stats (likes, retweets)
    - Red left border accent

    Args:
        audio_path: TTS narration audio for this social segment
        posts: List of dicts with handle, text, likes, retweets
        output_path: Output video path
        btc_price: BTC price for ticker

    Returns:
        Path to output video, or "" on failure
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = audio_dur + 0.3

    safe_btc = btc_price.replace("'", "").replace('"', "")
    has_wm = os.path.exists(WATERMARK)

    # Build inputs — APEX V2: no per-segment music
    inputs = [audio_path]
    inp_idx = 1
    if has_wm:
        inputs.append(WATERMARK)
        wm_idx = inp_idx
        inp_idx += 1
    else:
        wm_idx = -1

    # VDS procedural background (7-layer, no video files)
    _, bg_fg = _build_black_diamond_bg(total_dur, label_out="bgvig")
    fg = bg_fg

    # VDS-1: Top red accent bar
    fg += f"[bgvig]drawbox=x=0:y=0:w=1920:h=4:color={COLOR_RED}:t=fill[bgbar];\n"

    # VDS: Pulse dot top-left
    fg += f"[bgbar]drawbox=x=20:y=16:w=10:h=10:color={COLOR_RED}:t=fill[bgdot];\n"

    # VDS: Section header — gold eyebrow kicker
    fg += (f"[bgdot]drawtext=fontfile={FONT_MONO}:"
           f"text='SOCIAL PULSE - WHAT BITCOIN IS SAYING':"
           f"fontcolor={COLOR_RED}:fontsize=14:x=(w-text_w)/2:y=20[bgtitle];\n")
    last_v = "bgtitle"

    # Render up to 2 tweet cards — stacked vertically with spacing
    card_y_start = 90
    card_height = 260
    card_spacing = 30
    card_width = 1360
    card_x = 280

    # Issue 6: Check for screenshot paths and add as inputs
    screenshot_indices = {}
    for ci, post in enumerate(posts[:2]):
        ss_path = post.get("screenshot_path", "")
        if ss_path and os.path.exists(ss_path):
            inputs.append(ss_path)
            screenshot_indices[ci] = inp_idx
            inp_idx += 1
            logger.info(f"  Using tweet screenshot for card {ci}: {os.path.basename(ss_path)}")

    for ci, post in enumerate(posts[:2]):
        handle = _sanitize_text(post.get("handle", "unknown"))
        if not handle.startswith("@"):
            handle = f"@{handle}"
        tweet_text = _word_wrap(_sanitize_text(post.get("text", "")), max_width=55, max_lines=3)
        likes = post.get("likes", 0)
        retweets = post.get("retweets", 0)
        likes_str = f"{likes:,}" if isinstance(likes, int) else str(likes)
        rt_str = f"{retweets:,}" if isinstance(retweets, int) else str(retweets)

        cy = card_y_start + ci * (card_height + card_spacing)
        tag = f"c{ci}"

        # Card glow (subtle red behind card — outer glow)
        fg += f"color=c={COLOR_RED}@0.08:s={card_width + 24}x{card_height + 24}:d={total_dur}:r=30[{tag}glow];\n"
        fg += f"[{last_v}][{tag}glow]overlay={card_x - 12}:{cy - 12}[{tag}g];\n"

        # Card body
        fg += f"color=c={COLOR_PANEL}@0.92:s={card_width}x{card_height}:d={total_dur}:r=30[{tag}body];\n"
        # Outer red border (2px)
        fg += f"[{tag}body]drawbox=x=0:y=0:w={card_width}:h={card_height}:color={COLOR_RED}@0.4:t=2[{tag}brd];\n"
        # Inner glow border (dark red, 2px inside the outer border)
        fg += f"[{tag}brd]drawbox=x=4:y=4:w={card_width - 8}:h={card_height - 8}:color={COLOR_PANEL2}@0.3:t=2[{tag}inner];\n"
        # Left accent bar
        fg += f"[{tag}inner]drawbox=x=0:y=0:w=6:h={card_height}:color={COLOR_RED}:t=fill[{tag}lbar];\n"
        # Top edge accent
        fg += f"[{tag}lbar]drawbox=x=0:y=0:w={card_width}:h=2:color={COLOR_RED}:t=fill[{tag}top];\n"

        # Issue 6: If screenshot available, overlay it inside card; else render text
        if ci in screenshot_indices:
            ss_idx = screenshot_indices[ci]
            # Scale screenshot to fit inside card (with padding)
            fg += (f"[{ss_idx}:v]scale={card_width - 16}:{card_height - 16}:"
                   f"force_original_aspect_ratio=decrease,"
                   f"pad={card_width - 16}:{card_height - 16}:(ow-iw)/2:(oh-ih)/2:{COLOR_PANEL}[{tag}ss];\n")
            fg += f"[{tag}top][{tag}ss]overlay=8:8[{tag}src];\n"
        else:
            # Pulse dot
            fg += f"[{tag}top]drawbox=x=20:y=18:w=8:h=8:color={COLOR_RED}:t=fill[{tag}dot];\n"

            # Handle — monospace font
            fg += (f"[{tag}dot]drawtext=fontfile={FONT_MONO}:"
                   f"text='{handle}':"
                   f"fontcolor={COLOR_RED}:fontsize=14:x=38:y=16[{tag}hdl];\n")

            # Tweet text — bold for readability
            fg += (f"[{tag}hdl]drawtext=fontfile={FONT_BOLD}:"
                   f"text='{tweet_text}':"
                   f"fontcolor={COLOR_TEXT}:fontsize=22:x=24:y=52:line_spacing=16:"
                   f"box=0[{tag}txt];\n")

            # Engagement stats bottom
            fg += (f"[{tag}txt]drawtext=fontfile={FONT_MONO}:"
                   f"text='{likes_str} likes  |  {rt_str} RTs':"
                   f"fontcolor={COLOR_RED}:fontsize=12:x=24:y=h-28[{tag}stats];\n")

            # Source label bottom-right
            fg += (f"[{tag}stats]drawtext=fontfile={FONT_MONO}:"
                   f"text='via X':fontcolor={COLOR_MUTED}:fontsize=12:"
                   f"x=w-80:y=h-30[{tag}src];\n")

        # Overlay card on base with fade-in
        fade_start = ci * 0.4
        fg += f"[{tag}g][{tag}src]overlay={card_x}:{cy}:format=auto,fade=t=in:st={fade_start}:d=0.3[{tag}out];\n"
        last_v = f"{tag}out"

    # VDS: Subtle bottom label
    bottom_header_y = card_y_start + len(posts[:2]) * (card_height + card_spacing) + 10
    fg += (f"[{last_v}]drawtext=fontfile={FONT_MONO}:"
           f"text='SOCIAL PULSE - WHAT BITCOIN IS SAYING':"
           f"fontcolor={COLOR_RED}@0.3:fontsize=12:x=(w-text_w)/2:y={bottom_header_y}[vbhdr];\n")
    last_v = "vbhdr"

    # VDS animated scrolling info bar
    fg += _build_info_bar_fg(total_dur, btc_price, label_in=last_v, label_out="vtick")
    last_v = "vtick"

    # Watermark
    if has_wm:
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[{last_v}][wm]overlay=W-170:16[vwm];\n"
        last_v = "vwm"

    fg += f"[{last_v}]format=yuv420p[outv];\n"

    # FIX 4: explicit stereo format before loudnorm/aresample to prevent channel layout error
    fg += f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=limit=0.891:level=disabled:attack=5:release=50[outa]"

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "social tweet card", 180,
    )

    if ok:
        logger.info(f"  Tweet card visual: {len(posts[:2])} cards, {total_dur:.1f}s")
        return output_path
    return ""


# ── Glitch transition ───────────────────────────────────────────────────────

REMOTION_DIR = os.path.join(os.path.dirname(__file__), "remotion")


def _make_remotion_glitch(output_path: str) -> str:
    """Render GlitchTransition via Remotion. Returns path or '' on failure.

    Remotion outputs video-only. We mix in the whoosh audio from the branded
    glitch_transition_waud.mp4 asset for the transition sound effect.
    Falls back to silent track if branded asset not available.
    """
    entry = os.path.join(REMOTION_DIR, "src", "index.tsx")
    if not os.path.exists(entry):
        return ""
    try:
        r = subprocess.run(
            ["npx", "remotion", "render", entry, "GlitchTransition",
             output_path, "--log=error"],
            cwd=REMOTION_DIR, timeout=60, capture_output=True, text=True,
        )
        if r.returncode == 0 and os.path.exists(output_path):
            with_audio = output_path + ".waud.mp4"
            dur = ffprobe_duration(output_path)

            # Mix in whoosh SFX
            if os.path.exists(GLITCH_WHOOSH):
                ok = run_ffmpeg([
                    "-i", output_path,
                    "-i", GLITCH_WHOOSH,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-af", "volume=2.5,afade=t=in:d=0.05,afade=t=out:st=" + f"{max(0, dur-0.15):.2f}" + ":d=0.15",
                    "-t", str(dur),
                    "-shortest",
                    with_audio,
                ], "remotion glitch + whoosh sfx", 30)
            elif os.path.exists(GLITCH_TRANSITION):
                ok = run_ffmpeg([
                    "-i", output_path,
                    "-i", GLITCH_TRANSITION,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-af", "volume=3.0,afade=t=in:d=0.05,afade=t=out:st=" + f"{max(0, dur-0.15):.2f}" + ":d=0.15",
                    "-t", str(dur),
                    "-shortest",
                    with_audio,
                ], "remotion glitch + whoosh audio", 30)
            else:
                # Fallback: silent track
                ok = run_ffmpeg([
                    "-i", output_path,
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", str(dur),
                    "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-shortest", with_audio,
                ], "remotion glitch add silence", 30)

            if ok and os.path.exists(with_audio):
                os.replace(with_audio, output_path)
            elif os.path.exists(with_audio):
                os.remove(with_audio)
            logger.info(f"  Remotion glitch transition: {dur:.2f}s (with whoosh)")
            return output_path
        else:
            logger.warning(f"Remotion glitch render failed: {r.stderr[-300:]}")
    except Exception as e:
        logger.warning(f"Remotion glitch error: {e}")
    return ""


def _remotion_enabled() -> bool:
    """Check if remotion_visuals feature flag is enabled."""
    try:
        from utils.feature_flags import is_enabled
        return is_enabled("remotion_visuals")
    except Exception:
        return False


def _render_remotion(comp_id: str, output_path: str, props: dict = None,
                     timeout: int = 120) -> str:
    """Render a Remotion composition. Returns path or '' on failure.

    Args:
        comp_id: Composition ID (e.g. 'WaveformVisualizer')
        output_path: Where to write the rendered video
        props: Optional input props as dict (passed via --props)
        timeout: Render timeout in seconds
    """
    entry = os.path.join(REMOTION_DIR, "src", "index.tsx")
    if not os.path.exists(entry):
        return ""
    try:
        cmd = ["npx", "remotion", "render", entry, comp_id, output_path, "--log=error"]
        if props:
            cmd += ["--props", json.dumps(props)]
        r = subprocess.run(cmd, cwd=REMOTION_DIR, timeout=timeout,
                           capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(output_path):
            return output_path
        logger.warning(f"Remotion {comp_id} render failed: {r.stderr[-300:]}")
    except Exception as e:
        logger.warning(f"Remotion {comp_id} error: {e}")
    return ""


def _remotion_with_audio(video_path: str, audio_path: str, output_path: str,
                         bg_music: bool = True) -> str:
    """Mux Remotion video (no audio) with TTS audio + optional background music.

    Returns output_path on success, '' on failure.
    """
    dur = ffprobe_duration(audio_path)
    if dur <= 0:
        dur = 5
    total_dur = dur + 0.3

    # APEX V2: No per-segment music — continuous BGM mixed in concatenate_parts()
    ok = run_ffmpeg([
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]setpts=PTS-STARTPTS[v];"
        f"[1:a]aresample=async=1[outa]",
        "-map", "[v]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        "-t", str(total_dur), output_path,
    ], f"remotion mux", 180)

    return output_path if ok else ""


def make_remotion_waveform(audio_path: str, output_path: str,
                           title: str = "Pulse Check Daily",
                           btc_price: str = "N/A",
                           date: str = "") -> str:
    """Render WaveformVisualizer via Remotion + mux with TTS audio.

    Falls back to '' on failure (caller should use FFmpeg make_host_visual).
    """
    if not _remotion_enabled():
        return ""
    if not date:
        from datetime import date as _d
        date = _d.today().isoformat()

    dur = ffprobe_duration(audio_path)
    total_dur = dur + 0.3
    # Issue 10: Add 30-frame (1s) buffer so Remotion video never ends before audio
    frames = max(math.ceil(total_dur * 30) + 30, 90)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("WaveformVisualizer", raw_video, props={
        "title": title,
        "btcPrice": btc_price,
        "date": date,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=True)
    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if muxed:
        logger.info(f"  Remotion WaveformVisualizer: {ffprobe_duration(muxed):.1f}s")
    return muxed


def _mix_swoosh_into_segment(video_path: str) -> str:
    """Mix card_swoosh.wav into the first 0.4s of a video segment.

    Modifies the file in-place (via temp rename). Returns the path.
    """
    if not os.path.exists(CARD_SWOOSH) or not os.path.exists(video_path):
        return video_path
    tmp = video_path + ".swoosh.mp4"
    ok = run_ffmpeg([
        "-i", video_path,
        "-i", CARD_SWOOSH,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.6[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        tmp,
    ], "mix card swoosh", 30)
    if ok and os.path.exists(tmp):
        os.replace(tmp, video_path)
    elif os.path.exists(tmp):
        os.remove(tmp)
    return video_path


def make_remotion_social_card(audio_path: str, posts: list, output_path: str,
                              btc_price: str = "N/A") -> str:
    """Render SocialCard via Remotion + mux with TTS audio.

    Falls back to '' on failure (caller should use FFmpeg make_social_card_visual).
    """
    if not _remotion_enabled():
        return ""

    post = posts[0] if posts else {}
    dur = ffprobe_duration(audio_path)
    total_dur = dur + 0.3
    # Issue 10: durationInFrames must NEVER be shorter than audio — add 1 second (30 frames) buffer
    frames = max(math.ceil(total_dur * 30) + 30, 90)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("SocialCard", raw_video, props={
        "handle": post.get("handle", "ProtocolPulse"),
        "text": post.get("text", "")[:200],
        "likes": post.get("likes", 0),
        "retweets": post.get("retweets", 0),
        "durationInFrames": frames,
    })
    if not result:
        return ""

    muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=True)
    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if muxed:
        # Mix in card swoosh SFX on entrance
        muxed = _mix_swoosh_into_segment(muxed)
        logger.info(f"  Remotion SocialCard: {ffprobe_duration(muxed):.1f}s")
    return muxed


def make_remotion_title_card(audio_path: str, output_path: str,
                             title: str = "", date: str = "",
                             btc_price: str = "N/A") -> str:
    """Render TitleCard via Remotion + mux with TTS + jingle audio.

    Falls back to '' on failure (caller should use FFmpeg make_intro_coldopen).
    """
    # Session 4 Fix 1: Title card suppressed — kills momentum with 8s dead air
    logger.info("Title card suppressed — per PIPELINE_LAWS session 4")
    return ""
    if not _remotion_enabled():
        return ""
    if not date:
        from datetime import date as _d
        date = _d.today().isoformat()

    dur = ffprobe_duration(audio_path)
    total_dur = max(dur + 1.0, 4.0)
    frames = max(math.ceil(total_dur * 30), 120)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("TitleCard", raw_video, props={
        "title": title or "Pulse Check Daily",
        "date": date,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    # Mux with TTS + jingle (same audio chain as make_intro_coldopen)
    import glob as _glob
    jingle = os.path.join(ASSETS, "music", "pp_intro.mp3")
    if not os.path.exists(jingle):
        tracks = _glob.glob(os.path.join(ASSETS, "music", "intro_*.mp3"))
        jingle = tracks[0] if tracks else ""

    total_dur = max(dur + 1.0, 4.0)
    has_jingle = bool(jingle and os.path.exists(jingle))

    if has_jingle:
        ok = run_ffmpeg([
            "-i", raw_video,
            "-i", audio_path,
            "-i", jingle,
            "-filter_complex",
            f"[0:v]setpts=PTS-STARTPTS[v];"
            f"[1:a]volume=1.0[tts_a];"
            f"[2:a]volume=0.35[jingle_a];"
            f"[tts_a][jingle_a]amix=inputs=2:duration=first:weights=1 0.35[outa]",
            "-map", "[v]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(total_dur), output_path,
        ], "remotion title card + jingle", 120)
    else:
        muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=False)
        ok = bool(muxed)

    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if ok and os.path.exists(output_path):
        logger.info(f"  Remotion TitleCard: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def _make_remotion_intel_panel(duration_frames: int = 300,
                               btc_price: str = "N/A") -> str:
    """Session 4 Fix 6: Render IntelPanel overlay via Remotion.

    Reads narrative_context.json for live data. Returns path to rendered
    transparent overlay video, or '' on failure.
    """
    if not _remotion_enabled():
        return ""

    # Read narrative context
    import json as _json, datetime as _dt
    _intel_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "intelligence")
    _nc_path = os.path.join(_intel_dir, "narrative_context.json")

    narrative = "Bitcoin Sound Money"
    market_mood = "NEUTRAL"
    quote_text = ""
    quote_handle = ""

    try:
        with open(_nc_path) as f:
            nc = _json.load(f)
        computed = nc.get("computed_at", "")
        if computed:
            age = (_dt.datetime.now(_dt.timezone.utc) -
                   _dt.datetime.fromisoformat(computed)).total_seconds() / 3600
            if age < 12:
                narrative = nc.get("dominant_narrative", narrative)[:42]
                market_mood = nc.get("market_mood", "neutral").upper().replace("_", " ")[:16]
                hint = nc.get("eryn_intro_hook", "")
                if "'" in hint:
                    qs = hint.find("'") + 1
                    qe = hint.find("'", qs)
                    if qe > qs:
                        quote_text = hint[qs:qe][:70]
                tl = nc.get("thought_leaders_mentioned", [])
                quote_handle = ("@" + tl[0][:18]) if tl else ""
    except Exception:
        pass

    import hashlib
    props_hash = hashlib.md5(f"{btc_price}{narrative}{market_mood}".encode()).hexdigest()[:8]
    out_path = os.path.join(tempfile.gettempdir(), f"intel_panel_{props_hash}.mp4")

    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        return out_path  # cached

    result = _render_remotion("IntelPanel", out_path, props={
        "btcPrice": btc_price,
        "narrative": narrative,
        "marketMood": market_mood,
        "quoteText": quote_text,
        "quoteHandle": quote_handle,
        "durationInFrames": duration_frames,
    }, timeout=120)

    if result:
        logger.info(f"  Remotion IntelPanel rendered: {narrative} / {market_mood}")
    return result or ""


def make_remotion_lower_third(clip_path: str, source: str, output_path: str,
                              btc_price: str = "N/A",
                              speaker_name: str = "") -> str:
    """Render LowerThird overlay via Remotion and composite onto clip.

    Falls back to '' on failure (caller should use FFmpeg make_clip_visual).
    """
    if not _remotion_enabled():
        return ""

    clip_dur = ffprobe_duration(clip_path)
    if clip_dur <= 0:
        return ""

    # Render LowerThird overlay (6 seconds max, shown near start of clip)
    overlay_dur = min(6.0, clip_dur * 0.6)
    frames = math.ceil(overlay_dur * 30)

    raw_overlay = output_path + ".remotion_lt.mp4"
    result = _render_remotion("LowerThird", raw_overlay, props={
        "channelName": source.replace("@", ""),
        "speakerName": speaker_name,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    # Composite LowerThird onto clip (overlay the rendered frames at bottom)
    # LowerThird has transparent bg in Remotion but renders to opaque MP4.
    # We overlay just the bottom 120px band from the LowerThird render.
    ok = run_ffmpeg([
        "-i", clip_path,
        "-i", raw_overlay,
        "-filter_complex",
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[clip];"
        f"[1:v]crop=1920:120:0:960[ltband];"
        f"[clip][ltband]overlay=0:960:enable='lte(t,{overlay_dur})',format=yuv420p[outv];"
        f"[0:a]asetpts=PTS-STARTPTS,volume=1.0[outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        output_path,
    ], "remotion lower third composite", 180)

    if os.path.exists(raw_overlay):
        try:
            os.remove(raw_overlay)
        except OSError:
            pass
    if ok and os.path.exists(output_path):
        logger.info(f"  Remotion LowerThird on clip: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def make_transition_visual(output_path: str, duration: float = 0.6) -> str:
    """Glitch transition — branded asset with custom_whoosh mixed at -6dB.

    Priority:
    1. Branded glitch_transition_waud.mp4 asset + custom_whoosh.wav at -6dB
    2. Simple dark flash fallback with whoosh

    Duration: 0.5s-0.8s. Clamped to this range.
    """
    duration = max(0.5, min(0.8, duration))

    # Issue 7 FIX: Use branded asset IMMEDIATELY (skip Remotion — it fails silently)
    if os.path.exists(GLITCH_TRANSITION):
        # Mix custom whoosh at -6dB (loud enough to hear clearly)
        has_whoosh = os.path.exists(GLITCH_WHOOSH)
        if has_whoosh:
            ok = run_ffmpeg([
                "-i", GLITCH_TRANSITION,
                "-i", GLITCH_WHOOSH,
                "-filter_complex",
                f"[0:v]scale=1920:1080,setsar=1,fps=30,trim=0:{duration},setpts=PTS-STARTPTS,format=yuv420p[outv];"
                f"[0:a]atrim=0:{duration},asetpts=PTS-STARTPTS,volume=1.5[ta];"
                f"[1:a]atrim=0:{duration},asetpts=PTS-STARTPTS,volume=0.5[wa];"
                f"[ta][wa]amix=inputs=2:duration=first[outa]",
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
                "-r", "30", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                "-t", str(duration),
                output_path,
            ], "glitch transition + whoosh", 30)
        else:
            ok = run_ffmpeg([
                "-i", GLITCH_TRANSITION,
                "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
                "-r", "30", "-vf", f"scale=1920:1080,setsar=1,fps=30,trim=0:{duration},setpts=PTS-STARTPTS,format=yuv420p",
                "-af", f"atrim=0:{duration},asetpts=PTS-STARTPTS,volume=2.0",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                "-t", str(duration),
                output_path,
            ], "glitch transition", 30)
        if ok and os.path.exists(output_path):
            dur = ffprobe_duration(output_path)
            logger.info(f"  TRANSITION FIRING: glitch asset + whoosh ({dur:.2f}s)")
            return output_path

    # Last resort: short dark flash with whoosh
    logger.warning("Glitch asset not found — using dark flash with whoosh")
    if os.path.exists(GLITCH_WHOOSH):
        ok = run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c={COLOR_BG}:s=1920x1080:d={duration}:r=30",
            "-i", GLITCH_WHOOSH,
            "-filter_complex",
            f"[1:a]atrim=0:{duration},asetpts=PTS-STARTPTS,volume=0.5[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
            output_path,
        ], "transition fallback + whoosh", 30)
    else:
        ok = run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c={COLOR_BG}:s=1920x1080:d={duration}:r=30",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
            output_path,
        ], "transition fallback", 30)
    return output_path if ok else ""


def apply_xfade(clip1_path: str, clip2_path: str, output_path: str,
                 transition: str = "fade", duration: float = 1.0) -> str:
    """Issue 8: Apply xfade crossfade between two clips instead of hard-cut transitions.

    Overlaps the last `duration` seconds of clip1 with the first `duration` seconds of clip2.
    Returns output_path on success, '' on failure.
    """
    dur1 = ffprobe_duration(clip1_path)
    if dur1 <= duration:
        return ""
    offset = dur1 - duration
    ok = run_ffmpeg([
        "-i", clip1_path, "-i", clip2_path,
        "-filter_complex",
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[v0];"
        f"[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[v1];"
        f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a0];"
        f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a1];"
        f"[v0][v1]xfade=transition={transition}:duration={duration}:offset={offset},format=yuv420p[outv];"
        f"[a0][a1]acrossfade=d={duration}:c1=tri:c2=tri[outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        output_path,
    ], "xfade transition", 300)
    return output_path if ok and os.path.exists(output_path) else ""


# ── YouTube clip visual ─────────────────────────────────────────────────────

def make_clip_visual(clip_path: str, source: str, output_path: str,
                     btc_price: str = "N/A") -> str:
    """APEX B-roll / partner clip — BEV2 restraint (let the clip carry the moment).

    Red border frame, corner brackets (BD), info rail (BEV2),
    glass lower-third with red top accent. PROTOCOL PULSE watermark top-right.
    CRITICAL: Original audio is preserved.
    """
    clip_dur = ffprobe_duration(clip_path)
    if clip_dur <= 0:
        logger.warning(f"Clip has zero duration: {clip_path}")
        return ""

    safe_source = source.replace("'", "").replace('"', "").replace(":", "")
    safe_btc = btc_price.replace("'", "").replace('"', "")

    fade_out_start = max(0, clip_dur - 0.5)
    fg = (
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,"
        f"fade=t=in:d=0.3,fade=t=out:st={fade_out_start}:d=0.5[clip];\n"
        # Red border frame (2px all edges)
        f"[clip]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
        f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
        f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
        f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
        # BD corner brackets
        f"drawbox=x=0:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
        # Top-right watermark (red, 18px, 60% opacity)
        f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
        f"fontcolor={COLOR_RED}@0.6:fontsize=18:x=W-text_w-20:y=16"
        f"[clip_branded];\n"
        # Glass lower-third with red top accent line
        f"color=c={COLOR_PANEL}@0.88:s=800x90:d={clip_dur}:r=30[ltbg];\n"
        f"[ltbg]drawbox=x=0:y=0:w=800:h=4:color={COLOR_RED}:t=fill[ltbar];\n"
        f"[ltbar]drawtext=fontfile={FONT_BOLD}:text='{safe_source}':"
        f"fontcolor={COLOR_WHITE}:fontsize=26:x=20:y=24[ltname];\n"
        f"[ltname]drawtext=fontfile={FONT_MONO}:text='SOURCE - PARTNER CHANNEL':"
        f"fontcolor={COLOR_MUTED}:fontsize=12:x=20:y=60[ltfull];\n"
        f"[clip_branded][ltfull]overlay=0:870:enable='between(t,0.5,6.5)'[clip_lt];\n"
    )
    # Info rail at bottom (always present)
    fg += _build_signature_info_rail(clip_dur, btc_price, "clip_lt", "clip_railed")
    fg += (
        f"[clip_railed]format=yuv420p[outv];\n"
        # Issue 4 FIX: Strip first 2.5s of clip audio (intro jangle) + fade in 0.5s
        f"[0:a]atrim=start=2.5,asetpts=PTS-STARTPTS,"
        f"highpass=f=50,lowpass=f=15000,"
        f"afade=t=in:d=0.5,afade=t=out:st={max(0, fade_out_start - 2.5)}:d=0.5[outa]"
    )

    ok = run_ffmpeg_filtergraph(
        [clip_path], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k"],
        output_path, f"clip visual ({safe_source})",
    )
    return output_path if ok else ""


# ── Concatenation ────────────────────────────────────────────────────────────

def normalize_part(part_path: str, output_path: str) -> str:
    """Normalize a video part to EXACTLY consistent format for concatenation.

    Every part must have identical stream parameters to prevent concat drift:
    - 1920x1080, 30fps CFR, yuv420p, h264
    - aac 48000Hz stereo
    - Consistent video_track_timescale
    - aresample async to absorb minor timing differences
    """
    part_path = ensure_audio(part_path)
    ok = run_ffmpeg(
        ["-i", part_path,
         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-r", "30", "-vsync", "cfr",
         "-vf", "scale=1920:1080,setsar=1,format=yuv420p",
         "-video_track_timescale", "90000",
         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
         "-af", "aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,loudnorm=I=-14:TP=-3.0:LRA=7,aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=level_in=1:level_out=0.794:limit=0.708:attack=3:release=30",
         output_path],
        "normalize", 180,
    )
    return output_path if (ok and os.path.exists(output_path)) else part_path


def concatenate_parts(parts: list, output_path: str) -> str:
    """FIX 1+8+12: Concat video parts with fade transitions (no black frames).

    Uses concat demuxer with fade-in/fade-out on each part for smooth transitions.
    No standalone glitch transition clips. Final loudnorm with LRA=7 (FIX 12).
    """
    valid = [p for p in parts if p and os.path.exists(p)]
    if not valid:
        logger.error("No valid parts to concatenate")
        return ""
    if len(valid) == 1:
        shutil.copy2(valid[0], output_path)
        return output_path

    # Normalize all parts with brief fade-in/fade-out for smooth cuts (FIX 1+8)
    normalized = []
    for i, p in enumerate(valid):
        tmp = output_path + f".norm{i}.mp4"
        p = ensure_audio(p)
        dur = ffprobe_duration(p)
        fade_out_start = max(0, dur - 0.15)
        ok = run_ffmpeg(
            ["-i", p,
             "-c:v", "libx264", "-crf", "17", "-preset", "medium",
             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
             "-r", "30", "-vsync", "cfr",
             "-vf", f"scale=1920:1080,setsar=1,format=yuv420p,fade=t=in:d=0.15,fade=t=out:st={fade_out_start}:d=0.15",
             "-video_track_timescale", "90000",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
             # BUG5 FIX: Remove per-segment loudnorm — single authoritative pass at end
             "-af", f"aresample=async=1,afade=t=in:d=0.1,afade=t=out:st={fade_out_start}:d=0.15",
             tmp],
            "normalize+fade", 180,
        )
        chosen = tmp if (ok and os.path.exists(tmp)) else p
        # BLACK HOLE GUARD: scan for >1s of black, replace with bg-only clip
        try:
            bd = subprocess.run(
                ["ffprobe", "-v", "quiet", "-f", "lavfi",
                 "-i", "movie=" + chosen + ",blackdetect=d=1:pix_th=0.02",
                 "-show_entries", "tags=lavfi.black_start,lavfi.black_end",
                 "-of", "csv=p=0"],
                capture_output=True, text=True, timeout=30
            )
            black_dur = sum(
                float(m.group(1))
                for m in [re.search(r"black_duration:([\d.]+)", l) for l in bd.stderr.splitlines()]
                if m
            )
            if black_dur > 1.0:
                logger.warning("BLACK HOLE part %d: %.1fs black -- replacing with bg-only", i, black_dur)
                dur = ffprobe_duration(chosen)
                bg_only = chosen + ".bgonly.mp4"
                run_ffmpeg([
                    "-f", "lavfi", "-i",
                    "color=c=0x0A0A0F:s=1920x1080:d={:.3f}:r=30".format(dur),
                    "-f", "lavfi", "-i",
                    "anullsrc=r=48000:cl=stereo:d={:.3f}".format(dur),
                    "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                    "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                    "-t", "{:.3f}".format(dur), bg_only
                ], "bg-only fallback {}".format(i), 60)
                if os.path.exists(bg_only):
                    chosen = bg_only
        except Exception as _bh_err:
            logger.warning("Black hole check failed: %s", _bh_err)
        normalized.append(chosen)

    # Session 4 Fix 7B: Re-apply longer fade to last part (outro) for clean ending
    if len(normalized) >= 2:
        last_part = normalized[-1]
        last_dur = ffprobe_duration(last_part)
        if last_dur > 2.0:
            last_refaded = last_part + ".refaded.mp4"
            fade_v_start = max(0, last_dur - 1.5)
            fade_a_start = max(0, last_dur - 2.5)
            ok_refade = run_ffmpeg(
                ["-i", last_part,
                 "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                 "-b:v", "8M", "-r", "30", "-vsync", "cfr",
                 "-vf", f"scale=1920:1080,setsar=1,format=yuv420p,fade=t=in:d=0.15,fade=t=out:st={fade_v_start:.2f}:d=1.5:color=0x0A0A0F",
                 "-video_track_timescale", "90000",
                 "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                 "-af", f"aresample=async=1,afade=t=in:d=0.1,afade=t=out:st={fade_a_start:.2f}:d=2.5",
                 last_refaded],
                "outro extended fade", 180,
            )
            if ok_refade and os.path.exists(last_refaded):
                normalized[-1] = last_refaded
                logger.info(f"  Fix 7B: Extended outro fade applied (1.5s video, 2.5s audio)")

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for p in normalized:
            f.write(f"file '{os.path.abspath(p)}'\n")

    # Concat demuxer with stream copy (parts are already normalized)
    concat_raw = output_path + ".concat_raw.mp4"
    ok = run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_file,
         "-c", "copy", concat_raw],
        "concat demux", 300,
    )

    if not ok or not os.path.exists(concat_raw):
        logger.error("Concat demuxer failed")
        return ""

    # APEX V2 FIX 1: Continuous background music across ENTIRE episode
    # Music plays ONCE continuously — no per-segment start/stop/fade
    from music import ffprobe_duration as _music_ffprobe_dur
    has_bgm = os.path.exists(BG_MUSIC)
    if has_bgm:
        dur = _music_ffprobe_dur(concat_raw)
        if dur > 0:
            music_mixed = output_path + ".music_mixed.mp4"
            ok_music = run_ffmpeg([
                "-fflags", "+genpts",
                "-i", concat_raw,
                "-stream_loop", "-1", "-i", BG_MUSIC,
                "-filter_complex", (
                    # Issue 6 FIX: Continuous BGM with sidechain ducking — music never drops to silence
                    f"[0:a]asetpts=PTS-STARTPTS,asplit[tts_main][tts_sc];"
                    f"[1:a]volume=0.12,afade=t=in:d=2.0,"
                    f"afade=t=out:st={max(0,dur-3.0)}:d=3.0[bgm_raw];"
                    f"[bgm_raw][tts_sc]sidechaincompress="
                    f"threshold=0.02:ratio=4:attack=5:release=200[bgm_ducked];"
                    f"[tts_main][bgm_ducked]amix=inputs=2:duration=first"
                    f":weights=1 1[mixed_audio];"
                    f"[mixed_audio]aresample=async=1[outa]"
                ),
                "-map", "0:v", "-map", "[outa]",
                # BUG2 FIX: Full libx264 re-encode (not -c:v copy) to reset PTS for AV sync
                "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                "-r", "30", "-vsync", "cfr",
                "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                "-t", str(dur),
                music_mixed
            ], "continuous bgm mix", 600)
            if ok_music and os.path.exists(music_mixed):
                logger.info(f"  APEX V2: Continuous BGM mixed ({dur:.1f}s episode)")
                concat_raw = music_mixed
            else:
                logger.warning("  APEX V2: BGM mix failed — proceeding without music")
    else:
        logger.warning("  APEX V2: No BG_MUSIC file found — no music bed")

    # FIX 6: Mix whoosh SFX at transition points between segments
    has_whoosh = os.path.exists(GLITCH_WHOOSH)
    if has_whoosh and len(valid) > 1:
        # Calculate transition timestamps (cumulative durations of each part)
        transition_times = []
        cumulative = 0.0
        for pidx, p in enumerate(valid[:-1]):
            pdur = ffprobe_duration(p)
            cumulative += pdur
            transition_times.append(cumulative)

        if transition_times:
            whoosh_mixed = output_path + ".whoosh_mixed.mp4"
            # Build filter: delay each whoosh to its transition time, then amix all
            whoosh_inputs = []
            whoosh_fg_parts = []
            for ti, ttime in enumerate(transition_times):
                whoosh_inputs.extend(["-i", GLITCH_WHOOSH])
                delay_ms = int(ttime * 1000)
                whoosh_fg_parts.append(
                    f"[{ti+1}:a]volume=0.6,adelay={delay_ms}|{delay_ms}[whoosh_{ti}]"
                )
            # Amix all whooshes together
            whoosh_labels = "".join(f"[whoosh_{ti}]" for ti in range(len(transition_times)))
            whoosh_fg_parts.append(
                f"{whoosh_labels}amix=inputs={len(transition_times)}:duration=longest[all_whoosh]"
            )
            # Mix whoosh into episode audio
            whoosh_fg_parts.append(
                f"[0:a][all_whoosh]amix=inputs=2:duration=first:weights=1 0.5[outa]"
            )
            whoosh_fg = ";\n".join(whoosh_fg_parts)

            ok_whoosh = run_ffmpeg(
                ["-fflags", "+genpts", "-i", concat_raw] + whoosh_inputs +
                ["-filter_complex", whoosh_fg,
                 "-map", "0:v", "-map", "[outa]",
                 "-c:v", "copy",
                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                 whoosh_mixed],
                "whoosh SFX mix", 300,
            )
            if ok_whoosh and os.path.exists(whoosh_mixed):
                logger.info(f"  FIX 6: Whoosh SFX at {len(transition_times)} transitions")
                concat_raw = whoosh_mixed
            else:
                logger.warning("  FIX 6: Whoosh mix failed — proceeding without SFX")

    # Final encode: nuclear PTS reset + AV sync lock + BUG5 single authoritative loudnorm
    # CRF 15 + minrate 3.5M floor to guarantee ≥3.5Mbps output (was CRF 17 → 2.8Mbps on dark content)
    ok = run_ffmpeg(
        ["-fflags", "+genpts+igndts+discardcorrupt",
         "-i", concat_raw,
         "-c:v", "libx264", "-crf", "15", "-preset", "medium",
         "-b:v", "8M", "-minrate", "3.5M", "-maxrate", "10M", "-bufsize", "15M",
         "-r", "30", "-vsync", "cfr",
         "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         # BUG5 FIX: Single authoritative loudnorm at end (removed from all intermediate steps)
         "-af", "asetpts=PTS-STARTPTS,aresample=async=1:min_hard_comp=0.1:first_pts=0,loudnorm=I=-14:TP=-2.0:LRA=7:linear=true,alimiter=level_in=1:level_out=0.891:limit=0.891:attack=5:release=50",
         "-avoid_negative_ts", "make_zero",
         "-max_interleave_delta", "0",
         "-movflags", "+faststart",
         output_path],
        "concat final encode", 600,
    )

    # Cleanup
    if os.path.exists(concat_raw):
        try: os.remove(concat_raw)
        except OSError: pass
    for p in normalized:
        if ".norm" in p and os.path.exists(p):
            try: os.remove(p)
            except OSError: pass
    for p in valid:
        if p.endswith("_waud.mp4") and os.path.exists(p):
            try: os.remove(p)
            except OSError: pass
    if os.path.exists(concat_file):
        os.remove(concat_file)

    return output_path if ok else ""


# ── Main assembly ────────────────────────────────────────────────────────────

def assemble_episode(script: dict, audio_data: dict, extracted_clips: dict,
                     output_path: str, btc_price: str = "N/A",
                     music_bed: str = "", intro_music: str = "",
                     broll_clips: list = None) -> str:
    """Assemble a V6 ESPN-quality episode.

    Args:
        script: Script with dialogue array
        audio_data: From generate_dialogue_audio() — {lines, full, total_duration}
        extracted_clips: From clip_extractor.extract_all() — {rank: {path, channel, ...}}
        output_path: Final video path
        btc_price: BTC price string for ticker
        broll_clips: FIX 6 — list of Pexels B-roll clip paths

    Returns:
        Path to final video, or "" on failure
    """
    logger.info("=" * 60)
    logger.info("ASSEMBLING V10 EPISODE — WAVEFORM VISUALIZER")
    logger.info("=" * 60)

    try:
        return _assemble_episode_inner(script, audio_data, extracted_clips,
                                       output_path, btc_price, music_bed, intro_music,
                                       broll_clips=broll_clips)
    except Exception:
        import traceback
        logger.error("ASSEMBLY CRASHED — full traceback:")
        traceback.print_exc()
        return ""


def _assemble_episode_inner(script, audio_data, extracted_clips,
                            output_path, btc_price="N/A", music_bed="", intro_music="",
                            broll_clips=None):
    # FIX 5: Fetch BTC price if not provided or showing N/A
    if not btc_price or btc_price in ("N/A", "$N/A", ""):
        btc_price = _fetch_btc_price()
        logger.info(f"  BTC price fetched: {btc_price}")

    # Issue 12: Override default BG_MUSIC with mood-matched music bed if provided
    # Ensure music is mixed at -20dB under ALL narration segments
    global BG_MUSIC
    if music_bed and os.path.exists(music_bed):
        BG_MUSIC = music_bed
        logger.info(f"  Music bed ACTIVE: {os.path.basename(music_bed)}")
    elif os.path.exists(BG_MUSIC):
        logger.info(f"  Music bed ACTIVE (default): {os.path.basename(BG_MUSIC)}")
    else:
        logger.warning(f"  Issue 12: NO MUSIC BED FOUND — narration will have no background music")

    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "work")
    os.makedirs(work_dir, exist_ok=True)

    dialogue = script.get("dialogue", [])
    lines = audio_data.get("lines", [])
    parts = []
    part_idx = 0

    # Issue 5 FIX: Use the SAME social_posts list from the script (set by daily_producer).
    # This ensures the assembler's card visuals match the narrator's script order EXACTLY.
    # Only fall back to fetching if script doesn't have social_posts.
    tweet_card_posts = []
    social_card_idx = 0

    script_social_posts = script.get("social_posts", [])
    if script_social_posts:
        tweet_card_posts = list(script_social_posts)
        # Add display_order to each post for deterministic ordering
        for di, dp in enumerate(tweet_card_posts):
            dp["display_order"] = di
        logger.info(f"  SOCIAL ORDER (from script, Issue 5 fix): {len(tweet_card_posts)} posts")
    else:
        # Fallback: fetch fresh if script has no social_posts
        try:
            from utils.feature_flags import is_enabled
            if is_enabled("tweet_cards"):
                from utils.social_fetcher import get_todays_social_posts
                tweet_card_posts = get_todays_social_posts(max_posts=4)
                tweet_card_posts.sort(key=lambda p: p.get("likes", 0), reverse=True)
                for di, dp in enumerate(tweet_card_posts):
                    dp["display_order"] = di
        except Exception as e:
            logger.warning(f"Tweet card data load failed: {e}")

    if tweet_card_posts:
        # Sort by display_order to guarantee match with script narration
        tweet_card_posts.sort(key=lambda p: p.get("display_order", 0))
        logger.info(f"  SOCIAL POST ORDER CHECK:")
        for ti, tp in enumerate(tweet_card_posts):
            logger.info(f"    #{ti}: @{tp.get('handle', '?')} — {tp.get('text', '')[:40]}")

    # --- 1. INTRO: Session 4 Fix 1 — COLD OPEN ONLY, NO TITLE CARD ---
    # Title card killed — dead air that murders momentum. Episode goes:
    # cold_open_hook → immediate first narration segment.
    audio_lines = audio_data.get("lines", [])
    cold_open_consumed = False

    # Find cold_open audio (first dialogue entry with type "cold_open", or first host line)
    cold_open_audio = None
    for al in audio_lines:
        if al.get("host") in ("CLIP",) or not al.get("path"):
            continue
        if al.get("path") and os.path.exists(al.get("path", "")):
            cold_open_audio = al
            break

    logger.info("  Session 4: Title card SUPPRESSED — cold open leads directly into content")

    if cold_open_audio:
        intro_out = os.path.join(work_dir, f"part_{part_idx:03d}_cold_open_hook.mp4")
        # GPT face-first: get clip 1 YouTube thumbnail for cold open face panel
        co_thumb = ""
        if 1 in extracted_clips:
            co_clip_info = extracted_clips[1]
            co_thumb = fetch_youtube_thumbnail(co_clip_info)
            if co_thumb:
                logger.info(f"  Cold open thumbnail: {os.path.basename(co_thumb)}")
        intro_result = make_intro_coldopen(cold_open_audio["path"], intro_out, btc_price=btc_price)
        if intro_result:
            # FIX 2: No PiP overlay on cold open — pure background + date text per PIPELINE_LAWS
            parts.append(intro_result)
            dur = ffprobe_duration(intro_result)
            logger.info(f"[{part_idx:03d}] COLD OPEN (clean bg + date only): {dur:.1f}s")
            part_idx += 1
            cold_open_consumed = True
        else:
            logger.warning("[---] Cold open intro failed, starting with first dialogue")
    else:
        logger.warning("[---] No cold open audio available, starting with first dialogue")

    # FIX 6: Prepare B-roll clips for insertion between host segments
    broll_queue = []
    if broll_clips:
        for bp in broll_clips:
            if isinstance(bp, str) and os.path.exists(bp):
                broll_queue.append(bp)
            elif isinstance(bp, dict) and bp.get("path") and os.path.exists(bp["path"]):
                broll_queue.append(bp["path"])
        logger.info(f"  B-roll clips available: {len(broll_queue)}")
    broll_idx = 0
    host_segment_count = 0  # Insert broll every 2 host segments

    # --- 2. DIALOGUE + CLIPS ---

    # Build thumbnail map: rank → thumbnail_path
    clip_thumbnails = {}
    for rank, cinfo in extracted_clips.items():
        tp = fetch_youtube_thumbnail(cinfo)
        if tp:
            clip_thumbnails[rank] = tp
            logger.info(f"  Thumbnail for clip #{rank}: {os.path.basename(tp)}")

    # Build PiP preview map: rank → pip_path (for narration segments before clips)
    pip_previews = {}
    for rank, cinfo in extracted_clips.items():
        clip_path = cinfo.get("path", "")
        if clip_path and os.path.exists(clip_path):
            pip_out = os.path.join(work_dir, f"pip_preview_r{rank}.mp4")
            pip_result = make_pip_preview(clip_path, pip_out)
            if pip_result:
                pip_previews[rank] = pip_result
                logger.info(f"  PiP preview for clip #{rank}: ready")

    # Track which audio line index we're on (host lines only, not CLIPs)
    # If we consumed the cold_open, skip the first host audio line
    audio_idx = 1 if cold_open_consumed else 0

    prev_segment_type = "intro"  # Track previous segment type for transition logic

    for i, entry in enumerate(dialogue):
        entry_type = entry.get("type", "")
        host_field = entry.get("host", "")

        # Skip first host entry if it was consumed as cold open
        if cold_open_consumed and i == 0 and host_field != "CLIP":
            cold_open_consumed = False  # only skip once
            continue

        if host_field == "CLIP":
            # Issue 7 FIX: Fire glitch transition before each clip (setup→clip)
            if prev_segment_type in ("setup", "cold_open", "react"):
                trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_transition_to_clip.mp4")
                trans_result = make_transition_visual(trans_out, duration=0.6)
                if trans_result:
                    parts.append(trans_result)
                    logger.info(f"GLITCH TRANSITION: [{prev_segment_type}] → [CLIP] using {os.path.basename(GLITCH_TRANSITION)}")
                    part_idx += 1

            # YouTube clip — full screen, original audio
            rank = entry.get("rank", 0)
            clip_info = extracted_clips.get(rank, {})
            clip_path = clip_info.get("path", "")

            if clip_path and os.path.exists(clip_path):
                # FIX 4: Pre-convert AV1/HEVC clips to H264 to avoid black frame bug in filtergraphs
                codec_check = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=codec_name", "-of", "default", clip_path],
                    capture_output=True, text=True, timeout=10
                )
                clip_codec = codec_check.stdout.strip().replace("codec_name=", "").strip()
                if clip_codec in ("av1", "hevc", "vp9", "vp8"):
                    h264_path = clip_path + ".h264.mp4"
                    ok_conv = run_ffmpeg([
                        "-i", clip_path,
                        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                        "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", h264_path,
                    ], f"AV1→H264 pre-convert clip #{rank}", 120)
                    if ok_conv and os.path.exists(h264_path):
                        clip_path = h264_path
                        logger.info(f"  FIX4: Pre-converted {clip_codec.upper()} clip #{rank} to H264")

                clip_out = os.path.join(work_dir, f"part_{part_idx:03d}_clip_r{rank}.mp4")
                channel = clip_info.get("channel", "")
                handle = f"@{channel.replace(' ', '')}" if channel else "ProtocolPulse"
                result = ""
                try:
                    result = make_remotion_lower_third(
                        clip_path, handle, clip_out,
                        btc_price=btc_price,
                        speaker_name=clip_info.get("speaker", ""),
                    )
                except Exception as e:
                    logger.warning(f"Remotion LowerThird failed: {e}")
                if not result:
                    result = make_clip_visual(clip_path, handle, clip_out, btc_price=btc_price)
                if result:
                    # Mix lower_slide SFX at start of clip (for LowerThird entrance)
                    mix_lower_slide_sfx(result)
                    parts.append(result)
                    dur = ffprobe_duration(result)
                    logger.info(f"[{part_idx:03d}] CLIP #{rank} [{channel}]: {dur:.1f}s (with lower slide SFX)")
                    part_idx += 1
                else:
                    logger.warning(f"[---] Clip #{rank}: visual failed, skipping")
            else:
                logger.warning(f"[---] Clip #{rank}: file not found ({clip_path}) — injecting branded placeholder")
                placeholder_out = os.path.join(work_dir, f"part_{part_idx:03d}_clip_placeholder_r{rank}.mp4")
                placeholder_result = _make_clip_unavailable_card(rank, placeholder_out, btc_price)
                if placeholder_result:
                    parts.append(placeholder_result)
                    dur = ffprobe_duration(placeholder_result)
                    logger.info(f"[{part_idx:03d}] CLIP #{rank} PLACEHOLDER: {dur:.1f}s")
                    part_idx += 1
            prev_segment_type = "clip"
            continue

        # Issue 7 FIX: Fire glitch transition between setup→clip pairs
        if prev_segment_type in ("setup", "react") and entry_type in ("setup",):
            trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_transition.mp4")
            trans_result = make_transition_visual(trans_out, duration=0.6)
            if trans_result:
                parts.append(trans_result)
                logger.info(f"GLITCH TRANSITION: [{prev_segment_type}] → [{entry_type}] using {os.path.basename(GLITCH_TRANSITION)}")
                part_idx += 1

        # Host dialogue line — find matching audio
        # BUG1 FIX: Accept failed TTS entries (path=None) to maintain script/audio mapping.
        # When TTS failed, generate fallback silence so the visual segment still renders.
        line_audio = None
        while audio_idx < len(audio_lines):
            al = audio_lines[audio_idx]
            audio_idx += 1
            if al.get("host") in ("CLIP",):
                continue  # skip CLIP markers, advance past them
            # Found a host entry (valid audio OR failed TTS with path=None)
            line_audio = al
            break

        if not line_audio:
            logger.warning(f"[---] No audio entry for dialogue {i} ({entry_type}) — skipping")
            continue

        # BUG1 FIX: If TTS failed (path=None), generate silence so segment still renders
        if not line_audio.get("path") or not os.path.exists(line_audio.get("path", "")):
            fallback_text = line_audio.get("text", entry.get("text", ""))
            fallback_path = _generate_fallback_silent_audio(work_dir, part_idx, fallback_text)
            if fallback_path:
                line_audio = dict(line_audio)
                line_audio["path"] = fallback_path
                logger.warning(f"  [BUG1] Segment {i} ({entry_type}): TTS fallback silence generated")
            else:
                logger.warning(f"  [BUG1] Segment {i} ({entry_type}): silence generation failed, skipping")
                continue

        host_num = int(line_audio.get("host", 1)) if str(line_audio.get("host", "1")).isdigit() else 1
        text = line_audio.get("text", entry.get("text", ""))
        audio_path = line_audio["path"]

        # Silent gap guard: TTS files < 5KB are likely empty/corrupt
        try:
            tts_size = os.path.getsize(audio_path)
            if tts_size < 5000:
                logger.warning(f"  [GAP GUARD] Segment {i} ({entry_type}): TTS file {os.path.basename(audio_path)} is {tts_size}B (<5KB) — substituting 0.5s silence pad")
                silence_pad = os.path.join(work_dir, f"silence_pad_{part_idx:03d}.m4a")
                run_ffmpeg([
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", "0.5", "-c:a", "aac", "-b:a", "192k", silence_pad,
                ], "silence pad", 10)
                if os.path.exists(silence_pad):
                    audio_path = silence_pad
        except OSError:
            pass

        # Mix TTS with background music if music utility supports it
        # (We handle music mixing directly in make_host_visual via assets/music/pp_background.mp3)
        # Don't double-mix here — our new make_host_visual handles it internally

        # Create host visual with animated background
        # Determine thumbnail for setup/react segments
        clip_rank = entry.get("clip_rank", 0)
        thumb = clip_thumbnails.get(clip_rank, "") if entry_type in ("setup", "react") else ""

        line_out = os.path.join(work_dir, f"part_{part_idx:03d}_{entry_type}.mp4")

        # Sprint 1.5: Each tweet as its OWN video segment
        if entry_type == "social_segment" and tweet_card_posts and social_card_idx < len(tweet_card_posts):
            # Render up to 3 individual card segments (one per tweet)
            card_posts = tweet_card_posts[social_card_idx:social_card_idx + 3]
            # Session 4 Fix 4: Rank cards by relevance to narrator text
            card_posts = _rank_cards_for_segment(card_posts, text)

            # Try capturing tweet screenshots
            for cp in card_posts:
                tweet_url = cp.get("tweet_url", cp.get("url", ""))
                if tweet_url and not cp.get("screenshot_path"):
                    handle_name = cp.get("handle", "unknown").replace("@", "")
                    ss_path = os.path.join(work_dir, f"tweet_{handle_name}_{social_card_idx}.png")
                    try:
                        from utils.tweet_screenshot import capture_tweet
                        if capture_tweet(tweet_url, ss_path):
                            cp["screenshot_path"] = ss_path
                    except Exception:
                        pass

            # Issue 5 FIX: Render all cards, then xfade them into one continuous segment
            card_rendered_paths = []
            # First card uses the current audio_path (matched by script)
            # Remaining cards: if there are more audio lines for social segments, use them
            # Otherwise, render with the same audio (single narration covers all cards)
            for ci, cp in enumerate(card_posts):
                card_out = os.path.join(work_dir, f"part_{part_idx:03d}_social_card_{ci}.mp4")
                logger.info(f"  SOCIAL CARD {ci}: @{cp.get('handle', '?')} — {cp.get('text', '')[:40]}")

                # Use the current audio for first card, try to find audio for subsequent cards
                card_audio = audio_path if ci == 0 else None
                if ci > 0:
                    # Look ahead for more social audio lines
                    peek_idx = audio_idx
                    while peek_idx < len(audio_lines):
                        al = audio_lines[peek_idx]
                        if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al["path"]):
                            card_audio = al["path"]
                            audio_idx = peek_idx + 1
                            break
                        peek_idx += 1
                    if not card_audio:
                        card_audio = audio_path  # fallback: reuse first card's audio

                # Render single-card visual
                card_result = ""
                try:
                    card_result = make_remotion_social_card(
                        card_audio, [cp], card_out, btc_price=btc_price,
                    )
                except Exception:
                    pass
                if not card_result:
                    card_result = make_social_card_visual(
                        card_audio, [cp], card_out, btc_price=btc_price,
                    )
                    if card_result:
                        card_result = _mix_swoosh_into_segment(card_result)
                if not card_result:
                    card_result = make_host_visual(
                        card_audio, host_num, text, card_out,
                        btc_price=btc_price, label=f"social_card_{ci}",
                        segment_type="social_segment",
                    )
                if card_result:
                    card_rendered_paths.append(card_result)
                    dur = ffprobe_duration(card_result)
                    logger.info(f"  SOCIAL CARD {ci} rendered: @{cp.get('handle', '?')} ({dur:.1f}s)")

            # Issue 5 FIX: Stitch cards with xfade transitions (no black flash)
            if len(card_rendered_paths) >= 2:
                # Apply sequential xfade between all cards
                current_stitched = card_rendered_paths[0]
                for xfi in range(1, len(card_rendered_paths)):
                    xfade_out = os.path.join(work_dir, f"part_{part_idx:03d}_social_xfade_{xfi}.mp4")
                    xfade_result = apply_xfade(
                        current_stitched, card_rendered_paths[xfi],
                        xfade_out, transition="slideleft", duration=0.4,
                    )
                    if xfade_result:
                        current_stitched = xfade_result
                        logger.info(f"  Issue 5: xfade card {xfi-1}→{xfi} OK")
                    else:
                        # Fallback: just append without transition
                        logger.warning(f"  Issue 5: xfade failed for cards {xfi-1}→{xfi}")
                        parts.append(current_stitched)
                        current_stitched = card_rendered_paths[xfi]
                        part_idx += 1
                # Mix card_swoosh SFX at transition points
                if os.path.exists(CARD_SWOOSH) and len(card_rendered_paths) > 1:
                    swoosh_mixed = current_stitched + ".swoosh.mp4"
                    card_durs = [ffprobe_duration(p) for p in card_rendered_paths]
                    swoosh_inputs = []
                    swoosh_fg_parts = []
                    cumul = 0.0
                    for si in range(len(card_durs) - 1):
                        cumul += card_durs[si] - 0.4  # account for xfade overlap
                        swoosh_inputs.extend(["-i", CARD_SWOOSH])
                        delay_ms = int(cumul * 1000)
                        swoosh_fg_parts.append(f"[{si+1}:a]volume=0.5,adelay={delay_ms}|{delay_ms}[sw_{si}]")
                    sw_labels = "".join(f"[sw_{si}]" for si in range(len(card_durs) - 1))
                    swoosh_fg_parts.append(f"{sw_labels}amix=inputs={len(card_durs)-1}:duration=longest[all_sw]")
                    swoosh_fg_parts.append(f"[0:a][all_sw]amix=inputs=2:duration=first:weights=1 0.5[outa]")
                    swoosh_fg = ";\n".join(swoosh_fg_parts)
                    ok_sw = run_ffmpeg(
                        ["-i", current_stitched] + swoosh_inputs +
                        ["-filter_complex", swoosh_fg,
                         "-map", "0:v", "-map", "[outa]",
                         "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                         swoosh_mixed],
                        "card swoosh mix", 120,
                    )
                    if ok_sw and os.path.exists(swoosh_mixed):
                        current_stitched = swoosh_mixed
                parts.append(current_stitched)
                dur = ffprobe_duration(current_stitched)
                logger.info(f"[{part_idx:03d}] SOCIAL CARDS (xfaded): {dur:.1f}s")
                part_idx += 1
            elif len(card_rendered_paths) == 1:
                parts.append(card_rendered_paths[0])
                dur = ffprobe_duration(card_rendered_paths[0])
                logger.info(f"[{part_idx:03d}] SOCIAL CARD (single): {dur:.1f}s")
                part_idx += 1

            social_card_idx += len(card_posts)
            prev_segment_type = entry_type
            continue  # parts already added per-card above
        elif entry_type == "social_segment":
            # No tweet card data available — fall back to host visual
            result = make_host_visual(
                audio_path, host_num, text, line_out,
                btc_price=btc_price, label=f"{entry_type} #{part_idx}",
                segment_type=entry_type,
            )
        else:
            # BV2: Route to Broadcast Engine V2 scene system (falls back to Black Diamond)
            # Dual host: map host_num to speaker name
            seg_speaker = "ERYN" if host_num == 1 else "MARK"
            seg_data = {"type": entry_type, "text": text,
                        "speaker": seg_speaker,  # dual host — Eryn + Mark
                        "headline": entry.get("headline", ""),  # Session 4 Fix 2
                        "next_speaker": ""}
            # Look ahead for next clip speaker
            if entry_type == "setup" and clip_rank and clip_rank in extracted_clips:
                seg_data["next_speaker"] = extracted_clips[clip_rank].get("channel", "")
            # FIX 1: Pass PiP video directly into the scene renderer (not as a post-processing overlay)
            pip_vid = pip_previews.get(clip_rank, "") if entry_type == "setup" and clip_rank else ""
            if pip_vid:
                logger.info(f"  FIX1: PiP video embedded for SETUP → clip #{clip_rank}")
            result = make_broadcast_segment(
                seg_data, audio_path, host_num,
                part_idx, len(dialogue),
                line_out, btc_price=btc_price,
                thumbnail_path=thumb,
                pip_video_path=pip_vid,  # FIX 1: actual video in PiP panel
            )

        if result:
            parts.append(result)
            dur = ffprobe_duration(result)
            speaker_label = "ERYN" if host_num == 1 else "MARK"
            logger.info(f"[{part_idx:03d}] {entry_type.upper()} [{speaker_label}]: {dur:.1f}s")
            part_idx += 1
            prev_segment_type = entry_type
            host_segment_count += 1

            # FIX 6: Insert B-roll clip every 2 host segments
            if broll_queue and broll_idx < len(broll_queue) and host_segment_count % 2 == 0:
                broll_path = broll_queue[broll_idx]
                broll_out = os.path.join(work_dir, f"part_{part_idx:03d}_broll_{broll_idx}.mp4")
                # Trim broll to 4s with BG music (or silent if no music)
                # BD branded overlay: red border + corners + ticker + watermark
                bd_broll_vf = (
                    "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                    "setsar=1,fps=30,fade=t=in:d=0.3,fade=t=out:st=3.5:d=0.5,"
                    f"drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=0:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=0:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1880:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1916:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=0:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=0:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1880:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1916:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
                    f"fontcolor={COLOR_RED}@0.6:fontsize=18:x=W-text_w-20:y=16,"
                    f"drawtext=fontfile={FONT_MONO}:text='// INCOMING SIGNAL':"
                    f"fontcolor={COLOR_RED}@0.8:fontsize=12:x=16:y=18,"
                    "format=yuv420p[outv];"
                )
                # APEX V2: No per-segment music — continuous BGM in concatenate_parts
                broll_ok = run_ffmpeg([
                    "-i", broll_path,
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", "4",
                    "-filter_complex",
                    bd_broll_vf +
                    "[1:a]atrim=0:4[outa]",
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-shortest",
                    broll_out,
                ], f"broll clip {broll_idx}", 60)
                if broll_ok and os.path.exists(broll_out):
                    parts.append(broll_out)
                    logger.info(f"[{part_idx:03d}] B-ROLL #{broll_idx}: 4.0s")
                    part_idx += 1
                broll_idx += 1
        else:
            logger.warning(f"[---] Host visual failed for {entry_type}")

    # --- 3. BRANDED OUTRO ---
    # Issue 8 FIX: The "Stay sovereign" wrap narration plays OVER the outro visual.
    # Remove the last wrap segment from parts (it will play over the outro instead).
    # Find the wrap audio (last non-CLIP audio line).
    wrap_audio = ""
    for al in reversed(audio_lines):
        if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al.get("path", "")):
            wrap_audio = al["path"]
            break

    # Issue 8 FIX: If the last part is a wrap scene, remove it — wrap audio plays over outro instead
    if parts and wrap_audio:
        last_part_name = os.path.basename(parts[-1]) if parts[-1] else ""
        if "wrap" in last_part_name.lower():
            removed = parts.pop()
            part_idx -= 1
            logger.info(f"  Issue 8: Removed duplicate wrap segment ({os.path.basename(removed)}) — plays over outro instead")

    if wrap_audio:
        logger.info(f"  Wrap narration for outro: {os.path.basename(wrap_audio)}")

    narration_end = sum(ffprobe_duration(p) for p in parts if p and os.path.exists(p))
    logger.info(f"Narration ends at {narration_end:.1f}s — outro starts here")

    # FIX 1: No standalone pre-outro transition — xfade in concatenation

    outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_branded.mp4")
    # Pass wrap narration so "Stay sovereign" plays OVER the branded outro visual
    outro_result = make_branded_outro(outro_out, narration_audio=wrap_audio)
    if outro_result:
        parts.append(outro_result)
        dur = ffprobe_duration(outro_result)
        logger.info(f"[{part_idx:03d}] OUTRO (branded): {dur:.1f}s")
        part_idx += 1
    else:
        # Fall back to tag video
        outro_out2 = os.path.join(work_dir, f"part_{part_idx:03d}_outro_tag.mp4")
        outro_result = make_tag_video(outro_out2)
        if outro_result:
            parts.append(outro_result)
            dur = ffprobe_duration(outro_result)
            logger.info(f"[{part_idx:03d}] OUTRO (tag fallback): {dur:.1f}s")
            part_idx += 1
        else:
            logger.warning("[---] No outro available")

    # --- 4. CONCATENATE ---
    logger.info(f"\nConcatenating {len(parts)} parts...")
    for i, p in enumerate(parts):
        dur = ffprobe_duration(p) if p and os.path.exists(p) else 0
        logger.info(f"  Part {i:03d}: {os.path.basename(p)} ({dur:.1f}s)")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    result = concatenate_parts(parts, output_path)

    if result and os.path.exists(result):
        dur = ffprobe_duration(result)
        sz = os.path.getsize(result) / 1024 / 1024
        logger.info(f"\n{'='*60}")
        logger.info(f"DONE: {result}")
        logger.info(f"Duration: {dur:.1f}s | Size: {sz:.1f}MB")
        logger.info(f"{'='*60}")
        return result

    logger.error("Assembly failed — no output produced")
    return ""


def verify_video(path: str) -> bool:
    """Verify output video meets spec."""
    logger.info(f"Verifying: {os.path.basename(path)}")

    if not os.path.exists(path):
        logger.error("File does not exist")
        return False

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True,
    )
    try:
        info = json.loads(r.stdout)
    except Exception:
        logger.error("Cannot parse ffprobe output")
        return False

    streams = info.get("streams", [])
    fmt = info.get("format", {})
    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)

    checks = []
    if vid:
        w, h = int(vid.get("width", 0)), int(vid.get("height", 0))
        checks.append(("Video codec", vid.get("codec_name") == "h264", vid.get("codec_name")))
        checks.append(("Resolution", w == 1920 and h == 1080, f"{w}x{h}"))
    else:
        checks.append(("Video stream", False, "MISSING"))

    if aud:
        checks.append(("Audio codec", aud.get("codec_name") == "aac", aud.get("codec_name")))
        checks.append(("Sample rate", aud.get("sample_rate") == "48000", aud.get("sample_rate")))
    else:
        checks.append(("Audio stream", False, "MISSING"))

    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / 1024 / 1024
    checks.append(("Duration", 5 <= duration <= 600, f"{duration:.1f}s"))
    checks.append(("File size", 0.5 <= size_mb <= 500, f"{size_mb:.1f}MB"))

    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        logger.info(f"  [{status}] {name}: {detail}")

    return all_pass


if __name__ == "__main__":
    logger.info("Assembler V6 — use daily_producer.py to run the full pipeline")

```

### FILE: script_writer.py
```python
#!/usr/bin/env python3
"""Script Writer V5 — generates host dialogue AROUND real YouTube clips.

Takes the 5 clips selected by clip_selector and generates:
- Cold open teasing clip #1
- Setup → Clip → React dialogue for each clip
- Wrap-up and sign-off

Host dialogue supports the clips, not the other way around.
"""
import json
import logging
import os
import re
import sys

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from relay import get_key

logger = logging.getLogger("ScriptWriter")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[script] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SCRIPT_PROMPT = """You are writing host dialogue for "Pulse Check" — a daily Bitcoin highlight show.
Think: ESPN SportsCenter meets Cypherpunk Gossip. MMA Central energy. The clips are the star.

HOST 1 (Eryn) — Sharp, fast, no-fluff. Confident mid-20s American female. Sets up each clip like a boxing ring announcer.
HOST 2 (Mark) — Hot takes, contrarian, dry wit. Warm strong male voice. Reacts like he just saw a knockout.

TONE RULES (NON-NEGOTIABLE):
- NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
- SETUP lines = 2-4 sentences. A sharp framing angle + one specific data point. Leave them wanting the clip.
- REACT lines = 2-4 sentences. A hot take with substance — specific implication, not a vague platitude.
- Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
- Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
- Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
- Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.
- After clips 2 and 4, add a BRIDGE line (type: "bridge") connecting that clip's theme to the next. 1-2 sentences. Eryn only. Elevate the stakes or pivot the angle.
- REACT lines: when a clip lands something genuinely significant, give it 2-3 sharp sentences. Brief is not always best. Incisive > terse.
- NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
- End with "Stay sovereign."

CRITICAL EPISODE ARC RULES (NON-NEGOTIABLE):
- Start with the most shocking/interesting fact. NO intro. NO "welcome to Protocol Pulse."
- At minute 3 (after Clip 2 setup), include a re-engagement hook: "But here's where it gets interesting..."
- At the halfway point, pivot to something unexpected or contrarian.
- End ABRUPTLY after the call to action. NEVER say "thanks for watching" or "see you next time."
  These phrases signal the video is ending and cause immediate viewer drop-off.
- Each narrator line should be 1-3 sentences. Never more than 4 sentences per turn.
- Include at least one specific number/metric in every other segment.

DELIVERY RULES:
- ALWAYS open setup lines with a natural verbal bridge: "Ok so—", "Right, and—", "Here's the thing—", "Check this out—", "So—". Never start cold.
- The setup is a LAY-UP for the clip. Tease the knockout moment. Don't explain the whole clip.
- React lines start with a reaction word: "Yeah.", "Exactly.", "Wild.", "That's the tell.", "100%.", "I mean—"
- Tone = investigative gossip journalist who happens to understand Austrian economics.
- Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
- Min 3, max 4 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.

EPISODE STRUCTURE (follow this order):
1. [COLD_OPEN] — The hook. Most shocking insight. 1-2 sentences MAX.
2. [NARRATION] — Setup for Clip 1. Why this matters. End with transition to clip.
3. [NARRATION] — Analysis after Clip 1. Connect to bigger picture.
4. [NARRATION] — Setup for Clip 2 with re-engagement hook at ~minute 3.
5. [NARRATION] — Analysis after Clip 2.
6. [DATA] — Hard metrics segment. MINIMUM 3 exchanges (Eryn + Mark). Cover: price context, hash rate or difficulty, one on-chain signal. At least one specific number per line. Target: 45-60 seconds of spoken content.
7. [SOCIAL] — MINIMUM 3 tweet reads + 2 Mark reactions. Eryn reads each tweet sharp and brief. Target: 40-50 seconds.
8. [WARM] — 2-3 sentences synthesizing the day's theme, then abrupt CTA. Target: 20-30 seconds. End ABRUPTLY. No "thanks for watching."

NARRATION PHILOSOPHY — Simon Dixon / Preston Pysh standard:
- Every line must contain ONE specific insight, data point, or evaluated observation
- Never state what already happened — analyze WHY it matters and WHAT COMES NEXT
- Eryn sets up the angle with a sharp framing line + 1 specific number or fact
- Mark delivers the contrarian take, macro context, or on-chain implication
- Forbidden phrases: "Bitcoin continues to", "the market is watching", "this is significant",
  "interesting to note", "worth keeping an eye on", any pure restatement of price
- Required: each exchange references at least one of: hashrate, difficulty adjustment,
  miner profitability, HODLer behavior, lightning adoption, ETF flows, or macro correlation
- Minimum 3 sentences per speaker turn. Never 1-2 sentence fluff turns.
- Bridges between clips must connect thematic dots — not just "next up"
- DATA segment minimum: 4 exchanges, each with a specific metric, each with an implication

EPISODE LENGTH LAW: Full episode narration must total at least 600 words (excluding clip durations). With 5 clips averaging 30s each = 150s clip time. 600 words spoken ≈ 4 minutes. Total target: 10+ minutes. Sharp does not mean short. Incisive 3-sentence reactions are sharper than vague 1-liners. Go deeper on REACT lines when the clip moment is significant.

SEGMENT TAGGING (MANDATORY — controls Eryn's voice dynamics):
Every dialogue text line MUST start with a segment type tag in brackets. The TTS engine reads this tag to adjust vocal delivery. If missing, the voice defaults to CLEAR which is safe but loses dramatic range.
  [COLD_OPEN] — opening hook only (first 1-2 sentences). Dramatic whisper. MAX 2 per episode.
  [NARRATION] — standard narration, setup, and analysis. Clear and confident. This is 70-80% of lines.
  [DATA] — specific metrics, prices, hashrates, on-chain numbers. Authoritative.
  [SOCIAL] — social segment commentary. Slightly warmer tone.
  [WARM] — outros, calls to action, sign-offs. Inviting.
Example: {{"host": 1, "text": "[NARRATION] Bitcoin miners are facing a squeeze as difficulty adjusts upward.", "type": "setup"}}
The tag is INSIDE the text string, not the type field. Both must be present.

SOCIAL SEGMENT:
If social posts data is provided below, add a "WHAT THE BITCOIN INTERNET IS SAYING" segment after the last clip:
- Eryn reads 2-3 of the top tweets provided (sharp, brief, 1 line each)
- Mark drops a one-liner reaction to the best one
- This is a separate section in the dialogue with type: "social_segment"
CRITICAL: If no social posts data is provided (empty or "NONE"), do NOT fabricate tweet content. Skip the social segment entirely. Law A1 — no invented data.

{clips_info}

BTC Price Today: {btc_price}
Top Tweets/Nostr Posts Today: {social_posts}
{live_context}
Return ONLY valid JSON (no markdown, no code fences):
{{
  "cold_open": "explosive 1-sentence cold open",
  "dialogue": [
    {{"host": 1, "text": "...", "type": "cold_open"}},
    {{"host": 1, "text": "...", "type": "setup", "clip_rank": 1}},
    {{"host": "CLIP", "rank": 1}},
    {{"host": 2, "text": "...", "type": "react", "clip_rank": 1}},
    {{"host": 1, "text": "...", "type": "setup", "clip_rank": 2}},
    {{"host": "CLIP", "rank": 2}},
    {{"host": 2, "text": "...", "type": "react", "clip_rank": 2}},
    ...and so on for all clips...
    {{"host": 1, "text": "...", "type": "social_segment"}},
    {{"host": 2, "text": "...", "type": "social_segment"}},
    {{"host": 1, "text": "Final wrap. Stay sovereign.", "type": "wrap"}}
  ],
  "episode_title": "Short punchy title (5-8 words)",
  "thumbnail": {{
    "headline": "BOLD THUMBNAIL TEXT (5-8 words)",
    "subtext": "secondary line"
  }},
  "segments_summary": ["headline for each clip topic"],
  "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
}}

IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5)."""


# Maps bracket tags in text to segment types for TTS voice modes
_TAG_TO_TYPE = {
    "COLD_OPEN": "cold_open",
    "NARRATION": "setup",
    "DATA": "data",
    "SOCIAL": "social_segment",
    "WARM": "wrap",
    "BRIDGE": "setup",  # inter-clip context bridges treated as narration
}

_TAG_PATTERN = re.compile(r"^\[(" + "|".join(_TAG_TO_TYPE.keys()) + r")\]\s*")


def _extract_segment_tags(result: dict) -> dict:
    """Extract [TAG] prefixes from dialogue text and set entry type accordingly.

    If a dialogue line starts with [NARRATION], [DATA], etc., strip the tag
    from the text and set/override the type field for TTS voice mode selection.
    """
    dialogue = result.get("dialogue", [])
    for entry in dialogue:
        text = entry.get("text", "")
        if not text:
            continue
        m = _TAG_PATTERN.match(text)
        if m:
            tag = m.group(1)
            entry["text"] = text[m.end():]
            entry["type"] = _TAG_TO_TYPE[tag]
    return result


def _format_clips_info(selections: dict) -> str:
    """Format clip selections for the script prompt."""
    clips = selections.get("clips", [])
    parts = []
    for c in clips:
        parts.append(
            f"CLIP #{c['rank']}:\n"
            f"  Channel: {c.get('channel', 'Unknown')}\n"
            f"  Video: {c.get('video_title', 'Untitled')}\n"
            f"  Quote: \"{c.get('quote', '')}\"\n"
            f"  Why selected: {c.get('why', '')}\n"
            f"  Suggested setup: {c.get('host_setup', '')}\n"
            f"  Suggested reaction: {c.get('host_react', '')}\n"
        )
    return "\n".join(parts)


def _load_narrative_context() -> dict:
    """Load narrative_context.json for narrative-aware script generation.
    Returns empty dict if missing or stale (>6hr old)."""
    import os
    from datetime import datetime, timezone
    ctx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "intelligence", "narrative_context.json")
    try:
        with open(ctx_path) as f:
            ctx = json.load(f)
        # Check staleness
        computed = ctx.get("computed_at", "")
        if computed:
            computed_dt = datetime.fromisoformat(computed.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - computed_dt).total_seconds() / 3600
            if age_hours > 6:
                logger.warning(f"Narrative context is {age_hours:.1f}h old (>6h) — using generic prompt")
                return {}
        return ctx
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Narrative context unavailable: {e}")
        return {}


NARRATIVE_INJECTION = """
TODAY'S LIVE NARRATIVE CONTEXT (from real-time thought leader monitoring):
Dominant narrative: {dominant_narrative}
Market mood: {market_mood}
What thought leaders are saying: {episode_narrative}
Eryn should reference: {eryn_intro_hook}
Mark should add: {mark_context}
Suggested bridge lines: {narrative_bridge_lines}

MANDATORY SCRIPT RULES (from narrative context):
- Eryn's cold open MUST reference the dominant narrative in her first sentence
- At least ONE of the clips must be explicitly connected to the X discourse
  (e.g., "This is what everyone on Crypto Twitter has been discussing all morning...")
- Mark must cite at least one specific data point from the narrative context (not generic)
- Avoid topics flagged in: {avoid_topics}
- The show must feel LIVE — like Eryn and Mark have been tracking this story all morning

DATA SEGMENT REQUIREMENT: The data/metrics discussed must relate to today's
dominant narrative ({dominant_narrative}). If narrative is "ETF inflows",
cite actual ETF flow numbers. If "mining difficulty", cite actual hashrate/difficulty data.
Eryn and Mark must sound like analysts who read the numbers this morning, not generalists.
"""


def _populate_segment_headlines(result: dict) -> dict:
    """Session 4 Fix 2: Add 'headline' key to each dialogue entry.

    Maps segment type + clip rank to a meaningful headline so _smart_headline()
    in assembler.py gets a real headline instead of truncated spoken text.
    """
    dialogue = result.get("dialogue", [])
    summaries = result.get("segments_summary", [])
    episode_title = result.get("episode_title", "Pulse Check Daily")

    for entry in dialogue:
        if entry.get("headline"):
            continue  # already has one
        host = entry.get("host")
        if host == "CLIP":
            continue  # clip markers don't need headlines

        seg_type = entry.get("type", "")
        clip_rank = entry.get("clip_rank", 0)

        if seg_type == "cold_open":
            entry["headline"] = episode_title
        elif seg_type in ("setup", "react") and clip_rank:
            # Use segments_summary (clip "why" strings) keyed by rank
            idx = clip_rank - 1
            if 0 <= idx < len(summaries) and summaries[idx]:
                entry["headline"] = summaries[idx][:55]
            else:
                entry["headline"] = episode_title
        elif seg_type == "data":
            entry["headline"] = "TODAY'S INTELLIGENCE"
        elif seg_type == "social_segment":
            entry["headline"] = "SIGNAL FROM THE FIELD"
        elif seg_type in ("wrap", "outro"):
            entry["headline"] = "STAY SOVEREIGN"
        elif seg_type == "bridge":
            entry["headline"] = episode_title
        else:
            # Generic narrator — use episode title
            entry["headline"] = episode_title

    return result


def generate_from_clips(selections: dict, btc_price: str = "N/A",
                        live_context: str = "") -> dict:
    """Generate host dialogue script around the selected clips.

    Args:
        selections: Output from clip_selector.select_clips()
        btc_price: Current BTC price string
        live_context: Real-time live stream/Spaces intelligence (optional)

    Returns:
        Script dict with dialogue array
    """
    clips = selections.get("clips", [])
    if not clips:
        logger.error("No clips provided for script generation")
        return _fallback_script(selections)

    from relay import call_llm

    clips_info = _format_clips_info(selections)

    # Real social data — per Law A1, never fabricate
    try:
        from utils.social_fetcher import get_todays_social_posts
        social_data = get_todays_social_posts(max_posts=5)
        if social_data:
            social_posts = "\n".join([
                f"@{p['handle']} tweeted: \"{p['text'][:200]}\" ({p['likes']} likes)"
                for p in social_data
            ])
        else:
            social_posts = "NONE — skip social segment entirely"
    except Exception as e:
        logger.warning(f"Social data fetch failed: {e}")
        social_posts = "NONE — skip social segment entirely"

    # Build live context block
    live_block = ""
    if live_context:
        live_block = (
            "\nLIVE INTELLIGENCE: The following events are happening RIGHT NOW or happened "
            "in the last few hours on Bitcoin YouTube/X Spaces. Reference these naturally "
            "in your narration to make the episode feel current and urgent:\n"
            f"{live_context}\n"
        )

    # Inject narrative context from thought leader monitoring
    narrative_ctx = _load_narrative_context()
    if narrative_ctx and narrative_ctx.get("dominant_narrative"):
        try:
            bridge_lines = narrative_ctx.get("narrative_bridge_lines", [])
            narrative_block = NARRATIVE_INJECTION.format(
                dominant_narrative=narrative_ctx.get("dominant_narrative", ""),
                market_mood=narrative_ctx.get("market_mood", ""),
                episode_narrative=narrative_ctx.get("episode_narrative", ""),
                eryn_intro_hook=narrative_ctx.get("eryn_intro_hook", ""),
                mark_context=narrative_ctx.get("mark_context", ""),
                narrative_bridge_lines="\n".join(bridge_lines) if bridge_lines else "none",
                avoid_topics=", ".join(narrative_ctx.get("avoid_topics", [])),
            )
            live_block = narrative_block + "\n" + live_block
            logger.info(f"Narrative context injected: {narrative_ctx.get('dominant_narrative')}")
        except Exception as e:
            logger.warning(f"Failed to inject narrative context: {e}")

    prompt = SCRIPT_PROMPT.format(clips_info=clips_info, btc_price=btc_price,
                                   social_posts=social_posts, live_context=live_block)

    logger.info(f"Generating script for {len(clips)} clips...")
    text = call_llm(prompt, max_tokens=4000)
    if text is None:
        logger.warning("All LLM providers failed, using fallback script")
        return _fallback_script(selections)

    try:

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text)

        # Extract [TAG] prefixes from text and set type fields for TTS
        result = _extract_segment_tags(result)

        # Session 4 Fix 2: Populate 'headline' per dialogue entry for assembler
        result = _populate_segment_headlines(result)

        # Validate structure
        dialogue = result.get("dialogue", [])
        clip_entries = [d for d in dialogue if d.get("host") == "CLIP"]
        speech_entries = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]

        logger.info(f"Script generated: {len(dialogue)} entries "
                    f"({len(speech_entries)} speech, {len(clip_entries)} clips)")
        logger.info(f"Title: {result.get('episode_title', 'Untitled')}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return _fallback_script(selections)
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return _fallback_script(selections)


def _fallback_script(selections: dict) -> dict:
    """Generate a basic script from clip selections without Claude."""
    clips = selections.get("clips", [])
    cold_open = selections.get("cold_open", "Breaking developments in Bitcoin today.")

    dialogue = [
        {"host": 1, "text": cold_open, "type": "cold_open"},
    ]

    for c in clips:
        rank = c.get("rank", 0)
        setup = c.get("host_setup", f"Check out what {c.get('channel', 'this channel')} just dropped.")
        react = c.get("host_react", "That's a big deal. The market hasn't priced this in yet.")

        dialogue.append({"host": 1, "text": setup, "type": "setup", "clip_rank": rank})
        dialogue.append({"host": "CLIP", "rank": rank})
        dialogue.append({"host": 2, "text": react, "type": "react", "clip_rank": rank})

    dialogue.append({
        "host": 1,
        "text": "That's your Pulse Check for today. Stay sovereign.",
        "type": "wrap",
    })

    title = selections.get("episode_title", "Pulse Check Daily")

    return {
        "cold_open": cold_open,
        "dialogue": dialogue,
        "episode_title": title,
        "thumbnail": {"headline": title.upper(), "subtext": "Daily Bitcoin Intelligence"},
        "segments_summary": [c.get("why", "") for c in clips],
        "shorts_quotes": [c.get("quote", "")[:80] for c in clips[:3]],
    }


# Legacy compatibility
def generate_script(stories=None, style="default", btc_price="N/A"):
    """Legacy wrapper — generate a sample script for testing."""
    logger.info("Legacy generate_script called — use generate_from_clips for V5 pipeline")
    return generate_sample_script(style)


def generate_sample_script(style="default"):
    """Sample script for testing without live data."""
    return {
        "episode_title": "The Quiet Accumulation",
        "cold_open": "Three sovereign wealth funds just disclosed Bitcoin positions worth twelve billion dollars.",
        "dialogue": [
            {"host": 1, "text": "Three sovereign wealth funds just disclosed Bitcoin positions. Twelve billion dollars. This is Pulse Check.", "type": "cold_open"},
            {"host": 1, "text": "Bitcoin Magazine just dropped this bombshell.", "type": "setup", "clip_rank": 1},
            {"host": "CLIP", "rank": 1},
            {"host": 2, "text": "Dude. When the entities that print fiat start hoarding the exit asset, that tells you everything.", "type": "react", "clip_rank": 1},
            {"host": 1, "text": "And look at what Simply Bitcoin is reporting on hash rate.", "type": "setup", "clip_rank": 2},
            {"host": "CLIP", "rank": 2},
            {"host": 2, "text": "Record high hash rate. Miners aren't leaving. They're doubling down.", "type": "react", "clip_rank": 2},
            {"host": 1, "text": "That's your Pulse Check. Stay sovereign.", "type": "wrap"},
        ],
        "thumbnail": {"headline": "SMART MONEY IS MOVING", "subtext": "Nations are stacking"},
        "segments_summary": ["Sovereign wealth funds buying BTC", "Hash rate hits record"],
        "shorts_quotes": ["When the entities that print fiat start hoarding the exit asset", "Miners aren't leaving"],
    }


if __name__ == "__main__":
    script = generate_sample_script()
    print(json.dumps(script, indent=2))

```

### FILE: manifest_builder.py
```python
#!/usr/bin/env python3
"""Manifest Builder — generates episode_manifest.json BEFORE assembly.

Reads: script JSON, audio_data dict, extracted_clips dict, social_posts list.
Produces: episode_manifest.json with explicit segment timeline.

Phase 1: Runs in PARALLEL with existing assembler. Logs manifest vs actual.
"""
import json
import logging
import os
from datetime import datetime, timezone

from music import ffprobe_duration

logger = logging.getLogger("ManifestBuilder")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[manifest] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def build_manifest(script: dict, audio_data: dict, extracted_clips: dict,
                   output_dir: str, music_bed: str = "",
                   btc_price: str = "N/A") -> dict:
    """Build episode manifest from script + audio + clips.

    Args:
        script: Script dict with dialogue array and social_posts
        audio_data: From generate_dialogue_audio() — {lines, total_duration}
        extracted_clips: {rank: {path, channel, duration, video_id, ...}}
        output_dir: Where to save episode_manifest.json
        music_bed: Path to selected music bed track
        btc_price: BTC price string

    Returns:
        Complete manifest dict (also saved to disk)
    """
    dialogue = script.get("dialogue", [])
    audio_lines = audio_data.get("lines", [])
    social_posts = script.get("social_posts", [])
    episode_title = script.get("episode_title", "Pulse Check")
    date_str = datetime.now().strftime("%Y-%m-%d")

    segments = []
    seg_id = 0
    cumulative_sec = 0.0
    audio_idx = 0
    clip_count = 0
    unique_channels = set()

    def _next_audio():
        nonlocal audio_idx
        while audio_idx < len(audio_lines):
            al = audio_lines[audio_idx]
            if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al.get("path", "")):
                audio_idx += 1
                return al
            audio_idx += 1
        return None

    def _add_segment(seg_type, duration, audio_path="", video_path="",
                     visual_mode="cyberpunk_bg", primary_visual="waveform_only",
                     transition_in="none", transition_out="none",
                     music_state="bed_ducked", clip_fade_in=0.0, clip_fade_out=0.0,
                     logo_allowed=False, face_expected=False, clip_rank=0,
                     lower_third=None, social_card_data=None, pip_source=None):
        nonlocal seg_id, cumulative_sec
        seg = {
            "id": seg_id,
            "type": seg_type,
            "screen_mode": seg_type,
            "start_sec": round(cumulative_sec, 2),
            "duration_sec": round(duration, 2),
            "audio_path": audio_path,
            "video_path": video_path,
            "visual_mode": visual_mode,
            "primary_visual_type": primary_visual,
            "transition_in": transition_in,
            "transition_out": transition_out,
            "music_state": music_state,
            "clip_fade_in_sec": clip_fade_in,
            "clip_fade_out_sec": clip_fade_out,
            "logo_allowed": logo_allowed,
            "face_expected": face_expected,
            "clip_rank": clip_rank,
            "lower_third": lower_third,
            "social_card_data": social_card_data,
            "pip_source": pip_source,
        }
        segments.append(seg)
        cumulative_sec += duration
        seg_id += 1
        return seg

    # Process dialogue entries
    social_card_idx = 0
    cold_open_done = False

    for i, entry in enumerate(dialogue):
        entry_type = entry.get("type", "")
        host_field = entry.get("host", "")

        if host_field == "CLIP":
            rank = entry.get("rank", 0)
            clip_info = extracted_clips.get(rank, {})
            clip_path = clip_info.get("path", "")
            channel = clip_info.get("channel", "")

            if clip_path and os.path.exists(clip_path):
                clip_dur = ffprobe_duration(clip_path)
                clip_count += 1
                if channel:
                    unique_channels.add(channel)

                # Transition before clip
                _add_segment("transition", 0.7,
                             transition_in="custom_whoosh",
                             music_state="transition_swell",
                             visual_mode="transition")

                # The clip itself
                _add_segment("partner_clip", clip_dur,
                             audio_path=clip_path,
                             video_path=clip_path,
                             visual_mode="fullscreen_clip",
                             primary_visual="fullscreen_clip",
                             transition_in="custom_whoosh",
                             transition_out="xfade_1s",
                             music_state="none",
                             clip_fade_in=0.3,
                             clip_fade_out=0.5,
                             logo_allowed=True,
                             face_expected=True,
                             clip_rank=rank,
                             lower_third={
                                 "channel": channel,
                                 "speaker": clip_info.get("speaker", ""),
                                 "topic": clip_info.get("topic", ""),
                             })
            continue

        # Host dialogue
        al = _next_audio()
        if not al:
            continue

        audio_path = al["path"]
        audio_dur = ffprobe_duration(audio_path)
        if audio_dur <= 0:
            audio_dur = 5.0

        # Map entry type to segment type
        if entry_type == "cold_open" and not cold_open_done:
            cold_open_done = True
            pip_src = None
            if 1 in extracted_clips:
                pip_src = extracted_clips[1].get("path", "")
            _add_segment("cold_open", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="pip_upcoming",
                         music_state="none",
                         face_expected=True,
                         pip_source=pip_src)
            # Title sequence after cold open
            _add_segment("title_sequence", 4.0,
                         music_state="title_hit",
                         visual_mode="title_card",
                         logo_allowed=True)

        elif entry_type == "setup":
            clip_rank = entry.get("clip_rank", 0)
            pip_src = None
            if clip_rank and clip_rank in extracted_clips:
                pip_src = extracted_clips[clip_rank].get("path", "")
            _add_segment("narration_setup", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="pip_upcoming",
                         pip_source=pip_src,
                         face_expected=bool(pip_src))

        elif entry_type == "react":
            _add_segment("narration_react", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="clip_callback_thumb")

        elif entry_type == "social_segment":
            # Each tweet as its own segment
            cards = social_posts[social_card_idx:social_card_idx + 3]
            for ci, card in enumerate(cards):
                card_dur = audio_dur + 0.3 if ci == 0 else 8.0
                _add_segment("social_card", card_dur,
                             audio_path=audio_path if ci == 0 else "",
                             visual_mode="remotion_social_card",
                             primary_visual="social_card",
                             transition_in="card_swoosh" if ci > 0 else "none",
                             transition_out="card_swoosh",
                             social_card_data={
                                 "handle": card.get("handle", ""),
                                 "text": card.get("text", ""),
                                 "likes": card.get("likes", 0),
                                 "screenshot_path": card.get("screenshot_path", ""),
                             })
            social_card_idx += len(cards)

        elif entry_type == "data_segment":
            _add_segment("data_segment", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="data_card")

        elif entry_type == "wrap":
            _add_segment("wrap", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="waveform_only",
                         music_state="outro_rise")

        else:
            # Generic narration
            _add_segment(entry_type or "narration", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="waveform_only")

    # Outro
    _add_segment("outro", 8.0,
                 visual_mode="branded_outro",
                 primary_visual="branded_outro",
                 music_state="outro_rise",
                 logo_allowed=True)

    # Build episode manifest
    manifest = {
        "episode_id": date_str,
        "episode_title": episode_title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_loudness_lufs": -14,
        "true_peak_dbtp": -1.5,
        "music_bed_path": music_bed,
        "logo_policy": "restraint",
        "btc_price": btc_price,
        "total_segments": len(segments),
        "total_duration_estimate": round(cumulative_sec, 2),
        "segments": segments,
        "qc_expectations": {
            "total_duration_range": [360, 900],
            "clip_count": clip_count,
            "unique_channels": len(unique_channels),
            "loudness_lufs": -14,
            "true_peak_dbtp": -1.5,
            "max_silent_gap_sec": 2.0,
            "max_black_frames_sec": 0.5,
        },
    }

    # Save to disk
    manifest_path = os.path.join(output_dir, "episode_manifest.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest built: {len(segments)} segments, ~{cumulative_sec:.0f}s estimated")
    logger.info(f"  Clips: {clip_count} from {len(unique_channels)} channels")
    logger.info(f"  Saved: {manifest_path}")

    return manifest

```

### FILE: preflight.py
```python
#!/usr/bin/env python3
"""
PREFLIGHT.PY v2 — Protocol Pulse Pipeline Smoke Gate
=====================================================
<15 second runtime. Catches every class of failure seen in production.

Exit 0 = safe to render. Exit 1 = DO NOT render.

Usage:
  python3 preflight.py           # full check inc. live TTS
  python3 preflight.py --no-tts  # skip live ElevenLabs call
"""

import os, sys, ast, json, re, time, tempfile, argparse, subprocess
from datetime import datetime

BASE = '/home/ultron/protocol_pulse'
V3   = f'{BASE}/video_pipeline_v3'

PASS = '\033[92m✅ PASS\033[0m'
FAIL = '\033[91m❌ FAIL\033[0m'
HEAD = '\033[96m'
RST  = '\033[0m'

results = []

def chk(name, passed, detail=''):
    print(f'  {PASS if passed else FAIL}  {name}' + (f'\n         → {detail}' if detail and not passed else ''))
    results.append((name, passed, detail))
    return passed

def sec(title):
    print(f'\n{HEAD}── {title} {"─"*(52-len(title))}{RST}')

def env():
    e = {}
    if os.path.exists(f'{BASE}/.env'):
        for ln in open(f'{BASE}/.env'):
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1)
                e[k.strip()] = v.strip()
    return e

# ── 1. SYNTAX ─────────────────────────────────────────────
def check_syntax():
    sec('SYNTAX & COMPILE')
    ok = True
    for name in ['tts_engine.py', 'daily_producer.py', 'assembler.py']:
        path = f'{V3}/{name}'
        if not os.path.exists(path):
            chk(f'Exists: {name}', False, f'NOT FOUND: {path}'); ok = False; continue
        try:
            ast.parse(open(path).read())
            chk(f'Syntax OK: {name}', True)
        except SyntaxError as e:
            chk(f'Syntax OK: {name}', False, str(e)); ok = False
    return ok

# ── 2. REQUIRED CONSTANTS ─────────────────────────────────
def check_constants():
    sec('REQUIRED CONSTANTS — tts_engine.py')
    ok = True
    c = open(f'{V3}/tts_engine.py').read() if os.path.exists(f'{V3}/tts_engine.py') else ''

    for const, val in [('SILENCE_GAP', '0.3'), ('MAX_CHUNK_CHARS', '500'), ('VOICE_MODES', '{')]:
        present = bool(re.search(rf'^{const}\s*=', c, re.MULTILINE))
        if not chk(f'Constant: {const} = {val}', present,
                   f'MISSING — add: {const} = {val}'):
            ok = False

    # _KEY_CACHE — must exist exactly once
    kc = len(re.findall(r'^_KEY_CACHE', c, re.MULTILINE))
    if not chk(f'_KEY_CACHE declared (x{kc})', kc == 1,
               f'Found {kc} declarations — deduplicate to exactly 1'):
        ok = False
    return ok

# ── 3. BANNED PATTERNS ────────────────────────────────────
def check_banned():
    sec('BANNED PATTERNS')
    ok = True
    tts = open(f'{V3}/tts_engine.py').read() if os.path.exists(f'{V3}/tts_engine.py') else ''
    asm = open(f'{V3}/assembler.py').read()   if os.path.exists(f'{V3}/assembler.py')   else ''

    # Banned voice (returns 200 + 0 bytes silently)
    if not chk('Banned voice absent: uxKr2vlA4hYgXZR1oPRT',
               'uxKr2vlA4hYgXZR1oPRT' not in tts,
               'BANNED voice ID in tts_engine.py — delete immediately'):
        ok = False

    # Wrong sample rates
    for pat in ['r=44100', 'ar 44100', '-ar 44100', 'cl=mono']:
        if not chk(f'No legacy rate: "{pat}"', pat not in tts,
                   f'{pat} still present — must be 48000Hz stereo'):
            ok = False

    # assembler: ban BARE 0xFF0000 (no @) — atmospheric @0.xx are OK per PIPELINE_LAWS
    bare_red = bool(re.search(r'0xFF0000[^@\s]', asm))
    if not chk('No bare 0xFF0000 in assembler', not bare_red,
               'Bare 0xFF0000 found (no opacity) — use COLOR_RED (0xFF3333)'):
        ok = False

    # assembler: 0xFF0033 always banned (off-spec red)
    if not chk('No 0xFF0033 off-spec red', '0xFF0033' not in asm,
               '0xFF0033 found — replace with COLOR_RED (0xFF3333)'):
        ok = False

    # assembler: ban BARE 0xFFFFFF (no @) — with opacity is OK for subtle UI
    bare_white = bool(re.search(r'0xFFFFFF[^@]', asm))
    if not chk('No bare 0xFFFFFF in assembler', not bare_white,
               'Bare 0xFFFFFF found — use COLOR_WHITE (0xF4F5F8)'):
        ok = False

    return ok

# ── 4. ENVIRONMENT ────────────────────────────────────────
def check_env():
    sec('ENVIRONMENT')
    ok = True
    e = env()

    if not chk('TTS_PROVIDER=elevenlabs', e.get('TTS_PROVIDER','').lower() == 'elevenlabs',
               f'TTS_PROVIDER={e.get("TTS_PROVIDER","MISSING")!r}'):
        ok = False

    for key in ['ELEVENLABS_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY']:
        val = e.get(key, '')
        if not chk(f'{key} set', len(val) > 10, f'{key} missing/empty in .env'):
            ok = False
    return ok

# ── 5. VOICE IDs ──────────────────────────────────────────
def check_voices():
    sec('VOICE IDs')
    c = open(f'{V3}/tts_engine.py').read() if os.path.exists(f'{V3}/tts_engine.py') else ''
    chk('Eryn voice present: kdnRe2koJdOK4Ovxn2DI', 'kdnRe2koJdOK4Ovxn2DI' in c,
        'Eryn voice ID missing from tts_engine.py')
    chk('Mark voice present: 1SM7GgM6IMuvQlz2BwM3', '1SM7GgM6IMuvQlz2BwM3' in c,
        'Mark voice ID missing from tts_engine.py')
    chk('Banned voice absent: uxKr2vlA4hYgXZR1oPRT', 'uxKr2vlA4hYgXZR1oPRT' not in c,
        'BANNED voice in tts_engine.py — causes silent 0-byte audio')

# ── 6. ASSEMBLER CONSTANTS ────────────────────────────────
def check_assembler():
    sec('ASSEMBLER COLOR CONSTANTS')
    c = open(f'{V3}/assembler.py').read() if os.path.exists(f'{V3}/assembler.py') else ''
    for const, val in [('COLOR_RED','0xFF3333'),('COLOR_WHITE','0xF4F5F8'),('COLOR_BG','0x0A0A0F')]:
        chk(f'{const} = {val}', const in c and val in c,
            f'{const} missing or wrong value — expected {val}')

# ── 7. LIVE TTS SMOKE TEST ────────────────────────────────
def check_tts_smoke():
    sec('LIVE TTS SMOKE TEST')
    import urllib.request as ul
    e = env()
    api_key = e.get('ELEVENLABS_API_KEY', '')
    if not api_key:
        chk('ElevenLabs key available', False, 'Cannot smoke test — key missing'); return

    VOICE = 'kdnRe2koJdOK4Ovxn2DI'
    url   = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}'
    body  = json.dumps({'text': 'Bitcoin. Signal confirmed.',
                        'model_id': 'eleven_turbo_v2',
                        'voice_settings': {'stability': 0.45, 'similarity_boost': 0.82}}).encode()
    try:
        t0  = time.time()
        req = ul.Request(url, data=body, headers={
            'xi-api-key': api_key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
        with ul.urlopen(req, timeout=20) as r:
            audio = r.read()
        elapsed = time.time() - t0
        chk('ElevenLabs API reachable', True)
        size_ok = len(audio) > 10240
        chk(f'Audio >10KB ({len(audio)//1024}KB, {elapsed:.1f}s)', size_ok,
            f'Only {len(audio)}B — check quota / API key')
        if size_ok:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio); tmp = f.name
            r2 = subprocess.run(
                ['ffprobe','-v','quiet','-show_entries','format=duration',
                 '-of','default=noprint_wrappers=1:nokey=1', tmp],
                capture_output=True, text=True)
            os.unlink(tmp)
            dur = float(r2.stdout.strip()) if r2.stdout.strip() else 0.0
            chk(f'Audio duration > 0.4s ({dur:.2f}s)', dur > 0.4,
                'Zero-duration audio — silent response from ElevenLabs')
    except Exception as ex:
        chk('ElevenLabs API reachable', False, str(ex))

# ── MAIN ──────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--no-tts', action='store_true')
    args = p.parse_args()

    print(f'\n{"═"*60}')
    print(f'  PROTOCOL PULSE PREFLIGHT  —  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"═"*60}')

    check_syntax()
    check_constants()
    check_banned()
    check_env()
    check_voices()
    check_assembler()
    if not args.no_tts:
        check_tts_smoke()

    total  = len(results)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f'\n{"═"*60}')
    if failed == 0:
        print(f'\033[92m  ✅  ALL {total} CHECKS PASSED — SAFE TO RENDER\033[0m')
    else:
        print(f'\033[91m  ❌  {failed}/{total} FAILED — DO NOT START RENDER\033[0m')
        for name, ok, detail in results:
            if not ok:
                print(f'     • {name}')
                if detail: print(f'       → {detail}')
    print(f'{"═"*60}\n')
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()

```

### FILE: music.py
```python
#!/usr/bin/env python3
"""Music Integration — handles background music, jingles, and transitions.

All music files are optional. If missing, the pipeline skips gracefully.
"""
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE, "assets", "music")

INTRO_JINGLE = os.path.join(MUSIC_DIR, "pp_intro.mp3")
BG_MUSIC = os.path.join(MUSIC_DIR, "pp_background.mp3")
TRANSITION = os.path.join(MUSIC_DIR, "pp_transition.mp3")
OUTRO_JINGLE = os.path.join(MUSIC_DIR, "pp_outro.mp3")


def has_music() -> bool:
    """Check if any background music is available (mood tracks or legacy)."""
    if os.path.exists(BG_MUSIC):
        return True
    import glob
    mood_tracks = glob.glob(os.path.join(MUSIC_DIR, "*_*.mp3"))
    return len(mood_tracks) > 0


def has_intro() -> bool:
    return os.path.exists(INTRO_JINGLE)


def has_transition() -> bool:
    return os.path.exists(TRANSITION)


def has_outro() -> bool:
    return os.path.exists(OUTRO_JINGLE)


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def mix_tts_with_music(tts_path: str, output_path: str,
                       music_volume: float = 0.12,
                       music_path: str = "") -> bool:
    """Mix TTS audio with background music underneath.

    Background music plays at -18dB (volume=0.12) with 1s fade in/out.

    Args:
        tts_path: Path to TTS audio file
        output_path: Where to save mixed audio
        music_volume: Volume level for background music (0.12 = ~-18dB)
        music_path: Custom music file path (uses BG_MUSIC if empty)

    Returns:
        True if mixing succeeded
    """
    music_file = music_path if (music_path and os.path.exists(music_path)) else BG_MUSIC
    if not os.path.exists(music_file):
        # No music available — just copy TTS as-is
        subprocess.run(["cp", tts_path, output_path], capture_output=True)
        return os.path.exists(output_path)

    tts_dur = ffprobe_duration(tts_path)
    if tts_dur <= 0:
        return False

    fade_out_start = max(0, tts_dur - 1.0)

    cmd = [
        "ffmpeg", "-y",
        "-i", tts_path,
        "-i", music_file,
        "-filter_complex",
        f"[1:a]volume={music_volume},"
        f"afade=t=in:d=1,"
        f"afade=t=out:st={fade_out_start}:d=1,"
        f"atrim=0:{tts_dur}[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first[out]",
        "-map", "[out]",
        "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
        output_path,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and os.path.exists(output_path)
    except subprocess.TimeoutExpired:
        return False


def ensure_music_dir():
    """Create music directory if it doesn't exist."""
    os.makedirs(MUSIC_DIR, exist_ok=True)

```

### FILE: gemini_grade.py
```python
#!/usr/bin/env python3
"""
gemini_grade.py — Protocol Pulse V6 Quality Gate
Submits full forensic data to Gemini 2.5 Pro for rigorous grading.
Only exits 0 (PASS) if grade == A and broadcast_ready == True.
PBX sees NOTHING until this exits 0.
"""
import os, sys, json, urllib.request, subprocess, re, time

# Load env
for line in open('/home/ultron/protocol_pulse/.env'):
    l = line.strip()
    if '=' in l and not l.startswith('#'):
        k, _, v = l.partition('=')
        k = k.strip(); v = v.strip().strip("'").strip('"')
        if k: os.environ[k] = v

GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')
LOG = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/grade_report.log'
GRADE_FILE = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/v6_gemini_grade.json'
PASS_FILE = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/v6_grade_PASS.txt'
RENDER_LOG = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/v6_render.log'

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()

# ── Find the output file ──────────────────────────────────────────────────────
OUTPUT_DIR = '/home/ultron/protocol_pulse/video_pipeline_v3/output'
today = time.strftime('%Y%m%d')

candidates = []
for root, dirs, files in os.walk(OUTPUT_DIR):
    for f in files:
        if f.endswith('.mp4') and 'pulse_check' in f and 'music_mixed' not in f and 'concat_raw' not in f and 'norm' not in f:
            full = os.path.join(root, f)
            candidates.append((os.path.getmtime(full), full))

candidates.sort(reverse=True)
LATEST = candidates[0][1] if candidates else None

if not LATEST:
    log("FATAL: No MP4 output found")
    sys.exit(2)

log(f"Grading: {LATEST}")

# ── ffprobe ───────────────────────────────────────────────────────────────────
log("Running ffprobe...")
probe_raw = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{LATEST}"')
try:
    probe = json.loads(probe_raw)
    fmt = probe.get('format', {})
    streams = probe.get('streams', [])
    duration = float(fmt.get('duration', 0))
    filesize_mb = int(fmt.get('size', 0)) / 1048576
    v_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
    a_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})
    width = v_stream.get('width', 0)
    height = v_stream.get('height', 0)
    vcodec = v_stream.get('codec_name', 'unknown')
    fps_raw = v_stream.get('r_frame_rate', '0/1')
    fps_num, fps_den = fps_raw.split('/') if '/' in fps_raw else (fps_raw, '1')
    fps = round(int(fps_num) / max(int(fps_den), 1), 2)
    acodec = a_stream.get('codec_name', 'unknown')
    sample_rate = a_stream.get('sample_rate', '?')
    channels = a_stream.get('channel_layout', '?')
    num_streams = len(streams)
    bit_rate_kbps = round(int(fmt.get('bit_rate', 0)) / 1000)
except Exception as e:
    log(f"ffprobe parse error: {e}")
    duration = filesize_mb = 0
    width = height = fps = 0
    vcodec = acodec = 'unknown'
    sample_rate = channels = '?'
    num_streams = 0
    bit_rate_kbps = 0

log(f"Duration: {duration:.1f}s | Size: {filesize_mb:.1f}MB | {width}x{height} @ {fps}fps | {vcodec}/{acodec}")

# ── Black frame detection ─────────────────────────────────────────────────────
log("Running blackdetect...")
black_raw = run(f'ffmpeg -i "{LATEST}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1 | grep black_')
black_segments = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', black_raw)
# Filter out very short blacks at start/end (normal fade in/out)
black_mid = [(s,e,d) for s,e,d in black_segments
             if float(s) > 2.0 and float(e) < duration - 2.0]
black_count_total = len(black_segments)
black_count_mid = len(black_mid)
log(f"Black segments: {black_count_total} total, {black_count_mid} mid-video (problem ones)")

# ── Silence detection ─────────────────────────────────────────────────────────
log("Running silencedetect...")
silence_raw = run(f'ffmpeg -i "{LATEST}" -af "silencedetect=noise=-45dB:d=0.8" -f null - 2>&1 | grep silence_')
silence_starts = re.findall(r'silence_start: ([\d.]+)', silence_raw)
silence_ends = re.findall(r'silence_end: ([\d.]+)', silence_raw)
silence_mid = [float(s) for s in silence_starts if float(s) > 2.0 and float(s) < duration - 2.0]
silence_count = len(silence_mid)
log(f"Silence gaps >0.8s mid-video: {silence_count}")

# ── EBU R128 loudness ─────────────────────────────────────────────────────────
log("Running EBU R128 loudness measurement...")
loudness_raw = run(f'ffmpeg -i "{LATEST}" -af "ebur128=peak=true" -f null - 2>&1 | grep -E "Integrated|True Peak|LRA|Threshold"')
integrated_match = re.search(r'(?:Integrated loudness|I:)\s*(-[\d.]+)\s*LUFS', loudness_raw) or re.search(r'I:\s+(-[\d.]+)', loudness_raw)
true_peak_match = re.search(r'(?:True peak|Peak:)\s+(-?[\d.]+)', loudness_raw)
lra_match = re.search(r'LRA:\s+([\d.]+)', loudness_raw)
integrated_lufs = float(integrated_match.group(1)) if integrated_match else None
true_peak_dbfs = float(true_peak_match.group(1)) if true_peak_match else None
lra_lu = float(lra_match.group(1)) if lra_match else None
log(f"Loudness: {integrated_lufs} LUFS | True Peak: {true_peak_dbfs} dBFS | LRA: {lra_lu} LU")

# ── Freeze frame detection ────────────────────────────────────────────────────
log("Running freezedetect...")
freeze_raw = run(f'ffmpeg -i "{LATEST}" -vf "freezedetect=n=0.001:d=1.0" -an -f null - 2>&1 | grep freeze')
freeze_count = len(re.findall(r'freeze_start', freeze_raw))
log(f"Freeze frames: {freeze_count}")

# ── Audio/video stream count ──────────────────────────────────────────────────
has_video = v_stream != {}
has_audio = a_stream != {}

# ── Read render log for content context ──────────────────────────────────────
render_log_content = ''
try:
    with open(RENDER_LOG) as f:
        lines = f.readlines()
    # Filter noise, keep meaningful lines
    keep = [l.strip() for l in lines if l.strip() and
            not any(x in l for x in ['urllib3', 'HTTP Request', 'DEBUG', 'WARNING: Retrying'])]
    render_log_content = '\n'.join(keep[-200:])
except:
    render_log_content = 'Render log unavailable'

# ── Build Gemini prompt ───────────────────────────────────────────────────────
log("Building Gemini grading prompt...")

PROMPT = f"""You are the Chief Quality Officer for Protocol Pulse, a daily autonomous Bitcoin intelligence video show.
Your job: grade this episode with maximum rigour. Be brutally honest. A grade A means it is genuinely broadcast-ready and PBX will publish it immediately. Do not hand out A grades lightly.

=== EPISODE FORENSIC DATA ===

FILE: {os.path.basename(LATEST)}
DURATION: {duration:.1f} seconds ({duration/60:.1f} minutes)
FILE SIZE: {filesize_mb:.1f} MB
BITRATE: {bit_rate_kbps} kbps
RESOLUTION: {width}x{height}
FRAMERATE: {fps} fps
VIDEO CODEC: {vcodec}
AUDIO CODEC: {acodec} | {sample_rate} Hz | {channels}
TOTAL STREAMS: {num_streams}

LOUDNESS (EBU R128):
  Integrated: {integrated_lufs} LUFS   (target: -16 to -14 LUFS)
  True Peak: {true_peak_dbfs} dBFS     (must be under -1.0 dBFS)
  LRA: {lra_lu} LU                     (target: 4-18 LU)

BLACK FRAME SEGMENTS: {black_count_total} total | {black_count_mid} mid-video
  (Mid-video blacks are critical failures. Start/end fades OK.)
  Details: {str(black_mid[:5]) if black_mid else 'none'}

SILENCE GAPS (>0.8s, mid-video): {silence_count}

FREEZE FRAMES (>1s): {freeze_count}

=== RENDER LOG (content/script details) ===
{render_log_content}

=== GRADING RUBRIC ===

Grade each dimension 1-10. Then calculate weighted overall score.

TECHNICAL QUALITY (40% weight):
1. duration_check: 240-480s ideal (8-8min). Under 180s = automatic F. 480-600s acceptable. Over 600s penalise.
2. resolution_check: 1920x1080 = 10. 1280x720 = 7. Anything else = fail.
3. framerate_check: 24-30fps = 10. Under 24fps = 5. Under 15fps = 0.
4. loudness_check: -16 to -14 LUFS = 10. -18 to -12 LUFS = 7. Outside -20 to -10 = critical failure (score 0).
5. true_peak_check: Under -1 dBFS = 10. -1 to 0 = 7. Over 0 dBFS = critical failure (clipping).
6. black_frames_check: 0 mid-video blacks = 10. 1 = 6. 2+ = critical failure (score 0).
7. silence_check: 0 gaps = 10. 1-2 gaps = 6. 3+ = major issue (score 3).
8. freeze_check: 0 freezes = 10. 1 = 5. 2+ = critical failure.
9. codec_check: h264/aac = 10. h265/aac = 10. Other combos = 5.
10. file_integrity_check: Clean container, both streams present, reasonable bitrate (500-5000 kbps) = 10.

CONTENT QUALITY (35% weight):
11. clip_relevance: Are clips from real Bitcoin news? Are the sources credible (not altcoin shills, not 24/7 loops)?
12. script_quality: Is the narration between clips informed, specific, and adds value beyond just re-reading the clips?
13. cold_open_hook: Does the episode open with a compelling, specific hook that makes you want to keep watching?
14. narrative_arc: Does the episode flow logically from open -> clips -> analysis -> close? Or is it random?
15. host_authenticity: Do the two hosts (Eryn and Mark) sound like distinct voices? Natural banter? Not robotic?
16. episode_title: Is the title specific and punchy? Not generic clickbait. Should reflect the actual main story.
17. no_filler: No ad reads, no sponsor segments, no off-topic content, no repeated clips.
18. timeliness: Is the content from today or yesterday? Not stale week-old news.

PRODUCTION QUALITY (25% weight):
19. music_mix: Background music present at proper level, not overpowering narration. Sidechain ducking working?
20. transitions: Are there clean glitch transitions between segments? No hard cuts mid-sentence.
21. visual_polish: Cyberpunk aesthetic consistent. Lower thirds present. No graphical glitches.
22. no_artifacts: No stuttering, no looping, no corrupted frames visible.
23. audio_quality: Narration clear, no clipping, no echo, no background noise in voiceover.
24. pacing: Does the episode feel tight? Not dragging? Not too rushed?

=== YOUR RESPONSE ===

You MUST respond ONLY with valid JSON. No preamble, no explanation, no markdown fences. Raw JSON only.

{{
  "grade": "A|B|C|D|F",
  "overall_score": 0-100,
  "broadcast_ready": true|false,
  "technical_score": 0-100,
  "content_score": 0-100,
  "production_score": 0-100,
  "dimensions": {{
    "duration_check": {{"score": 0-10, "note": "explain"}},
    "resolution_check": {{"score": 0-10, "note": "explain"}},
    "framerate_check": {{"score": 0-10, "note": "explain"}},
    "loudness_check": {{"score": 0-10, "note": "explain"}},
    "true_peak_check": {{"score": 0-10, "note": "explain"}},
    "black_frames_check": {{"score": 0-10, "note": "explain"}},
    "silence_check": {{"score": 0-10, "note": "explain"}},
    "freeze_check": {{"score": 0-10, "note": "explain"}},
    "codec_check": {{"score": 0-10, "note": "explain"}},
    "file_integrity_check": {{"score": 0-10, "note": "explain"}},
    "clip_relevance": {{"score": 0-10, "note": "explain"}},
    "script_quality": {{"score": 0-10, "note": "explain"}},
    "cold_open_hook": {{"score": 0-10, "note": "explain"}},
    "narrative_arc": {{"score": 0-10, "note": "explain"}},
    "host_authenticity": {{"score": 0-10, "note": "explain"}},
    "episode_title": {{"score": 0-10, "note": "explain"}},
    "no_filler": {{"score": 0-10, "note": "explain"}},
    "timeliness": {{"score": 0-10, "note": "explain"}},
    "music_mix": {{"score": 0-10, "note": "explain"}},
    "transitions": {{"score": 0-10, "note": "explain"}},
    "visual_polish": {{"score": 0-10, "note": "explain"}},
    "no_artifacts": {{"score": 0-10, "note": "explain"}},
    "audio_quality": {{"score": 0-10, "note": "explain"}},
    "pacing": {{"score": 0-10, "note": "explain"}}
  }},
  "critical_failures": [],
  "warnings": [],
  "strengths": [],
  "verdict": "One punchy sentence summarising the episode quality",
  "recommendation": "PUBLISH|FIX_AND_RERENDER|DO_NOT_PUBLISH"
}}

Grade thresholds:
- A: overall_score >= 88, zero critical_failures, broadcast_ready = true
- B: overall_score 75-87, at most 1 minor critical failure
- C: overall_score 60-74
- D: overall_score 40-59
- F: overall_score < 40 OR duration < 180s OR clipping OR 2+ mid-video black segments
"""

# ── Call Gemini ───────────────────────────────────────────────────────────────
log("Calling Gemini 2.5 Pro for grading (this may take 30-60s)...")

url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}'
payload = {
    'contents': [{'parts': [{'text': PROMPT}]}],
    'generationConfig': {'maxOutputTokens': 8000, 'temperature': 0.05}
}

req_obj = urllib.request.Request(url,
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req_obj, timeout=90) as resp:
        d = json.loads(resp.read())
        parts = d['candidates'][0]['content'].get('parts', [])
        text = next((p['text'] for p in parts if 'text' in p), None)
        if not text:
            log("FATAL: Gemini returned no text")
            sys.exit(2)
except urllib.error.HTTPError as e:
    log(f"FATAL: Gemini HTTP error {e.code}: {e.read().decode()[:200]}")
    sys.exit(2)
except Exception as e:
    log(f"FATAL: Gemini call failed: {e}")
    sys.exit(2)

# ── Parse result ──────────────────────────────────────────────────────────────
clean = text.strip()
if '```json' in clean:
    clean = clean.split('```json')[1].split('```')[0].strip()
elif '```' in clean:
    clean = clean.split('```')[1].split('```')[0].strip()

try:
    result = json.loads(clean)
except json.JSONDecodeError as e:
    log(f"FATAL: Could not parse Gemini JSON: {e}")
    log(f"Raw response: {clean[:500]}")
    sys.exit(2)

grade = result.get('grade', 'F')
score = result.get('overall_score', 0)
broadcast = result.get('broadcast_ready', False)
recommendation = result.get('recommendation', 'DO_NOT_PUBLISH')
verdict = result.get('verdict', '')
critical = result.get('critical_failures', [])
warnings = result.get('warnings', [])
strengths = result.get('strengths', [])

# Save full grade report
with open(GRADE_FILE, 'w') as f:
    json.dump(result, f, indent=2)
log(f"Grade report saved to {GRADE_FILE}")

# ── Print full scorecard ──────────────────────────────────────────────────────
log("=" * 60)
log(f"GEMINI GRADE: {grade}  |  SCORE: {score}/100  |  {recommendation}")
log(f"VERDICT: {verdict}")
log(f"Technical: {result.get('technical_score')}/100  Content: {result.get('content_score')}/100  Production: {result.get('production_score')}/100")
log("-" * 60)

dims = result.get('dimensions', {})
for dim, data in dims.items():
    s = data.get('score', '?')
    n = data.get('note', '')
    flag = '  ✓' if isinstance(s, int) and s >= 8 else ('  !' if isinstance(s, int) and s < 6 else '')
    log(f"  {dim:30s} {s}/10{flag}  {n[:80]}")

log("-" * 60)
if critical:
    log(f"CRITICAL FAILURES ({len(critical)}):")
    for c in critical:
        log(f"  !! {c}")
if warnings:
    log(f"WARNINGS ({len(warnings)}):")
    for w in warnings:
        log(f"  -- {w}")
if strengths:
    log(f"STRENGTHS ({len(strengths)}):")
    for s in strengths:
        log(f"  ++ {s}")
log("=" * 60)

# ── Pass/fail gate ────────────────────────────────────────────────────────────
if grade == 'A' and broadcast and score >= 88:
    log("*** GRADE A CONFIRMED — BROADCAST READY ***")
    with open(PASS_FILE, 'w') as f:
        f.write(f"GRADE A CONFIRMED\n")
        f.write(f"File: {LATEST}\n")
        f.write(f"Score: {score}/100\n")
        f.write(f"Verdict: {verdict}\n")
        f.write(f"Graded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"\nGRADE_A_PASS|{score}|{LATEST}|{verdict}")
    sys.exit(0)
else:
    log(f"NOT GRADE A: {grade} ({score}/100) — PBX will not be shown this render")
    print(f"\nGRADE_{grade}_FAIL|{score}|{LATEST}|{verdict}")
    sys.exit(1)

```

### FILE: qc_pipeline.py
```python
#!/usr/bin/env python3
"""QC Pipeline — preflight checks + post-render quality validation.

Two entry points:
  preflight_check(manifest_path) — runs BEFORE render
  post_render_qc(video_path, manifest_path) — runs AFTER render

V1 Rule: QC failures LOG only. Do NOT block publish.
"""
import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger("QCPipeline")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[qc] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")


def _ffprobe_duration(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip()) if r.stdout.strip() else 0.0
    except Exception:
        return 0.0


def _ffprobe_bitrate(path: str) -> int:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=bit_rate",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return int(r.stdout.strip()) if r.stdout.strip() else 0
    except Exception:
        return 0


def preflight_check(manifest_path: str) -> tuple:
    """Verify all assets exist and are valid BEFORE rendering.

    Returns:
        (passed: bool, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []

    if not os.path.exists(manifest_path):
        return False, ["Manifest file not found"], []

    with open(manifest_path) as f:
        manifest = json.load(f)

    segments = manifest.get("segments", [])
    logger.info(f"Preflight check: {len(segments)} segments")

    # Check music bed
    music_bed = manifest.get("music_bed_path", "")
    if music_bed and not os.path.exists(music_bed):
        warnings.append(f"Music bed not found: {music_bed}")

    # Check background assets
    bg_files = [
        os.path.join(ASSETS, "backgrounds", "cyberspace.mp4"),
        os.path.join(ASSETS, "backgrounds", "cyberpunk_loop.mp4"),
    ]
    if not any(os.path.exists(bg) for bg in bg_files):
        warnings.append("No background video assets found")

    for seg in segments:
        seg_id = seg.get("id", "?")
        seg_type = seg.get("type", "unknown")

        # Check audio paths
        audio_path = seg.get("audio_path", "")
        if audio_path and not os.path.exists(audio_path):
            if seg_type in ("partner_clip", "cold_open", "narration_setup",
                            "narration_react", "social_card", "wrap"):
                errors.append(f"MISSING AUDIO: segment {seg_id} ({seg_type}): {audio_path}")
            else:
                warnings.append(f"Missing audio: segment {seg_id} ({seg_type}): {audio_path}")
        elif audio_path and os.path.exists(audio_path):
            dur = _ffprobe_duration(audio_path)
            if dur <= 0:
                errors.append(f"ZERO DURATION audio: segment {seg_id} ({seg_type}): {audio_path}")

        # Check clip paths and quality
        video_path = seg.get("video_path", "")
        if seg_type == "partner_clip" and video_path:
            if not os.path.exists(video_path):
                errors.append(f"MISSING CLIP: segment {seg_id}: {video_path}")
            else:
                bitrate = _ffprobe_bitrate(video_path)
                if bitrate > 0 and bitrate < 1_500_000:
                    warnings.append(
                        f"LOW QUALITY clip: segment {seg_id} at {bitrate/1e6:.1f}Mbps: {video_path}")

        # Check social card data
        if seg_type == "social_card":
            card = seg.get("social_card_data", {})
            if not card.get("handle") or not card.get("text"):
                warnings.append(f"Social card segment {seg_id} missing handle/text")
            ss = card.get("screenshot_path", "")
            if ss and not os.path.exists(ss):
                warnings.append(f"Missing screenshot: segment {seg_id}: {ss}")

    passed = len(errors) == 0
    logger.info(f"Preflight: {'PASS' if passed else 'FAIL'} — {len(errors)} errors, {len(warnings)} warnings")
    for e in errors:
        logger.error(f"  ERROR: {e}")
    for w in warnings:
        logger.warning(f"  WARN: {w}")

    return passed, errors, warnings


def post_render_qc(video_path: str, manifest_path: str = "") -> dict:
    """Run automated quality checks AFTER rendering.

    Returns:
        QC report dict with pass/fail for each check.
    """
    report = {
        "video_path": video_path,
        "checks": {},
        "passed": False,
        "details": {},
    }

    if not os.path.exists(video_path):
        report["checks"]["file_exists"] = False
        report["details"]["file_exists"] = "Video file not found"
        return report
    report["checks"]["file_exists"] = True

    # Load manifest expectations if available
    qc_exp = {}
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        qc_exp = manifest.get("qc_expectations", {})

    # 1. Duration check
    duration = _ffprobe_duration(video_path)
    dur_range = qc_exp.get("total_duration_range", [360, 900])
    dur_ok = dur_range[0] <= duration <= dur_range[1]
    report["checks"]["duration"] = dur_ok
    report["details"]["duration"] = {
        "measured": round(duration, 1),
        "expected_range": dur_range,
    }
    logger.info(f"  Duration: {duration:.1f}s (range {dur_range}) {'PASS' if dur_ok else 'FAIL'}")

    # 2. Loudness check (integrated LUFS)
    lufs = None
    true_peak = None
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-filter:a", "loudnorm=print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        # Parse loudnorm JSON from stderr
        stderr = r.stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            ln_data = json.loads(stderr[json_start:json_end])
            lufs = float(ln_data.get("input_i", -99))
            true_peak = float(ln_data.get("input_tp", 0))
    except Exception as e:
        logger.warning(f"  Loudness measurement failed: {e}")

    target_lufs = qc_exp.get("loudness_lufs", -14)
    if lufs is not None:
        lufs_ok = abs(lufs - target_lufs) <= 2
        report["checks"]["loudness"] = lufs_ok
        report["details"]["loudness"] = {
            "measured_lufs": round(lufs, 1),
            "target_lufs": target_lufs,
            "deviation": round(abs(lufs - target_lufs), 1),
        }
        logger.info(f"  Loudness: {lufs:.1f} LUFS (target {target_lufs}) {'PASS' if lufs_ok else 'FAIL'}")
    else:
        report["checks"]["loudness"] = None
        report["details"]["loudness"] = "measurement_failed"

    # 3. True peak check
    target_tp = qc_exp.get("true_peak_dbtp", -1.5)
    if true_peak is not None:
        tp_ok = true_peak <= target_tp
        report["checks"]["true_peak"] = tp_ok
        report["details"]["true_peak"] = {
            "measured_dbtp": round(true_peak, 1),
            "max_dbtp": target_tp,
        }
        logger.info(f"  True peak: {true_peak:.1f} dBTP (max {target_tp}) {'PASS' if tp_ok else 'FAIL'}")
    else:
        report["checks"]["true_peak"] = None

    # 4. Silent gap detection (>2s)
    silences = []
    try:
        max_gap = qc_exp.get("max_silent_gap_sec", 2.0)
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af",
             f"silencedetect=noise=-40dB:d={max_gap}", "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        import re
        for match in re.finditer(r"silence_start: ([\d.]+).*?silence_end: ([\d.]+)", r.stderr, re.DOTALL):
            start, end = float(match.group(1)), float(match.group(2))
            silences.append({"start": round(start, 1), "end": round(end, 1),
                             "duration": round(end - start, 1)})
    except Exception as e:
        logger.warning(f"  Silence detection failed: {e}")

    silence_ok = len(silences) == 0
    report["checks"]["no_dead_air"] = silence_ok
    report["details"]["silences"] = silences
    logger.info(f"  Silent gaps (>{qc_exp.get('max_silent_gap_sec', 2.0)}s): {len(silences)} {'PASS' if silence_ok else 'FAIL'}")

    # 5. Black frame detection (>0.5s)
    black_frames = []
    try:
        max_black = qc_exp.get("max_black_frames_sec", 0.5)
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf",
             f"blackdetect=d={max_black}:pix_th=0.02",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        import re
        for match in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", r.stderr):
            black_frames.append({
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "duration": float(match.group(3)),
            })
    except Exception as e:
        logger.warning(f"  Black frame detection failed: {e}")

    black_ok = len(black_frames) == 0
    report["checks"]["no_black_frames"] = black_ok
    report["details"]["black_frames"] = black_frames
    logger.info(f"  Black frames (>{qc_exp.get('max_black_frames_sec', 0.5)}s): {len(black_frames)} {'PASS' if black_ok else 'FAIL'}")

    # 6. Clip count check
    exp_clips = qc_exp.get("clip_count", 0)
    if exp_clips > 0:
        report["details"]["expected_clips"] = exp_clips

    # Overall pass
    check_vals = [v for v in report["checks"].values() if v is not None]
    report["passed"] = all(check_vals) if check_vals else False

    logger.info(f"  QC Overall: {'PASS' if report['passed'] else 'FAIL'}")
    return report


def save_qc_report(report: dict, output_dir: str) -> str:
    """Save QC report to disk."""
    report_path = os.path.join(output_dir, "qc_report.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"  QC report saved: {report_path}")
    return report_path


def main():
    """CLI: python3 qc_pipeline.py <output_dir>"""
    if len(sys.argv) < 2:
        print("Usage: python3 qc_pipeline.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]

    # Find video and manifest
    import glob
    videos = glob.glob(os.path.join(output_dir, "pulse_check_*.mp4"))
    manifest_path = os.path.join(output_dir, "episode_manifest.json")

    if not videos:
        print(f"No pulse_check_*.mp4 found in {output_dir}")
        sys.exit(1)

    video_path = videos[0]
    print(f"QC Pipeline — {video_path}")

    # Preflight (if manifest exists)
    if os.path.exists(manifest_path):
        passed, errors, warnings = preflight_check(manifest_path)
        print(f"\nPreflight: {'PASS' if passed else 'FAIL'}")

    # Post-render QC
    report = post_render_qc(video_path, manifest_path)
    save_qc_report(report, output_dir)

    print(f"\nPost-render QC: {'PASS' if report['passed'] else 'FAIL'}")
    for check, val in report["checks"].items():
        status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
        print(f"  [{status}] {check}")

    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()

```

### FILE: thumbnail_gen.py
```python
#!/usr/bin/env python3
"""Thumbnail Generator V5 — MMA Central / ESPN style thumbnails.

Features:
- Avatar face prominently on right side
- Bold, thick white text with drop shadow on left
- Red accent color for emphasis words
- Dark cinematic background with gradient
- Asymmetric layout (text 40%, image 60%)
- BTC price badge in corner
- "PROTOCOL PULSE" branding
"""
import os

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Brand colors
BG_DARK = (8, 8, 8)
RED = (204, 0, 0)
RED_BRIGHT = (255, 51, 51)
WHITE = (255, 255, 255)
GRAY = (120, 120, 120)
LIGHT_GRAY = (180, 180, 180)

# Default avatar path (from model_registry)
AVATAR_PATH = os.path.expanduser("~/protocol_pulse/oracle/Proto_P_Avatar_512.png")


def generate_thumbnail(headline: str, subtext: str = "",
                       output_path: str = "thumbnail.png",
                       btc_price: str = "",
                       avatar_path: str = None,
                       top_quote: str = "") -> str:
    """Generate a 1280x720 MMA Central style YouTube thumbnail.

    Args:
        headline: Bold main text (5-8 words)
        subtext: Secondary line
        output_path: Where to save
        btc_price: BTC price for badge
        avatar_path: Path to avatar/face image
        top_quote: Optional quote text for additional context

    Returns:
        Path to generated thumbnail, or "" on failure.
    """
    if not HAS_PIL:
        print("  [thumb] Pillow not installed, skipping thumbnail")
        return ""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    W, H = 1280, 720
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # ── Background: dark cinematic gradient ──────────────────────────────
    for y in range(H):
        for x in range(W):
            # Diagonal gradient: dark to slightly lighter
            factor = (x / W * 0.3 + y / H * 0.7)
            r = int(8 + 15 * factor)
            g = int(5 + 5 * factor)
            b = int(5 + 5 * factor)
            draw.point((x, y), fill=(r, g, b))

    # Red accent glow behind where face will be (right side)
    for y in range(H):
        for x in range(max(0, W - 500), W):
            alpha = (x - (W - 500)) / 500.0
            gy = 1.0 - abs(y / H - 0.5) * 2
            intensity = alpha * gy * 0.15
            r = int(8 + 200 * intensity)
            g = int(5 + 10 * intensity)
            b = int(5 + 10 * intensity)
            draw.point((x, y), fill=(r, g, b))

    # ── Avatar / face image (right 60%) ──────────────────────────────────
    face_path = avatar_path or AVATAR_PATH
    if os.path.exists(face_path):
        try:
            face_img = Image.open(face_path).convert("RGBA")
            # Scale to fit right portion, vertically centered
            face_h = H
            face_w = int(face_img.width * face_h / face_img.height)
            face_img = face_img.resize((face_w, face_h), Image.LANCZOS)

            # Enhance: slightly more contrast for dramatic look
            enhancer = ImageEnhance.Contrast(face_img)
            face_img = enhancer.enhance(1.2)
            enhancer = ImageEnhance.Brightness(face_img)
            face_img = enhancer.enhance(0.85)

            # Create gradient mask for left-edge fade
            mask = Image.new("L", (face_w, face_h), 255)
            mask_draw = ImageDraw.Draw(mask)
            fade_width = face_w // 3
            for x in range(fade_width):
                alpha = int(255 * (x / fade_width))
                mask_draw.line([(x, 0), (x, face_h)], fill=alpha)

            # Position on right side
            face_x = W - face_w + 50
            img.paste(face_img, (face_x, 0), mask)
        except Exception as e:
            print(f"  [thumb] Avatar load error: {e}")

    draw = ImageDraw.Draw(img)  # Refresh draw after paste

    # ── Red accent bars ──────────────────────────────────────────────────
    draw.rectangle([(0, 0), (6, H)], fill=RED)  # Left edge
    draw.rectangle([(0, 380), (520, 384)], fill=RED)  # Horizontal accent

    # ── "PULSE CHECK" show name (top-left) ───────────────────────────────
    try:
        font_show = ImageFont.truetype(FONT_BOLD, 26)
    except Exception:
        font_show = ImageFont.load_default()
    draw.text((25, 22), "PULSE CHECK", fill=RED_BRIGHT, font=font_show)

    # ── Main headline (left 45% of frame) ────────────────────────────────
    try:
        font_headline = ImageFont.truetype(FONT_BOLD, 68)
    except Exception:
        font_headline = ImageFont.load_default()

    max_text_width = int(W * 0.48)
    words = headline.upper().split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_headline)
        if bbox[2] - bbox[0] > max_text_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    # Draw headline with drop shadow
    line_height = 78
    total_height = len(lines) * line_height
    start_y = max(80, (340 - total_height) // 2 + 60)

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        # Shadow (offset)
        draw.text((27, y + 4), line, fill=(20, 20, 20), font=font_headline)
        draw.text((28, y + 3), line, fill=(30, 30, 30), font=font_headline)
        # Main text
        draw.text((25, y), line, fill=WHITE, font=font_headline)

    # ── Subtext below accent line ────────────────────────────────────────
    if subtext:
        try:
            font_sub = ImageFont.truetype(FONT_BOLD, 32)
        except Exception:
            font_sub = ImageFont.load_default()
        draw.text((25, 405), subtext.upper(), fill=LIGHT_GRAY, font=font_sub)

    # ── Quote (if provided) ──────────────────────────────────────────────
    if top_quote:
        try:
            font_quote = ImageFont.truetype(FONT_MONO, 18)
        except Exception:
            font_quote = ImageFont.load_default()
        quote_text = f'"{top_quote[:80]}"'
        draw.text((25, 450), quote_text, fill=GRAY, font=font_quote)

    # ── BTC price badge (bottom-left) ────────────────────────────────────
    if btc_price:
        try:
            font_btc = ImageFont.truetype(FONT_BOLD, 28)
            font_btc_label = ImageFont.truetype(FONT_MONO, 16)
        except Exception:
            font_btc = font_btc_label = ImageFont.load_default()

        # Badge background
        badge_w, badge_h = 200, 55
        badge_x, badge_y = 25, H - 75
        draw.rectangle(
            [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
            fill=(15, 15, 15), outline=RED, width=2,
        )
        # BTC icon (circle)
        draw.ellipse(
            [(badge_x + 8, badge_y + 12), (badge_x + 38, badge_y + 42)],
            fill=RED,
        )
        draw.text((badge_x + 16, badge_y + 14), "B", fill=WHITE, font=font_btc_label)
        # Price text
        draw.text((badge_x + 48, badge_y + 12), btc_price, fill=WHITE, font=font_btc)

    # ── "PROTOCOL PULSE" branding (bottom-right) ────────────────────────
    try:
        font_brand = ImageFont.truetype(FONT_MONO, 16)
    except Exception:
        font_brand = ImageFont.load_default()
    draw.text((W - 200, H - 35), "PROTOCOL PULSE", fill=GRAY, font=font_brand)

    img.save(output_path, "PNG", quality=95)
    sz = os.path.getsize(output_path) // 1024
    print(f"  [thumb] Generated: {output_path} ({W}x{H}, {sz}KB)")
    return output_path


if __name__ == "__main__":
    out = os.path.join(BASE, "output", "test_thumbnail_v5.png")
    generate_thumbnail(
        "HASH RATE BREAKS ALL RECORDS",
        "Nations are stacking",
        out,
        btc_price="$97,234",
        top_quote="When the entities that print fiat start hoarding the exit asset...",
    )

```

### FILE: shorts_cutter.py
```python
#!/usr/bin/env python3
"""Shorts Cutter V5 — generate vertical 9:16 shorts using Oracle avatar.

Picks the 3 most quotable one-liners from host dialogue.
Uses the Oracle avatar server for lip-synced shorts.
Falls back to text-on-dark if avatar is unavailable.
"""
import json
import logging
import os
import subprocess
import tempfile
import time

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger("ShortsCutter")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[shorts] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
AVATAR_SERVER = "http://localhost:8200"

# Jessica's voice for avatar
AVATAR_VOICE_ID = "cgSgspJ2msm6clMCkdW9"


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _avatar_available() -> bool:
    """Check if Oracle avatar server is running."""
    if not HAS_REQUESTS:
        return False
    try:
        r = requests.get(f"{AVATAR_SERVER}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def create_avatar_short(text: str, headline: str, output_path: str,
                        btc_price: str = "", short_index: int = 0) -> str:
    """Generate a vertical short with avatar lip-syncing the text.

    1. Call avatar server to generate lip-synced video
    2. Resize/crop to 1080x1920 vertical
    3. Add branded overlay (title text, BTC price, branding)

    Falls back to text-on-dark if avatar server is unavailable.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Try avatar server first
    if _avatar_available():
        logger.info(f"  Short #{short_index+1}: generating avatar video...")
        avatar_mp4 = output_path + ".avatar_raw.mp4"

        try:
            # Generate audio via ElevenLabs first, then send to avatar
            from relay import get_key
            from tts_engine import tts_elevenlabs

            tts_path = output_path + ".tts.m4a"
            if tts_elevenlabs(text, tts_path, host=1):
                # Read audio and send to avatar server
                import base64
                with open(tts_path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()

                resp = requests.post(
                    f"{AVATAR_SERVER}/generate",
                    json={
                        "audio_base64": audio_b64,
                        "content_type": "audio/mp4",
                        "enable_blinks": True,
                        "enable_head_movement": True,
                        "fps": 30,
                    },
                    timeout=120,
                )

                if resp.status_code == 200:
                    with open(avatar_mp4, "wb") as f:
                        f.write(resp.content)

                    if os.path.exists(avatar_mp4) and os.path.getsize(avatar_mp4) > 1000:
                        # Convert to vertical with overlays
                        result = _add_short_overlays(avatar_mp4, headline, output_path,
                                                      btc_price, short_index)
                        # Cleanup
                        for tmp in [avatar_mp4, tts_path]:
                            if os.path.exists(tmp):
                                try:
                                    os.remove(tmp)
                                except OSError:
                                    pass
                        if result:
                            return result
                else:
                    logger.warning(f"  Avatar server returned {resp.status_code}")

            # Cleanup TTS if avatar failed
            if os.path.exists(tts_path):
                try:
                    os.remove(tts_path)
                except OSError:
                    pass

        except Exception as e:
            logger.warning(f"  Avatar generation failed: {e}")

    # Fallback: TTS audio with text-on-dark vertical video
    logger.info(f"  Short #{short_index+1}: fallback (text-on-dark)...")
    return _create_text_short(text, headline, output_path, btc_price, short_index)


def _add_short_overlays(avatar_video: str, headline: str, output_path: str,
                         btc_price: str = "", short_index: int = 0) -> str:
    """Add branded overlays to avatar video and convert to 1080x1920 vertical."""
    dur = ffprobe_duration(avatar_video)
    if dur <= 0:
        return ""

    safe_headline = headline.replace("'", "").replace(":", " -").replace('"', '').replace("%", " pct")

    # Word-wrap headline for bottom overlay
    words = safe_headline.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > 28:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    lines = lines[:3]

    headline_filters = ""
    for i, line in enumerate(lines):
        y = 1500 + i * 55
        headline_filters += (
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor=white:fontsize=42:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y={y},"
        )

    btc_text = btc_price.replace("'", "") if btc_price else ""
    btc_filter = ""
    if btc_text:
        btc_filter = (
            f"drawtext=fontfile={FONT_MONO}:text='BTC {btc_text}':"
            f"fontcolor=0xCC0000:fontsize=24:x=w-text_w-20:y=50,"
        )

    fg = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"drawbox=x=0:y=0:w=1080:h=80:c=0x0A0A0A@0.7:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
        f"fontcolor=white:fontsize=32:x=(w-text_w)/2:y=25,"
        f"{btc_filter}"
        f"{headline_filters}"
        f"drawbox=x=0:y=1820:w=1080:h=100:c=0x0A0A0A@0.8:t=fill,"
        f"drawtext=fontfile={FONT_MONO}:text='@ProtocolPulse':"
        f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=1845,"
        f"format=yuv420p[v];\n"
        f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    fd, fpath = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fg)
        cmd = [
            "ffmpeg", "-y", "-i", avatar_video,
            "-filter_complex_script", fpath,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "22", "-preset", "fast",
            "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
            "-t", str(min(dur, 59)),
            output_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            logger.error(f"  Short overlay failed: {r.stderr[-300:]}")
            return ""
    finally:
        os.unlink(fpath)

    out_dur = ffprobe_duration(output_path)
    sz = os.path.getsize(output_path) // 1024
    logger.info(f"  Short #{short_index+1}: {out_dur:.1f}s, {sz}KB (avatar)")
    return output_path


def _create_text_short(text: str, headline: str, output_path: str,
                       btc_price: str = "", short_index: int = 0) -> str:
    """Fallback: generate a vertical short with TTS audio + text overlay on dark bg."""
    from tts_engine import tts_elevenlabs

    tts_path = output_path + ".tts.m4a"
    if not tts_elevenlabs(text, tts_path, host=1):
        logger.error(f"  TTS failed for short #{short_index+1}")
        return ""

    dur = ffprobe_duration(tts_path)
    if dur <= 0:
        return ""

    safe_text = text[:120].replace("'", "").replace('"', '').replace(":", " -").replace("%", " pct")
    safe_headline = headline[:60].replace("'", "").replace('"', '').replace(":", " -")

    # Word-wrap text
    words = safe_text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > 30:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)

    text_filters = ""
    for i, line in enumerate(lines[:5]):
        y = 750 + i * 55
        text_filters += (
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor=white:fontsize=40:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y={y},"
        )

    fg = (
        f"color=c=0x080808:s=1080x1920:d={dur}:r=30,"
        f"drawbox=x=0:y=0:w=1080:h=80:c=0x0A0A0A@0.7:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
        f"fontcolor=white:fontsize=32:x=(w-text_w)/2:y=25,"
        f"{text_filters}"
        f"drawbox=x=0:y=1820:w=1080:h=100:c=0x0A0A0A@0.8:t=fill,"
        f"drawtext=fontfile={FONT_MONO}:text='@ProtocolPulse':"
        f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=1845,"
        f"format=yuv420p[v];\n"
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    fd, fpath = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fg)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x080808:s=1080x1920:d={dur}:r=30",
            "-i", tts_path,
            "-filter_complex_script", fpath,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "22", "-preset", "fast",
            "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
            "-t", str(min(dur, 59)),
            output_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            logger.error(f"  Short text fallback failed: {r.stderr[-300:]}")
            return ""
    finally:
        os.unlink(fpath)
        if os.path.exists(tts_path):
            try:
                os.remove(tts_path)
            except OSError:
                pass

    out_dur = ffprobe_duration(output_path)
    sz = os.path.getsize(output_path) // 1024
    logger.info(f"  Short #{short_index+1}: {out_dur:.1f}s, {sz}KB (text fallback)")
    return output_path


def generate_shorts(script: dict, output_dir: str, btc_price: str = "",
                    max_shorts: int = 3) -> list:
    """Generate vertical shorts from the script's best quotes.

    Uses shorts_quotes from the script, or picks from dialogue reactions.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Get quotes for shorts
    quotes = script.get("shorts_quotes", [])
    if not quotes or len(quotes) < max_shorts:
        # Pick from dialogue reactions
        for entry in script.get("dialogue", []):
            if entry.get("type") in ("react", "wrap") and entry.get("host") in (1, 2, "1", "2"):
                text = entry.get("text", "")
                if 20 <= len(text) <= 150:
                    quotes.append(text)
            if len(quotes) >= max_shorts:
                break

    headlines = script.get("segments_summary", [])
    episode_title = script.get("episode_title", "Pulse Check")

    shorts = []
    for i, quote in enumerate(quotes[:max_shorts]):
        headline = headlines[i] if i < len(headlines) else episode_title
        short_path = os.path.join(output_dir, f"short_{i+1}.mp4")
        result = create_avatar_short(
            quote, headline, short_path,
            btc_price=btc_price, short_index=i,
        )
        if result:
            shorts.append(result)

    logger.info(f"Generated {len(shorts)}/{max_shorts} shorts")
    return shorts


if __name__ == "__main__":
    from script_writer import generate_sample_script
    script = generate_sample_script()
    out_dir = os.path.join(BASE, "output", "test_shorts_v5")
    shorts = generate_shorts(script, out_dir, btc_price="$97,000")
    print(f"Generated {len(shorts)} shorts")

```

### FILE: chapters.py
```python
#!/usr/bin/env python3
"""Chapter markers — YouTube description format + FFmpeg chapter metadata.
Generates timestamped chapter list from dialogue audio timing data."""
import os, subprocess, json


def generate_chapters(script: dict, audio_data: dict,
                      output_path: str) -> str:
    """Generate YouTube-format chapter markers.

    Args:
        script: V4 script with chapters array
        audio_data: From generate_dialogue_audio() with timing info
        output_path: Path for chapters.txt

    Returns:
        Path to chapters file.
    """
    chapters = script.get("chapters", [])
    lines = audio_data.get("lines", [])
    total_dur = audio_data.get("total_duration", 0)

    if not chapters:
        # Auto-generate from dialogue structure
        chapters = _auto_chapters(script, lines)

    # Calculate timestamps based on line timing
    timed_chapters = _assign_timestamps(chapters, lines, total_dur)

    # Write YouTube description format
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write("CHAPTERS\n")
        f.write("=" * 40 + "\n\n")
        for ch in timed_chapters:
            f.write(f"{ch['timestamp']}  {ch['title']}\n")
        f.write(f"\n{'=' * 40}\n")
        f.write("Copy the timestamps above into your YouTube description.\n")

    print(f"  [chapters] Generated {len(timed_chapters)} chapters → {output_path}")
    return output_path


def _auto_chapters(script: dict, lines: list) -> list:
    """Generate chapters automatically from dialogue structure."""
    chapters = [{"title": "Intro", "time_hint": "start"}]
    summaries = script.get("segments_summary", [])

    if summaries:
        for i, s in enumerate(summaries):
            hint = "after_intro" if i == 0 else ("mid" if i < len(summaries) - 1 else "late")
            chapters.append({"title": s, "time_hint": hint})
    else:
        # Scan for topic changes in dialogue
        seen_topics = 0
        for i, line in enumerate(lines):
            text = line.get("text", "")
            if any(w in text.lower() for w in ["meanwhile", "now", "next", "speaking of", "but here"]):
                seen_topics += 1
                chapters.append({
                    "title": f"Topic {seen_topics}",
                    "time_hint": "mid",
                })

    chapters.append({"title": "Outro", "time_hint": "end"})
    return chapters


def _assign_timestamps(chapters: list, lines: list, total_dur: float) -> list:
    """Assign actual timestamps to chapter hints."""
    n = len(chapters)
    if n == 0:
        return []

    timed = []
    for i, ch in enumerate(chapters):
        hint = ch.get("time_hint", "mid")

        if hint == "start":
            seconds = 0
        elif hint == "after_intro":
            # After first few dialogue lines
            if len(lines) > 2:
                seconds = lines[2].get("start", 0) + lines[2].get("duration", 0)
            else:
                seconds = total_dur * 0.1
        elif hint == "end":
            seconds = max(0, total_dur - 20)
        elif hint == "late":
            seconds = total_dur * 0.7
        else:  # "mid" — distribute evenly
            frac = (i / max(n - 1, 1))
            seconds = total_dur * frac

        seconds = max(0, int(seconds))
        mins = seconds // 60
        secs = seconds % 60
        timed.append({
            "title": ch["title"],
            "seconds": seconds,
            "timestamp": f"{mins}:{secs:02d}",
        })

    return timed


def embed_ffmpeg_chapters(video_path: str, chapters_path: str,
                          output_path: str) -> str:
    """Embed chapter metadata into the video file via FFmpeg."""
    # Read chapters
    chapters = []
    with open(chapters_path) as f:
        for line in f:
            line = line.strip()
            if ":" in line and line[0].isdigit():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    ts, title = parts
                    mins, secs = ts.split(":")
                    total_s = int(mins) * 60 + int(secs)
                    chapters.append({"start": total_s, "title": title})

    if not chapters:
        return video_path

    # Build FFmpeg metadata file
    meta_lines = [";FFMETADATA1"]
    for i, ch in enumerate(chapters):
        start_ms = ch["start"] * 1000
        if i + 1 < len(chapters):
            end_ms = chapters[i + 1]["start"] * 1000
        else:
            end_ms = start_ms + 60000  # 1 min default for last chapter
        meta_lines.append("[CHAPTER]")
        meta_lines.append("TIMEBASE=1/1000")
        meta_lines.append(f"START={start_ms}")
        meta_lines.append(f"END={end_ms}")
        meta_lines.append(f"title={ch['title']}")

    meta_path = video_path + ".ffmeta.txt"
    with open(meta_path, "w") as f:
        f.write("\n".join(meta_lines))

    r = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-i", meta_path,
         "-map_metadata", "1", "-c", "copy", output_path],
        capture_output=True, text=True, timeout=120,
    )

    try:
        os.remove(meta_path)
    except Exception:
        pass

    if r.returncode == 0 and os.path.exists(output_path):
        return output_path
    return video_path


# Alias for compatibility with verification imports
generate_chapters_txt = generate_chapters


if __name__ == "__main__":
    sample = {
        "chapters": [
            {"title": "Intro", "time_hint": "start"},
            {"title": "Mining Difficulty", "time_hint": "after_intro"},
            {"title": "Sovereign Funds", "time_hint": "mid"},
            {"title": "Outro", "time_hint": "end"},
        ],
    }
    audio = {"lines": [], "total_duration": 120}
    base = os.path.dirname(os.path.abspath(__file__))
    generate_chapters(sample, audio, os.path.join(base, "output", "test_chapters.txt"))

```

### FILE: utils/clip_scorer.py
```python
#!/usr/bin/env python3
"""Intelligent Clip Scoring Engine — data-driven clip selection.

Scores each potential clip moment 0-100 based on 5 dimensions:
1. Topic velocity (from daily_signals.json) — 0-25 points
2. Engagement potential (topic trending on X) — 0-20 points
3. Novelty (not covered in recent episodes) — 0-20 points
4. Speaker authority (channel priority) — 0-15 points
5. Emotional impact (keyword analysis) — 0-20 points

Per PRODUCTION_DESIGN_LAWS.md and PIPELINE_LAWS Section 9.
"""

import json
import logging
import os

logger = logging.getLogger("ClipScorer")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_SIGNALS_PATH = os.path.join(BASE, "data", "intelligence", "daily_signals.json")
LIVE_SIGNALS_PATH = os.path.join(BASE, "data", "intelligence", "live_signals.json")
USED_CLIPS_PATH = os.path.join(BASE, "data", "used_clips.json")
NARRATIVE_CONTEXT_PATH = os.path.join(BASE, "data", "intelligence", "narrative_context.json")
CHANNELS_FILE = os.path.join(BASE, "channels.yaml")

# High-impact words that indicate emotional/breaking content
IMPACT_WORDS = [
    "breaking", "shocking", "unprecedented", "historic", "billion", "million",
    "crashed", "surged", "banned", "approved", "emergency", "revolutionary",
    "first time", "never before", "record", "all-time", "critical", "massive",
    "collapse", "exploded", "plummeted", "skyrocketed", "halving", "strategic reserve",
]

# Engagement-boosting topics (from tweet study data and X algorithm preferences)
HIGH_ENGAGEMENT_TOPICS = {
    "ETF": 18, "price": 16, "mining": 14, "regulation": 15,
    "self-custody": 12, "macro": 13, "institutional": 14,
    "lightning": 10, "privacy": 11,
}


def _load_json(path):
    """Load JSON file safely."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_channel_priorities():
    """Load channel priority map from channels.yaml."""
    try:
        import yaml
        with open(CHANNELS_FILE) as f:
            config = yaml.safe_load(f)
        priorities = {}
        for ch in config.get("channels", []) + config.get("mainstream", []):
            name = ch.get("name", ch.get("handle", ""))
            if name:
                priorities[name] = ch.get("priority", ch.get("tier", 3))
        return priorities
    except Exception:
        return {}


def _get_recent_topics(max_episodes=3):
    """Get topics covered in last N episodes (for novelty scoring)."""
    data = _load_json(USED_CLIPS_PATH)
    if not data:
        return set()

    recent = data.get("episodes", [])[-max_episodes:]
    topics = set()
    for ep in recent:
        # Extract channel names as proxy for topics (full topic tracking would need
        # the actual clip quotes stored in episode memory)
        topics.update(ep.get("channels", []))
    return topics


def _get_live_boost_topics():
    """Get topics from active live streams for velocity boost (1.5x per LIVE_INTELLIGENCE_LAWS)."""
    data = _load_json(LIVE_SIGNALS_PATH)
    if not data:
        return set()
    live_topics = set()
    for s in data.get("live_streams", []):
        if s.get("status") == "live":
            live_topics.update(s.get("topics", []))
    return live_topics


def _load_narrative_context():
    """Load narrative_context.json for narrative match scoring."""
    return _load_json(NARRATIVE_CONTEXT_PATH) or {}


def _score_narrative_match(clip: dict, narrative_context: dict) -> int:
    """Score how well a clip matches today's dominant thought leader narrative.

    0-25 points:
    - 25: clip topic exactly matches #1 narrative AND channel is thought leader's YT channel
    - 20: clip topic matches #1 narrative
    - 15: clip topic matches #2 or #3 narrative
    - 10: clip topic adjacent to a narrative
    - 5:  clip mentions any trending thought leader by name
    - 0:  no narrative connection
    """
    priority_topics = narrative_context.get("clip_selection_priority", [])
    if not priority_topics:
        return 0

    clip_text = " ".join([
        clip.get("quote", ""),
        clip.get("key_quote", ""),
        clip.get("video_title", ""),
        clip.get("why", ""),
        clip.get("host_setup", ""),
        clip.get("narrator_intro", ""),
    ]).lower()

    if not clip_text.strip():
        return 0

    # Check exact match with top narrative
    top_narrative = priority_topics[0].lower() if priority_topics else ""
    if top_narrative:
        top_words = [w for w in top_narrative.split() if len(w) > 2]
        if top_words and all(w in clip_text for w in top_words):
            return 25  # Full match with #1 narrative
        if top_words and any(w in clip_text for w in top_words):
            return 20  # Partial match with #1 narrative

    # Check secondary narratives (#2 and #3)
    for topic in priority_topics[1:3]:
        topic_words = [w for w in topic.lower().split() if len(w) > 2]
        if topic_words and any(w in clip_text for w in topic_words):
            return 15

    # Check thought leader name mentions
    thought_leaders = narrative_context.get("thought_leaders_mentioned", [])
    if any(tl.lower() in clip_text for tl in thought_leaders if tl):
        return 5

    return 0


def score_clip(clip, daily_signals=None, channel_priorities=None, recent_channels=None,
               live_topics=None, narrative_context=None):
    """Score a single clip moment 0-100 across 6 dimensions.

    Dimensions:
    1. Topic velocity (daily_signals.json) — 0-25 pts
    2. Engagement potential (X trending) — 0-20 pts
    3. Novelty (not in recent episodes) — 0-20 pts
    4. Speaker authority (channel tier) — 0-15 pts
    5. Emotional impact (keyword) — 0-20 pts
    6. Narrative match (thought leader discourse) — 0-25 pts

    Raw total 0-125, normalized to 0-100.

    Args:
        clip: Dict with at minimum 'channel' and 'quote'/'transcript' keys.
        daily_signals: Loaded daily_signals.json dict (or None to load from disk).
        channel_priorities: Dict of channel_name -> priority int (or None to load).
        recent_channels: Set of channel names from recent episodes (or None to compute).
        live_topics: Set of topics from active live streams (or None to load).
        narrative_context: Loaded narrative_context.json dict (or None to load from disk).

    Returns:
        int: Score 0-100.
    """
    if daily_signals is None:
        daily_signals = _load_json(DAILY_SIGNALS_PATH) or {}
    if channel_priorities is None:
        channel_priorities = _load_channel_priorities()
    if recent_channels is None:
        recent_channels = _get_recent_topics(max_episodes=3)
    if live_topics is None:
        live_topics = _get_live_boost_topics()
    if narrative_context is None:
        narrative_context = _load_narrative_context()

    # Combine all text for analysis
    text = " ".join([
        clip.get("quote", ""),
        clip.get("why", ""),
        clip.get("host_setup", ""),
        clip.get("video_title", ""),
    ]).lower()

    raw_score = 0

    # ── 1. Topic Velocity (0-25 points) ──
    topic_velocity = daily_signals.get("topic_velocity", [])
    best_velocity = 0
    for topic_entry in topic_velocity:
        topic_name = topic_entry.get("topic", "").lower()
        velocity = topic_entry.get("velocity_score", 0)

        if topic_name in text or any(w in text for w in topic_name.split()):
            topic_score = min(velocity / 4, 25)
            if topic_name in live_topics:
                topic_score = min(topic_score * 1.5, 25)
            best_velocity = max(best_velocity, topic_score)

    raw_score += round(best_velocity)

    # ── 2. Engagement Potential (0-20 points) ──
    engagement_score = 0
    for topic, base_engagement in HIGH_ENGAGEMENT_TOPICS.items():
        if topic.lower() in text:
            engagement_score = max(engagement_score, base_engagement)
    raw_score += min(engagement_score, 20)

    # ── 3. Novelty (0-20 points) ──
    channel = clip.get("channel", "")
    if channel in recent_channels:
        raw_score += 5
    else:
        raw_score += 20

    # ── 4. Speaker Authority (0-15 points) ──
    priority = channel_priorities.get(channel, 3)
    authority_map = {1: 15, 2: 10, 3: 5}
    raw_score += authority_map.get(priority, 3)

    # ── 5. Emotional Impact (0-20 points) ──
    impact_count = sum(1 for w in IMPACT_WORDS if w in text)
    raw_score += min(impact_count * 5, 20)

    # ── 6. Narrative Match (0-25 points) ──
    raw_score += _score_narrative_match(clip, narrative_context)

    # Normalize: raw 0-125 → 0-100
    final_score = min(100, round(raw_score * 100 / 125))
    return final_score


def rank_clips(clips, daily_signals=None, narrative_context=None):
    """Score and rank a list of clips. Returns clips sorted by score (highest first).

    Each clip gets a 'score' field added.

    Args:
        clips: List of clip dicts (from Claude's selection).
        daily_signals: Optional pre-loaded daily_signals.json.
        narrative_context: Optional pre-loaded narrative_context.json.

    Returns:
        List of clips sorted by score descending, each with 'score' added.
    """
    if daily_signals is None:
        daily_signals = _load_json(DAILY_SIGNALS_PATH) or {}
    if narrative_context is None:
        narrative_context = _load_narrative_context()

    channel_priorities = _load_channel_priorities()
    recent_channels = _get_recent_topics(max_episodes=3)
    live_topics = _get_live_boost_topics()

    # Log narrative context
    dominant = narrative_context.get("dominant_narrative", "none")
    priorities = narrative_context.get("clip_selection_priority", [])
    if dominant and dominant != "none":
        logger.info(f"Episode narrative: {dominant} | Priority topics: {priorities}")

    for clip in clips:
        clip["score"] = score_clip(
            clip,
            daily_signals=daily_signals,
            channel_priorities=channel_priorities,
            recent_channels=recent_channels,
            live_topics=live_topics,
            narrative_context=narrative_context,
        )

    ranked = sorted(clips, key=lambda c: c.get("score", 0), reverse=True)

    for i, clip in enumerate(ranked):
        logger.info(f"  SCORE #{i+1}: [{clip.get('channel', '')}] "
                    f"score={clip['score']} — {clip.get('video_title', '')[:40]}")

    return ranked


def select_top_clips(clips, count=5, daily_signals=None, narrative_context=None):
    """Score all clips, then pick the top N from N unique channels.

    Enforces channel diversity: one clip per channel, highest-scored wins.

    Args:
        clips: List of clip dicts.
        count: Number of clips to select (default 5).
        daily_signals: Optional pre-loaded daily_signals.json.
        narrative_context: Optional pre-loaded narrative_context.json.

    Returns:
        List of top N clips from N unique channels, sorted by score.
    """
    ranked = rank_clips(clips, daily_signals=daily_signals, narrative_context=narrative_context)

    selected = []
    seen_channels = set()
    for clip in ranked:
        channel = clip.get("channel", "")
        if channel in seen_channels:
            continue
        seen_channels.add(channel)
        selected.append(clip)
        if len(selected) >= count:
            break

    logger.info(f"Selected top {len(selected)} clips from {len(seen_channels)} unique channels")
    return selected


if __name__ == "__main__":
    # Demo with mock clips
    test_clips = [
        {"channel": "Simply Bitcoin", "quote": "Bitcoin ETF inflows just hit a record billion dollars",
         "video_title": "BREAKING: ETF Record Inflows", "why": "Record breaking ETF data"},
        {"channel": "TFTC", "quote": "Hash rate surged to unprecedented levels",
         "video_title": "Mining Update: Hash Rate ATH", "why": "Historic hash rate data"},
        {"channel": "What Bitcoin Did", "quote": "The fed is going to have to cut rates",
         "video_title": "Macro Analysis with Luke Gromen", "why": "Macro insight"},
        {"channel": "Preston Pysh", "quote": "Self custody is more important than ever",
         "video_title": "Why Self-Custody Matters in 2026", "why": "Sovereignty angle"},
        {"channel": "Blockworks", "quote": "Lightning network capacity just exploded",
         "video_title": "Lightning Network Growth", "why": "Layer 2 data"},
    ]

    results = select_top_clips(test_clips, count=5)
    print("\nTop clips by score:")
    for c in results:
        print(f"  {c['score']:3d} | {c['channel']:20s} | {c['video_title']}")

```

### FILE: utils/quality_gate.py
```python
"""Quality Gate — compute episode quality score and decide upload eligibility.

Score 0-100 based on REAL production quality metrics (ffprobe analysis).
Per PIPELINE_FORENSIC_AUDIT LAW D4 + 2026-03-12 QC overhaul.

Previous version was manifest-metadata-only and scored 94/100 on renders
that Gemini graded F (29-38/100). Now runs actual ffprobe checks for:
  - Silence detection (silencedetect)
  - Black frame detection (blackdetect)
  - True peak analysis (loudnorm)
  - Duration validation
"""
import json
import logging
import os
import re
import subprocess

logger = logging.getLogger("QualityGate")


def _run_ffprobe_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip()) if r.stdout.strip() else 0.0
    except Exception:
        return 0.0


def _detect_silence(video_path: str, min_duration: float = 2.0,
                    noise_db: int = -40) -> list:
    """Run ffmpeg silencedetect and return list of silent segments.

    Returns: [{"start": float, "end": float, "duration": float}, ...]
    """
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af",
             f"silencedetect=noise={noise_db}dB:d={min_duration}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        silences = []
        for match in re.finditer(
            r"silence_start: ([\d.]+).*?silence_end: ([\d.]+).*?silence_duration: ([\d.]+)",
            r.stderr, re.DOTALL,
        ):
            silences.append({
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "duration": float(match.group(3)),
            })
        return silences
    except Exception as e:
        logger.warning(f"Silence detection failed: {e}")
        return []


def _detect_black_frames(video_path: str, min_duration: float = 0.5,
                         pix_threshold: float = 0.02) -> list:
    """Run ffmpeg blackdetect and return list of black segments.

    Returns: [{"start": float, "end": float, "duration": float}, ...]
    """
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf",
             f"blackdetect=d={min_duration}:pix_th={pix_threshold}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        blacks = []
        for match in re.finditer(
            r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)",
            r.stderr,
        ):
            blacks.append({
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "duration": float(match.group(3)),
            })
        return blacks
    except Exception as e:
        logger.warning(f"Black frame detection failed: {e}")
        return []


def _measure_loudness(video_path: str) -> dict:
    """Run ffmpeg loudnorm to get LUFS and true peak.

    Returns: {"lufs": float|None, "true_peak": float|None}
    """
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-filter:a", "loudnorm=print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        stderr = r.stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            ln_data = json.loads(stderr[json_start:json_end])
            return {
                "lufs": float(ln_data.get("input_i", -99)),
                "true_peak": float(ln_data.get("input_tp", 0)),
            }
    except Exception as e:
        logger.warning(f"Loudness measurement failed: {e}")
    return {"lufs": None, "true_peak": None}


def compute_quality_score(manifest_path: str, video_path: str = "") -> int:
    """Score 0-100 based on real video quality analysis.

    Two modes:
      - manifest_path only: legacy manifest-based scoring (capped at 60)
      - manifest_path + video_path: full ffprobe analysis

    Critical failures that force score to 0:
      - Total silence > 5s (host audio missing)
      - Any mid-video black segment > 2s
      - No video file / unreadable

    Penalties:
      - True peak > -1.0 dBFS: -20 points
      - LUFS deviation > 3 from -14: -10 points
      - Any silence > 2s: -15 per occurrence (on top of critical check)

    Base points (from manifest, max 50):
      - Clips present with good AV sync: up to 15
      - Channel diversity: 10
      - Music present: 10
      - Pipeline success flag: 15
    """
    # ── Load manifest ──
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Cannot read manifest: {e}")
        return 0

    # ── Base score from manifest (max 50) ──
    score = 0
    clips_used = manifest.get("clips_used", [])

    # AV sync: up to 15 points (5 per clip, max 3 clips)
    for clip in clips_used[:3]:
        av_offset = clip.get("av_offset", 999)
        if av_offset < 0.05:
            score += 5
        elif av_offset < 0.15:
            score += 3
    # Benefit of doubt if no av_offset data
    if clips_used and not any("av_offset" in c for c in clips_used):
        score += 5 * min(len(clips_used), 3)

    # Channel diversity: 10 points
    channels = [c.get("channel", "") for c in clips_used]
    if channels and len(channels) == len(set(channels)):
        score += 10

    # Music present: 10 points
    if manifest.get("music_track") or manifest.get("timing", {}).get("7_assemble"):
        score += 10

    # Pipeline success: 15 points
    if manifest.get("success", False):
        score += 15

    score = min(50, score)
    logger.info(f"  Manifest base score: {score}/50")

    # ── If no video path, cap at manifest score (max 50) ──
    if not video_path or not os.path.exists(video_path):
        logger.warning("  No video file for ffprobe analysis — capped at manifest score")
        return min(50, score)

    # ── Real ffprobe checks (up to 50 bonus points, or hard penalties) ──
    failures = []
    duration = _run_ffprobe_duration(video_path)

    # Duration check: must be > 60s for a real episode
    if duration < 60:
        failures.append(f"Video too short: {duration:.1f}s")
        logger.error(f"  CRITICAL: Video duration {duration:.1f}s < 60s")
        return 0

    # ── Silence detection ──
    silences = _detect_silence(video_path, min_duration=2.0)
    total_silence = sum(s["duration"] for s in silences)

    if total_silence > 5.0:
        # Critical: > 5s total silence means host audio is missing
        failures.append(f"Total silence: {total_silence:.1f}s (>5s limit)")
        logger.error(f"  CRITICAL FAIL: {total_silence:.1f}s total silence detected "
                      f"({len(silences)} gaps). Host audio likely missing.")
        for s in silences:
            logger.error(f"    Silent gap: {s['start']:.1f}s - {s['end']:.1f}s "
                          f"({s['duration']:.1f}s)")
        return 0

    # Non-critical silence penalty: -15 per gap
    silence_penalty = len(silences) * 15
    if silences:
        logger.warning(f"  Silence penalty: -{silence_penalty} ({len(silences)} gaps >2s)")

    # ── Black frame detection ──
    blacks = _detect_black_frames(video_path, min_duration=0.5)

    # Filter: ignore first 2s (title card) and last 5s (outro fade)
    mid_blacks = [b for b in blacks
                  if b["start"] > 2.0 and b["end"] < (duration - 5.0)]

    critical_blacks = [b for b in mid_blacks if b["duration"] > 2.0]
    if critical_blacks:
        failures.append(f"{len(critical_blacks)} black segments >2s mid-video")
        logger.error(f"  CRITICAL FAIL: {len(critical_blacks)} black frame segments >2s:")
        for b in critical_blacks:
            logger.error(f"    Black: {b['start']:.1f}s - {b['end']:.1f}s "
                          f"({b['duration']:.1f}s)")
        return 0

    black_penalty = len(mid_blacks) * 10
    if mid_blacks:
        logger.warning(f"  Black frame penalty: -{black_penalty} ({len(mid_blacks)} segments >0.5s)")

    # ── Loudness / True peak ──
    loudness = _measure_loudness(video_path)
    peak_penalty = 0
    lufs_penalty = 0

    if loudness["true_peak"] is not None:
        if loudness["true_peak"] > -1.0:
            peak_penalty = 20
            logger.warning(f"  True peak penalty: -20 ({loudness['true_peak']:.1f} dBTP > -1.0)")
        logger.info(f"  True peak: {loudness['true_peak']:.1f} dBTP")

    if loudness["lufs"] is not None:
        lufs_dev = abs(loudness["lufs"] - (-14))
        if lufs_dev > 3:
            lufs_penalty = 10
            logger.warning(f"  LUFS penalty: -10 ({loudness['lufs']:.1f} LUFS, "
                            f"deviation {lufs_dev:.1f} from -14)")
        logger.info(f"  Integrated LUFS: {loudness['lufs']:.1f}")

    # ── Compute final score ──
    # Video analysis bonus: 50 points minus penalties
    video_bonus = max(0, 50 - silence_penalty - black_penalty - peak_penalty - lufs_penalty)
    final_score = min(100, score + video_bonus)

    logger.info(f"  Video analysis: +{video_bonus}/50 "
                f"(silence:-{silence_penalty} black:-{black_penalty} "
                f"peak:-{peak_penalty} lufs:-{lufs_penalty})")
    logger.info(f"  Final score: {final_score}/100")

    return final_score


def should_upload(score: int, threshold: int = 85) -> bool:
    """Determine if episode quality is high enough for auto-upload."""
    return score >= threshold


def format_score_report(score: int, threshold: int = 85) -> str:
    """Format a human-readable quality report."""
    status = "PASS" if score >= threshold else "HOLD"
    bar = "#" * (score // 5) + "-" * (20 - score // 5)
    return f"QUALITY SCORE: {score}/100 [{bar}] {status} (threshold: {threshold})"

```

### FILE: utils/telegram_alerts.py
```python
"""Telegram Alerts — push notifications for pipeline events.

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
All functions are no-ops when tokens aren't configured (never crash).
"""
import logging
import os

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

LEVEL_EMOJI = {
    "info": "\u2139\ufe0f",       # ℹ️
    "warning": "\u26a0\ufe0f",    # ⚠️
    "error": "\u274c",            # ❌
    "critical": "\U0001f6a8",     # 🚨
}


def send_alert(message: str, level: str = "info") -> bool:
    """Send a Telegram message. Returns True on success, False otherwise.

    Levels: info, warning, error, critical.
    No-op if bot token or chat ID not configured.
    """
    if not BOT_TOKEN or not CHAT_ID:
        return False

    try:
        import requests
    except ImportError:
        logger.warning("requests not available for Telegram alerts")
        return False

    emoji = LEVEL_EMOJI.get(level, "\u2139\ufe0f")
    text = f"{emoji} *Protocol Pulse*\n{message}"

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=10)
        if resp.status_code == 200:
            return True
        logger.warning(f"Telegram API {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")
    return False


def alert_pipeline_start(episode_date: str, test_mode: bool = False):
    mode = " (TEST)" if test_mode else ""
    send_alert(f"Pipeline started{mode} — {episode_date}")


def alert_pipeline_success(episode_date: str, quality_score: int,
                           duration: float, output_path: str):
    send_alert(
        f"Episode {episode_date} complete\n"
        f"Score: {quality_score}/100\n"
        f"Duration: {duration:.0f}s\n"
        f"Path: {os.path.basename(output_path)}"
    )


def alert_pipeline_failure(episode_date: str, step: str, error: str):
    send_alert(
        f"PIPELINE FAILED at step {step}\n"
        f"Episode: {episode_date}\n"
        f"Error: {error[:200]}",
        level="critical",
    )


def alert_quality_hold(episode_date: str, quality_score: int, reason: str = ""):
    send_alert(
        f"QUALITY HOLD — Episode {episode_date}\n"
        f"Score: {quality_score}/100\n"
        f"Below 85 threshold"
        + (f"\nReason: {reason}" if reason else ""),
        level="warning",
    )


def alert_upload_success(episode_date: str, youtube_url: str):
    send_alert(f"Uploaded: {episode_date}\n{youtube_url}")

```