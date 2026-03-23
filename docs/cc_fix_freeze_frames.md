Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Eliminate all remaining freeze frames. Grade D shows 5 freeze frames still
occurring after the PiP fix. Root cause: 8 locations in assembler.py use
stream_loop=-1 without proper PTS reset, causing timestamp discontinuities at
loop boundaries that freezedetect flags as freeze frames.

FILES IN SCOPE: video_pipeline_v3/assembler.py ONLY
DO NOT touch: tts_engine.py, overnight_render_loop.py, daily_producer.py, script_writer.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CROSS-LLM AUDIT (mandatory)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse
python3 utils/cross_llm_audit.py --feature fix-freeze-frames
[save C1 output path]
python3 utils/cross_llm_audit.py --feature fix-freeze-frames --cycle 2 --cycle1-results [C1_PATH]

Register the feature first by adding to FEATURE_MAP and EXPLICIT_FILES in
utils/cross_llm_audit.py:
  "fix-freeze-frames": ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["fix-freeze-frames"] = ["video_pipeline_v3/assembler.py"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — AUDIT ALL stream_loop=-1 LOCATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find every location in assembler.py using stream_loop=-1 or loop=-1:
  grep -n "stream_loop\|loop=-1\|loop=.*-1" video_pipeline_v3/assembler.py

For EACH location, determine:
  a) Is this a VIDEO stream? (needs trim+setpts fix)
  b) Is this an AUDIO stream? (music loops are fine — audio doesn't cause freeze frames)
  c) Does it already have trim+setpts applied after the loop?

The freeze frame fix: for any VIDEO stream using stream_loop=-1, immediately
after the loop filter apply: trim=0:{duration},setpts=PTS-STARTPTS
This resets timestamps to be monotonically increasing with no discontinuities.

Known locations requiring the fix (video only):
  Line 121: BG_LOOP input for narrator segments
  Line 1833: pip_video_path for PiP panel (already partially fixed)
  Line 4353: BG_LOOP in outro
  Line 4544: BG_LOOP in data segment
  Line 4915: BG_LOOP in another segment

Audio loops (stream_loop=-1 on music files) do NOT cause freeze frames — skip:
  Line 4217: BG_MUSIC (audio only)
  Line 4260: BG_MUSIC (audio only)
  Line 4309: INTRO_MUSIC_FILE (audio only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — IMPLEMENT FIX FOR EACH VIDEO stream_loop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each video stream_loop=-1 location, find the filtergraph string that
processes that input and add trim+setpts immediately after scale/crop:

Pattern to find:
  f"[{idx}:v]scale=1920:1080..."
  
Pattern after fix:
  f"[{idx}:v]trim=0:{duration},setpts=PTS-STARTPTS,scale=1920:1080..."

The duration variable to use depends on context:
  - For BG_LOOP used as background: use total_dur (segment duration)
  - For PiP video: use total_dur
  - Always add +0.5s safety buffer: trim=0:{total_dur + 0.5}

Read the _get_bg_layer() function fully — this is the primary source of BG_LOOP
usage. Apply the fix there so ALL callers inherit it automatically.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — VERIFY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 -m py_compile video_pipeline_v3/assembler.py && echo SYNTAX_OK

Run a quick freeze check on the existing video to confirm threshold:
  ffmpeg -i output/2026-03-22/pulse_check_20260322.mp4 \
    -vf "freezedetect=n=0.003:d=2.0" -an -f null - 2>&1 | grep freeze_start | wc -l

After next render completes, freeze count must be 0 or 1 maximum.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh  # must show 0 FAILs
git add video_pipeline_v3/assembler.py
git commit -m "fix(assembler): trim+setpts on ALL bg_loop video stream_loops — eliminates freeze frame PTS discontinuities at loop boundaries"
git push

IMPORTANT: Do not ask for confirmation before committing. Run git add, git commit, and git push automatically. The commit is part of the task, not optional.
