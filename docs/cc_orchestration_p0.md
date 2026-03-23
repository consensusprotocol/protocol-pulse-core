Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.

CONTEXT: A cross-LLM audit (Gemini, GPT-4o, Grok, Perplexity) was run against
this pipeline. Claude Code then read the actual codebase and corrected their
findings. Most of what the external LLMs flagged is already solved. The real
P0 list has exactly 5 items. Fix only these 5. Nothing else.

DO NOT touch: assembler.py, tts_engine.py, script_writer.py, gemini_grade.py
These files are already correct. The external LLMs were wrong about them.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P0 FIX 1: flock process lock in daily_producer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add flock-based lock at the start of main() in daily_producer.py.
Prevents multiple producers from running simultaneously.

import fcntl
lock_file = open("/tmp/daily_producer.lock", "w")
try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    logger.error("Another producer is already running. Exiting.")
    sys.exit(1)

Release at end: fcntl.flock(lock_file, fcntl.LOCK_UN)

Verify: run two instances simultaneously, second should exit immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P0 FIX 2: Remove CC self-healing from overnight_render_loop.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The fire_cc_fix() function spawns tmux CC sessions to auto-patch code.
This has caused its own outages — CC sessions conflict with running renders,
introduce new bugs, and create the stale pyc problem.

Replace fire_cc_fix() behavior:
- CLASS A/B: still attempt Qwen patch (local, fast, safe)
- CLASS C: log the failure + send Telegram alert + STOP the iteration
  Do NOT spawn a CC session. Do NOT auto-patch.
  Let the human (or watchdog) decide what to fix.

The watchdog CC healing built earlier is the RIGHT place for CC sessions.
The overnight loop should NOT spawn CC sessions — it's a render loop, not a repair loop.

Find fire_cc_fix() in overnight_render_loop.py.
Replace the CC session spawn with: log error + Telegram alert + return.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P0 FIX 3: Step-level checkpointing in daily_producer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Currently if step 9 fails, the loop restarts from step 1 — wasting all TTS
audio and clips. Add checkpoint resume logic.

write_render_context() already exists (added yesterday). Extend it:
- After each step completes successfully, write step number to context file
- On new render attempt, check context file for last_completed_step
- If last_completed_step >= 4 (clips extracted) and clips still exist:
  skip steps 1-4, resume from step 5 with --skip-scan
- If last_completed_step >= 5 (audio generated) and audio files exist:
  skip steps 1-5, resume from step 6 (assembly only)

This turns a 45-minute full render into a 10-minute assembly-only retry
when the early steps already completed successfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P0 FIX 4: Watchdog tracks actual subprocess PID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current watchdog reads overnight_loop.log and producer_debug.log.
Enhancement: also read /proc/<producer_pid>/fd/* to find actual stderr.

In local_watchdog.py reactive mode:
1. Find the daily_producer.py PID: subprocess.run(['pgrep', '-f', 'daily_producer'])
2. If found, read /proc/<pid>/environ to verify TTS_PROVIDER and keys
3. If TTS_PROVIDER != expected or key missing: CLASS A crash, trigger repair
4. Log the actual env state every health check cycle

This is the /proc check ChatGPT recommended. It confirmed TTS_PROVIDER=elevenlabs
is set, so routine monitoring will catch any future drift immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P0 FIX 5: Harden overnight_render_loop daemon restart behavior
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Currently the daemon restarts the full loop on any failure, losing the
iteration count and resetting the 6-hour clock. Causes "always iteration 1" syndrome.

Fix: preserve state across restarts
- Write current iteration + start_time to /tmp/render_state.json on each iteration
- On startup, read /tmp/render_state.json
- If start_time < 6 hours ago: resume from saved iteration, don't reset clock
- If start_time >= 6 hours ago OR iteration >= 8: start fresh

This means if the loop dies and restarts, it continues from iteration 3
instead of starting over from iteration 1 every time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENTATION ORDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Read overnight_render_loop.py fully
2. Read video_pipeline_v3/daily_producer.py fully
3. Read services/local_watchdog.py fully
4. Implement all 5 fixes
5. python3 -m py_compile on all modified files
6. bash regression_test.sh — 0 FAILs required
7. find /home/ultron -name "*.pyc" -delete
8. git add + commit + push
9. Restart: pkill -f overnight_render_loop && pkill -f daily_producer && sleep 3 && python3 overnight_render_loop.py --daemon &
10. Verify: pgrep -f daily_producer confirms only ONE process after step 9

COMMIT MESSAGE:
fix(orchestration): flock process lock, remove CC self-healing from loop,
step checkpointing, watchdog /proc env check, daemon state persistence


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECOND-PASS CONSENSUS (from ChatGPT, Perplexity, Gemini reviewing CC output)
Add these after the 5 P0 fixes. Same session.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P1 FIX 6: Make post-render QC blocking (ChatGPT)
In daily_producer.py, find "Post-render QC failed (non-blocking)" and change
the behavior: if QC fails, do NOT return success. Return failure so the loop
knows the render is bad and retries. A render that fails QC is not a successful
render regardless of whether the file exists.

P1 FIX 7: Hard-lock TTS provider at startup (ChatGPT)
In tts_engine.py, at the top of the file add a validation block:
  provider = os.environ.get("TTS_PROVIDER", "local").lower()
  if provider == "elevenlabs" and not os.environ.get("ELEVENLABS_API_KEY"):
      raise RuntimeError("TTS_PROVIDER=elevenlabs but ELEVENLABS_API_KEY is missing")
  logger.info(f"TTS provider locked: {provider}")
This makes misconfiguration a hard failure at startup, not a silent fallback.

P1 FIX 8: VRAM cleanup between renders (Gemini)
In daily_producer.py at the start of each render iteration, add:
  try:
      import torch
      if torch.cuda.is_available():
          torch.cuda.empty_cache()
          torch.cuda.synchronize()
          logger.info("VRAM cleared")
  except Exception:
      pass
Prevents memory fragmentation on long-running 4090 sessions.

P1 FIX 9: Episode topic memory — prevent narrative repetition (Gemini)
In script_writer.py, before building the prompt, load the last 3 episode
titles from data/episode_memory.json and inject into the prompt:
  "RECENT EPISODES (do not repeat these topics):
   - [title 1]
   - [title 2]
   - [title 3]"
This prevents 4 consecutive "Bitcoin at $70k" episodes.

P1 FIX 10: Auto-commit rule in all CC specs (addresses your concern)
Add to the bottom of every CC spec going forward:
  "IMPORTANT: Do not ask for confirmation to commit. Run git add, commit,
   and push automatically. The commit is part of the task, not optional."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT MESSAGE (updated):
fix(orchestration): flock lock, remove CC self-healing, step checkpointing,
watchdog PID tracking, daemon state, QC blocking, TTS hard-lock, VRAM cleanup,
topic memory — full consensus from 4-model audit
