Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPREHENSIVE PIPELINE AUDIT — FULL SYSTEM
Protocol Pulse Pulse Check Video Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTEXT:
This pipeline has been patched extensively over multiple sessions.
Individual fixes have resolved individual symptoms but the system
continues to fail in new ways. This audit treats the entire pipeline
as a system and finds everything at once.

History of failures this session alone:
- KeyError: 'Name' — crashed 20+ times across 12 hours
- Root cause: .format() on user content, stale .pyc from git worktrees
- Render loop dying in forensics — subprocess.TimeoutExpired not caught
- Daemon sleeping to 8am regardless of Grade A achievement
- ElevenLabs TTS_PROVIDER not being picked up by running processes
- 4-31 freeze frames from stream_loop=-1 PTS discontinuities
- 4 silence gaps from ElevenLabs API latency
- Social segment never appearing — fetched after script generation
- Space tap scraper crashing on import — missing quotes on set literals
- Watchdog not scanning producer_debug.log — missing all crashes
- Multiple daily_producer processes running simultaneously
- Forensics hanging for hours — WhisperModel blocking synchronously

STEP 1 — REGISTER AUDIT FEATURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add to utils/cross_llm_audit.py:
  FEATURE_MAP["pipeline-comprehensive-audit"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["pipeline-comprehensive-audit"] = [
      "overnight_render_loop.py",
      "video_pipeline_v3/daily_producer.py",
      "video_pipeline_v3/script_writer.py",
      "video_pipeline_v3/tts_engine.py",
      "video_pipeline_v3/assembler.py",
      "services/local_watchdog.py",
  ]

STEP 2 — READ ALL 6 FILES COMPLETELY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read every file in full before running the audit.
Understand the complete flow:
  overnight_render_loop → daily_producer → script_writer
  → tts_engine → assembler → gemini_grade

For each file note:
  - All .format() calls touching user content
  - All subprocess calls without timeout
  - All dict accesses without .get() on external data
  - All bare except: pass hiding failures
  - All hardcoded paths that may not exist
  - All environment variable reads and when they're evaluated
  - All stream_loop=-1 video inputs without trim+setpts

STEP 3 — CYCLE 1 CROSS-LLM AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature pipeline-comprehensive-audit

Each model answers these 8 questions independently:

1. MOST FRAGILE POINT: What single failure in this pipeline would
   cause the most damage and is currently least protected?

2. WRONG ASSUMPTIONS: What does this code assume that is provably
   false given the failure history above?

3. ELEVENLABS ROUTING: TTS_PROVIDER=elevenlabs is set in .env but
   processes are using local Kokoro. Diagnose exactly why and fix it.
   Hint: check HOW .env is loaded in daily_producer.py vs tts_engine.py

4. FREEZE FRAMES: Are all stream_loop=-1 video inputs now protected
   with trim+setpts? Find any remaining unprotected locations.

5. GRADE A BLOCKER: What in the current architecture structurally
   prevents Grade A? Not individual bugs — architectural issues.

6. WATCHDOG GAPS: What failure modes does the watchdog still miss?
   Beyond producer_debug.log — what else is it not watching?

7. SILENCE GAPS: 4 silence gaps still appearing. Root cause beyond
   ElevenLabs latency — what else could cause them in this pipeline?

8. REBUILD VS FIX: For each of the 6 files — rebuild from scratch
   or fix in place? Give one-line rationale for each.

STEP 4 — CYCLE 2 CROSS-EXAMINATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature pipeline-comprehensive-audit --cycle 2 --cycle1-results [C1]

Each model:
1. Identifies the strongest finding from the other two models
2. Challenges the weakest finding from the other two models
3. Produces a ranked list of P0 fixes (must fix before next render)

STEP 5 — IMPLEMENT ALL P0 FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Based on consensus P0 list — fix every P0 issue across all 6 files.
For each fix:
  a) Show exact lines changed
  b) python3 -m py_compile [file] — syntax check
  c) Explain why this prevents the historical failure

Fix ElevenLabs routing as highest priority P0.
Fix any remaining stream_loop issues.
Fix any remaining watchdog gaps.

STEP 6 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs
find /home/ultron -name "*.pyc" -delete
git add overnight_render_loop.py video_pipeline_v3/daily_producer.py
git add video_pipeline_v3/script_writer.py video_pipeline_v3/tts_engine.py
git add video_pipeline_v3/assembler.py services/local_watchdog.py
git commit -m "fix(pipeline): comprehensive cross-LLM audit — all P0 issues resolved across 6 files"
git push

STEP 7 — RESTART RENDER + VERIFY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After commit:
  find /home/ultron -name "*.pyc" -delete
  pkill -f overnight_render_loop
  pkill -f daily_producer
  cd ~/protocol_pulse && python3 overnight_render_loop.py --daemon &

Watch the first render through Step 5 and confirm:
  - No KeyError
  - TTS_PROVIDER shows elevenlabs in logs
  - Audio lines count increases past 29
  - Work files increase past 101
  - Video file timestamp is fresh (today, not Mar 22 15:45)

STEP 8 — UPDATE QWEN CONTEXT BIBLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For every new failure pattern discovered in this audit,
append to ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md immediately.
Root cause, fix, verify steps, watchdog action.


IMPORTANT: Do not ask for confirmation before committing. Run git add, git commit, and git push automatically. The commit is part of the task, not optional.
