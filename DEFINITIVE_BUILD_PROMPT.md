# PROTOCOL PULSE — DEFINITIVE PIPELINE BUILD PROMPT
# Corrected for PRODUCTION_DESIGN_LAWS compliance
# Synthesized from 5 LLM reviews (Claude, Gemini, GPT, Grok, Perplexity)
# This is the FINAL prompt. No more iterations. Execute this.
# Generated: 2026-03-06

---

## FOR THE NEW CLAUDE AGENT:

Read these from GitHub FIRST (use web_fetch):
1. https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/HANDOFF_FINAL.md
2. https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/PIPELINE_MANIFEST_SPEC.md
3. https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/PRODUCTION_DESIGN_LAWS.md
4. https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/video_pipeline_v3/VIDEO_PIPELINE_FORENSIC_AUDIT_V2.md

Then on Ultron, read: PIPELINE_LAWS.md

---

## THE NORTH STAR

"Do not ship another smarter assembler. Ship a dumber renderer driven by
an explicit manifest plus QC gates — where the manifest carries DESIGN
INTENT, not just timing."

## THREE GOLDEN RULES

1. "No Inference" — manifest_renderer.py is FORBIDDEN from using if-statements
   to guess what a segment is. If it's not in the manifest JSON, it doesn't exist.
2. "Audio-First" — audio master bus finalized BEFORE video mux.
   1-frame audio desync = automatic F.
3. "Failsafe" — missing assets produce branded fallbacks, never black screens.

## LAW COMPLIANCE CORRECTIONS (previous prompt had these wrong):

### CORRECTION 1: Cold open has NO music buffer
Previous prompt said "add 1-second intro music before voice."
PRODUCTION_DESIGN_LAWS says: "NO intro. NO music. Start mid-action with stakes."
CORRECT: Cold open = immediate voice + face on screen. Zero pre-roll. Zero music.
Music only begins at the title sequence (4 seconds in).

### CORRECTION 2: Outro ends ABRUPTLY, no fade-to-black
Previous prompt said "1s fade to black."
PRODUCTION_DESIGN_LAWS says: "End ABRUPTLY after CTA. NEVER say thanks for watching."
CORRECT: After the CTA line, hard cut to branded outro card (3-4 seconds), then END.
No graceful fade. No lingering. Abrupt = the viewer wants to click next.

### CORRECTION 3: Logo REMOVED from narration segments entirely
PRODUCTION_DESIGN_LAWS Logo Restraint Addendum: Logo appears ONLY in:
  1. Title card (prominent, centered)
  2. Partner clip watermark (60px, 40% opacity, top-right)
  3. Outro card
NEVER in narration, social cards, data segments, or transitions.

### CORRECTION 4: Audio targets from the design laws
PRODUCTION_DESIGN_LAWS Section 3 specifies:
  - Music bed under narration: -18dB to -22dB (NOT -10dB as previous prompt said)
  - Music STOPS during partner clips (not just ducked — STOPS)
  - Music ducks AUTOMATICALLY when voice is present (sidechain, attack 50ms, release 500ms)
  - Target loudness: -14 LUFS for all clips AND narration (laws say -14, not -16)

### CORRECTION 5: Music behavior is per-segment-type, not global
  - Cold open: NO music
  - Title sequence: branded heartbeat thumps + synth tone
  - Narration (setup/react): music bed at -18dB to -22dB, sidechain ducked under voice
  - Partner clips: music STOPS completely (let clip audio breathe)
  - Transitions: whoosh SFX only (no music swell in v1)
  - Social segment: subtle bed continues
  - Wrap/verdict: music continues, warm tone
  - Outro card: outro jingle rises after last narrator word, ends abruptly

---

## SPRINT 1: FIX VISIBLE FAILURES (obey the laws)

Execute these in order. Each has an acceptance test.

### 1.1 Remove duplicate outro narration
FIX: In assemble_episode(), remove narration_audio param from outro call.
Outro = visual + outro jingle ONLY. No voice.
DONE WHEN: Episode has exactly ONE occurrence of the closing VO line in audio stream.

### 1.2 Add clip audio/video fade protection on EVERY partner clip
FIX: Apply to all clips in make_clip_visual():
  Audio: -af "afade=t=in:d=0.3,afade=t=out:st={duration-0.5}:d=0.5"
  Video: -vf "fade=t=in:d=0.3,fade=t=out:st={duration-0.5}:d=0.5"
DONE WHEN: No clip starts or ends with a hard cut. Scrubbing shows smooth entry/exit.

### 1.3 Audio normalization — per-clip processing chain
FIX: Apply to EVERY partner clip before assembly:
  -af "highpass=f=50,lowpass=f=15000,loudnorm=I=-14:TP=-1.5:LRA=7"
Apply to EVERY narration TTS file:
  -af "loudnorm=I=-14:TP=-1.5:LRA=7"
DONE WHEN: Back-to-back clips have no audible volume jump. Measured within ±1 LU.

