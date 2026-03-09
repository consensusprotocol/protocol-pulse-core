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
