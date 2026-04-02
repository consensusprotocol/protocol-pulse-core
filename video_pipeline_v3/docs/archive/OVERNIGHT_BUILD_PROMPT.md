You are executing a COMPLETE PRODUCTION REBUILD of the Protocol Pulse video pipeline. This is an overnight autonomous session. Work through ALL phases sequentially. Do not stop until Phase 3 is complete and a final test render passes all quality checks.

BEFORE WRITING ANY CODE, read these documents completely:
1. PIPELINE_LAWS.md (all sections including 19 and 20)
2. Read ~/protocol_pulse/PRODUCTION_DESIGN_LAWS.md (the entire document — this is the scientific foundation for everything you build)
3. PIPELINE_FORENSIC_AUDIT.md

The PRODUCTION_DESIGN_LAWS.md contains research-backed rules for episode structure, visual pacing, sound design, the face rule, anti-AI-detection, and thumbnail rules. Every build decision must trace back to a rule in that document.

=======================================================================
PHASE 1: REMOTION COMPONENT REBUILD (~2 hours)
=======================================================================

All components in remotion/src/compositions/. Use brand.ts for ALL colors.
Test render EACH component individually before moving to Phase 2.

COMPONENT A — CyberpunkBackground.tsx (NEW):
10-second seamless loop, 1920x1080, 30fps.
- Background: Animated dark gradient mesh. Use Remotion interpolate() to slowly
  shift a radial gradient position over the loop duration. Colors: #0A0A0A to #0D0D0D.
- Floating particles: 8-12 tiny circles, BRAND.RED at 10-15% opacity.
  Each particle has independent x/y drift using sine waves with different frequencies.
  Speed: very slow (full screen traverse in ~30 seconds). Particles wrap around edges.
- Grid lines: Faint perspective grid (like Tron), 2% opacity, BRAND.RED.
  Lines converge toward a vanishing point slightly above center.
  Grid slowly drifts forward (parallax motion toward viewer).
- Scan line: Single horizontal line, BRAND.RED at 8% opacity, 2px height.
  Sweeps slowly top-to-bottom over 8 seconds, then resets.
- Noise texture: SVG noise filter at 3% opacity overlaid on everything.
- Must loop SEAMLESSLY (frame 0 and frame 299 must match perfectly).

Render: npx remotion render src/index.tsx CyberpunkBackground --output-location=../assets/backgrounds/cyberpunk_loop.mp4 --props='{"durationInFrames":300}'
Verify: Play and confirm seamless loop. No visible jump at loop point.
Commit: git add remotion/src/compositions/CyberpunkBackground.tsx assets/backgrounds/ -m 'feat: CyberpunkBackground — animated loop with particles, grid, scanline'

COMPONENT B — WaveformVisualizer.tsx (REBUILD):
Per PRODUCTION_DESIGN_LAWS Section 2: narration visual stack.
NO LOGO in this component (logo restraint rule — max 3 appearances per episode).
- Background: Transparent (this overlays on CyberpunkBackground in assembler)
  OR render with CyberpunkBackground composited in for standalone use.
- Waveform: Stylized heartbeat/EKG line matching the Protocol Pulse logo aesthetic.
  Main line: BRAND.RED, 3px stroke, smooth bezier curves.
  NOT raw audio data. DESIGNED waveform: flatline → gradual peaks → sharp spike → decay → flatline.
  Animation: draws left-to-right over the full duration, synchronized loosely to speech cadence.
  Width: 800px centered. Height: 50px.
- Neon glow: Duplicate the SVG path, apply CSS filter blur(6px), opacity 0.4, BRAND.RED.
  Creates a neon tube effect behind the crisp line.
- Traveling dot: 6px circle, BRAND.WHITE, follows the path position.
  Subtle trail effect (2-3 previous positions at decreasing opacity).
