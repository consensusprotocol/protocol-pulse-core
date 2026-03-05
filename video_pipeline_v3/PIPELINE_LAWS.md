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
- [ ] No other Claude Code session writing to video_pipeline_v3/

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
- E1: One Claude Code session writing to video_pipeline_v3/ at a time.
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
