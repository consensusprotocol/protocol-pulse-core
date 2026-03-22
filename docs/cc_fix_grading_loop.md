Read ~/protocol_pulse/PIPELINE_LAWS.md first.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY AUDIT-FIRST LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO NOT write any code until the cross-LLM audit completes.
The audit fires Gemini + GPT-4o + Grok in parallel on the actual files.
Their consensus determines what gets built and how.
This is non-negotiable — skipping the audit is what caused every regression tonight.

TASK: Fix the grading loop — grade must fire automatically after every render.
Tonight the grade fired manually 6+ times because the loop kept dying in forensics.

FILES IN SCOPE:
- overnight_render_loop.py
- video_pipeline_v3/gemini_grade.py
DO NOT touch: assembler.py, tts_engine.py, daily_producer.py, script_writer.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CROSS-LLM AUDIT (Cycle 1 + 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse
python3 utils/cross_llm_audit.py --feature fix-grading-loop
[save C1 output]
python3 utils/cross_llm_audit.py --feature fix-grading-loop --cycle 2 --cycle1-results [C1_OUTPUT]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — IMPLEMENT ALL AUDIT P0 FINDINGS PLUS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Known issues to fix:
1. run_forensics() has no total timeout — individual ffmpeg calls have timeouts
   but if the function hangs between calls, the loop dies.
   Fix: wrap entire run_forensics() in a thread with 10-minute hard timeout.
   If it times out, return {} and log warning — loop continues to grading.

2. grade_with_gemini() failing silently — the fallback subprocess path needs
   to correctly parse gemini_grade.py output.
   Verify the GRADE_X_PASS/FAIL line format and parse it correctly.

3. freeze detection threshold too sensitive:
   Change freezedetect=n=0.001 to n=0.003 in run_forensics().
   Change freezedetect=n=0.001 to n=0.003 in gemini_grade.py.
   The current threshold flags bg_loop transitions as freeze frames.

4. Loop never logs "GRADE:" line — add explicit logging after every grade result
   so monitoring tools can detect success.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — END-TO-END TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test forensics runs in under 10 minutes:
  time python3 -c "
  import sys; sys.path.insert(0,'video_pipeline_v3')
  import overnight_render_loop as l
  r = l.run_forensics('video_pipeline_v3/output/2026-03-22/pulse_check_20260322.mp4')
  print('forensics result:', r)
  "
Test grade fires automatically:
  python3 -c "
  import overnight_render_loop as l
  f = l.run_forensics('video_pipeline_v3/output/2026-03-22/pulse_check_20260322.mp4')
  g = l.grade_with_gemini('video_pipeline_v3/output/2026-03-22/pulse_check_20260322.mp4', f, '')
  print('grade:', g.get('grade') if g else 'FAILED')
  "

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh
git add overnight_render_loop.py video_pipeline_v3/gemini_grade.py
git commit -m "fix(loop): forensics 10min thread timeout, freeze threshold n=0.003, grade auto-fires every render"
git push