- Mirror reflection: Same path flipped below, opacity 0.15, blur(2px).
- Bottom info bar: Full width, 44px, bg rgba(10,10,10,0.9), top border 1px BRAND.BORDER.
  Text: "PROTOCOL PULSE  |  PULSE CHECK  |  BTC $72,285  |  PROTOCOLPULSE.IO"
  Font: JetBrains Mono, 13px, BRAND.GOLD (#FFCC00), letter-spacing 2px, centered.

Props: { title: string, btcPrice: string, date: string, durationInFrames: number }

Render test: npx remotion render src/index.tsx WaveformVisualizer --output-location=../test_outputs/waveform.mp4 --props='{"title":"Bitcoin Daily Brief","btcPrice":"$72,285","date":"March 5, 2026","durationInFrames":150}'
Commit: git add remotion/src/compositions/WaveformVisualizer.tsx -m 'feat: WaveformVisualizer v2 — neon heartbeat, traveling dot, gold bar, no logo'

COMPONENT C — SocialCard.tsx (REBUILD):
Fix: durationInFrames MUST match actual audio duration. Never hardcode frame count.
- Background: CyberpunkBackground (import or render separately and composite)
- Header: "WHAT THE BITCOIN INTERNET IS SAYING" — BRAND.RED, 26px, Inter Bold, centered.
  Fade in at frame 0-10.
- Card container: 1100x260, centered vertically.
  Background: rgba(12,12,12,0.92).
  Border: 2px BRAND.RED outer. 1px BRAND.DARK_RED inner (double border glow simulation).
  Rounded corners: 8px.
- Animated scanlines INSIDE the card only: horizontal 1px lines every 4px, BRAND.RED at 4% opacity.
  Scroll upward at 1px per frame.
- Pulse dot: 8px circle, BRAND.RED, top-left inside card (8px margin).
  Opacity oscillates: 0.3 → 1.0 → 0.3 over 1 second cycle using interpolate + sine.
- Handle: "@saylor" — BRAND.RED, monospace (JetBrains Mono), 22px, top-left after pulse dot.
- Tweet text: BRAND.WHITE (#EDEDED), Inter, 24px, max 3 lines, word-wrapped.
  Below handle, 16px padding.
- Engagement: "♥ 65,156  |  ↻ 6,918" — BRAND.LIGHT_RED for hearts, #888888 for RTs.
  Bottom-left of card, 16px, monospace.
- "via X" — #555555, 13px, bottom-right of card.
- Animation: Card slides up from +100px translateY to 0 + opacity 0→1 over 12 frames (0.4s).
  Card holds for remaining duration.
  Last 10 frames: opacity 1→0 fade out.
- Bottom bar: Same gold bar as WaveformVisualizer.

Props: { handle: string, text: string, likes: number, retweets: number, durationInFrames: number }

Render test: npx remotion render src/index.tsx SocialCard --output-location=../test_outputs/social.mp4 --props='{"handle":"saylor","text":"I'\''m buying bitcoin right now. Are you?","likes":32171,"retweets":2554,"durationInFrames":150}'
Commit: git add remotion/src/compositions/SocialCard.tsx -m 'feat: SocialCard v2 — fixed duration, scanlines, pulse dot, slide animation'

COMPONENT D — TitleCard.tsx (REBUILD):
This is the ONE segment where the logo appears prominently.
- Duration: 120 frames (4 seconds).
- Background: Dark radial gradient with subtle red light source that slowly moves.
  Center: #0C0808, edges: #020202. Red accent light at 5% intensity.
- Frame 0-30: Logo fades in. Use ../assets/logo_protocol_pulse.png.
  Since the logo has a black background (it's actually JPEG), use chromakey/colorkey
  to remove the black: detect if the image is JPEG and apply removal.
  OR just overlay it on the dark background where black blends naturally.
  Size: 300px height, centered.
  Scale animation: 0.85 → 1.0 with spring easing.
  Subtle glow: drop-shadow 0 0 30px rgba(204,0,0,0.3).
- Frame 40-60: Episode title fades in below logo.
  White (#EDEDED), Inter Bold, 32px, letter-spacing 1px.
  SlideUp: translateY 15→0.
- Frame 65-80: Date + "PULSE CHECK" in BRAND.RED, 16px, fades in below title.
- Frame 80-110: Red EKG pulse line sweeps across bottom 200px of frame.
  SVG path animation: flatline → sharp peak → decay → flatline.
  Draws left-to-right over 1 second.
  BRAND.RED, 3px stroke, with glow (blur copy).
- Frame 110-120: Everything holds, slight overall fade begins.
- Audio: Generate 2 heartbeat thumps + low synth pad:
  ffmpeg -f lavfi -i "sine=frequency=60:duration=4,afade=t=in:d=0.1,afade=t=out:st=3.5:d=0.5" -f lavfi -i "sine=frequency=80:duration=0.15,afade=t=out:d=0.15" -filter_complex "[0][1]amix=inputs=2:duration=first" -ar 44100 -ac 2 ../assets/sfx/title_heartbeat.wav

Render: npx remotion render src/index.tsx TitleCard --output-location=../test_outputs/title.mp4 --props='{"title":"Bitcoin Daily Brief — March 5, 2026","date":"March 5, 2026","durationInFrames":120}'
Commit: git add remotion/src/compositions/TitleCard.tsx assets/sfx/title_heartbeat.wav -m 'feat: TitleCard v2 — animated logo, EKG pulse, heartbeat SFX'

COMPONENT E — LowerThird.tsx (REBUILD):
Alpha channel overlay for partner clip identification.
- Background: Transparent (render with alpha for overlay compositing).
  If ProRes 4444 is needed: --codec=prores --prores-profile=4444
- Position: bottom 100px of 1920x1080 frame.
- Gradient bar: left-to-right, transparent → rgba(0,0,0,0.85) from x=0 to x=600.
- Small Protocol Pulse logo: 50px height, 40% opacity, positioned at x=30, vertically centered.
  (This is one of the 3 allowed logo appearances per episode)
- Channel name: White, Inter Bold, 20px, positioned at x=95.
- Speaker name (if provided): BRAND.RED, Inter, 16px, below channel name.
- Animation: Slide in from left (translateX -200→0) over 10 frames (0.33s).
  Hold for duration minus 16 frames.
  Fade out over last 6 frames.

Props: { channelName: string, speakerName?: string, durationInFrames: number }

Render: npx remotion render src/index.tsx LowerThird --output-location=../test_outputs/lower.mov --codec=prores --prores-profile=4444 --props='{"channelName":"Simply Bitcoin","speakerName":"Nico Moran","durationInFrames":180}'
Commit: git add remotion/src/compositions/LowerThird.tsx -m 'feat: LowerThird v2 — alpha overlay, logo (50px), slide animation'

COMPONENT F — GlitchTransition.tsx (REBUILD):
Alpha channel transition. 1 second duration.
- Duration: 30 frames (1 second at 30fps).
- Background: Transparent (alpha channel).
- Effect: Cyberpunk data-glitch reveal.
  - Frame 0-5: Red scan lines begin sweeping left-to-right. Each line is 2-4px tall.
    Lines are staggered (different start times). Color: BRAND.RED.
  - Frame 5-20: As scan lines pass, they leave transparency (alpha=0) behind them.
    Red glitch pixel blocks appear randomly in the swept area (8x8px, BRAND.RED, random positions).
    Brief white flash at frame 12 (full frame, opacity 0.15, 1 frame only).
  - Frame 20-25: Most of frame is transparent. Residual glitch particles fade out.
  - Frame 25-30: Fully transparent. Clean transition complete.
- The assembler composites this between outgoing and incoming clips:
  Outgoing clip plays → transition overlay starts → transparent areas reveal incoming clip.

Render: npx remotion render src/index.tsx GlitchTransition --output-location=../assets/transitions/glitch_alpha.mov --codec=prores --prores-profile=4444
Commit: git add remotion/src/compositions/GlitchTransition.tsx assets/transitions/glitch_alpha.mov -m 'feat: GlitchTransition v2 — 1s alpha reveal with scan lines'

COMPONENT G — Sound Effects (assets/sfx/):
Generate ALL required SFX:

1. Transition whoosh (already may exist, regenerate at 1.0s):
   ffmpeg -f lavfi -i "anoisesrc=d=1.0:c=pink:r=44100,afade=t=in:d=0.05,afade=t=out:st=0.7:d=0.3,highpass=f=1500,lowpass=f=8000" -ar 44100 -ac 2 assets/sfx/glitch_whoosh.wav

2. Card swoosh (0.4s, subtle):
   ffmpeg -f lavfi -i "anoisesrc=d=0.4:c=pink:r=44100,afade=t=in:d=0.03,afade=t=out:st=0.2:d=0.2,highpass=f=2000,lowpass=f=6000,volume=0.4" -ar 44100 -ac 2 assets/sfx/card_swoosh.wav

3. Data blip (0.2s):
   ffmpeg -f lavfi -i "sine=frequency=1200:duration=0.2,afade=t=in:d=0.02,afade=t=out:st=0.1:d=0.1,volume=0.3" -ar 44100 -ac 2 assets/sfx/data_blip.wav

4. Lower third slide (0.3s):
   ffmpeg -f lavfi -i "anoisesrc=d=0.3:c=white:r=44100,afade=t=in:d=0.02,afade=t=out:st=0.15:d=0.15,highpass=f=3000,lowpass=f=5000,volume=0.25" -ar 44100 -ac 2 assets/sfx/lower_slide.wav

5. Title heartbeat (generated in TitleCard step above)

Commit: git add assets/sfx/ -m 'feat: complete SFX library — whoosh, swoosh, blip, slide, heartbeat'

UPDATE index.tsx — Register ALL compositions with correct default props and sizes.
Commit: git add remotion/src/index.tsx -m 'feat: register all 7 Remotion compositions'

PHASE 1 VERIFICATION:
Render ALL components individually. ALL must succeed. Screenshot/log results.
If any component fails to render, fix it before proceeding.

=======================================================================
PHASE 2: ASSEMBLER + SCRIPT WRITER REWRITE (~3 hours)
=======================================================================

This is the critical phase. Read PRODUCTION_DESIGN_LAWS.md Section 1 (Episode Structure)
AGAIN before starting this phase. The episode arc defined there is the blueprint.

VOICES — tts_engine.py:
Replace ALL voice IDs:
  Host 1 (female): Eryn — kdnRe2koJdOK4Ovxn2DI
    Default: stability 0.75, similarity 0.75, style 0.10, speed 1.12
  Host 2 (male): Mark — 1SM7GgM6IMuvQlz2BwM3
    Default: stability 0.40, similarity 0.75, style 0.10, speed 1.10

VOICE_MODES for Host 1:
  cold_open: stability 0.38, similarity 0.78, style 0.15, speed 1.12
  setup/react: stability 0.75, similarity 0.75, style 0.10, speed 1.12
  social_segment: stability 0.60, similarity 0.75, style 0.12, speed 1.12
  wrap: stability 0.60, similarity 0.72, style 0.20, speed 1.10
  data: stability 0.70, similarity 0.78, style 0.10, speed 1.10

Add speed parameter to ElevenLabs API call body:
  "speed": voice.get("speed", 1.0)
If ElevenLabs API doesn't accept speed param, use FFmpeg post-processing:
  ffmpeg -i input.mp3 -af "atempo=1.12" output.mp3

Commit: git add tts_engine.py -m 'fix: Eryn + Mark voices with speed 1.12x'

SCRIPT WRITER — script_writer.py:
Update SCRIPT_PROMPT to enforce the episode arc from PRODUCTION_DESIGN_LAWS:

The script MUST produce segments in this order:
1. [COLD_OPEN] — The hook. Most shocking insight. 1-2 sentences MAX.
2. [NARRATION] — Setup for Clip 1. Why this matters. End with transition to clip.
3. [NARRATION] — Analysis after Clip 1. Connect to bigger picture.
4. [NARRATION] — Setup for Clip 2 with re-engagement hook at ~minute 3.
5. [NARRATION] — Analysis after Clip 2.
6. [DATA] — Hard metrics segment: hash rate, price, on-chain data.
7. [SOCIAL] — Commentary on what Bitcoin internet is saying.
8. [WARM] — Wrap-up, verdict, call to action. End ABRUPTLY. No "thanks for watching."

Each line must be tagged with the segment type prefix.
The parse function strips the tag and passes segment_type to TTS.

Add to SCRIPT_PROMPT:
  "CRITICAL RULES:
  - Start with the most shocking/interesting fact. NO intro. NO 'welcome to Protocol Pulse.'
  - At minute 3 (after Clip 2 setup), include a re-engagement hook: 'But here's where it gets interesting...'
  - At the halfway point, pivot to something unexpected or contrarian.
  - End ABRUPTLY after the call to action. NEVER say 'thanks for watching' or 'see you next time.'
    These phrases signal the video is ending and cause immediate viewer drop-off.
  - Each narrator line should be 1-3 sentences. Never more than 4 sentences per turn.
  - Include at least one specific number/metric in every other segment."

Commit: git add script_writer.py -m 'feat: episode arc structure + segment tagging in script writer'

ASSEMBLER — assembler.py (MAJOR REWRITE):
This is the biggest change. The assembler must implement PRODUCTION_DESIGN_LAWS Section 1.

New assembly flow:
```
1. Render TitleCard via Remotion (4 seconds) → part_001_title.mp4
   Mix with title_heartbeat.wav audio

2. Generate COLD OPEN TTS → render with CyberpunkBackground + WaveformVisualizer
   PiP PREVIEW: Extract 5-10s muted clip from first partner clip.
   Overlay PiP at bottom-right, 30% frame size, with:
     - Thin elegant border (1px white at 30% opacity)
     - Subtle Ken Burns pan (scale 1.0→1.05 over duration)
     - Rounded corners (use FFmpeg crop+overlay)
   → part_002_cold_open.mp4

3. ALPHA TRANSITION: Composite glitch_alpha.mov between parts
   Overlay on outgoing clip last 30 frames + incoming clip first 30 frames
   Mix with glitch_whoosh.wav
   → part_003_transition.mp4

4. PARTNER CLIP 1: Full screen partner clip video+audio
   Overlay LowerThird (alpha) at start, showing channel name + speaker
   Mix with lower_slide.wav at overlay start
   → part_004_clip1.mp4

5. ALPHA TRANSITION → part_005_transition.mp4

6. NARRATION SEGMENT: Analysis of Clip 1
   Background: cyberpunk_loop.mp4 (looped to match duration)
   Overlay: WaveformVisualizer (Remotion render matching audio duration)
   Previous clip thumbnail: top-right corner, 200px wide, 60% opacity, static
   NO PiP preview here (visual variety — different from cold open)
   → part_006_narration.mp4

7. ALPHA TRANSITION → part_007_transition.mp4

8. PARTNER CLIP 2: Same as Clip 1 treatment (LowerThird + slide SFX)
   → part_008_clip2.mp4

9. ALPHA TRANSITION → part_009_transition.mp4

10. NARRATION + DATA SEGMENT:
    Background: cyberpunk_loop.mp4
    Overlay: WaveformVisualizer
    If discussing metrics: overlay animated data card (simple FFmpeg drawtext with
    the metric number, styled with BRAND colors)
    → part_010_data.mp4

11. ALPHA TRANSITION → part_011_transition.mp4

12. SOCIAL SEGMENT: For each tweet post:
    Render SocialCard via Remotion (durationInFrames = ceil(audio_seconds * 30))
    Mix TTS audio over the Remotion card video
    Mix card_swoosh.wav at the start of each card
    CRITICAL: Pass posts to social card renderer in the SAME ORDER as script writer
    → part_012_social.mp4

13. ALPHA TRANSITION → part_013_transition.mp4

14. WRAP SEGMENT: Narrator delivers verdict
    Background: cyberpunk_loop.mp4
    Overlay: WaveformVisualizer
    → part_014_wrap.mp4

15. OUTRO: Existing outro_branded.mp4
    → part_015_outro.mp4

16. CONCATENATE ALL PARTS:
    Create filelist.txt with all parts in order
    ffmpeg -f concat -safe 0 -i filelist.txt -c:v libx264 -crf 17 -preset medium
    -b:v 8M -maxrate 10M -bufsize 15M -c:a aac -b:a 192k -ar 48000
    -vf "setpts=PTS-STARTPTS" -af "asetpts=PTS-STARTPTS,aresample=async=1"
    output.mp4

17. VALIDATE:
    - AV sync < 0.05s (check_av_sync)
    - Bitrate > 5Mbps (ffprobe)
    - Resolution 1920x1080 (ffprobe)
    - Duration > 60s for test mode
    - Quality score (quality_gate.py)
```

PiP PREVIEW IMPLEMENTATION:
When building a narration segment that precedes a partner clip:
1. Extract 8 seconds from the partner clip starting at 5 seconds in:
   ffmpeg -ss 5 -i clip.mp4 -t 8 -vf "scale=480:270,format=yuva420p" -an pip_raw.mp4
2. Apply Ken Burns (slow zoom):
   -vf "scale=500:282,zoompan=z='min(zoom+0.0005,1.05)':d=240:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=480x270"
3. Add elegant border:
   -vf "pad=484:274:2:2:color=white@0.3"
4. Overlay on narration background at position x=1400, y=540 (bottom-right area)

MUSIC BED:
- Select mood-appropriate track from assets/music/ (existing mood classifier)
- Mix at -20dB under ALL narration and social segments
- Full volume during title card (first 4 seconds)
- Fade out during partner clips (let clip audio breathe)
- Fade back in when narration resumes
- Different track or mood shift at halfway point if episode > 8 minutes

LOGO RESTRAINT (per PRODUCTION_DESIGN_LAWS addendum):
Logo appears ONLY in:
1. TitleCard (prominent, centered)
2. LowerThird during partner clips (tiny, 50px, corner)
3. Outro video (pre-baked)
NO logo in narration segments, social cards, data segments, or transitions.

Commit in stages:
1. git add assembler.py -m 'feat: full episode arc assembly with Remotion integration'
2. git add assembler.py -m 'feat: PiP preview system for narration segments'
3. git add assembler.py -m 'feat: sound design integration — whoosh, swoosh, blip, slide'

Run bash regression_test.sh after each commit.

=======================================================================
PHASE 3: INTEGRATION TEST + FRESH RENDER (~1 hour)
=======================================================================

1. Clear ALL caches:
   rm -rf cache/clips/* cache/transcripts/* downloads/clip_cache/* 2>/dev/null

2. Run full test render:
   python3 daily_producer.py --test

3. VALIDATE the output against PRODUCTION_DESIGN_LAWS:
   - Does the cold open start with the hook? (no intro, no "welcome")
   - Is TitleCard the animated logo with EKG pulse?
   - Do alpha transitions appear between EVERY segment?
   - Do transitions have whoosh sound?
   - Is Eryn's voice clear and confident (not whispery)?
   - Is the speaking speed slightly faster than default (~1.12x)?
   - Does the PiP preview appear during at least one narration segment?
   - Are social cards the Remotion cyberpunk version (not FFmpeg drawtext)?
   - Does each social card have a swoosh entry sound?
   - Is the LowerThird overlay visible on partner clips?
   - Does the logo appear ONLY in title card, lower thirds, and outro?
   - Is the CyberpunkBackground visible behind narration segments?
   - Is there a re-engagement hook around minute 3?
   - Does the episode end ABRUPTLY after CTA (no "thanks for watching")?
   - Is the music bed present under narration at -20dB?
   - Is the final bitrate > 5Mbps?
   - Is AV sync < 0.05s?

4. Log ALL results.

5. git add -A && git commit -m 'feat: PRODUCTION REBUILD COMPLETE — full episode arc, Remotion visuals, Eryn+Mark voices, PiP preview, sound design' && git push origin main

6. Report the SCP path:
   echo "OVERNIGHT BUILD COMPLETE"
   echo "SCP: scp ultron:~/protocol_pulse/video_pipeline_v3/output/[latest_dir]/pulse_check_*.mp4 ~/Downloads/"
   echo "Quality score: [score]/100"
   echo "AV sync: [offset]s"
   echo "Bitrate: [bitrate] Mbps"
   echo "Duration: [duration]s"
   echo "Eryn voice: confirmed/failed"
   echo "Remotion components: [count]/6 rendered"
   echo "PiP preview: yes/no"
   echo "Transitions: [count] alpha transitions"

This session should take 4-6 hours. Do not stop until Phase 3 validation passes.
If any Phase 1 component fails to render, fix it before proceeding.
If the Phase 3 test render fails validation, identify the failures and fix them.
The goal: PBX wakes up to a broadcast-quality video ready for download.
