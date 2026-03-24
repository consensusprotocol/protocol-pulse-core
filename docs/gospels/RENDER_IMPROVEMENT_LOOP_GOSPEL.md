# RENDER IMPROVEMENT LOOP — GOSPEL
# render_improvement_loop.py
# Version: 1.1 — PATCHED BY CROSS-LLM AUDIT (2026-03-24, Gemini+GPT-4o+Grok, 2 cycles)
# DO NOT MODIFY WITHOUT FULL LLM AUDIT CYCLE

## MISSION
Autonomous, self-improving render loop that ingests a Gemini grade JSON,
identifies every failing dimension, surgically audits the responsible code,
reaches multi-LLM consensus on the fix, implements via CC, verifies,
then fires the next render — with zero human intervention.
Target: every render iteration improves on the last. Loop runs until Grade A (90+).

## LAWS (inviolable — if any is violated, the loop aborts and alerts PBX)

LAW 1 — SURGICAL CONTEXT ONLY
Never send full files to external LLMs. Max 120 lines per audit payload.
Each failing grade dimension maps to a specific code section. Only that section
is audited. Broad context = generic output = wasted tokens = failure.

LAW 2 — QWEN FIRST, ALWAYS (cost law)
Qwen3 runs locally on 4090 via Ollama — $0 per call.
Qwen does: file reading, candidate identification, root cause hypothesis,
code section extraction (exact line ranges). Qwen output feeds into
external LLMs as pre-filtered context. External LLMs never see raw files.
Estimated savings: 70% reduction in external API spend.

LAW 3 — GRADE JSON IS THE CONTRACT
Loop ingests grade_iterN.json. Extracts all dimensions with score < 8.
Maps each failing dimension to its responsible file+function via
DIMENSION_MAP (defined below). Only mapped sections go to audit.
Unmapped dimensions → route to DEFAULT_HANDLER (see below), alert PBX.

LAW 4 — EXTERNAL LLMS IN PARALLEL, NOT SEQUENCE
Gemini + GPT-4o fire simultaneously in threads (same pattern as
existing cross_llm_audit.py). Never sequential. Timeout: 45s per call.
If one LLM times out → proceed with the other + Qwen. Never block loop.

LAW 5 — CONSENSUS REQUIRED FOR IMPLEMENTATION
A fix is implemented ONLY if Qwen + at least 1 external LLM agree on
root cause. "Same" means: same file, same function, same mechanism.
Vague agreement is not consensus. Specific agreement is consensus.
If models disagree → write disagreement to QWEN_CONTEXT_BIBLE.md,
alert PBX via Telegram, skip this dimension, continue with others.
Never implement a contested fix autonomously.

LAW 6 — VERIFICATION GATE — MANDATORY BEFORE NEXT RENDER
After CC implements fix:
  a) Diff sanity check: if files changed > expected OR diff > 50 lines, REJECT immediately
  b) regression_test.sh → must show 0 FAILs
  c) Dimension-specific test (freeze: freezedetect, audio: ebur128, etc.)
  d) If all pass → git commit → next render fires
  e) If any fails → automated `git revert HEAD` → Telegram alert → retry audit (max 2 retries)

LAW 7 — QWEN_CONTEXT_BIBLE.md IS INSTITUTIONAL MEMORY
Before every audit cycle, loop reads QWEN_CONTEXT_BIBLE.md.
After every fix (successful or failed), loop appends to it.
Pattern: dimension, root_cause, fix_applied, verify_result, iteration.
This prevents re-discovering solved problems. Ever.

LAW 8 — TOKEN BUDGET ENFORCEMENT (AUDIT-REVISED)
Per-dimension budget: simple fix = $0.75, complex refactor = $2.00.
Cycle soft cap: $7.50 (all external LLM calls including CC session).
Daily hard cap: $25.00. If soft cap hit → Qwen-only mode for remaining dims.
If hard cap hit → loop pauses, alerts PBX with cost report, writes
`"status": "failed"` to IPC JSON.
Track spend per call using tiktoken estimation before firing.
Log all costs to persistent ledger: `/tmp/llm_cost_run_YYYYMMDD.json`.
Tiered model selection: Sonnet for targeted single-function fixes,
Opus only for architectural refactors — governed by `fix_complexity`
field in DIMENSION_MAP entries.
Configurable via env: `MAX_TOKENS_PER_FIX_CYCLE`.

