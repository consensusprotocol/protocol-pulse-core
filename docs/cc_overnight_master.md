Read PIPELINE_LAWS.md first. This is an autonomous overnight session. Work through all tasks in order, commit after each one, and do not stop until everything is done.

## TASK LIST (in order)

### TASK 1 - Wait for and verify assembler_fix CC session
Check if tmux session 'assembler_fix' is still running:
  tmux has-session -t assembler_fix 2>/dev/null && echo running || echo done
If still running, wait (sleep 60, check again) until it finishes.
Then: git pull origin main
Then: grep the last 5 git log entries and verify assembler fix was committed.

### TASK 2 - Wait for and verify avatar_audit CC session
Same as above for tmux session 'avatar_audit'.
After it finishes: git pull origin main

### TASK 3 - Restart avatar server with latest code
  pkill -f avatar_server.py 2>/dev/null; sleep 3
  cd ~/protocol_pulse/oracle && nohup python3 avatar_server.py > logs/avatar_server.log 2>&1 &
  sleep 20
  curl http://localhost:8200/health
Verify avg_latency_sec is less than 20. Log the result.

### TASK 4 - Fix gunicorn.pid in .gitignore
  cd ~/protocol_pulse
  grep -q "gunicorn.pid" .gitignore || echo "gunicorn.pid" >> .gitignore
  git add .gitignore && git commit -m "chore: add gunicorn.pid to .gitignore" && git push || echo "nothing to commit"

### TASK 5 - Fire V10 render
Wipe TTS cache first:
  rm -rf ~/protocol_pulse/video_pipeline_v3/tts_cache/ && mkdir -p ~/protocol_pulse/video_pipeline_v3/tts_cache/
Then fire render:
  cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --skip-scan 2>&1 | tee logs/v10_render.log
This will take 60-90 minutes. Wait for it to complete.

### TASK 6 - Run forensics on V10
After render completes, find the output mp4 (largest non-intermediate file in output/$(date +%Y-%m-%d)/).
Run:
  ffprobe -v quiet -print_format json -show_format -show_streams <video_file>
  ffmpeg -i <video_file> -af "silencedetect=n=-50dB:d=2.0" -f null - 2>&1 | grep silence_start
  ffmpeg -i <video_file> -af "ebur128=peak=true" -f null - 2>&1 | tail -20
Log: duration, true peak, silence gap count, file size.

### TASK 7 - Grade V10
  cd ~/protocol_pulse/video_pipeline_v3 && python3 gemini_grade.py 2>&1 | tee logs/grade_report_v10.log
Wait for grade. Log the result.

### TASK 8 - If Grade A: launch overnight loop. If not Grade A: targeted fix then retry once.
IF grade is A (score >= 88):
  - Save winner config to logs/WINNER_RECIPE.json
  - Launch: tmux new-session -d -s overnight_loop "cd ~/protocol_pulse && python3 overnight_render_loop.py 2>&1 | tee video_pipeline_v3/logs/overnight_loop.log"
  - Log "GRADE A ACHIEVED - overnight loop running"

IF grade is NOT A:
  Read the grade log, identify the top 2-3 failing dimensions.
  Make targeted fixes to assembler.py or tts_engine.py ONLY for the failing dimensions.
  Run regression_test.sh - must show zero FAILs.
  Commit: git add -A && git commit -m "fix(pipeline): targeted V10 grade fixes" && git push
  Wipe TTS cache again, fire V11 render, grade V11.
  If V11 is Grade A, launch overnight loop as above.

### TASK 9 - Update handoff doc
  cd ~/protocol_pulse && bash sync_handoff.sh
This regenerates and pushes CURRENT_STATE.md to GitHub.

### TASK 10 - Final status report
Write a summary to ~/protocol_pulse/docs/overnight_report.md with:
- Which tasks completed
- V10/V11 grade and score
- Whether overnight loop is running
- Any remaining issues for morning
- Git log of all commits made overnight
Then: git add docs/overnight_report.md && git commit -m "chore: overnight session report" && git push

## RULES
- Never skip regression_test.sh before any commit touching pipeline code
- Never merge without zero FAILs
- Commit and push after EVERY task
- If any step fails 3 times, log it and move to the next task
- Do NOT touch: app.py, oracle/avatar_server.py (unless Task 3 restart confirms latency still broken)
- One CC session max on this repo at a time
