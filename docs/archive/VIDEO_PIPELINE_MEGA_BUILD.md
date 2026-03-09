# ═══════════════════════════════════════════════════════════════════════════
# PULSE CHECK VIDEO PIPELINE — 20-PHASE AUTONOMOUS BUILD
# ═══════════════════════════════════════════════════════════════════════════
#
# ESTIMATED TIME: 6-10 hours
# WORKING DIRECTORY: /home/ultron/protocol_pulse/
#
# ═══════════════════════════════════════════════════════════════════════════
# MANDATORY FIRST STEP: READ THE FULL CONTEXT DOCUMENT
# ═══════════════════════════════════════════════════════════════════════════

cat /home/ultron/protocol_pulse/VIDEO_PIPELINE_CONTEXT.md

# READ EVERY WORD. Contains architecture, what exists, what's broken, API keys,
# channel configs, show format, design standards. You are blind without it.

# ═══════════════════════════════════════════════════════════════════════════
# CRITICAL RULES FOR ENTIRE SESSION
# ═══════════════════════════════════════════════════════════════════════════
#
# 1. NEVER delete existing working code. Extend, don't replace.
# 2. git commit + push after EVERY phase. Commit message format:
#    "pipeline phase N: description"
# 3. Test everything with actual execution, not just reading code.
# 4. If a phase produces video/audio output, verify with ffprobe.
# 5. TREAT EACH PHASE as the only task. Triple-verify before moving on.
# 6. DO NOT skip phases. DO NOT rush. Quality over speed.
# 7. All video output: 1920x1080 @ 30fps unless stated otherwise.
# 8. All audio output: 44100Hz stereo MP3/WAV.
# 9. Use the SadTalker venv for ML tasks:
#    /home/ultron/SadTalker/venv/bin/python3
# 10. Regular python3 for non-ML tasks.

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: FIX THE FOUNDATION — LOCAL ASSEMBLER
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# PROBLEM: ultron_client.py and ultron_assembler.py call video.protocolpulse.io
# which doesn't exist. The whole pipeline dies at the assembly step.
#
# FIX: Create a LOCAL assembly module that uses moviepy + ffmpeg directly.
# The existing code expected an HTTP API — replace with local function calls.
#
# 1. Read current ultron_assembler.py:
#    cat services/video_engine/assembly/ultron_assembler.py
#
# 2. Create: services/video_engine/assembly/local_assembler.py
#    This replaces the HTTP-based assembler with local moviepy/ffmpeg calls.
#    Must implement:
#    - assemble_horizontal(manifest, bundle_path) → MP4 file path
#    - assemble_vertical(manifest, bundle_path) → MP4 file path (9:16)
#    - export_audio_only(manifest, bundle_path) → MP3 file path
#    
#    Assembly logic:
#    - Read the timeline manifest (list of segments)
#    - Each segment is either: clip (from YouTube), narration (voiceover audio),
#      tweet_card (image overlay), lower_third (text overlay), or transition
#    - Concatenate clips with ffmpeg (fastest: ffmpeg concat demuxer)
#    - Mix narration audio on top of clips where specified
#    - Overlay tweet cards and lower thirds using ffmpeg drawtext/overlay filters
#
# 3. Create: services/video_engine/assembly/ffmpeg_ops.py
#    Low-level ffmpeg operations:
#    - concat_clips(clip_paths, output_path) — concat demuxer
#    - add_audio_mix(video_path, audio_path, output_path, volume) — mix audio
#    - overlay_image(video_path, image_path, output_path, x, y, start, end) — picture overlay
#    - add_text_overlay(video_path, text, output_path, font, size, x, y, start, end) — drawtext
#    - crossfade(clip1, clip2, duration, output) — xfade filter
#    - scale_and_pad(input_path, output_path, w, h) — fit any clip to target resolution
#    - extract_audio(video_path, output_path) — audio-only export
#
#    ALL operations must use subprocess.run with proper error checking.
#    Use ffprobe to get duration/dimensions before operating.
#
# 4. Update services/video_engine/ultron_client.py:
#    Add a local_mode flag. When ULTRON_HOST is empty or "localhost",
#    use local_assembler instead of HTTP calls.
#    Keep the HTTP client for future use, just add the local fallback.
#
# VERIFICATION GATE:
# V1: python3 -c "from services.video_engine.assembly.local_assembler import LocalAssembler; print('IMPORT OK')"
# V2: python3 -c "from services.video_engine.assembly.ffmpeg_ops import *; print('OPS OK')"
# V3: Create a 5-second test: generate a solid color clip, overlay text "TEST", verify output
#     ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=5 -vf "drawtext=text='TEST':fontsize=72:fontcolor=white:x=(w-tw)/2:y=(h-th)/2" -c:v libx264 -t 5 /tmp/test_assembly.mp4
#     ffprobe /tmp/test_assembly.mp4 (must show 1920x1080, ~5s, h264)
#
# git add -A && git commit -m "pipeline phase 1: local assembler + ffmpeg ops" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: MOTION GRAPHICS ENGINE — INTRO, OUTRO, TRANSITIONS
# ═══════════════════════════════════════════════════════════════════════════
# Time: 45-60 min
#
# Create: services/video_engine/graphics/motion_graphics.py
# Also: services/video_engine/graphics/__init__.py
#
# This generates all the branded video elements using ffmpeg filters + Pillow.
# NO external dependencies like After Effects. Pure code-generated graphics.
#
# 1. INTRO BUMPER (4 seconds):
#    - Black screen
#    - Red horizontal line grows from center outward (like a pulse/heartbeat)
#    - "PULSE CHECK" text fades in (Space Mono or available monospace font)
#    - "DAILY BITCOIN INTELLIGENCE" subtitle fades in below
#    - Date stamp: "MARCH 3, 2026" small text
#    - Whoosh sound effect (generate with ffmpeg: sine wave sweep)
#    - Output: data/graphics/intro_bumper.mp4 (regenerate daily with date)
#
#    Implementation: Use Pillow to render frames → ffmpeg to encode video.
#    Render 120 frames (4s @ 30fps). Each frame:
#    - Frame 0-30: black → red line grows (Pillow draw.line)
#    - Frame 30-60: text "PULSE CHECK" alpha increases (composite)
#    - Frame 60-90: subtitle fades in
#    - Frame 90-120: hold
#    Save frames as PNG sequence, encode: ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 output.mp4
#
# 2. OUTRO BUMPER (3 seconds):
#    - "STAY SOVEREIGN" text center
#    - "protocolpulse.io" below
#    - Red line shrinks to center → black
#    - Same reverse of intro animation
#
# 3. TRANSITION (1 second):
#    - Quick red line sweep left-to-right (like a scanner)
#    - Usable between story segments
#    - Output: data/graphics/transition.mp4
#
# 4. LOWER THIRD TEMPLATE:
#    Function: render_lower_third(name, title, channel_logo_path=None) → PNG
#    - Semi-transparent dark bar at bottom of frame (1920x200)
#    - Red accent line at top of bar
#    - Speaker name in white, bold
#    - Channel/title in gray below
#    - Optional channel logo on left
#    - Returns 1920x1080 RGBA PNG (transparent except lower third area)
#
# 5. STORY TITLE CARD (2 seconds):
#    Function: render_title_card(headline, story_number) → list of frame PNGs
#    - Story number ("01", "02") in large red text
#    - Headline text in white
#    - Subtle grid/scanline effect in background
#    - Fades in over 15 frames, holds, fades out over 15 frames
#
# For all Pillow rendering, check available fonts:
# fc-list | grep -i "mono\|space\|noto" | head -10
# Use DejaVuSansMono or NotoSansMono if Space Mono isn't installed.
#
# VERIFICATION GATE:
# V1: python3 -c "from services.video_engine.graphics.motion_graphics import generate_intro; generate_intro('/tmp/test_intro.mp4')" && ffprobe /tmp/test_intro.mp4
# V2: ffprobe shows 1920x1080, ~4 seconds, h264
# V3: python3 -c "from services.video_engine.graphics.motion_graphics import render_lower_third; render_lower_third('Michael Saylor', 'MicroStrategy Chairman', '/tmp/test_lt.png')" && file /tmp/test_lt.png
# V4: Intro video actually looks good (open a frame and check visually)
#
# git add -A && git commit -m "pipeline phase 2: motion graphics engine" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: YOUTUBE SCANNER — END-TO-END TEST
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# The YouTube scanner code EXISTS but has never run successfully.
# Test it end-to-end with ONE channel.
#
# 1. Read the full scanner: cat services/video_engine/sources/youtube_scanner.py
#
# 2. Create a test script: tests/test_youtube_scan.py
#    - Import YouTubeScanner
#    - Configure with JUST Simply Bitcoin (most frequent uploads)
#    - Set max_age_hours=72 (3 days to ensure we find something)
#    - Run scan_all()
#    - Print results
#    - If no videos found, debug: manually run yt-dlp to check
#      yt-dlp --flat-playlist --print "%(id)s %(title)s %(upload_date)s" "https://www.youtube.com/@SimplyBitcoin/videos" --playlist-end 3
#
# 3. Fix any issues found. Common problems:
#    - yt-dlp might need --cookies or different format
#    - Channel handles vs IDs might be wrong
#    - Date parsing issues
#    - The scanner calls ultron.transcribe() which uses HTTP — fix to call
#      faster-whisper locally instead
#
# 4. Verify Whisper transcription works locally:
#    python3 -c "from faster_whisper import WhisperModel; m = WhisperModel('base', device='cuda'); print('WHISPER OK')"
#    If model not downloaded, it will download on first use.
#
# 5. Modify youtube_scanner.py to support LOCAL transcription:
#    Instead of sending audio to an HTTP endpoint, call faster-whisper directly.
#    Create helper: services/video_engine/local_whisper.py
#    - transcribe_audio(audio_path) → {text, segments, words}
#    - Use word-level timestamps (word_timestamps=True)
#    - Model: "base" for speed, "small" for accuracy
#    - Device: "cuda" for GPU acceleration
#
# 6. Run the full test again with local transcription:
#    python3 tests/test_youtube_scan.py
#    Should output: channel name, video title, transcript preview
#
# VERIFICATION GATE:
# V1: yt-dlp successfully lists recent videos from at least 3 channels
# V2: Audio download works (check for .wav or .mp3 file)
# V3: Whisper transcription produces text with word-level timestamps
# V4: Test script runs without errors and produces structured output
#
# git add -A && git commit -m "pipeline phase 3: youtube scanner end-to-end test" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: X/TWITTER SCRAPING — NOTABLE TWEETS + SCREENSHOTS
# ═══════════════════════════════════════════════════════════════════════════
# Time: 45-60 min
#
# Two components: (A) fetch notable tweets, (B) screenshot them beautifully.
#
# A. TWEET FETCHING:
# 1. Read tweet_monitor.py — it uses Twitter API v2 Bearer token
# 2. Test if Bearer token works:
#    curl -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" "https://api.twitter.com/2/tweets/search/recent?query=from:saylor&max_results=10"
# 3. If API works: fix tweet_monitor.py to actually fetch and filter
#    - Query: from:saylor OR from:LynAldenContact OR from:JeffBooth... (top 10 accounts)
#    - Filter: min_likes=500, exclude replies, last 24 hours
#    - Return: tweet text, author, metrics, tweet_id
# 4. If API is rate-limited or doesn't work: build Playwright scraper as fallback
#    Create: services/video_engine/sources/tweet_scraper.py
#    - Uses Playwright (headless Chromium)
#    - Navigate to https://x.com/saylor (public profile, no login needed)
#    - Extract recent tweets with like counts
#    - Filter by engagement threshold
#    - playwright install chromium (if not already installed)
#
# B. TWEET SCREENSHOTS:
# 1. Read tweet_card_renderer.py — it renders with Pillow (works but basic)
# 2. Create ENHANCED renderer: services/video_engine/sources/tweet_screenshot.py
#    Option 1 (Preferred): Playwright screenshot of actual tweet
#    - Navigate to https://x.com/saylor/status/{tweet_id}
#    - Wait for tweet to load
#    - Screenshot the tweet card element
#    - Add Protocol Pulse watermark + dark border
#    - Resize to 1920x1080 for video overlay (center tweet, dark background)
#    Option 2 (Fallback): Enhanced Pillow rendering
#    - Use tweet_card_renderer.py as base
#    - Add: profile picture (from PP cache, not Twitter CDN)
#    - Add: like/retweet/reply counts
#    - Add: verified badge
#    - Better typography (proper line spacing, text wrapping)
# 3. Both options produce 1920x1080 PNG files for video overlay.
#
# VERIFICATION GATE:
# V1: python3 -c "from services.video_engine.sources.tweet_monitor import TweetMonitor; t=TweetMonitor(['saylor']); print(t.configured)" → True
# V2: Test fetch returns at least 1 tweet (or scraper returns data)
# V3: Screenshot/render produces a 1920x1080 PNG of a real tweet
# V4: ffprobe confirms image dimensions
#
# git add -A && git commit -m "pipeline phase 4: twitter scraping + screenshots" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: NOSTR POST CAPTURE — LIVE RELAY + SCREENSHOTS
# ═══════════════════════════════════════════════════════════════════════════
# Time: 45-60 min
#
# Create: services/video_engine/sources/nostr_capture.py
#
# Two parts: (A) fetch noteworthy Nostr posts, (B) screenshot them.
#
# A. NOSTR POST FETCHING:
# 1. Read existing services/nostr_service.py and nostr_signal_service.py
# 2. Build a focused fetcher for the video pipeline:
#    - Connect to relays: wss://relay.damus.io, wss://nos.lol, wss://relay.nostr.band
#    - Subscribe to events (kind=1) from monitored pubkeys (7 in allowlist)
#    - Filter: last 24 hours, min 10 zaps or reactions
#    - Use websocket-client (already installed) for relay connections
#    - Implementation:
#      import websocket, json
#      ws = websocket.create_connection("wss://relay.damus.io")
#      filter = {"kinds": [1], "authors": [pubkey_list], "since": unix_24h_ago}
#      ws.send(json.dumps(["REQ", "sub1", filter]))
#      # Read events until EOSE
#    - Parse events, extract content, author, created_at, reactions
#    - Return top 3-5 posts by engagement
#
# B. NOSTR SCREENSHOTS:
# 1. Create Playwright-based Nostr post screenshotter:
#    - Navigate to https://njump.me/{note_id} or https://snort.social/e/{note_id}
#    - Wait for post to render
#    - Screenshot the post card
#    - Add Protocol Pulse branding + dark frame
#    - Resize to 1920x1080 for video overlay
# 2. Fallback: Pillow-rendered card (similar to tweet_card_renderer)
#    - Purple/dark themed (Nostr colors)
#    - Author name + npub display name
#    - Post content with proper text wrapping
#    - Zap count, reaction count
#    - "via Nostr" badge
#
# VERIFICATION GATE:
# V1: python3 -c "from services.video_engine.sources.nostr_capture import fetch_notable_nostr; posts = fetch_notable_nostr(); print(f'Found {len(posts)} posts')"
# V2: At least 1 post returned (or graceful empty if relays are slow)
# V3: Screenshot/render produces 1920x1080 PNG
# V4: File exists and is valid image
#
# git add -A && git commit -m "pipeline phase 5: nostr capture + screenshots" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: X SPACES LISTENER — RECORDING + TRANSCRIPTION
# ═══════════════════════════════════════════════════════════════════════════
# Time: 60-90 min (most experimental phase)
#
# Replace the skeleton spaces_monitor.py with a real implementation.
#
# APPROACH: yt-dlp can record live X Spaces audio. For completed Spaces,
# recordings are sometimes available.
#
# 1. Research: How to find active/recent Spaces:
#    - Twitter API v2 Spaces endpoints (if available with our token tier)
#      curl -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" "https://api.twitter.com/2/spaces/search?query=bitcoin&state=live"
#    - If API not available: Playwright scraping of twitter.com/i/spaces
#    - Third option: monitor specific accounts known to host Spaces
#      (Matt Odell, Marty Bent, Preston Pysh, Bitcoin Magazine)
#
# 2. Create: services/video_engine/sources/spaces_listener.py
#    - find_recent_spaces(accounts, hours=24) → list of Space metadata
#    - record_space(space_url, output_path, max_duration=3600) → audio file
#      Uses: yt-dlp "{space_url}" -x --audio-format wav -o "{output_path}"
#    - transcribe_space(audio_path) → {text, segments, words}
#      Uses local_whisper from Phase 3
#
# 3. Integration:
#    - If no Spaces found, pipeline continues gracefully (soft dependency)
#    - If Space found, treat like a YouTube video: transcribe → triage → clip
#    - Spaces clips labeled differently: "From X Spaces with {host}"
#
# 4. Fallback for when Spaces API isn't available:
#    - Monitor known Spaces-hosting accounts
#    - Check if they're currently in a Space (Twitter API or scraping)
#    - If found, try to record with yt-dlp
#    - If nothing found, return empty list (pipeline continues)
#
# VERIFICATION GATE:
# V1: python3 -c "from services.video_engine.sources.spaces_listener import find_recent_spaces; print(find_recent_spaces(['ODELL', 'MartyBent']))"
# V2: Function returns list (even if empty — no crashes)
# V3: If a Space is found and recorded, Whisper can transcribe it
# V4: Output structure matches what the triage stage expects
#
# git add -A && git commit -m "pipeline phase 6: X Spaces listener" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 7: AUDIO WAVEFORM VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════
# Time: 45-60 min
#
# When showing audio clips (Spaces, podcast segments), display an animated
# audio waveform that moves with the vocals. This is the visual element
# that makes audio content cinematic.
#
# Create: services/video_engine/graphics/waveform_viz.py
#
# 1. Generate waveform video from audio:
#    Function: audio_to_waveform_video(audio_path, output_path, duration,
#              color="#CC2222", bg_color="#0a0f0a", style="bars")
#    
#    Implementation using ffmpeg showwaves filter:
#    ffmpeg -i audio.wav -filter_complex "[0:a]showwaves=s=1920x400:mode=cline:rate=30:colors=#CC2222[v]" -map "[v]" -c:v libx264 waveform.mp4
#    
#    Or for bar-style (more cinematic):
#    ffmpeg -i audio.wav -filter_complex "[0:a]showfreqs=s=1920x400:mode=bar:ascale=log:fscale=lin:colors=#CC2222[v]" -map "[v]" waveform.mp4
#
# 2. Composite waveform with speaker card:
#    Function: render_audio_segment(audio_path, speaker_name, topic, output_path)
#    - Dark background (1920x1080)
#    - Speaker name + topic at top
#    - Waveform visualization in center (1920x400 area)
#    - Source badge at bottom ("X Spaces" / "Nostr" / etc.)
#    - Red accent elements
#    - Protocol Pulse watermark
#
# 3. Alternative: Pillow + numpy waveform frames
#    If ffmpeg showwaves doesn't look good enough:
#    - Load audio with wave module or librosa
#    - Compute RMS energy per frame (30fps)
#    - Render bars with Pillow for each frame
#    - Better control over aesthetics
#    - More cinematic look: mirror bars, gradient colors, glow effects
#
# VERIFICATION GATE:
# V1: Generate a 5-second test audio (ffmpeg -f lavfi -i sine=f=440:d=5 /tmp/test_tone.wav)
# V2: python3 -c "from services.video_engine.graphics.waveform_viz import audio_to_waveform_video; audio_to_waveform_video('/tmp/test_tone.wav', '/tmp/test_wave.mp4')"
# V3: ffprobe /tmp/test_wave.mp4 shows 1920x1080, ~5 seconds
# V4: The waveform actually moves/animates (check multiple frames differ)
#
# git add -A && git commit -m "pipeline phase 7: audio waveform visualization" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 8: GROK TRIAGE — LIVE TEST WITH REAL DATA
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# The Grok triage code exists. Test it with real transcript data.
#
# 1. Read: cat services/video_engine/editorial/grok_triage.py
#
# 2. Create test: tests/test_grok_triage.py
#    - Use transcript data from Phase 3 YouTube scan (or generate test data)
#    - If no real transcripts yet, create a mock transcript from a recent
#      Bitcoin Magazine video (manually transcribe 2 min or use test fixture)
#    - Call GrokTriage.triage(transcripts_dict)
#    - Verify output validates against TriageOutput schema
#    - Check: candidates found, rejections flagged, risk flags identified
#
# 3. Fix any issues:
#    - XAI_API_KEY availability: echo $XAI_API_KEY | head -c10
#    - API endpoint: should be https://api.x.ai/v1/chat/completions
#    - Model: grok-2 or grok-beta (check current available)
#    - If Grok API fails: add Claude fallback for triage
#
# 4. Ensure triage handles all source types:
#    - youtube transcripts
#    - tweet text
#    - nostr post text
#    - spaces transcripts (when available)
#
# VERIFICATION GATE:
# V1: Grok API responds (test with simple prompt first)
# V2: Triage produces valid TriageOutput with candidates
# V3: No sponsor reads or ad segments in candidates
# V4: Schema validation passes
#
# git add -A && git commit -m "pipeline phase 8: grok triage live test" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 9: CLAUDE DIRECTOR — SHOW PLAN GENERATION
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# Test the Claude Director with real triage output.
#
# 1. Read: cat services/video_engine/editorial/claude_director.py
#
# 2. Test with output from Phase 8 (or generate realistic test data)
#    python3 tests/test_claude_director.py
#    - Feed triage output + transcripts to ClaudeDirector
#    - Claude generates complete ShowPlanV2
#    - Verify: stories selected, narrator scripts written, clips defined
#
# 3. Verify show plan quality:
#    - Does it have a cold open script?
#    - Are clip_transcript fields EXACT text from source transcripts?
#    - Are narrator scripts natural, not robotic?
#    - Is there a Signal vs Noise segment?
#    - Is the Community Pulse section filled?
#    - Does it respect the 5-8 minute target?
#
# 4. Fix any issues with prompting, schema validation, or API calls.
#
# VERIFICATION GATE:
# V1: Claude API responds and generates a show plan
# V2: ShowPlanV2 schema validation passes
# V3: At least 2 stories with narration scripts
# V4: Clip definitions reference real source transcripts
#
# git add -A && git commit -m "pipeline phase 9: claude director live test" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 10: CLIP EXTRACTION — PRECISION CUTS
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# Test clip extraction with real show plan + source videos.
#
# 1. Read: cat services/video_engine/editorial/clip_extractor.py
#
# 2. The extractor uses fuzzy text matching to find exact timestamps.
#    It needs:
#    - Word-level Whisper transcripts (from Phase 3)
#    - clip_transcript text from show plan (from Phase 9)
#    - Original downloaded audio/video files
#
# 3. Fix for local execution:
#    - Replace any ultron.extract_clip() calls with local ffmpeg
#    - ffmpeg -ss {start} -to {end} -i {input} -c copy {output}
#    - Verify clips start/end at sentence boundaries (no mid-word cuts)
#
# 4. Create: tests/test_clip_extraction.py
#    - Use show plan from Phase 9
#    - Extract all defined clips
#    - Verify each clip:
#      - Correct duration (within ±2 seconds of specified)
#      - No mid-sentence cuts
#      - Audio quality intact
#
# VERIFICATION GATE:
# V1: At least 2 clips extracted successfully
# V2: Each clip is between 15-120 seconds
# V3: ffprobe confirms valid audio/video in each clip
# V4: Clips don't start or end mid-word
#
# git add -A && git commit -m "pipeline phase 10: clip extraction live test" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 11: ELEVENLABS NARRATION — BROADCAST-QUALITY VOICEOVER
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# Generate all narrator voiceover audio using ElevenLabs.
#
# 1. Read: cat services/video_engine/editorial/narration_generator.py
#
# 2. First, check available voices:
#    curl -s -H "xi-api-key: $ELEVENLABS_API_KEY" "https://api.elevenlabs.io/v1/voices" | python3 -c "import json,sys; voices=json.load(sys.stdin)['voices']; [print(f'{v[\"voice_id\"]}: {v[\"name\"]}') for v in voices[:15]]"
#    
#    Pick a MALE voice with authority — "Adam" or "Josh" or similar deep voice.
#    NOT Jessica (that's the Oracle avatar voice).
#    Update the voice_id in narration_generator.py.
#
# 3. Test generation:
#    - Use narrator scripts from the Phase 9 show plan
#    - Generate audio for EACH segment: cold_open, lead_story_intro, transition, etc.
#    - Apply emotion-aware settings (already in VOICE_SETTINGS dict)
#    - Apply loudnorm filter for broadcast consistency:
#      ffmpeg -i narration.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11 normalized.mp3
#
# 4. Cost tracking:
#    - Log characters used per generation
#    - ElevenLabs charges ~$0.30/1000 chars
#    - A 5-8 minute show uses roughly 3000-5000 chars of narration
#
# VERIFICATION GATE:
# V1: ElevenLabs API returns audio (test with "Welcome to Pulse Check" string)
# V2: All narrator segments generated as MP3/WAV files
# V3: Audio sounds professional — proper pacing, no artifacts
# V4: Loudnorm applied — consistent volume across all segments
# V5: Total character count logged
#
# git add -A && git commit -m "pipeline phase 11: ElevenLabs narration generation" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 12: THUMBNAIL GENERATOR
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30 min
#
# Create: services/video_engine/graphics/thumbnail.py
#
# YouTube-style thumbnails that get clicks.
#
# 1. Function: generate_thumbnail(headline, channel_names, date_str, output_path)
#    - Size: 1920x1080 (YouTube standard)
#    - Dark background with subtle grid pattern
#    - Large bold headline text (2-3 words max, white)
#    - "PULSE CHECK" red badge top-left
#    - Date in corner
#    - Source channel icons/names along bottom
#    - Red accent elements (lines, borders)
#    - Protocol Pulse logo watermark
#
# 2. Also generate vertical thumbnail for shorts:
#    Function: generate_vertical_thumbnail(headline, output_path)
#    - Size: 1080x1920 (9:16)
#    - Same branding but vertical layout
#
# VERIFICATION GATE:
# V1: python3 -c "from services.video_engine.graphics.thumbnail import generate_thumbnail; generate_thumbnail('SAYLOR BUYS 10B', ['Bitcoin Magazine', 'Simply Bitcoin'], '2026-03-03', '/tmp/test_thumb.png')"
# V2: file /tmp/test_thumb.png → PNG, 1920x1080
# V3: Thumbnail looks professional (check visually by opening frame)
#
# git add -A && git commit -m "pipeline phase 12: thumbnail generator" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 13: FULL ASSEMBLY — STITCH EVERYTHING TOGETHER
# ═══════════════════════════════════════════════════════════════════════════
# Time: 60-90 min (CRITICAL PHASE)
#
# Wire up the local_assembler to produce a complete episode.
#
# 1. Create: services/video_engine/assembly/episode_builder.py
#    This is the master assembly function that takes ALL generated assets
#    and produces the final video.
#
#    Function: build_episode(bundle_path) → dict with file paths
#
#    Assembly order:
#    a. INTRO BUMPER (4s) — from motion_graphics
#    b. COLD OPEN narration (15s) — narration audio over dark background with title
#    c. For each STORY:
#       - TITLE CARD (2s) — story number + headline
#       - NARRATOR INTRO (10-20s) — voiceover with waveform or dark card
#       - SOURCE CLIP (60-120s) — the YouTube clip with lower third
#       - NARRATOR ANALYSIS (10-20s) — post-clip voiceover commentary
#    d. SIGNAL vs NOISE (30s) — narration + branded cards
#    e. COMMUNITY PULSE (30s):
#       - Tweet screenshots with narration
#       - Nostr post screenshots with narration
#    f. OUTRO BUMPER (3s) — from motion_graphics
#
#    Technical implementation:
#    - Scale ALL clips to 1920x1080 first (scale_and_pad from ffmpeg_ops)
#    - Generate each segment as separate MP4 files
#    - Concatenate with ffmpeg concat demuxer (fastest, no re-encode)
#    - Add background music bed (low volume, royalty-free or generated)
#    - Final loudnorm pass on entire output
#
# 2. Handle edge cases:
#    - Missing clips → use title card + narration only
#    - Missing tweets → skip Community Pulse tweet section
#    - Missing Nostr → skip Community Pulse Nostr section  
#    - No Spaces data → pipeline continues without it
#
# 3. Output files:
#    - data/episodes/{date}/pulse_check_{date}_full.mp4 (horizontal)
#    - data/episodes/{date}/pulse_check_{date}_thumb.png (thumbnail)
#    - data/episodes/{date}/pulse_check_{date}_audio.mp3 (podcast)
#    - data/episodes/{date}/manifest.json (what was included)
#
# VERIFICATION GATE:
# V1: build_episode produces an MP4 file
# V2: ffprobe: 1920x1080, 30fps, h264 + aac, duration 3-10 minutes
# V3: Video plays from start to finish without errors
# V4: Intro and outro bumpers are present
# V5: At least 1 source clip is included
# V6: Narration audio is audible and synced
# V7: Lower thirds appear during clips
# V8: Thumbnail generated
#
# git add -A && git commit -m "pipeline phase 13: full episode assembly" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 14: SHORTS CREATOR — VERTICAL 9:16 CLIPS
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# Create vertical versions of each story clip for TikTok/IG/YT Shorts.
#
# 1. Read existing: cat services/video_engine/shorts_creator.py
#
# 2. For each story clip in the show plan:
#    - Crop/pad to 1080x1920 (9:16)
#    - Add bottom caption bar with headline text
#    - Add "PULSE CHECK" branded top bar
#    - Add waveform at bottom during audio-only segments
#    - Keep it under 60 seconds
#    - Add a hook in first 3 seconds (text overlay of most compelling quote)
#
# 3. Output: data/episodes/{date}/shorts/short_{n}.mp4 (one per story)
#
# VERIFICATION GATE:
# V1: At least 2 shorts generated
# V2: Each short is 1080x1920 (9:16), under 60s
# V3: Branded elements visible
#
# git add -A && git commit -m "pipeline phase 14: shorts creator" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 15: X TEASER TRAILER
# ═══════════════════════════════════════════════════════════════════════════
# Time: 20-30 min
#
# Create a ~90-second teaser for X/Twitter that previews the full episode.
#
# 1. From the show plan, extract the "teaser_hook" from each clip
#    (the most viral 15-25 second moment)
# 2. Stitch them with fast transitions:
#    Hook1 → red flash → Hook2 → red flash → Hook3 → "Full episode: protocolpulse.io"
# 3. Add energetic background music or tone
# 4. Must be attention-grabbing in first 3 seconds
# 5. Output: data/episodes/{date}/pulse_check_{date}_teaser.mp4
#
# VERIFICATION GATE:
# V1: Teaser exists, 60-120 seconds, 1920x1080
# V2: Contains clips from at least 2 different sources
# V3: Ends with CTA
#
# git add -A && git commit -m "pipeline phase 15: X teaser trailer" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 16: DAILY DRIVER INTEGRATION — WIRE EVERYTHING TOGETHER
# ═══════════════════════════════════════════════════════════════════════════
# Time: 60-90 min
#
# The daily_driver.py orchestrator needs to be updated to use all new components.
#
# 1. Read the full daily_driver.py: cat services/video_engine/daily_driver.py
#
# 2. Update the run() method to use:
#    - local_whisper (instead of ultron HTTP for transcription)
#    - local_assembler (instead of HTTP assembler)
#    - nostr_capture (new source)
#    - spaces_listener (new source, soft dependency)
#    - tweet_screenshot (enhanced screenshots)
#    - motion_graphics (intro/outro/transitions)
#    - waveform_viz (audio visualization)
#    - thumbnail generator
#    - episode_builder (full assembly)
#    - shorts_creator (vertical clips)
#
# 3. Create data directories if they don't exist:
#    mkdir -p data/episodes state data/graphics data/video_engine/cache
#
# 4. Add a --test-run flag that:
#    - Only scans 2 channels (not all 14)
#    - Only generates 1 clip
#    - Skips distribution
#    - Produces a quick 2-3 minute test episode
#
# 5. Full pipeline should be runnable as:
#    cd /home/ultron/protocol_pulse
#    python3 -m services.video_engine.daily_driver --test-run
#
# VERIFICATION GATE:
# V1: python3 -m services.video_engine.daily_driver --test-run --dry-run
#     (Shows plan without executing — no errors)
# V2: python3 -m services.video_engine.daily_driver --test-run
#     (Actually runs and produces output)
# V3: Output files exist in data/episodes/{date}/
# V4: Full episode MP4 plays
# V5: Shorts exist
# V6: Thumbnail exists
# V7: No unhandled exceptions
#
# git add -A && git commit -m "pipeline phase 16: daily driver integration" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 17: FIRST REAL RUN — PRODUCE TODAY'S EPISODE
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-60 min (mostly waiting for processing)
#
# Run the FULL pipeline (not test-run) to produce a real episode.
#
# cd /home/ultron/protocol_pulse
# python3 -m services.video_engine.daily_driver --now --force 2>&1 | tee data/episodes/$(date +%Y-%m-%d)/pipeline.log
#
# Monitor and fix any issues that arise. Common problems:
# - Rate limits (Twitter API, ElevenLabs)
# - GPU memory (if Whisper + other models compete)
# - Disk space (check: df -h /home/ultron)
# - Missing videos (some channels may not have posted in 48h)
#
# VERIFICATION GATE:
# V1: Pipeline completes without fatal errors
# V2: Episode MP4 exists and plays (5-8 minutes)
# V3: At least 3 source channels represented
# V4: Narration is present and audible
# V5: Lower thirds show correct speaker names
# V6: Intro and outro bumpers play
# V7: Thumbnail looks professional
# V8: Shorts generated
# V9: Teaser generated
# V10: Cost log shows reasonable spend (<$5)
#
# git add -A && git commit -m "pipeline phase 17: first real episode produced" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 18: AUTOMATED SCHEDULER — DAILY CRON
# ═══════════════════════════════════════════════════════════════════════════
# Time: 20-30 min
#
# Set up automatic daily execution.
#
# 1. Create: services/video_engine/run_daily.sh
#    #!/bin/bash
#    cd /home/ultron/protocol_pulse
#    source /home/ultron/SadTalker/venv/bin/activate
#    export $(cat .env | xargs) 2>/dev/null
#    python3 -m services.video_engine.daily_driver --now 2>&1 | tee "data/episodes/$(date +%Y-%m-%d)/pipeline.log"
#
# 2. Add crontab:
#    crontab -e
#    # Run Pulse Check daily at 6:00 PM ET (23:00 UTC) — catches full day of content
#    0 23 * * * /home/ultron/protocol_pulse/services/video_engine/run_daily.sh
#
# 3. Add a health check that the Replit frontend can query:
#    Create an endpoint that reports latest episode date, status, and file sizes.
#    Push a small status file: data/episodes/latest_status.json
#    {"date": "2026-03-03", "status": "complete", "duration_sec": 420, "clips": 5, "shorts": 5}
#
# VERIFICATION GATE:
# V1: run_daily.sh executes without errors
# V2: crontab -l shows the scheduled job
# V3: latest_status.json is written after run
#
# git add -A && git commit -m "pipeline phase 18: daily scheduler" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 19: UPLOAD TO REPLIT — CLIPS PAGE DATA
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30-45 min
#
# Push episode data to Replit so the /clips page can display results.
# Push episodes to a publicly accessible location.
#
# 1. Create: services/video_engine/distribution/replit_sync.py
#    - Read latest episode from data/episodes/{date}/
#    - Push metadata to Replit DB:
#      INSERT INTO clip_job (title, source, duration, status, file_url, created_at)
#    - Push video files to Replit static/ or a cloud storage
#      (Note: Replit has limited storage — consider using Cloudflare R2 or similar)
#    - For now: push metadata JSON to Replit, with video URLs pointing to
#      a simple HTTP server on Ultron (or Cloudflare tunnel)
#
# 2. Update /clips page data source:
#    Push to Replit: the clips metadata JSON so the frontend can render
#    Use the Replit relay to execute:
#    - Insert clip records into DB
#    - Or write a JSON file that the /clips route reads
#
# 3. Sync command:
#    ./sync_to_replit.sh (already exists from earlier session)
#    Plus DB insert via relay
#
# VERIFICATION GATE:
# V1: Clip metadata accessible from Replit
# V2: /clips page shows at least 1 clip entry
# V3: Episode data is properly structured
#
# git add -A && git commit -m "pipeline phase 19: replit clip sync" && git push

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 20: FINAL QUALITY AUDIT + DOCUMENTATION
# ═══════════════════════════════════════════════════════════════════════════
# Time: 30 min
#
# 1. Run the full test suite:
#    python3 -m pytest tests/ -v 2>&1 | tail -30
#    (Create any missing test files)
#
# 2. Verify all components:
echo "=== COMPONENT CHECK ==="
python3 -c "from services.video_engine.assembly.local_assembler import LocalAssembler; print('✓ LocalAssembler')" 2>&1
python3 -c "from services.video_engine.assembly.ffmpeg_ops import concat_clips; print('✓ FFmpeg Ops')" 2>&1
python3 -c "from services.video_engine.graphics.motion_graphics import generate_intro; print('✓ Motion Graphics')" 2>&1
python3 -c "from services.video_engine.graphics.waveform_viz import audio_to_waveform_video; print('✓ Waveform Viz')" 2>&1
python3 -c "from services.video_engine.graphics.thumbnail import generate_thumbnail; print('✓ Thumbnail')" 2>&1
python3 -c "from services.video_engine.sources.nostr_capture import fetch_notable_nostr; print('✓ Nostr Capture')" 2>&1
python3 -c "from services.video_engine.sources.spaces_listener import find_recent_spaces; print('✓ Spaces Listener')" 2>&1
python3 -c "from services.video_engine.sources.tweet_screenshot import capture_tweet; print('✓ Tweet Screenshot')" 2>&1
python3 -c "from services.video_engine.local_whisper import transcribe_audio; print('✓ Local Whisper')" 2>&1
python3 -c "from services.video_engine.assembly.episode_builder import build_episode; print('✓ Episode Builder')" 2>&1

echo "=== LATEST EPISODE CHECK ==="
ls -la data/episodes/*/pulse_check_*_full.mp4 2>/dev/null | tail -1
ls -la data/episodes/*/shorts/ 2>/dev/null | tail -3
ls -la data/episodes/*/pulse_check_*_thumb.png 2>/dev/null | tail -1

echo "=== GIT STATUS ==="
git log --oneline -20
#
# 3. Create: docs/VIDEO_PIPELINE.md
#    Complete documentation of:
#    - Architecture overview
#    - How to run manually
#    - How the scheduler works
#    - API keys needed
#    - Cost estimates
#    - Troubleshooting guide
#
# 4. Final git push:
#    git add -A && git commit -m "pipeline phase 20: quality audit + docs" && git push
#
# ═══════════════════════════════════════════════════════════════════════════
# SESSION COMPLETE
# ═══════════════════════════════════════════════════════════════════════════
#
# REPORT what was accomplished:
# - Phases completed with details
# - Episode produced (duration, clip count, file sizes)
# - Any components that need follow-up
# - Cost breakdown (API usage)
# - Recommendations for improvement
