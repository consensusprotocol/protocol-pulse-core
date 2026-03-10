# VIDEO FIX SPRINT - THREE CONFIRMED BUGS
# Load PIPELINE_LAWS.md first, then fix in order.

## SETUP
cd ~/protocol_pulse
cat PIPELINE_LAWS.md
git checkout feature/video-audio-fix

## BUG 1 (CRITICAL): NO NARRATOR VOICES
EVIDENCE: 193kbps AAC audio exists but zero audible voices.
TTS cache has 130+ .m4a files (4s-21s each). ElevenLabs IS working.
The voice audio is being generated but not reaching the listener.

DIAGNOSIS STEPS:
1. Add debug print in daily_run.py after generate_all_audio() to log
   audio_paths['segments'] - show first 3 paths + file sizes
2. In assemble_episode(), trace how audio_path flows to segment builders
3. Check if the per-segment .mp4 files have audio streams (ffprobe on a
   work_dir segment file during a test run)
4. Check concatenate_parts() - is [0:a] actually voice or silence?

MOST LIKELY CAUSE:
The audio_paths dict from generate_all_audio() has correct paths at
generation time but the files are in run_dir which gets cleaned up.
OR: individual segment builds are failing silently and returning video
with no audio, so concat_raw has no voice, only BGM gets added.

FIX: Whatever the cause, ensure TTS audio paths are valid and present
when assemble_episode() uses them. Add validation: if segment audio
file missing at assembly time, re-generate it from tts_cache.

## BUG 2 (CRITICAL): PIP SHOWS STATIC THUMBNAIL NOT VIDEO
EVIDENCE: PiP overlay during narration shows static image, not playing video.

ROOT CAUSE:
make_pip_preview() gets clip_path. If it is a JPEG (thumbnail), ffprobe
returns 0 duration, function returns ''. But cold open thumbnail persists.

FIX:
1. In make_pip_preview(): if clip_path.lower().endswith(('.jpg','.jpeg','.png')):
   return '' immediately
2. In assemble_episode() PiP build loop: only call make_pip_preview if
   extracted_clip has path ending in .mp4 with duration > 30s
3. PiP must loop: use -stream_loop -1 in extraction if needed
   Extract full narration_duration of video from the clip, not just 8s

## BUG 3 (HIGH): COLD OPEN ASSET OVERLAP
EVIDENCE: Opening frame shows thumbnail face panel overlapping text.

ROOT CAUSE:
In make_intro_coldopen(): thumbnail scaled to 1056:1080 overlaid at x=0:y=0
Then drawtext at x=(w-text_w)/2 = ~960px = CENTER of thumbnail. Collision.

FIX (apply Option A):
Remove thumbnail overlay from cold open entirely.
Per PIPELINE_LAWS: cold open = pure dramatic hook, no logos/watermarks.
Cold open = #0A0A0F bg + subtle grid + date text only. Clean and cinematic.
Delete lines 573-595 block (has_thumb_co / thumbface / thumbblend logic).
Set face_base = 'bgclean' unconditionally.

## STEP 4: BUILD GEMINI FILE API QC SCRIPT
File: ~/protocol_pulse/utils/gemini_video_qc.py

Install: pip3 install google-generativeai --break-system-packages

The script uploads the full MP4 to Gemini File API (not frame extraction).
Gemini 2.5 Pro watches the ACTUAL VIDEO with AUDIO and grades it.
Model: gemini-2.5-pro
Key: os.environ['GEMINI_API_KEY']

Prompt asks Gemini to score 0-10 on: voices, pip, cold_open, background,
debug_text, audio_quality, pacing. Returns JSON with overall_grade A-F.
Also returns: top_3_fixes list + claude_code_prompt for next pass.

Output: ~/protocol_pulse/logs/gemini_qc/TIMESTAMP/GEMINI_QC_REPORT.json

## STEP 5: RENDER-QC-FIX LOOP
After all 3 bugs fixed and gemini_video_qc.py built:

LOOP until Gemini overall_grade == 'A':
  1. python3 video_pipeline_v3/daily_run.py
  2. ffmpeg blackdetect + silencedetect + ebur128 check
  3. python3 utils/gemini_video_qc.py <output.mp4>
  4. Apply fixes from claude_code_prompt in the report
  5. regression_test.sh must pass
  6. git add -A && git commit -m 'fix: cycle N' && git push
  7. Update ~/protocol_pulse/logs/refinement_cycles.md
  If grade = A: STOP. Print silver platter URL.
  Max 10 cycles.

## LAWS
- Mark voice: 1SM7GgM6IMuvQlz2BwM3 at 1.10x speed
- No MuseTalk, SadTalker
- apply_blink() = `return frame` (disabled)
- Zero debug text in output
- regression_test.sh zero FAILs before commit
- git add -A && commit && push every cycle

## START: Fix Bug 1 now. Trace the audio path.
