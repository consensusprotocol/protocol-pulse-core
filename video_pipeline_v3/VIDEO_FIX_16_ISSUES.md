CRITICAL VIDEO PIPELINE FIX SESSION. Read ALL of these before writing any code:
1. PIPELINE_LAWS.md (all sections)
2. ~/protocol_pulse/PRODUCTION_DESIGN_LAWS.md (the ENTIRE document)
3. PIPELINE_FORENSIC_AUDIT.md

PBX just reviewed the production render and found 16 issues. EVERY SINGLE ONE must be fixed.
Do NOT skip any. Do NOT claim done without proof.

=== ISSUE 1: OPENING — SKIP LOGO, START WITH HOOK ===
Per PRODUCTION_DESIGN_LAWS Section 1: the cold open starts at 0:00 with the most shocking moment.
NO logo intro first. The TitleCard plays AFTER the cold open hook (at ~8 seconds).
Current: Logo with black frame box plays first → wrong.
Fix assembler.py episode assembly order:
  1. Cold open narrator hook (with PiP preview of first clip) → FIRST
  2. TitleCard (4 seconds, Remotion) → SECOND
  3. Then into Segment 1

=== ISSUE 2: PiP PREVIEW — TOO SMALL, BADLY POSITIONED, STATIC ===
Current: Small static thumbnail in bottom-right corner with pan effect.
Required: Larger size (40% of frame width, ~768x432), positioned center-right.
Must be ACTUAL VIDEO playing (muted), not a static image with pan.
FFmpeg: Extract 8 seconds of actual video, scale to 768x432, overlay at x=1100, y=350.
Add elegant thin border: pad filter with 2px white at 20% opacity.
Add subtle drop shadow (drawbox behind at +4px offset, black at 30%).

=== ISSUE 3: CUSTOM WHOOSH SOUND ===
PBX is uploading custom whoosh to: assets/sfx/custom_whoosh.mp3
Check if it exists: ls assets/sfx/custom_whoosh.mp3
If it exists, use it for ALL transitions instead of the generated pink noise whoosh.
If it doesn't exist yet, use a placeholder but log: "CUSTOM WHOOSH NOT FOUND — using generated"
Convert to wav for consistency: ffmpeg -i assets/sfx/custom_whoosh.mp3 assets/sfx/custom_whoosh.wav

=== ISSUE 4: CLIPS START MID-SENTENCE ===
The clip_extractor is cutting in at the wrong timestamp.
Fix: When extracting a clip segment, scan backwards from the selected start time to find
the beginning of the sentence. Use the timestamped transcript to find the nearest sentence
boundary BEFORE the selected moment. A sentence boundary = a period, question mark, or
exclamation mark followed by a pause of 0.5+ seconds.
The clip should START at the beginning of the relevant sentence, not mid-thought.

=== ISSUE 5: AD READ IN UNCHAINED CLIP ===
The ad read double gate (PIPELINE_LAWS Section 15) is not catching this.
Add more patterns to AD_READ_PATTERNS in clip_extractor.py:
  "unchained.com", "unchained capital", "collaborative custody",
  "swan bitcoin", "river.com", "fold app", "cash app",
  "strike app", "download the app", "link in description"
Also: after clip extraction, do a SECOND pass: scan the extracted clip's transcript
for any ad read pattern. If found, log and reject the clip, select next best.

=== ISSUE 6: CLIPS END ABRUPTLY ===
The silence detection should prevent this (V11 fix).
Verify silence detection is still active: grep 'silencedetect' clip_extractor.py
If the feature flag silence_detection is FALSE, flip it to TRUE.
Increase end padding from 8s to 10s to give more room for natural pauses.

=== ISSUE 7: CHANNEL DEDUP BROKEN ===
The production render has TWO Natalie Brunell clips. This violates the 5-clip rule.
Fix clip_selector.py: After Claude selects clips, ENFORCE unique channels in Python:
  seen_channels = set()
  deduped = []
  for clip in sorted_clips:
      if clip["channel"] not in seen_channels:
          seen_channels.add(clip["channel"])
          deduped.append(clip)
  if len(deduped) < 5:
      logger.error(f"DEDUP: Only {len(deduped)} unique channels. Need replacement clips.")
  selected_clips = deduped[:5]
This must be AFTER the LLM selection, as a hard enforcement layer.

