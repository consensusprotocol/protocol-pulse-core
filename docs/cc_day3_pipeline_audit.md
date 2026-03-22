Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Run the most thorough cross-LLM audit in Protocol Pulse history.
Today had 24+ patches to the video pipeline, many of which were partial relay
fixes that masked root causes instead of fixing them. The KeyError bug alone
caused 8+ render failures across 12 hours. This audit finds everything else
lurking before it causes another lost night.

SCOPE: The 5 highest-churn files from today plus the new services built today.

FILES TO AUDIT (in priority order):
1. video_pipeline_v3/script_writer.py         (10 patches today — highest risk)
2. video_pipeline_v3/tts_engine.py            (7 patches today — prosody, voice)
3. overnight_render_loop.py                   (3 patches — forensics, SIGTERM)
4. services/local_watchdog.py                 (3 patches — new service)
5. video_pipeline_v3/assembler.py             (critical — untouched but complex)
6. video_pipeline_v3/clip_selector.py         (new function select_montage_clips)
7. video_pipeline_v3/clip_extractor.py        (new function extract_montage_all)
8. services/montage_producer.py               (new service built today)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — RENDER STATUS CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check render is running and healthy before starting audit:
  pgrep -la python3 | grep overnight
  tail -5 ~/protocol_pulse/video_pipeline_v3/logs/overnight_loop.log
  ls ~/protocol_pulse/video_pipeline_v3/output/2026-03-21/audio/ | wc -l

If render is NOT running: start it first:
  cd ~/protocol_pulse && git pull && python3 overnight_render_loop.py --daemon &

DO NOT interrupt the render. Audit is read-only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — INDIVIDUAL FILE DEEP READS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read each file completely. For each file, look for:

CATEGORY 1 — CRASH RISKS (P0)
- Any remaining .format() calls that touch user-supplied content
- Any unprotected dict access (d["key"] without .get()) on external data
- Any subprocess calls without timeout
- Any file operations without existence checks
- Any import statements inside functions that could fail silently
- Race conditions between cron jobs and running processes
- Any hardcoded paths that may not exist
- Silent exception handling (bare except: pass) hiding real failures

CATEGORY 2 — QUALITY RISKS (P1)
- Functions that claim to do X but actually do Y
- Missing fallback paths (what happens if Ollama is down?)
- Inconsistent state between in-memory and on-disk data
- Log messages that could mislead debugging
- Cron job timing conflicts (two jobs that could collide)
- Missing HOTFIX_EXEMPT on commits that need it
- Any TODO, FIXME, HACK comments indicating known issues

CATEGORY 3 — TECHNICAL DEBT (P2)
- Dead code paths that are never reached
- Duplicate functionality between files
- Functions over 100 lines that should be split
- Missing docstrings on critical functions
- Inconsistent error handling patterns across files

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — CROSS-LLM AUDIT VIA cross_llm_audit.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cross_llm_audit.py exists at ~/protocol_pulse/utils/cross_llm_audit.py.
It sends code to Gemini + GPT-4o + Grok in parallel threads.

For each of the 8 files, run a targeted audit:

python3 utils/cross_llm_audit.py --feature pipeline-day3-audit

BUT FIRST: add a new feature entry to FEATURE_MAP in cross_llm_audit.py:
    "pipeline-day3-audit": ("WATCHDOG_LLM_GOSPEL.md", "main"),

And add to EXPLICIT_FILES:
    "pipeline-day3-audit": [
        "video_pipeline_v3/script_writer.py",
        "video_pipeline_v3/tts_engine.py",
        "overnight_render_loop.py",
        "services/local_watchdog.py",
        "video_pipeline_v3/clip_selector.py",
        "video_pipeline_v3/clip_extractor.py",
        "services/montage_producer.py",
    ],

Run cycle 1:
    python3 utils/cross_llm_audit.py --feature pipeline-day3-audit

Save cycle 1 output path, then run cycle 2:
    python3 utils/cross_llm_audit.py --feature pipeline-day3-audit --cycle 2 --cycle1-results [OUTPUT_FROM_C1]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — SYNTHESIZE AND FIX ALL P0 ISSUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
From the cross-LLM audit output + your own read, compile a definitive list
of P0 issues (crash risks). For each P0:

A) Describe the issue precisely
B) Show the exact lines
C) Write the fix
D) Apply the fix
E) Run: python3 -m py_compile [file] && echo SYNTAX_OK

Fix ALL P0 issues before moving to P1.
Fix P1 issues that are quick wins (under 5 lines).
Document P2 issues but do not fix (too risky mid-render).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — ASSEMBLER.PY SPECIAL AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
assembler.py is the most complex file (1800+ lines) and has NOT been patched
today — meaning any existing bugs are still there. Read it specifically for:

1. Any ffmpeg filter_complex strings built with string concatenation
   (these can fail with special characters in clip metadata)
2. Any calls to files that may not exist (clip paths, audio paths)
   without existence checks before subprocess calls
3. The social segment builder — does it handle empty tweet lists?
4. The intro/outro builders — do they handle missing music files?
5. The PiP (Picture-in-Picture) logic — what happens if clip is corrupt?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — REGRESSION TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh
Must show 0 FAILs before any commit.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — COMMIT ALL FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add [all modified files]
git commit -m "fix(audit): cross-LLM pipeline audit Day 3 — P0/P1 fixes across script_writer, tts_engine, overnight_render_loop, watchdog, assembler"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8 — WRITE AUDIT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write a clear audit report to:
~/protocol_pulse/docs/audits/DAY3_PIPELINE_AUDIT_2026-03-22.md

Format:
## P0 Issues Found and Fixed (N total)
For each: file, line, issue, fix applied

## P1 Issues Found and Fixed (N total)
For each: file, line, issue, fix applied

## P1 Issues Documented (fix in next session)
For each: file, line, issue, recommended fix

## P2 Technical Debt
Summary list

## Cross-LLM Consensus
What Gemini, GPT-4o, and Grok all agreed on
What they disagreed on
Final determination

## Render Safety Assessment
Verdict: is the current render expected to complete without crashes?
What is the remaining risk level?

DO NOT touch: PIPELINE_LAWS.md, any gospel docs, any .env files
DO NOT restart the render loop unless it crashes first
PIPELINE LAW: regression_test.sh must show 0 FAILs before commit
