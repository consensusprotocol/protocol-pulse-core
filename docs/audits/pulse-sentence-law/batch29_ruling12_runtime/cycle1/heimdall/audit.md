# Heimdall audit

**Question:** Batch 29 = RULING 12 (orchestrator 2026-11-12 '09:32'): the runtime gate G5 (segment_v1/qa_gates.gate_g5, both aspects 16:9 and 9:16) changes its duration window from 60-120 s to: the measured final is ACCEPTED from 58.0 to 72.0 s inclusive; a value outside the 60-70 s format target (but inside 58-72) passes and is recorded as a deviation (results['duration_deviation'], a string naming the size and side); outside 58-72 it fails, and a failure carries no deviation. Constants G5_DURATION_ACCEPT_S = (58.0, 72.0) and G5_DURATION_TARGET_S = (60.0, 70.0). Must-fail tests (test_round2_mustfail TestDurationWindow): 57.9 and 72.1 rejected and 58.0 and 72.0 accepted in both aspects; 59.625 and 71.084 accepted with the exact deviation strings; 60 / 65 / 70 accepted with no deviation; the old 102.9 s vertical (accepted under 60-120) is now rejected; 50 and 130 rejected. Mutations (57.9 / 72.1 bounds, the old 60-120 window, a 59-70 target, no deviation, strict bounds, a deviation on a failure) each fail a test. Nothing else in G5 (dims, SAR, fps, loudness, true peak) changes.
FIND: any boundary error; any way a value outside 58-72 passes or a value inside fails; a deviation string that is wrong or missing; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0058
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
