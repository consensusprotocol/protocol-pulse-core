# CC BUILD SPEC — render_improvement_loop.py
# Fire this as a SEPARATE Claude Code session after the audit session completes.
# Date: 2026-03-24
# Source: Cross-LLM audit consensus (Gemini+GPT-4o+Grok, 2 cycles)

## STEP 1 — READ THE GOSPEL
Read ~/protocol_pulse/docs/gospels/RENDER_IMPROVEMENT_LOOP_GOSPEL.md fully.
This is the v1.1 audited spec. Every section, every law, every protocol must be followed exactly.
Do NOT deviate from the gospel. If something seems wrong, flag it — do not "fix" it silently.

## STEP 2 — READ THE AUDIT CONSENSUS
Read ~/protocol_pulse/docs/audits/render-improvement-loop/FINAL_CONSENSUS.md.
This contains the 2-cycle cross-LLM audit findings. The gospel already incorporates all
consensus fixes, but reading the audit gives you the WHY behind each design decision.

## STEP 3 — READ EXISTING CODE
Read these files to understand the integration points:
- ~/protocol_pulse/overnight_render_loop.py (full — understand `fire_cc_fix`, `run_single_render`, main loop)
- ~/protocol_pulse/video_pipeline_v3/gemini_grade.py (understand grade JSON format)
- ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md (understand Bible format)
- ~/protocol_pulse/utils/cross_llm_audit.py (understand LLM caller pattern)

## STEP 4 — BUILD render_improvement_loop.py
Create ~/protocol_pulse/render_improvement_loop.py

The file MUST implement the EXACT loop flow from the gospel (Section "LOOP FLOW").
Use the gospel as the single source of truth for:
- IPC protocol (stateful JSON handshake — Section "IPC PROTOCOL")
- Qwen integration (resilience wrapper — Section "QWEN INTEGRATION")
- CC session detection (zombie-safe — LAW 9)
- Diff sanity check + regression test + auto-revert (LAW 6)
- Budget enforcement (LAW 8)
- Stalemate detection (LAW 13)
- Clean startup state (LAW 12)
- Heartbeat writer
- Fix history logger
- Telegram alerts (all events listed in gospel)
- DEFAULT_HANDLER for unmapped dimensions
- DIMENSION_MAP and DIMENSION_META from gospel
- Configuration loaded from render_improvement_config.yaml with env var overrides

### Key implementation requirements:
1. **IPC JSON handshake** — read fix_request_iterN.json, write fix_complete_iterN.json
   with dimensions_fixed/failed/skipped arrays, timestamps, cost_usd, diff_hash
2. **Qwen resilience wrapper** — 3 retries, exponential backoff (2/4/8s), schema validation,
   semantic null check, graceful per-dimension degradation
3. **External LLM calls** — reuse the pattern from cross_llm_audit.py (parallel threads,
   Gemini + GPT-4o simultaneously, 45s timeout)
4. **CC session management** — zombie-safe tmux detection (2-layer: session exists +
   process alive + recent activity), auto-kill zombies, 30-min hard timeout
5. **CC spec writer** — hardened prompt with strict constraints (no refactor, no new deps,
   max 50 line diff, regression test mandatory)
6. **Verification gate** — diff sanity check → regression_test.sh → per-dim test →
   auto-revert on any failure
7. **Stalemate detection** — track skipped dims across iterations, apply tiebreak/default
   after 2 consecutive disagreements
8. **Budget tracking** — per-call token estimation, per-dimension budget enforcement,
   cycle soft cap, daily hard cap, cost ledger JSON
9. **Heartbeat writer** — update /tmp/improvement_loop.heartbeat.json every 60s
10. **Fix history** — append to fix_history.jsonl after each dimension outcome
11. **Telegram alerts** — all events from gospel Telegram section
12. **BIBLE updates** — read before cycle, append after each fix (success or failure)
13. **Config loading** — render_improvement_config.yaml with all parameters from gospel

### What NOT to do:
- Do NOT modify overnight_render_loop.py in this session (that's a separate task)
- Do NOT modify assembler.py, clip_extractor.py, or any pipeline files
- Do NOT add new pip dependencies without checking they're already installed
- Do NOT create test files — the test is a simulation (see STEP 5)

## STEP 5 — TEST: SIMULATE A GRADE WITH 3 FAILING DIMENSIONS
Create a test script at ~/protocol_pulse/tests/test_render_improvement_loop.py

The test should:
1. Create a mock grade_iter1.json with 3 failing dimensions:
   - freeze_check: score 3 (CRITICAL)
   - true_peak_check: score 5 (HIGH)
   - script_quality: score 6 (MEDIUM)
2. Create a mock fix_request_iter1.json in /tmp/
3. Run the improvement loop in "dry-run" mode (no actual CC sessions, no actual LLM calls)
   - Mock Qwen responses (return valid JSON with fix_spec)
   - Mock external LLM responses (agree with Qwen)
   - Mock CC session (create tmux session, write dummy commit)
4. Verify:
   - IPC JSON completion file is written with correct schema
   - dimensions_fixed list contains the 3 dimensions
   - Heartbeat file was updated
   - Fix history JSONL was appended
   - BIBLE was updated
   - Stale IPC files were cleaned on startup
   - Budget was tracked correctly

## STEP 6 — REGRESSION TEST
```bash
cd ~/protocol_pulse
bash regression_test.sh
```
Must show 0 FAILs. If any fail, investigate and fix before committing.

## STEP 7 — COMMIT
```bash
git add render_improvement_loop.py
git add tests/test_render_improvement_loop.py
git add docs/gospels/RENDER_IMPROVEMENT_LOOP_GOSPEL.md
git commit -m "feat(pipeline): render_improvement_loop.py — autonomous grade-driven fix loop"
git push
```

## STEP 8 — CREATE render_improvement_config.yaml
Write ~/protocol_pulse/render_improvement_config.yaml with all defaults from gospel.
Add to git commit.

## CRITICAL REMINDERS
- The gospel is LAW. Do not improvise. Do not add features not in the gospel.
- Every Qwen call uses the resilience wrapper. No exceptions.
- Every CC session uses zombie-safe detection. No exceptions.
- Every fix goes through diff sanity check → regression test → auto-revert. No exceptions.
- IPC is stateful JSON, not flag files. No exceptions.
- Log every state transition. Silent failures are pipeline-killing defects.
- Max allowed diff per fix: 50 lines.
- If you're unsure about anything, flag it in a comment — do not guess.
