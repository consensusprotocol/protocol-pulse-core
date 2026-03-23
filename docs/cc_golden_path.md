Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: GOLDEN PATH TEST HARNESS
~/protocol_pulse/tests/golden_path.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT THIS IS:
A single CLI script that runs a complete, deterministic end-to-end
render using fixed canned inputs, then asserts on every output.
No live APIs. No random clip selection. Same inputs every time.
Same expected outputs every time.

This is the thing that gives you confidence no automated agent can
give by inspection. Run it before every CC session. Run it after.
If it passes, the pipeline is sound. If it fails, you know exactly
what broke and when.

WHY IT MATTERS:
Right now there is no way to tell if a new CC session accidentally
broke something that was previously working. You find out at 2am
when the render fails. The golden path test finds it in 5 minutes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create: ~/protocol_pulse/tests/golden_path.py
Create: ~/protocol_pulse/tests/fixtures/golden_selections.json
Create: ~/protocol_pulse/tests/fixtures/golden_script.json
Create: ~/protocol_pulse/tests/fixtures/golden_brief.json

STEP 1 — CREATE FIXED FIXTURE FILES

golden_selections.json: a fixed set of 5 pre-downloaded clips
  Use clips already in video_pipeline_v3/output/ from a known good render.
  Hard-code their paths, durations, scores, channels.
  These never change. Same clips every time.

golden_script.json: a fixed dialogue script
  A pre-written script with 8-10 lines across hosts 1 and 2.
  No LLM calls needed. Same script every time.
  Include one SOCIAL segment and one WRAP segment.

golden_brief.json: a fixed morning brief
  Hard-coded BTC price ($84,000), FNG score (28), mood (tense).
  No API calls. Static.

STEP 2 — THE TEST RUNNER

golden_path.py runs these checks in order, timing each one:

CHECK 1 — IMPORTS (< 5 seconds)
  Import all pipeline modules without error.
  Verify TTS_PROVIDER env var is set and matches expected.
  Verify all API keys present in environment.
  Verify GPU available (nvidia-smi).
  PASS/FAIL with exact error.

CHECK 2 — TTS GENERATION (< 120 seconds)
  Run tts_engine.py on 3 lines from golden_script.json.
  Assert: output files exist and are non-zero.
  Assert: audio duration is between 2s and 30s per line.
  Assert: sample rate is 44100 or 48000 Hz (not 0).
  Assert: TTS provider used matches TTS_PROVIDER env.
  Log: which TTS provider was used.
  PASS/FAIL.

CHECK 3 — ASSEMBLY (< 180 seconds)
  Run assembler.py with golden_selections.json + 3 TTS lines.
  Assert: output .mp4 file exists and size > 10MB.
  Assert: duration is between 60s and 900s.
  Assert: resolution is 1920x1080.
  Assert: frame rate is 29.97 or 30fps.
  Assert: freezedetect finds 0 freeze frames (n=0.003:d=1.5).
  Assert: silencedetect finds 0 silence gaps > 0.8s in middle 80%.
  Assert: loudness integrated is between -18 and -10 LUFS.
  Assert: true peak is <= -0.5 dBFS.
  PASS/FAIL with exact metric values.

CHECK 4 — PROCESS LOCK (< 5 seconds)
  Spawn two daily_producer.py processes simultaneously.
  Assert: second process exits with "Another producer running" within 3s.
  Assert: only one process running after 5s.
  PASS/FAIL.

CHECK 5 — WATCHDOG DETECTION (< 30 seconds)
  Write a fake KeyError traceback to /tmp/producer_debug.log.
  Run local_watchdog.py --mode reactive.
  Assert: watchdog detected the crash (check watchdog log for "CRASH DETECTED").
  Assert: watchdog did NOT spawn a CC session (check tmux list-sessions).
  Clean up fake log entry.
  PASS/FAIL.

CHECK 6 — RENDER CONTEXT FILE (< 5 seconds)
  Verify /tmp/render_context_YYYYMMDD.json exists from recent render.
  Assert: has required fields (episode_date, steps_completed, btc_price).
  Assert: steps_completed contains at least [1, 2].
  PASS/FAIL.

CHECK 7 — GLOBAL TWEET GATE (< 10 seconds)
  Import can_post_tweet from services/x_service.py.
  Post 4 tweets in rapid succession to the gate.
  Assert: first 3 allowed, 4th blocked (daily limit).
  Reset the test entries from the DB after.
  PASS/FAIL.

STEP 3 — OUTPUT FORMAT

python3 tests/golden_path.py

Output:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROTOCOL PULSE — GOLDEN PATH TEST
Run: 2026-03-23 01:30:00 ET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PASS] CHECK 1: Imports + env         (2.1s)
[PASS] CHECK 2: TTS generation        (47.3s) — provider: elevenlabs
[PASS] CHECK 3: Assembly              (142.8s) — 0 freezes, -14.2 LUFS
[PASS] CHECK 4: Process lock          (3.2s)
[PASS] CHECK 5: Watchdog detection    (8.1s)
[PASS] CHECK 6: Render context file   (0.1s)
[PASS] CHECK 7: Tweet gate            (0.8s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESULT: 7/7 PASS — pipeline is SOUND
Total time: 204.4s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

On failure:
[FAIL] CHECK 3: Assembly — FREEZE FRAMES: 4 detected (threshold: 0)
       Expected: 0 freeze frames
       Got: 4 freeze frames at t=12.3s, t=34.1s, t=67.8s, t=89.2s
       Fix: check assembler.py stream_loop PTS handling

STEP 4 — WIRE INTO WORKFLOW

Add to regression_test.sh — run before any commit:
  python3 tests/golden_path.py --quick  (checks 1,4,5,6,7 only — 30s)

Add to overnight_render_loop.py — run before first render of day:
  result = subprocess.run(['python3', 'tests/golden_path.py', '--quick'])
  if result.returncode != 0:
      logger.error("Golden path preflight FAILED — aborting render")
      send_telegram("⚠️ PREFLIGHT FAILED — render aborted, check golden_path.py")
      sys.exit(1)

STEP 5 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 tests/golden_path.py  # must show 7/7 PASS
bash regression_test.sh       # must show 0 FAIL
git add tests/
git commit -m "feat(tests): golden path test harness — 7 checks, deterministic, CI-ready"
git push

IMPORTANT: Do not ask for confirmation before committing.
Run git add, commit, and push automatically.
The commit is part of the task, not optional.