### 1.4 Sidechain music ducking (not static volume)
FIX: In make_host_visual(), replace static music volume with sidechain:
  Music idles at -18dB (per laws, NOT -10dB)
  When voice present: music ducks to -30dB automatically
  Attack: 50ms, Release: 500ms (Gemini's recommendation for spoken-word)
  Music STOPS during partner clips (boolean in manifest, not just ducked)
  Music does NOT play during cold open
DONE WHEN: Music audibly present between narrator sentences, ducks cleanly during speech,
  fully silent during partner clips. Music breathes back naturally in pauses.

### 1.5 Fix social cards — render EACH tweet as its OWN video segment
FIX: Refactor make_social_card_visual(). Instead of one monolithic video:
  For each tweet:
    1. Generate narration audio for THIS tweet
    2. Render Remotion SocialCard for THIS tweet (durationInFrames = audio duration + 30 frames)
    3. Add entry animation (0.3s slide-in) and exit (0.3s fade-out)
    4. Append as separate part to parts[] list
DONE WHEN: Each card appears for its full narration, no dark gaps, no overlapping.

### 1.6 Fix cold open — face on screen, no logo, no music
FIX: Rewrite make_intro_coldopen():
  Visual: PiP preview of first clip (face visible) OR full-screen first-clip moment
  Audio: Narrator hook voice ONLY. No jingle. No intro music. Immediate voice.
  NO logo anywhere in cold open.
  Duration: 6-8 seconds of pure hook.
After cold open: 4-second title sequence (Remotion TitleCard with EKG + heartbeat SFX)
Then straight into Segment 1.
DONE WHEN: First frame shows cyberpunk bg + face (PiP or fullscreen) + subtitle.
  No logo. No music. Voice starts immediately.

### 1.7 Swap cyberpunk background
FIX: Current cyberpunk_loop.mp4 is 862KB (too dark/empty).
  Option A: Use cyberspace.mp4 (55MB, rich visuals)
  Option B: Use neon_lines.mp4 (103MB, rich visuals)
  Option C: Re-render CyberpunkBackground.tsx with brighter particles/grid
  If using large files, apply Gemini's glow enhancement:
    -filter_complex "[v]split[main][glow];[glow]boxblur=10:5,curves=all='0/0 0.5/0.2 1/1'[g];[main][g]blend=all_mode='screen'"
DONE WHEN: Narration segments have visible, animated background — never plain black.

### 1.8 Outro ends abruptly (per laws)
FIX: Branded outro card plays for 3-4 seconds with outro jingle.
  No fade-to-black. Hard cut at the end. Video STOPS.
  CTA ("Subscribe for tomorrow's brief") is spoken by narrator in the WRAP segment,
  NOT over the outro card. Outro card = visual + music ONLY.
DONE WHEN: Last frame is the branded card. No gradual fade. Abrupt end.

### 1.9 Logo restraint enforcement
FIX: Audit every function that renders the Protocol Pulse logo.
  REMOVE logo from: make_host_visual, make_social_card_visual, cold open
  KEEP logo in: title card (centered), make_clip_visual (60px watermark, 40% opacity), outro card
DONE WHEN: Logo appears in max 3 places per episode. Never in narration segments.

---

## SPRINT 2: MANIFEST ARCHITECTURE (v1 minimal subset)

### 2.1 Build manifest_builder.py

Generates episode_manifest.json BEFORE rendering. Saved to disk (enables crash resume).

v1 REQUIRED fields per segment:
  - id, type, start_sec, duration_sec
  - audio_path, video_path (or visual_mode + asset path)
  - transition_in, transition_out
  - music_state: "none" | "title_hit" | "bed_ducked" | "transition_swell" | "outro_rise"
  - clip_fade_in_sec, clip_fade_out_sec
  - screen_mode: "cold_open" | "title_sequence" | "partner_clip" | "narration_setup" |
    "narration_react" | "data_segment" | "social_card" | "wrap" | "outro"
  - logo_allowed: boolean
  - face_expected: boolean
  - primary_visual_type: "pip_upcoming" | "clip_callback_thumb" | "data_card" |
    "social_card" | "waveform_only"

Episode-level:
  - target_loudness_lufs: -14
  - true_peak_dbtp: -1.5
  - music_bed_path
  - logo_policy: "restraint" (only title, clip watermark, outro)

Build ALONGSIDE existing assembler. Don't replace it yet.
Log what manifest WOULD have produced vs what assembler actually did.
This is the parallel-run phase.

DONE WHEN: episode_manifest.json exists on disk in output folder. All segments listed
with correct types and screen modes. Manifest is valid JSON and complete before render starts.

### 2.2 Build qc_pipeline.py

Asset preflight (BEFORE render):
  - Verify all audio/video paths exist
  - Verify background asset is not empty/corrupt
  - Verify all clips meet 1.5Mbps minimum bitrate
  - Verify all social card data has text + handle (screenshot optional)

Post-render QC:
  - Integrated loudness within ±2 LU of -14 LUFS
  - True peak <= -1.5 dBTP
  - No silent gaps > 2.0 seconds
  - No black frame sequences > 0.5 seconds
  - Total duration in expected range (360-900 seconds)
  - Clip count matches manifest

V1 RULE: QC failures LOG + ALERT (Telegram) but do NOT block publish.
We flip to hard-gate after 3 consecutive clean runs.

DONE WHEN: qc_pipeline.py runs after every render. Results logged. Telegram alert fires
on any failure. No publish blocked in v1.

---

## SPRINT 3: VISUAL RETENTION ENGINE (Reference PRODUCTION_DESIGN_LAWS)

Only execute Sprint 3 AFTER Sprint 1 + 2 are verified working.

### 3.1 Narration Visual Stack (per design laws)
Every narration segment must have ALL of these layers:
  Layer 1: Animated background (cyberpunk/cyberspace loop, with subtle zoom 1.0→1.05)
  Layer 2: Primary visual (rotates by segment type):
    - SETUP: PiP preview of upcoming clip (30% frame, bottom-right, rounded corners, drop shadow)
    - REACT: Small thumbnail callback of previous clip (15% frame, top-right)
    - DATA: Data card overlay (BTC price, hashrate, metric)
    - SOCIAL: Not applicable (social has its own segment type)
  Layer 3: Waveform visualizer (bottom-third, center-left, NOT blocking PiP)
  Layer 4: Info bar (gold, bottom, full width: BTC price | date | protocolpulse.io)
  Layer 5: Subtitle (word-level highlighting if time permits, else standard white text)
  NO LOGO in any narration layer.

Visual change every 15-25 seconds GUARANTEED. If a narration segment exceeds 20 seconds,
the manifest must specify a visual change event (swap PiP, pop data card, cycle background).

### 3.2 PiP Preview System
  - 30% frame size, bottom-right at position (1200, 500)
  - Rounded corners (if FFmpeg supports, else thin white border at 20% opacity)
  - Drop shadow (drawbox at +4px offset, black at 30%)
  - "COMING UP..." label inside PiP, bottom-left, bold white, 24px
  - Slow Ken Burns zoom inside PiP (1.0→1.05 over segment duration)
  - Use MIDPOINT of clip for preview (not first 8 seconds which may be title card)
  - Only on SETUP segments. Hidden during REACT segments.

### 3.3 Social Card Design
  - Each card: glassmorphism panel (blurred bg, soft red glow, scanlines)
  - Entry: 0.3s slide-in from right
  - Hold: matches narration duration for that tweet
  - Exit: 0.3s fade out
  - Content: avatar (if available), @handle, tweet text, likes count
  - If Playwright screenshot available: use it as the card visual
  - If not: Remotion text-based card with cyberpunk styling

### 3.4 Lower Thirds on Partner Clips
  - Slide-in from left, 0.4s animation
  - Duration: 5 seconds, then slide-out
  - Content: Channel name | Speaker name | Topic
  - Styling: glassmorphism bar, Protocol Pulse red accent, small logo (50px)

### 3.5 Word-Level Subtitle Highlighting (if time permits)
  - Use Whisper word-level timestamps
  - Current word: Protocol Pulse Red (#CC0000), bold
  - Previous/upcoming words: white (#FFFFFF), 70% opacity
  - Slight scale-up (1.05x) on active word if ASS format supports it
  - This is the "Hormozi retention trick" — 40% retention improvement industry-wide
  - IF this is too complex for this session, ship standard white subtitles and flag for Sprint 4

---

## AFTER ALL SPRINTS: RENDER + VERIFY

1. Clear clip cache: rm -rf cache/clips/* 2>/dev/null
2. Run production render: python3 daily_producer.py (NO --test flag)
3. Verify manifest exists on disk in output folder
4. Run qc_pipeline.py on the output
5. Report: SCP path, quality score, duration, channels used, QC results
6. Git push all changes

ACCEPTANCE CRITERIA (the render passes when ALL of these are true):
  □ First frame: face on screen, no logo, no music, immediate voice hook
  □ Title sequence: 4 seconds, EKG animation, follows cold open
  □ No narration segment is "just waveform on black" — always has primary visual
  □ Visual change every 15-25 seconds (no static frame >25s)
  □ Each social card visible for its full narration, no dark gaps
  □ PiP appears on SETUP segments only, hidden on REACT
  □ Logo only in: title card, clip watermark (40% opacity), outro
  □ Music present during narration, silent during clips, no music in cold open
  □ No clip starts or ends with hard cut (fades applied)
  □ No duplicate narration in outro
  □ Outro ends abruptly (no fade-to-black)
  □ All clips within ±1 LU of -14 LUFS
  □ episode_manifest.json exists in output folder
  □ qc_pipeline.py log exists with results

---

## DO NOT ATTEMPT IN THIS SESSION:
- Thumbnail generator
- Shorts auto-extraction
- B-roll/chart overlays
- Transition energy scoring
- Virtual zoom on backgrounds (beyond subtle PiP Ken Burns)
- Channel expansion
- Newsletter fixes
- Terminal API fixes
- Replit migration

Stay focused. Foundation first. Polish later.
