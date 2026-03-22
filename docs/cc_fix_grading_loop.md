Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Fix the grading loop — grade must fire automatically after every render
without manual intervention. Also fix the remaining freeze frame detection issue.

DO NOT touch: assembler.py, tts_engine.py, daily_producer.py, script_writer.py

STEP 1 — AUDIT THE GRADING LOOP
Read overnight_render_loop.py run_forensics() and grade_with_gemini() fully.
Find exactly why forensics times out and kills the loop.
Check: does run_forensics() complete in under 10 minutes on a 7-minute video?
  time ffmpeg -i output/2026-03-22/pulse_check_20260322.mp4 -vf "freezedetect=n=0.003:d=1.0" -an -f null - 2>&1 | tail -3
Note: the threshold n=0.003 is more appropriate than n=0.001 for this content.

STEP 2 — FIX FORENSICS TIMEOUT
The TTS artifact check subprocess (WhisperModel) may still be blocking.
Verify the subprocess has a hard 45s timeout and cannot block the loop.
Add a total forensics timeout: if run_forensics() takes >8 minutes total, return {} and continue.
Implement using threading.Timer or subprocess.run with timeout on the entire forensics call.

STEP 3 — FIX FREEZE FRAME DETECTION THRESHOLD
Current: freezedetect=n=0.001:d=1.0 — too sensitive, flags bg_loop transitions
Fix: freezedetect=n=0.003:d=1.5 — matches the Grade B episode behavior
Update the threshold in run_forensics() and in gemini_grade.py.

STEP 4 — FIX GRADE AUTO-FIRE
The grade must fire automatically. Verify the fallback path works:
  When grade_with_gemini() fails → run gemini_grade.py as subprocess → parse result
Test the full flow: python3 overnight_render_loop.py --test-grade output/2026-03-22/pulse_check_20260322.mp4
(add --test-grade flag if it doesn't exist)

STEP 5 — REGRESSION + COMMIT
bash regression_test.sh
git add overnight_render_loop.py
git commit -m "fix(loop): forensics timeout protection, freeze threshold n=0.003, grade auto-fires every render"
git push