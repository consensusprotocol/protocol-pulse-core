# GOSPEL: REGRESSION TEST AUTO-REPAIR
# Version 1.0 | March 2026 | Status: NOT BUILT ❌

## PROBLEM BEING SOLVED
When regression_test.sh fails before a commit, a developer (or CC session)
must manually read the failure, identify the file, write the fix, and re-run.
This breaks the automated pipeline — CC sessions stall waiting for human input.
Local Qwen can diagnose and patch regression failures autonomously in <60 seconds.

## WHAT IT DOES
1. Runs after every CC session completes a code change
2. If regression_test.sh exits with code 1 (FAILs exist): captures failure output
3. Sends failure + relevant file content to local Qwen for diagnosis
4. Applies patch via git apply
5. Re-runs regression_test.sh
6. If passes: commits patch + Telegrams success
7. If still fails after 2 attempts: Telegrams PBX + halts (never blind commit)

## MODEL
LOCAL: Qwen3-Coder:30b via Ollama port 11435 (GPU 2, free)
No API fallback — if Ollama down, halt and alert. Never patch blindly without diagnosis.

## FILES
Service:     ~/protocol_pulse/services/regression_auto_repair.py (TO BUILD)
Trigger:     Called from overnight_render_loop.py before each commit attempt
             Called from watchdog --mode reactive when FAILs detected
Log:         ~/protocol_pulse/logs/regression_repair.log
Patch log:   ~/protocol_pulse/logs/regression_patches.jsonl

## TRIGGER CONDITIONS
Triggered when regression_test.sh output contains:
  "[FAIL]" — hard failure, must fix before commit
NOT triggered when only "[WARN]" — warnings are acceptable

## REPAIR WORKFLOW
Step 1: Run regression_test.sh, capture stdout
Step 2: Parse failing test names and which check failed
Step 3: For each FAIL:
  - Identify the file the test is checking (from test name)
  - Read that file's relevant section
  - Send to Qwen: "regression test failed with this output: {output}
    Here is the relevant file content: {content}
    Write a minimal unified diff to fix the failing test."
Step 4: Apply diff with: patch -p1 < /tmp/repair.patch
Step 5: Re-run regression_test.sh
Step 6a: All tests pass → git add + commit + Telegram "REPAIRED: {test_name}"
Step 6b: Still failing → revert with git checkout → Telegram alert → halt

## SAFETY RULES (non-negotiable)
1. Never repair the same file twice in one session (circular fix risk)
2. Never repair regression_test.sh itself
3. Never repair assembler.py (too complex, too risky)
4. Max 3 repair attempts per CC session total
5. Always git stash before first repair attempt so revert is clean
6. Every patch saved to regression_patches.jsonl for audit trail
7. If Qwen confidence in patch < 0.7: do not apply, alert only

## REPAIR PROMPT TEMPLATE
system: "You are a Python/bash debugging expert. Analyze this regression test
         failure and return ONLY a valid unified diff patch that fixes it.
         Be minimal — change as few lines as possible."
user:   "REGRESSION FAILURE:\n{test_output}\n\nFILE: {filename}\n{content[:2000]}"

## INTEGRATION WITH WATCHDOG
Watchdog --mode reactive checks for regression failures every 60 seconds.
If regression_test.sh shows FAILs: calls regression_auto_repair.py
This means failed commits get repaired within 60-120 seconds automatically.

## WHAT NEVER CHANGES
- Never commit without regression_test.sh = 0 FAILs (this gospel does not override PIPELINE_LAWS)
- Repair service must itself be exempt from auto-repair (no self-modification)
- All patches logged permanently — full audit trail required
- Human override always available: touch /tmp/watchdog_repair_disabled
