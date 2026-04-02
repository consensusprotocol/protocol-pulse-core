CRITICAL VIDEO FIXES — 10 issues from PBX production review.
Read PIPELINE_LAWS.md and ~/protocol_pulse/PRODUCTION_DESIGN_LAWS.md before writing code.
Take your time. Do this RIGHT. Do not rush. Each fix must be verified.

=== ISSUE 1: INTRO PLAYS TWICE + LOGO STILL SHOWING ===
The cold open narrator hook plays TWICE at the start of the video.
The logo intro STILL plays before the content.

Fix in assembler.py:
- Remove TitleCard from the beginning entirely. The episode starts with the
  cold open narrator hook + PiP preview. Period.
- Find where parts are being duplicated. Search for where cold_open or intro
  parts are added to the parts list. There's likely a double-append bug.
- Verify: The first frame of the video should be the PiP preview + narrator voice.
  No logo. No title card. No duplication.

=== ISSUE 2: PiP PREVIEW LAYOUT — BLOCKING TEXT + PULSE ===
Current: PiP preview is right-side but overlaps narrator text and pulse animation.
The text subtitle is center-aligned and runs into the PiP frame.

Fix the narrator segment visual layout:
  LEFT 55% of frame (x=0 to x=1056):
    - Pulse waveform animation: centered in this zone, y=340, 600px wide
    - Subtitle text: centered in this zone, y=440, max-width 900px, word-wrapped
      Font: white, Inter, 28px. NEVER extend past x=1000.
  RIGHT 40% of frame (x=1056 to x=1920):
    - PiP preview: positioned at x=1056, y=200, size 820x462 (16:9)
    - "COMING UP..." label: inside PiP, bottom-left, bold white, 32px
    - Thin elegant border: 2px white at 30% opacity
  BOTTOM BAR: full width, gold ticker, same as current

This creates a clean split-screen: narration content left, preview right.
No overlap. No blocking.

=== ISSUE 3: CLIPS STILL CUTTING MID-SENTENCE ===
This has been flagged 3 times. The current sentence-boundary detection is not working.

Root cause analysis needed. Check clip_extractor.py:
  grep -n 'sentence\|boundary\|period\|silence' clip_extractor.py

The fix must be bulletproof:
1. When extracting a clip, get the timestamped transcript for the full video
2. Find the selected start timestamp
3. Walk BACKWARDS through the transcript to find the nearest sentence end
   (period, question mark, exclamation mark followed by >=0.3s gap)
4. Set clip start to the NEXT word after that sentence end
5. For clip END: walk FORWARDS from the selected end timestamp to find the
   nearest sentence end. Extend the clip to include the complete sentence.
6. Maximum extension: 5 seconds in either direction
7. If no sentence boundary found within 5 seconds, use the original timestamp
   but log: "WARNING: No sentence boundary found, using raw timestamp"

Add a dedicated function:
def find_sentence_boundary(timestamped_text, target_time, direction='backward', max_search_seconds=5):
    '''Find nearest sentence ending (. ? !) relative to target_time.
    direction: 'backward' for clip start, 'forward' for clip end.
    Returns adjusted timestamp.'''

=== ISSUE 4: PiP PREVIEW SHOWS BEFORE NARRATOR PIVOTS ===
During the "handoff" where narrator 2 responds to narrator 1 about the PREVIOUS clip,
the NEXT clip's PiP preview is already visible. Confusing.

Fix: The PiP preview for clip N should ONLY appear when the narrator begins discussing
clip N's topic. Not during the reaction to clip N-1.

Implementation in assembler.py:
- Tag each narration segment as either "reaction" (discussing previous clip) or
  "setup" (introducing next clip)
- Script writer already tags [NARRATION] — add sub-tags:
  [NARRATION:REACT] — reacting to previous clip, show PREVIOUS clip thumbnail (small, top-right)
  [NARRATION:SETUP] — introducing next clip, show NEXT clip PiP preview (large, right panel)
- If sub-tag not available, use heuristic: first narrator turn after a clip = REACT,
  second narrator turn = SETUP

=== ISSUE 5: TWEET MISMATCH — SAYLOR NARRATION, POMPLIANO CARD ===
This has been flagged THREE TIMES. Still broken.

FORENSIC DEBUG required. In daily_producer.py and assembler.py:
1. Print the EXACT social_posts list when passed to script_writer
2. Print the EXACT social_posts list when passed to assembler
3. Compare the two. They MUST be identical in order.

The root cause is likely:
a) social_posts is being sorted/shuffled between the two calls, OR
b) The script writer receives posts in one order but the assembler
   iterates them differently (e.g., by index vs by some other key)