=== ISSUE 8: ALPHA TRANSITIONS STILL STATIC FRAMES ===
The alpha transitions are being inserted as their own concat segment (hard cut in, hard cut out)
instead of being OVERLAID between outgoing and incoming clips.
Fix assembler.py concatenate logic:
  Instead of: [clip1.mp4] [transition.mp4] [clip2.mp4]
  Do: Overlap the last 30 frames of clip1 with the first 30 frames of clip2,
  with the alpha transition composited on top.
  FFmpeg: Use xfade filter with custom transition, OR:
  - Extend clip1 by 1 second, extend clip2 to start 1 second early
  - Overlay transition.mov (with alpha) on the overlap region
  If alpha compositing is too complex, use FFmpeg xfade:
  ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex "xfade=transition=fade:duration=1:offset={clip1_duration-1}" output.mp4

=== ISSUE 9: TWEET CARD MISMATCH (FIRST CARD ALWAYS WRONG) ===
The first social card always shows wrong tweet (Pompliano) while narrator reads Saylor.
Root cause: The social posts list is being passed in different orders to:
  a) script_writer.py (generates narration order)
  b) assembler social card renderer (renders visual order)
Fix: In daily_producer.py, when passing social_posts to both systems,
use the EXACT SAME list in the EXACT SAME order. Sort by engagement (likes) descending
ONCE, then pass that sorted list to both script writer and assembler.
Add logging: "SOCIAL ORDER: #{i}: @{handle} — {text[:40]}"

=== ISSUE 10: TWEET CARDS GO BLACK THEN RETURN ===
The Remotion SocialCard durationInFrames is shorter than the audio segment.
When the Remotion video ends but audio continues, the frame goes black.
Fix: durationInFrames = int(math.ceil(audio_duration * 30)) + 30  (add 1 second buffer)
Never let durationInFrames be shorter than the audio.

=== ISSUE 11: FEMALE VOICE — SWAP TO VALLEY GIRL ===
PBX wants to try Natasha Valley Girl: uxKr2vlA4hYgXZR1oPRT
But this voice returned 404 last time (not on the ElevenLabs account).
First: Check if it's available now by making a test API call.
If available: use Natasha with stability 0.38, similarity 0.78, style 0.20, speed 1.12
If NOT available: Search the voice library API for "valley girl" or "energetic" female voices.
  ElevenLabs API: GET /v1/voices with search
  Pick the most energetic, confident young female voice that IS available.
Report which voice was selected and its ID.

=== ISSUE 12: NO BACKGROUND MUSIC ===
34 music files exist at assets/music/ but are NOT being mixed in.
Audit: grep -n 'music\|mix_music\|music_bed\|mood_music' assembler.py daily_producer.py
Find where music mixing broke. The feature flag mood_music is TRUE.
Fix: Ensure the mood-selected track is mixed at -20dB under ALL narration segments.
Music should fade in at episode start, duck under clips, return under narration.

=== ISSUE 13: VOICE WAVEFORM ANIMATION MISSING ===
The Remotion WaveformVisualizer heartbeat animation should appear during narrator segments.
It should be positioned to the LEFT side of the PiP preview video, not blocking it.
Layout for narrator segments:
  Left 60% of frame: Cyberpunk background + waveform (bottom-third) + subtitle text
  Right 40% of frame: PiP preview video of upcoming clip
  Bottom bar: Gold ticker (full width)

=== ISSUE 14: PULSE ANIMATION POSITIONING ===
The heartbeat pulse is cool but shouldn't block the PiP preview.
Position it: center-left of frame, vertically centered, 600px wide.
The PiP preview goes to the right of it.

=== ISSUE 15: VIDEO QUALITY OF CLIPS ===
Bitcoin Magazine clip is only 4.4MB for a 40-second clip. That's ~880kbps — way too low.
The yt-dlp format selector IS correct (bestvideo+bestaudio).
Possible issue: the channel might only have low-quality uploads.
Add a quality check AFTER download:
  ffprobe the downloaded clip. If bitrate < 2Mbps, log warning:
  "LOW QUALITY SOURCE: {channel} clip at {bitrate}Mbps — below 2Mbps threshold"
  Consider using a different clip from a higher-quality channel.

=== ISSUE 16: CYBERPUNK BACKGROUND ===
Verify the Remotion CyberpunkBackground loop is actually being used as the base layer
for narration segments. If not, wire it: loop cyberpunk_loop.mp4 as the background,
overlay waveform + PiP + text on top.

AFTER ALL 16 FIXES:
1. Run bash regression_test.sh
2. Clear clip cache: rm -rf cache/clips/* 2>/dev/null
3. Run PRODUCTION render: python3 daily_producer.py (no --test flag)
4. Verify: 5 clips from 5 different channels, no ad reads, no mid-sentence starts
5. Report SCP path + all validation metrics
6. Git push origin main

DO NOT STOP until all 16 issues are addressed and verified.