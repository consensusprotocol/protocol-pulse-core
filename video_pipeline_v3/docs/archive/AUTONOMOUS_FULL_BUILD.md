AUTONOMOUS 3-HOUR SESSION. Read ALL gospel docs first:
1. PIPELINE_LAWS.md
2. ~/protocol_pulse/PRODUCTION_DESIGN_LAWS.md
3. ~/protocol_pulse/CONTENT_INTELLIGENCE_LAWS.md
4. ~/protocol_pulse/LIVE_INTELLIGENCE_LAWS.md

Execute these phases IN ORDER. Do NOT stop until all phases complete AND a production video renders successfully.

=== PHASE 1: X SPACES LISTENER (45 min) ===

Check if twspace-dl or yt-dlp can capture X Spaces:
  which twspace-dl 2>/dev/null
  pip3 list 2>/dev/null | grep -i space
  yt-dlp --help 2>/dev/null | grep -i space

If twspace-dl is not installed:
  pip3 install twspace-dl --break-system-packages 2>/dev/null || pip3 install twspace-dl

Build utils/spaces_monitor.py:
  Monitor Bitcoin influencer X accounts for active Spaces.
  Key accounts to monitor (from channels.yaml handles + major Bitcoiners):
    @saborosgrams (Saifedean), @saborosgrams @jack, @saylor, @APompliano,
    @LynAldenContact, @DocumentingBTC, @PeterMcCormack, @nataborelle,
    @PrestonPysh, @MartyBent, @stephanlivera

  Detection methods (try in order):
  1. yt-dlp: yt-dlp --flat-playlist "https://twitter.com/i/spaces/{space_id}"
  2. twspace-dl: twspace-dl -i {space_id}
  3. Twitter/X API: check user's fleetline for active spaces (if API available)
  4. Fallback: poll twitter.com/user profile pages for "LIVE" badge via requests

  When a Space is detected:
  1. Log: "X SPACE LIVE: @{handle} — {title}"
  2. Attempt audio capture (twspace-dl or yt-dlp)
  3. If capture succeeds: pipe to Whisper in 30-second chunks
  4. Classify each chunk: topics + sentiment
  5. Update data/intelligence/live_signals.json with space data
  6. The daily_producer.py will read live_signals when generating the next episode

  Cron: */5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/spaces_monitor.py >> logs/spaces_monitor.log 2>&1

  Even if full audio capture doesn't work yet, the DETECTION must work.
  Detecting that a Space is live is valuable data for the Terminal API.

Commit: git add utils/spaces_monitor.py -m 'feat: X Spaces monitor — detect + capture live Bitcoin Spaces'

=== PHASE 2: INTEGRATE LIVE SIGNALS INTO VIDEO PIPELINE (30 min) ===

The video pipeline must READ live_signals.json and incorporate live intelligence.

In daily_producer.py, BEFORE clip selection:
  1. Read data/intelligence/live_signals.json
  2. If any live streams or spaces are detected in last 6 hours:
     - Extract topics from live signals
     - Pass to script_writer as "LIVE_CONTEXT": tells Claude about real-time activity
     - Example: "LIVE CONTEXT: Swan Bitcoin was live-streaming about Bitcoin price.
       Simply Bitcoin is discussing '$500K+'. Incorporate these real-time signals."
  3. The script writer uses this context to make narration more timely and relevant
  4. If a live stream's topics overlap with selected clips, mention it:
     "And this is happening in real-time — Swan Bitcoin was just live discussing this exact topic."

In script_writer.py, add LIVE_CONTEXT to the SCRIPT_PROMPT:
  If live_context is provided:
  "LIVE INTELLIGENCE: The following events are happening RIGHT NOW or happened
  in the last few hours on Bitcoin YouTube/X Spaces. Reference these naturally
  in your narration to make the episode feel current and urgent:
  {live_context}"

Commit: git add daily_producer.py script_writer.py -m 'feat: integrate live signals into video pipeline — real-time context'

=== PHASE 3: VERIFY ALL 10 FIXES FROM LAST SESSION (15 min) ===

Quickly verify each fix is actually in the code:

1. No logo intro at start: grep -n 'title_card\|TitleCard' assembler.py | head -5
   Verify TitleCard is NOT the first part in the assembly
2. Split-screen layout: grep -n '1056\|55%\|split.*screen\|pip.*position' assembler.py | head -5
3. Sentence boundary: grep -n 'find_sentence_boundary\|sentence_bound' clip_extractor.py | head -3
4. PiP timing (only on pivot): grep -n 'REACT\|SETUP\|pip.*pivot' assembler.py | head -3
5. Tweet order fix: grep -n 'display_order\|SOCIAL.*ORDER' daily_producer.py assembler.py | head -5
6. Tweet screenshots: grep -n 'tweet_screenshot\|capture_tweet\|playwright' assembler.py | head -3
7. Music bed: grep -n 'music\|mix_music\|MUSIC' assembler.py | head -5
8. Stay sovereign outro: grep -n 'Stay sovereign\|stay_sovereign\|WARM.*sovereign' script_writer.py | head -3
9. Cyberpunk background: grep -n 'cyberpunk_loop\|bg_loop' assembler.py | head -3
10. Clip quality: grep -n '_get_bitrate\|3_000_000\|1_500_000' clip_extractor.py | head -3

Log all results. If any fix is missing, apply it now.

=== PHASE 4: PRODUCTION VIDEO RENDER (60 min) ===

Clear ALL caches for fresh content:
  rm -rf cache/clips/* cache/transcripts/* downloads/clip_cache/* 2>/dev/null

Run PRODUCTION render (NOT test mode):
  python3 daily_producer.py 2>&1

This must:
- Scan 80 channels for fresh content
- Use intelligent clip scorer for data-driven selection
- Select 5 clips from 5 DIFFERENT channels (hard enforce)
- Read live_signals.json for real-time context
- Use Eryn (female, speed 1.12x) + Mark (male, speed 1.10x)
- Episode arc: cold open hook → clip1 → narration → clip2 → etc.
- PiP preview on SETUP segments only
- Alpha transitions between EVERY segment with custom whoosh
- Background music from assets/music/ at -20dB
- Cyberpunk background on all narrator segments
- Tweet screenshots via Playwright
- "Stay sovereign" closing line
- No logo in first frame, no double-play
- Quality gate: score >= 85

WAIT for it to complete. Do NOT move to Phase 5 until the render finishes.

After render completes, report:
  - Output path (SCP command for PBX)
  - Quality score
  - Duration
  - Bitrate
  - AV sync
  - Channels used (list all 5)
  - Live signals incorporated (yes/no)
  - Music track used
  - Tweet screenshots captured (count)

=== PHASE 5: POST-RENDER CLEANUP + GIT (15 min) ===

1. Run regression test: bash regression_test.sh
2. Git add all changes
3. Git commit: "feat: live intelligence integration + production render with all fixes"
4. Git push origin main
5. Report EVERYTHING to the tmux console so PBX can see results on next status check

RULES:
- Do NOT rush. Take your time on each phase.
- If a phase fails, debug and fix before moving on.
- The production render is the MOST IMPORTANT output. It must succeed.
- If the render takes 60+ minutes, that's fine — wait for it.
- Log everything. PBX will check tmux output for status.

This session runs for 3 hours autonomously. PBX is away. Execute everything.