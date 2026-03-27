Read PIPELINE_LAWS.md fully.
Read video_pipeline_v3/assembler.py lines 1-50 to understand structure.
Read video_pipeline_v3/assembler.py - search for "itsoffset", "audio_offset", "setpts", "asetpts", "concat", "social", "tweet", "transcript".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE FIX SESSION — PBX HUMAN REVIEW FEEDBACK (B GRADE 81/100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RENDER FILE: video_pipeline_v3/output/2026-03-25/pulse_check_20260325.mp4
ALL SYMPTOMS REPORTED BY HUMAN REVIEWER:

SYMPTOM 1 — AUDIO TRACK PULLED FORWARD ~0.5s (CRITICAL — LIKELY ROOT CAUSE OF MOST ISSUES)
Evidence: Outro audio played early, outro visual came in late. Lip sync off on ALL partner
channel clips. Wrong tweet on screen while different tweet is being narrated.
HYPOTHESIS: The assembled audio is offset ~0.5s early relative to video timeline.
ACTION: Run this ffprobe analysis on the render file FIRST before changing anything:
  ffprobe -v quiet -print_format json -show_streams \
    video_pipeline_v3/output/2026-03-25/pulse_check_20260325.mp4 \
    | python3 -c "import sys,json; d=json.load(sys.stdin); [print(s['codec_type'], s.get('start_time'), s.get('start_pts')) for s in d['streams']]"
  
  Also run:
  ffprobe -v quiet -print_format json -show_streams \
    video_pipeline_v3/output/2026-03-25/pulse_check_20260325.mp4.concat_raw.mp4 \
    | python3 -c "import sys,json; d=json.load(sys.stdin); [print(s['codec_type'], s.get('start_time'), s.get('start_pts')) for s in d['streams']]"

If audio start_time differs from video start_time by ~0.5s, confirm the hypothesis.

FIX: In assembler.py, find where audio is merged with video (look for ffmpeg concat, 
amix, or amerge commands). Add/correct the audio delay to match video:
  -itsoffset should be set to 0 for audio (not positive which would pull it forward)
  OR if using filter_complex, ensure asetpts=PTS-STARTPTS is applied after concat
  The fix should be: ensure audio and video start_time are both 0.000 in the final output.

SYMPTOM 2 — TRANSCRIPT TEXT BURNED INTO PARTNER CLIP FRAMES
Partner channel clips (highlighted segments from YouTube channels) have transcript/subtitle
text visible as overlaid text burned into the video frame itself.
Find in assembler.py or clip_extractor.py where partner clips are processed.
Look for: drawtext, subtitles, ass, srt, vf filter with text.
Remove any subtitle/transcript overlay from partner channel clips.
These clips should be clean — no burned-in text.

SYMPTOM 3 — WRONG TWEET ON SCREEN DURING SOCIAL SEGMENT
At ~9:47 "What Bitcoin Internet Is Saying" segment: @nvk tweet stays on screen
while narration reads TFTC and Marty Bent tweets.
Find in assembler.py the social segment assembly. The tweet display clips must be
synchronized to match the narration order exactly.
Each tweet visual must appear at the exact moment narration begins reading that tweet.
Check the timing logic for social segment clip sequencing.

SYMPTOM 4 — TRANSITION WOOSH WITH NO VISUAL CHANGE (8:49 and 9:05)
Transition sound plays but screen doesn't change to new segment visual.
Find transition insertion logic in assembler.py.
The transition audio cue must be paired with a visual transition (fade, cut, or wipe).
If no visual asset is available, remove the audio cue too — silence is better than mismatch.

SYMPTOM 5 — TTS PRONUNCIATION FIXES (ElevenLabs)
PBX voice mispronounces:
  - "$2B" reads as "two dollars B" → should be "2 billion dollars"
  - "Marty" (Bent) mispronounced
Find in script_writer.py or tts_engine.py where text is prepared for ElevenLabs.
Add a pre-TTS text normalization function:
  - Replace "$(\d+)B\b" → "\1 billion dollars"
  - Replace "$(\d+)M\b" → "\1 million dollars"  
  - Replace "$(\d+)T\b" → "\1 trillion dollars"
  - Add "Marty" to pronunciation dictionary if ElevenLabs supports it
  - Also handle "2B", "5B", "10B" patterns (no dollar sign)

SYMPTOM 6 — SEGMENT TRANSITION TIMING (9:47 segment boundary)
Last few frames of "Today's Intelligence" segment still showing when 
"What Bitcoin Internet Is Saying" narration has already begun.
The segment start frame must be exactly aligned with when narration begins.
Add 0-frame buffer between segments (no overlap, no gap).

AFTER ANALYSIS:
1. Report the audio/video start_time offset values from ffprobe
2. If offset confirmed, implement the fix in assembler.py
3. Fix transcript burn-in on partner clips
4. Fix tweet sync logic
5. Fix TTS number normalization
6. Run: bash regression_test.sh — must show 0 FAILs
7. git add -A && git commit -m "fix(pipeline): audio offset, tweet sync, transcript burn-in, TTS normalization — PBX B-grade review" && git push