Fix: In daily_producer.py, create a SINGLE sorted list ONCE:
  social_posts_ordered = sorted(social_posts, key=lambda p: p.get('likes', 0), reverse=True)
  # FREEZE this order — pass the SAME list to both systems
  # Add index to each: social_posts_ordered[i]['display_order'] = i

In assembler.py social card renderer:
  # Sort by display_order before rendering
  posts = sorted(posts, key=lambda p: p.get('display_order', 0))

In script_writer.py:
  # Pass posts with display_order, ensure Claude writes narration in that order

Add logging:
  logger.info(f"SOCIAL POST ORDER CHECK:")
  for i, p in enumerate(social_posts_ordered):
      logger.info(f"  #{i}: @{p['handle']} — {p['text'][:40]}")

=== ISSUE 6: ACTUAL TWEET SCREENSHOTS ===
Playwright + Chromium are installed on Ultron. utils/tweet_screenshot.py exists.
But it's NOT being used in the video pipeline.

Wire it into assembler.py:
When building a social card, check if tweet_url is available.
If yes: capture screenshot via tweet_screenshot.py
  screenshot = capture_tweet(tweet_url, f"cache/tweet_{handle}.png")
If screenshot succeeds: overlay the screenshot image on the Remotion SocialCard
  background INSTEAD of the text-only card.
If screenshot fails: fall back to text-only Remotion SocialCard.

The screenshot should be cropped, scaled to fit the card area (1100x260),
and positioned inside the card container with the glassmorphism border.

=== ISSUE 7: NO BACKGROUND MUSIC ===
34 music files exist at assets/music/ but are NOT being mixed into the final output.

FORENSIC DEBUG:
  grep -n 'music\|mix_music\|music_bed\|MUSIC\|select_music\|mood' assembler.py | head -20
  
Find where the music mixing function is defined and where it's called.
If it's never called, wire it in.
If it's called but failing silently, add error logging.

Music rules per PRODUCTION_DESIGN_LAWS Section 3:
- Select mood-appropriate track from assets/music/
- Mix at -20dB under ALL narration segments
- Full volume first 3 seconds (title moment), then duck
- MUTE during partner clips (let clip audio breathe)
- Fade back in when narration resumes
- Different track at halfway point if episode > 8 minutes

=== ISSUE 8: OUTRO "STAY SOVEREIGN" VOICE MISSING ===
The closing line should be spoken by the narrator as the outro plays.
Add to script_writer.py episode arc:
  The LAST line is always: [WARM] "Stay sovereign. This has been Protocol Pulse."
  This is NOT optional. It is the brand signoff.

In assembler.py:
  The final narration segment (the wrap) must include this line.
  It plays OVER the outro visual (logo animation or branded clip).
  If no outro visual exists, play it over the cyberpunk background.

=== ISSUE 9: CYBERPUNK BACKGROUND STILL NOT VISIBLE ===
The narrator segments still show plain black background, not the
cyberpunk_loop.mp4 animated background.

Verify: ls -la assets/backgrounds/cyberpunk_loop.mp4
If it exists, check assembler.py for where it's supposed to be used.
Grep: grep -n 'cyberpunk\|background.*loop\|bg_loop' assembler.py

The cyberpunk background should be the BASE LAYER for ALL narrator segments.
All other elements (waveform, text, PiP) overlay on top of it.
Use FFmpeg: -stream_loop -1 -i cyberpunk_loop.mp4 as the first input,
then overlay everything else.

=== ISSUE 10: VIDEO CLIP QUALITY ENFORCEMENT ===
The clip quality was good this time. Lock it in as a HARD rule.

In clip_extractor.py, after downloading a clip:
  bitrate = get_bitrate(clip_path)  # ffprobe
  if bitrate < 3_000_000:  # 3 Mbps minimum
      logger.warning(f"LOW QUALITY: {channel} clip at {bitrate/1e6:.1f}Mbps")
      # Try re-downloading with explicit quality:
      # yt-dlp -f 'bestvideo[height>=720]+bestaudio' ...
  if bitrate < 1_500_000:  # 1.5 Mbps absolute floor
      logger.error(f"REJECTED: {channel} clip at {bitrate/1e6:.1f}Mbps — below 1.5Mbps floor")
      return None  # Reject clip, select replacement

AFTER ALL 10 FIXES:
1. Run bash regression_test.sh — must pass
2. Do NOT render a new video yet. Just commit all fixes.
3. Git push origin main
4. Report which fixes were applied and how they were verified

Take your time. Each fix must be individually verified before moving to the next.
PBX explicitly said: do not rush, do this right.