LAW 9 — ONE CC SESSION AT A TIME (ZOMBIE-SAFE)
The loop never fires a CC session while another is active on same repo.
Detection is TWO-LAYER (not just tmux ls):
  1. Check tmux session exists by name
  2. Verify live `claude` process inside session:
     `tmux list-panes -t <session> -F "#{pane_pid}"` → verify PID alive via `/proc/<pid>/status`
  3. Check session has had recent activity (< 10 min):
     `tmux display-message -t <session> -p "#{session_activity}"`
If session exists but fails liveness checks → `tmux kill-session -t <session>`,
log ZOMBIE_SESSION_DETECTED, launch fresh.
Hard timeout on waiting for any CC session response: 30 minutes.
On timeout → mark fix attempt as `"status": "timeout"` in IPC JSON.

LAW 10 — NEVER TOUCH RENDER_MAIN
The loop NEVER sends keys to render_main. It only reads its log.
All fixes go in separate CC sessions. Render loop and fix loop are
completely isolated processes.

LAW 11 — FAIL FAST, FAIL LOUD (AUDIT-ADDED)
Every failure must be logged with full context and trigger a Telegram alert.
Silent failures are pipeline-killing defects.
Fire-and-forget patterns are BANNED — every async operation must have
a confirmation protocol and a timeout.

LAW 12 — CLEAN STARTUP STATE (AUDIT-ADDED)
On startup, both overnight_render_loop.py and render_improvement_loop.py
must glob-delete all stale IPC files:
  `/tmp/fix_request_iter*.json`
  `/tmp/fix_complete_iter*.json`
  `/tmp/improvement_loop.heartbeat.json`
  `/tmp/cc_session.heartbeat.json`
This ensures no stale artifacts from prior crashed runs corrupt current state.

LAW 13 — STALEMATE DETECTION (AUDIT-ADDED)
Track skipped dimensions across iterations.
After 2 consecutive disagreements on the SAME dimension:
  1. Apply conservative safe default if one exists (e.g., ffmpeg-normalize for true_peak)
  2. Use highest-confidence model's recommendation as tiebreaker
  3. If no resolution after 3 identical iterations → abort cycle with CRITICAL Telegram alert
Config: `CONSENSUS_STRATEGY = "majority_conservative"` — on 3-way split, default to reject.

## IPC PROTOCOL (AUDIT-ADDED — replaces flag files)

### Stateful JSON Handshake
Flag files (`/tmp/render_fix_complete_iterN`) are BANNED.
All IPC uses stateful JSON with validation:

**Request** (written by overnight_render_loop.py):
```json
{
  "status": "pending",
  "iteration": 3,
  "pid": 12345,
  "request_timestamp": "2026-03-24T05:30:00Z",
  "grade_file": "/path/to/grade_iter3.json",
  "failing_dimensions": ["freeze_check", "true_peak_check", "visual_polish"]
}
```

**Completion** (written by render_improvement_loop.py):
```json
{
  "status": "complete",
  "request_timestamp": "2026-03-24T05:30:00Z",
  "completion_timestamp": "2026-03-24T06:15:00Z",
  "dimensions_fixed": ["freeze_check", "true_peak_check"],
  "dimensions_failed": [],
  "dimensions_skipped": ["visual_polish"],
  "cost_usd": 3.42,
  "diff_hash": "abc123"
}
```

**Validation rules:**
- Main loop validates `fix_complete.request_timestamp == fix_request.request_timestamp`
  before accepting result as valid for THIS run (prevents stale-flag misdirection)
- Improvement loop validates `fix_request.iteration` matches current known render
  iteration (prevents stale fix applied to wrong iteration)
- If iteration mismatch → write `"status": "stale"` and alert
- All files written with `chmod 600` (prevent world-readable IPC)

