Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Fix PiP left panel — restore world-class title + sponsor carousel design.
The left panel next to the PiP preview loop video currently shows a plain background.
It should show: episode title at top, then sponsor/partner carousel cards below.

DO NOT touch: tts_engine.py, overnight_render_loop.py, gemini_grade.py, daily_producer.py
DO NOT change the right PiP panel (the preview loop video) — that stays exactly as is.

STEP 1 — AUDIT
Read assembler.py make_pip_scene() or equivalent PiP function fully.
Find the left panel code — what does it currently render?
Check git log for the last commit that had the title+carousel:
  git log --oneline -30 -- video_pipeline_v3/assembler.py | head -15
Check what commit had the world-class design and read that version:
  git show [COMMIT]:video_pipeline_v3/assembler.py | grep -A50 "title.*pill\|carousel\|sponsor"

STEP 2 — RESTORE LEFT PANEL
The left panel should contain:
  TOP: Episode title in large white Impact/bold text with red Protocol Pulse accent
  MIDDLE: Segment topic label (e.g. "BITCOIN TECHNICAL ANALYSIS")  
  BOTTOM: Sponsor/partner ad carousel — rotating through partner cards
          (Curated Mining, RNS.ID Digital Residency, etc.)
          Cards should auto-rotate every 8 seconds using ffmpeg drawtext

Read the VISUAL_DESIGN_SYSTEM.md for exact brand colors and typography specs:
  cat ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md | head -100

Implement the left panel using pure FFmpeg drawtext/drawbox — no external images needed.
Match the red/black/white Protocol Pulse brand exactly.

STEP 3 — SPONSOR CAROUSEL DATA
Partner cards to rotate through:
  1. "CURATED MINING" — "White-glove Bitcoin mining" — curatedmining.io
  2. "PALAU DIGITAL ID" — "Sovereign identity via RNS.ID" — protocolpulse.io/digital-residency
  3. "PROTOCOL PULSE+" — "Premium Bitcoin intelligence" — protocolpulse.io

Use ffmpeg enable expression for time-based rotation:
  enable='between(t,0,8)' for card 1, enable='between(t,8,16)' for card 2, etc.

STEP 4 — TEST
Run a test render of just the PiP scene:
  python3 -c "from assembler import make_pip_scene; ..." 
Verify left panel shows title and carousel visually.
Run regression_test.sh — 0 FAILs required.

STEP 5 — COMMIT
git add video_pipeline_v3/assembler.py
git commit -m "feat(assembler): restore PiP left panel — episode title + sponsor carousel, Protocol Pulse brand design"
git push