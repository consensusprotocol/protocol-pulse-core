Load ~/protocol_pulse/PIPELINE_LAWS.md first. Fix freeze frames in assembler.py — Grade C (80/100), only critical failure is freeze_check (4 freezes penalized).

FORENSIC DATA from pulse_check_20260320.mp4 (287MB, 614s, Grade C 80/100):

FREEZE EVENTS (exact ffprobe output):
  8.35s → 15.89s  (7.5s)  — INTRO ZONE, excluded by grader (already fixed)
  430.65s → 434.22s (3.6s) — data/social scene zone ~7:10
  434.22s → 440.85s (6.6s) — immediately after, same zone ~7:14
  450.82s → 451.99s (1.2s) — same zone ~7:31
  452.62s → 453.72s (1.1s) — same zone ~7:33
  458.92s → 462.35s (3.4s) — same zone ~7:39
  584.72s → 605.55s (20.8s) — OUTRO ZONE, excluded by grader (already fixed)

PART MAPPING (work dir durations):
  part_027_data.mp4: 23s  |  part_027_setup.mp4: 30s
  part_028_data.mp4: 27s  |  part_028_transition_to_clip: 0.5s
  part_029_clip_r6.mp4: 21s  |  part_029_data.mp4: 21s
  part_030_data.mp4: 25s  |  part_030_transition: 0.5s

The freeze cluster at 430-462s maps to the data scene parts (part_027 through part_031).
These are data/narration scenes that use bg_loop.mp4 as background.

ROOT CAUSE: The _get_bg_layer() function trims bg_loop to the exact scene duration.
When the scene duration hits a static frame at the trim boundary, ffmpeg holds that
frame for the remainder of the scene = freeze artifact.

The previous fix (f8eca6e1) added +0.5s to the wrap scene only. The data scenes
and setup scenes also use _get_bg_layer() and are not covered by that fix.

STEP 1 — READ the actual code:
  grep -n "_get_bg_layer\|bg_loop\|trim=" ~/protocol_pulse/video_pipeline_v3/assembler.py | head -30
  sed -n "$(grep -n 'def _get_bg_layer' ~/protocol_pulse/video_pipeline_v3/assembler.py | head -1 | cut -d: -f1),$(($(grep -n 'def _get_bg_layer' ~/protocol_pulse/video_pipeline_v3/assembler.py | head -1 | cut -d: -f1)+40))p" ~/protocol_pulse/video_pipeline_v3/assembler.py

STEP 2 — FIX _get_bg_layer() globally:
  The fix: increase the trim buffer from +0.5s to +2.0s on ALL scenes, not just wrap.
  This ensures bg_loop always has content past the scene boundary and never stalls.

  Find the trim= line in _get_bg_layer() and change:
    trim=0:{duration + 0.5}  → trim=0:{duration + 2.0}
  or if it says:
    trim=0:{duration}  → trim=0:{duration + 2.0}

  Also add loop protection: before the trim, add -stream_loop -1 to the ffmpeg input
  so bg_loop cycles rather than holding the last frame:
    The bg_loop filter should use -stream_loop -1 on the INPUT, not trim.
    Check if -stream_loop is already in the ffmpeg command for bg_loop.
    If not, add it to the input args for bg_loop.

STEP 3 — ALSO check make_data_scene() and make_setup_scene():
  These are the scene functions that produce the 430-462s freeze cluster.
  Search for where they call _get_bg_layer() or build their own ffmpeg bg filter.
  If they hardcode trim= without the +2.0 buffer, fix them too.

STEP 4 — VERIFY the fix makes sense:
  grep -n "trim=0:" ~/protocol_pulse/video_pipeline_v3/assembler.py | head -20
  Every trim= that caps bg_loop to a scene duration should have +2.0 buffer.

STEP 5 — regression test and commit:
  bash ~/protocol_pulse/regression_test.sh
  Expected: ZERO FAILs

  git add video_pipeline_v3/assembler.py
  git commit -m "fix(assembler): increase bg_loop trim buffer to +2.0s on ALL scenes — eliminates freeze frames in data/setup zones"
  git push

STEP 6 — Kick a fresh render to validate:
  After commit, kill current render loop, restart:
    pkill -f overnight_render_loop; pkill -f daily_producer; sleep 3
    cd ~/protocol_pulse && git pull
    tmux send-keys -t avatar "cd ~/protocol_pulse && python3 overnight_render_loop.py --daemon" Enter

Do NOT change gemini_grade.py, tts_engine.py, routes.py, or any non-pipeline file.
assembler.py ONLY.