### Timeouts
- Per-iteration wait: 90 minutes hard timeout
- Aggregate improvement budget per cycle: 2 hours total
- Poll interval: 60 seconds
- On timeout: log CRITICAL, send Telegram alert, write `"status": "timeout"`, fail forward

### Circuit Breaker (AUDIT-ADDED)
`_consecutive_fix_failures` counter in main loop state.
After 2 consecutive fix timeouts or failures:
  → Abort full cycle
  → Send CRITICAL Telegram: "Repair watchdog appears offline — aborting render cycle"
  → Exit with non-zero status
Reset counter to 0 on any successful fix confirmation.

### Improvement Loop Heartbeat
Improvement loop writes `/tmp/improvement_loop.heartbeat.json` every 60 seconds:
```json
{"timestamp": "2026-03-24T05:45:00Z", "iteration": 3, "current_dimension": "freeze_check"}
```
Main loop validates during wait:
- File exists AND `(now - heartbeat_timestamp) < 120s`
- If stale > 120s → improvement loop has crashed → write timeout, alert, fail forward

## DIMENSION_MAP
# Maps each Gemini grade dimension to responsible files + functions
# Format: dimension_name → [(file, function_or_line_hint)]

DIMENSION_MAP = {
    "freeze_check":       [("video_pipeline_v3/clip_extractor.py", "generate_clip"),
                           ("video_pipeline_v3/assembler.py", "build_scene")],
    "true_peak_check":    [("video_pipeline_v3/assembler.py", "apply_loudnorm"),
                           ("video_pipeline_v3/assembler.py", "final_mix")],
    "loudness_check":     [("video_pipeline_v3/assembler.py", "apply_loudnorm")],
    "silence_check":      [("video_pipeline_v3/tts_engine.py", "generate_audio"),
                           ("video_pipeline_v3/assembler.py", "concat_audio")],
    "host_authenticity":  [("video_pipeline_v3/assembler.py", "generate_host_segment"),
                           ("oracle/avatar_server.py", "generate_video")],
    "visual_polish":      [("video_pipeline_v3/assembler.py", "build_scene"),
                           ("video_pipeline_v3/clip_extractor.py", "generate_clip")],
    "no_artifacts":       [("video_pipeline_v3/assembler.py", "preflight_check")],
    "audio_quality":      [("video_pipeline_v3/assembler.py", "final_mix")],
    "black_frames_check": [("video_pipeline_v3/assembler.py", "concat_segments")],
    "script_quality":     [("video_pipeline_v3/script_writer.py", "write_script")],
    "cold_open_hook":     [("video_pipeline_v3/script_writer.py", "write_cold_open")],
    "episode_title":      [("video_pipeline_v3/daily_producer.py", "generate_title")],
    "narrative_arc":      [("video_pipeline_v3/script_writer.py", "write_script")],
    "music_mix":          [("video_pipeline_v3/assembler.py", "mix_music")],
    "transitions":        [("video_pipeline_v3/assembler.py", "apply_transitions")],
    "clip_relevance":     [("video_pipeline_v3/clip_extractor.py", "score_clips")],
    # AUDIT-ADDED: previously missing dimensions
    "pacing":             [("video_pipeline_v3/script_writer.py", "write_script"),
                           ("video_pipeline_v3/assembler.py", "build_scene")],
    "subtitle_accuracy":  [("video_pipeline_v3/assembler.py", "generate_subtitles")],
    "color_grading":      [("video_pipeline_v3/assembler.py", "apply_color_grade")],
    "thumbnail_quality":  [("video_pipeline_v3/daily_producer.py", "generate_thumbnail")],
}

# Per-dimension metadata (AUDIT-ADDED)
DIMENSION_META = {
    # dimension_name: {priority, fix_complexity, max_cost_usd, safe_default}
    "freeze_check":       {"priority": "critical", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "true_peak_check":    {"priority": "critical", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": "ffmpeg-normalize -tp -2.0"},
    "black_frames_check": {"priority": "critical", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "host_authenticity":  {"priority": "critical", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "loudness_check":     {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": "loudnorm filter I=-14:LRA=7:TP=-2"},
    "silence_check":      {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "visual_polish":      {"priority": "high", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "audio_quality":      {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "script_quality":     {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "cold_open_hook":     {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "narrative_arc":      {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "music_mix":          {"priority": "medium", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "transitions":        {"priority": "medium", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "clip_relevance":     {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "no_artifacts":       {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "episode_title":      {"priority": "low", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "pacing":             {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "subtitle_accuracy":  {"priority": "medium", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "color_grading":      {"priority": "low", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "thumbnail_quality":  {"priority": "low", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
}

## DEFAULT_HANDLER (AUDIT-ADDED — for unmapped dimensions)
When a Gemini grade contains a dimension NOT in DIMENSION_MAP:
  1. Log WARNING: "Unknown dimension '[name]' encountered — score=[X]"
  2. Fire Telegram alert: "Unknown dimension '[name]' — PBX review needed"
  3. Route to generic CC prompt: "Investigate dimension '[name]' with Gemini feedback: [note].
     Identify the most likely responsible file and function. Do NOT implement any fix.
     Report your findings only."
  4. Queue for manual review — do NOT auto-fix unmapped dimensions
  5. Append to QWEN_CONTEXT_BIBLE.md: `UNMAPPED: [name] — [Gemini note]`

## QWEN INTEGRATION (AUDIT-HARDENED)
Model: qwen3:30b-a3b (runs on local 4090 via Ollama)
Endpoint: http://localhost:11434/api/generate
Fallback: qwen3:8b if 30b unavailable

### Pre-flight Health Check (MANDATORY)
Before starting improvement loop: `GET localhost:11434/api/tags`
If Ollama unreachable after 3 attempts:
  → Write `"status": "failed"` to IPC JSON immediately
  → Send Telegram: "Ollama unreachable — improvement loop cannot start"
  → Exit cleanly — do NOT crash

### Resilience Wrapper (MANDATORY on every Ollama call)
```python
# Pseudocode — every Qwen call MUST use this pattern
for attempt in range(3):
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        data = response.json()
        validate_schema(data, QWEN_RESPONSE_SCHEMA)  # jsonschema
        if data.get("fix_spec") is None:  # semantic null check
            raise ValueError("Qwen returned null fix_spec")
        return data
    except (ConnectionError, Timeout) as e:
        backoff = [2, 4, 8][attempt]
        log(f"Qwen attempt {attempt+1} failed: {e}, backing off {backoff}s")
        time.sleep(backoff)
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        log(f"Qwen response invalid: {e}")
        if attempt < 2: time.sleep(2)
# All 3 retries exhausted:
log(f"ERROR: Qwen unavailable after 3 retries for dimension {dim}")
telegram_alert(f"Qwen unavailable — skipping fix for {dim}")
mark_dimension_failed(dim)
continue  # graceful degradation — move to next dimension
```

Prompt template:
  "You are a senior video pipeline engineer. Here is a failing code section
   and the specific error description. Identify the root cause precisely and
   provide a minimal, surgical fix. Be concise. Output JSON only:
   {root_cause: str, fix_patch: str, confidence: float, verify_cmd: str}"

## LOOP FLOW (exact execution order — AUDIT-REVISED)

```
START: fix_request_iterN.json exists with status="pending"
  │
  ├─ 0. PREFLIGHT:
  │    ├─ Cleanup stale IPC files (LAW 12)
  │    ├─ Ollama health check (GET /api/tags, 3 retries)
  │    │   FAIL → write status="failed" to IPC, alert, exit
  │    └─ Write heartbeat file (first beat)
  │
  ├─ 1. INGEST: parse grade JSON from fix_request, extract failing dims (score < 8)
  │          sort by priority (DIMENSION_META) then score ascending (worst first)
  │
  ├─ 2. BIBLE READ: load QWEN_CONTEXT_BIBLE.md
  │          check if any failing dim has a known fix → apply directly, skip audit
  │          check stalemate history → skip dims with 2+ prior disagreements
  │
  ├─ 3. FOR EACH FAILING DIMENSION:
  │    │
  │    ├─ 3a. MAP: look up DIMENSION_MAP → get file + function
  │    │         if unmapped → DEFAULT_HANDLER (log, alert, skip — see above)
  │    │
  │    ├─ 3b. BUDGET CHECK: estimate cost for this dimension
  │    │         if cycle budget exceeded → Qwen-only mode
  │    │         if daily hard cap exceeded → mark remaining as "failed", alert, stop
  │    │
  │    ├─ 3c. EXTRACT: use ast/grep to pull exact function (≤120 lines)
  │    │         also pull the Gemini note for this dimension as context
  │    │
  │    ├─ 3d. QWEN (local, $0): send extracted section + Gemini note
  │    │         uses resilience wrapper (3 retries, backoff, schema validation)
  │    │         timeout: 30s per call
  │    │
  │    ├─ 3e. EXTERNAL LLMS (parallel threads, if Qwen confidence < 0.85):
  │    │         payload: Qwen findings + code section + Gemini note ONLY
  │    │         Gemini + GPT-4o simultaneously, 45s timeout each
  │    │         prompt: "Do you agree with this root cause? What is your fix?"
  │    │
  │    ├─ 3f. CONSENSUS CHECK:
  │    │         if Qwen + 1 external agree on root cause → proceed
  │    │         if Qwen confidence ≥ 0.85 + no external disagreement → proceed
  │    │         if disagreement:
  │    │           → check stalemate history for this dimension
  │    │           → if 2nd consecutive disagreement → apply safe_default or tiebreak
  │    │           → if 1st disagreement → Bible entry, Telegram, skip dim
  │    │
  │    ├─ 3g. WRITE FIX SPEC: append to /tmp/cc_render_fix_iterN.md
  │    │         format: dimension, file, function, exact patch, verification cmd
  │    │
  │    └─ 3h. UPDATE HEARTBEAT (every 60s during processing)
  │
  ├─ 4. WAIT FOR CC SLOT (zombie-safe detection — LAW 9)
  │         poll every 30s, max 30 min wait
  │         2-layer check: session exists + process alive + recent activity
  │         kill zombie sessions, log, relaunch
  │
  ├─ 5. FIRE CC SESSION:
  │         tmux new-session -d -s render_fix_iterN
  │         boot CC, send spec (with guardrails — see CC SPEC FORMAT below)
  │         wait for completion (poll for prompt return, max 45 min)
  │         write CC session heartbeat every 30s
  │
  ├─ 6. VERIFY (MANDATORY — LAW 6):
  │    ├─ Diff sanity check: count files changed + total diff lines
  │    │   if files_changed > expected OR diff_lines > 50 → REJECT, git revert HEAD
  │    ├─ regression_test.sh → 0 FAILs
  │    │   FAIL → git revert HEAD, Telegram alert, retry audit (max 2x)
  │    └─ per-dimension tests (freezedetect, ebur128, etc.)
  │         PASS: git commit, continue
  │         FAIL: git revert HEAD, Telegram alert, retry audit (max 2x)
  │
  ├─ 7. BIBLE WRITE: append all findings, fixes, results
  │
  ├─ 8. FIX HISTORY LOG: append to fix_history.jsonl
  │         {dimension, fix_applied, pre_score, iteration, cost_usd, outcome, timestamp}
  │
  ├─ 9. GIT PULL INTO RENDER_MAIN:
  │         tmux send-keys -t render_main "git pull" Enter
  │
  └─ 10. SIGNAL OVERNIGHT_RENDER_LOOP:
            Write IPC completion JSON (see IPC PROTOCOL above)
            Include dimensions_fixed[], dimensions_failed[], dimensions_skipped[]
            overnight_render_loop.py validates and proceeds to next render
```

## INTEGRATION WITH OVERNIGHT_RENDER_LOOP.PY (AUDIT-REVISED)
overnight_render_loop.py change (minimal, surgical):
After grade < 90:
  1. Write grade_iterN.json (already does this)
  2. Cleanup stale IPC files on startup (LAW 12)
  3. Write /tmp/fix_request_iterN.json (stateful JSON — see IPC PROTOCOL)
  4. Launch render_improvement_loop.py as subprocess with grade file path
  5. Poll for /tmp/fix_complete_iterN.json (60s interval, 90-min hard timeout)
     - Validate request_timestamp matches
     - Check improvement loop heartbeat for liveness
  6. On completion: read dimensions_fixed[], update cycle state
  7. On timeout: log CRITICAL, Telegram alert, increment _consecutive_fix_failures
  8. Circuit breaker: if _consecutive_fix_failures >= 2, abort cycle
  9. git pull (picks up fixes)
  10. Fire next render iteration

## CC SPEC FORMAT (written to /tmp/cc_render_fix_iterN.md) — AUDIT-HARDENED
For each consensus fix:
  FILE: video_pipeline_v3/assembler.py
  FUNCTION: apply_loudnorm (lines 847-891)
  ROOT CAUSE: [Qwen + LLM consensus]
  FIX: [exact patch]
  VERIFY: [ffmpeg/ffprobe command that proves fix worked]
  BIBLE ENTRY: [what to write to QWEN_CONTEXT_BIBLE.md]

CC instruction at top of spec (HARDENED):
  "STRICT INSTRUCTIONS — READ CAREFULLY:
   1. Implement ONLY the exact patches specified below. Nothing else.
   2. Do NOT refactor surrounding code. Do NOT rename variables. Do NOT add comments.
   3. Do NOT modify function signatures or add external dependencies.
   4. Do NOT touch files not specified in this fix spec.
   5. Maximum allowed diff: 50 lines across all patches combined.
   6. Run the verify command for each fix before committing.
   7. bash regression_test.sh must show 0 FAILs.
   8. If regression_test.sh fails, STOP. Do not commit. Report the failure.
   9. git add -A && git commit -m 'fix(pipeline): [dims fixed] — autonomous loop iterN'
   10. git push"

## TELEGRAM ALERTS
On loop start: "Render improvement loop started — iterN, score=X, dims=[list]"
On each fix: "Fix applied: [dimension] — [root cause summary]"
On completion: "Loop complete — iterN fixes committed, iterN+1 queued"
On disagreement: "LLM disagreement on [dimension] — PBX review needed"
On stalemate (2nd consecutive): "STALEMATE on [dimension] — applying tiebreak/default"
On hard budget limit: "Token budget hit — loop paused, manual review needed"
On Grade A: "GRADE A ACHIEVED — score=X, broadcast=True — publishing"
On zombie session: "ZOMBIE_SESSION_DETECTED — killed and relaunched"
On Qwen failure: "Qwen unavailable — skipping fix for [dimension]"
On circuit breaker: "CRITICAL: Repair watchdog offline — aborting render cycle"
On diff oversize: "CRITICAL: CC exceeded diff limit — fix rejected and reverted"
On consecutive fix failures: "CRITICAL: 2+ consecutive fix failures — cycle aborted"

## CONFIGURATION (AUDIT-ADDED — externalized from code)
All operational parameters MUST be configurable via environment variables
or a `render_improvement_config.yaml` file. No magic numbers in code.

```yaml
# render_improvement_config.yaml
max_iterations: 8
max_hours: 6
per_iteration_timeout_seconds: 5400  # 90 min
max_improvement_time_seconds: 7200   # 2 hours aggregate
cc_session_timeout_seconds: 2700     # 45 min
zombie_activity_threshold_seconds: 600  # 10 min
heartbeat_interval_seconds: 60
poll_interval_seconds: 60
consecutive_fix_failure_threshold: 2
cost_soft_cap_usd: 7.50
cost_hard_cap_daily_usd: 25.00
consensus_strategy: "majority_conservative"
stalemate_max_consecutive: 2
max_diff_lines: 50
ollama_timeout_seconds: 30
ollama_retry_count: 3
ollama_backoff_seconds: [2, 4, 8]
```

## WHAT THIS IS NOT
- Not a replacement for the human render loop — it runs BETWEEN iterations
- Not a general-purpose code fixer — only touches DIMENSION_MAP'd sections
- Not unlimited — hard token budget enforced, hard retry limit enforced
- Not autonomous past disagreement — contested fixes always go to PBX
- Not fire-and-forget — every operation has confirmation, timeout, and alerting

## SUCCESS METRIC
Grade improves by minimum 5 points per iteration cycle.
Grade A (90+) achieved within 4 iterations after loop activation.
External LLM spend under $7.50 per cycle (revised from $2.00 per audit findings).
Zero regressions introduced (enforced by mandatory revert-on-fail).

## ADDENDUM — INJECTED BEFORE BUILD (PBX-APPROVED)

### CONVERGENCE REQUIREMENT
The loop does NOT stop at a single Grade A.
Loop continues until 10 CONSECUTIVE Grade A renders (score >= 88, broadcast_ready=true).
Consecutive counter resets to 0 on any non-A grade.
Counter tracked in: ~/protocol_pulse/video_pipeline_v3/logs/consecutive_a_grades.txt
On 10 consecutive A grades: send Telegram "PIPELINE LOCKED — 10 consecutive Grade A renders. Loop complete." and exit.
On each Grade A: send Telegram "Grade A #{n}/10 — score=X. {n} more to lock."

### ANTI-HALLUCINATION GUARDRAILS FOR AUDIT SESSIONS

RULE 1 — BIG ISSUES FIRST, ALWAYS.
When cross_llm_audit.py synthesizes findings, sort all issues by impact:
  CRITICAL (score 0): Fix immediately. Everything else waits.
  HIGH (score 1-4): Fix in same cycle after CRITICAL resolved.
  MEDIUM (score 5-7): Only address after HIGH issues eliminated.
  LOW (score 8-9): Do not touch until pipeline consistently hits 90+.
Never fix LOW issues when CRITICAL issues exist. This is how cycles get wasted.

RULE 2 — NO SPECULATION IN AUDIT PROMPTS.
Every audit prompt must include this instruction to all 3 LLMs:
  "Only report issues you can verify from the code/data provided.
   Do not invent failure modes. Do not speculate about what might break.
   If you cannot see evidence of a problem in the actual files, say 'no issue found'."

RULE 3 — GEMINI VIDEO GRADING UPGRADE (critical for content dimensions).
Current grader sends only forensic metadata to Gemini — no actual video.
Gemini cannot score script_quality, cold_open_hook, narrative_arc, visual_polish,
host_authenticity, or pacing from render logs. All 7-8/10 scores on these are
hallucinated confidence, not real evaluation.
FIX: For content dimensions, upload the actual MP4 to Gemini using the
Files API (gemini.upload_file), then include the file reference in the grading prompt.
Gemini 2.5 Pro can watch video and evaluate content genuinely.
Technical dimensions (ffprobe metrics) remain as hard data — no change needed there.
Split the grading into two passes:
  PASS 1: Technical (ffprobe data only) — deterministic, no LLM needed
  PASS 2: Content (actual video upload to Gemini) — genuine multimodal eval
This eliminates the "Assumed acceptable" hallucination that inflates content scores.

RULE 4 — CONSENSUS THRESHOLD FOR FIXES.
A fix only gets implemented if Qwen + at least 1 external LLM identify the SAME root cause.
"Same" means: same file, same function, same mechanism. Not just "audio has issues."
Vague agreement is not consensus. Specific agreement is consensus.

RULE 5 — DIMENSION WEIGHTING REFLECTS REALITY.
Current weights: Technical 40%, Content 35%, Production 25%.
Problem: avatar (host_authenticity) is 1/24 dimensions but one 0/10 drops score by ~15 points.
Fix: critical failure dimensions (avatar, true_peak, black_frames, freeze_frames) must each
be individually gated — any single 0/10 on these makes broadcast_ready=false regardless of
overall weighted score. This prevents a technically perfect video with one fatal flaw
from sneaking through with a high overall score.

## AUDIT TRAIL
- Audit date: 2026-03-24
- Models: Gemini 2.5 Pro, GPT-4o, Grok-3
- Cycles: 2 (full cross-examination)
- Winner: Gemini (identified blocking-to-blind failure mode shift in Cycle 2)
- Critical issues found: 5 (IPC, timeout coupling, stalemate, CC guardrails, Qwen fault tolerance)
- All mitigations incorporated into gospel v1.1
- Audit artifacts: docs/audits/render-improvement-loop/
